import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Pose2D(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    x: float
    y: float
    yaw_rad: float


class Goal2D(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    x: float
    y: float


class RobotScenarioConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    robot_id: str
    marker_id: int
    spawn: Pose2D
    goal: Goal2D
    initial_task: str

    @field_validator("robot_id")
    @classmethod
    def _robot_id_format(cls, v: str) -> str:
        if not re.match(r"^robot_[1-9][0-9]*$", v):
            raise ValueError(f"robot_id must match robot_N (N >= 1); got {v!r}")
        return v

    @field_validator("marker_id")
    @classmethod
    def _marker_id_range(cls, v: int) -> int:
        if not (1 <= v <= 49):
            raise ValueError(f"marker_id must be in 1..49; got {v}")
        return v


class TimedObstacleConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    obstacle_id: str
    asset: str
    spawn_at_sec: float
    remove_at_sec: float | None = None
    pose: Pose2D

    @field_validator("spawn_at_sec")
    @classmethod
    def _spawn_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"spawn_at_sec must be >= 0; got {v}")
        return v

    @model_validator(mode="after")
    def _remove_after_spawn(self) -> "TimedObstacleConfig":
        if self.remove_at_sec is not None and self.remove_at_sec <= self.spawn_at_sec:
            raise ValueError(
                f"remove_at_sec ({self.remove_at_sec}) must be > spawn_at_sec ({self.spawn_at_sec})"
            )
        return self


class AisleBarrierConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    effective_width_m: float
    center_x_m: float
    length_m: float

    @field_validator("effective_width_m")
    @classmethod
    def _effective_width_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"effective_width_m must be > 0; got {v}")
        return v

    @field_validator("length_m")
    @classmethod
    def _length_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"length_m must be > 0; got {v}")
        return v


class ExpectedConflictConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    type: Literal["deadlock", "bottleneck", "anomaly"]
    involved_robots: tuple[str, ...]
    onset_window_sec: tuple[float, float]
    min_duration_sec: float

    @field_validator("involved_robots")
    @classmethod
    def _non_empty(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if not v:
            raise ValueError("involved_robots must be non-empty")
        return v

    @field_validator("onset_window_sec")
    @classmethod
    def _window_increasing(cls, v: tuple[float, float]) -> tuple[float, float]:
        if v[0] >= v[1]:
            raise ValueError(f"onset_window_sec must be increasing; got {v}")
        return v


class ScenarioRuntimeOverrides(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    physics_hz: int = 60
    rendering_hz: int = 30
    duration_sec: float | None = None

    @field_validator("physics_hz")
    @classmethod
    def _physics_hz_fixed(cls, v: int) -> int:
        if v != 60:
            raise ValueError("physics_hz must be 60 for schema_version 1")
        return v

    @field_validator("rendering_hz")
    @classmethod
    def _rendering_hz_fixed(cls, v: int) -> int:
        if v != 30:
            raise ValueError("rendering_hz must be 30 for schema_version 1")
        return v


class ScenarioConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1]
    name: Literal["head_on_deadlock", "intersection_bottleneck", "dynamic_anomaly"]
    seed: int
    duration_sec: float
    robots: tuple[RobotScenarioConfig, ...]
    timed_obstacles: tuple[TimedObstacleConfig, ...] = ()
    aisle_barrier: AisleBarrierConfig | None = None
    expected_conflict: ExpectedConflictConfig
    runtime: ScenarioRuntimeOverrides = Field(default_factory=ScenarioRuntimeOverrides)

    @field_validator("seed")
    @classmethod
    def _seed_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"seed must be >= 0; got {v}")
        return v

    @field_validator("duration_sec")
    @classmethod
    def _duration_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"duration_sec must be > 0; got {v}")
        return v

    @model_validator(mode="after")
    def _cross_field_validation(self) -> "ScenarioConfig":
        robot_ids = [r.robot_id for r in self.robots]
        if len(robot_ids) != len(set(robot_ids)):
            raise ValueError(f"robot_id values must be unique; got {robot_ids}")

        marker_ids = [r.marker_id for r in self.robots]
        if len(marker_ids) != len(set(marker_ids)):
            raise ValueError(f"marker_id values must be unique; got {marker_ids}")

        for r in self.robots:
            n = int(r.robot_id.split("_")[1])
            if r.marker_id != n:
                raise ValueError(
                    f"robot {r.robot_id!r} must have marker_id={n}; got {r.marker_id}"
                )

        for obs in self.timed_obstacles:
            end = obs.remove_at_sec if obs.remove_at_sec is not None else self.duration_sec
            if obs.spawn_at_sec >= self.duration_sec:
                raise ValueError(
                    f"obstacle {obs.obstacle_id!r} spawn_at_sec {obs.spawn_at_sec} "
                    f">= duration_sec {self.duration_sec}"
                )
            if end > self.duration_sec:
                raise ValueError(
                    f"obstacle {obs.obstacle_id!r} remove_at_sec {end} "
                    f"> duration_sec {self.duration_sec}"
                )

        robot_id_set = set(robot_ids)
        for rid in self.expected_conflict.involved_robots:
            if rid not in robot_id_set:
                raise ValueError(
                    f"involved_robot {rid!r} not in configured robots {robot_id_set}"
                )

        w_start, w_end = self.expected_conflict.onset_window_sec
        if w_end > self.duration_sec:
            raise ValueError(
                f"onset_window_sec end {w_end} > duration_sec {self.duration_sec}"
            )

        return self


class RobotAssetConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    asset_name: Literal["turtlebot3_burger"] = "turtlebot3_burger"
    left_wheel_joint: Literal["wheel_left_joint"] = "wheel_left_joint"
    right_wheel_joint: Literal["wheel_right_joint"] = "wheel_right_joint"
    # The URDF importer's fix_base default welds base_link to the world via this
    # joint; it must be disabled so the differential drive can move the chassis.
    base_fixed_joint: Literal["base_joint"] = "base_joint"
    base_link: Literal["base_link"] = "base_link"
    lidar_link: Literal["base_scan"] = "base_scan"
    wheel_radius_m: float = 0.033
    wheel_separation_m: float = 0.160
    max_linear_velocity_mps: float = 0.22
    max_angular_velocity_radps: float = 2.84
    wheel_drive_stiffness: float = 0.0
    wheel_drive_damping: float = 1000.0
    command_timeout_sec: float = 0.5
    wheel_static_friction: float = 0.8
    wheel_dynamic_friction: float = 0.6


class CameraConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    prim_path: Literal["/World/Sensors/OverheadCamera"] = "/World/Sensors/OverheadCamera"
    frame_id: Literal["overhead_camera"] = "overhead_camera"
    width: Literal[1280] = 1280
    height: Literal[960] = 960
    fps: Literal[30] = 30
    position_m: tuple[float, float, float] = (0.0, 0.0, 3.0)
    # Nadir orientation (w, x, y, z). Parameterized so tilted-camera mount (spec §13)
    # is a config-only change; default is identity = straight down.
    orientation_quat_wxyz: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    focal_length_mm: float = 10.48
    horizontal_aperture_mm: float = 20.955
    # Square-pixel vertical aperture; CameraInfo K and M1 homography must match.
    vertical_aperture_mm: float = 15.716
    # Central conflict ROI (PoC, not full room — spec FR6.6.5).
    roi_width_m: float = 6.0
    roi_depth_m: float = 4.5


class WarehouseConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    width_m: float = 12.0
    depth_m: float = 8.0
    nominal_aisle_width_m: float = 1.2
    wall_thickness_m: float = 0.1
    wall_height_m: float = 1.2


class ResolvedRunConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    scenario_path: Path
    scenario: ScenarioConfig
    headless: bool
    repetitions: int
    output_dir: Path
    topic_timeout_sec: float
    ros_domain_id: int | None


class RunResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: str
    repetition: int
    completed: bool
    elapsed_simulation_sec: float
    manifest_path: Path
    failure: str | None

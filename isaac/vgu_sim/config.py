import re
from pathlib import Path
from typing import Any, Literal

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


class ObstacleSize(BaseModel):
    """Bounding-box size in meters for a static or timed obstacle."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    x_m: float = Field(default=0.3, gt=0)
    y_m: float = Field(default=0.3, gt=0)
    z_m: float = Field(default=0.5, gt=0)


class StaticObstacleConfig(BaseModel):
    """A fixed-pose obstacle present for the entire scenario duration."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    obstacle_id: str = Field(min_length=1)
    pose: Pose2D
    size: ObstacleSize = ObstacleSize()


class TimedObstacleConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    obstacle_id: str
    asset: str
    spawn_at_sec: float
    remove_at_sec: float | None = None
    pose: Pose2D
    size: ObstacleSize = ObstacleSize()

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


class HeadOnAsymmetricParams(BaseModel):
    """Parametric knobs for the head-on-asymmetric scenario family."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    blocker_west_m: float | None = None
    blocker_east_m: float | None = None
    arrival_offset_m: float = 0.0

    @field_validator("blocker_west_m", "blocker_east_m")
    @classmethod
    def _blocker_non_negative(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError(f"blocker offset must be >= 0 when set; got {v}")
        return v

    @field_validator("arrival_offset_m")
    @classmethod
    def _arrival_offset_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"arrival_offset_m must be >= 0; got {v}")
        return v


class OracleConfig(BaseModel):
    """The ground-truth yield decision and its rationale for a scenario."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    correct_yielder: str
    fcfs_yielder: str
    feasible_yielders: tuple[str, ...]
    objective: Literal["min_total_time_to_goal"] = "min_total_time_to_goal"
    rationale: str

    @model_validator(mode="after")
    def _feasible_yielders_contain_correct(self) -> "OracleConfig":
        if not self.feasible_yielders:
            raise ValueError("feasible_yielders must be non-empty")
        if self.correct_yielder not in self.feasible_yielders:
            raise ValueError(
                f"feasible_yielders must contain correct_yielder "
                f"{self.correct_yielder!r}; got {self.feasible_yielders}"
            )
        return self

    @property
    def contrasts_fcfs(self) -> bool:
        """Whether the correct yielder differs from the naive FCFS yielder."""
        return self.correct_yielder != self.fcfs_yielder


FAMILY_BY_LEGACY_NAME: dict[str, str] = {
    "head_on_deadlock": "head_on",
    "intersection_bottleneck": "intersection",
    "dynamic_anomaly": "dynamic_anomaly",
}
# normal_flow is the T0 negative-control family: no conflict is expected, so
# its scenarios carry `expected_conflict: null` (and only they may).
ScenarioFamily = Literal["head_on", "intersection", "dynamic_anomaly", "normal_flow"]
CONFLICT_FREE_FAMILIES: frozenset[str] = frozenset({"normal_flow"})


class ScenarioConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1]
    name: str
    family: ScenarioFamily
    seed: int
    duration_sec: float
    robots: tuple[RobotScenarioConfig, ...]
    timed_obstacles: tuple[TimedObstacleConfig, ...] = ()
    static_obstacles: tuple[StaticObstacleConfig, ...] = ()
    aisle_barrier: AisleBarrierConfig | None = None
    parameters: HeadOnAsymmetricParams | None = None
    oracle: OracleConfig | None = None
    # Required but nullable: every scenario must state its conflict, and null
    # is the explicit "none expected" of a conflict-free family.
    expected_conflict: ExpectedConflictConfig | None
    runtime: ScenarioRuntimeOverrides = Field(default_factory=ScenarioRuntimeOverrides)

    @model_validator(mode="before")
    @classmethod
    def _infer_family_from_legacy_name(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "family" in data:
            return data
        name = data.get("name")
        family = FAMILY_BY_LEGACY_NAME.get(name)
        if family is None:
            raise ValueError(f"family is required for scenario name {name!r}")
        return {**data, "family": family}

    @field_validator("name")
    @classmethod
    def _name_format(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", v):
            raise ValueError(f"name must match ^[a-z][a-z0-9_]*$; got {v!r}")
        return v

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
        conflict_free = self.family in CONFLICT_FREE_FAMILIES
        if self.expected_conflict is None and not conflict_free:
            raise ValueError(
                f"expected_conflict may be null only for families "
                f"{sorted(CONFLICT_FREE_FAMILIES)}; got family {self.family!r}"
            )
        if self.expected_conflict is not None and conflict_free:
            raise ValueError(
                f"family {self.family!r} expects no conflict: expected_conflict must be null"
            )
        if self.expected_conflict is not None:
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

        obstacle_ids = [o.obstacle_id for o in self.static_obstacles] + [
            o.obstacle_id for o in self.timed_obstacles
        ]
        if len(obstacle_ids) != len(set(obstacle_ids)):
            raise ValueError(
                f"obstacle_id values must be unique across static and timed "
                f"obstacles; got {obstacle_ids}"
            )

        if self.oracle is not None:
            oracle_robot_ids = (
                self.oracle.correct_yielder,
                self.oracle.fcfs_yielder,
                *self.oracle.feasible_yielders,
            )
            for rid in oracle_robot_ids:
                if rid not in robot_id_set:
                    raise ValueError(
                        f"oracle robot {rid!r} not in configured robots {robot_id_set}"
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

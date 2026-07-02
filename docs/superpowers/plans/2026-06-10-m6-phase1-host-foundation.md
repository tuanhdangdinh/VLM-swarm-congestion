# M6 Simulation – Phase 1: Host-Testable Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the host-testable layer of Module 6: Pydantic config models, path resolution, canonical scenario YAMLs, event scheduler, and conflict-oracle pure functions — everything runnable with `pytest tests/unit -q` on macOS without Isaac Sim.

**Architecture:** All code lives under the new top-level `isaac/` package. Config models are frozen Pydantic v2 with `extra="forbid"`. Path logic is pure Python. Event scheduler and conflict oracle are pure functions with no I/O. The Isaac Sim USD/ROS tasks are deferred to Phase 2.

**Tech Stack:** Python 3.10+, Pydantic v2, PyYAML, pytest. No ROS2, no Isaac Sim, no OpenCV required.

---

## File Map

| File | Responsibility |
|---|---|
| `isaac/__init__.py` | Package root |
| `isaac/scripts/__init__.py` | Scripts sub-package |
| `isaac/vgu_sim/__init__.py` | Library sub-package |
| `isaac/vgu_sim/config.py` | All Pydantic v2 models (spec §4) |
| `isaac/vgu_sim/paths.py` | Canonical path resolution |
| `isaac/vgu_sim/event_scheduler.py` | Timed obstacle scheduler (spec §7.6) |
| `isaac/vgu_sim/oracle.py` | Conflict-detection pure functions (spec §9.4) |
| `isaac/config/robot.yaml` | RobotAssetConfig defaults |
| `isaac/config/warehouse.yaml` | WarehouseConfig defaults |
| `isaac/config/lidar/turtlebot3_lds_01.json` | RTX lidar sensor profile |
| `isaac/config/scenarios/head_on_deadlock.yaml` | Canonical head-on config (spec §4.3) |
| `isaac/config/scenarios/intersection_bottleneck.yaml` | Canonical bottleneck config (spec §8.2) |
| `isaac/config/scenarios/dynamic_anomaly.yaml` | Canonical anomaly config (spec §8.3) |
| `tests/unit/test_m6_config.py` | Config model unit tests |
| `tests/unit/test_m6_paths.py` | Path resolution unit tests |
| `tests/unit/test_m6_event_scheduler.py` | Scheduler unit tests |
| `tests/unit/test_m6_oracle.py` | Oracle unit tests |

---

### Task 1: Package Scaffold

**Files:**
- Create: `isaac/__init__.py`
- Create: `isaac/scripts/__init__.py`
- Create: `isaac/vgu_sim/__init__.py`
- Create: `isaac/assets/markers/aruco_4x4_50/.gitkeep`
- Create: `isaac/assets/robots/turtlebot3_burger/.gitkeep`
- Create: `isaac/assets/warehouse/.gitkeep`
- Create: `isaac/scenarios/.gitkeep`

- [ ] **Step 1: Create package files**

```bash
mkdir -p isaac/scripts isaac/vgu_sim \
         isaac/assets/markers/aruco_4x4_50 \
         isaac/assets/robots/turtlebot3_burger \
         isaac/assets/warehouse \
         isaac/scenarios \
         isaac/config/lidar \
         isaac/config/scenarios
touch isaac/__init__.py isaac/scripts/__init__.py isaac/vgu_sim/__init__.py
touch isaac/assets/markers/aruco_4x4_50/.gitkeep
touch isaac/assets/robots/turtlebot3_burger/.gitkeep
touch isaac/assets/warehouse/.gitkeep
touch isaac/scenarios/.gitkeep
```

- [ ] **Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '.'); import isaac; import isaac.vgu_sim; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add isaac/
git commit -m "chore: scaffold isaac package structure for M6"
```

---

### Task 2: Pydantic Config Models

**Files:**
- Create: `isaac/vgu_sim/config.py`
- Create: `tests/unit/test_m6_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_m6_config.py
import math
import pytest
from pydantic import ValidationError
from isaac.vgu_sim.config import (
    Pose2D, Goal2D, RobotScenarioConfig, TimedObstacleConfig,
    ExpectedConflictConfig, ScenarioRuntimeOverrides, ScenarioConfig,
    RobotAssetConfig, CameraConfig, WarehouseConfig, ResolvedRunConfig, RunResult,
)
from pathlib import Path


VALID_HEAD_ON = {
    "schema_version": 1,
    "name": "head_on_deadlock",
    "seed": 42,
    "duration_sec": 45.0,
    "robots": [
        {"robot_id": "robot_1", "marker_id": 1,
         "spawn": {"x": -4.5, "y": 0.0, "yaw_rad": 0.0},
         "goal": {"x": 4.5, "y": 0.0}, "initial_task": "cross_narrow_aisle"},
        {"robot_id": "robot_2", "marker_id": 2,
         "spawn": {"x": 4.5, "y": 0.0, "yaw_rad": math.pi},
         "goal": {"x": -4.5, "y": 0.0}, "initial_task": "cross_narrow_aisle"},
    ],
    "timed_obstacles": [],
    "expected_conflict": {
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2"],
        "onset_window_sec": [8.0, 25.0],
        "min_duration_sec": 2.0,
    },
    "runtime": {"physics_hz": 60, "rendering_hz": 30},
}


def test_valid_head_on_parses():
    cfg = ScenarioConfig.model_validate(VALID_HEAD_ON)
    assert cfg.name == "head_on_deadlock"
    assert cfg.seed == 42
    assert len(cfg.robots) == 2


def test_invalid_robot_id_format_rejected():
    bad = {**VALID_HEAD_ON, "robots": [
        {**VALID_HEAD_ON["robots"][0], "robot_id": "bot_1"},
        VALID_HEAD_ON["robots"][1],
    ]}
    with pytest.raises(ValidationError, match="robot_id"):
        ScenarioConfig.model_validate(bad)


def test_duplicate_robot_ids_rejected():
    bad = {**VALID_HEAD_ON, "robots": [
        VALID_HEAD_ON["robots"][0],
        {**VALID_HEAD_ON["robots"][1], "robot_id": "robot_1"},
    ]}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate(bad)


def test_duplicate_marker_ids_rejected():
    bad = {**VALID_HEAD_ON, "robots": [
        VALID_HEAD_ON["robots"][0],
        {**VALID_HEAD_ON["robots"][1], "marker_id": 1},
    ]}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate(bad)


def test_marker_id_must_match_robot_number():
    bad = {**VALID_HEAD_ON, "robots": [
        {**VALID_HEAD_ON["robots"][0], "marker_id": 5},
        VALID_HEAD_ON["robots"][1],
    ]}
    with pytest.raises(ValidationError, match="marker_id"):
        ScenarioConfig.model_validate(bad)


def test_negative_seed_rejected():
    with pytest.raises(ValidationError, match="seed"):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "seed": -1})


def test_onset_window_outside_duration_rejected():
    bad_conflict = {**VALID_HEAD_ON["expected_conflict"],
                    "onset_window_sec": [30.0, 50.0]}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "expected_conflict": bad_conflict})


def test_onset_window_must_be_increasing():
    bad_conflict = {**VALID_HEAD_ON["expected_conflict"],
                    "onset_window_sec": [20.0, 10.0]}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "expected_conflict": bad_conflict})


def test_timed_obstacle_remove_before_spawn_rejected():
    obstacle = {"obstacle_id": "obs_1", "asset": "dynamic_obstacle.usd",
                "spawn_at_sec": 10.0, "remove_at_sec": 5.0,
                "pose": {"x": 1.5, "y": 0.0, "yaw_rad": 0.0}}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "timed_obstacles": [obstacle]})


def test_marker_id_out_of_range_rejected():
    bad = {**VALID_HEAD_ON, "robots": [
        {**VALID_HEAD_ON["robots"][0], "marker_id": 50},
        VALID_HEAD_ON["robots"][1],
    ]}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate(bad)


def test_camera_config_defaults():
    cam = CameraConfig()
    assert cam.width == 1280
    assert cam.height == 960
    assert cam.focal_length_mm == pytest.approx(10.48)
    assert cam.horizontal_aperture_mm == pytest.approx(20.955)
    assert cam.vertical_aperture_mm == pytest.approx(15.716)
    assert cam.orientation_quat_wxyz == (1.0, 0.0, 0.0, 0.0)


def test_robot_asset_config_defaults():
    r = RobotAssetConfig()
    assert r.wheel_radius_m == pytest.approx(0.033)
    assert r.wheel_separation_m == pytest.approx(0.160)
    assert r.max_linear_velocity_mps == pytest.approx(0.22)


def test_scenario_config_is_frozen():
    cfg = ScenarioConfig.model_validate(VALID_HEAD_ON)
    with pytest.raises(Exception):
        cfg.seed = 99
```

- [ ] **Step 2: Run tests — verify all fail**

```bash
pytest tests/unit/test_m6_config.py -v 2>&1 | head -20
```
Expected: `ImportError` or `ModuleNotFoundError` for `isaac.vgu_sim.config`

- [ ] **Step 3: Implement `isaac/vgu_sim/config.py`**

```python
# isaac/vgu_sim/config.py
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
```

- [ ] **Step 4: Run tests — verify all pass**

```bash
pytest tests/unit/test_m6_config.py -v
```
Expected: all 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/config.py tests/unit/test_m6_config.py
git commit -m "feat: add M6 Pydantic config models"
```

---

### Task 3: Path Resolution

**Files:**
- Create: `isaac/vgu_sim/paths.py`
- Create: `tests/unit/test_m6_paths.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_m6_paths.py
from pathlib import Path
import pytest
from isaac.vgu_sim.paths import (
    isaac_root,
    robot_asset_path,
    warehouse_asset_path,
    scenario_config_path,
    scenario_output_path,
    run_output_dir,
)


def test_robot_asset_path_is_under_isaac():
    p = robot_asset_path()
    assert p == Path("isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.usda")


def test_warehouse_asset_path():
    p = warehouse_asset_path()
    assert p == Path("isaac/assets/warehouse/warehouse_base.usd")


def test_scenario_config_path():
    p = scenario_config_path("head_on_deadlock")
    assert p == Path("isaac/config/scenarios/head_on_deadlock.yaml")


def test_scenario_output_path():
    p = scenario_output_path("head_on_deadlock")
    assert p == Path("isaac/scenarios/head_on_deadlock.usd")


def test_run_output_dir():
    p = run_output_dir(Path("data/logs/simulation"), "head_on_deadlock", seed=42, rep=0)
    assert p == Path("data/logs/simulation/head_on_deadlock-seed42-rep000")


def test_paths_are_relative():
    """All canonical paths must be relative — no absolute machine paths."""
    for p in [robot_asset_path(), warehouse_asset_path(),
              scenario_config_path("dynamic_anomaly"), scenario_output_path("dynamic_anomaly")]:
        assert not p.is_absolute(), f"{p} must be relative"


def test_component_asset_paths():
    from isaac.vgu_sim.paths import component_asset_path
    assert component_asset_path("rack_block") == Path("isaac/assets/warehouse/rack_block.usd")
    assert component_asset_path("aisle_barrier") == Path("isaac/assets/warehouse/aisle_barrier.usd")
    assert component_asset_path("dynamic_obstacle") == Path("isaac/assets/warehouse/dynamic_obstacle.usd")
    assert component_asset_path("loading_zone") == Path("isaac/assets/warehouse/loading_zone.usd")
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/unit/test_m6_paths.py -v 2>&1 | head -10
```
Expected: `ImportError` for `isaac.vgu_sim.paths`

- [ ] **Step 3: Implement `isaac/vgu_sim/paths.py`**

```python
# isaac/vgu_sim/paths.py
from pathlib import Path

_ISAAC_ROOT = Path("isaac")
_ASSETS = _ISAAC_ROOT / "assets"
_SCENARIOS_OUT = _ISAAC_ROOT / "scenarios"
_CONFIG = _ISAAC_ROOT / "config"

_COMPONENT_NAMES = frozenset(
    {"rack_block", "loading_zone", "aisle_barrier", "dynamic_obstacle"}
)


def isaac_root() -> Path:
    return _ISAAC_ROOT


def robot_asset_path() -> Path:
    return _ASSETS / "robots" / "turtlebot3_burger" / "turtlebot3_burger.usda"


def warehouse_asset_path() -> Path:
    return _ASSETS / "warehouse" / "warehouse_base.usd"


def component_asset_path(name: str) -> Path:
    if name not in _COMPONENT_NAMES:
        raise ValueError(f"Unknown component asset {name!r}; known: {sorted(_COMPONENT_NAMES)}")
    return _ASSETS / "warehouse" / f"{name}.usd"


def scenario_config_path(name: str) -> Path:
    return _CONFIG / "scenarios" / f"{name}.yaml"


def scenario_output_path(name: str) -> Path:
    return _SCENARIOS_OUT / f"{name}.usd"


def run_output_dir(output_root: Path, scenario_name: str, seed: int, rep: int) -> Path:
    return output_root / f"{scenario_name}-seed{seed}-rep{rep:03d}"
```

- [ ] **Step 4: Run — verify pass**

```bash
pytest tests/unit/test_m6_paths.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/paths.py tests/unit/test_m6_paths.py
git commit -m "feat: add M6 canonical path resolution"
```

---

### Task 4: Canonical Scenario YAMLs and Config Files

**Files:**
- Create: `isaac/config/scenarios/head_on_deadlock.yaml`
- Create: `isaac/config/scenarios/intersection_bottleneck.yaml`
- Create: `isaac/config/scenarios/dynamic_anomaly.yaml`
- Create: `isaac/config/robot.yaml`
- Create: `isaac/config/warehouse.yaml`
- Create: `isaac/config/lidar/turtlebot3_lds_01.json`
- Modify: `tests/unit/test_m6_config.py` (add round-trip tests)

- [ ] **Step 1: Write failing round-trip tests** (append to `test_m6_config.py`)

```python
# Append to tests/unit/test_m6_config.py

import yaml
from isaac.vgu_sim.config import ScenarioConfig, RobotAssetConfig, WarehouseConfig
from isaac.vgu_sim.paths import scenario_config_path
import json


def _load_scenario(name: str) -> ScenarioConfig:
    path = scenario_config_path(name)
    with open(path) as f:
        data = yaml.safe_load(f)
    return ScenarioConfig.model_validate(data)


def test_head_on_yaml_round_trip():
    cfg = _load_scenario("head_on_deadlock")
    assert cfg.name == "head_on_deadlock"
    assert len(cfg.robots) == 2
    assert cfg.robots[0].robot_id == "robot_1"
    assert cfg.robots[1].robot_id == "robot_2"
    assert cfg.expected_conflict.type == "deadlock"


def test_intersection_yaml_round_trip():
    cfg = _load_scenario("intersection_bottleneck")
    assert cfg.name == "intersection_bottleneck"
    assert len(cfg.robots) == 4
    assert cfg.expected_conflict.type == "bottleneck"


def test_dynamic_anomaly_yaml_round_trip():
    cfg = _load_scenario("dynamic_anomaly")
    assert cfg.name == "dynamic_anomaly"
    assert len(cfg.robots) == 4
    assert len(cfg.timed_obstacles) == 1
    obs = cfg.timed_obstacles[0]
    assert obs.spawn_at_sec == pytest.approx(8.0)
    assert obs.remove_at_sec == pytest.approx(20.0)
    assert cfg.expected_conflict.type == "anomaly"


def test_robot_yaml_matches_defaults():
    with open("isaac/config/robot.yaml") as f:
        data = yaml.safe_load(f)
    r = RobotAssetConfig.model_validate(data)
    assert r.wheel_radius_m == pytest.approx(0.033)


def test_lidar_json_has_required_keys():
    with open("isaac/config/lidar/turtlebot3_lds_01.json") as f:
        d = json.load(f)
    assert d["numChannels"] == 1
    assert d["horizontalFov"] == pytest.approx(360.0)
    assert d["rotationRate"] == pytest.approx(10.0)
    assert d["minRange"] == pytest.approx(0.12)
    assert d["maxRange"] == pytest.approx(3.5)
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/unit/test_m6_config.py -k "yaml or json" -v 2>&1 | head -20
```
Expected: `FileNotFoundError` for scenario YAMLs

- [ ] **Step 3: Write `head_on_deadlock.yaml`**

```yaml
# isaac/config/scenarios/head_on_deadlock.yaml
schema_version: 1
name: head_on_deadlock
seed: 42
duration_sec: 45.0

robots:
  - robot_id: robot_1
    marker_id: 1
    spawn: {x: -4.5, y: 0.0, yaw_rad: 0.0}
    goal: {x: 4.5, y: 0.0}
    initial_task: cross_narrow_aisle
  - robot_id: robot_2
    marker_id: 2
    spawn: {x: 4.5, y: 0.0, yaw_rad: 3.141592653589793}
    goal: {x: -4.5, y: 0.0}
    initial_task: cross_narrow_aisle

timed_obstacles: []

expected_conflict:
  type: deadlock
  involved_robots: [robot_1, robot_2]
  onset_window_sec: [8.0, 25.0]
  min_duration_sec: 2.0

runtime:
  physics_hz: 60
  rendering_hz: 30
```

- [ ] **Step 4: Write `intersection_bottleneck.yaml`**

Spawn one robot per cross-aisle approach, 3.0 m from origin, goals on the opposite side (spec §8.2).

```yaml
# isaac/config/scenarios/intersection_bottleneck.yaml
schema_version: 1
name: intersection_bottleneck
seed: 42
duration_sec: 60.0

robots:
  - robot_id: robot_1
    marker_id: 1
    spawn: {x: -3.0, y: 0.0, yaw_rad: 0.0}
    goal: {x: 3.0, y: 0.0}
    initial_task: cross_intersection
  - robot_id: robot_2
    marker_id: 2
    spawn: {x: 3.0, y: 0.0, yaw_rad: 3.141592653589793}
    goal: {x: -3.0, y: 0.0}
    initial_task: cross_intersection
  - robot_id: robot_3
    marker_id: 3
    spawn: {x: 0.0, y: -3.0, yaw_rad: 1.5707963267948966}
    goal: {x: 0.0, y: 3.0}
    initial_task: cross_intersection
  - robot_id: robot_4
    marker_id: 4
    spawn: {x: 0.0, y: 3.0, yaw_rad: -1.5707963267948966}
    goal: {x: 0.0, y: -3.0}
    initial_task: cross_intersection

timed_obstacles: []

expected_conflict:
  type: bottleneck
  involved_robots: [robot_1, robot_2, robot_3, robot_4]
  onset_window_sec: [5.0, 30.0]
  min_duration_sec: 2.0

runtime:
  physics_hz: 60
  rendering_hz: 30
```

- [ ] **Step 5: Write `dynamic_anomaly.yaml`**

```yaml
# isaac/config/scenarios/dynamic_anomaly.yaml
schema_version: 1
name: dynamic_anomaly
seed: 42
duration_sec: 60.0

robots:
  - robot_id: robot_1
    marker_id: 1
    spawn: {x: -3.0, y: 0.0, yaw_rad: 0.0}
    goal: {x: 3.0, y: 0.0}
    initial_task: traverse_east
  - robot_id: robot_2
    marker_id: 2
    spawn: {x: 3.0, y: 0.0, yaw_rad: 3.141592653589793}
    goal: {x: -3.0, y: 0.0}
    initial_task: traverse_west
  - robot_id: robot_3
    marker_id: 3
    spawn: {x: 0.0, y: -3.0, yaw_rad: 1.5707963267948966}
    goal: {x: 0.0, y: 3.0}
    initial_task: traverse_north
  - robot_id: robot_4
    marker_id: 4
    spawn: {x: 0.0, y: 3.0, yaw_rad: -1.5707963267948966}
    goal: {x: 0.0, y: -3.0}
    initial_task: traverse_south

timed_obstacles:
  - obstacle_id: blocker_east
    asset: dynamic_obstacle.usd
    spawn_at_sec: 8.0
    remove_at_sec: 20.0
    pose: {x: 1.5, y: 0.0, yaw_rad: 0.0}

expected_conflict:
  type: anomaly
  involved_robots: [robot_1]
  onset_window_sec: [8.0, 25.0]
  min_duration_sec: 2.0

runtime:
  physics_hz: 60
  rendering_hz: 30
```

- [ ] **Step 6: Write `robot.yaml`**

```yaml
# isaac/config/robot.yaml
asset_name: turtlebot3_burger
left_wheel_joint: wheel_left_joint
right_wheel_joint: wheel_right_joint
base_link: base_link
lidar_link: base_scan
wheel_radius_m: 0.033
wheel_separation_m: 0.160
max_linear_velocity_mps: 0.22
max_angular_velocity_radps: 2.84
wheel_drive_stiffness: 0.0
wheel_drive_damping: 1000.0
command_timeout_sec: 0.5
wheel_static_friction: 0.8
wheel_dynamic_friction: 0.6
```

- [ ] **Step 7: Write `warehouse.yaml`**

```yaml
# isaac/config/warehouse.yaml
width_m: 12.0
depth_m: 8.0
nominal_aisle_width_m: 1.2
wall_thickness_m: 0.1
wall_height_m: 1.2
```

- [ ] **Step 8: Write `lidar/turtlebot3_lds_01.json`**

Isaac Sim RTX lidar profile matching FR6.4.9 (360° FOV, 1°/step, 10 Hz, 0.12–3.5 m range).

```json
{
  "class": "sensor",
  "type": "lidar",
  "numChannels": 1,
  "numEchos": 1,
  "numRows": 1,
  "rotationRate": 10.0,
  "startAzimuthDeg": 0.0,
  "endAzimuthDeg": 360.0,
  "horizontalFov": 360.0,
  "verticalFov": 0.0,
  "horizontalResolution": 1.0,
  "depthRange": [0.12, 3.5],
  "minRange": 0.12,
  "maxRange": 3.5,
  "reportRateBaseHz": 10.0,
  "scanType": "rotary",
  "intensity": true
}
```

- [ ] **Step 9: Run — verify all pass**

```bash
pytest tests/unit/test_m6_config.py -v
```
Expected: all tests (original 12 + 5 new round-trip) PASS

- [ ] **Step 10: Commit**

```bash
git add isaac/config/ tests/unit/test_m6_config.py
git commit -m "feat: add M6 canonical scenario YAMLs and config files"
```

---

### Task 5: Event Scheduler

**Files:**
- Create: `isaac/vgu_sim/event_scheduler.py`
- Create: `tests/unit/test_m6_event_scheduler.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_m6_event_scheduler.py
import pytest
from isaac.vgu_sim.config import TimedObstacleConfig, Pose2D
from isaac.vgu_sim.event_scheduler import EventScheduler


def _make_obs(obs_id: str, spawn: float, remove: float | None) -> TimedObstacleConfig:
    return TimedObstacleConfig(
        obstacle_id=obs_id,
        asset="dynamic_obstacle.usd",
        spawn_at_sec=spawn,
        remove_at_sec=remove,
        pose=Pose2D(x=1.5, y=0.0, yaw_rad=0.0),
    )


def test_no_events_before_spawn():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    applied = sched.apply_due_events(5.0)
    assert applied == ()
    assert not sched.is_active("obs1")


def test_obstacle_activates_at_spawn_time():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    applied = sched.apply_due_events(8.0)
    assert "obs1" in applied
    assert sched.is_active("obs1")


def test_obstacle_deactivates_at_remove_time():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    sched.apply_due_events(8.0)
    applied = sched.apply_due_events(20.0)
    assert "obs1" in applied
    assert not sched.is_active("obs1")


def test_event_applied_only_once():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    sched.apply_due_events(8.0)
    applied_again = sched.apply_due_events(9.0)
    assert "obs1" not in applied_again


def test_events_sorted_by_time():
    obs_a = _make_obs("obs_a", 15.0, None)
    obs_b = _make_obs("obs_b", 5.0, None)
    sched = EventScheduler([obs_a, obs_b])
    applied = sched.apply_due_events(10.0)
    assert "obs_b" in applied
    assert "obs_a" not in applied


def test_reset_restores_inactive_state():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    sched.apply_due_events(8.0)
    assert sched.is_active("obs1")
    sched.reset()
    assert not sched.is_active("obs1")


def test_reset_allows_events_to_fire_again():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    sched.apply_due_events(8.0)
    sched.reset()
    applied = sched.apply_due_events(8.0)
    assert "obs1" in applied
    assert sched.is_active("obs1")


def test_permanent_obstacle_never_deactivates():
    sched = EventScheduler([_make_obs("obs_perm", 5.0, None)])
    sched.apply_due_events(5.0)
    applied = sched.apply_due_events(100.0)
    assert "obs_perm" not in applied
    assert sched.is_active("obs_perm")
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/unit/test_m6_event_scheduler.py -v 2>&1 | head -10
```

- [ ] **Step 3: Implement `isaac/vgu_sim/event_scheduler.py`**

```python
# isaac/vgu_sim/event_scheduler.py
from dataclasses import dataclass, field
from typing import Callable

from isaac.vgu_sim.config import TimedObstacleConfig


@dataclass(order=True)
class _Event:
    time_sec: float
    obstacle_id: str
    action: str  # "spawn" or "remove"


class EventScheduler:
    """Schedules timed obstacle activation/deactivation against simulation time.

    The scheduler is side-effect-free on its own: callers provide an optional
    callback to execute the actual USD prim activation. In host-only tests the
    callback is omitted and only state tracking is verified.
    """

    def __init__(
        self,
        obstacles: list[TimedObstacleConfig] | tuple[TimedObstacleConfig, ...],
        activate_fn: Callable[[str], None] | None = None,
        deactivate_fn: Callable[[str], None] | None = None,
    ) -> None:
        self._obstacles = list(obstacles)
        self._activate_fn = activate_fn or (lambda _: None)
        self._deactivate_fn = deactivate_fn or (lambda _: None)
        self._active: set[str] = set()
        self._applied: set[tuple[str, str]] = set()
        self._events: list[_Event] = self._build_events()

    def _build_events(self) -> list[_Event]:
        events: list[_Event] = []
        for obs in self._obstacles:
            events.append(_Event(obs.spawn_at_sec, obs.obstacle_id, "spawn"))
            if obs.remove_at_sec is not None:
                events.append(_Event(obs.remove_at_sec, obs.obstacle_id, "remove"))
        events.sort()
        return events

    def reset(self) -> None:
        """Restore all obstacles to inactive state and clear applied tracking."""
        for obs_id in list(self._active):
            self._deactivate_fn(obs_id)
        self._active.clear()
        self._applied.clear()

    def apply_due_events(self, simulation_time_sec: float) -> tuple[str, ...]:
        """Apply all events whose time <= simulation_time_sec.

        Returns the obstacle IDs of events applied this call.
        """
        applied_ids: list[str] = []
        for event in self._events:
            if event.time_sec > simulation_time_sec:
                break
            key = (event.obstacle_id, event.action)
            if key in self._applied:
                continue
            self._applied.add(key)
            if event.action == "spawn":
                self._activate_fn(event.obstacle_id)
                self._active.add(event.obstacle_id)
            else:
                self._deactivate_fn(event.obstacle_id)
                self._active.discard(event.obstacle_id)
            applied_ids.append(event.obstacle_id)
        return tuple(applied_ids)

    def is_active(self, obstacle_id: str) -> bool:
        return obstacle_id in self._active
```

- [ ] **Step 4: Run — verify pass**

```bash
pytest tests/unit/test_m6_event_scheduler.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/event_scheduler.py tests/unit/test_m6_event_scheduler.py
git commit -m "feat: add M6 timed obstacle event scheduler"
```

---

### Task 6: Conflict Oracle Pure Functions

**Files:**
- Create: `isaac/vgu_sim/oracle.py`
- Create: `tests/unit/test_m6_oracle.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_m6_oracle.py
import pytest
from isaac.vgu_sim.oracle import (
    is_stopped,
    is_slow,
    head_on_conflict_active,
    intersection_conflict_active,
    anomaly_conflict_active,
    classify_speed,
)


def test_is_stopped_below_threshold():
    assert is_stopped(0.005) is True


def test_is_stopped_at_threshold():
    assert is_stopped(0.01) is False  # strictly less than


def test_is_slow_below_threshold():
    assert is_slow(0.02) is True


def test_is_slow_at_threshold():
    assert is_slow(0.03) is False  # strictly less than


def test_classify_speed_stopped():
    assert classify_speed(0.0) == "STOPPED"


def test_classify_speed_slow():
    assert classify_speed(0.02) == "SLOW"


def test_classify_speed_moving():
    assert classify_speed(0.1) == "MOVING"


# head_on_conflict_active(positions: list[(x,y)], speeds: list[float], min_duration_sec achieved via caller)
def test_head_on_active_when_both_stopped_and_close():
    positions = [(-0.2, 0.0), (0.2, 0.0)]
    speeds = [0.005, 0.005]
    assert head_on_conflict_active(positions, speeds) is True


def test_head_on_not_active_when_too_far():
    positions = [(-1.0, 0.0), (1.0, 0.0)]
    speeds = [0.005, 0.005]
    assert head_on_conflict_active(positions, speeds) is False


def test_head_on_not_active_when_one_moving():
    positions = [(-0.2, 0.0), (0.2, 0.0)]
    speeds = [0.005, 0.15]
    assert head_on_conflict_active(positions, speeds) is False


def test_intersection_active_three_in_radius():
    # 3 robots within 1.0 m of origin, all slow
    positions = [(0.3, 0.0), (-0.3, 0.0), (0.0, 0.3), (2.0, 2.0)]
    speeds = [0.01, 0.01, 0.01, 0.15]
    assert intersection_conflict_active(positions, speeds) is True


def test_intersection_not_active_only_two_in_radius():
    positions = [(0.3, 0.0), (-0.3, 0.0), (2.0, 2.0), (2.0, -2.0)]
    speeds = [0.01, 0.01, 0.01, 0.01]
    assert intersection_conflict_active(positions, speeds) is False


def test_intersection_not_active_mean_speed_too_high():
    # 4 in radius but mean speed >= 0.03
    positions = [(0.3, 0.0), (-0.3, 0.0), (0.0, 0.3), (0.0, -0.3)]
    speeds = [0.05, 0.05, 0.05, 0.05]
    assert intersection_conflict_active(positions, speeds) is False


def test_anomaly_active_when_obstacle_present_and_robot_slow_upstream():
    # obstacle at (1.5, 0); robot at (0.5, 0) is upstream (x < 1.5) within 1.0 m
    obstacle_pose = (1.5, 0.0)
    robot_positions = [(0.5, 0.0)]
    robot_speeds = [0.01]
    assert anomaly_conflict_active(obstacle_pose, robot_positions, robot_speeds, obstacle_active=True) is True


def test_anomaly_not_active_when_obstacle_absent():
    obstacle_pose = (1.5, 0.0)
    robot_positions = [(0.5, 0.0)]
    robot_speeds = [0.01]
    assert anomaly_conflict_active(obstacle_pose, robot_positions, robot_speeds, obstacle_active=False) is False


def test_anomaly_not_active_when_robot_too_far():
    obstacle_pose = (1.5, 0.0)
    robot_positions = [(-1.0, 0.0)]
    robot_speeds = [0.01]
    assert anomaly_conflict_active(obstacle_pose, robot_positions, robot_speeds, obstacle_active=True) is False
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/unit/test_m6_oracle.py -v 2>&1 | head -10
```

- [ ] **Step 3: Implement `isaac/vgu_sim/oracle.py`**

```python
# isaac/vgu_sim/oracle.py
import math
from typing import Literal

# Thresholds from spec §9.4
_STOPPED_MPS = 0.01
_SLOW_MPS = 0.03
_HEAD_ON_DISTANCE_M = 0.8
_INTERSECTION_RADIUS_M = 1.0
_ANOMALY_UPSTREAM_M = 1.0


def is_stopped(planar_speed_mps: float) -> bool:
    return planar_speed_mps < _STOPPED_MPS


def is_slow(planar_speed_mps: float) -> bool:
    return planar_speed_mps < _SLOW_MPS


def classify_speed(
    planar_speed_mps: float,
) -> Literal["STOPPED", "SLOW", "MOVING"]:
    if is_stopped(planar_speed_mps):
        return "STOPPED"
    if is_slow(planar_speed_mps):
        return "SLOW"
    return "MOVING"


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def head_on_conflict_active(
    positions: list[tuple[float, float]],
    speeds: list[float],
) -> bool:
    """True when both involved robots are stopped and their center distance < 0.8 m."""
    if len(positions) != 2 or len(speeds) != 2:
        raise ValueError("head_on_conflict_active requires exactly 2 robots")
    both_stopped = all(is_stopped(s) for s in speeds)
    close_enough = _dist(positions[0], positions[1]) < _HEAD_ON_DISTANCE_M
    return both_stopped and close_enough


def intersection_conflict_active(
    positions: list[tuple[float, float]],
    speeds: list[float],
) -> bool:
    """True when >= 3 robots are within 1.0 m of origin and mean speed < 0.03 m/s."""
    origin = (0.0, 0.0)
    in_radius = [
        i for i, pos in enumerate(positions)
        if _dist(pos, origin) < _INTERSECTION_RADIUS_M
    ]
    if len(in_radius) < 3:
        return False
    mean_speed = sum(speeds[i] for i in in_radius) / len(in_radius)
    return is_slow(mean_speed)


def anomaly_conflict_active(
    obstacle_pose: tuple[float, float],
    robot_positions: list[tuple[float, float]],
    robot_speeds: list[float],
    *,
    obstacle_active: bool,
) -> bool:
    """True when obstacle is active and an involved robot is slow within 1.0 m upstream."""
    if not obstacle_active:
        return False
    for pos, speed in zip(robot_positions, robot_speeds):
        if _dist(pos, obstacle_pose) < _ANOMALY_UPSTREAM_M and is_slow(speed):
            return True
    return False
```

- [ ] **Step 4: Run — verify pass**

```bash
pytest tests/unit/test_m6_oracle.py -v
```
Expected: all 14 tests PASS

- [ ] **Step 5: Run full unit suite**

```bash
pytest tests/unit/ -q
```
Expected: all unit tests pass, no regressions

- [ ] **Step 6: Commit**

```bash
git add isaac/vgu_sim/oracle.py tests/unit/test_m6_oracle.py
git commit -m "feat: add M6 conflict oracle pure functions"
```

---

## Phase 1 Complete

Run the full host suite to confirm everything is green:

```bash
pytest tests/unit/ -v --tb=short
```

All tasks in Phase 1 are runnable on macOS without Isaac Sim. Phase 2 (`docs/superpowers/plans/2026-06-10-m6-phase2-isaac-sim.md`) covers robot import, USD authoring, ROS graph wiring, the runner, and simulation acceptance tests — all of which require Linux + Isaac Sim 6.0.

# M6 Acceptance Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make M6 write acceptance-grade `ground_truth.jsonl` records that can prove head-on conflict formation and collision-free execution.

**Architecture:** Add a focused runtime logger module that samples robot world poses from the Isaac stage, derives planar speeds, evaluates the existing scenario oracle, and writes JSONL records at 10 Hz. Keep Isaac runtime sampling in M6 and reuse `isaac.vgu_sim.oracle` for conflict classification so the runner stays thin.

**Tech Stack:** Python 3.10+, Isaac Sim 6.0 `pxr` APIs, ROS 2 Jazzy runtime, `pytest`.

---

## File Structure

- Create `isaac/vgu_sim/acceptance_logging.py`
  - Owns `RobotRuntimeState`, `AcceptanceRecord`, pose sampling, speed derivation, contact placeholder fields, and JSON-safe record construction.
  - Keeps no ROS dependencies.
- Modify `isaac/vgu_sim/runner.py`
  - Replace `_write_ground_truth(...)` with an `AcceptanceLogger` instance.
  - Write at 10 Hz, while physics continues at 60 Hz.
- Add `tests/unit/test_m6_acceptance_logging.py`
  - Tests record shape, head-on conflict detection from sampled state, and 10 Hz write cadence without Isaac Sim.
- Leave `isaac/vgu_sim/oracle.py` unchanged in the first slice.
  - It already contains `head_on_conflict_active(...)`, `intersection_conflict_active(...)`, and `anomaly_conflict_active(...)`.

## Scope

This plan implements the first acceptance slice for `head_on_deadlock`. It also creates the record schema so `intersection_bottleneck` and `dynamic_anomaly` can be added later without changing the JSONL contract.

Out of scope for this slice:
- Real PhysX contact impulse extraction.
- M1/M2/M5 orchestration.
- Nav2 or M4 execution.
- Full acceptance support for non-head-on scenarios.

---

### Task 1: Add Pure Acceptance Record Builder

**Files:**
- Create: `isaac/vgu_sim/acceptance_logging.py`
- Test: `tests/unit/test_m6_acceptance_logging.py`

- [x] **Step 1: Write the failing tests**

Create `tests/unit/test_m6_acceptance_logging.py`:

```python
import json

from isaac.vgu_sim.acceptance_logging import (
    AcceptanceLogger,
    RobotRuntimeState,
    build_acceptance_record,
)
from isaac.vgu_sim.config import ExpectedConflictConfig, Goal2D, RobotScenarioConfig, ScenarioConfig, ScenarioRuntimeOverrides, Pose2D


def _head_on_scenario() -> ScenarioConfig:
    return ScenarioConfig(
        schema_version=1,
        name="head_on_deadlock",
        seed=42,
        duration_sec=45.0,
        robots=(
            RobotScenarioConfig(
                robot_id="robot_1",
                marker_id=1,
                spawn=Pose2D(x=-3.0, y=0.0, yaw_rad=0.0),
                goal=Goal2D(x=3.0, y=0.0),
                initial_task="cross_narrow_aisle",
            ),
            RobotScenarioConfig(
                robot_id="robot_2",
                marker_id=2,
                spawn=Pose2D(x=3.0, y=0.0, yaw_rad=3.141592653589793),
                goal=Goal2D(x=-3.0, y=0.0),
                initial_task="cross_narrow_aisle",
            ),
        ),
        timed_obstacles=(),
        expected_conflict=ExpectedConflictConfig(
            type="deadlock",
            involved_robots=("robot_1", "robot_2"),
            onset_window_sec=(8.0, 25.0),
            min_duration_sec=2.0,
        ),
        runtime=ScenarioRuntimeOverrides(),
    )


def test_build_head_on_record_marks_conflict_active_when_robots_are_close_and_stopped():
    scenario = _head_on_scenario()
    states = {
        "robot_1": RobotRuntimeState(robot_id="robot_1", x=-0.2, y=0.0, theta=0.0, speed_mps=0.005),
        "robot_2": RobotRuntimeState(robot_id="robot_2", x=0.2, y=0.0, theta=3.14159, speed_mps=0.005),
    }

    record = build_acceptance_record(8.25, scenario, states)

    assert record["sim_time_sec"] == 8.25
    assert record["conflict_active"] is True
    assert record["conflict_type"] == "deadlock"
    assert record["involved_robots"] == ["robot_1", "robot_2"]
    assert record["min_pairwise_distance_m"] == 0.4
    assert record["robot_static_contacts"] == []
    assert record["robot_robot_contacts"] == []
    assert record["robots"]["robot_1"]["distance_to_goal_m"] == 3.2


def test_acceptance_logger_writes_jsonl_only_on_10hz_ticks(tmp_path):
    scenario = _head_on_scenario()
    path = tmp_path / "ground_truth.jsonl"
    states = {
        "robot_1": RobotRuntimeState(robot_id="robot_1", x=-0.2, y=0.0, theta=0.0, speed_mps=0.005),
        "robot_2": RobotRuntimeState(robot_id="robot_2", x=0.2, y=0.0, theta=3.14159, speed_mps=0.005),
    }

    with path.open("w", encoding="utf-8") as handle:
        logger = AcceptanceLogger(handle, scenario, log_hz=10.0)
        logger.maybe_write(0.00, states)
        logger.maybe_write(0.0167, states)
        logger.maybe_write(0.1000, states)

    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["sim_time_sec"] for r in records] == [0.0, 0.1]
```

- [x] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/unit/test_m6_acceptance_logging.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'isaac.vgu_sim.acceptance_logging'`.

- [x] **Step 3: Implement the pure record builder**

Create `isaac/vgu_sim/acceptance_logging.py`:

```python
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import TextIO

from isaac.vgu_sim.config import ScenarioConfig
from isaac.vgu_sim.oracle import head_on_conflict_active


@dataclass(frozen=True)
class RobotRuntimeState:
    robot_id: str
    x: float
    y: float
    theta: float
    speed_mps: float


def _round4(value: float) -> float:
    return round(float(value), 4)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _min_pairwise_distance(states: dict[str, RobotRuntimeState]) -> float | None:
    robots = list(states.values())
    if len(robots) < 2:
        return None
    distances = [
        _distance((a.x, a.y), (b.x, b.y))
        for i, a in enumerate(robots)
        for b in robots[i + 1 :]
    ]
    return min(distances)


def _goal_lookup(scenario: ScenarioConfig) -> dict[str, tuple[float, float]]:
    return {robot.robot_id: (robot.goal.x, robot.goal.y) for robot in scenario.robots}


def _head_on_active(scenario: ScenarioConfig, states: dict[str, RobotRuntimeState]) -> bool:
    involved = list(scenario.expected_conflict.involved_robots)
    if len(involved) != 2 or any(robot_id not in states for robot_id in involved):
        return False
    positions = [(states[robot_id].x, states[robot_id].y) for robot_id in involved]
    speeds = [states[robot_id].speed_mps for robot_id in involved]
    return head_on_conflict_active(positions, speeds)


def build_acceptance_record(
    sim_time_sec: float,
    scenario: ScenarioConfig,
    states: dict[str, RobotRuntimeState],
) -> dict[str, object]:
    goals = _goal_lookup(scenario)
    robots: dict[str, dict[str, float]] = {}
    for robot_id in sorted(states):
        state = states[robot_id]
        goal = goals.get(robot_id)
        distance_to_goal = None
        if goal is not None:
            distance_to_goal = _distance((state.x, state.y), goal)
        robots[robot_id] = {
            "x": _round4(state.x),
            "y": _round4(state.y),
            "theta": _round4(state.theta),
            "speed_mps": _round4(state.speed_mps),
            "goal_x": _round4(goal[0]) if goal is not None else None,
            "goal_y": _round4(goal[1]) if goal is not None else None,
            "distance_to_goal_m": _round4(distance_to_goal) if distance_to_goal is not None else None,
        }

    conflict_active = False
    if scenario.name == "head_on_deadlock":
        conflict_active = _head_on_active(scenario, states)

    min_distance = _min_pairwise_distance(states)
    return {
        "sim_time_sec": _round4(sim_time_sec),
        "robots": robots,
        "conflict_active": conflict_active,
        "conflict_type": scenario.expected_conflict.type,
        "involved_robots": list(scenario.expected_conflict.involved_robots),
        "min_pairwise_distance_m": _round4(min_distance) if min_distance is not None else None,
        "robot_static_contacts": [],
        "robot_robot_contacts": [],
    }


class AcceptanceLogger:
    def __init__(self, file: TextIO, scenario: ScenarioConfig, log_hz: float = 10.0) -> None:
        self._file = file
        self._scenario = scenario
        self._period_sec = 1.0 / log_hz
        self._next_log_sec = 0.0

    def maybe_write(self, sim_time_sec: float, states: dict[str, RobotRuntimeState]) -> None:
        if sim_time_sec + 1e-9 < self._next_log_sec:
            return
        record = build_acceptance_record(sim_time_sec, self._scenario, states)
        self._file.write(json.dumps(record, sort_keys=True) + "\n")
        self._next_log_sec += self._period_sec
```

- [x] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest tests/unit/test_m6_acceptance_logging.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/acceptance_logging.py tests/unit/test_m6_acceptance_logging.py
git commit -m "feat: add M6 acceptance record builder"
```

---

### Task 2: Add Isaac Stage Sampling

**Files:**
- Modify: `isaac/vgu_sim/acceptance_logging.py`
- Test: `tests/unit/test_m6_acceptance_logging.py`

- [x] **Step 1: Write the failing tests**

Append to `tests/unit/test_m6_acceptance_logging.py`:

```python
from isaac.vgu_sim.acceptance_logging import RobotPoseTracker


def test_pose_tracker_computes_speed_from_previous_sample():
    tracker = RobotPoseTracker()
    first = tracker.update_from_positions(
        sim_time_sec=1.0,
        positions={"robot_1": (0.0, 0.0, 0.0)},
    )
    second = tracker.update_from_positions(
        sim_time_sec=1.5,
        positions={"robot_1": (0.1, 0.0, 0.0)},
    )

    assert first["robot_1"].speed_mps == 0.0
    assert second["robot_1"].speed_mps == 0.2
```

- [x] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/unit/test_m6_acceptance_logging.py::test_pose_tracker_computes_speed_from_previous_sample -q
```

Expected: fail with `ImportError` for `RobotPoseTracker`.

- [x] **Step 3: Implement `RobotPoseTracker` and Isaac sampler**

Modify `isaac/vgu_sim/acceptance_logging.py`:

```python
class RobotPoseTracker:
    def __init__(self) -> None:
        self._previous: dict[str, tuple[float, float, float]] = {}

    def update_from_positions(
        self,
        sim_time_sec: float,
        positions: dict[str, tuple[float, float, float]],
    ) -> dict[str, RobotRuntimeState]:
        states: dict[str, RobotRuntimeState] = {}
        for robot_id, (x, y, theta) in positions.items():
            speed = 0.0
            prev = self._previous.get(robot_id)
            if prev is not None:
                prev_time, prev_x, prev_y = prev
                dt = sim_time_sec - prev_time
                if dt > 0.0:
                    speed = _distance((x, y), (prev_x, prev_y)) / dt
            states[robot_id] = RobotRuntimeState(
                robot_id=robot_id,
                x=x,
                y=y,
                theta=theta,
                speed_mps=speed,
            )
            self._previous[robot_id] = (sim_time_sec, x, y)
        return states


def sample_robot_positions(stage, robot_ids: list[str]) -> dict[str, tuple[float, float, float]]:
    from pxr import UsdGeom

    positions: dict[str, tuple[float, float, float]] = {}
    for robot_id in robot_ids:
        prim = stage.GetPrimAtPath(f"/World/Robots/{robot_id}")
        if not prim or not prim.IsValid():
            continue
        matrix = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0.0)
        translation = matrix.ExtractTranslation()
        rotation = matrix.ExtractRotation()
        yaw_rad = math.radians(rotation.Decompose((0, 0, 1), (0, 1, 0), (1, 0, 0))[0])
        positions[robot_id] = (float(translation[0]), float(translation[1]), yaw_rad)
    return positions
```

- [x] **Step 4: Run the tests**

Run:

```bash
pytest tests/unit/test_m6_acceptance_logging.py -q
```

Expected: all tests in the file pass.

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/acceptance_logging.py tests/unit/test_m6_acceptance_logging.py
git commit -m "feat: sample M6 robot runtime poses"
```

---

### Task 3: Wire Acceptance Logger Into Runner

**Files:**
- Modify: `isaac/vgu_sim/runner.py`
- Test: `tests/unit/test_m6_acceptance_logging.py`

- [x] **Step 1: Write the failing unit test for runner helper**

Append to `tests/unit/test_m6_acceptance_logging.py`:

```python
from isaac.vgu_sim.runner import _should_sample_acceptance_log


def test_should_sample_acceptance_log_at_10hz_with_60hz_physics():
    assert _should_sample_acceptance_log(step=0, physics_hz=60, log_hz=10) is True
    assert _should_sample_acceptance_log(step=1, physics_hz=60, log_hz=10) is False
    assert _should_sample_acceptance_log(step=5, physics_hz=60, log_hz=10) is False
    assert _should_sample_acceptance_log(step=6, physics_hz=60, log_hz=10) is True
```

- [x] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/unit/test_m6_acceptance_logging.py::test_should_sample_acceptance_log_at_10hz_with_60hz_physics -q
```

Expected: fail with import error for `_should_sample_acceptance_log`.

- [x] **Step 3: Add runner helper and replace ground-truth write path**

Modify `isaac/vgu_sim/runner.py` imports:

```python
from isaac.vgu_sim.acceptance_logging import (
    AcceptanceLogger,
    RobotPoseTracker,
    sample_robot_positions,
)
```

Add helper near `_TopicTimeoutError`:

```python
def _should_sample_acceptance_log(step: int, physics_hz: int, log_hz: int) -> bool:
    interval = max(1, physics_hz // log_hz)
    return step % interval == 0
```

Replace the loop body in `run_repetition(...)`:

```python
        physics_dt = 1.0 / 60.0
        duration = config.scenario.runtime.duration_sec or config.scenario.duration_sec
        robot_ids = [robot.robot_id for robot in config.scenario.robots]
        pose_tracker = RobotPoseTracker()

        step = 0
        sim_time = 0.0
        import omni.usd
        stage = omni.usd.get_context().get_stage()
        with open(gt_path, "w", encoding="utf-8") as gt_file:
            logger = AcceptanceLogger(gt_file, config.scenario, log_hz=10.0)
            while sim_time < duration and app.is_running():
                app.update()
                scheduler.apply_due_events(sim_time)
                if _should_sample_acceptance_log(step, physics_hz=60, log_hz=10):
                    positions = sample_robot_positions(stage, robot_ids)
                    states = pose_tracker.update_from_positions(sim_time, positions)
                    logger.maybe_write(sim_time, states)
                sim_time += physics_dt
                step += 1
```

Delete `_write_ground_truth(...)` because the runner no longer uses it.

- [x] **Step 4: Run the focused tests**

Run:

```bash
pytest tests/unit/test_m6_acceptance_logging.py -q
```

Expected: all tests in the file pass.

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/runner.py tests/unit/test_m6_acceptance_logging.py
git commit -m "feat: write M6 acceptance logs from runner"
```

---

### Task 4: Align Existing Simulation Acceptance Test With 10 Hz Records

**Files:**
- Modify: `tests/simulation/test_m6_scenarios.py`

- [x] **Step 1: Write the failing assertion update**

Modify `_assert_conflict_formed(...)` in `tests/simulation/test_m6_scenarios.py`:

```python
def _assert_conflict_formed(gt_path: Path, min_duration_sec: float) -> None:
    records = [json.loads(line) for line in gt_path.read_text().splitlines() if line.strip()]
    consecutive = 0.0
    previous_time: float | None = None
    for rec in records:
        current_time = float(rec["sim_time_sec"])
        if previous_time is None:
            dt = 0.0
        else:
            dt = current_time - previous_time
        previous_time = current_time
        if rec.get("conflict_active", False):
            consecutive += dt
            if consecutive >= min_duration_sec:
                return
        else:
            consecutive = 0.0
    pytest.fail(f"Conflict never active for {min_duration_sec}s in {gt_path}")
```

- [x] **Step 2: Run static unit tests**

Run:

```bash
pytest tests/unit/test_m6_acceptance_logging.py -q
```

Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add tests/simulation/test_m6_scenarios.py
git commit -m "test: measure M6 conflict duration from JSONL timestamps"
```

---

### Task 5: Isaac Runtime Verification

**Files:**
- No source changes unless verification exposes a defect.

- [ ] **Step 1: Build/regenerate assets on the Isaac Sim machine**

Run on Windows PowerShell from repo root:

```powershell
& "$env:ISAAC_SIM_ROOT\python.bat" -m isaac.scripts.import_turtlebot3 `
  --urdf isaac\assets\robots\turtlebot3_burger\turtlebot3_burger.urdf `
  --output-dir isaac\assets\robots `
  --force

& "$env:ISAAC_SIM_ROOT\python.bat" -m isaac.scripts.build_warehouse

& "$env:ISAAC_SIM_ROOT\python.bat" -m isaac.scripts.build_scenario `
  --config isaac\config\scenarios\head_on_deadlock.yaml
```

Expected files:

```text
isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.usda
isaac/assets/warehouse/warehouse_base.usd
isaac/scenarios/head_on_deadlock.usd
```

- [ ] **Step 2: Run head-on scenario**

Run:

```powershell
& "$env:ISAAC_SIM_ROOT\python.bat" -m isaac.scripts.run_simulation `
  --scenario head_on_deadlock `
  --seed 42 `
  --headless `
  --topic-timeout-sec 30
```

Expected: `All 1 repetition(s) completed successfully.`

- [ ] **Step 3: Inspect JSONL fields**

Run:

```powershell
Get-Content data\logs\simulation\head_on_deadlock-seed42-rep000\ground_truth.jsonl -TotalCount 3
```

Expected: each line contains `sim_time_sec`, `robots`, `conflict_active`, `conflict_type`, `involved_robots`, `min_pairwise_distance_m`, `robot_static_contacts`, and `robot_robot_contacts`.

- [ ] **Step 4: Run simulation acceptance test in Isaac environment**

Run:

```powershell
& "$env:ISAAC_SIM_ROOT\python.bat" -m pytest tests\simulation\test_m6_scenarios.py::test_head_on_conflict_forms_and_collision_free -q
```

Expected: pass if the stop stub and ROS 2 Jazzy bridge are active and the generated stage is valid.

---

## Self-Review

**Spec coverage:** This plan covers the missing fields currently expected by `tests/simulation/test_m6_scenarios.py`: `conflict_active` and `robot_static_contacts`. It also adds robot pose, speed, goal distance, involved robots, conflict type, pairwise distance, and robot-robot contact placeholders for forward compatibility.

**Known gap:** Real PhysX contact extraction remains out of scope for this first slice. The JSON contract includes contact arrays, but this plan initializes them empty. That is acceptable only for the current head-on smoke acceptance test; a later plan should add real contact sampling or a geometric collision oracle.

**Type consistency:** `RobotRuntimeState`, `AcceptanceLogger`, `RobotPoseTracker`, `sample_robot_positions`, and `_should_sample_acceptance_log` are defined before use. The plan uses existing `ScenarioConfig` and `oracle.head_on_conflict_active`.

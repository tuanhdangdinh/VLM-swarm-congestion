# M5 Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the M5 orchestrator — a ROS2 node and its pure-logic core that detects sustained robot stalls, runs the M2→M3 reasoning pipeline in-process on a background thread, fans the grounded command out to M4, tracks command lifecycle, and owns the coordination-task registry published to M1.

**Architecture:** All decision logic lives in pure, `rclpy`-free modules (`models`, `congestion_detector`, `state_machine`, `command_lifecycle`, `task_registry`, `reasoning_pipeline`) that are unit-tested on macOS without a ROS2 install. A thin `orchestrator_node` wires those modules to ROS2 topics/services and a `ThreadPoolExecutor`, so reasoning never blocks the spin thread. M5 invokes M2/M3 by direct Python import behind a `ReasoningPipeline` Protocol (the approved deviation from the `/reasoning/analyze` action), so it can be built and tested against a mock before M3 lands.

**Tech Stack:** Python 3.10, Pydantic v2, `rclpy` (node only), `reasoning.vlm` / `reasoning.rag` (in-process), `opencv-contrib-python` + `cv_bridge` (frame dump), `pytest`, `PyYAML` (config).

**Spec:** `docs/specs/module5_orchestrator.md` (re-read before starting; it was edited 2026-06-12).

---

## File Structure

Pure-logic modules (no `rclpy`, unit-tested offline):

- `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` — all Pydantic contracts (§4) + `TerminalStage` enum + `parse_scene_snapshot` + `load_config`.
- `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/congestion_detector.py` — `CongestionDetector` (extends the existing `is_congested` helper).
- `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py` — existing `CommandState` enum + `CommandTracker` + `CooldownTracker`.
- `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/task_registry.py` — `TaskRegistry` (base assignment + override + effective + JSON).
- `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/state_machine.py` — `OrchestratorState` enum, `Directive`, `OrchestratorStateMachine`.
- `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` — `ReasoningPipeline` Protocol, `InProcessPipeline`, `dump_frame_png`, `build_reasoner_request`, `fan_out_command`.

ROS2 glue (integration-tested, guarded by `importorskip("rclpy")`):

- `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` — thin node.
- `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/__init__.py` — public re-exports.
- `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml` — config (rewritten to §4 schema).
- `ros2_ws/src/swarm_orchestrator/launch/orchestrator.launch.py` — launch with `config_file` arg.
- `ros2_ws/src/swarm_orchestrator/package.xml` — add `std_msgs`, `sensor_msgs`, `cv_bridge`.

Tests:

- `tests/unit/test_m5_models.py`, `test_m5_congestion_detector.py`, `test_m5_command_lifecycle.py`, `test_m5_task_registry.py`, `test_m5_state_machine.py`, `test_m5_reasoning_pipeline.py`
- `tests/integration/test_m5_node.py` (marked `ros2`)

---

## Task 0: Test plumbing & dependencies

**Files:**
- Modify: `pyproject.toml` (pytest `pythonpath`, `markers`)
- Modify: `ros2_ws/src/swarm_orchestrator/package.xml`

- [ ] **Step 1: Add the orchestrator package to the pytest import path and register the `ros2` marker**

In `pyproject.toml`, under `[tool.pytest.ini_options]`, change the `pythonpath` line and add `markers`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = [".", "ros2_ws/src/swarm_perception", "ros2_ws/src/swarm_orchestrator"]
markers = [
    "ros2: integration tests that require a sourced ROS2 environment (deselect with -m 'not ros2')",
]
```

- [ ] **Step 2: Verify the orchestrator package is importable under pytest**

Run: `python -c "import sys; sys.path.insert(0, 'ros2_ws/src/swarm_orchestrator'); import swarm_orchestrator.command_lifecycle as c; print(c.CommandState.PENDING)"`
Expected: prints `CommandState.PENDING`

- [ ] **Step 3: Declare new ROS2 dependencies in package.xml**

Replace the `<depend>` block in `ros2_ws/src/swarm_orchestrator/package.xml`:

```xml
  <buildtool_depend>ament_python</buildtool_depend>
  <depend>rclpy</depend>
  <depend>std_msgs</depend>
  <depend>sensor_msgs</depend>
  <depend>cv_bridge</depend>
  <depend>swarm_interfaces</depend>
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml ros2_ws/src/swarm_orchestrator/package.xml
git commit -m "chore: wire M5 test path, ros2 marker, and package deps"
```

---

## Task 1: Data models (`models.py`)

**Files:**
- Create: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py`
- Test: `tests/unit/test_m5_models.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for M5 orchestrator Pydantic contracts and parsing helpers."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import (
    CongestionEvent,
    OrchestratorConfig,
    PipelineOutcome,
    SceneSnapshot,
    TaskAssignment,
    TerminalStage,
    load_config,
    parse_scene_snapshot,
)
from reasoning.vlm.models import ReasonerDiagnostics, ReasonerResult


def test_task_assignment_holds_task_and_goal():
    a = TaskAssignment(task="pick_a", goal=(3.0, 1.5))
    assert a.task == "pick_a"
    assert a.goal == (3.0, 1.5)


def test_congestion_event_rejects_empty_robots():
    with pytest.raises(ValidationError):
        CongestionEvent(
            involved_robots=[],
            stall_durations_sec={},
            detected_at=1.0,
            reason="x",
        )


def test_congestion_event_sorts_involved_robots():
    e = CongestionEvent(
        involved_robots=["robot_2", "robot_0"],
        stall_durations_sec={"robot_0": 12.0, "robot_2": 13.0},
        detected_at=1.0,
        reason="stall",
    )
    assert e.involved_robots == ["robot_0", "robot_2"]


def test_orchestrator_config_rejects_negative_threshold():
    with pytest.raises(ValidationError):
        OrchestratorConfig(
            stall_threshold_sec=-1.0,
            progress_epsilon_m=0.1,
            cooldown_sec=15.0,
            command_timeout_sec=20.0,
            reasoning_backend_id="mock",
            initial_tasks={"robot_0": TaskAssignment(task="t", goal=(0.0, 0.0))},
            frame_dump_dir="data/logs/m5_frames",
        )


def test_load_config_parses_nested_yaml_dict_with_goal_lists():
    raw = {
        "stall_threshold_sec": 12.0,
        "progress_epsilon_m": 0.1,
        "cooldown_sec": 15.0,
        "command_timeout_sec": 20.0,
        "reasoning_backend_id": "mock",
        "frame_dump_dir": "data/logs/m5_frames",
        "initial_tasks": {
            "robot_0": {"task": "pick_a", "goal": [3.0, 1.5]},
            "robot_1": {"task": "pick_b", "goal": [4.0, 2.0]},
        },
    }
    cfg = load_config(raw)
    assert cfg.initial_tasks["robot_0"].goal == (3.0, 1.5)
    assert cfg.frame_downscale_width is None  # default


def test_load_config_raises_on_missing_required_field():
    with pytest.raises(ValidationError):
        load_config({"progress_epsilon_m": 0.1})  # missing stall_threshold_sec etc.


def test_parse_scene_snapshot_extracts_robots_and_dropped_frame():
    raw = json.dumps(
        {
            "stamp": 5.0,
            "frame_id": "cam0",
            "robots": [
                {
                    "robot_id": "robot_0",
                    "x": 1.0,
                    "y": 2.0,
                    "theta": 0.0,
                    "linear_velocity": 0.0,
                    "angular_velocity": 0.0,
                    "task": "pick_a",
                    "status": "STOPPED",
                    "goal": [3.0, 1.5],
                    "stamp": 5.0,
                }
            ],
            "diagnostics": {"dropped_frame": False},
        }
    )
    snap = parse_scene_snapshot(raw)
    assert snap.stamp == 5.0
    assert snap.frame_id == "cam0"
    assert snap.dropped_frame is False
    assert snap.robots[0].robot_id == "robot_0"
    assert snap.robots[0].status == "STOPPED"


def test_parse_scene_snapshot_reads_dropped_frame_true_from_diagnostics():
    raw = json.dumps(
        {"stamp": 6.0, "frame_id": "cam0", "robots": [], "diagnostics": {"dropped_frame": True}}
    )
    snap = parse_scene_snapshot(raw)
    assert snap.dropped_frame is True
    assert snap.robots == []


def test_parse_scene_snapshot_raises_on_malformed_json():
    with pytest.raises(ValueError):
        parse_scene_snapshot("{not json")


def test_pipeline_outcome_carries_terminal_stage_enum():
    diag = ReasonerDiagnostics(
        request_id="r1", backend_id="mock", attempts=1, parse_status="failed"
    )
    result = ReasonerResult(request_id="r1", decision=None, raw_text=None, diagnostics=diag)
    outcome = PipelineOutcome(
        request_id="r1",
        reasoner_result=result,
        grounded_command=None,
        terminal_stage=TerminalStage.VLM,
        failure_reason="decision=None",
    )
    assert outcome.terminal_stage is TerminalStage.VLM
    assert outcome.grounded_command is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_m5_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'swarm_orchestrator.models'`

- [ ] **Step 3: Write the implementation**

```python
"""Pydantic contracts and parsing helpers for the M5 orchestrator (no rclpy)."""
from __future__ import annotations

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from reasoning.vlm.models import ReasonerResult


class TerminalStage(str, Enum):
    """Where a reasoning pipeline run terminated, for diagnostics."""

    VLM = "vlm"
    GROUNDING = "grounding"
    OK = "ok"


class TaskAssignment(BaseModel):
    """A robot's base mission assignment: task label plus world-frame goal."""

    model_config = ConfigDict(frozen=True)

    task: str = Field(min_length=1)
    goal: tuple[float, float]


class OrchestratorConfig(BaseModel):
    """Runtime configuration for the orchestrator, loaded from YAML at startup."""

    model_config = ConfigDict(frozen=True)

    stall_threshold_sec: float = Field(ge=0.0)
    progress_epsilon_m: float = Field(ge=0.0)
    cooldown_sec: float = Field(ge=0.0)
    command_timeout_sec: float = Field(ge=0.0)
    reasoning_backend_id: str = Field(min_length=1)
    initial_tasks: dict[str, TaskAssignment]
    frame_dump_dir: str = Field(min_length=1)
    keep_debug_frames: bool = False
    frame_scene_max_skew_sec: float = Field(default=1.0, ge=0.0)
    frame_downscale_width: int | None = Field(default=None, gt=0)

    @field_validator("initial_tasks")
    @classmethod
    def _non_empty_robot_ids(cls, v: dict[str, TaskAssignment]) -> dict[str, TaskAssignment]:
        if any(not rid for rid in v):
            raise ValueError("initial_tasks robot ids must be non-empty strings")
        return v


class RobotView(BaseModel):
    """M5's internal projection of one M1 RobotState (decoupled from swarm_perception)."""

    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    x: float
    y: float
    theta: float
    linear_velocity: float
    status: str
    stamp: float = Field(ge=0.0)


class SceneSnapshot(BaseModel):
    """M5's internal projection of one M1 SceneState JSON message."""

    model_config = ConfigDict(frozen=True)

    stamp: float = Field(ge=0.0)
    frame_id: str = Field(min_length=1)
    robots: list[RobotView]
    dropped_frame: bool = False


class CongestionEvent(BaseModel):
    """A detected sustained-stall event handed to the state machine."""

    model_config = ConfigDict(frozen=True)

    involved_robots: list[str] = Field(min_length=1)
    stall_durations_sec: dict[str, float]
    detected_at: float
    reason: str

    @field_validator("involved_robots")
    @classmethod
    def _sorted_unique(cls, v: list[str]) -> list[str]:
        return sorted(set(v))


class PipelineOutcome(BaseModel):
    """Result of one M2->M3 reasoning pipeline run."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1)
    reasoner_result: ReasonerResult
    grounded_command: dict[str, Any] | None
    terminal_stage: TerminalStage
    failure_reason: str | None = None


def parse_scene_snapshot(raw: str) -> SceneSnapshot:
    """Parse an M1 SceneState JSON string into M5's internal SceneSnapshot.

    Args:
        raw: JSON string published on `/perception/scene_state`.

    Returns:
        The projected snapshot. `dropped_frame` is read from `diagnostics`.

    Raises:
        ValueError: If the payload is not valid JSON or fails schema projection.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed SceneState JSON: {exc}") from exc
    diagnostics = data.get("diagnostics", {}) or {}
    robots = [
        RobotView(
            robot_id=r["robot_id"],
            x=r["x"],
            y=r["y"],
            theta=r["theta"],
            linear_velocity=r["linear_velocity"],
            status=r["status"],
            stamp=r["stamp"],
        )
        for r in data.get("robots", [])
    ]
    return SceneSnapshot(
        stamp=data["stamp"],
        frame_id=data["frame_id"],
        robots=robots,
        dropped_frame=bool(diagnostics.get("dropped_frame", False)),
    )


def load_config(raw: dict[str, Any]) -> OrchestratorConfig:
    """Build an OrchestratorConfig from a plain dict (e.g. parsed YAML).

    Args:
        raw: Mapping of config keys; `initial_tasks` values may use list goals.

    Returns:
        A validated, frozen config.

    Raises:
        pydantic.ValidationError: If required fields are missing or invalid.
    """
    tasks_in = raw.get("initial_tasks", {})
    initial_tasks = {
        rid: TaskAssignment(task=spec["task"], goal=tuple(spec["goal"]))
        for rid, spec in tasks_in.items()
    }
    merged = {**raw, "initial_tasks": initial_tasks}
    return OrchestratorConfig(**merged)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_m5_models.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py tests/unit/test_m5_models.py
git commit -m "feat: add M5 orchestrator data models and parsing helpers"
```

---

## Task 2: Congestion detector (`congestion_detector.py`)

**Files:**
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/congestion_detector.py`
- Test: `tests/unit/test_m5_congestion_detector.py`

The detector measures distance to each robot's **effective** goal (override if active, base otherwise). To stay decoupled, `update` takes a `goal_of: Callable[[str], tuple[float, float] | None]` supplied by the node from the registry, rather than importing `TaskRegistry` (avoids a circular dependency and keeps the unit test trivial).

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the M5 progress-based congestion detector."""
from __future__ import annotations

from swarm_orchestrator.congestion_detector import CongestionDetector
from swarm_orchestrator.models import OrchestratorConfig, RobotView, SceneSnapshot, TaskAssignment


def _config(**overrides) -> OrchestratorConfig:
    base = dict(
        stall_threshold_sec=10.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={"robot_0": TaskAssignment(task="t", goal=(0.0, 0.0))},
        frame_dump_dir="data/logs/m5_frames",
    )
    base.update(overrides)
    return OrchestratorConfig(**base)


def _snapshot(robots, stamp=0.0, dropped=False) -> SceneSnapshot:
    return SceneSnapshot(stamp=stamp, frame_id="cam0", robots=robots, dropped_frame=dropped)


def _robot(rid, x, y, status="STOPPED", stamp=0.0) -> RobotView:
    return RobotView(
        robot_id=rid, x=x, y=y, theta=0.0, linear_velocity=0.0, status=status, stamp=stamp
    )


_GOALS = {"robot_0": (10.0, 0.0)}


def goal_of(rid):
    return _GOALS.get(rid)


def test_no_event_before_threshold_elapses():
    det = CongestionDetector(_config())
    assert det.update(_snapshot([_robot("robot_0", 5.0, 0.0)], stamp=0.0), goal_of, now=0.0) is None
    assert det.update(_snapshot([_robot("robot_0", 5.0, 0.0)], stamp=9.0), goal_of, now=9.0) is None


def test_event_emitted_after_stall_threshold():
    det = CongestionDetector(_config())
    det.update(_snapshot([_robot("robot_0", 5.0, 0.0)]), goal_of, now=0.0)
    event = det.update(_snapshot([_robot("robot_0", 5.0, 0.0)], stamp=11.0), goal_of, now=11.0)
    assert event is not None
    assert event.involved_robots == ["robot_0"]
    assert event.stall_durations_sec["robot_0"] >= 10.0


def test_progress_resets_stall_timer():
    det = CongestionDetector(_config())
    det.update(_snapshot([_robot("robot_0", 5.0, 0.0)]), goal_of, now=0.0)
    # Robot moved 1m closer at t=8 -> progress, timer resets.
    assert det.update(_snapshot([_robot("robot_0", 6.0, 0.0)], stamp=8.0), goal_of, now=8.0) is None
    # Only 5s of no-progress since reset.
    assert det.update(_snapshot([_robot("robot_0", 6.0, 0.0)], stamp=13.0), goal_of, now=13.0) is None


def test_stale_robot_never_triggers():
    det = CongestionDetector(_config())
    det.update(_snapshot([_robot("robot_0", 5.0, 0.0, status="STALE")]), goal_of, now=0.0)
    assert det.update(
        _snapshot([_robot("robot_0", 5.0, 0.0, status="STALE")], stamp=20.0), goal_of, now=20.0
    ) is None


def test_robot_without_goal_never_triggers():
    det = CongestionDetector(_config())
    det.update(_snapshot([_robot("robot_9", 5.0, 0.0)]), goal_of, now=0.0)  # no goal mapping
    assert det.update(_snapshot([_robot("robot_9", 5.0, 0.0)], stamp=20.0), goal_of, now=20.0) is None


def test_dropped_frame_holds_timers():
    det = CongestionDetector(_config())
    det.update(_snapshot([_robot("robot_0", 5.0, 0.0)]), goal_of, now=0.0)
    # A dropped frame at t=20 must not be read as progress nor advance/emit.
    assert det.update(_snapshot([], stamp=20.0, dropped=True), goal_of, now=20.0) is None
    # Real frame at t=11 (clock continued) still stalled -> fires.
    event = det.update(_snapshot([_robot("robot_0", 5.0, 0.0)], stamp=11.0), goal_of, now=11.0)
    assert event is not None


def test_multi_robot_event_lists_all_stalled():
    goals = {"robot_0": (10.0, 0.0), "robot_1": (10.0, 0.0)}
    det = CongestionDetector(_config())
    snap0 = _snapshot([_robot("robot_0", 5.0, 0.0), _robot("robot_1", 6.0, 0.0)])
    det.update(snap0, goals.get, now=0.0)
    snap1 = _snapshot([_robot("robot_0", 5.0, 0.0), _robot("robot_1", 6.0, 0.0)], stamp=11.0)
    event = det.update(snap1, goals.get, now=11.0)
    assert event.involved_robots == ["robot_0", "robot_1"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_m5_congestion_detector.py -v`
Expected: FAIL with `ImportError: cannot import name 'CongestionDetector'`

- [ ] **Step 3: Write the implementation** (replace the whole file)

```python
"""Progress-based congestion detection for M5 (no rclpy)."""
from __future__ import annotations

import math
from collections.abc import Callable

from swarm_orchestrator.models import CongestionEvent, OrchestratorConfig, SceneSnapshot

GoalLookup = Callable[[str], tuple[float, float] | None]


def is_congested(wait_time_sec: float, threshold_sec: float) -> bool:
    """Return True when an observed wait time has reached the stall threshold."""
    return wait_time_sec >= threshold_sec


class _Progress:
    __slots__ = ("min_distance", "last_improved_at")

    def __init__(self, distance: float, now: float) -> None:
        self.min_distance = distance
        self.last_improved_at = now


class CongestionDetector:
    """Tracks per-robot distance-to-goal progress and emits stall events.

    A robot is stalled when its minimum observed distance-to-goal has not improved
    by more than `progress_epsilon_m` for at least `stall_threshold_sec`, while it
    has a goal and a non-STALE status.
    """

    def __init__(self, config: OrchestratorConfig) -> None:
        self._config = config
        self._progress: dict[str, _Progress] = {}

    def update(
        self,
        scene: SceneSnapshot,
        goal_of: GoalLookup,
        now: float,
    ) -> CongestionEvent | None:
        """Advance per-robot progress timers and emit an event on stall.

        Args:
            scene: Latest scene projection from M1.
            goal_of: Maps a robot id to its effective goal, or None if it has none.
            now: Monotonic clock in seconds.

        Returns:
            A `CongestionEvent` if one or more robots crossed the stall threshold,
            else None. On a dropped/late frame the call is a no-op (state held).
        """
        if scene.dropped_frame:
            return None

        stalled: dict[str, float] = {}
        seen: set[str] = set()
        for robot in scene.robots:
            seen.add(robot.robot_id)
            goal = goal_of(robot.robot_id)
            if goal is None or robot.status == "STALE":
                self._progress.pop(robot.robot_id, None)
                continue
            distance = math.dist((robot.x, robot.y), goal)
            state = self._progress.get(robot.robot_id)
            if state is None:
                self._progress[robot.robot_id] = _Progress(distance, now)
                continue
            if distance < state.min_distance - self._config.progress_epsilon_m:
                state.min_distance = distance
                state.last_improved_at = now
            stall = now - state.last_improved_at
            if is_congested(stall, self._config.stall_threshold_sec):
                stalled[robot.robot_id] = stall

        # Forget robots no longer present so they do not linger as stale state.
        for rid in self._progress.keys() - seen:
            self._progress.pop(rid, None)

        if not stalled:
            return None
        return CongestionEvent(
            involved_robots=sorted(stalled),
            stall_durations_sec=stalled,
            detected_at=now,
            reason=f"{len(stalled)} robot(s) stalled >= {self._config.stall_threshold_sec}s",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_m5_congestion_detector.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/swarm_orchestrator/congestion_detector.py tests/unit/test_m5_congestion_detector.py
git commit -m "feat: implement M5 progress-based congestion detector"
```

---

## Task 3: Task registry (`task_registry.py`)

**Files:**
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/task_registry.py`
- Test: `tests/unit/test_m5_task_registry.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the M5 task/status registry with coordination overrides."""
from __future__ import annotations

import json

from swarm_orchestrator.models import OrchestratorConfig, TaskAssignment
from swarm_orchestrator.task_registry import TaskRegistry


def _config() -> OrchestratorConfig:
    return OrchestratorConfig(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={
            "robot_1": TaskAssignment(task="pick_b", goal=(4.0, 2.0)),
            "robot_0": TaskAssignment(task="pick_a", goal=(3.0, 1.5)),
        },
        frame_dump_dir="data/logs/m5_frames",
    )


def test_load_initial_sets_base_assignments():
    reg = TaskRegistry()
    reg.load_initial(_config())
    assert reg.effective("robot_0") == ("pick_a", (3.0, 1.5))
    assert reg.effective("robot_1") == ("pick_b", (4.0, 2.0))


def test_effective_returns_none_for_unknown_robot():
    reg = TaskRegistry()
    assert reg.effective("ghost") is None


def test_override_changes_effective_goal_then_reverts_on_clear():
    reg = TaskRegistry()
    reg.load_initial(_config())
    reg.set_override("robot_0", action="yield", goal=(1.0, 1.0), command_id="c1")
    assert reg.effective("robot_0") == ("yield", (1.0, 1.0))
    reg.clear_override("robot_0")
    assert reg.effective("robot_0") == ("pick_a", (3.0, 1.5))


def test_to_json_is_sorted_and_carries_effective_values():
    reg = TaskRegistry()
    reg.load_initial(_config())
    reg.set_override("robot_0", action="reroute", goal=(9.0, 9.0), command_id="c1")
    payload = json.loads(reg.to_json())
    assert list(payload.keys()) == ["robot_0", "robot_1"]  # sorted
    assert payload["robot_0"]["task"] == "reroute"
    assert payload["robot_0"]["goal"] == [9.0, 9.0]
    assert payload["robot_1"]["task"] == "pick_b"


def test_to_json_is_deterministic():
    reg = TaskRegistry()
    reg.load_initial(_config())
    assert reg.to_json() == reg.to_json()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_m5_task_registry.py -v`
Expected: FAIL with `AttributeError`/`TypeError` (current `TaskRegistry` has no `load_initial`/`effective`)

- [ ] **Step 3: Write the implementation** (replace the whole file)

```python
"""Coordination task/status registry owned by M5 and published to M1 (no rclpy)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from swarm_orchestrator.models import OrchestratorConfig, TaskAssignment


@dataclass
class _Override:
    action: str
    goal: tuple[float, float]
    command_id: str


@dataclass
class _Entry:
    base: TaskAssignment
    override: _Override | None = None


@dataclass
class TaskRegistry:
    """Per-robot base assignment plus optional active coordination override.

    The published JSON always carries the *effective* task and goal: the override
    while one is active, the base assignment otherwise.
    """

    entries: dict[str, _Entry] = field(default_factory=dict)

    def load_initial(self, config: OrchestratorConfig) -> None:
        """Populate base assignments from config (called once at startup)."""
        self.entries = {rid: _Entry(base=assignment) for rid, assignment in config.initial_tasks.items()}

    def assign(self, robot_id: str, task: str, goal: tuple[float, float]) -> None:
        """Set or replace a robot's base mission assignment."""
        self.entries[robot_id] = _Entry(base=TaskAssignment(task=task, goal=goal))

    def set_override(
        self, robot_id: str, action: str, goal: tuple[float, float], command_id: str
    ) -> None:
        """Apply a coordination override for a robot (no-op if robot unknown)."""
        entry = self.entries.get(robot_id)
        if entry is None:
            return
        entry.override = _Override(action=action, goal=goal, command_id=command_id)

    def clear_override(self, robot_id: str) -> None:
        """Remove a robot's override so its effective goal reverts to the base."""
        entry = self.entries.get(robot_id)
        if entry is not None:
            entry.override = None

    def effective(self, robot_id: str) -> tuple[str, tuple[float, float]] | None:
        """Return the (task, goal) currently in effect for a robot, or None."""
        entry = self.entries.get(robot_id)
        if entry is None:
            return None
        if entry.override is not None:
            return entry.override.action, entry.override.goal
        return entry.base.task, entry.base.goal

    def to_json(self) -> str:
        """Serialize the effective registry as deterministic JSON sorted by robot id."""
        payload = {}
        for robot_id in sorted(self.entries):
            task, goal = self.effective(robot_id)  # type: ignore[misc]
            payload[robot_id] = {"task": task, "goal": [goal[0], goal[1]]}
        return json.dumps(payload, sort_keys=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_m5_task_registry.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/swarm_orchestrator/task_registry.py tests/unit/test_m5_task_registry.py
git commit -m "feat: extend M5 task registry with coordination overrides and JSON"
```

---

## Task 4: Command tracker & cooldown tracker (`command_lifecycle.py`)

**Files:**
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py`
- Test: `tests/unit/test_m5_command_lifecycle.py`

M4 publishes `CoordinationStatus.status` strings; M5 maps `"active"→ACTIVE`, `"completed"→COMPLETED`, `"failed"→FAILED`. Unknown strings are ignored (logged by the node).

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for M5 command lifecycle tracking and cooldown gating."""
from __future__ import annotations

from swarm_orchestrator.command_lifecycle import (
    CommandRecord,
    CommandState,
    CooldownTracker,
    CommandTracker,
)


def _record(command_id="c1", robots=("robot_0", "robot_1"), timeout=20.0, dispatched=0.0):
    return CommandRecord(
        command_id=command_id,
        robot_ids=list(robots),
        dispatched_at=dispatched,
        timeout_sec=timeout,
        fallback="stop_all",
        request_id="r1",
    )


def test_register_starts_all_robots_pending():
    tracker = CommandTracker()
    tracker.register(_record())
    assert tracker.state_of("c1", "robot_0") is CommandState.PENDING


def test_apply_status_advances_to_active_then_completed():
    tracker = CommandTracker()
    tracker.register(_record(robots=("robot_0",)))
    tracker.apply_status("c1", "robot_0", "active")
    assert tracker.state_of("c1", "robot_0") is CommandState.ACTIVE
    tracker.apply_status("c1", "robot_0", "completed")
    assert tracker.state_of("c1", "robot_0") is CommandState.COMPLETED


def test_unknown_status_string_is_ignored():
    tracker = CommandTracker()
    tracker.register(_record(robots=("robot_0",)))
    tracker.apply_status("c1", "robot_0", "banana")
    assert tracker.state_of("c1", "robot_0") is CommandState.PENDING


def test_command_resolved_only_when_all_robots_terminal():
    tracker = CommandTracker()
    tracker.register(_record(robots=("robot_0", "robot_1")))
    tracker.apply_status("c1", "robot_0", "completed")
    assert tracker.is_resolved("c1") is False
    tracker.apply_status("c1", "robot_1", "failed")
    assert tracker.is_resolved("c1") is True


def test_check_timeouts_marks_unresolved_command():
    tracker = CommandTracker()
    tracker.register(_record(robots=("robot_0",), timeout=20.0, dispatched=0.0))
    assert tracker.check_timeouts(now=19.0) == []
    timed_out = tracker.check_timeouts(now=21.0)
    assert timed_out == ["c1"]
    assert tracker.state_of("c1", "robot_0") is CommandState.TIMED_OUT


def test_check_timeouts_ignores_already_resolved():
    tracker = CommandTracker()
    tracker.register(_record(robots=("robot_0",), timeout=20.0))
    tracker.apply_status("c1", "robot_0", "completed")
    assert tracker.check_timeouts(now=100.0) == []


def test_cooldown_active_then_expires():
    cd = CooldownTracker(cooldown_sec=15.0)
    cd.start(["robot_0", "robot_1"], now=0.0)
    assert cd.active_robots(now=10.0) == {"robot_0", "robot_1"}
    assert cd.active_robots(now=16.0) == set()


def test_cooldown_without_command_record():
    # Pipeline-failure path: cooldown starts though no command was dispatched.
    cd = CooldownTracker(cooldown_sec=5.0)
    cd.start(["robot_2"], now=100.0)
    assert "robot_2" in cd.active_robots(now=101.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_m5_command_lifecycle.py -v`
Expected: FAIL with `ImportError: cannot import name 'CommandRecord'`

- [ ] **Step 3: Write the implementation** (replace the whole file; keep the existing `CommandState` enum verbatim)

```python
"""Command lifecycle and cooldown tracking for M5 (no rclpy)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

_TERMINAL = frozenset({"COMPLETED", "FAILED", "TIMED_OUT"})
_STATUS_MAP = {
    "active": "ACTIVE",
    "completed": "COMPLETED",
    "failed": "FAILED",
}


class CommandState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass
class CommandRecord:
    """Bookkeeping for one dispatched coordination command (multi-robot)."""

    command_id: str
    robot_ids: list[str]
    dispatched_at: float
    timeout_sec: float
    fallback: str
    request_id: str
    robot_states: dict[str, CommandState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.robot_states:
            self.robot_states = {rid: CommandState.PENDING for rid in self.robot_ids}


class CommandTracker:
    """Tracks per-robot lifecycle for dispatched commands and detects timeouts."""

    def __init__(self) -> None:
        self._records: dict[str, CommandRecord] = {}

    def register(self, record: CommandRecord) -> None:
        self._records[record.command_id] = record

    def state_of(self, command_id: str, robot_id: str) -> CommandState | None:
        record = self._records.get(command_id)
        return None if record is None else record.robot_states.get(robot_id)

    def apply_status(self, command_id: str, robot_id: str, status: str) -> None:
        """Apply an M4 status string to a robot; unknown strings are ignored."""
        record = self._records.get(command_id)
        if record is None or robot_id not in record.robot_states:
            return
        mapped = _STATUS_MAP.get(status)
        if mapped is None:
            return
        record.robot_states[robot_id] = CommandState[mapped]

    def is_resolved(self, command_id: str) -> bool:
        record = self._records.get(command_id)
        if record is None:
            return False
        return all(s.name in _TERMINAL for s in record.robot_states.values())

    def robots_of(self, command_id: str) -> list[str]:
        record = self._records.get(command_id)
        return [] if record is None else list(record.robot_ids)

    def fallback_of(self, command_id: str) -> str | None:
        record = self._records.get(command_id)
        return None if record is None else record.fallback

    def check_timeouts(self, now: float) -> list[str]:
        """Mark unresolved commands past their deadline TIMED_OUT; return their ids."""
        timed_out: list[str] = []
        for command_id, record in self._records.items():
            if self.is_resolved(command_id):
                continue
            if now - record.dispatched_at >= record.timeout_sec:
                for rid, state in record.robot_states.items():
                    if state.name not in _TERMINAL:
                        record.robot_states[rid] = CommandState.TIMED_OUT
                timed_out.append(command_id)
        return timed_out


class CooldownTracker:
    """Single owner of per-robot re-trigger cooldowns (FR5.2.2)."""

    def __init__(self, cooldown_sec: float) -> None:
        self._cooldown_sec = cooldown_sec
        self._until: dict[str, float] = {}

    def start(self, robot_ids: list[str], now: float) -> None:
        deadline = now + self._cooldown_sec
        for rid in robot_ids:
            self._until[rid] = deadline

    def active_robots(self, now: float) -> set[str]:
        return {rid for rid, until in self._until.items() if until > now}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_m5_command_lifecycle.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py tests/unit/test_m5_command_lifecycle.py
git commit -m "feat: add M5 command tracker and cooldown tracker"
```

---

## Task 5: State machine (`state_machine.py`)

**Files:**
- Create: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/state_machine.py`
- Test: `tests/unit/test_m5_state_machine.py`

The machine is a pure transition object. The node feeds it inputs and executes the returned `Directive`. It owns the current state, the active `request_id`, and per-robot consecutive-failure counts; it consults injected sets (cooldown robots, robots with an active command) for gating.

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the M5 orchestrator state machine."""
from __future__ import annotations

from swarm_orchestrator.models import (
    CongestionEvent,
    PipelineOutcome,
    TerminalStage,
)
from swarm_orchestrator.state_machine import (
    DirectiveKind,
    OrchestratorState,
    OrchestratorStateMachine,
)
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
)


def _event(robots=("robot_0",), now=11.0):
    return CongestionEvent(
        involved_robots=list(robots),
        stall_durations_sec={r: 12.0 for r in robots},
        detected_at=now,
        reason="stall",
    )


def _ok_outcome(request_id):
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_0"],
        root_cause="head-on",
        strategy="yield",
        justification="x",
    )
    diag = ReasonerDiagnostics(
        request_id=request_id, backend_id="mock", attempts=1, parse_status="valid"
    )
    result = ReasonerResult(
        request_id=request_id, decision=decision, raw_text="{}", diagnostics=diag
    )
    return PipelineOutcome(
        request_id=request_id,
        reasoner_result=result,
        grounded_command={"command_id": "c1", "actions": [{"robot_id": "robot_0", "action": "yield"}],
                          "expected_resolution_time_sec": 20.0, "fallback": "stop"},
        terminal_stage=TerminalStage.OK,
        failure_reason=None,
    )


def _failed_outcome(request_id, stage=TerminalStage.VLM):
    diag = ReasonerDiagnostics(
        request_id=request_id, backend_id="mock", attempts=2, parse_status="failed"
    )
    result = ReasonerResult(
        request_id=request_id, decision=None, raw_text=None, diagnostics=diag
    )
    return PipelineOutcome(
        request_id=request_id,
        reasoner_result=result,
        grounded_command=None,
        terminal_stage=stage,
        failure_reason="decision=None",
    )


def test_event_in_monitoring_starts_analysis_when_ungated():
    sm = OrchestratorStateMachine()
    directive = sm.on_event(_event(), cooldown_robots=set(), busy_robots=set(), now=11.0)
    assert directive.kind is DirectiveKind.START_ANALYSIS
    assert sm.state is OrchestratorState.ANALYZING
    assert directive.request_id  # generated


def test_event_suppressed_when_robot_in_cooldown():
    sm = OrchestratorStateMachine()
    directive = sm.on_event(_event(), cooldown_robots={"robot_0"}, busy_robots=set(), now=11.0)
    assert directive.kind is DirectiveKind.SUPPRESSED
    assert sm.state is OrchestratorState.MONITORING


def test_event_suppressed_when_robot_has_active_command():
    sm = OrchestratorStateMachine()
    directive = sm.on_event(_event(), cooldown_robots=set(), busy_robots={"robot_0"}, now=11.0)
    assert directive.kind is DirectiveKind.SUPPRESSED


def test_event_ignored_while_analyzing():
    sm = OrchestratorStateMachine()
    sm.on_event(_event(), cooldown_robots=set(), busy_robots=set(), now=11.0)
    directive = sm.on_event(_event(now=12.0), cooldown_robots=set(), busy_robots=set(), now=12.0)
    assert directive.kind is DirectiveKind.IGNORED
    assert sm.state is OrchestratorState.ANALYZING


def test_ok_outcome_directs_dispatch_and_returns_monitoring():
    sm = OrchestratorStateMachine()
    d = sm.on_event(_event(), cooldown_robots=set(), busy_robots=set(), now=11.0)
    directive = sm.on_outcome(_ok_outcome(d.request_id), now=13.0)
    assert directive.kind is DirectiveKind.DISPATCH
    assert sm.state is OrchestratorState.MONITORING


def test_failed_outcome_directs_cooldown_and_increments_failures():
    sm = OrchestratorStateMachine()
    d = sm.on_event(_event(), cooldown_robots=set(), busy_robots=set(), now=11.0)
    directive = sm.on_outcome(_failed_outcome(d.request_id), now=13.0)
    assert directive.kind is DirectiveKind.COOLDOWN
    assert directive.robots == ["robot_0"]
    assert sm.failure_count("robot_0") == 1
    assert sm.state is OrchestratorState.MONITORING


def test_completed_resolution_resets_failure_count():
    sm = OrchestratorStateMachine()
    d = sm.on_event(_event(), cooldown_robots=set(), busy_robots=set(), now=11.0)
    sm.on_outcome(_failed_outcome(d.request_id), now=13.0)
    assert sm.failure_count("robot_0") == 1
    sm.on_command_resolved(["robot_0"], all_completed=True)
    assert sm.failure_count("robot_0") == 0


def test_frame_unavailable_suppresses_without_analyzing():
    sm = OrchestratorStateMachine()
    directive = sm.on_event(
        _event(), cooldown_robots=set(), busy_robots=set(), now=11.0, frame_ready=False
    )
    assert directive.kind is DirectiveKind.SUPPRESSED
    assert sm.state is OrchestratorState.MONITORING
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_m5_state_machine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'swarm_orchestrator.state_machine'`

- [ ] **Step 3: Write the implementation**

```python
"""Pure transition logic for the M5 orchestrator state machine (no rclpy, no I/O)."""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from swarm_orchestrator.models import CongestionEvent, PipelineOutcome, TerminalStage


class OrchestratorState(str, Enum):
    MONITORING = "monitoring"
    ANALYZING = "analyzing"
    DISPATCHING = "dispatching"


class DirectiveKind(str, Enum):
    START_ANALYSIS = "start_analysis"
    SUPPRESSED = "suppressed"
    IGNORED = "ignored"
    DISPATCH = "dispatch"
    COOLDOWN = "cooldown"
    NONE = "none"


@dataclass(frozen=True)
class Directive:
    """An instruction returned to the node, which performs the side effects."""

    kind: DirectiveKind
    request_id: str | None = None
    robots: list[str] = field(default_factory=list)
    outcome: PipelineOutcome | None = None


class OrchestratorStateMachine:
    """Single in-flight reasoning cycle with cooldown/active-command gating."""

    def __init__(self) -> None:
        self.state = OrchestratorState.MONITORING
        self._active_request_id: str | None = None
        self._active_robots: list[str] = []
        self._failures: dict[str, int] = defaultdict(int)

    def failure_count(self, robot_id: str) -> int:
        return self._failures[robot_id]

    def on_event(
        self,
        event: CongestionEvent,
        cooldown_robots: set[str],
        busy_robots: set[str],
        now: float,
        frame_ready: bool = True,
    ) -> Directive:
        """Handle a congestion event; only MONITORING starts a new cycle."""
        if self.state is not OrchestratorState.MONITORING:
            return Directive(kind=DirectiveKind.IGNORED)
        if not frame_ready:
            return Directive(kind=DirectiveKind.SUPPRESSED, robots=event.involved_robots)
        gated = set(event.involved_robots) & (cooldown_robots | busy_robots)
        if gated:
            return Directive(kind=DirectiveKind.SUPPRESSED, robots=event.involved_robots)
        request_id = uuid.uuid4().hex
        self.state = OrchestratorState.ANALYZING
        self._active_request_id = request_id
        self._active_robots = list(event.involved_robots)
        return Directive(
            kind=DirectiveKind.START_ANALYSIS,
            request_id=request_id,
            robots=event.involved_robots,
        )

    def on_outcome(self, outcome: PipelineOutcome, now: float) -> Directive:
        """Handle a completed pipeline run; returns DISPATCH or COOLDOWN."""
        robots = self._active_robots
        if outcome.terminal_stage is TerminalStage.OK and outcome.grounded_command is not None:
            self.state = OrchestratorState.DISPATCHING
            directive = Directive(
                kind=DirectiveKind.DISPATCH,
                request_id=outcome.request_id,
                robots=robots,
                outcome=outcome,
            )
            # Node performs dispatch; cycle returns to MONITORING immediately after.
            self.state = OrchestratorState.MONITORING
            self._clear_active()
            return directive
        for rid in robots:
            self._failures[rid] += 1
        self.state = OrchestratorState.MONITORING
        self._clear_active()
        return Directive(kind=DirectiveKind.COOLDOWN, request_id=outcome.request_id, robots=robots)

    def on_command_resolved(self, robots: list[str], all_completed: bool) -> None:
        """Update failure counters when a dispatched command resolves."""
        for rid in robots:
            if all_completed:
                self._failures[rid] = 0
            else:
                self._failures[rid] += 1

    def _clear_active(self) -> None:
        self._active_request_id = None
        self._active_robots = []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_m5_state_machine.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/swarm_orchestrator/state_machine.py tests/unit/test_m5_state_machine.py
git commit -m "feat: implement M5 orchestrator state machine"
```

---

## Task 6: Reasoning pipeline, frame dump, and fan-out (`reasoning_pipeline.py`)

**Files:**
- Create: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py`
- Test: `tests/unit/test_m5_reasoning_pipeline.py`

This module holds (a) the `ReasoningPipeline` Protocol + `InProcessPipeline`, (b) `dump_frame_png` (RGB→BGR, optional downscale), (c) `build_reasoner_request` (SceneSnapshot→ReasonerRequest), and (d) `fan_out_command` (grounded dict→per-robot tuples, §9.2).

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the M5 reasoning pipeline adapter, frame dump, and fan-out."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from swarm_orchestrator.models import RobotView, SceneSnapshot, TerminalStage
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    build_reasoner_request,
    dump_frame_png,
    fan_out_command,
)
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
)


def _snapshot():
    return SceneSnapshot(
        stamp=5.0,
        frame_id="cam0",
        robots=[
            RobotView(robot_id="robot_0", x=1.0, y=2.0, theta=0.0,
                      linear_velocity=0.0, status="STOPPED", stamp=5.0)
        ],
        dropped_frame=False,
    )


# ---- build_reasoner_request ----

def test_build_reasoner_request_maps_snapshot_and_image_path():
    req = build_reasoner_request(
        request_id="r1", snapshot=_snapshot(), image_path="/tmp/r1.png"
    )
    assert req.request_id == "r1"
    assert req.image_path == "/tmp/r1.png"
    assert req.frame_id == "cam0"
    assert req.robot_states[0].robot_id == "robot_0"
    assert req.robot_states[0].status == "STOPPED"


# ---- dump_frame_png ----

def test_dump_frame_png_writes_file(tmp_path):
    frame_rgb = np.zeros((4, 6, 3), dtype=np.uint8)
    dest = tmp_path / "r1.png"
    dump_frame_png(frame_rgb, str(dest), downscale_width=None)
    assert dest.is_file()


def test_dump_frame_png_downscales_preserving_aspect(tmp_path):
    import cv2
    frame_rgb = np.zeros((100, 200, 3), dtype=np.uint8)
    dest = tmp_path / "r1.png"
    dump_frame_png(frame_rgb, str(dest), downscale_width=100)
    out = cv2.imread(str(dest))
    assert out.shape[1] == 100  # width
    assert out.shape[0] == 50   # height halved to preserve 2:1 aspect


def test_dump_frame_png_converts_rgb_to_bgr(tmp_path):
    import cv2
    frame_rgb = np.zeros((1, 1, 3), dtype=np.uint8)
    frame_rgb[0, 0] = (255, 0, 0)  # pure red in RGB
    dest = tmp_path / "r1.png"
    dump_frame_png(frame_rgb, str(dest), downscale_width=None)
    bgr = cv2.imread(str(dest))  # imread returns BGR
    assert tuple(int(c) for c in bgr[0, 0]) == (0, 0, 255)  # red stored as BGR


# ---- fan_out_command ----

def test_fan_out_produces_one_command_per_action():
    grounded = {
        "command_id": "c1",
        "actions": [
            {"robot_id": "robot_0", "action": "yield", "parameters": {"dir": "left"}},
            {"robot_id": "robot_1", "action": "wait", "parameters": {}},
        ],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop_all",
    }
    msgs = fan_out_command(grounded, fallback_timeout=20.0)
    assert len(msgs) == 2
    assert msgs[0] == ("c1", "robot_0", "yield", json.dumps({"dir": "left"}, sort_keys=True), 18.0)
    assert msgs[1][1] == "robot_1"


def test_fan_out_uses_fallback_timeout_when_resolution_zero():
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield"}],
        "expected_resolution_time_sec": 0,
        "fallback": "stop_all",
    }
    msgs = fan_out_command(grounded, fallback_timeout=20.0)
    assert msgs[0][4] == 20.0


# ---- InProcessPipeline ----

class _FakeReasoner:
    def __init__(self, result):
        self._result = result
    def run(self, request):
        return self._result


def _ok_result():
    decision = CongestionDecision(
        congestion_detected=True, type="deadlock", involved_robots=["robot_0"],
        root_cause="head-on", strategy="yield", justification="x",
    )
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)


def _no_congestion_result():
    decision = CongestionDecision(
        congestion_detected=False, type="none", involved_robots=[],
        root_cause="clear", strategy="none", justification="x",
    )
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)


def _failed_result():
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=2, parse_status="failed")
    return ReasonerResult(request_id="r1", decision=None, raw_text=None, diagnostics=diag)


def _request(image="/tmp/r1.png"):
    return build_reasoner_request(request_id="r1", snapshot=_snapshot(), image_path=image)


def test_pipeline_ok_grounds_and_returns_ok(tmp_path):
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield"}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()),
        ground_fn=lambda result: grounded,
    )
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.OK
    assert outcome.grounded_command == grounded


def test_pipeline_no_congestion_terminates_at_vlm():
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_no_congestion_result()),
        ground_fn=lambda result: pytest.fail("ground_fn must not run"),
    )
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.VLM
    assert outcome.grounded_command is None


def test_pipeline_vlm_failure_terminates_at_vlm():
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_failed_result()),
        ground_fn=lambda result: pytest.fail("ground_fn must not run"),
    )
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.VLM
    assert outcome.failure_reason is not None


def test_pipeline_grounding_failure_terminates_at_grounding():
    def _raise(result):
        raise ValueError("schema invalid")
    pipe = InProcessPipeline(reasoner=_FakeReasoner(_ok_result()), ground_fn=_raise)
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.GROUNDING
    assert "schema invalid" in outcome.failure_reason
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_m5_reasoning_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'swarm_orchestrator.reasoning_pipeline'`

- [ ] **Step 3: Write the implementation**

```python
"""M5 reasoning pipeline adapter, frame dump, request build, and fan-out (no rclpy)."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol

import cv2
import numpy as np

from swarm_orchestrator.models import (
    PipelineOutcome,
    SceneSnapshot,
    TerminalStage,
)
from reasoning.vlm.models import ReasonerRequest, ReasonerResult, RobotStateInput

GroundFn = Callable[[ReasonerResult], dict[str, Any]]


def build_reasoner_request(
    request_id: str, snapshot: SceneSnapshot, image_path: str
) -> ReasonerRequest:
    """Project a SceneSnapshot plus a dumped image path into a ReasonerRequest."""
    robot_states = [
        RobotStateInput(
            robot_id=r.robot_id,
            x=r.x,
            y=r.y,
            theta=r.theta,
            linear_velocity=r.linear_velocity,
            status=r.status,
        )
        for r in snapshot.robots
    ]
    return ReasonerRequest(
        request_id=request_id,
        image_path=image_path,
        frame_id=snapshot.frame_id,
        stamp=snapshot.stamp,
        robot_states=robot_states,
    )


def dump_frame_png(frame_rgb: np.ndarray, dest_path: str, downscale_width: int | None) -> None:
    """Write an RGB frame to disk as PNG for the VLM backend.

    The M1 boundary is RGB; OpenCV writes BGR, so we convert at this boundary
    (annotation status colors are semantic — a swapped-channel dump corrupts what
    M2 reads). Optionally downscale to `downscale_width`, preserving aspect ratio.

    Args:
        frame_rgb: RGB image array `(H, W, 3)`.
        dest_path: Destination PNG path.
        downscale_width: Target width in pixels, or None for full resolution.
    """
    image = frame_rgb
    if downscale_width is not None and image.shape[1] > downscale_width:
        scale = downscale_width / image.shape[1]
        new_size = (downscale_width, max(1, round(image.shape[0] * scale)))
        image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    cv2.imwrite(dest_path, bgr)


def fan_out_command(
    grounded: dict[str, Any], fallback_timeout: float
) -> list[tuple[str, str, str, str, float]]:
    """Expand a grounded command into per-robot (id, robot, action, params, timeout) tuples.

    Mapping per spec §9.2. `parameters` serialize with sorted keys; an absent or
    zero `expected_resolution_time_sec` falls back to `fallback_timeout`.
    """
    command_id = grounded["command_id"]
    resolution = grounded.get("expected_resolution_time_sec") or 0
    timeout = float(resolution) if resolution else fallback_timeout
    messages: list[tuple[str, str, str, str, float]] = []
    for action in grounded["actions"]:
        params_json = json.dumps(action.get("parameters", {}), sort_keys=True)
        messages.append(
            (command_id, action["robot_id"], action["action"], params_json, timeout)
        )
    return messages


class ReasoningPipeline(Protocol):
    """Backend/transport-agnostic M2->M3 pipeline."""

    def run(self, request: ReasonerRequest) -> PipelineOutcome: ...


class InProcessPipeline:
    """Default adapter: calls M2 `Reasoner.run` then M3 grounding, both in-process.

    Failures from either stage are caught and reported via `failure_reason`; they
    are never raised past this adapter (FR5.3.2, E3/E4).
    """

    def __init__(self, reasoner: Any, ground_fn: GroundFn) -> None:
        self._reasoner = reasoner
        self._ground_fn = ground_fn

    def run(self, request: ReasonerRequest) -> PipelineOutcome:
        result = self._reasoner.run(request)
        decision = result.decision
        if decision is None:
            return self._vlm_terminal(request.request_id, result, "decision=None")
        if not decision.congestion_detected:
            return self._vlm_terminal(request.request_id, result, "congestion_detected=false")
        try:
            grounded = self._ground_fn(result)
        except Exception as exc:  # grounding/schema failure — bounded here
            return PipelineOutcome(
                request_id=request.request_id,
                reasoner_result=result,
                grounded_command=None,
                terminal_stage=TerminalStage.GROUNDING,
                failure_reason=f"grounding failed: {exc}",
            )
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=result,
            grounded_command=grounded,
            terminal_stage=TerminalStage.OK,
            failure_reason=None,
        )

    @staticmethod
    def _vlm_terminal(
        request_id: str, result: ReasonerResult, reason: str
    ) -> PipelineOutcome:
        return PipelineOutcome(
            request_id=request_id,
            reasoner_result=result,
            grounded_command=None,
            terminal_stage=TerminalStage.VLM,
            failure_reason=reason,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_m5_reasoning_pipeline.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py tests/unit/test_m5_reasoning_pipeline.py
git commit -m "feat: add M5 reasoning pipeline adapter, frame dump, and fan-out"
```

---

## Task 7: ROS2 node, config, launch, and public API (`orchestrator_node.py`)

**Files:**
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py`
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/__init__.py`
- Modify: `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`
- Modify: `ros2_ws/src/swarm_orchestrator/launch/orchestrator.launch.py`
- Test: `tests/integration/test_m5_node.py` (marked `ros2`)

The node is glue: it wires the pure modules to ROS2 and a `ThreadPoolExecutor(max_workers=1)`. The reasoning logic is already tested; integration tests here are guarded by `importorskip("rclpy")` and only verify wiring (subscriptions parse, a trigger publishes commands via a mock pipeline, status updates lifecycle, registry publishes). They will skip on macOS without ROS2.

- [ ] **Step 1: Rewrite the config YAML to the §4 schema**

Replace `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`:

```yaml
# M5 orchestrator config. Loaded by orchestrator_node via the config_file param.
stall_threshold_sec: 12.0
progress_epsilon_m: 0.10
cooldown_sec: 15.0
command_timeout_sec: 20.0
reasoning_backend_id: mock
frame_dump_dir: data/logs/m5_frames
keep_debug_frames: false
frame_scene_max_skew_sec: 1.0
frame_downscale_width: null
initial_tasks:
  robot_0: { task: pick_zone_a, goal: [3.0, 1.5] }
  robot_1: { task: pick_zone_b, goal: [4.0, 2.0] }
```

- [ ] **Step 2: Write the failing integration test**

```python
"""Integration tests for the M5 orchestrator node (require a sourced ROS2 env)."""
from __future__ import annotations

import pytest

rclpy = pytest.importorskip("rclpy")

from swarm_orchestrator.models import OrchestratorConfig, TaskAssignment  # noqa: E402
from swarm_orchestrator.orchestrator_node import OrchestratorNode  # noqa: E402

pytestmark = pytest.mark.ros2


def _config(tmp_path):
    return OrchestratorConfig(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={"robot_0": TaskAssignment(task="t", goal=(10.0, 0.0))},
        frame_dump_dir=str(tmp_path),
    )


@pytest.fixture(autouse=True)
def _rclpy_lifecycle():
    rclpy.init()
    yield
    rclpy.shutdown()


def test_node_publishes_registry_on_startup(tmp_path):
    node = OrchestratorNode(config=_config(tmp_path))
    try:
        assert node.last_published_registry is not None
        assert "robot_0" in node.last_published_registry
    finally:
        node.destroy_node()


def test_scene_state_callback_does_not_crash_on_malformed_json(tmp_path):
    node = OrchestratorNode(config=_config(tmp_path))
    try:
        node._on_scene_state(_StringMsg("{not json"))  # logged + skipped, no raise
    finally:
        node.destroy_node()


class _StringMsg:
    def __init__(self, data):
        self.data = data
```

- [ ] **Step 3: Run the integration test to verify it fails (or skips cleanly)**

Run: `pytest tests/integration/test_m5_node.py -v`
Expected: SKIP if `rclpy` absent; otherwise FAIL with `ImportError`/`TypeError` (node not yet implemented).

- [ ] **Step 4: Write the node implementation** (replace the whole file)

```python
"""Thin ROS2 node wiring M5's pure logic to topics, services, and a worker thread."""
from __future__ import annotations

import json
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import rclpy
import yaml
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String

from swarm_interfaces.msg import CoordinationCommand, CoordinationStatus

from swarm_orchestrator.command_lifecycle import CommandRecord, CommandTracker, CooldownTracker
from swarm_orchestrator.congestion_detector import CongestionDetector
from swarm_orchestrator.models import (
    OrchestratorConfig,
    PipelineOutcome,
    load_config,
    parse_scene_snapshot,
)
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    ReasoningPipeline,
    build_reasoner_request,
    dump_frame_png,
    fan_out_command,
)
from swarm_orchestrator.state_machine import (
    DirectiveKind,
    OrchestratorStateMachine,
)
from swarm_orchestrator.task_registry import TaskRegistry

from reasoning.rag.command_grounder import validate_coordination_command  # noqa: F401 (live use)
from reasoning.vlm import build_backend
from reasoning.vlm.models import ReasonerConfig
from reasoning.vlm.reasoner import Reasoner


def _build_default_pipeline(config: OrchestratorConfig) -> ReasoningPipeline:
    backend = build_backend(config.reasoning_backend_id)
    reasoner = Reasoner(backend, ReasonerConfig(backend_id=config.reasoning_backend_id))

    def ground(result):
        # M3 is a stub this milestone; validate the contract dict it will return.
        raise NotImplementedError("M3 grounding not yet implemented")

    return InProcessPipeline(reasoner=reasoner, ground_fn=ground)


class OrchestratorNode(Node):
    """Layer-2 controller: detect stalls, run reasoning off-thread, dispatch to M4."""

    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        pipeline: ReasoningPipeline | None = None,
    ) -> None:
        super().__init__("orchestrator_node")
        self.declare_parameter("config_file", "")
        self._config = config or self._load_config_from_param()
        self._pipeline = pipeline or _build_default_pipeline(self._config)

        self._detector = CongestionDetector(self._config)
        self._machine = OrchestratorStateMachine()
        self._tracker = CommandTracker()
        self._cooldown = CooldownTracker(self._config.cooldown_sec)
        self._registry = TaskRegistry()
        self._registry.load_initial(self._config)

        self._bridge = CvBridge()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._future: Future[PipelineOutcome] | None = None
        self._frame_rgb = None
        self._frame_stamp: float | None = None
        self._latest_snapshot = None
        self.last_published_registry: str | None = None

        self._cmd_pub = self.create_publisher(CoordinationCommand, "/coordination/commands", 10)
        self._tasks_pub = self.create_publisher(String, "/coordination/tasks", 10)
        self.create_subscription(String, "/perception/scene_state", self._on_scene_state, 10)
        self.create_subscription(Image, "/perception/annotated_frame", self._on_frame, 10)
        self.create_subscription(
            CoordinationStatus, "/coordination/status", self._on_status, 10
        )
        self.create_timer(0.5, self._on_timer)

        Path(self._config.frame_dump_dir).mkdir(parents=True, exist_ok=True)
        self._publish_registry()

    # ---- config ----

    def _load_config_from_param(self) -> OrchestratorConfig:
        path = self.get_parameter("config_file").get_parameter_value().string_value
        if not path:
            raise ValueError("config_file parameter is required")
        with open(path) as handle:
            return load_config(yaml.safe_load(handle))

    # ---- callbacks (thin) ----

    def _on_frame(self, msg: Image) -> None:
        self._frame_rgb = self._bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")
        self._frame_stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

    def _on_scene_state(self, msg: String) -> None:
        try:
            snapshot = parse_scene_snapshot(msg.data)
        except ValueError as exc:
            self.get_logger().warning(f"skipping malformed SceneState: {exc}")
            return
        self._latest_snapshot = snapshot
        now = time.monotonic()
        event = self._detector.update(snapshot, self._effective_goal, now)
        if event is None:
            return
        frame_ready = self._frame_is_fresh(snapshot.stamp)
        directive = self._machine.on_event(
            event,
            cooldown_robots=self._cooldown.active_robots(now),
            busy_robots=self._busy_robots(),
            now=now,
            frame_ready=frame_ready,
        )
        if directive.kind is DirectiveKind.START_ANALYSIS:
            self._submit_pipeline(directive.request_id, snapshot)
        elif directive.kind is DirectiveKind.SUPPRESSED:
            self.get_logger().info(
                f"trigger suppressed robots={event.involved_robots} frame_ready={frame_ready}"
            )

    def _on_status(self, msg: CoordinationStatus) -> None:
        self._tracker.apply_status(msg.command_id, msg.robot_id, msg.status)
        if self._tracker.is_resolved(msg.command_id):
            self._resolve_command(msg.command_id)

    def _on_timer(self) -> None:
        now = time.monotonic()
        for command_id in self._tracker.check_timeouts(now):
            self.get_logger().warning(f"command {command_id} timed out")
            self._resolve_command(command_id)
        if self._future is not None and self._future.done():
            outcome = self._future.result()
            self._future = None
            self._handle_outcome(outcome, now)

    # ---- pipeline lifecycle ----

    def _submit_pipeline(self, request_id: str, snapshot) -> None:
        frame = self._frame_rgb
        downscale = self._config.frame_downscale_width
        dump_dir = self._config.frame_dump_dir

        def task() -> PipelineOutcome:
            image_path = str(Path(dump_dir) / f"{request_id}.png")
            dump_frame_png(frame, image_path, downscale)
            request = build_reasoner_request(request_id, snapshot, image_path)
            return self._pipeline.run(request)

        self._future = self._executor.submit(task)

    def _handle_outcome(self, outcome: PipelineOutcome, now: float) -> None:
        directive = self._machine.on_outcome(outcome, now)
        if directive.kind is DirectiveKind.DISPATCH and outcome.grounded_command is not None:
            self._dispatch(outcome)
        elif directive.kind is DirectiveKind.COOLDOWN:
            self._cooldown.start(directive.robots, now)
            self.get_logger().info(
                f"request={outcome.request_id} no dispatch "
                f"stage={outcome.terminal_stage.value} reason={outcome.failure_reason}"
            )
        self._cleanup_frame(outcome.request_id)

    def _dispatch(self, outcome: PipelineOutcome) -> None:
        grounded = outcome.grounded_command
        messages = fan_out_command(grounded, self._config.command_timeout_sec)
        robot_ids = [m[1] for m in messages]
        timeout = messages[0][4] if messages else self._config.command_timeout_sec
        self._tracker.register(
            CommandRecord(
                command_id=grounded["command_id"],
                robot_ids=robot_ids,
                dispatched_at=time.monotonic(),
                timeout_sec=timeout,
                fallback=grounded.get("fallback", ""),
                request_id=outcome.request_id,
            )
        )
        for command_id, robot_id, action, params_json, _timeout in messages:
            msg = CoordinationCommand()
            msg.command_id = command_id
            msg.robot_id = robot_id
            msg.action = action
            msg.parameters_json = params_json
            msg.timeout_sec = _timeout
            self._cmd_pub.publish(msg)
            self._registry.set_override(robot_id, action, self._effective_goal(robot_id) or (0.0, 0.0), command_id)
            self.get_logger().info(
                f"dispatch request={outcome.request_id} command={command_id} robot={robot_id}"
            )
        self._publish_registry()

    def _resolve_command(self, command_id: str) -> None:
        robots = self._tracker.robots_of(command_id)
        for robot_id in robots:
            self._registry.clear_override(robot_id)
        all_completed = all(
            self._tracker.state_of(command_id, r) and
            self._tracker.state_of(command_id, r).name == "COMPLETED"
            for r in robots
        )
        self._machine.on_command_resolved(robots, all_completed)
        self._cooldown.start(robots, time.monotonic())
        self._publish_registry()

    # ---- helpers ----

    def _effective_goal(self, robot_id: str):
        eff = self._registry.effective(robot_id)
        return None if eff is None else eff[1]

    def _busy_robots(self) -> set[str]:
        busy: set[str] = set()
        for command_id in list(self._tracker._records):  # node-local read
            if not self._tracker.is_resolved(command_id):
                busy.update(self._tracker.robots_of(command_id))
        return busy

    def _frame_is_fresh(self, scene_stamp: float) -> bool:
        if self._frame_rgb is None or self._frame_stamp is None:
            return False
        return abs(scene_stamp - self._frame_stamp) <= self._config.frame_scene_max_skew_sec

    def _cleanup_frame(self, request_id: str) -> None:
        if self._config.keep_debug_frames:
            return
        path = Path(self._config.frame_dump_dir) / f"{request_id}.png"
        path.unlink(missing_ok=True)

    def _publish_registry(self) -> None:
        payload = self._registry.to_json()
        self.last_published_registry = payload
        msg = String()
        msg.data = payload
        self._tasks_pub.publish(msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = OrchestratorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Re-export the public API from `__init__.py`**

Replace `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/__init__.py`:

```python
"""M5 orchestrator: congestion detection, reasoning pipeline, command lifecycle."""
from swarm_orchestrator.command_lifecycle import (
    CommandRecord,
    CommandState,
    CommandTracker,
    CooldownTracker,
)
from swarm_orchestrator.congestion_detector import CongestionDetector
from swarm_orchestrator.models import (
    CongestionEvent,
    OrchestratorConfig,
    PipelineOutcome,
    SceneSnapshot,
    TaskAssignment,
    TerminalStage,
    load_config,
    parse_scene_snapshot,
)
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    ReasoningPipeline,
    build_reasoner_request,
    dump_frame_png,
    fan_out_command,
)
from swarm_orchestrator.state_machine import (
    Directive,
    DirectiveKind,
    OrchestratorState,
    OrchestratorStateMachine,
)
from swarm_orchestrator.task_registry import TaskRegistry

__all__ = [
    "CommandRecord",
    "CommandState",
    "CommandTracker",
    "CongestionDetector",
    "CongestionEvent",
    "CooldownTracker",
    "Directive",
    "DirectiveKind",
    "InProcessPipeline",
    "OrchestratorConfig",
    "OrchestratorState",
    "OrchestratorStateMachine",
    "PipelineOutcome",
    "ReasoningPipeline",
    "SceneSnapshot",
    "TaskAssignment",
    "TaskRegistry",
    "TerminalStage",
    "build_reasoner_request",
    "dump_frame_png",
    "fan_out_command",
    "load_config",
    "parse_scene_snapshot",
]
```

Note: importing `swarm_orchestrator` (the package root) pulls no `rclpy` — the node module is *not* imported here, so unit tests stay ROS2-free.

- [ ] **Step 6: Update the launch file to pass the config file**

Replace `ros2_ws/src/swarm_orchestrator/launch/orchestrator.launch.py`:

```python
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config_file = str(
        Path(get_package_share_directory("swarm_orchestrator")) / "config" / "orchestrator.yaml"
    )
    return LaunchDescription(
        [
            Node(
                package="swarm_orchestrator",
                executable="orchestrator_node",
                output="screen",
                parameters=[{"config_file": config_file}],
            )
        ]
    )
```

- [ ] **Step 7: Run the full unit suite plus the integration test**

Run: `pytest tests/unit/ -v && pytest tests/integration/test_m5_node.py -v`
Expected: unit PASS; integration SKIP on macOS (no `rclpy`) or PASS in a sourced ROS2 env.

- [ ] **Step 8: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/ tests/integration/test_m5_node.py
git commit -m "feat: implement M5 orchestrator ROS2 node, config, and launch"
```

---

## Task 8: Full-suite verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite excluding ros2-marked tests**

Run: `pytest -m "not ros2" -v`
Expected: all M1 and M5 unit tests PASS, no errors, no collection failures.

- [ ] **Step 2: Lint the new code**

Run: `ruff check ros2_ws/src/swarm_orchestrator tests/unit/test_m5_*.py tests/integration/test_m5_node.py`
Expected: no errors. Fix any reported issues, then re-run.

- [ ] **Step 3: Confirm pure modules import no rclpy**

Run: `python -c "import sys; sys.path.insert(0, 'ros2_ws/src/swarm_orchestrator'); import swarm_orchestrator; assert 'rclpy' not in sys.modules; print('clean')"`
Expected: prints `clean` (NFR5.3).

- [ ] **Step 4: Commit any lint fixes**

```bash
git add -A
git commit -m "chore: lint fixes for M5 orchestrator"
```

---

## Self-Review (completed during planning)

**Spec coverage** — every FR maps to a task:
- FR5.1.* → Task 2 (detector; dropped-frame hold, STALE/no-goal exclusion, multi-robot, effective-goal lookup).
- FR5.2.* → Task 5 (state machine; single in-flight, gating, request_id, failure counters, frame-ready suppression).
- FR5.3.* → Task 6 (`ReasoningPipeline`/`InProcessPipeline`, `PipelineOutcome`, terminal stages) + Task 7 (background executor, frame buffer/dump).
- FR5.4.* → Task 4 (`CommandTracker`, timeout, resolution) + Task 6 (`fan_out_command`) + Task 7 (dispatch, fallback retained in `CommandRecord`).
- FR5.5.* → Task 3 (base + override, effective, deterministic JSON) + Task 7 (publish on startup/change).
- FR5.6.* → Task 7 (thin callbacks, timer, config-driven, fail-fast `load_config`).
- E1–E10 → malformed JSON (Task 7 `_on_scene_state`), dropped frame (Task 2), decision=None/no-congestion (Task 6), grounding failure (Task 6), M4 FAILED/TIMED_OUT (Task 4 + Task 7 `_resolve_command`), command timeout (Task 4), absent robot (M4 filters; dispatch still sent in Task 7), invalid config (Task 1 `load_config` raises), no-frame/stale-frame suppression (Task 5 + Task 7 `_frame_is_fresh`).
- §9.2 fan-out mapping → Task 6 tests assert the exact tuple shape and fallback-timeout rule.

**Type consistency** — `CongestionDetector.update(scene, goal_of, now)` matches its caller in Task 7; `OrchestratorStateMachine.on_event/on_outcome/on_command_resolved` signatures match Task 7 usage; `fan_out_command` returns 5-tuples consumed identically in Task 6 tests and Task 7 `_dispatch`; `PipelineOutcome`/`TerminalStage` defined in Task 1 are used unchanged in Tasks 5–7.

**Deviation from spec wording:** the spec's detector signature shows `update(scene, task_registry, now)`. The plan injects a `goal_of` callable instead of the whole `TaskRegistry` to avoid a module cycle and keep the unit test trivial — same behavior (effective-goal lookup), looser coupling. Note this when executing; if a reviewer prefers the literal signature, pass `registry.effective`-derived lookup unchanged.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-12-m5-orchestrator.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**

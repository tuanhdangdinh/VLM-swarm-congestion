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
    snap = _snapshot([_robot("robot_0", 6.0, 0.0)], stamp=13.0)
    assert det.update(snap, goal_of, now=13.0) is None


def test_stale_robot_never_triggers():
    det = CongestionDetector(_config())
    det.update(_snapshot([_robot("robot_0", 5.0, 0.0, status="STALE")]), goal_of, now=0.0)
    assert det.update(
        _snapshot([_robot("robot_0", 5.0, 0.0, status="STALE")], stamp=20.0), goal_of, now=20.0
    ) is None


def test_robot_without_goal_never_triggers():
    det = CongestionDetector(_config())
    det.update(_snapshot([_robot("robot_9", 5.0, 0.0)]), goal_of, now=0.0)  # no goal mapping
    snap = _snapshot([_robot("robot_9", 5.0, 0.0)], stamp=20.0)
    assert det.update(snap, goal_of, now=20.0) is None


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

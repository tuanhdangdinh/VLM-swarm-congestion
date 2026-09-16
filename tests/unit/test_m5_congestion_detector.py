"""Unit tests for the M5 progress-based congestion detector."""
from __future__ import annotations

from pathlib import Path

import yaml
from swarm_orchestrator.congestion_detector import CongestionDetector
from swarm_orchestrator.models import (
    OrchestratorConfig,
    RobotView,
    SceneSnapshot,
    TaskAssignment,
    load_config,
)


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


def test_close_slow_pair_triggers_even_when_goal_progress_jitters():
    goals = {"robot_0": (10.0, 0.0), "robot_1": (-10.0, 0.0)}
    det = CongestionDetector(
        _config(proximity_threshold_m=0.5, proximity_slow_speed_mps=0.05)
    )
    snap0 = _snapshot(
        [
            _robot("robot_0", 0.00, 0.00, status="STOPPED"),
            _robot("robot_1", 0.40, 0.00, status="STOPPED"),
        ]
    )
    det.update(snap0, goals.get, now=0.0)
    # Tiny pose jitter can reset/avoid the goal-progress trigger, but a close
    # slow pair held over the threshold is still a physical deadlock.
    snap1 = _snapshot(
        [
            _robot("robot_0", 0.02, 0.00, status="STOPPED"),
            _robot("robot_1", 0.38, 0.00, status="STOPPED"),
        ],
        stamp=11.0,
    )
    event = det.update(snap1, goals.get, now=11.0)
    assert event is not None
    assert event.involved_robots == ["robot_0", "robot_1"]
    assert "close/slow" in event.reason


def test_robot_within_goal_tolerance_is_not_stalled():
    # Default goal_reached_tolerance_m is 0.15; 0.1 m short of the goal is inside it.
    det = CongestionDetector(_config())
    det.update(_snapshot([_robot("robot_0", 9.9, 0.0)]), goal_of, now=0.0)
    event = det.update(
        _snapshot([_robot("robot_0", 9.9, 0.0)], stamp=20.0), goal_of, now=20.0
    )
    assert event is None


def test_robot_just_outside_goal_tolerance_can_stall():
    # 0.16 m short of the goal is just past the 0.15 m tolerance, so ordinary
    # no-progress stall detection still applies.
    det = CongestionDetector(_config(stall_threshold_sec=10.0))
    det.update(_snapshot([_robot("robot_0", 9.84, 0.0)]), goal_of, now=0.0)
    event = det.update(
        _snapshot([_robot("robot_0", 9.84, 0.0)], stamp=11.0), goal_of, now=11.0
    )
    assert event is not None
    assert event.involved_robots == ["robot_0"]


def test_arrival_clears_prior_stall_bookkeeping():
    det = CongestionDetector(_config(stall_threshold_sec=10.0))
    # Robot stalls short of the goal.
    det.update(_snapshot([_robot("robot_0", 5.0, 0.0)]), goal_of, now=0.0)
    event = det.update(_snapshot([_robot("robot_0", 5.0, 0.0)], stamp=11.0), goal_of, now=11.0)
    assert event is not None

    # Robot then reaches the goal -> arrival must clear the stall, not just pause it.
    assert det.update(
        _snapshot([_robot("robot_0", 9.95, 0.0)], stamp=12.0), goal_of, now=12.0
    ) is None

    # Robot leaves the goal again. If arrival had not cleared bookkeeping, the
    # stale last_improved_at from t=0 would make this look stalled immediately.
    det.update(_snapshot([_robot("robot_0", 9.7, 0.0)], stamp=13.0), goal_of, now=13.0)
    assert det.update(
        _snapshot([_robot("robot_0", 9.7, 0.0)], stamp=14.0), goal_of, now=14.0
    ) is None


def test_goal_reached_tolerance_loads_from_yaml():
    path = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
    cfg = load_config(yaml.safe_load(path.read_text(encoding="utf-8")))
    assert cfg.goal_reached_tolerance_m == 0.15


def test_close_pair_timer_resets_when_robots_separate():
    goals = {"robot_0": (10.0, 0.0), "robot_1": (-10.0, 0.0)}
    det = CongestionDetector(
        _config(proximity_threshold_m=0.5, proximity_slow_speed_mps=0.05)
    )
    det.update(
        _snapshot([_robot("robot_0", 0.0, 0.0), _robot("robot_1", 0.4, 0.0)]),
        goals.get,
        now=0.0,
    )
    det.update(
        _snapshot([_robot("robot_0", 0.0, 0.0), _robot("robot_1", 1.0, 0.0)], stamp=5.0),
        goals.get,
        now=5.0,
    )
    event = det.update(
        _snapshot([_robot("robot_0", 0.0, 0.0), _robot("robot_1", 0.4, 0.0)], stamp=11.0),
        goals.get,
        now=11.0,
    )
    assert event is None


def test_close_slow_pair_triggers_when_both_robots_stale():
    # Two robots close enough to occlude each other's ArUco marker go STALE
    # together (StateEstimator freezes their last-known pose/velocity rather
    # than dropping them). This is itself proximity evidence and must still
    # trigger, otherwise M5 goes blind exactly when a standoff needs it most.
    goals = {"robot_0": (10.0, 0.0), "robot_1": (-10.0, 0.0)}
    det = CongestionDetector(
        _config(proximity_threshold_m=0.5, proximity_slow_speed_mps=0.05)
    )
    snap0 = _snapshot(
        [
            _robot("robot_0", 0.00, 0.00, status="STALE"),
            _robot("robot_1", 0.40, 0.00, status="STALE"),
        ]
    )
    det.update(snap0, goals.get, now=0.0)
    snap1 = _snapshot(
        [
            _robot("robot_0", 0.00, 0.00, status="STALE"),
            _robot("robot_1", 0.40, 0.00, status="STALE"),
        ],
        stamp=11.0,
    )
    event = det.update(snap1, goals.get, now=11.0)
    assert event is not None
    assert event.involved_robots == ["robot_0", "robot_1"]
    assert "close/slow" in event.reason

"""Unit tests for M5's position-verified base-goal arrival gate (FR5.1.9)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from swarm_orchestrator.arrival import ArrivalGate, classify_arrival
from swarm_orchestrator.congestion_detector import CongestionDetector
from swarm_orchestrator.models import (
    OrchestratorConfig,
    RobotView,
    SceneSnapshot,
    TaskAssignment,
    load_config,
)

GOAL = (2.5, 0.0)


def _config(**overrides) -> OrchestratorConfig:
    base = dict(
        stall_threshold_sec=10.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={"robot_2": TaskAssignment(task="t", goal=GOAL)},
        frame_dump_dir="data/logs/m5_frames",
    )
    base.update(overrides)
    return OrchestratorConfig(**base)


def _robot(rid="robot_2", x=2.5, y=0.0, status="STOPPED", stamp=0.0) -> RobotView:
    return RobotView(
        robot_id=rid, x=x, y=y, theta=0.0, linear_velocity=0.0, status=status, stamp=stamp
    )


def _snapshot(robots, stamp=0.0, dropped=False) -> SceneSnapshot:
    return SceneSnapshot(stamp=stamp, frame_id="cam0", robots=robots, dropped_frame=dropped)


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[float, float]]] = []

    def __call__(self, robot_id: str, goal: tuple[float, float]) -> None:
        self.calls.append((robot_id, goal))


# ---- classify_arrival ----


def test_classify_arrival_accepts_when_estimate_within_tolerance():
    check = classify_arrival(GOAL, (2.3, 0.1), 0.35, 0.2, 2.0)

    assert check.accepted is True
    assert check.reason == "within_tolerance"
    assert check.distance_m == pytest.approx(0.2236, abs=1e-3)


def test_classify_arrival_rejects_when_estimate_beyond_tolerance():
    check = classify_arrival(GOAL, (1.91, 0.0), 0.35, 0.2, 2.0)

    assert check.accepted is False
    assert check.reason == "beyond_tolerance"
    assert check.distance_m == pytest.approx(0.59)


def test_classify_arrival_accepts_when_no_estimate_available():
    check = classify_arrival(GOAL, None, 0.35, None, 2.0)

    assert check.accepted is True
    assert check.reason == "no_estimate"
    assert check.distance_m is None


def test_classify_arrival_accepts_but_flags_stale_estimate():
    check = classify_arrival(GOAL, (1.91, 0.0), 0.35, 5.0, 2.0)

    assert check.accepted is True
    assert check.reason == "stale_estimate"
    assert check.distance_m == pytest.approx(0.59)


def test_classify_arrival_treats_unknown_age_as_stale():
    check = classify_arrival(GOAL, (2.5, 0.0), 0.35, None, 2.0)

    assert check.accepted is True
    assert check.reason == "stale_estimate"


def test_classify_arrival_accepts_estimate_exactly_at_tolerance():
    check = classify_arrival(GOAL, (2.25, 0.0), 0.25, 0.0, 2.0)

    assert check.accepted is True
    assert check.reason == "within_tolerance"


# ---- ArrivalGate ----


def test_gate_marks_arrived_when_estimate_corroborates():
    marked = _Recorder()
    gate = ArrivalGate(_config(), marked)

    decision = gate.on_nav2_success("robot_2", GOAL, _robot(x=2.4), 0.2)

    assert decision.check.accepted is True
    assert marked.calls == [("robot_2", GOAL)]
    assert gate.counts["accepted"] == 1


def test_gate_does_not_mark_arrived_when_estimate_beyond_tolerance():
    marked = _Recorder()
    gate = ArrivalGate(_config(), marked)

    decision = gate.on_nav2_success("robot_2", GOAL, _robot(x=1.91), 0.2)

    assert decision.check.accepted is False
    assert marked.calls == []
    assert gate.counts == {"accepted": 0, "rejected": 1, "late": 0}
    assert gate.pending_robots() == {"robot_2"}


def test_gate_treats_stale_status_estimate_as_unverified_and_accepts():
    marked = _Recorder()
    gate = ArrivalGate(_config(), marked)

    decision = gate.on_nav2_success("robot_2", GOAL, _robot(x=1.91, status="STALE"), 0.0)

    assert decision.check.reason == "stale_estimate"
    assert marked.calls == [("robot_2", GOAL)]


def test_gate_accepts_unverified_when_position_check_disabled():
    marked = _Recorder()
    gate = ArrivalGate(_config(arrival_position_check=False), marked)

    decision = gate.on_nav2_success("robot_2", GOAL, _robot(x=1.91), 0.2)

    assert decision.check is None
    assert marked.calls == [("robot_2", GOAL)]
    assert gate.pending_robots() == set()


def test_gate_accepts_late_when_robot_reaches_tolerance_on_a_later_scene():
    marked = _Recorder()
    gate = ArrivalGate(_config(), marked)
    gate.on_nav2_success("robot_2", GOAL, _robot(x=1.91), 0.2)

    decisions = gate.on_scene(_snapshot([_robot(x=2.45)]), lambda rid: GOAL)

    assert [d.robot_id for d in decisions] == ["robot_2"]
    assert decisions[0].late is True
    assert marked.calls == [("robot_2", GOAL)]
    assert gate.counts == {"accepted": 0, "rejected": 1, "late": 1}


def test_gate_accepts_late_only_once_per_rejected_arrival():
    marked = _Recorder()
    gate = ArrivalGate(_config(), marked)
    gate.on_nav2_success("robot_2", GOAL, _robot(x=1.91), 0.2)
    scene = _snapshot([_robot(x=2.45)])

    first = gate.on_scene(scene, lambda rid: GOAL)
    second = gate.on_scene(scene, lambda rid: GOAL)

    assert len(first) == 1
    assert second == []
    assert len(marked.calls) == 1
    assert gate.counts["late"] == 1


def test_gate_does_not_accept_late_while_robot_stays_beyond_tolerance():
    marked = _Recorder()
    gate = ArrivalGate(_config(), marked)
    gate.on_nav2_success("robot_2", GOAL, _robot(x=1.91), 0.2)

    assert gate.on_scene(_snapshot([_robot(x=1.95)]), lambda rid: GOAL) == []
    assert marked.calls == []
    assert gate.pending_robots() == {"robot_2"}


def test_gate_does_not_accept_late_on_a_stale_estimate_at_the_goal():
    marked = _Recorder()
    gate = ArrivalGate(_config(), marked)
    gate.on_nav2_success("robot_2", GOAL, _robot(x=1.91), 0.2)

    decisions = gate.on_scene(_snapshot([_robot(x=2.5, status="STALE")]), lambda rid: GOAL)

    assert decisions == []
    assert marked.calls == []


def test_gate_holds_pending_arrival_on_a_dropped_frame():
    marked = _Recorder()
    gate = ArrivalGate(_config(), marked)
    gate.on_nav2_success("robot_2", GOAL, _robot(x=1.91), 0.2)

    decisions = gate.on_scene(_snapshot([_robot(x=2.5)], dropped=True), lambda rid: GOAL)

    assert decisions == []
    assert gate.pending_robots() == {"robot_2"}


def test_gate_drops_pending_arrival_when_the_effective_goal_changes():
    marked = _Recorder()
    gate = ArrivalGate(_config(), marked)
    gate.on_nav2_success("robot_2", GOAL, _robot(x=1.91), 0.2)

    decisions = gate.on_scene(_snapshot([_robot(x=2.5)]), lambda rid: (-2.5, 0.0))

    assert decisions == []
    assert marked.calls == []
    assert gate.pending_robots() == set()


def test_gate_clears_pending_arrival_on_a_later_corroborated_success():
    marked = _Recorder()
    gate = ArrivalGate(_config(), marked)
    gate.on_nav2_success("robot_2", GOAL, _robot(x=1.91), 0.2)

    gate.on_nav2_success("robot_2", GOAL, _robot(x=2.45), 0.2)

    assert marked.calls == [("robot_2", GOAL)]
    assert gate.pending_robots() == set()
    assert gate.counts == {"accepted": 1, "rejected": 1, "late": 0}


def test_rejected_arrival_leaves_the_robot_stall_eligible():
    config = _config()
    detector = CongestionDetector(config)
    gate = ArrivalGate(config, detector.mark_arrived)
    # Nav2 claims success while M1 keeps the robot 0.59 m short (run 20260925_124609).
    short = _robot(x=1.91)
    gate.on_nav2_success("robot_2", GOAL, short, 0.2)

    assert detector.update(_snapshot([short]), lambda rid: GOAL, 0.0) is None
    event = detector.update(_snapshot([short], stamp=1.0), lambda rid: GOAL, 20.0)

    assert event is not None
    assert event.involved_robots == ["robot_2"]


def test_accepted_arrival_excuses_the_robot_from_stall_evidence():
    config = _config()
    detector = CongestionDetector(config)
    gate = ArrivalGate(config, detector.mark_arrived)
    parked = _robot(x=2.3)
    gate.on_nav2_success("robot_2", GOAL, parked, 0.2)

    detector.update(_snapshot([parked]), lambda rid: GOAL, 0.0)

    assert detector.update(_snapshot([parked], stamp=1.0), lambda rid: GOAL, 20.0) is None


# ---- config ----


def test_config_rejects_tolerance_above_arrived_radius():
    with pytest.raises(ValidationError, match="arrived_radius_m"):
        _config(arrival_position_tolerance_m=0.6, arrived_radius_m=0.5)


def test_config_rejects_non_positive_tolerance():
    with pytest.raises(ValidationError):
        _config(arrival_position_tolerance_m=0.0)


def test_config_rejects_non_positive_estimate_max_age():
    with pytest.raises(ValidationError):
        _config(arrival_estimate_max_age_sec=0.0)


def test_config_defaults_enable_the_position_check():
    config = _config()

    assert config.arrival_position_check is True
    assert config.arrival_position_tolerance_m == pytest.approx(0.35)
    assert config.arrival_estimate_max_age_sec == pytest.approx(2.0)


def test_shipped_orchestrator_yaml_loads_with_arrival_keys():
    path = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
    config = load_config(yaml.safe_load(path.read_text()))

    assert config.arrival_position_check is True
    assert config.arrival_position_tolerance_m == pytest.approx(0.35)
    assert config.arrival_estimate_max_age_sec == pytest.approx(2.0)
    assert config.arrival_position_tolerance_m <= config.arrived_radius_m

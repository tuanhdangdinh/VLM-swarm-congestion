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

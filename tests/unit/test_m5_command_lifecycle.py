"""Unit tests for M5 command lifecycle tracking and cooldown gating."""
from __future__ import annotations

from swarm_orchestrator.command_lifecycle import (
    CommandRecord,
    CommandState,
    CommandTracker,
    CooldownTracker,
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


def test_apply_status_accepts_uppercase_from_command_bus():
    # CommandBusNode publishes "COMPLETED" / "FAILED" (uppercase). The tracker
    # must accept these so the orchestrator resolves commands instead of timing out.
    tracker = CommandTracker()
    tracker.register(_record(robots=("robot_0", "robot_1")))
    tracker.apply_status("c1", "robot_0", "COMPLETED")
    assert tracker.state_of("c1", "robot_0") is CommandState.COMPLETED
    tracker.apply_status("c1", "robot_1", "FAILED")
    assert tracker.state_of("c1", "robot_1") is CommandState.FAILED


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


def test_check_timeouts_expires_pending_command_past_deadline():
    # No status ever arrived from M4 (lost dispatch): all robots stay PENDING.
    tracker = CommandTracker()
    tracker.register(_record(robots=("robot_0", "robot_1"), timeout=20.0, dispatched=0.0))
    timed_out = tracker.check_timeouts(now=21.0)
    assert timed_out == ["c1"]
    assert tracker.state_of("c1", "robot_0") is CommandState.TIMED_OUT
    assert tracker.state_of("c1", "robot_1") is CommandState.TIMED_OUT


def test_check_timeouts_keeps_active_command_past_deadline():
    # M4 is mid-execution (ACTIVE): liveness is delegated to M4, never expire.
    tracker = CommandTracker()
    tracker.register(_record(robots=("robot_0",), timeout=20.0, dispatched=0.0))
    tracker.apply_status("c1", "robot_0", "active")
    timed_out = tracker.check_timeouts(now=21.0)
    assert timed_out == []
    assert tracker.state_of("c1", "robot_0") is CommandState.ACTIVE


def test_check_timeouts_mixed_pending_and_active_not_expired():
    # One robot ACTIVE, one still PENDING: treat the whole command as ACTIVE.
    tracker = CommandTracker()
    tracker.register(_record(robots=("robot_0", "robot_1"), timeout=20.0, dispatched=0.0))
    tracker.apply_status("c1", "robot_0", "active")
    timed_out = tracker.check_timeouts(now=21.0)
    assert timed_out == []
    assert tracker.state_of("c1", "robot_0") is CommandState.ACTIVE
    assert tracker.state_of("c1", "robot_1") is CommandState.PENDING


def test_check_timeouts_resolved_command_not_reported():
    tracker = CommandTracker()
    tracker.register(_record(robots=("robot_0",), timeout=20.0, dispatched=0.0))
    tracker.apply_status("c1", "robot_0", "completed")
    timed_out = tracker.check_timeouts(now=100.0)
    assert timed_out == []
    assert tracker.state_of("c1", "robot_0") is CommandState.COMPLETED


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

"""Unit tests for M5 command lifecycle tracking and cooldown gating."""
from __future__ import annotations

from swarm_orchestrator.command_lifecycle import (
    AttemptMemory,
    CommandRecord,
    CommandState,
    CommandTracker,
    CooldownTracker,
    summarize_executed_strategy,
    summarize_outcome,
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


def _memory(window: float = 60.0) -> AttemptMemory:
    memory = AttemptMemory(window_sec=window)
    memory.record("c1", ["robot_1", "robot_2"], "yield", "robot_1", now=0.0)
    return memory


def test_attempt_memory_returns_none_before_resolve_without_clearing():
    memory = _memory()
    assert memory.context_for(["robot_1"], now=5.0) is None
    memory.resolve("c1", "completed", now=10.0)
    assert memory.context_for(["robot_1"], now=11.0) is not None


def test_attempt_memory_returns_record_within_window_for_overlapping_robots():
    memory = _memory()
    memory.resolve("c1", "completed", now=10.0)
    record = memory.context_for(["robot_2", "robot_3"], now=40.0)
    assert record is not None
    assert record.command_id == "c1"
    assert record.strategy == "yield"
    assert record.yield_robot == "robot_1"
    assert record.outcome_status == "completed"
    assert record.resolved_at == 10.0


def test_attempt_memory_returns_none_after_window_expires():
    memory = _memory(window=60.0)
    memory.resolve("c1", "completed", now=10.0)
    assert memory.context_for(["robot_1"], now=70.5) is None
    # expiry clears the slot; an earlier `now` cannot resurrect it
    assert memory.context_for(["robot_1"], now=20.0) is None


def test_attempt_memory_clears_on_disjoint_robot_set():
    memory = _memory()
    memory.resolve("c1", "failed", now=10.0)
    assert memory.context_for(["robot_9"], now=20.0) is None
    assert memory.context_for(["robot_1"], now=21.0) is None


def test_attempt_memory_new_record_supersedes_previous():
    memory = _memory()
    memory.resolve("c1", "failed", now=10.0)
    memory.record("c2", ["robot_1", "robot_2"], "reverse", None, now=30.0)
    assert memory.context_for(["robot_1"], now=31.0) is None
    memory.resolve("c2", "completed", now=50.0)
    record = memory.context_for(["robot_1"], now=60.0)
    assert record is not None and record.command_id == "c2"


def test_attempt_memory_resolve_ignores_superseded_command():
    memory = _memory()
    memory.record("c2", ["robot_1"], "reverse", None, now=30.0)
    memory.resolve("c1", "timed_out", now=35.0)
    assert memory.context_for(["robot_1"], now=36.0) is None


def test_attempt_memory_window_zero_disables():
    memory = _memory(window=0.0)
    memory.resolve("c1", "completed", now=10.0)
    assert memory.context_for(["robot_1"], now=11.0) is None


def test_summarize_outcome_precedence_timed_out_over_failed_over_completed():
    completed, failed, timed_out = (
        CommandState.COMPLETED,
        CommandState.FAILED,
        CommandState.TIMED_OUT,
    )
    assert summarize_outcome({"a": completed, "b": completed}) == "completed"
    assert summarize_outcome({"a": completed, "b": failed}) == "failed"
    assert summarize_outcome({"a": failed, "b": timed_out}) == "timed_out"


def test_attempt_memory_resolve_keeps_first_resolution_time():
    memory = _memory()
    memory.resolve("c1", "timed_out", now=10.0)
    memory.resolve("c1", "completed", now=14.0)
    record = memory.context_for(["robot_1"], now=20.0)
    assert record is not None
    assert record.resolved_at == 10.0
    assert record.outcome_status == "completed"


def test_attempt_memory_returns_record_again_on_second_analysis_in_window():
    memory = _memory()
    memory.resolve("c1", "completed", now=10.0)
    assert memory.context_for(["robot_1"], now=20.0) is not None
    assert memory.context_for(["robot_1"], now=30.0) is not None


def test_summarize_executed_strategy_is_the_decided_strategy_when_its_action_ran():
    assert summarize_executed_strategy(["temporary_wait", "yield"], "yield") == "yield"


def test_summarize_executed_strategy_names_a_reroute_by_its_own_action():
    # a reroute fans out as reroute + temporary_wait; that is the reroute executing, not "mixed"
    assert summarize_executed_strategy(["reroute", "temporary_wait"], "reroute") == "reroute"


def test_summarize_executed_strategy_is_the_single_action_when_degraded_uniformly():
    assert (
        summarize_executed_strategy(["temporary_wait", "temporary_wait"], "yield")
        == "temporary_wait"
    )


def test_summarize_executed_strategy_is_mixed_when_degraded_unevenly():
    assert summarize_executed_strategy(["reverse", "temporary_wait"], "yield") == "mixed"


def test_summarize_executed_strategy_is_none_without_actions():
    assert summarize_executed_strategy([], "yield") is None


def test_attempt_memory_record_stores_executed_strategy():
    memory = AttemptMemory(window_sec=60.0)
    memory.record("c2", ["robot_1"], "yield", None, now=0.0, executed_strategy="temporary_wait")
    memory.resolve("c2", "completed", now=1.0)
    record = memory.context_for(["robot_1"], now=2.0)
    assert record is not None
    assert record.executed_strategy == "temporary_wait"


def test_attempt_memory_record_defaults_executed_strategy_to_none():
    memory = _memory()
    memory.resolve("c1", "completed", now=1.0)
    record = memory.context_for(["robot_1"], now=2.0)
    assert record is not None
    assert record.executed_strategy is None

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

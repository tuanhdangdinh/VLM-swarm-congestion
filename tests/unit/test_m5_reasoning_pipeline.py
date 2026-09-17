"""Unit tests for the M5 reasoning pipeline adapter, frame dump, and fan-out."""
from __future__ import annotations

import json

import numpy as np
import pytest
from swarm_orchestrator.command_lifecycle import AttemptRecord
from swarm_orchestrator.models import PipelineOutcome, RobotView, SceneSnapshot, TerminalStage
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    build_failure_context,
    build_reasoner_request,
    dump_frame_png,
    fan_out_command,
    write_decision_artifact,
)

from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    FailureContext,
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
    diag = ReasonerDiagnostics(
        request_id="r1", backend_id="mock", attempts=2, parse_status="failed"
    )
    return ReasonerResult(request_id="r1", decision=None, raw_text=None, diagnostics=diag)


def _must_not_ground(result, robot_positions=None, geometry=None):
    pytest.fail("ground_fn must not run")


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
        ground_fn=lambda result, robot_positions=None, geometry=None: grounded,
    )
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.OK
    assert outcome.grounded_command == grounded


def test_pipeline_no_congestion_terminates_at_vlm():
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_no_congestion_result()),
        ground_fn=_must_not_ground,
    )
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.VLM
    assert outcome.grounded_command is None


def test_pipeline_vlm_failure_terminates_at_vlm():
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_failed_result()),
        ground_fn=_must_not_ground,
    )
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.VLM
    assert outcome.failure_reason is not None


def test_pipeline_grounding_failure_terminates_at_grounding():
    def _raise(result, robot_positions=None, geometry=None):
        raise ValueError("schema invalid")
    pipe = InProcessPipeline(reasoner=_FakeReasoner(_ok_result()), ground_fn=_raise)
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.GROUNDING
    assert "schema invalid" in outcome.failure_reason


class _RaisingReasoner:
    def run(self, request):
        raise RuntimeError("backend exploded")


def test_pipeline_reasoner_exception_terminates_at_vlm_without_raising():
    # An unexpected exception from M2 must become a PipelineOutcome, not bubble out
    # (FR5.3.2: failures from either stage are caught, never raised past the adapter).
    pipe = InProcessPipeline(
        reasoner=_RaisingReasoner(),
        ground_fn=_must_not_ground,
    )
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.VLM
    assert outcome.grounded_command is None
    assert "backend exploded" in outcome.failure_reason


def test_pipeline_invalid_grounded_command_terminates_at_grounding():
    # A grounded dict that fails the coordination_command schema must not reach OK.
    invalid = {"command_id": "c1"}  # missing actions / fallback / resolution
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()),
        ground_fn=lambda result, robot_positions=None, geometry=None: invalid,
    )
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.GROUNDING
    assert outcome.grounded_command is None


def test_pipeline_valid_grounded_command_passes_validation():
    valid = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield"}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()),
        ground_fn=lambda result, robot_positions=None, geometry=None: valid,
    )
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.OK
    assert outcome.grounded_command == valid


def test_pipeline_filters_grounded_actions_to_request_robot_ids():
    grounded = {
        "command_id": "c1",
        "actions": [
            {"robot_id": "robot_0", "action": "temporary_wait"},
            {"robot_id": "robot_20", "action": "temporary_wait"},
        ],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()),
        ground_fn=lambda result, robot_positions=None, geometry=None: grounded,
    )

    outcome = pipe.run(_request())

    assert outcome.terminal_stage is TerminalStage.OK
    assert outcome.grounded_command["actions"] == [
        {"robot_id": "robot_0", "action": "temporary_wait"}
    ]


def test_pipeline_rejects_grounded_actions_for_unknown_robot_ids():
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_20", "action": "temporary_wait"}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()),
        ground_fn=lambda result, robot_positions=None, geometry=None: grounded,
    )

    outcome = pipe.run(_request())

    assert outcome.terminal_stage is TerminalStage.GROUNDING
    assert "no actions for known robots" in outcome.failure_reason


def test_pipeline_passes_snapshot_positions_to_grounder():
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield"}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    seen: dict[str, object] = {}

    def _record(result, robot_positions=None, geometry=None):
        seen["positions"] = robot_positions
        seen["geometry"] = geometry
        return grounded

    geometry = SceneGeometry(
        corridor=CorridorGeometry(
            half_length_m=1.0, aisle_half_width_m=0.6, occluder_height_m=0.9
        )
    )
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()), ground_fn=_record, scene_geometry=geometry
    )

    pipe.run(_request())

    assert seen["positions"] == {"robot_0": (1.0, 2.0)}
    assert seen["geometry"] == geometry


def test_pipeline_passes_no_geometry_to_grounder_when_unconfigured():
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield"}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    seen: dict[str, object] = {"geometry": "unset"}

    def _record(result, robot_positions=None, geometry=None):
        seen["geometry"] = geometry
        return grounded

    pipe = InProcessPipeline(reasoner=_FakeReasoner(_ok_result()), ground_fn=_record)

    pipe.run(_request())

    assert seen["geometry"] is None


# ---- decision artifacts ----

def test_write_decision_artifact_preserves_m2_result_on_grounding_failure(tmp_path):
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on aisle conflict",
        strategy="robot_1 yields while robot_2 passes",
        justification="both robots are stopped in opposing directions",
    )
    diagnostics = ReasonerDiagnostics(
        request_id="r1",
        backend_id="openai",
        attempts=1,
        parse_status="valid",
        latency_ms=123,
        token_usage={"total_tokens": 42},
    )
    result = ReasonerResult(
        request_id="r1",
        decision=decision,
        raw_text='{"congestion_detected": true}',
        diagnostics=diagnostics,
    )
    outcome = PipelineOutcome(
        request_id="r1",
        reasoner_result=result,
        grounded_command=None,
        terminal_stage=TerminalStage.GROUNDING,
        failure_reason="grounding failed: M3 grounding not yet implemented",
    )

    path = write_decision_artifact(tmp_path, outcome)
    payload = json.loads(path.read_text())

    assert path == tmp_path / "r1.json"
    assert payload["request_id"] == "r1"
    assert payload["terminal_stage"] == "grounding"
    assert payload["failure_reason"] == "grounding failed: M3 grounding not yet implemented"
    assert payload["grounded_command_present"] is False
    assert payload["decision"]["type"] == "deadlock"
    assert payload["decision"]["involved_robots"] == ["robot_1", "robot_2"]
    assert payload["diagnostics"]["backend_id"] == "openai"
    assert payload["diagnostics"]["token_usage"] == {"total_tokens": 42}
    assert payload["raw_text"] == '{"congestion_detected": true}'


# ---- failure context ----

def _attempt(status: str = "completed", resolved_at: float = 100.0) -> AttemptRecord:
    return AttemptRecord(
        command_id="c1",
        robot_ids=["robot_1", "robot_2"],
        strategy="yield",
        yield_robot="robot_1",
        dispatched_at=40.0,
        resolved_at=resolved_at,
        outcome_status=status,
    )


def _ok_outcome() -> PipelineOutcome:
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on aisle conflict",
        strategy="yield",
        justification="both robots are stopped in opposing directions",
    )
    result = ReasonerResult(
        request_id="r1",
        decision=decision,
        raw_text='{"congestion_detected": true}',
        diagnostics=ReasonerDiagnostics(
            request_id="r1", backend_id="openai", attempts=1, parse_status="valid"
        ),
    )
    return PipelineOutcome(
        request_id="r1",
        reasoner_result=result,
        grounded_command={"command_id": "c1", "actions": []},
        terminal_stage=TerminalStage.OK,
    )


def test_build_failure_context_names_yielder_and_seconds_since_completion():
    ctx = build_failure_context(_attempt(), now=131.0)
    assert ctx.strategy == "yield"
    assert ctx.yield_robot == "robot_1"
    assert ctx.outcome_status == "completed"
    assert ctx.failure_detail == (
        "yield completed 31 s ago; congestion re-detected for the same robots"
    )


def test_build_failure_context_reports_run_time_for_timed_out_attempt():
    ctx = build_failure_context(_attempt(status="timed_out", resolved_at=60.0), now=90.0)
    assert ctx.outcome_status == "timed_out"
    assert ctx.failure_detail == (
        "yield timed_out after 20 s; congestion re-detected for the same robots"
    )


def test_build_reasoner_request_passes_failure_context_through():
    ctx = FailureContext(strategy="yield", outcome_status="failed", failure_detail="d")
    with_ctx = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png", failure_context=ctx)
    without = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png")
    assert with_ctx.failure_context == ctx
    assert without.failure_context is None


def test_write_decision_artifact_records_failure_context(tmp_path):
    ctx = FailureContext(
        strategy="yield", yield_robot="robot_1", outcome_status="completed", failure_detail="d"
    )
    path = write_decision_artifact(tmp_path, _ok_outcome(), failure_context=ctx)
    payload = json.loads(path.read_text())
    assert payload["failure_context"] == {
        "strategy": "yield",
        "yield_robot": "robot_1",
        "crossing_order": None,
        "outcome_status": "completed",
        "failure_detail": "d",
    }


def test_build_failure_context_notes_executed_strategy_when_it_differs():
    record = _attempt()
    record.executed_strategy = "temporary_wait"
    ctx = build_failure_context(record, now=131.0)
    assert ctx.strategy == "yield"
    assert ctx.failure_detail == (
        "yield completed 31 s ago (executed as temporary_wait); "
        "congestion re-detected for the same robots"
    )


def test_build_failure_context_notes_executed_strategy_after_run_time_when_not_completed():
    record = _attempt(status="timed_out", resolved_at=60.0)
    record.executed_strategy = "temporary_wait"
    ctx = build_failure_context(record, now=90.0)
    assert ctx.failure_detail == (
        "yield timed_out after 20 s (executed as temporary_wait); "
        "congestion re-detected for the same robots"
    )


def test_build_failure_context_omits_executed_note_when_it_matches_strategy():
    record = _attempt()
    record.executed_strategy = "yield"
    assert "(executed as" not in build_failure_context(record, now=131.0).failure_detail


def test_write_decision_artifact_writes_null_failure_context_when_absent(tmp_path):
    payload = json.loads(write_decision_artifact(tmp_path, _ok_outcome()).read_text())
    assert payload["failure_context"] is None

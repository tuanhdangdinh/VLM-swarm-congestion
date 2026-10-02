"""Unit tests for the M5 reasoning pipeline adapter, frame dump, and fan-out."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import yaml
from swarm_orchestrator.command_lifecycle import (
    AttemptContexts,
    AttemptMemory,
    AttemptRecord,
)
from swarm_orchestrator.models import (
    OrchestratorConfig,
    PipelineOutcome,
    RobotView,
    SceneSnapshot,
    TaskAssignment,
    TerminalStage,
)
from swarm_orchestrator.plan_tracker import PlanTracker
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    LatestRawFrame,
    append_scene_log,
    attach_registry_assignments,
    build_failure_context,
    build_failure_contexts,
    build_reasoner_request,
    dump_frame_png,
    fan_out_command,
    raw_frame_dump_path,
    raw_frame_skew_sec,
    summarize_yield_grounding,
    write_decision_artifact,
)
from swarm_orchestrator.task_registry import TaskRegistry

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import ArmGeometry, CorridorGeometry, SceneGeometry
from reasoning.vlm.backend_factory import (
    backend_section,
    describe_effective_sampling,
    resolve_reasoner_config,
)
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    BackendResponse,
    CongestionDecision,
    FailureContext,
    GeminiBackendConfig,
    OpenAIBackendConfig,
    ProposedPlanLeg,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
    StaticObstacleInput,
)
from reasoning.vlm.prompt_builder import build_prompt_payload
from reasoning.vlm.reasoner import Reasoner


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


def test_build_reasoner_request_defaults_to_the_current_prompt_version():
    req = build_reasoner_request(request_id="r1", snapshot=_snapshot(), image_path="/tmp/r1.png")
    assert req.prompt_version == 2


def test_build_reasoner_request_passes_prompt_version_through():
    req = build_reasoner_request(
        request_id="r1", snapshot=_snapshot(), image_path="/tmp/r1.png", prompt_version=1
    )
    assert req.prompt_version == 1


def test_build_reasoner_request_leaves_goal_and_task_none_without_registry():
    state = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png").robot_states[0]
    assert state.goal is None and state.task is None


def _registry_goal(robot_id):
    return {"robot_0": (2.5, 0.0)}.get(robot_id)


def _registry_task(robot_id):
    return {"robot_0": "cross_narrow_aisle"}.get(robot_id)


def test_attach_registry_assignments_sets_goal_and_task_per_robot():
    attached = attach_registry_assignments(_snapshot(), _registry_goal, _registry_task)
    assert attached.robots[0].goal == (2.5, 0.0)
    assert attached.robots[0].task == "cross_narrow_aisle"
    assert _snapshot().robots[0].goal is None


def test_attach_registry_assignments_leaves_unassigned_robots_none():
    attached = attach_registry_assignments(_snapshot(), lambda _r: None, lambda _r: None)
    assert attached.robots[0].goal is None and attached.robots[0].task is None


def test_build_reasoner_request_carries_registry_goal_and_task():
    snapshot = attach_registry_assignments(_snapshot(), _registry_goal, _registry_task)
    state = build_reasoner_request("r1", snapshot, "/tmp/r1.png").robot_states[0]
    assert state.goal == (2.5, 0.0)
    assert state.task == "cross_narrow_aisle"


def test_v2_prompt_renders_the_registry_goal_and_task():
    snapshot = attach_registry_assignments(_snapshot(), _registry_goal, _registry_task)
    prompt = build_prompt_payload(build_reasoner_request("r1", snapshot, "/tmp/r1.png"))
    assert "goal_x=2.50, goal_y=0.00, task=cross_narrow_aisle" in prompt.user_prompt


def test_scene_stored_before_the_bundle_still_parses_without_goal_or_task():
    stored = _snapshot().model_dump(mode="json")
    for robot in stored["robots"]:
        del robot["goal"], robot["task"]
    assert SceneSnapshot(**stored).robots[0].goal is None


def test_attached_scene_round_trips_through_the_artifact_json():
    snapshot = attach_registry_assignments(_snapshot(), _registry_goal, _registry_task)
    restored = SceneSnapshot(**json.loads(json.dumps(snapshot.model_dump(mode="json"))))
    assert restored == snapshot


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


def _must_not_ground(result, robot_positions=None, geometry=None, **_gate):
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
        ground_fn=lambda result, robot_positions=None, geometry=None, **_gate: grounded,
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
    def _raise(result, robot_positions=None, geometry=None, **_gate):
        raise ValueError("schema invalid")
    pipe = InProcessPipeline(reasoner=_FakeReasoner(_ok_result()), ground_fn=_raise)
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.GROUNDING
    assert "schema invalid" in outcome.failure_reason


# ---- (a0) plan channel, behind plan_channel_enabled ----


def _fixed_ground_fn(grounded):
    return lambda result, robot_positions=None, geometry=None, **_gate: dict(grounded)


def _yield_result(request_id="r1", proposed_plan=None, yield_robot=None):
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_0"],
        root_cause="head-on",
        strategy="yield",
        justification="x",
        yield_robot=yield_robot,
        proposed_plan=proposed_plan,
    )
    diag = ReasonerDiagnostics(
        request_id=request_id, backend_id="mock", attempts=1, parse_status="valid"
    )
    return ReasonerResult(
        request_id=request_id, decision=decision, raw_text="{}", diagnostics=diag
    )


def _head_on_request() -> ReasonerRequest:
    snapshot = SceneSnapshot(
        stamp=5.0,
        frame_id="cam0",
        robots=[
            RobotView(robot_id="robot_1", x=-0.3, y=0.0, theta=0.0, linear_velocity=0.0,
                      status="STOPPED", stamp=5.0),
            RobotView(robot_id="robot_2", x=0.3, y=0.0, theta=3.14159, linear_velocity=0.0,
                      status="STOPPED", stamp=5.0),
        ],
        dropped_frame=False,
    )
    return build_reasoner_request(request_id="r1", snapshot=snapshot, image_path="/tmp/r1.png")


def _head_on_yield_result() -> ReasonerResult:
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on",
        strategy="yield",
        justification="x",
        yield_robot="robot_1",
    )
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)


def _shipped_grounding_params() -> GroundingParams:
    import yaml

    with open("config/rag.yaml", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return GroundingParams(**raw["grounding"])


def test_plan_matches_dispatch_on_the_real_two_robot_head_on_grounder():
    # The CORE engine's own exhaustively-verified claim, checked against the
    # SHIPPED mode (config/rag.yaml's grounding.mode: derived, not legacy):
    # in a two-robot head-on, the tracked plan's legs ARE what
    # ground_reasoner_result actually dispatches (ruling 3 extended the
    # default-plan equivalence to derived mode). Uses the real grounder
    # (not a mock ground_fn), so this is the one live check that
    # `dispatch_matches_plan` reports True where the engine's own sweeps
    # already prove it must.
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_head_on_yield_result()),
        ground_fn=ground_reasoner_result,
        grounding_params=_shipped_grounding_params(),
        plan_tracker=PlanTracker(),
    )
    outcome = pipe.run(_head_on_request())
    assert outcome.plan is not None
    assert outcome.plan.dispatch_matches_plan is True


def test_plan_present_derived_mode_band_gap_is_measured_not_hidden():
    # The one documented, narrower boundary (CORE step's note, re-flagged in
    # this task): `_plan_problems` does not model DERIVED mode's backup-band
    # sweep for a VLM-supplied verbatim plan, so a plan naming the decided
    # (feasible-by-the-room-check) yielder can pass verification as
    # `vlm_verbatim` while the REAL derived-mode dispatch reroutes under an
    # impossible band. `dispatch_matches_plan` makes that divergence visible
    # instead of silently assumed away.
    impossible_band = GroundingParams(mode="derived", backup_band_m=(0.01, 0.02))
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on",
        strategy="yield",
        justification="x",
        yield_robot="robot_1",
        proposed_plan=[
            ProposedPlanLeg(robot_id="robot_1", action="yield"),
            ProposedPlanLeg(robot_id="robot_2", action="cross"),
        ],
    )
    diag = ReasonerDiagnostics(
        request_id="r1", backend_id="mock", attempts=1, parse_status="valid"
    )
    result = ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(result),
        ground_fn=ground_reasoner_result,
        grounding_params=impossible_band,
        plan_tracker=PlanTracker(),
    )
    outcome = pipe.run(_head_on_request())
    assert outcome.plan is not None
    assert outcome.plan.provenance == "vlm_verbatim"
    assert outcome.grounded_command["actions"][0]["action"] == "reroute"
    assert outcome.plan.dispatch_matches_plan is False


_IB10_STANDOFF = {
    "robot_1": (-0.2192, -0.0014),
    "robot_2": (0.33, 0.0158),
    "robot_3": (-0.0208, -0.2583),
    "robot_4": (0.0045, 0.2773),
}
_JUNCTION_ARMS = {
    "robot_1": ArmGeometry(axis="x", side=-1),
    "robot_2": ArmGeometry(axis="x", side=1),
    "robot_3": ArmGeometry(axis="y", side=-1),
    "robot_4": ArmGeometry(axis="y", side=1),
}


def _junction_clear_geometry() -> SceneGeometry:
    corridor = CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.6, aisle_half_width_m=0.6, occluder_height_m=0.0
    )
    return SceneGeometry(
        corridor=corridor,
        arms=_JUNCTION_ARMS,
        junction_recede_offset_m=1.2,
        junction_backup_clearance_m=1.1,
    )


def _junction_clear_request() -> ReasonerRequest:
    snapshot = SceneSnapshot(
        stamp=1.0,
        frame_id="cam0",
        robots=[
            RobotView(
                robot_id=rid, x=xy[0], y=xy[1], theta=0.0, linear_velocity=0.0,
                status="STOPPED", stamp=1.0,
            )
            for rid, xy in _IB10_STANDOFF.items()
        ],
        dropped_frame=False,
    )
    return build_reasoner_request(request_id="r1", snapshot=snapshot, image_path="/tmp/r1.png")


def _junction_clear_result(request_id: str = "r1") -> ReasonerResult:
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=list(_IB10_STANDOFF),
        root_cause="four-way standoff",
        strategy="junction_clear",
        justification="jam",
    )
    diag = ReasonerDiagnostics(
        request_id=request_id, backend_id="mock", attempts=1, parse_status="valid"
    )
    return ReasonerResult(request_id=request_id, decision=decision, raw_text="{}", diagnostics=diag)


def test_junction_clear_seeds_phases_and_matches_dispatch():
    # Advisor-review regression: comparing phase one ALONE against the
    # accepted plan's full recede-then-yield sequence made
    # `dispatch_matches_plan` read False for every `junction_clear`
    # decision, even this clean one -- `junction_clear_plan_matches_dispatch`
    # reconstructs the whole sequence's per-robot action instead.
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_junction_clear_result()),
        ground_fn=ground_reasoner_result,
        grounding_params=GroundingParams(mode="derived"),
        scene_geometry=_junction_clear_geometry(),
        plan_tracker=PlanTracker(),
    )
    outcome = pipe.run(_junction_clear_request())
    assert outcome.plan is not None
    assert outcome.plan.dispatch_matches_plan is True
    assert outcome.junction_phases is not None
    assert [phase.label for phase in outcome.junction_phases.phases] == [
        "recede",
        "recede",
        "cross",
        "release",
    ]
    assert outcome.grounded_command["command_id"] == outcome.junction_phases.phases[0].command[
        "command_id"
    ]


def test_junction_clear_absent_without_a_declared_pocket_still_matches():
    # The plain-`yield` fallback path (`_ground_derived`'s own junction_clear
    # branch): no `junction_phases` to seed, and the single dispatched
    # command IS the whole resolution, so the ordinary `plan_matches_dispatch`
    # must still read True.
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_junction_clear_result()),
        ground_fn=ground_reasoner_result,
        grounding_params=GroundingParams(mode="derived"),
        scene_geometry=_junction_clear_geometry().model_copy(
            update={"junction_recede_offset_m": None}
        ),
        plan_tracker=PlanTracker(),
    )
    outcome = pipe.run(_junction_clear_request())
    assert outcome.junction_phases is None
    assert outcome.plan is not None
    assert outcome.plan.dispatch_matches_plan is True


def test_plan_tracker_omitted_leaves_the_outcome_and_command_untouched():
    # Flag off (no plan_tracker passed, the default): `run()` must never call
    # verify_and_repair_plan or touch the grounded command, so the dispatch
    # path is byte-identical to before this channel existed.
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield", "parameters": {}}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()), ground_fn=_fixed_ground_fn(grounded)
    )
    outcome = pipe.run(_request())
    assert outcome.plan is None
    assert outcome.grounded_command == grounded
    assert "plan_id" not in outcome.grounded_command["actions"][0]["parameters"]


def test_plan_tracker_enabled_assigns_a_plan_id_and_tags_every_action():
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield", "parameters": {"x": 1}}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    tracker = PlanTracker()
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()),
        ground_fn=_fixed_ground_fn(grounded),
        plan_tracker=tracker,
    )
    outcome = pipe.run(_request())
    assert outcome.plan is not None
    assert outcome.plan.plan_id == 1
    # Not emitted by _ok_result's decision -> M3's own derived plan.
    assert outcome.plan.provenance == "m3_default"
    assert outcome.plan.superseded_plan_id is None
    assert outcome.grounded_command["actions"][0]["parameters"]["plan_id"] == 1
    # The rest of parameters survives untouched.
    assert outcome.grounded_command["actions"][0]["parameters"]["x"] == 1
    assert tracker.active_plan is not None and tracker.active_plan.plan_id == 1


def test_plan_tracker_leaves_grounded_command_shape_otherwise_unchanged():
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield", "parameters": {}}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()),
        ground_fn=_fixed_ground_fn(grounded),
        plan_tracker=PlanTracker(),
    )
    outcome = pipe.run(_request())
    tagged = outcome.grounded_command
    assert tagged["command_id"] == grounded["command_id"]
    assert tagged["expected_resolution_time_sec"] == grounded["expected_resolution_time_sec"]
    assert tagged["fallback"] == grounded["fallback"]
    assert tagged["actions"][0]["robot_id"] == "robot_0"
    assert tagged["actions"][0]["action"] == "yield"


def test_plan_tracker_second_decision_supersedes_the_first():
    # _ok_result()'s decision (single robot, strategy "yield", no declared
    # scene geometry) derives an m3_default plan of a single "wait" leg
    # (_derive_default_plan has no counterpart robot to yield to). A second
    # decision with an EXPLICIT, genuinely different leg (a "yield" leg,
    # consistent with the strategy per `_is_consistent`) is what exercises
    # supersession here -- an identical second decision would now be a HOLD
    # (ruling 2026-10-02; see TestHoldSemantics-equivalent coverage in
    # test_m5_plan_tracker.py), not a supersession.
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield", "parameters": {}}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    tracker = PlanTracker()
    ground_fn = _fixed_ground_fn(grounded)
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()), ground_fn=ground_fn, plan_tracker=tracker
    )
    first = pipe.run(_request())
    assert first.plan.plan_id == 1
    assert first.plan.plan_held is False

    pipe2 = InProcessPipeline(
        reasoner=_FakeReasoner(_no_congestion_result()), ground_fn=ground_fn, plan_tracker=tracker
    )
    # A congestion_detected=False analysis never reaches the plan channel
    # (it terminates at VLM, before grounding); confirm that, then supersede
    # with a second real decision.
    cleared = pipe2.run(_request())
    assert cleared.plan is None

    pipe3 = InProcessPipeline(
        reasoner=_FakeReasoner(
            _yield_result(proposed_plan=[ProposedPlanLeg(robot_id="robot_0", action="yield")])
        ),
        ground_fn=ground_fn,
        plan_tracker=tracker,
    )
    second = pipe3.run(_request())
    assert second.plan.plan_id == 2
    assert second.plan.superseded_plan_id == 1
    assert second.plan.plan_held is False


def test_plan_tracker_identical_second_decision_is_a_hold_not_a_replan():
    # The step-4 regression gate's "zero unforced replans": a second analysis
    # whose verified plan is identical to the active plan's remaining legs is
    # a HOLD (ruling 2026-10-02) -- same plan_id, no supersession.
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield", "parameters": {}}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    tracker = PlanTracker()
    ground_fn = _fixed_ground_fn(grounded)
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()), ground_fn=ground_fn, plan_tracker=tracker
    )
    first = pipe.run(_request())
    assert first.plan.plan_id == 1

    pipe2 = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()), ground_fn=ground_fn, plan_tracker=tracker
    )
    second = pipe2.run(_request())
    assert second.plan.plan_id == 1
    assert second.plan.plan_held is True
    assert second.plan.superseded_plan_id is None
    assert tracker.plan_holds == 1


class _RaisingPlanTracker:
    """A plan_tracker double whose `accept_plan` always raises."""

    def accept_plan(self, verified):
        raise RuntimeError("plan tracker exploded")


def test_plan_channel_failure_never_blocks_an_otherwise_successful_dispatch():
    # "never raised past this adapter" (FR5.3.2), extended to the plan
    # channel: a verify_and_repair_plan/accept_plan exception must still let
    # the already-grounded command dispatch, untouched by _attach_plan_id.
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield", "parameters": {}}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()),
        ground_fn=_fixed_ground_fn(grounded),
        plan_tracker=_RaisingPlanTracker(),
    )
    outcome = pipe.run(_request())
    assert outcome.terminal_stage is TerminalStage.OK
    assert outcome.grounded_command == grounded
    assert "plan_id" not in outcome.grounded_command["actions"][0]["parameters"]
    assert outcome.plan is None
    assert outcome.plan_error is not None
    assert "plan tracker exploded" in outcome.plan_error


def test_write_decision_artifact_records_plan_error_when_present(tmp_path):
    outcome = _ok_outcome().model_copy(update={"plan_error": "plan tracker exploded"})
    payload = json.loads(write_decision_artifact(tmp_path, outcome).read_text())
    assert payload["plan_error"] == "plan tracker exploded"


def test_write_decision_artifact_omits_plan_error_key_when_absent(tmp_path):
    payload = json.loads(write_decision_artifact(tmp_path, _ok_outcome()).read_text())
    assert "plan_error" not in payload


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
        ground_fn=lambda result, robot_positions=None, geometry=None, **_gate: invalid,
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
        ground_fn=lambda result, robot_positions=None, geometry=None, **_gate: valid,
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
        ground_fn=lambda result, robot_positions=None, geometry=None, **_gate: grounded,
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
        ground_fn=lambda result, robot_positions=None, geometry=None, **_gate: grounded,
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

    def _record(result, robot_positions=None, geometry=None, **_gate):
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


def test_pipeline_passes_no_priorities_kwarg_without_a_declared_priority():
    seen: dict[str, object] = {}

    def _record(result, robot_positions=None, geometry=None, **kwargs):
        seen.update(kwargs)
        return {
            "command_id": "c1",
            "actions": [{"robot_id": "robot_0", "action": "yield"}],
            "expected_resolution_time_sec": 18.0,
            "fallback": "stop",
        }

    for priorities in (None, {}):
        seen.clear()
        InProcessPipeline(
            reasoner=_FakeReasoner(_ok_result()), ground_fn=_record, priorities=priorities
        ).run(_request())
        assert "priorities" not in seen


def test_pipeline_passes_declared_priorities_to_grounder():
    seen: dict[str, object] = {}

    def _record(result, robot_positions=None, geometry=None, **kwargs):
        seen.update(kwargs)
        return {
            "command_id": "c1",
            "actions": [{"robot_id": "robot_0", "action": "yield"}],
            "expected_resolution_time_sec": 18.0,
            "fallback": "stop",
        }

    InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()), ground_fn=_record, priorities={"robot_0": 1}
    ).run(_request())
    assert seen["priorities"] == {"robot_0": 1}


def _priority_prompt(priorities: dict[str, int]) -> tuple[str, str]:
    # The M5 path that builds a prompt: registry -> attached assignments ->
    # request -> payload. Labels are the B2 _r2 member's.
    tasks = {
        "robot_1": TaskAssignment(task="routine_order_delivery", goal=(2.5, 0.0),
                                  priority=priorities.get("robot_1", 0)),
        "robot_2": TaskAssignment(task="urgent_order_delivery", goal=(-2.5, 0.0),
                                  priority=priorities.get("robot_2", 0)),
    }
    config = OrchestratorConfig(
        stall_threshold_sec=12.0, progress_epsilon_m=0.1, cooldown_sec=15.0,
        command_timeout_sec=20.0, reasoning_backend_id="mock",
        frame_dump_dir="data/logs/m5_frames", initial_tasks=tasks,
    )
    registry = TaskRegistry()
    registry.load_initial(config)
    snapshot = SceneSnapshot(
        stamp=30.0,
        frame_id="cam0",
        robots=[
            RobotView(robot_id="robot_1", x=-0.12, y=0.0, theta=0.0,
                      linear_velocity=0.0, status="STOPPED", stamp=30.0),
            RobotView(robot_id="robot_2", x=0.12, y=0.0, theta=3.14159,
                      linear_velocity=0.0, status="STOPPED", stamp=30.0),
        ],
    )

    def goal_of(rid):
        effective = registry.effective(rid)
        return None if effective is None else effective[1]

    attached = attach_registry_assignments(snapshot, goal_of, registry.mission_task)
    request = build_reasoner_request("req-b2", attached, "/tmp/req-b2.png")
    payload = build_prompt_payload(request)
    return payload.system_prompt, payload.user_prompt


def test_priority_is_never_rendered_in_the_prompt():
    plain = _priority_prompt({})
    for priorities in ({"robot_2": 1}, {"robot_1": 1}, {"robot_1": 7, "robot_2": 3}):
        assert _priority_prompt(priorities) == plain
    # "priority" occurs in the prompt only as the strategy enum value.
    user = plain[1]
    assert user.count("priority") == user.count("priority_override")
    assert "task=urgent_order_delivery" in user


def test_pipeline_passes_no_geometry_to_grounder_when_unconfigured():
    grounded = {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield"}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }
    seen: dict[str, object] = {"geometry": "unset"}

    def _record(result, robot_positions=None, geometry=None, **_gate):
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


def test_write_decision_artifact_records_prompt_version(tmp_path):
    path = write_decision_artifact(tmp_path, _ok_outcome(), request=_request())
    payload = json.loads(path.read_text())
    assert payload["prompt_version"] == 2


def test_write_decision_artifact_prompt_version_is_none_without_request(tmp_path):
    payload = json.loads(write_decision_artifact(tmp_path, _ok_outcome()).read_text())
    assert payload["prompt_version"] is None


def test_write_decision_artifact_records_plan_state_when_request_carries_one(tmp_path):
    from swarm_orchestrator.plan_tracker import PlanTracker

    from reasoning.rag.command_grounder import VerifiedPlan
    from reasoning.vlm.models import ProposedPlanLeg

    tracker = PlanTracker()
    verified = VerifiedPlan(
        legs=[
            ProposedPlanLeg(robot_id="robot_1", action="yield"),
            ProposedPlanLeg(robot_id="robot_2", action="cross"),
        ],
        provenance="vlm_verbatim",
    )
    accepted = tracker.accept_plan(verified)
    plan_state = tracker.plan_state_context(accepted.plan.plan_id, since_plan_id=None)
    request = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", prompt_version=3, plan_state=plan_state
    )
    path = write_decision_artifact(tmp_path, _ok_outcome(), request=request)
    payload = json.loads(path.read_text())
    assert payload["plan_state"]["plan_id"] == accepted.plan.plan_id
    assert payload["plan_state"]["legs"][0]["robot_id"] == "robot_1"


def test_write_decision_artifact_omits_plan_state_key_when_absent(tmp_path):
    payload = json.loads(
        write_decision_artifact(tmp_path, _ok_outcome(), request=_request()).read_text()
    )
    assert "plan_state" not in payload


def test_write_decision_artifact_records_image_fallback_diagnostics(tmp_path):
    result = ReasonerResult(
        request_id="r2",
        decision=None,
        raw_text="I'm sorry, I can't assist with that.",
        diagnostics=ReasonerDiagnostics(
            request_id="r2",
            backend_id="openai",
            attempts=4,
            parse_status="failed",
            refusal_attempts=3,
            image_fallback_used=True,
            image_fallback_attempt=3,
        ),
    )
    outcome = PipelineOutcome(
        request_id="r2",
        reasoner_result=result,
        grounded_command=None,
        terminal_stage=TerminalStage.VLM,
        failure_reason="vlm returned no decision",
    )

    payload = json.loads(write_decision_artifact(tmp_path, outcome).read_text())

    assert payload["diagnostics"]["refusal_attempts"] == 3
    assert payload["diagnostics"]["image_fallback_used"] is True
    assert payload["diagnostics"]["image_fallback_attempt"] == 3


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


def test_build_reasoner_request_passes_geometry_switch_through():
    on = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png")
    off = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", include_pairwise_geometry=False
    )
    assert on.include_pairwise_geometry is True
    assert off.include_pairwise_geometry is False


def test_build_reasoner_request_passes_robot_presentation_order_through():
    default = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png")
    reversed_order = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", robot_presentation_order="id_desc"
    )
    assert default.robot_presentation_order == "id_asc"
    assert reversed_order.robot_presentation_order == "id_desc"


def test_build_reasoner_request_accepts_the_config_robot_order():
    # Under a fixed mode the node hands the config value straight through (the
    # "random" mode resolves via EpisodeOrderTracker instead); node code is not
    # exercised by the unit suite, so pin the seam here.
    cfg = OrchestratorConfig(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={"robot_0": TaskAssignment(task="t", goal=(0.0, 0.0))},
        frame_dump_dir="data/logs/m5_frames",
        prompt_robot_order="id_desc",
    )
    req = build_reasoner_request(
        "r1",
        _snapshot(),
        "/tmp/r1.png",
        robot_presentation_order=cfg.prompt_robot_order,
    )

    assert req.robot_presentation_order == "id_desc"


def test_build_reasoner_request_passes_static_obstacles_through():
    obstacle = StaticObstacleInput(
        obstacle_id="blocker_west", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3
    )
    default = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png")
    on = build_reasoner_request(
        "r1",
        _snapshot(),
        "/tmp/r1.png",
        static_obstacles=[obstacle],
        include_static_obstacles=True,
    )
    assert default.static_obstacles == []
    assert default.include_static_obstacles is False
    assert on.static_obstacles == [obstacle]
    assert on.include_static_obstacles is True


def test_build_reasoner_request_accepts_the_config_obstacle_tuple():
    # The node hands the config's tuple straight to build_reasoner_request; this
    # pins that seam, since node code is not exercised by the unit suite.
    cfg = OrchestratorConfig(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={"robot_0": TaskAssignment(task="t", goal=(0.0, 0.0))},
        frame_dump_dir="data/logs/m5_frames",
        prompt_static_obstacles=True,
        static_obstacles=(
            StaticObstacleInput(
                obstacle_id="blocker_west", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3
            ),
        ),
    )
    req = build_reasoner_request(
        "r1",
        _snapshot(),
        "/tmp/r1.png",
        static_obstacles=cfg.static_obstacles,
        include_static_obstacles=cfg.prompt_static_obstacles,
    )

    assert req.include_static_obstacles is True
    assert [o.obstacle_id for o in req.static_obstacles] == ["blocker_west"]


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


def _l4_memory() -> AttemptMemory:
    # Run 20260925_011246 (L4): yield(robot_1) FAILED, temporary_wait COMPLETED,
    # then the re-analysis that re-yielded robot_1 (request ca63fbd5).
    memory = AttemptMemory(window_sec=60.0)
    memory.record("c1-yield", ["robot_1", "robot_2"], "yield", "robot_1", now=4.3)
    memory.resolve("c1-yield", "failed", now=126.0)
    memory.record("c2-wait", ["robot_1"], "temporary_wait", None, now=146.3)
    memory.resolve("c2-wait", "completed", now=164.9)
    return memory


def _request_from_memory(memory: AttemptMemory, now: float) -> ReasonerRequest:
    latest, last_failed = build_failure_contexts(
        memory.contexts_for(["robot_1", "robot_2"], now), now
    )
    return build_reasoner_request(
        "r1",
        _snapshot(),
        "/tmp/r1.png",
        failure_context=latest,
        last_failed_context=last_failed,
    )


def test_request_carries_wait_and_failed_yield_after_wait_completes():
    request = _request_from_memory(_l4_memory(), now=182.2)
    assert request.failure_context is not None
    assert request.failure_context.strategy == "temporary_wait"
    assert request.failure_context.outcome_status == "completed"
    assert request.last_failed_context is not None
    assert request.last_failed_context.strategy == "yield"
    assert request.last_failed_context.yield_robot == "robot_1"
    assert request.last_failed_context.outcome_status == "failed"
    assert request.last_failed_context.failure_detail == (
        "yield failed after 122 s; congestion re-detected for the same robots"
    )
    prompt = build_prompt_payload(request).user_prompt
    assert "Previous attempt in this episode:" in prompt
    assert "Earlier failed attempt in this episode:" in prompt


def test_request_carries_single_block_when_latest_attempt_is_the_failure():
    memory = AttemptMemory(window_sec=60.0)
    memory.record("c1-yield", ["robot_1", "robot_2"], "yield", "robot_1", now=4.3)
    memory.resolve("c1-yield", "failed", now=126.0)
    request = _request_from_memory(memory, now=143.0)
    assert request.failure_context is not None
    assert request.failure_context.outcome_status == "failed"
    assert request.last_failed_context is None
    assert "Earlier failed attempt" not in build_prompt_payload(request).user_prompt


def test_request_carries_no_last_failed_context_when_nothing_failed():
    memory = AttemptMemory(window_sec=60.0)
    memory.record("c1", ["robot_1", "robot_2"], "reverse", None, now=0.0)
    memory.resolve("c1", "completed", now=36.0)
    request = _request_from_memory(memory, now=53.0)
    assert request.failure_context is not None
    assert request.last_failed_context is None


def test_build_failure_contexts_returns_none_pair_without_attempts():
    assert build_failure_contexts(AttemptContexts(None, None), now=10.0) == (None, None)


def test_build_reasoner_request_passes_last_failed_context_through():
    latest = FailureContext(strategy="temporary_wait", outcome_status="completed",
                            failure_detail="d")
    failed = FailureContext(strategy="yield", outcome_status="failed", failure_detail="e")
    request = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", failure_context=latest, last_failed_context=failed
    )
    assert request.last_failed_context == failed
    assert build_reasoner_request("r1", _snapshot(), "/tmp/r1.png").last_failed_context is None


def test_write_decision_artifact_round_trips_last_failed_context(tmp_path):
    request = _request_from_memory(_l4_memory(), now=182.2)
    path = write_decision_artifact(
        tmp_path,
        _ok_outcome(),
        failure_context=request.failure_context,
        last_failed_context=request.last_failed_context,
        request=request,
    )
    payload = json.loads(path.read_text())
    assert payload["last_failed_context"] == {
        "strategy": "yield",
        "yield_robot": "robot_1",
        "crossing_order": None,
        "outcome_status": "failed",
        "failure_detail": "yield failed after 122 s; congestion re-detected for the same robots",
    }
    rebuilt = build_reasoner_request(
        "r1",
        _snapshot(),
        "/tmp/r1.png",
        failure_context=FailureContext(**payload["failure_context"]),
        last_failed_context=FailureContext(**payload["last_failed_context"]),
    )
    rendered = build_prompt_payload(rebuilt).user_prompt
    assert rendered == payload["prompt"]["user_prompt"]
    assert "Earlier failed attempt in this episode:" in rendered


def test_write_decision_artifact_writes_null_last_failed_context_when_absent(tmp_path):
    payload = json.loads(write_decision_artifact(tmp_path, _ok_outcome()).read_text())
    assert payload["last_failed_context"] is None


def test_write_decision_artifact_records_run_and_session_ids(tmp_path):
    path = write_decision_artifact(tmp_path, _ok_outcome(), run_id="20260917_1101", session_id="s1")
    payload = json.loads(path.read_text())
    assert payload["run_id"] == "20260917_1101"
    assert payload["session_id"] == "s1"


def test_write_decision_artifact_nulls_measurement_fields_when_absent(tmp_path):
    payload = json.loads(write_decision_artifact(tmp_path, _ok_outcome()).read_text())
    assert payload["run_id"] is None
    assert payload["session_id"] is None
    assert payload["prompt"] is None
    assert payload["scene"] is None
    assert payload["distance_to_goal_m"] == {}
    assert payload["robot_presentation_order"] is None
    assert payload["prompt_robot_order_mode"] is None
    assert payload["prompt_robot_order_seed"] is None
    assert payload["episode_index"] is None


def test_write_decision_artifact_omits_plan_key_when_plan_channel_is_off(tmp_path):
    # Flag-off byte-identity: outcome.plan is None (every caller before the
    # (a0) plan channel existed), so the artifact gains no "plan" key at all
    # -- not even `"plan": null` -- matching the probe/probe_index pattern.
    payload = json.loads(write_decision_artifact(tmp_path, _ok_outcome()).read_text())
    assert "plan" not in payload


def test_write_decision_artifact_records_plan_dispatch_info_when_present(tmp_path):
    from swarm_orchestrator.models import PlanDispatchInfo
    from swarm_orchestrator.plan_tracker import TrackedLeg

    from reasoning.rag.command_grounder import PlanEdit

    outcome = _ok_outcome().model_copy(
        update={
            "plan": PlanDispatchInfo(
                plan_id=2,
                provenance="repaired",
                legs=(
                    TrackedLeg(robot_id="robot_1", action="yield", status="pending"),
                    TrackedLeg(robot_id="robot_2", action="cross", status="pending"),
                ),
                edits=(PlanEdit(op="swap", robot_ids=("robot_1", "robot_2"), reason="r"),),
                superseded_plan_id=1,
                cancel_order=("robot_2",),
                dispatch_matches_plan=True,
            )
        }
    )
    payload = json.loads(write_decision_artifact(tmp_path, outcome).read_text())
    assert payload["plan"]["plan_id"] == 2
    assert payload["plan"]["provenance"] == "repaired"
    assert payload["plan"]["superseded_plan_id"] == 1
    assert payload["plan"]["cancel_order"] == ["robot_2"]
    assert payload["plan"]["edits"][0]["op"] == "swap"
    assert payload["plan"]["legs"][0] == {
        "robot_id": "robot_1",
        "action": "yield",
        "status": "pending",
    }
    assert payload["plan"]["dispatch_matches_plan"] is True
    assert payload["plan"]["plan_held"] is False


def test_write_decision_artifact_records_a_held_plan(tmp_path):
    # Hold semantics (ruling 2026-10-02): a re-affirmed plan's artifact
    # records plan_held: true alongside the UNCHANGED active plan_id.
    from swarm_orchestrator.models import PlanDispatchInfo
    from swarm_orchestrator.plan_tracker import TrackedLeg

    outcome = _ok_outcome().model_copy(
        update={
            "plan": PlanDispatchInfo(
                plan_id=1,
                provenance="vlm_verbatim",
                legs=(TrackedLeg(robot_id="robot_1", action="yield", status="active"),),
                dispatch_matches_plan=True,
                plan_held=True,
            )
        }
    )
    payload = json.loads(write_decision_artifact(tmp_path, outcome).read_text())
    assert payload["plan"]["plan_held"] is True
    assert payload["plan"]["plan_id"] == 1
    assert payload["plan"]["superseded_plan_id"] is None


def test_write_decision_artifact_records_presentation_order_provenance(tmp_path):
    request = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", robot_presentation_order="id_desc"
    )
    path = write_decision_artifact(
        tmp_path,
        _ok_outcome(),
        request=request,
        prompt_robot_order_mode="random",
        prompt_robot_order_seed=4242,
        episode_index=3,
    )
    payload = json.loads(path.read_text())

    assert payload["robot_presentation_order"] == "id_desc"
    assert payload["prompt_robot_order_mode"] == "random"
    assert payload["prompt_robot_order_seed"] == 4242
    assert payload["episode_index"] == 3


def test_write_decision_artifact_records_the_order_the_prompt_rendered(tmp_path):
    # The effective order is read off the request, not the caller's argument, so
    # the artifact can never disagree with the prompt whose hashes sit beside it.
    request = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", robot_presentation_order="id_asc"
    )
    payload = json.loads(
        write_decision_artifact(
            tmp_path, _ok_outcome(), request=request, prompt_robot_order_mode="random"
        ).read_text()
    )

    assert payload["robot_presentation_order"] == "id_asc"


# A blocker parked behind each corridor mouth, boxing in whichever robot would
# have to retreat past it. Mirrors the head-on asymmetric family fixtures.
_WEST_BLOCKER = StaticObstacleInput(
    obstacle_id="obstacle_1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3
)
_EAST_BLOCKER = StaticObstacleInput(
    obstacle_id="obstacle_2", x=1.85, y=0.0, size_x_m=0.3, size_y_m=0.3
)


def _gated_yield_command(mode, obstacles):
    """Ground a head-on yield through M3's feasibility gate, as the pipeline does."""
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on aisle conflict",
        strategy="yield",
        justification="both robots are stopped in opposing directions",
        yield_robot="robot_1",
    )
    result = ReasonerResult(
        request_id="r1",
        decision=decision,
        raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="r1", backend_id="openai", attempts=1, parse_status="valid"
        ),
    )
    return ground_reasoner_result(
        result,
        robot_positions={"robot_1": (-0.3, 0.0), "robot_2": (0.3, 0.0)},
        geometry=SceneGeometry(
            corridor=CorridorGeometry(
                axis="x",
                center_m=0.0,
                half_length_m=1.0,
                aisle_half_width_m=0.6,
                occluder_height_m=0.9,
            )
        ),
        static_obstacles=obstacles,
        yield_feasibility_mode=mode,
    )


def _yield_artifact(command, tmp_path, **kwargs):
    outcome = PipelineOutcome(
        request_id="r1",
        reasoner_result=_ok_outcome().reasoner_result,
        grounded_command=command,
        # A cycle only reaches OK once grounding returned a command that passed
        # validation, so a missing command pairs with the GROUNDING stage.
        terminal_stage=TerminalStage.OK if command is not None else TerminalStage.GROUNDING,
    )
    return json.loads(write_decision_artifact(tmp_path, outcome, **kwargs).read_text())


def test_write_decision_artifact_records_a_swapped_yielder(tmp_path):
    payload = _yield_artifact(_gated_yield_command("swap", (_WEST_BLOCKER,)), tmp_path)

    assert payload["yield_robot_grounded_from"] == "robot_1"
    assert payload["yield_regrounded_reason"].startswith("yield re-grounded:")
    assert payload["yield_refusal_reason"] is None


def test_write_decision_artifact_records_a_refused_yield(tmp_path):
    payload = _yield_artifact(_gated_yield_command("refuse", (_WEST_BLOCKER,)), tmp_path)

    assert payload["yield_refusal_reason"].startswith("yield refused:")
    assert payload["yield_robot_grounded_from"] is None
    assert payload["yield_regrounded_reason"] is None


def test_write_decision_artifact_nulls_yield_provenance_when_the_gate_is_off(tmp_path):
    # A yield that grounded normally still carries a `reason` (the M2 root
    # cause), so a presence check rather than a prefix check would false-positive.
    payload = _yield_artifact(_gated_yield_command("off", (_WEST_BLOCKER,)), tmp_path)

    assert payload["yield_robot_grounded_from"] is None
    assert payload["yield_regrounded_reason"] is None
    assert payload["yield_refusal_reason"] is None


def test_write_decision_artifact_records_the_configured_feasibility_mode(tmp_path):
    # Recorded from config, so an artifact set stays partitionable by condition
    # even across the cycles where the gate never fired.
    payload = _yield_artifact(
        _gated_yield_command("swap", ()), tmp_path, grounding_yield_feasibility="swap"
    )

    assert payload["grounding_yield_feasibility"] == "swap"
    assert payload["yield_robot_grounded_from"] is None


def test_write_decision_artifact_nulls_yield_provenance_without_a_grounded_command(tmp_path):
    payload = _yield_artifact(None, tmp_path)

    assert payload["grounded_command_present"] is False
    assert payload["yield_robot_grounded_from"] is None
    assert payload["yield_refusal_reason"] is None
    assert payload["grounding_yield_feasibility"] is None


def test_summarize_yield_grounding_names_both_ends_of_a_swap():
    # Drives the M5 "yield re-grounded request=... from=... to=..." log line.
    provenance = summarize_yield_grounding(_gated_yield_command("swap", (_WEST_BLOCKER,)))

    assert provenance.grounded_from == "robot_1"
    assert provenance.grounded_to == "robot_2"
    assert provenance.refusal_reason is None


def test_summarize_yield_grounding_names_only_the_target_when_no_swap_happened():
    # The east blocker boxes in robot_2, not the decided yielder, so the yield
    # stays put: a target but no provenance.
    provenance = summarize_yield_grounding(_gated_yield_command("swap", (_EAST_BLOCKER,)))

    assert provenance.grounded_to == "robot_1"
    assert provenance.grounded_from is None


def test_summarize_yield_grounding_reports_a_refusal_without_a_yield_target():
    # Drives the M5 "yield refused request=... reason=..." log line. A refusal
    # fans out temporary_wait to everyone, so there is no yield action to name.
    provenance = summarize_yield_grounding(_gated_yield_command("refuse", (_WEST_BLOCKER,)))

    assert provenance.refusal_reason.startswith("yield refused:")
    assert provenance.grounded_to is None
    assert provenance.grounded_from is None


def test_summarize_yield_grounding_is_all_none_without_a_command():
    assert summarize_yield_grounding(None) == (None, None, None, None)


def test_write_decision_artifact_records_rendered_prompt_with_hashes(tmp_path):
    import hashlib

    request = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png")
    path = write_decision_artifact(tmp_path, _ok_outcome(), request=request)
    payload = json.loads(path.read_text())
    expected = build_prompt_payload(request)
    assert payload["prompt"]["user_prompt"] == expected.user_prompt
    assert payload["prompt"]["system_prompt"] == expected.system_prompt
    assert payload["prompt"]["user_sha256"] == (
        hashlib.sha256(expected.user_prompt.encode()).hexdigest()
    )
    assert payload["prompt"]["system_sha256"] == (
        hashlib.sha256(expected.system_prompt.encode()).hexdigest()
    )


def test_write_decision_artifact_records_scene_snapshot_and_distances(tmp_path):
    path = write_decision_artifact(
        tmp_path, _ok_outcome(), snapshot=_snapshot(), distance_to_goal_m={"robot_0": 1.5}
    )
    payload = json.loads(path.read_text())
    assert payload["scene"]["stamp"] == 5.0
    assert payload["scene"]["robots"][0]["robot_id"] == "robot_0"
    assert payload["distance_to_goal_m"] == {"robot_0": 1.5}


def test_append_scene_log_appends_one_json_line_per_call(tmp_path):
    path = tmp_path / "s1.jsonl"
    append_scene_log(path, _snapshot(), session_id="s1", run_id=None, now=10.0)
    append_scene_log(path, _snapshot(), session_id="s1", run_id="20260917_1101", now=11.0)
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert [line["t"] for line in lines] == [10.0, 11.0]
    assert lines[0]["session_id"] == "s1"
    assert lines[0]["run_id"] is None
    assert lines[1]["run_id"] == "20260917_1101"
    assert lines[0]["scene"]["frame_id"] == "cam0"


def _grounded_stub() -> dict:
    return {
        "command_id": "c1",
        "actions": [{"robot_id": "robot_0", "action": "yield"}],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }


def test_pipeline_passes_yield_feasibility_settings_to_grounder():
    seen: dict[str, object] = {}

    def _record(result, robot_positions=None, geometry=None, **gate):
        seen.update(gate)
        return _grounded_stub()

    obstacles = (
        StaticObstacleInput(obstacle_id="obstacle_1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3),
    )
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_ok_result()),
        ground_fn=_record,
        static_obstacles=obstacles,
        yield_feasibility_mode="swap",
    )

    pipe.run(_request())

    assert seen["static_obstacles"] == obstacles
    assert seen["yield_feasibility_mode"] == "swap"


def test_pipeline_yield_feasibility_defaults_to_off_and_no_obstacles():
    seen: dict[str, object] = {}

    def _record(result, robot_positions=None, geometry=None, **gate):
        seen.update(gate)
        return _grounded_stub()

    pipe = InProcessPipeline(reasoner=_FakeReasoner(_ok_result()), ground_fn=_record)

    pipe.run(_request())

    assert seen["static_obstacles"] == ()
    assert seen["yield_feasibility_mode"] == "off"


# ---- effective reasoner sampling config ----

_DECISION_JSON = (
    '{"congestion_detected": true, "type": "deadlock", '
    '"involved_robots": ["robot_0"], "root_cause": "head-on", '
    '"strategy": "yield", "justification": "both stopped"}'
)


def _shipped_vlm() -> dict:
    return yaml.safe_load(Path("config/models.yaml").read_text())["vlm"]


def _artifact_for(backend, backend_id: str, backend_config, tmp_path) -> dict:
    """Run one reasoning pass through M2 and return the artifact M5 writes for it."""
    image = tmp_path / "frame.png"
    image.write_bytes(b"png")
    config = resolve_reasoner_config(_shipped_vlm(), backend_id)
    result = Reasoner(
        backend, config, describe_effective_sampling(config, backend_config)
    ).run(
        build_reasoner_request(
            request_id="r1", snapshot=_snapshot(), image_path=str(image)
        )
    )
    outcome = PipelineOutcome(
        request_id="r1",
        reasoner_result=result,
        grounded_command=None,
        terminal_stage=TerminalStage.VLM,
        failure_reason=None,
    )
    return json.loads(write_decision_artifact(tmp_path, outcome).read_text())


def test_write_decision_artifact_records_shipped_openai_sampling_config(tmp_path):
    payload = _artifact_for(
        MockBackend(response_text=_DECISION_JSON),
        "openai",
        OpenAIBackendConfig(**backend_section(_shipped_vlm(), "openai")),
        tmp_path,
    )
    effective = payload["reasoner_config_effective"]
    assert effective["backend_id"] == "openai"
    assert effective["model_id"] == "gpt-4o-2024-08-06"
    assert effective["temperature"] == 0.0
    assert effective["max_attempts"] == 4
    assert effective["image_fallback_after_attempts"] == 2
    assert effective["max_tokens"] == 2048
    assert effective["unsupported_sampling"] is None


def test_write_decision_artifact_records_shipped_gemini_sampling_config(tmp_path):
    class UnsupportedSamplingBackend:
        def analyze(self, payload, config):
            return BackendResponse(
                text=_DECISION_JSON,
                backend_id="gemini-robotics-er-2-preview",
                raw={"unsupported_sampling": {"temperature": 0.6, "top_p": 0.95}},
            )

    payload = _artifact_for(
        UnsupportedSamplingBackend(),
        "gemini",
        GeminiBackendConfig(**backend_section(_shipped_vlm(), "gemini")),
        tmp_path,
    )
    effective = payload["reasoner_config_effective"]
    assert effective["thinking_level"] == "low"
    assert effective["model_id"] == "gemini-robotics-er-2-preview"
    # No per-backend override, so the shared reasoner block's Cosmos preset is
    # what was configured — recorded even though the API drops it.
    assert effective["temperature"] == 0.6
    assert effective["image_fallback_after_attempts"] is None
    assert effective["unsupported_sampling"] == {"temperature": 0.6, "top_p": 0.95}


def test_write_decision_artifact_records_served_model_next_to_configured_alias(tmp_path):
    class ServedSnapshotBackend:
        def analyze(self, payload, config):
            return BackendResponse(
                text=_DECISION_JSON, backend_id="gpt-4o", served_model="gpt-4o-2024-08-06"
            )

    payload = _artifact_for(
        ServedSnapshotBackend(),
        "openai",
        OpenAIBackendConfig(**backend_section(_shipped_vlm(), "openai")),
        tmp_path,
    )
    assert payload["reasoner_config_effective"]["model_id"] == "gpt-4o-2024-08-06"
    assert payload["reasoner_config_effective"]["served_model"] == "gpt-4o-2024-08-06"
    assert payload["diagnostics"]["served_model"] == "gpt-4o-2024-08-06"


def test_write_decision_artifact_served_model_is_null_when_backend_reports_none(tmp_path):
    payload = _artifact_for(
        MockBackend(response_text=_DECISION_JSON),
        "openai",
        OpenAIBackendConfig(**backend_section(_shipped_vlm(), "openai")),
        tmp_path,
    )
    assert payload["reasoner_config_effective"]["served_model"] is None


def test_write_decision_artifact_sampling_config_is_null_when_undescribed(tmp_path):
    outcome = PipelineOutcome(
        request_id="r1",
        reasoner_result=ReasonerResult(
            request_id="r1",
            decision=None,
            raw_text=None,
            diagnostics=ReasonerDiagnostics(
                request_id="r1", backend_id="mock", attempts=1, parse_status="failed"
            ),
        ),
        grounded_command=None,
        terminal_stage=TerminalStage.VLM,
        failure_reason="decision=None",
    )
    payload = json.loads(write_decision_artifact(tmp_path, outcome).read_text())
    assert payload["reasoner_config_effective"] is None


# ---- raw camera frame dumps ----

def test_raw_frame_dump_path_sits_beside_the_annotated_dump():
    assert raw_frame_dump_path("data/logs/m5_frames", "r1") == Path(
        "data/logs/m5_frames/r1_raw.png"
    )


def test_raw_frame_skew_sec_is_positive_when_the_raw_frame_is_newer():
    assert raw_frame_skew_sec(10.25, 10.0) == pytest.approx(0.25)


def test_raw_frame_skew_sec_is_negative_when_the_raw_frame_lags():
    assert raw_frame_skew_sec(9.75, 10.0) == pytest.approx(-0.25)


def test_latest_raw_frame_returns_none_before_any_frame_arrives():
    assert LatestRawFrame().latest() is None


def test_latest_raw_frame_keeps_only_the_newest_frame():
    holder = LatestRawFrame()
    holder.update(np.zeros((2, 2, 3), dtype=np.uint8), 1.0)
    holder.update(np.ones((2, 2, 3), dtype=np.uint8), 2.0)

    frame, stamp = holder.latest()
    assert stamp == 2.0
    assert frame[0, 0].tolist() == [1, 1, 1]


def test_latest_raw_frame_accepts_an_out_of_order_frame_as_the_newest():
    # Best-effort, depth-1: nothing reorders, so a late frame simply replaces.
    holder = LatestRawFrame()
    holder.update(np.zeros((2, 2, 3), dtype=np.uint8), 5.0)
    holder.update(np.ones((2, 2, 3), dtype=np.uint8), 4.0)

    _frame, stamp = holder.latest()
    assert stamp == 4.0


# ---- T0 log-only probe (stage-1 only) ----


class _CountingReasoner:
    def __init__(self, result):
        self._result = result
        self.calls = 0

    def run(self, request):
        self.calls += 1
        return self._result


def test_pipeline_analyze_never_grounds_congestion_decision():
    reasoner = _CountingReasoner(_ok_result())
    pipe = InProcessPipeline(reasoner=reasoner, ground_fn=_must_not_ground)

    outcome = pipe.analyze(_request())

    assert reasoner.calls == 1
    assert outcome.terminal_stage is TerminalStage.PROBE
    assert outcome.grounded_command is None
    assert outcome.reasoner_result.decision.congestion_detected is True


def test_pipeline_analyze_records_no_congestion_decision_as_probe():
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_no_congestion_result()), ground_fn=_must_not_ground
    )
    outcome = pipe.analyze(_request())
    assert outcome.terminal_stage is TerminalStage.PROBE
    assert outcome.failure_reason is None


def test_pipeline_analyze_vlm_failure_terminates_at_vlm():
    pipe = InProcessPipeline(reasoner=_FakeReasoner(_failed_result()), ground_fn=_must_not_ground)
    outcome = pipe.analyze(_request())
    assert outcome.terminal_stage is TerminalStage.VLM
    assert outcome.failure_reason == "decision=None"


def test_pipeline_analyze_reasoner_exception_terminates_at_vlm_without_raising():
    pipe = InProcessPipeline(reasoner=_RaisingReasoner(), ground_fn=_must_not_ground)
    outcome = pipe.analyze(_request())
    assert outcome.terminal_stage is TerminalStage.VLM
    assert "backend exploded" in outcome.failure_reason


def _probe_outcome():
    return PipelineOutcome(
        request_id="r1",
        reasoner_result=_ok_result(),
        grounded_command=None,
        terminal_stage=TerminalStage.PROBE,
    )


# The artifact keys every analysis wrote before T0 probes existed; probe mode
# off must leave this set, and so every existing artifact, unchanged.
_PRE_PROBE_ARTIFACT_KEYS = {
    "request_id", "run_id", "session_id", "terminal_stage", "failure_reason",
    "grounded_command_present", "decision", "diagnostics", "reasoner_config_effective",
    "raw_text", "failure_context", "last_failed_context", "prompt",
    "robot_presentation_order", "prompt_robot_order_mode", "prompt_robot_order_seed",
    "episode_index", "grounding_yield_feasibility", "yield_robot_grounded_from",
    "yield_regrounded_reason", "yield_refusal_reason", "scene", "distance_to_goal_m",
    "shadow_classical",
}
# The prompt-v2 bundle (2026-09-27) adds `prompt_version` to every artifact on
# purpose; the probe invariant above is about probe keys only. The derived
# grounding wiring (2026-09-28) likewise adds the grounding mode, its params
# source, the command's degradations and the stage-2 record to every artifact.
_TRIGGERED_ARTIFACT_KEYS = _PRE_PROBE_ARTIFACT_KEYS | {
    "prompt_version",
    "grounding_mode",
    "grounding_params_source",
    "grounding_degradations",
    "stage2",
}


def test_write_decision_artifact_omits_probe_keys_for_triggered_analysis(tmp_path):
    payload = json.loads(write_decision_artifact(tmp_path, _probe_outcome()).read_text())
    assert set(payload) == _TRIGGERED_ARTIFACT_KEYS


def test_write_decision_artifact_marks_probe_and_would_be_decision(tmp_path):
    payload = json.loads(
        write_decision_artifact(
            tmp_path, _probe_outcome(), request=_request(), probe_index=3
        ).read_text()
    )
    assert payload["probe"] is True
    assert payload["probe_index"] == 3
    assert payload["terminal_stage"] == "probe"
    assert payload["grounded_command_present"] is False
    assert payload["decision"]["congestion_detected"] is True
    assert payload["decision"]["strategy"] == "yield"
    assert set(payload) == _TRIGGERED_ARTIFACT_KEYS | {"probe", "probe_index"}

"""R3.3 arm `dispatch-model-order-when-verified` (prereg-v3 rev 3, 2026-10-07).

`plan_dispatch_order_source` chooses where a `junction_clear` resolution's
RECEDE dispatch order comes from: `"chi"` (default, the inherited
behaviour) always dispatches `rank_recede_candidates`' chi order;
`"model_when_verified"` dispatches the model's own `proposed_plan` recede
order when, and only when, that plan verified `vlm_verbatim`. The recede SET,
the pockets (chi-rank), the cross phase and the release order are the same
in both modes.

The default-mode zero-delta check compares against goldens written by the
PRE-change code (`data/dispatch_order/junction_default_payloads.json`,
generated at a823aeb from `_default_payloads` below before any edit): with
the two new artifact keys stripped, every byte must match.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import OrchestratorConfig, RobotView, SceneSnapshot, TaskAssignment
from swarm_orchestrator.plan_tracker import PlanTracker
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    build_reasoner_request,
    registry_dispatch,
    write_decision_artifact,
)
from swarm_orchestrator.retreat_stage2 import snapshot_frame_from_request

from reasoning.rag.command_grounder import ground_junction_clear_phases, ground_reasoner_result
from reasoning.rag.maneuver_geometry import (
    GroundingParams,
    rank_recede_candidates,
    recede_distance_m,
    recede_pocket_offset_m,
)
from reasoning.rag.scene_geometry import ArmGeometry, CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
)

_GOLDEN = Path(__file__).parent / "data" / "dispatch_order" / "junction_default_payloads.json"
_NEW_ARTIFACT_KEYS = ("dispatch_order_source", "plan_dispatch_order_source")

# IB10 four-way standoff (the same fixture `test_m5_reasoning_pipeline`'s
# junction_clear tests use): chi ranks robot_4 (0.9227) before robot_3
# (0.9417), a 0.019 margin -- inside the default epsilon 0.15.
_STANDOFF = {
    "robot_1": (-0.2192, -0.0014),
    "robot_2": (0.33, 0.0158),
    "robot_3": (-0.0208, -0.2583),
    "robot_4": (0.0045, 0.2773),
}
_ARMS = {
    "robot_1": ArmGeometry(axis="x", side=-1),
    "robot_2": ArmGeometry(axis="x", side=1),
    "robot_3": ArmGeometry(axis="y", side=-1),
    "robot_4": ArmGeometry(axis="y", side=1),
}
_CHI_ORDER = ["robot_4", "robot_3"]
_MODEL_ORDER = ["robot_3", "robot_4"]
_SWAPPED_PLAN = [
    ProposedPlanLeg(robot_id="robot_3", action="reverse"),
    ProposedPlanLeg(robot_id="robot_4", action="reverse"),
    ProposedPlanLeg(robot_id="robot_1", action="yield"),
    ProposedPlanLeg(robot_id="robot_2", action="cross"),
]
_CHI_PLAN = [
    ProposedPlanLeg(robot_id="robot_4", action="reverse"),
    ProposedPlanLeg(robot_id="robot_3", action="reverse"),
    ProposedPlanLeg(robot_id="robot_1", action="yield"),
    ProposedPlanLeg(robot_id="robot_2", action="cross"),
]


class _FakeReasoner:
    def __init__(self, result: ReasonerResult) -> None:
        self._result = result

    def run(self, request: ReasonerRequest) -> ReasonerResult:
        return self._result


def _geometry(stagger_m: float | None = None) -> SceneGeometry:
    corridor = CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.6, aisle_half_width_m=0.6, occluder_height_m=0.0
    )
    return SceneGeometry(
        corridor=corridor,
        arms=_ARMS,
        junction_recede_offset_m=1.2,
        junction_backup_clearance_m=1.1,
        junction_recede_stagger_m=stagger_m,
    )


def _request() -> ReasonerRequest:
    snapshot = SceneSnapshot(
        stamp=1.0,
        frame_id="cam0",
        robots=[
            RobotView(
                robot_id=rid, x=xy[0], y=xy[1], theta=0.0, linear_velocity=0.0,
                status="STOPPED", stamp=1.0,
            )
            for rid, xy in _STANDOFF.items()
        ],
        dropped_frame=False,
    )
    return build_reasoner_request(request_id="r1", snapshot=snapshot, image_path="/tmp/r1.png")


def _result(plan: list[ProposedPlanLeg] | None = None) -> ReasonerResult:
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=list(_STANDOFF),
        root_cause="four-way standoff",
        strategy="junction_clear",
        justification="jam",
        proposed_plan=plan,
    )
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)


def _pipeline(
    result: ReasonerResult,
    *,
    params: GroundingParams | None = None,
    geometry: SceneGeometry | None = None,
    **kwargs: Any,
) -> InProcessPipeline:
    return InProcessPipeline(
        reasoner=_FakeReasoner(result),
        ground_fn=ground_reasoner_result,
        grounding_params=params or GroundingParams(mode="derived"),
        scene_geometry=geometry or _geometry(),
        plan_tracker=PlanTracker(),
        **kwargs,
    )


def _payload(outcome: Any, request: ReasonerRequest, tmp_dir: Path, **kwargs: Any) -> dict:
    dispatch = registry_dispatch(outcome, set(_STANDOFF))
    path = write_decision_artifact(
        tmp_dir,
        outcome,
        request=request,
        grounding_yield_feasibility="off",
        dispatch=dispatch,
        **kwargs,
    )
    return json.loads(path.read_text(encoding="utf-8"))


_GOLDEN_CASES: dict[str, tuple[list[ProposedPlanLeg] | None, float | None]] = {
    "plan_absent": (None, None),
    "plan_within_epsilon_swapped": (_SWAPPED_PLAN, None),
    "plan_within_epsilon_swapped_staggered": (_SWAPPED_PLAN, 0.1),
}


def _default_payloads(
    tmp_dir: Path, pipeline_kwargs: dict[str, Any], artifact_kwargs: dict[str, Any]
) -> dict[str, dict]:
    payloads = {}
    for name, (plan, stagger_m) in _GOLDEN_CASES.items():
        request = _request()
        outcome = _pipeline(_result(plan), geometry=_geometry(stagger_m), **pipeline_kwargs).run(
            request
        )
        payloads[name] = _payload(outcome, request, tmp_dir / name, **artifact_kwargs)
    return payloads


def _receders(outcome: Any) -> list[str]:
    return [
        phase.robot_id for phase in outcome.junction_phases.phases if phase.label == "recede"
    ]


def _reverse_actor(command: dict) -> str:
    (actor,) = [a["robot_id"] for a in command["actions"] if a["action"] == "reverse"]
    return actor


# ---- (1) default mode: byte-identical to the pre-change code ----


@pytest.mark.parametrize("pipeline_kwargs", [{}, {"dispatch_order_source": "chi"}])
def test_default_mode_payload_is_byte_identical_to_pre_change_golden(tmp_path, pipeline_kwargs):
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    payloads = _default_payloads(
        tmp_path, pipeline_kwargs, {"plan_dispatch_order_source": "chi"}
    )
    assert set(payloads) == set(golden)
    for name, payload in payloads.items():
        stripped = {k: v for k, v in payload.items() if k not in _NEW_ARTIFACT_KEYS}
        expected = json.dumps(golden[name], sort_keys=True)
        assert json.dumps(stripped, sort_keys=True) == expected, name


def test_default_mode_artifact_records_chi_source_and_configured_mode(tmp_path):
    payloads = _default_payloads(tmp_path, {}, {"plan_dispatch_order_source": "chi"})
    for payload in payloads.values():
        assert payload["dispatch_order_source"] == "chi"
        assert payload["plan_dispatch_order_source"] == "chi"


def test_default_mode_within_epsilon_plan_still_dispatches_chi_order():
    outcome = _pipeline(_result(_SWAPPED_PLAN)).run(_request())
    assert outcome.dispatch_order_source == "chi"
    assert _receders(outcome) == _CHI_ORDER
    assert _reverse_actor(outcome.grounded_command) == _CHI_ORDER[0]
    assert outcome.plan.order_equivalent is True


def test_grounder_recede_order_none_is_identical_to_omitting_it():
    request = _request()
    frame = snapshot_frame_from_request(request)
    kwargs = dict(snapshot=frame, params=GroundingParams(mode="derived"), geometry=_geometry(0.1))
    assert ground_junction_clear_phases(
        _result(), recede_order=None, **kwargs
    ) == ground_junction_clear_phases(_result(), **kwargs)


# ---- (2) model_when_verified + verified plan: model order dispatched ----


def test_model_mode_verified_within_epsilon_plan_dispatches_model_order():
    outcome = _pipeline(
        _result(_SWAPPED_PLAN), dispatch_order_source="model_when_verified"
    ).run(_request())
    assert outcome.plan.provenance == "vlm_verbatim"
    assert outcome.dispatch_order_source == "model"
    assert _receders(outcome) == _MODEL_ORDER
    reverse_order = [
        _reverse_actor(phase.command)
        for phase in outcome.junction_phases.phases
        if phase.label == "recede"
    ]
    assert reverse_order == _MODEL_ORDER


def test_model_mode_dispatched_command_is_the_model_ordered_first_phase():
    # `grounded_command` IS what M5 dispatches (the queue's own phase 0 is
    # discarded), so it must be re-seated on the model-ordered phase 0.
    outcome = _pipeline(
        _result(_SWAPPED_PLAN), dispatch_order_source="model_when_verified"
    ).run(_request())
    first = outcome.junction_phases.phases[0].command
    assert outcome.grounded_command["command_id"] == first["command_id"]
    assert _reverse_actor(outcome.grounded_command) == _MODEL_ORDER[0]


def test_model_mode_keeps_order_equivalent_measured_against_chi():
    # R3.3 stratifies A vs B by `order_equivalent`; under B it must still say
    # "the model's order differs from chi within epsilon", not "differs
    # from what was dispatched" (which is then never true).
    outcome = _pipeline(
        _result(_SWAPPED_PLAN), dispatch_order_source="model_when_verified"
    ).run(_request())
    assert outcome.plan.order_equivalent is True
    assert outcome.plan.dispatch_matches_plan is True


def test_model_mode_chi_ordered_plan_is_model_source_and_not_order_equivalent():
    outcome = _pipeline(
        _result(_CHI_PLAN), dispatch_order_source="model_when_verified"
    ).run(_request())
    assert outcome.dispatch_order_source == "model"
    assert _receders(outcome) == _CHI_ORDER
    assert outcome.plan.order_equivalent is False


def test_model_mode_artifact_records_model_source_consistent_with_junction_phases(tmp_path):
    request = _request()
    outcome = _pipeline(
        _result(_SWAPPED_PLAN), dispatch_order_source="model_when_verified"
    ).run(request)
    payload = _payload(
        outcome, request, tmp_path, plan_dispatch_order_source="model_when_verified"
    )
    assert payload["dispatch_order_source"] == "model"
    assert payload["plan_dispatch_order_source"] == "model_when_verified"
    phases = payload["junction_phases"]["phases"]
    recorded = [p["robot_id"] for p in phases if p["label"] == "recede"]
    assert recorded == _MODEL_ORDER
    assert _reverse_actor(payload["dispatched_command"]) == _MODEL_ORDER[0]


def test_model_mode_release_order_stays_chi():
    outcome = _pipeline(
        _result(_SWAPPED_PLAN), dispatch_order_source="model_when_verified"
    ).run(_request())
    release = outcome.junction_phases.phases[-1]
    assert release.label == "release"
    held = [a["robot_id"] for a in release.command["actions"]]
    # chi lead (robot_4) is released first, so it is addressed by no action.
    assert _CHI_ORDER[0] not in held
    yielder_action = next(a for a in release.command["actions"] if a["robot_id"] == "robot_1")
    assert yielder_action["parameters"]["crossing_order"] == _CHI_ORDER
    assert yielder_action["parameters"]["passer_robot_id"] == _CHI_ORDER[0]


def test_model_mode_cross_and_fallback_are_identical_to_chi_mode():
    chi = _pipeline(_result(_SWAPPED_PLAN), geometry=_geometry(0.1)).run(_request())
    model = _pipeline(
        _result(_SWAPPED_PLAN),
        geometry=_geometry(0.1),
        dispatch_order_source="model_when_verified",
    ).run(_request())
    assert chi.junction_phases.phases[2:] == model.junction_phases.phases[2:]
    assert chi.junction_phases.fallback_command == model.junction_phases.fallback_command
    assert (
        chi.junction_phases.fallback_held_robot_ids
        == model.junction_phases.fallback_held_robot_ids
    )


# ---- (3) model_when_verified + plan failing verification: chi ----


def test_model_mode_order_outside_epsilon_falls_back_to_chi():
    # epsilon below the 0.019 chi margin: the swapped order is a verification
    # problem, reorder-repaired, so the recede order is M3's, not the model's.
    params = GroundingParams(mode="derived", junction_recede_order_epsilon=0.01)
    outcome = _pipeline(
        _result(_SWAPPED_PLAN), params=params, dispatch_order_source="model_when_verified"
    ).run(_request())
    assert outcome.plan.provenance == "repaired"
    assert outcome.dispatch_order_source == "chi"
    assert _receders(outcome) == _CHI_ORDER
    assert _reverse_actor(outcome.grounded_command) == _CHI_ORDER[0]


def test_model_mode_wrong_recede_set_falls_back_to_chi():
    plan = [
        ProposedPlanLeg(robot_id="robot_1", action="reverse"),
        ProposedPlanLeg(robot_id="robot_3", action="reverse"),
        ProposedPlanLeg(robot_id="robot_4", action="yield"),
        ProposedPlanLeg(robot_id="robot_2", action="cross"),
    ]
    outcome = _pipeline(_result(plan), dispatch_order_source="model_when_verified").run(
        _request()
    )
    assert outcome.plan.provenance != "vlm_verbatim"
    assert outcome.dispatch_order_source == "chi"
    assert _receders(outcome) == _CHI_ORDER


# ---- (4) model_when_verified + m3_default provenance: chi ----


def test_model_mode_absent_plan_m3_default_dispatches_chi():
    outcome = _pipeline(_result(None), dispatch_order_source="model_when_verified").run(
        _request()
    )
    assert outcome.plan.provenance == "m3_default"
    assert outcome.dispatch_order_source == "chi"
    assert _receders(outcome) == _CHI_ORDER


def test_model_mode_inconsistent_plan_m3_default_dispatches_chi():
    plan = [ProposedPlanLeg(robot_id=rid, action="wait") for rid in _STANDOFF]
    outcome = _pipeline(_result(plan), dispatch_order_source="model_when_verified").run(
        _request()
    )
    assert outcome.plan.provenance == "m3_default"
    assert outcome.dispatch_order_source == "chi"
    assert _receders(outcome) == _CHI_ORDER


# ---- (5) pocket invariant: pockets stay chi-rank under model order ----


def test_model_mode_pockets_stay_chi_rank_with_a_declared_stagger():
    geometry = _geometry(0.1)
    request = _request()
    frame = snapshot_frame_from_request(request)
    params = GroundingParams(mode="derived")
    chi_rank = {
        rid: rank
        for rank, rid in enumerate(
            rank_recede_candidates(frame, ["robot_3", "robot_4"], geometry, params)
        )
    }
    outcome = _pipeline(
        _result(_SWAPPED_PLAN), geometry=geometry, dispatch_order_source="model_when_verified"
    ).run(request)
    assert _receders(outcome) == _MODEL_ORDER
    for phase in outcome.junction_phases.phases:
        if phase.label != "recede":
            continue
        (action,) = [a for a in phase.command["actions"] if a["action"] == "reverse"]
        expected = recede_distance_m(
            frame,
            phase.robot_id,
            geometry,
            offset_m=recede_pocket_offset_m(geometry, chi_rank[phase.robot_id]),
        )
        assert action["parameters"]["backup_distance_m"] == expected
    # Not vacuous: the stagger makes the two ranks' pockets differ.
    assert recede_pocket_offset_m(geometry, 0) != recede_pocket_offset_m(geometry, 1)


def test_model_mode_recede_commands_equal_chi_mode_up_to_order():
    chi = _pipeline(_result(_SWAPPED_PLAN), geometry=_geometry(0.1)).run(_request())
    model = _pipeline(
        _result(_SWAPPED_PLAN),
        geometry=_geometry(0.1),
        dispatch_order_source="model_when_verified",
    ).run(_request())
    chi_recedes = {p.robot_id: p for p in chi.junction_phases.phases if p.label == "recede"}
    model_recedes = {p.robot_id: p for p in model.junction_phases.phases if p.label == "recede"}
    assert chi_recedes == model_recedes


# ---- grounder-level guard and config ----


def test_grounder_rejects_a_recede_order_that_is_not_a_permutation_of_chi():
    request = _request()
    frame = snapshot_frame_from_request(request)
    with pytest.raises(ValueError, match="permutation"):
        ground_junction_clear_phases(
            _result(),
            snapshot=frame,
            params=GroundingParams(mode="derived"),
            geometry=_geometry(),
            recede_order=["robot_3"],
        )


def test_pipeline_rejects_an_unknown_dispatch_order_source():
    with pytest.raises(ValueError, match="dispatch_order_source"):
        _pipeline(_result(), dispatch_order_source="model")


def _config(**overrides: Any) -> OrchestratorConfig:
    base: dict[str, Any] = dict(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={"robot_0": TaskAssignment(task="t", goal=(0.0, 0.0))},
        frame_dump_dir="data/logs/m5_frames",
    )
    return OrchestratorConfig(**{**base, **overrides})


def test_config_dispatch_order_source_defaults_to_chi():
    assert _config().plan_dispatch_order_source == "chi"


def test_config_model_when_verified_requires_the_plan_channel():
    with pytest.raises(ValidationError, match="plan_channel_enabled"):
        _config(plan_dispatch_order_source="model_when_verified")
    assert (
        _config(
            plan_dispatch_order_source="model_when_verified", plan_channel_enabled=True
        ).plan_dispatch_order_source
        == "model_when_verified"
    )


def test_config_rejects_an_unknown_dispatch_order_source():
    with pytest.raises(ValidationError):
        _config(plan_dispatch_order_source="model")


def test_shipped_orchestrator_yaml_declares_chi():
    import yaml

    path = (
        Path(__file__).resolve().parents[2]
        / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
    )
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["plan_dispatch_order_source"] == "chi"


def test_model_mode_without_a_recede_sequence_records_chi(tmp_path):
    # No declared pocket: the plain-yield fallback, no recede phases at all,
    # so nothing for the model's order to reorder.
    no_pocket = _geometry().model_copy(update={"junction_recede_offset_m": None})
    request = _request()
    outcome = _pipeline(
        _result(_SWAPPED_PLAN), geometry=no_pocket, dispatch_order_source="model_when_verified"
    ).run(request)
    assert outcome.junction_phases is None
    payload = _payload(
        outcome, request, tmp_path, plan_dispatch_order_source="model_when_verified"
    )
    assert payload["dispatch_order_source"] == "chi"
    assert payload["plan_dispatch_order_source"] == "model_when_verified"


def test_artifact_dispatch_order_source_is_null_when_nothing_was_grounded(tmp_path):
    outcome = _pipeline(_result()).run(_request()).model_copy(update={"grounded_command": None})
    payload = json.loads(
        write_decision_artifact(tmp_path, outcome, plan_dispatch_order_source="chi").read_text(
            encoding="utf-8"
        )
    )
    assert payload["dispatch_order_source"] is None
    assert payload["plan_dispatch_order_source"] == "chi"

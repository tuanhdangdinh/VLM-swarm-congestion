"""Node-level tests for `plan_dispatch_mismatch_visibility` (ROS2 stubbed).

Replays recorded decisions (minimal copies under
`tests/unit/data/plan_dispatch_mismatch/`) through the real
`OrchestratorNode._handle_outcome` with the real `PlanTracker`: the m5V chain
`b07a700f` (plan accepted, robot_4's reverse dropped by a node handoff,
robot_1/robot_2 reversed against `wait` legs) then `95066420` (a hold that
reverses robot_5 against its `continue` leg), and cv `6a05a618` (a refused
reverse). Key off must add nothing; key on must add only records and lines.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import (
    OrchestratorConfig,
    PipelineOutcome,
    PlanDispatchInfo,
    TaskAssignment,
    TerminalStage,
)

from reasoning.rag.command_grounder import VerifiedPlan
from reasoning.rag.plan_metrics import score_decision_artifact, score_dispatch_agreement
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
    ReasonerDiagnostics,
    ReasonerResult,
)
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    _FakePipeline,
    _make_node,
    node_env,
)

DATA = Path(__file__).parent / "data" / "plan_dispatch_mismatch"
FIVE = [f"robot_{i}" for i in range(1, 6)]
NEW_KEYS = ("plan_dispatch_mismatch", "reverse_dispatch")
NEW_LINE_PREFIXES = (
    "plan dispatch mismatch",
    "reverse refused",
    "reverse executed",
    "plan leg status",
)


def _fixture(name: str) -> dict:
    return json.loads((DATA / name).read_text())


def _node(node_env, tmp_path, *, visibility: bool | None):  # noqa: F811
    overrides: dict = dict(
        t0_probe_mode=False,
        plan_channel_enabled=True,
        prompt_robot_order_seed=7,
        initial_tasks={rid: TaskAssignment(task="t", goal=(0.0, 0.0)) for rid in FIVE},
    )
    if visibility is not None:
        overrides["plan_dispatch_mismatch_visibility"] = visibility
    node, _clock = _make_node(node_env, tmp_path / f"v{visibility}", _FakePipeline(), **overrides)
    return node


def _verified_legs(artifact: dict) -> list[ProposedPlanLeg]:
    plan = artifact["plan"]
    legs = [(leg["robot_id"], leg["action"]) for leg in plan["legs"]]
    if plan["plan_held"]:
        proposed = {
            leg["robot_id"]: leg["action"] for leg in artifact["decision"]["proposed_plan"]
        }
        done = {leg["robot_id"] for leg in plan["legs"] if leg["status"] == "done"}
        legs = [pair for pair in legs if pair[0] not in done]
        legs += [(r, proposed.get(r, "continue")) for r in sorted(done)]
    return [ProposedPlanLeg(robot_id=r, action=a) for r, a in legs]


def _replay(node, artifact: dict) -> PipelineOutcome:
    request_id = artifact["request_id"]
    verified = VerifiedPlan(
        legs=_verified_legs(artifact), provenance=artifact["plan"]["provenance"]
    )
    acceptance = node._plan_tracker.accept_plan(verified)
    diagnostics = ReasonerDiagnostics(
        request_id=request_id, backend_id="mock", attempts=1, parse_status="valid"
    )
    outcome = PipelineOutcome(
        request_id=request_id,
        reasoner_result=ReasonerResult(
            request_id=request_id,
            decision=CongestionDecision.model_validate(artifact["decision"]),
            raw_text="{}",
            diagnostics=diagnostics,
        ),
        grounded_command=artifact["dispatched_command"],
        terminal_stage=TerminalStage.OK,
        plan=PlanDispatchInfo(
            plan_id=acceptance.plan.plan_id,
            provenance=verified.provenance,
            legs=acceptance.plan.legs,
            dispatch_matches_plan=artifact["plan"]["dispatch_matches_plan"],
            plan_held=acceptance.held,
        ),
        plan_verified_legs=tuple(verified.legs),
    )
    node._handle_outcome(outcome, now=1000.0)
    return outcome


def _complete(node, command_id: str, robots: list[str]) -> None:
    for robot_id in robots:
        node._on_status(SimpleNamespace(command_id=command_id, robot_id=robot_id, status="ACTIVE"))
        node._on_status(
            SimpleNamespace(command_id=command_id, robot_id=robot_id, status="COMPLETED")
        )


def _chain(node) -> None:
    first = _fixture("m5V_b07a700f_reverse_handoff.json")
    _replay(node, first)
    _complete(node, first["dispatched_command"]["command_id"], ["robot_1", "robot_2", "robot_3"])
    _replay(node, _fixture("m5V_95066420_reverse_hold.json"))


def _artifact(node, request_id: str) -> dict:
    return json.loads((Path(node._config.decision_log_dir) / f"{request_id}.json").read_text())


def _lines(node) -> list[tuple[str, str]]:
    return list(node.get_logger().lines)


def _published(node) -> list[tuple]:
    return [
        (m.command_id, m.robot_id, m.action, m.parameters_json, m.timeout_sec)
        for m in node._cmd_pub.published
    ]


def test_key_defaults_off():
    assert OrchestratorConfig.model_fields["plan_dispatch_mismatch_visibility"].default is False


def test_key_on_without_plan_channel_is_refused(tmp_path):
    from tests.unit.test_m5_node_probe import _config

    with pytest.raises(ValidationError, match="requires plan_channel_enabled"):
        _config(tmp_path, plan_dispatch_mismatch_visibility=True)


def test_startup_line_suffix_only_when_on(node_env, tmp_path):  # noqa: F811
    on = _node(node_env, tmp_path, visibility=True)
    off = _node(node_env, tmp_path, visibility=False)

    [on_line] = on.get_logger().matching("grounding mode=")
    [off_line] = off.get_logger().matching("grounding mode=")
    assert on_line.endswith(" plan_dispatch_mismatch_visibility=true")
    assert on_line[: -len(" plan_dispatch_mismatch_visibility=true")] == off_line


def test_key_on_95066420_keeps_provenance_and_records_override(node_env, tmp_path):  # noqa: F811
    node = _node(node_env, tmp_path, visibility=True)
    _chain(node)

    artifact = _artifact(node, "95066420efa54188962f5c4f68806a4c")
    block = artifact["plan_dispatch_mismatch"]
    assert artifact["plan"]["provenance"] == "vlm_verbatim"
    assert block["provenance_dispatched"] == "overridden"
    assert block["verbatim_dispatched"] is False
    assert block["kinds"] == ["unplanned_motion"]
    assert block["tags"] == ["plan=overridden:reverse:robot_5:continue->reverse"]


def test_key_on_95066420_logs_one_mismatch_warning(node_env, tmp_path):  # noqa: F811
    node = _node(node_env, tmp_path, visibility=True)
    _chain(node)

    lines = [
        msg
        for level, msg in _lines(node)
        if level == "warning" and msg.startswith("plan dispatch mismatch request=95066420")
    ]
    assert lines == [
        "plan dispatch mismatch request=95066420efa54188962f5c4f68806a4c strategy=reverse "
        "robot=robot_5 planned=continue dispatched=reverse kind=unplanned_motion plan_id=1 "
        "reason=template:reverse_acts_on_involved_robots"
    ]


def test_key_on_b07a700f_records_the_dropped_reverse_as_not_sent(node_env, tmp_path):  # noqa: F811
    node = _node(node_env, tmp_path, visibility=True)
    _replay(node, _fixture("m5V_b07a700f_reverse_handoff.json"))

    record = {
        leg["robot_id"]: leg
        for leg in _artifact(node, "b07a700f441b4745a6be81f3899668ed")["plan_dispatch_mismatch"][
            "leg_status"
        ]
    }
    assert record["robot_4"]["status"] == "pending"
    assert record["robot_4"]["effective_status"] == "not_sent"
    assert record["robot_4"]["reason"] == "grounding=node_handoff:robot_1->robot_4"
    assert record["robot_1"]["effective_status"] == "overridden"
    assert record["robot_1"]["ran"] == "reverse"


def test_key_on_overridden_leg_completion_logs_a_corrected_status_line(
    node_env, tmp_path  # noqa: F811
):
    node = _node(node_env, tmp_path, visibility=True)
    first = _fixture("m5V_b07a700f_reverse_handoff.json")
    _replay(node, first)
    _complete(node, first["dispatched_command"]["command_id"], ["robot_1"])

    assert node._plan_tracker.active_plan.leg_for("robot_1").status == "done"
    assert node.get_logger().matching("plan leg status ") == [
        "plan leg status plan_id=1 robot=robot_1 leg=wait recorded=done effective=overridden "
        "ran=reverse request=b07a700f441b4745a6be81f3899668ed"
    ]


def test_key_on_95066420_leg_record_carries_the_earlier_override(node_env, tmp_path):  # noqa: F811
    node = _node(node_env, tmp_path, visibility=True)
    _chain(node)

    artifact = _artifact(node, "95066420efa54188962f5c4f68806a4c")
    record = {leg["robot_id"]: leg for leg in artifact["plan_dispatch_mismatch"]["leg_status"]}
    assert artifact["plan"]["plan_held"] is True
    assert (record["robot_1"]["status"], record["robot_1"]["effective_status"]) == (
        "done",
        "overridden",
    )
    assert record["robot_1"]["effect_request_id"] == "b07a700f441b4745a6be81f3899668ed"
    assert record["robot_5"]["effective_status"] == "overridden"
    assert record["robot_3"]["effective_status"] == "done"


def test_key_on_leaves_tracker_statuses_and_prompt_plan_state_unchanged(
    node_env, tmp_path  # noqa: F811
):
    on = _node(node_env, tmp_path, visibility=True)
    off = _node(node_env, tmp_path, visibility=False)
    _chain(on)
    _chain(off)

    plan_id = on._plan_tracker.active_plan.plan_id
    assert on._plan_tracker.active_plan == off._plan_tracker.active_plan
    assert on._plan_tracker.plan_state_context(
        plan_id, since_plan_id=None
    ) == off._plan_tracker.plan_state_context(plan_id, since_plan_id=None)


def test_key_on_publishes_exactly_the_key_off_commands(node_env, tmp_path):  # noqa: F811
    on = _node(node_env, tmp_path, visibility=True)
    off = _node(node_env, tmp_path, visibility=False)
    _chain(on)
    _chain(off)

    assert _published(on) == _published(off)


def _strip_session(artifact: dict) -> dict:
    return {key: value for key, value in artifact.items() if key != "session_id"}


@pytest.mark.parametrize(
    "request_id", ["b07a700f441b4745a6be81f3899668ed", "95066420efa54188962f5c4f68806a4c"]
)
def test_key_on_artifact_only_adds_the_new_blocks(node_env, tmp_path, request_id):  # noqa: F811
    on = _node(node_env, tmp_path, visibility=True)
    off = _node(node_env, tmp_path, visibility=False)
    _chain(on)
    _chain(off)

    on_artifact = _strip_session(_artifact(on, request_id))
    off_artifact = _strip_session(_artifact(off, request_id))
    assert not set(NEW_KEYS) & set(off_artifact)
    assert {k: v for k, v in on_artifact.items() if k not in NEW_KEYS} == off_artifact


def test_key_off_artifact_matches_a_node_without_the_key(node_env, tmp_path):  # noqa: F811
    explicit = _node(node_env, tmp_path, visibility=False)
    default = _node(node_env, tmp_path, visibility=None)
    _chain(explicit)
    _chain(default)

    for request_id in ("b07a700f441b4745a6be81f3899668ed", "95066420efa54188962f5c4f68806a4c"):
        assert _strip_session(_artifact(explicit, request_id)) == _strip_session(
            _artifact(default, request_id)
        )


def test_key_on_log_only_adds_the_new_lines(node_env, tmp_path):  # noqa: F811
    on = _node(node_env, tmp_path, visibility=True)
    off = _node(node_env, tmp_path, visibility=False)
    _chain(on)
    _chain(off)

    def normalise(lines):
        return [
            (level, msg.replace(" plan_dispatch_mismatch_visibility=true", ""))
            for level, msg in lines
            if not msg.startswith(NEW_LINE_PREFIXES) and not msg.startswith("session_id=")
            and not msg.startswith("decision artifact written")
        ]

    assert normalise(_lines(on)) == normalise(_lines(off))
    assert not any(msg.startswith(NEW_LINE_PREFIXES) for _level, msg in _lines(off))


def test_key_on_reverse_executed_line(node_env, tmp_path):  # noqa: F811
    node = _node(node_env, tmp_path, visibility=True)
    _chain(node)

    assert node.get_logger().matching("reverse executed request=95066420") == [
        "reverse executed request=95066420efa54188962f5c4f68806a4c robots=robot_4,robot_5 "
        "dispatched=reverse"
    ]
    trace = _artifact(node, "95066420efa54188962f5c4f68806a4c")["reverse_dispatch"]
    assert trace["status"] == "executed"


def test_key_on_refused_reverse_logs_an_explicit_refusal(node_env, tmp_path):  # noqa: F811
    node = _node(node_env, tmp_path, visibility=True)
    artifact = _fixture("cvD_6a05a618_reverse_refused.json")
    _replay(node, artifact)

    [line] = node.get_logger().matching("reverse refused request=")
    assert line.startswith(
        f"reverse refused request={artifact['request_id']} robots=robot_2,robot_4 "
        "dispatched=temporary_wait reason=reverse refused: both robots outside the corridor"
    )
    assert node.get_logger().matching("reverse executed") == []
    trace = _artifact(node, artifact["request_id"])["reverse_dispatch"]
    assert (trace["status"], trace["dispatched"]) == ("refused", "temporary_wait")


def test_key_on_corrected_agreement_excludes_the_override(node_env, tmp_path):  # noqa: F811
    node = _node(node_env, tmp_path, visibility=True)
    _chain(node)

    artifact = _artifact(node, "95066420efa54188962f5c4f68806a4c")
    agreement = score_dispatch_agreement(artifact)
    assert agreement is not None
    assert (agreement.agreement, agreement.agreement_dispatched) == (True, False)
    assert (agreement.verbatim, agreement.verbatim_dispatched) == (True, False)


def test_registered_metric_is_identical_with_key_on_and_off(node_env, tmp_path):  # noqa: F811
    on = _node(node_env, tmp_path, visibility=True)
    off = _node(node_env, tmp_path, visibility=False)
    _chain(on)
    _chain(off)

    request_id = "95066420efa54188962f5c4f68806a4c"
    on_metrics = score_decision_artifact(_artifact(on, request_id))
    assert on_metrics == score_decision_artifact(_artifact(off, request_id))
    assert on_metrics.model_dump(mode="json") == score_decision_artifact(
        _artifact(off, request_id)
    ).model_dump(mode="json")
    assert score_dispatch_agreement(_artifact(off, request_id)) is None


def test_visibility_failure_never_blocks_dispatch(node_env, tmp_path, monkeypatch):  # noqa: F811
    node = _node(node_env, tmp_path, visibility=True)
    node_module = __import__("swarm_orchestrator.orchestrator_node", fromlist=["x"])

    def boom(*_args, **_kwargs):
        raise RuntimeError("synthetic")

    monkeypatch.setattr(node_module, "build_plan_dispatch_visibility", boom)
    _replay(node, _fixture("m5V_b07a700f_reverse_handoff.json"))

    assert node._cmd_pub.published
    block = _artifact(node, "b07a700f441b4745a6be81f3899668ed")["plan_dispatch_mismatch"]
    assert block == {"error": "RuntimeError: synthetic"}


def test_withheld_decision_logs_one_summary_warning(node_env, tmp_path):  # noqa: F811
    from swarm_orchestrator.plan_dispatch_visibility import (
        LegEffectLedger,
        build_plan_dispatch_visibility,
    )

    node = _node(node_env, tmp_path, visibility=True)
    artifact = _fixture("m5D_03bba450_yield_shield.json")
    verified = VerifiedPlan(legs=_verified_legs(artifact), provenance="vlm_verbatim")
    acceptance = node._plan_tracker.accept_plan(verified)
    outcome = PipelineOutcome(
        request_id=artifact["request_id"],
        reasoner_result=ReasonerResult(
            request_id=artifact["request_id"],
            decision=CongestionDecision.model_validate(artifact["decision"]),
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id=artifact["request_id"], backend_id="mock", attempts=1,
                parse_status="valid",
            ),
        ),
        grounded_command=artifact["dispatched_command"],
        terminal_stage=TerminalStage.OK,
        plan=PlanDispatchInfo(
            plan_id=acceptance.plan.plan_id,
            provenance="vlm_verbatim",
            legs=acceptance.plan.legs,
            dispatch_matches_plan=False,
        ),
        plan_verified_legs=tuple(verified.legs),
    )

    record = build_plan_dispatch_visibility(
        outcome,
        dispatch_command=artifact["dispatched_command"],
        dropped_robot_ids=(),
        withheld_reason="refusal_no_action",
        request_robot_ids=FIVE,
        ledger=LegEffectLedger(),
    )

    assert record is not None
    assert record.warning_lines == (
        f"plan dispatch mismatch request={artifact['request_id']} strategy=yield "
        "robot=robot_1,robot_4 planned=robot_1:yield,robot_4:cross dispatched=none "
        "kind=withheld plan_id=1 reason=withheld:refusal_no_action",
    )
    legs = {leg["robot_id"]: leg for leg in record.mismatch_block["leg_status"]}
    assert legs["robot_1"]["effective_status"] == "not_sent"
    assert legs["robot_1"]["reason"] == "withheld:refusal_no_action"


def _pipeline_outcome(plan_tracker):
    from swarm_orchestrator.reasoning_pipeline import InProcessPipeline

    from reasoning.rag.command_grounder import ground_reasoner_result
    from reasoning.rag.maneuver_geometry import GroundingParams
    from tests.unit.test_m5_reasoning_pipeline import _FakeReasoner, _head_on_request

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
        grounding_params=GroundingParams(mode="derived", backup_band_m=(0.01, 0.02)),
        plan_tracker=plan_tracker,
    )
    return pipe.run(_head_on_request())


def test_in_process_pipeline_carries_the_verified_legs_it_compared():
    from swarm_orchestrator.plan_tracker import PlanTracker

    outcome = _pipeline_outcome(PlanTracker())

    assert outcome.plan is not None
    assert outcome.plan_verified_legs == (
        ProposedPlanLeg(robot_id="robot_1", action="yield"),
        ProposedPlanLeg(robot_id="robot_2", action="cross"),
    )
    assert outcome.plan.dispatch_matches_plan is False


def test_in_process_pipeline_sets_no_verified_legs_without_the_plan_channel():
    assert _pipeline_outcome(None).plan_verified_legs is None

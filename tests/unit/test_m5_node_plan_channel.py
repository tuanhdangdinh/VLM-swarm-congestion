"""Node-level tests for the (a0) plan channel's orchestrator_node.py wiring (ROS2 stubbed).

Companion to `tests/unit/test_m5_plan_tracker.py` (the pure `PlanTracker` unit
tests) and `tests/unit/test_m5_reasoning_pipeline.py` (the pure
`InProcessPipeline` wiring tests): this file is the one place that exercises
`orchestrator_node.py`'s OWN plan-channel code -- `PlanTracker` construction
behind `plan_channel_enabled`, the `command_id -> plan_id` side table built in
`_dispatch`, and `_apply_plan_leg_status`'s translation of M4's
`CoordinationStatus` vocabulary onto a plan leg -- against the real node class,
per the harness `test_m5_node_probe.py` already established (ROS2 stubbed in
`sys.modules`, everything past that surface is the real code).
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from swarm_orchestrator.models import PipelineOutcome, TerminalStage
from swarm_orchestrator.plan_tracker import PlanTracker

from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    _commands,
    _make_node,
    _result,
    _trigger_real,
    node_env,
)


def _plan_command(request_id: str, plan_id: int) -> dict:
    return {
        "command_id": f"cmd-{request_id}",
        "actions": [
            {
                "robot_id": "robot_2",
                "action": "yield",
                "parameters": {"backup_distance_m": 0.8, "plan_id": plan_id},
            },
            {
                "robot_id": "robot_1",
                "action": "temporary_wait",
                "parameters": {"plan_id": plan_id},
            },
        ],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }


class _PlanAwareFakePipeline:
    """Stands in for `InProcessPipeline` already carrying the (a0) outcome.

    `InProcessPipeline.run`'s own plan-channel wiring (verify_and_repair_plan,
    `_attach_plan_id`) is unit-tested in `test_m5_reasoning_pipeline.py`; this
    fake calls `accept_plan` on the SAME `PlanTracker` instance the node
    holds (handed in after node construction -- the node creates its own
    tracker in `__init__`), so the node-level test below exercises a REAL
    tracked plan while staying isolated to `orchestrator_node.py`'s own
    wiring (the command_id -> plan_id side table, `_apply_plan_leg_status`),
    not a re-test of `InProcessPipeline.run`'s internals.
    """

    def __init__(self, tracker: PlanTracker) -> None:
        self._tracker = tracker

    def run(self, request):
        from reasoning.rag.command_grounder import VerifiedPlan
        from reasoning.vlm.models import ProposedPlanLeg

        verified = VerifiedPlan(
            legs=[
                ProposedPlanLeg(robot_id="robot_2", action="yield"),
                ProposedPlanLeg(robot_id="robot_1", action="cross"),
            ],
            provenance="vlm_verbatim",
        )
        acceptance = self._tracker.accept_plan(verified)
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id),
            grounded_command=_plan_command(request.request_id, acceptance.plan.plan_id),
            terminal_stage=TerminalStage.OK,
            plan=_plan_dispatch_info(acceptance),
        )


def _plan_dispatch_info(acceptance):
    from swarm_orchestrator.models import PlanDispatchInfo

    return PlanDispatchInfo(
        plan_id=acceptance.plan.plan_id,
        provenance=acceptance.plan.provenance,
        legs=acceptance.plan.legs,
        dispatch_matches_plan=True,
    )


def test_plan_tracker_absent_when_flag_off(node_env, tmp_path):  # noqa: F811
    from tests.unit.test_m5_node_probe import _FakePipeline

    node, _clock = _make_node(node_env, tmp_path, _FakePipeline(), t0_probe_mode=False)
    assert node._plan_tracker is None


def test_plan_tracker_constructed_when_flag_on(node_env, tmp_path):  # noqa: F811
    from tests.unit.test_m5_node_probe import _FakePipeline

    node, _clock = _make_node(
        node_env, tmp_path, _FakePipeline(), t0_probe_mode=False, plan_channel_enabled=True
    )
    assert isinstance(node._plan_tracker, PlanTracker)


def test_on_status_is_a_no_op_when_the_plan_channel_is_off(node_env, tmp_path):  # noqa: F811
    from tests.unit.test_m5_node_probe import _FakePipeline

    node, _clock = _make_node(node_env, tmp_path, _FakePipeline(), t0_probe_mode=False)
    # Must not raise even though no plan_tracker and no command_id are known.
    node._apply_plan_leg_status("cmd-unknown", "robot_1", "ACTIVE")


def test_dispatch_records_the_command_to_plan_mapping_and_status_updates_the_leg(
    node_env, tmp_path  # noqa: F811
):
    from tests.unit.test_m5_node_probe import _FakePipeline

    # Build with a throwaway pipeline first (OrchestratorNode creates its own
    # PlanTracker in __init__), then swap in the plan-aware fake wired to the
    # REAL tracker instance the node now holds.
    node, clock = _make_node(
        node_env, tmp_path, _FakePipeline(), t0_probe_mode=False, plan_channel_enabled=True
    )
    node._pipeline = _PlanAwareFakePipeline(node._plan_tracker)

    _trigger_real(node, stamp=60.0)
    node._future.result(timeout=5.0)
    node._on_timer()

    published = _commands(node)
    assert published, "no command was dispatched"
    command_id = published[0].command_id
    plan_id = node._plan_id_by_command_id[command_id]
    assert plan_id == node._plan_tracker.active_plan.plan_id
    params = json.loads(published[0].parameters_json or "{}")
    assert params.get("plan_id") == plan_id

    node._on_status(
        SimpleNamespace(command_id=command_id, robot_id="robot_2", status="ACTIVE")
    )
    assert node._plan_tracker.active_plan.leg_for("robot_2").status == "active"

    node._on_status(
        SimpleNamespace(command_id=command_id, robot_id="robot_2", status="COMPLETED")
    )
    assert node._plan_tracker.active_plan.leg_for("robot_2").status == "done"


def test_on_status_with_unknown_command_id_does_not_raise(node_env, tmp_path):  # noqa: F811
    from tests.unit.test_m5_node_probe import _FakePipeline

    node, _clock = _make_node(
        node_env,
        tmp_path,
        _FakePipeline(),
        t0_probe_mode=False,
        plan_channel_enabled=True,
    )
    # A command_id this node never dispatched (e.g. base_mission, or a
    # command from a prior process): no KeyError, no crash.
    node._apply_plan_leg_status("cmd-never-dispatched", "robot_2", "ACTIVE")


def test_timed_out_command_marks_its_plan_legs_failed(node_env, tmp_path):  # noqa: F811
    # A timeout never goes through `_on_status` (M4 never answered at all, or
    # never finished), so without explicit handling in `_on_timer` a leg
    # could stay `pending`/`active` forever after its command gives up --
    # false in the next plan-state block, and misclassifies the next
    # revision as `unforced` instead of `evidence_driven`.
    from tests.unit.test_m5_node_probe import _FakePipeline

    node, clock = _make_node(
        node_env, tmp_path, _FakePipeline(), t0_probe_mode=False, plan_channel_enabled=True
    )
    node._pipeline = _PlanAwareFakePipeline(node._plan_tracker)

    _trigger_real(node, stamp=60.0)
    node._future.result(timeout=5.0)
    node._on_timer()  # delivers the outcome and dispatches

    plan_id = node._plan_tracker.active_plan.plan_id
    assert node._plan_tracker.plan(plan_id).leg_for("robot_2").status == "pending"

    clock.t += node._config.command_timeout_sec + 1.0
    node._on_timer()  # fires check_timeouts -> the new leg-failing hook

    plan = node._plan_tracker.plan(plan_id)
    assert plan.leg_for("robot_2").status == "failed"
    assert plan.leg_for("robot_1").status == "failed"


def _reverse_plan_command(request_id: str) -> dict:
    return {
        "command_id": f"cmd-{request_id}",
        "actions": [
            {"robot_id": "robot_2", "action": "reverse", "parameters": {"backup_distance_m": 0.8}},
        ],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }


class _ReverseContinuePlanFakePipeline:
    """A plan with one `reverse` leg and one `continue` leg of ANOTHER robot.

    Freeze-blocking finding 3 (step-7a fix): pins `orchestrator_node.
    _with_plan_continue_partners` against the real node, mirroring episode
    1 decision 2's exact shape (`robot_2` reverses, `robot_1` continues, the
    SAME accepted plan).
    """

    def __init__(self, tracker: PlanTracker) -> None:
        self._tracker = tracker

    def run(self, request):
        from reasoning.rag.command_grounder import VerifiedPlan
        from reasoning.vlm.models import ProposedPlanLeg

        verified = VerifiedPlan(
            legs=[
                ProposedPlanLeg(robot_id="robot_2", action="reverse"),
                ProposedPlanLeg(robot_id="robot_1", action="continue"),
            ],
            provenance="vlm_verbatim",
        )
        acceptance = self._tracker.accept_plan(verified)
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id),
            grounded_command=_reverse_plan_command(request.request_id),
            terminal_stage=TerminalStage.OK,
            plan=_plan_dispatch_info(acceptance),
        )


def test_reverse_leg_carries_the_same_plans_continue_partner(node_env, tmp_path):  # noqa: F811
    from tests.unit.test_m5_node_probe import _FakePipeline

    node, clock = _make_node(
        node_env, tmp_path, _FakePipeline(), t0_probe_mode=False, plan_channel_enabled=True
    )
    node._pipeline = _ReverseContinuePlanFakePipeline(node._plan_tracker)

    _trigger_real(node, stamp=60.0)
    node._future.result(timeout=5.0)
    node._on_timer()

    published = _commands(node)
    reverse_msgs = [msg for msg in published if msg.action == "reverse"]
    assert reverse_msgs, "no reverse command was dispatched"
    params = json.loads(reverse_msgs[0].parameters_json or "{}")
    assert params.get("plan_continue_partners") == ["robot_1"]


def test_reverse_leg_without_a_tracked_plan_carries_no_continue_partners(
    node_env, tmp_path  # noqa: F811
):
    # v1/no-plan-channel regression pin: the plan-channel flag is off, so
    # `_with_plan_continue_partners` must be a byte-identical no-op.
    from tests.unit.test_m5_node_probe import _FakePipeline

    class _ReverseOnlyFakePipeline:
        def run(self, request):
            return PipelineOutcome(
                request_id=request.request_id,
                reasoner_result=_result(request.request_id),
                grounded_command=_reverse_plan_command(request.request_id),
                terminal_stage=TerminalStage.OK,
                plan=None,
            )

    node, clock = _make_node(node_env, tmp_path, _FakePipeline(), t0_probe_mode=False)
    node._pipeline = _ReverseOnlyFakePipeline()

    _trigger_real(node, stamp=60.0)
    node._future.result(timeout=5.0)
    node._on_timer()

    published = _commands(node)
    reverse_msgs = [msg for msg in published if msg.action == "reverse"]
    assert reverse_msgs, "no reverse command was dispatched"
    params = json.loads(reverse_msgs[0].parameters_json or "{}")
    assert "plan_continue_partners" not in params

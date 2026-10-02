"""Node-level tests for `junction_clear`'s M5 phase-queue wiring (ROS2 stubbed).

Companion to `tests/unit/test_junction_phase_queue.py` (the pure
`JunctionPhaseQueue` unit tests) and `tests/unit/test_command_grounder_*`
(`ground_junction_clear_phases`): this file is the one place that exercises
`orchestrator_node.py`'s OWN phase-advancement wiring (`_dispatch` seeding a
queue, `_resolve_command` -> `_advance_junction_phase` ->
`_dispatch_junction_phase`) against the real node class, per the harness
`test_m5_node_probe.py` already established.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from swarm_orchestrator.models import PipelineOutcome, TerminalStage

from reasoning.rag.command_grounder import ground_junction_clear_phases, verify_and_repair_plan
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import ArmGeometry, CorridorGeometry, SceneGeometry
from reasoning.vlm.models import ReasonerDiagnostics, ReasonerResult, RobotStateInput, SnapshotFrame
from reasoning.vlm.output_parser import parse_decision_text
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    _commands,
    _make_node,
    node_env,
)

IB10_STANDOFF = {
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


def _geometry() -> SceneGeometry:
    corridor = CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.6, aisle_half_width_m=0.6, occluder_height_m=0.0
    )
    return SceneGeometry(corridor=corridor, arms=_ARMS, junction_recede_offset_m=1.2)


def _params() -> GroundingParams:
    return GroundingParams(mode="derived")


def _frame() -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=xy[0], y=xy[1], theta=0.0, status="STOPPED")
            for rid, xy in IB10_STANDOFF.items()
        ],
    )


def _reasoner_result(request_id: str) -> ReasonerResult:
    decision_json = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": list(IB10_STANDOFF),
        "root_cause": "four-way standoff",
        "strategy": "junction_clear",
        "justification": "jam",
    }
    decision = parse_decision_text(json.dumps(decision_json))
    return ReasonerResult(
        request_id=request_id,
        decision=decision,
        raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id=request_id, backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


class _JunctionClearFakePipeline:
    """Stands in for `InProcessPipeline`, already carrying a real `junction_clear` outcome.

    Builds `outcome.junction_phases`/`outcome.plan` through the REAL
    verify/repair engine and the REAL `PlanTracker` instance the node holds
    (handed in after construction, mirroring
    `test_m5_node_plan_channel._PlanAwareFakePipeline`), so this is a
    node-level test of the WIRING, not a re-test of `ground_junction_clear_
    phases`/`PlanTracker` themselves.
    """

    def __init__(self, tracker) -> None:
        self._tracker = tracker

    def run(self, request):
        from swarm_orchestrator.models import PlanDispatchInfo

        result = _reasoner_result(request.request_id)
        frame = _frame()
        geometry = _geometry()
        params = _params()
        plan = ground_junction_clear_phases(
            result, snapshot=frame, params=params, geometry=geometry
        )
        verified = verify_and_repair_plan(
            result.decision, frame, geometry=geometry, grounding_params=params
        )
        acceptance = self._tracker.accept_plan(verified)
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=result,
            grounded_command=plan.phases[0].command,
            terminal_stage=TerminalStage.OK,
            plan=PlanDispatchInfo(
                plan_id=acceptance.plan.plan_id,
                provenance=acceptance.plan.provenance,
                legs=acceptance.plan.legs,
                dispatch_matches_plan=True,
            ),
            junction_phases=plan,
        )


def _dispatch_via_handle_outcome(node, clock):
    outcome = node._pipeline.run(SimpleNamespace(request_id="req-jc", robot_states=[]))
    node._handle_outcome(outcome, clock.t)


def _complete_command(node, command_id: str) -> None:
    """Report COMPLETED for every robot a dispatched command addressed."""
    robot_ids = node._tracker.robots_of(command_id)
    for robot_id in robot_ids:
        node._on_status(
            SimpleNamespace(command_id=command_id, robot_id=robot_id, status="COMPLETED")
        )


def _fail_command(node, command_id: str) -> None:
    """Report FAILED for the active robot, COMPLETED for every held one.

    Mirrors M4's own `_release_linked_waits` cascade (a `reverse`/`yield`
    leg's terminal status releases every linked `temporary_wait` in the
    same command) closely enough for this test: whichever status the
    active robot gets, every held robot still resolves, and
    `summarize_outcome` rolls the whole command up to non-"completed".
    """
    robot_ids = node._tracker.robots_of(command_id)
    node._on_status(
        SimpleNamespace(command_id=command_id, robot_id=robot_ids[0], status="FAILED")
    )
    for robot_id in robot_ids[1:]:
        node._on_status(
            SimpleNamespace(command_id=command_id, robot_id=robot_id, status="COMPLETED")
        )


def _node(node_env, tmp_path, **overrides):  # noqa: F811
    node, clock = _make_node(
        node_env,
        tmp_path,
        pipeline=None,
        t0_probe_mode=False,
        plan_channel_enabled=True,
        **overrides,
    )
    node._pipeline = _JunctionClearFakePipeline(node._plan_tracker)
    return node, clock


class TestPhaseQueueSeeding:
    def test_dispatch_seeds_a_phase_queue_keyed_by_the_dispatched_command_id(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)

        published = _commands(node)
        assert published, "no command was dispatched"
        command_id = published[0].command_id
        assert command_id == "req-jc-junction-recede-robot_4"
        assert command_id in node._junction_phase_queues

    def test_dispatch_log_line_carries_the_plan_id(self, node_env, tmp_path):  # noqa: F811
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)

        plan_id = node._plan_tracker.active_plan.plan_id
        lines = node.get_logger().matching("dispatch request=")
        assert any(f"plan_id={plan_id}" in line for line in lines)


class TestOrdinaryPhaseAdvance:
    def test_completed_recede_dispatches_the_second_recede(self, node_env, tmp_path):  # noqa: F811
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)
        first_id = _commands(node)[0].command_id

        _complete_command(node, first_id)

        published = _commands(node)
        command_ids = {msg.command_id for msg in published}
        assert "req-jc-junction-recede-robot_3" in command_ids
        assert "req-jc-junction-recede-robot_3" in node._junction_phase_queues
        assert first_id not in node._junction_phase_queues

    def test_completed_second_recede_dispatches_the_cross_phase(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)
        first_id = _commands(node)[0].command_id
        _complete_command(node, first_id)
        second_id = "req-jc-junction-recede-robot_3"

        _complete_command(node, second_id)

        command_ids = {msg.command_id for msg in _commands(node)}
        assert "req-jc-junction-cross" in command_ids
        assert "req-jc-junction-cross" in node._junction_phase_queues

    def test_completed_cross_phase_empties_the_queue(self, node_env, tmp_path):  # noqa: F811
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)
        first_id = _commands(node)[0].command_id
        _complete_command(node, first_id)
        _complete_command(node, "req-jc-junction-recede-robot_3")

        _complete_command(node, "req-jc-junction-cross")

        assert node._junction_phase_queues == {}

    def test_later_phases_carry_the_same_plan_id_as_phase_one(self, node_env, tmp_path):  # noqa: F811
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)
        first_id = _commands(node)[0].command_id
        plan_id = node._plan_id_by_command_id[first_id]

        _complete_command(node, first_id)

        assert node._plan_id_by_command_id["req-jc-junction-recede-robot_3"] == plan_id

    def test_a_later_phase_also_routes_status_onto_the_same_tracked_plan(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)
        first_id = _commands(node)[0].command_id
        plan_id = node._plan_tracker.active_plan.plan_id
        _complete_command(node, first_id)
        second_id = "req-jc-junction-recede-robot_3"

        node._on_status(SimpleNamespace(command_id=second_id, robot_id="robot_3", status="ACTIVE"))

        assert node._plan_tracker.plan(plan_id).leg_for("robot_3").status == "active"


class TestFailureFallback:
    def test_failed_first_recede_dispatches_the_fallback(self, node_env, tmp_path):  # noqa: F811
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)
        first_id = _commands(node)[0].command_id

        _fail_command(node, first_id)

        command_ids = {msg.command_id for msg in _commands(node)}
        assert "req-jc-yield" in command_ids
        assert "req-jc-yield" in node._junction_phase_queues
        lines = node.get_logger().matching("junction_clear phase advance")
        assert any("phase_reached=fallback" in line for line in lines)

    def test_fallback_resolution_empties_the_queue(self, node_env, tmp_path):  # noqa: F811
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)
        first_id = _commands(node)[0].command_id
        _fail_command(node, first_id)

        _complete_command(node, "req-jc-yield")

        assert node._junction_phase_queues == {}

    def test_a_timed_out_recede_also_dispatches_the_fallback(self, node_env, tmp_path):  # noqa: F811
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)

        # The recede command's own `timeout_sec` is `fan_out_command`'s
        # `expected_resolution_time_sec` (`junction_recede_hold_sec`, 120 s
        # by default), NOT `node._config.command_timeout_sec` (20 s) --
        # `ground_junction_clear_phases` sizes a recede phase's own backstop
        # independently of the node's generic command timeout.
        clock.t += _params().junction_recede_hold_sec + 1.0
        node._on_timer()

        command_ids = {msg.command_id for msg in _commands(node)}
        assert "req-jc-yield" in command_ids


class TestFlagOffByteIdentity:
    def test_dispatch_log_line_has_no_plan_id_when_the_flag_is_off(
        self, node_env, tmp_path  # noqa: F811
    ):
        from tests.unit.test_m5_node_probe import _FakePipeline, _trigger_real

        node, _clock = _make_node(node_env, tmp_path, _FakePipeline(), t0_probe_mode=False)
        _trigger_real(node, stamp=60.0)
        node._future.result(timeout=5.0)
        node._on_timer()

        lines = node.get_logger().matching("dispatch request=")
        assert lines, "no dispatch logged"
        assert all("plan_id=" not in line for line in lines)

"""M3 `convoy` / `priority_override` alias onto the ordered yield (unified scene design)."""
from __future__ import annotations

import itertools
import math

import pytest
from swarm_orchestrator.models import RobotView, SceneSnapshot
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    attach_registry_assignments,
    build_reasoner_request,
)

from reasoning.rag.command_grounder import (
    degradation_cause,
    ground_reasoner_result,
    resolve_strategy_alias,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)

_LEGACY = GroundingParams(mode="legacy")
_DERIVED = GroundingParams(mode="derived")


def _t1_geometry() -> SceneGeometry:
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x", center_m=0.0, half_length_m=1.0, aisle_half_width_m=0.6, occluder_height_m=0.9
        )
    )


def _a55j_geometry() -> SceneGeometry:
    # B3 convoy_counterflow's goal-table row: the A55-J barrier (T2b's).
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x", center_m=0.0, half_length_m=0.5, aisle_half_width_m=0.6, occluder_height_m=0.9
        )
    )


def _state(rid, x, y, theta, goal) -> RobotStateInput:
    return RobotStateInput(robot_id=rid, x=x, y=y, theta=theta, goal=goal)


def _b3_frame(r1_x: float = -0.12, r2_x: float = 0.12) -> SnapshotFrame:
    return SnapshotFrame(stamp=30.0, robots=[
        _state("robot_1", r1_x, 0.0, 0.0, (2.45, -0.30)),
        _state("robot_2", r2_x, 0.0, math.pi, (-2.00, 0.0)),
        _state("robot_3", -1.90, 0.0, 0.0, (2.45, 0.30)),
        _state("robot_4", -2.47, 0.0, 0.0, (1.85, 0.0)),
    ])


def _b2_frame() -> SnapshotFrame:
    return SnapshotFrame(stamp=30.0, robots=[
        _state("robot_1", -0.12, 0.0, 0.0, (2.5, 0.0)),
        _state("robot_2", 0.12, 0.0, math.pi, (-2.5, 0.0)),
    ])


def _t1x_frame() -> SnapshotFrame:
    return SnapshotFrame(stamp=30.0, robots=[
        _state("robot_1", -0.5, 0.0, 0.0, (1.75, 0.0)),
        _state("robot_2", 0.5, 0.0, math.pi, (-1.75, 0.0)),
        _state("robot_3", 0.0, -0.5, math.pi / 2, (0.0, 1.75)),
        _state("robot_4", 0.0, 0.5, -math.pi / 2, (0.0, -1.75)),
    ])


def _decision(strategy: str, involved: list[str], **update) -> CongestionDecision:
    base = dict(
        congestion_detected=True, type="deadlock", involved_robots=involved,
        root_cause="standoff in the single-lane aisle", strategy=strategy, justification="j",
    )
    base.update(update)
    return CongestionDecision(**base)


def _result(decision: CongestionDecision) -> ReasonerResult:
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)


def _positions(frame: SnapshotFrame) -> dict[str, tuple[float, float]]:
    return {s.robot_id: (s.x, s.y) for s in frame.robots}


_PLATOON = ["robot_1", "robot_2", "robot_3", "robot_4"]


class TestResolveConvoyAlias:
    def test_counter_flow_robot_yields_and_the_platoon_crosses_in_queue_order(self):
        alias = resolve_strategy_alias(
            _decision("convoy", _PLATOON), _b3_frame(), geometry=_a55j_geometry()
        )
        assert alias is not None
        assert alias.requested_strategy == "convoy"
        assert alias.decision.strategy == "yield"
        assert alias.decision.yield_robot == "robot_2"
        assert alias.decision.crossing_order == ["robot_1", "robot_3", "robot_4", "robot_2"]

    def test_valid_decided_order_is_kept(self):
        decision = _decision(
            "convoy", _PLATOON, crossing_order=["robot_3", "robot_1", "robot_4", "robot_2"]
        )
        alias = resolve_strategy_alias(decision, _b3_frame(), geometry=_a55j_geometry())
        assert alias is not None
        assert alias.decision.crossing_order == ["robot_3", "robot_1", "robot_4", "robot_2"]

    def test_queue_order_without_geometry_is_by_distance_to_the_yielder(self):
        alias = resolve_strategy_alias(_decision("convoy", _PLATOON), _b3_frame())
        assert alias is not None
        assert alias.decision.crossing_order == ["robot_1", "robot_3", "robot_4", "robot_2"]

    def test_two_robot_head_on_has_no_unique_counter_flow_robot(self):
        decision = _decision("convoy", ["robot_1", "robot_2"])
        assert resolve_strategy_alias(decision, _b2_frame()) is None

    def test_four_way_intersection_has_no_counter_flow_minority(self):
        # T1-X negative probe: perpendicular arms oppose nobody by > 90 deg
        # except their own opposite, so no single robot opposes all others.
        assert resolve_strategy_alias(_decision("convoy", _PLATOON), _t1x_frame()) is None

    def test_missing_goal_leaves_the_decision_alone(self):
        frame = _b3_frame()
        robots = [r.model_copy(update={"goal": None}) if r.robot_id == "robot_4" else r
                  for r in frame.robots]
        frame = frame.model_copy(update={"robots": robots})
        assert resolve_strategy_alias(_decision("convoy", _PLATOON), frame) is None

    def test_no_snapshot_leaves_the_decision_alone(self):
        assert resolve_strategy_alias(_decision("convoy", _PLATOON), None) is None

    def test_two_counter_flow_robots_have_no_minority(self):
        frame = _b3_frame()
        robots = [
            r.model_copy(update={"goal": (-3.0, 0.0), "theta": math.pi})
            if r.robot_id == "robot_4" else r
            for r in frame.robots
        ]
        frame = frame.model_copy(update={"robots": robots})
        assert resolve_strategy_alias(_decision("convoy", _PLATOON), frame) is None


class TestResolvePriorityAlias:
    def test_unique_max_priority_passes_first(self):
        decision = _decision("priority_override", ["robot_1", "robot_2"])
        alias = resolve_strategy_alias(decision, _b2_frame(), priorities={"robot_2": 1})
        assert alias is not None
        assert alias.decision.yield_robot == "robot_1"
        assert alias.decision.crossing_order == ["robot_2", "robot_1"]

    @pytest.mark.parametrize("priorities", [None, {}, {"robot_1": 1, "robot_2": 1}])
    def test_no_unique_max_is_unsupported(self, priorities):
        decision = _decision("priority_override", ["robot_1", "robot_2"])
        assert resolve_strategy_alias(decision, _b2_frame(), priorities=priorities) is None

    def test_three_robots_cannot_map_onto_one_yield(self):
        decision = _decision("priority_override", ["robot_1", "robot_2", "robot_3"])
        assert resolve_strategy_alias(
            decision, _b3_frame(), priorities={"robot_1": 1}
        ) is None

    @pytest.mark.parametrize(
        "strategy", ["yield", "reverse", "temporary_wait", "reroute"]
    )
    def test_other_strategies_are_never_aliased(self, strategy):
        update = {"yield_robot": "robot_1"} if strategy == "yield" else {}
        decision = _decision(strategy, ["robot_1", "robot_2"], **update)
        assert resolve_strategy_alias(decision, _b2_frame(), priorities={"robot_2": 1}) is None


class TestGroundAlias:
    def test_convoy_executes_identically_to_the_platoon_yield_legacy(self):
        frame = _b3_frame()
        convoy = ground_reasoner_result(
            _result(_decision("convoy", _PLATOON)), _positions(frame), _a55j_geometry(),
            snapshot=frame, params=_LEGACY,
        )
        yield_ = ground_reasoner_result(
            _result(_decision(
                "yield", _PLATOON, yield_robot="robot_2",
                crossing_order=["robot_1", "robot_3", "robot_4", "robot_2"],
            )),
            _positions(frame), _a55j_geometry(), snapshot=frame, params=_LEGACY,
        )
        assert convoy["degradations"] == ["strategy=aliased:convoy"]
        assert "degradations" not in yield_
        assert {k: v for k, v in convoy.items() if k != "degradations"} == yield_
        assert convoy["actions"][0]["action"] == "yield"
        assert convoy["actions"][0]["parameters"]["crossing_order"] == [
            "robot_1", "robot_3", "robot_4"
        ]

    def test_priority_override_executes_identically_to_the_routine_yield_derived(self):
        frame = _b2_frame()
        override = ground_reasoner_result(
            _result(_decision("priority_override", ["robot_1", "robot_2"])),
            geometry=_t1_geometry(), snapshot=frame, params=_DERIVED,
            priorities={"robot_2": 1},
        )
        yield_ = ground_reasoner_result(
            _result(_decision(
                "yield", ["robot_1", "robot_2"], yield_robot="robot_1",
                crossing_order=["robot_2", "robot_1"],
            )),
            geometry=_t1_geometry(), snapshot=frame, params=_DERIVED,
        )
        assert override["degradations"][-1] == "strategy=aliased:priority_override"
        assert override["degradations"][:-1] == yield_["degradations"]
        assert override["actions"] == yield_["actions"]
        assert override["actions"][0]["robot_id"] == "robot_1"

    def test_unmapped_priority_override_keeps_the_bounded_wait(self):
        frame = _b2_frame()
        command = ground_reasoner_result(
            _result(_decision("priority_override", ["robot_1", "robot_2"])),
            geometry=_t1_geometry(), snapshot=frame, params=_DERIVED,
        )
        assert command["degradations"] == ["strategy=unsupported:priority_override"]
        assert {a["action"] for a in command["actions"]} == {"temporary_wait"}

    def test_alias_tag_is_a_provenance_marker(self):
        assert degradation_cause("strategy=aliased:convoy") is None
        assert degradation_cause("strategy=aliased:priority_override") is None


_PIN_STRATEGIES = ["yield", "reverse", "temporary_wait", "reroute", "convoy", "priority_override"]


class TestPrioritiesByteIdentityPins:
    """`priorities` changes nothing but a mappable priority_override."""

    @pytest.mark.parametrize(
        ("strategy", "params"),
        list(itertools.product(_PIN_STRATEGIES, [None, _LEGACY, _DERIVED])),
    )
    def test_two_robot_commands_unchanged_by_priorities_except_the_override(
        self, strategy, params
    ):
        frame = _b2_frame()
        update = {"yield_robot": "robot_1"} if strategy == "yield" else {}
        result = _result(_decision(strategy, ["robot_1", "robot_2"], **update))
        kwargs = dict(geometry=_t1_geometry(), snapshot=frame, params=params)
        plain = ground_reasoner_result(result, _positions(frame), **kwargs)
        for priorities in ({}, {"robot_1": 1, "robot_2": 1}, {"robot_9": 3}):
            assert ground_reasoner_result(
                result, _positions(frame), priorities=priorities, **kwargs
            ) == plain
        with_priority = ground_reasoner_result(
            result, _positions(frame), priorities={"robot_2": 1}, **kwargs
        )
        if strategy == "priority_override":
            assert with_priority != plain
        else:
            assert with_priority == plain

    @pytest.mark.parametrize("params", [None, _LEGACY, _DERIVED])
    @pytest.mark.parametrize("strategy", ["yield", "temporary_wait", "reroute"])
    def test_four_robot_non_alias_commands_unchanged(self, strategy, params):
        frame = _b3_frame()
        order = ["robot_1", "robot_3", "robot_4", "robot_2"]
        update = (
            {"yield_robot": "robot_2", "crossing_order": order} if strategy == "yield" else {}
        )
        result = _result(_decision(strategy, _PLATOON, **update))
        kwargs = dict(geometry=_a55j_geometry(), snapshot=frame, params=params)
        assert ground_reasoner_result(
            result, _positions(frame), priorities={"robot_1": 2}, **kwargs
        ) == ground_reasoner_result(result, _positions(frame), **kwargs)


def _b2_request():
    snapshot = SceneSnapshot(
        stamp=30.0,
        frame_id="overhead_camera",
        robots=[
            RobotView(robot_id="robot_1", x=-0.12, y=0.0, theta=0.0,
                      linear_velocity=0.0, status="STOPPED", stamp=30.0),
            RobotView(robot_id="robot_2", x=0.12, y=0.0, theta=math.pi,
                      linear_velocity=0.0, status="STOPPED", stamp=30.0),
        ],
    )
    goals = {"robot_1": (2.5, 0.0), "robot_2": (-2.5, 0.0)}
    tasks = {"robot_1": "routine_order_delivery", "robot_2": "urgent_order_delivery"}
    return build_reasoner_request(
        "r1", attach_registry_assignments(snapshot, goals.get, tasks.get), "/tmp/r1.png"
    )


class _FakeReasoner:
    def __init__(self, decision: CongestionDecision) -> None:
        self._result = _result(decision)

    def run(self, request):
        return self._result


class TestPipelineAlias:
    def test_priority_override_gets_the_yield_stage2_and_grounds_the_yield(self):
        pipe = InProcessPipeline(
            reasoner=_FakeReasoner(_decision("priority_override", ["robot_1", "robot_2"])),
            ground_fn=ground_reasoner_result,
            scene_geometry=_t1_geometry(),
            grounding_params=_DERIVED,
            priorities={"robot_2": 1},
        )
        outcome = pipe.run(_b2_request())
        assert outcome.stage2 is not None
        assert outcome.stage2.yielder_id == "robot_1"
        assert outcome.grounded_command is not None
        assert outcome.grounded_command["actions"][0]["action"] == "yield"
        assert outcome.grounded_command["actions"][0]["robot_id"] == "robot_1"
        assert "strategy=aliased:priority_override" in outcome.grounded_command["degradations"]
        # The stage-1 decision itself is recorded as the model gave it.
        assert outcome.reasoner_result.decision.strategy == "priority_override"

    def test_priority_override_without_priorities_skips_stage2(self):
        pipe = InProcessPipeline(
            reasoner=_FakeReasoner(_decision("priority_override", ["robot_1", "robot_2"])),
            ground_fn=ground_reasoner_result,
            scene_geometry=_t1_geometry(),
            grounding_params=_DERIVED,
        )
        outcome = pipe.run(_b2_request())
        assert outcome.stage2 is None
        assert outcome.grounded_command["degradations"] == [
            "strategy=unsupported:priority_override"
        ]

"""Verifier-candidate-options condition: M3's own audit decides every offered action.

`derive_candidate_options` never hand-writes an option: each (robot, action)
is offered iff `_plan_problems` -- the leg audit `verify_and_repair_plan`
runs -- flags nothing on that robot's leg under the action's registered
probe context. These tests pin that contract, the IB10 axis-mirror outcome
the condition exists for, and the obstacle-gated yield.
"""
import sys
from pathlib import Path

import pytest

from reasoning.rag.command_grounder import (
    _plan_problems,
    derive_candidate_options,
    verify_and_repair_plan,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)

sys.path.insert(0, str(Path(__file__).parent))
from test_junction_clear_grounding import _frame as _ib10_frame  # noqa: E402
from test_junction_clear_grounding import _geometry as _ib10_geometry  # noqa: E402

_HEAD_ON = SnapshotFrame(
    stamp=1.0,
    robots=[
        RobotStateInput(robot_id="robot_1", x=-0.3, y=0.0, theta=0.0),
        RobotStateInput(robot_id="robot_2", x=0.3, y=0.0, theta=3.14),
    ],
)
_WEST_BLOCKER = StaticObstacleInput(obstacle_id="o1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3)


def _corridor_geometry() -> SceneGeometry:
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x", center_m=0.0, half_length_m=1.0, aisle_half_width_m=0.6, occluder_height_m=0.9
        )
    )


def _actions(options, robot_id):
    return [action for action, _ in options[robot_id]]


class TestHeadOn:
    def test_unobstructed_head_on_offers_every_non_continue_action(self):
        options = derive_candidate_options(_HEAD_ON, geometry=_corridor_geometry())
        for robot_id in ("robot_1", "robot_2"):
            assert _actions(options, robot_id) == ["yield", "reverse", "cross", "wait", "reroute"]

    def test_continue_is_never_listed(self):
        options = derive_candidate_options(_HEAD_ON, geometry=_corridor_geometry())
        assert all(action != "continue" for opts in options.values() for action, _ in opts)

    def test_boxed_in_yielder_is_not_offered_yield_under_the_gate(self):
        options = derive_candidate_options(
            _HEAD_ON,
            geometry=_corridor_geometry(),
            static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
        )
        assert "yield" not in _actions(options, "robot_1")
        assert "yield" in _actions(options, "robot_2")

    def test_gate_off_offers_the_boxed_in_yield_like_the_audit_does(self):
        options = derive_candidate_options(
            _HEAD_ON,
            geometry=_corridor_geometry(),
            static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="off",
        )
        assert "yield" in _actions(options, "robot_1")

    def test_cross_requires_a_feasible_releasing_yield(self):
        # robot_2 can only cross behind robot_1's yield, which the gate refuses.
        options = derive_candidate_options(
            _HEAD_ON,
            geometry=_corridor_geometry(),
            static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
        )
        assert "cross" not in _actions(options, "robot_2")
        assert "cross" in _actions(options, "robot_1")

    def test_single_robot_scene_offers_no_pairwise_action(self):
        frame = SnapshotFrame(stamp=1.0, robots=[_HEAD_ON.robots[0]])
        options = derive_candidate_options(frame, geometry=_corridor_geometry())
        assert "yield" not in _actions(options, "robot_1")
        assert "cross" not in _actions(options, "robot_1")


class TestIB10AxisMirror:
    def _options(self):
        return derive_candidate_options(
            _ib10_frame(),
            geometry=_ib10_geometry(),
            grounding_params=GroundingParams(mode="derived"),
        )

    def test_reverse_is_offered_only_to_the_structural_recede_pair(self):
        options = self._options()
        offered = sorted(rid for rid, opts in options.items() if "reverse" in [a for a, _ in opts])
        assert offered == ["robot_3", "robot_4"]

    def test_the_axis_mirror_e_w_reverse_is_never_offered(self):
        options = self._options()
        assert "reverse" not in _actions(options, "robot_1")
        assert "reverse" not in _actions(options, "robot_2")

    def test_reverse_names_the_declared_arm(self):
        options = self._options()
        assert ("reverse", "south arm") in options["robot_3"]
        assert ("reverse", "north arm") in options["robot_4"]

    def test_the_mirrored_plan_is_exactly_what_the_audit_rejects(self):
        mirrored = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2", "robot_3", "robot_4"],
            root_cause="jam",
            strategy="junction_clear",
            justification="jam",
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="reverse"),
                ProposedPlanLeg(robot_id="robot_2", action="reverse"),
                ProposedPlanLeg(robot_id="robot_3", action="yield"),
                ProposedPlanLeg(robot_id="robot_4", action="cross"),
            ],
        )
        verified = verify_and_repair_plan(
            mirrored, _ib10_frame(), geometry=_ib10_geometry(),
            grounding_params=GroundingParams(mode="derived"),
        )
        assert verified.provenance != "vlm_verbatim"



def _audit_context(frame, robot_id, action, geometry, junction):
    """Rebuild the registered probe context, independently of the implementation."""
    known = [s.robot_id for s in frame.robots]
    others = [s for s in frame.robots if s.robot_id != robot_id]
    me = frame.find_robot(robot_id)
    partner = min(others, key=lambda s: ((s.x - me.x) ** 2 + (s.y - me.y) ** 2, s.robot_id))
    if action == "reverse" and junction:
        involved, strategy, assigned = known, "junction_clear", {robot_id: "reverse"}
    elif action == "reverse":
        involved = [robot_id, partner.robot_id]
        strategy, assigned = "reverse", dict.fromkeys(involved, "reverse")
    elif action == "yield":
        involved = [robot_id, partner.robot_id]
        strategy, assigned = "yield", {robot_id: "yield", partner.robot_id: "cross"}
    else:
        involved = [robot_id, partner.robot_id]
        strategy = "temporary_wait" if action == "wait" else "reroute"
        assigned = {robot_id: action, partner.robot_id: "wait"}
    decision = CongestionDecision(
        congestion_detected=True, type="deadlock", involved_robots=involved, root_cause="x",
        strategy=strategy, justification="x",
        yield_robot=robot_id if action == "yield" else None,
    )
    order = [*assigned, *(rid for rid in known if rid not in assigned)]
    legs = [ProposedPlanLeg(robot_id=rid, action=assigned.get(rid, "continue")) for rid in order]
    return legs, decision


@pytest.mark.parametrize(
    ("frame_fn", "geometry_fn", "junction"),
    [(lambda: _HEAD_ON, _corridor_geometry, False), (_ib10_frame, _ib10_geometry, True)],
)
def test_every_offered_single_leg_action_passes_the_audit_under_its_context(
    frame_fn, geometry_fn, junction
):
    frame, geometry = frame_fn(), geometry_fn()
    params = GroundingParams(mode="derived")
    options = derive_candidate_options(
        frame, geometry=geometry, yield_feasibility_mode="swap", grounding_params=params
    )
    for robot_id, offered in options.items():
        for action, _ in offered:
            if action == "cross":
                continue  # pairwise; covered by the head-on cross tests above
            legs, decision = _audit_context(frame, robot_id, action, geometry, junction)
            problems = _plan_problems(legs, decision, frame, geometry, (), "swap", params)
            flagged = {legs[i].robot_id for i, _ in problems}
            assert robot_id not in flagged, (robot_id, action, problems)

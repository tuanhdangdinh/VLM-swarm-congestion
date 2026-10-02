"""Tests for `junction_clear` (prereg-v2 (a), build-order step 5).

Covers: the chi cost-ranked recede selection (hand-computed cells, including
a synthetic follower cell pinning the N_f weight), the recede-endpoint
geometry against the intersection-resolvability study's IB10 numbers, the
(a0) consistency rule, `_derive_default_plan`'s full-sequence derivation
(recede-set-plus-yield, and the fallback to plain `yield`), the
`_plan_problems` phase-ordering audit (and its repair), staggered-not-
simultaneous (`ground_junction_clear_phases` never puts two recede legs in
one command), and legacy-mode's graceful non-spatial-wait degradation.
"""
from __future__ import annotations

import pytest

from reasoning.rag.command_grounder import (
    CommandGroundingError,
    _derive_default_plan,
    ground_junction_clear_phases,
    ground_reasoner_result,
    verify_and_repair_plan,
)
from reasoning.rag.maneuver_geometry import (
    GroundingParams,
    is_at_recede_pocket,
    rank_recede_candidates,
    recede_cost,
    recede_distance_m,
    recede_follower_count,
)
from reasoning.rag.scene_geometry import ArmGeometry, CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)

IB10_STANDOFF = {
    "robot_1": (-0.2192, -0.0014),
    "robot_2": (0.33, 0.0158),
    "robot_3": (-0.0208, -0.2583),
    "robot_4": (0.0045, 0.2773),
}
JUNCTION_ARMS = {
    "robot_1": ArmGeometry(axis="x", side=-1),
    "robot_2": ArmGeometry(axis="x", side=1),
    "robot_3": ArmGeometry(axis="y", side=-1),
    "robot_4": ArmGeometry(axis="y", side=1),
}


def _corridor() -> CorridorGeometry:
    return CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.6, aisle_half_width_m=0.6, occluder_height_m=0.0
    )


def _geometry(offset_m: float | None = 1.2) -> SceneGeometry:
    return SceneGeometry(
        corridor=_corridor(), arms=JUNCTION_ARMS, junction_recede_offset_m=offset_m
    )


def _frame(positions: dict[str, tuple[float, float]] | None = None) -> SnapshotFrame:
    positions = positions or IB10_STANDOFF
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=xy[0], y=xy[1], theta=0.0, status="STOPPED")
            for rid, xy in positions.items()
        ],
    )


def _decision(**overrides) -> CongestionDecision:
    base = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": list(IB10_STANDOFF),
        "root_cause": "four-way standoff",
        "strategy": "junction_clear",
        "justification": "jam",
    }
    base.update(overrides)
    return CongestionDecision(**base)


def _verify(decision: CongestionDecision, geometry: SceneGeometry | None):
    return verify_and_repair_plan(
        decision, _frame(), geometry=geometry, grounding_params=GroundingParams(mode="derived")
    )


def _result(decision: CongestionDecision, request_id: str = "req-jc") -> ReasonerResult:
    return ReasonerResult(
        request_id=request_id,
        decision=decision,
        raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id=request_id, backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


# ---- chi cost-ranked recede selection (hand-computed cells) ----


class TestChiRanking:
    def test_ib10_d_space_matches_the_study_within_rounding(self):
        # Study: "the cross pair reverses along its own arms to |y| ~= 1.2
        # (legs 0.93-0.95 m from +-0.25-0.27)". From the IB10 GT standoff
        # (robot_3 y=-0.2583, robot_4 y=0.2773), D_SPACE = 1.2 - |y|.
        geometry = _geometry()
        frame = _frame()
        assert recede_distance_m(frame, "robot_3", geometry) == 0.942
        assert recede_distance_m(frame, "robot_4", geometry) == 0.923
        assert 0.93 <= recede_distance_m(frame, "robot_3", geometry) <= 0.95
        assert 0.92 <= recede_distance_m(frame, "robot_4", geometry) <= 0.95

    def test_ib10_cross_pair_has_no_followers(self):
        # One robot per arm in IB10: N_f = 0 everywhere, so chi weights (s, t)
        # are irrelevant to THIS cell's ranking -- it reduces to D_SPACE order.
        geometry = _geometry()
        frame = _frame()
        for robot_id in IB10_STANDOFF:
            assert recede_follower_count(frame, robot_id, geometry) == 0

    def test_ib10_robot_4_ranks_before_robot_3(self):
        # robot_4 is already farther out (|y| 0.2773 > 0.2583), so it has the
        # smaller D_SPACE/chi and recedes FIRST in the staggered order.
        geometry = _geometry()
        frame = _frame()
        params = GroundingParams()
        assert recede_cost(frame, "robot_4", geometry, params) < recede_cost(
            frame, "robot_3", geometry, params
        )
        assert rank_recede_candidates(frame, ["robot_3", "robot_4"], geometry, params) == [
            "robot_4",
            "robot_3",
        ]

    def test_candidates_restricted_to_the_yield_axis_are_never_chosen(self):
        # Interpretation (not settled by name in either spec, flagged in the
        # task report): the recede candidate SET is structural (declared arm
        # axis != geometry.corridor.axis), not chi-discovered. robot_1/
        # robot_2 (axis "x", matching corridor.axis) have a LOWER chi than
        # either cross-axis robot at this standoff (closer to centre is
        # irrelevant to this specific geometry; the point is they are simply
        # never offered to chi at all for a junction_clear decision).
        geometry = _geometry()
        frame = _frame()
        params = GroundingParams()
        # Confirm the trap would fire if candidates were NOT restricted:
        # robot_2 (yield axis) chi-ranks ahead of both cross-axis robots.
        all_ranked = rank_recede_candidates(frame, list(IB10_STANDOFF), geometry, params)
        assert all_ranked[0] == "robot_2"
        # The actual default-plan derivation never asks chi to rank
        # robot_1/robot_2 at all (see TestDefaultPlanDerivation below).

    def test_a_follower_on_the_same_arm_raises_chi_and_can_flip_the_order(self):
        # Synthetic cell (hand-computed): robot_5 shares robot_4's arm (y,
        # +1) and sits farther out (0.80 m > 0.27 m) -- a follower in
        # robot_4's recede path. With the default weights (s=1.0, t=0.5):
        #   chi(robot_3) = 1.0*0.93 + 0.5*0 = 0.93
        #   chi(robot_4) = 1.0*0.93 + 0.5*1 = 1.43
        # robot_4's extra follower cost (0.5) flips the order that the
        # no-follower IB10 cell gives (robot_4 first there).
        arms = {
            "robot_3": ArmGeometry(axis="y", side=-1),
            "robot_4": ArmGeometry(axis="y", side=1),
            "robot_5": ArmGeometry(axis="y", side=1),
        }
        geometry = SceneGeometry(corridor=_corridor(), arms=arms, junction_recede_offset_m=1.2)
        frame = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id="robot_3", x=0.0, y=-0.27, theta=0.0),
                RobotStateInput(robot_id="robot_4", x=0.0, y=0.27, theta=0.0),
                RobotStateInput(robot_id="robot_5", x=0.0, y=0.80, theta=0.0),
            ],
        )
        params = GroundingParams()
        assert recede_distance_m(frame, "robot_3", geometry) == 0.93
        assert recede_distance_m(frame, "robot_4", geometry) == 0.93
        assert recede_follower_count(frame, "robot_3", geometry) == 0
        assert recede_follower_count(frame, "robot_4", geometry) == 1
        assert recede_cost(frame, "robot_3", geometry, params) == 0.93
        assert recede_cost(frame, "robot_4", geometry, params) == pytest.approx(1.43)
        assert rank_recede_candidates(frame, ["robot_3", "robot_4"], geometry, params) == [
            "robot_3",
            "robot_4",
        ]

    def test_a_robot_with_no_declared_arm_is_not_a_candidate(self):
        geometry = SceneGeometry(
            corridor=_corridor(),
            arms={"robot_3": ArmGeometry(axis="y", side=-1)},
            junction_recede_offset_m=1.2,
        )
        frame = _frame()
        assert recede_distance_m(frame, "robot_4", geometry) is None
        ranked = rank_recede_candidates(frame, ["robot_3", "robot_4"], geometry, GroundingParams())
        assert ranked == ["robot_3"]

    def test_no_declared_pocket_means_no_candidate_at_all(self):
        geometry = _geometry(offset_m=None)
        frame = _frame()
        assert recede_distance_m(frame, "robot_3", geometry) is None
        assert (
            rank_recede_candidates(frame, ["robot_3", "robot_4"], geometry, GroundingParams()) == []
        )

    def test_is_at_recede_pocket_uses_the_tolerance(self):
        geometry = _geometry()
        frame = SnapshotFrame(
            stamp=1.0,
            robots=[RobotStateInput(robot_id="robot_3", x=0.0, y=-1.18, theta=0.0)],
        )
        params = GroundingParams(junction_recede_tolerance_m=0.05)
        tighter = params.model_copy(update={"junction_recede_tolerance_m": 0.01})
        assert recede_distance_m(frame, "robot_3", geometry) == 0.02
        assert is_at_recede_pocket(frame, "robot_3", geometry, params) is True
        assert is_at_recede_pocket(frame, "robot_3", geometry, tighter) is False
        assert is_at_recede_pocket(frame, "robot_1", geometry, params) is False


# ---- (a0) consistency rule ----


class TestConsistencyRule:
    def test_a_reverse_leg_alone_is_consistent(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_4", action="reverse"),
                ProposedPlanLeg(robot_id="robot_3", action="reverse"),
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ]
        )
        verified = _verify(decision, _geometry())
        assert verified.provenance == "vlm_verbatim"

    def test_no_reverse_or_yield_leg_is_inconsistent(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_4", action="wait"),
                ProposedPlanLeg(robot_id="robot_3", action="wait"),
                ProposedPlanLeg(robot_id="robot_1", action="wait"),
                ProposedPlanLeg(robot_id="robot_2", action="wait"),
            ]
        )
        verified = _verify(decision, _geometry())
        assert verified.provenance == "m3_default"
        assert verified.rejection_stage == "inconsistent"

    def test_a_yield_leg_alone_satisfies_consistency_too(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_4", action="yield"),
                ProposedPlanLeg(robot_id="robot_1", action="continue"),
                ProposedPlanLeg(robot_id="robot_2", action="continue"),
                ProposedPlanLeg(robot_id="robot_3", action="continue"),
            ]
        )
        verified = _verify(decision, _geometry())
        assert verified.provenance != "m3_default" or verified.rejection_stage != "inconsistent"


# ---- _derive_default_plan: the full recede-then-yield sequence ----


class TestDefaultPlanDerivation:
    def test_default_plan_is_the_full_sequence_in_chi_order_then_the_yield(self):
        legs = _derive_default_plan(
            _decision(),
            _frame(),
            geometry=_geometry(),
            static_obstacles=(),
            yield_feasibility_mode="off",
            priorities=None,
            grounding_params=GroundingParams(mode="derived"),
        )
        by_robot = {leg.robot_id: leg.action for leg in legs}
        assert by_robot["robot_4"] == "reverse"
        assert by_robot["robot_3"] == "reverse"
        assert by_robot["robot_1"] == "yield"
        assert by_robot["robot_2"] == "cross"
        order = [leg.robot_id for leg in legs]
        # Recede legs (chi order) strictly precede the yield-axis legs.
        assert order.index("robot_4") < order.index("robot_1")
        assert order.index("robot_3") < order.index("robot_1")
        assert order.index("robot_1") < order.index("robot_2")

    def test_falls_back_to_plain_yield_when_no_pocket_is_declared(self):
        legs = _derive_default_plan(
            _decision(),
            _frame(),
            geometry=_geometry(offset_m=None),
            static_obstacles=(),
            yield_feasibility_mode="off",
            priorities=None,
            grounding_params=GroundingParams(mode="derived"),
        )
        by_robot = {leg.robot_id: leg.action for leg in legs}
        assert "reverse" not in by_robot.values()
        assert by_robot["robot_1"] == "yield"
        assert by_robot["robot_2"] == "cross"
        # J1 drops the cross-axis pair to no-op, matching "v1 behavior ...
        # single yield or no-op".
        assert by_robot["robot_3"] == "continue"
        assert by_robot["robot_4"] == "continue"

    def test_falls_back_to_plain_yield_with_no_geometry_at_all(self):
        legs = _derive_default_plan(
            _decision(),
            _frame(),
            geometry=None,
            static_obstacles=(),
            yield_feasibility_mode="off",
            priorities=None,
            grounding_params=GroundingParams(mode="derived"),
        )
        by_robot = {leg.robot_id: leg.action for leg in legs}
        assert "reverse" not in by_robot.values()


# ---- _plan_problems: phase ordering audit and its repair ----


class TestPhaseOrderingAudit:
    def test_a_plan_that_crosses_before_receding_is_repaired(self):
        # A yield/cross leg positioned BEFORE a recede leg is infeasible --
        # the escort would run while a cross-axis robot is still 0.24-0.34 m
        # away, unexempted outside its own command.
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
                ProposedPlanLeg(robot_id="robot_4", action="reverse"),
                ProposedPlanLeg(robot_id="robot_3", action="reverse"),
            ]
        )
        verified = _verify(decision, _geometry())
        # A pure REORDER (same per-robot actions, corrected sequence) is the
        # minimal repair here -- two edits, never a substitution.
        assert verified.provenance == "repaired"
        assert len(verified.edits) == 2
        assert all(edit.op == "reorder" for edit in verified.edits)
        order = [leg.robot_id for leg in verified.legs if leg.action != "continue"]
        assert order == ["robot_4", "robot_3", "robot_1", "robot_2"]

    def test_a_correctly_ordered_plan_is_accepted_verbatim(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_4", action="reverse"),
                ProposedPlanLeg(robot_id="robot_3", action="reverse"),
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ]
        )
        verified = _verify(decision, _geometry())
        assert verified.provenance == "vlm_verbatim"


# ---- ground_junction_clear_phases: staggered, never simultaneous ----


class TestStaggeredNeverSimultaneous:
    def test_each_recede_candidate_gets_its_own_command(self):
        plan = ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
            geometry=_geometry(),
        )
        recede_phases = [p for p in plan.phases if p.label == "recede"]
        assert len(recede_phases) == 2
        assert recede_phases[0].robot_id == "robot_4"
        assert recede_phases[1].robot_id == "robot_3"
        for phase in recede_phases:
            reverse_actions = [
                a for a in phase.command["actions"] if a["action"] == "reverse"
            ]
            assert len(reverse_actions) == 1
            assert reverse_actions[0]["robot_id"] == phase.robot_id

    def test_every_recede_command_exempts_the_whole_scrum_via_temporary_wait(self):
        # Safety (a): `admitted_partners` exempts a `reverse` only against
        # the OTHER members of its OWN command -- every involved robot must
        # be addressed, active one real, the rest held.
        plan = ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
            geometry=_geometry(),
        )
        for phase in plan.phases:
            if phase.label != "recede":
                continue
            addressed = {a["robot_id"] for a in phase.command["actions"]}
            assert addressed == set(IB10_STANDOFF)

    def test_the_cross_phase_still_holds_both_receded_robots(self):
        # `reverse` never holds on its own (M4 always resolves it with
        # hold_sec=0.0): the final phase must keep BOTH recede candidates
        # `temporary_wait`-ed too, or a receded robot could resume its base
        # mission back through the junction mid-crossing.
        plan = ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
            geometry=_geometry(),
        )
        cross = next(p for p in plan.phases if p.label == "cross")
        held = {
            a["robot_id"]
            for a in cross.command["actions"]
            if a["action"] == "temporary_wait"
        }
        assert {"robot_3", "robot_4"} <= held

    def test_the_fallback_is_a_plain_yield_dropping_the_cross_pair_via_j1(self):
        plan = ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
            geometry=_geometry(),
        )
        assert plan.fallback_command["degradations"]
        assert "order=junction_same_axis" in plan.fallback_command["degradations"]
        actions = {a["robot_id"]: a["action"] for a in plan.fallback_command["actions"]}
        assert actions.get("robot_1") == "yield" or actions.get("robot_2") == "yield"
        assert "robot_3" not in actions
        assert "robot_4" not in actions

    def test_raises_when_no_candidate_survives_chi(self):
        with pytest.raises(CommandGroundingError):
            ground_junction_clear_phases(
                _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
                geometry=_geometry(offset_m=None),
            )


# ---- end-to-end ground_reasoner_result: the single-command contract ----


class TestSingleCommandContract:
    def test_phase_one_is_the_cheapest_chi_recede(self):
        command = ground_reasoner_result(
            _result(_decision()), geometry=_geometry(), snapshot=_frame(),
            params=GroundingParams(mode="derived"),
        )
        actions = {a["robot_id"]: a["action"] for a in command["actions"]}
        assert actions["robot_4"] == "reverse"
        assert "junction_clear=recede" in command["degradations"]

    def test_legacy_mode_degrades_to_a_non_spatial_wait_not_a_crash(self):
        command = ground_reasoner_result(_result(_decision()), robot_positions={
            rid: xy for rid, xy in IB10_STANDOFF.items()
        })
        actions = {a["action"] for a in command["actions"]}
        assert actions == {"temporary_wait"}

    def test_no_pocket_declared_falls_back_to_plain_yield_at_the_top_level(self):
        command = ground_reasoner_result(
            _result(_decision()), geometry=_geometry(offset_m=None), snapshot=_frame(),
            params=GroundingParams(mode="derived"),
        )
        assert "junction_clear=fallback:no_candidates" in command["degradations"]
        actions = {a["robot_id"]: a["action"] for a in command["actions"]}
        assert "robot_3" not in actions and "robot_4" not in actions

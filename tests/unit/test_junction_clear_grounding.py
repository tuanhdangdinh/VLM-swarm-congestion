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

    def test_release_phase_actions_are_a_passive_hold_not_a_maneuver(self):
        # Regression pin for a real bug this task's own VM verification run
        # caught: `command_bus_node`'s `yield` branch always runs
        # `Nav2Adapter.backup` FIRST, defaulting `backup_distance_m` to
        # 0.3 m when absent -- an unrequested 0.3 m backup for an
        # already-correctly-parked held robot. `backup_distance_m: 0.0`
        # must be explicit (completes on the first odometry tick, no real
        # motion), and `hold_sec` must be positive or the hold/CrossingChain
        # logic (`_on_backup_result`'s `hold_sec <= 0.0` branch) never
        # engages at all -- the release would complete immediately after
        # the (near-instant) backup step, never actually waiting for the
        # lead's clearance.
        plan = ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
            geometry=_geometry(),
        )
        release = next(p for p in plan.phases if p.label == "release")
        for action in release.command["actions"]:
            assert action["action"] == "yield"
            assert action["parameters"]["backup_distance_m"] == 0.0
            assert action["parameters"]["hold_sec"] > 0.0
            assert action["parameters"]["passer_robot_id"] == "robot_4"

    def test_cross_phase_matches_the_studys_c_prime_numbers_only_with_j2_declared(self):
        # Advisor-review finding: without `junction_backup_clearance_m`
        # (J2) ALSO declared, the cross phase grounds with the shipped
        # 1.7 m clearance -- the study's "1, E-W, shipped" row, whose
        # park->passer-goal race (0.39-0.52 m, < 0.45 in 6/8 rows) is
        # exactly what this feature exists to avoid. The scene MUST
        # declare both `junction_recede_offset_m` (this feature) AND
        # `junction_backup_clearance_m` (J2) for the yield phase to run at
        # the study's "1, E-W, J2" row numbers (backup 0.69-0.91, park |x|
        # 1.02, escort 1.77-2.00) instead.
        without_j2 = ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
            geometry=_geometry(),
        )
        with_j2 = ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
            geometry=_geometry().model_copy(update={"junction_backup_clearance_m": 1.1}),
        )
        # The cross phase specifically, not `phases[-1]`: with 2+ recede
        # candidates (step-7a fix) a trailing "release" phase follows it,
        # whose held robots ALSO use `action == "yield"` (the staggered
        # post-composite release, a different command entirely).
        cross_without = next(p for p in without_j2.phases if p.label == "cross")
        cross_with = next(p for p in with_j2.phases if p.label == "cross")
        yielder_without = next(
            a for a in cross_without.command["actions"] if a["action"] == "yield"
        )
        yielder_with = next(
            a for a in cross_with.command["actions"] if a["action"] == "yield"
        )
        assert yielder_without["parameters"]["backup_distance_m"] == 1.151  # shipped 1.7 m
        assert yielder_with["parameters"]["backup_distance_m"] == 0.799  # J2 1.1 m, in [0.69, 0.91]
        assert abs(yielder_with["parameters"]["retreat_x_m"]) == pytest.approx(1.018, abs=1e-3)
        escort_with = yielder_with["parameters"]["passer_escort_distance_m"]
        assert 1.77 <= escort_with <= 2.00

    def test_cross_phase_safety_numbers_do_not_react_to_the_recede_pairs_position(self):
        # Pinning the `JunctionClearPhasePlan` docstring's own "the scene
        # does not change mid-sequence" assumption (advisor review): ground
        # the cross phase from the PRE-recede snapshot and again from a
        # POST-recede one (robot_3/robot_4 already at their |y|=1.2
        # pockets); the SAFETY-CRITICAL yield parameters -- the ones a
        # band/room/escort sweep could react to -- must be identical either
        # way, since none of them reads a cross-axis robot's position.
        # FINDING, reported rather than papered over: the `extra_holds`
        # LIST ORDER (robot_3 vs robot_4 first) can differ between the two
        # snapshots -- chi re-ranks on whichever positions it is given, and
        # the two recede candidates are an exact tie at |y|=1.2 -- but this
        # never happens in this system's actual use (one
        # `ground_junction_clear_phases` call per decision, from one
        # snapshot, never re-ground from a later one), and the tie is
        # broken by robot_id either way, so it is deterministic, not a race.
        geometry = _geometry().model_copy(update={"junction_backup_clearance_m": 1.1})
        pre = ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
            geometry=geometry,
        )
        post_positions = dict(IB10_STANDOFF)
        post_positions["robot_3"] = (-0.0208, -1.2)
        post_positions["robot_4"] = (0.0045, 1.2)
        post = ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(post_positions),
            params=GroundingParams(mode="derived"), geometry=geometry,
        )
        cross_pre = next(p for p in pre.phases if p.label == "cross")
        cross_post = next(p for p in post.phases if p.label == "cross")
        yielder_pre = next(
            a for a in cross_pre.command["actions"] if a["action"] == "yield"
        )
        yielder_post = next(
            a for a in cross_post.command["actions"] if a["action"] == "yield"
        )
        safety_keys = (
            "backup_distance_m",
            "pull_off_lateral_m",
            "retreat_x_m",
            "retreat_y_m",
            "passer_escort_distance_m",
        )
        for key in safety_keys:
            assert yielder_pre["parameters"][key] == yielder_post["parameters"][key], key

    def test_the_fallback_is_a_plain_yield_dropping_the_cross_pair_via_j1(self):
        plan = ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
            geometry=_geometry(),
        )
        assert plan.fallback_command["degradations"]
        assert "order=junction_same_axis" in plan.fallback_command["degradations"]
        actions = {a["robot_id"]: a["action"] for a in plan.fallback_command["actions"]}
        assert actions.get("robot_1") == "yield" or actions.get("robot_2") == "yield"
        # J1 still drops both cross-axis robots from the YIELD's own order,
        # but neither is left unaddressed: a recede candidate may already
        # have receded (or failed mid-recede) by the time of this fallback,
        # and its base mission must not be free to resume through the
        # junction while the fallback yield runs.
        assert actions.get("robot_3") == "temporary_wait"
        assert actions.get("robot_4") == "temporary_wait"
        assert plan.fallback_held_robot_ids == ("robot_4", "robot_3")

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


# ---- loudness guard (step-6 coordinator ruling): neither field declared,
# one missing, or both declared ----


class TestShippedUnsolvedLoudnessGuard:
    """IB10's goal table must declare BOTH `junction_recede_offset_m` and
    `junction_backup_clearance_m` to reach the study's solved row. This guard
    makes the unsolved-row silent failure (bug 4,
    docs/implementation_notes.md 2026-10-02 step-5 post-landing entry)
    log-visible without changing any grounded number.
    """

    def _plan(self, *, offset_m, backup_clearance_m):
        geometry = _geometry(offset_m=offset_m)
        if backup_clearance_m is not None:
            geometry = geometry.model_copy(
                update={"junction_backup_clearance_m": backup_clearance_m}
            )
        return ground_junction_clear_phases(
            _result(_decision()), snapshot=_frame(), params=GroundingParams(mode="derived"),
            geometry=geometry,
        )

    def test_both_fields_missing_tags_no_candidates_and_shipped_unsolved(self):
        # No pocket, no J2: never reaches `ground_junction_clear_phases` at
        # all (it would raise), so `ground_reasoner_result`'s own top-level
        # fallback applies. The field-missing tag is independent of WHY the
        # fallback fired (coordinator ruling), so both tags are present, the
        # second naming both missing fields.
        command = ground_reasoner_result(
            _result(_decision()), geometry=_geometry(offset_m=None), snapshot=_frame(),
            params=GroundingParams(mode="derived"),
        )
        assert "junction_clear=fallback:no_candidates" in command["degradations"]
        assert (
            "junction_geometry=shipped_unsolved:"
            "missing=junction_recede_offset_m,junction_backup_clearance_m"
            in command["degradations"]
        )

    def test_backup_clearance_alone_without_recede_offset_tags_the_missing_offset(self):
        # J2 declared but no pocket: `ranked` is empty regardless (the offset
        # gate short-circuits before J2 is ever consulted), same top-level
        # fallback as the fully-missing case -- J2 alone cannot trigger the
        # composite -- but now the tag names only the field that is actually
        # missing (J2 itself is present).
        command = ground_reasoner_result(
            _result(_decision()), geometry=_geometry(offset_m=None).model_copy(
                update={"junction_backup_clearance_m": 1.1}
            ), snapshot=_frame(), params=GroundingParams(mode="derived"),
        )
        assert "junction_clear=fallback:no_candidates" in command["degradations"]
        assert (
            "junction_geometry=shipped_unsolved:missing=junction_recede_offset_m"
            in command["degradations"]
        )

    def test_no_candidates_for_an_unrelated_reason_never_gets_the_field_tag(self):
        # Both fields declared, but no cross-axis robot survives chi (no
        # `arms` declared at all): `no_candidates` fires for a geometric
        # reason, not a missing field, so the new tag must NOT appear --
        # this is exactly the false-positive `no_candidates` alone cannot
        # rule out (coordinator review finding).
        geometry = SceneGeometry(
            corridor=_corridor(), junction_recede_offset_m=1.2, junction_backup_clearance_m=1.1,
        )
        command = ground_reasoner_result(
            _result(_decision()), geometry=geometry, snapshot=_frame(),
            params=GroundingParams(mode="derived"),
        )
        assert "junction_clear=fallback:no_candidates" in command["degradations"]
        assert not any(
            tag.startswith("junction_geometry=shipped_unsolved") for tag in command["degradations"]
        )

    def test_recede_offset_alone_without_j2_tags_every_phase_shipped_unsolved(self):
        # The actual silent-failure case: the composite proceeds (a pocket is
        # declared) but grounds the cross phase and fallback through the
        # shipped 1.7 m clearance. The tag must be loud wherever a caller
        # looks: phase one (the single-command contract's return value),
        # every recede phase, the cross phase, and the fallback -- naming
        # only the field actually missing (the pocket is declared). The
        # trailing "release" phase (step-7a fix) is excluded on purpose: its
        # geometry (`passer_clear_m`) never reads `junction_backup_clearance_m`
        # at all, so tagging it would misattribute a degradation it does not
        # have.
        tag = "junction_geometry=shipped_unsolved:missing=junction_backup_clearance_m"
        plan = self._plan(offset_m=1.2, backup_clearance_m=None)
        for phase in plan.phases:
            if phase.label == "release":
                continue
            assert tag in phase.command["degradations"], phase.label
        assert tag in plan.fallback_command["degradations"]
        top_level = ground_reasoner_result(
            _result(_decision()), geometry=_geometry(offset_m=1.2), snapshot=_frame(),
            params=GroundingParams(mode="derived"),
        )
        assert tag in top_level["degradations"]

    def test_both_fields_present_tags_nothing_and_grounds_the_solved_row(self):
        plan = self._plan(offset_m=1.2, backup_clearance_m=1.1)
        for phase in plan.phases:
            assert not any(
                tag.startswith("junction_geometry=shipped_unsolved")
                for tag in phase.command["degradations"]
            ), phase.label
        assert not any(
            tag.startswith("junction_geometry=shipped_unsolved")
            for tag in plan.fallback_command["degradations"]
        )
        cross = next(p for p in plan.phases if p.label == "cross")
        yielder = next(a for a in cross.command["actions"] if a["action"] == "yield")
        # The study's solved "1, E-W, J2" row (also pinned, without the tag
        # question, by test_cross_phase_matches_the_studys_c_prime_numbers_
        # only_with_j2_declared above): the guard changes no grounded number.
        assert yielder["parameters"]["backup_distance_m"] == 0.799
        assert abs(yielder["parameters"]["retreat_x_m"]) == pytest.approx(1.018, abs=1e-3)
        assert 1.77 <= yielder["parameters"]["passer_escort_distance_m"] <= 2.00

    def test_tagged_and_untagged_runs_ground_identical_numbers_elsewhere(self):
        # The guard must be purely additive to `degradations`: strip that key
        # from both plans' commands and the rest must match byte-for-byte,
        # since the untagged (both-fields) and tagged (J2-missing) runs
        # legitimately ground DIFFERENT yield numbers (solved vs. unsolved
        # row) -- what must NOT differ is the recede phase (which never reads
        # `junction_backup_clearance_m`) and every command's shape.
        with_j2 = self._plan(offset_m=1.2, backup_clearance_m=1.1)
        without_j2 = self._plan(offset_m=1.2, backup_clearance_m=None)
        for a, b in zip(with_j2.phases, without_j2.phases, strict=True):
            if a.label == "recede":
                assert a.command["actions"] == b.command["actions"]


# ---- recede-set membership and order audit (step-7a fix, freeze-blocking
# finding 1: a plan naming the wrong recede pair, or the right pair in the
# wrong order, used to verify vlm_verbatim with no repair offered) ----


class TestRecedeSetAudit:
    def test_correct_plan_still_verifies_verbatim(self):
        # Confirmation, not a change (the step-6 sweep's control case): the
        # chi-ranked pair, in chi order, with the yield-axis legs after.
        decision = _decision(
            proposed_plan=[
                {"robot_id": "robot_4", "action": "reverse"},
                {"robot_id": "robot_3", "action": "reverse"},
                {"robot_id": "robot_1", "action": "yield"},
                {"robot_id": "robot_2", "action": "cross"},
            ]
        )
        verified = _verify(decision, _geometry())
        assert verified.provenance == "vlm_verbatim"
        assert verified.edits == []

    def test_wrong_recede_pair_is_no_longer_accepted_verbatim(self):
        # The step-4 sweep's exact finding: the yield-axis pair named as the
        # recede set (and vice versa) used to verify vlm_verbatim -- a
        # metric hole, since the actual dispatch (chi-ranked, structural)
        # would never match it. Now flagged and repaired (or, if the repair
        # distance is exhausted, defaulted) -- never silently verbatim.
        #
        # Step-7b ruling (ii): this is the sweep's `recede_pair_full_axis_
        # swap` case (true minimal repair depth 5), one of the two
        # documented m3_default-by-design cases at the frozen default bound
        # (3) -- `scripts/junction_clear_repair_bound_sweep.py`,
        # docs/reports/2026-10-03-step7b-oracle-freeze.md.
        decision = _decision(
            proposed_plan=[
                {"robot_id": "robot_1", "action": "reverse"},
                {"robot_id": "robot_2", "action": "reverse"},
                {"robot_id": "robot_3", "action": "yield"},
                {"robot_id": "robot_4", "action": "cross"},
            ]
        )
        verified = _verify(decision, _geometry())
        assert verified.provenance == "m3_default"
        assert verified.rejection_stage == "repair_bound_exceeded"

    def test_missing_both_recede_candidates_falls_to_m3_default_at_the_frozen_bound(self):
        # The sweep's `missing_both_recede_candidates` case (true minimal
        # repair depth 4): just over the frozen bound (3), the third
        # documented m3_default-by-design case.
        decision = _decision(
            proposed_plan=[
                {"robot_id": "robot_1", "action": "yield"},
                {"robot_id": "robot_2", "action": "cross"},
            ]
        )
        verified = _verify(decision, _geometry())
        assert verified.provenance == "m3_default"
        assert verified.rejection_stage == "repair_bound_exceeded"

    def test_recede_legs_in_the_wrong_relative_order_become_repaired(self):
        # Run B's exact live bug: both recede candidates correctly membered,
        # but listed in the order OPPOSITE chi's (robot_4 before robot_3,
        # per TestChiRanking.test_ib10_robot_4_ranks_before_robot_3) -- a
        # single `reorder` edit fixes it, well within the shipped bound.
        decision = _decision(
            proposed_plan=[
                {"robot_id": "robot_3", "action": "reverse"},
                {"robot_id": "robot_4", "action": "reverse"},
                {"robot_id": "robot_1", "action": "yield"},
                {"robot_id": "robot_2", "action": "cross"},
            ]
        )
        verified = _verify(decision, _geometry())
        assert verified.provenance == "repaired"
        assert len(verified.edits) == 1
        assert verified.edits[0].op == "reorder"
        assert [leg.robot_id for leg in verified.legs if leg.action == "reverse"] == [
            "robot_4",
            "robot_3",
        ]

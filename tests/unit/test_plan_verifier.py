"""Tests for the (a0) M3 verify/repair engine in `reasoning.rag.command_grounder`.

Covers: validation/consistency matrix, lenient completion, repair minimality
(including a reorder-only minimal repair), three-way provenance on every
path, and the two-robot head-on regression pins against `resolve_yield_roles`
and `_apply_yield_feasibility`'s existing swap gate -- the CRITICAL
requirement that v2's engine reduces to v1's behaviour exactly.
"""

import itertools

import pytest
from pydantic import ValidationError

from reasoning.rag.command_grounder import (
    CommandGroundingError,
    PlanRepairParams,
    _derive_default_plan,
    ground_reasoner_result,
    resolve_yield_roles,
    verify_and_repair_plan,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import ArmGeometry, CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)


def _decision(**overrides) -> CongestionDecision:
    base = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2"],
        "root_cause": "head-on standoff",
        "strategy": "yield",
        "justification": "j",
        "yield_robot": "robot_1",
    }
    base.update(overrides)
    return CongestionDecision(**base)


def _frame(*robots: tuple[str, float, float]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0) for rid, x, y in robots],
    )


def _geometry() -> SceneGeometry:
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x", center_m=0.0, half_length_m=1.0, aisle_half_width_m=0.6, occluder_height_m=0.9
        )
    )


_DEADLOCK = _frame(("robot_1", -0.3, 0.0), ("robot_2", 0.3, 0.0))
_WEST_BLOCKER = StaticObstacleInput(obstacle_id="o1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3)
_EAST_BLOCKER = StaticObstacleInput(obstacle_id="o2", x=1.85, y=0.0, size_x_m=0.3, size_y_m=0.3)


class TestPlanAbsentReducesToM3Default:
    def test_plan_absent_is_m3_default_with_zero_edits(self):
        decision = _decision()
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())

        assert verified.provenance == "m3_default"
        assert verified.edits == []
        assert verified.rejection_stage == "absent"
        assert verified.rejection_reason == "plan absent"

    def test_plan_absent_default_matches_resolve_yield_roles(self):
        decision = _decision()
        verified = verify_and_repair_plan(
            decision, _DEADLOCK, geometry=_geometry(), static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
        )
        roles = resolve_yield_roles(
            decision, _DEADLOCK, geometry=_geometry(), static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
        )

        yielder_actions = [leg.action for leg in verified.legs if leg.robot_id == roles.yielder_id]
        assert yielder_actions == ["yield"]
        order = [leg.robot_id for leg in verified.legs if leg.action == "cross"]
        assert order == roles.crossing_order


class TestSwapGateOneLegRepair:
    """CRITICAL regression: the engine must reduce to the v1 swap gate."""

    def _plan_named_yielder(self, yielder="robot_1", passer="robot_2"):
        return [
            ProposedPlanLeg(robot_id=yielder, action="yield"),
            ProposedPlanLeg(robot_id=passer, action="cross"),
        ]

    def test_infeasible_named_yielder_repairs_with_exactly_one_swap_edit(self):
        decision = _decision(proposed_plan=self._plan_named_yielder())
        verified = verify_and_repair_plan(
            decision, _DEADLOCK, geometry=_geometry(), static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
        )

        assert verified.provenance == "repaired"
        assert len(verified.edits) == 1
        assert verified.edits[0].op == "swap"
        assert set(verified.edits[0].robot_ids) == {"robot_1", "robot_2"}

    def test_repaired_yielder_and_order_match_apply_yield_feasibility_swap(self):
        decision = _decision(proposed_plan=self._plan_named_yielder())
        verified = verify_and_repair_plan(
            decision, _DEADLOCK, geometry=_geometry(), static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
        )
        roles = resolve_yield_roles(
            decision, _DEADLOCK, geometry=_geometry(), static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
        )

        yielder_leg = next(leg for leg in verified.legs if leg.action == "yield")
        cross_legs = [leg.robot_id for leg in verified.legs if leg.action == "cross"]
        assert yielder_leg.robot_id == roles.yielder_id == "robot_2"
        assert cross_legs == roles.crossing_order == ["robot_1"]

    def test_feasible_named_yielder_is_verbatim_zero_edits(self):
        # East blocked only: robot_1 (named yielder, retreats west) is fine.
        decision = _decision(proposed_plan=self._plan_named_yielder())
        verified = verify_and_repair_plan(
            decision, _DEADLOCK, geometry=_geometry(), static_obstacles=(_EAST_BLOCKER,),
            yield_feasibility_mode="swap",
        )

        assert verified.provenance == "vlm_verbatim"
        assert verified.edits == []
        assert [leg.action for leg in verified.legs] == ["yield", "cross"]

    def test_plan_equal_to_default_is_verbatim(self):
        # No obstacles: robot_1 is always feasible, so the VLM's plan matches
        # M3's own default exactly.
        decision = _decision(proposed_plan=self._plan_named_yielder())
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())

        assert verified.provenance == "vlm_verbatim"
        assert verified.edits == []


class TestReorderIsAMinimalRepairWhenSubstitutionCannotFix:
    """A case where the minimal repair is a reorder, not a substitution."""

    def _three_robot_frame(self):
        return _frame(("robot_1", -0.3, 0.0), ("robot_2", 1.5, 0.0), ("robot_3", 0.3, 0.0))

    def test_wrong_nearest_first_order_repairs_with_one_reorder_edit(self):
        frame = self._three_robot_frame()
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),  # farther, listed first
                ProposedPlanLeg(robot_id="robot_3", action="cross"),  # nearer, listed second
            ],
        )

        verified = verify_and_repair_plan(decision, frame, geometry=_geometry())

        assert verified.provenance == "repaired"
        assert len(verified.edits) == 1
        assert verified.edits[0].op == "reorder"
        cross_order = [leg.robot_id for leg in verified.legs if leg.action == "cross"]
        assert cross_order == ["robot_3", "robot_2"]
        # No action changed for any robot: a pure positional fix.
        before = {"robot_1": "yield", "robot_2": "cross", "robot_3": "cross"}
        after = {leg.robot_id: leg.action for leg in verified.legs}
        assert after == before


class TestConsistencyMatrix:
    @pytest.mark.parametrize(
        "strategy, plan_actions, consistent",
        [
            ("yield", {"robot_1": "yield", "robot_2": "cross"}, True),
            ("yield", {"robot_1": "yield", "robot_2": "yield"}, False),
            ("yield", {"robot_1": "cross", "robot_2": "cross"}, False),
            ("temporary_wait", {"robot_1": "wait", "robot_2": "wait"}, True),
            ("temporary_wait", {"robot_1": "continue", "robot_2": "continue"}, False),
            ("reroute", {"robot_1": "reroute", "robot_2": "wait"}, True),
            ("reroute", {"robot_1": "wait", "robot_2": "wait"}, False),
        ],
    )
    def test_consistency_gates_m3_default(self, strategy, plan_actions, consistent):
        decision = _decision(
            strategy=strategy,
            yield_robot="robot_1" if strategy == "yield" else None,
            proposed_plan=[
                ProposedPlanLeg(robot_id=rid, action=action) for rid, action in plan_actions.items()
            ],
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())

        if consistent:
            assert verified.provenance != "m3_default" or verified.rejection_stage is None
        else:
            assert verified.provenance == "m3_default"
            assert verified.rejection_stage == "inconsistent"

    def test_reverse_has_no_registered_consistency_rule(self):
        # The spec is silent on `reverse`; any plan with a "reverse" strategy
        # decision must not be rejected purely for its action mix.
        decision = _decision(
            strategy="reverse",
            yield_robot=None,
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="continue"),
                ProposedPlanLeg(robot_id="robot_2", action="continue"),
            ],
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        assert verified.rejection_stage != "inconsistent"


class TestPlanFieldDisagreement:
    def test_plan_yield_leg_disagreeing_with_yield_robot_is_inconsistent(self):
        # Both robots are feasible (no obstacles): the plan's own yield leg
        # names robot_2, but the decision's stated yield_robot is robot_1.
        # Picking one over the other would be reinterpretation.
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_2", action="yield"),
                ProposedPlanLeg(robot_id="robot_1", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())

        assert verified.provenance == "m3_default"
        assert verified.rejection_stage == "inconsistent"
        assert "yield_robot" in verified.rejection_reason

    def test_plan_crossing_order_disagreeing_with_decision_order_is_inconsistent(self):
        frame = _frame(("robot_1", -0.3, 0.0), ("robot_2", 0.3, 0.0), ("robot_3", 1.0, 0.0))
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            crossing_order=["robot_2", "robot_3", "robot_1"],  # robot_1 yields
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_3", action="cross"),  # swapped order
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ],
        )
        verified = verify_and_repair_plan(decision, frame, geometry=_geometry())

        assert verified.provenance == "m3_default"
        assert verified.rejection_stage == "inconsistent"
        assert "crossing_order" in verified.rejection_reason

    def test_repair_is_not_blocked_by_the_field_disagreement_gate(self):
        # The gate checks the plan against decision fields ONCE, before any
        # repair; the swap-gate repair reassigning the yield role away from
        # `yield_robot` must still succeed (the repair target, not the
        # original plan, is allowed to disagree).
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(
            decision, _DEADLOCK, geometry=_geometry(), static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
        )

        assert verified.provenance == "repaired"


class TestLenientCompletion:
    def test_omitted_robot_gets_continue_leg_not_counted_as_repair(self):
        frame = _frame(("robot_1", -0.3, 0.0), ("robot_2", 0.3, 0.0), ("robot_3", 5.0, 5.0))
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(decision, frame, geometry=_geometry())

        assert verified.plan_completed_legs == ["robot_3"]
        completed_leg = next(leg for leg in verified.legs if leg.robot_id == "robot_3")
        assert completed_leg.action == "continue"
        assert verified.provenance == "vlm_verbatim"
        assert verified.edits == []

    def test_completion_is_reported_even_when_plan_is_rejected(self):
        frame = _frame(("robot_1", -0.3, 0.0), ("robot_2", 0.3, 0.0), ("robot_3", 5.0, 5.0))
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="yield"),  # inconsistent: two yields
            ]
        )
        verified = verify_and_repair_plan(decision, frame, geometry=_geometry())

        assert verified.provenance == "m3_default"
        assert verified.plan_completed_legs == ["robot_3"]


class TestUnknownRobotIdRejected:
    def test_unknown_robot_id_is_rejected_wholesale_not_partially_repaired(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_99", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())

        assert verified.provenance == "m3_default"
        assert verified.rejection_stage == "unknown_robot"
        assert "robot_99" in verified.rejection_reason


class TestDuplicateRobotRejectedAtSchema:
    def test_duplicate_robot_id_raises_on_direct_construction(self):
        with pytest.raises(ValidationError):
            CongestionDecision(
                congestion_detected=True,
                type="deadlock",
                involved_robots=["robot_1", "robot_2"],
                root_cause="x",
                strategy="yield",
                justification="j",
                proposed_plan=[
                    ProposedPlanLeg(robot_id="robot_1", action="yield"),
                    ProposedPlanLeg(robot_id="robot_1", action="cross"),
                ],
            )


class TestRepairDistanceBound:
    def test_default_bound_is_frozen_at_four(self):
        # Step-7b ruling (ii) froze 3 (no bound in 1-4 reached full
        # coverage). RE-FROZEN at 4 by the same procedure under the
        # chi-epsilon verbatim rule (RULED 2026-10-03): `recede_order_
        # swapped` leaves the corpus and the two depth-5 cases drop to 4, so
        # bound 4 covers every remaining repairable case
        # (docs/reports/2026-10-03-plan-grammar-fixes.md).
        assert PlanRepairParams().max_repair_edits == 4

    def test_repair_exceeding_bound_falls_back_to_m3_default(self):
        # Both sides blocked: no involved robot can feasibly yield at all, so
        # no repair within the bound can ever succeed.
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(
            decision,
            _DEADLOCK,
            geometry=_geometry(),
            static_obstacles=(_WEST_BLOCKER, _EAST_BLOCKER),
            yield_feasibility_mode="swap",
            repair_params=PlanRepairParams(max_repair_edits=2),
        )

        assert verified.provenance == "m3_default"
        assert verified.rejection_stage == "repair_bound_exceeded"

    def test_zero_bound_never_repairs(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(
            decision,
            _DEADLOCK,
            geometry=_geometry(),
            static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
            repair_params=PlanRepairParams(max_repair_edits=0),
        )

        assert verified.provenance == "m3_default"
        assert verified.rejection_stage == "repair_bound_exceeded"


class TestExemptionPairing:
    def test_involved_robot_marked_continue_under_yield_is_infeasible(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="continue"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())

        assert verified.provenance == "repaired"
        assert any(edit.op == "substitute" for edit in verified.edits)
        cross_leg = next(leg for leg in verified.legs if leg.robot_id == "robot_2")
        assert cross_leg.action == "cross"


class TestJunctionSameAxisReuse:
    def test_same_axis_opposite_side_cross_leg_is_substituted(self):
        # Mirrors the J1 four-way pattern: two robots held on the same axis,
        # opposite sides, both marked cross -- the engine must flag (not
        # silently drop) the same robot `_junction_same_axis_order` would.
        geometry = SceneGeometry(
            corridor=CorridorGeometry(
                axis="x",
                center_m=0.0,
                half_length_m=0.6,
                aisle_half_width_m=0.6,
                occluder_height_m=0.0,
            ),
            arms={
                "robot_1": ArmGeometry(axis="x", side=-1),
                "robot_2": ArmGeometry(axis="y", side=1),
                "robot_3": ArmGeometry(axis="y", side=-1),
            },
        )
        frame = _frame(("robot_1", -0.5, 0.0), ("robot_2", 0.0, 0.5), ("robot_3", 0.0, -0.5))
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
                ProposedPlanLeg(robot_id="robot_3", action="cross"),
            ],
        )

        verified = verify_and_repair_plan(decision, frame, geometry=geometry)

        # At least one of the opposite-side pair must no longer be "cross".
        actions = {leg.robot_id: leg.action for leg in verified.legs}
        assert not (actions["robot_2"] == "cross" and actions["robot_3"] == "cross")


class TestNonCongestionPrecondition:
    def test_non_congestion_decision_raises(self):
        decision = CongestionDecision(
            congestion_detected=False,
            type="none",
            involved_robots=[],
            root_cause="clear",
            strategy="none",
            justification="nothing happening",
        )
        with pytest.raises(CommandGroundingError):
            verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())


def _project_legacy_command(command: dict, known_ids: list[str]) -> dict[str, str]:
    """Project a `ground_reasoner_result` LEGACY-mode command onto plan legs.

    A `temporary_wait` is a `cross` leg exactly when the command also
    contains a `yield` (it is a suppressed passer, M4's ordered-release
    convention); otherwise it is a genuine `wait`. A robot the command
    names no action for gets `continue` (`_derive_default_plan`'s
    scene-wide completion).
    """
    acted = {action["robot_id"]: action["action"] for action in command["actions"]}
    has_yield = any(action == "yield" for action in acted.values())
    projected: dict[str, str] = {}
    for robot_id in known_ids:
        action = acted.get(robot_id, "continue")
        if action == "temporary_wait":
            projected[robot_id] = "cross" if has_yield else "wait"
        else:
            projected[robot_id] = action
    return projected


_MATRIX_STRATEGIES = [
    "yield",
    "reverse",
    "temporary_wait",
    "reroute",
    "convoy",
    "priority_override",
]
_MATRIX_POSITIONS_2 = [
    {"robot_1": (-0.3, 0.0), "robot_2": (0.3, 0.0)},
    {"robot_1": (-0.04, 0.0), "robot_2": (0.08, 0.0)},
    {"robot_1": (-2.5, 0.0), "robot_2": (-1.5, 0.0)},
    {"robot_1": (-1.9, 0.0), "robot_2": (0.2, 0.0)},
]
_MATRIX_GATES = [
    ((), "off"),
    ((_WEST_BLOCKER,), "off"),
    ((_WEST_BLOCKER,), "swap"),
    ((_WEST_BLOCKER,), "refuse"),
]


class TestDefaultPlanMatchesLegacyGrounding:
    """`_derive_default_plan` must match what `ground_reasoner_result` (legacy
    mode) actually dispatches -- the CRITICAL regression requirement generalized
    past the hand-picked swap-gate fixtures, per code review.

    NOTE (known, deliberate scope boundary): this equivalence is verified for
    LEGACY-mode grounding only. DERIVED-mode's backup-band / retreat-candidate
    sweep (`GroundingParams`, `prepare_retreat_selection`) can degrade a yield
    to a reroute in a way `_derive_default_plan` does not model, since
    `verify_and_repair_plan` takes no `GroundingParams` in this CORE step
    (confirmed divergent with a deliberately-impossible `backup_band_m`; not
    fixed here -- flagged in the implementation notes and task report instead
    of silently claimed equivalent).
    """

    @pytest.mark.parametrize(
        "strategy, yield_robot, positions, use_geometry, gate",
        list(
            itertools.product(
                _MATRIX_STRATEGIES,
                [None, "robot_2"],
                _MATRIX_POSITIONS_2,
                [False, True],
                _MATRIX_GATES,
            )
        ),
    )
    def test_default_plan_matches_legacy_command_two_robot(
        self, strategy, yield_robot, positions, use_geometry, gate
    ):
        obstacles, mode = gate
        geometry = _geometry() if use_geometry else None
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2"],
            root_cause="head-on aisle conflict",
            strategy=strategy,
            justification="robots are stopped face to face",
            yield_robot=yield_robot,
        )
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        command = ground_reasoner_result(
            result,
            robot_positions=positions,
            geometry=geometry,
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
        )
        snapshot = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0)
                for rid, (x, y) in positions.items()
            ],
        )
        default_legs = _derive_default_plan(
            decision,
            snapshot,
            geometry=geometry,
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
            priorities=None,
        )

        assert {leg.robot_id: leg.action for leg in default_legs} == _project_legacy_command(
            command, list(positions)
        )

    def test_default_plan_matches_legacy_three_robot_multi_passer_refusal(self):
        # The legacy nearest-first-passer refusal (`_first_passer_refusal`)
        # must gate the default plan too, not just `ground_reasoner_result`.
        positions = {"robot_1": (-0.3, 0.0), "robot_2": (1.5, 0.0), "robot_3": (0.3, 0.0)}
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2", "robot_3"],
            root_cause="x",
            strategy="yield",
            justification="j",
            yield_robot="robot_1",
            crossing_order=["robot_1", "robot_2", "robot_3"],
        )
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        command = ground_reasoner_result(result, robot_positions=positions, geometry=_geometry())
        snapshot = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0)
                for rid, (x, y) in positions.items()
            ],
        )
        default_legs = _derive_default_plan(
            decision,
            snapshot,
            geometry=_geometry(),
            static_obstacles=(),
            yield_feasibility_mode="off",
            priorities=None,
        )

        assert [action["action"] for action in command["actions"]] == ["temporary_wait"] * 3
        assert {leg.robot_id: leg.action for leg in default_legs} == {
            "robot_1": "wait",
            "robot_2": "wait",
            "robot_3": "wait",
        }

    def test_default_plan_without_grounding_params_does_not_model_derived_mode(self):
        # Pre-ruling-3 behaviour, still exact when `grounding_params` is
        # omitted: DERIVED mode's backup-band sweep can degrade a yield to a
        # reroute, but with no `GroundingParams` passed in `_derive_default_plan`
        # has no way to see that, so it still says yield/cross. Omitting
        # `grounding_params` is a caller choice (e.g. LEGACY-mode callers that
        # have none), not a remaining gap -- see the next test for the ruling
        # 3 fix when it IS passed.
        from reasoning.rag.maneuver_geometry import GroundingParams

        snapshot = _DEADLOCK
        decision = _decision()
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        impossible_band = GroundingParams(mode="derived", backup_band_m=(0.01, 0.02))
        command = ground_reasoner_result(
            result, snapshot=snapshot, params=impossible_band, geometry=_geometry()
        )
        default_legs = _derive_default_plan(
            decision,
            snapshot,
            geometry=_geometry(),
            static_obstacles=(),
            yield_feasibility_mode="off",
            priorities=None,
        )

        assert command["actions"][0]["action"] == "reroute"  # derived mode degrades
        assert {leg.robot_id: leg.action for leg in default_legs}["robot_1"] == "yield"

    def test_default_plan_with_grounding_params_models_derived_mode_band_infeasibility(self):
        # Repair-semantics ruling 3 (2026-10-02): WITH `grounding_params`
        # passed, the default plan now models the SAME backup-band sweep
        # `ground_reasoner_result`'s derived-mode dispatch runs, and reaches
        # the SAME reroute degradation -- the gap the previous test documents
        # is closed when the caller supplies the params it was always missing.
        from reasoning.rag.maneuver_geometry import GroundingParams

        snapshot = _DEADLOCK
        decision = _decision()
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        impossible_band = GroundingParams(mode="derived", backup_band_m=(0.01, 0.02))
        command = ground_reasoner_result(
            result, snapshot=snapshot, params=impossible_band, geometry=_geometry()
        )
        default_legs = _derive_default_plan(
            decision,
            snapshot,
            geometry=_geometry(),
            static_obstacles=(),
            yield_feasibility_mode="off",
            priorities=None,
            grounding_params=impossible_band,
        )

        assert command["actions"][0]["action"] == "reroute"
        by_robot = {leg.robot_id: leg.action for leg in default_legs}
        assert by_robot["robot_1"] == "reroute"
        assert by_robot["robot_2"] == "wait"


def _ordered_active_legs(legs: list[ProposedPlanLeg]) -> list[tuple[str, str]]:
    """Non-`continue` legs as `(robot_id, action)`, in execution order.

    Unlike a `{robot_id: action}` dict this preserves crossing ORDER, which
    is exactly what the multi-passer equivalence/divergence tests below turn
    on: two plans can agree on every robot's action and still differ in who
    crosses first.
    """
    return [(leg.robot_id, leg.action) for leg in legs if leg.action != "continue"]


def _project_legacy_command_ordered(command: dict, known_ids: list[str]) -> list[tuple[str, str]]:
    acted = {action["robot_id"]: action["action"] for action in command["actions"]}
    has_yield = any(action == "yield" for action in acted.values())
    ordered: list[tuple[str, str]] = []
    # `command["actions"]` is already in execution order (yield/reroute
    # first, each wait/cross after); project it directly rather than
    # iterating `known_ids`, so crossing order survives the projection.
    for action in command["actions"]:
        robot_id, value = action["robot_id"], action["action"]
        if value == "temporary_wait":
            ordered.append((robot_id, "cross" if has_yield else "wait"))
        else:
            ordered.append((robot_id, value))
    named = {robot_id for robot_id, _ in ordered}
    for robot_id in known_ids:
        if robot_id not in named:
            ordered.append((robot_id, "continue"))
    return ordered


def _derived_grounding_params():
    """The SHIPPED `config/rag.yaml` `grounding:` section, loaded from disk.

    Not hand-copied: a future edit to the shipped config changes this sweep's
    inputs automatically, so the equivalence claim stays pinned to "what M5
    actually runs" rather than a snapshot of it.
    """
    import yaml

    with open("config/rag.yaml", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return GroundingParams(**raw["grounding"])


class TestDefaultPlanMatchesDerivedGrounding:
    """Repair-semantics ruling 3 (2026-10-02): `_derive_default_plan` with
    `grounding_params` set must match what `ground_reasoner_result` (DERIVED
    mode) actually dispatches -- the equivalence `TestDefaultPlanMatchesLegacyGrounding`
    proves for LEGACY mode, now extended to the mode the fleet actually ships
    (`config/rag.yaml` `grounding.mode: derived`). The two-robot head-on
    equivalence smoke (prereg-v2 build-order step 4) runs derived mode and
    counts only if this class is green.
    """

    @pytest.mark.parametrize(
        "strategy, yield_robot, positions, gate",
        list(
            itertools.product(
                _MATRIX_STRATEGIES,
                [None, "robot_2"],
                _MATRIX_POSITIONS_2,
                _MATRIX_GATES,
            )
        ),
    )
    def test_default_plan_matches_derived_command_two_robot(
        self, strategy, yield_robot, positions, gate
    ):
        obstacles, mode = gate
        geometry = _geometry()
        params = _derived_grounding_params()
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2"],
            root_cause="head-on aisle conflict",
            strategy=strategy,
            justification="robots are stopped face to face",
            yield_robot=yield_robot,
        )
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        snapshot = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0)
                for rid, (x, y) in positions.items()
            ],
        )
        command = ground_reasoner_result(
            result,
            geometry=geometry,
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
            snapshot=snapshot,
            params=params,
        )
        default_legs = _derive_default_plan(
            decision,
            snapshot,
            geometry=geometry,
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
            priorities=None,
            grounding_params=params,
        )

        assert {leg.robot_id: leg.action for leg in default_legs} == _project_legacy_command(
            command, list(positions)
        )

    def test_default_plan_matches_derived_command_with_an_impossible_backup_band(self):
        # The exact fixture
        # `test_default_plan_with_grounding_params_models_derived_mode_band_infeasibility`
        # pins directly, re-asserted here as a member of the systematic sweep
        # rather than a hand-picked case.
        geometry = _geometry()
        params = GroundingParams(mode="derived", backup_band_m=(0.01, 0.02))
        snapshot = _DEADLOCK
        decision = _decision()
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        command = ground_reasoner_result(
            result, snapshot=snapshot, params=params, geometry=geometry
        )
        default_legs = _derive_default_plan(
            decision,
            snapshot,
            geometry=geometry,
            static_obstacles=(),
            yield_feasibility_mode="off",
            priorities=None,
            grounding_params=params,
        )

        assert {leg.robot_id: leg.action for leg in default_legs} == _project_legacy_command(
            command, ["robot_1", "robot_2"]
        )


class TestPlanPresentTwoRobotMatchesLegacyGrounding:
    """The swap-gate-reduction claim, exercised with the plan PRESENT (not
    absent): a v1-shaped VLM plan (names the same yielder `ground_reasoner_result`
    would) must execute to the identical ordered legs v1 actually dispatches,
    across the full two-robot strategy x yielder x position x geometry x gate
    matrix. This is what "the engine must reduce to the existing swap-gate
    behavior" means when there IS a plan to verify, not just when it is
    absent.
    """

    def _v1_shaped_plan(
        self, strategy: str, yield_robot: str | None
    ) -> list[ProposedPlanLeg] | None:
        primary = yield_robot or "robot_1"
        other = "robot_2" if primary == "robot_1" else "robot_1"
        if strategy == "yield":
            return [
                ProposedPlanLeg(robot_id=primary, action="yield"),
                ProposedPlanLeg(robot_id=other, action="cross"),
            ]
        if strategy == "reverse":
            return [
                ProposedPlanLeg(robot_id="robot_1", action="reverse"),
                ProposedPlanLeg(robot_id="robot_2", action="reverse"),
            ]
        if strategy == "temporary_wait":
            return [
                ProposedPlanLeg(robot_id="robot_1", action="wait"),
                ProposedPlanLeg(robot_id="robot_2", action="wait"),
            ]
        if strategy == "reroute":
            return [
                ProposedPlanLeg(robot_id="robot_1", action="reroute"),
                ProposedPlanLeg(robot_id="robot_2", action="wait"),
            ]
        # convoy / priority_override: no direct plan-vocabulary primitive;
        # `ground_reasoner_result` aliases them to a yield internally
        # (`resolve_strategy_alias`), but `verify_and_repair_plan` does not
        # apply that alias to its own consistency/feasibility checks. Plan-
        # present behavior for these two strategies is UNVERIFIED by this
        # sweep -- flagged in the task report, not silently assumed correct.
        return None

    @pytest.mark.parametrize(
        "strategy, yield_robot, positions, use_geometry, gate",
        list(
            itertools.product(
                _MATRIX_STRATEGIES,
                [None, "robot_2"],
                _MATRIX_POSITIONS_2,
                [False, True],
                _MATRIX_GATES,
            )
        ),
    )
    def test_plan_present_matches_legacy_command_two_robot(
        self, strategy, yield_robot, positions, use_geometry, gate
    ):
        plan = self._v1_shaped_plan(strategy, yield_robot)
        if plan is None:
            pytest.skip("convoy/priority_override: no direct plan primitive, unaliased here")
        obstacles, mode = gate
        geometry = _geometry() if use_geometry else None
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2"],
            root_cause="head-on aisle conflict",
            strategy=strategy,
            justification="robots are stopped face to face",
            yield_robot=yield_robot,
            proposed_plan=plan,
        )
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        command = ground_reasoner_result(
            result,
            robot_positions=positions,
            geometry=geometry,
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
        )
        snapshot = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0)
                for rid, (x, y) in positions.items()
            ],
        )
        verified = verify_and_repair_plan(
            decision,
            snapshot,
            geometry=geometry,
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
        )

        assert _ordered_active_legs(verified.legs) == _project_legacy_command_ordered(
            command, list(positions)
        )


class TestYieldFeasibilityModeContractNeverBrokenByRepair:
    """`"off"`/`"refuse"` mean the yielder is NEVER reassigned -- a hard mode
    contract (mirroring `_apply_yield_feasibility`'s own gate), not just "no
    room-based reassignment". A `swap` repair edit touching the `yield` role
    must never fire outside `yield_feasibility_mode == "swap"`, even when an
    unrelated ordering defect would otherwise make such a swap "work".
    """

    def _three_robot_order_defect(self, yield_robot: str) -> CongestionDecision:
        # robot_2 (far, x=1.5) listed before robot_3 (near, x=0.3): violates
        # nearest-first regardless of who yields.
        return _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            yield_robot=yield_robot,
            crossing_order=["robot_1", "robot_2", "robot_3"],
            proposed_plan=[
                ProposedPlanLeg(robot_id=yield_robot, action="yield"),
                *(
                    ProposedPlanLeg(robot_id=rid, action="cross")
                    for rid in ["robot_1", "robot_2", "robot_3"]
                    if rid != yield_robot
                ),
            ],
        )

    def _frame(self) -> SnapshotFrame:
        return _frame(("robot_1", -0.3, 0.0), ("robot_2", 1.5, 0.0), ("robot_3", 0.3, 0.0))

    @pytest.mark.parametrize("mode", ["off", "refuse"])
    def test_yield_leg_never_moves_off_the_decided_yielder(self, mode):
        decision = self._three_robot_order_defect("robot_1")
        frame = self._frame()
        verified = verify_and_repair_plan(
            decision, frame, geometry=_geometry(), yield_feasibility_mode=mode
        )

        yield_legs = [leg for leg in verified.legs if leg.action == "yield"]
        if yield_legs:
            assert yield_legs[0].robot_id == "robot_1"
        else:
            # No yield leg at all means the whole thing fell back to a wait
            # fan-out (matching v1's own refusal) -- also an acceptable
            # outcome, just never a REASSIGNED yielder.
            assert all(leg.action in ("wait", "continue") for leg in verified.legs)

    def test_off_mode_never_generates_a_yield_touching_swap_edit(self):
        decision = self._three_robot_order_defect("robot_1")
        frame = self._frame()
        verified = verify_and_repair_plan(
            decision, frame, geometry=_geometry(), yield_feasibility_mode="off"
        )

        assert not any(edit.op == "swap" for edit in verified.edits)


class TestRepairCanResolveWhatLegacyRefuses:
    """RESOLVED by repair-semantics ruling 1 (2026-10-02, pinned as current
    behaviour; plan PRESENT only -- the plan-ABSENT path above is unaffected
    and still matches v1 exactly). See `docs/implementation_notes.md` for the
    full writeup.

    For a 3+-robot multi-passer scene with an independent ordering defect
    AND a room defect together, `_ground_legacy`'s swap gate only tries a
    room-based reassignment and then separately refuses on the leftover
    ordering violation -- `_first_passer_refusal`'s own comment says this is
    deliberate ("refused rather than reordered, so the executed order is
    always the decided one"). This engine's repair search is allowed to
    reorder AND reassign, so it can find a minimal, fully feasible
    resolution where legacy output is a wait fan-out for every robot. Ruling
    1 confirms this is intended, not an accident: reorder repairs MAY resolve
    a 3+-robot plan-PRESENT scene v1's refuse-only ordering policy would
    abandon -- that capability is this contract's purpose, and v1's
    plan-ABSENT behaviour (the bit-identical requirement, verified exactly
    elsewhere in this file) is untouched either way. The two cells of this
    sweep that are genuine yielder reassignments (not pure reorders) are
    further pinned by `TestTieBreakPrefersFeasibilityGateYielder` (ruling 2).
    """

    def test_repair_can_find_a_feasible_plan_where_v1_swap_mode_refuses(self):
        positions = {"robot_1": (-0.3, 0.0), "robot_2": (1.5, 0.0), "robot_3": (0.3, 0.0)}
        west_blocker = _WEST_BLOCKER
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2", "robot_3"],
            root_cause="x",
            strategy="yield",
            justification="j",
            yield_robot="robot_1",
            crossing_order=["robot_1", "robot_2", "robot_3"],
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
                ProposedPlanLeg(robot_id="robot_3", action="cross"),
            ],
        )
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        command = ground_reasoner_result(
            result,
            robot_positions=positions,
            geometry=_geometry(),
            static_obstacles=(west_blocker,),
            yield_feasibility_mode="swap",
        )
        # v1 refuses entirely here: room-swaps to robot_2, still finds the
        # ordering bad, gives up.
        assert all(action["action"] == "temporary_wait" for action in command["actions"])

        snapshot = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0)
                for rid, (x, y) in positions.items()
            ],
        )
        verified = verify_and_repair_plan(
            decision,
            snapshot,
            geometry=_geometry(),
            static_obstacles=(west_blocker,),
            yield_feasibility_mode="swap",
        )

        # The engine finds SOME executable resolution instead of refusing.
        assert verified.provenance == "repaired"
        yield_legs = [leg for leg in verified.legs if leg.action == "yield"]
        assert len(yield_legs) == 1
        # And it is genuinely feasible: re-auditing the accepted plan finds
        # no outstanding problems.
        problems = _plan_problems_for_test(
            verified.legs, decision, snapshot, _geometry(), (west_blocker,), "swap"
        )
        assert problems == []


class TestTieBreakPrefersFeasibilityGateYielder:
    """Repair-semantics ruling 2 (2026-10-02, `docs/implementation_notes.md`):
    equal-cost repair candidates tie-break toward M3's derived plan,
    "including its yielder pick". Pins the exact two cells the ruling names
    (`_DIVERGENT_THREE_ROBOT_CELLS`'s two "swap"-mode, `yield_robot="robot_1"`
    entries): before this ruling the fixed `_ops` enumeration order found a
    feasible repair naming `robot_3` as yielder first; `_apply_yield_feasibility`'s
    own candidate scan (`"swap"` mode, `robot_ids[1:]` in order) would have
    picked `robot_2` -- the first room-feasible candidate -- so the repair
    must now land there instead, at the SAME minimal edit depth (never a
    deeper one: ruling 2 is a same-depth tie-break, not a search widening).
    """

    @pytest.mark.parametrize(
        "order",
        [
            ["robot_1", "robot_2", "robot_3"],
            ["robot_1", "robot_3", "robot_2"],
        ],
    )
    def test_repair_prefers_the_feasibility_gates_candidate_yielder(self, order):
        positions = {"robot_1": (-0.3, 0.0), "robot_2": (1.5, 0.0), "robot_3": (0.3, 0.0)}
        plan = [ProposedPlanLeg(robot_id="robot_1", action="yield")] + [
            ProposedPlanLeg(robot_id=rid, action="cross") for rid in order if rid != "robot_1"
        ]
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2", "robot_3"],
            root_cause="x",
            strategy="yield",
            justification="j",
            yield_robot="robot_1",
            crossing_order=order,
            proposed_plan=plan,
        )
        snapshot = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0)
                for rid, (x, y) in positions.items()
            ],
        )
        verified = verify_and_repair_plan(
            decision,
            snapshot,
            geometry=_geometry(),
            static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
        )

        assert verified.provenance == "repaired"
        yield_legs = [leg for leg in verified.legs if leg.action == "yield"]
        assert len(yield_legs) == 1
        # The feasibility gate's own candidate scan (robot_ids[1:] in order,
        # first room-feasible wins) picks robot_2 over robot_3 here -- never
        # reached by the BFS's fixed enumeration order alone before this fix.
        assert yield_legs[0].robot_id == "robot_2"
        assert not _plan_problems_for_test(
            verified.legs, decision, snapshot, _geometry(), (_WEST_BLOCKER,), "swap"
        )


def _plan_problems_for_test(legs, decision, snapshot, geometry, static_obstacles, mode):
    from reasoning.rag.command_grounder import _plan_problems

    return _plan_problems(legs, decision, snapshot, geometry, static_obstacles, mode)


_POSITIONS_3 = [
    {"robot_1": (-0.3, 0.0), "robot_2": (0.3, 0.0), "robot_3": (1.2, 0.0)},
    {"robot_1": (-0.3, 0.0), "robot_2": (1.5, 0.0), "robot_3": (0.3, 0.0)},
]
_ORDERS_3 = [
    ["robot_1", "robot_2", "robot_3"],
    ["robot_1", "robot_3", "robot_2"],
]
_EAST_BLOCKER = StaticObstacleInput(obstacle_id="o2", x=1.85, y=0.0, size_x_m=0.3, size_y_m=0.3)
_GATES_3 = [
    ((), "off"),
    ((_WEST_BLOCKER,), "off"),
    ((_WEST_BLOCKER,), "swap"),
    ((_WEST_BLOCKER, _EAST_BLOCKER), "swap"),
    ((_WEST_BLOCKER,), "refuse"),
]


class TestDefaultPlanMatchesLegacyThreeRobotMultiPasserMatrix:
    """The plan-ABSENT equivalence claim, exhaustively, not just one fixture:
    every 3-robot multi-passer combination of yielder x crossing order x
    position pair x gate must give `_derive_default_plan` the SAME per-robot
    action as `ground_reasoner_result`'s actual legacy dispatch.
    """

    @pytest.mark.parametrize(
        "yield_robot, order, positions, gate",
        list(itertools.product(["robot_1", "robot_2"], _ORDERS_3, _POSITIONS_3, _GATES_3)),
    )
    def test_default_plan_matches_legacy_three_robot(self, yield_robot, order, positions, gate):
        obstacles, mode = gate
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2", "robot_3"],
            root_cause="x",
            strategy="yield",
            justification="j",
            yield_robot=yield_robot,
            crossing_order=order,
        )
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        command = ground_reasoner_result(
            result,
            robot_positions=positions,
            geometry=_geometry(),
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
        )
        snapshot = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0)
                for rid, (x, y) in positions.items()
            ],
        )
        default_legs = _derive_default_plan(
            decision,
            snapshot,
            geometry=_geometry(),
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
            priorities=None,
        )

        assert {leg.robot_id: leg.action for leg in default_legs} == _project_legacy_command(
            command, list(positions)
        )


# The documented, intentional plan-PRESENT divergence set (code review,
# 2026-10-01), keyed on (yield_robot, tuple(order), sorted positions,
# len(obstacles), mode) -- obstacle COUNT matters within "swap"/"refuse"
# (whether the decided yielder is actually room-infeasible depends on which
# gate's obstacles are active), unlike "off" (ignores obstacles entirely, so
# both of its gates diverge identically). Computed exhaustively against this
# exact matrix/projection (not hand-derived); any NEW divergence this test
# finds that is not in this set means the pin is stale, not that the set is
# wrong -- recompute it, do not silently add to it.
def _divergence_key(yield_robot, order, positions, obstacles, mode):
    return (
        yield_robot,
        tuple(order),
        tuple(sorted(positions.items())),
        len(obstacles),
        mode,
    )


_DIVERGENT_THREE_ROBOT_CELLS: set[tuple] = {
    _divergence_key(
        "robot_1", ("robot_1", "robot_2", "robot_3"), _POSITIONS_3[1], (_WEST_BLOCKER,), "off"
    ),
    _divergence_key("robot_1", ("robot_1", "robot_2", "robot_3"), _POSITIONS_3[1], (), "off"),
    _divergence_key(
        "robot_1", ("robot_1", "robot_2", "robot_3"), _POSITIONS_3[1], (_WEST_BLOCKER,), "swap"
    ),
    _divergence_key(
        "robot_1", ("robot_1", "robot_3", "robot_2"), _POSITIONS_3[0], (_WEST_BLOCKER,), "off"
    ),
    _divergence_key("robot_1", ("robot_1", "robot_3", "robot_2"), _POSITIONS_3[0], (), "off"),
    _divergence_key(
        "robot_1", ("robot_1", "robot_3", "robot_2"), _POSITIONS_3[1], (_WEST_BLOCKER,), "swap"
    ),
    _divergence_key(
        "robot_2", ("robot_1", "robot_2", "robot_3"), _POSITIONS_3[1], (_WEST_BLOCKER,), "off"
    ),
    _divergence_key("robot_2", ("robot_1", "robot_2", "robot_3"), _POSITIONS_3[1], (), "off"),
    _divergence_key(
        "robot_2", ("robot_1", "robot_2", "robot_3"), _POSITIONS_3[1], (_WEST_BLOCKER,), "refuse"
    ),
    _divergence_key(
        "robot_2", ("robot_1", "robot_2", "robot_3"), _POSITIONS_3[1], (_WEST_BLOCKER,), "swap"
    ),
    _divergence_key(
        "robot_2", ("robot_1", "robot_3", "robot_2"), _POSITIONS_3[1], (_WEST_BLOCKER,), "off"
    ),
    _divergence_key("robot_2", ("robot_1", "robot_3", "robot_2"), _POSITIONS_3[1], (), "off"),
    _divergence_key(
        "robot_2", ("robot_1", "robot_3", "robot_2"), _POSITIONS_3[1], (_WEST_BLOCKER,), "refuse"
    ),
    _divergence_key(
        "robot_2", ("robot_1", "robot_3", "robot_2"), _POSITIONS_3[1], (_WEST_BLOCKER,), "swap"
    ),
}


class TestPlanPresentThreeRobotMultiPasserMatrix:
    """`verify_and_repair_plan` against the SAME 3-robot matrix, plan PRESENT
    (a v1-shaped plan naming `yield_robot` as yielder, `order` as the full
    crossing sequence). Pins the divergence set explicitly: any NEW
    divergence not in `_DIVERGENT_THREE_ROBOT_CELLS` fails this test, so a
    future change cannot silently widen it.
    """

    @pytest.mark.parametrize(
        "yield_robot, order, positions, gate",
        list(itertools.product(["robot_1", "robot_2"], _ORDERS_3, _POSITIONS_3, _GATES_3)),
    )
    def test_matches_legacy_except_the_pinned_divergence_set(
        self, yield_robot, order, positions, gate
    ):
        obstacles, mode = gate
        plan = [ProposedPlanLeg(robot_id=yield_robot, action="yield")] + [
            ProposedPlanLeg(robot_id=rid, action="cross") for rid in order if rid != yield_robot
        ]
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2", "robot_3"],
            root_cause="x",
            strategy="yield",
            justification="j",
            yield_robot=yield_robot,
            crossing_order=order,
            proposed_plan=plan,
        )
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        command = ground_reasoner_result(
            result,
            robot_positions=positions,
            geometry=_geometry(),
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
        )
        snapshot = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0)
                for rid, (x, y) in positions.items()
            ],
        )
        verified = verify_and_repair_plan(
            decision,
            snapshot,
            geometry=_geometry(),
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
        )
        v1_actions = _project_legacy_command(command, list(positions))
        engine_actions = {leg.robot_id: leg.action for leg in verified.legs}

        # The hard mode contract, re-asserted matrix-wide: off/refuse never
        # reassign the yielder, however the crossing order comes out.
        if mode in ("off", "refuse"):
            engine_yield = [rid for rid, a in engine_actions.items() if a == "yield"]
            assert not engine_yield or engine_yield[0] == yield_robot

        cell = _divergence_key(yield_robot, order, positions, obstacles, mode)
        if cell in _DIVERGENT_THREE_ROBOT_CELLS:
            assert engine_actions != v1_actions, (
                "pinned as a documented divergence, but it stopped diverging -- "
                "narrow _DIVERGENT_THREE_ROBOT_CELLS"
            )
            # Still must be a genuinely feasible resolution, not a defect.
            assert not _plan_problems_for_test(
                verified.legs, decision, snapshot, _geometry(), obstacles, mode
            )
        else:
            assert engine_actions == v1_actions


class TestPlanCannotOverrideV1YielderWhenUnset:
    """CRITICAL regression (code review, round 5): a plan naming a DIFFERENT
    yielder than `resolve_robot_order(decision)[0]` must never be honored
    verbatim, in ANY `yield_feasibility_mode` including `"swap"`, when
    `decision.yield_robot` is unset. Honoring it would let the VLM's plan
    silently override v1's pre-gate yielder in the common two-robot head-on,
    breaking "v2 changes no v1 outcome semantics there" at the one place it
    matters most. Covers exactly the gap the matrix sweeps above cannot see:
    every `_v1_shaped_plan` there names `yield_robot or "robot_1"`, so it
    never tries the other robot when `yield_robot` is None.
    """

    @pytest.mark.parametrize(
        "positions, use_geometry, gate",
        list(itertools.product(_MATRIX_POSITIONS_2, [False, True], _MATRIX_GATES)),
    )
    def test_plan_naming_the_other_robot_still_matches_v1(self, positions, use_geometry, gate):
        obstacles, mode = gate
        geometry = _geometry() if use_geometry else None
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2"],
            root_cause="head-on aisle conflict",
            strategy="yield",
            justification="robots are stopped face to face",
            yield_robot=None,
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_2", action="yield"),
                ProposedPlanLeg(robot_id="robot_1", action="cross"),
            ],
        )
        result = ReasonerResult(
            request_id="req1",
            decision=decision,
            raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
            ),
        )
        command = ground_reasoner_result(
            result,
            robot_positions=positions,
            geometry=geometry,
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
        )
        snapshot = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0)
                for rid, (x, y) in positions.items()
            ],
        )
        verified = verify_and_repair_plan(
            decision,
            snapshot,
            geometry=geometry,
            static_obstacles=obstacles,
            yield_feasibility_mode=mode,
        )

        assert _ordered_active_legs(verified.legs) == _project_legacy_command_ordered(
            command, list(positions)
        )

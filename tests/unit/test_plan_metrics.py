"""Tests for the pure plan-quality scorer in `reasoning.rag.plan_metrics`."""

import pytest

from reasoning.rag.command_grounder import PlanRepairParams, verify_and_repair_plan
from reasoning.rag.plan_metrics import (
    any_leg_exhausted,
    classify_revision_cause,
    compute_episode_plan_stability,
    compute_plan_churn,
    is_order_only_repair,
    score_decision_artifact,
    score_plan_decision,
    strategy_matches_oracle,
    tabulate_provenance_by_strategy_correctness,
)
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
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


class TestScorePlanDecisionProvenancePaths:
    def test_plan_absent_scores_not_emitted_not_agreement(self):
        decision = _decision()
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        metrics = score_plan_decision(decision, verified)

        assert metrics.emitted is False
        assert metrics.consistent is None
        assert metrics.agreement is False
        assert metrics.edit_distance is None
        assert metrics.provenance == "m3_default"
        assert metrics.rejection_stage == "absent"

    def test_verbatim_plan_scores_emitted_and_agreement(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        metrics = score_plan_decision(decision, verified)

        assert metrics.emitted is True
        assert metrics.consistent is True
        assert metrics.agreement is True
        assert metrics.edit_distance == 0
        assert metrics.provenance == "vlm_verbatim"
        assert metrics.rejection_stage is None

    def test_repaired_plan_scores_emitted_but_not_agreement(self):
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
        metrics = score_plan_decision(decision, verified)

        assert metrics.emitted is True
        assert metrics.consistent is True
        assert metrics.agreement is False
        assert metrics.edit_distance == 1
        assert metrics.provenance == "repaired"

    def test_inconsistent_plan_scores_emitted_but_not_consistent(self):
        # Split 2026-10-03: a parseable plan that breaks the consistency rule
        # WAS emitted; it is the `consistent` flag that records the rejection.
        # Downstream semantics are unchanged: still m3_default, no agreement,
        # no edit distance.
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="yield"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        metrics = score_plan_decision(decision, verified)

        assert metrics.emitted is True
        assert metrics.consistent is False
        assert metrics.agreement is False
        assert metrics.provenance == "m3_default"
        assert metrics.rejection_stage == "inconsistent"
        assert metrics.edit_distance is None

    def test_plan_disagreeing_with_own_yield_robot_scores_not_consistent(self):
        # The second "inconsistent" path (`_plan_disagrees_with_decision_fields`).
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_2", action="yield"),
                ProposedPlanLeg(robot_id="robot_1", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        metrics = score_plan_decision(decision, verified)

        assert metrics.emitted is True
        assert metrics.consistent is False
        assert metrics.rejection_stage == "inconsistent"

    def test_unknown_robot_plan_scores_not_emitted(self):
        # Naming a robot outside the snapshot is unparseable, not inconsistent.
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_7", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        metrics = score_plan_decision(decision, verified)

        assert metrics.emitted is False
        assert metrics.consistent is None
        assert metrics.rejection_stage == "unknown_robot"

    def test_repair_bound_exceeded_still_scores_emitted(self):
        # The plan WAS parseable and consistent; it just could not be
        # feasibly repaired. Emission is about reaching the audit, not
        # surviving it.
        east_blocker = StaticObstacleInput(
            obstacle_id="o2", x=1.85, y=0.0, size_x_m=0.3, size_y_m=0.3
        )
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
            static_obstacles=(_WEST_BLOCKER, east_blocker),
            yield_feasibility_mode="swap",
            repair_params=PlanRepairParams(max_repair_edits=2),
        )
        metrics = score_plan_decision(decision, verified)

        assert metrics.emitted is True
        assert metrics.consistent is True
        assert metrics.provenance == "m3_default"
        assert metrics.rejection_stage == "repair_bound_exceeded"
        # Not 0: a bound-exceeded plan is not indistinguishable from a
        # verbatim (zero-edit) one.
        assert metrics.edit_distance is None


class TestOracleOrderAgreementScoredPreRepair:
    def test_agreement_true_when_proposed_order_matches_oracle(self):
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_3", action="cross"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ],
        )
        frame = _frame(("robot_1", -0.3, 0.0), ("robot_2", 0.3, 0.0), ("robot_3", 1.0, 0.0))
        verified = verify_and_repair_plan(decision, frame, geometry=_geometry())
        metrics = score_plan_decision(decision, verified, oracle_order=["robot_3", "robot_2"])

        assert metrics.oracle_order_agreement is True

    def test_agreement_scored_pre_repair_even_though_order_changes_after(self):
        # The proposed order already matches the oracle; the engine should
        # not need to touch it (regardless, scoring reads the PROPOSED order,
        # not the repaired one).
        frame = _frame(("robot_1", -0.3, 0.0), ("robot_2", 1.5, 0.0), ("robot_3", 0.3, 0.0))
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),  # wrong geometry order
                ProposedPlanLeg(robot_id="robot_3", action="cross"),
            ],
        )
        verified = verify_and_repair_plan(decision, frame, geometry=_geometry())
        assert verified.provenance == "repaired"  # sanity: the engine did reorder it

        # Oracle agrees with the VLM's ORIGINAL (pre-repair) order.
        metrics = score_plan_decision(decision, verified, oracle_order=["robot_2", "robot_3"])
        assert metrics.oracle_order_agreement is True

        # A different oracle (matching the post-repair order) disagrees,
        # proving the score is not silently reading the repaired plan.
        metrics_post = score_plan_decision(decision, verified, oracle_order=["robot_3", "robot_2"])
        assert metrics_post.oracle_order_agreement is False

    def test_agreement_none_when_no_oracle_registered(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        metrics = score_plan_decision(decision, verified, oracle_order=None)
        assert metrics.oracle_order_agreement is None

    def test_agreement_none_when_plan_was_not_emitted(self):
        decision = _decision()  # no plan at all
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        metrics = score_plan_decision(decision, verified, oracle_order=["robot_2"])
        assert metrics.oracle_order_agreement is None

    def test_agreement_none_when_emitted_plan_is_inconsistent(self):
        # Gated on consistency, as before the emitted/consistent split, so the
        # split leaves this metric's population unchanged.
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="yield"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        metrics = score_plan_decision(decision, verified, oracle_order=["robot_2"])
        assert metrics.emitted is True
        assert metrics.oracle_order_agreement is None

    def test_agreement_false_when_plan_omits_an_oracle_robot(self):
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
                ProposedPlanLeg(robot_id="robot_3", action="continue"),
            ],
        )
        frame = _frame(("robot_1", -0.3, 0.0), ("robot_2", 0.3, 0.0), ("robot_3", 1.0, 0.0))
        verified = verify_and_repair_plan(decision, frame, geometry=_geometry())
        metrics = score_plan_decision(decision, verified, oracle_order=["robot_2", "robot_3"])
        assert metrics.oracle_order_agreement is False


def _leg(robot_id: str, action: str) -> ProposedPlanLeg:
    return ProposedPlanLeg(robot_id=robot_id, action=action)


class TestPlanChurn:
    def test_identical_plans_have_zero_churn(self):
        plan = [_leg("robot_1", "yield"), _leg("robot_2", "cross")]
        churn = compute_plan_churn(plan, plan)
        assert churn.changed_robot_ids == ()
        assert churn.churn_fraction == 0.0
        assert churn.revision_type == "incremental"

    def test_one_changed_robot_is_partial_churn(self):
        previous = [_leg("robot_1", "yield"), _leg("robot_2", "cross")]
        current = [_leg("robot_1", "reverse"), _leg("robot_2", "cross")]
        churn = compute_plan_churn(previous, current)
        assert churn.changed_robot_ids == ("robot_1",)
        assert churn.churn_fraction == 0.5
        assert churn.revision_type == "incremental"

    def test_full_rewrite_is_wholesale(self):
        previous = [_leg("robot_1", "yield"), _leg("robot_2", "cross")]
        current = [_leg("robot_1", "wait"), _leg("robot_2", "wait")]
        churn = compute_plan_churn(previous, current, incremental_fraction_bound=0.5)
        assert churn.churn_fraction == 1.0
        assert churn.revision_type == "wholesale"

    def test_robot_only_in_one_plan_counts_as_changed(self):
        previous = [_leg("robot_1", "yield")]
        current = [_leg("robot_1", "yield"), _leg("robot_2", "cross")]
        churn = compute_plan_churn(previous, current)
        assert churn.changed_robot_ids == ("robot_2",)
        assert churn.churn_fraction == 0.5

    def test_boundary_fraction_is_incremental(self):
        previous = [_leg("robot_1", "yield"), _leg("robot_2", "cross")]
        current = [_leg("robot_1", "wait"), _leg("robot_2", "cross")]
        churn = compute_plan_churn(previous, current, incremental_fraction_bound=0.5)
        assert churn.churn_fraction == 0.5
        assert churn.revision_type == "incremental"


class TestRevisionCause:
    def test_no_failures_is_unforced(self):
        assert classify_revision_cause([]) == "unforced"

    def test_any_failure_is_evidence_driven(self):
        assert classify_revision_cause(["robot_1"]) == "evidence_driven"


class TestEpisodePlanStability:
    def test_single_plan_has_zero_replans(self):
        plan = [ProposedPlanLeg(robot_id="robot_1", action="yield")]
        stability = compute_episode_plan_stability([plan])
        assert stability.replan_count == 0
        assert stability.churns == []

    def test_empty_episode_has_zero_replans(self):
        stability = compute_episode_plan_stability([])
        assert stability.replan_count == 0

    def test_three_plans_gives_two_churn_entries(self):
        plan_a = [ProposedPlanLeg(robot_id="robot_1", action="yield")]
        plan_b = [ProposedPlanLeg(robot_id="robot_1", action="wait")]
        plan_c = [ProposedPlanLeg(robot_id="robot_1", action="yield")]
        stability = compute_episode_plan_stability([plan_a, plan_b, plan_c])

        assert stability.replan_count == 2
        assert len(stability.churns) == 2
        assert stability.churns[0].changed_robot_ids == ("robot_1",)
        assert stability.churns[1].changed_robot_ids == ("robot_1",)

    def test_holds_from_plan_tracker_do_not_inflate_replan_count(self):
        # The caller contract the docstring now states: `plans` is one entry
        # per GENUINELY accepted `PlanAcceptance` (held=False), never one
        # entry per analysis. A re-affirmed plan (ruling 2026-10-02) must
        # not count toward replan_count -- this is what makes "zero unforced
        # replans" well-defined on a two-robot head-on re-asked more than
        # once.
        from swarm_orchestrator.plan_tracker import PlanTracker

        from reasoning.rag.command_grounder import VerifiedPlan

        tracker = PlanTracker()
        verified_a = VerifiedPlan(
            legs=[ProposedPlanLeg(robot_id="robot_1", action="yield")],
            provenance="vlm_verbatim",
        )
        verified_b = VerifiedPlan(
            legs=[ProposedPlanLeg(robot_id="robot_1", action="wait")],
            provenance="vlm_verbatim",
        )
        accepted_plans = []
        for verified in (verified_a, verified_a, verified_a, verified_b):
            acceptance = tracker.accept_plan(verified)
            if not acceptance.held:
                accepted_plans.append(acceptance.plan.as_proposed_plan())

        assert tracker.plan_holds == 2  # the two repeats of verified_a
        stability = compute_episode_plan_stability(accepted_plans)
        assert stability.replan_count == 1  # only verified_a -> verified_b


class TestAnyLegExhausted:
    """Step-7a fix (freeze-blocking finding 5): the exhausted-flag scorer."""

    def test_true_when_a_leg_is_exhausted(self):
        assert any_leg_exhausted(["done", "exhausted", "failed"]) is True

    def test_false_when_no_leg_is_exhausted(self):
        assert any_leg_exhausted(["done", "failed", "pending", "active"]) is False

    def test_false_for_an_empty_plan(self):
        assert any_leg_exhausted([]) is False


# ---- verbatim-pilot rulings A, C, D (2026-10-06) ----
#
# Plan blocks below are the pilot's stored `PlanDispatchInfo` shapes
# (docs/reports/2026-10-06-verbatim-pilot.md, "Every dispatched plan"),
# copied field for field from the decision artifacts.

_REORDER_R1_R2 = {
    "op": "reorder",
    "robot_ids": ["robot_1", "robot_2"],
    "reason": (
        "reordered: cross leg has no preceding yield leg to release it; robot_1 and "
        "robot_2 exchanged position"
    ),
}
_B1_ORACLE = ["robot_1", "robot_3"]
_IB10_ACCEPTED = ("junction_clear",)


def _legs(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"robot_id": rid, "action": action} for rid, action in pairs]


def _artifact(
    decision: dict, provenance: str, legs: list[dict], *, edits: list[dict] | None = None,
    dispatch_matches_plan: bool = True, rejection_reason: str | None = None,
) -> dict:
    base = {
        "congestion_detected": True,
        "type": "deadlock",
        "root_cause": "r",
        "justification": "j",
    }
    return {
        "decision": {**base, **decision},
        "plan": {
            "plan_id": 1,
            "provenance": provenance,
            "legs": [{**leg, "status": "pending"} for leg in legs],
            "edits": edits or [],
            "rejection_reason": rejection_reason,
            "dispatch_matches_plan": dispatch_matches_plan,
            "order_equivalent": False,
            "plan_held": False,
        },
    }


def _episode_2() -> dict:
    # ER-2 head-on s43 trigger: correct yielder, listed cross-first.
    proposed = _legs(("robot_1", "cross"), ("robot_2", "yield"))
    return _artifact(
        {"involved_robots": ["robot_1", "robot_2"], "strategy": "yield",
         "yield_robot": "robot_2", "proposed_plan": proposed},
        "repaired", _legs(("robot_2", "yield"), ("robot_1", "cross")), edits=[_REORDER_R1_R2],
    )


def _episode_6() -> dict:
    # ER-2 B1 s42 trigger: verbatim, robot_3 still held (start_delay_sec 80).
    proposed = _legs(("robot_2", "yield"), ("robot_1", "cross"), ("robot_3", "continue"))
    return _artifact(
        {"type": "bottleneck", "involved_robots": ["robot_1", "robot_2"],
         "strategy": "yield", "yield_robot": "robot_2", "proposed_plan": proposed},
        "vlm_verbatim", proposed,
    )


def _episode_7() -> dict:
    # ER-2 B1 s43 trigger: same yielder as episode 6, listed cross-first.
    proposed = _legs(("robot_1", "cross"), ("robot_2", "yield"), ("robot_3", "continue"))
    return _artifact(
        {"type": "bottleneck", "involved_robots": ["robot_1", "robot_2"],
         "strategy": "yield", "yield_robot": "robot_2", "proposed_plan": proposed},
        "repaired",
        _legs(("robot_2", "yield"), ("robot_1", "cross"), ("robot_3", "continue")),
        edits=[_REORDER_R1_R2],
    )


def _ib10_gpt4o_yield_mismatch() -> dict:
    # gpt-4o IB10 s42 at sim 153.5: verbatim multi-passer yield, dispatched
    # differently, strategy outside the cell's accepted set.
    proposed = _legs(
        ("robot_1", "yield"), ("robot_2", "cross"), ("robot_3", "continue"),
        ("robot_4", "continue"),
    )
    return _artifact(
        {"involved_robots": ["robot_1", "robot_2"],
         "strategy": "yield", "yield_robot": "robot_1",
         "crossing_order": ["robot_2", "robot_1"], "proposed_plan": proposed},
        "vlm_verbatim", proposed, dispatch_matches_plan=False,
    )


def _ib10_gpt4o_reverse_match() -> dict:
    # gpt-4o IB10 s42 at sim 67.1: verbatim `reverse` (no leg rule) that
    # dispatched as proposed -- the verbatim-inflation case.
    proposed = _legs(
        ("robot_1", "reverse"), ("robot_2", "reverse"), ("robot_4", "reverse"),
        ("robot_3", "continue"),
    )
    return _artifact(
        {"involved_robots": ["robot_1", "robot_2", "robot_4"],
         "strategy": "reverse", "proposed_plan": proposed},
        "vlm_verbatim", proposed,
    )


class TestRepairedOrderOnlySubclass:
    def test_order_only_true_for_pilot_episode_2_edit_shape(self):
        metrics = score_decision_artifact(_episode_2())
        assert metrics.provenance == "repaired"
        assert metrics.repaired_order_only is True

    def test_order_only_true_for_pilot_episode_7_edit_shape(self):
        metrics = score_decision_artifact(_episode_7())
        assert metrics.provenance == "repaired"
        assert metrics.repaired_order_only is True

    def test_order_only_true_when_the_verifier_reproduces_episode_2_live(self):
        decision = _decision(
            yield_robot="robot_2",
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="cross"),
                ProposedPlanLeg(robot_id="robot_2", action="yield"),
            ],
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        assert [(edit.op, edit.robot_ids) for edit in verified.edits] == [
            ("reorder", ("robot_1", "robot_2"))
        ]
        assert score_plan_decision(decision, verified).repaired_order_only is True

    def test_order_only_false_for_a_swap_repair(self):
        # Pilot episode 1's shape: the swap gate re-grounds the yielder.
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
        assert [edit.op for edit in verified.edits] == ["swap"]
        assert score_plan_decision(decision, verified).repaired_order_only is False

    def test_order_only_false_for_reorder_plus_substitute(self):
        # Pilot episode 8's edit shape.
        edits = [
            {"op": "reorder", "robot_ids": ["robot_1", "robot_4"], "reason": "r"},
            {"op": "substitute", "robot_ids": ["robot_1"], "reason": "s"},
        ]
        proposed = _legs(
            ("robot_1", "cross"), ("robot_2", "wait"), ("robot_3", "reverse"),
            ("robot_4", "reverse"),
        )
        artifact = _artifact(
            {"involved_robots": ["robot_1", "robot_2", "robot_3", "robot_4"],
             "strategy": "junction_clear", "proposed_plan": proposed},
            "repaired",
            _legs(("robot_4", "reverse"), ("robot_2", "wait"), ("robot_3", "reverse"),
                  ("robot_1", "yield")),
            edits=edits, dispatch_matches_plan=False,
        )
        assert score_decision_artifact(artifact).repaired_order_only is False

    def test_order_only_none_when_not_repaired(self):
        assert score_decision_artifact(_episode_6()).repaired_order_only is None

    def test_empty_edit_list_is_not_an_order_only_repair(self):
        assert is_order_only_repair([]) is False


class TestVerbatimDispatchMatched:
    def test_ib10_gpt4o_verbatim_mismatch_is_false(self):
        metrics = score_decision_artifact(
            _ib10_gpt4o_yield_mismatch(), accepted_strategies=_IB10_ACCEPTED
        )
        assert metrics.provenance == "vlm_verbatim"
        assert metrics.verbatim_dispatch_matched is False
        assert metrics.strategy_correct is False

    def test_ib10_gpt4o_verbatim_reverse_matches_but_is_strategy_incorrect(self):
        metrics = score_decision_artifact(
            _ib10_gpt4o_reverse_match(), accepted_strategies=_IB10_ACCEPTED
        )
        assert metrics.agreement is True
        assert metrics.verbatim_dispatch_matched is True
        assert metrics.strategy_correct is False

    def test_none_when_the_dispatch_match_is_unknown(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        assert verified.provenance == "vlm_verbatim"
        assert score_plan_decision(decision, verified).verbatim_dispatch_matched is None

    def test_none_when_the_plan_is_not_verbatim(self):
        metrics = score_decision_artifact(_episode_2())
        assert metrics.provenance == "repaired"
        assert metrics.verbatim_dispatch_matched is None


class TestProvenanceConditionedOnStrategyCorrectness:
    def test_strategy_unscored_without_an_accepted_set(self):
        assert strategy_matches_oracle("yield", None) is None

    def test_strategy_membership_in_the_accepted_set(self):
        assert strategy_matches_oracle("junction_clear", _IB10_ACCEPTED) is True
        assert strategy_matches_oracle("reverse", _IB10_ACCEPTED) is False

    def test_ib10_gpt4o_verbatim_plans_are_conditioned_out_of_the_correct_stratum(self):
        metrics = [
            score_decision_artifact(artifact, accepted_strategies=_IB10_ACCEPTED)
            for artifact in (_ib10_gpt4o_yield_mismatch(), _ib10_gpt4o_reverse_match())
        ]
        table = tabulate_provenance_by_strategy_correctness(metrics)
        assert table["strategy_correct"].plans == 0
        incorrect = table["strategy_incorrect"]
        assert incorrect.plans == 2
        assert incorrect.vlm_verbatim == 2
        assert incorrect.verbatim_dispatch_matched == 1
        assert incorrect.verbatim_dispatch_mismatched == 1
        assert table["strategy_unscored"].plans == 0

    def test_cells_without_accepted_strategies_land_in_the_unscored_stratum(self):
        metrics = [score_decision_artifact(_episode_2()), score_decision_artifact(_episode_7())]
        table = tabulate_provenance_by_strategy_correctness(metrics)
        unscored = table["strategy_unscored"]
        assert unscored.plans == 2
        assert unscored.repaired == 2
        assert unscored.repaired_order_only == 2

    def test_every_stratum_is_present_on_an_empty_input(self):
        table = tabulate_provenance_by_strategy_correctness([])
        assert set(table) == {"strategy_correct", "strategy_incorrect", "strategy_unscored"}
        assert all(stratum.plans == 0 for stratum in table.values())


class TestScoreDecisionArtifact:
    def test_none_without_a_plan_block(self):
        artifact = _episode_6()
        artifact["plan"] = None
        assert score_decision_artifact(artifact) is None

    def test_none_without_a_decision(self):
        artifact = _episode_6()
        artifact["decision"] = None
        assert score_decision_artifact(artifact) is None

    @pytest.mark.parametrize(
        ("proposed", "obstacles", "bound"),
        [
            (None, (), 4),
            ([("robot_1", "yield"), ("robot_7", "cross")], (), 4),
            ([("robot_1", "yield"), ("robot_2", "yield")], (), 4),
            ([("robot_1", "yield"), ("robot_2", "cross")], ("west", "east"), 2),
        ],
        ids=["absent", "unknown_robot", "inconsistent", "repair_bound_exceeded"],
    )
    def test_rejection_stage_round_trips_through_the_stored_plan_block(
        self, proposed, obstacles, bound
    ):
        blockers = {
            "west": _WEST_BLOCKER,
            "east": StaticObstacleInput(obstacle_id="o2", x=1.85, y=0.0, size_x_m=0.3,
                                        size_y_m=0.3),
        }
        decision = _decision(
            proposed_plan=None if proposed is None else [
                ProposedPlanLeg(robot_id=rid, action=action) for rid, action in proposed
            ]
        )
        verified = verify_and_repair_plan(
            decision, _DEADLOCK, geometry=_geometry(),
            static_obstacles=tuple(blockers[name] for name in obstacles),
            yield_feasibility_mode="swap",
            repair_params=PlanRepairParams(max_repair_edits=bound),
        )
        artifact = {
            "decision": decision.model_dump(mode="json"),
            "plan": {
                "provenance": verified.provenance,
                "legs": [leg.model_dump(mode="json") for leg in verified.legs],
                "edits": [edit.model_dump(mode="json") for edit in verified.edits],
                "rejection_reason": verified.rejection_reason,
                "dispatch_matches_plan": True,
            },
        }
        assert score_decision_artifact(artifact) == score_plan_decision(
            decision, verified, dispatch_matches_plan=True
        )


class TestOracleOrderExcludesHeldRobots:
    def test_pilot_episode_6_agrees_once_the_held_robot_is_excluded(self):
        metrics = score_decision_artifact(
            _episode_6(), oracle_order=_B1_ORACLE, held_robot_ids={"robot_3"}
        )
        assert metrics.oracle_order_agreement is True

    def test_pilot_episode_6_was_false_by_construction_without_the_exclusion(self):
        metrics = score_decision_artifact(_episode_6(), oracle_order=_B1_ORACLE)
        assert metrics.oracle_order_agreement is False

    def test_pilot_episode_7_pre_repair_order_agrees_once_the_held_robot_is_excluded(self):
        metrics = score_decision_artifact(
            _episode_7(), oracle_order=_B1_ORACLE, held_robot_ids={"robot_3"}
        )
        assert metrics.oracle_order_agreement is True

    def test_released_robot_named_continue_still_disagrees(self):
        # The exclusion is for held robots only: a released oracle robot
        # given `continue` still cannot agree.
        artifact = _episode_6()
        artifact["decision"]["proposed_plan"] = _legs(
            ("robot_2", "yield"), ("robot_1", "continue"), ("robot_3", "cross")
        )
        artifact["plan"]["legs"] = artifact["decision"]["proposed_plan"]
        metrics = score_decision_artifact(
            artifact, oracle_order=_B1_ORACLE, held_robot_ids={"robot_3"}
        )
        assert metrics.oracle_order_agreement is False

    def test_empty_oracle_without_held_robots_keeps_the_pre_ruling_result(self):
        metrics = score_decision_artifact(_episode_6(), oracle_order=[])
        assert metrics.oracle_order_agreement is True

    def test_none_when_every_oracle_robot_is_held(self):
        metrics = score_decision_artifact(
            _episode_6(), oracle_order=_B1_ORACLE, held_robot_ids={"robot_1", "robot_3"}
        )
        assert metrics.oracle_order_agreement is None

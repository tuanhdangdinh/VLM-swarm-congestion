"""Tests for the pure plan-quality scorer in `reasoning.rag.plan_metrics`."""

from reasoning.rag.command_grounder import verify_and_repair_plan
from reasoning.rag.plan_metrics import (
    any_leg_exhausted,
    classify_revision_cause,
    compute_episode_plan_stability,
    compute_plan_churn,
    score_plan_decision,
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
        assert metrics.agreement is False
        assert metrics.edit_distance == 1
        assert metrics.provenance == "repaired"

    def test_inconsistent_plan_scores_not_emitted(self):
        decision = _decision(
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="yield"),
            ]
        )
        verified = verify_and_repair_plan(decision, _DEADLOCK, geometry=_geometry())
        metrics = score_plan_decision(decision, verified)

        assert metrics.emitted is False
        assert metrics.rejection_stage == "inconsistent"
        assert metrics.edit_distance is None

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
        from reasoning.rag.command_grounder import PlanRepairParams

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

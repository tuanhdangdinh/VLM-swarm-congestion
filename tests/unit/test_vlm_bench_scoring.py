"""Bench metrics on hand-built cases and on the real offline grounder."""

from __future__ import annotations

import pytest

from benchmarks.vlm_bench.grounder_offline import (
    executable_yielders,
    ground_decision,
    refusal_class,
)
from benchmarks.vlm_bench.models import GroundingOutcome, GTCluster
from benchmarks.vlm_bench.scoring import (
    cluster_recalls,
    coverage,
    score_item,
    summarize,
    yielder_agrees,
)
from tests.unit.vlm_bench_fixtures import synthetic_items

A = GTCluster(index=0, onset_s=0.0, end_s=10.0, involved=("robot_1", "robot_2"))
B = GTCluster(index=1, onset_s=0.0, end_s=10.0, involved=("robot_3", "robot_4", "robot_5"))


def _feasible(_item, _decision):
    return GroundingOutcome(feasible=True)


def _refused(_item, _decision):
    reason = "yield refused: no shared lane: robot_1 and robot_2 both run along x"
    return GroundingOutcome(
        feasible=False, refusal_reason=reason, refusal_class=refusal_class(reason)
    )


def test_coverage_true_one_cluster_named():
    assert coverage(["robot_1"], [A]) is True


def test_coverage_false_second_cluster_missed():
    assert coverage(["robot_1", "robot_2"], [A, B]) is False


def test_coverage_true_both_clusters_named():
    assert coverage(["robot_2", "robot_5"], [A, B]) is True


def test_coverage_none_without_clusters():
    assert coverage(["robot_1"], []) is None


def test_cluster_recalls_partial():
    assert cluster_recalls(["robot_1", "robot_3"], [A, B]) == pytest.approx((0.5, 1 / 3))


def test_yielder_agrees_single_reference():
    assert yielder_agrees("robot_1", "robot_1") is True
    assert yielder_agrees("robot_1", "robot_2") is False


def test_yielder_agrees_set_membership():
    assert yielder_agrees("robot_2", ("robot_1", "robot_2")) is True


def test_yielder_agrees_none_for_empty_oracle():
    assert yielder_agrees("robot_1", ()) is None


def test_refusal_class_strips_detail():
    lane = refusal_class("yield refused: ambiguous lane: robot_3 heads 39 deg")
    yielder = refusal_class("yield refused: no feasible yielder (robot_1 0.00 m)")
    assert (lane, yielder) == ("ambiguous lane", "no feasible yielder")


def test_score_item_feasible_decision():
    item = synthetic_items()["aaaa0003"]
    score = score_item(item, item.recorded.decision, "recorded", _feasible)
    assert score.grounding.feasible is True


def test_summarize_feasibility_and_histogram_refused():
    items = synthetic_items()
    scores = [
        score_item(items["aaaa0002"], items["aaaa0002"].recorded.decision, "recorded", _refused),
        score_item(items["aaaa0003"], items["aaaa0003"].recorded.decision, "recorded", _feasible),
    ]
    summary = summarize(scores)
    assert (summary.feasibility.num, summary.feasibility.den) == (1, 2)
    assert summary.refusal_histogram == {"no shared lane": 1}


def test_score_item_partial_coverage_two_clusters():
    item = synthetic_items()["aaaa0002"]
    score = score_item(item, item.recorded.decision, "recorded", _feasible)
    assert score.covered is False
    assert score.cluster_recalls == (0.0, 1.0)


def test_score_item_full_coverage_two_clusters():
    item = synthetic_items()["aaaa0003"]
    assert score_item(item, item.recorded.decision, "recorded", _feasible).covered is True


def test_score_item_f1_against_matched_conflict():
    item = synthetic_items()["aaaa0002"]
    score = score_item(item, item.recorded.decision, "recorded", _feasible)
    assert score.f1_matched == pytest.approx(1.0)


def test_score_item_f1_partial_overlap():
    item = synthetic_items()["aaaa0003"]
    score = score_item(item, item.recorded.decision, "recorded", _feasible)
    assert score.f1_matched == pytest.approx(2 * 2 / (4 + 2))


def test_score_item_oracle_disagrees_when_yielder_not_executable():
    item = synthetic_items()["aaaa0002"]
    score = score_item(
        item, item.recorded.decision, "recorded", _feasible, lambda _i, _d: ("robot_4",)
    )
    assert score.oracle_agree is False


def test_score_item_oracle_agrees_when_yielder_executable():
    item = synthetic_items()["aaaa0002"]
    score = score_item(
        item, item.recorded.decision, "recorded", _feasible, lambda _i, _d: ("robot_3",)
    )
    assert score.oracle_agree is True


def test_score_item_mc_disagreement_on_first_conflict():
    item = synthetic_items()["aaaa0002"]
    score = score_item(item, item.recorded.decision, "recorded", _feasible)
    assert (score.mc_yielder, score.mc_agree) == ("robot_4", False)


def test_summarize_fp_rate_positive_without_conflict():
    items = synthetic_items()
    scores = [
        score_item(items[r], items[r].recorded.decision, "recorded", _feasible)
        for r in ("aaaa0001", "aaaa0003")
    ]
    summary = summarize(scores)
    assert (summary.fp_rate.num, summary.fp_rate.den) == (1, 1)


def test_score_item_cost_fields_absent_without_cost():
    item = synthetic_items()["aaaa0003"]
    score = score_item(item, item.recorded.decision, "classical", _feasible, with_cost=False)
    assert (score.token_usage, score.latency_ms, score.est_usd) == (None, None, None)


def test_summarize_cost_none_when_absent():
    item = synthetic_items()["aaaa0003"]
    score = score_item(item, item.recorded.decision, "classical", _feasible, with_cost=False)
    summary = summarize([score])
    assert (summary.mean_total_tokens, summary.est_usd_total) == (None, None)


def test_ground_decision_real_grounder_refuses_ambiguous_lane():
    item = synthetic_items()["aaaa0002"]
    outcome = ground_decision(item, item.recorded.decision)
    assert outcome.feasible is False
    assert outcome.refusal_class == "ambiguous lane"


def test_ground_decision_real_grounder_accepts_wait():
    item = synthetic_items()["aaaa0003"]
    assert ground_decision(item, item.recorded.decision).feasible is True


def test_ground_decision_none_for_negative():
    item = synthetic_items()["aaaa0005"]
    assert ground_decision(item, item.recorded.decision) is None


def test_executable_yielders_empty_on_refused_scene():
    item = synthetic_items()["aaaa0002"]
    assert executable_yielders(item, item.recorded.decision) == ()

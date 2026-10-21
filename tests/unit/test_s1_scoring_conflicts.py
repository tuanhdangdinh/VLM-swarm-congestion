"""Unit tests for A33(5) GT conflict episodes and A33(6) per-conflict scoring."""

from pathlib import Path

import pytest

from benchmarks.s1_scoring import (
    ConflictParams,
    conflict_episodes,
    read_bundle,
    score_conflicts,
    summarize_conflicts,
)

DATA = Path(__file__).parent / "data" / "s1_scoring"


@pytest.fixture(scope="module")
def detection():
    return score_conflicts(read_bundle(DATA / "detection"))


def test_conflicts_recall_is_none_when_zero_conflicts():
    result = score_conflicts(read_bundle(DATA / "complete"))
    assert result.n_conflicts == 0
    assert result.recall is None
    assert result.precision is None


def test_conflict_episodes_ignore_declared_gt_involved_robots():
    episodes = conflict_episodes(read_bundle(DATA / "detection"))
    assert [e.involved for e in episodes] == [("robot_1", "robot_2"), ("robot_3", "robot_4")]


def test_conflict_episodes_merge_reencounter_within_gap():
    episodes = conflict_episodes(read_bundle(DATA / "detection"))
    assert (episodes[0].onset_s, episodes[0].end_s) == pytest.approx((10.0, 21.8))


def test_conflict_episodes_split_reencounter_when_gap_param_small():
    episodes = conflict_episodes(read_bundle(DATA / "detection"), ConflictParams(merge_gap_s=0.5))
    assert len(episodes) == 3


def test_detection_matched_reports_latency_type_and_f1(detection):
    first = detection.conflicts[0]
    assert first.detected
    assert first.n_matched == 2
    assert first.latency_s == pytest.approx(2.0)
    assert first.type_label == "deadlock"
    assert first.type_correct is True
    assert first.involved_f1 == 1.0


def test_detection_unmatched_censors_latency_at_window_end(detection):
    second = detection.conflicts[1]
    assert not second.detected
    assert second.latency_s is None
    assert second.latency_censored_at_s == pytest.approx(27.8 + 5.0 - 25.0)
    assert second.involved_f1_unconditional == 0.0


def test_detection_false_positive_when_outside_every_window(detection):
    assert detection.n_false_positive == 1
    fp = next(a for a in detection.analyses if a.request_id == "a3")
    assert fp.matched_conflict is None


def test_detection_counts_backend_failed_apart_from_negatives(detection):
    assert (detection.n_positive, detection.n_negative, detection.n_backend_failed) == (3, 1, 1)
    assert detection.recall == 0.5
    assert detection.precision == pytest.approx(2 / 3)


def test_type_correct_follows_accepted_types_param():
    params = ConflictParams(accepted_types=("crowding",))
    result = score_conflicts(read_bundle(DATA / "detection"), params)
    assert result.conflicts[0].type_correct is False


def test_plan_quality_excludes_held_plans_from_replans(detection):
    pq = detection.conflicts[0].plan_quality
    assert (pq.n_scored, pq.n_emitted, pq.n_agreement) == (2, 2, 2)
    assert pq.provenance_counts == {"vlm_verbatim": 2}
    assert pq.replan_count == 0
    assert pq.oracle_order_agreement is None


def test_summarize_conflicts_pools_sum_over_sum_across_episodes(detection):
    empty = score_conflicts(read_bundle(DATA / "complete"))
    summary = summarize_conflicts([detection, empty])
    assert (summary.n_conflicts, summary.n_detected) == (2, 1)
    assert summary.recall == 0.5
    assert summary.precision == pytest.approx(2 / 3)
    assert summary.mean_latency_s == pytest.approx(2.0)
    assert summary.n_latency_censored == 1
    assert summary.n_backend_failed == 1

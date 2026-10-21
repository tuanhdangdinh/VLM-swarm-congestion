"""Unit tests for the A33(7) Arm A - Arm B estimand (synthetic bundles)."""

from pathlib import Path

import pytest

from benchmarks.s1_scoring import arm_delta, pair_by_seed, read_bundle

DATA = Path(__file__).parent / "data" / "s1_scoring"


def _by_name(result):
    return {m.measure: m for m in result.measures}


def test_arm_delta_is_zero_when_arms_identical():
    records = read_bundle(DATA / "detection")
    result = arm_delta([records], [records], reps=200)
    measures = _by_name(result)
    for name in ("throughput_at_tau", "restricted_makespan_s", "detection_recall",
                 "detection_latency_s", "involved_f1", "plan_emission_rate"):
        m = measures[name]
        assert m.estimate == 0.0, name
        assert (m.ci_low, m.ci_high) == (0.0, 0.0), name
        assert m.status == "ok", name


def test_arm_delta_uses_common_window_when_one_arm_censored():
    result = arm_delta(
        [read_bundle(DATA / "complete")], [read_bundle(DATA / "censored")], reps=50
    )
    assert result.pairs[0].tau_s == pytest.approx(7.0)
    measures = _by_name(result)
    assert measures["throughput_at_tau"].estimate == 0.0
    assert measures["restricted_makespan_s"].estimate == 0.0


def test_arm_delta_delay_vacuous_without_table():
    records = read_bundle(DATA / "complete")
    assert _by_name(arm_delta([records], [records], reps=10))[
        "delay_lower_bound_mean_s"
    ].status == "vacuous"


def test_arm_delta_flags_degenerate_arm_b_without_positive_analyses():
    a = read_bundle(DATA / "detection")
    b = a.model_copy(update={"artifacts": []})
    recall = _by_name(arm_delta([a], [b], reps=50))["detection_recall"]
    assert recall.status == "degenerate_arm_b"
    assert recall.estimate == pytest.approx(0.5)


def test_pair_by_seed_reports_unpaired_bundles():
    pairs, un_a, un_b = pair_by_seed(
        [read_bundle(DATA / "complete")], [read_bundle(DATA / "detection")]
    )
    assert pairs == []
    assert (un_a, un_b) == (["complete"], ["detection"])


def test_pair_by_seed_raises_on_duplicate_seed_within_arm():
    records = read_bundle(DATA / "complete")
    with pytest.raises(ValueError):
        pair_by_seed([records, records], [records])


def test_arm_delta_reports_no_pairs_status_when_seeds_disjoint():
    result = arm_delta([read_bundle(DATA / "complete")], [read_bundle(DATA / "detection")])
    assert {m.status for m in result.measures} == {"no_pairs"}

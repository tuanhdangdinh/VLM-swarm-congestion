"""Unit tests for A33(4) per-segment delay_vs_free_flow (synthetic bundles)."""

from pathlib import Path

import pytest

from benchmarks.s1_scoring import load_segment_table, read_bundle, score_delay, summarize_delay

DATA = Path(__file__).parent / "data" / "s1_scoring"
TABLE = load_segment_table(DATA / "free_flow_segments.json")


def test_delay_is_travel_minus_free_flow_when_segment_arrives():
    result = score_delay(read_bundle(DATA / "complete"), TABLE, "synthetic")
    seg = next(s for s in result.segments if s.segment == "A->B")
    # Departure at the first 0.2 m/s sample (rel 1.0); arrival within 0.35 m of B (rel 9.4).
    assert (seg.departure_s, seg.arrival_s) == pytest.approx((1.0, 9.4))
    assert seg.delay_s == pytest.approx(4.4)
    assert seg.reason == "scored"


def test_delay_is_lower_bound_at_t_end_when_segment_censored():
    result = score_delay(read_bundle(DATA / "censored"), TABLE, "synthetic")
    seg = next(s for s in result.segments if s.segment == "A->B")
    assert seg.reason == "censored"
    assert seg.delay_s is None
    assert seg.delay_lower_bound_s == pytest.approx(7.0 - 1.0 - 4.0)
    assert result.n_censored == 2


def test_delay_is_vacuous_without_table():
    result = score_delay(read_bundle(DATA / "complete"), None)
    assert result.vacuous
    assert {s.reason for s in result.segments} == {"no_table"}


def test_delay_is_no_baseline_when_scene_key_missing():
    result = score_delay(read_bundle(DATA / "complete"), TABLE, "mapd_5_s1b")
    assert {s.reason for s in result.segments} == {"no_baseline"}
    assert result.mean_delay_lower_bound_s is None


def test_load_segment_table_raises_without_table_id(tmp_path):
    path = tmp_path / "t.json"
    path.write_text('{"scenes": {}}')
    with pytest.raises(ValueError):
        load_segment_table(path)


def test_summarize_delay_pools_segments_across_episodes():
    results = [score_delay(read_bundle(DATA / name), TABLE, "synthetic")
               for name in ("complete", "censored")]
    summary = summarize_delay(results)
    assert (summary.n_scored, summary.n_censored) == (2, 2)
    assert summary.mean_delay_arrived_s == pytest.approx(4.4)
    assert summary.mean_delay_lower_bound_s == pytest.approx((4.4 + 4.4 + 2.0 + 1.0) / 4)

"""Unit tests for the A33(3) throughput curve (synthetic bundles)."""

from pathlib import Path

import pytest

from benchmarks.s1_scoring import (
    aggregate_throughput,
    read_bundle,
    score_throughput,
    throughput_at,
)

DATA = Path(__file__).parent / "data" / "s1_scoring"


def test_throughput_steps_at_each_dwell_completion():
    result = score_throughput(read_bundle(DATA / "complete"))
    assert result.completion_times_s == pytest.approx([16.0, 17.0])
    assert throughput_at(result, 15.9) == 0.0
    assert throughput_at(result, 16.0) == 0.5
    assert throughput_at(result, 17.0) == 1.0


def test_throughput_is_undefined_after_censoring():
    result = score_throughput(read_bundle(DATA / "censored"))
    assert throughput_at(result, 7.0) == 0.0
    assert throughput_at(result, 7.5) is None


def test_throughput_grid_covers_zero_to_t_end():
    result = score_throughput(read_bundle(DATA / "complete"), grid_s=1.0)
    assert len(result.curve) == 25
    assert result.curve[16] == 0.5


def test_aggregate_throughput_counts_only_episodes_still_observed():
    complete = score_throughput(read_bundle(DATA / "complete"))
    censored = score_throughput(read_bundle(DATA / "censored"))
    points = {p.t: p for p in aggregate_throughput([complete, censored])}
    assert points[5.0].n_at_risk == 2
    assert points[17.0].n_at_risk == 1
    assert points[17.0].mean == 1.0

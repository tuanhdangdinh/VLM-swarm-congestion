"""Unit tests for A33(1) completeness and A33(2) makespan (synthetic bundles)."""

from pathlib import Path

import pytest

from benchmarks.s1_scoring import (
    MakespanResult,
    read_bundle,
    restricted_makespan,
    rmst,
    score_completeness,
    score_makespan,
    summarize_completeness,
)
from benchmarks.s1_scoring.makespan import kaplan_meier

DATA = Path(__file__).parent / "data" / "s1_scoring"


def test_completeness_is_complete_when_every_task_dwelled():
    result = score_completeness(read_bundle(DATA / "complete"))
    assert (result.status, result.tasks_completed, result.tasks_total) == ("complete", 2, 2)


def test_makespan_is_last_dwell_rel_release_when_complete():
    result = score_makespan(read_bundle(DATA / "complete"))
    assert result.value_s == pytest.approx(17.0)
    assert not result.censored
    assert not result.manifest_mismatch


def test_completeness_is_censored_when_budget_cut():
    result = score_completeness(read_bundle(DATA / "censored"))
    assert result.status == "censored"
    assert result.censor_reason == "stop_flag"


def test_makespan_is_right_censored_at_t_end_when_budget_cut():
    result = score_makespan(read_bundle(DATA / "censored"))
    assert result.value_s is None
    assert result.censored
    assert result.censor_time_s == pytest.approx(7.0)
    assert result.censor_reason == "stop_flag"


def test_completeness_is_failed_when_horizon_reached_incomplete():
    result = score_completeness(read_bundle(DATA / "detection"))
    assert result.status == "failed"


def test_restricted_makespan_raises_when_censored_before_tau():
    censored = score_makespan(read_bundle(DATA / "censored"))
    with pytest.raises(ValueError):
        restricted_makespan(censored, 20.0)


def test_restricted_makespan_is_tau_when_censored_at_tau():
    censored = score_makespan(read_bundle(DATA / "censored"))
    assert restricted_makespan(censored, 7.0) == 7.0


def _m(value, censor=None):
    return MakespanResult(
        value_s=value, censored=value is None, censor_time_s=censor,
        censor_reason="horizon" if value is None else None,
        manifest_makespan_s=None, manifest_mismatch=False,
    )


def test_kaplan_meier_drops_survival_at_each_event_with_censoring():
    steps = kaplan_meier([_m(10.0), _m(None, 15.0), _m(20.0)])
    assert [(s.t, round(s.survival, 4)) for s in steps] == [(10.0, 0.6667), (20.0, 0.0)]


def test_rmst_is_tau_when_no_episode_completes():
    assert rmst([_m(None, 30.0), _m(None, 40.0)], 30.0) == pytest.approx(30.0)


def test_rmst_integrates_km_curve_up_to_tau():
    # S(t) = 1 on [0, 10), 0.5 on [10, 20); area to 20 = 10 + 5.
    assert rmst([_m(10.0), _m(None, 30.0)], 20.0) == pytest.approx(15.0)


def test_summarize_completeness_excludes_censored_from_wilson_denominator():
    results = [score_completeness(read_bundle(DATA / name))
               for name in ("complete", "censored", "detection")]
    summary = summarize_completeness(results)
    assert (summary.n_complete, summary.n_uncensored, summary.n_censored) == (1, 2, 1)
    assert summary.proportion == 0.5
    assert 0.0 < summary.ci_low < 0.5 < summary.ci_high < 1.0

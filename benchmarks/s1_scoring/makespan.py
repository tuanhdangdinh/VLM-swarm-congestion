"""Completeness and makespan (= time-to-full-resolution) for S1 episodes.

Implements prereg-v3 A33(1) (completeness) and A33(2) (makespan, which the v2
design maps one-to-one onto time-to-full-resolution), with the A33(0)
censoring rule: an incomplete episode's makespan is right-censored at T_end,
never missing. Across episodes: Kaplan-Meier and the restricted mean (RMST),
never a naive mean over censored runs.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict

from benchmarks.s1_scoring.bundle_io import BundleRecords, CensorReason

CompletenessStatus = Literal["complete", "failed", "censored"]

# A33(2): makespan vs M5's manifest makespan_sim_sec cross-check tolerance.
MANIFEST_TOLERANCE_S = 0.05


class CompletenessResult(BaseModel):
    """A33(1) completeness of one episode."""

    model_config = ConfigDict(frozen=True)

    tasks_completed: int
    tasks_total: int
    status: CompletenessStatus
    censor_reason: CensorReason
    t_end_rel: float


class MakespanResult(BaseModel):
    """A33(2) makespan of one episode; right-censored when incomplete."""

    model_config = ConfigDict(frozen=True)

    value_s: float | None
    censored: bool
    censor_time_s: float | None
    censor_reason: CensorReason | None
    manifest_makespan_s: float | None
    manifest_mismatch: bool


def completion_times(records: BundleRecords) -> list[float]:
    """Rel-s of every `dwell_complete` event up to T_end, sorted.

    Args:
        records: The bundle records.

    Returns:
        The completion times.
    """
    times = [
        records.m1_to_rel(e["sim_t"])
        for e in records.task_events
        if e["event"] == "dwell_complete"
    ]
    return sorted(t for t in times if t <= records.t_end_rel)


def score_completeness(records: BundleRecords) -> CompletenessResult:
    """Score A33(1): tasks completed by T_end and the tri-state status.

    Args:
        records: The bundle records.

    Returns:
        `complete` when every task finished, `failed` when the run reached its
        horizon incomplete, `censored` when it was cut earlier.
    """
    done = len(completion_times(records))
    if done >= records.tasks_total:
        status: CompletenessStatus = "complete"
    elif records.censor_reason == "horizon":
        status = "failed"
    else:
        status = "censored"
    return CompletenessResult(
        tasks_completed=done,
        tasks_total=records.tasks_total,
        status=status,
        censor_reason=records.censor_reason,
        t_end_rel=records.t_end_rel,
    )


def score_makespan(records: BundleRecords) -> MakespanResult:
    """Score A33(2): the latest dwell completion, or right-censored at T_end.

    Args:
        records: The bundle records.

    Returns:
        The makespan record, with M5's manifest value cross-checked.
    """
    times = completion_times(records)
    manifest = records.manifest_makespan_sim_sec
    if len(times) >= records.tasks_total:
        value = times[-1]
        mismatch = manifest is not None and abs(manifest - value) > MANIFEST_TOLERANCE_S
        return MakespanResult(
            value_s=value, censored=False, censor_time_s=None, censor_reason=None,
            manifest_makespan_s=manifest, manifest_mismatch=mismatch,
        )
    return MakespanResult(
        value_s=None, censored=True, censor_time_s=records.t_end_rel,
        censor_reason=records.censor_reason, manifest_makespan_s=manifest,
        manifest_mismatch=manifest is not None,
    )


def restricted_makespan(result: MakespanResult, tau_s: float) -> float:
    """min(makespan, tau), exactly observable when the episode is observed to tau.

    Args:
        result: The makespan record.
        tau_s: The restriction time in rel-s.

    Returns:
        The restricted makespan.

    Raises:
        ValueError: When the episode is censored before tau.
    """
    if result.value_s is not None:
        return min(result.value_s, tau_s)
    if result.censor_time_s is not None and result.censor_time_s + 1e-9 < tau_s:
        raise ValueError("episode censored before tau; restricted makespan unobserved")
    return tau_s


class KaplanMeierStep(BaseModel):
    """One step of a Kaplan-Meier survival curve."""

    model_config = ConfigDict(frozen=True)

    t: float
    survival: float
    n_at_risk: int


def kaplan_meier(results: Sequence[MakespanResult]) -> list[KaplanMeierStep]:
    """Kaplan-Meier estimate of P(makespan > t) across episodes (A33(2)).

    Args:
        results: One makespan record per episode.

    Returns:
        The steps at each observed completion time.
    """
    obs = sorted(
        (r.value_s if r.value_s is not None else r.censor_time_s, r.value_s is not None)
        for r in results
        if r.value_s is not None or r.censor_time_s is not None
    )
    steps: list[KaplanMeierStep] = []
    survival = 1.0
    n = len(obs)
    i = 0
    while i < len(obs):
        t = obs[i][0]
        events = sum(1 for tt, e in obs if tt == t and e)
        ties = sum(1 for tt, _ in obs if tt == t)
        if events:
            survival *= 1.0 - events / n
            steps.append(KaplanMeierStep(t=t, survival=survival, n_at_risk=n))
        n -= ties
        i += ties
    return steps


def rmst(results: Sequence[MakespanResult], tau_s: float) -> float:
    """Restricted mean makespan up to tau: the area under the KM curve.

    Args:
        results: One makespan record per episode.
        tau_s: The restriction time.

    Returns:
        The RMST in seconds (tau when no episode completes before tau).
    """
    if not math.isfinite(tau_s) or tau_s < 0:
        raise ValueError("tau_s must be finite and non-negative")
    area, last_t, survival = 0.0, 0.0, 1.0
    for step in kaplan_meier(results):
        if step.t >= tau_s:
            break
        area += survival * (step.t - last_t)
        last_t, survival = step.t, step.survival
    return area + survival * (tau_s - last_t)


class CompletenessSummary(BaseModel):
    """A33(1) across-episode completeness: Wilson CI over non-censored episodes."""

    model_config = ConfigDict(frozen=True)

    n_complete: int
    n_uncensored: int
    n_censored: int
    proportion: float | None
    ci_low: float | None
    ci_high: float | None


def summarize_completeness(
    results: Sequence[CompletenessResult], z: float = 1.959963984540054
) -> CompletenessSummary:
    """Proportion `complete` among non-censored episodes with a Wilson CI (A33(1)).

    Args:
        results: One completeness record per episode.
        z: The normal quantile (95% by default).

    Returns:
        The summary; proportion and CI are None when every episode is censored.
    """
    uncensored = [r for r in results if r.status != "censored"]
    n = len(uncensored)
    k = sum(1 for r in uncensored if r.status == "complete")
    if not n:
        return CompletenessSummary(
            n_complete=0, n_uncensored=0, n_censored=len(results), proportion=None,
            ci_low=None, ci_high=None,
        )
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return CompletenessSummary(
        n_complete=k, n_uncensored=n, n_censored=len(results) - n, proportion=p,
        ci_low=max(0.0, centre - half), ci_high=min(1.0, centre + half),
    )

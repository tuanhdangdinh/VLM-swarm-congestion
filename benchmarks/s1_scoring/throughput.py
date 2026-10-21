"""Throughput curve for S1 episodes: completed tasks / 25 over sim time.

Implements prereg-v3 A33(3). The per-episode curve is a right-continuous step
function defined on [0, T_end] only; it is never carried flat past censoring.
Across episodes the mean is taken over the episodes still observed at t, with
n_at_risk reported (A33(3) PROPOSAL).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from benchmarks.s1_scoring.bundle_io import BundleRecords, CensorReason
from benchmarks.s1_scoring.makespan import completion_times

# A33(3) PROPOSAL: grid step for the reported curve.
DEFAULT_GRID_S = 1.0


class ThroughputResult(BaseModel):
    """A33(3) throughput curve of one episode."""

    model_config = ConfigDict(frozen=True)

    completion_times_s: list[float]
    tasks_total: int
    t_end_rel: float
    censor_reason: CensorReason
    grid_s: float
    curve: list[float]


class ThroughputPoint(BaseModel):
    """One point of the across-episode mean curve."""

    model_config = ConfigDict(frozen=True)

    t: float
    mean: float | None
    n_at_risk: int


def throughput_at(result: ThroughputResult, t: float) -> float | None:
    """Theta(t) = completions up to t / tasks_total, or None past T_end.

    Args:
        result: The episode's throughput record.
        t: Rel-s.

    Returns:
        The fraction, or None when t lies beyond the observation end.
    """
    if t > result.t_end_rel + 1e-9:
        return None
    return sum(1 for c in result.completion_times_s if c <= t) / result.tasks_total


def score_throughput(records: BundleRecords, grid_s: float = DEFAULT_GRID_S) -> ThroughputResult:
    """Score A33(3): completion events and the curve on a fixed grid.

    Args:
        records: The bundle records.
        grid_s: Grid step in seconds (A33(3) PROPOSAL default 1.0).

    Returns:
        The throughput record; `curve[k]` is Theta(k * grid_s) for k * grid_s <= T_end.
    """
    if grid_s <= 0:
        raise ValueError("grid_s must be positive")
    times = completion_times(records)
    n_points = int(math.floor(records.t_end_rel / grid_s + 1e-9)) + 1
    curve = []
    j = 0
    for k in range(n_points):
        t = k * grid_s
        while j < len(times) and times[j] <= t:
            j += 1
        curve.append(j / records.tasks_total)
    return ThroughputResult(
        completion_times_s=times, tasks_total=records.tasks_total,
        t_end_rel=records.t_end_rel, censor_reason=records.censor_reason,
        grid_s=grid_s, curve=curve,
    )


def aggregate_throughput(
    results: Sequence[ThroughputResult], grid_s: float = DEFAULT_GRID_S
) -> list[ThroughputPoint]:
    """Mean Theta(t) over the episodes still observed at t (A33(3) PROPOSAL).

    Args:
        results: One throughput record per episode.
        grid_s: Grid step in seconds.

    Returns:
        One point per grid time up to the longest observation.
    """
    if not results:
        return []
    horizon = max(r.t_end_rel for r in results)
    points = []
    for k in range(int(math.floor(horizon / grid_s + 1e-9)) + 1):
        t = k * grid_s
        values = [v for v in (throughput_at(r, t) for r in results) if v is not None]
        points.append(
            ThroughputPoint(
                t=t, mean=sum(values) / len(values) if values else None, n_at_risk=len(values)
            )
        )
    return points

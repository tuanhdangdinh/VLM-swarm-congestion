"""All A33 per-episode measures of one S1 bundle in one record.

Reads the bundle once (A33(0)) and applies A33(1)-(6). The record is what
the CLI writes, one JSON line per bundle.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from benchmarks.s1_scoring.bundle_io import BundleRecords, CensorReason, read_bundle
from benchmarks.s1_scoring.conflicts import ConflictParams, ConflictsResult, score_conflicts
from benchmarks.s1_scoring.delay import (
    DEFAULT_SCENE_KEY,
    DEFAULT_TABLE,
    DelayResult,
    TableArg,
    score_delay,
)
from benchmarks.s1_scoring.makespan import (
    CompletenessResult,
    MakespanResult,
    score_completeness,
    score_makespan,
)
from benchmarks.s1_scoring.throughput import DEFAULT_GRID_S, ThroughputResult, score_throughput

A33_REF = "prereg-v3 A33 (feat/v3-design f7a8d62)"


class EpisodeScores(BaseModel):
    """Every A33 per-episode measure of one bundle."""

    model_config = ConfigDict(frozen=True)

    a33: str = A33_REF
    bundle: str
    seed: int | None
    gt_offset_s: float
    t_end_rel: float
    abs_gt_end: float
    censor_reason: CensorReason
    completeness: CompletenessResult
    makespan: MakespanResult
    throughput: ThroughputResult
    delay: DelayResult
    conflicts: ConflictsResult


def score_records(
    records: BundleRecords,
    *,
    table: TableArg = DEFAULT_TABLE,
    scene_key: str = DEFAULT_SCENE_KEY,
    grid_s: float = DEFAULT_GRID_S,
    params: ConflictParams | None = None,
) -> EpisodeScores:
    """Apply A33(1)-(6) to already-read records.

    Args:
        records: The bundle records (possibly truncated, A33(7)).
        table: The segment-keyed free-flow table, None (delay vacuous), or
            `DEFAULT_TABLE` (the scene key's frozen table, A34 R8).
        scene_key: The free-flow scene key.
        grid_s: The throughput grid step.
        params: The per-conflict PROPOSAL parameters.

    Returns:
        The episode record.
    """
    return EpisodeScores(
        bundle=records.bundle,
        seed=records.seed,
        gt_offset_s=records.gt_offset_s,
        t_end_rel=records.t_end_rel,
        abs_gt_end=records.abs_gt_end,
        censor_reason=records.censor_reason,
        completeness=score_completeness(records),
        makespan=score_makespan(records),
        throughput=score_throughput(records, grid_s),
        delay=score_delay(records, table, scene_key),
        conflicts=score_conflicts(records, params),
    )


def score_bundle(
    bundle: Path,
    *,
    table: TableArg = DEFAULT_TABLE,
    scene_key: str = DEFAULT_SCENE_KEY,
    grid_s: float = DEFAULT_GRID_S,
    params: ConflictParams | None = None,
) -> EpisodeScores:
    """Read one bundle and apply A33(1)-(6).

    Args:
        bundle: The bundle directory.
        table: The segment-keyed free-flow table, None (delay vacuous), or
            `DEFAULT_TABLE` (the scene key's frozen table, A34 R8).
        scene_key: The free-flow scene key.
        grid_s: The throughput grid step.
        params: The per-conflict PROPOSAL parameters.

    Returns:
        The episode record.
    """
    return score_records(
        read_bundle(Path(bundle)), table=table, scene_key=scene_key, grid_s=grid_s, params=params
    )

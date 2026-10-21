"""S1 confirmatory scorers, implementing prereg-v3 A33 exactly.

Definitions: `docs/superpowers/specs/2026-10-06-prereg-v3-design.md` A33
(`feat/v3-design` f7a8d62), frozen before any confirmatory S1 episode ran.
One module per measure family: `makespan` (A33(1)-(2)), `throughput`
(A33(3)), `delay` (A33(4)), `conflicts` (A33(5)-(6)), `arm_delta` (A33(7));
`bundle_io` reads the bundle records on one clock (A33(0)).

CLI: `python -m benchmarks.s1_scoring <bundle_dir>... --out results.jsonl`.
"""

from benchmarks.s1_scoring.arm_delta import ArmDeltaResult, MeasureDelta, arm_delta, pair_by_seed
from benchmarks.s1_scoring.bundle_io import (
    BundleRecords,
    NotAnEpisodeError,
    gt_offset,
    read_bundle,
    truncate,
)
from benchmarks.s1_scoring.conflicts import (
    ConflictEpisode,
    ConflictParams,
    ConflictScore,
    ConflictsResult,
    ConflictsSummary,
    conflict_episodes,
    pair_intervals,
    score_conflicts,
    summarize_conflicts,
)
from benchmarks.s1_scoring.delay import (
    DEFAULT_TABLE,
    S1B_FREE_FLOW_TABLE,
    DelayResult,
    DelaySummary,
    SegmentDelay,
    SegmentTable,
    default_segment_table,
    load_segment_table,
    score_delay,
    summarize_delay,
)
from benchmarks.s1_scoring.episode import EpisodeScores, score_bundle, score_records
from benchmarks.s1_scoring.makespan import (
    CompletenessResult,
    CompletenessSummary,
    MakespanResult,
    kaplan_meier,
    restricted_makespan,
    rmst,
    score_completeness,
    score_makespan,
    summarize_completeness,
)
from benchmarks.s1_scoring.throughput import (
    ThroughputResult,
    aggregate_throughput,
    score_throughput,
    throughput_at,
)

__all__ = [
    "DEFAULT_TABLE",
    "S1B_FREE_FLOW_TABLE",
    "ArmDeltaResult",
    "BundleRecords",
    "CompletenessResult",
    "CompletenessSummary",
    "ConflictEpisode",
    "ConflictParams",
    "ConflictScore",
    "ConflictsResult",
    "ConflictsSummary",
    "DelayResult",
    "DelaySummary",
    "EpisodeScores",
    "MakespanResult",
    "MeasureDelta",
    "NotAnEpisodeError",
    "SegmentDelay",
    "SegmentTable",
    "ThroughputResult",
    "aggregate_throughput",
    "arm_delta",
    "conflict_episodes",
    "gt_offset",
    "kaplan_meier",
    "default_segment_table",
    "load_segment_table",
    "pair_by_seed",
    "pair_intervals",
    "read_bundle",
    "restricted_makespan",
    "rmst",
    "score_bundle",
    "score_completeness",
    "score_conflicts",
    "score_delay",
    "score_makespan",
    "score_records",
    "score_throughput",
    "summarize_completeness",
    "summarize_conflicts",
    "summarize_delay",
    "throughput_at",
    "truncate",
]

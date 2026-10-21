"""Per-segment delay_vs_free_flow for S1 task streams.

Implements prereg-v3 A33(4). A segment is one task leg A->B of one robot;
departure and arrival follow the two timing rules frozen in every free-flow
table (`own_departure`, `gt_within_0.35_stay_0.5`), applied per segment, and
the baseline comes from a table keyed by (scene, "A->B"). Without a table or
a key the delay is null (`no_table` / `no_baseline`), never fabricated. A34 R8
(owner ruling on A33(10) D3) froze the 2026-10-10 S1b harvest as
`data/free_flow_s1b_2026-10-10.json`; it is the default table for every
`mapd_5*` scene key, and an explicit `table=None` still means `no_table`.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict

from benchmarks.s1_scoring.bundle_io import BundleRecords

# Frozen free-flow timing rules (scripts/free_flow_table.py, free_flow_v2.json).
DEPARTURE_SPEED_MPS = 0.03
ARRIVAL_TOLERANCE_M = 0.35
ARRIVAL_STAY_M = 0.5
# A33(4) PROPOSAL default scene key (ruled A34 R11).
DEFAULT_SCENE_KEY = "mapd_5_s1b"
# A34 R8: the frozen S1b free-flow table, default for `mapd_5*` scene keys.
S1B_FREE_FLOW_TABLE: Final = Path(__file__).parent / "data" / "free_flow_s1b_2026-10-10.json"
S1B_FREE_FLOW_MD5: Final = "b4002d7697f4d8f27c31792a9b269162"
DEFAULT_TABLE_SCENE_PREFIX: Final = "mapd_5"

SegmentReason = Literal["scored", "censored", "never_departed", "no_table", "no_baseline"]


class SegmentTable(BaseModel):
    """A free-flow table keyed by (scene, segment), A33(4)."""

    model_config = ConfigDict(frozen=True)

    table_id: str
    scenes: dict[str, dict[str, float]]

    def lookup(self, scene: str, segment: str) -> float | None:
        """Return the free-flow time of `segment` in `scene`, or None."""
        return self.scenes.get(scene, {}).get(segment)


def load_segment_table(path: Path) -> SegmentTable:
    """Load a segment-keyed free-flow table.

    The file is JSON with `table_id` and `scenes.<scene>.<"A->B">.time_sec`.

    Args:
        path: The table file.

    Returns:
        The table.

    Raises:
        ValueError: When `table_id` is missing or an entry has no `time_sec`.
    """
    raw = json.loads(Path(path).read_text())
    if not raw.get("table_id"):
        raise ValueError(f"{path}: free-flow table has no table_id")
    scenes: dict[str, dict[str, float]] = {}
    for scene, entries in (raw.get("scenes") or {}).items():
        scenes[scene] = {}
        for segment, entry in entries.items():
            if "->" not in segment:
                continue
            if not isinstance(entry, dict) or "time_sec" not in entry:
                raise ValueError(f"{path}: {scene}/{segment} has no time_sec")
            scenes[scene][segment] = float(entry["time_sec"])
    return SegmentTable(table_id=raw["table_id"], scenes=scenes)


class _DefaultTable:
    """Sentinel type: resolve the table from the scene key (A34 R8)."""

    def __repr__(self) -> str:
        return "DEFAULT_TABLE"


DEFAULT_TABLE: Final = _DefaultTable()
TableArg = SegmentTable | None | _DefaultTable


def default_segment_table(scene_key: str) -> SegmentTable | None:
    """Return the frozen free-flow table registered for `scene_key`, if any.

    Args:
        scene_key: The free-flow scene key.

    Returns:
        The frozen S1b table (A34 R8) for a `mapd_5*` key, else None.
    """
    if not scene_key.startswith(DEFAULT_TABLE_SCENE_PREFIX):
        return None
    return load_segment_table(S1B_FREE_FLOW_TABLE)


def resolve_table(table: TableArg, scene_key: str) -> SegmentTable | None:
    """Resolve a table argument: `DEFAULT_TABLE` means the scene key's frozen table.

    Args:
        table: A table, None (no table), or `DEFAULT_TABLE`.
        scene_key: The free-flow scene key.

    Returns:
        The table to score with, or None.
    """
    if isinstance(table, _DefaultTable):
        return default_segment_table(scene_key)
    return table


class SegmentDelay(BaseModel):
    """One task segment's A33(4) delay record (times in rel-s)."""

    model_config = ConfigDict(frozen=True)

    robot_id: str
    task_index: int
    segment: str
    issued_s: float
    departure_s: float | None
    arrival_s: float | None
    free_flow_s: float | None
    delay_s: float | None
    delay_lower_bound_s: float | None
    reason: SegmentReason


class DelayResult(BaseModel):
    """A33(4) per-episode delay summary."""

    model_config = ConfigDict(frozen=True)

    table_id: str | None
    scene_key: str
    segments: list[SegmentDelay]
    n_scored: int
    n_censored: int
    mean_delay_arrived_s: float | None
    mean_delay_lower_bound_s: float | None
    vacuous: bool


def _segment_times(
    records: BundleRecords, robot_id: str, node_xy: tuple[float, float],
    issued_gt: float, window_end_gt: float,
) -> tuple[float | None, float | None]:
    track = [(s.t, s.poses[robot_id]) for s in records.gt if robot_id in s.poses]
    track = [(t, p) for t, p in track if issued_gt <= t <= window_end_gt]
    departure = next((t for t, p in track if p[2] > DEPARTURE_SPEED_MPS), None)
    if departure is None:
        return None, None
    after = [
        (t, math.hypot(p[0] - node_xy[0], p[1] - node_xy[1])) for t, p in track if t >= departure
    ]
    for i, (t, d) in enumerate(after):
        if d <= ARRIVAL_TOLERANCE_M and all(later <= ARRIVAL_STAY_M for _, later in after[i:]):
            return departure, t
    return departure, None


def _segment_events(records: BundleRecords) -> dict[tuple[str, int], dict[str, Any]]:
    out: dict[tuple[str, int], dict[str, Any]] = {}
    for e in records.task_events:
        if e.get("task_index") is None or e["event"] not in ("issued", "dwell_complete"):
            continue
        out.setdefault((e["robot_id"], int(e["task_index"])), {})[e["event"]] = e["sim_t"]
    return out


def score_delay(
    records: BundleRecords,
    table: TableArg = DEFAULT_TABLE,
    scene_key: str = DEFAULT_SCENE_KEY,
) -> DelayResult:
    """Score A33(4) for every issued segment of one episode.

    Args:
        records: The bundle records.
        table: The segment-keyed free-flow table; None (then every segment is
            `no_table` and the result is vacuous); or `DEFAULT_TABLE` (the
            default), which loads the frozen table of a `mapd_5*` scene key.
        scene_key: The table's scene key (A33(4) default `mapd_5_s1b`).

    Returns:
        The per-segment records and the episode summary.
    """
    table = resolve_table(table, scene_key)
    events = _segment_events(records)
    end_gt = records.abs_gt_end
    segments: list[SegmentDelay] = []
    for (robot_id, k), ev in sorted(events.items()):
        if "issued" not in ev or robot_id not in records.sequences:
            continue
        seq = records.sequences[robot_id]
        if k >= len(seq):
            continue
        origin = records.start_nodes.get(robot_id) if k == 0 else seq[k - 1]
        segment = f"{origin}->{seq[k]}"
        issued_gt = ev["issued"] - records.gt_offset_s
        window_end_gt = (
            ev["dwell_complete"] - records.gt_offset_s if "dwell_complete" in ev else end_gt
        )
        departure, arrival = _segment_times(
            records, robot_id, records.nodes[seq[k]], issued_gt, min(window_end_gt, end_gt)
        )
        ff = table.lookup(scene_key, segment) if table is not None else None
        rel = records.gt_to_rel
        dep_rel = rel(departure) if departure is not None else None
        arr_rel = rel(arrival) if arrival is not None else None
        delay = lower = None
        if table is None:
            reason: SegmentReason = "no_table"
        elif ff is None:
            reason = "no_baseline"
        elif dep_rel is None:
            reason = "never_departed"
        elif arr_rel is None:
            reason = "censored"
            lower = records.t_end_rel - dep_rel - ff
        else:
            reason = "scored"
            delay = arr_rel - dep_rel - ff
        segments.append(
            SegmentDelay(
                robot_id=robot_id, task_index=k, segment=segment,
                issued_s=records.m1_to_rel(ev["issued"]), departure_s=dep_rel,
                arrival_s=arr_rel, free_flow_s=ff, delay_s=delay,
                delay_lower_bound_s=lower, reason=reason,
            )
        )
    arrived = [s.delay_s for s in segments if s.delay_s is not None]
    charged = [
        s.delay_s if s.delay_s is not None else s.delay_lower_bound_s
        for s in segments
        if s.reason in ("scored", "censored")
    ]
    return DelayResult(
        table_id=table.table_id if table is not None else None,
        scene_key=scene_key,
        segments=segments,
        n_scored=len(arrived),
        n_censored=sum(1 for s in segments if s.reason == "censored"),
        mean_delay_arrived_s=sum(arrived) / len(arrived) if arrived else None,
        mean_delay_lower_bound_s=sum(charged) / len(charged) if charged else None,
        vacuous=not charged,
    )


class DelaySummary(BaseModel):
    """A33(4) across-episode delay: segments pooled over episodes."""

    model_config = ConfigDict(frozen=True)

    n_episodes: int
    n_scored: int
    n_censored: int
    mean_delay_arrived_s: float | None
    mean_delay_lower_bound_s: float | None


def summarize_delay(results: Sequence[DelayResult]) -> DelaySummary:
    """Pool every episode's segments (A33(4) across-episode PROPOSAL).

    Args:
        results: One delay record per episode.

    Returns:
        The pooled means over arrived segments and, as a lower bound, over
        departed segments; None where no segment qualifies.
    """
    segments = [s for r in results for s in r.segments]
    arrived = [s.delay_s for s in segments if s.delay_s is not None]
    charged = [
        s.delay_s if s.delay_s is not None else s.delay_lower_bound_s
        for s in segments
        if s.reason in ("scored", "censored")
    ]
    return DelaySummary(
        n_episodes=len(results),
        n_scored=len(arrived),
        n_censored=sum(1 for s in segments if s.reason == "censored"),
        mean_delay_arrived_s=sum(arrived) / len(arrived) if arrived else None,
        mean_delay_lower_bound_s=sum(charged) / len(charged) if charged else None,
    )

"""Arm A - Arm B delta per regime on a per-pair common window.

Implements prereg-v3 A33(7). R3.6a item 4 registers only "CI estimation of
the delta per regime"; the method below is A33's PROPOSAL on the v2 rev-6
precedent: pairs by `stream_start.seed`, a per-pair common window
tau_i = min(T_end,A, T_end,B) (the dollar cap stops only the arm that spends),
every measure recomputed on both episodes truncated at tau_i, the mean of the
paired differences (pooled-ratio difference for proportions) and a paired
percentile bootstrap over pairs. Every delta is conditional on owner
decision D4 (Arm B identity and parity).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict

from benchmarks.s1_scoring.bundle_io import BundleRecords, truncate
from benchmarks.s1_scoring.conflicts import ConflictParams
from benchmarks.s1_scoring.delay import DEFAULT_SCENE_KEY, DEFAULT_TABLE, TableArg, resolve_table
from benchmarks.s1_scoring.episode import A33_REF, EpisodeScores, score_records
from benchmarks.s1_scoring.makespan import restricted_makespan

# A33(7) PROPOSAL bootstrap settings.
DEFAULT_REPS = 10000
DEFAULT_BOOT_SEED = 20261021
DEFAULT_LEVEL = 0.95

DeltaStatus = Literal["ok", "vacuous", "degenerate_arm_b", "no_pairs"]


class PairWindow(BaseModel):
    """One seed-matched pair and its common window."""

    model_config = ConfigDict(frozen=True)

    seed: int | None
    bundle_a: str
    bundle_b: str
    tau_s: float


class MeasureDelta(BaseModel):
    """One A33(7) delta with its paired bootstrap CI."""

    model_config = ConfigDict(frozen=True)

    measure: str
    estimate: float | None
    ci_low: float | None
    ci_high: float | None
    arm_a_value: float | None
    arm_b_value: float | None
    n_pairs: int
    status: DeltaStatus


class ArmDeltaResult(BaseModel):
    """A33(7) Arm A - Arm B result for one regime."""

    model_config = ConfigDict(frozen=True)

    a33: str = A33_REF
    conditional_on: str = "owner decision D4 (Arm B identity and parity, A13(iii))"
    pairs: list[PairWindow]
    unpaired_a: list[str]
    unpaired_b: list[str]
    reps: int
    boot_seed: int
    level: float
    measures: list[MeasureDelta]


def pair_by_seed(
    arm_a: Sequence[BundleRecords], arm_b: Sequence[BundleRecords]
) -> tuple[list[tuple[BundleRecords, BundleRecords]], list[str], list[str]]:
    """Pair episodes by `stream_start.seed` (A33(7) PROPOSAL).

    Args:
        arm_a: Arm A records.
        arm_b: Arm B records.

    Returns:
        The pairs (in Arm A order) and the unpaired bundle names of each arm.

    Raises:
        ValueError: When a seed appears twice within one arm.
    """
    def index(arm: Sequence[BundleRecords], name: str) -> dict[int | None, BundleRecords]:
        out: dict[int | None, BundleRecords] = {}
        for r in arm:
            if r.seed in out:
                raise ValueError(f"arm {name}: seed {r.seed} appears twice")
            out[r.seed] = r
        return out

    a, b = index(arm_a, "A"), index(arm_b, "B")
    pairs = [(a[s], b[s]) for s in a if s in b]
    return (
        pairs,
        [a[s].bundle for s in a if s not in b],
        [b[s].bundle for s in b if s not in a],
    )


def _ci(stats: list[float], level: float) -> tuple[float | None, float | None]:
    if not stats:
        return None, None
    lo, hi = np.quantile(np.asarray(stats), [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(lo), float(hi)


def _mean_delta(
    name: str, values: list[tuple[float | None, float | None]], idx: np.ndarray, level: float
) -> MeasureDelta:
    d = np.asarray(
        [a - b if a is not None and b is not None else np.nan for a, b in values], dtype=float
    )
    usable = [(a, b) for a, b in values if a is not None and b is not None]
    if not usable:
        return MeasureDelta(
            measure=name, estimate=None, ci_low=None, ci_high=None, arm_a_value=None,
            arm_b_value=None, n_pairs=0, status="vacuous",
        )
    # Resample pairs (indices into all pairs); a pair without a value drops out.
    boot = [float(np.nanmean(d[i])) for i in idx if not np.all(np.isnan(d[i]))]
    lo, hi = _ci(boot, level)
    return MeasureDelta(
        measure=name, estimate=float(np.nanmean(d)), ci_low=lo, ci_high=hi,
        arm_a_value=float(np.mean([a for a, _ in usable])),
        arm_b_value=float(np.mean([b for _, b in usable])),
        n_pairs=len(usable), status="ok",
    )


def _ratio_delta(
    name: str,
    parts: list[tuple[float, float, float, float]],
    idx: np.ndarray,
    level: float,
    degenerate: bool,
) -> MeasureDelta:
    arr = np.asarray(parts, dtype=float).reshape(-1, 4)

    def stat(rows: np.ndarray) -> tuple[float | None, float | None, float | None]:
        na, da, nb, db = rows.sum(axis=0) if len(rows) else (0.0, 0.0, 0.0, 0.0)
        ra = na / da if da else None
        rb = nb / db if db else None
        return (ra - rb if ra is not None and rb is not None else None), ra, rb

    est, ra, rb = stat(arr)
    if est is None:
        return MeasureDelta(
            measure=name, estimate=None, ci_low=None, ci_high=None, arm_a_value=ra,
            arm_b_value=rb, n_pairs=len(parts),
            status="degenerate_arm_b" if degenerate else "vacuous",
        )
    boot = [s for s in (stat(arr[i])[0] for i in idx) if s is not None]
    lo, hi = _ci(boot, level)
    return MeasureDelta(
        measure=name, estimate=est, ci_low=lo, ci_high=hi, arm_a_value=ra, arm_b_value=rb,
        n_pairs=len(parts), status="degenerate_arm_b" if degenerate else "ok",
    )


def _conflict_parts(
    ea: EpisodeScores, eb: EpisodeScores, part: Callable[[EpisodeScores], tuple[float, float]]
) -> tuple[float, float, float, float]:
    na, da = part(ea)
    nb, db = part(eb)
    return na, da, nb, db


def _recall(e: EpisodeScores) -> tuple[float, float]:
    return float(e.conflicts.n_detected), float(e.conflicts.n_conflicts)


def _latency(e: EpisodeScores) -> tuple[float, float]:
    lat = [c.latency_s for c in e.conflicts.conflicts if c.latency_s is not None]
    return float(sum(lat)), float(len(lat))


def _type_accuracy(e: EpisodeScores) -> tuple[float, float]:
    det = [c for c in e.conflicts.conflicts if c.detected]
    return float(sum(1 for c in det if c.type_correct)), float(len(det))


def _f1(e: EpisodeScores) -> tuple[float, float]:
    det = [c.involved_f1 for c in e.conflicts.conflicts if c.involved_f1 is not None]
    return float(sum(det)), float(len(det))


def _emission(e: EpisodeScores) -> tuple[float, float]:
    pq = [c.plan_quality for c in e.conflicts.conflicts]
    return float(sum(p.n_emitted for p in pq)), float(sum(p.n_scored for p in pq))


def _agreement(e: EpisodeScores) -> tuple[float, float]:
    pq = [c.plan_quality for c in e.conflicts.conflicts]
    return float(sum(p.n_agreement for p in pq)), float(sum(p.n_scored for p in pq))


def arm_delta(
    arm_a: Sequence[BundleRecords],
    arm_b: Sequence[BundleRecords],
    *,
    table: TableArg = DEFAULT_TABLE,
    scene_key: str = DEFAULT_SCENE_KEY,
    params: ConflictParams | None = None,
    reps: int = DEFAULT_REPS,
    boot_seed: int = DEFAULT_BOOT_SEED,
    level: float = DEFAULT_LEVEL,
) -> ArmDeltaResult:
    """Estimate every A33(7) Arm A - Arm B delta for one regime.

    Args:
        arm_a: Arm A (Layer-2-on) bundle records.
        arm_b: Arm B bundle records.
        table: The segment-keyed free-flow table, None (delay vacuous), or
            `DEFAULT_TABLE` (the scene key's frozen table, A34 R8).
        scene_key: The free-flow scene key.
        params: The per-conflict PROPOSAL parameters.
        reps: Bootstrap replicates.
        boot_seed: Bootstrap RNG seed.
        level: CI level.

    Returns:
        One delta per measure, each with its paired percentile bootstrap CI.
    """
    table = resolve_table(table, scene_key)
    pairs, un_a, un_b = pair_by_seed(arm_a, arm_b)
    windows: list[PairWindow] = []
    scored: list[tuple[EpisodeScores, EpisodeScores, float]] = []
    for ra, rb in pairs:
        tau = min(ra.t_end_rel, rb.t_end_rel)
        windows.append(PairWindow(seed=ra.seed, bundle_a=ra.bundle, bundle_b=rb.bundle, tau_s=tau))
        ea = score_records(truncate(ra, tau), table=table, scene_key=scene_key, params=params)
        eb = score_records(truncate(rb, tau), table=table, scene_key=scene_key, params=params)
        scored.append((ea, eb, tau))
    if not scored:
        return ArmDeltaResult(
            pairs=[], unpaired_a=un_a, unpaired_b=un_b, reps=reps, boot_seed=boot_seed,
            level=level,
            measures=[
                MeasureDelta(measure=m, estimate=None, ci_low=None, ci_high=None,
                             arm_a_value=None, arm_b_value=None, n_pairs=0, status="no_pairs")
                for m in ("throughput_at_tau", "restricted_makespan_s",
                          "delay_lower_bound_mean_s", "detection_recall", "detection_latency_s",
                          "type_accuracy", "involved_f1", "plan_emission_rate",
                          "plan_agreement_rate")
            ],
        )
    rng = np.random.default_rng(boot_seed)
    idx = rng.integers(0, len(scored), size=(reps, len(scored)))
    degenerate = sum(eb.conflicts.n_positive for _, eb, _ in scored) == 0
    measures = [
        _mean_delta(
            "throughput_at_tau",
            [(ea.completeness.tasks_completed / ea.completeness.tasks_total,
              eb.completeness.tasks_completed / eb.completeness.tasks_total)
             for ea, eb, _ in scored],
            idx, level,
        ),
        _mean_delta(
            "restricted_makespan_s",
            [(restricted_makespan(ea.makespan, tau), restricted_makespan(eb.makespan, tau))
             for ea, eb, tau in scored],
            idx, level,
        ),
        _mean_delta(
            "delay_lower_bound_mean_s",
            [(ea.delay.mean_delay_lower_bound_s, eb.delay.mean_delay_lower_bound_s)
             for ea, eb, _ in scored],
            idx, level,
        ),
    ]
    for name, part in (
        ("detection_recall", _recall),
        ("detection_latency_s", _latency),
        ("type_accuracy", _type_accuracy),
        ("involved_f1", _f1),
        ("plan_emission_rate", _emission),
        ("plan_agreement_rate", _agreement),
    ):
        measures.append(
            _ratio_delta(
                name, [_conflict_parts(ea, eb, part) for ea, eb, _ in scored], idx, level,
                degenerate,
            )
        )
    return ArmDeltaResult(
        pairs=windows, unpaired_a=un_a, unpaired_b=un_b, reps=reps, boot_seed=boot_seed,
        level=level, measures=measures,
    )

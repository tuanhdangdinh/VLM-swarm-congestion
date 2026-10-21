"""Per-conflict S1 scoring: GT conflict episodes, detection, type, F1, plan quality.

Implements prereg-v3 A33(5) (GT conflict episodes from the S1 Monte Carlo's
0.45 m centre-gap encounter, merged into multi-robot episodes) and A33(6)
(analysis classes, the detection matching rule, latency, type label,
involved-set F1 and plan-quality metrics (i-a)-(vi) via the tracked
`reasoning.rag.plan_metrics`). Every A33 PROPOSAL choice is a field of
`ConflictParams`, defaulted to A33's value.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from benchmarks.s1_scoring.bundle_io import BundleRecords
from reasoning.rag.plan_metrics import (
    classify_revision_cause,
    compute_episode_plan_stability,
    score_decision_artifact,
)
from reasoning.vlm.models import ProposedPlanLeg

# A33(5) REGISTERED: the S1 MC encounter definition (s1_live_conflict_stats).
ENCOUNTER_M = 0.45

AnalysisClass = Literal["backend_failed", "negative", "positive"]


class ConflictParams(BaseModel):
    """A33(5)/(6) PROPOSAL parameters, defaulted to the A33 values."""

    model_config = ConfigDict(frozen=True)

    merge_gap_s: float = Field(default=2.0, ge=0.0)
    min_duration_s: float = Field(default=0.0, ge=0.0)
    pre_s: float = Field(default=0.0, ge=0.0)
    post_s: float = Field(default=5.0, ge=0.0)
    min_overlap: int = Field(default=1, ge=1)
    accepted_types: tuple[str, ...] = ("deadlock",)
    incremental_fraction_bound: float = Field(default=0.5, ge=0.0, le=1.0)


class PairInterval(BaseModel):
    """A maximal run of GT samples with one pair's centre gap below 0.45 m."""

    model_config = ConfigDict(frozen=True)

    pair: tuple[str, str]
    onset_s: float
    end_s: float
    min_gap_m: float
    to_end: bool


class ConflictEpisode(BaseModel):
    """A33(5) GT conflict episode: a connected component of pair intervals."""

    model_config = ConfigDict(frozen=True)

    index: int
    onset_s: float
    end_s: float
    involved: tuple[str, ...]
    pairs: tuple[tuple[str, str], ...]
    to_end: bool


class Analysis(BaseModel):
    """One decision artifact, classified per A33(6)."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    t_s: float
    analysis_class: AnalysisClass
    involved: tuple[str, ...]
    type_label: str | None
    matched_conflict: int | None


class PlanQuality(BaseModel):
    """A33(6) plan-quality metrics (i-a)-(vi) over a set of analyses."""

    model_config = ConfigDict(frozen=True)

    n_scored: int
    n_emitted: int
    n_consistent: int
    n_agreement: int
    emission_rate: float | None
    consistency_rate: float | None
    agreement_rate: float | None
    mean_edit_distance: float | None
    provenance_counts: dict[str, int]
    oracle_order_agreement: None = None
    replan_count: int
    churn_fractions: list[float]
    revision_types: list[str]
    revision_causes: list[str]


class ConflictScore(BaseModel):
    """A33(6) scores of one GT conflict episode."""

    model_config = ConfigDict(frozen=True)

    conflict: ConflictEpisode
    detected: bool
    n_matched: int
    latency_s: float | None
    latency_censored_at_s: float | None
    type_label: str | None
    type_correct: bool | None
    involved_f1: float | None
    involved_f1_unconditional: float
    plan_quality: PlanQuality


class ConflictsResult(BaseModel):
    """A33(6) per-run detection aggregates and per-conflict scores."""

    model_config = ConfigDict(frozen=True)

    params: ConflictParams
    conflicts: list[ConflictScore]
    analyses: list[Analysis]
    n_conflicts: int
    n_detected: int
    recall: float | None
    n_positive: int
    n_false_positive: int
    precision: float | None
    n_negative: int
    n_backend_failed: int
    type_label_counts: dict[str, int]
    run_plan_quality: PlanQuality


def pair_intervals(records: BundleRecords) -> list[PairInterval]:
    """Every GT pair encounter (centre gap < 0.45 m), times in rel-s (A33(5)).

    Args:
        records: The bundle records.

    Returns:
        The intervals, sorted by onset.
    """
    open_: dict[tuple[str, str], dict[str, float]] = {}
    out: list[PairInterval] = []
    for s in records.gt:
        ids = sorted(s.poses, key=lambda r: (len(r), r))
        for a, b in itertools.combinations(ids, 2):
            pa, pb = s.poses[a], s.poses[b]
            gap = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
            key = (a, b)
            if gap < ENCOUNTER_M:
                iv = open_.setdefault(key, {"onset": s.t, "end": s.t, "min": gap})
                iv["end"] = s.t
                iv["min"] = min(iv["min"], gap)
            elif key in open_:
                iv = open_.pop(key)
                out.append(_interval(records, key, iv, to_end=False))
    out += [_interval(records, key, iv, to_end=True) for key, iv in open_.items()]
    return sorted(out, key=lambda iv: (iv.onset_s, iv.pair))


def _interval(records, key, iv, to_end):
    return PairInterval(
        pair=key, onset_s=records.gt_to_rel(iv["onset"]), end_s=records.gt_to_rel(iv["end"]),
        min_gap_m=iv["min"], to_end=to_end,
    )


def conflict_episodes(
    records: BundleRecords, params: ConflictParams | None = None
) -> list[ConflictEpisode]:
    """Merge pair intervals into A33(5) conflict episodes.

    Two intervals join when they share a robot and are separated by at most
    `merge_gap_s` (overlap counts as separation 0); components shorter than
    `min_duration_s` are dropped.

    Args:
        records: The bundle records.
        params: The PROPOSAL parameters (A33 defaults when None).

    Returns:
        The conflict episodes, indexed in onset order.
    """
    params = params or ConflictParams()
    ivs = pair_intervals(records)
    parent = list(range(len(ivs)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in itertools.combinations(range(len(ivs)), 2):
        a, b = ivs[i], ivs[j]
        if not set(a.pair) & set(b.pair):
            continue
        gap = max(a.onset_s, b.onset_s) - min(a.end_s, b.end_s)
        if gap <= params.merge_gap_s:
            parent[find(i)] = find(j)
    groups: dict[int, list[PairInterval]] = {}
    for i, iv in enumerate(ivs):
        groups.setdefault(find(i), []).append(iv)
    episodes = []
    for members in groups.values():
        onset = min(m.onset_s for m in members)
        end = max(m.end_s for m in members)
        if end - onset < params.min_duration_s:
            continue
        robots = {r for m in members for r in m.pair}
        episodes.append(
            (onset, end, tuple(sorted(robots, key=lambda r: (len(r), r))),
             tuple(sorted({m.pair for m in members})), any(m.to_end for m in members))
        )
    episodes.sort()
    return [
        ConflictEpisode(index=k, onset_s=o, end_s=e, involved=inv, pairs=prs, to_end=te)
        for k, (o, e, inv, prs, te) in enumerate(episodes)
    ]


def classify_analysis(records: BundleRecords, artifact: dict[str, Any]) -> Analysis:
    """Classify one decision artifact per A33(6), unmatched.

    Args:
        records: The bundle records (for the clock).
        artifact: One parsed decision artifact.

    Returns:
        The analysis with `matched_conflict` None.
    """
    decision = artifact.get("decision")
    if not decision:
        cls: AnalysisClass = "backend_failed"
        involved: tuple[str, ...] = ()
    elif decision.get("congestion_detected") is True:
        cls = "positive"
        involved = tuple(decision.get("involved_robots") or ())
    else:
        cls = "negative"
        involved = ()
    return Analysis(
        request_id=str(artifact.get("request_id") or ""),
        t_s=records.m1_to_rel(artifact["scene"]["stamp"]),
        analysis_class=cls,
        involved=involved,
        type_label=decision.get("type") if decision else None,
        matched_conflict=None,
    )


def match_analysis(
    analysis: Analysis, conflicts: Sequence[ConflictEpisode], params: ConflictParams
) -> int | None:
    """Apply the A33(6) matching rule to one positive analysis.

    Args:
        analysis: The analysis.
        conflicts: The episode's GT conflicts.
        params: The PROPOSAL parameters.

    Returns:
        The matched conflict index, or None.
    """
    if analysis.analysis_class != "positive":
        return None
    best: tuple[tuple[float, ...], int] | None = None
    for c in conflicts:
        if not c.onset_s - params.pre_s <= analysis.t_s <= c.end_s + params.post_s:
            continue
        overlap = len(set(analysis.involved) & set(c.involved))
        if overlap < params.min_overlap:
            continue
        started = c.onset_s <= analysis.t_s
        key = (-overlap, 0 if started else 1, -c.onset_s if started else c.onset_s)
        if best is None or key < best[0]:
            best = (key, c.index)
    return best[1] if best else None


def f1(predicted: Sequence[str], truth: Sequence[str]) -> float:
    """Set F1 = 2|P & T| / (|P| + |T|); 0.0 when both are empty.

    Args:
        predicted: The predicted robot set.
        truth: The ground-truth robot set.

    Returns:
        The F1 score.
    """
    p, t = set(predicted), set(truth)
    return 2 * len(p & t) / (len(p) + len(t)) if p or t else 0.0


def plan_quality(
    artifacts: Sequence[dict[str, Any]], incremental_fraction_bound: float
) -> PlanQuality:
    """A33(6) (i-a)-(vi) over artifacts, via the tracked plan_metrics scorer.

    Args:
        artifacts: Decision artifacts in time order.
        incremental_fraction_bound: Churn fraction at or below which a
            revision is incremental (PROPOSAL 0.5).

    Returns:
        The plan-quality summary; (v) is always None (no S1 order oracle).
    """
    scored = [
        m for m in (
            score_decision_artifact(a, oracle_order=None, accepted_strategies=None)
            for a in artifacts
        ) if m is not None
    ]
    emitted = [m for m in scored if m.emitted]
    consistent = [m for m in emitted if m.consistent]
    agreement = [m for m in scored if m.agreement]
    edits = [m.edit_distance for m in scored if m.edit_distance is not None]
    plans: list[list[ProposedPlanLeg]] = []
    causes: list[str] = []
    seen: set[Any] = set()
    for a in artifacts:
        block = a.get("plan")
        if not block or block.get("plan_held") or block.get("plan_id") in seen:
            continue
        seen.add(block.get("plan_id"))
        plans.append(
            [ProposedPlanLeg(robot_id=leg["robot_id"], action=leg["action"])
             for leg in block.get("legs") or []]
        )
        if len(plans) > 1:
            failed = [
                leg["robot_id"] for leg in (a.get("plan_state") or {}).get("legs") or []
                if leg.get("status") in ("failed", "exhausted")
            ]
            causes.append(classify_revision_cause(failed))
    stability = compute_episode_plan_stability(
        plans, incremental_fraction_bound=incremental_fraction_bound
    )
    return PlanQuality(
        n_scored=len(scored), n_emitted=len(emitted), n_consistent=len(consistent),
        n_agreement=len(agreement),
        emission_rate=len(emitted) / len(scored) if scored else None,
        consistency_rate=len(consistent) / len(emitted) if emitted else None,
        agreement_rate=len(agreement) / len(scored) if scored else None,
        mean_edit_distance=sum(edits) / len(edits) if edits else None,
        provenance_counts=dict(Counter(m.provenance for m in scored)),
        replan_count=stability.replan_count,
        churn_fractions=[c.churn_fraction for c in stability.churns],
        revision_types=[c.revision_type for c in stability.churns],
        revision_causes=causes,
    )


def score_conflicts(
    records: BundleRecords, params: ConflictParams | None = None
) -> ConflictsResult:
    """Score A33(6) for one episode: every GT conflict and every analysis.

    Args:
        records: The bundle records.
        params: The PROPOSAL parameters (A33 defaults when None).

    Returns:
        Per-conflict scores and per-run detection aggregates. Recall is None
        with zero conflicts, precision None with zero positive analyses.
    """
    params = params or ConflictParams()
    conflicts = conflict_episodes(records, params)
    analyses = []
    by_conflict: dict[int, list[tuple[Analysis, dict[str, Any]]]] = {}
    for artifact in records.artifacts:
        a = classify_analysis(records, artifact)
        a = a.model_copy(update={"matched_conflict": match_analysis(a, conflicts, params)})
        analyses.append(a)
        if a.matched_conflict is not None:
            by_conflict.setdefault(a.matched_conflict, []).append((a, artifact))
    scores = []
    for c in conflicts:
        matched = by_conflict.get(c.index, [])
        first = matched[0][0] if matched else None
        label = first.type_label if first else None
        scores.append(
            ConflictScore(
                conflict=c,
                detected=first is not None,
                n_matched=len(matched),
                latency_s=first.t_s - c.onset_s if first else None,
                latency_censored_at_s=(
                    None if first else min(c.end_s + params.post_s, records.t_end_rel) - c.onset_s
                ),
                type_label=label,
                type_correct=(label in params.accepted_types) if first else None,
                involved_f1=f1(first.involved, c.involved) if first else None,
                involved_f1_unconditional=f1(first.involved, c.involved) if first else 0.0,
                plan_quality=plan_quality(
                    [art for _, art in matched], params.incremental_fraction_bound
                ),
            )
        )
    positives = [a for a in analyses if a.analysis_class == "positive"]
    fps = [a for a in positives if a.matched_conflict is None]
    detected = sum(1 for s in scores if s.detected)
    return ConflictsResult(
        params=params,
        conflicts=scores,
        analyses=analyses,
        n_conflicts=len(conflicts),
        n_detected=detected,
        recall=detected / len(conflicts) if conflicts else None,
        n_positive=len(positives),
        n_false_positive=len(fps),
        precision=(len(positives) - len(fps)) / len(positives) if positives else None,
        n_negative=sum(1 for a in analyses if a.analysis_class == "negative"),
        n_backend_failed=sum(1 for a in analyses if a.analysis_class == "backend_failed"),
        type_label_counts=dict(Counter(a.type_label for a in positives if a.type_label)),
        run_plan_quality=plan_quality(records.artifacts, params.incremental_fraction_bound),
    )


class ConflictsSummary(BaseModel):
    """A33(6) across-episode per-conflict measures, pooled as in A33(7)."""

    model_config = ConfigDict(frozen=True)

    n_episodes: int
    n_conflicts: int
    n_detected: int
    recall: float | None
    n_positive: int
    precision: float | None
    type_accuracy: float | None
    mean_latency_s: float | None
    n_latency_censored: int
    mean_involved_f1: float | None
    emission_rate: float | None
    agreement_rate: float | None
    n_backend_failed: int


def summarize_conflicts(results: Sequence[ConflictsResult]) -> ConflictsSummary:
    """Pool per-conflict measures over episodes (A33(6) across-episode PROPOSAL).

    Args:
        results: One conflicts record per episode.

    Returns:
        Sum-over-sum rates and means over detected conflicts; None where a
        denominator is zero.
    """
    def ratio(num: float, den: float) -> float | None:
        return num / den if den else None

    conflicts = [c for r in results for c in r.conflicts]
    detected = [c for c in conflicts if c.detected]
    positives = sum(r.n_positive for r in results)
    plans = [c.plan_quality for c in conflicts]
    return ConflictsSummary(
        n_episodes=len(results),
        n_conflicts=len(conflicts),
        n_detected=len(detected),
        recall=ratio(len(detected), len(conflicts)),
        n_positive=positives,
        precision=ratio(positives - sum(r.n_false_positive for r in results), positives),
        type_accuracy=ratio(sum(1 for c in detected if c.type_correct), len(detected)),
        mean_latency_s=ratio(sum(c.latency_s or 0.0 for c in detected), len(detected)),
        n_latency_censored=sum(1 for c in conflicts if c.latency_censored_at_s is not None),
        mean_involved_f1=ratio(sum(c.involved_f1 or 0.0 for c in detected), len(detected)),
        emission_rate=ratio(sum(p.n_emitted for p in plans), sum(p.n_scored for p in plans)),
        agreement_rate=ratio(sum(p.n_agreement for p in plans), sum(p.n_scored for p in plans)),
        n_backend_failed=sum(r.n_backend_failed for r in results),
    )

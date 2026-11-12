"""Bench metrics (spec `docs/specs/v4_vlm_bench.md` §Scoring Metrics).

The set-level metrics are pure functions. `score_item` joins them with the
offline grounder for one (item, decision) pair; `summarize` pools item scores.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from benchmarks.s1_scoring.conflicts import f1, plan_quality
from benchmarks.vlm_bench.models import BenchItem, GroundingOutcome, GTCluster, ItemScore
from benchmarks.vlm_bench.oracle import classical_yielder, matched_conflict, mc_yielder

GroundFn = Callable[[BenchItem, dict[str, Any] | None], GroundingOutcome | None]
OracleFn = Callable[[BenchItem, dict[str, Any]], tuple[str, ...]]


def cluster_named(involved: Sequence[str], cluster: GTCluster, min_overlap: int = 1) -> bool:
    """Whether a decision's involved set names a GT cluster (shares ≥ `min_overlap` robots).

    Args:
        involved: The decision's involved robots.
        cluster: The GT cluster.
        min_overlap: A33(6) `min_overlap`.

    Returns:
        True when named.
    """
    return len(set(involved) & set(cluster.involved)) >= min_overlap


def coverage(involved: Sequence[str], clusters: Sequence[GTCluster]) -> bool | None:
    """Whether every GT cluster is named; None when there is no cluster.

    Args:
        involved: The decision's involved robots (empty for a negative).
        clusters: The item's active GT clusters.

    Returns:
        The coverage flag, or None.
    """
    if not clusters:
        return None
    return all(cluster_named(involved, c) for c in clusters)


def cluster_recalls(involved: Sequence[str], clusters: Sequence[GTCluster]) -> tuple[float, ...]:
    """Per-cluster recall |D ∩ I_c| / |I_c|.

    Args:
        involved: The decision's involved robots.
        clusters: The item's active GT clusters.

    Returns:
        One recall per cluster.
    """
    d = set(involved)
    return tuple(len(d & set(c.involved)) / len(c.involved) for c in clusters if c.involved)


def yielder_agrees(chosen: str | None, reference: str | Sequence[str] | None) -> bool | None:
    """Agreement of a chosen yielder with a reference yielder or set.

    Args:
        chosen: The decision's yielder.
        reference: A single yielder, a set of acceptable yielders, or None.

    Returns:
        None when either side is missing or the set is empty; else membership.
    """
    if chosen is None or reference is None:
        return None
    if isinstance(reference, str):
        return chosen == reference
    if not reference:
        return None
    return chosen in reference


def score_item(
    item: BenchItem,
    decision: dict[str, Any] | None,
    source: str,
    ground_fn: GroundFn,
    oracle_fn: OracleFn | None = None,
    with_cost: bool = True,
) -> ItemScore:
    """Score one decision on one item.

    Args:
        item: The bench item.
        decision: The decision dict, or None (backend failed / refused).
        source: "recorded", "classical" or "replay:<variant>".
        ground_fn: Offline grounder (`grounder_offline.ground_decision`).
        oracle_fn: Geometry oracle (`grounder_offline.executable_yielders`);
            None skips it.
        with_cost: Attach the recorded tokens, latency and dollars.

    Returns:
        The item score.
    """
    valid = decision is not None
    positive = bool(decision and decision.get("congestion_detected") is True)
    involved = tuple(decision.get("involved_robots") or ()) if positive else ()
    clusters = item.gt.clusters
    grounding = ground_fn(item, decision) if positive else None
    matched = matched_conflict(item, decision)
    by_index = {c.index: c for c in item.gt.episode_conflicts}
    f1_matched = f1(involved, by_index[matched].involved) if matched is not None else None
    f1_uncond = (f1_matched or 0.0) if clusters else None
    yielder = None
    oracle_set = None
    if positive and decision.get("strategy") == "yield":
        yielder = decision.get("yield_robot")
        if yielder and oracle_fn is not None:
            oracle_set = oracle_fn(item, decision)
    cls_yielder = classical_yielder(item) if source != "classical" else None
    mc = mc_yielder(item, matched)
    live_refused = (
        bool(item.live.refusal_reason) if source == "recorded" and positive else None
    )
    usage = item.recorded.token_usage if with_cost else None
    return ItemScore(
        item_id=item.item_id,
        batch=item.batch,
        episode=item.episode,
        source=source,
        decision=decision,
        valid=valid,
        positive=positive,
        strategy=decision.get("strategy") if decision else None,
        involved=involved,
        grounding=grounding,
        live_refused=live_refused,
        n_clusters=len(clusters),
        covered=coverage(involved, clusters) if valid else None,
        cluster_recalls=cluster_recalls(involved, clusters) if valid else (),
        matched_conflict=matched,
        f1_matched=f1_matched,
        f1_unconditional=f1_uncond if valid else None,
        yielder=yielder,
        oracle_yielders=oracle_set,
        oracle_agree=yielder_agrees(yielder, oracle_set) if yielder else None,
        classical_yielder=cls_yielder,
        classical_agree=yielder_agrees(yielder, cls_yielder) if yielder else None,
        mc_yielder=mc,
        mc_agree=yielder_agrees(yielder, mc) if yielder else None,
        no_gt_conflict=not clusters,
        token_usage=usage,
        latency_ms=item.recorded.latency_ms if with_cost else None,
        est_usd=(
            item.recorded.est_usd_per_call * item.recorded.attempts
            if with_cost
            and item.recorded.est_usd_per_call is not None
            and item.recorded.attempts
            else None
        ),
    )


_NEGATIVE: dict[str, Any] = {
    "congestion_detected": False,
    "type": "none",
    "involved_robots": [],
    "root_cause": "none_feasible in every group",
    "strategy": "none",
    "justification": "none_feasible in every group",
}


def _primary(
    item: BenchItem, chosen: Sequence[tuple[str, dict[str, Any]]], matched: int | None
) -> tuple[str, dict[str, Any]] | None:
    yields = [(label, d) for label, d in chosen if d.get("strategy") == "yield"]
    if not yields:
        return None
    if item.mc is not None and item.mc.pair:
        pair = set(item.mc.pair)
        for label, d in yields:
            if pair <= set(d.get("involved_robots") or ()):
                return label, d
    if matched is not None:
        robots = set(next(c.involved for c in item.gt.episode_conflicts if c.index == matched))
        return max(
            yields, key=lambda e: len(robots & set(e[1].get("involved_robots") or ()))
        )
    return yields[0]


def score_group_decisions(
    item: BenchItem,
    decisions: dict[str, dict[str, Any] | None],
    source: str,
    ground_fn: GroundFn,
    oracle_fn: OracleFn | None = None,
    option_scores: dict[str, ItemScore] | None = None,
) -> ItemScore:
    """Score a per-group answer (one decision or None per observed group) as one item row.

    Each chosen decision is grounded on its own (`score_item`), never as a
    merged decision. The row then combines them:

    - involved = the union of the chosen decisions' robots, in group order;
      coverage, per-cluster recall and the A33(6) matched conflict and F1
      are computed on that union, with the existing functions;
    - grounding is feasible when every chosen decision is; the first refusal
      reason, class and error are kept and the action kinds concatenated;
    - strategy is the chosen strategies joined with `+` in group order;
    - the yielder (and its M3-oracle, shadow and MC agreement) comes from
      one chosen yield: the one containing the MC first-conflict pair, else
      the one sharing most robots with the matched conflict, else the first;
    - every group `none_feasible` scores as a negative answer.

    Args:
        item: The bench item.
        decisions: Group label -> decision dict, or None for `none_feasible`.
        source: The row's source label.
        ground_fn: Offline grounder (`grounder_offline.ground_decision`).
        oracle_fn: Geometry oracle; None skips it.
        option_scores: Optional precomputed `score_item` rows per label (an
            oracle search reuses them); missing labels are scored here.

    Returns:
        The combined item score; `decision` holds the union and the
        per-group decisions under `group_decisions`.
    """
    chosen = [(label, d) for label, d in decisions.items() if d is not None]
    if not chosen:
        base = score_item(item, dict(_NEGATIVE), source, ground_fn, oracle_fn, with_cost=False)
        return base.model_copy(
            update={"decision": {**_NEGATIVE, "group_decisions": dict(decisions)}}
        )
    scores = dict(option_scores or {})
    for label, decision in chosen:
        if label not in scores:
            scores[label] = score_item(
                item, decision, source, ground_fn, oracle_fn, with_cost=False
            )
    involved: list[str] = []
    for _, decision in chosen:
        involved += [r for r in decision.get("involved_robots") or () if r not in involved]
    strategy = "+".join(d.get("strategy") or "?" for _, d in chosen)
    union = {
        "congestion_detected": True,
        "type": chosen[0][1].get("type"),
        "involved_robots": involved,
        "strategy": strategy,
    }
    matched = matched_conflict(item, union)
    clusters = item.gt.clusters
    by_index = {c.index: c for c in item.gt.episode_conflicts}
    f1_matched = f1(involved, by_index[matched].involved) if matched is not None else None
    primary = _primary(item, chosen, matched)
    primary_score = scores[primary[0]] if primary is not None else None
    yielder = primary[1].get("yield_robot") if primary is not None else None
    union["yield_robot"] = yielder
    union["group_decisions"] = dict(decisions)
    outcomes = [scores[label].grounding for label, _ in chosen]
    first_bad = next((o for o in outcomes if o is not None and not o.feasible), None)
    grounding = GroundingOutcome(
        feasible=all(o is not None and o.feasible for o in outcomes),
        refusal_reason=None if first_bad is None else first_bad.refusal_reason,
        refusal_class=None if first_bad is None else first_bad.refusal_class,
        error=None if first_bad is None else first_bad.error,
        grounded_yielder=(
            None if primary_score is None or primary_score.grounding is None
            else primary_score.grounding.grounded_yielder
        ),
        action_kinds=tuple(k for o in outcomes if o is not None for k in o.action_kinds),
    )
    oracle_set = None if primary_score is None else primary_score.oracle_yielders
    cls_yielder = classical_yielder(item) if source != "classical" else None
    mc = mc_yielder(item, matched)
    return ItemScore(
        item_id=item.item_id,
        batch=item.batch,
        episode=item.episode,
        source=source,
        decision=union,
        valid=True,
        positive=True,
        strategy=strategy,
        involved=tuple(involved),
        grounding=grounding,
        n_clusters=len(clusters),
        covered=coverage(involved, clusters),
        cluster_recalls=cluster_recalls(involved, clusters),
        matched_conflict=matched,
        f1_matched=f1_matched,
        f1_unconditional=(f1_matched or 0.0) if clusters else None,
        yielder=yielder,
        oracle_yielders=oracle_set,
        oracle_agree=yielder_agrees(yielder, oracle_set) if yielder else None,
        classical_yielder=cls_yielder,
        classical_agree=yielder_agrees(yielder, cls_yielder) if yielder else None,
        mc_yielder=mc,
        mc_agree=yielder_agrees(yielder, mc) if yielder else None,
        no_gt_conflict=not clusters,
    )


class Rate(BaseModel):
    """A pooled proportion with its counts."""

    model_config = ConfigDict(frozen=True)

    num: int
    den: int

    @property
    def value(self) -> float | None:
        """The proportion, or None for an empty domain."""
        return self.num / self.den if self.den else None

    def text(self) -> str:
        """`0.667 (2/3)` or `n/a (0/0)`."""
        return f"{self.value:.3f} ({self.num}/{self.den})" if self.den else "n/a (0/0)"


class Summary(BaseModel):
    """Pooled bench metrics over a set of item scores."""

    model_config = ConfigDict(frozen=True)

    n_items: int
    n_valid: int
    n_positive: int
    feasibility: Rate
    yield_feasibility: Rate
    refusal_histogram: dict[str, int]
    live_reproduction: Rate
    coverage: Rate
    coverage_positive: Rate
    mean_cluster_recall: float | None
    f1_matched_mean: float | None
    n_matched: int
    f1_unconditional_mean: float | None
    oracle_agreement: Rate
    oracle_empty: int
    classical_agreement: Rate
    mc_agreement: Rate
    fp_rate: Rate
    unmatched_positives: int
    strategy_counts: dict[str, int]
    plan_quality: dict[str, Any] | None = None
    mean_total_tokens: float | None = None
    mean_latency_ms: float | None = None
    est_usd_total: float | None = None


def _rate(flags: Sequence[bool | None]) -> Rate:
    seen = [f for f in flags if f is not None]
    return Rate(num=sum(1 for f in seen if f), den=len(seen))


def _mean(values: Sequence[float | None]) -> float | None:
    seen = [v for v in values if v is not None]
    return sum(seen) / len(seen) if seen else None


def summarize(
    scores: Sequence[ItemScore], plan_artifacts: Sequence[Sequence[dict[str, Any]]] | None = None
) -> Summary:
    """Pool item scores into the bench summary.

    Args:
        scores: Item scores of one run (or one batch).
        plan_artifacts: Per-episode lists of `{decision, plan, plan_state}`
            artifacts for A33(6) plan quality; None leaves it null.

    Returns:
        The summary.
    """
    positives = [s for s in scores if s.positive]
    grounded = [s for s in positives if s.grounding is not None]
    histogram = Counter(
        s.grounding.refusal_class or "grounding_error"
        for s in grounded
        if not s.grounding.feasible
    )
    yields = [s for s in grounded if s.strategy == "yield"]
    with_clusters = [s for s in scores if s.valid and s.n_clusters]
    no_conflict = [s for s in scores if s.valid and s.no_gt_conflict]
    with_yielder = [s for s in scores if s.yielder]
    plan = None
    if plan_artifacts is not None:
        per_ep = [plan_quality(arts, 0.5) for arts in plan_artifacts if arts]
        scored = sum(p.n_scored for p in per_ep)
        emitted = sum(p.n_emitted for p in per_ep)
        plan = {
            "n_scored": scored,
            "emission_rate_i_a": emitted / scored if scored else None,
            "consistency_rate_i_b": (
                sum(p.n_consistent for p in per_ep) / emitted if emitted else None
            ),
            "agreement_rate_ii": sum(p.n_agreement for p in per_ep) / scored if scored else None,
            "mean_edit_distance_iii": _mean([p.mean_edit_distance for p in per_ep]),
            "provenance_counts_iv": dict(
                sum((Counter(p.provenance_counts) for p in per_ep), Counter())
            ),
            "oracle_order_agreement_v": None,
            "replan_count_vi": sum(p.replan_count for p in per_ep),
        }
    totals = [
        (s.token_usage or {}).get("total_tokens") for s in scores if s.token_usage is not None
    ]
    usd = [s.est_usd for s in scores if s.est_usd is not None]
    return Summary(
        n_items=len(scores),
        n_valid=sum(1 for s in scores if s.valid),
        n_positive=len(positives),
        feasibility=_rate([s.grounding.feasible for s in grounded]),
        yield_feasibility=_rate([s.grounding.feasible for s in yields]),
        refusal_histogram=dict(histogram.most_common()),
        live_reproduction=_rate(
            [
                (not s.grounding.feasible) == s.live_refused
                for s in grounded
                if s.live_refused is not None
            ]
        ),
        coverage=_rate([s.covered for s in with_clusters]),
        coverage_positive=_rate([s.covered for s in with_clusters if s.positive]),
        mean_cluster_recall=_mean([r for s in with_clusters for r in s.cluster_recalls]),
        f1_matched_mean=_mean([s.f1_matched for s in scores]),
        n_matched=sum(1 for s in scores if s.f1_matched is not None),
        f1_unconditional_mean=_mean([s.f1_unconditional for s in with_clusters]),
        oracle_agreement=_rate([s.oracle_agree for s in with_yielder]),
        oracle_empty=sum(1 for s in with_yielder if s.oracle_yielders == ()),
        classical_agreement=_rate([s.classical_agree for s in with_yielder]),
        mc_agreement=_rate([s.mc_agree for s in with_yielder]),
        fp_rate=_rate([s.positive for s in no_conflict]),
        unmatched_positives=sum(1 for s in positives if s.matched_conflict is None),
        strategy_counts=dict(Counter(s.strategy for s in positives).most_common()),
        plan_quality=plan,
        mean_total_tokens=_mean(totals),
        mean_latency_ms=_mean([s.latency_ms for s in scores]),
        est_usd_total=sum(usd) if usd else None,
    )

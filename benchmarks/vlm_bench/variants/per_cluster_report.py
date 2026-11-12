"""The per-cluster (`gf-per-cluster-v1`) `candidates` report: ceiling, naive chooser, joint check.

The slot builder (`per_cluster`) never reads `item.gt`. This module does, for
scoring only: the oracle per-group choice (the combination of one option or
`none_feasible` per group that a GT-informed chooser would pick, scored with
`scoring.score_group_decisions`), the fixed first-option-per-group chooser,
and the GT strata (one cluster; two clusters that one observed group touches;
two clusters split across groups).
"""

from __future__ import annotations

import itertools
import statistics
from collections.abc import Sequence
from typing import Any

from benchmarks.s1_scoring.conflicts import f1
from benchmarks.vlm_bench.grounder_offline import ground_decision
from benchmarks.vlm_bench.models import BenchItem, ItemScore
from benchmarks.vlm_bench.scoring import Summary, score_group_decisions, score_item, summarize
from benchmarks.vlm_bench.variants.gf_cluster import ClusterOption
from benchmarks.vlm_bench.variants.per_cluster import (
    GENERATOR_VERSION_PER_CLUSTER,
    PerClusterCandidateSet,
    joint_check,
    per_cluster_candidates,
)

PC_RULES: tuple[str, ...] = ("coverage", "match", "f1", "single")
PC_RULE_TEXT: dict[str, str] = {
    "coverage": "coverage first, then matched F1, then mean per-cluster recall",
    "match": "highest Jaccard of the chosen robots with the union of the active GT "
    "clusters, then coverage, then matched F1",
    "f1": "matched involved F1 first, then coverage",
    "single": "rule `coverage` restricted to at most one non-none group (v2's single "
    "choice over the same options; a self-check against the v2 ceiling)",
}
Combo = tuple[ClusterOption | None, ...]


def stratum(item: BenchItem, candidates: PerClusterCandidateSet) -> str:
    """The item's GT stratum: "0", "1", "touch", "split" or "3+" active clusters.

    Args:
        item: The bench item.
        candidates: Its slots (their groups are the observed groups).

    Returns:
        "touch" when two active clusters and one observed group shares a
        robot with both, "split" for the other two-cluster items.
    """
    clusters = [set(c.involved) for c in item.gt.clusters]
    if len(clusters) != 2:
        return str(len(clusters)) if len(clusters) < 3 else "3+"
    groups = [set(g.robots) for g in candidates.base.groups]
    touch = any(all(c & g for c in clusters) for g in groups)
    return "touch" if touch else "split"


def _decisions(candidates: PerClusterCandidateSet, combo: Combo) -> dict[str, Any]:
    return {
        slot.label: None if option is None else option.decision()
        for slot, option in zip(candidates.slots, combo, strict=True)
    }


def _f1v(score: ItemScore) -> float:
    return -1.0 if score.f1_matched is None else score.f1_matched


def _rank(rule: str, item: BenchItem, score: ItemScore) -> tuple[float, ...]:
    covered = 1.0 if score.covered else 0.0
    if rule in ("coverage", "single"):
        recalls = score.cluster_recalls
        return (covered, _f1v(score), statistics.mean(recalls) if recalls else -1.0)
    if rule == "f1":
        return (_f1v(score), covered)
    union = {r for c in item.gt.clusters for r in c.involved}
    involved = set(score.involved)
    jaccard = len(involved & union) / len(involved | union) if union else _f1v(score)
    return (jaccard, covered, _f1v(score))


def oracle_combos(
    item: BenchItem, candidates: PerClusterCandidateSet
) -> dict[str, tuple[Combo, ItemScore]]:
    """The per-group choice a GT-informed chooser would make under each rule.

    Every combination of one option or `none_feasible` per slot is scored;
    ties keep the earlier combination (`none_feasible` sorts first, so a tie
    keeps fewer commands). GT is used here only to score.

    Args:
        item: The bench item.
        candidates: Its slots.

    Returns:
        Rule -> (combination in slot order, combined score).
    """
    cache: dict[tuple[str, int], ItemScore] = {}

    def option_score(label: str, index: int, option: ClusterOption) -> ItemScore:
        if (label, index) not in cache:
            cache[(label, index)] = score_item(
                item, option.decision(), "oracle", ground_decision, with_cost=False
            )
        return cache[(label, index)]

    lists = [[None, *slot.options] for slot in candidates.slots]
    best: dict[str, tuple[Combo, ItemScore, tuple[float, ...]]] = {}
    for combo in itertools.product(*lists):
        precomputed = {
            slot.label: option_score(slot.label, slot.options.index(option), option)
            for slot, option in zip(candidates.slots, combo, strict=True)
            if option is not None
        }
        score = score_group_decisions(
            item, _decisions(candidates, combo), "oracle", ground_decision,
            option_scores=precomputed,
        )
        n_chosen = sum(1 for o in combo if o is not None)
        for rule in PC_RULES:
            if rule == "single" and n_chosen > 1:
                continue
            rank = _rank(rule, item, score)
            if rule not in best or rank > best[rule][2]:
                best[rule] = (combo, score, rank)
    return {rule: (combo, score) for rule, (combo, score, _) in best.items()}


def combo_extras(item: BenchItem, combo: Combo) -> dict[str, Any]:
    """GT-side extras of one per-group choice: none count, spurious commands, per-cluster F1.

    Args:
        item: The bench item.
        combo: One option or None per slot.

    Returns:
        `n_slots`, `n_none`, `n_spurious` (chosen options naming no robot of
        any active GT cluster) and `per_cluster_f1` (mean over active
        clusters of the best F1 of any one chosen option; None without
        clusters).
    """
    union = {r for c in item.gt.clusters for r in c.involved}
    chosen = [o for o in combo if o is not None]
    per_cluster = [
        max((f1(o.robots, c.involved) for o in chosen), default=0.0) for c in item.gt.clusters
    ]
    return {
        "n_slots": len(combo),
        "n_none": len(combo) - len(chosen),
        "n_spurious": sum(1 for o in chosen if not set(o.robots) & union),
        "per_cluster_f1": statistics.mean(per_cluster) if per_cluster else None,
    }


def per_cluster_row(item: BenchItem) -> dict[str, Any]:
    """One item's per-cluster record: slots, oracle choices, the first-per-group chooser.

    Args:
        item: The bench item.

    Returns:
        A JSON-safe row.
    """
    candidates, _, _ = per_cluster_candidates(item)
    decision = item.recorded.decision
    positive = bool(decision and decision.get("congestion_detected") is True)
    oracle = oracle_combos(item, candidates) if candidates.slots else {}
    first: Combo = tuple(s.options[0] if s.options else None for s in candidates.slots)
    first_score = score_group_decisions(
        item, _decisions(candidates, first), "first", ground_decision
    )

    def entry(combo: Combo, score: ItemScore) -> dict[str, Any]:
        chosen = {
            s.label: o for s, o in zip(candidates.slots, combo, strict=True)
        }
        return {
            "choice": {
                label: None if o is None else candidates.base.options.index(o) + 1
                for label, o in chosen.items()
            },
            "score": score.model_dump(mode="json"),
            **combo_extras(item, combo),
            "joint": joint_check(item, chosen).model_dump(mode="json"),
        }

    return {
        "item_id": item.item_id,
        "batch": item.batch,
        "recorded_positive": positive,
        "n_clusters": len(item.gt.clusters),
        "stratum": stratum(item, candidates),
        "slots": {s.label: len(s.options) for s in candidates.slots},
        "slot_robots": {s.label: list(s.robots) for s in candidates.slots},
        "no_group_fallback": not candidates.base.groups,
        "n_options": candidates.n_options,
        "n_options_v2": len(candidates.base.options),
        "oracle": {rule: entry(*pair) for rule, pair in oracle.items()},
        "first": entry(first, first_score),
        "generator_version": GENERATOR_VERSION_PER_CLUSTER,
    }


def _sizes(values: Sequence[float]) -> str:
    if not values:
        return "n/a"
    return (
        f"{statistics.mean(values):.2f} (median {statistics.median(values):g}, "
        f"{min(values):g}-{max(values):g})"
    )


def _f(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _summary(entries: Sequence[dict[str, Any]]) -> Summary:
    return summarize([ItemScore.model_validate(e["score"]) for e in entries])


def summary_line(label: str, entries: Sequence[dict[str, Any]]) -> str:
    """One Markdown row: the bench metrics plus the per-cluster extras.

    Args:
        label: Row label.
        entries: Oracle or chooser entries of `per_cluster_row`.

    Returns:
        The row.
    """
    s = _summary(entries)
    slots = sum(e["n_slots"] for e in entries)
    none = sum(e["n_none"] for e in entries)
    pcf = [e["per_cluster_f1"] for e in entries if e["per_cluster_f1"] is not None]
    exact = sum(1 for e in entries if e["joint"]["shared_robots"] or e["joint"]["retreat_clashes"])
    near = sum(1 for e in entries if e["joint"]["path_proximity"])
    multi = sum(1 for e in entries if e["joint"]["n_commands"] >= 2)
    return (
        f"| {label} | {s.feasibility.text()} | {s.coverage.text()} "
        f"| {_f(s.mean_cluster_recall)} | {_f(s.f1_matched_mean)} ({s.n_matched}) "
        f"| {_f(s.f1_unconditional_mean)} | {_f(statistics.mean(pcf) if pcf else None)} "
        f"| {s.mc_agreement.text()} | {none}/{slots} "
        f"| {sum(e['n_spurious'] for e in entries)} | {multi} | {exact} | {near} |"
    )


HEADER = (
    "| Set | M3 feasibility (each option) | coverage | mean cluster recall "
    "| involved F1 matched (n) | F1 unconditional | per-cluster best-option F1 "
    "| yielder vs MC | none_feasible / slots | spurious commands "
    "| items with ≥ 2 commands | joint exact conflict | joint path proximity (heuristic) |"
)


def _strata_line(label: str, rows: Sequence[dict[str, Any]], key: str) -> str:
    def cell(name: str) -> str:
        sub = [r for r in rows if r["stratum"] == name and key_entry(r, key) is not None]
        covered = sum(1 for r in sub if key_entry(r, key)["score"]["covered"])
        return f"{covered}/{len(sub)}"

    two = [r for r in rows if r["stratum"] in ("touch", "split")]
    two_cov = sum(1 for r in two if key_entry(r, key)["score"]["covered"])
    return (
        f"| {label} | {cell('1')} | {two_cov}/{len(two)} | {cell('touch')} | {cell('split')} |"
    )


def key_entry(row: dict[str, Any], key: str) -> dict[str, Any] | None:
    """The row's entry for an oracle rule or "first".

    Args:
        row: A `per_cluster_row`.
        key: "first" or a rule in `PC_RULES`.

    Returns:
        The entry, or None (no slot, no oracle).
    """
    return row["first"] if key == "first" else row["oracle"].get(key)


def render_per_cluster_summary(rows: Sequence[dict[str, Any]]) -> str:
    """The Markdown ceiling and naive-chooser report over the recorded positives.

    Args:
        rows: `per_cluster_row` output for every item.

    Returns:
        The Markdown text.
    """
    pos = [r for r in rows if r["recorded_positive"]]
    with_slots = [r for r in pos if r["slots"]]
    lines = [
        f"# Grounding-first per-cluster choice ({GENERATOR_VERSION_PER_CLUSTER})",
        "",
        f"Items: {len(rows)}; recorded positives: {len(pos)}; positives with ≥ 1 slot: "
        f"{len(with_slots)}; no-group fallback slot (`outside`): "
        f"{sum(1 for r in pos if r['no_group_fallback'])}.",
        "",
        "Slots per positive: "
        + ", ".join(
            f"{n}: {sum(1 for r in pos if len(r['slots']) == n)}"
            for n in sorted({len(r['slots']) for r in pos})
        )
        + ". Options per slot: "
        + _sizes([n for r in pos for n in r["slots"].values()])
        + ". Options per item: "
        + _sizes([r["n_options"] for r in pos])
        + f" (v2 default list: {_sizes([r['n_options_v2'] for r in pos])}).",
        "",
        "Strata (recorded positives): "
        + ", ".join(
            f"{name} {sum(1 for r in pos if r['stratum'] == name)}"
            for name in ("0", "1", "touch", "split", "3+")
        )
        + ".",
        "",
        HEADER,
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for rule in PC_RULES:
        entries = [r["oracle"][rule] for r in pos if rule in r["oracle"]]
        lines.append(summary_line(f"oracle `{rule}`", entries))
    lines.append(summary_line("first option in every group", [r["first"] for r in pos]))
    lines += [
        "",
        "Rules: " + "; ".join(f"`{k}`: {v}" for k, v in PC_RULE_TEXT.items()) + ".",
        "",
        "Coverage by stratum (recorded positives):",
        "",
        "| Set | 1 cluster | 2 clusters | 2 clusters, one group touches both "
        "| 2 clusters, split across groups |",
        "|---|---|---|---|---|",
    ]
    for rule in PC_RULES:
        lines.append(_strata_line(f"oracle `{rule}`", with_slots, rule))
    lines.append(_strata_line("first option in every group", pos, "first"))
    every = [r for r in rows if r["slots"]]
    lines += [
        "",
        "All items:",
        "",
        HEADER,
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        summary_line("oracle `coverage`", [r["oracle"]["coverage"] for r in every]),
        summary_line("first option in every group", [r["first"] for r in rows]),
    ]
    fp = [r for r in rows if r["n_clusters"] == 0]
    lines += [
        "",
        f"Items with no active GT cluster: {len(fp)}; first-per-group answers positive on "
        f"{sum(1 for r in fp if r['first']['score']['positive'])}.",
    ]
    return "\n".join(lines) + "\n"


__all__ = [
    "PC_RULES",
    "PC_RULE_TEXT",
    "combo_extras",
    "key_entry",
    "oracle_combos",
    "per_cluster_row",
    "render_per_cluster_summary",
    "stratum",
    "summary_line",
]

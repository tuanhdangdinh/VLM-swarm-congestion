"""The v2 (`gf-candidates-v2`) `candidates` report: ceiling, oracle choice, grouping vs GT.

The generator (`gf_cluster`) never reads `item.gt`. This module does, for
scoring only: whether an option names the active GT clusters, the
oracle-choice ceiling (the option a perfect chooser would pick, scored with
the bench's own `score_item`), and how the observed groups agree with the GT
clusters.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Callable, Sequence
from typing import Any

from benchmarks.vlm_bench.grounder_offline import ground_command, ground_decision
from benchmarks.vlm_bench.models import BenchItem, ItemScore
from benchmarks.vlm_bench.scoring import Summary, score_item, summarize
from benchmarks.vlm_bench.variants.candidate_report import recorded_key
from benchmarks.vlm_bench.variants.gf_cluster import (
    GENERATOR_VERSION_V2,
    GroupingParams,
    SectionFlag,
    executed_key_v2,
    generate_cluster_candidates,
    grouping_params,
    observed_groups,
)
from benchmarks.vlm_bench.variants.grounding_first import GENERATOR_VERSION, generate_candidates

CONFIGS: tuple[tuple[str, SectionFlag, SectionFlag], ...] = (
    ("v2 (drop outside, drop span)", "drop", "drop"),
    ("v2 (keep outside, drop span)", "keep", "drop"),
    ("v2 (drop outside, keep span)", "drop", "keep"),
    ("v2 (keep outside, keep span)", "keep", "keep"),
)


def recorded_key_v2(item: BenchItem) -> tuple[str, ...] | None:
    """What M3 executes for the recorded decision, under the v2 key (holds included).

    Args:
        item: The bench item.

    Returns:
        The v2 executed key, or None (negative, refused, degraded or error).
    """
    decision = item.recorded.decision
    if not decision or not decision.get("congestion_detected"):
        return None
    try:
        command = ground_command(item, decision)
    except Exception:  # a grounding error executes nothing
        return None
    return executed_key_v2(decision.get("strategy", ""), command)


ORACLE_RULES: tuple[str, ...] = ("match", "coverage", "f1")
ORACLE_RULE_TEXT: dict[str, str] = {
    "match": "best match: highest Jaccard of the option's robots with the union of the "
    "active GT clusters, then coverage, then matched F1",
    "coverage": "coverage first, then matched F1, then mean per-cluster recall",
    "f1": "matched involved F1 first, then coverage",
}


def _f1(score: ItemScore) -> float:
    return -1.0 if score.f1_matched is None else score.f1_matched


def _rank(rule: str, item: BenchItem, score: ItemScore) -> tuple[float, ...]:
    covered = 1.0 if score.covered else 0.0
    if rule == "coverage":
        recalls = score.cluster_recalls
        return (covered, _f1(score), statistics.mean(recalls) if recalls else -1.0)
    if rule == "f1":
        return (_f1(score), covered)
    union = {r for c in item.gt.clusters for r in c.involved}
    involved = set(score.involved)
    jaccard = len(involved & union) / len(involved | union) if union else _f1(score)
    return (jaccard, covered, _f1(score))


def oracle_choices(
    item: BenchItem, options: Sequence[Any]
) -> dict[str, tuple[int | None, ItemScore]]:
    """The option a GT-informed chooser would pick under each rule, and its bench score.

    Rules (`ORACLE_RULE_TEXT`): "match" (the option whose robots best match
    the active GT clusters), "coverage" (the coverage ceiling) and "f1".
    Ties keep the earlier option. GT is used here only to score.

    Args:
        item: The bench item.
        options: The listed options (`ExecutableOption` or `ClusterOption`).

    Returns:
        Rule -> (1-based option number, score). The number is None when the
        list is empty; the oracle then answers "none".
    """
    scored = [
        (number, score_item(item, o.decision(), "oracle", ground_decision, with_cost=False))
        for number, o in enumerate(options, start=1)
    ]
    if not scored:
        negative = {
            "congestion_detected": False, "type": "none", "involved_robots": [],
            "root_cause": "no option", "strategy": "none", "justification": "no option",
        }
        none = score_item(item, negative, "oracle", ground_decision, with_cost=False)
        return {rule: (None, none) for rule in ORACLE_RULES}
    out: dict[str, tuple[int | None, ItemScore]] = {}
    for rule in ORACLE_RULES:
        best = scored[0]
        for candidate in scored[1:]:
            if _rank(rule, item, candidate[1]) > _rank(rule, item, best[1]):
                best = candidate
        out[rule] = best
    return out


def _cluster_agreement(item: BenchItem, params: GroupingParams | None = None) -> dict[str, Any]:
    groups = [set(g.robots) for g in observed_groups(item, params)]
    per_cluster = []
    for cluster in item.gt.clusters:
        c = set(cluster.involved)
        per_cluster.append(
            {
                "size": len(c),
                "equal": any(g == c for g in groups),
                "contained": any(c <= g for g in groups),
                "overlap2": any(len(c & g) >= 2 for g in groups),
                "overlap1": any(c & g for g in groups),
            }
        )
    clusters = [set(c.involved) for c in item.gt.clusters]
    return {
        "n_groups": len(groups),
        "clusters": per_cluster,
        "all_contained": bool(clusters) and all(any(c <= g for g in groups) for c in clusters),
        # One observed group touches every active cluster: a single group
        # option can then cover the item.
        "one_group_touches_all": bool(clusters)
        and any(all(c & g for c in clusters) for g in groups),
    }


def cluster_candidate_row(
    item: BenchItem, offgroup: SectionFlag = "drop", cross_group: SectionFlag = "drop"
) -> dict[str, Any]:
    """One item's v2 candidate-set record, with the v1 set for comparison.

    Args:
        item: The bench item.
        offgroup: The outside-any-group section flag.
        cross_group: The spans-two-groups section flag.

    Returns:
        A JSON-safe row.
    """
    v1 = generate_candidates(item, include_wait=True)
    v2 = generate_cluster_candidates(item, True, offgroup, cross_group)
    decision = item.recorded.decision
    positive = bool(decision and decision.get("congestion_detected") is True)
    key1 = recorded_key(item) if positive else None
    key2 = recorded_key_v2(item) if positive else None
    resolving = [o for o in v2.options if o.resolving]
    v1_oracle = oracle_choices(item, v1.options)
    v2_oracle = oracle_choices(item, v2.options)
    clusters = [set(c.involved) for c in item.gt.clusters]
    return {
        "item_id": item.item_id,
        "batch": item.batch,
        "episode": item.episode,
        "recorded_positive": positive,
        "recorded_strategy": decision.get("strategy") if decision else None,
        "recorded_n_involved": len(decision.get("involved_robots") or ()) if positive else 0,
        "recorded_executed_key": None if key1 is None else list(key1),
        "recorded_executed_key_v2": None if key2 is None else list(key2),
        "n_clusters": len(item.gt.clusters),
        "groups": {g.label: list(g.robots) for g in v2.groups},
        "threshold_m": v2.threshold_m,
        "offgroup": offgroup,
        "cross_group": cross_group,
        "section_counts": v2.section_counts(),
        "n_options": len(v2.options),
        "n_resolving": len(resolving),
        "n_group_options": sum(1 for o in v2.options if o.scope == "group"),
        "n_multi_passer_yields": sum(
            1 for o in v2.options if o.strategy == "yield" and len(o.base_key) > 3
        ),
        "n_with_holds": sum(1 for o in v2.options if o.held),
        "v1_n_options": len(v1.options),
        "v1_n_resolving": sum(1 for o in v1.options if o.resolving),
        "v1_in_set_all": key1 is not None and key1 in v1.keys,
        "v1_in_set_resolving": key1 is not None and key1 in v1.resolving_keys,
        "executed_not_listed_v1": key1 is not None and key1 not in v1.keys,
        # Membership on v1's key (as the v1 report counted it) and on the v2 key.
        "in_set_all": key1 is not None and key1 in v2.base_keys,
        "in_set_resolving": key1 is not None
        and key1 in {o.base_key for o in v2.options if o.resolving},
        "in_set_all_v2key": key2 is not None and key2 in v2.keys,
        "any_all": bool(v2.options),
        "any_resolving": bool(resolving),
        "any_resolving_in_cluster": any(set(o.robots) <= c for o in resolving for c in clusters),
        "any_resolving_touching_cluster": any(
            set(o.robots) & c for o in resolving for c in clusters
        ),
        # Hypothesis (b): is the generator-order option 1 inside one active cluster?
        "v1_option1_in_cluster": bool(v1.options)
        and any(set(v1.options[0].robots) <= c for c in clusters),
        "option1_in_cluster": bool(v2.options)
        and any(set(v2.options[0].robots) <= c for c in clusters),
        "option1_strategy": v2.options[0].strategy if v2.options else None,
        "v1_oracle_option": {rule: n for rule, (n, _) in v1_oracle.items()},
        "v1_oracle": {rule: _score_fields(sc) for rule, (_, sc) in v1_oracle.items()},
        "oracle_option": {rule: n for rule, (n, _) in v2_oracle.items()},
        "oracle": {rule: _score_fields(sc) for rule, (_, sc) in v2_oracle.items()},
        "agreement": _cluster_agreement(item),
        "generator_version": GENERATOR_VERSION_V2,
    }


def _score_fields(score: ItemScore) -> dict[str, Any]:
    return score.model_dump(mode="json")


def _sizes(values: Sequence[int]) -> str:
    if not values:
        return "n/a"
    return (
        f"{statistics.mean(values):.1f} (median {statistics.median(values):g}, "
        f"{min(values)}-{max(values)})"
    )


def _count(rows: Sequence[dict[str, Any]], field: str) -> str:
    return f"{sum(1 for r in rows if r[field])}/{len(rows)}"


def _oracle_summary(rows: Sequence[dict[str, Any]], field: str, rule: str) -> Summary:
    return summarize([ItemScore.model_validate(r[field][rule]) for r in rows])


def _f(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def oracle_line(label: str, summary: Summary) -> str:
    """One Markdown row of the oracle-choice table.

    Args:
        label: Row label.
        summary: The pooled oracle scores.

    Returns:
        The row.
    """
    return (
        f"| {label} | {summary.feasibility.text()} | {summary.coverage.text()} "
        f"| {_f(summary.mean_cluster_recall)} | {_f(summary.f1_matched_mean)} "
        f"({summary.n_matched}) | {_f(summary.f1_unconditional_mean)} "
        f"| {summary.mc_agreement.text()} |"
    )


def grouping_sweep(
    items: Sequence[BenchItem],
    variants: Sequence[tuple[str, Callable[[BenchItem], GroupingParams]]],
) -> list[str]:
    """Markdown rows: observed-group vs GT-cluster agreement under alternative rules.

    Args:
        items: The items.
        variants: (label, params factory) pairs.

    Returns:
        Table rows (header included).
    """
    lines = [
        "| Rule | clusters equal | contained in a group | ≥ 2 robots in one group "
        "| items, every cluster contained | items, one group touches every cluster |",
        "|---|---|---|---|---|---|",
    ]
    for label, factory in variants:
        per = [_cluster_agreement(item, factory(item)) for item in items if item.gt.clusters]
        clusters = [c for p in per for c in p["clusters"]]
        n = len(clusters)
        lines.append(
            f"| {label} | {sum(c['equal'] for c in clusters)}/{n} "
            f"| {sum(c['contained'] for c in clusters)}/{n} "
            f"| {sum(c['overlap2'] for c in clusters)}/{n} "
            f"| {sum(p['all_contained'] for p in per)}/{len(per)} "
            f"| {sum(p['one_group_touches_all'] for p in per)}/{len(per)} |"
        )
    return lines


def default_sweep() -> list[tuple[str, Callable[[BenchItem], GroupingParams]]]:
    """The grouping rules the report compares against the default.

    Returns:
        (label, params factory) pairs; the first is the default rule.
    """
    def make(threshold: float | None, seeds: frozenset[str], attach: bool):
        def factory(item: BenchItem) -> GroupingParams:
            base = grouping_params(item)
            return GroupingParams(
                threshold_m=base.threshold_m if threshold is None else threshold,
                seed_statuses=seeds,
                attach_moving=attach,
            )

        return factory

    stopped_slow = frozenset({"STOPPED", "SLOW"})
    with_stale = frozenset({"STOPPED", "SLOW", "STALE"})
    out: list[tuple[str, Callable[[BenchItem], GroupingParams]]] = [
        ("**default**: r_conflict_m (1.5 m), +STALE, MOVING attach", make(None, with_stale, True))
    ]
    for threshold in (0.5, 1.0, 2.0):
        out.append((f"{threshold} m, +STALE, MOVING attach", make(threshold, with_stale, True)))
    out.append(("1.5 m, +STALE, no attach", make(1.5, with_stale, False)))
    out.append(("1.5 m, STOPPED/SLOW only, MOVING attach", make(1.5, stopped_slow, True)))
    out.append(("1.5 m, STOPPED/SLOW only, no attach", make(1.5, stopped_slow, False)))
    return out


def render_cluster_summary(
    rows_by_config: dict[str, Sequence[dict[str, Any]]],
    items: Sequence[BenchItem] | None = None,
) -> str:
    """The Markdown v1-vs-v2 ceiling report over the recorded positives.

    Args:
        rows_by_config: Config label -> `cluster_candidate_row` output for
            every item (the v1 columns are read from the first config).
        items: The items, for the grouping sweep (None skips it).

    Returns:
        The Markdown text.
    """
    labels = list(rows_by_config)
    first = rows_by_config[labels[0]]
    pos_ids = {r["item_id"] for r in first if r["recorded_positive"]}
    lines = [
        f"# Grounding-first candidate sets: {GENERATOR_VERSION} vs {GENERATOR_VERSION_V2}",
        "",
        f"Items: {len(first)}; recorded positives: {len(pos_ids)}.",
        "",
        "| Set (over recorded positives) | options mean (median, range) "
        "| resolving mean (median, range) | recorded inside (v1 key) "
        "| recorded inside, resolving | ≥ 1 resolving | resolving in one GT cluster "
        "| executed-not-listed (v1) now listed |",
        "|---|---|---|---|---|---|---|---|",
    ]
    pos1 = [r for r in first if r["recorded_positive"]]
    enl = [r for r in pos1 if r["executed_not_listed_v1"]]
    lines.append(
        f"| {GENERATOR_VERSION} | {_sizes([r['v1_n_options'] for r in pos1])} "
        f"| {_sizes([r['v1_n_resolving'] for r in pos1])} | {_count(pos1, 'v1_in_set_all')} "
        f"| {_count(pos1, 'v1_in_set_resolving')} | n/a | n/a | 0/{len(enl)} |"
    )
    for label in labels:
        pos = [r for r in rows_by_config[label] if r["recorded_positive"]]
        enl = [r for r in pos if r["executed_not_listed_v1"]]
        lines.append(
            f"| {label} | {_sizes([r['n_options'] for r in pos])} "
            f"| {_sizes([r['n_resolving'] for r in pos])} | {_count(pos, 'in_set_all')} "
            f"| {_count(pos, 'in_set_resolving')} | {_count(pos, 'any_resolving')} "
            f"| {_count(pos, 'any_resolving_in_cluster')} "
            f"| {sum(1 for r in enl if r['in_set_all'])}/{len(enl)} |"
        )
    header = [
        "| Set | M3 feasibility | coverage | mean cluster recall | involved F1 matched (n) "
        "| F1 unconditional | yielder vs MC |",
        "|---|---|---|---|---|---|---|",
    ]
    for rule in ORACLE_RULES:
        lines += ["", f"Oracle choice, rule `{rule}` ({ORACLE_RULE_TEXT[rule]}), "
                  "recorded positives:", "", *header,
                  oracle_line(GENERATOR_VERSION, _oracle_summary(pos1, "v1_oracle", rule))]
        for label in labels:
            pos = [r for r in rows_by_config[label] if r["recorded_positive"]]
            lines.append(oracle_line(label, _oracle_summary(pos, "oracle", rule)))
    lines += ["", "Oracle choice, rule `match`, all items:", "", *header,
              oracle_line(GENERATOR_VERSION, _oracle_summary(first, "v1_oracle", "match"))]
    for label in labels:
        lines.append(
            oracle_line(label, _oracle_summary(rows_by_config[label], "oracle", "match"))
        )
    lines += ["", lane_scoped_note(first) + f" ({labels[0]}, all items)"]
    lines += _detail_lines(first, labels[0])
    for rule in ("coverage", "match"):
        lines += _two_cluster_lines(rows_by_config, rule)
    lines += _agreement_lines(first)
    if items is not None:
        lines += ["", "Grouping-rule sensitivity (observed groups vs active GT clusters):", ""]
        lines += grouping_sweep(items, default_sweep())
    lines += _strategy_lines(rows_by_config[labels[0]], labels[0])
    return "\n".join(lines) + "\n"


def _two_cluster_lines(
    rows_by_config: dict[str, Sequence[dict[str, Any]]], rule: str
) -> list[str]:
    labels = list(rows_by_config)
    first = rows_by_config[labels[0]]
    lines = [
        "",
        f"Oracle coverage (rule `{rule}`) by active GT cluster count (recorded positives):",
        "",
        "| Set | 1 cluster | 2 clusters | 2 clusters, one group touches both "
        "| 2 clusters, split across groups |",
        "|---|---|---|---|---|",
    ]

    def cell(rows: Sequence[dict[str, Any]], field: str) -> str:
        n = sum(1 for r in rows if r[field][rule]["covered"])
        return f"{n}/{len(rows)}"

    def split(rows: Sequence[dict[str, Any]]) -> tuple[list, list, list, list]:
        pos = [r for r in rows if r["recorded_positive"]]
        one = [r for r in pos if r["n_clusters"] == 1]
        two = [r for r in pos if r["n_clusters"] == 2]
        touch = [r for r in two if r["agreement"]["one_group_touches_all"]]
        apart = [r for r in two if not r["agreement"]["one_group_touches_all"]]
        return one, two, touch, apart

    one, two, touch, apart = split(first)
    lines.append(
        f"| {GENERATOR_VERSION} | {cell(one, 'v1_oracle')} | {cell(two, 'v1_oracle')} "
        f"| {cell(touch, 'v1_oracle')} | {cell(apart, 'v1_oracle')} |"
    )
    for label in labels:
        one, two, touch, apart = split(rows_by_config[label])
        lines.append(
            f"| {label} | {cell(one, 'oracle')} | {cell(two, 'oracle')} "
            f"| {cell(touch, 'oracle')} | {cell(apart, 'oracle')} |"
        )
    return lines


def _detail_lines(rows: Sequence[dict[str, Any]], label: str) -> list[str]:
    pos = [r for r in rows if r["recorded_positive"]]
    unlisted = [r for r in pos if r["executed_not_listed_v1"] and not r["in_set_all"]]
    unresolved = [r for r in pos if not r["any_resolving"]]
    return [
        "",
        f"Option 1 (generator order) inside one active GT cluster, recorded positives: "
        f"{GENERATOR_VERSION} {_count(pos, 'v1_option1_in_cluster')}; "
        f"{label} {_count(pos, 'option1_in_cluster')}.",
        "",
        f"Executed-not-listed (v1) still unlisted under {label}: "
        + (
            "; ".join(
                f"`{r['item_id']}` {r['recorded_executed_key']} groups {r['groups']}"
                for r in unlisted
            )
            or "none"
        )
        + ".",
        "",
        f"Recorded positives with no resolving option under {label}: "
        + (
            "; ".join(f"`{r['item_id']}` groups {r['groups']}" for r in unresolved) or "none"
        )
        + ".",
    ]


def _agreement_lines(rows: Sequence[dict[str, Any]]) -> list[str]:
    with_clusters = [r for r in rows if r["n_clusters"]]
    lines = [
        "",
        "Observed groups (default rule) vs active GT clusters, all items with ≥ 1 cluster:",
        "",
        "| GT cluster size | n | equal to a group | contained in a group "
        "| ≥ 2 robots in one group | ≥ 1 robot in a group |",
        "|---|---|---|---|---|---|",
    ]
    clusters = [c for r in with_clusters for c in r["agreement"]["clusters"]]
    for size in sorted({c["size"] for c in clusters}) + ["all"]:
        sub = [c for c in clusters if size == "all" or c["size"] == size]
        lines.append(
            f"| {size} | {len(sub)} | {sum(c['equal'] for c in sub)} "
            f"| {sum(c['contained'] for c in sub)} | {sum(c['overlap2'] for c in sub)} "
            f"| {sum(c['overlap1'] for c in sub)} |"
        )
    n_groups = Counter(r["agreement"]["n_groups"] for r in rows)
    lines += [
        "",
        f"Items with every active cluster inside one observed group: "
        f"{sum(r['agreement']['all_contained'] for r in with_clusters)}/{len(with_clusters)}; "
        f"one group touching every active cluster: "
        f"{sum(r['agreement']['one_group_touches_all'] for r in with_clusters)}"
        f"/{len(with_clusters)}. Observed groups per item: "
        + ", ".join(f"{k}: {v}" for k, v in sorted(n_groups.items()))
        + ".",
    ]
    return lines


def _strategy_lines(rows: Sequence[dict[str, Any]], label: str) -> list[str]:
    pos = [r for r in rows if r["recorded_positive"]]
    lines = [
        "",
        f"By recorded strategy ({label}):",
        "",
        "| Recorded strategy | n | v1 inside (all) | v2 inside (all) | v2 ≥ 1 resolving |",
        "|---|---|---|---|---|",
    ]
    for strategy, n in Counter(r["recorded_strategy"] for r in pos).most_common():
        sub = [r for r in pos if r["recorded_strategy"] == strategy]
        lines.append(
            f"| {strategy} | {n} | {_count(sub, 'v1_in_set_all')} | {_count(sub, 'in_set_all')} "
            f"| {_count(sub, 'any_resolving')} |"
        )
    return lines


def lane_scoped_note(rows: Sequence[dict[str, Any]]) -> str:
    """One line: group yields offered, multi-passer, and lane-scoped (with holds).

    Args:
        rows: `cluster_candidate_row` output.

    Returns:
        The text.
    """
    return (
        f"Group-level options listed: {sum(r['n_group_options'] for r in rows)}; "
        f"multi-passer yields: {sum(r['n_multi_passer_yields'] for r in rows)}; "
        f"options holding robots outside the key (lane-scoped crossing or retreat "
        f"shield): {sum(r['n_with_holds'] for r in rows)}."
    )


__all__ = [
    "CONFIGS",
    "cluster_candidate_row",
    "default_sweep",
    "grouping_sweep",
    "lane_scoped_note",
    "ORACLE_RULES",
    "oracle_choices",
    "recorded_key_v2",
    "render_cluster_summary",
]

"""The grounding-first `candidates` report: option-set size and the zero-cost ceiling.

For each item: the executable option count, whether the recorded decision
executes one of the listed options (matched on what M3 executes, not on the
strategy label), and whether any option exists. If no option exists, the
lever cannot help on that item.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Sequence
from typing import Any

from benchmarks.vlm_bench.grounder_offline import ground_command, ground_decision
from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.variants.grounding_first import (
    GENERATOR_VERSION,
    executed_key,
    generate_candidates,
)


def recorded_key(item: BenchItem) -> tuple[str, ...] | None:
    """What M3 executes for the recorded decision, under the candidate rule.

    Args:
        item: The bench item.

    Returns:
        The executed key, or None (negative, refused, degraded or error).
    """
    decision = item.recorded.decision
    if not decision or not decision.get("congestion_detected"):
        return None
    try:
        command = ground_command(item, decision)
    except Exception:  # a grounding error executes nothing
        return None
    return executed_key(decision.get("strategy", ""), command)


def candidate_row(item: BenchItem) -> dict[str, Any]:
    """One item's candidate-set record.

    Args:
        item: The bench item.

    Returns:
        A JSON-safe row.
    """
    candidates = generate_candidates(item, include_wait=True)
    decision = item.recorded.decision
    positive = bool(decision and decision.get("congestion_detected") is True)
    key = recorded_key(item) if positive else None
    lenient = ground_decision(item, decision) if positive else None
    resolving = [o for o in candidates.options if o.resolving]
    clusters = [set(c.involved) for c in item.gt.clusters]
    return {
        "item_id": item.item_id,
        "batch": item.batch,
        "episode": item.episode,
        "recorded_valid": decision is not None,
        "recorded_positive": positive,
        "recorded_strategy": decision.get("strategy") if decision else None,
        "recorded_feasible_bench": None if lenient is None else lenient.feasible,
        "recorded_executed_key": None if key is None else list(key),
        "n_options": len(candidates.options),
        "n_resolving": len(resolving),
        "option_strategies": dict(Counter(o.strategy for o in candidates.options)),
        "in_set_all": key is not None and key in candidates.keys,
        "in_set_resolving": key is not None and key in candidates.resolving_keys,
        "any_all": bool(candidates.options),
        "any_resolving": bool(resolving),
        # The option's probed robots all inside one active GT cluster (strict),
        # or sharing at least one robot with one (coverage `min_overlap` = 1).
        "any_resolving_in_cluster": any(
            set(o.robots) <= c for o in resolving for c in clusters
        ),
        "any_resolving_touching_cluster": any(
            set(o.robots) & c for o in resolving for c in clusters
        ),
        "generator_version": GENERATOR_VERSION,
    }


def _sizes(values: Sequence[int]) -> str:
    if not values:
        return "n/a"
    return (
        f"{statistics.mean(values):.1f} (median {statistics.median(values):g}, "
        f"{min(values)}-{max(values)})"
    )


def _count(rows: Sequence[dict[str, Any]], field: str) -> str:
    n = sum(1 for r in rows if r[field])
    return f"{n}/{len(rows)}"


def render_candidate_summary(rows: Sequence[dict[str, Any]]) -> str:
    """The Markdown ceiling table over the recorded positives (and all items).

    Args:
        rows: `candidate_row` output for every item.

    Returns:
        The Markdown text.
    """
    pos = [r for r in rows if r["recorded_positive"]]
    lines = [
        f"# Grounding-first candidate sets ({GENERATOR_VERSION})",
        "",
        f"Items: {len(rows)}; recorded positives: {len(pos)}.",
        "",
        "| Option set (over recorded positives) | set size mean (median, range) "
        "| recorded decision inside | ≥ 1 option |",
        "|---|---|---|---|",
        f"| resolving (yield / reverse / reroute) | {_sizes([r['n_resolving'] for r in pos])} "
        f"| {_count(pos, 'in_set_resolving')} | {_count(pos, 'any_resolving')} |",
        f"| incl. temporary_wait | {_sizes([r['n_options'] for r in pos])} "
        f"| {_count(pos, 'in_set_all')} | {_count(pos, 'any_all')} |",
        "",
        "Resolving option on an active GT cluster (recorded positives): all probed robots "
        f"in one cluster {_count(pos, 'any_resolving_in_cluster')}; at least one robot in a "
        f"cluster {_count(pos, 'any_resolving_touching_cluster')}.",
        "",
        "| Option set (all items) | set size mean (median, range) | ≥ 1 option |",
        "|---|---|---|",
        f"| resolving | {_sizes([r['n_resolving'] for r in rows])} "
        f"| {_count(rows, 'any_resolving')} |",
        f"| incl. temporary_wait | {_sizes([r['n_options'] for r in rows])} "
        f"| {_count(rows, 'any_all')} |",
        "",
        "Recorded positives: bench M3 feasibility (lenient) "
        f"{_count(pos, 'recorded_feasible_bench')}; executes as asked (candidate rule) "
        f"{sum(1 for r in pos if r['recorded_executed_key'])}/{len(pos)}.",
        "",
        "| Recorded strategy | n | inside (resolving) | inside (incl. wait) "
        "| ≥ 1 resolving option | ≥ 1 executable yield |",
        "|---|---|---|---|---|---|",
    ]
    for strategy, n in Counter(r["recorded_strategy"] for r in pos).most_common():
        sub = [r for r in pos if r["recorded_strategy"] == strategy]
        yields = sum(1 for r in sub if r["option_strategies"].get("yield"))
        lines.append(
            f"| {strategy} | {n} | {_count(sub, 'in_set_resolving')} "
            f"| {_count(sub, 'in_set_all')} | {_count(sub, 'any_resolving')} "
            f"| {yields}/{len(sub)} |"
        )
    return "\n".join(lines) + "\n"

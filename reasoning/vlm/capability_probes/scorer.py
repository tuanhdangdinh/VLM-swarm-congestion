"""Per-probe-type scoring with Wilson confidence intervals.

Wilson score interval (Wilson 1927), not the normal (Wald) approximation: the
methodology review backing prereg-v2's "Statistics and reporting" section
(`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`) specifies Wilson
CIs on proportions, and Wilson stays well-behaved at the small per-type `n`
(10-20 items) and extreme accuracies (0% or 100%) this battery expects, where
the normal approximation is known to misbehave.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable

from reasoning.vlm.capability_probes.models import (
    ProbeAnswerRecord,
    ProbeRunSummary,
    ProbeType,
    ProbeTypeSummary,
)

# z for a 95% two-sided interval.
_Z_95 = 1.959963984540054


def wilson_interval(successes: int, n: int, z: float = _Z_95) -> tuple[float, float]:
    """Return the two-sided Wilson score interval for `successes / n`.

    Args:
        successes: Number of correct items.
        n: Number of items scored.
        z: Normal-distribution critical value (default: 95% two-sided).

    Returns:
        `(lo, hi)`, both in `[0, 1]`; `(0.0, 1.0)` when `n == 0`.
    """
    if n == 0:
        return 0.0, 1.0
    phat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = phat + z2 / (2 * n)
    margin = z * math.sqrt(phat * (1 - phat) / n + z2 / (4 * n * n))
    lo = (center - margin) / denom
    hi = (center + margin) / denom
    return max(0.0, lo), min(1.0, hi)


def score_records(
    records: Iterable[ProbeAnswerRecord],
    chance_rate_by_item: dict[str, float],
    backend_id: str,
    manifest_seed: int,
) -> ProbeRunSummary:
    """Aggregate scored items into one `ProbeRunSummary`, one entry per probe type.

    Args:
        records: One `ProbeAnswerRecord` per scored item.
        chance_rate_by_item: `item_id -> 1 / option_count`, so a probe type
            whose option count varies by item (`nearest_first`) still reports
            a meaningful chance baseline (the mean across its items).
        backend_id: The backend the whole run was scored under.
        manifest_seed: The manifest's `seed`, recorded for provenance.

    Returns:
        The run summary; a probe type with zero scored records is omitted.
    """
    by_type: dict[ProbeType, list[ProbeAnswerRecord]] = defaultdict(list)
    for record in records:
        by_type[record.probe_type].append(record)

    summaries = []
    total = 0
    for probe_type, items in by_type.items():
        n = len(items)
        total += n
        correct = sum(1 for item in items if item.correct)
        lo, hi = wilson_interval(correct, n)
        chance_rates = [chance_rate_by_item[item.item_id] for item in items]
        failure_counts: dict[str, int] = defaultdict(int)
        for item in items:
            failure_counts[item.failure_cause or "none"] += 1
        summaries.append(
            ProbeTypeSummary(
                probe_type=probe_type,
                n=n,
                correct=correct,
                accuracy=correct / n,
                wilson_lo=lo,
                wilson_hi=hi,
                chance_rate=sum(chance_rates) / len(chance_rates),
                failure_cause_counts=dict(failure_counts),
            )
        )
    summaries.sort(key=lambda s: s.probe_type)
    return ProbeRunSummary(
        backend_id=backend_id, manifest_seed=manifest_seed, n_items=total, by_type=summaries
    )

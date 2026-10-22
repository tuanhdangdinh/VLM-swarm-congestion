"""Yielder references for the bench: the M3-executable oracle, the live shadow, the MC.

The geometry oracle itself grounds through the real M3
(`grounder_offline.executable_yielders`); this module decides which items each
reference applies to and what yielder it names.
"""

from __future__ import annotations

from typing import Any

from benchmarks.s1_scoring.conflicts import (
    Analysis,
    ConflictEpisode,
    ConflictParams,
    match_analysis,
)
from benchmarks.vlm_bench.models import BenchItem, GTCluster


def to_episode(cluster: GTCluster) -> ConflictEpisode:
    """Convert a stored cluster back to the A33 scorer's `ConflictEpisode`.

    Args:
        cluster: The stored cluster.

    Returns:
        The equivalent conflict episode.
    """
    return ConflictEpisode(
        index=cluster.index,
        onset_s=cluster.onset_s,
        end_s=cluster.end_s,
        involved=cluster.involved,
        pairs=cluster.pairs,
        to_end=False,
    )


def matched_conflict(item: BenchItem, decision: dict[str, Any] | None) -> int | None:
    """The A33(6) conflict a decision matches at the item's time, or None.

    Args:
        item: The bench item.
        decision: The decision (positive decisions only can match).

    Returns:
        The matched conflict index.
    """
    if not decision or decision.get("congestion_detected") is not True:
        return None
    analysis = Analysis(
        request_id=item.request_id,
        t_s=item.t_s,
        analysis_class="positive",
        involved=tuple(decision.get("involved_robots") or ()),
        type_label=decision.get("type"),
        matched_conflict=None,
    )
    params = ConflictParams(pre_s=item.gt.pre_s, post_s=item.gt.post_s)
    return match_analysis(analysis, [to_episode(c) for c in item.gt.episode_conflicts], params)


def classical_yielder(item: BenchItem) -> str | None:
    """The live shadow's yielder (`resolve_classical`), when it chose `yield`.

    Args:
        item: The bench item.

    Returns:
        The yielder id, or None.
    """
    decision = item.classical.recorded_decision or {}
    if decision.get("strategy") != "yield":
        return None
    return decision.get("yield_robot")


def mc_yielder(item: BenchItem, matched: int | None) -> str | None:
    """The MC first-conflict yielder, for items on the MC's first conflict only.

    Applies when the MC predicts an `executable_yield`, the item's matched GT
    conflict contains the MC pair, and that conflict is the episode's first GT
    conflict containing the pair.

    Args:
        item: The bench item.
        matched: The item's matched conflict index.

    Returns:
        The MC yielder, or None when the reference does not apply.
    """
    mc = item.mc
    if mc is None or mc.outcome != "executable_yield" or not mc.yielder or matched is None:
        return None
    pair = set(mc.pair)
    first = next(
        (c.index for c in sorted(item.gt.episode_conflicts, key=lambda c: c.onset_s)
         if pair <= set(c.involved)),
        None,
    )
    return mc.yielder if first == matched else None

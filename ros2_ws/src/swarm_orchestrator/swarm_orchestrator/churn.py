"""Coordination-level churn: dispatch identities, clusters and the bound (no rclpy).

prereg-v3 A21 (owner choice iii, "measure first, bound later"). S1b pilot 2's
E3 was a coordination-level LIVELOCK: from 212 sim-s to the horizon M5
alternated two clearing yields inside one latch cluster (robot_2 yields to
robot_5 on lane x, then robot_3 yields to robot_5 at box N, then robot_2
again, ...). Each yield broke the latch it targeted and none produced task
progress. The episode scorer's identical-run loop check read it as a run of 1,
because consecutive dispatches were never identical.

This module is the ONE definition both the offline scorer
(`scripts/s1_churn_stats.py`) and M5's default-off bound
(`ChurnBoundConfig`, `orchestrator_node`) call, so live and offline cannot
drift:

- `dispatch_identity`: what a clearing dispatch targets. A yield is
  `("yield", yielder, first passer)`; any other clearing command is the
  sorted `robot:action` list of its non-wait actions; an all-wait command is
  not a clearing dispatch (None).
- `latch_cluster`: the robots a dispatch acts on, grown by the scene's latch
  graph (centre gap < `LATCH_RADIUS_M`, M4's `min_distance_m`), so the two
  alternating E3 yields (identities {r2, r5} and {r3, r5}) fall in one
  cluster. Two dispatches share a cluster when their clusters intersect.
- `alternation_count` / `identity_repeats`: the generalised loop detector.
  The identical-run check is lookback 1; an A-B-A-B alternation repeats at
  lookback 2.
- `ChurnLedger`: the per-cluster, per-window clearing-dispatch budget and
  the alternation check over one episode's dispatch history.

Parameter values are deliberately unset (`ChurnBoundConfig` rejects an
enabled bound without them): they are to be frozen from churn data (target:
p95 of productive-resolution counts), per registered cell.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

# M4's `min_distance_m`, the latch the safety monitor holds robots on; the
# same 0.45 m the S1 Monte Carlo and the echo's engaged-pair rule use.
LATCH_RADIUS_M = 0.45

# Actions that hold a robot rather than move it to clear a conflict.
_HOLD_ACTIONS = frozenset({"temporary_wait"})

Identity = tuple[str, ...]


def dispatch_identity(command: Mapping[str, Any] | None) -> Identity | None:
    """The conflict a clearing dispatch targets, or None for a non-clearing one.

    Args:
        command: A grounded/dispatched command (`actions` with `robot_id`,
            `action`, `parameters`).

    Returns:
        `("yield", yielder, passer)` for a yield (passer = the yield's
        `passer_robot_id`, else the first of its `crossing_order`, else "");
        otherwise the sorted `robot:action` strings of every non-wait action;
        None when every action is a wait (or the command is empty).
    """
    if not command:
        return None
    actions = list(command.get("actions") or [])
    for action in actions:
        if action.get("action") == "yield":
            params = action.get("parameters") or {}
            passer = params.get("passer_robot_id")
            if not passer:
                order = params.get("crossing_order") or []
                passer = order[0] if order else ""
            return ("yield", str(action.get("robot_id")), str(passer))
    clearing = sorted(
        f"{action.get('robot_id')}:{action.get('action')}"
        for action in actions
        if action.get("action") not in _HOLD_ACTIONS
    )
    return tuple(clearing) if clearing else None


def identity_robots(identity: Identity) -> frozenset[str]:
    """The robots an identity names (yielder and passer, or every acting robot)."""
    if identity and identity[0] == "yield":
        return frozenset(r for r in identity[1:] if r)
    return frozenset(item.split(":", 1)[0] for item in identity)


def latch_components(
    positions: Mapping[str, tuple[float, float]], radius_m: float = LATCH_RADIUS_M
) -> list[frozenset[str]]:
    """Connected components of the latch graph (centre gap < `radius_m`).

    Args:
        positions: Robot id -> world (x, y).
        radius_m: Latch radius.

    Returns:
        Every component, singletons included.
    """
    ids = sorted(positions)
    parent = {rid: rid for rid in ids}

    def find(rid: str) -> str:
        while parent[rid] != rid:
            parent[rid] = parent[parent[rid]]
            rid = parent[rid]
        return rid

    for i, first in enumerate(ids):
        for second in ids[i + 1 :]:
            (ax, ay), (bx, by) = positions[first], positions[second]
            if math.hypot(ax - bx, ay - by) < radius_m:
                parent[find(first)] = find(second)
    groups: dict[str, set[str]] = {}
    for rid in ids:
        groups.setdefault(find(rid), set()).add(rid)
    return [frozenset(group) for group in groups.values()]


def latch_cluster(
    identity: Identity,
    positions: Mapping[str, tuple[float, float]],
    radius_m: float = LATCH_RADIUS_M,
) -> frozenset[str]:
    """The identity's robots plus every robot latched to them (transitively).

    Args:
        identity: A `dispatch_identity`.
        positions: Robot id -> world (x, y) at the dispatch's scene.
        radius_m: Latch radius.

    Returns:
        The cluster's robot ids.
    """
    named = identity_robots(identity)
    cluster = set(named)
    for component in latch_components(positions, radius_m):
        if component & named:
            cluster |= component
    return frozenset(cluster)


def alternation_count(identities: Sequence[Identity]) -> int:
    """A-B-A completions: positions whose identity equals the one two back, not the last.

    E3's tail C-A-B-A-B-A-B-A-B scores 7; an identical run A-A-A scores 0.
    """
    return sum(
        1
        for i in range(2, len(identities))
        if identities[i] == identities[i - 2] and identities[i] != identities[i - 1]
    )


def identity_repeats(identities: Sequence[Identity], lookback: int) -> int:
    """Positions whose identity occurred within the previous `lookback` dispatches.

    Lookback 1 counts identical consecutive repeats (the pre-A21 check);
    lookback 2 also counts period-2 alternation.
    """
    return sum(
        1
        for i in range(1, len(identities))
        if identities[i] in identities[max(0, i - lookback) : i]
    )


def longest_identical_run(identities: Sequence[Identity]) -> int:
    """Longest run of consecutive identical identities (the pre-A21 loop check)."""
    longest = run = 0
    previous: Identity | None = None
    for identity in identities:
        run = run + 1 if identity == previous else 1
        previous = identity
        longest = max(longest, run)
    return longest


@dataclass(frozen=True)
class ChurnRecord:
    """One clearing dispatch in the ledger."""

    stamp: float
    identity: Identity
    cluster: frozenset[str]
    request_id: str = ""


ChurnReason = Literal["budget", "alternation"]


@dataclass(frozen=True)
class ChurnVerdict:
    """The bound's answer for one would-be clearing dispatch."""

    withhold: bool
    reason: ChurnReason | None
    # Same-cluster clearing dispatches inside the window, before this one.
    cluster_dispatches_in_window: int
    # Same-cluster A-B-A completions this dispatch would add to the window's.
    cluster_alternations_in_window: int
    cluster: frozenset[str] = field(default_factory=frozenset)


class ChurnLedger:
    """Per-episode clearing-dispatch history and the default-off bound's check."""

    def __init__(self) -> None:
        self._records: list[ChurnRecord] = []

    @property
    def records(self) -> tuple[ChurnRecord, ...]:
        """Every recorded clearing dispatch, oldest first."""
        return tuple(self._records)

    def record(
        self, stamp: float, identity: Identity, cluster: Iterable[str], request_id: str = ""
    ) -> ChurnRecord:
        """Append one dispatched clearing command."""
        entry = ChurnRecord(
            stamp=stamp, identity=identity, cluster=frozenset(cluster), request_id=request_id
        )
        self._records.append(entry)
        return entry

    def same_cluster_window(
        self, stamp: float, cluster: frozenset[str], window_sec: float
    ) -> list[ChurnRecord]:
        """Recorded dispatches whose cluster intersects `cluster` within `window_sec`."""
        return [
            r for r in self._records if stamp - r.stamp <= window_sec and r.cluster & cluster
        ]

    def check(
        self,
        stamp: float,
        identity: Identity,
        cluster: frozenset[str],
        *,
        budget_k: int,
        window_sec: float,
        alternation_max: int,
    ) -> ChurnVerdict:
        """Decide whether one clearing dispatch exceeds the bound.

        Args:
            stamp: Scene time of the would-be dispatch (sim seconds).
            identity: Its `dispatch_identity`.
            cluster: Its `latch_cluster`.
            budget_k: Clearing dispatches allowed per cluster per window.
            window_sec: The window (sim seconds).
            alternation_max: A-B-A completions allowed per cluster per window.

        Returns:
            The verdict; `withhold` when the budget is spent (`budget`) or the
            dispatch would push the window's alternations past
            `alternation_max` (`alternation`).
        """
        prior = self.same_cluster_window(stamp, cluster, window_sec)
        sequence = [r.identity for r in prior] + [identity]
        alternations = alternation_count(sequence)
        reason: ChurnReason | None = None
        if len(prior) >= budget_k:
            reason = "budget"
        elif alternations > alternation_max:
            reason = "alternation"
        return ChurnVerdict(
            withhold=reason is not None,
            reason=reason,
            cluster_dispatches_in_window=len(prior),
            cluster_alternations_in_window=alternations,
            cluster=cluster,
        )

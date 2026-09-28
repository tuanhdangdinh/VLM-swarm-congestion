"""Per-episode robot presentation-order policy for the M2 prompt (no rclpy)."""
from __future__ import annotations

import hashlib
import random
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from reasoning.vlm.models import RobotPresentationOrder

# What the M5 config may ask for: either fixed order, or a per-episode draw that
# counterbalances the order within one run instead of across paired runs.
RobotPresentationOrderMode = Literal["id_asc", "id_desc", "random"]

_DRAWABLE_ORDERS: tuple[RobotPresentationOrder, ...] = ("id_asc", "id_desc")


def derive_order_seed(run_id: str | None, session_id: str) -> int:
    """Derive a stable integer seed from the run id, falling back to the session id.

    Args:
        run_id: `VGU_RUN_ID` as set by the launcher, or None.
        session_id: Identifier of the M5 process.

    Returns:
        A 64-bit seed. SHA-256 rather than `hash()` because `PYTHONHASHSEED`
        randomizes string hashes per process, which would leave two paired runs
        sharing one run id drawing different sequences.
    """
    digest = hashlib.sha256((run_id or session_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


@dataclass(frozen=True)
class PresentationOrderPolicy:
    """Maps a congestion-episode index to the order the prompt lists robots in.

    A fixed mode returns itself for every episode. `"random"` walks one
    `random.Random(seed)` stream and takes one independent draw per episode
    index, so the same seed and index always yield the same order and paired
    runs sharing a `VGU_RUN_ID` see the same sequence.
    """

    mode: RobotPresentationOrderMode
    seed: int

    def order_for_episode(self, episode_index: int) -> RobotPresentationOrder:
        """Return the effective presentation order for one congestion episode.

        Args:
            episode_index: Zero-based index of the episode within the run.

        Returns:
            `"id_asc"` or `"id_desc"`; never the configured `"random"`, so the
            caller always has a concrete order to render and to record.

        Raises:
            ValueError: If `episode_index` is negative.
        """
        if episode_index < 0:
            raise ValueError(f"episode_index must be >= 0, got {episode_index}")
        if self.mode != "random":
            return self.mode
        rng = random.Random(self.seed)
        drawn = _DRAWABLE_ORDERS[0]
        for _ in range(episode_index + 1):
            drawn = rng.choice(_DRAWABLE_ORDERS)
        return drawn


class EpisodeOrderTracker:
    """Holds one congestion episode's presentation order across its re-analyses.

    An episode opens on the first analysis for a robot set disjoint from the one
    being tracked, and closes when any of its robots arrives. This mirrors
    `AttemptMemory`'s episode scope without borrowing its window, which is 0 in
    the memoryless control and would otherwise make every re-analysis look like a
    new episode. Every analysis inside one episode reuses the order drawn at its
    start, so a counterbalanced run varies the order between episodes only.

    Three or more robots (T2b, 2026-09-28). Besides the analysed robot sets
    (`_robots`) the episode tracks its *members*: those sets plus every robot a
    dispatched command of the episode names (`note_dispatch`) and every queued
    follower whose solo stall was folded into it mid-maneuver (`fold`). Once
    the members number three or more, overlap is tested against the members
    (so the follower's later stall merges into the episode instead of opening a
    new one) and the episode closes on the LAST member's arrival, not the
    first. With at most two members every rule is the two-robot one above,
    byte for byte: a two-robot scene can never reach three members.
    """

    def __init__(self, policy: PresentationOrderPolicy) -> None:
        self._policy = policy
        self._index = -1
        self._robots: set[str] = set()
        self._members: set[str] = set()
        self._arrived: set[str] = set()
        self._order: RobotPresentationOrder | None = None

    def _multi_robot(self) -> bool:
        return len(self._members) >= 3

    @property
    def episode_index(self) -> int:
        """Zero-based index of the latest episode; -1 before the first one."""
        return self._index

    def order_for(self, robot_ids: Iterable[str]) -> tuple[int, RobotPresentationOrder]:
        """Return the episode index and presentation order for one analysis.

        Args:
            robot_ids: Robots the congestion event involves.

        Returns:
            `(episode_index, order)`. Overlapping robots continue the current
            episode and get its order back unchanged; a disjoint set opens the
            next episode and draws again.
        """
        robots = set(robot_ids)
        scope = self._members if self._multi_robot() else self._robots
        if self._order is None or not robots & scope:
            self._index += 1
            self._order = self._policy.order_for_episode(self._index)
            self._robots = robots
            self._members = set(robots)
            self._arrived = set()
        else:
            self._robots |= robots
            self._members |= robots
        return self._index, self._order

    def note_dispatch(self, robot_ids: Iterable[str]) -> None:
        """Add the robots a dispatched command names to the open episode's members.

        Args:
            robot_ids: Every robot the episode's grounded command reaches.
        """
        if self._order is not None:
            self._members |= set(robot_ids)

    def fold(self, robot_ids: Iterable[str]) -> bool:
        """Make a queued follower a member of the open episode, opening none.

        Args:
            robot_ids: The follower whose solo stall arrived while the
                episode's command was in flight (see `is_queued_follower`).

        Returns:
            True when this added a member, False when there was nothing new
            to add or no episode is open.
        """
        added = set(robot_ids) - self._members
        if self._order is None or not added:
            return False
        self._members |= added
        return True

    def end_episode(self, robot_ids: Iterable[str]) -> bool:
        """Close the current episode if it involves any of `robot_ids`.

        With three or more members, an arrival only marks that member; the
        episode closes once every member has arrived.

        Args:
            robot_ids: Robots whose congestion has resolved, e.g. one arrival.

        Returns:
            True if an episode was closed, False if none was tracking them (or,
            with three or more members, some member has not arrived yet).
        """
        if self._order is None:
            return False
        if self._multi_robot():
            arrived = set(robot_ids) & self._members
            if not arrived:
                return False
            self._arrived |= arrived
            if not self._members <= self._arrived:
                return False
        elif not set(robot_ids) & self._robots:
            return False
        self._order = None
        self._robots = set()
        self._members = set()
        self._arrived = set()
        return True

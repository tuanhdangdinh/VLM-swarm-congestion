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
    """

    def __init__(self, policy: PresentationOrderPolicy) -> None:
        self._policy = policy
        self._index = -1
        self._robots: set[str] = set()
        self._order: RobotPresentationOrder | None = None

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
        if self._order is None or not robots & self._robots:
            self._index += 1
            self._order = self._policy.order_for_episode(self._index)
            self._robots = robots
        else:
            self._robots |= robots
        return self._index, self._order

    def end_episode(self, robot_ids: Iterable[str]) -> bool:
        """Close the current episode if it involves any of `robot_ids`.

        Args:
            robot_ids: Robots whose congestion has resolved, e.g. one arrival.

        Returns:
            True if an episode was closed, False if none was tracking them.
        """
        if self._order is None or not set(robot_ids) & self._robots:
            return False
        self._order = None
        self._robots = set()
        return True

"""Ordered hold-until-last release for a yield with several passers.

ROS2-free logic behind `CommandBusNode`'s yield hold. A yield grounded for more
than one passer carries the passing order (`crossing_order`) and a clearance
distance per passer. The chain admits one passer at a time in that order: the
first at hold start, each later one when its predecessor has moved its own
clearance distance, and the yield's hold ends only when the LAST passer has
cleared (the Pillar-3 minimum, research design rev 8.6 §A.4). With one passer
the chain is exactly the pre-2026-09-28 single-passer hold.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# Clearance used when a yield names a passer but no `passer_clear_m`; the
# command bus's historical default.
DEFAULT_PASSER_CLEAR_M = 1.5


@dataclass(frozen=True)
class PasserPlan:
    """One passer of a yield hold.

    Attributes:
        robot_id: The passing robot.
        clear_m: Odometry displacement since its admission that counts as
            clear of the parked yielder.
        escort_m: Raw-cmd_vel escort distance, or None when the passer
            traverses under Nav2 after its wait is released.
    """

    robot_id: str
    clear_m: float
    escort_m: float | None


@dataclass(frozen=True)
class ChainStep:
    """A passer cleared.

    Attributes:
        cleared: The passer that just cleared.
        next: The passer admitted in its place, or None when it was the last
            one and the hold ends.
    """

    cleared: PasserPlan
    next: PasserPlan | None


def _valid_order(order: Any, first: str) -> list[str] | None:
    if not isinstance(order, list) or len(order) < 2:
        return None
    if not all(isinstance(robot_id, str) and robot_id for robot_id in order):
        return None
    if len(set(order)) != len(order) or order[0] != first:
        return None
    return order


def _aligned(values: Any, length: int) -> list[float] | None:
    if not isinstance(values, list) or len(values) != length:
        return None
    try:
        return [float(value) for value in values]
    except (TypeError, ValueError):
        return None


def plan_crossing(parameters: Mapping[str, Any]) -> tuple[PasserPlan, ...]:
    """Read a yield command's ordered passers from its parameters.

    The first passer always comes from the single-passer keys
    (`passer_robot_id`, `passer_clear_m`, `passer_escort_distance_m`), so a
    two-robot yield plans exactly as before. Later passers come from
    `crossing_order` with `crossing_clear_m` / `crossing_escort_m` aligned to
    it; a missing or misaligned list falls back to the first passer's value.
    A later passer is escorted only when the first one is.

    Args:
        parameters: The decoded yield `parameters_json`.

    Returns:
        The passers in crossing order; empty when the yield names no passer.
        A `crossing_order` that is not a duplicate-free list of robot ids
        starting with `passer_robot_id` is ignored (single passer).
    """
    first = parameters.get("passer_robot_id")
    if not first:
        return ()
    clear_m = float(parameters.get("passer_clear_m", DEFAULT_PASSER_CLEAR_M))
    raw_escort = parameters.get("passer_escort_distance_m")
    escort_m = None if raw_escort is None else float(raw_escort)
    plans = [PasserPlan(str(first), clear_m, escort_m)]
    order = _valid_order(parameters.get("crossing_order"), str(first))
    if order is None:
        return tuple(plans)
    clears = _aligned(parameters.get("crossing_clear_m"), len(order))
    escorts = _aligned(parameters.get("crossing_escort_m"), len(order))
    for position in range(1, len(order)):
        passer_clear = clears[position] if clears is not None else clear_m
        if escort_m is None:
            passer_escort = None
        else:
            passer_escort = escorts[position] if escorts is not None else passer_clear
        plans.append(PasserPlan(order[position], passer_clear, passer_escort))
    return tuple(plans)


class CrossingChain:
    """Admit passers one at a time and report when each clears.

    Displacement is frame-free: each passer's first odometry sample after its
    admission is its reference, and it clears once it is `clear_m` from that
    reference. Samples from any robot other than the admitted passer are
    ignored, so a queued passer's motion before its turn cannot end the hold.
    """

    def __init__(self, passers: Sequence[PasserPlan]) -> None:
        if not passers:
            raise ValueError("a crossing chain needs at least one passer")
        self._passers = tuple(passers)
        self._index = 0
        self._reference: tuple[float, float] | None = None
        self._finished = False

    @property
    def passers(self) -> tuple[PasserPlan, ...]:
        """All passers in crossing order."""
        return self._passers

    @property
    def current(self) -> PasserPlan:
        """The admitted passer (the last one once the chain has finished)."""
        return self._passers[self._index]

    @property
    def is_multi_passer(self) -> bool:
        """True when more than one passer is ordered."""
        return len(self._passers) > 1

    @property
    def finished(self) -> bool:
        """True once the last passer has cleared."""
        return self._finished

    def on_odometry(self, robot_id: str, x: float, y: float) -> ChainStep | None:
        """Feed one odometry position of a passer.

        Args:
            robot_id: Robot the odometry belongs to.
            x: Odometry-frame x in metres.
            y: Odometry-frame y in metres.

        Returns:
            A `ChainStep` when the admitted passer has just cleared, else None.
        """
        if self._finished or robot_id != self.current.robot_id:
            return None
        if self._reference is None:
            self._reference = (x, y)
            return None
        # Same arithmetic as the pre-chain single-passer hold, so a boundary
        # sample clears (or not) exactly as it did.
        moved = ((x - self._reference[0]) ** 2 + (y - self._reference[1]) ** 2) ** 0.5
        if moved < self.current.clear_m:
            return None
        cleared = self.current
        self._reference = None
        if self._index == len(self._passers) - 1:
            self._finished = True
            return ChainStep(cleared=cleared, next=None)
        self._index += 1
        return ChainStep(cleared=cleared, next=self.current)

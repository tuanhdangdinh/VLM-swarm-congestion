"""M5 contradiction trigger: arm an early re-analysis when a leg contradicts itself (no rclpy).

prereg-v3 R3.4 closed-loop item. While a dispatched command is in flight, a
leg M4 reports FAILED, or a robot measurably departing from what its leg
implies, arms ONE contradiction for that command. The node fires it when the
command resolves -- never mid-maneuver, since M4 rejects a second command for
a busy robot -- skipping the remaining cooldown, at most
`per_event_replan_budget` times per congestion episode.

What a leg "implies", per action (`leg_expectation`); every predicate is
measured from the robot's first M1 position after its leg turned ACTIVE (the
anchor), so M1's constant camera bias cancels:

- `yield` with a grounded target (derived mode's `retreat_x_m`/`retreat_y_m`,
  else legacy's `park_axis`/`park_coord_m`): the robot closes on that target,
  then holds there. Diverged when its distance to the target rises more than
  the bound above the smallest distance seen so far. A yield with no target
  in its parameters is not watched for divergence.
- `reverse`: the robot backs `backup_distance_m` (M4's 0.3 m default when
  absent) and stops. Diverged when its travel from the anchor exceeds
  `backup_distance_m + bound`. Heading-free on purpose: M3 never relies on
  M1's heading to place a reverse, so neither does this check.
- `temporary_wait`/`wait`/`stop`, only in a command with no `yield`/`reverse`
  leg: the robot stays put. Diverged when its travel from the anchor exceeds
  the bound. A wait linked to a yield or reverse is excluded because M4
  releases or escorts it through the gap while the leg is still ACTIVE.
- Every other action (`reroute`, `convoy`, `navigate`, ...): not watched for
  divergence -- the robot's implied position along a Nav2 path is not
  defined. A FAILED status still arms on every watched command.

`junction_clear` phase commands are never watched (the node does not register
them): a failed phase already auto-advances to the composite's fallback on the
same callback, and an early re-analysis would race it.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

ContradictionCause = Literal["leg_failed", "divergence"]
ExpectationKind = Literal["approach_target", "bounded_travel", "stationary"]

# M4's own default when a yield/reverse carries no backup distance
# (`command_bus_node._dispatch`).
_M4_DEFAULT_BACKUP_M = 0.3
_WAIT_ACTIONS = frozenset({"temporary_wait", "wait", "stop"})
_LINKING_ACTIONS = frozenset({"yield", "reverse"})


class LegExpectation(BaseModel):
    """What one dispatched leg implies about its robot's position."""

    model_config = ConfigDict(frozen=True)

    robot_id: str
    action: str
    kind: ExpectationKind
    # approach_target: a 2D world target, or one world axis and its coordinate.
    target_xy: tuple[float, float] | None = None
    target_axis: Literal["x", "y"] | None = None
    target_coord_m: float | None = None
    # bounded_travel: the commanded travel distance.
    travel_m: float | None = None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def leg_expectation(
    robot_id: str,
    action: str,
    parameters: Mapping[str, Any],
    command_actions: Sequence[str],
) -> LegExpectation | None:
    """Return what a dispatched leg implies, or None when it is not watched for divergence.

    Args:
        robot_id: The commanded robot.
        action: The leg's action name.
        parameters: The leg's dispatched parameters.
        command_actions: Every action name in the same command (a wait is
            watched only when none of them is a yield or reverse).

    Returns:
        The leg's expectation, or None for an unwatched action or a yield
        with no grounded target.
    """
    if action == "yield":
        rx, ry = _number(parameters.get("retreat_x_m")), _number(parameters.get("retreat_y_m"))
        if rx is not None and ry is not None:
            return LegExpectation(
                robot_id=robot_id, action=action, kind="approach_target", target_xy=(rx, ry)
            )
        axis = parameters.get("park_axis")
        coord = _number(parameters.get("park_coord_m"))
        if axis in ("x", "y") and coord is not None:
            return LegExpectation(
                robot_id=robot_id,
                action=action,
                kind="approach_target",
                target_axis=axis,
                target_coord_m=coord,
            )
        return None
    if action == "reverse":
        travel = _number(parameters.get("backup_distance_m"))
        return LegExpectation(
            robot_id=robot_id,
            action=action,
            kind="bounded_travel",
            travel_m=_M4_DEFAULT_BACKUP_M if travel is None else abs(travel),
        )
    if action in _WAIT_ACTIONS and not _LINKING_ACTIONS & set(command_actions):
        return LegExpectation(robot_id=robot_id, action=action, kind="stationary")
    return None


class DivergenceReading(BaseModel):
    """One evaluation of a leg's divergence predicate."""

    model_config = ConfigDict(frozen=True)

    diverged: bool
    # The monitored quantity: distance to target (approach_target) or
    # travel from the anchor (bounded_travel / stationary).
    measured_m: float
    # The largest value of `measured_m` the leg allows at this instant.
    allowed_m: float


def _distance_to_target(expectation: LegExpectation, position: tuple[float, float]) -> float:
    if expectation.target_xy is not None:
        return math.hypot(
            position[0] - expectation.target_xy[0], position[1] - expectation.target_xy[1]
        )
    index = 0 if expectation.target_axis == "x" else 1
    return abs(position[index] - (expectation.target_coord_m or 0.0))


def evaluate_divergence(
    expectation: LegExpectation,
    anchor: tuple[float, float],
    position: tuple[float, float],
    best_distance_m: float,
    bound_m: float,
) -> DivergenceReading:
    """Evaluate one leg's divergence predicate at one observed position.

    Args:
        expectation: The leg's expectation (`leg_expectation`).
        anchor: The robot's first observed position after its leg turned ACTIVE.
        position: The robot's current M1 position.
        best_distance_m: For `approach_target`, the smallest distance to the
            target observed so far (anchor included); ignored otherwise.
        bound_m: The registered divergence bound.

    Returns:
        The reading; `diverged` is true exactly when `measured_m > allowed_m`.
    """
    if expectation.kind == "approach_target":
        measured = _distance_to_target(expectation, position)
        allowed = best_distance_m + bound_m
    else:
        measured = math.hypot(position[0] - anchor[0], position[1] - anchor[1])
        travel = expectation.travel_m if expectation.kind == "bounded_travel" else 0.0
        allowed = (travel or 0.0) + bound_m
    return DivergenceReading(diverged=measured > allowed, measured_m=measured, allowed_m=allowed)


class Contradiction(BaseModel):
    """The first contradiction armed for one watched command."""

    model_config = ConfigDict(frozen=True)

    command_id: str
    robot_id: str
    action: str
    cause: ContradictionCause
    # Congestion episode the command was dispatched in (the budget key).
    episode_index: int | None
    # Every robot the command addressed: the early analysis's event robots.
    robot_ids: tuple[str, ...]
    # The triggering event's robot set the command was dispatched for (the
    # plan-continue exemption scope the early analysis inherits).
    trigger_robot_ids: tuple[str, ...]
    measured_m: float | None = None
    allowed_m: float | None = None

    def log_fields(self) -> str:
        """Structured `key=value` fields naming the cause, for M5's log lines."""
        text = (
            f"cause={self.cause} command={self.command_id} robot={self.robot_id} "
            f"action={self.action} episode={self.episode_index}"
        )
        if self.measured_m is not None and self.allowed_m is not None:
            text += f" measured_m={self.measured_m:.3f} allowed_m={self.allowed_m:.3f}"
        return text


@dataclass
class _LegWatch:
    action: str
    expectation: LegExpectation | None
    anchor: tuple[float, float] | None = None
    best_distance_m: float = math.inf


@dataclass
class _CommandWatch:
    robot_ids: tuple[str, ...]
    episode_index: int | None
    trigger_robot_ids: tuple[str, ...]
    legs: dict[str, _LegWatch] = field(default_factory=dict)
    contradiction: Contradiction | None = None


class ContradictionMonitor:
    """Watches dispatched commands, arms contradictions, and owns the per-episode budget."""

    def __init__(self, divergence_bound_m: float, per_event_replan_budget: int) -> None:
        self._bound_m = divergence_bound_m
        self._budget = per_event_replan_budget
        self._watches: dict[str, _CommandWatch] = {}
        self._used: dict[int | None, int] = {}

    @property
    def budget(self) -> int:
        """The configured early re-analyses allowed per congestion episode."""
        return self._budget

    def watch(
        self,
        command_id: str,
        legs: Sequence[tuple[str, str, Mapping[str, Any]]],
        episode_index: int | None,
        trigger_robot_ids: Sequence[str] = (),
    ) -> None:
        """Start watching one dispatched command.

        Args:
            command_id: The dispatched command's id.
            legs: `(robot_id, action, parameters)` per dispatched leg.
            episode_index: Congestion episode the command was dispatched in.
            trigger_robot_ids: The triggering event's robots.
        """
        actions = [action for _robot, action, _params in legs]
        self._watches[command_id] = _CommandWatch(
            robot_ids=tuple(robot for robot, _action, _params in legs),
            episode_index=episode_index,
            trigger_robot_ids=tuple(sorted(trigger_robot_ids)),
            legs={
                robot: _LegWatch(action, leg_expectation(robot, action, params, actions))
                for robot, action, params in legs
            },
        )

    def is_watched(self, command_id: str) -> bool:
        """Whether `command_id` is a watched, still-unresolved command."""
        return command_id in self._watches

    def _arm(
        self,
        command_id: str,
        watch: _CommandWatch,
        robot_id: str,
        cause: ContradictionCause,
        reading: DivergenceReading | None = None,
    ) -> Contradiction:
        contradiction = Contradiction(
            command_id=command_id,
            robot_id=robot_id,
            action=watch.legs[robot_id].action,
            cause=cause,
            episode_index=watch.episode_index,
            robot_ids=watch.robot_ids,
            trigger_robot_ids=watch.trigger_robot_ids,
            measured_m=None if reading is None else reading.measured_m,
            allowed_m=None if reading is None else reading.allowed_m,
        )
        watch.contradiction = contradiction
        return contradiction

    def on_leg_failed(self, command_id: str, robot_id: str) -> Contradiction | None:
        """Arm a `leg_failed` contradiction for a watched command's FAILED leg.

        Returns:
            The newly armed contradiction, or None when the command is not
            watched, the robot is not one of its legs, or one is already armed.
        """
        watch = self._watches.get(command_id)
        if watch is None or watch.contradiction is not None or robot_id not in watch.legs:
            return None
        return self._arm(command_id, watch, robot_id, "leg_failed")

    def observe(
        self,
        positions: Mapping[str, tuple[float, float]],
        is_active: Callable[[str, str], bool],
    ) -> list[Contradiction]:
        """Evaluate every ACTIVE watched leg against one M1 scene.

        Args:
            positions: Robot id -> current `(x, y)`; the caller leaves out
                robots M1 reports STALE.
            is_active: `(command_id, robot_id) -> bool`, true while M5's
                command tracker holds that leg ACTIVE.

        Returns:
            The contradictions armed by this scene (at most one per command).
        """
        armed: list[Contradiction] = []
        for command_id, watch in self._watches.items():
            if watch.contradiction is not None:
                continue
            for robot_id in sorted(watch.legs):
                leg = watch.legs[robot_id]
                position = positions.get(robot_id)
                if leg.expectation is None or position is None:
                    continue
                if not is_active(command_id, robot_id):
                    continue
                if leg.anchor is None:
                    leg.anchor = position
                if leg.expectation.kind == "approach_target":
                    leg.best_distance_m = min(
                        leg.best_distance_m, _distance_to_target(leg.expectation, position)
                    )
                reading = evaluate_divergence(
                    leg.expectation, leg.anchor, position, leg.best_distance_m, self._bound_m
                )
                if reading.diverged:
                    armed.append(self._arm(command_id, watch, robot_id, "divergence", reading))
                    break
        return armed

    def take_for_resolution(self, command_id: str) -> Contradiction | None:
        """Stop watching a resolved command and hand back its armed contradiction, once.

        The node resolves a command once per terminal status message (M4
        republishes), so the watch is removed on the first call and every
        later call returns None.
        """
        watch = self._watches.pop(command_id, None)
        return None if watch is None else watch.contradiction

    def budget_used(self, episode_index: int | None) -> int:
        """Early re-analyses already fired for one congestion episode."""
        return self._used.get(episode_index, 0)

    def budget_remaining(self, episode_index: int | None) -> bool:
        """Whether one more early re-analysis is allowed for this episode."""
        return self.budget_used(episode_index) < self._budget

    def charge(self, episode_index: int | None) -> int:
        """Spend one unit of an episode's budget; returns the units used."""
        self._used[episode_index] = self.budget_used(episode_index) + 1
        return self._used[episode_index]

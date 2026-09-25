"""Position-verified base-goal arrival for M5 (no rclpy).

M4 relays Nav2's own "Goal succeeded" as a `CoordinationStatus` with
`command_id="base_mission"`. That report is the primary outcome measure of the
congestion experiment, and it is not evidence the robot is at its goal: in run
20260925_124609 `bt_navigator` reported success for robot_2 while M1 placed it
0.59 m from the goal. Everything here cross-checks that report against M1's
position estimate so a Nav2 false success cannot become a false episode success.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from swarm_orchestrator.models import OrchestratorConfig, RobotView, SceneSnapshot

ArrivalReason = Literal[
    "within_tolerance", "beyond_tolerance", "no_estimate", "stale_estimate"
]
MarkArrived = Callable[[str, tuple[float, float]], None]
GoalLookup = Callable[[str], tuple[float, float] | None]


class ArrivalCheck(BaseModel):
    """Verdict of one position cross-check on a reported arrival."""

    model_config = ConfigDict(frozen=True)

    accepted: bool
    distance_m: float | None
    reason: ArrivalReason


class ArrivalDecision(BaseModel):
    """One arrival the gate has ruled on, for the caller to log.

    `check` is None when the position check is disabled by config, in which case
    the arrival was accepted unverified (legacy behaviour).
    """

    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    goal: tuple[float, float]
    check: ArrivalCheck | None = None
    late: bool = False


def classify_arrival(
    reported_goal: tuple[float, float],
    estimated_position: tuple[float, float] | None,
    tolerance_m: float,
    estimate_age_sec: float | None,
    max_estimate_age_sec: float,
) -> ArrivalCheck:
    """Decide whether a reported arrival is corroborated by M1's position estimate.

    An absent or stale estimate accepts the report: an M1 outage must not block
    every arrival in a run, it only means the arrival is unverified.

    Args:
        reported_goal: The goal M4/Nav2 reported reached, as `(x, y)` in metres.
        estimated_position: M1's latest world-frame `(x, y)` for that robot, or
            None when it has no usable estimate.
        tolerance_m: Maximum distance from the goal that corroborates arrival.
        estimate_age_sec: Seconds since the estimate was received; None when
            unknown, which is treated as stale.
        max_estimate_age_sec: Oldest estimate still considered corroborating.

    Returns:
        The verdict, carrying the measured distance whenever a position was
        supplied (including the stale case, so the log can show it).
    """
    if estimated_position is None:
        return ArrivalCheck(accepted=True, distance_m=None, reason="no_estimate")
    distance = math.dist(estimated_position, reported_goal)
    if estimate_age_sec is None or estimate_age_sec > max_estimate_age_sec:
        return ArrivalCheck(accepted=True, distance_m=distance, reason="stale_estimate")
    if distance <= tolerance_m:
        return ArrivalCheck(accepted=True, distance_m=distance, reason="within_tolerance")
    return ArrivalCheck(accepted=False, distance_m=distance, reason="beyond_tolerance")


class ArrivalGate:
    """Gates M4's base-goal arrival reports on M1's position estimate (FR5.1.9).

    An accepted report is passed straight to `mark_arrived`. A rejected one is
    held as pending: the robot is *not* marked arrived, so the congestion
    detector keeps accruing stall evidence for it and a robot stalled short of
    its goal can still trigger analysis. Each later scene re-checks the pending
    robot, and accepts it late once M1 itself places it within tolerance — no
    second Nav2 success is required.
    """

    def __init__(self, config: OrchestratorConfig, mark_arrived: MarkArrived) -> None:
        self._config = config
        self._mark_arrived = mark_arrived
        self._pending: dict[str, tuple[float, float]] = {}
        self._counts = {"accepted": 0, "rejected": 0, "late": 0}

    @property
    def counts(self) -> dict[str, int]:
        """Event tallies: a robot rejected and later accepted increments both."""
        return dict(self._counts)

    def pending_robots(self) -> set[str]:
        """Robots whose Nav2 success was rejected and not yet accepted late."""
        return set(self._pending)

    def on_nav2_success(
        self,
        robot_id: str,
        goal: tuple[float, float],
        estimate: RobotView | None,
        estimate_age_sec: float | None,
    ) -> ArrivalDecision:
        """Rule on one `base_mission` COMPLETED report.

        Args:
            robot_id: Robot Nav2 reported success for.
            goal: Its effective goal at the time of the report.
            estimate: M1's latest view of that robot, or None if it has none.
            estimate_age_sec: Seconds since that view was received, or None.

        Returns:
            The decision; `mark_arrived` has already been called when it is
            accepted.
        """
        if not self._config.arrival_position_check:
            self._pending.pop(robot_id, None)
            self._counts["accepted"] += 1
            self._mark_arrived(robot_id, goal)
            return ArrivalDecision(robot_id=robot_id, goal=goal)
        position = None if estimate is None else (estimate.x, estimate.y)
        # A STALE robot's position is M1's last good fix carried forward frozen,
        # so it is corroborating evidence of nothing however recently it arrived.
        age = (
            float("inf")
            if estimate is not None and estimate.status == "STALE"
            else estimate_age_sec
        )
        check = classify_arrival(
            goal,
            position,
            self._config.arrival_position_tolerance_m,
            age,
            self._config.arrival_estimate_max_age_sec,
        )
        if check.accepted:
            self._pending.pop(robot_id, None)
            self._counts["accepted"] += 1
            self._mark_arrived(robot_id, goal)
        else:
            self._pending[robot_id] = goal
            self._counts["rejected"] += 1
        return ArrivalDecision(robot_id=robot_id, goal=goal, check=check)

    def on_scene(self, scene: SceneSnapshot, goal_of: GoalLookup) -> list[ArrivalDecision]:
        """Re-check pending rejected arrivals against a fresh scene.

        Args:
            scene: Latest scene projection from M1.
            goal_of: Maps a robot id to its effective goal, or None if it has none.

        Returns:
            The arrivals accepted late by this scene, in robot-id order; each has
            already been passed to `mark_arrived`.
        """
        # Same rule as the detector (FR5.1.4): a late/suppressed frame carries no
        # new evidence, so it must not resolve a pending arrival either way.
        if not self._pending or scene.dropped_frame:
            return []
        views = {robot.robot_id: robot for robot in scene.robots}
        accepted: list[ArrivalDecision] = []
        for robot_id, goal in sorted(self._pending.items()):
            if goal_of(robot_id) != goal:
                # The robot was re-tasked or put under a command override; the
                # report is about a goal it is no longer pursuing.
                self._pending.pop(robot_id, None)
                continue
            view = views.get(robot_id)
            if view is None or view.status == "STALE":
                continue
            distance = math.dist((view.x, view.y), goal)
            if distance > self._config.arrival_position_tolerance_m:
                continue
            self._pending.pop(robot_id, None)
            self._counts["late"] += 1
            self._mark_arrived(robot_id, goal)
            accepted.append(
                ArrivalDecision(
                    robot_id=robot_id,
                    goal=goal,
                    check=ArrivalCheck(
                        accepted=True, distance_m=distance, reason="within_tolerance"
                    ),
                    late=True,
                )
            )
        return accepted

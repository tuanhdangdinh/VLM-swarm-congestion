"""Arm B: the rev-8 classical congestion reasoner (geometry rules, no image).

Normative rules: "Arm B — classical reasoner specification" in
`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`.
"""

import math
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from reasoning.vlm.models import BlockerKind, RobotStateInput, SnapshotFrame

_STOPPED_STATUSES = frozenset({"STOPPED", "STALE"})

ClassicalScenario = Literal["none", "head_on", "intersection", "blocked_path", "unknown"]


class ConflictZone(BaseModel):
    """Mapped conflict zone from scenario config: a world-frame circle."""

    model_config = ConfigDict(frozen=True)

    zone_id: str = Field(min_length=1)
    x: float
    y: float
    radius_m: float = Field(gt=0)


class ClassicalParams(BaseModel):
    """Arm B thresholds (rev-8); tunable on T1 only, frozen at `prereg-v1`."""

    model_config = ConfigDict(frozen=True)

    r_conflict_m: float = Field(default=1.5, gt=0)
    r_block_m: float = Field(default=1.0, gt=0)
    heading_opposition_min_deg: float = Field(default=150.0, gt=0, le=180)
    axis_cross_min_deg: float = Field(default=45.0, ge=0, le=180)
    axis_cross_max_deg: float = Field(default=135.0, ge=0, le=180)
    arrival_tie_sec: float = Field(default=1.0, gt=0)
    stopped_speed_mps: float = Field(default=0.05, gt=0)
    goal_beyond_max_deg: float = Field(default=60.0, gt=0, le=180)

    @model_validator(mode="after")
    def _check_axis_window(self) -> "ClassicalParams":
        if self.axis_cross_min_deg > self.axis_cross_max_deg:
            raise ValueError(
                f"axis_cross_min_deg {self.axis_cross_min_deg} exceeds "
                f"axis_cross_max_deg {self.axis_cross_max_deg}"
            )
        return self


class ClassicalClassification(BaseModel):
    """Geometry-classifier verdict (RQ1 control).

    `conflict_center`/`conflict_radius_m` locate the zone the verdict was
    reached at, so FCFS arrival is measured where the conflict is: the pair
    midpoint with `r_conflict_m` for `head_on`, the matched mapped zone for
    `intersection`, and None for the scenarios that carry no ordering.
    """

    model_config = ConfigDict(frozen=True)

    scenario: ClassicalScenario
    congestion_type: Literal["none", "deadlock", "bottleneck", "anomaly"]
    blocker_kind: BlockerKind | None
    involved_robots: list[str]
    conflict_center: tuple[float, float] | None = None
    conflict_radius_m: float | None = Field(default=None, gt=0)
    zone_id: str | None = None


def classify_scene(
    frames: Sequence[SnapshotFrame],
    zones: Sequence[ConflictZone],
    params: ClassicalParams,
) -> ClassicalClassification:
    """Classify the latest frame with the rev-8 Arm B geometry rules.

    Rules evaluate in order `head_on` -> `intersection` -> `blocked_path` ->
    `unknown`; the verdict is `none` when no robot is stopped. A robot is
    stopped when `|linear_velocity| < stopped_speed_mps`, or, with no
    velocity, when its status is STOPPED or STALE.

    - `head_on`: exactly two stopped robots within `r_conflict_m` of each
      other (no third stopped robot within `r_conflict_m` of either), heading
      opposition >= `heading_opposition_min_deg`, and each goal bearing
      within `goal_beyond_max_deg` of the bearing to the other robot. When
      either goal is unknown the goal check is skipped.
    - `intersection`: >= 2 stopped robots within `r_conflict_m` of a mapped
      zone's center, two of which have goal-bearing axes crossing at an
      angle in `[axis_cross_min_deg, axis_cross_max_deg]`.
    - `blocked_path`: stopped robots with no tracked robot within
      `r_block_m` in their forward half-plane. The classifier has no image
      channel, so `blocker_kind` is always `object` here: the forced
      non-divergence T3a measures.

    Args:
        frames: Snapshot history; only the latest frame (by stamp) is
            classified.
        zones: Mapped conflict zones from scenario config.
        params: Classifier thresholds.

    Returns:
        Classification with sorted involved robot ids.

    Raises:
        ValueError: If `frames` is empty.
    """
    if not frames:
        raise ValueError("classify_scene requires at least one frame")
    latest = max(frames, key=lambda frame: frame.stamp)
    stopped = sorted(
        (state for state in latest.robots if _is_stopped(state, params)),
        key=lambda state: state.robot_id,
    )
    if not stopped:
        return ClassicalClassification(
            scenario="none", congestion_type="none", blocker_kind=None, involved_robots=[]
        )

    pair = _head_on_pair(stopped, params)
    if pair is not None:
        a, b = pair
        return ClassicalClassification(
            scenario="head_on",
            congestion_type="deadlock",
            blocker_kind="robot",
            involved_robots=[a.robot_id, b.robot_id],
            conflict_center=((a.x + b.x) / 2.0, (a.y + b.y) / 2.0),
            conflict_radius_m=params.r_conflict_m,
        )

    for zone in zones:
        crossing = _intersection_robots(stopped, zone, params)
        if crossing:
            return ClassicalClassification(
                scenario="intersection",
                congestion_type="bottleneck",
                blocker_kind="robot",
                involved_robots=crossing,
                conflict_center=(zone.x, zone.y),
                conflict_radius_m=zone.radius_m,
                zone_id=zone.zone_id,
            )

    blocked = [s.robot_id for s in stopped if not _has_robot_ahead(s, latest.robots, params)]
    if blocked:
        return ClassicalClassification(
            scenario="blocked_path",
            congestion_type="anomaly",
            blocker_kind="object",
            involved_robots=blocked,
        )

    return ClassicalClassification(
        scenario="unknown",
        congestion_type="anomaly",
        blocker_kind=None,
        involved_robots=[s.robot_id for s in stopped],
    )


def _is_stopped(state: RobotStateInput, params: ClassicalParams) -> bool:
    if state.linear_velocity is not None:
        return abs(state.linear_velocity) < params.stopped_speed_mps
    return (state.status or "").upper() in _STOPPED_STATUSES


def _distance(a: RobotStateInput, b: RobotStateInput) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _angle_between_deg(a: float, b: float) -> float:
    diff = abs(a - b) % (2 * math.pi)
    if diff > math.pi:
        diff = 2 * math.pi - diff
    return math.degrees(diff)


def _head_on_pair(
    stopped: list[RobotStateInput], params: ClassicalParams
) -> tuple[RobotStateInput, RobotStateInput] | None:
    for i, a in enumerate(stopped):
        for b in stopped[i + 1 :]:
            if _distance(a, b) > params.r_conflict_m:
                continue
            crowded = any(
                other.robot_id not in (a.robot_id, b.robot_id)
                and min(_distance(other, a), _distance(other, b)) <= params.r_conflict_m
                for other in stopped
            )
            if crowded:
                continue
            if _angle_between_deg(a.theta, b.theta) < params.heading_opposition_min_deg:
                continue
            if a.goal is not None and b.goal is not None:
                if not (_goal_beyond(a, a.goal, b, params) and _goal_beyond(b, b.goal, a, params)):
                    continue
            return a, b
    return None


def _goal_beyond(
    robot: RobotStateInput,
    goal: tuple[float, float],
    other: RobotStateInput,
    params: ClassicalParams,
) -> bool:
    goal_bearing = math.atan2(goal[1] - robot.y, goal[0] - robot.x)
    other_bearing = math.atan2(other.y - robot.y, other.x - robot.x)
    return _angle_between_deg(goal_bearing, other_bearing) <= params.goal_beyond_max_deg


def _intersection_robots(
    stopped: list[RobotStateInput], zone: ConflictZone, params: ClassicalParams
) -> list[str]:
    in_zone = [s for s in stopped if math.hypot(s.x - zone.x, s.y - zone.y) <= params.r_conflict_m]
    axes = [math.atan2(s.goal[1] - s.y, s.goal[0] - s.x) for s in in_zone if s.goal is not None]
    for i, axis_a in enumerate(axes):
        for axis_b in axes[i + 1 :]:
            angle = _angle_between_deg(axis_a, axis_b)
            if params.axis_cross_min_deg <= angle <= params.axis_cross_max_deg:
                return [s.robot_id for s in in_zone]
    return []


def _has_robot_ahead(
    robot: RobotStateInput, all_robots: list[RobotStateInput], params: ClassicalParams
) -> bool:
    heading = (math.cos(robot.theta), math.sin(robot.theta))
    for other in all_robots:
        if other.robot_id == robot.robot_id:
            continue
        dx, dy = other.x - robot.x, other.y - robot.y
        if math.hypot(dx, dy) <= params.r_block_m and dx * heading[0] + dy * heading[1] > 0:
            return True
    return False

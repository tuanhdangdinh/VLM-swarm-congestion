"""prereg-v3 A26(i): the retreat shield (B1 + M5 task intent).

The A25 no-admit diagnosis (docs/reports/2026-10-12-no-admit-diagnosis.md,
mechanism B): M3 sweeps a derived yield's retreat against every other
robot's DECISION-TIME position only. A bystander still driving its task
route walks into the retreat mid-maneuver, forms a fresh safety latch with
the yielder that the A19 command-start waiver does not cover, and both
robots freeze until M4's motion deadline (E10, E13, E14, E17b).

The shield holds such a bystander for the yield's own wait budget: an
UNLINKED `temporary_wait` beside the yield (the A21 lane-scoped hold
precedent), tagged `grounding=retreat_shield:<id>`. Shielded robots are
never passers, so they stay out of the crossing order and the escort.

Which bystanders: every robot outside the command whose INTENT path comes
within `min_distance_m + retreat_shield_margin_m` of the retreat corridor
(the backup line plus the pull-off leg, as M4 executes them):

- The intent path runs from the robot's snapshot position to its current
  task node (M5's base-mission goal, `TaskRegistry.mission_goal`, the
  registry channel the node-handoff rule reads), then on to its NEXT task
  node when the robot can reach the current node and finish its dwell
  inside the yield's nominal motion time (`intent_reaches_next`). The next
  leg is what covers a robot that arrives, dwells and departs mid-maneuver
  (E14, E17b): its current leg alone never touches the corridor.
- A robot pinned in a standing latch is never shielded: within
  `min_distance_m` of another robot outside the command, both not MOVING.
  M4's safety monitor holds both members of such a pair and the latch only
  releases at `min_distance_m` separation, which neither can reach, so the
  robot cannot move during the maneuver (E16 r3: latched with r2 at
  0.413 m from 105 to 200 sim-s, through the whole completed yield).

A shielded robot is a member of the yield's command, so M4's safety
monitor exempts its pair with the backing yielder
(`safety.admitted_partners`): it is held where the decision snapshot saw
it (plus the M2-call drift), a position the retreat sweep already checked.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import SnapshotFrame

SHIELD_TAG = "grounding=retreat_shield"
SHIELD_REASON_PREFIX = "retreat shield:"
# The M4 command key (A26(ii), B3); M4 reads it verbatim through M5's
# parameters passthrough, like `backup_facing_rad`.
FAST_FAIL_KEY = "fresh_latch_fast_fail"
FAST_FAIL_ACTIONS = frozenset({"yield", "reverse"})
# M4's raw-cmd_vel primitive speeds (`Nav2Adapter.backup` / `sidestep`
# defaults): the nominal motion time is the naive time M4 scales its own
# safety deadline from (`naive_sec`), in sim-s.
_M4_BACKUP_SPEED_MPS = 0.1
_M4_TURN_RATE_RPS = 0.5
# M4's speed limit (`config/safety.yaml` `max_linear_velocity_mps`): the
# fastest a bystander can reach its node, so the next-leg read is
# conservative (it includes a leg rather than miss one).
_BYSTANDER_MAX_SPEED_MPS = 0.2
# A pinned pair's members are both held; a MOVING robot is not latched.
_UNPINNED_STATUSES = frozenset({"MOVING"})


class RobotTaskIntent(BaseModel):
    """One robot's task intent as M5 knows it at the decision.

    Attributes:
        goal: The robot's current task node (`TaskRegistry.mission_goal`).
        next_goal: The node of the task after it, or None for the last task.
        dwell_sec: Sim-s the robot will still wait at `goal` before it
            leaves for `next_goal`: the full dwell while it travels, the
            remainder while it dwells.
    """

    model_config = ConfigDict(frozen=True)

    goal: tuple[float, float]
    next_goal: tuple[float, float] | None = None
    dwell_sec: float = Field(default=0.0, ge=0.0)


class ShieldVerdict(BaseModel):
    """Why one bystander is (not) shielded, for tests and the batch report."""

    model_config = ConfigDict(frozen=True)

    robot_id: str
    shielded: bool
    # Closest approach of the intent path to the corridor centreline, metres.
    distance_m: float
    pinned_with: tuple[str, ...] = ()
    next_leg: bool = False


def _point_segment(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length_sq = dx * dx + dy * dy
    t = 0.0 if length_sq == 0.0 else ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def _cross(o: tuple[float, float], p: tuple[float, float], q: tuple[float, float]) -> float:
    return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])


def segment_distance(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> float:
    """Minimum distance between segments `ab` and `cd` (0.0 when they cross).

    Args:
        a: First segment's start, world `(x, y)`.
        b: First segment's end.
        c: Second segment's start.
        d: Second segment's end.

    Returns:
        The distance in metres.
    """
    d1, d2 = _cross(c, d, a), _cross(c, d, b)
    d3, d4 = _cross(a, b, c), _cross(a, b, d)
    if (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0) and d1 * d2 != 0 and d3 * d4 != 0:
        return 0.0
    return min(
        _point_segment(a, c, d),
        _point_segment(b, c, d),
        _point_segment(c, a, b),
        _point_segment(d, a, b),
    )


def retreat_corridor(
    start: tuple[float, float],
    facing_rad: float,
    backup_m: float,
    retreat: tuple[float, float],
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """The yielder's retreat centreline as M4 drives it: backup, then pull-off.

    Args:
        start: The yielder's snapshot position.
        facing_rad: World facing of the backup line (the robot faces along
            it while it backs; `backup_facing_rad`, else its heading).
        backup_m: Backup distance.
        retreat: The grounded retreat point (`retreat_x_m`, `retreat_y_m`).

    Returns:
        Two segments: start -> backup end, backup end -> retreat point.
    """
    end = (start[0] - backup_m * math.cos(facing_rad), start[1] - backup_m * math.sin(facing_rad))
    return [(start, end), (end, retreat)]


def nominal_motion_sec(backup_m: float, lateral_m: float) -> float:
    """The yield's nominal backup + pull-off time at M4's primitive speeds, sim-s.

    Args:
        backup_m: Backup distance.
        lateral_m: Pull-off lateral distance (0 for none).

    Returns:
        `backup/0.1 + (pi/0.5 + |lateral|/0.1)`, the naive times M4 scales
        its own motion deadlines from (no sidestep term without a lateral).
    """
    motion = abs(backup_m) / _M4_BACKUP_SPEED_MPS
    if lateral_m:
        motion += math.pi / _M4_TURN_RATE_RPS + abs(lateral_m) / _M4_BACKUP_SPEED_MPS
    return motion


def intent_reaches_next(
    position: tuple[float, float], intent: RobotTaskIntent, motion_sec: float
) -> bool:
    """Whether a robot can leave its current node for the next inside the motion time.

    Args:
        position: The robot's snapshot position.
        intent: Its task intent.
        motion_sec: The yield's nominal motion time (`nominal_motion_sec`).

    Returns:
        True when it has a next task and `distance / max speed + dwell` is
        within `motion_sec`.
    """
    if intent.next_goal is None:
        return False
    depart = math.dist(position, intent.goal) / _BYSTANDER_MAX_SPEED_MPS + intent.dwell_sec
    return depart <= motion_sec


def pinned_partners(
    frame: SnapshotFrame, robot_id: str, members: set[str] | frozenset[str], min_distance_m: float
) -> tuple[str, ...]:
    """Robots outside the command `robot_id` stands latched with, both not MOVING.

    Args:
        frame: The decision snapshot.
        robot_id: The bystander.
        members: Every robot the command addresses.
        min_distance_m: The safety latch distance.

    Returns:
        The partner ids, sorted; empty when the robot is free to move.
    """
    me = frame.find_robot(robot_id)
    if me is None or me.status in _UNPINNED_STATUSES:
        return ()
    return tuple(
        sorted(
            other.robot_id
            for other in frame.robots
            if other.robot_id != robot_id
            and other.robot_id not in members
            and other.status not in _UNPINNED_STATUSES
            and math.dist((me.x, me.y), (other.x, other.y)) < min_distance_m
        )
    )


def shield_verdicts(
    frame: SnapshotFrame,
    yield_action: Mapping[str, Any],
    members: set[str] | frozenset[str],
    min_distance_m: float,
    margin_m: float,
    task_intents: Mapping[str, RobotTaskIntent] | None,
) -> list[ShieldVerdict]:
    """Score every bystander of one derived yield against its retreat corridor.

    Args:
        frame: The decision snapshot.
        yield_action: The command's `yield` action (`robot_id`, `parameters`
            with `backup_distance_m`, `retreat_x_m`, `retreat_y_m`, optional
            `pull_off_lateral_m` and `backup_facing_rad`).
        members: Every robot the command addresses (never shielded).
        min_distance_m: The safety latch distance.
        margin_m: Corridor margin beyond the latch distance.
        task_intents: Robot id -> M5 task intent; a robot without one uses
            its snapshot goal and no next leg.

    Returns:
        One verdict per bystander, in snapshot order; empty when the yield
        lacks a retreat point or its yielder is not in the snapshot.
    """
    params = yield_action.get("parameters") or {}
    yielder = frame.find_robot(str(yield_action.get("robot_id")))
    if yielder is None or "retreat_x_m" not in params or "retreat_y_m" not in params:
        return []
    facing = params.get("backup_facing_rad")
    facing = yielder.theta if not isinstance(facing, (int, float)) else float(facing)
    backup = float(params.get("backup_distance_m", 0.0))
    lateral = float(params.get("pull_off_lateral_m") or 0.0)
    corridor = retreat_corridor(
        (yielder.x, yielder.y),
        facing,
        backup,
        (float(params["retreat_x_m"]), float(params["retreat_y_m"])),
    )
    motion = nominal_motion_sec(backup, lateral)
    verdicts: list[ShieldVerdict] = []
    for robot in frame.robots:
        if robot.robot_id in members:
            continue
        position = (robot.x, robot.y)
        intent = (task_intents or {}).get(robot.robot_id)
        if intent is None and robot.goal is not None:
            intent = RobotTaskIntent(goal=(float(robot.goal[0]), float(robot.goal[1])))
        legs: list[tuple[tuple[float, float], tuple[float, float]]] = []
        next_leg = False
        if intent is not None:
            legs.append((position, intent.goal))
            if intent_reaches_next(position, intent, motion):
                legs.append((intent.goal, intent.next_goal))  # type: ignore[arg-type]
                next_leg = True
        distance = min(
            (segment_distance(a, b, c, d) for a, b in corridor for c, d in legs),
            default=math.inf,
        )
        pinned = pinned_partners(frame, robot.robot_id, members, min_distance_m)
        verdicts.append(
            ShieldVerdict(
                robot_id=robot.robot_id,
                shielded=distance < min_distance_m + margin_m and not pinned,
                distance_m=round(distance, 4) if math.isfinite(distance) else 1e9,
                pinned_with=pinned,
                next_leg=next_leg,
            )
        )
    return verdicts


def apply_retreat_shield(
    command: dict[str, Any],
    snapshot: SnapshotFrame | None,
    geometry: SceneGeometry | None,
    params: GroundingParams | None,
    task_intents: Mapping[str, RobotTaskIntent] | None = None,
) -> dict[str, Any]:
    """Hold every bystander whose intent path crosses a derived yield's retreat.

    Runs only with `params.retreat_shield` and `params.dynamic_scene_arms`
    on, on a dynamic footprint view (`geometry.rear_room_band ==
    "footprint"`), for a command carrying a derived yield (a retreat
    point). Anything else is returned unchanged (same object).

    Args:
        command: The grounded command.
        snapshot: The decision snapshot.
        geometry: The geometry the command was grounded on.
        params: Grounding parameters.
        task_intents: Robot id -> M5 task intent, or None.

    Returns:
        The command with one unlinked `temporary_wait` per shielded robot
        (the yield's own wait budget: its passers' `duration_sec`, else
        `params.wait_backstop_sec`) and one `grounding=retreat_shield:<id>`
        tag each; unchanged when nobody is shielded.
    """
    if (
        params is None
        or not params.retreat_shield
        or not params.dynamic_scene_arms
        or snapshot is None
        or geometry is None
        or geometry.rear_room_band != "footprint"
    ):
        return command
    actions: Sequence[dict[str, Any]] = command.get("actions") or []
    yield_action = next((a for a in actions if a.get("action") == "yield"), None)
    if yield_action is None:
        return command
    members = {str(a.get("robot_id")) for a in actions}
    verdicts = shield_verdicts(
        snapshot,
        yield_action,
        members,
        geometry.robot.safety_radius_m,
        params.retreat_shield_margin_m,
        task_intents,
    )
    shielded = [v.robot_id for v in verdicts if v.shielded]
    if not shielded:
        return command
    wait_sec = next(
        (
            float((a.get("parameters") or {})["duration_sec"])
            for a in actions
            if a.get("action") == "temporary_wait"
            and "duration_sec" in (a.get("parameters") or {})
        ),
        params.wait_backstop_sec,
    )
    yielder_id = str(yield_action.get("robot_id"))
    holds = [
        {
            "robot_id": robot_id,
            "action": "temporary_wait",
            "parameters": {
                "duration_sec": wait_sec,
                # A wait substituted for the decided strategy, so
                # `project_dispatched_legs` reads it as a `wait`, not a
                # `cross` beside the yield (the lane-scoped hold rule).
                "requested_strategy": "yield",
                "reason": f"{SHIELD_REASON_PREFIX} intent crosses {yielder_id}'s retreat",
            },
        }
        for robot_id in shielded
    ]
    return {
        **command,
        "actions": [*actions, *holds],
        "degradations": [
            *command.get("degradations", []),
            *(f"{SHIELD_TAG}:{robot_id}" for robot_id in shielded),
        ],
    }


def apply_fresh_latch_fast_fail(
    command: dict[str, Any], params: GroundingParams | None
) -> dict[str, Any]:
    """Mark each clearing backup for M4's fresh-latch fast-fail (A26(ii), B3).

    Args:
        command: The grounded command.
        params: Grounding parameters.

    Returns:
        With `params.retreat_fast_fail` and `params.dynamic_scene_arms` on,
        the command with `fresh_latch_fast_fail: true` on every `yield` and
        `reverse` action; otherwise the command unchanged (same object).
    """
    if params is None or not params.retreat_fast_fail or not params.dynamic_scene_arms:
        return command
    actions = command.get("actions") or []
    if not any(a.get("action") in FAST_FAIL_ACTIONS for a in actions):
        return command
    return {
        **command,
        "actions": [
            {
                **action,
                "parameters": {**(action.get("parameters") or {}), FAST_FAIL_KEY: True},
            }
            if action.get("action") in FAST_FAIL_ACTIONS
            else action
            for action in actions
        ],
    }

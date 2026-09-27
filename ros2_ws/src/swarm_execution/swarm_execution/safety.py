"""Pure safety-invariant logic for the M4 safety monitor.

These functions are deliberately ROS2-free so the safety invariants
(`min_distance_m`, `max_linear_velocity_mps` from `config/safety.yaml`) can be
unit-tested without a running node. `safety_monitor_node.py` wires scene state
into these functions and actuates an emergency stop on the result.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from itertools import combinations

REASON_MIN_DISTANCE = "min_distance_violation"
REASON_SPEED_LIMIT = "speed_limit_violation"
REASON_STALE_POSE = "stale_pose_unsafe"

# Margin added to `min_distance_m` for the STALE fail-safe band: a marker can
# vanish while the pair is still closing, and M1 needs stale_after_sec (1.15
# sim-s since the 2026-09-27 sim-time camera flip; previously 3 wall-s, the same
# ~1.14 sim-s at RTF ~0.38) to declare STALE, so the last fresh distance
# understates the real one. This is a margin, not full coverage of that window
# (1.15 s at the 0.2 m/s limit is 0.23 m); the keep-the-existing-latch half of
# the rule covers the rest.
STALE_UNSAFE_MARGIN_M = 0.15

# Per-robot coordination actions that exempt a pair from the latch rules. Both
# are raw-cmd_vel clearing primitives (backup, sidestep, hold, escort) that
# legitimately work inside min_distance_m. Nav2-goal legs (navigate, goal,
# priority_override, reroute, convoy) and waits (wait, temporary_wait, stop)
# are deliberately absent: in runs G4 and K1 (2026-09-25/26) a reroute leg
# plus its partner's temporary_wait disarmed the monitor and drove one robot
# into its parked partner for ~51 s. See
# docs/reports/2026-09-26-close-approach-analysis.md.
CLEARING_ACTIONS: frozenset[str] = frozenset({"yield", "reverse"})

TERMINAL_STATUSES: frozenset[str] = frozenset({"COMPLETED", "FAILED", "CANCELLED"})


@dataclass(frozen=True)
class SafetyLimits:
    """Safety invariants loaded from `config/safety.yaml`."""

    min_distance_m: float
    max_linear_velocity_mps: float
    stale_pose_is_unsafe: bool = True
    stale_unsafe_distance_m: float | None = None

    def __post_init__(self) -> None:
        # Derived rather than a literal default so the band tracks
        # `min_distance_m` when that is retuned (it went 0.3 -> 0.45 once).
        if self.stale_unsafe_distance_m is None:
            object.__setattr__(
                self,
                "stale_unsafe_distance_m",
                self.min_distance_m + STALE_UNSAFE_MARGIN_M,
            )


@dataclass(frozen=True)
class LatchEvaluation:
    """Result of one scene snapshot evaluation.

    Attributes:
        latched: Robot ids that must be held under a safety stop.
        reasons: Latch reason per robot id, one of the `REASON_*` constants.
        last_fresh_distances: Updated pairwise-distance memory to feed back into
            the next call, keyed by the sorted `(robot_id, robot_id)` pair.
    """

    latched: frozenset[str] = frozenset()
    reasons: dict[str, str] = field(default_factory=dict)
    last_fresh_distances: dict[tuple[str, str], float] = field(default_factory=dict)


def is_clearing_action(action: str | None) -> bool:
    """Return True if a coordination action is a clearing maneuver.

    Args:
        action: The per-robot `CoordinationCommand.action`, or None when the
            command behind an ACTIVE status has not been seen.

    Returns:
        True only for an action in `CLEARING_ACTIONS`. An unknown action is
        not clearing, so a missing command fails closed (no exemption).
    """
    return action in CLEARING_ACTIONS


def clearing_exempt_robots(
    active_by_robot: Mapping[str, str],
    action_by_key: Mapping[tuple[str, str], str],
) -> frozenset[str]:
    """Return the robots whose ACTIVE coordination command is a clearing maneuver.

    The result is the `exempt` set for `detect_proximity_violations` and
    `evaluate_latches`. Those functions skip any pair with an exempt member, so
    a pair is exempt exactly while a clearing maneuver is among its members'
    ACTIVE commands. This keeps the yield flow working: the passer's linked
    `temporary_wait` does not exempt it, but the pair stays exempt through the
    yielder's own ACTIVE `yield`.

    Args:
        active_by_robot: Robot id -> command id of its current ACTIVE command,
            from `/coordination/status`.
        action_by_key: `(command_id, robot_id)` -> per-robot action, from
            `/coordination/commands`. The command id is shared by every robot
            of one decision and carries the strategy, not the robot's action,
            so the action must come from the command itself.

    Returns:
        Robot ids whose ACTIVE command's action is in `CLEARING_ACTIONS`. A
        robot whose command was never seen is not exempt.
    """
    return frozenset(
        robot_id
        for robot_id, command_id in active_by_robot.items()
        if is_clearing_action(action_by_key.get((command_id, robot_id)))
    )


class CoordinationTracker:
    """Track per-robot ACTIVE coordination commands and their actions.

    ROS2-free bookkeeping for the safety monitor. Commands and statuses arrive
    on separate topics with no cross-topic ordering guarantee, so the two maps
    are joined only when `exempt_robots` is called; a status that lands before
    its command resolves correctly once the command arrives.
    """

    # Bound for command actions that never receive a terminal status (e.g. a
    # command dropped before dispatch). Far above any real in-flight count.
    MAX_TRACKED_COMMANDS = 256

    def __init__(self) -> None:
        self._action_by_key: dict[tuple[str, str], str] = {}
        self._active_by_robot: dict[str, str] = {}

    def record_command(self, command_id: str, robot_id: str, action: str) -> None:
        """Remember the per-robot action of a dispatched coordination command.

        Args:
            command_id: `CoordinationCommand.command_id`.
            robot_id: `CoordinationCommand.robot_id`.
            action: `CoordinationCommand.action`, e.g. `yield` or `reroute`.
        """
        if not command_id or not robot_id:
            return
        key = (command_id, robot_id)
        self._action_by_key.pop(key, None)
        self._action_by_key[key] = action
        while len(self._action_by_key) > self.MAX_TRACKED_COMMANDS:
            self._action_by_key.pop(next(iter(self._action_by_key)))

    def record_status(self, command_id: str, robot_id: str, status: str) -> bool:
        """Apply one `/coordination/status` update.

        A terminal status clears a robot only when it belongs to the command
        the robot is ACTIVE on, as in the command bus's in-flight registry: a
        busy-rejected command's FAILED, or a `base_mission` status from
        `coordination_client`, must not end a live maneuver's exemption.

        Args:
            command_id: `CoordinationStatus.command_id`.
            robot_id: `CoordinationStatus.robot_id`.
            status: `CoordinationStatus.status`.

        Returns:
            True if the robot's ACTIVE command changed.
        """
        if not robot_id:
            return False
        if status == "ACTIVE":
            changed = self._active_by_robot.get(robot_id) != command_id
            self._active_by_robot[robot_id] = command_id
            return changed
        if status not in TERMINAL_STATUSES:
            return False
        self._action_by_key.pop((command_id, robot_id), None)
        if self._active_by_robot.get(robot_id) == command_id:
            del self._active_by_robot[robot_id]
            return True
        return False

    def active_action(self, robot_id: str) -> str | None:
        """Return the action of the robot's ACTIVE command, or None.

        Args:
            robot_id: Robot to look up.

        Returns:
            The action, or None if the robot is not ACTIVE or its command has
            not been seen.
        """
        command_id = self._active_by_robot.get(robot_id)
        if command_id is None:
            return None
        return self._action_by_key.get((command_id, robot_id))

    def exempt_robots(self) -> frozenset[str]:
        """Return the robots currently exempting their pairs (see `clearing_exempt_robots`)."""
        return clearing_exempt_robots(self._active_by_robot, self._action_by_key)


def detect_proximity_violations(
    robots: list[dict],
    min_distance_m: float,
    exempt: set[str] | frozenset[str] = frozenset(),
) -> set[str]:
    """Return the ids of robots in any pair closer than `min_distance_m`.

    Distance is the Euclidean ground-plane separation between robot centres.
    The threshold is strict: a separation equal to `min_distance_m` is allowed,
    only strictly-closer pairs are flagged. Both robots in a violating pair are
    returned so the caller can stop each one.

    Pairs containing an `exempt` robot are skipped. The exempt set is the
    robots executing a clearing maneuver (`clearing_exempt_robots`): a yielder
    parked off-centerline during its hold must let the passer come closer than
    `min_distance_m`. The yielder pulls off 0.35 m while the latch threshold is
    0.45 m, so without the pair exemption the pass itself would latch the
    passer and freeze both robots. Robot-level exemption on the caller side
    cannot express this: it unlatches the yielder but still latches its
    partner.

    Args:
        robots: Robot state dicts, each with `robot_id`, `x`, and `y`.
        min_distance_m: Minimum allowed centre-to-centre separation in metres.
        exempt: Robots whose ACTIVE command is a clearing maneuver; pairs with
            at least one such member are not flagged.

    Returns:
        The set of `robot_id`s involved in at least one violating pair.
    """
    flagged: set[str] = set()
    for a, b in combinations(robots, 2):
        if a["robot_id"] in exempt or b["robot_id"] in exempt:
            continue
        distance = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
        if distance < min_distance_m:
            flagged.add(a["robot_id"])
            flagged.add(b["robot_id"])
    return flagged


def exceeds_speed_limit(linear_velocity: float, max_linear_velocity_mps: float) -> bool:
    """Return True if `linear_velocity` magnitude exceeds the speed limit."""
    return abs(linear_velocity) > max_linear_velocity_mps


def _pair_key(a_id: str, b_id: str) -> tuple[str, str]:
    return (a_id, b_id) if a_id <= b_id else (b_id, a_id)


def evaluate_latches(
    robots: list[dict],
    limits: SafetyLimits,
    previous_latched: set[str] | frozenset[str] = frozenset(),
    last_fresh_distances: Mapping[tuple[str, str], float] | None = None,
    exempt: set[str] | frozenset[str] = frozenset(),
) -> LatchEvaluation:
    """Compute the latched-robot set for one scene snapshot.

    Two rules, unioned:

    1. **Proximity** — `detect_proximity_violations` on the snapshot as given.
    2. **STALE fail-safe** (`stale_pose_is_unsafe`) — a robot M1 reports as
       `STALE` has an unknown pose, which is *unsafe*, not absent. Such a robot
       keeps any latch it already had, and is latched afresh if the last
       reading in which it and another robot were *both* non-STALE put the pair
       within `stale_unsafe_distance_m`.

    Rule 2 exists because of run D (2026-09-16): two robots drove together
    until their ArUco quads overlapped, overlapping markers are undetectable,
    so both went `STALE` at 0.078 m centre distance. With no fresh non-STALE
    pair the monitor neither latched nor kept a latch, and the robots were
    pushed around interpenetrating for ~400 s.

    Rule 2 deliberately uses the remembered *non-STALE* pairwise distance and
    not the pose carried in the snapshot: M1 freezes and republishes the last
    known pose of a STALE robot, and that carried pose is exactly the datum
    that becomes wrong while the robot keeps moving. A pair never observed
    fresh together has no memory entry and is not latched by distance — only a
    pre-existing latch carries it.

    Release is fresh-reading-gated: a latch survives every STALE snapshot and
    lifts only once a non-STALE reading shows the pair at or beyond
    `min_distance_m`.

    Robots in `exempt` (an ACTIVE clearing maneuver, `clearing_exempt_robots`)
    are exempt from rule 2 exactly as they are from rule 1: a commanded backup
    is the designed way out of a close standoff and the fail-safe must not
    stall it. A robot on a Nav2 leg or a wait is not exempt, so a latch that
    fired before such a command went ACTIVE persists (run K1, 2026-09-26).

    Args:
        robots: Robot state dicts with `robot_id`, `x`, `y`, and optionally
            `status`. A missing `status` is treated as non-STALE.
        limits: Safety invariants from `config/safety.yaml`.
        previous_latched: Robot ids latched by the previous evaluation.
        last_fresh_distances: Pairwise-distance memory returned by the previous
            evaluation; `None` on the first call.
        exempt: Robots whose ACTIVE command is a clearing maneuver.

    Returns:
        The new latched set, the reason per latched robot, and the updated
        pairwise-distance memory.
    """
    memory = dict(last_fresh_distances or {})
    latched: set[str] = set()
    reasons: dict[str, str] = {}

    for robot_id in detect_proximity_violations(
        robots, limits.min_distance_m, exempt
    ):
        latched.add(robot_id)
        reasons[robot_id] = REASON_MIN_DISTANCE

    stale = {r["robot_id"] for r in robots if r.get("status") == "STALE"}

    # Only a both-fresh pair refreshes the memory; a distance measured against
    # a STALE robot's carried pose would launder the stale datum into the
    # memory the fail-safe trusts.
    fresh = [r for r in robots if r["robot_id"] not in stale]
    for a, b in combinations(fresh, 2):
        distance = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
        memory[_pair_key(a["robot_id"], b["robot_id"])] = distance

    if not limits.stale_pose_is_unsafe:
        return LatchEvaluation(frozenset(latched), reasons, memory)

    robot_ids = [r["robot_id"] for r in robots]
    for a_id, b_id in combinations(robot_ids, 2):
        if a_id not in stale and b_id not in stale:
            continue
        if a_id in exempt or b_id in exempt:
            continue
        last_distance = memory.get(_pair_key(a_id, b_id))
        if last_distance is None or last_distance >= limits.stale_unsafe_distance_m:
            continue
        for robot_id in (a_id, b_id):
            latched.add(robot_id)
            reasons.setdefault(robot_id, REASON_STALE_POSE)

    for robot_id in stale & set(previous_latched):
        if robot_id in exempt:
            continue
        latched.add(robot_id)
        reasons.setdefault(robot_id, REASON_STALE_POSE)

    return LatchEvaluation(frozenset(latched), reasons, memory)

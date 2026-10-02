"""Pure safety-invariant logic for the M4 safety monitor.

These functions are deliberately ROS2-free so the safety invariants
(`min_distance_m`, `max_linear_velocity_mps` from `config/safety.yaml`) can be
unit-tested without a running node. `safety_monitor_node.py` wires scene state
into these functions and actuates an emergency stop on the result.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from swarm_execution.crossing_chain import plan_crossing
from swarm_execution.yield_phase import YIELD_BACKUP_PHASE_DETAILS

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

# Per-robot coordination actions that exempt pairs from the latch rules (only
# the clearing robot's pairs with its own command's partners; see
# `CoordinationTracker.exemption`). Both
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
class ClearingExemption:
    """Which robot pairs the latch rules skip while clearing maneuvers run.

    Attributes:
        clearing_robots: Robots whose ACTIVE command is a clearing maneuver.
            The speed rule and the STALE keep-latch rule are per robot and use
            this set.
        pairs: Sorted `(robot_id, robot_id)` pairs the distance rule and the
            STALE remembered-distance rule skip: each clearing robot paired
            with the partners its own clearing command names. None is the
            pre-2026-09-28 robot scope, where every pair containing a clearing
            robot is skipped; it remains for callers that pass a bare robot
            set.
    """

    clearing_robots: frozenset[str] = frozenset()
    pairs: frozenset[tuple[str, str]] | None = None

    def covers_pair(self, a_id: str, b_id: str) -> bool:
        """Return True if the pair `(a_id, b_id)` is exempt from the pair rules."""
        if self.pairs is None:
            return a_id in self.clearing_robots or b_id in self.clearing_robots
        return _pair_key(a_id, b_id) in self.pairs


ExemptInput = set[str] | frozenset[str] | ClearingExemption


def _as_exemption(exempt: ExemptInput) -> ClearingExemption:
    if isinstance(exempt, ClearingExemption):
        return exempt
    return ClearingExemption(clearing_robots=frozenset(exempt), pairs=None)


def crossing_order_from_parameters(
    action: str, parameters: Mapping[str, Any] | None
) -> tuple[str, ...] | None:
    """Return the ordered passers a yield command names, or None.

    Delegates to the command bus's own parser (`plan_crossing`), so the
    passers the monitor pairs with the yielder are exactly the passers the
    bus escorts and releases.

    Args:
        action: The per-robot `CoordinationCommand.action`.
        parameters: The decoded `parameters_json`, or None when absent or
            unparseable.

    Returns:
        The passer ids in crossing order, or None for a non-yield action, a
        yield naming no passer, or parameters the bus itself cannot parse
        (it then fails the yield at dispatch, so nothing is exempt).
    """
    if action != "yield" or not parameters:
        return None
    try:
        plans = plan_crossing(parameters)
    except (TypeError, ValueError):
        return None
    return tuple(plan.robot_id for plan in plans) or None


def plan_continue_partners_from_parameters(
    action: str, parameters: Mapping[str, Any] | None
) -> frozenset[str]:
    """Return a `reverse` leg's extra same-plan `continue` partners, or empty.

    Freeze-blocking finding 3 (2026-10-02 IB10 composite smoke, step-7a
    fix): `admitted_partners`'s own-command `members` scope has no way to
    see a `continue` leg of the SAME accepted plan, since a `continue`
    robot receives no command at all. M5 (`orchestrator_node.
    _with_plan_continue_partners`) carries that membership on the reverse
    leg's own `parameters_json` instead -- this is the M4-side read of that
    field, narrowly scoped to exactly the named robots (never a blanket
    same-command-or-wider exemption).

    Args:
        action: The per-robot `CoordinationCommand.action`.
        parameters: The decoded `parameters_json`, or None when absent or
            unparseable.

    Returns:
        The named robot ids, or an empty frozenset for a non-`reverse`
        action, absent parameters, or a malformed/non-list field.
    """
    if action != "reverse" or not parameters:
        return frozenset()
    partners = parameters.get("plan_continue_partners")
    if not isinstance(partners, list) or not all(isinstance(p, str) and p for p in partners):
        return frozenset()
    return frozenset(partners)


def admitted_partners(
    robot_id: str,
    action: str | None,
    members: Sequence[str],
    order: Sequence[str] | None,
    completed: set[str] | frozenset[str],
    backing_up: bool = False,
    plan_partners: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """Return the robots a clearing robot is exempt against.

    A `reverse`, or a yield that names no passers, pairs with every other
    robot of its own command. A yield with a passer order pairs, while the
    yielder is known to be backing up or pulling off (`backing_up`), with
    every robot its command addressed: it is driving away from the scrum it
    was grounded to clear, and M3 swept that path clear of every robot. From
    the hold on, or when the phase is unknown, it pairs with `order[0]`, and
    with each later passer only once every earlier passer's wait under the
    command has COMPLETED, i.e. the command bus released it (a busy-reject's
    FAILED does not count). A robot outside the command is never a partner,
    EXCEPT `plan_partners` (freeze-blocking finding 3, step-7a fix): a
    `continue` leg of the SAME accepted plan as this `reverse`, named
    explicitly on the command's own parameters
    (`plan_continue_partners_from_parameters`) since it receives no command
    of its own to be a `member` of. Additive only, never a substitute for
    the own-command scope above.

    Args:
        robot_id: The clearing robot.
        action: Its ACTIVE command's per-robot action.
        members: Every robot the command addressed, in arrival order.
        order: `crossing_order_from_parameters` of the yield, or None.
        completed: Robots whose status for this command reached COMPLETED.
        backing_up: True only while the yield's latest phase signal is its
            backup or pull-off (`CoordinationTracker.record_status`).
        plan_partners: `plan_continue_partners_from_parameters`'s output for
            this SAME command/robot; empty for every pre-step-7a caller and
            for any action other than a plain `reverse` with a tracked plan.

    Returns:
        Partner robot ids, never including `robot_id`.
    """
    if not is_clearing_action(action):
        return frozenset()
    extra = frozenset(r for r in plan_partners if r != robot_id)
    if action != "yield" or order is None:
        return frozenset(r for r in members if r != robot_id) | extra
    if backing_up:
        return frozenset(r for r in (*members, *order) if r != robot_id) | extra
    admitted: list[str] = []
    for position, passer in enumerate(order):
        if position > 0 and order[position - 1] not in completed:
            break
        admitted.append(passer)
    return frozenset(r for r in admitted if r != robot_id) | extra


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

    This is the per-robot half of `ClearingExemption` (the speed rule and the
    STALE keep-latch rule); which pairs are exempt comes from
    `CoordinationTracker.exemption`. The passer's linked `temporary_wait` does
    not make it a clearing robot; its pair with the yielder is exempt through
    the yielder's own ACTIVE `yield`.

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
    on separate topics with no cross-topic ordering guarantee, so the maps
    are joined only when `exempt_robots` or `exemption` is called; a status
    that lands before its command resolves correctly once the command arrives.

    Command membership (which robots a command addressed) and per-command
    COMPLETED statuses are kept independently of the per-robot action map,
    which a terminal status clears: a passer's wait completing at hold start
    must not end the yielder-passer pair's exemption.

    A yield's phase comes from the ACTIVE status details the command bus
    publishes (`yield_phase.YIELD_BACKUP_PHASE_DETAILS`, then
    `HOLD_STARTED_DETAIL`). It is monotonic per command and robot: once any
    other non-empty detail is seen the backup phase is over for good, so a
    late republish of a backup-phase status cannot reopen it. A missing
    detail carries no phase and is never the backup phase (fail closed).
    """

    # Bound for command actions that never receive a terminal status (e.g. a
    # command dropped before dispatch). Far above any real in-flight count.
    MAX_TRACKED_COMMANDS = 256

    def __init__(self) -> None:
        self._action_by_key: dict[tuple[str, str], str] = {}
        self._active_by_robot: dict[str, str] = {}
        self._members_by_command: dict[str, list[str]] = {}
        self._order_by_command: dict[str, tuple[str, ...]] = {}
        self._completed_by_command: dict[str, set[str]] = {}
        # (command_id, robot_id) -> True while backing up, False once past it
        # for good; absent while no phase detail has been seen.
        self._backing_up_by_key: dict[tuple[str, str], bool] = {}
        # (command_id, robot_id) -> this reverse leg's extra same-plan
        # `continue` partners (freeze-blocking finding 3, step-7a fix); empty
        # for every pre-step-7a command and absent entirely once evicted.
        self._plan_partners_by_key: dict[tuple[str, str], frozenset[str]] = {}

    def record_command(
        self,
        command_id: str,
        robot_id: str,
        action: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> None:
        """Remember the per-robot action of a dispatched coordination command.

        Args:
            command_id: `CoordinationCommand.command_id`.
            robot_id: `CoordinationCommand.robot_id`.
            action: `CoordinationCommand.action`, e.g. `yield` or `reroute`.
            parameters: The decoded `parameters_json`, read for a yield's
                passer order and (step-7a fix) a reverse leg's extra
                same-plan `continue` partners; None when absent or
                unparseable.
        """
        if not command_id or not robot_id:
            return
        key = (command_id, robot_id)
        self._action_by_key.pop(key, None)
        self._action_by_key[key] = action
        self._plan_partners_by_key.pop(key, None)
        plan_partners = plan_continue_partners_from_parameters(action, parameters)
        if plan_partners:
            self._plan_partners_by_key[key] = plan_partners
        while len(self._action_by_key) > self.MAX_TRACKED_COMMANDS:
            evicted_key = next(iter(self._action_by_key))
            self._action_by_key.pop(evicted_key)
            self._plan_partners_by_key.pop(evicted_key, None)

        members = self._members_by_command.pop(command_id, [])
        if robot_id not in members:
            members.append(robot_id)
        self._members_by_command[command_id] = members
        order = crossing_order_from_parameters(action, parameters)
        if order is not None:
            self._order_by_command[command_id] = order
        while len(self._members_by_command) > self.MAX_TRACKED_COMMANDS:
            evicted = next(iter(self._members_by_command))
            del self._members_by_command[evicted]
            self._order_by_command.pop(evicted, None)
            self._completed_by_command.pop(evicted, None)

    def record_status(
        self, command_id: str, robot_id: str, status: str, detail: str | None = None
    ) -> bool:
        """Apply one `/coordination/status` update.

        A terminal status clears a robot only when it belongs to the command
        the robot is ACTIVE on, as in the command bus's in-flight registry: a
        busy-rejected command's FAILED, or a `base_mission` status from
        `coordination_client`, must not end a live maneuver's exemption.

        Args:
            command_id: `CoordinationStatus.command_id`.
            robot_id: `CoordinationStatus.robot_id`.
            status: `CoordinationStatus.status`.
            detail: `CoordinationStatus.detail`; an ACTIVE status's detail
                is the yield's phase signal. None counts as unknown.

        Returns:
            True if the robot's ACTIVE command changed.
        """
        if not robot_id:
            return False
        if status == "ACTIVE":
            self._record_phase(command_id, robot_id, detail)
            changed = self._active_by_robot.get(robot_id) != command_id
            self._active_by_robot[robot_id] = command_id
            return changed
        if status not in TERMINAL_STATUSES:
            return False
        if status == "COMPLETED" and command_id in self._members_by_command:
            self._completed_by_command.setdefault(command_id, set()).add(robot_id)
        self._action_by_key.pop((command_id, robot_id), None)
        self._backing_up_by_key.pop((command_id, robot_id), None)
        if self._active_by_robot.get(robot_id) == command_id:
            del self._active_by_robot[robot_id]
            return True
        return False

    def _record_phase(self, command_id: str, robot_id: str, detail: str | None) -> None:
        key = (command_id, robot_id)
        if self._backing_up_by_key.get(key) is False:
            return
        self._backing_up_by_key.pop(key, None)
        if not detail:
            return
        self._backing_up_by_key[key] = detail in YIELD_BACKUP_PHASE_DETAILS
        while len(self._backing_up_by_key) > self.MAX_TRACKED_COMMANDS:
            self._backing_up_by_key.pop(next(iter(self._backing_up_by_key)))

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
        """Return the robots running a clearing maneuver (`clearing_exempt_robots`)."""
        return clearing_exempt_robots(self._active_by_robot, self._action_by_key)

    def exemption(self) -> ClearingExemption:
        """Return the pair-scoped exemption for the current ACTIVE commands.

        Each clearing robot is paired with `admitted_partners` of its own
        ACTIVE command, in the phase its latest status signalled. A robot
        that command never addressed stays fully protected against it,
        EXCEPT a `continue` robot of the SAME tracked plan the reverse leg's
        own `parameters_json` names explicitly (step-7a fix, finding 3).

        Returns:
            The clearing robots and their exempt pairs.
        """
        clearing = self.exempt_robots()
        pairs: set[tuple[str, str]] = set()
        for robot_id in clearing:
            command_id = self._active_by_robot[robot_id]
            key = (command_id, robot_id)
            partners = admitted_partners(
                robot_id,
                self._action_by_key.get(key),
                self._members_by_command.get(command_id, ()),
                self._order_by_command.get(command_id),
                self._completed_by_command.get(command_id, frozenset()),
                backing_up=self._backing_up_by_key.get(key, False),
                plan_partners=self._plan_partners_by_key.get(key, frozenset()),
            )
            pairs.update(_pair_key(robot_id, partner) for partner in partners)
        return ClearingExemption(clearing_robots=clearing, pairs=frozenset(pairs))


def detect_proximity_violations(
    robots: list[dict],
    min_distance_m: float,
    exempt: ExemptInput = frozenset(),
) -> set[str]:
    """Return the ids of robots in any pair closer than `min_distance_m`.

    Distance is the Euclidean ground-plane separation between robot centres.
    The threshold is strict: a separation equal to `min_distance_m` is allowed,
    only strictly-closer pairs are flagged. Both robots in a violating pair are
    returned so the caller can stop each one.

    Exempt pairs are skipped: a yielder parked off-centerline during its
    hold must let the passer come closer than `min_distance_m`. The yielder
    pulls off 0.35 m while the latch threshold is 0.45 m, so without the pair
    exemption the pass itself would latch the passer and freeze both robots.
    Robot-level exemption on the caller side cannot express this: it
    unlatches the yielder but still latches its partner. The monitor passes
    `CoordinationTracker.exemption()`, which exempts only the clearing robot
    paired with its own command's partners, so a bystander still latches
    against a backing yielder.

    Args:
        robots: Robot state dicts, each with `robot_id`, `x`, and `y`.
        min_distance_m: Minimum allowed centre-to-centre separation in metres.
        exempt: A `ClearingExemption`, or a bare set of clearing robots, which
            exempts every pair with at least one such member (robot scope).

    Returns:
        The set of `robot_id`s involved in at least one violating pair.
    """
    exemption = _as_exemption(exempt)
    flagged: set[str] = set()
    for a, b in combinations(robots, 2):
        if exemption.covers_pair(a["robot_id"], b["robot_id"]):
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
    exempt: ExemptInput = frozenset(),
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

    Exempt pairs skip rule 2's remembered-distance latch exactly as they skip
    rule 1: a commanded backup is the designed way out of a close standoff and
    the fail-safe must not stall it. The keep-the-existing-latch half is per
    robot, so it is lifted for every clearing robot; a clearing robot that is
    still within the band of a non-exempt robot (a bystander) is re-latched
    by the pair-scoped half instead. A robot on a Nav2 leg or a wait is not
    exempt, so a latch that fired before such a command went ACTIVE persists
    (run K1, 2026-09-26).

    Args:
        robots: Robot state dicts with `robot_id`, `x`, `y`, and optionally
            `status`. A missing `status` is treated as non-STALE.
        limits: Safety invariants from `config/safety.yaml`.
        previous_latched: Robot ids latched by the previous evaluation.
        last_fresh_distances: Pairwise-distance memory returned by the previous
            evaluation; `None` on the first call.
        exempt: A `ClearingExemption`, or a bare set of clearing robots
            (robot scope; see `detect_proximity_violations`).

    Returns:
        The new latched set, the reason per latched robot, and the updated
        pairwise-distance memory.
    """
    exemption = _as_exemption(exempt)
    memory = dict(last_fresh_distances or {})
    latched: set[str] = set()
    reasons: dict[str, str] = {}

    for robot_id in detect_proximity_violations(
        robots, limits.min_distance_m, exemption
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
        if exemption.covers_pair(a_id, b_id):
            continue
        last_distance = memory.get(_pair_key(a_id, b_id))
        if last_distance is None or last_distance >= limits.stale_unsafe_distance_m:
            continue
        for robot_id in (a_id, b_id):
            latched.add(robot_id)
            reasons.setdefault(robot_id, REASON_STALE_POSE)

    for robot_id in stale & set(previous_latched):
        if robot_id in exemption.clearing_robots:
            continue
        latched.add(robot_id)
        reasons.setdefault(robot_id, REASON_STALE_POSE)

    return LatchEvaluation(frozenset(latched), reasons, memory)

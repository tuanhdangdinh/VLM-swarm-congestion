"""Pure base-mission driver logic for the M4 coordination client (ROS2-free).

M5 does not issue navigate goals — base goals "load from scenario/launch config
at startup" and "Layer 1 runs continuously; coordination commands modulate it,
they do not replace it" (M5 spec, Out of scope). This driver realizes that: it
keeps each robot navigating to its effective registry goal, hands ownership to the
command bus while a coordination command is in flight, and resumes base
navigation when the command resolves.

Ownership boundary (no contention on a robot's Nav2 goal):

- The driver owns a robot's `navigate_to_pose` goal *except* between a
  coordination command for that robot and *that same command's* terminal
  status — suppression is command-scoped, not merely robot-scoped.
- On a command it asks the caller to cancel the driver's own goal (the command
  bus and the client use separate `Nav2Adapter` instances, so the bus's own
  cancel does not touch the driver's goal), then suppresses re-issue and
  records the command as the suppression owner.
- On the *owner's* terminal status (COMPLETED/FAILED) it un-suppresses and
  re-issues the base goal — required because an override goal can equal the
  base goal (e.g. yield), so resumption cannot rely on a goal change. A
  terminal status for any other command — e.g. the command bus busy-rejecting
  a second command while the robot is still mid-maneuver — is ignored:
  unsuppressing there would re-issue the base goal, whose send cancels-all on
  the robot's `navigate_to_pose` and kills the in-flight maneuver.

State is keyed on Nav2 *acceptance*, not on send, for two runtime realities the
naive "mark issued on send" model gets wrong:

- **Startup race.** If the first navigate is sent before Nav2's action servers are
  lifecycle-ACTIVE it is rejected; since the registry is static after startup,
  nothing would ever re-issue. `on_goal_rejected` clears the confirmed goal so a
  periodic `retry()` re-sends until Nav2 accepts.
- **Status republish.** The command bus republishes each status ~3× (its
  re-publish timers). `on_status` acts only on the suppressed→resumed transition,
  so a republished COMPLETED does not thrash a fresh resume goal.

Hand-off race guard (`handoff_guard`, default on; docs/reports/
2026-10-08-ib10-remedy-validation.md run m4). The client learns of a command
only when it processes `/coordination/commands`, which can lag the command
bus's own dispatch by a few hundred ms. Three leaks let a base goal reach
Nav2 inside that window, and the guard closes all three:

- **Cross-robot resume fan-out.** A terminal for robot A used to return every
  unaccepted robot's goal, so robot B's goal was re-sent on A's terminal even
  though B's own successor command was already ACTIVE on the bus. With the
  guard, a terminal resumes only its own robot; any other robot that still
  needs a goal is re-issued by its own terminal or by `retry()`.
- **Registry re-send fan-out.** M5 republishes `/coordination/tasks` on every
  dispatch and resolve, i.e. at every phase hand-off, and `on_registry` used
  to return every unaccepted robot as well. With the guard it issues only
  robots whose goal is new or changed.
- **Late acceptance.** A base goal sent before the hand-off can be accepted by
  Nav2 after it. `on_goal_accepted` then reports it as not owned (returns
  False) and does not record it, so the caller cancels it and the owner's
  terminal still re-issues the base goal.

The guard suppresses rather than defers: nothing is queued while a command
owns the robot, and the existing terminal-driven resume stays the single,
immediate re-issue point that reads the current registry goal.
"""
from __future__ import annotations

_TERMINAL_STATUSES = {"COMPLETED", "FAILED"}

_Goal = tuple[float, float]


class BaseMissionDriver:
    """Decide which `navigate_to_pose` goals to (re)issue from registry/status."""

    def __init__(self, handoff_guard: bool = True) -> None:
        """Create a driver with no goals and no suppressed robots.

        Args:
            handoff_guard: Enable the hand-off race guard (module docstring).
                False restores the pre-guard behaviour exactly: a terminal
                resumes every unaccepted robot, and a late-accepted goal is
                recorded as accepted.
        """
        self._handoff_guard = handoff_guard
        self._goals: dict[str, _Goal] = {}
        self._accepted: dict[str, _Goal] = {}
        # robot_id -> command_id that owns the suppression (see on_command).
        self._suppressed_by: dict[str, str] = {}
        # robot_id -> the latest command_id seen for a robot that was already
        # suppressed (step-7b race guard; see on_command/on_status). Tracks
        # "the robot's currently-active command" independently of which
        # command this driver believes it owns, because /coordination/commands
        # and /coordination/status have no cross-topic ordering guarantee: a
        # successor command can be seen here before the predecessor's own
        # terminal status is processed.
        self._pending_next: dict[str, str] = {}
        # robot_id -> command_ids whose own terminal status was already seen
        # (and matched neither owner nor pending, i.e. fell to on_status's
        # "unknown" case) BEFORE this driver's on_command ever saw that same
        # command_id. Such a command will never send another terminal (the
        # command bus publishes each status a bounded number of times), so
        # recording it as pending later would promote it to owner on the
        # current owner's terminal and strand the robot suppressed forever,
        # with no terminal left to ever free it. on_command consults this to
        # discard such a command instead of queuing it.
        self._resolved_unmatched: dict[str, set[str]] = {}
        self._held: set[str] = set()
        # Log-worthy events since the last drain_events() call (race-guard
        # decisions); kept out of the return-value contract every existing
        # caller already depends on.
        self._events: list[str] = []

    def _desired(self) -> list[tuple[str, _Goal]]:
        """Owned, unheld robots whose Nav2-accepted goal differs from desired."""
        return [
            (robot_id, goal)
            for robot_id, goal in self._goals.items()
            if robot_id not in self._suppressed_by
            and robot_id not in self._held
            and self._accepted.get(robot_id) != goal
        ]

    def _resume(self, robot_id: str, command_id: str) -> list[tuple[str, _Goal]]:
        """Goals a terminal for `robot_id` re-issues (own robot only under the guard)."""
        desired = self._desired()
        if not self._handoff_guard:
            return desired
        others = sorted(rid for rid, _ in desired if rid != robot_id)
        if others:
            self._events.append(
                "handoff guard: cross-robot resume suppressed "
                f"trigger_robot={robot_id} trigger_command={command_id} "
                f"suppressed={','.join(others)}"
            )
        return [(rid, goal) for rid, goal in desired if rid == robot_id]

    def command_owner(self, robot_id: str) -> str | None:
        """Return the command id that currently owns `robot_id`, or None."""
        return self._suppressed_by.get(robot_id)

    def holds_command(self, robot_id: str, command_id: str) -> bool:
        """True while `command_id` owns `robot_id` and no successor has been seen.

        Args:
            robot_id: Robot to check.
            command_id: Command expected to own the robot.

        Returns:
            True when `command_id` is the suppression owner and no different
            command is queued behind it (`_pending_next`).
        """
        if self._suppressed_by.get(robot_id) != command_id:
            return False
        return self._pending_next.get(robot_id, command_id) == command_id

    def on_holds(self, held: set[str]) -> None:
        """Record the safety monitor's currently-latched robot set.

        Held robots are skipped by `on_registry`, `on_status`, and `retry`
        issuance. There is no special resume path: a robot released from hold
        is simply no longer excluded, so the next periodic `retry()` re-issues
        it like any other unaccepted goal.

        Args:
            held: Robot ids currently latched under a safety stop.
        """
        self._held = set(held)

    def on_registry(self, registry: dict[str, dict]) -> list[tuple[str, _Goal]]:
        """Record effective goals; return navigate goals to issue for owned robots.

        An entry flagged `start_pending` (M5's per-robot `start_delay_sec` has
        not elapsed) records no goal, so the robot is not driven until a later
        registry carries it without the flag. With the hand-off guard on, only
        robots whose goal is new or changed in this registry are returned; an
        unchanged, unaccepted goal is left to `retry()`.
        """
        changed: set[str] = set()
        for robot_id, entry in registry.items():
            if entry.get("start_pending"):
                continue
            goal = (float(entry["goal"][0]), float(entry["goal"][1]))
            if self._goals.get(robot_id) != goal:
                changed.add(robot_id)
            self._goals[robot_id] = goal
        desired = self._desired()
        if not self._handoff_guard:
            return desired
        # M5 republishes the registry on every dispatch and resolve, i.e. at
        # exactly the phase hand-offs where this client lags the command bus
        # (run m4's unlogged third send). Only a new or changed goal is issued
        # here; an unchanged unaccepted goal is left to retry().
        unchanged = sorted(rid for rid, _ in desired if rid not in changed)
        if unchanged:
            self._events.append(
                "handoff guard: registry re-send suppressed "
                f"suppressed={','.join(unchanged)}"
            )
        return [(rid, goal) for rid, goal in desired if rid in changed]

    def on_command(self, robot_id: str, command_id: str) -> bool:
        """Hand robot ownership to the command bus under `command_id`.

        Args:
            robot_id: Robot the coordination command targets.
            command_id: Command taking (or attempting to take) ownership.

        Returns:
            True if the driver was the owner (so the caller should cancel the
            driver's own navigate goal), False if the robot was already
            suppressed. In the latter case the original owner is kept: the
            command bus busy-rejects a second command for a mid-maneuver
            robot, so that command must not steal the suppression it never
            actually held. `command_id` is recorded as the robot's
            latest-seen command (step-7b race guard) so a stale terminal for
            the OLD owner, arriving after this one, is not mistaken for the
            robot's real, currently-active command -- UNLESS `command_id`'s
            own terminal already arrived and was seen as unmatched before
            this call (`_resolved_unmatched`): that command will never send
            another terminal, so recording it as pending now would promote
            it to owner later and strand the robot suppressed forever. Such
            a command is discarded instead, leaving the current owner
            untouched.
        """
        if robot_id in self._suppressed_by:
            if command_id in self._resolved_unmatched.get(robot_id, ()):
                self._resolved_unmatched[robot_id].discard(command_id)
                self._events.append(
                    "race guard: command resolved before being seen, discarded "
                    f"robot={robot_id} command={command_id}"
                )
                return False
            self._pending_next[robot_id] = command_id
            return False
        self._suppressed_by[robot_id] = command_id
        self._pending_next.pop(robot_id, None)
        self._accepted.pop(robot_id, None)
        return True

    def on_status(
        self, robot_id: str, command_id: str, status: str
    ) -> list[tuple[str, _Goal]]:
        """On the robot's currently-active command's terminal, resume base navigation.

        Only the robot's currently-active command's terminal unsuppresses.
        That is usually the suppression owner (`_suppressed_by`), but not
        always: `/coordination/commands` and `/coordination/status` carry no
        cross-topic ordering guarantee, so a successor command's `on_command`
        call can be processed here before the predecessor's own terminal
        status is (step-7b race guard, from a reproduced M4 race where a
        junction-phase successor was processed first and the predecessor's
        later, stale terminal then freed the robot for good instead of the
        successor holding it). Three cases, by which command_id this status
        matches:

        - The recorded owner, with no newer command seen since: genuine
          completion — unsuppress and resume, exactly as before.
        - The recorded owner, but a newer command was already seen for this
          robot (`_pending_next`): this terminal is stale for a superseded
          command. Logged and ignored in the sense that it never resumes
          base navigation — but the newer command is promoted to owner
          now, since the predecessor it was waiting behind has genuinely
          terminated.
        - The pending (not-yet-owning) command itself, arriving before the
          recorded owner's own terminal: a COMPLETED means the command bus
          had already finished it for real (this is the race's other
          direction) — promote and resume now. A FAILED means it never took
          ownership at all (e.g. a genuine busy-reject) — logged and
          ignored, the recorded owner is untouched.
        - Anything else (a duplicate/already-superseded terminal) is logged
          and ignored.

        Args:
            robot_id: Robot the status belongs to.
            command_id: Command the status belongs to.
            status: `ACTIVE`/`COMPLETED`/`FAILED`; only a terminal status
                (`COMPLETED`/`FAILED`) is acted on.

        Returns:
            Navigate goals to (re)issue, or `[]` when nothing resumes. With
            the hand-off guard on, only `robot_id`'s own goal is returned.
        """
        if status not in _TERMINAL_STATUSES:
            return []
        owner = self._suppressed_by.get(robot_id)
        pending = self._pending_next.get(robot_id)
        if command_id == owner:
            if pending is not None and pending != command_id:
                self._events.append(
                    "race guard: superseded terminal ignored "
                    f"robot={robot_id} command={command_id} status={status} "
                    f"promoted_to={pending}"
                )
                self._suppressed_by[robot_id] = pending
                self._pending_next.pop(robot_id, None)
                return []
            del self._suppressed_by[robot_id]
            self._pending_next.pop(robot_id, None)
            return self._resume(robot_id, command_id)
        if command_id == pending:
            self._pending_next.pop(robot_id, None)
            if status == "COMPLETED":
                self._events.append(
                    "race guard: pending command completed before predecessor "
                    f"terminal robot={robot_id} command={command_id} owner_was={owner}"
                )
                self._suppressed_by.pop(robot_id, None)
                return self._resume(robot_id, command_id)
            # This command_id never took ownership; a redelivery of its own
            # on_command (DDS retry) must not re-queue it as pending either,
            # since this was its one-and-only terminal.
            self._resolved_unmatched.setdefault(robot_id, set()).add(command_id)
            self._events.append(
                "race guard: stale terminal ignored "
                f"robot={robot_id} command={command_id} status={status} "
                f"reason=pending_never_owned owner={owner}"
            )
            return []
        # Neither the recorded owner nor the pending command: most often
        # this command_id's own terminal, arriving before this driver's
        # on_command for it ever did (no cross-topic ordering guarantee).
        # Recorded so a LATER on_command for this exact command_id (step-7b
        # race guard) knows it already resolved, rather than queuing it.
        self._resolved_unmatched.setdefault(robot_id, set()).add(command_id)
        self._events.append(
            "race guard: stale terminal ignored "
            f"robot={robot_id} command={command_id} status={status} "
            f"reason=unknown_command owner={owner}"
        )
        return []

    def drain_events(self) -> list[str]:
        """Return and clear log-worthy race-guard decisions since the last call."""
        events, self._events = self._events, []
        return events

    def on_goal_accepted(self, robot_id: str, goal: _Goal) -> bool:
        """Record that Nav2 accepted a navigate goal, so it is not re-issued.

        Args:
            robot_id: Robot whose base goal Nav2 accepted.
            goal: The accepted goal.

        Returns:
            True when the acceptance was recorded. False (guard on only) when
            a coordination command already owns the robot: the goal was sent
            before the hand-off and accepted after it, so it is not recorded
            and the caller must cancel it; the owner's terminal re-issues the
            base goal as usual.
        """
        owner = self._suppressed_by.get(robot_id)
        if self._handoff_guard and owner is not None:
            self._events.append(
                "handoff guard: late base goal accepted under command "
                f"robot={robot_id} owner={owner} "
                f"goal=({float(goal[0]):.2f}, {float(goal[1]):.2f})"
            )
            return False
        self._accepted[robot_id] = (float(goal[0]), float(goal[1]))
        return True

    def on_goal_rejected(self, robot_id: str) -> None:
        """Forget a rejected/failed goal so the next retry re-sends it."""
        self._accepted.pop(robot_id, None)

    def retry(self) -> list[tuple[str, _Goal]]:
        """Re-issue any owned goal Nav2 has not confirmed (e.g. sent before ACTIVE)."""
        return self._desired()

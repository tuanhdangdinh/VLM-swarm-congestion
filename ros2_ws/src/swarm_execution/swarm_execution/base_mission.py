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
"""
from __future__ import annotations

_TERMINAL_STATUSES = {"COMPLETED", "FAILED"}

_Goal = tuple[float, float]


class BaseMissionDriver:
    """Decide which `navigate_to_pose` goals to (re)issue from registry/status."""

    def __init__(self) -> None:
        self._goals: dict[str, _Goal] = {}
        self._accepted: dict[str, _Goal] = {}
        # robot_id -> command_id that owns the suppression (see on_command).
        self._suppressed_by: dict[str, str] = {}
        self._held: set[str] = set()

    def _desired(self) -> list[tuple[str, _Goal]]:
        """Owned, unheld robots whose Nav2-accepted goal differs from desired."""
        return [
            (robot_id, goal)
            for robot_id, goal in self._goals.items()
            if robot_id not in self._suppressed_by
            and robot_id not in self._held
            and self._accepted.get(robot_id) != goal
        ]

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
        """Record effective goals; return navigate goals to issue for owned robots."""
        for robot_id, entry in registry.items():
            self._goals[robot_id] = (float(entry["goal"][0]), float(entry["goal"][1]))
        return self._desired()

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
            actually held.
        """
        if robot_id in self._suppressed_by:
            return False
        self._suppressed_by[robot_id] = command_id
        self._accepted.pop(robot_id, None)
        return True

    def on_status(
        self, robot_id: str, command_id: str, status: str
    ) -> list[tuple[str, _Goal]]:
        """On the owning command's terminal status, re-issue base navigation.

        Only the suppression owner's terminal unsuppresses: a terminal for
        any other command (busy-reject FAILED, stale republish after the
        owner changed) returns `[]` and leaves suppression, held-set, and
        registry state untouched. The owner check also makes republished
        statuses (the command bus emits each ~3×) resume exactly once, since
        the first terminal removes the owner entry.
        """
        if status not in _TERMINAL_STATUSES:
            return []
        if self._suppressed_by.get(robot_id) != command_id:
            return []
        del self._suppressed_by[robot_id]
        return self._desired()

    def on_goal_accepted(self, robot_id: str, goal: _Goal) -> None:
        """Record that Nav2 accepted a navigate goal, so it is not re-issued."""
        self._accepted[robot_id] = (float(goal[0]), float(goal[1]))

    def on_goal_rejected(self, robot_id: str) -> None:
        """Forget a rejected/failed goal so the next retry re-sends it."""
        self._accepted.pop(robot_id, None)

    def retry(self) -> list[tuple[str, _Goal]]:
        """Re-issue any owned goal Nav2 has not confirmed (e.g. sent before ACTIVE)."""
        return self._desired()

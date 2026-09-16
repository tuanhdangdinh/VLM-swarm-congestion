"""Command watchdog core (fallback when no built-in controller timeout).

Pure stale-command decision used by the rclpy relay node in
`cmd_vel_watchdog_node.py`: forward the last `/<robot_id>/cmd_vel` to
`/<robot_id>/cmd_vel_safe` until no command has arrived for
command_timeout_sec, then zero it (FR6.4.8). Kept rclpy-free so it is
unit-testable without ROS 2 (CLAUDE.md: logic outside node classes).

Also holds the authoritative safety-hold state: `/<robot_id>/cmd_vel_safe` is
the only topic the drive graphs consume, so a robot listed in `/safety/holds`
must relay zero here no matter which of the four `/cmd_vel` publishers wrote
last (see `docs/specs/module4/safety-monitor.md` §8).
"""
from __future__ import annotations

import json


def watchdog_velocity(
    elapsed_sec: float | None,
    commanded: tuple[float, float],
    timeout_sec: float,
    held: bool = False,
) -> tuple[float, float]:
    """Return the (linear_x, angular_z) to forward, zeroed if held or stale.

    Args:
        elapsed_sec: Simulation seconds since the last command, or None if no
            command has been received yet.
        commanded: The last commanded `(linear_x, angular_z)`.
        timeout_sec: Stale threshold in seconds.
        held: True when the robot is under a safety hold (`/safety/holds`).

    Returns:
        `(0.0, 0.0)` if held or stale, else `commanded`.
    """
    # Checked before the timeout so a hold wins over a perfectly fresh command:
    # last-writer-wins on /cmd_vel cannot be trusted to carry the safety stop.
    if held:
        return (0.0, 0.0)
    if elapsed_sec is None or elapsed_sec > timeout_sec:
        return (0.0, 0.0)
    return commanded


def parse_holds(payload: str) -> tuple[set[str], bool]:
    """Parse a `/safety/holds` JSON payload into the held robot-id set.

    Args:
        payload: Message data, expected to be JSON `{"held": ["robot_1", ...]}`.

    Returns:
        `(held_ids, ok)`. `ok` is False for any malformed payload, with
        `held_ids` empty. Callers must warn and **keep their previous hold
        set** on `ok=False` rather than applying the empty set — dropping
        holds on a corrupt message would release the safety stop this relay
        exists to enforce.
    """
    try:
        decoded = json.loads(payload)
    except (ValueError, TypeError):
        return (set(), False)
    if not isinstance(decoded, dict):
        return (set(), False)
    ids = decoded.get("held", [])
    # A bare string would otherwise iterate into per-character "robot ids".
    if not isinstance(ids, list):
        return (set(), False)
    if not all(isinstance(rid, str) and rid for rid in ids):
        return (set(), False)
    return (set(ids), True)


class SafetyHoldState:
    """Held-robot set shared by every per-robot relay, fed from `/safety/holds`."""

    def __init__(self) -> None:
        self._held: frozenset[str] = frozenset()

    def set_held(self, robot_ids: set[str]) -> tuple[set[str], set[str]]:
        """Replace the held set and report the transitions it caused.

        Args:
            robot_ids: The full held set from the latest `/safety/holds` message.

        Returns:
            `(engaged, released)` — ids newly held and ids no longer held, so the
            caller can log once per transition instead of once per message.
        """
        incoming = frozenset(robot_ids)
        engaged = set(incoming - self._held)
        released = set(self._held - incoming)
        # Rebind rather than mutate: the relay timers read this set without a
        # lock, so a reader must never observe a half-updated set.
        self._held = incoming
        return (engaged, released)

    def is_held(self, robot_id: str) -> bool:
        """Return True when `robot_id` is currently under a safety hold."""
        return robot_id in self._held

"""Command watchdog core (fallback when no built-in controller timeout).

Pure stale-command decision used by the rclpy relay node in
`cmd_vel_watchdog_node.py`: forward the last `/<robot_id>/cmd_vel` to
`/<robot_id>/cmd_vel_safe` until no command has arrived for
command_timeout_sec, then zero it (FR6.4.8). Kept rclpy-free so it is
unit-testable without ROS 2 (CLAUDE.md: logic outside node classes).
"""
from __future__ import annotations


def watchdog_velocity(
    elapsed_sec: float | None,
    commanded: tuple[float, float],
    timeout_sec: float,
) -> tuple[float, float]:
    """Return the (linear_x, angular_z) to forward, zeroed if stale.

    Args:
        elapsed_sec: Simulation seconds since the last command, or None if no
            command has been received yet.
        commanded: The last commanded `(linear_x, angular_z)`.
        timeout_sec: Stale threshold in seconds.

    Returns:
        `commanded` if a command arrived within `timeout_sec`, else `(0.0, 0.0)`.
    """
    if elapsed_sec is None or elapsed_sec > timeout_sec:
        return (0.0, 0.0)
    return commanded

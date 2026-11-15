"""Command watchdog core (fallback when no built-in controller timeout).

Pure stale-command decision used by the rclpy relay node in
`cmd_vel_watchdog_node.py`: forward the last `/<robot_id>/cmd_vel` to
`/<robot_id>/cmd_vel_safe` until no command has arrived for
command_timeout_sec, then zero it (FR6.4.8). Kept rclpy-free so it is
unit-testable without ROS 2 (CLAUDE.md: logic outside node classes).
"""
from __future__ import annotations

import math


def forward_min_range(
    ranges: list[float] | tuple[float, ...],
    angle_min: float,
    angle_increment: float,
    sector_deg: float,
) -> float:
    """Return the nearest valid lidar return inside the forward sector."""
    if not ranges or angle_increment == 0.0:
        return math.inf

    half_sector = math.radians(sector_deg) / 2.0
    valid = []
    for index, value in enumerate(ranges):
        if math.isnan(value) or math.isinf(value) or value <= 0.0:
            continue
        angle = angle_min + index * angle_increment
        # Normalize to [-pi, pi] so sectors crossing the scan wrap work.
        angle = math.atan2(math.sin(angle), math.cos(angle))
        if abs(angle) <= half_sector:
            valid.append(value)
    return min(valid) if valid else math.inf


def forward_peer_distance(
    own_pose: tuple[float, float, float],
    peer_pose: tuple[float, float],
    lateral_half_width_m: float,
) -> float:
    """Return peer distance ahead in own frame, or inf if not in lane ahead."""
    own_x, own_y, own_yaw = own_pose
    peer_x, peer_y = peer_pose
    dx = peer_x - own_x
    dy = peer_y - own_y
    forward = math.cos(own_yaw) * dx + math.sin(own_yaw) * dy
    lateral = -math.sin(own_yaw) * dx + math.cos(own_yaw) * dy
    if forward <= 0.0 or abs(lateral) > lateral_half_width_m:
        return math.inf
    return forward


def watchdog_velocity(
    elapsed_sec: float | None,
    commanded: tuple[float, float],
    timeout_sec: float,
    forward_obstacle_m: float | None = None,
    stop_range_m: float = 0.45,
) -> tuple[float, float]:
    """Return the (linear_x, angular_z) to forward, zeroed if stale or blocked.

    Args:
        elapsed_sec: Simulation seconds since the last command, or None if no
            command has been received yet.
        commanded: The last commanded `(linear_x, angular_z)`.
        timeout_sec: Stale threshold in seconds.
        forward_obstacle_m: Nearest front-sector obstacle range, if known.
        stop_range_m: Stop if `forward_obstacle_m` is below this range.

    Returns:
        `commanded` if it is fresh and unblocked, else `(0.0, 0.0)`.
    """
    if elapsed_sec is None or elapsed_sec > timeout_sec:
        return (0.0, 0.0)
    if (
        forward_obstacle_m is not None
        and forward_obstacle_m < stop_range_m
        and commanded[0] > 0.0
    ):
        return (0.0, 0.0)
    return commanded

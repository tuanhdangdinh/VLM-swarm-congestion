import math
from typing import Literal

# Thresholds from spec §9.4
_STOPPED_MPS = 0.01
_SLOW_MPS = 0.03
_HEAD_ON_DISTANCE_M = 0.8
_INTERSECTION_RADIUS_M = 1.0
_ANOMALY_UPSTREAM_M = 1.0


def is_stopped(planar_speed_mps: float) -> bool:
    """Return True when speed is strictly below the stopped threshold (0.01 m/s).

    Args:
        planar_speed_mps: Planar speed magnitude in metres per second.

    Returns:
        True if the robot is considered stopped.
    """
    return planar_speed_mps < _STOPPED_MPS


def is_slow(planar_speed_mps: float) -> bool:
    """Return True when speed is strictly below the slow threshold (0.03 m/s).

    Args:
        planar_speed_mps: Planar speed magnitude in metres per second.

    Returns:
        True if the robot is considered slow (includes stopped).
    """
    return planar_speed_mps < _SLOW_MPS


def classify_speed(
    planar_speed_mps: float,
) -> Literal["STOPPED", "SLOW", "MOVING"]:
    """Classify a planar speed into one of three motion categories.

    Args:
        planar_speed_mps: Planar speed magnitude in metres per second.

    Returns:
        "STOPPED" if speed < 0.01, "SLOW" if speed < 0.03, else "MOVING".
    """
    if is_stopped(planar_speed_mps):
        return "STOPPED"
    if is_slow(planar_speed_mps):
        return "SLOW"
    return "MOVING"


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def head_on_conflict_active(
    positions: list[tuple[float, float]],
    speeds: list[float],
) -> bool:
    """True when both involved robots are stopped and their center distance < 0.8 m.

    Args:
        positions: Exactly two (x, y) world-frame positions in metres.
        speeds: Exactly two planar speed magnitudes in metres per second.

    Returns:
        True when both robots are stopped and within head-on conflict distance.

    Raises:
        ValueError: If positions or speeds do not contain exactly 2 elements.
    """
    if len(positions) != 2 or len(speeds) != 2:
        raise ValueError("head_on_conflict_active requires exactly 2 robots")
    both_stopped = all(is_stopped(s) for s in speeds)
    close_enough = _dist(positions[0], positions[1]) < _HEAD_ON_DISTANCE_M
    return both_stopped and close_enough


def intersection_conflict_active(
    positions: list[tuple[float, float]],
    speeds: list[float],
) -> bool:
    """True when >= 3 robots are within 1.0 m of origin and mean speed < 0.03 m/s.

    Args:
        positions: World-frame (x, y) positions in metres for all robots.
        speeds: Planar speed magnitudes in metres per second, same order as positions.

    Returns:
        True when an intersection bottleneck conflict is detected.
    """
    origin = (0.0, 0.0)
    in_radius = [
        i for i, pos in enumerate(positions)
        if _dist(pos, origin) < _INTERSECTION_RADIUS_M
    ]
    if len(in_radius) < 3:
        return False
    mean_speed = sum(speeds[i] for i in in_radius) / len(in_radius)
    return is_slow(mean_speed)


def anomaly_conflict_active(
    obstacle_pose: tuple[float, float],
    robot_positions: list[tuple[float, float]],
    robot_speeds: list[float],
    *,
    obstacle_active: bool,
) -> bool:
    """True when obstacle is active and an involved robot is slow within 1.0 m.

    Args:
        obstacle_pose: World-frame (x, y) position of the obstacle in metres.
        robot_positions: World-frame (x, y) positions for each robot in metres.
        robot_speeds: Planar speed magnitudes in metres per second, same order as
            robot_positions.
        obstacle_active: Whether the dynamic obstacle is currently present in the scene.

    Returns:
        True when a dynamic anomaly conflict is detected.
    """
    if not obstacle_active:
        return False
    for pos, speed in zip(robot_positions, robot_speeds):
        if _dist(pos, obstacle_pose) <= _ANOMALY_UPSTREAM_M and is_slow(speed):
            return True
    return False

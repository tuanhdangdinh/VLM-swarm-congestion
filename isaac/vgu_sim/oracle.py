import math
from typing import Literal

# Thresholds from spec §9.4
_STOPPED_MPS = 0.01
_SLOW_MPS = 0.03
_HEAD_ON_DISTANCE_M = 0.8
_INTERSECTION_RADIUS_M = 1.0
_ANOMALY_UPSTREAM_M = 1.0
# Bottleneck (B1/B3): how far from the aperture's lane segment a stopped pair's
# midpoint may sit (B1's designed merge is ~0.6 m west of the A55-E mouth), and
# the radius inside which a robot counts as parked at its own goal (M5's
# arrival_position_tolerance_m), so two robots resting at neighbouring goals
# beyond the gate never read as a conflict.
_BOTTLENECK_APPROACH_M = 1.0
_ARRIVED_RADIUS_M = 0.35


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


def _distance_to_segment(
    point: tuple[float, float], x_span: tuple[float, float], lane_y: float
) -> float:
    x = min(max(point[0], x_span[0]), x_span[1])
    return _dist(point, (x, lane_y))


def bottleneck_conflict_active(
    positions: list[tuple[float, float]],
    speeds: list[float],
    gate_x_span: tuple[float, float],
    *,
    distances_to_goal: list[float | None] | None = None,
    lane_y: float = 0.0,
) -> bool:
    """True when a stopped pair is jammed at a single-lane aperture (B1, B3).

    A pair qualifies when both robots are stopped (the head-on threshold,
    0.01 m/s), neither is parked at its own goal (within 0.35 m), their
    centres are closer than 0.8 m (the head-on distance), and the pair's
    midpoint lies within 1.0 m of the aperture's lane segment. Any
    qualifying pair makes the conflict active, whatever the headings: the
    B1 merge latches perpendicular, the B3 standoff head-on, and a follower
    latch behind either counts too.

    Args:
        positions: World-frame (x, y) positions in metres for every robot.
        speeds: Planar speeds in metres per second, same order.
        gate_x_span: The aperture's `(x_low, x_high)` in world metres (the
            scenario's `aisle_barrier` centre -/+ half its length).
        distances_to_goal: Each robot's distance to its own goal, same order;
            None (or a None entry) never excludes a robot.
        lane_y: World y of the aperture's lane centreline.

    Returns:
        True when at least one qualifying pair exists.

    Raises:
        ValueError: If the lists differ in length or the span is reversed.
    """
    if len(positions) != len(speeds) or (
        distances_to_goal is not None and len(distances_to_goal) != len(positions)
    ):
        raise ValueError("positions, speeds and distances_to_goal must align")
    if gate_x_span[0] > gate_x_span[1]:
        raise ValueError(f"gate_x_span {gate_x_span} is reversed")
    candidates = [
        i
        for i, speed in enumerate(speeds)
        if is_stopped(speed)
        and not (
            distances_to_goal is not None
            and distances_to_goal[i] is not None
            and distances_to_goal[i] <= _ARRIVED_RADIUS_M
        )
    ]
    for n, i in enumerate(candidates):
        for j in candidates[n + 1 :]:
            if _dist(positions[i], positions[j]) >= _HEAD_ON_DISTANCE_M:
                continue
            midpoint = (
                (positions[i][0] + positions[j][0]) / 2.0,
                (positions[i][1] + positions[j][1]) / 2.0,
            )
            if _distance_to_segment(midpoint, gate_x_span, lane_y) <= _BOTTLENECK_APPROACH_M:
                return True
    return False


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

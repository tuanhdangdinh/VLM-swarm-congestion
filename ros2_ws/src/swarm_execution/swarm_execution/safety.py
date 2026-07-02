"""Pure safety-invariant logic for the M4 safety monitor.

These functions are deliberately ROS2-free so the safety invariants
(`min_distance_m`, `max_linear_velocity_mps` from `config/safety.yaml`) can be
unit-tested without a running node. `safety_monitor_node.py` wires scene state
into these functions and actuates an emergency stop on the result.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class SafetyLimits:
    """Safety invariants loaded from `config/safety.yaml`."""

    min_distance_m: float
    max_linear_velocity_mps: float


def detect_proximity_violations(
    robots: list[dict], min_distance_m: float
) -> set[str]:
    """Return the ids of robots in any pair closer than `min_distance_m`.

    Distance is the Euclidean ground-plane separation between robot centres.
    The threshold is strict: a separation equal to `min_distance_m` is allowed,
    only strictly-closer pairs are flagged. Both robots in a violating pair are
    returned so the caller can stop each one.

    Args:
        robots: Robot state dicts, each with `robot_id`, `x`, and `y`.
        min_distance_m: Minimum allowed centre-to-centre separation in metres.

    Returns:
        The set of `robot_id`s involved in at least one violating pair.
    """
    flagged: set[str] = set()
    for a, b in combinations(robots, 2):
        distance = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
        if distance < min_distance_m:
            flagged.add(a["robot_id"])
            flagged.add(b["robot_id"])
    return flagged


def exceeds_speed_limit(linear_velocity: float, max_linear_velocity_mps: float) -> bool:
    """Return True if `linear_velocity` magnitude exceeds the speed limit."""
    return abs(linear_velocity) > max_linear_velocity_mps

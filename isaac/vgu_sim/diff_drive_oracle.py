"""Forward-displacement reference used as a TEST ORACLE only.

This module is never on the production drive path — Isaac's
`DifferentialController` OmniGraph node owns the in-sim twist→wheel math. This
function predicts the straight-line displacement of a constant forward command
so the in-sim integration test (tests/simulation/test_m4_phase1_drive.py) can
assert the robot actually moved that far end-to-end.
"""
from __future__ import annotations


def forward_distance(linear_x: float, duration_sec: float) -> float:
    """Return the straight-line distance covered at a constant forward speed.

    Args:
        linear_x: Forward body velocity in m/s.
        duration_sec: Drive duration in seconds.

    Returns:
        Distance in meters.
    """
    return linear_x * duration_sec

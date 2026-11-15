import math

from isaac.vgu_sim.cmd_vel_watchdog import (
    forward_min_range,
    forward_peer_distance,
    watchdog_velocity,
)

TIMEOUT = 0.5


def test_no_command_yet_is_zero():
    assert watchdog_velocity(None, (0.2, 0.1), TIMEOUT) == (0.0, 0.0)


def test_fresh_command_passes_through():
    assert watchdog_velocity(0.1, (0.2, 0.1), TIMEOUT) == (0.2, 0.1)


def test_stale_command_is_zeroed():
    assert watchdog_velocity(0.6, (0.2, 0.1), TIMEOUT) == (0.0, 0.0)


def test_exactly_at_timeout_still_passes():
    # stale only when strictly older than the timeout
    assert watchdog_velocity(0.5, (0.2, 0.1), TIMEOUT) == (0.2, 0.1)


def test_forward_obstacle_zeroes_fresh_forward_command():
    assert watchdog_velocity(0.1, (0.2, 0.1), TIMEOUT, 0.3, 0.32) == (0.0, 0.0)


def test_far_forward_obstacle_allows_fresh_command():
    assert watchdog_velocity(0.1, (0.2, 0.1), TIMEOUT, 0.8, 0.32) == (0.2, 0.1)


def test_forward_range_uses_angles_around_zero():
    # Five beams at -45, -22.5, 0, +22.5, +45 degrees. With a 35 degree
    # sector only the center beam is counted.
    ranges = [0.2, 0.3, 0.4, 0.25, 0.1]
    assert forward_min_range(ranges, -math.pi / 4, math.pi / 8, 35.0) == 0.4


def test_forward_peer_distance_returns_forward_component_for_in_lane_peer():
    assert forward_peer_distance((0.0, 0.0, 0.0), (0.4, 0.1), 0.25) == 0.4


def test_forward_peer_distance_ignores_peer_behind():
    assert math.isinf(forward_peer_distance((0.0, 0.0, 0.0), (-0.4, 0.0), 0.25))


def test_forward_peer_distance_ignores_peer_outside_lane():
    assert math.isinf(forward_peer_distance((0.0, 0.0, 0.0), (0.4, 0.4), 0.25))

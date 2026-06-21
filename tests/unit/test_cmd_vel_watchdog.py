from isaac.vgu_sim.cmd_vel_watchdog import watchdog_velocity

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

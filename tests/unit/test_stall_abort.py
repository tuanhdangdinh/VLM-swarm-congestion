"""Unit tests for the M4 execution-side stall abort detector (no ROS2).

Report: docs/reports/2026-11-15-m4-stall-abort.md. Every scenario is driven in
sim seconds at the primitives' 20 Hz tick, with odometry at 10 Hz (the
ground-truth rate the replay fixtures use; live odometry is faster).
"""
from __future__ import annotations

import math

import pytest
from pydantic import ValidationError
from swarm_execution.stall_abort import (
    STALL_ABORT_DETAIL_PREFIX,
    StallAbortConfig,
    StallDetector,
    StallWatch,
    config_from_safety,
    stall_abort_log_line,
    startup_suffix,
)

TICK = 0.05
ODOM_PERIOD = 0.1


def _cfg(**overrides) -> StallAbortConfig:
    return StallAbortConfig(enabled=True, **overrides)


def _run(
    detector: StallDetector,
    duration_s: float,
    command,
    pose,
    t0: float = 0.0,
    odom_ok=lambda t: True,
    held=lambda t: False,
):
    """Drive `detector` for `duration_s`; return the first verdict and its time.

    Args:
        command: `t -> (v, w)` commanded at that tick.
        pose: `t -> (x, y, yaw)` measured at that odometry stamp.
        odom_ok: `t -> bool`, False drops that odometry sample.
        held: `t -> bool`, the safety hold.
    """
    steps = int(round(duration_s / TICK))
    odom_index = 0
    for i in range(steps + 1):
        t = round(t0 + i * TICK, 6)
        while round(t0 + odom_index * ODOM_PERIOD, 6) <= t:
            stamp = round(t0 + odom_index * ODOM_PERIOD, 6)
            if odom_ok(stamp):
                detector.on_odom(stamp, *pose(stamp))
            odom_index += 1
        v, w = command(t)
        verdict = detector.observe(t, v, w, held=held(t))
        if verdict is not None:
            return verdict, t
    return None, None


def _straight(speed: float, start_s: float = 0.0, ramp_s: float = 0.0):
    """Pose of a robot driving along x at `speed` after `start_s`, with a linear ramp."""

    def pose(t: float):
        moving = max(0.0, t - start_s)
        if ramp_s > 0.0 and moving < ramp_s:
            x = 0.5 * speed * moving * moving / ramp_s
        else:
            x = speed * (moving - 0.5 * ramp_s)
        return (x, 0.0, 0.0)

    return pose


def _pinned_after(speed: float, stop_s: float):
    def pose(t: float):
        return (speed * min(t, stop_s), 0.0, 0.0)

    return pose


# Genuine stalls


def test_stall_fires_when_pinned_from_start() -> None:
    detector = StallDetector(_cfg())
    verdict, t = _run(detector, 30.0, lambda t: (-0.1, 0.0), lambda t: (0.0, 0.0, 0.0))
    assert verdict is not None and verdict.outcome == "stall"
    assert verdict.mode == "linear"
    cfg = _cfg()
    # First evaluable window: grace then one full window.
    assert t == pytest.approx(cfg.grace_s + cfg.window_s, abs=0.15)


def test_stall_fires_when_pinned_mid_manoeuvre() -> None:
    # The m5D robot_3 pattern: 0.09 m/s for 5.9 s, then stopped within 0.2 s.
    detector = StallDetector(_cfg())
    verdict, t = _run(detector, 60.0, lambda t: (0.1, 0.0), _pinned_after(0.09, 5.9))
    assert verdict is not None and verdict.outcome == "stall"
    assert 5.9 < t < 5.9 + _cfg().window_s + 0.2
    assert verdict.measured < verdict.expected_min


def test_stall_fires_on_slow_creep_below_threshold() -> None:
    cfg = _cfg()
    creep = 0.1 * cfg.min_progress_ratio * 0.5
    detector = StallDetector(cfg)
    verdict, _ = _run(detector, 30.0, lambda t: (0.1, 0.0), _straight(creep))
    assert verdict is not None and verdict.outcome == "stall"


def test_stall_fires_when_turn_in_place_is_blocked() -> None:
    detector = StallDetector(_cfg())
    verdict, _ = _run(detector, 30.0, lambda t: (0.0, 0.5), lambda t: (0.0, 0.0, 0.01))
    assert verdict is not None and verdict.outcome == "stall"
    assert verdict.mode == "angular"


def test_stall_fires_for_reverse_command_pinned() -> None:
    detector = StallDetector(_cfg())
    verdict, _ = _run(detector, 60.0, lambda t: (-0.1, 0.3), _pinned_after(-0.1, 4.0))
    assert verdict is not None and verdict.outcome == "stall"


# False-positive cases


def test_no_stall_when_driving_normally() -> None:
    detector = StallDetector(_cfg())
    verdict, _ = _run(detector, 60.0, lambda t: (0.1, 0.0), _straight(0.1))
    assert verdict is None


def test_no_stall_when_turning_in_place() -> None:
    detector = StallDetector(_cfg())
    verdict, _ = _run(
        detector, 20.0, lambda t: (0.0, 0.5), lambda t: (0.0, 0.0, 0.5 * t)
    )
    assert verdict is None


def test_no_stall_during_ramp_up_after_start() -> None:
    detector = StallDetector(_cfg())
    verdict, _ = _run(
        detector, 30.0, lambda t: (0.1, 0.0), _straight(0.1, start_s=0.5, ramp_s=1.0)
    )
    assert verdict is None


def test_no_stall_while_safety_hold_zeroes_the_command() -> None:
    # The primitive keeps publishing 0.1 m/s; the relay zeroes cmd_vel_safe.
    detector = StallDetector(_cfg())
    verdict, _ = _run(
        detector,
        60.0,
        lambda t: (0.1, 0.0),
        lambda t: (0.0, 0.0, 0.0),
        held=lambda t: True,
    )
    assert verdict is None


def test_no_stall_after_hold_release_within_grace() -> None:
    # Held for 20 s at a standstill, then released and driving normally.
    detector = StallDetector(_cfg())

    def pose(t: float):
        return (0.1 * max(0.0, t - 20.3), 0.0, 0.0)

    verdict, _ = _run(
        detector, 40.0, lambda t: (0.1, 0.0), pose, held=lambda t: t < 20.0
    )
    assert verdict is None


def test_no_stall_when_waiting_with_zero_command() -> None:
    detector = StallDetector(_cfg())
    verdict, _ = _run(detector, 60.0, lambda t: (0.0, 0.0), lambda t: (0.0, 0.0, 0.0))
    assert verdict is None


def test_no_stall_when_commanded_speed_is_below_minimum() -> None:
    cfg = _cfg()
    detector = StallDetector(cfg)
    slow = cfg.min_linear_mps * 0.5
    verdict, _ = _run(detector, 60.0, lambda t: (slow, 0.0), lambda t: (0.0, 0.0, 0.0))
    assert verdict is None


def test_no_stall_during_brief_odometry_dropout() -> None:
    cfg = _cfg()
    detector = StallDetector(cfg)
    gap_s = cfg.stale_input_s * 0.8
    verdict, _ = _run(
        detector,
        30.0,
        lambda t: (0.1, 0.0),
        _straight(0.1),
        odom_ok=lambda t: not (10.0 < t < 10.0 + gap_s),
    )
    assert verdict is None


def test_input_stale_on_long_odometry_dropout() -> None:
    cfg = _cfg()
    detector = StallDetector(cfg)
    verdict, t = _run(
        detector,
        30.0,
        lambda t: (0.1, 0.0),
        _straight(0.1),
        odom_ok=lambda t: t < 10.0,
    )
    assert verdict is not None and verdict.outcome == "input_stale"
    assert t == pytest.approx(10.0 - ODOM_PERIOD + cfg.stale_input_s, abs=TICK + 1e-6)
    assert verdict.odom_age_s > cfg.stale_input_s


def test_input_stale_when_no_odometry_ever_arrives() -> None:
    cfg = _cfg()
    detector = StallDetector(cfg)
    verdict, t = _run(
        detector, 10.0, lambda t: (-0.1, 0.0), _straight(0.1), odom_ok=lambda t: False
    )
    assert verdict is not None and verdict.outcome == "input_stale"
    assert t == pytest.approx(cfg.stale_input_s, abs=TICK + 1e-6)


def test_input_stale_even_with_zero_command() -> None:
    # A primitive that cannot see its own odometry cannot verify anything.
    detector = StallDetector(_cfg())
    verdict, _ = _run(
        detector, 10.0, lambda t: (0.0, 0.0), _straight(0.0), odom_ok=lambda t: t < 2.0
    )
    assert verdict is not None and verdict.outcome == "input_stale"


def test_no_stall_while_decelerating_at_the_end() -> None:
    detector = StallDetector(_cfg())

    def command(t: float):
        return (max(0.0, 0.1 * (1.0 - max(0.0, t - 10.0) / 3.0)), 0.0)

    def pose(t: float):
        if t <= 10.0:
            return (0.1 * t, 0.0, 0.0)
        tau = min(t - 10.0, 3.0)
        return (1.0 + 0.1 * (tau - tau * tau / 6.0), 0.0, 0.0)

    verdict, _ = _run(detector, 20.0, command, pose)
    assert verdict is None


def test_no_stall_with_noisy_measurements() -> None:
    detector = StallDetector(_cfg())

    def pose(t: float):
        noise = 0.004 * math.sin(37.0 * t) + 0.003 * math.cos(91.0 * t)
        return (0.1 * t + noise, noise, 0.02 * math.sin(13.0 * t))

    verdict, _ = _run(detector, 60.0, lambda t: (0.1, 0.0), pose)
    assert verdict is None


def test_no_stall_with_noise_on_a_stationary_held_robot() -> None:
    detector = StallDetector(_cfg())

    def pose(t: float):
        return (0.005 * math.sin(37.0 * t), 0.005 * math.cos(53.0 * t), 0.0)

    verdict, _ = _run(detector, 60.0, lambda t: (0.0, 0.0), pose)
    assert verdict is None


def test_verdict_is_identical_at_any_real_time_factor() -> None:
    # The detector sees only sim seconds (node clock and odometry stamps), so
    # a 0.17x and a 1.0x run of the same sim-time trace are the same input.
    # Here the wall time per tick differs but is never passed in; the sim
    # trace is replayed identically, so the verdicts must match exactly.
    results = []
    for _rtf in (0.17, 1.0):
        detector = StallDetector(_cfg())
        results.append(
            _run(detector, 60.0, lambda t: (0.1, 0.0), _pinned_after(0.09, 5.9))
        )
    assert results[0] == results[1]


def test_no_stall_across_turn_then_drive_phase_change() -> None:
    detector = StallDetector(_cfg())

    def command(t: float):
        return (0.0, 0.5) if t < 6.28 else (0.1, 0.0)

    def pose(t: float):
        if t < 6.28:
            return (0.0, 0.0, 0.5 * t)
        lag = max(0.0, t - 6.28 - 0.3)
        return (-0.1 * lag, 0.0, 3.14)

    verdict, _ = _run(detector, 30.0, command, pose)
    assert verdict is None


def test_out_of_order_odometry_is_ignored() -> None:
    detector = StallDetector(_cfg())
    detector.on_odom(1.0, 0.0, 0.0, 0.0)
    detector.on_odom(0.5, 5.0, 5.0, 0.0)
    assert detector.latest_odom_stamp == 1.0


# Config, log line, startup suffix


def test_config_defaults_off() -> None:
    assert StallAbortConfig().enabled is False


def test_config_rejects_non_positive_window() -> None:
    with pytest.raises(ValidationError):
        StallAbortConfig(window_s=0.0)


def test_config_rejects_ratio_outside_unit_interval() -> None:
    with pytest.raises(ValidationError):
        StallAbortConfig(min_progress_ratio=1.5)


def test_config_from_safety_absent_is_off() -> None:
    assert config_from_safety({"min_distance_m": 0.45}).enabled is False


def test_config_from_safety_enabled_only_on_literal_true() -> None:
    assert config_from_safety({"stall_abort": {"enabled": "true"}}).enabled is False
    assert config_from_safety({"stall_abort": {"enabled": 1}}).enabled is False
    assert config_from_safety({"stall_abort": {"enabled": True}}).enabled is True


def test_config_from_safety_reads_parameters() -> None:
    cfg = config_from_safety({"stall_abort": {"enabled": True, "window_s": 4.0}})
    assert cfg.window_s == 4.0


def test_config_from_safety_non_mapping_is_off() -> None:
    assert config_from_safety({"stall_abort": True}).enabled is False


def test_startup_suffix_empty_when_off() -> None:
    assert startup_suffix(StallAbortConfig()) == ""


def test_startup_suffix_names_every_parameter_when_on() -> None:
    cfg = _cfg()
    suffix = startup_suffix(cfg)
    assert suffix.startswith(" stall_abort=True ")
    for name in (
        "window_s",
        "min_progress_ratio",
        "grace_s",
        "stale_input_s",
        "min_linear_mps",
        "min_angular_radps",
        "min_expected_m",
        "min_expected_rad",
    ):
        assert f"{name}={getattr(cfg, name)}" in suffix


def test_stall_detail_format_linear() -> None:
    detector = StallDetector(_cfg())
    verdict, _ = _run(detector, 30.0, lambda t: (0.1, 0.0), lambda t: (0.0, 0.0, 0.0))
    detail = verdict.detail()
    assert detail.startswith(f"{STALL_ABORT_DETAIL_PREFIX} commanded 0.100 m/s for 3.0 s")
    assert "measured 0.000 m (expected >= 0.075 m)" in detail


def test_input_stale_detail_names_the_age() -> None:
    detector = StallDetector(_cfg())
    verdict, _ = _run(
        detector, 10.0, lambda t: (0.1, 0.0), _straight(0.1), odom_ok=lambda t: False
    )
    assert verdict.detail().startswith(f"{STALL_ABORT_DETAIL_PREFIX} input_stale")


def test_log_line_has_the_scorer_keys() -> None:
    detector = StallDetector(_cfg())
    verdict, _ = _run(detector, 30.0, lambda t: (0.1, 0.0), lambda t: (0.0, 0.0, 0.0))
    line = stall_abort_log_line("cmd-1", "robot_3", "escort", "drive", verdict, 150.25)
    assert line.startswith(
        "stall abort robot=robot_3 command=cmd-1 primitive=escort phase=drive reason=stall "
    )
    for key in ("commanded_m=0.300", "measured_m=0.000", "window_s=3.00", "sim_t=150.250"):
        assert key in line


def test_watch_gates_command_on_safety_hold() -> None:
    held = {"value": True}
    lines: list[str] = []
    watch = StallWatch(
        _cfg(),
        robot_id="robot_1",
        command_id="c",
        primitive="backup",
        is_held=lambda: held["value"],
        log=lines.append,
    )
    t = 0.0
    for i in range(400):
        t = i * TICK
        if i % 2 == 0:
            watch.on_odom(t, 0.0, 0.0, 0.0)
        assert watch.observe(t, -0.1, 0.0, phase="backup") is None
    held["value"] = False
    detail = None
    for i in range(400, 600):
        t = i * TICK
        if i % 2 == 0:
            watch.on_odom(t, 0.0, 0.0, 0.0)
        detail = watch.observe(t, -0.1, 0.0, phase="backup")
        if detail is not None:
            break
    assert detail is not None and detail.startswith(STALL_ABORT_DETAIL_PREFIX)
    assert len(lines) == 1 and lines[0].startswith("stall abort robot=robot_1 command=c")


def test_watch_fires_once() -> None:
    lines: list[str] = []
    watch = StallWatch(_cfg(), "robot_1", "c", "backup", log=lines.append)
    fired = 0
    for i in range(400):
        t = i * TICK
        watch.on_odom(t, 0.0, 0.0, 0.0)
        if watch.observe(t, -0.1, 0.0, phase="backup") is not None:
            fired += 1
    assert fired == 1 and len(lines) == 1

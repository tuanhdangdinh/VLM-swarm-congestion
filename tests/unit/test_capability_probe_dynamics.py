"""GT derivation rules for the battery-v2 dynamic probe types (synthetic tracks)."""

from __future__ import annotations

import math

import pytest

from reasoning.vlm.capability_probes import dynamics as dyn
from reasoning.vlm.capability_probes.episode_v2 import command_windows_from_log


def _track(paths: dict, t_end: float = 40.0, goals: dict | None = None) -> dyn.GtTrack:
    """10 Hz GT rows; `paths[rid](t) -> (x, y, theta)`."""
    rows = []
    steps = int(round(t_end * 10))
    for i in range(steps + 1):
        t = round(i * 0.1, 4)
        robots = {}
        for rid, path in paths.items():
            x, y, theta = path(t)
            robot = {"x": x, "y": y, "theta": theta, "speed_mps": 0.0}
            if goals and rid in goals:
                gx, gy = goals[rid]
                robot.update(
                    {"goal_x": gx, "goal_y": gy, "distance_to_goal_m": math.hypot(gx - x, gy - y)}
                )
            robots[rid] = robot
        rows.append({"sim_time_sec": t, "robots": robots})
    return dyn.GtTrack(rows)


def _line(x0, y0, vx, vy, t_start=0.0, t_stop=1e9):
    theta = math.atan2(vy, vx) if (vx or vy) else 0.0

    def path(t):
        dt = min(max(t - t_start, 0.0), t_stop - t_start)
        return x0 + vx * dt, y0 + vy * dt, theta

    return path


def _still(x, y, theta=0.0):
    return lambda t: (x, y, theta)


def _motion(rid, speed, pixel_motion, pixel=(0.0, 0.0), reversing=False):
    return dyn.RobotMotion(
        robot_id=rid,
        speed_mps=speed,
        motion=dyn.motion_class(speed),
        reversing=reversing,
        pixel_motion=pixel_motion,
        pixel=pixel,
    )


def test_velocity_is_backward_position_difference():
    track = _track({"r": _line(0.0, 0.0, 0.2, 0.0)})
    vx, vy = track.velocity("r", 10.0)
    assert vx == pytest.approx(0.2) and vy == pytest.approx(0.0)


def test_velocity_ignores_heading_for_a_reversing_robot():
    # Heading +x, moving -x (M4 backup): motion must come from positions.
    track = _track({"r": lambda t: (5.0 - 0.1 * t, 0.0, 0.0)})
    vx, _ = track.velocity("r", 10.0)
    assert vx == pytest.approx(-0.1)
    assert dyn.is_reversing((vx, 0.0), 0.0)


def test_row_near_rejects_stamps_outside_tolerance():
    track = _track({"r": _still(0, 0)}, t_end=5.0)
    assert track.row_near(5.2) is None
    assert track.row_near(4.97)["sim_time_sec"] == pytest.approx(5.0)


@pytest.mark.parametrize(
    ("speed", "expected"),
    [
        (0.15, "moving"),
        (0.08, "moving"),
        (0.05, "ambiguous"),
        (0.03, "stationary"),
        (None, "ambiguous"),
    ],
)
def test_motion_class_bands(speed, expected):
    assert dyn.motion_class(speed) == expected


def test_motion_direction_edge_single_robot_toward():
    motions = {
        "robot_1": _motion("robot_1", 0.15, (10.0, 0.0)),
        "robot_2": _motion("robot_2", 0.0, (0.0, 0.0)),
    }
    answer, reason, classes = dyn.motion_direction_answer(motions, "edge:right")
    assert (answer, reason) == ("robot_1", "ok")
    assert classes == {"robot_1": "toward", "robot_2": "not_toward"}


def test_motion_direction_two_robots_toward_is_dropped():
    motions = {
        "robot_1": _motion("robot_1", 0.15, (10.0, 0.0)),
        "robot_2": _motion("robot_2", 0.15, (10.0, 1.0)),
    }
    assert dyn.motion_direction_answer(motions, "edge:right")[1] == "several_robots_toward"


def test_motion_direction_no_robot_toward_is_dropped():
    motions = {
        "robot_1": _motion("robot_1", 0.15, (-10.0, 0.0)),
        "robot_2": _motion("robot_2", 0.0, (0.0, 0.0)),
    }
    assert dyn.motion_direction_answer(motions, "edge:right")[1] == "no_robot_toward"


def test_motion_direction_angle_inside_margin_band_is_ambiguous():
    # 50 deg off the bearing: neither toward (<= 30) nor clearly not (>= 75).
    direction = (math.cos(math.radians(50)), math.sin(math.radians(50)))
    motions = {
        "robot_1": _motion("robot_1", 0.15, (10.0, 0.0)),
        "robot_2": _motion("robot_2", 0.15, direction),
    }
    assert dyn.motion_direction_answer(motions, "edge:right")[1] == "ambiguous_option"


def test_motion_direction_slow_creeping_option_is_ambiguous():
    motions = {
        "robot_1": _motion("robot_1", 0.15, (10.0, 0.0)),
        "robot_2": _motion("robot_2", 0.05, (-1.0, 0.0)),
    }
    assert dyn.motion_direction_answer(motions, "edge:right")[1] == "ambiguous_option"


def test_motion_direction_reversing_option_is_dropped():
    motions = {
        "robot_1": _motion("robot_1", 0.15, (10.0, 0.0), reversing=True),
        "robot_2": _motion("robot_2", 0.0, (0.0, 0.0)),
    }
    assert dyn.motion_direction_answer(motions, "edge:right")[1] == "reversing_robot"


def test_motion_direction_robot_target_uses_bearing_and_excludes_target():
    motions = {
        "robot_1": _motion("robot_1", 0.15, (10.0, 0.0), pixel=(100.0, 500.0)),
        "robot_2": _motion("robot_2", 0.0, (0.0, 0.0), pixel=(600.0, 500.0)),
        "robot_3": _motion("robot_3", 0.15, (0.0, -10.0), pixel=(600.0, 800.0)),
    }
    answer, reason, classes = dyn.motion_direction_answer(motions, "robot:robot_2")
    # robot_3 moves up the image (-v) straight at robot_2 too: two toward.
    assert reason == "several_robots_toward"
    assert set(classes) == {"robot_1", "robot_3"}
    motions["robot_3"] = _motion("robot_3", 0.15, (10.0, 0.0), pixel=(600.0, 800.0))
    assert dyn.motion_direction_answer(motions, "robot:robot_2")[:2] == ("robot_1", "ok")


def test_motion_direction_robot_target_needs_two_other_robots():
    motions = {
        "robot_1": _motion("robot_1", 0.15, (10.0, 0.0)),
        "robot_2": _motion("robot_2", 0.0, (0.0, 0.0), pixel=(600.0, 0.0)),
    }
    assert dyn.motion_direction_answer(motions, "robot:robot_2")[1] == "too_few_options"


def _head_on_track():
    # robot_1 drives at 0.15 m/s toward a parked robot_2 and stops 0.35 m short.
    stop_at = (3.5 - 0.35) / 0.15
    return _track(
        {"robot_1": _line(-2.0, 0.0, 0.15, 0.0, t_stop=stop_at), "robot_2": _still(1.5, 0.0)}
    )


def test_conflict_yes_when_threshold_reached_within_horizon():
    answer, reason, facts = dyn.conflict_prediction_answer(
        _head_on_track(), "robot_1", "robot_2", 12.0
    )
    assert (answer, reason) == ("yes", "ok")
    assert facts["future_min_distance_m"] <= dyn.CONFLICT_YES_MAX_M


def test_conflict_no_when_paths_stay_apart():
    track = _track({"robot_1": _line(-2.0, 0.0, 0.15, 0.0), "robot_3": _still(0.0, 1.5)})
    answer, reason, _ = dyn.conflict_prediction_answer(track, "robot_1", "robot_3", 5.0)
    assert (answer, reason) == ("no", "ok")


def test_conflict_drops_unreachable_threshold():
    # 3.5 m apart, one robot at 0.15 m/s: 0.5 m is unreachable in 10 s.
    answer, reason, _ = dyn.conflict_prediction_answer(_head_on_track(), "robot_1", "robot_2", 1.0)
    assert (answer, reason) == (None, "threshold_unreachable")


def test_conflict_drops_pair_already_close():
    assert (
        dyn.conflict_prediction_answer(_head_on_track(), "robot_1", "robot_2", 19.0)[1]
        == "already_close"
    )


def test_conflict_drops_pair_with_nobody_moving():
    track = _track({"a": _still(0.0, 0.0), "b": _still(1.0, 0.0)})
    assert dyn.conflict_prediction_answer(track, "a", "b", 5.0)[1] == "pair_not_moving"


def test_conflict_drops_future_minimum_inside_margin_band():
    stop_at = (3.5 - 0.5) / 0.15  # settles exactly at 0.5 m
    track = _track({"a": _line(-2.0, 0.0, 0.15, 0.0, t_stop=stop_at), "b": _still(1.5, 0.0)})
    assert dyn.conflict_prediction_answer(track, "a", "b", 12.0)[1] == "margin_too_small"


def test_conflict_drops_horizon_past_end_of_gt():
    assert (
        dyn.conflict_prediction_answer(_head_on_track(), "robot_1", "robot_2", 35.0)[1]
        == "horizon_beyond_gt"
    )


def test_command_window_inside_horizon_excludes():
    assert not dyn.horizon_is_command_free(10.0, 10.0, [(15.0, 30.0)])


def test_command_window_active_at_stamp_excludes():
    assert not dyn.horizon_is_command_free(10.0, 10.0, [(2.0, 11.0)])


def test_command_window_outside_horizon_keeps():
    assert dyn.horizon_is_command_free(10.0, 10.0, [(0.0, 9.5), (20.5, 40.0)])


def test_wall_to_sim_interpolates_and_extrapolates_at_real_time():
    anchors = [(1000.0, 10.0), (1010.0, 14.0)]
    assert dyn.wall_to_sim(1005.0, anchors) == pytest.approx(12.0)
    assert dyn.wall_to_sim(1020.0, anchors) == pytest.approx(24.0)


_P = "[orchestrator_node-1] [INFO] [{}] [orchestrator_node]: "
_LOG = "\n".join(
    [
        _P.format("1000.000000000") + "starting analysis request=aa11 robots=['robot_1'] reason=x",
        _P.format("1000.400000000") + "dispatch request=aa11 command=aa11-yield robot=robot_2",
        _P.format("1000.410000000") + "dispatch request=aa11 command=aa11-yield robot=robot_1",
        _P.format("1050.000000000") + "starting analysis request=bb22 robots=['robot_2'] reason=x",
        _P.format("1040.000000000") + "command aa11-yield resolved status=completed",
    ]
)


def test_command_windows_open_at_decision_stamp_and_close_at_resolution():
    windows = command_windows_from_log(_LOG, {"aa11": 20.0, "bb22": 40.0})
    # Resolution at wall 1040 maps to sim 36.0 (anchors 1000->20, 1050->40).
    assert windows == [(20.0, pytest.approx(36.0 + dyn.COMMAND_END_SLACK_SEC))]


def test_unresolved_command_window_stays_open():
    log = "\n".join(line for line in _LOG.splitlines() if "resolved" not in line)
    assert command_windows_from_log(log, {"aa11": 20.0})[0][1] == math.inf


def test_no_dispatch_means_no_windows():
    assert command_windows_from_log("nothing here\n", {}) == []


def test_dispatch_without_any_anchor_is_unmappable():
    assert command_windows_from_log(_LOG, {}) is None


def test_motion_onset_detects_delayed_start():
    track = _track({"r": _line(0.0, 0.0, 0.15, 0.0, t_start=12.0)})
    assert dyn.motion_onset_times(track)["r"] == pytest.approx(12.2, abs=0.11)


def _arrival_track(t1=10.0, t2=15.0):
    return _track(
        {
            "robot_1": _line(0.0, 0.0, 0.2, 0.0, t_stop=t1),
            "robot_2": _line(0.0, 1.0, 0.2, 0.0, t_stop=t2),
        },
        goals={"robot_1": (0.2 * t1, 0.0), "robot_2": (0.2 * t2, 1.0)},
    )


def test_goal_arrival_time_is_first_row_within_tolerance():
    arrival = dyn.goal_arrival_time(_arrival_track(), "robot_1", 16.0)
    assert arrival == pytest.approx(10.0 - dyn.GOAL_ARRIVAL_TOLERANCE_M / 0.2, abs=0.11)


def test_temporal_order_goal_answer_inside_window():
    answer, reason, facts = dyn.temporal_order_answer(
        _arrival_track(), "goal", "robot_1", "robot_2", 16.0
    )
    assert (answer, reason) == ("robot_1", "ok")
    assert (
        dyn.TEMPORAL_WINDOW_SEC[0] <= facts["since_later_event_sec"] <= dyn.TEMPORAL_WINDOW_SEC[1]
    )


def test_temporal_order_outside_window_is_dropped():
    assert (
        dyn.temporal_order_answer(_arrival_track(), "goal", "robot_1", "robot_2", 25.0)[1]
        == "outside_window"
    )


def test_temporal_order_before_both_events_is_dropped():
    assert (
        dyn.temporal_order_answer(_arrival_track(), "goal", "robot_1", "robot_2", 12.0)[1]
        == "event_missing"
    )


def test_temporal_order_near_tie_is_dropped():
    track = _arrival_track(t1=10.0, t2=11.0)
    assert (
        dyn.temporal_order_answer(track, "goal", "robot_1", "robot_2", 12.0)[1] == "gap_too_small"
    )


def test_stop_time_needs_preceding_motion():
    parked = _track({"r": _still(0.0, 0.0)})
    assert dyn.stop_time(parked, "r", 10.0) is None
    track = _track({"r": _line(0.0, 0.0, 0.2, 0.0, t_stop=5.0)})
    assert dyn.stop_time(track, "r", 10.0) == pytest.approx(5.4, abs=0.15)


def test_temporal_order_stop_needs_a_standoff():
    # Both robots stop 2 s+ apart in time, but 3 m apart in space: no standoff.
    track = _track(
        {
            "robot_1": _line(0.0, 0.0, 0.2, 0.0, t_stop=10.0),
            "robot_2": _line(0.0, 3.0, 0.2, 0.0, t_stop=15.0),
        }
    )
    assert (
        dyn.temporal_order_answer(track, "stop", "robot_1", "robot_2", 16.0)[1] == "not_a_standoff"
    )
    near = _track(
        {
            "robot_1": _line(0.0, 0.0, 0.2, 0.0, t_stop=10.0),
            "robot_2": _line(0.0, 0.5, 0.2, 0.0, t_stop=12.5),
        }
    )
    assert dyn.temporal_order_answer(near, "stop", "robot_1", "robot_2", 14.0)[:2] == (
        "robot_1",
        "ok",
    )


def test_yes_exclusion_horizon_ends_at_first_threshold_crossing():
    answer, _, facts = dyn.conflict_prediction_answer(_head_on_track(), "robot_1", "robot_2", 12.0)
    assert answer == "yes"
    crossing = facts["first_within_threshold_sec"]
    # Crossing 0.5 m: robot_1 reaches x = 1.0 at t = 3.0 / 0.15 = 20.0 s.
    assert crossing == pytest.approx(20.0, abs=0.11)
    assert dyn.exclusion_horizon_sec("yes", 12.0, facts) == pytest.approx(crossing - 12.0)
    # A command dispatched after the crossing cannot change a "yes".
    assert dyn.horizon_is_command_free(12.0, crossing - 12.0, [(crossing + 0.5, 40.0)])


def test_no_exclusion_horizon_is_the_full_horizon():
    assert dyn.exclusion_horizon_sec("no", 5.0, {}) == dyn.CONFLICT_HORIZON_SEC

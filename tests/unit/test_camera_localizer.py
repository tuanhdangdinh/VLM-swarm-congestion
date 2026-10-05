"""Unit tests for camera-based localization maths (`map -> <robot>/odom`).

Pure SE(2) checks plus the hold/ignore behaviour of `CameraLocalizer.update`.
No ROS 2 runtime: `swarm_perception` is on `pythonpath` via pyproject.toml, the
same way `tests/unit/test_perception.py` imports it.
"""
from __future__ import annotations

import math

import pytest
from swarm_perception.camera_localizer import (
    DEFAULT_M1_LATENCY_COMPENSATION_SEC,
    CameraLocalizer,
    compose,
    invert,
    map_to_odom,
    normalize_yaw,
    odom_lookup_stamp,
)

IDENTITY = (0.0, 0.0, 0.0)


def _scene_state(stamp: float, *robots: dict) -> dict:
    return {
        "stamp": stamp,
        "frame_id": "overhead_camera",
        "robots": list(robots),
        "diagnostics": {},
    }


def _robot(robot_id: str, x: float, y: float, theta: float, status: str = "MOVING") -> dict:
    return {
        "robot_id": robot_id,
        "x": x,
        "y": y,
        "theta": theta,
        "linear_velocity": 0.1,
        "status": status,
    }


def test_map_to_odom_is_identity_when_frames_coincide():
    assert map_to_odom(IDENTITY, IDENTITY) == pytest.approx(IDENTITY, abs=1e-9)


def test_map_to_odom_recovers_spawn_offset():
    # robot_1 spawned at (-1.5, 0, 0) and has driven 0.3 m along +x: the camera
    # sees -1.2 m in map, odometry reports 0.3 m from its spawn-relative origin.
    result = map_to_odom((-1.5 + 0.3, 0.0, 0.0), (0.3, 0.0, 0.0))

    assert result == pytest.approx((-1.5, 0.0, 0.0), abs=1e-9)


def test_map_to_odom_handles_rotated_spawn():
    # robot_2 spawned at (1.5, 0, pi) facing -x. Odometry yaw is 0 (no turn
    # since spawn) while the map yaw is pi, so the correction must carry the
    # whole rotation and still land the translation at the spawn x.
    result = map_to_odom((1.5 - 0.3, 0.0, math.pi), (0.3, 0.0, 0.0))

    assert result[0] == pytest.approx(1.5, abs=1e-9)
    assert result[1] == pytest.approx(0.0, abs=1e-9)
    assert result[2] == pytest.approx(math.pi, abs=1e-9)


def test_compose_invert_round_trip():
    pose = (1.7, -0.9, 2.3)

    assert compose(pose, invert(pose)) == pytest.approx(IDENTITY, abs=1e-9)
    assert compose(invert(pose), pose) == pytest.approx(IDENTITY, abs=1e-9)


def test_update_holds_last_transform_when_stale():
    localizer = CameraLocalizer("robot_1")
    localizer.update(_scene_state(1.0, _robot("robot_1", -1.2, 0.0, 0.0)), (0.3, 0.0, 0.0))
    first = localizer.latest

    held = localizer.update(
        _scene_state(2.0, _robot("robot_1", 99.0, 99.0, 1.0, status="STALE")),
        (0.5, 0.0, 0.0),
    )

    assert held == first
    assert localizer.updates == 1
    assert localizer.holds == 1
    assert localizer.last_update_stamp == 1.0


def test_update_returns_none_before_first_fix():
    localizer = CameraLocalizer("robot_1")

    # Robot not in frame at all.
    assert localizer.update(_scene_state(1.0), (0.0, 0.0, 0.0)) is None
    # Robot in frame but with an unusable pose field.
    unusable = _robot("robot_1", 0.0, 0.0, 0.0)
    unusable["theta"] = None
    assert localizer.update(_scene_state(2.0, unusable), (0.0, 0.0, 0.0)) is None
    # No odometry yet.
    assert localizer.update(_scene_state(3.0, _robot("robot_1", -1.2, 0.0, 0.0)), None) is None

    assert localizer.latest is None
    assert localizer.last_update_stamp is None
    assert localizer.holds == 3


def test_seeded_localizer_reports_initial_transform_before_first_fix():
    seed = (-1.5, 0.0, 0.0)
    localizer = CameraLocalizer("robot_1", initial_map_to_odom=seed)

    assert localizer.latest == seed
    assert localizer.seeded is True
    # The seed is not an update: it comes from the constructor, not a fix.
    assert localizer.updates == 0
    assert localizer.holds == 0


def test_first_fix_replaces_seed_and_clears_seeded_flag():
    seed = (-1.5, 0.0, 0.0)
    localizer = CameraLocalizer("robot_1", initial_map_to_odom=seed)

    result = localizer.update(
        _scene_state(1.0, _robot("robot_1", -1.2, 0.0, 0.0)), (0.3, 0.0, 0.0)
    )

    assert result == pytest.approx((-1.5, 0.0, 0.0), abs=1e-9)
    assert localizer.seeded is False
    assert localizer.updates == 1


def test_stale_before_first_fix_keeps_seed():
    seed = (-1.5, 0.0, 0.0)
    localizer = CameraLocalizer("robot_1", initial_map_to_odom=seed)

    held = localizer.update(
        _scene_state(1.0, _robot("robot_1", 99.0, 99.0, 1.0, status="STALE")),
        (0.3, 0.0, 0.0),
    )

    assert held == seed
    assert localizer.seeded is True
    assert localizer.updates == 0
    assert localizer.holds == 1


def test_unseeded_localizer_has_no_transform_before_first_fix():
    localizer = CameraLocalizer("robot_1")

    assert localizer.latest is None
    assert localizer.seeded is False


def test_update_ignores_other_robots():
    localizer = CameraLocalizer("robot_1")

    result = localizer.update(
        _scene_state(1.0, _robot("robot_2", 1.2, 0.0, math.pi)), (0.3, 0.0, 0.0)
    )

    assert result is None
    assert localizer.updates == 0
    assert localizer.holds == 1


def test_yaw_normalized():
    # Composition must not accumulate past a revolution, and the (-pi, pi]
    # convention keeps +pi (robot_2's spawn heading) from flipping to -pi.
    assert compose((0.0, 0.0, 2.5), (0.0, 0.0, 2.5))[2] == pytest.approx(
        5.0 - 2.0 * math.pi, abs=1e-9
    )
    assert normalize_yaw(math.pi) == pytest.approx(math.pi, abs=1e-12)
    assert normalize_yaw(-math.pi) == pytest.approx(math.pi, abs=1e-12)
    assert normalize_yaw(-3.0 * math.pi / 2.0) == pytest.approx(math.pi / 2.0, abs=1e-12)

    for yaw in (0.0, 1.0, -1.0, 4.0, -4.0, 7.5, -7.5):
        wrapped = normalize_yaw(yaw)
        assert -math.pi < wrapped <= math.pi
        # Same rotation, different representative.
        assert math.cos(wrapped) == pytest.approx(math.cos(yaw), abs=1e-9)
        assert math.sin(wrapped) == pytest.approx(math.sin(yaw), abs=1e-9)


def _stamped_robot(robot_id: str, stamp: float | None, status: str = "SLOW") -> dict:
    robot = _robot(robot_id, 0.8, 0.0, 1.15, status=status)
    if stamp is not None:
        robot["stamp"] = stamp
    return robot


def test_odom_lookup_stamp_fresh_detection_uses_scene_stamp_minus_latency():
    scene = _scene_state(123.4, _stamped_robot("robot_1", 123.4))

    assert odom_lookup_stamp(scene, "robot_1", 0.03) == pytest.approx(123.37, abs=1e-9)


def test_odom_lookup_stamp_carried_pose_uses_its_own_detection_stamp():
    # The cp_a_s42 bag at sim 123.0: marker lost since 122.767, M1 carries the
    # old pose forward (robot stamp frozen, scene stamp advancing, SLOW).
    scene = _scene_state(123.0, _stamped_robot("robot_1", 122.766666666))

    assert odom_lookup_stamp(scene, "robot_1", 0.03) == pytest.approx(122.736666666, abs=1e-9)


def test_odom_lookup_stamp_missing_robot_stamp_falls_back_to_scene_stamp():
    scene = _scene_state(50.0, _stamped_robot("robot_1", None))

    assert odom_lookup_stamp(scene, "robot_1", 0.03) == pytest.approx(49.97, abs=1e-9)


def test_odom_lookup_stamp_absent_robot_returns_none():
    scene = _scene_state(50.0, _stamped_robot("robot_2", 50.0))

    assert odom_lookup_stamp(scene, "robot_1", 0.03) is None


def test_odom_lookup_stamp_unstamped_scene_and_robot_returns_none():
    scene = {"robots": [_stamped_robot("robot_1", None)]}

    assert odom_lookup_stamp(scene, "robot_1", 0.03) is None


def test_odom_lookup_stamp_rejects_boolean_stamp():
    scene = _scene_state(50.0, _stamped_robot("robot_1", True))

    assert odom_lookup_stamp(scene, "robot_1", 0.0) == pytest.approx(50.0, abs=1e-9)


def test_odom_lookup_stamp_stale_entry_still_resolves_but_update_holds():
    # STALE is the localizer's own hold rule (`update`), not the lookup's: the
    # stamp resolves, and the update that follows holds the correction.
    scene = _scene_state(60.0, _stamped_robot("robot_1", 58.5, status="STALE"))
    localizer = CameraLocalizer("robot_1", initial_map_to_odom=(-2.4, 0.0, 0.0))

    assert odom_lookup_stamp(scene, "robot_1", 0.03) == pytest.approx(58.47, abs=1e-9)
    assert localizer.update(scene, (3.2, 0.0, 1.15)) == (-2.4, 0.0, 0.0)
    assert localizer.holds == 1


def test_odom_lookup_stamp_default_latency_is_measured_value():
    scene = _scene_state(10.0, _stamped_robot("robot_1", 10.0))

    assert odom_lookup_stamp(scene, "robot_1") == pytest.approx(
        10.0 - DEFAULT_M1_LATENCY_COMPENSATION_SEC, abs=1e-12
    )
    assert 0.0 < DEFAULT_M1_LATENCY_COMPENSATION_SEC < 0.1


def test_carried_pose_paired_at_its_stamp_reproduces_fresh_correction():
    # Drift-free odometry: the robot turns in place at 0.8 rad/s from yaw 0
    # (spawn (-2.4, 0, 0)). The fresh fix at t=1.0 and the same pose carried
    # to t=1.4 must give the same map->odom when each is paired with odometry
    # at the pose's own time; pairing the carried pose with odometry at 1.4
    # (the pre-fix latest lookup) is off by -0.8 * 0.4 = -0.32 rad.
    spawn = (-2.4, 0.0, 0.0)
    rate = 0.8

    def odom_at(t: float) -> tuple[float, float, float]:
        return (0.0, 0.0, normalize_yaw(rate * t))

    camera_pose = compose(spawn, odom_at(1.0))
    fresh = _scene_state(1.0, {**_stamped_robot("robot_1", 1.0), "x": camera_pose[0],
                               "y": camera_pose[1], "theta": camera_pose[2]})
    carried = _scene_state(1.4, {**_stamped_robot("robot_1", 1.0), "x": camera_pose[0],
                                 "y": camera_pose[1], "theta": camera_pose[2]})
    localizer = CameraLocalizer("robot_1")

    first = localizer.update(fresh, odom_at(odom_lookup_stamp(fresh, "robot_1", 0.0)))
    second = localizer.update(carried, odom_at(odom_lookup_stamp(carried, "robot_1", 0.0)))
    latest = map_to_odom(camera_pose, odom_at(1.4))

    assert first == pytest.approx(spawn, abs=1e-9)
    assert second == pytest.approx(spawn, abs=1e-9)
    assert latest[2] == pytest.approx(-0.32, abs=1e-9)

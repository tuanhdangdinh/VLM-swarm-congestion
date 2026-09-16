"""Unit tests for camera-based localization maths (`map -> <robot>/odom`).

Pure SE(2) checks plus the hold/ignore behaviour of `CameraLocalizer.update`.
No ROS 2 runtime: `swarm_perception` is on `pythonpath` via pyproject.toml, the
same way `tests/unit/test_perception.py` imports it.
"""
from __future__ import annotations

import math

import pytest
from swarm_perception.camera_localizer import (
    CameraLocalizer,
    compose,
    invert,
    map_to_odom,
    normalize_yaw,
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

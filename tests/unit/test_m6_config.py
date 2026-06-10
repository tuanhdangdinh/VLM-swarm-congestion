import math
import pytest
from pydantic import ValidationError
from isaac.vgu_sim.config import (
    Pose2D, Goal2D, RobotScenarioConfig, TimedObstacleConfig,
    ExpectedConflictConfig, ScenarioRuntimeOverrides, ScenarioConfig,
    RobotAssetConfig, CameraConfig, WarehouseConfig, ResolvedRunConfig, RunResult,
)
from pathlib import Path


VALID_HEAD_ON = {
    "schema_version": 1,
    "name": "head_on_deadlock",
    "seed": 42,
    "duration_sec": 45.0,
    "robots": [
        {"robot_id": "robot_1", "marker_id": 1,
         "spawn": {"x": -4.5, "y": 0.0, "yaw_rad": 0.0},
         "goal": {"x": 4.5, "y": 0.0}, "initial_task": "cross_narrow_aisle"},
        {"robot_id": "robot_2", "marker_id": 2,
         "spawn": {"x": 4.5, "y": 0.0, "yaw_rad": math.pi},
         "goal": {"x": -4.5, "y": 0.0}, "initial_task": "cross_narrow_aisle"},
    ],
    "timed_obstacles": [],
    "expected_conflict": {
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2"],
        "onset_window_sec": [8.0, 25.0],
        "min_duration_sec": 2.0,
    },
    "runtime": {"physics_hz": 60, "rendering_hz": 30},
}


def test_valid_head_on_parses():
    cfg = ScenarioConfig.model_validate(VALID_HEAD_ON)
    assert cfg.name == "head_on_deadlock"
    assert cfg.seed == 42
    assert len(cfg.robots) == 2


def test_invalid_robot_id_format_rejected():
    bad = {**VALID_HEAD_ON, "robots": [
        {**VALID_HEAD_ON["robots"][0], "robot_id": "bot_1"},
        VALID_HEAD_ON["robots"][1],
    ]}
    with pytest.raises(ValidationError, match="robot_id"):
        ScenarioConfig.model_validate(bad)


def test_duplicate_robot_ids_rejected():
    bad = {**VALID_HEAD_ON, "robots": [
        VALID_HEAD_ON["robots"][0],
        {**VALID_HEAD_ON["robots"][1], "robot_id": "robot_1"},
    ]}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate(bad)


def test_duplicate_marker_ids_rejected():
    bad = {**VALID_HEAD_ON, "robots": [
        VALID_HEAD_ON["robots"][0],
        {**VALID_HEAD_ON["robots"][1], "marker_id": 1},
    ]}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate(bad)


def test_marker_id_must_match_robot_number():
    bad = {**VALID_HEAD_ON, "robots": [
        {**VALID_HEAD_ON["robots"][0], "marker_id": 5},
        VALID_HEAD_ON["robots"][1],
    ]}
    with pytest.raises(ValidationError, match="marker_id"):
        ScenarioConfig.model_validate(bad)


def test_negative_seed_rejected():
    with pytest.raises(ValidationError, match="seed"):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "seed": -1})


def test_onset_window_outside_duration_rejected():
    bad_conflict = {**VALID_HEAD_ON["expected_conflict"],
                    "onset_window_sec": [30.0, 50.0]}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "expected_conflict": bad_conflict})


def test_onset_window_must_be_increasing():
    bad_conflict = {**VALID_HEAD_ON["expected_conflict"],
                    "onset_window_sec": [20.0, 10.0]}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "expected_conflict": bad_conflict})


def test_timed_obstacle_remove_before_spawn_rejected():
    obstacle = {"obstacle_id": "obs_1", "asset": "dynamic_obstacle.usd",
                "spawn_at_sec": 10.0, "remove_at_sec": 5.0,
                "pose": {"x": 1.5, "y": 0.0, "yaw_rad": 0.0}}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "timed_obstacles": [obstacle]})


def test_marker_id_out_of_range_rejected():
    bad = {**VALID_HEAD_ON, "robots": [
        {**VALID_HEAD_ON["robots"][0], "marker_id": 50},
        VALID_HEAD_ON["robots"][1],
    ]}
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate(bad)


def test_camera_config_defaults():
    cam = CameraConfig()
    assert cam.width == 1280
    assert cam.height == 960
    assert cam.focal_length_mm == pytest.approx(10.48)
    assert cam.horizontal_aperture_mm == pytest.approx(20.955)
    assert cam.vertical_aperture_mm == pytest.approx(15.716)
    assert cam.orientation_quat_wxyz == (1.0, 0.0, 0.0, 0.0)


def test_robot_asset_config_defaults():
    r = RobotAssetConfig()
    assert r.wheel_radius_m == pytest.approx(0.033)
    assert r.wheel_separation_m == pytest.approx(0.160)
    assert r.max_linear_velocity_mps == pytest.approx(0.22)


def test_scenario_config_is_frozen():
    cfg = ScenarioConfig.model_validate(VALID_HEAD_ON)
    with pytest.raises(Exception):
        cfg.seed = 99

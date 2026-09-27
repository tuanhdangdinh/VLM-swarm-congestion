import json
import math

import pytest
import yaml
from pydantic import ValidationError

from isaac.vgu_sim.config import (
    CameraConfig,
    ObstacleSize,
    OracleConfig,
    RobotAssetConfig,
    ScenarioConfig,
)
from isaac.vgu_sim.paths import scenario_config_path

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
    with pytest.raises(ValidationError):
        cfg.seed = 99


def _load_scenario(name: str) -> ScenarioConfig:
    path = scenario_config_path(name)
    with open(path) as f:
        data = yaml.safe_load(f)
    return ScenarioConfig.model_validate(data)


def test_head_on_yaml_round_trip():
    cfg = _load_scenario("head_on_deadlock")
    assert cfg.name == "head_on_deadlock"
    assert len(cfg.robots) == 2
    assert cfg.robots[0].robot_id == "robot_1"
    assert cfg.robots[1].robot_id == "robot_2"
    assert cfg.aisle_barrier is not None
    assert cfg.aisle_barrier.effective_width_m == pytest.approx(0.4)
    assert cfg.aisle_barrier.length_m == pytest.approx(0.9)
    assert cfg.expected_conflict.type == "deadlock"


def test_head_on_goals_stay_inside_camera_roi():
    # +-3.0 is exactly the camera ROI edge (roi_width_m: 6.0), so a marker at
    # its goal is half off-frame and undetectable by M1; +-2.5 keeps 0.5 m of
    # margin (~107 px at 1280 px / 6.0 m).
    cfg = _load_scenario("head_on_deadlock")

    assert (cfg.robots[0].goal.x, cfg.robots[0].goal.y) == pytest.approx((2.5, 0.0))
    assert (cfg.robots[1].goal.x, cfg.robots[1].goal.y) == pytest.approx((-2.5, 0.0))


def test_intersection_yaml_round_trip():
    cfg = _load_scenario("intersection_bottleneck")
    assert cfg.name == "intersection_bottleneck"
    assert len(cfg.robots) == 4
    assert cfg.expected_conflict.type == "bottleneck"


def test_dynamic_anomaly_yaml_round_trip():
    cfg = _load_scenario("dynamic_anomaly")
    assert cfg.name == "dynamic_anomaly"
    assert len(cfg.robots) == 4
    assert len(cfg.timed_obstacles) == 1
    obs = cfg.timed_obstacles[0]
    assert obs.spawn_at_sec == pytest.approx(8.0)
    assert obs.remove_at_sec == pytest.approx(20.0)
    assert cfg.expected_conflict.type == "anomaly"


def test_robot_yaml_matches_defaults():
    with open("isaac/config/robot.yaml") as f:
        data = yaml.safe_load(f)
    r = RobotAssetConfig.model_validate(data)
    assert r.wheel_radius_m == pytest.approx(0.033)
    assert r.wheel_separation_m == pytest.approx(0.160)
    assert r.max_linear_velocity_mps == pytest.approx(0.22)


def test_lidar_json_has_required_keys():
    with open("isaac/config/lidar/turtlebot3_lds_01.json") as f:
        d = json.load(f)
    assert d["numChannels"] == 1
    assert d["horizontalFov"] == pytest.approx(360.0)
    assert d["rotationRate"] == pytest.approx(10.0)
    assert d["minRange"] == pytest.approx(0.12)
    assert d["maxRange"] == pytest.approx(3.5)


def test_legacy_name_infers_family():
    cfg = ScenarioConfig.model_validate(VALID_HEAD_ON)
    assert cfg.family == "head_on"


def test_explicit_family_accepted_for_generated_name():
    cfg = ScenarioConfig.model_validate(
        {**VALID_HEAD_ON, "name": "head_on_asymmetric_w0p2_eopen_o0", "family": "head_on"}
    )
    assert cfg.family == "head_on"


def test_generated_name_without_family_rejected():
    with pytest.raises(ValidationError, match="family is required"):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "name": "head_on_asymmetric_x"})


def test_name_with_uppercase_or_dash_rejected():
    with pytest.raises(ValidationError):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "name": "Head-On", "family": "head_on"})


def test_static_obstacle_parses_with_default_size():
    cfg = ScenarioConfig.model_validate({**VALID_HEAD_ON, "static_obstacles": [
        {"obstacle_id": "blocker_west", "pose": {"x": -1.85, "y": 0.0, "yaw_rad": 0.0}}]})
    assert cfg.static_obstacles[0].size.x_m == pytest.approx(0.3)
    assert cfg.static_obstacles[0].size.z_m == pytest.approx(0.5)


def test_timed_obstacle_size_defaults():
    cfg = ScenarioConfig.model_validate({**VALID_HEAD_ON, "timed_obstacles": [
        {"obstacle_id": "box", "asset": "dynamic_obstacle", "spawn_at_sec": 1.0,
         "pose": {"x": 0.0, "y": 0.0, "yaw_rad": 0.0}}]})
    assert cfg.timed_obstacles[0].size.y_m == pytest.approx(0.3)


def test_obstacle_size_must_be_positive():
    with pytest.raises(ValidationError):
        ObstacleSize(x_m=0.0)


def test_duplicate_obstacle_id_across_static_and_timed_rejected():
    static_obstacle = {"obstacle_id": "box", "pose": {"x": 0.0, "y": 0.0, "yaw_rad": 0.0}}
    timed_obstacle = {
        "obstacle_id": "box", "asset": "dynamic_obstacle", "spawn_at_sec": 1.0,
        "pose": {"x": 0.0, "y": 0.0, "yaw_rad": 0.0},
    }
    with pytest.raises(ValidationError, match="obstacle_id"):
        ScenarioConfig.model_validate({
            **VALID_HEAD_ON,
            "static_obstacles": [static_obstacle],
            "timed_obstacles": [timed_obstacle],
        })


def test_oracle_with_unknown_robot_rejected():
    with pytest.raises(ValidationError, match="robot_9"):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "oracle": {
            "correct_yielder": "robot_9", "fcfs_yielder": "robot_1",
            "feasible_yielders": ["robot_9"], "rationale": "x"}})


def test_oracle_feasible_yielders_must_contain_correct_yielder():
    with pytest.raises(ValidationError):
        OracleConfig(correct_yielder="robot_2", fcfs_yielder="robot_1",
                     feasible_yielders=("robot_1",), rationale="x")


def test_oracle_contrasts_fcfs_when_yielders_differ():
    oracle = OracleConfig(correct_yielder="robot_2", fcfs_yielder="robot_1",
                          feasible_yielders=("robot_2",), rationale="x")
    assert oracle.contrasts_fcfs is True


def test_parameters_round_trip_through_json_dump():
    cfg = ScenarioConfig.model_validate({**VALID_HEAD_ON, "parameters": {
        "blocker_west_m": 0.2, "blocker_east_m": None, "arrival_offset_m": 0.0}})
    again = ScenarioConfig.model_validate(cfg.model_dump(mode="json"))
    assert again == cfg


def _normal_flow_dict() -> dict:
    return {**VALID_HEAD_ON, "name": "normal_flow", "family": "normal_flow",
            "expected_conflict": None}


def test_normal_flow_family_accepts_null_expected_conflict():
    cfg = ScenarioConfig.model_validate(_normal_flow_dict())
    assert cfg.family == "normal_flow"
    assert cfg.expected_conflict is None


def test_expected_conflict_key_still_required_when_omitted():
    data = _normal_flow_dict()
    del data["expected_conflict"]
    with pytest.raises(ValidationError, match="expected_conflict"):
        ScenarioConfig.model_validate(data)


def test_null_expected_conflict_rejected_for_conflict_family():
    with pytest.raises(ValidationError, match="expected_conflict"):
        ScenarioConfig.model_validate({**VALID_HEAD_ON, "expected_conflict": None})


def test_normal_flow_family_rejects_expected_conflict_block():
    with pytest.raises(ValidationError, match="normal_flow"):
        ScenarioConfig.model_validate(
            {**_normal_flow_dict(), "expected_conflict": VALID_HEAD_ON["expected_conflict"]}
        )

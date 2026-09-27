"""Tests for the T3c v2 `dynamic_anomaly_v2` scenario and its Nav2 map."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, load_scenario
from isaac.vgu_sim.config import CameraConfig, WarehouseConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = REPO_ROOT / "isaac/config/scenarios/dynamic_anomaly_v2.yaml"
NORMAL_FLOW_PATH = REPO_ROOT / "isaac/config/scenarios/normal_flow.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCHESTRATOR_YAML = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
RESOLUTION_M = 0.05
# TurtleBot3 Burger nav2 footprint width (+-0.09 m).
ROBOT_WIDTH_M = 0.18
# Transit speed and departure time measured on the normal_flow T0 run
# 20260927_111348 (same lanes): the basis of the scenario's timing.
TRANSIT_MPS = 0.15
DEPARTURE_SIM_SEC = 10.6
M5_FIRST_SCENE_SIM_SEC = 12.0


def _cell_at(grid, cfg: WarehouseConfig, x: float, y: float) -> int:
    col = round((x + cfg.width_m / 2) / RESOLUTION_M)
    row = round((cfg.depth_m / 2 - y) / RESOLUTION_M)
    return int(grid[row, col])


def _scenario_grid():
    scenario = load_scenario(SCENARIO_PATH)
    grid, _ = build_occupancy_grid(
        WarehouseConfig(),
        obstacles=[],
        resolution_m=RESOLUTION_M,
        aisle_barrier=scenario.aisle_barrier,
        static_obstacles=scenario.static_obstacles,
    )
    return grid


def _obstacle():
    (obstacle,) = load_scenario(SCENARIO_PATH).timed_obstacles
    return obstacle


def _robot(robot_id: str):
    return next(r for r in load_scenario(SCENARIO_PATH).robots if r.robot_id == robot_id)


def _x_at(robot, sim_sec: float) -> float:
    direction = np.sign(robot.goal.x - robot.spawn.x)
    return robot.spawn.x + direction * TRANSIT_MPS * max(0.0, sim_sec - DEPARTURE_SIM_SEC)


def test_dynamic_anomaly_v2_yaml_loads_and_validates():
    scenario = load_scenario(SCENARIO_PATH)

    assert scenario.name == "dynamic_anomaly_v2"
    assert scenario.family == "dynamic_anomaly"
    assert [r.robot_id for r in scenario.robots] == ["robot_1", "robot_2"]


def test_dynamic_anomaly_v2_expects_anomaly_on_robot_1():
    conflict = load_scenario(SCENARIO_PATH).expected_conflict

    assert conflict.type == "anomaly"
    assert conflict.involved_robots == ("robot_1",)


def test_dynamic_anomaly_v2_has_no_oracle_yet():
    # The anomaly/transient answer key waits on prompt-v2's blocker_kind field.
    assert load_scenario(SCENARIO_PATH).oracle is None


def test_dynamic_anomaly_v2_has_only_one_timed_obstacle():
    scenario = load_scenario(SCENARIO_PATH)

    assert scenario.aisle_barrier is None
    assert scenario.static_obstacles == ()
    assert len(scenario.timed_obstacles) == 1


def test_dynamic_anomaly_v2_reuses_normal_flow_lanes():
    ours = load_scenario(SCENARIO_PATH).robots
    theirs = load_scenario(NORMAL_FLOW_PATH).robots

    assert [(r.spawn, r.goal) for r in ours] == [(r.spawn, r.goal) for r in theirs]


def test_dynamic_anomaly_v2_spawns_and_goals_inside_camera_roi_with_margin():
    camera = CameraConfig()
    half_x, half_y = camera.roi_width_m / 2 - 0.5, camera.roi_depth_m / 2 - 0.5

    for robot in load_scenario(SCENARIO_PATH).robots:
        for x, y in ((robot.spawn.x, robot.spawn.y), (robot.goal.x, robot.goal.y)):
            assert abs(x) <= half_x and abs(y) <= half_y, (robot.robot_id, x, y)


def test_dynamic_anomaly_v2_obstacle_inside_camera_roi():
    camera = CameraConfig()
    obs = _obstacle()

    assert abs(obs.pose.x) + obs.size.x_m / 2 <= camera.roi_width_m / 2
    assert abs(obs.pose.y) + obs.size.y_m / 2 <= camera.roi_depth_m / 2


def test_dynamic_anomaly_v2_obstacle_covers_robot_1_lane_between_spawn_and_goal():
    obs, r1 = _obstacle(), _robot("robot_1")

    assert obs.pose.y - obs.size.y_m / 2 <= r1.spawn.y <= obs.pose.y + obs.size.y_m / 2
    assert r1.spawn.x < obs.pose.x - obs.size.x_m / 2
    assert obs.pose.x + obs.size.x_m / 2 < r1.goal.x


def test_dynamic_anomaly_v2_obstacle_centre_is_off_axis_on_robot_1_side():
    obs, r1 = _obstacle(), _robot("robot_1")

    assert obs.pose.y != 0.0
    assert np.sign(obs.pose.y) == np.sign(r1.spawn.y)


def test_dynamic_anomaly_v2_obstacle_leaves_no_detour_for_the_robot():
    # A passable gap lets Nav2's scan-fed costmaps replan around the box, so
    # robot_1 never stalls and M5 never triggers an analysis.
    obs = _obstacle()
    aisle_half = WarehouseConfig().nominal_aisle_width_m / 2
    north_gap = aisle_half - (obs.pose.y + obs.size.y_m / 2)
    south_gap = (obs.pose.y - obs.size.y_m / 2) + aisle_half

    assert max(north_gap, south_gap) < ROBOT_WIDTH_M


def test_dynamic_anomaly_v2_window_opens_after_m5_startup():
    assert _obstacle().spawn_at_sec > M5_FIRST_SCENE_SIM_SEC


def test_dynamic_anomaly_v2_robot_2_has_cleared_obstacle_before_spawn():
    obs, r2 = _obstacle(), _robot("robot_2")

    assert _x_at(r2, obs.spawn_at_sec) < obs.pose.x - obs.size.x_m / 2


def test_dynamic_anomaly_v2_robot_1_reaches_obstacle_while_active():
    obs, r1 = _obstacle(), _robot("robot_1")
    west_face = obs.pose.x - obs.size.x_m / 2

    # Not yet at the face when it spawns (no spawning into the robot) ...
    assert _x_at(r1, obs.spawn_at_sec) < west_face - 0.5
    # ... and would reach it long before it is removed.
    arrival = DEPARTURE_SIM_SEC + (west_face - r1.spawn.x) / TRANSIT_MPS
    assert arrival < obs.remove_at_sec


def test_dynamic_anomaly_v2_leaves_time_to_resolve_after_removal():
    scenario = load_scenario(SCENARIO_PATH)
    obs, r1 = _obstacle(), _robot("robot_1")
    remaining = r1.goal.x - (obs.pose.x - obs.size.x_m / 2)

    assert obs.remove_at_sec + remaining / TRANSIT_MPS + 30.0 <= scenario.duration_sec


def test_dynamic_anomaly_v2_onset_window_spans_spawn_and_stall_trigger():
    scenario = load_scenario(SCENARIO_PATH)
    start, end = scenario.expected_conflict.onset_window_sec
    stall_threshold = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["stall_threshold_sec"]

    assert start == pytest.approx(_obstacle().spawn_at_sec)
    assert end >= start + stall_threshold
    assert end <= _obstacle().remove_at_sec


def test_dynamic_anomaly_v2_lanes_are_free_in_generated_map():
    cfg = WarehouseConfig()
    grid = _scenario_grid()

    for robot in load_scenario(SCENARIO_PATH).robots:
        lo, hi = sorted((robot.spawn.x, robot.goal.x))
        for x in np.arange(lo, hi + 1e-9, RESOLUTION_M):
            assert _cell_at(grid, cfg, x, robot.spawn.y) == 255, (robot.robot_id, x)


def test_dynamic_anomaly_v2_obstacle_is_not_baked_into_map():
    cfg = WarehouseConfig()
    obs = _obstacle()

    assert _cell_at(_scenario_grid(), cfg, obs.pose.x, obs.pose.y) == 255


def test_dynamic_anomaly_v2_map_equals_default_map():
    base, _ = build_occupancy_grid(WarehouseConfig(), obstacles=[], resolution_m=RESOLUTION_M)

    assert np.array_equal(base, _scenario_grid())


def test_committed_dynamic_anomaly_v2_map_matches_scenario_yaml():
    map_yaml = MAPS_DIR / "warehouse_map_dynamic_anomaly_v2.yaml"
    data = yaml.safe_load(map_yaml.read_text())
    committed = np.flipud(np.array(Image.open(map_yaml.parent / data["image"])))

    assert data["image"] == "warehouse_map_dynamic_anomaly_v2.pgm"
    assert data["resolution"] == pytest.approx(RESOLUTION_M)
    assert data["origin"][:2] == [-6.0, -4.0]
    assert np.array_equal(committed, _scenario_grid())

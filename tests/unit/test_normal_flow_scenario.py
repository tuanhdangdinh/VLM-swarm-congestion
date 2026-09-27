"""Tests for the T0 negative-control `normal_flow` scenario and its Nav2 map."""
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
SCENARIO_PATH = REPO_ROOT / "isaac/config/scenarios/normal_flow.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
# M4's pairwise safety latch (swarm_execution/config/safety.yaml min_distance_m).
M4_LATCH_M = 0.45
# Required clearance above the latch so ordinary DWB lane drift cannot trip it.
LATCH_MARGIN_M = 0.2
# Robot half-width (nav2 footprint +-0.09 m) plus global inflation_radius 0.10 m:
# a lane closer than this to a rack face sits in a nonzero-cost band, and NavFn
# would pull both paths toward the aisle centreline -- the head-on conflict.
ZERO_COST_CLEARANCE_M = 0.09 + 0.10
RESOLUTION_M = 0.05


def _cell_at(grid, cfg: WarehouseConfig, x: float, y: float) -> int:
    col = round((x + cfg.width_m / 2) / RESOLUTION_M)
    row = round((cfg.depth_m / 2 - y) / RESOLUTION_M)
    return int(grid[row, col])


def test_normal_flow_yaml_loads_and_validates():
    scenario = load_scenario(SCENARIO_PATH)

    assert scenario.name == "normal_flow"
    assert scenario.family == "normal_flow"
    assert scenario.expected_conflict is None
    assert [r.robot_id for r in scenario.robots] == ["robot_1", "robot_2"]


def test_normal_flow_has_no_barrier_or_obstacles():
    scenario = load_scenario(SCENARIO_PATH)

    assert scenario.aisle_barrier is None
    assert scenario.static_obstacles == ()
    assert scenario.timed_obstacles == ()


def test_normal_flow_robots_stay_in_their_own_lane():
    scenario = load_scenario(SCENARIO_PATH)

    for robot in scenario.robots:
        assert robot.spawn.y == pytest.approx(robot.goal.y), robot.robot_id


def test_normal_flow_robots_travel_in_opposite_directions():
    r1, r2 = load_scenario(SCENARIO_PATH).robots

    assert np.sign(r1.goal.x - r1.spawn.x) == -np.sign(r2.goal.x - r2.spawn.x)


def test_normal_flow_lane_separation_clears_m4_latch_with_margin():
    r1, r2 = load_scenario(SCENARIO_PATH).robots

    # Both lanes run along x, so their lateral offset is a lower bound on the
    # pairwise distance at every instant of a lane-following traversal.
    assert abs(r1.spawn.y - r2.spawn.y) >= M4_LATCH_M + LATCH_MARGIN_M


def test_normal_flow_lanes_sit_in_zero_cost_aisle_band():
    scenario = load_scenario(SCENARIO_PATH)
    aisle_half_width = WarehouseConfig().nominal_aisle_width_m / 2

    for robot in scenario.robots:
        assert abs(robot.spawn.y) + ZERO_COST_CLEARANCE_M <= aisle_half_width, robot.robot_id


def test_normal_flow_spawns_and_goals_inside_camera_roi_with_margin():
    camera = CameraConfig()
    half_x, half_y = camera.roi_width_m / 2 - 0.5, camera.roi_depth_m / 2 - 0.5

    for robot in load_scenario(SCENARIO_PATH).robots:
        for x, y in ((robot.spawn.x, robot.spawn.y), (robot.goal.x, robot.goal.y)):
            assert abs(x) <= half_x and abs(y) <= half_y, (robot.robot_id, x, y)


def test_normal_flow_lanes_are_free_in_generated_map():
    cfg = WarehouseConfig()
    scenario = load_scenario(SCENARIO_PATH)
    grid, _ = build_occupancy_grid(
        cfg,
        obstacles=[],
        resolution_m=RESOLUTION_M,
        aisle_barrier=scenario.aisle_barrier,
        static_obstacles=scenario.static_obstacles,
    )

    for robot in scenario.robots:
        lo, hi = sorted((robot.spawn.x, robot.goal.x))
        for x in np.arange(lo, hi + 1e-9, RESOLUTION_M):
            for dy in (-ZERO_COST_CLEARANCE_M, 0.0, ZERO_COST_CLEARANCE_M):
                y = robot.spawn.y + dy
                assert _cell_at(grid, cfg, x, y) == 255, (robot.robot_id, x, y)


def test_normal_flow_map_equals_default_map():
    cfg = WarehouseConfig()
    scenario = load_scenario(SCENARIO_PATH)
    base, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=RESOLUTION_M)
    generated, _ = build_occupancy_grid(
        cfg,
        obstacles=[],
        resolution_m=RESOLUTION_M,
        aisle_barrier=scenario.aisle_barrier,
        static_obstacles=scenario.static_obstacles,
    )

    assert np.array_equal(base, generated)


def test_committed_normal_flow_map_matches_scenario_yaml():
    cfg = WarehouseConfig()
    scenario = load_scenario(SCENARIO_PATH)
    expected, _ = build_occupancy_grid(
        cfg,
        obstacles=[],
        resolution_m=RESOLUTION_M,
        aisle_barrier=scenario.aisle_barrier,
        static_obstacles=scenario.static_obstacles,
    )
    map_yaml = MAPS_DIR / "warehouse_map_normal_flow.yaml"
    data = yaml.safe_load(map_yaml.read_text())
    committed = np.flipud(np.array(Image.open(map_yaml.parent / data["image"])))

    assert data["resolution"] == pytest.approx(RESOLUTION_M)
    assert data["origin"][:2] == [-6.0, -4.0]
    assert np.array_equal(committed, expected)

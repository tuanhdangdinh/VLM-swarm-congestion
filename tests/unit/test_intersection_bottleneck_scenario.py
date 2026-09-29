"""Tests for the T1 four-way scenario `intersection_bottleneck` (2026-09-29 audit).

Pins the light fixes of the modern-apparatus audit (tracked band on both axes,
equal approach radii, free floor, per-scenario map, run length, Arm B's mapped
zone and the smoke's mock), and the structural defect the audit predicted for
the single-yield grounding at a four-way standoff.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from swarm_orchestrator.shadow_classical import find_censored_arrivals

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, load_scenario
from isaac.vgu_sim.config import WarehouseConfig
from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path
from reasoning.baselines.classical_reasoner import (
    ConflictZone,
    classify_scene,
    load_classical_params,
    resolve_classical,
)
from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.maneuver_geometry import load_grounding_params
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)
from reasoning.vlm.output_parser import parse_decision_text

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = REPO_ROOT / "isaac/config/scenarios/intersection_bottleneck.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCHESTRATOR_YAML = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
CALIBRATION_YAML = REPO_ROOT / "ros2_ws/src/swarm_perception/config/calibration.yaml"
MOCK_PATH = REPO_ROOT / "config/mock_decisions/intersection_yield_once.json"
SKIP_MOCK_PATH = REPO_ROOT / "config/mock_decisions/intersection_skip_then_yield_once.json"
RESOLUTION_M = 0.05

# Verified M1 tracking extent on x (head-on family goals at +-2.5; +-3.0 gave
# 0/146 detections); the same inset from the homography edge is applied on y.
VERIFIED_TRACKED_ABS_X_M = 2.5
# M4 safety (swarm_execution config/safety.yaml), centre to centre.
LATCH_M = 0.45
# M1's position bias near the ROI edge (arrival notes: ~0.1 m).
M1_BIAS_M = 0.1
# Robot half-width (nav2 footprint) plus global inflation_radius: the band
# around a lane that must be free floor for NavFn to keep it straight.
ZERO_COST_CLEARANCE_M = 0.09 + 0.10
# Transit speed and the M5 stall latency window of the synthetic buffer.
SPEED_MPS = 0.15
ZONE = {"zone_id": "crossing_1", "x": 0.0, "y": 0.0, "radius_m": 1.5}


def _scenario():
    return load_scenario(SCENARIO_PATH)


def _homography_edges() -> tuple[float, float]:
    data = yaml.safe_load(CALIBRATION_YAML.read_text())
    h = np.array(data["homography"])
    width, height = data["image_size"]
    corners = [h @ np.array([u, v, 1.0]) for u in (0, width) for v in (0, height)]
    return (
        min(abs(c[0] / c[2]) for c in corners),
        min(abs(c[1] / c[2]) for c in corners),
    )


def _tracked_band() -> tuple[float, float]:
    edge_x, edge_y = _homography_edges()
    inset = edge_x - VERIFIED_TRACKED_ABS_X_M
    return edge_x - inset, edge_y - inset


def _cell(grid, cfg: WarehouseConfig, x: float, y: float) -> int:
    col = round((x + cfg.width_m / 2) / RESOLUTION_M)
    row = round((cfg.depth_m / 2 - y) / RESOLUTION_M)
    return int(grid[row, col])


def _buffer(standoff_m: float, lags: dict[str, float], window_sec: float = 60.0):
    """Ring-buffer frames from spawn to a four-way standoff `standoff_m` out."""
    scenario = _scenario()
    frames = []
    for step in range(int(window_sec / 0.25) + 1):
        t = step * 0.25
        robots = []
        for robot in scenario.robots:
            sx, sy = robot.spawn.x, robot.spawn.y
            length = math.hypot(robot.goal.x - sx, robot.goal.y - sy)
            ux, uy = (robot.goal.x - sx) / length, (robot.goal.y - sy) / length
            run = math.hypot(sx, sy) - standoff_m
            travel = min(max(0.0, (t - lags[robot.robot_id]) * SPEED_MPS), run)
            moving = 0.0 < travel < run
            robots.append(RobotStateInput(
                robot_id=robot.robot_id, x=sx + ux * travel, y=sy + uy * travel,
                theta=robot.spawn.yaw_rad, linear_velocity=SPEED_MPS if moving else 0.0,
                status="MOVING" if moving else "STOPPED", goal=(robot.goal.x, robot.goal.y),
            ))
        frames.append(SnapshotFrame(stamp=t, robots=robots))
    return frames


LAG_CASES = (
    {"robot_1": 0.0, "robot_2": 0.0, "robot_3": 0.0, "robot_4": 0.0},
    {"robot_1": 0.0, "robot_2": 0.4, "robot_3": 0.8, "robot_4": 1.2},
    {"robot_1": 2.0, "robot_2": 1.5, "robot_3": 0.5, "robot_4": 0.0},
)
STANDOFFS_M = (0.3, 0.4, 0.5)


class TestScenario:
    def test_family_is_declared_intersection(self):
        assert "family: intersection" in SCENARIO_PATH.read_text()
        assert _scenario().family == "intersection"

    def test_four_robots_with_matching_markers(self):
        assert [(r.robot_id, r.marker_id) for r in _scenario().robots] == [
            ("robot_1", 1), ("robot_2", 2), ("robot_3", 3), ("robot_4", 4),
        ]

    def test_marker_assets_exist_for_every_robot(self):
        dictionary = aruco_dict_name(REPO_ROOT / "ros2_ws/src/swarm_perception/config/aruco.yaml")
        for robot in _scenario().robots:
            assert marker_png_path(dictionary, robot.marker_id).is_file(), robot.robot_id

    def test_t1_carries_no_oracle_and_no_scene_objects(self):
        scenario = _scenario()
        assert scenario.oracle is None
        assert scenario.aisle_barrier is None
        assert scenario.static_obstacles == ()
        assert scenario.timed_obstacles == ()

    def test_expected_conflict_is_a_four_robot_bottleneck(self):
        conflict = _scenario().expected_conflict
        assert conflict.type == "bottleneck"
        assert conflict.involved_robots == ("robot_1", "robot_2", "robot_3", "robot_4")

    def test_duration_covers_a_three_passer_yield(self):
        # Onset window end, plus ~80 sim-s of 0.1 m/s escorts and the backup,
        # plus the final Nav2 legs; the June value (60 s) ended mid-approach.
        scenario = _scenario()
        assert scenario.duration_sec >= scenario.expected_conflict.onset_window_sec[1] + 200.0


class TestTrackedBand:
    def test_band_is_derived_from_the_calibration_homography(self):
        edge_x, edge_y = _homography_edges()
        assert edge_x == pytest.approx(2.789, abs=1e-3)
        assert edge_y == pytest.approx(2.092, abs=1e-3)
        assert _tracked_band()[1] == pytest.approx(1.803, abs=1e-3)

    def test_every_spawn_and_goal_is_inside_the_tracked_band(self):
        band_x, band_y = _tracked_band()
        for robot in _scenario().robots:
            for x, y in ((robot.spawn.x, robot.spawn.y), (robot.goal.x, robot.goal.y)):
                assert abs(x) <= band_x and abs(y) <= band_y, (robot.robot_id, x, y)

    def test_approach_radii_are_equal(self):
        radii = {round(math.hypot(r.spawn.x, r.spawn.y), 6) for r in _scenario().robots}
        assert radii == {1.75}

    def test_each_goal_is_the_opposite_arm(self):
        for robot in _scenario().robots:
            assert (robot.goal.x, robot.goal.y) == pytest.approx((-robot.spawn.x, -robot.spawn.y))

    def test_each_robot_faces_its_goal(self):
        for robot in _scenario().robots:
            bearing = math.atan2(robot.goal.y - robot.spawn.y, robot.goal.x - robot.spawn.x)
            assert math.cos(bearing - robot.spawn.yaw_rad) == pytest.approx(1.0)


class TestMap:
    def test_committed_map_matches_scenario_and_default(self):
        scenario = _scenario()
        map_yaml = MAPS_DIR / f"warehouse_map_{scenario.name}.yaml"
        data = yaml.safe_load(map_yaml.read_text())
        committed = np.flipud(np.array(Image.open(map_yaml.parent / data["image"])))
        grid, _ = build_occupancy_grid(
            WarehouseConfig(), obstacles=[], resolution_m=RESOLUTION_M,
            aisle_barrier=scenario.aisle_barrier, static_obstacles=scenario.static_obstacles,
        )
        default = np.flipud(np.array(Image.open(MAPS_DIR / "warehouse_map.pgm")))
        assert data["image"] == f"warehouse_map_{scenario.name}.pgm"
        assert data["origin"][:2] == [-6.0, -4.0]
        assert np.array_equal(committed, grid)
        assert np.array_equal(committed, default)

    def test_every_lane_is_free_floor_with_zero_cost_margin(self):
        cfg = WarehouseConfig()
        grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=RESOLUTION_M)
        for robot in _scenario().robots:
            sx, sy, gx, gy = robot.spawn.x, robot.spawn.y, robot.goal.x, robot.goal.y
            steps = int(round(math.hypot(gx - sx, gy - sy) / RESOLUTION_M))
            for i in range(steps + 1):
                x, y = sx + (gx - sx) * i / steps, sy + (gy - sy) * i / steps
                for d in (-ZERO_COST_CLEARANCE_M, 0.0, ZERO_COST_CLEARANCE_M):
                    px, py = (x, y + d) if sy == gy else (x + d, y)
                    assert _cell(grid, cfg, px, py) == 255, (robot.robot_id, px, py)

    def test_the_arms_are_walled_by_racks(self):
        # Rack blocks fill the quadrants: 0.7 m off any lane is occupied.
        cfg = WarehouseConfig()
        grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=RESOLUTION_M)
        for x, y in ((1.2, 0.7), (-1.2, -0.7), (0.7, 1.2), (-0.7, -1.2)):
            assert _cell(grid, cfg, x, y) == 0, (x, y)


class TestArmBZone:
    def _zone(self) -> ConflictZone:
        return ConflictZone(**ZONE)

    def test_goal_table_declares_the_zone_and_the_four_goals(self):
        table = ORCHESTRATOR_YAML.read_text()
        assert "intersection_bottleneck (T1, four robots)" in table
        assert "{ zone_id: crossing_1, x: 0.0, y: 0.0, radius_m: 1.5 }" in table
        for robot in _scenario().robots:
            assert f"[{robot.goal.x}, {robot.goal.y}]" in table, robot.robot_id

    def test_shipped_zone_list_stays_empty(self):
        assert yaml.safe_load(ORCHESTRATOR_YAML.read_text())["shadow_classical_zones"] == []

    def test_zone_radius_is_the_membership_radius(self):
        # Membership uses r_conflict_m; FCFS arrival uses zone.radius_m. Equal
        # radii keep every classified robot inside the FCFS zone.
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        assert self._zone().radius_m == params.r_conflict_m

    def test_spawns_sit_outside_the_zone_beyond_m1_bias(self):
        zone = self._zone()
        for robot in _scenario().robots:
            spawn_r = math.hypot(robot.spawn.x - zone.x, robot.spawn.y - zone.y)
            assert spawn_r - M1_BIAS_M > zone.radius_m, robot.robot_id

    @pytest.mark.parametrize("standoff_m", STANDOFFS_M)
    @pytest.mark.parametrize("lags", LAG_CASES)
    def test_standoff_classifies_intersection_without_censoring(self, standoff_m, lags):
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        frames = _buffer(standoff_m, lags)
        resolution = resolve_classical(frames, [self._zone()], params)
        assert resolution.classification.scenario == "intersection"
        assert resolution.classification.involved_robots == [
            "robot_1", "robot_2", "robot_3", "robot_4",
        ]
        assert find_censored_arrivals(frames, resolution.classification) == []
        assert resolution.decision.strategy == "yield"
        assert len(resolution.decision.crossing_order) == 4
        assert resolution.decision.yield_robot == resolution.passing_order[-1]

    @pytest.mark.parametrize("standoff_m", STANDOFFS_M)
    def test_without_the_zone_no_intersection_is_possible(self, standoff_m):
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        verdict = classify_scene(_buffer(standoff_m, LAG_CASES[0]), [], params)
        assert verdict.scenario != "intersection"


class TestMockDecision:
    def test_first_decision_is_a_full_order_yield_then_the_scene_clears(self):
        first, *rest = json.loads(MOCK_PATH.read_text())
        decision = parse_decision_text(json.dumps(first))
        assert decision.strategy == "yield"
        assert decision.type == "bottleneck"
        assert decision.yield_robot == "robot_2"
        assert sorted(decision.crossing_order) == ["robot_1", "robot_2", "robot_3", "robot_4"]
        assert [parse_decision_text(json.dumps(d)).strategy for d in rest] == ["none"]

    def test_skip_variant_answers_none_first_then_the_same_yield(self):
        # Smoke IB10's mock: the first analysis may be a start-up stall of one
        # robot, so the scripted yield is the second answer.
        skip, *rest = json.loads(SKIP_MOCK_PATH.read_text())
        assert parse_decision_text(json.dumps(skip)).strategy == "none"
        assert rest == json.loads(MOCK_PATH.read_text())


class TestSingleYieldGroundingAtFourWayStandoff:
    """The structural defect the audit predicted before the smoke.

    Two opposing pairs meet at the centre, so every passer's straight escort
    runs through a robot that is still waiting its turn. M4 exempts only the
    yielder's pairs with its admitted passers, so the passer latches against
    the waiting robot (0.45 m) whatever the order.
    """

    def _command(self, standoff_m: float) -> tuple[dict, SnapshotFrame]:
        frame = _buffer(standoff_m, LAG_CASES[0])[-1]
        first = json.loads(MOCK_PATH.read_text())[0]
        result = ReasonerResult(
            request_id="req-ib", decision=parse_decision_text(json.dumps(first)), raw_text="{}",
            diagnostics=ReasonerDiagnostics(
                request_id="req-ib", backend_id="mock", attempts=1, parse_status="valid"
            ),
        )
        shipped = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"]
        geometry = SceneGeometry(**shipped)
        command = ground_reasoner_result(
            result, geometry=geometry, snapshot=frame,
            params=load_grounding_params(REPO_ROOT / "config/rag.yaml"),
        )
        return command, frame

    @pytest.mark.parametrize("standoff_m", STANDOFFS_M)
    def test_derived_grounding_executes_the_mock_as_a_yield(self, standoff_m):
        command, _ = self._command(standoff_m)
        (yield_action,) = [a for a in command["actions"] if a["action"] == "yield"]
        assert yield_action["robot_id"] == "robot_2"
        assert yield_action["parameters"]["crossing_order"] == ["robot_1", "robot_3", "robot_4"]

    @pytest.mark.parametrize("standoff_m", STANDOFFS_M)
    def test_a_passer_escort_runs_into_its_waiting_opposing_partner(self, standoff_m):
        # The yield clears one arm of one opposing pair; the other pair is
        # still nose to nose, so whichever of them passes first drives its
        # straight escort into the other, which is still waiting its turn.
        command, frame = self._command(standoff_m)
        (yield_action,) = [a for a in command["actions"] if a["action"] == "yield"]
        p = yield_action["parameters"]
        order = p["crossing_order"]
        position = order.index("robot_3")
        assert order.index("robot_4") > position
        passer, partner = frame.find_robot("robot_3"), frame.find_robot("robot_4")
        heading = (math.cos(passer.theta), math.sin(passer.theta))
        closest = min(
            math.hypot(passer.x + heading[0] * s - partner.x, passer.y + heading[1] * s - partner.y)
            for s in np.arange(0.0, p["crossing_escort_m"][position], 0.05)
        )
        assert closest < LATCH_M

    @pytest.mark.parametrize("standoff_m", STANDOFFS_M)
    def test_first_passer_skims_the_waiting_cross_pair(self, standoff_m):
        # robot_1's escort along y = 0 passes the north-south pair at their
        # standoff offset: inside M4's latch at 0.3-0.4 m, and inside its
        # 0.6 m STALE fail-safe band at 0.5 m.
        command, frame = self._command(standoff_m)
        (yield_action,) = [a for a in command["actions"] if a["action"] == "yield"]
        p = yield_action["parameters"]
        passer = frame.find_robot("robot_1")
        closest = min(
            math.hypot(passer.x + s - w.x, passer.y - w.y)
            for s in np.arange(0.0, p["crossing_escort_m"][0], 0.05)
            for w in (frame.find_robot("robot_3"), frame.find_robot("robot_4"))
        )
        assert closest == pytest.approx(standoff_m, abs=0.05)

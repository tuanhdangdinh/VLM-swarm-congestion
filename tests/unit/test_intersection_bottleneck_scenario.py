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

from swarm_orchestrator.shadow_classical import (
    ClassicalRetreatContext,
    classical_retreat_answer,
    find_censored_arrivals,
)

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, load_scenario
from isaac.vgu_sim.config import WarehouseConfig
from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path
from reasoning.baselines.classical_reasoner import (
    ConflictZone,
    classify_scene,
    load_classical_params,
    resolve_classical,
)
from reasoning.rag.command_grounder import (
    PlanRepairParams,
    ground_reasoner_result,
    verify_and_repair_plan,
)
from reasoning.rag.maneuver_geometry import GroundingParams, load_grounding_params
from reasoning.rag.scene_geometry import (
    SceneGeometry,
    arm_geometry,
    required_room_m,
    yield_retreat_room_m,
)
from reasoning.vlm.models import (
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)
from reasoning.vlm.output_parser import parse_decision_text

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = REPO_ROOT / "isaac/config/scenarios/intersection_bottleneck.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCHESTRATOR_YAML = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
CALIBRATION_YAML = REPO_ROOT / "ros2_ws/src/swarm_perception/config/calibration.yaml"
MOCK_PATH = REPO_ROOT / "config/mock_decisions/intersection_yield_once.json"
SKIP_MOCK_PATH = REPO_ROOT / "config/mock_decisions/intersection_skip_then_yield_once.json"
JUNCTION_CLEAR_M3_DEFAULT_MOCK_PATH = (
    REPO_ROOT / "config/mock_decisions/intersection_junction_clear_m3_default_once.json"
)
JUNCTION_CLEAR_VLM_VERBATIM_MOCK_PATH = (
    REPO_ROOT / "config/mock_decisions/intersection_junction_clear_vlm_verbatim_once.json"
)
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


class TestJunctionClearMockDecisions:
    """Step-6 composite smoke mocks: both runs skip once (the same one-trigger
    pattern `SKIP_MOCK_PATH` uses, sized from the IB9 20260929_084557 smoke
    this scenario shares its spawns/speeds with) before the real
    `junction_clear` decision -- run A names only the strategy token (M3's
    chi-ranked derivation owns the sequence, `m3_default`); run B also names
    a valid `proposed_plan` for the chi recede pair in order, so every leg is
    feasible verbatim.
    """

    @staticmethod
    def _geometry() -> SceneGeometry:
        shipped = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"]
        return SceneGeometry(**{
            **shipped,
            "corridor": {
                "axis": "x", "center_m": 0.0, "half_length_m": 0.6,
                "aisle_half_width_m": 0.6, "occluder_height_m": 0.0,
            },
            "arms": JUNCTION_ARMS,
            "junction_recede_offset_m": 1.2,
            "junction_backup_clearance_m": 1.1,
        })

    def test_both_runs_skip_once_then_answer_junction_clear_then_clear(self):
        for path in (JUNCTION_CLEAR_M3_DEFAULT_MOCK_PATH, JUNCTION_CLEAR_VLM_VERBATIM_MOCK_PATH):
            skip, decision_json, clear = json.loads(path.read_text())
            assert parse_decision_text(json.dumps(skip)).strategy == "none"
            decision = parse_decision_text(json.dumps(decision_json))
            assert decision.strategy == "junction_clear"
            assert sorted(decision.involved_robots) == list(ROBOTS)
            assert parse_decision_text(json.dumps(clear)).strategy == "none"

    def test_run_a_has_no_proposed_plan(self):
        _skip, decision_json, _clear = json.loads(JUNCTION_CLEAR_M3_DEFAULT_MOCK_PATH.read_text())
        assert "proposed_plan" not in decision_json

    def test_run_b_names_the_chi_recede_pair_in_chi_order(self):
        _skip, decision_json, _clear = json.loads(
            JUNCTION_CLEAR_VLM_VERBATIM_MOCK_PATH.read_text()
        )
        actions = {leg["robot_id"]: leg["action"] for leg in decision_json["proposed_plan"]}
        assert actions == {
            "robot_4": "reverse", "robot_3": "reverse", "robot_1": "yield", "robot_2": "cross",
        }
        order = [leg["robot_id"] for leg in decision_json["proposed_plan"]]
        assert order.index("robot_4") < order.index("robot_3")  # D_SPACE 0.923 < 0.942

    def test_run_a_decision_verifies_as_m3_default(self):
        _skip, decision_json, _clear = json.loads(JUNCTION_CLEAR_M3_DEFAULT_MOCK_PATH.read_text())
        decision = parse_decision_text(json.dumps(decision_json))
        verified = verify_and_repair_plan(
            decision, _ib10_frame(), geometry=self._geometry(),
            repair_params=PlanRepairParams(), grounding_params=GroundingParams(mode="derived"),
        )
        assert verified.provenance == "m3_default"
        assert verified.rejection_reason == "plan absent"

    def test_run_b_decision_verifies_verbatim_before_any_vm_time_is_spent(self):
        # Advisor review: confirm run B's scripted plan grounds with no
        # repair under the EXACT geometry it will be deployed with, locally,
        # before spending VM time on it.
        _skip, decision_json, _clear = json.loads(
            JUNCTION_CLEAR_VLM_VERBATIM_MOCK_PATH.read_text()
        )
        decision = parse_decision_text(json.dumps(decision_json))
        verified = verify_and_repair_plan(
            decision, _ib10_frame(), geometry=self._geometry(),
            repair_params=PlanRepairParams(), grounding_params=GroundingParams(mode="derived"),
        )
        assert verified.provenance == "vlm_verbatim"
        assert verified.edits == []


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


# The junction declaration of the goal-table row (orchestrator.yaml): the
# junction box (the crossing of the two 1.2 m aisles, no barrier, so no
# occluder) and each robot's approach arm with the arm's outward sign.
JUNCTION_CORRIDOR = (
    "{ axis: x, center_m: 0.0, half_length_m: 0.6, aisle_half_width_m: 0.6,\n"
    "#     occluder_height_m: 0.0 }"
)
JUNCTION_ARMS = {
    "robot_1": {"axis": "x", "side": -1},
    "robot_2": {"axis": "x", "side": 1},
    "robot_3": {"axis": "y", "side": -1},
    "robot_4": {"axis": "y", "side": 1},
}
OPPOSITE = {"robot_1": "robot_2", "robot_2": "robot_1", "robot_3": "robot_4", "robot_4": "robot_3"}
ROBOTS = ("robot_1", "robot_2", "robot_3", "robot_4")
# Verified M1 tracking on y: GT (0, 1.75) tracked 366/366 rows (T3a smoke).
VERIFIED_TRACKED_ABS_Y_M = 1.75
# Robot half-width (nav2 footprint): the body must stay on free floor.
HALF_WIDTH_M = 0.09
# IB10 ground truth at the standoff (INTERSECTION_SMOKE_SUMMARY.txt).
IB10_STANDOFF = {
    "robot_1": (-0.2192, -0.0014),
    "robot_2": (0.33, 0.0158),
    "robot_3": (-0.0208, -0.2583),
    "robot_4": (0.0045, 0.2773),
}


def _junction_geometry() -> SceneGeometry:
    shipped = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"]
    corridor = {
        "axis": "x", "center_m": 0.0, "half_length_m": 0.6,
        "aisle_half_width_m": 0.6, "occluder_height_m": 0.0,
    }
    return SceneGeometry(**{**shipped, "corridor": corridor, "arms": JUNCTION_ARMS})


def _ib10_frame() -> SnapshotFrame:
    scenario = _scenario()
    return SnapshotFrame(stamp=1.0, robots=[
        RobotStateInput(
            robot_id=r.robot_id, x=IB10_STANDOFF[r.robot_id][0], y=IB10_STANDOFF[r.robot_id][1],
            theta=r.spawn.yaw_rad, status="STOPPED", goal=(r.goal.x, r.goal.y),
        )
        for r in scenario.robots
    ])


def _frames():
    cases = [(f"standoff-{s}", _buffer(s, LAG_CASES[0])[-1]) for s in STANDOFFS_M]
    return [*cases, ("ib10", _ib10_frame())]


def _order(yielder: str) -> list[str]:
    return [OPPOSITE[yielder], *[r for r in ROBOTS if r not in (yielder, OPPOSITE[yielder])]]


def _yield_decision(yielder: str, order: list[str] | None = None) -> ReasonerResult:
    decision = {
        "congestion_detected": True, "type": "bottleneck", "involved_robots": list(ROBOTS),
        "root_cause": "four-way standoff", "strategy": "yield",
        "justification": "all four robots stopped at the crossing", "yield_robot": yielder,
        "crossing_order": [yielder, *(order or _order(yielder))],
    }
    return ReasonerResult(
        request_id="req-ib", decision=parse_decision_text(json.dumps(decision)), raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="req-ib", backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


def _ground(yielder, frame, geometry=None, order=None, **kwargs) -> dict:
    return ground_reasoner_result(
        _yield_decision(yielder, order), geometry=geometry or _junction_geometry(),
        snapshot=frame, params=load_grounding_params(REPO_ROOT / "config/rag.yaml"), **kwargs,
    )


def _yield_parameters(command: dict) -> dict:
    (action,) = [a for a in command["actions"] if a["action"] == "yield"]
    return action["parameters"]


def _arm_room_from_map(robot_id: str) -> float:
    # Free floor along the arm, from the junction mouth outward to the first
    # occupied cell under the robot's body (centreline +- half-width).
    cfg = WarehouseConfig()
    grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=RESOLUTION_M)
    arm = JUNCTION_ARMS[robot_id]
    mouth = 0.6
    s = mouth
    while True:
        coord = arm["side"] * s
        for d in (-HALF_WIDTH_M, 0.0, HALF_WIDTH_M):
            x, y = (coord, d) if arm["axis"] == "x" else (d, coord)
            if _cell(grid, cfg, x, y) != 255:
                return s - mouth
        s += RESOLUTION_M


class TestJunctionGeometry:
    """Each robot yields back along the arm it came in on (S2 discharged)."""

    def test_goal_table_declares_the_junction_and_every_arm(self):
        table = ORCHESTRATOR_YAML.read_text()
        assert f"scenario_geometry corridor\n#     {JUNCTION_CORRIDOR}" in table
        for robot_id, arm in JUNCTION_ARMS.items():
            assert f"{robot_id}: {{ axis: {arm['axis']}, side: {arm['side']} }}" in table

    def test_goal_table_declares_the_step_6_junction_clear_fields(self):
        # Step 6 (build-order, this scenario's composite smoke): the goal
        # table must document BOTH J2 fields together, or the cross phase
        # silently grounds the unsolved shipped row (bug 4,
        # docs/implementation_notes.md 2026-10-02 step-5 post-landing entry).
        table = ORCHESTRATOR_YAML.read_text()
        assert "junction_recede_offset_m: 1.2" in table
        assert "junction_backup_clearance_m: 1.1" in table
        assert "junction_geometry=shipped_unsolved" in table

    def test_arms_are_the_approach_arms_of_the_scenario(self):
        for robot in _scenario().robots:
            arm = JUNCTION_ARMS[robot.robot_id]
            axis = "x" if robot.spawn.y == 0.0 else "y"
            coord = robot.spawn.x if axis == "x" else robot.spawn.y
            assert (arm["axis"], arm["side"]) == (axis, int(math.copysign(1, coord)))

    def test_shipped_geometry_keeps_a_single_corridor(self):
        shipped = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"]
        assert SceneGeometry(**shipped).arms is None

    def test_shipped_geometry_has_no_junction_clearance_override(self):
        # J2 (design study 2026-09-29 S1, section 3) is off by default: the
        # shipped goal-table geometry declares no override, so every v1 and
        # v2-pre-J2 scene keeps the verified 1.7 m head-on tuning.
        shipped = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"]
        assert SceneGeometry(**shipped).junction_backup_clearance_m is None

    @pytest.mark.parametrize("yielder", ROBOTS)
    @pytest.mark.parametrize(("case", "frame"), _frames())
    def test_every_yielder_grounds_a_yield_along_its_own_arm(self, yielder, case, frame):
        command = _ground(yielder, frame)
        p = _yield_parameters(command)
        start = frame.find_robot(yielder)
        arm = JUNCTION_ARMS[yielder]
        axis, perp = (0, 1) if arm["axis"] == "x" else (1, 0)
        end = (p["retreat_x_m"], p["retreat_y_m"])
        moved = (end[axis] - (start.x, start.y)[axis]) * arm["side"]
        assert moved == pytest.approx(p["backup_distance_m"], abs=1e-3), case
        assert abs(end[perp] - (start.x, start.y)[perp]) == pytest.approx(0.36, abs=1e-3)
        # J1 (v2-branch divergence from the v1-frozen Arm B, design study
        # 2026-09-29): in this symmetric four-way, the two cross-axis robots
        # are each other's opposite-side partner, so both drop out of the
        # order; only the yielder's own-axis opposite robot keeps an action.
        same_axis_order = [r for r in _order(yielder) if JUNCTION_ARMS[r]["axis"] == arm["axis"]]
        assert [a["robot_id"] for a in command["actions"]] == [yielder, *same_axis_order]

    @pytest.mark.parametrize("yielder", ROBOTS)
    @pytest.mark.parametrize(("case", "frame"), _frames())
    def test_shipped_single_corridor_grounds_no_north_south_yield(self, yielder, case, frame):
        # S2 as the smoke found it: under the single x corridor a north-south
        # yielder degrades to a reroute; an east-west one grounds a yield.
        command = _ground(yielder, frame, geometry=SceneGeometry(
            **yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"]
        ))
        actions = {a["action"] for a in command["actions"]}
        if JUNCTION_ARMS[yielder]["axis"] == "y":
            assert "yield" not in actions, case
        else:
            assert "yield" in actions, case

    @pytest.mark.parametrize("yielder", ROBOTS)
    @pytest.mark.parametrize(("case", "frame"), _frames())
    def test_retreat_stays_tracked_and_on_free_floor(self, yielder, case, frame):
        p = _yield_parameters(_ground(yielder, frame))
        start = frame.find_robot(yielder)
        corner = (
            (p["retreat_x_m"], start.y) if JUNCTION_ARMS[yielder]["axis"] == "x"
            else (start.x, p["retreat_y_m"])
        )
        end = (p["retreat_x_m"], p["retreat_y_m"])
        assert abs(end[0]) <= VERIFIED_TRACKED_ABS_X_M
        assert abs(end[1]) <= VERIFIED_TRACKED_ABS_Y_M, case
        cfg = WarehouseConfig()
        grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=RESOLUTION_M)
        for a, b in (((start.x, start.y), corner), (corner, end)):
            for t in np.linspace(0.0, 1.0, 40):
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                for dx, dy in ((HALF_WIDTH_M, 0), (-HALF_WIDTH_M, 0), (0, HALF_WIDTH_M),
                               (0, -HALF_WIDTH_M)):
                    assert _cell(grid, cfg, x + dx, y + dy) == 255, (yielder, case, x, y)

    @pytest.mark.parametrize("robot_id", ROBOTS)
    def test_map_leaves_every_arm_the_required_retreat_room(self, robot_id):
        # Racks wall the arms laterally; axially each arm runs to the
        # perimeter wall, far beyond the room a park point needs.
        assert _arm_room_from_map(robot_id) >= required_room_m(_junction_geometry()) + 2.0

    @pytest.mark.parametrize("yielder", ROBOTS)
    def test_gate_scores_each_arm_against_its_own_map_wall(self, yielder):
        # The perimeter walls as static obstacles: the gate measures each
        # yielder's room along its own arm and it matches the map.
        geometry = _junction_geometry()
        walls = []
        for robot_id, arm in JUNCTION_ARMS.items():
            face = arm["side"] * (0.6 + _arm_room_from_map(robot_id))
            centre = face + arm["side"] * 0.15
            x, y = (centre, 0.0) if arm["axis"] == "x" else (0.0, centre)
            walls.append(StaticObstacleInput(
                obstacle_id=f"wall_{robot_id}", x=x, y=y, size_x_m=0.3, size_y_m=0.3,
            ))
        resolved, side = arm_geometry(geometry, yielder)
        room = yield_retreat_room_m(IB10_STANDOFF[yielder], side, walls, resolved)
        assert room == pytest.approx(_arm_room_from_map(yielder), abs=1e-6)
        command = _ground(
            yielder, _ib10_frame(), static_obstacles=walls, yield_feasibility_mode="swap"
        )
        assert _yield_parameters(command).get("yield_robot_grounded_from") is None
        assert command["actions"][0]["robot_id"] == yielder

    @pytest.mark.parametrize("standoff_m", STANDOFFS_M)
    @pytest.mark.parametrize("lags", LAG_CASES)
    def test_arm_b_retreat_is_computed_and_equals_the_grounded_one(self, standoff_m, lags):
        # Arm B's shadow runs the same roles and ranking functions, so it
        # follows the arms: whichever robot it picks, its retreat is computed
        # and is the pose the grounder executes for that yield.
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        frames = _buffer(standoff_m, lags)
        classical = resolve_classical(frames, [ConflictZone(**ZONE)], params).decision
        context = ClassicalRetreatContext(
            params=load_grounding_params(REPO_ROOT / "config/rag.yaml"),
            geometry=_junction_geometry(),
        )
        for yielder in ROBOTS:
            order = [yielder, *[r for r in classical.crossing_order if r != yielder]]
            decision = classical.model_copy(
                update={"yield_robot": yielder, "crossing_order": order}
            )
            answer = classical_retreat_answer(decision, frames[-1], context)
            assert answer.status == "computed", (yielder, answer.reason)
            p = _yield_parameters(_ground(yielder, frames[-1], order=order[1:]))
            assert (round(answer.x, 3), round(answer.y, 3)) == (p["retreat_x_m"], p["retreat_y_m"])


class TestFourWayResidualsUnderJunctionGeometry:
    """What the arms fix at grounding (S1 resolved by J1, v2-branch divergence
    from the v1-frozen Arm B) and what they do not (S2 stays discharged)."""

    def test_cross_axis_held_pair_gets_no_action_instead_of_an_inexecutable_one(self):
        # Pre-J1 this was `test_robot_3_escort_still_runs_into_the_waiting_
        # robot_4`: robot_3's queued escort ran straight through robot_4 at
        # 0.000 m (the design study's standing finding). J1 drops the
        # mutually opposite-side pair (robot_3, robot_4) from the order
        # instead of grounding an inexecutable escort for either of them.
        frame = _ib10_frame()
        command = _ground("robot_2", frame, order=["robot_1", "robot_3", "robot_4"])
        p = _yield_parameters(command)
        assert p["crossing_order"] == ["robot_1"]
        assert "crossing_escort_m" not in p
        assert [a["robot_id"] for a in command["actions"]] == ["robot_2", "robot_1"]
        assert "order=junction_same_axis" in command["degradations"]

    def test_first_passer_starts_inside_the_latch_of_the_cross_pair(self):
        # robot_1 is never exempt against robot_3 / robot_4, so M4 holds it.
        robot_1 = IB10_STANDOFF["robot_1"]
        for other in ("robot_3", "robot_4"):
            assert math.dist(robot_1, IB10_STANDOFF[other]) < LATCH_M

    def test_north_south_same_arm_escort_leaves_the_tracked_band(self):
        # robot_3 yields south; its opposing partner robot_4 must pass the
        # parked yielder by the clearance, which ends beyond M1's y band.
        frame = _ib10_frame()
        p = _yield_parameters(_ground("robot_3", frame))
        assert p["crossing_order"][0] == "robot_4"
        end_y = frame.find_robot("robot_4").y - p["passer_escort_distance_m"]
        assert end_y < -_tracked_band()[1]


class TestJunctionBackupClearanceOverride:
    """J2 end to end through `ground_reasoner_result` (design study
    2026-09-29 S1, section 3): the two-robot N-S yield the table grounds,
    not the four-way order `_yield_decision`/`_ground` build. The shipped
    1.7 m clearance is what `test_north_south_same_arm_escort_leaves_the_tracked_band`
    shows failing the band; 1.1 m is the study's fix.
    """

    @staticmethod
    def _standoff_frame(standoff_m: float) -> SnapshotFrame:
        # E-W robots parked at their goal arms (the study's 1.75 m row), N-S
        # robots at the two-robot yield's standoff offset +-standoff_m. The
        # E-W pair is scene dressing only: it is not in this decision's
        # crossing order.
        return SnapshotFrame(stamp=1.0, robots=[
            RobotStateInput(
                robot_id="robot_1", x=-1.75, y=0.0, theta=0.0, status="STOPPED",
                goal=(1.75, 0.0),
            ),
            RobotStateInput(
                robot_id="robot_2", x=1.75, y=0.0, theta=math.pi, status="STOPPED",
                goal=(-1.75, 0.0),
            ),
            RobotStateInput(
                robot_id="robot_3", x=0.0, y=-standoff_m, theta=math.pi / 2, status="STOPPED",
                goal=(0.0, standoff_m),
            ),
            RobotStateInput(
                robot_id="robot_4", x=0.0, y=standoff_m, theta=-math.pi / 2, status="STOPPED",
                goal=(0.0, -standoff_m),
            ),
        ])

    @staticmethod
    def _ground_ns_yield(frame: SnapshotFrame, geometry: SceneGeometry) -> dict:
        # A plain two-robot yield (robot_3 yields, robot_4 the only passer),
        # as the study's section-3 sweep grounds it: `_yield_decision` always
        # declares all four `ROBOTS` involved, which a two-robot crossing
        # order fails to cover and falls back to the implicit four-way order.
        decision = {
            "congestion_detected": True, "type": "bottleneck",
            "involved_robots": ["robot_3", "robot_4"], "root_cause": "n-s yield",
            "strategy": "yield", "justification": "n-s pair stopped at the junction",
            "yield_robot": "robot_3", "crossing_order": ["robot_3", "robot_4"],
        }
        result = ReasonerResult(
            request_id="req-ns", decision=parse_decision_text(json.dumps(decision)),
            raw_text="{}", diagnostics=ReasonerDiagnostics(
                request_id="req-ns", backend_id="mock", attempts=1, parse_status="valid"
            ),
        )
        command = ground_reasoner_result(
            result, geometry=geometry, snapshot=frame,
            params=load_grounding_params(REPO_ROOT / "config/rag.yaml"),
        )
        return _yield_parameters(command)

    @pytest.mark.parametrize("standoff_m", [0.10, 0.13, 0.20, 0.27])
    def test_junction_clearance_keeps_the_n_s_passer_in_band(self, standoff_m):
        geometry = _junction_geometry().model_copy(
            update={"junction_backup_clearance_m": 1.1}
        )
        frame = self._standoff_frame(standoff_m)
        p = self._ground_ns_yield(frame, geometry)
        assert p["backup_distance_m"] == round(1.018 - standoff_m, 3)
        end_y = frame.find_robot("robot_4").y - p["passer_escort_distance_m"]
        assert abs(end_y) == pytest.approx(1.668, abs=1e-3)
        assert abs(end_y) <= 1.70

    def test_without_the_override_the_shipped_clearance_still_governs(self):
        # Regression: the same end-to-end path, no override set, reproduces
        # the shipped-clearance row of the study's table (section 3) exactly.
        geometry = _junction_geometry()  # junction_backup_clearance_m defaults None
        frame = self._standoff_frame(0.13)
        p = self._ground_ns_yield(frame, geometry)
        assert p["backup_distance_m"] == 1.44
        end_y = frame.find_robot("robot_4").y - p["passer_escort_distance_m"]
        assert abs(end_y) == pytest.approx(2.22, abs=1e-3)


def test_legacy_grounding_parks_a_north_south_yielder_on_its_arm():
    # Legacy mode (the T2b forced-order harness mode) honours the arms too:
    # park point on robot_3's own arm, crossing passers cleared out of the
    # junction along their own axes, the same-arm passer past the park point.
    positions = {rid: xy for rid, xy in IB10_STANDOFF.items()}
    command = ground_reasoner_result(
        _yield_decision("robot_3", ["robot_1", "robot_2", "robot_4"]),
        robot_positions=positions,
        geometry=_junction_geometry(),
    )
    p = _yield_parameters(command)
    park = round(-(0.6 * (3.0 - 0.21) / 3.0 + 0.06 + 0.4), 3)
    assert (p["park_axis"], p["park_coord_m"]) == ("y", park)
    assert "park_x_m" not in p
    assert p["backup_distance_m"] == round(IB10_STANDOFF["robot_3"][1] - park, 3)
    assert p["crossing_clear_m"] == [
        round(0.6 - IB10_STANDOFF["robot_1"][0] + 0.65, 3),
        round(IB10_STANDOFF["robot_2"][0] + 0.6 + 0.65, 3),
        round(IB10_STANDOFF["robot_4"][1] - park + 0.65, 3),
    ]


def test_north_south_mock_is_the_skip_mock_with_robot_3_yielding():
    # The v2 smoke's second run: the same scripted shape, the yield handed to
    # a north-south robot so its own-arm grounding runs live.
    skip, yield_decision, clear = json.loads(
        (REPO_ROOT / "config/mock_decisions/intersection_skip_then_yield_robot_3_once.json")
        .read_text()
    )
    _, reference, reference_clear = json.loads(SKIP_MOCK_PATH.read_text())
    decision = parse_decision_text(json.dumps(yield_decision))
    assert parse_decision_text(json.dumps(skip)).strategy == "none"
    assert (decision.strategy, decision.yield_robot) == ("yield", "robot_3")
    assert decision.crossing_order == ["robot_4", "robot_1", "robot_2", "robot_3"]
    assert {k: v for k, v in yield_decision.items() if k not in (
        "yield_robot", "crossing_order", "justification"
    )} == {k: v for k, v in reference.items() if k not in (
        "yield_robot", "crossing_order", "justification"
    )}
    assert clear == reference_clear

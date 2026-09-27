"""Tests for the T3b obstacle-in-candidate scenario `obstacle_in_candidate`.

The candidate machinery (`reasoning.rag.retreat_candidates`) never sees the
box: it is untracked by construction. These tests therefore recompute the
swept paths themselves and measure them against the box's footprint, using
the scenario's own numbers.
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, load_scenario
from isaac.vgu_sim.config import (
    BUILTIN_TIMED_OBSTACLE_ASSETS,
    CameraConfig,
    RetreatOracleConfig,
    WarehouseConfig,
)
from reasoning.rag.command_grounder import prepare_retreat_selection
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_candidates import RetreatCandidate
from reasoning.rag.scene_geometry import SceneGeometry, park_offset_m, pull_off_lateral_m
from reasoning.vlm.models import CongestionDecision, RobotStateInput, SnapshotFrame

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = REPO_ROOT / "isaac/config/scenarios/obstacle_in_candidate.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCHESTRATOR_YAML = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
RAG_YAML = REPO_ROOT / "config/rag.yaml"
MOCK_PATH = REPO_ROOT / "config/mock_decisions/obstacle_in_candidate_yield_once.json"
RESOLUTION_M = 0.05
# The per-scenario band M5 must be given (orchestrator.yaml goal table row).
BAND_M = (-0.55, 1.0)
# Nav2 footprint [[+-0.07, +-0.09]] (nav2_params.yaml): the radius a robot
# turning in place sweeps.
CIRCUMSCRIBED_RADIUS_M = math.hypot(0.07, 0.09)
# M5's first scene and the earliest robot departure seen on the VM (sim s).
M5_FIRST_SCENE_SIM_SEC = 12.0
EARLIEST_DEPARTURE_SIM_SEC = 10.6
# Standoff variation the design must tolerate: separations seen in the head-on
# family (0.23-0.98 m), a +-0.2 m shift of the meeting point along the
# corridor, yielder lateral jitter, and the passer sitting up to 0.04 m north
# of the yielder (0.05 m flips the default; see the dedicated test).
SEPARATIONS_M = (0.25, 0.46, 0.7, 0.98)
SHIFTS_M = (-0.2, -0.1, 0.0, 0.1, 0.2)
YIELDER_YS_M = (-0.06, 0.0, 0.06)
PASSER_OFFSETS_M = (-0.2, -0.05, 0.0, 0.04)


def _scenario():
    return load_scenario(SCENARIO_PATH)


def _box(scenario) -> tuple[float, float, float, float]:
    (box,) = scenario.timed_obstacles
    hx, hy = box.size.x_m / 2, box.size.y_m / 2
    return (box.pose.x - hx, box.pose.x + hx, box.pose.y - hy, box.pose.y + hy)


def _robot(scenario, robot_id: str):
    return next(r for r in scenario.robots if r.robot_id == robot_id)


def _geometry(scenario) -> SceneGeometry:
    # The shipped block with the corridor moved to this scenario's barrier,
    # exactly the edit the orchestrator.yaml goal table asks for.
    data = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"]
    barrier = scenario.aisle_barrier
    data["corridor"] = {
        **data["corridor"],
        "center_m": barrier.center_x_m,
        "half_length_m": barrier.length_m / 2,
    }
    return SceneGeometry(**data)


def _params(band: tuple[float, float] | None = BAND_M) -> GroundingParams:
    section = yaml.safe_load(RAG_YAML.read_text())["grounding"]
    return GroundingParams(**{**section, "aisle_y_band_m": band})


def _standoff(
    scenario,
    separation_m: float = 0.46,
    shift_m: float = 0.0,
    yielder_y_m: float = 0.0,
    passer_offset_m: float = 0.0,
) -> SnapshotFrame:
    """Both robots stopped nose to nose around the midpoint of their spawns."""
    r1, r2 = _robot(scenario, "robot_1"), _robot(scenario, "robot_2")
    mid = (r1.spawn.x + r2.spawn.x) / 2 + shift_m
    return SnapshotFrame(
        stamp=30.0,
        robots=[
            RobotStateInput(
                robot_id="robot_1", x=mid - separation_m / 2, y=yielder_y_m, theta=0.0
            ),
            RobotStateInput(
                robot_id="robot_2",
                x=mid + separation_m / 2,
                y=yielder_y_m + passer_offset_m,
                theta=math.pi,
            ),
        ],
    )


def _selection(scenario, frame: SnapshotFrame, band=BAND_M):
    oracle = scenario.oracle
    return prepare_retreat_selection(
        frame, oracle.yielder, [oracle.passer], _params(band), geometry=_geometry(scenario)
    )


def _segment(p0, p1, step_m: float = 0.02) -> list[tuple[float, float]]:
    count = max(1, math.ceil(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / step_m))
    return [
        (p0[0] + (p1[0] - p0[0]) * i / count, p0[1] + (p1[1] - p0[1]) * i / count)
        for i in range(count + 1)
    ]


def _sweep(frame: SnapshotFrame, yielder_id: str, candidate: RetreatCandidate):
    """Robot-centre path of the backup and then the sidestep to `candidate`."""
    yielder = frame.find_robot(yielder_id)
    parked = (yielder.x - candidate.backup_m, yielder.y)
    return _segment((yielder.x, yielder.y), parked) + _segment(parked, (candidate.x, candidate.y))


def _box_distance(point: tuple[float, float], box) -> float:
    x0, x1, y0, y1 = box
    dx = max(x0 - point[0], 0.0, point[0] - x1)
    dy = max(y0 - point[1], 0.0, point[1] - y1)
    return math.hypot(dx, dy)


def _sweep_margin_m(scenario) -> float:
    # What the sidestep already keeps from an aisle wall: robot half-width
    # plus wall margin (scene_geometry.pull_off_lateral_m).
    geometry = _geometry(scenario)
    return geometry.robot.half_width_m + geometry.wall_margin_m


def _cell(x: float, y: float, cfg: WarehouseConfig) -> tuple[int, int]:
    return (
        int(np.floor((cfg.depth_m / 2 - y) / RESOLUTION_M)),
        int(np.floor((x + cfg.width_m / 2) / RESOLUTION_M)),
    )


def _grid(scenario):
    grid, _ = build_occupancy_grid(
        WarehouseConfig(),
        obstacles=[],
        resolution_m=RESOLUTION_M,
        aisle_barrier=scenario.aisle_barrier,
        static_obstacles=scenario.static_obstacles,
    )
    return grid


def _marker_plane(point: tuple[float, float], height_m: float, scenario) -> tuple[float, float]:
    """Where a world point at `height_m` appears in marker-plane coordinates.

    The stage-2 rings are placed with M1's homography, which is exact only at
    the marker plane; anything lower or higher images radially shifted.
    """
    camera_z = CameraConfig().position_m[2]
    plane = _geometry(scenario).camera.marker_height_m
    scale = (camera_z - plane) / (camera_z - height_m)
    return point[0] * scale, point[1] * scale


class TestScenario:
    def test_loads_as_head_on_with_a_retreat_oracle(self):
        scenario = _scenario()

        assert scenario.name == "obstacle_in_candidate"
        assert scenario.family == "head_on"
        assert [r.robot_id for r in scenario.robots] == ["robot_1", "robot_2"]
        assert isinstance(scenario.oracle, RetreatOracleConfig)

    def test_box_is_a_built_in_static_box(self):
        (box,) = _scenario().timed_obstacles

        assert box.asset == "static_box"
        assert box.asset in BUILTIN_TIMED_OBSTACLE_ASSETS

    def test_box_is_present_before_m5_and_departure_and_never_removed(self):
        (box,) = _scenario().timed_obstacles

        assert box.spawn_at_sec < min(M5_FIRST_SCENE_SIM_SEC, EARLIEST_DEPARTURE_SIM_SEC)
        assert box.remove_at_sec is None

    def test_spawns_and_goals_inside_camera_roi_with_margin(self):
        camera = CameraConfig()
        half_x, half_y = camera.roi_width_m / 2 - 0.5, camera.roi_depth_m / 2 - 0.5

        for robot in _scenario().robots:
            for x, y in ((robot.spawn.x, robot.spawn.y), (robot.goal.x, robot.goal.y)):
                assert abs(x) <= half_x + 1e-9 and abs(y) <= half_y + 1e-9, (robot.robot_id, x, y)

    def test_robots_meet_head_on_through_the_corridor(self):
        scenario = _scenario()
        r1, r2 = _robot(scenario, "robot_1"), _robot(scenario, "robot_2")
        barrier = scenario.aisle_barrier
        west, east = (barrier.center_x_m + s * barrier.length_m / 2 for s in (-1, 1))

        assert r1.spawn.x < west and r1.goal.x > east
        assert r2.spawn.x > east and r2.goal.x < west
        # A straight approach run before each mouth (head_on_deadlock header).
        assert west - r1.spawn.x >= 0.4 - 1e-9 and r2.spawn.x - east >= 0.4 - 1e-9


class TestGeometry:
    def test_park_point_lands_in_the_junction(self):
        scenario = _scenario()
        geometry = _geometry(scenario)
        park_x = geometry.corridor.center_m - park_offset_m(geometry)
        aisle_half = WarehouseConfig().nominal_aisle_width_m / 2

        assert park_x == pytest.approx(-0.323, abs=1e-3)
        assert abs(park_x) + CIRCUMSCRIBED_RADIUS_M <= aisle_half

    def test_nominal_standoff_parks_at_the_park_point(self):
        scenario = _scenario()
        frame = _standoff(scenario)
        selection = _selection(scenario, frame)
        geometry = _geometry(scenario)
        park_x = round(geometry.corridor.center_m - park_offset_m(geometry), 3)

        # The park-point floor, not the pass clearance, sets the backup.
        assert selection.backup.feasible
        assert frame.find_robot("robot_1").x - selection.backup.value_m == pytest.approx(park_x)

    def test_band_offers_exactly_three_candidates(self):
        scenario = _scenario()
        selection = _selection(scenario, _standoff(scenario))
        lateral = round(pull_off_lateral_m(_geometry(scenario)), 3)

        assert sorted((c.label, c.lateral_m) for c in selection.candidates) == [
            ("A", lateral),
            ("B", -lateral),
            ("C", 2 * lateral),
        ]
        assert len(selection.candidates) == scenario.oracle.candidate_count

    def test_declared_aisle_alone_offers_two_so_the_band_is_needed(self):
        scenario = _scenario()
        selection = _selection(scenario, _standoff(scenario), band=None)

        assert sorted(c.label for c in selection.candidates) == ["A", "B"]

    def test_ranked_first_is_the_occupied_candidate(self):
        scenario = _scenario()
        oracle = scenario.oracle
        ranked = _selection(scenario, _standoff(scenario)).candidates

        assert [c.label for c in ranked] == ["C", "A", "B"]
        assert ranked[0].label == oracle.occupied_candidate == oracle.classical_candidate

    def test_box_fills_the_occupied_candidate(self):
        scenario = _scenario()
        frame = _standoff(scenario)
        box = _box(scenario)
        occupied = next(
            c for c in _selection(scenario, frame).candidates
            if c.label == scenario.oracle.occupied_candidate
        )
        half_width = _geometry(scenario).robot.half_width_m

        assert _box_distance((occupied.x, occupied.y), box) == 0.0
        assert min(_box_distance(p, box) for p in _sweep(frame, "robot_1", occupied)) < half_width

    def test_other_candidates_sweeps_clear_the_box_by_the_sweep_margin(self):
        scenario = _scenario()
        frame = _standoff(scenario)
        box = _box(scenario)
        margin = _sweep_margin_m(scenario)

        for candidate in _selection(scenario, frame).candidates:
            if candidate.label in scenario.oracle.correct_candidates:
                clearance = min(_box_distance(p, box) for p in _sweep(frame, "robot_1", candidate))
                assert clearance >= margin, (candidate.label, clearance)

    @pytest.mark.parametrize(
        ("separation", "shift", "yielder_y", "passer_offset"),
        list(itertools.product(SEPARATIONS_M, SHIFTS_M, YIELDER_YS_M, PASSER_OFFSETS_M)),
    )
    def test_design_holds_over_standoff_variation(
        self, separation, shift, yielder_y, passer_offset
    ):
        scenario = _scenario()
        oracle = scenario.oracle
        frame = _standoff(scenario, separation, shift, yielder_y, passer_offset)
        ranked = _selection(scenario, frame).candidates
        box = _box(scenario)
        half_width = _geometry(scenario).robot.half_width_m
        margin = _sweep_margin_m(scenario)
        clearance = {
            c.label: min(_box_distance(p, box) for p in _sweep(frame, "robot_1", c))
            for c in ranked
        }

        assert len(ranked) == oracle.candidate_count
        assert ranked[0].label == oracle.occupied_candidate
        assert clearance[oracle.occupied_candidate] < half_width
        for label in oracle.correct_candidates:
            assert clearance[label] >= margin - 1e-9, (label, clearance[label])

    def test_passer_north_of_the_yielder_flips_the_default_to_b(self):
        # Known limit: all candidates share the parked point, so the sidestep
        # clearance ties unless the passer sits off the yielder's line. North
        # by >= ~0.05 m (half a 0.09 m sample step), the northern sidesteps
        # pass nearer it and the southern B ranks first: the default is then
        # unoccupied and the trial loses its by-construction contrast.
        scenario = _scenario()
        ranked = _selection(scenario, _standoff(scenario, passer_offset_m=0.05)).candidates

        assert ranked[0].label == "B"

    def test_candidates_lie_on_open_floor(self):
        scenario = _scenario()
        cfg = WarehouseConfig()
        grid = _grid(scenario)
        reach = np.arange(-CIRCUMSCRIBED_RADIUS_M, CIRCUMSCRIBED_RADIUS_M + 1e-9, 0.02)

        for c in _selection(scenario, _standoff(scenario)).candidates:
            for dx, dy in itertools.product(reach, reach):
                if math.hypot(dx, dy) <= CIRCUMSCRIBED_RADIUS_M:
                    assert grid[_cell(c.x + dx, c.y + dy, cfg)] == 255, (c.label, dx, dy)

    def test_box_stands_clear_of_the_rack_face_and_the_transit_lane(self):
        scenario = _scenario()
        x0, x1, y0, _ = _box(scenario)
        aisle_half = WarehouseConfig().nominal_aisle_width_m / 2

        assert x0 >= -aisle_half + 0.05 and x1 <= aisle_half
        assert y0 - CIRCUMSCRIBED_RADIUS_M >= 0.5


class TestParallax:
    def test_occupied_letter_lands_on_the_box_image(self):
        scenario = _scenario()
        x0, x1, y0, y1 = _box(scenario)
        occupied = _selection(scenario, _standoff(scenario)).candidates[0]
        top = scenario.timed_obstacles[0].size.z_m
        corners = [
            _marker_plane((x, y), z, scenario)
            for x, y, z in itertools.product((x0, x1), (y0, y1), (0.0, top))
        ]
        us, vs = zip(*corners, strict=True)

        assert min(us) < occupied.x < max(us)
        assert min(vs) < occupied.y < max(vs)

    def test_adjacent_ring_stays_clear_of_the_box_image(self):
        # The ring is drawn at the marker plane (where the homography is
        # exact); the box's nearest visible edge is its floor edge, imaged
        # inward toward the camera axis.
        scenario = _scenario()
        x0, _, y0, _ = _box(scenario)
        ring_radius_m = 0.15
        adjacent = next(
            c for c in _selection(scenario, _standoff(scenario)).candidates if c.label == "A"
        )
        _, near_edge_v = _marker_plane((x0, y0), 0.0, scenario)

        assert adjacent.y + ring_radius_m < near_edge_v


class TestMap:
    def test_committed_map_matches_scenario_yaml(self):
        scenario = _scenario()
        map_yaml = MAPS_DIR / f"warehouse_map_{scenario.name}.yaml"
        data = yaml.safe_load(map_yaml.read_text())
        committed = np.flipud(np.array(Image.open(map_yaml.parent / data["image"])))

        assert data["image"] == f"warehouse_map_{scenario.name}.pgm"
        assert data["resolution"] == pytest.approx(RESOLUTION_M)
        assert data["origin"][:2] == [-6.0, -4.0]
        assert np.array_equal(committed, _grid(scenario))

    def test_map_bakes_the_corridor_not_the_box(self):
        scenario = _scenario()
        cfg = WarehouseConfig()
        grid = _grid(scenario)
        (box,) = scenario.timed_obstacles
        barrier = scenario.aisle_barrier

        assert grid[_cell(box.pose.x, box.pose.y, cfg)] == 255
        assert grid[_cell(barrier.center_x_m, 0.4, cfg)] == 0
        assert grid[_cell(barrier.center_x_m, -0.4, cfg)] == 0

    def test_robot_lanes_are_free_in_generated_map(self):
        scenario = _scenario()
        cfg = WarehouseConfig()
        grid = _grid(scenario)

        for robot in scenario.robots:
            lo, hi = sorted((robot.spawn.x, robot.goal.x))
            for x in np.arange(lo, hi + 1e-9, RESOLUTION_M):
                assert grid[_cell(x, robot.spawn.y + 1e-6, cfg)] == 255, (robot.robot_id, x)


class TestOracle:
    def test_oracle_avoids_the_occupied_candidate_and_contrasts_classical(self):
        oracle = _scenario().oracle

        assert (oracle.yielder, oracle.passer) == ("robot_1", "robot_2")
        assert oracle.occupied_candidate == "C"
        assert oracle.correct_candidates == ("A", "B")
        assert oracle.contrasts_classical is True

    def test_chance_of_avoidance_is_two_thirds(self):
        # Flagged: rev 8.6 tests >= 9/15 against chance 1/3, the rate of one
        # specific candidate; "avoid the occupied one" has chance 2/3.
        assert _scenario().oracle.chance_rate == pytest.approx(2 / 3)

    def test_oracle_rejects_an_occupied_candidate_marked_correct(self):
        with pytest.raises(ValidationError, match="cannot also be correct"):
            RetreatOracleConfig(
                yielder="robot_1", passer="robot_2", candidate_count=3,
                occupied_candidate="C", correct_candidates=("A", "C"),
                classical_candidate="C", rationale="x",
            )

    def test_oracle_rejects_labels_that_miss_the_candidate_set(self):
        with pytest.raises(ValidationError, match="exactly"):
            RetreatOracleConfig(
                yielder="robot_1", passer="robot_2", candidate_count=3,
                occupied_candidate="C", correct_candidates=("A",),
                classical_candidate="C", rationale="x",
            )

    def test_scenario_rejects_an_oracle_yielder_it_does_not_have(self):
        data = yaml.safe_load(SCENARIO_PATH.read_text())
        data["oracle"]["yielder"] = "robot_9"
        from isaac.vgu_sim.config import ScenarioConfig

        with pytest.raises(ValidationError, match="robot_9"):
            ScenarioConfig.model_validate(data)


class TestM5Settings:
    def test_orchestrator_goal_table_lists_the_t3b_settings(self):
        text = ORCHESTRATOR_YAML.read_text()

        assert "obstacle_in_candidate (T3b, junction head-on) -> +-2.5 as written" in text
        assert "center_m: 1.2, half_length_m: 0.8" in text
        assert f"grounding_aisle_y_band_m: [{BAND_M[0]}, {BAND_M[1]}]" in text

    def test_scenario_header_states_the_same_band(self):
        assert f"grounding_aisle_y_band_m: [{BAND_M[0]}, {BAND_M[1]}]" in SCENARIO_PATH.read_text()

    def test_shipped_goals_are_the_scenario_goals(self):
        tasks = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["initial_tasks"]

        for robot in _scenario().robots:
            assert tuple(tasks[robot.robot_id]["goal"]) == (robot.goal.x, robot.goal.y)

    def test_mock_decision_yields_the_oracle_yielder_once(self):
        first, *rest = json.loads(MOCK_PATH.read_text())
        decision = CongestionDecision.model_validate(first)
        oracle = _scenario().oracle

        assert decision.strategy == "yield"
        assert decision.yield_robot == oracle.yielder
        assert set(decision.involved_robots) == {oracle.yielder, oracle.passer}
        assert [CongestionDecision.model_validate(d).strategy for d in rest] == ["none"]

"""Tests for the v3 S1b pilot scene (`mapd_5_s1b`) and its S1b-only config.

Pins the authored S1b design (prereg-v3 R3.6 + R3.6a; header of
isaac/config/scenarios/mapd_5_s1b.yaml): the tracked band is cleared of the
four rack quadrants and carries two 0.55 x 1.60 rack islands; every corridor
is >= 0.90 m (the latch-aware bound); the committed Nav2 map regenerates
byte for byte; spawns and first goals are the S1 seed draws (S1a's labels
and forbidden pair, so S1a and S1b draw the same stream per seed); the M5
overlay snippet stays in lockstep with the robots and loads into the real M5
config with the recomputed sim-time stagger; and the S1b-only grounding file
differs from the S1a file in the two aisle bands only.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from swarm_orchestrator.models import load_config
from swarm_orchestrator.reasoning_pipeline import load_grounding_source
from swarm_orchestrator.task_stream import (
    build_task_stream_plan,
    draw_start_nodes,
    draw_task_sequences,
)

from isaac.scripts.generate_warehouse_map import (
    build_occupancy_grid,
    load_scenario,
    world_to_cell,
)
from isaac.vgu_sim.config import ScenarioConfig, WarehouseConfig
from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = REPO_ROOT / "isaac/config/scenarios"
S1B = SCENARIOS / "mapd_5_s1b.yaml"
S1A = SCENARIOS / "mapd_5.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCH = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
SEEDS_FILE = REPO_ROOT / "config/s1_seeds.yaml"
S1B_GROUNDING = REPO_ROOT / "config/grounding/s1b_dynamic.yaml"
S1A_GROUNDING = REPO_ROOT / "config/grounding/s1_dynamic.yaml"
RES = 0.05

NODE_POSES = {
    "Wp": (-2.3, 1.2, 0.0),
    "Wm": (-2.3, -1.2, 0.0),
    "N": (0.05, 1.55, -math.pi / 2),
    "S": (0.05, -1.55, math.pi / 2),
    "E": (2.3, 0.0, math.pi),
}
NODES_XY = {node: (x, y) for node, (x, y, _) in NODE_POSES.items()}
FORBIDDEN = [("Wp", "Wm")]
ROBOTS = [f"robot_{n}" for n in range(1, 6)]
# (x0, x1, y0, y1) of the two islands, west then east.
ISLANDS = [(-1.30, -0.75, -0.70, 0.90), (0.25, 0.80, -0.90, 0.70)]
BAND = (-2.5, 2.5, -1.8, 1.8)


def _raw() -> dict:
    return yaml.safe_load(S1B.read_text())


def _scenario() -> ScenarioConfig:
    return load_scenario(S1B)


def _overlay(path: Path = S1B) -> dict:
    lines = path.read_text().splitlines()
    begin = lines.index("#   --- M5 overlay begin ---")
    end = lines.index("#   --- M5 overlay end ---")
    assert all(line.startswith("#   ") for line in lines[begin + 1 : end])
    return yaml.safe_load("\n".join(line[4:] for line in lines[begin + 1 : end]))


def _grid() -> np.ndarray:
    scenario = _scenario()
    grid, _ = build_occupancy_grid(
        WarehouseConfig(),
        obstacles=[],
        resolution_m=RES,
        static_obstacles=scenario.static_obstacles,
        rack_clearance=scenario.rack_clearance,
    )
    return grid


def _occupied(grid: np.ndarray, x: float, y: float) -> bool:
    row, col = world_to_cell(x, y, WarehouseConfig(), RES)
    return grid[row, col] == 0


class TestScenarioYaml:
    def test_scenario_validates_as_a_five_robot_cell(self):
        scenario = _scenario()
        assert scenario.name == "mapd_5_s1b"
        assert [r.robot_id for r in scenario.robots] == ROBOTS
        assert [r.marker_id for r in scenario.robots] == [1, 2, 3, 4, 5]

    def test_scenario_name_matches_its_file(self):
        assert S1B.stem == _scenario().name

    def test_pilot_only_marking_is_present(self):
        assert "PILOT-ONLY -- DO NOT COLLECT" in S1B.read_text()

    def test_duration_is_s1as_horizon(self):
        assert _scenario().duration_sec == load_scenario(S1A).duration_sec == 600.0

    def test_spawns_cover_the_five_task_nodes_with_their_yaws(self):
        spawns = {(r.spawn.x, r.spawn.y): r.spawn.yaw_rad for r in _scenario().robots}
        assert spawns == {(x, y): pytest.approx(yaw) for x, y, yaw in NODE_POSES.values()}

    def test_spawn_assignment_is_the_seed_draw(self):
        scenario = _scenario()
        drawn = draw_start_nodes(scenario.seed, ROBOTS, NODES_XY)
        actual = {
            r.robot_id: next(n for n, xy in NODES_XY.items() if (r.spawn.x, r.spawn.y) == xy)
            for r in scenario.robots
        }
        assert actual == drawn

    def test_goals_are_each_robots_first_drawn_task(self):
        scenario = _scenario()
        starts = draw_start_nodes(scenario.seed, ROBOTS, NODES_XY)
        sequences = draw_task_sequences(scenario.seed, starts, NODES_XY, 5, FORBIDDEN)
        for robot in scenario.robots:
            assert (robot.goal.x, robot.goal.y) == NODES_XY[sequences[robot.robot_id][0]]

    def test_initial_task_is_the_first_alternation_label(self):
        assert all(r.initial_task == "pickup" for r in _scenario().robots)

    def test_rack_clearance_is_the_tracked_band(self):
        rc = _scenario().rack_clearance
        assert rc is not None
        assert (rc.x_min_m, rc.x_max_m, rc.y_min_m, rc.y_max_m) == BAND
        assert _scenario().loop_map is None
        assert _scenario().aisle_barrier is None
        assert _scenario().timed_obstacles == ()

    def test_islands_are_two_low_c55_boxes(self):
        obstacles = _scenario().static_obstacles
        assert [o.obstacle_id for o in obstacles] == ["obstacle_1", "obstacle_2"]
        boxes = [
            (
                o.pose.x - o.size.x_m / 2,
                o.pose.x + o.size.x_m / 2,
                o.pose.y - o.size.y_m / 2,
                o.pose.y + o.size.y_m / 2,
            )
            for o in obstacles
        ]
        assert boxes == [pytest.approx(b) for b in ISLANDS]
        for o in obstacles:
            assert (o.size.x_m, o.size.y_m) == (0.55, 1.6)
            assert o.pose.yaw_rad == 0.0
            # Above the 0.182 m lidar plane, low enough for a <= 0.05 m camera shadow.
            assert 0.182 < o.size.z_m <= 0.3

    def test_rack_coverage_is_about_ten_percent_of_the_band(self):
        area = sum((x1 - x0) * (y1 - y0) for x0, x1, y0, y1 in ISLANDS)
        assert area / 18.0 == pytest.approx(0.0978, abs=5e-4)

    def test_every_corridor_meets_the_latch_aware_bound(self):
        (ax0, ax1, ay0, ay1), (bx0, bx1, by0, by1) = ISLANDS
        gaps = [
            ax0 - BAND[0],
            bx0 - ax1,
            BAND[1] - bx1,
            BAND[3] - ay1,
            ay0 - BAND[2],
            BAND[3] - by1,
            by0 - BAND[2],
        ]
        # W_min = 0.45 latch + 2 * (0.09 half-width + 0.10 inflation) + 0.05 cell.
        assert min(gaps) == pytest.approx(0.90)
        assert all(g >= 0.88 - 1e-9 for g in gaps)

    def test_nodes_sit_inside_the_s1a_envelope_off_the_islands(self):
        for x, y in NODES_XY.values():
            assert abs(x) <= 2.3 and abs(y) <= 1.55
            for x0, x1, y0, y1 in ISLANDS:
                dx = max(x0 - x, 0.0, x - x1)
                dy = max(y0 - y, 0.0, y - y1)
                assert math.hypot(dx, dy) >= 0.5
        assert (-1.75, 0.0) not in NODES_XY.values()

    def test_no_node_sits_in_another_nodes_handoff_radius(self):
        pts = list(NODES_XY.values())
        dmin = min(math.dist(a, b) for i, a in enumerate(pts) for b in pts[i + 1 :])
        assert dmin == pytest.approx(2.376, abs=1e-3)
        assert dmin > 4 * 0.5

    def test_labels_and_forbidden_pair_are_s1as(self):
        s1a = _overlay(S1A)["task_stream"]
        s1b = _overlay()["task_stream"]
        assert set(s1a["nodes"]) == set(s1b["nodes"])
        assert s1a["forbidden_legs"] == s1b["forbidden_legs"]

    @pytest.mark.parametrize("index", range(5))
    def test_seed_draws_are_identical_on_both_floors(self, index):
        # Lockstep: the same seed draws the same abstract task stream on S1a
        # and S1b (labels and forbidden list are S1a's; positions differ).
        seed = yaml.safe_load(SEEDS_FILE.read_text())["seeds"][index]
        s1a_nodes = _overlay(S1A)["task_stream"]["nodes"]
        a_starts = draw_start_nodes(seed, ROBOTS, s1a_nodes)
        b_starts = draw_start_nodes(seed, ROBOTS, NODES_XY)
        assert a_starts == b_starts
        assert draw_task_sequences(seed, a_starts, s1a_nodes, 5, FORBIDDEN) == (
            draw_task_sequences(seed, b_starts, NODES_XY, 5, FORBIDDEN)
        )

    def test_expected_conflict_is_the_schema_placeholder_over_all_robots(self):
        conflict = _scenario().expected_conflict
        assert conflict is not None
        assert set(conflict.involved_robots) == set(ROBOTS)
        assert conflict.onset_window_sec[1] <= _scenario().duration_sec


class TestMap:
    def test_grid_equals_the_committed_s1b_map_byte_for_byte(self):
        committed = np.array(Image.open(MAPS_DIR / "warehouse_map_mapd_5_s1b.pgm"))
        assert np.array_equal(_grid(), committed)

    def test_map_yaml_points_at_its_image_with_the_shared_origin(self):
        data = yaml.safe_load((MAPS_DIR / "warehouse_map_mapd_5_s1b.yaml").read_text())
        assert data["image"] == "warehouse_map_mapd_5_s1b.pgm"
        assert data["resolution"] == RES
        assert data["origin"] == [-6.0, -4.0, 0.0]

    def test_band_is_free_except_the_islands(self):
        grid = _grid()
        for x in np.arange(-2.45, 2.46, 0.1):
            for y in np.arange(-1.75, 1.76, 0.1):
                in_island = any(
                    x0 - 0.05 <= x <= x1 + 0.05 and y0 - 0.05 <= y <= y1 + 0.05
                    for x0, x1, y0, y1 in ISLANDS
                )
                if not in_island:
                    assert not _occupied(grid, x, y), (x, y)

    def test_island_cores_are_occupied(self):
        grid = _grid()
        for x0, x1, y0, y1 in ISLANDS:
            assert _occupied(grid, (x0 + x1) / 2, (y0 + y1) / 2)
            assert _occupied(grid, x0 + 0.05, y0 + 0.05)

    def test_racks_remain_outside_the_band(self):
        grid = _grid()
        for x, y in [(-2.6, 1.0), (2.6, -1.0), (-1.5, 1.9), (1.5, -1.9), (4.0, 3.0)]:
            assert _occupied(grid, x, y), (x, y)

    def test_aisle_stubs_stay_open_as_in_s1a(self):
        grid = _grid()
        for x, y in [(-3.0, 0.0), (3.0, 0.0), (0.0, 2.2), (0.0, -2.2)]:
            assert not _occupied(grid, x, y), (x, y)


class TestOverlaySnippet:
    def test_roster_matches_the_robots(self):
        tasks = _overlay()["initial_tasks"]
        robots = {r.robot_id: r for r in _scenario().robots}
        assert set(tasks) == set(robots)
        for rid, spec in tasks.items():
            assert tuple(spec["goal"]) == (robots[rid].goal.x, robots[rid].goal.y)
            assert spec["task"] == robots[rid].initial_task

    def test_stream_block_matches_the_design(self):
        stream = _overlay()["task_stream"]
        assert stream["enabled"] is True
        assert stream["seed"] == _scenario().seed
        assert {k: tuple(v) for k, v in stream["nodes"].items()} == NODES_XY
        assert stream["tasks_per_robot"] == 5
        assert [tuple(leg) for leg in stream["forbidden_legs"]] == FORBIDDEN
        assert stream["dwell_sim_sec"] == 5.0
        assert stream["horizon_sim_sec"] == _scenario().duration_sec
        assert stream["finished_mode"] == "park"

    def test_pinned_start_nodes_equal_the_spawn_assignment_and_the_draw(self):
        stream = _overlay()["task_stream"]
        assert stream["start_nodes"] == draw_start_nodes(stream["seed"], ROBOTS, NODES_XY)
        spawns = {r.robot_id: (r.spawn.x, r.spawn.y) for r in _scenario().robots}
        assert {rid: NODES_XY[n] for rid, n in stream["start_nodes"].items()} == spawns

    def test_release_stagger_is_the_recomputed_sim_delta(self):
        # R3.6a: Delta is recomputed for the S1b legs:
        # 4 Delta < (L_min - 0.45) / v with L_min = 2.376 (Wp-N / Wm-S).
        stream = _overlay()["task_stream"]
        assert stream["release_stagger_sim_sec"] == 3.0
        assert "release_stagger_wall_sec" not in stream
        bound = (2.376 - 0.45) / 0.15 / 4.0
        assert stream["release_stagger_sim_sec"] < bound

    def test_snippet_loads_into_the_m5_config_and_replans_the_draw(self):
        raw = yaml.safe_load(ORCH.read_text())
        raw.update(_overlay())
        config = load_config(raw)
        assert config.grounding_params_path == "config/grounding/s1b_dynamic.yaml"
        assert config.grounding_yield_feasibility == "swap"
        assert config.dispatch_enabled is True
        assert config.plan_channel_enabled is True
        assert config.prompt_static_obstacles is False
        assert config.refusal_no_action is True
        assert config.reanalysis_suppression.enabled is True
        assert config.scenario_geometry is not None
        assert config.scenario_geometry.arms is None
        plan = build_task_stream_plan(config.task_stream, config.initial_tasks)
        assert plan.start_nodes_drawn is False
        assert plan.tasks_total == 25
        sequences = draw_task_sequences(plan.seed, plan.start_nodes, NODES_XY, 5, FORBIDDEN)
        assert {rid: tuple(t.node for t in q) for rid, q in plan.tasks.items()} == sequences
        assert config.task_stream.release_clock == "sim"
        assert plan.release_offsets_sim_sec == {rid: i * 3.0 for i, rid in enumerate(ROBOTS)}

    def test_declared_corridor_is_s1as_box(self):
        # aisle_half_width_m sets the dynamic-lane sidestep (0.6 - 0.24 = 0.36).
        assert _overlay()["scenario_geometry"]["corridor"] == {
            **_overlay(S1A)["scenario_geometry"]["corridor"],
            "occluder_height_m": 0.3,
        }

    def test_static_obstacles_declare_the_islands_and_band_fences(self):
        boxes = _overlay()["static_obstacles"]
        assert len(boxes) == 6
        assert all(b["obstacle_id"].startswith("obstacle_") for b in boxes)
        scenario_islands = {
            (o.pose.x, o.pose.y, o.size.x_m, o.size.y_m) for o in _scenario().static_obstacles
        }
        declared = {(b["x"], b["y"], b["size_x_m"], b["size_y_m"]) for b in boxes}
        assert scenario_islands <= declared
        fences = declared - scenario_islands
        assert fences == {
            (-2.75, 0.0, 0.5, 4.6),
            (2.75, 0.0, 0.5, 4.6),
            (0.0, 2.05, 5.0, 0.5),
            (0.0, -2.05, 5.0, 0.5),
        }
        # Each fence starts exactly on a band edge.
        for x, y, sx, sy in fences:
            edges = {round(abs(x) - sx / 2, 6), round(abs(y) - sy / 2, 6)}
            assert 2.5 in edges or 1.8 in edges


class TestGroundingParamsFile:
    def test_s1b_file_loads_with_dynamic_arms_on(self):
        source = load_grounding_source(S1B_GROUNDING)
        assert source.section_present is True
        assert source.params.dynamic_scene_arms is True
        assert source.params.escort_turn_cap is True

    def test_s1b_bands_are_the_tracked_band_minus_the_chassis_margin(self):
        params = load_grounding_source(S1B_GROUNDING).params
        assert params.aisle_y_band_m == pytest.approx((-1.66, 1.66))
        assert params.aisle_x_band_m == pytest.approx((-2.36, 2.36))

    def test_only_the_bands_differ_from_the_s1a_file(self):
        s1b = yaml.safe_load(S1B_GROUNDING.read_text())["grounding"]
        s1a = yaml.safe_load(S1A_GROUNDING.read_text())["grounding"]
        assert set(s1b) == set(s1a)
        assert {k for k in s1a if s1a[k] != s1b[k]} == {"aisle_y_band_m", "aisle_x_band_m"}

    def test_overlay_points_at_the_s1b_file_never_rag_yaml(self):
        assert _overlay()["grounding_params_path"] == "config/grounding/s1b_dynamic.yaml"
        shipped = yaml.safe_load(ORCH.read_text())
        assert shipped["shadow_classical_params_path"] == "config/rag.yaml"
        assert "shadow_classical_params_path" not in _overlay()


def _ground(poses, goals, yielder, grounding_file: Path) -> dict:
    raw = yaml.safe_load(ORCH.read_text())
    raw.update(_overlay())
    config = load_config(raw)
    frame = SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=r, x=x, y=y, theta=t, goal=goals[r])
            for r, (x, y, t) in poses.items()
        ],
    )
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=list(poses),
        root_cause="standoff",
        strategy="yield",
        justification="jam",
        yield_robot=yielder,
    )
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    result = ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)
    return ground_reasoner_result(
        result,
        robot_positions={r: (x, y) for r, (x, y, _) in poses.items()},
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        snapshot=frame,
        params=load_grounding_source(grounding_file).params,
    )


# Head-on in the 1.10 m island_w <-> south-wall gap: robot_1 S -> Wp
# westbound, robot_2 Wm -> S eastbound, 0.40 m apart.
_SOUTH_GAP = {"robot_1": (-0.8, -1.25, math.pi), "robot_2": (-1.2, -1.25, 0.0)}
_SOUTH_GOALS = {"robot_1": NODES_XY["Wp"], "robot_2": NODES_XY["S"]}


class TestGroundingOnTheS1bFloor:
    def test_s1b_bands_ground_an_executable_yield_in_a_shared_gap(self):
        command = _ground(_SOUTH_GAP, _SOUTH_GOALS, "robot_1", S1B_GROUNDING)
        action = command["actions"][0]
        assert (action["robot_id"], action["action"]) == ("robot_1", "yield")
        params = action["parameters"]
        # Clearance 1.7 from robot_2 0.40 m ahead -> a 1.30 m backup east.
        assert params["backup_distance_m"] == pytest.approx(1.3)
        assert params["pull_off_lateral_m"] == pytest.approx(0.36)
        x, y = params["retreat_x_m"], params["retreat_y_m"]
        assert BAND[0] + 0.14 <= x <= BAND[1] - 0.14
        assert BAND[2] + 0.14 <= y <= BAND[3] - 0.14

    def test_s1a_bands_would_refuse_the_same_scene(self):
        # Why S1b needs its own grounding file: S1a's |y| <= 0.46 band holds
        # every retreat sample inside S1a's aisle, i.e. off this floor's gap.
        command = _ground(_SOUTH_GAP, _SOUTH_GOALS, "robot_1", S1A_GROUNDING)
        assert command["actions"][0]["action"] != "yield"
        assert "retreat=no-valid-candidate" in command["degradations"]

"""Tests for the v3 S1 pilot scene (`mapd_5`) and its S1-only config artifacts.

Pins the authored design of docs/superpowers/specs/2026-10-06-v3-scene-design.md
"S1" (feat/v3-design) and the prereg-v3 A11/A11(iii) overlay prerequisites:
the floor is B1's byte for byte (MAP_SCENARIO=bottleneck_merge), the spawns
and first goals are SEED-DERIVED from the registered list via the repo's own
task-stream draws, the M5 overlay snippet in the yaml header stays in
lockstep with the robots and loads into the real M5 config (the S6 hand-sync
pattern), the S1-only grounding file turns dynamic_scene_arms on WITHOUT
touching the md5-pinned config/rag.yaml, and the registered 100-seed list
regenerates deterministically to its committed digest.
"""
from __future__ import annotations

import hashlib
import math
import random
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

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, load_scenario
from isaac.vgu_sim.config import ScenarioConfig, WarehouseConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = REPO_ROOT / "isaac/config/scenarios"
MAPD = SCENARIOS / "mapd_5.yaml"
B1 = SCENARIOS / "bottleneck_merge.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCH = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
SEEDS_FILE = REPO_ROOT / "config/s1_seeds.yaml"
GROUNDING_FILE = REPO_ROOT / "config/grounding/s1_dynamic.yaml"
RES = 0.05

# Scene design S1 "Layout": node -> (x, y, spawn yaw).
NODE_POSES = {
    "Wp": (-2.3, 0.35, 0.0),
    "Wm": (-2.3, -0.35, 0.0),
    "N": (0.0, 1.55, -math.pi / 2),
    "S": (0.0, -1.55, math.pi / 2),
    "E": (2.3, 0.0, math.pi),
}
NODES_XY = {node: (x, y) for node, (x, y, _) in NODE_POSES.items()}
FORBIDDEN = [("Wp", "Wm")]
ROBOTS = [f"robot_{n}" for n in range(1, 6)]


def _raw() -> dict:
    return yaml.safe_load(MAPD.read_text())


def _scenario() -> ScenarioConfig:
    return load_scenario(MAPD)


def _seeds() -> dict:
    return yaml.safe_load(SEEDS_FILE.read_text())


def _overlay() -> dict:
    lines = MAPD.read_text().splitlines()
    begin = lines.index("#   --- M5 overlay begin ---")
    end = lines.index("#   --- M5 overlay end ---")
    block = [line[4:] if line != "#" else "" for line in lines[begin + 1:end]]
    assert all(line.startswith("#   ") for line in lines[begin + 1:end])
    return yaml.safe_load("\n".join(block))


class TestScenarioYaml:
    def test_scenario_validates_as_a_five_robot_cell(self):
        scenario = _scenario()
        assert scenario.name == "mapd_5"
        assert [r.robot_id for r in scenario.robots] == ROBOTS
        assert [r.marker_id for r in scenario.robots] == [1, 2, 3, 4, 5]

    def test_scenario_name_matches_its_file(self):
        assert MAPD.stem == _scenario().name

    def test_pilot_only_marking_is_present(self):
        text = MAPD.read_text()
        assert "PILOT-ONLY -- DO NOT COLLECT" in text

    def test_duration_is_the_registered_horizon(self):
        assert _scenario().duration_sec == 600.0

    def test_spawns_cover_the_five_task_nodes_with_their_yaws(self):
        spawns = {(r.spawn.x, r.spawn.y): r.spawn.yaw_rad for r in _scenario().robots}
        assert spawns == {
            (x, y): pytest.approx(yaw) for x, y, yaw in NODE_POSES.values()
        }

    def test_spawn_assignment_is_the_seed_draw(self):
        scenario = _scenario()
        drawn = draw_start_nodes(scenario.seed, ROBOTS, NODES_XY)
        actual = {
            r.robot_id: next(
                node for node, (x, y) in NODES_XY.items()
                if (r.spawn.x, r.spawn.y) == (x, y)
            )
            for r in scenario.robots
        }
        assert actual == drawn

    def test_goals_are_each_robots_first_drawn_task(self):
        scenario = _scenario()
        starts = draw_start_nodes(scenario.seed, ROBOTS, NODES_XY)
        sequences = draw_task_sequences(scenario.seed, starts, NODES_XY, 5, FORBIDDEN)
        for robot in scenario.robots:
            assert (robot.goal.x, robot.goal.y) == NODES_XY[sequences[robot.robot_id][0]]

    def test_drawn_sequences_never_use_a_forbidden_leg(self):
        scenario = _scenario()
        starts = draw_start_nodes(scenario.seed, ROBOTS, NODES_XY)
        sequences = draw_task_sequences(scenario.seed, starts, NODES_XY, 5, FORBIDDEN)
        forbidden = {frozenset(leg) for leg in FORBIDDEN}
        for rid, seq in sequences.items():
            legs = list(zip((starts[rid],) + seq, seq))
            assert all(a != b and frozenset((a, b)) not in forbidden for a, b in legs)

    def test_initial_task_is_the_first_alternation_label(self):
        assert all(r.initial_task == "pickup" for r in _scenario().robots)

    def test_floor_is_b1s_gate_block_verbatim(self):
        assert _raw()["aisle_barrier"] == yaml.safe_load(B1.read_text())["aisle_barrier"]
        assert "loop_map" not in _raw()
        assert _scenario().static_obstacles == ()
        assert _scenario().timed_obstacles == ()

    def test_grid_equals_the_committed_b1_map_byte_for_byte(self):
        scenario = _scenario()
        grid, _ = build_occupancy_grid(
            WarehouseConfig(), obstacles=[], resolution_m=RES,
            aisle_barrier=scenario.aisle_barrier, loop_map=scenario.loop_map,
        )
        committed = np.array(Image.open(MAPS_DIR / "warehouse_map_bottleneck_merge.pgm"))
        assert np.array_equal(grid, committed)

    def test_expected_conflict_is_the_schema_placeholder_over_all_robots(self):
        conflict = _scenario().expected_conflict
        assert conflict is not None
        assert set(conflict.involved_robots) == set(ROBOTS)
        assert conflict.onset_window_sec[1] <= _scenario().duration_sec


class TestOverlaySnippet:
    def test_roster_matches_the_robots(self):
        tasks = _overlay()["initial_tasks"]
        robots = {r.robot_id: r for r in _scenario().robots}
        assert set(tasks) == set(robots)
        for rid, spec in tasks.items():
            assert tuple(spec["goal"]) == (robots[rid].goal.x, robots[rid].goal.y)
            assert spec["task"] == robots[rid].initial_task

    def test_stream_block_matches_the_scene_design(self):
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
        drawn = draw_start_nodes(stream["seed"], ROBOTS, NODES_XY)
        assert stream["start_nodes"] == drawn
        spawns = {r.robot_id: (r.spawn.x, r.spawn.y) for r in _scenario().robots}
        assert {rid: NODES_XY[node] for rid, node in stream["start_nodes"].items()} == spawns

    def test_release_stagger_wall_value_covers_the_registered_delta(self):
        # Registered Delta = 4 sim-s; wall value 4 / RTF_pilot with the
        # EXTRAPOLATED 5-stack RTF 0.15-0.19 -> 21.1-26.7 wall-s (provisional
        # until the RTF pilot re-derives it; the C9 pattern).
        stagger = _overlay()["task_stream"]["release_stagger_wall_sec"]
        assert 4.0 / 0.19 <= stagger <= 4.0 / 0.15

    def test_snippet_loads_into_the_m5_config_and_replans_the_draw(self):
        raw = yaml.safe_load(ORCH.read_text())
        raw.update(_overlay())
        config = load_config(raw)
        assert config.grounding_params_path == "config/grounding/s1_dynamic.yaml"
        assert config.grounding_yield_feasibility == "swap"
        assert config.dispatch_enabled is True
        assert config.plan_channel_enabled is True
        assert config.prompt_static_obstacles is False
        assert config.scenario_geometry is not None
        assert config.scenario_geometry.arms is None
        plan = build_task_stream_plan(config.task_stream, config.initial_tasks)
        assert plan.start_nodes_drawn is False
        assert plan.tasks_total == 25
        sequences = draw_task_sequences(
            plan.seed, plan.start_nodes, NODES_XY, 5, FORBIDDEN)
        assert {rid: tuple(t.node for t in q) for rid, q in plan.tasks.items()} == sequences
        assert [t.label for t in plan.tasks["robot_1"]] == [
            "pickup", "delivery", "pickup", "delivery", "pickup"]
        stagger = config.task_stream.release_stagger_wall_sec
        assert plan.release_offsets_wall_sec == {
            rid: i * stagger for i, rid in enumerate(ROBOTS)}

    def test_static_obstacles_declare_the_racks_and_gate_blocks(self):
        boxes = _overlay()["static_obstacles"]
        assert len(boxes) == 6
        centers = {(b["x"], b["y"]) for b in boxes}
        assert {(-1.55, 1.2), (1.55, 1.2), (-1.55, -1.2), (1.55, -1.2)} <= centers
        gate = [b for b in boxes if b["x"] == 1.2]
        assert {b["y"] for b in gate} == {0.4375, -0.4375}
        # Gate blocks reproduce the A55-E barrier: x in [0.7, 1.7],
        # |y| in [0.275, 0.6] (effective width 0.55 against the 0.6 wall).
        for b in gate:
            assert (b["size_x_m"], b["size_y_m"]) == (1.0, 0.325)
        # Neutral ids only (standing rule: never name role or side).
        assert all(b["obstacle_id"].startswith("obstacle_") for b in boxes)


class TestGroundingParamsFile:
    def test_s1_file_loads_with_dynamic_arms_on(self):
        source = load_grounding_source(GROUNDING_FILE)
        assert source.section_present is True
        assert source.params.dynamic_scene_arms is True
        assert source.params.mode == "derived"

    def test_s1_file_declares_both_aisle_bands(self):
        params = load_grounding_source(GROUNDING_FILE).params
        assert params.aisle_y_band_m == (-0.46, 0.46)
        assert params.aisle_x_band_m == (-0.46, 0.46)

    def test_shared_keys_are_a_verbatim_copy_of_rag_yaml(self):
        # A rag.yaml tuning change must fail HERE, not silently diverge.
        s1 = yaml.safe_load(GROUNDING_FILE.read_text())["grounding"]
        rag = yaml.safe_load((REPO_ROOT / "config/rag.yaml").read_text())["grounding"]
        extras = set(s1) - set(rag)
        assert extras == {
            "dynamic_scene_arms", "dynamic_handoff_radius_m",
            "aisle_y_band_m", "aisle_x_band_m",
        }
        assert {k: s1[k] for k in rag} == rag

    def test_overlay_points_at_the_s1_file_never_rag_yaml(self):
        assert _overlay()["grounding_params_path"] == "config/grounding/s1_dynamic.yaml"
        # The shipped shadow path (Arm B thresholds) stays on rag.yaml.
        shipped = yaml.safe_load(ORCH.read_text())
        assert shipped["shadow_classical_params_path"] == "config/rag.yaml"
        assert "shadow_classical_params_path" not in _overlay()


class TestSeedList:
    def test_list_regenerates_deterministically_to_its_digest(self):
        data = _seeds()
        rng = random.Random(int.from_bytes(
            hashlib.sha256(data["salt"].encode()).digest()[:8], "big"))
        regenerated = rng.sample(range(1, 2**31), 100)
        assert data["seeds"] == regenerated
        digest = hashlib.sha256(
            ",".join(str(s) for s in regenerated).encode()).hexdigest()
        assert data["sha256_digest"] == digest

    def test_hundred_distinct_seeds_with_twenty_confirmatory(self):
        data = _seeds()
        assert len(data["seeds"]) == 100
        assert len(set(data["seeds"])) == 100
        assert data["confirmatory_count"] == 20

    def test_pilot_scenario_is_authored_on_the_first_registered_seed(self):
        assert _scenario().seed == _seeds()["seeds"][0]
        assert _overlay()["task_stream"]["seed"] == _seeds()["seeds"][0]

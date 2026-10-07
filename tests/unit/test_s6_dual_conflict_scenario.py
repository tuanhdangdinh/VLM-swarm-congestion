"""Tests for the v3 S6 dual-conflict scene (`s6_dual_conflict`).

Pins the authored design of docs/superpowers/specs/2026-10-06-v3-scene-design.md
"S6" (feat/v3-design): the floor is the shipped loop map plus the T1 barrier,
the four poses are the spec's, the committed Nav2 map regenerates byte for
byte, the PROPOSED decision-level oracle loads and scores mechanically, and
the M5 overlay snippet in the yaml header agrees with the robots' goals (the
hand-sync trap). The offline feasibility script's structural verdicts are
pinned here; its numbers are recorded in the hand-off report, not frozen.
"""
from __future__ import annotations

import subprocess
import sys
import typing
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from swarm_orchestrator.models import load_config

from isaac.scripts.check_s6_feasibility import run_checks
from isaac.scripts.generate_warehouse_map import (
    build_occupancy_grid,
    load_scenario,
    world_to_cell,
)
from isaac.vgu_sim.config import (
    DualConflictOracleConfig,
    OraclePlanLegAction,
    ScenarioConfig,
    WarehouseConfig,
)
from reasoning.vlm.models import PlanLegAction

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = REPO_ROOT / "isaac/config/scenarios"
S6 = SCENARIOS / "s6_dual_conflict.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCH = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
MAP_STEM = "warehouse_map_s6_dual_conflict"
RES = 0.05


def _raw() -> dict:
    return yaml.safe_load(S6.read_text())


def _scenario() -> ScenarioConfig:
    return load_scenario(S6)


def _oracle() -> DualConflictOracleConfig:
    oracle = _scenario().oracle
    assert isinstance(oracle, DualConflictOracleConfig)
    return oracle


class TestScenarioYaml:
    def test_scenario_validates_as_a_four_robot_head_on_cell(self):
        scenario = _scenario()
        assert scenario.name == "s6_dual_conflict"
        assert scenario.family == "head_on"
        assert [r.robot_id for r in scenario.robots] == [
            "robot_1", "robot_2", "robot_3", "robot_4"]

    def test_poses_are_the_spec_table(self):
        poses = {r.robot_id: (r.spawn.x, r.spawn.y, r.spawn.yaw_rad, r.goal.x, r.goal.y)
                 for r in _scenario().robots}
        pi = 3.141592653589793
        assert poses == {
            "robot_1": (-1.5, 0.0, 0.0, 2.5, 0.0),
            "robot_2": (1.5, 0.0, pi, -2.5, 0.0),
            "robot_3": (0.2, 1.2, 0.0, 2.05, 1.2),
            "robot_4": (2.10, 1.2, pi, 0.0, 1.2),
        }

    def test_floor_is_the_shipped_loop_map_plus_the_t1_barrier(self):
        raw = _raw()
        loop = yaml.safe_load((SCENARIOS / "loop_detour_permanent.yaml").read_text())
        t1 = yaml.safe_load((SCENARIOS / "head_on_deadlock.yaml").read_text())
        assert raw["loop_map"] == loop["loop_map"]
        assert raw["aisle_barrier"] == t1["aisle_barrier"]

    def test_no_obstacles_are_authored(self):
        scenario = _scenario()
        assert scenario.timed_obstacles == ()
        assert scenario.static_obstacles == ()

    def test_expected_conflict_lists_both_pairs(self):
        conflict = _scenario().expected_conflict
        assert conflict is not None
        assert conflict.type == "deadlock"
        assert set(conflict.involved_robots) == _oracle().involved_robots


class TestOracle:
    def test_oracle_loads_as_the_proposed_dual_conflict_oracle(self):
        oracle = _oracle()
        assert oracle.criterion_status == "proposed"
        assert oracle.scored_decision == "first_triggered"
        assert oracle.execution_scored is False
        assert [c.involved_robots for c in oracle.conflicts] == [
            ("robot_1", "robot_2"), ("robot_3", "robot_4")]
        assert [c.jam_midpoint_xy for c in oracle.conflicts] == [(0.0, 0.0), (1.15, 1.2)]

    def test_jam_midpoints_are_the_mean_of_each_pairs_spawns(self):
        robots = {r.robot_id: r for r in _scenario().robots}
        for conflict in _oracle().conflicts:
            a, b = (robots[rid] for rid in conflict.involved_robots)
            assert conflict.jam_midpoint_xy == pytest.approx(
                ((a.spawn.x + b.spawn.x) / 2, (a.spawn.y + b.spawn.y) / 2))

    def test_plan_leg_vocabulary_mirrors_the_vlm_contract(self):
        assert typing.get_args(OraclePlanLegAction) == typing.get_args(PlanLegAction)

    def test_addressing_actions_are_every_leg_action_but_continue(self):
        assert set(_oracle().addressing_actions) == (
            set(typing.get_args(PlanLegAction)) - {"continue"})

    def test_plan_with_a_non_continue_leg_in_each_pair_addresses_both(self):
        legs = [("robot_2", "yield"), ("robot_1", "cross"), ("robot_4", "reverse")]
        assert _oracle().addresses_both(legs)

    def test_plan_covering_one_pair_addresses_one_conflict(self):
        legs = [("robot_2", "yield"), ("robot_1", "cross")]
        assert _oracle().conflicts_addressed(legs) == {"A": True, "B": False}
        assert not _oracle().addresses_both(legs)

    def test_continue_legs_do_not_address_a_conflict(self):
        legs = [("robot_2", "yield"), ("robot_3", "continue"), ("robot_4", "continue")]
        assert not _oracle().addresses_both(legs)

    def test_no_plan_addresses_nothing(self):
        assert _oracle().conflicts_addressed([]) == {"A": False, "B": False}

    def test_a_conflict_is_named_only_when_both_members_are_involved(self):
        named = _oracle().conflicts_named(["robot_1", "robot_2", "robot_3"])
        assert named == {"A": True, "B": False}

    def test_oracle_rejects_overlapping_pairs(self):
        raw = _raw()["oracle"]
        raw["conflicts"][1]["involved_robots"] = ["robot_2", "robot_4"]
        with pytest.raises(ValueError, match="disjoint"):
            DualConflictOracleConfig.model_validate(raw)

    def test_oracle_rejects_midpoints_inside_the_separate_event_radius(self):
        raw = _raw()["oracle"]
        raw["separate_event_radius_m"] = 1.7
        with pytest.raises(ValueError, match="separate events"):
            DualConflictOracleConfig.model_validate(raw)

    def test_oracle_rejects_continue_as_an_addressing_action(self):
        raw = _raw()["oracle"]
        raw["addressing_actions"] = ["yield", "continue"]
        with pytest.raises(ValueError, match="continue"):
            DualConflictOracleConfig.model_validate(raw)

    def test_oracle_rejects_a_pair_of_one_robot(self):
        raw = _raw()["oracle"]
        raw["conflicts"][0]["involved_robots"] = ["robot_1", "robot_1"]
        with pytest.raises(ValueError, match="two distinct robots"):
            DualConflictOracleConfig.model_validate(raw)

    def test_oracle_rejects_extra_fields(self):
        raw = {**_raw()["oracle"], "correct_strategy": "yield"}
        with pytest.raises(ValueError):
            DualConflictOracleConfig.model_validate(raw)

    def test_scenario_rejects_an_oracle_robot_that_is_not_configured(self):
        raw = _raw()
        raw["robots"] = raw["robots"][:3]
        raw["expected_conflict"]["involved_robots"] = ["robot_1", "robot_2", "robot_3"]
        with pytest.raises(ValueError, match="robot_4"):
            ScenarioConfig.model_validate(raw)

    def test_scenario_rejects_an_expected_conflict_that_is_not_the_pair_union(self):
        raw = _raw()
        raw["expected_conflict"]["involved_robots"] = ["robot_1", "robot_2"]
        with pytest.raises(ValueError, match="union of the dual conflict pairs"):
            ScenarioConfig.model_validate(raw)


class TestMap:
    def test_map_regenerates_byte_identical(self, tmp_path):
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "isaac/scripts/generate_warehouse_map.py"),
             "--out-dir", str(tmp_path), "--scenario", str(S6)],
            check=True, cwd=REPO_ROOT, capture_output=True,
        )
        for ext in (".pgm", ".yaml"):
            fresh = (tmp_path / f"{MAP_STEM}{ext}").read_bytes()
            assert fresh == (MAPS_DIR / f"{MAP_STEM}{ext}").read_bytes()

    def test_map_yaml_points_at_existing_image(self):
        data = yaml.safe_load((MAPS_DIR / f"{MAP_STEM}.yaml").read_text())
        assert data["image"] == f"{MAP_STEM}.pgm"
        assert (MAPS_DIR / data["image"]).exists()
        assert data["resolution"] == pytest.approx(RES)
        assert data["origin"][:2] == [-6.0, -4.0]

    def test_committed_map_matches_scenario_yaml(self):
        scenario = _scenario()
        expected, _ = build_occupancy_grid(
            WarehouseConfig(), obstacles=[], resolution_m=RES,
            aisle_barrier=scenario.aisle_barrier, loop_map=scenario.loop_map,
        )
        committed = np.array(Image.open(MAPS_DIR / f"{MAP_STEM}.pgm"))
        assert np.array_equal(committed, expected)

    @pytest.mark.parametrize(
        ("x", "y", "value"),
        [
            (0.0, 0.0, 255),     # barrier corridor axis
            (0.0, 0.45, 0),      # barrier north block: seals the N-S strip
            (0.0, -0.45, 0),     # barrier south block
            (0.0, 1.2, 255),     # N-S strip at the second aisle's mouth
            (1.15, 1.2, 255),    # second aisle, B's jam midpoint
            (1.15, 0.75, 0),     # connector-west remnant under the aisle
            (1.8, 0.75, 255),    # connector
            (2.3, 1.2, 0),       # rack east of the second aisle
            (1.15, -1.2, 0),     # SE rack: the carve is on the north side only
        ],
    )
    def test_map_cells_follow_the_s6_floor(self, x, y, value):
        img = np.array(Image.open(MAPS_DIR / f"{MAP_STEM}.pgm"))
        row, col = world_to_cell(x, y, WarehouseConfig(), RES)
        assert int(img[row, col]) == value


def _header_overlay() -> dict:
    lines = S6.read_text().splitlines()
    start = lines.index("#   initial_tasks:")
    block = ["initial_tasks:"]
    for line in lines[start + 1:]:
        if not line.startswith("#     robot_"):
            break
        block.append(line[3:])
    return yaml.safe_load("\n".join(block))


class TestOverlaySnippet:
    def test_snippet_goals_match_the_robots(self):
        tasks = _header_overlay()["initial_tasks"]
        robots = {r.robot_id: r for r in _scenario().robots}
        assert set(tasks) == set(robots)
        for rid, spec in tasks.items():
            assert tuple(spec["goal"]) == (robots[rid].goal.x, robots[rid].goal.y)
            assert spec["task"] == robots[rid].initial_task

    def test_snippet_delays_only_pair_b(self):
        tasks = _header_overlay()["initial_tasks"]
        delays = {rid: spec.get("start_delay_sec", 0.0) for rid, spec in tasks.items()}
        assert delays["robot_1"] == delays["robot_2"] == 0.0
        assert delays["robot_3"] == delays["robot_4"] > 0.0

    def test_snippet_loads_into_the_m5_config(self):
        raw = yaml.safe_load(ORCH.read_text())
        raw["initial_tasks"] = _header_overlay()["initial_tasks"]
        config = load_config(raw)
        assert config.initial_tasks["robot_3"].start_delay_sec == 16.0
        assert config.initial_tasks["robot_4"].goal == (0.0, 1.2)


@pytest.fixture(scope="module")
def feasibility() -> dict[str, object]:
    return {r.name: r for r in run_checks(S6)}


class TestFeasibility:
    @pytest.mark.parametrize(
        "name",
        [
            "committed_map_matches_scenario",
            "poses_inside_tracked_band",
            "marker_stale_zone",
            "markers_unoccluded",
            "spawn_pairwise_floor",
            "solo_path_to_goal",
            "no_detour_round_a_sealed_jam",
            "jam_midpoint_separation",
            "conflict_routes_disjoint",
            "both_jams_formed_by_first_trigger",
        ],
    )
    def test_structural_check_passes(self, feasibility, name):
        assert feasibility[name].passed, feasibility[name].detail

    def test_arm_b_crowding_is_reported_not_hidden(self, feasibility):
        # Open finding, not a pass condition: robot_2 and robot_3 stand
        # inside r_conflict_m at the standoff, so the classical head_on rule
        # sees both pairs as crowded. Flip this pin if the poses change.
        check = feasibility["arm_b_head_on_not_crowded"]
        assert not check.passed
        assert all(k.endswith("robot_2-robot_3") for k in check.detail["within_r_conflict"])

    def test_robot_4_spawn_overlap_is_reported_not_hidden(self, feasibility):
        # Open finding: the chassis box reaches x = 2.202 against the aisle's
        # east end at 2.2. Flip this pin if robot_4's spawn moves.
        check = feasibility["spawn_chassis_clears_occupied_cells"]
        assert not check.passed
        clearance = check.detail["clearance_m"]
        assert [rid for rid, gap in clearance.items() if gap <= 0.0] == ["robot_4"]


def test_scenario_name_matches_its_file():
    assert S6.stem == _scenario().name

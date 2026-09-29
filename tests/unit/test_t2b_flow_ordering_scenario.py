"""Tests for the T2b flow-ordering scenario `t2b_flow_ordering`.

Every geometry claim of the scenario header is recomputed here with M3's and
Arm B's own functions, at the corpus standoff and under the standoff variation
the head-on family showed, the way the T3b scenario pinned its geometry.
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

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, load_scenario
from isaac.vgu_sim.config import WarehouseConfig
from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path
from reasoning.baselines.classical_reasoner import classify_scene, load_classical_params
from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.maneuver_geometry import GroundingParams, load_grounding_params
from reasoning.rag.scene_geometry import SceneGeometry, park_offset_m, passer_clearance_m
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)
from reasoning.vlm.output_parser import parse_decision_text
from scripts.t2b_forced_order import ARMS, T2B_CORRIDOR, T2B_INITIAL_TASKS

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = REPO_ROOT / "isaac/config/scenarios/t2b_flow_ordering.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCHESTRATOR_YAML = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
RESOLUTION_M = 0.05

# M4 safety (swarm_execution config/safety.yaml): distance latch and the STALE
# fail-safe band, both centre to centre on M1 positions.
LATCH_M = 0.45
STALE_BAND_M = 0.6
# M1's position bias near the ROI edge (arrival notes: ~0.1 m).
M1_BIAS_M = 0.1
# Verified M1 tracking extent (head-on family goals at +-2.5; +-3.0 gave 0/146).
TRACKED_ABS_X_M = 2.5
# Standoff variation to tolerate: family separations 0.23-0.98 m, a +-0.2 m
# shift of the meeting point, and the corpus nose-to-nose (+-0.12).
SEPARATIONS_M = (0.24, 0.46, 0.7, 0.98)
SHIFTS_M = (-0.2, -0.1, 0.0, 0.1, 0.2)
ROBOT_3_JITTER_M = (-M1_BIAS_M, 0.0, M1_BIAS_M)


def _scenario():
    return load_scenario(SCENARIO_PATH)


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


def _positions(scenario, separation_m=0.24, shift_m=0.0, robot_3_dx_m=0.0):
    mid = shift_m
    x3 = _robot(scenario, "robot_3").spawn.x + robot_3_dx_m
    return {
        "robot_1": (mid - separation_m / 2, 0.0),
        "robot_2": (mid + separation_m / 2, 0.0),
        "robot_3": (x3, 0.0),
    }


def _grid_cases():
    return itertools.product(SEPARATIONS_M, SHIFTS_M, ROBOT_3_JITTER_M)


def _result(decision: CongestionDecision) -> ReasonerResult:
    return ReasonerResult(
        request_id="req-t2b",
        decision=decision,
        raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="req-t2b", backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


def _mock_decision(arm: str) -> CongestionDecision:
    first = json.loads((REPO_ROOT / ARMS[arm].mock_decision_file).read_text())[0]
    return parse_decision_text(json.dumps(first))


def _legacy(scenario, arm: str, positions) -> dict:
    return ground_reasoner_result(
        _result(_mock_decision(arm)),
        robot_positions=positions,
        geometry=_geometry(scenario),
        params=GroundingParams(mode="legacy"),
    )


def _yield_parameters(command: dict) -> dict:
    (yield_action,) = [a for a in command["actions"] if a["action"] == "yield"]
    return yield_action["parameters"]


class TestScenario:
    def test_three_robots_with_matching_markers(self):
        scenario = _scenario()
        assert [(r.robot_id, r.marker_id) for r in scenario.robots] == [
            ("robot_1", 1), ("robot_2", 2), ("robot_3", 3),
        ]

    def test_marker_assets_exist_for_every_robot(self):
        dictionary = aruco_dict_name(REPO_ROOT / "ros2_ws/src/swarm_perception/config/aruco.yaml")
        for robot in _scenario().robots:
            assert marker_png_path(dictionary, robot.marker_id).is_file(), robot.robot_id

    def test_expected_conflict_stays_the_standoff_pair(self):
        conflict = _scenario().expected_conflict
        assert conflict.involved_robots == ("robot_1", "robot_2")

    def test_oracle_orders_the_west_side_first_with_robot_2_yielding(self):
        oracle = _scenario().oracle
        assert oracle.correct_yielder == "robot_2"
        assert oracle.correct_order == ("robot_1", "robot_3")
        # Corrected 2026-09-29: Arm B's full tie yields robot_2, the oracle's
        # own yielder, so T2b's FCFS contrast is nominally absent (live
        # answers are coin flips around the tie).
        assert oracle.fcfs_yielder == "robot_2"
        assert oracle.contrasts_fcfs is False
        assert oracle.objective == "min_total_time_to_goal"

    def test_margin_frozen_as_censored_lower_bound(self):
        # Frozen 2026-09-29 from harness_20260928_171248 under the
        # user-approved censored-counts-as-dominated rule; the alternative
        # arm ended in the permanent bystander latch on both seeds.
        margin = _scenario().oracle.margin
        assert margin is not None
        assert margin.margin == 0.6485
        assert margin.censored is True
        assert margin.n_per_order == 2
        assert margin.threshold == 0.2
        assert margin.passes


class TestHoldBackPosition:
    """robot_3 at x = -2.45: the constraint table of the scenario header."""

    def test_tracked_by_m1(self):
        x3 = _robot(_scenario(), "robot_3").spawn.x
        assert abs(x3) + 0.05 <= TRACKED_ABS_X_M + 1e-9

    def test_no_latch_against_robot_1_at_spawn(self):
        scenario = _scenario()
        gap = abs(_robot(scenario, "robot_1").spawn.x - _robot(scenario, "robot_3").spawn.x)
        assert gap >= LATCH_M + M1_BIAS_M

    def test_arm_b_sees_a_two_robot_head_on_across_the_standoff_grid(self):
        scenario = _scenario()
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        goals = {r.robot_id: (r.goal.x, r.goal.y) for r in scenario.robots}
        for separation, shift, jitter in _grid_cases():
            positions = _positions(scenario, separation, shift, jitter)
            frame = SnapshotFrame(stamp=30.0, robots=[
                RobotStateInput(robot_id=rid, x=x, y=y,
                                theta=math.pi if rid == "robot_2" else 0.0,
                                linear_velocity=0.0, status="STOPPED", goal=goals[rid])
                for rid, (x, y) in positions.items()
            ])
            verdict = classify_scene([frame], [], params)
            assert verdict.scenario == "head_on", (separation, shift, jitter)
            assert verdict.involved_robots == ["robot_1", "robot_2"]

    def test_binding_bound_is_the_alternative_escort_end(self):
        # The report's band [-2.5, -2.24] was for the 2.0 m corridor; here the
        # alternative order's escort end binds: x3 <= -(P + c) - latch - bias.
        scenario = _scenario()
        geometry = _geometry(scenario)
        bound = -(park_offset_m(geometry) + passer_clearance_m(geometry)) - LATCH_M - M1_BIAS_M
        assert bound == pytest.approx(-2.324, abs=1e-3)
        assert -TRACKED_ABS_X_M <= _robot(scenario, "robot_3").spawn.x <= bound


class TestOracleOrder:
    """Legacy grounding of the oracle arm's mock decision, as the harness runs it."""

    def test_grounds_robot_2_yielding_for_robot_1_then_robot_3(self):
        scenario = _scenario()
        for separation, shift, jitter in _grid_cases():
            command = _legacy(scenario, "oracle", _positions(scenario, separation, shift, jitter))
            p = _yield_parameters(command)
            assert command["actions"][0]["robot_id"] == "robot_2"
            assert p["crossing_order"] == ["robot_1", "robot_3"]

    def test_park_point_is_the_short_corridor_offset(self):
        scenario = _scenario()
        p = _yield_parameters(_legacy(scenario, "oracle", _positions(scenario)))
        assert p["park_x_m"] == pytest.approx(1.124, abs=1e-3)
        assert p["pull_off_lateral_m"] == pytest.approx(0.36)

    def test_every_passer_ends_clear_of_robot_1_at_its_goal(self):
        # M4 drives each passer its own clearance from where it is admitted;
        # both end at park + clearance. robot_1 then drives on to its goal,
        # which must stay out of robot_3's latch and STALE bands.
        scenario = _scenario()
        goal_1 = _robot(scenario, "robot_1").goal.x
        for separation, shift, jitter in _grid_cases():
            positions = _positions(scenario, separation, shift, jitter)
            p = _yield_parameters(_legacy(scenario, "oracle", positions))
            ends = [positions[rid][0] + clear
                    for rid, clear in zip(p["crossing_order"], p["crossing_clear_m"], strict=True)]
            assert max(ends) == pytest.approx(1.774, abs=1e-3)
            assert goal_1 - max(ends) - M1_BIAS_M >= STALE_BAND_M

    def test_robot_3_goal_lies_past_its_escort_end(self):
        scenario = _scenario()
        p = _yield_parameters(_legacy(scenario, "oracle", _positions(scenario)))
        end_3 = _robot(scenario, "robot_3").spawn.x + p["crossing_clear_m"][1]
        goal_3 = _robot(scenario, "robot_3").goal.x
        assert 0.0 <= goal_3 - end_3 <= 0.35
        assert _robot(scenario, "robot_1").goal.x - goal_3 >= LATCH_M + M1_BIAS_M

    def test_hold_backstop_covers_both_escorts(self):
        # 0.1 m/s escorts (Nav2Adapter), both passers in sequence.
        scenario = _scenario()
        p = _yield_parameters(_legacy(scenario, "oracle", _positions(scenario)))
        assert p["hold_sec"] > sum(p["crossing_clear_m"]) / 0.1


class TestAlternativeOrder:
    """Legacy grounding of the alternative arm: robot_1 yields toward robot_3."""

    def test_first_passer_guard_permits_it(self):
        scenario = _scenario()
        for separation, shift, jitter in _grid_cases():
            command = _legacy(
                scenario, "alternative", _positions(scenario, separation, shift, jitter)
            )
            assert command["actions"][0]["action"] == "yield"
            assert command["actions"][0]["robot_id"] == "robot_1"
            assert _yield_parameters(command)["crossing_order"] == ["robot_2", "robot_3"]

    def test_robot_1_reaches_its_park_point_clear_of_robot_3(self):
        scenario = _scenario()
        for separation, shift, jitter in _grid_cases():
            positions = _positions(scenario, separation, shift, jitter)
            p = _yield_parameters(_legacy(scenario, "alternative", positions))
            x3 = positions["robot_3"][0]
            park = (p["park_x_m"], p["pull_off_lateral_m"])
            assert math.dist(park, (x3, 0.0)) - M1_BIAS_M >= STALE_BAND_M
            # The straight backup runs along the lane toward robot_3.
            assert abs(p["park_x_m"] - x3) - M1_BIAS_M >= STALE_BAND_M

    def test_robot_2_escort_end_is_clear_of_the_waiting_robot_3(self):
        scenario = _scenario()
        for separation, shift, jitter in _grid_cases():
            positions = _positions(scenario, separation, shift, jitter)
            p = _yield_parameters(_legacy(scenario, "alternative", positions))
            end_2 = positions["robot_2"][0] - p["crossing_clear_m"][0]
            assert end_2 - positions["robot_3"][0] - M1_BIAS_M >= LATCH_M

    def test_robot_2_goal_sits_on_robot_3_escort_line(self):
        # The predicted latch of the header: robot_3's eastbound escort starts
        # from its hold-back spot straight through robot_2's west goal region.
        scenario = _scenario()
        p = _yield_parameters(_legacy(scenario, "alternative", _positions(scenario)))
        x3 = _robot(scenario, "robot_3").spawn.x
        goal_2 = _robot(scenario, "robot_2").goal
        assert x3 < goal_2.x < x3 + p["crossing_clear_m"][1]
        assert abs(goal_2.y) < LATCH_M


class TestDerivedModeFlags:
    """The shipped derived mode is not what the harness runs; pin why."""

    def _derived(self, scenario, arm: str) -> dict:
        positions = _positions(scenario)
        frame = SnapshotFrame(stamp=30.0, robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=math.pi if rid == "robot_2" else 0.0)
            for rid, (x, y) in positions.items()
        ])
        return ground_reasoner_result(
            _result(_mock_decision(arm)),
            snapshot=frame,
            geometry=_geometry(scenario),
            params=load_grounding_params(REPO_ROOT / "config/rag.yaml"),
        )

    def test_alternative_order_degrades_to_a_reroute(self):
        command = self._derived(_scenario(), "alternative")
        assert command["actions"][0]["action"] == "reroute"
        assert any(tag.startswith("yield=infeasible") for tag in command["degradations"])

    def test_oracle_order_escort_end_lands_inside_robot_1_latch(self):
        scenario = _scenario()
        p = _yield_parameters(self._derived(scenario, "oracle"))
        end_3 = _robot(scenario, "robot_3").spawn.x + p["crossing_clear_m"][1]
        assert _robot(scenario, "robot_1").goal.x - end_3 < LATCH_M


class TestMap:
    def test_committed_map_matches_scenario_yaml(self):
        scenario = _scenario()
        map_yaml = MAPS_DIR / f"warehouse_map_{scenario.name}.yaml"
        data = yaml.safe_load(map_yaml.read_text())
        committed = np.flipud(np.array(Image.open(map_yaml.parent / data["image"])))
        grid, _ = build_occupancy_grid(
            WarehouseConfig(), obstacles=[], resolution_m=RESOLUTION_M,
            aisle_barrier=scenario.aisle_barrier, static_obstacles=scenario.static_obstacles,
        )
        assert data["image"] == f"warehouse_map_{scenario.name}.pgm"
        assert data["origin"][:2] == [-6.0, -4.0]
        assert np.array_equal(committed, grid)

    def test_robot_lanes_are_free_through_the_short_corridor(self):
        scenario = _scenario()
        cfg = WarehouseConfig()
        grid, _ = build_occupancy_grid(
            cfg, obstacles=[], resolution_m=RESOLUTION_M,
            aisle_barrier=scenario.aisle_barrier, static_obstacles=(),
        )
        for robot in scenario.robots:
            lo, hi = sorted((robot.spawn.x, robot.goal.x))
            for x in np.arange(lo, hi + 1e-9, RESOLUTION_M):
                row = int(np.floor((cfg.depth_m / 2 - 1e-6) / RESOLUTION_M))
                col = int(np.floor((x + cfg.width_m / 2) / RESOLUTION_M))
                assert grid[row, col] == 255, (robot.robot_id, x)
        barrier = scenario.aisle_barrier
        row = int(np.floor((cfg.depth_m / 2 - 0.4) / RESOLUTION_M))
        col = int(np.floor((barrier.center_x_m + cfg.width_m / 2) / RESOLUTION_M))
        assert grid[row, col] == 0


class TestM5Settings:
    def test_harness_goals_are_the_scenario_goals(self):
        for robot in _scenario().robots:
            assert T2B_INITIAL_TASKS[robot.robot_id]["goal"] == [robot.goal.x, robot.goal.y]

    def test_harness_corridor_is_the_scenario_barrier(self):
        barrier = _scenario().aisle_barrier
        assert T2B_CORRIDOR["center_m"] == barrier.center_x_m
        assert T2B_CORRIDOR["half_length_m"] == barrier.length_m / 2

    def test_only_robot_3_is_held_back(self):
        delays = {rid: t.get("start_delay_sec", 0.0) for rid, t in T2B_INITIAL_TASKS.items()}
        assert delays == {"robot_1": 0.0, "robot_2": 0.0, "robot_3": 55.0}

    def test_goal_table_and_header_state_the_settings(self):
        table = ORCHESTRATOR_YAML.read_text()
        header = SCENARIO_PATH.read_text()
        assert "t2b_flow_ordering (T2b, three robots)" in table
        assert "start_delay_sec: 55 }" in table
        assert "center_m: 0.0, half_length_m: 0.5" in table
        assert "robot_3.start_delay_sec = 55" in header
        assert "center_m 0.0, half_length_m 0.5" in header

    def test_start_delay_covers_the_trigger_and_precedes_robot_3_turn(self):
        # Corpus (header): standoff 8.2-10.0 sim-s after departure, ~2 wall-s
        # of M5 start-up latency, the 12 wall-s stall window; three-robot RTF
        # at least 0.28 (the four-robot runs measured 0.277-0.310).
        delay = T2B_INITIAL_TASKS["robot_3"]["start_delay_sec"]
        stall_window_sec = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["stall_threshold_sec"]
        for rtf in (0.28, 0.31, 0.34, 0.39):
            trigger = 10.0 / rtf + stall_window_sec + 2.0
            assert trigger + 1.0 < delay, rtf  # + the mock's ~1 s dispatch
            # robot_3's turn: backup + sidestep (>= 15 sim-s) and robot_1's
            # escort (>= 18.9 sim-s) after the dispatch.
            assert trigger + 1.0 + (15.0 + 18.9) / rtf > delay


class TestMockDecisions:
    @pytest.mark.parametrize("arm", sorted(ARMS))
    def test_first_decision_forces_the_arm_then_the_scene_clears(self, arm):
        first, *rest = json.loads((REPO_ROOT / ARMS[arm].mock_decision_file).read_text())
        decision = parse_decision_text(json.dumps(first))
        spec = ARMS[arm]
        assert decision.strategy == "yield"
        assert decision.yield_robot == spec.yielder
        assert [r for r in decision.crossing_order if r != spec.yielder] == list(
            spec.crossing_order
        )
        assert [parse_decision_text(json.dumps(d)).strategy for d in rest] == ["none"]

    def test_the_arms_are_the_oracle_and_its_one_alternative(self):
        oracle = _scenario().oracle
        assert (ARMS["oracle"].yielder, ARMS["oracle"].crossing_order) == (
            oracle.correct_yielder, oracle.correct_order
        )
        assert ARMS["alternative"].yielder in oracle.feasible_yielders
        assert ARMS["alternative"].yielder != oracle.correct_yielder

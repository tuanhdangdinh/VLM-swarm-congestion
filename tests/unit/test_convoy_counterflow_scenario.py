"""Tests for the B3 convoy scene `convoy_counterflow` (unified scene design).

Recomputes the scene header's geometry, timing and Arm B claims with M3's and
Arm B's own functions over the T2b standoff grid (separation x shift x M1
jitter of the held queue, 45 cases), in the standard constraint-check
table's C1-C13 order, plus the vacated-spawn clearance and the omitted-queue
censoring the design registers.
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

from isaac.scripts.generate_warehouse_map import load_scenario
from isaac.vgu_sim.config import OracleConfig
from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path
from reasoning.baselines.classical_reasoner import (
    classify_scene,
    load_classical_params,
    resolve_classical,
)
from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import SceneGeometry, park_offset_m, passer_clearance_m
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)
from reasoning.vlm.output_parser import parse_decision_text

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = REPO_ROOT / "isaac/config/scenarios/convoy_counterflow.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCHESTRATOR_YAML = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
MOCKS = REPO_ROOT / "config/mock_decisions"
CONVOY_MOCK = MOCKS / "convoy_counterflow_convoy_once.json"
ORACLE_MOCK = MOCKS / "convoy_counterflow_oracle_order_once.json"
ALTERNATIVE_MOCK = MOCKS / "convoy_counterflow_alternative_order_once.json"

TRACKED_X_M = 2.5
MARKER_HALF_M = 0.06
LATCH_M = 0.45
LEGAL_GAP_M = 0.55
SPAWN_GAP_M = 0.57
GOAL_STACK_M = 0.60
# R-GOAL-SEP: robot_1/robot_3's own goal-to-goal separation must clear the
# 0.45 m floor plus a 0.15 m margin (Rev 22 B3 goal-table fix). The pre-fix
# stack (+-0.3, 0.6 m apart) sat exactly on this bar with zero headroom --
# the root cause of the latch this fix closes -- so this threshold is chosen
# to fail against that old geometry, not just the new one.
GOAL_SEP_FLOOR_M = LATCH_M + 0.15
R1R3_GOAL_LATERAL_M = 0.36
M1_BIAS_M = 0.1
BACKUP_MPS = 0.09
ESCORT_MPS = 0.10
TRANSIT_MPS = 0.15
SIDESTEP_SIM = 4.0
# Four-stack RTF window, M5 start (sim-s) at four stacks, and the timeline.
RTF_WINDOW = (0.19, 0.21, 0.24, 0.26)
M5_START_SIM = 20.0
STALL_WALL = 12.0
M5_LATENCY_WALL = 2.0
DISPATCH_BUDGET_WALL = 75.0
STANDOFF_SIM = 27.0
HOLD_WALL = 120.0
PREDICTED_MAKESPAN_SIM = 190.0
LEGACY = GroundingParams(mode="legacy")

SEPARATIONS_M = (0.24, 0.46, 0.70)
SHIFTS_M = (-0.2, -0.1, 0.0, 0.1, 0.2)
JITTERS_M = (-M1_BIAS_M, 0.0, M1_BIAS_M)
GRID = list(itertools.product(SEPARATIONS_M, SHIFTS_M, JITTERS_M))
# The cases in which robot_3 crowds the head_on pair (within r_conflict of
# robot_1): 10 of 45.
CROWDED = {
    (0.24, -0.2, 0.1),
    (0.46, -0.2, 0.0), (0.46, -0.2, 0.1), (0.46, -0.1, 0.1),
    (0.70, -0.2, -0.1), (0.70, -0.2, 0.0), (0.70, -0.2, 0.1),
    (0.70, -0.1, 0.0), (0.70, -0.1, 0.1), (0.70, 0.0, 0.1),
}


def _scenario():
    return load_scenario(SCENARIO_PATH)


def _robot(robot_id: str):
    return next(r for r in _scenario().robots if r.robot_id == robot_id)


def _goals() -> dict[str, tuple[float, float]]:
    return {r.robot_id: (r.goal.x, r.goal.y) for r in _scenario().robots}


def _geometry() -> SceneGeometry:
    # The shipped block with the corridor moved to the A55-J barrier.
    data = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"]
    barrier = _scenario().aisle_barrier
    data["corridor"] = {
        **data["corridor"], "center_m": barrier.center_x_m, "half_length_m": barrier.length_m / 2,
    }
    return SceneGeometry(**data)


def _positions(separation=0.24, shift=0.0, jitter=0.0) -> dict[str, tuple[float, float]]:
    return {
        "robot_1": (shift - separation / 2, 0.0),
        "robot_2": (shift + separation / 2, 0.0),
        "robot_3": (_robot("robot_3").spawn.x + jitter, 0.0),
        "robot_4": (_robot("robot_4").spawn.x + jitter, 0.0),
    }


def _frame(positions, held=("robot_3", "robot_4")) -> SnapshotFrame:
    goals = _goals()
    return SnapshotFrame(
        stamp=30.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=math.pi if rid == "robot_2" else 0.0,
                            linear_velocity=0.0, status="STOPPED", goal=goals[rid])
            for rid, (x, y) in positions.items()
        ],
        held_robot_ids=held,
    )


def _result(decision: CongestionDecision) -> ReasonerResult:
    return ReasonerResult(
        request_id="req-b3", decision=decision, raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="req-b3", backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


def _mock(path: Path) -> CongestionDecision:
    return parse_decision_text(json.dumps(json.loads(path.read_text())[0]))


def _legacy(decision: CongestionDecision, positions) -> dict:
    return ground_reasoner_result(
        _result(decision), robot_positions=positions, geometry=_geometry(),
        snapshot=_frame(positions), params=LEGACY,
    )


def _yield_parameters(command: dict) -> dict:
    (action,) = [a for a in command["actions"] if a["action"] == "yield"]
    return action["parameters"]


def _closest_point_on_segment(
    point: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
) -> float:
    """Distance from `point` to its closest point on segment `a`-`b`.

    Args:
        point: The fixed point (a parked robot's goal).
        a: Segment start (a released robot's escort end).
        b: Segment end (that robot's own goal).

    Returns:
        The minimum distance in metres, clamped to the segment (not the
        infinite line).
    """
    ax, ay = a
    bx, by = b
    px, py = point
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.dist((ax + t * dx, ay + t * dy), point)


class TestScenario:
    def test_four_robots_with_matching_markers(self):
        assert [(r.robot_id, r.marker_id) for r in _scenario().robots] == [
            ("robot_1", 1), ("robot_2", 2), ("robot_3", 3), ("robot_4", 4),
        ]

    def test_marker_assets_exist_for_every_robot(self):
        dictionary = aruco_dict_name(REPO_ROOT / "ros2_ws/src/swarm_perception/config/aruco.yaml")
        for robot in _scenario().robots:
            assert marker_png_path(dictionary, robot.marker_id).is_file(), robot.robot_id

    def test_spawns_and_goals_are_the_design_table(self):
        rows = {r.robot_id: (r.spawn.x, r.spawn.y, r.goal.x, r.goal.y, r.initial_task)
                for r in _scenario().robots}
        assert rows == {
            "robot_1": (-1.2, 0.0, 2.45, -0.36, "cross_narrow_aisle"),
            "robot_2": (1.2, 0.0, -2.0, 0.0, "cross_narrow_aisle"),
            "robot_3": (-1.9, 0.0, 2.45, 0.36, "cross_narrow_aisle"),
            "robot_4": (-2.47, 0.0, 1.85, 0.0, "cross_narrow_aisle"),
        }

    def test_aperture_is_a55_j(self):
        barrier = _scenario().aisle_barrier
        assert (barrier.effective_width_m, barrier.center_x_m, barrier.length_m) == (
            0.55, 0.0, 1.0
        )

    def test_family_and_expected_conflict(self):
        scenario = _scenario()
        assert scenario.family == "convoy"
        conflict = scenario.expected_conflict
        assert conflict.type == "deadlock"
        assert conflict.involved_robots == ("robot_1", "robot_2", "robot_3", "robot_4")
        assert conflict.onset_window_sec == (15.0, 50.0)

    def test_oracle_is_the_strategy_label_shape(self):
        oracle = _scenario().oracle
        assert isinstance(oracle, OracleConfig)
        assert oracle.correct_yielder == "robot_2"
        assert oracle.correct_order == ("robot_1", "robot_3", "robot_4")
        assert oracle.correct_strategy == "convoy"
        assert oracle.accepted_strategies == ("convoy", "yield")
        assert oracle.platoon == ("robot_1", "robot_3", "robot_4")
        assert oracle.fcfs_yielder == "robot_2"
        assert oracle.margin is None


class TestC1TrackedBand:
    def test_spawns_and_goals(self):
        for robot in _scenario().robots:
            for x in (robot.spawn.x, robot.goal.x):
                assert abs(x) <= TRACKED_X_M, robot.robot_id
        assert TRACKED_X_M + _robot("robot_4").spawn.x == pytest.approx(0.03)

    def test_park_point_and_escort_ends(self):
        for case in GRID:
            positions = _positions(*case)
            p = _yield_parameters(_legacy(_mock(ORACLE_MOCK), positions))
            assert p["park_x_m"] == pytest.approx(1.124, abs=1e-3), case
            ends = [positions[rid][0] + clear
                    for rid, clear in zip(p["crossing_order"], p["crossing_clear_m"], strict=True)]
            assert ends == pytest.approx([1.774] * 3, abs=1e-3), case
            assert max(ends) + MARKER_HALF_M <= TRACKED_X_M


class TestC2PairGaps:
    def test_every_passer_is_commanded_so_the_parked_pair_is_exempt(self):
        # Passing the parked robot_2 at lateral 0.36 < 0.45 is legal only as
        # an admitted passer (pair-scoped exemption): all three must be in
        # the crossing order, each under a linked wait.
        command = _legacy(_mock(ORACLE_MOCK), _positions())
        p = _yield_parameters(command)
        assert p["crossing_order"] == ["robot_1", "robot_3", "robot_4"]
        waits = {a["robot_id"]: a["parameters"].get("linked_position")
                 for a in command["actions"] if a["action"] == "temporary_wait"}
        assert waits == {"robot_1": 0, "robot_3": 1, "robot_4": 2}
        assert p["pull_off_lateral_m"] == pytest.approx(0.36)
        assert p["pull_off_lateral_m"] < LATCH_M

    def test_alternative_robot_1_park_clears_the_held_robot_3(self):
        park = -park_offset_m(_geometry())
        lateral = 0.36
        x3 = _robot("robot_3").spawn.x
        assert park - x3 == pytest.approx(0.776, abs=1e-3)
        assert math.dist((park, lateral), (x3, 0.0)) == pytest.approx(0.855, abs=1e-3)
        assert park - x3 >= LEGAL_GAP_M

    def test_alternative_robot_2_escort_end_latches_on_robot_3(self):
        # The alternative order is censored: its escort ends 0.13 m from the
        # held robot_3, a latch (a lower-bound margin, as in T2b).
        end = -(park_offset_m(_geometry()) + passer_clearance_m(_geometry()))
        assert end == pytest.approx(-1.774, abs=1e-3)
        assert end - _robot("robot_3").spawn.x == pytest.approx(0.126, abs=1e-3)
        assert end - _robot("robot_3").spawn.x < LATCH_M


class TestC3SpawnGaps:
    def test_queue_spacing(self):
        spawns = {r.robot_id: (r.spawn.x, r.spawn.y) for r in _scenario().robots}
        assert math.dist(spawns["robot_1"], spawns["robot_3"]) == pytest.approx(0.70)
        assert math.dist(spawns["robot_3"], spawns["robot_4"]) == pytest.approx(0.57)
        for a, b in itertools.combinations(spawns.values(), 2):
            assert math.dist(a, b) >= SPAWN_GAP_M - 1e-9


class TestC4ArmB:
    def test_without_the_exclusion_35_of_45_read_head_on(self):
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        flipped = set()
        for case in GRID:
            verdict = classify_scene([_frame(_positions(*case), held=())], [], params)
            if verdict.scenario == "head_on":
                assert verdict.involved_robots == ["robot_1", "robot_2"], case
            else:
                assert (verdict.scenario, verdict.involved_robots) == (
                    "blocked_path", ["robot_3"]
                ), case
                flipped.add(case)
        assert flipped == CROWDED

    def test_with_the_queue_held_the_crowded_cases_wait_on_the_pair(self):
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        for case in GRID:
            resolution = resolve_classical([_frame(_positions(*case))], [], params)
            if case in CROWDED:
                assert resolution.classification.scenario == "unknown", case
                assert resolution.decision.strategy == "temporary_wait", case
            else:
                assert resolution.classification.scenario == "head_on", case
                assert resolution.decision.yield_robot == "robot_2", case
            assert resolution.decision.involved_robots == ["robot_1", "robot_2"], case
            assert resolution.decision.crossing_order is None, case

    def test_moving_the_queue_east_makes_it_worse(self):
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        flips = 0
        for case in GRID:
            positions = _positions(*case)
            positions["robot_3"] = (positions["robot_3"][0] + 0.1, 0.0)
            positions["robot_4"] = (positions["robot_4"][0] + 0.07, 0.0)
            verdict = classify_scene([_frame(positions, held=())], [], params)
            flips += verdict.scenario != "head_on"
        assert flips == 18


class TestOmittedQueueCensoring:
    def test_arm_b_command_leaves_the_queue_uncommanded(self):
        # Arm B's two-robot yield never orders the platoon: robot_3 and
        # robot_4 get no action and are released into the parked yielder.
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        positions = _positions()
        decision = resolve_classical([_frame(positions)], [], params).decision
        command = _legacy(decision, positions)
        assert {a["robot_id"] for a in command["actions"]} == {"robot_1", "robot_2"}

    def test_released_robot_3_breaches_the_latch_past_the_parked_robot_2(self):
        p = _yield_parameters(_legacy(_mock(ORACLE_MOCK), _positions()))
        lateral = p["pull_off_lateral_m"]
        reach = math.sqrt(LATCH_M**2 - lateral**2)
        assert reach == pytest.approx(0.27, abs=1e-3)
        assert p["park_x_m"] - reach == pytest.approx(0.854, abs=1e-3)


class TestC5ParkFeasibility:
    def test_oracle_grounds_the_design_backups(self):
        for case in GRID:
            positions = _positions(*case)
            p = _yield_parameters(_legacy(_mock(ORACLE_MOCK), positions))
            backup = abs(positions["robot_2"][0] - p["park_x_m"])
            assert p["backup_distance_m"] == pytest.approx(max(0.3, backup), abs=1e-3), case

    @pytest.mark.parametrize(("standoff", "backup", "escort_1"), [
        ((-0.12, 0.12), 1.004, 1.894),
        ((-0.20, 0.04), 1.084, 1.974),
    ])
    def test_design_table(self, standoff, backup, escort_1):
        positions = _positions()
        positions["robot_1"], positions["robot_2"] = (standoff[0], 0.0), (standoff[1], 0.0)
        p = _yield_parameters(_legacy(_mock(ORACLE_MOCK), positions))
        assert p["backup_distance_m"] == pytest.approx(backup, abs=1e-3)
        # The design doc's 3.574 / 4.174 are the escorts from the rejected
        # queue 0.1 m east (-1.8 / -2.4); from the built -1.9 / -2.47 queue
        # they are 3.674 / 4.244 (every end still x = 1.774).
        assert p["crossing_clear_m"] == pytest.approx([escort_1, 3.674, 4.244], abs=1e-3)


class TestC7GoalStack:
    def test_later_escort_ends_clear_the_goals(self):
        for goal in (_goals()["robot_1"], _goals()["robot_3"]):
            assert math.dist((1.774, 0.0), goal) == pytest.approx(0.766, abs=0.01)

    def test_robot_4_goal_clears_the_parked_robot_2_and_the_other_goals(self):
        goal_4 = _goals()["robot_4"]
        assert math.dist(goal_4, (1.124, 0.36)) == pytest.approx(0.81, abs=0.01)
        for rid in ("robot_1", "robot_3"):
            assert math.dist(goal_4, _goals()[rid]) == pytest.approx(0.70, abs=0.01)
            assert math.dist(goal_4, _goals()[rid]) >= GOAL_STACK_M

    def test_passer_goals_lie_past_their_escort_end(self):
        # R-GOAL-FAR: every passer goal is beyond the 1.774 escort end.
        for rid in ("robot_1", "robot_3", "robot_4"):
            assert _goals()[rid][0] - 1.774 >= 0.05

    def test_robot_1_and_robot_3_goal_separation_clears_the_safety_margin(self):
        # R-GOAL-SEP (Rev 22): the pair the pre-fix grid never checked
        # directly. The pre-fix +-0.3 stack (0.6 m apart) happened to sit
        # exactly on GOAL_SEP_FLOOR_M with zero headroom -- a necessary
        # condition for the fix, and a cheap regression guard -- but it is
        # NOT itself the root cause: two robots resting 0.6 m apart are safe
        # at rest. The root cause is dynamic (see
        # test_robot_3_release_approach_clears_the_parked_robot_1 below):
        # robot_3's released base-mission approach cuts the corner toward its
        # own goal and passes closer to the parked robot_1 than the static
        # separation would suggest. This test only guards the static number
        # from regressing back to the old, no-headroom stack.
        g1, g3 = _goals()["robot_1"], _goals()["robot_3"]
        separation = math.dist(g1, g3)
        assert separation == pytest.approx(2 * R1R3_GOAL_LATERAL_M, abs=1e-6)
        assert separation >= GOAL_SEP_FLOOR_M
        pre_fix_separation = 2 * 0.3
        assert pre_fix_separation == pytest.approx(GOAL_SEP_FLOOR_M)
        assert separation > pre_fix_separation

    def test_robot_3_release_approach_clears_the_parked_robot_1(self):
        # R-APPROACH (Rev 22): the actual failure mechanism. Once robot_3's
        # escort ends at (1.774, 0.0) (TestC7's own pin), its released
        # base-mission Nav2 leg runs roughly straight to its own goal --
        # cutting inside the goal-to-goal separation on the way. Model that
        # leg as the segment from the escort end to robot_3's goal and take
        # its closest approach to the parked robot_1: at the pre-fix +-0.3
        # stack this is 0.549 m, BELOW GOAL_SEP_FLOOR_M (0.60) -- consistent
        # with the measured VM approach (0.426-0.444 m once real Nav2
        # drift/timing is added). At the adopted +-0.36 stack it is 0.636 m,
        # clearing the floor. This is the pin the pre-fix 45-case standoff
        # grid never computed (it only ever placed robot_3 at its spawn, not
        # partway down its post-escort approach).
        escort_end = (1.774, 0.0)
        g1, g3 = _goals()["robot_1"], _goals()["robot_3"]
        closest = _closest_point_on_segment(g1, escort_end, g3)
        assert closest == pytest.approx(0.636, abs=1e-3)
        assert closest >= GOAL_SEP_FLOOR_M

        pre_fix_g1, pre_fix_g3 = (2.45, -0.3), (2.45, 0.3)
        pre_fix_closest = _closest_point_on_segment(pre_fix_g1, escort_end, pre_fix_g3)
        assert pre_fix_closest == pytest.approx(0.549, abs=1e-3)
        assert pre_fix_closest < GOAL_SEP_FLOOR_M

    def test_goal_lateral_matches_this_scenes_own_pull_off_margin(self):
        # The adopted +-0.36 is exactly pull_off_lateral_m for this scene
        # (aisle_half_width_m 0.6 - robot.half_width_m 0.09 - wall_margin_m
        # 0.15): the same margin discipline already governing robot_2's own
        # parked lateral offset here (TestC2PairGaps), so neither passer
        # goal sits closer to the rack face than robot_2 already safely does.
        from reasoning.rag.scene_geometry import pull_off_lateral_m

        assert R1R3_GOAL_LATERAL_M == pytest.approx(pull_off_lateral_m(_geometry()))
        for goal in (_goals()["robot_1"], _goals()["robot_3"]):
            assert abs(goal[1]) == pytest.approx(R1R3_GOAL_LATERAL_M)


class TestVacatedSpawnClearance:
    def test_robot_2_goal_sits_on_robot_3_spawn(self):
        assert math.dist(_goals()["robot_2"], (_robot("robot_3").spawn.x, 0.0)) == (
            pytest.approx(0.1)
        )

    @pytest.mark.parametrize("rtf", RTF_WINDOW)
    def test_robot_3_departs_before_the_earliest_robot_2_arrival(self, rtf):
        # robot_3 moves once admitted (after robot_1 clears); robot_2 only
        # returns once robot_4 (admitted after robot_3 clears) has cleared.
        trigger_wall = (STANDOFF_SIM - M5_START_SIM) / rtf + STALL_WALL + M5_LATENCY_WALL
        earliest_dispatch = M5_START_SIM + rtf * (trigger_wall + 1.0)
        latest_dispatch = M5_START_SIM + rtf * DISPATCH_BUDGET_WALL
        robot_3_departs_by = latest_dispatch + 1.084 / BACKUP_MPS + SIDESTEP_SIM + 1.974 / (
            ESCORT_MPS
        )
        robot_2_arrives_from = (
            earliest_dispatch + 1.004 / BACKUP_MPS + SIDESTEP_SIM
            + (1.894 + 3.674 + 4.244) / ESCORT_MPS
            + math.dist((1.124, 0.36), _goals()["robot_2"]) / TRANSIT_MPS
        )
        assert robot_3_departs_by < robot_2_arrives_from, (rtf, robot_3_departs_by)

    def test_robot_3_is_far_from_robot_2_goal_once_it_has_cleared(self):
        assert 1.774 - _goals()["robot_2"][0] >= LEGAL_GAP_M


class TestC8Fcfs:
    def test_spawns_clear_the_fcfs_zone(self):
        radius = load_classical_params(REPO_ROOT / "config/rag.yaml").head_on_fcfs_radius_m
        for rid in ("robot_1", "robot_2"):
            assert abs(_robot(rid).spawn.x) - radius == pytest.approx(0.2)
            assert abs(_robot(rid).spawn.x) >= radius + 0.1


class TestC9ReleaseWindow:
    @pytest.mark.parametrize("rtf", RTF_WINDOW)
    def test_release_after_dispatch_and_before_robot_3_admission(self, rtf):
        release_sim = M5_START_SIM + rtf * HOLD_WALL
        trigger_wall = (STANDOFF_SIM - M5_START_SIM) / rtf + STALL_WALL + M5_LATENCY_WALL
        assert trigger_wall < DISPATCH_BUDGET_WALL < HOLD_WALL
        earliest_dispatch = M5_START_SIM + rtf * (trigger_wall + 1.0)
        admission_3 = earliest_dispatch + 1.004 / BACKUP_MPS + SIDESTEP_SIM + 1.894 / ESCORT_MPS
        assert M5_START_SIM + rtf * DISPATCH_BUDGET_WALL < release_sim < admission_3, rtf

    def test_window_matches_the_header(self):
        assert M5_START_SIM + 0.19 * HOLD_WALL == pytest.approx(42.8)
        assert M5_START_SIM + 0.26 * HOLD_WALL == pytest.approx(51.2)


class TestC10toC12Budget:
    def test_duration(self):
        assert PREDICTED_MAKESPAN_SIM + 60.0 <= _scenario().duration_sec

    def test_escort_wall_bound(self):
        # Longest escort 4.244 m = 42.4 sim-s; at the slowest RTF it stays far
        # inside max(15 x nominal, 30) wall-s.
        nominal = 4.244 / ESCORT_MPS
        assert nominal / min(RTF_WINDOW) < 15.0 * nominal

    def test_robot_count(self):
        assert len(_scenario().robots) == 4

    def test_hold_backstop_covers_all_three_escorts(self):
        # M4 timers run on sim time (use_sim_time); 0.1 m/s escorts in turn.
        for case in GRID:
            p = _yield_parameters(_legacy(_mock(ORACLE_MOCK), _positions(*case)))
            assert p["hold_sec"] > sum(p["crossing_clear_m"]) / ESCORT_MPS, case


class TestC13Map:
    def test_committed_map_equals_the_t2b_map(self):
        def grid(name):
            data = yaml.safe_load((MAPS_DIR / f"warehouse_map_{name}.yaml").read_text())
            return np.array(Image.open(MAPS_DIR / data["image"]))

        assert np.array_equal(grid("convoy_counterflow"), grid("t2b_flow_ordering"))


class TestMockDecisions:
    def test_convoy_executes_identically_to_the_oracle_order(self):
        for case in GRID:
            positions = _positions(*case)
            convoy = _legacy(_mock(CONVOY_MOCK), positions)
            oracle = _legacy(_mock(ORACLE_MOCK), positions)
            assert convoy["degradations"] == ["strategy=aliased:convoy"], case
            assert convoy["actions"] == oracle["actions"], case

    def test_alternative_grounds_robot_1_yielding_to_the_counter_flow(self):
        command = _legacy(_mock(ALTERNATIVE_MOCK), _positions())
        assert command["actions"][0]["robot_id"] == "robot_1"
        assert _yield_parameters(command)["crossing_order"] == ["robot_2", "robot_3", "robot_4"]

    @pytest.mark.parametrize("path", [CONVOY_MOCK, ORACLE_MOCK, ALTERNATIVE_MOCK])
    def test_each_mock_clears_after_one_decision(self, path):
        _first, *rest = json.loads(path.read_text())
        assert [parse_decision_text(json.dumps(d)).strategy for d in rest] == ["none"]


class TestM5Settings:
    def test_goal_table_and_header_state_the_settings(self):
        table = ORCHESTRATOR_YAML.read_text().replace("\n#     ", " ")
        header = SCENARIO_PATH.read_text()
        assert "convoy_counterflow (B3, four robots" in table
        assert "start_delay_sec: 120 }" in table
        assert "center_m: 0.0, half_length_m: 0.5" in table
        assert "start_delay_sec: 120" in header
        assert "grounding.mode legacy" in header

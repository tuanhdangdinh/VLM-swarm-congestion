"""Tests for the B1 bottleneck scene `bottleneck_merge` (unified scene design).

Recomputes the scene header's geometry, timing and Arm B claims with M3's and
Arm B's own functions over a grid of predicted merge standoffs (robot_1's
stop point x robot_2's latch pose x robot_2's heading), in the standard
constraint-check table's C1-C13 order.
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

from swarm_orchestrator.models import RobotView, SceneSnapshot
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    attach_registry_assignments,
    build_reasoner_request,
)

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, load_scenario
from isaac.vgu_sim.config import OracleConfig, WarehouseConfig
from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path
from reasoning.baselines.classical_reasoner import (
    ConflictZone,
    classify_scene,
    load_classical_params,
    resolve_classical,
)
from reasoning.rag.command_grounder import ground_reasoner_result, prepare_retreat_selection
from reasoning.rag.maneuver_geometry import GroundingParams, load_grounding_params
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RetreatChoiceDecision,
    RetreatChoiceResult,
    RobotStateInput,
    SnapshotFrame,
)
from reasoning.vlm.output_parser import parse_decision_text
from reasoning.vlm.prompt_builder import build_prompt_payload
from reasoning.vlm.stage2_prompt import build_stage2_prompt_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = REPO_ROOT / "isaac/config/scenarios/bottleneck_merge.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCHESTRATOR_YAML = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
MOCK_PATH = REPO_ROOT / "config/mock_decisions/bottleneck_merge_yield_once.json"
RESOLUTION_M = 0.05

# Tracked band (IBB4: homography edges 2.789 / 2.092 less the verified inset).
TRACKED_X_M = 2.5
TRACKED_Y_M = 1.80
MARKER_HALF_M = 0.06
# M4 safety, centre to centre; the unified design's mover legality criterion
# (latch + 0.10 M1 budget) and spawn floor (latch + M1 max 0.084).
LATCH_M = 0.45
LEGAL_GAP_M = 0.55
SPAWN_GAP_M = 0.57
GOAL_STACK_M = 0.60
# R-POCKET: |x| + 0.09 + 0.05 <= 0.6 inside the N-S aisle.
NS_BAND = (-0.46, 0.46)
TRANSIT_MPS = 0.15
BACKUP_MPS = 0.09
ESCORT_MPS = 0.10
# Three-stack RTF window and M5's start (sim-s) at 2-3 stacks.
RTF_WINDOW = (0.28, 0.34, 0.39)
M5_START_SIM = 12.0
STALL_WALL = 12.0
M5_LATENCY_WALL = 2.0
# Worst dispatch after the trigger: the gpt-4o refusal retries (design: all
# dispatches land by ~75 wall-s).
DISPATCH_BUDGET_WALL = 75.0
STANDOFF_SIM = (18.0, 22.0)
PREDICTED_MAKESPAN_SIM = 130.0

# The design doc's four predicted standoffs (robot_1 x; robot_2 x, y, heading).
DESIGN_POSES = (
    (0.10, (0.15, 0.45, -80.0)),
    (0.00, (0.20, 0.40, -70.0)),
    (0.20, (0.30, 0.42, -60.0)),
    (-0.10, (0.10, 0.35, -90.0)),
)
# The constraint grid around them: robot_1's stop x, robot_2's latch pose and
# heading. robot_1 stops with robot_2 ahead of it (east of it), as at every
# design pose; the level-or-past poses are a separate registered sub-case.
_FULL_GRID = list(itertools.product(
    (-0.1, 0.0, 0.1, 0.2),     # robot_1 x
    (0.1, 0.2, 0.3),           # robot_2 x
    (0.35, 0.45),              # robot_2 y
    (-90.0, -75.0, -60.0),     # robot_2 heading, deg
))
GRID = [case for case in _FULL_GRID if case[1] > case[0]]
LEVEL_OR_PAST = [case for case in _FULL_GRID if case[1] <= case[0]]


def _scenario():
    return load_scenario(SCENARIO_PATH)


def _robot(robot_id: str):
    return next(r for r in _scenario().robots if r.robot_id == robot_id)


def _goals() -> dict[str, tuple[float, float]]:
    return {r.robot_id: (r.goal.x, r.goal.y) for r in _scenario().robots}


def _geometry() -> SceneGeometry:
    # The shipped block with the goal-table row's junction box and arms.
    # half_length_m raised 0.6 -> 1.1 by the rev-19b geometry fix (header of
    # isaac/config/scenarios/bottleneck_merge.yaml): restores the escort
    # margin at the measured trigger poses (TestMeasuredPoses below) without
    # moving robot_2's park y (verified unchanged: it is set by
    # backup_clearance_m, not half_length_m, until half_length_m > ~1.3).
    data = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"]
    data["corridor"] = {
        "axis": "x", "center_m": 0.0, "half_length_m": 1.1,
        "aisle_half_width_m": 0.6, "occluder_height_m": 0.0,
    }
    data["arms"] = {
        "robot_1": {"axis": "x", "side": -1},
        "robot_2": {"axis": "y", "side": 1},
        "robot_3": {"axis": "x", "side": -1},
    }
    return SceneGeometry(**data)


def _params() -> GroundingParams:
    base = load_grounding_params(REPO_ROOT / "config/rag.yaml")
    return GroundingParams(**{**base.model_dump(), "aisle_x_band_m": NS_BAND})


def _frame(r1_x: float, r2: tuple[float, float, float], *, held: bool = True) -> SnapshotFrame:
    goals = _goals()
    return SnapshotFrame(
        stamp=30.0,
        robots=[
            RobotStateInput(robot_id="robot_1", x=r1_x, y=0.0, theta=0.0,
                            linear_velocity=0.0, status="STOPPED", goal=goals["robot_1"]),
            RobotStateInput(robot_id="robot_2", x=r2[0], y=r2[1], theta=math.radians(r2[2]),
                            linear_velocity=0.0, status="STOPPED", goal=goals["robot_2"]),
            RobotStateInput(robot_id="robot_3", x=_robot("robot_3").spawn.x, y=0.0, theta=0.0,
                            linear_velocity=0.0, status="STOPPED", goal=goals["robot_3"]),
        ],
        held_robot_ids=("robot_3",) if held else (),
    )


def _grid_frames():
    for r1_x, r2_x, r2_y, heading in GRID:
        yield (r1_x, r2_x, r2_y, heading), _frame(r1_x, (r2_x, r2_y, heading))


def _result(decision: CongestionDecision) -> ReasonerResult:
    return ReasonerResult(
        request_id="req-b1", decision=decision, raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="req-b1", backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


def _mock_decision() -> CongestionDecision:
    first = json.loads(MOCK_PATH.read_text())[0]
    return parse_decision_text(json.dumps(first))


def _ground(frame: SnapshotFrame, decision: CongestionDecision | None = None) -> dict:
    return ground_reasoner_result(
        _result(decision or _mock_decision()), snapshot=frame, geometry=_geometry(),
        params=_params(),
    )


def _yield(command: dict) -> dict:
    (action,) = [a for a in command["actions"] if a["action"] == "yield"]
    return action


class TestScenario:
    def test_three_robots_with_matching_markers(self):
        assert [(r.robot_id, r.marker_id) for r in _scenario().robots] == [
            ("robot_1", 1), ("robot_2", 2), ("robot_3", 3),
        ]

    def test_marker_assets_exist_for_every_robot(self):
        dictionary = aruco_dict_name(REPO_ROOT / "ros2_ws/src/swarm_perception/config/aruco.yaml")
        for robot in _scenario().robots:
            assert marker_png_path(dictionary, robot.marker_id).is_file(), robot.robot_id

    def test_spawns_goals_and_tasks_are_the_design_table(self):
        rows = {
            r.robot_id: (r.spawn.x, r.spawn.y, round(r.spawn.yaw_rad, 6), r.goal.x, r.goal.y,
                         r.initial_task)
            for r in _scenario().robots
        }
        assert rows == {
            "robot_1": (-1.0, 0.0, 0.0, 2.45, -0.3, "cross_narrow_aisle"),
            "robot_2": (0.0, 1.75, round(-math.pi / 2, 6), 1.9, 0.0, "cross_narrow_aisle"),
            "robot_3": (-2.45, 0.0, 0.0, 2.45, 0.3, "cross_narrow_aisle"),
        }

    def test_aperture_is_a55_e(self):
        barrier = _scenario().aisle_barrier
        assert (barrier.effective_width_m, barrier.center_x_m, barrier.length_m) == (
            0.55, 1.2, 1.0
        )
        # 0.1 m clear of the N-S aisle edge (0.6), so both N-S arms stay open.
        assert barrier.center_x_m - barrier.length_m / 2 - 0.6 == pytest.approx(0.1)

    def test_family_and_expected_conflict(self):
        scenario = _scenario()
        assert scenario.family == "bottleneck"
        conflict = scenario.expected_conflict
        assert conflict.type == "bottleneck"
        assert conflict.involved_robots == ("robot_1", "robot_2", "robot_3")
        assert conflict.onset_window_sec == (8.0, 40.0)

    def test_oracle_is_feasibility_determined_without_a_margin(self):
        oracle = _scenario().oracle
        assert isinstance(oracle, OracleConfig)
        assert oracle.correct_yielder == "robot_2"
        assert oracle.feasible_yielders == ("robot_2",)
        assert oracle.correct_order == ("robot_1", "robot_3")
        assert oracle.margin is None
        assert oracle.fcfs_yielder == "robot_2"


class TestMergeSynchrony:
    def test_robot_1_leads_the_merge_by_about_1_4_s(self):
        r1, r2 = _robot("robot_1"), _robot("robot_2")
        t1 = (0.1 - r1.spawn.x) / TRANSIT_MPS
        t2 = math.dist((r2.spawn.x, r2.spawn.y), (0.15, 0.45)) / TRANSIT_MPS
        assert t1 == pytest.approx(7.33, abs=0.01)
        assert t2 - t1 == pytest.approx(1.39, abs=0.02)
        # Inside the designed (0, ~2.5) s window of a perpendicular latch.
        assert 0.0 < t2 - t1 < 2.5

    def test_every_robot_faces_its_first_leg(self):
        # The main-aisle pair faces east along y = 0; robot_2 faces south down
        # its arm toward the merge (escorts drive the spawn heading).
        first_leg = {"robot_1": (1.0, 0.0), "robot_2": (0.0, -1.0), "robot_3": (1.0, 0.0)}
        for robot in _scenario().robots:
            dx, dy = first_leg[robot.robot_id]
            assert math.cos(math.atan2(dy, dx) - robot.spawn.yaw_rad) == pytest.approx(1.0)

    def test_run_before_the_gate_mouth_is_at_least_half_a_metre(self):
        # R-RUN: the lead has >= 0.5 m of straight run before the merge.
        assert 0.1 - _robot("robot_1").spawn.x >= 0.5


class TestC1TrackedBand:
    def test_spawns_and_goals(self):
        for robot in _scenario().robots:
            for x, y in ((robot.spawn.x, robot.spawn.y), (robot.goal.x, robot.goal.y)):
                assert abs(x) <= TRACKED_X_M and abs(y) <= TRACKED_Y_M, (robot.robot_id, x, y)

    def test_robot_2_park_point_stays_tracked(self):
        for case, frame in _grid_frames():
            p = _yield(_ground(frame))["parameters"]
            assert abs(p["retreat_y_m"]) <= TRACKED_Y_M, case
            assert p["retreat_y_m"] == pytest.approx(1.70, abs=0.02), case

    def test_escort_ends_stay_tracked_with_the_marker(self):
        for case, frame in _grid_frames():
            p = _yield(_ground(frame))["parameters"]
            starts = {s.robot_id: s.x for s in frame.robots}
            for rid, clear in zip(p["crossing_order"], p["crossing_clear_m"], strict=True):
                end = starts[rid] + clear
                # +0.5 from the original 1.25: rev-19b half_length_m fix.
                assert end == pytest.approx(1.75, abs=1e-3), case
                assert end + MARKER_HALF_M <= TRACKED_X_M, case


class TestC2PairGaps:
    def test_robot_3_escort_end_clears_robot_1_at_its_goal(self):
        gap = math.dist((1.25, 0.0), _goals()["robot_1"])
        assert gap == pytest.approx(1.24, abs=0.01)
        assert gap >= LEGAL_GAP_M

    def test_robot_1_escort_moves_away_from_the_held_robot_3(self):
        start_gap = _robot("robot_1").spawn.x - _robot("robot_3").spawn.x
        assert start_gap == pytest.approx(1.45)
        # robot_1 only moves east from here; robot_3 is held at its spawn.
        for r1_x, *_ in GRID:
            assert r1_x - _robot("robot_3").spawn.x >= start_gap - 0.1

    def test_parked_robot_2_is_off_both_escort_lines(self):
        for case, frame in _grid_frames():
            p = _yield(_ground(frame))["parameters"]
            assert abs(p["retreat_y_m"]) >= LEGAL_GAP_M, case

    def test_robot_2_holds_until_robot_3_has_cleared(self):
        # Ordered release: the yielder's hold ends after the last passer in
        # crossing_order clears, so robot_2's return never meets robot_3.
        for case, frame in _grid_frames():
            p = _yield(_ground(frame))["parameters"]
            assert p["crossing_order"][-1] == "robot_3", case
            # +0.5 from the original 3.70: rev-19b half_length_m fix.
            assert p["crossing_clear_m"][-1] == pytest.approx(4.20, abs=1e-3), case

    def test_goals_are_pairwise_legal(self):
        for a, b in itertools.combinations(_goals().values(), 2):
            assert math.dist(a, b) >= LEGAL_GAP_M


class TestC3SpawnGaps:
    def test_every_spawn_pair_clears_the_spawn_floor(self):
        spawns = {r.robot_id: (r.spawn.x, r.spawn.y) for r in _scenario().robots}
        gaps = {
            (a, b): math.dist(spawns[a], spawns[b])
            for a, b in itertools.combinations(sorted(spawns), 2)
        }
        assert gaps[("robot_1", "robot_3")] == pytest.approx(1.45)
        assert gaps[("robot_1", "robot_2")] == pytest.approx(2.02, abs=0.01)
        assert min(gaps.values()) >= SPAWN_GAP_M


class TestC4ArmB:
    def test_without_the_held_exclusion_the_held_robot_3_is_blocked_path(self):
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        for case, _frame_ in _grid_frames():
            frame = _frame_.model_copy(update={"held_robot_ids": ()})
            verdict = classify_scene([frame], [], params)
            assert (verdict.scenario, verdict.involved_robots) == (
                "blocked_path", ["robot_3"]
            ), case

    def test_with_robot_3_held_arm_b_waits_on_the_merge_pair(self):
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        for case, frame in _grid_frames():
            resolution = resolve_classical([frame], [], params)
            assert resolution.classification.scenario == "unknown", case
            assert resolution.decision.involved_robots == ["robot_1", "robot_2"], case
            assert resolution.decision.strategy == "temporary_wait", case
            assert resolve_classical([frame], [], params, prior_attempts=1).decision.strategy == (
                "reroute"
            )

    def test_level_or_past_merge_reads_robot_1_blocked(self):
        # Registered sub-case: with robot_2 level with or behind robot_1, no
        # tracked robot is in robot_1's front half-plane, so Arm B reads it
        # blocked_path (and would reroute it) whatever robot_3 is.
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        assert len(LEVEL_OR_PAST) == 18
        for r1_x, r2_x, r2_y, heading in LEVEL_OR_PAST:
            frame = _frame(r1_x, (r2_x, r2_y, heading))
            verdict = classify_scene([frame], [], params)
            assert (verdict.scenario, verdict.involved_robots) == (
                "blocked_path", ["robot_1"]
            ), (r1_x, r2_x, r2_y, heading)

    def test_a_gate_mouth_zone_changes_nothing(self):
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        zone = ConflictZone(zone_id="aperture_1", x=0.4, y=0.0, radius_m=1.5)
        for case, frame in _grid_frames():
            assert classify_scene([frame], [zone], params) == classify_scene(
                [frame], [], params
            ), case

    def test_arm_b_has_no_path_to_bottleneck(self):
        # Every goal bearing is within ~15 deg of east: parallel, never the
        # 45-135 deg crossing the intersection rule needs.
        goals = _goals()
        for case, frame in _grid_frames():
            bearings = [
                math.degrees(math.atan2(goals[s.robot_id][1] - s.y, goals[s.robot_id][0] - s.x))
                for s in frame.robots
            ]
            assert max(abs(b) for b in bearings) < 45.0, case


class TestC5ParkFeasibility:
    def test_robot_2_yield_grounds_with_an_in_band_backup(self):
        for case, frame in _grid_frames():
            command = _ground(frame)
            action = _yield(command)
            assert action["robot_id"] == "robot_2", case
            assert 0.5 <= action["parameters"]["backup_distance_m"] <= 2.0, case
            assert not any(t.startswith("yield=infeasible") for t in command["degradations"])

    @pytest.mark.parametrize(("r1_x", "r2"), DESIGN_POSES)
    def test_design_poses_ground_the_design_table(self, r1_x, r2):
        frame = _frame(r1_x, r2)
        p = _yield(_ground(frame))["parameters"]
        backup = {0.10: 1.25, 0.00: 1.30, 0.20: 1.28, -0.10: 1.35}[r1_x]
        # +0.5 from the original {1.15, 1.25, 1.05, 1.35} / 3.70: the
        # rev-19b half_length_m 0.6 -> 1.1 fix adds a flat 0.5 m to every
        # crossing-arm passer's escort distance (far_mouth moves +0.5).
        escort = {0.10: 1.65, 0.00: 1.75, 0.20: 1.55, -0.10: 1.85}[r1_x]
        assert p["backup_distance_m"] == pytest.approx(backup, abs=1e-3)
        assert p["crossing_clear_m"] == pytest.approx([escort, 4.20], abs=1e-3)

    def test_alternative_robot_1_yield_is_refused(self):
        # The feasibility contrast: robot_3 behind robot_1 leaves no backup in
        # band, so derived grounding degrades robot_1's yield to a reroute.
        alternative = _mock_decision().model_copy(update={
            "yield_robot": "robot_1", "crossing_order": ["robot_2", "robot_3", "robot_1"],
        })
        for case, frame in _grid_frames():
            command = _ground(frame, alternative)
            assert command["actions"][0] == {
                "robot_id": "robot_1", "action": "reroute", "parameters": {"waypoints": []},
            }, case
            assert command["degradations"] == [
                "yield=infeasible:no backup distance in band [0.5, 2.0] m satisfies "
                "clearance 1.7 m"
            ], case


# The as-authored (half_length_m 0.6) geometry's real trigger poses (rev-19b
# root cause), read from ground truth in data/logs/vm_runs/bscene_smoke/: the
# predecessor's B1S1 smoke, this session's b1_oracle/b1_oracle_r2
# replications, and four sweep-batch first analyses (SW1_oracle_s42 seed 42;
# SW1_alternative_s42/s43 and SW1_wait_s42 -- SW1_oracle_s43 produced no
# scoreable dispatch and is not included). All GT (M1 differs by <=0.03 m /
# <=4 deg on every field). Seven of the eight land in the LEVEL_OR_PAST
# sub-case (robot_2.x < robot_1.x) the pre-fix GRID excluded from every
# feasibility check -- the class of error this fix closes. Fields:
# (robot_1.x, robot_1.y, robot_1.theta_rad, robot_2.x, robot_2.y,
# robot_2.theta_rad).
MEASURED_TRIGGER_POSES = (
    ("B1S1", (0.3852, -0.0558, 0.0407), (0.3601, 0.3101, -0.9161)),
    ("b1_oracle", (0.4325, -0.0061, -0.0599), (0.3267, 0.3108, -1.1530)),
    ("b1_oracle_r2", (0.4114, -0.0270, -0.1916), (0.2797, 0.3225, -1.2280)),
    ("SW1_oracle_s42", (0.3840, -0.0492, -0.0469), (0.2873, 0.3626, -1.1036)),
    ("SW1_alternative_s42", (0.4648, -0.0524, 0.0419), (0.3341, 0.2728, -0.9754)),
    ("SW1_alternative_s43", (0.4307, -0.0303, -0.0703), (0.2899, 0.3075, -1.1662)),
    ("SW1_wait_s42", (0.4829, -0.0582, 0.0851), (0.3306, 0.2676, -1.1220)),
    ("SW1_wait_s43", (0.1477, -0.0090, 0.1268), (0.2737, 0.3598, -1.1631)),
)


def _measured_frame(r1: tuple[float, float, float], r2: tuple[float, float, float]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=30.0,
        robots=[
            RobotStateInput(robot_id="robot_1", x=r1[0], y=r1[1], theta=r1[2],
                             linear_velocity=0.0, status="STOPPED", goal=(2.45, -0.3)),
            RobotStateInput(robot_id="robot_2", x=r2[0], y=r2[1], theta=r2[2],
                             linear_velocity=0.0, status="STOPPED", goal=(1.9, 0.0)),
            RobotStateInput(robot_id="robot_3", x=-2.4625, y=0.0, theta=0.0,
                             linear_velocity=0.0, status="STOPPED", goal=(2.45, 0.3)),
        ],
        held_robot_ids=(),
    )


class TestMeasuredTriggerPosesWereInfeasiblePreFix:
    """Regression pin for the rev-19b root cause (bscene_smoke Rev 19).

    Re-grounds the 8 measured poses at the PRE-FIX half_length_m (0.6) --
    fixed numeric inputs to the grounding functions, independent of the
    scenario YAML -- so the diagnosis stays locked in if the escort formula
    or its constants ever regress.
    """

    def _pre_fix_geometry(self) -> SceneGeometry:
        return _geometry().model_copy(
            update={"corridor": _geometry().corridor.model_copy(update={"half_length_m": 0.6})}
        )

    def test_seven_of_eight_are_the_untested_level_or_past_sub_case(self):
        sub_d = [name for name, r1, r2 in MEASURED_TRIGGER_POSES if r2[0] < r1[0]]
        assert sub_d == [
            "B1S1", "b1_oracle", "b1_oracle_r2", "SW1_oracle_s42",
            "SW1_alternative_s42", "SW1_alternative_s43", "SW1_wait_s42",
        ]

    def test_seven_of_eight_ground_the_oracle_yield_infeasible(self):
        # far_mouth (corridor.half_length_m, 0.6 pre-fix) minus robot_1.x,
        # plus escort_clearance_m (robot.safety_radius_m 0.45 +
        # passer_margin_m 0.2 = 0.65): required = 1.25 - robot_1.x.
        deficits = {
            "B1S1": 0.865, "b1_oracle": 0.818, "b1_oracle_r2": 0.839,
            "SW1_oracle_s42": 0.866, "SW1_alternative_s42": 0.785,
            "SW1_alternative_s43": 0.819, "SW1_wait_s42": 0.767,
        }
        geo = self._pre_fix_geometry()
        for name, r1, r2 in MEASURED_TRIGGER_POSES:
            if name not in deficits:
                continue
            command = ground_reasoner_result(
                _result(_mock_decision()), snapshot=_measured_frame(r1, r2),
                geometry=geo, params=_params(),
            )
            assert command["degradations"] == [
                "retreat=default:no_choice",
                f"yield=infeasible:required escort {deficits[name]:.3f} m outside "
                "band [1.0, 3.5] m",
            ], name

    def test_the_eighth_pose_is_feasible_but_under_margin(self):
        # SW1_wait_s43: the one measured pose in the "std" (r2.x > r1.x)
        # sub-case, already handled by the pre-fix GRID -- feasible at the
        # 1.0 m floor, but with only 0.102 m of margin, well under this
        # fix's 0.15 m target (see TestMeasuredPosesGroundFeasibleWithMargin).
        name, r1, r2 = next(p for p in MEASURED_TRIGGER_POSES if p[0] == "SW1_wait_s43")
        geo = self._pre_fix_geometry()
        command = ground_reasoner_result(
            _result(_mock_decision()), snapshot=_measured_frame(r1, r2),
            geometry=geo, params=_params(),
        )
        assert command["degradations"] == ["retreat=default:no_choice"]
        p = _yield(command)["parameters"]
        assert p["crossing_clear_m"][0] - 1.0 == pytest.approx(0.102, abs=1e-3)


class TestMeasuredPosesGroundFeasibleWithMargin:
    """The rev-19b fix's actual acceptance test: at half_length_m 1.1 (the
    shipped value), every one of the 8 measured trigger poses grounds the
    oracle yield feasible with >= 0.15 m of escort margin over the 1.0 m
    floor -- the task's pass condition, checked directly, not inferred from
    the formula.
    """

    def test_every_measured_pose_clears_the_floor_with_margin(self):
        for name, r1, r2 in MEASURED_TRIGGER_POSES:
            command = _ground(_measured_frame(r1, r2))
            action = _yield(command)
            assert action["robot_id"] == "robot_2", name
            assert not any(t.startswith("yield=infeasible") for t in command["degradations"]), name
            escort = action["parameters"]["crossing_clear_m"][0]
            assert escort - 1.0 >= 0.15, (name, escort)

    def test_robot_2_park_y_is_unchanged_by_the_half_length_fix(self):
        # The coupling this fix had to verify was safe: half_length_m also
        # feeds robot_2's own backup/park geometry (shared corridor object).
        # park y is set by backup_clearance_m (the 1.7 m clearance to
        # robot_1), not half_length_m, until half_length_m exceeds ~1.3, so
        # it stays 1.70 (0.10 inside the 1.80 tracked ceiling) at 1.1.
        for name, r1, r2 in MEASURED_TRIGGER_POSES:
            command = _ground(_measured_frame(r1, r2))
            park_y = _yield(command)["parameters"]["retreat_y_m"]
            assert park_y == pytest.approx(1.70, abs=0.02), name

    def test_reverse_along_heading_residual_at_two_shallow_headings(self):
        # NOT fixed by this change (documented residual, header of
        # isaac/config/scenarios/bottleneck_merge.yaml): M4's actual reverse
        # maneuver runs along robot_2's heading, not the arm axis, and
        # overshoots the NS_BAND west edge at the two shallowest measured
        # headings. The backup distance is set by the 1.7 m clearance to
        # robot_1, independent of half_length_m, so this is unaffected by
        # the escort fix in either direction.
        known_fails = {"B1S1", "SW1_alternative_s42"}
        for name, r1, r2 in MEASURED_TRIGGER_POSES:
            command = _ground(_measured_frame(r1, r2))
            backup = _yield(command)["parameters"]["backup_distance_m"]
            end_x = r2[0] + backup * math.cos(r2[2] + math.pi)
            in_band = end_x >= NS_BAND[0]
            assert in_band == (name not in known_fails), (name, end_x)


class TestC6RetreatCandidates:
    def test_every_candidate_stays_inside_the_ns_aisle(self):
        for case, frame in _grid_frames():
            selection = prepare_retreat_selection(
                frame, "robot_2", ["robot_1", "robot_3"], _params(), geometry=_geometry()
            )
            assert selection.candidates, case
            for candidate in selection.candidates:
                assert NS_BAND[0] - 1e-9 <= candidate.x <= NS_BAND[1] + 1e-9, case

    def test_without_the_x_band_candidate_a_lands_in_the_ne_rack(self):
        # The design's C6 FAIL the band fixes: x_park = x_robot_2 + 0.36.
        base = load_grounding_params(REPO_ROOT / "config/rag.yaml")
        frame = _frame(0.10, (0.15, 0.45, -80.0))
        selection = prepare_retreat_selection(
            frame, "robot_2", ["robot_1", "robot_3"], base, geometry=_geometry()
        )
        assert max(c.x for c in selection.candidates) == pytest.approx(0.51, abs=1e-3)

    @pytest.mark.parametrize(("r1_x", "r2"), DESIGN_POSES)
    def test_reverse_along_the_heading_stays_in_the_aisle_at_the_design_poses(self, r1_x, r2):
        # M4 reverses on odometry along the heading, not the arm axis.
        x0, _y0, heading = r2
        backup = _yield(_ground(_frame(r1_x, r2)))["parameters"]["backup_distance_m"]
        end_x = x0 + backup * math.cos(math.radians(heading) + math.pi)
        assert end_x >= NS_BAND[0], (r1_x, r2)

    def test_heading_gate_bound(self):
        # The west-drift bound x0 >= d cos|theta| - 0.46 (d <= 1.35): it holds
        # for every x0 >= 0 only down to ~-70 deg; at -62 deg it needs
        # x0 >= 0.17. The smoke records the heading and x at the trigger.
        def min_x0(heading_deg: float) -> float:
            return 1.35 * math.cos(math.radians(heading_deg)) + NS_BAND[0]

        assert min_x0(-70.0) == pytest.approx(0.002, abs=1e-3)
        assert min_x0(-62.0) == pytest.approx(0.174, abs=1e-3)
        assert min_x0(-90.0) < -0.4


class TestC7GoalStack:
    def test_goals_are_at_least_0_6_m_apart(self):
        goals = _goals()
        assert math.dist(goals["robot_2"], goals["robot_1"]) == pytest.approx(0.626, abs=1e-3)
        assert math.dist(goals["robot_2"], goals["robot_3"]) == pytest.approx(0.626, abs=1e-3)
        assert math.dist(goals["robot_1"], goals["robot_3"]) == pytest.approx(0.60)
        for a, b in itertools.combinations(goals.values(), 2):
            assert math.dist(a, b) >= GOAL_STACK_M - 1e-9

    def test_escort_end_clears_every_goal(self):
        for goal in _goals().values():
            assert math.dist((1.25, 0.0), goal) >= GOAL_STACK_M

    def test_goals_sit_past_the_gate(self):
        barrier = _scenario().aisle_barrier
        for goal in _goals().values():
            assert goal[0] > barrier.center_x_m + barrier.length_m / 2


class TestC9ReleaseWindow:
    def test_robot_3_is_held_80_s(self):
        text = ORCHESTRATOR_YAML.read_text()
        assert "start_delay_sec: 80 }" in text

    @pytest.mark.parametrize("rtf", RTF_WINDOW)
    def test_release_falls_after_dispatch_and_before_admission(self, rtf):
        release_sim = M5_START_SIM + rtf * 80.0
        latest_trigger_wall = (STANDOFF_SIM[1] - M5_START_SIM) / rtf + STALL_WALL + M5_LATENCY_WALL
        assert latest_trigger_wall < DISPATCH_BUDGET_WALL < 80.0
        latest_dispatch_sim = M5_START_SIM + rtf * DISPATCH_BUDGET_WALL
        assert latest_dispatch_sim < release_sim
        # robot_3's admission follows robot_2's backup and robot_1's escort.
        earliest_trigger_wall = (
            (STANDOFF_SIM[0] - M5_START_SIM) / rtf + STALL_WALL + M5_LATENCY_WALL
        )
        earliest_dispatch_sim = M5_START_SIM + rtf * (earliest_trigger_wall + 1.0)
        admission_sim = earliest_dispatch_sim + 1.25 / BACKUP_MPS + 1.05 / ESCORT_MPS
        assert release_sim < admission_sim, (rtf, release_sim, admission_sim)

    def test_release_window_matches_the_header(self):
        assert M5_START_SIM + 0.28 * 80.0 == pytest.approx(34.4)
        assert M5_START_SIM + 0.39 * 80.0 == pytest.approx(43.2)


class TestC10toC12Budget:
    def test_duration_covers_the_makespan_with_margin(self):
        assert PREDICTED_MAKESPAN_SIM + 60.0 <= _scenario().duration_sec

    def test_escort_wall_bound_holds_at_the_slowest_rtf(self):
        assert 1.0 / min(RTF_WINDOW) < 15.0

    def test_robot_count(self):
        assert len(_scenario().robots) <= 4


class TestC13Map:
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

    def test_barrier_blocks_the_gate_sides_and_leaves_the_arms_open(self):
        cfg = WarehouseConfig()
        grid, _ = build_occupancy_grid(
            cfg, obstacles=[], resolution_m=RESOLUTION_M,
            aisle_barrier=_scenario().aisle_barrier,
        )

        def cell(x, y):
            col = round((x + cfg.width_m / 2) / RESOLUTION_M)
            row = round((cfg.depth_m / 2 - y) / RESOLUTION_M)
            return int(grid[row, col])

        assert cell(1.2, 0.45) == 0 and cell(1.2, -0.45) == 0
        assert cell(1.2, 0.0) == 255
        for y in (0.3, 0.8, 1.2, 1.7):
            assert cell(0.0, y) == 255, y


class TestTextChannels:
    """The aperture reaches no text channel (amendments item 28)."""

    def test_goal_table_keeps_obstacles_and_zones_out(self):
        config = yaml.safe_load(ORCHESTRATOR_YAML.read_text())
        assert config["prompt_static_obstacles"] is False
        assert config.get("static_obstacles") in (None, [])
        assert config["shadow_classical_zones"] == []
        assert _scenario().static_obstacles == ()

    def test_rendered_prompt_names_no_aperture(self):
        goals = _goals()
        snapshot = SceneSnapshot(
            stamp=30.0,
            frame_id="overhead_camera",
            robots=[
                RobotView(robot_id=s.robot_id, x=s.x, y=s.y, theta=s.theta,
                          linear_velocity=0.0, status="STOPPED", stamp=30.0)
                for s in _frame(0.10, (0.15, 0.45, -80.0)).robots
            ],
        )
        attached = attach_registry_assignments(
            snapshot, goals.get, lambda _rid: "cross_narrow_aisle"
        )
        for order in ("id_asc", "id_desc"):
            request = build_reasoner_request(
                "req-b1", attached, "/tmp/req-b1.png", robot_presentation_order=order
            )
            payload = build_prompt_payload(request)
            text = (payload.system_prompt + payload.user_prompt).lower()
            for term in ("aperture", "barrier", "gate", "static obstacles", "1.2, 0"):
                assert term not in text, (order, term)


class _RecordingChooser:
    def __init__(self) -> None:
        self.requests = []

    def choose(self, request):
        self.requests.append(request)
        return RetreatChoiceResult(
            request_id=request.request_id, backend_id="fixed",
            choice=RetreatChoiceDecision(retreat_choice="A", justification="j"),
            raw_text="{}", attempts=1,
        )


class _MockReasoner:
    def run(self, request):
        return _result(_mock_decision())


class TestStage2TextChannel:
    """Stage 2 is the other text channel B1 opens (derived, stage 2 on)."""

    # The design poses with two in-band candidates, where stage 2 is called.
    TWO_CANDIDATE_POSES = ((0.20, (0.30, 0.42, -60.0)), (-0.10, (0.10, 0.35, -90.0)))

    def _request(self, r1_x, r2):
        goals = _goals()
        snapshot = SceneSnapshot(
            stamp=30.0,
            frame_id="overhead_camera",
            robots=[
                RobotView(robot_id=s.robot_id, x=s.x, y=s.y, theta=s.theta,
                          linear_velocity=0.0, status="STOPPED", stamp=30.0)
                for s in _frame(r1_x, r2).robots
            ],
        )
        attached = attach_registry_assignments(
            snapshot, goals.get, lambda _rid: "cross_narrow_aisle"
        )
        return build_reasoner_request("req-b1", attached, "/tmp/req-b1.png")

    @pytest.mark.parametrize(("r1_x", "r2"), TWO_CANDIDATE_POSES)
    def test_stage2_prompt_names_no_aperture(self, r1_x, r2):
        chooser = _RecordingChooser()
        pipe = InProcessPipeline(
            reasoner=_MockReasoner(), ground_fn=ground_reasoner_result,
            scene_geometry=_geometry(), grounding_params=_params(), retreat_chooser=chooser,
        )
        outcome = pipe.run(self._request(r1_x, r2))
        assert outcome.stage2 is not None and outcome.stage2.status == "answered"
        (request,) = chooser.requests
        payload = build_stage2_prompt_payload(request)
        text = (payload.system_prompt + payload.user_prompt).lower()
        for term in ("aperture", "barrier", "gate", "corridor", "static obstacles"):
            assert term not in text, term
        for candidate in request.candidates:
            assert NS_BAND[0] - 1e-9 <= candidate.x <= NS_BAND[1] + 1e-9

    def test_single_candidate_poses_skip_stage2(self):
        chooser = _RecordingChooser()
        pipe = InProcessPipeline(
            reasoner=_MockReasoner(), ground_fn=ground_reasoner_result,
            scene_geometry=_geometry(), grounding_params=_params(), retreat_chooser=chooser,
        )
        outcome = pipe.run(self._request(0.10, (0.15, 0.45, -80.0)))
        assert outcome.stage2.skip_reason == "single_candidate"
        assert chooser.requests == []


class TestM5Settings:
    def test_goal_table_and_header_state_the_settings(self):
        table = ORCHESTRATOR_YAML.read_text()
        header = SCENARIO_PATH.read_text()
        assert "bottleneck_merge (B1, three robots" in table
        assert "grounding_aisle_x_band_m: [-0.46, 0.46]" in table
        assert "robot_2: { axis: y, side: 1 }" in table.replace("\n#     ", " ")
        assert "start_delay_sec: 80" in header
        assert "grounding_aisle_x_band_m: [-0.46, 0.46]" in header

    def test_shipped_config_is_not_left_on_b1(self):
        config = yaml.safe_load(ORCHESTRATOR_YAML.read_text())
        assert config["grounding_aisle_x_band_m"] is None
        assert "robot_3" not in config["initial_tasks"]


class TestMockDecision:
    def test_first_decision_is_the_oracle_yield_then_the_scene_clears(self):
        first, *rest = json.loads(MOCK_PATH.read_text())
        decision = parse_decision_text(json.dumps(first))
        oracle = _scenario().oracle
        assert decision.type == "bottleneck"
        assert decision.yield_robot == oracle.correct_yielder
        assert tuple(r for r in decision.crossing_order if r != decision.yield_robot) == (
            oracle.correct_order
        )
        assert [parse_decision_text(json.dumps(d)).strategy for d in rest] == ["none"]

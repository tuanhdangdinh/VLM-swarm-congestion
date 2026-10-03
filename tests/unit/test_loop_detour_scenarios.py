"""Tests for the loop-map wait-vs-detour family (prereg-v2 (b), step 8 phase 2).

`loop_detour_permanent` (a box: never moves) and `loop_detour_transient`
(the marker-less robot visual: leaves at the registered dwell) differ only
in the blocker entity and the oracle. These pins hold the design control
(a gap NavFn still plans through but the collision monitor stops robot_1
short of, so the detour decision stays with M2/M3), the no-text-persistence
property (grep level, B1/B2-visual style), the tracked band, Arm B's
per-cell answer, the oracle/cost-record validators, the VM config overlay,
and the GT scorer.
"""
from __future__ import annotations

import difflib
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from swarm_orchestrator.models import RobotView, SceneSnapshot, TaskAssignment, load_config
from swarm_orchestrator.reasoning_pipeline import (
    attach_registry_assignments,
    build_reasoner_request,
)

from isaac.scripts.generate_warehouse_map import load_scenario
from isaac.vgu_sim.config import LoopDetourCostRecord, LoopDetourOracleConfig
from reasoning.baselines.classical_reasoner import load_classical_params, resolve_classical
from reasoning.vlm.models import RobotStateInput, SnapshotFrame
from reasoning.vlm.prompt_builder import build_prompt_payload
from scripts.coverage_scene_scores import loop_cost_record, score_loop
from scripts.strategy_regret import SCENES, preflight
from scripts.vm.v2_overlay import overlay_orchestrator, overlay_rag

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = REPO_ROOT / "isaac/config/scenarios"
CELLS = ("permanent", "transient")
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
NAV2_PARAMS = REPO_ROOT / "ros2_ws/src/swarm_simulation/config/nav2_params.yaml"
ORCH = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
RAG = REPO_ROOT / "config/rag.yaml"
# The marker-less visual's middle plate (its lidar cross-section) at the
# authored scale 1.82: ~0.25 m wide (blocked_path_object.yaml header).
VISUAL_PLATE_HALF_WIDTH_M = 0.125
MAP_RESOLUTION_M = 0.05
TRACKED_BAND_M = (2.5, 2.0)
DETOUR = [[0.3, 1.2], [1.8, 1.2]]


def _path(cell: str) -> Path:
    return SCENARIOS / f"loop_detour_{cell}.yaml"


def _raw(cell: str) -> dict:
    return yaml.safe_load(_path(cell).read_text())


def _nav2() -> dict:
    return yaml.safe_load(NAV2_PARAMS.read_text())


def _polygon_half_width(points: str) -> float:
    return max(abs(y) for _x, y in yaml.safe_load(points))


def _inscribed_radius(footprint: str) -> float:
    pts = yaml.safe_load(footprint)
    return min(max(abs(x) for x, _ in pts), max(abs(y) for _, y in pts))


def _blocker_north_edge(cell: str) -> float:
    blocker = _raw(cell)["timed_obstacles"][0]
    if blocker["asset"] == "static_box":
        return blocker["pose"]["y"] + blocker["size"]["y_m"] / 2.0
    return blocker["pose"]["y"] + VISUAL_PLATE_HALF_WIDTH_M


def _corridor_half_width(cell: str) -> float:
    return _raw(cell)["aisle_barrier"]["effective_width_m"] / 2.0


class TestPairDiff:
    def test_cells_differ_only_in_name_header_blocker_and_oracle(self):
        a, b = _path("permanent").read_text(), _path("transient").read_text()
        changed = [
            line for line in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
            if line[:1] in "+-" and not line.startswith(("+++", "---"))
        ]
        allowed_prefixes = ("name:", "#", "  #", "    asset:", "    remove_at_sec:",
                            "    pose:", "  persistence:", "  correct_strategy:",
                            "  accepted_strategies:", "    ")
        for line in changed:
            assert line[1:].startswith(allowed_prefixes), line
        ra, rb = _raw("permanent"), _raw("transient")
        for key in ("robots", "loop_map", "aisle_barrier", "static_obstacles",
                    "expected_conflict", "duration_sec", "seed", "runtime", "family"):
            assert ra[key] == rb[key], key

    def test_blocker_entities_are_the_box_and_the_visual(self):
        assert _raw("permanent")["timed_obstacles"][0]["asset"] == "static_box"
        assert _raw("permanent")["timed_obstacles"][0]["remove_at_sec"] is None
        transient = _raw("transient")["timed_obstacles"][0]
        assert transient["asset"] == "robot_visual_no_marker"
        assert transient["remove_at_sec"] is not None
        for cell in CELLS:
            assert _raw(cell)["timed_obstacles"][0]["spawn_at_sec"] == 0.0

    @pytest.mark.parametrize("cell", CELLS)
    def test_scenario_validates_with_loop_oracle(self, cell):
        config = load_scenario(_path(cell))
        assert isinstance(config.oracle, LoopDetourOracleConfig)
        assert config.oracle.persistence == cell
        assert [r.robot_id for r in config.robots] == ["robot_1"]


class TestDesignControl:
    """The gap NavFn keeps but the collision monitor refuses."""

    @pytest.mark.parametrize("cell", CELLS)
    def test_both_cells_leave_the_same_gap(self, cell):
        gap = _corridor_half_width(cell) - _blocker_north_edge(cell)
        assert gap == pytest.approx(0.22, abs=1e-9)

    @pytest.mark.parametrize("cell", CELLS)
    def test_gap_is_narrower_than_the_collision_monitor_stop_box(self, cell):
        stop_box = 2 * _polygon_half_width(
            _nav2()["collision_monitor"]["ros__parameters"]["forward_stop"]["points"]
        )
        gap = _corridor_half_width(cell) - _blocker_north_edge(cell)
        assert gap < stop_box

    @pytest.mark.parametrize("cell", CELLS)
    def test_gap_keeps_a_navfn_cell_clear_of_the_inscribed_radius(self, cell):
        # A free cell whose centre is farther than the inscribed radius from
        # both edges must survive the 0.05 m discretization, with one cell of
        # lidar-marking slack.
        inscribed = _inscribed_radius(
            _nav2()["global_costmap"]["global_costmap"]["ros__parameters"]["footprint"]
        )
        gap = _corridor_half_width(cell) - _blocker_north_edge(cell)
        assert gap - MAP_RESOLUTION_M > 2 * inscribed

    @pytest.mark.parametrize("cell", CELLS)
    def test_empty_corridor_clears_the_stop_box_when_centred(self, cell):
        stop_half = _polygon_half_width(
            _nav2()["collision_monitor"]["ros__parameters"]["forward_stop"]["points"]
        )
        assert _corridor_half_width(cell) - stop_half >= 0.12

    @pytest.mark.parametrize("cell", CELLS)
    def test_corridor_sits_between_the_junction_and_the_connector(self, cell):
        raw = _raw(cell)
        barrier, loop = raw["aisle_barrier"], raw["loop_map"]
        lo = barrier["center_x_m"] - barrier["length_m"] / 2.0
        hi = barrier["center_x_m"] + barrier["length_m"] / 2.0
        assert lo > 0.6
        assert hi < loop["connector_center_x_m"] - loop["connector_width_m"] / 2.0
        blocker = raw["timed_obstacles"][0]["pose"]["x"]
        assert lo < blocker < hi

    def test_barrier_camera_shadow_clears_the_connector_centreline(self):
        # A 0.9 m block shadows its footprint scaled by (3 - 0.2) / (3 - 0.9)
        # about the nadir (loop-preemption report, Section 3).
        raw = _raw("permanent")
        barrier, loop = raw["aisle_barrier"], raw["loop_map"]
        k = (3.0 - 0.2) / (3.0 - 0.9)
        shadow_hi_x = k * (barrier["center_x_m"] + barrier["length_m"] / 2.0)
        assert shadow_hi_x < loop["connector_center_x_m"] - 0.06

    @pytest.mark.parametrize("cell", CELLS)
    def test_map_regenerates_byte_identical(self, cell, tmp_path):
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "isaac/scripts/generate_warehouse_map.py"),
             "--out-dir", str(tmp_path), "--scenario", str(_path(cell))],
            check=True, cwd=REPO_ROOT, capture_output=True,
        )
        name = f"warehouse_map_loop_detour_{cell}"
        for ext in (".pgm", ".yaml"):
            fresh = (tmp_path / f"{name}{ext}").read_bytes()
            assert fresh == (MAPS_DIR / f"{name}{ext}").read_bytes()

    def test_both_cells_share_one_map(self):
        a = (MAPS_DIR / "warehouse_map_loop_detour_permanent.pgm").read_bytes()
        b = (MAPS_DIR / "warehouse_map_loop_detour_transient.pgm").read_bytes()
        assert a == b


class TestTrackedBand:
    @pytest.mark.parametrize("cell", CELLS)
    def test_every_endpoint_and_waypoint_is_inside_the_tracked_band(self, cell):
        raw = _raw(cell)
        robot = raw["robots"][0]
        points = [(robot["spawn"]["x"], robot["spawn"]["y"]),
                  (robot["goal"]["x"], robot["goal"]["y"]), *map(tuple, DETOUR)]
        for x, y in points:
            assert abs(x) <= TRACKED_BAND_M[0] and abs(y) <= TRACKED_BAND_M[1], (x, y)

    def test_detour_waypoints_are_on_the_loop(self):
        loop = _raw("permanent")["loop_map"]
        half = loop["second_aisle_width_m"] / 2.0
        for _x, y in DETOUR:
            assert abs(y - loop["second_aisle_center_y_m"]) <= half
        # First waypoint in the N-S strip (|x| <= 0.6), second at the connector.
        assert abs(DETOUR[0][0]) <= 0.6
        assert DETOUR[1][0] == loop["connector_center_x_m"]


def _frame(stamp: float = 40.0) -> SnapshotFrame:
    return SnapshotFrame(stamp=stamp, robots=[
        RobotStateInput(robot_id="robot_1", x=0.62, y=0.13, theta=0.0, linear_velocity=0.0,
                        status="STOPPED", task="cross_narrow_aisle", goal=(2.3, 0.0)),
    ])


class TestNoTextPersistence:
    """Persistence reaches no text channel: the blocker is untracked in both cells."""

    def _prompt(self, order: str = "id_asc") -> str:
        frame = _frame()
        snapshot = SceneSnapshot(
            stamp=frame.stamp, frame_id="overhead_camera",
            robots=[RobotView(robot_id=s.robot_id, x=s.x, y=s.y, theta=s.theta,
                              linear_velocity=0.0, status="STOPPED", stamp=frame.stamp)
                    for s in frame.robots],
        )
        task = TaskAssignment(task="cross_narrow_aisle", goal=(2.3, 0.0))
        attached = attach_registry_assignments(snapshot, lambda _r: task.goal, lambda _r: task.task)
        request = build_reasoner_request("req-loop", attached, "/tmp/req-loop.png",
                                         robot_presentation_order=order)
        return build_prompt_payload(request).user_prompt

    @pytest.mark.parametrize("cell", CELLS)
    def test_only_robot_1_is_tracked(self, cell):
        assert [r["robot_id"] for r in _raw(cell)["robots"]] == ["robot_1"]
        assert _raw(cell)["static_obstacles"] == []

    @pytest.mark.parametrize("order", ["id_asc", "id_desc"])
    def test_rendered_prompt_names_no_scenario_blocker_term(self, order):
        # "blocker" / "transient" / "object" are excluded: the fixed v2
        # template asks for `blocker_kind` in exactly those words whatever
        # the scene (T3a's question), so they are the question, not a hint.
        text = self._prompt(order).lower()
        for term in ("static_box", "robot_visual", "box", "paused", "fallen",
                     "fault", "dwell", "resume", "permanent"):
            assert term not in text, term

    def test_goal_table_row_declares_no_text_channel(self):
        config = yaml.safe_load(ORCH.read_text())
        assert not config.get("prompt_static_obstacles")
        assert not config.get("static_obstacles")
        assert "loop_detour_permanent / loop_detour_transient" in ORCH.read_text()


class TestArmB:
    """Arm B reads no image, so both cells get the same classical answer."""

    def test_both_cells_are_blocked_path_reroute(self):
        resolution = resolve_classical([_frame()], [], load_classical_params(RAG))
        assert resolution.classification.scenario == "blocked_path"
        assert resolution.decision.strategy == "reroute"
        assert [(leg.robot_id, leg.action) for leg in resolution.decision.proposed_plan] == [
            ("robot_1", "reroute")
        ]
        for cell in CELLS:
            oracle = _raw(cell)["oracle"]
            assert (oracle["classical_scenario"], oracle["classical_strategy"]) == (
                "blocked_path", "reroute"
            )

    def test_only_the_transient_cell_contrasts_arm_b(self):
        assert not load_scenario(_path("permanent")).oracle.contrasts_classical
        assert load_scenario(_path("transient")).oracle.contrasts_classical


def _cost(**overrides) -> dict:
    record = {
        "wait_time_to_goal_sec": 60.0, "wait_censored": False,
        "reroute_time_to_goal_sec": 90.0, "reroute_censored": False,
        "winner": "temporary_wait", "margin": 0.5, "n_per_arm": 1,
    }
    record.update(overrides)
    return record


class TestOracleValidators:
    def test_permanent_must_answer_reroute(self):
        with pytest.raises(ValueError):
            LoopDetourOracleConfig(
                persistence="permanent", correct_strategy="temporary_wait",
                accepted_strategies=("temporary_wait",), classical_strategy="reroute",
                classical_scenario="blocked_path", rationale="r",
            )

    def test_cost_winner_must_match_the_answer(self):
        with pytest.raises(ValueError):
            LoopDetourOracleConfig(
                persistence="transient", correct_strategy="reroute",
                accepted_strategies=("reroute",), classical_strategy="reroute",
                classical_scenario="blocked_path", rationale="r",
                cost=LoopDetourCostRecord(**_cost()),
            )

    def test_censored_winner_is_rejected(self):
        with pytest.raises(ValueError):
            LoopDetourCostRecord(**_cost(wait_censored=True))

    def test_margin_must_match_the_table(self):
        with pytest.raises(ValueError):
            LoopDetourCostRecord(**_cost(margin=0.2))

    def test_slower_winner_is_rejected(self):
        with pytest.raises(ValueError):
            LoopDetourCostRecord(**_cost(winner="reroute", margin=-0.3333))

    def test_passes_reads_the_threshold(self):
        assert LoopDetourCostRecord(**_cost()).passes
        assert not LoopDetourCostRecord(
            **_cost(reroute_time_to_goal_sec=66.0, margin=0.1)
        ).passes

    def test_loop_cost_record_from_a_censored_permanent_table(self):
        table = {"arms": {
            "wait": {"mean_total_sec": 228.0, "censored": True, "n": 1, "run_ids": ["w"]},
            "reroute": {"mean_total_sec": 80.0, "censored": False, "n": 1, "run_ids": ["r"]},
        }}
        record = loop_cost_record(table)
        assert record["winner"] == "reroute"
        assert record["wait_censored"] is True
        assert record["margin"] == pytest.approx(228.0 / 80.0 - 1.0, abs=1e-4)


class TestOverlay:
    def test_loop_overlay_sets_the_goal_table_row(self):
        text = overlay_orchestrator(ORCH.read_text(), "loop_permanent")
        config = load_config(yaml.safe_load(text))
        assert config.scenario_geometry.reroute_waypoints == tuple(map(tuple, DETOUR))
        assert {rid: t.goal for rid, t in config.initial_tasks.items()} == {"robot_1": (2.3, 0.0)}
        assert overlay_rag(RAG.read_text(), "loop_permanent") is None

    def test_overlay_refuses_an_already_overlaid_file(self):
        once = overlay_orchestrator(ORCH.read_text(), "loop_permanent")
        with pytest.raises(ValueError):
            overlay_orchestrator(once, "loop_transient")

    def test_overlay_touches_only_the_two_blocks(self):
        before = ORCH.read_text().splitlines()
        after = overlay_orchestrator(ORCH.read_text(), "loop_transient").splitlines()
        changed = [line for line in difflib.unified_diff(before, after, lineterm="", n=0)
                   if line[:1] in "+-" and not line.startswith(("+++", "---"))]
        assert all("robot_" in line or "reroute_waypoints" in line for line in changed), changed

    @pytest.mark.parametrize("cell", CELLS)
    def test_overlaid_tree_passes_the_regret_preflight(self, cell, tmp_path):
        scene = SCENES[f"loop_detour_{cell}"]
        repo = tmp_path / "repo"
        for relpath in (scene.scenario_relpath, scene.map_relpath,
                        *(Path(a.mock_decision_file) for a in scene.arms.values())):
            (repo / relpath).parent.mkdir(parents=True, exist_ok=True)
            (repo / relpath).write_bytes((REPO_ROOT / relpath).read_bytes())
        orch = repo / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
        orch.parent.mkdir(parents=True, exist_ok=True)
        orch.write_text(overlay_orchestrator(ORCH.read_text(), f"loop_{cell}"))
        (repo / "config").mkdir(parents=True, exist_ok=True)
        (repo / "config/rag.yaml").write_text(RAG.read_text())
        assert preflight(scene, repo) == []

    def test_convoy_slip_overlay_matches_the_b3_row(self, tmp_path):
        scene = SCENES["convoy_counterflow"]
        repo = tmp_path / "repo"
        for relpath in (scene.scenario_relpath, scene.map_relpath,
                        *(Path(a.mock_decision_file) for a in scene.arms.values())):
            (repo / relpath).parent.mkdir(parents=True, exist_ok=True)
            (repo / relpath).write_bytes((REPO_ROOT / relpath).read_bytes())
        orch = repo / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
        orch.parent.mkdir(parents=True, exist_ok=True)
        orch.write_text(overlay_orchestrator(ORCH.read_text(), "convoy_slip"))
        (repo / "config").mkdir(parents=True, exist_ok=True)
        (repo / "config/rag.yaml").write_text(overlay_rag(RAG.read_text(), "convoy_slip"))
        assert preflight(scene, repo) == []


def _write_gt(gt_dir: Path, track: list[tuple[float, float, float]], goal=(2.3, 0.0)) -> Path:
    """track[i] = (x, y, speed) of robot_1 at sim t = i * 0.5."""
    gt_dir.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"sim_time_sec": i * 0.5, "robots": {"robot_1": {
        "x": x, "y": y, "theta": 0.0, "speed_mps": v,
        "distance_to_goal_m": math.dist((x, y), goal)}}})
        for i, (x, y, v) in enumerate(track)]
    (gt_dir / "ground_truth.jsonl").write_text("\n".join(lines) + "\n")
    return gt_dir


def _decisions(tmp_path: Path, strategy: str | None, stamp: float) -> Path:
    out = tmp_path / "decisions"
    out.mkdir()
    if strategy is not None:
        (out / "a.json").write_text(json.dumps({
            "decision": {"congestion_detected": True, "strategy": strategy},
            "grounded_command_present": True, "scene": {"stamp": stamp},
        }))
    return out


def _approach_then(tail: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    still = [(-2.4, 0.0, 0.0)] * 4
    drive = [(-2.4 + 0.075 * i, 0.0, 0.15) for i in range(1, 41)]  # to x = 0.6 by t = 22
    return still + drive + tail


class TestScoreLoop:
    def test_reroute_run_detours_after_dispatch_and_arrives(self, tmp_path):
        stall = [(0.6, 0.1, 0.0)] * 10                        # t 22-27
        loop = [(0.4, 0.6 + 0.1 * i, 0.15) for i in range(1, 8)]  # onto the loop
        home = [(2.3, 0.0, 0.0)] * 6
        gt = _write_gt(tmp_path / "gt", _approach_then(stall + loop + home))
        result = score_loop(gt, _raw("permanent"),
                            decisions_dir=_decisions(tmp_path, "reroute", 25.0))
        assert result["arrived"] and not result["censored"]
        assert result["stall"]["onset_sec"] == pytest.approx(22.0)
        assert result["entered_loop_sec"] > 25.0
        assert result["self_detour"] is False
        assert result["decision_correct"] is True
        assert result["outcome_rank"][0] == 1

    def test_loop_entry_before_any_reroute_is_a_self_detour(self, tmp_path):
        loop = [(0.4, 0.6 + 0.1 * i, 0.15) for i in range(1, 8)]
        gt = _write_gt(tmp_path / "gt", _approach_then(loop + [(2.3, 0.0, 0.0)] * 4))
        result = score_loop(gt, _raw("permanent"), decisions_dir=_decisions(tmp_path, None, 0.0))
        assert result["self_detour"] is True
        assert result["dispatch"] is None

    def test_never_arriving_wait_run_is_censored(self, tmp_path):
        stall = [(0.6, 0.1, 0.0)] * 40
        gt = _write_gt(tmp_path / "gt", _approach_then(stall))
        result = score_loop(gt, _raw("permanent"),
                            decisions_dir=_decisions(tmp_path, "temporary_wait", 25.0))
        assert result["censored"] and not result["arrived"]
        assert result["self_detour"] is False
        assert result["decision_correct"] is False
        assert result["outcome_rank"][0] == 0
        assert result["tracked_band"]["in_band"]

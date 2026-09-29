"""Tests for the strategy-regret harness (scripts/strategy_regret.py, item 29).

Nothing here runs Isaac: sweeps are scored from synthetic ground truth and
synthetic run scores, and preflight runs against a scratch tree.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from reasoning.vlm.output_parser import parse_decision_text
from scripts.strategy_regret import (
    SCENES,
    cost_table,
    main,
    plan_runs,
    preflight,
    roles_from_command,
    roles_from_decision,
    score_regret,
)
from scripts.t2b_forced_order import RunScore

ROOT = Path(__file__).resolve().parents[2]
ORCH_RELPATH = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")


def _first_decision(path: str) -> dict:
    return json.loads((ROOT / path).read_text())[0]


def _score(arm: str, total: float, *, censored: bool = False, run: str = "r") -> RunScore:
    # Two robots: one arrives at `total`, the other at t0 (or never).
    return RunScore(
        arm=arm, run_id=f"{arm}_{run}", t0_sec=0.0,
        arrivals_sec={"robot_1": total, "robot_2": None if censored else 0.0},
        end_sec=total,
    )


def _scene_tree(tmp_path: Path, name: str) -> Path:
    scene = SCENES[name]
    repo = tmp_path / "repo"
    for relpath in (scene.scenario_relpath, scene.map_relpath,
                    *(Path(a.mock_decision_file) for a in scene.arms.values())):
        (repo / relpath).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relpath, repo / relpath)
    orch = yaml.safe_load((ROOT / ORCH_RELPATH).read_text())
    orch["initial_tasks"] = scene.initial_tasks
    orch["scenario_geometry"]["corridor"].update(scene.corridor)
    if scene.scenario_geometry_arms is not None:
        orch["scenario_geometry"]["arms"] = scene.scenario_geometry_arms
    if scene.aisle_x_band_m is not None:
        orch["grounding_aisle_x_band_m"] = list(scene.aisle_x_band_m)
    (repo / ORCH_RELPATH).parent.mkdir(parents=True, exist_ok=True)
    (repo / ORCH_RELPATH).write_text(yaml.safe_dump(orch), encoding="utf-8")
    rag = yaml.safe_load((ROOT / "config/rag.yaml").read_text())
    rag["grounding"]["mode"] = scene.grounding_mode
    (repo / "config").mkdir(parents=True, exist_ok=True)
    (repo / "config/rag.yaml").write_text(yaml.safe_dump(rag), encoding="utf-8")
    return repo


class TestRegistry:
    @pytest.mark.parametrize(
        ("scene", "arm"), [(s, a) for s, spec in SCENES.items() for a in spec.arms]
    )
    def test_each_arm_mock_executes_as_the_arm(self, scene, arm):
        spec = SCENES[scene]
        decision = _first_decision(spec.arms[arm].mock_decision_file)
        parse_decision_text(json.dumps(decision))
        assert roles_from_decision(spec, decision) in spec.arms[arm].roles

    @pytest.mark.parametrize("scene", sorted(SCENES))
    def test_scene_goals_are_the_scenario_goals(self, scene):
        spec = SCENES[scene]
        scenario = yaml.safe_load((ROOT / spec.scenario_relpath).read_text())
        goals = {r["robot_id"]: [r["goal"]["x"], r["goal"]["y"]] for r in scenario["robots"]}
        assert {rid: t["goal"] for rid, t in spec.initial_tasks.items()} == goals

    @pytest.mark.parametrize("scene", sorted(SCENES))
    def test_scene_row_is_in_the_goal_table(self, scene):
        assert scene in (ROOT / ORCH_RELPATH).read_text()

    def test_arms_have_distinct_roles_within_a_scene(self):
        for spec in SCENES.values():
            keys = [key for arm in spec.arms.values() for key in arm.roles]
            assert len(keys) == len(set(keys)), spec.name

    def test_convoy_label_executes_as_the_oracle_arm(self):
        spec = SCENES["convoy_counterflow"]
        convoy = _first_decision("config/mock_decisions/convoy_counterflow_convoy_once.json")
        assert roles_from_decision(spec, convoy) in spec.arms["oracle"].roles

    @pytest.mark.parametrize("member", ["priority_urgent_r1", "priority_urgent_r2"])
    def test_priority_override_executes_as_the_routine_yield(self, member):
        spec = SCENES[member]
        override = _first_decision("config/mock_decisions/priority_urgent_override_once.json")
        assert roles_from_decision(spec, override) in spec.arms["yield_routine"].roles


class TestPreflight:
    @pytest.mark.parametrize("scene", sorted(SCENES))
    def test_a_configured_tree_passes(self, tmp_path, scene):
        assert preflight(SCENES[scene], _scene_tree(tmp_path, scene)) == []

    def test_the_shipped_tree_is_refused_for_b3(self):
        problems = preflight(SCENES["convoy_counterflow"], ROOT)
        assert any("initial_tasks lacks robot_4" in p for p in problems)
        assert any("grounding.mode is 'derived'" in p for p in problems)

    def test_missing_x_band_is_refused_for_b1(self, tmp_path):
        repo = _scene_tree(tmp_path, "bottleneck_merge")
        orch = yaml.safe_load((repo / ORCH_RELPATH).read_text())
        orch["grounding_aisle_x_band_m"] = None
        (repo / ORCH_RELPATH).write_text(yaml.safe_dump(orch), encoding="utf-8")
        problems = preflight(SCENES["bottleneck_merge"], repo)
        assert any("grounding_aisle_x_band_m" in p for p in problems)

    def test_missing_priority_is_refused_for_b2(self, tmp_path):
        repo = _scene_tree(tmp_path, "priority_urgent_r2")
        orch = yaml.safe_load((repo / ORCH_RELPATH).read_text())
        orch["initial_tasks"]["robot_2"].pop("priority")
        (repo / ORCH_RELPATH).write_text(yaml.safe_dump(orch), encoding="utf-8")
        problems = preflight(SCENES["priority_urgent_r2"], repo)
        assert problems == [
            "orchestrator.yaml initial_tasks.robot_2.priority is 0, priority_urgent_r2 needs 1"
        ]

    def test_a_missing_mock_is_refused(self, tmp_path):
        repo = _scene_tree(tmp_path, "convoy_counterflow")
        (repo / SCENES["convoy_counterflow"].arms["pair_yield"].mock_decision_file).unlink()
        assert any("missing file" in p for p in preflight(SCENES["convoy_counterflow"], repo))


class TestPlan:
    def test_arms_are_interleaved_per_seed(self):
        runs = plan_runs(SCENES["convoy_counterflow"], [42, 43])
        assert [(r["seed"], r["arm"]) for r in runs] == [
            (42, "oracle"), (42, "alternative"), (42, "pair_yield"),
            (43, "oracle"), (43, "alternative"), (43, "pair_yield"),
        ]
        assert runs[0]["label"] == "convoy_counterflow_oracle_seed42"

    def test_arm_subset(self):
        runs = plan_runs(SCENES["bottleneck_merge"], [42], ["wait"])
        assert [(r["arm"], r["strategy"]) for r in runs] == [("wait", "temporary_wait")]

    def test_unknown_arm_is_refused(self):
        with pytest.raises(ValueError, match="no arms"):
            plan_runs(SCENES["bottleneck_merge"], [42], ["convoy"])


class TestCostTable:
    def test_best_arm_and_regrets(self):
        scores = [_score("oracle", 180.0, run="a"), _score("oracle", 200.0, run="b"),
                  _score("alternative", 260.0, run="a"), _score("alternative", 280.0, run="b")]
        table = cost_table(SCENES["t2b_flow_ordering"], scores)
        assert table["best_arm"] == "oracle"
        assert table["arms"]["oracle"]["mean_total_sec"] == 190.0
        assert table["arms"]["alternative"]["regret_sec"] == 80.0
        assert table["arms"]["alternative"]["regret_is_lower_bound"] is False

    def test_censored_arm_is_a_lower_bound_and_never_the_reference(self):
        scores = [_score("oracle", 300.0, run="a"), _score("oracle", 300.0, run="b"),
                  _score("pair_yield", 250.0, censored=True, run="a"),
                  _score("pair_yield", 250.0, censored=True, run="b")]
        table = cost_table(SCENES["convoy_counterflow"], scores)
        assert table["best_arm"] == "oracle"
        pair = table["arms"]["pair_yield"]
        assert pair["censored"] is True and pair["regret_is_lower_bound"] is True
        # 250 + the never-arrived robot counted to the end (250) = 500.
        assert pair["mean_total_sec"] == 500.0

    def test_too_few_runs_is_refused(self):
        with pytest.raises(ValueError, match="below 2 runs"):
            cost_table(SCENES["t2b_flow_ordering"], [_score("oracle", 1.0)])

    def test_unknown_arm_run_is_refused(self):
        with pytest.raises(ValueError, match="unknown arm"):
            cost_table(SCENES["t2b_flow_ordering"], [_score("convoy", 1.0)] * 2)


def _table() -> dict:
    scores = [_score("oracle", 190.0, run="a"), _score("oracle", 190.0, run="b"),
              _score("alternative", 300.0, censored=True, run="a"),
              _score("alternative", 300.0, censored=True, run="b"),
              _score("pair_yield", 260.0, censored=True, run="a"),
              _score("pair_yield", 260.0, censored=True, run="b")]
    return cost_table(SCENES["convoy_counterflow"], scores)


class TestRegret:
    def test_convoy_and_platoon_yield_score_the_same_regret_with_their_labels(self):
        table = _table()
        convoy = score_regret(table, _first_decision(
            "config/mock_decisions/convoy_counterflow_convoy_once.json"))
        yield_ = score_regret(table, _first_decision(
            "config/mock_decisions/convoy_counterflow_oracle_order_once.json"))
        assert convoy["arm"] == yield_["arm"] == "oracle"
        assert convoy["regret_sec"] == yield_["regret_sec"] == 0.0
        assert (convoy["label"], convoy["label_accepted"]) == ("convoy", True)
        assert (yield_["label"], yield_["label_accepted"]) == ("yield", True)

    def test_censored_arm_regret_is_a_lower_bound(self):
        result = score_regret(_table(), _first_decision(
            "config/mock_decisions/convoy_counterflow_alternative_order_once.json"))
        assert result["arm"] == "alternative"
        assert result["regret_sec"] == 410.0
        assert result["regret_is_lower_bound"] is True

    def test_decision_outside_the_swept_arms_is_unmapped(self):
        decision = {
            "congestion_detected": True, "type": "deadlock",
            "involved_robots": ["robot_1", "robot_2", "robot_3", "robot_4"],
            "root_cause": "x", "strategy": "reroute", "justification": "x",
        }
        result = score_regret(_table(), decision)
        assert result["arm"] is None and result["regret_sec"] is None
        assert result["roles"] == ["reroute", "robot_1"]

    def test_artifact_degradation_maps_the_refused_yield_to_its_reroute(self):
        scores = [_score(arm, total, run=r) for arm, total in
                  (("oracle", 130.0), ("alternative", 200.0), ("wait", 300.0))
                  for r in ("a", "b")]
        table = cost_table(SCENES["bottleneck_merge"], scores)
        artifact = {
            "decision": _first_decision(
                "config/mock_decisions/bottleneck_merge_alternative_order_once.json"),
            "grounding_degradations": [
                "yield=infeasible:no backup distance in band [0.5, 2.0] m satisfies "
                "clearance 1.7 m"
            ],
            "yield_refusal_reason": None,
            "scene": None,
        }
        result = score_regret(table, artifact)
        assert result["roles"] == ["reroute", "robot_1"]
        assert result["roles_source"] == "artifact_degradation"
        assert (result["arm"], result["regret_sec"]) == ("alternative", 70.0)

    def test_artifact_refusal_maps_to_the_wait_fan_out(self):
        scores = [_score(arm, total, run=r) for arm, total in
                  (("oracle", 130.0), ("wait", 300.0)) for r in ("a", "b")]
        table = cost_table(SCENES["bottleneck_merge"], scores)
        artifact = {
            "decision": _first_decision("config/mock_decisions/bottleneck_merge_yield_once.json"),
            "yield_refusal_reason": "yield refused: both robots outside the corridor",
            "grounding_degradations": [],
            "scene": None,
        }
        result = score_regret(table, artifact)
        assert result["arm"] == "wait" and result["regret_sec"] == 170.0

    def test_grounded_command_roles_take_precedence(self):
        record = {
            "decision": {"strategy": "convoy"},
            "grounded_command": {"actions": [
                {"robot_id": "robot_2", "action": "yield",
                 "parameters": {"crossing_order": ["robot_1", "robot_3", "robot_4"]}},
            ]},
        }
        assert roles_from_command(record["grounded_command"]) == (
            "yield", "robot_2", ("robot_1", "robot_3", "robot_4")
        )
        assert score_regret(_table(), record)["arm"] == "oracle"

    def test_all_censored_table_defines_no_regret(self):
        scores = [_score(arm, 300.0, censored=True, run=r)
                  for arm in ("oracle", "alternative") for r in ("a", "b")]
        table = cost_table(SCENES["t2b_flow_ordering"], scores)
        result = score_regret(table, _first_decision(
            "config/mock_decisions/t2b_oracle_order_once.json"))
        assert result["arm"] == "oracle" and result["regret_sec"] is None
        assert "censored" in result["note"]


def _write_gt(directory: Path, arrivals: dict[str, float | None], end: float) -> Path:
    directory.mkdir(parents=True)
    rows = []
    for step in range(int(end) + 1):
        t = float(step)
        robots = {}
        for rid, at in arrivals.items():
            arrived = at is not None and t >= at
            robots[rid] = {"speed_mps": 0.0 if arrived else 0.1,
                           "distance_to_goal_m": 0.1 if arrived else 2.0}
        rows.append({"sim_time_sec": t, "robots": robots})
    (directory / "ground_truth.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    return directory


class TestCli:
    def test_score_then_regret_round_trip(self, tmp_path, capsys):
        runs = []
        for arm, arrivals in (("oracle", {"robot_1": 50.0, "robot_2": 60.0}),
                              ("alternative", {"robot_1": 80.0, "robot_2": None})):
            for seed in (42, 43):
                gt = _write_gt(tmp_path / f"{arm}_{seed}" / "gt", arrivals, 100.0)
                runs += ["--run", f"{arm}:{gt}"]
        out = tmp_path / "table.json"
        assert main(["score", "--scene", "t2b_flow_ordering", *runs, "--out", str(out)]) == 0
        table = json.loads(out.read_text())
        assert table["best_arm"] == "oracle"
        assert table["arms"]["alternative"]["censored"] is True
        decision = tmp_path / "decision.json"
        decision.write_text(
            (ROOT / "config/mock_decisions/t2b_alternative_order_once.json").read_text()
        )
        capsys.readouterr()
        assert main(["regret", "--table", str(out), "--decision", str(decision)]) == 0
        result = json.loads(capsys.readouterr().out)
        assert result["arm"] == "alternative" and result["regret_is_lower_bound"] is True

    def test_plan_tsv(self, capsys):
        assert main(["plan", "--scene", "bottleneck_merge", "--seeds", "42", "--tsv"]) == 0
        lines = capsys.readouterr().out.strip().splitlines()
        assert [line.split("\t")[0] for line in lines] == ["oracle", "alternative", "wait"]

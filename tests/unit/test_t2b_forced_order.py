"""Tests for the T2b forced-order harness (scripts/t2b_forced_order.py and its VM driver).

Nothing here runs Isaac: the driver is exercised against a scratch tree whose
fc_launch.sh is a stub that writes synthetic ground truth.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from isaac.vgu_sim.config import ScenarioConfig
from scripts.t2b_forced_order import (
    ARMS,
    REQUIRED_COMMITS,
    REQUIRED_SIGNATURES,
    T2B_CORRIDOR,
    T2B_INITIAL_TASKS,
    margin_record,
    plan_runs,
    preflight,
    score_ground_truth,
    write_margin,
)

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "scripts" / "vm" / "t2b_forced_order.sh"
SCENARIO_RELPATH = Path("isaac/config/scenarios/t2b_flow_ordering.yaml")
GOALS = {"robot_1": (2.5, 0.0), "robot_2": (-2.0, 0.0), "robot_3": (1.85, 0.0)}


def _t2b_tree(tmp_path: Path) -> Path:
    """A copy of the files preflight reads, configured for T2b."""
    repo = tmp_path / "repo"
    paths = {relpath for relpath, _needle, _what in REQUIRED_SIGNATURES}
    paths |= {
        str(SCENARIO_RELPATH),
        "ros2_ws/src/swarm_simulation/maps/warehouse_map_t2b_flow_ordering.yaml",
        *(spec.mock_decision_file for spec in ARMS.values()),
    }
    for relpath in paths:
        (repo / relpath).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relpath, repo / relpath)
    orch = yaml.safe_load(
        (ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml").read_text()
    )
    orch["initial_tasks"] = T2B_INITIAL_TASKS
    orch["scenario_geometry"]["corridor"].update(T2B_CORRIDOR)
    orch_path = repo / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
    orch_path.parent.mkdir(parents=True, exist_ok=True)
    orch_path.write_text(yaml.safe_dump(orch), encoding="utf-8")
    rag = yaml.safe_load((ROOT / "config/rag.yaml").read_text())
    rag["grounding"]["mode"] = "legacy"
    (repo / "config/rag.yaml").write_text(yaml.safe_dump(rag), encoding="utf-8")
    return repo


class TestPreflight:
    def test_this_tree_has_every_safety_symbol_and_commit(self):
        problems = preflight(ROOT)
        assert not [p for p in problems if "missing" in p and "file" not in p]
        assert not [p for p in problems if "ancestor" in p]

    def test_this_tree_as_shipped_is_refused_for_its_config(self):
        # The shipped configs are the two-robot family's: the operator must
        # set T2b's by hand, and the preflight says what is missing.
        problems = preflight(ROOT)
        assert any("initial_tasks lacks robot_3" in p for p in problems)
        assert any("half_length_m" in p for p in problems)
        assert any("grounding.mode is 'derived'" in p for p in problems)

    def test_a_t2b_configured_tree_passes(self, tmp_path):
        assert preflight(_t2b_tree(tmp_path)) == []

    @pytest.mark.parametrize("index", range(len(REQUIRED_SIGNATURES)))
    def test_each_missing_safety_symbol_refuses(self, tmp_path, index):
        repo = _t2b_tree(tmp_path)
        relpath, needle, what = REQUIRED_SIGNATURES[index]
        path = repo / relpath
        path.write_text(path.read_text().replace(needle, "REMOVED"), encoding="utf-8")
        problems = preflight(repo)
        assert any(what in p for p in problems)

    def test_missing_hold_back_delay_refuses(self, tmp_path):
        repo = _t2b_tree(tmp_path)
        orch_path = repo / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
        orch = yaml.safe_load(orch_path.read_text())
        del orch["initial_tasks"]["robot_3"]["start_delay_sec"]
        orch_path.write_text(yaml.safe_dump(orch), encoding="utf-8")
        assert any("robot_3.start_delay_sec is 0.0" in p for p in preflight(repo))

    def test_a_git_tree_without_the_safety_commits_refuses(self, tmp_path):
        repo = _t2b_tree(tmp_path)
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "x"]):
            subprocess.run(["git", "-C", str(repo), *cmd], check=True, env=env,
                           capture_output=True)
        problems = preflight(repo)
        assert len([p for p in problems if "not an ancestor" in p]) == len(REQUIRED_COMMITS)

    def test_the_required_commits_include_both_safety_commits(self):
        assert {"9c38042", "38868d2"} <= set(REQUIRED_COMMITS)


def test_plan_interleaves_the_arms_per_seed():
    runs = plan_runs([42, 43])
    assert [(r["arm"], r["seed"]) for r in runs] == [
        ("oracle", 42), ("alternative", 42), ("oracle", 43), ("alternative", 43),
    ]
    assert all((ROOT / r["mock_decision_file"]).is_file() for r in runs)


def _write_gt(gt_dir: Path, arrivals: dict[str, float | None], end: float = 200.0,
              depart: float = 11.0) -> Path:
    """Synthetic ground truth: each robot closes on its goal and parks at `arrivals`."""
    gt_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    t = 0.0
    while t <= end + 1e-9:
        robots = {}
        for rid, arrive in arrivals.items():
            if arrive is not None and t >= arrive:
                distance = 0.05
            else:
                distance = 4.0 if t < depart else max(0.6, 4.0 - 0.1 * (t - depart))
            robots[rid] = {"distance_to_goal_m": distance, "goal_x": GOALS[rid][0],
                           "goal_y": GOALS[rid][1], "speed_mps": 0.0 if t < depart else 0.1,
                           "theta": 0.0, "x": 0.0, "y": 0.0}
        rows.append({"robots": robots, "sim_time_sec": round(t, 3)})
        t += 0.5
    (gt_dir / "ground_truth.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    (gt_dir / "run_manifest.json").write_text(json.dumps({"run_id": gt_dir.parent.name}))
    return gt_dir


class TestScore:
    def test_total_is_the_sum_of_time_to_goal_from_departure(self, tmp_path):
        gt = _write_gt(tmp_path / "r" / "gt", {"robot_1": 60.0, "robot_2": 120.0, "robot_3": 100.0})
        score = score_ground_truth("oracle", gt)
        assert score.t0_sec == 11.0
        assert score.total_sec == pytest.approx((60 - 11) + (120 - 11) + (100 - 11))
        assert score.censored is False

    def test_a_robot_that_never_arrives_counts_to_the_end_and_censors(self, tmp_path):
        gt = _write_gt(tmp_path / "r" / "gt", {"robot_1": 60.0, "robot_2": None,
                                                "robot_3": None}, end=200.0)
        score = score_ground_truth("alternative", gt)
        assert score.censored is True
        assert score.total_sec == pytest.approx((60 - 11) + 2 * (200 - 11))

    def test_passing_through_the_goal_is_not_an_arrival(self, tmp_path):
        gt = _write_gt(tmp_path / "r" / "gt", {"robot_1": 60.0, "robot_2": 120.0,
                                                "robot_3": 100.0})
        path = gt / "ground_truth.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for row in rows:  # robot_3 touches its goal at t=40 and leaves again
            if 40.0 <= row["sim_time_sec"] < 41.0:
                row["robots"]["robot_3"]["distance_to_goal_m"] = 0.1
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        assert score_ground_truth("oracle", gt).arrivals_sec["robot_3"] == 100.0

    def _scores(self, tmp_path, alternative_arrival_3):
        scores = []
        for seed in (42, 43):
            scores.append(score_ground_truth("oracle", _write_gt(
                tmp_path / f"o{seed}" / "gt", {"robot_1": 60.0, "robot_2": 120.0,
                                               "robot_3": 100.0})))
            scores.append(score_ground_truth("alternative", _write_gt(
                tmp_path / f"a{seed}" / "gt", {"robot_1": 150.0, "robot_2": 70.0,
                                               "robot_3": alternative_arrival_3})))
        return scores

    def test_margin_record_validates_as_the_scenario_margin(self, tmp_path):
        record = margin_record(self._scores(tmp_path, 180.0))
        assert record["n_per_order"] == 2
        assert record["censored"] is False
        assert record["margin"] == pytest.approx(
            record["alternative_total_sec"] / record["oracle_total_sec"] - 1, abs=1e-4
        )
        data = yaml.safe_load((ROOT / SCENARIO_RELPATH).read_text())
        data["oracle"]["margin"] = record
        oracle = ScenarioConfig.model_validate(data).oracle
        assert oracle.margin.passes is True

    def test_a_never_finishing_alternative_is_a_censored_lower_bound(self, tmp_path):
        record = margin_record(self._scores(tmp_path, None))
        assert record["censored"] is True

    def test_a_failed_oracle_run_refuses_to_score(self, tmp_path):
        scores = self._scores(tmp_path, 180.0)
        scores.append(score_ground_truth("oracle", _write_gt(
            tmp_path / "o44" / "gt", {"robot_1": 60.0, "robot_2": None, "robot_3": 100.0})))
        with pytest.raises(ValueError, match="oracle runs never finished"):
            margin_record(scores)

    def test_one_run_per_order_is_not_enough(self, tmp_path):
        with pytest.raises(ValueError, match="need >= 2"):
            margin_record(self._scores(tmp_path, 180.0)[:2])

    def test_write_margin_replaces_only_the_placeholder(self, tmp_path):
        scenario = tmp_path / "t2b.yaml"
        original = (ROOT / SCENARIO_RELPATH).read_text()
        scenario.write_text(original)
        record = margin_record(self._scores(tmp_path, 180.0))
        text = write_margin(scenario, record)
        changed = [
            (a, b) for a, b in zip(original.splitlines(), text.splitlines(), strict=True)
            if a != b
        ]
        assert len(changed) == 1 and changed[0][0] == "  margin: null"
        oracle = ScenarioConfig.model_validate(yaml.safe_load(text)).oracle
        assert oracle.margin.alternative_order == ("robot_2", "robot_3")
        with pytest.raises(ValueError, match="exactly one"):
            write_margin(scenario, record)


_STUB_FC_LAUNCH = r"""#!/usr/bin/env bash
# Test stand-in for fc_launch.sh: records its env and writes ground truth the
# way Isaac names it; the oracle arm finishes sooner.
set -eu
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "STUB SCENARIO=${SCENARIO} SEED=${SEED} MOCK=${MOCK_DECISION_FILE} REC_SEC=${REC_SEC}"
echo "[fc-launch] logs saved to ${REPO}/data/logs/fc_run_20260928_1200${SEED}/tail_logs.txt"
gt="$REPO/data/logs/simulation/${SCENARIO}-seed${SEED}-rep000"
mkdir -p "$gt"
case "$MOCK_DECISION_FILE" in *oracle*) late=100 ;; *) late=180 ;; esac
"$PYTHON" "$REPO/make_gt.py" "$gt" "$late"
"""

_MAKE_GT = r"""
import json, sys
from pathlib import Path
gt, late = Path(sys.argv[1]), float(sys.argv[2])
rows = []
for i in range(401):
    t = i * 0.5
    robots = {}
    for rid, arrive in (("robot_1", 60.0), ("robot_2", late + 20.0), ("robot_3", late)):
        d = 0.05 if t >= arrive else (4.0 if t < 11 else max(0.6, 4.0 - 0.1 * (t - 11)))
        robots[rid] = {"distance_to_goal_m": d, "speed_mps": 0.0 if t < 11 else 0.1}
    rows.append({"robots": robots, "sim_time_sec": t})
(gt / "ground_truth.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
(gt / "run_manifest.json").write_text(json.dumps({"run_id": gt.name}))
"""


def test_driver_runs_every_arm_and_seed_then_scores(tmp_path):
    repo = _t2b_tree(tmp_path)
    stub = repo / "scripts" / "vm" / "fc_launch.sh"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text(_STUB_FC_LAUNCH)
    (repo / "make_gt.py").write_text(_MAKE_GT)
    shims = tmp_path / "bin"
    shims.mkdir()
    for name in ("sudo", "uptime"):
        (shims / name).write_text("#!/bin/sh\nexit 0\n")
        (shims / name).chmod(0o755)
    out = tmp_path / "out"
    env = {**os.environ, "REPO": str(repo), "OUT": str(out), "SEEDS": "42 43",
           "SETTLE_SEC": "0", "PYTHON": sys.executable,
           "PATH": f"{shims}:{Path(sys.executable).parent}:{os.environ['PATH']}"}

    completed = subprocess.run(["bash", str(DRIVER)], env=env, capture_output=True,
                               text=True, check=False, timeout=120)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    for label in ("oracle_seed42", "alternative_seed42", "oracle_seed43", "alternative_seed43"):
        assert (out / label / "gt" / "ground_truth.jsonl").is_file()
        condition = (out / label / "CONDITION.txt").read_text()
        assert f"arm={label.split('_')[0]}" in condition
    launcher = (out / "alternative_seed43" / "launcher.log").read_text()
    assert "SEED=43 MOCK=config/mock_decisions/t2b_alternative_order_once.json" in launcher
    record = json.loads((out / "margin.json").read_text())
    assert record["n_per_order"] == 2 and record["margin"] > 0.2
    # The scenario is never written by the driver.
    assert "  margin: null" in (repo / SCENARIO_RELPATH).read_text()


def test_driver_refuses_to_run_when_preflight_fails(tmp_path):
    repo = _t2b_tree(tmp_path)
    safety = repo / "ros2_ws/src/swarm_execution/swarm_execution/safety.py"
    safety.write_text(safety.read_text().replace("class ClearingExemption", "class X"))
    stub = repo / "scripts" / "vm" / "fc_launch.sh"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text("#!/usr/bin/env bash\ntouch \"$(dirname \"$0\")/RAN\"\n")
    env = {**os.environ, "REPO": str(repo), "OUT": str(tmp_path / "out"),
           "PYTHON": sys.executable}

    completed = subprocess.run(["bash", str(DRIVER)], env=env, capture_output=True,
                               text=True, check=False, timeout=60)

    assert completed.returncode == 1
    assert "REFUSING TO RUN" in completed.stderr
    assert "pair-scoped clearing exemption (9c38042)" in completed.stderr
    assert not (stub.parent / "RAN").exists()


def _git_init_commit(repo: Path) -> dict[str, str]:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "x"]):
        subprocess.run(["git", "-C", str(repo), *cmd], check=True, env=env,
                       capture_output=True)
    return env


def test_an_rsync_deployed_tree_over_an_old_checkout_relies_on_symbols(tmp_path):
    # HEAD lacks the safety commits, but the files were synced on top of it:
    # ancestry cannot speak for them, the symbol checks do.
    repo = _t2b_tree(tmp_path)
    safety = repo / "ros2_ws/src/swarm_execution/swarm_execution/safety.py"
    text = safety.read_text()
    safety.write_text(text.replace("class ClearingExemption", "class X"))
    _git_init_commit(repo)
    safety.write_text(text)
    assert preflight(repo) == []


def _run_score(tmp_path, alternative_arrival_3, *extra):
    runs = []
    for seed in (42, 43):
        runs += ["--run", "oracle:" + str(_write_gt(
            tmp_path / f"o{seed}" / "gt", {"robot_1": 60.0, "robot_2": 120.0, "robot_3": 100.0}))]
        runs += ["--run", "alternative:" + str(_write_gt(
            tmp_path / f"a{seed}" / "gt",
            {"robot_1": 150.0, "robot_2": 70.0, "robot_3": alternative_arrival_3}))]
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "t2b_forced_order.py"), "score", *runs, *extra],
        capture_output=True, text=True, check=False,
    )


def test_score_reports_a_censored_margin_as_a_lower_bound_not_a_pass(tmp_path):
    completed = _run_score(tmp_path, None)
    assert completed.returncode == 0, completed.stderr
    assert "LOWER-BOUND (feasibility contrast" in completed.stdout
    assert " PASS" not in completed.stdout


def test_score_refuses_to_write_a_censored_margin_without_consent(tmp_path):
    completed = _run_score(tmp_path, None, "--write-scenario")
    assert completed.returncode != 0
    assert "--accept-censored" in completed.stderr
    assert "  margin: null" in (ROOT / SCENARIO_RELPATH).read_text()


def test_score_reports_a_finished_margin_as_pass_or_fail(tmp_path):
    completed = _run_score(tmp_path, 180.0)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.rstrip().endswith("PASS")

#!/usr/bin/env python3
"""Forced-order verification harness for T2b (flow ordering).

The battery design's T2b oracle (`correct_order: [robot_1, robot_3]`,
`robot_2` yielding) is valid only if scripted executions of both orders show
the oracle order beating the alternative by >= 20% total time-to-goal. This
tool prepares and scores those executions; `scripts/vm/t2b_forced_order.sh`
runs them on the VM through `scripts/vm/fc_launch.sh`.

Arms (each a once-style mock decision script, legacy grounding):

- `oracle`: `robot_2` yields, `robot_1` then `robot_3` cross.
- `alternative`: `robot_1` yields, `robot_2` then `robot_3` cross — the other
  order the first-passer guard (`38868d2`) permits (its first passer is the
  standoff partner).

Subcommands:

- `preflight --repo <tree>`: refuse to run unless the deployed tree carries
  the T2b safety slice (pair-scoped exemption, ordered release, first-passer
  guard, one passer parser) and the hold-back, and M5/M3 are configured for
  T2b. Stdlib + PyYAML only, so it runs on the VM host.
- `plan`: print the run matrix for `--seeds`.
- `score --run <arm>:<ground-truth dir> ...`: total time-to-goal per run from
  Isaac ground truth, the margin, and optionally `--write-scenario` to record
  it in the scenario's `oracle.margin`.

Usage:
    python3 scripts/t2b_forced_order.py preflight --repo /home/ubuntu/vgu-vlm-swarm
    python3 scripts/t2b_forced_order.py plan --seeds 42 43
    python3 scripts/t2b_forced_order.py score \\
        --run oracle:runs/oracle_seed42/gt --run oracle:runs/oracle_seed43/gt \\
        --run alternative:runs/alternative_seed42/gt \\
        --run alternative:runs/alternative_seed43/gt --out margin.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = "t2b_flow_ordering"
SCENARIO_RELPATH = Path("isaac/config/scenarios") / f"{SCENARIO}.yaml"
ORCHESTRATOR_RELPATH = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
RAG_RELPATH = Path("config/rag.yaml")
MAP_RELPATH = Path("ros2_ws/src/swarm_simulation/maps") / f"warehouse_map_{SCENARIO}.yaml"


@dataclass(frozen=True)
class ArmSpec:
    """One forced order: who yields, who crosses in what order, and its mock."""

    yielder: str
    crossing_order: tuple[str, ...]
    mock_decision_file: str


ARMS: dict[str, ArmSpec] = {
    "oracle": ArmSpec(
        yielder="robot_2",
        crossing_order=("robot_1", "robot_3"),
        mock_decision_file="config/mock_decisions/t2b_oracle_order_once.json",
    ),
    "alternative": ArmSpec(
        yielder="robot_1",
        crossing_order=("robot_2", "robot_3"),
        mock_decision_file="config/mock_decisions/t2b_alternative_order_once.json",
    ),
}

# M5 settings the T2b runs need (set by hand in orchestrator.yaml, as the goal
# table there lists). The scenario YAML header justifies each value.
T2B_INITIAL_TASKS: dict[str, dict[str, Any]] = {
    "robot_1": {"task": "cross_narrow_aisle", "goal": [2.5, 0.0]},
    "robot_2": {"task": "cross_narrow_aisle", "goal": [-2.0, 0.0]},
    "robot_3": {"task": "cross_narrow_aisle", "goal": [1.85, 0.0], "start_delay_sec": 55.0},
}
T2B_CORRIDOR = {"axis": "x", "center_m": 0.0, "half_length_m": 0.5}
# The first-passer guard, and with it the alternative arm's yield, exists only
# in legacy grounding; derived mode grounds the alternative's backup infeasible
# (robot_3 inside the 1.7 m backup clearance) and degrades it to a reroute.
REQUIRED_GROUNDING_MODE = "legacy"

# The T2b safety slice and the hold-back, each by its commit and by a symbol it
# introduced. The symbol check holds on any deployed tree (git checkout or
# rsync copy); the commit check runs too when the tree is a git checkout.
REQUIRED_COMMITS: dict[str, str] = {
    "9c38042": "pair-scoped clearing exemption",
    "99f4699": "ordered hold-until-last release",
    "38868d2": "first-passer guard",
    "fc441d4": "one passer-order parser for monitor and bus",
    "daa2558": "per-robot start_delay_sec hold-back",
}
REQUIRED_SIGNATURES: tuple[tuple[str, str, str], ...] = (
    ("ros2_ws/src/swarm_execution/swarm_execution/safety.py", "class ClearingExemption",
     "pair-scoped clearing exemption (9c38042)"),
    ("ros2_ws/src/swarm_execution/swarm_execution/safety.py", "def covers_pair(",
     "pair-scoped clearing exemption (9c38042)"),
    ("ros2_ws/src/swarm_execution/swarm_execution/crossing_chain.py", "class CrossingChain",
     "ordered hold-until-last release (99f4699)"),
    ("reasoning/rag/command_grounder.py", "def _first_passer_refusal(",
     "first-passer guard (38868d2)"),
    ("ros2_ws/src/swarm_execution/swarm_execution/safety.py",
     "from swarm_execution.crossing_chain import plan_crossing",
     "one passer-order parser (fc441d4)"),
    ("ros2_ws/src/swarm_execution/swarm_execution/base_mission.py",
     'entry.get("start_pending")', "M4 honours the hold-back (daa2558)"),
    ("ros2_ws/src/swarm_orchestrator/swarm_orchestrator/task_registry.py",
     '["start_pending"] = True', "M5 publishes the hold-back (daa2558)"),
)

# Arrival: within M5's arrival_position_tolerance_m of the goal, and never
# farther than ARRIVAL_STAY_M afterwards (an escort passing through does not
# count).
ARRIVAL_TOLERANCE_M = 0.35
ARRIVAL_STAY_M = 0.5
# First ground-truth sample with a robot faster than this is the common t0.
DEPARTURE_SPEED_MPS = 0.03
MIN_RUNS_PER_ORDER = 2


def preflight(repo: Path) -> list[str]:
    """Check a deployed tree is safe and configured for the T2b forced orders.

    Args:
        repo: Root of the tree the runs will use.

    Returns:
        One message per failed check; empty when the tree may run.
    """
    problems: list[str] = []
    for relpath, needle, what in REQUIRED_SIGNATURES:
        path = repo / relpath
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if needle not in text:
            problems.append(f"missing {what}: {needle!r} not in {relpath}")
    if (repo / ".git").exists():
        for commit, what in REQUIRED_COMMITS.items():
            ancestor = subprocess.run(
                ["git", "-C", str(repo), "merge-base", "--is-ancestor", commit, "HEAD"],
                capture_output=True, check=False,
            )
            if ancestor.returncode != 0:
                problems.append(f"missing {what}: commit {commit} is not an ancestor of HEAD")
    for relpath in (SCENARIO_RELPATH, MAP_RELPATH, *(Path(a.mock_decision_file)
                                                      for a in ARMS.values())):
        if not (repo / relpath).is_file():
            problems.append(f"missing file {relpath}")
    problems += _check_orchestrator(repo / ORCHESTRATOR_RELPATH)
    problems += _check_grounding(repo / RAG_RELPATH)
    return problems


def _check_orchestrator(path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing file {path}"]
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    problems = []
    tasks = config.get("initial_tasks") or {}
    for robot_id, expected in T2B_INITIAL_TASKS.items():
        actual = tasks.get(robot_id)
        if actual is None:
            problems.append(f"orchestrator.yaml initial_tasks lacks {robot_id}")
            continue
        for key, value in expected.items():
            got = actual.get(key, 0.0 if key == "start_delay_sec" else None)
            if (list(got) if isinstance(got, (list, tuple)) else got) != value:
                problems.append(
                    f"orchestrator.yaml initial_tasks.{robot_id}.{key} is {got!r}, "
                    f"T2b needs {value!r}"
                )
    extra = sorted(set(tasks) - set(T2B_INITIAL_TASKS))
    if extra:
        problems.append(f"orchestrator.yaml initial_tasks has robots T2b lacks: {extra}")
    corridor = ((config.get("scenario_geometry") or {}).get("corridor")) or {}
    for key, value in T2B_CORRIDOR.items():
        if corridor.get(key) != value:
            problems.append(
                f"orchestrator.yaml scenario_geometry.corridor.{key} is "
                f"{corridor.get(key)!r}, T2b needs {value!r}"
            )
    if config.get("t0_probe_mode"):
        problems.append("orchestrator.yaml t0_probe_mode must be false for T2b")
    return problems


def _check_grounding(path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing file {path}"]
    grounding = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("grounding") or {}
    mode = grounding.get("mode", "legacy")
    if mode != REQUIRED_GROUNDING_MODE:
        return [
            f"config/rag.yaml grounding.mode is {mode!r}; the forced orders need "
            f"{REQUIRED_GROUNDING_MODE!r} (the first-passer guard and the alternative "
            "arm's yield are legacy-only)"
        ]
    return []


def plan_runs(seeds: list[int]) -> list[dict[str, Any]]:
    """Return the run matrix, arms interleaved per seed so drift hits both.

    Args:
        seeds: Isaac seeds; each arm runs once per seed.

    Returns:
        One entry per run: arm, seed, the mock decision file, and the label
        the VM driver names the run's output directory with.
    """
    return [
        {
            "arm": arm,
            "seed": seed,
            "mock_decision_file": spec.mock_decision_file,
            "label": f"{arm}_seed{seed}",
        }
        for seed in seeds
        for arm, spec in ARMS.items()
    ]


@dataclass(frozen=True)
class RunScore:
    """Total time-to-goal of one forced-order run."""

    arm: str
    run_id: str
    t0_sec: float
    arrivals_sec: dict[str, float | None]
    end_sec: float

    @property
    def censored(self) -> bool:
        """True when some robot never arrived before the run ended."""
        return any(value is None for value in self.arrivals_sec.values())

    @property
    def total_sec(self) -> float:
        """Sum over robots of time-to-goal from t0; a missing arrival counts to the end."""
        return sum(
            (self.end_sec if at is None else at) - self.t0_sec for at in self.arrivals_sec.values()
        )


def score_ground_truth(arm: str, gt_dir: Path) -> RunScore:
    """Score one run from Isaac's `ground_truth.jsonl` (sim time, true poses).

    Args:
        arm: The arm the run executed.
        gt_dir: Directory holding `ground_truth.jsonl` (and optionally
            `run_manifest.json`, whose `run_id` names the run).

    Returns:
        The run's arrivals and total.

    Raises:
        ValueError: If the file has no samples or no robot ever moves.
    """
    rows = [
        json.loads(line)
        for line in (gt_dir / "ground_truth.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError(f"{gt_dir}: empty ground truth")
    t0 = next(
        (
            row["sim_time_sec"]
            for row in rows
            if any(r["speed_mps"] > DEPARTURE_SPEED_MPS for r in row["robots"].values())
        ),
        None,
    )
    if t0 is None:
        raise ValueError(f"{gt_dir}: no robot ever moved")
    robot_ids = sorted(rows[0]["robots"])
    arrivals: dict[str, float | None] = {}
    for robot_id in robot_ids:
        distances = [(row["sim_time_sec"], row["robots"][robot_id]["distance_to_goal_m"])
                     for row in rows if robot_id in row["robots"]]
        arrival = None
        for index, (stamp, distance) in enumerate(distances):
            if distance <= ARRIVAL_TOLERANCE_M and all(
                later <= ARRIVAL_STAY_M for _t, later in distances[index:]
            ):
                arrival = stamp
                break
        arrivals[robot_id] = arrival
    manifest = gt_dir / "run_manifest.json"
    run_id = gt_dir.parent.name if gt_dir.name in ("gt", "ground_truth") else gt_dir.name
    if manifest.is_file():
        run_id = f"{run_id}:{json.loads(manifest.read_text(encoding='utf-8')).get('run_id')}"
    return RunScore(arm=arm, run_id=run_id, t0_sec=t0, arrivals_sec=arrivals,
                    end_sec=rows[-1]["sim_time_sec"])


def margin_record(scores: list[RunScore]) -> dict[str, Any]:
    """Build the scenario's `oracle.margin` record from scored runs of both arms.

    Args:
        scores: Every scored run.

    Returns:
        The record as `OracleMarginRecord` fields.

    Raises:
        ValueError: If an arm has fewer than `MIN_RUNS_PER_ORDER` runs, or an
            oracle run never finished (the oracle order itself failed, so no
            margin is meaningful).
    """
    by_arm = {arm: [s for s in scores if s.arm == arm] for arm in ARMS}
    for arm, runs in by_arm.items():
        if len(runs) < MIN_RUNS_PER_ORDER:
            raise ValueError(f"{arm}: {len(runs)} run(s), need >= {MIN_RUNS_PER_ORDER}")
    failed = [s.run_id for s in by_arm["oracle"] if s.censored]
    if failed:
        raise ValueError(f"oracle runs never finished: {failed}; re-author, do not score")
    oracle_total = sum(s.total_sec for s in by_arm["oracle"]) / len(by_arm["oracle"])
    alternative = by_arm["alternative"]
    alternative_total = sum(s.total_sec for s in alternative) / len(alternative)
    spec = ARMS["alternative"]
    return {
        "metric": "total_time_to_goal_sec",
        "oracle_total_sec": round(oracle_total, 3),
        "alternative_total_sec": round(alternative_total, 3),
        "alternative_yielder": spec.yielder,
        "alternative_order": list(spec.crossing_order),
        "margin": round(round(alternative_total, 3) / round(oracle_total, 3) - 1.0, 4),
        "threshold": 0.20,
        "censored": any(s.censored for s in alternative),
        "n_per_order": min(len(runs) for runs in by_arm.values()),
        "run_ids": [s.run_id for s in scores],
    }


_MARGIN_LINE = re.compile(r"^(  margin:) null\b.*$", re.M)


def write_margin(scenario_path: Path, record: dict[str, Any]) -> str:
    """Replace the scenario's `  margin: null` line with the record.

    Args:
        scenario_path: The T2b scenario YAML.
        record: `margin_record` output.

    Returns:
        The new file text (also written).

    Raises:
        ValueError: If the file has no single `  margin: null` placeholder.
    """
    text = scenario_path.read_text(encoding="utf-8")
    if len(_MARGIN_LINE.findall(text)) != 1:
        raise ValueError(f"{scenario_path}: expected exactly one '  margin: null' line")
    flow = json.dumps(record, separators=(", ", ": "))
    new = _MARGIN_LINE.sub(lambda m: f"{m.group(1)} {flow}", text)
    scenario_path.write_text(new, encoding="utf-8")
    return new


def _cmd_preflight(args: argparse.Namespace) -> int:
    problems = preflight(Path(args.repo))
    for problem in problems:
        print(f"PREFLIGHT FAIL: {problem}", file=sys.stderr)
    if problems:
        return 1
    print("PREFLIGHT OK: safety slice, hold-back and T2b config present")
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    for run in plan_runs(args.seeds):
        if args.tsv:
            print("\t".join(str(run[k]) for k in ("arm", "seed", "mock_decision_file", "label")))
        else:
            print(json.dumps(run))
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    scores = []
    for item in args.run:
        arm, _, path = item.partition(":")
        if arm not in ARMS or not path:
            raise SystemExit(f"--run must be <{'|'.join(ARMS)}>:<ground-truth dir>; got {item!r}")
        scores.append(score_ground_truth(arm, Path(path)))
    for score in scores:
        arrivals = {k: (None if v is None else round(v - score.t0_sec, 2))
                    for k, v in score.arrivals_sec.items()}
        print(f"{score.arm:12s} {score.run_id}  total={score.total_sec:.2f}s "
              f"censored={score.censored} time_to_goal={arrivals}")
    record = margin_record(scores)
    verdict = "PASS" if record["margin"] >= record["threshold"] else "FAIL"
    bound = " (lower bound: an alternative run never finished)" if record["censored"] else ""
    print(f"margin={record['margin']:.4f} threshold={record['threshold']} {verdict}{bound}")
    if args.out:
        Path(args.out).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if args.write_scenario:
        sys.path.insert(0, str(REPO_ROOT))
        from isaac.vgu_sim.config import ScenarioConfig

        path = REPO_ROOT / SCENARIO_RELPATH
        ScenarioConfig.model_validate(yaml.safe_load(write_margin(path, record)))
        print(f"wrote oracle.margin to {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight", help="refuse unless the tree may run T2b forced orders")
    pre.add_argument("--repo", default=str(REPO_ROOT))
    pre.set_defaults(func=_cmd_preflight)
    plan = sub.add_parser("plan", help="print the run matrix")
    plan.add_argument("--seeds", type=int, nargs="+", default=[42, 43])
    plan.add_argument("--tsv", action="store_true", help="arm, seed, mock, label per line")
    plan.set_defaults(func=_cmd_plan)
    score = sub.add_parser("score", help="score runs and compute the margin")
    score.add_argument("--run", action="append", required=True)
    score.add_argument("--out")
    score.add_argument("--write-scenario", action="store_true")
    score.set_defaults(func=_cmd_score)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

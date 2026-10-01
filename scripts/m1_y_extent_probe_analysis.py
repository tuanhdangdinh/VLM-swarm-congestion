#!/usr/bin/env python3
"""Offline scorer for the M1 y-extent verification probe (v2 build-order step 3).

Each probe run (`scripts/vm/m1_y_extent_probe.sh`) holds four robots
STATIONARY at known spawn poses for the whole episode, so unlike a moving
scenario there is no need to time-match M1's scene log against ground truth:
the nominal position *is* the scenario's authored spawn (confirmed by GT to
settle within ~0.0002 m of it, see the `gt_settle_bias_m` column below), and
every measured pose can be compared against that constant directly.

For each robot in a run this reports, from `m5_scene.jsonl` (M5's per-second
copy of `/perception/scene_state`, `swarm_orchestrator/reasoning_pipeline.py
append_scene_log`):

- `rows`: total scene rows carrying this robot.
- `fresh`: rows where M1's status is not STALE (a STALE row is a carried-
  forward last-known pose, not a new detection -- CLAUDE.md's "late/lost
  frames" convention).
- `fresh_rate`: fresh / rows.
- `longest_stale_streak`: the longest run of consecutive STALE rows, for
  distinguishing "briefly drops out, recovers" from "latches permanently".
- `bias_x_m` / `bias_y_m`: mean, median and max absolute error of M1's
  (x, y) against the scenario's authored spawn, over fresh rows only.

And from `gt/ground_truth.jsonl` (Isaac's own chassis-prim samples, ~10 Hz
sim time): `gt_settle_bias_m`, the max absolute deviation of the robot's
true pose from its authored spawn over the whole run -- confirms the robot
actually stayed put (it is not M1's job to correct for a robot that moved).

Usage:
    python3 scripts/m1_y_extent_probe_analysis.py <run_dir> [<run_dir> ...]

<run_dir> is one `data/logs/vm_runs/y_extent_probe/<a|b>_<stamp>/` directory,
holding `scenario.yaml`, `m5_scene.jsonl` and `gt/ground_truth.jsonl` (see
`scripts/vm/m1_y_extent_probe.sh`'s collection step).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean, median


def load_spawns(scenario_yaml: Path) -> dict[str, tuple[float, float]]:
    """Read each robot's authored spawn (x, y) from a probe scenario yaml.

    Args:
        scenario_yaml: Path to the scenario's `isaac/config/scenarios/*.yaml`.

    Returns:
        Mapping of robot_id to its authored `(x, y)` spawn in world meters.
    """
    import yaml

    data = yaml.safe_load(scenario_yaml.read_text())
    return {r["robot_id"]: (r["spawn"]["x"], r["spawn"]["y"]) for r in data["robots"]}


def score_scene_log(scene_log: Path, spawns: dict[str, tuple[float, float]]) -> dict:
    """Score one run's M1 scene log against its scenario's authored spawns.

    Args:
        scene_log: Path to `m5_scene.jsonl`.
        spawns: robot_id -> authored (x, y), from `load_spawns`.

    Returns:
        Mapping of robot_id to its per-robot score dict (see module docstring).
    """
    per_robot: dict[str, dict] = {
        rid: {"rows": 0, "fresh": 0, "errors_x": [], "errors_y": [], "stale_run": 0, "longest_stale_streak": 0}
        for rid in spawns
    }
    for line in scene_log.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        for robot in record["scene"]["robots"]:
            rid = robot["robot_id"]
            if rid not in per_robot:
                continue
            state = per_robot[rid]
            state["rows"] += 1
            if robot["status"] == "STALE":
                state["stale_run"] += 1
                state["longest_stale_streak"] = max(state["longest_stale_streak"], state["stale_run"])
            else:
                state["stale_run"] = 0
                state["fresh"] += 1
                sx, sy = spawns[rid]
                state["errors_x"].append(abs(robot["x"] - sx))
                state["errors_y"].append(abs(robot["y"] - sy))

    results = {}
    for rid, state in per_robot.items():
        ex, ey = state["errors_x"], state["errors_y"]
        results[rid] = {
            "spawn": spawns[rid],
            "rows": state["rows"],
            "fresh": state["fresh"],
            "fresh_rate": round(state["fresh"] / state["rows"], 4) if state["rows"] else None,
            "longest_stale_streak": state["longest_stale_streak"],
            "bias_x_m": _summary(ex),
            "bias_y_m": _summary(ey),
        }
    return results


def _summary(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    return {"mean": round(mean(values), 4), "median": round(median(values), 4), "max": round(max(values), 4)}


def score_gt(gt_path: Path, spawns: dict[str, tuple[float, float]]) -> dict[str, float]:
    """Max true-pose deviation from each robot's authored spawn, from GT.

    Args:
        gt_path: Path to `ground_truth.jsonl`.
        spawns: robot_id -> authored (x, y), from `load_spawns`.

    Returns:
        Mapping of robot_id to its max GT deviation from spawn, in meters.
    """
    max_dev: dict[str, float] = dict.fromkeys(spawns, 0.0)
    for line in gt_path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        for rid, robot in record.get("robots", {}).items():
            if rid not in spawns:
                continue
            sx, sy = spawns[rid]
            dev = max(abs(robot["x"] - sx), abs(robot["y"] - sy))
            max_dev[rid] = max(max_dev[rid], dev)
    return {rid: round(dev, 4) for rid, dev in max_dev.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dirs", nargs="+", type=Path)
    args = parser.parse_args()

    for run_dir in args.run_dirs:
        scenario_yaml = run_dir / "scenario.yaml"
        scene_log = run_dir / "m5_scene.jsonl"
        gt_path = run_dir / "gt" / "ground_truth.jsonl"
        if not scenario_yaml.exists() or not scene_log.exists():
            print(f"SKIP {run_dir}: missing scenario.yaml or m5_scene.jsonl", file=sys.stderr)
            continue

        spawns = load_spawns(scenario_yaml)
        scene_scores = score_scene_log(scene_log, spawns)
        gt_scores = score_gt(gt_path, spawns) if gt_path.exists() else {}

        print(f"=== {run_dir.name} ===")
        for rid in sorted(spawns, key=lambda r: int(r.split("_")[1])):
            s = scene_scores[rid]
            gt_dev = gt_scores.get(rid)
            print(
                f"  {rid} spawn={s['spawn']} rows={s['rows']} fresh={s['fresh']} "
                f"fresh_rate={s['fresh_rate']} longest_stale_streak={s['longest_stale_streak']} "
                f"bias_x_m={s['bias_x_m']} bias_y_m={s['bias_y_m']} gt_settle_bias_m={gt_dev}"
            )


if __name__ == "__main__":
    main()

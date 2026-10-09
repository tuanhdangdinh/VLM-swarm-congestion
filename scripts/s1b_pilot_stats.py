"""Score the S1b pilot short runs: M1 coverage and solo free-flow legs.

Implements rules 2 and 3 of the S1b first-light VM NOTES (pre-registered
2026-10-09, reused unchanged by the 2026-10-10 pilot wave):

* ``m1cov``: per (marker, node), the fresh fraction = M1 scene rows where the
  robot is present and not STALE / all M1 scene rows, over sim t >= first
  scene row + 10 s; PASS >= 0.95 with a median position error <= 0.02 m
  against GT (GT offset fitted per run, the S1 rule). The node of each robot
  is its parked goal (``initial_tasks.txt``).
* ``ff``: per solo leg, departure = first GT displacement > 0.03 m from the
  spawn; arrival = first GT time within 0.35 m of the goal that stays within
  for 0.5 sim-s; leg time = arrival - departure (sim-s). Also the M5 accepted
  arrivals and the moving robot's STALE/absent share of M1 rows between
  departure and arrival (flag > 0.05).

Usage:
    python scripts/s1b_pilot_stats.py m1cov <bundle_dir> [...]
    python scripts/s1b_pilot_stats.py ff <bundle_dir> [...]

Prints one JSON object per bundle.
"""

from __future__ import annotations

import bisect
import json
import math
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s1_live_conflict_stats as slcs  # noqa: E402

NODES = {
    "Wp": (-2.30, 1.35),
    "Wm": (-2.30, -1.35),
    "N": (-0.25, 1.35),
    "S": (-0.25, -1.35),
    "E": (2.30, 0.00),
}
FRESH_PASS = 0.95
ERR_PASS_M = 0.02
WARMUP_S = 10.0
DEPART_M = 0.03
ARRIVE_M = 0.35
STAY_S = 0.5
STALE_FLAG = 0.05


def _node_of(x: float, y: float) -> str:
    return min(NODES, key=lambda n: math.hypot(NODES[n][0] - x, NODES[n][1] - y))


def _goals(bundle: Path) -> dict[str, tuple[float, float]]:
    goals = {}
    for line in (bundle / "initial_tasks.txt").read_text().splitlines():
        m = re.search(r"(robot_\d+): \{.*goal: \[([-0-9.]+), ([-0-9.]+)\]", line)
        if m:
            goals[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return goals


def _gt_at(gt: list[dict], gt_t: list[float], t: float) -> dict:
    i = bisect.bisect_left(gt_t, t)
    return gt[min(max(i, 0), len(gt) - 1)]


def m1cov(bundle: Path) -> dict:
    """Fresh fraction and position error per (marker, node) for one parked run."""
    gt = slcs._jl(bundle / "gt" / "ground_truth.jsonl")
    scene = [r for r in slcs._jl(bundle / "m5_scene.jsonl") if r["scene"].get("stamp") is not None]
    gt_t = [r["sim_time_sec"] for r in gt]
    off = slcs._gt_offset(gt, scene)
    goals = _goals(bundle)
    t0 = scene[0]["scene"]["stamp"] + WARMUP_S
    rows = [r["scene"] for r in scene if r["scene"]["stamp"] >= t0]
    out = {}
    for rid, (gx, gy) in sorted(goals.items()):
        fresh = 0
        stale_times = []
        errs = []
        for s in rows:
            v = next((r for r in s["robots"] if r["robot_id"] == rid), None)
            if v is None or v["status"] == "STALE":
                stale_times.append(round(s["stamp"], 2))
                continue
            fresh += 1
            g = _gt_at(gt, gt_t, s["stamp"] - off)["robots"][rid]
            errs.append(math.hypot(v["x"] - g["x"], v["y"] - g["y"]))
        frac = fresh / len(rows) if rows else 0.0
        err = statistics.median(errs) if errs else None
        out[rid] = {
            "marker": int(rid.split("_")[1]),
            "node": _node_of(gx, gy),
            "rows": len(rows),
            "fresh_fraction": round(frac, 4),
            "median_err_m": None if err is None else round(err, 4),
            "pass": frac >= FRESH_PASS and err is not None and err <= ERR_PASS_M,
            "stale_times": stale_times[:20],
        }
    return {"bundle": bundle.name, "gt_offset_s": off, "t0": t0, "robots": out}


def ff(bundle: Path) -> dict:
    """Departure, arrival and leg time of the one moving robot of a solo leg."""
    gt = slcs._jl(bundle / "gt" / "ground_truth.jsonl")
    scene = [r for r in slcs._jl(bundle / "m5_scene.jsonl") if r["scene"].get("stamp") is not None]
    goals = _goals(bundle)
    (rid, (gx, gy)), = goals.items()
    off = slcs._gt_offset(gt, scene) if scene else 0.0
    x0, y0 = gt[0]["robots"][rid]["x"], gt[0]["robots"][rid]["y"]
    depart = next(
        (
            r["sim_time_sec"]
            for r in gt
            if math.hypot(r["robots"][rid]["x"] - x0, r["robots"][rid]["y"] - y0) > DEPART_M
        ),
        None,
    )
    arrive = None
    for i, r in enumerate(gt):
        if depart is None or r["sim_time_sec"] < depart:
            continue
        p = r["robots"][rid]
        if math.hypot(p["x"] - gx, p["y"] - gy) > ARRIVE_M:
            continue
        window = [
            q for q in gt[i:] if q["sim_time_sec"] <= r["sim_time_sec"] + STAY_S
        ]
        if window[-1]["sim_time_sec"] < r["sim_time_sec"] + STAY_S - 0.15:
            break
        if all(
            math.hypot(q["robots"][rid]["x"] - gx, q["robots"][rid]["y"] - gy) <= ARRIVE_M
            for q in window
        ):
            arrive = r["sim_time_sec"]
            break
    stale_share = None
    if depart is not None and arrive is not None and scene:
        rows = [
            s["scene"]
            for s in scene
            if depart <= s["scene"]["stamp"] - off <= arrive
        ]
        bad = sum(
            1
            for s in rows
            if not any(r["robot_id"] == rid and r["status"] != "STALE" for r in s["robots"])
        )
        stale_share = round(bad / len(rows), 4) if rows else None
    m5 = (bundle / "m5.log").read_text() if (bundle / "m5.log").exists() else ""
    accepted = len(re.findall(r"arrived at base goal|arrival accepted late", m5))
    return {
        "bundle": bundle.name,
        "robot": rid,
        "leg": f"{_node_of(x0, y0)}->{_node_of(gx, gy)}",
        "departure_s": depart,
        "arrival_s": arrive,
        "leg_time_s": None if depart is None or arrive is None else round(arrive - depart, 2),
        "m5_accepted_arrivals": accepted,
        "stale_share": stale_share,
        "stale_flag": stale_share is not None and stale_share > STALE_FLAG,
        "gt_offset_s": off,
    }


def main() -> None:
    """Entry point."""
    mode, *bundles = sys.argv[1:]
    fn = {"m1cov": m1cov, "ff": ff}[mode]
    for b in bundles:
        print(json.dumps(fn(Path(b))))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fit M1's upstream latency in the ROS domain from a costmap-probe bag export.

M1 publishes a robot's pose with the camera frame's stamp `s`, but the pose it
measured is the robot's pose at an earlier ROS time `s - d`: the render /
transport / stamping pipeline upstream of M1. The camera localizer's A-prime
lookup (`camera_localizer.odom_lookup_time`) pairs the scene with odometry at
`s - d`, so `d` is the knob `m1_latency_compensation_sec`.

Truth here is ROS-domain only: Isaac's odometry is drift-free and spawn-
relative, so the true base pose at ROS time t is `spawn . odom(t)`
(`docs/reports/2026-10-05-costmap-source-probe.md`: odom matches the re-timed
ground truth to 0.2 mm). No `ground_truth.jsonl` time is used, so the GT
clock offset (0.300 s) cannot leak in.

Two independent estimators, per run, by grid search over d (5 ms steps):

- `translation`: rows where the robot moves >= 0.08 m/s and turns <= 0.2
  rad/s; minimises the mean position residual after removing M1's constant
  position bias (the median residual at rest).
- `rotation`: rows turning >= 0.1 rad/s; minimises the mean absolute heading
  residual.

Usage:
    python3 scripts/m1_latency_fit.py RUN_DIR [RUN_DIR ...] [--json OUT]
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import statistics
from pathlib import Path

SPAWN = (-2.4, 0.0, 0.0)
GRID = [round(-0.10 + 0.005 * k, 3) for k in range(121)]  # -0.10 .. 0.50 s


def _wrap(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


class OdomTruth:
    """Spawn-composed odometry, linearly interpolated on ROS stamps."""

    def __init__(self, rows: list[dict]) -> None:
        rows = sorted(rows, key=lambda r: r["stamp"])
        self.t = [r["stamp"] for r in rows]
        self.rows = rows

    def at(self, t: float) -> tuple[float, float, float] | None:
        """True base pose in map at ROS time `t`, or None outside the series."""
        i = bisect.bisect_right(self.t, t)
        if i == 0 or i >= len(self.t):
            return None
        a, b = self.rows[i - 1], self.rows[i]
        f = (t - a["stamp"]) / (b["stamp"] - a["stamp"]) if b["stamp"] > a["stamp"] else 0.0
        x = a["x"] + f * (b["x"] - a["x"])
        y = a["y"] + f * (b["y"] - a["y"])
        yaw = a["yaw"] + f * _wrap(b["yaw"] - a["yaw"])
        sx, sy, syaw = SPAWN
        c, s = math.cos(syaw), math.sin(syaw)
        return sx + c * x - s * y, sy + s * x + c * y, _wrap(syaw + yaw)

    def rates(self, t: float, h: float = 0.05) -> tuple[float, float] | None:
        """(speed m/s, yaw rate rad/s) at `t` by central difference."""
        a, b = self.at(t - h), self.at(t + h)
        if a is None or b is None:
            return None
        return math.hypot(b[0] - a[0], b[1] - a[1]) / (2 * h), _wrap(b[2] - a[2]) / (2 * h)


def fit_run(run_dir: Path) -> dict:
    """Fit d for one run's export by both estimators."""
    rows = [json.loads(line) for line in (run_dir / "export.jsonl").open()]
    truth = OdomTruth([r for r in rows if r["kind"] == "odom_tf"])
    scenes = [r for r in rows if r["kind"] == "scene" and r.get("stamp") is not None
              and r.get("status") != "STALE"]
    # Fresh detections only: a carried-forward row (marker lost, robot stamp
    # frozen while the scene stamp advances) is not a latency sample. Exports
    # written before `robot_stamp` existed cannot be filtered (flagged below).
    has_robot_stamp = any("robot_stamp" in r for r in scenes)
    if has_robot_stamp:
        scenes = [r for r in scenes if r.get("robot_stamp") is not None
                  and abs(r["robot_stamp"] - r["stamp"]) < 1e-6]
    rest, trans, rot = [], [], []
    for r in scenes:
        rates = truth.rates(r["stamp"])
        if rates is None:
            continue
        v, w = rates
        if v < 0.01 and abs(w) < 0.01:
            p = truth.at(r["stamp"])
            rest.append((r["x"] - p[0], r["y"] - p[1]))
        elif v >= 0.08 and abs(w) <= 0.2:
            trans.append(r)
        elif abs(w) >= 0.1:
            rot.append(r)
    bx = statistics.median(e[0] for e in rest) if rest else 0.0
    by = statistics.median(e[1] for e in rest) if rest else 0.0

    def pos_cost(d: float) -> float:
        errs = []
        for r in trans:
            p = truth.at(r["stamp"] - d)
            if p is not None:
                errs.append(math.hypot(r["x"] - bx - p[0], r["y"] - by - p[1]))
        return statistics.fmean(errs) if errs else float("inf")

    def yaw_cost(d: float) -> float:
        errs = []
        for r in rot:
            p = truth.at(r["stamp"] - d)
            if p is not None:
                errs.append(abs(_wrap(r["theta"] - p[2])))
        return statistics.fmean(errs) if errs else float("inf")

    out: dict = {"run": run_dir.name, "fresh_only": has_robot_stamp,
                 "bias_xy_m": [round(bx, 4), round(by, 4)],
                 "n_rest": len(rest), "n_translation": len(trans), "n_rotation": len(rot)}
    for name, cost, n in (("translation", pos_cost, len(trans)), ("rotation", yaw_cost, len(rot))):
        if n < 10:
            out[name] = None
            continue
        costs = [(cost(d), d) for d in GRID]
        best, d_best = min(costs)
        at0 = cost(0.0)
        out[name] = {"d_sec": d_best, "residual_at_d": round(best, 5),
                     "residual_at_0": round(at0, 5)}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    results = [fit_run(run) for run in args.runs]
    for r in results:
        print(json.dumps(r))
    ds = [r[k]["d_sec"] for r in results for k in ("translation", "rotation") if r.get(k)]
    if ds:
        print(json.dumps({"all_estimates_sec": ds, "median_sec": statistics.median(ds)}))
    if args.json:
        args.json.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

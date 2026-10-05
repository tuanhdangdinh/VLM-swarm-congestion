#!/usr/bin/env python3
"""Forward model of the loop-map global costmap's obstacle marks (offline).

Answers "which marks in the second-aisle crop are legitimate lidar returns,
and which are mis-registered ones?" for a recorded run bundle
(docs/reports/2026-10-05-costmap-source-probe.md). It replays the run's
ground-truth robot pose at the lidar's 10 Hz, ray-casts a 1-degree, single-
plane scan against the loop map's physical geometry at the 0.182 m scan plane
(every rack remnant, including the 0.3 m connector remnants, is solid there),
then registers each hit with a *believed* pose and marks the hit cell, exactly
as the global costmap's ObstacleLayer would with `clearing: false` (the Jazzy
default this project never overrides): marks accumulate until a
ClearEntireCostmap request, never raytraced away.

Believed-pose models (`--model`):

- `gt`   : believed = ground truth. Whatever this marks is geometry-only
           (legitimate returns, incl. resolution bleed into static-free cells).
- `lag`  : the camera localizer's pairing. map->odom is computed from an M1
           pose `L` seconds old and the latest odom, and the costmap reads it
           `D` seconds later (map->odom is future-stamped by
           transform_tolerance 0.3 s): believed(t) = GT(tau) + (GT(t_c)^-1 +
           GT(t)) with t_c = t - D, tau = t_c - L (SE(2) composition), i.e. the
           localizer's yaw error theta(tau) - theta(t_c) rotates every hit about
           the robot.

Marks are compared cell-for-cell against the observed `costmap_crop` rows in
the bundle's probe output (lethal = 100), with the static layer taken from
the first full-grid crop, inflation re-applied (cost >= 99 within the
inscribed radius), and the waypoint probe's closed-column metric.

Usage:
    costmap_source_analysis.py BUNDLE --start 8.0 --end 37.8 \
        [--model lag --lag 0.45 --delay 0.3] [--probe probe.jsonl]
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
from pathlib import Path

import numpy as np

RES = 0.05
ORIGIN = (-6.0, -4.0)
LIDAR_OFFSET_X = -0.032  # base_link -> base_scan, turtlebot3_burger URDF
SCAN_HZ = 10.0
RANGE_MIN, RANGE_MAX = 0.12, 3.5
INSCRIBED = 0.08  # Nav2-computed inscribed radius incl. 0.01 footprint padding
AISLE_Y = (0.925, 1.475)
AISLE_X = (0.65, 1.5)

HALF_W, HALF_D, AISLE_HALF = 6.0, 4.0, 0.6
WALL_T = 0.1
RACK_X = (AISLE_HALF, HALF_W)  # rack blocks fill |x| in [0.6, 6], |y| in [0.6, 4]
RACK_Y = (AISLE_HALF, HALF_D)


def loop_map_rects(
    aisle_cy: float = 1.2,
    aisle_w: float = 0.55,
    aisle_x: tuple[float, float] = (0.6, 2.2),
    conn_cx: float = 1.8,
    conn_w: float = 0.55,
) -> list[tuple[float, float, float, float]]:
    """Return the loop map's solid rectangles at the lidar plane.

    Mirrors `isaac/vgu_sim/scenario_builder._author_loop_connectors`: NE is
    replaced by four remainders; NW, SE, SW and the perimeter walls are the
    shared warehouse's. Heights are irrelevant here because every remainder
    (0.9 m slabs, 0.3 m connector remnants) is taller than the 0.182 m plane.

    Args:
        aisle_cy: Second-aisle centre y.
        aisle_w: Second-aisle width.
        aisle_x: Second-aisle x extent.
        conn_cx: Connector centre x.
        conn_w: Connector width.

    Returns:
        Rectangles as `(x_min, x_max, y_min, y_max)` in world metres.
    """
    ay0, ay1 = aisle_cy - aisle_w / 2, aisle_cy + aisle_w / 2
    cx0, cx1 = conn_cx - conn_w / 2, conn_cx + conn_w / 2
    rects = [
        (-HALF_W, HALF_W, HALF_D - WALL_T, HALF_D),
        (-HALF_W, HALF_W, -HALF_D, -HALF_D + WALL_T),
        (-HALF_W, -HALF_W + WALL_T, -HALF_D, HALF_D),
        (HALF_W - WALL_T, HALF_W, -HALF_D, HALF_D),
        (-HALF_W, -AISLE_HALF, AISLE_HALF, HALF_D),  # NW
        (-HALF_W, -AISLE_HALF, -HALF_D, -AISLE_HALF),  # SW
        (AISLE_HALF, HALF_W, -HALF_D, -AISLE_HALF),  # SE
        (AISLE_HALF, HALF_W, ay1, HALF_D),  # NE top_slab
        (aisle_x[1], HALF_W, ay0, ay1),  # NE aisle_east_of_loop
        (AISLE_HALF, cx0, AISLE_HALF, ay0),  # connector_west_remnant (0.3 m)
        (cx1, HALF_W, AISLE_HALF, ay0),  # connector_east_remnant (0.3 m)
    ]
    return rects


def raycast(ox: float, oy: float, ang: np.ndarray, rects) -> np.ndarray:
    """Return the first-hit range along each bearing (inf when none).

    Args:
        ox: Ray origin x (world).
        oy: Ray origin y (world).
        ang: Bearings in radians (world frame).
        rects: Solid rectangles `(x_min, x_max, y_min, y_max)`.

    Returns:
        Ranges, same shape as `ang`.
    """
    dx, dy = np.cos(ang), np.sin(ang)
    best = np.full(ang.shape, np.inf)
    with np.errstate(divide="ignore", invalid="ignore"):
        for x0, x1, y0, y1 in rects:
            tx0, tx1 = (x0 - ox) / dx, (x1 - ox) / dx
            ty0, ty1 = (y0 - oy) / dy, (y1 - oy) / dy
            tmin = np.maximum(np.minimum(tx0, tx1), np.minimum(ty0, ty1))
            tmax = np.minimum(np.maximum(tx0, tx1), np.maximum(ty0, ty1))
            # Axis-parallel rays: inside the slab -> (-inf, inf), outside -> nan.
            hit = (tmax >= tmin) & (tmax > 0) & np.isfinite(tmin)
            t = np.where(tmin > 0, tmin, np.inf)
            best = np.where(hit & (t < best), t, best)
    return best


class GroundTruth:
    """Ground-truth robot_1 pose, interpolated on sim time."""

    def __init__(self, path: Path, robot: str = "robot_1") -> None:
        self.t, self.p = [], []
        for line in path.open():
            row = json.loads(line)
            r = row["robots"][robot]
            self.t.append(row["sim_time_sec"])
            self.p.append((r["x"], r["y"], r["theta"]))
        self.unwrapped = np.unwrap(np.array([p[2] for p in self.p]))

    def pose(self, t: float) -> tuple[float, float, float]:
        """Return `(x, y, theta)` at sim time `t` (linear interpolation)."""
        i = bisect.bisect_left(self.t, t)
        if i <= 0:
            return self.p[0]
        if i >= len(self.t):
            return self.p[-1]
        t0, t1 = self.t[i - 1], self.t[i]
        a = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
        x = self.p[i - 1][0] + a * (self.p[i][0] - self.p[i - 1][0])
        y = self.p[i - 1][1] + a * (self.p[i][1] - self.p[i - 1][1])
        th = self.unwrapped[i - 1] + a * (self.unwrapped[i] - self.unwrapped[i - 1])
        return x, y, th


def compose(a, b):
    """SE(2) a (+) b."""
    c, s = math.cos(a[2]), math.sin(a[2])
    return a[0] + c * b[0] - s * b[1], a[1] + s * b[0] + c * b[1], a[2] + b[2]


def inverse(a):
    """SE(2) inverse."""
    c, s = math.cos(a[2]), math.sin(a[2])
    return -c * a[0] - s * a[1], s * a[0] - c * a[1], -a[2]


def believed_pose(gt: GroundTruth, t: float, model: str, lag: float, delay: float):
    """Pose the costmap uses to register a scan taken at `t`."""
    if model == "gt" or (lag == 0.0):
        return gt.pose(t)
    t_c = t - delay
    tau = t_c - lag
    return compose(gt.pose(tau), compose(inverse(gt.pose(t_c)), gt.pose(t)))


def cell_of(x: float, y: float) -> tuple[int, int]:
    """Global-costmap (col, row) of a world point."""
    return int(math.floor((x - ORIGIN[0]) / RES)), int(math.floor((y - ORIGIN[1]) / RES))


def simulate_marks(gt, t0, t1, model, lag, delay, rects, phase_deg=0.0):
    """Yield `(t, set_of_new_cells)` per scan between t0 and t1."""
    beams = np.deg2rad(np.arange(360) + phase_deg)
    t = t0
    while t <= t1 + 1e-9:
        x, y, th = gt.pose(t)
        lx, ly = x + LIDAR_OFFSET_X * math.cos(th), y + LIDAR_OFFSET_X * math.sin(th)
        rng = raycast(lx, ly, th + beams, rects)
        ok = (rng >= RANGE_MIN) & (rng < RANGE_MAX)
        bx, by, bth = believed_pose(gt, t, model, lag, delay)
        blx = bx + LIDAR_OFFSET_X * math.cos(bth)
        bly = by + LIDAR_OFFSET_X * math.sin(bth)
        ang = bth + beams[ok]
        px = blx + rng[ok] * np.cos(ang)
        py = bly + rng[ok] * np.sin(ang)
        cells = {cell_of(a, b) for a, b in zip(px, py)}
        yield t, cells
        t += 1.0 / SCAN_HZ


class Crop:
    """The probe's second-aisle crop geometry and observed rows."""

    def __init__(self, probe_path: Path) -> None:
        rows = [json.loads(line) for line in probe_path.open()]
        self.rows = [r for r in rows if r["kind"] == "costmap_crop"]
        if not self.rows:
            raise ValueError(f"no costmap_crop rows in {probe_path}")
        base = self.rows[0]
        self.x0, self.y0 = base["x0"], base["y0"]
        self.nr, self.nc = len(base["crop"]), len(base["crop"][0])
        self.c0, self.r0 = cell_of(self.x0, self.y0)
        self.static = np.array(base["crop"])
        self.static_lethal = self.static == 100

    def lethal_from(self, cells) -> np.ndarray:
        """Boolean crop mask of marked cells."""
        m = np.zeros((self.nr, self.nc), dtype=bool)
        for c, r in cells:
            i, j = r - self.r0, c - self.c0
            if 0 <= i < self.nr and 0 <= j < self.nc:
                m[i, j] = True
        return m

    def inscribed(self, lethal: np.ndarray) -> np.ndarray:
        """Cells with cost >= 99: static >= 99, or within INSCRIBED of a mark."""
        out = self.static >= 99
        k = int(math.ceil(INSCRIBED / RES))
        ii, jj = np.nonzero(lethal)
        for i, j in zip(ii, jj):
            for di in range(-k, k + 1):
                for dj in range(-k, k + 1):
                    if math.hypot(di, dj) * RES <= INSCRIBED + 1e-9:
                        a, b = i + di, j + dj
                        if 0 <= a < self.nr and 0 <= b < self.nc:
                            out[a, b] = True
        return out

    def closed_cols(self, ge99: np.ndarray) -> int:
        """The waypoint probe's metric: aisle columns with no cell below 99."""
        rows = [i for i in range(self.nr) if AISLE_Y[0] <= self.y0 + i * RES <= AISLE_Y[1]]
        cols = [j for j in range(self.nc) if AISLE_X[0] <= self.x0 + j * RES <= AISLE_X[1]]
        return sum(1 for j in cols if all(ge99[i, j] for i in rows))


def render(static_lethal, observed, predicted, crop: Crop) -> str:
    """Overlay: S static, B both, O observed only, P predicted only."""
    out = []
    for i in reversed(range(crop.nr)):
        line = []
        for j in range(crop.nc):
            if static_lethal[i, j]:
                line.append("S")
            elif observed[i, j] and predicted[i, j]:
                line.append("B")
            elif observed[i, j]:
                line.append("O")
            elif predicted[i, j]:
                line.append("P")
            else:
                line.append(".")
        out.append(f"{crop.y0 + i * RES:5.3f} " + "".join(line))
    out.append("      " + "".join(str(int(round((crop.x0 + j * RES) * 10)) % 10)
                              for j in range(crop.nc)))
    return "\n".join(out)


def compare(bundle: Path, probe: Path, t0: float, t1: float, model: str, lag: float,
            delay: float, phases: list[float], show: list[float]) -> dict:
    """Run one model over [t0, t1] and score it against every crop row."""
    gt = GroundTruth(bundle / "gt" / "ground_truth.jsonl")
    crop = Crop(probe)
    rects = loop_map_rects()
    scans = []
    for ph in phases:
        scans.extend(simulate_marks(gt, t0, t1, model, lag, delay, rects, ph))
    scans.sort(key=lambda s: s[0])
    acc: set = set()
    k = 0
    table = []
    for row in crop.rows:
        if row["sim"] < t0 or row["sim"] > t1 + 1.0:
            continue
        while k < len(scans) and scans[k][0] <= row["sim"]:
            acc |= scans[k][1]
            k += 1
        obs = (np.array(row["crop"]) == 100) & ~crop.static_lethal
        pred = crop.lethal_from(acc) & ~crop.static_lethal
        tp = int((obs & pred).sum())
        ge99 = crop.inscribed(pred | crop.static_lethal)
        table.append({
            "sim": row["sim"], "obs_new": int(obs.sum()), "pred_new": int(pred.sum()),
            "tp": tp, "recall": round(tp / obs.sum(), 3) if obs.sum() else None,
            "precision": round(tp / pred.sum(), 3) if pred.sum() else None,
            "obs_closed": row["aisle_closed_cols"], "pred_closed": crop.closed_cols(ge99),
        })
        if any(abs(row["sim"] - s) < 0.05 for s in show):
            print(f"--- sim {row['sim']} model={model} lag={lag} delay={delay}")
            print(render(crop.static_lethal, obs, pred, crop))
    return {"model": model, "lag": lag, "delay": delay, "rows": table}


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--probe", type=Path, default=None)
    ap.add_argument("--start", type=float, default=8.0)
    ap.add_argument("--end", type=float, default=37.8)
    ap.add_argument("--model", choices=["gt", "lag"], default="lag")
    ap.add_argument("--lag", type=float, default=0.45)
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--phases", default="0", help="comma-separated beam phase offsets (deg)")
    ap.add_argument("--show", default="", help="comma-separated crop sim times to render")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()
    probe = args.probe or args.bundle / "probe.jsonl"
    phases = [float(p) for p in args.phases.split(",")]
    show = [float(s) for s in args.show.split(",") if s]
    res = compare(args.bundle, probe, args.start, args.end, args.model, args.lag,
                  args.delay, phases, show)
    print(f"model={res['model']} lag={res['lag']} delay={res['delay']}")
    print(" sim    obs_new pred_new  tp  recall prec  closed(obs/pred)")
    for r in res["rows"]:
        print(f"{r['sim']:7.2f} {r['obs_new']:7d} {r['pred_new']:8d} {r['tp']:4d}  "
              f"{r['recall']!s:6} {r['precision']!s:5}  {r['obs_closed']:2d}/{r['pred_closed']:2d}")
    if args.json:
        args.json.write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

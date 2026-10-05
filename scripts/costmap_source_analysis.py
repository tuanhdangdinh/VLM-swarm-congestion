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

Replay mode (`--replay RUN_DIR`, a scripts/vm/costmap_probe.sh run with
`export.jsonl`, `phases.jsonl`, `gt/` and `scenario.yaml`): re-projects every
RECORDED scan per probe phase three ways -- through the recorded TF exactly as
the costmap does (`tf`), at the ground-truth pose (`gt`: real returns incl.
range noise), and as an exact ray-cast at the ground-truth pose (`ideal`) --
and scores each against the recorded grid's new lethal cells.

Usage:
    costmap_source_analysis.py BUNDLE --start 8.0 --end 37.8 \
        [--model lag --lag 0.45 --delay 0.3] [--probe probe.jsonl]
    costmap_source_analysis.py RUN_DIR --replay [--json out.json]
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
        cells = {cell_of(a, b) for a, b in zip(px, py, strict=True)}
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
        for i, j in zip(ii, jj, strict=True):
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


def _interp_series(series: list[dict], t: float) -> tuple[float, float, float] | None:
    """Linear (x, y, yaw) interpolation of stamp-sorted TF rows; None if outside."""
    stamps = [r["stamp"] for r in series]
    i = bisect.bisect_left(stamps, t)
    if i <= 0 or i >= len(series):
        return None
    a, b = series[i - 1], series[i]
    w = (t - a["stamp"]) / (b["stamp"] - a["stamp"]) if b["stamp"] > a["stamp"] else 0.0
    dyaw = (b["yaw"] - a["yaw"] + math.pi) % (2 * math.pi) - math.pi
    return a["x"] + w * (b["x"] - a["x"]), a["y"] + w * (b["y"] - a["y"]), a["yaw"] + w * dyaw


def static_lethal_indices(meta: dict, scenario_yaml: Path) -> set[int]:
    """Flat global-costmap indices the static layer marks lethal.

    Rebuilds the scenario's Nav2 map with the same generator the VM uses
    (`isaac/scripts/generate_warehouse_map.py`); map_server row 0 is the
    north edge, the costmap's row 0 the south edge.
    """
    import sys

    repo = Path(__file__).resolve().parents[1]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from isaac.scripts.generate_warehouse_map import (
        OCCUPIED,
        build_occupancy_grid,
        load_scenario,
    )
    from isaac.vgu_sim.config import WarehouseConfig

    scenario = load_scenario(scenario_yaml)
    grid, _ = build_occupancy_grid(
        # The VM map is generated at exactly 0.05 m; the costmap reports it as
        # float32 (0.0500000007), which would shift the rasterization by a row.
        WarehouseConfig(), obstacles=[], resolution_m=round(meta["res"], 6),
        aisle_barrier=scenario.aisle_barrier, static_obstacles=scenario.static_obstacles,
        loop_map=scenario.loop_map)
    h, w = grid.shape
    if (h, w) != (meta["h"], meta["w"]):
        raise ValueError(f"map {w}x{h} != costmap {meta['w']}x{meta['h']}")
    rows, cols = np.nonzero(grid == OCCUPIED)
    return {int((h - 1 - r) * w + c) for r, c in zip(rows, cols, strict=True)}


class Replay:
    """Re-project a costmap-probe bag export's scans two ways and score them.

    `tf` registers each scan exactly as the global costmap does (map->odom
    and odom->base_footprint interpolated at the scan stamp, then the fixed
    base_scan mount); `gt` registers it with the ground-truth pose at the
    same stamp. Marks accumulate from each `cleared` phase marker (the
    costmap was cleared there) and are compared with the recorded grid.
    """

    def __init__(self, run_dir: Path) -> None:
        rows = [json.loads(line) for line in (run_dir / "export.jsonl").open()]
        self.meta = next(r for r in rows if r["kind"] == "grid_meta")
        self.scans = sorted((r for r in rows if r["kind"] == "scan"), key=lambda r: r["stamp"])
        self.map_odom = sorted((r for r in rows if r["kind"] == "map_odom"),
                               key=lambda r: r["stamp"])
        self.odom_tf = sorted((r for r in rows if r["kind"] == "odom_tf"), key=lambda r: r["stamp"])
        self.grids = sorted((r for r in rows if r["kind"] == "grid"), key=lambda r: r["rec"])
        self.scene = sorted((r for r in rows if r["kind"] == "scene" and r["stamp"] is not None),
                            key=lambda r: r["stamp"])
        self.markers = [json.loads(line) for line in (run_dir / "phases.jsonl").open()]
        self.gt = GroundTruth(run_dir / "gt" / "ground_truth.jsonl")
        self.rects = loop_map_rects()
        lidar = [r for r in rows if r["kind"] == "tf_static" and r["child"].endswith("base_scan")]
        self.lidar_x = lidar[0]["x"] if lidar else LIDAR_OFFSET_X
        self.static = static_lethal_indices(self.meta, run_dir / "scenario.yaml")

    def cell_index(self, x: float, y: float) -> int | None:
        """Flat global-costmap index of a world point, or None off-grid."""
        m = self.meta
        c = int(math.floor((x - m["ox"]) / m["res"]))
        r = int(math.floor((y - m["oy"]) / m["res"]))
        if 0 <= c < m["w"] and 0 <= r < m["h"]:
            return r * m["w"] + c
        return None

    def project(self, scan: dict, pose) -> set[int]:
        """Cells marked by one scan registered at lidar `pose` (x, y, yaw)."""
        out = set()
        rmax = min(scan["rmax"], RANGE_MAX)
        for i, r in enumerate(scan["ranges"]):
            if r is None or r < scan["rmin"] or r >= rmax:
                continue
            a = pose[2] + scan["amin"] + i * scan["ainc"]
            idx = self.cell_index(pose[0] + r * math.cos(a), pose[1] + r * math.sin(a))
            if idx is not None:
                out.add(idx)
        return out

    def lidar_pose(self, base) -> tuple[float, float, float]:
        """Lidar pose from a base_footprint pose (identity-rotation mount)."""
        return compose(base, (self.lidar_x, 0.0, 0.0))

    def tf_base(self, t: float):
        """Base pose the costmap uses at stamp t, or None when TF cannot serve it."""
        mo, ot = _interp_series(self.map_odom, t), _interp_series(self.odom_tf, t)
        if mo is None or ot is None:
            return None
        return compose(mo, ot)

    def ideal_scan(self, scan: dict, gt_lidar) -> dict:
        """The same scan with every range replaced by the exact ray-cast range."""
        n = len(scan["ranges"])
        ang = gt_lidar[2] + scan["amin"] + np.arange(n) * scan["ainc"]
        ray = raycast(gt_lidar[0], gt_lidar[1], ang, self.rects)
        return dict(scan, ranges=[float(r) if r < scan["rmax"] else None for r in ray])

    def beam_residuals(self, scan: dict, gt_lidar) -> dict:
        """Measured-vs-raycast range residuals from the ground-truth lidar pose."""
        n = len(scan["ranges"])
        ang = gt_lidar[2] + scan["amin"] + np.arange(n) * scan["ainc"]
        ray = raycast(gt_lidar[0], gt_lidar[1], ang, self.rects)
        short = long_ = phantom = 0
        for i, r in enumerate(scan["ranges"]):
            expect = ray[i] if ray[i] < scan["rmax"] else None
            # Isaac's RTX scan encodes "no return" as -1.0 (< range_min), which
            # laser_geometry drops exactly like a max-range reading.
            if r is None or r < scan["rmin"] or r >= scan["rmax"]:
                long_ += expect is not None
                continue
            if expect is None:
                phantom += 1
            elif r < expect - 0.10:
                short += 1
        return {"short": short, "missing": long_, "no_geometry": phantom}

    def run(self, aisle_only_box=(0.4, 2.1, 0.6, 1.5)) -> list[dict]:
        """Score every phase; returns one summary dict per phase."""
        m = self.meta
        x0, x1, y0, y1 = aisle_only_box

        def in_box(idx):
            r, c = divmod(idx, m["w"])
            x, y = m["ox"] + (c + 0.5) * m["res"], m["oy"] + (r + 0.5) * m["res"]
            return x0 <= x <= x1 and y0 <= y <= y1

        starts = [mk for mk in self.markers if mk["event"] == "phase_start"]
        ends = {mk["index"]: mk for mk in self.markers if mk["event"] == "phase_end"}
        clears = [mk["sim"] for mk in self.markers if mk["event"] == "cleared"]
        out = []
        for ph in starts:
            t0 = max(c for c in clears if c <= ph["sim"] + 1e-6)
            t1 = ends[ph["index"]]["sim"] if ph["index"] in ends else self.scans[-1]["stamp"]
            # The last grid published inside this phase (stamps are sim);
            # scans are accumulated up to that grid's stamp, so a grid
            # published after the next clear is never scored.
            grid = None
            for g in self.grids:
                if t0 < g["stamp"] <= t1:
                    grid = g
            t_cut = grid["stamp"] if grid else t1
            tf_marks, gt_marks, ideal_marks = set(), set(), set()
            yaw_err, pos_err, beams = [], [], {"short": 0, "missing": 0, "no_geometry": 0, "n": 0}
            for s in self.scans:
                if not (t0 < s["stamp"] <= t_cut):
                    continue
                base = self.tf_base(s["stamp"])
                gt_base = self.gt.pose(s["stamp"])
                gt_l = self.lidar_pose(gt_base)
                gt_marks |= self.project(s, gt_l)
                ideal_marks |= self.project(self.ideal_scan(s, gt_l), gt_l)
                if base is not None:
                    tf_marks |= self.project(s, self.lidar_pose(base))
                    yaw_err.append((base[2] - gt_base[2] + math.pi) % (2 * math.pi) - math.pi)
                    pos_err.append(math.hypot(base[0] - gt_base[0], base[1] - gt_base[1]))
                res = self.beam_residuals(s, gt_l)
                for k, v in res.items():
                    beams[k] += v
                beams["n"] += 1
            obs = set(grid["new_lethal"]) if grid else set()
            obs_box = {i for i in obs if in_box(i)}
            tf_box = {i for i in tf_marks if in_box(i)}
            gt_box = {i for i in gt_marks if in_box(i)}
            ideal_box = {i for i in ideal_marks if in_box(i)}
            def score(o, p, static=self.static):
                # new_lethal already excludes the static map; so must the prediction.
                p = p - static
                tp = len(o & p)
                return {"obs": len(o), "pred": len(p), "tp": tp,
                        "recall": round(tp / len(o), 3) if o else None,
                        "precision": round(tp / len(p), 3) if p else None}

            ya = np.abs(np.array(yaw_err)) if yaw_err else np.array([np.nan])
            out.append({
                "phase": ph, "t0": t0, "t1": t1, "grid_stamp": grid["stamp"] if grid else None,
                "whole_tf": score(obs, tf_marks), "whole_gt": score(obs, gt_marks),
                "aisle_tf": score(obs_box, tf_box), "aisle_gt": score(obs_box, gt_box),
                "aisle_obs_minus_tf": len(obs_box - tf_box - gt_box),
                "aisle_obs_ideal_geometry": len(obs_box & ideal_box),
                "aisle_obs_range_noise": len((obs_box & gt_box) - ideal_box),
                "aisle_obs_geometry": len(obs_box & gt_box),
                "aisle_obs_registration": len(obs_box & (tf_box - gt_box)),
                "yaw_err_max": round(float(np.nanmax(ya)), 4),
                "yaw_err_rms": round(float(np.sqrt(np.nanmean(ya ** 2))), 4),
                "pos_err_max": round(max(pos_err), 4) if pos_err else None,
                "beams": beams,
                "closed_cols": _closed_cols_from_crop(grid) if grid else None,
                "render": self.render_box(obs_box, gt_box, tf_box),
            })
        return out

    def render_box(self, obs: set[int], gt: set[int], tf: set[int],
                   box=(0.4, 2.1, 0.6, 1.5)) -> str:
        """Crop map: S static, G observed+geometry, R observed+registration-only,
        U observed unexplained, g/r predicted-only (geometry / registration)."""
        m = self.meta
        c0 = int(math.floor((box[0] - m["ox"]) / m["res"]))
        c1 = int(math.floor((box[1] - m["ox"]) / m["res"]))
        r0 = int(math.floor((box[2] - m["oy"]) / m["res"]))
        r1 = int(math.floor((box[3] - m["oy"]) / m["res"]))
        lines = []
        for r in range(r1, r0 - 1, -1):
            row = []
            for c in range(c0, c1 + 1):
                i = r * m["w"] + c
                if i in self.static:
                    row.append("S")
                elif i in obs:
                    row.append("G" if i in gt else ("R" if i in tf else "U"))
                elif i in gt:
                    row.append("g")
                elif i in tf:
                    row.append("r")
                else:
                    row.append(".")
            lines.append(f"{m['oy'] + (r + 0.5) * m['res']:5.3f} " + "".join(row))
        lines.append("      " + "".join(
            str(int(round((m["ox"] + (c + 0.5) * m["res"]) * 10)) % 10) for c in range(c0, c1 + 1)))
        return "\n".join(lines)

    def static_cells(self) -> set[tuple[int, int]]:
        """Static-map lethal cells as `(col, row)`."""
        w = self.meta["w"]
        return {(i % w, i // w) for i in self.static}

    def phase_scans(self, index: int, registration: str = "tf"):
        """Yield `(ox, oy, ranges, angles)` for one phase, as `accumulate` takes."""
        start = next(m for m in self.markers if m["event"] == "phase_start" and m["index"] == index)
        end = next(m for m in self.markers if m["event"] == "phase_end" and m["index"] == index)
        t0, t1 = start["sim"], end["sim"]
        grids = [g for g in self.grids if t0 < g["stamp"] <= t1]
        t_cut = grids[-1]["stamp"] if grids else t1
        for s in self.scans:
            if not (t0 < s["stamp"] <= t_cut):
                continue
            base = self.tf_base(s["stamp"]) if registration == "tf" else self.gt.pose(s["stamp"])
            if base is None:
                continue
            ox, oy, th = self.lidar_pose(base)
            r = np.array([v if v is not None else -1.0 for v in s["ranges"]])
            a = th + s["amin"] + np.arange(len(r)) * s["ainc"]
            ok = (r >= s["rmin"]) & (r < s["rmax"])
            yield ox, oy, r[ok], a[ok]

    def observed_closed(self, index: int) -> int:
        """Closed columns of the last recorded grid of a phase (from its new marks)."""
        start = next(m for m in self.markers if m["event"] == "phase_start" and m["index"] == index)
        end = next(m for m in self.markers if m["event"] == "phase_end" and m["index"] == index)
        grids = [g for g in self.grids if start["sim"] < g["stamp"] <= end["sim"]]
        w = self.meta["w"]
        marks = {(i % w, i // w) for i in grids[-1]["new_lethal"]}
        return closed_cols_from_marks(marks, self.static_cells())

    def timeline(self, t0: float, t1: float, step: float = 0.5) -> list[dict]:
        """Registration error and observed aisle marks, time-aligned on sim time."""
        rows = []
        t = t0
        while t <= t1:
            base, g = self.tf_base(t), self.gt.pose(t)
            grid = None
            for gr in self.grids:
                if gr["stamp"] <= t:
                    grid = gr
            rows.append({
                "t": round(t, 2),
                "yaw_err": None if base is None else round(
                    (base[2] - g[2] + math.pi) % (2 * math.pi) - math.pi, 4),
                "gt_wz": round((self.gt.pose(t + 0.05)[2] - self.gt.pose(t - 0.05)[2]) / 0.1, 3),
                "obs_closed": _closed_cols_from_crop(grid) if grid else None,
                "obs_new_crop": _new_in_crop(grid) if grid else None,
            })
            t += step
        return rows


def _ray_cells(ox: float, oy: float, ex: float, ey: float) -> list[tuple[int, int]]:
    """Cells crossed from (ox, oy) towards (ex, ey), excluding the end cell."""
    n = max(1, int(math.hypot(ex - ox, ey - oy) / (RES / 4)))
    end = cell_of(ex, ey)
    out, last = [], None
    for k in range(n):
        c = cell_of(ox + (ex - ox) * k / n, oy + (ey - oy) * k / n)
        if c != last and c != end:
            out.append(c)
            last = c
    return out


def accumulate(scans, clearing: bool, obstacle_max: float, raytrace_max: float) -> set:
    """Obstacle-layer marks after a scan sequence, with or without raytrace clearing.

    Mirrors nav2_costmap_2d::ObstacleLayer per scan: when `clearing`, free
    every cell a ray crosses up to `raytrace_max` (end cell excluded); then
    mark every return closer than `obstacle_max`.

    Args:
        scans: Iterable of `(ox, oy, ranges, world_angles)`; ranges already
            filtered to valid returns.
        clearing: The observation source's `clearing` flag.
        obstacle_max: `obstacle_max_range`.
        raytrace_max: `raytrace_max_range`.

    Returns:
        Set of `(col, row)` lethal cells.
    """
    marks: set = set()
    for ox, oy, rng, ang in scans:
        ex, ey = ox + rng * np.cos(ang), oy + rng * np.sin(ang)
        if clearing and marks:
            for r, a, x, y in zip(rng, ang, ex, ey, strict=True):
                if r > raytrace_max:
                    x, y = ox + raytrace_max * math.cos(a), oy + raytrace_max * math.sin(a)
                for c in _ray_cells(ox, oy, x, y):
                    marks.discard(c)
        keep = rng < obstacle_max
        marks |= {cell_of(x, y) for x, y in zip(ex[keep], ey[keep], strict=True)}
    return marks


def closed_cols_from_marks(marks: set, static_cells: set) -> int:
    """Closed aisle columns: every aisle cell within the inscribed radius of a lethal cell.

    Inscribed radius 0.08 m covers exactly the 3x3 neighbourhood at 0.05 m.
    """
    lethal = marks | static_cells
    rows = [cell_of(0.0, y)[1] for y in np.arange(AISLE_Y[0], AISLE_Y[1] + 1e-9, RES)]
    cols = [cell_of(x, 0.0)[0] for x in np.arange(AISLE_X[0] + RES / 2, AISLE_X[1], RES)]
    closed = 0
    for c in cols:
        if all(any((c + dc, r + dr) in lethal for dc in (-1, 0, 1) for dr in (-1, 0, 1))
               for r in rows):
            closed += 1
    return closed


def _crop_y0_x0(grid: dict) -> tuple[float, float]:
    return ORIGIN[1] + (grid["crop_r0"] + 0.5) * RES, ORIGIN[0] + (grid["crop_c0"] + 0.5) * RES


def _closed_cols_from_crop(grid: dict) -> int:
    """The waypoint probe's closed-column metric on an exported crop."""
    y0, x0 = _crop_y0_x0(grid)
    crop = grid["crop"]
    rows = [i for i in range(len(crop)) if AISLE_Y[0] <= y0 + i * RES <= AISLE_Y[1]]
    cols = [j for j in range(len(crop[0])) if AISLE_X[0] <= x0 + j * RES <= AISLE_X[1]]
    return sum(1 for j in cols if min(crop[i][j] for i in rows) >= 99)


def _new_in_crop(grid: dict) -> int:
    """New (non-static) lethal cells inside the exported crop."""
    w = int(round(2 * -ORIGIN[0] / RES))
    r0, c0 = grid["crop_r0"], grid["crop_c0"]
    nr, nc = len(grid["crop"]), len(grid["crop"][0])
    return sum(1 for i in grid["new_lethal"]
               if r0 <= i // w < r0 + nr and c0 <= i % w < c0 + nc)


COUNTERFACTUALS = (
    ("as configured: clearing off, 3.5 m", False, 3.5, 3.0),
    ("C: obstacle_max_range 2.5", False, 2.5, 3.0),
    ("C: obstacle_max_range 2.0", False, 2.0, 3.0),
    ("H: clearing on, raytrace 3.0 (default)", True, 3.5, 3.0),
    ("H: clearing on, raytrace 3.5", True, 3.5, 3.5),
    ("H+C: clearing on, 2.5 / 3.0", True, 2.5, 3.0),
)


def main_counterfactual(run_dir: Path) -> int:
    """Closed aisle columns per phase under obstacle-layer parameter variants."""
    rp = Replay(run_dir)
    static = rp.static_cells()
    starts = [m for m in rp.markers if m["event"] == "phase_start"]
    for ph in starts:
        i = ph["index"]
        print(f"phase {i} {ph['kind']} wz={ph.get('wz')}: observed closed {rp.observed_closed(i)}")
        for name, clearing, omax, rmax in COUNTERFACTUALS:
            marks = accumulate(rp.phase_scans(i, "tf"), clearing, omax, rmax)
            print(f"  {name:42s} closed {closed_cols_from_marks(marks, static):2d}")
        marks = accumulate(rp.phase_scans(i, "gt"), False, 3.5, 3.0)
        print(f"  {'A bound: perfect localizer (GT), as configured':42s} closed "
              f"{closed_cols_from_marks(marks, static):2d}")
    return 0


def forward_counterfactual(bundle: Path, t0: float, t1: float, lag: float, delay: float) -> int:
    """Run-2 forward model (lag registration) under the same variants."""
    gt = GroundTruth(bundle / "gt" / "ground_truth.jsonl")
    crop = Crop(bundle / "probe.jsonl")
    static = {(crop.c0 + j, crop.r0 + i) for i, j in zip(*np.nonzero(crop.static_lethal),
                                                        strict=True)}
    rects = loop_map_rects()
    beams = np.deg2rad(np.arange(360.0))

    def scans(t_end):
        t = t0
        while t <= t_end + 1e-9:
            x, y, th = gt.pose(t)
            lx, ly = x + LIDAR_OFFSET_X * math.cos(th), y + LIDAR_OFFSET_X * math.sin(th)
            rng = raycast(lx, ly, th + beams, rects)
            ok = (rng >= RANGE_MIN) & (rng < RANGE_MAX)
            bx, by, bth = believed_pose(gt, t, "lag", lag, delay)
            yield (bx + LIDAR_OFFSET_X * math.cos(bth), by + LIDAR_OFFSET_X * math.sin(bth),
                   rng[ok], bth + beams[ok])
            t += 1.0 / SCAN_HZ

    for t_end in (18.07, 24.43, t1):
        print(f"forward model lag={lag} delay={delay}, sim {t0} -> {t_end}:")
        for name, clearing, omax, rmax in COUNTERFACTUALS:
            marks = accumulate(scans(t_end), clearing, omax, rmax)
            print(f"  {name:42s} closed {closed_cols_from_marks(marks, static):2d}")
    return 0


def main_replay(run_dir: Path, json_out: Path | None) -> int:
    """Print the per-phase replay attribution for one costmap-probe run."""
    rp = Replay(run_dir)
    res = rp.run()
    for r in res:
        ph = r["phase"]
        print(f"phase {ph['index']} {ph['kind']} wz={ph.get('wz')} sec={ph['sec']} "
              f"[{r['t0']:.2f}, {r['t1']:.2f}] grid@{r['grid_stamp']}")
        print(f"  yaw_err max {r['yaw_err_max']} rms {r['yaw_err_rms']}  "
              f"pos_err max {r['pos_err_max']}")
        print(f"  whole grid: TF-replay {r['whole_tf']}  GT-replay {r['whole_gt']}")
        print(f"  aisle crop: TF-replay {r['aisle_tf']}  GT-replay {r['aisle_gt']}")
        print(f"  aisle obs geometry split: ideal ray-cast {r['aisle_obs_ideal_geometry']}, "
              f"range noise only {r['aisle_obs_range_noise']}")
        print(f"  aisle obs = geometry {r['aisle_obs_geometry']} + registration "
              f"{r['aisle_obs_registration']} + unexplained {r['aisle_obs_minus_tf']}; "
              f"closed cols {r['closed_cols']}")
        print(f"  beams {r['beams']}")
        print(r["render"])
    if json_out:
        json_out.write_text(json.dumps(res, indent=1, default=str))
    return 0


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--counterfactual", action="store_true",
                    help="closed columns under obstacle-layer variants (replay or forward)")
    ap.add_argument("--replay", action="store_true",
                    help="BUNDLE is a costmap_probe run dir (export.jsonl + phases.jsonl + gt/)")
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
    if args.replay and args.counterfactual:
        return main_counterfactual(args.bundle)
    if args.replay:
        return main_replay(args.bundle, args.json)
    if args.counterfactual:
        return forward_counterfactual(args.bundle, args.start, args.end, args.lag, args.delay)
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

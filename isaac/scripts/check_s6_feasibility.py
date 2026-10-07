# isaac/scripts/check_s6_feasibility.py
"""CLI: offline feasibility checks for the S6 dual-conflict scene.

Usage:
    python isaac/scripts/check_s6_feasibility.py
    python isaac/scripts/check_s6_feasibility.py --json

Runs on this machine only (no Isaac, no Nav2, no VM). Every check reads the
scenario yaml and the committed Nav2 map that `generate_warehouse_map.py`
wrote for it, so the numbers describe the artifacts a run would load:

- the committed map equals a fresh rasterization of the scenario;
- every pose sits inside M1's verified tracked band, clear of the registered
  marker-1 STALE point and of every rack/barrier camera shadow;
- spawn pairs keep the 0.650 m stationary floor, and each spawn's chassis
  box clears the occupied cells;
- each robot has a free path to its goal on the grid eroded by the robot's
  half-width, alone in the scene;
- sealing a pair's jam cross-section disconnects that pair from its goals
  (no detour round the map, so the head-on cannot dissolve on its own);
- both jam midpoints, measured at the half-arc point of the pair's grid
  path, and the cross-pair member distance at the standoff against Arm B's
  r_conflict_m.

Every number printed is a prediction from geometry, not an observation of a
run. The verdicts are not registered claims.
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import (
    FREE,
    build_occupancy_grid,
    load_scenario,
)
from isaac.vgu_sim.config import (
    CameraConfig,
    DualConflictOracleConfig,
    LoopMapConfig,
    ScenarioConfig,
    WarehouseConfig,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SCENARIO = REPO_ROOT / "isaac/config/scenarios/s6_dual_conflict.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
RESOLUTION_M = 0.05

# M1's verified tracked band and the homography's y edge
# (docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md).
TRACKED_BAND_M = (2.5, 1.80)
HOMOGRAPHY_Y_EDGE_M = 2.092
# Marker 1 is chronically STALE at this pose; -1.65 is verified clean, so a
# 0.10 m keep-out is the narrowest radius the probes support
# (docs/reports/2026-10-01-robot1-stale-rootcause.md).
MARKER_1_STALE_POINT = (-1.75, 0.0)
MARKER_1_STALE_KEEPOUT_M = 0.10
# Verified-clean (marker, pose) pairs, from the v3 scene design's shared
# constraints table; any other pair is unverified until a VM probe.
VERIFIED_CLEAN_POSES: dict[int, tuple[tuple[float, float], ...]] = {
    1: ((-2.4, 0.0), (-1.65, 0.0), (1.75, 0.0), (-1.37, 0.359)),
    2: ((1.75, 0.0), (-1.75, 0.0), (1.85, 0.0), (2.4, 0.0), (1.481, -0.344)),
    3: ((0.0, -1.2), (0.0, -1.8), (0.0, 1.75)),
    4: ((0.0, 1.2), (0.0, 2.0), (0.0, -1.75)),
}
STATIONARY_FLOOR_M = 0.650
# Standoff gap range: the 0.45 m pair latch (safety.yaml min_distance_m) down
# to the ~0.32 m follower latch (unified scene design, queue spacing).
STANDOFF_GAPS_M = (0.45, 0.32)
ARM_B_R_CONFLICT_M = 1.5
TRANSIT_SPEED_MPS = 0.15
STALL_TRIGGER_WALL_SEC = 12.0
RTF_RANGE = (0.21, 0.24)
M5_START_DELAY_WALL_SEC = 16.0

# turtlebot3_burger.urdf: base_link collision box 0.140 m centred 0.032 m
# behind base_link; wheels at y = +-0.08 with 0.018 m width.
CHASSIS_X_RANGE_M = (-0.102, 0.038)
CHASSIS_HALF_WIDTH_M = 0.089
MARKER_HEIGHT_M = 0.21
MARKER_HALF_SIZE_M = 0.06
RACK_HEIGHT_M = 0.9
BARRIER_HEIGHT_M = 0.9


@dataclass(frozen=True)
class Box3D:
    """An axis-aligned occluder: world x/y extent and height from the floor."""

    name: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    height_m: float


@dataclass(frozen=True)
class CheckResult:
    """One feasibility check: a name, a pass/fail verdict and its numbers."""

    name: str
    passed: bool
    detail: dict


def load_committed_grid(scenario: ScenarioConfig) -> np.ndarray:
    """Load the scenario's committed Nav2 map as a grid (row 0 = world +y edge)."""
    path = MAPS_DIR / f"warehouse_map_{scenario.name}.pgm"
    return np.array(Image.open(path))


def fresh_grid(scenario: ScenarioConfig) -> np.ndarray:
    """Rasterize the scenario exactly as `generate_warehouse_map.py` does."""
    grid, _ = build_occupancy_grid(
        WarehouseConfig(),
        obstacles=[],
        resolution_m=RESOLUTION_M,
        aisle_barrier=scenario.aisle_barrier,
        static_obstacles=scenario.static_obstacles,
        loop_map=scenario.loop_map,
    )
    return grid


def cell_center(row: int, col: int, cfg: WarehouseConfig) -> tuple[float, float]:
    """World centre of grid cell `(row, col)`."""
    x = -cfg.width_m / 2 + (col + 0.5) * RESOLUTION_M
    y = cfg.depth_m / 2 - (row + 0.5) * RESOLUTION_M
    return x, y


def point_cell(x: float, y: float, cfg: WarehouseConfig) -> tuple[int, int]:
    """Grid cell containing world point `(x, y)` (floor, not round)."""
    col = math.floor((x + cfg.width_m / 2) / RESOLUTION_M)
    row = math.floor((cfg.depth_m / 2 - y) / RESOLUTION_M)
    return row, col


def eroded_free(grid: np.ndarray, clearance_m: float) -> np.ndarray:
    """Free cells whose centre is more than `clearance_m` from every occupied cell.

    Occupied cells are treated as their full square, so a free cell survives
    only when the nearest occupied square edge is farther than the clearance.
    """
    occupied = grid != FREE
    blocked = occupied.copy()
    reach = int(math.ceil(clearance_m / RESOLUTION_M)) + 1
    h, w = grid.shape
    for dr in range(-reach, reach + 1):
        for dc in range(-reach, reach + 1):
            # Distance from a cell centre to the nearest point of a neighbour
            # square offset by (dr, dc) cells.
            gx = max(abs(dc) - 0.5, 0.0) * RESOLUTION_M
            gy = max(abs(dr) - 0.5, 0.0) * RESOLUTION_M
            if math.hypot(gx, gy) > clearance_m:
                continue
            shifted = np.zeros_like(occupied)
            src_r = slice(max(0, dr), h + min(0, dr))
            dst_r = slice(max(0, -dr), h + min(0, -dr))
            src_c = slice(max(0, dc), w + min(0, dc))
            dst_c = slice(max(0, -dc), w + min(0, -dc))
            shifted[dst_r, dst_c] = occupied[src_r, src_c]
            blocked |= shifted
    return ~blocked


def shortest_path(
    free: np.ndarray, start: tuple[int, int], goal: tuple[int, int]
) -> list[tuple[int, int]] | None:
    """8-connected Dijkstra over `free`; None when the goal is unreachable."""
    if not (free[start] and free[goal]):
        return None
    h, w = free.shape
    steps = [(dr, dc, math.hypot(dr, dc)) for dr in (-1, 0, 1) for dc in (-1, 0, 1)
             if (dr, dc) != (0, 0)]
    dist = {start: 0.0}
    prev: dict[tuple[int, int], tuple[int, int]] = {}
    heap = [(0.0, start)]
    while heap:
        d, node = heapq.heappop(heap)
        if node == goal:
            path = [node]
            while node in prev:
                node = prev[node]
                path.append(node)
            return path[::-1]
        if d > dist.get(node, math.inf):
            continue
        r, c = node
        for dr, dc, cost in steps:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < h and 0 <= nc < w) or not free[nr, nc]:
                continue
            # No corner cutting between two blocked orthogonal neighbours.
            if dr and dc and not (free[r + dr, c] and free[r, c + dc]):
                continue
            nd = d + cost
            if nd < dist.get((nr, nc), math.inf):
                dist[(nr, nc)] = nd
                prev[(nr, nc)] = node
                heapq.heappush(heap, (nd, (nr, nc)))
    return None


def path_world(path: list[tuple[int, int]], cfg: WarehouseConfig) -> list[tuple[float, float]]:
    """World centres of a grid path."""
    return [cell_center(r, c, cfg) for r, c in path]


def path_length_m(points: list[tuple[float, float]]) -> float:
    """Polyline length in metres."""
    return sum(math.dist(a, b) for a, b in zip(points, points[1:], strict=False))


def point_at_arc_fraction(
    points: list[tuple[float, float]], fraction: float
) -> tuple[float, float]:
    """The point a given fraction of the way along a polyline, by arc length."""
    target = fraction * path_length_m(points)
    walked = 0.0
    for a, b in zip(points, points[1:], strict=False):
        seg = math.dist(a, b)
        if walked + seg >= target and seg > 0:
            t = (target - walked) / seg
            return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        walked += seg
    return points[-1]


def free_run_center_y(grid: np.ndarray, x: float, y: float, cfg: WarehouseConfig) -> float:
    """World y of the centre of the vertical free run through `(x, y)`.

    Measured from the run's cell edges in the map column containing `x`: the
    axis of the aisle the point lies in.
    """
    row, col = point_cell(x, y, cfg)
    column = grid[:, col] == FREE
    if not column[row]:
        raise ValueError(f"({x}, {y}) is not on a free cell")
    top = row
    while top > 0 and column[top - 1]:
        top -= 1
    bottom = row
    while bottom < len(column) - 1 and column[bottom + 1]:
        bottom += 1
    y_top = cfg.depth_m / 2 - top * RESOLUTION_M
    y_bottom = cfg.depth_m / 2 - (bottom + 1) * RESOLUTION_M
    return (y_top + y_bottom) / 2.0


def occluders(scenario: ScenarioConfig) -> list[Box3D]:
    """Every box taller than the floor that can shadow a marker for the camera.

    Mirrors `warehouse_builder._build_rack_blocks` (four 0.9 m quadrants),
    `scenario_builder._author_aisle_barrier` (two 0.9 m blocks) and
    `scenario_builder._author_loop_connectors` (NE replaced by four remnants,
    two of them `connector_remnant_height_m` tall).
    """
    cfg = WarehouseConfig()
    half = cfg.nominal_aisle_width_m / 2.0
    x_far = cfg.width_m / 2.0
    y_far = cfg.depth_m / 2.0
    boxes = [
        Box3D("rack_NW", -x_far, -half, half, y_far, RACK_HEIGHT_M),
        Box3D("rack_SW", -x_far, -half, -y_far, -half, RACK_HEIGHT_M),
        Box3D("rack_SE", half, x_far, -y_far, -half, RACK_HEIGHT_M),
    ]
    loop: LoopMapConfig | None = scenario.loop_map
    if loop is None:
        boxes.append(Box3D("rack_NE", half, x_far, half, y_far, RACK_HEIGHT_M))
    else:
        a_lo = loop.second_aisle_center_y_m - loop.second_aisle_width_m / 2.0
        a_hi = loop.second_aisle_center_y_m + loop.second_aisle_width_m / 2.0
        c_lo = loop.connector_center_x_m - loop.connector_width_m / 2.0
        c_hi = loop.connector_center_x_m + loop.connector_width_m / 2.0
        low = loop.connector_remnant_height_m
        boxes += [
            Box3D("ne_top_slab", half, x_far, a_hi, y_far, RACK_HEIGHT_M),
            Box3D("ne_aisle_east_of_loop", loop.second_aisle_x_max_m, x_far, a_lo, a_hi,
                  RACK_HEIGHT_M),
            Box3D("ne_connector_west_remnant", half, c_lo, half, a_lo, low),
            Box3D("ne_connector_east_remnant", c_hi, x_far, half, a_lo, low),
        ]
    barrier = scenario.aisle_barrier
    if barrier is not None and barrier.effective_width_m / 2.0 < half:
        eff = barrier.effective_width_m / 2.0
        x_lo = barrier.center_x_m - barrier.length_m / 2.0
        x_hi = barrier.center_x_m + barrier.length_m / 2.0
        boxes += [
            Box3D("barrier_north", x_lo, x_hi, eff, half, BARRIER_HEIGHT_M),
            Box3D("barrier_south", x_lo, x_hi, -half, -eff, BARRIER_HEIGHT_M),
        ]
    return boxes


def ray_hits_box(
    camera: tuple[float, float, float], point: tuple[float, float, float], box: Box3D
) -> bool:
    """Whether the segment camera -> point passes through `box` (slab test)."""
    lo = (box.x_min, box.y_min, 0.0)
    hi = (box.x_max, box.y_max, box.height_m)
    t_enter, t_exit = 0.0, 1.0
    for axis in range(3):
        d = point[axis] - camera[axis]
        if abs(d) < 1e-12:
            if not (lo[axis] <= camera[axis] <= hi[axis]):
                return False
            continue
        t0 = (lo[axis] - camera[axis]) / d
        t1 = (hi[axis] - camera[axis]) / d
        t_enter = max(t_enter, min(t0, t1))
        t_exit = min(t_exit, max(t0, t1))
        if t_enter > t_exit:
            return False
    # Touching the box only at the marker itself is not an occlusion.
    return t_enter < 1.0 - 1e-9


def marker_occluders(
    scenario: ScenarioConfig, xy: tuple[float, float]
) -> list[str]:
    """Names of every occluder between the camera and the marker's corners/centre."""
    cam = CameraConfig().position_m
    h = MARKER_HALF_SIZE_M
    samples = [(xy[0] + dx, xy[1] + dy, MARKER_HEIGHT_M)
               for dx in (-h, 0.0, h) for dy in (-h, 0.0, h)]
    hits = []
    for box in occluders(scenario):
        if any(ray_hits_box(cam, p, box) for p in samples):
            hits.append(box.name)
    return hits


def chassis_clearance_m(
    grid: np.ndarray, x: float, y: float, yaw_rad: float, cfg: WarehouseConfig
) -> float:
    """Signed gap from the chassis box to the nearest occupied cell (< 0 = overlap).

    Only axis-aligned headings (0 or pi) are supported, the only ones S6 uses.
    """
    facing = round(math.cos(yaw_rad))
    if abs(math.sin(yaw_rad)) > 1e-6 or facing == 0:
        raise ValueError(f"only yaw 0 or pi is supported; got {yaw_rad}")
    back, front = CHASSIS_X_RANGE_M
    xs = sorted((x + facing * back, x + facing * front))
    rx_min, rx_max = xs
    ry_min, ry_max = y - CHASSIS_HALF_WIDTH_M, y + CHASSIS_HALF_WIDTH_M
    rows, cols = np.nonzero(grid != FREE)
    cx_min = -cfg.width_m / 2 + cols * RESOLUTION_M
    cy_max = cfg.depth_m / 2 - rows * RESOLUTION_M
    cx_max, cy_min = cx_min + RESOLUTION_M, cy_max - RESOLUTION_M
    gap_x = np.maximum(cx_min - rx_max, rx_min - cx_max)
    gap_y = np.maximum(cy_min - ry_max, ry_min - cy_max)
    outside = np.where(
        (gap_x > 0) & (gap_y > 0), np.hypot(gap_x, gap_y), np.maximum(gap_x, gap_y)
    )
    return float(outside.min())


def _round(v: float) -> float:
    return round(v, 3)


def run_checks(scenario_path: Path = DEFAULT_SCENARIO) -> list[CheckResult]:
    """Run every S6 feasibility check and return the results in order."""
    scenario = load_scenario(scenario_path)
    oracle = scenario.oracle
    if not isinstance(oracle, DualConflictOracleConfig):
        raise ValueError(f"{scenario_path} carries no dual-conflict oracle")
    cfg = WarehouseConfig()
    robots = {r.robot_id: r for r in scenario.robots}
    results: list[CheckResult] = []

    committed = load_committed_grid(scenario)
    results.append(CheckResult(
        "committed_map_matches_scenario",
        bool(np.array_equal(committed, fresh_grid(scenario))),
        {"map": f"warehouse_map_{scenario.name}.pgm", "shape": list(committed.shape)},
    ))
    grid = committed

    poses = {}
    for r in scenario.robots:
        poses[f"{r.robot_id}.spawn"] = (r.marker_id, (r.spawn.x, r.spawn.y))
        poses[f"{r.robot_id}.goal"] = (r.marker_id, (r.goal.x, r.goal.y))
    # Nominal standoff poses: each pair stops symmetric about its midpoint.
    for conflict in oracle.conflicts:
        a, b = (robots[rid] for rid in conflict.involved_robots)
        mx, my = conflict.jam_midpoint_xy
        ux, uy = b.spawn.x - a.spawn.x, b.spawn.y - a.spawn.y
        norm = math.hypot(ux, uy)
        for g in STANDOFF_GAPS_M:
            off = g / 2.0
            poses[f"{a.robot_id}.standoff_g{g}"] = (
                a.marker_id, (mx - off * ux / norm, my - off * uy / norm))
            poses[f"{b.robot_id}.standoff_g{g}"] = (
                b.marker_id, (mx + off * ux / norm, my + off * uy / norm))

    out_of_band = {k: [_round(v) for v in xy] for k, (_, xy) in poses.items()
                   if abs(xy[0]) > TRACKED_BAND_M[0] + 1e-9
                   or abs(xy[1]) > TRACKED_BAND_M[1] + 1e-9}
    on_edge = sorted(k for k, (_, xy) in poses.items()
                     if abs(abs(xy[0]) - TRACKED_BAND_M[0]) < 1e-9
                     or abs(abs(xy[1]) - TRACKED_BAND_M[1]) < 1e-9)
    results.append(CheckResult(
        "poses_inside_tracked_band",
        not out_of_band,
        {"band": list(TRACKED_BAND_M), "out_of_band": out_of_band, "on_band_edge": on_edge,
         "max_abs_y_vs_homography_edge": [
             _round(max(abs(xy[1]) for _, xy in poses.values()) + MARKER_HALF_SIZE_M),
             HOMOGRAPHY_Y_EDGE_M]},
    ))

    near_stale = {k: _round(math.dist(xy, MARKER_1_STALE_POINT))
                  for k, (m, xy) in poses.items()
                  if m == 1 and math.dist(xy, MARKER_1_STALE_POINT) <= MARKER_1_STALE_KEEPOUT_M}
    verified = {}
    for k, (m, xy) in poses.items():
        verified[k] = any(math.dist(xy, p) < 1e-6 for p in VERIFIED_CLEAN_POSES.get(m, ()))
    results.append(CheckResult(
        "marker_stale_zone",
        not near_stale,
        {"marker_1_stale_point": list(MARKER_1_STALE_POINT),
         "keepout_m": MARKER_1_STALE_KEEPOUT_M,
         "poses_in_keepout": near_stale,
         "unverified_marker_poses": sorted(k for k, ok in verified.items() if not ok),
         "verified_marker_poses": sorted(k for k, ok in verified.items() if ok)},
    ))

    shadowed = {k: hits for k, (_, xy) in poses.items()
                if (hits := marker_occluders(scenario, xy))}
    results.append(CheckResult(
        "markers_unoccluded",
        not shadowed,
        {"camera_m": list(CameraConfig().position_m), "marker_height_m": MARKER_HEIGHT_M,
         "occluded": shadowed},
    ))

    spawn_pairs = {}
    ids = sorted(robots)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ra, rb = robots[a], robots[b]
            spawn_pairs[f"{a}-{b}"] = _round(
                math.dist((ra.spawn.x, ra.spawn.y), (rb.spawn.x, rb.spawn.y)))
    results.append(CheckResult(
        "spawn_pairwise_floor",
        min(spawn_pairs.values()) >= STATIONARY_FLOOR_M,
        {"floor_m": STATIONARY_FLOOR_M, "pairs_m": spawn_pairs,
         "min_m": min(spawn_pairs.values())},
    ))

    clearances = {rid: _round(chassis_clearance_m(grid, r.spawn.x, r.spawn.y,
                                                  r.spawn.yaw_rad, cfg))
                  for rid, r in robots.items()}
    results.append(CheckResult(
        "spawn_chassis_clears_occupied_cells",
        min(clearances.values()) > 0.0,
        {"chassis_x_range_m": list(CHASSIS_X_RANGE_M),
         "half_width_m": CHASSIS_HALF_WIDTH_M, "clearance_m": clearances},
    ))

    free = eroded_free(grid, CHASSIS_HALF_WIDTH_M)
    paths: dict[str, list[tuple[float, float]] | None] = {}
    lengths = {}
    for rid, r in robots.items():
        p = shortest_path(free, point_cell(r.spawn.x, r.spawn.y, cfg),
                          point_cell(r.goal.x, r.goal.y, cfg))
        paths[rid] = None if p is None else path_world(p, cfg)
        lengths[rid] = None if p is None else _round(path_length_m(paths[rid]))
    results.append(CheckResult(
        "solo_path_to_goal",
        all(p is not None for p in paths.values()),
        {"erosion_m": CHASSIS_HALF_WIDTH_M, "path_length_m": lengths},
    ))

    no_detour = {}
    for conflict in oracle.conflicts:
        mx, my = conflict.jam_midpoint_xy
        sealed = free.copy()
        # A disk wider than the 0.55 m aisle seals the jam cross-section.
        seal_r = 0.30
        for row in range(sealed.shape[0]):
            for col in range(sealed.shape[1]):
                if math.dist(cell_center(row, col, cfg), (mx, my)) <= seal_r:
                    sealed[row, col] = False
        for rid in conflict.involved_robots:
            r = robots[rid]
            p = shortest_path(sealed, point_cell(r.spawn.x, r.spawn.y, cfg),
                              point_cell(r.goal.x, r.goal.y, cfg))
            no_detour[f"{conflict.conflict_id}:{rid}"] = p is None
    results.append(CheckResult(
        "no_detour_round_a_sealed_jam",
        all(no_detour.values()),
        {"seal_radius_m": 0.30, "disconnected": no_detour},
    ))

    midpoints = {}
    for conflict in oracle.conflicts:
        a, b = (robots[rid] for rid in conflict.involved_robots)
        p = shortest_path(free, point_cell(a.spawn.x, a.spawn.y, cfg),
                          point_cell(b.spawn.x, b.spawn.y, cfg))
        if p is None:
            midpoints[conflict.conflict_id] = None
            continue
        # Exact spawns replace the end cells' centres, so only the interior
        # carries the half-cell (0.025 m) quantization.
        pts = [(a.spawn.x, a.spawn.y), *path_world(p, cfg)[1:-1], (b.spawn.x, b.spawn.y)]
        mid_x, mid_y = point_at_arc_fraction(pts, 0.5)
        # Path cells sit half a cell off the aisle axis (both aisles' walls
        # fall on cell edges), so y is taken as the centre of the free run of
        # the un-eroded map column the midpoint lies in: the aisle's own axis.
        midpoints[conflict.conflict_id] = (mid_x, free_run_center_y(grid, mid_x, mid_y, cfg))
    measured = [m for m in midpoints.values() if m is not None]
    separation = math.dist(*measured) if len(measured) == 2 else None
    declared = math.dist(*(c.jam_midpoint_xy for c in oracle.conflicts))
    results.append(CheckResult(
        "jam_midpoint_separation",
        separation is not None and separation > oracle.separate_event_radius_m,
        {"measured_midpoints": {k: None if v is None else [_round(c) for c in v]
                                for k, v in midpoints.items()},
         "measured_separation_m": None if separation is None else _round(separation),
         "declared_separation_m": _round(declared),
         "separate_event_radius_m": oracle.separate_event_radius_m,
         "grid_resolution_m": RESOLUTION_M},
    ))

    path_gap = None
    a_ids, b_ids = (c.involved_robots for c in oracle.conflicts)
    pts_a = [pt for rid in a_ids if paths[rid] for pt in paths[rid]]
    pts_b = [pt for rid in b_ids if paths[rid] for pt in paths[rid]]
    if pts_a and pts_b:
        arr_a, arr_b = np.array(pts_a), np.array(pts_b)
        diff = arr_a[:, None, :] - arr_b[None, :, :]
        path_gap = float(np.sqrt((diff ** 2).sum(-1)).min())
    results.append(CheckResult(
        "conflict_routes_disjoint",
        path_gap is not None and path_gap > 2 * CHASSIS_HALF_WIDTH_M,
        {"min_route_gap_m": None if path_gap is None else _round(path_gap)},
    ))

    cross = {}
    for g in STANDOFF_GAPS_M:
        for ra in a_ids:
            for rb in b_ids:
                pa = poses[f"{ra}.standoff_g{g}"][1]
                pb = poses[f"{rb}.standoff_g{g}"][1]
                cross[f"g{g}:{ra}-{rb}"] = _round(math.dist(pa, pb))
    crowded = sorted(k for k, d in cross.items() if d <= ARM_B_R_CONFLICT_M)
    results.append(CheckResult(
        "arm_b_head_on_not_crowded",
        not crowded,
        {"r_conflict_m": ARM_B_R_CONFLICT_M, "cross_pair_standoff_m": cross,
         "within_r_conflict": crowded},
    ))

    gap_a = math.dist(*((robots[r].spawn.x, robots[r].spawn.y) for r in a_ids))
    gap_b = math.dist(*((robots[r].spawn.x, robots[r].spawn.y) for r in b_ids))
    closing = 2 * TRANSIT_SPEED_MPS
    delta = (gap_a - gap_b) / closing
    timing = {
        "spawn_gap_m": {"A": _round(gap_a), "B": _round(gap_b)},
        "close_sec": {f"g{g}": {"A": _round((gap_a - g) / closing),
                                "B": _round((gap_b - g) / closing)}
                      for g in STANDOFF_GAPS_M},
        "b_departure_lag_sim_sec": _round(delta),
        "start_delay_wall_sec_for_rtf": {str(rtf): _round(delta / rtf) for rtf in RTF_RANGE},
        "proposed_start_delay_wall_sec": M5_START_DELAY_WALL_SEC,
        "b_minus_a_standoff_sim_sec": {
            str(rtf): _round(M5_START_DELAY_WALL_SEC * rtf - delta) for rtf in RTF_RANGE},
        "first_trigger_after_standoff_sim_sec": {
            str(rtf): _round(STALL_TRIGGER_WALL_SEC * rtf) for rtf in RTF_RANGE},
    }
    results.append(CheckResult(
        "both_jams_formed_by_first_trigger",
        all(abs(M5_START_DELAY_WALL_SEC * rtf - delta) < STALL_TRIGGER_WALL_SEC * rtf
            for rtf in RTF_RANGE),
        timing,
    ))
    return results


def main() -> int:
    """Entry point: print every check, exit 0 regardless of verdicts."""
    parser = argparse.ArgumentParser(description="Offline S6 feasibility checks")
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args()
    results = run_checks(args.scenario)
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
        return 0
    for r in results:
        print(f"[{'PASS' if r.passed else 'FAIL'}] {r.name}")
        print(f"    {json.dumps(r.detail)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""S1 kinematic Monte Carlo: hotspots, first conflicts, latch-cluster risk.

A committed rebuild of the S1 hotspot Monte Carlo whose assumptions the v3
scene design states ("Sources and Method"; the original ran from a session
scratchpad and was never committed):

- robots run at 0.15 m/s along piecewise-linear routes;
- each robot dwells the registered 5 sim-s at every node;
- releases are staggered by Delta sim-s in robot-id order;
- an *encounter* is a centre gap < 0.45 m, and both robots then freeze (the
  Layer-2-off proxy); a moving robot that comes within 0.45 m of a frozen
  robot freezes too;
- Nav2 deviation is not modelled.

Start nodes and task sequences come from the shipped M5 draws
(`swarm_orchestrator.task_stream.draw_start_nodes` / `draw_task_sequences`),
so the abstract task stream of a seed is the one M5 would run.

Two route sources:
- `nominal`: the S1a scene doc's hand routes (node -> arm mouth -> (0, 0) ->
  arm mouth -> node), used to reproduce the published S1a row;
- `grid`: a NavFn-like Dijkstra on the floor's Nav2 global costmap (static
  layer + the 0.10 m inflation, validated against a live costmap dump), then
  string-pulled through zero-cost cells.

Finished robots either park on their last node (variant C, `park`, what M5
runs today) or wander to the node with the fewest robots at or bound for it
(variant D, `wander`, the scene doc's reference row).

Usage:
    python scripts/s1_mc.py --floor s1a --routes nominal --finished wander
    python scripts/s1_mc.py --floor s1b --scenario isaac/config/scenarios/mapd_5_s1b.yaml

Prints one JSON summary.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "ros2_ws/src/swarm_orchestrator"))

from swarm_orchestrator.task_stream import draw_start_nodes, draw_task_sequences  # noqa: E402

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, load_scenario  # noqa: E402
from isaac.vgu_sim.config import WarehouseConfig  # noqa: E402

V_MPS = 0.15
DWELL_S = 5.0
ENCOUNTER_M = 0.45
DT = 0.1
RES = 0.05
# Live global costmap (s1_pilot evidence dump, bottleneck_merge map): cells at
# centre distance <= 0.0707 m from an occupied cell read INSCRIBED (99 -> 253),
# cells at 0.10 m read 80 (-> ~205), cells beyond read 0.
INSCRIBED_MAX_M = 0.075
INFLATED_MAX_M = 0.101
COST_INSCRIBED = 253
COST_INFLATED = 205
# A single executable yield needs the yielder to back until it is
# `backup_clearance_m` (1.7, config/rag.yaml grounding) from the passer:
# backup >= 1.7 - gap (E1's executed cb78: gap 0.337 -> grounded 1.36 m).
# M3's room GATE asks less (required_room_m, 0.95 m in E1) but the
# retreat-candidate sweep then finds no candidate (the S1b synthetic
# E-handoff check), so resolvability is scored on the backup requirement.
BACKUP_CLEARANCE_M = 1.7
REAR_ROOM_M = 2.0
ROBOT_HALF_WIDTH_M = 0.09
BAND = (-2.5, 2.5, -1.8, 1.8)
ROBOTS = [f"robot_{k}" for k in range(1, 6)]

S1A_NODES = {
    "Wp": (-2.3, 0.35),
    "Wm": (-2.3, -0.35),
    "N": (0.0, 1.55),
    "S": (0.0, -1.55),
    "E": (2.3, 0.0),
}
S1A_MOUTHS = {
    "Wp": (-0.6, 0.35),
    "Wm": (-0.6, -0.35),
    "N": (0.0, 0.6),
    "S": (0.0, -0.6),
    "E": (0.6, 0.0),
}


def edt(occ: np.ndarray, rmax: int = 14) -> np.ndarray:
    """Euclidean distance (cells) to the nearest True cell, capped at rmax."""
    h, w = occ.shape
    out = np.full(occ.shape, float(rmax + 1))
    pad = np.pad(occ, rmax, constant_values=False)
    for di in range(-rmax, rmax + 1):
        for dj in range(-rmax, rmax + 1):
            r = math.hypot(di, dj)
            if r > rmax:
                continue
            sh = pad[rmax + di : rmax + di + h, rmax + dj : rmax + dj + w]
            np.minimum(out, np.where(sh, r, out), out=out)
    return out


@dataclass
class Floor:
    """An occupancy grid in costmap orientation (row 0 = world y min)."""

    name: str
    occ: np.ndarray
    nodes: dict[str, tuple[float, float]]
    forbidden: list[tuple[str, str]]
    regions: list[tuple[str, tuple[float, float, float, float]]]
    origin: tuple[float, float] = (-6.0, -4.0)
    dist_m: np.ndarray = field(init=False)
    cost: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        self.dist_m = edt(self.occ) * RES
        cost = np.zeros(self.occ.shape, dtype=np.int32)
        cost[self.dist_m <= INFLATED_MAX_M] = COST_INFLATED
        cost[self.dist_m <= INSCRIBED_MAX_M] = COST_INSCRIBED
        cost[self.occ] = 254
        self.cost = cost

    def cell(self, x: float, y: float) -> tuple[int, int]:
        return (
            int(math.floor((y - self.origin[1]) / RES)),
            int(math.floor((x - self.origin[0]) / RES)),
        )

    def xy(self, r: int, c: int) -> tuple[float, float]:
        return (self.origin[0] + (c + 0.5) * RES, self.origin[1] + (r + 0.5) * RES)

    def region(self, x: float, y: float) -> str:
        for name, (x0, x1, y0, y1) in self.regions:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return name
        return "open"

    def band_cells(self) -> np.ndarray:
        h, w = self.occ.shape
        rr, cc = np.mgrid[0:h, 0:w]
        xs = self.origin[0] + (cc + 0.5) * RES
        ys = self.origin[1] + (rr + 0.5) * RES
        return (xs >= BAND[0]) & (xs <= BAND[1]) & (ys >= BAND[2]) & (ys <= BAND[3])


def floor_from_scenario(name: str, scenario_path: Path, nodes, forbidden, regions) -> Floor:
    """Build a Floor from a scenario yaml through the shipped map generator."""
    sc = load_scenario(scenario_path)
    grid, _ = build_occupancy_grid(
        WarehouseConfig(),
        obstacles=[],
        resolution_m=RES,
        aisle_barrier=sc.aisle_barrier,
        static_obstacles=sc.static_obstacles,
        loop_map=sc.loop_map,
        rack_clearance=sc.rack_clearance,
    )
    return Floor(name, np.flipud(grid == 0).copy(), nodes, forbidden, regions)


def _dijkstra(
    floor: Floor,
    src: tuple[int, int],
    window: tuple[int, int, int, int],
    blocked: np.ndarray | None = None,
):
    """Single-source cost-weighted Dijkstra (8-connected) inside a cell window."""
    r0, r1, c0, c1 = window
    weight = np.where(floor.cost >= COST_INSCRIBED, np.inf, (50.0 + 0.8 * floor.cost) / 50.0)
    if blocked is not None:
        weight = np.where(blocked, np.inf, weight)
    dist = {src: 0.0}
    prev: dict = {}
    pq = [(0.0, src)]
    steps = [
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, math.sqrt(2)),
        (-1, 1, math.sqrt(2)),
        (1, -1, math.sqrt(2)),
        (1, 1, math.sqrt(2)),
    ]
    done = set()
    while pq:
        d, (r, c) = heapq.heappop(pq)
        if (r, c) in done:
            continue
        done.add((r, c))
        w_here = weight[r, c]
        for dr, dc, ln in steps:
            nr, nc = r + dr, c + dc
            if not (r0 <= nr < r1 and c0 <= nc < c1):
                continue
            wgt = weight[nr, nc]
            if not np.isfinite(wgt):
                continue
            nd = d + ln * 0.5 * (wgt + w_here)
            if nd < dist.get((nr, nc), np.inf):
                dist[(nr, nc)] = nd
                prev[(nr, nc)] = (r, c)
                heapq.heappush(pq, (nd, (nr, nc)))
    return dist, prev


def _string_pull(floor: Floor, pts: list, blocked: np.ndarray | None = None) -> np.ndarray:
    def clear(p, q) -> bool:
        n = max(2, int(math.hypot(q[0] - p[0], q[1] - p[1]) / (RES / 2)) + 1)
        for t in np.linspace(0.0, 1.0, n):
            x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
            r, c = floor.cell(x, y)
            if floor.cost[r, c] > 0 or (blocked is not None and blocked[r, c]):
                return False
        return True

    out = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not clear(pts[i], pts[j]):
            j -= 1
        out.append(pts[j])
        i = j
    return np.array(out)


def grid_routes_from(
    floor: Floor, a: tuple[float, float], targets: dict, blocked: np.ndarray | None = None
) -> dict:
    """NavFn-like routes from one point to several: Dijkstra, then string-pulled.

    `blocked` marks extra lethal cells (frozen robots' 0.45 m disks in the
    reroute variant); the start cell is always admitted.
    """
    margin = 0.3
    r0, c0 = floor.cell(BAND[0] - margin, BAND[2] - margin)
    r1, c1 = floor.cell(BAND[1] + margin, BAND[3] + margin)
    src = floor.cell(*a)
    if blocked is not None:
        blocked = blocked.copy()
        blocked[src] = False
    dist, prev = _dijkstra(floor, src, (r0, r1 + 1, c0, c1 + 1), blocked)
    out = {}
    for name, b in targets.items():
        goal = floor.cell(*b)
        if goal not in dist:
            raise ValueError(f"no route {a} -> {b} on {floor.name}")
        cells = [goal]
        while cells[-1] != src:
            cells.append(prev[cells[-1]])
        cells.reverse()
        pts = [a] + [floor.xy(r, c) for r, c in cells[1:-1]] + [b]
        out[name] = _string_pull(floor, pts, blocked)
    return out


def grid_route(floor: Floor, a: tuple[float, float], b: tuple[float, float]) -> np.ndarray:
    """Single NavFn-like route (see `grid_routes_from`)."""
    return grid_routes_from(floor, a, {"b": b})["b"]


def nominal_route(a: str, b: str) -> np.ndarray:
    """S1a scene-doc route: node -> arm mouth -> (0, 0) -> arm mouth -> node."""
    pts = [S1A_NODES[a], S1A_MOUTHS[a], (0.0, 0.0), S1A_MOUTHS[b], S1A_NODES[b]]
    return np.array(pts)


def polyline_len(p: np.ndarray) -> float:
    return float(np.sum(np.hypot(*np.diff(p, axis=0).T)))


class Path_:
    """Arc-length parametrised polyline."""

    def __init__(self, pts: np.ndarray) -> None:
        self.pts = pts
        seg = np.hypot(*np.diff(pts, axis=0).T)
        self.cum = np.concatenate([[0.0], np.cumsum(seg)])
        self.length = float(self.cum[-1])

    def at(self, s: float) -> tuple[float, float, float]:
        s = min(max(s, 0.0), self.length)
        i = int(np.searchsorted(self.cum, s, side="right") - 1)
        i = min(i, len(self.pts) - 2)
        seg = self.cum[i + 1] - self.cum[i]
        t = 0.0 if seg <= 0 else (s - self.cum[i]) / seg
        p, q = self.pts[i], self.pts[i + 1]
        return (
            p[0] + t * (q[0] - p[0]),
            p[1] + t * (q[1] - p[1]),
            math.atan2(q[1] - p[1], q[0] - p[0]),
        )


@dataclass
class Robot:
    rid: str
    node: str
    tasks: list[str]
    release_t: float
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    phase: str = "held"  # held, travel, dwell, done, frozen
    path: Path_ | None = None
    s: float = 0.0
    target: str | None = None
    dwell_end: float = 0.0
    done_tasks: int = 0
    wander: bool = False
    moving: bool = False


# Spawn heading per node label (scene design S1 / mapd_5 header; S1b keeps
# the labels' yaws).
NODE_YAW = {"Wp": 0.0, "Wm": 0.0, "N": -math.pi / 2, "S": math.pi / 2, "E": math.pi}


def _snapshot_row(r: Robot, floor: Floor) -> dict:
    """One robot as a Layer-2 snapshot sees it: pose, M1-like status, registry goal."""
    if r.phase in ("travel",):
        goal = floor.nodes[r.target]
    elif r.phase == "held":
        goal = floor.nodes[r.tasks[0]]
    elif r.phase == "dwell":
        goal = floor.nodes[r.node]
    elif r.phase == "frozen":
        goal = floor.nodes[r.target] if r.target else floor.nodes[r.node]
    else:  # done (parked)
        goal = floor.nodes[r.node]
    return {
        "robot_id": r.rid,
        "x": r.x,
        "y": r.y,
        "theta": r.heading,
        "status": "MOVING" if r.phase == "travel" else "STOPPED",
        "goal": goal,
        "phase": r.phase,
    }


def kind_of(a: Robot, b: Robot) -> str:
    if not (a.moving and b.moving):
        return "static"
    d = abs((a.heading - b.heading + math.pi) % (2 * math.pi) - math.pi)
    if d > math.radians(135):
        return "head-on"
    if d < math.radians(45):
        return "same-direction"
    return "crossing"


def rear_room(floor: Floor, rob: Robot, others: list[Robot]) -> float:
    """Clear distance behind a robot along its reverse heading (capped at REAR_ROOM_M).

    Blocked by the band edge, by a static obstacle within the robot's
    half-width + 0.05 m (M3's retreat_box_margin_m), or by entering another
    robot's 0.45 m radius while closing on it.
    """
    back = rob.heading + math.pi
    step = 0.02
    s = 0.0
    while s < REAR_ROOM_M:
        s2 = s + step
        x = rob.x + s2 * math.cos(back)
        y = rob.y + s2 * math.sin(back)
        if not (BAND[0] <= x <= BAND[1] and BAND[2] <= y <= BAND[3]):
            return s
        r, c = floor.cell(x, y)
        if floor.dist_m[r, c] < ROBOT_HALF_WIDTH_M + 0.05:
            return s
        for o in others:
            if o is rob:
                continue
            d_now = math.hypot(o.x - x, o.y - y)
            d_prev = math.hypot(
                o.x - (rob.x + s * math.cos(back)), o.y - (rob.y + s * math.sin(back))
            )
            if d_now < ENCOUNTER_M and d_now < d_prev:
                return s
        s = s2
    return REAR_ROOM_M


def _frozen_mask(floor: Floor, frozen: list[Robot]) -> np.ndarray:
    h, w = floor.occ.shape
    rr, cc = np.mgrid[0:h, 0:w]
    xs = floor.origin[0] + (cc + 0.5) * RES
    ys = floor.origin[1] + (rr + 0.5) * RES
    mask = np.zeros((h, w), dtype=bool)
    for f in frozen:
        mask |= np.hypot(xs - f.x, ys - f.y) < ENCOUNTER_M + RES
    return mask


CONVERGE_R_M = 1.0


def _track_exposure(robots, floor, t, contacts, open_contacts, conv_state) -> None:
    """Pass-through (no freeze) exposure bookkeeping.

    A *contact* is a contiguous interval with centre gap < 0.45 m (the
    encounter definition) while robots pass through each other; its duration
    is how long a real pair would sit inside the latch radius. A
    *multi-contact* is >= 3 robots in one < 0.45 m component; a *node
    convergence* is >= 3 robots within 1.0 m of one task node (E2's S-node
    triple). Both are counted once per onset.
    """
    ids = list(range(len(robots)))
    adj = {i: set() for i in ids}
    for i in ids:
        for j in ids[i + 1 :]:
            a, b = robots[i], robots[j]
            gap = math.hypot(a.x - b.x, a.y - b.y)
            key = (a.rid, b.rid)
            if gap < ENCOUNTER_M:
                adj[i].add(j)
                adj[j].add(i)
                if key not in open_contacts:
                    open_contacts[key] = {
                        "onset": t,
                        "end": t,
                        "kind": kind_of(a, b),
                        "mid": ((a.x + b.x) / 2, (a.y + b.y) / 2),
                        "region": floor.region((a.x + b.x) / 2, (a.y + b.y) / 2),
                    }
                open_contacts[key]["end"] = t
            elif key in open_contacts:
                contacts.append(open_contacts.pop(key))
    seen, big = set(), 0
    for i in ids:
        if i in seen:
            continue
        stack, comp = [i], 0
        seen.add(i)
        while stack:
            k = stack.pop()
            comp += 1
            for n in adj[k]:
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        big = max(big, comp)
    if big >= 3 and not conv_state["multi"]:
        conv_state["multi_events"] += 1
    conv_state["multi"] = big >= 3
    for node, (nx, ny) in floor.nodes.items():
        near = sum(1 for r in robots if math.hypot(r.x - nx, r.y - ny) < CONVERGE_R_M)
        was = conv_state["node"].get(node, False)
        if near >= 3 and not was:
            conv_state["node_events"] += 1
        conv_state["node"][node] = near >= 3


def _largest_cluster(robots: list[Robot], pairs: set[frozenset]) -> int:
    parent = {r.rid: r.rid for r in robots}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for p in pairs:
        a, b = tuple(p)
        parent[find(a)] = find(b)
    sizes = Counter(find(a) for p in pairs for a in p)
    return max((sum(1 for r in robots if find(r.rid) == k) for k in sizes), default=0)


def run_episode(
    floor: Floor,
    routes: dict,
    seed: int,
    *,
    delta: float,
    finished: str,
    freeze: bool,
    horizon: float = 600.0,
    reroute: bool = False,
    snapshot_delay: float | None = None,
) -> dict:
    """Simulate one seeded episode; return its encounter / flow record.

    `snapshot_delay` (freeze mode): also record every robot's state
    `snapshot_delay` sim-s after the first encounter (`first_snapshot`), the
    scene a stall-triggered Layer-2 analysis would see.

    `reroute` (freeze mode only, the latch-cluster-risk variant): after each
    new freeze, every travelling robot whose remaining route passes within
    0.45 m of a frozen robot replans around the frozen robots' 0.45 m disks
    (Nav2 sees a stopped robot and plans around it when the floor allows);
    with no such route it keeps its old one.
    """
    node_ids = sorted(floor.nodes)
    starts = draw_start_nodes(seed, ROBOTS, node_ids)
    seqs = draw_task_sequences(seed, starts, node_ids, 5, floor.forbidden)
    robots = []
    for k, rid in enumerate(ROBOTS):
        r = Robot(rid, starts[rid], list(seqs[rid]), k * delta)
        r.x, r.y = floor.nodes[r.node]
        r.heading = NODE_YAW.get(r.node, 0.0)
        robots.append(r)
    first_snapshot: list[dict] | None = None

    def start_leg(r: Robot, dest: str, t: float) -> None:
        r.path = Path_(routes[(r.node, dest)])
        r.s = 0.0
        r.target = dest
        r.phase = "travel"

    def concentration(node: str, me: Robot) -> int:
        n = 0
        for o in robots:
            if o is me:
                continue
            if (o.phase == "travel" and o.target == node) or (
                o.phase != "travel" and o.node == node
            ):
                n += 1
        return n

    encounters: list[dict] = []
    frozen_pairs: set[frozenset] = set()
    new_freeze = False
    reroutes = 0
    t_cluster3 = None
    contacts: list[dict] = []
    open_contacts: dict = {}
    conv_state = {"multi": False, "multi_events": 0, "node": {}, "node_events": 0}
    occupied_arrivals = 0
    wander_legs = 0
    completed = 0
    makespan = None
    t = 0.0
    nsteps = int(horizon / DT) + 1
    for _ in range(nsteps):
        t = round(t + DT, 6)
        for r in robots:
            r.moving = False
            if r.phase == "frozen":
                continue
            if r.phase == "held" and t >= r.release_t - 1e-9:
                start_leg(r, r.tasks[0], t)
            elif r.phase == "dwell" and t >= r.dwell_end - 1e-9:
                r.done_tasks += 1
                completed += 1
                if completed == 25:
                    makespan = t
                if r.done_tasks < len(r.tasks):
                    start_leg(r, r.tasks[r.done_tasks], t)
                else:
                    r.phase = "done"
                    if finished == "wander":
                        best = min(
                            (
                                n
                                for n in node_ids
                                if n != r.node
                                and frozenset((r.node, n))
                                not in {frozenset(f) for f in floor.forbidden}
                            ),
                            key=lambda n: (
                                concentration(n, r),
                                polyline_len(routes[(r.node, n)]),
                                n,
                            ),
                        )
                        if concentration(best, r) < concentration(r.node, r):
                            r.wander = True
                            wander_legs += 1
                            start_leg(r, best, t)
            if r.phase == "travel":
                r.s += V_MPS * DT
                x, y, hd = r.path.at(r.s)
                r.x, r.y, r.heading = x, y, hd
                r.moving = True
                if r.s >= r.path.length - 1e-9:
                    r.node = r.target
                    nx, ny = floor.nodes[r.node]
                    if any(
                        o is not r
                        and o.phase != "travel"
                        and math.hypot(o.x - nx, o.y - ny) < ENCOUNTER_M
                        for o in robots
                    ):
                        occupied_arrivals += 1
                    if r.wander:
                        r.phase = "done"
                        r.wander = False
                    else:
                        r.phase = "dwell"
                        r.dwell_end = t + DWELL_S
        if not freeze:
            _track_exposure(robots, floor, t, contacts, open_contacts, conv_state)
        if makespan is not None and not freeze:
            break
        if freeze:
            for i, a in enumerate(robots):
                for b in robots[i + 1 :]:
                    key = frozenset((a.rid, b.rid))
                    if key in frozen_pairs:
                        continue
                    if not (a.moving or b.moving):
                        continue
                    gap = math.hypot(a.x - b.x, a.y - b.y)
                    if gap >= ENCOUNTER_M:
                        continue
                    if a.phase != "frozen" and b.phase != "frozen" or a.moving or b.moving:
                        mid = ((a.x + b.x) / 2, (a.y + b.y) / 2)
                        need = BACKUP_CLEARANCE_M - gap
                        rooms = {
                            a.rid: rear_room(floor, a, robots),
                            b.rid: rear_room(floor, b, robots),
                        }
                        encounters.append(
                            {
                                "t": t,
                                "pair": sorted([a.rid, b.rid]),
                                "kind": kind_of(a, b),
                                "region": floor.region(*mid),
                                "mid": mid,
                                "into_frozen": a.phase == "frozen" or b.phase == "frozen",
                                "delta_artifact": a.phase == "held" or b.phase == "held",
                                "resolvable": max(rooms.values()) >= need - 1e-9,
                            }
                        )
                        frozen_pairs.add(key)
                        a.phase = "frozen"
                        b.phase = "frozen"
                        a.moving = b.moving = False
                        new_freeze = True
            if new_freeze and t_cluster3 is None and _largest_cluster(robots, frozen_pairs) >= 3:
                t_cluster3 = t
            if reroute and new_freeze:
                frozen = [r for r in robots if r.phase == "frozen"]
                mask = _frozen_mask(floor, frozen)
                for r in robots:
                    if r.phase != "travel":
                        continue
                    rest = [r.path.at(s_)[:2] for s_ in np.arange(r.s, r.path.length, 0.05)]
                    if not any(
                        math.hypot(px - f.x, py - f.y) < ENCOUNTER_M
                        for px, py in rest
                        for f in frozen
                    ):
                        continue
                    try:
                        pts = grid_routes_from(
                            floor, (r.x, r.y), {"t": floor.nodes[r.target]}, mask
                        )["t"]
                    except ValueError:
                        continue
                    r.path = Path_(pts)
                    r.s = 0.0
                    reroutes += 1
                new_freeze = False
            if (
                snapshot_delay is not None
                and first_snapshot is None
                and encounters
                and t >= encounters[0]["t"] + snapshot_delay - 1e-9
            ):
                first_snapshot = [_snapshot_row(r, floor) for r in robots]
            if all(r.phase in ("frozen", "done") for r in robots) and (
                snapshot_delay is None or first_snapshot is not None
            ):
                break
    # final clusters over frozen pairs
    parent = {r.rid: r.rid for r in robots}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for p in frozen_pairs:
        a, b = tuple(p)
        parent[find(a)] = find(b)
    sizes = Counter(find(r.rid) for r in robots if r.phase == "frozen")
    biggest = max(sizes.values()) if sizes else 0
    return {
        "seed": seed,
        "encounters": encounters,
        "completed": completed,
        "makespan": makespan,
        "occupied_arrivals": occupied_arrivals,
        "wander_legs": wander_legs,
        "biggest_cluster": biggest,
        "t_end": t,
        "first_snapshot": first_snapshot,
        "reroutes": reroutes,
        "t_cluster3": t_cluster3,
        "contacts": contacts + [dict(v, open=True) for v in open_contacts.values()],
        "multi_contact_events": conv_state["multi_events"],
        "node_convergence_events": conv_state["node_events"],
        "frozen_at_end": sum(1 for r in robots if r.phase == "frozen"),
    }


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))] if xs else None


def summarise(eps: list[dict], window_m: float = 1.2) -> dict:
    """Aggregate episode records into the published-row statistics."""
    with_enc = [e for e in eps if e["encounters"]]
    firsts = [e["encounters"][0] for e in with_enc]
    ft = [f["t"] for f in firsts]
    out = {
        "episodes": len(eps),
        "with_encounter": len(with_enc),
        "first_t_median": statistics.median(ft) if ft else None,
        "first_t_p10": pct(ft, 0.1),
        "first_t_p90": pct(ft, 0.9),
        "encounters_per_episode": sum(len(e["encounters"]) for e in eps) / len(eps),
        "into_frozen_total": sum(sum(1 for x in e["encounters"] if x["into_frozen"]) for e in eps),
        "encounters_total": sum(len(e["encounters"]) for e in eps),
        "first_region": dict(Counter(f["region"] for f in firsts).most_common()),
        "first_kind": dict(Counter(f["kind"] for f in firsts).most_common()),
        "first_resolvable": sum(1 for f in firsts if f["resolvable"]),
        "all_resolvable_frac": (
            sum(sum(1 for x in e["encounters"] if x["resolvable"]) for e in eps)
            / max(1, sum(len(e["encounters"]) for e in eps))
        ),
        "first_delta_artifact": sum(1 for f in firsts if f.get("delta_artifact")),
        "delta_artifact_any": sum(
            1 for e in eps if any(x.get("delta_artifact") for x in e["encounters"])
        ),
        "frozen_at_end_mean": sum(e.get("frozen_at_end", 0) for e in eps) / len(eps),
        "reroutes_mean": sum(e.get("reroutes", 0) for e in eps) / len(eps),
        "cluster_ge3": sum(1 for e in eps if e["biggest_cluster"] >= 3),
        # Latch-cluster risk: a >= 3-robot frozen cluster within W sim-s of the
        # episode's first encounter (W = 60, E1's measured yield chain: dispatch
        # 48.6 -> clearance release 103.3 sim-s = 55 sim-s, rounded up).
        "cluster3_within_60s": sum(
            1
            for e in eps
            if e["encounters"]
            and e.get("t_cluster3") is not None
            and e["t_cluster3"] - e["encounters"][0]["t"] <= 60.0
        ),
        "cluster3_lag_median": (
            statistics.median(
                [
                    e["t_cluster3"] - e["encounters"][0]["t"]
                    for e in eps
                    if e["encounters"] and e.get("t_cluster3") is not None
                ]
            )
            if any(e.get("t_cluster3") is not None for e in eps)
            else None
        ),
        "cluster_5": sum(1 for e in eps if e["biggest_cluster"] >= 5),
        "completed_all": sum(1 for e in eps if e["completed"] == 25),
    }
    # Floor-independent concentration: the largest share of first conflicts in
    # any window_m x window_m square (S1a's junction box is 1.2 x 1.2).
    if firsts:
        mids = np.array([f["mid"] for f in firsts])
        best = 0
        best_c = None
        for cx in np.arange(-2.5, 2.5 + 1e-9, 0.05):
            for cy in np.arange(-1.8, 1.8 + 1e-9, 0.05):
                n = int(
                    np.sum(
                        (np.abs(mids[:, 0] - cx) <= window_m / 2)
                        & (np.abs(mids[:, 1] - cy) <= window_m / 2)
                    )
                )
                if n > best:
                    best, best_c = n, (round(float(cx), 2), round(float(cy), 2))
        out["max_window_share"] = best / len(firsts)
        out["max_window_centre"] = best_c
        # 0.5 m hotspot map of first conflicts
        hist = Counter()
        for f in firsts:
            hist[(math.floor(f["mid"][0] / 0.5) * 0.5, math.floor(f["mid"][1] / 0.5) * 0.5)] += 1
        out["hotspot_0p5m"] = {f"{k[0]:+.1f},{k[1]:+.1f}": v for k, v in hist.most_common(12)}
    return out


def flow_summary(eps: list[dict]) -> dict:
    ms = [e["makespan"] for e in eps if e["makespan"] is not None]
    cs = [c for e in eps for c in e.get("contacts", [])]
    durs = [c["end"] - c["onset"] + DT for c in cs]
    return {
        "contacts_per_episode": len(cs) / len(eps),
        "contact_duration_median": statistics.median(durs) if durs else None,
        "contact_duration_p90": pct(durs, 0.9),
        "contacts_long_ge5s_frac": (sum(1 for d in durs if d >= 5.0) / len(durs)) if durs else None,
        "contact_kinds": dict(Counter(c["kind"] for c in cs).most_common()),
        "multi_contact_events_per_episode": sum(e["multi_contact_events"] for e in eps) / len(eps),
        "node_convergence_events_per_episode": sum(e["node_convergence_events"] for e in eps)
        / len(eps),
        "episodes": len(eps),
        "completed": len(ms),
        "makespan_median": statistics.median(ms) if ms else None,
        "makespan_p10": pct(ms, 0.1),
        "makespan_p90": pct(ms, 0.9),
        "wander_legs_mean": sum(e["wander_legs"] for e in eps) / len(eps),
        "occupied_arrivals_mean": sum(e["occupied_arrivals"] for e in eps) / len(eps),
    }


def mc_seeds(n: int) -> list[int]:
    """The MC draw set: seeds 1..n (independent of the registered episode list)."""
    return list(range(1, n + 1))


def build_routes(floor: Floor, mode: str) -> dict:
    routes = {}
    for a in floor.nodes:
        others = {b: floor.nodes[b] for b in floor.nodes if b != a}
        if mode == "nominal":
            for b in others:
                routes[(a, b)] = nominal_route(a, b)
        else:
            for b, pts in grid_routes_from(floor, floor.nodes[a], others).items():
                routes[(a, b)] = pts
    return routes


S1A_REGIONS = [
    ("junction", (-0.6, 0.6, -0.6, 0.6)),
    ("E mouth", (0.6, 0.7, -0.6, 0.6)),
    ("E gate/bay", (0.7, 3.0, -0.6, 0.6)),
    ("W arm", (-3.0, -0.6, -0.6, 0.6)),
    ("N arm", (-0.6, 0.6, 0.6, 2.3)),
    ("S arm", (-0.6, 0.6, -2.3, -0.6)),
]


def s1a_floor() -> Floor:
    return floor_from_scenario(
        "s1a",
        REPO / "isaac/config/scenarios/bottleneck_merge.yaml",
        S1A_NODES,
        [("Wp", "Wm")],
        S1A_REGIONS,
    )


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", choices=["s1a", "s1b"], default="s1a")
    ap.add_argument("--scenario", type=Path, default=None)
    ap.add_argument("--routes", choices=["nominal", "grid"], default="grid")
    ap.add_argument("--finished", choices=["wander", "park"], default="wander")
    ap.add_argument("--delta", type=float, default=4.0)
    ap.add_argument("--n", type=int, default=400)
    args = ap.parse_args()
    if args.floor == "s1a":
        floor = s1a_floor()
    else:
        from scripts.s1b_layout import s1b_floor  # noqa: PLC0415

        floor = s1b_floor(args.scenario)
    routes = build_routes(floor, args.routes)
    seeds = mc_seeds(args.n)
    frozen = [
        run_episode(floor, routes, s, delta=args.delta, finished=args.finished, freeze=True)
        for s in seeds
    ]
    free = [
        run_episode(floor, routes, s, delta=args.delta, finished=args.finished, freeze=False)
        for s in seeds
    ]
    print(
        json.dumps(
            {
                "floor": floor.name,
                "routes": args.routes,
                "finished": args.finished,
                "delta": args.delta,
                "n": args.n,
                "leg_lengths": {
                    f"{a}-{b}": round(polyline_len(p), 3) for (a, b), p in routes.items()
                },
                "freeze": summarise(frozen),
                "free_flow": flow_summary(free),
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()

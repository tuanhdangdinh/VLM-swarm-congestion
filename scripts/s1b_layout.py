"""S1b (sparse-warehouse regime variant) floor: geometry checks and density table.

Builds the S1b floor through the shipped map generator (rack clearance of
the tracked band + the scene's rack islands as static obstacles), then
reports what prereg-v3 R3.6a asks for:

- rack coverage as a share of the tracked band (|x| <= 2.5, |y| <= 1.8);
- every corridor between islands and walls, with its width arithmetic
  against the latch-aware bound (two passing robots need centre separation
  >= 0.45 m, each centre outside the Nav2 inflation of its wall);
- free cells per agent, nominal (pre-inflation, geometric) and on the
  post-inflation global costmap, for the S1a floor and the S1b floor (the
  regime-axis table);
- which node-pair routes pass through the shared corridor (grid router of
  scripts/s1_mc.py, not by eye);
- the release-stagger feasibility bound 4*Delta < (L_min - 0.45) / v on the
  new leg lengths.

Usage:
    python scripts/s1b_layout.py [--scenario isaac/config/scenarios/mapd_5_s1b.yaml]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import s1_mc as M  # noqa: E402

S1B_SCENARIO = REPO / "isaac/config/scenarios/mapd_5_s1b.yaml"
BAND_AREA_M2 = 5.0 * 3.6
N_AGENTS = 5


def _islands(scenario) -> list[tuple[str, float, float, float, float]]:
    """Rack islands = static obstacles whose centre lies inside the band."""
    out = []
    for o in scenario.static_obstacles:
        if abs(o.pose.x) <= 2.5 and abs(o.pose.y) <= 1.8:
            out.append(
                (
                    o.obstacle_id,
                    o.pose.x - o.size.x_m / 2,
                    o.pose.x + o.size.x_m / 2,
                    o.pose.y - o.size.y_m / 2,
                    o.pose.y + o.size.y_m / 2,
                )
            )
    return out


def s1b_nodes(scenario) -> dict[str, tuple[float, float]]:
    """Task nodes from the scenario's M5 overlay snippet (header comment)."""
    import yaml

    lines = Path(scenario).read_text().splitlines()
    begin = lines.index("#   --- M5 overlay begin ---")
    end = lines.index("#   --- M5 overlay end ---")
    block = yaml.safe_load(
        "\n".join(line[4:] if line != "#" else "" for line in lines[begin + 1 : end])
    )
    ts = block["task_stream"]
    return (
        {k: tuple(v) for k, v in ts["nodes"].items()},
        [tuple(p) for p in ts.get("forbidden_legs", [])],
    )


def s1b_overlay(scenario) -> dict:
    """The scenario header's M5 overlay snippet as a dict."""
    import yaml

    lines = Path(scenario).read_text().splitlines()
    begin = lines.index("#   --- M5 overlay begin ---")
    end = lines.index("#   --- M5 overlay end ---")
    return yaml.safe_load(
        "\n".join(line[4:] if line != "#" else "" for line in lines[begin + 1 : end])
    )


def s1b_regions(islands) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Named regions: the inter-island corridor first, then the island gaps."""
    (_, ax0, ax1, ay0, ay1), (_, bx0, bx1, by0, by1) = sorted(islands, key=lambda i: i[1])
    oy0, oy1 = max(ay0, by0), min(ay1, by1)
    return [
        ("corridor", (ax1, bx0, oy0, oy1)),
        ("west passage", (-2.5, ax0, ay0, ay1)),
        ("east passage", (bx1, 2.5, by0, by1)),
        ("north of west island", (ax0 - 0.3, ax1 + 0.3, ay1, 1.8)),
        ("south of west island", (ax0 - 0.3, ax1 + 0.3, -1.8, ay0)),
        ("north of east island", (bx0 - 0.3, bx1 + 0.3, by1, 1.8)),
        ("south of east island", (bx0 - 0.3, bx1 + 0.3, -1.8, by0)),
    ]


def s1b_floor(scenario_path: Path | None = None) -> M.Floor:
    """Build the S1b Floor (generator grid, overlay nodes, named regions)."""
    from isaac.scripts.generate_warehouse_map import load_scenario

    path = scenario_path or S1B_SCENARIO
    sc = load_scenario(path)
    nodes, forbidden = s1b_nodes(path)
    return M.floor_from_scenario("s1b", path, nodes, forbidden, s1b_regions(_islands(sc)))


def corridor_table(floor: M.Floor, islands) -> list[dict]:
    """Physical and costmap widths of every island-island / island-wall gap."""
    (_, ax0, ax1, ay0, ay1), (_, bx0, bx1, by0, by1) = sorted(islands, key=lambda i: i[1])
    gaps = [
        ("west wall <-> west island", "x", -2.5, ax0, (ay0 + ay1) / 2),
        ("west island <-> east island", "x", ax1, bx0, (max(ay0, by0) + min(ay1, by1)) / 2),
        ("east island <-> east wall", "x", bx1, 2.5, (by0 + by1) / 2),
        ("west island <-> north wall", "y", ay1, 1.8, (ax0 + ax1) / 2),
        ("west island <-> south wall", "y", -1.8, ay0, (ax0 + ax1) / 2),
        ("east island <-> north wall", "y", by1, 1.8, (bx0 + bx1) / 2),
        ("east island <-> south wall", "y", -1.8, by0, (bx0 + bx1) / 2),
    ]
    out = []
    for name, axis, lo, hi, at in gaps:
        width = hi - lo
        # Walk the costmap across the gap at the gap's mid-span.
        n = int(round(width / M.RES))
        cells = []
        for k in range(n):
            u = lo + (k + 0.5) * M.RES
            x, y = (u, at) if axis == "x" else (at, u)
            r, c = floor.cell(x, y)
            cells.append(int(floor.cost[r, c]))
        traversable = sum(1 for v in cells if v < M.COST_INSCRIBED) * M.RES
        zero = sum(1 for v in cells if v == 0) * M.RES
        out.append(
            {
                "gap": name,
                "physical_m": round(width, 3),
                "centre_traversable_m": round(traversable, 3),
                "zero_cost_m": round(zero, 3),
                # Two robot centres 0.45 apart, both on zero-cost cells.
                "two_lane_ok": zero >= 0.45 - 1e-9,
                "meets_0p85": width >= 0.85 - 1e-9,
                "meets_0p90": width >= 0.90 - 1e-9,
            }
        )
    return out


def density_row(floor: M.Floor, island_area_m2: float, nominal_free_m2: float) -> dict:
    band = floor.band_cells()
    cell_m2 = M.RES * M.RES
    trav = float(np.sum(band & (floor.cost < M.COST_INSCRIBED))) * cell_m2
    zero = float(np.sum(band & (floor.cost == 0))) * cell_m2
    row = {
        "floor": floor.name,
        "obstacle_in_band_m2": round(island_area_m2, 3),
        "obstacle_share_of_band": round(island_area_m2 / BAND_AREA_M2, 4),
        "nominal_free_m2": round(nominal_free_m2, 3),
        "postinfl_traversable_m2": round(trav, 3),
        "postinfl_zero_cost_m2": round(zero, 3),
    }
    for label, area in (
        ("nominal", nominal_free_m2),
        ("postinfl_trav", trav),
        ("postinfl_zero", zero),
    ):
        row[f"{label}_cells055_per_agent"] = round(area / 0.55**2 / N_AGENTS, 2)
        row[f"{label}_cells045_per_agent"] = round(area / 0.45**2 / N_AGENTS, 2)
    return row


def gap_rects(islands) -> dict[str, tuple[float, float, float, float]]:
    """Every island-island and island-wall gap as an (x0, x1, y0, y1) rect."""
    (_, ax0, ax1, ay0, ay1), (_, bx0, bx1, by0, by1) = sorted(islands, key=lambda i: i[1])
    return {
        "island_w <-> island_e": (ax1, bx0, max(ay0, by0), min(ay1, by1)),
        "west wall <-> island_w": (-2.5, ax0, ay0, ay1),
        "island_e <-> east wall": (bx1, 2.5, by0, by1),
        "island_w <-> north wall": (ax0, ax1, ay1, 1.8),
        "island_w <-> south wall": (ax0, ax1, -1.8, ay0),
        "island_e <-> north wall": (bx0, bx1, by1, 1.8),
        "island_e <-> south wall": (bx0, bx1, -1.8, by0),
    }


def routes_through_gaps(floor: M.Floor, routes: dict, islands) -> dict[str, list[str]]:
    """Unordered node pairs whose route traverses each gap end to end.

    A route counts for a gap when >= 0.4 m of it lies inside the gap's
    rectangle and neither endpoint node is inside it (a node's own gap is
    not a shared corridor).
    """

    def inside(p, r) -> bool:
        return r[0] <= p[0] <= r[1] and r[2] <= p[1] <= r[3]

    out: dict[str, list[str]] = {}
    for name, rect in gap_rects(islands).items():
        hits = []
        for (a, b), pts in routes.items():
            if a > b or inside(floor.nodes[a], rect) or inside(floor.nodes[b], rect):
                continue
            p = M.Path_(pts)
            run = sum(1 for s in np.arange(0.0, p.length, 0.05) if inside(p.at(s)[:2], rect)) * 0.05
            if run >= 0.4:
                hits.append(f"{a}-{b}")
        out[name] = hits
    return out


def report(scenario_path: Path | None = None) -> dict:
    """Full S1b geometry report (JSON-serialisable)."""
    from isaac.scripts.generate_warehouse_map import load_scenario

    path = scenario_path or S1B_SCENARIO
    sc = load_scenario(path)
    isl = _islands(sc)
    floor = s1b_floor(path)
    routes = M.build_routes(floor, "grid")
    island_area = sum((x1 - x0) * (y1 - y0) for _, x0, x1, y0, y1 in isl)
    s1a = M.s1a_floor()
    # S1a nominal free floor (scene doc): 8.88 m2 of the band minus the A55-E
    # gate blocks 0.65 m2 -> 8.23 m2; obstacles 9.12 + 0.65 = 9.77 m2.
    lengths = {f"{a}->{b}": round(M.polyline_len(p), 3) for (a, b), p in routes.items()}
    allowed = [
        M.polyline_len(p)
        for (a, b), p in routes.items()
        if frozenset((a, b)) not in {frozenset(f) for f in floor.forbidden}
    ]
    lmin = min(allowed)
    nodes = floor.nodes
    pair_d = {
        f"{a}-{b}": round(math.dist(nodes[a], nodes[b]), 3)
        for i, a in enumerate(sorted(nodes))
        for b in sorted(nodes)[i + 1 :]
    }
    return {
        "islands": isl,
        "coverage_of_band": round(island_area / BAND_AREA_M2, 4),
        "corridors": corridor_table(floor, isl),
        "density": [
            density_row(s1a, 9.77, 8.23),
            density_row(floor, island_area, BAND_AREA_M2 - island_area),
        ],
        "node_pair_euclid_m": pair_d,
        "leg_lengths_m": lengths,
        "lmin_allowed_m": round(lmin, 3),
        "delta_bound_sim_s": round((lmin - 0.45) / M.V_MPS / 4.0, 3),
        "routes_through_gaps": routes_through_gaps(floor, routes, isl),
        "node_min_clearance_m": {
            n: round(float(floor.dist_m[floor.cell(*xy)]), 3) for n, xy in nodes.items()
        },
    }


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", type=Path, default=None)
    args = ap.parse_args()
    print(json.dumps(report(args.scenario), indent=1))


if __name__ == "__main__":
    main()

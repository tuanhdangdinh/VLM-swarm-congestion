#!/usr/bin/env python3
"""Generate the solo-in-space free-flow scenario variants (one per robot per cell).

The prereg-v2 spec ("Foundations round adopted (2026-10-05)", METHOD RULED)
fixes free-flow baselines as SOLO-IN-SPACE: each robot traverses its cell's
course ALONE, on its own scenario variant with its own USD build. A parked
robot is an obstacle, so the other robots are absent rather than staggered
(`docs/reports/2026-10-05-flow-metrics.md` Part 2 has the per-order clearance
table that rules solo-in-time out).

For each registered cell and each of its robots this writes
`isaac/config/scenarios/free_flow/<cell>_ff_<robot_id>.yaml`:

- the robot entry is the parent's, verbatim (spawn, goal, marker, `loaded`,
  `initial_task`);
- the course is the parent's: `aisle_barrier`, `loop_map`, `static_obstacles`
  and `timed_obstacles` are kept, EXCEPT in the blocker cells
  (`BLOCKER_CELLS`), whose timed and static blockers are stripped too (the
  blocker is the cell's point; free flow means an unobstructed course);
- `family: normal_flow`, `expected_conflict: null`, no `oracle`, no
  `parameters`: a lone robot has no conflict, and the parent's conflict and
  oracle name robots the variant no longer holds (`ScenarioConfig` rejects
  them); `parameters` only annotates the head-on family's generator inputs;
- `duration_sec` is trimmed to `VARIANT_DURATION_SEC` (the Isaac runner reads
  `runtime.duration_sec or duration_sec`; fc_launch's `--duration-sec` is a
  dead flag), with `runtime.duration_sec` cleared.

Nav2 maps rasterize barriers, racks and static obstacles only (timed obstacles
are never baked), and no blocker cell has a static obstacle, so every
variant's occupancy grid equals its parent's (pinned by
`tests/unit/test_free_flow_variants.py`); the VM driver points Nav2 at the
parent's map (`MAP_SCENARIO`), so no new map files are installed.

`manifest.json` beside the variants records, per variant, the parent, its
sha256, the robot, the map to use, the stripped obstacles and the one M5
`initial_tasks` line (no `start_delay_sec`: the table's `own_departure` origin
makes a hold irrelevant, and dropping it keeps the run short), so the VM
driver needs no yaml parsing.

Usage:
    make_free_flow_variants.py            # (re)write every variant + manifest
    make_free_flow_variants.py --check    # exit 1 if any committed file differs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = REPO_ROOT / "isaac" / "config" / "scenarios"
OUT_DIR = SCENARIOS_DIR / "free_flow"
MANIFEST_NAME = "manifest.json"
VARIANT_SUFFIX = "_ff_"
# Solo traversals are ~20-40 sim-s after a ~12-20 sim-s bring-up (the robots
# depart when M5 starts, B2 harvest 2026-10-04: 13.9 sim-s); 120 sim-s leaves
# room for a slow bring-up plus the arrival rule's stay window.
VARIANT_DURATION_SEC = 120.0

# Cells harvested for `free_flow_v1`, in harvest priority order (the v2-scored
# cells first). Paths are relative to SCENARIOS_DIR.
FREE_FLOW_CELLS: dict[str, str] = {
    "head_on_asymmetric_w0p2_eopen_bshort_o0": (
        "family/head_on_asymmetric_w0p2_eopen_bshort_o0.yaml"
    ),
    "t2b_flow_ordering": "t2b_flow_ordering.yaml",
    "bottleneck_merge": "bottleneck_merge.yaml",
    "priority_visual_r1": "priority_visual_r1.yaml",
    "convoy_counterflow_slip": "convoy_counterflow_slip.yaml",
    "intersection_bottleneck": "intersection_bottleneck.yaml",
    "obstacle_in_candidate": "obstacle_in_candidate.yaml",
    "dynamic_anomaly_v2": "dynamic_anomaly_v2.yaml",
}
# The ruling's blocker cells: their blockers are stripped from the variants.
BLOCKER_CELLS: frozenset[str] = frozenset(
    {"obstacle_in_candidate", "dynamic_anomaly_v2", "blocked_path_object", "blocked_path_transient"}
)
# Cells whose baseline another cell's runs supply: identical spawns, goals,
# barrier and map, and the B2-visual load prop is visual-only (no Collision,
# RigidBody or Mass API, `isaac/vgu_sim/load_prop_asset.py`). Verified by
# `tests/unit/test_free_flow_variants.py`.
COVERED_BY: dict[str, str] = {
    "priority_visual_r2": "priority_visual_r1",
    "priority_urgent_r1": "priority_visual_r1",
    "priority_urgent_r2": "priority_visual_r1",
}


def variant_name(cell: str, robot_id: str) -> str:
    """The variant scenario name for one robot of one cell.

    Args:
        cell: The parent scenario name.
        robot_id: The solo robot.

    Returns:
        `<cell>_ff_<robot_id>`.
    """
    return f"{cell}{VARIANT_SUFFIX}{robot_id}"


def file_sha256(path: Path) -> str:
    """Lowercase sha256 hex of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def m5_task_line(robot: dict[str, Any]) -> str:
    """The orchestrator.yaml `initial_tasks` line for a solo robot.

    Args:
        robot: The scenario robot entry.

    Returns:
        A `  robot_N: { task: ..., goal: [x, y] }` line (2-space indented, the
        form `scripts/vm/patch_initial_tasks.py --set` accepts).
    """
    goal = robot["goal"]
    return (
        f"  {robot['robot_id']}: {{ task: {robot['initial_task']}, "
        f"goal: [{float(goal['x'])}, {float(goal['y'])}] }}"
    )


def make_variant(
    cell: str, parent: dict[str, Any], robot_id: str
) -> tuple[dict[str, Any], list[str]]:
    """Build one solo variant from a parent scenario.

    Args:
        cell: The parent scenario name.
        parent: The parent scenario yaml, parsed.
        robot_id: The robot that traverses alone.

    Returns:
        `(variant data, stripped obstacle ids)`.

    Raises:
        ValueError: If the parent's name differs from `cell`, the robot is not
            in the parent, or a non-blocker cell carries timed obstacles (a
            timed event on a free-flow course needs its own ruling).
    """
    if parent.get("name") != cell:
        raise ValueError(f"parent name {parent.get('name')!r} != cell {cell!r}")
    robots = [r for r in parent["robots"] if r["robot_id"] == robot_id]
    if len(robots) != 1:
        raise ValueError(f"{cell}: robot {robot_id!r} not found exactly once")
    timed = list(parent.get("timed_obstacles") or [])
    static = list(parent.get("static_obstacles") or [])
    stripped: list[str] = []
    if cell in BLOCKER_CELLS:
        stripped = [o["obstacle_id"] for o in (*timed, *static)]
        timed, static = [], []
    elif timed:
        raise ValueError(f"{cell}: timed obstacles on a non-blocker cell need a ruling")
    runtime = {k: v for k, v in (parent.get("runtime") or {}).items() if k != "duration_sec"}
    variant: dict[str, Any] = {
        "schema_version": parent["schema_version"],
        "name": variant_name(cell, robot_id),
        "family": "normal_flow",
        "seed": parent["seed"],
        "duration_sec": VARIANT_DURATION_SEC,
        "robots": robots,
        "timed_obstacles": timed,
        "static_obstacles": static,
        "aisle_barrier": parent.get("aisle_barrier"),
        "loop_map": parent.get("loop_map"),
        "expected_conflict": None,
        "runtime": runtime,
    }
    return variant, stripped


def render_variant(variant: dict[str, Any], cell: str, parent_rel: str, parent_sha: str,
                   stripped: list[str]) -> str:
    """The variant's file text: a provenance header plus the yaml body."""
    header = [
        "# GENERATED by scripts/make_free_flow_variants.py -- do not edit by hand.",
        f"# Solo-in-space free-flow variant of `{cell}`.",
        f"# Parent: isaac/config/scenarios/{parent_rel}",
        f"# Parent sha256: {parent_sha}",
        "# prereg-v2 spec, Foundations round adopted, METHOD RULED 2026-10-05: this",
        "# robot traverses the parent's course ALONE; same spawn, goal, barriers and map.",
        f"# Stripped blockers: {', '.join(stripped) if stripped else 'none'}.",
    ]
    body = yaml.safe_dump(variant, sort_keys=False, default_flow_style=False)
    return "\n".join(header) + "\n" + body


def generate(cells: dict[str, str] | None = None) -> dict[str, str]:
    """Render every variant file and the manifest.

    Args:
        cells: Cell name -> parent path relative to SCENARIOS_DIR (default
            `FREE_FLOW_CELLS`).

    Returns:
        File name (inside OUT_DIR) -> text.
    """
    files: dict[str, str] = {}
    manifest: dict[str, Any] = {
        "generator": "scripts/make_free_flow_variants.py",
        "mechanism": "solo_in_space",
        "duration_sec": VARIANT_DURATION_SEC,
        "covered_by": dict(sorted(COVERED_BY.items())),
        "variants": {},
    }
    for cell, rel in (cells or FREE_FLOW_CELLS).items():
        parent_path = SCENARIOS_DIR / rel
        parent = yaml.safe_load(parent_path.read_text(encoding="utf-8"))
        parent_sha = file_sha256(parent_path)
        robot_ids = sorted(
            (r["robot_id"] for r in parent["robots"]), key=lambda rid: int(rid.split("_")[1])
        )
        for robot_id in robot_ids:
            variant, stripped = make_variant(cell, parent, robot_id)
            name = variant["name"]
            files[f"{name}.yaml"] = render_variant(variant, cell, rel, parent_sha, stripped)
            manifest["variants"][name] = {
                "parent": cell,
                "parent_path": f"isaac/config/scenarios/{rel}",
                "parent_sha256": parent_sha,
                "robot_id": robot_id,
                "map_scenario": cell,
                "m5_task_line": m5_task_line(variant["robots"][0]),
                "stripped_obstacles": stripped,
            }
    files[MANIFEST_NAME] = json.dumps(manifest, indent=2) + "\n"
    return files


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="verify the committed files instead of writing them")
    args = parser.parse_args(argv)
    files = generate()
    if args.check:
        stale = sorted(
            name for name, text in files.items()
            if not (OUT_DIR / name).is_file()
            or (OUT_DIR / name).read_text(encoding="utf-8") != text
        )
        extra = sorted(p.name for p in OUT_DIR.glob("*") if p.name not in files)
        for name in stale:
            print(f"STALE {name}", file=sys.stderr)
        for name in extra:
            print(f"EXTRA {name}", file=sys.stderr)
        return 1 if stale or extra else 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (OUT_DIR / name).write_text(text, encoding="utf-8")
    print(f"wrote {len(files) - 1} variants + {MANIFEST_NAME} to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

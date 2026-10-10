"""M1 freshness of one marker while its robot sits at a node, from an episode bundle.

The S1b pilot-1 coverage pass found marker 2 at Wp at 0.874 (one 8.3 s STALE
burst on a static robot); pilot 2 re-checks it on whatever traffic passes Wp.
For every M5 scene-log row (`m5_scene.jsonl`, ~3 Hz), the robot's GT pose at
that sim time (`gt/ground_truth.jsonl`, nearest-later GT row) decides whether
it is within `--radius` of the node; such rows count as fresh unless the
robot is absent from the M1 scene or STALE.

Usage:
    python scripts/s1b_marker_at_node.py <bundle_dir> [--robot robot_2] [--node -2.3,1.35]
        [--radius 0.35]

Prints one JSON object.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
from pathlib import Path


def analyse(bundle: Path, robot: str, node: tuple[float, float], radius: float) -> dict:
    """Freshness of `robot`'s marker overall and while within `radius` of `node`."""
    rows = [json.loads(line) for line in (bundle / "m5_scene.jsonl").open()]
    gt = [json.loads(line) for line in (bundle / "gt" / "ground_truth.jsonl").open()]
    gt_t = [g["sim_time_sec"] for g in gt]
    near = stale_near = stale_all = 0
    for row in rows:
        scene = row["scene"]
        state = next((r for r in scene["robots"] if r["robot_id"] == robot), None)
        stale = state is None or state["status"] == "STALE"
        stale_all += stale
        index = min(bisect.bisect_left(gt_t, scene["stamp"]), len(gt) - 1)
        pose = gt[index]["robots"][robot]
        if math.hypot(pose["x"] - node[0], pose["y"] - node[1]) <= radius:
            near += 1
            stale_near += stale
    return {
        "bundle": bundle.name,
        "robot": robot,
        "node": node,
        "radius_m": radius,
        "rows": len(rows),
        "stale_share_all": round(stale_all / max(len(rows), 1), 4),
        "rows_near_node": near,
        "stale_near_node": stale_near,
        "fresh_near_node": None if not near else round(1 - stale_near / near, 4),
    }


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--robot", default="robot_2")
    ap.add_argument("--node", default="-2.3,1.35")
    ap.add_argument("--radius", type=float, default=0.35)
    args = ap.parse_args()
    node = tuple(float(v) for v in args.node.split(","))
    print(json.dumps(analyse(args.bundle, args.robot, node, args.radius)))


if __name__ == "__main__":
    main()

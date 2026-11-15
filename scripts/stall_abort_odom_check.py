"""Check recorded `/odom` against ground truth for bundles that carry a rosbag.

Report: docs/reports/2026-11-15-m4-stall-abort.md, section 2.2. Read-only;
no VM, no API call.

For each robot whose `/<robot>/odom` is in the bundle's `bag/*.mcap`, the
odometry (spawn-relative, stamped with ROS sim time) is mapped into the world
frame with the robot's first GT pose, and compared with GT at every fifth GT
row for clock offsets 0.00-1.99 s (GT time = ROS sim time - offset). Prints
the offset with the smallest maximum position error, and that error.

Usage (repo root):
    python scripts/stall_abort_odom_check.py <bundle_dir> [...]
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mcap_lite  # noqa: E402


def check(bundle: Path) -> list[str]:
    """One line per robot with odometry in the bundle's bag."""
    bags = sorted((bundle / "bag").glob("*.mcap")) if (bundle / "bag").is_dir() else []
    if not bags:
        return [f"{bundle.name}\tno bag"]
    with (bundle / "gt" / "ground_truth.jsonl").open(encoding="utf-8") as handle:
        gt = [json.loads(line) for line in handle]
    lines = []
    for robot in sorted({r for row in gt for r in row["robots"]}):
        odom = []
        for bag in bags:
            for _topic, _t, payload in mcap_lite.iter_messages(bag, {f"/{robot}/odom"}):
                d = mcap_lite.decode_odometry(payload)
                odom.append((d["stamp"], d["x"], d["y"]))
        if len(odom) < 2:
            continue
        odom.sort()
        stamps = [o[0] for o in odom]
        rows = [(row["sim_time_sec"], row["robots"][robot]) for row in gt if robot in row["robots"]]
        spawn = rows[0][1]
        c, s = math.cos(spawn["theta"]), math.sin(spawn["theta"])

        def odom_at(t: float, stamps=stamps, odom=odom) -> tuple[float, float]:
            i = min(max(bisect.bisect_left(stamps, t), 1), len(odom) - 1)
            a, b = odom[i - 1], odom[i]
            f = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
            return a[1] + f * (b[1] - a[1]), a[2] + f * (b[2] - a[2])

        best = None
        for k in range(200):
            offset = k * 0.01
            errors = []
            for t, pose in rows[::5]:
                if not stamps[0] <= t + offset <= stamps[-1]:
                    continue
                ox, oy = odom_at(t + offset)
                wx, wy = spawn["x"] + c * ox - s * oy, spawn["y"] + s * ox + c * oy
                errors.append(math.hypot(wx - pose["x"], wy - pose["y"]))
            if errors and (best is None or max(errors) < best[1]):
                best = (offset, max(errors), sorted(errors)[len(errors) // 2], len(errors))
        if best is not None:
            lines.append(
                f"{bundle.name}\t{robot}\todom_msgs={len(odom)}\toffset={best[0]:.2f}\t"
                f"max_err_m={best[1]:.4f}\tmedian_err_m={best[2]:.4f}\trows={best[3]}"
            )
    return lines


def main() -> None:
    """Entry point."""
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.is_dir():
            for line in check(path):
                print(line)


if __name__ == "__main__":
    main()

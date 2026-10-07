#!/usr/bin/env python3
"""GT-offset audit: re-derive frozen GT-joined answers with the clock offset applied.

The costmap probe (`docs/reports/2026-10-05-costmap-source-probe.md`, Rev 2)
established that Isaac's `ground_truth.jsonl` `sim_time_sec` runs 0.300 s
behind ROS header stamps: odometry at ROS stamp t equals the GT pose at GT
time t - 0.300 (0.2 mm residual). Any consumer that looks GT up at a ROS stamp
(an M1 scene stamp, a camera-frame stamp, a decision `scene.stamp`) at equal
numeric time therefore reads truth 0.300 s later than intended, and, for
content shown in an M1 frame, a further ~0.15 s later than the frame depicts
(M1's own upstream latency; together the empirical -0.45 s M1-to-GT join
offset of `scripts/rescore_arrivals.py`).

This tool quantifies that bias on frozen artifacts; it changes nothing:

- `battery-v2`: every frozen `manifest_v2.json` item is re-gated and
  re-derived with the frame stamp mapped onto the GT clock by `--shift`
  seconds (0.300 = clock only; 0.45 = clock plus M1 latency, i.e. the
  truth the frame depicts). Reports answer flips and gate drops per item.
- `loop`: `coverage_scene_scores.score_loop`'s `self_detour` compares a GT
  time (loop entry) with a decision `scene.stamp` (ROS); prints both and
  the margin, so a run within the 0.300 s bias is visible.

Usage:
    python3 scripts/gt_offset_audit.py battery-v2 --logs-root data/logs/vm_runs --shift 0.3
    python3 scripts/gt_offset_audit.py loop --run DIR [--run DIR ...]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PERCEPTION_SRC = REPO_ROOT / "ros2_ws" / "src" / "swarm_perception"
for _p in (REPO_ROOT, PERCEPTION_SRC):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from reasoning.vlm.capability_probes import episode_v2 as ep  # noqa: E402

GT_CLOCK_OFFSET_SEC = 0.300
MANIFEST_V1 = REPO_ROOT / "reasoning" / "vlm" / "capability_probes" / "manifest_v1.json"
MANIFEST_V2 = REPO_ROOT / "reasoning" / "vlm" / "capability_probes" / "manifest_v2.json"
CALIBRATION = PERCEPTION_SRC / "config" / "calibration.yaml"


def rederive_item(item: dict, logs_root: Path, shift: float, homography, image_size) -> dict:
    """Re-gate and re-derive one frozen item with its frame stamp shifted onto the GT clock.

    Args:
        item: One `manifest_v2.json` item.
        logs_root: Root the item's `run_id` is relative to.
        shift: Seconds subtracted from the frame stamp before every GT lookup.
        homography: M1's pixel-to-world homography.
        image_size: Calibration image size `(w, h)`.

    Returns:
        `{"item_id", "status", "frozen", "rederived"}`; status is `same`,
        `flipped`, or `dropped:<reason>`.
    """
    episode = ep.load_episode(logs_root / item["run_id"], logs_root)
    if episode.command_windows is not None and shift:
        # Command windows open at decision `scene.stamp`s (ROS clock), so they
        # move onto the GT clock by the clock offset only; onset windows are
        # already GT-derived and stay put.
        episode.command_windows = [
            (a - GT_CLOCK_OFFSET_SEC, b - GT_CLOCK_OFFSET_SEC) for a, b in episode.command_windows
        ]
    frame = ep.find_frame(episode.episode_dir, item["frame_source"], item["frame_ref"])
    shifted = dataclasses.replace(frame, stamp=frame.stamp - shift)
    ctx, reason = ep.gate_frame(episode, shifted, homography, image_size)
    out = {"item_id": item["item_id"], "frozen": item["correct_answer"], "rederived": None}
    if ctx is None:
        out["status"] = f"dropped:{reason}"
        return out
    derived = ep.derive(episode, ctx, item["probe_type"], item["question_key"])
    if isinstance(derived, str):
        out["status"] = f"dropped:{derived}"
        return out
    out["rederived"] = derived.correct_answer
    out["status"] = "same" if derived.correct_answer == item["correct_answer"] else "flipped"
    out["derivation"] = derived.derivation
    return out


def main_battery_v2(args: argparse.Namespace) -> int:
    from swarm_perception.calibration import load_calibration

    calibration = load_calibration(str(CALIBRATION))
    items = json.loads(MANIFEST_V2.read_text(encoding="utf-8"))["items"]
    counts: Counter = Counter()
    rows = []
    for item in items:
        row = rederive_item(item, Path(args.logs_root), args.shift,
                            calibration.homography, calibration.image_size)
        row["probe_type"] = item["probe_type"]
        row["subset"] = item["subset"]
        counts[(item["probe_type"], row["status"].split(":")[0])] += 1
        rows.append(row)
        if row["status"] != "same":
            print(f"{item['item_id']:40s} {row['status']:34s} frozen={row['frozen']} "
                  f"rederived={row['rederived']}")
    print(f"shift={args.shift:+.3f} s over {len(items)} items:")
    for key, value in sorted(counts.items()):
        print(f"  {key[0]:20s} {key[1]:8s} {value}")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return 0


def main_battery_v1(args: argparse.Namespace) -> int:
    """Re-run the v1 manifest auditor with every GT lookup shifted by `--shift`."""
    from reasoning.vlm.capability_probes import scanning
    from reasoning.vlm.capability_probes.manifest_io import load_manifest
    from scripts import audit_capability_probe_manifest as audit

    original = scanning.nearest_gt_row
    scanning.nearest_gt_row = lambda rows, stamp: original(rows, stamp - args.shift)
    try:
        manifest = load_manifest(MANIFEST_V1)
        failures = audit.audit_manifest(manifest, Path(args.logs_root), CALIBRATION)
    finally:
        scanning.nearest_gt_row = original
    answer_flips = {k: [f for f in v if "!= recorded" in f] for k, v in failures.items()}
    answer_flips = {k: v for k, v in answer_flips.items() if v}
    print(f"shift={args.shift:+.3f} s over {len(manifest.items)} v1 items: "
          f"{len(failures)} with any audit failure, {len(answer_flips)} with an answer change")
    for item_id, fails in sorted(failures.items()):
        print(f"  {item_id}: {'; '.join(fails)}")
    return 0


def main_loop(args: argparse.Namespace) -> int:
    from scripts.coverage_scene_scores import (
        LOOP_ENTRY_Y_M,
        first_dispatch,
        load_ground_truth,
    )

    for run in args.run:
        run_dir = Path(run)
        series = load_ground_truth(run_dir / "gt")
        on_loop = next((s for s in series["robot_1"] if s.y > LOOP_ENTRY_Y_M), None)
        decisions = run_dir / "decisions"
        dispatch = first_dispatch(decisions) if decisions.is_dir() else None
        reroute_at = (dispatch["stamp"] if dispatch and dispatch["strategy"] == "reroute"
                      else None)
        entry = None if on_loop is None else on_loop.t
        margin = (None if entry is None or reroute_at is None
                  else round(entry + GT_CLOCK_OFFSET_SEC - reroute_at, 3))
        print(json.dumps({"run": run_dir.name, "entered_loop_gt_sec": entry,
                          "first_dispatch": dispatch,
                          "entry_minus_dispatch_ros_sec": margin,
                          "within_bias": None if margin is None
                          else abs(margin) <= GT_CLOCK_OFFSET_SEC}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("battery-v2")
    b.add_argument("--logs-root", required=True)
    b.add_argument("--shift", type=float, default=GT_CLOCK_OFFSET_SEC)
    b.add_argument("--json")
    b1 = sub.add_parser("battery-v1")
    b1.add_argument("--logs-root", required=True)
    b1.add_argument("--shift", type=float, default=GT_CLOCK_OFFSET_SEC)
    lp = sub.add_parser("loop")
    lp.add_argument("--run", action="append", required=True)
    args = parser.parse_args()
    handlers = {"battery-v2": main_battery_v2, "battery-v1": main_battery_v1, "loop": main_loop}
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())

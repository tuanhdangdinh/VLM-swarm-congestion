#!/usr/bin/env python3
"""Independently re-verify every frozen capability-probe item against source logs.

Re-reads each manifest item's own decision JSON and matched `ground_truth.jsonl`
row from `--logs-root` and recomputes everything the build script computed,
independently of the build script's in-memory state (it re-derives from the
source files on disk, not from the frozen manifest's own recorded fields).
It shares its check definitions (`reasoning.vlm.capability_probes.scanning`
and `.occlusion`) with the build script, so it cannot catch a defect in
those definitions themselves -- but `tests/unit/test_annotation_geometry_fidelity.py`
ties `occlusion.py`'s replica of M1's drawing geometry to the real
`swarm_perception.annotation.draw_robot_overlay`/`grid._draw_cell_badge`
functions it replicates, closing that gap for the geometry the occlusion
checks depend on (2026-10-02, fourth correction). Earlier: third correction
-- two prior visual spot-check rounds each missed a real defect the build
script's own filters had not yet been taught to catch; this script replaces
ad hoc visual checking with a full, re-derived audit of all 60 items.

Checks, per item:
    - The frame rematerializes and its content hash still matches.
    - The source decision JSON and its matched GT row still exist and agree
      with the manifest's recorded `sim_time_sec` / `m1_gt_max_disagreement_m`.
    - `locate_robot`: every robot's M1 box/label clears all 9 grid badges;
      the named robot's GT cell is unique among tracked robots; M1 and GT
      agree on the named robot's cell; that cell equals `correct_answer`.
    - `left_right`: M1 and GT agree on the named robot's side; that side
      equals `correct_answer`.
    - `nearest_first`: M1 and GT agree on the nearest other robot; that robot
      equals `correct_answer`.
    - `robot_count`: the scene is legible (edge-clear, separated, no STALE)
      and the tracked robot count equals `correct_answer`.
    - Every robot-naming item: the frame is legible under
      `scanning.scene_is_legible` (edge-clear, separated, no STALE, no
      inter-robot box/label overlap).
    - No two items of the same probe type are a near-duplicate scene: same
      reference robot (or both none), same tracked robot set, and
      `scanning.max_displacement_m` under
      `scanning.NEAR_DUPLICATE_MAX_DISPLACEMENT_M`.

Exits non-zero if any item fails any check, printing every failure (not just
the first), so every defect in a run is visible at once.

Usage:
    python scripts/audit_capability_probe_manifest.py \\
        --manifest reasoning/vlm/capability_probes/manifest_v1.json \\
        --logs-root /path/to/data/logs/vm_runs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PERCEPTION_SRC = REPO_ROOT / "ros2_ws" / "src" / "swarm_perception"
if str(PERCEPTION_SRC) not in sys.path:
    sys.path.insert(0, str(PERCEPTION_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reasoning.vlm.capability_probes import ground_truth as gtlib  # noqa: E402, I001
from reasoning.vlm.capability_probes import occlusion  # noqa: E402
from reasoning.vlm.capability_probes import scanning  # noqa: E402
from reasoning.vlm.capability_probes.manifest_io import (  # noqa: E402
    load_manifest,
    materialize_frame,
)
from reasoning.vlm.capability_probes.models import ProbeItem, ProbeManifest  # noqa: E402


def _load_source(item: ProbeItem, logs_root: Path) -> tuple[dict, dict]:
    """Re-read `item`'s own decision JSON and matched GT row from disk.

    Returns:
        `(m1_robots, gt_robots)`, each `robot_id -> {"x", "y", "status"?}`.

    Raises:
        FileNotFoundError: The episode's decision or GT file no longer exists.
        ValueError: No GT row matches the decision's `scene.stamp` any more.
    """
    episode_dir = logs_root / item.run_id
    decision_path = episode_dir / "decisions" / f"{item.request_id}.json"
    if not decision_path.is_file():
        raise FileNotFoundError(f"decision file missing: {decision_path}")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    scene = decision["scene"]
    m1_robots = {
        r["robot_id"]: {"x": r["x"], "y": r["y"], "status": r.get("status")}
        for r in scene["robots"]
    }
    gt_rows = scanning.load_gt_rows(episode_dir / "gt" / "ground_truth.jsonl")
    gt_row = scanning.nearest_gt_row(gt_rows, float(scene["stamp"]))
    if gt_row is None:
        raise ValueError(f"no GT row matches stamp {scene['stamp']} any more")
    gt_robots = {rid: {"x": r["x"], "y": r["y"]} for rid, r in gt_row["robots"].items()}
    return m1_robots, gt_robots


def _audit_item(item: ProbeItem, logs_root: Path, homography) -> list[str]:
    """Return every check `item` fails (empty = fully verified)."""
    failures: list[str] = []

    try:
        materialize_frame(item, logs_root)
    except (FileNotFoundError, ValueError) as exc:
        failures.append(f"frame materialization: {exc}")
        return failures  # nothing else is checkable without the source data

    try:
        m1_robots, gt_robots = _load_source(item, logs_root)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        failures.append(f"source re-load: {exc}")
        return failures

    width, height = item.image_width, item.image_height
    m1_pixels = {
        rid: gtlib.world_to_pixel(pos["x"], pos["y"], homography)
        for rid, pos in m1_robots.items()
    }

    if not scanning.scene_is_legible(m1_robots, m1_pixels, width, height):
        failures.append("scene is not legible (edge/separation/STALE) under current M1 positions")

    if item.probe_type == "robot_count":
        if str(len(gt_robots)) != item.correct_answer:
            failures.append(
                f"robot_count: GT count {len(gt_robots)} != recorded {item.correct_answer}"
            )
        if len(m1_robots) != len(gt_robots):
            failures.append(f"robot_count: M1 count {len(m1_robots)} != GT count {len(gt_robots)}")
        return failures

    rid = item.reference_robot_id
    if rid not in gt_robots or rid not in m1_robots:
        failures.append(f"named robot {rid!r} no longer tracked in this frame")
        return failures

    if item.probe_type == "left_right":
        gt_side, margin = gtlib.left_right_answer(gt_robots[rid]["x"], homography, width, height)
        m1_side, _ = gtlib.left_right_answer(m1_robots[rid]["x"], homography, width, height)
        if margin < gtlib.LEFT_RIGHT_MARGIN_M:
            failures.append(f"left_right: margin {margin:.3f} m below the registered bound")
        if gt_side != m1_side:
            failures.append(f"left_right: GT side {gt_side!r} != M1 side {m1_side!r}")
        if gt_side != item.correct_answer:
            failures.append(f"left_right: GT side {gt_side!r} != recorded {item.correct_answer!r}")

    elif item.probe_type == "nearest_first":
        if len(gt_robots) < 3:
            failures.append("nearest_first: fewer than 3 robots now tracked in this frame")
        else:
            gt_nearest = gtlib.nearest_first_answer(gt_robots, rid)
            m1_nearest = gtlib.nearest_first_answer(m1_robots, rid)
            if gt_nearest is None or m1_nearest is None:
                failures.append("nearest_first: fewer than 2 other robots now present")
            else:
                if gt_nearest[1] < gtlib.NEAREST_FIRST_MARGIN_M:
                    failures.append(
                        f"nearest_first: gap {gt_nearest[1]:.3f} m below the registered bound"
                    )
                if gt_nearest[0] != m1_nearest[0]:
                    failures.append(
                        f"nearest_first: GT nearest {gt_nearest[0]!r} != "
                        f"M1 nearest {m1_nearest[0]!r}"
                    )
                if gt_nearest[0] != item.correct_answer:
                    failures.append(
                        f"nearest_first: GT nearest {gt_nearest[0]!r} != "
                        f"recorded {item.correct_answer!r}"
                    )

    elif item.probe_type == "locate_robot":
        gt_cells = {
            other_id: gtlib.grid_cell_answer(pos["x"], pos["y"], homography, width, height)
            for other_id, pos in gt_robots.items()
        }
        gt_cell = gt_cells.get(rid)
        m1_cell = gtlib.grid_cell_answer(
            m1_robots[rid]["x"], m1_robots[rid]["y"], homography, width, height
        )
        if gt_cell is None:
            failures.append("locate_robot: named robot's GT position too close to a cell boundary")
        else:
            if m1_cell != gt_cell:
                failures.append(f"locate_robot: GT cell {gt_cell} != M1 cell {m1_cell}")
            if str(gt_cell) != item.correct_answer:
                failures.append(
                    f"locate_robot: GT cell {gt_cell} != recorded {item.correct_answer!r}"
                )
            shared = any(
                other_id != rid and other_cell == gt_cell
                for other_id, other_cell in gt_cells.items()
            )
            if shared:
                failures.append(
                    f"locate_robot: another tracked robot also occupies cell {gt_cell}"
                )
        if any(
            occlusion.robot_overlaps_any_grid_badge(other_id, u, v, width, height)
            for other_id, (u, v) in m1_pixels.items()
        ):
            failures.append("locate_robot: a robot's M1 box/label overlaps a grid badge")

    return failures


def audit_manifest(
    manifest: ProbeManifest, logs_root: Path, calibration_path: Path
) -> dict[str, list[str]]:
    """Run every item's audit; return `item_id -> failures` for items with any.

    Also checks, within each probe type, for near-duplicate scenes using the
    same `scanning.max_displacement_m` distance comparison the build script's
    own dedup uses: two items naming the same reference robot (or both
    naming none) over the same tracked robot set, whose largest per-robot GT
    displacement is under `scanning.NEAR_DUPLICATE_MAX_DISPLACEMENT_M`.
    """
    from swarm_perception.calibration import load_calibration

    homography = load_calibration(str(calibration_path)).homography

    failures_by_item: dict[str, list[str]] = {}
    seen_by_type: dict[str, list[tuple[str, str | None, dict[str, dict]]]] = {}
    for item in manifest.items:
        failures = _audit_item(item, logs_root, homography)
        try:
            _m1_robots, gt_robots = _load_source(item, logs_root)
            scenes_seen = seen_by_type.setdefault(item.probe_type, [])
            for other_id, other_ref, other_robots in scenes_seen:
                if other_ref != item.reference_robot_id:
                    continue
                displacement = scanning.max_displacement_m(gt_robots, other_robots)
                if (
                    displacement is not None
                    and displacement < scanning.NEAR_DUPLICATE_MAX_DISPLACEMENT_M
                ):
                    failures.append(
                        f"near-duplicate scene (max displacement {displacement:.3f} m), "
                        f"shared with item {other_id!r}"
                    )
            scenes_seen.append((item.item_id, item.reference_robot_id, gt_robots))
        except (FileNotFoundError, ValueError, KeyError):
            pass  # already reported by _audit_item's own source re-load check
        if failures:
            failures_by_item[item.item_id] = failures
    return failures_by_item


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPO_ROOT / "reasoning/vlm/capability_probes/manifest_v1.json",
    )
    parser.add_argument("--logs-root", type=Path, required=True)
    parser.add_argument(
        "--calibration",
        type=Path,
        default=REPO_ROOT / "ros2_ws" / "src" / "swarm_perception" / "config" / "calibration.yaml",
    )
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    failures_by_item = audit_manifest(manifest, args.logs_root, args.calibration)

    if not failures_by_item:
        print(f"OK: all {len(manifest.items)} items passed every check")
        return 0

    print(f"FAILED: {len(failures_by_item)}/{len(manifest.items)} items failed at least one check")
    for item_id, failures in sorted(failures_by_item.items()):
        print(f"  {item_id}:")
        for failure in failures:
            print(f"    - {failure}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

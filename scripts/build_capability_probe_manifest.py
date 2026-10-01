#!/usr/bin/env python3
"""Scan run logs and freeze the capability-probe manifest (prereg-v2 step 10).

Scans `--logs-root` (a `data/logs/vm_runs` tree) for every
`<run>/<episode>/decisions/*.json` alongside a `gt/ground_truth.jsonl`,
matches each decision to the Isaac Sim ground-truth row at its `scene.stamp`,
and -- only where M1's estimate and GT agree within
`ground_truth.M1_GT_MAX_DISAGREEMENT_M` -- derives the GT-correct answer for
whichever of the four probe types the frame supports (a 2-robot frame cannot
support `nearest_first`; a robot near the frame's centre column cannot
support `left_right`; etc.). Item selection is a deterministic, seeded,
balanced sample (`reasoning.vlm.capability_probes.selection`) across the
eligible candidates, never hand-picked and never padded with synthetic items:
a probe type with too few eligible candidates is reported short, not topped
up.

This script makes no VLM backend calls -- it is pure log scanning, GT
arithmetic, and image I/O (reading frame dimensions, writing the grid-overlay
preview for `locate_robot` items is the runner's job, not this script's).

Usage:
    python scripts/build_capability_probe_manifest.py \\
        --logs-root /path/to/data/logs/vm_runs \\
        --calibration ros2_ws/src/swarm_perception/config/calibration.yaml \\
        --out reasoning/vlm/capability_probes/manifest_v1.json \\
        --seed 20261002 --target-per-type 15
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PERCEPTION_SRC = REPO_ROOT / "ros2_ws" / "src" / "swarm_perception"
if str(PERCEPTION_SRC) not in sys.path:
    sys.path.insert(0, str(PERCEPTION_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2  # noqa: E402, I001

from reasoning.vlm.capability_probes import ground_truth as gtlib  # noqa: E402
from reasoning.vlm.capability_probes import occlusion  # noqa: E402
from reasoning.vlm.capability_probes import scanning  # noqa: E402
from reasoning.vlm.capability_probes.grid import GRID_CELL_COUNT  # noqa: E402
from reasoning.vlm.capability_probes.manifest_io import save_manifest, sha256_file  # noqa: E402
from reasoning.vlm.capability_probes.models import ProbeItem, ProbeManifest, ProbeType  # noqa: E402
from reasoning.vlm.capability_probes.selection import balanced_sample  # noqa: E402

_ANNOTATED_SUFFIXES = ("_raw.png", "_stage2.png")


@dataclass
class _Candidate:
    probe_type: ProbeType
    run_id: str
    scenario: str
    request_id: str
    frame_path: Path
    image_width: int
    image_height: int
    sim_time_sec: float
    reference_robot_id: str | None
    question: str
    options: list[str]
    correct_answer: str
    image_choices: bool
    m1_gt_max_disagreement_m: float
    # Scene-configuration fingerprint (reference robot + every robot's
    # GT position, rounded to 5 cm), so two frames of a stalled episode that
    # differ only by a few seconds of simulated time -- same robots, same
    # positions -- cannot both enter the pool as if they were independent
    # evidence (2026-10-02, third correction).
    dedup_key: str


def _question_for(probe_type: ProbeType, reference_robot_id: str | None) -> str:
    if probe_type == "robot_count":
        return (
            "How many ID-labelled robots (each shown with a colored status box "
            "and an ID label above it) are visible in the image?"
        )
    if probe_type == "left_right":
        return (
            f"Looking at the image, is robot {reference_robot_id} positioned in the "
            "left half or the right half of the frame?"
        )
    if probe_type == "nearest_first":
        return f"Which other robot is positioned nearest to robot {reference_robot_id}?"
    if probe_type == "locate_robot":
        return f"Which lettered grid cell is robot {reference_robot_id} in?"
    raise ValueError(f"unknown probe_type {probe_type!r}")


def _annotated_frame_path(frames_dir: Path, request_id: str) -> Path | None:
    candidate = frames_dir / f"{request_id}.png"
    if not candidate.is_file():
        return None
    for suffix in _ANNOTATED_SUFFIXES:
        if candidate.name.endswith(suffix):
            return None
    return candidate


def _scan_episode(
    episode_dir: Path,
    logs_root: Path,
    homography,
    calibration_image_size: tuple[int, int],
    drop_counts: Counter,
) -> list[_Candidate]:
    gt_path = episode_dir / "gt" / "ground_truth.jsonl"
    decisions_dir = episode_dir / "decisions"
    frames_dir = episode_dir / "frames"
    if not (gt_path.is_file() and decisions_dir.is_dir() and frames_dir.is_dir()):
        return []

    manifest_path = episode_dir / "gt" / "run_manifest.json"
    scenario = episode_dir.name
    if manifest_path.is_file():
        try:
            scenario = json.loads(manifest_path.read_text(encoding="utf-8")).get(
                "scenario", scenario
            )
        except (json.JSONDecodeError, OSError):
            pass
    run_id = str(episode_dir.relative_to(logs_root))
    gt_rows = scanning.load_gt_rows(gt_path)

    candidates: list[_Candidate] = []
    for decision_path in sorted(decisions_dir.glob("*.json")):
        try:
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
            scene = decision["scene"]
            request_id = decision["request_id"]
            stamp = float(scene["stamp"])
            m1_robots = {
                r["robot_id"]: {"x": r["x"], "y": r["y"], "status": r.get("status")}
                for r in scene["robots"]
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            drop_counts["unparseable_decision"] += 1
            continue

        gt_row = scanning.nearest_gt_row(gt_rows, stamp)
        if gt_row is None:
            drop_counts["no_matching_gt"] += 1
            continue
        gt_robots = {rid: {"x": r["x"], "y": r["y"]} for rid, r in gt_row["robots"].items()}

        disagreement = gtlib.max_m1_gt_disagreement_m(m1_robots, gt_robots)
        if disagreement > gtlib.M1_GT_MAX_DISAGREEMENT_M:
            drop_counts["m1_gt_disagreement"] += 1
            continue

        frame_path = _annotated_frame_path(frames_dir, request_id)
        if frame_path is None:
            drop_counts["frame_missing"] += 1
            continue

        image = cv2.imread(str(frame_path))
        if image is None:
            drop_counts["frame_missing"] += 1
            continue
        height, width = image.shape[:2]
        if (width, height) != tuple(calibration_image_size):
            drop_counts["calibration_scale_mismatch"] += 1
            continue

        base = dict(
            run_id=run_id,
            scenario=scenario,
            request_id=request_id,
            frame_path=frame_path,
            image_width=width,
            image_height=height,
            sim_time_sec=gt_row["sim_time_sec"],
            m1_gt_max_disagreement_m=disagreement,
        )

        m1_pixels = {
            rid: gtlib.world_to_pixel(pos["x"], pos["y"], homography)
            for rid, pos in m1_robots.items()
        }

        # Gates every probe type from this frame (2026-10-02, third
        # correction): if the frame itself isn't legible, no question about
        # any robot in it is answerable, regardless of which one is asked.
        if not scanning.scene_is_legible(m1_robots, m1_pixels, width, height):
            drop_counts["scene_not_legible"] += 1
            continue

        if 1 <= len(gt_robots) <= 5:
            candidates.append(
                _Candidate(
                    probe_type="robot_count",
                    reference_robot_id=None,
                    question=_question_for("robot_count", None),
                    options=[str(n) for n in range(1, 6)],
                    correct_answer=str(len(gt_robots)),
                    image_choices=False,
                    dedup_key=scanning.dedup_key(None, gt_robots),
                    **base,
                )
            )
        else:
            drop_counts["robot_count_out_of_scope"] += 1

        # Every robot's GT grid cell, so a `locate_robot` candidate can be
        # dropped when another tracked robot shares the same cell: a shared
        # cell makes the item answerable by "point at the cluster" without
        # actually identifying the named robot by its label.
        gt_cells = {
            rid: gtlib.grid_cell_answer(pos["x"], pos["y"], homography, width, height)
            for rid, pos in gt_robots.items()
        }
        # Any robot's M1-drawn box/label colliding with any of the 9 fixed
        # badge positions makes every `locate_robot` item from this frame
        # unanswerable (a badge can sit on a robot other than the one named),
        # so this is checked once per frame, not per candidate.
        any_badge_occluded = any(
            occlusion.robot_overlaps_any_grid_badge(rid, u, v, width, height)
            for rid, (u, v) in m1_pixels.items()
        )

        for robot_id, pos in gt_robots.items():
            side, margin = gtlib.left_right_answer(pos["x"], homography, width, height)
            m1_side, _ = gtlib.left_right_answer(
                m1_robots[robot_id]["x"], homography, width, height
            )
            if margin >= gtlib.LEFT_RIGHT_MARGIN_M and side == m1_side:
                candidates.append(
                    _Candidate(
                        probe_type="left_right",
                        reference_robot_id=robot_id,
                        question=_question_for("left_right", robot_id),
                        options=["left", "right"],
                        correct_answer=side,
                        image_choices=False,
                        dedup_key=scanning.dedup_key(robot_id, gt_robots),
                        **base,
                    )
                )
            elif margin >= gtlib.LEFT_RIGHT_MARGIN_M:
                drop_counts["m1_gt_answer_disagreement"] += 1

            cell = gt_cells[robot_id]
            if cell is None:
                drop_counts["grid_boundary_too_close"] += 1
            elif any_badge_occluded:
                drop_counts["badge_occludes_label"] += 1
            elif any(
                other_id != robot_id and other_cell == cell
                for other_id, other_cell in gt_cells.items()
            ):
                drop_counts["cell_not_unique"] += 1
            else:
                m1_cell = gtlib.grid_cell_answer(
                    m1_robots[robot_id]["x"], m1_robots[robot_id]["y"], homography, width, height
                )
                if m1_cell != cell:
                    drop_counts["m1_gt_answer_disagreement"] += 1
                else:
                    candidates.append(
                        _Candidate(
                            probe_type="locate_robot",
                            reference_robot_id=robot_id,
                            question=_question_for("locate_robot", robot_id),
                            options=[str(i) for i in range(GRID_CELL_COUNT)],
                            correct_answer=str(cell),
                            image_choices=True,
                            dedup_key=scanning.dedup_key(robot_id, gt_robots),
                            **base,
                        )
                    )

            if len(gt_robots) < 3:
                drop_counts["too_few_robots"] += 1
                continue
            nearest = gtlib.nearest_first_answer(gt_robots, robot_id)
            if nearest is None:
                drop_counts["too_few_robots"] += 1
                continue
            nearest_id, gap = nearest
            if gap < gtlib.NEAREST_FIRST_MARGIN_M:
                drop_counts["margin_too_small"] += 1
                continue
            m1_nearest = gtlib.nearest_first_answer(m1_robots, robot_id)
            if m1_nearest is None or m1_nearest[0] != nearest_id:
                drop_counts["m1_gt_answer_disagreement"] += 1
                continue
            others = sorted(rid for rid in gt_robots if rid != robot_id)
            candidates.append(
                _Candidate(
                    probe_type="nearest_first",
                    reference_robot_id=robot_id,
                    question=_question_for("nearest_first", robot_id),
                    options=others,
                    correct_answer=nearest_id,
                    image_choices=False,
                    dedup_key=scanning.dedup_key(robot_id, gt_robots),
                    **base,
                )
            )

    return candidates


def _balance_by_correct_answer(candidate: _Candidate) -> str:
    return candidate.correct_answer


def _balance_by_scene_robot_count(candidate: _Candidate) -> str:
    # nearest_first has no natural "correct answer" axis to balance (the
    # correct robot id is scene-specific); balance by how many robots were in
    # the scene instead, so the item set spans 3-, 4-, and 5-robot scenes
    # rather than whichever happens to be scanned first.
    return str(len(candidate.options) + 1)


def _scene_key(candidate: _Candidate) -> str:
    return candidate.run_id


def _item_seed(manifest_seed: int, item_id: str) -> int:
    digest = hashlib.sha256(f"{manifest_seed}:item:{item_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def build_manifest(
    logs_root: Path,
    calibration_path: Path,
    seed: int,
    target_per_type: int,
    max_per_scene: int,
) -> tuple[ProbeManifest, Counter]:
    """Scan `logs_root` and select a frozen, balanced item set.

    Args:
        logs_root: Root of a `data/logs/vm_runs` tree.
        calibration_path: M1's `calibration.yaml` the dumped frames were
            rendered under.
        seed: Selection and lettering seed.
        target_per_type: Max items to select per probe type.
        max_per_scene: Max items any one run/episode may contribute per type.

    Returns:
        `(manifest, drop_counts)`; `drop_counts` tallies why candidates were
        excluded, for the gap report.
    """
    from swarm_perception.calibration import load_calibration

    calibration = load_calibration(str(calibration_path))
    homography = calibration.homography

    drop_counts: Counter = Counter()
    candidates_by_type: dict[ProbeType, list[_Candidate]] = {
        "robot_count": [],
        "left_right": [],
        "nearest_first": [],
        "locate_robot": [],
    }
    episode_dirs = sorted({p.parent for p in logs_root.rglob("decisions") if p.is_dir()})
    for episode_dir in episode_dirs:
        for candidate in _scan_episode(
            episode_dir, logs_root, homography, calibration.image_size, drop_counts
        ):
            candidates_by_type[candidate.probe_type].append(candidate)

    selected: list[ProbeItem] = []
    for probe_type, candidates in candidates_by_type.items():
        deduped: dict[str, _Candidate] = {}
        duplicates = 0
        for candidate in candidates:
            if candidate.dedup_key in deduped:
                duplicates += 1
            else:
                deduped[candidate.dedup_key] = candidate
        if duplicates:
            drop_counts[f"duplicate_scene_{probe_type}"] += duplicates
        candidates = list(deduped.values())

        balance_key = (
            _balance_by_correct_answer
            if probe_type in ("robot_count", "left_right", "locate_robot")
            else _balance_by_scene_robot_count
        )
        chosen = balanced_sample(
            candidates,
            balance_key=balance_key,
            scene_key=_scene_key,
            target=target_per_type,
            seed=seed,
            max_per_scene=max_per_scene,
        )
        for index, candidate in enumerate(chosen):
            item_id = f"{probe_type}_{index:03d}"
            item_seed = _item_seed(seed, item_id)
            selected.append(
                ProbeItem(
                    item_id=item_id,
                    probe_type=candidate.probe_type,
                    run_id=candidate.run_id,
                    scenario=candidate.scenario,
                    request_id=candidate.request_id,
                    frame_relpath=str(candidate.frame_path.relative_to(logs_root)),
                    frame_sha256=sha256_file(candidate.frame_path),
                    image_width=candidate.image_width,
                    image_height=candidate.image_height,
                    sim_time_sec=candidate.sim_time_sec,
                    reference_robot_id=candidate.reference_robot_id,
                    question=candidate.question,
                    options=candidate.options,
                    correct_answer=candidate.correct_answer,
                    image_choices=candidate.image_choices,
                    seed=item_seed,
                    m1_gt_max_disagreement_m=candidate.m1_gt_max_disagreement_m,
                )
            )

    manifest = ProbeManifest(seed=seed, items=selected)
    return manifest, drop_counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs-root", type=Path, required=True)
    parser.add_argument(
        "--calibration",
        type=Path,
        default=REPO_ROOT / "ros2_ws" / "src" / "swarm_perception" / "config" / "calibration.yaml",
    )
    parser.add_argument(
        "--out", type=Path, default=REPO_ROOT / "reasoning/vlm/capability_probes/manifest_v1.json"
    )
    parser.add_argument("--seed", type=int, default=20261002)
    parser.add_argument("--target-per-type", type=int, default=15)
    parser.add_argument("--max-per-scene", type=int, default=5)
    args = parser.parse_args()

    manifest, drop_counts = build_manifest(
        args.logs_root, args.calibration, args.seed, args.target_per_type, args.max_per_scene
    )
    save_manifest(manifest, args.out)

    by_type: Counter = Counter(item.probe_type for item in manifest.items)
    scenarios_by_type: dict[str, set[str]] = {}
    for item in manifest.items:
        scenarios_by_type.setdefault(item.probe_type, set()).add(item.scenario)

    print(f"wrote {args.out} ({len(manifest.items)} items, seed={args.seed})")
    for probe_type in sorted(by_type):
        n_scenes = len(scenarios_by_type[probe_type])
        short = " SHORT" if by_type[probe_type] < args.target_per_type else ""
        print(f"  {probe_type}: {by_type[probe_type]}/{args.target_per_type} items, "
              f"{n_scenes} scenes{short}")
    if drop_counts:
        print("dropped candidates:")
        for reason, count in sorted(drop_counts.items()):
            print(f"  {reason}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

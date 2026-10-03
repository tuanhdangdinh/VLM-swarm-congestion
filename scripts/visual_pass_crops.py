#!/usr/bin/env python3
"""Per-robot crops and an A/B diff for the B2-visual pass (prereg-v2 step 9).

Evidence tool, offline: reads one or more VM run bundles
(`scripts/vm/v2_final_run.sh` with `SNAPSHOTS=1`: `snapshots/{raw,annotated}_<sim>.png`
plus Isaac ground truth `gt/ground_truth.jsonl`), picks the snapshot nearest
each requested sim time, maps each robot's GT pose to pixels with M1's
calibration homography (`ros2_ws/src/swarm_perception/config/calibration.yaml`,
pixel -> world, inverted here), and writes lossless PNG crops. On every crop it
runs OpenCV's ArUco detector (M1's dictionary) and records whether the robot's
own marker id decodes -- a direct "marker not occluded by the load prop"
check, independent of M1's tracking statistics.

`--ab` builds the loaded-vs-empty comparison: the same robot at the same pose
(its spawn, before departure) in two members, crops side by side plus the
absolute-difference image.

Usage:
    python3 scripts/visual_pass_crops.py crops --run r1:RUN_DIR --run r2:RUN_DIR \\
        --phase spawn:8 --phase standoff:auto --phase goal:end --out OUT_DIR
    python3 scripts/visual_pass_crops.py ab --loaded RUN_DIR --empty RUN_DIR \\
        --robot robot_1 --out OUT_DIR
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION = REPO_ROOT / "ros2_ws/src/swarm_perception/config/calibration.yaml"
ARUCO = REPO_ROOT / "ros2_ws/src/swarm_perception/config/aruco.yaml"
CROP_HALF_PX = 70
_SNAP_RE = re.compile(r"^(raw|annotated)_([\d.]+)\.png$")


def world_to_pixel(x: float, y: float, homography: np.ndarray) -> tuple[int, int]:
    """Map a world-frame point (metres) to pixel `(u, v)` (world-to-pixel)."""
    inv = np.linalg.inv(homography)
    p = inv @ np.array([x, y, 1.0])
    return int(round(p[0] / p[2])), int(round(p[1] / p[2]))


def load_gt(run: Path) -> list[dict]:
    """Isaac ground-truth rows of one run."""
    text = (run / "gt" / "ground_truth.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def snapshots(run: Path, kind: str) -> list[tuple[float, Path]]:
    """`(sim stamp, path)` of one snapshot kind, sorted by stamp."""
    found = []
    for path in (run / "snapshots").glob(f"{kind}_*.png"):
        match = _SNAP_RE.match(path.name)
        if match:
            found.append((float(match.group(2)), path))
    return sorted(found)


def pose_at(rows: list[dict], t: float, robot: str) -> dict:
    """The GT row of `robot` nearest sim time `t`."""
    row = min(rows, key=lambda r: abs(r["sim_time_sec"] - t))
    return {**row["robots"][robot], "t": row["sim_time_sec"]}


def detect_ids(crop: np.ndarray) -> list[int]:
    """ArUco ids decoded in a BGR crop with M1's dictionary."""
    name = yaml.safe_load(ARUCO.read_text())["aruco"]["dictionary"]
    detector = cv2.aruco.ArucoDetector(
        cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, name)),
        cv2.aruco.DetectorParameters(),
    )
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    big = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    _corners, ids, _rej = detector.detectMarkers(big)
    return [] if ids is None else sorted(int(i) for i in ids.flatten())


def crop_at(image: np.ndarray, u: int, v: int) -> np.ndarray:
    """A square crop centred on `(u, v)`, clipped to the image."""
    h, w = image.shape[:2]
    return image[max(0, v - CROP_HALF_PX):min(h, v + CROP_HALF_PX),
                 max(0, u - CROP_HALF_PX):min(w, u + CROP_HALF_PX)]


def _homography() -> np.ndarray:
    return np.array(yaml.safe_load(CALIBRATION.read_text())["homography"], dtype=float)


def _phase_time(spec: str, rows: list[dict], snaps: list[tuple[float, Path]]) -> float:
    if spec == "end":
        return snaps[-1][0]
    if spec == "auto":
        # The standoff: the first instant after departure where every robot is
        # slower than 0.02 m/s and the pair is within 1.0 m.
        moved = False
        for row in rows:
            robots = list(row["robots"].values())
            moved = moved or any(r["speed_mps"] > 0.03 for r in robots)
            if moved and len(robots) >= 2 and all(r["speed_mps"] < 0.02 for r in robots):
                a, b = robots[:2]
                if np.hypot(a["x"] - b["x"], a["y"] - b["y"]) < 1.0:
                    return row["sim_time_sec"]
        return snaps[len(snaps) // 2][0]
    return float(spec)


def cmd_crops(args: argparse.Namespace) -> int:
    hom = _homography()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = []
    for item in args.run:
        member, _, run_dir = item.partition(":")
        run = Path(run_dir)
        rows = load_gt(run)
        for phase in args.phase:
            name, _, spec = phase.partition(":")
            for kind in ("raw", "annotated"):
                snaps = snapshots(run, kind)
                if not snaps:
                    continue
                t = _phase_time(spec, rows, snaps)
                stamp, path = min(snaps, key=lambda s: abs(s[0] - t))
                image = cv2.imread(str(path))
                for robot in sorted(rows[0]["robots"]):
                    pose = pose_at(rows, stamp, robot)
                    u, v = world_to_pixel(pose["x"], pose["y"], hom)
                    crop = crop_at(image, u, v)
                    file = out / f"{member}_{name}_{robot}_{kind}_{stamp:.1f}.png"
                    cv2.imwrite(str(file), crop)
                    report.append({
                        "member": member, "phase": name, "kind": kind, "robot": robot,
                        "snapshot_sim": stamp, "gt": {k: round(pose[k], 3) for k in ("x", "y")},
                        "speed_mps": round(pose["speed_mps"], 3), "pixel": [u, v],
                        "aruco_ids": detect_ids(crop), "file": file.name,
                    })
    (out / "crops.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for r in report:
        print(f"{r['member']} {r['phase']:8s} {r['kind']:9s} {r['robot']} "
              f"t={r['snapshot_sim']:.1f} gt=({r['gt']['x']},{r['gt']['y']}) "
              f"v={r['speed_mps']} ids={r['aruco_ids']}")
    return 0


def cmd_ab(args: argparse.Namespace) -> int:
    hom = _homography()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    crops = {}
    meta = {}
    for label, run_dir in (("loaded", args.loaded), ("empty", args.empty)):
        run = Path(run_dir)
        rows = load_gt(run)
        snaps = snapshots(run, "raw")
        # Before departure: the robot sits at its spawn, the same pose in both
        # members (byte-identical geometry).
        still = [s for s in snaps
                 if pose_at(rows, s[0], args.robot)["speed_mps"] < 0.005
                 and all(r["robots"][args.robot]["speed_mps"] < 0.005
                         for r in rows if r["sim_time_sec"] <= s[0])]
        stamp, path = (still or snaps)[len(still or snaps) // 2 if still else 0]
        pose = pose_at(rows, stamp, args.robot)
        u, v = world_to_pixel(pose["x"], pose["y"], hom)
        crops[label] = crop_at(cv2.imread(str(path)), u, v)
        meta[label] = {"snapshot_sim": stamp, "gt": [round(pose["x"], 3), round(pose["y"], 3)],
                       "pixel": [u, v], "aruco_ids": detect_ids(crops[label])}
    h = min(c.shape[0] for c in crops.values())
    w = min(c.shape[1] for c in crops.values())
    a, b = crops["loaded"][:h, :w], crops["empty"][:h, :w]
    diff = cv2.absdiff(a, b)
    cv2.imwrite(str(out / f"ab_{args.robot}_loaded.png"), a)
    cv2.imwrite(str(out / f"ab_{args.robot}_empty.png"), b)
    cv2.imwrite(str(out / f"ab_{args.robot}_absdiff.png"), diff)
    cv2.imwrite(str(out / f"ab_{args.robot}_side_by_side.png"), np.hstack([a, b, diff]))
    # Per-pixel max over channels: the brown prop on the grey floor differs
    # mostly in hue, not luminance. The marker window is the centre square
    # (the 0.12 m marker is ~28 px across at this scale): near-zero there
    # means the load prop changed nothing on the marker itself.
    chan = diff.max(axis=2)
    cy, cx, r = h // 2, w // 2, 14
    marker = chan[cy - r:cy + r, cx - r:cx + r]
    meta["diff"] = {"mean_abs_maxchan": round(float(chan.mean()), 2),
                    "pixels_over_30": int((chan > 30).sum()),
                    "marker_window_mean_abs": round(float(marker.mean()), 2),
                    "marker_window_pixels_over_30": int((marker > 30).sum()),
                    "crop_px": [h, w]}
    (out / f"ab_{args.robot}.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    crops = sub.add_parser("crops")
    crops.add_argument("--run", action="append", required=True)
    crops.add_argument("--phase", action="append", required=True)
    crops.add_argument("--out", required=True)
    crops.set_defaults(func=cmd_crops)
    ab = sub.add_parser("ab")
    ab.add_argument("--loaded", required=True)
    ab.add_argument("--empty", required=True)
    ab.add_argument("--robot", default="robot_1")
    ab.add_argument("--out", required=True)
    ab.set_defaults(func=cmd_ab)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

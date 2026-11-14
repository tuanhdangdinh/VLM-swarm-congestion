"""Offline prototype for the improved-annotation scope (2026-11-14). No model calls.

Measures legibility of the 24 head-on standoff frames and renders the proposed
image variants for a few example scenes:

* ``L1`` - fixed crop of the existing annotated frame to the corridor band,
  upscaled 1.6x (Lanczos). Same crop box for every scene.
* ``L2`` - the existing annotated frame with the old 1-px red labels removed
  (inpainted from the surrounding floor) and redrawn as large white-on-black
  label panels pushed apart horizontally, boxes thickened, then the L1
  crop/upscale. Label placement uses only the robot poses in the scene state.
* ``L2raw`` - the same overlay drawn on the raw frame (batch-2 scenes only),
  to check that post-processing and re-drawing from raw give the same picture.
* ``K1`` - L2 plus the declared static obstacle (M5's ``static_obstacles``
  config, i.e. system geometry) outlined and labelled ``obstacle_1``.

Type L variants must change no pixel outside the robots' label/box zone
before the crop; the script asserts that.

Usage (from the repo root of the worktree):

    python data/experiments/2026-11-14-improved-annotation-scope/render_variants.py \
        --runs-dir <main checkout>/data/logs/vm_runs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
for _extra in (REPO_ROOT, REPO_ROOT / "scripts", REPO_ROOT / "ros2_ws/src/swarm_perception"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from swarm_perception.geometry import world_to_pixel  # noqa: E402

import replay_live_decisions as L  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
CALIBRATION = REPO_ROOT / "ros2_ws/src/swarm_perception/config/calibration.yaml"

ORIGINAL_12 = (
    "20260925_063520", "20260925_065143", "20260925_070637",
    "20260925_072130", "20260925_073621", "20260925_075116",
    "20260925_155433", "20260925_160951", "20260925_162451",
    "20260925_163949", "20260925_165442", "20260925_170938",
)
# First positive analysis of the ER-2 live runs of the same two scenario cells
# (2026-09-25); SHA-verified with prompt v1 and obstacle text on.
EXTRA_12 = (
    "20260925_124609", "20260925_130115", "20260925_132335",
    "20260925_133841", "20260925_135334", "20260925_140824",
    "20260925_183343", "20260925_184840", "20260925_190322",
    "20260925_191810", "20260925_193307", "20260925_194800",
)
EXAMPLES = ("810c9104", "189ae2a6", "53264de9")  # west+raw, east+raw, west no raw

# Fixed for every scene: the corridor band, both corridor ends included.
CROP_BOX = (0, 280, 1280, 680)  # (u0, v0, u1, v1)
UPSCALE = 1.6
BOX_HALF_PX = 20  # annotation.py draw_robot_overlay
STOPPED_RED = (200, 0, 0)
CAMERA_HEIGHT_M = 3.0
MARKER_PLANE_M = 0.21
LABEL_SCALE = 0.7
LABEL_THICK = 2
LABEL_PAD = 4
LABEL_LIFT_PX = 6  # panel bottom sits this far above the box top (clear of the barrier)
LABEL_PUSH_PX = 45  # each panel is pushed this far away from the pair's midpoint


def load_homography() -> np.ndarray:
    return np.asarray(yaml.safe_load(CALIBRATION.read_text())["homography"], dtype=float)


def first_standoff(runs: tuple[str, ...], runs_dir: Path) -> list[L.Artifact]:
    """First SHA-verified genuine standoff per run, by the September selector.

    `load_artifacts` returns each run's artifacts in M5 log order, and
    `select_standoff_artifacts` is the rule the 12 replay stimuli came from.
    """
    matched = L.check_integrity(L.load_artifacts(runs, runs_dir)).matched
    out: dict[str, L.Artifact] = {}
    for a in L.select_standoff_artifacts(matched):
        out.setdefault(a.image_path.parent.parent.name, a)
    return [out[r] for r in runs if r in out]


def robot_pixels(a: L.Artifact, H: np.ndarray) -> dict[str, tuple[int, int]]:
    return {r["robot_id"]: world_to_pixel((r["x"], r["y"]), H) for r in a.scene["robots"]}


def red_mask(img: np.ndarray) -> np.ndarray:
    return (img[:, :, 0] > 110) & (img[:, :, 1] < 80) & (img[:, :, 2] < 80)


def rel_luminance(rgb: np.ndarray) -> float:
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


def contrast(a_rgb, b_rgb) -> float:
    la, lb = sorted((rel_luminance(a_rgb), rel_luminance(b_rgb)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def measure(a: L.Artifact, H: np.ndarray) -> dict:
    img = np.asarray(Image.open(a.image_path).convert("RGB")).astype(np.int32)
    px = robot_pixels(a, H)
    red = red_mask(img)
    top = min(v for _, v in px.values()) - BOX_HALF_PX - 2
    ys, xs = np.nonzero(red[: top + 1])
    label_rows = (int(ys.min()), int(ys.max())) if len(ys) else None
    # x-height: the 'o' of the leftmost label, columns 9..16 px after its start
    left = min(px.values())
    u0 = left[0] - BOX_HALF_PX
    sub = red[: top + 1, u0 + 9 : u0 + 16]
    oy = np.nonzero(sub.any(axis=1))[0]
    # label extents: per robot, label starts at cx-20 and is ~55 px wide (scale 0.5)
    starts = sorted(u - BOX_HALF_PX for u, _ in px.values())
    gap = starts[1] - (starts[0] + 55)
    floor = np.median(img[top - 30 : top - 16, 560:720].reshape(-1, 3), axis=0)
    band = img[400:560]
    light = (band.min(axis=2) > 120) & (np.ptp(band, axis=2) < 12)
    light[:, 520:760] = False  # the robots' white ArUco markers
    ly, lx = np.nonzero(light)
    obst = (int(lx.min()), int(lx.max()), int(ly.min()) + 400, int(ly.max()) + 400)
    obst_rgb = np.median(img[obst[2] : obst[3] + 1, obst[0] : obst[1] + 1].reshape(-1, 3), axis=0)
    corr = np.median(img[470:490, 420:520].reshape(-1, 3), axis=0)
    marker_wh = []
    for cx, cy in px.values():
        win = img[cy - 22 : cy + 23, cx - 22 : cx + 23]
        wy, wx = np.nonzero(win.min(axis=2) > 170)
        marker_wh.append((int(wx.max() - wx.min() + 1), int(wy.max() - wy.min() + 1)))
    centres = sorted(u for u, _ in px.values())
    near = obst[1] if obst[1] < 640 else obst[0]
    dist = min(abs(near - c) for c in centres)
    return {
        "request": a.request_id[:8],
        "side": a.obstacle_side,
        "raw": a.raw_image_path.is_file(),
        "robot_px": {k: list(v) for k, v in sorted(px.items())},
        "robot_sep_px": centres[1] - centres[0],
        "marker_white_wh_px": marker_wh,
        "label_rows": label_rows,
        "label_strip_h": (label_rows[1] - label_rows[0] + 1) if label_rows else None,
        "x_height_px": int(oy.max() - oy.min() + 1) if len(oy) else None,
        "label_gap_px": gap,
        "label_floor_rgb": floor.tolist(),
        "label_contrast": round(contrast(STOPPED_RED, floor), 2),
        "obstacle_top_bbox": obst,
        "obstacle_top_wh": (obst[1] - obst[0] + 1, obst[3] - obst[2] + 1),
        "obstacle_rgb": obst_rgb.tolist(),
        "corridor_rgb": corr.tolist(),
        "obstacle_contrast": round(contrast(obst_rgb, corr), 2),
        "near_robot_to_obstacle_px": dist,
    }


def _crop_up(img: np.ndarray) -> np.ndarray:
    u0, v0, u1, v1 = CROP_BOX
    pil = Image.fromarray(img[v0:v1, u0:u1].astype(np.uint8))
    w, h = pil.size
    return np.asarray(pil.resize((round(w * UPSCALE), round(h * UPSCALE)), Image.LANCZOS))


def _remove_old_labels(img: np.ndarray, px: dict[str, tuple[int, int]]) -> np.ndarray:
    # Old label of each robot: drawn at (cx-20, cy-25) baseline, ~55 x 14 px.
    mask = np.zeros(img.shape[:2], np.uint8)
    zone = np.zeros_like(mask)
    for cx, cy in px.values():
        zone[cy - BOX_HALF_PX - 22 : cy - BOX_HALF_PX - 1, cx - BOX_HALF_PX - 2 : cx + 40] = 1
    mask[(red_mask(img) & zone.astype(bool))] = 255
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    bgr = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2BGR)
    out = cv2.inpaint(bgr, mask, 3, cv2.INPAINT_TELEA)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def draw_legible(img: np.ndarray, px: dict[str, tuple[int, int]]) -> np.ndarray:
    """Thicker boxes and large non-overlapping label panels (state-derived only)."""
    out = img.copy()
    mid = sum(u for u, _ in px.values()) / len(px)
    font = cv2.FONT_HERSHEY_SIMPLEX
    for rid, (cx, cy) in sorted(px.items()):
        cv2.rectangle(out, (cx - BOX_HALF_PX - 1, cy - BOX_HALF_PX - 1),
                      (cx + BOX_HALF_PX + 1, cy + BOX_HALF_PX + 1), STOPPED_RED, 3)
        (tw, th), base = cv2.getTextSize(rid, font, LABEL_SCALE, LABEL_THICK)
        direction = -1 if cx < mid else 1
        pcx = cx + direction * LABEL_PUSH_PX
        x0 = int(pcx - tw / 2 - LABEL_PAD)
        y1 = cy - BOX_HALF_PX - LABEL_LIFT_PX
        y0 = y1 - th - base - 2 * LABEL_PAD
        x1 = x0 + tw + 2 * LABEL_PAD
        cv2.line(out, (int(pcx), y1), (cx, cy - BOX_HALF_PX - 2), (255, 255, 255), 2, cv2.LINE_AA)
        cv2.rectangle(out, (x0, y0), (x1, y1), (0, 0, 0), -1)
        cv2.rectangle(out, (x0, y0), (x1, y1), STOPPED_RED, 2)
        cv2.putText(out, rid, (x0 + LABEL_PAD, y1 - LABEL_PAD - base), font,
                    LABEL_SCALE, (255, 255, 255), LABEL_THICK, cv2.LINE_AA)
    return out


def ground_to_marker_plane(x: float, y: float) -> tuple[float, float]:
    """Map a z=0 world point to the marker-plane point that images onto the same pixel.

    The calibration homography is for the marker plane (z = 0.21 m); the camera
    sits 3.0 m above the world origin (M5 `scenario_geometry.camera`), so a
    ground point appears at the plane point scaled by (3.0 - 0.21) / 3.0.
    """
    scale = (CAMERA_HEIGHT_M - MARKER_PLANE_M) / CAMERA_HEIGHT_M
    return x * scale, y * scale


def draw_obstacles(img: np.ndarray, a: L.Artifact, H: np.ndarray) -> np.ndarray:
    """Type K: outline + label the declared static obstacles' ground footprint.

    `StaticObstacleInput` carries no height, so the system can place only the
    footprint, not the top face the camera sees.
    """
    out = img.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    for ob in a.static_obstacles:
        hx, hy = ob.size_x_m / 2, ob.size_y_m / 2
        corners = [world_to_pixel(ground_to_marker_plane(ob.x + dx, ob.y + dy), H)
                   for dx, dy in ((-hx, hy), (hx, hy), (hx, -hy), (-hx, -hy))]
        cv2.polylines(out, [np.asarray(corners, np.int32)], True, (0, 255, 255), 3, cv2.LINE_AA)
        u = min(c[0] for c in corners)
        v = max(c[1] for c in corners) + 30
        cv2.putText(out, ob.obstacle_id, (u, v), font, LABEL_SCALE, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(out, ob.obstacle_id, (u, v), font, LABEL_SCALE, (0, 255, 255), 2, cv2.LINE_AA)
    return out


def change_zone_ok(before: np.ndarray, after: np.ndarray, px: dict[str, tuple[int, int]]) -> tuple:
    """Every changed pixel must lie in the robots' label/box zone (Type L check)."""
    diff = np.abs(before.astype(int) - after.astype(int)).sum(axis=2) > 0
    ys, xs = np.nonzero(diff)
    us = [u for u, _ in px.values()]
    vs = [v for _, v in px.values()]
    zone = (min(us) - 160, max(us) + 160, min(vs) - 110, max(vs) + BOX_HALF_PX + 5)
    inside = (xs >= zone[0]) & (xs <= zone[1]) & (ys >= zone[2]) & (ys <= zone[3])
    bbox = (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())) if len(xs) else None
    return bool(inside.all()), int(diff.sum()), bbox, zone


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", type=Path, required=True)
    args = parser.parse_args()
    H = load_homography()
    scenes = first_standoff(ORIGINAL_12, args.runs_dir) + first_standoff(EXTRA_12, args.runs_dir)
    rows = [measure(a, H) | {"set": "original" if i < 12 else "extra"} for i, a in enumerate(scenes)]
    (OUT_DIR / "measurements.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(json.dumps(r))
    checks = []
    for a in scenes:
        key = a.request_id[:8]
        px = robot_pixels(a, H)
        ann = np.asarray(Image.open(a.image_path).convert("RGB"))
        l2_full = draw_legible(_remove_old_labels(ann, px), px)
        ok, n, bbox, zone = change_zone_ok(ann, l2_full, px)
        cleaned = red_mask(_remove_old_labels(ann, px))
        leftover = sum(int(cleaned[cy - BOX_HALF_PX - 22 : cy - BOX_HALF_PX - 1,
                                   cx - BOX_HALF_PX + 2 : cx + 40].sum())
                       for cx, cy in px.values())
        checks.append({"request": key, "L2_changes_only_in_robot_zone": ok,
                       "old_label_red_px_left": leftover,
                       "changed_px": n, "changed_bbox": bbox, "zone": zone})
        if key not in EXAMPLES:
            continue
        k1_full = draw_obstacles(l2_full, a, H)
        Image.fromarray(_crop_up(ann)).save(OUT_DIR / f"{key}_L1.png")
        Image.fromarray(_crop_up(l2_full)).save(OUT_DIR / f"{key}_L2.png")
        Image.fromarray(_crop_up(k1_full)).save(OUT_DIR / f"{key}_K1.png")
        if a.raw_image_path.is_file():
            raw = np.asarray(Image.open(a.raw_image_path).convert("RGB"))
            l2_raw = draw_legible(raw, px)
            Image.fromarray(_crop_up(l2_raw)).save(OUT_DIR / f"{key}_L2raw.png")
            d = np.abs(l2_raw.astype(int) - l2_full.astype(int)).sum(axis=2)
            checks[-1]["L2raw_vs_L2_mean_abs_diff"] = round(float(d.mean()), 3)
            checks[-1]["L2raw_vs_L2_px_diff_gt30"] = int((d > 30).sum())
            checks[-1]["raw_vs_ann_px_diff_gt30"] = int(
                (np.abs(raw.astype(int) - ann.astype(int)).sum(axis=2) > 30).sum())
    (OUT_DIR / "type_l_checks.json").write_text(json.dumps(checks, indent=1))
    for c in checks:
        print(json.dumps(c))
    assert all(c["L2_changes_only_in_robot_zone"] for c in checks), "Type L check failed"


if __name__ == "__main__":
    main()

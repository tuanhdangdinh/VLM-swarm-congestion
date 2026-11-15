"""Render the improved-annotation replay stimuli (offline; no model calls).

Promoted from the scope prototype
`data/experiments/2026-11-14-improved-annotation-scope/render_variants.py`, with the
same geometry and drawing constants. Pre-registered in
docs/superpowers/specs/2026-11-14-improved-annotation-replay-design.md.

Image variants per scene:

* ``C_ref`` - the annotated frame M2 received live, unchanged (1280 x 960).
* ``grey`` - one neutral mid-grey PNG of the frame size, for ``D_ref``.
* ``L2`` (Type L) - the annotated frame with the 1-px red labels inpainted away and
  redrawn as large white-on-black panels pushed apart, boxes thickened, then a
  fixed crop (u 0-1280, v 280-680) upscaled 1.6x to 2048 x 640. Label placement
  uses only the robot poses M1 already publishes; no fact is added.
* ``K1`` (Type K) - L2 plus the declared static obstacle's ground footprint
  (M5 ``static_obstacles``) outlined in cyan and labelled ``obstacle_1``, then
  the same crop. The config holds no obstacle height, so the outline lands on
  the box's shaded side face and base, not on its bright top face.

Usage:

    python scripts/render_annotation_variants.py --runs-dir <main>/data/logs/vm_runs
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
for _extra in (REPO_ROOT, REPO_ROOT / "ros2_ws/src/swarm_perception"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from swarm_perception.geometry import world_to_pixel  # noqa: E402

from scripts.replay_live_decisions import (  # noqa: E402
    Artifact,
    check_integrity,
    load_artifacts,
    select_standoff_artifacts,
)

OUT_DIR = REPO_ROOT / "data/experiments/2026-11-14-improved-annotation-replay"
CALIBRATION = REPO_ROOT / "ros2_ws/src/swarm_perception/config/calibration.yaml"

ORIGINAL_12: tuple[str, ...] = (
    "20260925_063520",
    "20260925_065143",
    "20260925_070637",
    "20260925_072130",
    "20260925_073621",
    "20260925_075116",
    "20260925_155433",
    "20260925_160951",
    "20260925_162451",
    "20260925_163949",
    "20260925_165442",
    "20260925_170938",
)
# ER-2 live runs of the same two scenario cells (2026-09-25), prompt v1, text on.
# `20260925_181526` is excluded (its live decision failed to parse; scope Rev 2).
EXTRA_12: tuple[str, ...] = (
    "20260925_124609",
    "20260925_130115",
    "20260925_132335",
    "20260925_133841",
    "20260925_135334",
    "20260925_140824",
    "20260925_183343",
    "20260925_184840",
    "20260925_190322",
    "20260925_191810",
    "20260925_193307",
    "20260925_194800",
)
EXPECTED_SCENES: tuple[str, ...] = (
    "53264de9",
    "5e7b5a59",
    "2c3fbfa5",
    "61119197",
    "d053d0dc",
    "3120c65f",
    "810c9104",
    "42fb0cb8",
    "d4b96fbd",
    "189ae2a6",
    "e4b1bd03",
    "618a9f29",
    "710c40e5",
    "7b0fbf9e",
    "ea126abd",
    "bb48067c",
    "d592a820",
    "32aec602",
    "bc56a57a",
    "920ec0d9",
    "8027a8a2",
    "41d72639",
    "653be8f3",
    "f94cb7ed",
)

# Fixed for every scene: the corridor band with both corridor ends in view.
CROP_BOX = (0, 280, 1280, 680)  # (u0, v0, u1, v1)
UPSCALE = 1.6
BOX_HALF_PX = 20  # annotation.py draw_robot_overlay
STOPPED_RED = (200, 0, 0)
# annotation.py _STATUS_COLORS for STOPPED, SLOW, MOVING (STALE grey is not
# separable from the floor and does not occur in the 24 scenes).
STATUS_COLOURS: tuple[tuple[int, int, int], ...] = ((200, 0, 0), (200, 200, 0), (0, 200, 0))
CAMERA_HEIGHT_M = 3.0
MARKER_PLANE_M = 0.21
LABEL_SCALE = 0.7
LABEL_THICK = 2
LABEL_PAD = 4
LABEL_LIFT_PX = 6  # panel bottom sits this far above the box top (clear of the barrier)
LABEL_PUSH_PX = 45  # each panel is pushed this far away from the pair's midpoint
ZONE_U_PX = 160  # Type L change zone: robot u +- this
ZONE_ABOVE_PX = 110  # and from this far above the robots ...
K1_OUTLINE_THICK = 3
K1_COLOUR = (0, 255, 255)
GREY_VALUE = 128


def load_homography(path: Path = CALIBRATION) -> np.ndarray:
    """Load the marker-plane homography (world metres to pixels).

    Args:
        path: The M1 calibration YAML.

    Returns:
        The 3 x 3 world-to-pixel homography.
    """
    return np.asarray(yaml.safe_load(path.read_text())["homography"], dtype=float)


def first_standoffs(runs: tuple[str, ...], runs_dir: Path) -> list[Artifact]:
    """Return the first SHA-verified genuine standoff of each run, in run order.

    Args:
        runs: Run folder names.
        runs_dir: Directory holding the run folders.

    Returns:
        One artifact per run that has a standoff.
    """
    matched = check_integrity(load_artifacts(runs, runs_dir)).matched
    out: dict[str, Artifact] = {}
    for artifact in select_standoff_artifacts(matched):
        out.setdefault(artifact.image_path.parent.parent.name, artifact)
    return [out[r] for r in runs if r in out]


def load_scenes(runs_dir: Path) -> list[Artifact]:
    """Load the 24 pre-registered scenes and assert the facts scoring relies on.

    Raises:
        RuntimeError: If the scene set, the prompt version, the side balance or
            the west/east identity of `robot_1`/`robot_2` differs from the design.
    """
    scenes = first_standoffs(ORIGINAL_12, runs_dir) + first_standoffs(EXTRA_12, runs_dir)
    prefixes = tuple(a.request_id[:8] for a in scenes)
    if prefixes != EXPECTED_SCENES:
        raise RuntimeError(f"scene set differs from the design: {prefixes}")
    for a in scenes:
        if a.prompt_version != 1 or a.failure_context or a.last_failed_context or a.plan_state:
            raise RuntimeError(f"{a.request_id}: not a plain prompt-v1 artifact")
        xs = {r["robot_id"]: r["x"] for r in a.scene["robots"]}
        if set(xs) != {"robot_1", "robot_2"} or not xs["robot_1"] < xs["robot_2"]:
            raise RuntimeError(f"{a.request_id}: robot_1 is not the west robot")
        if not a.image_path.is_file():
            raise RuntimeError(f"{a.request_id}: annotated frame missing")
    sides = [a.obstacle_side for a in scenes]
    if sides.count("west") != 12 or sides.count("east") != 12:
        raise RuntimeError(f"side balance differs: {sides}")
    return scenes


def robot_pixels(artifact: Artifact, homography: np.ndarray) -> dict[str, tuple[int, int]]:
    """Map each robot's world position to its pixel `(u, v)` (marker plane)."""
    return {
        r["robot_id"]: world_to_pixel((r["x"], r["y"]), homography)
        for r in artifact.scene["robots"]
    }


def red_mask(img: np.ndarray) -> np.ndarray:
    """Pixels drawn in the overlay's STOPPED red (tolerant of anti-aliasing)."""
    return colour_mask(img, STOPPED_RED)


def colour_mask(img: np.ndarray, colour: tuple[int, int, int]) -> np.ndarray:
    """Pixels drawn in one saturated overlay colour (each channel 200 or 0).

    Args:
        img: RGB image.
        colour: One of the M1 status colours whose channels are 200 or 0.

    Returns:
        Boolean mask, tolerant of anti-aliasing.
    """
    mask = np.ones(img.shape[:2], dtype=bool)
    for channel, value in enumerate(colour):
        mask &= img[:, :, channel] > 110 if value == 200 else img[:, :, channel] < 80
    return mask


def overlay_colours(
    img: np.ndarray, px: dict[str, tuple[int, int]]
) -> dict[str, tuple[int, int, int]]:
    """Read each robot's overlay colour (its M1 status colour) from its box edges.

    M1 colours each box by the status it held when it drew the frame, which can
    differ from the M5 snapshot's status (scene `61119197`: robot_1 drawn SLOW
    yellow, snapshot STOPPED). L2 keeps the frame's colour so it adds nothing.

    Raises:
        ValueError: If a box edge matches no saturated status colour.
    """
    out = {}
    for rid, (cx, cy) in px.items():
        edges = np.concatenate(
            [
                img[
                    cy - BOX_HALF_PX : cy - BOX_HALF_PX + 1, cx - BOX_HALF_PX : cx + BOX_HALF_PX + 1
                ],
                img[
                    cy + BOX_HALF_PX : cy + BOX_HALF_PX + 1, cx - BOX_HALF_PX : cx + BOX_HALF_PX + 1
                ],
            ],
            axis=1,
        )
        counts = {c: int(colour_mask(edges, c).sum()) for c in STATUS_COLOURS}
        best = max(counts, key=counts.get)
        if counts[best] < 40:
            raise ValueError(f"{rid}: no status colour on its box edges ({counts})")
        out[rid] = best
    return out


def crop_upscale(img: np.ndarray) -> np.ndarray:
    """Apply the fixed corridor-band crop and the Lanczos 1.6x upscale.

    Args:
        img: Full 1280 x 960 RGB frame.

    Returns:
        The 2048 x 640 RGB image.
    """
    u0, v0, u1, v1 = CROP_BOX
    pil = Image.fromarray(img[v0:v1, u0:u1].astype(np.uint8))
    w, h = pil.size
    return np.asarray(pil.resize((round(w * UPSCALE), round(h * UPSCALE)), Image.LANCZOS))


def remove_old_labels(
    img: np.ndarray,
    px: dict[str, tuple[int, int]],
    colours: dict[str, tuple[int, int, int]],
) -> np.ndarray:
    """Inpaint the old 1-px labels away (in each robot's colour), only in the label strips."""
    hit = np.zeros(img.shape[:2], dtype=bool)
    for rid, (cx, cy) in px.items():
        zone = np.zeros(img.shape[:2], dtype=bool)
        zone[cy - BOX_HALF_PX - 22 : cy - BOX_HALF_PX - 1, cx - BOX_HALF_PX - 2 : cx + 40] = True
        hit |= colour_mask(img, colours[rid]) & zone
    mask = np.zeros(img.shape[:2], np.uint8)
    mask[hit] = 255
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    bgr = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2BGR)
    out = cv2.inpaint(bgr, mask, 3, cv2.INPAINT_TELEA)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def draw_legible(
    img: np.ndarray,
    px: dict[str, tuple[int, int]],
    colours: dict[str, tuple[int, int, int]],
) -> np.ndarray:
    """Draw 3-px boxes and large non-overlapping label panels from the poses only."""
    out = img.copy()
    mid = sum(u for u, _ in px.values()) / len(px)
    font = cv2.FONT_HERSHEY_SIMPLEX
    for rid, (cx, cy) in sorted(px.items()):
        colour = colours[rid]
        cv2.rectangle(
            out,
            (cx - BOX_HALF_PX - 1, cy - BOX_HALF_PX - 1),
            (cx + BOX_HALF_PX + 1, cy + BOX_HALF_PX + 1),
            colour,
            3,
        )
        (tw, th), base = cv2.getTextSize(rid, font, LABEL_SCALE, LABEL_THICK)
        direction = -1 if cx < mid else 1
        pcx = cx + direction * LABEL_PUSH_PX
        x0 = int(pcx - tw / 2 - LABEL_PAD)
        y1 = cy - BOX_HALF_PX - LABEL_LIFT_PX
        y0 = y1 - th - base - 2 * LABEL_PAD
        x1 = x0 + tw + 2 * LABEL_PAD
        cv2.line(out, (int(pcx), y1), (cx, cy - BOX_HALF_PX - 2), (255, 255, 255), 2, cv2.LINE_AA)
        cv2.rectangle(out, (x0, y0), (x1, y1), (0, 0, 0), -1)
        cv2.rectangle(out, (x0, y0), (x1, y1), colour, 2)
        cv2.putText(
            out,
            rid,
            (x0 + LABEL_PAD, y1 - LABEL_PAD - base),
            font,
            LABEL_SCALE,
            (255, 255, 255),
            LABEL_THICK,
            cv2.LINE_AA,
        )
    return out


def ground_to_marker_plane(x: float, y: float) -> tuple[float, float]:
    """Map a z = 0 world point to the marker-plane point imaging onto the same pixel.

    The homography is for the marker plane (z = 0.21 m) and the camera sits 3.0 m
    above the origin, so a ground point images like the plane point scaled by
    (3.0 - 0.21) / 3.0.
    """
    scale = (CAMERA_HEIGHT_M - MARKER_PLANE_M) / CAMERA_HEIGHT_M
    return x * scale, y * scale


def obstacle_outline_px(artifact: Artifact, homography: np.ndarray) -> list[list[tuple[int, int]]]:
    """Pixel corners of each declared obstacle's ground footprint."""
    polys = []
    for ob in artifact.static_obstacles:
        hx, hy = ob.size_x_m / 2, ob.size_y_m / 2
        polys.append(
            [
                world_to_pixel(ground_to_marker_plane(ob.x + dx, ob.y + dy), homography)
                for dx, dy in ((-hx, hy), (hx, hy), (hx, -hy), (-hx, -hy))
            ]
        )
    return polys


def draw_obstacles(img: np.ndarray, artifact: Artifact, homography: np.ndarray) -> np.ndarray:
    """Type K: outline and label each declared obstacle's ground footprint."""
    out = img.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    for ob, corners in zip(
        artifact.static_obstacles, obstacle_outline_px(artifact, homography), strict=True
    ):
        cv2.polylines(
            out, [np.asarray(corners, np.int32)], True, K1_COLOUR, K1_OUTLINE_THICK, cv2.LINE_AA
        )
        u = min(c[0] for c in corners)
        v = max(c[1] for c in corners) + 30
        cv2.putText(out, ob.obstacle_id, (u, v), font, LABEL_SCALE, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(out, ob.obstacle_id, (u, v), font, LABEL_SCALE, K1_COLOUR, 2, cv2.LINE_AA)
    return out


def k1_zone(artifact: Artifact, homography: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Boxes `(u0, u1, v0, v1)` the K1 overlay may touch: each outline and its label."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    zones = []
    for ob, corners in zip(
        artifact.static_obstacles, obstacle_outline_px(artifact, homography), strict=True
    ):
        us, vs = [c[0] for c in corners], [c[1] for c in corners]
        pad = K1_OUTLINE_THICK + 2
        zones.append((min(us) - pad, max(us) + pad, min(vs) - pad, max(vs) + pad))
        (tw, th), base = cv2.getTextSize(ob.obstacle_id, font, LABEL_SCALE, 5)
        u, v = min(us), max(vs) + 30
        zones.append((u - 4, u + tw + 4, v - th - 4, v + base + 4))
    return zones


def type_l_zone(px: dict[str, tuple[int, int]]) -> tuple[int, int, int, int]:
    """The robot label/box zone `(u0, u1, v0, v1)` inside which L2 may change pixels."""
    us = [u for u, _ in px.values()]
    vs = [v for _, v in px.values()]
    return (
        min(us) - ZONE_U_PX,
        max(us) + ZONE_U_PX,
        min(vs) - ZONE_ABOVE_PX,
        max(vs) + BOX_HALF_PX + 5,
    )


def changed_outside(
    before: np.ndarray, after: np.ndarray, zones: list[tuple[int, int, int, int]]
) -> tuple[int, int]:
    """Count changed pixels and how many of them fall outside every zone.

    Returns:
        `(changed, outside)` pixel counts.
    """
    diff = np.abs(before.astype(int) - after.astype(int)).sum(axis=2) > 0
    ys, xs = np.nonzero(diff)
    inside = np.zeros(len(xs), dtype=bool)
    for u0, u1, v0, v1 in zones:
        inside |= (xs >= u0) & (xs <= u1) & (ys >= v0) & (ys <= v1)
    return int(diff.sum()), int((~inside).sum())


@dataclass(frozen=True)
class Rendered:
    """Full-frame and sent images of one scene."""

    annotated: np.ndarray
    l2_full: np.ndarray
    k1_full: np.ndarray
    l2: np.ndarray
    k1: np.ndarray


def render_scene(artifact: Artifact, homography: np.ndarray) -> Rendered:
    """Render L2 and K1 for one scene from its stored annotated frame."""
    px = robot_pixels(artifact, homography)
    ann = np.asarray(Image.open(artifact.image_path).convert("RGB"))
    colours = overlay_colours(ann, px)
    l2_full = draw_legible(remove_old_labels(ann, px, colours), px, colours)
    k1_full = draw_obstacles(l2_full, artifact, homography)
    return Rendered(ann, l2_full, k1_full, crop_upscale(l2_full), crop_upscale(k1_full))


def png_bytes(img: np.ndarray) -> bytes:
    """Encode an RGB array as PNG bytes with no metadata (deterministic)."""
    buffer = io.BytesIO()
    Image.fromarray(img.astype(np.uint8)).save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def md5_bytes(data: bytes) -> str:
    """Hex MD5 of bytes."""
    return hashlib.md5(data).hexdigest()  # noqa: S324 - an identity check, not security


def md5_file(path: Path) -> str:
    """Hex MD5 of a file's bytes."""
    return md5_bytes(path.read_bytes())


def pixel_md5(img: np.ndarray) -> str:
    """Hex MD5 of decoded RGB pixel bytes plus the shape."""
    arr = np.ascontiguousarray(img.astype(np.uint8))
    return md5_bytes(str(arr.shape).encode() + arr.tobytes())


def grey_image(size: tuple[int, int]) -> np.ndarray:
    """Neutral mid-grey RGB image of `(width, height)`."""
    return np.full((size[1], size[0], 3), GREY_VALUE, dtype=np.uint8)


def write_stimuli(scenes: list[Artifact], out_dir: Path) -> dict[str, dict[str, str]]:
    """Render and write every stimulus image; return md5s per scene and variant.

    Args:
        scenes: The 24 scenes.
        out_dir: Experiment directory; images go to `stimuli/`.

    Returns:
        `{scene: {variant: file md5, variant_pixels: pixel md5, ...}}` plus a
        `"grey"` entry.
    """
    homography = load_homography()
    stim = out_dir / "stimuli"
    stim.mkdir(parents=True, exist_ok=True)
    out: dict[str, dict[str, str]] = {}
    sizes = set()
    for a in scenes:
        key = a.request_id[:8]
        r = render_scene(a, homography)
        sizes.add((r.annotated.shape[1], r.annotated.shape[0]))
        entry = {
            "C_ref": md5_file(a.image_path),
            "C_ref_pixels": pixel_md5(r.annotated),
        }
        for name, img in (("L2", r.l2), ("K1", r.k1)):
            data = png_bytes(img)
            (stim / f"{key}_{name}.png").write_bytes(data)
            entry[name] = md5_bytes(data)
            entry[f"{name}_pixels"] = pixel_md5(img)
        out[key] = entry
    if len(sizes) != 1:
        raise RuntimeError(f"frames differ in size: {sorted(sizes)}")
    ((w, h),) = sizes
    grey = grey_image((w, h))
    data = png_bytes(grey)
    (out_dir / f"grey_{w}x{h}.png").write_bytes(data)
    out["grey"] = {"grey": md5_bytes(data), "grey_pixels": pixel_md5(grey)}
    return out


def contact_sheet(scenes: list[Artifact], out_dir: Path, path: Path) -> Path:
    """Write a JPEG contact sheet: one row per scene, L2 left and K1 right."""
    thumb_w, thumb_h = 512, 160
    sheet = Image.new("RGB", (2 * thumb_w + 140, len(scenes) * (thumb_h + 4)), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    for i, a in enumerate(scenes):
        key = a.request_id[:8]
        y = i * (thumb_h + 4)
        draw.text((4, y + 70), f"{key} {a.obstacle_side}", fill=(0, 0, 0))
        for j, name in enumerate(("L2", "K1")):
            with Image.open(out_dir / "stimuli" / f"{key}_{name}.png") as img:
                sheet.paste(img.resize((thumb_w, thumb_h), Image.LANCZOS), (140 + j * thumb_w, y))
    sheet.save(path, quality=85)
    return path


def main() -> None:
    """Render all stimuli and the contact sheet; print the md5 table."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    scenes = load_scenes(args.runs_dir)
    md5s = write_stimuli(scenes, args.out_dir)
    contact_sheet(scenes, args.out_dir, args.out_dir / "contact_sheet.jpg")
    print(json.dumps(md5s, indent=1))


if __name__ == "__main__":
    main()

"""Zoomed congestion-crop tile: the prompt-apparatus second image (no rclpy).

Prereg-v2 rev 6 registers a "zoomed congestion-crop tile" A/B cell. The tile
is cut from the SAME annotated frame M2 receives (M1's annotation pipeline,
overlays included), around the world-frame bounding box of the congestion
event's INVOLVED set (the detector's `CongestionEvent.involved_robots`, every
robot of it, not one trigger robot; apparatus ruling 2026-10-04) plus a
registered margin, widened to the frame's aspect ratio and resized to a
registered width. It is written beside the stage-1 dump as
`<request_id>_zoom.png`.

Every failure degrades to "no tile" with the reason recorded -- the request
then carries no second image and the prompt no tile sentence, so a failed
crop can never announce an image that is not attached.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict

from swarm_orchestrator.stage2_marks import project_world_to_image

if TYPE_CHECKING:
    from swarm_perception.models import CalibrationArtifact

# Same tolerance as the stage-2 marks: a frame whose x/y scale factors differ
# by more than this is not a resize of the calibrated frame.
_SCALE_TOLERANCE = 0.01


class ZoomTileRecord(BaseModel):
    """What the zoom tile shows, for the artifact's `prompt_conditions` block."""

    model_config = ConfigDict(frozen=True)

    attached: bool
    reason: str | None = None
    path: str | None = None
    robot_ids: tuple[str, ...] = ()
    # Robots' bounding box plus margin, world metres `(x_min, x_max, y_min, y_max)`.
    world_bounds_m: tuple[float, float, float, float] | None = None
    # Crop rectangle in the source frame's pixels, `(x0, y0, x1, y1)`, exclusive end.
    crop_px: tuple[int, int, int, int] | None = None
    source_size: tuple[int, int] | None = None
    output_size: tuple[int, int] | None = None


def zoom_tile_path(frame_dump_dir: str | Path, request_id: str) -> Path:
    """Return where one analysis's zoom tile is written (`<request_id>_zoom.png`)."""
    return Path(frame_dump_dir) / f"{request_id}_zoom.png"


def compute_zoom_crop(
    positions: list[tuple[float, float]],
    margin_m: float,
    homography: np.ndarray,
    calibration_size: tuple[int, int],
    frame_size: tuple[int, int],
) -> tuple[tuple[int, int, int, int], tuple[float, float, float, float]]:
    """Pixel crop around robots' world bounding box, at the frame's aspect ratio.

    Args:
        positions: World `(x, y)` of the robots to frame, metres.
        margin_m: World margin added on every side of their bounding box.
        homography: M1's pixel-to-world homography.
        calibration_size: `(width, height)` the homography was solved for.
        frame_size: `(width, height)` of the frame being cropped.

    Returns:
        `(crop_px, world_bounds_m)`: the crop `(x0, y0, x1, y1)` clamped inside
        the frame, and the margin-padded world box it was derived from.

    Raises:
        ValueError: If `positions` is empty.
    """
    if not positions:
        raise ValueError("no robot positions to frame")
    xs = [x for x, _ in positions]
    ys = [y for _, y in positions]
    bounds = (min(xs) - margin_m, max(xs) + margin_m, min(ys) - margin_m, max(ys) + margin_m)
    corners = [(bounds[i], bounds[j]) for i in (0, 1) for j in (2, 3)]
    pixels = project_world_to_image(corners, homography, calibration_size, frame_size)
    us = [u for u, _ in pixels]
    vs = [v for _, v in pixels]
    width, height = frame_size
    crop_w = max(us) - min(us)
    crop_h = max(vs) - min(vs)
    aspect = width / height
    # Widen the narrow dimension so the tile keeps the frame's aspect ratio.
    if crop_w / max(crop_h, 1e-9) < aspect:
        crop_w = crop_h * aspect
    else:
        crop_h = crop_w / aspect
    crop_w = min(crop_w, width)
    crop_h = min(crop_h, height)
    cu = (max(us) + min(us)) / 2.0
    cv_ = (max(vs) + min(vs)) / 2.0
    x0 = int(math.floor(min(max(cu - crop_w / 2.0, 0.0), width - crop_w)))
    y0 = int(math.floor(min(max(cv_ - crop_h / 2.0, 0.0), height - crop_h)))
    x1 = min(width, x0 + int(math.ceil(crop_w)))
    y1 = min(height, y0 + int(math.ceil(crop_h)))
    return (x0, y0, x1, y1), bounds


def write_zoom_tile(
    frame_rgb: np.ndarray,
    request_id: str,
    frame_dump_dir: str | Path,
    robot_positions: Mapping[str, tuple[float, float]],
    calibration: CalibrationArtifact | None,
    margin_m: float,
    width_px: int,
) -> ZoomTileRecord:
    """Crop, resize and write the zoom tile for one analysis; never raises.

    Args:
        frame_rgb: The annotated RGB frame M2 is sent, `(H, W, 3)`.
        request_id: Identifier of the analysis cycle (names the file).
        frame_dump_dir: Directory the stage-1 frame is dumped into.
        robot_positions: World `(x, y)` of the event's involved robots, by id;
            the crop covers all of them.
        calibration: M1's calibration, or None when unavailable.
        margin_m: World margin around the robots' bounding box.
        width_px: Output tile width; height follows the frame's aspect ratio.

    Returns:
        The record; `attached=False` with a reason on any failure.
    """
    robot_ids = tuple(sorted(robot_positions))
    if calibration is None:
        return ZoomTileRecord(attached=False, reason="calibration_unavailable", robot_ids=robot_ids)
    if frame_rgb is None or not robot_positions:
        return ZoomTileRecord(
            attached=False,
            reason="no_frame" if frame_rgb is None else "no_robots",
            robot_ids=robot_ids,
        )
    try:
        height, width = frame_rgb.shape[:2]
        cal_w, cal_h = calibration.image_size
        sx, sy = width / cal_w, height / cal_h
        if abs(sx - sy) > _SCALE_TOLERANCE * sx:
            return ZoomTileRecord(
                attached=False,
                reason=(
                    f"frame_size_mismatch: frame {width}x{height} vs calibration "
                    f"{cal_w}x{cal_h}"
                ),
                robot_ids=robot_ids,
                source_size=(width, height),
            )
        crop, bounds = compute_zoom_crop(
            [robot_positions[rid] for rid in robot_ids],
            margin_m,
            calibration.homography,
            (cal_w, cal_h),
            (width, height),
        )
        x0, y0, x1, y1 = crop
        tile = frame_rgb[y0:y1, x0:x1]
        out_h = max(1, round(width_px * tile.shape[0] / tile.shape[1]))
        interpolation = cv2.INTER_CUBIC if width_px > tile.shape[1] else cv2.INTER_AREA
        tile = cv2.resize(tile, (width_px, out_h), interpolation=interpolation)
        dest = zoom_tile_path(frame_dump_dir, request_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # RGB at the M1 boundary; OpenCV writes BGR.
        if not cv2.imwrite(str(dest), cv2.cvtColor(tile, cv2.COLOR_RGB2BGR)):
            return ZoomTileRecord(
                attached=False, reason=f"write_failed: {dest}", robot_ids=robot_ids
            )
        return ZoomTileRecord(
            attached=True,
            path=str(dest),
            robot_ids=robot_ids,
            world_bounds_m=bounds,
            crop_px=crop,
            source_size=(width, height),
            output_size=(width_px, out_h),
        )
    except Exception as exc:  # a failed crop drops the tile, never the analysis
        return ZoomTileRecord(
            attached=False, reason=f"crop_error: {type(exc).__name__}: {exc}", robot_ids=robot_ids
        )

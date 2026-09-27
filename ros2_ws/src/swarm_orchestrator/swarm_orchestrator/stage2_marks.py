"""Stage-2 set-of-mark rendering: candidate letters drawn on the decision frame (no rclpy).

Rev-8 A.3 adopts set-of-mark prompting (2310.11441): each retreat candidate is
drawn on the image with its letter, so the model can tie a letter to what it
sees at that spot. The drawing is made here, where M5's dumped stage-1 frame
(M1's annotated frame) and M1's calibration meet, and is written as a separate
`<request_id>_stage2.png`; the stage-1 dump is never modified.

Every failure degrades to the unmarked stage-1 frame with the reason recorded;
nothing here raises into the stage-2 call. `swarm_perception` is imported
lazily for the same reason: an M5 install without it must still start, with
stage 2 unmarked, instead of failing at import.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from swarm_perception.models import CalibrationArtifact

# Radius of the ring drawn around each candidate: the space the yielder will
# occupy there (a TurtleBot3 is ~0.3 m across). A ring, not a filled disc, so
# an obstacle sitting on a candidate stays visible inside it.
_FOOTPRINT_RADIUS_M = 0.15
# Letter badge radius as a fraction of the frame width (12 px at 1280), with a
# floor so the glyph stays legible on a downscaled frame. Small on purpose:
# at ~0.0044 m/px a 0.3 m obstacle spans ~69 px, and the badge must not hide it.
_BADGE_RADIUS_FRACTION = 0.0095
_BADGE_RADIUS_MIN_PX = 9
# A dumped frame whose x and y scale factors differ by more than this is not
# a resize of the calibrated frame, so the homography does not apply to it.
_SCALE_TOLERANCE = 0.01
_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)

LetterPoint = tuple[str, float, float]


class LetterMark(BaseModel):
    """One candidate letter placed on the stage-2 image."""

    model_config = ConfigDict(frozen=True)

    letter: str
    # World-frame candidate position, metres.
    x: float
    y: float
    # Pixel position in the drawn image (after any downscale), as `(u, v)`.
    u: int
    v: int


class Stage2Marks(BaseModel):
    """What the stage-2 image shows, for the stage-2 artifact block."""

    model_config = ConfigDict(frozen=True)

    marks_drawn: bool
    # Why the marks were not drawn; None when they were.
    reason: str | None = None
    # The stage-1 frame the marks were drawn on (or would have been).
    source_image_path: str
    # The image the stage-2 call is given: the marked copy, or the source.
    image_path: str
    calibration_path: str | None = None
    # Dumped-frame size over calibration size, as `(sx, sy)`.
    scale: tuple[float, float] | None = None
    marks: list[LetterMark] = []


def stage2_image_path(source_image_path: str, request_id: str) -> str:
    """Return where the marked stage-2 image of one analysis is written.

    Args:
        source_image_path: The dumped stage-1 frame, `<dir>/<request_id>.png`.
        request_id: Identifier of the analysis cycle.

    Returns:
        `<dir>/<request_id>_stage2.png`, beside the stage-1 frame.
    """
    return str(Path(source_image_path).with_name(f"{request_id}_stage2.png"))


def project_world_to_image(
    points: Sequence[tuple[float, float]],
    homography: np.ndarray,
    calibration_size: tuple[int, int],
    image_size: tuple[int, int],
) -> list[tuple[float, float]]:
    """Project world-frame points into pixel coordinates of a (resized) frame.

    World to pixel: `swarm_perception.geometry.world_to_pixel` applies the
    inverse of M1's pixel-to-world ground-plane homography, the same mapping
    M1's annotation pass draws robot boxes with. The result is in the
    calibrated frame's pixels, then scaled to `image_size`.

    Args:
        points: World coordinates `(x, y)` in metres.
        homography: M1's pixel-to-world homography, `(3, 3)`.
        calibration_size: `(width, height)` the homography was solved for.
        image_size: `(width, height)` of the frame drawn on.

    Returns:
        Pixel coordinates `(u, v)` in `image_size`, one per point.
    """
    from swarm_perception.geometry import world_to_pixel

    sx = image_size[0] / calibration_size[0]
    sy = image_size[1] / calibration_size[1]
    projected = []
    for point in points:
        u, v = world_to_pixel(point, homography)
        projected.append((u * sx, v * sy))
    return projected


def _draw_mark(image: np.ndarray, letter: str, centre: tuple[int, int], ring_px: int) -> None:
    height, width = image.shape[:2]
    badge = max(_BADGE_RADIUS_MIN_PX, round(_BADGE_RADIUS_FRACTION * width))
    # Black under white: the ring reads on a light floor and on a dark one.
    if ring_px > badge:
        cv2.circle(image, centre, ring_px, _BLACK, 3, cv2.LINE_AA)
        cv2.circle(image, centre, ring_px, _WHITE, 1, cv2.LINE_AA)
    cv2.circle(image, centre, badge, _WHITE, -1, cv2.LINE_AA)
    cv2.circle(image, centre, badge, _BLACK, 2, cv2.LINE_AA)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.05 * badge
    thickness = max(1, round(badge / 6))
    (text_w, text_h), _ = cv2.getTextSize(letter, font, scale, thickness)
    origin = (centre[0] - text_w // 2, centre[1] + text_h // 2)
    cv2.putText(image, letter, origin, font, scale, _BLACK, thickness, cv2.LINE_AA)


class CandidateMarker:
    """Draws stage-2 candidate letters with M1's calibration; never raises."""

    def __init__(
        self,
        calibration: CalibrationArtifact | None,
        calibration_path: str | None,
        unavailable_reason: str | None = None,
    ) -> None:
        """Hold the calibration the marks are placed with.

        Args:
            calibration: M1's calibration, or None when it could not be loaded.
            calibration_path: Where it was (or should have been) loaded from.
            unavailable_reason: Why `calibration` is None; recorded on every
                render.
        """
        self._calibration = calibration
        self._calibration_path = calibration_path
        self._unavailable_reason = (
            None
            if calibration is not None
            else unavailable_reason or "calibration_unavailable"
        )

    @classmethod
    def from_path(cls, path: str) -> CandidateMarker:
        """Load M1's calibration file; a failure yields an unavailable marker.

        Args:
            path: The `calibration.yaml` M1 runs with.

        Returns:
            A marker that draws, or one that records why it cannot.
        """
        try:
            from swarm_perception.calibration import load_calibration

            return cls(load_calibration(path), path)
        except Exception as exc:  # stage 2 must run unmarked rather than stop M5
            return cls.unavailable(
                f"calibration_unavailable: {type(exc).__name__}: {exc}", path
            )

    @classmethod
    def unavailable(cls, reason: str, calibration_path: str | None = None) -> CandidateMarker:
        """Build a marker that never draws and records `reason`.

        Args:
            reason: Why no calibration is available.
            calibration_path: The path that failed, if any.

        Returns:
            The marker.
        """
        return cls(None, calibration_path, reason)

    @property
    def available(self) -> bool:
        """Whether a calibration is loaded."""
        return self._calibration is not None

    @property
    def unavailable_reason(self) -> str | None:
        """Why no calibration is loaded, or None when one is."""
        return self._unavailable_reason

    def render(
        self, request_id: str, source_image_path: str, letters: Sequence[LetterPoint]
    ) -> Stage2Marks:
        """Draw each candidate letter at its position on a copy of the frame.

        Args:
            request_id: Identifier of the analysis cycle (names the output).
            source_image_path: The dumped stage-1 frame.
            letters: `(letter, x, y)` per candidate, world frame in metres.

        Returns:
            The marks and the image to send; on any failure the unmarked
            source with `marks_drawn=False` and the reason.
        """
        base = {
            "source_image_path": source_image_path,
            "calibration_path": self._calibration_path,
        }
        try:
            return self._render(request_id, source_image_path, letters, base)
        except Exception as exc:  # drawing must never fail the stage-2 call
            return Stage2Marks(
                marks_drawn=False,
                reason=f"render_error: {type(exc).__name__}: {exc}",
                image_path=source_image_path,
                **base,
            )

    def _render(
        self,
        request_id: str,
        source_image_path: str,
        letters: Sequence[LetterPoint],
        base: dict,
    ) -> Stage2Marks:
        def unmarked(reason: str, **extra) -> Stage2Marks:
            return Stage2Marks(
                marks_drawn=False, reason=reason, image_path=source_image_path, **base, **extra
            )

        calibration = self._calibration
        if calibration is None:
            return unmarked(self._unavailable_reason or "calibration_unavailable")
        # imread returns BGR and imwrite takes BGR, so the file-to-file draw
        # stays in OpenCV's order; the RGB boundary was crossed at the dump.
        image = cv2.imread(source_image_path, cv2.IMREAD_COLOR)
        if image is None:
            return unmarked(f"frame_unreadable: {source_image_path}")
        height, width = image.shape[:2]
        cal_w, cal_h = calibration.image_size
        scale = (width / cal_w, height / cal_h)
        if abs(scale[0] - scale[1]) > _SCALE_TOLERANCE * scale[0]:
            return unmarked(
                f"frame_size_mismatch: frame {width}x{height} vs calibration {cal_w}x{cal_h}",
                scale=scale,
            )
        homography = calibration.homography
        centres = project_world_to_image(
            [(x, y) for _, x, y in letters], homography, (cal_w, cal_h), (width, height)
        )
        rims = project_world_to_image(
            [(x + _FOOTPRINT_RADIUS_M, y) for _, x, y in letters],
            homography,
            (cal_w, cal_h),
            (width, height),
        )
        marks = [
            LetterMark(letter=letter, x=x, y=y, u=round(u), v=round(v))
            for (letter, x, y), (u, v) in zip(letters, centres, strict=True)
        ]
        outside = [m.letter for m in marks if not (0 <= m.u < width and 0 <= m.v < height)]
        if outside:
            return unmarked(
                f"candidate_out_of_frame: {','.join(outside)}", scale=scale, marks=marks
            )
        drawn = image.copy()
        for mark, (u, v), (ru, rv) in zip(marks, centres, rims, strict=True):
            ring_px = round(float(np.hypot(ru - u, rv - v)))
            _draw_mark(drawn, mark.letter, (mark.u, mark.v), ring_px)
        dest = stage2_image_path(source_image_path, request_id)
        if not cv2.imwrite(dest, drawn):
            return unmarked(f"render_error: could not write {dest}", scale=scale, marks=marks)
        return Stage2Marks(
            marks_drawn=True, image_path=dest, scale=scale, marks=marks, **base
        )

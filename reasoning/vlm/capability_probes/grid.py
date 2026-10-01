"""Fixed 3x3 pixel-space grid overlay for the `locate_robot` probe.

The grid partitions the image into 9 cells of fixed pixel bounds (row-major,
index 0 top-left .. 8 bottom-right), independent of calibration: it needs
only the frame's own width and height. Which physical cell shows which
letter badge is drawn fresh per item from the item's seed
(`reasoning.vlm.capability_probes.letters`), so the correct answer is not
always the same letter (e.g. always the centre cell) across items -- the
marked-choice rule (SoM/MOKA, prereg-v2 rev 5), applied to a grid instead of
per-candidate marks.

Ground truth for "which cell is robot X in" is instead a pixel-space question
computed from Isaac Sim's world-frame position via M1's calibration
(`reasoning.vlm.capability_probes.ground_truth`); this module only defines
the partition and draws it.
"""
from __future__ import annotations

import cv2
import numpy as np

GRID_ROWS = 3
GRID_COLS = 3
GRID_CELL_COUNT = GRID_ROWS * GRID_COLS

# A point within this many pixels of a cell boundary is excluded from the
# candidate pool (`ground_truth.grid_cell_for_pixel` returns None): close to a
# boundary, a few pixels of M1/GT disagreement or rendering jitter could flip
# the "correct" cell, which would make the item's frozen answer unreliable.
_BOUNDARY_MARGIN_PX = 18

_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)
_LINE_COLOR = (0, 215, 255)  # amber; visible on both the light floor and dark shelving


def cell_bounds_px(image_width: int, image_height: int) -> list[tuple[int, int, int, int]]:
    """Return each cell's pixel bounds, row-major index 0 (top-left) to 8 (bottom-right).

    Args:
        image_width: Frame width in pixels.
        image_height: Frame height in pixels.

    Returns:
        `(x0, y0, x1, y1)` per cell, `x1`/`y1` exclusive.
    """
    col_edges = [round(c * image_width / GRID_COLS) for c in range(GRID_COLS + 1)]
    row_edges = [round(r * image_height / GRID_ROWS) for r in range(GRID_ROWS + 1)]
    bounds = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            bounds.append((col_edges[col], row_edges[row], col_edges[col + 1], row_edges[row + 1]))
    return bounds


def cell_center_px(cell_index: int, image_width: int, image_height: int) -> tuple[int, int]:
    """Return the pixel centre of one grid cell, for drawing its letter badge."""
    x0, y0, x1, y1 = cell_bounds_px(image_width, image_height)[cell_index]
    return (x0 + x1) // 2, (y0 + y1) // 2


def cell_index_for_pixel(u: int, v: int, image_width: int, image_height: int) -> int | None:
    """Return the grid cell containing `(u, v)`, or None near a boundary or off-frame.

    Args:
        u: Pixel column.
        v: Pixel row.
        image_width: Frame width in pixels.
        image_height: Frame height in pixels.

    Returns:
        The 0-based row-major cell index, or None when `(u, v)` falls outside
        the frame or within `_BOUNDARY_MARGIN_PX` of a cell edge.
    """
    if not (0 <= u < image_width and 0 <= v < image_height):
        return None
    col_edges = [round(c * image_width / GRID_COLS) for c in range(GRID_COLS + 1)]
    row_edges = [round(r * image_height / GRID_ROWS) for r in range(GRID_ROWS + 1)]
    col = next((c for c in range(GRID_COLS) if col_edges[c] <= u < col_edges[c + 1]), None)
    row = next((r for r in range(GRID_ROWS) if row_edges[r] <= v < row_edges[r + 1]), None)
    if col is None or row is None:
        return None
    if min(u - col_edges[col], col_edges[col + 1] - u) < _BOUNDARY_MARGIN_PX:
        return None
    if min(v - row_edges[row], row_edges[row + 1] - v) < _BOUNDARY_MARGIN_PX:
        return None
    return row * GRID_COLS + col


def _draw_cell_badge(image: np.ndarray, letter: str, centre: tuple[int, int]) -> None:
    height, width = image.shape[:2]
    radius = max(16, round(0.016 * width))
    cv2.circle(image, centre, radius, _WHITE, -1, cv2.LINE_AA)
    cv2.circle(image, centre, radius, _BLACK, 2, cv2.LINE_AA)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.045 * radius
    thickness = max(1, round(radius / 10))
    (text_w, text_h), _ = cv2.getTextSize(letter, font, scale, thickness)
    origin = (centre[0] - text_w // 2, centre[1] + text_h // 2)
    cv2.putText(image, letter, origin, font, scale, _BLACK, thickness, cv2.LINE_AA)


def draw_grid_overlay(image: np.ndarray, option_by_letter: dict[str, str]) -> np.ndarray:
    """Draw grid lines and one letter badge per cell on a copy of `image`.

    Args:
        image: BGR frame (OpenCV convention), as read by `cv2.imread`.
        option_by_letter: Letter -> grid-cell-index string (e.g. `{"A": "4"}`),
            from `reasoning.vlm.capability_probes.letters.build_item_choices`.

    Returns:
        A new BGR image with the grid and letters drawn; `image` is untouched.
    """
    height, width = image.shape[:2]
    drawn = image.copy()
    col_edges = [round(c * width / GRID_COLS) for c in range(1, GRID_COLS)]
    row_edges = [round(r * height / GRID_ROWS) for r in range(1, GRID_ROWS)]
    for x in col_edges:
        cv2.line(drawn, (x, 0), (x, height), _LINE_COLOR, 2, cv2.LINE_AA)
    for y in row_edges:
        cv2.line(drawn, (0, y), (width, y), _LINE_COLOR, 2, cv2.LINE_AA)
    for letter, cell_index_str in option_by_letter.items():
        centre = cell_center_px(int(cell_index_str), width, height)
        _draw_cell_badge(drawn, letter, centre)
    return drawn

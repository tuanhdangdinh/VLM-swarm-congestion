"""Checks a probe item's drawn marks against M1's own annotation drawing.

A grid badge (`grid.draw_grid_overlay`) sitting on top of a robot's status
box or ID label, or one robot's box covering another robot's label, would
make an item unanswerable from the image alone (2026-10-02, visual
spot-check history: a badge at a cell centre landing on a robot whose GT
position is itself near that centre; then, separately, a *different*
tracked robot's label clipped by a badge in the same frame; then a
neighbouring robot's box covering part of the named robot's label). This
module replicates `swarm_perception.annotation.draw_robot_overlay`'s box/label
pixel geometry -- not an approximation of it, and
`tests/unit/test_annotation_geometry_fidelity.py` renders the real function
and asserts every drawn pixel stays inside these rects plus `SLACK_PX` -- so
the checks here test (within that slack) the pixels M1 actually draws.

**Scope**: only the status box and ID label are modelled, not the velocity
arrow or goal marker `draw_robot_overlay` also draws. Those are decorative
(not needed to read a robot's identity or position) and are small/thin
enough that the fidelity test's slack does not need to cover them; a probe
item does not depend on either being unoccluded.
"""
from __future__ import annotations

import cv2

# Mirrors swarm_perception.annotation.draw_robot_overlay exactly: box
# half-size 20 px; label origin at (cx - box_half, cy - box_half - 5),
# FONT_HERSHEY_SIMPLEX scale 0.5 thickness 1. Any drift between these
# constants and that module would silently reintroduce the occlusion bug
# this module exists to catch; `test_annotation_geometry_fidelity.py` pins
# the two against each other.
_BOX_HALF_PX = 20
_LABEL_FONT = cv2.FONT_HERSHEY_SIMPLEX
_LABEL_SCALE = 0.5
_LABEL_THICKNESS = 1

# Pixels of slack added around a rect or badge radius before testing overlap:
# `draw_robot_overlay`'s box outline and `grid._draw_cell_badge`'s ring are
# each 2-3 px of line thickness, and OpenCV's anti-aliased lines (LINE_AA)
# spread a faint edge slightly further than the nominal geometry.
# `test_annotation_geometry_fidelity.py` measures this directly.
SLACK_PX = 3


def robot_annotation_rects(robot_id: str, cx: int, cy: int) -> list[tuple[int, int, int, int]]:
    """Return the pixel rects M1's annotation pass draws for one robot.

    Args:
        robot_id: The robot's id (its drawn label text).
        cx: Robot centre pixel column.
        cy: Robot centre pixel row.

    Returns:
        `[status_box_rect, id_label_rect]`, each `(x0, y0, x1, y1)`.
    """
    box = (cx - _BOX_HALF_PX, cy - _BOX_HALF_PX, cx + _BOX_HALF_PX, cy + _BOX_HALF_PX)
    (text_w, text_h), baseline = cv2.getTextSize(
        robot_id, _LABEL_FONT, _LABEL_SCALE, _LABEL_THICKNESS
    )
    label_x0 = cx - _BOX_HALF_PX
    label_y0 = cy - _BOX_HALF_PX - 5 - text_h
    label = (label_x0, label_y0, label_x0 + text_w, label_y0 + text_h + baseline)
    return [box, label]


def _rect_circle_overlaps(
    rect: tuple[int, int, int, int], centre: tuple[int, int], radius: int
) -> bool:
    x0, y0, x1, y1 = rect
    cx, cy = centre
    closest_x = max(x0, min(cx, x1))
    closest_y = max(y0, min(cy, y1))
    dx, dy = cx - closest_x, cy - closest_y
    return (dx * dx + dy * dy) <= (radius + SLACK_PX) ** 2


def rects_overlap(
    a: tuple[int, int, int, int], b: tuple[int, int, int, int], slack: int = SLACK_PX
) -> bool:
    """Return whether two axis-aligned rects overlap, each padded by `slack`.

    Args:
        a: `(x0, y0, x1, y1)`.
        b: `(x0, y0, x1, y1)`.
        slack: Pixels each rect is grown by on every side before testing.

    Returns:
        True if the padded rects intersect.
    """
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return (
        ax0 - slack < bx1 + slack
        and ax1 + slack > bx0 - slack
        and ay0 - slack < by1 + slack
        and ay1 + slack > by0 - slack
    )


def robot_overlaps_any_grid_badge(
    robot_id: str, cx: int, cy: int, image_width: int, image_height: int
) -> bool:
    """Return whether M1's drawn box/label for this robot would collide with any grid badge.

    Every grid cell always gets exactly one letter badge drawn at its centre
    (`grid.draw_grid_overlay`) -- only *which* letter varies by item seed --
    so this checks the robot's drawn geometry against all 9 fixed badge
    positions, not only the position that happens to be its own correct cell.

    Args:
        robot_id: The robot's id.
        cx: Robot centre pixel column.
        cy: Robot centre pixel row.
        image_width: Frame width in pixels.
        image_height: Frame height in pixels.

    Returns:
        True if any of the 9 badges would overlap the robot's status box or
        ID label.
    """
    from reasoning.vlm.capability_probes.grid import (
        GRID_CELL_COUNT,
        badge_radius_px,
        cell_center_px,
    )

    radius = badge_radius_px(image_width)
    rects = robot_annotation_rects(robot_id, cx, cy)
    for cell_index in range(GRID_CELL_COUNT):
        centre = cell_center_px(cell_index, image_width, image_height)
        if any(_rect_circle_overlaps(rect, centre, radius) for rect in rects):
            return True
    return False

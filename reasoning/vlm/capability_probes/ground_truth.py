"""Machine-derived correct answers for each probe type, from Isaac Sim GT.

Every answer here is computed from `gt/ground_truth.jsonl` (Isaac Sim's own
logged world-frame robot poses), never hand-labeled, projected into pixels
only through M1's calibration homography. `swarm_perception` is imported
lazily (same convention as `swarm_orchestrator.stage2_marks`): a probe-battery
install without the M1 package must still fail with a clear ImportError at
the one call site that needs it, not at module import time.

**Left-vs-right operationalization (recorded for the v2 freeze owner):**
"left-vs-right of aisle" is operationalized here as image-frame left/right of
the frame's own horizontal centre column, not a world-frame aisle-centreline
side. The two are the same question only when the aisle's long axis runs
left-right in the image (true for every scenario this battery draws from,
verified by projecting GT positions back onto a sample frame before this
module was written); a scenario whose aisle runs top-to-bottom in-frame would
need a different operationalization. This is a visual-grounding probe (LRR-Bench's
framing) rather than a scene-geometry probe, so the image-frame definition is
the one actually being tested.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

# Maximum per-axis disagreement (metres) between M1's estimate and Isaac's GT
# for every robot in a frame, for the frame to be usable at all: beyond this,
# the ID label M1 drew is no longer trustworthy evidence of where the GT
# position actually is in the image.
M1_GT_MAX_DISAGREEMENT_M = 0.1

# A robot occupies roughly this radius around its centre point (a TurtleBot3
# is ~0.3 m across; mirrors swarm_orchestrator.stage2_marks's
# _FOOTPRINT_RADIUS_M). A margin check against a centre point alone would let
# an item through where the robot's drawn body straddles the line being
# checked against.
ROBOT_FOOTPRINT_RADIUS_M = 0.15

# Minimum |x_world - aisle_centre_x| (metres) for a left_right candidate to be
# kept (2026-10-02, corrected after a visual spot-check): must clear both the
# robot's own footprint and the M1-vs-GT disagreement bound, so neither the
# robot's physical body nor M1's drawn label can land on the wrong side of
# the centre column. `ROBOT_FOOTPRINT_RADIUS_M + M1_GT_MAX_DISAGREEMENT_M`
# is 0.25; rounded up for slack.
LEFT_RIGHT_MARGIN_M = 0.3

# Minimum gap (metres) between the nearest and second-nearest other robot for
# a nearest_first candidate to be kept, for the same reason.
NEAREST_FIRST_MARGIN_M = 0.3


def world_to_pixel(x: float, y: float, homography: np.ndarray) -> tuple[int, int]:
    """Project one Isaac Sim GT world point into frame pixels via M1's homography.

    Args:
        x: World-frame x, metres.
        y: World-frame y, metres.
        homography: M1's pixel-to-world homography, `(3, 3)` (its inverse is
            the world-to-pixel direction used here).

    Returns:
        Pixel coordinate `(u, v)`.
    """
    from swarm_perception.geometry import world_to_pixel as _world_to_pixel

    return _world_to_pixel((x, y), homography)


def pixel_to_world(u: float, v: float, homography: np.ndarray) -> tuple[float, float]:
    """Inverse of `world_to_pixel`; used only to locate the frame's centre column in world x."""
    from swarm_perception.geometry import pixel_to_world as _pixel_to_world

    return _pixel_to_world((u, v), homography)


def aisle_center_x_world(homography: np.ndarray, image_width: int, image_height: int) -> float:
    """Return the world-frame x of the frame's own horizontal centre column.

    See the module docstring: this is the left_right reference line, defined
    in image space and only expressed in world x for a cheap world-frame
    margin check (`left_right_answer`).
    """
    x, _ = pixel_to_world(image_width / 2.0, image_height / 2.0, homography)
    return x


def robot_count_answer(robots: dict[str, dict]) -> str:
    """Return the GT robot count as the probe's canonical answer string."""
    return str(len(robots))


def nearest_first_answer(
    robots: dict[str, dict], reference_robot_id: str
) -> tuple[str, float] | None:
    """Return the GT-nearest other robot to `reference_robot_id`, and its margin.

    Args:
        robots: GT robot_id -> `{"x": ..., "y": ...}` at the matched instant.
        reference_robot_id: The robot the question names.

    Returns:
        `(nearest_robot_id, gap_m)` where `gap_m` is the distance from the
        nearest to the second-nearest other robot (the margin
        `NEAREST_FIRST_MARGIN_M` is checked against), or None when fewer than
        two other robots are present.
    """
    ref = robots[reference_robot_id]
    others = sorted(
        (
            (rid, math.hypot(r["x"] - ref["x"], r["y"] - ref["y"]))
            for rid, r in robots.items()
            if rid != reference_robot_id
        ),
        key=lambda pair: pair[1],
    )
    if len(others) < 2:
        return None
    gap = others[1][1] - others[0][1]
    return others[0][0], gap


def left_right_answer(
    x: float, homography: np.ndarray, image_width: int, image_height: int
) -> tuple[str, float]:
    """Return ("left" | "right", margin_m) for one robot's world-frame x.

    Args:
        x: The robot's GT world-frame x, metres.
        homography: M1's calibration homography.
        image_width: Frame width in pixels.
        image_height: Frame height in pixels.

    Returns:
        `"left"` when `x` is left of the frame's centre column (smaller
        world x, given this calibration's positive x-to-u scale), else
        `"right"`; `margin_m` is `|x - centre_x|`.
    """
    centre_x = aisle_center_x_world(homography, image_width, image_height)
    side = "left" if x < centre_x else "right"
    return side, abs(x - centre_x)


def grid_cell_answer(
    x: float, y: float, homography: np.ndarray, image_width: int, image_height: int
) -> int | None:
    """Return the GT grid-cell index (0..8) for one robot's world position.

    Args:
        x: World-frame x, metres.
        y: World-frame y, metres.
        homography: M1's calibration homography.
        image_width: Frame width in pixels.
        image_height: Frame height in pixels.

    Returns:
        The cell index, or None when the projected pixel is off-frame or
        too close to a cell boundary (`grid.cell_index_for_pixel`).
    """
    from reasoning.vlm.capability_probes.grid import cell_index_for_pixel

    u, v = world_to_pixel(x, y, homography)
    return cell_index_for_pixel(u, v, image_width, image_height)


# A robot within this many pixels of a frame edge may have its M1-drawn ID
# label clipped (2026-10-02, visual spot-check: a robot_1 label was cut off
# at the right edge of a kept item's frame). Any probe item naming a robot
# must be answerable from a fully visible label.
EDGE_MARGIN_PX = 70

# Two robots' drawn 40x40 status boxes (box half-size 20 px,
# `swarm_perception.annotation.draw_robot_overlay`) start touching at 40 px
# of separation; this gives slack so a `robot_count` frame's boxes/labels
# stay visually distinct rather than merging into one blob.
MIN_ROBOT_SEPARATION_PX = 70


def is_away_from_frame_edge(u: int, v: int, image_width: int, image_height: int) -> bool:
    """Return whether `(u, v)` clears `EDGE_MARGIN_PX` from every frame edge.

    Args:
        u: Pixel column.
        v: Pixel row.
        image_width: Frame width in pixels.
        image_height: Frame height in pixels.

    Returns:
        True when a robot centred at `(u, v)` is far enough from every edge
        that its ID label (drawn by M1's annotation pass near the robot) is
        unlikely to be clipped.
    """
    return (
        EDGE_MARGIN_PX <= u <= image_width - EDGE_MARGIN_PX
        and EDGE_MARGIN_PX <= v <= image_height - EDGE_MARGIN_PX
    )


def max_m1_gt_disagreement_m(m1_robots: dict[str, dict], gt_robots: dict[str, dict]) -> float:
    """Return the largest per-axis M1-vs-GT disagreement across shared robots.

    Args:
        m1_robots: robot_id -> `{"x": ..., "y": ...}` from the decision
            artifact's `scene.robots` (M1's estimate at prompt time).
        gt_robots: robot_id -> `{"x": ..., "y": ...}` from the matched
            `ground_truth.jsonl` row (Isaac Sim's own state).

    Returns:
        `inf` when the robot sets disagree (a frame a probe item must not be
        built from); otherwise the largest absolute per-axis difference,
        metres.
    """
    if set(m1_robots) != set(gt_robots):
        return math.inf
    worst = 0.0
    for robot_id, m1 in m1_robots.items():
        gt = gt_robots[robot_id]
        worst = max(worst, abs(m1["x"] - gt["x"]), abs(m1["y"] - gt["y"]))
    return worst

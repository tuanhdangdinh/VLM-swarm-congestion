"""Ties the capability-probe occlusion geometry to M1's real drawing code.

`reasoning.vlm.capability_probes.occlusion` and `.grid` each replicate pixel
geometry owned elsewhere (`swarm_perception.annotation.draw_robot_overlay`
and `grid._draw_cell_badge` itself). A replica that quietly drifted from the
real drawing would make every occlusion/legibility check built on it wrong
in the same direction the check exists to catch (2026-10-02, third
correction review). These tests render the real functions on a blank canvas
and assert every pixel they actually paint stays inside the replica's rects
or radius, padded by `occlusion.SLACK_PX` -- not a looser approximation of
"close enough".
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path("ros2_ws/src/swarm_perception").resolve()))
from swarm_perception.annotation import draw_robot_overlay
from swarm_perception.models import CalibrationArtifact, RobotState

from reasoning.vlm.capability_probes import grid, occlusion

_CANVAS_SIZE = 600
_ROBOT_CENTRE = (300, 300)
_IDENTITY_CALIBRATION = CalibrationArtifact(
    intrinsics=np.eye(3),
    distortion=np.zeros(5),
    homography=np.eye(3),
    image_size=(_CANVAS_SIZE, _CANVAS_SIZE),
    source_id="test",
    created_at=0.0,
)


def _painted_pixels(image: np.ndarray) -> list[tuple[int, int]]:
    """Return `(x, y)` of every pixel `image` differs from black at."""
    ys, xs = np.nonzero(np.any(image != 0, axis=2))
    return list(zip(xs.tolist(), ys.tolist(), strict=True))


def _inside(rect: tuple[int, int, int, int], x: int, y: int, slack: int) -> bool:
    x0, y0, x1, y1 = rect
    return (x0 - slack) <= x <= (x1 + slack) and (y0 - slack) <= y <= (y1 + slack)


class TestRobotAnnotationRectsMatchTheRealDrawing:
    def test_every_drawn_pixel_is_inside_the_box_or_label_rect(self):
        canvas = np.zeros((_CANVAS_SIZE, _CANVAS_SIZE, 3), dtype=np.uint8)
        robot = RobotState(
            robot_id="robot_1",
            x=float(_ROBOT_CENTRE[0]),
            y=float(_ROBOT_CENTRE[1]),
            theta=0.0,
            linear_velocity=0.0,  # suppresses the velocity arrow (out of scope)
            angular_velocity=0.0,
            task=None,
            status="STOPPED",
            goal=None,  # suppresses the goal marker (out of scope)
            stamp=0.0,
        )
        draw_robot_overlay(canvas, robot, color=(0, 200, 0), calibration=_IDENTITY_CALIBRATION)

        box, label = occlusion.robot_annotation_rects("robot_1", *_ROBOT_CENTRE)
        painted = _painted_pixels(canvas)
        assert painted, "the real drawing function painted nothing -- test setup is broken"
        slack = occlusion.SLACK_PX
        stray = [
            (x, y)
            for x, y in painted
            if not (_inside(box, x, y, slack) or _inside(label, x, y, slack))
        ]
        assert stray == []

    def test_a_longer_id_paints_outside_the_short_label_rect(self):
        # Negative control: proves the test above is not vacuous by showing a
        # label rect that is too narrow DOES get flagged.
        canvas = np.zeros((_CANVAS_SIZE, _CANVAS_SIZE, 3), dtype=np.uint8)
        robot = RobotState(
            robot_id="robot_12345",
            x=float(_ROBOT_CENTRE[0]),
            y=float(_ROBOT_CENTRE[1]),
            theta=0.0,
            linear_velocity=0.0,
            angular_velocity=0.0,
            task=None,
            status="STOPPED",
            goal=None,
            stamp=0.0,
        )
        draw_robot_overlay(canvas, robot, color=(0, 200, 0), calibration=_IDENTITY_CALIBRATION)

        _box, undersized_label = occlusion.robot_annotation_rects("r", *_ROBOT_CENTRE)
        painted = _painted_pixels(canvas)
        stray = [
            (x, y) for x, y in painted if not _inside(undersized_label, x, y, occlusion.SLACK_PX)
        ]
        # Some of "robot_12345"'s painted pixels must fall outside "r"'s
        # (much narrower) label rect, even with slack.
        assert stray != []


class TestGridBadgeRadiusMatchesTheRealDrawing:
    def test_every_drawn_pixel_is_inside_the_badge_radius(self):
        width, height = 1280, 960
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        centre = grid.cell_center_px(4, width, height)
        grid._draw_cell_badge(canvas, "A", centre)  # white-box: tests grid's own internals

        radius = grid.badge_radius_px(width)
        painted = _painted_pixels(canvas)
        assert painted
        cx, cy = centre
        max_r = max(((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x, y in painted)
        assert max_r <= radius + occlusion.SLACK_PX

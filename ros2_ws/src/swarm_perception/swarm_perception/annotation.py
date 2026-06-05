from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np

from swarm_perception.geometry import world_to_pixel
from swarm_perception.models import CalibrationArtifact, RobotState, SceneState

_STATUS_COLORS: dict[str, tuple[int, int, int]] = {
    "MOVING": (0, 200, 0),
    "SLOW": (200, 200, 0),
    "STOPPED": (200, 0, 0),
    "STALE": (128, 128, 128),
}

_ARROW_LENGTH_PX = 40
_GOAL_RADIUS_PX = 8


def status_to_color(status: str) -> tuple[int, int, int]:
    return _STATUS_COLORS.get(status, (128, 128, 128))


def draw_robot_overlay(
    image: np.ndarray,
    robot: RobotState,
    color: tuple[int, int, int],
    calibration: CalibrationArtifact,
) -> None:
    """Draw status box, ID label, velocity arrow, and goal marker on image in-place."""
    import cv2

    h, w = image.shape[:2]
    cx, cy = world_to_pixel((robot.x, robot.y), calibration.homography)

    box_half = 20
    pt1 = (max(0, cx - box_half), max(0, cy - box_half))
    pt2 = (min(w - 1, cx + box_half), min(h - 1, cy + box_half))
    cv2.rectangle(image, pt1, pt2, color, 2)

    cv2.putText(
        image,
        robot.robot_id,
        (max(0, cx - box_half), max(0, cy - box_half - 5)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA,
    )

    if abs(robot.linear_velocity) > 1e-3:
        ax = int(round(cx + _ARROW_LENGTH_PX * math.cos(robot.theta)))
        ay = int(round(cy - _ARROW_LENGTH_PX * math.sin(robot.theta)))  # image y flipped
        ax = max(0, min(w - 1, ax))
        ay = max(0, min(h - 1, ay))
        cv2.arrowedLine(image, (cx, cy), (ax, ay), color, 2, tipLength=0.3)

    if robot.goal is not None:
        gx, gy = world_to_pixel(robot.goal, calibration.homography)
        gx = max(0, min(w - 1, gx))
        gy = max(0, min(h - 1, gy))
        cv2.circle(image, (gx, gy), _GOAL_RADIUS_PX, color, 2)
        cv2.drawMarker(image, (gx, gy), color, cv2.MARKER_CROSS, _GOAL_RADIUS_PX * 2, 1)


def render_annotated_frame(
    image: np.ndarray,
    scene_state: SceneState,
    calibration: CalibrationArtifact,
    style: Mapping[str, object] | None = None,
) -> np.ndarray:
    annotated = image.copy()
    for robot in scene_state.robots:
        color = status_to_color(robot.status)
        draw_robot_overlay(annotated, robot, color, calibration)
    return annotated

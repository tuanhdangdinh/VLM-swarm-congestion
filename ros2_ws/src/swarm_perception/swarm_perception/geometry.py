from __future__ import annotations

import math

import numpy as np


def pixel_to_world(
    pixel: tuple[float, float],
    homography: np.ndarray,
) -> tuple[float, float]:
    uv = np.array([pixel[0], pixel[1], 1.0], dtype=np.float64)
    xyw = homography @ uv
    xyw /= xyw[2]
    return float(xyw[0]), float(xyw[1])


def world_to_pixel(
    world_point: tuple[float, float],
    homography: np.ndarray,
) -> tuple[int, int]:
    H_inv = np.linalg.inv(homography)
    xy = np.array([world_point[0], world_point[1], 1.0], dtype=np.float64)
    uvw = H_inv @ xy
    uvw /= uvw[2]
    return int(round(float(uvw[0]))), int(round(float(uvw[1])))


def pixels_to_world(
    pixels: np.ndarray,
    homography: np.ndarray,
) -> np.ndarray:
    """Transform (N, 2) pixel array to (N, 2) world array via homography."""
    n = pixels.shape[0]
    ones = np.ones((n, 1), dtype=np.float64)
    uvs = np.hstack([pixels.astype(np.float64), ones])  # (N, 3)
    xyw = (homography @ uvs.T).T                         # (N, 3)
    xyw /= xyw[:, 2:3]
    return xyw[:, :2]


def estimate_marker_heading(corner_world: np.ndarray) -> float:
    """Return heading theta (radians) from ordered world-frame ArUco corners.

    Corner order: [TL, TR, BR, BL] (OpenCV ArUco convention after homography).
    The robot faces toward the top edge, so the heading vector is:
        dv = top_midpoint − bottom_midpoint
    where top_midpoint  = (corners[0] + corners[1]) / 2
          bottom_midpoint = (corners[3] + corners[2]) / 2
    """
    top_mid = (corner_world[0] + corner_world[1]) / 2.0
    bottom_mid = (corner_world[3] + corner_world[2]) / 2.0
    dv = top_mid - bottom_mid
    return math.atan2(float(dv[1]), float(dv[0]))

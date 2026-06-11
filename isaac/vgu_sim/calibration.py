"""Analytic camera calibration derived from the live CameraConfig.

Pure math: no Isaac (`omni`/`pxr`) and no `swarm_perception` imports, so this
runs and is fully unit-testable on any host (e.g. macOS).
"""
from __future__ import annotations

import numpy as np

from isaac.vgu_sim.config import CameraConfig


def camera_intrinsics(config: CameraConfig) -> np.ndarray:
    """Build the 3x3 pinhole intrinsics matrix from the camera config.

    Args:
        config: Overhead camera configuration.

    Returns:
        The 3x3 intrinsics matrix `K`.
    """
    fx = config.focal_length_mm / config.horizontal_aperture_mm * config.width
    fy = config.focal_length_mm / config.vertical_aperture_mm * config.height
    cx = config.width / 2.0
    cy = config.height / 2.0
    return np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)

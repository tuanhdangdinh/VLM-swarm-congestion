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


def _quat_to_rotation_matrix(quat_wxyz: tuple[float, float, float, float]) -> np.ndarray:
    """Convert a (w, x, y, z) unit quaternion to a 3x3 rotation matrix.

    The rotation maps camera-local axes into world axes (camera-to-world).
    """
    w, x, y, z = quat_wxyz
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def pixel_to_world_homography(config: CameraConfig) -> np.ndarray:
    """Compute the pixel->world (ground plane z=0) homography for the camera.

    Uses the full projective model so a tilted mount (non-identity
    `orientation_quat_wxyz`) yields a valid homography; for the default nadir
    pose it reduces to the closed-form overhead mapping.

    Args:
        config: Overhead camera configuration.

    Returns:
        The 3x3 homography `H` mapping pixel `(u, v, 1)` to world `(X, Y, 1)`.
    """
    k = camera_intrinsics(config)
    r_cw = _quat_to_rotation_matrix(config.orientation_quat_wxyz)
    r_wc = r_cw.T
    r_flip = np.diag([1.0, -1.0, -1.0])  # USD camera coords -> OpenCV coords
    m = k @ r_flip @ r_wc
    cam_center = np.array(config.position_m, dtype=np.float64)
    h_w2p = np.column_stack([m[:, 0], m[:, 1], -(m @ cam_center)])
    h_p2w = np.linalg.inv(h_w2p)
    return h_p2w / h_p2w[2, 2]

"""Analytic camera calibration derived from the live CameraConfig.

Pure math: no Isaac (`omni`/`pxr`) and no `swarm_perception` imports, so this
runs and is fully unit-testable on any host (e.g. macOS).
"""
from __future__ import annotations

import numpy as np

from isaac.vgu_sim.config import CameraConfig

# Height (m) of the ArUco marker plane above the floor. Source of truth is
# `isaac.vgu_sim.marker_asset.MARKER_HEIGHT_M`; duplicated here because
# marker_asset imports `pxr` at module level, which would break this module's
# "runs on any host without Isaac" guarantee. A parity test pins the two values.
MARKER_HEIGHT_M = 0.21


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


def pixel_to_world_homography(
    config: CameraConfig,
    plane_height_m: float = 0.0,
) -> np.ndarray:
    """Compute the pixel->world homography for the plane `z = plane_height_m`.

    Uses the full projective model so a tilted mount (non-identity
    `orientation_quat_wxyz`) yields a valid homography; for the default nadir
    pose it reduces to the closed-form overhead mapping.

    A homography is plane-specific: a point at height h projects like a ground
    point at radius scaled by H / (H - h), so mapping ArUco pixels through the
    z=0 homography over-estimates every radial coordinate. Pass the marker
    plane height (`MARKER_HEIGHT_M`) to remove that bias.

    Args:
        config: Overhead camera configuration.
        plane_height_m: Height in meters of the target world plane above the
            floor. `0.0` is the ground plane.

    Returns:
        The 3x3 homography `H` mapping pixel `(u, v, 1)` to the world point
        `(X, Y, 1)` that lies on the plane `z = plane_height_m`.
    """
    k = camera_intrinsics(config)
    r_cw = _quat_to_rotation_matrix(config.orientation_quat_wxyz)
    r_wc = r_cw.T
    r_flip = np.diag([1.0, -1.0, -1.0])  # USD camera coords -> OpenCV coords
    m = k @ r_flip @ r_wc
    # Translating the world down by plane_height_m puts the target plane at
    # z = 0 without changing orientation or the returned (X, Y), so the whole
    # plane change reduces to lowering the camera centre by that amount.
    cam_center = np.array(config.position_m, dtype=np.float64) - np.array(
        [0.0, 0.0, plane_height_m], dtype=np.float64
    )
    h_w2p = np.column_stack([m[:, 0], m[:, 1], -(m @ cam_center)])
    h_p2w = np.linalg.inv(h_w2p)
    return h_p2w / h_p2w[2, 2]


# Analytic calibration is derived, not captured, so it carries a fixed
# timestamp sentinel. This keeps regenerated calibration.yaml byte-stable.
ANALYTIC_CREATED_AT = 0.0


def build_calibration_dict(
    config: CameraConfig,
    plane_height_m: float = MARKER_HEIGHT_M,
) -> dict[str, object]:
    """Build a YAML-serializable calibration mapping for `swarm_perception`.

    The returned dict matches the schema consumed by
    `swarm_perception.calibration.load_calibration`. The homography targets the
    ArUco marker plane by default, because M1 feeds it marker pixels.

    Args:
        config: Overhead camera configuration.
        plane_height_m: Height in meters of the plane the homography maps onto.

    Returns:
        Mapping with intrinsics, distortion, homography, image_size, source_id,
        created_at, and plane_height_m.
    """
    k = camera_intrinsics(config)
    h_mat = pixel_to_world_homography(config, plane_height_m)
    return {
        "intrinsics": k.tolist(),
        "distortion": [0.0, 0.0, 0.0, 0.0, 0.0],
        "homography": h_mat.tolist(),
        "image_size": [config.width, config.height],
        "source_id": "isaac_sim",
        "created_at": ANALYTIC_CREATED_AT,
        # Self-describing artifact: consumers can tell which plane the
        # homography was solved for. load_calibration ignores extra keys.
        "plane_height_m": plane_height_m,
    }

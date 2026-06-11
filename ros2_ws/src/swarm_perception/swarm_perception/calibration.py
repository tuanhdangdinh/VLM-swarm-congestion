from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import yaml

from swarm_perception.frame_source import CalibrationError
from swarm_perception.models import CalibrationArtifact


def load_calibration(path: str | Path) -> CalibrationArtifact:
    path = Path(path)
    if not path.exists():
        raise CalibrationError(f"Calibration file not found: {path}")
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise CalibrationError(
            f"Calibration must be a YAML mapping; got {type(data).__name__} in {path}"
        )
    required = {"intrinsics", "distortion", "homography", "image_size", "source_id", "created_at"}
    missing = required - set(data.keys())
    if missing:
        raise CalibrationError(f"Calibration missing fields: {missing}")
    try:
        return CalibrationArtifact(
            intrinsics=np.array(data["intrinsics"], dtype=np.float64),
            distortion=np.array(data["distortion"], dtype=np.float64),
            homography=np.array(data["homography"], dtype=np.float64),
            image_size=(int(data["image_size"][0]), int(data["image_size"][1])),
            source_id=str(data["source_id"]),
            created_at=float(data["created_at"]),
        )
    except (CalibrationError, ValueError):
        raise
    except Exception as exc:
        raise CalibrationError(f"Invalid calibration data: {exc}") from exc


def save_calibration(artifact: CalibrationArtifact, path: str | Path) -> None:
    path = Path(path)
    data = {
        "intrinsics": artifact.intrinsics.tolist(),
        "distortion": artifact.distortion.tolist(),
        "homography": artifact.homography.tolist(),
        "image_size": list(artifact.image_size),
        "source_id": artifact.source_id,
        "created_at": artifact.created_at,
    }
    with path.open("w") as f:
        yaml.safe_dump(data, f)


def calibrate_intrinsics_from_checkerboard(
    image_paths: Sequence[str | Path],
    board_size: tuple[int, int],
    square_size_m: float,
) -> tuple[np.ndarray, np.ndarray, float]:
    import cv2

    obj_pts: list[np.ndarray] = []
    img_pts: list[np.ndarray] = []
    cols, rows = board_size
    objp = np.zeros((rows * cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * square_size_m

    image_size: tuple[int, int] | None = None
    for p in image_paths:
        img = cv2.imread(str(p))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, board_size)
        if not ret:
            continue
        if image_size is None:
            image_size = (gray.shape[1], gray.shape[0])
        obj_pts.append(objp)
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        img_pts.append(corners_refined)

    if not obj_pts or image_size is None:
        raise CalibrationError("No valid checkerboard frames found.")

    ret, K, dist, _, _ = cv2.calibrateCamera(obj_pts, img_pts, image_size, None, None)
    return K.astype(np.float64), dist.astype(np.float64), float(ret)


def estimate_homography(
    pixel_points: np.ndarray,
    world_points: np.ndarray,
) -> np.ndarray:
    import cv2

    if len(pixel_points) < 4:
        raise CalibrationError("At least 4 point correspondences required.")
    H, _ = cv2.findHomography(
        pixel_points.astype(np.float32),
        world_points.astype(np.float32),
    )
    if H is None:
        raise CalibrationError("cv2.findHomography returned None; check input points.")
    return H.astype(np.float64)


def undistort_frame(image: np.ndarray, calibration: CalibrationArtifact) -> np.ndarray:
    import cv2

    return cv2.undistort(image, calibration.intrinsics, calibration.distortion)

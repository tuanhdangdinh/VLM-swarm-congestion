from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np

from swarm_perception.geometry import estimate_marker_heading, pixels_to_world
from swarm_perception.models import CalibrationArtifact, MarkerDetection

logger = logging.getLogger(__name__)

_ARUCO_DICT_NAMES: dict[str, int] = {}


def _aruco_dict_const(name: str) -> int:
    import cv2

    if not _ARUCO_DICT_NAMES:
        _ARUCO_DICT_NAMES.update(
            {
                "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
                "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
                "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
                "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
                "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
            }
        )
    if name not in _ARUCO_DICT_NAMES:
        supported = ", ".join(sorted(_ARUCO_DICT_NAMES))
        raise ValueError(f"Unknown ArUco dictionary name: {name!r}. Supported: {supported}")
    return _ARUCO_DICT_NAMES[name]


def validate_marker_dictionary(name: str) -> None:
    """Raise ValueError if `name` is not a supported ArUco dictionary.

    Call this once at node/config init so a bad marker_dictionary fails fast
    instead of raising on every frame deep inside detection.
    """
    _aruco_dict_const(name)


def _make_aruco_dict(dictionary_name: str):
    import cv2

    const = _aruco_dict_const(dictionary_name)
    if hasattr(cv2.aruco, "getPredefinedDictionary"):
        return cv2.aruco.getPredefinedDictionary(const)
    return cv2.aruco.Dictionary_get(const)  # type: ignore[attr-defined]


def _make_detector_params(params_override: dict[str, object] | None):
    import cv2

    if hasattr(cv2.aruco, "DetectorParameters"):
        params = cv2.aruco.DetectorParameters()
    else:
        params = cv2.aruco.DetectorParameters_create()  # type: ignore[attr-defined]
    if params_override:
        for k, v in params_override.items():
            setattr(params, k, v)
    return params


def detect_aruco_markers(
    image: np.ndarray,
    dictionary_name: str = "DICT_4X4_50",
    detector_params: dict[str, object] | None = None,
) -> tuple[list[int], list[np.ndarray]]:
    """Detect ArUco markers; return (marker_ids, corner_arrays each shaped (4,2))."""
    import cv2

    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image
    aruco_dict = _make_aruco_dict(dictionary_name)
    params = _make_detector_params(detector_params)

    if hasattr(cv2.aruco, "ArucoDetector"):
        detector = cv2.aruco.ArucoDetector(aruco_dict, params)
        corners, ids, _ = detector.detectMarkers(gray)
    else:
        corners, ids, _ = cv2.aruco.detectMarkers(  # type: ignore[attr-defined]
            gray, aruco_dict, parameters=params
        )

    if ids is None or len(ids) == 0:
        return [], []

    ids_flat = [int(i[0]) for i in ids]
    # OpenCV returns corners as list of (1,4,2) arrays; squeeze to (4,2)
    corners_sq = [c.squeeze(axis=0).astype(np.float64) for c in corners]
    return ids_flat, corners_sq


def build_marker_detections(
    marker_ids: Sequence[int],
    marker_corners: Sequence[np.ndarray],
    calibration: CalibrationArtifact,
) -> list[MarkerDetection]:
    """Convert raw ArUco output to world-frame MarkerDetection objects."""
    detections: list[MarkerDetection] = []
    for mid, corners_px in zip(marker_ids, marker_corners):
        corners_px = np.array(corners_px, dtype=np.float64).reshape(4, 2)
        center_px = corners_px.mean(axis=0)
        try:
            corners_world = pixels_to_world(corners_px, calibration.homography)
            center_world = corners_world.mean(axis=0)
            theta = estimate_marker_heading(corners_world)
        except Exception as exc:
            logger.warning("Dropping malformed marker %d: %s", mid, exc)
            continue
        detections.append(
            MarkerDetection(
                marker_id=int(mid),
                corner_pixels=corners_px,
                center_pixel=(float(center_px[0]), float(center_px[1])),
                center_world=(float(center_world[0]), float(center_world[1])),
                theta=theta,
                confidence=1.0,
            )
        )
    return detections


def filter_duplicate_detections(
    detections: Sequence[MarkerDetection],
) -> list[MarkerDetection]:
    """Keep the highest-confidence detection per marker ID (first-seen as tiebreaker)."""
    seen: dict[int, MarkerDetection] = {}
    for det in detections:
        if det.marker_id not in seen or det.confidence > seen[det.marker_id].confidence:
            seen[det.marker_id] = det
    return list(seen.values())

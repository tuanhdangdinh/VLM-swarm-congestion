from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from swarm_perception.annotation import render_annotated_frame
from swarm_perception.calibration import undistort_frame
from swarm_perception.detection import (
    build_marker_detections,
    detect_aruco_markers,
    filter_duplicate_detections,
)
from swarm_perception.models import CalibrationArtifact, Frame, SceneState
from swarm_perception.state_estimator import StateEstimator


def process_frame(
    frame: Frame,
    calibration: CalibrationArtifact,
    state_estimator: StateEstimator,
    task_registry: Mapping[str, Mapping[str, object]] | None = None,
    detector_params: Mapping[str, object] | None = None,
    annotation_style: Mapping[str, object] | None = None,
    marker_dictionary: str = "DICT_4X4_50",
) -> tuple[SceneState, np.ndarray]:
    """Pure end-to-end perception pass; preferred unit/integration test entrypoint.

    `marker_dictionary` selects the ArUco dictionary (e.g. from config/aruco.yaml);
    it must match the dictionary used to generate the robots' markers.

    Does not publish to ROS2. Detection failures are represented in diagnostics,
    not raised as exceptions.
    """
    undistorted = undistort_frame(frame.image, calibration)
    marker_ids, marker_corners = detect_aruco_markers(
        undistorted,
        dictionary_name=marker_dictionary,
        detector_params=dict(detector_params) if detector_params else None,
    )
    detections = build_marker_detections(marker_ids, marker_corners, calibration)
    detections = filter_duplicate_detections(detections)
    # Robots named in the task registry are the ones we expect to see; report
    # any that go missing through diagnostics.
    expected_robot_ids = set(task_registry) if task_registry else set()
    scene_state = state_estimator.update(
        detections,
        frame.stamp,
        task_registry=task_registry,
        expected_robot_ids=expected_robot_ids,
        frame_id=frame.frame_id,
    )
    annotated = render_annotated_frame(undistorted, scene_state, calibration, style=annotation_style)
    return scene_state, annotated

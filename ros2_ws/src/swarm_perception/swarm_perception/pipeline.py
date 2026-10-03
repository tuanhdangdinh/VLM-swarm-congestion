from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from swarm_perception.annotation import MetricGridSpec, TrailHistory, render_annotated_frame
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
    expected_robot_ids: set[str] | None = None,
    detector_params: Mapping[str, object] | None = None,
    annotation_style: Mapping[str, object] | None = None,
    marker_dictionary: str = "DICT_4X4_50",
    *,
    metric_grid: MetricGridSpec | None = None,
    motion_trails: TrailHistory | None = None,
) -> tuple[SceneState, np.ndarray]:
    """Pure end-to-end perception pass; preferred unit/integration test entrypoint.

    `marker_dictionary` selects the ArUco dictionary (e.g. from config/aruco.yaml);
    it must match the dictionary used to generate the robots' markers.

    Does not publish to ROS2. Detection failures are represented in diagnostics,
    not raised as exceptions.

    `metric_grid` / `motion_trails` switch on the prompt-apparatus overlays
    (prereg-v2 rev 6, A/B conditions, default off). When either is on, the
    diagnostics gain `annotation_overlays` (and `metric_grid_spacing_m` for the
    grid) so M5 states in the prompt only what M1 actually drew; with both off
    the diagnostics and the annotated frame are byte-identical to before.
    """
    undistorted = undistort_frame(frame.image, calibration)
    marker_ids, marker_corners = detect_aruco_markers(
        undistorted,
        dictionary_name=marker_dictionary,
        detector_params=dict(detector_params) if detector_params else None,
    )
    detections = build_marker_detections(marker_ids, marker_corners, calibration)
    detections = filter_duplicate_detections(detections)
    # Robots named in the task registry are the primary allowlist. Standalone
    # M1/demo runs can pass an explicit allowlist when M5 has not published
    # /coordination/tasks yet. None means no allowlist; set() means filter all.
    allowed_ids = set(task_registry) if task_registry else expected_robot_ids
    scene_state = state_estimator.update(
        detections,
        frame.stamp,
        task_registry=task_registry,
        expected_robot_ids=allowed_ids,
        frame_id=frame.frame_id,
    )
    if motion_trails is not None:
        motion_trails.update(scene_state)
    annotated = render_annotated_frame(
        undistorted,
        scene_state,
        calibration,
        style=annotation_style,
        metric_grid=metric_grid,
        motion_trails=motion_trails,
    )
    overlays = [
        name
        for name, enabled in (
            ("metric_grid", metric_grid is not None),
            ("motion_trails", motion_trails is not None),
        )
        if enabled
    ]
    if overlays:
        diagnostics = {**scene_state.diagnostics, "annotation_overlays": overlays}
        if metric_grid is not None:
            diagnostics["metric_grid_spacing_m"] = metric_grid.spacing_m
        scene_state = scene_state.model_copy(update={"diagnostics": diagnostics})
    return scene_state, annotated

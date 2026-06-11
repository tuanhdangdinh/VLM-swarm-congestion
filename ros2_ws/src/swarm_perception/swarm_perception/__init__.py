"""ROS2 perception package — M1 Perception & Robot ID Tracking."""
from swarm_perception.frame_source import CalibrationError, FrameSource, FrameSourceTimeoutError
from swarm_perception.geometry import (
    estimate_marker_heading,
    pixel_to_world,
    pixels_to_world,
    world_to_pixel,
)
from swarm_perception.models import (
    CalibrationArtifact,
    Frame,
    MarkerDetection,
    RobotState,
    SceneState,
    scene_state_to_json_dict,
)
from swarm_perception.pipeline import process_frame
from swarm_perception.state_estimator import (
    StateEstimator,
    build_scene_diagnostics,
    classify_motion_status,
    estimate_velocity,
    low_pass_filter,
)

__all__ = [
    "CalibrationArtifact",
    "CalibrationError",
    "Frame",
    "FrameSource",
    "FrameSourceTimeoutError",
    "MarkerDetection",
    "RobotState",
    "SceneState",
    "StateEstimator",
    "build_scene_diagnostics",
    "classify_motion_status",
    "estimate_marker_heading",
    "estimate_velocity",
    "low_pass_filter",
    "pixel_to_world",
    "pixels_to_world",
    "process_frame",
    "scene_state_to_json_dict",
    "world_to_pixel",
]

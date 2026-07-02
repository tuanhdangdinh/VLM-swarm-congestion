#!/usr/bin/env python3
"""Smoke test for the swarm_perception package.

This intentionally avoids ROS 2 runtime setup. It exercises the pure perception
path and ROS-adjacent publisher helpers that can run in a plain Python process.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
PERCEPTION_SRC = REPO_ROOT / "ros2_ws" / "src" / "swarm_perception"
CALIBRATION_PATH = PERCEPTION_SRC / "config" / "calibration.yaml"

if str(PERCEPTION_SRC) not in sys.path:
    sys.path.insert(0, str(PERCEPTION_SRC))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def marker_detection(marker_id: int, x: float, y: float = 0.0):
    from swarm_perception.models import MarkerDetection

    corners = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    return MarkerDetection(
        marker_id=marker_id,
        corner_pixels=corners,
        center_pixel=(x, y),
        center_world=(x, y),
        theta=0.0,
        confidence=1.0,
    )


class FakeStamp:
    sec = 0
    nanosec = 0


class FakeHeader:
    def __init__(self) -> None:
        self.stamp = FakeStamp()
        self.frame_id = ""


class FakeImageMsg:
    def __init__(self) -> None:
        self.header = FakeHeader()


class FakeBridge:
    def __init__(self) -> None:
        self.last_image = None
        self.last_encoding = None

    def cv2_to_imgmsg(self, image, encoding):
        self.last_image = image
        self.last_encoding = encoding
        return FakeImageMsg()


class FakePublisher:
    def __init__(self) -> None:
        self.published = []

    def publish(self, msg) -> None:
        self.published.append(msg)


def smoke_calibration_and_dictionary() -> None:
    from swarm_perception.calibration import load_calibration
    from swarm_perception.detection import validate_marker_dictionary

    calibration = load_calibration(CALIBRATION_PATH)
    check(calibration.homography.shape == (3, 3), "calibration homography must be 3x3")
    check(calibration.intrinsics.shape == (3, 3), "calibration intrinsics must be 3x3")

    validate_marker_dictionary("DICT_4X4_50")
    try:
        validate_marker_dictionary("DICT_NOT_REAL")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid marker dictionary should raise ValueError")


def smoke_blank_frame_pipeline() -> None:
    from swarm_perception.calibration import load_calibration
    from swarm_perception.models import Frame, scene_state_to_json_dict
    from swarm_perception.pipeline import process_frame
    from swarm_perception.state_estimator import StateEstimator

    calibration = load_calibration(CALIBRATION_PATH)
    frame = Frame(
        image=np.zeros((64, 64, 3), dtype=np.uint8),
        stamp=1.25,
        frame_id="overhead_camera",
        source_id=calibration.source_id,
    )
    registry = {"robot_1": {"task": "deliver", "goal": {"x": 1.0, "y": 2.0}}}

    scene_state, annotated = process_frame(
        frame,
        calibration,
        StateEstimator(velocity_alpha=1.0),
        task_registry=registry,
        marker_dictionary="DICT_4X4_50",
    )

    check(scene_state.stamp == frame.stamp, "scene stamp should match frame stamp")
    check(scene_state.frame_id == frame.frame_id, "scene frame_id should match frame frame_id")
    check(scene_state.robots == [], "blank frame should produce no robot states")
    check(scene_state.diagnostics["markers_detected"] == 0, "blank frame should detect no markers")
    check(
        scene_state.diagnostics["ids_missing"] == ["robot_1"],
        "registry robot should be reported missing",
    )
    check(scene_state.diagnostics["dropped_frame"] is False, "blank frame is not dropped")
    check(annotated.shape == frame.image.shape, "annotated image should preserve frame shape")
    json.dumps(scene_state_to_json_dict(scene_state))


def smoke_late_frame_handling() -> None:
    from swarm_perception.state_estimator import StateEstimator

    estimator = StateEstimator(velocity_alpha=1.0)
    estimator.update([marker_detection(0, 0.0)], stamp=10.0)
    late_state = estimator.update([marker_detection(0, 5.0)], stamp=9.0)

    check(late_state.stamp == 9.0, "late state should retain late frame stamp")
    check(late_state.robots == [], "late state should suppress carried-forward robots")
    check(late_state.diagnostics["dropped_frame"] is True, "late frame should be flagged dropped")

    next_state = estimator.update([marker_detection(0, 0.01)], stamp=10.1)
    check(len(next_state.robots) == 1, "next in-order frame should produce robot state")
    check(abs(next_state.robots[0].linear_velocity - 0.1) < 1e-6, "late frame corrupted velocity")


def smoke_annotated_frame_publisher() -> None:
    from swarm_perception.perception_node import _split_stamp, publish_annotated_frame

    check(_split_stamp(1.9999999999) == (2, 0), "stamp split should normalize nanosecond carry")

    publisher = FakePublisher()
    bridge = FakeBridge()
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    publish_annotated_frame(publisher, bridge, image, stamp=12.5, frame_id="overhead_camera")

    check(len(publisher.published) == 1, "annotated publisher should publish exactly one message")
    check(bridge.last_image is image, "annotated publisher should encode image bytes")
    check(bridge.last_encoding == "rgb8", "annotated publisher should use rgb8 encoding")
    msg = publisher.published[0]
    check(msg.header.frame_id == "overhead_camera", "annotated frame_id should be preserved")
    check((msg.header.stamp.sec, msg.header.stamp.nanosec) == (12, 500_000_000), "bad stamp")


def main() -> int:
    smoke_calibration_and_dictionary()
    smoke_blank_frame_pipeline()
    smoke_late_frame_handling()
    smoke_annotated_frame_publisher()
    print("swarm_perception smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping

import numpy as np

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String as RosString
    _HAS_ROS2 = True
except ImportError:
    rclpy = None
    Node = object
    RosString = None
    _HAS_ROS2 = False

from swarm_perception.calibration import load_calibration
from swarm_perception.detection import validate_marker_dictionary
from swarm_perception.models import Frame, SceneState, scene_state_to_json_dict
from swarm_perception.pipeline import process_frame
from swarm_perception.state_estimator import StateEstimator

logger = logging.getLogger(__name__)


class PerceptionNode(Node):
    """ROS2 node: subscribes to camera frames, runs the M1 perception pipeline,
    publishes SceneState and diagnostics as JSON strings."""

    def __init__(self) -> None:
        super().__init__("perception_node")

        # Empty default → resolve the calibration installed with the package, so
        # `ros2 run swarm_perception perception_node` works without parameters and
        # is not CWD-relative. Override with the calibration_path parameter.
        self.declare_parameter("calibration_path", "")
        self.declare_parameter("image_topic", "/camera/image_raw")
        self.declare_parameter("marker_dictionary", "DICT_4X4_50")
        self.declare_parameter("stopped_threshold_mps", 0.01)
        self.declare_parameter("slow_threshold_mps", 0.05)
        self.declare_parameter("stale_after_sec", 1.0)
        self.declare_parameter("velocity_alpha", 0.3)

        cal_path = self.get_parameter("calibration_path").value
        if not cal_path:
            cal_path = self._default_calibration_path()
        self._calibration = load_calibration(cal_path)

        self._marker_dictionary = self.get_parameter("marker_dictionary").value
        # Fail fast on a bad dictionary instead of raising on every frame inside
        # detection (where _on_image_msg would swallow it and publish nothing).
        validate_marker_dictionary(self._marker_dictionary)
        self.get_logger().info(f"Using ArUco dictionary: {self._marker_dictionary}")

        # frame_id here is only the fallback when a Frame carries no frame_id;
        # process_frame passes the actual image frame_id through to the estimator.
        self._estimator = StateEstimator(
            stopped_threshold_mps=self.get_parameter("stopped_threshold_mps").value,
            slow_threshold_mps=self.get_parameter("slow_threshold_mps").value,
            stale_after_sec=self.get_parameter("stale_after_sec").value,
            velocity_alpha=self.get_parameter("velocity_alpha").value,
            frame_id="overhead_camera",
        )

        self._task_registry: dict[str, Mapping[str, object]] = {}

        self._state_pub = self.create_publisher(RosString, "/perception/scene_state", 10)
        self._diag_pub = self.create_publisher(RosString, "/perception/status", 10)
        self._task_sub = self.create_subscription(
            RosString, "/coordination/tasks", self._on_task_registry, 10
        )

        # Annotated-frame publishing requires cv_bridge + sensor_msgs/Image; left
        # as None when those are unavailable so on_frame() can skip it cleanly.
        self._bridge = None
        self._annotated_pub = None

        image_topic = self.get_parameter("image_topic").value
        try:
            from cv_bridge import CvBridge
            from sensor_msgs.msg import Image as RosImage

            self._bridge = CvBridge()
            self._annotated_pub = self.create_publisher(
                RosImage, "/perception/annotated_frame", 10
            )
            self._img_sub = self.create_subscription(
                RosImage, image_topic, self._on_image_msg, 10
            )
            self.get_logger().info(f"Subscribed to {image_topic}")
        except ImportError:
            self.get_logger().warning(
                "cv_bridge unavailable; image subscription and annotated_frame "
                "publishing disabled."
            )

        self.get_logger().info("PerceptionNode started.")

    @staticmethod
    def _default_calibration_path() -> str:
        """Resolve the calibration.yaml installed in the package share directory."""
        from ament_index_python.packages import get_package_share_directory

        return os.path.join(
            get_package_share_directory("swarm_perception"), "config", "calibration.yaml"
        )

    def _on_task_registry(self, msg) -> None:
        try:
            parsed = json.loads(msg.data)
        except json.JSONDecodeError as exc:
            self.get_logger().error(f"Bad task registry JSON: {exc}")
            return
        if not isinstance(parsed, dict):
            self.get_logger().error(
                f"Task registry must be a JSON object keyed by robot_id; got {type(parsed).__name__}"
            )
            return
        # Drop entries whose value is not an object so downstream registry.get()
        # always yields a mapping.
        cleaned: dict[str, Mapping[str, object]] = {}
        for robot_id, entry in parsed.items():
            if isinstance(entry, dict):
                cleaned[robot_id] = entry
            else:
                self.get_logger().warning(
                    f"Ignoring task registry entry for {robot_id!r}: expected object, "
                    f"got {type(entry).__name__}"
                )
        self._task_registry = cleaned

    def _on_image_msg(self, msg) -> None:
        try:
            cv_image = self._bridge.imgmsg_to_cv2(msg, desired_encoding="rgb8")
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            frame = Frame(
                image=cv_image,
                stamp=stamp,
                frame_id=msg.header.frame_id or "overhead_camera",
                source_id=self._calibration.source_id,
            )
            self.on_frame(frame)
        except Exception as exc:
            self.get_logger().error(f"Frame processing error: {exc}")

    def on_frame(self, frame: Frame) -> None:
        """Perception callback; also the integration test entrypoint."""
        scene_state, annotated = process_frame(
            frame,
            self._calibration,
            self._estimator,
            self._task_registry,
            marker_dictionary=self._marker_dictionary,
        )
        publish_scene_state(self._state_pub, scene_state)
        publish_diagnostics(self._diag_pub, scene_state.diagnostics, scene_state.stamp)
        if self._annotated_pub is not None and self._bridge is not None:
            publish_annotated_frame(
                self._annotated_pub,
                self._bridge,
                annotated,
                scene_state.stamp,
                scene_state.frame_id,
            )


def publish_scene_state(publisher, scene_state: SceneState) -> None:
    if publisher is None:
        return
    msg = RosString()
    msg.data = json.dumps(scene_state_to_json_dict(scene_state))
    publisher.publish(msg)


def publish_annotated_frame(
    publisher,
    bridge,
    annotated_image: np.ndarray,
    stamp: float,
    frame_id: str,
) -> None:
    """Publish the annotated RGB frame as a sensor_msgs/Image.

    `bridge` is a cv_bridge.CvBridge used to encode the image bytes. The float
    `stamp` is split into the message header's sec/nanosec fields so M2 can
    align the visual observation with the matching SceneState.
    """
    if publisher is None or bridge is None:
        return
    msg = bridge.cv2_to_imgmsg(annotated_image, encoding="rgb8")
    msg.header.frame_id = frame_id
    sec, nanosec = _split_stamp(stamp)
    msg.header.stamp.sec = sec
    msg.header.stamp.nanosec = nanosec
    publisher.publish(msg)


def _split_stamp(stamp: float) -> tuple[int, int]:
    """Split a float seconds stamp into (sec, nanosec) with nanosec in [0, 1e9).

    Computed via total nanoseconds so rounding can never yield nanosec == 1e9
    (e.g. stamp=1.9999999999 → (2, 0), not (1, 1000000000)).
    """
    total_ns = int(round(stamp * 1e9))
    return total_ns // 1_000_000_000, total_ns % 1_000_000_000


def publish_diagnostics(
    publisher,
    diagnostics: Mapping[str, object],
    stamp: float,
) -> None:
    if publisher is None:
        return
    msg = RosString()
    msg.data = json.dumps({"stamp": stamp, **diagnostics})
    publisher.publish(msg)


def main(args=None) -> None:
    if not _HAS_ROS2:
        raise SystemExit("rclpy is required to run PerceptionNode.")
    rclpy.init(args=args)
    node = PerceptionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

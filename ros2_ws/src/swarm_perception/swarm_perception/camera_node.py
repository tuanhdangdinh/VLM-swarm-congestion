"""ROS2 camera source node; publishes raw RGB frames from a hardware camera or
video file on a timer.

In Isaac Sim deployments this node is typically replaced by the Isaac ROS2
bridge, which publishes directly to the image topic that PerceptionNode
subscribes to. This node exists so a launched stack has a real frame source for
hardware / video-file testing without an external bridge.
"""
from __future__ import annotations

try:
    import rclpy
    from rclpy.node import Node
    _HAS_ROS2 = True
except ImportError:
    rclpy = None
    Node = object
    _HAS_ROS2 = False


class CameraNode(Node):
    def __init__(self) -> None:
        super().__init__("camera_node")
        self.declare_parameter("device", "0")
        self.declare_parameter("fps", 30)
        self.declare_parameter("image_topic", "/camera/image_raw")
        self.declare_parameter("frame_id", "overhead_camera")

        import cv2
        from cv_bridge import CvBridge
        from sensor_msgs.msg import Image as RosImage

        self._cv2 = cv2
        self._bridge = CvBridge()
        self._frame_id = self.get_parameter("frame_id").value

        topic = self.get_parameter("image_topic").value
        self._pub = self.create_publisher(RosImage, topic, 10)

        # device may be an integer camera index ("0") or a file/stream path.
        device_raw = str(self.get_parameter("device").value)
        device = int(device_raw) if device_raw.isdigit() else device_raw
        self._cap = cv2.VideoCapture(device)
        if not self._cap.isOpened():
            # Fail fast: a frame source that can't open should not leave a
            # silently-alive node that never publishes /camera/image_raw.
            self._cap.release()
            msg = f"Failed to open camera device: {device!r}"
            self.get_logger().error(msg)
            raise RuntimeError(msg)

        fps = max(1, int(self.get_parameter("fps").value))
        self._timer = self.create_timer(1.0 / fps, self._on_timer)
        self.get_logger().info(f"CameraNode publishing {device!r} -> {topic} at {fps} FPS.")

    def _on_timer(self) -> None:
        if self._cap is None or not self._cap.isOpened():
            return
        ok, bgr = self._cap.read()
        if not ok or bgr is None:
            self.get_logger().warning("Camera read failed; skipping frame.")
            return
        rgb = self._cv2.cvtColor(bgr, self._cv2.COLOR_BGR2RGB)
        msg = self._bridge.cv2_to_imgmsg(rgb, encoding="rgb8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id
        self._pub.publish(msg)

    def destroy_node(self) -> None:
        if getattr(self, "_cap", None) is not None:
            self._cap.release()
        super().destroy_node()


def main(args=None) -> None:
    if not _HAS_ROS2:
        raise SystemExit("rclpy is required to run CameraNode.")
    rclpy.init(args=args)
    node = CameraNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

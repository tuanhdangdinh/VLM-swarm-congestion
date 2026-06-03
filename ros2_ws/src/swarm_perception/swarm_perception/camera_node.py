try:
    import rclpy
    from rclpy.node import Node
except ImportError:  # Allows unit imports outside ROS2.
    rclpy = None
    Node = object


class CameraNode(Node):
    def __init__(self):
        super().__init__("camera_node")
        self.get_logger().info("Camera node scaffold started.")


def main(args=None):
    if rclpy is None:
        raise SystemExit("rclpy is required to run this node.")
    rclpy.init(args=args)
    node = CameraNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

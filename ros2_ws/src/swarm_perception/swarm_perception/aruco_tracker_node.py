try:
    import rclpy
    from rclpy.node import Node
except ImportError:
    rclpy = None
    Node = object


class ArucoTrackerNode(Node):
    def __init__(self):
        super().__init__("aruco_tracker_node")
        self.get_logger().info("ArUco tracker node scaffold started.")


def main(args=None):
    if rclpy is None:
        raise SystemExit("rclpy is required to run this node.")
    rclpy.init(args=args)
    node = ArucoTrackerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

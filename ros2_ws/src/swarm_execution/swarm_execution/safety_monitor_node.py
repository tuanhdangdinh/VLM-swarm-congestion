try:
    import rclpy
    from rclpy.node import Node
except ImportError:
    rclpy = None
    Node = object


class SafetyMonitorNode(Node):
    def __init__(self):
        super().__init__("safety_monitor_node")
        self.get_logger().info("Safety monitor scaffold started.")


def main(args=None):
    if rclpy is None:
        raise SystemExit("rclpy is required to run this node.")
    rclpy.init(args=args)
    node = SafetyMonitorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

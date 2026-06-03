try:
    import rclpy
    from rclpy.node import Node
except ImportError:
    rclpy = None
    Node = object


class CoordinationClientNode(Node):
    def __init__(self):
        super().__init__("coordination_client_node")
        self.get_logger().info("Coordination client scaffold started.")


def main(args=None):
    if rclpy is None:
        raise SystemExit("rclpy is required to run this node.")
    rclpy.init(args=args)
    node = CoordinationClientNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

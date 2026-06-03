try:
    import rclpy
    from rclpy.node import Node
except ImportError:
    rclpy = None
    Node = object


class OrchestratorNode(Node):
    def __init__(self):
        super().__init__("orchestrator_node")
        self.get_logger().info("Orchestrator scaffold started.")


def main(args=None):
    if rclpy is None:
        raise SystemExit("rclpy is required to run this node.")
    rclpy.init(args=args)
    node = OrchestratorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

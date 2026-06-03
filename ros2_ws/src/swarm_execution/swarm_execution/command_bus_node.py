try:
    import rclpy
    from rclpy.node import Node
except ImportError:
    rclpy = None
    Node = object


class CommandBusNode(Node):
    def __init__(self):
        super().__init__("command_bus_node")
        self.get_logger().info("Command bus scaffold started.")


def main(args=None):
    if rclpy is None:
        raise SystemExit("rclpy is required to run this node.")
    rclpy.init(args=args)
    node = CommandBusNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

"""M4 coordination client: the continuous base-mission driver.

Keeps each robot navigating to its effective goal from M5's `/coordination/tasks`
registry, hands ownership to the command bus while a coordination command is in
flight, and resumes base navigation when the command resolves. The decision logic
is the ROS2-free `BaseMissionDriver`; this node only adapts topics to it and
issues Nav2 goals through `Nav2Adapter`.

See docs/specs/module4/phase3-closed-loop.md §6: without this driver nothing
issues the initial Nav2 goals (the standoff never forms) and a yielding robot
never resumes its goal after backing up.

Also subscribes to the safety monitor's `/safety/holds` so this driver's own
2 s retry loop does not immediately re-issue a goal the safety monitor just
cancelled — without that, the two nodes fight over the robot's Nav2 goal
indefinitely (see docs/specs/module4/safety-monitor.md §4).
"""
from __future__ import annotations

import json

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String
    from swarm_interfaces.msg import CoordinationCommand, CoordinationStatus
except ImportError:
    rclpy = None
    Node = object
    String = object
    CoordinationCommand = object
    CoordinationStatus = object


def _registry_qos() -> "QoSProfile":
    # Match M5's /coordination/tasks publisher (TRANSIENT_LOCAL + RELIABLE) so a
    # client that starts after M5 still receives the latched startup registry —
    # otherwise the initial navigate goals are never issued and the loop never
    # starts. Mirrors swarm_perception.perception_node._registry_qos.
    return QoSProfile(
        depth=1,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        reliability=ReliabilityPolicy.RELIABLE,
    )

from swarm_execution.base_mission import BaseMissionDriver
from swarm_execution.nav2_adapter import Nav2Adapter


class CoordinationClientNode(Node):
    # Re-issue any base goal Nav2 has not yet accepted. Recovers the startup race
    # where the registry arrives before Nav2's action servers are lifecycle-ACTIVE
    # (the registry is static after startup, so without this the rejected initial
    # goal would never be retried and robots would never move).
    RETRY_PERIOD_SEC = 2.0

    def __init__(self) -> None:
        super().__init__("coordination_client_node")
        self._adapter = Nav2Adapter(self)
        self._driver = BaseMissionDriver()
        self.create_subscription(
            String, "/coordination/tasks", self._on_registry, _registry_qos()
        )
        self.create_subscription(
            CoordinationCommand, "/coordination/commands", self._on_command, 10
        )
        self.create_subscription(
            CoordinationStatus, "/coordination/status", self._on_status, 10
        )
        self.create_subscription(String, "/safety/holds", self._on_holds, 10)
        self.create_timer(self.RETRY_PERIOD_SEC, self._on_retry)
        self.get_logger().info("Coordination client started.")

    def _on_registry(self, msg: String) -> None:
        try:
            registry = json.loads(msg.data)
        except (ValueError, TypeError) as exc:
            self.get_logger().warning(f"coordination/tasks parse failed: {exc}")
            return
        for robot_id, goal in self._driver.on_registry(registry):
            self._issue_navigate(robot_id, goal)

    def _on_command(self, msg: CoordinationCommand) -> None:
        if self._driver.on_command(msg.robot_id):
            # The command bus uses a separate Nav2Adapter, so cancel our own
            # navigate goal here to avoid two action goals fighting on this robot.
            self._adapter.cancel(msg.robot_id)

    def _on_status(self, msg: CoordinationStatus) -> None:
        for robot_id, goal in self._driver.on_status(msg.robot_id, msg.status):
            self.get_logger().info(f"resume base mission robot={robot_id} goal={goal}")
            self._issue_navigate(robot_id, goal)

    def _on_holds(self, msg: String) -> None:
        try:
            payload = json.loads(msg.data)
        except (ValueError, TypeError) as exc:
            self.get_logger().warning(f"safety/holds parse failed: {exc}")
            return
        self._driver.on_holds(set(payload.get("held", [])))

    def _on_retry(self) -> None:
        for robot_id, goal in self._driver.retry():
            self._issue_navigate(robot_id, goal)

    def _issue_navigate(self, robot_id: str, goal: tuple[float, float]) -> None:
        # The registry carries no target heading, so default yaw to 0.0; reaching
        # the goal position is what the mission requires.
        self._adapter.send_goal(
            robot_id,
            goal[0],
            goal[1],
            0.0,
            on_result=lambda status, _detail, rid=robot_id, g=goal: self._on_nav_result(
                rid, g, status
            ),
        )

    def _on_nav_result(
        self, robot_id: str, goal: tuple[float, float], status: str
    ) -> None:
        # "ACTIVE" = Nav2 accepted the goal; "FAILED"/"goal rejected" = it did not,
        # so forget it and let the retry timer re-send. A later "COMPLETED" (goal
        # reached) leaves the accepted goal in place — nothing to re-issue.
        if status == "ACTIVE":
            self._driver.on_goal_accepted(robot_id, goal)
        elif status == "FAILED":
            self._driver.on_goal_rejected(robot_id)


def main(args=None):
    if rclpy is None:
        raise SystemExit("rclpy is required to run this node.")
    rclpy.init(args=args)
    node = CoordinationClientNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

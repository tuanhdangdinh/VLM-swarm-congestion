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

Hand-off race guard (ROS parameter `handoff_race_guard`, default True; IB10
remedy validation run m4, docs/reports/2026-10-08-ib10-remedy-validation.md).
On top of the driver-side guard (`BaseMissionDriver`), this node cancels a
base goal that Nav2 accepted after the hand-off, cancelling only its own goal
handle. When the new command keeps the robot off Nav2 (`_NON_NAV2_ACTIONS`),
it also cancels the robot's controller `follow_path` goals, once at hand-off
and again at `CONTROLLER_STOP_FOLLOWUP_SEC` while the command still owns the
robot. This stops a FollowPath orphaned by a `navigate_to_pose` cancel (see
`Nav2Adapter.stop_controller`). Every guard action logs a line starting
`handoff guard:`.
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


# Actions under which the command bus never drives the robot through Nav2 (a
# raw-cmd_vel maneuver or a stationary hold). Under these, any FollowPath still
# running on the robot's controller is an orphan of a cancelled base goal and is
# stopped. Nav2-driven actions (navigate, reroute, ...) are excluded: the bus's
# own goal preempts the controller, and a follow_path cancel-all could kill it.
_NON_NAV2_ACTIONS = frozenset({"yield", "reverse", "wait", "temporary_wait", "stop"})


class CoordinationClientNode(Node):
    # Re-issue any base goal Nav2 has not yet accepted. Recovers the startup race
    # where the registry arrives before Nav2's action servers are lifecycle-ACTIVE
    # (the registry is static after startup, so without this the rejected initial
    # goal would never be retried and robots would never move).
    RETRY_PERIOD_SEC = 2.0
    # Repeat the hand-off controller stop at these node-clock delays while the
    # same command still owns the robot. A FollowPath request still in flight
    # when the first cancel-all arrives is accepted after it and would survive
    # that cancel.
    CONTROLLER_STOP_FOLLOWUP_SEC = (0.5, 1.5)
    # Class-level default so nodes built without __init__ (unit tests) keep the
    # shipped behaviour; __init__ overrides it from the ROS parameter.
    _handoff_guard = True

    def __init__(self) -> None:
        super().__init__("coordination_client_node")
        # Kill switch for the hand-off race guard (BaseMissionDriver docstring
        # and _on_command). False restores the pre-guard client exactly.
        self.declare_parameter("handoff_race_guard", True)
        self._handoff_guard = bool(self.get_parameter("handoff_race_guard").value)
        self._command_actions: dict[tuple[str, str], str] = {}
        self._adapter = Nav2Adapter(self)
        self._driver = BaseMissionDriver(handoff_guard=self._handoff_guard)
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
        # Reports base-goal arrival to M5 (command_id "base_mission"); the command
        # bus's own statuses keep their command ids, so the two never collide.
        self._status_pub = self.create_publisher(CoordinationStatus, "/coordination/status", 10)
        self.create_timer(self.RETRY_PERIOD_SEC, self._on_retry)
        self.get_logger().info(
            f"Coordination client started. handoff_race_guard={self._handoff_guard}"
        )

    def _on_registry(self, msg: String) -> None:
        try:
            registry = json.loads(msg.data)
        except (ValueError, TypeError) as exc:
            self.get_logger().warning(f"coordination/tasks parse failed: {exc}")
            return
        for robot_id, goal in self._driver.on_registry(registry):
            self._issue_navigate(robot_id, goal)
        self._log_driver_events()

    def _on_command(self, msg: CoordinationCommand) -> None:
        action = str(getattr(msg, "action", "") or "")
        if self._handoff_guard:
            self._command_actions[(msg.robot_id, msg.command_id)] = action
        if self._driver.on_command(msg.robot_id, msg.command_id):
            # The command bus uses a separate Nav2Adapter, so cancel our own
            # navigate goal here to avoid two action goals fighting on this robot.
            self._adapter.cancel(msg.robot_id)
            if self._handoff_guard and action in _NON_NAV2_ACTIONS:
                # The navigate cancel above (or the bus's own, a few hundred
                # ms earlier) can orphan a FollowPath on the controller; stop it.
                self._stop_controller(msg.robot_id, msg.command_id, action, "handover")
        self._log_driver_events()

    def _on_status(self, msg: CoordinationStatus) -> None:
        for robot_id, goal in self._driver.on_status(
            msg.robot_id, msg.command_id, msg.status
        ):
            self.get_logger().info(f"resume base mission robot={robot_id} goal={goal}")
            self._issue_navigate(robot_id, goal)
        if msg.status in ("COMPLETED", "FAILED"):
            self._command_actions.pop((msg.robot_id, msg.command_id), None)
        self._log_driver_events()

    def _sim_now(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _stop_controller(
        self, robot_id: str, command_id: str, action: str, reason: str
    ) -> None:
        """Cancel robot_id's controller FollowPath and schedule follow-up cancels.

        Args:
            robot_id: Robot handed to a non-Nav2 coordination command.
            command_id: The command that owns the robot.
            action: That command's action (for the log line).
            reason: `handover` (on_command), `late_accept` (a base goal
                accepted after the hand-off) or `followup` (a delayed repeat).
        """
        self._adapter.stop_controller(robot_id)
        self.get_logger().info(
            "handoff guard: controller stop "
            f"robot={robot_id} command={command_id} action={action} "
            f"reason={reason} sim_t={self._sim_now():.3f}"
        )
        if reason == "followup":
            return
        for delay_sec in self.CONTROLLER_STOP_FOLLOWUP_SEC:
            self._schedule_controller_followup(robot_id, command_id, action, delay_sec)

    def _schedule_controller_followup(
        self, robot_id: str, command_id: str, action: str, delay_sec: float
    ) -> None:
        timer_ref: dict = {}

        def _fire() -> None:
            timer = timer_ref["timer"]
            timer.cancel()
            self.destroy_timer(timer)
            # Only while the same command still owns the robot: after its
            # terminal the client itself may have resumed a base goal, whose
            # FollowPath a cancel-all here would kill.
            if self._driver.holds_command(robot_id, command_id):
                self._stop_controller(robot_id, command_id, action, "followup")

        timer_ref["timer"] = self.create_timer(delay_sec, _fire)

    def _log_driver_events(self) -> None:
        # Step-7b race guard: `BaseMissionDriver` queues log-worthy ownership
        # decisions (stale terminals, pending-command promotions) rather than
        # logging directly, since it stays ROS2-free. Drained after every
        # on_command/on_status call so nothing is lost between calls.
        for line in self._driver.drain_events():
            self.get_logger().info(line)

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
            if not self._driver.on_goal_accepted(robot_id, goal):
                # Hand-off guard: this base goal was sent before a coordination
                # command took the robot and accepted after it. Cancel only our
                # own handle (a cancel-all could hit the bus's goal).
                self._adapter.cancel_own_goal(robot_id)
                owner = self._driver.command_owner(robot_id)
                action = self._command_actions.get((robot_id, owner or ""), "")
                if owner is not None and action in _NON_NAV2_ACTIONS:
                    self._stop_controller(robot_id, owner, action, "late_accept")
            self._log_driver_events()
        elif status == "FAILED":
            self._driver.on_goal_rejected(robot_id)
        elif status == "COMPLETED":
            msg = CoordinationStatus()
            msg.command_id = "base_mission"
            msg.robot_id = robot_id
            msg.status = "COMPLETED"
            msg.detail = f"goal reached ({goal[0]:.2f}, {goal[1]:.2f})"
            self._status_pub.publish(msg)
            self.get_logger().info(f"base goal reached robot={robot_id} goal={goal}")


def main(args=None):
    if rclpy is None:
        raise SystemExit("rclpy is required to run this node.")
    rclpy.init(args=args)
    node = CoordinationClientNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

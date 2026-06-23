"""Action-client wrapper around per-robot Nav2 (M4 spec phase2-nav2-stack.md S7).

This is the ONLY component that talks to Nav2 directly. It does not publish
CoordinationStatus or talk to M5 -- that translation belongs to the command
bus (Phase 3, command-bus.md), per the spec's boundary rule.
"""
from __future__ import annotations

import math

try:
    import rclpy
    from geometry_msgs.msg import PoseStamped
    from nav2_msgs.action import FollowWaypoints, NavigateToPose
    from rclpy.action import ActionClient
    from rclpy.node import Node
except ImportError:
    # rclpy/nav2_msgs/geometry_msgs are unavailable in this dev environment and
    # in CI. Fall back to minimal stand-ins so this module stays importable
    # and unit-testable without a sourced ROS2 install; real message/action
    # classes are used whenever rclpy is present.
    rclpy = None
    ActionClient = object
    Node = object

    class _Point:
        def __init__(self) -> None:
            self.x = 0.0
            self.y = 0.0
            self.z = 0.0

    class _Quaternion:
        def __init__(self) -> None:
            self.x = 0.0
            self.y = 0.0
            self.z = 0.0
            self.w = 1.0

    class _Pose:
        def __init__(self) -> None:
            self.position = _Point()
            self.orientation = _Quaternion()

    class _Header:
        def __init__(self) -> None:
            self.frame_id = ""

    class PoseStamped:
        def __init__(self) -> None:
            self.header = _Header()
            self.pose = _Pose()

    class NavigateToPose:
        class Goal:
            def __init__(self) -> None:
                self.pose = PoseStamped()

    class FollowWaypoints:
        class Goal:
            def __init__(self) -> None:
                self.poses: list[PoseStamped] = []


class Nav2Adapter(Node):
    """Per-robot Nav2 action-client wrapper: send_goal, send_waypoints, cancel."""

    def __init__(self) -> None:
        super().__init__("nav2_adapter")
        # Named `_goal_clients`, not `_clients`: `rclpy.node.Node.__init__` already
        # owns a private `self._clients` list (its own service-client bookkeeping,
        # consumed by the executor's `node.clients` property). Naming this dict
        # `_clients` silently overwrote that list with our dict -- invisible until
        # an executor spins this node with a real action client and a subscription
        # both present, at which point `node.clients` (`yield from self._clients`)
        # yields our dict's *keys* (robot_id strings) instead of `Client` objects,
        # and the executor's `can_execute(entity)` crashes with
        # `AttributeError: 'str' object has no attribute '_executor_event'`. The
        # existing unit tests never caught this: they build the adapter via
        # `Nav2Adapter.__new__(Nav2Adapter)` to bypass `Node.__init__` entirely, so
        # the collision never occurred in that offline path.
        self._goal_clients: dict[str, ActionClient] = {}
        self._waypoint_clients: dict[str, ActionClient] = {}
        self._active_goals: dict[str, object] = {}

    def _make_client(self, robot_id: str, action_name: str) -> ActionClient:
        action_type = NavigateToPose if action_name == "navigate_to_pose" else FollowWaypoints
        return ActionClient(self, action_type, f"/{robot_id}/{action_name}")

    def send_goal(self, robot_id: str, x: float, y: float, yaw: float):
        """Send a NavigateToPose goal, pre-empting any active goal for robot_id."""
        if robot_id in self._active_goals:
            self._active_goals[robot_id].cancel_goal_async()

        client = self._goal_clients.setdefault(robot_id, self._make_client(robot_id, "navigate_to_pose"))
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.orientation.z, goal_msg.pose.pose.orientation.w = _yaw_to_quat_zw(yaw)

        future = client.send_goal_async(goal_msg)
        # `Future.result()` never blocks -- it returns whatever is currently set,
        # `None` if the future hasn't resolved yet. `send_goal_async` only queues
        # the request; nothing resolves it until this node is spun. The real
        # `rclpy` path spins here explicitly; the offline `rclpy is None` stand-in
        # (no ROS2 install) has no executor to spin, so the fake future in tests
        # already has its result set synchronously and this call is a no-op there.
        if rclpy is not None:
            rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)
        handle = future.result()
        self._active_goals[robot_id] = handle
        return handle

    def send_waypoints(self, robot_id: str, waypoints: list[tuple[float, float]]):
        """Send a FollowWaypoints goal for a route (M3 reroute/convoy)."""
        client = self._waypoint_clients.setdefault(
            robot_id, self._make_client(robot_id, "follow_waypoints")
        )
        goal_msg = FollowWaypoints.Goal()
        for x, y in waypoints:
            pose = _pose_at(x, y)
            goal_msg.poses.append(pose)
        future = client.send_goal_async(goal_msg)
        if rclpy is not None:
            rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)
        handle = future.result()
        self._active_goals[robot_id] = handle
        return handle

    def cancel(self, robot_id: str) -> None:
        """Cancel robot_id's active goal, if any. No-op if none is active."""
        handle = self._active_goals.get(robot_id)
        if handle is not None:
            handle.cancel_goal_async()


def _yaw_to_quat_zw(yaw: float) -> tuple[float, float]:
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def _pose_at(x: float, y: float) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = "map"
    pose.pose.position.x = x
    pose.pose.position.y = y
    return pose

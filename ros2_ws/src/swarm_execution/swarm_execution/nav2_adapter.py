"""Action-client wrapper around per-robot Nav2.

This is the execution-side boundary to Nav2. It intentionally hides ROS action
message construction from higher-level coordination code, so command bus logic
can stay focused on translating CoordinationCommand messages.
"""
from __future__ import annotations

import math
from collections.abc import Callable

try:
    from action_msgs.msg import GoalStatus
    import rclpy
    from builtin_interfaces.msg import Duration
    from geometry_msgs.msg import PoseStamped, Twist
    from nav2_msgs.action import BackUp, FollowWaypoints, NavigateToPose
    from rclpy.action import ActionClient
    from rclpy.node import Node
except ImportError:
    # Keep the module importable in non-ROS unit tests.
    rclpy = None
    ActionClient = object
    Node = object

    class GoalStatus:
        STATUS_SUCCEEDED = 4

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

    class Duration:
        def __init__(self, sec: int = 0, nanosec: int = 0) -> None:
            self.sec = sec
            self.nanosec = nanosec

    class BackUp:
        class Goal:
            def __init__(self) -> None:
                self.target = _Point()
                self.speed = 0.0
                self.time_allowance = Duration()


class Nav2Adapter(Node):
    """Per-robot Nav2 action-client wrapper: send_goal, send_waypoints, cancel."""

    def __init__(self, node: Node | None = None) -> None:
        if node is None:
            super().__init__("nav2_adapter")
            self._node = self
        else:
            self._node = node
        self._goal_clients: dict[str, ActionClient] = {}
        self._waypoint_clients: dict[str, ActionClient] = {}
        self._backup_clients: dict[str, ActionClient] = {}
        self._cancel_clients: dict[str, ActionClient] = {}
        self._active_goals: dict[str, object] = {}
        self._backup_pubs: dict[str, object] = {}
        self._backup_timers: dict[str, object] = {}

    def _make_client(self, robot_id: str, action_name: str) -> ActionClient:
        action_type = {
            "navigate_to_pose": NavigateToPose,
            "follow_waypoints": FollowWaypoints,
            "backup": BackUp,
        }[action_name]
        return ActionClient(self._node, action_type, f"/{robot_id}/{action_name}")

    def send_goal(
        self,
        robot_id: str,
        x: float,
        y: float,
        yaw: float,
        on_result: Callable[[str, str], None] | None = None,
    ):
        """Send a NavigateToPose goal, pre-empting any active goal for robot_id."""
        self.cancel(robot_id)
        client = self._goal_clients.setdefault(robot_id, self._make_client(robot_id, "navigate_to_pose"))
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)
        goal_msg.pose.pose.orientation.z, goal_msg.pose.pose.orientation.w = _yaw_to_quat_zw(yaw)

        future = client.send_goal_async(goal_msg)
        future.add_done_callback(
            lambda done, rid=robot_id, cb=on_result: self._on_goal_response(rid, done, cb)
        )
        return future

    def send_waypoints(
        self,
        robot_id: str,
        waypoints: list[tuple[float, float]],
        on_result: Callable[[str, str], None] | None = None,
    ):
        """Send a FollowWaypoints goal for a route."""
        self.cancel(robot_id)
        client = self._waypoint_clients.setdefault(
            robot_id, self._make_client(robot_id, "follow_waypoints")
        )
        goal_msg = FollowWaypoints.Goal()
        for x, y in waypoints:
            goal_msg.poses.append(_pose_at(x, y))
        future = client.send_goal_async(goal_msg)
        future.add_done_callback(
            lambda done, rid=robot_id, cb=on_result: self._on_goal_response(rid, done, cb)
        )
        return future

    def backup(
        self,
        robot_id: str,
        distance_m: float,
        speed_mps: float = 0.1,
        on_result: Callable[[str, str], None] | None = None,
    ):
        """Reverse the robot by `distance_m` by publishing directly to cmd_vel.

        Bypasses Nav2's BackUp action and the collision_monitor entirely. The
        collision_monitor's forward_stop polygon fires when the other robot is
        in front of the yielding robot — which is always the case in a head-on
        standoff — and kills the Nav2 BackUp behavior before it can open the
        gap. Publishing negative Twist directly to cmd_vel goes straight to the
        Isaac watchdog without passing through the collision_monitor.
        """
        self.cancel(robot_id)
        # Cancel any in-progress timer backup for this robot.
        old_timer = self._backup_timers.pop(robot_id, None)
        if old_timer is not None:
            try:
                old_timer.cancel()
            except Exception:
                pass

        pub = self._backup_pubs.get(robot_id)
        if pub is None:
            pub = self._node.create_publisher(Twist, f"/{robot_id}/cmd_vel", 10)
            self._backup_pubs[robot_id] = pub

        travel_sec = abs(distance_m) / speed_mps if speed_mps else 0.0
        deadline = self._node.get_clock().now().nanoseconds * 1e-9 + travel_sec

        def _tick() -> None:
            now = self._node.get_clock().now().nanoseconds * 1e-9
            if now >= deadline:
                timer = self._backup_timers.pop(robot_id, None)
                if timer is not None:
                    timer.cancel()
                pub.publish(Twist())
                if on_result is not None:
                    on_result("COMPLETED", "backup done")
            else:
                twist = Twist()
                twist.linear.x = -abs(speed_mps)
                pub.publish(twist)

        timer = self._node.create_timer(0.05, _tick)
        self._backup_timers[robot_id] = timer
        if on_result is not None:
            on_result("ACTIVE", "backup started")

    def cancel(self, robot_id: str) -> None:
        """Cancel robot_id's active goal and any in-progress backup timer.

        Issues cancel-all via ActionClient in addition to handle-based cancel so
        goals whose handles are not yet registered in _active_goals (race window
        between send_goal_async and the _on_goal_response callback) are also
        killed before a backup starts.
        """
        timer = self._backup_timers.pop(robot_id, None)
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass
        handle = self._active_goals.get(robot_id)
        if handle is not None:
            handle.cancel_goal_async()
        # Cancel-all: catches any in-flight goal whose handle is not yet in
        # _active_goals due to the async _on_goal_response callback window.
        if ActionClient is not object:
            client = self._cancel_clients.get(robot_id)
            if client is None:
                client = ActionClient(
                    self._node, NavigateToPose, f"/{robot_id}/navigate_to_pose"
                )
                self._cancel_clients[robot_id] = client
            try:
                client.cancel_goals_async(goals_to_cancel=None)
            except Exception:
                pass

    def _on_goal_response(
        self,
        robot_id: str,
        future,
        on_result: Callable[[str, str], None] | None,
    ) -> None:
        try:
            handle = future.result()
        except Exception as exc:
            if on_result is not None:
                on_result("FAILED", f"goal response failed: {exc}")
            return
        if handle is None or not getattr(handle, "accepted", True):
            if on_result is not None:
                on_result("FAILED", "goal rejected")
            return
        self._active_goals[robot_id] = handle
        if on_result is not None:
            on_result("ACTIVE", "goal accepted")
        result_future = handle.get_result_async()
        result_future.add_done_callback(
            lambda done, rid=robot_id, cb=on_result: self._on_goal_result(rid, done, cb)
        )

    def _on_goal_result(
        self,
        robot_id: str,
        future,
        on_result: Callable[[str, str], None] | None,
    ) -> None:
        try:
            result = future.result()
        except Exception as exc:
            status = "FAILED"
            detail = f"goal result failed: {exc}"
        else:
            status_code = getattr(result, "status", None)
            if status_code == GoalStatus.STATUS_SUCCEEDED:
                status = "COMPLETED"
                detail = "goal succeeded"
            else:
                status = "FAILED"
                detail = f"goal ended with status={status_code}"
        self._active_goals.pop(robot_id, None)
        if on_result is not None:
            on_result(status, detail)


def _yaw_to_quat_zw(yaw: float) -> tuple[float, float]:
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def _pose_at(x: float, y: float) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = "map"
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    return pose

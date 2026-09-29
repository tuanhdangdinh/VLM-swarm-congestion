"""Action-client wrapper around per-robot Nav2.

This is the execution-side boundary to Nav2. It intentionally hides ROS action
message construction from higher-level coordination code, so command bus logic
can stay focused on translating CoordinationCommand messages.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable

try:
    from action_msgs.msg import GoalStatus
    from action_msgs.srv import CancelGoal
    import rclpy
    from builtin_interfaces.msg import Duration
    from geometry_msgs.msg import PoseStamped, Twist
    from nav2_msgs.action import BackUp, FollowWaypoints, NavigateToPose
    from nav_msgs.msg import Odometry
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

    class _Vector3:
        def __init__(self) -> None:
            self.x = 0.0
            self.y = 0.0
            self.z = 0.0

    class Twist:
        def __init__(self) -> None:
            self.linear = _Vector3()
            self.angular = _Vector3()

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

    class _PoseWithCovariance:
        def __init__(self) -> None:
            self.pose = _Pose()

    class Odometry:
        def __init__(self) -> None:
            self.pose = _PoseWithCovariance()

    class _UUID:
        def __init__(self) -> None:
            self.uuid = [0] * 16

    class _Time:
        def __init__(self) -> None:
            self.sec = 0
            self.nanosec = 0

    class _GoalInfo:
        def __init__(self) -> None:
            self.goal_id = _UUID()
            self.stamp = _Time()

    class CancelGoal:
        """Stub mirroring `action_msgs/srv/CancelGoal` for non-ROS unit tests."""

        ERROR_NONE = 0

        class Request:
            def __init__(self) -> None:
                self.goal_info = _GoalInfo()

from swarm_execution.yield_phase import BACKUP_STARTED_DETAIL


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
        # Keyed by (robot_id, action_name): each robot has one cancel service
        # per action, so robot_id alone would alias navigate_to_pose and
        # follow_waypoints onto the same client.
        self._cancel_clients: dict[tuple[str, str], object] = {}
        self._active_goals: dict[str, object] = {}
        self._backup_pubs: dict[str, object] = {}
        self._backup_timers: dict[str, object] = {}
        self._backup_odom_subs: dict[str, object] = {}

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

        Closed-loop on odometry, not a wall-clock deadline: this VM's Isaac Sim
        instance runs well under real time (confirmed ~0.48x standalone, worse
        under the full node stack), so a `distance_m / speed_mps` wall-clock
        timer stops long before the robot has actually traveled `distance_m` —
        physics integrates against sim time, not wall time. Odometry feedback
        is unaffected by that mismatch: it stops publishing exactly when the
        robot has actually moved far enough, however long that takes in real
        time. A generous wall-clock safety bound still applies in case the
        robot is genuinely physically blocked and never reaches the target.

        The safety bound is deliberately OS-monotonic wall time
        (`time.monotonic()`), immune to `use_sim_time`: the node clock follows
        `/clock`, which is sourced from the sim and freezes when the sim
        hangs — the exact failure this bound guards against.
        """
        self.cancel(robot_id)

        pub = self._backup_pubs.get(robot_id)
        if pub is None:
            pub = self._node.create_publisher(Twist, f"/{robot_id}/cmd_vel", 10)
            self._backup_pubs[robot_id] = pub

        odom_state: dict[str, object] = {"start": None, "last": None, "yaw": None}

        def _on_odom(msg, _state=odom_state) -> None:
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            _state["last"] = (p.x, p.y)
            _state["yaw"] = 2.0 * math.atan2(q.z, q.w)
            if _state["start"] is None:
                _state["start"] = (p.x, p.y)

        odom_sub = self._node.create_subscription(
            Odometry, f"/{robot_id}/odom", _on_odom, 10
        )
        self._backup_odom_subs[robot_id] = odom_sub

        # Safety bound: generous multiple of the naive wall-clock estimate, or
        # a floor, so a physically blocked robot doesn't back up forever.
        # Multiplier sized from measured in-stack behavior: a manual backup
        # test only covered 0.492 m of 0.8 m within a 6x/48s window, implying
        # an effective realtime factor under the full node stack well below
        # the ~0.48x measured standalone. 15x gives comfortable margin over
        # the ~78s a linear extrapolation of that measurement implies.
        # OS-monotonic on purpose: with use_sim_time the node clock tracks
        # /clock from the sim, which freezes if the sim hangs — defeating a
        # deadline whose whole job is to catch a hung/blocked scenario.
        naive_sec = abs(distance_m) / speed_mps if speed_mps else 0.0
        safety_deadline = time.monotonic() + max(naive_sec * 15.0, 30.0)

        def _finish(status: str, detail: str) -> None:
            timer = self._backup_timers.pop(robot_id, None)
            if timer is not None:
                try:
                    timer.cancel()
                except Exception:
                    pass
            sub = self._backup_odom_subs.pop(robot_id, None)
            if sub is not None:
                try:
                    self._node.destroy_subscription(sub)
                except Exception:
                    pass
            pub.publish(Twist())
            if on_result is not None:
                on_result(status, detail)

        def _tick() -> None:
            traveled = 0.0
            start = odom_state["start"]
            last = odom_state["last"]
            if start is not None and last is not None:
                traveled = math.hypot(last[0] - start[0], last[1] - start[1])

            if traveled >= abs(distance_m):
                _finish("COMPLETED", f"backup complete: moved {traveled:.3f} m")
                return
            if time.monotonic() >= safety_deadline:
                _finish(
                    "FAILED",
                    f"backup timed out: moved {traveled:.3f} m of {abs(distance_m):.3f} m",
                )
                return

            twist = Twist()
            twist.linear.x = -abs(speed_mps)
            # Lane servo while reversing (mirror of the escort's, sign
            # flipped: lateral velocity is -|v|*sin(yaw) when backing, so
            # returning to the odom y=0 lane from y>0 needs yaw>0). Blind
            # straight reversing from a slightly-angled standoff pose
            # drifted the yielder into the corridor wall until the safety
            # bound fired (H3 run 12).
            yaw = odom_state["yaw"]
            if last is not None and yaw is not None:
                desired_yaw = max(-0.3, min(0.3, 1.0 * last[1]))
                heading_error = desired_yaw - yaw
                while heading_error > math.pi:
                    heading_error -= 2.0 * math.pi
                while heading_error < -math.pi:
                    heading_error += 2.0 * math.pi
                twist.angular.z = max(-0.5, min(0.5, 2.0 * heading_error))
            pub.publish(twist)

        timer = self._node.create_timer(0.05, _tick)
        self._backup_timers[robot_id] = timer
        if on_result is not None:
            on_result("ACTIVE", BACKUP_STARTED_DETAIL)

    def sidestep(
        self,
        robot_id: str,
        lateral_m: float,
        speed_mps: float = 0.1,
        turn_rate_rps: float = 0.5,
        on_result: Callable[[str, str], None] | None = None,
    ):
        """Step the robot sideways by `lateral_m` via turn-drive-turn on cmd_vel.

        Positive `lateral_m` steps left in the robot frame, negative right.
        Replaces the Nav2-planned pull-off leg of a yield: routing a ~0.35 m
        reposition through the full planner/controller stack proved fragile —
        with motion BVH the local costmap now sees the other robot, and DWB
        fell into "Failed to make progress" recovery loops that kept the yield
        from ever reaching a terminal status. Like backup(), this bypasses
        Nav2 and the collision_monitor entirely and closes the loop on
        odometry (heading from the odom quaternion for the turns, planar
        displacement for the drive), so it terminates deterministically at
        any realtime factor. The same OS-monotonic safety bound as backup()
        guards the genuinely-blocked case.
        """
        if lateral_m == 0.0:
            if on_result is not None:
                on_result("COMPLETED", "side step complete: zero lateral")
            return

        self.cancel(robot_id)

        pub = self._backup_pubs.get(robot_id)
        if pub is None:
            pub = self._node.create_publisher(Twist, f"/{robot_id}/cmd_vel", 10)
            self._backup_pubs[robot_id] = pub

        direction = 1.0 if lateral_m > 0 else -1.0
        odom_state: dict[str, object] = {"pos": None, "yaw": None}
        # Phases: turn toward the offset, drive it, turn back to the original
        # heading so the robot faces its base-mission direction again.
        phase_state: dict[str, object] = {
            "phase": "turn_out",
            "start_yaw": None,
            "drive_start": None,
        }
        yaw_tolerance_rad = 0.05

        def _on_odom(msg, _state=odom_state) -> None:
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            _state["pos"] = (p.x, p.y)
            _state["yaw"] = 2.0 * math.atan2(q.z, q.w)

        odom_sub = self._node.create_subscription(
            Odometry, f"/{robot_id}/odom", _on_odom, 10
        )
        self._backup_odom_subs[robot_id] = odom_sub

        naive_sec = math.pi / turn_rate_rps + abs(lateral_m) / speed_mps
        safety_deadline = time.monotonic() + max(naive_sec * 15.0, 30.0)

        def _finish(status: str, detail: str) -> None:
            timer = self._backup_timers.pop(robot_id, None)
            if timer is not None:
                try:
                    timer.cancel()
                except Exception:
                    pass
            sub = self._backup_odom_subs.pop(robot_id, None)
            if sub is not None:
                try:
                    self._node.destroy_subscription(sub)
                except Exception:
                    pass
            pub.publish(Twist())
            if on_result is not None:
                on_result(status, detail)

        def _wrap(angle: float) -> float:
            while angle > math.pi:
                angle -= 2.0 * math.pi
            while angle < -math.pi:
                angle += 2.0 * math.pi
            return angle

        def _tick() -> None:
            if time.monotonic() >= safety_deadline:
                _finish(
                    "FAILED",
                    f"side step timed out in phase {phase_state['phase']}",
                )
                return
            yaw = odom_state["yaw"]
            pos = odom_state["pos"]
            if yaw is None or pos is None:
                return
            if phase_state["start_yaw"] is None:
                phase_state["start_yaw"] = yaw

            twist = Twist()
            phase = phase_state["phase"]
            if phase == "turn_out":
                target = _wrap(phase_state["start_yaw"] + direction * math.pi / 2.0)
                if abs(_wrap(yaw - target)) < yaw_tolerance_rad:
                    phase_state["phase"] = "drive"
                    phase_state["drive_start"] = pos
                else:
                    twist.angular.z = direction * turn_rate_rps
                    pub.publish(twist)
                    return
            if phase_state["phase"] == "drive":
                start = phase_state["drive_start"]
                traveled = math.hypot(pos[0] - start[0], pos[1] - start[1])
                if traveled >= abs(lateral_m):
                    phase_state["phase"] = "turn_back"
                else:
                    twist.linear.x = abs(speed_mps)
                    pub.publish(twist)
                    return
            if phase_state["phase"] == "turn_back":
                target = _wrap(phase_state["start_yaw"])
                if abs(_wrap(yaw - target)) < yaw_tolerance_rad:
                    _finish(
                        "COMPLETED",
                        f"side step complete: moved {abs(lateral_m):.3f} m",
                    )
                else:
                    twist.angular.z = -direction * turn_rate_rps
                    pub.publish(twist)

        timer = self._node.create_timer(0.05, _tick)
        self._backup_timers[robot_id] = timer
        if on_result is not None:
            on_result("ACTIVE", "side step started")

    def drive_heading(
        self,
        robot_id: str,
        target_yaw_rad: float,
        distance_m: float,
        speed_mps: float = 0.1,
        turn_rate_rps: float = 0.5,
        on_result: Callable[[str, str], None] | None = None,
    ):
        """Rotate to an absolute odom-frame heading, then drive straight.

        The passer's escorted gap transit: DWB could not traverse the barrier
        gap even with a ±0.19 m free band (creep at ~0.01 m/s across four
        H3 runs), so the coordination layer drives the transit itself with
        the same odometry-closed-loop raw-cmd_vel pattern as backup() and
        sidestep(). `target_yaw_rad` is in the robot's own odom frame; both
        robots spawn facing their base goal, so odom yaw 0 always points
        toward the goal regardless of map orientation — the caller needs no
        frame knowledge. Same OS-monotonic safety bound as the siblings.
        """
        self.cancel(robot_id)

        pub = self._backup_pubs.get(robot_id)
        if pub is None:
            pub = self._node.create_publisher(Twist, f"/{robot_id}/cmd_vel", 10)
            self._backup_pubs[robot_id] = pub

        odom_state: dict[str, object] = {"pos": None, "yaw": None}
        phase_state: dict[str, object] = {"phase": "turn", "drive_start": None}
        yaw_tolerance_rad = 0.05

        def _on_odom(msg, _state=odom_state) -> None:
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            _state["pos"] = (p.x, p.y)
            _state["yaw"] = 2.0 * math.atan2(q.z, q.w)

        odom_sub = self._node.create_subscription(
            Odometry, f"/{robot_id}/odom", _on_odom, 10
        )
        self._backup_odom_subs[robot_id] = odom_sub

        naive_sec = math.pi / turn_rate_rps + abs(distance_m) / speed_mps
        safety_deadline = time.monotonic() + max(naive_sec * 15.0, 30.0)

        def _finish(status: str, detail: str) -> None:
            timer = self._backup_timers.pop(robot_id, None)
            if timer is not None:
                try:
                    timer.cancel()
                except Exception:
                    pass
            sub = self._backup_odom_subs.pop(robot_id, None)
            if sub is not None:
                try:
                    self._node.destroy_subscription(sub)
                except Exception:
                    pass
            pub.publish(Twist())
            if on_result is not None:
                on_result(status, detail)

        def _wrap(angle: float) -> float:
            while angle > math.pi:
                angle -= 2.0 * math.pi
            while angle < -math.pi:
                angle += 2.0 * math.pi
            return angle

        def _tick() -> None:
            if time.monotonic() >= safety_deadline:
                _finish(
                    "FAILED",
                    f"escort timed out in phase {phase_state['phase']}",
                )
                return
            yaw = odom_state["yaw"]
            pos = odom_state["pos"]
            if yaw is None or pos is None:
                return

            twist = Twist()
            if phase_state["phase"] == "turn":
                error = _wrap(target_yaw_rad - yaw)
                if abs(error) < yaw_tolerance_rad:
                    phase_state["phase"] = "drive"
                    phase_state["drive_start"] = pos
                else:
                    twist.angular.z = turn_rate_rps if error > 0 else -turn_rate_rps
                    pub.publish(twist)
                    return
            if phase_state["phase"] == "drive":
                start = phase_state["drive_start"]
                traveled = math.hypot(pos[0] - start[0], pos[1] - start[1])
                if traveled >= abs(distance_m):
                    _finish(
                        "COMPLETED",
                        f"escort complete: moved {traveled:.3f} m",
                    )
                    return
                twist.linear.x = abs(speed_mps)
                # Centerline servo, not open-loop straight: both robots spawn
                # ON the lane centerline (odom y=0 for the target_yaw_rad=0
                # escort), and heading-tolerance drift over meters of tunnel
                # pushed the passer into the parked yielder (physical contact,
                # H3 run 9). Steer toward the y=0 line with a clamped heading
                # correction plus a P-term on heading error.
                lateral = pos[1]
                desired_yaw = _wrap(
                    target_yaw_rad + max(-0.3, min(0.3, -1.0 * lateral))
                )
                heading_error = _wrap(desired_yaw - yaw)
                twist.angular.z = max(-turn_rate_rps, min(turn_rate_rps, 2.0 * heading_error))
                pub.publish(twist)

        timer = self._node.create_timer(0.05, _tick)
        self._backup_timers[robot_id] = timer
        if on_result is not None:
            on_result("ACTIVE", "escort started")

    def cancel(self, robot_id: str) -> None:
        """Cancel robot_id's active goal and any in-progress backup timer.

        Beyond cancelling our own goal handle, this clears every goal on the
        robot's `navigate_to_pose` and `follow_waypoints` servers through the
        action cancel service. That covers two cases a goal handle cannot: a
        goal still inside the `send_goal_async`/`_on_goal_response` race
        window, and — the important one — goals issued by a *different* node.
        `command_bus_node` and `coordination_client_node` each hold their own
        `Nav2Adapter`, so neither owns the other's handles; only the
        server-side cancel service can stop a goal the other node sent.

        This previously called `ActionClient.cancel_goals_async()`, which does
        not exist in rclpy: the class exposes `send_goal_async` but no public
        cancel entry point, and cancellation lives on
        `ClientGoalHandle.cancel_goal_async()` or the private
        `ActionClient._cancel_goal_async(goal_handle)`. The resulting
        `AttributeError` was swallowed by a bare `except: pass`, so the
        cancel-all silently did nothing on every call while callers went on to
        log success.
        """
        timer = self._backup_timers.pop(robot_id, None)
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass
        sub = self._backup_odom_subs.pop(robot_id, None)
        if sub is not None:
            try:
                self._node.destroy_subscription(sub)
            except Exception:
                pass
        handle = self._active_goals.get(robot_id)
        if handle is not None:
            handle.cancel_goal_async()
        self._cancel_all(robot_id, "navigate_to_pose")
        self._cancel_all(robot_id, "follow_waypoints")

    def _cancel_all(self, robot_id: str, action_name: str) -> None:
        """Cancel every goal on one of robot_id's action servers.

        Args:
            robot_id: Robot whose action server should be cleared.
            action_name: Action to clear, e.g. `navigate_to_pose`.
        """
        service_name = f"/{robot_id}/{action_name}/_action/cancel_goal"
        key = (robot_id, action_name)
        client = self._cancel_clients.get(key)
        if client is None:
            client = self._node.create_client(CancelGoal, service_name)
            self._cancel_clients[key] = client
        # Readiness is checked, never waited on: cancel() runs inside safety
        # and coordination callbacks, and blocking here would stall the very
        # executor that has to deliver the cancel response. A freshly created
        # client is not ready until discovery completes, so the first cancel
        # after node start can legitimately skip.
        if not client.service_is_ready():
            self._node.get_logger().warning(
                f"cancel-all skipped: service not ready "
                f"robot={robot_id} action={action_name}"
            )
            return
        future = client.call_async(build_cancel_all_request(CancelGoal.Request))
        future.add_done_callback(
            lambda done, rid=robot_id, act=action_name: self._on_cancel_all_response(
                rid, act, done
            )
        )

    def _on_cancel_all_response(
        self,
        robot_id: str,
        action_name: str,
        future,
    ) -> None:
        try:
            response = future.result()
        except Exception as exc:
            self._node.get_logger().warning(
                f"cancel-all failed robot={robot_id} action={action_name} "
                f"error={exc}"
            )
            return
        goals_canceling = getattr(response, "goals_canceling", None) or []
        self._node.get_logger().info(
            f"cancel-all robot={robot_id} action={action_name} "
            f"return_code={getattr(response, 'return_code', None)} "
            f"goals_canceling={len(goals_canceling)}"
        )

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


def build_cancel_all_request(request_cls: type) -> object:
    """Build a `CancelGoal` request that cancels every goal on an action server.

    The cancel policy in `action_msgs/srv/CancelGoal` keys off both fields
    together: a zero goal id with a zero stamp means "cancel all goals", while
    a zero goal id with a *non-zero* stamp only cancels goals accepted at or
    before that stamp. Both are therefore zeroed explicitly rather than left
    at whatever the message default happens to be.

    Args:
        request_cls: The `CancelGoal.Request` class to instantiate.

    Returns:
        A request whose `goal_info.goal_id.uuid` is 16 zero bytes and whose
        `goal_info.stamp` is zero.
    """
    request = request_cls()
    request.goal_info.goal_id.uuid = [0] * 16
    request.goal_info.stamp.sec = 0
    request.goal_info.stamp.nanosec = 0
    return request


def _yaw_to_quat_zw(yaw: float) -> tuple[float, float]:
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def _pose_at(x: float, y: float) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = "map"
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    return pose

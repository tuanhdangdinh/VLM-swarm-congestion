"""Action-client wrapper around per-robot Nav2.

This is the execution-side boundary to Nav2. It intentionally hides ROS action
message construction from higher-level coordination code, so command bus logic
can stay focused on translating CoordinationCommand messages.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping
from typing import Any

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

# Line-hold servo gains, the escort's centerline-servo values: heading
# correction per metre of cross-track error, and its clamp in radians.
_LINE_HOLD_GAIN = 1.0
_LINE_HOLD_MAX_RAD = 0.3


def line_hold_yaw(
    heading_rad: float,
    start: tuple[float, float],
    position: tuple[float, float],
    reversing: bool = False,
) -> float:
    """Heading that steers a robot back onto a line while it drives along it.

    The line runs through `start` along `heading_rad`, all in one frame (the
    robot's odom frame). The correction is the escort's centerline servo,
    generalized from the odom y=0 line to any line: cross-track error
    (positive left of travel) times `_LINE_HOLD_GAIN`, clamped to
    `_LINE_HOLD_MAX_RAD`, steering back toward the line.

    `reversing=True` mirrors the correction for a robot backing along the
    line: moving backward, lateral velocity flips with the drive direction
    (it is `-|v| * sin(heading error)`), so returning to the line needs the
    heading offset on the other side — the sign flip `backup`'s odom y=0
    servo already applies, generalized to any line.

    Args:
        heading_rad: The robot's facing along the line (travel direction when
            driving forward, its opposite when reversing).
        start: A point on the line, `(x, y)` in metres.
        position: The robot's current `(x, y)` in metres.
        reversing: True when the robot backs along the line.

    Returns:
        The desired heading in radians, wrapped to `(-pi, pi]`.
    """
    dx = position[0] - start[0]
    dy = position[1] - start[1]
    cross = -dx * math.sin(heading_rad) + dy * math.cos(heading_rad)
    gain = _LINE_HOLD_GAIN if reversing else -_LINE_HOLD_GAIN
    correction = max(-_LINE_HOLD_MAX_RAD, min(_LINE_HOLD_MAX_RAD, gain * cross))
    return math.atan2(math.sin(heading_rad + correction), math.cos(heading_rad + correction))


# A line turned further than this from the start heading is not one to hold
# while reversing; M3 itself caps the turn at 45 degrees.
_LINE_TURN_MAX_RAD = math.pi / 2


def backup_line_turn(parameters: Mapping[str, Any]) -> float | None:
    """Turn from the backup's start heading onto the line M3 swept, or None.

    prereg-v3 A25: a dynamic-lane yield carries `backup_facing_rad` (the
    world-frame facing of the swept retreat line) and
    `backup_reference_yaw_rad` (the yielder's world yaw in the same decision
    snapshot). Their wrapped difference is the same turn in any frame, so it
    is applied to the robot's own odom start yaw (the escort-heading
    pattern of `PasserPlan.escort_turn_rad`).

    Args:
        parameters: The decoded yield `parameters_json`.

    Returns:
        The turn in radians, wrapped to `(-pi, pi]`; None when either key is
        absent or not a finite number, or the turn exceeds 90 degrees.
    """
    values = []
    for key in ("backup_facing_rad", "backup_reference_yaw_rad"):
        value = parameters.get(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        if not math.isfinite(value):
            return None
        values.append(float(value))
    turn = math.atan2(math.sin(values[0] - values[1]), math.cos(values[0] - values[1]))
    if abs(turn) > _LINE_TURN_MAX_RAD:
        return None
    return turn


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
        """Send a FollowWaypoints goal for a route.

        Unlike `send_goal`, this subscribes to the action's feedback and logs
        each change of the server's `current_waypoint`, so a multi-leg route's
        progress is visible in the M4 log (the first live use of this path
        stalled with no record of which leg it was on).
        """
        self.cancel(robot_id)
        client = self._waypoint_clients.setdefault(
            robot_id, self._make_client(robot_id, "follow_waypoints")
        )
        goal_msg = FollowWaypoints.Goal()
        for x, y in waypoints:
            goal_msg.poses.append(_pose_at(x, y))
        progress: dict[str, int | None] = {"current": None}
        future = client.send_goal_async(
            goal_msg,
            feedback_callback=lambda feedback, rid=robot_id, route=list(waypoints): (
                self._on_waypoint_feedback(rid, route, progress, feedback)
            ),
        )
        future.add_done_callback(
            lambda done, rid=robot_id, cb=on_result: self._on_goal_response(rid, done, cb)
        )
        return future

    def _on_waypoint_feedback(
        self,
        robot_id: str,
        route: list[tuple[float, float]],
        progress: dict[str, int | None],
        feedback_msg,
    ) -> None:
        """Log a FollowWaypoints route's leg index each time it changes.

        Args:
            robot_id: Robot following the route.
            route: The waypoints sent, as `(x, y)` in the map frame.
            progress: Per-goal mutable state holding the last logged index.
            feedback_msg: The action feedback message (`.feedback.current_waypoint`).
        """
        feedback = getattr(feedback_msg, "feedback", feedback_msg)
        index = getattr(feedback, "current_waypoint", None)
        if index is None or index == progress["current"]:
            return
        progress["current"] = int(index)
        target = route[index] if 0 <= index < len(route) else None
        target_text = "none" if target is None else f"({target[0]:.2f}, {target[1]:.2f})"
        sim_t = self._node.get_clock().now().nanoseconds / 1e9
        self._node.get_logger().info(
            f"waypoint leg progress robot={robot_id} current_waypoint={index} "
            f"of={len(route)} target={target_text} sim_t={sim_t:.3f}"
        )

    def backup(
        self,
        robot_id: str,
        distance_m: float,
        speed_mps: float = 0.1,
        on_result: Callable[[str, str], None] | None = None,
        hold_start_line: bool = False,
        line_turn_rad: float = 0.0,
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

        `hold_start_line=True` (prereg-v3 A11(iii) sibling, S1 task streams,
        where a backing robot may be off its spawn heading) replaces the odom
        y=0 lane servo with the line through the robot's own pose at its
        first odometry sample, along its heading there, with the reversing
        correction sign (`line_hold_yaw`). The default servo assumes heading
        ~0 (it steers toward odom y=0, the spawn line), so an off-heading
        yielder backed along an arc instead of a straight line; the default
        path is unchanged.

        `line_turn_rad` (prereg-v3 A25, with `hold_start_line` only) turns
        that line from the start heading by this much: the line still runs
        through the start pose, now along `start_yaw + line_turn_rad`, so a
        yielder off its swept lane axis backs along the axis M3 validated
        (`backup_line_turn`). 0.0 is exactly the start-heading line.
        """
        self.cancel(robot_id)

        pub = self._backup_pubs.get(robot_id)
        if pub is None:
            pub = self._node.create_publisher(Twist, f"/{robot_id}/cmd_vel", 10)
            self._backup_pubs[robot_id] = pub

        odom_state: dict[str, object] = {
            "start": None,
            "start_yaw": None,
            "last": None,
            "yaw": None,
        }

        def _on_odom(msg, _state=odom_state) -> None:
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            _state["last"] = (p.x, p.y)
            _state["yaw"] = 2.0 * math.atan2(q.z, q.w)
            if _state["start"] is None:
                _state["start"] = (p.x, p.y)
                _state["start_yaw"] = _state["yaw"]

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
                if hold_start_line and start is not None:
                    # Hold the line through the backup's own start pose along
                    # the start heading — never the odom y=0 spawn line, which
                    # only matches for a robot still on its spawn heading.
                    desired_yaw = line_hold_yaw(
                        odom_state["start_yaw"] + line_turn_rad, start, last, reversing=True
                    )
                else:
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
        relative_to_start: bool = False,
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

        `relative_to_start=True` (prereg-v3 A11(iii), S1 task streams, where
        a robot's goal is no longer its spawn heading) instead turns by
        `target_yaw_rad` from the robot's odom yaw at its first odometry
        sample, and the drive holds the line through the drive-start pose
        along that heading (`line_hold_yaw`), not the spawn line odom y=0.
        The default path is unchanged.
        """
        self.cancel(robot_id)

        pub = self._backup_pubs.get(robot_id)
        if pub is None:
            pub = self._node.create_publisher(Twist, f"/{robot_id}/cmd_vel", 10)
            self._backup_pubs[robot_id] = pub

        odom_state: dict[str, object] = {"pos": None, "yaw": None}
        phase_state: dict[str, object] = {"phase": "turn", "drive_start": None, "target": None}
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

            if relative_to_start and phase_state["target"] is None:
                phase_state["target"] = _wrap(yaw + target_yaw_rad)
            target = phase_state["target"] if relative_to_start else target_yaw_rad

            twist = Twist()
            if phase_state["phase"] == "turn":
                error = _wrap(target - yaw)
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
                if relative_to_start:
                    heading_error = _wrap(line_hold_yaw(target, start, pos) - yaw)
                    twist.angular.z = max(
                        -turn_rate_rps, min(turn_rate_rps, 2.0 * heading_error)
                    )
                    pub.publish(twist)
                    return
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

    def cancel_own_goal(self, robot_id: str) -> bool:
        """Cancel only this adapter's most recent accepted goal handle for robot_id.

        Unlike `cancel`, this sends no server-side cancel-all, so a goal the
        command bus's own adapter sent to the same action server is untouched.

        Args:
            robot_id: Robot whose own goal handle should be cancelled.

        Returns:
            True if a handle was found and its cancel requested.
        """
        handle = self._active_goals.get(robot_id)
        if handle is None:
            return False
        handle.cancel_goal_async()
        return True

    def stop_controller(self, robot_id: str) -> None:
        """Cancel every goal on robot_id's controller_server `follow_path` action.

        Cancelling a `navigate_to_pose` goal does not always stop the robot.
        In Nav2 Jazzy (1.3.x) `BtActionNode::halt()` cancels its `FollowPath`
        goal only when `should_cancel_goal()` holds, which returns false while
        `goal_handle_` is still null, i.e. while the FollowPath goal request
        is in flight and its response has not been spun yet. A
        `navigate_to_pose` cancel that lands in that window leaves the
        controller following the path with no owner (IB10 remedy run m4).
        The controller's own `follow_path` server accepts cancel requests for
        active goals, and `computeControl` handles one by calling
        `terminate_all()` and `publishZeroVelocity()` (zero twist on
        `cmd_vel_nav`, then the collision monitor forwards it), so this
        cancel stops the robot through Nav2's own path and needs no separate
        raw zero twist.

        Args:
            robot_id: Robot whose controller should stop.
        """
        self._cancel_all(robot_id, "follow_path")

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

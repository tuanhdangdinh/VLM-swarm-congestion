from __future__ import annotations

import json

try:
    import rclpy
    from rclpy.node import Node
    from swarm_interfaces.msg import CoordinationCommand, CoordinationStatus
except ImportError:
    rclpy = None
    Node = object
    CoordinationCommand = object
    CoordinationStatus = object

from swarm_execution.nav2_adapter import Nav2Adapter


class CommandBusNode(Node):
    def __init__(self):
        super().__init__("command_bus_node")
        self._adapter = Nav2Adapter(self)
        self._status_republish_timers = []
        self._status_pub = self.create_publisher(CoordinationStatus, "/coordination/status", 10)
        self.create_subscription(
            CoordinationCommand,
            "/coordination/commands",
            self._on_command,
            10,
        )
        self.get_logger().info("Command bus started.")

    def _on_command(self, msg: CoordinationCommand) -> None:
        self.get_logger().info(
            f"command received command={msg.command_id} robot={msg.robot_id} action={msg.action}"
        )
        try:
            params = json.loads(msg.parameters_json or "{}")
            pending_result = self._dispatch(msg, params)
        except Exception as exc:
            self._publish_status(msg, "FAILED", str(exc))
            self.get_logger().error(
                f"command failed command={msg.command_id} robot={msg.robot_id}: {exc}"
            )
            return
        if not pending_result:
            self._publish_status(msg, "COMPLETED", "dispatched")

    def _dispatch(self, msg: CoordinationCommand, params: dict) -> bool:
        robot_id = msg.robot_id
        action = msg.action
        if action in {"navigate", "goal", "priority_override"}:
            goal = params.get("goal") or params.get("target") or {}
            x = goal["x"] if isinstance(goal, dict) else goal[0]
            y = goal["y"] if isinstance(goal, dict) else goal[1]
            yaw = goal.get("yaw", 0.0) if isinstance(goal, dict) else 0.0
            self._adapter.send_goal(
                robot_id,
                float(x),
                float(y),
                float(yaw),
                on_result=lambda status, detail, command=msg: self._publish_status(
                    command, status, detail
                ),
            )
            return True
        if action in {"reroute", "convoy"}:
            waypoints = params.get("waypoints") or []
            if not waypoints:
                # No explicit waypoints: re-send the original task goal so the
                # robot resumes navigation from its current position. This is
                # the common case when M3 grounds reroute without a specific
                # alternative path (the grounder leaves waypoints empty as a
                # placeholder for scenarios without a pre-planned detour).
                goal = params.get("goal") or params.get("target") or {}
                if goal:
                    x = goal["x"] if isinstance(goal, dict) else goal[0]
                    y = goal["y"] if isinstance(goal, dict) else goal[1]
                    yaw = goal.get("yaw", 0.0) if isinstance(goal, dict) else 0.0
                    self._adapter.send_goal(
                        robot_id,
                        float(x),
                        float(y),
                        float(yaw),
                        on_result=lambda status, detail, command=msg: self._publish_status(
                            command, status, detail
                        ),
                    )
                    return True
                # No goal either — mark completed so M5 can escalate.
                return False
            self._adapter.send_waypoints(
                robot_id,
                [(float(p["x"]), float(p["y"])) if isinstance(p, dict) else (float(p[0]), float(p[1]))
                 for p in waypoints],
                on_result=lambda status, detail, command=msg: self._publish_status(
                    command, status, detail
                ),
            )
            return True
        if action in {"yield", "reverse"}:
            # Clearing maneuver: a head-on standoff does not clear if the yielding
            # robot merely stops nose-to-nose, so it physically reverses to open
            # the aisle (Phase 3 closed loop). Distance comes from the grounded
            # command; default to a conservative back-off if absent.
            distance_m = float(params.get("backup_distance_m", 0.3))
            # hold_sec (yield only): after backing up the robot holds position so
            # the other robot can navigate through the cleared aisle before this
            # robot resumes. reverse does not hold; both robots back up symmetrically.
            hold_sec = float(params.get("hold_sec", 0.0)) if action == "yield" else 0.0
            # pull_off_* (yield only, optional): a straight backup alone leaves
            # the yielder on the same line the passer must travel, so it
            # re-blocks the corridor. If the grounder supplied a lateral
            # parking pose, route there via Nav2's normal planner/controller
            # (not the raw-cmd_vel bypass backup() uses) after the initial
            # backup has opened enough separation for collision_monitor to
            # stay quiet.
            pull_off_x = params.get("pull_off_x")
            pull_off_y = params.get("pull_off_y")
            pull_off_yaw = float(params.get("pull_off_yaw", 0.0))
            has_pull_off = (
                action == "yield" and pull_off_x is not None and pull_off_y is not None
            )

            def _start_hold(command, _hold_sec: float) -> None:
                self._publish_status(command, "ACTIVE", "holding for passing robot")
                timer_ref: dict = {}

                def _hold_expired() -> None:
                    self._publish_status(command, "COMPLETED", "yield complete")
                    t = timer_ref.get("timer")
                    if t is not None:
                        t.cancel()
                        self.destroy_timer(t)

                t = self.create_timer(_hold_sec, _hold_expired)
                timer_ref["timer"] = t

            def _on_pull_off_result(
                status: str,
                detail: str,
                command=msg,
                _hold_sec: float = hold_sec,
            ) -> None:
                if status != "COMPLETED" or _hold_sec <= 0.0:
                    self._publish_status(command, status, detail)
                    return
                _start_hold(command, _hold_sec)

            def _on_backup_result(
                status: str,
                detail: str,
                command=msg,
                _hold_sec: float = hold_sec,
            ) -> None:
                if status != "COMPLETED":
                    self._publish_status(command, status, detail)
                    return
                if has_pull_off:
                    self._publish_status(command, "ACTIVE", "pulling off aisle centerline")
                    self._adapter.send_goal(
                        robot_id,
                        float(pull_off_x),
                        float(pull_off_y),
                        pull_off_yaw,
                        on_result=_on_pull_off_result,
                    )
                    return
                if _hold_sec <= 0.0:
                    self._publish_status(command, status, detail)
                    return
                _start_hold(command, _hold_sec)

            self._adapter.backup(robot_id, distance_m, on_result=_on_backup_result)
            return True
        if action in {"wait", "temporary_wait", "stop"}:
            self._adapter.cancel(robot_id)
            duration_sec = float(params.get("duration_sec", 0.0))
            if duration_sec <= 0.0:
                return False
            # Hold Nav2 paused for duration_sec before publishing COMPLETED so
            # M5 cannot dispatch a competing command until the window expires.
            self._publish_status(msg, "ACTIVE", "waiting")
            timer_ref: dict = {}

            def _wait_expired(_command=msg) -> None:
                self._publish_status(_command, "COMPLETED", "wait complete")
                t = timer_ref.get("timer")
                if t is not None:
                    t.cancel()
                    self.destroy_timer(t)

            t = self.create_timer(duration_sec, _wait_expired)
            timer_ref["timer"] = t
            return True
        raise ValueError(f"unsupported action: {action}")

    def _publish_status(self, command: CoordinationCommand, status: str, detail: str) -> None:
        msg = CoordinationStatus()
        msg.command_id = command.command_id
        msg.robot_id = command.robot_id
        msg.status = status
        msg.detail = detail
        self._status_pub.publish(msg)
        self.get_logger().info(
            f"status published command={command.command_id} robot={command.robot_id} status={status}"
        )
        for delay_sec in (0.25, 0.75):
            self._schedule_status_republish(msg, delay_sec)

    def _schedule_status_republish(self, msg: CoordinationStatus, delay_sec: float) -> None:
        timer_ref = {}

        def republish() -> None:
            self._status_pub.publish(msg)
            self.get_logger().info(
                f"status republished command={msg.command_id} robot={msg.robot_id} status={msg.status}"
            )
            timer = timer_ref["timer"]
            timer.cancel()
            self.destroy_timer(timer)
            self._status_republish_timers.remove(timer)

        timer = self.create_timer(delay_sec, republish)
        timer_ref["timer"] = timer
        self._status_republish_timers.append(timer)

    def destroy_node(self) -> bool:
        for timer in list(self._status_republish_timers):
            timer.cancel()
            self.destroy_timer(timer)
            self._status_republish_timers.remove(timer)
        return super().destroy_node()


def main(args=None):
    if rclpy is None:
        raise SystemExit("rclpy is required to run this node.")
    rclpy.init(args=args)
    node = CommandBusNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

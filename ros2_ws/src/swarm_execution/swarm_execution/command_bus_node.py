from __future__ import annotations

import json
from typing import NamedTuple

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


class _ActiveWait(NamedTuple):
    """Bookkeeping for a wait/temporary_wait/stop timer eligible for early release.

    `timer_ref` is the same mutable dict the wait's own expiry closure writes
    the timer into (see `_dispatch`'s wait branch), rather than the timer
    object itself. Registering this way — before `create_timer` returns —
    means a release triggered synchronously (e.g. a stubbed timer in tests)
    cannot race the `timer_ref["timer"] = t` assignment that happens after.
    """

    timer_ref: dict
    command: CoordinationCommand


class CommandBusNode(Node):
    def __init__(self):
        super().__init__("command_bus_node")
        self._adapter = Nav2Adapter(self)
        self._status_republish_timers = []
        # robot_id -> command_id currently holding that robot's Nav2 slot.
        # Populated/cleared from _publish_status so it can never drift from
        # what was actually published (see _update_in_flight_registry).
        self._in_flight: dict[str, str] = {}
        # (command_id, robot_id) -> still-active wait timer, so a linked
        # yield/reverse's terminal status can release it early instead of
        # waiting out its fixed duration (see _release_linked_waits).
        self._active_waits: dict[tuple[str, str], _ActiveWait] = {}
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
        active_command_id = self._in_flight.get(msg.robot_id)
        if active_command_id is not None:
            if active_command_id == msg.command_id:
                # Redelivery (DDS retry, republish) of the command already
                # driving this robot: not a new command, so no dispatch and
                # no status — the original in-flight status already covers it.
                self.get_logger().info(
                    f"duplicate command ignored command={msg.command_id} robot={msg.robot_id}"
                )
                return
            # A busy-rejected yield/reverse never dispatched, so a linked wait
            # released by this FAILED must not read as "yield failed" — no
            # yield was attempted. Provenance is passed explicitly, never
            # inferred from detail text.
            self._publish_status(
                msg,
                "FAILED",
                f"robot busy: {active_command_id}",
                release_detail="released: yield rejected",
            )
            return
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
            wait_key = (msg.command_id, robot_id)
            timer_ref: dict = {}
            # Register before create_timer returns so a release racing a
            # synchronously-firing timer (or vice versa) cannot resurrect an
            # entry that already completed — see _ActiveWait.
            self._active_waits[wait_key] = _ActiveWait(timer_ref=timer_ref, command=msg)

            def _wait_expired(_command=msg, _key=wait_key) -> None:
                self._active_waits.pop(_key, None)
                self._publish_status(_command, "COMPLETED", "wait complete")
                t = timer_ref.get("timer")
                if t is not None:
                    t.cancel()
                    self.destroy_timer(t)

            t = self.create_timer(duration_sec, _wait_expired)
            timer_ref["timer"] = t
            return True
        raise ValueError(f"unsupported action: {action}")

    def _publish_status(
        self,
        command: CoordinationCommand,
        status: str,
        detail: str,
        release_detail: str | None = None,
    ) -> None:
        self._update_in_flight_registry(command.robot_id, command.command_id, status)
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
        if status in ("COMPLETED", "FAILED") and command.action in ("yield", "reverse"):
            self._release_linked_waits(command.command_id, status, release_detail)

    def _release_linked_waits(
        self, command_id: str, yield_status: str, release_detail: str | None = None
    ) -> None:
        """Complete every still-active wait sharing `command_id` with a terminal yield.

        M5 grounds a two-robot resolution — one robot `yield`s, another
        `temporary_wait`s — under one `command_id`. Without this, the waiting
        robot re-enters the aisle when its fixed-duration timer expires, even
        if the yielding robot is still mid-maneuver. Releasing the wait the
        moment the yield reaches a terminal status keeps both robots' terminal
        statuses tied to the same real-world event, so M5 can re-analyze with
        both robots free.

        Args:
            command_id: Command identifier shared by the yield and its linked wait(s).
            yield_status: Terminal status of the yield/reverse action (`COMPLETED` or `FAILED`).
            release_detail: Explicit provenance override for the released waits'
                detail text (used by the busy-reject path, where the yield never
                dispatched and "yield failed" would be misleading).
        """
        detail = release_detail or (
            "released: yield complete" if yield_status == "COMPLETED" else "released: yield failed"
        )
        for key in [k for k in self._active_waits if k[0] == command_id]:
            wait = self._active_waits.pop(key)
            timer = wait.timer_ref.get("timer")
            if timer is not None:
                timer.cancel()
                self.destroy_timer(timer)
            self._publish_status(wait.command, "COMPLETED", detail)

    def _update_in_flight_registry(self, robot_id: str, command_id: str, status: str) -> None:
        """Keep `_in_flight` in sync with the status that is about to publish.

        A robot enters the registry on the first `ACTIVE` published for a
        command and leaves it on a terminal status (`COMPLETED`/`FAILED`),
        but only if that terminal status belongs to the command currently
        holding the slot — a stale/rejected command's terminal status must
        not evict a different command that has since taken over.

        Args:
            robot_id: Robot identifier the status belongs to.
            command_id: Command identifier the status belongs to.
            status: Status value about to be published (e.g. ACTIVE, COMPLETED, FAILED).
        """
        if status == "ACTIVE":
            self._in_flight[robot_id] = command_id
        elif status in ("COMPLETED", "FAILED"):
            if self._in_flight.get(robot_id) == command_id:
                del self._in_flight[robot_id]

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

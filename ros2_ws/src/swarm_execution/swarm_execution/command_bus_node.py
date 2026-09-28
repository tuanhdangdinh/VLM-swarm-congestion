from __future__ import annotations

import json
import time
from typing import NamedTuple

try:
    import rclpy
    from nav_msgs.msg import Odometry
    from rclpy.node import Node
    from swarm_interfaces.msg import CoordinationCommand, CoordinationStatus
except ImportError:
    rclpy = None
    Node = object
    Odometry = object
    CoordinationCommand = object
    CoordinationStatus = object

from swarm_execution.crossing_chain import CrossingChain, plan_crossing
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
    # Nav2-leg watchdog: M5 never expires a command with an ACTIVE robot (it
    # delegates liveness to M4), so a Nav2 action server that hangs mid-goal
    # would otherwise leave the command ACTIVE forever and gate the robot out
    # of re-analysis. The deadline is 3x the command's own timeout_sec with a
    # generous floor (timeout_sec <= 0 means "absent" on the wire).
    NAV_WATCHDOG_SWEEP_PERIOD_SEC = 1.0
    NAV_WATCHDOG_TIMEOUT_MULTIPLIER = 3.0
    NAV_WATCHDOG_FLOOR_SEC = 120.0

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
        # (command_id, robot_id) -> (monotonic deadline, command) for Nav2
        # goal/waypoint legs awaiting a result callback. Deadline arithmetic
        # is time.monotonic() on purpose: the node runs on sim time, so a
        # node-clock deadline would freeze with /clock (see _sweep docstring).
        self._nav_watchdogs: dict[tuple[str, str], tuple[float, CoordinationCommand]] = {}
        self._status_pub = self.create_publisher(CoordinationStatus, "/coordination/status", 10)
        self.create_subscription(
            CoordinationCommand,
            "/coordination/commands",
            self._on_command,
            10,
        )
        self.create_timer(self.NAV_WATCHDOG_SWEEP_PERIOD_SEC, self._sweep_nav_watchdogs)
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
                on_result=self._make_nav_result_handler(msg),
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
                        on_result=self._make_nav_result_handler(msg),
                    )
                    return True
                # No goal either — mark completed so M5 can escalate.
                return False
            self._adapter.send_waypoints(
                robot_id,
                [
                    (float(p["x"]), float(p["y"]))
                    if isinstance(p, dict)
                    else (float(p[0]), float(p[1]))
                    for p in waypoints
                ],
                on_result=self._make_nav_result_handler(msg),
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
            # pull_off_lateral_m (yield only, optional): a straight backup
            # alone leaves the yielder on the passer's line AND, with
            # min_distance_m=0.45 in the 1.2 m aisle, too close for the passer
            # to clear without tripping the safety latch — so the yielder
            # steps sideways off the centerline. Executed as a raw-cmd_vel
            # sidestep (adapter.sidestep), not a Nav2 goal: the planned leg
            # proved unreliable once the costmap could see the other robot
            # (DWB "Failed to make progress" recovery loops, observed
            # 2026-07-03), and it self-terminates, so no nav watchdog needed.
            pull_off_lateral = params.get("pull_off_lateral_m")
            has_pull_off = action == "yield" and pull_off_lateral is not None
            # passer_robot_id / passer_clear_m (yield only, optional): end the
            # hold as soon as the passer has actually cleared, measured as its
            # own odometry displacement since hold start (frame-free). A fixed
            # hold under-shoots at low realtime factors (12 s sim expired
            # mid-traverse, both robots re-entered together, 2026-07-03);
            # hold_sec remains the upper-bound backstop for a passer that
            # never moves.
            # passer_escort_distance_m (optional): when present, the passer is
            # DRIVEN through the gap by the raw-cmd_vel escort primitive
            # during the hold instead of resuming Nav2 — DWB could not
            # transit the gap even with a widened free band (creep at
            # ~0.01 m/s, H3 runs 4-7). While escorted, the passer's linked
            # wait stays ACTIVE (suppressing its base mission) and releases
            # via the normal yield-terminal path once the hold ends.
            # crossing_order (optional, 2+ passers): the passers are admitted
            # one at a time in that order and the hold ends only when the
            # LAST one has cleared; with a single passer the chain is exactly
            # the hold described above. See crossing_chain.py.
            passers = plan_crossing(params) if action == "yield" else ()
            chain = CrossingChain(passers) if passers else None

            def _start_hold(command, _hold_sec: float) -> None:
                self._publish_status(command, "ACTIVE", "holding for passing robot")
                timer_ref: dict = {}
                odom_subs: list = []
                done_ref = {"done": False}

                def _finish_hold(detail: str) -> None:
                    if done_ref["done"]:
                        return
                    done_ref["done"] = True
                    self._publish_status(command, "COMPLETED", detail)
                    t = timer_ref.get("timer")
                    if t is not None:
                        t.cancel()
                        self.destroy_timer(t)
                    for sub in odom_subs:
                        self.destroy_subscription(sub)

                def _hold_expired() -> None:
                    _finish_hold("yield complete")

                def _on_passer_odom(passer_id: str, odom_msg) -> None:
                    if done_ref["done"]:
                        return
                    p = odom_msg.pose.pose.position
                    step = chain.on_odometry(passer_id, p.x, p.y)
                    if step is None:
                        return
                    if step.next is None:
                        _finish_hold("yield complete: passer cleared")
                        return
                    # An escorted passer's wait is still holding its base
                    # mission; it is past the yielder now, so let it go.
                    self._release_wait(
                        command.command_id, step.cleared.robot_id, "released: passer cleared"
                    )
                    _admit(step.next, "released: previous passer cleared")

                def _admit(passer, release_detail: str) -> None:
                    if passer.escort_m is not None:
                        # Odom yaw 0 faces each robot's base goal (every robot
                        # spawns facing its goal), so no map-frame knowledge.
                        self._adapter.drive_heading(
                            passer.robot_id,
                            target_yaw_rad=0.0,
                            distance_m=float(passer.escort_m),
                            on_result=lambda status, detail, rid=passer.robot_id: (
                                self.get_logger().info(f"escort {rid}: {status} {detail}")
                            ),
                        )
                    elif chain.is_multi_passer:
                        self._release_wait(command.command_id, passer.robot_id, release_detail)
                    else:
                        # No escort grounded: release the linked wait NOW so
                        # the passer traverses under Nav2 while the yielder is
                        # parked. Released only at terminal, the passer sat
                        # frozen through the whole hold and both robots
                        # re-entered the aisle together, re-deadlocking
                        # (observed 2026-07-03).
                        self._release_linked_waits(
                            command.command_id, "COMPLETED", release_detail=release_detail
                        )
                    odom_subs.append(
                        self.create_subscription(
                            Odometry,
                            f"/{passer.robot_id}/odom",
                            lambda odom_msg, rid=passer.robot_id: _on_passer_odom(rid, odom_msg),
                            10,
                        )
                    )

                if chain is None:
                    # No passer named: nothing to watch, release every linked
                    # wait at hold start (same reason as the no-escort case).
                    self._release_linked_waits(
                        command.command_id, "COMPLETED",
                        release_detail="released: yield holding",
                    )
                else:
                    _admit(chain.current, "released: yield holding")

                t = self.create_timer(_hold_sec, _hold_expired)
                timer_ref["timer"] = t

            def _on_pull_off_result(
                status: str,
                detail: str,
                command=msg,
                _hold_sec: float = hold_sec,
            ) -> None:
                if status == "ACTIVE":
                    # sidestep's own start signal; the pull-off ACTIVE was
                    # already published by _on_backup_result.
                    return
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
                    self._adapter.sidestep(
                        robot_id,
                        float(pull_off_lateral),
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

    def _make_nav_result_handler(self, command: CoordinationCommand):
        """Wrap `_publish_status` for a Nav2 goal/waypoint leg with the watchdog.

        Arms the liveness watchdog when Nav2 accepts the goal (the ACTIVE
        callback); terminal statuses flow through `_publish_status`, whose
        registry bookkeeping disarms it (see `_update_in_flight_registry`).

        Args:
            command: The coordination command this Nav2 leg belongs to.

        Returns:
            An `on_result(status, detail)` callback for `Nav2Adapter`.
        """

        def _on_result(status: str, detail: str) -> None:
            if status == "ACTIVE":
                self._arm_nav_watchdog(command)
            self._publish_status(command, status, detail)

        return _on_result

    def _arm_nav_watchdog(self, command: CoordinationCommand) -> None:
        """Arm an OS-monotonic deadline for an in-flight Nav2 leg.

        `timeout_sec <= 0` on the wire means "absent", so the floor applies.
        The deadline uses `time.monotonic()`, never the node clock: this node
        runs with `use_sim_time`, and a sim-clock deadline would freeze along
        with `/clock` — defeating a watchdog meant to catch a hung server.
        """
        timeout_sec = float(getattr(command, "timeout_sec", 0.0) or 0.0)
        deadline = time.monotonic() + max(
            self.NAV_WATCHDOG_TIMEOUT_MULTIPLIER * timeout_sec,
            self.NAV_WATCHDOG_FLOOR_SEC,
        )
        self._nav_watchdogs[(command.command_id, command.robot_id)] = (deadline, command)

    def _sweep_nav_watchdogs(self) -> None:
        """Fail Nav2 legs whose monotonic deadline has passed.

        Runs on a coarse periodic node timer. That timer ticks sim time, but
        in the scenario that matters — sim alive, Nav2 action server hung —
        sim timers still fire; a fully-frozen sim freezes the robots too and
        is out of scope (mirrors `Nav2Adapter.backup`'s tick-based deadline).
        The in-flight check before firing guards against double-publishing if
        a real terminal status landed concurrently with the sweep.
        """
        now = time.monotonic()
        for key in [k for k, (deadline, _) in self._nav_watchdogs.items() if now >= deadline]:
            _deadline, command = self._nav_watchdogs.pop(key)
            if self._in_flight.get(command.robot_id) != command.command_id:
                continue
            self.get_logger().error(
                f"nav2 leg watchdog fired command={command.command_id} robot={command.robot_id}"
            )
            self._adapter.cancel(command.robot_id)
            self._publish_status(command, "FAILED", "nav2 leg timed out")

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
            f"status published command={command.command_id} "
            f"robot={command.robot_id} status={status}"
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

    def _release_wait(self, command_id: str, robot_id: str, detail: str) -> None:
        """Complete one still-active linked wait, if it is still active.

        The ordered release of a multi-passer yield: unlike
        `_release_linked_waits`, later passers' waits under the same command
        stay in place.

        Args:
            command_id: Command identifier shared by the yield and the wait.
            robot_id: The passer whose wait is released.
            detail: Status detail for the released wait.
        """
        wait = self._active_waits.pop((command_id, robot_id), None)
        if wait is None:
            return
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

        A terminal status also disarms the Nav2-leg watchdog for exactly this
        `(command_id, robot_id)`. Keeping the disarm here — the single choke
        point every published status passes through — means the watchdog
        cannot drift from what was actually published.

        Args:
            robot_id: Robot identifier the status belongs to.
            command_id: Command identifier the status belongs to.
            status: Status value about to be published (e.g. ACTIVE, COMPLETED, FAILED).
        """
        if status == "ACTIVE":
            self._in_flight[robot_id] = command_id
        elif status in ("COMPLETED", "FAILED"):
            self._nav_watchdogs.pop((command_id, robot_id), None)
            if self._in_flight.get(robot_id) == command_id:
                del self._in_flight[robot_id]

    def _schedule_status_republish(self, msg: CoordinationStatus, delay_sec: float) -> None:
        timer_ref = {}

        def republish() -> None:
            self._status_pub.publish(msg)
            self.get_logger().info(
                f"status republished command={msg.command_id} "
                f"robot={msg.robot_id} status={msg.status}"
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

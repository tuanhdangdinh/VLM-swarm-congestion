"""Thin rclpy relay node for the Branch B cmd_vel watchdog (M4 Phase 1 / FR6.4.8).

`ROS2SubscribeTwist` has no built-in command timeout, so each robot's drive graph
subscribes `/<robot_id>/cmd_vel_safe` (see `ros_graphs.create_robot_ros_graph`)
instead of the public `/<robot_id>/cmd_vel`. This node sits in front: it forwards
the last `/cmd_vel` to `/cmd_vel_safe` at 20 Hz and zeroes it once no command has
arrived for `command_timeout_sec`, so a single non-repeating Twist coasts to a
stop. The public `/<robot_id>/cmd_vel` contract for M4/M5 is unchanged.

Because `/cmd_vel_safe` is the *only* topic the drive graphs consume, this relay
is also where M4's safety stop is made authoritative: while a robot appears in
`/safety/holds` its `cmd_vel_safe` is zero regardless of which `/cmd_vel`
publisher (safety monitor, Nav2 controller, collision monitor, docking server)
wrote last. See `docs/specs/module4/safety-monitor.md` §8.

The stale-command decision lives in the rclpy-free `cmd_vel_watchdog.watchdog_velocity`
core (unit-tested offline); this module is the thin ROS 2 plumbing around it
(CLAUDE.md: keep reusable logic outside node classes). Run with `use_sim_time=True`
so the timeout is measured against Isaac's `/clock`, matching the simulation step
rate rather than wall time.
"""
from __future__ import annotations

import threading

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String

from isaac.vgu_sim.cmd_vel_watchdog import SafetyHoldState, parse_holds, watchdog_velocity


class CmdVelWatchdog(Node):
    """Relay `/cmd_vel` -> `/cmd_vel_safe`, zeroing it while held or once stale."""

    def __init__(
        self,
        robot_id: str,
        timeout_sec: float,
        holds: SafetyHoldState | None = None,
    ) -> None:
        # use_sim_time so get_clock() follows /clock; the timeout is in sim seconds.
        super().__init__(
            f"{robot_id}_cmd_vel_watchdog",
            parameter_overrides=[
                Parameter("use_sim_time", Parameter.Type.BOOL, True)
            ],
        )
        self._robot_id = robot_id
        self._timeout = timeout_sec
        self._holds = holds if holds is not None else SafetyHoldState()
        self._last: tuple[float, float] = (0.0, 0.0)
        self._last_stamp: float | None = None
        self._pub = self.create_publisher(Twist, f"/{robot_id}/cmd_vel_safe", 10)
        self.create_subscription(Twist, f"/{robot_id}/cmd_vel", self._on_cmd, 10)
        self.create_timer(0.05, self._tick)  # 20 Hz relay/guard

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_cmd(self, msg: Twist) -> None:
        # Recorded even while held: a hold gates the output only, so a release
        # resumes on the publisher's live command instead of waiting out a
        # freshly-expired timeout.
        self._last = (msg.linear.x, msg.angular.z)
        self._last_stamp = self._now()

    def _tick(self) -> None:
        elapsed = None if self._last_stamp is None else self._now() - self._last_stamp
        vx, wz = watchdog_velocity(
            elapsed, self._last, self._timeout, self._holds.is_held(self._robot_id)
        )
        out = Twist()
        out.linear.x, out.angular.z = vx, wz
        self._pub.publish(out)


class SafetyHoldListener(Node):
    """Subscribe `/safety/holds` once and feed the shared `SafetyHoldState`."""

    def __init__(self, holds: SafetyHoldState) -> None:
        super().__init__("cmd_vel_watchdog_holds")
        self._holds = holds
        self.create_subscription(String, "/safety/holds", self._on_holds, 10)

    def _on_holds(self, msg: String) -> None:
        held, ok = parse_holds(msg.data)
        if not ok:
            # Keep the previous hold set: applying an empty set on a corrupt
            # message would release the safety stop. The monitor's 1 s
            # unconditional heartbeat re-delivers a genuine release.
            self.get_logger().warning(f"safety/holds parse failed payload={msg.data!r}")
            return
        engaged, released = self._holds.set_held(held)
        for robot_id in sorted(engaged):
            self.get_logger().info(f"cmd_vel relay hold engaged robot={robot_id}")
        for robot_id in sorted(released):
            self.get_logger().info(f"cmd_vel relay hold released robot={robot_id}")


def spin_in_thread(
    robot_ids: list[str],
    timeout_sec: float,
    enforce_safety_holds: bool = True,
) -> tuple[SingleThreadedExecutor, list[Node]]:
    """Start one watchdog per robot in a background executor thread.

    Mirrors `tests/simulation/stop_stub.StopStubNode.spin_in_thread`: the caller
    keeps the sim loop on the main thread while the watchdogs relay in the
    background. Returns the executor (call `.shutdown()` to stop) and the nodes.

    Args:
        robot_ids: Robot ids to guard (one node each).
        timeout_sec: Stale-command threshold in sim seconds (config.command_timeout_sec).
        enforce_safety_holds: When True (default), add the `/safety/holds`
            listener so a held robot's `cmd_vel_safe` is zeroed authoritatively.
            False is a kill-switch that restores plain stale-command relaying.

    Returns:
        The running `(executor, nodes)`; the daemon spin thread stops when the
        executor is shut down or the process exits. `nodes` holds the per-robot
        relays followed by the hold listener when enforcement is on.
    """
    if not rclpy.ok():
        rclpy.init(args=None)
    executor = SingleThreadedExecutor()
    holds = SafetyHoldState()
    nodes: list[Node] = [CmdVelWatchdog(rid, timeout_sec, holds) for rid in robot_ids]
    if enforce_safety_holds:
        nodes.append(SafetyHoldListener(holds))
    for node in nodes:
        executor.add_node(node)
    threading.Thread(target=executor.spin, daemon=True).start()
    return executor, nodes


def main(enforce_safety_holds: bool = True) -> None:
    """Standalone entry point: guard robot_1 and robot_2 (head_on_deadlock).

    Args:
        enforce_safety_holds: See `spin_in_thread`.
    """
    from isaac.vgu_sim.config import RobotAssetConfig

    timeout = RobotAssetConfig().command_timeout_sec
    rclpy.init(args=None)
    executor = SingleThreadedExecutor()
    holds = SafetyHoldState()
    nodes: list[Node] = [
        CmdVelWatchdog("robot_1", timeout, holds),
        CmdVelWatchdog("robot_2", timeout, holds),
    ]
    if enforce_safety_holds:
        nodes.append(SafetyHoldListener(holds))
    for node in nodes:
        executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()

"""Thin rclpy relay node for the Branch B cmd_vel watchdog (M4 Phase 1 / FR6.4.8).

`ROS2SubscribeTwist` has no built-in command timeout, so each robot's drive graph
subscribes `/<robot_id>/cmd_vel_safe` (see `ros_graphs.create_robot_ros_graph`)
instead of the public `/<robot_id>/cmd_vel`. This node sits in front: it forwards
the last `/cmd_vel` to `/cmd_vel_safe` at 20 Hz and zeroes it once no command has
arrived for `command_timeout_sec`, so a single non-repeating Twist coasts to a
stop. The public `/<robot_id>/cmd_vel` contract for M4/M5 is unchanged.

The stale-command decision lives in the rclpy-free `cmd_vel_watchdog.watchdog_velocity`
core (unit-tested offline); this module is the thin ROS 2 plumbing around it
(CLAUDE.md: keep reusable logic outside node classes). Run with `use_sim_time=True`
so the timeout is measured against Isaac's `/clock`, matching the simulation step
rate rather than wall time.
"""
from __future__ import annotations

import math
import threading

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformException, TransformListener

from isaac.vgu_sim.cmd_vel_watchdog import (
    forward_min_range,
    forward_peer_distance,
    watchdog_velocity,
)

FORWARD_STOP_RANGE_M = 0.32
FORWARD_STOP_SECTOR_DEG = 35.0
PEER_STOP_RANGE_M = 0.32
PEER_LATERAL_HALF_WIDTH_M = 0.25


class CmdVelWatchdog(Node):
    """Relay `/cmd_vel` -> `/cmd_vel_safe`, zeroing the command once it goes stale."""

    def __init__(self, robot_id: str, timeout_sec: float, peer_ids: list[str] | None = None) -> None:
        # use_sim_time so get_clock() follows /clock; the timeout is in sim seconds.
        super().__init__(
            f"{robot_id}_cmd_vel_watchdog",
            parameter_overrides=[
                Parameter("use_sim_time", Parameter.Type.BOOL, True)
            ],
        )
        self._timeout = timeout_sec
        self._robot_id = robot_id
        self._peer_ids = peer_ids or []
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._last: tuple[float, float] = (0.0, 0.0)
        self._last_stamp: float | None = None
        self._forward_obstacle_m: float | None = None
        self._pub = self.create_publisher(Twist, f"/{robot_id}/cmd_vel_safe", 10)
        self.create_subscription(Twist, f"/{robot_id}/cmd_vel", self._on_cmd, 10)
        self.create_subscription(LaserScan, f"/{robot_id}/scan", self._on_scan, 10)
        self.create_timer(0.05, self._tick)  # 20 Hz relay/guard

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_cmd(self, msg: Twist) -> None:
        self._last = (msg.linear.x, msg.angular.z)
        self._last_stamp = self._now()

    def _on_scan(self, msg: LaserScan) -> None:
        self._forward_obstacle_m = forward_min_range(
            list(msg.ranges),
            msg.angle_min,
            msg.angle_increment,
            FORWARD_STOP_SECTOR_DEG,
        )

    def _peer_forward_obstacle(self) -> float:
        try:
            own_tf = self._tf_buffer.lookup_transform(
                "map", f"{self._robot_id}/base_link", rclpy.time.Time()
            ).transform
        except TransformException:
            return math.inf

        q = own_tf.rotation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        own_pose = (own_tf.translation.x, own_tf.translation.y, yaw)
        closest = math.inf
        for peer_id in self._peer_ids:
            try:
                peer_tf = self._tf_buffer.lookup_transform(
                    "map", f"{peer_id}/base_link", rclpy.time.Time()
                ).transform
            except TransformException:
                continue
            distance = forward_peer_distance(
                own_pose,
                (peer_tf.translation.x, peer_tf.translation.y),
                PEER_LATERAL_HALF_WIDTH_M,
            )
            closest = min(closest, distance)
        return closest

    def _tick(self) -> None:
        elapsed = None if self._last_stamp is None else self._now() - self._last_stamp
        forward_obstacle = min(
            self._forward_obstacle_m
            if self._forward_obstacle_m is not None
            else math.inf,
            self._peer_forward_obstacle(),
        )
        vx, wz = watchdog_velocity(
            elapsed,
            self._last,
            self._timeout,
            forward_obstacle,
            max(FORWARD_STOP_RANGE_M, PEER_STOP_RANGE_M),
        )
        out = Twist()
        out.linear.x, out.angular.z = vx, wz
        self._pub.publish(out)


def spin_in_thread(
    robot_ids: list[str], timeout_sec: float
) -> tuple[SingleThreadedExecutor, list[CmdVelWatchdog]]:
    """Start one watchdog per robot in a background executor thread.

    Mirrors `tests/simulation/stop_stub.StopStubNode.spin_in_thread`: the caller
    keeps the sim loop on the main thread while the watchdogs relay in the
    background. Returns the executor (call `.shutdown()` to stop) and the nodes.

    Args:
        robot_ids: Robot ids to guard (one node each).
        timeout_sec: Stale-command threshold in sim seconds (config.command_timeout_sec).

    Returns:
        The running `(executor, nodes)`; the daemon spin thread stops when the
        executor is shut down or the process exits.
    """
    if not rclpy.ok():
        rclpy.init(args=None)
    executor = SingleThreadedExecutor()
    nodes = [
        CmdVelWatchdog(rid, timeout_sec, [peer for peer in robot_ids if peer != rid])
        for rid in robot_ids
    ]
    for node in nodes:
        executor.add_node(node)
    threading.Thread(target=executor.spin, daemon=True).start()
    return executor, nodes


def main() -> None:
    """Standalone entry point: guard robot_1 and robot_2 (head_on_deadlock)."""
    from isaac.vgu_sim.config import RobotAssetConfig

    timeout = RobotAssetConfig().command_timeout_sec
    rclpy.init(args=None)
    executor = SingleThreadedExecutor()
    for node in (
        CmdVelWatchdog("robot_1", timeout, ["robot_2"]),
        CmdVelWatchdog("robot_2", timeout, ["robot_1"]),
    ):
        executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()

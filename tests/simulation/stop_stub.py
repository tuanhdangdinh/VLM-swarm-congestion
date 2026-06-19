# tests/simulation/stop_stub.py
from __future__ import annotations

import math
import threading

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

_FORWARD_STOP_RANGE_M = 0.25
_FORWARD_SECTOR_DEG = 30
_MAX_STUB_SPEED_MPS = 0.15


def _check_speed(speed_mps: float) -> None:
    # Shared safety guard for every test-side commander (FR6.8.5a). Keeping it in
    # one place stops a second driver from quietly raising the cap.
    if speed_mps > _MAX_STUB_SPEED_MPS:
        raise ValueError("stop stub speed must not exceed 0.15 m/s (spec FR6.8.5a)")


class StopStub:
    def __init__(self, robot_id: str, speed_mps: float = 0.10) -> None:
        _check_speed(speed_mps)
        self._robot_id = robot_id
        self._speed = speed_mps

    def on_scan(self, msg: LaserScan) -> Twist:
        n = len(msg.ranges)
        if n == 0:
            return Twist()

        angle_inc_deg = math.degrees(msg.angle_increment)
        sector_steps = max(1, round(_FORWARD_SECTOR_DEG / angle_inc_deg))

        forward_ranges = (
            list(msg.ranges[:sector_steps])
            + list(msg.ranges[max(0, n - sector_steps):])
        )

        valid = [r for r in forward_ranges
                 if not math.isnan(r) and not math.isinf(r) and r > 0]
        min_range = min(valid) if valid else float("inf")

        cmd = Twist()
        if min_range >= _FORWARD_STOP_RANGE_M:
            cmd.linear.x = self._speed
        return cmd


class StopStubNode(Node):
    def __init__(self, robot_ids: list[str], speed_mps: float = 0.10) -> None:
        super().__init__("stop_stub")
        self._stubs = {rid: StopStub(rid, speed_mps) for rid in robot_ids}
        self._pubs = {}
        self._subs = []

        for rid in robot_ids:
            pub = self.create_publisher(Twist, f"/{rid}/cmd_vel", 10)
            self._pubs[rid] = pub

            def _on_scan(msg: LaserScan, robot_id: str = rid) -> None:
                cmd = self._stubs[robot_id].on_scan(msg)
                self._pubs[robot_id].publish(cmd)

            sub = self.create_subscription(
                LaserScan, f"/{rid}/scan", _on_scan, 5
            )
            self._subs.append(sub)

    @classmethod
    def spin_in_thread(
        cls, robot_ids: list[str], speed_mps: float = 0.10
    ) -> StopStubNode:
        rclpy.init(args=None)
        node = cls(robot_ids, speed_mps)
        t = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        t.start()
        return node


class FixedTwistDriver(Node):
    """ROS2 node that drives robots straight forward at a capped speed.

    Publishes a constant forward `Twist` (`linear.x = speed`) to each
    `/<robot_id>/cmd_vel` at 10 Hz. Unlike `StopStubNode` it does not read the
    laser scan; it is the active commander for the Phase 1 drive-chain
    acceptance procedure. Speed is capped at 0.15 m/s by the same guard as
    `StopStub` (FR6.8.5a). Calling `request_stop` ceases publishing so the
    `CmdVelWatchdog` (Branch B) is what zeroes the wheels, exercising the
    command-timeout path.
    """

    _PUBLISH_HZ = 10.0

    def __init__(self, robot_ids: list[str], speed_mps: float = 0.10) -> None:
        _check_speed(speed_mps)  # before super().__init__ so the cap is enforceable offline
        super().__init__("fixed_twist_driver")
        self._speed = speed_mps
        self._pubs = {
            rid: self.create_publisher(Twist, f"/{rid}/cmd_vel", 10)
            for rid in robot_ids
        }
        self._timer = self.create_timer(1.0 / self._PUBLISH_HZ, self._publish_forward)

    def _publish_forward(self) -> None:
        cmd = Twist()
        cmd.linear.x = self._speed
        for pub in self._pubs.values():
            pub.publish(cmd)

    def request_stop(self) -> None:
        """Stop publishing so the watchdog (not this node) zeroes the wheels."""
        self._timer.cancel()

    @classmethod
    def spin_in_thread(
        cls, robot_ids: list[str], speed_mps: float = 0.10
    ) -> FixedTwistDriver:
        if not rclpy.ok():
            rclpy.init(args=None)
        node = cls(robot_ids, speed_mps)
        t = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        t.start()
        return node

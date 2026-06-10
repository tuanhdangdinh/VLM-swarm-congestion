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


class StopStub:
    def __init__(self, robot_id: str, speed_mps: float = 0.10) -> None:
        if speed_mps > 0.15:
            raise ValueError("stop stub speed must not exceed 0.15 m/s (spec FR6.8.5a)")
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
    ) -> "StopStubNode":
        rclpy.init(args=None)
        node = cls(robot_ids, speed_mps)
        t = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        t.start()
        return node

#!/usr/bin/env python3
"""Costmap-source probe: park, clear, then hold still or rotate in place.

VM-only phase controller for the phantom-lethal-costmap diagnosis
(docs/reports/2026-10-05-costmap-source-probe.md). Runs inside the `vgu_ros`
container next to a live fc_launch stack whose M5 drives robot_1 to a park
pose (scripts/vm/v2_overlay.py `costmap_probe_a` / `costmap_probe_b`). It
records nothing heavy itself: `ros2 bag record` (driver) captures the scan,
TF, odometry, scene state and the global costmap, so no Python receive queue
can lag or drop them (the waypoint probe's rows ran ~2 s behind their content).

Sequence:

1. Wait for the park: robot_1 has moved >= `MOVED_M` from the odometry
   origin (IsaacComputeOdometry is spawn-relative, identity at t=0, so this
   holds even when the probe starts after the drive) and then stayed still
   (|vx| and |wz| below `STILL_EPS`) for `STILL_SEC` sim seconds.
2. For each phase, in order: call the global costmap's
   `clear_entirely_global_costmap` (so every phase starts from the static map
   only), publish a `phase_start` marker, run the phase, publish `phase_end`.
   - `static:<sec>` -- publish nothing; the robot stays parked.
   - `rot:<wz>:<sec>:<hold>` -- publish `wz` rad/s on `/<robot>/cmd_vel`
     (the watchdog relay's input, so the collision monitor, idle with Nav2
     idle, plays no part) for `sec` sim seconds, then zero, then hold still
     `hold` sim seconds.

Markers go to the `/costmap_probe/phase` topic (recorded in the bag) and to
OUT_JSONL, each with sim time.

Usage: costmap_probe.py OUT_JSONL TIMEOUT_WALL_SEC PHASES [ROBOT_ID] [PARK_ODOM_X,Y]
    PARK_ODOM_X,Y: the park pose in robot_1's odom frame (map pose minus
    spawn); when given, the park also requires odometry within
    `PARK_TOL_M` of it, so a mid-route pause is not taken for the park.
    PHASES e.g. "static:120,rot:1.0:6.283:4,rot:0.3:20.94:4"
"""
import json
import math
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from nav2_msgs.srv import ClearEntireCostmap
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String

MOVED_M = 0.3
STILL_EPS = 0.01
STILL_SEC = 3.0
PARK_TOL_M = 0.25
CMD_PERIOD_SEC = 0.05


def parse_phases(spec: str) -> list[dict]:
    """Parse the PHASES argument into phase dicts."""
    phases = []
    for item in spec.split(","):
        parts = item.split(":")
        if parts[0] == "static" and len(parts) == 2:
            phases.append({"kind": "static", "sec": float(parts[1])})
        elif parts[0] == "rot" and len(parts) == 4:
            phases.append({"kind": "rot", "wz": float(parts[1]), "sec": float(parts[2]),
                           "hold": float(parts[3])})
        else:
            raise ValueError(f"bad phase {item!r}")
    return phases


class CostmapProbe(Node):
    """Drive the park/clear/hold/rotate sequence and mark each phase."""

    def __init__(self, out_path: str, robot_id: str,
                 park_odom: tuple[float, float] | None = None) -> None:
        super().__init__("costmap_probe",
                         parameter_overrides=[Parameter("use_sim_time", value=True)])
        self._out = open(out_path, "a", encoding="utf-8")
        self._robot = robot_id
        ns = f"/{robot_id}"
        self._odom = None
        self._park_odom = park_odom
        # depth 1: only the newest odometry matters for the stillness test.
        self.create_subscription(Odometry, f"{ns}/odom", self._on_odom, 1)
        self._cmd = self.create_publisher(Twist, f"{ns}/cmd_vel", 10)
        self._marker = self.create_publisher(String, "/costmap_probe/phase", 10)
        self._clear = self.create_client(
            ClearEntireCostmap, f"{ns}/global_costmap/clear_entirely_global_costmap")

    def sim(self) -> float:
        """Current sim time in seconds."""
        return self.get_clock().now().nanoseconds / 1e9

    def mark(self, event: str, **fields) -> None:
        """Write one marker row to the JSONL and the marker topic."""
        row = {"event": event, "sim": round(self.sim(), 3), "wall": round(time.time(), 3)}
        row.update(fields)
        text = json.dumps(row)
        self._out.write(text + "\n")
        self._out.flush()
        self._marker.publish(String(data=text))

    def _on_odom(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self._odom = (p.x, p.y, 2.0 * math.atan2(q.z, q.w),
                      msg.twist.twist.linear.x, msg.twist.twist.angular.z,
                      msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9)

    def spin_for(self, sim_sec: float, deadline: float, wz: float | None = None) -> bool:
        """Spin for `sim_sec` sim seconds, publishing `wz` if given."""
        end = self.sim() + sim_sec
        next_cmd = 0.0
        while rclpy.ok() and time.monotonic() < deadline and self.sim() < end:
            rclpy.spin_once(self, timeout_sec=0.02)
            if wz is not None and time.monotonic() >= next_cmd:
                msg = Twist()
                msg.angular.z = wz
                self._cmd.publish(msg)
                next_cmd = time.monotonic() + CMD_PERIOD_SEC
        return self.sim() >= end

    def wait_parked(self, deadline: float) -> bool:
        """Block until robot_1 has moved and then stayed still STILL_SEC."""
        still_since = None
        moved = False
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self._odom is None:
                continue
            x, y, _, vx, wz, _ = self._odom
            if not moved and math.hypot(x, y) >= MOVED_M:
                moved = True
                self.mark("moved", odom_x=round(x, 3), odom_y=round(y, 3))
            if not moved:
                continue
            near = self._park_odom is None or math.hypot(
                x - self._park_odom[0], y - self._park_odom[1]) <= PARK_TOL_M
            if near and abs(vx) < STILL_EPS and abs(wz) < STILL_EPS:
                still_since = self.sim() if still_since is None else still_since
                if self.sim() - still_since >= STILL_SEC:
                    self.mark("parked", odom=[round(v, 4) for v in self._odom])
                    return True
            else:
                still_since = None
        return False

    def clear(self, deadline: float) -> bool:
        """Clear the whole global costmap; True when the service answered."""
        if not self._clear.wait_for_service(timeout_sec=10.0):
            self.mark("clear_unavailable")
            return False
        future = self._clear.call_async(ClearEntireCostmap.Request())
        while rclpy.ok() and time.monotonic() < deadline and not future.done():
            rclpy.spin_once(self, timeout_sec=0.05)
        ok = future.done() and future.exception() is None
        self.mark("cleared" if ok else "clear_failed",
                  error=None if ok else str(future.exception()))
        return ok

    def run(self, phases: list[dict], deadline: float) -> int:
        """Run the full sequence; returns a process exit code."""
        self.mark("probe_start", phases=phases, robot=self._robot)
        if not self.wait_parked(deadline):
            self.mark("park_timeout")
            return 2
        for i, phase in enumerate(phases):
            if not self.clear(deadline):
                return 3
            self.mark("phase_start", index=i, **phase)
            if phase["kind"] == "static":
                done = self.spin_for(phase["sec"], deadline)
            else:
                done = self.spin_for(phase["sec"], deadline, wz=phase["wz"])
                for _ in range(5):
                    self._cmd.publish(Twist())
                done = done and self.spin_for(phase["hold"], deadline)
            odom = [round(v, 4) for v in self._odom] if self._odom else None
            self.mark("phase_end", index=i, completed=done, odom=odom)
            if not done:
                return 4
        self.mark("probe_done")
        return 0


def main() -> int:
    """CLI entry point."""
    out_path, timeout, spec = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    robot_id = sys.argv[4] if len(sys.argv) > 4 else "robot_1"
    park_odom = tuple(float(v) for v in sys.argv[5].split(",")) if len(sys.argv) > 5 else None
    phases = parse_phases(spec)
    rclpy.init()
    node = CostmapProbe(out_path, robot_id, park_odom)
    try:
        code = node.run(phases, time.monotonic() + timeout)
    finally:
        for _ in range(5):
            node._cmd.publish(Twist())
        node.mark("probe_end")
        node.destroy_node()
        rclpy.shutdown()
    return code


if __name__ == "__main__":
    sys.exit(main())

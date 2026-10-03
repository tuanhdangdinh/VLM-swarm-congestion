#!/usr/bin/env python3
"""Loop-detour family: sample robot_1's Nav2 view (VM-only helper).

Adapted from the phase-1 loop pre-emption sampler
(data/logs/vm_runs/loop_preemption/_vm_driver/loop_preemption_sampler.py,
itself from the T3a costmap sampler): subscribe to robot_1's global/local
costmap + /plan + /clock and write one JSON line every ~2 wall s. Boxes for
the loop_detour_* geometry (isaac/config/scenarios/loop_detour_permanent.yaml):
  - BLOCKER: the blocker's lidar footprint, x in [0.875, 1.125],
    y in [-0.25, 0.03].
  - GAP: the 0.22 m gap north of it, y in [0.03, 0.25] -- must stay
    sub-lethal in the global costmap (NavFn plans through it) for the
    design control to hold.
  - Every row carries the current global plan's max |y| and whether ANY
    pose has y > 0.6 (into the connector band / second aisle): before a
    reroute is dispatched that is the self-detour (pre-emption) signal.

Usage: loop_family_sampler.py OUT_JSONL DURATION_WALL_SEC
"""
import json
import sys
import time

import rclpy
from nav_msgs.msg import OccupancyGrid, Path
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

# x0, x1, y0, y1 in world frame.
BLOCKER_BOX = (0.875, 1.125, -0.25, 0.03)  # blocker lidar footprint
GAP_BOX = (0.875, 1.125, 0.03, 0.25)       # the 0.22 m design gap
SECOND_AISLE_Y = 0.6                       # primary/second-aisle boundary


def box_max(grid, box):
    if grid is None:
        return None
    info = grid.info
    res, ox, oy = info.resolution, info.origin.position.x, info.origin.position.y
    best = None
    for row in range(info.height):
        y = oy + (row + 0.5) * res
        if not (box[2] <= y <= box[3]):
            continue
        for col in range(info.width):
            x = ox + (col + 0.5) * res
            if box[0] <= x <= box[1]:
                v = grid.data[row * info.width + col]
                best = v if best is None else max(best, v)
    return best


def gap_bottleneck(grid, box):
    """Max over the box's x-columns of the cheapest cell in that column.

    Below 99 (an OccupancyGrid-scaled inscribed cost) every column has a
    cell NavFn can traverse, i.e. the gap is still plannable.
    """
    if grid is None:
        return None
    info = grid.info
    res, ox, oy = info.resolution, info.origin.position.x, info.origin.position.y
    worst = None
    for col in range(info.width):
        x = ox + (col + 0.5) * res
        if not (box[0] <= x <= box[1]):
            continue
        cheapest = None
        for row in range(info.height):
            y = oy + (row + 0.5) * res
            if box[2] <= y <= box[3]:
                v = grid.data[row * info.width + col]
                cheapest = v if cheapest is None else min(cheapest, v)
        if cheapest is not None:
            worst = cheapest if worst is None else max(worst, cheapest)
    return worst


class Sampler(Node):
    def __init__(self):
        super().__init__("loop_family_sampler")
        latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.g = self.l = self.plan = None
        self.sim = None
        self.plan_n = 0
        self.create_subscription(OccupancyGrid, "/robot_1/global_costmap/costmap", self._g, latched)
        self.create_subscription(OccupancyGrid, "/robot_1/local_costmap/costmap", self._l, latched)
        self.create_subscription(Path, "/robot_1/plan", self._p, 10)
        best_effort = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(Clock, "/clock", self._c, best_effort)

    def _g(self, m):
        self.g = m

    def _l(self, m):
        self.l = m

    def _p(self, m):
        self.plan = m
        self.plan_n += 1

    def _c(self, m):
        self.sim = m.clock.sec + m.clock.nanosec * 1e-9

    def row(self):
        plan = None
        if self.plan is not None and self.plan.poses:
            pts = [(p.pose.position.x, p.pose.position.y) for p in self.plan.poses]
            ys = [y for _, y in pts]
            plan = {
                "n": len(pts),
                "end": [round(pts[-1][0], 2), round(pts[-1][1], 2)],
                "max_abs_y": round(max(abs(y) for y in ys), 3),
                "entered_second_aisle": any(y > SECOND_AISLE_Y for y in ys),
                "msgs": self.plan_n,
            }
        return {
            "wall": round(time.time(), 2),
            "sim": None if self.sim is None else round(self.sim, 2),
            "global_blocker_max": box_max(self.g, BLOCKER_BOX),
            "global_gap_max": box_max(self.g, GAP_BOX),
            "local_blocker_max": box_max(self.l, BLOCKER_BOX),
            "local_gap_max": box_max(self.l, GAP_BOX),
            "global_gap_bottleneck": gap_bottleneck(self.g, GAP_BOX),
            "plan": plan,
        }


def main():
    out, dur = sys.argv[1], float(sys.argv[2])
    rclpy.init()
    node = Sampler()
    end = time.time() + dur
    nxt = time.time()
    with open(out, "a") as f:
        while time.time() < end and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.2)
            if time.time() >= nxt:
                f.write(json.dumps(node.row()) + "\n")
                f.flush()
                nxt = time.time() + 2.0
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

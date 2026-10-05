#!/usr/bin/env python3
"""Declared-reroute validation probe: trigger once, record the command chain.

VM-only helper for the follow_waypoints validation
(docs/reports/2026-10-05-follow-waypoints-validation.md). Runs inside the
`vgu_ros` container next to a live fc_launch stack and does two things:

1. **Trigger.** On a blocker-free map M5's progress detector never fires, so
   the mock's scripted `reroute` would never be requested. Once robot_1's M1
   pose crosses `TRIGGER_X` (moving east in the primary aisle), call M5's
   `/orchestrator/trigger_analysis` service exactly once. M5 then runs the
   ordinary pipeline: mock decision -> M3 grounding (declared
   `reroute_waypoints`) -> M4 `follow_waypoints`. `TRIGGER_X=none` records
   only.
2. **Record**, one JSON line per sample, for classifying any stall:
   `/<robot>/cmd_vel_nav` (DWB output, before the collision monitor) and
   `/<robot>/cmd_vel` (after it) at full rate, odometry at 10 Hz, every
   `map -> <robot>/odom` transform the camera localizer publishes (change
   only), DWB's `/<robot>/evaluation` summary (valid-trajectory count and
   the chosen twist) at full rate, and the follow_waypoints action's
   feedback/status. Every row carries sim time (`use_sim_time`).

Usage: waypoint_probe.py OUT_JSONL DURATION_WALL_SEC TRIGGER_X [ROBOT_ID]
"""
import json
import sys
import time

import rclpy
from action_msgs.msg import GoalStatusArray
from geometry_msgs.msg import Twist
from nav2_msgs.action import FollowWaypoints
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage

try:
    from dwb_msgs.msg import LocalPlanEvaluation
except ImportError:  # recorded as absent rather than failing the probe
    LocalPlanEvaluation = None

from swarm_interfaces.srv import TriggerCongestionAnalysis

ODOM_PERIOD_SEC = 0.1


class WaypointProbe(Node):
    """Fire one manual analysis trigger and record robot-level command flow."""

    def __init__(self, out_path: str, trigger_x: float | None, robot_id: str) -> None:
        super().__init__(
            "waypoint_probe", parameter_overrides=[Parameter("use_sim_time", value=True)]
        )
        self._out = open(out_path, "a", encoding="utf-8")
        self._robot = robot_id
        self._trigger_x = trigger_x
        self._triggered = False
        self._trigger_future = None
        self._last_odom_sim = -1.0
        self._last_map_odom = None
        self._client = self.create_client(TriggerCongestionAnalysis, "/orchestrator/trigger_analysis")
        ns = f"/{robot_id}"
        self.create_subscription(String, "/perception/scene_state", self._on_scene, 10)
        self.create_subscription(Twist, f"{ns}/cmd_vel_nav", lambda m: self._on_twist("cmd_vel_nav", m), 50)
        self.create_subscription(Twist, f"{ns}/cmd_vel", lambda m: self._on_twist("cmd_vel", m), 50)
        self.create_subscription(Odometry, f"{ns}/odom", self._on_odom, 50)
        self.create_subscription(TFMessage, "/tf", self._on_tf, 100)
        self.create_subscription(
            FollowWaypoints.Impl.FeedbackMessage,
            f"{ns}/follow_waypoints/_action/feedback",
            self._on_wp_feedback,
            10,
        )
        self.create_subscription(
            GoalStatusArray, f"{ns}/follow_waypoints/_action/status", self._on_wp_status, 10
        )
        if LocalPlanEvaluation is not None:
            self.create_subscription(LocalPlanEvaluation, f"{ns}/evaluation", self._on_eval, 50)
        self._write("probe_start", trigger_x=trigger_x, robot=robot_id,
                    evaluation_available=LocalPlanEvaluation is not None)

    def _sim(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _write(self, kind: str, **fields) -> None:
        row = {"kind": kind, "wall": round(time.time(), 3), "sim": round(self._sim(), 3)}
        row.update(fields)
        self._out.write(json.dumps(row) + "\n")
        self._out.flush()

    def _on_scene(self, msg: String) -> None:
        try:
            scene = json.loads(msg.data)
        except ValueError:
            return
        robot = next((r for r in scene.get("robots", []) if r.get("robot_id") == self._robot), None)
        if robot is None:
            return
        if self._trigger_x is None or self._triggered:
            return
        if robot["x"] < self._trigger_x:
            return
        if not self._client.service_is_ready():
            self._write("trigger_deferred", reason="service not ready", x=robot["x"])
            return
        self._triggered = True
        request = TriggerCongestionAnalysis.Request()
        request.reason = f"waypoints_validation x>={self._trigger_x}"
        self._write("trigger_sent", m1_x=robot["x"], m1_y=robot["y"], m1_theta=robot["theta"],
                    m1_status=robot.get("status"), scene_stamp=scene.get("stamp"))
        self._trigger_future = self._client.call_async(request)
        self._trigger_future.add_done_callback(self._on_trigger_response)

    def _on_trigger_response(self, future) -> None:
        try:
            response = future.result()
        except Exception as exc:  # recorded, never silent
            self._write("trigger_response", error=str(exc))
            return
        self._write("trigger_response", accepted=response.accepted,
                    analysis_id=response.analysis_id, message=response.message)

    def _on_twist(self, topic: str, msg: Twist) -> None:
        self._write(topic, vx=round(msg.linear.x, 4), wz=round(msg.angular.z, 4))

    def _on_odom(self, msg: Odometry) -> None:
        sim = self._sim()
        if sim - self._last_odom_sim < ODOM_PERIOD_SEC:
            return
        self._last_odom_sim = sim
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        t = msg.twist.twist
        self._write("odom", x=round(p.x, 4), y=round(p.y, 4), qz=round(q.z, 5), qw=round(q.w, 5),
                    vx=round(t.linear.x, 4), wz=round(t.angular.z, 4))

    def _on_tf(self, msg: TFMessage) -> None:
        child = f"{self._robot}/odom"
        for tf in msg.transforms:
            if tf.header.frame_id != "map" or tf.child_frame_id != child:
                continue
            tr = tf.transform.translation
            rot = tf.transform.rotation
            value = (round(tr.x, 4), round(tr.y, 4), round(rot.z, 5), round(rot.w, 5))
            if value == self._last_map_odom:
                continue
            self._last_map_odom = value
            self._write("map_odom", x=value[0], y=value[1], qz=value[2], qw=value[3])

    def _on_eval(self, msg) -> None:
        valid = [t for t in msg.twists if t.total >= 0.0]
        best = msg.twists[msg.best_index] if 0 <= msg.best_index < len(msg.twists) else None
        row = {"n": len(msg.twists), "n_valid": len(valid), "best_index": int(msg.best_index)}
        if best is not None:
            row.update(best_vx=round(best.traj.velocity.x, 4), best_wz=round(best.traj.velocity.theta, 4),
                       best_total=round(best.total, 3))
        self._write("evaluation", **row)

    def _on_wp_feedback(self, msg) -> None:
        self._write("wp_feedback", current_waypoint=int(msg.feedback.current_waypoint))

    def _on_wp_status(self, msg: GoalStatusArray) -> None:
        self._write("wp_status", statuses=[int(s.status) for s in msg.status_list])


def main() -> int:
    """CLI entry point."""
    out_path = sys.argv[1]
    duration = float(sys.argv[2])
    trigger_x = None if sys.argv[3] == "none" else float(sys.argv[3])
    robot_id = sys.argv[4] if len(sys.argv) > 4 else "robot_1"
    rclpy.init()
    node = WaypointProbe(out_path, trigger_x, robot_id)
    deadline = time.monotonic() + duration
    try:
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
    finally:
        node._write("probe_end")
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""M4 safety monitor: enforce the inter-robot min-distance invariant.

The reasoning loop (M1 -> M5 -> M2 -> M3 -> M4) decides goals at 0.5-2 Hz; this
node is an independent, fast guard on top. It watches M1's global scene state and,
when two robots violate `min_distance_m` from `config/safety.yaml`, issues an
immediate zero-`Twist` on `/<robot_id>/cmd_vel` for each robot in the offending
pair AND cancels the robot's active Nav2 goal.

Cancelling the goal stops DWB from generating new velocity commands. Without the
cancel, DWB keeps publishing to cmd_vel_nav at 20 Hz (which collision_monitor
forwards to cmd_vel) and races with the safety monitor's zero at equal rate —
net result is a slow crawl into the other robot rather than a stop. With the
cancel, DWB stops immediately and the safety zero has no competition.

Coordination command suppression: when M4 dispatches a yield/backup command for
a robot, the safety stop is temporarily lifted so the backup motion can execute.
The exemption clears when the command completes or fails.

Also publishes `/safety/holds` (the latched robot set) so `coordination_client`
can suppress its own 2 s retry loop for a robot whose goal this monitor just
cancelled. Without that signal the two nodes fight over the goal forever: the
monitor cancels it, the retry loop re-issues it 2 s later, the monitor cancels
it again. See docs/specs/module4/safety-monitor.md §4.
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    import rclpy
    from ament_index_python.packages import get_package_share_directory
    from geometry_msgs.msg import Twist
    from nav2_msgs.action import NavigateToPose
    from rclpy.action import ActionClient
    from rclpy.node import Node
    from std_msgs.msg import String
    from swarm_interfaces.msg import CoordinationStatus
    import yaml
except ImportError:
    rclpy = None
    Node = object
    CoordinationStatus = None
    ActionClient = None
    NavigateToPose = None

from swarm_execution.safety import (
    SafetyLimits,
    detect_proximity_violations,
    exceeds_speed_limit,
)


def holds_payload(held: set[str]) -> str:
    """Serialize latched robot ids to the `/safety/holds` JSON payload.

    Kept ROS2-free (module-level, no `self`) so it is unit-testable without a
    running node, alongside the pure functions in `swarm_execution.safety`.

    Args:
        held: Robot ids currently latched under a safety stop.

    Returns:
        JSON string `{"held": [...]}` with ids sorted for deterministic output.
    """
    return json.dumps({"held": sorted(held)})


class SafetyMonitorNode(Node):
    # Hold-republish rate: faster than DWB's 20 Hz so the zero-Twist dominates
    # on cmd_vel between scene updates (goal cancel stops DWB, but republish
    # also guards against any transient cmd_vel publication from other sources).
    HOLD_PERIOD_SEC = 0.025  # 40 Hz

    # /safety/holds refresh rate: independent of HOLD_PERIOD_SEC (that timer is
    # tuned to out-race DWB on cmd_vel; holds only needs to cover a late-joining
    # subscriber before the next scene-driven change, so 1 Hz is plenty).
    HOLDS_REFRESH_PERIOD_SEC = 1.0

    def __init__(self) -> None:
        super().__init__("safety_monitor_node")
        self._limits = _load_safety_limits(self)
        self._stop_pubs: dict[str, object] = {}
        self._nav_clients: dict[str, object] = {}
        self._latched_stops: set[str] = set()
        self._coordinating: set[str] = set()
        self.create_subscription(
            String, "/perception/scene_state", self._on_scene_state, 10
        )
        if CoordinationStatus is not None:
            self.create_subscription(
                CoordinationStatus, "/coordination/status", self._on_coord_status, 10
            )
        self._holds_pub = self.create_publisher(String, "/safety/holds", 10)
        self.create_timer(self.HOLD_PERIOD_SEC, self._hold_stops)
        self.create_timer(self.HOLDS_REFRESH_PERIOD_SEC, self._refresh_holds)
        self.get_logger().info(
            "Safety monitor started "
            f"min_distance_m={self._limits.min_distance_m} "
            f"max_linear_velocity_mps={self._limits.max_linear_velocity_mps}"
        )

    def _on_coord_status(self, msg) -> None:
        robot_id = msg.robot_id
        if not robot_id:
            return
        if msg.status == "ACTIVE":
            self._coordinating.add(robot_id)
        elif msg.status in ("COMPLETED", "FAILED", "CANCELLED"):
            self._coordinating.discard(robot_id)

    def _hold_stops(self) -> None:
        for robot_id in self._latched_stops:
            self._emergency_stop(robot_id)

    def _on_scene_state(self, msg: String) -> None:
        try:
            scene = json.loads(msg.data)
        except (ValueError, TypeError) as exc:
            self.get_logger().warning(f"scene_state parse failed: {exc}")
            return
        positions: list[dict] = []
        speeders: set[str] = set()
        for robot in scene.get("robots", []):
            try:
                robot_id = robot["robot_id"]
                x = float(robot["x"])
                y = float(robot["y"])
            except (KeyError, TypeError, ValueError) as exc:
                self.get_logger().warning(f"skipping malformed robot entry: {exc}")
                continue
            positions.append({"robot_id": robot_id, "x": x, "y": y})
            velocity = robot.get("linear_velocity")
            if velocity is not None and exceeds_speed_limit(
                float(velocity), self._limits.max_linear_velocity_mps
            ):
                speeders.add(robot_id)

        flagged = (
            detect_proximity_violations(positions, self._limits.min_distance_m)
            | speeders
        )
        effective = flagged - self._coordinating

        # Cancel Nav2 goal for newly-flagged robots so DWB stops generating
        # velocity commands. Without this, DWB races with the zero-Twist at
        # equal rate and the robot crawls rather than stopping.
        newly_flagged = effective - self._latched_stops
        for robot_id in newly_flagged:
            self._cancel_nav2_goal(robot_id)

        previous = self._latched_stops
        self._latched_stops = effective
        for robot_id in effective:
            self._emergency_stop(robot_id)
        if effective != previous:
            self._publish_holds()

    def _publish_holds(self) -> None:
        """Publish the current latched-robot set to `/safety/holds`."""
        self._holds_pub.publish(String(data=holds_payload(self._latched_stops)))

    def _refresh_holds(self) -> None:
        """Republish `/safety/holds` on a 1 s cadence while any robot is held.

        Covers a subscriber that joins between two `_on_scene_state`-driven
        changes; a no-op when nothing is latched since the change path already
        published the empty list once when the set emptied.
        """
        if self._latched_stops:
            self._publish_holds()

    def _cancel_nav2_goal(self, robot_id: str) -> None:
        """Cancel robot_id's active Nav2 goal to stop DWB velocity generation.

        Uses rclpy ActionClient.cancel_goals_async(goals_to_cancel=None) which
        sends a cancel-all request without needing the goal handle. This stops
        DWB from publishing new velocity commands to cmd_vel_nav. Fire-and-forget.
        """
        if ActionClient is None or NavigateToPose is None:
            return
        client = self._nav_clients.get(robot_id)
        if client is None:
            client = ActionClient(self, NavigateToPose, f"/{robot_id}/navigate_to_pose")
            self._nav_clients[robot_id] = client
        try:
            client.cancel_goals_async(goals_to_cancel=None)
        except Exception:
            pass
        self.get_logger().info(f"nav2 goal cancelled robot={robot_id}")

    def _emergency_stop(self, robot_id: str) -> None:
        self._publish_zero(robot_id)
        self.get_logger().warning(
            f"safety stop robot={robot_id} reason=min_distance_violation"
        )

    def _publish_zero(self, robot_id: str) -> None:
        pub = self._stop_pubs.get(robot_id)
        if pub is None:
            # Publish directly to cmd_vel — this is what the Isaac watchdog and
            # collision_monitor both write to. DWB is stopped by goal cancel so
            # there is no competing publisher once the cancel lands.
            pub = self.create_publisher(Twist, f"/{robot_id}/cmd_vel", 10)
            self._stop_pubs[robot_id] = pub
        pub.publish(Twist())


def _load_safety_limits(node: Node) -> SafetyLimits:
    """Load `config/safety.yaml` from the package share, falling back to defaults."""
    defaults = SafetyLimits(min_distance_m=0.3, max_linear_velocity_mps=0.2)
    try:
        share = get_package_share_directory("swarm_execution")
        path = Path(share) / "config" / "safety.yaml"
        data = yaml.safe_load(path.read_text())["safety"]
        return SafetyLimits(
            min_distance_m=float(data["min_distance_m"]),
            max_linear_velocity_mps=float(data["max_linear_velocity_mps"]),
        )
    except Exception as exc:  # noqa: BLE001 - degrade to documented defaults
        node.get_logger().warning(
            f"safety.yaml load failed ({exc}); using defaults "
            f"min_distance_m={defaults.min_distance_m}"
        )
        return defaults


def main(args=None):
    if rclpy is None:
        raise SystemExit("rclpy is required to run this node.")
    rclpy.init(args=args)
    node = SafetyMonitorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

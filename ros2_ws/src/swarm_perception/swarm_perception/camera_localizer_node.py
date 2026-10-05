"""ROS 2 node: publish `map -> <robot>/odom` from the overhead camera (M1).

One instance per robot. It plays exactly AMCL's role in the TF tree — it owns
the `map -> <robot>/odom` edge — but sources the correction from M1's ArUco
measurement of that robot's absolute pose instead of from a lidar scan match.
Launched via `nav2_robot.launch.py localization:=camera`, where the
ground-truth static publisher and AMCL are both suppressed so exactly one node
writes this edge.

All the maths lives in `camera_localizer.py` (no ROS imports, unit-tested
offline); this module only converts messages, looks up TF, and broadcasts.

Odometry is looked up at the M1 pose's own time (`odom_lookup:=stamped`, the
v3 costmap fix A-prime): the robot entry's stamp minus
`m1_latency_compensation_sec`. `odom_lookup:=latest` restores the pre-fix
`Time()` pairing for A/B runs only.

Run it through `nav2_robot.launch.py`, or pass `use_sim_time:=true` explicitly:
outgoing transforms are stamped from this node's clock, so on system time it
would stamp them onto a timeline the sim-time TF buffer never reaches.
"""
from __future__ import annotations

import json
import math

try:
    import rclpy
    from geometry_msgs.msg import TransformStamped
    from rclpy.duration import Duration
    from rclpy.node import Node
    from rclpy.time import Time
    from std_msgs.msg import String as RosString
    from tf2_ros import (
        ConnectivityException,
        ExtrapolationException,
        LookupException,
        TransformBroadcaster,
    )
    from tf2_ros.buffer import Buffer
    from tf2_ros.transform_listener import TransformListener

    _HAS_ROS2 = True
except ImportError:
    # Keep the module importable in non-ROS unit tests (same guard style as
    # swarm_execution/nav2_adapter.py). Note Duration here is
    # rclpy.duration.Duration, not builtin_interfaces.msg.Duration.
    rclpy = None
    Node = object
    Duration = None
    Time = None
    TransformStamped = None
    RosString = None
    Buffer = None
    TransformListener = None
    TransformBroadcaster = None

    class _Tf2Error(Exception):
        """Stand-in so the TF except clause below is importable without tf2_ros."""

    LookupException = ConnectivityException = ExtrapolationException = _Tf2Error
    _HAS_ROS2 = False

from swarm_perception.camera_localizer import (
    DEFAULT_M1_LATENCY_COMPENSATION_SEC,
    CameraLocalizer,
    Pose2D,
    normalize_yaw,
    odom_lookup_stamp,
)

ODOM_LOOKUP_MODES = ("stamped", "latest")


class CameraLocalizerNode(Node):
    """Turn M1 scene states into the `map -> <robot>/odom` TF for one robot."""

    LOG_EVERY_N_UPDATES = 60

    def __init__(self) -> None:
        super().__init__("camera_localizer")

        self.declare_parameter("robot_id", "")
        # Absolute default on purpose: this node runs inside
        # PushRosNamespace(<robot_id>), where a relative name would resolve to
        # /<robot_id>/perception/scene_state and never receive anything, since
        # M1 publishes one global scene state for all robots.
        self.declare_parameter("scene_state_topic", "/perception/scene_state")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("odom_frame", "")
        self.declare_parameter("base_frame", "")
        self.declare_parameter("publish_rate_hz", 20.0)
        self.declare_parameter("transform_tolerance_sec", 0.3)
        self.declare_parameter("set_initial_pose", True)
        self.declare_parameter("initial_pose.x", 0.0)
        self.declare_parameter("initial_pose.y", 0.0)
        self.declare_parameter("initial_pose.yaw", 0.0)
        # v3 costmap fix A-prime: `stamped` pairs each M1 pose with odometry at
        # the pose's own time (`camera_localizer.odom_lookup_stamp`); `latest`
        # is the pre-fix Time() lookup, kept only as an A/B switch.
        self.declare_parameter("odom_lookup", "stamped")
        self.declare_parameter(
            "m1_latency_compensation_sec", DEFAULT_M1_LATENCY_COMPENSATION_SEC
        )

        self._robot_id = str(self.get_parameter("robot_id").value or "")
        if not self._robot_id:
            # Fail fast: without a robot_id there is no robot to look up in the
            # scene state and no correct odom frame to publish to.
            raise ValueError(
                "camera_localizer requires the `robot_id` parameter (e.g. robot_1)."
            )

        self._map_frame = str(self.get_parameter("map_frame").value)
        self._odom_frame = (
            str(self.get_parameter("odom_frame").value or "") or f"{self._robot_id}/odom"
        )
        self._base_frame = (
            str(self.get_parameter("base_frame").value or "")
            or f"{self._robot_id}/base_footprint"
        )
        self._transform_tolerance_sec = float(
            self.get_parameter("transform_tolerance_sec").value
        )
        publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)
        if publish_rate_hz <= 0.0:
            raise ValueError(f"publish_rate_hz must be > 0; got {publish_rate_hz}")
        self._odom_lookup = str(self.get_parameter("odom_lookup").value)
        if self._odom_lookup not in ODOM_LOOKUP_MODES:
            raise ValueError(
                f"odom_lookup must be one of {ODOM_LOOKUP_MODES}; got {self._odom_lookup!r}"
            )
        self._latency_compensation_sec = float(
            self.get_parameter("m1_latency_compensation_sec").value
        )
        if not 0.0 <= self._latency_compensation_sec < 1.0:
            raise ValueError(
                "m1_latency_compensation_sec must be in [0, 1); got "
                f"{self._latency_compensation_sec}"
            )
        self._stamped_lookup_failures = 0

        # Seed map -> odom with the spawn pose, exactly as AMCL's
        # set_initial_pose does: IsaacComputeOdometry's odom frame is
        # spawn-relative and identity at t=0, so the spawn pose in map IS
        # map -> odom at startup. Without this, a Nav2 costmap that needs
        # this edge blocks until the first camera fix arrives, which can lose
        # a lifecycle-activation race (see nav2_robot.launch.py docstring).
        initial_map_to_odom: Pose2D | None = None
        if bool(self.get_parameter("set_initial_pose").value):
            initial_map_to_odom = (
                float(self.get_parameter("initial_pose.x").value),
                float(self.get_parameter("initial_pose.y").value),
                normalize_yaw(float(self.get_parameter("initial_pose.yaw").value)),
            )

        self._localizer = CameraLocalizer(
            self._robot_id, initial_map_to_odom=initial_map_to_odom
        )
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._tf_broadcaster = TransformBroadcaster(self)

        scene_state_topic = str(self.get_parameter("scene_state_topic").value)
        self._scene_sub = self.create_subscription(
            RosString, scene_state_topic, self._on_scene_state, 10
        )
        self._timer = self.create_timer(1.0 / publish_rate_hz, self._publish_map_to_odom)

        self.get_logger().info(
            f"camera_localizer started robot_id={self._robot_id} "
            f"scene_state_topic={scene_state_topic} "
            f"tf={self._map_frame}->{self._odom_frame} "
            f"odom_lookup={self._odom_frame}->{self._base_frame} "
            f"odom_lookup_mode={self._odom_lookup} "
            f"m1_latency_compensation_sec={self._latency_compensation_sec} "
            f"publish_rate_hz={publish_rate_hz}"
        )
        if initial_map_to_odom is not None:
            self.get_logger().info(
                f"camera localizer seeded map_odom=("
                f"{initial_map_to_odom[0]:.3f}, {initial_map_to_odom[1]:.3f}, "
                f"{initial_map_to_odom[2]:.3f}) robot={self._robot_id}"
            )

    def _on_scene_state(self, msg) -> None:
        """Fold one `/perception/scene_state` message into the held correction."""
        try:
            scene_state = json.loads(msg.data)
        except json.JSONDecodeError as exc:
            self.get_logger().error(
                f"camera_localizer robot_id={self._robot_id} bad scene_state JSON: {exc}"
            )
            return
        if not isinstance(scene_state, dict):
            self.get_logger().error(
                f"camera_localizer robot_id={self._robot_id} scene_state must be a "
                f"JSON object; got {type(scene_state).__name__}"
            )
            return

        if self._odom_lookup == "stamped":
            lookup_stamp = odom_lookup_stamp(
                scene_state, self._robot_id, self._latency_compensation_sec
            )
            if lookup_stamp is None:
                # Robot absent (or unstamped): nothing to pair; update() holds.
                self._localizer.update(scene_state, None)
                return
            odom_pose = self._lookup_odom_pose(lookup_stamp)
        else:
            odom_pose = self._lookup_odom_pose(None)
        if odom_pose is None:
            return
        # Track the *transition* into the first real update (0 -> 1), not
        # `latest is not None`: a seeded localizer already has a non-None
        # `latest` before any real fix, so a presence check would never fire
        # here and this log would go missing entirely under seeding.
        was_seeded = self._localizer.seeded
        updates_before = self._localizer.updates
        transform = self._localizer.update(scene_state, odom_pose)
        if transform is None:
            return
        if updates_before == 0 and self._localizer.updates == 1:
            replaced = " replaced_seed=true" if was_seeded else ""
            self.get_logger().info(
                f"camera localization acquired robot={self._robot_id}{replaced} "
                f"map_odom=({transform[0]:.3f}, {transform[1]:.3f}, {transform[2]:.3f})"
            )
        # `self._localizer.updates and ...`, not just the modulo: seeding
        # means `transform` is non-None (the held seed) even before any real
        # update, so without this guard every hold while `updates == 0` would
        # match `0 % LOG_EVERY_N_UPDATES == 0` and spam this log every cycle.
        elif (
            self._localizer.updates
            and self._localizer.updates % self.LOG_EVERY_N_UPDATES == 0
        ):
            self.get_logger().info(
                f"camera_localizer robot_id={self._robot_id} "
                f"updates={self._localizer.updates} holds={self._localizer.holds} "
                f"stamped_lookup_failures={self._stamped_lookup_failures} "
                f"map_odom=({transform[0]:.3f}, {transform[1]:.3f}, {transform[2]:.3f}) "
                f"scene_stamp={self._localizer.last_update_stamp}"
            )

    def _lookup_odom_pose(self, stamp: float | None) -> Pose2D | None:
        """Look up `<robot>/odom -> <robot>/base_footprint` as a Pose2D.

        Args:
            stamp: ROS time (seconds) to look the transform up at, or None for
                the latest available transform (the pre-fix `latest` mode).

        Returns:
            The odometry pose as `(x, y, yaw)`, or None when TF cannot serve it.
        """
        if stamp is not None and stamp < 0.0:
            self._stamped_lookup_failures += 1
            return None
        # `stamped`: no TF wait (timeout 0). The listener shares this node's
        # executor, so a blocking wait inside this callback could never be
        # satisfied; the pose time is in the past by M1's pipeline latency, so
        # odometry (60 Hz) normally covers it already. An extrapolation miss
        # holds the previous correction; it must never fall back to the latest
        # transform, which is exactly the pre-fix pairing error.
        when = Time() if stamp is None else Time(nanoseconds=int(round(stamp * 1e9)))
        try:
            tf = self._tf_buffer.lookup_transform(self._odom_frame, self._base_frame, when)
        except (LookupException, ConnectivityException, ExtrapolationException) as exc:
            if stamp is not None:
                self._stamped_lookup_failures += 1
            self.get_logger().warning(
                f"camera_localizer robot_id={self._robot_id} no TF "
                f"{self._odom_frame}->{self._base_frame} at stamp={stamp} "
                f"stamped_lookup_failures={self._stamped_lookup_failures}: {exc}",
                throttle_duration_sec=5.0,
            )
            return None
        translation = tf.transform.translation
        rotation = tf.transform.rotation
        # Planar yaw from a z-axis quaternion; normalized because a w < 0
        # quaternion is the same rotation but yields yaw outside (-pi, pi].
        yaw = normalize_yaw(2.0 * math.atan2(rotation.z, rotation.w))
        return (translation.x, translation.y, yaw)

    def _publish_map_to_odom(self) -> None:
        """Broadcast the held correction, at a fixed rate independent of frames."""
        transform = self._localizer.latest
        if transform is None:
            return
        x, y, yaw = transform
        msg = TransformStamped()
        # Stamped into the future by transform_tolerance, which is AMCL's own
        # convention: it lets TF consumers extrapolate up to that horizon
        # instead of rejecting a correction that is always slightly stale.
        msg.header.stamp = (
            self.get_clock().now() + Duration(seconds=self._transform_tolerance_sec)
        ).to_msg()
        msg.header.frame_id = self._map_frame
        msg.child_frame_id = self._odom_frame
        msg.transform.translation.x = x
        msg.transform.translation.y = y
        msg.transform.translation.z = 0.0
        msg.transform.rotation.x = 0.0
        msg.transform.rotation.y = 0.0
        msg.transform.rotation.z = math.sin(yaw / 2.0)
        msg.transform.rotation.w = math.cos(yaw / 2.0)
        self._tf_broadcaster.sendTransform(msg)


def main(args=None) -> None:
    if not _HAS_ROS2:
        raise SystemExit("rclpy is required to run CameraLocalizerNode.")
    rclpy.init(args=args)
    node = CameraLocalizerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from isaac.vgu_sim.config import CameraConfig, RobotAssetConfig, RobotScenarioConfig
from isaac.vgu_sim.lidar import author_rtx_lidar

if TYPE_CHECKING:
    from isaacsim.sensors.experimental.rtx import LidarSensor


class RosGraphError(Exception):
    pass


# M6 FR6.4.9: 360 deg FOV, 1 deg resolution, 10 Hz, 0.12-3.5 m range. RPLIDAR_S2E
# is the base config because it is a genuine single-elevation-ray 2D rotary scan
# (elevationDeg: [0]) -- the property the height-separation exclusion mechanism in
# docs/specs/module4/phase2-nav2-stack.md S10 depends on. Its native range
# (0.05-30 m) and resolution (0.1125 deg, from a 32000 Hz firing rate) do not match
# FR6.4.9, so both are overridden via the `attributes` dict, which Lidar.create()
# applies to the OmniLidar prim after loading the base config (verified against
# isaacsim.sensors.experimental.rtx.impl.lidar.Lidar.__init__/_apply_attributes on
# the host). patternFiringRateHz=3600 is derived from the LaserScan resolution
# formula used by the official standalone example
# (source/standalone_examples/api/isaacsim.ros2.bridge/rtx_lidar.py):
# horizontalResolution = 360 * scanRateBaseHz / patternFiringRateHz, so
# 360 * 10 / 3600 = 1.0 deg at the target 10 Hz tick rate.
_LIDAR_CONFIG = "RPLIDAR_S2E"
_LIDAR_TICK_RATE_HZ = 10.0
_LIDAR_ATTRIBUTES: dict[str, Any] = {
    "omni:sensor:Core:nearRangeM": 0.12,
    "omni:sensor:Core:farRangeM": 3.5,
    "omni:sensor:Core:scanRateBaseHz": 10.0,
    "omni:sensor:Core:patternFiringRateHz": 3600,
}


def _read_laser_scan_metadata(prim) -> dict[str, Any]:
    """Read LaserScan publish geometry from a rotary OmniLidar prim's attributes.

    Mirrors the metadata extraction the deprecated `OgnROS2RtxLidarHelper` OmniGraph
    node performs internally, so `RtxLidarROS2PublishLaserScan` (a plain Replicator
    writer, not an OmniGraph node -- see
    docs/specs/module4/phase2-nav2-stack.md S10) can be initialized directly from
    the prim authored by `Lidar.create()`.

    Args:
        prim: The USD `OmniLidar` prim to read scan geometry from.

    Returns:
        Keyword arguments for `LidarSensor.attach_writer("RtxLidarROS2PublishLaserScan", ...)`.

    Raises:
        RuntimeError: If the prim's scan-rate or firing-rate attributes are zero or unset.
    """
    rotation_rate = float(prim.GetAttribute("omni:sensor:Core:scanRateBaseHz").Get() or 0)
    near_range = float(prim.GetAttribute("omni:sensor:Core:nearRangeM").Get() or 0)
    far_range = float(prim.GetAttribute("omni:sensor:Core:farRangeM").Get() or 0)
    firing_rate = int(prim.GetAttribute("omni:sensor:Core:patternFiringRateHz").Get() or 0)
    if rotation_rate <= 0 or firing_rate <= 0:
        raise RuntimeError(
            "LaserScan: scanRateBaseHz or patternFiringRateHz is 0 on the lidar prim"
        )
    return dict(
        horizontalFov=360.0,
        horizontalResolution=360.0 * rotation_rate / firing_rate,
        depthRange=[near_range, far_range],
        rotationRate=rotation_rate,
        azimuthRange=[-180.0, 180.0],
    )


def create_robot_lidar_sensor(
    stage,
    robot: RobotScenarioConfig,
    robot_prim_path: str,
    config: RobotAssetConfig,
) -> LidarSensor:
    """Author and wire the RTX 2D lidar for one robot (M6 FR6.4.9).

    Creates the lidar mount `Xform` under `<robot>/.../<lidar_link>` via
    `author_rtx_lidar()`, then creates the real RTX lidar sensor and attaches a
    `sensor_msgs/LaserScan` ROS2 publisher on `/<robot_id>/scan`. This is plain
    Python sensor-object creation (`isaacsim.sensors.experimental.rtx.Lidar` /
    `LidarSensor`), not an OmniGraph node, and is therefore separate from the
    `og.Controller.edit` graph built by `create_robot_ros_graph` -- see
    docs/specs/module4/phase2-nav2-stack.md S10.

    Args:
        stage: The USD stage holding the robot.
        robot: Per-robot scenario config (used for `robot_id`).
        robot_prim_path: Root prim of the robot subtree.
        config: Robot asset config (used for `lidar_link`).

    Returns:
        The `LidarSensor` wrapping the authored sensor. The caller must keep a
        reference alive for the simulation's lifetime: `LidarSensor.__del__`
        detaches its ROS2 writer and destroys its render product, which would
        silently stop `/<robot_id>/scan` from publishing if the sensor were
        garbage-collected.
    """
    from isaacsim.core.experimental.utils import prim as prim_utils
    from isaacsim.sensors.experimental.rtx import Lidar, LidarSensor

    robot_id = robot.robot_id
    lidar_xform_path = author_rtx_lidar(stage, robot_prim_path, config.lidar_link)

    lidar = Lidar.create(
        path=f"{lidar_xform_path}/rtx_sensor",
        config=_LIDAR_CONFIG,
        tick_rate=_LIDAR_TICK_RATE_HZ,
        attributes=_LIDAR_ATTRIBUTES,
    )
    sensor = LidarSensor(lidar, annotators=[])

    laser_scan_meta = _read_laser_scan_metadata(prim_utils.get_prim_at_path(lidar.paths[0]))
    sensor.attach_writer(
        "RtxLidarROS2PublishLaserScan",
        topicName=f"{robot_id}/scan",
        frameId=f"{robot_id}/base_scan",
        **laser_scan_meta,
    )
    return sensor


def create_global_ros_graphs(
    stage,
    camera_prim_path: str,
    config: CameraConfig,
) -> None:
    import omni.graph.core as og
    import omni.replicator.core as rep

    graph_path = "/World/ROSGraphs/Global"

    render_product = rep.create.render_product(
        camera_prim_path, (config.width, config.height)
    )

    # Trigger publishers from OnPlaybackTick (execution evaluator). OnPhysicsStep
    # only fires inside an on-demand graph; in an execution graph it silently
    # never triggers ("Physics OnSimulationStep node detected in a non on-demand
    # Graph"). OnPlaybackTick.outputs:tick is the per-frame execution pulse.
    og.Controller.edit(
        {"graph_path": f"{graph_path}/clock_graph", "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_tick",   "omni.graph.action.OnPlaybackTick"),
                ("read_time", "isaacsim.core.nodes.IsaacReadSimulationTime"),
                ("pub_clock", "isaacsim.ros2.bridge.ROS2PublishClock"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_tick.outputs:tick",            "pub_clock.inputs:execIn"),
                ("read_time.outputs:simulationTime", "pub_clock.inputs:timeStamp"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("pub_clock.inputs:topicName", "/clock"),
            ],
        },
    )

    og.Controller.edit(
        {"graph_path": f"{graph_path}/camera_rgb_graph", "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_tick", "omni.graph.action.OnPlaybackTick"),
                ("pub_rgb", "isaacsim.ros2.bridge.ROS2CameraHelper"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_tick.outputs:tick", "pub_rgb.inputs:execIn"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("pub_rgb.inputs:topicName",         "/camera/image_raw"),
                ("pub_rgb.inputs:frameId",            config.frame_id),
                ("pub_rgb.inputs:renderProductPath",  render_product.path),
                ("pub_rgb.inputs:type",               "rgb"),
                # Stamp frames with wall-clock time. Simulation time stays at 0
                # in this static run, and the bridge drops any message with an
                # invalid (0) timestamp. M1/M5 consume on wall-clock (no
                # use_sim_time), so system time is both correct and required for
                # frames to actually publish.
                ("pub_rgb.inputs:useSystemTime",      True),
                # Leave qosProfile at its node default (empty string). The Isaac
                # ROS2 nodes treat qosProfile as a JSON document; the literal
                # "default" is not valid JSON and floods the log with parse
                # errors. The empty default is a RELIABLE/keep-last(10) profile,
                # which M1's default-QoS subscriber connects to.
            ],
        },
    )

    og.Controller.edit(
        {"graph_path": f"{graph_path}/camera_info_graph", "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_tick",      "omni.graph.action.OnPlaybackTick"),
                ("pub_cam_info", "isaacsim.ros2.bridge.ROS2CameraInfoHelper"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_tick.outputs:tick", "pub_cam_info.inputs:execIn"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("pub_cam_info.inputs:topicName",        "/camera/camera_info"),
                ("pub_cam_info.inputs:frameId",           config.frame_id),
                ("pub_cam_info.inputs:renderProductPath", render_product.path),
                ("pub_cam_info.inputs:useSystemTime",     True),
            ],
        },
    )


def create_robot_ros_graph(
    stage,
    robot: RobotScenarioConfig,
    robot_prim_path: str,
    config: RobotAssetConfig,
) -> None:
    import omni.graph.core as og
    from pxr import Usd, UsdPhysics

    robot_id = robot.robot_id
    graph_path = f"/World/ROSGraphs/{robot_id}/drive_graph"

    # The ArticulationRootAPI is applied deep inside the referenced robot asset
    # (e.g. /World/Robots/<id>/Geometry/base_footprint/base_link), not as a
    # direct child of the robot prim, so traverse the whole subtree.
    root_prim = stage.GetPrimAtPath(robot_prim_path)
    art_roots = [
        p for p in Usd.PrimRange(root_prim)
        if p.HasAPI(UsdPhysics.ArticulationRootAPI)
    ]
    if len(art_roots) != 1:
        raise RosGraphError(
            f"Expected exactly 1 ArticulationRootAPI under {robot_prim_path}; "
            f"found {len(art_roots)}"
        )
    chassis_path = art_roots[0].GetPath().pathString

    # Drive + odometry graph (M4 Phase 1 / M6 FR6.7.4). A geometry_msgs/Twist on
    # cmd_vel drives the articulation; IsaacComputeOdometry publishes /<id>/odom.
    # Node interface verified against Isaac 6.0.0 — see
    # docs/specs/module4/phase1-drive-chain.md §2a. The lidar (RTX /scan) is added
    # in Phase 2, not here.
    #
    # ROS2SubscribeTwist emits the linear/angular commands as double3 vectors, but
    # DifferentialController takes scalar forward/yaw rates, so BreakVector3 picks
    # off linear.x and angular.z. dt is fed from OnPlaybackTick.deltaSeconds so the
    # controller's acceleration integration uses real frame time. Data edges
    # (twist -> break -> diff -> art) make the execution evaluator order the nodes
    # correctly within each tick.
    #
    # Branch B watchdog (M4 Phase 1 Task 6 / FR6.4.8): ROS2SubscribeTwist has no
    # built-in command timeout, so the graph subscribes /<id>/cmd_vel_safe instead
    # of the public /<id>/cmd_vel. The out-of-graph CmdVelWatchdog relay node
    # (cmd_vel_watchdog_node.py) republishes /cmd_vel -> /cmd_vel_safe and zeros it
    # after command_timeout_sec of silence, so a single non-repeating Twist coasts
    # to a stop. The public /<id>/cmd_vel contract for M4/M5 is unchanged.
    cmd_vel_topic = f"/{robot_id}/cmd_vel_safe"

    # TF tree (M4 Phase 1 Task 6 / FR6.7.5-6.7.6): the dynamic odom->base_footprint
    # edge is published on /tf from the same IsaacComputeOdometry pose that feeds
    # pub_odom (so /tf and /odom never disagree); the fixed base_footprint->base_link
    # and base_link->base_scan mounts are latched on /tf_static. ROS2PublishOdometry
    # does NOT emit TF itself (verified, spec §2a), so there is no double-publish of
    # the dynamic edge. ROS2PublishRawTransformTree.inputs:rotation is a quatd[4] in
    # xyzw order (identity = (0, 0, 0, 1)); the static mounts have identity rotation.
    # Mount offsets are the turtlebot3_burger URDF joint origins:
    #   base_joint (base_footprint->base_link): xyz = (0, 0, 0.010)
    #   scan_joint (base_link->base_scan):       xyz = (-0.032, 0, 0.172)
    og.Controller.edit(
        {"graph_path": graph_path, "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_tick",      "omni.graph.action.OnPlaybackTick"),
                ("read_time",    "isaacsim.core.nodes.IsaacReadSimulationTime"),
                ("twist_sub",    "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
                ("break_lin",    "omni.graph.nodes.BreakVector3"),
                ("break_ang",    "omni.graph.nodes.BreakVector3"),
                ("diff_ctrl",    "isaacsim.robot.wheeled_robots.DifferentialController"),
                ("art_ctrl",     "isaacsim.core.nodes.IsaacArticulationController"),
                ("odom_compute", "isaacsim.core.nodes.IsaacComputeOdometry"),
                ("pub_odom",     "isaacsim.ros2.bridge.ROS2PublishOdometry"),
                ("pub_tf",       "isaacsim.ros2.bridge.ROS2PublishRawTransformTree"),
                ("pub_tf_base",  "isaacsim.ros2.bridge.ROS2PublishRawTransformTree"),
                ("pub_tf_scan",  "isaacsim.ros2.bridge.ROS2PublishRawTransformTree"),
            ],
            og.Controller.Keys.CONNECT: [
                # Drive chain: cmd_vel_safe -> wheel velocity targets -> articulation.
                ("on_tick.outputs:tick",                 "twist_sub.inputs:execIn"),
                ("on_tick.outputs:tick",                 "diff_ctrl.inputs:execIn"),
                ("on_tick.outputs:tick",                 "art_ctrl.inputs:execIn"),
                ("on_tick.outputs:deltaSeconds",         "diff_ctrl.inputs:dt"),
                ("twist_sub.outputs:linearVelocity",     "break_lin.inputs:tuple"),
                ("twist_sub.outputs:angularVelocity",    "break_ang.inputs:tuple"),
                ("break_lin.outputs:x",                  "diff_ctrl.inputs:linearVelocity"),
                ("break_ang.outputs:z",                  "diff_ctrl.inputs:angularVelocity"),
                ("diff_ctrl.outputs:velocityCommand",    "art_ctrl.inputs:velocityCommand"),
                # Odometry. timeStamp must be wired explicitly -- ROS2PublishOdometry's
                # inputs:timeStamp has no execution-graph default source and defaults
                # to 0.0 (verified against the node's .ogn schema and
                # OgnROS2PublishOdometry.cpp, which reads db.inputs.timeStamp() as
                # given), which tf2/rclpy log as "Timestamp is invalid" and drop.
                ("on_tick.outputs:tick",                 "odom_compute.inputs:execIn"),
                ("odom_compute.outputs:execOut",          "pub_odom.inputs:execIn"),
                ("read_time.outputs:simulationTime",      "pub_odom.inputs:timeStamp"),
                ("odom_compute.outputs:position",         "pub_odom.inputs:position"),
                ("odom_compute.outputs:orientation",      "pub_odom.inputs:orientation"),
                ("odom_compute.outputs:linearVelocity",   "pub_odom.inputs:linearVelocity"),
                ("odom_compute.outputs:angularVelocity",  "pub_odom.inputs:angularVelocity"),
                # Dynamic odom -> base_footprint TF on /tf, stamped with sim time so
                # use_sim_time consumers (the watchdog, tf2) accept it. Translation
                # and rotation come straight from the odometry node, matching /odom.
                ("on_tick.outputs:tick",                  "pub_tf.inputs:execIn"),
                ("read_time.outputs:simulationTime",      "pub_tf.inputs:timeStamp"),
                ("odom_compute.outputs:position",         "pub_tf.inputs:translation"),
                ("odom_compute.outputs:orientation",      "pub_tf.inputs:rotation"),
                # Static mount TFs on /tf_static (latched, published once). Despite
                # staticPublisher's transient-local QoS, ROS2PublishRawTransformTree
                # still stamps the single latched message from inputs:timeStamp, which
                # also has no default-graph source and defaults to 0.0 -- this produced
                # the same "Timestamp is invalid" warnings for base_link/base_scan seen
                # alongside the odom ones, and was originally misread as evidence the
                # dynamic /tf edge above was broken too (it was not; see
                # docs/specs/module4/phase2-nav2-stack.md S5 for the corrected finding).
                ("on_tick.outputs:tick",                  "pub_tf_base.inputs:execIn"),
                ("read_time.outputs:simulationTime",      "pub_tf_base.inputs:timeStamp"),
                ("on_tick.outputs:tick",                  "pub_tf_scan.inputs:execIn"),
                ("read_time.outputs:simulationTime",      "pub_tf_scan.inputs:timeStamp"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("twist_sub.inputs:topicName",       cmd_vel_topic),
                # Wheel-command order must match velocityCommand's [left, right].
                ("art_ctrl.inputs:targetPrim",       chassis_path),
                ("art_ctrl.inputs:jointNames",       [config.left_wheel_joint, config.right_wheel_joint]),
                ("diff_ctrl.inputs:wheelRadius",     config.wheel_radius_m),
                ("diff_ctrl.inputs:wheelDistance",   config.wheel_separation_m),
                ("diff_ctrl.inputs:maxLinearSpeed",  config.max_linear_velocity_mps),
                ("diff_ctrl.inputs:maxAngularSpeed", config.max_angular_velocity_radps),
                ("odom_compute.inputs:chassisPrim", chassis_path),
                ("pub_odom.inputs:topicName",        f"/{robot_id}/odom"),
                ("pub_odom.inputs:odomFrameId",      f"{robot_id}/odom"),
                ("pub_odom.inputs:chassisFrameId",   f"{robot_id}/base_footprint"),
                # Dynamic odom -> base_footprint.
                ("pub_tf.inputs:topicName",          "/tf"),
                ("pub_tf.inputs:staticPublisher",    False),
                ("pub_tf.inputs:parentFrameId",      f"{robot_id}/odom"),
                ("pub_tf.inputs:childFrameId",       f"{robot_id}/base_footprint"),
                # Static base_footprint -> base_link (URDF base_joint origin).
                ("pub_tf_base.inputs:topicName",        "/tf_static"),
                ("pub_tf_base.inputs:staticPublisher",  True),
                ("pub_tf_base.inputs:parentFrameId",    f"{robot_id}/base_footprint"),
                ("pub_tf_base.inputs:childFrameId",     f"{robot_id}/base_link"),
                ("pub_tf_base.inputs:translation",      [0.0, 0.0, 0.010]),
                ("pub_tf_base.inputs:rotation",         [0.0, 0.0, 0.0, 1.0]),
                # Static base_link -> base_scan (URDF scan_joint origin).
                ("pub_tf_scan.inputs:topicName",        "/tf_static"),
                ("pub_tf_scan.inputs:staticPublisher",  True),
                ("pub_tf_scan.inputs:parentFrameId",    f"{robot_id}/base_link"),
                ("pub_tf_scan.inputs:childFrameId",     f"{robot_id}/base_scan"),
                ("pub_tf_scan.inputs:translation",      [-0.032, 0.0, 0.172]),
                ("pub_tf_scan.inputs:rotation",         [0.0, 0.0, 0.0, 1.0]),
            ],
        },
    )

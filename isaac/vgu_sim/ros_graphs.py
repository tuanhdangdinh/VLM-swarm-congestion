from __future__ import annotations

from isaac.vgu_sim.config import CameraConfig, RobotAssetConfig, RobotScenarioConfig


class RosGraphError(Exception):
    pass


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
    cmd_vel_topic = f"/{robot_id}/cmd_vel"
    og.Controller.edit(
        {"graph_path": graph_path, "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_tick",      "omni.graph.action.OnPlaybackTick"),
                ("twist_sub",    "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
                ("break_lin",    "omni.graph.nodes.BreakVector3"),
                ("break_ang",    "omni.graph.nodes.BreakVector3"),
                ("diff_ctrl",    "isaacsim.robot.wheeled_robots.DifferentialController"),
                ("art_ctrl",     "isaacsim.core.nodes.IsaacArticulationController"),
                ("odom_compute", "isaacsim.core.nodes.IsaacComputeOdometry"),
                ("pub_odom",     "isaacsim.ros2.bridge.ROS2PublishOdometry"),
            ],
            og.Controller.Keys.CONNECT: [
                # Drive chain: cmd_vel -> wheel velocity targets -> articulation.
                ("on_tick.outputs:tick",                 "twist_sub.inputs:execIn"),
                ("on_tick.outputs:tick",                 "diff_ctrl.inputs:execIn"),
                ("on_tick.outputs:tick",                 "art_ctrl.inputs:execIn"),
                ("on_tick.outputs:deltaSeconds",         "diff_ctrl.inputs:dt"),
                ("twist_sub.outputs:linearVelocity",     "break_lin.inputs:tuple"),
                ("twist_sub.outputs:angularVelocity",    "break_ang.inputs:tuple"),
                ("break_lin.outputs:x",                  "diff_ctrl.inputs:linearVelocity"),
                ("break_ang.outputs:z",                  "diff_ctrl.inputs:angularVelocity"),
                ("diff_ctrl.outputs:velocityCommand",    "art_ctrl.inputs:velocityCommand"),
                # Odometry.
                ("on_tick.outputs:tick",                 "odom_compute.inputs:execIn"),
                ("odom_compute.outputs:execOut",          "pub_odom.inputs:execIn"),
                ("odom_compute.outputs:position",         "pub_odom.inputs:position"),
                ("odom_compute.outputs:orientation",      "pub_odom.inputs:orientation"),
                ("odom_compute.outputs:linearVelocity",   "pub_odom.inputs:linearVelocity"),
                ("odom_compute.outputs:angularVelocity",  "pub_odom.inputs:angularVelocity"),
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
            ],
        },
    )

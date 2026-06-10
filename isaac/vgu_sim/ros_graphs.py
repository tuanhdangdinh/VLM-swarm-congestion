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

    og.Controller.edit(
        {"graph_path": f"{graph_path}/clock_graph", "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_step",   "isaacsim.core.nodes.OnPhysicsStep"),
                ("pub_clock", "isaacsim.ros2.bridge.ROS2PublishClock"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_step.outputs:step", "pub_clock.inputs:execIn"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("pub_clock.inputs:topicName", "/clock"),
                ("pub_clock.inputs:qosProfile", "default"),
            ],
        },
    )

    og.Controller.edit(
        {"graph_path": f"{graph_path}/camera_rgb_graph", "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_step", "isaacsim.core.nodes.OnPhysicsStep"),
                ("pub_rgb", "isaacsim.ros2.bridge.ROS2CameraHelper"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_step.outputs:step", "pub_rgb.inputs:execIn"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("pub_rgb.inputs:topicName",         "/camera/image_raw"),
                ("pub_rgb.inputs:frameId",            config.frame_id),
                ("pub_rgb.inputs:renderProductPath",  render_product.path),
                ("pub_rgb.inputs:type",               "rgb"),
            ],
        },
    )

    og.Controller.edit(
        {"graph_path": f"{graph_path}/camera_info_graph", "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_step",      "isaacsim.core.nodes.OnPhysicsStep"),
                ("pub_cam_info", "isaacsim.ros2.bridge.ROS2CameraInfoHelper"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_step.outputs:step", "pub_cam_info.inputs:execIn"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("pub_cam_info.inputs:topicName",        "/camera/camera_info"),
                ("pub_cam_info.inputs:frameId",           config.frame_id),
                ("pub_cam_info.inputs:renderProductPath", render_product.path),
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
    from pxr import UsdPhysics

    robot_id = robot.robot_id
    graph_path = f"/World/ROSGraphs/{robot_id}/drive_graph"
    lidar_prim_path = f"{robot_prim_path}/{config.lidar_link}"

    art_roots = [
        p for p in stage.GetPrimAtPath(robot_prim_path).GetChildren()
        if p.HasAPI(UsdPhysics.ArticulationRootAPI)
    ]
    if len(art_roots) != 1:
        raise RosGraphError(
            f"Expected exactly 1 ArticulationRootAPI under {robot_prim_path}; "
            f"found {len(art_roots)}"
        )
    art_root_path = art_roots[0].GetPath().pathString

    og.Controller.edit(
        {"graph_path": graph_path, "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_step",       "isaacsim.core.nodes.OnPhysicsStep"),
                ("sub_twist",     "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
                ("diff_ctrl",     "isaacsim.robot.wheeled_robots.DifferentialController"),
                ("art_ctrl",      "isaacsim.core.nodes.IsaacArticulationController"),
                ("odom_compute",  "isaacsim.core.nodes.IsaacComputeOdometry"),
                ("pub_odom",      "isaacsim.ros2.bridge.ROS2PublishOdometry"),
                ("pub_tf_dyn",    "isaacsim.ros2.bridge.ROS2PublishRawTransformTree"),
                ("pub_tf_static", "isaacsim.ros2.bridge.ROS2PublishRawTransformTree"),
                ("pub_lidar",     "isaacsim.ros2.bridge.ROS2RtxLidarHelper"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_step.outputs:step",             "sub_twist.inputs:execIn"),
                ("sub_twist.outputs:execOut",         "diff_ctrl.inputs:execIn"),
                ("diff_ctrl.outputs:execOut",         "art_ctrl.inputs:execIn"),
                ("art_ctrl.outputs:execOut",          "odom_compute.inputs:execIn"),
                ("odom_compute.outputs:execOut",      "pub_odom.inputs:execIn"),
                ("pub_odom.outputs:execOut",          "pub_tf_dyn.inputs:execIn"),
                ("sub_twist.outputs:linearVelocity",  "diff_ctrl.inputs:linearVelocity"),
                ("sub_twist.outputs:angularVelocity", "diff_ctrl.inputs:angularVelocity"),
                ("diff_ctrl.outputs:velocityCommand", "art_ctrl.inputs:velocityCommand"),
                ("odom_compute.outputs:position",      "pub_odom.inputs:position"),
                ("odom_compute.outputs:orientation",   "pub_odom.inputs:orientation"),
                ("odom_compute.outputs:linearVelocity","pub_odom.inputs:linearVelocity"),
                ("odom_compute.outputs:angularVelocity","pub_odom.inputs:angularVelocity"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("sub_twist.inputs:topicName",          f"/{robot_id}/cmd_vel"),
                ("diff_ctrl.inputs:wheelRadius",         config.wheel_radius_m),
                ("diff_ctrl.inputs:wheelDistance",       config.wheel_separation_m),
                ("diff_ctrl.inputs:maxLinearSpeed",      config.max_linear_velocity_mps),
                ("diff_ctrl.inputs:maxAngularSpeed",     config.max_angular_velocity_radps),
                ("art_ctrl.inputs:robotPath",            art_root_path),
                ("art_ctrl.inputs:jointNames",
                 [config.left_wheel_joint, config.right_wheel_joint]),
                ("odom_compute.inputs:chassisPrim",      robot_prim_path),
                ("pub_odom.inputs:topicName",            f"/{robot_id}/odom"),
                ("pub_odom.inputs:frameId",              f"{robot_id}/odom"),
                ("pub_odom.inputs:childFrameId",         f"{robot_id}/base_footprint"),
                ("pub_odom.inputs:qosProfile",           "default"),
                ("pub_tf_dyn.inputs:topicName",          "/tf"),
                ("pub_tf_dyn.inputs:parentFrameId",      f"{robot_id}/odom"),
                ("pub_tf_dyn.inputs:childFrameId",       f"{robot_id}/base_footprint"),
                ("pub_tf_dyn.inputs:qosProfile",         "default"),
                ("pub_tf_static.inputs:topicName",       "/tf_static"),
                ("pub_tf_static.inputs:qosProfile",      "transient_local"),
                ("pub_lidar.inputs:topicName",           f"/{robot_id}/scan"),
                ("pub_lidar.inputs:frameId",             f"{robot_id}/base_scan"),
                ("pub_lidar.inputs:lidarPrimPath",       lidar_prim_path),
                ("pub_lidar.inputs:type",                "laser_scan"),
            ],
        },
    )

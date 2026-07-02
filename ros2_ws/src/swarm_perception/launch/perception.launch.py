import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory("swarm_perception")
    calibration_path = os.path.join(pkg_share, "config", "calibration.yaml")

    # Load the ArUco dictionary from config so changes there take effect.
    # Tolerate a missing or malformed file by falling back to the default.
    aruco_path = os.path.join(pkg_share, "config", "aruco.yaml")
    marker_dictionary = "DICT_4X4_50"
    try:
        with open(aruco_path) as f:
            aruco_cfg = yaml.safe_load(f)
        aruco_section = aruco_cfg.get("aruco") if isinstance(aruco_cfg, dict) else None
        if isinstance(aruco_section, dict):
            marker_dictionary = aruco_section.get("dictionary", marker_dictionary)
    except FileNotFoundError:
        pass

    return LaunchDescription(
        [
            # Set to "false" in Isaac Sim / external-bridge deployments where
            # /camera/image_raw is already published by the simulator or an
            # external bridge. CameraNode fails fast on a missing device, so
            # leaving it enabled in those deployments would crash the launch.
            DeclareLaunchArgument(
                "use_camera_node",
                default_value="true",
                description=(
                    "Launch the hardware CameraNode. Set to 'false' when an external "
                    "source (Isaac Sim ROS2 bridge, Gazebo, etc.) publishes /camera/image_raw."
                ),
            ),
            DeclareLaunchArgument(
                "expected_robot_ids",
                default_value="",
                description=(
                    "Optional comma-separated robot allowlist for standalone M1 "
                    "runs before /coordination/tasks is available, e.g. "
                    "'robot_1,robot_2'. Empty leaves detections unfiltered."
                ),
            ),
            Node(
                package="swarm_perception",
                executable="camera_node",
                name="camera_node",
                output="screen",
                parameters=[{"image_topic": "/camera/image_raw"}],
                condition=IfCondition(LaunchConfiguration("use_camera_node")),
            ),
            Node(
                package="swarm_perception",
                executable="perception_node",
                name="perception_node",
                output="screen",
                parameters=[
                    {
                        "calibration_path": calibration_path,
                        "image_topic": "/camera/image_raw",
                        "marker_dictionary": marker_dictionary,
                        "stopped_threshold_mps": 0.01,
                        "slow_threshold_mps": 0.05,
                        # 1.0s/0.3 let two robots overlapping markers at close
                        # range (e.g. a head-on standoff) go STALE within about
                        # a second, right when M5 most needs live positions.
                        # 3.0s/0.15 gives more grace before marker occlusion
                        # flips status, and smooths velocity so a brief
                        # detection gap doesn't zero out perceived motion.
                        "stale_after_sec": 3.0,
                        "velocity_alpha": 0.15,
                        "expected_robot_ids": LaunchConfiguration("expected_robot_ids"),
                    }
                ],
            ),
        ]
    )

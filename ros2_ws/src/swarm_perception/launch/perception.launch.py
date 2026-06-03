from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(package="swarm_perception", executable="camera_node", output="screen"),
            Node(package="swarm_perception", executable="aruco_tracker_node", output="screen"),
        ]
    )

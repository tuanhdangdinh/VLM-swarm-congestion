from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config_file = str(
        Path(get_package_share_directory("swarm_orchestrator")) / "config" / "orchestrator.yaml"
    )
    return LaunchDescription(
        [
            Node(
                package="swarm_orchestrator",
                executable="orchestrator_node",
                output="screen",
                parameters=[{"config_file": config_file}],
            )
        ]
    )

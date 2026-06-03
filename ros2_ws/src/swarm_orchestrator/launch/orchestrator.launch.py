from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [Node(package="swarm_orchestrator", executable="orchestrator_node", output="screen")]
    )

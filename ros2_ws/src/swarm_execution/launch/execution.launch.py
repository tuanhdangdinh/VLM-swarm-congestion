from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(package="swarm_execution", executable="command_bus_node", output="screen"),
            Node(package="swarm_execution", executable="coordination_client_node", output="screen"),
            Node(package="swarm_execution", executable="safety_monitor_node", output="screen"),
        ]
    )

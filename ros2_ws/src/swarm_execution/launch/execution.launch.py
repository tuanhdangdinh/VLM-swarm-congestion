from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            # command_bus_node's hold/wait timers (yield, temporary_wait)
            # ground durations against Isaac's clock; they must tick in sim
            # time so they stay motion-consistent when Isaac runs below
            # realtime factor 1.0.
            Node(
                package="swarm_execution",
                executable="command_bus_node",
                output="screen",
                parameters=[{"use_sim_time": True}],
            ),
            # coordination_client_node relays those same grounded durations
            # to Nav2, so it must share sim time with command_bus_node.
            Node(
                package="swarm_execution",
                executable="coordination_client_node",
                output="screen",
                parameters=[{"use_sim_time": True}],
            ),
            # safety_monitor_node stays on wall time: its latching reacts to
            # M1 perception messages, not grounded durations, so it has no
            # sim-time dependency to correct for.
            Node(package="swarm_execution", executable="safety_monitor_node", output="screen"),
        ]
    )

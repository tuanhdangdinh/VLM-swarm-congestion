from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument(
            "ros_domain_id",
            default_value="0",
            description="ROS_DOMAIN_ID matching the Isaac Sim bridge",
        ),
        Node(
            package="swarm_perception",
            executable="perception_node",
            name="perception_node",
            parameters=[{"use_sim_time": True}],
            remappings=[
                ("image_raw", "/camera/image_raw"),
                ("camera_info", "/camera/camera_info"),
            ],
        ),
    ])

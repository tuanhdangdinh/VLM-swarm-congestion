"""Per-robot Nav2 bringup: static `map -> <robot_id>/odom` TF (ground-truth
shortcut, see phase2-nav2-stack.md S5) plus the namespaced Nav2 stack (added
in Task 6).

`/<robot_id>/odom` is spawn-relative, not absolute-world (Task 5 correction
in phase2-nav2-stack.md S5): `IsaacComputeOdometry` zeroes its reference at
node initialization rather than reading the chassis's absolute world pose.
The static `map -> odom` transform therefore must equal the robot's spawn
pose (x, y, yaw from the scenario config), not identity. Spawn pose is not
known to this reusable launch file, so the caller supplies it via the
required `x`/`y`/`yaw` launch arguments — no default is provided, so a
caller who forgets them gets a loud missing-argument error at launch time
instead of silently reintroducing the identity-transform bug this task
corrected.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    robot_id = LaunchConfiguration("robot_id")
    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    yaw = LaunchConfiguration("yaw")
    return LaunchDescription(
        [
            DeclareLaunchArgument("robot_id", description="e.g. robot_1"),
            DeclareLaunchArgument(
                "x",
                description="Robot's spawn-pose x (m) from the scenario config; "
                "this is the map->odom translation, not identity.",
            ),
            DeclareLaunchArgument(
                "y",
                description="Robot's spawn-pose y (m) from the scenario config.",
            ),
            DeclareLaunchArgument(
                "yaw",
                description="Robot's spawn-pose yaw (rad) from the scenario config.",
            ),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="map_to_odom_ground_truth",
                # Ground-truth shortcut (deliberate PoC, not real-robot path):
                # map -> <robot_id>/odom equals the robot's spawn pose, since
                # IsaacComputeOdometry's odom frame is spawn-relative, not
                # absolute-world (verified Task 5; see phase2-nav2-stack.md
                # S5 "Correction"). Uses the current documented flag syntax
                # (--x/--y/--frame-id/...), not the deprecated 8-positional-
                # arg form.
                arguments=[
                    "--x", x,
                    "--y", y,
                    "--z", "0.0",
                    "--roll", "0.0",
                    "--pitch", "0.0",
                    "--yaw", yaw,
                    "--frame-id", "map",
                    "--child-frame-id", [robot_id, "/odom"],
                ],
            ),
        ]
    )

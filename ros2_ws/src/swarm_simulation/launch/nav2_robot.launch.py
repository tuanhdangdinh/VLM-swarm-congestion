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

Task 6 adds the namespaced Nav2 navigation stack (controller, planner,
costmaps, BT navigator, behavior server) via `nav2_bringup`'s
`navigation_launch.py`, plus a single shared, non-namespaced `map_server` +
`lifecycle_manager` for the static map (see phase2-nav2-stack.md S11 for the
verified convention and why). This deliberately does NOT use
`nav2_bringup`'s full `bringup_launch.py`/`localization_launch.py`: those
also launch `nav2_amcl`, which publishes its own `map -> odom` TF and would
collide with the ground-truth static transform above (spec S5 Option A is
explicit: bypass AMCL). `navigation_launch.py` only contains
controller/planner/costmap/bt_navigator/waypoint_follower/behavior_server —
no localization nodes — so it composes cleanly with the static TF.

`navigation_launch.py` does NOT itself push a ROS namespace onto its nodes
(verified on host: the unmodified include alone produces a flat
`/controller_server`, not `/robot_1/controller_server`) — `bringup_launch.py`
applies `PushRosNamespace` around its `GroupAction` itself, but
`navigation_launch.py` is meant to be included from inside that group, not
called standalone. Without it, every namespace-scoped param lookup in the
`RewrittenYaml`-rewritten params file (rooted under `<robot_id>:`) silently
misses, and `controller_server` falls back to its plugin defaults — which
have no critics configured, so it fails to configure
("No critics defined for FollowPath") even though the params file looks
correct on disk. Fixed here by wrapping the include in our own
`GroupAction([PushRosNamespace(robot_id), IncludeLaunchDescription(...)])`,
matching what `bringup_launch.py` does internally.

`navigation_launch.py` also does not frame-prefix anything itself (verified
against the installed Jazzy source: it only remaps the `/tf`/`/tf_static`
*topics*, not frame_id strings -- "there doesn't seem to be a better
alternative" per its own comment). Nav2's own upstream multirobot example
params (`nav2_multirobot_params_all.yaml`) leave `global_frame`/
`robot_base_frame` unprefixed, because their assumed setup gives each robot
an isolated, also-unprefixed TF tree under its own namespace. This project's
Isaac bridge instead publishes one shared `/tf` topic carrying
namespace-prefixed frame_ids for every robot (verified via `ros2 topic echo
/tf`: `frame_id: robot_1/odom`, `child_frame_id: robot_1/base_footprint`) --
a different, also-valid convention, but one where `nav2_params.yaml`'s frame
fields must themselves carry the `<robot_id>/` prefix to match. `map`
stays unprefixed (one shared warehouse map frame); `odom`/`base_link` do not.
`nav2_params.yaml` spells these as the literal placeholder
`<robot_namespace>` (matching Nav2's own substitution-token convention from
`bringup_launch.py`'s `ReplaceString`, reused here rather than invented) and
this launch file substitutes it via the same `ReplaceString` action. Differs
from `bringup_launch.py`'s own usage in one respect: upstream replaces with
`'/' + namespace` (leading slash) because its example only ever uses the
token in *topic* fields (`<robot_namespace>/scan`), where a leading slash is
the absolute-topic convention; this project's tokens sit in *frame_id*
fields, where tf2 frame names are conventionally unprefixed by a leading
slash, so the substitution here uses the bare `robot_id` instead.

Because `navigation_launch.py` remaps absolute `/tf` and `/tf_static` to
relative `tf` and `tf_static` inside every node, our outer namespace push
would otherwise make Nav2 listen on `/robot_1/tf` and `/robot_1/tf_static`,
while Isaac publishes the multi-robot TF tree on shared global `/tf` and
`/tf_static`. The group-level remaps below preserve namespaced Nav2 nodes
while keeping TF subscriptions on the shared topics.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from nav2_common.launch import ReplaceString
from ament_index_python.packages import get_package_share_directory


def generate_launch_description() -> LaunchDescription:
    robot_id = LaunchConfiguration("robot_id")
    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    yaw = LaunchConfiguration("yaw")

    nav2_bringup_dir = get_package_share_directory("nav2_bringup")
    sim_dir = get_package_share_directory("swarm_simulation")
    map_yaml = PathJoinSubstitution([sim_dir, "maps", "warehouse_map.yaml"])
    raw_params_file = PathJoinSubstitution([sim_dir, "config", "nav2_params.yaml"])
    # Substitute the literal `<robot_namespace>` token in nav2_params.yaml's
    # frame_id fields with the bare robot_id (no leading slash -- see module
    # docstring for why this differs from bringup_launch.py's own '/' +
    # namespace convention). Passed straight through as `params_file`, not
    # wrapped in our own ParameterFile/RewrittenYaml here -- verified against
    # the installed Jazzy navigation_launch.py source: it does its own
    # `ParameterFile(RewrittenYaml(source_file=params_file, ...))` wrapping
    # internally and expects `params_file` to be a plain path substitution.
    params_file = ReplaceString(
        source_file=raw_params_file,
        replacements={"<robot_namespace>": robot_id},
    )

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
            # Shared, non-namespaced map_server: one static map for the whole
            # warehouse, not per-robot. Verified against the installed Jazzy
            # nav2_bringup source in the ROS container (phase2-nav2-stack.md S11) — its own
            # multi-robot examples namespace map_server per-robot only
            # because they also namespace AMCL with it via
            # localization_launch.py; since this design bypasses AMCL, there
            # is nothing per-robot about the map itself, so a single shared
            # instance avoids redundant identical map_server processes.
            Node(
                package="nav2_map_server",
                executable="map_server",
                name="map_server",
                parameters=[{"use_sim_time": True, "yaml_filename": map_yaml}],
            ),
            Node(
                package="nav2_lifecycle_manager",
                executable="lifecycle_manager",
                name="lifecycle_manager_map_server",
                parameters=[
                    {
                        "use_sim_time": True,
                        "autostart": True,
                        "node_names": ["map_server"],
                    }
                ],
            ),
            GroupAction(
                [
                    PushRosNamespace(robot_id),
                    SetRemap(src="tf", dst="/tf"),
                    SetRemap(src="tf_static", dst="/tf_static"),
                    IncludeLaunchDescription(
                        PythonLaunchDescriptionSource(
                            PathJoinSubstitution(
                                [nav2_bringup_dir, "launch", "navigation_launch.py"]
                            )
                        ),
                        launch_arguments={
                            "namespace": robot_id,
                            "use_sim_time": "true",
                            "params_file": params_file,
                            "autostart": "true",
                        }.items(),
                    ),
                ]
            ),
        ]
    )

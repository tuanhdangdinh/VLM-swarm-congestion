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

Verified on host (`ros2 node info` + captured `/proc/<pid>/cmdline`) that an
earlier version of this fix did NOT work: it used `SetRemap(src="tf",
dst="/tf")`, a *relative* match key, which `PushRosNamespace(robot_id)`
turns into rule `/robot_1/tf:=/tf` on the node's command line. rclcpp/rcl
remapping only fires when a rule's match key equals the literal topic name a
node's `create_subscription` call requests; `tf2_ros::TransformListener`
always requests the *absolute* topic `/tf` (and `/tf_static`), regardless of
namespace, so a relative-keyed rule can never match it and was a no-op.
`navigation_launch.py`'s own `remappings=[('/tf', 'tf'), ('/tf_static',
'tf_static')]` (absolute match keys, passed as each `Node()`'s own
`remappings=` kwarg) is therefore the only rule that ever matched, and it won
by being the only candidate, not by remap-precedence order: it redirected
the listener to relative `tf`, which the namespace push then turned into
`/robot_1/tf` -- a topic nothing publishes on, hence the TF timeout, even
though `ros2 topic echo /tf` showed Isaac's shared TF tree alive the whole
time. Confirmed via `ros2 node info
/robot_1/transform_listener_impl_<hash>` showing `Subscribers: /robot_1/tf,
/robot_1/tf_static` before this fix.

Fixed by giving our group-level `SetRemap` an *absolute* match key instead
(`src="/tf"`, `src="/tf_static"`): this matches the same literal topic name
`TransformListener` requests, so our identity rule (`/tf` -> `/tf`) now has a
real candidate match, unlike the old relative-keyed version. Our rule and
`navigation_launch.py`'s own `/tf:=tf` rule now both key on the literal
`/tf` request, and empirically ours wins -- confirmed via `ros2 node info`
post-fix, not derived from any documented rcl remap-precedence rule (which
was not independently verified here, so do not assume a specific ordering
mechanism if this stops working after a launch_ros/rcl version bump;
re-verify the same way). Re-verified post-fix: `ros2 node info` on the
transform listener nodes now shows `Subscribers: /tf, /tf_static`, and the
"Timed out waiting for transform" log line stops appearing.

A second, separate, same-class bug was found while verifying the above fix:
`global_costmap`'s static map subscription showed up in `ros2 node info
/robot_1/global_costmap/global_costmap` as `/robot_1/map`, while the shared,
non-namespaced `map_server` above only ever publishes on unnamespaced `/map`
-- producing a recurring `Can't update static costmap layer, no map received`
warning (`map_server` itself confirmed actually publishing: `ros2 topic info
/map --verbose` showed 1 publisher with `TRANSIENT_LOCAL` durability, and
`ros2 topic echo /map --once` returned a message; `ros2 topic hz /map` is
the wrong tool here since a latched topic does not repeat).

Unlike the `/tf` case, this did **not** respond to the same `SetRemap` shape.
A relative-keyed `SetRemap(src="map", dst="/map")` was added here first
(the natural counterpart to the `/tf` fix's absolute key, since this
subscription request looked relative rather than hardcoded-absolute) and
its rule did appear correctly on the launched process's own command line
(`-r map:=/map`, confirmed via `pgrep -fa`/`/proc/<pid>/cmdline`); an
isolated rclpy `create_subscription("map", ...)` test with the identical
remap argument also resolved to `/map` exactly as expected. Yet
`ros2 node info` on `global_costmap` kept showing the subscription bound to
`/robot_1/map` regardless, both before and after that `SetRemap` was added,
and the warning kept recurring (re-confirmed via a non-zero
`grep -c "no map received"` count on a fresh launch after a full container
restart and rebuild, ruling out a stale-process artifact). `ros2 param get
/robot_1/global_costmap/global_costmap map_topic` showed the parameter
itself already held the literal string `/robot_1/map` with no override
configured anywhere in `nav2_params.yaml` -- indicating `nav2_costmap_2d`
builds this particular subscription's name from its own `map_topic`
parameter directly (namespace-qualifying it itself) rather than handing a
plain relative name through the ordinary launch-time remap pipeline that
`/tf` goes through, so no `SetRemap` rule, of either key style, can
intercept it; this was not independently confirmed against the
`nav2_costmap_2d`/`StaticLayer` source (binary-only install on this host,
no source tree available to inspect), only inferred from this parameter
behavior plus the `SetRemap`'s otherwise-confirmed inertness.

Fixed instead in `nav2_params.yaml`'s `global_costmap.global_costmap.
map_topic`, set directly to the absolute literal `/map`, bypassing
remapping entirely. Verified via `ros2 node info` after rebuilding
(`colcon build --merge-install --packages-select swarm_simulation`) and a
fresh launch: `global_costmap`'s `Subscribers` list shows `/map`, not
`/robot_1/map`; `grep -c "no map received"` over a fresh launch log was 0
across the full lifecycle bring-up; `global_costmap`/`local_costmap` and the
nodes depending on them (`controller_server`, `planner_server`,
`bt_navigator`) all reached lifecycle `active`. The inert `SetRemap(src=
"map", dst="/map")` rule was removed rather than left in place, since it
was confirmed to never match anything this subscription actually requests.

2026-09-16 — `localization` launch argument (`static` | `amcl`, default
`static`). This qualifies, but does not supersede, the ground-truth paragraph
above: `static` keeps exactly the verified behaviour described there (the
`map -> <robot_id>/odom` static publisher at the spawn pose) and stays the
default, so the verified closed loop is unchanged unless the flag is set.
`localization:=amcl` instead starts one namespaced `nav2_amcl` per robot, plus
its own `lifecycle_manager_localization`, which derives `map ->
<robot_id>/odom` from that robot's lidar against the shared static map; the
static publisher is suppressed in that mode, since two publishers of the same
TF edge would fight. `nav2_bringup`'s `localization_launch.py` is still not
used, but now for a reason unrelated to AMCL: it hardcodes its own
`map_server` + `lifecycle_manager`, which would collide by name with the
shared, non-namespaced pair launched below. The AMCL node is therefore
declared directly here and wrapped in the same
`ParameterFile(RewrittenYaml(root_key=<robot_id>, ...))` the vendored
`nav2_navigation.launch.py` applies to its own nodes, so the `amcl:` block in
`nav2_params.yaml` resolves under the namespace root the same way the rest of
the stack's parameters do. The shared non-namespaced `map_server` remains
correct under `amcl` — the "since this design bypasses AMCL" comment on that
node keeps its conclusion but loses its stated reason: `amcl:`'s `map_topic`
is the absolute literal `/map`, so every robot's AMCL reads the one shared map
publisher and still needs nothing per-robot about the map. AMCL publishes only
TF and `~/amcl_pose`; it never writes `/<robot_id>/odom`, so M4's
odometry-closed primitives (backup, hold) behave identically under either
mode. Not yet verified on the host — see phase2-nav2-stack.md S12.

2026-09-16 — `localization:=camera`, a third mode alongside `static` and
`amcl`. It starts one namespaced `camera_localizer` node per robot
(`swarm_perception`), which plays exactly AMCL's role — it owns the
`map -> <robot_id>/odom` edge — but derives it from M1's overhead camera
instead of from lidar: the camera measures `T_map_base` from that robot's ArUco
marker (M1's world frame is the Nav2 `map` frame, verified), TF supplies
`T_odom_base`, and the published correction is
`T_map_base . T_odom_base^-1`. It exists because AMCL localizes to 2 cm while
the robots sit near the corridor but degenerates during the yield manoeuvre in
this symmetric warehouse, where the camera's fix is global and scenario-
independent. Like `amcl`, it suppresses the static ground-truth publisher (one
writer per TF edge); unlike `amcl`, it needs no per-scenario map. Two
operational notes. **M1 must already be running and publishing
`/perception/scene_state` before Nav2 activates**: under `camera` there is no
`map -> odom` at all until the first camera fix, and the costmaps block waiting
for that edge exactly as they do under `amcl`. And the node deliberately looks
up the *latest* `odom -> base_footprint` rather than the transform at the scene
stamp, because `scene_state.stamp` is the camera image header time, which Isaac
fills from SYSTEM time, while TF and every node here run on SIM time
(`use_sim_time: true`) — the two stamps are not comparable, so a stamped lookup
would fail or extrapolate wildly. The resulting latency error is bounded by
speed * camera latency (<= 0.2 m/s * ~0.1 s = <= 2 cm). The node carries no
node-level `/tf` remaps, for the same reason the AMCL node below carries none.

2026-09-16 — `map_yaml` launch argument, defaulting to the shared
`maps/warehouse_map.yaml` so default behaviour is unchanged. It exists because
a scenario may author collision bodies the default map does not contain: the
`head_on_deadlock` `aisle_barrier` blocks are real physics bodies in Isaac, so
each robot's lidar sees corridor walls at |y| = 0.275 m where the default map
says open aisle. Measured with `localization:=amcl`: AMCL comes up correctly
and then converges to a ~1 m error. `isaac/scripts/generate_warehouse_map.py
--scenario` bakes those blocks into `maps/warehouse_map_<scenario>.yaml`, which
this argument selects for the shared `map_server` (and hence for every robot's
AMCL and global costmap, both of which read the one absolute `/map` topic).
"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from launch_ros.descriptions import ParameterFile
from launch_ros.parameter_descriptions import ParameterValue
from nav2_common.launch import ReplaceString, RewrittenYaml


def _localization_equals(mode: str, localization: LaunchConfiguration) -> IfCondition:
    """Build a condition that fires when the `localization` argument equals `mode`.

    Args:
        mode: Expected value of the `localization` launch argument.
        localization: Launch configuration holding the selected mode.

    Returns:
        Condition true only when `localization` resolves to `mode`. A fresh
        instance per call, so no two actions share a condition object.
    """
    return IfCondition(PythonExpression(["'", localization, "' == '", mode, "'"]))


def generate_launch_description() -> LaunchDescription:
    robot_id = LaunchConfiguration("robot_id")
    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    yaw = LaunchConfiguration("yaw")
    start_map_server = LaunchConfiguration("start_map_server")
    localization = LaunchConfiguration("localization")
    map_yaml = LaunchConfiguration("map_yaml")

    sim_dir = get_package_share_directory("swarm_simulation")
    default_map_yaml = PathJoinSubstitution([sim_dir, "maps", "warehouse_map.yaml"])
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
    # The one exception to the "passed straight through" note above: the AMCL
    # node below is declared by this file, not by nav2_navigation.launch.py, so
    # nothing else wraps the params file on its behalf. Mirror the vendored
    # launch's wrapping exactly (root_key = robot_id, convert_types,
    # allow_substs) so `amcl:` resolves for a node whose fully-qualified name
    # is `/<robot_id>/amcl`, the same way the rest of the stack's blocks do.
    # Substitutions are inert until performed, so building this in `static`
    # mode costs nothing; only the amcl node consumes it.
    amcl_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key=robot_id,
            param_rewrites={},
            convert_types=True,
        ),
        allow_substs=True,
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
            DeclareLaunchArgument(
                "start_map_server",
                default_value="true",
                description="Launch map_server + lifecycle_manager_map_server. "
                "Set to false for the second (and further) robot to avoid "
                "duplicate non-namespaced nodes conflicting on the same name. "
                "The first robot's map_server serves all robots since the "
                "warehouse map is shared and not per-robot.",
            ),
            DeclareLaunchArgument(
                "map_yaml",
                default_value=default_map_yaml,
                description="Static map YAML; pass the per-scenario map (e.g. "
                "warehouse_map_head_on_deadlock.yaml) so AMCL and the global "
                "planner see runtime barriers.",
            ),
            DeclareLaunchArgument(
                "localization",
                default_value="static",
                description="static|amcl|camera. static: ground-truth map->odom "
                "at the spawn pose (PoC default). amcl: per-robot nav2_amcl "
                "publishes map-><robot>/odom from lidar; initial pose from "
                "x/y/yaw. camera: per-robot camera_localizer publishes "
                "map-><robot>/odom from M1's overhead-camera pose; requires M1 "
                "running on /perception/scene_state before Nav2 activates.",
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
                # Suppressed under localization:=amcl, where nav2_amcl owns
                # this same TF edge; two publishers of one edge would fight.
                condition=_localization_equals("static", localization),
            ),
            # Shared, non-namespaced map_server: one static map for the whole
            # warehouse, not per-robot. Verified against the installed Jazzy
            # nav2_bringup source in the ROS container (phase2-nav2-stack.md S11) — its own
            # multi-robot examples namespace map_server per-robot only
            # because they also namespace AMCL with it via
            # localization_launch.py; since this design bypasses AMCL, there
            # is nothing per-robot about the map itself, so a single shared
            # instance avoids redundant identical map_server processes.
            # Guard with start_map_server (default true) so a second robot's
            # launch can pass start_map_server:=false to skip these, avoiding
            # duplicate non-namespaced node name conflicts when two instances
            # of this launch file are running simultaneously.
            # yaml_filename is the `map_yaml` argument, so a scenario map
            # reaches every robot through this one server.
            Node(
                package="nav2_map_server",
                executable="map_server",
                name="map_server",
                parameters=[{"use_sim_time": True, "yaml_filename": map_yaml}],
                condition=IfCondition(start_map_server),
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
                condition=IfCondition(start_map_server),
            ),
            GroupAction(
                [
                    PushRosNamespace(robot_id),
                    # Absolute match keys ("/tf", not "tf"): TransformListener
                    # always subscribes to the absolute topic regardless of
                    # namespace, so this is the literal name a remap rule
                    # must match to fire at all (see module docstring for the
                    # verified failure of the relative-key version of this
                    # rule). This identity rule is consumed before
                    # navigation_launch.py's own internal `/tf:=tf` rule can
                    # act on the same request.
                    SetRemap(src="/tf", dst="/tf"),
                    SetRemap(src="/tf_static", dst="/tf_static"),
                    # No SetRemap rule for `map` here, unlike /tf/tf_static
                    # above: `ros2 node info` showed global_costmap's static
                    # map subscription bound to `/robot_1/map`, and the
                    # process's own command line did carry a relative-keyed
                    # `-r map:=/map` rule that an isolated rclpy
                    # create_subscription("map", ...) test confirmed resolves
                    # correctly through ordinary remapping -- yet the costmap
                    # node's actual subscription stayed on `/robot_1/map`
                    # regardless. `ros2 param get
                    # .../global_costmap map_topic` showed the param itself
                    # already holds the namespace-qualified string
                    # `/robot_1/map` with no override configured, indicating
                    # nav2_costmap_2d's `Costmap2DROS`/`StaticLayer` build
                    # this subscription name from the `map_topic` parameter
                    # directly rather than through the launch-time relative-
                    # name-plus-remap pipeline /tf goes through, so a
                    # SetRemap rule here cannot intercept it. Fixed instead in
                    # nav2_params.yaml's `global_costmap.map_topic`, set to
                    # the absolute literal `/map` (see that file's comment).
                    # Use the vendored nav2_navigation.launch.py (same dir)
                    # rather than the upstream nav2_bringup version: Jazzy
                    # builds that include route_server in lifecycle_nodes block
                    # activation for this project (route_server needs a route
                    # graph file; see nav2_navigation.launch.py header comment).
                    IncludeLaunchDescription(
                        PythonLaunchDescriptionSource(
                            PathJoinSubstitution(
                                [sim_dir, "launch", "nav2_navigation.launch.py"]
                            )
                        ),
                        launch_arguments={
                            "namespace": robot_id,
                            "use_sim_time": "true",
                            "params_file": params_file,
                            "autostart": "true",
                        }.items(),
                    ),
                    # localization:=amcl only. Deliberately no node-level
                    # remappings= here, unlike navigation_launch.py's nodes:
                    # the group-level absolute-keyed SetRemap rules above are
                    # what keep TF on the shared /tf and /tf_static topics
                    # (see module docstring for the verified failure mode of
                    # relative keys), and adding a node-level `/tf` rule here
                    # would only reintroduce the candidate that lost.
                    # Overrides after amcl_params win (launch_ros applies the
                    # parameters list in order); the initial pose is the same
                    # spawn pose the static transform used, so AMCL starts
                    # converged rather than hunting for a global fix.
                    Node(
                        package="nav2_amcl",
                        executable="amcl",
                        name="amcl",
                        output="screen",
                        parameters=[
                            amcl_params,
                            {
                                "use_sim_time": True,
                                "set_initial_pose": True,
                                "initial_pose.x": ParameterValue(x, value_type=float),
                                "initial_pose.y": ParameterValue(y, value_type=float),
                                "initial_pose.z": 0.0,
                                "initial_pose.yaw": ParameterValue(
                                    yaw, value_type=float
                                ),
                            },
                        ],
                        condition=_localization_equals("amcl", localization),
                    ),
                    # Separate from lifecycle_manager_navigation (owned by the
                    # vendored navigation launch) and from
                    # lifecycle_manager_map_server: AMCL is per-robot, so this
                    # manager is namespaced with it and manages only `amcl`.
                    Node(
                        package="nav2_lifecycle_manager",
                        executable="lifecycle_manager",
                        name="lifecycle_manager_localization",
                        output="screen",
                        parameters=[
                            {
                                "use_sim_time": True,
                                "autostart": True,
                                "node_names": ["amcl"],
                            }
                        ],
                        condition=_localization_equals("amcl", localization),
                    ),
                    # localization:=camera only. Same TF role as the amcl node
                    # above (sole publisher of map -> <robot_id>/odom) and the
                    # same deliberate absence of node-level `/tf` remappings —
                    # the group-level absolute-keyed SetRemap rules are what
                    # keep its broadcaster and listener on shared /tf.
                    # No lifecycle manager: this is a plain rclpy node, not a
                    # nav2 lifecycle node, so it starts publishing as soon as
                    # M1's first scene state and the robot's odometry TF are
                    # both available. Its frame and topic defaults derive from
                    # robot_id inside the node (scene_state_topic stays the
                    # absolute, shared /perception/scene_state, which one M1
                    # instance publishes for every robot), so robot_id is the
                    # only parameter this launch file needs to pass.
                    Node(
                        package="swarm_perception",
                        executable="camera_localizer_node",
                        name="camera_localizer",
                        output="screen",
                        # ParameterValue(..., value_type=str) for the same
                        # reason the amcl node wraps its floats: launch_ros
                        # cannot infer a parameter's type from a bare
                        # substitution, and a mis-inferred robot_id would
                        # either trip the node's fail-fast check or, worse,
                        # arrive mangled.
                        parameters=[
                            {
                                "use_sim_time": True,
                                "robot_id": ParameterValue(robot_id, value_type=str),
                            }
                        ],
                        condition=_localization_equals("camera", localization),
                    ),
                ]
            ),
        ]
    )

"""Offline checks on the `amcl:` block and the `localization` launch default.

Pure YAML/AST inspection -- no ROS 2 runtime, no launch execution. These guard
the conventions that are invisible to a syntax check but silently break AMCL:
namespace-token frame ids, absolute topic literals, sensor-matched laser
ranges, and the `static` default that keeps the verified closed loop intact.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PARAMS_PATH = REPO_ROOT / "ros2_ws/src/swarm_simulation/config/nav2_params.yaml"
LAUNCH_PATH = REPO_ROOT / "ros2_ws/src/swarm_simulation/launch/nav2_robot.launch.py"
LIDAR_CONFIG_PATH = REPO_ROOT / "isaac/config/lidar/turtlebot3_lds_01.json"

NAMESPACE_TOKEN = "<robot_namespace>"


def _amcl_params() -> dict:
    params = yaml.safe_load(PARAMS_PATH.read_text())
    assert "amcl" in params, "nav2_params.yaml has no top-level amcl block"
    return params["amcl"]["ros__parameters"]


def _launch_argument_default(name: str) -> str:
    """Return the `default_value` of a DeclareLaunchArgument call, via AST."""
    module = ast.parse(LAUNCH_PATH.read_text())
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        func_name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if func_name != "DeclareLaunchArgument":
            continue
        if not node.args or ast.literal_eval(node.args[0]) != name:
            continue
        for keyword in node.keywords:
            if keyword.arg == "default_value":
                return ast.literal_eval(keyword.value)
        raise AssertionError(f"DeclareLaunchArgument({name!r}) has no default_value")
    raise AssertionError(f"DeclareLaunchArgument({name!r}) not found")


def _launch_argument_default_node(name: str) -> ast.expr:
    """Return the raw AST of a DeclareLaunchArgument's `default_value`.

    Unlike `_launch_argument_default`, this does not evaluate the expression, so
    it also works for a default built from launch substitutions.
    """
    module = ast.parse(LAUNCH_PATH.read_text())
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        func_name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if func_name != "DeclareLaunchArgument":
            continue
        if not node.args or ast.literal_eval(node.args[0]) != name:
            continue
        for keyword in node.keywords:
            if keyword.arg == "default_value":
                return keyword.value
        raise AssertionError(f"DeclareLaunchArgument({name!r}) has no default_value")
    raise AssertionError(f"DeclareLaunchArgument({name!r}) not found")


def test_map_yaml_launch_default_is_base_map():
    default = _launch_argument_default_node("map_yaml")
    # Resolved through the module-level `default_map_yaml` binding, so follow
    # the name to the PathJoinSubstitution it is assigned.
    if isinstance(default, ast.Name):
        module = ast.parse(LAUNCH_PATH.read_text())
        assignments = [
            n
            for n in ast.walk(module)
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == default.id for t in n.targets)
        ]
        assert len(assignments) == 1, f"{default.id} assigned {len(assignments)} times"
        default = assignments[0].value

    source = ast.unparse(default)
    assert "PathJoinSubstitution" in source
    assert "'maps'" in source
    assert "'warehouse_map.yaml'" in source


def test_map_server_reads_the_map_yaml_launch_argument():
    # Guards the inert-argument failure: a `map_yaml` argument that map_server
    # does not read would still declare, parse, and default correctly.
    source = LAUNCH_PATH.read_text()
    module = ast.parse(source)
    bindings = [
        ast.unparse(node.value)
        for node in ast.walk(module)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "map_yaml" for t in node.targets)
    ]

    assert bindings == ["LaunchConfiguration('map_yaml')"]
    assert '"yaml_filename": map_yaml' in source


def test_amcl_block_uses_namespace_token_frames():
    params = _amcl_params()

    assert NAMESPACE_TOKEN in params["odom_frame_id"]
    assert NAMESPACE_TOKEN in params["base_frame_id"]
    # `map` is the single shared warehouse frame, never per-robot.
    assert params["global_frame_id"] == "map"
    assert NAMESPACE_TOKEN not in params["global_frame_id"]


def test_amcl_scan_and_map_topics_are_absolute():
    params = _amcl_params()

    assert params["scan_topic"].startswith("/")
    assert params["map_topic"].startswith("/")


def test_amcl_laser_ranges_match_lds_config():
    params = _amcl_params()
    lidar = json.loads(LIDAR_CONFIG_PATH.read_text())

    assert params["laser_min_range"] == lidar["minRange"]
    assert params["laser_max_range"] == lidar["maxRange"]


def test_static_localization_is_launch_default():
    assert _launch_argument_default("localization") == "static"


def test_camera_localization_mode_is_declared():
    # Asserts the gating, not a docstring mention: a `camera` paragraph in the
    # module docstring with no gated node would launch nothing, and a gated
    # node under the wrong mode string would never fire.
    source = LAUNCH_PATH.read_text()
    ast.parse(source)

    assert '_localization_equals("camera", localization)' in source
    assert 'executable="camera_localizer_node"' in source
    assert 'package="swarm_perception"' in source
    assert "static|amcl|camera" in _launch_argument_description("localization")


def test_camera_localizer_receives_initial_pose_parameters():
    # Guards the bring-up race the seed fixes: a camera Node lacking
    # initial_pose.* would have no map-><robot>/odom until the first camera
    # fix, reintroducing the costmap-activation timeout this parameter avoids.
    module = ast.parse(LAUNCH_PATH.read_text())

    camera_node = None
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        func_name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if func_name != "Node":
            continue
        executable = next(
            (kw.value for kw in node.keywords if kw.arg == "executable"), None
        )
        if executable is not None and ast.literal_eval(executable) == "camera_localizer_node":
            camera_node = node
            break

    assert camera_node is not None, "camera_localizer_node Node(...) not found"
    parameters_node = next(kw.value for kw in camera_node.keywords if kw.arg == "parameters")
    parameters_source = ast.unparse(parameters_node)

    assert "set_initial_pose" in parameters_source
    assert "initial_pose.x" in parameters_source
    assert "initial_pose.y" in parameters_source
    assert "initial_pose.yaw" in parameters_source


def _launch_argument_description(name: str) -> str:
    """Return the concatenated `description` string of a DeclareLaunchArgument."""
    module = ast.parse(LAUNCH_PATH.read_text())
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        func_name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if func_name != "DeclareLaunchArgument":
            continue
        if not node.args or ast.literal_eval(node.args[0]) != name:
            continue
        for keyword in node.keywords:
            if keyword.arg == "description":
                return ast.literal_eval(keyword.value)
        raise AssertionError(f"DeclareLaunchArgument({name!r}) has no description")
    raise AssertionError(f"DeclareLaunchArgument({name!r}) not found")


def _obstacle_scan_source(costmap: str) -> dict:
    params = yaml.safe_load(PARAMS_PATH.read_text())
    layer = params[costmap][costmap]["ros__parameters"]["obstacle_layer"]
    return layer["scan"]


def test_global_costmap_scan_clearing_enabled():
    # v3 costmap fix H: Jazzy defaults `clearing` to false, which kept every
    # mis-registered mark lethal until a recovery clear.
    assert _obstacle_scan_source("global_costmap")["clearing"] is True


def test_local_costmap_scan_clearing_enabled():
    assert _obstacle_scan_source("local_costmap")["clearing"] is True


def test_costmap_raytrace_range_covers_obstacle_range():
    # The shipped raytrace default (3.0 m) < obstacle_max_range (3.5 m) would
    # leave marks 3.0-3.5 m out uncleared even with clearing on.
    for costmap in ("global_costmap", "local_costmap"):
        scan = _obstacle_scan_source(costmap)
        assert scan["raytrace_max_range"] >= scan["obstacle_max_range"]
        assert scan["marking"] is True

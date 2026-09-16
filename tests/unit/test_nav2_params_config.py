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

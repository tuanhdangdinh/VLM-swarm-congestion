from __future__ import annotations

import ast
from pathlib import Path


LAUNCH_PATH = (
    Path(__file__).resolve().parents[2]
    / "ros2_ws/src/swarm_simulation/launch/nav2_navigation.launch.py"
)


def _lifecycle_nodes() -> list[str]:
    module = ast.parse(LAUNCH_PATH.read_text())
    for node in ast.walk(module):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "lifecycle_nodes":
                return ast.literal_eval(node.value)
    raise AssertionError("lifecycle_nodes assignment not found")


def test_vendored_navigation_launch_excludes_unused_lifecycle_blockers():
    lifecycle_nodes = _lifecycle_nodes()
    source = LAUNCH_PATH.read_text()

    assert "route_server" not in lifecycle_nodes
    assert "velocity_smoother" not in lifecycle_nodes
    assert "collision_monitor" in lifecycle_nodes
    assert "nav2_velocity_smoother" not in source

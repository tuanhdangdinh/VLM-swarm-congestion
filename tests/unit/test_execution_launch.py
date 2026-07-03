from __future__ import annotations

import ast
from pathlib import Path


LAUNCH_PATH = (
    Path(__file__).resolve().parents[2]
    / "ros2_ws/src/swarm_execution/launch/execution.launch.py"
)


def _node_calls() -> dict[str, ast.Call]:
    module = ast.parse(LAUNCH_PATH.read_text())
    nodes: dict[str, ast.Call] = {}
    for call in ast.walk(module):
        if not isinstance(call, ast.Call):
            continue
        if not (isinstance(call.func, ast.Name) and call.func.id == "Node"):
            continue
        executable = None
        for keyword in call.keywords:
            if keyword.arg == "executable":
                executable = ast.literal_eval(keyword.value)
        if executable is not None:
            nodes[executable] = call
    return nodes


def _uses_sim_time(call: ast.Call) -> bool:
    for keyword in call.keywords:
        if keyword.arg != "parameters":
            continue
        parameters = ast.literal_eval(keyword.value)
        for entry in parameters:
            if isinstance(entry, dict) and entry.get("use_sim_time") is True:
                return True
    return False


def test_command_bus_node_uses_sim_time():
    nodes = _node_calls()
    assert _uses_sim_time(nodes["command_bus_node"])


def test_coordination_client_node_uses_sim_time():
    nodes = _node_calls()
    assert _uses_sim_time(nodes["coordination_client_node"])


def test_safety_monitor_node_stays_on_wall_time():
    nodes = _node_calls()
    assert not _uses_sim_time(nodes["safety_monitor_node"])

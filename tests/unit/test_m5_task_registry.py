"""Unit tests for the M5 task/status registry with coordination overrides."""
from __future__ import annotations

import json

from swarm_orchestrator.models import OrchestratorConfig, TaskAssignment
from swarm_orchestrator.task_registry import TaskRegistry


def _config() -> OrchestratorConfig:
    return OrchestratorConfig(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={
            "robot_1": TaskAssignment(task="pick_b", goal=(4.0, 2.0)),
            "robot_0": TaskAssignment(task="pick_a", goal=(3.0, 1.5)),
        },
        frame_dump_dir="data/logs/m5_frames",
    )


def test_load_initial_sets_base_assignments():
    reg = TaskRegistry()
    reg.load_initial(_config())
    assert reg.effective("robot_0") == ("pick_a", (3.0, 1.5))
    assert reg.effective("robot_1") == ("pick_b", (4.0, 2.0))


def test_effective_returns_none_for_unknown_robot():
    reg = TaskRegistry()
    assert reg.effective("ghost") is None


def test_override_changes_effective_goal_then_reverts_on_clear():
    reg = TaskRegistry()
    reg.load_initial(_config())
    reg.set_override("robot_0", action="yield", goal=(1.0, 1.0), command_id="c1")
    assert reg.effective("robot_0") == ("yield", (1.0, 1.0))
    reg.clear_override("robot_0")
    assert reg.effective("robot_0") == ("pick_a", (3.0, 1.5))


def test_to_json_is_sorted_and_carries_effective_values():
    reg = TaskRegistry()
    reg.load_initial(_config())
    reg.set_override("robot_0", action="reroute", goal=(9.0, 9.0), command_id="c1")
    payload = json.loads(reg.to_json())
    assert list(payload.keys()) == ["robot_0", "robot_1"]  # sorted
    assert payload["robot_0"]["task"] == "reroute"
    assert payload["robot_0"]["goal"] == [9.0, 9.0]
    assert payload["robot_1"]["task"] == "pick_b"


def test_to_json_is_deterministic():
    reg = TaskRegistry()
    reg.load_initial(_config())
    assert reg.to_json() == reg.to_json()

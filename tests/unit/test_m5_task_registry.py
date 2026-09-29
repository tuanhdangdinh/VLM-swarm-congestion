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


def test_mission_task_returns_the_base_task():
    reg = TaskRegistry()
    reg.load_initial(_config())
    assert reg.mission_task("robot_0") == "pick_a"


def test_mission_task_ignores_an_active_override():
    # The prompt renders the mission label, never a coordination action such
    # as "yield", which would hand the VLM the previous dispatch.
    reg = TaskRegistry()
    reg.load_initial(_config())
    reg.set_override("robot_0", action="yield", goal=(1.0, 1.0), command_id="c1")
    assert reg.mission_task("robot_0") == "pick_a"


def test_mission_task_returns_none_for_unknown_robot():
    assert TaskRegistry().mission_task("ghost") is None


def _delayed_config(delay: float) -> OrchestratorConfig:
    base = _config()
    tasks = dict(base.initial_tasks)
    tasks["robot_3"] = TaskAssignment(task="cross", goal=(1.85, 0.0), start_delay_sec=delay)
    return base.model_copy(update={"initial_tasks": tasks})


def test_registry_json_without_start_delay_is_unchanged():
    # The exact bytes every run before start_delay_sec published.
    reg = TaskRegistry()
    reg.load_initial(_config(), now=100.0)
    assert reg.to_json() == (
        '{"robot_0": {"goal": [3.0, 1.5], "task": "pick_a"}, '
        '"robot_1": {"goal": [4.0, 2.0], "task": "pick_b"}}'
    )
    assert reg.release_due(1e9) == []


def test_registry_json_never_publishes_priority():
    # priority is M3-only: M1 and M4 read this JSON, and it must not change.
    base = _config()
    tasks = {
        rid: task.model_copy(update={"priority": 5}) for rid, task in base.initial_tasks.items()
    }
    plain, prioritised = TaskRegistry(), TaskRegistry()
    plain.load_initial(base, now=100.0)
    prioritised.load_initial(base.model_copy(update={"initial_tasks": tasks}), now=100.0)
    assert prioritised.to_json() == plain.to_json()


def test_delayed_robot_is_published_pending_with_its_mission_goal():
    reg = TaskRegistry()
    reg.load_initial(_delayed_config(50.0), now=100.0)
    payload = json.loads(reg.to_json())
    assert payload["robot_3"] == {"task": "cross", "goal": [1.85, 0.0], "start_pending": True}
    assert "start_pending" not in payload["robot_0"]
    assert reg.is_pending("robot_3") is True
    assert reg.is_pending("robot_0") is False


def test_delayed_robot_is_released_once_its_delay_elapses():
    reg = TaskRegistry()
    reg.load_initial(_delayed_config(50.0), now=100.0)
    assert reg.release_due(149.9) == []
    assert reg.release_due(150.0) == ["robot_3"]
    assert reg.release_due(151.0) == []
    assert reg.is_pending("robot_3") is False
    assert "start_pending" not in json.loads(reg.to_json())["robot_3"]


def test_zero_start_delay_is_not_pending():
    reg = TaskRegistry()
    reg.load_initial(_delayed_config(0.0), now=100.0)
    assert reg.is_pending("robot_3") is False
    assert "start_pending" not in json.loads(reg.to_json())["robot_3"]


def test_pending_robot_keeps_the_flag_under_an_override():
    reg = TaskRegistry()
    reg.load_initial(_delayed_config(50.0), now=100.0)
    reg.set_override("robot_3", action="temporary_wait", goal=(1.85, 0.0), command_id="c1")
    assert json.loads(reg.to_json())["robot_3"]["start_pending"] is True

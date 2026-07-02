"""Unit tests for the M4 base-mission driver pure logic (no ROS2 runtime).

The driver decides which `navigate_to_pose` goals the coordination client should
(re)issue as it observes M5's `/coordination/tasks` registry plus the
`/coordination/commands` and `/coordination/status` streams. It owns base
navigation; the command bus owns a robot from command dispatch until the command
resolves.
"""
from __future__ import annotations

from swarm_execution.base_mission import BaseMissionDriver


def test_initial_registry_issues_navigate_for_each_robot():
    driver = BaseMissionDriver()

    issues = driver.on_registry(
        {
            "robot_1": {"task": "cross", "goal": [3.0, 0.0]},
            "robot_2": {"task": "cross", "goal": [-3.0, 0.0]},
        }
    )

    assert sorted(issues) == [("robot_1", (3.0, 0.0)), ("robot_2", (-3.0, 0.0))]


def test_accepted_goal_is_not_reissued():
    driver = BaseMissionDriver()
    registry = {"robot_1": {"task": "cross", "goal": [3.0, 0.0]}}
    driver.on_registry(registry)
    driver.on_goal_accepted("robot_1", (3.0, 0.0))

    assert driver.on_registry(registry) == []


def test_changed_goal_reissues_navigate():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_goal_accepted("robot_1", (3.0, 0.0))

    issues = driver.on_registry({"robot_1": {"task": "cross", "goal": [1.0, 2.0]}})

    assert issues == [("robot_1", (1.0, 2.0))]


def test_rejected_goal_is_reissued_on_retry():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    # Nav2 not yet ACTIVE: the initial send is rejected.
    driver.on_goal_rejected("robot_1")

    assert driver.retry() == [("robot_1", (3.0, 0.0))]


def test_accepted_goal_is_not_reissued_on_retry():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_goal_accepted("robot_1", (3.0, 0.0))

    assert driver.retry() == []


def test_command_suppresses_base_navigation_and_requests_cancel():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})

    # A coordination command for robot_1 hands ownership to the command bus.
    should_cancel = driver.on_command("robot_1")

    assert should_cancel is True
    # While suppressed, registry updates must not re-issue base navigation.
    assert driver.on_registry({"robot_1": {"task": "yield", "goal": [3.0, 0.0]}}) == []


def test_second_command_for_same_robot_does_not_request_cancel_again():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1")

    assert driver.on_command("robot_1") is False


def test_completed_status_resumes_base_navigation():
    driver = BaseMissionDriver()
    # yield's override goal equals the base goal, so the registry goal never
    # changes across the override — resumption cannot rely on a goal change.
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1")

    issues = driver.on_status("robot_1", "COMPLETED")

    assert issues == [("robot_1", (3.0, 0.0))]


def test_failed_status_also_resumes_base_navigation():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1")

    assert driver.on_status("robot_1", "FAILED") == [("robot_1", (3.0, 0.0))]


def test_republished_terminal_status_resumes_only_once():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1")

    first = driver.on_status("robot_1", "COMPLETED")
    # The command bus republishes each status ~3x; a second COMPLETED must not
    # re-issue another resume goal (which would thrash the robot's navigate).
    second = driver.on_status("robot_1", "COMPLETED")

    assert first == [("robot_1", (3.0, 0.0))]
    assert second == []


def test_non_terminal_status_does_not_resume():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1")

    assert driver.on_status("robot_1", "ACTIVE") == []
    # Still suppressed after a non-terminal status.
    assert driver.on_registry({"robot_1": {"task": "yield", "goal": [3.0, 0.0]}}) == []


def test_non_suppressed_robot_keeps_navigating_during_other_robots_override():
    driver = BaseMissionDriver()
    driver.on_registry(
        {
            "robot_1": {"task": "cross", "goal": [3.0, 0.0]},
            "robot_2": {"task": "cross", "goal": [-3.0, 0.0]},
        }
    )
    driver.on_command("robot_1")

    # robot_2 is untouched; a fresh goal for it still issues.
    issues = driver.on_registry(
        {
            "robot_1": {"task": "yield", "goal": [3.0, 0.0]},
            "robot_2": {"task": "cross", "goal": [-2.5, 0.0]},
        }
    )

    assert issues == [("robot_2", (-2.5, 0.0))]


# ---------------------------------------------------------------------------
# Node wiring (ROS2 bypassed via __new__)
# ---------------------------------------------------------------------------


import json as _json

from swarm_execution.coordination_client_node import CoordinationClientNode


class _StringMsg:
    def __init__(self, data: str) -> None:
        self.data = data


class _CmdMsg:
    def __init__(self, robot_id: str) -> None:
        self.robot_id = robot_id


class _StatusMsg:
    def __init__(self, robot_id: str, status: str) -> None:
        self.robot_id = robot_id
        self.status = status


class _FakeAdapter:
    def __init__(self) -> None:
        self.goals: list = []
        self.cancels: list = []
        self.on_results: dict = {}

    def send_goal(self, robot_id, x, y, yaw, on_result=None):
        self.goals.append((robot_id, x, y, yaw))
        self.on_results[robot_id] = on_result

    def cancel(self, robot_id):
        self.cancels.append(robot_id)


def _make_client():
    node = CoordinationClientNode.__new__(CoordinationClientNode)
    node._adapter = _FakeAdapter()
    node._driver = BaseMissionDriver()

    class _Logger:
        def info(self, _msg):
            pass

        def warning(self, _msg):
            pass

    node.get_logger = lambda: _Logger()
    return node


def test_node_issues_navigate_from_registry():
    node = _make_client()
    node._on_registry(
        _StringMsg(_json.dumps({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}}))
    )
    assert node._adapter.goals == [("robot_1", 3.0, 0.0, 0.0)]


def test_node_cancels_own_goal_on_command():
    node = _make_client()
    node._on_registry(
        _StringMsg(_json.dumps({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}}))
    )
    node._on_command(_CmdMsg("robot_1"))
    assert node._adapter.cancels == ["robot_1"]


def test_node_resumes_navigate_on_completed_status():
    node = _make_client()
    node._on_registry(
        _StringMsg(_json.dumps({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}}))
    )
    node._on_command(_CmdMsg("robot_1"))
    node._adapter.goals.clear()

    node._on_status(_StatusMsg("robot_1", "COMPLETED"))

    assert node._adapter.goals == [("robot_1", 3.0, 0.0, 0.0)]


def test_node_retry_reissues_when_goal_rejected():
    node = _make_client()
    reg = _StringMsg(_json.dumps({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}}))
    node._on_registry(reg)
    # Nav2 not yet ACTIVE: the goal is rejected.
    node._adapter.on_results["robot_1"]("FAILED", "goal rejected")
    node._adapter.goals.clear()

    node._on_retry()

    assert node._adapter.goals == [("robot_1", 3.0, 0.0, 0.0)]


def test_node_retry_noop_after_goal_accepted():
    node = _make_client()
    reg = _StringMsg(_json.dumps({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}}))
    node._on_registry(reg)
    node._adapter.on_results["robot_1"]("ACTIVE", "goal accepted")
    node._adapter.goals.clear()

    node._on_retry()

    assert node._adapter.goals == []

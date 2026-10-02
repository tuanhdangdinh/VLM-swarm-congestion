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
    should_cancel = driver.on_command("robot_1", "cmd-1")

    assert should_cancel is True
    # While suppressed, registry updates must not re-issue base navigation.
    assert driver.on_registry({"robot_1": {"task": "yield", "goal": [3.0, 0.0]}}) == []


def test_second_command_for_same_robot_does_not_request_cancel_again():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1", "cmd-1")

    assert driver.on_command("robot_1", "cmd-2") is False


def test_completed_status_resumes_base_navigation():
    driver = BaseMissionDriver()
    # yield's override goal equals the base goal, so the registry goal never
    # changes across the override — resumption cannot rely on a goal change.
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1", "cmd-1")

    issues = driver.on_status("robot_1", "cmd-1", "COMPLETED")

    assert issues == [("robot_1", (3.0, 0.0))]


def test_failed_status_also_resumes_base_navigation():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1", "cmd-1")

    assert driver.on_status("robot_1", "cmd-1", "FAILED") == [("robot_1", (3.0, 0.0))]


def test_republished_terminal_status_resumes_only_once():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1", "cmd-1")

    first = driver.on_status("robot_1", "cmd-1", "COMPLETED")
    # The command bus republishes each status ~3x; a second COMPLETED must not
    # re-issue another resume goal (which would thrash the robot's navigate).
    second = driver.on_status("robot_1", "cmd-1", "COMPLETED")

    assert first == [("robot_1", (3.0, 0.0))]
    assert second == []


def test_non_terminal_status_does_not_resume():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1", "cmd-1")

    assert driver.on_status("robot_1", "cmd-1", "ACTIVE") == []
    # Still suppressed after a non-terminal status.
    assert driver.on_registry({"robot_1": {"task": "yield", "goal": [3.0, 0.0]}}) == []


def test_owner_terminal_status_resumes():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1", "cmd-1")

    assert driver.on_status("robot_1", "cmd-1", "COMPLETED") == [
        ("robot_1", (3.0, 0.0))
    ]


def test_non_owner_terminal_status_keeps_suppression():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1", "cmd-1")

    # The command bus busy-rejects a second command (cmd-2) for a robot still
    # mid-maneuver under cmd-1. That FAILED must not unsuppress: re-issuing the
    # base goal would cancel-all the in-flight pull-off and re-enter the aisle.
    assert driver.on_status("robot_1", "cmd-2", "FAILED") == []
    # Still suppressed: registry updates issue nothing for robot_1.
    assert driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}}) == []
    # The true owner's terminal later resumes as normal.
    assert driver.on_status("robot_1", "cmd-1", "COMPLETED") == [
        ("robot_1", (3.0, 0.0))
    ]


# ---------------------------------------------------------------------------
# Step-7b ruling (i): race guard (successor command processed before the
# predecessor's own terminal status; /coordination/commands and
# /coordination/status carry no cross-topic ordering guarantee).
# ---------------------------------------------------------------------------


def test_v1_single_command_path_is_byte_identical():
    """Regression pin: a robot with only ever one command resumes exactly as before."""
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})

    assert driver.on_command("robot_1", "cmd-1") is True
    assert driver.on_status("robot_1", "cmd-1", "COMPLETED") == [
        ("robot_1", (3.0, 0.0))
    ]
    assert driver.drain_events() == []


def test_7a_race_successor_seen_before_predecessor_terminal_is_not_freed():
    """Reproduces 7a's exact race: a successor's on_command is processed
    before the predecessor's own terminal status. The predecessor's stale
    terminal must not resume base navigation; the successor becomes owner."""
    driver = BaseMissionDriver()
    driver.on_registry({"robot_4": {"task": "cross", "goal": [0.0, -1.75]}})
    driver.on_command("robot_4", "cross-cmd")

    # The release phase's successor command is seen (and, from this driver's
    # view, busy-rejected) BEFORE the cross phase's own terminal arrives.
    assert driver.on_command("robot_4", "release-cmd") is False

    # The predecessor's stale terminal must not resume the base mission.
    assert driver.on_status("robot_4", "cross-cmd", "COMPLETED") == []
    events = driver.drain_events()
    assert any("promoted_to=release-cmd" in e for e in events)

    # The robot stays suppressed under the successor; a registry update
    # issues nothing for it.
    assert driver.on_registry({"robot_4": {"task": "cross", "goal": [0.0, -1.75]}}) == []

    # Only the successor's own terminal frees the robot.
    assert driver.on_status("robot_4", "release-cmd", "COMPLETED") == [
        ("robot_4", (0.0, -1.75))
    ]


def test_race_successor_terminal_arrives_before_predecessor_terminal():
    """The other race direction: the successor's own terminal (a fast
    maneuver) is processed before the stale predecessor terminal ever
    arrives. The successor's COMPLETED must resume; the later, stale
    predecessor terminal must then be a no-op."""
    driver = BaseMissionDriver()
    driver.on_registry({"robot_4": {"task": "cross", "goal": [0.0, -1.75]}})
    driver.on_command("robot_4", "cross-cmd")
    driver.on_command("robot_4", "release-cmd")

    assert driver.on_status("robot_4", "release-cmd", "COMPLETED") == [
        ("robot_4", (0.0, -1.75))
    ]
    events = driver.drain_events()
    assert any("race guard: pending command completed" in e for e in events)

    # The stale predecessor terminal, arriving late, must not double-resume.
    assert driver.on_status("robot_4", "cross-cmd", "COMPLETED") == []


def test_three_command_phase_chain_recede_cross_release():
    """Models the full junction_clear phase chain (recede -> cross ->
    release) on one robot, with the SAME race at both phase boundaries."""
    driver = BaseMissionDriver()
    driver.on_registry({"robot_3": {"task": "cross", "goal": [0.0, 1.75]}})

    driver.on_command("robot_3", "recede-cmd")
    # cross's command is seen before recede's own terminal (race #1).
    driver.on_command("robot_3", "cross-cmd")
    assert driver.on_status("robot_3", "recede-cmd", "COMPLETED") == []

    # release's command is seen before cross's own terminal (race #2).
    driver.on_command("robot_3", "release-cmd")
    assert driver.on_status("robot_3", "cross-cmd", "COMPLETED") == []

    # Only release's own terminal frees the robot, at the end of the chain.
    assert driver.on_status("robot_3", "release-cmd", "COMPLETED") == [
        ("robot_3", (0.0, 1.75))
    ]


def test_command_terminal_seen_before_its_own_on_command_is_not_stranded():
    """Advisor-review regression pin: a command's terminal status can arrive
    (and be seen as unmatched) BEFORE this driver's on_command for that same
    command_id ever does -- no cross-topic ordering guarantee. If that
    command_id were then queued as pending on its (late) on_command, the
    owner's later terminal would promote it to owner -- but it already sent
    its one-and-only terminal and will never send another, stranding the
    robot suppressed forever. It must be discarded instead."""
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1", "cmd-1")

    # cmd-2's busy-reject FAILED arrives before cmd-2's own on_command.
    assert driver.on_status("robot_1", "cmd-2", "FAILED") == []
    # cmd-2's on_command arrives late; it must be discarded, not pending.
    assert driver.on_command("robot_1", "cmd-2") is False

    # The true owner's terminal must resume normally -- not get stuck
    # waiting for cmd-2 (which will never send another terminal).
    assert driver.on_status("robot_1", "cmd-1", "COMPLETED") == [
        ("robot_1", (3.0, 0.0))
    ]


def test_redelivered_on_command_for_an_already_resolved_pending_is_discarded():
    """The FAILED-pending case's own redelivery: once a pending command's
    own terminal (FAILED, never-took-ownership) has been consumed, a
    redelivery of its on_command (DDS retry) must not re-queue it either."""
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1", "cmd-1")
    driver.on_command("robot_1", "cmd-2")
    assert driver.on_status("robot_1", "cmd-2", "FAILED") == []

    # Redelivery of cmd-2's on_command must be discarded, not re-pending'd.
    assert driver.on_command("robot_1", "cmd-2") is False
    assert driver.on_status("robot_1", "cmd-1", "COMPLETED") == [
        ("robot_1", (3.0, 0.0))
    ]


def test_genuine_busy_reject_terminal_still_does_not_free_the_owner():
    """Regression pin for the EXISTING busy-reject contract: a command that
    never even reached on_command (command_bus_node's own busy-reject,
    which the client observes only as a FAILED status) must not free the
    robot, same as before this ruling's change."""
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_command("robot_1", "cmd-1")

    assert driver.on_status("robot_1", "cmd-2", "FAILED") == []
    assert driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}}) == []
    assert driver.on_status("robot_1", "cmd-1", "COMPLETED") == [
        ("robot_1", (3.0, 0.0))
    ]


def test_initial_issue_skips_held_robot():
    driver = BaseMissionDriver()
    driver.on_holds({"robot_1"})

    issues = driver.on_registry(
        {
            "robot_1": {"task": "cross", "goal": [3.0, 0.0]},
            "robot_2": {"task": "cross", "goal": [-3.0, 0.0]},
        }
    )

    assert issues == [("robot_2", (-3.0, 0.0))]


def test_retry_skips_held_robot():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    # robot_1 is latched under a safety stop; the safety monitor cancelled its
    # goal so it is unaccepted and would normally be re-issued on retry.
    driver.on_holds({"robot_1"})

    assert driver.retry() == []


def test_release_from_hold_reissues_on_next_retry():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}})
    driver.on_holds({"robot_1"})
    assert driver.retry() == []

    # Released from hold: no special resume path, the normal 2s retry tick
    # picks it up like any other unaccepted goal.
    driver.on_holds(set())

    assert driver.retry() == [("robot_1", (3.0, 0.0))]


def test_non_suppressed_robot_keeps_navigating_during_other_robots_override():
    driver = BaseMissionDriver()
    driver.on_registry(
        {
            "robot_1": {"task": "cross", "goal": [3.0, 0.0]},
            "robot_2": {"task": "cross", "goal": [-3.0, 0.0]},
        }
    )
    driver.on_command("robot_1", "cmd-1")

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
    def __init__(self, robot_id: str, command_id: str = "cmd-1") -> None:
        self.robot_id = robot_id
        self.command_id = command_id


class _StatusMsg:
    def __init__(self, robot_id: str, status: str, command_id: str = "cmd-1") -> None:
        self.robot_id = robot_id
        self.status = status
        self.command_id = command_id


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


def test_node_forwards_holds_to_driver():
    node = _make_client()
    node._on_registry(
        _StringMsg(_json.dumps({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}}))
    )
    node._adapter.goals.clear()

    node._on_holds(_StringMsg(_json.dumps({"held": ["robot_1"]})))
    node._on_retry()

    assert node._adapter.goals == []


def test_node_retry_noop_after_goal_accepted():
    node = _make_client()
    reg = _StringMsg(_json.dumps({"robot_1": {"task": "cross", "goal": [3.0, 0.0]}}))
    node._on_registry(reg)
    node._adapter.on_results["robot_1"]("ACTIVE", "goal accepted")
    node._adapter.goals.clear()

    node._on_retry()

    assert node._adapter.goals == []


def test_start_pending_robot_is_not_driven():
    driver = BaseMissionDriver()

    issues = driver.on_registry(
        {
            "robot_1": {"task": "cross", "goal": [2.5, 0.0]},
            "robot_3": {"task": "cross", "goal": [1.85, 0.0], "start_pending": True},
        }
    )

    assert issues == [("robot_1", (2.5, 0.0))]
    assert driver.retry() == [("robot_1", (2.5, 0.0))]


def test_released_robot_is_driven_on_the_next_registry():
    driver = BaseMissionDriver()
    driver.on_registry(
        {"robot_3": {"task": "cross", "goal": [1.85, 0.0], "start_pending": True}}
    )

    issues = driver.on_registry({"robot_3": {"task": "cross", "goal": [1.85, 0.0]}})

    assert issues == [("robot_3", (1.85, 0.0))]


def test_released_robot_under_a_command_resumes_only_on_the_command_terminal():
    driver = BaseMissionDriver()
    driver.on_registry(
        {"robot_3": {"task": "cross", "goal": [1.85, 0.0], "start_pending": True}}
    )
    assert driver.on_command("robot_3", "c1") is True

    assert driver.on_registry({"robot_3": {"task": "cross", "goal": [1.85, 0.0]}}) == []
    assert driver.on_status("robot_3", "c1", "COMPLETED") == [("robot_3", (1.85, 0.0))]

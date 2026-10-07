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
from types import SimpleNamespace

from swarm_execution.coordination_client_node import CoordinationClientNode


class _StringMsg:
    def __init__(self, data: str) -> None:
        self.data = data


class _CmdMsg:
    def __init__(self, robot_id: str, command_id: str = "cmd-1", action: str = "") -> None:
        self.robot_id = robot_id
        self.command_id = command_id
        self.action = action


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

    def cancel_own_goal(self, robot_id):
        self.own_cancels.append(robot_id)
        return True

    def stop_controller(self, robot_id):
        self.controller_stops.append(robot_id)


class _FakeTimer:
    def __init__(self, period, callback) -> None:
        self.period = period
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


def _make_client(handoff_guard: bool = True):
    node = CoordinationClientNode.__new__(CoordinationClientNode)
    node._adapter = _FakeAdapter()
    node._adapter.own_cancels = []
    node._adapter.controller_stops = []
    node._handoff_guard = handoff_guard
    node._command_actions = {}
    node._driver = BaseMissionDriver(handoff_guard=handoff_guard)
    node.infos = []
    node.timers = []

    class _Logger:
        def info(self, msg):
            node.infos.append(str(msg))

        def warning(self, _msg):
            pass

    class _Clock:
        def now(self):
            return SimpleNamespace(nanoseconds=104.267e9)

    def _create_timer(period, callback):
        timer = _FakeTimer(period, callback)
        node.timers.append(timer)
        return timer

    node.get_logger = lambda: _Logger()
    node.get_clock = lambda: _Clock()
    node.create_timer = _create_timer
    node.destroy_timer = lambda _timer: None
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


# ---------------------------------------------------------------------------
# Hand-off race guard (IB10 remedy validation run m4,
# docs/reports/2026-10-08-ib10-remedy-validation.md section 5). The cross phase
# completes for every robot within ~10 ms; the client, lagging the command bus,
# processes robot_2's cross terminal AFTER the bus already dispatched robot_1's
# release yield but BEFORE the client itself has seen that command.
# ---------------------------------------------------------------------------

_IB10_REGISTRY = {
    "robot_1": {"task": "cross_intersection", "goal": [1.75, 0.0]},
    "robot_2": {"task": "cross_intersection", "goal": [-1.75, 0.0]},
    "robot_3": {"task": "cross_intersection", "goal": [0.0, 1.75]},
    "robot_4": {"task": "cross_intersection", "goal": [0.0, -1.75]},
}


def _driver_in_cross_phase(handoff_guard: bool = True) -> BaseMissionDriver:
    driver = BaseMissionDriver(handoff_guard=handoff_guard)
    driver.on_registry(_IB10_REGISTRY)
    for robot_id, goal in _IB10_REGISTRY.items():
        driver.on_goal_accepted(robot_id, tuple(goal["goal"]))
    for robot_id in _IB10_REGISTRY:
        driver.on_command(robot_id, "cross")
    return driver


def test_other_robot_terminal_does_not_resend_unaccepted_robot():
    driver = _driver_in_cross_phase()
    assert driver.on_status("robot_1", "cross", "COMPLETED") == [("robot_1", (1.75, 0.0))]
    driver.drain_events()

    # robot_1's resume goal is not accepted yet and its release yield is
    # already ACTIVE on the bus: robot_2's terminal must not re-send it.
    assert driver.on_status("robot_2", "cross", "COMPLETED") == [("robot_2", (-1.75, 0.0))]

    events = driver.drain_events()
    assert any(
        "handoff guard: cross-robot resume suppressed" in e
        and "trigger_robot=robot_2" in e
        and "suppressed=robot_1" in e
        for e in events
    )


def test_guard_off_restores_cross_robot_resume_fan_out():
    driver = _driver_in_cross_phase(handoff_guard=False)
    driver.on_status("robot_1", "cross", "COMPLETED")

    assert driver.on_status("robot_2", "cross", "COMPLETED") == [
        ("robot_1", (1.75, 0.0)),
        ("robot_2", (-1.75, 0.0)),
    ]
    assert driver.drain_events() == []


def test_suppressed_robot_is_still_resumed_by_retry_after_its_terminal():
    driver = _driver_in_cross_phase()
    driver.on_status("robot_1", "cross", "COMPLETED")
    driver.on_status("robot_2", "cross", "COMPLETED")

    # robot_1 is not lost: an unaccepted, unowned goal is still retried.
    assert ("robot_1", (1.75, 0.0)) in driver.retry()


def test_late_accept_under_command_is_not_recorded():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [1.75, 0.0]}})
    # The base goal is in flight when the release command takes the robot.
    driver.on_command("robot_1", "release")

    assert driver.on_goal_accepted("robot_1", (1.75, 0.0)) is False
    assert any(
        "handoff guard: late base goal accepted under command" in e
        and "robot=robot_1" in e
        and "owner=release" in e
        for e in driver.drain_events()
    )
    # The owner's terminal still re-issues the base goal immediately.
    assert driver.on_status("robot_1", "release", "COMPLETED") == [("robot_1", (1.75, 0.0))]


def test_guard_off_late_accept_is_recorded_as_before():
    driver = BaseMissionDriver(handoff_guard=False)
    driver.on_registry({"robot_1": {"task": "cross", "goal": [1.75, 0.0]}})
    driver.on_command("robot_1", "release")

    assert driver.on_goal_accepted("robot_1", (1.75, 0.0)) is True
    # Pre-guard behaviour: the recorded acceptance masks the terminal resume.
    assert driver.on_status("robot_1", "release", "COMPLETED") == []


def test_accept_without_command_is_recorded():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [1.75, 0.0]}})

    assert driver.on_goal_accepted("robot_1", (1.75, 0.0)) is True
    assert driver.retry() == []


def test_holds_command_tracks_owner_and_successor():
    driver = BaseMissionDriver()
    driver.on_registry({"robot_1": {"task": "cross", "goal": [1.75, 0.0]}})
    driver.on_command("robot_1", "cross")
    assert driver.holds_command("robot_1", "cross") is True

    driver.on_command("robot_1", "release")
    assert driver.holds_command("robot_1", "cross") is False

    driver.on_status("robot_1", "cross", "COMPLETED")
    assert driver.holds_command("robot_1", "release") is True

    driver.on_status("robot_1", "release", "COMPLETED")
    assert driver.holds_command("robot_1", "release") is False
    assert driver.command_owner("robot_1") is None


def test_7b_race_guard_unchanged_under_handoff_guard():
    """The step-7b successor-before-terminal guard still promotes, never resumes."""
    driver = BaseMissionDriver(handoff_guard=True)
    driver.on_registry({"robot_1": {"task": "cross", "goal": [1.75, 0.0]}})
    driver.on_command("robot_1", "cross")
    driver.on_command("robot_1", "release")

    assert driver.on_status("robot_1", "cross", "COMPLETED") == []
    assert driver.command_owner("robot_1") == "release"
    assert driver.on_status("robot_1", "release", "COMPLETED") == [("robot_1", (1.75, 0.0))]


def _client_in_cross_phase(handoff_guard: bool = True):
    node = _make_client(handoff_guard=handoff_guard)
    node._on_registry(_StringMsg(_json.dumps(_IB10_REGISTRY)))
    for robot_id in _IB10_REGISTRY:
        node._adapter.on_results[robot_id]("ACTIVE", "goal accepted")
    node._on_command(_CmdMsg("robot_1", "cross", "yield"))
    for robot_id in ("robot_2", "robot_3", "robot_4"):
        node._on_command(_CmdMsg(robot_id, "cross", "temporary_wait"))
    node._adapter.goals.clear()
    node._adapter.cancels.clear()
    node._adapter.controller_stops.clear()
    node.timers.clear()
    node.infos.clear()
    return node


def test_m4_sequence_release_command_blocks_resend_and_stops_controller():
    node = _client_in_cross_phase()

    # sim 104.17: robot_1's cross yield completes -> resume #1 (legitimate).
    node._on_status(_StatusMsg("robot_1", "COMPLETED", "cross"))
    assert node._adapter.goals == [("robot_1", 1.75, 0.0, 0.0)]
    resume_1_result = node._adapter.on_results["robot_1"]

    # +0.36 s: robot_2's cross terminal; robot_1's release is already ACTIVE
    # on the bus but unseen here. Pre-guard this re-sent robot_1 (resume #2).
    node._on_status(_StatusMsg("robot_2", "COMPLETED", "cross"))
    assert node._adapter.goals == [("robot_1", 1.75, 0.0, 0.0), ("robot_2", -1.75, 0.0, 0.0)]

    # The release yield reaches the client: cancel the base goal and stop the
    # controller so an orphaned FollowPath cannot drive robot_1.
    node._on_command(_CmdMsg("robot_1", "release", "yield"))
    assert node._adapter.cancels == ["robot_1"]
    assert node._adapter.controller_stops == ["robot_1"]
    assert sorted(t.period for t in node.timers) == [0.5, 1.5]
    assert any(
        "handoff guard: controller stop robot=robot_1 command=release action=yield "
        "reason=handover" in line
        for line in node.infos
    )

    # Resume #1's goal is accepted only now: cancel it, stop the controller.
    resume_1_result("ACTIVE", "goal accepted")
    assert node._adapter.own_cancels == ["robot_1"]
    assert node._adapter.controller_stops == ["robot_1", "robot_1"]
    assert any("late base goal accepted under command robot=robot_1" in l for l in node.infos)
    assert any("reason=late_accept" in line for line in node.infos)

    # No base goal reaches robot_1 while the release yield owns it.
    node._on_retry()
    assert node._adapter.goals.count(("robot_1", 1.75, 0.0, 0.0)) == 1


def test_controller_followups_fire_only_while_command_owns_robot():
    node = _client_in_cross_phase()
    node._on_status(_StatusMsg("robot_1", "COMPLETED", "cross"))
    node._on_command(_CmdMsg("robot_1", "release", "yield"))
    first, second = sorted(node.timers, key=lambda t: t.period)

    first.callback()
    assert node._adapter.controller_stops == ["robot_1", "robot_1"]
    assert first.cancelled

    node._on_status(_StatusMsg("robot_1", "COMPLETED", "release"))
    second.callback()
    assert node._adapter.controller_stops == ["robot_1", "robot_1"]


def test_nav2_driven_command_does_not_stop_controller():
    node = _client_in_cross_phase()
    node._on_status(_StatusMsg("robot_1", "COMPLETED", "cross"))

    node._on_command(_CmdMsg("robot_1", "reroute-1", "reroute"))

    assert node._adapter.cancels == ["robot_1"]
    assert node._adapter.controller_stops == []
    assert node.timers == []


def test_guard_off_client_resends_and_never_stops_controller():
    node = _client_in_cross_phase(handoff_guard=False)
    node._on_status(_StatusMsg("robot_1", "COMPLETED", "cross"))
    resume_1_result = node._adapter.on_results["robot_1"]

    node._on_status(_StatusMsg("robot_2", "COMPLETED", "cross"))
    assert node._adapter.goals.count(("robot_1", 1.75, 0.0, 0.0)) == 2

    node._on_command(_CmdMsg("robot_1", "release", "yield"))
    resume_1_result("ACTIVE", "goal accepted")
    assert node._adapter.controller_stops == []
    assert node._adapter.own_cancels == []

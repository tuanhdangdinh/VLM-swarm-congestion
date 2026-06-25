"""Unit tests for Nav2Adapter using a fake ActionClient (no real ROS2 needed).

Tests cover send_goal, send_waypoints, and cancel behaviors with synchronous
fakes replacing rclpy action infrastructure.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from swarm_execution.nav2_adapter import Nav2Adapter


# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------


class _FakeGoalHandle:
    """Minimal stand-in for a rclpy goal handle."""

    def __init__(self) -> None:
        self.accepted = True
        self._cancel = MagicMock()

    def cancel_goal_async(self) -> None:
        self._cancel()


class _FakeFuture:
    """Future whose add_done_callback fires synchronously."""

    def __init__(self, handle: _FakeGoalHandle) -> None:
        self._handle = handle

    def result(self) -> _FakeGoalHandle:
        return self._handle

    def add_done_callback(self, cb) -> None:
        cb(self)


class _FakeActionClient:
    """Minimal stand-in for rclpy ActionClient."""

    def __init__(self) -> None:
        self.sent_goals: list = []
        self._handle = _FakeGoalHandle()

    def send_goal_async(self, goal_msg) -> _FakeFuture:
        self.sent_goals.append(goal_msg)
        return _FakeFuture(self._handle)

    def wait_for_server(self, timeout_sec=None) -> bool:
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter() -> Nav2Adapter:
    """Nav2Adapter with __init__ bypassed and fake action-client factory."""
    a = Nav2Adapter.__new__(Nav2Adapter)
    a._goal_clients: dict = {}
    a._waypoint_clients: dict = {}
    a._active_goals: dict = {}
    a._make_client = lambda robot_id, action_name: _FakeActionClient()
    return a


# ---------------------------------------------------------------------------
# Tests: send_goal
# ---------------------------------------------------------------------------


def test_send_goal_creates_client_for_robot(adapter: Nav2Adapter) -> None:
    """send_goal registers a client entry for the target robot."""
    adapter.send_goal("robot_1", x=1.0, y=2.0, yaw=0.0)
    assert "robot_1" in adapter._goal_clients


def test_send_goal_reuses_client_on_second_call(adapter: Nav2Adapter) -> None:
    """Second send_goal to the same robot reuses the existing ActionClient."""
    adapter.send_goal("robot_1", x=1.0, y=2.0, yaw=0.0)
    first_client = adapter._goal_clients["robot_1"]

    adapter.send_goal("robot_1", x=3.0, y=4.0, yaw=0.5)
    second_client = adapter._goal_clients["robot_1"]

    assert first_client is second_client


def test_send_goal_preempts_active_goal(adapter: Nav2Adapter) -> None:
    """send_goal cancels any previously active goal for that robot."""
    adapter.send_goal("robot_1", x=1.0, y=2.0, yaw=0.0)
    first_handle = adapter._active_goals["robot_1"]

    adapter.send_goal("robot_1", x=3.0, y=4.0, yaw=0.0)

    first_handle._cancel.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: send_waypoints
# ---------------------------------------------------------------------------


def test_send_waypoints_creates_waypoint_client(adapter: Nav2Adapter) -> None:
    """send_waypoints registers a waypoint-client entry for the target robot."""
    adapter.send_waypoints("robot_1", waypoints=[(1.0, 2.0), (3.0, 4.0)])
    assert "robot_1" in adapter._waypoint_clients


def test_send_waypoints_builds_correct_pose_count(adapter: Nav2Adapter) -> None:
    """A 3-waypoint list produces a goal with exactly 3 pose entries."""
    waypoints = [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0)]
    adapter.send_waypoints("robot_1", waypoints=waypoints)

    client: _FakeActionClient = adapter._waypoint_clients["robot_1"]
    goal_msg = client.sent_goals[-1]
    assert len(goal_msg.poses) == 3


# ---------------------------------------------------------------------------
# Tests: cancel
# ---------------------------------------------------------------------------


def test_cancel_calls_cancel_goal_async(adapter: Nav2Adapter) -> None:
    """cancel invokes cancel_goal_async on the robot's active goal handle."""
    adapter.send_goal("robot_1", x=1.0, y=2.0, yaw=0.0)
    handle = adapter._active_goals["robot_1"]

    adapter.cancel("robot_1")

    handle._cancel.assert_called_once()


def test_cancel_unknown_robot_is_noop(adapter: Nav2Adapter) -> None:
    """cancel for a robot with no active goal must not raise."""
    adapter.cancel("robot_9")  # should not raise

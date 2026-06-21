from unittest.mock import MagicMock

import pytest
from swarm_execution.nav2_adapter import Nav2Adapter


class _FakeGoalHandle:
    def __init__(self):
        self.accepted = True
        self.cancel_goal_async = MagicMock()


class _FakeActionClient:
    def __init__(self):
        self.sent_goals = []
        self._handle = _FakeGoalHandle()

    def send_goal_async(self, goal_msg):
        self.sent_goals.append(goal_msg)
        future = MagicMock()
        future.result.return_value = self._handle
        return future

    def wait_for_server(self, timeout_sec=None):
        return True


@pytest.fixture
def adapter():
    a = Nav2Adapter.__new__(Nav2Adapter)  # bypass rclpy Node.__init__ in this offline test
    a._clients = {}
    a._active_goals = {}
    a._make_client = lambda robot_id, action_name: _FakeActionClient()
    return a


def test_send_goal_creates_one_client_per_robot(adapter):
    adapter.send_goal("robot_1", x=1.0, y=2.0, yaw=0.0)
    assert "robot_1" in adapter._clients


def test_send_goal_preempts_previous_goal(adapter):
    adapter.send_goal("robot_1", x=1.0, y=2.0, yaw=0.0)
    first_handle = adapter._active_goals["robot_1"]
    adapter.send_goal("robot_1", x=3.0, y=4.0, yaw=0.0)
    first_handle.cancel_goal_async.assert_called_once()


def test_cancel_calls_cancel_goal_async(adapter):
    adapter.send_goal("robot_1", x=1.0, y=2.0, yaw=0.0)
    handle = adapter._active_goals["robot_1"]
    adapter.cancel("robot_1")
    handle.cancel_goal_async.assert_called_once()


def test_cancel_unknown_robot_is_a_noop(adapter):
    adapter.cancel("robot_9")  # must not raise

"""Unit tests for Nav2Adapter using a fake ActionClient (no real ROS2 needed).

Tests cover send_goal, send_waypoints, and cancel behaviors with synchronous
fakes replacing rclpy action infrastructure.
"""
from __future__ import annotations

import math
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import swarm_execution.nav2_adapter as nav2_adapter
from swarm_execution.nav2_adapter import Nav2Adapter

# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------


class _FakeGoalHandle:
    """Minimal stand-in for a rclpy goal handle."""

    def __init__(self) -> None:
        self.accepted = True
        self._cancel = MagicMock()
        self._result_future = _DeferredFuture(SimpleNamespace(status=4))

    def cancel_goal_async(self) -> None:
        self._cancel()

    def get_result_async(self):
        return self._result_future


class _FakeFuture:
    """Future whose add_done_callback fires synchronously."""

    def __init__(self, handle: _FakeGoalHandle) -> None:
        self._handle = handle

    def result(self) -> _FakeGoalHandle:
        return self._handle

    def add_done_callback(self, cb) -> None:
        cb(self)


class _DeferredFuture:
    """Future whose callback fires only when trigger() is called."""

    def __init__(self, result) -> None:
        self._result = result
        self._callbacks = []

    def result(self):
        return self._result

    def add_done_callback(self, cb) -> None:
        self._callbacks.append(cb)

    def trigger(self) -> None:
        for cb in list(self._callbacks):
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


class _FakePublisher:
    def __init__(self) -> None:
        self.messages: list = []

    def publish(self, msg) -> None:
        self.messages.append(msg)


class _FakeSubscription:
    def __init__(self, callback) -> None:
        self.callback = callback
        self.destroyed = False


class _FakeTimer:
    def __init__(self, callback) -> None:
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def tick(self) -> None:
        if not self.cancelled:
            self.callback()


class _FakeClock:
    def __init__(self) -> None:
        self.seconds = 0.0

    def now(self):
        return SimpleNamespace(nanoseconds=self.seconds * 1e9)

    def advance(self, delta_sec: float) -> None:
        self.seconds += delta_sec


class _FakeNode:
    def __init__(self) -> None:
        self.clock = _FakeClock()
        self.publishers: dict = {}
        self.subscriptions: list[_FakeSubscription] = []
        self.timers: list[_FakeTimer] = []
        self.destroyed_subs: list = []

    def create_publisher(self, msg_type, topic, qos):
        pub = _FakePublisher()
        self.publishers[topic] = pub
        return pub

    def create_subscription(self, msg_type, topic, callback, qos):
        sub = _FakeSubscription(callback)
        self.subscriptions.append(sub)
        return sub

    def create_timer(self, period, callback):
        timer = _FakeTimer(callback)
        self.timers.append(timer)
        return timer

    def destroy_subscription(self, sub) -> None:
        sub.destroyed = True
        self.destroyed_subs.append(sub)

    def get_clock(self):
        return self.clock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter() -> Nav2Adapter:
    """Nav2Adapter built on a fake node, with a fake action-client factory."""
    a = Nav2Adapter(_FakeNode())
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


def test_send_goal_sets_map_frame_and_requested_pose(adapter: Nav2Adapter) -> None:
    """The sent goal pose uses the map frame and the requested x/y/yaw."""
    adapter.send_goal("robot_1", x=1.25, y=-0.5, yaw=0.5)

    client: _FakeActionClient = adapter._goal_clients["robot_1"]
    goal_msg = client.sent_goals[-1]

    assert goal_msg.pose.header.frame_id == "map"
    assert goal_msg.pose.pose.position.x == 1.25
    assert goal_msg.pose.pose.position.y == -0.5
    assert (
        goal_msg.pose.pose.orientation.z,
        goal_msg.pose.pose.orientation.w,
    ) == pytest.approx((math.sin(0.25), math.cos(0.25)))


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


def test_send_waypoints_sets_map_frame_and_requested_positions(adapter: Nav2Adapter) -> None:
    """Each sent waypoint pose uses the map frame and its requested x/y."""
    waypoints = [(1.0, 0.0), (2.0, 0.5)]
    adapter.send_waypoints("robot_1", waypoints=waypoints)

    client: _FakeActionClient = adapter._waypoint_clients["robot_1"]
    goal_msg = client.sent_goals[-1]

    for pose, (x, y) in zip(goal_msg.poses, waypoints, strict=True):
        assert pose.header.frame_id == "map"
        assert pose.pose.position.x == x
        assert pose.pose.position.y == y


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


def test_send_goal_reports_active_then_completed_on_action_result(adapter: Nav2Adapter) -> None:
    statuses = []

    adapter.send_goal(
        "robot_1",
        x=1.0,
        y=2.0,
        yaw=0.0,
        on_result=lambda status, detail: statuses.append((status, detail)),
    )

    assert statuses == [("ACTIVE", "goal accepted")]
    handle = adapter._active_goals["robot_1"]
    handle._result_future.trigger()
    assert statuses == [("ACTIVE", "goal accepted"), ("COMPLETED", "goal succeeded")]
    assert "robot_1" not in adapter._active_goals


def test_send_goal_reports_failed_on_aborted_action_result(adapter: Nav2Adapter) -> None:
    statuses = []

    adapter.send_goal(
        "robot_1",
        x=1.0,
        y=2.0,
        yaw=0.0,
        on_result=lambda status, detail: statuses.append((status, detail)),
    )
    handle = adapter._active_goals["robot_1"]
    handle._result_future._result.status = 6
    handle._result_future.trigger()

    assert statuses[-1] == ("FAILED", "goal ended with status=6")


def test_make_client_uses_parent_node_when_provided(monkeypatch) -> None:
    """ActionClient callbacks must live on the spun command bus node."""
    calls = []

    class FakeActionClient:
        def __init__(self, node, action_type, action_name):
            calls.append((node, action_type, action_name))

    parent_node = object()
    adapter = Nav2Adapter.__new__(Nav2Adapter)
    adapter._node = parent_node
    monkeypatch.setattr(nav2_adapter, "ActionClient", FakeActionClient)

    adapter._make_client("robot_1", "navigate_to_pose")

    assert calls == [(parent_node, nav2_adapter.NavigateToPose, "/robot_1/navigate_to_pose")]


# ---------------------------------------------------------------------------
# Tests: backup (closed-loop on odometry)
# ---------------------------------------------------------------------------
#
# Isaac Sim on the target VM runs well under real time (confirmed ~0.48x
# standalone, worse under the full node stack), so a wall-clock deadline
# stops the backup long before the robot has actually traveled distance_m.
# backup() now closes the loop on odometry displacement instead, with a
# generous wall-clock safety bound for a genuinely blocked robot. These tests
# use a small fake _node exposing create_publisher/create_subscription/
# create_timer/get_clock so the tick and odometry callbacks can be driven
# manually without a real ROS2 executor. The fakes themselves live in the
# "Fake infrastructure" section above, alongside the `adapter` fixture.


def _odom_at(x: float, y: float, yaw: float = 0.0):
    msg = nav2_adapter.Odometry()
    msg.pose.pose.position.x = x
    msg.pose.pose.position.y = y
    msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
    msg.pose.pose.orientation.w = math.cos(yaw / 2.0)
    return msg


@pytest.fixture
def backup_adapter() -> tuple[Nav2Adapter, _FakeNode]:
    node = _FakeNode()
    return Nav2Adapter(node), node


def test_backup_does_not_complete_before_target_distance_traveled(backup_adapter) -> None:
    adapter, node = backup_adapter
    statuses: list[tuple[str, str]] = []
    adapter.backup(
        "robot_1", distance_m=0.8, speed_mps=0.1,
        on_result=lambda s, d: statuses.append((s, d)),
    )
    assert statuses == [("ACTIVE", "backup started")]

    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]

    # Odometry reports only a small displacement (mirrors the sub-realtime
    # sim measured in production): well short of the 0.8 m target.
    odom_sub.callback(_odom_at(0.0, 0.0))
    node.clock.advance(0.05)
    odom_sub.callback(_odom_at(-0.03, 0.0))
    timer.tick()

    assert statuses == [("ACTIVE", "backup started")]  # no COMPLETED yet
    assert not timer.cancelled


def test_backup_completes_once_odometry_shows_target_distance(backup_adapter) -> None:
    adapter, node = backup_adapter
    statuses: list[tuple[str, str]] = []
    adapter.backup(
        "robot_1", distance_m=0.8, speed_mps=0.1,
        on_result=lambda s, d: statuses.append((s, d)),
    )
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]

    odom_sub.callback(_odom_at(0.0, 0.0))
    odom_sub.callback(_odom_at(-0.8, 0.0))  # reached the target distance
    timer.tick()

    assert statuses[-1][0] == "COMPLETED"
    assert timer.cancelled
    assert node.destroyed_subs == [odom_sub]


def test_backup_fails_on_safety_timeout_when_robot_stays_blocked(
    backup_adapter, monkeypatch
) -> None:
    adapter, node = backup_adapter
    wall = {"now": 100.0}
    monkeypatch.setattr(nav2_adapter.time, "monotonic", lambda: wall["now"])
    statuses: list[tuple[str, str]] = []
    adapter.backup(
        "robot_1", distance_m=0.8, speed_mps=0.1,
        on_result=lambda s, d: statuses.append((s, d)),
    )
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]

    # Robot never moves (e.g. physically blocked) — odometry stays flat.
    odom_sub.callback(_odom_at(0.0, 0.0))
    wall["now"] += 1000.0  # well past the safety deadline
    timer.tick()

    assert statuses[-1][0] == "FAILED"
    assert "timed out" in statuses[-1][1]
    assert timer.cancelled


def test_backup_deadline_fires_when_sim_clock_is_frozen(
    backup_adapter, monkeypatch
) -> None:
    """A hung sim freezes /clock; the OS-monotonic deadline must still fire."""
    adapter, node = backup_adapter
    wall = {"now": 100.0}
    monkeypatch.setattr(nav2_adapter.time, "monotonic", lambda: wall["now"])
    statuses: list[tuple[str, str]] = []
    adapter.backup(
        "robot_1", distance_m=0.8, speed_mps=0.1,
        on_result=lambda s, d: statuses.append((s, d)),
    )
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]

    odom_sub.callback(_odom_at(0.0, 0.0))
    # Sim clock never advances (node.clock.seconds stays 0.0) — only wall
    # time moves, exactly the hung-sim scenario the deadline exists for.
    wall["now"] += 1000.0
    timer.tick()

    assert statuses[-1][0] == "FAILED"
    assert "timed out" in statuses[-1][1]


def test_backup_deadline_ignores_sim_clock_jump(backup_adapter, monkeypatch) -> None:
    """A sim-clock jump alone must not expire the OS-monotonic deadline."""
    adapter, node = backup_adapter
    wall = {"now": 100.0}
    monkeypatch.setattr(nav2_adapter.time, "monotonic", lambda: wall["now"])
    statuses: list[tuple[str, str]] = []
    adapter.backup(
        "robot_1", distance_m=0.8, speed_mps=0.1,
        on_result=lambda s, d: statuses.append((s, d)),
    )
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]

    odom_sub.callback(_odom_at(0.0, 0.0))
    node.clock.advance(1000.0)  # sim clock jumps; wall time does not move
    timer.tick()

    assert statuses == [("ACTIVE", "backup started")]
    assert not timer.cancelled


def test_backup_cleans_up_odom_subscription_on_cancel(backup_adapter) -> None:
    adapter, node = backup_adapter
    adapter.backup("robot_1", distance_m=0.8, speed_mps=0.1)
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]

    adapter.cancel("robot_1")

    assert timer.cancelled
    assert odom_sub in node.destroyed_subs
    assert "robot_1" not in adapter._backup_odom_subs


def _drive_sidestep(node, odom_sub, timer, yaw_seq):
    """Feed odometry through the sidestep phases: turn, drive, turn back.

    `yaw_seq` maps published-command inspection to odometry responses so the
    test drives the real closed-loop state machine, not a reimplementation.
    """
    # Phase 1: report unrotated, then rotated yaw.
    odom_sub.callback(_odom_at(0.0, 0.0, yaw=0.0))
    timer.tick()
    odom_sub.callback(_odom_at(0.0, 0.0, yaw=yaw_seq["turned"]))
    timer.tick()
    # Phase 2: displacement grows to the lateral target.
    odom_sub.callback(_odom_at(0.0, 0.35, yaw=yaw_seq["turned"]))
    timer.tick()
    # Phase 3: yaw restored.
    odom_sub.callback(_odom_at(0.0, 0.35, yaw=0.0))
    timer.tick()


def test_sidestep_completes_after_turn_drive_turn(backup_adapter) -> None:
    adapter, node = backup_adapter
    statuses: list[tuple[str, str]] = []
    adapter.sidestep(
        "robot_1", lateral_m=0.35,
        on_result=lambda s, d: statuses.append((s, d)),
    )
    assert statuses == [("ACTIVE", "side step started")]
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]

    _drive_sidestep(node, odom_sub, timer, {"turned": math.pi / 2})

    assert statuses[-1][0] == "COMPLETED"
    assert "side step complete" in statuses[-1][1]
    # Terminal tick stops motion with a zero twist.
    pub = node.publishers["/robot_1/cmd_vel"]
    last = pub.messages[-1]
    assert last.linear.x == 0.0 and last.angular.z == 0.0


def test_sidestep_turns_left_for_positive_lateral(backup_adapter) -> None:
    adapter, node = backup_adapter
    adapter.sidestep("robot_1", lateral_m=0.35)
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]

    odom_sub.callback(_odom_at(0.0, 0.0, yaw=0.0))
    timer.tick()

    pub = node.publishers["/robot_1/cmd_vel"]
    assert pub.messages[-1].angular.z > 0.0
    assert pub.messages[-1].linear.x == 0.0


def test_sidestep_turns_right_for_negative_lateral(backup_adapter) -> None:
    adapter, node = backup_adapter
    adapter.sidestep("robot_1", lateral_m=-0.35)
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]

    odom_sub.callback(_odom_at(0.0, 0.0, yaw=0.0))
    timer.tick()

    pub = node.publishers["/robot_1/cmd_vel"]
    assert pub.messages[-1].angular.z < 0.0


def test_sidestep_drives_forward_only_after_turn_complete(backup_adapter) -> None:
    adapter, node = backup_adapter
    adapter.sidestep("robot_1", lateral_m=0.35)
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]
    pub = node.publishers["/robot_1/cmd_vel"]

    odom_sub.callback(_odom_at(0.0, 0.0, yaw=0.0))
    timer.tick()
    assert pub.messages[-1].linear.x == 0.0

    odom_sub.callback(_odom_at(0.0, 0.0, yaw=math.pi / 2))
    timer.tick()
    assert pub.messages[-1].linear.x > 0.0
    assert pub.messages[-1].angular.z == 0.0


def test_sidestep_times_out_on_monotonic_deadline_when_blocked(
    backup_adapter, monkeypatch
) -> None:
    adapter, node = backup_adapter
    wall = {"now": 100.0}
    monkeypatch.setattr(nav2_adapter.time, "monotonic", lambda: wall["now"])
    statuses: list[tuple[str, str]] = []
    adapter.sidestep(
        "robot_1", lateral_m=0.35,
        on_result=lambda s, d: statuses.append((s, d)),
    )
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]

    odom_sub.callback(_odom_at(0.0, 0.0, yaw=0.0))
    wall["now"] += 1000.0
    timer.tick()

    assert statuses[-1][0] == "FAILED"
    assert "timed out" in statuses[-1][1]


def test_sidestep_zero_lateral_completes_immediately(backup_adapter) -> None:
    adapter, node = backup_adapter
    statuses: list[tuple[str, str]] = []
    adapter.sidestep(
        "robot_1", lateral_m=0.0,
        on_result=lambda s, d: statuses.append((s, d)),
    )
    assert statuses[-1][0] == "COMPLETED"


def test_drive_heading_turns_to_absolute_yaw_then_drives(backup_adapter) -> None:
    adapter, node = backup_adapter
    statuses: list[tuple[str, str]] = []
    adapter.drive_heading(
        "robot_2", target_yaw_rad=0.0, distance_m=2.4,
        on_result=lambda s, d: statuses.append((s, d)),
    )
    assert statuses == [("ACTIVE", "escort started")]
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]
    pub = node.publishers["/robot_2/cmd_vel"]

    # Facing 30 deg off target: must rotate (negative z toward 0), not drive.
    odom_sub.callback(_odom_at(0.0, 0.0, yaw=math.radians(30)))
    timer.tick()
    assert pub.messages[-1].linear.x == 0.0
    assert pub.messages[-1].angular.z < 0.0

    # Aligned: drives forward.
    odom_sub.callback(_odom_at(0.0, 0.0, yaw=0.0))
    timer.tick()
    assert pub.messages[-1].linear.x > 0.0
    assert pub.messages[-1].angular.z == 0.0

    # Distance covered: terminal COMPLETED with zero twist.
    odom_sub.callback(_odom_at(2.4, 0.0, yaw=0.0))
    timer.tick()
    assert statuses[-1][0] == "COMPLETED"
    assert "escort complete" in statuses[-1][1]
    assert pub.messages[-1].linear.x == 0.0


def test_drive_heading_times_out_on_monotonic_deadline(
    backup_adapter, monkeypatch
) -> None:
    adapter, node = backup_adapter
    wall = {"now": 50.0}
    monkeypatch.setattr(nav2_adapter.time, "monotonic", lambda: wall["now"])
    statuses: list[tuple[str, str]] = []
    adapter.drive_heading(
        "robot_2", target_yaw_rad=0.0, distance_m=2.4,
        on_result=lambda s, d: statuses.append((s, d)),
    )
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]
    odom_sub.callback(_odom_at(0.0, 0.0, yaw=0.0))
    wall["now"] += 10000.0
    timer.tick()
    assert statuses[-1][0] == "FAILED"
    assert "timed out" in statuses[-1][1]


def test_drive_heading_steers_back_toward_lane_center(backup_adapter) -> None:
    # The escort must servo to odom y=0 (the lane centerline both robots
    # spawn on), not drive an open-loop straight line: heading-tolerance
    # drift over 2.4m pushed the passer into the parked yielder (H3 run 9,
    # physical contact, both robots wedged).
    adapter, node = backup_adapter
    adapter.drive_heading("robot_2", target_yaw_rad=0.0, distance_m=2.4)
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]
    pub = node.publishers["/robot_2/cmd_vel"]

    # Aligned but displaced north of the lane (y=+0.2): while driving, the
    # commanded twist must steer negative (back toward y=0).
    odom_sub.callback(_odom_at(0.0, 0.2, yaw=0.0))
    timer.tick()  # turn phase passes (already at target yaw)
    odom_sub.callback(_odom_at(0.0, 0.2, yaw=0.0))
    timer.tick()
    assert pub.messages[-1].linear.x > 0.0
    assert pub.messages[-1].angular.z < 0.0

    # Displaced south: steer positive.
    odom_sub.callback(_odom_at(0.5, -0.2, yaw=0.0))
    timer.tick()
    assert pub.messages[-1].angular.z > 0.0

    # On the centerline: no correction.
    odom_sub.callback(_odom_at(1.0, 0.0, yaw=0.0))
    timer.tick()
    assert pub.messages[-1].angular.z == 0.0


def test_backup_steers_back_toward_lane_center_while_reversing(backup_adapter) -> None:
    # Reversing 1.3m inside the 0.55m corridor from a slightly-angled
    # standoff pose drifted the yielder into a wall until the safety bound
    # fired (H3 run 12) — backup needs the same lane servo as the escort.
    # Sign flips vs forward drive: moving backward, lateral velocity is
    # -|v|*sin(yaw), so returning to y=0 from y>0 needs yaw>0 (wz>0).
    adapter, node = backup_adapter
    adapter.backup("robot_1", distance_m=1.3, speed_mps=0.1)
    odom_sub = node.subscriptions[-1]
    timer = node.timers[-1]
    pub = node.publishers["/robot_1/cmd_vel"]

    odom_sub.callback(_odom_at(0.0, 0.2, yaw=0.0))
    timer.tick()
    assert pub.messages[-1].linear.x < 0.0
    assert pub.messages[-1].angular.z > 0.0

    odom_sub.callback(_odom_at(-0.5, -0.2, yaw=0.0))
    timer.tick()
    assert pub.messages[-1].angular.z < 0.0

    odom_sub.callback(_odom_at(-1.0, 0.0, yaw=0.0))
    timer.tick()
    assert pub.messages[-1].angular.z == 0.0

"""Node-level tests of the M4 stall abort: adapter primitives and command bus (mocked ROS).

Report: docs/reports/2026-11-15-m4-stall-abort.md.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
import swarm_execution.nav2_adapter as nav2_adapter
import yaml
from swarm_execution import command_bus_node as bus_mod
from swarm_execution.command_bus_node import CommandBusNode, load_stall_abort_config
from swarm_execution.nav2_adapter import Nav2Adapter
from swarm_execution.stall_abort import (
    STALL_ABORT_DETAIL_PREFIX,
    StallAbortConfig,
    StallWatch,
    startup_suffix,
)

from scripts.stall_abort_replay import ReplayNode, odom_message

REPO = Path(__file__).resolve().parents[2]
TICK = 0.05

if bus_mod.CoordinationStatus is object:

    class _CoordinationStatusStub:
        def __init__(self):
            self.command_id = None
            self.robot_id = None
            self.status = None
            self.detail = None

    bus_mod.CoordinationStatus = _CoordinationStatusStub


def _watch(robot="robot_1", primitive="backup", log=None, held=None):
    return StallWatch(
        StallAbortConfig(enabled=True),
        robot_id=robot,
        command_id="cmd-S",
        primitive=primitive,
        is_held=held,
        log=log,
    )


def _drive(node: ReplayNode, robot: str, pose, duration_s: float, start_s: float = 10.0,
           stamp=lambda t: t, results=None):
    """Tick the adapter's live timer at 20 Hz, odometry at 10 Hz from `pose(t)`."""
    topic = f"/{robot}/odom"
    for i in range(int(round(duration_s / TICK)) + 1):
        t = round(start_s + i * TICK, 6)
        node.clock.seconds = t
        if i % 2 == 0 and topic in node.odom_callbacks:
            x, y, yaw = pose(t)
            node.odom_callbacks[topic](odom_message(stamp(t), x, y, yaw))
        live = [timer for timer in node.timers if not timer.cancelled]
        if not live:
            return t
        live[-1].callback()
        if results and results[-1][0] in ("COMPLETED", "FAILED"):
            return t
    return None


def _backup_rig(watch):
    node = ReplayNode()
    node.clock.seconds = 10.0
    adapter = Nav2Adapter(node)
    results: list[tuple[str, str]] = []
    adapter.backup(
        "robot_1", 1.3, on_result=lambda s, d: results.append((s, d)), stall_watch=watch
    )
    return node, adapter, results


# Adapter primitives


def test_backup_pinned_aborts_failed_with_zero_twist_and_log_line() -> None:
    lines: list[str] = []
    node, adapter, results = _backup_rig(_watch(log=lines.append))
    _drive(node, "robot_1", lambda t: (0.0, 0.0, 0.0), 30.0, results=results)
    status, detail = results[-1]
    assert status == "FAILED" and detail.startswith(STALL_ABORT_DETAIL_PREFIX)
    last = node.publishers["/robot_1/cmd_vel"].messages[-1]
    assert (last.linear.x, last.angular.z) == (0.0, 0.0)
    assert all(timer.cancelled for timer in node.timers)
    assert "/robot_1/odom" not in node.odom_callbacks
    assert len(lines) == 1
    assert lines[0].startswith(
        "stall abort robot=robot_1 command=cmd-S primitive=backup phase=backup reason=stall"
    )


def test_backup_pinned_without_watch_keeps_driving() -> None:
    node, _adapter, results = _backup_rig(None)
    _drive(node, "robot_1", lambda t: (0.0, 0.0, 0.0), 30.0, results=results)
    assert results == [("ACTIVE", "backup started")]
    assert node.publishers["/robot_1/cmd_vel"].messages[-1].linear.x == -0.1


def test_backup_command_stream_identical_with_and_without_watch_when_moving() -> None:
    def pose(t: float):
        return (-0.1 * max(0.0, t - 10.2), 0.0, 0.0)

    streams = []
    for watch in (None, _watch()):
        node, _adapter, results = _backup_rig(watch)
        _drive(node, "robot_1", pose, 30.0, results=results)
        assert results[-1][0] == "COMPLETED"
        streams.append(
            [(m.linear.x, m.angular.z) for m in node.publishers["/robot_1/cmd_vel"].messages]
        )
    assert streams[0] == streams[1]


def test_backup_without_odometry_aborts_input_stale() -> None:
    node, _adapter, results = _backup_rig(_watch())
    for i in range(60):
        node.clock.seconds = round(10.0 + i * TICK, 6)
        [t for t in node.timers if not t.cancelled][-1].callback()
        if results[-1][0] == "FAILED":
            break
    assert results[-1][0] == "FAILED"
    assert results[-1][1].startswith(f"{STALL_ABORT_DETAIL_PREFIX} input_stale")


def test_backup_lagging_header_stamps_abort_input_stale() -> None:
    # Odometry keeps arriving but its stamps froze: stale, not "no movement".
    node, _adapter, results = _backup_rig(_watch())
    _drive(
        node,
        "robot_1",
        lambda t: (-0.1 * (t - 10.0), 0.0, 0.0),
        10.0,
        stamp=lambda t: min(t, 11.0),
        results=results,
    )
    assert results[-1][0] == "FAILED"
    assert "input_stale" in results[-1][1]


def test_backup_held_robot_is_not_aborted() -> None:
    node, _adapter, results = _backup_rig(_watch(held=lambda: True))
    _drive(node, "robot_1", lambda t: (0.0, 0.0, 0.0), 60.0, results=results)
    assert results == [("ACTIVE", "backup started")]


def test_sidestep_blocked_turn_aborts_in_turn_out() -> None:
    lines: list[str] = []
    node = ReplayNode()
    node.clock.seconds = 10.0
    results: list[tuple[str, str]] = []
    Nav2Adapter(node).sidestep(
        "robot_1",
        0.35,
        on_result=lambda s, d: results.append((s, d)),
        stall_watch=_watch(primitive="pull_off", log=lines.append),
    )
    _drive(node, "robot_1", lambda t: (0.0, 0.0, 0.0), 30.0, results=results)
    assert results[-1][0] == "FAILED"
    assert "rad/s" in results[-1][1]
    assert "primitive=pull_off phase=turn_out reason=stall mode=angular" in lines[0]


def test_sidestep_without_odometry_aborts_input_stale() -> None:
    node = ReplayNode()
    node.clock.seconds = 10.0
    results: list[tuple[str, str]] = []
    Nav2Adapter(node).sidestep(
        "robot_1", 0.35, on_result=lambda s, d: results.append((s, d)), stall_watch=_watch()
    )
    for i in range(60):
        node.clock.seconds = round(10.0 + i * TICK, 6)
        [t for t in node.timers if not t.cancelled][-1].callback()
        if results[-1][0] == "FAILED":
            break
    assert results[-1][0] == "FAILED" and "input_stale" in results[-1][1]
    # Nothing was ever published without odometry, except the final zero.
    messages = node.publishers["/robot_1/cmd_vel"].messages
    assert [(m.linear.x, m.angular.z) for m in messages] == [(0.0, 0.0)]


def test_drive_heading_pinned_in_drive_aborts() -> None:
    lines: list[str] = []
    node = ReplayNode()
    node.clock.seconds = 10.0
    results: list[tuple[str, str]] = []
    Nav2Adapter(node).drive_heading(
        "robot_3",
        target_yaw_rad=0.0,
        distance_m=1.6,
        on_result=lambda s, d: results.append((s, d)),
        stall_watch=_watch(robot="robot_3", primitive="escort", log=lines.append),
    )

    def pose(t: float):
        # The m5D pattern: 0.09 m/s, then stopped against the face at 5.9 s.
        return (0.09 * min(t - 10.0, 5.9), 0.0, 0.0)

    _drive(node, "robot_3", pose, 60.0, results=results)
    assert results[-1][0] == "FAILED"
    assert "primitive=escort phase=drive reason=stall" in lines[0]
    assert node.clock.seconds < 10.0 + 5.9 + 3.0


def test_drive_heading_without_watch_runs_to_completion_unchanged() -> None:
    streams = []
    for watch in (None, _watch(robot="robot_3", primitive="escort")):
        node = ReplayNode()
        node.clock.seconds = 10.0
        results: list[tuple[str, str]] = []
        Nav2Adapter(node).drive_heading(
            "robot_3",
            0.0,
            1.0,
            on_result=lambda s, d, r=results: r.append((s, d)),
            stall_watch=watch,
        )
        _drive(node, "robot_3", lambda t: (0.1 * (t - 10.2), 0.0, 0.0), 30.0, results=results)
        assert results[-1][0] == "COMPLETED"
        streams.append(
            [(m.linear.x, m.angular.z) for m in node.publishers["/robot_3/cmd_vel"].messages]
        )
    assert streams[0] == streams[1]


def test_stall_abort_sim_time_independent_of_wall_rate(monkeypatch) -> None:
    # The primitive's own deadline is wall-monotonic; the abort is sim time.
    fire_times = []
    for rtf in (0.17, 1.0):
        wall = {"t": 1000.0}
        monkeypatch.setattr(nav2_adapter.time, "monotonic", lambda w=wall: w["t"])
        node, _adapter, results = _backup_rig(_watch())

        def pose(t: float, _wall=wall, _rtf=rtf):
            _wall["t"] = 1000.0 + (t - 10.0) / _rtf
            return (-0.1 * min(max(0.0, t - 10.2), 2.0), 0.0, 0.0)

        fire_times.append(_drive(node, "robot_1", pose, 60.0, results=results))
        assert results[-1][1].startswith(STALL_ABORT_DETAIL_PREFIX)
    assert fire_times[0] == fire_times[1]


def test_odom_stamp_sec_reads_header_and_tolerates_stub() -> None:
    assert nav2_adapter.odom_stamp_sec(odom_message(12.25, 0.0, 0.0, 0.0)) == pytest.approx(12.25)
    assert nav2_adapter.odom_stamp_sec(nav2_adapter.Odometry()) is None


# Command bus


class _Logger:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def info(self, msg) -> None:
        self.lines.append(str(msg))

    warning = info
    error = info


class _Timer:
    def __init__(self, period, cb) -> None:
        self.period = period
        self.cb = cb
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class _Msg:
    def __init__(self, command_id, robot_id, action, parameters) -> None:
        self.command_id = command_id
        self.robot_id = robot_id
        self.action = action
        self.parameters_json = json.dumps(parameters)
        self.timeout_sec = 0.0


class _Adapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.on_result: dict[str, object] = {}

    def cancel(self, robot_id) -> None:
        self.calls.append(("cancel", robot_id, {}))

    def backup(self, robot_id, distance_m, on_result=None, **kwargs) -> None:
        self.calls.append(("backup", robot_id, kwargs))
        self.on_result[f"backup:{robot_id}"] = on_result

    def sidestep(self, robot_id, lateral_m, on_result=None, **kwargs) -> None:
        self.calls.append(("sidestep", robot_id, kwargs))
        self.on_result[f"sidestep:{robot_id}"] = on_result

    def drive_heading(self, robot_id, target_yaw_rad, distance_m, on_result=None, **kwargs):
        self.calls.append(("drive_heading", robot_id, kwargs))
        self.on_result[f"escort:{robot_id}"] = on_result


def _bus(stall_on: bool):
    node = CommandBusNode.__new__(CommandBusNode)
    node._adapter = _Adapter()
    node._in_flight = {}
    node._active_waits = {}
    node._nav_watchdogs = {}
    node._status_republish_timers = []
    node._fresh_latch = None
    node._stall_config = StallAbortConfig(enabled=stall_on)
    node._held = frozenset()
    node._holds_sub = None
    node.timers = []
    node.subscriptions = []

    def create_timer(period, cb):
        timer = _Timer(period, cb)
        node.timers.append(timer)
        return timer

    def create_subscription(mtype, topic, cb, qos):
        node.subscriptions.append((topic, cb))
        return topic

    node.create_timer = create_timer
    node.destroy_timer = lambda t: None
    node.create_subscription = create_subscription
    node.destroy_subscription = lambda s: None
    logger = _Logger()
    node.get_logger = lambda: logger
    node.get_clock = lambda: SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=0))
    published: list[tuple] = []

    class _Pub:
        def publish(self, msg):
            published.append((msg.command_id, msg.robot_id, msg.status, msg.detail))

    node._status_pub = _Pub()
    return node, published, logger


_YIELD = {
    "backup_distance_m": 0.8,
    "hold_sec": 45.0,
    "pull_off_lateral_m": 0.35,
    "passer_robot_id": "robot_2",
    "passer_clear_m": 2.4,
    "passer_escort_distance_m": 2.4,
}
_STALL = (
    f"{STALL_ABORT_DETAIL_PREFIX} commanded 0.100 m/s for 3.0 s, "
    "measured 0.004 m (expected >= 0.075 m)"
)


def test_stall_kwargs_empty_with_key_off() -> None:
    node, _published, _logger = _bus(stall_on=False)
    node._on_command(_Msg("cmd-Y", "robot_1", "reverse", {"backup_distance_m": 1.3}))
    assert node._adapter.calls[-1] == ("backup", "robot_1", {})


def test_stall_kwargs_empty_on_node_built_without_config() -> None:
    node = CommandBusNode.__new__(CommandBusNode)
    assert node._stall_kwargs("robot_1", "c", "backup") == {}


def test_backup_gets_a_watch_with_key_on() -> None:
    node, _published, _logger = _bus(stall_on=True)
    node._on_command(_Msg("cmd-Y", "robot_1", "reverse", {"backup_distance_m": 1.3}))
    kind, robot, kwargs = node._adapter.calls[-1]
    assert (kind, robot) == ("backup", "robot_1")
    assert isinstance(kwargs["stall_watch"], StallWatch)


def test_backup_stall_reaches_m5_as_failed_with_reason() -> None:
    node, published, _logger = _bus(stall_on=True)
    node._on_command(_Msg("cmd-Y", "robot_2", "temporary_wait", {"duration_sec": 120.0}))
    node._on_command(_Msg("cmd-Y", "robot_1", "reverse", {"backup_distance_m": 1.3}))
    node._adapter.on_result["backup:robot_1"]("FAILED", _STALL)
    assert ("cmd-Y", "robot_1", "FAILED", _STALL) in published
    assert ("cmd-Y", "robot_2", "COMPLETED", "released: yield failed") in published


def test_pull_off_gets_a_watch_with_key_on() -> None:
    node, _published, _logger = _bus(stall_on=True)
    node._on_command(_Msg("cmd-Y", "robot_1", "yield", _YIELD))
    node._adapter.on_result["backup:robot_1"]("COMPLETED", "backup complete")
    kind, _robot, kwargs = node._adapter.calls[-1]
    assert kind == "sidestep" and isinstance(kwargs["stall_watch"], StallWatch)


def _escort(stall_on: bool):
    node, published, logger = _bus(stall_on=stall_on)
    node._on_command(_Msg("cmd-Y", "robot_2", "temporary_wait", {"duration_sec": 120.0}))
    node._on_command(_Msg("cmd-Y", "robot_1", "yield", _YIELD))
    node._adapter.on_result["backup:robot_1"]("COMPLETED", "backup complete")
    node._adapter.on_result["sidestep:robot_1"]("COMPLETED", "side step complete")
    return node, published, logger


def test_escort_gets_a_watch_with_key_on() -> None:
    node, _published, _logger = _escort(stall_on=True)
    kind, robot, kwargs = node._adapter.calls[-1]
    assert (kind, robot) == ("drive_heading", "robot_2")
    assert isinstance(kwargs["stall_watch"], StallWatch)


def test_escort_stall_fails_the_passer_wait_with_reason() -> None:
    node, published, logger = _escort(stall_on=True)
    node._adapter.on_result["escort:robot_2"]("FAILED", _STALL)
    assert ("cmd-Y", "robot_2", "FAILED", _STALL) in published
    assert ("cmd-Y", "robot_2") not in node._active_waits
    assert f"escort robot_2: FAILED {_STALL}" in logger.lines
    # The yielder's hold is untouched: it still ends on its own timer.
    assert not any(p[1] == "robot_1" and p[2] in ("COMPLETED", "FAILED") for p in published)


def test_escort_deadline_failure_keeps_the_wait_as_before() -> None:
    node, published, _logger = _escort(stall_on=True)
    node._adapter.on_result["escort:robot_2"]("FAILED", "escort timed out in phase drive")
    assert ("cmd-Y", "robot_2") in node._active_waits
    assert not any(p[1] == "robot_2" and p[2] == "FAILED" for p in published)


def test_escort_with_key_off_gets_no_watch() -> None:
    node, _published, _logger = _escort(stall_on=False)
    assert node._adapter.calls[-1] == ("drive_heading", "robot_2", {})


def test_holds_message_gates_the_watch() -> None:
    node, _published, _logger = _bus(stall_on=True)
    watch = node._stall_kwargs("robot_1", "c", "backup")["stall_watch"]
    node._on_safety_holds(SimpleNamespace(data=json.dumps({"held": ["robot_1"]})))
    assert watch._is_held() is True
    node._on_safety_holds(SimpleNamespace(data="not json"))
    assert watch._is_held() is True
    node._on_safety_holds(SimpleNamespace(data=json.dumps({"held": []})))
    assert watch._is_held() is False


def test_holds_subscription_shared_with_fresh_latch() -> None:
    node, _published, _logger = _bus(stall_on=True)
    node._ensure_holds_subscription()
    node._fresh_latch_watch()
    assert [topic for topic, _cb in node.subscriptions] == ["/safety/holds"]


def test_startup_line_unchanged_with_key_off() -> None:
    assert "Command bus started." + startup_suffix(StallAbortConfig()) == "Command bus started."


def _install_share(monkeypatch, tmp_path: Path, safety: dict) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "safety.yaml").write_text(yaml.safe_dump({"safety": safety}))
    packages = types.ModuleType("ament_index_python.packages")
    packages.get_package_share_directory = lambda name: str(tmp_path)
    monkeypatch.setitem(sys.modules, "ament_index_python", types.ModuleType("ament_index_python"))
    monkeypatch.setitem(sys.modules, "ament_index_python.packages", packages)


def _base_safety() -> dict:
    path = REPO / "ros2_ws/src/swarm_execution/config/safety.yaml"
    return yaml.safe_load(path.read_text())["safety"]


def test_loader_reads_base_safety_file_as_off(monkeypatch, tmp_path) -> None:
    _install_share(monkeypatch, tmp_path, _base_safety())
    node = SimpleNamespace(get_logger=lambda: _Logger())
    assert load_stall_abort_config(node) == StallAbortConfig()


def test_loader_reads_merged_fragment_as_on(monkeypatch, tmp_path) -> None:
    fragment = yaml.safe_load((REPO / "config/safety/stall_abort.fragment.yaml").read_text())
    _install_share(monkeypatch, tmp_path, {**_base_safety(), **fragment["safety"]})
    node = SimpleNamespace(get_logger=lambda: _Logger())
    config = load_stall_abort_config(node)
    assert config.enabled is True
    assert startup_suffix(config).startswith(" stall_abort=True window_s=3.0 ")


def test_loader_unreadable_file_is_off_with_a_warning(monkeypatch, tmp_path) -> None:
    packages = types.ModuleType("ament_index_python.packages")
    packages.get_package_share_directory = lambda name: str(tmp_path / "missing")
    monkeypatch.setitem(sys.modules, "ament_index_python", types.ModuleType("ament_index_python"))
    monkeypatch.setitem(sys.modules, "ament_index_python.packages", packages)
    logger = _Logger()
    assert load_stall_abort_config(SimpleNamespace(get_logger=lambda: logger)).enabled is False
    assert logger.lines and logger.lines[0].startswith("stall_abort config unreadable")


def test_fragment_values_equal_code_defaults() -> None:
    fragment = yaml.safe_load((REPO / "config/safety/stall_abort.fragment.yaml").read_text())
    block = fragment["safety"]["stall_abort"]
    assert block.pop("enabled") is True
    assert StallAbortConfig(enabled=True, **block) == StallAbortConfig(enabled=True)
    assert set(fragment["safety"]) == {"stall_abort"}


def test_base_safety_file_has_no_stall_abort_key() -> None:
    assert "stall_abort" not in _base_safety()

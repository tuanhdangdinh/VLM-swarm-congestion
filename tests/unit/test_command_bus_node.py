import json

from swarm_execution import command_bus_node as _command_bus_node_mod
from swarm_execution.command_bus_node import CommandBusNode

if _command_bus_node_mod.CoordinationStatus is object:
    # This dev sandbox has no rclpy/swarm_interfaces build at all, so the
    # module's ImportError shim falls back to plain `object`, which rejects
    # attribute assignment and would break every real `_publish_status` call
    # (including pre-existing tests, not just the ones added here). Swap in
    # a minimal mutable stand-in so the real _on_command/_publish_status
    # integration is actually exercisable in this environment; a real ROS2
    # environment imports the genuine generated message class instead.
    class _CoordinationStatusStub:
        def __init__(self):
            self.command_id = None
            self.robot_id = None
            self.status = None
            self.detail = None

    _command_bus_node_mod.CoordinationStatus = _CoordinationStatusStub


class _Msg:
    def __init__(
        self,
        command_id="cmd-1",
        robot_id="robot_1",
        action="navigate",
        parameters_json="{}",
        timeout_sec=0.0,
    ):
        self.command_id = command_id
        self.robot_id = robot_id
        self.action = action
        self.parameters_json = parameters_json
        self.timeout_sec = timeout_sec


def test_command_bus_dispatches_yield_to_backup():
    node = CommandBusNode.__new__(CommandBusNode)
    calls = []

    class Adapter:
        def backup(self, robot_id, distance_m, on_result=None):
            calls.append(("backup", robot_id, distance_m))

    node._adapter = Adapter()
    pending = node._dispatch(
        _Msg(action="yield"), {"duration_sec": 8.0, "backup_distance_m": 0.4}
    )

    assert calls == [("backup", "robot_1", 0.4)]
    assert pending is True


def test_command_bus_dispatches_reverse_to_backup():
    node = CommandBusNode.__new__(CommandBusNode)
    calls = []

    class Adapter:
        def backup(self, robot_id, distance_m, on_result=None):
            calls.append(("backup", robot_id, distance_m))

    node._adapter = Adapter()
    pending = node._dispatch(_Msg(action="reverse"), {"backup_distance_m": 0.3})

    assert calls == [("backup", "robot_1", 0.3)]
    assert pending is True


def test_command_bus_dispatches_wait_to_cancel():
    # duration_sec > 0 holds Nav2 paused via a timer (f5f592e) rather than
    # completing immediately, so dispatch is pending until the hold expires.
    calls = []

    class Adapter:
        def cancel(self, robot_id):
            calls.append(("cancel", robot_id))

    node, _published = _build_node(Adapter())
    pending = node._dispatch(_Msg(action="temporary_wait"), {"duration_sec": 8.0})

    assert calls == [("cancel", "robot_1")]
    assert pending is True


def test_command_bus_dispatches_reroute_to_waypoints():
    node = CommandBusNode.__new__(CommandBusNode)
    calls = []

    class Adapter:
        def send_waypoints(self, robot_id, waypoints, on_result=None):
            calls.append(("waypoints", robot_id, waypoints))

    node._adapter = Adapter()
    pending = node._dispatch(
        _Msg(action="reroute"),
        {"waypoints": [{"x": 1.0, "y": 2.0}, [3.0, 4.0]]},
    )

    assert calls == [("waypoints", "robot_1", [(1.0, 2.0), (3.0, 4.0)])]
    assert pending is True


def test_command_bus_dispatches_goal_to_navigate():
    node = CommandBusNode.__new__(CommandBusNode)
    calls = []

    class Adapter:
        def send_goal(self, robot_id, x, y, yaw, on_result=None):
            calls.append(("goal", robot_id, x, y, yaw))

    node._adapter = Adapter()
    pending = node._dispatch(
        _Msg(action="navigate"), {"goal": {"x": 1.0, "y": 2.0, "yaw": 0.5}}
    )

    assert calls == [("goal", "robot_1", 1.0, 2.0, 0.5)]
    assert pending is True


def test_command_bus_does_not_complete_nav_command_before_action_result():
    node = CommandBusNode.__new__(CommandBusNode)
    statuses = []

    class Logger:
        def info(self, msg):
            pass

        def error(self, msg):
            pass

    class Adapter:
        def send_goal(self, robot_id, x, y, yaw, on_result=None):
            self.on_result = on_result

    adapter = Adapter()
    node._adapter = adapter
    node._in_flight = {}
    node.get_logger = lambda: Logger()
    node._publish_status = lambda command, status, detail: statuses.append((status, detail))

    node._on_command(
        _Msg(
            command_id="nav-1",
            action="navigate",
            parameters_json=json.dumps({"goal": {"x": 1.0, "y": 2.0}}),
        )
    )

    assert statuses == []
    adapter.on_result("COMPLETED", "goal succeeded")
    assert statuses == [("COMPLETED", "goal succeeded")]


def test_command_bus_yield_pull_off_sends_goal_after_backup():
    # A straight backup alone re-blocks the passer's path in the head-on
    # scenario, so a grounded yield with pull_off_* must route through
    # Nav2's send_goal (not another raw-cmd_vel backup) once the initial
    # backup opens separation.
    node = CommandBusNode.__new__(CommandBusNode)
    calls = []

    class Adapter:
        def backup(self, robot_id, distance_m, on_result=None):
            calls.append(("backup", robot_id, distance_m))
            self.backup_on_result = on_result

        def send_goal(self, robot_id, x, y, yaw, on_result=None):
            calls.append(("send_goal", robot_id, x, y, yaw))
            self.goal_on_result = on_result

    adapter = Adapter()
    node._adapter = adapter
    node._nav_watchdogs = {}
    node._publish_status = lambda command, status, detail: None

    pending = node._dispatch(
        _Msg(action="yield"),
        {
            "backup_distance_m": 0.8,
            "hold_sec": 12.0,
            "pull_off_x": -1.4,
            "pull_off_y": 0.35,
            "pull_off_yaw": 0.0,
        },
    )
    assert pending is True
    assert calls == [("backup", "robot_1", 0.8)]

    adapter.backup_on_result("COMPLETED", "backup done")
    assert calls == [
        ("backup", "robot_1", 0.8),
        ("send_goal", "robot_1", -1.4, 0.35, 0.0),
    ]


def test_command_bus_yield_holds_after_pull_off_completes():
    node = CommandBusNode.__new__(CommandBusNode)
    statuses = []

    class Adapter:
        def backup(self, robot_id, distance_m, on_result=None):
            self.backup_on_result = on_result

        def send_goal(self, robot_id, x, y, yaw, on_result=None):
            self.goal_on_result = on_result

    adapter = Adapter()
    node._adapter = adapter
    node._nav_watchdogs = {}
    node._publish_status = lambda command, status, detail: statuses.append((status, detail))
    node.create_timer = lambda period, cb: cb() or object()
    node.destroy_timer = lambda t: None

    node._dispatch(
        _Msg(action="yield"),
        {
            "backup_distance_m": 0.8,
            "hold_sec": 12.0,
            "pull_off_x": -1.4,
            "pull_off_y": 0.35,
            "pull_off_yaw": 0.0,
        },
    )
    adapter.backup_on_result("COMPLETED", "backup done")
    adapter.goal_on_result("COMPLETED", "goal succeeded")

    assert ("ACTIVE", "holding for passing robot") in statuses
    assert ("COMPLETED", "yield complete") in statuses


def test_command_bus_yield_without_pull_off_holds_directly_after_backup():
    # Backwards-compat path: no pull_off_* params (e.g. an unmapped robot_id
    # in the grounder's lookup) keeps the original straight-backup-then-hold
    # behavior.
    node = CommandBusNode.__new__(CommandBusNode)
    calls = []
    statuses = []

    class Adapter:
        def backup(self, robot_id, distance_m, on_result=None):
            calls.append(("backup", robot_id, distance_m))
            self.backup_on_result = on_result

        def send_goal(self, robot_id, x, y, yaw, on_result=None):
            calls.append(("send_goal", robot_id, x, y, yaw))

    adapter = Adapter()
    node._adapter = adapter
    node._publish_status = lambda command, status, detail: statuses.append((status, detail))
    node.create_timer = lambda period, cb: cb() or object()
    node.destroy_timer = lambda t: None

    node._dispatch(
        _Msg(action="yield"),
        {"backup_distance_m": 0.8, "hold_sec": 12.0},
    )
    adapter.backup_on_result("COMPLETED", "backup done")

    assert calls == [("backup", "robot_1", 0.8)]
    assert ("ACTIVE", "holding for passing robot") in statuses
    assert ("COMPLETED", "yield complete") in statuses


def _build_node(adapter):
    """Build a CommandBusNode test double wired for real `_publish_status`.

    Unlike the dispatch-only tests above, the in-flight registry tests need
    the genuine `_publish_status`/`_on_command` integration (not an
    overridden lambda), so this stubs only the rclpy-facing collaborators:
    the status publisher, logger, and timer creation.
    """
    node = CommandBusNode.__new__(CommandBusNode)
    node._adapter = adapter
    node._in_flight = {}
    node._active_waits = {}
    node._nav_watchdogs = {}
    node._status_republish_timers = []
    node.create_timer = lambda period, cb: object()
    node.destroy_timer = lambda t: None

    class Logger:
        def info(self, msg):
            pass

        def error(self, msg):
            pass

    node.get_logger = lambda: Logger()

    published = []

    class StatusPub:
        def publish(self, msg):
            published.append((msg.command_id, msg.robot_id, msg.status, msg.detail))

    node._status_pub = StatusPub()
    return node, published


def test_second_command_while_busy_rejected_with_failed_status():
    class Adapter:
        def backup(self, robot_id, distance_m, on_result=None):
            on_result("ACTIVE", "backup started")

    node, published = _build_node(Adapter())

    node._on_command(_Msg(command_id="cmd-1", robot_id="robot_1", action="yield"))
    node._on_command(_Msg(command_id="cmd-2", robot_id="robot_1", action="yield"))

    assert ("cmd-1", "robot_1", "ACTIVE", "backup started") in published
    assert ("cmd-2", "robot_1", "FAILED", "robot busy: cmd-1") in published
    assert node._in_flight == {"robot_1": "cmd-1"}


def test_same_command_id_redelivery_ignored():
    class Adapter:
        def backup(self, robot_id, distance_m, on_result=None):
            on_result("ACTIVE", "backup started")

    node, published = _build_node(Adapter())

    node._on_command(_Msg(command_id="cmd-1", robot_id="robot_1", action="yield"))
    published.clear()
    node._on_command(_Msg(command_id="cmd-1", robot_id="robot_1", action="yield"))

    assert published == []
    assert node._in_flight == {"robot_1": "cmd-1"}


class _FakeTimer:
    """Cancel-able stand-in for `rclpy.timer.Timer` in tests."""

    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class _YieldWaitAdapter:
    """Combined adapter double: captures yield `backup()` callbacks by robot
    so a test can complete/fail the yield after the linked wait is already
    registered, and records `cancel()` calls from wait dispatch."""

    def __init__(self):
        self.backup_on_result: dict[str, callable] = {}
        self.cancel_calls: list[str] = []

    def backup(self, robot_id, distance_m, on_result=None):
        self.backup_on_result[robot_id] = on_result

    def cancel(self, robot_id):
        self.cancel_calls.append(robot_id)


def test_linked_wait_released_when_yield_completes():
    adapter = _YieldWaitAdapter()
    node, published = _build_node(adapter)
    # duration_sec=100.0 is unique to the wait's own timer (republish timers
    # use 0.25/0.75), so keying by period lets the test recover exactly that
    # timer later and assert it was cancelled, not just replaced/ignored.
    timers_by_period: dict[float, _FakeTimer] = {}

    def create_timer_stub(period, cb):
        timer = _FakeTimer()
        timers_by_period[period] = timer
        return timer

    node.create_timer = create_timer_stub

    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_2",
            action="temporary_wait",
            parameters_json=json.dumps({"duration_sec": 100.0}),
        )
    )
    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_1",
            action="yield",
            parameters_json=json.dumps({"backup_distance_m": 0.3}),
        )
    )

    assert ("cmd-A", "robot_2") in node._active_waits

    adapter.backup_on_result["robot_1"]("COMPLETED", "backup done")

    assert ("cmd-A", "robot_2") not in node._active_waits
    assert ("cmd-A", "robot_2", "COMPLETED", "released: yield complete") in published
    assert timers_by_period[100.0].cancelled is True


def test_linked_wait_released_when_yield_completes_via_hold_expiry():
    # The representative production path: yield's terminal COMPLETED comes
    # from the post-backup hold timer expiring (hold_sec > 0), not directly
    # from the backup result. Same _publish_status gate as the direct-COMPLETED
    # path, but exercised through the actual hold/pull-off machinery.
    adapter = _YieldWaitAdapter()
    node, published = _build_node(adapter)

    # Only the yield's hold timer (period=12.0) fires synchronously, so the
    # linked wait's own 100.0s timer and the 0.25/0.75s republish timers stay
    # inert — matching test_wait_natural_expiry_still_publishes_completed's
    # rationale for isolating exactly one timer per stub call.
    def create_timer_stub(period, cb):
        if period == 12.0:
            return cb() or _FakeTimer()
        return _FakeTimer()

    node.create_timer = create_timer_stub

    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_2",
            action="temporary_wait",
            parameters_json=json.dumps({"duration_sec": 100.0}),
        )
    )
    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_1",
            action="yield",
            parameters_json=json.dumps({"backup_distance_m": 0.3, "hold_sec": 12.0}),
        )
    )

    assert ("cmd-A", "robot_2") in node._active_waits

    adapter.backup_on_result["robot_1"]("COMPLETED", "backup done")

    assert ("cmd-A", "robot_2") not in node._active_waits
    assert ("cmd-A", "robot_2", "COMPLETED", "released: yield complete") in published


def test_linked_wait_released_when_yield_fails():
    adapter = _YieldWaitAdapter()
    node, published = _build_node(adapter)
    node.create_timer = lambda period, cb: _FakeTimer()

    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_2",
            action="temporary_wait",
            parameters_json=json.dumps({"duration_sec": 100.0}),
        )
    )
    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_1",
            action="yield",
            parameters_json=json.dumps({"backup_distance_m": 0.3}),
        )
    )

    adapter.backup_on_result["robot_1"]("FAILED", "backup obstructed")

    assert ("cmd-A", "robot_2") not in node._active_waits
    assert ("cmd-A", "robot_2", "COMPLETED", "released: yield failed") in published


def test_unlinked_wait_unaffected_by_other_commands_terminal():
    adapter = _YieldWaitAdapter()
    node, published = _build_node(adapter)
    node.create_timer = lambda period, cb: _FakeTimer()

    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_2",
            action="temporary_wait",
            parameters_json=json.dumps({"duration_sec": 100.0}),
        )
    )
    node._on_command(
        _Msg(
            command_id="cmd-B",
            robot_id="robot_3",
            action="yield",
            parameters_json=json.dumps({"backup_distance_m": 0.3}),
        )
    )

    published.clear()
    adapter.backup_on_result["robot_3"]("COMPLETED", "backup done")

    assert ("cmd-A", "robot_2") in node._active_waits
    assert all(entry[1] != "robot_2" for entry in published)


def test_busy_rejected_yield_releases_linked_wait_as_rejected():
    # A yield that never dispatched (busy-rejected by the in-flight guard)
    # must still free its linked wait — otherwise the waiting robot is held
    # hostage to a maneuver that will never happen — but with provenance
    # "rejected", not "failed": no yield was attempted.
    adapter = _YieldWaitAdapter()
    node, published = _build_node(adapter)
    node.create_timer = lambda period, cb: _FakeTimer()

    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_2",
            action="temporary_wait",
            parameters_json=json.dumps({"duration_sec": 100.0}),
        )
    )
    node._on_command(
        _Msg(
            command_id="cmd-0",
            robot_id="robot_1",
            action="yield",
            parameters_json=json.dumps({"backup_distance_m": 0.3}),
        )
    )
    # Mark robot_1 in-flight under cmd-0 so the next command busy-rejects.
    adapter.backup_on_result["robot_1"]("ACTIVE", "backup started")

    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_1",
            action="yield",
            parameters_json=json.dumps({"backup_distance_m": 0.3}),
        )
    )

    assert ("cmd-A", "robot_1", "FAILED", "robot busy: cmd-0") in published
    assert ("cmd-A", "robot_2") not in node._active_waits
    assert ("cmd-A", "robot_2", "COMPLETED", "released: yield rejected") in published


def test_linked_wait_released_when_reverse_completes():
    # Parity check for the second clearing action: the release gate covers
    # action in {"yield", "reverse"}, but every other linked-wait test
    # exercises yield only.
    adapter = _YieldWaitAdapter()
    node, published = _build_node(adapter)
    node.create_timer = lambda period, cb: _FakeTimer()

    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_2",
            action="temporary_wait",
            parameters_json=json.dumps({"duration_sec": 100.0}),
        )
    )
    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_1",
            action="reverse",
            parameters_json=json.dumps({"backup_distance_m": 0.3}),
        )
    )

    assert ("cmd-A", "robot_2") in node._active_waits

    adapter.backup_on_result["robot_1"]("COMPLETED", "backup done")

    assert ("cmd-A", "robot_2") not in node._active_waits
    assert ("cmd-A", "robot_2", "COMPLETED", "released: yield complete") in published


def test_wait_natural_expiry_still_publishes_completed():
    # Only the wait's own duration timer (period=5.0) fires synchronously;
    # the status-republish timers (period 0.25/0.75, scheduled from within
    # the real _publish_status) must stay inert, or their own timer_ref
    # bookkeeping (set after create_timer returns) would raise.
    adapter = _YieldWaitAdapter()
    node, published = _build_node(adapter)

    def create_timer_stub(period, cb):
        if period == 5.0:
            return cb() or _FakeTimer()
        return _FakeTimer()

    node.create_timer = create_timer_stub

    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_2",
            action="temporary_wait",
            parameters_json=json.dumps({"duration_sec": 5.0}),
        )
    )

    assert ("cmd-A", "robot_2") not in node._active_waits
    assert ("cmd-A", "robot_2", "COMPLETED", "wait complete") in published


def test_robot_freed_after_terminal_status_allows_new_command():
    calls = []

    class Adapter:
        def __init__(self):
            self.backup_on_result = None

        def backup(self, robot_id, distance_m, on_result=None):
            self.backup_on_result = on_result
            calls.append(("backup", robot_id, distance_m))
            on_result("ACTIVE", "backup started")

    adapter = Adapter()
    node, published = _build_node(adapter)

    node._on_command(_Msg(command_id="cmd-1", robot_id="robot_1", action="yield"))
    adapter.backup_on_result("COMPLETED", "backup complete")

    assert node._in_flight == {}

    node._on_command(_Msg(command_id="cmd-2", robot_id="robot_1", action="yield"))

    assert calls == [("backup", "robot_1", 0.3), ("backup", "robot_1", 0.3)]
    assert ("cmd-2", "robot_1", "ACTIVE", "backup started") in published


class _NavLegAdapter:
    """Adapter double for Nav2-leg watchdog tests: captures send_goal/backup
    callbacks per robot and records cancel() calls so a test can assert the
    watchdog cancelled the hung Nav2 goal."""

    def __init__(self):
        self.on_results: dict[str, callable] = {}
        self.backup_on_result: dict[str, callable] = {}
        self.cancel_calls: list[str] = []

    def send_goal(self, robot_id, x, y, yaw, on_result=None):
        self.on_results[robot_id] = on_result

    def backup(self, robot_id, distance_m, on_result=None):
        self.backup_on_result[robot_id] = on_result

    def cancel(self, robot_id):
        self.cancel_calls.append(robot_id)


def _dispatch_nav_leg(node, command_id="nav-1", timeout_sec=0.0):
    node._on_command(
        _Msg(
            command_id=command_id,
            robot_id="robot_1",
            action="navigate",
            parameters_json=json.dumps({"goal": {"x": 1.0, "y": 2.0}}),
            timeout_sec=timeout_sec,
        )
    )


def test_nav_watchdog_armed_when_nav_leg_goes_active():
    adapter = _NavLegAdapter()
    node, _published = _build_node(adapter)

    _dispatch_nav_leg(node)
    adapter.on_results["robot_1"]("ACTIVE", "goal accepted")

    assert ("nav-1", "robot_1") in node._nav_watchdogs


def test_nav_watchdog_deadline_is_three_times_command_timeout(monkeypatch):
    monkeypatch.setattr(_command_bus_node_mod.time, "monotonic", lambda: 1000.0)
    adapter = _NavLegAdapter()
    node, _published = _build_node(adapter)

    _dispatch_nav_leg(node, timeout_sec=100.0)
    adapter.on_results["robot_1"]("ACTIVE", "goal accepted")

    deadline, _command = node._nav_watchdogs[("nav-1", "robot_1")]
    assert deadline == 1000.0 + 300.0


def test_nav_watchdog_deadline_floors_at_120s_when_timeout_absent(monkeypatch):
    monkeypatch.setattr(_command_bus_node_mod.time, "monotonic", lambda: 1000.0)
    adapter = _NavLegAdapter()
    node, _published = _build_node(adapter)

    # timeout_sec=0.0 means "absent" on the wire; the floor must apply.
    _dispatch_nav_leg(node, timeout_sec=0.0)
    adapter.on_results["robot_1"]("ACTIVE", "goal accepted")

    deadline, _command = node._nav_watchdogs[("nav-1", "robot_1")]
    assert deadline == 1000.0 + 120.0


def test_nav_watchdog_expiry_fails_command_and_cancels_goal(monkeypatch):
    now = {"value": 1000.0}
    monkeypatch.setattr(
        _command_bus_node_mod.time, "monotonic", lambda: now["value"]
    )
    adapter = _NavLegAdapter()
    node, published = _build_node(adapter)

    _dispatch_nav_leg(node)
    adapter.on_results["robot_1"]("ACTIVE", "goal accepted")

    now["value"] = 1000.0 + 120.0
    node._sweep_nav_watchdogs()

    assert ("nav-1", "robot_1", "FAILED", "nav2 leg timed out") in published
    assert adapter.cancel_calls == ["robot_1"]
    assert node._in_flight == {}
    assert node._nav_watchdogs == {}


def test_nav_watchdog_does_not_fire_before_deadline(monkeypatch):
    now = {"value": 1000.0}
    monkeypatch.setattr(
        _command_bus_node_mod.time, "monotonic", lambda: now["value"]
    )
    adapter = _NavLegAdapter()
    node, published = _build_node(adapter)

    _dispatch_nav_leg(node)
    adapter.on_results["robot_1"]("ACTIVE", "goal accepted")

    now["value"] = 1000.0 + 119.0
    node._sweep_nav_watchdogs()

    assert all(entry[2] != "FAILED" for entry in published)
    assert ("nav-1", "robot_1") in node._nav_watchdogs


def test_nav_watchdog_disarmed_on_real_terminal_status():
    adapter = _NavLegAdapter()
    node, _published = _build_node(adapter)

    _dispatch_nav_leg(node)
    adapter.on_results["robot_1"]("ACTIVE", "goal accepted")
    adapter.on_results["robot_1"]("COMPLETED", "goal succeeded")

    assert node._nav_watchdogs == {}


def test_nav_watchdog_stale_entry_does_not_double_publish(monkeypatch):
    # Reentrancy guard: if a real terminal already freed the in-flight slot,
    # a leftover watchdog entry must be dropped silently, not fire FAILED.
    monkeypatch.setattr(_command_bus_node_mod.time, "monotonic", lambda: 1000.0)
    adapter = _NavLegAdapter()
    node, published = _build_node(adapter)
    node._nav_watchdogs[("nav-1", "robot_1")] = (
        0.0,
        _Msg(command_id="nav-1", robot_id="robot_1"),
    )

    node._sweep_nav_watchdogs()

    assert published == []
    assert node._nav_watchdogs == {}


def test_pull_off_leg_arms_watchdog_and_disarms_on_result():
    adapter = _NavLegAdapter()
    node, _published = _build_node(adapter)

    node._on_command(
        _Msg(
            command_id="cmd-Y",
            robot_id="robot_1",
            action="yield",
            parameters_json=json.dumps(
                {
                    "backup_distance_m": 0.8,
                    "hold_sec": 12.0,
                    "pull_off_x": -1.4,
                    "pull_off_y": 0.35,
                }
            ),
        )
    )
    adapter.backup_on_result["robot_1"]("COMPLETED", "backup done")

    assert ("cmd-Y", "robot_1") in node._nav_watchdogs

    # Pull-off result arrived (Nav2 not hung): entering the hold phase must
    # disarm even though no terminal status publishes yet (the hold timer
    # owns termination from here).
    adapter.on_results["robot_1"]("COMPLETED", "goal succeeded")

    assert node._nav_watchdogs == {}


def test_nav_watchdog_failure_releases_linked_wait(monkeypatch):
    now = {"value": 1000.0}
    monkeypatch.setattr(
        _command_bus_node_mod.time, "monotonic", lambda: now["value"]
    )
    adapter = _NavLegAdapter()
    node, published = _build_node(adapter)
    node.create_timer = lambda period, cb: _FakeTimer()

    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_2",
            action="temporary_wait",
            parameters_json=json.dumps({"duration_sec": 100.0}),
        )
    )
    node._on_command(
        _Msg(
            command_id="cmd-A",
            robot_id="robot_1",
            action="yield",
            parameters_json=json.dumps(
                {"backup_distance_m": 0.3, "pull_off_x": -1.4, "pull_off_y": 0.35}
            ),
        )
    )
    adapter.backup_on_result["robot_1"]("COMPLETED", "backup done")

    now["value"] = 1000.0 + 120.0
    node._sweep_nav_watchdogs()

    assert ("cmd-A", "robot_1", "FAILED", "nav2 leg timed out") in published
    assert ("cmd-A", "robot_2") not in node._active_waits
    assert ("cmd-A", "robot_2", "COMPLETED", "released: yield failed") in published

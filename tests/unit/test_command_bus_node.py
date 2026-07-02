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
    ):
        self.command_id = command_id
        self.robot_id = robot_id
        self.action = action
        self.parameters_json = parameters_json


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

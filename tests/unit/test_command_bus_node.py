import json

from swarm_execution.command_bus_node import CommandBusNode


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
    node = CommandBusNode.__new__(CommandBusNode)
    calls = []

    class Adapter:
        def cancel(self, robot_id):
            calls.append(("cancel", robot_id))

    node._adapter = Adapter()
    pending = node._dispatch(_Msg(action="temporary_wait"), {"duration_sec": 8.0})

    assert calls == [("cancel", "robot_1")]
    assert pending is False


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

"""prereg-v3 A25: a dynamic-lane yield backs along the axis M3 swept, not its own heading.

The no-admit diagnosis (docs/reports/2026-10-12-no-admit-diagnosis.md):
under a dynamic lane view M3 sweeps a yielder's retreat along the SNAPPED
lane axis (any heading within 30 degrees of it), while M4's
`backup_line_hold` backed it along its own start heading. Two of the six
no-admit yields (E11, E17a; 23 and 18 degrees off the axis) drifted
0.43-0.57 m off the validated path into rack island W and timed out on the
backup's safety deadline. The fix: M3 states the swept line as a world-frame
facing plus the yielder's world yaw at the decision (the escort-heading
pattern, A11(iii)), and M4 holds that line, turned from its own start yaw.

Fixtures (`data/a25_no_admit/yields.json`): every live S1b yield dispatched
in E6-E17 (9), with the decision, the stage-2 label, the decision snapshot
and the dispatched yield. Offline re-grounding reproduces each dispatched
yield exactly, so the fixtures are the live inputs.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from swarm_execution import nav2_adapter
from swarm_execution.nav2_adapter import Nav2Adapter, backup_line_turn

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.maneuver_geometry import backup_line_facing
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    RetreatChoiceDecision,
    RobotStateInput,
    SnapshotFrame,
)
from tests.unit.test_nav2_adapter import _FakeNode, _odom_at
from tests.unit.test_s1_resolvability import _floor, _frame, _reasoner_result

FIXTURES = json.loads(
    (Path(__file__).parent / "data/a25_no_admit/yields.json").read_text(encoding="utf-8")
)["cases"]
CASES = {case["case"]: case for case in FIXTURES}
_REPRODUCED_KEYS = (
    "backup_distance_m",
    "pull_off_lateral_m",
    "retreat_x_m",
    "retreat_y_m",
    "passer_robot_id",
    "crossing_order",
    "hold_sec",
)
# Robot footprint (nav2_params.yaml `footprint`): 0.14 m along the heading,
# 0.18 m across.
_HALF_LENGTH_M = 0.07
_HALF_WIDTH_M = 0.09


def _ground(case: dict[str, Any], **param_updates: Any) -> dict[str, Any]:
    config, params = _floor("s1b")
    if param_updates:
        params = params.model_copy(update=param_updates)
    frame = _frame(case["rows"])
    choice = (
        None
        if case["retreat_choice"] is None
        else RetreatChoiceDecision(retreat_choice=case["retreat_choice"], justification="live")
    )
    return ground_reasoner_result(
        _reasoner_result(CongestionDecision.model_validate(case["decision"])),
        robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        snapshot=frame,
        params=params,
        retreat_choice=choice,
    )


def _yield(command: dict[str, Any]) -> dict[str, Any]:
    return next(a for a in command["actions"] if a["action"] == "yield")


def _row(case: dict[str, Any], robot_id: str) -> dict[str, Any]:
    return next(r for r in case["rows"] if r["robot_id"] == robot_id)


def _wrap(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


# ---- the fixtures are the live inputs ----


@pytest.mark.parametrize("name", sorted(CASES))
def test_regrounding_reproduces_the_dispatched_live_yield(name):
    case = CASES[name]
    grounded = _yield(_ground(case))
    live = case["yield"]
    assert grounded["robot_id"] == live["robot_id"]
    for key in _REPRODUCED_KEYS:
        assert grounded["parameters"].get(key) == live["parameters"].get(key), key


@pytest.mark.parametrize("name", sorted(CASES))
def test_live_retreat_lies_on_the_snapped_axis_not_the_heading(name):
    # The defect's geometry: every dispatched retreat point is start + backup
    # along a world axis + lateral along its left -- never along -heading.
    case = CASES[name]
    params = case["yield"]["parameters"]
    me = _row(case, case["yield"]["robot_id"])
    backup, lateral = params["backup_distance_m"], params["pull_off_lateral_m"]

    def landing(facing: float) -> tuple[float, float]:
        return (
            me["x"] - backup * math.cos(facing) - lateral * math.sin(facing),
            me["y"] - backup * math.sin(facing) + lateral * math.cos(facing),
        )

    target = (params["retreat_x_m"], params["retreat_y_m"])
    on_axis = min(
        math.dist(landing(k * math.pi / 2), target) for k in range(4)
    )
    assert on_axis < 2e-3
    drift = math.dist(landing(me["theta"]), target)
    if name in ("E11", "E14", "E17a"):
        # 18-23 degrees off the axis: the executed retreat missed the
        # validated one by 0.43-0.62 m.
        assert drift > 0.4
    else:
        assert drift < 0.25


# ---- M3: the swept line crosses the boundary ----


@pytest.mark.parametrize("name", sorted(CASES))
def test_dynamic_yield_states_the_swept_backup_facing(name):
    case = CASES[name]
    grounded = _yield(_ground(case))["parameters"]
    me = _row(case, case["yield"]["robot_id"])
    facing = grounded["backup_facing_rad"]
    assert grounded["backup_reference_yaw_rad"] == round(me["theta"], 6)
    # The facing is an axis direction (a snapped lane), within 30 degrees
    # of the yielder's heading.
    assert min(abs(_wrap(facing - k * math.pi / 2)) for k in range(4)) < 1e-6
    assert abs(_wrap(facing - me["theta"])) <= math.radians(30.0) + 1e-9
    # And backing along it, then stepping left by the lateral, lands exactly
    # on the retreat M3 validated.
    backup = grounded["backup_distance_m"]
    lateral = grounded["pull_off_lateral_m"]
    landing = (
        me["x"] - backup * math.cos(facing) - lateral * math.sin(facing),
        me["y"] - backup * math.sin(facing) + lateral * math.cos(facing),
    )
    assert math.dist(landing, (grounded["retreat_x_m"], grounded["retreat_y_m"])) < 2e-3


def test_backup_facing_turns_e11_and_e17a_onto_their_axes():
    e11 = _yield(_ground(CASES["E11"]))["parameters"]
    e17a = _yield(_ground(CASES["E17a"]))["parameters"]
    assert e11["backup_facing_rad"] == 0.0  # backs west along -x, faces +x
    assert math.degrees(_wrap(e11["backup_facing_rad"] - e11["backup_reference_yaw_rad"])) == (
        pytest.approx(22.83, abs=0.01)
    )
    assert e17a["backup_facing_rad"] == round(math.pi / 2, 6)  # backs south along -y
    assert math.degrees(
        _wrap(e17a["backup_facing_rad"] - e17a["backup_reference_yaw_rad"])
    ) == pytest.approx(-18.44, abs=0.01)


@pytest.mark.parametrize("name", sorted(CASES))
def test_backup_facing_changes_nothing_else_in_the_command(name):
    case = CASES[name]
    command = _ground(case)
    stripped = {
        k: v
        for k, v in _yield(command)["parameters"].items()
        if k not in ("backup_facing_rad", "backup_reference_yaw_rad")
    }
    live = dict(case["yield"]["parameters"])
    live.pop("plan_id", None)  # stamped by M5's plan channel, after grounding
    assert stripped == live


@pytest.mark.parametrize("name", sorted(CASES))
def test_switch_off_commands_carry_no_backup_facing(name):
    command = _ground(CASES[name], dynamic_scene_arms=False)
    for action in command["actions"]:
        parameters = action.get("parameters") or {}
        assert "backup_facing_rad" not in parameters
        assert "backup_reference_yaw_rad" not in parameters
        assert "backup_line_hold" not in parameters


def _lane_frame(yielder_theta: float) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=yielder_theta),
            RobotStateInput(robot_id="robot_2", x=0.4, y=0.0, theta=math.pi),
        ],
    )


def _footprint_lane(band: str = "footprint") -> SceneGeometry:
    corridor = CorridorGeometry(
        axis="x", center_m=0.2, half_length_m=0.2, aisle_half_width_m=0.6, occluder_height_m=0.0
    )
    return SceneGeometry(corridor=corridor, rear_room_band=band)


def test_backup_line_facing_is_the_axis_facing_and_the_decision_yaw():
    facing = backup_line_facing(_lane_frame(0.3), "robot_1", "robot_2", _footprint_lane())
    assert facing == (0.0, 0.3)


def test_backup_line_facing_needs_a_dynamic_footprint_view():
    # Declared geometry (aisle band) keeps M4's own-heading line: byte-identity.
    aisle = _footprint_lane("aisle")
    assert backup_line_facing(_lane_frame(0.3), "robot_1", "robot_2", aisle) is None
    assert backup_line_facing(_lane_frame(0.3), "robot_1", "robot_2", None) is None


def test_backup_line_facing_refuses_a_turn_past_45_degrees():
    # A yielder facing away from its partner (`rear_inconsistent`) would need
    # a ~180 degree turn while reversing: keep the legacy line instead.
    assert backup_line_facing(_lane_frame(math.pi), "robot_1", "robot_2", _footprint_lane()) is None
    assert backup_line_facing(
        _lane_frame(math.radians(46.0)), "robot_1", "robot_2", _footprint_lane()
    ) is None
    assert backup_line_facing(
        _lane_frame(math.radians(44.0)), "robot_1", "robot_2", _footprint_lane()
    ) == (0.0, pytest.approx(math.radians(44.0)))


# ---- M4: the line turn ----


def test_backup_line_turn_reads_the_wrapped_turn():
    assert backup_line_turn({"backup_facing_rad": 0.0, "backup_reference_yaw_rad": -0.399}) == (
        pytest.approx(0.399)
    )
    assert backup_line_turn(
        {"backup_facing_rad": math.pi, "backup_reference_yaw_rad": -2.9}
    ) == pytest.approx(_wrap(math.pi + 2.9))


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"backup_facing_rad": 0.0},
        {"backup_reference_yaw_rad": 0.0},
        {"backup_facing_rad": "0.0", "backup_reference_yaw_rad": 0.1},
        {"backup_facing_rad": None, "backup_reference_yaw_rad": 0.1},
        {"backup_facing_rad": float("nan"), "backup_reference_yaw_rad": 0.1},
        {"backup_facing_rad": True, "backup_reference_yaw_rad": 0.1},
        # Past 90 degrees is not a line to hold while reversing.
        {"backup_facing_rad": math.pi, "backup_reference_yaw_rad": 0.0},
    ],
)
def test_backup_line_turn_is_none_unless_well_formed(parameters):
    assert backup_line_turn(parameters) is None


# ---- the executed path, replayed through M4's own controllers ----


def _corners(x: float, y: float, yaw: float) -> list[tuple[float, float]]:
    c, s = math.cos(yaw), math.sin(yaw)
    return [
        (x + dx * c - dy * s, y + dx * s + dy * c)
        for dx, dy in (
            (_HALF_LENGTH_M, _HALF_WIDTH_M),
            (_HALF_LENGTH_M, -_HALF_WIDTH_M),
            (-_HALF_LENGTH_M, -_HALF_WIDTH_M),
            (-_HALF_LENGTH_M, _HALF_WIDTH_M),
        )
    ]


def _overlaps(corners: list[tuple[float, float]], box: tuple[float, ...]) -> bool:
    # Separating-axis test: oriented chassis rectangle vs axis-aligned box.
    x0, x1, y0, y1 = box
    box_pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    axes = [(1.0, 0.0), (0.0, 1.0)]
    for i in range(2):
        ex, ey = corners[i + 1][0] - corners[i][0], corners[i + 1][1] - corners[i][1]
        axes.append((-ey, ex))
    for ax, ay in axes:
        a = [px * ax + py * ay for px, py in corners]
        b = [px * ax + py * ay for px, py in box_pts]
        if max(a) <= min(b) or max(b) <= min(a):
            return False
    return True


def _boxes() -> list[tuple[float, ...]]:
    config, _ = _floor("s1b")
    return [
        (o.x - o.size_x_m / 2, o.x + o.size_x_m / 2, o.y - o.size_y_m / 2, o.y + o.size_y_m / 2)
        for o in config.static_obstacles
    ]


def _replay(case: dict[str, Any], parameters: dict[str, Any]) -> list[tuple[float, float, float]]:
    """Drive M4's backup then sidestep controllers on a unicycle; return the poses.

    World coordinates stand in for odom: the line turn is relative to the
    start yaw, so it is the same in either frame.
    """
    me = _row(case, case["yield"]["robot_id"])
    pose = [me["x"], me["y"], me["theta"]]
    poses = [tuple(pose)]
    node = _FakeNode()
    adapter = Nav2Adapter(node)
    done: list[str] = []
    turn = backup_line_turn(parameters)
    kwargs: dict[str, Any] = {"hold_start_line": True}
    if turn is not None:
        kwargs["line_turn_rad"] = turn

    def run(start) -> None:
        start()
        sub, timer = node.subscriptions[-1], node.timers[-1]
        pub = node.publishers[f"/{case['yield']['robot_id']}/cmd_vel"]
        for _ in range(20000):
            sub.callback(_odom_at(pose[0], pose[1], yaw=pose[2]))
            before = len(done)
            timer.tick()
            if len(done) > before and done[-1] != "ACTIVE":
                return
            twist = pub.messages[-1]
            dt = 0.05
            pose[2] = _wrap(pose[2] + twist.angular.z * dt)
            pose[0] += twist.linear.x * math.cos(pose[2]) * dt
            pose[1] += twist.linear.x * math.sin(pose[2]) * dt
            poses.append(tuple(pose))
        raise AssertionError("controller never terminated")

    robot_id = case["yield"]["robot_id"]
    run(
        lambda: adapter.backup(
            robot_id,
            parameters["backup_distance_m"],
            on_result=lambda status, _detail: done.append(status),
            **kwargs,
        )
    )
    assert done[-1] == "COMPLETED"
    run(
        lambda: adapter.sidestep(
            robot_id,
            parameters["pull_off_lateral_m"],
            on_result=lambda status, _detail: done.append(status),
        )
    )
    assert done[-1] == "COMPLETED"
    return poses


def _first_contact(poses) -> tuple[float, float, float] | None:
    boxes = _boxes()
    for pose in poses:
        corners = _corners(*pose)
        if any(_overlaps(corners, box) for box in boxes):
            return pose
    return None


@pytest.mark.parametrize("name", ["E11", "E17a"])
def test_heading_line_backup_runs_into_island_w_as_it_did_live(name):
    # Red reproduction of the live contact: the pre-fix command (no facing).
    case = CASES[name]
    contact = _first_contact(_replay(case, case["yield"]["parameters"]))
    assert contact is not None
    # Island W is x [-1.30, -0.75], y [-0.70, 0.90].
    assert -1.45 < contact[0] < -0.6


@pytest.mark.parametrize("name", sorted(CASES))
def test_axis_line_backup_and_sidestep_stay_clear_and_land_on_the_retreat(name):
    case = CASES[name]
    parameters = _yield(_ground(case))["parameters"]
    poses = _replay(case, parameters)
    assert _first_contact(poses) is None
    end = poses[-1]
    target = (parameters["retreat_x_m"], parameters["retreat_y_m"])
    assert math.dist(end[:2], target) < 0.06


def test_axis_line_backup_keeps_the_partner_clear_while_it_turns():
    # The initial turn (up to ~23 degrees) swings the chassis next to the
    # exempt partner: it must not close on it below the standoff gap.
    for name in ("E11", "E14", "E17a"):
        case = CASES[name]
        parameters = _yield(_ground(case))["parameters"]
        partner = _row(case, parameters["passer_robot_id"])
        me = _row(case, case["yield"]["robot_id"])
        start_gap = math.dist((me["x"], me["y"]), (partner["x"], partner["y"]))
        gaps = [math.dist(p[:2], (partner["x"], partner["y"])) for p in _replay(case, parameters)]
        assert min(gaps) >= start_gap - 1e-6


def test_line_turn_default_is_the_start_heading_line():
    # Absent turn: bit-identical commands to the pre-A25 start-line hold.
    for turn_kwargs in ({}, {"line_turn_rad": 0.0}):
        node = _FakeNode()
        adapter = Nav2Adapter(node)
        adapter.backup("robot_1", 1.3, hold_start_line=True, **turn_kwargs)
        sub, timer = node.subscriptions[-1], node.timers[-1]
        pub = node.publishers["/robot_1/cmd_vel"]
        sub.callback(_odom_at(2.0, 1.0, yaw=math.pi / 2))
        timer.tick()
        sub.callback(_odom_at(2.1, 0.5, yaw=math.pi / 2))
        timer.tick()
        desired = nav2_adapter.line_hold_yaw(math.pi / 2, (2.0, 1.0), (2.1, 0.5), True)
        assert pub.messages[-1].angular.z == pytest.approx(2.0 * (desired - math.pi / 2))


def test_line_turn_steers_onto_the_turned_line_from_the_first_tick():
    node = _FakeNode()
    adapter = Nav2Adapter(node)
    adapter.backup("robot_1", 1.3, hold_start_line=True, line_turn_rad=0.4)
    sub, timer = node.subscriptions[-1], node.timers[-1]
    pub = node.publishers["/robot_1/cmd_vel"]
    sub.callback(_odom_at(0.0, 0.0, yaw=-0.4))
    timer.tick()
    # Facing -0.4, the line faces 0.0: turn left (clamped) while reversing.
    assert pub.messages[-1].linear.x < 0.0
    assert pub.messages[-1].angular.z == pytest.approx(0.5)


# ---- M4: the command bus hands the turn to the backup ----


def _bus_rig():
    from tests.unit.test_command_bus_node import _BackupKwargsRig

    return _BackupKwargsRig()


_E11_FACING = {"backup_facing_rad": 0.0, "backup_reference_yaw_rad": -0.399}


def test_bus_turns_the_held_line_onto_the_swept_axis():
    rig = _bus_rig()
    rig.command(
        "robot_4", "yield", {"backup_distance_m": 1.395, "backup_line_hold": True, **_E11_FACING}
    )
    assert rig.backups == [("robot_4", 1.395)]
    assert rig.backup_kwargs == [{"hold_start_line": True, "line_turn_rad": pytest.approx(0.399)}]


def test_bus_ignores_the_facing_without_line_hold():
    rig = _bus_rig()
    rig.command("robot_4", "yield", {"backup_distance_m": 1.395, **_E11_FACING})
    assert rig.backup_kwargs == [{}]


def test_bus_ignores_the_facing_on_a_reverse():
    # M3 states it for yields only; a reverse keeps its own start line.
    rig = _bus_rig()
    rig.command(
        "robot_4", "reverse", {"backup_distance_m": 0.9, "backup_line_hold": True, **_E11_FACING}
    )
    assert rig.backup_kwargs == [{"hold_start_line": True}]


def test_bus_ignores_a_malformed_facing():
    rig = _bus_rig()
    rig.command(
        "robot_4",
        "yield",
        {"backup_distance_m": 1.3, "backup_line_hold": True, "backup_facing_rad": "0.0",
         "backup_reference_yaw_rad": -0.4},
    )
    assert rig.backup_kwargs == [{"hold_start_line": True}]

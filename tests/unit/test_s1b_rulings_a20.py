"""prereg-v3 A20: S1b crossing boxes, the heading-lane yield and the echo latch preference.

(1) S1b declares its REAL crossing boxes (island-corner T-junctions,
    `scripts/s1b_layout.py crossing_boxes` + `box_ports`) and the dynamic
    crossing view anchors to the box both robots overlap, per axis.
(2) An ambiguous node-handoff ARRIVER yields along its own heading
    (`grounding=dynamic_arms:heading_lane`), capped at 45 degrees off the
    bearing axis, with the footprint sweep as guard; M4 backs along any
    heading natively.
(3) The echo mock prefers members of an engaged latch pair (two stalled
    robots closer than 0.45 m in the prompt's state block).

Fixtures (`data/s1b_rulings_a20/scenes.json`): S1b Monte Carlo first
conflicts (scripts/s1_mc.py, 2.5 sim-s after the first encounter) and the
first E2 analysis of S1b pilot 1 (the 33 deg handoff arriver).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest

from reasoning.rag.command_grounder import ground_reasoner_result, verify_and_repair_plan
from reasoning.rag.grounding_view import resolve_grounding_view
from reasoning.rag.maneuver_geometry import retreat_axes
from reasoning.rag.scene_geometry import (
    CorridorGeometry,
    JunctionBox,
    SceneGeometry,
    arm_geometry,
    yield_retreat_room_m,
)
from reasoning.vlm.mock_backend import EchoRobot, echo_select
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)
from tests.unit.test_s1_resolvability import _floor, _frame, _reasoner_result

REPO = Path(__file__).resolve().parents[2]
SCENES = json.loads((Path(__file__).parent / "data/s1b_rulings_a20/scenes.json").read_text())


def _stalled(rows: list[dict[str, Any]]) -> list[str]:
    return [r["robot_id"] for r in rows if r["status"] != "MOVING"]


def _decision(involved: list[str], yielder: str | None = None, **extra: Any) -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=involved,
        root_cause="echo",
        strategy="yield",
        justification="echo",
        yield_robot=yielder or involved[0],
        **extra,
    )


def _ground(rows: list[dict[str, Any]], decision: CongestionDecision, floor: str = "s1b"):
    config, params = _floor(floor)
    frame = _frame(rows)
    return ground_reasoner_result(
        _reasoner_result(decision),
        robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        snapshot=frame,
        params=params,
    )


def _refusal(command: dict[str, Any]) -> str | None:
    for action in command["actions"]:
        reason = str((action.get("parameters") or {}).get("reason", ""))
        if reason.startswith("yield refused:"):
            return reason
    return None


# ---- (1) crossing boxes ----


def test_junction_box_measures_its_own_centre_and_half_length_per_axis():
    box = JunctionBox(name="N", x_min_m=-0.75, x_max_m=0.25, y_min_m=0.7, y_max_m=1.8)
    assert (box.center_m("x"), box.half_length_m("x")) == (-0.25, 0.5)
    assert (box.center_m("y"), box.half_length_m("y")) == (1.25, 0.55)
    assert box.contains((0.30, 1.0), margin_m=0.09)
    assert not box.contains((0.30, 1.0))


def test_junction_boxes_need_the_junction_declared():
    corridor = CorridorGeometry(half_length_m=0.6, aisle_half_width_m=0.6, occluder_height_m=0.3)
    box = JunctionBox(name="N", x_min_m=-0.75, x_max_m=0.25, y_min_m=0.7, y_max_m=1.8)
    with pytest.raises(ValueError, match="junction_declared"):
        SceneGeometry(corridor=corridor, junction_boxes=(box,))
    with pytest.raises(ValueError, match="non-positive"):
        JunctionBox(name="bad", x_min_m=1.0, x_max_m=1.0, y_min_m=0.0, y_max_m=1.0)


def test_s1b_overlay_declares_exactly_the_crossing_boxes_the_layout_derives():
    sys.path.insert(0, str(REPO / "scripts"))
    import s1b_layout as layout

    from isaac.scripts.generate_warehouse_map import load_scenario

    scenario = load_scenario(layout.S1B_SCENARIO)
    floor = layout.s1b_floor()
    import s1_mc

    routes = s1_mc.build_routes(floor, "grid")
    derived = layout.box_ports(floor, routes, layout.crossing_boxes(layout._islands(scenario)))
    crossings = {name: info["box"] for name, info in derived.items() if info["crossing"]}
    assert sorted(crossings) == ["N", "NW", "S", "SW"]
    assert not derived["NE"]["crossing"] and not derived["SE"]["crossing"]
    declared = _floor("s1b")[0].scenario_geometry
    assert declared.junction_declared is True
    assert {
        box.name: [box.x_min_m, box.x_max_m, box.y_min_m, box.y_max_m]
        for box in declared.junction_boxes
    } == crossings


def test_crossing_inside_box_n_grounds_on_box_n():
    case = SCENES["s1b_mc_seed36"]
    command = _ground(case["rows"], _decision(_stalled(case["rows"])))
    assert "grounding=dynamic_arms:crossing" in command["degradations"]
    assert "grounding=dynamic_arms:junction_box:N" in command["degradations"]
    assert command["actions"][0]["action"] == "yield"


def test_crossing_view_arms_measure_from_the_box_on_each_axis():
    case = SCENES["s1b_mc_seed36"]
    config, params = _floor("s1b")
    frame = _frame(case["rows"])
    view = resolve_grounding_view(
        _decision(_stalled(case["rows"])), frame, config.scenario_geometry, params
    )
    assert view.geometry is not None and view.geometry.junction_box is not None
    assert view.geometry.junction_box.name == "N"
    for robot_id, arm in view.geometry.arms.items():
        corridor = arm_geometry(view.geometry, robot_id)[0].corridor
        expected = (-0.25, 0.5) if arm.axis == "x" else (1.25, 0.55)
        assert (corridor.axis, corridor.center_m, corridor.half_length_m) == (arm.axis, *expected)


def test_far_apart_crossing_pair_outside_every_box_still_refuses():
    case = SCENES["s1b_mc_seed15"]
    command = _ground(case["rows"], _decision(_stalled(case["rows"])))
    reason = _refusal(command)
    assert reason is not None
    assert reason.startswith("yield refused: no declared junction:")
    assert "no declared junction box (NW, SW, N, S) holds both robots" in reason
    assert not any(a["action"] == "yield" for a in command["actions"])


# ---- (2) heading lane ----


def test_e2_live_command_carried_the_ambiguous_refusal():
    # The stored live command (pilot 1, pre-A20 tree) refused with "ambiguous
    # lane" (no room measured). Its byte reproduction through the production
    # pipeline on 47fde2d is scripts/s1b_live_replay.py's job, not this pin.
    case = SCENES["s1b_e2_live"]
    assert "grounding=dynamic_arms:ambiguous_refused:robot_1:33" in case["live_degradations"]


def test_e2_arriver_now_grounds_a_heading_lane_and_the_sweep_refuses_it():
    # A20(2) converts the 33 deg arriver to a heading lane. Backing along its
    # own heading (WSW-facing, so it backs ENE) clips island_e's SE corner
    # inside the 0.14 m half-width + box margin, so the guard refuses with
    # the measured reason instead of "ambiguous lane".
    case = SCENES["s1b_e2_live"]
    command = _ground(case["rows"], CongestionDecision(**case["decision"]))
    assert "grounding=dynamic_arms:heading_lane:robot_1:33" in command["degradations"]
    assert _refusal(command) == (
        "yield refused: no executable retreat (robot_1 has no retreat candidate surviving "
        "the sweep; robot_2 is the node-handoff occupant, which never yields)"
    )
    assert " 0.00 m" not in _refusal(command)


def test_heading_lane_arriver_backs_along_its_own_heading():
    case = SCENES["s1b_mc_seed10"]
    rows = case["rows"]
    command = _ground(rows, _decision(_stalled(rows)))
    tag = next(t for t in command["degradations"] if "heading_lane" in t)
    arriver = tag.split(":")[2]
    yield_action = command["actions"][0]
    assert yield_action["action"] == "yield" and yield_action["robot_id"] == arriver
    params = yield_action["parameters"]
    assert params["backup_line_hold"] is True
    state = next(r for r in rows if r["robot_id"] == arriver)
    # The retreat pose = backup along -heading, then the lateral step along
    # the robot-frame left of that heading.
    back = (-math.cos(state["theta"]), -math.sin(state["theta"]))
    left = (-math.sin(state["theta"]), math.cos(state["theta"]))
    x = state["x"] + params["backup_distance_m"] * back[0] + params["pull_off_lateral_m"] * left[0]
    y = state["y"] + params["backup_distance_m"] * back[1] + params["pull_off_lateral_m"] * left[1]
    assert (params["retreat_x_m"], params["retreat_y_m"]) == pytest.approx((x, y), abs=1e-3)


def _with_heading(rows: list[dict[str, Any]], robot_id: str, theta: float) -> list[dict[str, Any]]:
    return [dict(r, theta=theta) if r["robot_id"] == robot_id else r for r in rows]


def test_heading_beyond_45_deg_of_the_bearing_axis_keeps_the_refusal():
    # E2's pair bears along x; -125 deg is 35 deg off y (ambiguous) but 55 deg
    # off the x bearing, so backing along it would open the pair sideways.
    case = SCENES["s1b_e2_live"]
    rows = _with_heading(case["rows"], "robot_1", math.radians(-125.0))
    command = _ground(rows, CongestionDecision(**case["decision"]))
    assert not any("heading_lane" in t for t in command["degradations"])
    assert "grounding=dynamic_arms:ambiguous_refused:robot_1:35" in command["degradations"]


def test_arriver_facing_away_from_the_occupant_keeps_the_refusal():
    case = SCENES["s1b_e2_live"]
    rows = _with_heading(case["rows"], "robot_1", math.radians(33.0))
    command = _ground(rows, CongestionDecision(**case["decision"]))
    assert not any("heading_lane" in t for t in command["degradations"])
    assert "grounding=dynamic_arms:ambiguous_refused:robot_1:33" in command["degradations"]


def test_legacy_mode_keeps_the_refusal():
    case = SCENES["s1b_e2_live"]
    config, params = _floor("s1b")
    frame = _frame(case["rows"])
    view = resolve_grounding_view(
        CongestionDecision(**case["decision"]),
        frame,
        config.scenario_geometry,
        params.model_copy(update={"mode": "legacy"}),
    )
    assert view.refusal_reason is not None and "ambiguous lane" in view.refusal_reason


def test_heading_lane_room_equals_the_axis_room_on_an_axis_heading():
    corridor = CorridorGeometry(
        axis="x", center_m=0.5, half_length_m=0.5, aisle_half_width_m=0.6, occluder_height_m=0.0
    )
    axis = SceneGeometry(corridor=corridor, rear_room_band="footprint")
    tilted = axis.model_copy(update={"lane_heading_rad": 0.0})
    boxes = [
        StaticObstacleInput(obstacle_id="a", x=-1.5, y=0.05, size_x_m=0.5, size_y_m=0.5),
        StaticObstacleInput(obstacle_id="b", x=2.5, y=0.0, size_x_m=0.5, size_y_m=2.0),
    ]
    for side in (-1.0, 1.0):
        assert yield_retreat_room_m((0.0, 0.0), side, boxes, tilted) == pytest.approx(
            yield_retreat_room_m((0.0, 0.0), side, boxes, axis)
        )


def test_heading_lane_room_is_measured_along_the_diagonal():
    # A 45 deg lane through the origin; a unit box centred 2 m back along it.
    heading = math.radians(45.0)
    corridor = CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.1, aisle_half_width_m=0.6, occluder_height_m=0.0
    )
    lane = SceneGeometry(corridor=corridor, rear_room_band="footprint", lane_heading_rad=heading)
    d = 2.0
    box = StaticObstacleInput(
        obstacle_id="b", x=-d * math.cos(heading), y=-d * math.sin(heading),
        size_x_m=1.0, size_y_m=1.0,
    )
    room = yield_retreat_room_m((0.0, 0.0), -1.0, [box], lane)
    # The near corner of the box, (-d cos h + 0.5, -d sin h + 0.5), sits on the
    # lane line at along = -(d - 0.5 * sqrt 2); the mouth is at along -0.1.
    assert room == pytest.approx(d - 0.5 * math.sqrt(2.0) - 0.1, abs=1e-9)
    assert yield_retreat_room_m((0.0, 0.0), 1.0, [box], lane) is None


def test_heading_lane_retreat_axes_follow_minus_heading():
    case = SCENES["s1b_e2_live"]
    config, params = _floor("s1b")
    frame = _frame(case["rows"])
    view = resolve_grounding_view(
        CongestionDecision(**case["decision"]), frame, config.scenario_geometry, params
    )
    axes = retreat_axes(frame, "robot_1", "robot_2", view.geometry)
    theta = next(r["theta"] for r in case["rows"] if r["robot_id"] == "robot_1")
    assert axes.retreat == pytest.approx((-math.cos(theta), -math.sin(theta)))


def _plan(involved: list[str], yielder: str) -> CongestionDecision:
    # A self-consistent plan: its yield leg names the decision's yield_robot.
    legs = [ProposedPlanLeg(robot_id=yielder, action="yield")]
    legs += [ProposedPlanLeg(robot_id=r, action="cross") for r in involved if r != yielder]
    ordered = [yielder, *(r for r in involved if r != yielder)]
    return _decision(ordered, yielder, proposed_plan=legs)


def _verify(decision: CongestionDecision, rows: list[dict[str, Any]]):
    config, params = _floor("s1b")
    return verify_and_repair_plan(
        decision,
        _frame(rows),
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        grounding_params=params,
    )


def test_plan_naming_the_heading_lane_arriver_verifies_verbatim_and_matches_dispatch():
    # The A18 identity rule covers the heading lane with no new code: the
    # final yielder is the arriver either way, only its retreat axis differs.
    from reasoning.rag.command_grounder import plan_matches_dispatch

    # The lane pair only: a plan crossing the lane-scoped off-lane robots
    # would hit the registered A18 residual (1), unrelated to the lane.
    rows = SCENES["s1b_mc_seed10"]["rows"]
    pair = ["robot_2", "robot_5"]
    command = _ground(rows, _decision(pair))
    assert "grounding=dynamic_arms:heading_lane:robot_2:43" in command["degradations"]
    assert command["actions"][0]["robot_id"] == "robot_2"
    verified = _verify(_plan(pair, "robot_2"), rows)
    assert verified.provenance == "vlm_verbatim"
    assert plan_matches_dispatch(verified.legs, command, [r["robot_id"] for r in rows])


def test_plan_naming_the_handoff_occupant_is_repaired_onto_the_arriver():
    from reasoning.rag.command_grounder import plan_matches_dispatch

    # The view hands the yield to the arriver whoever the plan names (node
    # handoff), so the identity rule repairs the plan onto it: one swap.
    rows = SCENES["s1b_mc_seed10"]["rows"]
    pair = ["robot_2", "robot_5"]
    command = _ground(rows, _decision(["robot_5", "robot_2"]))
    assert command["actions"][0]["robot_id"] == "robot_2"
    verified = _verify(_plan(pair, "robot_5"), rows)
    assert verified.provenance == "repaired"
    assert [(e.op, e.robot_ids) for e in verified.edits] == [("swap", ("robot_2", "robot_5"))]
    assert next(leg.robot_id for leg in verified.legs if leg.action == "yield") == "robot_2"
    assert plan_matches_dispatch(verified.legs, command, [r["robot_id"] for r in rows])


def test_m4_line_hold_tracks_a_non_axis_backup_line():
    # M4's backup holds the line through its start pose along its START yaw
    # (any yaw) and counts Euclidean odom distance, so a 33 deg backup needs
    # no M4 change. Unicycle-integrate `_tick`'s law from a 0.05 m offset.
    from swarm_execution.nav2_adapter import line_hold_yaw

    start_yaw = math.radians(-147.0)
    start = (0.0, 0.0)
    x, y, yaw = 0.0, 0.05, start_yaw
    dt, speed = 0.05, 0.08
    for _ in range(400):
        desired = line_hold_yaw(start_yaw, start, (x, y), reversing=True)
        error = math.atan2(math.sin(desired - yaw), math.cos(desired - yaw))
        yaw += max(-0.5, min(0.5, 2.0 * error)) * dt
        x -= speed * math.cos(yaw) * dt
        y -= speed * math.sin(yaw) * dt
    cross = -(x - start[0]) * math.sin(start_yaw) + (y - start[1]) * math.cos(start_yaw)
    along = (x - start[0]) * math.cos(start_yaw) + (y - start[1]) * math.sin(start_yaw)
    assert abs(cross) < 0.01
    assert along < -1.5  # backed along -heading, i.e. away from where it faced


# ---- (3) echo latch-pair preference ----


def _echo(*robots: tuple[str, float, float, bool]) -> list[str]:
    return echo_select([EchoRobot(rid, x, y, stalled) for rid, x, y, stalled in robots])


def test_echo_prefers_the_engaged_latch_pair_over_a_dwelling_robot():
    # robot_1 dwells at E (stalled, latch-free); robot_3/robot_4 are latched.
    names = _echo(
        ("robot_1", 2.3, 0.0, True),
        ("robot_2", -2.3, 1.35, False),
        ("robot_3", -1.9, -0.2, True),
        ("robot_4", -1.9, 0.2, True),
    )
    assert names == ["robot_3", "robot_4"]


def test_echo_names_only_the_closest_pair_first_member_yielding():
    # prereg-v3 A21 (supersedes A20(3)'s "every latch-pair member"): ONE
    # cluster, the closest pair's two members; the second pair is dropped.
    names = _echo(
        ("robot_1", 0.0, 0.0, True),
        ("robot_2", 0.40, 0.0, True),
        ("robot_3", 2.0, 0.0, True),
        ("robot_4", 2.0, 0.30, True),
    )
    assert names == ["robot_3", "robot_4"]


def test_echo_falls_back_to_every_stalled_robot_without_a_latch_pair():
    names = _echo(
        ("robot_1", 0.0, 0.0, True),
        ("robot_2", 0.50, 0.0, True),
        ("robot_3", 2.0, 0.0, False),
    )
    assert names == ["robot_1", "robot_2"]


def test_echo_ignores_a_moving_robot_inside_the_latch_radius():
    names = _echo(
        ("robot_1", 0.0, 0.0, True),
        ("robot_2", 0.30, 0.0, False),
        ("robot_3", 3.0, 0.0, True),
    )
    assert names == ["robot_1", "robot_3"]


def test_mc_replay_uses_the_live_echo_selection():
    sys.path.insert(0, str(REPO / "scripts"))
    import s1_grounding_replay

    rows = [
        {"robot_id": "robot_2", "x": 0.40, "y": 0.0, "status": "STOPPED"},
        {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "status": "STOPPED"},
        {"robot_id": "robot_3", "x": 2.0, "y": 0.0, "status": "STOPPED"},
    ]
    assert s1_grounding_replay.echo_names(rows) == ["robot_1", "robot_2"]


def test_state_line_parse_keeps_coordinates_off_the_goal_fields():
    from reasoning.vlm.mock_backend import echo_involved_robots
    from reasoning.vlm.models import PromptPayload

    text = "\n".join(
        [
            "- robot_id=robot_1, x=2.30, y=0.00, theta=3.14, status=STOPPED, "
            "goal_x=-0.25, goal_y=1.35",
            "- robot_id=robot_2, x=-0.20, y=1.35, theta=0.00, status=STOPPED, "
            "goal_x=2.30, goal_y=0.00",
            "- robot_id=robot_3, x=-0.25, y=1.10, theta=1.57, status=STOPPED, "
            "goal_x=2.30, goal_y=0.00",
        ]
    )
    payload = PromptPayload(
        system_prompt="s",
        user_prompt=text,
        image_path="/tmp/x.png",
        known_robot_ids=["robot_1", "robot_2", "robot_3"],
    )
    assert echo_involved_robots(payload) == ["robot_2", "robot_3"]


def test_frame_rows_are_snapshot_states():
    # Guard on the fixture format the tests above rely on.
    frame = _frame(SCENES["s1b_mc_seed36"]["rows"])
    assert isinstance(frame, SnapshotFrame)
    assert all(isinstance(r, RobotStateInput) for r in frame.robots)

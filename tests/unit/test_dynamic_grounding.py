"""Dynamic per-snapshot arms, node-handoff grounding and parked-robot exclusion.

v3 scene design S1 prerequisite 2 (dynamic arms + node handoff) and S2's
parked-robot exclusion, both off by default: `GroundingParams.dynamic_scene_arms`
is False and `SceneGeometry.parked_robots` is None. With both off, every
grounding output must be byte-identical to the pre-change grounder: the
goldens in `data/dynamic_grounding/flags_off_goldens.json` were written by
`_golden_outputs` below on the untouched v3 integration tip (bf7eb73, plus
only the fc_launch recorder commit) before any M3 edit.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import RobotView, SceneSnapshot, TaskAssignment
from swarm_orchestrator.plan_tracker import PlanTracker
from swarm_orchestrator.reasoning_pipeline import InProcessPipeline, build_reasoner_request
from swarm_orchestrator.task_registry import TaskRegistry

from reasoning.rag.command_grounder import (
    CommandGroundingError,
    degradation_cause,
    filter_command_robot_ids,
    ground_junction_clear_phases,
    ground_reasoner_result,
    resolve_yield_roles,
    verify_and_repair_plan,
)
from reasoning.rag.grounding_view import (
    apply_backup_line_hold,
    apply_escort_headings,
    derive_dynamic_arms,
    derive_escort_heading,
    exclude_parked_robots,
    find_node_handoff,
    resolve_grounding_view,
)
from reasoning.rag.maneuver_geometry import GroundingParams, rank_recede_candidates, recede_cost
from reasoning.rag.scene_geometry import ArmGeometry, SceneGeometry, park_offset_m
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)

_GOLDEN = Path(__file__).parent / "data" / "dynamic_grounding" / "flags_off_goldens.json"

Pose = tuple[float, float, float]

# Head-on corridor (head_on_deadlock-like barrier corridor).
_HEAD_ON_GEOMETRY_ARGS: dict[str, Any] = {
    "corridor": {
        "axis": "x",
        "center_m": 0.0,
        "half_length_m": 1.0,
        "aisle_half_width_m": 0.6,
        "occluder_height_m": 0.9,
    }
}
# IB10 four-way junction (the test_junction_release_pull_off fixture).
_IB10_ARMS = {
    "robot_1": {"axis": "x", "side": -1},
    "robot_2": {"axis": "x", "side": 1},
    "robot_3": {"axis": "y", "side": -1},
    "robot_4": {"axis": "y", "side": 1},
}
_IB10_GEOMETRY_ARGS: dict[str, Any] = {
    "corridor": {
        "axis": "x",
        "center_m": 0.0,
        "half_length_m": 0.6,
        "aisle_half_width_m": 0.6,
        "occluder_height_m": 0.0,
    },
    "arms": _IB10_ARMS,
    "junction_recede_offset_m": 1.2,
    "junction_backup_clearance_m": 1.1,
    "junction_recede_stagger_m": 0.2,
    "tracked_extent_m": 1.75,
}
# S1 MAPD-5 plus-floor: the junction box |x|, |y| <= 0.6 at the origin, no
# barrier, no declared arms (the scene doc's "none static" row).
_S1_GEOMETRY_ARGS: dict[str, Any] = {
    "corridor": {
        "axis": "x",
        "center_m": 0.0,
        "half_length_m": 0.6,
        "aisle_half_width_m": 0.6,
        "occluder_height_m": 0.0,
    },
}

_HEAD_ON: dict[str, Pose] = {"robot_1": (-0.2, 0.0, 0.0), "robot_2": (0.2, 0.0, math.pi)}
_IB10: dict[str, Pose] = {
    "robot_1": (-0.2192, -0.0014, 0.0),
    "robot_2": (0.33, 0.0158, math.pi),
    "robot_3": (-0.0208, -0.2583, math.pi / 2),
    "robot_4": (0.0045, 0.2773, -math.pi / 2),
}
# S1 mid-route head-on on the W arm's +0.35 lane, between Wp and the mouth.
_S1_LANE: dict[str, Pose] = {"robot_1": (-1.6, 0.35, 0.0), "robot_2": (-1.2, 0.35, math.pi)}
# S1 node handoff at the N tip (0, 1.55): robot_1 dwells on it, robot_2
# arrives behind it on the N-S arm, both facing north.
_S1_HANDOFF: dict[str, Pose] = {
    "robot_1": (0.0, 1.55, math.pi / 2),
    "robot_2": (0.0, 1.12, math.pi / 2),
}
_NODE_N = (0.0, 1.55)


def _frame(
    poses: dict[str, Pose], goals: dict[str, tuple[float, float]] | None = None
) -> SnapshotFrame:
    goals = goals or {}
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=theta, goal=goals.get(rid))
            for rid, (x, y, theta) in poses.items()
        ],
    )


def _decision(strategy: str, involved: list[str], **extra: Any) -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=involved,
        root_cause="standoff",
        strategy=strategy,
        justification="jam",
        **extra,
    )


def _result(decision: CongestionDecision) -> ReasonerResult:
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)


def _ground(
    decision: CongestionDecision,
    frame: SnapshotFrame,
    geometry: SceneGeometry | None,
    params: GroundingParams | None,
    **kwargs: Any,
) -> Any:
    try:
        return ground_reasoner_result(
            _result(decision),
            robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
            geometry=geometry,
            snapshot=frame,
            params=params,
            **kwargs,
        )
    except CommandGroundingError as exc:
        return f"CommandGroundingError: {exc}"


def _golden_cases() -> dict[str, tuple[CongestionDecision, dict[str, Pose], dict[str, Any] | None]]:
    """Decision, poses and geometry kwargs (None = no geometry) per golden case."""
    two = ["robot_1", "robot_2"]
    four = ["robot_1", "robot_2", "robot_3", "robot_4"]
    cases: dict[str, tuple[CongestionDecision, dict[str, Pose], dict[str, Any] | None]] = {}
    for scene, poses, geometry in (
        ("head_on", _HEAD_ON, _HEAD_ON_GEOMETRY_ARGS),
        ("head_on_nogeom", _HEAD_ON, None),
        ("s1_lane", _S1_LANE, _S1_GEOMETRY_ARGS),
        ("s1_handoff", _S1_HANDOFF, _S1_GEOMETRY_ARGS),
    ):
        for yielder in two:
            cases[f"{scene}_yield_{yielder.replace('robot_', 'r')}"] = (
                _decision("yield", two, yield_robot=yielder), poses, geometry
            )
        cases[f"{scene}_reverse"] = (_decision("reverse", two), poses, geometry)
        cases[f"{scene}_wait"] = (_decision("temporary_wait", two), poses, geometry)
    ib10 = _IB10_GEOMETRY_ARGS
    cases["ib10_junction_clear"] = (_decision("junction_clear", four), _IB10, ib10)
    cases["ib10_yield_r1"] = (_decision("yield", four, yield_robot="robot_1"), _IB10, ib10)
    cases["ib10_reverse"] = (_decision("reverse", ["robot_3", "robot_4"]), _IB10, ib10)
    return cases


_PARAMS: dict[str, GroundingParams | None] = {
    "legacy_none": None,
    "derived": GroundingParams(mode="derived"),
}


def _golden_outputs(params_override: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every flags-off output the goldens pin, JSON-serialized.

    `params_override` re-runs the matrix with extra GroundingParams fields
    (e.g. the dynamic switch explicitly False) on the derived-mode column.
    """
    params_by_name = dict(_PARAMS)
    if params_override:
        params_by_name["derived"] = GroundingParams(mode="derived", **params_override)
    out: dict[str, Any] = {}
    goals = {"robot_1": _NODE_N, "robot_2": _NODE_N}
    for name, (decision, poses, geometry_args) in _golden_cases().items():
        geometry = None if geometry_args is None else SceneGeometry.model_validate(geometry_args)
        frame = _frame(poses, goals if name.startswith("s1_handoff") else None)
        for params_name, params in params_by_name.items():
            for gate in ("off", "swap"):
                key = f"{name}|{params_name}|{gate}"
                out[f"ground|{key}"] = _ground(
                    decision, frame, geometry, params, yield_feasibility_mode=gate
                )
                plan = verify_and_repair_plan(
                    decision,
                    frame,
                    geometry=geometry,
                    yield_feasibility_mode=gate,
                    grounding_params=params,
                )
                out[f"plan|{key}"] = plan.model_dump(mode="json")
                if decision.strategy == "yield":
                    roles = resolve_yield_roles(
                        decision, frame, geometry=geometry, yield_feasibility_mode=gate
                    )
                    out[f"roles|{key}"] = roles.model_dump(mode="json")
        if decision.strategy == "junction_clear" and geometry is not None:
            phases = ground_junction_clear_phases(
                _result(decision),
                snapshot=frame,
                params=GroundingParams(mode="derived"),
                geometry=geometry,
            )
            out[f"phases|{name}"] = phases.model_dump(mode="json")
    return json.loads(json.dumps(out, sort_keys=True))


def test_flags_off_outputs_match_pre_change_goldens():
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert _golden_outputs() == golden


def test_flags_explicitly_off_match_pre_change_goldens():
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert _golden_outputs({"dynamic_scene_arms": False}) == golden


def _without_backup_line_hold(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _without_backup_line_hold(v) for k, v in value.items() if k != "backup_line_hold"
        }
    if isinstance(value, list):
        return [_without_backup_line_hold(v) for v in value]
    return value


def test_dynamic_switch_leaves_junction_clear_on_declared_geometry():
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    on = _golden_outputs({"dynamic_scene_arms": True})
    keys = [k for k in golden if "ib10_junction_clear" in k and "|derived|" in k]
    assert keys
    # `backup_line_hold` is M4 motion-frame semantics (hold your own backup
    # start line), not geometry: stripped here, every declared-geometry
    # number of the composite must still match the goldens under the switch.
    assert {k: _without_backup_line_hold(on[k]) for k in keys} == {k: golden[k] for k in keys}


def test_dynamic_fields_stay_out_of_the_params_dump_when_off():
    assert "dynamic_scene_arms" not in GroundingParams(mode="derived").model_dump()
    assert "dynamic_handoff_radius_m" not in GroundingParams(mode="derived").model_dump()
    dumped = GroundingParams(mode="derived", dynamic_scene_arms=True).model_dump()
    assert dumped["dynamic_scene_arms"] is True
    assert dumped["dynamic_handoff_radius_m"] == 0.5


def test_new_tags_have_a_registered_cause():
    for tag in (
        "grounding=parked_excluded:robot_5",
        "grounding=parked_excluded:robot_5:untracked",
        "grounding=parked_displaced:robot_5",
        "grounding=parked_only:robot_5",
        "grounding=dynamic_arms:lane:x",
        "grounding=dynamic_arms:crossing",
        "grounding=dynamic_arms:ambiguous",
        "grounding=dynamic_arms:unavailable",
        "grounding=dynamic_arms:rear_inconsistent:robot_1",
        "grounding=node_handoff:robot_2->robot_1",
        "grounding=node_handoff_regrounded:robot_1->robot_2",
        "grounding=rear_regrounded:robot_1->robot_2",
        "grounding=rear_exempt:robot_1",
        "grounding=escort_off:robot_1:goal_reached",
    ):
        assert degradation_cause(tag) is None


# ---- dynamic arms: derivation against hand-computed geometry ----

_DYNAMIC = GroundingParams(mode="derived", dynamic_scene_arms=True)
_S1 = SceneGeometry.model_validate(_S1_GEOMETRY_ARGS)
_TWO = ["robot_1", "robot_2"]


def _derive(poses, decision, goals=None, geometry=_S1, references=None):
    return derive_dynamic_arms(decision, _frame(poses, goals), geometry, _DYNAMIC, references)


def test_mid_route_lane_jam_derives_corridor_from_the_pair():
    # W arm, +0.35 lane: robot_1 at x=-1.6 facing east, robot_2 at x=-1.2
    # facing west. Midpoint -1.4, half-separation 0.2, no occluder.
    decision, geometry, tags = _derive(_S1_LANE, _decision("yield", _TWO, yield_robot="robot_1"))
    assert tags == ["grounding=dynamic_arms:lane:x"]
    assert decision.yield_robot == "robot_1"
    corridor = geometry.corridor
    assert (corridor.axis, corridor.center_m, corridor.half_length_m) == ("x", -1.4, 0.2)
    assert corridor.occluder_height_m == 0.0
    assert corridor.aisle_half_width_m == 0.6
    assert geometry.arms is None and geometry.tracked_extent_m is None
    # Park offset = 0.2 * (3 - 0.21) / 3 + 0.06 + 0.4 = 0.646 from the midpoint.
    assert park_offset_m(geometry) == pytest.approx(0.646)


def test_mid_route_lane_yield_retreats_away_from_partner_with_head_on_backup():
    command = _ground(
        _decision("yield", _TWO, yield_robot="robot_1"),
        _frame(_S1_LANE, {"robot_2": _NODE_WP}),
        _S1,
        _DYNAMIC,
    )
    yield_action = command["actions"][0]
    params = yield_action["parameters"]
    assert yield_action["robot_id"] == "robot_1"
    # Clearance 1.7 from a passer 0.4 m ahead: 1.3 m; it backs WEST (-x).
    assert params["backup_distance_m"] == 1.3
    assert params["retreat_x_m"] == pytest.approx(-2.9)
    # Passer travel past the parked yielder (|-1.2 - -2.9| = 1.7) + 0.65.
    assert params["passer_escort_distance_m"] == pytest.approx(2.35)
    # Escorted west, toward its goal Wp (A11(iii)), from its west heading.
    assert params["passer_escort_heading_rad"] == pytest.approx(math.pi, abs=1e-6)
    assert params["passer_escort_reference_yaw_rad"] == pytest.approx(math.pi, abs=1e-6)
    assert command["degradations"][-1] == "grounding=dynamic_arms:lane:x"


def test_declared_geometry_refuses_the_same_lane_jam():
    # Why S1 needs the switch: the declared junction corridor puts both lane
    # robots beyond its west mouth, so the same yield is refused.
    command = _ground(
        _decision("yield", _TWO, yield_robot="robot_1"),
        _frame(_S1_LANE),
        _S1,
        GroundingParams(mode="derived"),
    )
    assert {a["action"] for a in command["actions"]} == {"temporary_wait"}


def test_mid_route_jam_on_a_north_south_arm_derives_a_y_lane():
    poses = {"robot_1": (0.0, -1.3, math.pi / 2), "robot_2": (0.0, -0.9, -math.pi / 2)}
    _, geometry, tags = _derive(poses, _decision("yield", _TWO, yield_robot="robot_1"))
    assert tags == ["grounding=dynamic_arms:lane:y"]
    corridor = geometry.corridor
    assert (corridor.axis, corridor.center_m, corridor.half_length_m) == ("y", -1.1, 0.2)


def test_crossing_conflict_derives_arms_from_headings_on_the_declared_box():
    # W-lane robot heading east meets an S-arm robot heading north.
    poses = {"robot_1": (-0.45, 0.35, 0.0), "robot_2": (0.05, -0.45, math.pi / 2)}
    _, geometry, tags = _derive(poses, _decision("yield", _TWO, yield_robot="robot_1"))
    assert tags == ["grounding=dynamic_arms:crossing"]
    assert geometry.arms == {
        "robot_1": ArmGeometry(axis="x", side=-1),
        "robot_2": ArmGeometry(axis="y", side=-1),
    }
    # Bearing (0.5, -0.8) is y-major; centre and box stay the declared ones.
    assert geometry.corridor.axis == "y"
    assert (geometry.corridor.center_m, geometry.corridor.half_length_m) == (0.0, 0.6)


def test_crossing_yield_backs_out_along_own_arm_and_passer_leaves_the_box():
    poses = {"robot_1": (-0.45, 0.35, 0.0), "robot_2": (0.05, -0.45, math.pi / 2)}
    command = _ground(
        _decision("yield", _TWO, yield_robot="robot_1"),
        _frame(poses, {"robot_2": _NODE_N}),
        _S1,
        _DYNAMIC,
    )
    params = command["actions"][0]["parameters"]
    # Passer 0.5 m ahead along -x: clearance 1.7 -> 1.2 m backup, west.
    assert params["backup_distance_m"] == 1.2
    assert params["retreat_x_m"] == pytest.approx(-1.65)
    # robot_2 drives north to the far mouth (+0.6): 1.05 m + 0.65 clearance.
    assert params["passer_escort_distance_m"] == pytest.approx(1.7)
    # Along its own arm toward its goal N.
    assert params["passer_escort_heading_rad"] == pytest.approx(math.pi / 2, abs=1e-6)


def test_heading_between_axes_keeps_declared_geometry():
    poses = {"robot_1": (-0.3, 0.3, math.pi / 4), "robot_2": (0.2, -0.2, math.pi)}
    decision = _decision("yield", _TWO, yield_robot="robot_1")
    out_decision, geometry, tags = _derive(poses, decision)
    assert geometry is _S1 and out_decision is decision
    assert tags == ["grounding=dynamic_arms:ambiguous"]


def test_parallel_lanes_side_by_side_keep_declared_geometry():
    # Both on x lanes but displaced across the aisle: no lane conflict.
    poses = {"robot_1": (-1.5, 0.35, 0.0), "robot_2": (-1.4, -0.35, 0.0)}
    _, geometry, tags = _derive(poses, _decision("yield", _TWO, yield_robot="robot_1"))
    assert geometry is _S1
    assert tags == ["grounding=dynamic_arms:ambiguous"]


def test_partner_missing_from_snapshot_keeps_declared_geometry():
    poses = {"robot_1": _S1_LANE["robot_1"]}
    _, geometry, tags = _derive(poses, _decision("yield", _TWO, yield_robot="robot_1"))
    assert geometry is _S1
    assert tags == ["grounding=dynamic_arms:unavailable"]


def test_yielder_facing_away_from_partner_is_swapped_for_the_partner():
    # Same-direction pair away from any node: robot_1 leads (facing east,
    # away from robot_2), so M4 would back it into robot_2.
    poses = {"robot_1": (-1.0, 0.35, 0.0), "robot_2": (-1.45, 0.35, 0.0)}
    decision, geometry, tags = _derive(poses, _decision("yield", _TWO, yield_robot="robot_1"))
    assert decision.yield_robot == "robot_2"
    assert decision.involved_robots == ["robot_2", "robot_1"]
    assert tags == [
        "grounding=rear_regrounded:robot_1->robot_2",
        "grounding=dynamic_arms:lane:x",
    ]
    assert geometry.corridor.center_m == pytest.approx(-1.225)


def test_lane_reverse_exempts_the_robot_that_would_back_into_its_partner():
    poses = {"robot_1": (-1.0, 0.35, 0.0), "robot_2": (-1.45, 0.35, 0.0)}
    command = _ground(_decision("reverse", _TWO), _frame(poses), _S1, _DYNAMIC)
    assert [a["robot_id"] for a in command["actions"]] == ["robot_2"]
    assert "grounding=rear_exempt:robot_1" in command["degradations"]


def test_head_on_lane_reverse_backs_both_robots():
    command = _ground(_decision("reverse", _TWO), _frame(_S1_LANE), _S1, _DYNAMIC)
    assert [a["robot_id"] for a in command["actions"]] == ["robot_1", "robot_2"]
    assert command["degradations"] == ["grounding=dynamic_arms:lane:x"]


def test_rear_room_from_declared_obstacles_still_gates_the_lane_yielder():
    # The feasibility gate measures the yielder's rear room from the dynamic
    # lane mouth: a block 0.3 m behind robot_1 hands the yield to robot_2.
    wall = StaticObstacleInput(
        obstacle_id="w", x=-2.0, y=0.35, size_x_m=0.2, size_y_m=1.2, height_m=0.5
    )
    command = _ground(
        _decision("yield", _TWO, yield_robot="robot_1"),
        _frame(_S1_LANE),
        _S1,
        _DYNAMIC,
        static_obstacles=[wall],
        yield_feasibility_mode="swap",
    )
    assert command["actions"][0]["robot_id"] == "robot_2"
    assert "yield_robot=regrounded" in command["degradations"]


# ---- node handoff with the task-stream registry ----

_NODE_S = (0.0, -1.55)
_NODE_WP = (-2.3, 0.35)


def _stream_registry() -> TaskRegistry:
    # robot_1 started on S, robot_2 on Wp (their `initial_tasks`-era goals);
    # the stream then advanced both to N, robot_2 while a yield it was
    # dispatched still held its override.
    registry = TaskRegistry()
    registry.load_assignments(
        {
            "robot_1": TaskAssignment(task="pickup", goal=_NODE_S),
            "robot_2": TaskAssignment(task="pickup", goal=_NODE_WP),
        }
    )
    registry.set_base("robot_1", "delivery", _NODE_N)
    registry.set_override("robot_2", "yield", _NODE_WP, "c1")
    registry.set_base("robot_2", "delivery", _NODE_N)
    return registry


def test_mission_goal_is_the_current_task_node_under_an_override():
    registry = _stream_registry()
    assert registry.mission_goal("robot_2") == _NODE_N
    assert registry.effective("robot_2") == ("yield", _NODE_WP)
    assert registry.mission_goal("robot_9") is None


def test_handoff_uses_the_registry_task_node_not_the_stale_override():
    registry = _stream_registry()
    effective = {rid: registry.effective(rid)[1] for rid in _TWO}
    frame = _frame(_S1_HANDOFF, effective)
    decision = _decision("yield", _TWO, yield_robot="robot_1")
    # The snapshot's goals are the effective (stale) ones: no handoff.
    assert find_node_handoff(decision, frame, 0.5) is None
    references = {rid: registry.mission_goal(rid) for rid in _TWO}
    assert find_node_handoff(decision, frame, 0.5, references) == ("robot_2", "robot_1")


def test_handoff_regrounds_the_yield_to_the_arriver():
    references = {"robot_1": _NODE_N, "robot_2": _NODE_N}
    command = _ground(
        _decision("yield", _TWO, yield_robot="robot_1"),
        _frame(_S1_HANDOFF),
        _S1,
        _DYNAMIC,
        goal_references=references,
    )
    yield_action = command["actions"][0]
    assert yield_action["robot_id"] == "robot_2"
    params = yield_action["parameters"]
    assert params["passer_robot_id"] == "robot_1"
    # Inward: from y=1.12, clearance 1.7 from the occupant 0.43 m ahead.
    assert params["backup_distance_m"] == pytest.approx(1.27)
    assert params["retreat_y_m"] == pytest.approx(-0.15)
    # The occupant's goal is still the node it sits on (its dwell has not
    # ended): no goal bearing, so it is not escorted (A11(iii)).
    assert "passer_escort_distance_m" not in params
    assert command["degradations"][-4:] == [
        "grounding=node_handoff:robot_2->robot_1",
        "grounding=node_handoff_regrounded:robot_1->robot_2",
        "grounding=dynamic_arms:lane:y",
        "grounding=escort_off:robot_1:goal_reached",
    ]


def test_handoff_holds_after_the_occupant_goal_advances():
    # The occupant's dwell ended and its next task (S) was issued; it still
    # sits on N, and the arriver's current node is still N.
    references = {"robot_1": _NODE_S, "robot_2": _NODE_N}
    decision = _decision("yield", _TWO, yield_robot="robot_2")
    frame = _frame(_S1_HANDOFF)
    assert find_node_handoff(decision, frame, 0.5, references) == ("robot_2", "robot_1")
    _, _, tags = derive_dynamic_arms(decision, frame, _S1, _DYNAMIC, references)
    assert tags == ["grounding=node_handoff:robot_2->robot_1", "grounding=dynamic_arms:lane:y"]


def test_handoff_reverse_leaves_the_occupant_exempt():
    references = {"robot_1": _NODE_N, "robot_2": _NODE_N}
    command = _ground(
        _decision("reverse", _TWO),
        _frame(_S1_HANDOFF),
        _S1,
        _DYNAMIC,
        goal_references=references,
    )
    assert [(a["robot_id"], a["action"]) for a in command["actions"]] == [
        ("robot_2", "reverse")
    ]
    assert command["degradations"] == ["grounding=node_handoff:robot_2->robot_1"]


def test_no_handoff_without_an_occupied_node():
    references = {"robot_1": _NODE_S, "robot_2": _NODE_WP}
    decision = _decision("yield", _TWO, yield_robot="robot_1")
    assert find_node_handoff(decision, _frame(_S1_LANE), 0.5, references) is None


def test_plan_verifier_audits_the_handoff_roles():
    references = {"robot_1": _NODE_N, "robot_2": _NODE_N}
    plan = verify_and_repair_plan(
        _decision("yield", _TWO, yield_robot="robot_1"),
        _frame(_S1_HANDOFF),
        geometry=_S1,
        grounding_params=_DYNAMIC,
        goal_references=references,
    )
    assert [(leg.robot_id, leg.action) for leg in plan.legs] == [
        ("robot_2", "yield"),
        ("robot_1", "cross"),
    ]


def test_plan_naming_the_occupant_is_not_called_inconsistent():
    # M3, not the model, re-grounded the yield: the model's self-consistent
    # plan is audited against its own decision and stays verbatim; the
    # override shows as a dispatch mismatch instead (next test).
    references = {"robot_1": _NODE_N, "robot_2": _NODE_N}
    decision = _decision(
        "yield",
        _TWO,
        yield_robot="robot_1",
        proposed_plan=[
            ProposedPlanLeg(robot_id="robot_1", action="yield"),
            ProposedPlanLeg(robot_id="robot_2", action="cross"),
        ],
    )
    plan = verify_and_repair_plan(
        decision,
        _frame(_S1_HANDOFF),
        geometry=_S1,
        grounding_params=_DYNAMIC,
        goal_references=references,
    )
    assert plan.provenance == "vlm_verbatim"
    assert plan.rejection_stage is None


def _handoff_request(registry: TaskRegistry):
    robots = [
        RobotView(
            robot_id=rid, x=x, y=y, theta=theta, linear_velocity=0.0, status="STOPPED",
            stamp=5.0, goal=registry.effective(rid)[1], task=registry.mission_task(rid),
        )
        for rid, (x, y, theta) in _S1_HANDOFF.items()
    ]
    snapshot = SceneSnapshot(stamp=5.0, frame_id="cam0", robots=robots, dropped_frame=False)
    return build_reasoner_request(request_id="r1", snapshot=snapshot, image_path="/tmp/r1.png")


class _FakeReasoner:
    def __init__(self, result: ReasonerResult) -> None:
        self._result = result

    def run(self, request):
        return self._result


def test_pipeline_feeds_the_registry_task_node_to_grounding():
    registry = _stream_registry()
    seen: dict[str, Any] = {}

    def ground(result, **kwargs):
        seen.update(kwargs)
        return ground_reasoner_result(result, **kwargs)

    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_result(_decision("yield", _TWO, yield_robot="robot_1"))),
        ground_fn=ground,
        scene_geometry=_S1,
        grounding_params=_DYNAMIC,
        stage2_enabled=False,
        goal_reference_of=registry.mission_goal,
    )
    request = _handoff_request(registry)
    outcome = pipe.run(request)
    assert seen["goal_references"] == {"robot_1": _NODE_N, "robot_2": _NODE_N}
    # The prompt still carries the effective goals.
    assert request.robot_states[1].goal == _NODE_WP
    assert outcome.grounded_command["actions"][0]["robot_id"] == "robot_2"
    assert outcome.stage2.yielder_id == "robot_2"


def test_pipeline_reports_the_handoff_override_as_a_dispatch_mismatch():
    registry = _stream_registry()
    decision = _decision(
        "yield",
        _TWO,
        yield_robot="robot_1",
        proposed_plan=[
            ProposedPlanLeg(robot_id="robot_1", action="yield"),
            ProposedPlanLeg(robot_id="robot_2", action="cross"),
        ],
    )
    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_result(decision)),
        ground_fn=ground_reasoner_result,
        scene_geometry=_S1,
        grounding_params=_DYNAMIC,
        stage2_enabled=False,
        plan_tracker=PlanTracker(),
        goal_reference_of=registry.mission_goal,
    )
    outcome = pipe.run(_handoff_request(registry))
    assert outcome.grounded_command["actions"][0]["robot_id"] == "robot_2"
    assert outcome.plan.provenance == "vlm_verbatim"
    assert outcome.plan.dispatch_matches_plan is False


def test_pipeline_passes_no_goal_references_with_the_switch_off():
    registry = _stream_registry()
    seen: dict[str, Any] = {}

    def ground(result, **kwargs):
        seen.update(kwargs)
        return ground_reasoner_result(result, **kwargs)

    pipe = InProcessPipeline(
        reasoner=_FakeReasoner(_result(_decision("yield", _TWO, yield_robot="robot_1"))),
        ground_fn=ground,
        scene_geometry=_S1,
        grounding_params=GroundingParams(mode="derived"),
        stage2_enabled=False,
        goal_reference_of=registry.mission_goal,
    )
    pipe.run(_handoff_request(registry))
    assert "goal_references" not in seen


# ---- S2 parked-robot exclusion in the junction composite ----

# IB10 standoff backed out of the scene doc's S2 composite table (`_fe`):
# robot_1 reverse 0.981 -> x=-1.2, robot_2 0.670 -> x=+1.0, robot_4 0.923 ->
# y=+1.2, robot_3 0.742 -> y=-1.0; robot_5 parked on the east arm at 2.40.
_S2_FE: dict[str, Pose] = {
    "robot_1": (-0.219, 0.0, 0.0),
    "robot_2": (0.330, 0.0, math.pi),
    "robot_3": (0.0, -0.258, math.pi / 2),
    "robot_4": (0.0, 0.277, -math.pi / 2),
    "robot_5": (2.40, 0.0, math.pi),
}
_FIVE = ["robot_1", "robot_2", "robot_3", "robot_4", "robot_5"]


def _s2_geometry(axis: str, *, parked: bool) -> SceneGeometry:
    args = {
        **_IB10_GEOMETRY_ARGS,
        "corridor": {**_IB10_GEOMETRY_ARGS["corridor"], "axis": axis},
        "arms": {**_IB10_ARMS, "robot_5": {"axis": "x", "side": 1}},
    }
    if parked:
        args["parked_robots"] = {"robot_5": (2.40, 0.0)}
    return SceneGeometry.model_validate(args)


def _s2_phases(axis: str, *, parked: bool, involved=_FIVE, poses=_S2_FE):
    return ground_junction_clear_phases(
        _result(_decision("junction_clear", list(involved))),
        snapshot=_frame(poses),
        params=GroundingParams(mode="derived"),
        geometry=_s2_geometry(axis, parked=parked),
    )


def _recedes(plan) -> list[tuple[str, float]]:
    return [
        (phase.robot_id, phase.command["actions"][0]["parameters"]["backup_distance_m"])
        for phase in plan.phases
        if phase.label == "recede"
    ]


def _addressed(plan) -> set[str]:
    commands = [phase.command for phase in plan.phases] + [plan.fallback_command]
    return {action["robot_id"] for command in commands for action in command["actions"]}


def test_mirrored_composite_without_exclusion_lets_the_parked_robot_lead():
    plan = _s2_phases("y", parked=False)
    assert _recedes(plan)[0] == ("robot_5", 0.0)
    assert len(_recedes(plan)) == 3


def test_mirrored_composite_excludes_the_parked_robot_and_keeps_its_follower_weight():
    plan = _s2_phases("y", parked=True)
    assert _recedes(plan) == [("robot_1", 0.981), ("robot_2", 0.67)]
    assert "robot_5" not in _addressed(plan)
    cross = next(phase for phase in plan.phases if phase.label == "cross")
    yield_action = cross.command["actions"][0]
    # Mirrored column: robot_3 backs 0.760 to y=-1.018, robot_4 passes.
    assert (yield_action["robot_id"], yield_action["parameters"]["backup_distance_m"]) == (
        "robot_3",
        0.76,
    )
    assert yield_action["parameters"]["crossing_order"] == ["robot_4"]
    frame = _frame(_S2_FE)
    geometry = _s2_geometry("y", parked=True)
    params = GroundingParams(mode="derived")
    # chi keeps robot_5 as robot_2's follower: 0.870 + 0.5 * 1.
    assert recede_cost(frame, "robot_1", geometry, params) == pytest.approx(0.981)
    assert recede_cost(frame, "robot_2", geometry, params) == pytest.approx(1.370)
    assert rank_recede_candidates(frame, ["robot_1", "robot_2"], geometry, params) == [
        "robot_1",
        "robot_2",
    ]
    commands = [phase.command for phase in plan.phases] + [plan.fallback_command]
    for command in commands:
        assert command["degradations"][-1] == "grounding=parked_excluded:robot_5"


def test_shipped_composite_drops_the_parked_robot_from_the_crossing():
    without = _s2_phases("x", parked=False)
    cross = next(phase for phase in without.phases if phase.label == "cross")
    yield_params = cross.command["actions"][0]["parameters"]
    assert "robot_5" in yield_params["crossing_order"]
    plan = _s2_phases("x", parked=True)
    assert _recedes(plan) == [("robot_4", 0.923), ("robot_3", 0.742)]
    cross = next(phase for phase in plan.phases if phase.label == "cross")
    yield_action = cross.command["actions"][0]
    # The scene doc's shipped column: robot_1 backs 0.799 to the park at
    # x=-1.018 and robot_2 alone is escorted 1.998.
    assert yield_action["robot_id"] == "robot_1"
    assert yield_action["parameters"]["backup_distance_m"] == 0.799
    assert yield_action["parameters"]["retreat_x_m"] == -1.018
    assert yield_action["parameters"]["crossing_order"] == ["robot_2"]
    assert yield_action["parameters"]["passer_escort_distance_m"] == 1.998
    assert "robot_5" not in _addressed(plan)


def test_ground_reasoner_result_tags_phase_zero_once():
    command = ground_reasoner_result(
        _result(_decision("junction_clear", _FIVE)),
        geometry=_s2_geometry("y", parked=True),
        snapshot=_frame(_S2_FE),
        params=GroundingParams(mode="derived"),
    )
    assert command["actions"][0]["robot_id"] == "robot_1"
    assert command["degradations"].count("grounding=parked_excluded:robot_5") == 1


def test_parked_robot_not_named_changes_nothing():
    four = _FIVE[:4]
    with_parked = _s2_phases("y", parked=True, involved=four)
    without = _s2_phases("y", parked=False, involved=four)
    assert with_parked == without


def test_displaced_parked_robot_is_grounded_and_tagged():
    poses = {**_S2_FE, "robot_5": (1.6, 0.0, math.pi)}
    decision, tags = exclude_parked_robots(
        _decision("junction_clear", _FIVE), _frame(poses), _s2_geometry("y", parked=True)
    )
    assert decision.involved_robots == _FIVE
    assert tags == ["grounding=parked_displaced:robot_5"]


def test_untracked_parked_robot_is_excluded_and_tagged():
    poses = {rid: pose for rid, pose in _S2_FE.items() if rid != "robot_5"}
    decision, tags = exclude_parked_robots(
        _decision("junction_clear", _FIVE), _frame(poses), _s2_geometry("y", parked=True)
    )
    assert "robot_5" not in decision.involved_robots
    assert tags == ["grounding=parked_excluded:robot_5:untracked"]


def test_parked_yielder_and_crossing_order_are_cleared():
    decision = _decision(
        "yield", _FIVE, yield_robot="robot_5", crossing_order=list(reversed(_FIVE))
    )
    out, tags = exclude_parked_robots(decision, _frame(_S2_FE), _s2_geometry("x", parked=True))
    assert out.yield_robot is None
    assert out.crossing_order == ["robot_4", "robot_3", "robot_2", "robot_1"]
    assert tags == ["grounding=parked_excluded:robot_5"]


def test_all_parked_decision_is_left_whole_and_tagged():
    decision = _decision("reverse", ["robot_5"])
    out, tags = exclude_parked_robots(decision, _frame(_S2_FE), _s2_geometry("x", parked=True))
    assert out is decision
    assert tags == ["grounding=parked_only:robot_5"]


def test_non_spatial_decision_keeps_the_parked_robot():
    decision = _decision("temporary_wait", _FIVE)
    view = resolve_grounding_view(decision, _frame(_S2_FE), _s2_geometry("x", parked=True))
    assert view.decision is decision and view.tags == ()


def test_plan_verifier_gives_the_parked_robot_no_role():
    plan = verify_and_repair_plan(
        _decision("junction_clear", _FIVE),
        _frame(_S2_FE),
        geometry=_s2_geometry("y", parked=True),
        grounding_params=GroundingParams(mode="derived"),
    )
    legs = {leg.robot_id: leg.action for leg in plan.legs}
    assert legs["robot_5"] == "continue"
    assert [leg.robot_id for leg in plan.legs if leg.action == "reverse"] == [
        "robot_1",
        "robot_2",
    ]


def test_plan_giving_the_parked_robot_a_role_is_repaired_not_rejected():
    decision = _decision(
        "junction_clear",
        _FIVE,
        crossing_order=list(_FIVE),
        proposed_plan=[
            ProposedPlanLeg(robot_id="robot_5", action="reverse"),
            ProposedPlanLeg(robot_id="robot_1", action="reverse"),
            ProposedPlanLeg(robot_id="robot_2", action="reverse"),
            ProposedPlanLeg(robot_id="robot_3", action="yield"),
            ProposedPlanLeg(robot_id="robot_4", action="cross"),
        ],
    )
    plan = verify_and_repair_plan(
        decision,
        _frame(_S2_FE),
        geometry=_s2_geometry("y", parked=True),
        grounding_params=GroundingParams(mode="derived"),
    )
    assert plan.provenance == "repaired"
    assert [(edit.op, edit.robot_ids) for edit in plan.edits] == [("substitute", ("robot_5",))]
    assert {leg.robot_id: leg.action for leg in plan.legs}["robot_5"] == "continue"


def test_empty_parked_list_is_rejected():
    with pytest.raises(ValidationError):
        SceneGeometry.model_validate({**_S1_GEOMETRY_ARGS, "parked_robots": {}})


# ---- escort heading from the passer's current goal (prereg-v3 A11(iii)) ----

_NODE_E = (2.3, 0.0)


def _lane_view(yielder: str, poses=_S1_LANE):
    _, geometry, _ = _derive(poses, _decision("yield", _TWO, yield_robot=yielder))
    return geometry


def test_escort_heading_toward_an_east_goal_is_zero():
    # The backward-compatible value: an eastbound passer's escort is the
    # odom-yaw-0 escort every pre-v3 robot (spawned facing east) ran.
    frame = _frame(_S1_LANE, {"robot_1": _NODE_E})
    heading = derive_escort_heading(
        "robot_1", "robot_2", frame, _lane_view("robot_2"), _DYNAMIC
    )
    assert (heading.heading_rad, heading.reference_yaw_rad, heading.reason) == (0.0, 0.0, None)


def test_escort_heading_toward_a_west_goal_is_pi():
    frame = _frame(_S1_LANE, {"robot_2": _NODE_WP})
    heading = derive_escort_heading(
        "robot_2", "robot_1", frame, _lane_view("robot_1"), _DYNAMIC
    )
    assert heading.heading_rad == pytest.approx(math.pi, abs=1e-6)
    assert heading.reason is None


def test_escort_heading_snaps_a_cornering_goal_to_the_lane_axis():
    # robot_1 on the W lane bound for N: the raw bearing (~40 deg) would
    # drive the escort into the NW rack; it runs east along the lane.
    frame = _frame(_S1_LANE, {"robot_1": _NODE_N})
    heading = derive_escort_heading(
        "robot_1", "robot_2", frame, _lane_view("robot_2"), _DYNAMIC
    )
    assert heading.heading_rad == 0.0


def test_escort_heading_uses_the_registry_goal_not_the_snapshot_goal():
    # The snapshot carries a stale override goal (west); the registry's
    # current task node is east, past the yielder.
    frame = _frame(_S1_LANE, {"robot_1": _NODE_WP})
    heading = derive_escort_heading(
        "robot_1",
        "robot_2",
        frame,
        _lane_view("robot_2"),
        _DYNAMIC,
        goal_references={"robot_1": _NODE_E},
    )
    assert heading.heading_rad == 0.0


def test_handoff_dweller_with_a_new_goal_is_escorted_toward_it():
    # The occupant's dwell on N just ended and its next node (S) was issued
    # while it still sits on N facing north: it is escorted south, a half
    # turn from its heading, past the arriver backing inward.
    references = {"robot_1": _NODE_S, "robot_2": _NODE_N}
    command = _ground(
        _decision("yield", _TWO, yield_robot="robot_2"),
        _frame(_S1_HANDOFF),
        _S1,
        _DYNAMIC,
        goal_references=references,
    )
    yield_action = command["actions"][0]
    params = yield_action["parameters"]
    assert (yield_action["robot_id"], params["passer_robot_id"]) == ("robot_2", "robot_1")
    assert params["passer_escort_heading_rad"] == pytest.approx(-math.pi / 2, abs=1e-6)
    assert params["passer_escort_reference_yaw_rad"] == pytest.approx(math.pi / 2, abs=1e-6)
    assert params["passer_escort_distance_m"] > 0
    assert not any(tag.startswith("grounding=escort_off") for tag in command["degradations"])


def test_escort_heading_reason_goal_reached_for_a_dwelling_occupant():
    frame = _frame(_S1_HANDOFF)
    view = derive_dynamic_arms(
        _decision("yield", _TWO, yield_robot="robot_2"),
        frame,
        _S1,
        _DYNAMIC,
        {"robot_1": _NODE_N, "robot_2": _NODE_N},
    )[1]
    heading = derive_escort_heading(
        "robot_1", "robot_2", frame, view, _DYNAMIC, {"robot_1": _NODE_N}
    )
    assert heading.reason == "goal_reached"


def test_escort_heading_reason_no_goal():
    heading = derive_escort_heading(
        "robot_2", "robot_1", _frame(_S1_LANE), _lane_view("robot_1"), _DYNAMIC
    )
    assert heading.reason == "no_goal"


def test_escort_heading_reason_goal_behind_the_passer():
    # robot_2's escort was sized to pass the parked robot_1 (west); its goal
    # is east, behind it.
    frame = _frame(_S1_LANE, {"robot_2": _NODE_E})
    heading = derive_escort_heading(
        "robot_2", "robot_1", frame, _lane_view("robot_1"), _DYNAMIC
    )
    assert heading.reason == "goal_behind"


def test_escort_heading_reason_goal_straight_across_the_axis():
    poses = {"robot_1": (-0.45, 0.35, 0.0), "robot_2": (0.05, -0.45, math.pi / 2)}
    _, view, _ = _derive(poses, _decision("yield", _TWO, yield_robot="robot_1"))
    frame = _frame(poses, {"robot_2": (2.3, -0.45)})
    heading = derive_escort_heading("robot_2", "robot_1", frame, view, _DYNAMIC)
    assert heading.reason == "goal_off_axis"


def test_escort_heading_reason_untracked_passer():
    frame = _frame({"robot_1": _S1_LANE["robot_1"]})
    heading = derive_escort_heading("robot_2", "robot_1", frame, _S1, _DYNAMIC)
    assert heading.reason == "untracked"


def test_underivable_heading_drops_the_escort_and_tags_it():
    command = _ground(
        _decision("yield", _TWO, yield_robot="robot_1"),
        _frame(_S1_LANE, {"robot_2": _NODE_E}),
        _S1,
        _DYNAMIC,
    )
    params = command["actions"][0]["parameters"]
    assert "passer_escort_distance_m" not in params
    assert "passer_escort_heading_rad" not in params
    # The clearance gate is unchanged: M4 still ends the hold on it.
    assert params["passer_clear_m"] == pytest.approx(2.35)
    assert command["degradations"][-1] == "grounding=escort_off:robot_2:goal_behind"


_ESCORT_YIELD = {
    "command_id": "r1-yield",
    "actions": [
        {
            "robot_id": "robot_1",
            "action": "yield",
            "parameters": {
                "backup_distance_m": 1.3,
                "passer_robot_id": "robot_2",
                "passer_clear_m": 2.35,
                "passer_escort_distance_m": 2.35,
                "crossing_order": ["robot_2", "robot_3"],
                "crossing_clear_m": [2.35, 2.75],
                "crossing_escort_m": [2.35, 2.75],
            },
        },
        {"robot_id": "robot_2", "action": "temporary_wait", "parameters": {"linked_position": 0}},
        {"robot_id": "robot_3", "action": "temporary_wait", "parameters": {"linked_position": 1}},
    ],
    "expected_resolution_time_sec": 150.0,
    "fallback": "stop",
}
_LANE_THREE: dict[str, Pose] = {**_S1_LANE, "robot_3": (-0.8, 0.35, math.pi)}


def test_escort_headings_are_aligned_with_the_crossing_order():
    frame = _frame(_LANE_THREE, {"robot_2": _NODE_WP, "robot_3": _NODE_WP})
    command = apply_escort_headings(_ESCORT_YIELD, frame, _lane_view("robot_1"), _DYNAMIC)
    params = command["actions"][0]["parameters"]
    assert params["passer_escort_heading_rad"] == pytest.approx(math.pi, abs=1e-6)
    assert params["crossing_escort_heading_rad"] == [pytest.approx(math.pi, abs=1e-6)] * 2
    assert params["crossing_escort_reference_yaw_rad"] == [pytest.approx(math.pi, abs=1e-6)] * 2
    assert "degradations" not in command


def test_one_underivable_passer_drops_the_whole_chain_escort():
    frame = _frame(_LANE_THREE, {"robot_2": _NODE_WP})
    command = apply_escort_headings(_ESCORT_YIELD, frame, _lane_view("robot_1"), _DYNAMIC)
    params = command["actions"][0]["parameters"]
    assert "passer_escort_distance_m" not in params and "crossing_escort_m" not in params
    assert params["crossing_clear_m"] == [2.35, 2.75]
    assert command["degradations"] == ["grounding=escort_off:robot_3:no_goal"]


def test_pruned_passer_drops_its_escort_heading_too():
    frame = _frame(_LANE_THREE, {"robot_2": _NODE_WP, "robot_3": _NODE_WP})
    command = apply_escort_headings(_ESCORT_YIELD, frame, _lane_view("robot_1"), _DYNAMIC)
    pruned = filter_command_robot_ids(command, {"robot_1", "robot_2"})
    params = pruned["actions"][0]["parameters"]
    assert params["crossing_order"] == ["robot_2"]
    assert len(params["crossing_escort_heading_rad"]) == 1
    assert len(params["crossing_escort_reference_yaw_rad"]) == 1


def test_switch_off_leaves_the_command_object_untouched():
    frame = _frame(_LANE_THREE, {"robot_2": _NODE_WP, "robot_3": _NODE_WP})
    off = GroundingParams(mode="derived")
    assert apply_escort_headings(_ESCORT_YIELD, frame, _S1, off) is _ESCORT_YIELD
    assert apply_escort_headings(_ESCORT_YIELD, frame, _S1, None) is _ESCORT_YIELD


def test_flags_off_escorts_carry_no_heading_parameter():
    # Byte-compatibility of the M4 contract: no flags-off golden command
    # names the new keys, so M4 runs its odom-yaw-0 escort for all of them.
    golden = _GOLDEN.read_text(encoding="utf-8")
    assert "passer_escort_distance_m" in golden
    assert "escort_heading" not in golden and "escort_reference_yaw" not in golden


def test_junction_clear_escorts_get_headings_under_the_switch():
    goals = {"robot_1": (1.75, 0.0), "robot_2": (-1.75, 0.0)}
    goals |= {"robot_3": (0.0, 1.75), "robot_4": (0.0, -1.75)}
    four = ["robot_1", "robot_2", "robot_3", "robot_4"]
    plan = ground_junction_clear_phases(
        _result(_decision("junction_clear", four)),
        snapshot=_frame(_IB10),
        params=_DYNAMIC,
        geometry=SceneGeometry.model_validate(_IB10_GEOMETRY_ARGS),
        goal_references=goals,
    )
    escorted = [
        action["parameters"]
        for command in [*(p.command for p in plan.phases), plan.fallback_command]
        for action in command["actions"]
        if action["action"] == "yield" and "passer_escort_distance_m" in action["parameters"]
    ]
    assert escorted
    for params in escorted:
        # Every IB10 robot spawned facing its goal: the turn is ~0.
        turn = params["passer_escort_heading_rad"] - params["passer_escort_reference_yaw_rad"]
        assert math.atan2(math.sin(turn), math.cos(turn)) == pytest.approx(0.0, abs=0.05)


# ---- backup line hold (prereg-v3 A11(iii) sibling: spawn-frame backups) ----


def test_dynamic_yield_backup_holds_the_start_line():
    command = _ground(
        _decision("yield", _TWO, yield_robot="robot_1"),
        _frame(_S1_LANE, {"robot_2": _NODE_WP}),
        _S1,
        _DYNAMIC,
    )
    yield_action = command["actions"][0]
    assert yield_action["action"] == "yield"
    assert yield_action["parameters"]["backup_line_hold"] is True


def test_dynamic_reverse_marks_every_reversing_robot():
    command = _ground(_decision("reverse", _TWO), _frame(_S1_LANE), _S1, _DYNAMIC)
    reverses = [a for a in command["actions"] if a["action"] == "reverse"]
    assert len(reverses) == 2
    assert all(a["parameters"]["backup_line_hold"] is True for a in reverses)


def test_switch_off_backup_line_hold_leaves_the_command_object_untouched():
    off = GroundingParams(mode="derived")
    assert apply_backup_line_hold(_ESCORT_YIELD, off) is _ESCORT_YIELD
    assert apply_backup_line_hold(_ESCORT_YIELD, None) is _ESCORT_YIELD


def test_flags_off_backups_carry_no_line_hold_parameter():
    # Byte-compatibility of the M4 contract: no flags-off golden command
    # names the key, so M4 keeps the odom y=0 spawn-line servo for all of
    # them.
    golden = _GOLDEN.read_text(encoding="utf-8")
    assert "backup_distance_m" in golden
    assert "backup_line_hold" not in golden


def test_junction_recede_backups_get_line_hold_with_their_pockets():
    four = ["robot_1", "robot_2", "robot_3", "robot_4"]
    plan = ground_junction_clear_phases(
        _result(_decision("junction_clear", four)),
        snapshot=_frame(_IB10),
        params=_DYNAMIC,
        geometry=SceneGeometry.model_validate(_IB10_GEOMETRY_ARGS),
    )
    recedes = [
        action["parameters"]
        for phase in plan.phases
        for action in phase.command["actions"]
        if action["action"] == "reverse"
    ]
    assert recedes
    for params in recedes:
        # The key rides on the same action whose pocket distance it backs.
        assert params["backup_distance_m"] > 0
        assert params["backup_line_hold"] is True
    holds = [
        action["parameters"]
        for command in [*(p.command for p in plan.phases), plan.fallback_command]
        for action in command["actions"]
        if action["action"] == "yield"
    ]
    assert holds
    assert all(params["backup_line_hold"] is True for params in holds)

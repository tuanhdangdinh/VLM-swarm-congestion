"""Queued corridor-crosser hold (2026-11-15): M3 holds robots a corridor yield leaves out.

Convoy counterflow (docs/reports/2026-11-15-demo-campaign-results.md section 5):
the model's first decision names only the standoff pair, so legacy grounding
commands only those two and the queued robots, released later by M5's start
delay, follow the passer through the gate and latch. With
`hold_queued_crossers` on, a legacy corridor yield also holds every robot it
does not name whose goal lies across the declared corridor, on a linked wait
appended to the crossing order nearest-to-the-gate first, exactly as if the
decision had named it. Off (the default), every command is byte-identical.

The snapshots are the recorded first-trigger frames of live convoy takes 1
(robot_2 yields) and 2 (robot_1 yields), inlined.
"""

from __future__ import annotations

import json

import pytest
from swarm_orchestrator.models import plan_order_status_line
from swarm_orchestrator.plan_tracker import PlanTracker
from swarm_orchestrator.reasoning_pipeline import InProcessPipeline, write_decision_artifact

from reasoning.rag.command_grounder import (
    QUEUED_CROSSER_PREFIX,
    QUEUED_CROSSER_TAG,
    degradation_cause,
    ground_reasoner_result,
    plan_matches_dispatch,
    queued_crosser_outcome,
    verify_and_repair_plan,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import (
    ArmGeometry,
    CorridorGeometry,
    SceneGeometry,
    is_single_corridor,
    traverses_corridor,
)
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)
from tests.unit.test_m5_node_probe import _config, node_env  # noqa: F401

LEGACY = GroundingParams(mode="legacy")
GEOMETRY = SceneGeometry(
    corridor=CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.5, aisle_half_width_m=0.6, occluder_height_m=0.9
    )
)
ALL_FOUR = ["robot_1", "robot_2", "robot_3", "robot_4"]


def _robot(rid: str, x: float, y: float, theta: float, goal: tuple[float, float]):
    return RobotStateInput(
        robot_id=rid, x=x, y=y, theta=theta, status="STOPPED", task="cross_narrow_aisle", goal=goal
    )


# cvD_t01_a1 request 35084986, scene stamp 27.8 (poses rounded to 0.1 mm).
TAKE1 = SnapshotFrame(
    stamp=27.8,
    robots=[
        _robot("robot_2", 0.2212, 0.0033, -3.1172, (-2.0, 0.0)),
        _robot("robot_3", -1.909, 0.0022, 0.0, (2.45, 0.36)),
        _robot("robot_4", -2.4821, 0.0022, 0.0, (1.85, 0.0)),
        _robot("robot_1", -0.1242, -0.0131, 0.0, (2.45, -0.36)),
    ],
)
# cvD_t02_a1 request 759bdb94, scene stamp 28.87.
TAKE2 = SnapshotFrame(
    stamp=28.866666666,
    robots=[
        _robot("robot_3", -1.909, 0.0022, 0.0, (2.45, 0.36)),
        _robot("robot_2", 0.1297, 0.0392, 3.1416, (-2.0, 0.0)),
        _robot("robot_4", -2.4821, 0.0022, 0.0, (1.85, 0.0)),
        _robot("robot_1", -0.1308, -0.0131, -0.0997, (2.45, -0.36)),
    ],
)


def _result(
    yield_robot: str = "robot_2",
    involved: list[str] | None = None,
    crossing_order: list[str] | None = None,
    plan: list[tuple[str, str]] | None = None,
    strategy: str = "yield",
) -> ReasonerResult:
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=involved or ["robot_1", "robot_2"],
        root_cause="head-on standoff in the corridor",
        strategy=strategy,
        justification="j",
        yield_robot=yield_robot if strategy == "yield" else None,
        crossing_order=crossing_order,
        proposed_plan=(
            None
            if plan is None
            else [ProposedPlanLeg(robot_id=rid, action=action) for rid, action in plan]
        ),
    )
    return ReasonerResult(
        request_id="req",
        decision=decision,
        raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="req", backend_id="gemini", attempts=1, parse_status="valid"
        ),
    )


def _ground(result: ReasonerResult, frame: SnapshotFrame = TAKE1, **kwargs):
    positions = {r.robot_id: (r.x, r.y) for r in frame.robots}
    params = kwargs.pop("params", LEGACY)
    geometry = kwargs.pop("geometry", GEOMETRY)
    return ground_reasoner_result(
        result, positions, geometry, snapshot=frame, params=params, **kwargs
    )


def _structure(command: dict) -> dict:
    yields = [a for a in command["actions"] if a["action"] == "yield"]
    linked = {
        a["robot_id"]: a["parameters"]["linked_position"]
        for a in command["actions"]
        if a["action"] == "temporary_wait" and "linked_position" in a["parameters"]
    }
    return {
        "yielder": yields[0]["robot_id"] if yields else None,
        "crossing_order": yields[0]["parameters"].get("crossing_order") if yields else None,
        "linked": linked,
    }


def _without_trace(command: dict) -> dict:
    # The added robots' traceability key and tags are the only intended
    # differences from the command of a decision that named them itself.
    actions = []
    for action in command["actions"]:
        parameters = {
            k: v for k, v in action.get("parameters", {}).items() if k != "queued_crossers_added"
        }
        actions.append({**action, "parameters": parameters})
    stripped = {k: v for k, v in command.items() if k != "degradations"}
    return {**stripped, "actions": actions}


# --- corridor-traversal predicate ------------------------------------------------


def test_traverses_corridor_true_when_goal_beyond_far_mouth():
    assert traverses_corridor((-1.909, 0.0), (2.45, 0.36), GEOMETRY) is True


def test_traverses_corridor_false_when_goal_on_same_side():
    assert traverses_corridor((-1.909, 0.0), (-3.0, 0.36), GEOMETRY) is False


def test_traverses_corridor_false_when_goal_inside_corridor():
    assert traverses_corridor((-1.909, 0.0), (0.4, 0.0), GEOMETRY) is False


def test_traverses_corridor_false_when_robot_inside_corridor():
    assert traverses_corridor((-0.3, 0.0), (2.45, 0.0), GEOMETRY) is False


def test_traverses_corridor_false_when_goal_unknown():
    assert traverses_corridor((-1.909, 0.0), None, GEOMETRY) is False


def test_traverses_corridor_reads_the_declared_axis():
    y_corridor = GEOMETRY.model_copy(
        update={"corridor": GEOMETRY.corridor.model_copy(update={"axis": "y"})}
    )
    assert traverses_corridor((0.0, -1.9), (0.3, 2.0), y_corridor) is True
    assert traverses_corridor((-1.9, 0.0), (2.45, 0.0), y_corridor) is False


def test_traverses_corridor_reads_the_declared_centre():
    shifted = GEOMETRY.model_copy(
        update={"corridor": GEOMETRY.corridor.model_copy(update={"center_m": 3.0})}
    )
    assert traverses_corridor((-1.9, 0.0), (2.45, 0.0), shifted) is False
    assert traverses_corridor((2.0, 0.0), (4.0, 0.0), shifted) is True


def test_is_single_corridor_true_for_a_plain_corridor():
    assert is_single_corridor(GEOMETRY) is True


def test_is_single_corridor_false_with_junction_arms():
    arms = {"robot_1": ArmGeometry(axis="x", side=-1)}
    assert is_single_corridor(GEOMETRY.model_copy(update={"arms": arms})) is False


def test_is_single_corridor_false_with_declared_junction():
    assert is_single_corridor(GEOMETRY.model_copy(update={"junction_declared": True})) is False


def test_is_single_corridor_false_for_a_dynamic_lane_view():
    lane = GEOMETRY.model_copy(update={"lane_robots": ("robot_1", "robot_2")})
    assert is_single_corridor(lane) is False


# --- grounding ---------------------------------------------------------------


def test_hold_grounds_pair_yield_into_full_sequence_when_robot_2_yields():
    command = _ground(_result("robot_2"), hold_queued_crossers=True)
    assert _structure(command) == {
        "yielder": "robot_2",
        "crossing_order": ["robot_1", "robot_3", "robot_4"],
        "linked": {"robot_1": 0, "robot_3": 1, "robot_4": 2},
    }


def test_hold_grounds_pair_yield_into_full_sequence_when_robot_1_yields():
    command = _ground(_result("robot_1"), TAKE2, hold_queued_crossers=True)
    assert _structure(command) == {
        "yielder": "robot_1",
        "crossing_order": ["robot_2", "robot_3", "robot_4"],
        "linked": {"robot_2": 0, "robot_3": 1, "robot_4": 2},
    }


@pytest.mark.parametrize(("frame", "yielder"), [(TAKE1, "robot_2"), (TAKE2, "robot_1")])
def test_hold_equals_command_of_decision_naming_all_four(frame, yielder):
    passer = "robot_1" if yielder == "robot_2" else "robot_2"
    held = _ground(_result(yielder), frame, hold_queued_crossers=True)
    named = _ground(
        _result(yielder, ALL_FOUR, [passer, "robot_3", "robot_4", yielder]), frame
    )
    assert _without_trace(held) == named


def test_hold_tags_each_added_robot():
    command = _ground(_result("robot_2"), hold_queued_crossers=True)
    assert command["degradations"] == [
        f"{QUEUED_CROSSER_TAG}:robot_3:goal_across_corridor",
        f"{QUEUED_CROSSER_TAG}:robot_4:goal_across_corridor",
    ]
    assert all(degradation_cause(tag) is None for tag in command["degradations"])


def test_hold_records_added_robots_on_the_yield():
    command = _ground(_result("robot_2"), hold_queued_crossers=True)
    yield_action = next(a for a in command["actions"] if a["action"] == "yield")
    assert yield_action["parameters"]["queued_crossers_added"] == ["robot_3", "robot_4"]


def test_hold_leaves_model_yielder_and_named_passer_first():
    command = _ground(_result("robot_2", crossing_order=["robot_1", "robot_2"]),
                      hold_queued_crossers=True)
    yield_action = next(a for a in command["actions"] if a["action"] == "yield")
    assert yield_action["robot_id"] == "robot_2"
    assert yield_action["parameters"]["passer_robot_id"] == "robot_1"


def test_hold_orders_added_robots_nearest_to_the_gate_first():
    swapped = SnapshotFrame(
        stamp=TAKE1.stamp,
        robots=[
            r.model_copy(update={"x": {"robot_3": -2.4821, "robot_4": -1.909}.get(r.robot_id, r.x)})
            for r in TAKE1.robots
        ],
    )
    command = _ground(_result("robot_2"), swapped, hold_queued_crossers=True)
    assert _structure(command)["crossing_order"] == ["robot_1", "robot_4", "robot_3"]


def test_hold_leaves_decision_naming_all_four_unchanged():
    result = _result("robot_2", ALL_FOUR, ["robot_1", "robot_3", "robot_4", "robot_2"])
    assert _ground(result, hold_queued_crossers=True) == _ground(result)


def test_hold_skips_robots_whose_goals_stay_on_their_side():
    staying = SnapshotFrame(
        stamp=TAKE1.stamp,
        robots=[
            r.model_copy(update={"goal": (-3.0, 0.0)}) if r.robot_id in ("robot_3", "robot_4")
            else r
            for r in TAKE1.robots
        ],
    )
    result = _result("robot_2")
    assert _ground(result, staying, hold_queued_crossers=True) == _ground(result, staying)


def test_hold_off_is_byte_identical():
    result = _result("robot_2")
    assert _ground(result, hold_queued_crossers=False) == _ground(result)
    assert _structure(_ground(result))["linked"] == {}


def test_hold_keeps_refused_yield_fan_out_on_named_robots():
    # Both robots east of the corridor: the same-side refusal fires as before.
    east = SnapshotFrame(
        stamp=TAKE1.stamp,
        robots=[
            r.model_copy(update={"x": {"robot_1": 0.9, "robot_2": 1.4}.get(r.robot_id, r.x)})
            for r in TAKE1.robots
        ],
    )
    result = _result("robot_2")
    command = _ground(result, east, hold_queued_crossers=True)
    assert command == _ground(result, east)
    assert sorted(a["robot_id"] for a in command["actions"]) == ["robot_1", "robot_2"]


def test_hold_withheld_when_it_would_trip_the_first_passer_check():
    # robot_5 queued just east of the mouth, nearer the yielder than the
    # named passer: holding it would refuse the yield, so the model's pair
    # yield is grounded as without the key and the hold is withheld.
    frame = SnapshotFrame(
        stamp=TAKE1.stamp,
        robots=[*TAKE1.robots, _robot("robot_5", 0.52, 0.0, 3.1416, (-2.5, 0.0))],
    )
    result = _result("robot_2")
    command = _ground(result, frame, hold_queued_crossers=True)
    baseline = _ground(result, frame)
    assert {k: v for k, v in command.items() if k != "degradations"} == baseline
    assert len(command["degradations"]) == 1
    assert command["degradations"][0].startswith(
        "crossing_order=augment_withheld:robot_5,robot_3,robot_4:yield refused: first passer"
    )
    assert degradation_cause(command["degradations"][0]) is None


def test_hold_is_a_no_op_in_derived_mode():
    params = GroundingParams(mode="derived")
    result = _result("robot_2")
    assert _ground(result, params=params, hold_queued_crossers=True) == _ground(
        result, params=params
    )


def test_hold_is_a_no_op_with_junction_arms():
    arms = {
        "robot_1": ArmGeometry(axis="x", side=-1),
        "robot_2": ArmGeometry(axis="x", side=1),
    }
    geometry = GEOMETRY.model_copy(update={"arms": arms})
    result = _result("robot_2")
    assert _ground(result, geometry=geometry, hold_queued_crossers=True) == _ground(
        result, geometry=geometry
    )


def test_hold_is_a_no_op_for_non_yield_strategy():
    result = _result(strategy="temporary_wait")
    assert _ground(result, hold_queued_crossers=True) == _ground(result)


def test_hold_is_a_no_op_without_snapshot():
    result = _result("robot_2")
    positions = {r.robot_id: (r.x, r.y) for r in TAKE1.robots}
    held = ground_reasoner_result(
        result, positions, GEOMETRY, params=LEGACY, hold_queued_crossers=True
    )
    assert held == ground_reasoner_result(result, positions, GEOMETRY, params=LEGACY)


def test_queued_crosser_outcome_lists_added_robots():
    outcome = queued_crosser_outcome(_result("robot_2").decision, TAKE1, GEOMETRY)
    assert outcome.added == ("robot_3", "robot_4")
    assert outcome.withheld_reason is None


# --- plan verification -------------------------------------------------------


def _verify(result: ReasonerResult, frame: SnapshotFrame = TAKE1, **kwargs):
    return verify_and_repair_plan(
        result.decision, frame, geometry=GEOMETRY, grounding_params=LEGACY, **kwargs
    )


_CONTINUE_PLAN = [
    ("robot_2", "yield"), ("robot_1", "cross"), ("robot_3", "continue"), ("robot_4", "continue")
]
_WAIT_PLAN = [("robot_2", "yield"), ("robot_1", "cross"), ("robot_3", "wait"), ("robot_4", "wait")]


def test_verify_off_keeps_continue_plan_verbatim():
    assert _verify(_result("robot_2", plan=_CONTINUE_PLAN)).provenance == "vlm_verbatim"


@pytest.mark.parametrize("plan", [_CONTINUE_PLAN, _WAIT_PLAN])
def test_verify_on_repairs_queued_legs_to_cross(plan):
    verified = _verify(_result("robot_2", plan=plan), hold_queued_crossers=True)
    assert verified.provenance == "repaired"
    assert [(leg.robot_id, leg.action) for leg in verified.legs] == [
        ("robot_2", "yield"), ("robot_1", "cross"), ("robot_3", "cross"), ("robot_4", "cross")
    ]
    assert [(e.op, e.robot_ids) for e in verified.edits] == [
        ("substitute", ("robot_3",)), ("substitute", ("robot_4",))
    ]
    assert all(e.reason.startswith(QUEUED_CROSSER_PREFIX) for e in verified.edits)


@pytest.mark.parametrize("plan", [_CONTINUE_PLAN, _WAIT_PLAN, None])
def test_verify_on_matches_held_dispatch(plan):
    result = _result("robot_2", plan=plan)
    verified = _verify(result, hold_queued_crossers=True)
    command = _ground(result, hold_queued_crossers=True)
    assert plan_matches_dispatch(verified.legs, command, [r.robot_id for r in TAKE1.robots])


def test_verify_on_plan_absent_defaults_queued_robots_to_cross():
    verified = _verify(_result("robot_2"), hold_queued_crossers=True)
    assert verified.provenance == "m3_default"
    actions = {leg.robot_id: leg.action for leg in verified.legs}
    assert actions == {
        "robot_2": "yield", "robot_1": "cross", "robot_3": "cross", "robot_4": "cross"
    }


def test_verify_on_keeps_plan_naming_all_four_verbatim():
    plan = [("robot_2", "yield"), ("robot_1", "cross"), ("robot_3", "cross"), ("robot_4", "cross")]
    result = _result("robot_2", ALL_FOUR, ["robot_1", "robot_3", "robot_4", "robot_2"], plan)
    assert _verify(result, hold_queued_crossers=True) == _verify(result)


def test_verify_on_is_a_no_op_in_derived_mode():
    result = _result("robot_2", plan=_CONTINUE_PLAN)
    derived = GroundingParams(mode="derived")
    on = verify_and_repair_plan(
        result.decision, TAKE1, geometry=GEOMETRY, grounding_params=derived,
        hold_queued_crossers=True,
    )
    off = verify_and_repair_plan(
        result.decision, TAKE1, geometry=GEOMETRY, grounding_params=derived
    )
    assert on == off


# --- M5 pipeline, config, status line, artifact ------------------------------


def _request(frame: SnapshotFrame = TAKE1) -> ReasonerRequest:
    return ReasonerRequest(
        request_id="req",
        image_path="/tmp/req.png",
        frame_id="overhead_camera",
        stamp=frame.stamp,
        robot_states=list(frame.robots),
    )


def _pipeline(**kwargs) -> InProcessPipeline:
    return InProcessPipeline(
        reasoner=None,
        ground_fn=ground_reasoner_result,
        scene_geometry=GEOMETRY,
        grounding_params=LEGACY,
        plan_tracker=PlanTracker(),
        **kwargs,
    )


def test_pipeline_on_dispatches_full_sequence_with_matching_plan():
    outcome = _pipeline(hold_queued_crossers=True)._run_from_result(
        _request(), _result("robot_2", plan=_CONTINUE_PLAN)
    )
    assert _structure(outcome.grounded_command)["linked"] == {
        "robot_1": 0, "robot_3": 1, "robot_4": 2
    }
    assert outcome.plan.provenance == "repaired"
    assert outcome.plan.dispatch_matches_plan is True


def test_pipeline_default_passes_no_hold_argument():
    seen: dict = {}

    def ground_fn(result, robot_positions=None, geometry=None, **kwargs):
        seen.update(kwargs)
        return ground_reasoner_result(result, robot_positions, geometry, **kwargs)

    pipe = InProcessPipeline(
        reasoner=None, ground_fn=ground_fn, scene_geometry=GEOMETRY, grounding_params=LEGACY
    )
    pipe._run_from_result(_request(), _result("robot_2"))
    assert "hold_queued_crossers" not in seen


def test_pipeline_off_dispatch_is_unchanged():
    on = _pipeline()._run_from_result(_request(), _result("robot_2", plan=_CONTINUE_PLAN))
    assert sorted(a["robot_id"] for a in on.grounded_command["actions"]) == ["robot_1", "robot_2"]
    assert on.plan.provenance == "vlm_verbatim"


def test_artifact_records_added_robots_when_on(tmp_path):
    outcome = _pipeline(hold_queued_crossers=True)._run_from_result(
        _request(), _result("robot_2", plan=_CONTINUE_PLAN)
    )
    payload = json.loads(write_decision_artifact(tmp_path, outcome).read_text())
    assert payload["grounding_queued_crossers_added"] == ["robot_3", "robot_4"]


def test_artifact_omits_added_robots_when_off(tmp_path):
    outcome = _pipeline()._run_from_result(_request(), _result("robot_2", plan=_CONTINUE_PLAN))
    payload = json.loads(write_decision_artifact(tmp_path, outcome).read_text())
    assert "grounding_queued_crossers_added" not in payload


def test_config_defaults_off(tmp_path):
    assert _config(tmp_path).grounding_hold_queued_crossers is False


def test_status_line_absent_when_off_by_default(tmp_path):
    assert plan_order_status_line(_config(tmp_path)) is None


def test_status_line_unchanged_when_off(tmp_path):
    config = _config(tmp_path, plan_channel_enabled=True, prompt_held_robot_state=True)
    assert "queued" not in plan_order_status_line(config)


def test_status_line_names_it_when_on(tmp_path):
    config = _config(tmp_path, grounding_hold_queued_crossers=True)
    assert plan_order_status_line(config) == (
        "plan order condition plan_dispatch_order_source=chi "
        "prompt_plan_grammar_rules=False prompt_candidate_options=False "
        "grounding_hold_queued_crossers=True"
    )


def test_default_pipeline_receives_the_key(node_env, tmp_path, monkeypatch):  # noqa: F811
    from swarm_orchestrator.reasoning_pipeline import GroundingParamsSource

    node_module, _ = node_env
    monkeypatch.setattr(node_module, "_load_vlm_config", lambda _b: (_Cfg(), None))
    monkeypatch.setattr(node_module, "_load_vlm_adapter", lambda _b: None)
    monkeypatch.setattr(node_module, "build_backend", lambda _a, _c: object())
    monkeypatch.setattr(node_module, "describe_effective_sampling", lambda _r, _c: None)
    monkeypatch.setattr(node_module, "Reasoner", lambda *a, **k: object())
    monkeypatch.setattr(node_module, "build_retreat_choice_backend", lambda _b, _k: None)
    source = GroundingParamsSource(path="x", section_present=True, params=LEGACY)
    for flag in (False, True):
        config = _config(tmp_path, grounding_hold_queued_crossers=flag)
        pipe = node_module._build_default_pipeline(config, source)
        assert pipe._hold_queued_crossers is flag


class _Cfg:
    def model_copy(self, update):
        return self


@pytest.mark.parametrize("mode", ["swap", "refuse"])
def test_hold_runs_after_the_feasibility_gate_when_gate_on(mode):
    named = _result("robot_2", ALL_FOUR, ["robot_1", "robot_3", "robot_4", "robot_2"])
    held = _ground(_result("robot_2"), yield_feasibility_mode=mode, hold_queued_crossers=True)
    assert _without_trace(held) == _ground(named, yield_feasibility_mode=mode)


def test_hold_adds_nothing_when_the_gate_refuses_the_yield():
    from reasoning.vlm.models import StaticObstacleInput

    # Both robots boxed in: the refuse-mode gate refuses, and the fan-out
    # stays on the named pair.
    boxes = (
        StaticObstacleInput(obstacle_id="w", x=-0.5, y=0.0, size_x_m=0.3, size_y_m=0.3),
        StaticObstacleInput(obstacle_id="e", x=0.6, y=0.0, size_x_m=0.3, size_y_m=0.3),
    )
    result = _result("robot_2")
    kwargs = {"static_obstacles": boxes, "yield_feasibility_mode": "refuse"}
    held = _ground(result, hold_queued_crossers=True, **kwargs)
    assert held == _ground(result, **kwargs)
    assert all(a["action"] == "temporary_wait" for a in held["actions"])

"""Counterflow yielder feasibility (2026-11-15): a corridor yield's crossers must start opposite the yielder.

Convoy counterflow (docs/reports/2026-11-15-convoy-non-arrival-and-yielder-feasibility.md):
legacy multi-passer grounding parks the yielder on its own side of the corridor
and escorts every passer through the gate to that side, past the park point.
A robot that waits on the yielder's side to cross the other way (a queued
platoon member the hold added, or a named passer) stands in the first
passer's exit path, so the escort latches against it. With
`yield_counterflow_swap` on, such a yield is handed to another robot the
decision names, whose crossing robots all start on the far side, with the
model's choice recorded (`yield_robot_grounded_from`); with no such robot the
yield is refused. Off (the default), every command is byte-identical.

The snapshots are the hold tests' inlined first-trigger frames of live convoy
takes 1 (model: robot_2 yields) and 2 (model: robot_1 yields), plus mirrored
and y-axis copies built from take 2.
"""

from __future__ import annotations

import json

import pytest
from swarm_orchestrator.models import plan_order_status_line
from swarm_orchestrator.plan_tracker import PlanTracker
from swarm_orchestrator.reasoning_pipeline import InProcessPipeline, write_decision_artifact

from reasoning.rag.command_grounder import (
    COUNTERFLOW_REFUSED_TAG,
    COUNTERFLOW_REGROUNDED_TAG,
    QUEUED_CROSSER_PREFIX,
    counterflow_crossers,
    counterflow_yield_outcome,
    degradation_cause,
    ground_reasoner_result,
    plan_matches_dispatch,
    verify_and_repair_plan,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import ArmGeometry, CorridorGeometry, SceneGeometry
from reasoning.vlm.models import RobotStateInput, SnapshotFrame
from tests.unit.test_m5_node_probe import _config, node_env  # noqa: F401
from tests.unit.test_queued_crosser_hold import (
    _CONTINUE_PLAN,
    ALL_FOUR,
    GEOMETRY,
    LEGACY,
    TAKE1,
    TAKE2,
    _Cfg,
    _request,
    _result,
    _robot,
    _structure,
)

BOTH = {"hold_queued_crossers": True, "yield_counterflow_swap": True}
HOLD = {"hold_queued_crossers": True}
_ROBOT_1_PLAN = [
    ("robot_1", "yield"), ("robot_2", "cross"), ("robot_3", "continue"), ("robot_4", "continue")
]


def _mirror(frame: SnapshotFrame) -> SnapshotFrame:
    # Mirror x and exchange the standoff pair's ids: the platoon now queues
    # EAST behind robot_2 and travels west, and robot_1 is the counter-flow
    # robot from the west. The feasible yielder is therefore robot_1.
    relabel = {"robot_1": "robot_2", "robot_2": "robot_1"}
    return SnapshotFrame(
        stamp=frame.stamp,
        robots=[
            _robot(
                relabel.get(r.robot_id, r.robot_id), -r.x, r.y, r.theta, (-r.goal[0], r.goal[1])
            )
            for r in frame.robots
        ],
    )


def _transpose(frame: SnapshotFrame) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=frame.stamp,
        robots=[_robot(r.robot_id, r.y, r.x, r.theta, (r.goal[1], r.goal[0])) for r in frame.robots],
    )


MIRRORED = _mirror(TAKE2)
Y_AXIS = _transpose(TAKE2)
Y_GEOMETRY = GEOMETRY.model_copy(
    update={"corridor": GEOMETRY.corridor.model_copy(update={"axis": "y"})}
)


def _shift(frame: SnapshotFrame, dx: float) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=frame.stamp,
        robots=[
            _robot(r.robot_id, r.x + dx, r.y, r.theta, (r.goal[0] + dx, r.goal[1]))
            for r in frame.robots
        ],
    )


SHIFTED = _shift(TAKE2, 3.0)
SHIFTED_GEOMETRY = GEOMETRY.model_copy(
    update={"corridor": GEOMETRY.corridor.model_copy(update={"center_m": 3.0})}
)
# Platoons on both sides: robot_3 queues west (goal east), robot_4 east (goal west).
BOTH_SIDES = SnapshotFrame(
    stamp=28.9,
    robots=[
        _robot("robot_1", -0.1308, -0.0131, 0.0, (2.45, -0.36)),
        _robot("robot_2", 0.1297, 0.0392, 3.1416, (-2.0, 0.0)),
        _robot("robot_3", -1.909, 0.0022, 0.0, (2.45, 0.36)),
        _robot("robot_4", 1.909, 0.0022, 3.1416, (-2.45, 0.36)),
    ],
)
# Every robot past the east mouth: the corridor same-side check refuses the yield.
ALL_EAST = SnapshotFrame(
    stamp=80.0,
    robots=[
        _robot("robot_1", 1.65, 0.0, 0.0, (2.45, -0.36)),
        _robot("robot_2", 1.13, -0.38, 3.14, (-2.0, 0.0)),
        _robot("robot_3", 1.25, 0.18, 0.0, (2.45, 0.36)),
        _robot("robot_4", 0.82, -0.09, 0.0, (1.85, 0.0)),
    ],
)


def _ground(result, frame=TAKE1, geometry=GEOMETRY, **kwargs):
    positions = {r.robot_id: (r.x, r.y) for r in frame.robots}
    params = kwargs.pop("params", LEGACY)
    return ground_reasoner_result(
        result, positions, geometry, snapshot=frame, params=params, **kwargs
    )


def _yield_params(command: dict) -> dict:
    return next(a for a in command["actions"] if a["action"] == "yield")["parameters"]


def _strip_counterflow(command: dict) -> dict:
    # The only intended differences from grounding the feasible yielder
    # directly: the two provenance keys and the counterflow tag.
    actions = []
    for action in command["actions"]:
        parameters = {
            k: v
            for k, v in action.get("parameters", {}).items()
            if k not in ("yield_robot_grounded_from", "yield_regrounded_reason")
        }
        actions.append({**action, "parameters": parameters})
    tags = [t for t in command.get("degradations", []) if not t.startswith(COUNTERFLOW_REGROUNDED_TAG)]
    stripped = {k: v for k, v in command.items() if k != "degradations"}
    return {**stripped, "actions": actions, **({"degradations": tags} if tags else {})}


# --- predicate ------------------------------------------------------------------


def test_counterflow_crossers_lists_queued_robots_on_the_yielders_side():
    positions = {r.robot_id: (r.x, r.y) for r in TAKE2.robots}
    order = ["robot_2", "robot_3", "robot_4"]
    assert counterflow_crossers("robot_1", order, positions, GEOMETRY) == ["robot_3", "robot_4"]


def test_counterflow_crossers_empty_when_every_crosser_starts_opposite():
    positions = {r.robot_id: (r.x, r.y) for r in TAKE2.robots}
    order = ["robot_1", "robot_3", "robot_4"]
    assert counterflow_crossers("robot_2", order, positions, GEOMETRY) == []


def test_counterflow_crossers_ignores_robots_inside_the_corridor():
    positions = {"robot_1": (-0.13, 0.0), "robot_2": (0.13, 0.0), "robot_3": (-0.45, 0.0)}
    assert counterflow_crossers("robot_1", ["robot_2", "robot_3"], positions, GEOMETRY) == []


# --- outcome --------------------------------------------------------------------


def test_outcome_swaps_platoon_side_yielder_to_counterflow_robot():
    outcome = counterflow_yield_outcome(
        _result("robot_1").decision, TAKE2, GEOMETRY, hold_queued_crossers=True
    )
    assert outcome.decision.yield_robot == "robot_2"
    assert outcome.grounded_from == "robot_1"
    assert outcome.regrounded_reason.startswith("yield re-grounded: counterflow:")
    assert "robot_3, robot_4" in outcome.regrounded_reason
    assert outcome.refusal_reason is None


def test_outcome_leaves_feasible_model_yielder_alone():
    outcome = counterflow_yield_outcome(
        _result("robot_2").decision, TAKE1, GEOMETRY, hold_queued_crossers=True
    )
    assert outcome.decision is None and outcome.refusal_reason is None


def test_outcome_is_a_no_op_for_a_pair_yield_without_the_hold():
    # Without the hold only the named passer crosses, and it starts opposite.
    outcome = counterflow_yield_outcome(_result("robot_1").decision, TAKE2, GEOMETRY)
    assert outcome.decision is None and outcome.refusal_reason is None


# --- grounding ------------------------------------------------------------------


@pytest.mark.parametrize("frame", [TAKE1, TAKE2])
def test_swap_grounds_platoon_side_choice_as_counterflow_robot_yield(frame):
    command = _ground(_result("robot_1"), frame, **BOTH)
    assert _structure(command) == {
        "yielder": "robot_2",
        "crossing_order": ["robot_1", "robot_3", "robot_4"],
        "linked": {"robot_1": 0, "robot_3": 1, "robot_4": 2},
    }


@pytest.mark.parametrize("frame", [TAKE1, TAKE2])
def test_swap_equals_hold_only_grounding_of_the_feasible_yielder(frame):
    swapped = _ground(_result("robot_1"), frame, **BOTH)
    direct = _ground(_result("robot_2"), frame, **HOLD)
    assert _strip_counterflow(swapped) == direct


def test_swap_records_model_choice_and_reason_on_the_yield():
    parameters = _yield_params(_ground(_result("robot_1"), TAKE2, **BOTH))
    assert parameters["yield_robot_grounded_from"] == "robot_1"
    assert parameters["yield_regrounded_reason"].startswith("yield re-grounded: counterflow:")


def test_swap_tags_the_command():
    command = _ground(_result("robot_1"), TAKE2, **BOTH)
    tags = [t for t in command["degradations"] if t.startswith(COUNTERFLOW_REGROUNDED_TAG)]
    assert tags == [f"{COUNTERFLOW_REGROUNDED_TAG}:robot_1:robot_2"]
    assert degradation_cause(tags[0]) is None


@pytest.mark.parametrize("frame", [TAKE1, TAKE2])
def test_feasible_model_yielder_is_identical_to_hold_only(frame):
    assert _ground(_result("robot_2"), frame, **BOTH) == _ground(_result("robot_2"), frame, **HOLD)


@pytest.mark.parametrize("yielder", ["robot_1", "robot_2"])
@pytest.mark.parametrize("frame", [TAKE1, TAKE2])
def test_key_off_is_byte_identical_to_hold_only(frame, yielder):
    off = _ground(_result(yielder), frame, yield_counterflow_swap=False, **HOLD)
    assert off == _ground(_result(yielder), frame, **HOLD)


@pytest.mark.parametrize("yielder", ["robot_1", "robot_2"])
def test_both_keys_off_is_byte_identical_to_default(yielder):
    explicit = _ground(
        _result(yielder), TAKE2, hold_queued_crossers=False, yield_counterflow_swap=False
    )
    assert explicit == _ground(_result(yielder), TAKE2)


def test_mirrored_platoon_swaps_to_the_other_robot():
    # Platoon east, counter-flow robot_2 west: robot_2 yielding is now the
    # infeasible choice and robot_1 the feasible one.
    command = _ground(_result("robot_2"), MIRRORED, **BOTH)
    assert _structure(command)["yielder"] == "robot_1"
    assert _structure(command)["crossing_order"] == ["robot_2", "robot_3", "robot_4"]
    assert _yield_params(command)["yield_robot_grounded_from"] == "robot_2"


def test_mirrored_platoon_keeps_the_feasible_choice():
    assert _ground(_result("robot_1"), MIRRORED, **BOTH) == _ground(
        _result("robot_1"), MIRRORED, **HOLD
    )


def test_y_axis_corridor_swaps_on_the_declared_axis():
    command = _ground(_result("robot_1"), Y_AXIS, Y_GEOMETRY, **BOTH)
    assert _structure(command)["yielder"] == "robot_2"


def test_shifted_corridor_centre_swaps_on_the_declared_centre():
    command = _ground(_result("robot_1"), SHIFTED, SHIFTED_GEOMETRY, **BOTH)
    assert _structure(command)["yielder"] == "robot_2"


def test_named_all_four_with_platoon_side_yielder_is_swapped():
    result = _result("robot_1", ALL_FOUR, ["robot_2", "robot_3", "robot_4", "robot_1"])
    for keys in (BOTH, {"yield_counterflow_swap": True}):
        command = _ground(result, TAKE2, **keys)
        assert _structure(command) == {
            "yielder": "robot_2",
            "crossing_order": ["robot_1", "robot_3", "robot_4"],
            "linked": {"robot_1": 0, "robot_3": 1, "robot_4": 2},
        }


def test_named_all_four_swap_equals_named_all_four_feasible_yielder():
    wrong = _result("robot_1", ALL_FOUR, ["robot_2", "robot_3", "robot_4", "robot_1"])
    right = _result("robot_2", ALL_FOUR, ["robot_1", "robot_3", "robot_4", "robot_2"])
    swapped = _ground(wrong, TAKE2, yield_counterflow_swap=True)
    assert _strip_counterflow(swapped) == _ground(right, TAKE2)


def test_platoons_on_both_sides_refuse_the_yield():
    command = _ground(_result("robot_1"), BOTH_SIDES, **BOTH)
    assert {a["action"] for a in command["actions"]} == {"temporary_wait"}
    assert sorted(a["robot_id"] for a in command["actions"]) == ["robot_1", "robot_2"]
    reason = command["actions"][0]["parameters"]["reason"]
    assert reason.startswith("yield refused: counterflow:")
    refused = [t for t in command["degradations"] if t.startswith(COUNTERFLOW_REFUSED_TAG)]
    assert refused == [f"{COUNTERFLOW_REFUSED_TAG}:robot_1"]
    assert degradation_cause(refused[0]) == "infeasible_geometry"


def test_existing_same_side_refusal_is_unchanged():
    result = _result("robot_2", ["robot_2", "robot_4"])
    assert _ground(result, ALL_EAST, **BOTH) == _ground(result, ALL_EAST, **HOLD)


@pytest.mark.parametrize("mode", ["swap", "refuse"])
def test_room_gate_modes_compose_without_obstacles(mode):
    gated = _ground(_result("robot_1"), TAKE2, yield_feasibility_mode=mode, **BOTH)
    assert _strip_counterflow(gated) == _ground(
        _result("robot_2"), TAKE2, yield_feasibility_mode=mode, **HOLD
    )


def test_is_a_no_op_in_derived_mode():
    derived = GroundingParams(mode="derived")
    on = _ground(_result("robot_1"), TAKE2, params=derived, **BOTH)
    assert on == _ground(_result("robot_1"), TAKE2, params=derived, **HOLD)


def test_is_a_no_op_with_junction_arms():
    arms = GEOMETRY.model_copy(
        update={
            "arms": {
                "robot_1": ArmGeometry(axis="x", side=-1.0),
                "robot_2": ArmGeometry(axis="x", side=1.0),
            }
        }
    )
    assert _ground(_result("robot_1"), TAKE2, arms, **BOTH) == _ground(
        _result("robot_1"), TAKE2, arms, **HOLD
    )


def test_is_a_no_op_for_non_yield_strategy():
    result = _result(strategy="reverse")
    assert _ground(result, TAKE2, **BOTH) == _ground(result, TAKE2, **HOLD)


def test_is_a_no_op_without_snapshot():
    positions = {r.robot_id: (r.x, r.y) for r in TAKE2.robots}
    result = _result("robot_1")
    on = ground_reasoner_result(result, positions, GEOMETRY, params=LEGACY, **BOTH)
    assert on == ground_reasoner_result(result, positions, GEOMETRY, params=LEGACY, **HOLD)


# --- plan verification ----------------------------------------------------------


def _verify(result, frame=TAKE2, **kwargs):
    return verify_and_repair_plan(
        result.decision, frame, geometry=GEOMETRY, grounding_params=LEGACY, **kwargs
    )


def test_verify_repairs_platoon_side_yield_leg_by_one_swap():
    verified = _verify(_result("robot_1", plan=_ROBOT_1_PLAN), **BOTH)
    assert verified.provenance == "repaired"
    assert [(leg.robot_id, leg.action) for leg in verified.legs] == [
        ("robot_2", "yield"), ("robot_1", "cross"), ("robot_3", "cross"), ("robot_4", "cross")
    ]
    ops = [(e.op, e.robot_ids) for e in verified.edits]
    assert ops.count(("swap", ("robot_1", "robot_2"))) == 1
    assert sorted(op for op in ops if op[0] == "substitute") == [
        ("substitute", ("robot_3",)), ("substitute", ("robot_4",))
    ]
    swap = next(e for e in verified.edits if e.op == "swap")
    assert swap.reason.startswith("yield re-grounded: counterflow:")
    assert all(
        e.reason.startswith(QUEUED_CROSSER_PREFIX) for e in verified.edits if e.op == "substitute"
    )


@pytest.mark.parametrize("plan", [_ROBOT_1_PLAN, None])
def test_verify_matches_swapped_dispatch(plan):
    result = _result("robot_1", plan=plan)
    verified = _verify(result, **BOTH)
    command = _ground(result, TAKE2, **BOTH)
    assert plan_matches_dispatch(verified.legs, command, [r.robot_id for r in TAKE2.robots])


def test_verify_plan_absent_defaults_to_feasible_yielder():
    verified = _verify(_result("robot_1"), **BOTH)
    assert verified.provenance == "m3_default"
    assert {leg.robot_id: leg.action for leg in verified.legs} == {
        "robot_2": "yield", "robot_1": "cross", "robot_3": "cross", "robot_4": "cross"
    }


@pytest.mark.parametrize("yielder", ["robot_1", "robot_2"])
def test_verify_key_off_is_identical_to_hold_only(yielder):
    plan = _ROBOT_1_PLAN if yielder == "robot_1" else _CONTINUE_PLAN
    result = _result(yielder, plan=plan)
    assert _verify(result, yield_counterflow_swap=False, **HOLD) == _verify(result, **HOLD)


def test_verify_feasible_model_yielder_is_identical_to_hold_only():
    result = _result("robot_2", plan=_CONTINUE_PLAN)
    assert _verify(result, TAKE1, **BOTH) == _verify(result, TAKE1, **HOLD)


def test_verify_refusal_defaults_to_waits():
    verified = _verify(_result("robot_1", plan=_ROBOT_1_PLAN), BOTH_SIDES, **BOTH)
    assert verified.provenance == "m3_default"
    assert verified.rejection_reason.startswith("plan unrepairable: yield refused: counterflow:")
    actions = {leg.robot_id: leg.action for leg in verified.legs}
    assert actions == {
        "robot_1": "wait", "robot_2": "wait", "robot_3": "continue", "robot_4": "continue"
    }


def test_verify_is_a_no_op_in_derived_mode():
    derived = GroundingParams(mode="derived")
    result = _result("robot_1", plan=_ROBOT_1_PLAN)
    on = verify_and_repair_plan(
        result.decision, TAKE2, geometry=GEOMETRY, grounding_params=derived, **BOTH
    )
    off = verify_and_repair_plan(
        result.decision, TAKE2, geometry=GEOMETRY, grounding_params=derived, **HOLD
    )
    assert on == off


# --- M5 pipeline, config, status line, artifact ---------------------------------


def _pipeline(**kwargs) -> InProcessPipeline:
    return InProcessPipeline(
        reasoner=None,
        ground_fn=ground_reasoner_result,
        scene_geometry=GEOMETRY,
        grounding_params=LEGACY,
        plan_tracker=PlanTracker(),
        **kwargs,
    )


def test_pipeline_dispatches_feasible_yielder_with_matching_plan():
    outcome = _pipeline(**BOTH)._run_from_result(
        _request(TAKE2), _result("robot_1", plan=_ROBOT_1_PLAN)
    )
    assert _structure(outcome.grounded_command)["yielder"] == "robot_2"
    assert outcome.plan.provenance == "repaired"
    assert outcome.plan.dispatch_matches_plan is True


def test_pipeline_default_passes_no_counterflow_argument():
    seen: dict = {}

    def ground_fn(result, robot_positions=None, geometry=None, **kwargs):
        seen.update(kwargs)
        return ground_reasoner_result(result, robot_positions, geometry, **kwargs)

    pipe = InProcessPipeline(
        reasoner=None, ground_fn=ground_fn, scene_geometry=GEOMETRY, grounding_params=LEGACY
    )
    pipe._run_from_result(_request(TAKE2), _result("robot_1"))
    assert "yield_counterflow_swap" not in seen


def test_pipeline_hold_only_is_unchanged():
    on = _pipeline(**HOLD)._run_from_result(_request(TAKE2), _result("robot_1", plan=_ROBOT_1_PLAN))
    assert _structure(on.grounded_command)["yielder"] == "robot_1"


def test_artifact_records_model_choice_and_reason(tmp_path):
    outcome = _pipeline(**BOTH)._run_from_result(
        _request(TAKE2), _result("robot_1", plan=_ROBOT_1_PLAN)
    )
    payload = json.loads(write_decision_artifact(tmp_path, outcome).read_text())
    assert payload["yield_robot_grounded_from"] == "robot_1"
    assert payload["yield_regrounded_reason"].startswith("yield re-grounded: counterflow:")
    assert payload["decision"]["yield_robot"] == "robot_1"
    assert payload["grounding_queued_crossers_added"] == ["robot_3", "robot_4"]


def test_config_defaults_off(tmp_path):
    assert _config(tmp_path).grounding_yield_counterflow_swap is False


def test_status_line_names_both_keys_in_order(tmp_path):
    config = _config(
        tmp_path, grounding_hold_queued_crossers=True, grounding_yield_counterflow_swap=True
    )
    assert plan_order_status_line(config) == (
        "plan order condition plan_dispatch_order_source=chi "
        "prompt_plan_grammar_rules=False prompt_candidate_options=False "
        "grounding_hold_queued_crossers=True grounding_yield_counterflow_swap=True"
    )


def test_status_line_unchanged_when_off(tmp_path):
    config = _config(tmp_path, grounding_hold_queued_crossers=True)
    assert "counterflow" not in plan_order_status_line(config)


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
        config = _config(tmp_path, grounding_yield_counterflow_swap=flag)
        pipe = node_module._build_default_pipeline(config, source)
        assert pipe._yield_counterflow_swap is flag

"""prereg-v3 A28(ii): escort grounding must clear the parked yielder's park point.

Live E20 command `6cf402ed` (docs/reports/2026-10-12-shield-fix-and-minibatch.md
§6) parked robot_1 at (2.156, -1.428), then escorted robot_3 1.843 m east
from its snapshot pose: the escort line passes ~0.13 m from the park point
and robot_3 pushed the exempt yielder (GT minimum 0.109 m). Under
`GroundingParams.escort_park_clearance` a yield whose escort leg passes
within `min_distance_m` (0.45 m) of the park point is infeasible and
degrades to the reroute fallback (`reasoning.rag.escort_clearance`).

Fixtures (`data/a28_escort_park/yields.json`): four live S1b yields
dispatched on `config/grounding/s1b_dynamic_shield.yaml` (E20 `6cf402ed`
and `f269ab37`, E21 `04457772`, E23 `9803bd34`), each with its decision,
snapshot rows, stage-2 grounded label, M5 task intent rebuilt from the
bundle's `tasks_*.jsonl`, and the dispatched command.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from swarm_orchestrator.reasoning_pipeline import empty_reroute_fallback, load_grounding_source

from reasoning.rag.command_grounder import (
    DEGRADATION_TAGS,
    degradation_cause,
    ground_reasoner_result,
)
from reasoning.rag.escort_clearance import (
    escort_legs,
    escort_park_violations,
    point_segment_distance,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_shield import RobotTaskIntent
from reasoning.vlm.models import (
    CongestionDecision,
    RetreatChoiceDecision,
    RobotStateInput,
    SnapshotFrame,
)
from tests.unit.test_s1_resolvability import _floor, _frame, _reasoner_result

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIELD_FILE = REPO_ROOT / "config/grounding/s1b_dynamic_shield.yaml"
S1B_FILE = REPO_ROOT / "config/grounding/s1b_dynamic.yaml"
CASES = {
    case["case"]: case
    for case in json.loads(
        (Path(__file__).parent / "data/a28_escort_park/yields.json").read_text(encoding="utf-8")
    )["cases"]
}
VETOED = "E20_6cf402ed"
# Admitted live yields that cleared the park point by more than the latch.
CLEAR_CONTROLS = ("E21_04457772", "E23_9803bd34")
# M5's plan id, and the A27 shield-hold key added after batch 3.
_IGNORED = {"plan_id", "retreat_shield_hold"}


def _params(path: Path = SHIELD_FILE, **updates: Any) -> GroundingParams:
    params = load_grounding_source(path).params
    return params.model_copy(update=updates) if updates else params


def _ground(case: dict[str, Any], params: GroundingParams) -> dict[str, Any]:
    config, _ = _floor("s1b")
    frame = _frame(case["rows"])
    intents = {
        rid: RobotTaskIntent(
            goal=tuple(v["goal"]),
            next_goal=None if v["next_goal"] is None else tuple(v["next_goal"]),
            dwell_sec=v["dwell_sec"],
        )
        for rid, v in case["intents"].items()
    }
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
        goal_references={rid: tuple(v["goal"]) for rid, v in case["intents"].items()},
        task_intents=intents,
    )


def _yield(command: dict[str, Any]) -> dict[str, Any] | None:
    return next((a for a in command["actions"] if a["action"] == "yield"), None)


def _live_yield_parameters(case: dict[str, Any]) -> dict[str, Any]:
    live = _yield(case["dispatched_command"])
    assert live is not None
    return {k: v for k, v in live["parameters"].items() if k != "plan_id"}


def _live_legs(case: dict[str, Any]):
    live = _yield(case["dispatched_command"])
    return escort_legs(
        live["robot_id"], live["parameters"], _frame(case["rows"]), _geometry(case)
    )


def _geometry(case: dict[str, Any]):
    # The dynamic view the live yield was grounded on: its corridor is what
    # `escort_axis` reads when a leg carries no heading.
    from reasoning.rag.grounding_view import resolve_grounding_view

    config, _ = _floor("s1b")
    return resolve_grounding_view(
        CongestionDecision.model_validate(case["decision"]),
        _frame(case["rows"]),
        config.scenario_geometry,
        _params(),
    ).geometry


def _state(robot_id: str, x: float, y: float, theta: float = 0.0) -> RobotStateInput:
    return RobotStateInput(robot_id=robot_id, x=x, y=y, theta=theta, status="STOPPED")


def _snapshot(*states: RobotStateInput) -> SnapshotFrame:
    return SnapshotFrame(stamp=1.0, robots=list(states))


# ---- the fixtures are the live inputs ----


@pytest.mark.parametrize("name", sorted(CASES))
def test_regrounding_reproduces_the_dispatched_yield_when_check_off(name):
    case = CASES[name]
    command = _ground(case, _params())
    grounded = _yield(command)
    live = _yield(case["dispatched_command"])
    assert grounded["robot_id"] == live["robot_id"]
    assert grounded["parameters"] == _live_yield_parameters(case)
    assert command["degradations"] == case["dispatched_command"]["degradations"]


@pytest.mark.parametrize("name", sorted(CASES))
def test_regrounding_reproduces_the_dispatched_waits_when_check_off(name):
    case = CASES[name]
    def waits(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # The A27 shield-hold key postdates batch 3, so E20 never carried it.
        return [
            {**a, "parameters": {k: v for k, v in a["parameters"].items() if k not in _IGNORED}}
            for a in actions
            if a["action"] != "yield"
        ]

    assert waits(_ground(case, _params())["actions"]) == waits(
        case["dispatched_command"]["actions"]
    )


# ---- E20 6cf402ed: the live push ----


def test_e20_escort_line_passes_inside_the_latch_of_the_park_point():
    (leg,) = _live_legs(CASES[VETOED])
    assert leg.passer_id == "robot_3"
    assert leg.heading_rad == 0.0
    assert leg.distance_m == 1.843
    # The snapshot line y = -1.297 against the park point y = -1.428; the
    # report's ~0.14 m reads the GT drive line (y ~ -1.27 at drive start).
    assert leg.park_clearance_m == pytest.approx(0.131, abs=1e-3)
    assert leg.start_xy[0] < 2.156 < leg.end_xy[0]


def test_e20_check_sees_the_dispatched_escort_heading_and_distance():
    case = CASES[VETOED]
    grounded = _yield(_ground(case, _params()))
    legs = escort_legs(
        grounded["robot_id"], grounded["parameters"], _frame(case["rows"]), _geometry(case)
    )
    assert legs == _live_legs(case)


def test_e20_yield_is_vetoed_when_park_clearance_on():
    command = _ground(CASES[VETOED], _params(escort_park_clearance=True))
    assert _yield(command) is None
    assert "yield=infeasible:escort_hits_park:robot_3:0.131" in command["degradations"]


def test_e20_veto_degrades_to_the_yielder_reroute_fallback():
    command = _ground(CASES[VETOED], _params(escort_park_clearance=True))
    assert [(a["robot_id"], a["action"]) for a in command["actions"]] == [
        ("robot_1", "reroute"),
        ("robot_3", "temporary_wait"),
    ]
    assert empty_reroute_fallback(command) == "yield=infeasible:escort_hits_park:robot_3:0.131"


def test_e20_veto_carries_the_cause_then_the_view_tag_only():
    # The internal heading pass's cap tag belongs to the vetoed yield and is
    # not carried; the view's provenance is appended as for any command.
    command = _ground(CASES[VETOED], _params(escort_park_clearance=True))
    assert command["degradations"] == [
        "yield=infeasible:escort_hits_park:robot_3:0.131",
        "grounding=dynamic_arms:lane:x",
    ]


def test_e20_is_vetoed_on_the_unshielded_s1b_file_too():
    command = _ground(CASES[VETOED], _params(S1B_FILE, escort_park_clearance=True))
    assert _yield(command) is None


# ---- positive controls: real clearances ground unchanged ----


@pytest.mark.parametrize("name", CLEAR_CONTROLS)
def test_clear_escort_grounds_byte_identical_when_park_clearance_on(name):
    case = CASES[name]
    on = _ground(case, _params(escort_park_clearance=True))
    off = _ground(case, _params())
    assert json.dumps(_yield(on)["parameters"]) == json.dumps(_yield(off)["parameters"])
    assert _yield(on)["parameters"] == _live_yield_parameters(case)
    assert on == off


@pytest.mark.parametrize(("name", "clearance"), [("E21_04457772", 0.558), ("E23_9803bd34", 0.896)])
def test_clear_escort_leg_measures_beyond_the_latch(name, clearance):
    (leg,) = _live_legs(CASES[name])
    assert leg.park_clearance_m == pytest.approx(clearance, abs=1e-3)


def test_f269ab37_leg_sits_just_inside_the_latch_and_is_vetoed():
    # Admitted live with no contact, but 0.447 m < 0.45 m: the ruling as
    # stated vetoes it (open question for the owner, A28 report).
    case = CASES["E20_f269ab37"]
    (leg,) = _live_legs(case)
    assert leg.park_clearance_m == pytest.approx(0.447, abs=1e-3)
    assert _yield(_ground(case, _params(escort_park_clearance=True))) is None


# ---- point-to-segment math and the boundary ----


def test_point_segment_distance_is_perpendicular_inside_the_segment():
    assert point_segment_distance((1.0, 0.3), (0.0, 0.0), (2.0, 0.0)) == pytest.approx(0.3)


def test_point_segment_distance_is_to_the_end_beyond_the_segment():
    assert point_segment_distance((3.0, 0.4), (0.0, 0.0), (2.0, 0.0)) == pytest.approx(
        math.hypot(1.0, 0.4)
    )


def test_point_segment_distance_is_to_the_start_behind_the_segment():
    assert point_segment_distance((-0.3, -0.4), (0.0, 0.0), (2.0, 0.0)) == pytest.approx(0.5)


def test_point_segment_distance_is_to_the_point_for_a_zero_length_segment():
    assert point_segment_distance((0.3, 0.4), (0.0, 0.0), (0.0, 0.0)) == pytest.approx(0.5)


def _single_passer(park_y: float, **extra: Any) -> dict[str, Any]:
    return {
        "retreat_x_m": 1.0,
        "retreat_y_m": park_y,
        "passer_robot_id": "robot_2",
        "passer_escort_distance_m": 2.0,
        "passer_clear_m": 2.0,
        "passer_escort_heading_rad": 0.0,
        "passer_escort_reference_yaw_rad": 0.0,
        **extra,
    }


_PAIR = _snapshot(_state("robot_1", 0.5, 0.0, math.pi), _state("robot_2", 0.0, 0.0))


def test_leg_exactly_at_the_latch_radius_clears_the_park_point():
    assert escort_park_violations("robot_1", _single_passer(0.45), _PAIR, None, 0.45) == []


def test_leg_just_inside_the_latch_radius_is_a_violation():
    (leg,) = escort_park_violations("robot_1", _single_passer(0.449), _PAIR, None, 0.45)
    assert leg.passer_id == "robot_2"
    assert leg.park_clearance_m == pytest.approx(0.449)


def test_park_point_past_the_escort_end_is_measured_to_the_end():
    (leg,) = escort_legs("robot_1", _single_passer(0.0, retreat_x_m=2.3), _PAIR, None)
    assert leg.park_clearance_m == pytest.approx(0.3)


# ---- which escorts are swept ----


def test_yield_without_an_escort_has_no_leg():
    parameters = _single_passer(0.0)
    del parameters["passer_escort_distance_m"]
    assert escort_legs("robot_1", parameters, _PAIR, None) == []


def test_leg_without_heading_and_geometry_runs_along_the_passer_heading():
    parameters = _single_passer(0.5)
    del parameters["passer_escort_heading_rad"]
    snapshot = _snapshot(
        _state("robot_1", 0.5, 0.0, math.pi), _state("robot_2", 0.0, 0.0, math.pi / 2)
    )
    (leg,) = escort_legs("robot_1", parameters, snapshot, None)
    assert leg.heading_rad == pytest.approx(math.pi / 2)
    assert leg.end_xy == pytest.approx((0.0, 2.0))


def test_leg_without_heading_runs_toward_the_yielder_along_the_declared_axis():
    case = CASES[VETOED]
    live = _yield(case["dispatched_command"])
    parameters = {
        k: v
        for k, v in live["parameters"].items()
        if k not in ("passer_escort_heading_rad", "passer_escort_reference_yaw_rad")
    }
    (leg,) = escort_legs("robot_1", parameters, _frame(case["rows"]), _geometry(case))
    # robot_1 (x 0.783) lies east of robot_3 (x 0.457) on the lane axis x.
    assert leg.heading_rad == 0.0
    assert leg.park_clearance_m == pytest.approx(0.131, abs=1e-3)


def test_queued_passer_leg_uses_its_own_escort_and_heading():
    parameters = _single_passer(
        5.0,
        crossing_order=["robot_2", "robot_3"],
        crossing_escort_m=[2.0, 1.5],
        crossing_clear_m=[2.0, 1.5],
        crossing_escort_heading_rad=[0.0, math.pi / 2],
        crossing_escort_reference_yaw_rad=[0.0, 0.0],
        retreat_x_m=-1.0,
        retreat_y_m=1.2,
    )
    snapshot = _snapshot(
        _state("robot_1", 0.5, 0.0, math.pi),
        _state("robot_2", 0.0, 0.0),
        _state("robot_3", -1.0, -0.5),
    )
    violations = escort_park_violations("robot_1", parameters, snapshot, None, 0.45)
    assert [leg.passer_id for leg in violations] == ["robot_3"]
    assert violations[0].end_xy == pytest.approx((-1.0, 1.0))
    assert violations[0].park_clearance_m == pytest.approx(0.2)


def test_queued_passer_leg_falls_back_to_its_clearance_without_escort_list():
    parameters = _single_passer(
        5.0,
        crossing_order=["robot_2", "robot_3"],
        crossing_clear_m=[2.0, 0.7],
    )
    snapshot = _snapshot(
        _state("robot_1", 0.5, 0.0, math.pi),
        _state("robot_2", 0.0, 0.0),
        _state("robot_3", -1.0, 0.0),
    )
    legs = escort_legs("robot_1", parameters, snapshot, None)
    assert [(leg.passer_id, leg.distance_m) for leg in legs] == [("robot_2", 2.0), ("robot_3", 0.7)]


# ---- the switch and the tag ----


def test_park_clearance_switch_defaults_off_and_stays_out_of_the_dump():
    params = _params()
    assert params.escort_park_clearance is False
    assert "escort_park_clearance" not in params.model_dump()


def test_park_clearance_switch_on_is_dumped():
    assert _params(escort_park_clearance=True).model_dump()["escort_park_clearance"] is True


def test_pinned_grounding_files_leave_the_switch_off():
    assert _params(S1B_FILE).escort_park_clearance is False
    assert _params(SHIELD_FILE).escort_park_clearance is False


def test_escort_hits_park_tag_is_an_infeasible_geometry_cause():
    assert "yield=infeasible" in DEGRADATION_TAGS
    assert degradation_cause("yield=infeasible:escort_hits_park:robot_3:0.131") == (
        "infeasible_geometry"
    )

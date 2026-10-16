"""prereg-v3 A28(ii): escort grounding must clear the parked yielder's park point.

Live E20 command `6cf402ed` (docs/reports/2026-10-12-shield-fix-and-minibatch.md
§6) parked robot_1 at (2.156, -1.428), then escorted robot_3 1.843 m east
from its snapshot pose: the escort line passes ~0.13 m from the park point
and robot_3 pushed the exempt yielder (GT minimum 0.109 m). Under
`GroundingParams.escort_park_clearance` every retreat candidate whose escort
leg would pass within `min_distance_m` (0.45 m) of its park point is dropped
before stage 2 (owner ruling 2026-10-16); only when none survives is the
yield infeasible, degrading to the reroute fallback. The post-selection
check on the chosen yield stays as a backstop
(`reasoning.rag.escort_clearance`).

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
from swarm_orchestrator.retreat_stage2 import run_retreat_stage2

from reasoning.rag.command_grounder import (
    DEGRADATION_TAGS,
    degradation_cause,
    filter_escort_park_candidates,
    ground_reasoner_result,
    prepare_retreat_selection,
)
from reasoning.rag.escort_clearance import (
    escort_legs,
    escort_park_violations,
    point_segment_distance,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_shield import RobotTaskIntent
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerRequest,
    RetreatChoiceDecision,
    RetreatChoiceResult,
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


_LIVE = object()


def _ground(
    case: dict[str, Any], params: GroundingParams, *, choice: Any = _LIVE
) -> dict[str, Any]:
    # `choice` overrides the live stage-2 label (None grounds the default).
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
    label = case["retreat_choice"] if choice is _LIVE else choice
    choice = (
        None
        if label is None
        else RetreatChoiceDecision(retreat_choice=label, justification="live")
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


# Superseded 2026-10-16 (owner ruling): the A28(ii) rule filters retreat
# CANDIDATES before stage 2 instead of vetoing the chosen yield. E20's chosen
# candidate A hit the park point, its B and C did not, so the yield now
# grounds on a surviving candidate (see the candidate-filter section below).


def test_e20_yield_still_grounds_when_park_clearance_on():
    command = _ground(CASES[VETOED], _params(escort_park_clearance=True))
    assert _yield(command) is not None
    assert not any(tag.startswith("yield=infeasible") for tag in command["degradations"])


def test_e20_filter_tags_candidate_a_then_carries_the_grounded_tags():
    # The live choice "A" is replayed literally: after the filter it names
    # the first surviving candidate (old B), as any positional veto does.
    command = _ground(CASES[VETOED], _params(escort_park_clearance=True))
    assert command["degradations"] == [
        "retreat=escort_park_filtered:A:robot_3:0.131",
        "grounding=dynamic_arms:lane:x",
        "grounding=escort_turn_cap:robot_3:2.35->1.843",
    ]


def test_e20_is_filtered_on_the_unshielded_s1b_file_too():
    command = _ground(CASES[VETOED], _params(S1B_FILE, escort_park_clearance=True))
    assert "retreat=escort_park_filtered:A:robot_3:0.131" in command["degradations"]
    assert _yield(command) is not None


# ---- positive controls: real clearances keep their pose ----


@pytest.mark.parametrize("name", CLEAR_CONTROLS)
def test_clear_escort_keeps_its_live_pose_when_park_clearance_on(name):
    # Both live yields chose a pose that clears the latch; the filter drops
    # only their candidate A, so the surviving set still holds the live pose.
    case = CASES[name]
    live = _live_yield_parameters(case)
    choice = _surviving_label(case, (live["retreat_x_m"], live["retreat_y_m"]))
    on = _yield(_ground(case, _params(escort_park_clearance=True), choice=choice))
    assert (on["parameters"]["retreat_x_m"], on["parameters"]["retreat_y_m"]) == (
        live["retreat_x_m"],
        live["retreat_y_m"],
    )
    differs = {k for k in live if on["parameters"].get(k) != live[k]}
    assert differs <= {"retreat_choice"}


@pytest.mark.parametrize(("name", "clearance"), [("E21_04457772", 0.558), ("E23_9803bd34", 0.896)])
def test_clear_escort_leg_measures_beyond_the_latch(name, clearance):
    (leg,) = _live_legs(CASES[name])
    assert leg.park_clearance_m == pytest.approx(clearance, abs=1e-3)


def test_f269ab37_leg_sits_just_inside_the_latch_and_is_filtered():
    # Admitted live with no contact, but 0.447 m < 0.45 m: the rule is the
    # rule, and its only other candidate (0.273 m) violates too.
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


# ---- declared geometry (no dynamic view, no escort heading) ----


def _corridor() -> SceneGeometry:
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x", center_m=0.0, half_length_m=1.0, aisle_half_width_m=0.6, occluder_height_m=0.9
        )
    )


_HEAD_ON = _snapshot(_state("robot_1", -0.3, 0.0), _state("robot_2", 0.3, 0.0, math.pi))


def _declared_head_on(params: GroundingParams) -> dict[str, Any]:
    # The shipped head-on deadlock (`test_command_grounder_derived`): robot_1
    # yields west to (-1.789, +-0.36), robot_2 is escorted 2.739 m west
    # along the corridor centreline.
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on standoff",
        strategy="yield",
        justification="j",
        yield_robot="robot_1",
    )
    return ground_reasoner_result(
        _reasoner_result(decision), snapshot=_HEAD_ON, params=params, geometry=_corridor()
    )


def test_declared_head_on_escort_runs_toward_the_yielder_along_the_corridor():
    parameters = _yield(_declared_head_on(GroundingParams(mode="derived")))["parameters"]
    assert "passer_escort_heading_rad" not in parameters
    (leg,) = escort_legs("robot_1", parameters, _HEAD_ON, _corridor())
    assert leg.heading_rad == pytest.approx(math.pi)
    assert leg.end_xy == pytest.approx((0.3 - 2.739, 0.0))
    # The passer passes the parked yielder at its pull-off lateral.
    assert leg.park_clearance_m == pytest.approx(abs(parameters["pull_off_lateral_m"]))


def test_declared_head_on_yield_is_vetoed_when_park_clearance_on():
    # The 0.36 m pull-off lateral is under the 0.45 m latch: the ruling as
    # stated vetoes the canonical head-on yield too (A28 owner question).
    command = _declared_head_on(GroundingParams(mode="derived", escort_park_clearance=True))
    assert _yield(command) is None
    assert command["degradations"][-1] == "yield=infeasible:escort_hits_park:robot_2:0.360"


# ---- candidate filter before stage 2 (owner ruling 2026-10-16) ----
#
# Pre-filter poses and park clearances of every fixture's candidates, in
# generation order (switch off), measured on the dispatched escort leg:
#   E20 6cf402ed  A (2.156, -1.428) 0.131 | B (2.156, -0.708) 0.589 | C (2.156, -0.348) 0.949
#   E20 f269ab37  A (0.715,  0.928) 0.273 | B (0.715,  1.648) 0.447
#   E21 04457772  A (-2.308, -0.946) 0.198 | B (-2.308, -0.586) 0.558
#   E23 9803bd34  A (1.445, -1.441) 0.184 | B (1.445, -0.721) 0.536 | C (1.445, -0.361) 0.896

_E20_OLD_B = (2.156, -0.708)
_E20_OLD_C = (2.156, -0.348)


class _FixedChooser:
    def __init__(self, letter: str) -> None:
        self._letter = letter

    def choose(self, request):
        return RetreatChoiceResult(
            request_id=request.request_id,
            backend_id="fixed",
            choice=RetreatChoiceDecision(retreat_choice=self._letter, justification="j"),
            raw_text="{}",
            attempts=1,
        )


def _goals(case: dict[str, Any]) -> dict[str, tuple[float, float]]:
    return {rid: tuple(v["goal"]) for rid, v in case["intents"].items()}


def _stage2(case: dict[str, Any], params: GroundingParams, letter: str = "A"):
    # Stage 2 as M5 runs it (`InProcessPipeline._run_from_result`): on the
    # grounding view's decision and geometry, with the same goal references.
    from reasoning.rag.grounding_view import resolve_grounding_view

    config, _ = _floor("s1b")
    frame = _frame(case["rows"])
    view = resolve_grounding_view(
        CongestionDecision.model_validate(case["decision"]),
        frame,
        config.scenario_geometry,
        params,
        _goals(case),
    )
    request = ReasonerRequest(
        request_id="r", image_path="/tmp/a28.png", frame_id="f", stamp=1.0,
        robot_states=list(frame.robots),
    )
    return run_retreat_stage2(
        request,
        view.decision,
        frame,
        params,
        _FixedChooser(letter),
        geometry=view.geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        goal_references=_goals(case),
    )


def _poses(record) -> dict[str, tuple[float, float]]:
    return {c["label"]: (round(c["x"], 3), round(c["y"], 3)) for c in record.candidates}


def _surviving_label(case: dict[str, Any], pose: tuple[float, float]) -> str:
    _, record = _stage2(case, _params(escort_park_clearance=True))
    return next(label for label, xy in _poses(record).items() if xy == pose)


def _park(command: dict[str, Any]) -> tuple[float, float]:
    parameters = _yield(command)["parameters"]
    return (parameters["retreat_x_m"], parameters["retreat_y_m"])


def _clearance(case: dict[str, Any], command: dict[str, Any]) -> float:
    grounded = _yield(command)
    (leg,) = escort_legs(
        grounded["robot_id"], grounded["parameters"], _frame(case["rows"]), _geometry(case)
    )
    return leg.park_clearance_m


def test_e20_stage2_offers_three_candidates_when_park_clearance_off():
    _, record = _stage2(CASES[VETOED], _params())
    assert _poses(record) == {
        "A": (2.156, -1.428),
        "B": _E20_OLD_B,
        "C": _E20_OLD_C,
    }


def test_e20_stage2_offers_only_the_candidates_clearing_the_park_point():
    # Candidate A is dropped; B and C re-letter A and B in generation order,
    # as a box-sweep or min-distance veto re-letters the survivors.
    _, record = _stage2(CASES[VETOED], _params(escort_park_clearance=True))
    assert record.status == "answered"
    assert _poses(record) == {"A": _E20_OLD_B, "B": _E20_OLD_C}
    shown = {
        letter: (round(entry["x"], 3), round(entry["y"], 3))
        for letter, entry in record.letter_assignment.items()
    }
    assert set(shown) == {"A", "B"}
    assert set(shown.values()) == {_E20_OLD_B, _E20_OLD_C}


@pytest.mark.parametrize("letter", ["A", "B"])
def test_e20_each_shown_letter_grounds_the_pose_it_was_shown_at(letter):
    case = CASES[VETOED]
    params = _params(escort_park_clearance=True)
    choice, record = _stage2(case, params, letter)
    entry = record.letter_assignment[letter]
    command = _ground(case, params, choice=choice.retreat_choice)
    assert _park(command) == (round(entry["x"], 3), round(entry["y"], 3))
    assert not any(tag.startswith("yield=infeasible") for tag in command["degradations"])


@pytest.mark.parametrize(("pose", "clearance"), [(_E20_OLD_B, 0.589), (_E20_OLD_C, 0.949)])
def test_e20_surviving_candidates_clear_the_park_point(pose, clearance):
    case = CASES[VETOED]
    params = _params(escort_park_clearance=True)
    command = _ground(case, params, choice=_surviving_label(case, pose))
    assert _park(command) == pose
    assert _clearance(case, command) == pytest.approx(clearance, abs=1e-3)


def test_e20_default_grounds_a_surviving_candidate():
    command = _ground(CASES[VETOED], _params(escort_park_clearance=True), choice=None)
    assert _park(command) in (_E20_OLD_B, _E20_OLD_C)
    assert "retreat=escort_park_filtered:A:robot_3:0.131" in command["degradations"]


def test_e20_filtered_candidates_are_recorded_on_the_selection():
    from reasoning.rag.grounding_view import resolve_grounding_view

    case = CASES[VETOED]
    params = _params(escort_park_clearance=True)
    config, _ = _floor("s1b")
    frame = _frame(case["rows"])
    view = resolve_grounding_view(
        CongestionDecision.model_validate(case["decision"]), frame,
        config.scenario_geometry, params, _goals(case),
    )
    selection = prepare_retreat_selection(
        frame, "robot_1", ["robot_3"], params,
        geometry=view.geometry, static_obstacles=config.static_obstacles,
    )
    filtered = filter_escort_park_candidates(
        selection, frame, params, geometry=view.geometry, goal_references=_goals(case)
    )
    assert filtered.escort_park_filtered == ["A:robot_3:0.131"]
    assert sorted(c.label for c in filtered.candidates) == ["A", "B"]
    assert selection.escort_park_filtered == []


def test_filter_returns_the_selection_unchanged_when_park_clearance_off():
    case = CASES[VETOED]
    params = _params()
    frame = _frame(case["rows"])
    selection = prepare_retreat_selection(
        frame, "robot_1", ["robot_3"], params, geometry=_geometry(case)
    )
    assert filter_escort_park_candidates(selection, frame, params, geometry=_geometry(case)) is (
        selection
    )


@pytest.mark.parametrize("name", sorted(CASES))
def test_stage2_record_is_unchanged_when_park_clearance_off(name):
    case = CASES[name]
    params = _params()
    with_refs = _stage2(case, params)
    assert with_refs[1].candidates == _stage2_without_refs(case, params)[1].candidates


def _stage2_without_refs(case: dict[str, Any], params: GroundingParams):
    from reasoning.rag.grounding_view import resolve_grounding_view

    config, _ = _floor("s1b")
    frame = _frame(case["rows"])
    view = resolve_grounding_view(
        CongestionDecision.model_validate(case["decision"]),
        frame,
        config.scenario_geometry,
        params,
        _goals(case),
    )
    request = ReasonerRequest(
        request_id="r", image_path="/tmp/a28.png", frame_id="f", stamp=1.0,
        robot_states=list(frame.robots),
    )
    return run_retreat_stage2(
        request, view.decision, frame, params, _FixedChooser("A"),
        geometry=view.geometry, static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
    )


def test_f269ab37_every_candidate_violates_so_no_candidate_survives():
    case = CASES["E20_f269ab37"]
    _, record = _stage2(case, _params(escort_park_clearance=True))
    assert record.status == "skipped"
    assert record.skip_reason == "no_candidates"
    assert record.candidates == []


def test_f269ab37_degrades_to_the_infeasible_reroute_with_both_filters_tagged():
    case = CASES["E20_f269ab37"]
    command = _ground(case, _params(escort_park_clearance=True))
    tags = command["degradations"]
    assert "retreat=escort_park_filtered:A:robot_2:0.273" in tags
    assert "retreat=escort_park_filtered:B:robot_2:0.447" in tags
    assert empty_reroute_fallback(command) is not None
    assert empty_reroute_fallback(command).startswith("yield=infeasible:escort_hits_park:robot_2:")
    assert [a["action"] for a in command["actions"]][0] == "reroute"


def test_e21_single_surviving_candidate_skips_stage2_and_grounds_the_live_pose():
    case = CASES["E21_04457772"]
    params = _params(escort_park_clearance=True)
    _, record = _stage2(case, params)
    assert record.skip_reason == "single_candidate"
    assert _poses(record) == {"A": (-2.308, -0.586)}
    command = _ground(case, params, choice=None)
    assert _park(command) == (-2.308, -0.586)
    assert _clearance(case, command) == pytest.approx(0.558, abs=1e-3)
    assert "retreat=escort_park_filtered:A:robot_4:0.198" in command["degradations"]


def test_e23_filter_keeps_b_and_c():
    case = CASES["E23_9803bd34"]
    _, record = _stage2(case, _params(escort_park_clearance=True))
    assert _poses(record) == {"A": (1.445, -0.721), "B": (1.445, -0.361)}


@pytest.mark.parametrize("name", sorted(CASES))
@pytest.mark.parametrize("letter", ["A", "B"])
def test_backstop_never_fires_on_a_filtered_survivor(name, letter):
    # The pre-filter and the post-selection check sweep the same leg.
    case = CASES[name]
    command = _ground(case, _params(escort_park_clearance=True), choice=letter)
    if _yield(command) is None:
        assert name == "E20_f269ab37"
        return
    assert not any(t.startswith("yield=infeasible") for t in command["degradations"])


def test_escort_park_filtered_tag_is_provenance():
    assert "retreat=escort_park_filtered" in DEGRADATION_TAGS
    assert degradation_cause("retreat=escort_park_filtered:A:robot_3:0.131") is None


def test_declared_head_on_filters_both_candidates_before_the_veto():
    command = _declared_head_on(GroundingParams(mode="derived", escort_park_clearance=True))
    assert command["degradations"] == [
        "retreat=escort_park_filtered:A:robot_2:0.360",
        "retreat=escort_park_filtered:B:robot_2:0.360",
        "yield=infeasible:escort_hits_park:robot_2:0.360",
    ]
    assert empty_reroute_fallback(command) == "yield=infeasible:escort_hits_park:robot_2:0.360"


def test_pipeline_hands_stage2_the_grounder_goal_references(monkeypatch):
    # The filter reads goal references through `apply_escort_headings`; stage
    # 2 must letter with the ones the grounder gets, or the letters drift.
    from swarm_orchestrator import reasoning_pipeline
    from swarm_orchestrator.models import RetreatStage2Record

    from tests.unit.test_m5_retreat_stage2 import _decision, _FakeReasoner, _geometry, _request

    seen: dict[str, Any] = {}

    def fake_stage2(*args, **kwargs):
        seen.update(kwargs)
        return None, RetreatStage2Record(status="skipped", skip_reason="disabled")

    monkeypatch.setattr(reasoning_pipeline, "run_retreat_stage2", fake_stage2)
    pipeline = reasoning_pipeline.InProcessPipeline(
        reasoner=_FakeReasoner(_decision()),
        ground_fn=ground_reasoner_result,
        scene_geometry=_geometry(),
        grounding_params=GroundingParams(
            mode="derived", dynamic_scene_arms=True, escort_park_clearance=True
        ),
        goal_reference_of=lambda rid: (2.5, 0.0) if rid == "robot_1" else (-2.5, 0.0),
    )
    pipeline.run(_request())
    assert seen["goal_references"] == {"robot_1": (2.5, 0.0), "robot_2": (-2.5, 0.0)}

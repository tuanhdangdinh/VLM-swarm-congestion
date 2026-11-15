"""Escort obstacle guard: an escort's straight leg must clear the declared static boxes.

Live demo take `m5D_t01_a1` (docs/reports/2026-11-15-escort-obstacle-guard.md;
campaign report section 8.7): decision 2 (`a15f3fc5`) grounded robot_3's
escort due west for 1.604 m from (1.354, 0.607), straight through rack
island `obstacle_2` (x 0.25-0.80, y -0.90-0.70). The robot drove into the
island's east face and stayed pinned there until M4's deadline. No M3 stage
compared the escort leg with the declared boxes. Under
`GroundingParams.escort_obstacle_guard` each retreat candidate whose escort
leg (as M4 drives it, after the heading and the turn cap) enters a box grown
by `robot.half_width_m + retreat_box_margin_m` is dropped, as the A28(ii)
escort/park filter drops one that passes the park point; when none survives
the yield is infeasible and degrades to the reroute M5 withholds.

Fixture (`data/escort_obstacle_guard/m5d_t01_a1.json`): the take's two
escort decisions with their snapshots, stage-2 labels, grounding params,
the bundle's scenario geometry and static obstacles, and the dispatched
commands.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from swarm_orchestrator.reasoning_pipeline import empty_reroute_fallback, load_grounding_source

from reasoning.rag.command_grounder import (
    DEGRADATION_TAGS,
    degradation_cause,
    ground_reasoner_result,
    plan_matches_dispatch,
    prepare_filtered_retreat_selection,
    resolve_yield_roles,
    verify_and_repair_plan,
)
from reasoning.rag.escort_obstacles import (
    escort_hits_obstacle_reason,
    escort_obstacle_hits,
    escort_obstacle_margin_m,
    grown_obstacle_boxes,
    segment_entry_m,
)
from reasoning.rag.grounding_view import resolve_grounding_view
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RetreatChoiceDecision,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads(
    (Path(__file__).parent / "data/escort_obstacle_guard/m5d_t01_a1.json").read_text(
        encoding="utf-8"
    )
)
CASES = {case["case"]: case for case in FIXTURE["cases"]}
BLOCKED = "decision_2_robot_3"
CLEAR = "decision_1_robot_4"
FRAGMENT = REPO_ROOT / "config/grounding/escort_obstacle_guard.fragment.yaml"
KIT_BASE = REPO_ROOT / "config/grounding/s1b_dynamic_shield_escort.yaml"
# M5's plan id and the A26(ii) fast-fail mark: added by M5 / the post-passes
# after grounding, not part of what this replay grounds.
_IGNORED = {"plan_id", "fresh_latch_fast_fail"}
_BOX = (1.0, 2.0, -0.5, 0.5)


class _Config(NamedTuple):
    # The three bundle config fields the grounder reads.
    scenario_geometry: SceneGeometry
    static_obstacles: tuple[StaticObstacleInput, ...]
    grounding_yield_feasibility: str


def _config() -> _Config:
    return _Config(
        SceneGeometry.model_validate(FIXTURE["scenario_geometry"]),
        tuple(StaticObstacleInput.model_validate(o) for o in FIXTURE["static_obstacles"]),
        FIXTURE["grounding_yield_feasibility"],
    )


def _params(case: dict[str, Any], **updates: Any) -> GroundingParams:
    return GroundingParams(**{**case["grounding_params"], **updates})


def _frame(case: dict[str, Any]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=case["stamp"],
        robots=[
            RobotStateInput(
                robot_id=r["robot_id"],
                x=r["x"],
                y=r["y"],
                theta=r["theta"],
                status=r["status"],
                goal=tuple(r["goal"]),
            )
            for r in case["rows"]
        ],
    )


def _goals(case: dict[str, Any]) -> dict[str, tuple[float, float]]:
    return {r["robot_id"]: tuple(r["goal"]) for r in case["rows"]}


def _result(case: dict[str, Any]) -> ReasonerResult:
    diag = ReasonerDiagnostics(request_id="r", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(
        request_id="r",
        decision=CongestionDecision.model_validate(case["decision"]),
        raw_text="{}",
        diagnostics=diag,
    )


def _ground(case: dict[str, Any], params: GroundingParams) -> dict[str, Any]:
    config = _config()
    frame = _frame(case)
    label = case["retreat_choice"]
    return ground_reasoner_result(
        _result(case),
        robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        snapshot=frame,
        params=params,
        retreat_choice=(
            None
            if label is None
            else RetreatChoiceDecision(retreat_choice=label, justification="live")
        ),
        goal_references=_goals(case),
    )


def _yield(command: dict[str, Any]) -> dict[str, Any] | None:
    return next((a for a in command["actions"] if a["action"] == "yield"), None)


def _stripped(parameters: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in parameters.items() if k not in _IGNORED}


def _unshielded(tags: list[str]) -> list[str]:
    # The replay passes no M5 task intents, so the A26 shield holds no one.
    return [tag for tag in tags if not tag.startswith("grounding=retreat_shield")]


def _view_geometry(case: dict[str, Any], params: GroundingParams):
    config = _config()
    return resolve_grounding_view(
        CongestionDecision.model_validate(case["decision"]),
        _frame(case),
        config.scenario_geometry,
        params,
        _goals(case),
    ).geometry


def _obstacle(obstacle_id: str, x: float, y: float, sx: float, sy: float) -> StaticObstacleInput:
    return StaticObstacleInput(obstacle_id=obstacle_id, x=x, y=y, size_x_m=sx, size_y_m=sy)


# ---- pure geometry: the centreline against one grown box ----


def test_segment_entry_is_none_when_box_is_beside_the_segment():
    assert segment_entry_m((0.0, 2.0), 0.0, 3.0, _BOX) is None


def test_segment_entry_is_the_face_distance_when_segment_crosses_the_box():
    assert segment_entry_m((0.0, 0.0), 0.0, 3.0, _BOX) == pytest.approx(1.0)


def test_segment_entry_is_none_when_segment_ends_before_the_box():
    assert segment_entry_m((0.0, 0.0), 0.0, 0.9, _BOX) is None


def test_segment_entry_is_none_when_segment_ends_exactly_on_the_face():
    assert segment_entry_m((0.0, 0.0), 0.0, 1.0, _BOX) is None


def test_segment_entry_is_none_when_segment_runs_along_a_face():
    # Touching a grown face is the margin met exactly, not an overlap.
    assert segment_entry_m((0.0, 0.5), 0.0, 3.0, _BOX) is None


def test_segment_entry_is_none_when_segment_only_touches_a_corner():
    # The line y = x - 0.5 touches the corner (1.0, 0.5) only.
    assert segment_entry_m((0.0, -0.5), math.pi / 4, 3.0, _BOX) is None


def test_segment_entry_is_none_for_a_zero_length_segment():
    assert segment_entry_m((1.5, 0.0), 0.0, 0.0, _BOX) is None


def test_segment_entry_measures_a_diagonal_heading():
    box = (0.76, 1.24, 0.76, 1.24)
    assert segment_entry_m((0.0, 0.0), math.pi / 4, 2.0, box) == pytest.approx(0.76 * math.sqrt(2))


def test_segment_entry_catches_a_diagonal_corner_clip():
    # The line y = x - 0.52 is inside only for x in (1.00, 1.02): a 0.028 m
    # clip between t = 1.414 and 1.443 that 0.1 m samples (1.4, 1.5) miss.
    entry = segment_entry_m((0.0, -0.52), math.pi / 4, 3.0, _BOX)
    assert entry == pytest.approx(math.sqrt(2))


def test_segment_entry_is_zero_when_start_inside_and_heading_deeper():
    assert segment_entry_m((1.1, 0.0), 0.0, 0.5, _BOX) == 0.0


def test_segment_entry_is_none_when_start_inside_and_heading_out():
    # The retreat sweep's floor rule: no deeper, but no veto.
    assert segment_entry_m((1.1, 0.0), math.pi, 0.5, _BOX) is None


def test_segment_entry_is_none_when_start_inside_and_heading_along_the_near_face():
    assert segment_entry_m((1.1, 0.0), math.pi / 2, 0.4, _BOX) is None


def test_grown_boxes_add_the_margin_on_every_side():
    (box,) = grown_obstacle_boxes([_obstacle("o", 0.525, -0.1, 0.55, 1.6)], 0.14)
    assert box.obstacle_id == "o"
    assert (box.x_min, box.x_max, box.y_min, box.y_max) == pytest.approx(
        (0.11, 0.94, -1.04, 0.84)
    )


def test_grazing_within_the_margin_blocks_the_segment():
    # Centreline 0.10 m from the bare face: inside half-width 0.09 + 0.05.
    (box,) = grown_obstacle_boxes([_obstacle("o", 1.5, 0.6, 1.0, 1.0)], 0.14)
    assert segment_entry_m((0.0, 0.0), 0.0, 3.0, (box.x_min, box.x_max, box.y_min, box.y_max))


def test_passing_beyond_the_margin_leaves_the_segment_clear():
    (box,) = grown_obstacle_boxes([_obstacle("o", 1.5, 0.65, 1.0, 1.0)], 0.14)
    bounds = (box.x_min, box.x_max, box.y_min, box.y_max)
    assert segment_entry_m((0.0, 0.0), 0.0, 3.0, bounds) is None


# ---- the margin is the retreat sweep's ----


def test_margin_is_half_width_plus_the_retreat_box_margin():
    case = CASES[BLOCKED]
    params = _params(case)
    assert escort_obstacle_margin_m(_view_geometry(case, params), params) == pytest.approx(0.14)


# ---- the live legs ----


def test_decision_2_leg_enters_obstacle_2_after_0_414_m():
    case = CASES[BLOCKED]
    params = _params(case)
    live = _yield(case["dispatched_command"])
    (hit,) = escort_obstacle_hits(
        live["robot_id"],
        live["parameters"],
        _frame(case),
        _view_geometry(case, params),
        _config().static_obstacles,
        0.14,
    )
    assert hit.passer_id == "robot_3"
    assert hit.obstacle_id == "obstacle_2"
    assert hit.heading_rad == pytest.approx(math.pi)
    assert hit.distance_m == 1.604
    # 1.354 (snapshot x) - 0.94 (east face 0.80 + 0.14).
    assert hit.clear_m == pytest.approx(0.414, abs=1e-3)
    assert escort_hits_obstacle_reason(hit) == "escort_hits_obstacle:robot_3:obstacle_2:0.414"


def test_decision_1_leg_clears_every_box():
    case = CASES[CLEAR]
    params = _params(case)
    live = _yield(case["dispatched_command"])
    hits = escort_obstacle_hits(
        live["robot_id"],
        live["parameters"],
        _frame(case),
        _view_geometry(case, params),
        _config().static_obstacles,
        0.14,
    )
    assert hits == []


def test_leg_without_a_park_point_is_still_swept():
    # Unlike the park-point check, the obstacle sweep needs no park point.
    case = CASES[BLOCKED]
    params = _params(case)
    live = _yield(case["dispatched_command"])
    parameters = {
        k: v for k, v in live["parameters"].items() if k not in ("retreat_x_m", "retreat_y_m")
    }
    hits = escort_obstacle_hits(
        live["robot_id"],
        parameters,
        _frame(case),
        _view_geometry(case, params),
        _config().static_obstacles,
        0.14,
    )
    assert [hit.obstacle_id for hit in hits] == ["obstacle_2"]


# ---- key off: byte-identical ----


@pytest.mark.parametrize("name", sorted(CASES))
def test_regrounding_reproduces_the_dispatched_yield_when_guard_off(name):
    case = CASES[name]
    command = _ground(case, _params(case))
    live = case["dispatched_command"]
    assert _stripped(_yield(command)["parameters"]) == _stripped(_yield(live)["parameters"])
    assert command["degradations"] == _unshielded(live["degradations"])


@pytest.mark.parametrize("name", sorted(CASES))
def test_guard_false_grounds_the_same_command_as_guard_absent(name):
    case = CASES[name]
    assert _ground(case, _params(case, escort_obstacle_guard=False)) == _ground(
        case, _params(case)
    )


def test_params_dump_omits_the_guard_when_off():
    assert "escort_obstacle_guard" not in GroundingParams().model_dump(mode="json")


def test_params_dump_carries_the_guard_when_on():
    dump = GroundingParams(escort_obstacle_guard=True).model_dump(mode="json")
    assert dump["escort_obstacle_guard"] is True


# ---- key on: decision 2 refused, decision 1 unchanged ----


def test_decision_2_grounds_no_yield_when_guard_on():
    case = CASES[BLOCKED]
    command = _ground(case, _params(case, escort_obstacle_guard=True))
    assert _yield(command) is None
    assert [a["action"] for a in command["actions"]][0] == "reroute"


def test_decision_2_names_the_obstacle_and_clear_length_when_guard_on():
    case = CASES[BLOCKED]
    command = _ground(case, _params(case, escort_obstacle_guard=True))
    # Candidate B (park-filtered) ranks below D, so the obstacle is the cause.
    infeasible = [t for t in command["degradations"] if t.startswith("yield=infeasible:")]
    assert infeasible == ["yield=infeasible:escort_hits_obstacle:robot_3:obstacle_2:0.414"]


def test_decision_2_tags_every_dropped_candidate_when_guard_on():
    case = CASES[BLOCKED]
    command = _ground(case, _params(case, escort_obstacle_guard=True))
    filtered = [t for t in command["degradations"] if t.startswith("retreat=escort_obstacle")]
    # Generation labels in rank order; B was already dropped by the park check.
    assert filtered == [
        "retreat=escort_obstacle_filtered:D:robot_3:obstacle_2:0.414",
        "retreat=escort_obstacle_filtered:A:robot_3:obstacle_2:0.414",
        "retreat=escort_obstacle_filtered:C:robot_3:obstacle_2:0.414",
    ]
    assert "retreat=escort_park_filtered:B:robot_3:0.151" in command["degradations"]


def test_decision_2_keeps_the_kept_yielder_when_guard_on():
    # A29's asymmetric rule: the gate-kept yielder's partner retry reads the
    # unfiltered selection, so a filtered-out escort reroutes, never swaps.
    case = CASES[BLOCKED]
    command = _ground(case, _params(case, escort_obstacle_guard=True))
    assert not any("sweep_regrounded" in tag for tag in command["degradations"])
    assert command["actions"][0]["robot_id"] == "robot_2"


def test_decision_2_refusal_is_withheld_by_m5():
    case = CASES[BLOCKED]
    command = _ground(case, _params(case, escort_obstacle_guard=True))
    assert empty_reroute_fallback(command) == (
        "yield=infeasible:escort_hits_obstacle:robot_3:obstacle_2:0.414"
    )


def test_decision_1_is_unchanged_when_guard_on():
    case = CASES[CLEAR]
    assert _ground(case, _params(case, escort_obstacle_guard=True)) == _ground(
        case, _params(case)
    )


def test_selection_is_empty_with_an_obstacle_cause_when_every_escort_is_blocked():
    case = CASES[BLOCKED]
    params = _params(case, escort_obstacle_guard=True)
    config = _config()
    frame = _frame(case)
    geometry = _view_geometry(case, params)
    roles = resolve_yield_roles(
        CongestionDecision.model_validate(case["decision"]),
        frame,
        geometry=geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        params=params,
        goal_references=_goals(case),
    )
    selection = prepare_filtered_retreat_selection(
        frame,
        roles.yielder_id,
        roles.crossing_order,
        params,
        geometry=geometry,
        static_obstacles=config.static_obstacles,
        goal_references=_goals(case),
    )
    assert selection.candidates == []
    assert selection.escort_obstacle_infeasible == [
        "escort_hits_obstacle:robot_3:obstacle_2:0.414"
    ]


def test_plan_verifier_agrees_with_dispatch_when_guard_on():
    case = CASES[BLOCKED]
    params = _params(case, escort_obstacle_guard=True)
    config = _config()
    verified = verify_and_repair_plan(
        CongestionDecision.model_validate(case["decision"]),
        _frame(case),
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        grounding_params=params,
        goal_references=_goals(case),
    )
    command = _ground(case, params)
    ids = [r["robot_id"] for r in case["rows"]]
    assert plan_matches_dispatch(verified.legs, command, ids)


# ---- vocabulary and the kit fragment ----


def test_filter_tag_is_provenance_and_refusal_is_infeasible_geometry():
    assert "retreat=escort_obstacle_filtered" in DEGRADATION_TAGS
    assert degradation_cause("retreat=escort_obstacle_filtered:A:robot_3:obstacle_2:0.414") is None
    assert (
        degradation_cause("yield=infeasible:escort_hits_obstacle:robot_3:obstacle_2:0.414")
        == "infeasible_geometry"
    )


def test_fragment_turns_on_only_the_guard_over_the_kit_grounding_file(tmp_path):
    import yaml

    base = yaml.safe_load(KIT_BASE.read_text(encoding="utf-8"))
    fragment = yaml.safe_load(FRAGMENT.read_text(encoding="utf-8"))
    assert fragment == {"grounding": {"escort_obstacle_guard": True}}
    merged = {**base, "grounding": {**base["grounding"], **fragment["grounding"]}}
    path = tmp_path / "grounding.yaml"
    path.write_text(yaml.safe_dump(merged), encoding="utf-8")
    on = load_grounding_source(path).params
    off = load_grounding_source(KIT_BASE).params
    assert on.escort_obstacle_guard is True
    assert on.model_copy(update={"escort_obstacle_guard": False}) == off

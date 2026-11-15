"""Reverse obstacle guard: a `reverse` strategy's backup legs must clear the declared boxes.

Validation take `m5V_t01_a1` (docs/reports/2026-11-15-escort-obstacle-guard.md,
section 8): decision `95066420` grounded a VLM `reverse` for robot_4 and
robot_5, 1.3 m each, backward along their snapshot headings. Both legs run
past rack island `obstacle_1` (x -1.30..-0.75, y -0.70..0.90): robot_4 came
within 5.5 mm of its south-west corner, robot_5 within 19 mm of its
north-west corner (ground truth). M3's reverse grounding never compared the
legs with the declared boxes. Under `GroundingParams.reverse_obstacle_guard`
each backup leg (snapshot start, heading theta + pi, the dispatched distance)
is swept with the escort guard's own test (`escort_obstacles.segment_entry_m`
against boxes grown by `robot.half_width_m + retreat_box_margin_m`); one
blocked leg refuses the whole reverse into the same 8 s wait fan-out the
corridor same-side refusal dispatches.

Fixture (`data/escort_obstacle_guard/reverse_cases.json`): decisions
`95066420` (both legs blocked) and `b07a700f` (three legs, all clear) of
`m5V_t01_a1`, and `d374802a` of the October bundle `s1b_E12_seed12_er2_c1`
(robot_2 blocked by the declared north wall, robot_4 clear), with their
snapshots, grounding params and dispatched commands, and the scene geometry
and static obstacles the two bundles share.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from swarm_orchestrator.reasoning_pipeline import (
    empty_reroute_fallback,
    load_grounding_source,
    yield_refusal_fan_out,
)

from reasoning.rag.command_grounder import (
    degradation_cause,
    ground_reasoner_result,
    plan_matches_dispatch,
    verify_and_repair_plan,
)
from reasoning.rag.escort_obstacles import (
    grown_obstacle_boxes,
    reverse_hits_obstacle_reason,
    reverse_obstacle_hits,
    segment_entry_m,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads(
    (Path(__file__).parent / "data/escort_obstacle_guard/reverse_cases.json").read_text(
        encoding="utf-8"
    )
)
CASES = {case["case"]: case for case in FIXTURE["cases"]}
BLOCKED = "m5v_95066420"
CLEAR = "m5v_b07a700f"
ONE_BLOCKED = "e12_d374802a"
FRAGMENT = REPO_ROOT / "config/grounding/reverse_obstacle_guard.fragment.yaml"
KIT_BASE = REPO_ROOT / "config/grounding/s1b_dynamic_shield_escort.yaml"
# M5's plan id is added after grounding.
_IGNORED = {"plan_id"}
_MARGIN = 0.14


def _geometry() -> SceneGeometry:
    return SceneGeometry.model_validate(FIXTURE["scenario_geometry"])


def _obstacles() -> tuple[StaticObstacleInput, ...]:
    return tuple(StaticObstacleInput.model_validate(o) for o in FIXTURE["static_obstacles"])


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


def _decision(case: dict[str, Any], **updates: Any) -> CongestionDecision:
    return CongestionDecision.model_validate({**case["decision"], **updates})


def _ground(
    case: dict[str, Any], params: GroundingParams, decision: CongestionDecision | None = None
) -> dict[str, Any]:
    frame = _frame(case)
    diag = ReasonerDiagnostics(request_id="r", backend_id="mock", attempts=1, parse_status="valid")
    result = ReasonerResult(
        request_id="r",
        decision=decision or _decision(case),
        raw_text="{}",
        diagnostics=diag,
    )
    return ground_reasoner_result(
        result,
        robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
        geometry=_geometry(),
        static_obstacles=_obstacles(),
        yield_feasibility_mode=FIXTURE["grounding_yield_feasibility"],
        snapshot=frame,
        params=params,
        goal_references=_goals(case),
    )


def _verify(case: dict[str, Any], params: GroundingParams, decision: CongestionDecision):
    return verify_and_repair_plan(
        decision,
        _frame(case),
        geometry=_geometry(),
        static_obstacles=_obstacles(),
        yield_feasibility_mode=FIXTURE["grounding_yield_feasibility"],
        grounding_params=params,
        goal_references=_goals(case),
    )


def _actions(command: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **action,
            "parameters": {
                k: v for k, v in (action.get("parameters") or {}).items() if k not in _IGNORED
            },
        }
        for action in command["actions"]
    ]


def _legs(case: dict[str, Any], robot_ids: list[str]) -> list[tuple[str, float]]:
    return [
        (a["robot_id"], a["parameters"]["backup_distance_m"])
        for a in case["dispatched_command"]["actions"]
        if a["action"] == "reverse" and a["robot_id"] in robot_ids
    ]


def _ids(case: dict[str, Any]) -> list[str]:
    return [r["robot_id"] for r in case["rows"]]


def _plan(case: dict[str, Any], actions: dict[str, str]) -> list[ProposedPlanLeg]:
    return [
        ProposedPlanLeg(robot_id=rid, action=actions.get(rid, "continue")) for rid in _ids(case)
    ]


# ---- the leg and its geometry: the escort guard's test, reused ----


def test_reverse_leg_starts_at_the_snapshot_pose_and_runs_backward():
    case = CASES[BLOCKED]
    frame = _frame(case)
    (hit, _) = reverse_obstacle_hits(
        _legs(case, ["robot_4", "robot_5"]), frame, _obstacles(), _MARGIN
    )
    state = frame.find_robot("robot_4")
    assert hit.robot_id == "robot_4"
    assert hit.start_xy == (state.x, state.y)
    backward = state.theta + math.pi
    assert math.cos(hit.heading_rad) == pytest.approx(math.cos(backward))
    assert math.sin(hit.heading_rad) == pytest.approx(math.sin(backward))
    assert hit.distance_m == 1.3


def test_reverse_clear_length_is_the_escort_segment_entry():
    case = CASES[BLOCKED]
    frame = _frame(case)
    (hit, _) = reverse_obstacle_hits(
        _legs(case, ["robot_4", "robot_5"]), frame, _obstacles(), _MARGIN
    )
    box = next(
        b for b in grown_obstacle_boxes(_obstacles(), _MARGIN) if b.obstacle_id == "obstacle_1"
    )
    assert hit.clear_m == segment_entry_m(hit.start_xy, hit.heading_rad, hit.distance_m, box.bounds)


def test_reverse_reason_names_robot_obstacle_and_clear_length():
    case = CASES[BLOCKED]
    (hit, _) = reverse_obstacle_hits(
        _legs(case, ["robot_4", "robot_5"]), _frame(case), _obstacles(), _MARGIN
    )
    assert reverse_hits_obstacle_reason(hit) == "reverse_hits_obstacle:robot_4:obstacle_1:0.305"


def test_reverse_hits_are_empty_without_declared_obstacles():
    case = CASES[BLOCKED]
    assert reverse_obstacle_hits(_legs(case, ["robot_4"]), _frame(case), (), _MARGIN) == []


def test_reverse_leg_of_a_robot_missing_from_the_snapshot_is_skipped():
    case = CASES[BLOCKED]
    assert reverse_obstacle_hits([("robot_9", 1.3)], _frame(case), _obstacles(), _MARGIN) == []


# ---- decision 95066420: the arithmetic ----


def test_95066420_robot_4_enters_obstacle_1_after_0_305_m():
    case = CASES[BLOCKED]
    hits = reverse_obstacle_hits(_legs(case, ["robot_4"]), _frame(case), _obstacles(), _MARGIN)
    (hit,) = hits
    # Backward heading 1.9601 - pi = -1.1815 rad; the grown west face of
    # obstacle_1 is x = -1.30 - 0.14 = -1.44, reached after
    # (-1.44 + 1.5559) / cos(-1.1815) = 0.1159 / 0.3803 = 0.305 m, at
    # y = -0.352 - 0.305 * 0.925 = -0.634, inside the grown y range.
    assert hit.obstacle_id == "obstacle_1"
    assert hit.clear_m == pytest.approx(0.305, abs=1e-3)


def test_95066420_robot_5_enters_obstacle_1_after_0_844_m():
    case = CASES[BLOCKED]
    (hit,) = reverse_obstacle_hits(
        _legs(case, ["robot_5"]), _frame(case), _obstacles(), _MARGIN
    )
    # Backward heading -1.8218 + pi = 1.3198 rad: x reaches -1.44 after
    # (-1.44 + 1.6496) / cos(1.3198) = 0.2096 / 0.2482 = 0.844 m, at
    # y = 0.008 + 0.844 * 0.969 = 0.825, inside the grown y range (to 1.04).
    assert hit.obstacle_id == "obstacle_1"
    assert hit.clear_m == pytest.approx(0.844, abs=1e-3)


# ---- key on: refused like the same-side refusal ----


def test_95066420_is_refused_into_a_wait_fan_out_when_guard_on():
    case = CASES[BLOCKED]
    command = _ground(case, _params(case, reverse_obstacle_guard=True))
    assert [a["robot_id"] for a in command["actions"]] == ["robot_4", "robot_5"]
    for action in command["actions"]:
        assert action["action"] == "temporary_wait"
        assert action["parameters"] == {
            "duration_sec": 8.0,
            "requested_strategy": "reverse",
            "reason": "reverse_hits_obstacle:robot_4:obstacle_1:0.305",
        }
    assert command["expected_resolution_time_sec"] == 8.0


def test_95066420_tags_every_blocked_leg_when_guard_on():
    case = CASES[BLOCKED]
    command = _ground(case, _params(case, reverse_obstacle_guard=True))
    assert command["degradations"] == [
        "reverse=infeasible:reverse_hits_obstacle:robot_4:obstacle_1:0.305",
        "reverse=infeasible:reverse_hits_obstacle:robot_5:obstacle_1:0.844",
        "grounding=dynamic_arms:lane:y",
    ]


def test_refused_reverse_is_dispatched_like_the_same_side_refusal():
    # Precedent (m5V `929335f4`, `2acc6130`): a refused reverse's waits are
    # dispatched; M5 withholds only refused yields and empty reroutes.
    case = CASES[BLOCKED]
    command = _ground(case, _params(case, reverse_obstacle_guard=True))
    assert yield_refusal_fan_out(command) is None
    assert empty_reroute_fallback(command) is None


def test_refusal_tag_counts_as_infeasible_geometry():
    assert (
        degradation_cause("reverse=infeasible:reverse_hits_obstacle:robot_4:obstacle_1:0.305")
        == "infeasible_geometry"
    )


def test_clear_reverse_is_unchanged_when_guard_on():
    case = CASES[CLEAR]
    assert _ground(case, _params(case, reverse_obstacle_guard=True)) == _ground(
        case, _params(case)
    )


def test_one_blocked_robot_refuses_the_whole_reverse():
    # Same-side precedent: the refusal holds every involved robot, never a
    # partial reverse of the clear ones.
    case = CASES[ONE_BLOCKED]
    command = _ground(case, _params(case, reverse_obstacle_guard=True))
    assert [(a["robot_id"], a["action"]) for a in command["actions"]] == [
        ("robot_2", "temporary_wait"),
        ("robot_4", "temporary_wait"),
    ]
    infeasible = [t for t in command["degradations"] if t.startswith("reverse=infeasible:")]
    assert infeasible == ["reverse=infeasible:reverse_hits_obstacle:robot_2:obstacle_5:1.267"]


def test_only_the_blocked_robot_of_d374802a_has_a_hit():
    case = CASES[ONE_BLOCKED]
    hits = reverse_obstacle_hits(
        _legs(case, ["robot_2", "robot_4"]), _frame(case), _obstacles(), _MARGIN
    )
    assert [(h.robot_id, h.obstacle_id) for h in hits] == [("robot_2", "obstacle_5")]


# ---- key off: byte-identical ----


@pytest.mark.parametrize("name", sorted(CASES))
def test_regrounding_reproduces_the_dispatched_reverse_when_guard_off(name):
    case = CASES[name]
    command = _ground(case, _params(case))
    live = case["dispatched_command"]
    assert _actions(command) == _actions(live)
    assert command["degradations"] == live["degradations"]


@pytest.mark.parametrize("name", sorted(CASES))
def test_guard_false_grounds_the_same_command_as_guard_absent(name):
    case = CASES[name]
    assert _ground(case, _params(case, reverse_obstacle_guard=False)) == _ground(
        case, _params(case)
    )


def test_escort_guard_alone_leaves_the_validated_reverse_unchanged():
    # m5V_t01_a1 ran with escort_obstacle_guard on; its reverse still grounds.
    case = CASES[BLOCKED]
    assert case["grounding_params"]["escort_obstacle_guard"] is True
    command = _ground(case, _params(case))
    assert [a["action"] for a in command["actions"]] == ["reverse", "reverse"]


def test_params_dump_omits_the_reverse_guard_when_off():
    assert "reverse_obstacle_guard" not in GroundingParams().model_dump(mode="json")


def test_params_dump_carries_the_reverse_guard_when_on():
    dump = GroundingParams(reverse_obstacle_guard=True).model_dump(mode="json")
    assert dump["reverse_obstacle_guard"] is True


def test_legacy_mode_ignores_the_reverse_guard():
    case = CASES[BLOCKED]
    on = _params(case, mode="legacy", reverse_obstacle_guard=True)
    off = _params(case, mode="legacy")
    assert _ground(case, on) == _ground(case, off)


# ---- the plan verifier agrees with dispatch ----


def test_default_plan_waits_every_reverse_robot_when_guard_on():
    case = CASES[BLOCKED]
    params = _params(case, reverse_obstacle_guard=True)
    decision = _decision(case, proposed_plan=None)
    verified = _verify(case, params, decision)
    assert verified.provenance == "m3_default"
    assert {leg.robot_id: leg.action for leg in verified.legs}["robot_4"] == "wait"
    assert plan_matches_dispatch(verified.legs, _ground(case, params, decision), _ids(case))


def test_plan_verifier_flags_a_blocked_reverse_leg_when_guard_on():
    case = CASES[BLOCKED]
    params = _params(case, reverse_obstacle_guard=True)
    decision = _decision(
        case, proposed_plan=_plan(case, {"robot_4": "reverse", "robot_5": "reverse"})
    )
    verified = _verify(case, params, decision)
    assert verified.provenance != "vlm_verbatim"
    by_robot = {leg.robot_id: leg.action for leg in verified.legs}
    assert (by_robot["robot_4"], by_robot["robot_5"]) == ("wait", "wait")
    assert plan_matches_dispatch(verified.legs, _ground(case, params, decision), _ids(case))


def test_plan_verifier_keeps_the_reverse_plan_when_guard_off():
    case = CASES[BLOCKED]
    params = _params(case)
    decision = _decision(
        case, proposed_plan=_plan(case, {"robot_4": "reverse", "robot_5": "reverse"})
    )
    verified = _verify(case, params, decision)
    assert verified.provenance == "vlm_verbatim"
    assert plan_matches_dispatch(verified.legs, _ground(case, params, decision), _ids(case))


def test_plan_verifier_keeps_a_clear_reverse_plan_when_guard_on():
    case = CASES[CLEAR]
    params = _params(case, reverse_obstacle_guard=True)
    reversing = [a["robot_id"] for a in case["dispatched_command"]["actions"]]
    decision = _decision(
        case, proposed_plan=_plan(case, dict.fromkeys(reversing, "reverse"))
    )
    assert _verify(case, params, decision) == _verify(case, _params(case), decision)


# ---- the kit fragment ----


def test_fragment_turns_on_only_the_reverse_guard_over_the_kit_grounding_file(tmp_path):
    import yaml

    base = yaml.safe_load(KIT_BASE.read_text(encoding="utf-8"))
    fragment = yaml.safe_load(FRAGMENT.read_text(encoding="utf-8"))
    assert fragment == {"grounding": {"reverse_obstacle_guard": True}}
    merged = {**base, "grounding": {**base["grounding"], **fragment["grounding"]}}
    path = tmp_path / "grounding.yaml"
    path.write_text(yaml.safe_dump(merged), encoding="utf-8")
    on = load_grounding_source(path).params
    off = load_grounding_source(KIT_BASE).params
    assert on.reverse_obstacle_guard is True
    assert on.model_copy(update={"reverse_obstacle_guard": False}) == off

"""Plan-leg / dispatch parity for lane-scoped off-lane holds (prereg-v3 A21).

Under a dynamic lane view `resolve_yield_roles` moves every robot outside
the lane conflict from the crossing order to `YieldRoles.off_lane`
(`order=lane_scoped:<ids>`), and dispatch holds them on a plain `wait`
beside the yield. `_plan_problems` never checked them, so a plan crossing
one verified `vlm_verbatim` (or `repaired` on other grounds) with
`dispatch_matches_plan=False` (A18 residual (1); reproduced on
feat/v3-integration@0b659d2, `base_plan` in the fixture file). The verifier
now reads the held set from the same outcome as the A18 yielder verdict and
repairs each such leg by one `substitute` to `wait`, with a
`LANE_SCOPED_HOLD_PREFIX` reason that `plan_metrics` stratifies.

Fixtures are MC first-conflict scenes from `scripts/plan_parity_mc_replay.py`
(`data/plan_offlane_hold/mc_scenes.json`); the scripted plan is the echo
decision's own yield with every other involved robot crossing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from reasoning.rag import command_grounder
from reasoning.rag.command_grounder import (
    LANE_SCOPED_HOLD_PREFIX,
    PlanRepairParams,
    _plan_dispatch_outcome,
    _plan_off_lane_holds,
    ground_reasoner_result,
    plan_matches_dispatch,
    resolve_yield_roles,
    verify_and_repair_plan,
)
from reasoning.rag.grounding_view import resolve_grounding_view
from reasoning.rag.plan_metrics import (
    is_lane_scope_only_repair,
    score_decision_artifact,
    score_plan_decision,
    tabulate_provenance_by_strategy_correctness,
)
from reasoning.vlm.models import CongestionDecision, ProposedPlanLeg
from tests.unit.test_s1_resolvability import (
    _echo_decision,
    _floor,
    _frame,
    _reasoner_result,
)

CASES: dict[str, dict[str, Any]] = json.loads(
    (Path(__file__).parent / "data" / "plan_offlane_hold" / "mc_scenes.json").read_text()
)["cases"]

# Plans whose only defect is the hold: the repair is one substitute per held robot.
HOLD_ONLY = [
    "s1a_seed8_vb_one_hold",
    "s1b_seed11_vb_one_hold",
    "s1b_seed391_vb_three_holds",
    "s1a_seed33_reorder_to_holds",
]
# Plans that also name a yielder dispatch re-grounds (A16(v)/A17/A18): one
# swap first, then the hold substitutes. `(named, final)` per case.
COMPOSED = {
    "s1a_seed153_sweep_retry_and_hold": ("robot_1", "robot_2"),
    "s1b_seed142_heading_handover_and_hold": ("robot_1", "robot_2"),
    "s1b_seed148_room_swap_and_three_holds": ("robot_1", "robot_2"),
}


def _scene(name: str):
    case = CASES[name]
    config, params = _floor(case["floor"])
    return case, config, params, _frame(case["rows"])


def _plan(involved: list[str], **extra: Any) -> CongestionDecision:
    legs = [ProposedPlanLeg(robot_id=involved[0], action="yield")]
    legs += [ProposedPlanLeg(robot_id=r, action="cross") for r in involved[1:]]
    return _echo_decision(involved, proposed_plan=legs, **extra)


def _verify(decision, frame, config, params, **kwargs: Any):
    return verify_and_repair_plan(
        decision,
        frame,
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=kwargs.pop("mode", "swap"),
        grounding_params=params,
        **kwargs,
    )


def _dispatch(involved, frame, config, params) -> dict[str, Any]:
    return ground_reasoner_result(
        _reasoner_result(_echo_decision(involved)),
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        snapshot=frame,
        params=params,
    )


def _known(frame) -> list[str]:
    return [r.robot_id for r in frame.robots]


def _hold_reason(robot_id: str, action: str = "cross") -> str:
    return (
        f"lane_scoped hold: {robot_id}: {action} substituted to wait; "
        f"dispatch holds {robot_id} outside the yield's lane conflict"
    )


# prereg-v3 A25 adds exactly these keys to a dynamic-lane yield (the swept
# backup line, `maneuver_geometry.backup_line_facing`); the baselines predate it.
_A25_KEYS = ("backup_facing_rad", "backup_reference_yaw_rad")


def _without_a25_keys(command: dict[str, Any]) -> dict[str, Any]:
    return {
        **command,
        "actions": [
            {
                **action,
                "parameters": {
                    k: v for k, v in (action.get("parameters") or {}).items() if k not in _A25_KEYS
                },
            }
            if action.get("action") == "yield"
            else action
            for action in command["actions"]
        ],
    }


@pytest.mark.parametrize("name", sorted(CASES))
def test_dispatched_command_is_byte_identical_to_the_baseline(name: str):
    # The fix is verifier-only: the derived path grounds exactly what
    # 0b659d2 grounded (sha over the sorted-key JSON of the command), apart
    # from the A25 backup-line keys.
    case, config, params, frame = _scene(name)
    command = _without_a25_keys(_dispatch(case["involved"], frame, config, params))
    digest = hashlib.sha256(json.dumps(command, sort_keys=True).encode()).hexdigest()
    assert digest == case["base_command_sha256"]


@pytest.mark.parametrize("name", sorted(CASES))
def test_held_set_is_the_dispatched_roles_off_lane(name: str):
    # Identity source: the same `_resolve_yield_outcome` -> `resolve_yield_roles`
    # chain dispatch grounds from, never the degradation tag.
    case, config, params, frame = _scene(name)
    view = resolve_grounding_view(
        _echo_decision(case["involved"]), frame, config.scenario_geometry, params
    )
    held = _plan_off_lane_holds(
        _plan_dispatch_outcome(
            view,
            frame,
            static_obstacles=config.static_obstacles,
            yield_feasibility_mode="swap",
            priorities=None,
            grounding_params=params,
        )
    )
    roles = resolve_yield_roles(
        view.decision,
        frame,
        geometry=view.geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        params=params,
    )
    command = _dispatch(case["involved"], frame, config, params)
    assert list(held) == roles.off_lane == case["off_lane"]
    assert f"order=lane_scoped:{','.join(case['off_lane'])}" in command["degradations"]


@pytest.mark.parametrize("name", sorted(CASES))
def test_pre_fix_audit_misses_the_hold(name: str, monkeypatch: pytest.MonkeyPatch):
    # Disabling the held set (the fix's only new verifier input) reproduces
    # the outcome measured on 0b659d2: legs that dispatch does not match.
    case, config, params, frame = _scene(name)
    monkeypatch.setattr(command_grounder, "_plan_off_lane_holds", lambda *a, **k: ())
    verified = _verify(_plan(case["involved"]), frame, config, params)
    command = _dispatch(case["involved"], frame, config, params)
    base = case["base_plan"]
    assert verified.provenance == base["provenance"]
    assert [[e.op, list(e.robot_ids)] for e in verified.edits] == base["edits"]
    assert plan_matches_dispatch(verified.legs, command, _known(frame)) is False
    assert base["dispatch_matches"] is False


@pytest.mark.parametrize("name", HOLD_ONLY)
def test_off_lane_cross_is_repaired_by_one_substitute_per_held_robot(name: str):
    case, config, params, frame = _scene(name)
    verified = _verify(_plan(case["involved"]), frame, config, params)
    assert verified.provenance == "repaired"
    assert [(e.op, e.robot_ids) for e in verified.edits] == [
        ("substitute", (rid,)) for rid in case["off_lane"]
    ]
    assert [e.reason for e in verified.edits] == [_hold_reason(rid) for rid in case["off_lane"]]


@pytest.mark.parametrize("name", HOLD_ONLY)
def test_hold_repaired_plan_matches_the_derived_dispatch(name: str):
    case, config, params, frame = _scene(name)
    verified = _verify(_plan(case["involved"]), frame, config, params)
    command = _dispatch(case["involved"], frame, config, params)
    assert plan_matches_dispatch(verified.legs, command, _known(frame))
    held = {leg.robot_id: leg.action for leg in verified.legs if leg.robot_id in case["off_lane"]}
    assert held == dict.fromkeys(case["off_lane"], "wait")


@pytest.mark.parametrize("name", sorted(COMPOSED))
def test_regrounded_yielder_and_hold_compose_in_one_repair(name: str):
    # The yielder verdict's swap comes first with its own reason; every held
    # robot (including the named yielder when dispatch holds it off the
    # lane, seed 148) then gets one substitute.
    named, final = COMPOSED[name]
    case, config, params, frame = _scene(name)
    verified = _verify(_plan(case["involved"]), frame, config, params)
    assert verified.provenance == "repaired"
    swap, *substitutes = verified.edits
    assert (swap.op, swap.robot_ids) == ("swap", tuple(sorted((named, final))))
    assert swap.reason.startswith("yield re-grounded: ")
    assert [(e.op, e.robot_ids) for e in substitutes] == [
        ("substitute", (rid,)) for rid in case["off_lane"]
    ]
    assert all(e.reason == _hold_reason(e.robot_ids[0]) for e in substitutes)
    command = _dispatch(case["involved"], frame, config, params)
    assert plan_matches_dispatch(verified.legs, command, _known(frame))


def test_composition_consumes_the_repair_bound():
    # One swap plus three hold substitutes is exactly the frozen bound (4).
    case, config, params, frame = _scene("s1b_seed148_room_swap_and_three_holds")
    at_bound = _verify(_plan(case["involved"]), frame, config, params)
    assert len(at_bound.edits) == PlanRepairParams().max_repair_edits == 4
    below = _verify(
        _plan(case["involved"]),
        frame,
        config,
        params,
        repair_params=PlanRepairParams(max_repair_edits=3),
    )
    assert below.provenance == "m3_default"
    assert below.rejection_reason == "repair distance exceeds bound 3"


def _with_held_leg(case: dict[str, Any], action: str | None) -> CongestionDecision:
    # The scripted plan with the first held robot's leg set to `action`, or
    # omitted (lenient completion) when None.
    held = case["off_lane"][0]
    legs = [ProposedPlanLeg(robot_id=case["involved"][0], action="yield")]
    for rid in case["involved"][1:]:
        if rid != held:
            legs.append(ProposedPlanLeg(robot_id=rid, action="cross"))
        elif action is not None:
            legs.append(ProposedPlanLeg(robot_id=rid, action=action))
    return _echo_decision(case["involved"], proposed_plan=legs)


def test_explicit_continue_on_a_held_robot_is_a_hold_substitute():
    case, config, params, frame = _scene("s1b_seed11_vb_one_hold")
    verified = _verify(_with_held_leg(case, "continue"), frame, config, params)
    assert verified.provenance == "repaired"
    assert [(e.op, e.robot_ids, e.reason) for e in verified.edits] == [
        ("substitute", ("robot_5",), _hold_reason("robot_5", "continue"))
    ]
    command = _dispatch(case["involved"], frame, config, params)
    assert plan_matches_dispatch(verified.legs, command, _known(frame))


def test_omitted_held_robot_is_completed_then_held():
    # Lenient completion gives the omitted robot `continue` (logged, not an
    # edit); dispatch holds it, so the repair substitutes it to `wait`.
    case, config, params, frame = _scene("s1b_seed11_vb_one_hold")
    verified = _verify(_with_held_leg(case, None), frame, config, params)
    assert "robot_5" in verified.plan_completed_legs
    assert [(e.op, e.robot_ids, e.reason) for e in verified.edits] == [
        ("substitute", ("robot_5",), _hold_reason("robot_5", "continue"))
    ]
    command = _dispatch(case["involved"], frame, config, params)
    assert plan_matches_dispatch(verified.legs, command, _known(frame))


def test_plan_that_holds_the_off_lane_robot_is_verbatim():
    case, config, params, frame = _scene("s1b_seed11_vb_one_hold")
    verified = _verify(_with_held_leg(case, "wait"), frame, config, params)
    assert verified.provenance == "vlm_verbatim"
    command = _dispatch(case["involved"], frame, config, params)
    assert plan_matches_dispatch(verified.legs, command, _known(frame))


def test_refuse_mode_leaves_the_hold_unchecked():
    # Same domain as the A18 yielder verdict (footprint view, `swap`,
    # derived params): refuse-mode plan legs stay outside it (registered).
    case, config, params, frame = _scene("s1b_seed11_vb_one_hold")
    verified = _verify(_plan(case["involved"]), frame, config, params, mode="refuse")
    assert verified.provenance == "vlm_verbatim"
    assert _plan_off_lane_holds(None) == ()


@pytest.mark.parametrize("name", sorted(CASES))
def test_lane_scope_only_stratum_separates_hold_only_repairs(name: str):
    case, config, params, frame = _scene(name)
    decision = _plan(case["involved"])
    verified = _verify(decision, frame, config, params)
    metrics = score_plan_decision(decision, verified, dispatch_matches_plan=True)
    assert metrics.repaired_lane_scope_only is (name in HOLD_ONLY)
    assert metrics.repaired_order_only is False
    artifact = {
        "decision": decision.model_dump(mode="json"),
        "plan": {
            "provenance": verified.provenance,
            "legs": [leg.model_dump(mode="json") for leg in verified.legs],
            "edits": [edit.model_dump(mode="json") for edit in verified.edits],
            "rejection_reason": verified.rejection_reason,
            "dispatch_matches_plan": True,
        },
    }
    assert score_decision_artifact(artifact) == metrics


def test_lane_scope_only_stratum_counts_in_the_provenance_table():
    rows = []
    for name in sorted(CASES):
        case, config, params, frame = _scene(name)
        decision = _plan(case["involved"])
        rows.append(score_plan_decision(decision, _verify(decision, frame, config, params)))
    table = tabulate_provenance_by_strategy_correctness(rows)
    assert table["strategy_unscored"].repaired == len(CASES)
    assert table["strategy_unscored"].repaired_lane_scope_only == len(HOLD_ONLY)


def test_lane_scope_only_needs_every_edit_to_be_a_hold_substitute():
    case, config, params, frame = _scene("s1a_seed153_sweep_retry_and_hold")
    edits = _verify(_plan(case["involved"]), frame, config, params).edits
    assert not is_lane_scope_only_repair(edits)
    assert is_lane_scope_only_repair(edits[1:])
    assert not is_lane_scope_only_repair([])
    assert LANE_SCOPED_HOLD_PREFIX == "lane_scoped hold:"

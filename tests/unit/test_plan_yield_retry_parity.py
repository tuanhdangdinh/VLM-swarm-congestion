"""Plan-leg / derived-path partner-retry parity (prereg-v3 A16(v)).

A16 taught `resolve_yield_roles` to retry the partner when the gate-kept
yielder has no executable retreat (infeasible backup, failed sweep or
infeasible escort). `verify_and_repair_plan` audited a model plan's yield leg
with the room check only, so a plan naming that kept yielder verified as
`vlm_verbatim` (reproduced on feat/v3-integration@31c8ce0) while dispatch
yielded the partner (`dispatch_matches_plan=False`), or refused the yield
outright. The verifier now reads the retry's verdict from the same function:
the plan is repaired by one `swap` onto the retried partner, or, when the
retry refuses, defaults to the refusal's waits with its true reason.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

import pytest

from reasoning.rag import command_grounder
from reasoning.rag.command_grounder import (
    _plan_problems,
    ground_reasoner_result,
    plan_matches_dispatch,
    verify_and_repair_plan,
)
from reasoning.rag.grounding_view import resolve_grounding_view
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
    RobotStateInput,
    SnapshotFrame,
)
from tests.unit.test_s1_resolvability import (
    FIXTURES,
    _echo_decision,
    _floor,
    _frame,
    _reasoner_result,
)
from tests.unit.test_s1_retreat_room import _EP1_GOALS, _EP1_SCENE, _FIVE, _shipped
from tests.unit.test_s1_retreat_room import _decision as _retreat_decision
from tests.unit.test_s1_retreat_room import _frame as _retreat_frame


def _plan(involved: list[str], yielder: str, **extra: Any) -> CongestionDecision:
    legs = [ProposedPlanLeg(robot_id=yielder, action="yield")]
    legs += [ProposedPlanLeg(robot_id=r, action="cross") for r in involved if r != yielder]
    return _echo_decision(involved, proposed_plan=legs, **extra)


def _scene(name: str):
    case = FIXTURES[name]
    config, params = _floor(case["floor"])
    return case, config, params, _frame(case["rows"])


def _verify(decision, frame, config, params, *, mode: str = "swap"):
    return verify_and_repair_plan(
        decision,
        frame,
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=mode,
        grounding_params=params,
    )


def _dispatch(decision, frame, config, params, *, mode: str = "swap") -> dict[str, Any]:
    return ground_reasoner_result(
        _reasoner_result(decision),
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=mode,
        snapshot=frame,
        params=params,
    )


def _yielder(legs) -> str | None:
    return next((leg.robot_id for leg in legs if leg.action == "yield"), None)


RETRIED = [
    ("s1b_sweep_regrounded_exec", "robot_2", "robot_4"),
    ("s1a_sweep_regrounded_exec", "robot_1", "robot_3"),
]
BOTH_FAIL = ["s1b_both_fail_sweep", "s1a_both_fail_sweep"]


@pytest.mark.parametrize(("name", "kept", "partner"), RETRIED)
def test_room_check_alone_accepts_the_sweep_failing_yielder(name: str, kept: str, partner: str):
    # The pre-A16(v) audit: no problem on the kept yielder's leg, hence the
    # reproduced `vlm_verbatim` while dispatch yielded the partner.
    case, config, params, frame = _scene(name)
    view = resolve_grounding_view(
        _echo_decision(case["involved"]), frame, config.scenario_geometry, params
    )
    legs = [*_plan(case["involved"], kept).proposed_plan]
    legs += [
        ProposedPlanLeg(robot_id=r.robot_id, action="continue")
        for r in frame.robots
        if r.robot_id not in case["involved"]
    ]
    problems = _plan_problems(
        legs, view.decision, frame, view.geometry, config.static_obstacles, "swap", params
    )
    assert problems == []


@pytest.mark.parametrize(("name", "kept", "partner"), RETRIED)
def test_plan_naming_the_sweep_failing_yielder_is_repaired_by_one_swap(
    name: str, kept: str, partner: str
):
    case, config, params, frame = _scene(name)
    verified = _verify(_plan(case["involved"], kept), frame, config, params)
    assert verified.provenance == "repaired"
    assert [(e.op, e.robot_ids) for e in verified.edits] == [
        ("swap", tuple(sorted((kept, partner))))
    ]
    assert verified.edits[0].reason == (
        f"yield re-grounded: {kept} has no retreat candidate surviving the sweep; {partner} "
        f"has an executable retreat; swapped roles {kept} (yield) <-> {partner} (cross)"
    )
    assert _yielder(verified.legs) == partner


@pytest.mark.parametrize(("name", "kept", "partner"), RETRIED)
def test_repaired_plan_matches_the_derived_dispatch(name: str, kept: str, partner: str):
    case, config, params, frame = _scene(name)
    verified = _verify(_plan(case["involved"], kept), frame, config, params)
    command = _dispatch(_echo_decision(case["involved"]), frame, config, params)
    assert f"yield_robot=sweep_regrounded:{kept}->{partner}" in command["degradations"]
    assert plan_matches_dispatch(verified.legs, command, [r.robot_id for r in frame.robots])
    plan_absent = _verify(_echo_decision(case["involved"]), frame, config, params)
    assert _yielder(plan_absent.legs) == _yielder(verified.legs) == partner


@pytest.mark.parametrize("name", BOTH_FAIL)
def test_both_retreats_failing_defaults_the_plan_to_the_refusal(name: str):
    # Both verified `vlm_verbatim` before, against a dispatched refusal.
    case, config, params, frame = _scene(name)
    verified = _verify(_plan(case["involved"], case["involved"][0]), frame, config, params)
    command = _dispatch(_echo_decision(case["involved"]), frame, config, params)
    assert verified.provenance == "m3_default"
    assert verified.rejection_stage == "repair_bound_exceeded"
    assert verified.rejection_reason.startswith(
        "plan unrepairable: yield refused: no executable retreat ("
    )
    assert {leg.action for leg in verified.legs if leg.robot_id in case["involved"]} == {"wait"}
    assert plan_matches_dispatch(verified.legs, command, [r.robot_id for r in frame.robots])


def test_partner_facing_away_is_never_repaired_onto():
    # Retry eligibility: robot_2 would back up off its retreat axis, so the
    # derived path refuses; the verifier must not swap the yield onto it.
    poses = {"robot_1": (-1.35, -0.95, 0.0), "robot_2": (-0.95, -0.95, 0.0)}
    frame = SnapshotFrame(
        stamp=1.0,
        robots=[RobotStateInput(robot_id=r, x=x, y=y, theta=t) for r, (x, y, t) in poses.items()],
    )
    config, params = _floor("s1b")
    verified = _verify(_plan(["robot_1", "robot_2"], "robot_1"), frame, config, params)
    assert verified.provenance == "m3_default"
    assert verified.rejection_reason.endswith("robot_2 would back up off its retreat axis)")


def test_node_handoff_occupant_is_never_repaired_onto():
    # robot_3 sits in robot_1's backup corridor; the partner robot_5 holds E
    # (the node-handoff occupant), so the derived path refuses the yield.
    geometry, obstacles, params = _shipped()
    frame = _retreat_frame({**_EP1_SCENE, "robot_3": (0.3, 0.05, 0.0)}, _EP1_GOALS)
    decision = _retreat_decision(_FIVE, "robot_1").model_copy(
        update={
            "proposed_plan": [
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_5", action="cross"),
                ProposedPlanLeg(robot_id="robot_3", action="cross"),
                ProposedPlanLeg(robot_id="robot_2", action="wait"),
                ProposedPlanLeg(robot_id="robot_4", action="wait"),
            ]
        }
    )
    verified = verify_and_repair_plan(
        decision,
        frame,
        geometry=geometry,
        static_obstacles=obstacles,
        yield_feasibility_mode="swap",
        grounding_params=params,
    )
    assert verified.provenance == "m3_default"
    assert verified.rejection_reason.endswith(
        "robot_5 is the node-handoff occupant, which never yields)"
    )
    assert _yielder(verified.legs) is None


def _unchanged(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> tuple[Any, Any]:
    case, config, params, frame = _scene("s1b_sweep_regrounded_exec")
    params = params.model_copy(update=kwargs.pop("params_update", {}))
    decision = _plan(case["involved"], "robot_2")
    post = _verify(decision, frame, config, params, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(command_grounder, "_plan_yield_verdict", lambda *a, **k: None)
        pre = _verify(decision, frame, config, params, **kwargs)
    return pre, post


def test_refuse_mode_plan_outcome_is_unchanged(monkeypatch: pytest.MonkeyPatch):
    # Outside the retry's domain the room check stands alone, as before.
    pre, post = _unchanged(monkeypatch, mode="refuse")
    assert post == pre
    assert post.provenance == "vlm_verbatim"


def test_declared_geometry_plan_outcome_is_unchanged(monkeypatch: pytest.MonkeyPatch):
    pre, post = _unchanged(monkeypatch, params_update={"dynamic_scene_arms": False})
    assert post == pre
    assert post.rejection_reason == "repair distance exceeds bound 4"


def _outcome(name: str) -> tuple[str, bool]:
    case, config, params, frame = _scene(name)
    decision = _plan(case["involved"], case["involved"][0])
    verified = _verify(decision, frame, config, params)
    command = _dispatch(_echo_decision(case["involved"]), frame, config, params)
    return verified.provenance, plan_matches_dispatch(
        verified.legs, command, [r.robot_id for r in frame.robots]
    )


def test_provenance_shift_runs_only_toward_dispatch(monkeypatch: pytest.MonkeyPatch):
    # Every replay fixture, scripted plan = the echo decision's own yield.
    # Pre-fix is reproduced by disabling the verdict (the fix's only input
    # to the verifier). A case may only move vb -> repaired (retry
    # succeeds) or vb -> m3_default (retry refuses), and every moved case
    # must flip dispatch_matches_plan False -> True.
    names = sorted(FIXTURES)
    post = {name: _outcome(name) for name in names}
    monkeypatch.setattr(command_grounder, "_plan_yield_verdict", lambda *a, **k: None)
    pre = {name: _outcome(name) for name in names}
    retried = {name for name, *_ in RETRIED}
    moved = {name for name in names if pre[name] != post[name]}
    assert moved == retried | set(BOTH_FAIL)
    for name in moved:
        assert pre[name] == ("vlm_verbatim", False)
        assert post[name] == ("repaired" if name in retried else "m3_default", True)
    assert Counter(p for p, _ in pre.values()) == Counter({"vlm_verbatim": 6, "m3_default": 4})
    assert Counter(p for p, _ in post.values()) == Counter(
        {"m3_default": 6, "vlm_verbatim": 2, "repaired": 2}
    )
    # Untouched here: the A16 heading handover (`heading_regrounded`) is a
    # grounding-view re-grounding, not the retry, and still verifies vb
    # against a dispatch that yields the facing partner.
    assert post["s1b_heading_regrounded_exec"] == ("vlm_verbatim", False)

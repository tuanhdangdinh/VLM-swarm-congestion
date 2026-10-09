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

A17 extends the verdict to the full derived pipeline's final yielder: a
grounding-view handover (`heading_regrounded`, and likewise
`rear_regrounded` / `node_handoff_regrounded`) moves the yield before the
retry runs, and a plan naming the model's yielder is repaired onto the robot
dispatch yields.
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
from reasoning.rag.plan_metrics import score_decision_artifact, score_plan_decision
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


@pytest.mark.parametrize(
    ("name", "yielder"),
    [("s1b_both_fail_sweep", "robot_2"), ("s1b_ambiguous_refused", "robot_2"),
     ("s1b_sweep_regrounded_exec", "robot_2")],
)
def test_rejection_stage_round_trips_through_the_stored_plan_block(name: str, yielder: str):
    # `plan unrepairable: ...` (retry or view refusal) re-scores offline as
    # the stage the verifier recorded live, not as `inconsistent`.
    case, config, params, frame = _scene(name)
    decision = _plan(case["involved"], yielder)
    verified = _verify(decision, frame, config, params)
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
    assert score_decision_artifact(artifact) == score_plan_decision(
        decision, verified, dispatch_matches_plan=True
    )


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
    # A17: the A16 heading handover (`heading_regrounded`, a grounding-view
    # re-grounding) now moves like the retry, because the verdict is the
    # full pipeline's final yielder. Until then it verified vb against a
    # dispatch that yields the facing partner.
    repaired = {name for name, *_ in RETRIED} | {HANDOVER[0]}
    moved = {name for name in names if pre[name] != post[name]}
    assert moved == repaired | set(BOTH_FAIL)
    for name in moved:
        assert pre[name] == ("vlm_verbatim", False)
        assert post[name] == ("repaired" if name in repaired else "m3_default", True)
    assert Counter(p for p, _ in pre.values()) == Counter({"vlm_verbatim": 6, "m3_default": 4})
    assert Counter(p for p, _ in post.values()) == Counter(
        {"m3_default": 6, "vlm_verbatim": 1, "repaired": 3}
    )


# The A16 heading handover (prereg-v3 A17): robot_3 heads 34 deg off both
# axes, so the grounding view hands the yield to robot_5, which faces it on
# the x lane (`grounding=heading_regrounded:robot_3->robot_5`), BEFORE
# `resolve_yield_roles` runs. The room check alone accepts robot_3's leg.
HANDOVER = ("s1b_heading_regrounded_exec", "robot_3", "robot_5")

# S1a MC seed 6's first conflict: the view hands robot_2's yield to robot_4
# (heading handover), then the partner retry finds no surviving retreat for
# robot_4 and its partner is robot_2 again, which would back up along its
# diagonal heading: the retry refuses. Composed handover-then-retry-SUCCESS
# is not constructible, because the retry's partner after a handover is
# always the robot handed over from, the one the view found ambiguous
# (0 of 800 MC first conflicts carry both tags).
_S1A_SEED6_ROWS = [
    {"robot_id": "robot_1", "x": 0.10837736411265103, "y": -1.319109093846961,
     "theta": -2.0096556257584033, "status": "MOVING", "goal": [0.0, -1.55]},
    {"robot_id": "robot_2", "x": -0.5770229710551237, "y": 0.5229770289448766,
     "theta": 0.7853981633974454, "status": "STOPPED", "goal": [0.0, 1.55]},
    {"robot_id": "robot_3", "x": -1.035899295539018, "y": -0.27261676488376696,
     "theta": 2.6839329969729007, "status": "MOVING", "goal": [-2.3, 0.35]},
    {"robot_id": "robot_4", "x": -0.3357514434695814, "y": 0.8961682416644989,
     "theta": -2.0451962095868037, "status": "STOPPED", "goal": [-2.3, 0.35]},
    {"robot_id": "robot_5", "x": -1.8424845928333025, "y": 0.12465659049998495,
     "theta": -0.45765965661689273, "status": "MOVING", "goal": [0.0, -1.55]},
]


def _regrounding_pairs(command: dict[str, Any]) -> list[tuple[str, str]]:
    # Every `<layer>_regrounded:<from>-><to>` tag of the dispatched command,
    # from the grounding view (heading, rear, node handoff) or the retry.
    pairs = []
    for tag in command.get("degradations", []):
        head, sep, ids = tag.rpartition(":")
        if sep and head.endswith("_regrounded") and "->" in ids:
            source, _, target = ids.partition("->")
            pairs.append(tuple(sorted((source, target))))
    return pairs


def test_room_check_alone_accepts_the_handed_over_yielder():
    # The pre-A17 audit: the verdict fired only on the retry's own tag, so
    # nothing flagged the leg of the robot the view handed the yield away
    # from, hence `vlm_verbatim` while dispatch yielded the facing partner.
    name, named, _ = HANDOVER
    case, config, params, frame = _scene(name)
    view = resolve_grounding_view(
        _echo_decision(case["involved"]), frame, config.scenario_geometry, params
    )
    legs = [*_plan(case["involved"], named).proposed_plan]
    legs += [
        ProposedPlanLeg(robot_id=r.robot_id, action="continue")
        for r in frame.robots
        if r.robot_id not in case["involved"]
    ]
    problems = _plan_problems(
        legs, view.decision, frame, view.geometry, config.static_obstacles, "swap", params
    )
    assert problems == []


def test_plan_naming_the_handed_over_yielder_is_repaired_by_one_swap():
    name, named, partner = HANDOVER
    case, config, params, frame = _scene(name)
    verified = _verify(_plan(case["involved"], named), frame, config, params)
    assert verified.provenance == "repaired"
    assert [(e.op, e.robot_ids) for e in verified.edits] == [
        ("swap", tuple(sorted((named, partner))))
    ]
    assert verified.edits[0].reason == (
        f"yield re-grounded: dispatch yields {partner}, not {named} "
        f"(grounding=heading_regrounded:{named}->{partner}); swapped roles {named} "
        f"(yield) <-> {partner} (cross)"
    )
    assert _yielder(verified.legs) == partner


def test_handed_over_plan_matches_the_derived_dispatch():
    name, named, partner = HANDOVER
    case, config, params, frame = _scene(name)
    verified = _verify(_plan(case["involved"], named), frame, config, params)
    command = _dispatch(_echo_decision(case["involved"]), frame, config, params)
    assert f"grounding=heading_regrounded:{named}->{partner}" in command["degradations"]
    assert plan_matches_dispatch(verified.legs, command, [r.robot_id for r in frame.robots])


@pytest.mark.parametrize(
    "name", [HANDOVER[0], *(name for name, *_ in RETRIED)]
)
def test_repair_swap_ids_equal_the_command_regrounding_pair(name: str):
    # Stratum separability: the plan's single edit is a swap whose ids are
    # exactly one `*_regrounded:<from>-><to>` pair of the dispatched command,
    # whichever layer (grounding view or partner retry) re-grounded it.
    case, config, params, frame = _scene(name)
    verified = _verify(_plan(case["involved"], case["involved"][0]), frame, config, params)
    command = _dispatch(_echo_decision(case["involved"]), frame, config, params)
    assert [edit.op for edit in verified.edits] == ["swap"]
    assert _regrounding_pairs(command) == [verified.edits[0].robot_ids]


def test_handover_then_retry_refusal_defaults_the_plan_to_the_refusal():
    config, params = _floor("s1a")
    frame = _frame(_S1A_SEED6_ROWS)
    involved = ["robot_2", "robot_4"]
    command = _dispatch(_echo_decision(involved), frame, config, params)
    assert "grounding=heading_regrounded:robot_2->robot_4" in command["degradations"]
    verified = _verify(_plan(involved, "robot_2"), frame, config, params)
    assert verified.provenance == "m3_default"
    assert verified.rejection_stage == "repair_bound_exceeded"
    assert verified.rejection_reason == (
        "plan unrepairable: yield refused: no executable retreat (robot_4 has no retreat "
        "candidate surviving the sweep; robot_2 would back up off its retreat axis)"
    )
    assert {leg.action for leg in verified.legs if leg.robot_id in involved} == {"wait"}
    assert plan_matches_dispatch(verified.legs, command, [r.robot_id for r in frame.robots])


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_verified_yielder_is_the_plan_absent_default_yielder(name: str):
    # The verdict is read from the call chain the default plan is derived
    # by, so on these fixtures a plan that survives verification yields the
    # robot the plan-absent default (M3's own derived plan) yields. Not an
    # MC-wide invariant: non-retry refusals stay verdict-free, and the
    # default plan's multi-passer refusal can disagree with derived dispatch
    # (6/400 S1b, 7/400 S1a first conflicts, pre-existing).
    case, config, params, frame = _scene(name)
    verified = _verify(_plan(case["involved"], case["involved"][0]), frame, config, params)
    default = _verify(_echo_decision(case["involved"]), frame, config, params)
    assert _yielder(verified.legs) == _yielder(default.legs)


# The verdict is an identity test on the final yielder, so every grounding
# view re-grounding is covered, not only the heading handover. S1a MC seed
# 211: robot_2 faces away from robot_3 on the x lane (`rear_regrounded`).
# S1b MC seed 316: robot_5 arrives at node N, which robot_2 occupies, so the
# arriver yields (`node_handoff_regrounded`). Both verified vb against a
# dispatch yielding the other robot before A17.
_VIEW_REGROUNDINGS = {
    "rear_regrounded": ("s1a", ["robot_2", "robot_3", "robot_4"], "robot_2", "robot_3", [
        {"robot_id": "robot_1", "x": -0.08182010817817348, "y": -1.3906661051267148,
         "theta": -1.0963964440029896, "status": "MOVING", "goal": [0.0, -1.55]},
        {"robot_id": "robot_2", "x": 1.137095111518571, "y": 0.12921165427571424,
         "theta": -0.11065722117389558, "status": "STOPPED", "goal": [2.3, 0.0]},
        {"robot_id": "robot_3", "x": 0.809113479076279, "y": -0.16565405788041335,
         "theta": 0.11065722117389558, "status": "STOPPED", "goal": [2.3, 0.0]},
        {"robot_id": "robot_4", "x": 1.5247706869545765, "y": -0.08613659033838032,
         "theta": -3.0309354324158977, "status": "STOPPED", "goal": [0.0, -1.55]},
        {"robot_id": "robot_5", "x": -1.7465995680707873, "y": -0.30789344539669034,
         "theta": 0.07594063626589467, "status": "MOVING", "goal": [2.3, 0.0]},
    ]),
    "node_handoff_regrounded": ("s1b", ["robot_2", "robot_5"], "robot_2", "robot_5", [
        {"robot_id": "robot_1", "x": -0.86553504844774, "y": 1.1064116120005596,
         "theta": -0.16820677185708616, "status": "MOVING", "goal": [2.3, 0.0]},
        {"robot_id": "robot_2", "x": -0.1830510568382873, "y": 1.316194098007452,
         "theta": -0.46760015758755624, "status": "STOPPED", "goal": [2.3, 0.0]},
        {"robot_id": "robot_3", "x": -0.30315263929117253, "y": -1.3227754774362288,
         "theta": -0.4733560418349155, "status": "MOVING", "goal": [-0.25, -1.35]},
        {"robot_id": "robot_4", "x": 0.8183587736462421, "y": -1.02741116134694,
         "theta": 0.10308160852270035, "status": "MOVING", "goal": [2.3, 0.0]},
        {"robot_id": "robot_5", "x": 0.19545190186115036, "y": 1.1218417088028256,
         "theta": 2.6682366117548786, "status": "STOPPED", "goal": [-0.25, 1.35]},
    ]),
}


@pytest.mark.parametrize("layer", sorted(_VIEW_REGROUNDINGS))
def test_any_view_regrounding_is_repaired_onto_the_dispatched_yielder(layer: str):
    floor, involved, named, final, rows = _VIEW_REGROUNDINGS[layer]
    config, params = _floor(floor)
    frame = _frame(rows)
    command = _dispatch(_echo_decision(involved), frame, config, params)
    assert f"grounding={layer}:{named}->{final}" in command["degradations"]
    verified = _verify(_plan(involved, named), frame, config, params)
    assert verified.provenance == "repaired"
    assert [(e.op, e.robot_ids) for e in verified.edits] == [
        ("swap", tuple(sorted((named, final))))
    ]
    assert _regrounding_pairs(command) == [verified.edits[0].robot_ids]
    assert plan_matches_dispatch(verified.legs, command, [r.robot_id for r in frame.robots])

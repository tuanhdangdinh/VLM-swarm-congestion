"""prereg-v3 A29 item (i): every reader of the retreat selection sees the filtered one.

A28(ii) (owner ruling 2026-10-16) drops, before stage 2, every retreat
candidate whose escort leg passes within `min_distance_m` of its park point
(`GroundingParams.escort_park_clearance`). Dispatch and stage 2 applied the
filter; three readers still consumed the unfiltered selection, so with the
switch on they could disagree with what is dispatched: Arm B's shadow
retreat (`shadow_classical.classical_retreat_answer`), the plan verifier's
yield->reroute model (`_derived_reroute_reason`) and the A15(iv) partner
swap (`_sweep_regrounded_roles`). All of them now read
`prepare_filtered_retreat_selection`, the one shared path.

Two rules are deliberately asymmetric (see the 2026-10-17 entry in
`docs/implementation_notes.md`): the gate-kept yielder whose candidates are
all filtered still reroutes (A29's recorded outcome, E20 `f269ab37`), while
a SWAPPED-IN partner with no surviving candidate counts as "no executable
retreat" for that role, as a partner with no sweep survivor already does.

Fixtures: the A28 live yields (`data/a28_escort_park/yields.json`) and the
S1 resolvability partner-retry scenes (`data/s1_resolvability`). The
switch-off goldens (`data/a29_filter_parity/golden_off.json`) were written
from `feat/v3-integration` @ 6ce2b92, before this change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from swarm_orchestrator.shadow_classical import ClassicalRetreatContext, classical_retreat_answer

from reasoning.rag.command_grounder import (
    ground_reasoner_result,
    plan_matches_dispatch,
    prepare_filtered_retreat_selection,
    project_dispatched_legs,
    resolve_yield_roles,
    verify_and_repair_plan,
)
from reasoning.rag.grounding_view import resolve_grounding_view
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.vlm.models import CongestionDecision, ProposedPlanLeg, SnapshotFrame
from tests.unit.test_a28_escort_park import CASES, _goals, _ground, _params, _stage2, _yield
from tests.unit.test_s1_resolvability import (
    FIXTURES,
    _echo_decision,
    _floor,
    _frame,
    _reasoner_result,
)

GOLDEN_OFF = Path(__file__).parent / "data/a29_filter_parity/golden_off.json"
# The S1 partner-retry scenes (`test_plan_yield_retry_parity`): kept yielder
# with no sweep survivor, partner retried; and both failing.
RETRIED = {"s1b_sweep_regrounded_exec": "robot_2", "s1a_sweep_regrounded_exec": "robot_1"}
BOTH_FAIL = {"s1b_both_fail_sweep": "robot_2", "s1a_both_fail_sweep": "robot_1"}
_E20_OLD_B = (2.156, -0.708)


def _decision(case: dict[str, Any], *, plan: bool = True) -> CongestionDecision:
    decision = CongestionDecision.model_validate(case["decision"])
    return decision if plan else decision.model_copy(update={"proposed_plan": None})


def _view(case: dict[str, Any], params: GroundingParams):
    config, _ = _floor("s1b")
    return resolve_grounding_view(
        _decision(case), _frame(case["rows"]), config.scenario_geometry, params, _goals(case)
    )


def _verify(case: dict[str, Any], params: GroundingParams, *, plan: bool = True):
    # As `InProcessPipeline` verifies: the model's decision, declared
    # geometry, the grounder's goal references.
    config, _ = _floor("s1b")
    return verify_and_repair_plan(
        _decision(case, plan=plan),
        _frame(case["rows"]),
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        grounding_params=params,
        goal_references=_goals(case),
    )


def _context(params: GroundingParams, geometry) -> ClassicalRetreatContext:
    config, _ = _floor("s1b")
    return ClassicalRetreatContext(
        params=params,
        geometry=geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
    )


def _ids(frame: SnapshotFrame) -> list[str]:
    return [robot.robot_id for robot in frame.robots]


def _observe_a28(case: dict[str, Any], params: GroundingParams) -> dict[str, Any]:
    # Every reader's output for one live yield, JSON-safe.
    config, _ = _floor("s1b")
    frame = _frame(case["rows"])
    view = _view(case, params)
    live = _ground(case, params)
    choice, record = _stage2(case, params)
    out: dict[str, Any] = {
        "dispatch_live": live,
        "dispatch_default": _ground(case, params, choice=None),
        "stage2_choice": None if choice is None else choice.model_dump(mode="json"),
        "stage2": record.model_dump(mode="json"),
        "shadow_declared": classical_retreat_answer(
            _decision(case), frame, _context(params, config.scenario_geometry)
        ).model_dump(mode="json"),
        "shadow_view": classical_retreat_answer(
            view.decision, frame, _context(params, view.geometry)
        ).model_dump(mode="json"),
    }
    for key, plan in (("plan", True), ("absent", False)):
        verified = _verify(case, params, plan=plan)
        out[f"verify_{key}"] = verified.model_dump(mode="json")
        out[f"matches_{key}"] = plan_matches_dispatch(verified.legs, live, _ids(frame))
    return out


def _s1_scene(name: str):
    case = FIXTURES[name]
    config, params = _floor(case["floor"])
    return case, config, params, _frame(case["rows"])


def _plan_naming(involved: list[str], yielder: str) -> CongestionDecision:
    legs = [ProposedPlanLeg(robot_id=yielder, action="yield")]
    legs += [ProposedPlanLeg(robot_id=r, action="cross") for r in involved if r != yielder]
    return _echo_decision(involved, proposed_plan=legs)


def _s1_dispatch(name: str, params: GroundingParams) -> dict[str, Any]:
    case, config, _, frame = _s1_scene(name)
    return ground_reasoner_result(
        _reasoner_result(_echo_decision(case["involved"])),
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        snapshot=frame,
        params=params,
    )


def _s1_verify(name: str, params: GroundingParams, decision: CongestionDecision):
    _, config, _, frame = _s1_scene(name)
    return verify_and_repair_plan(
        decision,
        frame,
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        grounding_params=params,
    )


def _observe_s1(name: str, params: GroundingParams, kept: str) -> dict[str, Any]:
    case, _, _, frame = _s1_scene(name)
    dispatch = _s1_dispatch(name, params)
    out: dict[str, Any] = {"dispatch": dispatch}
    for key, decision in (
        ("plan", _plan_naming(case["involved"], kept)),
        ("absent", _echo_decision(case["involved"])),
    ):
        verified = _s1_verify(name, params, decision)
        out[f"verify_{key}"] = verified.model_dump(mode="json")
        out[f"matches_{key}"] = plan_matches_dispatch(verified.legs, dispatch, _ids(frame))
    return out


def observe_all_off() -> dict[str, Any]:
    """Every reader's switch-off output over both fixture families (the golden)."""
    observed: dict[str, Any] = {
        name: _observe_a28(case, _params()) for name, case in sorted(CASES.items())
    }
    for name, kept in sorted({**RETRIED, **BOTH_FAIL}.items()):
        _, _, params, _ = _s1_scene(name)
        observed[name] = _observe_s1(name, params, kept)
    return json.loads(json.dumps(observed))


# ---- (c) switch off: byte-identical to 6ce2b92 ----


@pytest.fixture(scope="module")
def observed_off() -> dict[str, Any]:
    return observe_all_off()


@pytest.fixture(scope="module")
def golden_off() -> dict[str, Any]:
    return json.loads(GOLDEN_OFF.read_text(encoding="utf-8"))


def test_golden_covers_every_fixture(golden_off):
    assert set(golden_off) == {*CASES, *RETRIED, *BOTH_FAIL}


@pytest.mark.parametrize("name", sorted({*CASES, *RETRIED, *BOTH_FAIL}))
def test_every_reader_is_unchanged_when_park_clearance_off(name, observed_off, golden_off):
    assert observed_off[name] == golden_off[name]


# ---- (a) switch on: one filtered selection behind every reader ----


def _filtered_selection(case: dict[str, Any], params: GroundingParams):
    config, _ = _floor("s1b")
    frame = _frame(case["rows"])
    view = _view(case, params)
    roles = resolve_yield_roles(
        view.decision,
        frame,
        geometry=view.geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        params=params,
        goal_references=_goals(case),
    )
    return roles, prepare_filtered_retreat_selection(
        frame,
        roles.yielder_id,
        roles.crossing_order,
        params,
        geometry=view.geometry,
        static_obstacles=config.static_obstacles,
        goal_references=_goals(case),
    )


def _pose(candidate) -> tuple[float, float]:
    return (round(candidate.x, 3), round(candidate.y, 3))


@pytest.mark.parametrize("name", sorted(CASES))
def test_stage2_offers_exactly_the_filtered_selection(name):
    case = CASES[name]
    params = _params(escort_park_clearance=True)
    _, selection = _filtered_selection(case, params)
    _, record = _stage2(case, params)
    assert [c["label"] for c in record.candidates] == [c.label for c in selection.candidates]
    # An answered record also carries each candidate's shown `letter`.
    offered = [{k: v for k, v in c.items() if k != "letter"} for c in record.candidates]
    assert offered == [c.model_dump(mode="json") for c in selection.candidates]


@pytest.mark.parametrize("name", sorted(CASES))
def test_dispatch_default_grounds_the_filtered_rank_zero(name):
    case = CASES[name]
    params = _params(escort_park_clearance=True)
    _, selection = _filtered_selection(case, params)
    command = _ground(case, params, choice=None)
    tags = [t for t in command["degradations"] if t.startswith("retreat=escort_park_filtered:")]
    assert tags == [f"retreat=escort_park_filtered:{e}" for e in selection.escort_park_filtered]
    if not selection.candidates:
        assert _yield(command) is None
        return
    parameters = _yield(command)["parameters"]
    assert parameters["retreat_choice"] == selection.candidates[0].label
    assert (parameters["retreat_x_m"], parameters["retreat_y_m"]) == _pose(selection.candidates[0])


@pytest.mark.parametrize("name", sorted(CASES))
def test_shadow_default_is_the_filtered_rank_zero(name):
    case = CASES[name]
    params = _params(escort_park_clearance=True)
    view = _view(case, params)
    roles, selection = _filtered_selection(case, params)
    retreat = classical_retreat_answer(
        view.decision, _frame(case["rows"]), _context(params, view.geometry), _goals(case)
    )
    assert retreat.yielder_id == roles.yielder_id
    if not selection.candidates:
        assert retreat.status == "unavailable"
        assert retreat.reason.startswith("no candidate clears its park point: escort_hits_park:")
        return
    best = selection.candidates[0]
    assert retreat.status == "computed"
    assert retreat.candidate_count == len(selection.candidates)
    assert (retreat.candidate_label, retreat.x, retreat.y) == (best.label, best.x, best.y)


def test_e20_shadow_default_is_old_b_not_the_filtered_a():
    case = CASES["E20_6cf402ed"]
    params = _params(escort_park_clearance=True)
    view = _view(case, params)
    retreat = classical_retreat_answer(
        view.decision, _frame(case["rows"]), _context(params, view.geometry), _goals(case)
    )
    assert retreat.candidate_label == "A"
    assert (round(retreat.x, 3), round(retreat.y, 3)) == _E20_OLD_B
    assert retreat.candidate_count == 2


@pytest.mark.parametrize("name", sorted(CASES))
def test_verifier_default_plan_matches_the_filtered_dispatch(name):
    # Plan absent: M3's own default plan is the certification of what
    # dispatch does with the model's decision and no stage-2 choice.
    case = CASES[name]
    params = _params(escort_park_clearance=True)
    frame = _frame(case["rows"])
    verified = _verify(case, params, plan=False)
    command = _ground(case, params, choice=None)
    _, selection = _filtered_selection(case, params)
    yielder = next(leg for leg in verified.legs if leg.robot_id == selection.yielder_id)
    assert yielder.action == ("yield" if selection.candidates else "reroute")
    # A28's live commands carry A26 shield holds, which the verifier does
    # not model (`plan_metrics.shield_excluded_dispatch_match`).
    shield = "grounding=retreat_shield:"
    shielded = {t.removeprefix(shield) for t in command["degradations"] if t.startswith(shield)}
    dispatched = project_dispatched_legs(command, _ids(frame))
    assert {k: v for k, v in dispatched.items() if k not in shielded} == {
        leg.robot_id: leg.action for leg in verified.legs if leg.robot_id not in shielded
    }


@pytest.mark.parametrize("name", ["E20_6cf402ed", "E21_04457772", "E23_9803bd34"])
def test_verdict_on_a_surviving_yield_is_the_switch_off_verdict(name, golden_off):
    # A filter that leaves a survivor changes no role: the live plan's verdict
    # and its dispatch match are the switch-off ones.
    case = CASES[name]
    params = _params(escort_park_clearance=True)
    verified = _verify(case, params)
    assert verified.model_dump(mode="json") == golden_off[name]["verify_plan"]


# ---- (b) E20 f269ab37: no survivor, certified yield->reroute ----


def test_f269ab37_live_plan_is_certified_as_the_escort_hits_park_reroute():
    case = CASES["E20_f269ab37"]
    params = _params(escort_park_clearance=True)
    frame = _frame(case["rows"])
    verified = _verify(case, params)
    command = _ground(case, params)
    assert [a["action"] for a in command["actions"]][0] == "reroute"
    assert verified.provenance == "m3_default"
    assert verified.rejection_reason.startswith("plan unrepairable: ")
    assert "escort_hits_park:robot_2:0.447" in verified.rejection_reason
    assert plan_matches_dispatch(verified.legs, command, _ids(frame))


def test_f269ab37_default_plan_reroutes_the_yielder():
    case = CASES["E20_f269ab37"]
    params = _params(escort_park_clearance=True)
    frame = _frame(case["rows"])
    verified = _verify(case, params, plan=False)
    assert {leg.robot_id: leg.action for leg in verified.legs}["robot_4"] == "reroute"
    assert plan_matches_dispatch(verified.legs, _ground(case, params), _ids(frame))


def test_f269ab37_was_uncertified_before_the_veto(golden_off):
    # The switch-off golden carries the live yield, which dispatch executes;
    # the escort veto is what turns it into the certified reroute above.
    assert golden_off["E20_f269ab37"]["verify_plan"]["provenance"] == "vlm_verbatim"


# ---- (d) the A15(iv) partner swap ----


@pytest.mark.parametrize(("name", "kept"), sorted(RETRIED.items()))
def test_swapped_partner_without_a_surviving_candidate_refuses_the_yield(name, kept):
    # Switch off: the kept yielder fails the sweep, the partner yields. Switch
    # on: the partner's only candidate passes its park point, so the partner
    # has no executable retreat either; the yield is refused (wait fan-out),
    # as when the partner's own sweep finds nothing.
    case, _, params, frame = _s1_scene(name)
    on = params.model_copy(update={"escort_park_clearance": True})
    command = _s1_dispatch(name, on)
    assert {a["action"] for a in command["actions"]} == {"temporary_wait"}
    (refusal,) = [t for t in command["degradations"] if t.startswith("yield=infeasible:")]
    assert refusal.startswith(
        f"yield=infeasible:yield refused: no executable retreat ({kept} has no retreat "
        "candidate surviving the sweep; "
    )
    assert "has no retreat candidate clearing its park point (escort_hits_park:" in refusal


@pytest.mark.parametrize(("name", "kept"), sorted(RETRIED.items()))
def test_swap_refusal_is_certified_by_the_verifier(name, kept):
    case, _, params, frame = _s1_scene(name)
    on = params.model_copy(update={"escort_park_clearance": True})
    command = _s1_dispatch(name, on)
    for decision in (_plan_naming(case["involved"], kept), _echo_decision(case["involved"])):
        verified = _s1_verify(name, on, decision)
        assert plan_matches_dispatch(verified.legs, command, _ids(frame))


@pytest.mark.parametrize(("name", "kept"), sorted(RETRIED.items()))
def test_swap_still_fires_when_park_clearance_off(name, kept, golden_off):
    assert any(
        t.startswith(f"yield_robot=sweep_regrounded:{kept}->")
        for t in golden_off[name]["dispatch"]["degradations"]
    )


def test_kept_yielder_with_no_survivor_reroutes_instead_of_retrying_the_partner():
    # A29's recorded outcome is kept: the kept yielder's escort veto is not a
    # swap trigger (the partner robot_2 would fail its sweep, refusing it).
    case = CASES["E20_f269ab37"]
    command = _ground(case, _params(escort_park_clearance=True))
    assert not any("sweep_regrounded" in t for t in command["degradations"])
    assert command["actions"][0] == {**command["actions"][0], "robot_id": "robot_4"}
    assert command["actions"][0]["action"] == "reroute"


# ---- goal references reach the filter from every reader ----


def test_every_reader_hands_the_filter_the_grounder_goal_references(monkeypatch):
    # The fixtures' snapshot goals equal their registry goals, so a reader
    # dropping `goal_references` (None: snapshot goals) would pass every test
    # above; spy on the filter instead.
    from reasoning.rag import command_grounder

    case = CASES["E20_6cf402ed"]
    params = _params(escort_park_clearance=True)
    goals = _goals(case)
    seen: list[Any] = []
    real = command_grounder.filter_escort_park_candidates

    def spy(*args: Any, **kwargs: Any):
        seen.append(kwargs.get("goal_references"))
        return real(*args, **kwargs)

    monkeypatch.setattr(command_grounder, "filter_escort_park_candidates", spy)
    view = _view(case, params)
    readers = {
        "dispatch": lambda: _ground(case, params, choice=None),
        "stage2": lambda: _stage2(case, params),
        "verifier": lambda: _verify(case, params),
        "shadow": lambda: classical_retreat_answer(
            view.decision, _frame(case["rows"]), _context(params, view.geometry), goals
        ),
    }
    for name, read in readers.items():
        seen.clear()
        read()
        assert seen, name
        assert all(refs == goals for refs in seen), name

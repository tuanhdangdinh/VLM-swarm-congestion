"""Tests for the pure plan-versus-dispatch comparison (`plan_dispatch_mismatch`).

Recorded cases come from minimal copies of decision artifacts under
`tests/unit/data/plan_dispatch_mismatch/` (each names its source bundle in
`_fixture_source`; the bundles themselves are never touched). Synthetic cases
cover the kinds no recorded decision shows on its own.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from reasoning.rag.command_grounder import DEGRADATION_TAGS, degradation_cause
from reasoning.rag.plan_dispatch_mismatch import (
    OVERRIDE_TAG,
    classify_plan_dispatch,
    dispatched_provenance,
    leg_effects,
    reverse_dispatch,
)

DATA = Path(__file__).parent / "data" / "plan_dispatch_mismatch"


def _fixture(name: str) -> dict:
    return json.loads((DATA / name).read_text())


def _known(artifact: dict) -> list[str]:
    return [robot["robot_id"] for robot in artifact["scene"]["robots"]]


def _verified_legs(artifact: dict) -> list[dict]:
    # A non-held plan block's legs ARE the verified legs. On a hold they are
    # the active plan's: its non-done legs equal the verified ones (the hold
    # rule), and a verbatim decision's legs for the done robots are its own
    # proposed legs, `continue` when unnamed (scene-wide completion).
    plan = artifact["plan"]
    if not plan["plan_held"]:
        return plan["legs"]
    assert plan["provenance"] == "vlm_verbatim"
    proposed = {leg["robot_id"]: leg["action"] for leg in artifact["decision"]["proposed_plan"]}
    done = {leg["robot_id"] for leg in plan["legs"] if leg["status"] == "done"}
    legs = [leg for leg in plan["legs"] if leg["robot_id"] not in done]
    legs += [{"robot_id": r, "action": proposed.get(r, "continue")} for r in sorted(done)]
    return legs


def _classify(artifact: dict):
    withheld = artifact.get("dispatch_withheld")
    return classify_plan_dispatch(
        artifact["decision"]["strategy"],
        _verified_legs(artifact),
        artifact["dispatched_command"],
        _known(artifact),
        withheld_reason=None if withheld is None else withheld["reason"],
        dropped_robot_ids=artifact.get("dispatch_dropped_robot_ids") or (),
    )


def _items(result) -> dict[str, tuple[str, str, str]]:
    return {item.subject: (item.kind, item.planned, item.dispatched) for item in result.items}


def test_recorded_reverse_hold_95066420_flags_robot_5_unplanned_reverse():
    result = _classify(_fixture("m5V_95066420_reverse_hold.json"))

    assert result.matches is False
    assert _items(result) == {"robot_5": ("unplanned_motion", "continue", "reverse")}
    assert result.items[0].reason == "template:reverse_acts_on_involved_robots"
    assert result.tags() == [f"{OVERRIDE_TAG}:reverse:robot_5:continue->reverse"]


def test_recorded_reverse_hold_95066420_per_robot_equal_matches_the_recorded_flag():
    artifact = _fixture("m5V_95066420_reverse_hold.json")

    assert _classify(artifact).per_robot_equal is artifact["plan"]["dispatch_matches_plan"]


def test_recorded_reverse_handoff_b07a700f_names_the_dropped_and_the_extra_reversers():
    result = _classify(_fixture("m5V_b07a700f_reverse_handoff.json"))

    assert _items(result) == {
        "robot_4": ("planned_motion_not_sent", "reverse", "continue"),
        "robot_1": ("unplanned_motion", "wait", "reverse"),
        "robot_2": ("unplanned_motion", "wait", "reverse"),
    }
    reasons = {item.subject: item.reason for item in result.items}
    assert reasons["robot_4"] == "grounding=node_handoff:robot_1->robot_4"
    assert reasons["robot_2"] == "template:reverse_acts_on_involved_robots"


def test_recorded_reroute_df2ed72f_flags_the_rerouted_and_the_held_rerouters():
    result = _classify(_fixture("E16_df2ed72f_reroute.json"))

    assert _items(result) == {
        "robot_3": ("planned_motion_not_sent", "reroute", "wait"),
        "robot_4": ("planned_motion_not_sent", "reroute", "wait"),
        "robot_1": ("unplanned_motion", "wait", "reroute"),
    }
    reasons = {item.subject: item.reason for item in result.items}
    assert reasons["robot_1"] == "template:reroute_acts_on_first_involved_robot"
    assert reasons["robot_3"] == "template:reroute_waits_the_other_involved_robots"


def test_recorded_yield_with_retreat_shield_03bba450_is_an_excluded_artefact():
    artifact = _fixture("m5D_03bba450_yield_shield.json")
    result = _classify(artifact)

    assert artifact["plan"]["dispatch_matches_plan"] is False
    assert result.per_robot_equal is False
    assert result.matches is True
    assert {(e.subject, e.rule) for e in result.excluded} == {
        ("robot_3", "retreat_shield_bystander:A27(iv)"),
        ("robot_5", "retreat_shield_bystander:A27(iv)"),
    }


def test_recorded_yield_escort_satisfies_the_cross_leg():
    result = _classify(_fixture("m5D_03bba450_yield_shield.json"))

    assert result.dispatched["robot_4"] == "escort"
    assert result.dispatched["robot_1"] == "yield"


def test_recorded_convoy_yield_759bdb94_flags_the_planned_waits_never_sent():
    result = _classify(_fixture("cvD_759bdb94_yield_wait_unsent.json"))

    assert result.matches is False
    assert _items(result) == {
        "robot_3": ("hold_differs", "wait", "continue"),
        "robot_4": ("hold_differs", "wait", "continue"),
    }
    assert {item.reason for item in result.items} == {"unattributed"}


def test_withheld_decision_dispatches_nothing_and_names_the_reason():
    artifact = _fixture("m5D_03bba450_yield_shield.json")
    result = classify_plan_dispatch(
        "yield",
        artifact["plan"]["legs"],
        artifact["dispatched_command"],
        _known(artifact),
        withheld_reason="refusal_no_action",
    )

    assert set(result.dispatched.values()) == {"continue"}
    assert _items(result)["robot_1"] == ("planned_motion_not_sent", "yield", "continue")
    assert {item.reason for item in result.items if item.subject.startswith("robot")} == {
        "withheld:refusal_no_action"
    }
    assert result.excluded == ()


def _yield_command(yielder: str, passers: list[str], escort: float = 0.0) -> dict:
    params: dict = {"crossing_order": passers, "passer_robot_id": passers[0]}
    if escort:
        params["passer_escort_distance_m"] = escort
    return {
        "command_id": "c-yield",
        "actions": [
            {"robot_id": yielder, "action": "yield", "parameters": params},
            *(
                {"robot_id": r, "action": "temporary_wait", "parameters": {"linked_position": i}}
                for i, r in enumerate(passers)
            ),
        ],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }


def _legs(*pairs: tuple[str, str]) -> list[dict]:
    return [{"robot_id": r, "action": a} for r, a in pairs]


def test_registry_dropped_robot_reads_as_not_sent_with_reason():
    legs = _legs(("robot_1", "yield"), ("robot_2", "cross"))
    command = {**_yield_command("robot_1", ["robot_2"])}
    command["actions"] = command["actions"][:1]
    result = classify_plan_dispatch(
        "yield", legs, command, ["robot_1", "robot_2"], dropped_robot_ids=["robot_2"]
    )

    assert _items(result)["robot_2"] == ("hold_differs", "cross", "continue")
    assert result.items[0].reason == "registry_dropped"


def test_swapped_yielder_reports_yielder_differs():
    legs = _legs(("robot_2", "yield"), ("robot_1", "cross"))
    result = classify_plan_dispatch(
        "yield", legs, _yield_command("robot_1", ["robot_2"]), ["robot_1", "robot_2"]
    )

    assert _items(result) == {
        "robot_2": ("planned_motion_not_sent", "yield", "cross"),
        "robot_1": ("unplanned_motion", "cross", "yield"),
        "yielder": ("yielder_differs", "robot_2", "robot_1"),
        "passer": ("passer_differs", "robot_1", "robot_2"),
    }
    assert result.robots == ("robot_1", "robot_2")


def test_crossing_order_that_differs_from_the_plan_reports_order_differs():
    legs = _legs(("robot_1", "yield"), ("robot_2", "cross"), ("robot_3", "cross"))
    command = _yield_command("robot_1", ["robot_3", "robot_2"])
    result = classify_plan_dispatch("yield", legs, command, ["robot_1", "robot_2", "robot_3"])

    assert [(i.kind, i.planned, i.dispatched) for i in result.items] == [
        ("order_differs", "robot_2,robot_3", "robot_3,robot_2")
    ]


def test_reverse_given_where_the_plan_says_reroute_is_motion_differs():
    legs = _legs(("robot_1", "reroute"))
    command = {
        "command_id": "c",
        "actions": [{"robot_id": "robot_1", "action": "reverse", "parameters": {}}],
        "expected_resolution_time_sec": 8.0,
        "fallback": "stop",
    }

    result = classify_plan_dispatch("reverse", legs, command, ["robot_1"])

    assert _items(result) == {"robot_1": ("motion_differs", "reroute", "reverse")}


def test_escort_of_a_continue_leg_is_unplanned_motion():
    legs = _legs(("robot_1", "yield"), ("robot_2", "continue"))
    result = classify_plan_dispatch(
        "yield", legs, _yield_command("robot_1", ["robot_2"], escort=1.5), ["robot_1", "robot_2"]
    )

    assert _items(result)["robot_2"] == ("unplanned_motion", "continue", "escort")


def test_matching_dispatch_has_no_items_and_keeps_verbatim():
    legs = _legs(("robot_1", "yield"), ("robot_2", "cross"))
    result = classify_plan_dispatch(
        "yield", legs, _yield_command("robot_1", ["robot_2"]), ["robot_1", "robot_2"]
    )

    assert result.matches is True and result.per_robot_equal is True
    assert dispatched_provenance("vlm_verbatim", result) == "vlm_verbatim"


def test_dispatched_provenance_overridden_only_for_a_verbatim_plan():
    result = _classify(_fixture("m5V_95066420_reverse_hold.json"))

    assert dispatched_provenance("vlm_verbatim", result) == "overridden"
    assert dispatched_provenance("repaired", result) == "repaired"
    assert dispatched_provenance("m3_default", result) == "m3_default"


def _junction_phases(order: list[str], yielder: str) -> list[dict]:
    phases = [
        {
            "label": "recede",
            "robot_id": robot_id,
            "held_robot_ids": [r for r in order if r != robot_id],
            "command": {
                "command_id": f"c-recede-{robot_id}",
                "actions": [{"robot_id": robot_id, "action": "reverse", "parameters": {}}]
                + [
                    {"robot_id": r, "action": "temporary_wait", "parameters": {}}
                    for r in order
                    if r != robot_id
                ],
                "expected_resolution_time_sec": 8.0,
                "fallback": "stop",
            },
        }
        for robot_id in order
    ]
    phases.append(
        {
            "label": "cross",
            "robot_id": yielder,
            "held_robot_ids": list(order),
            "command": {
                "command_id": "c-cross",
                "actions": [{"robot_id": yielder, "action": "yield", "parameters": {}}]
                + [{"robot_id": r, "action": "temporary_wait", "parameters": {}} for r in order],
                "expected_resolution_time_sec": 8.0,
                "fallback": "stop",
            },
        }
    )
    return phases


def test_junction_recede_order_within_epsilon_is_excluded():
    legs = _legs(("robot_3", "reverse"), ("robot_4", "reverse"), ("robot_1", "yield"))
    phases = _junction_phases(["robot_4", "robot_3"], "robot_1")
    result = classify_plan_dispatch(
        "junction_clear",
        legs,
        phases[0]["command"],
        ["robot_1", "robot_3", "robot_4"],
        junction_phases=phases,
        order_equivalent=True,
    )

    assert result.matches is True
    assert [(e.subject, e.rule) for e in result.excluded] == [
        ("order", "junction_recede_order_epsilon")
    ]


def test_junction_recede_order_outside_epsilon_is_order_differs():
    legs = _legs(("robot_3", "reverse"), ("robot_4", "reverse"), ("robot_1", "yield"))
    phases = _junction_phases(["robot_4", "robot_3"], "robot_1")
    result = classify_plan_dispatch(
        "junction_clear",
        legs,
        phases[0]["command"],
        ["robot_1", "robot_3", "robot_4"],
        junction_phases=phases,
    )

    assert [item.kind for item in result.items] == ["order_differs"]


def test_junction_yielder_gap_is_flagged():
    legs = _legs(("robot_3", "reverse"), ("robot_4", "reverse"), ("robot_2", "yield"))
    phases = _junction_phases(["robot_3", "robot_4"], "robot_1")
    result = classify_plan_dispatch(
        "junction_clear",
        legs,
        phases[0]["command"],
        ["robot_1", "robot_2", "robot_3", "robot_4"],
        junction_phases=phases,
    )

    assert _items(result)["yielder"] == ("yielder_differs", "robot_2", "robot_1")


def test_leg_effects_on_the_b07a700f_plan_marks_overridden_and_not_sent():
    artifact = _fixture("m5V_b07a700f_reverse_handoff.json")
    result = _classify(artifact)

    effects = leg_effects(artifact["plan"]["legs"], result)

    assert effects == {
        "robot_3": ("as_planned", "reverse"),
        "robot_1": ("overridden", "reverse"),
        "robot_2": ("overridden", "reverse"),
        "robot_4": ("not_sent", "continue"),
    }


def test_leg_effects_skip_a_done_leg_the_dispatch_does_not_touch():
    artifact = _fixture("m5V_95066420_reverse_hold.json")
    result = _classify(artifact)

    effects = leg_effects(artifact["plan"]["legs"], result)

    assert effects == {
        "robot_4": ("as_planned", "reverse"),
        "robot_5": ("overridden", "reverse"),
    }


def test_reverse_dispatch_reads_executed_reverse():
    trace = reverse_dispatch(
        "reverse", _fixture("m5V_95066420_reverse_hold.json")["dispatched_command"]
    )

    assert trace is not None
    assert (trace.status, trace.reversed_robot_ids) == ("executed", ("robot_4", "robot_5"))


def test_reverse_dispatch_reads_untagged_refusal_from_the_wait_parameters():
    artifact = _fixture("cvD_6a05a618_reverse_refused.json")
    assert not artifact["dispatched_command"].get("degradations")

    trace = reverse_dispatch("reverse", artifact["dispatched_command"])

    assert trace is not None
    assert trace.status == "refused"
    assert trace.waiting_robot_ids == ("robot_2", "robot_4")
    assert trace.reason.startswith("reverse refused: both robots outside the corridor")
    assert trace.dispatched == "temporary_wait"


def test_reverse_dispatch_is_none_for_other_strategies():
    assert reverse_dispatch("yield", _yield_command("robot_1", ["robot_2"])) is None


@pytest.mark.parametrize("subject", ["robot_5", "yielder", "order"])
def test_override_tag_is_registered_as_a_provenance_marker(subject):
    assert degradation_cause(f"{OVERRIDE_TAG}:reverse:{subject}:continue->reverse") is None
    assert OVERRIDE_TAG in DEGRADATION_TAGS

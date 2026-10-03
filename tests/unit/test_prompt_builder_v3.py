"""Prompt v3 (prereg-v2 rev 4/6, 2026-10-02): plan-state block, reasoning-first JSON,
and the scenario-agnostic `proposed_plan` invitation."""

import hashlib
import re

import pytest
from pydantic import ValidationError

from reasoning.rag.command_grounder import _is_consistent, _plan_disagrees_with_decision_fields
from reasoning.vlm.models import (
    CURRENT_PROMPT_VERSION,
    CongestionDecision,
    FailureContext,
    PlanStateContext,
    PlanStateLeg,
    ProposedPlanLeg,
    ReasonerRequest,
    RobotStateInput,
    StaticObstacleInput,
)
from reasoning.vlm.prompt_builder import (
    _PLAN_GRAMMAR,
    _PLAN_INVITATION,
    SYSTEM_PROMPT,
    build_prompt_payload,
    render_plan_state_block,
)
from reasoning.vlm.prompt_v2 import SYSTEM_PROMPT_V2

_REASONING_LINE = (
    '- "reasoning": one to three sentences of your analysis, written before you commit '
    "to the fields below (what you see, why it is or is not congestion, and your plan "
    "if any)"
)
_PROPOSED_PLAN_LINE = (
    '- "proposed_plan": optional; your full proposed resolution as an ordered list of '
    '{"robot_id": ..., "action": ...}, action one of "yield", "reverse", "cross", '
    '"wait", "reroute", "continue" ("continue" for a known robot not part of the '
    "resolution); omit it, or set it to null, to let the system derive one for you"
)


def _request(**update: object) -> ReasonerRequest:
    base = ReasonerRequest(
        request_id="req-1",
        image_path="/tmp/frame.png",
        frame_id="overhead_camera",
        stamp=12.5,
        robot_states=[
            RobotStateInput(robot_id="robot_2", x=1.0, y=2.0, theta=1.57, status="MOVING"),
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
        ],
        prompt_version=3,
    )
    return ReasonerRequest(**{**base.model_dump(), **update})


def _goal_states() -> list[RobotStateInput]:
    return [
        RobotStateInput(
            robot_id="robot_1",
            x=-0.2,
            y=0.0,
            theta=0.0,
            linear_velocity=0.01,
            status="STOPPED",
            task="cross_narrow_aisle",
            goal=(2.5, 0.0),
        ),
        RobotStateInput(
            robot_id="robot_2",
            x=0.2,
            y=0.0,
            theta=3.14,
            linear_velocity=0.0,
            status="STALE",
            task="cross_narrow_aisle",
            goal=(-2.5, 0.0),
        ),
    ]


def _obstacle() -> StaticObstacleInput:
    return StaticObstacleInput(obstacle_id="obstacle_1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3)


def _plan_state(**update: object) -> PlanStateContext:
    base = {
        "plan_id": 3,
        "legs": [
            PlanStateLeg(robot_id="robot_1", action="yield", status="active"),
            PlanStateLeg(robot_id="robot_2", action="cross", status="pending"),
        ],
        "changed_robot_ids": ("robot_2",),
    }
    base.update(update)
    return PlanStateContext(**base)


def _prompt(**update: object) -> str:
    return build_prompt_payload(_request(**update)).user_prompt


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- versioning ----


def test_current_prompt_version_stays_v2_not_v3():
    # v3 is opt-in (M5 passes prompt_version=3 explicitly, e.g. behind
    # orchestrator.yaml's plan_channel_enabled): bumping the default would
    # silently change every existing caller's rendered prompt.
    assert CURRENT_PROMPT_VERSION == 2


def test_v3_is_a_known_version():
    assert _request(prompt_version=3).prompt_version == 3


def test_v3_differs_from_v2_on_the_same_request():
    assert _prompt() != _prompt(prompt_version=2)


def test_v3_keeps_the_system_prompt():
    assert build_prompt_payload(_request()).system_prompt == SYSTEM_PROMPT == SYSTEM_PROMPT_V2


# ---- reasoning-first JSON (rev 6) ----


def test_v3_lists_reasoning_before_every_other_field():
    prompt = _prompt()
    assert _REASONING_LINE in prompt
    fields_block = prompt[prompt.index(_REASONING_LINE) :]
    assert fields_block.index('"reasoning"') < fields_block.index('"congestion_detected"')
    assert fields_block.index('"congestion_detected"') < fields_block.index('"type"')


def test_v2_has_no_reasoning_field():
    assert "reasoning" not in _prompt(prompt_version=2)


# ---- proposed_plan invitation and output field (rev 3/4) ----


def test_v3_invites_the_proposed_plan_channel():
    prompt = _prompt()
    assert _PLAN_INVITATION in prompt
    assert prompt.index(_PLAN_INVITATION) < prompt.index("Produce a JSON object")


def test_v3_schema_lists_proposed_plan_last():
    prompt = _prompt()
    assert _PROPOSED_PLAN_LINE in prompt
    assert (_PROPOSED_PLAN_LINE + "\n\nRules:") in prompt


def test_v3_invitation_is_scenario_agnostic():
    # Names the field and the division of labor, never a strategy, scenario,
    # robot, or side.
    for term in ["yield", "reroute", "convoy", "robot_1", "robot_2", "west", "east"]:
        assert term not in _PLAN_INVITATION


def test_v2_has_neither_proposed_plan_mention_nor_invitation():
    prompt = _prompt(prompt_version=2)
    assert "proposed_plan" not in prompt
    assert _PLAN_INVITATION not in prompt


# ---- plan grammar (v3.1, 2026-10-03) ----

_STRATEGIES = list(CongestionDecision.model_fields["strategy"].annotation.__args__)
_ACTIONS = list(ProposedPlanLeg.model_fields["action"].annotation.__args__)


def _junction_states() -> list[RobotStateInput]:
    # IB10 formed-jam geometry (demo ep2 trigger snapshot, rounded).
    return [
        RobotStateInput(robot_id="robot_1", x=-0.24, y=0.01, theta=0.07, status="STOPPED"),
        RobotStateInput(robot_id="robot_2", x=0.24, y=0.02, theta=2.87, status="STOPPED"),
        RobotStateInput(robot_id="robot_3", x=-0.03, y=-0.29, theta=1.77, status="SLOW"),
        RobotStateInput(robot_id="robot_4", x=0.00, y=0.26, theta=-1.42, status="STOPPED"),
    ]


def _plan_region(prompt: str) -> str:
    # Extracted from the invitation to the schema header, independently of
    # `_PLAN_GRAMMAR` itself, so the byte-identity check below cannot pass
    # merely because the constant is a substring of both renders.
    return prompt[prompt.index("You may also propose") : prompt.index("Produce a JSON object")]


def test_v3_renders_the_plan_grammar_between_invitation_and_schema():
    prompt = _prompt()
    assert _PLAN_GRAMMAR in prompt
    assert prompt.index(_PLAN_INVITATION) < prompt.index(_PLAN_GRAMMAR)
    assert prompt.index(_PLAN_GRAMMAR) < prompt.index("Produce a JSON object")


def test_v3_plan_grammar_renders_byte_identically_on_head_on_and_junction_scenes():
    head_on = _prompt(robot_states=_goal_states(), static_obstacles=[_obstacle()],
                      include_static_obstacles=True)
    junction = _prompt(robot_states=_junction_states(), plan_state=_plan_state())
    assert head_on != junction
    assert _plan_region(head_on) == _plan_region(junction)
    assert _plan_region(head_on) == _PLAN_INVITATION + "\n" + _PLAN_GRAMMAR + "\n"


def test_v3_plan_grammar_glosses_every_plan_action_once():
    for action in _ACTIONS:
        assert _PLAN_GRAMMAR.count(f'\n- "{action}": ') == 1


def test_v3_glosses_every_strategy_token_in_the_same_register():
    # No strategy is singled out: every enum value gets exactly one gloss line.
    prompt = _prompt()
    for strategy in _STRATEGIES:
        assert prompt.count(f'\n  - "{strategy}": ') == 1


@pytest.mark.parametrize(
    ("strategy", "action", "minimum", "exact"),
    [
        ("yield", "yield", 1, True),
        ("temporary_wait", "wait", 1, False),
        ("reroute", "reroute", 1, False),
    ],
)
def test_v3_plan_grammar_count_rules_match_is_consistent(
    strategy: str, action: str, minimum: int, exact: bool
):
    rule = "exactly one" if exact else "at least one"
    assert f'- strategy "{strategy}": {rule} "{action}" leg' in _PLAN_GRAMMAR

    def legs(n: int) -> list[ProposedPlanLeg]:
        return [ProposedPlanLeg(robot_id=f"robot_{i}", action=action) for i in range(n)] + [
            ProposedPlanLeg(robot_id="robot_9", action="continue")
        ]

    assert _is_consistent(strategy, legs(minimum))
    assert not _is_consistent(strategy, legs(minimum - 1))
    assert _is_consistent(strategy, legs(minimum + 1)) is not exact


def test_v3_plan_grammar_states_the_decision_field_agreement_rule_on_yield_only():
    # `_plan_disagrees_with_decision_fields` runs for strategy "yield" only,
    # so the agreement rule rides that line and no other.
    yield_line = next(
        line for line in _PLAN_GRAMMAR.splitlines() if line.startswith('- strategy "yield"')
    )
    assert yield_line.endswith(
        "and the plan must agree with your own yield_robot and crossing_order answers"
    )
    assert _PLAN_GRAMMAR.count("yield_robot") == 1
    yield_decision = CongestionDecision(
        congestion_detected=True, type="deadlock", involved_robots=["robot_1", "robot_2"],
        root_cause="r", strategy="yield", justification="j", yield_robot="robot_1",
        proposed_plan=[
            ProposedPlanLeg(robot_id="robot_2", action="yield"),
            ProposedPlanLeg(robot_id="robot_1", action="cross"),
        ],
    )
    assert _plan_disagrees_with_decision_fields(yield_decision, yield_decision.proposed_plan)
    other = yield_decision.model_copy(update={"strategy": "junction_clear"})
    assert _plan_disagrees_with_decision_fields(other, other.proposed_plan) is None


def test_v3_convoy_gloss_names_the_opposing_robot():
    assert (
        '  - "convoy": robots heading the same way pass through in single file, in order, '
        "while an opposing robot gives way\n"
    ) in _prompt()


def test_v3_plan_grammar_junction_clear_rule_matches_is_consistent():
    assert '- strategy "junction_clear": at least one "reverse" or "yield" leg' in _PLAN_GRAMMAR
    for action in ("reverse", "yield"):
        assert _is_consistent("junction_clear", [ProposedPlanLeg(robot_id="r", action=action)])
    others = [a for a in _ACTIONS if a not in ("reverse", "yield")]
    other_legs = [ProposedPlanLeg(robot_id=f"r{i}", action=a) for i, a in enumerate(others)]
    assert not _is_consistent("junction_clear", other_legs)


def test_v3_plan_grammar_other_strategies_are_unconstrained_in_is_consistent():
    constrained = {"yield", "temporary_wait", "reroute", "junction_clear"}
    for strategy in _STRATEGIES:
        if strategy in constrained:
            continue
        assert f'strategy "{strategy}"' not in _PLAN_GRAMMAR
        assert _is_consistent(strategy, [ProposedPlanLeg(robot_id="r", action="continue")])


def test_v3_plan_grammar_is_scenario_agnostic():
    # Contract only: no robot ids, sides, scene nouns or counts.
    words = set(re.findall(r"[a-z_.-]+", _PLAN_GRAMMAR.lower()))
    for term in ["west", "east", "north", "south", "aisle", "intersection", "head-on",
                 "example", "e.g."]:
        assert term not in words
    assert "robot_" not in _PLAN_GRAMMAR
    assert not any(ch.isdigit() for ch in _PLAN_GRAMMAR)


def test_v2_has_no_plan_grammar():
    assert _PLAN_GRAMMAR not in _prompt(prompt_version=2)


# ---- plan-state block (rev 4, generalizing failure-context) ----


def test_v3_renders_plan_state_block_with_every_leg_and_status():
    prompt = _prompt(plan_state=_plan_state())
    assert "Active plan (plan_id=3):" in prompt
    assert "- robot_1: yield (active)" in prompt
    assert "- robot_2: cross (pending)" in prompt
    assert "Changed since the last invocation: robot_2" in prompt


def test_v3_plan_state_block_with_no_change_says_so():
    prompt = _prompt(plan_state=_plan_state(changed_robot_ids=()))
    assert "Nothing has changed since this plan was accepted." in prompt
    assert "Changed since the last invocation" not in prompt


def test_v3_omits_plan_state_block_when_absent():
    prompt = _prompt()
    assert "Active plan (plan_id=" not in prompt


def test_v3_plan_state_and_failure_context_can_coexist():
    context = FailureContext(
        strategy="yield",
        yield_robot="robot_1",
        outcome_status="failed",
        failure_detail="yield failed after 122 s; congestion re-detected for the same robots",
    )
    prompt = _prompt(failure_context=context, plan_state=_plan_state())
    assert "Previous attempt in this episode:" in prompt
    assert "Active plan (plan_id=3):" in prompt
    assert prompt.index("Previous attempt") < prompt.index("Active plan")


def test_render_plan_state_block_matches_what_the_prompt_renders():
    state = _plan_state()
    prompt = _prompt(plan_state=state)
    assert render_plan_state_block(state) in prompt


def test_v2_never_renders_a_plan_state_block_even_if_a_v3_request_is_replayed_as_v2():
    # plan_state is read only by the v3 template; a v2 request simply never
    # looks at the field (same convention as every other v3-only field).
    prompt = _prompt(prompt_version=2, plan_state=_plan_state())
    assert "Active plan (plan_id=" not in prompt


# ---- invariants the earlier features established, re-checked on v3 ----


def test_v3_id_desc_differs_only_in_the_ordered_regions():
    marker = "\nGuidance:\n"
    ascending = _prompt()
    descending = _prompt(robot_presentation_order="id_desc")
    assert ascending != descending
    assert len(ascending) == len(descending)
    assert ascending[ascending.index(marker) :] == descending[descending.index(marker) :]
    head = "Robot states:\n"
    assert ascending[: ascending.index(head)] == descending[: descending.index(head)]


def test_v3_renders_goal_and_task_when_present():
    prompt = _prompt(robot_states=_goal_states())
    assert (
        "- robot_id=robot_1, x=-0.20, y=0.00, theta=0.00, status=STOPPED, "
        "goal_x=2.50, goal_y=0.00, task=cross_narrow_aisle, linear_velocity=0.01\n"
    ) in prompt


# ---- pins ----

# name -> (length, SHA-256) of the v3 user prompt. Pinned when the plan-state /
# reasoning-first bundle landed, before any live data collected under v3; after
# the v2 freeze a change here is a new prompt version, not a re-pin.
_V3_PINS: dict[str, tuple[int, str]] = {
    # Re-pinned (prereg-v2 build-order step 5, 2026-10-02): the strategy
    # list gained "junction_clear" (+19 chars on every cell); no other v3
    # text changed. v1/v2 are frozen, separate modules and are unaffected.
    # Re-pinned again for revision v3.1 (2026-10-03, still pre-freeze): the
    # static `_PLAN_GRAMMAR` block and a one-line gloss per strategy token
    # (+1255 chars on every cell, identical delta everywhere). The v3.0
    # baseline digest was 22baf2df179c58fbbf1a757f2e7fe9ed435a533c434d966b272be3dcec551286
    # -- stored v3 artifacts carry `prompt_version: 3` either way, so
    # `user_sha256` is what tells a v3.0 decision from a v3.1 one.
    # Re-pinned for v3.2 (2026-10-03 coordinator ruling): the "yield" rule
    # line states the decision-field agreement rule and the convoy gloss
    # gains "while an opposing robot gives way" (+113 chars everywhere).
    # The v3.1 baseline digest was
    # 42463ce2c2610273d649dd5eca9dc61ff8bf3272023730a2feba3703130b9a4c (the
    # 2026-10-03 live ER-2 calibration episode ran on v3.1).
    "baseline": (
        6029,
        "c3fb9fcf4031f3c11961bfe7015887a38901d01049810f289b0c45324c36f873",
    ),
    "id_desc": (
        6029,
        "b5aa9b3540547a80db96c7a4d76b738edeb5eb0cb5216cf2d17a7d7e19d143d6",
    ),
    "no_geometry": (
        5843,
        "43eb4d90350bdbd5e08fd9aee3a3212b9b51401ac870aedc68886ce12ccc5f11",
    ),
    "goals_obstacles": (
        6432,
        "0e117f10d978030346e5cf04c23417c79997facfbd58605539f0b95203bda860",
    ),
    "plan_state": (
        6311,
        "080c12e4ae1c893f190aba29f063d978481432f119d1ff09b9521dcd6f950454",
    ),
    "failure_context": (
        6388,
        "495e565168db91d48621613496d498cc4f91ea7ccd8b4b64572b9ce4e34b9ea1",
    ),
}


def _pinned_requests() -> dict[str, ReasonerRequest]:
    return {
        "baseline": _request(),
        "id_desc": _request(robot_presentation_order="id_desc"),
        "no_geometry": _request(include_pairwise_geometry=False),
        "goals_obstacles": _request(
            robot_states=_goal_states(),
            static_obstacles=[_obstacle()],
            include_static_obstacles=True,
        ),
        "plan_state": _request(plan_state=_plan_state()),
        "failure_context": _request(
            failure_context=FailureContext(
                strategy="yield",
                yield_robot="robot_1",
                outcome_status="failed",
                failure_detail=(
                    "yield failed after 122 s; congestion re-detected for the same robots"
                ),
            )
        ),
    }


@pytest.mark.parametrize("name", list(_V3_PINS))
def test_v3_prompt_matches_its_pin(name: str):
    prompt = build_prompt_payload(_pinned_requests()[name]).user_prompt
    length, digest = _V3_PINS[name]
    assert len(prompt) == length
    assert _sha256(prompt) == digest


def test_v3_prompt_version_rejects_unknown_version():
    with pytest.raises(ValidationError):
        _request(prompt_version=4)

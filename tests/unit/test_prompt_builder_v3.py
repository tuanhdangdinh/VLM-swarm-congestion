"""Prompt v3 (prereg-v2 rev 4/6, 2026-10-02): plan-state block, reasoning-first JSON,
and the scenario-agnostic `proposed_plan` invitation."""

import hashlib

import pytest
from pydantic import ValidationError

from reasoning.vlm.models import (
    CURRENT_PROMPT_VERSION,
    FailureContext,
    PlanStateContext,
    PlanStateLeg,
    ReasonerRequest,
    RobotStateInput,
    StaticObstacleInput,
)
from reasoning.vlm.prompt_builder import (
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
    "baseline": (
        4642,
        "45de3546ae70ac073bf89f86a38a490302bd0f267cb5e16446bfe6302946674b",
    ),
    "id_desc": (
        4642,
        "adafcd84d6a21d6fca7733e978fef37b2de55981df08706969311fb08fa48b93",
    ),
    "no_geometry": (
        4456,
        "8e513c4b561a76e80472be7136f8c3cf9aec8fafdeac0cfdd127a44ea53226a8",
    ),
    "goals_obstacles": (
        5045,
        "8c9ce445ee84d35bb03c6e4934a9ad4c09466cb153b4d6ad8ddf9b360eea478c",
    ),
    "plan_state": (
        4924,
        "1536eaec10d7446f207dc62cd22bdfe3590507fea50e8de5cf61d16ea88e9e9a",
    ),
    "failure_context": (
        5001,
        "2f9cc036f198e8512ff2ca4ffc55935150d3f2725120f6539b7ae2627df05b8b",
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

"""Prompt v2 (the prompt-v2 bundle, 2026-09-27): new fields, goals/task, header fix."""

import hashlib

import pytest
from pydantic import ValidationError

from reasoning.vlm.models import (
    CURRENT_PROMPT_VERSION,
    FailureContext,
    ReasonerRequest,
    RobotStateInput,
    StaticObstacleInput,
)
from reasoning.vlm.prompt_builder import SYSTEM_PROMPT, build_prompt_payload
from reasoning.vlm.prompt_v1 import SYSTEM_PROMPT_V1, render_user_prompt_v1

_BLOCKER_KIND_LINE = (
    '- "blocker_kind": what is blocking the involved robots: "robot" when it is one '
    'of the robots listed above, "object" when it is a fixed obstacle, "transient" '
    "when it is a temporary obstruction expected to clear on its own; null when "
    "congestion_detected is false"
)
_CROSSING_ORDER_LINE = (
    '- "crossing_order": when three or more robots must be ordered, every involved '
    "robot ID in the order they should pass, first to pass first (a robot that "
    "yields passes after the robots it yields to); otherwise null"
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


def _prompt(**update: object) -> str:
    return build_prompt_payload(_request(**update)).user_prompt


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- versioning ----


def test_reasoner_request_defaults_to_the_current_prompt_version():
    assert CURRENT_PROMPT_VERSION == 2
    assert _request().prompt_version == 2


def test_reasoner_request_rejects_an_unknown_prompt_version():
    with pytest.raises(ValidationError):
        _request(prompt_version=3)


def test_prompt_version_1_dispatches_to_the_frozen_renderer():
    request = _request(prompt_version=1, robot_states=_goal_states())
    assert build_prompt_payload(request).user_prompt == render_user_prompt_v1(request)
    assert build_prompt_payload(request).system_prompt == SYSTEM_PROMPT_V1


def test_v2_differs_from_v1_on_the_same_request():
    assert _prompt() != _prompt(prompt_version=1)


def test_v2_keeps_the_system_prompt():
    assert build_prompt_payload(_request()).system_prompt == SYSTEM_PROMPT == SYSTEM_PROMPT_V1


# ---- new output fields ----


def test_v2_schema_lists_blocker_kind_after_yield_robot():
    prompt = _prompt()
    assert _BLOCKER_KIND_LINE in prompt
    assert prompt.index('- "yield_robot"') < prompt.index('- "blocker_kind"')


def test_v2_schema_lists_crossing_order_after_blocker_kind():
    prompt = _prompt()
    assert _CROSSING_ORDER_LINE in prompt
    assert prompt.index('- "blocker_kind"') < prompt.index('- "crossing_order"')
    assert (_CROSSING_ORDER_LINE + "\n\nRules:") in prompt


def test_v1_schema_has_neither_new_field():
    prompt = _prompt(prompt_version=1)
    assert "blocker_kind" not in prompt and "crossing_order" not in prompt


# ---- riders: header and task/goal rendering ----


def test_v2_header_makes_no_ordering_claim():
    for order in ("id_asc", "id_desc"):
        prompt = _prompt(robot_presentation_order=order)
        assert "\nRobot states:\n" in prompt
        assert "sorted by ID" not in prompt


def test_v1_header_still_claims_sorted_by_id():
    assert "Robot states (sorted by ID):" in _prompt(prompt_version=1)


def test_v2_renders_goal_and_task_when_present():
    prompt = _prompt(robot_states=_goal_states())
    assert (
        "- robot_id=robot_1, x=-0.20, y=0.00, theta=0.00, status=STOPPED, "
        "goal_x=2.50, goal_y=0.00, task=cross_narrow_aisle, linear_velocity=0.01\n"
    ) in prompt
    assert (
        "- robot_id=robot_2, x=0.20, y=0.00, theta=3.14, status=STALE, "
        "goal_x=-2.50, goal_y=0.00, task=cross_narrow_aisle, linear_velocity=0.00\n"
    ) in prompt


def test_v2_omits_goal_and_task_when_absent():
    prompt = _prompt()
    assert "goal_x" not in prompt and "task=" not in prompt


def test_v2_guidance_admits_stated_goals_as_evidence():
    # Amendments item 15a: v2 renders goals and tasks, so the v1 line forbidding
    # "assumptions about intent" would contradict them; only unstated intent is barred.
    prompt = _prompt(robot_states=_goal_states())
    assert (
        "- Decide from the robot states (including their stated goals and tasks) and the "
        "image; do not assume intentions beyond what is stated.\n"
    ) in prompt
    assert "assumptions about intent" not in prompt


def test_v1_guidance_keeps_the_intent_line():
    assert "not from assumptions about intent." in _prompt(prompt_version=1)


# ---- invariants the earlier features established, re-checked on v2 ----


def test_v2_id_desc_differs_only_in_the_ordered_regions():
    marker = "\nGuidance:\n"
    ascending = _prompt()
    descending = _prompt(robot_presentation_order="id_desc")
    assert ascending != descending
    assert len(ascending) == len(descending)
    assert ascending[ascending.index(marker) :] == descending[descending.index(marker) :]
    head = "Robot states:\n"
    assert ascending[: ascending.index(head)] == descending[: descending.index(head)]


def test_v2_omits_yielder_selection_criteria():
    # Same guard as the v1 test; the literal field name `blocker_kind` is the
    # one sanctioned occurrence of "blocker" (the T3a verdict the field asks
    # for), so only that token is exempted.
    for update in ({}, {"static_obstacles": [_obstacle()], "include_static_obstacles": True}):
        prompt = _prompt(**update).lower().replace('"blocker_kind"', "")
        for term in ["space", "retreat", "blocker", "clearance", "arrival", "first listed"]:
            assert term not in prompt


def _obstacle() -> StaticObstacleInput:
    return StaticObstacleInput(obstacle_id="obstacle_1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3)


def test_v2_new_schema_lines_name_no_robot_and_no_side():
    for line in (_BLOCKER_KIND_LINE, _CROSSING_ORDER_LINE):
        for term in ["robot_1", "robot_2", "west", "east", "back up"]:
            assert term not in line


def test_v2_failure_context_seams_are_unchanged():
    context = FailureContext(
        strategy="yield",
        yield_robot="robot_1",
        outcome_status="failed",
        failure_detail="yield failed after 122 s; congestion re-detected for the same robots",
    )
    prompt = _prompt(failure_context=context)
    assert 'Known robot IDs: ["robot_1", "robot_2"]\n\nPrevious attempt' in prompt
    assert "unless the scene has changed.\n\nGuidance:" in prompt


# ---- pins ----

# name -> (length, SHA-256) of the v2 user prompt. Pinned when the bundle
# landed and re-pinned once for the 15a guidance-line sign-off, before the
# freeze and before any live data; after the freeze a change here is a new
# prompt version, not a re-pin.
_V2_PINS: dict[str, tuple[int, str]] = {
    "baseline": (
        3846,
        "a7742ac423197c58d155279168952f40a302c61fd782db8e89a3abd9d1eb5109",
    ),
    "id_desc": (
        3846,
        "aad2b7a9c0a14985ce63a7295cb1a3d565156c16e69f980d1216b764ccfbd3c0",
    ),
    "no_geometry": (
        3660,
        "b837bfe2f790b9623cb126dc38d10c7661866475835f9f1b9c4c35dc35ec116c",
    ),
    "goals_obstacles": (
        4249,
        "960b2d672c271eccaaa7bfd5b370294ba32ba60c05f9e4951d173e245f81faa9",
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
    }


@pytest.mark.parametrize("name", ["baseline", "id_desc", "no_geometry", "goals_obstacles"])
def test_v2_prompt_matches_its_pin(name: str):
    prompt = build_prompt_payload(_pinned_requests()[name]).user_prompt
    length, digest = _V2_PINS[name]
    assert len(prompt) == length
    assert _sha256(prompt) == digest

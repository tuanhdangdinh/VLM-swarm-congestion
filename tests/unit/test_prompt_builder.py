import json

import pytest
from pydantic import ValidationError

from reasoning.vlm.models import FailureContext, ReasonerRequest, RobotStateInput
from reasoning.vlm.prompt_builder import (
    SYSTEM_PROMPT,
    build_prompt_payload,
    format_robot_state_lines,
    render_failure_context_block,
)


def _request() -> ReasonerRequest:
    return ReasonerRequest(
        request_id="req-1",
        image_path="/tmp/frame.png",
        frame_id="overhead_camera",
        stamp=12.5,
        robot_states=[
            RobotStateInput(robot_id="robot_2", x=1.0, y=2.0, theta=1.57, status="MOVING"),
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
        ],
    )


def test_format_robot_state_lines_includes_required_fields():
    lines = format_robot_state_lines([RobotStateInput(robot_id="robot_1", x=1.2, y=0.4, theta=1.57)])  # noqa: E501
    assert lines == ["robot_id=robot_1, x=1.20, y=0.40, theta=1.57"]


def test_format_robot_state_lines_appends_optional_fields_when_present():
    lines = format_robot_state_lines(
        [RobotStateInput(robot_id="robot_1", x=1.2, y=0.4, theta=1.57, status="MOVING", task="deliver_A", linear_velocity=0.15, angular_velocity=0.0)]  # noqa: E501
    )
    assert lines == [
        "robot_id=robot_1, x=1.20, y=0.40, theta=1.57, status=MOVING, task=deliver_A, linear_velocity=0.15, angular_velocity=0.00"  # noqa: E501
    ]


def test_build_prompt_payload_sorts_robots_and_collects_ids():
    payload = build_prompt_payload(_request())
    assert payload.known_robot_ids == ["robot_1", "robot_2"]
    assert payload.user_prompt.index("robot_id=robot_1") < payload.user_prompt.index("robot_id=robot_2")  # noqa: E501


def test_build_prompt_payload_is_deterministic():
    assert build_prompt_payload(_request()).user_prompt == build_prompt_payload(_request()).user_prompt  # noqa: E501


def test_build_prompt_payload_uses_fixed_system_prompt():
    assert build_prompt_payload(_request()).system_prompt == SYSTEM_PROMPT


def test_build_prompt_payload_embeds_known_ids_json():
    payload = build_prompt_payload(_request())
    assert json.dumps(["robot_1", "robot_2"]) in payload.user_prompt


def test_system_prompt_is_minimal_for_cosmos_reason2():
    # NVIDIA's Cosmos Reason 2 guide: keep the system prompt minimal and put the
    # task framing in the user turn.
    assert SYSTEM_PROMPT == "You are a helpful assistant."


def test_build_prompt_payload_requests_reasoning_trace():
    payload = build_prompt_payload(_request())
    assert "<think>" in payload.user_prompt
    assert "</think>" in payload.user_prompt


def test_reasoner_request_failure_context_defaults_to_none():
    assert _request().failure_context is None


def test_failure_context_optional_role_fields_default_to_none():
    ctx = FailureContext(
        strategy="yield",
        outcome_status="failed",
        failure_detail="yield failed after 12 s; congestion re-detected for the same robots",
    )
    assert ctx.yield_robot is None
    assert ctx.crossing_order is None


def test_failure_context_is_frozen():
    ctx = FailureContext(strategy="yield", outcome_status="failed", failure_detail="d")
    with pytest.raises(ValidationError):
        ctx.strategy = "reverse"


def test_failure_context_rejects_empty_strategy():
    with pytest.raises(ValidationError):
        FailureContext(strategy="", outcome_status="failed", failure_detail="d")


def _completed_yield() -> FailureContext:
    return FailureContext(
        strategy="yield",
        yield_robot="robot_1",
        outcome_status="completed",
        failure_detail="yield completed 31 s ago; congestion re-detected for the same robots",
    )


def test_render_failure_context_block_includes_strategy_outcome_and_detail():
    block = render_failure_context_block(_completed_yield())
    assert block.startswith("Previous attempt in this episode:")
    assert "- strategy=yield, yield_robot=robot_1, outcome=completed" in block
    assert (
        "- detail: yield completed 31 s ago; congestion re-detected for the same robots"
        in block
    )
    assert block.endswith("unless the scene has changed.")
    assert not block.startswith("\n") and not block.endswith("\n")


def test_render_failure_context_block_omits_yield_robot_when_none():
    block = render_failure_context_block(
        FailureContext(
            strategy="temporary_wait",
            outcome_status="timed_out",
            failure_detail="temporary_wait timed_out after 20 s; congestion re-detected for the same robots",  # noqa: E501
        )
    )
    assert "- strategy=temporary_wait, outcome=timed_out" in block
    assert "yield_robot" not in block


def test_build_prompt_payload_places_failure_block_before_guidance_when_set():
    request = _request().model_copy(update={"failure_context": _completed_yield()})
    prompt = build_prompt_payload(request).user_prompt
    ids = prompt.index("Known robot IDs:")
    block = prompt.index("Previous attempt in this episode:")
    guidance = prompt.index("Guidance:")
    assert ids < block < guidance
    assert 'Known robot IDs: ["robot_1", "robot_2"]\n\nPrevious attempt' in prompt
    assert "unless the scene has changed.\n\nGuidance:" in prompt


def test_build_prompt_payload_seam_is_unchanged_when_failure_context_none():
    prompt = build_prompt_payload(_request()).user_prompt
    assert 'Known robot IDs: ["robot_1", "robot_2"]\n\nGuidance:' in prompt
    assert "Previous attempt" not in prompt

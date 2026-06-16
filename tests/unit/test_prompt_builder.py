import json

from reasoning.vlm.models import ReasonerRequest, RobotStateInput
from reasoning.vlm.prompt_builder import (
    SYSTEM_PROMPT,
    build_prompt_payload,
    format_robot_state_lines,
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

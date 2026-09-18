import hashlib
import json

import pytest
from pydantic import ValidationError

from reasoning.vlm.models import FailureContext, ReasonerRequest, RobotStateInput
from reasoning.vlm.prompt_builder import (
    SYSTEM_PROMPT,
    build_prompt_payload,
    format_pairwise_geometry_lines,
    format_robot_state_lines,
    render_failure_context_block,
    render_visual_crosscheck_block,
)

# SHA-256 of the rendered user prompt for `_request()` before the opt-in
# visual-crosscheck block existed (commit 7f5e075, the prompt every artifact under
# data/logs/er2_grounding was produced with). Pinned so a stray newline from the
# new placeholder cannot silently change the default prompt: the flag is an added
# ablation condition, not a change to the apparatus.
_BASELINE_PROMPT_SHA256 = "5a57c937ff3a25021e6819f89e9f61fcf5d70ba1b15b969c3eb19bd80409ddfc"
_BASELINE_PROMPT_SHA256_NO_GEOMETRY = (
    "4664ff95aea2aff993b71962f108c85badb6d6cd8a45bc5936c4709cfc365c2a"
)
_NO_REDERIVE_CLAUSE = (
    "Use the pairwise geometry above; do not re-derive distances or facing from the coordinates."
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


def test_format_pairwise_geometry_flags_robots_facing_each_other():
    lines = format_pairwise_geometry_lines(
        [
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_2", x=1.0, y=0.0, theta=3.14159),
        ]
    )
    assert lines == [
        "robot_1 <-> robot_2: distance 1.00 m; robot_1 faces robot_2: yes; "
        "robot_2 faces robot_1: yes"
    ]


def test_format_pairwise_geometry_flags_diverging_robots_despite_opposite_headings():
    # robot_2 sits west of robot_1 and heads west; robot_1 heads east: moving apart
    lines = format_pairwise_geometry_lines(
        [
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_2", x=-1.25, y=0.0, theta=3.14159),
        ]
    )
    assert lines == [
        "robot_1 <-> robot_2: distance 1.25 m; robot_1 faces robot_2: no; "
        "robot_2 faces robot_1: no"
    ]


def test_format_pairwise_geometry_is_empty_with_fewer_than_two_robots():
    assert format_pairwise_geometry_lines([]) == []
    single = [RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)]
    assert format_pairwise_geometry_lines(single) == []


def test_build_prompt_payload_places_pairwise_geometry_between_states_and_known_ids():
    prompt = build_prompt_payload(_request()).user_prompt
    assert (
        "robot_id=robot_2, x=1.00, y=2.00, theta=1.57, status=MOVING\n\n"
        "Pairwise geometry (faces = heading within 60° of the direction to the other robot):\n"
        "- robot_1 <-> robot_2: distance 2.24 m; robot_1 faces robot_2: no; "
        "robot_2 faces robot_1: no\n\n"
        'Known robot IDs: ["robot_1", "robot_2"]'
    ) in prompt


def test_build_prompt_payload_omits_geometry_block_when_switched_off():
    request = _request().model_copy(update={"include_pairwise_geometry": False})
    prompt = build_prompt_payload(request).user_prompt
    assert "Pairwise geometry" not in prompt
    assert "pairwise geometry" not in prompt
    assert 'status=MOVING\n\nKnown robot IDs: ["robot_1", "robot_2"]' in prompt


def test_build_prompt_payload_keeps_facing_definition_when_geometry_switched_off():
    request = _request().model_copy(update={"include_pairwise_geometry": False})
    prompt = build_prompt_payload(request).user_prompt
    assert "each facing the other" in prompt
    assert "Opposite headings alone do NOT mean head-on" in prompt
    assert "from the coordinates" in prompt


def test_build_prompt_payload_guidance_defines_head_on_by_facing_and_distance():
    prompt = build_prompt_payload(_request()).user_prompt
    assert "each facing the other" in prompt
    assert "Opposite headings alone do NOT mean head-on" in prompt
    assert "differing by ~π" not in prompt
    assert "opposing goal directions" not in prompt


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_reasoner_request_visual_crosscheck_defaults_to_off():
    assert _request().include_visual_crosscheck is False


def test_build_prompt_payload_is_byte_identical_to_baseline_when_crosscheck_off():
    assert _sha256(build_prompt_payload(_request()).user_prompt) == _BASELINE_PROMPT_SHA256


def test_build_prompt_payload_is_byte_identical_to_baseline_without_geometry_or_crosscheck():
    request = _request().model_copy(update={"include_pairwise_geometry": False})
    assert (
        _sha256(build_prompt_payload(request).user_prompt)
        == _BASELINE_PROMPT_SHA256_NO_GEOMETRY
    )


def test_build_prompt_payload_omits_crosscheck_block_when_switched_off():
    prompt = build_prompt_payload(_request()).user_prompt
    assert "Cross-check the states against the image" not in prompt
    assert "about intent.\n\nProduce a JSON object" in prompt


def test_build_prompt_payload_appends_crosscheck_block_when_switched_on():
    request = _request().model_copy(update={"include_visual_crosscheck": True})
    prompt = build_prompt_payload(request).user_prompt
    assert "Cross-check the states against the image:" in prompt
    intent = prompt.index("assumptions about intent.")
    block = prompt.index("Cross-check the states against the image:")
    fields = prompt.index("Produce a JSON object with exactly these fields:")
    assert intent < block < fields
    assert "about intent.\n\nCross-check the states against the image:" in prompt
    assert "stated positions.\n\nProduce a JSON object" in prompt


def test_build_prompt_payload_keeps_no_rederive_clause_in_both_crosscheck_variants():
    # Fix B (2026-09-17): without this clause the VLM re-derived geometry from raw
    # theta and called two diverging robots a deadlock. The crosscheck block must
    # establish precedence, never replace this clause.
    off = build_prompt_payload(_request()).user_prompt
    on = build_prompt_payload(
        _request().model_copy(update={"include_visual_crosscheck": True})
    ).user_prompt
    assert _NO_REDERIVE_CLAUSE in off
    assert _NO_REDERIVE_CLAUSE in on


def test_crosscheck_block_states_image_precedence_only_on_clear_contradiction():
    block = render_visual_crosscheck_block(include_pairwise_geometry=True)
    assert "Only a clear contradiction matters" in block
    assert "trust the image" in block
    assert "naming the disagreement between the image and the stated positions" in block
    assert not block.startswith("\n") and not block.endswith("\n")


def test_crosscheck_block_never_invites_recomputing_geometry():
    # Any verb that reads as licence to derive geometry from raw coordinates would
    # reopen the run-3 failure mode the block is required not to reintroduce.
    for include_geometry in (True, False):
        block = render_visual_crosscheck_block(include_pairwise_geometry=include_geometry).lower()
        for forbidden in ("compute", "calculate", "measure", "estimate", "work out"):
            assert forbidden not in block
        assert "re-derive" not in block.replace("do not re-derive", "")


def test_crosscheck_block_names_the_geometry_block_as_default_source_when_geometry_on():
    block = render_visual_crosscheck_block(include_pairwise_geometry=True)
    assert "The pairwise geometry above stays the default source" in block
    assert "do not re-derive distances or facing from the coordinates" in block


def test_crosscheck_block_names_the_coordinates_as_default_source_when_geometry_off():
    block = render_visual_crosscheck_block(include_pairwise_geometry=False)
    assert "The coordinates above stay the default source" in block
    assert "pairwise geometry" not in block


def test_crosscheck_block_warns_that_tracker_states_can_be_wrong():
    block = render_visual_crosscheck_block(include_pairwise_geometry=True)
    assert "overhead camera tracker and can be wrong" in block
    assert "stale" in block and "swapped" in block


def test_render_failure_context_block_allows_reporting_no_congestion():
    block = render_failure_context_block(_completed_yield())
    assert (
        "If the congestion is no longer present, report congestion_detected=false. "
        "If it persists and the previous strategy did not clear it, prefer a different "
        "strategy unless the scene has changed."
    ) in block

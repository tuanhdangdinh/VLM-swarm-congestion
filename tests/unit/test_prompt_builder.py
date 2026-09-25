import hashlib
import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from reasoning.vlm.models import (
    FailureContext,
    ReasonerRequest,
    RobotStateInput,
    StaticObstacleInput,
)
from reasoning.vlm.prompt_builder import (
    SYSTEM_PROMPT,
    build_prompt_payload,
    format_pairwise_geometry_lines,
    format_robot_state_lines,
    format_static_obstacle_lines,
    order_robot_states,
    render_failure_context_block,
    render_visual_crosscheck_block,
)

# SHA-256 of the rendered user prompt for `_request()` with the opt-in
# visual-crosscheck block off. Pinned so a stray newline from the placeholder
# cannot silently change the default prompt: the flag is an added ablation
# condition, not a change to the apparatus.
#
# Re-pinned when `feat/gemini-er2-backend` merged into the FR2.1.9 line: these
# constants were generated at 7f5e075, which predates the permanent `yield_robot`
# stimulus change (rev-8 spec rev 8.6, 2026-09-19). Rendering `_request()` at
# 7d6e1c4 and at the merge differs only by the three documented FR2.1.9 edits —
# the guidance clause ("the robot named in yield_robot backs up" replacing
# "first listed robot backs up"), the `"yield_robot"` output-format bullet, and
# the extended `<think>` step — so the placeholder still adds no bytes and the
# pin is re-pointed rather than the code changed. The geometry-on value is now
# identical to `_PRE_OBSTACLE_OFF_PROMPT_SHA256` below by construction; the two
# constants are kept separate because they pin the same string for different
# reasons (crosscheck placeholder vs static-obstacle modality).
#
# Artifacts under data/logs/er2_grounding were produced with the 7f5e075 prompt
# (5a57c937…, geometry-off 4664ff95…), so they are comparable with each other
# but not byte-identical to anything rendered after the FR2.1.9 change.
_BASELINE_PROMPT_SHA256 = "3b77d224bb1c6de2f73ccd69c08b6ac686ae41dd9dca86442e5f34d278164001"
_BASELINE_PROMPT_SHA256_NO_GEOMETRY = (
    "a9c8abfc900a47d77a725b4855252a3ae623698a00e3ca394808cbed281945ed"
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


def test_build_prompt_payload_output_format_includes_yield_robot_bullet():
    prompt = build_prompt_payload(_request()).user_prompt
    assert (
        '- "yield_robot": the robot that should yield, or null when the strategy '
        'is not "yield"'
    ) in prompt


def test_build_prompt_payload_think_step_asks_which_robot_should_yield():
    prompt = build_prompt_payload(_request()).user_prompt
    think_block = prompt[prompt.index("<think>") : prompt.index("</think>")]
    assert "which robot should yield" in think_block


def test_build_prompt_payload_omits_yielder_selection_criteria():
    # The prompt must describe how to EXPRESS the yield_robot choice (the
    # field to fill in) but never hint at how to MAKE it - that choice is
    # exactly what downstream experiments measure. Guards against a future
    # edit reintroducing selection criteria (available space, blockers,
    # retreat room, clearance, arrival order) or the removed "first listed
    # robot backs up" list-position convention.
    prompt = build_prompt_payload(_request()).user_prompt.lower()
    for term in ["space", "retreat", "blocker", "clearance", "arrival", "first listed"]:
        assert term not in prompt


def _obstacles() -> list[StaticObstacleInput]:
    return [
        StaticObstacleInput(obstacle_id="box_b", x=1.85, y=0.5, size_x_m=0.4, size_y_m=0.2),
        StaticObstacleInput(obstacle_id="box_a", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3),
    ]


def test_format_static_obstacle_lines_renders_centre_and_extent():
    lines = format_static_obstacle_lines(
        [StaticObstacleInput(obstacle_id="obstacle_1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3)]
    )
    assert lines == ["obstacle_1: centre (-1.85, 0.00) m, extent 0.30 x 0.30 m"]


def test_format_static_obstacle_lines_sorts_several_obstacles_by_id():
    assert format_static_obstacle_lines(_obstacles()) == [
        "box_a: centre (-1.85, 0.00) m, extent 0.30 x 0.30 m",
        "box_b: centre (1.85, 0.50) m, extent 0.40 x 0.20 m",
    ]


def test_format_static_obstacle_lines_is_empty_without_obstacles():
    assert format_static_obstacle_lines([]) == []


def _obstacle_request(include: bool) -> ReasonerRequest:
    return _request().model_copy(
        update={"static_obstacles": _obstacles(), "include_static_obstacles": include}
    )


def test_build_prompt_payload_lists_every_static_obstacle_when_switched_on():
    prompt = build_prompt_payload(_obstacle_request(include=True)).user_prompt
    assert (
        "Static obstacles (world-frame axis-aligned boxes):\n"
        "- box_a: centre (-1.85, 0.00) m, extent 0.30 x 0.30 m\n"
        "- box_b: centre (1.85, 0.50) m, extent 0.40 x 0.20 m\n\n"
        'Known robot IDs: ["robot_1", "robot_2"]'
    ) in prompt


def test_build_prompt_payload_adds_obstacle_clause_when_switched_on():
    prompt = build_prompt_payload(_obstacle_request(include=True)).user_prompt
    assert (
        "Fixed obstacles in the scene are listed above and are the only ones "
        "present; a robot can neither occupy nor drive through one."
    ) in prompt


def test_build_prompt_payload_omits_obstacle_clause_when_switched_on_without_obstacles():
    # The flag and the obstacle list are two separate config edits. With the flag
    # on and the list empty the clause would affirm "the only ones present" over
    # an empty list - a false claim of an empty scene - so it must not render.
    request = _request().model_copy(update={"include_static_obstacles": True})
    prompt = build_prompt_payload(request).user_prompt
    assert "Static obstacles" not in prompt
    assert "Fixed obstacles" not in prompt


def test_build_prompt_payload_omits_obstacle_clause_when_switched_off():
    prompt = build_prompt_payload(_obstacle_request(include=False)).user_prompt
    assert "Static obstacles" not in prompt
    assert "Fixed obstacles" not in prompt
    assert "box_a" not in prompt


def test_build_prompt_payload_obstacle_clause_omits_yielder_selection_criteria():
    # Same guard as the yielder-criteria test above, applied to the obstacle
    # channel: the modality may state scene physics but must never hint at which
    # robot is blocked or should back up. Obstacle IDs here avoid the guarded
    # terms so any hit comes from wording this feature added, not from data.
    prompt = build_prompt_payload(_obstacle_request(include=True)).user_prompt.lower()
    for term in ["space", "retreat", "blocker", "clearance", "arrival", "first listed"]:
        assert term not in prompt
    clause_start = prompt.index("fixed obstacles in the scene")
    clause = prompt[clause_start : prompt.index("\n", clause_start)]
    for term in ["robot_1", "robot_2", "yield", "back up", "west", "east"]:
        assert term not in clause


def _shipped_obstacle_ids() -> list[str]:
    """Obstacle IDs from the commented static_obstacles block of the shipped M5 config."""
    path = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
    return re.findall(r"^#\s+-\s+\{\s*obstacle_id:\s*([^,\s]+)", path.read_text(encoding="utf-8"), re.M)  # noqa: E501


def test_shipped_orchestrator_yaml_obstacle_ids_do_not_leak_into_the_prompt():
    # Configured IDs render verbatim, so the leakage guard has to cover the real
    # config and not only hand-written fixtures: an ID like "blocker_west" would
    # tell the model the box is an obstruction and which side it obstructs.
    ids = _shipped_obstacle_ids()
    assert ids, "the commented static_obstacles block is missing from orchestrator.yaml"
    request = _request().model_copy(
        update={
            "static_obstacles": [
                StaticObstacleInput(obstacle_id=oid, x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3)
                for oid in ids
            ],
            "include_static_obstacles": True,
        }
    )
    prompt = build_prompt_payload(request).user_prompt.lower()
    for term in ["space", "retreat", "blocker", "clearance", "arrival", "first listed"]:
        assert term not in prompt
    for oid in ids:
        assert "west" not in oid and "east" not in oid


# SHA-256 of the rendered user prompt for `_request()` as produced by the prompt
# builder BEFORE the static-obstacle modality existed (rendered from commit
# 056fa22, this feature's parent; the builder last changed at 0efd01e).
# `write_decision_artifact` hashes this same string as `user_sha256`, so every
# decision artifact collected to date is comparable only while the OFF condition
# renders byte-for-byte identically. Any character the template gains in the OFF
# path breaks this hash - that is the point. The constant also pins the shared
# `_request()` fixture: if it fails after that fixture was edited, the fixture
# changed and the pin is still valid - re-point the test at an unmodified
# fixture rather than regenerating the constant.
_PRE_OBSTACLE_OFF_PROMPT_SHA256 = (
    "3b77d224bb1c6de2f73ccd69c08b6ac686ae41dd9dca86442e5f34d278164001"
)


def test_build_prompt_payload_off_prompt_is_byte_identical_to_pre_feature_prompt():
    # Obstacles are supplied and the flag is off: a renderer keyed off list
    # emptiness instead of the flag would fail here, not silently pass.
    prompt = build_prompt_payload(_obstacle_request(include=False)).user_prompt
    # Length first: it names the size of the drift, which the hash alone withholds.
    assert len(prompt) == 3338
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == _PRE_OBSTACLE_OFF_PROMPT_SHA256
    assert prompt == build_prompt_payload(_request()).user_prompt


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


def _ordered_request(order: str) -> ReasonerRequest:
    return _request().model_copy(update={"robot_presentation_order": order})


def test_reasoner_request_robot_presentation_order_defaults_to_id_asc():
    assert _request().robot_presentation_order == "id_asc"


def test_reasoner_request_robot_presentation_order_rejects_unknown_value():
    with pytest.raises(ValidationError):
        ReasonerRequest(**{**_request().model_dump(), "robot_presentation_order": "geometry"})


def test_reasoner_request_robot_presentation_order_round_trips_through_json_dump():
    dumped = _ordered_request("id_desc").model_dump(mode="json")
    assert dumped["robot_presentation_order"] == "id_desc"
    assert ReasonerRequest(**dumped).robot_presentation_order == "id_desc"


def test_build_prompt_payload_default_order_matches_the_pre_feature_prompt():
    # The default path must stay byte-identical, or every artifact collected so
    # far stops being comparable with everything rendered after this feature.
    prompt = build_prompt_payload(_request()).user_prompt
    assert len(prompt) == 3338
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == _PRE_OBSTACLE_OFF_PROMPT_SHA256


def test_build_prompt_payload_reverses_robot_lines_when_order_is_id_desc():
    prompt = build_prompt_payload(_ordered_request("id_desc")).user_prompt
    assert prompt.index("robot_id=robot_2") < prompt.index("robot_id=robot_1")


def test_build_prompt_payload_reverses_known_robot_ids_when_order_is_id_desc():
    payload = build_prompt_payload(_ordered_request("id_desc"))
    assert payload.known_robot_ids == ["robot_2", "robot_1"]
    assert 'Known robot IDs: ["robot_2", "robot_1"]' in payload.user_prompt


def test_build_prompt_payload_swaps_pairwise_roles_when_order_is_id_desc():
    # The pair's first/second roles have to follow the same order as the robot
    # list, or one prompt presents the same pair two different ways.
    prompt = build_prompt_payload(_ordered_request("id_desc")).user_prompt
    assert (
        "- robot_2 <-> robot_1: distance 2.24 m; robot_2 faces robot_1: no; "
        "robot_1 faces robot_2: no\n"
    ) in prompt


def test_build_prompt_payload_id_desc_leaves_the_guidance_text_unchanged():
    # Only the three ordered regions may differ; the task framing, guidance,
    # schema and answer format have to stay word-for-word the same, or the two
    # order conditions would differ in more than the thing under test.
    marker = "\nGuidance:\n"
    ascending = build_prompt_payload(_request()).user_prompt
    descending = build_prompt_payload(_ordered_request("id_desc")).user_prompt
    assert ascending != descending
    assert len(ascending) == len(descending)
    assert ascending[ascending.index(marker) :] == descending[descending.index(marker) :]


def test_format_pairwise_geometry_lines_default_order_is_ascending():
    states = [
        RobotStateInput(robot_id="robot_2", x=1.0, y=0.0, theta=3.14159),
        RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
    ]
    assert format_pairwise_geometry_lines(states)[0].startswith("robot_1 <-> robot_2")


def test_format_pairwise_geometry_lines_id_desc_puts_the_last_id_first():
    states = [
        RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
        RobotStateInput(robot_id="robot_2", x=1.0, y=0.0, theta=3.14159),
    ]
    assert format_pairwise_geometry_lines(states, "id_desc") == [
        "robot_2 <-> robot_1: distance 1.00 m; robot_2 faces robot_1: yes; "
        "robot_1 faces robot_2: yes"
    ]


def test_order_robot_states_leaves_the_input_list_untouched():
    states = [
        RobotStateInput(robot_id="robot_2", x=1.0, y=0.0, theta=0.0),
        RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
    ]
    assert [s.robot_id for s in order_robot_states(states, "id_desc")] == ["robot_2", "robot_1"]
    assert [s.robot_id for s in states] == ["robot_2", "robot_1"]

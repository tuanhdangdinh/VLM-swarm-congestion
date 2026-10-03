"""Prompt-apparatus conditions on prompt v3 (prereg-v2 rev 6 + round-3 deltas, 2026-10-04).

Every condition is an A/B cell, never a default. With all of them off the
six v3 pins in `test_prompt_builder_v3.py` hold untouched; each condition on
gets its own pin here (same `_request` fixture, same conventions). The
sentences are v3-only: the frozen v1/v2 templates never render them, and the
zoom tile is never attached under v1/v2.
"""
import hashlib

import pytest

from reasoning.vlm.models import (
    CandidateOption,
    ReasonerRequest,
    RobotCandidateOptions,
    RobotStateInput,
)
from reasoning.vlm.prompt_builder import (
    _CANDIDATE_OPTIONS_HEADER,
    _METRIC_GRID_SENTENCE,
    _MOTION_TRAILS_SENTENCE,
    _ZOOM_TILE_SENTENCE,
    build_prompt_payload,
    render_candidate_options_block,
)

_GRID_TEXT = _METRIC_GRID_SENTENCE.format(spacing="0.5")
_ALL_SENTENCES = (
    _GRID_TEXT,
    _MOTION_TRAILS_SENTENCE,
    _ZOOM_TILE_SENTENCE,
    _CANDIDATE_OPTIONS_HEADER,
)


def _request(**update: object) -> ReasonerRequest:
    # Identical to test_prompt_builder_v3._request, so the deltas are pure.
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


def _options() -> list[RobotCandidateOptions]:
    return [
        RobotCandidateOptions(
            robot_id="robot_2",
            options=[
                CandidateOption(action="reverse", detail="south arm"),
                CandidateOption(action="wait"),
            ],
        ),
        RobotCandidateOptions(
            robot_id="robot_1",
            options=[CandidateOption(action="yield"), CandidateOption(action="wait")],
        ),
    ]


def _prompt(**update: object) -> str:
    return build_prompt_payload(_request(**update)).user_prompt


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_CONDITIONS: dict[str, dict[str, object]] = {
    "metric_grid": {"metric_grid_spacing_m": 0.5},
    "motion_trails": {"motion_trails_drawn": True},
    "zoom_tile": {"zoom_tile_path": "/tmp/frame_zoom.png"},
    "candidate_options": {"candidate_options": _options()},
    "all_on": {
        "metric_grid_spacing_m": 0.5,
        "motion_trails_drawn": True,
        "zoom_tile_path": "/tmp/frame_zoom.png",
        "candidate_options": _options(),
    },
}

# name -> (length, SHA-256) of the v3.2 user prompt under one condition.
# Pinned 2026-10-04 with the apparatus build, before any live data under any
# condition. Pre-freeze, same exception as the v3 pins: a revision re-pins in
# place; after the prereg-v2 freeze a change here is a new prompt version.
_APPARATUS_PINS: dict[str, tuple[int, str]] = {
    "metric_grid": (
        6287,
        "5e454e849ff85241f1357e63d22d0fdc77a6d2f37c4a0263dabc62f65d466ec5",
    ),
    "motion_trails": (
        6199,
        "e8448cd34241c30dab4facb2bdd50b50dc7566e5aefd2c17647be5bbf5eba01b",
    ),
    "zoom_tile": (
        6248,
        "edadb4292b42f19cd1d898938c02e609330ce520496659d2fd0748ef8762f54d",
    ),
    "candidate_options": (
        6233,
        "bb8c8674f2b1df2a194b74a7640edd11b797acdb9f2d55fbfc952afcf53e9f8b",
    ),
    "all_on": (
        6878,
        "fec35f089741f326767641973137fc7addd787b821973cd0ba52e0b3e23c5f23",
    ),
}


@pytest.mark.parametrize("name", list(_CONDITIONS))
def test_apparatus_condition_matches_its_pin(name: str):
    prompt = _prompt(**_CONDITIONS[name])
    length, digest = _APPARATUS_PINS[name]
    assert len(prompt) == length
    assert _sha256(prompt) == digest


def test_all_off_renders_the_baseline_v3_pin():
    # The `baseline` pin of test_prompt_builder_v3 (v3.2).
    prompt = _prompt()
    assert _sha256(prompt) == "c3fb9fcf4031f3c11961bfe7015887a38901d01049810f289b0c45324c36f873"
    assert not any(sentence in prompt for sentence in _ALL_SENTENCES)


@pytest.mark.parametrize("name", list(_CONDITIONS))
def test_each_condition_only_inserts_text_before_the_plan_invitation(name: str):
    baseline = _prompt()
    on = _prompt(**_CONDITIONS[name])
    anchor = "You may also propose the full multi-robot resolution"
    head, tail = baseline.split(anchor)
    assert on.startswith(head) and on.endswith(anchor + tail)


@pytest.mark.parametrize(
    ("field", "value", "sentence"),
    [
        ("metric_grid_spacing_m", 0.5, _GRID_TEXT),
        ("motion_trails_drawn", True, _MOTION_TRAILS_SENTENCE),
        ("zoom_tile_path", "/tmp/frame_zoom.png", _ZOOM_TILE_SENTENCE),
    ],
)
def test_each_visual_sentence_renders_exactly_once_when_on(field, value, sentence):
    assert _prompt(**{field: value}).count(sentence) == 1


def test_grid_sentence_states_the_registered_spacing_and_example_cell():
    assert "one line every 0.5 m" in _GRID_TEXT
    assert "e.g. C4" in _GRID_TEXT


def test_grid_sentence_states_a_non_default_spacing_verbatim():
    assert "one line every 0.25 m" in _prompt(metric_grid_spacing_m=0.25)


@pytest.mark.parametrize("sentence", _ALL_SENTENCES)
def test_apparatus_text_is_scenario_agnostic(sentence: str):
    lowered = sentence.lower()
    for forbidden in ("robot_", "deadlock", "junction", "yield", "head-on", "aisle"):
        assert forbidden not in lowered


@pytest.mark.parametrize("version", [1, 2])
def test_frozen_templates_never_render_apparatus_text(version: int):
    request = _request(prompt_version=version, **_CONDITIONS["all_on"])
    payload = build_prompt_payload(request)
    assert not any(sentence in payload.user_prompt for sentence in _ALL_SENTENCES)
    assert payload.user_prompt == build_prompt_payload(_request(prompt_version=version)).user_prompt


@pytest.mark.parametrize("version", [1, 2])
def test_frozen_templates_never_attach_the_zoom_tile(version: int):
    payload = build_prompt_payload(
        _request(prompt_version=version, zoom_tile_path="/tmp/frame_zoom.png")
    )
    assert payload.extra_image_paths == []


def test_v3_zoom_tile_is_attached_after_the_frame():
    payload = build_prompt_payload(_request(zoom_tile_path="/tmp/frame_zoom.png"))
    assert payload.image_path == "/tmp/frame.png"
    assert payload.extra_image_paths == ["/tmp/frame_zoom.png"]


def test_all_off_attaches_no_extra_image():
    assert build_prompt_payload(_request()).extra_image_paths == []


def test_options_block_follows_presentation_order():
    asc = _prompt(candidate_options=_options())
    desc = _prompt(candidate_options=_options(), robot_presentation_order="id_desc")
    assert asc.index("- robot_1: yield, wait") < asc.index("- robot_2: reverse (south arm), wait")
    assert desc.index("- robot_2: reverse (south arm), wait") < desc.index("- robot_1: yield, wait")


def test_options_block_renders_a_robot_with_no_accepted_action_as_none():
    block = render_candidate_options_block(
        [RobotCandidateOptions(robot_id="robot_1", options=[])], ["robot_1"]
    )
    assert block.splitlines() == [_CANDIDATE_OPTIONS_HEADER, "- robot_1: none"]


def test_options_block_has_one_framing_sentence_then_one_line_per_robot():
    block = render_candidate_options_block(_options(), ["robot_1", "robot_2"])
    lines = block.splitlines()
    assert lines[0] == _CANDIDATE_OPTIONS_HEADER
    assert lines[1:] == ["- robot_1: yield, wait", "- robot_2: reverse (south arm), wait"]


def test_all_on_orders_the_blocks_grid_trails_tile_then_options():
    prompt = _prompt(**_CONDITIONS["all_on"])
    positions = [prompt.index(s) for s in _ALL_SENTENCES]
    assert positions == sorted(positions)

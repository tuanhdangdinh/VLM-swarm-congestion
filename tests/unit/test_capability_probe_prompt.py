"""Capability-probe prompt v1: SHA pins, frozen from birth.

A change to the raw template or to either rendered fixture is a new
`CAPABILITY_PROBE_PROMPT_VERSION`, never a silent edit (mirrors
`tests/unit/test_stage2_prompt.py`'s pin style for the stage-2 instrument).
"""
import hashlib

from reasoning.vlm.capability_probes.letters import build_item_choices
from reasoning.vlm.capability_probes.prompt import (
    CAPABILITY_PROBE_PROMPT_V1,
    CAPABILITY_PROBE_PROMPT_VERSION,
    CAPABILITY_PROBE_SYSTEM_PROMPT,
    build_capability_probe_prompt_payload,
)

_TEMPLATE_SHA256 = "b1af71e8e4bc4000bf8dc05aab31282517d8ed50b46929fe25d64fa9a69397df"
_SYSTEM_PROMPT_SHA256 = "bdbf03f8f1325e50bdb821bf509d031999dd17430fe3bd9ea422ddc046356d24"
_TEXT_CHOICE_RENDER_SHA256 = "841728fbd4fcd6fd9dc0559c4874a1e318ad01e7a6d6aef44f700380f878548f"
_IMAGE_CHOICE_RENDER_SHA256 = "5c572948f7f4a734f9c62c145f3382a38b6a8afc3495553c1c33d00502f6ec1d"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestVersion:
    def test_version_is_one(self):
        assert CAPABILITY_PROBE_PROMPT_VERSION == 1


class TestRawTemplatePins:
    def test_template_is_pinned(self):
        assert _sha256(CAPABILITY_PROBE_PROMPT_V1) == _TEMPLATE_SHA256

    def test_system_prompt_is_pinned(self):
        assert _sha256(CAPABILITY_PROBE_SYSTEM_PROMPT) == _SYSTEM_PROMPT_SHA256

    def test_system_prompt_is_not_the_stage1_system_prompt(self):
        # Self-contained per its own module docstring: no coupling to the
        # stage-1/stage-2 prompt lineage, so a prompt_builder edit cannot move
        # a single byte of this one.
        from reasoning.vlm.prompt_builder import SYSTEM_PROMPT

        assert CAPABILITY_PROBE_SYSTEM_PROMPT != SYSTEM_PROMPT


class TestRenderedFixturePins:
    def test_text_choice_rendering_is_pinned(self):
        choices = build_item_choices(["left", "right"], "left", item_seed=99)
        payload = build_capability_probe_prompt_payload(
            question="Looking at the image, is robot robot_1 positioned in the left half "
            "or the right half of the frame?",
            choices=choices,
            image_path="/tmp/frame.png",
            image_choices=False,
            known_robot_ids=["robot_1"],
        )
        assert _sha256(payload.user_prompt) == _TEXT_CHOICE_RENDER_SHA256

    def test_image_choice_rendering_is_pinned(self):
        options = [str(i) for i in range(9)]
        choices = build_item_choices(options, "4", item_seed=2026)
        payload = build_capability_probe_prompt_payload(
            question="Which lettered grid cell is robot robot_2 in?",
            choices=choices,
            image_path="/tmp/grid.png",
            image_choices=True,
            known_robot_ids=["robot_2"],
        )
        assert _sha256(payload.user_prompt) == _IMAGE_CHOICE_RENDER_SHA256

    def test_image_choice_rendering_never_mentions_coordinates(self):
        options = [str(i) for i in range(9)]
        choices = build_item_choices(options, "4", item_seed=2026)
        payload = build_capability_probe_prompt_payload(
            question="Which lettered grid cell is robot robot_2 in?",
            choices=choices,
            image_path="/tmp/grid.png",
            image_choices=True,
            known_robot_ids=["robot_2"],
        )
        for leak in ("x=", "y=", "coordinate"):
            assert leak not in payload.user_prompt

    def test_system_prompt_round_trips_unchanged(self):
        choices = build_item_choices(["left", "right"], "left", item_seed=1)
        payload = build_capability_probe_prompt_payload(
            question="q", choices=choices, image_path="/tmp/f.png",
            image_choices=False, known_robot_ids=[],
        )
        assert payload.system_prompt == CAPABILITY_PROBE_SYSTEM_PROMPT

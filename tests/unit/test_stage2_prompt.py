"""Stage-2 retreat-choice prompt, versions 2 (frozen) and 3: SHA pins and content rules.

A change to any pinned rendering is a new `Stage2PromptVersion`, not a re-pin.
Version 1 (text-only letters) never rendered a live call and was retired, not
frozen; its two pins survive below as the unmarked variant of version 2,
which renders it byte for byte. Version 2 is frozen history: the six funded
stage-2 calls of the 2026-09-28 calibration mini-pilot were rendered with it,
so its four pins stay and must keep holding (`prompt_version=2`). Version 3
(amendments item 26) lists the candidates in the request's `listing_order`;
given the letter-order listing it renders v2 byte for byte, so its own pins
use listings that put A elsewhere than first.
"""

import hashlib
import math

import pytest
from pydantic import ValidationError

from reasoning.rag.command_grounder import prepare_retreat_selection
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CURRENT_STAGE2_PROMPT_VERSION,
    RetreatCandidateOption,
    RetreatChoiceRequest,
    RobotStateInput,
    SnapshotFrame,
)
from reasoning.vlm.prompt_builder import SYSTEM_PROMPT
from reasoning.vlm.stage2_prompt import build_stage2_prompt_payload

# Version 2, frozen (the calibration mini-pilot corpus). Marks drawn:
_V2_HEAD_ON_MARKED_SHA256 = "61502f200d767d84b1564114cec24d5f061f79e0d038fd16babaab7f42e09b40"
_V2_THREE_ROBOT_MARKED_SHA256 = "3ff66fe973c7ec32785bfab2fad7dcf8d239bacab6537428e926617f7101ac37"
# Drawing degraded (unmarked frame); equal to the retired v1 pins.
_V2_HEAD_ON_UNMARKED_SHA256 = "4275d2ec3a58bd471614763296fdb6f32741bc8bc8d91e8aba464e32e975d233"
_V2_THREE_ROBOT_UNMARKED_SHA256 = (
    "d91e23c95a53b066a35458fae1661dcb5e0b661d1a9a88d1142b11e4bf4f0529"
)

# Version 3, rendered under these listing orders (A never first).
_HEAD_ON_LISTING = ["B", "A"]
_THREE_ROBOT_LISTING = ["C", "A", "D", "B"]
_V3_HEAD_ON_MARKED_SHA256 = "4655915eeefb8fbbee39d145fe6291d2d26093c8cf80788f2a2ed0db4df6a448"
_V3_THREE_ROBOT_MARKED_SHA256 = "27c1ed70c4381d005060246831ad929e15b92bb262102a3e8bced8cedcfb7423"
_V3_HEAD_ON_UNMARKED_SHA256 = "9c922b609b480348710d88ff7cec190e7ad56572655f07150823537da6430ca7"
_V3_THREE_ROBOT_UNMARKED_SHA256 = (
    "d1899a4e0a0f8b8efc0a4a486cf48e0ae3ce486d7ce8812b146d080573d1232d"
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _geometry() -> SceneGeometry:
    # Mirrors scenario_geometry in swarm_orchestrator/config/orchestrator.yaml.
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x", center_m=0.0, half_length_m=1.0, aisle_half_width_m=0.6, occluder_height_m=0.9
        )
    )


def _head_on_frame() -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id="robot_1", x=-0.3, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_2", x=0.3, y=0.0, theta=math.pi),
        ],
    )


def _request_from_selection(frame, yielder, passers, params, listing, geometry=None, **update):
    if update.get("prompt_version") != 2:
        update.setdefault("listing_order", listing)
    selection = prepare_retreat_selection(frame, yielder, passers, params, geometry=geometry)
    return RetreatChoiceRequest(
        request_id="req-1",
        image_path="/tmp/frame.png",
        yielder_id=yielder,
        crossing_order=list(passers),
        robot_states=list(frame.robots),
        candidates=[
            RetreatCandidateOption(
                label=c.label, x=c.x, y=c.y, backup_m=c.backup_m, lateral_m=c.lateral_m
            )
            for c in selection.candidates
        ],
        **update,
    )


def _head_on_request(**update) -> RetreatChoiceRequest:
    return _request_from_selection(
        _head_on_frame(),
        "robot_1",
        ["robot_2"],
        GroundingParams(mode="derived"),
        _HEAD_ON_LISTING,
        geometry=_geometry(),
        **update,
    )


def _three_robot_request(**update) -> RetreatChoiceRequest:
    frame = SnapshotFrame(
        stamp=2.0,
        robots=[
            RobotStateInput(robot_id="robot_3", x=0.4, y=1.5, theta=-math.pi / 2),
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_2", x=0.4, y=0.0, theta=math.pi),
        ],
    )
    params = GroundingParams(mode="derived", aisle_y_band_m=(-0.8, 0.8))
    return _request_from_selection(
        frame, "robot_1", ["robot_2", "robot_3"], params, _THREE_ROBOT_LISTING, **update
    )


_FIXTURES = {"head_on": _head_on_request, "three_robot": _three_robot_request}
_V2_PINS = {
    ("head_on", True): _V2_HEAD_ON_MARKED_SHA256,
    ("three_robot", True): _V2_THREE_ROBOT_MARKED_SHA256,
    ("head_on", False): _V2_HEAD_ON_UNMARKED_SHA256,
    ("three_robot", False): _V2_THREE_ROBOT_UNMARKED_SHA256,
}
_V3_PINS = {
    ("head_on", True): _V3_HEAD_ON_MARKED_SHA256,
    ("three_robot", True): _V3_THREE_ROBOT_MARKED_SHA256,
    ("head_on", False): _V3_HEAD_ON_UNMARKED_SHA256,
    ("three_robot", False): _V3_THREE_ROBOT_UNMARKED_SHA256,
}


class TestPins:
    def test_version_is_three(self):
        assert CURRENT_STAGE2_PROMPT_VERSION == 3
        assert _head_on_request().prompt_version == 3

    def test_version_one_is_not_renderable(self):
        with pytest.raises(ValidationError):
            _head_on_request(prompt_version=1)

    @pytest.mark.parametrize(("fixture", "marks_drawn"), list(_V3_PINS))
    def test_v3_rendering_is_pinned(self, fixture, marks_drawn):
        payload = build_stage2_prompt_payload(_FIXTURES[fixture](marks_drawn=marks_drawn))
        assert _sha256(payload.user_prompt) == _V3_PINS[fixture, marks_drawn]

    @pytest.mark.parametrize(("fixture", "marks_drawn"), list(_V2_PINS))
    def test_frozen_v2_rendering_is_pinned(self, fixture, marks_drawn):
        request = _FIXTURES[fixture](marks_drawn=marks_drawn, prompt_version=2)
        payload = build_stage2_prompt_payload(request)
        assert _sha256(payload.user_prompt) == _V2_PINS[fixture, marks_drawn]

    @pytest.mark.parametrize(("fixture", "marks_drawn"), list(_V2_PINS))
    def test_v3_with_letter_order_listing_renders_v2_bytes(self, fixture, marks_drawn):
        v2 = _FIXTURES[fixture](marks_drawn=marks_drawn, prompt_version=2)
        letters = sorted(c.label for c in v2.candidates)
        request = _FIXTURES[fixture](marks_drawn=marks_drawn, listing_order=letters)
        assert request.prompt_version == 3
        payload = build_stage2_prompt_payload(request)
        assert _sha256(payload.user_prompt) == _V2_PINS[fixture, marks_drawn]

    def test_v3_pins_differ_from_v2_pins(self):
        assert set(_V3_PINS.values()).isdisjoint(_V2_PINS.values())

    def test_system_prompt_is_the_stage1_system_prompt(self):
        assert build_stage2_prompt_payload(_head_on_request()).system_prompt == SYSTEM_PROMPT


class TestListingOrderValidation:
    def test_v3_requires_a_listing_order(self):
        with pytest.raises(ValidationError, match="requires listing_order"):
            _head_on_request(listing_order=None)

    def test_v2_rejects_a_listing_order(self):
        with pytest.raises(ValidationError, match="letter order"):
            _head_on_request(prompt_version=2, listing_order=["A", "B"])

    @pytest.mark.parametrize("listing", [["A"], ["A", "A"], ["A", "C"], ["A", "B", "C"]])
    def test_listing_order_must_permute_the_letters(self, listing):
        with pytest.raises(ValidationError, match="permutation"):
            _head_on_request(listing_order=listing)


class TestContent:
    def test_image_is_the_request_image(self):
        assert build_stage2_prompt_payload(_head_on_request()).image_path == "/tmp/frame.png"

    def test_marked_request_says_the_letters_are_drawn(self):
        prompt = build_stage2_prompt_payload(_head_on_request(marks_drawn=True)).user_prompt
        assert "Each position is marked on the image by its letter" in prompt
        assert "Choose the marked retreat position" in prompt
        assert "not drawn" not in prompt

    def test_lists_every_candidate_letter_with_coordinates(self):
        prompt = build_stage2_prompt_payload(_head_on_request()).user_prompt
        assert "- A: x=-1.79, y=0.36 (back up 1.49 m, then step 0.36 m aside)" in prompt
        assert "- B: x=-1.79, y=-0.36 (back up 1.49 m, then step 0.36 m aside)" in prompt
        assert '"<one of B, A>"' in prompt

    def test_unmarked_request_says_the_letters_are_not_drawn(self):
        prompt = build_stage2_prompt_payload(_head_on_request()).user_prompt
        assert "The letters are not drawn on the image" in prompt
        assert "marked" not in prompt

    @pytest.mark.parametrize("version", [2, 3])
    def test_candidate_list_order_never_reaches_the_prompt(self, version):
        request = _three_robot_request(prompt_version=version)
        reversed_request = request.model_copy(
            update={"candidates": list(reversed(request.candidates))}
        )
        assert (
            build_stage2_prompt_payload(reversed_request).user_prompt
            == build_stage2_prompt_payload(request).user_prompt
        )

    def test_v3_lists_candidates_and_answer_letters_in_listing_order(self):
        prompt = build_stage2_prompt_payload(_three_robot_request()).user_prompt
        listed = [line[2] for line in prompt.splitlines() if line[:2] == "- " and line[3] == ":"]
        assert listed == _THREE_ROBOT_LISTING
        assert '"<one of C, A, D, B>"' in prompt

    def test_v2_lists_candidates_in_letter_order(self):
        prompt = build_stage2_prompt_payload(
            _three_robot_request(prompt_version=2)
        ).user_prompt
        listed = [line[2] for line in prompt.splitlines() if line[:2] == "- " and line[3] == ":"]
        assert listed == ["A", "B", "C", "D"]
        assert '"<one of A, B, C, D>"' in prompt

    def test_withholds_sweep_clearances(self):
        prompt = build_stage2_prompt_payload(_three_robot_request()).user_prompt
        assert "clearance" not in prompt

    def test_marks_yielder_and_passers(self):
        prompt = build_stage2_prompt_payload(_three_robot_request()).user_prompt
        assert "- robot_1: x=0.00, y=0.00 (yielding)" in prompt
        assert "- robot_2: x=0.40, y=0.00 (passing)" in prompt
        assert "robot_1 will yield so that robot_2, robot_3 can pass" in prompt

    def test_duplicate_labels_rejected(self):
        option = RetreatCandidateOption(label="A", x=0.0, y=0.0, backup_m=1.0, lateral_m=0.3)
        with pytest.raises(ValidationError, match="unique"):
            RetreatChoiceRequest(
                request_id="r",
                image_path="/tmp/f.png",
                yielder_id="robot_1",
                crossing_order=["robot_2"],
                robot_states=[],
                candidates=[option, option],
                listing_order=["A", "A"],
            )

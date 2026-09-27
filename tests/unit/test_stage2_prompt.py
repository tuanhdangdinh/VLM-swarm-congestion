"""Stage-2 retreat-choice prompt, version 1: SHA pins and content rules.

A change to any pinned rendering is a new `Stage2PromptVersion`, not a re-pin.
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

_HEAD_ON_USER_SHA256 = "4275d2ec3a58bd471614763296fdb6f32741bc8bc8d91e8aba464e32e975d233"
_THREE_ROBOT_USER_SHA256 = "d91e23c95a53b066a35458fae1661dcb5e0b661d1a9a88d1142b11e4bf4f0529"


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


def _request_from_selection(frame, yielder, passers, params, geometry=None, **update):
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
        geometry=_geometry(),
        **update,
    )


def _three_robot_request() -> RetreatChoiceRequest:
    frame = SnapshotFrame(
        stamp=2.0,
        robots=[
            RobotStateInput(robot_id="robot_3", x=0.4, y=1.5, theta=-math.pi / 2),
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_2", x=0.4, y=0.0, theta=math.pi),
        ],
    )
    params = GroundingParams(mode="derived", aisle_y_band_m=(-0.8, 0.8))
    return _request_from_selection(frame, "robot_1", ["robot_2", "robot_3"], params)


class TestPins:
    def test_version_starts_at_one(self):
        assert CURRENT_STAGE2_PROMPT_VERSION == 1
        assert _head_on_request().prompt_version == 1

    def test_head_on_rendering_is_pinned(self):
        payload = build_stage2_prompt_payload(_head_on_request())
        assert _sha256(payload.user_prompt) == _HEAD_ON_USER_SHA256

    def test_three_robot_rendering_is_pinned(self):
        payload = build_stage2_prompt_payload(_three_robot_request())
        assert _sha256(payload.user_prompt) == _THREE_ROBOT_USER_SHA256

    def test_system_prompt_is_the_stage1_system_prompt(self):
        assert build_stage2_prompt_payload(_head_on_request()).system_prompt == SYSTEM_PROMPT


class TestContent:
    def test_image_is_the_request_frame_unchanged(self):
        assert build_stage2_prompt_payload(_head_on_request()).image_path == "/tmp/frame.png"

    def test_lists_every_candidate_letter_with_coordinates(self):
        prompt = build_stage2_prompt_payload(_head_on_request()).user_prompt
        assert "- A: x=-1.79, y=0.36 (back up 1.49 m, then step 0.36 m aside)" in prompt
        assert "- B: x=-1.79, y=-0.36 (back up 1.49 m, then step 0.36 m aside)" in prompt
        assert '"<one of A, B>"' in prompt

    def test_says_the_letters_are_not_drawn(self):
        prompt = build_stage2_prompt_payload(_head_on_request()).user_prompt
        assert "The letters are not drawn on the image" in prompt
        assert "marked" not in prompt

    def test_candidates_render_in_letter_order_not_rank_order(self):
        request = _head_on_request()
        reversed_request = request.model_copy(
            update={"candidates": list(reversed(request.candidates))}
        )
        assert (
            build_stage2_prompt_payload(reversed_request).user_prompt
            == build_stage2_prompt_payload(request).user_prompt
        )

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
        with pytest.raises(ValidationError):
            RetreatChoiceRequest(
                request_id="r",
                image_path="/tmp/f.png",
                yielder_id="robot_1",
                crossing_order=["robot_2"],
                robot_states=[],
                candidates=[option, option],
            )

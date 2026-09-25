"""Unit tests for the live-decision replay probe's reconstruction and refusal detection.

The pilot run directories under `data/logs/vm_runs/` are git-ignored, so the
reconstruction fixtures below inline one artifact's `scene`, `failure_context`,
presentation order and run-config flags, together with the `prompt.user_sha256`
that M5 actually recorded. A tiny generated PNG stands in for the frame, which
the prompt text does not depend on.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from reasoning.vlm.models import StaticObstacleInput
from reasoning.vlm.prompt_builder import build_prompt_payload
from scripts.replay_live_decisions import (
    Artifact,
    check_integrity,
    first_yield_artifacts,
    is_refusal,
    reconstruct_request,
    sha256_text,
)

# One artifact from run 20260925_063520 (obstacle west, failure-context block
# present) and one from 20260925_075116 (obstacle east, no block, id_desc).
FC_SCENE = {
    "dropped_frame": False,
    "frame_id": "overhead_camera",
    "robots": [
        {
            "linear_velocity": 2.0940756448662544e-32,
            "robot_id": "robot_1",
            "stamp": 1790318410.8013694,
            "status": "STOPPED",
            "theta": 0.0,
            "x": 2.462459316108063,
            "y": 0.002179132872137446,
        },
        {
            "linear_velocity": 0.016894177705431168,
            "robot_id": "robot_2",
            "stamp": 1790318410.8013694,
            "status": "SLOW",
            "theta": 2.9147972908027473,
            "x": 1.005685818038824,
            "y": -0.12747927302003814,
        },
    ],
    "stamp": 1790318410.8013694,
}
FC_BLOCK = {
    "crossing_order": None,
    "failure_detail": "yield completed 36 s ago; congestion re-detected for the same robots",
    "outcome_status": "completed",
    "strategy": "yield",
    "yield_robot": "robot_2",
}
FC_USER_SHA256 = "2a1281bc3ab54771276376f6bb7f68502757c7a96a26f7d47e47b4b83ce7eb4c"

DESC_SCENE = {
    "dropped_frame": False,
    "frame_id": "overhead_camera",
    "robots": [
        {
            "linear_velocity": 0.002858029699554995,
            "robot_id": "robot_2",
            "stamp": 1790322777.502067,
            "status": "STOPPED",
            "theta": 3.141592653589793,
            "x": 0.17106465160573736,
            "y": 0.004358265744274892,
        },
        {
            "linear_velocity": 0.0034094594787879504,
            "robot_id": "robot_1",
            "stamp": 1790322777.502067,
            "status": "STOPPED",
            "theta": -0.07485866135124043,
            "x": -0.22663342378339668,
            "y": -0.01198523079675573,
        },
    ],
    "stamp": 1790322777.502067,
}
DESC_USER_SHA256 = "9ca16f8a1c870a91a9312f1db853deac190e60a7a57929e13904e910804c2b1a"

SYSTEM_SHA256 = "75357d685f238b6afd7738be9786fdafde641eb6ca9a3be7471939715a68a4de"


def tiny_png(path: Path) -> Path:
    """Write an 8x8 PNG standing in for the real annotated frame."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(path)
    return path


def make_artifact(
    tmp_path: Path,
    *,
    scene: dict,
    failure_context: dict | None,
    order: str,
    user_sha256: str,
    obstacle_x: float,
    run: str = "20260925_063520",
    request_id: str = "4749a31abace4db0b3eca5d5127b73e9",
    live_decision: dict | None = None,
    live_parse_status: str = "valid",
    live_error_message: str | None = None,
    live_raw_text: str | None = None,
    with_image: bool = True,
) -> Artifact:
    """Build an `Artifact` from inlined fixture data plus a generated frame."""
    image_path = tmp_path / f"{request_id}.png"
    if with_image:
        tiny_png(image_path)
    return Artifact(
        run=run,
        request_id=request_id,
        path=tmp_path / f"{request_id}.json",
        image_path=image_path,
        scene=scene,
        failure_context=failure_context,
        stored_order=order,
        stored_user_sha256=user_sha256,
        stored_system_sha256=SYSTEM_SHA256,
        stored_user_prompt="",
        include_pairwise_geometry=True,
        include_static_obstacles=True,
        static_obstacles=(
            StaticObstacleInput(
                obstacle_id="obstacle_1", x=obstacle_x, y=0.0, size_x_m=0.3, size_y_m=0.3
            ),
        ),
        obstacle_x=obstacle_x,
        live_parse_status=live_parse_status,
        live_attempts=1,
        live_error_message=live_error_message,
        live_raw_text=live_raw_text,
        live_decision=live_decision,
        stamp=float(scene["stamp"]),
    )


@pytest.fixture()
def fc_artifact(tmp_path: Path) -> Artifact:
    return make_artifact(
        tmp_path,
        scene=FC_SCENE,
        failure_context=FC_BLOCK,
        order="id_asc",
        user_sha256=FC_USER_SHA256,
        obstacle_x=-1.85,
    )


def test_reconstructed_prompt_sha_matches_live_with_failure_context(fc_artifact):
    rendered = build_prompt_payload(reconstruct_request(fc_artifact)).user_prompt
    assert sha256_text(rendered) == FC_USER_SHA256


def test_reconstructed_prompt_sha_matches_live_under_id_desc(tmp_path):
    artifact = make_artifact(
        tmp_path,
        scene=DESC_SCENE,
        failure_context=None,
        order="id_desc",
        user_sha256=DESC_USER_SHA256,
        obstacle_x=1.85,
        run="20260925_075116",
        request_id="3120c65ffea940b98a22c09a8da76cfe",
    )
    rendered = build_prompt_payload(reconstruct_request(artifact)).user_prompt
    assert sha256_text(rendered) == DESC_USER_SHA256


def test_reconstructed_prompt_sha_differs_when_order_is_flipped(fc_artifact):
    rendered = build_prompt_payload(reconstruct_request(fc_artifact, "id_desc")).user_prompt
    assert sha256_text(rendered) != FC_USER_SHA256


def test_check_integrity_reports_match_when_prompt_and_frame_are_present(fc_artifact):
    result = check_integrity([fc_artifact])
    assert result.matched == [fc_artifact]
    assert result.mismatched == []
    assert result.missing_image == []


def test_check_integrity_reports_mismatch_when_stored_sha_is_wrong(tmp_path):
    artifact = make_artifact(
        tmp_path,
        scene=FC_SCENE,
        failure_context=FC_BLOCK,
        order="id_asc",
        user_sha256="0" * 64,
        obstacle_x=-1.85,
    )
    result = check_integrity([artifact])
    assert result.matched == []
    assert len(result.mismatched) == 1
    assert "line" in result.mismatched[0][1]


def test_check_integrity_excludes_artifact_when_frame_png_is_missing(tmp_path):
    artifact = make_artifact(
        tmp_path,
        scene=FC_SCENE,
        failure_context=FC_BLOCK,
        order="id_asc",
        user_sha256=FC_USER_SHA256,
        obstacle_x=-1.85,
        with_image=False,
    )
    result = check_integrity([artifact])
    assert result.matched == []
    assert result.missing_image == [artifact]


def test_correct_yielder_is_robot_2_when_obstacle_is_west(fc_artifact):
    assert fc_artifact.correct_yielder == "robot_2"


def test_correct_yielder_is_robot_1_when_obstacle_is_east(tmp_path):
    artifact = make_artifact(
        tmp_path,
        scene=DESC_SCENE,
        failure_context=None,
        order="id_desc",
        user_sha256=DESC_USER_SHA256,
        obstacle_x=1.85,
    )
    assert artifact.correct_yielder == "robot_1"


@pytest.mark.parametrize(
    "text",
    [
        "I'm sorry, I can't assist with that.",
        "I'm sorry, but I can't assist with that.",
        "I am sorry, but I cant assist with that request.",
    ],
)
def test_is_refusal_matches_observed_refusal_phrasings(text):
    assert is_refusal(text)


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        json.dumps({"congestion_detected": False}),
        "I'm sorry to report that robot_1 is stalled, but here is the JSON:",
    ],
)
def test_is_refusal_rejects_non_refusal_text(text):
    assert not is_refusal(text)


def test_live_attempt1_refusal_true_when_terminal_refusal_text_stored(tmp_path):
    artifact = make_artifact(
        tmp_path,
        scene=FC_SCENE,
        failure_context=FC_BLOCK,
        order="id_asc",
        user_sha256=FC_USER_SHA256,
        obstacle_x=-1.85,
        live_parse_status="failed",
        live_raw_text="I'm sorry, I can't assist with that.",
        live_error_message="VLM output contains no JSON object.",
    )
    assert artifact.live_attempt1_refusal


def test_live_attempt1_refusal_true_when_reask_recovered_with_no_json_error(tmp_path):
    artifact = make_artifact(
        tmp_path,
        scene=FC_SCENE,
        failure_context=FC_BLOCK,
        order="id_asc",
        user_sha256=FC_USER_SHA256,
        obstacle_x=-1.85,
        live_parse_status="invalid",
        live_raw_text=json.dumps({"congestion_detected": False}),
        live_error_message="VLM output contains no JSON object.",
    )
    assert artifact.live_attempt1_refusal


def test_live_attempt1_refusal_false_for_a_clean_valid_decision(fc_artifact):
    assert not fc_artifact.live_attempt1_refusal


def test_live_attempt1_refusal_false_for_a_schema_failure_not_a_refusal(tmp_path):
    artifact = make_artifact(
        tmp_path,
        scene=FC_SCENE,
        failure_context=FC_BLOCK,
        order="id_asc",
        user_sha256=FC_USER_SHA256,
        obstacle_x=-1.85,
        live_parse_status="invalid",
        live_raw_text=json.dumps({"congestion_detected": False}),
        live_error_message="VLM output failed schema validation: missing 'type'",
    )
    assert not artifact.live_attempt1_refusal


def test_first_yield_artifacts_picks_one_per_run_in_analysis_order(tmp_path):
    def art(run: str, request_id: str, strategy: str) -> Artifact:
        return make_artifact(
            tmp_path,
            scene=FC_SCENE,
            failure_context=None,
            order="id_asc",
            user_sha256=FC_USER_SHA256,
            obstacle_x=-1.85,
            run=run,
            request_id=request_id,
            live_decision={"strategy": strategy, "yield_robot": "robot_1"},
        )

    artifacts = [
        art("run_a", "a1", "none"),
        art("run_a", "a2", "yield"),
        art("run_a", "a3", "yield"),
        art("run_b", "b1", "yield"),
    ]
    assert [a.request_id for a in first_yield_artifacts(artifacts)] == ["a2", "b1"]

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
    Cell,
    _raw_frame_skews,
    build_arm_d_cells,
    build_arm_f_cells,
    build_arm_s_cells,
    check_integrity,
    first_yield_artifacts,
    is_refusal,
    is_standoff,
    make_downscaled_image,
    make_grey_image,
    mcnemar_exact,
    mentions_obstacle,
    reconstruct_request,
    select_standoff_artifacts,
    sha256_text,
    think_block,
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
    with_raw_image: bool = False,
    raw_frame_skew_sec: float | None = None,
) -> Artifact:
    """Build an `Artifact` from inlined fixture data plus a generated frame."""
    image_path = tmp_path / f"{request_id}.png"
    if with_image:
        tiny_png(image_path)
    if with_raw_image:
        tiny_png(tmp_path / f"{request_id}_raw.png")
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
        raw_frame_skew_sec=raw_frame_skew_sec,
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


@pytest.fixture()
def standoff_artifact(tmp_path: Path) -> Artifact:
    """A genuine head-on standoff: both STOPPED, 0.40 m apart, mutually facing."""
    return make_artifact(
        tmp_path,
        scene=DESC_SCENE,
        failure_context=None,
        order="id_desc",
        user_sha256=DESC_USER_SHA256,
        obstacle_x=1.85,
        run="20260925_075116",
        request_id="3120c65f00004db0b3eca5d5127b73e9",
    )


def test_is_standoff_true_for_stopped_facing_pair_within_threshold(standoff_artifact):
    assert is_standoff(standoff_artifact)


def test_is_standoff_false_when_robots_are_far_apart(fc_artifact):
    # The FC fixture's robots sit 1.46 m apart, well beyond the 0.6 m ceiling.
    assert not is_standoff(fc_artifact)


def test_is_standoff_false_when_one_robot_faces_away(tmp_path):
    scene = json.loads(json.dumps(DESC_SCENE))
    scene["robots"][0]["theta"] = 0.0
    artifact = make_artifact(
        tmp_path,
        scene=scene,
        failure_context=None,
        order="id_desc",
        user_sha256=DESC_USER_SHA256,
        obstacle_x=1.85,
    )
    assert not is_standoff(artifact)


def test_is_standoff_false_when_a_robot_is_still_moving(tmp_path):
    scene = json.loads(json.dumps(DESC_SCENE))
    scene["robots"][0]["status"] = "MOVING"
    scene["robots"][0]["linear_velocity"] = 0.25
    artifact = make_artifact(
        tmp_path,
        scene=scene,
        failure_context=None,
        order="id_desc",
        user_sha256=DESC_USER_SHA256,
        obstacle_x=1.85,
    )
    assert not is_standoff(artifact)


def test_is_standoff_true_when_status_is_stale_but_speed_is_negligible(tmp_path):
    scene = json.loads(json.dumps(DESC_SCENE))
    for robot in scene["robots"]:
        robot["status"] = "STALE"
    artifact = make_artifact(
        tmp_path,
        scene=scene,
        failure_context=None,
        order="id_desc",
        user_sha256=DESC_USER_SHA256,
        obstacle_x=1.85,
    )
    assert is_standoff(artifact)


def test_select_standoff_artifacts_drops_non_standoffs(standoff_artifact, fc_artifact):
    selected = select_standoff_artifacts([fc_artifact, standoff_artifact])
    assert [a.request_id for a in selected] == [standoff_artifact.request_id]


def test_select_standoff_artifacts_excludes_failure_context_by_default(tmp_path):
    artifact = make_artifact(
        tmp_path,
        scene=DESC_SCENE,
        failure_context=FC_BLOCK,
        order="id_desc",
        user_sha256=DESC_USER_SHA256,
        obstacle_x=1.85,
    )
    assert select_standoff_artifacts([artifact]) == []
    assert select_standoff_artifacts([artifact], exclude_failure_context=False) == [artifact]


def test_obstacle_side_is_west_for_a_negative_obstacle_x(fc_artifact):
    assert fc_artifact.obstacle_side == "west"


def test_obstacle_side_is_east_for_a_positive_obstacle_x(standoff_artifact):
    assert standoff_artifact.obstacle_side == "east"


def test_make_grey_image_is_uniform_mid_grey_at_the_requested_size(tmp_path):
    path = make_grey_image(tmp_path / "grey.png", (1280, 960))
    with Image.open(path) as image:
        assert image.size == (1280, 960)
        pixels = np.asarray(image.convert("RGB"))
    assert pixels.min() == pixels.max() == 128


def test_make_downscaled_image_keeps_aspect_ratio_at_the_target_width(tmp_path):
    source = tmp_path / "source.png"
    Image.fromarray(np.zeros((960, 1280, 3), dtype=np.uint8)).save(source)
    path = make_downscaled_image(source, tmp_path / "down.png", width=640)
    with Image.open(path) as image:
        assert image.size == (640, 480)


def test_make_downscaled_image_rounds_an_uneven_aspect_ratio(tmp_path):
    source = tmp_path / "source.png"
    Image.fromarray(np.zeros((101, 300, 3), dtype=np.uint8)).save(source)
    path = make_downscaled_image(source, tmp_path / "down.png", width=151)
    with Image.open(path) as image:
        assert image.size == (151, 51)


def test_make_downscaled_image_preserves_visible_structure(tmp_path):
    source = tmp_path / "source.png"
    array = np.zeros((960, 1280, 3), dtype=np.uint8)
    array[:, 640:] = 255
    Image.fromarray(array).save(source)
    path = make_downscaled_image(source, tmp_path / "down.png", width=640)
    with Image.open(path) as image:
        pixels = np.asarray(image.convert("RGB"))
    assert pixels[:, 10].max() == 0
    assert pixels[:, -10].min() == 255


def test_arm_s_cell_keys_encode_the_obstacle_text_factor(standoff_artifact):
    grey = standoff_artifact.image_path
    cells = build_arm_s_cells([standoff_artifact], grey, 1)
    keys = [c.key() for c in cells]
    assert len(keys) == len(set(keys)) == 8
    assert sum(k.endswith("|text_on") for k in keys) == 4
    assert sum(k.endswith("|text_off") for k in keys) == 4


def test_legacy_arm_cell_keys_are_unchanged_by_the_new_factor(standoff_artifact):
    cell = Cell(
        "O", standoff_artifact, "id_asc", "real", standoff_artifact.image_path, "shipped", 0
    )
    assert cell.key() == "|".join(
        ["O", standoff_artifact.run, standoff_artifact.request_id, "id_asc", "real", "shipped", "0"]
    )


def test_arm_s_text_off_cell_drops_the_obstacle_block_from_the_prompt(standoff_artifact):
    on = build_prompt_payload(
        reconstruct_request(standoff_artifact, include_static_obstacles=True)
    ).user_prompt
    off = build_prompt_payload(
        reconstruct_request(standoff_artifact, include_static_obstacles=False)
    ).user_prompt
    assert "obstacle_1: centre (1.85, 0.00) m" in on
    assert "obstacle" not in off.lower()


def test_arm_d_cells_pair_each_artifact_at_both_resolutions(standoff_artifact, tmp_path):
    downscaled = {standoff_artifact.request_id: tmp_path / "down.png"}
    cells = build_arm_d_cells([standoff_artifact], downscaled, 2)
    assert len(cells) == 4
    assert {c.image_label for c in cells} == {"real", "down640"}
    assert len({c.key() for c in cells}) == 4


def test_think_block_extracts_only_the_reasoning_trace():
    assert think_block("<think>\nblocked by a crate\n</think>\n{\"x\": 1}").strip() == (
        "blocked by a crate"
    )


def test_mentions_obstacle_matches_the_blocker_vocabulary():
    assert mentions_obstacle("robot_1 cannot retreat past the barrier")
    assert mentions_obstacle("the box at 1.85 blocks it")
    assert not mentions_obstacle("robot_1 should yield because it is closer to the goal")


def test_arm_s2_cell_keys_are_distinct_from_the_batch_1_arm(standoff_artifact):
    grey = standoff_artifact.image_path
    batch1 = {c.key() for c in build_arm_s_cells([standoff_artifact], grey, 1)}
    batch2 = {c.key() for c in build_arm_s_cells([standoff_artifact], grey, 1, "S2")}
    assert not batch1 & batch2
    assert all(k.startswith("S2|") for k in batch2)


def test_raw_image_path_appends_the_raw_suffix_to_the_request_id(fc_artifact):
    assert fc_artifact.raw_image_path.parent == fc_artifact.image_path.parent
    assert fc_artifact.raw_image_path.name == f"{fc_artifact.request_id}_raw.png"


def test_arm_f_cells_pair_each_artifact_at_both_frames(tmp_path):
    artifact = make_artifact(
        tmp_path,
        scene=FC_SCENE,
        failure_context=FC_BLOCK,
        order="id_asc",
        user_sha256=FC_USER_SHA256,
        obstacle_x=-1.85,
        with_raw_image=True,
    )
    cells = build_arm_f_cells([artifact], 3)
    assert len(cells) == 6
    assert len({c.key() for c in cells}) == 6
    by_label = {c.image_label: c.image_path for c in cells}
    assert by_label["annotated"] == artifact.image_path
    assert by_label["raw"] == artifact.raw_image_path
    assert all(path.is_file() for path in by_label.values())


def test_arm_f_cells_keep_the_stored_order_and_obstacle_text(standoff_artifact):
    cells = build_arm_f_cells([standoff_artifact], 1)
    assert {c.order for c in cells} == {standoff_artifact.stored_order}
    assert all(c.include_static_obstacles for c in cells)
    assert {c.policy for c in cells} == {"shipped"}


def test_raw_frame_substitution_leaves_the_prompt_sha_unchanged(tmp_path):
    artifact = make_artifact(
        tmp_path,
        scene=FC_SCENE,
        failure_context=FC_BLOCK,
        order="id_asc",
        user_sha256=FC_USER_SHA256,
        obstacle_x=-1.85,
        with_raw_image=True,
    )
    raw_request = reconstruct_request(artifact, image_path=artifact.raw_image_path)
    assert raw_request.image_path == str(artifact.raw_image_path)
    assert sha256_text(build_prompt_payload(raw_request).user_prompt) == FC_USER_SHA256


def test_raw_frame_skews_parses_signed_values_from_the_m5_log(tmp_path):
    log = tmp_path / "component_logs" / "m5.log"
    log.parent.mkdir(parents=True)
    log.write_text(
        "[orchestrator_node]: raw frame dumps enabled topic=/camera/image_raw\n"
        "[orchestrator_node]: raw frame skew_sec=-0.355 request=abc123 path=a_raw.png\n"
        "[orchestrator_node]: raw frame skew_sec=+1.328 request=def456 path=b_raw.png\n"
    )
    assert _raw_frame_skews(tmp_path) == {"abc123": -0.355, "def456": 1.328}


def test_raw_frame_skews_is_empty_when_the_run_has_no_m5_log(tmp_path):
    assert _raw_frame_skews(tmp_path) == {}


def test_mcnemar_exact_is_one_when_discordance_is_symmetric():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(4, 4) == 1.0


def test_mcnemar_exact_is_small_when_every_discordant_pair_agrees():
    assert mcnemar_exact(10, 0) == pytest.approx(2 / 2**10)

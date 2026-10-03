"""Replay integrity under the prompt apparatus: `prompt_conditions` rebuilds the prompt.

The integrity arm re-renders a stored decision's prompt from artifact fields
and re-asserts its SHA-256; an apparatus-on artifact must reconstruct
byte-identically from its `prompt_conditions` block, and an artifact without
the block (every one written before it existed) must reconstruct as all-off.
"""
from __future__ import annotations

import dataclasses

from swarm_orchestrator.models import AnnotationOverlayReport
from swarm_orchestrator.reasoning_pipeline import build_prompt_conditions
from swarm_orchestrator.zoom_tile import ZoomTileRecord

from reasoning.vlm.models import CandidateOption, RobotCandidateOptions
from reasoning.vlm.prompt_builder import build_prompt_payload
from scripts.replay_live_decisions import reconstruct_request
from tests.unit.test_replay_live_decisions import fc_artifact  # noqa: F401  (fixture)


def _apparatus_request(artifact):
    base = reconstruct_request(dataclasses.replace(artifact, prompt_version=3))
    tile = str(artifact.image_path.with_name(f"{artifact.request_id}_zoom.png"))
    return base.model_copy(
        update={
            "metric_grid_spacing_m": 0.5,
            "motion_trails_drawn": True,
            "zoom_tile_path": tile,
            "candidate_options": [
                RobotCandidateOptions(
                    robot_id=state.robot_id,
                    options=[CandidateOption(action="wait")],
                )
                for state in base.robot_states
            ],
        }
    )


def test_apparatus_artifact_reconstructs_byte_identically(fc_artifact):  # noqa: F811
    live = _apparatus_request(fc_artifact)
    conditions = build_prompt_conditions(
        request=live,
        overlays=AnnotationOverlayReport(
            overlays=("metric_grid", "motion_trails"), metric_grid_spacing_m=0.5
        ),
        prompt_metric_grid=True,
        prompt_motion_trails=True,
        prompt_zoom_tile=True,
        zoom_tile=ZoomTileRecord(attached=True, path=live.zoom_tile_path),
        permutation_votes=1,
        prompt_candidate_options=True,
    ).model_dump(mode="json")
    stored = dataclasses.replace(fc_artifact, prompt_version=3, prompt_conditions=conditions)
    rebuilt = build_prompt_payload(reconstruct_request(stored))
    original = build_prompt_payload(live)
    assert rebuilt.user_prompt == original.user_prompt
    assert rebuilt.extra_image_paths == original.extra_image_paths


def test_artifact_without_conditions_reconstructs_all_off(fc_artifact):  # noqa: F811
    request = reconstruct_request(fc_artifact)
    assert request.metric_grid_spacing_m is None
    assert request.motion_trails_drawn is False
    assert request.zoom_tile_path is None
    assert request.candidate_options is None


def test_drawn_but_unstated_grid_reconstructs_without_the_sentence(fc_artifact):  # noqa: F811
    base = reconstruct_request(dataclasses.replace(fc_artifact, prompt_version=3))
    conditions = build_prompt_conditions(
        request=base,
        overlays=AnnotationOverlayReport(overlays=("metric_grid",), metric_grid_spacing_m=0.5),
        prompt_metric_grid=False,
        prompt_motion_trails=False,
        prompt_zoom_tile=False,
        zoom_tile=None,
        permutation_votes=1,
        prompt_candidate_options=False,
    ).model_dump(mode="json")
    stored = dataclasses.replace(fc_artifact, prompt_version=3, prompt_conditions=conditions)
    assert reconstruct_request(stored).metric_grid_spacing_m is None

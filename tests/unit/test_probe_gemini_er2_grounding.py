"""Unit tests for the pure helpers in scripts/probe_gemini_er2_grounding.py.

Offline only: point denormalization ([y, x] 0-1000 -> pixel (u, v)), error
scoring with its forced one-to-one assignment, the 2x2 condition/state
construction, scene-log lookup, and key redaction. The one test that calls
`main` runs `--dry-run` with `requests.post` patched to fail, so a network
call would turn into a test failure rather than a silent live request.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from reasoning.vlm.prompt_builder import build_prompt_payload, format_pairwise_geometry_lines
from scripts.probe_gemini_er2_grounding import (
    CLEAR_HIT_M,
    RIGHT_ROBOT_M,
    RobotGroundTruth,
    build_cell_request,
    build_text_states,
    classify_point_error,
    denormalize_point,
    mean_scale_m_per_px,
    nearest_scene_row,
    parse_point_items,
    redact_secret,
    score_points,
)
from scripts.probe_gemini_er2_grounding import main as probe_main

_FAKE_KEY = "AQ.FakeKeyValueForTestingOnly123"
_IMAGE_SIZE = (1280, 960)
# The project's real overhead calibration: 0.004358 m/px, y axis flipped.
_HOMOGRAPHY = np.array(
    [
        [0.004358335072757633, 0.0, -2.789334446564885],
        [-0.0, -0.0043582657442748085, 2.091967557251908],
        [0.0, 0.0, 1.0],
    ]
)


def _truth(robot_id: str, pixel: tuple[float, float]) -> RobotGroundTruth:
    world = (
        pixel[0] * _HOMOGRAPHY[0][0] + _HOMOGRAPHY[0][2],
        pixel[1] * _HOMOGRAPHY[1][1] + _HOMOGRAPHY[1][2],
    )
    return RobotGroundTruth(
        robot_id=robot_id, source="aruco", center_pixel=pixel, center_world=world
    )


def test_denormalize_point_swaps_axes_and_scales():
    assert denormalize_point((500.0, 250.0), _IMAGE_SIZE) == (320.0, 480.0)


def test_denormalize_point_maps_origin_to_zero():
    assert denormalize_point((0.0, 0.0), _IMAGE_SIZE) == (0.0, 0.0)


def test_parse_point_items_accepts_fenced_json():
    text = '```json\n[{"point": [480, 620], "label": "robot_1"}]\n```'
    items = parse_point_items(text)
    assert [(item.label, item.point_yx) for item in items] == [("robot_1", (480.0, 620.0))]


def test_parse_point_items_skips_entries_without_two_coordinates():
    text = '[{"point": [1, 2, 3], "label": "a"}, {"point": [10, 20], "label": "b"}]'
    assert [item.label for item in parse_point_items(text)] == ["b"]


def test_parse_point_items_returns_empty_without_json_array():
    assert parse_point_items("I cannot see any robots.") == []


def test_classify_point_error_uses_robot_width_thresholds():
    assert classify_point_error(CLEAR_HIT_M - 0.01) == "clear_hit"
    assert classify_point_error(CLEAR_HIT_M + 0.01) == "right_robot"
    assert classify_point_error(RIGHT_ROBOT_M + 0.01) == "miss"


def test_score_points_matches_points_to_their_own_robots():
    truths = [_truth("robot_1", (400.0, 480.0)), _truth("robot_2", (900.0, 480.0))]
    items = parse_point_items(
        json.dumps(
            [
                {"point": [480.0 / 960 * 1000, 400.0 / 1280 * 1000], "label": "left"},
                {"point": [480.0 / 960 * 1000, 900.0 / 1280 * 1000], "label": "right"},
            ]
        )
    )
    scoring = score_points(items, truths, _IMAGE_SIZE, _HOMOGRAPHY)
    assert [score.robot_id for score in scoring.scores] == ["robot_1", "robot_2"]
    assert all(score.verdict == "clear_hit" for score in scoring.scores)
    assert scoring.total_error_m == pytest.approx(0.0, abs=1e-6)


def test_score_points_forces_one_to_one_so_a_repeated_point_cannot_hit_twice():
    truths = [_truth("robot_1", (611.0, 482.0)), _truth("robot_2", (668.0, 480.0))]
    same = {"point": [482.0 / 960 * 1000, 611.0 / 1280 * 1000], "label": "robot"}
    scoring = score_points(
        parse_point_items(json.dumps([same, same])), truths, _IMAGE_SIZE, _HOMOGRAPHY
    )
    verdicts = sorted(score.verdict for score in scoring.scores)
    assert verdicts == ["clear_hit", "right_robot"]
    assert scoring.returned_separation_m == pytest.approx(0.0, abs=1e-9)


def test_score_points_reports_truth_separation_for_two_robots():
    truths = [_truth("robot_1", (611.0, 482.0)), _truth("robot_2", (668.0, 480.0))]
    scoring = score_points([], truths, _IMAGE_SIZE, _HOMOGRAPHY)
    assert scoring.truth_separation_m == pytest.approx(0.2485, abs=1e-3)
    assert scoring.scores == []


def test_build_text_states_conflict_is_mutually_facing_at_035_m():
    line = format_pairwise_geometry_lines(build_text_states("conflict"))[0]
    assert "distance 0.35 m" in line
    assert "robot_1 faces robot_2: yes" in line
    assert "robot_2 faces robot_1: yes" in line


def test_build_text_states_clear_is_diverging_at_250_m():
    line = format_pairwise_geometry_lines(build_text_states("clear"))[0]
    assert "distance 2.50 m" in line
    assert "robot_1 faces robot_2: no" in line
    assert "robot_2 faces robot_1: no" in line


def test_build_text_states_conflict_reports_both_stopped():
    assert [state.status for state in build_text_states("conflict")] == ["STOPPED", "STOPPED"]


def test_build_cell_request_withholds_derived_geometry_when_disabled():
    request = build_cell_request(
        "B", 1, Path("frame.png"), "clear", include_pairwise_geometry=False
    )
    prompt = build_prompt_payload(request).user_prompt
    assert "Pairwise geometry" not in prompt
    assert "Compute distances and facing from the coordinates." in prompt


def test_build_cell_request_includes_derived_geometry_by_default():
    request = build_cell_request(
        "A", 2, Path("frame.png"), "conflict", include_pairwise_geometry=True
    )
    prompt = build_prompt_payload(request).user_prompt
    assert "Pairwise geometry" in prompt
    assert request.request_id == "er2-grounding-A-geom-2"


def test_redact_secret_scrubs_every_occurrence():
    text = f"HTTP 400 for key={_FAKE_KEY} and again {_FAKE_KEY}"
    scrubbed = redact_secret(text, _FAKE_KEY)
    assert _FAKE_KEY not in scrubbed
    assert scrubbed.count("***REDACTED***") == 2


def test_redact_secret_passes_text_through_without_a_secret():
    assert redact_secret("no secret here", None) == "no secret here"


def test_mean_scale_m_per_px_matches_the_calibration_scale():
    assert mean_scale_m_per_px(_HOMOGRAPHY) == pytest.approx(0.0043583, abs=1e-6)


def test_nearest_scene_row_picks_the_closest_stamp():
    rows = [
        {"scene": {"stamp": 100.0, "robots": [{"robot_id": "robot_1"}]}},
        {"scene": {"stamp": 103.5, "robots": [{"robot_id": "robot_1"}]}},
    ]
    row, delta = nearest_scene_row(rows, 103.0)
    assert row["scene"]["stamp"] == 103.5
    assert delta == pytest.approx(0.5)


def test_nearest_scene_row_raises_without_rows():
    with pytest.raises(ValueError):
        nearest_scene_row([], 1.0)


def test_dry_run_makes_no_network_call_and_needs_no_key(tmp_path, monkeypatch):
    cv2 = pytest.importorskip("cv2")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def _fail(*args, **kwargs):
        raise AssertionError("--dry-run must not perform any HTTP request")

    monkeypatch.setattr("reasoning.vlm.gemini_backend.requests.post", _fail)
    frames = []
    for name in ("conflict.png", "clear.png"):
        path = tmp_path / name
        cv2.imwrite(str(path), np.full((960, 1280, 3), 200, dtype=np.uint8))
        frames.append(path)

    exit_code = probe_main(
        [
            "--dry-run",
            "--frame-conflict",
            str(frames[0]),
            "--frame-clear",
            str(frames[1]),
        ]
    )
    assert exit_code == 0


def test_dry_run_reports_missing_frame_as_exit_one(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    exit_code = probe_main(
        [
            "--dry-run",
            "--frame-conflict",
            str(tmp_path / "missing_a.png"),
            "--frame-clear",
            str(tmp_path / "missing_b.png"),
        ]
    )
    assert exit_code == 1


def test_world_distance_matches_manual_homography_math():
    from scripts.probe_gemini_er2_grounding import world_distance_m

    distance = world_distance_m((0.0, 0.0), (100.0, 0.0), _HOMOGRAPHY)
    assert distance == pytest.approx(100.0 * _HOMOGRAPHY[0][0], abs=1e-9)
    assert math.isclose(distance, 0.4358335072757633, rel_tol=1e-9)

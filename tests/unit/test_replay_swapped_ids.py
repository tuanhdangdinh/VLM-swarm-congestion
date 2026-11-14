"""Unit tests for the head-on swapped-ID replay (offline; the backend is mocked).

The scene fixture is artifact `3120c65f` of run 20260925_075116 (east blocker,
stored order `id_desc`, no failure context), one of the 12 replay stimuli, with
the `prompt.user_sha256` M5 recorded live.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from reasoning.vlm.errors import BackendHTTPError
from reasoning.vlm.models import BackendResponse, ReasonerConfig, StaticObstacleInput
from reasoning.vlm.prompt_builder import build_prompt_payload
from scripts.replay_live_decisions import Artifact, reconstruct_request, sha256_text
from scripts.replay_swapped_ids import (
    ARMS,
    Cell,
    LedgerProxy,
    ProviderStop,
    attempt_cost_usd,
    build_cells,
    correct_physical,
    first_listed_physical,
    label_to_physical,
    outcome_of,
    pilot_failed,
    run_cell,
    swap_scene_labels,
    swapped_artifact,
)

EAST_SCENE = {
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
EAST_USER_SHA256 = "9ca16f8a1c870a91a9312f1db853deac190e60a7a57929e13904e910804c2b1a"


def _artifact(
    tmp_path: Path,
    obstacle_x: float = 1.85,
    request_id: str = "3120c65f" + "0" * 24,
    scene: dict | None = None,
) -> Artifact:
    image = tmp_path / f"{request_id}.png"
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(image)
    return Artifact(
        run="20260925_075116",
        request_id=request_id,
        path=tmp_path / f"{request_id}.json",
        image_path=image,
        scene=scene or EAST_SCENE,
        failure_context=None,
        stored_order="id_desc",
        stored_user_sha256=EAST_USER_SHA256,
        stored_system_sha256="",
        stored_user_prompt="",
        include_pairwise_geometry=True,
        include_static_obstacles=True,
        static_obstacles=(
            StaticObstacleInput(
                obstacle_id="obstacle_1", x=obstacle_x, y=0.0, size_x_m=0.3, size_y_m=0.3
            ),
        ),
        obstacle_x=obstacle_x,
        live_parse_status="valid",
        live_attempts=1,
        live_error_message=None,
        live_raw_text=None,
        live_decision=None,
        stamp=float(EAST_SCENE["stamp"]),
    )


def _render(artifact: Artifact, order: str) -> str:
    return build_prompt_payload(reconstruct_request(artifact, order, None, True)).user_prompt


def _exchange_tokens(text: str) -> str:
    return text.replace("robot_1", "\0").replace("robot_2", "robot_1").replace("\0", "robot_2")


def test_original_prompt_matches_live_sha_at_stored_order(tmp_path):
    assert sha256_text(_render(_artifact(tmp_path), "id_desc")) == EAST_USER_SHA256


@pytest.mark.parametrize(
    ("swapped_order", "original_order"), [("id_asc", "id_desc"), ("id_desc", "id_asc")]
)
def test_swapped_prompt_equals_original_with_labels_exchanged_opposite_order(
    tmp_path, swapped_order, original_order
):
    artifact = _artifact(tmp_path)
    swapped = _render(swapped_artifact(artifact), swapped_order)
    original = _render(artifact, original_order)
    assert swapped == _exchange_tokens(original)


def test_swapped_prompt_sha_differs_from_live(tmp_path):
    swapped = _render(swapped_artifact(_artifact(tmp_path)), "id_desc")
    assert sha256_text(swapped) != EAST_USER_SHA256


def test_swap_changes_only_robot_ids():
    swapped = swap_scene_labels(EAST_SCENE)
    for before, after in zip(EAST_SCENE["robots"], swapped["robots"], strict=True):
        assert {k: v for k, v in before.items() if k != "robot_id"} == {
            k: v for k, v in after.items() if k != "robot_id"
        }
        assert after["robot_id"] != before["robot_id"]
    assert {k: v for k, v in EAST_SCENE.items() if k != "robots"} == {
        k: v for k, v in swapped.items() if k != "robots"
    }


def test_swap_does_not_mutate_input():
    snapshot = json.dumps(EAST_SCENE, sort_keys=True)
    swap_scene_labels(EAST_SCENE)
    assert json.dumps(EAST_SCENE, sort_keys=True) == snapshot


def test_swap_rejects_artifact_with_failure_context(tmp_path):
    import dataclasses

    artifact = dataclasses.replace(_artifact(tmp_path), failure_context={"yield_robot": "robot_1"})
    with pytest.raises(ValueError):
        swapped_artifact(artifact)


def test_obstacle_block_unchanged_by_swap(tmp_path):
    artifact = _artifact(tmp_path)
    block = lambda text: [line for line in text.splitlines() if "obstacle_1" in line]  # noqa: E731
    assert block(_render(swapped_artifact(artifact), "id_asc")) == block(
        _render(artifact, "id_asc")
    )


def test_label_to_physical_flips_under_arm_b():
    assert label_to_physical("robot_1", "A_real") == "west"
    assert label_to_physical("robot_1", "A_grey") == "west"
    assert label_to_physical("robot_2", "A_grey") == "east"
    assert label_to_physical("robot_1", "B_grey") == "east"
    assert label_to_physical("robot_2", "B_grey") == "west"
    assert label_to_physical(None, "B_grey") is None


def test_correct_physical_is_away_from_blocker():
    assert correct_physical("west") == "east"
    assert correct_physical("east") == "west"


def test_first_listed_physical_matches_rendered_prompt(tmp_path):
    artifact = _artifact(tmp_path)
    west_x = min(r["x"] for r in EAST_SCENE["robots"])
    for arm in ARMS:
        rendered_artifact = swapped_artifact(artifact) if arm == "B_grey" else artifact
        for order in ("id_asc", "id_desc"):
            prompt = _render(rendered_artifact, order)
            first_line = next(
                line for line in prompt.splitlines() if line.startswith("- robot_id=")
            )
            first_is_west = f"x={west_x:.2f}" in first_line
            assert first_listed_physical(order, arm) == ("west" if first_is_west else "east")


def test_scored_physical_choice_matches_scene_coordinates(tmp_path):
    """A yield naming the label on the west robot scores west, in both arms."""
    artifact = _artifact(tmp_path)
    for arm in ARMS:
        rendered = swapped_artifact(artifact) if arm == "B_grey" else artifact
        west_label = min(rendered.scene["robots"], key=lambda r: r["x"])["robot_id"]
        assert label_to_physical(west_label, arm) == "west"


def test_outcome_scores_correct_label_under_swap():
    # East blocker: the west robot must yield; in Arm B it is labelled robot_2.
    assert outcome_of({"yield_robot": "robot_2"}, False, None, "west", "B_grey") == "correct"
    assert outcome_of({"yield_robot": "robot_1"}, False, None, "west", "B_grey") == "wrong"
    assert outcome_of({"yield_robot": "robot_1"}, False, None, "west", "A_grey") == "correct"


def test_outcome_counts_non_yield_and_failures():
    assert outcome_of({"yield_robot": None}, False, None, "west", "A_grey") == "no_yielder"
    assert outcome_of(None, True, None, "west", "A_grey") == "refusal"
    assert outcome_of(None, False, "boom", "west", "A_grey") == "error"
    assert outcome_of(None, False, None, "west", "A_grey") == "parse_failure"


def test_build_cells_counts_and_pilots_first(tmp_path):
    stimuli = [
        _artifact(tmp_path, request_id=f"{p}{'0' * 24}")
        for p in (
            "53264de9",
            "5e7b5a59",
            "2c3fbfa5",
            "61119197",
            "d053d0dc",
            "3120c65f",
            "810c9104",
            "42fb0cb8",
            "d4b96fbd",
            "189ae2a6",
            "e4b1bd03",
            "618a9f29",
        )
    ]
    cells = build_cells("gemini", stimuli, tmp_path / "grey.png")
    assert len(cells) == 144
    assert len({c.key() for c in cells}) == 144
    assert [c.pilot for c in cells[:12]] == [True] * 12
    assert not any(c.pilot for c in cells[12:])
    assert all(c.image_path.name == "grey.png" for c in cells if c.arm != "A_real")


def test_attempt_cost_counts_gemini_thought_tokens():
    usage = {"prompt_tokens": 1000, "completion_tokens": 100, "thought_tokens": 400}
    assert attempt_cost_usd("gemini", usage) == pytest.approx(1000e-6 + 500 * 5e-6)
    assert attempt_cost_usd("anthropic", {"input_tokens": 1000, "output_tokens": 100}) == (
        pytest.approx(1000 * 2e-6 + 100 * 10e-6)
    )
    assert attempt_cost_usd("openai", None) is None


def test_pilot_rule_stops_arm_on_three_failures():
    rows = [
        {
            "backend_id": "anthropic",
            "arm": "A_real",
            "pilot": True,
            "decision": None if i < 3 else {"yield_robot": "robot_1"},
            "image_fallback_used": False,
        }
        for i in range(4)
    ]
    assert pilot_failed(rows, "anthropic", "A_real") is True
    assert pilot_failed(rows[:3], "anthropic", "A_real") is None


class _ScriptedBackend:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def analyze(self, payload, config):
        self.calls += 1
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _decision_text(yield_robot: str) -> str:
    return json.dumps(
        {
            "congestion_detected": True,
            "type": "deadlock",
            "involved_robots": ["robot_1", "robot_2"],
            "root_cause": "standoff",
            "strategy": "yield",
            "justification": "x",
            "yield_robot": yield_robot,
        }
    )


def test_run_cell_with_mock_backend_scores_swapped_row(tmp_path):
    artifact = _artifact(tmp_path)
    grey = tmp_path / "grey.png"
    Image.fromarray(np.full((8, 8, 3), 128, dtype=np.uint8)).save(grey)
    backend = _ScriptedBackend(
        [
            BackendResponse(
                text=_decision_text("robot_2"),
                backend_id="mock",
                token_usage={"prompt_tokens": 10, "completion_tokens": 5},
            ),
        ]
    )
    proxy = LedgerProxy(backend, pace_sec=0.0)
    config = ReasonerConfig(backend_id="openai", temperature=0.0, max_attempts=4)
    row = run_cell(
        Cell("openai", "B_grey", artifact, "id_asc", 1, grey),
        proxy,
        config,
        {"model_id": "mock"},
        "abc1234",
    )
    assert row["outcome"] == "correct"  # east blocker, robot_2 = west robot in Arm B
    assert row["chosen_physical"] == "west"
    assert row["first_listed_physical"] == "east"
    assert row["prompt_matches_live"] is False
    assert row["image_condition"] == "grey"
    assert "base64" not in json.dumps(row)


def test_proxy_stops_provider_on_quota_429(tmp_path):
    artifact = _artifact(tmp_path)
    quota = BackendHTTPError("OpenAI returned HTTP 429: insufficient_quota", status_code=429)
    backend = _ScriptedBackend([quota, quota, quota, quota])
    proxy = LedgerProxy(backend, pace_sec=0.0)
    config = ReasonerConfig(backend_id="openai", temperature=0.0, max_attempts=4)
    row = run_cell(
        Cell("openai", "A_real", artifact, "id_desc", 1, artifact.image_path),
        proxy,
        config,
        {},
        "abc1234",
    )
    assert backend.calls == 1
    assert proxy.provider_stop is not None
    assert row["decision"] is None


def test_proxy_caps_transient_retries_per_run(tmp_path, monkeypatch):
    monkeypatch.setattr("reasoning.vlm.retry_policy._sleep_impl", lambda s: None)
    artifact = _artifact(tmp_path)
    err = BackendHTTPError("HTTP 503", status_code=503)
    backend = _ScriptedBackend([err] * 10)
    proxy = LedgerProxy(backend, pace_sec=0.0)
    config = ReasonerConfig(backend_id="openai", temperature=0.0, max_attempts=4)
    run_cell(
        Cell("openai", "A_real", artifact, "id_desc", 1, artifact.image_path),
        proxy,
        config,
        {},
        "abc1234",
    )
    assert backend.calls == 3  # one call plus at most two transient retries


def test_provider_stop_is_not_retryable():
    assert ProviderStop("x").retryable is False


def test_sonnet_real_frame_arm_stops_on_any_fallback():
    rows = [
        {
            "backend_id": "anthropic",
            "arm": "A_real",
            "pilot": True,
            "decision": {"yield_robot": "robot_1"},
            "image_fallback_used": i == 0,
        }
        for i in range(4)
    ]
    assert pilot_failed(rows, "anthropic", "A_real") is True
    grey = [dict(r, arm="A_grey") for r in rows]
    assert pilot_failed(grey, "anthropic", "A_grey") is False

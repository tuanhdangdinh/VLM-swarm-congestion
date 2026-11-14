"""Unit tests for the head-on JSON-only replay (offline; backends are mocked)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from test_replay_swapped_ids import _artifact, _decision_text

from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig
from reasoning.vlm.prompt_builder import build_prompt_payload
from reasoning.vlm.reasoner import build_reask_prompt
from scripts.replay_json_only import (
    COMPAT_PILOT,
    JSON_ONLY_LINE,
    TIERS,
    PromptConditionProxy,
    build_manifest,
    build_plan,
    cell_stopped,
    compat_gate,
    json_only,
    run_json_only_cell,
    sonnet_stopped,
    tier_fits,
)
from scripts.replay_live_decisions import reconstruct_request
from scripts.replay_swapped_ids import Cell, swapped_artifact

_RUNS_DIR = Path(__file__).resolve().parents[2] / "data/logs/vm_runs"
_MAIN_RUNS_DIR = Path("/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/data/logs/vm_runs")


def _v1(artifact, order="id_asc", text=True) -> str:
    return build_prompt_payload(reconstruct_request(artifact, order, None, text)).user_prompt


def _grey(tmp_path: Path) -> Path:
    grey = tmp_path / "grey.png"
    Image.fromarray(np.full((8, 8, 3), 128, dtype=np.uint8)).save(grey)
    return grey


@pytest.mark.parametrize("text", [True, False])
@pytest.mark.parametrize("order", ["id_asc", "id_desc"])
@pytest.mark.parametrize("swap", [False, True])
def test_json_only_replaces_only_the_answer_format_block(tmp_path, text, order, swap):
    artifact = _artifact(tmp_path)
    artifact = swapped_artifact(artifact) if swap else artifact
    v1 = _v1(artifact, order, text)
    sent = json_only(v1)
    head = v1[: v1.index("Answer using the following format:")]
    assert sent == head + JSON_ONLY_LINE
    assert "<think>" not in sent and "</think>" not in sent
    assert v1.endswith("surrounding text or markdown.")


def test_json_only_keeps_a_reask_suffix(tmp_path):
    payload = PromptPayload(
        system_prompt="s", user_prompt=_v1(_artifact(tmp_path)), image_path="x", known_robot_ids=[]
    )
    reasked = build_reask_prompt(payload, "bad").user_prompt
    suffix = reasked[len(payload.user_prompt) :]
    assert json_only(reasked) == json_only(payload.user_prompt) + suffix


def test_json_only_matches_the_current_builder_ending(tmp_path):
    import dataclasses

    v3 = build_prompt_payload(
        reconstruct_request(dataclasses.replace(_artifact(tmp_path), prompt_version=3), "id_asc")
    ).user_prompt
    sent = json_only(_v1(_artifact(tmp_path)))
    assert v3.endswith("non-empty.\n\n" + JSON_ONLY_LINE)
    assert sent.endswith("non-empty.\n\n" + JSON_ONLY_LINE)


def test_json_only_rejects_a_prompt_without_the_block():
    with pytest.raises(ValueError):
        json_only("no block here")


class _Scripted:
    def __init__(self, responses: list[BackendResponse]) -> None:
        self._responses = responses
        self.payloads: list[PromptPayload] = []
        self.pixels: list[tuple[int, int, int]] = []

    def analyze(self, payload, config):
        self.payloads.append(payload)
        with Image.open(payload.image_path) as image:
            self.pixels.append(image.convert("RGB").getpixel((0, 0)))
        return self._responses[min(len(self.payloads) - 1, len(self._responses) - 1)]


def _good(label: str = "robot_2") -> BackendResponse:
    return BackendResponse(
        text=_decision_text(label), backend_id="m", token_usage={"input_tokens": 10}
    )


def _refusal(category: str | None = "reasoning_extraction") -> BackendResponse:
    return BackendResponse(text="", backend_id="m", refusal=True, refusal_category=category)


def test_every_provider_receives_byte_identical_prompt_and_image(tmp_path):
    artifact = _artifact(tmp_path)
    grey = _grey(tmp_path)
    seen = {}
    for backend_id in ("gemini", "openai", "anthropic"):
        backend = _Scripted([_good()])
        run_json_only_cell(
            Cell(backend_id, "B_grey", artifact, "id_asc", 1, grey),
            PromptConditionProxy(backend, 0.0),
            ReasonerConfig(backend_id=backend_id, max_attempts=4),
            {},
            "abc",
            "tier1",
        )
        p = backend.payloads[0]
        seen[backend_id] = (p.system_prompt, p.user_prompt, Path(p.image_path).read_bytes())
    assert len(set(seen.values())) == 1


def test_proxy_transforms_every_attempt_and_keeps_reask_and_fallback(tmp_path):
    artifact = _artifact(tmp_path)
    backend = _Scripted([_refusal("other"), _refusal("other"), _good()])
    config = ReasonerConfig(backend_id="anthropic", max_attempts=4, image_fallback_after_attempts=2)
    row = run_json_only_cell(
        Cell("anthropic", "A_real", artifact, "id_asc", 1, artifact.image_path),
        PromptConditionProxy(backend, 0.0),
        config,
        {},
        "abc",
        "tier2",
    )
    assert all("<think>" not in p.user_prompt for p in backend.payloads)
    assert "previous response was invalid" in backend.payloads[1].user_prompt
    assert backend.payloads[2].user_prompt == backend.payloads[0].user_prompt
    assert backend.pixels[2] == (128, 128, 128)
    assert [a["reask_suffix"] for a in row["attempts"]] == [False, True, False]
    assert row["attempts"][0]["sent_user_sha256"] == row["prompt_user_sha256"]
    assert row["attempts"][0]["sent_image_sha256"] == row["image_sha256"]


def test_final_refusal_row_is_a_one_call_refusal(tmp_path):
    artifact = _artifact(tmp_path)
    backend = _Scripted([_refusal(), _good()])
    config = ReasonerConfig(
        backend_id="anthropic",
        max_attempts=4,
        image_fallback_after_attempts=2,
        final_refusal_categories=("reasoning_extraction",),
    )
    row = run_json_only_cell(
        Cell("anthropic", "A_grey", artifact, "id_asc", 1, _grey(tmp_path)),
        PromptConditionProxy(backend, 0.0),
        config,
        {},
        "abc",
        "tier1",
    )
    assert row["n_network_calls"] == 1
    assert row["outcome"] == "refusal"
    assert row["final_refusal"] is True
    assert row["image_fallback_used"] is False
    assert "base64" not in json.dumps(row)


def _stimuli(tmp_path: Path):
    west = _artifact(tmp_path, obstacle_x=-1.85, request_id="53264de9" + "0" * 24)
    east = _artifact(tmp_path, obstacle_x=1.85, request_id="61119197" + "0" * 24)
    others = [
        _artifact(tmp_path, obstacle_x=1.85 if i % 2 else -1.85, request_id=f"{i:08x}" + "1" * 24)
        for i in range(10)
    ]
    return [west, east, *others]


def test_plan_has_pilot_first_and_48_runs_per_cell(tmp_path):
    plan = build_plan("openai", _stimuli(tmp_path), _grey(tmp_path))
    assert [name for name, _ in plan] == ["pilot", "tier1", "tier2", "tier3"]
    cells = [c for _, cs in plan for c in cs]
    assert len({c.key() for c in cells}) == len(cells) == 240
    assert Counter(c.arm for c in cells) == {arm: 48 for tier in TIERS for arm in tier}
    for (_name, cs), arms in zip(plan[1:], TIERS, strict=True):
        assert {c.arm for c in cs} == set(arms)


def test_compat_pilot_covers_sides_orders_and_cells(tmp_path):
    (name, pilot), *_ = build_plan("gemini", _stimuli(tmp_path), _grey(tmp_path))
    assert len(pilot) == len(COMPAT_PILOT) == 8
    assert Counter(c.artifact.obstacle_side for c in pilot) == {"west": 4, "east": 4}
    assert Counter(c.order for c in pilot) == {"id_asc": 4, "id_desc": 4}
    assert {c.arm for c in pilot} == {arm for tier in TIERS for arm in tier}


def test_plan_order_is_seeded_and_differs_by_model(tmp_path):
    stimuli, grey = _stimuli(tmp_path), _grey(tmp_path)
    first = [c.key() for c in build_plan("openai", stimuli, grey)[1][1]]
    again = [c.key() for c in build_plan("openai", stimuli, grey)[1][1]]
    other = [c.key().split("|", 1)[1] for c in build_plan("gemini", stimuli, grey)[1][1]]
    assert first == again
    assert [k.split("|", 1)[1] for k in first] != other


def _row(**kw):
    base = {
        "backend_id": "openai",
        "phase": "pilot",
        "arm": "A_grey",
        "decision": {"x": 1},
        "attempt1_answered": True,
        "attempt1_refused": False,
        "image_fallback_used": False,
        "served_model": "m",
        "attempts": [
            {
                "provider_refusal": False,
                "text_refusal": False,
                "error": None,
                "finish_reason": "stop",
            }
        ],
    }
    return {**base, **kw}


def test_compat_gate_passes_eight_clean_runs():
    assert compat_gate([_row()] * 8, "openai")["passed"] is True


def test_compat_gate_allows_one_transport_miss_but_not_a_format_retry():
    error_then_answer = _row(
        attempt1_answered=False,
        attempts=[
            {
                "provider_refusal": False,
                "text_refusal": False,
                "error": "Timeout",
                "finish_reason": None,
            },
            {
                "provider_refusal": False,
                "text_refusal": False,
                "error": None,
                "finish_reason": "stop",
            },
        ],
    )
    assert compat_gate([_row()] * 7 + [error_then_answer], "openai")["passed"] is True
    format_retry = _row(
        attempt1_answered=False,
        attempts=[
            {
                "provider_refusal": False,
                "text_refusal": False,
                "error": None,
                "finish_reason": "stop",
            },
            {
                "provider_refusal": False,
                "text_refusal": False,
                "error": None,
                "finish_reason": "stop",
            },
        ],
    )
    gate = compat_gate([_row()] * 7 + [format_retry], "openai")
    assert gate["format_failures"] == 1 and gate["passed"] is False


def test_compat_gate_fails_on_any_provider_refusal_or_fallback():
    refused = _row(
        attempt1_answered=False,
        attempts=[
            {
                "provider_refusal": True,
                "text_refusal": False,
                "error": None,
                "finish_reason": "refusal",
            },
            {
                "provider_refusal": False,
                "text_refusal": False,
                "error": None,
                "finish_reason": "stop",
            },
        ],
    )
    assert compat_gate([_row()] * 7 + [refused], "openai")["passed"] is False
    assert compat_gate([_row()] * 7 + [_row(image_fallback_used=True)], "openai")["passed"] is False


def test_compat_gate_incomplete_pilot_does_not_pass():
    assert compat_gate([_row()] * 7, "openai")["passed"] is False


def test_cell_rule_stops_on_more_than_four_bad_of_first_eight():
    rows = [_row(decision=None)] * 5 + [_row()] * 3
    assert cell_stopped(rows, "openai", "A_grey") is True
    assert cell_stopped([_row(decision=None)] * 4 + [_row()] * 4, "openai", "A_grey") is False
    assert cell_stopped([_row(decision=None)] * 7, "openai", "A_grey") is False


def test_sonnet_rule_applies_only_to_anthropic():
    rows = [_row(backend_id="anthropic", attempt1_refused=True)] * 5 + [
        _row(backend_id="anthropic")
    ] * 3
    assert sonnet_stopped(rows, "anthropic") is True
    assert sonnet_stopped([{**r, "backend_id": "openai"} for r in rows], "openai") is False


def test_tier_fits_respects_both_caps():
    assert tier_fits(96, 0.0075, 0.11, 1.08, 2.0) is False
    assert tier_fits(96, 0.004, 0.03, 0.5, 2.0) is True
    assert tier_fits(10, 0.001, 0.01, 0.0, 4.999) is False


@pytest.mark.skipif(not _MAIN_RUNS_DIR.is_dir(), reason="stored September run artifacts absent")
def test_manifest_diff_is_block_only_for_all_12_stimuli(tmp_path):
    from scripts.replay_swapped_ids import grey_image_for, load_stimuli

    stimuli = load_stimuli(_MAIN_RUNS_DIR)
    manifest = build_manifest(stimuli, grey_image_for(stimuli, tmp_path))
    assert len(manifest["entries"]) == 12 * 2 * 3
    assert all(e["diff_is_block_only"] for e in manifest["entries"])
    assert len({e["json_only_user_sha256"] for e in manifest["entries"]}) == 72

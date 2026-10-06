"""Reasoning-dose pilot (2026-10-07): the request knobs the higher doses need.

Mocked HTTP only. gpt-5.1 above effort "none" must omit temperature/top_p
(HTTP 400 otherwise); reasoning tokens must reach `token_usage`; ER-2 must
accept the documented `medium` level. Every existing pin keeps its body.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from reasoning.vlm.backend_factory import build_backend
from reasoning.vlm.models import (
    GeminiBackendConfig,
    OpenAIBackendConfig,
    PromptPayload,
    ReasonerConfig,
)


class _FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _payload(tmp_path: Path) -> PromptPayload:
    frame = tmp_path / "frame.png"
    frame.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return PromptPayload(
        system_prompt="sys", user_prompt="usr", image_path=str(frame), known_robot_ids=[]
    )


def _capture(monkeypatch, module: str, payload: dict) -> dict:
    captured: dict = {}

    def fake_post(url, json, headers=None, timeout=None):
        captured["json"] = json
        return _FakeResponse(payload)

    monkeypatch.setattr(f"reasoning.vlm.{module}.requests.post", fake_post)
    return captured


def _openai_ok(usage: dict | None = None) -> dict:
    return {
        "model": "served-x",
        "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
        "usage": usage or {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    }


def _gpt51(**overrides) -> OpenAIBackendConfig:
    return OpenAIBackendConfig(
        model_id="gpt-5.1-2025-11-13",
        reasoning_effort="low",
        max_tokens_param="max_completion_tokens",
        **overrides,
    )


def test_omit_sampling_drops_temperature_and_top_p_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    captured = _capture(monkeypatch, "openai_backend", _openai_ok())
    backend = build_backend("openai", _gpt51(omit_sampling=True))
    backend.analyze(_payload(tmp_path), ReasonerConfig(backend_id="openai_gpt51", temperature=0.0))
    body = captured["json"]
    assert "temperature" not in body and "top_p" not in body
    assert body["reasoning_effort"] == "low"
    assert body["max_completion_tokens"] == 2048


def test_omit_sampling_records_the_dropped_values_per_call(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    _capture(monkeypatch, "openai_backend", _openai_ok())
    backend = build_backend("openai", _gpt51(omit_sampling=True))
    response = backend.analyze(
        _payload(tmp_path), ReasonerConfig(backend_id="openai_gpt51", temperature=0.0)
    )
    # top_k / presence_penalty are never sent by the OpenAI adapter and are
    # recorded as unsent on every call (conformance fix F08).
    assert response.raw["unsupported_sampling"] == {
        "temperature": 0.0,
        "top_p": 0.95,
        "top_k": 20,
        "presence_penalty": 0.0,
    }


def test_omit_sampling_defaults_off_and_keeps_sampling_fields(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    captured = _capture(monkeypatch, "openai_backend", _openai_ok())
    backend = build_backend("openai", _gpt51())
    response = backend.analyze(
        _payload(tmp_path), ReasonerConfig(backend_id="openai_gpt51", temperature=0.0)
    )
    assert captured["json"]["temperature"] == 0.0
    assert captured["json"]["top_p"] == 0.95
    # Only the two fields Chat Completions never carries (conformance F08).
    assert response.raw["unsupported_sampling"] == {"top_k": 20, "presence_penalty": 0.0}


def test_openai_usage_records_reasoning_tokens_when_reported(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    usage = {
        "prompt_tokens": 700,
        "completion_tokens": 90,
        "total_tokens": 790,
        "completion_tokens_details": {"reasoning_tokens": 75},
    }
    _capture(monkeypatch, "openai_backend", _openai_ok(usage))
    backend = build_backend("openai", _gpt51(omit_sampling=True))
    response = backend.analyze(
        _payload(tmp_path), ReasonerConfig(backend_id="openai_gpt51", temperature=0.0)
    )
    assert response.token_usage == {
        "prompt_tokens": 700,
        "completion_tokens": 90,
        "total_tokens": 790,
        "reasoning_tokens": 75,
    }


def test_openai_usage_omits_reasoning_tokens_when_not_reported(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    _capture(monkeypatch, "openai_backend", _openai_ok())
    backend = build_backend("openai", _gpt51())
    response = backend.analyze(
        _payload(tmp_path), ReasonerConfig(backend_id="openai_gpt51", temperature=0.0)
    )
    assert "reasoning_tokens" not in response.token_usage


@pytest.mark.parametrize("level", ["minimal", "low", "medium", "high"])
def test_gemini_accepts_every_documented_er2_thinking_level(monkeypatch, tmp_path, level):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    captured = _capture(
        monkeypatch, "gemini_backend", {"steps": [{"content": [{"type": "text", "text": "{}"}]}]}
    )
    backend = build_backend("gemini", GeminiBackendConfig(thinking_level=level))
    backend.analyze(_payload(tmp_path), ReasonerConfig(backend_id="gemini"))
    assert captured["json"]["generation_config"]["thinking_level"] == level


def test_gemini_rejects_an_undocumented_thinking_level():
    with pytest.raises(ValidationError):
        GeminiBackendConfig(thinking_level="max")

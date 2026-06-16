"""Unit tests for the OpenAI (GPT) VLM backend. No live API calls — requests is mocked."""
from __future__ import annotations

import pytest

from reasoning.vlm.backend_factory import build_backend
from reasoning.vlm.models import OpenAIBackendConfig, PromptPayload, ReasonerConfig
from reasoning.vlm.openai_backend import OpenAIBackend


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


def _payload(tmp_path) -> PromptPayload:
    image = tmp_path / "frame.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return PromptPayload(
        system_prompt="sys",
        user_prompt="describe the scene as json",
        image_path=str(image),
        known_robot_ids=["robot_0"],
    )


def _ok_body(text: str = '{"congestion_detected": false}') -> dict:
    return {
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
    }


def _cfg(**kw) -> ReasonerConfig:
    return ReasonerConfig(backend_id="openai", **kw)


def test_missing_api_key_raises_value_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIBackend(model_id="gpt-4o")


def test_analyze_posts_chat_completions_with_bearer_auth_and_image(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.openai_backend.requests.post", fake_post)
    backend = OpenAIBackend(model_id="gpt-4o", base_url="https://api.openai.com/v1")
    resp = backend.analyze(_payload(tmp_path), _cfg(timeout_sec=12.0))

    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test-123"
    assert captured["timeout"] == 12.0
    assert captured["json"]["model"] == "gpt-4o"
    # message content carries the rendered text plus a data-URL image part
    user = captured["json"]["messages"][1]
    parts = {part["type"] for part in user["content"]}
    assert parts == {"text", "image_url"}
    image_part = next(p for p in user["content"] if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")
    # raw text returned unparsed (parsing stays in output_parser.py)
    assert resp.text == '{"congestion_detected": false}'
    assert resp.backend_id == "gpt-4o"


def test_analyze_omits_unsupported_top_k(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.openai_backend.requests.post", fake_post)
    OpenAIBackend(model_id="gpt-4o").analyze(_payload(tmp_path), _cfg())
    assert "top_k" not in captured["json"]  # OpenAI rejects top_k


def test_token_usage_parsed_from_response(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setattr(
        "reasoning.vlm.openai_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, _ok_body()),
    )
    resp = OpenAIBackend(model_id="gpt-4o").analyze(_payload(tmp_path), _cfg())
    assert resp.token_usage == {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}


def test_http_error_maps_to_connection_error(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    monkeypatch.setattr(
        "reasoning.vlm.openai_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(429, text="rate limited"),
    )
    with pytest.raises(ConnectionError, match="HTTP 429"):
        OpenAIBackend(model_id="gpt-4o").analyze(_payload(tmp_path), _cfg())


def test_timeout_maps_to_connection_error(monkeypatch, tmp_path):
    import requests

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

    def fake_post(url, json, headers, timeout):
        raise requests.exceptions.Timeout("slow")

    monkeypatch.setattr("reasoning.vlm.openai_backend.requests.post", fake_post)
    with pytest.raises(ConnectionError):
        OpenAIBackend(model_id="gpt-4o").analyze(_payload(tmp_path), _cfg())


def test_factory_builds_openai_backend(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    backend = build_backend("openai", OpenAIBackendConfig(model_id="gpt-4o"))
    assert isinstance(backend, OpenAIBackend)


def test_factory_requires_config_for_openai():
    with pytest.raises(ValueError, match="openai backend requires"):
        build_backend("openai", None)

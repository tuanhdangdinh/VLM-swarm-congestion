"""Unit tests for the Anthropic (Claude) VLM backend. No live API calls — requests is mocked."""
from __future__ import annotations

import pytest

from reasoning.vlm.anthropic_backend import AnthropicBackend
from reasoning.vlm.backend_factory import build_backend
from reasoning.vlm.models import AnthropicBackendConfig, PromptPayload, ReasonerConfig


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
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 11, "output_tokens": 7},
    }


def _cfg(**kw) -> ReasonerConfig:
    return ReasonerConfig(backend_id="anthropic", **kw)


def test_missing_api_key_raises_value_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicBackend(model_id="claude-opus-4-8")


def test_analyze_posts_messages_with_api_key_auth_and_image(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.anthropic_backend.requests.post", fake_post)
    backend = AnthropicBackend(
        model_id="claude-opus-4-8", base_url="https://api.anthropic.com/v1"
    )
    resp = backend.analyze(_payload(tmp_path), _cfg(timeout_sec=12.0))

    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "sk-ant-test-123"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["timeout"] == 12.0
    assert captured["json"]["model"] == "claude-opus-4-8"
    # system prompt is a top-level field, not a messages[] entry
    assert captured["json"]["system"] == "sys"
    user = captured["json"]["messages"][0]
    assert user["role"] == "user"
    parts = {part["type"] for part in user["content"]}
    assert parts == {"text", "image"}
    image_part = next(p for p in user["content"] if p["type"] == "image")
    # bare base64 in source.data — no data: URL prefix
    assert image_part["source"]["type"] == "base64"
    assert image_part["source"]["media_type"] == "image/png"
    assert not image_part["source"]["data"].startswith("data:")
    # raw text returned unparsed (parsing stays in output_parser.py)
    assert resp.text == '{"congestion_detected": false}'
    assert resp.backend_id == "claude-opus-4-8"


def test_analyze_omits_sampling_params(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.anthropic_backend.requests.post", fake_post)
    AnthropicBackend(model_id="claude-opus-4-8").analyze(_payload(tmp_path), _cfg())
    # Claude Opus 4.7+ reject temperature/top_p/top_k with HTTP 400.
    for field in ("temperature", "top_p", "top_k"):
        assert field not in captured["json"]


def test_token_usage_parsed_from_response(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    monkeypatch.setattr(
        "reasoning.vlm.anthropic_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, _ok_body()),
    )
    resp = AnthropicBackend(model_id="claude-opus-4-8").analyze(_payload(tmp_path), _cfg())
    assert resp.token_usage == {"input_tokens": 11, "output_tokens": 7}


def test_refusal_with_empty_content_is_a_refusal_response(monkeypatch, tmp_path):
    # Rewritten 2026-10-06 (model-wiring ruling): a refusal used to raise
    # ConnectionError, which the Reasoner treated as a transport failure, so it
    # was never counted as a refusal. It is now a flagged response instead.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    refusal = {"content": [], "stop_reason": "refusal", "usage": {"input_tokens": 5}}
    monkeypatch.setattr(
        "reasoning.vlm.anthropic_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, refusal),
    )
    resp = AnthropicBackend(model_id="claude-opus-4-8").analyze(_payload(tmp_path), _cfg())
    assert resp.refusal is True
    assert resp.text == ""


def test_non_refusal_without_text_is_an_empty_billed_response(monkeypatch, tmp_path):
    # Conformance fix F07 (2026-10-07): a valid 200 with no text block is a
    # parse failure with its usage recorded on every adapter, no longer a
    # transport error with the billed usage lost.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    empty = {"content": [], "stop_reason": "max_tokens", "usage": {"input_tokens": 5}}
    monkeypatch.setattr(
        "reasoning.vlm.anthropic_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, empty),
    )
    resp = AnthropicBackend(model_id="claude-opus-4-8").analyze(_payload(tmp_path), _cfg())
    assert (resp.text, resp.finish_reason, resp.refusal) == ("", "max_tokens", False)
    assert resp.token_usage == {"input_tokens": 5}


def test_http_error_maps_to_connection_error(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    monkeypatch.setattr(
        "reasoning.vlm.anthropic_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(429, text="rate limited"),
    )
    with pytest.raises(ConnectionError, match="HTTP 429"):
        AnthropicBackend(model_id="claude-opus-4-8").analyze(_payload(tmp_path), _cfg())


def test_timeout_maps_to_backend_timeout_error(monkeypatch, tmp_path):
    # Conformance fix F11 (2026-10-07): one timeout label on every adapter.
    import requests

    from reasoning.vlm.errors import BackendTimeoutError

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")

    def fake_post(url, json, headers, timeout):
        raise requests.exceptions.Timeout("slow")

    monkeypatch.setattr("reasoning.vlm.anthropic_backend.requests.post", fake_post)
    with pytest.raises(BackendTimeoutError):
        AnthropicBackend(model_id="claude-opus-4-8").analyze(_payload(tmp_path), _cfg())


def test_factory_builds_anthropic_backend(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    backend = build_backend("anthropic", AnthropicBackendConfig(model_id="claude-opus-4-8"))
    assert isinstance(backend, AnthropicBackend)


def test_factory_requires_config_for_anthropic():
    with pytest.raises(ValueError, match="anthropic backend requires"):
        build_backend("anthropic", None)


def test_served_model_read_from_response(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    body = {**_ok_body(), "model": "claude-opus-4-8"}
    monkeypatch.setattr(
        "reasoning.vlm.anthropic_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, body),
    )
    resp = AnthropicBackend(model_id="claude-opus-4-8").analyze(_payload(tmp_path), _cfg())
    assert resp.served_model == "claude-opus-4-8"


def test_served_model_is_none_when_response_omits_model(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-123")
    monkeypatch.setattr(
        "reasoning.vlm.anthropic_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, _ok_body()),
    )
    resp = AnthropicBackend(model_id="claude-opus-4-8").analyze(_payload(tmp_path), _cfg())
    assert resp.served_model is None

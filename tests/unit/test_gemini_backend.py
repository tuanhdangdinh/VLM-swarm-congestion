"""Unit tests for the Gemini (Robotics-ER 2) VLM backend. No live API calls — requests is mocked."""
from __future__ import annotations

import json
import logging

import pytest

from reasoning.schemas import load_schema
from reasoning.vlm.backend_factory import build_backend
from reasoning.vlm.errors import BackendTimeoutError
from reasoning.vlm.gemini_backend import GeminiBackend
from reasoning.vlm.models import GeminiBackendConfig, PromptPayload, ReasonerConfig


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
        "steps": [
            {"type": "model_output", "content": [{"type": "text", "text": text}]},
        ],
        "usage": {
            "total_input_tokens": 11,
            "total_output_tokens": 7,
            "total_tokens": 18,
        },
    }


def _cfg(**kw) -> ReasonerConfig:
    return ReasonerConfig(backend_id="gemini", **kw)


def test_missing_api_key_raises_value_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiBackend(model_id="gemini-robotics-er-2-preview")


def test_analyze_posts_interactions_with_goog_header_and_image(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.gemini_backend.requests.post", fake_post)
    backend = GeminiBackend(
        model_id="gemini-robotics-er-2-preview",
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )
    resp = backend.analyze(_payload(tmp_path), _cfg(timeout_sec=12.0))

    assert captured["url"].endswith("/interactions")
    assert captured["headers"]["x-goog-api-key"] == "AQ.test-key-123"
    assert captured["timeout"] == 12.0
    # system_instruction is a plain string, not a messages[]/role entry
    assert captured["json"]["system_instruction"] == "sys"
    assert isinstance(captured["json"]["system_instruction"], str)
    parts = captured["json"]["input"]
    assert len(parts) == 2
    assert parts[0] == {"type": "text", "text": "describe the scene as json"}
    assert parts[1]["type"] == "image"
    assert parts[1]["mime_type"] == "image/png"
    assert isinstance(parts[1]["data"], str) and parts[1]["data"]
    assert captured["json"]["generation_config"]["thinking_level"] == "low"
    # raw text returned unparsed (parsing stays in output_parser.py)
    assert resp.text == '{"congestion_detected": false}'
    assert resp.backend_id == "gemini-robotics-er-2-preview"


def test_thinking_level_reflected_in_generation_config(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.gemini_backend.requests.post", fake_post)
    GeminiBackend(thinking_level="high").analyze(_payload(tmp_path), _cfg())
    assert captured["json"]["generation_config"]["thinking_level"] == "high"


def test_api_key_sent_in_header_never_in_body(monkeypatch, tmp_path):
    secret = "AQ.super-secret-key-value"
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.gemini_backend.requests.post", fake_post)
    GeminiBackend().analyze(_payload(tmp_path), _cfg())

    assert captured["headers"]["x-goog-api-key"] == secret
    serialized_body = json.dumps(captured["json"])
    assert secret not in serialized_body


def test_force_schema_true_attaches_response_format(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.gemini_backend.requests.post", fake_post)
    GeminiBackend(force_schema=True).analyze(_payload(tmp_path), _cfg())

    assert captured["json"]["response_format"] == {
        "type": "text",
        "mime_type": "application/json",
        "schema": load_schema("vlm_decision"),
    }


def test_force_schema_false_omits_response_format(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.gemini_backend.requests.post", fake_post)
    GeminiBackend(force_schema=False).analyze(_payload(tmp_path), _cfg())

    assert "response_format" not in captured["json"]


def test_seed_none_omits_generation_config_seed(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.gemini_backend.requests.post", fake_post)
    GeminiBackend(seed=None).analyze(_payload(tmp_path), _cfg())
    assert "seed" not in captured["json"]["generation_config"]


def test_seed_set_sends_generation_config_seed(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    captured: dict = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _FakeResponse(200, _ok_body())

    monkeypatch.setattr("reasoning.vlm.gemini_backend.requests.post", fake_post)
    GeminiBackend(seed=7).analyze(_payload(tmp_path), _cfg())
    assert captured["json"]["generation_config"]["seed"] == 7


def test_response_text_joined_across_steps_skipping_non_text_and_function_call(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    data = {
        "steps": [
            {
                "type": "model_output",
                "content": [
                    {"type": "text", "text": "line1"},
                    {"type": "thought_signature", "value": "opaque"},
                ],
            },
            {
                "type": "function_call",
                "content": [{"type": "function_call", "name": "lookup"}],
            },
            {
                "type": "model_output",
                "content": [{"type": "text", "text": "line2"}],
            },
        ]
    }
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, data),
    )
    resp = GeminiBackend().analyze(_payload(tmp_path), _cfg())
    assert resp.text == "line1\nline2"


def test_empty_response_behaves_like_openai_backend_equivalent(monkeypatch, tmp_path):
    # No "steps" key at all (malformed/empty) -- OpenAIBackend.analyze never raises
    # for missing content, it falls back to an empty string; GeminiBackend mirrors
    # that tolerance instead of raising.
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, {}),
    )
    resp = GeminiBackend().analyze(_payload(tmp_path), _cfg())
    assert resp.text == ""
    assert resp.token_usage is None


def test_token_usage_mapping_omits_absent_thought_tokens(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    body = _ok_body()
    assert "total_thought_tokens" not in body["usage"]
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, body),
    )
    resp = GeminiBackend().analyze(_payload(tmp_path), _cfg())
    assert resp.token_usage == {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}
    assert "thought_tokens" not in resp.token_usage


def test_token_usage_mapping_includes_thought_tokens_when_present(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    body = _ok_body()
    body["usage"]["total_thought_tokens"] = 171
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, body),
    )
    resp = GeminiBackend().analyze(_payload(tmp_path), _cfg())
    assert resp.token_usage == {
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "thought_tokens": 171,
        "total_tokens": 18,
    }


def test_unsupported_sampling_recorded_in_raw(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, _ok_body()),
    )
    resp = GeminiBackend().analyze(
        _payload(tmp_path),
        _cfg(temperature=0.6, top_p=0.95, top_k=20, presence_penalty=0.0),
    )
    assert resp.raw["unsupported_sampling"] == {
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "presence_penalty": 0.0,
    }


def test_unsupported_sampling_warning_emitted_once_across_two_calls(
    monkeypatch, tmp_path, caplog
):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, _ok_body()),
    )
    backend = GeminiBackend()
    with caplog.at_level(logging.WARNING, logger="reasoning.vlm.gemini_backend"):
        backend.analyze(_payload(tmp_path), _cfg())
        backend.analyze(_payload(tmp_path), _cfg())
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1


def test_unsupported_sampling_warning_names_the_dropped_fields(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, _ok_body()),
    )
    with caplog.at_level(logging.WARNING, logger="reasoning.vlm.gemini_backend"):
        GeminiBackend().analyze(_payload(tmp_path), _cfg())
    message = caplog.records[0].getMessage()
    for field in ("temperature", "top_p", "top_k", "presence_penalty"):
        assert field in message


def test_unsupported_sampling_warning_never_logs_the_api_key(monkeypatch, tmp_path, caplog):
    secret = "AQ.super-secret-key-value"
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, _ok_body()),
    )
    with caplog.at_level(logging.WARNING, logger="reasoning.vlm.gemini_backend"):
        GeminiBackend().analyze(_payload(tmp_path), _cfg())
    assert secret not in caplog.text


def test_http_error_maps_to_connection_error(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(429, text="rate limited"),
    )
    with pytest.raises(ConnectionError, match="HTTP 429"):
        GeminiBackend().analyze(_payload(tmp_path), _cfg())


def test_timeout_maps_to_backend_timeout_error(monkeypatch, tmp_path):
    import requests

    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")

    def fake_post(url, json, headers, timeout):
        raise requests.exceptions.Timeout("slow")

    monkeypatch.setattr("reasoning.vlm.gemini_backend.requests.post", fake_post)
    with pytest.raises(BackendTimeoutError):
        GeminiBackend().analyze(_payload(tmp_path), _cfg())


def test_factory_builds_gemini_backend(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    backend = build_backend("gemini", GeminiBackendConfig())
    assert isinstance(backend, GeminiBackend)


def test_factory_builds_gemini_backend_with_default_config(monkeypatch):
    # Mirrors the openai branch: a None backend_config falls back to the
    # backend's own default config rather than raising.
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    backend = build_backend("gemini", None)
    assert isinstance(backend, GeminiBackend)
    assert backend.model_id == "gemini-robotics-er-2-preview"


def test_served_model_read_from_response_when_present(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    body = {**_ok_body(), "model": "gemini-robotics-er-2-preview"}
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, body),
    )
    resp = GeminiBackend().analyze(_payload(tmp_path), _cfg())
    assert resp.served_model == "gemini-robotics-er-2-preview"


def test_served_model_is_none_not_the_request_id_when_response_omits_it(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test-key-123")
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers, timeout: _FakeResponse(200, _ok_body()),
    )
    resp = GeminiBackend().analyze(_payload(tmp_path), _cfg())
    assert resp.served_model is None

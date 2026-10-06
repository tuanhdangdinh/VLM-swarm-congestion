"""Model-wiring ruling (2026-10-06): request-shape pins and config pins for the new arms.

Covers the Anthropic (claude-sonnet-5-5), gpt-5.1 pilot, Qwen3-VL llama_server
and DeepSeek exploratory arms, plus the structured-refusal path through the
shared refusal pipeline. No live calls: `requests.post` is replaced by a fake.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests
import yaml
from PIL import Image

from reasoning.vlm.anthropic_backend import AnthropicBackend
from reasoning.vlm.backend_factory import (
    backend_adapter,
    build_backend,
    describe_effective_sampling,
    load_backend_config,
    resolve_reasoner_config,
)
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.models import (
    AnthropicBackendConfig,
    BackendResponse,
    LlamaServerBackendConfig,
    OpenAIBackendConfig,
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
    RetreatCandidateOption,
    RetreatChoiceRequest,
    RobotStateInput,
)
from reasoning.vlm.reasoner import Reasoner, write_reasoner_log
from reasoning.vlm.retreat_chooser import RetreatChooser

# The gpt-4o pin's request body as the pre-wiring adapter sent it (generated
# from the 41ba9e0 `openai_backend.py` with the shipped `openai` section and
# the fixed payload below). The wiring must not move a single byte of it.
_GPT4O_PIN_BODY = (
    '{"model": "gpt-4o-2024-08-06", "messages": [{"role": "system", "content": "sys"}, '
    '{"role": "user", "content": [{"type": "text", "text": "usr"}, {"type": "image_url", '
    '"image_url": {"url": "data:image/png;base64,iVBORw0KGgpmYWtl", "detail": "high"}}]}], '
    '"temperature": 0.0, "top_p": 0.95, "max_tokens": 2048, "stream": false}'
)

# The pre-wiring sections, verbatim: the wiring is additive only.
_PINNED_SECTIONS = {
    "reasoner": {
        "backend_id": "openai",
        "timeout_sec": 120,
        "max_attempts": 2,
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "presence_penalty": 0.0,
        "max_tokens": 2048,
        "allow_reask": True,
    },
    "llama_server": {
        "base_url": "http://127.0.0.1:8080/v1",
        "model_id": "cosmos-reason2-8b",
        "model_path": "$HOME/models/nvidia.Cosmos-Reason2-8B.f16.gguf.Q6_K.gguf",
        "mmproj_path": "$HOME/models/mmproj-nvidia.Cosmos-Reason2-8B.f16.gguf",
    },
    "openai": {
        "model_id": "gpt-4o-2024-08-06",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "organization": None,
        "reasoner": {"temperature": 0.0, "max_attempts": 4, "image_fallback_after_attempts": 2},
    },
    "gemini": {
        "model_id": "gemini-robotics-er-2-preview",
        "api_key_env": "GEMINI_API_KEY",
        "thinking_level": "low",
        "force_schema": False,
    },
}

_GOOD_DECISION = (
    '{"congestion_detected": true, "type": "deadlock", '
    '"involved_robots": ["robot_1"], "root_cause": "x", '
    '"strategy": "yield", "justification": "y"}'
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict:
        if self._payload is None:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload


def _shipped_vlm() -> dict:
    return yaml.safe_load(Path("config/models.yaml").read_text())["vlm"]


def _fixed_payload(tmp_path: Path, *, tile: bool = False) -> PromptPayload:
    frame = tmp_path / "frame.png"
    frame.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    extra = []
    if tile:
        zoom = tmp_path / "zoom.png"
        zoom.write_bytes(b"\x89PNG\r\n\x1a\ntile")
        extra = [str(zoom)]
    return PromptPayload(
        system_prompt="sys",
        user_prompt="usr",
        image_path=str(frame),
        known_robot_ids=["robot_1"],
        extra_image_paths=extra,
    )


def _capture(monkeypatch, module: str, response: _FakeResponse) -> dict:
    captured: dict = {}

    def fake_post(url, json, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return response

    monkeypatch.setattr(f"reasoning.vlm.{module}.requests.post", fake_post)
    return captured


def _openai_ok() -> _FakeResponse:
    return _FakeResponse(
        200,
        {
            "model": "served-x",
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
        },
    )


def _build_arm(backend_id: str):
    vlm = _shipped_vlm()
    return (
        build_backend(backend_adapter(vlm, backend_id), load_backend_config(vlm, backend_id)),
        resolve_reasoner_config(vlm, backend_id),
    )


# --- config pins ------------------------------------------------------------


def test_existing_pinned_sections_are_unchanged():
    vlm = _shipped_vlm()
    for name, expected in _PINNED_SECTIONS.items():
        assert vlm[name] == expected, name


def test_anthropic_arm_pins_sonnet_5_5_without_sampling_or_thinking():
    config = load_backend_config(_shipped_vlm(), "anthropic")
    assert isinstance(config, AnthropicBackendConfig)
    assert config.model_id == "claude-sonnet-5-5"
    assert config.thinking_type == "between_tools"
    assert config.effort is None


def test_gpt51_arm_resolves_to_the_openai_adapter_with_reasoning_effort_none():
    vlm = _shipped_vlm()
    config = load_backend_config(vlm, "openai_gpt51")
    assert backend_adapter(vlm, "openai_gpt51") == "openai"
    assert isinstance(config, OpenAIBackendConfig)
    assert config.model_id == "gpt-5.1-2025-11-13"
    assert config.reasoning_effort == "none"
    assert config.max_tokens_param == "max_completion_tokens"


def test_gpt51_arm_mirrors_the_gpt4o_reasoner_block():
    config = resolve_reasoner_config(_shipped_vlm(), "openai_gpt51")
    assert (config.temperature, config.max_attempts, config.image_fallback_after_attempts) == (
        0.0,
        4,
        2,
    )
    assert config.backend_id == "openai_gpt51"


def test_anthropic_arm_has_hosted_arm_parity_attempts_and_image_fallback():
    vlm = _shipped_vlm()
    sonnet = resolve_reasoner_config(vlm, "anthropic")
    gpt4o = resolve_reasoner_config(vlm, "openai")
    assert (sonnet.temperature, sonnet.max_attempts, sonnet.image_fallback_after_attempts) == (
        0.0,
        4,
        2,
    )
    assert (sonnet.max_attempts, sonnet.image_fallback_after_attempts) == (
        gpt4o.max_attempts,
        gpt4o.image_fallback_after_attempts,
    )
    assert sonnet.backend_id == "anthropic"


def test_deepseek_arm_has_hosted_arm_parity_attempts_and_image_fallback():
    vlm = _shipped_vlm()
    deepseek = resolve_reasoner_config(vlm, "deepseek")
    gpt4o = resolve_reasoner_config(vlm, "openai")
    assert (
        deepseek.temperature,
        deepseek.max_attempts,
        deepseek.image_fallback_after_attempts,
    ) == (0.0, 4, 2)
    assert (deepseek.max_attempts, deepseek.image_fallback_after_attempts) == (
        gpt4o.max_attempts,
        gpt4o.image_fallback_after_attempts,
    )
    assert deepseek.backend_id == "deepseek"


def test_deepseek_arm_is_not_pinned_to_the_retired_exp_id():
    config = load_backend_config(_shipped_vlm(), "deepseek")
    assert "exp" not in config.model_id


def test_qwen_arm_resolves_to_llama_server_with_vision_and_greedy_sampling():
    vlm = _shipped_vlm()
    config = load_backend_config(vlm, "llama_server_qwen3vl")
    assert backend_adapter(vlm, "llama_server_qwen3vl") == "llama_server"
    assert isinstance(config, LlamaServerBackendConfig)
    assert config.model_id == "qwen3-vl-8b-instruct-q4_k_m"
    assert config.mmproj_path is not None
    assert config.multi_image is True
    assert resolve_reasoner_config(vlm, "llama_server_qwen3vl").temperature == 0.0


def test_deepseek_arm_rides_the_openai_adapter_with_thinking_disabled():
    vlm = _shipped_vlm()
    config = load_backend_config(vlm, "deepseek")
    assert backend_adapter(vlm, "deepseek") == "openai"
    assert config.model_id == "deepseek-flash"
    assert config.base_url == "https://api.deepseek.com"
    assert config.api_key_env == "DEEPSEEK_API_KEY"
    assert config.thinking_type == "disabled"


def test_backend_adapter_rejects_an_unknown_adapter_key():
    with pytest.raises(ValueError, match="unknown adapter"):
        backend_adapter({"x": {"adapter": "nope"}}, "x")


def test_effective_sampling_records_the_gpt51_reasoning_effort():
    vlm = _shipped_vlm()
    effective = describe_effective_sampling(
        resolve_reasoner_config(vlm, "openai_gpt51"), load_backend_config(vlm, "openai_gpt51")
    )
    assert effective.backend_id == "openai_gpt51"
    assert effective.model_id == "gpt-5.1-2025-11-13"
    assert effective.reasoning_effort == "none"
    assert effective.thinking_mode is None


def test_effective_sampling_records_the_anthropic_thinking_mode():
    vlm = _shipped_vlm()
    effective = describe_effective_sampling(
        resolve_reasoner_config(vlm, "anthropic"), load_backend_config(vlm, "anthropic")
    )
    assert effective.thinking_mode == "between_tools"
    assert effective.reasoning_effort is None


def test_effective_sampling_leaves_new_fields_unset_for_the_gpt4o_pin():
    vlm = _shipped_vlm()
    effective = describe_effective_sampling(
        resolve_reasoner_config(vlm, "openai"), load_backend_config(vlm, "openai")
    )
    assert (effective.reasoning_effort, effective.thinking_mode, effective.effort) == (
        None,
        None,
        None,
    )


# --- OpenAI adapter request shapes -----------------------------------------


def test_gpt4o_pin_request_body_is_byte_identical_to_the_pre_wiring_body(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    captured = _capture(monkeypatch, "openai_backend", _openai_ok())
    backend, config = _build_arm("openai")
    backend.analyze(_fixed_payload(tmp_path), config)
    assert json.dumps(captured["json"]) == _GPT4O_PIN_BODY


def test_gpt51_request_carries_reasoning_effort_none_at_temperature_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    captured = _capture(monkeypatch, "openai_backend", _openai_ok())
    backend, config = _build_arm("openai_gpt51")
    backend.analyze(_fixed_payload(tmp_path), config)
    body = captured["json"]
    assert body["model"] == "gpt-5.1-2025-11-13"
    assert body["reasoning_effort"] == "none"
    assert body["temperature"] == 0.0
    assert body["max_completion_tokens"] == 2048
    assert "max_tokens" not in body
    assert "thinking" not in body


def test_deepseek_request_disables_thinking_and_omits_reasoning_effort(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    captured = _capture(monkeypatch, "openai_backend", _openai_ok())
    backend, config = _build_arm("deepseek")
    backend.analyze(_fixed_payload(tmp_path), config)
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["json"]["thinking"] == {"type": "disabled"}
    assert captured["json"]["temperature"] == 0.0
    assert "reasoning_effort" not in captured["json"]


def test_deepseek_images_ride_the_user_message_frame_first(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    captured = _capture(monkeypatch, "openai_backend", _openai_ok())
    backend, config = _build_arm("deepseek")
    backend.analyze(_fixed_payload(tmp_path, tile=True), config)
    system, user = captured["json"]["messages"]
    assert isinstance(system["content"], str)
    urls = [p["image_url"]["url"] for p in user["content"] if p["type"] == "image_url"]
    assert urls == [
        "data:image/png;base64,iVBORw0KGgpmYWtl",
        "data:image/png;base64,iVBORw0KGgp0aWxl",
    ]
    assert all(
        p["image_url"]["detail"] != "low" for p in user["content"] if p["type"] == "image_url"
    )


def test_openai_adapter_maps_a_truncated_body_to_a_transport_error(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    _capture(monkeypatch, "openai_backend", _FakeResponse(200, None))
    backend, config = _build_arm("deepseek")
    with pytest.raises(ConnectionError, match="malformed"):
        backend.analyze(_fixed_payload(tmp_path), config)


def test_openai_adapter_maps_a_silently_closed_connection_to_a_transport_error(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")

    def closed(url, json, headers=None, timeout=None):
        raise requests.exceptions.ConnectionError("Remote end closed connection without response")

    monkeypatch.setattr("reasoning.vlm.openai_backend.requests.post", closed)
    backend, config = _build_arm("deepseek")
    with pytest.raises(ConnectionError, match="connection failed"):
        backend.analyze(_fixed_payload(tmp_path), config)


def test_openai_adapter_sends_a_read_timeout(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    seen: dict = {}

    def fake_post(url, json, headers=None, timeout=None):
        seen["timeout"] = timeout
        return _openai_ok()

    monkeypatch.setattr("reasoning.vlm.openai_backend.requests.post", fake_post)
    backend, config = _build_arm("deepseek")
    backend.analyze(_fixed_payload(tmp_path), config)
    assert seen["timeout"] == config.timeout_sec


# --- Anthropic adapter request shapes ---------------------------------------


def _anthropic_ok(text: str = "{}") -> _FakeResponse:
    return _FakeResponse(
        200,
        {
            "model": "claude-sonnet-5-5",
            "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "stop_details": None,
            "usage": {
                "input_tokens": 1500,
                "output_tokens": 90,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    )


def _anthropic_refusal(category: str | None = "general_harms", text: str | None = None):
    content = [] if text is None else [{"type": "text", "text": text}]
    return _FakeResponse(
        200,
        {
            "model": "claude-sonnet-5-5",
            "content": content,
            "stop_reason": "refusal",
            "stop_details": {"type": "refusal", "category": category, "explanation": "x"},
            "usage": {"input_tokens": 1500, "output_tokens": 0},
        },
    )


def test_sonnet_request_has_no_sampling_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    captured = _capture(monkeypatch, "anthropic_backend", _anthropic_ok())
    backend, config = _build_arm("anthropic")
    backend.analyze(_fixed_payload(tmp_path), config)
    body = captured["json"]
    assert set(body) == {"model", "system", "messages", "max_tokens", "thinking"}
    for key in ("temperature", "top_p", "top_k"):
        assert key not in body


def test_sonnet_request_turns_thinking_off_with_between_tools(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    captured = _capture(monkeypatch, "anthropic_backend", _anthropic_ok())
    backend, config = _build_arm("anthropic")
    backend.analyze(_fixed_payload(tmp_path), config)
    assert captured["json"]["model"] == "claude-sonnet-5-5"
    assert captured["json"]["thinking"] == {"type": "between_tools"}
    assert "output_config" not in captured["json"]


def test_anthropic_effort_is_sent_under_output_config(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    captured = _capture(monkeypatch, "anthropic_backend", _anthropic_ok())
    backend = AnthropicBackend(model_id="claude-sonnet-5-5", effort="low")
    backend.analyze(_fixed_payload(tmp_path), ReasonerConfig(backend_id="anthropic"))
    assert captured["json"]["output_config"] == {"effort": "low"}
    assert "thinking" not in captured["json"]


def test_anthropic_multi_image_puts_frame_then_tile_then_text(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    captured = _capture(monkeypatch, "anthropic_backend", _anthropic_ok())
    backend, config = _build_arm("anthropic")
    backend.analyze(_fixed_payload(tmp_path, tile=True), config)
    content = captured["json"]["messages"][0]["content"]
    assert [part["type"] for part in content] == ["image", "image", "text"]
    assert content[0]["source"]["data"] == "iVBORw0KGgpmYWtl"
    assert content[1]["source"]["data"] == "iVBORw0KGgp0aWxl"


def test_anthropic_records_unsupported_sampling_per_call(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _capture(monkeypatch, "anthropic_backend", _anthropic_ok())
    backend, config = _build_arm("anthropic")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert response.raw["unsupported_sampling"] == {
        "temperature": 0.0,
        "top_p": 0.95,
        "top_k": 20,
        "presence_penalty": 0.0,
    }


def test_anthropic_usage_is_extracted_with_cache_counters(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _capture(monkeypatch, "anthropic_backend", _anthropic_ok())
    backend, config = _build_arm("anthropic")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert response.token_usage == {
        "input_tokens": 1500,
        "output_tokens": 90,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }


def test_anthropic_usage_records_thinking_tokens_when_reported(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    reply = _anthropic_ok()
    reply._payload["usage"]["output_tokens_details"] = {"thinking_tokens": 0}
    _capture(monkeypatch, "anthropic_backend", reply)
    backend, config = _build_arm("anthropic")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert response.token_usage["thinking_tokens"] == 0


def test_anthropic_skips_thinking_blocks_when_reading_text(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _capture(monkeypatch, "anthropic_backend", _anthropic_ok('{"a": 1}'))
    backend, config = _build_arm("anthropic")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert response.text == '{"a": 1}'
    assert response.refusal is False


def test_anthropic_refusal_stop_reason_is_a_refusal_outcome(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _capture(monkeypatch, "anthropic_backend", _anthropic_refusal("cyber"))
    backend, config = _build_arm("anthropic")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert response.refusal is True
    assert response.refusal_category == "cyber"
    assert response.text == ""
    assert response.served_model == "claude-sonnet-5-5"


def test_anthropic_refusal_with_text_is_still_a_refusal(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _capture(monkeypatch, "anthropic_backend", _anthropic_refusal(None, text=_GOOD_DECISION))
    backend, config = _build_arm("anthropic")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert response.refusal is True
    assert response.refusal_category is None


# --- llama_server (Qwen3-VL) multi-image ------------------------------------


def test_llama_server_multi_image_sends_frame_then_tile_then_text(monkeypatch, tmp_path):
    captured = _capture(monkeypatch, "llama_server_backend", _openai_ok())
    backend = LlamaServerBackend(model_id="qwen", mmproj_path="/m.gguf", multi_image=True)
    backend.analyze(_fixed_payload(tmp_path, tile=True), ReasonerConfig(backend_id="x"))
    content = captured["json"]["messages"][1]["content"]
    assert [part["type"] for part in content] == ["image_url", "image_url", "text"]
    assert content[1]["image_url"]["url"] == "data:image/png;base64,iVBORw0KGgp0aWxl"


def test_llama_server_refuses_extra_images_when_multi_image_is_off(tmp_path):
    backend = LlamaServerBackend(model_id="qwen", mmproj_path="/m.gguf")
    with pytest.raises(ValueError, match="does not support extra images"):
        backend.analyze(_fixed_payload(tmp_path, tile=True), ReasonerConfig(backend_id="x"))


def test_llama_server_single_image_body_is_unchanged_by_the_multi_image_flag(
    monkeypatch, tmp_path
):
    bodies = []
    for flag in (False, True):
        captured = _capture(monkeypatch, "llama_server_backend", _openai_ok())
        backend = LlamaServerBackend(model_id="qwen", mmproj_path="/m.gguf", multi_image=flag)
        backend.analyze(_fixed_payload(tmp_path), ReasonerConfig(backend_id="x"))
        bodies.append(json.dumps(captured["json"]))
    assert bodies[0] == bodies[1]


# --- structured refusals through the shared refusal pipeline ----------------


class _Scripted:
    def __init__(self, *responses: BackendResponse) -> None:
        self._responses = list(responses)
        self.payloads: list[PromptPayload] = []

    def analyze(self, payload, config):
        self.payloads.append(payload)
        return self._responses[min(len(self.payloads) - 1, len(self._responses) - 1)]


def _refused(category: str | None = "general_harms") -> BackendResponse:
    return BackendResponse(
        text="", backend_id="claude", refusal=True, refusal_category=category
    )


def _request(tmp_path: Path) -> ReasonerRequest:
    frame = tmp_path / "frame.png"
    Image.new("RGB", (8, 8), (10, 20, 30)).save(frame)
    return ReasonerRequest(
        request_id="req-1",
        image_path=str(frame),
        frame_id="cam",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )


def test_reasoner_counts_a_structured_refusal_as_a_refusal_attempt(tmp_path):
    backend = _Scripted(_refused(), BackendResponse(text=_GOOD_DECISION, backend_id="claude"))
    result = Reasoner(backend, ReasonerConfig(backend_id="anthropic")).run(_request(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.refusal_attempts == 1
    assert result.diagnostics.refusal_category == "general_harms"


def test_reasoner_rejects_a_refusal_even_when_its_text_parses(tmp_path):
    refused_with_text = BackendResponse(
        text=_GOOD_DECISION, backend_id="claude", refusal=True, refusal_category="bio"
    )
    backend = _Scripted(refused_with_text)
    config = ReasonerConfig(backend_id="anthropic", max_attempts=2)
    result = Reasoner(backend, config).run(_request(tmp_path))
    assert result.decision is None
    assert result.diagnostics.refusal_attempts == 2
    assert result.diagnostics.refusal_category == "bio"


def test_structured_refusal_triggers_the_neutral_image_fallback(tmp_path):
    answer = BackendResponse(text=_GOOD_DECISION, backend_id="c")
    backend = _Scripted(_refused(), _refused(), answer)
    config = ReasonerConfig(
        backend_id="anthropic", max_attempts=4, image_fallback_after_attempts=2
    )
    result = Reasoner(backend, config).run(_request(tmp_path))
    assert result.diagnostics.image_fallback_used is True
    assert result.diagnostics.image_fallback_attempt == 3


def test_retreat_chooser_counts_a_structured_refusal(tmp_path):
    request = RetreatChoiceRequest(
        request_id="req-1",
        image_path=str(tmp_path / "frame.png"),
        yielder_id="robot_1",
        crossing_order=["robot_2"],
        robot_states=[
            RobotStateInput(robot_id="robot_1", x=-0.3, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_2", x=0.3, y=0.0, theta=3.14),
        ],
        candidates=[
            RetreatCandidateOption(label="A", x=-1.79, y=0.36, backup_m=1.49, lateral_m=0.36),
            RetreatCandidateOption(label="B", x=-1.79, y=-0.36, backup_m=1.49, lateral_m=-0.36),
        ],
        listing_order=["B", "A"],
    )
    config = ReasonerConfig(backend_id="anthropic", max_attempts=2, timeout_sec=5.0)
    result = RetreatChooser(_Scripted(_refused()), config).choose(request)
    assert result.failure_cause == "refusal"
    assert result.refusal_attempts == 2


# --- refused-attempt usage (roster-validation ruling 3) ---------------------


def _sequenced_post(monkeypatch, module: str, *responses: _FakeResponse) -> list:
    sent: list = []

    def fake_post(url, json, headers=None, timeout=None):
        sent.append(json)
        return responses[min(len(sent) - 1, len(responses) - 1)]

    monkeypatch.setattr(f"reasoning.vlm.{module}.requests.post", fake_post)
    return sent


def _anthropic_billed_refusal(input_tokens: int) -> _FakeResponse:
    reply = _anthropic_refusal("reasoning_extraction")
    reply._payload["usage"] = {"input_tokens": input_tokens, "output_tokens": 0}
    return reply


def _sonnet_reasoner() -> Reasoner:
    backend, config = _build_arm("anthropic")
    return Reasoner(backend, config)


def test_terminal_refusal_records_every_refused_attempts_usage(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    refusals = [_anthropic_billed_refusal(4001 + index) for index in range(4)]
    _sequenced_post(monkeypatch, "anthropic_backend", *refusals)
    result = _sonnet_reasoner().run(_request(tmp_path))
    assert result.decision is None
    assert result.diagnostics.refusal_attempts == 4
    assert result.diagnostics.attempt_token_usage == [
        {"input_tokens": 4001 + index, "output_tokens": 0} for index in range(4)
    ]


def test_terminal_refusal_records_the_final_attempts_usage_as_token_usage(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    refusals = [_anthropic_billed_refusal(4001 + index) for index in range(4)]
    _sequenced_post(monkeypatch, "anthropic_backend", *refusals)
    result = _sonnet_reasoner().run(_request(tmp_path))
    assert result.diagnostics.token_usage == {"input_tokens": 4004, "output_tokens": 0}


def test_answer_after_refusals_keeps_the_refused_attempts_usage(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _sequenced_post(
        monkeypatch,
        "anthropic_backend",
        _anthropic_billed_refusal(4101),
        _anthropic_billed_refusal(4102),
        _anthropic_ok(_GOOD_DECISION),
    )
    result = _sonnet_reasoner().run(_request(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.image_fallback_attempt == 3
    assert [entry["input_tokens"] for entry in result.diagnostics.attempt_token_usage] == [
        4101,
        4102,
        1500,
    ]
    assert result.diagnostics.token_usage["input_tokens"] == 1500


class _DropsThenAnswers:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, payload, config):
        self.calls += 1
        if self.calls == 1:
            raise ConnectionError("connection closed")
        return BackendResponse(
            text=_GOOD_DECISION, backend_id="d", token_usage={"prompt_tokens": 7}
        )


def test_transport_error_attempt_records_no_usage(tmp_path):
    config = ReasonerConfig(backend_id="deepseek", max_attempts=4)
    result = Reasoner(_DropsThenAnswers(), config).run(_request(tmp_path))
    assert result.diagnostics.attempt_token_usage == [None, {"prompt_tokens": 7}]


def test_reasoner_log_records_attempt_usage_when_an_attempt_was_refused(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _sequenced_post(
        monkeypatch,
        "anthropic_backend",
        _anthropic_billed_refusal(4201),
        _anthropic_ok(_GOOD_DECISION),
    )
    request = _request(tmp_path)
    result = _sonnet_reasoner().run(request)
    log = tmp_path / "trace.jsonl"
    write_reasoner_log(log, request, result)
    record = json.loads(log.read_text())
    assert record["attempt_token_usage"][0] == {"input_tokens": 4201, "output_tokens": 0}


def test_reasoner_log_omits_attempt_usage_without_a_refusal(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _sequenced_post(monkeypatch, "anthropic_backend", _anthropic_ok(_GOOD_DECISION))
    request = _request(tmp_path)
    result = _sonnet_reasoner().run(request)
    log = tmp_path / "trace.jsonl"
    write_reasoner_log(log, request, result)
    assert "attempt_token_usage" not in json.loads(log.read_text())

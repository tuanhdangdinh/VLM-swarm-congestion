"""WIRE-NEXT ruling (2026-10-06): config and request-shape pins for the two hypothesis arms.

H1 arm `gemini_flash` (gemini-3.8-flash, same lab as ER-2) and H2 arm
`llama_server_molmo2er` (Molmo2-ER served by vLLM). No live calls:
`requests.post` / `requests.get` are replaced by fakes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from reasoning.vlm.backend_factory import (
    backend_adapter,
    build_backend,
    describe_effective_sampling,
    load_backend_config,
    resolve_reasoner_config,
)
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.models import (
    GeminiBackendConfig,
    LlamaServerBackendConfig,
    PromptPayload,
    ReasonerConfig,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import preflight_backend  # noqa: E402

# Pre-change request bodies (generated at b092f87 from the shipped config and
# the fixed payload below): the system_placement field must not move a byte
# of the existing llama_server arms.
_QWEN_PIN_BODY = (
    '{"model": "qwen3-vl-8b-instruct-q4_k_m", "messages": [{"role": "system", "content": '
    '"sys"}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": '
    '"data:image/png;base64,iVBORw0KGgpmYWtl"}}, {"type": "text", "text": "usr"}]}], '
    '"temperature": 0.0, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0, '
    '"max_tokens": 2048, "stream": false}'
)
_COSMOS_PIN_BODY = (
    '{"model": "cosmos-reason2-8b", "messages": [{"role": "system", "content": "sys"}, '
    '{"role": "user", "content": [{"type": "image_url", "image_url": {"url": '
    '"data:image/png;base64,iVBORw0KGgpmYWtl"}}, {"type": "text", "text": "usr"}]}], '
    '"temperature": 0.6, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0, '
    '"max_tokens": 2048, "stream": false}'
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload


def _shipped_vlm() -> dict:
    return yaml.safe_load((REPO_ROOT / "config" / "models.yaml").read_text())["vlm"]


def _payload(tmp_path: Path, *, tile: bool = False) -> PromptPayload:
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


def _sent(monkeypatch, tmp_path, backend_id: str, reply: dict, *, tile: bool = False) -> dict:
    captured: dict = {}

    def fake_post(url, json, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse(200, reply)

    module = "gemini_backend" if backend_id.startswith("gemini") else "llama_server_backend"
    monkeypatch.setattr(f"reasoning.vlm.{module}.requests.post", fake_post)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    vlm = _shipped_vlm()
    backend = build_backend(backend_adapter(vlm, backend_id), load_backend_config(vlm, backend_id))
    backend.analyze(_payload(tmp_path, tile=tile), resolve_reasoner_config(vlm, backend_id))
    return captured


_GEMINI_REPLY = {
    "model": "gemini-3.8-flash",
    "steps": [{"content": [{"type": "text", "text": "{}"}]}],
}
_CHAT_REPLY = {"model": "molmo2-er", "choices": [{"message": {"content": "{}"}}]}


# --- H1: gemini-3.8-flash ----------------------------------------------------


def test_gemini_flash_arm_rides_the_gemini_adapter_with_the_live_stable_id():
    vlm = _shipped_vlm()
    config = load_backend_config(vlm, "gemini_flash")
    assert backend_adapter(vlm, "gemini_flash") == "gemini"
    assert isinstance(config, GeminiBackendConfig)
    assert config.model_id == "gemini-3.8-flash"
    assert config.api_key_env == "GEMINI_API_KEY"
    assert config.force_schema is False


def test_gemini_flash_thinking_level_matches_the_er2_pin():
    vlm = _shipped_vlm()
    flash = load_backend_config(vlm, "gemini_flash")
    er2 = load_backend_config(vlm, "gemini")
    assert flash.thinking_level == er2.thinking_level == "low"


def test_gemini_flash_has_hosted_arm_parity_attempts_and_image_fallback():
    vlm = _shipped_vlm()
    flash = resolve_reasoner_config(vlm, "gemini_flash")
    gpt4o = resolve_reasoner_config(vlm, "openai")
    assert (flash.temperature, flash.max_attempts, flash.image_fallback_after_attempts) == (
        0.0,
        4,
        2,
    )
    assert (flash.max_attempts, flash.image_fallback_after_attempts) == (
        gpt4o.max_attempts,
        gpt4o.image_fallback_after_attempts,
    )


def test_er2_pin_keeps_its_frozen_two_attempt_no_fallback_config():
    er2 = resolve_reasoner_config(_shipped_vlm(), "gemini")
    assert (er2.max_attempts, er2.image_fallback_after_attempts) == (2, None)


def test_gemini_flash_request_sends_no_sampling_and_thinking_low(monkeypatch, tmp_path):
    body = _sent(monkeypatch, tmp_path, "gemini_flash", _GEMINI_REPLY)["json"]
    assert body["model"] == "gemini-3.8-flash"
    assert body["generation_config"] == {"thinking_level": "low", "max_output_tokens": 2048}
    for key in ("temperature", "top_p", "top_k"):
        assert key not in json.dumps(body)


def test_gemini_flash_request_is_packed_exactly_like_the_er2_pin(monkeypatch, tmp_path):
    flash = _sent(monkeypatch, tmp_path, "gemini_flash", _GEMINI_REPLY)["json"]
    er2 = _sent(monkeypatch, tmp_path, "gemini", _GEMINI_REPLY)["json"]
    assert {**flash, "model": "x"} == {**er2, "model": "x"}


def test_gemini_flash_records_unsupported_sampling_per_call(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        "reasoning.vlm.gemini_backend.requests.post",
        lambda url, json, headers=None, timeout=None: _FakeResponse(200, _GEMINI_REPLY),
    )
    vlm = _shipped_vlm()
    backend = build_backend("gemini", load_backend_config(vlm, "gemini_flash"))
    response = backend.analyze(_payload(tmp_path), resolve_reasoner_config(vlm, "gemini_flash"))
    assert response.raw["unsupported_sampling"]["temperature"] == 0.0
    assert response.served_model == "gemini-3.8-flash"


# --- H2: Molmo2-ER via vLLM --------------------------------------------------


def test_molmo_arm_rides_llama_server_with_user_prefix_and_greedy_sampling():
    vlm = _shipped_vlm()
    config = load_backend_config(vlm, "llama_server_molmo2er")
    assert backend_adapter(vlm, "llama_server_molmo2er") == "llama_server"
    assert isinstance(config, LlamaServerBackendConfig)
    assert config.model_id == "molmo2-er"
    assert config.base_url == "http://127.0.0.1:8090/v1"
    assert config.mmproj_path is not None
    assert config.system_placement == "user_prefix"
    assert resolve_reasoner_config(vlm, "llama_server_molmo2er").temperature == 0.0


def test_molmo_request_has_one_user_turn_with_the_preamble_prefixed(monkeypatch, tmp_path):
    body = _sent(monkeypatch, tmp_path, "llama_server_molmo2er", _CHAT_REPLY)["json"]
    assert [m["role"] for m in body["messages"]] == ["user"]
    content = body["messages"][0]["content"]
    assert [part["type"] for part in content] == ["image_url", "text"]
    assert content[1]["text"] == "sys\n\nusr"
    assert body["model"] == "molmo2-er"
    assert body["temperature"] == 0.0


def test_user_prefix_multi_image_keeps_frame_then_tile_then_text(tmp_path, monkeypatch):
    captured: dict = {}

    def fake_post(url, json, headers=None, timeout=None):
        captured["json"] = json
        return _FakeResponse(200, _CHAT_REPLY)

    monkeypatch.setattr("reasoning.vlm.llama_server_backend.requests.post", fake_post)
    backend = LlamaServerBackend(
        model_id="molmo2-er", mmproj_path="/m", multi_image=True, system_placement="user_prefix"
    )
    backend.analyze(_payload(tmp_path, tile=True), ReasonerConfig(backend_id="x"))
    content = captured["json"]["messages"][0]["content"]
    assert [part["type"] for part in content] == ["image_url", "image_url", "text"]
    assert content[1]["image_url"]["url"] == "data:image/png;base64,iVBORw0KGgp0aWxl"


def test_user_prefix_text_only_server_sends_one_string_user_turn():
    backend = LlamaServerBackend(model_id="m", system_placement="user_prefix")
    messages = backend._build_messages(
        PromptPayload(
            system_prompt="sys", user_prompt="usr", image_path="/f.png", known_robot_ids=[]
        )
    )
    assert messages == [{"role": "user", "content": "sys\n\nusr"}]


def test_llama_server_rejects_an_unknown_system_placement():
    with pytest.raises(ValueError, match="unknown system_placement"):
        LlamaServerBackend(model_id="m", system_placement="assistant_prefix")


@pytest.mark.parametrize(
    ("backend_id", "expected"),
    [("llama_server_qwen3vl", _QWEN_PIN_BODY), ("llama_server", _COSMOS_PIN_BODY)],
)
def test_existing_llama_server_bodies_are_byte_identical_to_the_pre_change_bodies(
    monkeypatch, tmp_path, backend_id, expected
):
    body = _sent(monkeypatch, tmp_path, backend_id, _CHAT_REPLY)["json"]
    assert json.dumps(body) == expected


def test_molmo_effective_block_records_user_prefix_before_text_v1():
    vlm = _shipped_vlm()
    payload_format = describe_effective_sampling(
        resolve_reasoner_config(vlm, "llama_server_molmo2er"),
        load_backend_config(vlm, "llama_server_molmo2er"),
    ).payload_format
    assert (
        payload_format.version,
        payload_format.image_position,
        payload_format.system_placement,
        payload_format.json_guidance,
    ) == ("v1", "before_text", "user_prefix", "prompt_only")


def test_qwen_effective_block_still_records_a_system_message():
    vlm = _shipped_vlm()
    payload_format = describe_effective_sampling(
        resolve_reasoner_config(vlm, "llama_server_qwen3vl"),
        load_backend_config(vlm, "llama_server_qwen3vl"),
    ).payload_format
    assert payload_format.system_placement == "system_message"


# --- preflight model listings ------------------------------------------------


def test_preflight_lists_gemini_models_without_the_models_prefix(monkeypatch):
    pages = [
        {"models": [{"name": "models/gemini-3.8-flash"}], "nextPageToken": "p2"},
        {"models": [{"name": "models/gemini-robotics-er-2-preview"}]},
    ]
    seen: list[dict] = []

    def fake_get(url, headers=None, params=None, timeout=None):
        seen.append({"url": url, "params": dict(params), "headers": dict(headers)})
        return _FakeResponse(200, pages[len(seen) - 1])

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(preflight_backend.requests, "get", fake_get)
    ids = preflight_backend.list_served_models(
        "gemini", "https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY"
    )
    assert ids == ["gemini-3.8-flash", "gemini-robotics-er-2-preview"]
    assert seen[1]["params"]["pageToken"] == "p2"
    assert seen[0]["headers"] == {"x-goog-api-key": "test-key"}


def test_preflight_lists_a_local_server_without_a_key(monkeypatch):
    def fake_get(url, headers=None, params=None, timeout=None):
        assert headers == {}
        return _FakeResponse(200, {"data": [{"id": "molmo2-er"}]})

    monkeypatch.setattr(preflight_backend.requests, "get", fake_get)
    assert preflight_backend.list_served_models(
        "llama_server", "http://127.0.0.1:8090/v1", None
    ) == ["molmo2-er"]


# --- Exploratory: glm-5.3-flash (Zhipu, Group D rolling pin) ----------------


def _glm_sent(monkeypatch, tmp_path) -> dict:
    captured: dict = {}

    def fake_post(url, json, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse(
            200,
            {
                "model": "glm-5.3-flash",
                "choices": [{"message": {"content": "{}", "reasoning_content": "r"}}],
                "usage": {
                    "prompt_tokens": 1670,
                    "completion_tokens": 40,
                    "total_tokens": 1710,
                    "completion_tokens_details": {"reasoning_tokens": 27},
                },
            },
        )

    monkeypatch.setattr("reasoning.vlm.openai_backend.requests.post", fake_post)
    monkeypatch.setenv("ZHIPUAI_API_KEY", "test-key")
    vlm = _shipped_vlm()
    backend = build_backend(
        backend_adapter(vlm, "zhipu_glm"), load_backend_config(vlm, "zhipu_glm")
    )
    captured["response"] = backend.analyze(
        _payload(tmp_path), resolve_reasoner_config(vlm, "zhipu_glm")
    )
    return captured


def test_glm_arm_rides_the_openai_adapter_against_the_zai_endpoint():
    vlm = _shipped_vlm()
    config = load_backend_config(vlm, "zhipu_glm")
    assert backend_adapter(vlm, "zhipu_glm") == "openai"
    assert config.model_id == "glm-5.3-flash"
    assert config.base_url == "https://api.z.ai/api/paas/v4"
    assert config.api_key_env == "ZHIPUAI_API_KEY"


def test_glm_runs_forced_thinking_at_the_lowest_documented_effort():
    # thinking.type "disabled" is HTTP 400 code 1210 on glm-5.3-flash; "low"
    # is the lowest of the documented low/high/max.
    config = load_backend_config(_shipped_vlm(), "zhipu_glm")
    assert (config.thinking_type, config.reasoning_effort) == ("enabled", "low")


def test_glm_output_cap_is_cap_proofed_above_the_shared_2048():
    vlm = _shipped_vlm()
    glm = resolve_reasoner_config(vlm, "zhipu_glm")
    shared = resolve_reasoner_config(vlm, "openai")
    assert glm.max_tokens == 16384 > shared.max_tokens == 2048


def test_glm_has_hosted_arm_parity_attempts_and_image_fallback():
    glm = resolve_reasoner_config(_shipped_vlm(), "zhipu_glm")
    assert (glm.temperature, glm.max_attempts, glm.image_fallback_after_attempts) == (0.0, 4, 2)


def test_glm_request_carries_thinking_enabled_effort_low_and_the_raised_cap(
    monkeypatch, tmp_path
):
    captured = _glm_sent(monkeypatch, tmp_path)
    body = captured["json"]
    assert captured["url"] == "https://api.z.ai/api/paas/v4/chat/completions"
    assert body["thinking"] == {"type": "enabled"}
    assert body["reasoning_effort"] == "low"
    assert body["max_tokens"] == 16384
    assert body["temperature"] == 0.0


def test_openai_adapter_records_reasoning_tokens_when_reported(monkeypatch, tmp_path):
    usage = _glm_sent(monkeypatch, tmp_path)["response"].token_usage
    assert usage == {
        "prompt_tokens": 1670,
        "completion_tokens": 40,
        "total_tokens": 1710,
        "reasoning_tokens": 27,
    }

"""Conformance-review fix program (2026-10-07): per-finding pins.

Rulings: prereg-v2 design spec, "Conformance-review RULINGS (2026-10-07)";
findings: `docs/reports/2026-10-07-conformance-review.md`. Every provider
shape below is a mocked response copied from the provider's documentation,
fetched 2026-10-07 (the doc is cited in each test's docstring). No live
calls: `requests.post` is replaced by a scripted fake.

Doc keys (as in the review): O-chat = developers.openai.com/api/reference/
resources/chat/subresources/completions/methods/create; O-ov =
developers.openai.com/api/reference/overview; D-chat = api-docs.deepseek.com/
api/create-chat-completion; Z-chat = docs.z.ai/api-reference/llm/
chat-completion; Z-code = docs.z.ai/api-reference/api-code; G-err =
ai.google.dev/gemini-api/docs/api-errors; G-api = ai.google.dev/api/
interactions-api; A-ref = platform.claude.com/docs/en/build-with-claude/
refusals-and-fallback; A-err = platform.claude.com/docs/en/api/errors.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests
import yaml
from PIL import Image

from reasoning.vlm.backend_factory import (
    backend_adapter,
    build_backend,
    describe_effective_sampling,
    load_backend_config,
    resolve_reasoner_config,
)
from reasoning.vlm.errors import BackendTimeoutError
from reasoning.vlm.gemini_backend import GENERATION_BLOCKED_CODES
from reasoning.vlm.models import (
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
    RetreatCandidateOption,
    RetreatChoiceRequest,
    RobotStateInput,
)
from reasoning.vlm.reasoner import Reasoner, write_reasoner_log
from reasoning.vlm.retreat_chooser import RetreatChooser

REPO_ROOT = Path(__file__).resolve().parents[2]

_KEYS = {
    "OPENAI_API_KEY": "sk-test-openai-0000",
    "DEEPSEEK_API_KEY": "sk-test-deepseek-0000",
    "ANTHROPIC_API_KEY": "sk-ant-test-0000",
    "GEMINI_API_KEY": "AQ.test-gemini-0000",
    "ZHIPUAI_API_KEY": "test-zhipu-0000.secret",
}

_MODULE = {
    "openai": "openai_backend",
    "openai_gpt51": "openai_backend",
    "deepseek": "openai_backend",
    "zhipu_glm": "openai_backend",
    "openai_gpt56sol": "openai_backend",
    "anthropic": "anthropic_backend",
    "gemini": "gemini_backend",
    "gemini_flash": "gemini_backend",
    "llama_server_qwen3vl": "llama_server_backend",
    "llama_server_molmo2er": "llama_server_backend",
}
_ARMS = list(_MODULE)

_GOOD_DECISION = (
    '{"congestion_detected": true, "type": "deadlock", '
    '"involved_robots": ["robot_1"], "root_cause": "x", '
    '"strategy": "yield", "justification": "y"}'
)

# Every arm's request body at d746768 (before any conformance fix), generated
# from the shipped config and `_fixed_payload`. Only gemini_flash may differ,
# and only by the two ruled fields (F05, F10).
_PRE_FIX_BODIES = {
    "openai": '{"model": "gpt-4o-2024-08-06", "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": [{"type": "text", "text": "usr"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgpmYWtl", "detail": "high"}}]}], "temperature": 0.0, "top_p": 0.95, "max_tokens": 2048, "stream": false}',  # noqa: E501
    "openai_gpt51": '{"model": "gpt-5.1-2025-11-13", "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": [{"type": "text", "text": "usr"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgpmYWtl", "detail": "high"}}]}], "temperature": 0.0, "top_p": 0.95, "max_completion_tokens": 2048, "stream": false, "reasoning_effort": "none"}',  # noqa: E501
    "deepseek": '{"model": "deepseek-flash", "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": [{"type": "text", "text": "usr"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgpmYWtl", "detail": "high"}}]}], "temperature": 0.0, "top_p": 0.95, "max_tokens": 2048, "stream": false, "thinking": {"type": "disabled"}}',  # noqa: E501
    "anthropic": '{"model": "claude-sonnet-5-5", "system": "sys", "messages": [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBORw0KGgpmYWtl"}}, {"type": "text", "text": "usr"}]}], "max_tokens": 2048, "thinking": {"type": "between_tools"}}',  # noqa: E501
    "gemini": '{"model": "gemini-robotics-er-2-preview", "system_instruction": "sys", "input": [{"type": "text", "text": "usr"}, {"type": "image", "data": "iVBORw0KGgpmYWtl", "mime_type": "image/png"}], "generation_config": {"thinking_level": "low", "max_output_tokens": 2048}}',  # noqa: E501
    "gemini_flash": '{"model": "gemini-3.8-flash", "system_instruction": "sys", "input": [{"type": "text", "text": "usr"}, {"type": "image", "data": "iVBORw0KGgpmYWtl", "mime_type": "image/png"}], "generation_config": {"thinking_level": "low", "max_output_tokens": 2048}}',  # noqa: E501
    "llama_server_qwen3vl": '{"model": "qwen3-vl-8b-instruct-q4_k_m", "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgpmYWtl"}}, {"type": "text", "text": "usr"}]}], "temperature": 0.0, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0, "max_tokens": 2048, "stream": false}',  # noqa: E501
    "llama_server_molmo2er": '{"model": "molmo2-er", "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgpmYWtl"}}, {"type": "text", "text": "sys\\n\\nusr"}]}], "temperature": 0.0, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0, "max_tokens": 2048, "stream": false}',  # noqa: E501
    "zhipu_glm": '{"model": "glm-5.3-flash", "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": [{"type": "text", "text": "usr"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgpmYWtl", "detail": "high"}}]}], "temperature": 0.0, "top_p": 0.95, "max_tokens": 16384, "stream": false, "reasoning_effort": "low", "thinking": {"type": "enabled"}}',  # noqa: E501
}

# Arms wired after the conformance program, pinned from their first commit
# (NOT pre-fix bodies). gpt-5.6-sol (2026-10-07, gpt-5.1 successor): the
# gpt-5.1 body with only the model id changed.
_ADDED_BODIES = {
    "openai_gpt56sol": '{"model": "gpt-5.6-sol", "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": [{"type": "text", "text": "usr"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgpmYWtl", "detail": "high"}}]}], "temperature": 0.0, "top_p": 0.95, "max_completion_tokens": 2048, "stream": false, "reasoning_effort": "none"}',  # noqa: E501
}


class _Resp:
    def __init__(
        self,
        status_code: int,
        payload: object = None,
        headers: dict[str, str] | None = None,
        text: str | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text if text is not None else json.dumps(payload)

    def json(self) -> object:
        if self._payload is None:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload


@pytest.fixture(autouse=True)
def _keys(monkeypatch):
    for name, value in _KEYS.items():
        monkeypatch.setenv(name, value)


def _vlm() -> dict:
    return yaml.safe_load((REPO_ROOT / "config" / "models.yaml").read_text())["vlm"]


def _arm(arm_id: str):
    vlm = _vlm()
    backend_config = load_backend_config(vlm, arm_id)
    reasoner_config = resolve_reasoner_config(vlm, arm_id)
    backend = build_backend(backend_adapter(vlm, arm_id), backend_config)
    return backend, reasoner_config, describe_effective_sampling(reasoner_config, backend_config)


def _script(monkeypatch, module: str, *responses) -> list[dict]:
    calls: list[dict] = []
    queue = list(responses)

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(json)
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, BaseException):
            raise item
        return item

    monkeypatch.setattr(f"reasoning.vlm.{module}.requests.post", fake_post)
    return calls


def _fixed_payload(tmp_path: Path) -> PromptPayload:
    frame = tmp_path / "frame.png"
    frame.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return PromptPayload(
        system_prompt="sys", user_prompt="usr", image_path=str(frame), known_robot_ids=["robot_1"]
    )


def _request(tmp_path: Path) -> ReasonerRequest:
    frame = tmp_path / "real.png"
    Image.new("RGB", (16, 12), (10, 200, 30)).save(frame)
    return ReasonerRequest(
        request_id="r-1",
        image_path=str(frame),
        frame_id="f",
        stamp=0.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0, y=0, theta=0)],
    )


def _stage2_request(tmp_path: Path) -> RetreatChoiceRequest:
    frame = tmp_path / "s2.png"
    Image.new("RGB", (16, 12)).save(frame)
    return RetreatChoiceRequest(
        request_id="req-2",
        image_path=str(frame),
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


def _chat_ok(content: str | None = _GOOD_DECISION, **extra) -> _Resp:
    choice = {"index": 0, "message": {"role": "assistant", "content": content}}
    choice["finish_reason"] = extra.pop("finish_reason", "stop")
    return _Resp(200, {"id": "chatcmpl-1", "model": "m", "choices": [choice], **extra})


def _anthropic_ok(text: str = _GOOD_DECISION) -> _Resp:
    return _Resp(
        200,
        {
            "id": "msg_1",
            "model": "claude-sonnet-5-5",
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "stop_details": None,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
    )


def _gemini_ok(text: str = _GOOD_DECISION, status: str = "completed") -> _Resp:
    return _Resp(
        200,
        {
            "id": "v1_interaction",
            "model": "gemini-3.8-flash",
            "object": "interaction",
            "status": status,
            "steps": [{"type": "model_output", "content": [{"type": "text", "text": text}]}],
        },
    )


def _ok_for(module: str) -> _Resp:
    if module == "anthropic_backend":
        return _anthropic_ok()
    if module == "gemini_backend":
        return _gemini_ok()
    return _chat_ok()


# --- request-byte freeze (no request byte moves, except the ruled flash fields)


@pytest.mark.parametrize("arm_id", _ARMS)
def test_request_bytes_match_the_pre_fix_body_except_ruled_flash_fields(
    monkeypatch, tmp_path, arm_id
):
    calls = _script(monkeypatch, _MODULE[arm_id], _ok_for(_MODULE[arm_id]))
    backend, config, _ = _arm(arm_id)
    backend.analyze(_fixed_payload(tmp_path), config)
    expected = json.loads(_PRE_FIX_BODIES.get(arm_id) or _ADDED_BODIES[arm_id])
    if arm_id == "gemini_flash":
        expected["generation_config"]["max_output_tokens"] = 16384  # F05
        expected["store"] = False  # F10
    assert json.dumps(calls[0]) == json.dumps(expected)


def test_er2_frozen_request_shape_is_byte_identical_and_sends_no_store(monkeypatch, tmp_path):
    """F10 ruling: ER-2's frozen pin keeps its wire shape (no `store`)."""
    calls = _script(monkeypatch, "gemini_backend", _gemini_ok())
    backend, config, _ = _arm("gemini")
    backend.analyze(_fixed_payload(tmp_path), config)
    assert json.dumps(calls[0]) == _PRE_FIX_BODIES["gemini"]
    assert "store" not in calls[0]


def test_gemini_flash_sends_store_false(monkeypatch, tmp_path):
    """F10 ruling. G-int: "By default, the API stores all Interaction objects
    (store=true) ... you can set store=false"; G-api `store` "Input only."."""
    calls = _script(monkeypatch, "gemini_backend", _gemini_ok())
    backend, config, _ = _arm("gemini_flash")
    backend.analyze(_fixed_payload(tmp_path), config)
    assert calls[0]["store"] is False


# --- F03: documented refusal channels ----------------------------------------


def test_openai_message_refusal_is_a_provider_refusal(monkeypatch, tmp_path):
    """O-chat: message `refusal: optional string or null` "The refusal message
    by the assistant." (content null)."""
    reply = _chat_ok(content=None)
    reply._payload["choices"][0]["message"]["refusal"] = "I'm unable to help with that."
    _script(monkeypatch, "openai_backend", reply)
    backend, config, _ = _arm("openai")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert (response.refusal, response.refusal_category) == (True, None)
    assert response.text == "I'm unable to help with that."


@pytest.mark.parametrize("arm_id", ["openai", "openai_gpt51", "deepseek", "openai_gpt56sol"])
def test_content_filter_finish_reason_is_a_provider_refusal(monkeypatch, tmp_path, arm_id):
    """O-chat: finish_reason "content_filter if content was omitted due to a
    flag from our content filters"; D-chat lists the same value."""
    _script(monkeypatch, "openai_backend", _chat_ok(content="", finish_reason="content_filter"))
    backend, config, _ = _arm(arm_id)
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert (response.refusal, response.refusal_category, response.finish_reason) == (
        True,
        "content_filter",
        "content_filter",
    )


def test_zhipu_sensitive_finish_reason_is_a_provider_refusal(monkeypatch, tmp_path):
    """Z-chat: finish_reason "Can be `stop`, `tool_calls`, `length`,
    `sensitive`, `model_context_window_exceeded` or `network_error`."."""
    _script(monkeypatch, "openai_backend", _chat_ok(content="", finish_reason="sensitive"))
    backend, config, _ = _arm("zhipu_glm")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert (response.refusal, response.refusal_category) == (True, "sensitive")


@pytest.mark.parametrize("code", ["1301", 1301])
def test_zhipu_1301_http_400_is_a_provider_refusal(monkeypatch, tmp_path, code):
    """Z-code: "1301 | 400 | System detected potentially unsafe or sensitive
    content in input or generation"; error shape `{"error": {"code": "1214",
    "message": ...}}` (string), Z-chat Error schema `code: integer`."""
    body = {"error": {"code": code, "message": "System detected potentially unsafe content."}}
    _script(monkeypatch, "openai_backend", _Resp(400, body))
    backend, config, _ = _arm("zhipu_glm")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert (response.refusal, response.refusal_category, response.text) == (True, "1301", "")


def test_zhipu_non_refusal_400_stays_a_deterministic_error(monkeypatch, tmp_path):
    """Z-code: "1210 | 400 | Invalid API parameter" -- not a refusal; under
    the F02 policy it consumes exactly one attempt."""
    body = {"error": {"code": "1210", "message": "Invalid API parameter"}}
    calls = _script(monkeypatch, "openai_backend", _Resp(400, body))
    backend, config, effective = _arm("zhipu_glm")
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    assert (len(calls), result.diagnostics.attempts, result.diagnostics.refusal_attempts) == (
        1,
        1,
        0,
    )
    record = result.diagnostics.attempt_records[0]
    assert (record.outcome, record.http_status, record.provider_error_code) == (
        "http_error",
        400,
        "1210",
    )


def test_zhipu_1301_takes_the_refusal_path_with_grey_fallback(monkeypatch, tmp_path):
    """Z-code 1301 (HTTP 400) is a refusal: all four attempts are spent and
    the grey-image fallback fires on attempt 3, not a one-attempt stop."""
    body = {"error": {"code": "1301", "message": "unsafe or sensitive content"}}
    calls = _script(monkeypatch, "openai_backend", _Resp(400, body))
    backend, config, effective = _arm("zhipu_glm")
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    diagnostics = result.diagnostics
    assert (len(calls), diagnostics.attempts, diagnostics.refusal_attempts) == (4, 4, 4)
    assert diagnostics.image_fallback_attempt == 3
    assert diagnostics.refusal_category == "1301"
    assert {r.outcome for r in diagnostics.attempt_records} == {"refusal"}
    assert {r.refusal_source for r in diagnostics.attempt_records} == {"provider"}
    assert diagnostics.attempt_records[0].http_status == 400


@pytest.mark.parametrize("code", sorted(GENERATION_BLOCKED_CODES))
def test_gemini_generation_blocked_code_is_a_provider_refusal(monkeypatch, tmp_path, code):
    """G-err "Generation blocked codes": "policy, safety, or content
    restrictions blocked the model's output. When you receive one of these
    codes, modify your input and retry." Standard requests: "the API sets
    the HTTP response status code ... and returns an error object":
    `{"error": {"code": ..., "message": ...}}`."""
    body = {"error": {"code": code, "message": "blocked"}}
    _script(monkeypatch, "gemini_backend", _Resp(400, body))
    backend, config, _ = _arm("gemini_flash")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert (response.refusal, response.refusal_category) == (True, code)


def test_gemini_blocked_code_takes_the_refusal_path_with_grey_fallback(monkeypatch, tmp_path):
    """G-err blocked code through the full pipeline on gemini_flash (4
    attempts, fallback after 2): the documented "modify your input and
    retry" is exactly the grey-image fallback."""
    body = {"error": {"code": "safety", "message": "blocked"}}
    calls = _script(
        monkeypatch, "gemini_backend", _Resp(400, body), _Resp(400, body), _gemini_ok()
    )
    backend, config, effective = _arm("gemini_flash")
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    assert result.decision is not None
    assert (result.diagnostics.attempts, result.diagnostics.refusal_attempts) == (3, 2)
    assert result.diagnostics.image_fallback_attempt == 3
    # The third request carried the neutral image, not the frame.
    assert calls[2]["input"][1]["data"] != calls[0]["input"][1]["data"]


def test_gemini_failed_status_with_blocked_code_is_a_provider_refusal(monkeypatch, tmp_path):
    """G-api Interaction `status`: "failed: The interaction failed."; a
    blocked code (G-err) on it is a refusal."""
    reply = _gemini_ok(text="", status="failed")
    reply._payload["error"] = {"code": "prohibited_content", "message": "blocked"}
    _script(monkeypatch, "gemini_backend", reply)
    backend, config, _ = _arm("gemini_flash")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert (response.refusal, response.refusal_category, response.finish_reason) == (
        True,
        "prohibited_content",
        "failed",
    )


def test_gemini_failed_status_without_blocked_code_is_a_transport_failure(monkeypatch, tmp_path):
    """G-api `status: failed` with no generation-blocked code is retried."""
    _script(monkeypatch, "gemini_backend", _gemini_ok(text="", status="failed"))
    backend, config, _ = _arm("gemini_flash")
    with pytest.raises(ConnectionError, match="interaction failed"):
        backend.analyze(_fixed_payload(tmp_path), config)


def test_anthropic_refusal_shape_is_a_provider_refusal(monkeypatch, tmp_path):
    """A-ref "What a refusal looks like": HTTP 200, `content: []`,
    `stop_reason: "refusal"`, `stop_details: {"type": "refusal", "category":
    "cyber", "explanation": ...}`."""
    reply = _Resp(
        200,
        {
            "id": "msg_01XFUDYJgAACzvnptvVoYEL",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-5-5",
            "content": [],
            "stop_reason": "refusal",
            "stop_details": {
                "type": "refusal",
                "category": "cyber",
                "explanation": "This request was declined because it could enable cyber harm.",
            },
            "usage": {"input_tokens": 412, "output_tokens": 0},
        },
    )
    _script(monkeypatch, "anthropic_backend", reply)
    backend, config, _ = _arm("anthropic")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert (response.refusal, response.refusal_category, response.finish_reason) == (
        True,
        "cyber",
        "refusal",
    )


def test_text_pattern_is_only_the_fallback_refusal_channel(monkeypatch, tmp_path):
    """No provider signal (plain `stop`): only the English pattern flags it,
    and the attempt record says so."""
    _script(
        monkeypatch,
        "openai_backend",
        _chat_ok(content="I'm sorry, I can't assist with that."),
        _chat_ok(),
    )
    backend, config, effective = _arm("openai")
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    first = result.diagnostics.attempt_records[0]
    assert (first.outcome, first.refusal_source) == ("refusal", "text_pattern")


def test_provider_refusal_counts_on_stage2(monkeypatch, tmp_path):
    """Stage 2 sees the same mapped channel (O-chat content_filter)."""
    _script(monkeypatch, "openai_backend", _chat_ok(content="", finish_reason="content_filter"))
    backend, config, _ = _arm("openai")
    stage2 = config.model_copy(update={"max_attempts": 2, "timeout_sec": 8})
    result = RetreatChooser(backend, stage2).choose(_stage2_request(tmp_path))
    assert (result.failure_cause, result.refusal_attempts) == ("refusal", 2)
    assert result.attempt_records[0].refusal_source == "provider"


# --- F04: DeepSeek system_fingerprint ----------------------------------------


def test_deepseek_system_fingerprint_reaches_effective_config_and_records(monkeypatch, tmp_path):
    """D-chat: "system_fingerprint string required This fingerprint
    represents the backend configuration that the model runs with."."""
    _script(monkeypatch, "openai_backend", _chat_ok(system_fingerprint="fp_8b2a6d7c1e"))
    backend, config, effective = _arm("deepseek")
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    diagnostics = result.diagnostics
    assert diagnostics.system_fingerprint == "fp_8b2a6d7c1e"
    assert diagnostics.reasoner_config_effective.system_fingerprint == "fp_8b2a6d7c1e"
    assert diagnostics.attempt_records[0].system_fingerprint == "fp_8b2a6d7c1e"


# --- F05 / F06: finish reasons persisted; flash cap and status:incomplete -----


def test_gemini_flash_cap_is_16384():
    """F05 ruling (GLM treatment); G-think: max_output_tokens "including
    thought tokens ... a hard cutoff"."""
    assert resolve_reasoner_config(_vlm(), "gemini_flash").max_tokens == 16384


def test_gemini_status_incomplete_is_recorded_per_attempt(monkeypatch, tmp_path):
    """G-api status "incomplete: The interaction is completed, but contains
    incomplete results (e.g. hitting max_tokens)"."""
    _script(
        monkeypatch,
        "gemini_backend",
        _gemini_ok(text='{"congestion_detected": tr', status="incomplete"),
        _gemini_ok(),
    )
    backend, config, effective = _arm("gemini_flash")
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    assert [r.finish_reason for r in result.diagnostics.attempt_records] == [
        "incomplete",
        "completed",
    ]
    assert result.diagnostics.attempt_records[0].outcome == "parse_failure"


@pytest.mark.parametrize(
    ("arm_id", "reply", "reason"),
    [
        ("openai", lambda: _chat_ok(finish_reason="length"), "length"),
        ("deepseek", lambda: _chat_ok(finish_reason="insufficient_system_resource"),
         "insufficient_system_resource"),
        ("anthropic", _anthropic_ok, "end_turn"),
        ("gemini", _gemini_ok, "completed"),
        ("llama_server_qwen3vl", lambda: _chat_ok(finish_reason="stop"), "stop"),
    ],
)
def test_finish_reason_is_persisted_in_decision_and_trace(
    monkeypatch, tmp_path, arm_id, reply, reason
):
    """F06: finish/stop/status reasons reach the artifact (decision JSON =
    diagnostics dump; JSONL trace)."""
    _script(monkeypatch, _MODULE[arm_id], reply())
    backend, config, effective = _arm(arm_id)
    request = _request(tmp_path)
    result = Reasoner(backend, config, effective).run(request)
    dumped = result.diagnostics.model_dump(mode="json")
    assert dumped["finish_reason"] == reason
    assert dumped["attempt_records"][-1]["finish_reason"] == reason
    trace = tmp_path / "trace.jsonl"
    write_reasoner_log(trace, request, result)
    record = json.loads(trace.read_text())
    assert record["finish_reason"] == reason
    assert record["attempt_records"][-1]["finish_reason"] == reason


# --- F07: empty-200 is a parse failure everywhere -----------------------------


@pytest.mark.parametrize(
    ("arm_id", "reply"),
    [
        ("openai", lambda: _chat_ok(content=None)),
        ("anthropic", lambda: _Resp(200, {"content": [], "stop_reason": "max_tokens",
                                          "usage": {"input_tokens": 9, "output_tokens": 2048}})),
        ("gemini", lambda: _gemini_ok(text="")),
        ("llama_server_qwen3vl", lambda: _chat_ok(content=None)),
    ],
)
def test_valid_200_without_text_is_a_parse_failure_with_usage(
    monkeypatch, tmp_path, arm_id, reply
):
    _script(monkeypatch, _MODULE[arm_id], reply())
    backend, config, effective = _arm(arm_id)
    config = config.model_copy(update={"max_attempts": 2})
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    assert result.diagnostics.error_type == "VLMOutputParseError"
    assert [r.outcome for r in result.diagnostics.attempt_records] == ["parse_failure"] * 2
    if arm_id == "anthropic":
        assert result.diagnostics.attempt_token_usage[0] == {
            "input_tokens": 9,
            "output_tokens": 2048,
        }


# --- F08: recorded sampling/thinking = sent (extended wire pin) --------------


def _sent_value(body: dict, field: str):
    generation = body.get("generation_config", {})
    if field in ("thinking_level", "seed"):
        return generation.get(field)
    if field == "max_tokens":
        for key in ("max_tokens", "max_completion_tokens"):
            if key in body:
                return body[key]
        return generation.get("max_output_tokens")
    if field == "thinking_mode":
        return (body.get("thinking") or {}).get("type")
    if field == "effort":
        return (body.get("output_config") or {}).get("effort")
    return body.get(field)


@pytest.mark.parametrize("arm_id", _ARMS)
def test_recorded_sampling_and_thinking_fields_are_exactly_what_is_sent(
    monkeypatch, tmp_path, arm_id
):
    """Every sampling field is either sent with its recorded value or listed
    in `unsupported_sampling` and absent from the body; every thinking /
    effort / seed / cap field recorded equals the body's (None = absent)."""
    calls = _script(monkeypatch, _MODULE[arm_id], _ok_for(_MODULE[arm_id]))
    backend, config, effective = _arm(arm_id)
    response = backend.analyze(_fixed_payload(tmp_path), config)
    body = calls[0]
    unsent = response.raw.get("unsupported_sampling") or {}
    for field in ("temperature", "top_p", "top_k", "presence_penalty"):
        recorded = getattr(effective, field)
        if field in unsent:
            assert unsent[field] == recorded, field
            assert field not in body and field not in body.get("generation_config", {}), field
        else:
            assert body[field] == recorded, field
    for field in ("thinking_level", "seed", "max_tokens", "thinking_mode", "effort",
                  "reasoning_effort"):
        assert _sent_value(body, field) == getattr(effective, field), field


# --- F09: arm id on every path -------------------------------------------------


def test_success_records_the_arm_id_not_the_model_id(monkeypatch, tmp_path):
    _script(monkeypatch, "openai_backend", _chat_ok())
    backend, config, effective = _arm("openai_gpt51")
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.backend_id == "openai_gpt51"


# --- F11: one timeout label ---------------------------------------------------


@pytest.mark.parametrize("arm_id", ["openai", "anthropic", "gemini", "llama_server_qwen3vl"])
def test_requests_timeout_is_a_backend_timeout_on_every_adapter(monkeypatch, tmp_path, arm_id):
    _script(monkeypatch, _MODULE[arm_id], requests.exceptions.ReadTimeout("read timed out"))
    backend, config, _ = _arm(arm_id)
    with pytest.raises(BackendTimeoutError):
        backend.analyze(_fixed_payload(tmp_path), config)


@pytest.mark.parametrize("arm_id", ["openai", "anthropic", "gemini", "llama_server_qwen3vl"])
def test_stage2_labels_a_requests_timeout_as_timeout(monkeypatch, tmp_path, arm_id):
    _script(monkeypatch, _MODULE[arm_id], requests.exceptions.ReadTimeout("read timed out"))
    backend, config, _ = _arm(arm_id)
    stage2 = config.model_copy(update={"max_attempts": 2, "timeout_sec": 8})
    result = RetreatChooser(backend, stage2).choose(_stage2_request(tmp_path))
    assert result.failure_cause == "timeout"
    assert [r.outcome for r in result.attempt_records] == ["timeout", "timeout"]


# --- F13: local arms at full parity ------------------------------------------


@pytest.mark.parametrize("arm_id", ["llama_server_qwen3vl", "llama_server_molmo2er"])
def test_local_arms_have_full_parity(arm_id):
    config = resolve_reasoner_config(_vlm(), arm_id)
    assert (config.max_attempts, config.image_fallback_after_attempts) == (4, 2)


def test_local_arm_grey_fallback_fires_on_a_text_refusal(monkeypatch, tmp_path):
    _script(
        monkeypatch,
        "llama_server_backend",
        _chat_ok(content="I'm sorry, but I can't assist with that."),
        _chat_ok(content="I'm sorry, but I can't assist with that."),
        _chat_ok(),
    )
    backend, config, effective = _arm("llama_server_qwen3vl")
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.image_fallback_attempt == 3


# --- F14: one re-ask suffix ----------------------------------------------------


class _RecordsPrompts:
    def __init__(self, answers: list[str]) -> None:
        self.prompts: list[PromptPayload] = []
        self._answers = answers

    def analyze(self, payload, config):
        from reasoning.vlm.models import BackendResponse

        self.prompts.append(payload)
        return BackendResponse(text=self._answers[len(self.prompts) - 1], backend_id="m")


def test_stage1_reask_suffix_never_stacks(tmp_path):
    backend = _RecordsPrompts(["not json", "still not json", "nope", _GOOD_DECISION])
    config = ReasonerConfig(backend_id="arm", max_attempts=4)
    result = Reasoner(backend, config).run(_request(tmp_path))
    assert result.decision is not None
    base = backend.prompts[0].user_prompt
    for later in backend.prompts[1:]:
        assert later.user_prompt.count("Your previous response was invalid") == 1
        assert later.user_prompt.startswith(base)


def test_stage1_reask_after_fallback_keeps_the_neutral_image(tmp_path):
    refusal = "I'm sorry, I can't assist with that."
    backend = _RecordsPrompts([refusal, refusal, "not json", _GOOD_DECISION])
    config = ReasonerConfig(backend_id="arm", max_attempts=4, image_fallback_after_attempts=2)
    Reasoner(backend, config).run(_request(tmp_path))
    first, third, fourth = backend.prompts[0], backend.prompts[2], backend.prompts[3]
    # Attempt 3 is the fallback (original text, neutral image); attempt 4
    # re-asks from it: neutral image kept, exactly one suffix.
    assert third.image_path == fourth.image_path != first.image_path
    assert third.user_prompt == first.user_prompt
    assert fourth.user_prompt.startswith(third.user_prompt)
    assert fourth.user_prompt.count("Your previous response was invalid") == 1


# --- F15: error text is redacted ------------------------------------------------


@pytest.mark.parametrize(
    ("arm_id", "env"),
    [
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("gemini", "GEMINI_API_KEY"),
        ("zhipu_glm", "ZHIPUAI_API_KEY"),
    ],
)
def test_http_error_body_echoing_the_key_is_redacted(monkeypatch, tmp_path, arm_id, env):
    key = _KEYS[env]
    body = {"error": {"code": "invalid_api_key", "message": f"Incorrect API key provided: {key}"}}
    _script(monkeypatch, _MODULE[arm_id], _Resp(401, body))
    backend, config, effective = _arm(arm_id)
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    assert key not in (result.diagnostics.error_message or "")
    assert "***REDACTED***" in result.diagnostics.error_message


# --- F16: additive usage --------------------------------------------------------


def test_openai_usage_adds_cached_and_image_tokens(monkeypatch, tmp_path):
    """O-chat usage.prompt_tokens_details: `cached_tokens` "Cached tokens
    present in the prompt", `image_tokens` "Image input tokens present in the
    prompt"."""
    usage = {
        "prompt_tokens": 1200,
        "completion_tokens": 40,
        "total_tokens": 1240,
        "prompt_tokens_details": {"cached_tokens": 1024, "image_tokens": 765},
    }
    _script(monkeypatch, "openai_backend", _chat_ok(usage=usage))
    backend, config, _ = _arm("openai")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert (response.token_usage["cached_tokens"], response.token_usage["image_tokens"]) == (
        1024,
        765,
    )


def test_openai_usage_adds_cache_write_tokens_for_gpt56sol(monkeypatch, tmp_path):
    """O-chat usage.prompt_tokens_details: `cache_write_tokens` "The unadjusted
    number of prompt tokens written to cache" (GPT-5.6 bills cache writes at
    1.25x the uncached input rate; latest-model guide, fetched 2026-10-07)."""
    usage = {
        "prompt_tokens": 1464,
        "completion_tokens": 4,
        "total_tokens": 1468,
        "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 1280},
        "completion_tokens_details": {"reasoning_tokens": 0},
    }
    _script(monkeypatch, "openai_backend", _chat_ok(usage=usage))
    backend, config, _ = _arm("openai_gpt56sol")
    response = backend.analyze(_fixed_payload(tmp_path), config)
    assert response.token_usage == {
        "prompt_tokens": 1464,
        "completion_tokens": 4,
        "total_tokens": 1468,
        "reasoning_tokens": 0,
        "cached_tokens": 0,
        "cache_write_tokens": 1280,
    }


def test_deepseek_usage_adds_cache_hit_and_miss(monkeypatch, tmp_path):
    """D-chat usage: "prompt_tokens ... equals prompt_cache_hit_tokens +
    prompt_cache_miss_tokens"; prompt_tokens_details.cached_tokens."""
    usage = {
        "completion_tokens": 30,
        "prompt_tokens": 900,
        "prompt_tokens_details": {"cached_tokens": 640},
        "prompt_cache_hit_tokens": 640,
        "prompt_cache_miss_tokens": 260,
        "total_tokens": 930,
    }
    _script(monkeypatch, "openai_backend", _chat_ok(usage=usage))
    backend, config, _ = _arm("deepseek")
    usage_out = backend.analyze(_fixed_payload(tmp_path), config).token_usage
    assert (
        usage_out["cached_tokens"],
        usage_out["prompt_cache_hit_tokens"],
        usage_out["prompt_cache_miss_tokens"],
    ) == (640, 640, 260)


def test_zhipu_usage_adds_cached_tokens(monkeypatch, tmp_path):
    """Z-chat usage.prompt_tokens_details.cached_tokens "Number of tokens
    served from cache"."""
    usage = {
        "prompt_tokens": 1670,
        "completion_tokens": 40,
        "prompt_tokens_details": {"cached_tokens": 1500},
        "total_tokens": 1710,
    }
    _script(monkeypatch, "openai_backend", _chat_ok(usage=usage))
    backend, config, _ = _arm("zhipu_glm")
    assert backend.analyze(_fixed_payload(tmp_path), config).token_usage["cached_tokens"] == 1500


def test_gemini_usage_adds_cached_tool_and_modality_tokens(monkeypatch, tmp_path):
    """G-api example `usage`: input_tokens_by_modality, total_cached_tokens,
    total_tool_use_tokens."""
    reply = _gemini_ok()
    reply._payload["usage"] = {
        "input_tokens_by_modality": [
            {"modality": "text", "tokens": 7},
            {"modality": "image", "tokens": 1032},
        ],
        "total_cached_tokens": 0,
        "total_input_tokens": 1039,
        "total_output_tokens": 20,
        "total_thought_tokens": 22,
        "total_tokens": 1081,
        "total_tool_use_tokens": 0,
    }
    _script(monkeypatch, "gemini_backend", reply)
    backend, config, _ = _arm("gemini")
    assert backend.analyze(_fixed_payload(tmp_path), config).token_usage == {
        "prompt_tokens": 1039,
        "completion_tokens": 20,
        "thought_tokens": 22,
        "total_tokens": 1081,
        "cached_tokens": 0,
        "tool_use_tokens": 0,
        "input_tokens_text": 7,
        "input_tokens_image": 1032,
    }


def test_gemini_usage_ignores_the_nonexistent_usage_metadata_field(monkeypatch, tmp_path):
    reply = _gemini_ok()
    reply._payload["usage_metadata"] = {"total_input_tokens": 5}
    _script(monkeypatch, "gemini_backend", reply)
    backend, config, _ = _arm("gemini")
    assert backend.analyze(_fixed_payload(tmp_path), config).token_usage is None


# --- F18: provider request ids --------------------------------------------------


def test_openai_request_id_header_is_recorded(monkeypatch, tmp_path):
    """O-ov: "x-request-id : Unique identifier for this API request"."""
    reply = _chat_ok()
    reply.headers = {"x-request-id": "req_abc123"}
    _script(monkeypatch, "openai_backend", reply)
    backend, config, effective = _arm("openai")
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    assert result.diagnostics.attempt_records[0].provider_request_id == "req_abc123"


def test_anthropic_request_id_header_is_recorded_on_an_http_error(monkeypatch, tmp_path):
    """A-err: "Every API response includes a unique `request-id` header"."""
    body = {"type": "error", "error": {"type": "invalid_request_error", "message": "bad"},
            "request_id": "req_018EeWyXxfu5pfWkrYcMdjWG"}
    _script(
        monkeypatch,
        "anthropic_backend",
        _Resp(400, body, headers={"request-id": "req_018EeWyXxfu5pfWkrYcMdjWG"}),
    )
    backend, config, effective = _arm("anthropic")
    result = Reasoner(backend, config, effective).run(_request(tmp_path))
    record = result.diagnostics.attempt_records[0]
    assert (record.provider_request_id, record.provider_error_code) == (
        "req_018EeWyXxfu5pfWkrYcMdjWG",
        "invalid_request_error",
    )


def test_zhipu_body_request_id_is_recorded(monkeypatch, tmp_path):
    """Z-chat ChatCompletionResponse `request_id`: "Request ID"."""
    reply = _chat_ok(request_id="20261007-zhipu-req")
    _script(monkeypatch, "openai_backend", reply)
    backend, config, _ = _arm("zhipu_glm")
    assert backend.analyze(_fixed_payload(tmp_path), config).provider_request_id == (
        "20261007-zhipu-req"
    )


def test_gemini_interaction_id_is_recorded(monkeypatch, tmp_path):
    """G-api Interaction `id`: "A unique identifier for the interaction"."""
    _script(monkeypatch, "gemini_backend", _gemini_ok())
    backend, config, _ = _arm("gemini")
    assert backend.analyze(_fixed_payload(tmp_path), config).provider_request_id == (
        "v1_interaction"
    )


# --- F21 ----------------------------------------------------------------------


def test_molmo_vllm_server_ignores_the_repo_generation_config():
    """V-oai: "To disable this behavior, please pass --generation-config vllm"."""
    script = (REPO_ROOT / "scripts" / "vm" / "molmo_serve.sh").read_text()
    assert "--generation-config vllm" in script

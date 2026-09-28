import json
import re
import time
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from PIL import Image

from reasoning.schemas import load_schema
from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.backend_factory import (
    backend_section,
    build_backend,
    describe_effective_sampling,
    resolve_reasoner_config,
)
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    BackendResponse,
    EffectiveSamplingConfig,
    GeminiBackendConfig,
    LlamaServerBackendConfig,
    OpenAIBackendConfig,
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
    RobotStateInput,
)
from reasoning.vlm.output_parser import BackendTimeoutError
from reasoning.vlm.reasoner import (
    Reasoner,
    build_failed_result,
    build_reask_prompt,
    invoke_backend,
    is_refusal,
    make_neutral_image,
    write_reasoner_log,
)


def test_llama_config_loads_without_model_path():
    config = LlamaServerBackendConfig(model_id="cosmos-reason2-8b")
    assert config.base_url == "http://127.0.0.1:8080/v1"
    assert config.model_path is None
    assert config.mmproj_path is None


def test_llama_config_accepts_optional_paths():
    config = LlamaServerBackendConfig(
        model_id="cosmos-reason2-8b",
        model_path="/models/cosmos.gguf",
        mmproj_path="/models/mmproj.gguf",
    )
    assert config.model_path == "/models/cosmos.gguf"
    assert config.mmproj_path == "/models/mmproj.gguf"


def test_vlmbackend_is_runtime_checkable_protocol():
    class Dummy:
        def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
            return BackendResponse(text="{}", backend_id="dummy")

    assert isinstance(Dummy(), VLMBackend)


_PAYLOAD = PromptPayload(
    system_prompt="sys",
    user_prompt="usr",
    image_path="/tmp/frame.png",
    known_robot_ids=["robot_1"],
)
_CONFIG = ReasonerConfig(backend_id="mock")


def test_mock_backend_default_returns_no_congestion_json():
    response = MockBackend().analyze(_PAYLOAD, _CONFIG)
    assert response.backend_id == "mock"
    assert '"congestion_detected": false' in response.text


def test_mock_backend_returns_configured_text_and_records_payload():
    backend = MockBackend(response_text='{"ok": true}')
    response = backend.analyze(_PAYLOAD, _CONFIG)
    assert response.text == '{"ok": true}'
    assert backend.last_payload is _PAYLOAD
    assert backend.last_config is _CONFIG


def test_mock_backend_sequence_advances_then_holds_last():
    backend = MockBackend(response_sequence=["first", "second"])
    assert backend.analyze(_PAYLOAD, _CONFIG).text == "first"
    assert backend.analyze(_PAYLOAD, _CONFIG).text == "second"
    assert backend.analyze(_PAYLOAD, _CONFIG).text == "second"


def test_invoke_backend_fills_latency_when_backend_reports_none():
    class NoLatencyBackend:
        def analyze(self, payload, config):
            return BackendResponse(text="{}", backend_id="nolat")

    response = invoke_backend(NoLatencyBackend(), _PAYLOAD, ReasonerConfig(backend_id="nolat"))
    assert response.latency_ms is not None and response.latency_ms >= 0


def test_invoke_backend_preserves_backend_reported_zero_latency():
    class ZeroLatencyBackend:
        def analyze(self, payload, config):
            return BackendResponse(text="{}", backend_id="zero", latency_ms=0)

    response = invoke_backend(ZeroLatencyBackend(), _PAYLOAD, ReasonerConfig(backend_id="zero"))
    assert response.latency_ms == 0


def test_invoke_backend_raises_on_timeout_without_blocking():
    class SlowBackend:
        def analyze(self, payload, config):
            time.sleep(0.5)
            return BackendResponse(text="{}", backend_id="slow")

    config = ReasonerConfig(backend_id="slow", timeout_sec=0.02)
    start = time.monotonic()
    with pytest.raises(BackendTimeoutError):
        invoke_backend(SlowBackend(), _PAYLOAD, config)
    # Must return promptly after the timeout, not after the 0.5s backend sleep.
    assert time.monotonic() - start < 0.3


def test_build_reask_prompt_appends_error_and_preserves_fields():
    reask = build_reask_prompt(_PAYLOAD, "bad enum")
    assert reask.system_prompt == _PAYLOAD.system_prompt
    assert reask.image_path == _PAYLOAD.image_path
    assert reask.known_robot_ids == _PAYLOAD.known_robot_ids
    assert "bad enum" in reask.user_prompt
    assert reask.user_prompt.startswith(_PAYLOAD.user_prompt)


def test_build_failed_result_has_none_decision():
    request = ReasonerRequest(
        request_id="req-9",
        image_path="/tmp/frame.png",
        frame_id="cam",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )
    result = build_failed_result(
        request=request,
        backend_id="mock",
        attempts=2,
        error_type="VLMOutputParseError",
        error_message="bad",
        raw_text="garbage",
    )
    assert result.decision is None
    assert result.raw_text == "garbage"
    assert result.diagnostics.parse_status == "failed"
    assert result.diagnostics.attempts == 2


_GOOD = (
    '{"congestion_detected": true, "type": "deadlock", '
    '"involved_robots": ["robot_1"], "root_cause": "x", '
    '"strategy": "yield", "justification": "y"}'
)
_BAD = "not json"


def _request_with_image(tmp_path) -> ReasonerRequest:
    image = tmp_path / "frame.png"
    image.write_bytes(b"\x89PNG\r\n")
    return ReasonerRequest(
        request_id="req-1",
        image_path=str(image),
        frame_id="cam",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )


def test_run_returns_decision_on_first_try(tmp_path):
    reasoner = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock"))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is not None
    assert result.decision.type == "deadlock"
    assert result.diagnostics.parse_status == "valid"
    assert result.diagnostics.attempts == 1


def test_run_records_no_decision_degradations_for_a_clean_answer(tmp_path):
    reasoner = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock"))
    assert reasoner.run(_request_with_image(tmp_path)).diagnostics.decision_degradations == []


def test_run_records_decision_degradations_without_a_reask(tmp_path):
    text = _GOOD[:-1] + ', "blocker_kind": "wall", "crossing_order": ["robot_9"]}'
    backend = MockBackend(response_text=text)
    result = Reasoner(backend, ReasonerConfig(backend_id="mock")).run(_request_with_image(tmp_path))
    assert result.decision is not None
    assert result.decision.blocker_kind is None and result.decision.crossing_order is None
    assert result.diagnostics.attempts == 1
    assert result.diagnostics.parse_status == "valid"
    assert result.diagnostics.decision_degradations == [
        "blocker_kind=default:invalid_label",
        "crossing_order=default:non_permutation",
    ]


def test_run_reasks_then_succeeds(tmp_path):
    backend = MockBackend(response_sequence=[_BAD, _GOOD])
    reasoner = Reasoner(backend, ReasonerConfig(backend_id="mock", max_attempts=2))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.attempts == 2
    assert result.diagnostics.parse_status == "invalid"


def test_run_exhausts_attempts_returns_none(tmp_path):
    backend = MockBackend(response_sequence=[_BAD, _BAD])
    reasoner = Reasoner(backend, ReasonerConfig(backend_id="mock", max_attempts=2))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is None
    assert result.diagnostics.parse_status == "failed"
    assert result.diagnostics.attempts == 2


def test_run_no_reask_when_disabled_exhausts_without_reasking(tmp_path):
    backend = MockBackend(response_text=_BAD)
    reasoner = Reasoner(
        backend, ReasonerConfig(backend_id="mock", max_attempts=2, allow_reask=False)
    )
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is None
    assert result.diagnostics.attempts == 2
    assert result.diagnostics.parse_status == "failed"
    assert "previous response was invalid" not in backend.last_payload.user_prompt


def test_run_timeout_then_success_is_valid(tmp_path):
    class FlakyTimeoutBackend:
        def __init__(self):
            self.calls = 0

        def analyze(self, payload, config):
            self.calls += 1
            if self.calls == 1:
                raise BackendTimeoutError("simulated transient timeout")
            return BackendResponse(text=_GOOD, backend_id="flaky")

    reasoner = Reasoner(FlakyTimeoutBackend(), ReasonerConfig(backend_id="flaky", max_attempts=2))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.parse_status == "valid"
    assert result.diagnostics.attempts == 2


def test_run_carries_token_usage(tmp_path):
    class UsageBackend:
        def analyze(self, payload, config):
            return BackendResponse(
                text=_GOOD, backend_id="usage", token_usage={"total_tokens": 5}
            )

    reasoner = Reasoner(UsageBackend(), ReasonerConfig(backend_id="usage"))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.diagnostics.token_usage == {"total_tokens": 5}


def test_run_rejects_duplicate_robot_ids(tmp_path):
    image = tmp_path / "frame.png"
    image.write_bytes(b"\x89PNG\r\n")
    request = ReasonerRequest(
        request_id="req-1",
        image_path=str(image),
        frame_id="cam",
        stamp=1.0,
        robot_states=[
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_1", x=1.0, y=1.0, theta=0.0),
        ],
    )
    with pytest.raises(ValueError):
        Reasoner(MockBackend(), ReasonerConfig(backend_id="mock")).run(request)


def test_run_rejects_missing_image():
    request = ReasonerRequest(
        request_id="req-1",
        image_path="/nonexistent/frame.png",
        frame_id="cam",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )
    with pytest.raises(FileNotFoundError):
        Reasoner(MockBackend(), ReasonerConfig(backend_id="mock")).run(request)


def test_run_unsupported_sampling_defaults_to_none_when_backend_reports_nothing(tmp_path):
    reasoner = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock"))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.diagnostics.unsupported_sampling is None


def test_run_carries_unsupported_sampling_from_backend_raw(tmp_path):
    class UnsupportedSamplingBackend:
        def analyze(self, payload, config):
            return BackendResponse(
                text=_GOOD,
                backend_id="gemini-like",
                raw={
                    "unsupported_sampling": {
                        "temperature": 0.6,
                        "top_p": 0.95,
                        "top_k": 20,
                        "presence_penalty": 0.0,
                    }
                },
            )

    reasoner = Reasoner(UnsupportedSamplingBackend(), ReasonerConfig(backend_id="gemini-like"))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.diagnostics.unsupported_sampling == {
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "presence_penalty": 0.0,
    }


def test_run_malformed_unsupported_sampling_value_becomes_none(tmp_path):
    class MalformedValueBackend:
        def analyze(self, payload, config):
            return BackendResponse(
                text=_GOOD, backend_id="malformed", raw={"unsupported_sampling": "not-a-dict"}
            )

    reasoner = Reasoner(MalformedValueBackend(), ReasonerConfig(backend_id="malformed"))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.diagnostics.unsupported_sampling is None


def test_run_unsupported_sampling_with_non_numeric_entries_becomes_none(tmp_path):
    class NonNumericEntriesBackend:
        def analyze(self, payload, config):
            return BackendResponse(
                text=_GOOD,
                backend_id="badvals",
                raw={"unsupported_sampling": {"temperature": "hot"}},
            )

    reasoner = Reasoner(NonNumericEntriesBackend(), ReasonerConfig(backend_id="badvals"))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.diagnostics.unsupported_sampling is None


def test_run_reask_then_success_preserves_unsupported_sampling(tmp_path):
    class ReaskUnsupportedSamplingBackend:
        def __init__(self):
            self.calls = 0

        def analyze(self, payload, config):
            self.calls += 1
            text = _BAD if self.calls == 1 else _GOOD
            return BackendResponse(
                text=text,
                backend_id="reask-gemini",
                raw={"unsupported_sampling": {"temperature": 0.6}},
            )

    reasoner = Reasoner(
        ReaskUnsupportedSamplingBackend(), ReasonerConfig(backend_id="reask-gemini", max_attempts=2)
    )
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.parse_status == "invalid"
    assert result.diagnostics.unsupported_sampling == {"temperature": 0.6}


def test_run_exhausted_retries_preserves_unsupported_sampling_from_last_attempt(tmp_path):
    class AlwaysInvalidUnsupportedSamplingBackend:
        def analyze(self, payload, config):
            return BackendResponse(
                text=_BAD,
                backend_id="always-bad-gemini",
                raw={"unsupported_sampling": {"temperature": 0.6}},
            )

    reasoner = Reasoner(
        AlwaysInvalidUnsupportedSamplingBackend(),
        ReasonerConfig(backend_id="always-bad-gemini", max_attempts=2),
    )
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is None
    assert result.diagnostics.unsupported_sampling == {"temperature": 0.6}


def test_build_failed_result_carries_unsupported_sampling():
    request = ReasonerRequest(
        request_id="req-9",
        image_path="/tmp/frame.png",
        frame_id="cam",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )
    result = build_failed_result(
        request=request,
        backend_id="mock",
        attempts=2,
        error_type="VLMOutputParseError",
        error_message="bad",
        raw_text="garbage",
        unsupported_sampling={"temperature": 0.6},
    )
    assert result.diagnostics.unsupported_sampling == {"temperature": 0.6}


def test_write_reasoner_log_includes_unsupported_sampling_when_present(tmp_path):
    class UnsupportedSamplingBackend:
        def analyze(self, payload, config):
            return BackendResponse(
                text=_GOOD,
                backend_id="gemini-like",
                raw={"unsupported_sampling": {"temperature": 0.6}},
            )

    log = tmp_path / "trace.jsonl"
    reasoner = Reasoner(UnsupportedSamplingBackend(), ReasonerConfig(backend_id="gemini-like"))
    result = reasoner.run(_request_with_image(tmp_path))
    write_reasoner_log(log, _request_with_image(tmp_path), result)
    record = json.loads(log.read_text().strip().splitlines()[0])
    assert record["unsupported_sampling"] == {"temperature": 0.6}


def test_write_reasoner_log_omits_unsupported_sampling_when_none(tmp_path):
    log = tmp_path / "trace.jsonl"
    reasoner = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock"))
    result = reasoner.run(_request_with_image(tmp_path))
    write_reasoner_log(log, _request_with_image(tmp_path), result)
    record = json.loads(log.read_text().strip().splitlines()[0])
    assert "unsupported_sampling" not in record


def test_write_reasoner_log_appends_jsonl(tmp_path):
    log = tmp_path / "trace.jsonl"
    reasoner = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock"))
    result = reasoner.run(_request_with_image(tmp_path))
    write_reasoner_log(log, _request_with_image(tmp_path), result)
    write_reasoner_log(log, _request_with_image(tmp_path), result)
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2
    record = json.loads(lines[0])
    assert record["request_id"] == "req-1"
    assert record["parse_status"] == "valid"


def test_llama_backend_orders_image_before_text(tmp_path):
    image = tmp_path / "frame.png"
    image.write_bytes(b"\x89PNG\r\n")
    backend = LlamaServerBackend(model_id="cosmos", mmproj_path="/models/mmproj.gguf")
    payload = PromptPayload(
        system_prompt="sys",
        user_prompt="usr",
        image_path=str(image),
        known_robot_ids=["robot_1"],
    )
    messages = backend._build_messages(payload)
    content = messages[1]["content"]
    # Media-first: image part precedes the text part (Cosmos Reason 2 convention).
    assert content[0]["type"] == "image_url"
    assert content[1]["type"] == "text"


def test_llama_backend_body_allows_reasoning_and_sends_sampling(tmp_path, monkeypatch):
    image = tmp_path / "frame.png"
    image.write_bytes(b"\x89PNG\r\n")
    backend = LlamaServerBackend(model_id="cosmos", mmproj_path="/models/mmproj.gguf")
    payload = PromptPayload(
        system_prompt="sys",
        user_prompt="usr",
        image_path=str(image),
        known_robot_ids=["robot_1"],
    )
    captured: dict = {}

    class _Resp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": _GOOD}}]}

    def _fake_post(url, json, timeout):  # noqa: A002 - mirrors requests.post signature
        captured.update(json)
        return _Resp()

    monkeypatch.setattr("reasoning.vlm.llama_server_backend.requests.post", _fake_post)
    backend.analyze(payload, ReasonerConfig(backend_id="llama_server"))

    # json_object response_format would suppress the <think> trace, so it must be absent.
    assert "response_format" not in captured
    assert captured["top_p"] == 0.95
    assert captured["top_k"] == 20
    assert captured["presence_penalty"] == 0.0


def test_build_backend_returns_mock_without_config():
    backend = build_backend("mock")
    assert isinstance(backend, VLMBackend)


def test_build_backend_llama_server_requires_config():
    with pytest.raises(ValueError):
        build_backend("llama_server")


def test_build_backend_returns_llama_server():
    config = LlamaServerBackendConfig(model_id="cosmos", base_url="http://127.0.0.1:8080/v1")
    backend = build_backend("llama_server", config)
    assert isinstance(backend, LlamaServerBackend)
    assert isinstance(backend, VLMBackend)


def test_build_backend_rejects_unknown_id():
    with pytest.raises(ValueError):
        build_backend("nope", LlamaServerBackendConfig(model_id="x"))


def test_build_backend_mock_returns_default_when_env_unset(monkeypatch):
    monkeypatch.delenv("VGU_MOCK_DECISION_FILE", raising=False)
    response = build_backend("mock").analyze(_PAYLOAD, _CONFIG)
    assert '"congestion_detected": false' in response.text


def test_build_backend_mock_uses_scripted_decision_file(tmp_path, monkeypatch):
    text = '{"congestion_detected": true, "strategy": "yield"}'
    decision_file = tmp_path / "scripted.json"
    decision_file.write_text(text, encoding="utf-8")
    monkeypatch.setenv("VGU_MOCK_DECISION_FILE", str(decision_file))
    backend = build_backend("mock")

    responses = [backend.analyze(_PAYLOAD, _CONFIG).text for _ in range(3)]

    assert responses == [text, text, text]


def test_build_backend_mock_missing_decision_file_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("VGU_MOCK_DECISION_FILE", str(tmp_path / "absent.json"))
    with pytest.raises(FileNotFoundError, match="VGU_MOCK_DECISION_FILE"):
        build_backend("mock")


def test_build_backend_mock_sequence_file_replays_entries_then_holds_last(
    tmp_path, monkeypatch
):
    first = {"congestion_detected": True, "strategy": "yield"}
    second = {"congestion_detected": False, "strategy": "none"}
    decision_file = tmp_path / "scripted_sequence.json"
    decision_file.write_text(json.dumps([first, second]), encoding="utf-8")
    monkeypatch.setenv("VGU_MOCK_DECISION_FILE", str(decision_file))
    backend = build_backend("mock")

    responses = [backend.analyze(_PAYLOAD, _CONFIG).text for _ in range(10)]

    assert json.loads(responses[0]) == first
    assert json.loads(responses[1]) == second
    assert json.loads(responses[2]) == second
    assert json.loads(responses[9]) == second


def test_build_backend_mock_empty_sequence_file_raises(tmp_path, monkeypatch):
    decision_file = tmp_path / "empty_sequence.json"
    decision_file.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("VGU_MOCK_DECISION_FILE", str(decision_file))

    with pytest.raises(ValueError, match=re.escape(str(decision_file))):
        build_backend("mock")


def test_head_on_yield_fixture_validates_against_schema():
    repo_root = Path(__file__).resolve().parents[2]
    fixture = repo_root / "config" / "mock_decisions" / "head_on_yield.json"
    document = json.loads(fixture.read_text(encoding="utf-8"))
    validator = Draft202012Validator(load_schema("vlm_decision"))
    assert not list(validator.iter_errors(document))


def test_public_api_is_importable_from_package():
    from reasoning.vlm import (
        CongestionDecision,
        MockBackend,
        Reasoner,
        ReasonerConfig,
        ReasonerRequest,
        ReasonerResult,
        build_backend,
    )

    assert Reasoner is not None
    assert build_backend is not None
    assert CongestionDecision is not None
    assert MockBackend is not None
    assert ReasonerConfig is not None
    assert ReasonerRequest is not None
    assert ReasonerResult is not None


def _openai_effective() -> EffectiveSamplingConfig:
    """The effective block M5 builds for the shipped `openai` backend section."""
    raw = yaml.safe_load(Path("config/models.yaml").read_text())["vlm"]
    return describe_effective_sampling(
        resolve_reasoner_config(raw, "openai"),
        OpenAIBackendConfig(**backend_section(raw, "openai")),
    )


def test_run_records_effective_sampling_config_when_described(tmp_path):
    effective = _openai_effective()
    reasoner = Reasoner(
        MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="openai"), effective
    )
    result = reasoner.run(_request_with_image(tmp_path))
    recorded = result.diagnostics.reasoner_config_effective
    assert recorded is not None
    assert recorded.model_id == "gpt-4o"
    assert recorded.temperature == 0.0
    assert recorded.max_attempts == 4
    assert recorded.image_fallback_after_attempts == 2
    assert recorded.unsupported_sampling is None


def test_run_effective_sampling_config_is_none_when_not_described(tmp_path):
    reasoner = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock"))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.diagnostics.reasoner_config_effective is None


def test_run_effective_sampling_config_carries_unsupported_fields(tmp_path):
    class UnsupportedSamplingBackend:
        def analyze(self, payload, config):
            return BackendResponse(
                text=_GOOD,
                backend_id="gemini-like",
                raw={"unsupported_sampling": {"temperature": 0.6, "top_p": 0.95}},
            )

    config = ReasonerConfig(backend_id="gemini")
    effective = describe_effective_sampling(config, GeminiBackendConfig(seed=7))
    result = Reasoner(UnsupportedSamplingBackend(), config, effective).run(
        _request_with_image(tmp_path)
    )
    recorded = result.diagnostics.reasoner_config_effective
    assert recorded is not None
    assert recorded.thinking_level == "low"
    assert recorded.seed == 7
    assert recorded.temperature == 0.6
    assert recorded.unsupported_sampling == {"temperature": 0.6, "top_p": 0.95}


def test_run_exhausted_retries_still_records_effective_sampling_config(tmp_path):
    reasoner = Reasoner(
        MockBackend(response_text=_BAD),
        ReasonerConfig(backend_id="openai", max_attempts=2),
        _openai_effective(),
    )
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is None
    assert result.diagnostics.reasoner_config_effective is not None
    assert result.diagnostics.reasoner_config_effective.temperature == 0.0


def test_write_reasoner_log_includes_effective_sampling_config_when_present(tmp_path):
    log = tmp_path / "trace.jsonl"
    reasoner = Reasoner(
        MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="openai"), _openai_effective()
    )
    result = reasoner.run(_request_with_image(tmp_path))
    write_reasoner_log(log, _request_with_image(tmp_path), result)
    record = json.loads(log.read_text().strip().splitlines()[0])
    assert record["reasoner_config_effective"]["temperature"] == 0.0
    assert record["reasoner_config_effective"]["max_attempts"] == 4
    assert record["reasoner_config_effective"]["image_fallback_after_attempts"] == 2
    assert record["reasoner_config_effective"]["model_id"] == "gpt-4o"


def test_write_reasoner_log_omits_effective_sampling_config_when_none(tmp_path):
    log = tmp_path / "trace.jsonl"
    reasoner = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock"))
    result = reasoner.run(_request_with_image(tmp_path))
    write_reasoner_log(log, _request_with_image(tmp_path), result)
    record = json.loads(log.read_text().strip().splitlines()[0])
    assert "reasoner_config_effective" not in record


_REFUSAL = "I'm sorry, I can't assist with that."
_REFUSAL_BUT = "I'm sorry, but I can't assist with that."
_REFUSAL_HELP = "I can't help with that request."


def test_is_refusal_matches_plain_sorry_variant():
    assert is_refusal(_REFUSAL)


def test_is_refusal_matches_but_variant():
    assert is_refusal(_REFUSAL_BUT)


def test_is_refusal_matches_generic_cannot_help_variant():
    assert is_refusal(_REFUSAL_HELP)


def test_is_refusal_matches_typographic_apostrophe():
    assert is_refusal("I’m sorry, I can’t assist with that.")


def test_is_refusal_rejects_a_valid_decision():
    assert not is_refusal(_GOOD)


def test_is_refusal_rejects_apology_inside_an_answer():
    assert not is_refusal("Sorry for the delay; robot_1 should yield to robot_2.")


def test_is_refusal_rejects_empty_text():
    assert not is_refusal("")


class _RecordingBackend:
    """Backend that replays a script and keeps every payload it was handed."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.payloads: list[PromptPayload] = []
        self.image_sizes: list[tuple[int, int] | None] = []
        self.image_pixels: list[tuple[int, int, int] | None] = []

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        self.payloads.append(payload)
        # The neutral image lives in a scratch directory deleted when `run`
        # returns, so it has to be inspected here rather than afterwards.
        try:
            with Image.open(payload.image_path) as image:
                rgb = image.convert("RGB")
                self.image_sizes.append(rgb.size)
                self.image_pixels.append(rgb.getpixel((0, 0)))
        except OSError:
            self.image_sizes.append(None)
            self.image_pixels.append(None)
        index = min(len(self.payloads) - 1, len(self._responses) - 1)
        return BackendResponse(text=self._responses[index], backend_id="recording")


def _request_with_real_png(tmp_path, size: tuple[int, int] = (64, 48)) -> ReasonerRequest:
    image = tmp_path / "frame.png"
    Image.new("RGB", size, (10, 200, 30)).save(image)
    return ReasonerRequest(
        request_id="req-fallback",
        image_path=str(image),
        frame_id="cam",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )


def _fallback_config(**overrides) -> ReasonerConfig:
    return ReasonerConfig(
        backend_id="recording", max_attempts=4, image_fallback_after_attempts=2, **overrides
    )


def test_make_neutral_image_matches_source_dimensions(tmp_path):
    source = tmp_path / "frame.png"
    Image.new("RGB", (32, 17), (1, 2, 3)).save(source)
    neutral = make_neutral_image(source, tmp_path / "neutral.png")
    with Image.open(neutral) as image:
        assert image.size == (32, 17)
        assert image.convert("RGB").getpixel((5, 5)) == (128, 128, 128)


def test_run_image_fallback_fires_on_the_attempt_after_the_threshold(tmp_path):
    backend = _RecordingBackend([_REFUSAL, _REFUSAL, _GOOD])
    result = Reasoner(backend, _fallback_config()).run(_request_with_real_png(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.attempts == 3
    assert result.diagnostics.refusal_attempts == 2
    assert result.diagnostics.image_fallback_used is True
    assert result.diagnostics.image_fallback_attempt == 3


def test_run_image_fallback_sends_a_neutral_image_of_the_frame_size(tmp_path):
    backend = _RecordingBackend([_REFUSAL, _REFUSAL, _GOOD])
    Reasoner(backend, _fallback_config()).run(_request_with_real_png(tmp_path, (64, 48)))
    assert backend.image_pixels[0] == (10, 200, 30)
    assert backend.image_pixels[2] == (128, 128, 128)
    assert backend.image_sizes[2] == (64, 48)
    assert backend.payloads[2].image_path != backend.payloads[0].image_path


def test_run_image_fallback_omits_the_reask_suffix(tmp_path):
    backend = _RecordingBackend([_REFUSAL, _REFUSAL, _GOOD])
    Reasoner(backend, _fallback_config()).run(_request_with_real_png(tmp_path))
    assert "previous response was invalid" in backend.payloads[1].user_prompt
    assert backend.payloads[2].user_prompt == backend.payloads[0].user_prompt


def test_run_image_fallback_fires_only_once_per_request(tmp_path):
    backend = _RecordingBackend([_REFUSAL])
    result = Reasoner(backend, _fallback_config()).run(_request_with_real_png(tmp_path))
    assert result.decision is None
    assert result.diagnostics.attempts == 4
    assert result.diagnostics.refusal_attempts == 4
    assert result.diagnostics.image_fallback_attempt == 3
    # Attempt 4 re-asks on top of the neutral-image payload rather than swapping again.
    assert backend.image_pixels[3] == (128, 128, 128)
    assert "previous response was invalid" in backend.payloads[3].user_prompt


def test_run_image_fallback_ignores_a_non_refusal_parse_failure(tmp_path):
    backend = _RecordingBackend([_BAD, _BAD, _GOOD])
    result = Reasoner(backend, _fallback_config()).run(_request_with_real_png(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.refusal_attempts == 0
    assert result.diagnostics.image_fallback_used is False
    assert backend.payloads[2].image_path == backend.payloads[0].image_path


def test_run_image_fallback_disabled_by_default_keeps_reasking(tmp_path):
    backend = _RecordingBackend([_REFUSAL])
    config = ReasonerConfig(backend_id="recording", max_attempts=4)
    result = Reasoner(backend, config).run(_request_with_real_png(tmp_path))
    assert config.image_fallback_after_attempts is None
    assert result.decision is None
    assert result.diagnostics.image_fallback_used is False
    assert result.diagnostics.image_fallback_attempt is None
    assert result.diagnostics.refusal_attempts == 4
    assert {p.image_path for p in backend.payloads} == {backend.payloads[0].image_path}


def test_run_image_fallback_degrades_to_reask_when_the_frame_is_unreadable(tmp_path):
    backend = _RecordingBackend([_REFUSAL, _REFUSAL, _GOOD])
    # `_request_with_image` writes a truncated PNG header that PIL cannot open.
    result = Reasoner(backend, _fallback_config()).run(_request_with_image(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.image_fallback_used is False
    assert "previous response was invalid" in backend.payloads[2].user_prompt


def test_write_reasoner_log_includes_image_fallback_when_it_fired(tmp_path):
    log = tmp_path / "trace.jsonl"
    request = _request_with_real_png(tmp_path)
    backend = _RecordingBackend([_REFUSAL, _REFUSAL, _GOOD])
    result = Reasoner(backend, _fallback_config()).run(request)
    write_reasoner_log(log, request, result)
    record = json.loads(log.read_text().strip().splitlines()[0])
    assert record["image_fallback_used"] is True
    assert record["image_fallback_attempt"] == 3
    assert record["refusal_attempts"] == 2


def test_write_reasoner_log_omits_image_fallback_without_a_refusal(tmp_path):
    log = tmp_path / "trace.jsonl"
    request = _request_with_image(tmp_path)
    result = Reasoner(
        MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock")
    ).run(request)
    write_reasoner_log(log, request, result)
    record = json.loads(log.read_text().strip().splitlines()[0])
    assert "image_fallback_used" not in record
    assert "refusal_attempts" not in record


def _served_backend(texts: list[str], served_model: str | None):
    class ServedModelBackend:
        def __init__(self) -> None:
            self._texts = list(texts)

        def analyze(self, payload, config):
            return BackendResponse(
                text=self._texts.pop(0), backend_id="gpt-4o", served_model=served_model
            )

    return ServedModelBackend()


def test_llama_backend_served_model_read_from_response(tmp_path, monkeypatch):
    image = tmp_path / "frame.png"
    image.write_bytes(b"\x89PNG\r\n")
    backend = LlamaServerBackend(model_id="cosmos", mmproj_path="/models/mmproj.gguf")
    payload = PromptPayload(
        system_prompt="sys", user_prompt="usr", image_path=str(image), known_robot_ids=["r"]
    )

    class _Resp:
        status_code = 200

        def json(self):
            return {"model": "cosmos-reason2-8b", "choices": [{"message": {"content": _GOOD}}]}

    monkeypatch.setattr(
        "reasoning.vlm.llama_server_backend.requests.post",
        lambda url, json, timeout: _Resp(),
    )
    resp = backend.analyze(payload, ReasonerConfig(backend_id="llama_server"))
    assert resp.served_model == "cosmos-reason2-8b"


def test_mock_backend_reports_no_served_model(tmp_path):
    result = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock")).run(
        _request_with_image(tmp_path)
    )
    assert result.diagnostics.served_model is None


def test_describe_effective_sampling_leaves_served_model_unset():
    assert _openai_effective().served_model is None


def test_run_records_served_model_in_diagnostics_and_effective_config(tmp_path):
    reasoner = Reasoner(
        _served_backend([_GOOD], "gpt-4o-2024-08-06"),
        ReasonerConfig(backend_id="openai"),
        _openai_effective(),
    )
    result = reasoner.run(_request_with_image(tmp_path))
    effective = result.diagnostics.reasoner_config_effective
    assert result.diagnostics.served_model == "gpt-4o-2024-08-06"
    assert effective.model_id == "gpt-4o"
    assert effective.served_model == "gpt-4o-2024-08-06"


def test_run_records_served_model_when_every_attempt_fails(tmp_path):
    reasoner = Reasoner(
        _served_backend([_BAD, _BAD], "gpt-4o-2024-08-06"),
        ReasonerConfig(backend_id="openai", max_attempts=2),
        _openai_effective(),
    )
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is None
    assert result.diagnostics.served_model == "gpt-4o-2024-08-06"
    assert result.diagnostics.reasoner_config_effective.served_model == "gpt-4o-2024-08-06"


def test_write_reasoner_log_includes_served_model_when_reported(tmp_path):
    request = _request_with_image(tmp_path)
    result = Reasoner(
        _served_backend([_GOOD], "gpt-4o-2024-08-06"), ReasonerConfig(backend_id="openai")
    ).run(request)
    log = tmp_path / "trace.jsonl"
    write_reasoner_log(log, request, result)
    assert json.loads(log.read_text())["served_model"] == "gpt-4o-2024-08-06"


def test_write_reasoner_log_omits_served_model_when_unreported(tmp_path):
    request = _request_with_image(tmp_path)
    result = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock")).run(
        request
    )
    log = tmp_path / "trace.jsonl"
    write_reasoner_log(log, request, result)
    assert "served_model" not in json.loads(log.read_text())

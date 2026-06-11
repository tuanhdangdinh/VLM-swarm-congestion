import json
import time

import pytest

from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    BackendResponse,
    LlamaServerBackendConfig,
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


def test_invoke_backend_fills_latency_when_missing():
    backend = MockBackend(response_text="{}", latency_ms=0)
    response = invoke_backend(backend, _PAYLOAD, ReasonerConfig(backend_id="mock"))
    assert response.latency_ms is not None and response.latency_ms >= 0


def test_invoke_backend_raises_on_timeout():
    class SlowBackend:
        def analyze(self, payload, config):
            time.sleep(0.2)
            return BackendResponse(text="{}", backend_id="slow")

    config = ReasonerConfig(backend_id="slow", timeout_sec=0.01)
    with pytest.raises(BackendTimeoutError):
        invoke_backend(SlowBackend(), _PAYLOAD, config)


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


def test_write_reasoner_log_appends_jsonl(tmp_path):
    log = tmp_path / "trace.jsonl"
    reasoner = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock"))
    result = reasoner.run(_request_with_image(tmp_path))
    write_reasoner_log(log, _request_with_image(tmp_path), result)
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["request_id"] == "req-1"
    assert record["parse_status"] == "valid"

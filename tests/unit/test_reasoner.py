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
    build_failed_result,
    build_reask_prompt,
    invoke_backend,
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

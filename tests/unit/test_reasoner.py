from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    BackendResponse,
    LlamaServerBackendConfig,
    PromptPayload,
    ReasonerConfig,
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

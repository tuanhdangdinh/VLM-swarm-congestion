"""Unit tests for resolving the VLM reasoner config with per-backend overrides."""
from __future__ import annotations

from pathlib import Path

import yaml

from reasoning.vlm.backend_factory import (
    backend_section,
    describe_effective_sampling,
    resolve_reasoner_config,
)
from reasoning.vlm.models import (
    EffectiveSamplingConfig,
    GeminiBackendConfig,
    LlamaServerBackendConfig,
    OpenAIBackendConfig,
    ReasonerConfig,
)


def _raw_vlm() -> dict:
    return {
        "reasoner": {"timeout_sec": 120, "temperature": 0.6, "top_p": 0.95, "top_k": 20},
        "llama_server": {"base_url": "http://127.0.0.1:8080/v1", "model_id": "cosmos"},
        "openai": {"model_id": "gpt-4o", "reasoner": {"temperature": 0.0}},
    }


def test_resolve_reasoner_config_applies_backend_specific_sampling_override():
    config = resolve_reasoner_config(_raw_vlm(), "openai")
    assert config.backend_id == "openai"
    assert config.temperature == 0.0
    assert config.top_p == 0.95


def test_resolve_reasoner_config_keeps_shared_sampling_without_override():
    config = resolve_reasoner_config(_raw_vlm(), "llama_server")
    assert config.temperature == 0.6
    assert config.timeout_sec == 120


def test_backend_section_strips_the_reasoner_override():
    assert backend_section(_raw_vlm(), "openai") == {"model_id": "gpt-4o"}
    assert backend_section(_raw_vlm(), "mock") == {}


def test_shipped_models_yaml_samples_greedily_for_openai_only():
    raw = yaml.safe_load(Path("config/models.yaml").read_text())["vlm"]
    assert resolve_reasoner_config(raw, "openai").temperature == 0.0
    assert resolve_reasoner_config(raw, "llama_server").temperature == 0.6


def test_shipped_models_yaml_overrides_max_attempts_for_openai_only():
    raw = yaml.safe_load(Path("config/models.yaml").read_text())["vlm"]
    assert resolve_reasoner_config(raw, "openai").max_attempts == 4
    assert resolve_reasoner_config(raw, "gemini").max_attempts == 2


def test_shipped_models_yaml_enables_image_fallback_for_openai_only():
    raw = yaml.safe_load(Path("config/models.yaml").read_text())["vlm"]
    assert resolve_reasoner_config(raw, "openai").image_fallback_after_attempts == 2
    assert resolve_reasoner_config(raw, "gemini").image_fallback_after_attempts is None
    assert resolve_reasoner_config(raw, "llama_server").image_fallback_after_attempts is None


def _shipped_vlm() -> dict:
    return yaml.safe_load(Path("config/models.yaml").read_text())["vlm"]


def _shipped_effective(backend_id: str, backend_config=None):
    return describe_effective_sampling(
        resolve_reasoner_config(_shipped_vlm(), backend_id), backend_config
    )


def test_describe_effective_sampling_records_shipped_openai_greedy_preset():
    effective = _shipped_effective(
        "openai", OpenAIBackendConfig(**backend_section(_shipped_vlm(), "openai"))
    )
    assert effective.backend_id == "openai"
    assert effective.model_id == "gpt-4o-2024-08-06"
    assert effective.temperature == 0.0
    assert effective.max_attempts == 4
    assert effective.image_fallback_after_attempts == 2
    assert effective.top_p == 0.95
    assert effective.max_tokens == 2048
    assert effective.unsupported_sampling is None


def test_describe_effective_sampling_records_shipped_gemini_thinking_level():
    effective = _shipped_effective(
        "gemini", GeminiBackendConfig(**backend_section(_shipped_vlm(), "gemini"))
    )
    assert effective.model_id == "gemini-robotics-er-2-preview"
    assert effective.thinking_level == "low"
    assert effective.seed is None
    # No gemini reasoner: override, so the shared Cosmos preset is what the
    # ReasonerConfig carries — recorded as configured even though the
    # Interactions API drops it (see unsupported_sampling).
    assert effective.temperature == 0.6
    assert effective.max_attempts == 2
    assert effective.image_fallback_after_attempts is None


def test_describe_effective_sampling_omits_model_id_without_backend_config():
    effective = describe_effective_sampling(ReasonerConfig(backend_id="mock"))
    assert effective.backend_id == "mock"
    assert effective.model_id is None
    assert effective.seed is None
    assert effective.thinking_level is None


def test_describe_effective_sampling_leaves_seed_unset_for_non_gemini_backend():
    effective = describe_effective_sampling(
        ReasonerConfig(backend_id="llama_server"),
        LlamaServerBackendConfig(model_id="cosmos-reason2-8b"),
    )
    assert effective.model_id == "cosmos-reason2-8b"
    assert effective.seed is None
    assert effective.thinking_level is None


def test_describe_effective_sampling_records_shipped_llama_server_image_fallback_off():
    effective = _shipped_effective(
        "llama_server",
        LlamaServerBackendConfig(**backend_section(_shipped_vlm(), "llama_server")),
    )
    assert effective.image_fallback_after_attempts is None


def test_effective_sampling_config_parses_block_recorded_before_image_fallback_field():
    recorded = describe_effective_sampling(ReasonerConfig(backend_id="mock")).model_dump(
        mode="json"
    )
    del recorded["image_fallback_after_attempts"]
    assert EffectiveSamplingConfig(**recorded).image_fallback_after_attempts is None

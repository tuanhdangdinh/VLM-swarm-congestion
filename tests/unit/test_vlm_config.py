"""Unit tests for resolving the VLM reasoner config with per-backend overrides."""
from __future__ import annotations

from pathlib import Path

import yaml

from reasoning.vlm.backend_factory import backend_section, resolve_reasoner_config


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

import json
import os
from pathlib import Path

from reasoning.vlm.anthropic_backend import AnthropicBackend
from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.gemini_backend import GeminiBackend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    AnthropicBackendConfig,
    EffectiveSamplingConfig,
    GeminiBackendConfig,
    LlamaServerBackendConfig,
    OpenAIBackendConfig,
    ReasonerConfig,
)
from reasoning.vlm.openai_backend import OpenAIBackend

BackendConfig = (
    LlamaServerBackendConfig | OpenAIBackendConfig | AnthropicBackendConfig | GeminiBackendConfig
)


def resolve_reasoner_config(raw_vlm: dict, backend_id: str) -> ReasonerConfig:
    """Build the reasoner config for one backend from the `vlm:` mapping of models.yaml.

    The shared `reasoner:` block supplies defaults; a `reasoner:` mapping nested
    under the backend's own section overrides them, so a chain-of-thought model
    can keep its sampling preset while a classifier backend samples greedily.

    Args:
        raw_vlm: The parsed `vlm:` mapping.
        backend_id: Backend whose config is wanted, e.g. "openai".

    Returns:
        A `ReasonerConfig` with `backend_id` set and overrides applied.
    """
    merged = dict(raw_vlm.get("reasoner", {}))
    merged.update(dict((raw_vlm.get(backend_id) or {}).get("reasoner", {})))
    merged["backend_id"] = backend_id
    return ReasonerConfig(**merged)


def describe_effective_sampling(
    reasoner_config: ReasonerConfig,
    backend_config: BackendConfig | None = None,
) -> EffectiveSamplingConfig:
    """Summarize the sampling settings one backend call will actually run under.

    Reads the configured values off the two config objects rather than off a
    constructed backend: every hosted backend requires its API key at
    construction, so the config objects are the only source available offline,
    and they are also the source of truth ("as configured", never
    provider-echoed).

    Args:
        reasoner_config: The resolved per-backend `ReasonerConfig`.
        backend_config: The backend's own config, or None for a backend that
            needs none (e.g. "mock"); `seed` and `thinking_level` are read only
            from a `GeminiBackendConfig`, being the only API that honours them.

    Returns:
        The effective sampling block, with `unsupported_sampling` left unset —
        that is a per-call fact the `Reasoner` fills in from the response.
    """
    is_gemini = isinstance(backend_config, GeminiBackendConfig)
    return EffectiveSamplingConfig(
        backend_id=reasoner_config.backend_id,
        model_id=getattr(backend_config, "model_id", None),
        temperature=reasoner_config.temperature,
        top_p=reasoner_config.top_p,
        top_k=reasoner_config.top_k,
        presence_penalty=reasoner_config.presence_penalty,
        max_attempts=reasoner_config.max_attempts,
        max_tokens=reasoner_config.max_tokens,
        seed=backend_config.seed if is_gemini else None,
        thinking_level=backend_config.thinking_level if is_gemini else None,
    )


def backend_section(raw_vlm: dict, backend_id: str) -> dict:
    """Return a backend's own config mapping without its nested reasoner override."""
    section = dict(raw_vlm.get(backend_id) or {})
    section.pop("reasoner", None)
    return section


def build_backend(
    backend_id: str,
    backend_config: BackendConfig | None = None,
) -> VLMBackend:
    """Construct a concrete VLM backend from its identifier and config.

    For `backend_id == "mock"`, the `VGU_MOCK_DECISION_FILE` environment
    variable may name a file holding either a single JSON decision object,
    whose UTF-8 text becomes the backend's scripted response, or a JSON
    array of decision objects, which becomes a scripted sequence: the
    backend replays each entry in order and holds the last entry for every
    call after the sequence is exhausted. This lets key-less closed-loop
    runs replay a specific decision (e.g.
    `config/mock_decisions/head_on_yield.json`) or a short scripted scene
    (e.g. `config/mock_decisions/head_on_yield_once.json`) instead of the
    default no-congestion answer. Unset or empty keeps the default
    behaviour.

    Args:
        backend_id: Selector, e.g. "mock" or "llama_server".
        backend_config: Backend-specific connection config. Optional because
            "mock" needs none; backends that require it raise on absence.

    Returns:
        A backend instance satisfying the `VLMBackend` Protocol.

    Raises:
        ValueError: If `backend_id` is not recognized, required config is
            missing for a backend that needs it, or `VGU_MOCK_DECISION_FILE`
            names a file containing an empty JSON array.
        FileNotFoundError: If `VGU_MOCK_DECISION_FILE` names a path that does
            not exist. Config errors fail fast at startup by convention.
    """
    if backend_id == "mock":
        decision_file = os.environ.get("VGU_MOCK_DECISION_FILE", "")
        if not decision_file:
            return MockBackend()
        path = Path(decision_file)
        if not path.exists():
            raise FileNotFoundError(
                f"VGU_MOCK_DECISION_FILE points to a missing file: {path}"
            )
        text = path.read_text(encoding="utf-8")
        parsed = json.loads(text)
        if isinstance(parsed, list):
            if not parsed:
                raise ValueError(
                    f"VGU_MOCK_DECISION_FILE names an empty decision array: {path}"
                )
            return MockBackend(response_sequence=[json.dumps(item) for item in parsed])
        return MockBackend(response_text=text)
    if backend_id == "llama_server":
        if backend_config is None:
            raise ValueError("llama_server backend requires a LlamaServerBackendConfig")
        return LlamaServerBackend(
            base_url=backend_config.base_url,
            model_id=backend_config.model_id,
            mmproj_path=backend_config.mmproj_path,
        )
    if backend_id == "openai":
        if backend_config is None:
            backend_config = OpenAIBackendConfig()
        return OpenAIBackend(
            model_id=backend_config.model_id,
            base_url=backend_config.base_url,
            api_key_env=backend_config.api_key_env,
            organization=backend_config.organization,
        )
    if backend_id == "anthropic":
        if backend_config is None:
            raise ValueError("anthropic backend requires an AnthropicBackendConfig")
        return AnthropicBackend(
            model_id=backend_config.model_id,
            base_url=backend_config.base_url,
            api_key_env=backend_config.api_key_env,
        )
    if backend_id == "gemini":
        if backend_config is None:
            backend_config = GeminiBackendConfig()
        return GeminiBackend(
            model_id=backend_config.model_id,
            base_url=backend_config.base_url,
            api_key_env=backend_config.api_key_env,
            thinking_level=backend_config.thinking_level,
            force_schema=backend_config.force_schema,
            seed=backend_config.seed,
        )
    raise ValueError(f"Unknown backend_id: {backend_id!r}")

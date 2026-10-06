import json
import os
from pathlib import Path

from pydantic import BaseModel

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

# The adapter (transport) each config type drives. A `models.yaml` backend
# section is named by its backend id; the section's own `adapter:` key picks
# the transport, defaulting to the section name, so one adapter can serve
# several pinned arms (e.g. `openai` = gpt-4o, `openai_gpt51` = gpt-5.1).
# `None` means the adapter takes no config ("mock").
BACKEND_CONFIG_TYPES: dict[str, type[BaseModel] | None] = {
    "mock": None,
    "llama_server": LlamaServerBackendConfig,
    "openai": OpenAIBackendConfig,
    "anthropic": AnthropicBackendConfig,
    "gemini": GeminiBackendConfig,
}


def backend_adapter(raw_vlm: dict, backend_id: str) -> str:
    """Return the adapter (transport) a configured backend id runs on.

    Args:
        raw_vlm: The parsed `vlm:` mapping of `config/models.yaml`.
        backend_id: A backend section name, e.g. "openai" or "openai_gpt51".

    Returns:
        One of the keys of `BACKEND_CONFIG_TYPES`.

    Raises:
        ValueError: The section names an unknown adapter, or the id has no
            section and is not itself an adapter name.
    """
    section = raw_vlm.get(backend_id) or {}
    adapter = section.get("adapter", backend_id)
    if adapter not in BACKEND_CONFIG_TYPES:
        raise ValueError(
            f"backend {backend_id!r} names unknown adapter {adapter!r}; "
            f"known: {sorted(BACKEND_CONFIG_TYPES)}"
        )
    return adapter


def load_backend_config(raw_vlm: dict, backend_id: str) -> BackendConfig | None:
    """Build the typed backend config for one configured backend id.

    Args:
        raw_vlm: The parsed `vlm:` mapping of `config/models.yaml`.
        backend_id: A backend section name.

    Returns:
        The adapter's config model, or None for an adapter that takes none.

    Raises:
        ValueError: Unknown adapter (see `backend_adapter`).
        pydantic.ValidationError: The section does not fit its adapter's model.
    """
    config_type = BACKEND_CONFIG_TYPES[backend_adapter(raw_vlm, backend_id)]
    if config_type is None:
        return None
    return config_type(**backend_section(raw_vlm, backend_id))


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
        The effective sampling block, with `unsupported_sampling` and
        `served_model` left unset — those are per-call facts the `Reasoner`
        fills in from the response.
    """
    is_gemini = isinstance(backend_config, GeminiBackendConfig)
    reasoning_effort = (
        backend_config.reasoning_effort if isinstance(backend_config, OpenAIBackendConfig) else None
    )
    thinking_mode = (
        backend_config.thinking_type
        if isinstance(backend_config, OpenAIBackendConfig | AnthropicBackendConfig)
        else None
    )
    effort = backend_config.effort if isinstance(backend_config, AnthropicBackendConfig) else None
    return EffectiveSamplingConfig(
        backend_id=reasoner_config.backend_id,
        model_id=getattr(backend_config, "model_id", None),
        temperature=reasoner_config.temperature,
        top_p=reasoner_config.top_p,
        top_k=reasoner_config.top_k,
        presence_penalty=reasoner_config.presence_penalty,
        max_attempts=reasoner_config.max_attempts,
        max_tokens=reasoner_config.max_tokens,
        image_fallback_after_attempts=reasoner_config.image_fallback_after_attempts,
        seed=backend_config.seed if is_gemini else None,
        thinking_level=backend_config.thinking_level if is_gemini else None,
        reasoning_effort=reasoning_effort,
        thinking_mode=thinking_mode,
        effort=effort,
    )


def backend_section(raw_vlm: dict, backend_id: str) -> dict:
    """Return a backend's own config mapping without its reasoner override or adapter key."""
    section = dict(raw_vlm.get(backend_id) or {})
    section.pop("reasoner", None)
    section.pop("adapter", None)
    return section


def _load_mock_script(path: Path, env_var: str) -> MockBackend:
    """Build a scripted mock from a file holding one JSON object or an array."""
    if not path.exists():
        raise FileNotFoundError(f"{env_var} points to a missing file: {path}")
    text = path.read_text(encoding="utf-8")
    parsed = json.loads(text)
    if isinstance(parsed, list):
        if not parsed:
            raise ValueError(f"{env_var} names an empty decision array: {path}")
        return MockBackend(response_sequence=[json.dumps(item) for item in parsed])
    return MockBackend(response_text=text)


def build_retreat_choice_backend(
    backend_id: str, stage1_backend: VLMBackend
) -> VLMBackend | None:
    """Return the backend the stage-2 retreat-choice call goes to, if any.

    A real backend is stateless per call, so stage 2 reuses the stage-1
    instance. The mock is scripted, and a shared instance would hand stage 2
    the next stage-1 entry of a `VGU_MOCK_DECISION_FILE` sequence, so stage 2
    gets its own mock only when `VGU_MOCK_RETREAT_CHOICE_FILE` names a script
    (one retreat-choice JSON object, or an array replayed like the decision
    file, e.g. `config/mock_decisions/retreat_choice_b.json`). Without one
    there is no stage-2 backend and the caller skips the call.

    Args:
        backend_id: The configured stage-1 backend selector.
        stage1_backend: The stage-1 backend instance.

    Returns:
        The stage-2 backend, or None for a mock with no stage-2 script.

    Raises:
        FileNotFoundError: If `VGU_MOCK_RETREAT_CHOICE_FILE` names a missing
            file (config errors fail fast at startup).
        ValueError: If it names an empty JSON array.
    """
    if backend_id != "mock":
        return stage1_backend
    choice_file = os.environ.get("VGU_MOCK_RETREAT_CHOICE_FILE", "")
    if not choice_file:
        return None
    return _load_mock_script(Path(choice_file), "VGU_MOCK_RETREAT_CHOICE_FILE")


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
        backend_id: Adapter selector, e.g. "mock" or "llama_server". A named
            arm (e.g. "openai_gpt51") is built by passing its adapter
            (`backend_adapter`) with its config (`load_backend_config`).
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
        return _load_mock_script(Path(decision_file), "VGU_MOCK_DECISION_FILE")
    if backend_id == "llama_server":
        if backend_config is None:
            raise ValueError("llama_server backend requires a LlamaServerBackendConfig")
        return LlamaServerBackend(
            base_url=backend_config.base_url,
            model_id=backend_config.model_id,
            mmproj_path=backend_config.mmproj_path,
            multi_image=backend_config.multi_image,
        )
    if backend_id == "openai":
        if backend_config is None:
            backend_config = OpenAIBackendConfig()
        return OpenAIBackend(
            model_id=backend_config.model_id,
            base_url=backend_config.base_url,
            api_key_env=backend_config.api_key_env,
            organization=backend_config.organization,
            reasoning_effort=backend_config.reasoning_effort,
            max_tokens_param=backend_config.max_tokens_param,
            thinking_type=backend_config.thinking_type,
        )
    if backend_id == "anthropic":
        if backend_config is None:
            raise ValueError("anthropic backend requires an AnthropicBackendConfig")
        return AnthropicBackend(
            model_id=backend_config.model_id,
            base_url=backend_config.base_url,
            api_key_env=backend_config.api_key_env,
            thinking_type=backend_config.thinking_type,
            effort=backend_config.effort,
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

from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import LlamaServerBackendConfig, OpenAIBackendConfig
from reasoning.vlm.openai_backend import OpenAIBackend

BackendConfig = LlamaServerBackendConfig | OpenAIBackendConfig


def build_backend(
    backend_id: str,
    backend_config: BackendConfig | None = None,
) -> VLMBackend:
    """Construct a concrete VLM backend from its identifier and config.

    Args:
        backend_id: Selector, e.g. "mock" or "llama_server".
        backend_config: Backend-specific connection config. Optional because
            "mock" needs none; backends that require it raise on absence.

    Returns:
        A backend instance satisfying the `VLMBackend` Protocol.

    Raises:
        ValueError: If `backend_id` is not recognized, or required config is
            missing for a backend that needs it.
    """
    if backend_id == "mock":
        return MockBackend()
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
            raise ValueError("openai backend requires an OpenAIBackendConfig")
        return OpenAIBackend(
            model_id=backend_config.model_id,
            base_url=backend_config.base_url,
            api_key_env=backend_config.api_key_env,
            organization=backend_config.organization,
        )
    raise ValueError(f"Unknown backend_id: {backend_id!r}")

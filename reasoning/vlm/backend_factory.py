from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import LlamaServerBackendConfig

BackendConfig = LlamaServerBackendConfig  # extend to a union as backends are added


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
    raise ValueError(f"Unknown backend_id: {backend_id!r}")

from typing import Protocol, runtime_checkable

from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig


@runtime_checkable
class VLMBackend(Protocol):
    """Common interface for pluggable VLM providers.

    Implementations own HTTP/transport, image encoding, and provider response
    parsing into a `BackendResponse`. Prompt building and output parsing stay
    backend-agnostic.
    """

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Run one VLM call and return the raw model output.

        Args:
            payload: Fully-rendered system/user prompt and image reference.
            config: Runtime decoding settings (temperature, max_tokens, timeout).

        Returns:
            Backend response carrying the raw assistant text and metadata.
        """
        ...

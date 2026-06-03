from reasoning.vlm.backend_base import VLMBackend, VLMRequest, VLMResponse


class VILABackend(VLMBackend):
    """Placeholder adapter for VILA-family models."""

    def analyze(self, request: VLMRequest) -> VLMResponse:
        raise NotImplementedError("VILA inference is not configured yet.")

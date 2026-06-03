from reasoning.vlm.backend_base import VLMBackend, VLMRequest, VLMResponse


class CosmosBackend(VLMBackend):
    """Placeholder adapter for NVIDIA Cosmos Reasoner."""

    def analyze(self, request: VLMRequest) -> VLMResponse:
        raise NotImplementedError("Cosmos inference is not configured yet.")

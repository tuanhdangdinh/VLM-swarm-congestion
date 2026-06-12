from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig

_DEFAULT_RESPONSE = (
    '{"congestion_detected": false, "type": "none", "involved_robots": [], '
    '"root_cause": "No congestion detected.", "strategy": "none", '
    '"justification": "Scene is clear."}'
)


class MockBackend:
    """Deterministic VLM backend for offline tests.

    Returns a fixed response, a default no-congestion decision, or a scripted
    sequence (holding the last entry once exhausted). Records the most recent
    payload and config for assertions.
    """

    def __init__(
        self,
        response_text: str | None = None,
        backend_id: str = "mock",
        latency_ms: int = 0,
        response_sequence: list[str] | None = None,
    ) -> None:
        self._response_text = response_text
        self._backend_id = backend_id
        self._latency_ms = latency_ms
        self._sequence = list(response_sequence) if response_sequence else None
        self._index = 0
        self.last_payload: PromptPayload | None = None
        self.last_config: ReasonerConfig | None = None

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Return a canned response and record the inputs."""
        self.last_payload = payload
        self.last_config = config
        if self._sequence is not None:
            text = self._sequence[min(self._index, len(self._sequence) - 1)]
            self._index += 1
        elif self._response_text is not None:
            text = self._response_text
        else:
            text = _DEFAULT_RESPONSE
        return BackendResponse(
            text=text,
            backend_id=self._backend_id,
            latency_ms=self._latency_ms,
        )

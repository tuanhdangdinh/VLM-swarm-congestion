"""Exception types for the M2 VLM reasoning module."""


class VLMOutputParseError(ValueError):
    """Raised when VLM output is not valid coordination-decision JSON."""


class RetreatLabelError(VLMOutputParseError):
    """Raised when a stage-2 answer names a letter that was not rendered.

    A subclass so callers can count the measurement plan's `invalid_label`
    cause apart from `parse_failure` without matching on message text.
    `choice` carries the well-formed answer that named the bad letter, so a
    caller can hand it on and let the grounder tag `invalid_label` itself.
    """

    def __init__(self, message: str, choice: object | None = None) -> None:
        super().__init__(message)
        self.choice = choice


class DecisionValidationError(ValueError):
    """Raised when a parsed decision references unknown robot IDs."""


class BackendTimeoutError(RuntimeError):
    """Raised by invoke_backend when the backend call exceeds timeout_sec."""


class BackendHTTPError(ConnectionError):
    """A provider answered with an HTTP error status (>= 400).

    A `ConnectionError` subclass so every caller that already handles the
    adapters' transport failures handles it unchanged; artifacts record it
    under that public name (`recorded_error_type`), so the `error_type`
    vocabulary analyses key on does not move. The status drives the shared
    retry policy (`reasoning.vlm.retry_policy`).

    Attributes:
        status_code: The HTTP status the provider returned.
        retry_after_sec: The provider's `Retry-After`, in seconds, when sent.
        provider_code: The provider's own error code from the body, if any.
        request_id: The provider's request id for the failed call, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        retry_after_sec: float | None = None,
        provider_code: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_sec = retry_after_sec
        self.provider_code = provider_code
        self.request_id = request_id

    @property
    def retryable(self) -> bool:
        """True for 429 and 5xx; every other 4xx is deterministic."""
        return self.status_code == 429 or self.status_code >= 500


def recorded_error_type(exc: BaseException) -> str:
    """Return the class name an artifact records for `exc`.

    Args:
        exc: The exception that ended an attempt.

    Returns:
        "ConnectionError" for a `BackendHTTPError` (see its docstring),
        otherwise the exception's own class name.
    """
    if isinstance(exc, BackendHTTPError):
        return "ConnectionError"
    return type(exc).__name__

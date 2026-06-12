"""Exception types for the M2 VLM reasoning module."""


class VLMOutputParseError(ValueError):
    """Raised when VLM output is not valid coordination-decision JSON."""


class DecisionValidationError(ValueError):
    """Raised when a parsed decision references unknown robot IDs."""


class BackendTimeoutError(RuntimeError):
    """Raised by invoke_backend when the backend call exceeds timeout_sec."""

"""Exception types for the M2 VLM reasoning module."""


class VLMOutputParseError(ValueError):
    """Raised when VLM output is not valid coordination-decision JSON."""


class RetreatLabelError(VLMOutputParseError):
    """Raised when a stage-2 answer names a letter that was not rendered.

    A subclass so callers can count the measurement plan's `invalid_label`
    cause apart from `parse_failure` without matching on message text.
    """


class DecisionValidationError(ValueError):
    """Raised when a parsed decision references unknown robot IDs."""


class BackendTimeoutError(RuntimeError):
    """Raised by invoke_backend when the backend call exceeds timeout_sec."""

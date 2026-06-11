import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.models import (
    BackendResponse,
    PromptPayload,
    ReasonerConfig,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
)
from reasoning.vlm.output_parser import BackendTimeoutError

_REASK_SUFFIX = (
    "\n\nYour previous response was invalid: {error_message}\n"
    "Please return ONLY a valid JSON object matching the schema above.\n"
    "Do not include any text, markdown, or explanation outside the JSON."
)


def invoke_backend(
    backend: VLMBackend,
    payload: PromptPayload,
    config: ReasonerConfig,
) -> BackendResponse:
    """Call a VLM backend with an outer thread-level timeout and latency timing.

    Args:
        backend: Any object satisfying the VLMBackend Protocol.
        payload: Rendered prompt payload.
        config: Runtime config; `timeout_sec` bounds the call.

    Returns:
        The backend response, with `latency_ms` filled from wall-clock time when
        the backend did not report it.

    Raises:
        BackendTimeoutError: If the call exceeds `config.timeout_sec`.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(backend.analyze, payload, config)
        start = time.monotonic()
        try:
            response = future.result(timeout=config.timeout_sec)
        except FutureTimeoutError as exc:
            raise BackendTimeoutError(
                f"Backend timed out after {config.timeout_sec}s"
            ) from exc
        elapsed_ms = int((time.monotonic() - start) * 1000)
    if not response.latency_ms:
        return response.model_copy(update={"latency_ms": elapsed_ms})
    return response


def build_reask_prompt(payload: PromptPayload, error_message: str) -> PromptPayload:
    """Build a corrective prompt after invalid output, preserving fixed fields.

    Args:
        payload: The payload whose response failed.
        error_message: Human-readable description of the failure.

    Returns:
        A new frozen payload with the corrective suffix appended.
    """
    suffix = _REASK_SUFFIX.format(error_message=error_message)
    return payload.model_copy(update={"user_prompt": payload.user_prompt + suffix})


def build_failed_result(
    request: ReasonerRequest,
    backend_id: str,
    attempts: int,
    error_type: str | None,
    error_message: str | None,
    raw_text: str | None = None,
) -> ReasonerResult:
    """Construct a safe failure result with decision=None after exhausted retries.

    Args:
        request: The originating request.
        backend_id: Configured backend identifier.
        attempts: Total backend calls made.
        error_type: Last error class name, if any.
        error_message: Last error message, if any.
        raw_text: Last raw model text, preserved for audit.

    Returns:
        A `ReasonerResult` with `decision=None` and `parse_status='failed'`.
    """
    return ReasonerResult(
        request_id=request.request_id,
        decision=None,
        raw_text=raw_text,
        diagnostics=ReasonerDiagnostics(
            request_id=request.request_id,
            backend_id=backend_id,
            attempts=attempts,
            parse_status="failed",
            error_type=error_type,
            error_message=error_message,
        ),
    )

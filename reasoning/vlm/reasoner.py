import json
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path

from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.errors import (
    BackendTimeoutError,
    DecisionValidationError,
    VLMOutputParseError,
)
from reasoning.vlm.models import (
    BackendResponse,
    PromptPayload,
    ReasonerConfig,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
)
from reasoning.vlm.output_parser import parse_decision_text, validate_involved_robots
from reasoning.vlm.prompt_builder import build_prompt_payload

# Formatted via _REASK_SUFFIX.format(error_message=...) in build_reask_prompt.
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

    On timeout, the executor is shut down without waiting so the caller is not
    blocked by a hung backend thread (the thread is abandoned and exits on its
    own). Latency is filled from wall-clock time only when the backend did not
    report it.

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
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(backend.analyze, payload, config)
    start = time.monotonic()
    try:
        response = future.result(timeout=config.timeout_sec)
    except FutureTimeoutError as exc:
        executor.shutdown(wait=False)
        raise BackendTimeoutError(
            f"Backend timed out after {config.timeout_sec}s"
        ) from exc
    elapsed_ms = int((time.monotonic() - start) * 1000)
    executor.shutdown(wait=True)
    if response.latency_ms is None:
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


class Reasoner:
    """Stateless M2 reasoning orchestrator: prompt -> backend -> parse -> validate."""

    def __init__(self, backend: VLMBackend, config: ReasonerConfig) -> None:
        self._backend = backend
        self._config = config

    def run(self, request: ReasonerRequest) -> ReasonerResult:
        """Execute one complete reasoning pass with bounded retry/re-ask.

        Args:
            request: Validated reasoning request.

        Returns:
            A `ReasonerResult` with a decision, or `decision=None` on failure.

        Raises:
            ValueError: If robot IDs are not unique.
            FileNotFoundError: If `image_path` does not exist.
        """
        robot_ids = [s.robot_id for s in request.robot_states]
        if len(robot_ids) != len(set(robot_ids)):
            raise ValueError("Duplicate robot_id values in request.robot_states")
        if not Path(request.image_path).is_file():
            raise FileNotFoundError(f"image_path does not exist: {request.image_path}")

        payload = build_prompt_payload(request)
        known_ids = set(robot_ids)
        attempts = 0
        last_raw: str | None = None
        last_error_type: str | None = None
        last_error_msg: str | None = None
        had_parse_failure = False

        while attempts < self._config.max_attempts:
            attempts += 1
            try:
                response = invoke_backend(self._backend, payload, self._config)
                last_raw = response.text
                decision = parse_decision_text(response.text)
                validate_involved_robots(decision, known_ids)
                return ReasonerResult(
                    request_id=request.request_id,
                    decision=decision,
                    raw_text=last_raw,
                    diagnostics=ReasonerDiagnostics(
                        request_id=request.request_id,
                        backend_id=response.backend_id,
                        attempts=attempts,
                        latency_ms=response.latency_ms,
                        token_usage=response.token_usage,
                        # "invalid" = a parse/validation failure occurred earlier but a
                        # retry/re-ask then succeeded
                        parse_status="invalid" if had_parse_failure else "valid",  # noqa: E501
                        error_type=last_error_type,
                        error_message=last_error_msg,
                    ),
                )
            except (BackendTimeoutError, ConnectionError) as exc:
                last_error_type, last_error_msg = type(exc).__name__, str(exc)
                continue
            except (VLMOutputParseError, DecisionValidationError) as exc:
                had_parse_failure = True
                last_error_type, last_error_msg = type(exc).__name__, str(exc)
                if self._config.allow_reask and attempts < self._config.max_attempts:
                    payload = build_reask_prompt(payload, str(exc))

        return build_failed_result(
            request=request,
            backend_id=self._config.backend_id,
            attempts=attempts,
            error_type=last_error_type,
            error_message=last_error_msg,
            raw_text=last_raw,
        )


def write_reasoner_log(
    output_path: str | Path,
    request: ReasonerRequest,
    result: ReasonerResult,
) -> None:
    """Append one request/response record to a JSONL trace file.

    Args:
        output_path: Destination JSONL file (opened in append mode).
        request: The originating request.
        result: The reasoning result to record.
    """
    record = {
        "request_id": request.request_id,
        "image_path": request.image_path,
        "frame_id": request.frame_id,
        "stamp": request.stamp,
        "robot_ids": [s.robot_id for s in request.robot_states],
        "backend_id": result.diagnostics.backend_id,
        "attempts": result.diagnostics.attempts,
        "latency_ms": result.diagnostics.latency_ms,
        "token_usage": result.diagnostics.token_usage,
        "parse_status": result.diagnostics.parse_status,
        "raw_text": result.raw_text,
        "decision": result.decision.model_dump(mode="json") if result.decision else None,
        "error_type": result.diagnostics.error_type,
        "error_message": result.diagnostics.error_message,
    }
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, default=str) + "\n")

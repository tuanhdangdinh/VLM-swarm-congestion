import json
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path

from PIL import Image

from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.errors import (
    BackendTimeoutError,
    DecisionValidationError,
    VLMOutputParseError,
)
from reasoning.vlm.models import (
    BackendResponse,
    EffectiveSamplingConfig,
    PromptPayload,
    ReasonerConfig,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
)
from reasoning.vlm.output_parser import (
    parse_decision_with_degradations,
    validate_involved_robots,
)
from reasoning.vlm.prompt_builder import build_prompt_payload

# Formatted via _REASK_SUFFIX.format(error_message=...) in build_reask_prompt.
_REASK_SUFFIX = (
    "\n\nYour previous response was invalid: {error_message}\n"
    "Please return ONLY a valid JSON object matching the schema above.\n"
    "Do not include any text, markdown, or explanation outside the JSON."
)


# Both phrasings appear in the live corpus ("I'm sorry, I can't assist with
# that." x28 and "I'm sorry, but I can't assist with that." x6 as of 2026-09-26);
# the third pattern is the generic decline the same family produces. Deliberately
# narrow: a model that merely mentions being sorry mid-answer is not a refusal,
# and a false positive would spend an attempt on a neutral image for nothing.
_REFUSAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"i(?:'m|’m| am) sorry,?\s+(?:but\s+)?i can(?:'|’)?t assist", re.I),
    re.compile(r"i can(?:'|’)?t help with", re.I),
)

# Mid-grey: the neutral stimulus the frame-replay study used (0/120 refusals,
# docs/reports/2026-09-25-frame-replay.md rev 2).
_NEUTRAL_IMAGE_RGB = (128, 128, 128)


def is_refusal(text: str) -> bool:
    """Return True when assistant text is a safety refusal rather than an answer.

    Args:
        text: Raw assistant text from one backend call.

    Returns:
        True if the text matches an observed refusal phrasing.
    """
    return any(pattern.search(text) for pattern in _REFUSAL_PATTERNS)


def make_neutral_image(source_image_path: str | Path, destination: str | Path) -> Path:
    """Write a solid mid-grey PNG matching a frame's dimensions.

    Args:
        source_image_path: The camera frame whose `(width, height)` is mirrored.
        destination: Where the neutral PNG is written.

    Returns:
        The destination path.
    """
    with Image.open(source_image_path) as image:
        size = image.size
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, _NEUTRAL_IMAGE_RGB).save(destination, format="PNG")
    return Path(destination)


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


def _extract_unsupported_sampling(raw: dict[str, object]) -> dict[str, float] | None:
    """Validate `BackendResponse.raw["unsupported_sampling"]` before it is trusted.

    `raw` is `dict[str, object]` and comes from a backend adapter, so this must
    not assume a well-formed value: a malformed entry (wrong type, non-numeric
    values) is treated the same as "backend did not report" rather than raised.

    Args:
        raw: The `BackendResponse.raw` mapping.

    Returns:
        A `dict[str, float]` of dropped sampling fields, or None if the key is
        absent or the value is not a str-to-number mapping.
    """
    value = raw.get("unsupported_sampling")
    if not isinstance(value, dict):
        return None
    if not all(
        isinstance(key, str) and isinstance(val, (int, float)) and not isinstance(val, bool)
        for key, val in value.items()
    ):
        return None
    return {key: float(val) for key, val in value.items()}


def attach_unsupported_sampling(
    effective: EffectiveSamplingConfig | None,
    unsupported_sampling: dict[str, float] | None,
    served_model: str | None = None,
) -> EffectiveSamplingConfig | None:
    """Fold a call's per-call backend reports into the effective config block.

    Args:
        effective: The configured sampling block, or None when the caller
            described none.
        unsupported_sampling: Sampling fields the backend reported dropping.
        served_model: The model string the provider reported serving the call.

    Returns:
        A copy carrying `unsupported_sampling` and `served_model`, or None when
        `effective` is None.
    """
    if effective is None:
        return None
    return effective.model_copy(
        update={"unsupported_sampling": unsupported_sampling, "served_model": served_model}
    )


def build_failed_result(
    request: ReasonerRequest,
    backend_id: str,
    attempts: int,
    error_type: str | None,
    error_message: str | None,
    raw_text: str | None = None,
    unsupported_sampling: dict[str, float] | None = None,
    effective_sampling: EffectiveSamplingConfig | None = None,
    refusal_attempts: int = 0,
    image_fallback_used: bool = False,
    image_fallback_attempt: int | None = None,
    served_model: str | None = None,
) -> ReasonerResult:
    """Construct a safe failure result with decision=None after exhausted retries.

    Args:
        request: The originating request.
        backend_id: Configured backend identifier.
        attempts: Total backend calls made.
        error_type: Last error class name, if any.
        error_message: Last error message, if any.
        raw_text: Last raw model text, preserved for audit.
        unsupported_sampling: Sampling fields the backend could not honour on
            its last successful call, if any (see `ReasonerDiagnostics`).
        effective_sampling: The configured sampling block for this call, if the
            caller described one. A refusal or exhausted-retry cycle is exactly
            the case an audit needs the decoding parameters for, so the failure
            path records them too.
        refusal_attempts: How many attempts were safety refusals.
        image_fallback_used: Whether the neutral-image retry fired.
        image_fallback_attempt: 1-based index of the neutral-image attempt.
        served_model: The model string the provider reported on the last
            response it returned, if any (a refusal still names its model).

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
            unsupported_sampling=unsupported_sampling,
            served_model=served_model,
            reasoner_config_effective=attach_unsupported_sampling(
                effective_sampling, unsupported_sampling, served_model
            ),
            refusal_attempts=refusal_attempts,
            image_fallback_used=image_fallback_used,
            image_fallback_attempt=image_fallback_attempt,
        ),
    )


class Reasoner:
    """Stateless M2 reasoning orchestrator: prompt -> backend -> parse -> validate."""

    def __init__(
        self,
        backend: VLMBackend,
        config: ReasonerConfig,
        effective_sampling: EffectiveSamplingConfig | None = None,
    ) -> None:
        """Wire a backend to its runtime config.

        Args:
            backend: Any object satisfying the `VLMBackend` Protocol.
            config: Resolved runtime config for this backend.
            effective_sampling: Configured sampling block recorded on every
                result, built by `describe_effective_sampling`. Optional so a
                test harness or a script may construct a `Reasoner` without the
                backend's own config; then nothing is recorded.
        """
        self._backend = backend
        self._config = config
        self._effective_sampling = effective_sampling

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

        base_payload = build_prompt_payload(request)
        payload = base_payload
        known_ids = set(robot_ids)
        attempts = 0
        last_raw: str | None = None
        last_error_type: str | None = None
        last_error_msg: str | None = None
        last_unsupported_sampling: dict[str, float] | None = None
        last_served_model: str | None = None
        had_parse_failure = False
        refusal_attempts = 0
        image_fallback_attempt: int | None = None
        # Created only when the mitigation actually fires, so the common path
        # touches the filesystem exactly as it did before.
        scratch: tempfile.TemporaryDirectory | None = None

        try:
            while attempts < self._config.max_attempts:
                attempts += 1
                try:
                    response = invoke_backend(self._backend, payload, self._config)
                    last_raw = response.text
                    last_unsupported_sampling = _extract_unsupported_sampling(response.raw)
                    last_served_model = response.served_model
                    decision, degradations = parse_decision_with_degradations(response.text)
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
                            unsupported_sampling=last_unsupported_sampling,
                            served_model=last_served_model,
                            reasoner_config_effective=attach_unsupported_sampling(
                                self._effective_sampling,
                                last_unsupported_sampling,
                                last_served_model,
                            ),
                            refusal_attempts=refusal_attempts,
                            image_fallback_used=image_fallback_attempt is not None,
                            image_fallback_attempt=image_fallback_attempt,
                            decision_degradations=degradations,
                        ),
                    )
                except (BackendTimeoutError, ConnectionError) as exc:
                    last_error_type, last_error_msg = type(exc).__name__, str(exc)
                    continue
                except (VLMOutputParseError, DecisionValidationError) as exc:
                    had_parse_failure = True
                    last_error_type, last_error_msg = type(exc).__name__, str(exc)
                    refused = is_refusal(last_raw or "")
                    if refused:
                        refusal_attempts += 1
                    if attempts >= self._config.max_attempts:
                        continue
                    if refused and self._should_fall_back(attempts, image_fallback_attempt):
                        scratch = scratch or tempfile.TemporaryDirectory(
                            prefix="m2-neutral-image-"
                        )
                        neutral = self._neutral_payload(base_payload, scratch.name)
                        if neutral is not None:
                            payload = neutral
                            image_fallback_attempt = attempts + 1
                            continue
                    if self._config.allow_reask:
                        payload = build_reask_prompt(payload, str(exc))

            return build_failed_result(
                request=request,
                backend_id=self._config.backend_id,
                attempts=attempts,
                error_type=last_error_type,
                error_message=last_error_msg,
                raw_text=last_raw,
                unsupported_sampling=last_unsupported_sampling,
                effective_sampling=self._effective_sampling,
                refusal_attempts=refusal_attempts,
                image_fallback_used=image_fallback_attempt is not None,
                image_fallback_attempt=image_fallback_attempt,
                served_model=last_served_model,
            )
        finally:
            if scratch is not None:
                scratch.cleanup()

    def _should_fall_back(self, attempts: int, image_fallback_attempt: int | None) -> bool:
        """Whether a refusal on `attempts` should trigger the neutral-image retry.

        The mitigation fires at most once per request: a second swap would spend
        another attempt on a stimulus that has already been shown not to help.
        """
        threshold = self._config.image_fallback_after_attempts
        return (
            threshold is not None
            and image_fallback_attempt is None
            and attempts >= threshold
        )

    def _neutral_payload(
        self, base_payload: PromptPayload, scratch_dir: str
    ) -> PromptPayload | None:
        """Build the fallback payload: the original prompt text, a neutral image.

        The re-ask suffix is deliberately absent — the refusal is not a formatting
        failure, so correcting the format would change the prompt for no reason
        and break comparability with the un-refused call. Returns None when the
        neutral image cannot be produced, so an unreadable frame degrades to the
        ordinary re-ask path instead of crashing the caller (M2 contract: failures
        surface as diagnostics, never as an exception out of `run`).
        """
        try:
            neutral = make_neutral_image(
                base_payload.image_path, Path(scratch_dir) / "neutral.png"
            )
        except OSError:
            return None
        return base_payload.model_copy(update={"image_path": str(neutral)})


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
    # Omit the key entirely rather than writing null, so existing artifact
    # readers/golden files that don't expect it are unaffected.
    if result.diagnostics.unsupported_sampling is not None:
        record["unsupported_sampling"] = result.diagnostics.unsupported_sampling
    if result.diagnostics.served_model is not None:
        record["served_model"] = result.diagnostics.served_model
    # Same rationale as above: a trace with no refusal and no fallback stays
    # byte-identical to one written before the mitigation existed.
    diagnostics = result.diagnostics
    if diagnostics.refusal_attempts or diagnostics.image_fallback_used:
        record["refusal_attempts"] = diagnostics.refusal_attempts
        record["image_fallback_used"] = diagnostics.image_fallback_used
        record["image_fallback_attempt"] = diagnostics.image_fallback_attempt
    effective = result.diagnostics.reasoner_config_effective
    if effective is not None:
        record["reasoner_config_effective"] = effective.model_dump(mode="json")
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, default=str) + "\n")

import json
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Literal

from PIL import Image

from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.errors import (
    BackendHTTPError,
    BackendTimeoutError,
    VLMOutputParseError,
    recorded_error_type,
)
from reasoning.vlm.models import (
    AttemptOutcome,
    AttemptRecord,
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
from reasoning.vlm.retry_policy import DEFAULT_RETRY_POLICY, RetryPolicy, classify_failure

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


def _extract_mock_mode(raw: dict[str, object]) -> str | None:
    """Return `raw["mock_mode"]` when it is a non-empty string, else None."""
    value = raw.get("mock_mode")
    return value if isinstance(value, str) and value else None


def attach_unsupported_sampling(
    effective: EffectiveSamplingConfig | None,
    unsupported_sampling: dict[str, float] | None,
    served_model: str | None = None,
    system_fingerprint: str | None = None,
) -> EffectiveSamplingConfig | None:
    """Fold a call's per-call backend reports into the effective config block.

    Args:
        effective: The configured sampling block, or None when the caller
            described none.
        unsupported_sampling: Sampling fields the backend reported dropping.
        served_model: The model string the provider reported serving the call.
        system_fingerprint: The provider's backend fingerprint, if sent (F04).

    Returns:
        A copy carrying the per-call reports, or None when `effective` is None.
    """
    if effective is None:
        return None
    return effective.model_copy(
        update={
            "unsupported_sampling": unsupported_sampling,
            "served_model": served_model,
            "system_fingerprint": system_fingerprint,
        }
    )


def exception_attempt_record(exc: BaseException, backoff_sec: float | None) -> AttemptRecord:
    """Describe an attempt whose backend call raised.

    Args:
        exc: The exception the attempt ended with.
        backoff_sec: Seconds the retry policy then slept, or None when this
            was the final attempt.

    Returns:
        The attempt's `AttemptRecord`.
    """
    outcome: AttemptOutcome
    if isinstance(exc, BackendHTTPError):
        outcome = "http_error"
    elif isinstance(exc, BackendTimeoutError):
        outcome = "timeout"
    elif isinstance(exc, ConnectionError):
        outcome = "transport_error"
    else:
        outcome = "unexpected_error"
    http = exc if isinstance(exc, BackendHTTPError) else None
    return AttemptRecord(
        outcome=outcome,
        error_type=recorded_error_type(exc),
        http_status=None if http is None else http.status_code,
        provider_error_code=None if http is None else http.provider_code,
        provider_request_id=None if http is None else http.request_id,
        retry_after_sec=None if http is None else http.retry_after_sec,
        backoff_sec=backoff_sec,
    )


def response_attempt_record(
    response: BackendResponse,
    outcome: AttemptOutcome,
    *,
    error_type: str | None = None,
    refusal_source: Literal["provider", "text_pattern"] | None = None,
    backoff_sec: float | None = None,
) -> AttemptRecord:
    """Describe an attempt that returned a response.

    Args:
        response: What the backend returned.
        outcome: How the attempt ended.
        error_type: The parse/validation error class, if any.
        refusal_source: Which channel flagged a refusal, if one did.
        backoff_sec: 0.0 when another attempt follows, None on the final one.

    Returns:
        The attempt's `AttemptRecord`.
    """
    http_status = response.raw.get("http_status")
    return AttemptRecord(
        outcome=outcome,
        error_type=error_type,
        http_status=http_status if isinstance(http_status, int) else None,
        provider_error_code=response.refusal_category if http_status is not None else None,
        finish_reason=response.finish_reason,
        provider_request_id=response.provider_request_id,
        system_fingerprint=response.system_fingerprint,
        refusal_source=refusal_source,
        backoff_sec=backoff_sec,
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
    refusal_category: str | None = None,
    attempt_token_usage: list[dict[str, int] | None] | None = None,
    system_fingerprint: str | None = None,
    finish_reason: str | None = None,
    attempt_records: list[AttemptRecord] | None = None,
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
        refusal_category: The provider's category for the last structured
            refusal, if any (`BackendResponse.refusal_category`).
        attempt_token_usage: Per-attempt usage in call order (None entries
            for attempts that returned no usage). The last entry becomes
            `token_usage`, so a terminal refusal still records what it billed.
        system_fingerprint: The provider's fingerprint on the last response.
        finish_reason: The provider's finish reason on the last response.
        attempt_records: Why each attempt ended, in call order.

    Returns:
        A `ReasonerResult` with `decision=None` and `parse_status='failed'`.
    """
    usage = list(attempt_token_usage or [])
    return ReasonerResult(
        request_id=request.request_id,
        decision=None,
        raw_text=raw_text,
        diagnostics=ReasonerDiagnostics(
            request_id=request.request_id,
            backend_id=backend_id,
            attempts=attempts,
            token_usage=usage[-1] if usage else None,
            attempt_token_usage=usage,
            parse_status="failed",
            error_type=error_type,
            error_message=error_message,
            unsupported_sampling=unsupported_sampling,
            served_model=served_model,
            system_fingerprint=system_fingerprint,
            finish_reason=finish_reason,
            reasoner_config_effective=attach_unsupported_sampling(
                effective_sampling, unsupported_sampling, served_model, system_fingerprint
            ),
            refusal_attempts=refusal_attempts,
            refusal_category=refusal_category,
            image_fallback_used=image_fallback_used,
            image_fallback_attempt=image_fallback_attempt,
            attempt_records=list(attempt_records or []),
        ),
    )


class Reasoner:
    """Stateless M2 reasoning orchestrator: prompt -> backend -> parse -> validate."""

    def __init__(
        self,
        backend: VLMBackend,
        config: ReasonerConfig,
        effective_sampling: EffectiveSamplingConfig | None = None,
        retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    ) -> None:
        """Wire a backend to its runtime config.

        Args:
            backend: Any object satisfying the `VLMBackend` Protocol.
            config: Resolved runtime config for this backend.
            effective_sampling: Configured sampling block recorded on every
                result, built by `describe_effective_sampling`. Optional so a
                test harness or a script may construct a `Reasoner` without the
                backend's own config; then nothing is recorded.
            retry_policy: Backoff between failed attempts (conformance
                ruling F02); the shared default for every arm.
        """
        self._backend = backend
        self._config = config
        self._effective_sampling = effective_sampling
        self._retry_policy = retry_policy

    @property
    def backend(self) -> VLMBackend:
        """The backend every call of this reasoner goes to."""
        return self._backend

    @property
    def config(self) -> ReasonerConfig:
        """The config every call of this reasoner runs under."""
        return self._config

    def run(self, request: ReasonerRequest) -> ReasonerResult:
        """Execute one complete reasoning pass with bounded retry/re-ask.

        Only invalid caller input raises, before any backend call; once the
        first attempt starts, every failure -- whatever exception class an
        adapter or the parser raises -- is a recorded attempt and the call
        ends in a `ReasonerResult`.

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
        for extra in base_payload.extra_image_paths:
            if not Path(extra).is_file():
                raise FileNotFoundError(f"extra image does not exist: {extra}")
        payload = base_payload
        # What a re-ask is built from: the original payload, or the
        # neutral-image one once the fallback fired -- never an already
        # re-asked payload, so the corrective suffix appears once whatever
        # the attempt number, as in stage 2 (conformance fix F14).
        reask_base = base_payload
        known_ids = set(robot_ids)
        max_attempts = self._config.max_attempts
        attempts = 0
        last_raw: str | None = None
        last_error_type: str | None = None
        last_error_msg: str | None = None
        last_unsupported_sampling: dict[str, float] | None = None
        last_served_model: str | None = None
        last_fingerprint: str | None = None
        last_finish_reason: str | None = None
        had_parse_failure = False
        refusal_attempts = 0
        refusal_category: str | None = None
        image_fallback_attempt: int | None = None
        waited_sec = 0.0
        # One entry per attempt, refused ones included: a refusal is billed.
        attempt_usage: list[dict[str, int] | None] = []
        records: list[AttemptRecord] = []
        # Created only when the mitigation actually fires, so the common path
        # touches the filesystem exactly as it did before.
        scratch: tempfile.TemporaryDirectory | None = None

        def failed(error_type: str | None, error_message: str | None) -> ReasonerResult:
            return build_failed_result(
                request=request,
                backend_id=self._config.backend_id,
                attempts=max(attempts, 1),
                error_type=error_type,
                error_message=error_message,
                raw_text=last_raw,
                unsupported_sampling=last_unsupported_sampling,
                effective_sampling=self._effective_sampling,
                refusal_attempts=refusal_attempts,
                image_fallback_used=image_fallback_attempt is not None,
                image_fallback_attempt=image_fallback_attempt,
                served_model=last_served_model,
                refusal_category=refusal_category,
                attempt_token_usage=attempt_usage,
                system_fingerprint=last_fingerprint,
                finish_reason=last_finish_reason,
                attempt_records=records,
            )

        try:
            while attempts < max_attempts:
                attempts += 1
                try:
                    response = invoke_backend(self._backend, payload, self._config)
                except Exception as exc:
                    # Timeouts, transport and HTTP errors, and anything else an
                    # adapter raises (a malformed provider body, a
                    # response-model validation error) are each one recorded
                    # attempt, never an escape from `run`: the M2 contract is
                    # decision=None after bounded retries.
                    attempt_usage.append(None)
                    last_error_type, last_error_msg = recorded_error_type(exc), str(exc)
                    # A deterministic 4xx ends the call: repeating the same
                    # request cannot succeed, so the budget is not spent on it.
                    stop = classify_failure(exc) == "stop"
                    backoff: float | None = None
                    if not stop and attempts < max_attempts:
                        backoff = self._retry_policy.wait_before_retry(exc, attempts, waited_sec)
                        waited_sec += backoff
                    records.append(exception_attempt_record(exc, backoff))
                    if stop:
                        break
                    continue
                attempt_usage.append(response.token_usage)
                last_raw = response.text
                last_unsupported_sampling = _extract_unsupported_sampling(response.raw)
                last_served_model = response.served_model
                last_fingerprint = response.system_fingerprint
                last_finish_reason = response.finish_reason
                final_attempt = attempts >= max_attempts
                try:
                    if response.refusal:
                        # A refusal on the provider's documented channel
                        # (BackendResponse.refusal) is a refusal whatever its
                        # text says, so it takes the same path as a text
                        # refusal below.
                        refusal_category = response.refusal_category or refusal_category
                        raise VLMOutputParseError(
                            "provider refusal (category="
                            f"{response.refusal_category or 'unspecified'})"
                        )
                    decision, degradations = parse_decision_with_degradations(response.text)
                    validate_involved_robots(decision, known_ids)
                except Exception as exc:
                    # A response came back (and is billed, so its usage is
                    # already recorded), so any failure reading it -- the
                    # parser's own errors or an unexpected one -- is a parse
                    # failure of this attempt.
                    had_parse_failure = True
                    last_error_type, last_error_msg = type(exc).__name__, str(exc)
                    # The provider's structured signal first; the English
                    # text pattern only as the fallback channel (F03).
                    refusal_source: Literal["provider", "text_pattern"] | None = None
                    if response.refusal:
                        refusal_source = "provider"
                    elif is_refusal(last_raw or ""):
                        refusal_source = "text_pattern"
                    if refusal_source is not None:
                        refusal_attempts += 1
                    records.append(
                        response_attempt_record(
                            response,
                            "refusal" if refusal_source is not None else "parse_failure",
                            error_type=last_error_type,
                            refusal_source=refusal_source,
                            backoff_sec=None if final_attempt else 0.0,
                        )
                    )
                    if final_attempt:
                        continue
                    if refusal_source is not None and self._should_fall_back(
                        attempts, image_fallback_attempt
                    ):
                        scratch = scratch or tempfile.TemporaryDirectory(
                            prefix="m2-neutral-image-"
                        )
                        neutral = self._neutral_payload(base_payload, scratch.name)
                        if neutral is not None:
                            payload = reask_base = neutral
                            image_fallback_attempt = attempts + 1
                            continue
                    if self._config.allow_reask:
                        payload = build_reask_prompt(reask_base, str(exc))
                    continue
                records.append(response_attempt_record(response, "answered"))
                return ReasonerResult(
                    request_id=request.request_id,
                    decision=decision,
                    raw_text=last_raw,
                    diagnostics=ReasonerDiagnostics(
                        request_id=request.request_id,
                        # The arm id on every path (F09), never the model id.
                        backend_id=self._config.backend_id,
                        attempts=attempts,
                        latency_ms=response.latency_ms,
                        token_usage=response.token_usage,
                        attempt_token_usage=attempt_usage,
                        # "invalid" = a parse/validation failure occurred earlier
                        # but a retry/re-ask then succeeded
                        parse_status="invalid" if had_parse_failure else "valid",
                        error_type=last_error_type,
                        error_message=last_error_msg,
                        unsupported_sampling=last_unsupported_sampling,
                        served_model=last_served_model,
                        system_fingerprint=last_fingerprint,
                        finish_reason=last_finish_reason,
                        reasoner_config_effective=attach_unsupported_sampling(
                            self._effective_sampling,
                            last_unsupported_sampling,
                            last_served_model,
                            last_fingerprint,
                        ),
                        refusal_attempts=refusal_attempts,
                        refusal_category=refusal_category,
                        image_fallback_used=image_fallback_attempt is not None,
                        image_fallback_attempt=image_fallback_attempt,
                        decision_degradations=degradations,
                        attempt_records=records,
                        mock_mode=_extract_mock_mode(response.raw),
                    ),
                )

            return failed(last_error_type, last_error_msg)
        except Exception as exc:
            # Last-resort net (e.g. the fallback scratch directory cannot be
            # created): the call still ends as a recorded failure with every
            # attempt's usage so far, never as an exception out of `run`.
            return failed(type(exc).__name__, str(exc))
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

        Every image is replaced, the zoom tile included. The re-ask suffix is
        deliberately absent — the refusal is not a formatting failure, so
        correcting the format would change the prompt for no reason and break
        comparability with the un-refused call. Returns None when the
        neutral image cannot be produced, so an unreadable frame degrades to the
        ordinary re-ask path instead of crashing the caller (M2 contract: failures
        surface as diagnostics, never as an exception out of `run`).
        """
        try:
            neutral = make_neutral_image(
                base_payload.image_path, Path(scratch_dir) / "neutral.png"
            )
            # A prompt-apparatus extra image (the zoom tile) is a crop of the
            # same realistic annotated frame -- the refusal trigger -- so it is
            # neutralized too; the image count and sizes stay as sent.
            extras = [
                str(make_neutral_image(path, Path(scratch_dir) / f"neutral_extra_{index}.png"))
                for index, path in enumerate(base_payload.extra_image_paths)
            ]
        except OSError:
            return None
        update: dict[str, object] = {"image_path": str(neutral)}
        if extras:
            update["extra_image_paths"] = extras
        return base_payload.model_copy(update=update)


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
        record["attempt_token_usage"] = diagnostics.attempt_token_usage
    if diagnostics.refusal_category is not None:
        record["refusal_category"] = diagnostics.refusal_category
    if diagnostics.finish_reason is not None:
        record["finish_reason"] = diagnostics.finish_reason
    if diagnostics.system_fingerprint is not None:
        record["system_fingerprint"] = diagnostics.system_fingerprint
    if diagnostics.mock_mode is not None:
        record["mock_mode"] = diagnostics.mock_mode
    # Every attempt's outcome, finish reason, provider request id and backoff
    # (conformance fixes F06/F18/F02), whatever the call's result.
    if diagnostics.attempt_records:
        record["attempt_records"] = [
            entry.model_dump(mode="json") for entry in diagnostics.attempt_records
        ]
    effective = result.diagnostics.reasoner_config_effective
    if effective is not None:
        record["reasoner_config_effective"] = effective.model_dump(mode="json")
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, default=str) + "\n")

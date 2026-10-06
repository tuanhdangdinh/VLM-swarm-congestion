"""Stage-2 retreat-choice call: prompt -> backend -> parse, bounded like stage 1."""

from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.errors import (
    BackendTimeoutError,
    RetreatLabelError,
    VLMOutputParseError,
    recorded_error_type,
)
from reasoning.vlm.models import (
    PromptPayload,
    ReasonerConfig,
    RetreatChoiceDecision,
    RetreatChoiceRequest,
    RetreatChoiceResult,
    Stage2FailureCause,
)
from reasoning.vlm.output_parser import parse_retreat_choice_text
from reasoning.vlm.reasoner import build_reask_prompt, invoke_backend, is_refusal
from reasoning.vlm.retry_policy import DEFAULT_RETRY_POLICY, RetryPolicy, classify_failure
from reasoning.vlm.stage2_prompt import build_stage2_prompt_payload


class RetreatChooser:
    """Backend-agnostic stage-2 caller; never raises past `choose`.

    `timeout_sec` bounds each call and `max_attempts` bounds the calls, so the
    worst case is their product. M5 passes the stage-1 `ReasonerConfig` with
    both replaced by its own `stage2_*` keys, so stage 2 does not inherit
    stage 1's budget (4 x 120 s on openai); the shared retry policy may add
    its backoff between attempts (at most one wait with two attempts). A
    timeout, a backend exception, a refusal or unparsable text spends an
    attempt (the last two re-ask when `allow_reask`); an HTTP 4xx other than
    429 ends the call at once, since repeating it cannot succeed; a well-formed answer
    naming an unrendered letter ends the call at once, since that letter is
    the measurement plan's `invalid_label` outcome, not a transport fault.
    """

    def __init__(
        self,
        backend: VLMBackend,
        config: ReasonerConfig,
        retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    ) -> None:
        """Wire a backend to the config its calls run under.

        Args:
            backend: Any object satisfying the `VLMBackend` Protocol.
            config: Timeout, attempt budget, sampling and re-ask policy.
            retry_policy: Backoff between failed attempts, the same policy
                stage 1 runs under (conformance ruling F02).
        """
        self._backend = backend
        self._config = config
        self._retry_policy = retry_policy

    @property
    def config(self) -> ReasonerConfig:
        """The config every call of this chooser runs under."""
        return self._config

    def choose(self, request: RetreatChoiceRequest) -> RetreatChoiceResult:
        """Ask the backend for one retreat letter.

        Args:
            request: The rendered-candidate set for one yield.

        Returns:
            The parsed choice, or `choice=None` with `failure_cause` set once
            the attempts run out. An `invalid_label` result keeps the parsed
            (unrendered) choice.
        """
        base_payload = build_stage2_prompt_payload(request)
        valid_labels = {candidate.label for candidate in request.candidates}
        backend_id = self._config.backend_id
        # One entry per attempt, refused ones included: a refusal is billed.
        usage: list[dict[str, int] | None] = []

        try:
            return self._attempt_loop(request, base_payload, valid_labels, usage)
        except Exception as exc:
            # Last-resort net: stage 2 ends as a recorded failure, never an
            # exception into M5 (the stage-1 `Reasoner.run` contract).
            return self._result(
                request, backend_id, None, None, max(len(usage), 1), None,
                "backend_error", type(exc).__name__, str(exc), 0, usage,
            )

    def _attempt_loop(
        self,
        request: RetreatChoiceRequest,
        base_payload: PromptPayload,
        valid_labels: set[str],
        usage: list[dict[str, int] | None],
    ) -> RetreatChoiceResult:
        payload = base_payload
        backend_id = self._config.backend_id
        attempts = 0
        raw_text: str | None = None
        latency_ms: int | None = None
        cause: Stage2FailureCause | None = None
        error_type: str | None = None
        error_message: str | None = None
        refusals = 0

        waited_sec = 0.0

        while attempts < self._config.max_attempts:
            attempts += 1
            try:
                response = invoke_backend(self._backend, payload, self._config)
            except Exception as exc:  # e.g. an HTTP 429 on an exhausted key
                usage.append(None)
                cause = "timeout" if isinstance(exc, BackendTimeoutError) else "backend_error"
                error_type, error_message = recorded_error_type(exc), str(exc)
                # The stage-1 retry policy (conformance ruling F02), unchanged.
                if classify_failure(exc) == "stop":
                    break
                if attempts < self._config.max_attempts:
                    waited_sec += self._retry_policy.wait_before_retry(exc, attempts, waited_sec)
                continue
            usage.append(response.token_usage)
            raw_text = response.text
            backend_id = response.backend_id
            latency_ms = response.latency_ms
            try:
                if response.refusal:
                    # Provider-flagged refusal: counted as a refusal below
                    # whatever text (often none) it carries.
                    raise VLMOutputParseError("provider refusal")
                choice = parse_retreat_choice_text(response.text, valid_labels)
            except RetreatLabelError as exc:
                invalid = exc.choice if isinstance(exc.choice, RetreatChoiceDecision) else None
                return self._result(
                    request, backend_id, invalid, raw_text, attempts, latency_ms,
                    "invalid_label", type(exc).__name__, str(exc), refusals, usage,
                )
            except Exception as exc:
                # The parser's own errors and any unexpected one alike: the
                # attempt returned (billed) text that yielded no letter.
                refused = response.refusal or is_refusal(response.text)
                refusals += int(refused)
                cause = "refusal" if refused else "parse_failure"
                error_type, error_message = type(exc).__name__, str(exc)
                if self._config.allow_reask:
                    payload = build_reask_prompt(base_payload, str(exc))
                continue
            return self._result(
                request, backend_id, choice, raw_text, attempts, latency_ms,
                None, error_type, error_message, refusals, usage,
            )
        return self._result(
            request, backend_id, None, raw_text, attempts, latency_ms,
            cause, error_type, error_message, refusals, usage,
        )

    def _result(
        self,
        request: RetreatChoiceRequest,
        backend_id: str,
        choice: RetreatChoiceDecision | None,
        raw_text: str | None,
        attempts: int,
        latency_ms: int | None,
        cause: Stage2FailureCause | None,
        error_type: str | None,
        error_message: str | None,
        refusals: int,
        usage: list[dict[str, int] | None],
    ) -> RetreatChoiceResult:
        return RetreatChoiceResult(
            request_id=request.request_id,
            backend_id=backend_id,
            choice=choice,
            raw_text=raw_text,
            attempts=attempts,
            latency_ms=latency_ms,
            failure_cause=cause,
            error_type=error_type,
            error_message=error_message,
            refusal_attempts=refusals,
            token_usage=usage[-1] if usage else None,
            attempt_token_usage=usage,
            max_attempts=self._config.max_attempts,
            timeout_sec=self._config.timeout_sec,
        )

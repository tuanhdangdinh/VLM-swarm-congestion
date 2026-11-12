"""The per-cluster ask / validate / re-ask loop, shared by the VLM bench and the live shadow.

One M2 call per analysis: the live payload with the per-group section
appended (`compose_per_cluster_payload`), validated against the item's
per-group contract (`parse_per_cluster_answer`) and re-asked with the
production re-ask builder (`reasoner.build_reask_prompt`) on an invalid
answer. Backend errors back off as the production `Reasoner` does
(`DEFAULT_RETRY_POLICY`); a deterministic 4xx ends the call.

The loop's rules, kept exactly as the bench ran them for R7:

- every re-ask is built from the first composed payload, so the corrective
  suffix appears once whatever the attempt number;
- a backend exception spends an attempt but does not mark the answer
  `invalid` (only a parse failure does);
- a failed run keeps the last response that came back (its text, usage and
  latency), even when a later attempt raised;
- unlike `Reasoner.run`, there is no neutral-image fallback on refusal.

Backend-agnostic, and imports nothing from `reasoning.rag`.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig
from reasoning.vlm.per_cluster_choice import (
    NONE_FEASIBLE,
    PerClusterCandidateSet,
    compose_per_cluster_payload,
    parse_per_cluster_answer,
    read_answer_keys,
)
from reasoning.vlm.reasoner import build_reask_prompt, invoke_backend
from reasoning.vlm.retry_policy import DEFAULT_RETRY_POLICY, RetryPolicy, classify_failure

ParseStatus = Literal["valid", "invalid", "failed"]


class PerClusterRunResult(BaseModel):
    """The outcome of one per-cluster M2 call (all attempts)."""

    model_config = ConfigDict(frozen=True)

    # SHA-256 of the first composed user prompt.
    prompt_sha256: str
    attempts: int = Field(ge=0)
    # "valid" first try, "invalid" valid after a re-ask, "failed" none valid.
    parse_status: ParseStatus
    # Label -> option id or `none_feasible`; None unless valid.
    choices: dict[str, str] | None = None
    # The model's JSON object of the accepted answer (empty unless valid).
    model_answer: dict[str, Any] = Field(default_factory=dict)
    # The last response that came back (accepted or not).
    raw_text: str | None = None
    token_usage: dict[str, int] | None = None
    latency_ms: int | None = None
    # One entry per attempt; None for an attempt that raised.
    attempt_token_usage: tuple[dict[str, int] | None, ...] = ()
    attempt_latency_ms: tuple[int | None, ...] = ()
    served_model: str | None = None
    backoff_sec: float = 0.0
    wall_ms: int = Field(default=0, ge=0)
    # The last parse error or backend exception ("Type: message").
    error: str | None = None

    @property
    def ok(self) -> bool:
        """Whether a valid answer was accepted."""
        return self.choices is not None


def run_per_cluster_choice(
    backend: VLMBackend,
    config: ReasonerConfig,
    base_payload: PromptPayload,
    candidates: PerClusterCandidateSet,
    retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
) -> PerClusterRunResult:
    """Ask once per attempt with the composed prompt; re-ask on invalid choices.

    Never raises: backend exceptions are recorded attempts.

    Args:
        backend: Any `VLMBackend`.
        config: Timeout per call, attempt budget, re-ask policy and sampling.
        base_payload: The live builder's payload (`build_prompt_payload`).
        candidates: The slots the section lists and the answer is checked on.
        retry_policy: Backoff between failed backend calls.

    Returns:
        The run result; `choices` set on a valid answer.
    """
    start = time.monotonic()
    first = compose_per_cluster_payload(base_payload, candidates)
    sha = hashlib.sha256(first.user_prompt.encode()).hexdigest()
    payload = first
    attempts = 0
    waited = 0.0
    failed_once = False
    last: BackendResponse | None = None
    error: str | None = None
    usage: list[dict[str, int] | None] = []
    latency: list[int | None] = []

    def result(**fields: Any) -> PerClusterRunResult:
        return PerClusterRunResult(
            prompt_sha256=sha,
            attempts=attempts,
            raw_text=None if last is None else last.text,
            token_usage=None if last is None else last.token_usage,
            latency_ms=None if last is None else last.latency_ms,
            attempt_token_usage=tuple(usage),
            attempt_latency_ms=tuple(latency),
            served_model=None if last is None else last.served_model,
            backoff_sec=round(waited, 3),
            wall_ms=int((time.monotonic() - start) * 1000),
            **fields,
        )

    while attempts < config.max_attempts:
        attempts += 1
        try:
            last = invoke_backend(backend, payload, config)
        except Exception as exc:  # one recorded attempt, as in `Reasoner.run`
            usage.append(None)
            latency.append(None)
            error = f"{type(exc).__name__}: {exc}"
            if classify_failure(exc) == "stop":
                break
            if attempts < config.max_attempts:
                waited += retry_policy.wait_before_retry(exc, attempts, waited)
            continue
        usage.append(last.token_usage)
        latency.append(last.latency_ms)
        parsed = parse_per_cluster_answer(last.text, candidates)
        if parsed.status == "choices":
            return result(
                parse_status="invalid" if failed_once else "valid",
                choices=dict(parsed.choices),
                model_answer=dict(parsed.model_answer),
                error=error if failed_once else None,
            )
        failed_once = True
        error = parsed.error
        if config.allow_reask:
            payload = build_reask_prompt(first, error or "invalid choices")
    return result(parse_status="failed", error=error)


class FixedGroupChoiceBackend:
    """A zero-network backend that answers the same rule in every group (sanity chooser).

    It reads the slot labels and allowed ids from the composed prompt's
    stated answer keys, so it needs no item.
    """

    def __init__(self, policy: Literal["first", "none_feasible"] = "first") -> None:
        """Fix the rule.

        Args:
            policy: "first" (the first listed option of every group) or
                "none_feasible" (every group).
        """
        self.policy = policy
        self.calls = 0

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Answer the rule's choice for every stated group.

        Args:
            payload: The composed payload.
            config: Ignored.

        Returns:
            The reply in the decision JSON shape plus `choices`.
        """
        self.calls += 1
        keys = read_answer_keys(payload.user_prompt)
        choices = {
            label: ids[0] if self.policy == "first" else NONE_FEASIBLE
            for label, ids in keys.items()
        }
        text = json.dumps(
            {
                "congestion_detected": True,
                "type": "deadlock",
                "involved_robots": [],
                "root_cause": "fixed-group-choice sanity backend",
                "strategy": "yield",
                "justification": "fixed-group-choice sanity backend",
                "choices": choices,
            }
        )
        return BackendResponse(text=text, backend_id="fixed-group-choice")


__all__ = [
    "FixedGroupChoiceBackend",
    "ParseStatus",
    "PerClusterRunResult",
    "run_per_cluster_choice",
]

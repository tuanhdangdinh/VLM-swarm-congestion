"""The `refusal_feedback` variant: the live prompt with both v4 refusal-feedback keys on.

Change 1 offers only the strategies M3 can ground on the item's scene; Change 2
states the episode's earlier withheld decisions, never shows a withheld
plan as accepted, and leaves out the plan-state block of a plan with nothing
in progress (`refusal_feedback_replay`). The production `Reasoner` and
parser answer, as in `baseline`. The episode is not re-simulated: earlier
outcomes are the recorded (feedback-off) ones.
"""

from __future__ import annotations

import hashlib

from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.refusal_feedback_replay import cached_episode_states, feedback_request
from benchmarks.vlm_bench.variants.base import ReplayContext, VariantAnswer
from reasoning.vlm.models import ReasonerRequest
from reasoning.vlm.prompt_builder import build_prompt_payload

REFUSAL_FEEDBACK_VARIANT = "refusal_feedback"


class RefusalFeedbackVariant:
    """The live request with `prompt_offer_groundable_strategies` and `refusal_feedback` on."""

    name = REFUSAL_FEEDBACK_VARIANT
    generator_version: str | None = None

    def __init__(self, window_sec: float = 300.0, max_entries: int = 3) -> None:
        self.window_sec = window_sec
        self.max_entries = max_entries

    def request(self, item: BenchItem, request: ReasonerRequest) -> ReasonerRequest:
        """The item's request with both changes applied (no backend call).

        Args:
            item: The bench item.
            request: The rebuilt live request.

        Returns:
            The modified request.
        """
        states = cached_episode_states(item.bundle, self.window_sec, self.max_entries)
        return feedback_request(request, item, states.get(item.request_id))

    def answer(
        self, item: BenchItem, request: ReasonerRequest, context: ReplayContext
    ) -> VariantAnswer:
        """Run the production `Reasoner` on the modified request.

        Args:
            item: The bench item.
            request: The rebuilt live request.
            context: Backend, config and `Reasoner`.

        Returns:
            The reasoner's decision, attempts and parse status; `extra` records
            the offered set, the stated proposals and the plan-state source.
        """
        modified = self.request(item, request)
        user = build_prompt_payload(modified).user_prompt
        result = context.reasoner.run(modified)
        diag = result.diagnostics
        states = cached_episode_states(item.bundle, self.window_sec, self.max_entries)
        state = states.get(item.request_id)
        return VariantAnswer(
            decision=None if result.decision is None else result.decision.model_dump(mode="json"),
            prompt_sha256=hashlib.sha256(user.encode()).hexdigest(),
            attempts=diag.attempts,
            parse_status=diag.parse_status,
            raw_text=result.raw_text,
            token_usage=diag.token_usage,
            latency_ms=diag.latency_ms,
            extra={
                "offered_strategies": list(modified.offered_strategies or ()),
                "refused_proposals": len(modified.refused_proposals or ()),
                "plan_state_source": None if state is None else state.plan_state_source,
            },
        )

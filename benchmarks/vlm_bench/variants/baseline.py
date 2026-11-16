"""The `baseline` variant: the live prompt builder and the production `Reasoner`, as is."""

from __future__ import annotations

import hashlib

from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.variants.base import ReplayContext, VariantAnswer
from reasoning.vlm.models import ReasonerRequest
from reasoning.vlm.prompt_builder import build_prompt_payload


class BaselineVariant:
    """The live M2 request, prompt and parser, unchanged."""

    name = "baseline"
    generator_version: str | None = None

    def answer(
        self, item: BenchItem, request: ReasonerRequest, context: ReplayContext
    ) -> VariantAnswer:
        """Run the production `Reasoner` on the rebuilt live request.

        Args:
            item: The bench item (unused; the request carries everything).
            request: The rebuilt live request.
            context: Backend, config and `Reasoner`.

        Returns:
            The reasoner's decision, attempts and parse status.
        """
        user = build_prompt_payload(request).user_prompt
        result = context.reasoner.run(request)
        diag = result.diagnostics
        return VariantAnswer(
            decision=None if result.decision is None else result.decision.model_dump(mode="json"),
            prompt_sha256=hashlib.sha256(user.encode()).hexdigest(),
            attempts=diag.attempts,
            parse_status=diag.parse_status,
            raw_text=result.raw_text,
            token_usage=diag.token_usage,
            latency_ms=diag.latency_ms,
        )

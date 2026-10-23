"""The prompt-variant plugin contract of the VLM bench `replay` mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from benchmarks.vlm_bench.models import BenchItem
from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.models import ReasonerConfig, ReasonerRequest
from reasoning.vlm.reasoner import Reasoner


@dataclass(frozen=True)
class ReplayContext:
    """What a variant may call: the cached backend, its config and the production `Reasoner`."""

    backend: VLMBackend
    reasoner_config: ReasonerConfig
    reasoner: Reasoner


class VariantAnswer(BaseModel):
    """One variant's answer on one item, in the existing decision schema."""

    model_config = ConfigDict(frozen=True)

    decision: dict[str, Any] | None
    # SHA-256 of the user prompt the first attempt sent (the composed prompt).
    prompt_sha256: str
    attempts: int
    parse_status: str
    raw_text: str | None = None
    n_candidates: int | None = None
    token_usage: dict[str, int] | None = None
    latency_ms: int | None = None
    note: str | None = None
    # Option-list variants: the presented number chosen, the same option's
    # number in the unshuffled list, the presented order (unshuffled numbers,
    # slot 1 first) and the per-item shuffle seed (None when not shuffled).
    option_number: int | None = None
    original_option: int | None = None
    option_order: tuple[int, ...] | None = None
    shuffle_item_seed: int | None = None


class PromptVariant(Protocol):
    """A prompt/representation variant: rebuilt live request in, scored decision out."""

    name: str
    # Version of the variant's extra input generator (None when it has none).
    generator_version: str | None

    def answer(
        self, item: BenchItem, request: ReasonerRequest, context: ReplayContext
    ) -> VariantAnswer:
        """Ask the backend on one item and map the reply to a decision dict.

        Args:
            item: The bench item.
            request: The live request, rebuilt by `run.rebuild_request`.
            context: Backend, config and `Reasoner`.

        Returns:
            The answer; backend or parse failures give `decision=None`.
        """
        ...

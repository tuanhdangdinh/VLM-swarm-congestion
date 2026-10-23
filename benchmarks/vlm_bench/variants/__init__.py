"""Prompt-variant registry of the VLM bench `replay` mode.

`baseline` is the live builder and `Reasoner` as is; `grounding_first` appends
the M3-executable option list (v4 lever 1).
"""

from benchmarks.vlm_bench.variants.base import PromptVariant, ReplayContext, VariantAnswer
from benchmarks.vlm_bench.variants.baseline import BaselineVariant
from benchmarks.vlm_bench.variants.grounding_first import (
    GENERATOR_VERSION,
    CandidateSet,
    ExecutableOption,
    FixedOptionBackend,
    GroundingFirstVariant,
    compose_payload,
    executed_key,
    generate_candidates,
    parse_option_answer,
    render_candidate_section,
)

VARIANTS: dict[str, PromptVariant] = {
    variant.name: variant for variant in (BaselineVariant(), GroundingFirstVariant())
}


def list_variants() -> list[str]:
    """The registered variant names.

    Returns:
        The names, sorted.
    """
    return sorted(VARIANTS)


def get_variant(name: str) -> PromptVariant:
    """Look a variant up by name.

    Args:
        name: The variant name.

    Returns:
        The variant.

    Raises:
        ValueError: For an unknown name.
    """
    if name not in VARIANTS:
        raise ValueError(f"unknown prompt variant {name!r}; known: {list_variants()}")
    return VARIANTS[name]


__all__ = [
    "GENERATOR_VERSION",
    "VARIANTS",
    "BaselineVariant",
    "CandidateSet",
    "ExecutableOption",
    "FixedOptionBackend",
    "GroundingFirstVariant",
    "PromptVariant",
    "ReplayContext",
    "VariantAnswer",
    "compose_payload",
    "executed_key",
    "generate_candidates",
    "get_variant",
    "list_variants",
    "parse_option_answer",
    "render_candidate_section",
]

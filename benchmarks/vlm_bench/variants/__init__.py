"""Prompt-variant registry of the VLM bench `replay` mode.

`baseline` is the live builder and `Reasoner` as is; `grounding_first` appends
the M3-executable option list (v4 lever 1; `gf_cluster` is its v2 generator,
options per observed group, v4 lever 2).
"""

from benchmarks.vlm_bench.variants.base import PromptVariant, ReplayContext, VariantAnswer
from benchmarks.vlm_bench.variants.baseline import BaselineVariant
from benchmarks.vlm_bench.variants.gf_cluster import (
    GENERATOR_VERSION_V2,
    ClusterCandidateSet,
    ClusterOption,
    GroundingFirstClusterVariant,
    ObservedGroup,
    compose_cluster_payload,
    executed_key_v2,
    generate_cluster_candidates,
    observed_groups,
    render_cluster_section,
    shuffle_cluster_candidates,
)
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
    shuffle_candidates,
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
    "GENERATOR_VERSION_V2",
    "VARIANTS",
    "BaselineVariant",
    "CandidateSet",
    "ClusterCandidateSet",
    "ClusterOption",
    "ExecutableOption",
    "FixedOptionBackend",
    "GroundingFirstClusterVariant",
    "GroundingFirstVariant",
    "ObservedGroup",
    "PromptVariant",
    "ReplayContext",
    "VariantAnswer",
    "compose_cluster_payload",
    "compose_payload",
    "executed_key",
    "executed_key_v2",
    "generate_candidates",
    "generate_cluster_candidates",
    "get_variant",
    "list_variants",
    "observed_groups",
    "parse_option_answer",
    "render_candidate_section",
    "render_cluster_section",
    "shuffle_candidates",
    "shuffle_cluster_candidates",
]

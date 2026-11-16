"""Prompt-variant registry of the VLM bench `replay` mode.

`baseline` is the live builder and `Reasoner` as is; `grounding_first` appends
the M3-executable option list (v4 lever 1; `gf_cluster` is its v2 generator,
options per observed group, v4 lever 2); `grounding_first_per_cluster` asks
for one choice per observed group over the v2 options (`per_cluster`, v4
lever 3); `refusal_feedback` turns on both v4 refusal-feedback keys
(offered strategies, withheld-decision feedback).
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
from benchmarks.vlm_bench.variants.per_cluster import (
    GENERATOR_VERSION_PER_CLUSTER,
    NONE_FEASIBLE,
    PER_CLUSTER_VARIANT,
    FixedGroupChoiceBackend,
    GroundingFirstPerClusterVariant,
    PerClusterCandidateSet,
    compose_per_cluster_payload,
    parse_per_cluster_answer,
    per_cluster_candidates,
    render_per_cluster_section,
)
from benchmarks.vlm_bench.variants.refusal_feedback import (
    REFUSAL_FEEDBACK_VARIANT,
    RefusalFeedbackVariant,
)

VARIANTS: dict[str, PromptVariant] = {
    variant.name: variant
    for variant in (
        BaselineVariant(),
        GroundingFirstVariant(),
        GroundingFirstPerClusterVariant(),
        RefusalFeedbackVariant(),
    )
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
    "GENERATOR_VERSION_PER_CLUSTER",
    "GENERATOR_VERSION_V2",
    "VARIANTS",
    "BaselineVariant",
    "CandidateSet",
    "ClusterCandidateSet",
    "ClusterOption",
    "ExecutableOption",
    "FixedGroupChoiceBackend",
    "FixedOptionBackend",
    "GroundingFirstClusterVariant",
    "GroundingFirstPerClusterVariant",
    "GroundingFirstVariant",
    "NONE_FEASIBLE",
    "ObservedGroup",
    "PER_CLUSTER_VARIANT",
    "PerClusterCandidateSet",
    "PromptVariant",
    "REFUSAL_FEEDBACK_VARIANT",
    "RefusalFeedbackVariant",
    "ReplayContext",
    "VariantAnswer",
    "compose_cluster_payload",
    "compose_payload",
    "compose_per_cluster_payload",
    "executed_key",
    "executed_key_v2",
    "generate_candidates",
    "generate_cluster_candidates",
    "get_variant",
    "list_variants",
    "observed_groups",
    "parse_option_answer",
    "parse_per_cluster_answer",
    "per_cluster_candidates",
    "render_candidate_section",
    "render_cluster_section",
    "render_per_cluster_section",
    "shuffle_candidates",
    "shuffle_cluster_candidates",
]

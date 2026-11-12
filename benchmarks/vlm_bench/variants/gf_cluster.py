"""Grounding-first v2: options enumerated per observed group (v4 lever 2).

v1 (`grounding_first.generate_candidates`) lists pair options only, so an
item whose conflict holds 3-5 robots, or two clusters, cannot be named in
full. v2 first groups the robots from the scene state alone, then probes
group-level options with the same real offline M3 and the same strict
"executes as asked" rule, and lists the v1 pair options under their group.

The grouping rule, the option enumeration and probing, and the executed keys
are shared with the live path and live in `reasoning.rag.cluster_options`
(the option models in `reasoning.vlm.executable_options`); their module
docstrings state the rules. This module adapts a `BenchItem` to those plain
inputs (scene -> `SnapshotFrame`, recorded classical `r_conflict_m` ->
`GroupingParams`, `grounder_offline.ground_command` as the probe), and keeps
the v2 single-choice prompt section and the bench variant. It never reads
`item.gt`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from benchmarks.vlm_bench.grounder_offline import ground_command, item_frame
from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.variants.grounding_first import CandidateSet, GroundingFirstVariant
from reasoning.baselines import ClassicalParams
from reasoning.rag import cluster_options
from reasoning.rag.cluster_options import GROUPING_RULE as GROUPING_RULE
from reasoning.rag.cluster_options import SEED_STATUSES as SEED_STATUSES
from reasoning.rag.cluster_options import GroupingParams as GroupingParams
from reasoning.rag.cluster_options import executed_key_v2 as executed_key_v2
from reasoning.vlm.executable_options import GENERATOR_VERSION_V2 as GENERATOR_VERSION_V2
from reasoning.vlm.executable_options import OUTSIDE as OUTSIDE
from reasoning.vlm.executable_options import SPAN as SPAN
from reasoning.vlm.executable_options import ClusterCandidateSet as ClusterCandidateSet
from reasoning.vlm.executable_options import ClusterOption as ClusterOption
from reasoning.vlm.executable_options import ObservedGroup as ObservedGroup
from reasoning.vlm.executable_options import SectionFlag as SectionFlag
from reasoning.vlm.executable_options import (
    shuffle_cluster_candidates as shuffle_cluster_candidates,
)
from reasoning.vlm.models import PromptPayload


def grouping_params(item: BenchItem) -> GroupingParams:
    """The grouping rule for one item: the episode's recorded classical `r_conflict_m`.

    Args:
        item: The bench item.

    Returns:
        The params (the `ClassicalParams` default when nothing was recorded).
    """
    params = ClassicalParams(**(item.classical.params or {}))
    return GroupingParams(threshold_m=params.r_conflict_m)


def observed_groups(
    item: BenchItem, params: GroupingParams | None = None
) -> tuple[ObservedGroup, ...]:
    """Proximity groups from the item's scene state (never its GT).

    Args:
        item: The bench item.
        params: The rule; None reads `grouping_params(item)`.

    Returns:
        The groups, labelled A, B, ... by size desc, then closest pair, then ids
        (`reasoning.rag.cluster_options.observed_groups`).
    """
    return cluster_options.observed_groups(item_frame(item), params or grouping_params(item))


def generate_cluster_candidates(
    item: BenchItem,
    include_wait: bool = True,
    offgroup: SectionFlag = "drop",
    cross_group: SectionFlag = "drop",
    params: GroupingParams | None = None,
) -> ClusterCandidateSet:
    """Enumerate the item's v2 options: group-level first, pairs under their group.

    Reads only the scene state, the recorded params/overlay (through the
    offline grounder) and the recorded classical `r_conflict_m`; never
    `item.gt`. The enumeration is `reasoning.rag.cluster_options.generate_cluster_candidates`
    with `ground_command(item, ...)` as the probe.

    Args:
        item: The bench item.
        include_wait: Also list `temporary_wait` options (last in each section).
        offgroup: Keep or drop the "outside any observed group" section.
        cross_group: Keep or drop the "spans two groups" section.
        params: The grouping rule; None reads `grouping_params(item)`.

    Returns:
        The options in section order (groups A, B, ..., then span, then
        outside), deduplicated on `executed_key_v2`.
    """
    params = params or grouping_params(item)
    return cluster_options.generate_cluster_candidates(
        item_frame(item),
        item.item_id,
        params,
        lambda decision: ground_command(item, decision),
        include_wait,
        offgroup,
        cross_group,
    )


def _section_title(name: str, groups: Sequence[ObservedGroup]) -> str:
    if name == SPAN:
        return "Pairs spanning two observed groups"
    if name == OUTSIDE:
        return "Outside any observed group" if groups else "No observed group in this scene"
    group = next(g for g in groups if g.label == name)
    return f"Group {name}: {', '.join(group.robots)}"


def render_cluster_section(candidates: ClusterCandidateSet) -> str:
    """The grouped option list and the answer instruction appended to the live prompt.

    Args:
        candidates: The item's v2 options (any within-section order).

    Returns:
        The section text; the last number is always "none of the above".
    """
    lines = [
        "Executable options, grouped by observed group. A group is robots that are "
        f"stopped, slow or stale within {candidates.threshold_m:.2f} m of each other "
        "(a moving robot that close joins the group). Each option below was checked on "
        "this exact scene by the motion planner that will execute your answer; any other "
        "choice would be refused or would not move a robot. Choose within the group that "
        "holds the conflict:"
    ]
    if not candidates.options:
        lines.append("(no executable option was found for this scene)")
    runs: list[tuple[str, int, int]] = []
    for number, option in enumerate(candidates.options, start=1):
        if runs and runs[-1][0] == option.section:
            runs[-1] = (option.section, runs[-1][1], number)
        else:
            runs.append((option.section, number, number))
    for name, first, last in runs:
        span = f"option {first}" if first == last else f"options {first}-{last}"
        lines.append(f"{_section_title(name, candidates.groups)} ({span})")
        for number in range(first, last + 1):
            lines.append(f"{number}) {candidates.options[number - 1].text}")
    none_number = len(candidates.options) + 1
    lines.append(
        f"{none_number}) none of the above: there is no congestion, or no listed option "
        "resolves it"
    )
    lines += [
        "",
        'Your strategy MUST be one of the numbered options above, or "none". Add one more '
        "field to the JSON object:",
        f'- "option": the number of the option you choose (1-{none_number}), or "none"',
        'State the reason for your choice in "justification". The chosen option\'s robots, '
        'strategy and yield robot are what will be executed; your own "involved_robots", '
        '"strategy" and "yield_robot" are not used.',
    ]
    return "\n".join(lines)


def compose_cluster_payload(base: PromptPayload, candidates: ClusterCandidateSet) -> PromptPayload:
    """The live payload with the grouped option section appended to its user prompt.

    Args:
        base: The live builder's payload, unchanged.
        candidates: The item's v2 options.

    Returns:
        The composed payload (system prompt and images unchanged).
    """
    user = f"{base.user_prompt}\n\n{render_cluster_section(candidates)}"
    return base.model_copy(update={"user_prompt": user})


class GroundingFirstClusterVariant(GroundingFirstVariant):
    """`grounding_first` with the v2 (observed-group) option generator."""

    generator_version: str | None = GENERATOR_VERSION_V2

    def __init__(
        self,
        include_wait: bool = True,
        shuffle_seed: int | None = None,
        offgroup: SectionFlag = "drop",
        cross_group: SectionFlag = "drop",
    ) -> None:
        """Configure the variant.

        Args:
            include_wait: List `temporary_wait` options too.
            shuffle_seed: When set, shuffle options within each section.
            offgroup: Keep or drop the "outside any observed group" section.
            cross_group: Keep or drop the "spans two groups" section.
        """
        super().__init__(include_wait=include_wait, shuffle_seed=shuffle_seed)
        self.offgroup = offgroup
        self.cross_group = cross_group

    def candidate_set(
        self, item: BenchItem
    ) -> tuple[CandidateSet, tuple[int, ...] | None, int | None]:
        """The item's v2 options as presented, with the shuffle order and per-item seed.

        Args:
            item: The bench item.

        Returns:
            The presented set, the presented order (None when not shuffled)
            and the per-item seed (or None).
        """
        candidates = generate_cluster_candidates(
            item, self.include_wait, self.offgroup, self.cross_group
        )
        if self.shuffle_seed is None:
            return candidates, None, None
        return shuffle_cluster_candidates(candidates, self.shuffle_seed)

    def compose(self, base: PromptPayload, candidates: CandidateSet) -> PromptPayload:
        """The live payload with the grouped option section appended.

        Args:
            base: The live builder's payload.
            candidates: The presented v2 options.

        Returns:
            The composed payload.
        """
        assert isinstance(candidates, ClusterCandidateSet)
        return compose_cluster_payload(base, candidates)

    def answer_extra(self, candidates: CandidateSet) -> dict[str, Any] | None:
        """Per-item grouping record for the run config.

        Args:
            candidates: The presented v2 options.

        Returns:
            Threshold, flags, groups and the option count per section.
        """
        assert isinstance(candidates, ClusterCandidateSet)
        return {
            "grouping_threshold_m": candidates.threshold_m,
            "offgroup": candidates.offgroup,
            "cross_group": candidates.cross_group,
            "groups": {g.label: list(g.robots) for g in candidates.groups},
            "section_counts": candidates.section_counts(),
        }

    def run_info(self) -> dict[str, Any]:
        """Run-level generator settings for the run config.

        Returns:
            The grouping rule and the section flags.
        """
        return {
            "grouping_rule": GROUPING_RULE,
            "grouping_threshold_source": "item.classical.params.r_conflict_m",
            "offgroup": self.offgroup,
            "cross_group": self.cross_group,
            "include_wait": self.include_wait,
        }

"""Executable-option contracts shown to M2: options M3 executes as asked, per observed group.

These are the data models of the grounding-first option lists (v4 levers 1-3):
an option is one decision the offline M3 probe grounded exactly as asked, and
it maps back to a `CongestionDecision` whose involved set, strategy, yielder
and crossing order are the probe's. The models live in M2 because they are
what the prompt lists and what an answer is mapped back to; M3
(`reasoning.rag.cluster_options`) builds them, and the per-group answer
contract (`reasoning.vlm.per_cluster_choice`) splits them into slots. This
module imports nothing from `reasoning.rag`, so the M3 -> M2 import direction
stays one-way.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from reasoning.vlm.models import CongestionDecision

GENERATOR_VERSION = "gf-candidates-v1"
GENERATOR_VERSION_V2 = "gf-candidates-v2"
OptionStrategy = Literal["yield", "reverse", "reroute", "temporary_wait"]
SectionFlag = Literal["keep", "drop"]
SPAN = "span"
OUTSIDE = "outside"
_RESOLVING: frozenset[str] = frozenset({"yield", "reverse", "reroute"})
_TYPES: frozenset[str] = frozenset({"deadlock", "bottleneck", "crowding", "anomaly"})


def _text(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and value.strip() else fallback


class RetreatPark(BaseModel):
    """The retreat M3 dispatches for a yield option (default stage-2 letter)."""

    model_config = ConfigDict(frozen=True)

    label: str | None = None
    x: float | None = None
    y: float | None = None
    backup_m: float | None = None
    lateral_m: float | None = None


class ExecutableOption(BaseModel):
    """One action M3 executes as asked on the item's scene."""

    model_config = ConfigDict(frozen=True)

    strategy: OptionStrategy
    # The probed `involved_robots`, in probe order; the mapped decision uses it verbatim.
    robots: tuple[str, ...]
    yield_robot: str | None = None
    # What M3 executes (`executed_key`); options are deduplicated on it.
    key: tuple[str, ...]
    separation_m: float
    park: RetreatPark | None = None
    text: str

    @property
    def resolving(self) -> bool:
        """Whether the option moves a robot (not a hold)."""
        return self.strategy in _RESOLVING

    def decision(self, model_answer: dict[str, Any] | None = None) -> dict[str, Any]:
        """This option as a decision dict in the existing schema.

        Only `type`, `root_cause` and `justification` come from the model;
        the involved set, strategy and yielder are the probe's, so the
        decision grounds exactly as the probe did.

        Args:
            model_answer: The model's parsed JSON object, or None.

        Returns:
            A validated `CongestionDecision` dump.
        """
        answer = model_answer or {}
        kind = answer.get("type")
        kind = kind.lower() if isinstance(kind, str) else None
        return CongestionDecision(
            congestion_detected=True,
            type=kind if kind in _TYPES else "deadlock",
            involved_robots=list(self.robots),
            root_cause=_text(answer.get("root_cause"), self.text),
            strategy=self.strategy,
            justification=_text(answer.get("justification"), self.text),
            yield_robot=self.yield_robot,
        ).model_dump(mode="json")


class CandidateSet(BaseModel):
    """The numbered executable options of one item."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    generator_version: str = GENERATOR_VERSION
    include_wait: bool = True
    options: tuple[ExecutableOption, ...] = ()

    @property
    def keys(self) -> frozenset[tuple[str, ...]]:
        """Executed keys of every option."""
        return frozenset(o.key for o in self.options)

    @property
    def resolving_keys(self) -> frozenset[tuple[str, ...]]:
        """Executed keys of the options that move a robot."""
        return frozenset(o.key for o in self.options if o.resolving)


class ObservedGroup(BaseModel):
    """One proximity group of robots observed in the scene state."""

    model_config = ConfigDict(frozen=True)

    label: str
    # Robot ids, sorted.
    robots: tuple[str, ...]
    # The MOVING robots that joined without linking.
    attached: tuple[str, ...] = ()
    min_separation_m: float


class ClusterOption(ExecutableOption):
    """A v2 option: an `ExecutableOption` placed in a section, with its crossing order."""

    # A group label ("A", "B", ...), `SPAN` or `OUTSIDE`.
    section: str
    # "pair_partial": one robot in the section's group, the other in no group.
    scope: Literal["group", "pair", "pair_partial"]
    crossing_order: tuple[str, ...] | None = None
    # v1's `executed_key` of the same command (no hold segment).
    base_key: tuple[str, ...]
    # Robots M3 holds with an unlinked wait inside a yield/reverse command.
    held: tuple[str, ...] = ()

    def decision(self, model_answer: dict[str, Any] | None = None) -> dict[str, Any]:
        """This option as a decision dict, crossing order included.

        Args:
            model_answer: The model's parsed JSON object, or None.

        Returns:
            A validated `CongestionDecision` dump; only `type`, `root_cause`
            and `justification` come from the model.
        """
        answer = model_answer or {}
        kind = answer.get("type")
        kind = kind.lower() if isinstance(kind, str) else None
        return CongestionDecision(
            congestion_detected=True,
            type=kind if kind in _TYPES else "deadlock",
            involved_robots=list(self.robots),
            root_cause=_text(answer.get("root_cause"), self.text),
            strategy=self.strategy,
            justification=_text(answer.get("justification"), self.text),
            yield_robot=self.yield_robot,
            crossing_order=None if self.crossing_order is None else list(self.crossing_order),
        ).model_dump(mode="json")


class ClusterCandidateSet(CandidateSet):
    """The numbered v2 options of one item, in section order."""

    generator_version: str = GENERATOR_VERSION_V2
    options: tuple[ClusterOption, ...] = ()
    groups: tuple[ObservedGroup, ...] = ()
    threshold_m: float
    offgroup: SectionFlag = "drop"
    cross_group: SectionFlag = "drop"

    @property
    def base_keys(self) -> frozenset[tuple[str, ...]]:
        """v1 executed keys of every option."""
        return frozenset(o.base_key for o in self.options)

    def section_counts(self) -> dict[str, int]:
        """Option count per section, in section order.

        Returns:
            Section -> count.
        """
        counts: dict[str, int] = {}
        for option in self.options:
            counts[option.section] = counts.get(option.section, 0) + 1
        return counts


def item_shuffle_seed(seed: int, item_id: str) -> int:
    """The per-item shuffle seed: a process-stable hash of the run seed and the item id.

    Args:
        seed: The run seed.
        item_id: The item id.

    Returns:
        A 64-bit integer seed.
    """
    return int(hashlib.sha256(f"{seed}:{item_id}".encode()).hexdigest()[:16], 16)


def shuffle_cluster_candidates(
    candidates: ClusterCandidateSet, seed: int
) -> tuple[ClusterCandidateSet, tuple[int, ...], int]:
    """Permute options within each section (sections keep their order; "none" stays last).

    Args:
        candidates: The item's options in generator order.
        seed: The run seed.

    Returns:
        The permuted set, the presented order as unshuffled 1-based numbers
        (slot 1 first), and the per-item seed (`item_shuffle_seed`).
    """
    item_seed = item_shuffle_seed(seed, candidates.item_id)
    rng = random.Random(item_seed)
    order: list[int] = []
    start = 0
    options = candidates.options
    while start < len(options):
        end = start
        while end < len(options) and options[end].section == options[start].section:
            end += 1
        block = list(range(start, end))
        rng.shuffle(block)
        order.extend(block)
        start = end
    permuted = candidates.model_copy(update={"options": tuple(options[i] for i in order)})
    return permuted, tuple(i + 1 for i in order), item_seed


__all__ = [
    "GENERATOR_VERSION",
    "GENERATOR_VERSION_V2",
    "OUTSIDE",
    "SPAN",
    "CandidateSet",
    "ClusterCandidateSet",
    "ClusterOption",
    "ExecutableOption",
    "ObservedGroup",
    "OptionStrategy",
    "RetreatPark",
    "SectionFlag",
    "item_shuffle_seed",
    "shuffle_cluster_candidates",
]

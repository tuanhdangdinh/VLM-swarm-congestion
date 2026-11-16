"""Grounding-first v2: options enumerated per observed group (v4 lever 2).

v1 (`grounding_first.generate_candidates`) lists pair options only, so an
item whose conflict holds 3-5 robots, or two clusters, cannot be named in
full. v2 first groups the robots from the scene state alone, then probes
group-level options with the same real offline M3 and the same strict
"executes as asked" rule, and lists the v1 pair options under their group.

Observed grouping (`observed_groups`), from what the live system has at
inference time and nothing else (never `item.gt`):

- A robot whose status is STOPPED, SLOW or STALE seeds a group. STALE is a
  seed because two robots close enough to occlude each other's marker go
  STALE together (the `CongestionDetector` close/slow-pair rule includes
  them for the same reason).
- Two seeds within `threshold_m` of each other (`<=`, the classical
  chooser's boundary) are linked; groups are the connected components of
  size >= 2. `threshold_m` is the episode's recorded classical
  `r_conflict_m` (1.5 m on every live item), the radius the live shadow uses
  for "in conflict".
- A MOVING robot within `threshold_m` of a group member joins the nearest
  such group, but links nothing: it cannot bridge two groups.
- Groups are labelled A, B, ... by size (desc), then closest pair, then ids.

Options per group, each probed with `grounder_offline.ground_command` and
kept only when M3 executes it as asked:

- `yield(Y, passers = group - Y)` for every Y (multi-passer yield, passers
  nearest Y first, sent as `crossing_order` with Y last). Kept when M3
  grounds a `yield` for Y itself. Derived-mode M3 may lane-scope the
  crossing (`order=lane_scoped`): the off-lane passers are then held by an
  unlinked wait. A yield may also hold a bystander whose route crosses the
  retreat (the A26 retreat shield). Either way the option text names the
  held robots and the key records them (`executed_key_v2`).
- `reverse(group)`: a `reverse` action and no `reverse=infeasible` tag.
- The v1 pair options whose two robots are both in the group, then
  `reroute(r)` for r in the group (waypoints on every reroute), then the
  v1 pairs with one robot in the group and the other in no group.
- `temporary_wait(group)` then the pair waits, last within the group.

Pairs with one robot in each of two groups go into a "spans two groups"
section, and pairs with neither robot in a group (and reroutes of a robot
in no group) into an "outside any observed group" section. Each section is a flag (`keep` or
`drop`, default `drop`). When the scene has no observed group, the outside
section is kept whatever the flag says, so the model still has options.

Options are deduplicated on the v2 executed key (`executed_key_v2`) in
presentation order, so a group option wins over a pair that executes the
same command.
"""

from __future__ import annotations

import itertools
import math
import random
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from benchmarks.vlm_bench.grounder_offline import ground_command
from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.variants.grounding_first import (
    CandidateSet,
    ExecutableOption,
    GroundingFirstVariant,
    OptionStrategy,
    RetreatPark,
    executed_key,
    item_shuffle_seed,
)
from reasoning.baselines import ClassicalParams
from reasoning.vlm.models import CongestionDecision, PromptPayload

GENERATOR_VERSION_V2 = "gf-candidates-v2"
SectionFlag = Literal["keep", "drop"]
SEED_STATUSES: frozenset[str] = frozenset({"STOPPED", "SLOW", "STALE"})
GROUPING_RULE = (
    "seeds: status STOPPED/SLOW/STALE; link seeds at separation <= threshold_m; "
    "components of size >= 2; a MOVING robot within threshold_m of a member joins "
    "the nearest group without linking; threshold_m = recorded classical r_conflict_m"
)
SPAN = "span"
OUTSIDE = "outside"
_TYPES: frozenset[str] = frozenset({"deadlock", "bottleneck", "crowding", "anomaly"})


class GroupingParams(BaseModel):
    """The observed-grouping rule's inputs."""

    model_config = ConfigDict(frozen=True)

    threshold_m: float = Field(gt=0)
    seed_statuses: frozenset[str] = SEED_STATUSES
    attach_moving: bool = True


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


def _text(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and value.strip() else fallback


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
        The groups, labelled A, B, ... by size desc, then closest pair, then ids.
    """
    params = params or grouping_params(item)
    robots = item.scene["robots"]
    pose = {r["robot_id"]: (float(r["x"]), float(r["y"])) for r in robots}
    seeds = [r["robot_id"] for r in robots if (r.get("status") or "") in params.seed_statuses]
    parent = {r: r for r in seeds}

    def find(robot_id: str) -> str:
        while parent[robot_id] != robot_id:
            robot_id = parent[robot_id]
        return robot_id

    for a, b in itertools.combinations(seeds, 2):
        if math.dist(pose[a], pose[b]) <= params.threshold_m:
            parent[find(a)] = find(b)
    members: dict[str, set[str]] = {}
    for robot_id in seeds:
        members.setdefault(find(robot_id), set()).add(robot_id)
    groups = [m for m in members.values() if len(m) >= 2]
    attached: list[set[str]] = [set() for _ in groups]
    if params.attach_moving:
        for robot in robots:
            rid = robot["robot_id"]
            if rid in seeds:
                continue
            near = [
                (min(math.dist(pose[rid], pose[m]) for m in group), index)
                for index, group in enumerate(groups)
            ]
            near = [n for n in near if n[0] <= params.threshold_m]
            if near:
                attached[min(near)[1]].add(rid)
    built = []
    for group, extra in zip(groups, attached, strict=True):
        ids = tuple(sorted(group | extra))
        built.append((ids, tuple(sorted(extra)), _min_separation(pose, ids)))
    built.sort(key=lambda g: (-len(g[0]), g[2], g[0]))
    return tuple(
        ObservedGroup(
            label=_label(i), robots=ids, attached=extra, min_separation_m=round(sep, 3)
        )
        for i, (ids, extra, sep) in enumerate(built)
    )


def _label(index: int) -> str:
    return chr(ord("A") + index) if index < 26 else f"G{index + 1}"


def _min_separation(pose: dict[str, tuple[float, float]], robots: Sequence[str]) -> float:
    pts = [pose[r] for r in robots if r in pose]
    if len(pts) < 2:
        return 0.0
    return min(math.dist(a, b) for a, b in itertools.combinations(pts, 2))


def executed_key_v2(strategy: str, command: dict[str, Any]) -> tuple[str, ...] | None:
    """v1's `executed_key` plus the robots a yield/reverse/reroute command holds.

    A derived-mode yield can lane-scope its crossing and hold the off-lane
    passers with an unlinked `temporary_wait`; v1's key ignores them, so a
    group yield and the pair yield it collapsed to would share a key while
    issuing different commands.

    Args:
        strategy: The decision's strategy.
        command: The grounded command.

    Returns:
        The v1 key, followed by `("hold", *sorted_held)` when the command
        holds robots outside the key; None when v1's key is None.
    """
    key = executed_key(strategy, command)
    if key is None or key[0] == "temporary_wait":
        return key
    held = _held(command, key)
    return key if not held else (*key, "hold", *held)


def _held(command: dict[str, Any], key: tuple[str, ...]) -> tuple[str, ...]:
    named = set(key[1:])
    return tuple(
        sorted(
            {
                a["robot_id"]
                for a in command.get("actions") or []
                if a.get("action") == "temporary_wait"
                and "linked_position" not in (a.get("parameters") or {})
                and a["robot_id"] not in named
            }
        )
    )


def _probe(
    strategy: str,
    robots: tuple[str, ...],
    yielder: str | None,
    crossing_order: tuple[str, ...] | None,
) -> dict[str, Any]:
    return {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": list(robots),
        "root_cause": "grounding-first candidate probe",
        "strategy": strategy,
        "justification": "grounding-first candidate probe",
        "yield_robot": yielder,
        "crossing_order": None if crossing_order is None else list(crossing_order),
    }


def _yield_text(
    yielder: str,
    passers: Sequence[str],
    held: Sequence[str],
    shielded: frozenset[str],
    park: RetreatPark,
    sep: float,
) -> str:
    where = (
        f"park {park.label or '?'} at ({park.x:.2f}, {park.y:.2f})"
        if park.x is not None and park.y is not None
        else "default park"
    )
    moves = ""
    if park.backup_m is not None:
        moves = f"; back {park.backup_m:.2f} m"
        if park.lateral_m:
            moves += f", side-step {park.lateral_m:+.2f} m"
    who = passers[0] if len(passers) == 1 else ", then ".join(passers) + " (in this order)"
    text = f"yield: {yielder} backs up and steps aside so {who} can pass ({where}{moves})"
    lane = [r for r in held if r not in shielded]
    shield = [r for r in held if r in shielded]
    if lane:
        verb = "holds" if len(lane) == 1 else "hold"
        text += f"; {' and '.join(lane)} {verb} in place, not in the crossing"
    if shield:
        verb = "holds" if len(shield) == 1 else "hold"
        text += f"; {' and '.join(shield)} {verb} in place, clear of the retreat path"
    return f"{text} [{sep:.2f} m apart]"


def _reverse_text(robots: Sequence[str], movers: Sequence[str], sep: float) -> str:
    still = [r for r in robots if r not in movers]
    verb = "backs" if len(movers) == 1 else "back"
    text = f"reverse: {' and '.join(movers)} {verb} straight out along the lane"
    if still:
        text += f" ({' and '.join(still)} not moved)"
    return f"{text} [{sep:.2f} m apart]"


def _wait_text(robots: Sequence[str], sep: float) -> str:
    return (
        f"temporary_wait: {' and '.join(robots)} hold in place until the way clears "
        f"[{sep:.2f} m apart]"
    )


def _option(
    item: BenchItem,
    pose: dict[str, tuple[float, float]],
    strategy: OptionStrategy,
    robots: tuple[str, ...],
    yielder: str | None,
    section: str,
    scope: Literal["group", "pair", "pair_partial"],
    crossing_order: tuple[str, ...] | None = None,
) -> ClusterOption | None:
    try:
        command = ground_command(item, _probe(strategy, robots, yielder, crossing_order))
    except Exception:  # an exception is a refusal for enumeration purposes
        return None
    base = executed_key(strategy, command)
    if base is None or base[0] != strategy:
        return None
    key = executed_key_v2(strategy, command)
    assert key is not None
    held = _held(command, base)
    sep = _min_separation(pose, robots)
    park = None
    if strategy == "yield":
        if base[1] != yielder:
            return None
        action = next(a for a in command["actions"] if a.get("action") == "yield")
        params = action.get("parameters") or {}
        park = RetreatPark(
            label=params.get("retreat_choice"),
            x=params.get("retreat_x_m"),
            y=params.get("retreat_y_m"),
            backup_m=params.get("backup_distance_m"),
            lateral_m=params.get("pull_off_lateral_m"),
        )
        shielded = frozenset(
            a["robot_id"]
            for a in command["actions"]
            if (a.get("parameters") or {}).get("retreat_shield_hold")
        )
        text = _yield_text(yielder, base[2:], held, shielded, park, sep)
    elif strategy == "reverse":
        text = _reverse_text(robots, base[1:], sep)
    elif strategy == "reroute":
        text = f"reroute: {' and '.join(base[1:])} follows the declared detour"
    else:
        text = _wait_text(robots, sep)
    return ClusterOption(
        strategy=strategy,
        robots=robots,
        yield_robot=yielder,
        key=key,
        separation_m=round(sep, 3),
        park=park,
        text=text,
        section=section,
        scope=scope,
        crossing_order=crossing_order,
        base_key=base,
        held=held,
    )


def _pair_section(
    pair: Sequence[str], member_of: dict[str, str]
) -> tuple[str, Literal["pair", "pair_partial"]]:
    labels = {member_of[r] for r in pair if r in member_of}
    if not labels:
        return OUTSIDE, "pair"
    if len(labels) > 1:
        return SPAN, "pair"
    inside = all(r in member_of for r in pair)
    return next(iter(labels)), "pair" if inside else "pair_partial"


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
    `item.gt`.

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
    groups = observed_groups(item, params)
    ids = [r["robot_id"] for r in item.scene["robots"]]
    pose = {r["robot_id"]: (float(r["x"]), float(r["y"])) for r in item.scene["robots"]}
    member_of = {r: g.label for g in groups for r in g.robots}
    sections: dict[str, list[list[ClusterOption | None]]] = {
        name: [[] for _ in range(10)]
        for name in [*(g.label for g in groups), SPAN, OUTSIDE]
    }
    # Buckets per section, in listing order: 0 group yields, 1 group reverse,
    # 2 pair yields, 3 pair reverses, 4 reroutes, 5 partial-pair yields,
    # 6 partial-pair reverses, 7 group wait, 8 pair waits, 9 partial-pair waits.
    # A partial pair has one robot in the group and one in no group.
    for group in groups:
        buckets = sections[group.label]
        for yielder in group.robots:
            passers = tuple(
                sorted(
                    (r for r in group.robots if r != yielder),
                    key=lambda r, y=yielder: (math.dist(pose[y], pose[r]), r),
                )
            )
            buckets[0].append(
                _option(
                    item, pose, "yield", (yielder, *passers), yielder, group.label, "group",
                    crossing_order=(*passers, yielder),
                )
            )
        buckets[1].append(_option(item, pose, "reverse", group.robots, None, group.label, "group"))
        if include_wait:
            buckets[7].append(
                _option(item, pose, "temporary_wait", group.robots, None, group.label, "group")
            )
    for yielder, passer in itertools.permutations(ids, 2):
        section, scope = _pair_section((yielder, passer), member_of)
        sections[section][2 if scope == "pair" else 5].append(
            _option(item, pose, "yield", (yielder, passer), yielder, section, scope)
        )
    for pair in itertools.combinations(ids, 2):
        section, scope = _pair_section(pair, member_of)
        sections[section][3 if scope == "pair" else 6].append(
            _option(item, pose, "reverse", pair, None, section, scope)
        )
        if include_wait:
            sections[section][8 if scope == "pair" else 9].append(
                _option(item, pose, "temporary_wait", pair, None, section, scope)
            )
    for robot in ids:
        section = member_of.get(robot, OUTSIDE)
        sections[section][4].append(_option(item, pose, "reroute", (robot,), None, section, "pair"))
    keep = {SPAN: cross_group == "keep", OUTSIDE: offgroup == "keep" or not groups}
    seen: set[tuple[str, ...]] = set()
    options: list[ClusterOption] = []
    for name, buckets in sections.items():
        if not keep.get(name, True):
            continue
        for index, bucket in enumerate(buckets):
            found = [o for o in bucket if o is not None]
            if index == 0:
                found.sort(key=lambda o: (_nearest(pose, o), o.robots))
            elif index not in (1, 7):
                found.sort(key=lambda o: (o.separation_m, o.robots))
            for option in found:
                if option.key not in seen:
                    seen.add(option.key)
                    options.append(option)
    return ClusterCandidateSet(
        item_id=item.item_id,
        include_wait=include_wait,
        options=tuple(options),
        groups=groups,
        threshold_m=params.threshold_m,
        offgroup=offgroup,
        cross_group=cross_group,
    )


def _nearest(pose: dict[str, tuple[float, float]], option: ClusterOption) -> float:
    yielder = option.yield_robot
    passers = [r for r in option.robots if r != yielder]
    if yielder is None or not passers:
        return 0.0
    return min(math.dist(pose[yielder], pose[r]) for r in passers)


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

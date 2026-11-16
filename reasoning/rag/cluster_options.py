"""Observed grouping and M3-executable option enumeration per group (v4 levers 2-3).

Shared by the offline VLM bench (`benchmarks/vlm_bench`, which adapts a
recorded item to these inputs) and, later, the live M5 path, so both run the
same grouping, probing and "executes as asked" rule (prereg-v3 A13(iii)).
Every function here takes plain inputs: a `SnapshotFrame`, the grouping
threshold, and a `ground(decision) -> command` callable (normally
`functools.partial(ground_probe, ProbeInputs(...))`). Nothing here can receive
ground truth.

Observed grouping (`observed_groups`), from what the live system has at
inference time and nothing else:

- A robot whose status is STOPPED, SLOW or STALE seeds a group. STALE is a
  seed because two robots close enough to occlude each other's marker go
  STALE together (the `CongestionDetector` close/slow-pair rule includes
  them for the same reason).
- Two seeds within `threshold_m` of each other (`<=`, the classical
  chooser's boundary) are linked; groups are the connected components of
  size >= 2. `threshold_m` is the episode's classical `r_conflict_m`
  (1.5 m on every live item), the radius the live shadow uses for
  "in conflict".
- A MOVING robot within `threshold_m` of a group member joins the nearest
  such group, but links nothing: it cannot bridge two groups.
- Groups are labelled A, B, ... by size (desc), then closest pair, then ids.

Options per group, each probed with `ground` and kept only when M3 executes
it as asked:

- `yield(Y, passers = group - Y)` for every Y (multi-passer yield, passers
  nearest Y first, sent as `crossing_order` with Y last). Kept when M3
  grounds a `yield` for Y itself. Derived-mode M3 may lane-scope the
  crossing (`order=lane_scoped`): the off-lane passers are then held by an
  unlinked wait. A yield may also hold a bystander whose route crosses the
  retreat (the A26 retreat shield). Either way the option text names the
  held robots and the key records them (`executed_key_v2`).
- `reverse(group)`: a `reverse` action and no `reverse=infeasible` tag.
- The pair options whose two robots are both in the group, then
  `reroute(r)` for r in the group (waypoints on every reroute), then the
  pairs with one robot in the group and the other in no group.
- `temporary_wait(group)` then the pair waits, last within the group.

Pairs with one robot in each of two groups go into a "spans two groups"
section, and pairs with neither robot in a group (and reroutes of a robot
in no group) into an "outside any observed group" section. Each section is a
flag (`keep` or `drop`, default `drop`). When the scene has no observed
group, the outside section is kept whatever the flag says, so the model still
has options.

Options are deduplicated on the v2 executed key (`executed_key_v2`) in
presentation order, so a group option wins over a pair that executes the
same command.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.command_grounder import YieldFeasibilityMode, ground_reasoner_result
from reasoning.rag.grounding_provenance import empty_reroute_fallback, summarize_yield_grounding
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_shield import RobotTaskIntent
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.executable_options import (
    OUTSIDE,
    SPAN,
    ClusterCandidateSet,
    ClusterOption,
    ObservedGroup,
    OptionStrategy,
    RetreatPark,
    SectionFlag,
)
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    SnapshotFrame,
    StaticObstacleInput,
)

SEED_STATUSES: frozenset[str] = frozenset({"STOPPED", "SLOW", "STALE"})
GROUPING_RULE = (
    "seeds: status STOPPED/SLOW/STALE; link seeds at separation <= threshold_m; "
    "components of size >= 2; a MOVING robot within threshold_m of a member joins "
    "the nearest group without linking; threshold_m = recorded classical r_conflict_m"
)
Grounder = Callable[[dict[str, Any]], dict[str, Any]]


class GroupingParams(BaseModel):
    """The observed-grouping rule's inputs."""

    model_config = ConfigDict(frozen=True)

    threshold_m: float = Field(gt=0)
    seed_statuses: frozenset[str] = SEED_STATUSES
    attach_moving: bool = True


class ProbeInputs(BaseModel):
    """Everything M3 needs to ground one probe decision on one scene (no ground truth).

    These are the inputs the live `InProcessPipeline` passes to
    `ground_reasoner_result`, minus the stage-2 retreat choice (probes do not
    run stage 2: a refusal is decided before it, so feasibility does not
    depend on it). Unknown fields are refused, so a caller cannot hand it
    ground truth by accident.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str
    # Recorded in the probe result's diagnostics only.
    backend_id: str = Field(min_length=1)
    snapshot: SnapshotFrame
    geometry: SceneGeometry | None = None
    static_obstacles: tuple[StaticObstacleInput, ...] = ()
    yield_feasibility_mode: YieldFeasibilityMode = "off"
    params: GroundingParams | None = None
    # Passed only when non-empty.
    priorities: dict[str, int] = Field(default_factory=dict)
    # Passed only when `params.dynamic_scene_arms`.
    goal_references: dict[str, tuple[float, float]] = Field(default_factory=dict)
    # Passed only when `params.dynamic_scene_arms` and `params.retreat_shield`.
    task_intents: dict[str, RobotTaskIntent] = Field(default_factory=dict)


def ground_probe(inputs: ProbeInputs, decision: dict[str, Any]) -> dict[str, Any]:
    """The grounded M3 command of one positive decision on the inputs' scene.

    Args:
        inputs: The scene and the episode's M3 inputs.
        decision: A positive decision dict (`CongestionDecision` fields).

    Returns:
        The command `ground_reasoner_result` returns, stage 2 not run.

    Raises:
        Exception: Whatever the grounder (or decision validation) raises;
            callers record it like the live `GROUNDING` terminal stage.
    """
    params = inputs.params
    frame = inputs.snapshot
    result = ReasonerResult(
        request_id=inputs.request_id,
        decision=CongestionDecision(**decision),
        raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id=inputs.request_id,
            backend_id=inputs.backend_id,
            attempts=1,
            parse_status="valid",
        ),
    )
    kwargs: dict[str, Any] = {}
    if inputs.priorities:
        kwargs["priorities"] = dict(inputs.priorities)
    if params is not None and params.dynamic_scene_arms:
        kwargs["goal_references"] = dict(inputs.goal_references)
        if params.retreat_shield:
            kwargs["task_intents"] = dict(inputs.task_intents)
    return ground_reasoner_result(
        result,
        robot_positions={r.robot_id: (r.x, r.y) for r in frame.robots},
        geometry=inputs.geometry,
        static_obstacles=inputs.static_obstacles,
        yield_feasibility_mode=inputs.yield_feasibility_mode,
        snapshot=frame,
        params=params,
        **kwargs,
    )


def observed_groups(snapshot: SnapshotFrame, params: GroupingParams) -> tuple[ObservedGroup, ...]:
    """Proximity groups from the scene state.

    Args:
        snapshot: The analysed scene (robot poses and statuses).
        params: The grouping rule.

    Returns:
        The groups, labelled A, B, ... by size desc, then closest pair, then ids.
    """
    robots = snapshot.robots
    pose = {r.robot_id: (float(r.x), float(r.y)) for r in robots}
    seeds = [r.robot_id for r in robots if (r.status or "") in params.seed_statuses]
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
            rid = robot.robot_id
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


def executed_key(strategy: str, command: dict[str, Any]) -> tuple[str, ...] | None:
    """What a grounded command executes, or None when it does not execute as asked.

    Args:
        strategy: The decision's strategy.
        command: The grounded command.

    Returns:
        `("yield", yielder, *crossing_order)`, `("reverse", *movers)`,
        `("reroute", *robots)` (waypoints on every reroute),
        `("temporary_wait", *robots)` (a wait the decision asked for), else
        None: refused, swapped-away, degraded or no-op commands.
    """
    # Infeasible when the yield gate refused or the yield degraded to an
    # empty-waypoint reroute (the bench's `outcome_of(command).feasible`).
    refusal = summarize_yield_grounding(command).refusal_reason
    if (refusal or empty_reroute_fallback(command)) is not None:
        return None
    actions = command.get("actions") or []
    tags = command.get("degradations") or []
    yields = [a for a in actions if a.get("action") == "yield"]
    if yields:
        params = yields[0].get("parameters") or {}
        order = params.get("crossing_order") or [params.get("passer_robot_id")]
        return ("yield", yields[0]["robot_id"], *(str(r) for r in order if r))
    reroutes = [a for a in actions if a.get("action") == "reroute"]
    if reroutes:
        if all((a.get("parameters") or {}).get("waypoints") for a in reroutes):
            return ("reroute", *sorted(a["robot_id"] for a in reroutes))
        return None
    reverses = [a for a in actions if a.get("action") == "reverse"]
    if reverses:
        if any(t.startswith("reverse=infeasible") for t in tags):
            return None
        return ("reverse", *sorted(a["robot_id"] for a in reverses))
    if strategy == "temporary_wait" and actions and all(
        a.get("action") == "temporary_wait" for a in actions
    ):
        return ("temporary_wait", *sorted(a["robot_id"] for a in actions))
    return None


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
    ground: Grounder,
    pose: dict[str, tuple[float, float]],
    strategy: OptionStrategy,
    robots: tuple[str, ...],
    yielder: str | None,
    section: str,
    scope: Literal["group", "pair", "pair_partial"],
    crossing_order: tuple[str, ...] | None = None,
) -> ClusterOption | None:
    try:
        command = ground(_probe(strategy, robots, yielder, crossing_order))
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
    pair: Sequence[str], member_of: Mapping[str, str]
) -> tuple[str, Literal["pair", "pair_partial"]]:
    labels = {member_of[r] for r in pair if r in member_of}
    if not labels:
        return OUTSIDE, "pair"
    if len(labels) > 1:
        return SPAN, "pair"
    inside = all(r in member_of for r in pair)
    return next(iter(labels)), "pair" if inside else "pair_partial"


def generate_cluster_candidates(
    snapshot: SnapshotFrame,
    item_id: str,
    params: GroupingParams,
    ground: Grounder,
    include_wait: bool = True,
    offgroup: SectionFlag = "drop",
    cross_group: SectionFlag = "drop",
) -> ClusterCandidateSet:
    """Enumerate the scene's v2 options: group-level first, pairs under their group.

    Args:
        snapshot: The analysed scene; robots are probed in its order.
        item_id: The id the option set is recorded under (a request id live).
        params: The grouping rule.
        ground: Grounds one probe decision into an M3 command (normally
            `functools.partial(ground_probe, inputs)`); an exception counts
            as a refusal.
        include_wait: Also list `temporary_wait` options (last in each section).
        offgroup: Keep or drop the "outside any observed group" section.
        cross_group: Keep or drop the "spans two groups" section.

    Returns:
        The options in section order (groups A, B, ..., then span, then
        outside), deduplicated on `executed_key_v2`.
    """
    groups = observed_groups(snapshot, params)
    ids = [r.robot_id for r in snapshot.robots]
    pose = {r.robot_id: (float(r.x), float(r.y)) for r in snapshot.robots}
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
                    ground, pose, "yield", (yielder, *passers), yielder, group.label, "group",
                    crossing_order=(*passers, yielder),
                )
            )
        buckets[1].append(
            _option(ground, pose, "reverse", group.robots, None, group.label, "group")
        )
        if include_wait:
            buckets[7].append(
                _option(ground, pose, "temporary_wait", group.robots, None, group.label, "group")
            )
    for yielder, passer in itertools.permutations(ids, 2):
        section, scope = _pair_section((yielder, passer), member_of)
        sections[section][2 if scope == "pair" else 5].append(
            _option(ground, pose, "yield", (yielder, passer), yielder, section, scope)
        )
    for pair in itertools.combinations(ids, 2):
        section, scope = _pair_section(pair, member_of)
        sections[section][3 if scope == "pair" else 6].append(
            _option(ground, pose, "reverse", pair, None, section, scope)
        )
        if include_wait:
            sections[section][8 if scope == "pair" else 9].append(
                _option(ground, pose, "temporary_wait", pair, None, section, scope)
            )
    for robot in ids:
        section = member_of.get(robot, OUTSIDE)
        sections[section][4].append(
            _option(ground, pose, "reroute", (robot,), None, section, "pair")
        )
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
        item_id=item_id,
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


__all__ = [
    "GROUPING_RULE",
    "SEED_STATUSES",
    "Grounder",
    "GroupingParams",
    "ProbeInputs",
    "executed_key",
    "executed_key_v2",
    "generate_cluster_candidates",
    "ground_probe",
    "observed_groups",
]

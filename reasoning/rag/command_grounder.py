import math
from collections.abc import Mapping, Sequence
from typing import Any, Literal, NamedTuple

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict

from reasoning.rag.maneuver_geometry import (
    Derivation,
    GroundingParams,
    derive_backup_distance,
    derive_escort_distance,
    derive_queued_passer_clearance,
    retreat_axes,
)
from reasoning.rag.retreat_candidates import (
    RetreatCandidate,
    generate_retreat_candidates,
    rank_candidates,
)
from reasoning.rag.scene_geometry import (
    SceneGeometry,
    arm_geometry,
    park_offset_m,
    passer_clearance_m,
    passer_travel_m,
    pull_off_lateral_m,
    required_room_m,
    yield_feasible,
    yield_retreat_room_m,
)
from reasoning.schemas import load_schema
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerResult,
    RetreatChoiceDecision,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)
from reasoning.vlm.output_parser import DECISION_DEGRADATION_TAGS

# What to do when the yielder M2 named cannot physically reach its park point:
# "off" grounds the named yielder regardless (every artifact collected before
# this gate existed was produced this way), "swap" re-grounds the yield to a
# feasible involved robot, "refuse" only ever degrades to a temporary wait.
YieldFeasibilityMode = Literal["off", "swap", "refuse"]


class CommandGroundingError(ValueError):
    """Raised when a grounded command is incomplete or invalid."""


# Fallback absolute map x the yielder parks at, used only when the caller
# supplies no `geometry`; with one, `park_offset_m` derives the offset from the
# declared scene instead. Hand-derived for head_on_deadlock: barrier blocks
# 0.90 m tall spanning x in [-1, 1] and an overhead camera at (0, 0, 3) put the
# blocks' projected top face on the marker plane (z = 0.21) at
# |x| ~= 1.0*(3-0.21)/(3-0.9) ~= 1.33; plus the 0.06 m marker half-width and a
# 0.3 m odometry margin that is ~1.69, rounded up to 1.8. 1.5 left only ~0.11 m
# of clearance and lost the marker in a live run (2026-09-16 run 7).
PARK_ABS_X_M = 1.8
# Bounds on the derived backup leg: under 0.3 m the reverse does not open the
# aisle at all, and 2.5 m is the longest run that stays inside the mapped aisle.
MIN_BACKUP_M = 0.3
MAX_BACKUP_M = 2.5
# Fallback margin added to the passer's distance-to-park so the hold only ends
# once the passer is clear of the parked yielder: 0.45 m safety radius (M4
# min_distance_m) plus a 0.20 m margin. Superseded by `passer_clearance_m` when
# the caller declares a geometry.
PASSER_CLEARANCE_M = 0.65
# Bounds on the derived escort leg. The upper bound must stay under what the
# 45 s hold backstop covers at the 0.1 m/s escort speed (4.5 m), otherwise the
# hold would expire mid-escort and both robots would re-enter the aisle.
MIN_ESCORT_M = 0.5
MAX_ESCORT_M = 4.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _passer_budget(escorts_m: Sequence[float]) -> float:
    # Backstop scale for a multi-passer yield, in units of one single-passer
    # hold: each passer costs max(1, escort / MAX_ESCORT_M), the ratio the
    # 45 s hold / 4.0 m escort pair was sized with. A backstop that expires
    # mid-crossing re-creates the 2026-07-03 re-deadlock.
    return sum(max(1.0, escort / MAX_ESCORT_M) for escort in escorts_m)


def resolve_robot_order(decision: CongestionDecision) -> list[str]:
    """Order the involved robots with the model's stated yielder listed first.

    Until this ordering existed, downstream grounding treated list position
    in `involved_robots` as the yielder channel; `yield_robot` makes that
    choice explicit instead.

    Scoped to `strategy == "yield"` only: `yield_robot` is only meaningful
    for that strategy, but other strategies also read position out of
    `involved_robots` for a different purpose (e.g. `reroute` sends
    `robot_ids[0]` to navigate and waits the rest). Reordering there on a
    stray or hallucinated `yield_robot` would silently swap which robot
    reroutes and which waits, so those strategies are left unchanged.

    Args:
        decision: Validated decision whose `yield_robot`, when set, is
            guaranteed by `CongestionDecision`'s validator to be a member of
            `involved_robots`.

    Returns:
        `involved_robots` unchanged unless `strategy == "yield"` and
        `yield_robot` is set and present, in which case `yield_robot` is
        moved to the front, with the remaining robots kept in their
        original relative order.
    """
    if (
        decision.strategy != "yield"
        or decision.yield_robot is None
        or decision.yield_robot not in decision.involved_robots
    ):
        return decision.involved_robots
    return [decision.yield_robot] + [
        robot_id for robot_id in decision.involved_robots if robot_id != decision.yield_robot
    ]


def validate_coordination_command(command: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema("coordination_command")
    errors = sorted(Draft202012Validator(schema).iter_errors(command), key=str)
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise CommandGroundingError(f"Command failed schema validation: {messages}")
    return command


def filter_command_robot_ids(
    command: dict[str, Any], allowed_robot_ids: set[str] | None
) -> dict[str, Any]:
    """Drop grounded actions for robots absent from the current scene snapshot.

    A yield's `crossing_order` (with its aligned `crossing_clear_m` /
    `crossing_escort_m`) is pruned of the dropped robots too, and the
    remaining waits' `linked_position` renumbered to match: M4's ordered
    release would otherwise admit, and hold the yielder for, a robot that
    received no command. A command that drops nothing is returned unchanged.
    """
    if allowed_robot_ids is None:
        return command

    actions = [
        action
        for action in command.get("actions", [])
        if action.get("robot_id") in allowed_robot_ids
    ]
    if not actions:
        raise CommandGroundingError(
            "Command contains no actions for known robots: "
            f"allowed={sorted(allowed_robot_ids)}"
        )
    if len(actions) != len(command.get("actions", [])):
        actions = _prune_crossing_order(actions, allowed_robot_ids)
    return {**command, "actions": actions}


def _prune_crossing_order(
    actions: list[dict[str, Any]], allowed_robot_ids: set[str]
) -> list[dict[str, Any]]:
    pruned_order: list[str] | None = None
    result: list[dict[str, Any]] = []
    for action in actions:
        parameters = action.get("parameters") or {}
        order = parameters.get("crossing_order")
        if action.get("action") == "yield" and isinstance(order, list):
            keep = [i for i, robot_id in enumerate(order) if robot_id in allowed_robot_ids]
            pruned_order = [order[i] for i in keep]
            parameters = {**parameters, "crossing_order": pruned_order}
            for key in ("crossing_clear_m", "crossing_escort_m"):
                values = parameters.get(key)
                if isinstance(values, list) and len(values) == len(order):
                    parameters[key] = [values[i] for i in keep]
            action = {**action, "parameters": parameters}
        result.append(action)
    if pruned_order is None:
        return result
    renumbered = []
    for action in result:
        parameters = action.get("parameters") or {}
        if "linked_position" in parameters and action.get("robot_id") in pruned_order:
            parameters = {
                **parameters,
                "linked_position": pruned_order.index(action["robot_id"]),
            }
            action = {**action, "parameters": parameters}
        renumbered.append(action)
    return renumbered


def _beyond_corridor_same_side(
    first: tuple[float, float],
    second: tuple[float, float],
    geometry: SceneGeometry,
) -> bool:
    """True when both robots sit past the corridor mouth on the same side.

    Backing either robot up from there re-enters or traverses the corridor
    instead of opening it (run C 2026-09-16 for yield; run 3 2026-09-17 for
    reverse, which drove a robot parked at its goal back into the aisle).
    """
    axis_index = 0 if geometry.corridor.axis == "x" else 1
    d_first = first[axis_index] - geometry.corridor.center_m
    d_second = second[axis_index] - geometry.corridor.center_m
    half_length = geometry.corridor.half_length_m
    both_beyond = abs(d_first) > half_length and abs(d_second) > half_length
    return both_beyond and d_first * d_second > 0


_ALIASED_STRATEGIES = frozenset({"convoy", "priority_override"})
# Goal bearings more than this far apart oppose each other (counter-flow).
_OPPOSED_BEARING_DEG = 90.0


class StrategyAlias(NamedTuple):
    """A `convoy` / `priority_override` decision mapped onto an ordered yield."""

    # The yield decision that is grounded in the original's place: its
    # `yield_robot` and full `crossing_order` (yielder last) are set.
    decision: CongestionDecision
    # The decided strategy, recorded as the `strategy=aliased:<strategy>` tag.
    requested_strategy: str


def resolve_strategy_alias(
    decision: CongestionDecision,
    snapshot: SnapshotFrame | None,
    *,
    geometry: SceneGeometry | None = None,
    priorities: Mapping[str, int] | None = None,
) -> StrategyAlias | None:
    """Map a `convoy` or `priority_override` decision onto the ordered yield.

    Neither strategy has a maneuver template of its own; both mean "one robot
    gives way, the rest pass in a stated order", which the single-yield
    primitive and M4's ordered release already execute (unified scene design,
    B2 and B3 grounding):

    - `convoy`: the yielder is the unique involved robot whose goal bearing
      opposes (> 90 degrees) every other involved robot's, while those others
      (at least two: the platoon) do not oppose each other. They cross in the
      decision's `crossing_order` when it is a valid permutation, else in
      queue order by distance to the gate (the corridor centre along its
      axis; the yielder without a geometry), ties by robot id.
    - `priority_override`: the beneficiary is the unique registry-max
      `priority` among the involved robots, which passes first; the robot
      below it yields. Only two involved robots can map: with more, every
      robot below the maximum would have to yield, which one yield cannot do.

    Args:
        decision: A validated decision.
        snapshot: The scene frame; `convoy` reads positions and goals from it.
        geometry: Declared scene geometry, locating the gate for queue order.
        priorities: M5's registry priorities; an absent robot is 0.

    Returns:
        The alias, or None when the decision uses neither strategy or no
        unique mapping exists (no unique counter-flow robot, a missing goal
        or position, no unique maximum priority, more than two robots). None
        leaves the decision to the legacy bounded wait tagged
        `strategy=unsupported`, the behaviour before the alias existed.
    """
    if not decision.congestion_detected or decision.strategy not in _ALIASED_STRATEGIES:
        return None
    involved = list(decision.involved_robots)
    if decision.strategy == "priority_override":
        levels = {rid: (priorities or {}).get(rid, 0) for rid in involved}
        if len(involved) != 2:
            return None
        top = max(levels.values())
        leaders = [rid for rid in involved if levels[rid] == top]
        if len(leaders) != 1:
            return None
        yielder = next(rid for rid in involved if rid != leaders[0])
        order = [leaders[0], yielder]
    else:
        if snapshot is None:
            return None
        states: dict[str, RobotStateInput] = {}
        for rid in involved:
            state = snapshot.find_robot(rid)
            if state is None or state.goal is None:
                return None
            states[rid] = state
        bearing = {
            rid: math.atan2(s.goal[1] - s.y, s.goal[0] - s.x)  # goal checked above
            for rid, s in states.items()
            if s.goal is not None
        }

        def opposed(a: str, b: str) -> bool:
            diff = abs(bearing[a] - bearing[b]) % (2 * math.pi)
            return math.degrees(min(diff, 2 * math.pi - diff)) > _OPPOSED_BEARING_DEG

        minority = [
            rid
            for rid in involved
            if len(involved) >= 3
            and all(opposed(rid, other) for other in involved if other != rid)
            and not any(
                opposed(a, b)
                for a in involved
                for b in involved
                if rid not in (a, b) and a < b
            )
        ]
        if len(minority) != 1:
            return None
        yielder = minority[0]
        platoon = [rid for rid in involved if rid != yielder]
        requested = [rid for rid in (decision.crossing_order or []) if rid != yielder]
        if sorted(requested) == sorted(platoon) and len(set(requested)) == len(platoon):
            passers = requested
        else:
            passers = sorted(
                platoon,
                key=lambda rid: (_gate_distance(states[rid], states[yielder], geometry), rid),
            )
        order = [*passers, yielder]
    aliased = decision.model_copy(
        update={"strategy": "yield", "yield_robot": yielder, "crossing_order": order}
    )
    return StrategyAlias(decision=aliased, requested_strategy=decision.strategy)


def _gate_distance(
    state: RobotStateInput, yielder: RobotStateInput, geometry: SceneGeometry | None
) -> float:
    if geometry is None:
        return math.hypot(state.x - yielder.x, state.y - yielder.y)
    coord = state.x if geometry.corridor.axis == "x" else state.y
    return abs(coord - geometry.corridor.center_m)


def _tag_alias(command: dict[str, Any], alias: StrategyAlias) -> dict[str, Any]:
    tags = [*command.get("degradations", []), f"strategy=aliased:{alias.requested_strategy}"]
    return validate_coordination_command({**command, "degradations": tags})


class _YieldFeasibility(NamedTuple):
    """Outcome of the feasibility gate: who yields, and why that changed."""

    robot_ids: list[str]
    grounded_from: str | None
    regrounded_reason: str | None
    refusal_reason: str | None


def _room_text(room_m: float | None) -> str:
    return "unbounded" if room_m is None else f"{room_m:.2f} m"


def _apply_yield_feasibility(
    robot_ids: list[str],
    robot_positions: dict[str, tuple[float, float]],
    static_obstacles: Sequence[StaticObstacleInput],
    geometry: SceneGeometry,
    mode: YieldFeasibilityMode,
) -> _YieldFeasibility:
    """Re-ground or refuse a yield whose named yielder cannot reach its park point.

    Each involved robot is scored as the candidate yielder: it would retreat to
    its own side of the corridor (away from the other robot), so the static
    obstacles beyond that corridor mouth bound how far back it can go. A robot
    with a declared junction arm is scored outward along that arm instead.

    Args:
        robot_ids: Involved robots, the decided yielder first.
        robot_positions: World-frame `(x, y)` in metres per robot id.
        static_obstacles: Fixed obstacles of the running scenario.
        geometry: Declared scene geometry.
        mode: `"swap"` may re-ground the yield to a feasible robot; `"refuse"`
            never swaps.

    Returns:
        The (possibly reordered) robot ids plus the provenance and reason
        strings the grounded command should carry.
    """
    axis_index = 0 if geometry.corridor.axis == "x" else 1
    positions = {
        robot_id: robot_positions.get(robot_id) for robot_id in robot_ids
    }
    if any(position is None for position in positions.values()):
        # Without every position the retreat side is undefined; leave the
        # decision alone rather than swapping on a partial scene.
        return _YieldFeasibility(robot_ids, None, None, None)

    rooms: dict[str, float | None] = {}
    feasible: dict[str, bool] = {}
    for robot_id, position in positions.items():
        assert position is not None
        robot_geometry, arm_side = arm_geometry(geometry, robot_id)
        if arm_side is not None:
            side = arm_side
        else:
            # The retreat side is taken against the first other involved
            # robot, which is exact for the two-robot head-on scenes this gate
            # targets; a junction declares each robot's arm instead.
            other = next(positions[o] for o in robot_ids if o != robot_id)
            assert other is not None
            side = -1.0 if position[axis_index] < other[axis_index] else 1.0
        rooms[robot_id] = yield_retreat_room_m(position, side, static_obstacles, robot_geometry)
        feasible[robot_id] = yield_feasible(position, side, static_obstacles, robot_geometry)

    decided = robot_ids[0]
    if feasible[decided]:
        return _YieldFeasibility(robot_ids, None, None, None)

    required = required_room_m(geometry)
    shortfall = (
        f"{decided} has {_room_text(rooms[decided])} retreat room "
        f"< {required:.2f} m required"
    )
    if mode == "swap":
        # Ties break on involved_robots order; the two-robot head-on scenes
        # this gate was written for never offer more than one candidate.
        candidates = [robot_id for robot_id in robot_ids[1:] if feasible[robot_id]]
        if candidates:
            chosen = candidates[0]
            reordered = [chosen] + [
                robot_id for robot_id in robot_ids if robot_id != chosen
            ]
            reason = f"yield re-grounded: {shortfall}; {chosen} feasible"
            return _YieldFeasibility(reordered, decided, reason, None)
        rooms_text = ", ".join(
            f"{robot_id} {_room_text(rooms[robot_id])}" for robot_id in robot_ids
        )
        return _YieldFeasibility(
            robot_ids,
            None,
            None,
            f"yield refused: no feasible yielder ({rooms_text} retreat room "
            f"< {required:.2f} m required)",
        )
    return _YieldFeasibility(robot_ids, None, None, f"yield refused: {shortfall}")


def ground_reasoner_result(
    result: ReasonerResult,
    robot_positions: dict[str, tuple[float, float]] | None = None,
    geometry: SceneGeometry | None = None,
    static_obstacles: Sequence[StaticObstacleInput] = (),
    yield_feasibility_mode: YieldFeasibilityMode = "off",
    *,
    snapshot: SnapshotFrame | None = None,
    params: GroundingParams | None = None,
    retreat_choice: RetreatChoiceDecision | None = None,
    crossing_order: Sequence[str] | None = None,
    priorities: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Convert a validated VLM decision into an executable coordination command.

    This is a small deterministic bridge until the full retrieval-backed M3
    grounder is restored. yield/reverse emit a bounded backward clearing
    maneuver (the yielding robot reverses to open a blocked aisle), temporary_wait
    cancels Nav2 goals, reroute forwards explicit waypoints when present, and the
    remaining semantic strategies degrade to a temporary wait rather than
    inventing unsafe motion. A `convoy` or `priority_override` decision that
    maps uniquely onto an ordered yield (`resolve_strategy_alias`) is grounded
    as that yield, in either mode, and tagged `strategy=aliased:<strategy>`;
    one that does not keeps the bounded wait.

    When `robot_positions` carries both yield participants, the yield distances
    are derived from where the robots actually are instead of the legacy
    constants sized for one assumed standoff pose. Deadlock onset is bimodal in
    this scenario — a nose-to-nose standoff near x=0 or a planner stall at ~1 m
    separation (observed 2026-09-16) — and fixed distances cannot suit both.

    When `geometry` is also supplied, the park point, sidestep and escort
    clearance are derived from that declared scene instead of the fallback
    constants above, so no scenario dimensions are hidden in M3. In that case a
    yield is refused — and degraded to a `temporary_wait` for every involved
    robot, like the remaining semantic strategies — when both robots already
    sit beyond the corridor on the same side, since the park point would then
    be on the far side and a reverse there would traverse the corridor instead
    of opening it.

    Everything above is the legacy mode: `params=None` or `params.mode ==
    "legacy"`, byte-identical to the grounder before the mode switch existed,
    whatever `snapshot` and `retreat_choice` say, for every command with at
    most one passer. A legacy yield with two or more passers (2026-09-28)
    also commands every passer in `crossing_order` for M4's ordered
    hold-until-last release (see `_ground_legacy`). With
    `params.mode == "derived"` the rev-8 Appendix A path runs instead (see
    `_ground_derived`): the snapshot replaces `robot_positions`, distances are
    feasibility-banded instead of clamped, the retreat is one of the ranked,
    swept-path-validated candidates, and the command carries a `degradations`
    list (tag vocabulary in `DEGRADATION_TAGS`).

    Args:
        result: Validated M2 reasoner output whose decision is grounded.
        robot_positions: Optional map of robot_id to world-frame `(x, y)` in
            metres, from the M5 scene snapshot. When it covers both the yielder
            and the passer, yield distances are scene-derived; otherwise the
            legacy fixed distances are used.
        geometry: Optional declared scene geometry (from M5 config). With it the
            yield park offset, sidestep and passer clearance are computed from
            the corridor, camera and robot dimensions; without it the fallback
            constants sized for head_on_deadlock apply.
        static_obstacles: Fixed obstacles of the running scenario, from M5
            config. Only read by the yield feasibility gate; an empty sequence
            makes that gate a no-op whatever `yield_feasibility_mode` says.
        yield_feasibility_mode: Whether a yield may be re-grounded away from the
            robot M2 named. `"off"` (the default) grounds it verbatim, `"swap"`
            hands the yield to a feasible involved robot when the named one is
            boxed in, `"refuse"` degrades to a temporary wait instead. The gate
            needs both `geometry` and `robot_positions` (in derived mode, the
            snapshot), and runs before any retreat candidate is generated.
        snapshot: Derived mode only: the scene frame every distance and
            candidate is derived from; `robot_positions` is ignored there. Must
            be the frame `prepare_retreat_selection` rendered stage 2 from, or
            the letters may name different poses. None (or a frame missing an
            involved robot) degrades a spatial strategy to a non-spatial wait.
        params: Grounding parameters and the mode switch; None means legacy.
        retreat_choice: Derived mode only: the parsed stage-2 answer. None or
            a letter that names no validated candidate grounds the top-ranked
            candidate instead, tagged `retreat=default:*`.
        crossing_order: Passing order for the non-yielders, overriding the
            decision's own. None reads `decision.crossing_order` (prompt-v2
            field; every involved robot) minus the grounded yielder. Must be a
            permutation of the involved robots minus the grounded yielder,
            else the involved-robots order is used (and tagged, in derived
            mode). Legacy mode reads it only for a yield with two or more
            passers.
        priorities: M5's registry priorities (robot id -> priority; absent
            means 0), which the prompt never sees. Read only to resolve a
            `priority_override` decision's beneficiary; None or empty leaves
            every command as it was before the field existed.

    Returns:
        Schema-validated coordination command dict.

    Raises:
        CommandGroundingError: If the decision is empty, reports no congestion,
            or names an unsupported strategy, or if the built command fails
            schema validation.
    """
    alias = (
        None
        if result.decision is None
        else resolve_strategy_alias(
            result.decision, snapshot, geometry=geometry, priorities=priorities
        )
    )
    if alias is not None:
        # Executed exactly as the equivalent yield; only the tag differs.
        result = result.model_copy(update={"decision": alias.decision})
    if params is not None and params.mode == "derived":
        command = _ground_derived(
            result,
            snapshot=snapshot,
            params=params,
            retreat_choice=retreat_choice,
            crossing_order=crossing_order,
            geometry=geometry,
            static_obstacles=static_obstacles,
            yield_feasibility_mode=yield_feasibility_mode,
        )
    else:
        command = _ground_legacy(
            result,
            robot_positions,
            geometry,
            static_obstacles,
            yield_feasibility_mode,
            crossing_order=crossing_order,
        )
    return command if alias is None else _tag_alias(command, alias)


def _legacy_passer_order(
    robot_ids: Sequence[str],
    decision: CongestionDecision,
    crossing_order: Sequence[str] | None,
) -> list[str]:
    # The robots after the (post-gate) yielder, in the requested crossing
    # order when one is given and is a permutation of them. Two robots have
    # one passer, so any order is moot there.
    rest = list(robot_ids[1:])
    if len(rest) < 2:
        return rest
    requested = crossing_order if crossing_order is not None else decision.crossing_order
    if requested is None:
        return rest
    candidate = [robot_id for robot_id in requested if robot_id != robot_ids[0]]
    if sorted(candidate) == sorted(rest) and len(set(candidate)) == len(rest):
        return candidate
    return rest


def _first_passer_refusal(
    yielder_id: str,
    passer_order: Sequence[str],
    robot_positions: dict[str, tuple[float, float]] | None,
) -> str | None:
    # The park side and the backup are computed away from passer_order[0],
    # which M4 treats as the standoff partner (escorted and pair-exempt from
    # the start). A queued robot named first would put the yielder's reverse
    # onto it, unguarded, or make it cross through the robot ahead of it. So
    # the first passer must be the passer nearest the yielder; anything else,
    # or an order that cannot be checked, is refused rather than reordered, so
    # the executed order is always the decided one.
    robots = [yielder_id, *passer_order]
    if robot_positions is None or any(r not in robot_positions for r in robots):
        return "yield refused: crossing order unverifiable without every robot's position"
    yx, yy = robot_positions[yielder_id]
    distance = {
        robot_id: math.hypot(robot_positions[robot_id][0] - yx, robot_positions[robot_id][1] - yy)
        for robot_id in passer_order
    }
    first = passer_order[0]
    if distance[first] > min(distance[r] for r in passer_order[1:]):
        return (
            f"yield refused: first passer {first} is not the passer nearest the "
            f"yielder {yielder_id}"
        )
    return None


def _ground_legacy(
    result: ReasonerResult,
    robot_positions: dict[str, tuple[float, float]] | None,
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
    crossing_order: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Scenario-tuned pre-rev-8 bridge; its output is pinned byte-identical.

    Byte-identical for one passer (two robots). A yield with two or more
    passers (2026-09-28) commands every one of them: the yield carries the
    passing order and a clearance per passer for M4's ordered hold-until-last
    release, each passer gets a linked wait with its `linked_position`, and
    the backstops scale with the passers' escort budget.
    """
    decision = result.decision
    if decision is None or not decision.congestion_detected:
        raise CommandGroundingError("cannot ground an empty or non-congestion decision")

    robot_ids = resolve_robot_order(decision)
    yield_grounded_from: str | None = None
    yield_regrounded_reason: str | None = None
    yield_refusal_reason: str | None = None
    if (
        decision.strategy == "yield"
        and yield_feasibility_mode != "off"
        and geometry is not None
        and robot_positions is not None
        and len(robot_ids) > 1
    ):
        robot_ids, yield_grounded_from, yield_regrounded_reason, yield_refusal_reason = (
            _apply_yield_feasibility(
                robot_ids, robot_positions, static_obstacles, geometry, yield_feasibility_mode
            )
        )
    command_id = f"{result.request_id}-{decision.strategy}"
    duration_sec = 8.0
    # Fallback distance the yielding robot reverses, used when the caller
    # supplies no positions (and by `reverse`, which has no park target). Sized
    # for a nose-to-nose standoff near x=0: robots stop at ~0.3-0.45 m
    # separation inside the aisle, and 0.8 m parked the yielder only ~0.7 m from
    # the gap's west exit — close enough that its inflated footprint forced the
    # passer into a tight S-curve right at the 0.55 m gap mouth, where DWB
    # stalled in "Failed to make progress" loops (observed 2026-07-03 run 4).
    # 1.3 m parks it ~1.2 m clear of that exit. The scene-aware path below
    # replaces this with |yielder_x - park_x|.
    backup_distance_m = 1.3
    # A straight backup alone re-deadlocks this scenario: the yielder stays on
    # the passer's line, and with min_distance_m=0.45 in the 1.2 m aisle the
    # passer cannot clear a centerline-parked yielder without tripping the
    # safety latch. The yielder therefore steps laterally off the centerline.
    # Expressed as a robot-frame lateral offset (positive = left), not an
    # absolute map pose: in head_on_deadlock.yaml both robots face each other
    # along x, so "step left" moves them to opposite sides of the aisle
    # regardless of which robot yields — no per-robot table or TF needed.
    # M4 executes it as a raw-cmd_vel turn-drive-turn (Nav2Adapter.sidestep);
    # the Nav2-planned pull-off it replaces stalled in DWB recovery loops
    # once motion BVH let the costmap see the other robot (2026-07-03).
    # 0.35 m keeps the yielder inside the wall clearance (aisle half-width
    # 0.6 m, inflated half-width ~0.19 m) while giving the passer 0.7 m of
    # centerline separation, above the 0.45 m safety threshold. This hand-sized
    # value is the fallback for callers without a `geometry`; with one, the same
    # number is derived by `scene_geometry.pull_off_lateral_m`.
    pull_off_lateral = 0.35
    # Upper-bound backstop for the yielder's hold, not the primary release:
    # M4 ends the hold the moment the passer's odometry shows it displaced
    # passer_clear_m since hold start (event-driven). A fixed 12 s hold
    # expired mid-traverse at low realtime factors and both robots re-entered
    # the aisle together (2026-07-03). 45 s covers a slow traverse with wide
    # margin; only reached if the passer never moves.
    yield_hold_sec = 45.0
    # The passer is DRIVEN through the gap by M4's raw-cmd_vel escort during
    # the hold (DWB could not transit the gap even with a widened free band —
    # ~0.01 m/s creep, H3 runs 4-7). The hold must only end once the passer is
    # fully PAST the parked yielder's x with margin, or the resuming yielder
    # crosses the still-approaching passer at <0.45 m separation and latches
    # both. These fallback values assume that same x=0 standoff (passer at
    # ~+0.25, yielder parked near x=-1.65, plus the 0.45 m safety radius);
    # the scene-aware path below replaces them with
    # |passer_coord - park_coord| + the passer clearance.
    passer_clear_m = 2.4
    passer_escort_distance_m = 2.4
    # Generous safety upper bound, not a motion-duration estimate (which was
    # wrong at any Isaac Sim realtime factor != 1). In the normal path the M4
    # command bus releases this wait the instant the linked yield reaches a
    # terminal status (event-driven); this constant is only reached if that
    # terminal-status signal is lost.
    passing_wait_sec = 120.0
    # Generous safety upper bound for the full yield cycle, used as
    # expected_resolution_time_sec. With M5 no longer expiring commands whose
    # robots are ACTIVE, this only bounds the PENDING/lost-dispatch case.
    yield_total_sec = 150.0

    if decision.strategy == "yield":
        park_coord: float | None = None
        park_axis: Literal["x", "y"] = "x"
        yield_refused = yield_refusal_reason is not None
        passer_order = _legacy_passer_order(robot_ids, decision, crossing_order)
        multi_passer = len(passer_order) > 1
        if multi_passer and not yield_refused:
            yield_refusal_reason = _first_passer_refusal(
                robot_ids[0], passer_order, robot_positions
            )
            yield_refused = yield_refusal_reason is not None
        # Fallback per-passer clearance, replaced below from each passer's own
        # position when the scene is known.
        crossing_clear = [passer_clear_m] * len(passer_order)
        if not yield_refused and len(robot_ids) > 1 and robot_positions is not None:
            yielder_position = robot_positions.get(robot_ids[0])
            passer_position = robot_positions.get(passer_order[0])
            if yielder_position is not None and passer_position is not None:
                corridor_center = 0.0
                park_offset = PARK_ABS_X_M
                passer_clearance = PASSER_CLEARANCE_M
                axis_index = 0
                # A yielder with a declared junction arm parks outward along it.
                arm_side: float | None = None
                yielder_geometry = geometry
                if geometry is not None:
                    yielder_geometry, arm_side = arm_geometry(geometry, robot_ids[0])
                    park_axis = yielder_geometry.corridor.axis
                    axis_index = 0 if park_axis == "x" else 1
                    corridor_center = geometry.corridor.center_m
                    park_offset = park_offset_m(geometry)
                    passer_clearance = passer_clearance_m(geometry)
                    pull_off_lateral = round(pull_off_lateral_m(geometry), 3)
                yielder_coord = yielder_position[axis_index]
                passer_coord = passer_position[axis_index]
                if yielder_geometry is not None:
                    # The far park point would sit on the opposite side, so the
                    # reverse would traverse the whole corridor — refuse instead.
                    yield_refused = _beyond_corridor_same_side(
                        yielder_position, passer_position, yielder_geometry
                    )
                    if yield_refused:
                        yield_refusal_reason = (
                            "yield refused: both robots outside the corridor on "
                            "the same side; a reverse would traverse it"
                        )
                if not yield_refused:
                    # Park on the yielder's own side of the corridor, away
                    # from the passer, so the two never swap sides mid-maneuver.
                    if arm_side is not None:
                        side = arm_side
                    else:
                        side = -1.0 if yielder_coord < passer_coord else 1.0
                    park_coord = round(corridor_center + side * park_offset, 3)

                    def _travel(passer_id: str, passer_xy: tuple[float, float]) -> float:
                        # Past the parked yielder along its axis, or out of the
                        # junction for a passer on a crossing arm.
                        if geometry is None:
                            return abs(passer_xy[axis_index] - park_coord)
                        parked_xy = (park_coord, park_coord)  # only the axis coord is read
                        return passer_travel_m(
                            passer_id, passer_xy, parked_xy, geometry, robot_ids[0]
                        )

                    already_parked = (yielder_coord - park_coord) * side >= 0.0
                    # A yielder already past the park point must not reverse
                    # further away from the aisle; MIN_BACKUP_M is just enough
                    # of a nudge for M4's reverse leg to report progress.
                    backup_distance_m = (
                        MIN_BACKUP_M
                        if already_parked
                        else round(
                            _clamp(abs(yielder_coord - park_coord), MIN_BACKUP_M, MAX_BACKUP_M),
                            3,
                        )
                    )
                    escort_m = round(
                        _clamp(
                            _travel(passer_order[0], passer_position) + passer_clearance,
                            MIN_ESCORT_M,
                            MAX_ESCORT_M,
                        ),
                        3,
                    )
                    passer_clear_m = escort_m
                    passer_escort_distance_m = escort_m
                    if multi_passer:
                        # Unclamped above: MAX_ESCORT_M sizes ONE passer
                        # against the 45 s hold; a queued passer can be
                        # farther, and a clamped clearance would end its
                        # crossing before it is past the parked yielder. The
                        # hold scales with the budget below instead.
                        for position, passer_id in enumerate(passer_order):
                            position_xy = robot_positions.get(passer_id)
                            if position_xy is None:
                                continue
                            crossing_clear[position] = round(
                                max(
                                    MIN_ESCORT_M,
                                    _travel(passer_id, position_xy) + passer_clearance,
                                ),
                                3,
                            )
        if yield_refused:
            actions = [
                {
                    "robot_id": robot_id,
                    "action": "temporary_wait",
                    "parameters": {
                        "duration_sec": duration_sec,
                        "requested_strategy": "yield",
                        "reason": yield_refusal_reason,
                    },
                }
                for robot_id in robot_ids
            ]
        else:
            yield_parameters: dict[str, Any] = {
                "backup_distance_m": backup_distance_m,
                "hold_sec": yield_hold_sec,
                "pull_off_lateral_m": pull_off_lateral,
                "reason": decision.root_cause,
            }
            if yield_grounded_from is not None:
                # Provenance for the decision trace: without it a reader of the
                # command cannot tell M2 named this yielder from M3 picking it.
                yield_parameters["yield_robot_grounded_from"] = yield_grounded_from
                yield_parameters["yield_regrounded_reason"] = yield_regrounded_reason
            if park_coord is not None:
                # Traceability only: M4 derives the backup from
                # backup_distance_m and reads parameters with .get, so the
                # extra keys are inert there. park_x_m predates the
                # axis-aware geometry and stays for the x-axis scenarios (and
                # tooling) that already read it.
                if park_axis == "x":
                    yield_parameters["park_x_m"] = park_coord
                if geometry is not None:
                    yield_parameters["park_axis"] = park_axis
                    yield_parameters["park_coord_m"] = park_coord
            if multi_passer:
                budget = _passer_budget(crossing_clear)
                yield_parameters["hold_sec"] = round(yield_hold_sec * budget, 1)
                passing_wait_sec = round(passing_wait_sec * budget, 1)
                yield_total_sec = round(yield_total_sec * budget, 1)
                passer_clear_m = crossing_clear[0]
                passer_escort_distance_m = crossing_clear[0]
            if len(robot_ids) > 1:
                yield_parameters["passer_robot_id"] = passer_order[0]
                yield_parameters["passer_clear_m"] = passer_clear_m
                yield_parameters["passer_escort_distance_m"] = passer_escort_distance_m
            if multi_passer:
                yield_parameters["crossing_order"] = list(passer_order)
                yield_parameters["crossing_clear_m"] = list(crossing_clear)
                yield_parameters["crossing_escort_m"] = list(crossing_clear)
            actions = [
                {
                    "robot_id": robot_ids[0],
                    "action": "yield",
                    "parameters": yield_parameters,
                },
            ]
            if multi_passer:
                # Every ordered passer is suppressed until M4's chain releases
                # it (linked_position = its place in crossing_order).
                actions.extend(
                    {
                        "robot_id": passer_id,
                        "action": "temporary_wait",
                        "parameters": {
                            "duration_sec": passing_wait_sec,
                            "linked_position": position,
                        },
                    }
                    for position, passer_id in enumerate(passer_order)
                )
            elif len(robot_ids) > 1:
                # Suppress the passing robot so M5 does not dispatch a
                # competing command while the aisle is still blocked. The M4
                # command bus releases this wait the moment the linked yield
                # reaches a terminal status (event-driven); passing_wait_sec
                # only bounds the case where that release signal is lost.
                actions.append(
                    {
                        "robot_id": robot_ids[1],
                        "action": "temporary_wait",
                        "parameters": {"duration_sec": passing_wait_sec},
                    }
                )
    elif decision.strategy == "reverse":
        reverse_refused = False
        if len(robot_ids) > 1 and robot_positions is not None and geometry is not None:
            first_position = robot_positions.get(robot_ids[0])
            second_position = robot_positions.get(robot_ids[1])
            if first_position is not None and second_position is not None:
                reverse_refused = _beyond_corridor_same_side(
                    first_position, second_position, geometry
                )
        if reverse_refused:
            actions = [
                {
                    "robot_id": robot_id,
                    "action": "temporary_wait",
                    "parameters": {
                        "duration_sec": duration_sec,
                        "requested_strategy": "reverse",
                        "reason": (
                            "reverse refused: both robots outside the corridor on "
                            "the same side; backing up would re-enter it"
                        ),
                    },
                }
                for robot_id in robot_ids
            ]
        else:
            actions = [
                {
                    "robot_id": robot_id,
                    "action": "reverse",
                    "parameters": {
                        "backup_distance_m": backup_distance_m,
                    },
                }
                for robot_id in robot_ids
            ]
    elif decision.strategy == "temporary_wait":
        actions = [
            {
                "robot_id": robot_id,
                "action": "temporary_wait",
                "parameters": {"duration_sec": duration_sec},
            }
            for robot_id in robot_ids
        ]
    elif decision.strategy == "reroute":
        # Asymmetric: first robot navigates, remaining robots wait long enough
        # for it to clear the contested zone. Sending all robots simultaneously
        # causes them to approach each other and re-collide immediately.
        clearance_wait_sec = 15.0
        actions = [
            {
                "robot_id": robot_ids[0],
                "action": "reroute",
                "parameters": {"waypoints": []},
            }
        ] + [
            {
                "robot_id": robot_id,
                "action": "temporary_wait",
                "parameters": {"duration_sec": clearance_wait_sec},
            }
            for robot_id in robot_ids[1:]
        ]
    elif decision.strategy in {"convoy", "priority_override"}:
        actions = [
            {
                "robot_id": robot_id,
                "action": "temporary_wait",
                "parameters": {
                    "duration_sec": duration_sec,
                    "requested_strategy": decision.strategy,
                },
            }
            for robot_id in robot_ids
        ]
    else:
        raise CommandGroundingError(f"unsupported strategy: {decision.strategy}")

    resolution_sec = (
        yield_total_sec if decision.strategy == "yield" and not yield_refused else duration_sec
    )
    return validate_coordination_command(
        {
            "command_id": command_id,
            "actions": actions,
            "expected_resolution_time_sec": resolution_sec,
            "fallback": "stop",
        }
    )


# Derived-mode degradation tags and the measurement-plan cause each one counts
# toward ("Measurement plan" in the rev-8 research design); None marks a
# convention or provenance marker that is not one of those causes. Emitted tags
# may carry a free-text suffix after the key; see `degradation_cause`.
DEGRADATION_TAGS: dict[str, str | None] = {
    # No snapshot, or a snapshot missing an involved robot: a spatial strategy
    # (yield, reverse) cannot be verified and runs as a non-spatial wait.
    "distances=unavailable": "no_snapshot",
    # Gate refusal, park point or backup/escort requirement outside its band.
    "yield=infeasible": "infeasible_geometry",
    # The legacy reverse template's corridor same-side refusal.
    "reverse=infeasible": "infeasible_geometry",
    # convoy / priority_override with no unique mapping onto the ordered
    # yield (`resolve_strategy_alias`): the legacy templates run a bounded
    # wait. Not a measurement-plan cause.
    "strategy=unsupported": None,
    # Provenance: a convoy / priority_override decision grounded as the
    # ordered yield it maps onto (`resolve_strategy_alias`); decisions with
    # these strategies do not pool across the alias commit.
    "strategy=aliased": None,
    # The backup is feasible but every retreat candidate failed the sweep.
    "retreat=no-valid-candidate": "infeasible_geometry",
    # A stage-2 letter naming no validated candidate.
    "retreat=default:invalid_label": "invalid_label",
    # No stage-2 answer reached grounding: the caller records why (timeout,
    # parse failure, a text-only condition, or Arm B, whose answer this IS).
    "retreat=default:no_choice": None,
    # A supplied crossing order that is not a permutation of the non-yielders.
    "order=default:non_permutation": "non_permutation_order",
    # Three or more robots with no explicit crossing order: involved-robots
    # order was used. Convention markers, not measurement-plan causes.
    "order=implicit": None,
    "roles=legacy-convention": None,
    # Provenance: the feasibility gate grounded a different yielder than M2
    # named (scored pre-gate, prereg amendments).
    "yield_robot=regrounded": None,
    "yield=no-passer": None,
    # Stage-1 parser tags for the prompt-v2 optional decision fields, recorded
    # on `ReasonerDiagnostics.decision_degradations`; merged here so one
    # `degradation_cause` covers the whole breakdown.
    **DECISION_DEGRADATION_TAGS,
}

def degradation_cause(tag: str) -> str | None:
    """Map one emitted degradation tag to its measurement-plan cause.

    Args:
        tag: An entry of a derived command's `degradations` list.

    Returns:
        The cause (`no_snapshot`, `infeasible_geometry`, `invalid_label`,
        `non_permutation_order`), or None for a convention/provenance marker.

    Raises:
        KeyError: If the tag matches no key of `DEGRADATION_TAGS`.
    """
    for key in sorted(DEGRADATION_TAGS, key=len, reverse=True):
        if tag == key or tag.startswith(f"{key}:"):
            return DEGRADATION_TAGS[key]
    raise KeyError(f"unknown degradation tag: {tag!r}")


_SPATIAL_STRATEGIES = frozenset({"yield", "reverse"})
# Matches the legacy grounder's non-spatial wait; kept separate so the legacy
# body stays verbatim.
_NONSPATIAL_WAIT_SEC = 8.0


class YieldRoles(BaseModel):
    """Who yields and in what order the rest cross, after the feasibility gate."""

    model_config = ConfigDict(frozen=True)

    # Involved robots with the grounded yielder first (the gate may reorder).
    robot_ids: list[str]
    crossing_order: list[str]
    grounded_from: str | None = None
    regrounded_reason: str | None = None
    # Set when no executable yield exists; the command is a wait fan-out.
    refusal_reason: str | None = None
    degradations: list[str]

    @property
    def yielder_id(self) -> str:
        """The robot that yields."""
        return self.robot_ids[0]


class RetreatSelection(BaseModel):
    """Stage-2 inputs: the derived backup and the ranked candidate set."""

    model_config = ConfigDict(frozen=True)

    yielder_id: str
    crossing_order: list[str]
    backup: Derivation
    # Best first: `candidates[0]` is the stage-2 default, the stage-2
    # fallback, and Arm B's stage-2 answer.
    candidates: list[RetreatCandidate]


def resolve_yield_roles(
    decision: CongestionDecision,
    snapshot: SnapshotFrame,
    *,
    geometry: SceneGeometry | None = None,
    static_obstacles: Sequence[StaticObstacleInput] = (),
    yield_feasibility_mode: YieldFeasibilityMode = "off",
    crossing_order: Sequence[str] | None = None,
) -> YieldRoles:
    """Resolve the yielder and crossing order of a yield decision.

    The same steps derived-mode grounding runs, exposed so a caller can learn
    the grounded yielder before rendering stage 2 for it: `yield_robot` (or
    the first involved robot, tagged `roles=legacy-convention`), then the
    yield feasibility gate on the snapshot positions, then the corridor
    same-side refusal, then the crossing order.

    Args:
        decision: A congestion decision with `strategy == "yield"`.
        snapshot: Scene frame supplying the robot positions.
        geometry: Declared scene geometry; the gate and the same-side refusal
            need it.
        static_obstacles: Fixed obstacles the gate scores retreat room against.
        yield_feasibility_mode: The gate mode (`"off"`, `"swap"`, `"refuse"`).
        crossing_order: Explicit passing order for the non-yielders, or None to
            use `decision.crossing_order` minus the grounded yielder (when the
            decision carries one).

    Returns:
        The roles, with `refusal_reason` set when no yield is executable.

    Raises:
        ValueError: If the decision's strategy is not `yield`.
    """
    if decision.strategy != "yield":
        raise ValueError(f"yield roles need a yield decision, got {decision.strategy!r}")
    degradations: list[str] = []
    if decision.yield_robot is None:
        degradations.append("roles=legacy-convention")
    robot_ids = resolve_robot_order(decision)
    if len(robot_ids) < 2:
        degradations.append("yield=no-passer")
        return YieldRoles(
            robot_ids=robot_ids,
            crossing_order=[],
            refusal_reason="yield refused: no other involved robot to pass",
            degradations=degradations,
        )

    positions = {state.robot_id: (state.x, state.y) for state in snapshot.robots}
    grounded_from: str | None = None
    regrounded_reason: str | None = None
    if yield_feasibility_mode != "off" and geometry is not None:
        robot_ids, grounded_from, regrounded_reason, refusal = _apply_yield_feasibility(
            robot_ids, positions, static_obstacles, geometry, yield_feasibility_mode
        )
        if refusal is not None:
            degradations.append(f"yield=infeasible:{refusal}")
            return YieldRoles(
                robot_ids=robot_ids,
                crossing_order=robot_ids[1:],
                refusal_reason=refusal,
                degradations=degradations,
            )
        if grounded_from is not None:
            degradations.append("yield_robot=regrounded")

    order = list(robot_ids[1:])
    if crossing_order is None and decision.crossing_order is not None:
        # The decision orders every involved robot; the grounded (post-gate)
        # yielder is dropped here so a gate swap cannot turn a valid model
        # order into a non-permutation.
        crossing_order = [rid for rid in decision.crossing_order if rid != robot_ids[0]]
    if crossing_order is not None:
        if sorted(crossing_order) == sorted(order) and len(set(crossing_order)) == len(order):
            order = list(crossing_order)
        else:
            degradations.append("order=default:non_permutation")
    elif len(order) > 1:
        degradations.append("order=implicit")

    if geometry is not None:
        yielder_position = positions.get(robot_ids[0])
        passer_position = positions.get(order[0])
        if (
            yielder_position is not None
            and passer_position is not None
            and _beyond_corridor_same_side(
                yielder_position, passer_position, arm_geometry(geometry, robot_ids[0])[0]
            )
        ):
            refusal = (
                "yield refused: both robots outside the corridor on "
                "the same side; a reverse would traverse it"
            )
            degradations.append(f"yield=infeasible:{refusal}")
            return YieldRoles(
                robot_ids=robot_ids,
                crossing_order=order,
                grounded_from=grounded_from,
                regrounded_reason=regrounded_reason,
                refusal_reason=refusal,
                degradations=degradations,
            )

    return YieldRoles(
        robot_ids=robot_ids,
        crossing_order=order,
        grounded_from=grounded_from,
        regrounded_reason=regrounded_reason,
        degradations=degradations,
    )


def prepare_retreat_selection(
    frame: SnapshotFrame,
    yielder_id: str,
    crossing_ids: Sequence[str],
    params: GroundingParams,
    *,
    geometry: SceneGeometry | None = None,
) -> RetreatSelection:
    """Derive the backup distance and the ranked retreat candidates.

    Deterministic in its inputs, so rendering stage 2 from this selection and
    grounding the answer later against the same frame see the same letters.

    Args:
        frame: Current scene snapshot.
        yielder_id: Robot that retreats (after the feasibility gate; see
            `resolve_yield_roles`).
        crossing_ids: Robots that will cross, in passing order.
        params: Geometry parameters.
        geometry: Declared scene geometry, or None.

    Returns:
        Selection with `candidates` ranked best-first; empty candidates when
        the backup is infeasible or nothing survives the sweep.
    """
    order = list(crossing_ids)
    backup = derive_backup_distance(frame, yielder_id, order, params, geometry=geometry)
    if not backup.feasible or backup.value_m is None:
        return RetreatSelection(
            yielder_id=yielder_id, crossing_order=order, backup=backup, candidates=[]
        )
    passer_id = order[0] if order else None
    candidates = generate_retreat_candidates(
        frame, yielder_id, backup.value_m, params, geometry=geometry, passer_id=passer_id
    )
    yielder = frame.find_robot(yielder_id)
    axes = retreat_axes(frame, yielder_id, passer_id, geometry)
    if yielder is None or axes is None:
        return RetreatSelection(
            yielder_id=yielder_id, crossing_order=order, backup=backup, candidates=[]
        )
    ranked = rank_candidates(
        candidates, math.atan2(axes.retreat[1], axes.retreat[0]), (yielder.x, yielder.y)
    )
    return RetreatSelection(
        yielder_id=yielder_id, crossing_order=order, backup=backup, candidates=ranked
    )


def _ground_derived(
    result: ReasonerResult,
    *,
    snapshot: SnapshotFrame | None,
    params: GroundingParams,
    retreat_choice: RetreatChoiceDecision | None,
    crossing_order: Sequence[str] | None,
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
) -> dict[str, Any]:
    """Rev-8 Appendix A grounding: verified-or-degrade, never blind constants.

    Non-yield strategies reuse the legacy templates on the snapshot positions
    (so the reverse same-side refusal still applies). A yield runs
    `resolve_yield_roles`, then `prepare_retreat_selection` for the grounded
    yielder, then applies the stage-2 choice. An infeasible backup or escort,
    or no surviving candidate, grounds a `reroute` of the yielder instead of a
    yield (rev-8 A.2/A.3); a gate or same-side refusal keeps the gate's wait
    fan-out. Every departure from the decision is tagged in `degradations`.
    """
    decision = result.decision
    if decision is None or not decision.congestion_detected:
        raise CommandGroundingError("cannot ground an empty or non-congestion decision")

    missing = (
        list(decision.involved_robots)
        if snapshot is None
        else [rid for rid in decision.involved_robots if snapshot.find_robot(rid) is None]
    )
    if decision.strategy in _SPATIAL_STRATEGIES and (snapshot is None or missing):
        reason = (
            "distances unavailable: no snapshot"
            if snapshot is None
            else f"distances unavailable: {', '.join(missing)} not in snapshot"
        )
        return _nonspatial_wait(result, decision, reason, ["distances=unavailable"])

    positions = (
        None
        if snapshot is None
        else {state.robot_id: (state.x, state.y) for state in snapshot.robots}
    )
    if decision.strategy != "yield" or snapshot is None:
        legacy = _ground_legacy(
            result, positions, geometry, static_obstacles, yield_feasibility_mode
        )
        return _with_degradations(legacy, _legacy_template_degradations(decision, legacy))

    roles = resolve_yield_roles(
        decision,
        snapshot,
        geometry=geometry,
        static_obstacles=static_obstacles,
        yield_feasibility_mode=yield_feasibility_mode,
        crossing_order=crossing_order,
    )
    degradations = list(roles.degradations)
    if roles.refusal_reason is not None:
        return _wait_fan_out(result, roles.robot_ids, roles.refusal_reason, degradations)

    selection = prepare_retreat_selection(
        snapshot, roles.yielder_id, roles.crossing_order, params, geometry=geometry
    )
    if not selection.backup.feasible:
        degradations.append(f"yield=infeasible:{selection.backup.reason}")
        return _reroute_yielder(result, decision, roles, degradations)
    if not selection.candidates:
        degradations.append("retreat=no-valid-candidate")
        return _reroute_yielder(result, decision, roles, degradations)

    chosen = selection.candidates[0]
    if retreat_choice is None:
        degradations.append("retreat=default:no_choice")
    else:
        match = next(
            (c for c in selection.candidates if c.label == retreat_choice.retreat_choice),
            None,
        )
        if match is None:
            degradations.append("retreat=default:invalid_label")
        else:
            chosen = match

    passer_id = roles.crossing_order[0]
    escort = derive_escort_distance(
        snapshot,
        passer_id,
        (chosen.x, chosen.y),
        params,
        geometry=geometry,
        yielder_id=roles.yielder_id,
    )
    if not escort.feasible:
        degradations.append(f"yield=infeasible:{escort.reason}")
        return _reroute_yielder(result, decision, roles, degradations)

    hold_sec = params.hold_backstop_sec
    wait_sec = params.wait_backstop_sec
    resolution_sec = params.resolution_backstop_sec
    crossing_clear: list[float] | None = None
    if len(roles.crossing_order) > 1:
        # One clearance per passer, each from its own position (M4 reuses the
        # first passer's for every later one otherwise), and backstops scaled
        # by the passers' budget, both as the legacy multi-passer yield does.
        crossing_clear = [escort.value_m]
        for robot_id in roles.crossing_order[1:]:
            queued = derive_queued_passer_clearance(
                snapshot,
                robot_id,
                (chosen.x, chosen.y),
                params,
                geometry=geometry,
                yielder_id=roles.yielder_id,
            )
            crossing_clear.append(queued.value_m if queued.value_m is not None else escort.value_m)
        budget = _passer_budget(crossing_clear)
        hold_sec = round(hold_sec * budget, 1)
        wait_sec = round(wait_sec * budget, 1)
        resolution_sec = round(resolution_sec * budget, 1)
    yield_parameters: dict[str, Any] = {
        "backup_distance_m": chosen.backup_m,
        "hold_sec": hold_sec,
        "pull_off_lateral_m": chosen.lateral_m,
        "retreat_choice": chosen.label,
        "retreat_x_m": round(chosen.x, 3),
        "retreat_y_m": round(chosen.y, 3),
        "reason": decision.root_cause,
        "passer_robot_id": passer_id,
        "passer_clear_m": escort.value_m,
        "passer_escort_distance_m": escort.value_m,
        "crossing_order": list(roles.crossing_order),
    }
    if crossing_clear is not None:
        yield_parameters["crossing_clear_m"] = list(crossing_clear)
        yield_parameters["crossing_escort_m"] = list(crossing_clear)
    if roles.grounded_from is not None:
        yield_parameters["yield_robot_grounded_from"] = roles.grounded_from
        yield_parameters["yield_regrounded_reason"] = roles.regrounded_reason
    actions: list[dict[str, Any]] = [
        {"robot_id": roles.yielder_id, "action": "yield", "parameters": yield_parameters}
    ]
    for position, robot_id in enumerate(roles.crossing_order):
        actions.append(
            {
                "robot_id": robot_id,
                "action": "temporary_wait",
                "parameters": {
                    "duration_sec": wait_sec,
                    "linked_position": position,
                },
            }
        )
    return validate_coordination_command(
        {
            "command_id": f"{result.request_id}-yield",
            "actions": actions,
            "expected_resolution_time_sec": resolution_sec,
            "fallback": "stop",
            "degradations": degradations,
        }
    )


def _legacy_template_degradations(
    decision: CongestionDecision, command: dict[str, Any]
) -> list[str]:
    # The legacy templates mark every wait they substitute for the decided
    # strategy with `requested_strategy`; surface those as tags too.
    substituted = [
        action["parameters"]
        for action in command["actions"]
        if action["action"] == "temporary_wait"
        and action.get("parameters", {}).get("requested_strategy") == decision.strategy
    ]
    if not substituted:
        return []
    if decision.strategy == "reverse":
        return [f"reverse=infeasible:{substituted[0]['reason']}"]
    return [f"strategy=unsupported:{decision.strategy}"]


def _with_degradations(command: dict[str, Any], degradations: list[str]) -> dict[str, Any]:
    return validate_coordination_command({**command, "degradations": degradations})


def _wait_fan_out(
    result: ReasonerResult, robot_ids: list[str], reason: str, degradations: list[str]
) -> dict[str, Any]:
    # Same shape as the legacy refused-yield fan-out.
    decision = result.decision
    assert decision is not None
    return _with_degradations(
        {
            "command_id": f"{result.request_id}-{decision.strategy}",
            "actions": [
                {
                    "robot_id": robot_id,
                    "action": "temporary_wait",
                    "parameters": {
                        "duration_sec": _NONSPATIAL_WAIT_SEC,
                        "requested_strategy": decision.strategy,
                        "reason": reason,
                    },
                }
                for robot_id in robot_ids
            ],
            "expected_resolution_time_sec": _NONSPATIAL_WAIT_SEC,
            "fallback": "stop",
        },
        degradations,
    )


def _nonspatial_wait(
    result: ReasonerResult,
    decision: CongestionDecision,
    reason: str,
    degradations: list[str],
) -> dict[str, Any]:
    robot_ids = resolve_robot_order(decision)
    return _wait_fan_out(result, robot_ids, reason, degradations)


def _reroute_yielder(
    result: ReasonerResult,
    decision: CongestionDecision,
    roles: YieldRoles,
    degradations: list[str],
) -> dict[str, Any]:
    # The yield is not executable with this geometry (rev-8 A.2/A.3): the robot
    # chosen to give way reroutes instead, the others wait, and M5 reanalyzes.
    reroute = decision.model_copy(
        update={
            "strategy": "reroute",
            "involved_robots": [roles.yielder_id, *roles.crossing_order],
        }
    )
    legacy = _ground_legacy(result.model_copy(update={"decision": reroute}), None, None, (), "off")
    return _with_degradations(legacy, degradations)

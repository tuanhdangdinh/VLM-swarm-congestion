import math
from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any, Literal, NamedTuple

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.maneuver_geometry import (
    Derivation,
    GroundingParams,
    derive_backup_distance,
    derive_escort_distance,
    derive_queued_passer_clearance,
    rank_recede_candidates,
    recede_axis_offset_m,
    recede_distance_m,
    recede_orders_equivalent,
    recede_pocket_offset_m,
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
    PlanLegAction,
    ProposedPlanLeg,
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


def _clamp_reverse_distance_to_tracked_band(
    robot_id: str,
    distance_m: float,
    position: tuple[float, float] | None,
    geometry: SceneGeometry | None,
) -> float:
    """Clamp a plain `reverse` leg's backup distance to stay inside `tracked_extent_m`.

    Freeze-blocking finding 4 (step-7a fix): a plain `reverse` had no
    awareness of where M1's verified tracking extent ends, reliably driving
    a robot already well outward on its own arm (e.g. mid-transit after a
    post-composite release) past it. Scoped to robots with a DECLARED arm
    only (`geometry.arms`), the same precondition `junction_recede_offset_m`
    uses -- a plain corridor scene with no arms has no axis convention to
    clamp against and is left untouched.

    Args:
        robot_id: The reversing robot.
        distance_m: The otherwise-computed backup distance.
        position: The robot's current `(x, y)`, or None if unknown.
        geometry: Declared scene geometry, or None.

    Returns:
        `distance_m` unchanged when `geometry`, `geometry.tracked_extent_m`,
        the robot's declared arm, or `position` is absent; otherwise the
        largest distance (never negative) that keeps the robot's post-backup
        progress along its own arm (`maneuver_geometry.recede_axis_offset_m`)
        at or inside `tracked_extent_m`.
    """
    if geometry is None or geometry.tracked_extent_m is None or position is None:
        return distance_m
    arm = (geometry.arms or {}).get(robot_id)
    if arm is None:
        return distance_m
    current_progress = recede_axis_offset_m(position, arm, geometry)
    headroom = geometry.tracked_extent_m - current_progress
    return round(max(0.0, min(distance_m, headroom)), 3)


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


def _reroute_waypoints(geometry: SceneGeometry | None) -> list[dict[str, float]]:
    # The scene's declared detour (loop map) as M4's `waypoints` list; empty
    # (M4 re-sends the goal) for every scene that declares none, so the
    # command is byte-identical to the pre-loop-map grounder there.
    if geometry is None or geometry.reroute_waypoints is None:
        return []
    return [{"x": float(x), "y": float(y)} for x, y in geometry.reroute_waypoints]


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
    # Set only by a tracked-band clamp that actually shortened a reverse;
    # empty keeps every other legacy command byte-identical (no key).
    clamp_tags: list[str] = []
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
            actions = []
            for robot_id in robot_ids:
                clamped_m = _clamp_reverse_distance_to_tracked_band(
                    robot_id,
                    backup_distance_m,
                    robot_positions.get(robot_id) if robot_positions else None,
                    geometry,
                )
                if clamped_m != backup_distance_m:
                    # Forcing-audit A5a: the clamp rewrites the leg after the
                    # decision; tag it so the artifact shows the change.
                    clamp_tags.append(
                        f"reverse=clamped_tracked_band:{robot_id}:"
                        f"{backup_distance_m:g}->{clamped_m:g}"
                    )
                actions.append(
                    {
                        "robot_id": robot_id,
                        "action": "reverse",
                        "parameters": {"backup_distance_m": clamped_m},
                    }
                )
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
                "parameters": {"waypoints": _reroute_waypoints(geometry)},
            }
        ] + [
            {
                "robot_id": robot_id,
                "action": "temporary_wait",
                "parameters": {"duration_sec": clearance_wait_sec},
            }
            for robot_id in robot_ids[1:]
        ]
    elif decision.strategy in {"convoy", "priority_override", "junction_clear"}:
        # `junction_clear` (prereg-v2 build-order step 5): LEGACY mode has no
        # feasibility bands to stage a recede-then-yield sequence against, so
        # it gets the same non-spatial wait fan-out every strategy this
        # bridge has no specific case for already gets -- never the
        # `CommandGroundingError` an actually-unsupported strategy raises.
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
    command: dict[str, Any] = {
        "command_id": command_id,
        "actions": actions,
        "expected_resolution_time_sec": resolution_sec,
        "fallback": "stop",
    }
    if clamp_tags:
        command["degradations"] = clamp_tags
    return validate_coordination_command(command)


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
    # Forcing-audit A5a: the tracked-band clamp (`_clamp_reverse_distance_to_
    # tracked_band`) shortened a reverse leg below the computed backup;
    # suffix `:<robot_id>:<from>-><to>` in metres. Provenance, not a cause:
    # the clamp is M3 safety machinery, never a model output.
    "reverse=clamped_tracked_band": None,
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
    # Forcing-audit A4: the decision DID give a `crossing_order`, but a
    # `junction_clear` yield-axis / plain-yield-fallback rebuild
    # (`_as_yield_decision`) discarded it, so the implicit order ran. Kept
    # apart from `order=implicit` ("none given") so repaired-order metrics
    # do not count a discarded model order as an absent one.
    "order=discarded_yield_axis": None,
    # J1 same-axis filter (v2-branch divergence from the v1-frozen Arm B,
    # design study 2026-09-29): a robot held opposite a same-axis partner
    # also in the order was dropped from it instead of leading it (see
    # `_junction_same_axis_order`). Provenance, not a measurement-plan cause
    # -- the order was never a model output.
    "order=junction_same_axis": None,
    "roles=legacy-convention": None,
    # Provenance: the feasibility gate grounded a different yielder than M2
    # named (scored pre-gate, prereg amendments).
    "yield_robot=regrounded": None,
    "yield=no-passer": None,
    # `junction_clear` phase markers (`ground_junction_clear_phases`):
    # provenance of which phase a dispatched command represents, not a
    # measurement-plan cause -- the phasing is M3/M5 machinery, never a
    # model output.
    "junction_clear=recede": None,
    "junction_clear=cross": None,
    # The geometry declares no recede precondition (no cross-axis candidate,
    # or no `junction_recede_offset_m` target): degraded to plain `yield`
    # ("v1 behavior... single yield or no-op", M5 spec section).
    "junction_clear=fallback:no_candidates": None,
    # Loudness guard (step-6 coordinator ruling): `junction_clear` grounded
    # without BOTH `junction_recede_offset_m` and `junction_backup_
    # clearance_m` (J2) declared -- emitted on the `no_candidates` fallback
    # when a field is the reason (never when a declared-but-empty chi
    # ranking is), and on every phase/fallback command when the composite
    # proceeds with J2 still undeclared, grounding the shipped 1.7 m
    # head-on clearance instead of the study's junction-scoped number (the
    # unsolved-row silent failure build-order step 5 found). Suffix names
    # the missing field(s): `:missing=junction_recede_offset_m`,
    # `:missing=junction_backup_clearance_m`, or both comma-joined.
    # Provenance only: the tag never changes which numbers are grounded.
    "junction_geometry=shipped_unsolved": None,
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


def _junction_geometry_missing_fields(geometry: SceneGeometry | None) -> list[str]:
    """Which of the two step-6 goal-table fields `geometry` fails to declare.

    `geometry is None` counts as both missing: with no declared geometry at
    all there is no `junction_recede_offset_m` pocket and no
    `junction_backup_clearance_m` (J2) override to miss separately.

    Args:
        geometry: Declared scene geometry, or None.

    Returns:
        `[]` when both fields are declared; otherwise the missing field
        name(s), `junction_recede_offset_m` before `junction_backup_clearance_m`.
    """
    if geometry is None:
        return ["junction_recede_offset_m", "junction_backup_clearance_m"]
    missing = []
    if geometry.junction_recede_offset_m is None:
        missing.append("junction_recede_offset_m")
    if geometry.junction_backup_clearance_m is None:
        missing.append("junction_backup_clearance_m")
    return missing


def _shipped_unsolved_tag(missing_fields: Sequence[str]) -> str:
    """The loudness guard's degradation tag, naming the missing field(s).

    Args:
        missing_fields: Non-empty output of `_junction_geometry_missing_fields`.

    Returns:
        `junction_geometry=shipped_unsolved:missing=<field,field,...>`.
    """
    return f"junction_geometry=shipped_unsolved:missing={','.join(missing_fields)}"


_SPATIAL_STRATEGIES = frozenset({"yield", "reverse", "junction_clear"})
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


def _junction_same_axis_order(
    order: list[str], yielder_id: str, geometry: SceneGeometry
) -> list[str]:
    """Drop a crossing robot held opposite a same-axis partner in the order.

    J1 (v2-branch divergence from the v1-frozen Arm B; design study
    2026-09-29, "Arm B classification against where the waiting robots are
    held"): two robots held on the same declared arm axis but opposite sides
    cannot both be given a `passer_travel_m` exit without one running
    through the other -- a crossing-axis exit leaves via the far mouth of
    the robot's own corridor, straight past whoever is parked at that
    mouth's opposite end (the study's IB10 escort-through-partner defect,
    0.000 m). Filtering is scoped to exactly that pattern, not to "any robot
    off the yielder's axis": a robot already on the yielder's own axis is
    never dropped, and a cross-axis robot keeps its place unless its own
    same-axis, opposite-side partner is also in the order. That is why a
    legitimate cross-axis passer (e.g. the `bottleneck_merge` T-junction,
    whose yielder's arm is perpendicular to its only passer, with no
    opposite-side partner on that passer's axis) is untouched, while the
    four-way's held N-S pair -- mutually opposite on their own axis, both
    off the yielder's axis -- drop out together.

    Args:
        order: Crossing order with the yielder already excluded.
        yielder_id: The robot that yields.
        geometry: Declared scene geometry.

    Returns:
        `order` unchanged when the yielder has no declared arm, or no robot
        in it has an opposite-side same-axis partner also present.
    """
    arms = geometry.arms or {}
    yielder_arm = arms.get(yielder_id)
    if yielder_arm is None:
        return order

    def has_opposite_partner(robot_id: str) -> bool:
        arm = arms.get(robot_id)
        if arm is None:
            return False
        return any(
            other_id != robot_id
            and arms.get(other_id) is not None
            and arms[other_id].axis == arm.axis
            and arms[other_id].side == -arm.side
            for other_id in order
        )

    return [
        robot_id
        for robot_id in order
        if arms.get(robot_id) is None
        or arms[robot_id].axis == yielder_arm.axis
        or not has_opposite_partner(robot_id)
    ]


def _junction_recede_candidates(
    decision: CongestionDecision, geometry: SceneGeometry
) -> list[str]:
    """The `junction_clear` recede set: involved robots off the yield axis.

    Interpretation (prereg-v2 build-order step 5; not settled by name in
    either spec): `geometry.corridor.axis` is the scene's declared primary
    yield axis (the single corridor an ordinary `yield` decision already
    grounds along, per `test_shipped_single_corridor_grounds_no_north_south_
    yield`); a recede candidate is an involved robot with a declared arm on
    the OTHER axis. This makes the axis a structural precondition, not
    something chi chooses between: chi (`maneuver_geometry.
    rank_recede_candidates`) only orders robots WITHIN this set (never a
    yield-axis robot against it), so a symmetric D_SPACE across axes can
    never make chi pick an E-W robot over the N-S cross pair by itself.

    Args:
        decision: A `junction_clear` decision.
        geometry: Declared scene geometry.

    Returns:
        Involved robots whose declared arm axis differs from
        `geometry.corridor.axis`, in `decision.involved_robots` order.
        Empty when `geometry.arms` is unset or no involved robot has a
        cross-axis arm.
    """
    arms = geometry.arms or {}
    corridor_axis = geometry.corridor.axis
    return [
        robot_id
        for robot_id in decision.involved_robots
        if (arm := arms.get(robot_id)) is not None and arm.axis != corridor_axis
    ]


def _junction_yield_axis_robots(
    decision: CongestionDecision, geometry: SceneGeometry
) -> list[str]:
    """The `junction_clear` yield set: involved robots on the yield axis.

    Complements `_junction_recede_candidates`: an involved robot with no
    declared arm, or whose declared arm matches `geometry.corridor.axis`, is
    on the yield axis and runs the ordinary single-yield resolution once the
    recede set has cleared.

    Args:
        decision: A `junction_clear` decision.
        geometry: Declared scene geometry.

    Returns:
        Involved robots not returned by `_junction_recede_candidates`, in
        `decision.involved_robots` order.
    """
    recede = set(_junction_recede_candidates(decision, geometry))
    return [robot_id for robot_id in decision.involved_robots if robot_id not in recede]


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
    yield feasibility gate on the snapshot positions, then the crossing
    order, then the junction same-axis filter (v2-branch divergence from the
    v1-frozen Arm B; a no-op when `geometry.arms` is unset), then the
    corridor same-side refusal.

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
        # J1, v2-branch divergence from the v1-frozen Arm B (design study
        # 2026-09-29, "Arm B classification against where the waiting robots
        # are held"; prereg-v2-design.md Prerequisites item 2). Scoped to one
        # pattern, not "cross-axis from the yielder": see
        # `_junction_same_axis_order`.
        filtered_order = _junction_same_axis_order(order, robot_ids[0], geometry)
        if filtered_order != order:
            degradations.append("order=junction_same_axis")
            order = filtered_order

    if not order:
        degradations.append("yield=no-passer")
        return YieldRoles(
            robot_ids=robot_ids,
            crossing_order=[],
            grounded_from=grounded_from,
            regrounded_reason=regrounded_reason,
            refusal_reason=(
                "yield refused: every involved robot is paired against a "
                "same-axis partner holding the opposite side"
            ),
            degradations=degradations,
        )

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
    if decision.strategy == "junction_clear" and snapshot is not None:
        # Scope (prereg-v2 build-order step 5): `junction_clear`'s composite
        # grounding is implemented for DERIVED mode only -- the shipped,
        # live `config/rag.yaml` mode and the only one IB10 is tested under.
        # LEGACY mode has no feasibility bands to stage a recede-then-yield
        # sequence against, so it is deliberately left on the generic
        # catch-all below (the same degradation every strategy this mode
        # has no specific case for already gets), consistent with how
        # legacy mode is "the pre-switch grounder, frozen" territory.
        candidates = (
            _junction_recede_candidates(decision, geometry) if geometry is not None else []
        )
        ranked = (
            rank_recede_candidates(snapshot, candidates, geometry, params)
            if geometry is not None and geometry.junction_recede_offset_m is not None
            else []
        )
        if not ranked:
            # No recede precondition (no declared pocket, or no cross-axis
            # candidate survives chi): "v1 behavior ... single yield or
            # no-op" (M5 spec section) -- plain `yield` over every involved
            # robot; J1 (`_junction_same_axis_order`) already drops a
            # cross-axis robot to no-op there, with no recede at all.
            fallback_result = result.model_copy(
                update={"decision": _as_yield_decision(decision)}
            )
            command = _ground_derived(
                fallback_result,
                snapshot=snapshot,
                params=params,
                retreat_choice=retreat_choice,
                crossing_order=crossing_order,
                geometry=geometry,
                static_obstacles=static_obstacles,
                yield_feasibility_mode=yield_feasibility_mode,
            )
            if crossing_order is None:
                # Forcing-audit A4: an explicit caller override is the
                # operative order; only the decision's own order is discarded.
                command = _tag_discarded_order(command, decision)
            # Forcing-audit A7: MERGE onto the plain yield's own tags (e.g.
            # `retreat=default:*`, `yield=infeasible:*`,
            # `order=junction_same_axis`), never replace them -- this is the
            # path the fallback_exhausted analysis scores.
            tags = [*command.get("degradations", []), "junction_clear=fallback:no_candidates"]
            # Loudness guard (step-6 coordinator ruling): `no_candidates` also
            # fires for an unrelated, legitimate reason (no cross-axis arms
            # under a fully-declared geometry), so it is not on its own a
            # signal that a goal-table field is missing. This tag is added
            # ONLY when a field actually is, independent of why `ranked` came
            # back empty, so its absence is a clean deploy check.
            missing = _junction_geometry_missing_fields(geometry)
            if missing:
                tags.append(_shipped_unsolved_tag(missing))
            return _with_degradations(command, tags)
        plan = ground_junction_clear_phases(
            result,
            snapshot=snapshot,
            params=params,
            geometry=geometry,  # geometry is not None: ranked is non-empty only then
            static_obstacles=static_obstacles,
            yield_feasibility_mode=yield_feasibility_mode,
            retreat_choice=retreat_choice,
        )
        # The standalone, single-command contract every other strategy keeps
        # (`ground_reasoner_result` always returns one dict): the NEXT
        # unresolved step. Flag-off (`plan_tracker is None`, no phase queue
        # to advance it) dispatches just this one phase and stops there --
        # safe (the exemption pairing is already correct for it) but not
        # fully orchestrated; flag-on, M5's phase queue
        # (`swarm_orchestrator.junction_phase_queue`) calls
        # `ground_junction_clear_phases` itself for the REST of `plan.phases`
        # and `plan.fallback_command`, seeded from this SAME decision cycle.
        return plan.phases[0].command
    if decision.strategy != "yield" or snapshot is None:
        legacy = _ground_legacy(
            result, positions, geometry, static_obstacles, yield_feasibility_mode
        )
        return _with_degradations(
            legacy,
            [*legacy.get("degradations", []), *_legacy_template_degradations(decision, legacy)],
        )

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


class JunctionClearPhase(BaseModel):
    """One dispatched command of a `junction_clear` resolution's sequence."""

    model_config = ConfigDict(frozen=True)

    label: Literal["recede", "cross", "release"]
    # The receding robot, for a "recede" phase; None for the final "cross"
    # (yield-axis) phase and for the trailing "release" phase (freeze-
    # blocking finding 2, step-7a fix: no new maneuver is commanded here,
    # only a staggered hold).
    robot_id: str | None
    command: dict[str, Any]
    # Every robot `command` addresses only to hold it (`temporary_wait`),
    # not to execute a leg of the ACCEPTED plan in this phase. M5 must
    # never route one of these robots' status from THIS command onto the
    # tracked plan's leg for it: that leg's real action (e.g. robot_1's
    # eventual `yield`) is still `pending`, dispatched by a LATER phase --
    # routing this phase's hold-`COMPLETED` onto it would mark it `done`
    # before it ever ran. Disjoint from the command's acting robot(s).
    held_robot_ids: tuple[str, ...] = ()


class JunctionClearPhasePlan(BaseModel):
    """The full ordered phase sequence M3 grounds for one `junction_clear` decision.

    Computed entirely from the ONE snapshot the triggering decision was made
    on: the scene does not change while an earlier phase's command is in
    flight (no other M2 analysis runs mid-sequence, and the robots not yet
    dispatched in the current phase are held by it, `temporary_wait`), so
    every later phase's geometry is valid when computed up front, not only
    when M5 is about to dispatch it. M5's phase queue
    (`swarm_orchestrator.junction_phase_queue`) owns dispatching `phases` in
    order and substituting `fallback_command` for the remaining robots on a
    FAILED recede, never re-deriving this plan or re-invoking M2.

    Freeze-blocking finding 2 (2026-10-02 IB10 composite smoke, episode 2):
    with 2+ recede candidates, `phases` carries one trailing `"release"`
    phase after `"cross"`. Without it, every recede candidate's hold
    (`held_robot_ids` in the cross phase) lapses together the instant
    `cross` resolves, so M4's per-robot base-mission resume (`BaseMissionDriver.
    on_status`, keyed on that SHARED command's terminal status) releases
    them all back toward their own base-mission goals at once -- a fresh,
    unordered encounter on the SAME N-S line the composite just cleared
    (both recede pockets sit on one axis coordinate, so there is no lateral
    room to pass). The `"release"` phase holds every recede candidate but
    the chi-cheapest one (`ranked[0]`, already the first to recede) PLUS the
    grounded yielder (`"the yielder re-enters last"`, (a) Sequencing) via a
    plain `yield` action whose `passer_robot_id` is `ranked[0]` -- reusing
    M4's existing odometry-gated `CrossingChain` (`swarm_execution.
    crossing_chain`) UNCHANGED, never a new M4 mechanism or a fixed timer
    (which would reproduce the exact bug: two identical fixed waits release
    together regardless of real clearance). `ranked[0]` itself is addressed
    by NO command in this phase, so nothing re-suppresses it: it resumes
    immediately, exactly like any other robot whose last owning command
    resolved with none to follow. Scoped to exactly ONE release stage (lead
    goes first, every other held robot follows together once the lead
    clears) -- correct for IB10's 2-candidate case; a 3+-candidate scene
    would need a full N-way chain, not built here (out of this task's
    scope).
    """

    model_config = ConfigDict(frozen=True)

    phases: list[JunctionClearPhase] = Field(min_length=1)
    # Plain `yield` over every involved robot (`_as_yield_decision` with no
    # restriction) -- "v1 behavior ... single yield or no-op" exactly, per
    # the M5 spec section. Dispatched by M5 in place of whichever phase
    # resolves FAILED, for every robot that phase (and every one after it)
    # would have addressed. Also holds every recede candidate that may
    # already have receded by the time of a later failure
    # (`fallback_held_robot_ids`): J1 drops them from the plain yield's own
    # order, but a ALREADY-receded one's base mission must still not be
    # free to resume through the junction while the fallback yield runs.
    fallback_command: dict[str, Any]
    fallback_held_robot_ids: tuple[str, ...] = ()


def ground_junction_clear_phases(
    result: ReasonerResult,
    *,
    snapshot: SnapshotFrame,
    params: GroundingParams,
    geometry: SceneGeometry,
    static_obstacles: Sequence[StaticObstacleInput] = (),
    yield_feasibility_mode: YieldFeasibilityMode = "off",
    retreat_choice: RetreatChoiceDecision | None = None,
) -> JunctionClearPhasePlan:
    """Ground a `junction_clear` decision's full recede-then-yield dispatch sequence.

    One command per phase, each independently schema-valid and
    dispatchable: a `reverse` command per recede candidate, in chi order
    (`maneuver_geometry.rank_recede_candidates` -- "Single yielder by
    default; a two-robot recede ... is a staggered sequential fallback,
    never simultaneous" is this same ascending order, one phase per
    candidate, never two in the same command), then the ordinary single
    `yield` command for the yield-axis robots (`_ground_derived`'s own yield
    branch, reused verbatim via `_as_yield_decision`, never a second
    implementation).

    Every phase's command addresses EVERY involved robot: the active one
    with its real maneuver, every other one with `temporary_wait`. This is
    load-bearing for safety, not cosmetic: `safety.admitted_partners` exempts
    a `reverse` only against the OTHER members of its OWN command (the (a)
    Safety section's citation), and the recede legs start 0.24-0.34 m from
    the yield-axis pair -- a single-robot command would latch immediately,
    before the recede could even begin. The held robots also stay
    `temporary_wait`-ed through the FINAL phase: `reverse` never holds (M4's
    command bus always resolves it with `hold_sec=0.0`), so without this a
    receded robot's base mission could resume toward its original goal, back
    through the junction, while the yield-axis pair is still crossing.

    Args:
        result: Validated M2 reasoner output, strategy `junction_clear`.
        snapshot: The scene frame every phase is grounded from (see
            `JunctionClearPhasePlan`'s docstring).
        params: Grounding parameters: the chi weights and recede hold
            (`junction_recede_cost_*`, `junction_recede_hold_sec`), and the
            ordinary yield bands/clearances the final phase uses.
        geometry: Declared scene geometry; must declare `arms` and
            `junction_recede_offset_m` for a non-degenerate plan -- the
            caller (`_ground_derived`'s `junction_clear` branch) is
            responsible for falling back to plain `yield` first when it does
            not, or when no candidate survives chi ranking; this function
            does not degrade on its own.
        static_obstacles: Fixed obstacles of the running scenario.
        yield_feasibility_mode: The yield feasibility gate mode for the final
            (yield-axis) phase.
        retreat_choice: Derived-mode stage-2 answer for the final phase, if
            any; never meaningful for a recede phase (no stage 2 exists for
            a straight-line recede to a declared pocket).

    Returns:
        The full phase sequence plus the plain-`yield` fallback command.
        Every returned command's `degradations` carries
        `junction_geometry=shipped_unsolved:missing=junction_backup_clearance_m`
        when `geometry` declares `junction_recede_offset_m` (required to
        reach this function at all) without also declaring
        `junction_backup_clearance_m` (J2): the cross phase and fallback
        still ground, but through the shipped 1.7 m head-on clearance
        rather than the study's junction-scoped number
        (loudness guard, step-6 coordinator ruling; never changes which
        numbers are grounded, only tags the command).

    Raises:
        CommandGroundingError: If the decision is empty, not
            `congestion_detected`, not `junction_clear`, or no recede
            candidate survives chi ranking under `geometry` (the caller's
            job to check first).
    """
    decision = result.decision
    if decision is None or not decision.congestion_detected:
        raise CommandGroundingError("cannot ground an empty or non-congestion decision")
    if decision.strategy != "junction_clear":
        raise CommandGroundingError(
            "ground_junction_clear_phases needs a junction_clear decision, got "
            f"{decision.strategy!r}"
        )
    candidates = _junction_recede_candidates(decision, geometry)
    ranked = rank_recede_candidates(snapshot, candidates, geometry, params)
    if not ranked:
        raise CommandGroundingError(
            "junction_clear: no recede candidate survives chi ranking under this geometry"
        )
    # Loudness guard (step-6 coordinator ruling): a pocket is declared
    # (`junction_recede_offset_m`, or `ranked` would be empty above) but J2's
    # junction-scoped clearance may not be -- the cross phase below then
    # grounds through `_ground_derived`'s ordinary yield branch, which falls
    # back to the shipped 1.7 m head-on clearance with no error (bug 4,
    # `docs/implementation_notes.md` 2026-10-02 step-5 post-landing entry).
    # Never behavior-changing: every phase still grounds exactly the numbers
    # it would have without this guard, only the tag is added. `missing` is
    # always `[]` or exactly `["junction_backup_clearance_m"]` here --
    # `junction_recede_offset_m` is guaranteed present, or `ranked` above
    # would already be empty.
    missing = _junction_geometry_missing_fields(geometry)
    missing_j2 = bool(missing)

    fallback_result = result.model_copy(update={"decision": _as_yield_decision(decision)})
    fallback_command = _tag_discarded_order(
        _ground_derived(
            fallback_result,
            snapshot=snapshot,
            params=params,
            retreat_choice=None,
            crossing_order=None,
            geometry=geometry,
            static_obstacles=static_obstacles,
            yield_feasibility_mode=yield_feasibility_mode,
        ),
        decision,
    )
    # Hold every recede candidate the fallback's own plain-yield grounding
    # does not already address (J1 drops them from its order on purpose):
    # one of them may already have receded by the time of a later failure,
    # and its base mission must not be free to resume through the junction
    # while this fallback yield runs.
    fallback_addressed = {action["robot_id"] for action in fallback_command["actions"]}
    fallback_extra_holds = [
        {
            "robot_id": robot_id,
            "action": "temporary_wait",
            "parameters": {"duration_sec": params.wait_backstop_sec},
        }
        for robot_id in ranked
        if robot_id not in fallback_addressed
    ]
    if fallback_extra_holds:
        fallback_command = validate_coordination_command(
            {**fallback_command, "actions": [*fallback_command["actions"], *fallback_extra_holds]}
        )
    if missing_j2:
        fallback_command = _with_degradations(
            fallback_command,
            [*fallback_command.get("degradations", []), _shipped_unsolved_tag(missing)],
        )

    phases: list[JunctionClearPhase] = []
    for rank, robot_id in enumerate(ranked):
        # Step-7b ruling (iv): the pocket is assigned by chi rank AFTER
        # ranking (chi itself measures the unstaggered offset), so a declared
        # stagger moves only the non-lead candidates' pockets inward.
        distance = recede_distance_m(
            snapshot, robot_id, geometry, offset_m=recede_pocket_offset_m(geometry, rank)
        )
        assert distance is not None  # guaranteed by `rank_recede_candidates`
        actions: list[dict[str, Any]] = [
            {
                "robot_id": robot_id,
                "action": "reverse",
                "parameters": {"backup_distance_m": distance, "reason": decision.root_cause},
            }
        ]
        held_robot_ids: list[str] = []
        for other_id in decision.involved_robots:
            if other_id == robot_id:
                continue
            actions.append(
                {
                    "robot_id": other_id,
                    "action": "temporary_wait",
                    "parameters": {"duration_sec": params.junction_recede_hold_sec},
                }
            )
            held_robot_ids.append(other_id)
        recede_degradations = ["junction_clear=recede"]
        if missing_j2:
            recede_degradations.append(_shipped_unsolved_tag(missing))
        command = validate_coordination_command(
            {
                "command_id": f"{result.request_id}-junction-recede-{robot_id}",
                "actions": actions,
                "expected_resolution_time_sec": params.junction_recede_hold_sec,
                "fallback": "stop",
                "degradations": recede_degradations,
            }
        )
        phases.append(
            JunctionClearPhase(
                label="recede",
                robot_id=robot_id,
                command=command,
                held_robot_ids=tuple(held_robot_ids),
            )
        )

    yield_robots = _junction_yield_axis_robots(decision, geometry)
    yield_result = result.model_copy(
        update={"decision": _as_yield_decision(decision, yield_robots)}
    )
    yield_command = _tag_discarded_order(
        _ground_derived(
            yield_result,
            snapshot=snapshot,
            params=params,
            retreat_choice=retreat_choice,
            crossing_order=None,
            geometry=geometry,
            static_obstacles=static_obstacles,
            yield_feasibility_mode=yield_feasibility_mode,
        ),
        decision,
    )
    acting_robot_ids = {action["robot_id"] for action in yield_command["actions"]}
    extra_holds = [
        {
            "robot_id": robot_id,
            "action": "temporary_wait",
            "parameters": {"duration_sec": params.wait_backstop_sec},
        }
        for robot_id in ranked
        if robot_id not in acting_robot_ids
    ]
    cross_degradations = [*yield_command.get("degradations", []), "junction_clear=cross"]
    if missing_j2:
        # This is the actual silent-failure site: with no J2 override, this
        # yield branch falls back to the shipped 1.7 m head-on clearance
        # instead of the study's junction-scoped number, parking an N-S
        # yielder outside the tracked band with no error otherwise.
        cross_degradations.append(_shipped_unsolved_tag(missing))
    yield_command = validate_coordination_command(
        {
            **yield_command,
            "command_id": f"{result.request_id}-junction-cross",
            "actions": [*yield_command["actions"], *extra_holds],
            "degradations": cross_degradations,
        }
    )
    # Every recede candidate is held (never acting) in the cross phase,
    # whether or not its own hold needed `extra_holds` above (it may
    # already be a `temporary_wait`/absent-but-filtered member of
    # `yield_command` for an unrelated reason -- `ranked` is still the
    # correct, complete held set for THIS phase either way).
    phases.append(
        JunctionClearPhase(
            label="cross", robot_id=None, command=yield_command, held_robot_ids=tuple(ranked)
        )
    )

    if len(ranked) >= 2:
        # Freeze-blocking finding 2 (step-7a fix): stagger the post-composite
        # release instead of letting every recede candidate's hold lapse
        # together the moment the cross phase resolves (`JunctionClearPhasePlan`'s
        # docstring has the full mechanism). `ranked[0]` (chi-cheapest,
        # already first to recede) is addressed by NO action here, so it is
        # free to resume the instant this phase is reached; every other
        # recede candidate, PLUS the grounded yielder ("the yielder re-enters
        # last", (a) Sequencing), is held via a plain `yield` action naming
        # `ranked[0]` as `passer_robot_id` -- M4's existing `CrossingChain`
        # (single-passer path, unchanged) ends each hold once `ranked[0]`'s
        # own odometry shows it cleared `passer_clear_m`, never on a fixed
        # timer. The clearance is geometry-derived, not a constant: the lead's
        # pocket offset plus the SECOND candidate's (far enough to have
        # passed the second candidate's own pocket on the same axis -- there
        # is no lateral room to pass it closer) plus `params.min_distance_m` (the
        # same safety-latch magnitude M4's own monitor enforces, redeclared
        # here rather than imported, since M3 must not depend on M4 config).
        lead_id = ranked[0]
        yielder_id = next(
            (
                action["robot_id"]
                for action in yield_command["actions"]
                if action["action"] == "yield"
            ),
            None,
        )
        release_held = [*ranked[1:], *([yielder_id] if yielder_id is not None else [])]
        # Step-7b ruling (iv): with staggered pockets the lead travels from
        # its own pocket past the SECOND candidate's (shallower) pocket, so
        # the two offsets are summed; without a stagger this is exactly the
        # original `2 * junction_recede_offset_m + min_distance_m`.
        lead_pocket_m = recede_pocket_offset_m(geometry, 0)
        second_pocket_m = recede_pocket_offset_m(geometry, 1)
        assert lead_pocket_m is not None and second_pocket_m is not None
        passer_clear_m = round(lead_pocket_m + second_pocket_m + params.min_distance_m, 3)
        def _passive_hold(hold_sec: float) -> dict[str, Any]:
            # A PASSIVE hold, not a maneuver: `command_bus_node`'s `yield`
            # branch always runs `Nav2Adapter.backup` first
            # (`backup_distance_m` defaults to 0.3 m when absent -- these
            # robots are already correctly parked, so an unrequested 0.3 m
            # additional backup would itself be a bug, not a hold). 0.0
            # completes that step on its first odometry tick, with no real
            # motion. `hold_sec` must be positive or the hold/CrossingChain
            # logic is skipped entirely (`_on_backup_result`'s
            # `hold_sec <= 0.0` branch).
            return {
                "backup_distance_m": 0.0,
                "hold_sec": hold_sec,
                "passer_robot_id": lead_id,
                "passer_clear_m": passer_clear_m,
            }

        # Every non-lead receder: a passive hold gated on the lead alone, as
        # in step 7a. Its own `yield` naming the lead is also what exempts
        # the receder/lead pair while the lead squeezes past it in the aisle
        # (`safety.admitted_partners`; the step-7b rerun measured 0.34 m).
        release_actions = [
            {
                "robot_id": robot_id,
                "action": "yield",
                "parameters": _passive_hold(params.junction_recede_hold_sec),
            }
            for robot_id in ranked[1:]
        ]
        expected_resolution_sec = params.junction_recede_hold_sec
        if yielder_id is not None:
            # Step-7b ruling (vi): the yielder re-enters LAST, behind every
            # receder, through M4's ordered multi-passer path
            # (`crossing_chain.plan_crossing`): passers [lead, *receders],
            # each admitted once its predecessor clears, the hold ending only
            # when the last receder has cleared. Step 7a gated the yielder on
            # the lead alone, so it and the second receder were released at
            # the same instant onto crossing paths (rerun
            # fc_run_20261003_022532: permanent 0.416 m latch). A receder
            # clears once it has crossed the junction box: its pocket offset
            # plus the box half-length plus `min_distance_m`. The second
            # receder keeps its own lead-gated `yield` above instead of the
            # linked `temporary_wait` the ruling's text names: a
            # `temporary_wait` is not a clearing action, so the receder/lead
            # pair would lose its exemption mid-pass and latch (M4 unchanged).
            # The yielder's backstop is twice the receders' so that even a
            # timer-ended hold never frees it together with them.
            receder_pockets = [recede_pocket_offset_m(geometry, r) for r in range(1, len(ranked))]
            receder_clears = [
                round(pocket + geometry.corridor.half_length_m + params.min_distance_m, 3)
                for pocket in receder_pockets
                if pocket is not None
            ]
            assert len(receder_clears) == len(ranked) - 1
            expected_resolution_sec = 2.0 * params.junction_recede_hold_sec
            release_actions.append(
                {
                    "robot_id": yielder_id,
                    "action": "yield",
                    "parameters": {
                        **_passive_hold(expected_resolution_sec),
                        "crossing_order": [lead_id, *ranked[1:]],
                        "crossing_clear_m": [passer_clear_m, *receder_clears],
                    },
                }
            )
        release_command = validate_coordination_command(
            {
                "command_id": f"{result.request_id}-junction-release",
                "actions": release_actions,
                "expected_resolution_time_sec": expected_resolution_sec,
                "fallback": "stop",
                "degradations": ["junction_clear=release"],
            }
        )
        phases.append(
            JunctionClearPhase(
                label="release",
                robot_id=None,
                command=release_command,
                held_robot_ids=tuple(release_held),
            )
        )

    return JunctionClearPhasePlan(
        phases=phases, fallback_command=fallback_command, fallback_held_robot_ids=tuple(ranked)
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


# (a0) Universal `proposed_plan` channel: M3 verify/repair engine.
#
# Division of labor (prereg-v2 design, "The VLM Coordinator"): the VLM
# proposes a scene-wide `CongestionDecision.proposed_plan`; this engine
# verifies it leg-by-leg against the SAME grounding checks the legacy/derived
# templates above already use (`_apply_yield_feasibility`'s room check via
# `yield_feasible`, `_beyond_corridor_same_side`, `_first_passer_refusal`,
# `_junction_same_axis_order`), repairs it with the fewest edits when some
# legs are infeasible, and falls back to its own derived plan
# (`_derive_default_plan`, built from `resolve_strategy_alias` /
# `resolve_yield_roles` / `resolve_robot_order` -- never a re-implementation)
# whenever the VLM's plan is absent, names an unknown robot, is inconsistent
# with the decided strategy, or needs more edits than the registered bound.
#
# This module does not change `ground_reasoner_result` or any dispatch path:
# it is a standalone audit that the next build-order step (M5 plan tracking,
# `junction_clear`) wires into execution.

PlanProvenance = Literal["vlm_verbatim", "repaired", "m3_default"]

# Why `VerifiedPlan.provenance == "m3_default"`, for callers (notably
# `reasoning.rag.plan_metrics`) that must tell "no plan to score" (`absent`,
# `unknown_robot`, `inconsistent` -- the VLM's plan never reached feasibility
# auditing) apart from "a plan was emitted but could not be feasibly repaired"
# (`repair_bound_exceeded`), without parsing `rejection_reason` text.
PlanRejectionStage = Literal["absent", "unknown_robot", "inconsistent", "repair_bound_exceeded"]

# A `proposed_plan` leg's action plays a "role" in the maneuver it names, as
# opposed to a passive "continue"/"wait" bystander. Only role-bearing actions
# need a feasibility check against the scene.
_ROLE_ACTIONS: frozenset[PlanLegAction] = frozenset({"yield", "reverse", "reroute", "cross"})


class PlanEdit(BaseModel):
    """One atomic repair operation applied while reconciling a VLM plan.

    `op` is one of three primitives, defined over positions in the ordered
    leg list: `"swap"` exchanges which robot holds two fixed positions
    (their actions stay pinned to the position, so this is a pure role
    re-assignment -- the swap gate generalized), `"reorder"` exchanges two
    whole legs' positions (each robot keeps its own action, only the
    execution order changes), and `"substitute"` changes one robot's action
    toward M3's own derived plan.
    """

    model_config = ConfigDict(frozen=True)

    op: Literal["swap", "reorder", "substitute"]
    robot_ids: tuple[str, ...]
    reason: str = Field(min_length=1)


class PlanRepairParams(BaseModel):
    """Tunable bound for the verify/repair engine, kept apart from `GroundingParams`.

    `GroundingParams` forbids unknown keys and may be serialized/hashed
    elsewhere; this is a separate, additive model so adding plan-repair
    tuning never touches that contract.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Frozen (step-7b ruling (ii), prereg-v2 (a0) build order item 7: re-swept
    # bounds 1-4 over the full 18-case `junction_clear` corpus, including
    # `recede_order_swapped` (`scripts/junction_clear_repair_bound_sweep.py`,
    # table in `docs/reports/2026-10-03-step7b-oracle-freeze.md`). No bound
    # in 1-4 reaches full repairable coverage (two depth-5 cases remain
    # m3_default even at bound=4); per the ruling's own freeze procedure
    # ("smallest full-coverage bound, else 3 with the documented tail"),
    # freezes at 3 -- which covers 11/14 repairable cases (79%), leaving
    # the two depth-5 cases (`recede_pair_full_axis_swap`,
    # `combined_wrong_pair_and_order`) and the one depth-4 case
    # (`missing_both_recede_candidates`) m3_default-by-design. This bound is
    # global (every v2 strategy's plan channel shares `PlanRepairParams`,
    # not just `junction_clear`); the step-4 two-robot head-on equivalence
    # smoke is unaffected because raising the bound only ever makes MORE
    # plans repairable, never fewer, and every swap-gate repair there costs
    # at most one edit (verified: full suite zero-delta after this change).
    #
    # RE-FROZEN AT 4 (χ-epsilon verbatim rule, RULED 2026-10-03, same
    # registered procedure): with `GroundingParams.
    # junction_recede_order_epsilon`, `recede_order_swapped` leaves the defect
    # corpus (verbatim by rule) and the two depth-5 cases drop to depth 4, so
    # bound 4 reaches full coverage of the 13 remaining repairable cases
    # (m3_default per bound 1/2/3/4: 9/5/3/0;
    # `docs/reports/2026-10-03-plan-grammar-fixes.md`). The procedure picks
    # the smallest full-coverage bound <= 4: procedure, not preference. The
    # depth-3 tail above is therefore no longer m3_default-by-design.
    max_repair_edits: int = Field(default=4, ge=0)


class VerifiedPlan(BaseModel):
    """Outcome of auditing one `CongestionDecision.proposed_plan`.

    `legs` is always a complete, scene-wide plan (every snapshot robot
    covered) ready to feed grounding; `provenance` says whether it is the
    VLM's own plan, a minimally repaired version of it, or M3's independent
    default.
    """

    model_config = ConfigDict(frozen=True)

    legs: list[ProposedPlanLeg]
    provenance: PlanProvenance
    edits: list[PlanEdit] = Field(default_factory=list)
    # Robots the VLM's plan omitted entirely, completed with a `continue` leg
    # (lenient completion); never counted as a repair edit. Populated even
    # when the plan is ultimately rejected, as a diagnostic.
    plan_completed_legs: list[str] = Field(default_factory=list)
    # Human-readable reason, set exactly when `provenance == "m3_default"`.
    rejection_reason: str | None = None
    # Structured counterpart of `rejection_reason`, for `plan_metrics`'
    # emission-rate scoring: None except when `provenance == "m3_default"`.
    rejection_stage: PlanRejectionStage | None = None


def _plan_disagrees_with_decision_fields(
    decision: CongestionDecision, legs: Sequence[ProposedPlanLeg]
) -> str | None:
    """Whether the plan's yield leg/order contradicts the decision's own fields.

    Checked ONCE against the VLM's original (pre-repair) plan only, never
    inside the repair search's acceptance check: repair is explicitly allowed
    to reassign the yield role (the swap gate generalized), so re-running
    this gate on a repair candidate would make that repair impossible.
    `yield_robot`/`crossing_order` are the model's own stated choice at
    decision time; a plan that answers differently is not a partial plan to
    complete or repair, it is a second, conflicting answer -- picking one
    over the other would be reinterpretation, so both failing together is
    treated as inconsistent instead.

    The expected yielder is `resolve_robot_order(decision)[0]` in EVERY mode,
    including `"swap"`, even when `decision.yield_robot` is unset (the
    implicit default is still "the decided yielder"). This is deliberately
    NOT mode-dependent: `"swap"` mode's flexibility is about M3's OWN repair
    re-grounding an infeasible decided yielder to a feasible alternative, not
    about a VLM plan being free to name a different robot from the start --
    the latter would let a plan silently override v1's pre-gate yielder in
    the common two-robot head-on, breaking the "v2 changes no v1 outcome
    semantics there" guarantee at the one place it matters most. A plan that
    wants a different yielder is only honored via feasibility-driven REPAIR
    (`_repair_plan`'s `swap`), never by starting from one.

    Args:
        decision: The decision the plan proposes to refine.
        legs: The VLM's own plan, after lenient completion.

    Returns:
        A reason string on disagreement, else None (including when the
        decision sets neither field, or the strategy is not `yield`).
    """
    if decision.strategy != "yield":
        return None
    yield_legs = [leg.robot_id for leg in legs if leg.action == "yield"]
    expected_yielder = resolve_robot_order(decision)[0]
    if len(yield_legs) == 1 and yield_legs[0] != expected_yielder:
        return (
            f"plan's yield leg ({yield_legs[0]!r}) disagrees with the decision's "
            f"own yield_robot ({expected_yielder!r})"
        )
    if decision.crossing_order is not None:
        plan_order = [leg.robot_id for leg in legs if leg.action == "cross"]
        expected = [rid for rid in decision.crossing_order if rid != expected_yielder]
        if plan_order and set(plan_order) == set(expected) and plan_order != expected:
            return (
                f"plan's crossing order {plan_order!r} disagrees with the decision's "
                f"own crossing_order-derived order {expected!r}"
            )
    return None


def _is_consistent(strategy: str, legs: Sequence[ProposedPlanLeg]) -> bool:
    """Whether `legs` refines `strategy` (the (a0) consistency rule).

    Only the strategies the design spec names carry a constraint
    (`yield` -> exactly one `yield` leg, `temporary_wait` -> at least one
    `wait` leg, `reroute` -> at least one `reroute` leg, `junction_clear` ->
    at least one `reverse` or `yield` leg); `reverse`, `convoy`,
    `priority_override` and `none` are left unconstrained because the spec is
    silent on them -- inventing a rule there would be reinterpretation, not
    verification.

    Args:
        strategy: The decision's own strategy token (never the alias target).
        legs: The complete, scene-wide candidate plan.

    Returns:
        True when `legs` is an acceptable refinement of `strategy`.
    """
    counts = Counter(leg.action for leg in legs)
    if strategy == "yield":
        return counts["yield"] == 1
    if strategy == "reroute":
        return counts["reroute"] >= 1
    if strategy == "temporary_wait":
        return counts["wait"] >= 1
    if strategy == "junction_clear":
        return counts["reverse"] >= 1 or counts["yield"] >= 1
    return True


def _plan_problems(
    legs: Sequence[ProposedPlanLeg],
    decision: CongestionDecision,
    snapshot: SnapshotFrame,
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
    grounding_params: GroundingParams | None = None,
) -> list[tuple[int, str]]:
    """Leg-by-leg feasibility audit, reusing M3's existing grounding checks.

    `yield_feasibility_mode` gates the room/obstacle check: `"off"` never
    checks it at all (v1's ungated behaviour -- a room-infeasible yielder is
    still accepted). `"swap"` and `"refuse"` both check whichever robot the
    CANDIDATE currently assigns the `yield` role -- they do not differ in
    WHICH robot is checked (a plan may legitimately name a yielder
    `decision.yield_robot` never committed to, via
    `_plan_disagrees_with_decision_fields`'s own
    `resolve_robot_order(decision)[0]` baseline, which both modes then
    validate identically); they differ in what happens on failure.
    `"swap"`'s `_ops` may then try a DIFFERENT robot via a `swap` edit.
    `"refuse"`'s `_ops` excludes any yield-touching `swap`
    (`yield_feasibility_mode != "swap"`), so an infeasible candidate there
    can only fall through to `m3_default` -- substitution cannot rescue it
    either, since removing the sole `yield` leg breaks the strategy's own
    consistency rule. This matches `_apply_yield_feasibility`'s `"refuse"`
    branch, which also never considers an alternative.

    The corridor same-side refusal is evaluated AFTER the room check, against
    whichever robot the CANDIDATE currently assigns the `yield` role (v1:
    `_ground_legacy` runs its own same-side check against `robot_ids[0]`
    only after `_apply_yield_feasibility` has already possibly reassigned
    it) -- so unlike the room check this one DOES move with a `swap` edit.
    The `reverse` same-side refusal instead keys on the decision's first two
    involved robots, fixed regardless of which of them still holds a
    `reverse` leg in the candidate (matching `_ground_legacy`'s own
    `robot_ids[0]`/`robot_ids[1]` pairing for `reverse`, which never
    reorders): substituting one of the pair away to `wait` must not silently
    dissolve the refusal for the one still holding `reverse` alone.

    Args:
        legs: Complete, scene-wide candidate plan.
        decision: The decision the plan proposes to refine.
        snapshot: Scene frame supplying every robot's position.
        geometry: Declared scene geometry; several checks are a no-op
            without it (nothing to verify against, same as the legacy gate).
        static_obstacles: Fixed obstacles the yield room check scores against.
        yield_feasibility_mode: The yield feasibility gate mode.
        grounding_params: M3's derived-mode grounding parameters (the chi
            weights); None uses the placeholder default. Only consulted by
            the `junction_clear` recede-set audit below, to recompute the
            SAME chi order `ground_junction_clear_phases` will dispatch.

    Returns:
        `(index, reason)` pairs into `legs` for every leg that fails a check;
        empty when every leg passes.
    """
    positions = {state.robot_id: (state.x, state.y) for state in snapshot.robots}
    problems: list[tuple[int, str]] = []
    active_idx = [i for i, leg in enumerate(legs) if leg.action != "continue"]
    involved = list(decision.involved_robots)

    if decision.strategy == "yield":
        # Exemption pairing: every robot the decision involves must hold a
        # role in the yield (the yielder or a crosser), never a bystander
        # `continue` -- an omitted robot is lenient completion (never
        # reaches here with `continue`+involved together by construction
        # except as a VLM-authored leg), but an explicit `continue` for an
        # involved robot under-specifies the resolution.
        for i, leg in enumerate(legs):
            if leg.action == "continue" and leg.robot_id in involved:
                problems.append(
                    (i, f"{leg.robot_id} is involved in the yield but marked continue")
                )

    yield_idx = [i for i in active_idx if legs[i].action == "yield"]
    cross_idx = [i for i in active_idx if legs[i].action == "cross"]

    def _room_shortfall(robot_id: str, partner_id: str | None) -> str | None:
        position = positions.get(robot_id)
        partner_position = positions.get(partner_id) if partner_id else None
        if geometry is None or position is None or partner_position is None:
            return None
        robot_geometry, arm_side = arm_geometry(geometry, robot_id)
        axis_index = 0 if robot_geometry.corridor.axis == "x" else 1
        side = (
            arm_side
            if arm_side is not None
            else (-1.0 if position[axis_index] < partner_position[axis_index] else 1.0)
        )
        if yield_feasible(position, side, static_obstacles, robot_geometry):
            return None
        room = yield_retreat_room_m(position, side, static_obstacles, robot_geometry)
        return (
            f"{robot_id} has {_room_text(room)} retreat room "
            f"< {required_room_m(robot_geometry):.2f} m required"
        )

    if geometry is not None and yield_feasibility_mode != "off" and yield_idx and involved:
        # Checked against whoever the CANDIDATE currently assigns the yield
        # leg to -- identically for "swap" and "refuse". The two modes do
        # not differ in WHICH robot's room is checked (a plan may legitimately
        # name a yielder `decision.yield_robot` never committed to, e.g. when
        # it is unset; that choice is then "the decided yielder" as far as
        # this plan goes, exactly like `_apply_yield_feasibility`'s own
        # `robot_ids[0]` is whatever `resolve_robot_order` resolved it to).
        # They differ in what happens when that check fails: "swap" lets a
        # `swap` repair edit try a different robot (`_ops` gates this);
        # "refuse" does not, so an infeasible candidate here can only fall
        # through to `m3_default` (never substituted into consistency either,
        # since removing the sole `yield` leg breaks the strategy's own
        # consistency rule) -- matching `_apply_yield_feasibility`'s own
        # `"refuse"` branch, which never considers an alternative.
        order = resolve_robot_order(decision)

        def _other_in_order(robot_id: str) -> str | None:
            return next((rid for rid in order if rid != robot_id), None)

        for i in yield_idx:
            robot_id = legs[i].robot_id
            reason = _room_shortfall(robot_id, _other_in_order(robot_id))
            if reason is not None:
                problems.append((i, reason))

    if geometry is not None and yield_idx and involved:
        # Partner is the first OTHER involved robot regardless of its
        # CURRENT action (v1's `robot_ids[1:]`-based pairing is unaffected by
        # a wait-fan-out substitution already applied to it) -- gating on
        # "first cross leg" instead would let a same-side-blocked yield slip
        # through the moment its partner is substituted to `wait`.
        yielder_id = legs[yield_idx[0]].robot_id
        partner_id = next((rid for rid in involved if rid != yielder_id), None)
        yielder_position = positions.get(yielder_id)
        partner_position = positions.get(partner_id) if partner_id else None
        if partner_id is not None and yielder_position is not None and partner_position is not None:
            yielder_geometry = arm_geometry(geometry, yielder_id)[0]
            if _beyond_corridor_same_side(yielder_position, partner_position, yielder_geometry):
                reason = (
                    f"{yielder_id}/{partner_id} both outside the corridor on the "
                    "same side; a reverse would traverse it"
                )
                problems.append((yield_idx[0], reason))
                partner_idx = next(
                    (i for i in active_idx if legs[i].robot_id == partner_id), None
                )
                if partner_idx is not None and legs[partner_idx].action != "continue":
                    problems.append((partner_idx, reason))

    if decision.strategy == "reverse" and geometry is not None and len(involved) >= 2:
        first_id, second_id = involved[0], involved[1]
        first_position, second_position = positions.get(first_id), positions.get(second_id)
        if (
            first_position is not None
            and second_position is not None
            and _beyond_corridor_same_side(first_position, second_position, geometry)
        ):
            reason = (
                f"{first_id}/{second_id} both outside the corridor on the same side; "
                "a reverse would traverse it"
            )
            for i in active_idx:
                if legs[i].robot_id in (first_id, second_id) and legs[i].action == "reverse":
                    problems.append((i, reason))

    if cross_idx:
        if not yield_idx or yield_idx[0] > cross_idx[0]:
            problems.append(
                (cross_idx[0], "cross leg has no preceding yield leg to release it")
            )
        elif geometry is not None:
            yielder_id = legs[yield_idx[0]].robot_id
            cross_robot_ids = [legs[i].robot_id for i in cross_idx]
            refusal = (
                _first_passer_refusal(yielder_id, cross_robot_ids, positions)
                if len(cross_robot_ids) > 1
                else None
            )
            if refusal is not None:
                problems.append((cross_idx[0], refusal))
            filtered = _junction_same_axis_order(cross_robot_ids, yielder_id, geometry)
            if filtered != cross_robot_ids:
                dropped = set(cross_robot_ids) - set(filtered)
                for i in cross_idx:
                    if legs[i].robot_id in dropped:
                        problems.append(
                            (i, f"{legs[i].robot_id} held opposite a same-axis partner (J1)")
                        )

    if decision.strategy == "junction_clear" and geometry is not None:
        # (a) Grounding's "recede before yield/cross": a recede candidate's
        # `reverse` leg (a `maneuver_geometry.rank_recede_candidates`
        # candidate) must precede every yield-axis `yield`/`cross` leg in
        # list order -- the plan's own analogue of M5's phased dispatch
        # (`ground_junction_clear_phases` never dispatches the yield-axis
        # phase until every recede leg it grounds has resolved). A VLM plan
        # that lists them the other way around is infeasible, not merely
        # suboptimal: the yield-axis escort would run while a recede
        # candidate is still 0.24-0.34 m away, unexempted by
        # `admitted_partners` outside its own command.
        recede_candidates = set(_junction_recede_candidates(decision, geometry))
        recede_idx = [
            i
            for i in active_idx
            if legs[i].robot_id in recede_candidates and legs[i].action == "reverse"
        ]
        later_idx = [
            i
            for i in active_idx
            if legs[i].robot_id not in recede_candidates and legs[i].action in ("yield", "cross")
        ]
        if recede_idx and later_idx:
            last_recede = max(recede_idx)
            for i in later_idx:
                if i < last_recede:
                    problems.append(
                        (
                            i,
                            f"{legs[i].robot_id}'s {legs[i].action} leg precedes a recede "
                            "leg; junction_clear recedes before it yields/crosses",
                        )
                    )

        # Freeze-blocking finding 1 (2026-10-02 IB10 composite smoke, step-4
        # sweep + run B live): the recede-before-yield check above only
        # verifies RELATIVE POSITION; it never checks WHICH robots hold the
        # recede legs (a plan naming the yield-axis pair as the recede set
        # verifies `vlm_verbatim`, a metric hole) or the ORDER BETWEEN the
        # two recede legs themselves (run B's live dispatch order, the
        # opposite of its own proposed plan, also verified `vlm_verbatim`).
        # The recede set is a structural precondition of the geometry
        # (`_junction_recede_candidates`), not something the VLM gets to
        # choose, and its dispatch order is `rank_recede_candidates`' chi
        # order on this SAME snapshot -- recomputed here, never re-derived,
        # so this audit flags exactly the plans `ground_junction_clear_phases`
        # would actually dispatch differently from.
        if recede_candidates:
            wrong_membership_idx = [i for i in active_idx if legs[i].action == "reverse"
                                     and legs[i].robot_id not in recede_candidates]
            for i in wrong_membership_idx:
                problems.append(
                    (
                        i,
                        f"{legs[i].robot_id} holds a reverse leg but is not a structural "
                        "recede candidate (off the yield axis); junction_clear's recede "
                        "set is fixed by geometry, not chosen by the plan",
                    )
                )
            missing_candidate_idx = [
                i
                for i, leg in enumerate(legs)
                if leg.robot_id in recede_candidates and leg.action != "reverse"
            ]
            for i in missing_candidate_idx:
                problems.append(
                    (
                        i,
                        f"{legs[i].robot_id} is a structural recede candidate but holds "
                        f"{legs[i].action!r} instead of reverse",
                    )
                )
            if not wrong_membership_idx and not missing_candidate_idx:
                recede_order_idx = [
                    i
                    for i in active_idx
                    if legs[i].robot_id in recede_candidates and legs[i].action == "reverse"
                ]
                if len(recede_order_idx) >= 2:
                    chi_params = (
                        grounding_params if grounding_params is not None else GroundingParams()
                    )
                    chi_order = rank_recede_candidates(
                        snapshot, sorted(recede_candidates), geometry, chi_params
                    )
                    actual_order = [legs[i].robot_id for i in recede_order_idx]
                    # χ-epsilon verbatim rule (RULED 2026-10-03): an order
                    # within `junction_recede_order_epsilon` of chi's is the
                    # same equivalence class, so it is not a problem here.
                    # Verification only -- dispatch stays in chi order, and
                    # `junction_clear_dispatch_match` records the divergence
                    # as `order_equivalent`. The recede SET audit above
                    # stays strict.
                    if not recede_orders_equivalent(
                        snapshot, actual_order, chi_order, geometry, chi_params
                    ):
                        for i in recede_order_idx:
                            problems.append(
                                (
                                    i,
                                    f"recede order {actual_order!r} disagrees with the "
                                    f"chi-ranked order {chi_order!r}",
                                )
                            )
    return problems


def _derived_yield_degrades_to_reroute(
    snapshot: SnapshotFrame,
    roles: YieldRoles,
    grounding_params: GroundingParams,
    geometry: SceneGeometry,
) -> bool:
    """Whether DERIVED-mode grounding would reroute this yield instead (ruling 3).

    Reuses `prepare_retreat_selection` and `derive_escort_distance`, exactly
    as `_ground_derived` does, so this can never drift from the shipped
    degradation logic. Checked against the best-ranked candidate
    (`selection.candidates[0]`), matching `_ground_derived` with no stage-2
    `retreat_choice` -- this engine accepts none.

    Args:
        snapshot: Scene frame supplying every robot's position.
        roles: The gated yield roles (`resolve_yield_roles`'s non-refused
            output).
        grounding_params: M3's derived-mode grounding parameters.
        geometry: Declared scene geometry.

    Returns:
        True when the backup is infeasible, no candidate survives, or the
        best candidate's escort is infeasible -- the same three conditions
        `_ground_derived` checks before calling `_reroute_yielder`.
    """
    selection = prepare_retreat_selection(
        snapshot, roles.yielder_id, roles.crossing_order, grounding_params, geometry=geometry
    )
    if not selection.backup.feasible or not selection.candidates:
        return True
    chosen = selection.candidates[0]
    escort = derive_escort_distance(
        snapshot,
        roles.crossing_order[0],
        (chosen.x, chosen.y),
        grounding_params,
        geometry=geometry,
        yielder_id=roles.yielder_id,
    )
    return not escort.feasible


def _yield_default_actions(
    working: CongestionDecision,
    snapshot: SnapshotFrame,
    positions: Mapping[str, tuple[float, float]],
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
    grounding_params: GroundingParams | None,
) -> tuple[dict[str, PlanLegAction], list[str]]:
    """The `yield` branch of `_derive_default_plan`'s default-plan derivation.

    Extracted so `junction_clear`'s yield-axis phase, and its fallback to
    plain `yield` (`_junction_clear_default_actions`), run through the
    IDENTICAL derivation an ordinary `yield` decision gets -- never a second
    implementation that could drift from it.

    Args:
        working: A decision with `strategy == "yield"` (the alias-resolved
            decision, or a `junction_clear` sub-decision rebuilt as one --
            see `_junction_clear_default_actions`).
        snapshot: Scene frame supplying every tracked robot and its position.
        positions: `{robot_id: (x, y)}` from `snapshot`, precomputed once by
            the caller.
        geometry: Declared scene geometry, or None for the legacy fallback.
        static_obstacles: Fixed obstacles of the running scenario.
        yield_feasibility_mode: The yield feasibility gate mode.
        grounding_params: M3's derived-mode grounding parameters, or None.

    Returns:
        `(actions, ordered)`: per-robot action overrides for every robot this
        branch assigns a leg to, and those robots in execution order.
    """
    roles = resolve_yield_roles(
        working,
        snapshot,
        geometry=geometry,
        static_obstacles=static_obstacles,
        yield_feasibility_mode=yield_feasibility_mode,
    )
    actions: dict[str, PlanLegAction] = {}
    # `resolve_yield_roles` does not itself apply the legacy multi-passer
    # nearest-first refusal (`_ground_legacy`'s own check, not duplicated
    # there either): apply it here so a 3+-robot default plan refuses
    # exactly where `_ground_legacy` would.
    multi_passer_refusal = (
        _first_passer_refusal(roles.yielder_id, roles.crossing_order, positions)
        if roles.refusal_reason is None and len(roles.crossing_order) > 1
        else None
    )
    if roles.refusal_reason is not None or multi_passer_refusal is not None:
        for robot_id in roles.robot_ids:
            actions[robot_id] = "wait"
        return actions, list(roles.robot_ids)
    if (
        grounding_params is not None
        and grounding_params.mode == "derived"
        and geometry is not None
        and _derived_yield_degrades_to_reroute(snapshot, roles, grounding_params, geometry)
    ):
        # Mirrors `_reroute_yielder`'s dispatch shape exactly: the yielder
        # reroutes, every crossing-order robot waits.
        actions[roles.yielder_id] = "reroute"
        for robot_id in roles.crossing_order:
            actions[robot_id] = "wait"
        return actions, [roles.yielder_id, *roles.crossing_order]
    actions[roles.yielder_id] = "yield"
    for robot_id in roles.crossing_order:
        actions[robot_id] = "cross"
    return actions, [roles.yielder_id, *roles.crossing_order]


def _as_yield_decision(
    working: CongestionDecision, involved_robots: Sequence[str] | None = None
) -> CongestionDecision:
    """Rebuild `working` as a `strategy == "yield"` decision for `_yield_default_actions`.

    `resolve_yield_roles` raises on any decision whose `strategy != "yield"`;
    this is the one place `junction_clear`'s default-plan derivation
    (`_junction_clear_default_actions`) crosses that boundary, always via an
    explicit rebuild, never by mutating `working.strategy` in place.

    Args:
        working: The alias-resolved decision to rebuild.
        involved_robots: The sub-decision's involved robots, or None to keep
            `working.involved_robots` unchanged (the plain-yield fallback).

    Returns:
        A copy with `strategy="yield"`, `involved_robots` as given,
        `yield_robot` carried over only if it is still involved, and
        `crossing_order` cleared (the restricted robot set may not be a
        permutation of the original order; `resolve_yield_roles` falls back
        to its own implicit order either way, so clearing avoids a spurious
        `order=default:non_permutation` degradation tag). A grounding caller
        marks a cleared model order with `_tag_discarded_order`
        (`order=discarded_yield_axis`), never `order=implicit`.
    """
    robots = list(working.involved_robots) if involved_robots is None else list(involved_robots)
    yield_robot = working.yield_robot if working.yield_robot in robots else None
    return working.model_copy(
        update={
            "strategy": "yield",
            "involved_robots": robots,
            "yield_robot": yield_robot,
            "crossing_order": None,
        }
    )


def _tag_discarded_order(command: dict[str, Any], original: CongestionDecision) -> dict[str, Any]:
    """Mark a command grounded from `_as_yield_decision(original)` whose order was discarded.

    Replaces `order=implicit` (which there would claim no order was given)
    with `order=discarded_yield_axis`, or appends that tag when the yield
    axis had too few passers for `order=implicit` to fire. No-op when
    `original` gave no `crossing_order`.
    """
    if original.crossing_order is None:
        return command
    tags = list(command.get("degradations", []))
    marker = "order=discarded_yield_axis"
    if "order=implicit" in tags:
        tags = [marker if tag == "order=implicit" else tag for tag in tags]
    else:
        tags.append(marker)
    return _with_degradations(command, tags)


def _junction_clear_default_actions(
    working: CongestionDecision,
    snapshot: SnapshotFrame,
    positions: Mapping[str, tuple[float, float]],
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
    grounding_params: GroundingParams | None,
) -> tuple[dict[str, PlanLegAction], list[str]]:
    """`junction_clear`'s default plan: the recede set in chi order, then the yield.

    (a) Grounding's "cost-ranked recede selection": chi orders
    `_junction_recede_candidates` (`maneuver_geometry.rank_recede_candidates`)
    -- the involved robots off the yield axis -- lowest cost first; every one
    of them gets a `reverse` leg, in that order (the STAGGERED fallback for
    the two-robot IB10 cross pair is this same ordering, never a
    simultaneous pair). The yield-axis robots then get the IDENTICAL
    derivation an ordinary `yield` decision gets (`_yield_default_actions`,
    via `_as_yield_decision`), listed AFTER every recede leg -- "recede
    before yield/cross" is a property of this ORDER, mirrored in
    `_plan_problems`' audit of a VLM-proposed plan.

    Falls back to plain `yield` over every involved robot -- "v1 behavior
    ... single yield or no-op" exactly as the M5 spec section states it,
    since `yield`'s own J1 filter (`_junction_same_axis_order`) already
    drops a cross-axis robot to no-op there -- when the geometry declares no
    recede precondition: no `junction_recede_offset_m` target, or no involved
    robot has a cross-axis declared arm.

    Args:
        working: The alias-resolved `junction_clear` decision.
        snapshot: Scene frame supplying every tracked robot and its position.
        positions: `{robot_id: (x, y)}` from `snapshot`.
        geometry: Declared scene geometry, or None (always the fallback).
        static_obstacles: Fixed obstacles of the running scenario.
        yield_feasibility_mode: The yield feasibility gate mode.
        grounding_params: M3's derived-mode grounding parameters, or None.

    Returns:
        `(actions, ordered)` covering every involved robot.
    """
    if geometry is None or geometry.junction_recede_offset_m is None:
        return _yield_default_actions(
            _as_yield_decision(working),
            snapshot,
            positions,
            geometry,
            static_obstacles,
            yield_feasibility_mode,
            grounding_params,
        )
    candidates = _junction_recede_candidates(working, geometry)
    recede_params = grounding_params if grounding_params is not None else GroundingParams()
    ranked = rank_recede_candidates(snapshot, candidates, geometry, recede_params)
    if not ranked:
        return _yield_default_actions(
            _as_yield_decision(working),
            snapshot,
            positions,
            geometry,
            static_obstacles,
            yield_feasibility_mode,
            grounding_params,
        )
    actions: dict[str, PlanLegAction] = {robot_id: "reverse" for robot_id in ranked}
    yield_robots = _junction_yield_axis_robots(working, geometry)
    yield_actions, yield_ordered = _yield_default_actions(
        _as_yield_decision(working, yield_robots),
        snapshot,
        positions,
        geometry,
        static_obstacles,
        yield_feasibility_mode,
        grounding_params,
    )
    actions.update(yield_actions)
    return actions, [*ranked, *yield_ordered]


def _derive_default_plan(
    decision: CongestionDecision,
    snapshot: SnapshotFrame,
    *,
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
    priorities: Mapping[str, int] | None,
    grounding_params: GroundingParams | None = None,
) -> list[ProposedPlanLeg]:
    """M3's own scene-wide plan for `decision`: the repair target and fallback.

    Built only from the functions `ground_reasoner_result` already grounds a
    command with (`resolve_strategy_alias`, `resolve_yield_roles`,
    `resolve_robot_order`) -- never a re-implementation -- so a plan-less
    decision's `m3_default` plan always names the same yielder/order/action
    the legacy and derived templates would already have dispatched.

    Repair-semantics ruling 3 (2026-10-02, `docs/implementation_notes.md`):
    with `grounding_params.mode == "derived"`, a `yield` decision also runs
    the SAME backup-band / retreat-candidate / escort feasibility sweep
    `_ground_derived` runs (`prepare_retreat_selection`, then
    `derive_escort_distance` for the best-ranked candidate), and degrades to
    the identical `reroute`-the-yielder shape `_reroute_yielder` dispatches
    when that sweep fails -- never a re-implementation of that degradation
    either. `grounding_params=None` (or `mode != "derived"`) is the pre-ruling-3
    behaviour exactly (LEGACY mode has no band to model). Like `_ground_derived`
    called with no stage-2 `retreat_choice` (this engine accepts none), the
    best-ranked candidate (`selection.candidates[0]`) is the one checked; a
    specific stage-2 pick is not modelled here.

    Args:
        decision: A validated, congestion-detected decision.
        snapshot: Scene frame supplying every tracked robot and its position.
        geometry: Declared scene geometry, or None for the legacy fallback.
        static_obstacles: Fixed obstacles of the running scenario.
        yield_feasibility_mode: The yield feasibility gate mode.
        priorities: M5's registry priorities, for `priority_override`.
        grounding_params: M3's derived-mode grounding parameters, or None for
            the legacy-only behaviour predating ruling 3.

    Returns:
        A complete plan: every `snapshot` robot gets exactly one leg.
    """
    known_robot_ids = [state.robot_id for state in snapshot.robots]
    positions = {state.robot_id: (state.x, state.y) for state in snapshot.robots}
    alias = resolve_strategy_alias(decision, snapshot, geometry=geometry, priorities=priorities)
    working = alias.decision if alias is not None else decision
    actions: dict[str, PlanLegAction] = dict.fromkeys(known_robot_ids, "continue")
    ordered: list[str] = []

    if working.strategy == "yield":
        yield_actions, yield_ordered = _yield_default_actions(
            working,
            snapshot,
            positions,
            geometry,
            static_obstacles,
            yield_feasibility_mode,
            grounding_params,
        )
        actions.update(yield_actions)
        ordered = yield_ordered
    elif working.strategy == "junction_clear":
        junction_actions, junction_ordered = _junction_clear_default_actions(
            working,
            snapshot,
            positions,
            geometry,
            static_obstacles,
            yield_feasibility_mode,
            grounding_params,
        )
        actions.update(junction_actions)
        ordered = junction_ordered
    elif working.strategy == "reverse":
        order = resolve_robot_order(working)
        refused = geometry is not None and any(
            _beyond_corridor_same_side(positions[a], positions[b], geometry)
            for a, b in combinations(order, 2)
            if a in positions and b in positions
        )
        for robot_id in order:
            actions[robot_id] = "wait" if refused else "reverse"
        ordered = order
    elif working.strategy == "temporary_wait":
        order = resolve_robot_order(working)
        for robot_id in order:
            actions[robot_id] = "wait"
        ordered = order
    elif working.strategy == "reroute":
        order = resolve_robot_order(working)
        if order:
            actions[order[0]] = "reroute"
            # TODO(junction_clear, prereg-v2 design.md build-order step 5): a
            # `wait` leg has no scene-geometry feasibility check of its own
            # yet (same documented placeholder as `_plan_problems`'s "reroute/
            # wait/continue legs have no scene geometry check of their own" --
            # `docs/implementation_notes.md`). The loop-map reroute grounding
            # (build-order step 8) is the natural owner; not silently assumed
            # feasible, just not modelled here either.
            for robot_id in order[1:]:
                actions[robot_id] = "wait"
        ordered = order
    else:
        # `convoy`/`priority_override` with no unique alias mapping: the
        # legacy templates' non-spatial wait fan-out (`_ground_legacy`).
        order = resolve_robot_order(working)
        for robot_id in order:
            actions[robot_id] = "wait"
        ordered = order

    remaining = [rid for rid in known_robot_ids if rid not in ordered]
    return [ProposedPlanLeg(robot_id=rid, action=actions[rid]) for rid in [*ordered, *remaining]]


def _preferred_yielder(
    decision: CongestionDecision,
    snapshot: SnapshotFrame,
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
) -> str | None:
    """The yielder M3's own feasibility candidate scan would pick, if any.

    Repair-semantics ruling 2 (2026-10-02, `docs/implementation_notes.md`):
    equal-cost repair candidates tie-break toward M3's derived plan,
    "including its yielder pick". For a 3+-robot compound defect (a
    room-infeasible decided yielder AND an independent crossing-order
    violation), `_derive_default_plan`'s own output has no yielder to
    compare against -- `_first_passer_refusal` collapses it to an all-wait
    fan-out, matching v1's own refusal there (see the OPEN CONTRACT
    QUESTION entry this ruling resolves). The candidate `_apply_yield_feasibility`
    itself would reground to (the first room-feasible robot in
    `robot_ids[1:]`, `"swap"` mode only) is still well-defined at that
    point, before the downstream multi-passer refusal discards it -- this
    exposes exactly that pick, independently of `_derive_default_plan`, so
    the repair search can prefer it without changing what `_derive_default_plan`
    itself returns.

    Args:
        decision: The decision the plan refines.
        snapshot: Scene frame supplying every robot's position.
        geometry: Declared scene geometry; None means the gate cannot run.
        static_obstacles: Fixed obstacles of the running scenario.
        yield_feasibility_mode: The yield feasibility gate mode; only
            `"swap"` ever reassigns a yielder, so every other mode returns
            None (no preference -- matches the "yielder never reassigned"
            hard mode contract).

    Returns:
        The robot id M3's own gate would assign the yield role to, or None
        when the decision is not a yield, geometry is absent, the mode never
        reassigns, or a position is missing.
    """
    if decision.strategy != "yield" or geometry is None or yield_feasibility_mode != "swap":
        return None
    robot_ids = resolve_robot_order(decision)
    if len(robot_ids) < 2:
        return None
    positions = {state.robot_id: (state.x, state.y) for state in snapshot.robots}
    if any(robot_id not in positions for robot_id in robot_ids):
        return None
    result = _apply_yield_feasibility(
        robot_ids, positions, static_obstacles, geometry, yield_feasibility_mode
    )
    return result.robot_ids[0] if result.refusal_reason is None else None


def _edit_reason(
    op: Literal["swap", "reorder", "substitute"],
    idx: tuple[int, ...],
    before: Sequence[ProposedPlanLeg],
    problems_by_index: Mapping[int, str],
    extra: str,
) -> str:
    if op == "substitute":
        (i,) = idx
        cause = problems_by_index.get(i)
        detail = f": {cause}" if cause else ""
        return (
            f"{before[i].robot_id}: {before[i].action} infeasible{detail}; "
            f"substituted to {extra} toward M3's derived plan"
        )
    i, j = idx
    cause = problems_by_index.get(i) or problems_by_index.get(j)
    detail = f": {cause}" if cause else ""
    if op == "swap":
        return (
            f"yield re-grounded{detail}; swapped roles {before[i].robot_id} "
            f"({before[i].action}) <-> {before[j].robot_id} ({before[j].action})"
        )
    return (
        f"reordered{detail}; {before[i].robot_id} and {before[j].robot_id} "
        "exchanged position"
    )


def _repair_plan(
    legs: list[ProposedPlanLeg],
    decision: CongestionDecision,
    snapshot: SnapshotFrame,
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
    default_by_robot: Mapping[str, PlanLegAction],
    max_edits: int,
    grounding_params: GroundingParams | None = None,
) -> tuple[list[ProposedPlanLeg] | None, list[PlanEdit]]:
    """Breadth-first minimal repair toward `default_by_robot`.

    Explores three operations over positions of the decision's own involved
    robots (`PlanEdit`'s docstring): `swap` (exchange which robot holds two
    fixed positions, generalizing the one-leg swap gate), `reorder` (exchange
    two whole legs' positions, for an ordering-only defect), and `substitute`
    toward M3's derived action for that robot. Breadth-first search over a
    bounded depth makes "fewest edits first" true by construction: every
    accepted plan found at a given depth is collected before any is returned,
    so a minimal-depth tie between several accepted candidates is broken by
    preference, not by discovery order alone (repair-semantics ruling 2,
    2026-10-02): a candidate whose `yield` leg matches `_preferred_yielder`
    (M3's own feasibility-gate pick, when the decision is a yield under
    `"swap"` mode) is preferred over one that does not; remaining ties break
    on a fixed, deterministic operation order (swaps, then reorders, then
    substitutions, each sorted by position -- see `_ops`'s docstring comment
    for why that order, not the reverse). This never widens the search past
    the minimal depth: a preferred-yielder candidate only wins over another
    candidate already accepted at the SAME depth.

    Args:
        legs: The VLM's plan after lenient completion (every snapshot robot
            covered); at least one leg fails `_plan_problems`.
        decision: The decision the plan proposes to refine.
        snapshot: Scene frame supplying every robot's position.
        geometry: Declared scene geometry.
        static_obstacles: Fixed obstacles of the running scenario.
        yield_feasibility_mode: The yield feasibility gate mode; forwarded to
            `_plan_problems` so a `"refuse"`-mode infeasibility (which never
            accepts a reassigned yielder) cannot be "fixed" by a `swap`.
        default_by_robot: M3's own derived action per robot
            (`_derive_default_plan`), the repair's substitution target.
        max_edits: Inclusive bound on the number of edits tried.
        grounding_params: M3's derived-mode grounding parameters (the chi
            weights); forwarded to `_plan_problems` so the `junction_clear`
            recede-order audit searches toward the SAME chi order
            `ground_junction_clear_phases` will dispatch, not a default one.

    Returns:
        `(repaired_legs, edits)` for the minimal repair found, or
        `(None, [])` when no accepted plan exists within `max_edits`.
    """
    preferred_yielder = _preferred_yielder(
        decision, snapshot, geometry, static_obstacles, yield_feasibility_mode
    )
    touchable = [i for i, leg in enumerate(legs) if leg.robot_id in set(decision.involved_robots)]

    def _problems(state: Sequence[ProposedPlanLeg]) -> dict[int, str]:
        return dict(
            _plan_problems(
                state,
                decision,
                snapshot,
                geometry,
                static_obstacles,
                yield_feasibility_mode,
                grounding_params,
            )
        )

    def _accepted(state: Sequence[ProposedPlanLeg]) -> bool:
        return _is_consistent(decision.strategy, state) and not _problems(state)

    def _ops(state: Sequence[ProposedPlanLeg]) -> list[tuple[str, tuple[int, ...], str]]:
        # Fixed, deterministic tie-break order: `reorder` (never changes who
        # holds which role) is tried before `swap` (a role re-assignment),
        # which is tried before `substitute` (can "bench" a robot to
        # wait/continue). `reorder` first means a pure ordering defect is
        # fixed by reordering, not by moving the yield role, whenever a
        # reorder can fix it alone -- `swap` only reassigns roles when
        # reordering cannot. Both are tried before `substitute`, which is a
        # degenerate, less useful repair at equal edit cost otherwise.
        #
        # A `swap` touching the `yield` role is never generated unless
        # `yield_feasibility_mode == "swap"`: `"off"` and `"refuse"` mean "the
        # yielder is never reassigned" as a hard mode contract (mirroring
        # `_apply_yield_feasibility`'s own mode gate), not just "no room-based
        # reassignment" -- an ordering-defect swap must not smuggle a yielder
        # change past that contract either.
        ops: list[tuple[str, tuple[int, ...], str]] = []
        for i, j in combinations(touchable, 2):
            ops.append(("reorder", (i, j), ""))
        if yield_feasibility_mode == "swap":
            for i, j in combinations(touchable, 2):
                if state[i].action != state[j].action:
                    ops.append(("swap", (i, j), ""))
        else:
            for i, j in combinations(touchable, 2):
                if state[i].action != state[j].action and "yield" not in (
                    state[i].action,
                    state[j].action,
                ):
                    ops.append(("swap", (i, j), ""))
        for i in touchable:
            target = default_by_robot.get(state[i].robot_id)
            if target is not None and target != state[i].action:
                ops.append(("substitute", (i,), target))
        return ops

    def _apply(
        state: Sequence[ProposedPlanLeg], op: str, idx: tuple[int, ...], extra: str
    ) -> list[ProposedPlanLeg]:
        new_state = list(state)
        if op == "substitute":
            (i,) = idx
            new_state[i] = ProposedPlanLeg(robot_id=state[i].robot_id, action=extra)
        elif op == "swap":
            i, j = idx
            new_state[i] = ProposedPlanLeg(robot_id=state[j].robot_id, action=state[i].action)
            new_state[j] = ProposedPlanLeg(robot_id=state[i].robot_id, action=state[j].action)
        else:  # reorder
            i, j = idx
            new_state[i], new_state[j] = state[j], state[i]
        return new_state

    def _key(state: Sequence[ProposedPlanLeg]) -> tuple[tuple[str, str], ...]:
        return tuple((leg.robot_id, leg.action) for leg in state)

    def _matches_preferred_yielder(state: Sequence[ProposedPlanLeg]) -> bool:
        if preferred_yielder is None:
            return False
        yield_leg = next((leg for leg in state if leg.action == "yield"), None)
        return yield_leg is not None and yield_leg.robot_id == preferred_yielder

    frontier: list[tuple[list[ProposedPlanLeg], list[PlanEdit]]] = [(legs, [])]
    visited = {_key(legs)}
    for _depth in range(max_edits):
        next_frontier: list[tuple[list[ProposedPlanLeg], list[PlanEdit]]] = []
        accepted: list[tuple[list[ProposedPlanLeg], list[PlanEdit]]] = []
        for state, edits in frontier:
            problems_by_index = _problems(state)
            for op, idx, extra in _ops(state):
                candidate = _apply(state, op, idx, extra)
                key = _key(candidate)
                if key in visited:
                    continue
                visited.add(key)
                reason = _edit_reason(op, idx, state, problems_by_index, extra)
                robot_ids = tuple(sorted({state[i].robot_id for i in idx}))
                new_edits = [*edits, PlanEdit(op=op, robot_ids=robot_ids, reason=reason)]
                if _accepted(candidate):
                    accepted.append((candidate, new_edits))
                else:
                    next_frontier.append((candidate, new_edits))
        if accepted:
            # Equal-cost (same minimal depth) tie-break toward M3's own
            # feasibility-gate yielder pick (ruling 2); the first-found
            # candidate (fixed `_ops` enumeration order) wins when none
            # matches, preserving every pre-existing outcome.
            preferred = [
                candidate for candidate in accepted if _matches_preferred_yielder(candidate[0])
            ]
            return preferred[0] if preferred else accepted[0]
        frontier = next_frontier
        if not frontier:
            break
    return None, []


def verify_and_repair_plan(
    decision: CongestionDecision,
    snapshot: SnapshotFrame,
    *,
    geometry: SceneGeometry | None = None,
    static_obstacles: Sequence[StaticObstacleInput] = (),
    yield_feasibility_mode: YieldFeasibilityMode = "off",
    repair_params: PlanRepairParams | None = None,
    priorities: Mapping[str, int] | None = None,
    grounding_params: GroundingParams | None = None,
) -> VerifiedPlan:
    """Audit, and if needed minimally repair, a decision's `proposed_plan`.

    Per-decision outcome (prereg-v2 (a0), "Verify/repair contract"):

    - Plan absent -> M3's own derived plan, provenance `m3_default`. For
      LEGACY-mode grounding (`grounding_params=None` or `mode != "derived"`)
      this has been verified to match `ground_reasoner_result`'s actual
      dispatched command exactly, over the full two-robot
      strategy/yielder/position/geometry/gate matrix
      (`TestDefaultPlanMatchesLegacyGrounding`) plus a 3-robot multi-passer
      matrix (`TestDefaultPlanMatchesLegacyThreeRobotMultiPasserMatrix`), both
      in `tests/unit/test_plan_verifier.py`.
      RESOLVED by repair-semantics ruling 3 (2026-10-02): with
      `grounding_params.mode == "derived"`, the DERIVED-mode backup-band /
      retreat-candidate sweep (`prepare_retreat_selection`, then
      `derive_escort_distance`) is also modelled
      (`_derived_yield_degrades_to_reroute`), so a feasible-by-the-legacy-check
      yield that DERIVED mode would actually reroute now defaults to that
      `reroute` too -- verified against `ground_reasoner_result`'s actual
      derived-mode dispatch, including the shipped `config/rag.yaml` values
      and a deliberately-impossible `backup_band_m`
      (`TestDefaultPlanMatchesDerivedGrounding`,
      `test_default_plan_does_not_model_derived_mode_band_infeasibility`,
      now flipped to assert parity). `grounding_params=None` keeps the
      pre-ruling-3 LEGACY-only behaviour exactly; a specific stage-2
      `retreat_choice` is still not modelled (this engine accepts none), so
      the check runs against the best-ranked candidate, matching
      `_ground_derived` with no stage-2 choice.
    - Plan present but naming a robot outside `snapshot` -> treated as
      unparseable, `m3_default`, reason logged (never reinterpreted as a
      partial plan).
    - Plan present, scene-wide complete (robots it omits are leniently
      completed with `continue`, logged in `plan_completed_legs`, not a
      repair), inconsistent with `decision.strategy` -> `m3_default`, reason
      logged. A plan whose own `yield` leg or crossing order contradicts the
      decision's own `yield_robot`/`crossing_order` (set at decision time) is
      also treated as inconsistent here -- a second, conflicting answer, not
      a partial one; picking one field over the other would be
      reinterpretation. This check runs once against the VLM's original
      plan, never inside the repair search, so repair remains free to
      reassign the yield role (the swap gate generalized).
    - Plan present, consistent, every leg feasible -> executed verbatim,
      `vlm_verbatim`.
    - Plan present, consistent, one or more legs infeasible -> the minimal
      repair (`_repair_plan`) toward M3's own derived plan, `repaired`, every
      edit logged with its reason.
    - Repair distance exceeds `repair_params.max_repair_edits` -> M3's own
      derived plan, `m3_default`, reason logged.

    In a two-robot head-on this reduces to the existing swap gate as a
    one-leg repair: the VLM's one `yield` leg on the infeasible robot and one
    `cross` leg on the feasible one are fixed by exactly one `swap` edit, and
    the result names the same yielder and order `_apply_yield_feasibility`'s
    `"swap"` mode would have chosen. Verified over the full two-robot
    strategy/yielder/position/geometry/gate matrix WITH the plan present
    (`TestPlanPresentTwoRobotMatchesLegacyGrounding`), not just absent: the
    executed legs match `ground_reasoner_result`'s actual dispatched command
    exactly in every one of those cells.

    `"off"` and `"refuse"` are a hard mode contract, not just "no room-based
    reassignment": the yielder is NEVER reassigned under either, even by a
    `swap` edit that would otherwise fix an unrelated ordering defect too
    (`_repair_plan`'s `_ops` excludes a yield-touching `swap` unless
    `yield_feasibility_mode == "swap"`, mirroring `_apply_yield_feasibility`'s
    own mode gate exactly).

    RESOLVED by repair-semantics rulings 1-2 (2026-10-02,
    `docs/implementation_notes.md`; plan PRESENT, 3+ robots only -- the
    two-robot and plan-absent guarantees above are unaffected and fully
    verified). `_first_passer_refusal`'s own comment records a deliberate v1
    design choice -- a bad crossing order is "refused rather than reordered,
    so the executed order is always the decided one" -- but ruling 1 confirms
    that reorder repairs MAY resolve a 3+-robot plan-PRESENT scene v1's
    refuse-only ordering policy would abandon: that capability is this
    contract's purpose, and v1's plan-ABSENT behaviour is untouched. For the
    two cells of that sweep that are genuine yielder reassignments (not pure
    reorders), ruling 2 settles which robot wins a same-depth tie: toward
    `_apply_yield_feasibility`'s own candidate-scan pick (`_preferred_yielder`),
    not the first candidate the BFS's fixed enumeration order happens to find.
    Current, pinned behaviour: `TestRepairCanResolveWhatLegacyRefuses`,
    `TestTieBreakPrefersFeasibilityGateYielder`,
    `TestPlanPresentThreeRobotMultiPasserMatrix`.

    Args:
        decision: A validated, congestion-detected decision.
        snapshot: Scene frame supplying every tracked robot and its position.
        geometry: Declared scene geometry, or None for the legacy fallback
            (several feasibility checks are then a no-op, matching the
            legacy gate's behaviour without a declared scene).
        static_obstacles: Fixed obstacles of the running scenario.
        yield_feasibility_mode: The yield feasibility gate mode used to
            derive M3's own plan and audit `yield` legs.
        repair_params: The repair-distance bound; None uses the placeholder
            default.
        priorities: M5's registry priorities, for a `priority_override`
            decision's default plan.
        grounding_params: M3's derived-mode grounding parameters (ruling 3);
            None keeps the default plan LEGACY-only, as before this ruling.

    Returns:
        The verified (or repaired, or defaulted) plan.

    Raises:
        CommandGroundingError: If the decision reports no congestion.
    """
    if not decision.congestion_detected:
        raise CommandGroundingError("cannot verify a plan for a non-congestion decision")
    repair_params = repair_params or PlanRepairParams()
    known_robot_ids = [state.robot_id for state in snapshot.robots]
    default_legs = _derive_default_plan(
        decision,
        snapshot,
        geometry=geometry,
        static_obstacles=static_obstacles,
        yield_feasibility_mode=yield_feasibility_mode,
        priorities=priorities,
        grounding_params=grounding_params,
    )

    if decision.proposed_plan is None:
        return VerifiedPlan(
            legs=default_legs,
            provenance="m3_default",
            rejection_reason="plan absent",
            rejection_stage="absent",
        )

    named_ids = {leg.robot_id for leg in decision.proposed_plan}
    unknown = sorted(named_ids - set(known_robot_ids))
    if unknown:
        return VerifiedPlan(
            legs=default_legs,
            provenance="m3_default",
            rejection_reason=f"plan unparseable: unknown robot_id(s) {unknown!r}",
            rejection_stage="unknown_robot",
        )

    completed = [rid for rid in known_robot_ids if rid not in named_ids]
    legs: list[ProposedPlanLeg] = [
        *decision.proposed_plan,
        *(ProposedPlanLeg(robot_id=rid, action="continue") for rid in completed),
    ]

    field_disagreement = _plan_disagrees_with_decision_fields(decision, legs)
    if not _is_consistent(decision.strategy, legs) or field_disagreement is not None:
        reason = field_disagreement or (
            f"plan inconsistent: strategy {decision.strategy!r} is not refined by "
            f"actions {[leg.action for leg in decision.proposed_plan]!r}"
        )
        return VerifiedPlan(
            legs=default_legs,
            provenance="m3_default",
            plan_completed_legs=completed,
            rejection_reason=reason,
            rejection_stage="inconsistent",
        )

    if not _plan_problems(
        legs,
        decision,
        snapshot,
        geometry,
        static_obstacles,
        yield_feasibility_mode,
        grounding_params,
    ):
        return VerifiedPlan(legs=legs, provenance="vlm_verbatim", plan_completed_legs=completed)

    default_by_robot = {leg.robot_id: leg.action for leg in default_legs}
    repaired, edits = _repair_plan(
        legs,
        decision,
        snapshot,
        geometry,
        static_obstacles,
        yield_feasibility_mode,
        default_by_robot,
        repair_params.max_repair_edits,
        grounding_params,
    )
    if repaired is None:
        return VerifiedPlan(
            legs=default_legs,
            provenance="m3_default",
            plan_completed_legs=completed,
            rejection_reason=f"repair distance exceeds bound {repair_params.max_repair_edits}",
            rejection_stage="repair_bound_exceeded",
        )
    return VerifiedPlan(
        legs=repaired, provenance="repaired", edits=edits, plan_completed_legs=completed
    )


def project_dispatched_legs(
    command: dict[str, Any], known_robot_ids: Sequence[str]
) -> dict[str, str]:
    """Project an actually-dispatched grounded command onto the (a0) leg vocabulary.

    `verify_and_repair_plan` is a standalone audit: in two-robot head-ons its
    output is verified to match `ground_reasoner_result`'s real dispatch
    exactly, but for a 3+-robot plan-PRESENT scene (repair-semantics ruling 1)
    and for a plan-present yield under DERIVED mode's backup-band sweep (which
    `_plan_problems` does not model), the executed command CAN legitimately
    differ from `VerifiedPlan.legs` -- the engine measures what the VLM
    proposed, it does not drive what M4 receives. This function makes that
    comparison possible rather than silently assumed away: it projects the
    actually-dispatched command back onto the SAME per-robot action
    vocabulary, so a caller (`InProcessPipeline`) can record whether the
    tracked plan's legs are what actually went out.

    A `temporary_wait` action is a `cross` leg exactly when the command also
    contains a `yield` (M4's ordered-release convention for a suppressed
    passer; both `_ground_legacy` and `_ground_derived` use it); otherwise it
    is a genuine `wait`. A robot the command names no action for gets
    `continue` (the plan's own scene-wide completion convention).

    Args:
        command: A grounded, schema-valid coordination command.
        known_robot_ids: Every tracked robot in the scene.

    Returns:
        `{robot_id: action}` in the (a0) `PlanLegAction` vocabulary, one
        entry per `known_robot_ids`.
    """
    acted = {action["robot_id"]: action["action"] for action in command.get("actions", [])}
    has_yield = any(action == "yield" for action in acted.values())
    projected: dict[str, str] = {}
    for robot_id in known_robot_ids:
        action = acted.get(robot_id, "continue")
        if action == "temporary_wait":
            projected[robot_id] = "cross" if has_yield else "wait"
        else:
            projected[robot_id] = action
    return projected


def plan_matches_dispatch(
    plan_legs: Sequence[ProposedPlanLeg],
    command: dict[str, Any],
    known_robot_ids: Sequence[str],
) -> bool:
    """Whether a tracked plan's legs are the SAME actions the command actually dispatches.

    Per-robot action equality only (not execution order): the plan-stability
    and provenance metrics are about which maneuver each robot was assigned,
    and order-only divergences are the documented ruling-1 reorder case,
    already a known, accepted gap -- this flag is about the stronger failure
    mode, a robot's recorded leg action being one nobody actually commanded.

    Args:
        plan_legs: The accepted plan's legs (`TrackedPlan.as_proposed_plan()`
            or `VerifiedPlan.legs`).
        command: The actually-dispatched grounded command.
        known_robot_ids: Every tracked robot in the scene.

    Returns:
        True when every robot's projected dispatched action equals its plan
        leg's action.
    """
    dispatched = project_dispatched_legs(command, known_robot_ids)
    plan_by_robot = {leg.robot_id: leg.action for leg in plan_legs}
    return dispatched == plan_by_robot


class JunctionDispatchMatch(BaseModel):
    """Order-aware comparison of a tracked plan against a `junction_clear` phase sequence."""

    model_config = ConfigDict(frozen=True)

    # Every robot's reconstructed dispatched action equals its plan leg's
    # action AND the plan's recede order is the dispatched recede order or
    # within its χ-epsilon equivalence class.
    matches: bool
    # True exactly when the plan's recede order differs from the dispatched
    # (χ) order but is within `GroundingParams.junction_recede_order_epsilon`
    # (the χ-epsilon verbatim rule): the verified plan and the dispatch
    # diverge inside the defined equivalence class, recorded, never hidden.
    order_equivalent: bool = False


def _dispatched_recede_order(plan: JunctionClearPhasePlan) -> list[str]:
    order: list[str] = []
    for phase in plan.phases:
        for action in phase.command.get("actions", []):
            if action["action"] == "reverse" and action["robot_id"] not in order:
                if action["robot_id"] not in phase.held_robot_ids:
                    order.append(action["robot_id"])
    return order


def junction_clear_dispatch_match(
    plan_legs: Sequence[ProposedPlanLeg],
    plan: JunctionClearPhasePlan,
    known_robot_ids: Sequence[str],
    *,
    snapshot: SnapshotFrame,
    geometry: SceneGeometry,
    params: GroundingParams,
) -> JunctionDispatchMatch:
    """`plan_matches_dispatch`'s order-aware analogue for a `junction_clear` sequence.

    A SINGLE dispatched command cannot be compared against the tracked
    plan's full sequence for this strategy the way `plan_matches_dispatch`
    compares an ordinary decision's one command: `junction_clear` phases
    across SEVERAL commands, each addressing every involved robot but only
    ACTING on some of them (`JunctionClearPhase.held_robot_ids` for the
    rest). This reconstructs the per-robot action the WHOLE sequence
    dispatches -- each robot's action from whichever phase actually acts on
    it, every phase's held robots excluded from its own contribution -- and
    compares that reconstruction to the tracked plan.

    Order-aware since the χ-epsilon verbatim rule (RULED 2026-10-03): the
    plan's `reverse` legs, in list order, are also compared with the order
    the recede phases dispatch them in. Dispatch always follows χ, so a
    verified plan whose recede order differs within epsilon is still a
    match, flagged `order_equivalent`; a difference beyond epsilon is not a
    match (freeze-blocker 1 stays closed).

    Args:
        plan_legs: The accepted plan's legs.
        plan: The full precomputed phase sequence
            (`ground_junction_clear_phases`'s output).
        known_robot_ids: Every tracked robot in the scene.
        snapshot: The snapshot the phases were grounded from (χ is ranked
            on it).
        geometry: Declared scene geometry the phases were grounded under.
        params: Grounding parameters (χ weights and the epsilon).

    Returns:
        The match and the order-equivalence flag.
    """
    dispatched: dict[str, str] = dict.fromkeys(known_robot_ids, "continue")
    for phase in plan.phases:
        held = set(phase.held_robot_ids)
        # A phase only contributes for a robot it actually addresses (step-7a
        # fix: the trailing "release" phase addresses only the held-over
        # robots, never the already-released lead -- without this guard, the
        # lead's `project_dispatched_legs` default of "continue" for a robot
        # the command never names would overwrite its REAL action from an
        # earlier phase purely because it is also not `held` here).
        acted_robot_ids = {action["robot_id"] for action in phase.command.get("actions", [])}
        for robot_id, action in project_dispatched_legs(phase.command, known_robot_ids).items():
            if robot_id not in held and robot_id in acted_robot_ids:
                dispatched[robot_id] = action
    plan_by_robot = {leg.robot_id: leg.action for leg in plan_legs}
    actions_match = dispatched == plan_by_robot
    plan_order = [leg.robot_id for leg in plan_legs if leg.action == "reverse"]
    dispatched_order = _dispatched_recede_order(plan)
    if plan_order == dispatched_order:
        return JunctionDispatchMatch(matches=actions_match)
    if recede_orders_equivalent(snapshot, plan_order, dispatched_order, geometry, params):
        return JunctionDispatchMatch(matches=actions_match, order_equivalent=True)
    return JunctionDispatchMatch(matches=False)


# Verifier-candidate-options condition (prereg-v2 rev 6 apparatus, round-3
# "constraints-in-prompt" recipe; 2026-10-04). The actions offered, in plan
# vocabulary order. `continue` is never listed: it is the "not part of the
# resolution" leg every robot may take, already stated by the plan grammar.
_CANDIDATE_OPTION_ACTIONS: tuple[PlanLegAction, ...] = (
    "yield",
    "reverse",
    "cross",
    "wait",
    "reroute",
)
_ARM_NAMES: dict[tuple[str, int], str] = {
    ("x", 1): "east arm",
    ("x", -1): "west arm",
    ("y", 1): "north arm",
    ("y", -1): "south arm",
}


def _nearest_partner(snapshot: SnapshotFrame, robot_id: str) -> str | None:
    state = snapshot.find_robot(robot_id)
    if state is None:
        return None
    others = [s for s in snapshot.robots if s.robot_id != robot_id]
    if not others:
        return None
    return min(
        others, key=lambda s: (math.hypot(s.x - state.x, s.y - state.y), s.robot_id)
    ).robot_id


def _probe_decision(
    strategy: str, involved: list[str], yield_robot: str | None = None
) -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=involved,
        root_cause="candidate-option probe",
        strategy=strategy,
        justification="candidate-option probe",
        yield_robot=yield_robot,
    )


def _probe_flags(
    decision: CongestionDecision,
    assigned: Mapping[str, PlanLegAction],
    snapshot: SnapshotFrame,
    robot_ids: Sequence[str],
    *,
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
    grounding_params: GroundingParams | None,
) -> set[str]:
    # Lists the assigned legs first, in the given order, then every other
    # snapshot robot as `continue` -- the scene-wide shape the audit expects.
    known = [state.robot_id for state in snapshot.robots]
    order = [*assigned, *(rid for rid in known if rid not in assigned)]
    legs = [ProposedPlanLeg(robot_id=rid, action=assigned.get(rid, "continue")) for rid in order]
    problems = _plan_problems(
        legs,
        decision,
        snapshot,
        geometry,
        static_obstacles,
        yield_feasibility_mode,
        grounding_params,
    )
    flagged = {legs[index].robot_id for index, _ in problems}
    return flagged & set(robot_ids)


def derive_candidate_options(
    snapshot: SnapshotFrame,
    *,
    geometry: SceneGeometry | None = None,
    static_obstacles: Sequence[StaticObstacleInput] = (),
    yield_feasibility_mode: YieldFeasibilityMode = "off",
    grounding_params: GroundingParams | None = None,
) -> dict[str, list[tuple[PlanLegAction, str | None]]]:
    """Per-robot plan actions the verifier's own audit accepts in this scene.

    Never a hand-written option list: every (robot, action) pair is decided by
    running `_plan_problems` -- the exact leg audit `verify_and_repair_plan`
    applies -- on a probe plan, and offered iff the audit flags nothing on
    that robot's leg. The audit is strategy-conditioned (it takes a decision),
    so each action is probed under ONE registered context (open design item,
    `docs/reports/2026-10-04-visual-apparatus.md`):

    - `yield`: strategy `yield`, involved = [robot, nearest other robot],
      yield_robot = robot, legs [robot: yield, partner: cross] (room/obstacle
      gate per `yield_feasibility_mode`, corridor same-side refusal).
    - `reverse`: when the scene declares junction arms and the all-robot
      `junction_clear` recede set is non-empty, strategy `junction_clear`
      over every robot with legs [robot: reverse] (only structural recede
      candidates pass -- the axis-mirror recede set is never offered);
      otherwise strategy `reverse`, involved = [robot, nearest], both
      reversing (corridor same-side refusal).
    - `cross`: offered iff some other robot's yield probe, with this robot as
      its crosser, flags neither leg (the cross leg needs a releasing yield).
    - `wait`, `reroute`: strategies `temporary_wait` / `reroute` with
      [robot: wait|reroute, partner: wait]; the audit has no geometry check
      for either today, so both are offered whenever the probe passes.

    Args:
        snapshot: The scene the decision will be made on.
        geometry: Declared scene geometry; without it most checks are no-ops
            (same as the audit itself).
        static_obstacles: Fixed obstacles of the running scenario.
        yield_feasibility_mode: The yield feasibility gate mode the audit runs.
        grounding_params: M3's derived-mode params (chi weights).

    Returns:
        Robot id -> `(action, detail)` pairs in vocabulary order; `detail` is
        the declared arm (e.g. `"south arm"`) for a `reverse`, else None.
        Every snapshot robot is a key, possibly with an empty list.
    """
    audit = {
        "geometry": geometry,
        "static_obstacles": static_obstacles,
        "yield_feasibility_mode": yield_feasibility_mode,
        "grounding_params": grounding_params,
    }
    known = [state.robot_id for state in snapshot.robots]
    junction_context = (
        geometry is not None
        and bool(geometry.arms)
        and bool(_junction_recede_candidates(_probe_decision("junction_clear", known), geometry))
    )
    yield_ok: dict[tuple[str, str], tuple[bool, bool]] = {}
    for yielder in known:
        for crosser in known:
            if crosser == yielder:
                continue
            flagged = _probe_flags(
                _probe_decision("yield", [yielder, crosser], yielder),
                {yielder: "yield", crosser: "cross"},
                snapshot,
                [yielder, crosser],
                **audit,
            )
            yield_ok[(yielder, crosser)] = (yielder not in flagged, crosser not in flagged)

    options: dict[str, list[tuple[PlanLegAction, str | None]]] = {}
    for robot_id in known:
        partner = _nearest_partner(snapshot, robot_id)
        accepted: list[tuple[PlanLegAction, str | None]] = []
        for action in _CANDIDATE_OPTION_ACTIONS:
            detail: str | None = None
            if action == "yield":
                ok = partner is not None and yield_ok[(robot_id, partner)][0]
            elif action == "cross":
                ok = any(
                    both[0] and both[1]
                    for (yielder, crosser), both in yield_ok.items()
                    if crosser == robot_id
                )
            elif action == "reverse":
                if junction_context:
                    ok = robot_id not in _probe_flags(
                        _probe_decision("junction_clear", known),
                        {robot_id: "reverse"},
                        snapshot,
                        [robot_id],
                        **audit,
                    )
                else:
                    involved = [robot_id] if partner is None else [robot_id, partner]
                    ok = robot_id not in _probe_flags(
                        _probe_decision("reverse", involved),
                        dict.fromkeys(involved, "reverse"),
                        snapshot,
                        [robot_id],
                        **audit,
                    )
                arm = (geometry.arms or {}).get(robot_id) if geometry is not None else None
                if arm is not None:
                    detail = _ARM_NAMES.get((arm.axis, arm.side))
            else:
                strategy = "temporary_wait" if action == "wait" else "reroute"
                involved = [robot_id] if partner is None else [robot_id, partner]
                assigned: dict[str, PlanLegAction] = {robot_id: action}
                if partner is not None:
                    assigned[partner] = "wait"
                ok = robot_id not in _probe_flags(
                    _probe_decision(strategy, involved), assigned, snapshot, [robot_id], **audit
                )
            if ok:
                accepted.append((action, detail))
        options[robot_id] = accepted
    return options

"""Per-decision grounding view: parked-robot exclusion and dynamic arms (no ROS2).

Two default-off transforms run on a validated decision before M3 grounds it,
so every grounding consumer (the command, stage 2, the plan verifier and the
`junction_clear` phase queue) sees the same roles and the same geometry:

1. Parked-robot exclusion (v3 scene design S2). A robot declared in
   `SceneGeometry.parked_robots` that M2 names as involved in a spatial
   decision is dropped from `involved_robots`, `yield_robot` and
   `crossing_order` while it sits at its declared pose. It stays in the
   snapshot, so the prompt still shows it and chi still counts it as a
   follower (`maneuver_geometry.recede_follower_count`).
2. Dynamic arms and node handoff (v3 scene design S1 prerequisite 2), behind
   `GroundingParams.dynamic_scene_arms`, for `yield` and `reverse` only. In
   S1's task streams robots jam mid-route, where the declared single corridor
   says nothing about the conflict. The conflict geometry is derived from the
   decision snapshot instead (see `derive_dynamic_arms`). `junction_clear`
   stays on the declared geometry: its recede pockets and release lanes are
   declared junction constants (S2/S3 work, gated separately).

A third pass under the same switch, `apply_escort_headings`, runs on the
grounded command instead (prereg-v3 A11(iii)): every escorted passer is
driven toward its current goal, not along its spawn heading. Its sibling,
`apply_backup_line_hold`, marks every yield/reverse backup of the grounded
command so M4 holds the line through the backup's own start pose instead of
servoing toward the odom y=0 spawn line.

The view is resolved once per decision, at each public grounding entry point
(`ground_reasoner_result`, `ground_junction_clear_phases`,
`verify_and_repair_plan`, and M5's stage-2 call); internal calls ground the
already-resolved decision and never resolve it again, so no tag is emitted
twice. Every input is the same at each entry point (decision, snapshot,
declared geometry, params, goal references), so each resolves the same view.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import CongestionDecision, RobotStateInput, SnapshotFrame

_SPATIAL_STRATEGIES = frozenset({"yield", "reverse", "junction_clear"})
_DYNAMIC_STRATEGIES = frozenset({"yield", "reverse"})
# A heading counts as running along an axis within 30 degrees of it; a robot
# mid-turn in the junction box (e.g. 45 degrees) has no unambiguous lane.
_AXIS_SNAP_COS = math.cos(math.radians(30.0))
# Floor for the dynamic corridor's half-length: two robots reported at the
# same along-axis coordinate (M1 error on a nose-to-nose pair) must still give
# a valid corridor (`CorridorGeometry.half_length_m > 0`).
_MIN_HALF_LENGTH_M = 0.05

Axis = Literal["x", "y"]


class GroundingView(BaseModel):
    """The decision and geometry M3 grounds with, and the tags that record why."""

    model_config = ConfigDict(frozen=True)

    decision: CongestionDecision
    geometry: SceneGeometry | None
    # Provenance tags (`grounding=...`), appended to the grounded command's
    # `degradations`; empty when neither transform changed anything.
    tags: tuple[str, ...] = ()


def _rebuilt(decision: CongestionDecision, **update: Any) -> CongestionDecision:
    # Re-validated, never `model_copy(update=...)`: the yield_robot and
    # crossing_order invariants must hold on the rebuilt decision too.
    return CongestionDecision.model_validate({**decision.model_dump(), **update})


def _robot_order(decision: CongestionDecision) -> list[str]:
    # `command_grounder.resolve_robot_order`, restated: this module sits below
    # the grounder (it imports this one). Yielder first for a yield; the
    # model's own order otherwise.
    if (
        decision.strategy == "yield"
        and decision.yield_robot is not None
        and decision.yield_robot in decision.involved_robots
    ):
        rest = [rid for rid in decision.involved_robots if rid != decision.yield_robot]
        return [decision.yield_robot, *rest]
    return list(decision.involved_robots)


def exclude_parked_robots(
    decision: CongestionDecision,
    snapshot: SnapshotFrame | None,
    geometry: SceneGeometry | None,
) -> tuple[CongestionDecision, list[str]]:
    """Drop declared parked robots from a spatial decision's roles.

    Args:
        decision: A validated decision.
        snapshot: The decision snapshot; None treats every parked robot as
            untracked.
        geometry: Declared scene geometry carrying `parked_robots`.

    Returns:
        The (possibly rebuilt) decision and its tags:
        `grounding=parked_excluded:<id>` per excluded robot (suffixed
        `:untracked` when it is not in the snapshot),
        `grounding=parked_displaced:<id>` for a listed robot farther than
        `parked_pose_tolerance_m` from its pose (kept in the decision), and
        `grounding=parked_only:<ids>` when every involved robot is parked
        (nothing is excluded then: an empty decision cannot be grounded).
        Non-spatial strategies, and decisions naming no parked robot, come
        back unchanged with no tags.
    """
    parked = None if geometry is None else geometry.parked_robots
    if not parked or decision.strategy not in _SPATIAL_STRATEGIES:
        return decision, []
    assert geometry is not None
    excluded: list[str] = []
    tags: list[str] = []
    for robot_id in decision.involved_robots:
        pose = parked.get(robot_id)
        if pose is None:
            continue
        state = None if snapshot is None else snapshot.find_robot(robot_id)
        if state is None:
            excluded.append(robot_id)
            tags.append(f"grounding=parked_excluded:{robot_id}:untracked")
            continue
        if math.hypot(state.x - pose[0], state.y - pose[1]) > geometry.parked_pose_tolerance_m:
            tags.append(f"grounding=parked_displaced:{robot_id}")
            continue
        excluded.append(robot_id)
        tags.append(f"grounding=parked_excluded:{robot_id}")
    if not excluded:
        return decision, tags
    remaining = [rid for rid in decision.involved_robots if rid not in excluded]
    if not remaining:
        displaced = [tag for tag in tags if tag.startswith("grounding=parked_displaced:")]
        return decision, [*displaced, f"grounding=parked_only:{','.join(excluded)}"]
    crossing_order = (
        None
        if decision.crossing_order is None
        else [rid for rid in decision.crossing_order if rid not in excluded]
    )
    yield_robot = None if decision.yield_robot in excluded else decision.yield_robot
    rebuilt = _rebuilt(
        decision,
        involved_robots=remaining,
        crossing_order=crossing_order,
        yield_robot=yield_robot,
    )
    return rebuilt, tags


def _heading_axis(theta: float) -> Axis | None:
    if abs(math.cos(theta)) >= _AXIS_SNAP_COS:
        return "x"
    if abs(math.sin(theta)) >= _AXIS_SNAP_COS:
        return "y"
    return None


def _coord(state: RobotStateInput, axis: Axis) -> float:
    return state.x if axis == "x" else state.y


def _heading_component(state: RobotStateInput, axis: Axis) -> float:
    return math.cos(state.theta) if axis == "x" else math.sin(state.theta)


def _goal_reference(
    robot_id: str,
    snapshot: SnapshotFrame,
    goal_references: Mapping[str, tuple[float, float]] | None,
) -> tuple[float, float] | None:
    if goal_references is not None:
        return goal_references.get(robot_id)
    state = snapshot.find_robot(robot_id)
    return None if state is None else state.goal


def find_node_handoff(
    decision: CongestionDecision,
    snapshot: SnapshotFrame,
    radius_m: float,
    goal_references: Mapping[str, tuple[float, float]] | None = None,
) -> tuple[str, str] | None:
    """Find an involved robot arriving at a node another involved robot occupies.

    The goal reference is each robot's CURRENT task node: M5's base-mission
    registry goal (`goal_references`, from `TaskRegistry.mission_goal`), which
    a task-stream advance (`TaskRegistry.set_base`) updates even while a
    coordination override is active, so never a stale override goal and
    never the static `initial_tasks` goal. Without `goal_references` the
    snapshot's own goals are used. The occupant's own goal is not compared:
    right after its dwell ends its goal has already advanced, while it still
    sits on the node.

    Args:
        decision: A validated decision.
        snapshot: The decision snapshot.
        radius_m: Occupancy radius around a node.
        goal_references: Robot id -> current task node, or None.

    Returns:
        `(arriver, occupant)` for the first arriver in yielder-first order
        whose node holds another involved robot, or None. The occupant is
        the involved robot nearest the arriver's node, within `radius_m` of
        it and nearer to it than the arriver: a latched arriver stops ~0.45 m
        behind the occupant, often inside the same radius itself.
    """
    order = _robot_order(decision)
    for arriver in order:
        node = _goal_reference(arriver, snapshot, goal_references)
        state = snapshot.find_robot(arriver)
        if node is None or state is None:
            continue
        own = math.hypot(state.x - node[0], state.y - node[1])
        occupants = []
        for other in order:
            other_state = snapshot.find_robot(other)
            if other == arriver or other_state is None:
                continue
            distance = math.hypot(other_state.x - node[0], other_state.y - node[1])
            if distance <= radius_m and distance < own:
                occupants.append((distance, other))
        if occupants:
            return arriver, min(occupants)[1]
    return None


def _with_yielder(
    decision: CongestionDecision, yielder: str, first_passer: str
) -> CongestionDecision:
    # The yielder first and the first passer right behind it in the involved
    # order; a model crossing order keeps its relative order for the rest.
    rest = [rid for rid in decision.involved_robots if rid not in (yielder, first_passer)]
    crossing_order = None
    if decision.crossing_order is not None:
        tail = [rid for rid in decision.crossing_order if rid not in (yielder, first_passer)]
        crossing_order = [first_passer, *tail, yielder]
    return _rebuilt(
        decision,
        involved_robots=[yielder, first_passer, *rest],
        yield_robot=yielder,
        crossing_order=crossing_order,
    )


def _apply_node_handoff(
    decision: CongestionDecision,
    handoff: tuple[str, str],
) -> tuple[CongestionDecision, list[str]]:
    arriver, occupant = handoff
    tags = [f"grounding=node_handoff:{arriver}->{occupant}"]
    if decision.strategy == "reverse":
        # The occupant is the exempt passer: only the robots that are not on
        # the node back away from it.
        remaining = [rid for rid in decision.involved_robots if rid != occupant]
        crossing_order = (
            None
            if decision.crossing_order is None
            else [rid for rid in decision.crossing_order if rid != occupant]
        )
        yield_robot = None if decision.yield_robot == occupant else decision.yield_robot
        rebuilt = _rebuilt(
            decision,
            involved_robots=remaining,
            crossing_order=crossing_order,
            yield_robot=yield_robot,
        )
        return rebuilt, tags
    named = _robot_order(decision)[0]
    if named != arriver:
        tags.append(f"grounding=node_handoff_regrounded:{named}->{arriver}")
    return _with_yielder(decision, arriver, occupant), tags


def _nearest_other(snapshot: SnapshotFrame, anchor: str, candidates: list[str]) -> str | None:
    anchor_state = snapshot.find_robot(anchor)
    if anchor_state is None:
        return None
    best: tuple[float, int, str] | None = None
    for index, robot_id in enumerate(candidates):
        state = snapshot.find_robot(robot_id)
        if robot_id == anchor or state is None:
            continue
        key = (math.hypot(state.x - anchor_state.x, state.y - anchor_state.y), index, robot_id)
        if best is None or key < best:
            best = key
    return None if best is None else best[2]


def _lane_geometry(
    declared: SceneGeometry, axis: Axis, anchor: RobotStateInput, partner: RobotStateInput
) -> SceneGeometry:
    a = _coord(anchor, axis)
    p = _coord(partner, axis)
    corridor = CorridorGeometry(
        axis=axis,
        center_m=round((a + p) / 2.0, 3),
        half_length_m=max(round(abs(a - p) / 2.0, 3), _MIN_HALF_LENGTH_M),
        # The lane is the declared aisle's width; a mid-route conflict
        # segment has no barrier between the two robots.
        aisle_half_width_m=declared.corridor.aisle_half_width_m,
        occluder_height_m=0.0,
    )
    # No arms: the passer-relative side rule then retreats each robot away
    # from its partner. Every centre-relative junction field (J2, recede
    # pockets, release pull-off, tracked extent) is measured from the
    # declared junction centre, not from this conflict's midpoint, so none is
    # carried over. Rear room is checked across the footprint and the yield
    # gate scores only this pair (`SceneGeometry.rear_room_band`,
    # `SceneGeometry.lane_robots`).
    return SceneGeometry(
        rear_room_band="footprint",
        lane_robots=(anchor.robot_id, partner.robot_id),
        corridor=corridor,
        camera=declared.camera,
        robot=declared.robot,
        park_margin_m=declared.park_margin_m,
        wall_margin_m=declared.wall_margin_m,
        passer_margin_m=declared.passer_margin_m,
        reroute_waypoints=declared.reroute_waypoints,
        parked_robots=declared.parked_robots,
        parked_pose_tolerance_m=declared.parked_pose_tolerance_m,
    )


def _crossing_geometry(
    declared: SceneGeometry,
    bearing_axis: Axis,
    snapshot: SnapshotFrame,
    robot_ids: list[str],
) -> SceneGeometry:
    arms: dict[str, dict[str, Any]] = {}
    for robot_id in robot_ids:
        state = snapshot.find_robot(robot_id)
        axis = None if state is None else _heading_axis(state.theta)
        if state is None or axis is None:
            continue
        # The arm a robot approached on is behind it: its outward side is
        # opposite its heading, exactly the declared-arm convention.
        side = -1 if _heading_component(state, axis) > 0.0 else 1
        arms[robot_id] = {"axis": axis, "side": side}
    data = declared.model_dump()
    data["arms"] = arms
    data["corridor"] = {**data["corridor"], "axis": bearing_axis}
    # The racks flanking each arm start at the box edge, which is every arm's
    # mouth: rear room is checked across the footprint, not the aisle
    # (`SceneGeometry.rear_room_band`).
    data["rear_room_band"] = "footprint"
    return SceneGeometry.model_validate(data)


def _rear_consistent(yielder: RobotStateInput, partner: RobotStateInput, axis: Axis) -> bool:
    # M4 executes a yield's backup along the robot's own -heading; the
    # passer-relative side rule retreats it away from the partner. The two
    # agree only when the yielder faces its partner.
    side = -1.0 if _coord(yielder, axis) < _coord(partner, axis) else 1.0
    return -_heading_component(yielder, axis) * side > 0.0


def _exempt_rear_blocked_reversers(
    decision: CongestionDecision, snapshot: SnapshotFrame, axis: Axis
) -> tuple[CongestionDecision, list[str]]:
    # A lane `reverse` backs every involved robot up along its own -heading.
    # A robot facing away from its nearest involved robot would back into it
    # (the front robot of a same-direction pair): it is left out of the
    # reversing set instead, unless that would leave nobody to reverse.
    order = list(decision.involved_robots)
    exempt = []
    for robot_id in order:
        state = snapshot.find_robot(robot_id)
        partner_id = _nearest_other(snapshot, robot_id, order)
        partner = None if partner_id is None else snapshot.find_robot(partner_id)
        if state is not None and partner is not None and not _rear_consistent(state, partner, axis):
            exempt.append(robot_id)
    if not exempt:
        return decision, []
    if len(exempt) == len(order):
        return decision, [f"grounding=dynamic_arms:rear_inconsistent:{','.join(exempt)}"]
    remaining = [rid for rid in order if rid not in exempt]
    crossing_order = (
        None
        if decision.crossing_order is None
        else [rid for rid in decision.crossing_order if rid not in exempt]
    )
    yield_robot = None if decision.yield_robot in exempt else decision.yield_robot
    rebuilt = _rebuilt(
        decision, involved_robots=remaining, crossing_order=crossing_order, yield_robot=yield_robot
    )
    return rebuilt, [f"grounding=rear_exempt:{rid}" for rid in exempt]


def derive_dynamic_arms(
    decision: CongestionDecision,
    snapshot: SnapshotFrame | None,
    geometry: SceneGeometry | None,
    params: GroundingParams | None,
    goal_references: Mapping[str, tuple[float, float]] | None = None,
) -> tuple[CongestionDecision, SceneGeometry | None, list[str]]:
    """Derive a yield/reverse decision's conflict geometry from its snapshot.

    Rules, in order (v3 scene design S1 prerequisite 2):

    1. Node handoff: an involved robot arriving at its current task node
       (`find_node_handoff`) while another involved robot occupies it. The
       arriver yields and the occupant is the exempt passer, whoever M2
       named; a `reverse` drops the occupant from the reversing set.
    2. The conflicting pair is the yielder (or, for `reverse`, the first
       involved robot) and the occupant of rule 1, else its nearest involved
       robot. The pair's relative bearing fixes the bearing axis (`x` when
       `|dx| >= |dy|`); each robot's heading fixes its lane axis when it is
       within 30 degrees of an axis.
    3. Lane conflict (both lanes equal the bearing axis: head-on, follower
       or handoff on one arm): a corridor along that axis centred on the
       pair's midpoint, half-length half their separation, the declared
       aisle width, no occluder and no arms. The existing passer-relative
       side rule then retreats the yielder away from its partner, its park
       target is `park_offset_m` from that midpoint, and the declared
       static obstacles bound its rear room (`yield_retreat_room_m`)
       across its own swept footprint, not the aisle width, with only the
       pair scored by the yield gate (`SceneGeometry.rear_room_band`,
       `SceneGeometry.lane_robots`). M4 backs a yielder up along its own
       -heading, so a yielder facing away from its partner (it would back
       into the partner) is swapped with the partner when the partner faces
       it; a `reverse` leaves such a robot out of the reversing set
       (`grounding=rear_exempt:<id>`).
    4. Crossing conflict (the two lanes differ, e.g. W lane against S arm):
       the declared corridor centre and box, with an arm per involved robot
       from its own heading (outward side = behind it, the declared-arm
       convention) and the corridor axis set to the bearing axis. Rear
       room is checked across the footprint here too.
    5. Anything else (a robot missing from the snapshot, a heading between
       axes, matching lanes across the bearing) keeps the declared
       geometry, tagged.

    Args:
        decision: A validated decision.
        snapshot: The decision snapshot.
        geometry: Declared scene geometry (camera, robot, aisle width and
            margins are always taken from it).
        params: Grounding parameters; the switch and the handoff radius.
        goal_references: Robot id -> current task node, from M5's registry.

    Returns:
        The (possibly re-roled) decision, the geometry to ground with, and
        the `grounding=...` tags. Unchanged with no tags when the switch is
        off, the strategy is not `yield`/`reverse`, or `geometry` or
        `snapshot` is None.
    """
    if (
        params is None
        or not params.dynamic_scene_arms
        or decision.strategy not in _DYNAMIC_STRATEGIES
        or geometry is None
        or snapshot is None
    ):
        return decision, geometry, []
    tags: list[str] = []
    handoff = find_node_handoff(
        decision, snapshot, params.dynamic_handoff_radius_m, goal_references
    )
    if handoff is not None:
        decision, handoff_tags = _apply_node_handoff(decision, handoff)
        tags.extend(handoff_tags)
    order = _robot_order(decision)
    anchor_id = order[0]
    partner_id = (
        handoff[1]
        if handoff is not None and decision.strategy == "yield"
        else _nearest_other(snapshot, anchor_id, order)
    )
    anchor = snapshot.find_robot(anchor_id)
    partner = None if partner_id is None else snapshot.find_robot(partner_id)
    if anchor is None or partner is None:
        if handoff is not None and decision.strategy == "reverse" and anchor is not None:
            # A handoff reverse left only the arriver: it backs away along its
            # own heading, which needs no corridor.
            return decision, geometry, tags
        return decision, geometry, [*tags, "grounding=dynamic_arms:unavailable"]
    dx = partner.x - anchor.x
    dy = partner.y - anchor.y
    bearing_axis: Axis = "x" if abs(dx) >= abs(dy) else "y"
    anchor_axis = _heading_axis(anchor.theta)
    partner_axis = _heading_axis(partner.theta)
    if anchor_axis is None or partner_axis is None:
        return decision, geometry, [*tags, "grounding=dynamic_arms:ambiguous"]
    if anchor_axis != partner_axis:
        crossing = _crossing_geometry(geometry, bearing_axis, snapshot, order)
        return decision, crossing, [*tags, "grounding=dynamic_arms:crossing"]
    if anchor_axis != bearing_axis:
        return decision, geometry, [*tags, "grounding=dynamic_arms:ambiguous"]
    if decision.strategy == "reverse":
        decision, rear_tags = _exempt_rear_blocked_reversers(decision, snapshot, bearing_axis)
        tags.extend(rear_tags)
    elif not _rear_consistent(anchor, partner, bearing_axis):
        if handoff is None and _rear_consistent(partner, anchor, bearing_axis):
            decision = _with_yielder(decision, partner_id, anchor_id)
            tags.append(f"grounding=rear_regrounded:{anchor_id}->{partner_id}")
            anchor, partner = partner, anchor
        else:
            tags.append(f"grounding=dynamic_arms:rear_inconsistent:{anchor_id}")
    lane = _lane_geometry(geometry, bearing_axis, anchor, partner)
    return decision, lane, [*tags, f"grounding=dynamic_arms:lane:{bearing_axis}"]


def resolve_grounding_view(
    decision: CongestionDecision,
    snapshot: SnapshotFrame | None,
    geometry: SceneGeometry | None,
    params: GroundingParams | None = None,
    goal_references: Mapping[str, tuple[float, float]] | None = None,
) -> GroundingView:
    """Apply parked-robot exclusion, then dynamic arms, to one decision.

    Args:
        decision: A validated decision (after any strategy alias).
        snapshot: The decision snapshot.
        geometry: Declared scene geometry.
        params: Grounding parameters (the dynamic-arms switch).
        goal_references: Robot id -> current task node, from M5's registry.

    Returns:
        The view; `decision` and `geometry` are the inputs themselves, with
        no tags, when neither transform applies.
    """
    excluded, tags = exclude_parked_robots(decision, snapshot, geometry)
    dynamic, dynamic_geometry, dynamic_tags = derive_dynamic_arms(
        excluded, snapshot, geometry, params, goal_references
    )
    return GroundingView(
        decision=dynamic, geometry=dynamic_geometry, tags=(*tags, *dynamic_tags)
    )


class EscortHeading(BaseModel):
    """One escorted passer's world-frame drive heading, or why it has none."""

    model_config = ConfigDict(frozen=True)

    # World-frame heading in radians (0, pi/2, pi or -pi/2: the escort axis
    # toward the goal), None when not derivable.
    heading_rad: float | None = None
    # The passer's world-frame heading in the decision snapshot. M4 drives in
    # the robot's own odom frame, whose yaw 0 is the SPAWN heading; turning
    # by `heading_rad - reference_yaw_rad` from its odom yaw at admission
    # needs no map-frame knowledge in M4.
    reference_yaw_rad: float | None = None
    # The passer's distance to its turn: the along-axis distance from its
    # snapshot position to its goal's coordinate on the escort axis. Routes
    # run node -> arm mouth -> junction centre -> arm mouth -> node, so a goal
    # off this axis is reached by leaving it at the goal's own coordinate on
    # it (0 for N/S/E, the junction centre). None with the heading.
    distance_to_turn_m: float | None = None
    reason: str | None = None


# A goal component along the escort axis below this is no direction: the goal
# sits straight across the lane (a robot about to turn into another arm).
_ESCORT_AXIS_MIN_M = 0.05


def derive_escort_heading(
    passer_id: str,
    yielder_id: str,
    snapshot: SnapshotFrame | None,
    geometry: SceneGeometry | None,
    params: GroundingParams,
    goal_references: Mapping[str, tuple[float, float]] | None = None,
) -> EscortHeading:
    """Derive the direction M4 escorts a passer in, from its current goal.

    prereg-v3 A11(iii): M4's escort assumed every robot spawned facing its
    goal (odom yaw 0); in S1 task streams the passer's goal is a different
    node every leg. The escort axis is the one its distance was measured on
    (`scene_geometry.passer_travel_m`): the passer's own arm axis when it is
    on a crossing arm, else the yielder's axis. The goal's component along
    that axis picks the sign. It must agree with the direction the distance
    assumed (past the parked yielder, or ahead out of the box for a crossing
    passer), or the escort leg would be the wrong length.

    Args:
        passer_id: The escorted robot.
        yielder_id: The yield's yielder.
        snapshot: The decision snapshot.
        geometry: The geometry the command was grounded on (the dynamic view
            when it fired).
        params: Grounding parameters; `dynamic_handoff_radius_m` is the
            radius inside which the passer counts as at its goal.
        goal_references: Robot id -> current task node (M5's registry), or
            None to use the snapshot's goals.

    Returns:
        The heading and the passer's snapshot heading, or a `reason`:
        `untracked` (passer or yielder not in the snapshot, or no geometry),
        `no_goal`, `goal_reached` (within `dynamic_handoff_radius_m`: a
        dwelling occupant), `goal_off_axis` (no along-axis component), or
        `goal_behind` (the goal lies opposite the direction the escort
        distance was measured in).
    """
    passer = None if snapshot is None else snapshot.find_robot(passer_id)
    yielder = None if snapshot is None else snapshot.find_robot(yielder_id)
    if passer is None or yielder is None or geometry is None or snapshot is None:
        return EscortHeading(reason="untracked")
    goal = _goal_reference(passer_id, snapshot, goal_references)
    if goal is None:
        return EscortHeading(reason="no_goal")
    if math.hypot(goal[0] - passer.x, goal[1] - passer.y) <= params.dynamic_handoff_radius_m:
        return EscortHeading(reason="goal_reached")
    yielder_arm = (geometry.arms or {}).get(yielder_id)
    yielder_axis: Axis = geometry.corridor.axis if yielder_arm is None else yielder_arm.axis
    passer_arm = (geometry.arms or {}).get(passer_id)
    if passer_arm is None or passer_arm.axis == yielder_axis:
        axis = yielder_axis
        expected = 1.0 if _coord(yielder, axis) > _coord(passer, axis) else -1.0
    else:
        axis = passer_arm.axis
        expected = -float(passer_arm.side)
    along = (goal[0] - passer.x) if axis == "x" else (goal[1] - passer.y)
    if abs(along) < _ESCORT_AXIS_MIN_M:
        return EscortHeading(reason="goal_off_axis")
    if along * expected < 0.0:
        return EscortHeading(reason="goal_behind")
    if axis == "x":
        heading = 0.0 if along > 0.0 else math.pi
    else:
        heading = math.pi / 2 if along > 0.0 else -math.pi / 2
    return EscortHeading(
        heading_rad=round(heading, 6),
        reference_yaw_rad=round(passer.theta, 6),
        distance_to_turn_m=round(abs(along), 3),
    )


def _escorted_passers(parameters: Mapping[str, Any]) -> list[str]:
    # M4's `crossing_chain.plan_crossing`, restated (M3 must not import M4):
    # the first passer is escorted when the escort distance is present, and
    # every later one of a valid `crossing_order` with it.
    first = parameters.get("passer_robot_id")
    if not first or parameters.get("passer_escort_distance_m") is None:
        return []
    order = parameters.get("crossing_order")
    if (
        isinstance(order, list)
        and len(order) >= 2
        and all(isinstance(robot_id, str) and robot_id for robot_id in order)
        and len(set(order)) == len(order)
        and order[0] == first
    ):
        return list(order)
    return [str(first)]


def _capped(value: Any, cap: float | None) -> Any:
    if cap is None or not isinstance(value, int | float) or value <= cap:
        return value
    return cap


def _cap_escorts_at_turn(
    parameters: dict[str, Any], passers: list[str], headings: list[EscortHeading]
) -> tuple[dict[str, Any], list[str]]:
    # Escort and clearance are capped together: M4 holds an escorted passer
    # under its linked wait until it has moved `clear_m`, so an escort that
    # stopped short of an uncapped clearance would leave it parked until the
    # hold backstop (`crossing_chain.CrossingChain`).
    capped = dict(parameters)
    tags: list[str] = []
    first_cap = headings[0].distance_to_turn_m
    for key in ("passer_escort_distance_m", "passer_clear_m"):
        if key in capped:
            capped[key] = _capped(capped[key], first_cap)
    for key in ("crossing_escort_m", "crossing_clear_m"):
        values = capped.get(key)
        if isinstance(values, list) and len(values) == len(headings):
            capped[key] = [
                _capped(value, heading.distance_to_turn_m)
                for value, heading in zip(values, headings, strict=True)
            ]
    for position, passer_id in enumerate(passers):
        before = (
            parameters.get("passer_escort_distance_m")
            if position == 0
            else (parameters.get("crossing_escort_m") or [None] * len(passers))[position]
        )
        after = (
            capped.get("passer_escort_distance_m")
            if position == 0
            else (capped.get("crossing_escort_m") or [None] * len(passers))[position]
        )
        if before is not None and after != before:
            tags.append(f"grounding=escort_turn_cap:{passer_id}:{before}->{after}")
    return capped, tags


def apply_escort_headings(
    command: dict[str, Any],
    snapshot: SnapshotFrame | None,
    geometry: SceneGeometry | None,
    params: GroundingParams | None,
    goal_references: Mapping[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Give every escorted passer of a grounded command its goal-bearing heading.

    Runs only with `params.dynamic_scene_arms` (prereg-v3 A11(iii)); with the
    switch off the command comes back as the same object, so every flags-off
    artifact keeps its bytes and M4 keeps driving odom yaw 0. With it on,
    each `yield` that grounds an escort gains `passer_escort_heading_rad` and
    `passer_escort_reference_yaw_rad` (plus `crossing_escort_heading_rad` /
    `crossing_escort_reference_yaw_rad`, aligned with `crossing_order`, for
    two or more passers). When any escorted passer's heading cannot be
    derived (`derive_escort_heading`), that yield's escort is dropped
    (`passer_escort_distance_m` and `crossing_escort_m` removed): M4 then
    releases each passer to Nav2 at its admission, the path a yield with no
    escort already takes, and the clearance gate is unchanged. Tagged
    `grounding=escort_off:<passer>:<reason>`. With `params.escort_turn_cap`
    also on, each passer's escort and clearance distances are capped at its
    `EscortHeading.distance_to_turn_m`, tagged
    `grounding=escort_turn_cap:<passer>:<before>-><after>` when the cap bites.

    Args:
        command: A grounded coordination command.
        snapshot: The decision snapshot.
        geometry: The geometry the command was grounded on.
        params: Grounding parameters (the switch).
        goal_references: Robot id -> current task node, or None.

    Returns:
        The command, with headings or with its escorts dropped.
    """
    if params is None or not params.dynamic_scene_arms:
        return command
    tags: list[str] = []
    actions: list[dict[str, Any]] = []
    for action in command.get("actions", []):
        parameters = action.get("parameters") or {}
        passers = _escorted_passers(parameters) if action.get("action") == "yield" else []
        if not passers:
            actions.append(action)
            continue
        headings = [
            derive_escort_heading(
                passer_id, action["robot_id"], snapshot, geometry, params, goal_references
            )
            for passer_id in passers
        ]
        failed = [(p, h.reason) for p, h in zip(passers, headings, strict=True) if h.reason]
        if failed:
            parameters = {
                key: value
                for key, value in parameters.items()
                if key not in ("passer_escort_distance_m", "crossing_escort_m")
            }
            tags.extend(f"grounding=escort_off:{p}:{reason}" for p, reason in failed)
        else:
            parameters = {
                **parameters,
                "passer_escort_heading_rad": headings[0].heading_rad,
                "passer_escort_reference_yaw_rad": headings[0].reference_yaw_rad,
            }
            if len(passers) > 1:
                parameters["crossing_escort_heading_rad"] = [h.heading_rad for h in headings]
                parameters["crossing_escort_reference_yaw_rad"] = [
                    h.reference_yaw_rad for h in headings
                ]
            if params.escort_turn_cap:
                parameters, cap_tags = _cap_escorts_at_turn(parameters, passers, headings)
                tags.extend(cap_tags)
        actions.append({**action, "parameters": parameters})
    updated = {**command, "actions": actions}
    if tags:
        updated["degradations"] = [*command.get("degradations", []), *tags]
    return updated


def apply_backup_line_hold(
    command: dict[str, Any],
    params: GroundingParams | None,
) -> dict[str, Any]:
    """Mark every yield/reverse backup of a grounded command for line hold.

    The spawn-frame sibling of `apply_escort_headings` (prereg-v3 A11(iii)):
    M4's `backup` servos the reversing robot toward the odom y=0 spawn line,
    which assumes it still faces its spawn heading. In S1 task streams a
    yielder off that heading backs along an ~0.2 m-radius arc instead of a
    straight line. Under `params.dynamic_scene_arms` every `yield` and
    `reverse` action gains `backup_line_hold: true`; M4 then holds the line
    through the robot's own backup start pose along its start heading, in
    the robot's odom frame — no world yaw crosses the M3/M4 boundary. With
    the switch off the command comes back as the same object, so every
    flags-off artifact keeps its bytes and M4 keeps the spawn-line servo.

    Args:
        command: A grounded coordination command.
        params: Grounding parameters (the switch).

    Returns:
        The command, with its backup actions marked.
    """
    if params is None or not params.dynamic_scene_arms:
        return command
    actions = [
        {**action, "parameters": {**(action.get("parameters") or {}), "backup_line_hold": True}}
        if action.get("action") in ("yield", "reverse")
        else action
        for action in command.get("actions", [])
    ]
    if actions == list(command.get("actions", [])):
        return command
    return {**command, "actions": actions}

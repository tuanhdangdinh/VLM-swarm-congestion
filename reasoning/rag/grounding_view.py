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
from typing import Any, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict

from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import (
    CorridorGeometry,
    JunctionBox,
    SceneGeometry,
    along_m,
    junction_box_for,
)
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
    # Set (opening with "yield refused:") when the dynamic view found no lane
    # it can ground a yield on (`derive_dynamic_arms`): every consumer then
    # refuses the yield instead of grounding it on `geometry`, the declared
    # fallback, whose corridor mouths say nothing about this conflict.
    refusal_reason: str | None = None


class DynamicArms(NamedTuple):
    """`derive_dynamic_arms`' result: roles, geometry, tags, and any refusal."""

    decision: CongestionDecision
    geometry: SceneGeometry | None
    tags: list[str]
    refusal_reason: str | None = None


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


def _axis_offset_deg(theta: float) -> int:
    # Degrees off the nearest world axis, 0..45.
    folded = math.degrees(math.atan2(abs(math.sin(theta)), abs(math.cos(theta))))
    return round(min(folded, 90.0 - folded))


def backup_follows_retreat(state: RobotStateInput, retreat: tuple[float, float]) -> bool:
    """Whether M4's backup of a robot runs along a retreat direction.

    M4 backs a yielder up along its own -heading (`backup_line_hold`), while
    M3 sweeps its retreat along an axis. The two describe the same motion
    only when the robot faces away from `retreat` within the 30 degree axis
    snap the dynamic view classifies lanes with: the lane rule's facing
    requirement (`_rear_consistent`) and its snap in one test.

    Args:
        state: The robot that would back up.
        retreat: Unit retreat direction `(x, y)` in the world frame.

    Returns:
        True when the robot's -heading is within 30 degrees of `retreat`.
    """
    backing = (-math.cos(state.theta), -math.sin(state.theta))
    return backing[0] * retreat[0] + backing[1] * retreat[1] >= _AXIS_SNAP_COS


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
    box: JunctionBox | None = None,
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
    if box is not None:
        # A20(1): the declared box this conflict sits in, measured per axis.
        data["corridor"]["center_m"] = box.center_m(bearing_axis)
        data["corridor"]["half_length_m"] = box.half_length_m(bearing_axis)
        data["junction_box"] = box.model_dump()
    # The racks flanking each arm start at the box edge, which is every arm's
    # mouth: rear room is checked across the footprint, not the aisle
    # (`SceneGeometry.rear_room_band`).
    data["rear_room_band"] = "footprint"
    return SceneGeometry.model_validate(data)


# A20(2): an ambiguous handoff arriver's heading must stay within 45 degrees
# of the conflict's bearing axis (that axis is its nearest one) for a backup
# along the heading to open the pair along the bearing; beyond that it backs
# mostly sideways and the yield is refused.
_HEADING_LANE_CAP_COS = math.cos(math.radians(45.0))


def _heading_lane_within_cap(arriver: RobotStateInput, bearing_axis: Axis) -> bool:
    return abs(_heading_component(arriver, bearing_axis)) >= _HEADING_LANE_CAP_COS - 1e-12


def _heading_lane_applies(
    arriver: RobotStateInput, occupant: RobotStateInput, bearing_axis: Axis
) -> bool:
    # The cap above, and the lane rule's facing requirement: the arriver
    # faces the occupant, so -heading points away from it.
    return _heading_lane_within_cap(arriver, bearing_axis) and (
        _rear_consistent(arriver, occupant, bearing_axis)
    )


def _heading_lane_cap_blocker(arriver: RobotStateInput, bearing_axis: Axis) -> str:
    # A21: name the cap when it is what refused (pilot 2, E4: the text named
    # rule 5's blocker while the 45 deg cap held the refusal).
    component = min(1.0, abs(_heading_component(arriver, bearing_axis)))
    off = round(math.degrees(math.acos(component)))
    return (
        f"{arriver.robot_id} is the node-handoff arriver, but it heads {off} deg off the "
        f"pair's {bearing_axis} bearing (beyond the 45 deg heading-lane cap)"
    )


def _heading_lane_geometry(
    declared: SceneGeometry, bearing_axis: Axis, arriver: RobotStateInput, occupant: RobotStateInput
) -> SceneGeometry:
    # Rule 3's lane, laid along the arriver's own heading instead of the
    # bearing axis (A20(2)): `center_m` / `half_length_m` are measured along
    # the heading (`scene_geometry.along_m`), so the passer-relative side
    # rule, the room gate, the park floor and the retreat sweep all run along
    # the line M4 backs the arriver on. `corridor.axis` keeps the bearing
    # axis (the heading's nearest) for the axis-only consumers.
    heading = round(arriver.theta, 6)
    base = _lane_geometry(declared, bearing_axis, arriver, occupant)
    lane = base.model_copy(update={"lane_heading_rad": heading})
    a = along_m(lane, (arriver.x, arriver.y))
    p = along_m(lane, (occupant.x, occupant.y))
    corridor = base.corridor.model_copy(
        update={
            "center_m": round((a + p) / 2.0, 3),
            "half_length_m": max(round(abs(a - p) / 2.0, 3), _MIN_HALF_LENGTH_M),
        }
    )
    return lane.model_copy(update={"corridor": corridor})


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
) -> DynamicArms:
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
       room is checked across the footprint here too. Only where the scene
       declares that box a junction (`SceneGeometry.junction_declared`,
       prereg-v3 A16(iii)). A floor that declares its own crossing boxes
       (`SceneGeometry.junction_boxes`, A20(1)) anchors to the box both
       robots' footprints overlap instead, measured per axis
       (`grounding=dynamic_arms:junction_box:<name>`), and to no other box.
       Otherwise a yield is refused honestly
       (`grounding=dynamic_arms:crossing_refused:<a>,<b>`, no room
       measured) and a `reverse` keeps the declared geometry, tagged
       `grounding=dynamic_arms:crossing_undeclared`.
    5. Bearing-axis fallback (`yield` only, prereg-v3 A14(iii)/A15(iv)): a
       robot whose heading is more than 30 degrees off both axes takes the
       pair's bearing axis as its lane when its partner's lane IS the
       bearing axis, but only as the passer, since M4 would back it up
       along its diagonal heading, not the swept axis. An ambiguous
       partner is tagged `grounding=dynamic_arms:bearing_lane:<id>:<deg>`
       and rule 3 runs. An ambiguous yielder also hands the yield to its
       partner when the partner faces it and rule 1 did not fix the yielder
       (`grounding=heading_regrounded:<from>-><to>`).
    5b. Heading lane (`yield` only, derived mode, prereg-v3 A20(2)): an
       ambiguous node-handoff ARRIVER (rule 1 fixed it as the yielder, so
       rule 5 cannot hand the yield over) yields along its own heading, the
       line M4 backs it on. The lane is rule 3's, laid along the heading
       (`SceneGeometry.lane_heading_rad`); the room gate, park floor,
       footprint sweep with its box margins and the aisle bands all run
       along it. Capped: the heading must lie within 45 degrees of the
       pair's bearing axis and the arriver must face the occupant, else the
       rule-6 refusal stands. Tagged
       `grounding=dynamic_arms:heading_lane:<id>:<deg>` (degrees off the
       nearest axis). The occupant's snapped lane does not matter (it
       passes); both robots ambiguous stays a rule-6 refusal.
    6. Honest refusal (`yield` only): anything rule 5 cannot place (both
       headings ambiguous, the snapped lane across the bearing, an
       ambiguous handoff arriver, a partner facing away) and matching lanes
       across the bearing (two robots side by side on parallel lanes) have
       no lane to ground a yield on. The declared fallback's corridor
       mouths sit on rack faces and would report a fabricated ~0.00 m room,
       so the yield is refused with its true reason instead
       (`refusal_reason`, tagged
       `grounding=dynamic_arms:ambiguous_refused:<id>:<deg>` per ambiguous
       robot or `grounding=dynamic_arms:parallel_refused:<a>,<b>:<deg>`),
       and no room is measured. A `reverse` keeps the declared geometry,
       tagged `grounding=dynamic_arms:ambiguous`, as before.
    7. A robot missing from the snapshot keeps the declared geometry,
       tagged `grounding=dynamic_arms:unavailable`.

    Args:
        decision: A validated decision.
        snapshot: The decision snapshot.
        geometry: Declared scene geometry (camera, robot, aisle width and
            margins are always taken from it).
        params: Grounding parameters; the switch and the handoff radius.
        goal_references: Robot id -> current task node, from M5's registry.

    Returns:
        The (possibly re-roled) decision, the geometry to ground with, the
        `grounding=...` tags and, under rule 6, the refusal reason (the
        geometry is then the declared one and must not be grounded on).
        Unchanged with no tags when the switch is off, the strategy is not
        `yield`/`reverse`, or `geometry` or `snapshot` is None.
    """
    if (
        params is None
        or not params.dynamic_scene_arms
        or decision.strategy not in _DYNAMIC_STRATEGIES
        or geometry is None
        or snapshot is None
    ):
        return DynamicArms(decision, geometry, [])
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
            return DynamicArms(decision, geometry, tags)
        return DynamicArms(decision, geometry, [*tags, "grounding=dynamic_arms:unavailable"])
    dx = partner.x - anchor.x
    dy = partner.y - anchor.y
    bearing_axis: Axis = "x" if abs(dx) >= abs(dy) else "y"
    anchor_axis = _heading_axis(anchor.theta)
    partner_axis = _heading_axis(partner.theta)
    # Set when rule 5 lent the partner the bearing axis: it may pass, never
    # yield, so rule 3's rear swap must not hand it the yield.
    partner_lent = False
    if decision.strategy == "yield" and (anchor_axis is None) != (partner_axis is None):
        ambiguous = anchor if anchor_axis is None else partner
        if partner_axis is None and anchor_axis == bearing_axis:
            tags.append(
                f"grounding=dynamic_arms:bearing_lane:{partner.robot_id}:"
                f"{_axis_offset_deg(partner.theta)}"
            )
            partner_axis = bearing_axis
            partner_lent = True
        elif (
            anchor_axis is None
            and partner_axis == bearing_axis
            and handoff is None
            and _rear_consistent(partner, anchor, bearing_axis)
        ):
            decision = _with_yielder(decision, partner.robot_id, anchor.robot_id)
            tags.append(
                f"grounding=dynamic_arms:bearing_lane:{anchor.robot_id}:"
                f"{_axis_offset_deg(anchor.theta)}"
            )
            tags.append(f"grounding=heading_regrounded:{anchor.robot_id}->{partner.robot_id}")
            anchor, partner = partner, anchor
            anchor_axis = bearing_axis
        elif (
            ambiguous is anchor
            and handoff is not None
            and params.mode == "derived"
            and _heading_lane_applies(anchor, partner, bearing_axis)
        ):
            # Rule 5b (A20(2)): the ambiguous node-handoff arriver yields
            # along its own heading.
            lane = _heading_lane_geometry(geometry, bearing_axis, anchor, partner)
            return DynamicArms(
                decision,
                _with_handoff_occupant(lane, decision, handoff),
                [
                    *tags,
                    f"grounding=dynamic_arms:heading_lane:{anchor.robot_id}:"
                    f"{_axis_offset_deg(anchor.theta)}",
                ],
            )
        else:
            snapped = partner if ambiguous is anchor else anchor
            cap_refused = (
                ambiguous is anchor
                and handoff is not None
                and params.mode == "derived"
                and not _heading_lane_within_cap(anchor, bearing_axis)
            )
            return _ambiguous_refusal(
                decision,
                geometry,
                tags,
                [ambiguous],
                _heading_lane_cap_blocker(anchor, bearing_axis)
                if cap_refused
                else _fallback_blocker(anchor, partner, snapped, ambiguous, bearing_axis, handoff),
            )
    if anchor_axis is None or partner_axis is None:
        if decision.strategy == "yield":
            return _ambiguous_refusal(decision, geometry, tags, [anchor, partner], None)
        return DynamicArms(decision, geometry, [*tags, "grounding=dynamic_arms:ambiguous"])
    if anchor_axis != partner_axis:
        box = (
            None
            if geometry.junction_boxes is None
            else junction_box_for(geometry, [(anchor.x, anchor.y), (partner.x, partner.y)])
        )
        if not geometry.junction_declared or (geometry.junction_boxes is not None and box is None):
            if decision.strategy == "yield":
                return _crossing_refusal(decision, geometry, tags, anchor, partner)
            return DynamicArms(
                decision, geometry, [*tags, "grounding=dynamic_arms:crossing_undeclared"]
            )
        crossing = _crossing_geometry(geometry, bearing_axis, snapshot, order, box)
        box_tags = [] if box is None else [f"grounding=dynamic_arms:junction_box:{box.name}"]
        return DynamicArms(
            decision,
            _with_handoff_occupant(crossing, decision, handoff),
            [*tags, "grounding=dynamic_arms:crossing", *box_tags],
        )
    if anchor_axis != bearing_axis:
        if decision.strategy == "yield":
            return _parallel_refusal(decision, geometry, tags, anchor, partner, anchor_axis)
        return DynamicArms(decision, geometry, [*tags, "grounding=dynamic_arms:ambiguous"])
    if decision.strategy == "reverse":
        decision, rear_tags = _exempt_rear_blocked_reversers(decision, snapshot, bearing_axis)
        tags.extend(rear_tags)
    elif not _rear_consistent(anchor, partner, bearing_axis):
        if (
            handoff is None
            and not partner_lent
            and _rear_consistent(partner, anchor, bearing_axis)
        ):
            decision = _with_yielder(decision, partner.robot_id, anchor.robot_id)
            tags.append(f"grounding=rear_regrounded:{anchor.robot_id}->{partner.robot_id}")
            anchor, partner = partner, anchor
        else:
            tags.append(f"grounding=dynamic_arms:rear_inconsistent:{anchor.robot_id}")
    lane = _lane_geometry(geometry, bearing_axis, anchor, partner)
    return DynamicArms(
        decision,
        _with_handoff_occupant(lane, decision, handoff),
        [*tags, f"grounding=dynamic_arms:lane:{bearing_axis}"],
    )


def _with_handoff_occupant(
    geometry: SceneGeometry, decision: CongestionDecision, handoff: tuple[str, str] | None
) -> SceneGeometry:
    # Rule 1's exempt passer, carried so the A15(iv) partner retry never
    # hands it the yield.
    if handoff is None or decision.strategy != "yield":
        return geometry
    return geometry.model_copy(update={"handoff_occupant": handoff[1]})


def _fallback_blocker(
    anchor: RobotStateInput,
    partner: RobotStateInput,
    snapped: RobotStateInput,
    ambiguous: RobotStateInput,
    bearing_axis: Axis,
    handoff: tuple[str, str] | None,
) -> str:
    # Why rule 5 could not lend the ambiguous robot the bearing axis.
    snapped_axis = _heading_axis(snapped.theta)
    if snapped_axis != bearing_axis:
        return (
            f"{snapped.robot_id}'s {snapped_axis} lane crosses the pair's "
            f"{bearing_axis} bearing"
        )
    if ambiguous is anchor and handoff is not None:
        return f"{anchor.robot_id} is the node-handoff arriver, so it must yield"
    return f"{partner.robot_id} faces away from {anchor.robot_id}"


def _ambiguous_refusal(
    decision: CongestionDecision,
    geometry: SceneGeometry,
    tags: list[str],
    ambiguous: list[RobotStateInput],
    blocker: str | None,
) -> DynamicArms:
    offsets = [(state.robot_id, _axis_offset_deg(state.theta)) for state in ambiguous]
    headings = " and ".join(f"{robot_id} heads {deg} deg" for robot_id, deg in offsets)
    clause = "" if blocker is None else f", and {blocker}"
    reason = (
        f"yield refused: ambiguous lane: {headings} off both axes (beyond the 30 deg "
        f"snap){clause}; no retreat room was measured"
    )
    refused = [
        f"grounding=dynamic_arms:ambiguous_refused:{robot_id}:{deg}" for robot_id, deg in offsets
    ]
    return DynamicArms(decision, geometry, [*tags, *refused], reason)


def _crossing_refusal(
    decision: CongestionDecision,
    geometry: SceneGeometry,
    tags: list[str],
    anchor: RobotStateInput,
    partner: RobotStateInput,
) -> DynamicArms:
    anchor_axis = _heading_axis(anchor.theta)
    partner_axis = _heading_axis(partner.theta)
    pair = f"{anchor.robot_id},{partner.robot_id}"
    where = (
        "the scene declares no junction to anchor the arms to"
        if geometry.junction_boxes is None
        else "no declared junction box ("
        + ", ".join(box.name for box in geometry.junction_boxes)
        + ") holds both robots"
    )
    reason = (
        f"yield refused: no declared junction: {anchor.robot_id} runs along {anchor_axis} "
        f"and {partner.robot_id} along {partner_axis} (a crossing), but {where}; no retreat "
        "room was measured"
    )
    return DynamicArms(
        decision, geometry, [*tags, f"grounding=dynamic_arms:crossing_refused:{pair}"], reason
    )


def _parallel_refusal(
    decision: CongestionDecision,
    geometry: SceneGeometry,
    tags: list[str],
    anchor: RobotStateInput,
    partner: RobotStateInput,
    lane_axis: Axis,
) -> DynamicArms:
    cross_axis: Axis = "y" if lane_axis == "x" else "x"
    along = abs(_coord(partner, lane_axis) - _coord(anchor, lane_axis))
    across = abs(_coord(partner, cross_axis) - _coord(anchor, cross_axis))
    bearing_deg = round(math.degrees(math.atan2(across, along)))
    pair = f"{anchor.robot_id},{partner.robot_id}"
    reason = (
        f"yield refused: no shared lane: {anchor.robot_id} and {partner.robot_id} both run "
        f"along {lane_axis} but sit {bearing_deg} deg across it (side by side); no retreat "
        "room was measured"
    )
    return DynamicArms(
        decision,
        geometry,
        [*tags, f"grounding=dynamic_arms:parallel_refused:{pair}:{bearing_deg}"],
        reason,
    )


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
        no tags, when neither transform applies. `refusal_reason` is set when
        the dynamic view refused a yield (`derive_dynamic_arms` rule 6).
    """
    excluded, tags = exclude_parked_robots(decision, snapshot, geometry)
    dynamic = derive_dynamic_arms(excluded, snapshot, geometry, params, goal_references)
    return GroundingView(
        decision=dynamic.decision,
        geometry=dynamic.geometry,
        tags=(*tags, *dynamic.tags),
        refusal_reason=dynamic.refusal_reason,
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

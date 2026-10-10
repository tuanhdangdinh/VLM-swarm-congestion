"""Declared scene geometry M3 derives yield maneuver distances from (no ROS2)."""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from reasoning.vlm.models import StaticObstacleInput

# Slack added on top of the bare park geometry before a retreat counts as
# feasible: odometry drift plus M4's reverse-leg overshoot routinely eat ~0.1 m,
# and a retreat sized to the millimetre would be declared feasible and then
# arrest against the obstacle (2026-09-25 run R2, arrested 0.102 m short).
FEASIBILITY_MARGIN_M: float = 0.2


class CorridorGeometry(BaseModel):
    """The contested corridor: the aisle segment two robots cannot share."""

    model_config = ConfigDict(frozen=True)

    axis: Literal["x", "y"] = "x"
    center_m: float = 0.0
    half_length_m: float = Field(gt=0.0)
    aisle_half_width_m: float = Field(gt=0.0)
    occluder_height_m: float = Field(ge=0.0)


class ArmGeometry(BaseModel):
    """The junction arm one robot approached on: its axis and its outward side."""

    model_config = ConfigDict(frozen=True)

    axis: Literal["x", "y"]
    # Sign of the arm's outward direction from the junction centre along
    # `axis`: the side the robot came from, so the side it retreats to.
    side: Literal[-1, 1]


class JunctionBox(BaseModel):
    """One declared crossing box: where an x-lane and a y-lane intersect.

    prereg-v3 A20(1): a floor with several crossings (S1b's island corners)
    declares each box by its world-frame extent, measured from the faces
    that bound it (rack/island faces and the band edge). Unlike the single
    declared `corridor` box, whose centre is `center_m` on both axes with one
    half-length, a box here has its own centre and half-length per axis.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    x_min_m: float
    x_max_m: float
    y_min_m: float
    y_max_m: float

    @model_validator(mode="after")
    def _extent_is_positive(self) -> JunctionBox:
        if self.x_max_m <= self.x_min_m or self.y_max_m <= self.y_min_m:
            raise ValueError(f"junction box {self.name} has a non-positive extent")
        return self

    def center_m(self, axis: Literal["x", "y"]) -> float:
        """Centre coordinate on `axis`."""
        low, high = (self.x_min_m, self.x_max_m) if axis == "x" else (self.y_min_m, self.y_max_m)
        return round((low + high) / 2.0, 6)

    def half_length_m(self, axis: Literal["x", "y"]) -> float:
        """Half-extent on `axis`: the distance from the centre to the box's mouth."""
        low, high = (self.x_min_m, self.x_max_m) if axis == "x" else (self.y_min_m, self.y_max_m)
        return round((high - low) / 2.0, 6)

    def contains(self, point: tuple[float, float], margin_m: float = 0.0) -> bool:
        """Whether `point` lies inside the box grown by `margin_m` on every side."""
        return (
            self.x_min_m - margin_m <= point[0] <= self.x_max_m + margin_m
            and self.y_min_m - margin_m <= point[1] <= self.y_max_m + margin_m
        )


class CameraGeometry(BaseModel):
    """Overhead camera mount and the plane its markers live on."""

    model_config = ConfigDict(frozen=True)

    height_m: float = Field(default=3.0, gt=0.0)
    marker_height_m: float = Field(default=0.21, ge=0.0)


class RobotGeometry(BaseModel):
    """Robot footprint, marker size, and the separation M4 enforces."""

    model_config = ConfigDict(frozen=True)

    half_width_m: float = Field(default=0.09, gt=0.0)
    marker_half_size_m: float = Field(default=0.06, ge=0.0)
    # Must equal the M4 safety monitor's min_distance_m (swarm_execution
    # config/safety.yaml); escort legs are sized to clear exactly that latch.
    safety_radius_m: float = Field(default=0.45, gt=0.0)


class SceneGeometry(BaseModel):
    """Scenario geometry a caller declares so M3 holds no scenario constants."""

    model_config = ConfigDict(frozen=True)

    corridor: CorridorGeometry
    camera: CameraGeometry = CameraGeometry()
    robot: RobotGeometry = RobotGeometry()
    # 0.3 gave a 7.6 s marker blackout right after the side-step (2026-09-16
    # run A); 0.4 matches the 1.8 m park verified clean in run 8 — the
    # rendered block edge is softer than the geometric projection.
    park_margin_m: float = Field(default=0.4, ge=0.0)
    wall_margin_m: float = Field(default=0.15, ge=0.0)
    passer_margin_m: float = Field(default=0.2, ge=0.0)
    # Junction scenes: robot id -> the arm it approached on. A listed robot
    # yields along its own arm (`arm_geometry`); every `corridor` dimension
    # but the axis is shared, so the junction centre is `corridor.center_m` on
    # both axes. None, or an unlisted robot, keeps the single corridor.
    arms: dict[str, ArmGeometry] | None = None
    # J2 (design study 2026-09-29 S1, section 3): backup clearance used in
    # place of GroundingParams.backup_clearance_m for a yielder with a
    # declared arm. The shipped 1.7 m clearance is the verified head-on
    # tuning and ends an N-S junction pass 0.28-0.45 m outside the tracked
    # band; None (default) keeps that tuning everywhere, including junction
    # scenes with no override declared, so every v1 pin stays byte-identical.
    junction_backup_clearance_m: float | None = Field(default=None, gt=0.0)
    # `junction_clear` (prereg-v2 build-order step 5): the absolute offset
    # from the junction centre, along a recede candidate's own arm axis, that
    # its "evacuation pocket" sits at (|y| in the study's IB10 geometry). This
    # is a DECLARED scene constant, not derived from backup-clearance
    # arithmetic: the intersection-resolvability study's C′ owner-override
    # path sizes it (~1.2 m) from a composite of constraints unrelated to
    # J2's own clearance -- the worst-lane yielder-return margin (>= ~1.0 m),
    # the FCFS crowding radius staying inside 1.5 m, and M1's tracked-band
    # edge -- never from `derive_backup_distance`'s clearance-band search
    # (see `maneuver_geometry.recede_distance_m`). None (default) keeps every
    # existing scene byte-identical and makes `junction_clear` grounding
    # degrade to the plain `yield` fallback (no pocket target to recede to).
    junction_recede_offset_m: float | None = Field(default=None, gt=0.0)
    # Step-7b ruling (iv): staggered recede pockets. The k-th recede
    # candidate in chi order (k = 0 is the lead) recedes to
    # `junction_recede_offset_m - k * junction_recede_stagger_m` instead of
    # the one shared pocket. The lead is released first and drives to its
    # goal on the SECOND candidate's arm, so with one shared 1.2 m pocket the
    # lead parks 0.45 m behind the second candidate (step-7b rerun GT:
    # (0.08, -1.65) vs (0.01, -1.21), exactly `min_distance_m`) and the pair
    # latches for good. A shallower second pocket keeps that endgame
    # separation outside M4's 0.6 m STALE band. Chi ranking always uses the
    # unstaggered offset, so the stagger never changes which robot leads.
    # None (default) keeps every scene byte-identical.
    junction_recede_stagger_m: float | None = Field(default=None, gt=0.0)
    # Freeze-blocking finding 4 (2026-10-02 IB10 composite smoke, both live
    # episodes): the verified M1 tracking extent along a declared arm's own
    # axis (`docs/reports/*y-extent*`: |y| <= 1.75 for IB10's N-S arms). A
    # plain `reverse` leg's backup distance is clamped so the robot's
    # post-backup progress along its OWN arm (`maneuver_geometry.
    # recede_axis_offset_m`, the SAME convention `junction_recede_offset_m`
    # uses) never exceeds this extent -- reproduced in BOTH live episodes
    # (|y|=2.38/2.42) when a robot already well outward on its arm (e.g.
    # mid-transit after a post-composite release) received a further fixed
    # backup with no awareness of where tracking ends. None (default) keeps
    # every existing scene, including every v1 pin, byte-identical -- no
    # clamp is applied without an explicit declaration.
    tracked_extent_m: float | None = Field(default=None, gt=0.0)
    # Loop-map reroute (prereg-v2 (b), build-order step 8 phase 2): the
    # world-frame `(x, y)` waypoints, in order, that take a rerouted robot
    # round the loop map's far aisle instead of re-sending its goal. M4
    # follows them (`follow_waypoints`) and the base mission then resumes
    # the robot's own goal from the last one, so the goal is not listed.
    # Declared per scene because only the loop map has an alternative path
    # to name. None (default) keeps every existing scene byte-identical: a
    # reroute there still grounds `waypoints: []` (a goal re-send).
    reroute_waypoints: tuple[tuple[float, float], ...] | None = None
    # prereg-v3 addendum A8 (i), the IB10 release-lane remedy: both recede
    # pockets sit on the shared N-S centreline, so the release lead's lane
    # runs straight through the held receder's pocket. With fix-H's clearing
    # costmap the lead skimmed it at 0.084-0.191 m centre distance (contact
    # twice; docs/reports/2026-10-08-ib10-lead-flip-diagnosis.md section 4).
    # When > 0, every held recede candidate on the lead's arm axis sidesteps
    # this far off that lane inside its release `yield`
    # (`command_grounder.ground_junction_clear_phases`). 0.0 (default) keeps
    # every scene byte-identical. PROPOSED 0.33 for IB10, frozen at Step 6.
    junction_release_pull_off_m: float = Field(default=0.0, ge=0.0)
    # World-frame side of that sidestep, as a sign along the axis
    # perpendicular to the held robot's arm (for an arm along y, -1 is -x).
    # Declared, not derived: the junction arm is mirror-symmetric, so its
    # geometry fixes the perpendicular axis but not a side. Required when the
    # pull-off is on. PROPOSED -1 for IB10: the lead passed the held robot on
    # +x in 10 of 11 recorded releases, under either lead.
    junction_release_pull_off_side: Literal[-1, 1] | None = None
    # v3 scene design S2: robots parked on purpose at a declared pose, e.g.
    # the parked E-W follower `robot_5` (goal = spawn). Robot id -> world
    # `(x, y)`. A listed robot that M2 names as involved is dropped from the
    # decision before grounding (`reasoning.rag.grounding_view`) while it sits
    # within `parked_pose_tolerance_m` of its pose: it gets no recede, yield
    # or crossing role and no clearance, but it stays in the frame, so it is
    # still drawn and still counts as a follower in chi's N_f (the S2
    # mechanism). Its arm, if it needs one for N_f, is declared in `arms` as
    # usual. None (default) keeps every scene byte-identical.
    parked_robots: dict[str, tuple[float, float]] | None = None
    # How far a parked robot may sit from its declared pose and still count
    # as parked: M5's `arrival_position_tolerance_m`. Farther out it has been
    # displaced into the scene and is grounded like any involved robot.
    parked_pose_tolerance_m: float = Field(default=0.35, gt=0.0)
    # prereg-v3 A16(iii): the declared corridor box is a real junction (rack
    # faces start at its edges), so the dynamic-arms view's crossing branch
    # (`grounding_view.derive_dynamic_arms` rule 4) may anchor its arms to
    # it. False (default): a crossing conflict under the dynamic view has no
    # junction to measure from -- on the open S1b floor it anchored to S1a's
    # junction box and read phantom geometry for 57/400 MC first conflicts
    # -- so a yield there is refused honestly. Read only by that view.
    junction_declared: bool = False
    # prereg-v3 A20(1): the floor's REAL crossing boxes, for a floor whose
    # crossings are not the declared `corridor` box (S1b: the island-corner
    # T-junctions, scripts/s1b_layout.py `crossing_boxes`). With boxes
    # declared, the dynamic view's crossing branch anchors a conflict's arms
    # to the box both robots' footprints overlap (`junction_box_for`) and
    # refuses honestly when there is none; the `corridor` box is then never
    # a crossing anchor. Needs `junction_declared`. None (default) keeps the
    # `corridor` box as the only junction, byte-identical (S1a).
    junction_boxes: tuple[JunctionBox, ...] | None = None
    # The fields below are set only by the dynamic-arms view
    # (`reasoning.rag.grounding_view`), never declared; their defaults keep
    # every declared scene byte-identical.
    # The declared `junction_boxes` entry a crossing view anchored to: every
    # arm then measures from that box's own centre and half-length on the
    # arm's axis (`arm_geometry`, `passer_travel_m`).
    junction_box: JunctionBox | None = None
    # prereg-v3 A20(2): a heading lane. The corridor runs along this world
    # heading (radians) instead of `corridor.axis`: `center_m` and
    # `half_length_m` are measured along it (`along_m`), and the yielder
    # backs along it, as M4 does (its own -heading). `corridor.axis` stays
    # the heading's nearest world axis, for the consumers that need an axis
    # (escort headings). None (default) keeps every axis-aligned view.
    lane_heading_rad: float | None = None
    # Lateral band `yield_retreat_room_m` checks static obstacles across:
    # "aisle" is `aisle_half_width_m` either side of the yielder, "footprint"
    # its own swept width (`robot.half_width_m` either side). S1 declares the
    # racks that flank every aisle as static obstacles, and a dynamic lane's
    # mouth is the yielder's own position (a crossing's is the junction box
    # edge, where the racks start), so across the aisle width each flanking
    # rack straddles the mouth and reads as 0 m of room (S1 pilot ep1: every
    # robot, 216/216 echo replays). Under "footprint" the aisle walls bound
    # the sidestep through `GroundingParams.aisle_{x,y}_band_m` instead.
    # "footprint" also limits the backup clearance to robots inside the swept
    # corridor (`maneuver_geometry.derive_backup_distance`).
    rear_room_band: Literal["aisle", "footprint"] = "aisle"
    # The `(yielder, partner)` pair a dynamic lane corridor was derived from.
    # The yield gate scores only these two: the lane says nothing about where
    # any other involved robot would retreat.
    lane_robots: tuple[str, str] | None = None
    # The node-handoff occupant of a dynamic view's yield (`grounding_view.
    # find_node_handoff`): the exempt passer, which no later re-grounding may
    # hand the yield to (`command_grounder.resolve_yield_roles`).
    handoff_occupant: str | None = None

    @model_validator(mode="after")
    def _lane_robots_are_a_pair(self) -> SceneGeometry:
        if self.lane_robots is not None and self.lane_robots[0] == self.lane_robots[1]:
            raise ValueError("lane_robots must name two different robots")
        return self

    @model_validator(mode="after")
    def _parked_robots_not_empty(self) -> SceneGeometry:
        if self.parked_robots is not None and not self.parked_robots:
            raise ValueError("parked_robots must list at least one robot, or be None")
        return self

    @model_validator(mode="after")
    def _release_pull_off_is_declared(self) -> SceneGeometry:
        if self.junction_release_pull_off_m == 0.0:
            return self
        if self.junction_recede_offset_m is None:
            raise ValueError("junction_release_pull_off_m needs junction_recede_offset_m")
        if self.junction_release_pull_off_side is None:
            raise ValueError("junction_release_pull_off_m needs junction_release_pull_off_side")
        wall_safe = pull_off_lateral_m(self)
        if self.junction_release_pull_off_m > wall_safe:
            raise ValueError(
                f"junction_release_pull_off_m {self.junction_release_pull_off_m} exceeds the "
                f"wall-safe lateral step {wall_safe:.3f} (aisle_half_width_m - robot "
                "half_width_m - wall_margin_m)"
            )
        return self

    @model_validator(mode="after")
    def _junction_boxes_are_declared(self) -> SceneGeometry:
        if self.junction_boxes is None:
            return self
        if not self.junction_boxes:
            raise ValueError("junction_boxes must list at least one box, or be None")
        if not self.junction_declared:
            raise ValueError("junction_boxes needs junction_declared: true")
        names = [box.name for box in self.junction_boxes]
        if len(set(names)) != len(names):
            raise ValueError("junction_boxes names must be unique")
        return self

    @model_validator(mode="after")
    def _reroute_waypoints_not_empty(self) -> SceneGeometry:
        if self.reroute_waypoints is not None and not self.reroute_waypoints:
            raise ValueError("reroute_waypoints must list at least one waypoint, or be None")
        return self

    @model_validator(mode="after")
    def _stagger_needs_a_pocket(self) -> SceneGeometry:
        if self.junction_recede_stagger_m is None:
            return self
        if self.junction_recede_offset_m is None:
            raise ValueError("junction_recede_stagger_m needs junction_recede_offset_m")
        if self.junction_recede_stagger_m >= self.junction_recede_offset_m:
            raise ValueError(
                "junction_recede_stagger_m must be smaller than junction_recede_offset_m"
            )
        return self


def arm_geometry(geometry: SceneGeometry, robot_id: str) -> tuple[SceneGeometry, float | None]:
    """Resolve the corridor a robot yields along, and its retreat side if fixed.

    Args:
        geometry: Declared scene geometry.
        robot_id: The robot that would retreat.

    Returns:
        `(geometry, None)` when the robot has no declared arm: the caller keeps
        its passer-relative side rule on the single corridor. Otherwise the
        geometry with `corridor.axis` set to the arm's axis (the same object
        when the axis already matches) and the arm's outward side as `-1.0`
        or `+1.0`.
    """
    arm = (geometry.arms or {}).get(robot_id)
    if arm is None:
        return geometry, None
    box = geometry.junction_box
    if box is not None:
        # A declared crossing box (A20(1)): the arm's mouth is that box's own
        # face on the arm's axis, not a square box at (center_m, center_m).
        corridor = geometry.corridor.model_copy(
            update={
                "axis": arm.axis,
                "center_m": box.center_m(arm.axis),
                "half_length_m": box.half_length_m(arm.axis),
            }
        )
        return geometry.model_copy(update={"corridor": corridor}), float(arm.side)
    if arm.axis != geometry.corridor.axis:
        corridor = geometry.corridor.model_copy(update={"axis": arm.axis})
        geometry = geometry.model_copy(update={"corridor": corridor})
    return geometry, float(arm.side)


def passer_travel_m(
    passer_id: str,
    passer_xy: tuple[float, float],
    yielder_parked_xy: tuple[float, float],
    geometry: SceneGeometry,
    yielder_id: str | None,
) -> float:
    """How far a passer drives, before the clearance margin, to be clear.

    A passer on the yielder's axis must get past the parked yielder: the
    distance between them along that axis, as the single-corridor grounder
    has always measured it. A passer on a crossing arm never meets the parked
    yielder; it must leave the junction, so the distance runs along its own
    axis to the far mouth (`corridor.half_length_m` past the centre, on the
    side opposite the arm it came from), floored at 0.

    Args:
        passer_id: The passing robot.
        passer_xy: Its world-frame `(x, y)` in metres.
        yielder_parked_xy: World position the yielder retreats to; only its
            coordinate on the yielder's axis is read.
        geometry: Declared scene geometry.
        yielder_id: The yielding robot, whose arm fixes the yielder's axis; None
            uses `corridor.axis`.

    Returns:
        Travel distance in metres.
    """
    yielder_geometry = geometry if yielder_id is None else arm_geometry(geometry, yielder_id)[0]
    axis_index = 0 if yielder_geometry.corridor.axis == "x" else 1
    passer_arm = (geometry.arms or {}).get(passer_id)
    if passer_arm is None or passer_arm.axis == yielder_geometry.corridor.axis:
        if yielder_geometry.lane_heading_rad is not None:
            return abs(
                along_m(yielder_geometry, passer_xy) - along_m(yielder_geometry, yielder_parked_xy)
            )
        return abs(passer_xy[axis_index] - yielder_parked_xy[axis_index])
    own_index = 0 if passer_arm.axis == "x" else 1
    forward = -float(passer_arm.side)
    own_corridor = arm_geometry(geometry, passer_id)[0].corridor
    far_mouth = own_corridor.center_m + forward * own_corridor.half_length_m
    return max(0.0, (far_mouth - passer_xy[own_index]) * forward)


def along_m(geometry: SceneGeometry, point: tuple[float, float]) -> float:
    """A point's coordinate along the corridor (the one `center_m` is measured on).

    Args:
        geometry: Scene geometry.
        point: World-frame `(x, y)` in metres.

    Returns:
        `x` or `y` for an axis-aligned corridor (exactly, no projection); the
        projection onto the heading for a heading lane (`lane_heading_rad`).
    """
    heading = geometry.lane_heading_rad
    if heading is None:
        return point[0] if geometry.corridor.axis == "x" else point[1]
    return point[0] * math.cos(heading) + point[1] * math.sin(heading)


def across_m(geometry: SceneGeometry, point: tuple[float, float]) -> float:
    """A point's coordinate across the corridor (perpendicular to `along_m`).

    Args:
        geometry: Scene geometry.
        point: World-frame `(x, y)` in metres.

    Returns:
        `y` or `x` for an axis-aligned corridor; the left-normal projection
        for a heading lane.
    """
    heading = geometry.lane_heading_rad
    if heading is None:
        return point[1] if geometry.corridor.axis == "x" else point[0]
    return -point[0] * math.sin(heading) + point[1] * math.cos(heading)


def corridor_direction(geometry: SceneGeometry) -> tuple[float, float]:
    """World-frame unit vector of increasing `along_m`.

    Args:
        geometry: Scene geometry.

    Returns:
        `(1, 0)` / `(0, 1)` for an axis-aligned corridor, the heading's unit
        vector for a heading lane.
    """
    heading = geometry.lane_heading_rad
    if heading is None:
        return (1.0, 0.0) if geometry.corridor.axis == "x" else (0.0, 1.0)
    return (math.cos(heading), math.sin(heading))


def junction_box_for(
    geometry: SceneGeometry, points: Sequence[tuple[float, float]]
) -> JunctionBox | None:
    """The declared crossing box every point's footprint overlaps, if any.

    A robot is in a box when its centre lies within `robot.half_width_m` of
    it (its body overlaps the box). First match in declaration order; the
    S1b boxes are far apart, so at most one can match a latched pair.

    Args:
        geometry: Scene geometry with `junction_boxes` declared.
        points: World-frame `(x, y)` of every robot that must be inside.

    Returns:
        The box, or None when no box holds them all or none is declared.
    """
    for box in geometry.junction_boxes or ():
        if all(box.contains(point, geometry.robot.half_width_m) for point in points):
            return box
    return None


def visibility_boundary_m(geometry: SceneGeometry) -> float:
    """Distance from the corridor centre past which a parked marker stays visible.

    The corridor's occluder (height `occluder_height_m`, ending at
    `half_length_m` from the centre) is seen by a camera at `height_m` directly
    above the centre. Its top edge projects onto the marker plane
    (`marker_height_m`) at `half_length_m * (height_m - marker_height_m) /
    (height_m - occluder_height_m)`, measured from the centre along
    `corridor.axis`.

    Args:
        geometry: Declared scene geometry.

    Returns:
        Boundary distance in metres from the corridor centre along the axis.

    Raises:
        ValueError: If the occluder reaches the camera or the marker plane sits
            at or above the camera, so the projection is undefined.
    """
    camera_to_occluder = geometry.camera.height_m - geometry.corridor.occluder_height_m
    camera_to_marker = geometry.camera.height_m - geometry.camera.marker_height_m
    if camera_to_occluder <= 0.0:
        raise ValueError(
            "occluder_height_m must be below camera height_m: "
            f"{geometry.corridor.occluder_height_m} >= {geometry.camera.height_m}"
        )
    if camera_to_marker <= 0.0:
        raise ValueError(
            "marker_height_m must be below camera height_m: "
            f"{geometry.camera.marker_height_m} >= {geometry.camera.height_m}"
        )
    return geometry.corridor.half_length_m * camera_to_marker / camera_to_occluder


def park_offset_m(geometry: SceneGeometry) -> float:
    """Offset from the corridor centre at which the yielder parks.

    `visibility_boundary_m` plus the marker's half-size (the whole marker, not
    just its centre, must clear the projected silhouette) plus `park_margin_m`.

    Args:
        geometry: Declared scene geometry.

    Returns:
        Park offset in metres from the corridor centre along `corridor.axis`.

    Raises:
        ValueError: If the visibility boundary is undefined for this geometry.
    """
    return (
        visibility_boundary_m(geometry)
        + geometry.robot.marker_half_size_m
        + geometry.park_margin_m
    )


def pull_off_lateral_m(geometry: SceneGeometry) -> float:
    """Lateral step the yielder takes off the corridor centreline.

    `aisle_half_width_m` minus the robot's `half_width_m` minus
    `wall_margin_m`, floored at 0.0 for an aisle too narrow to step aside in.

    Args:
        geometry: Declared scene geometry.

    Returns:
        Lateral offset in metres, perpendicular to `corridor.axis`.
    """
    lateral = (
        geometry.corridor.aisle_half_width_m
        - geometry.robot.half_width_m
        - geometry.wall_margin_m
    )
    return max(0.0, lateral)


def release_pull_off_lateral_m(
    geometry: SceneGeometry, held_id: str, lead_id: str
) -> float | None:
    """Robot-frame pull-off a held recede candidate takes off the release lead's lane.

    The lead's lane is its own arm's axis through the junction: inward along
    its own arm, out along the opposite one. A held robot whose declared arm
    runs along that same axis is parked on the lane (its pocket shares the
    centreline); a robot on the crossing axis is not. The step size is
    `junction_release_pull_off_m`; its world side is
    `junction_release_pull_off_side` along the axis perpendicular to the arm,
    converted to M4's robot-frame convention (positive = left) with the held
    robot facing the junction (heading = -side along its arm, the same
    convention as `maneuver_geometry.retreat_axes`): a straight reverse into
    its pocket keeps that heading.

    Args:
        geometry: Declared scene geometry.
        held_id: The held robot.
        lead_id: The release lead.

    Returns:
        The signed `pull_off_lateral_m` for `held_id`, rounded to the
        millimetre, or None when the pull-off is off, either robot has no
        declared arm, or the held robot's arm is not on the lead's axis.
    """
    if geometry.junction_release_pull_off_m == 0.0 or held_id == lead_id:
        return None
    arms = geometry.arms or {}
    held_arm = arms.get(held_id)
    lead_arm = arms.get(lead_id)
    if held_arm is None or lead_arm is None or held_arm.axis != lead_arm.axis:
        return None
    side = geometry.junction_release_pull_off_side
    assert side is not None  # enforced by SceneGeometry's validator
    # Facing the junction: heading = -arm.side along the arm axis. Its left is
    # the heading rotated +90 degrees; for an arm along y that is
    # (arm.side, 0), for an arm along x it is (0, -arm.side).
    left_on_lateral_axis = held_arm.side if held_arm.axis == "y" else -held_arm.side
    return round(side * left_on_lateral_axis * geometry.junction_release_pull_off_m, 3)


def passer_clearance_m(geometry: SceneGeometry) -> float:
    """Margin added beyond the parked yielder before the passer's hold may end.

    The robot's `safety_radius_m` plus `passer_margin_m`: resuming while the
    passer is still inside the safety radius latches both robots.

    Args:
        geometry: Declared scene geometry.

    Returns:
        Clearance distance in metres.
    """
    return geometry.robot.safety_radius_m + geometry.passer_margin_m


def required_room_m(geometry: SceneGeometry) -> float:
    """Room past the corridor mouth a yielder needs before it can park.

    The park point sits `park_offset_m` from the corridor centre, i.e.
    `park_offset_m - half_length_m` past the mouth; the robot's rear reaches
    another `half_width_m` beyond that, and `FEASIBILITY_MARGIN_M` covers
    odometry drift.

    Args:
        geometry: Declared scene geometry.

    Returns:
        Required room in metres, measured from the corridor mouth outward along
        `corridor.axis`.

    Raises:
        ValueError: If the visibility boundary is undefined for this geometry.
    """
    return (
        park_offset_m(geometry)
        - geometry.corridor.half_length_m
        + geometry.robot.half_width_m
        + FEASIBILITY_MARGIN_M
    )


def room_is_feasible(room_m: float | None, geometry: SceneGeometry) -> bool:
    """Whether that much room past the corridor mouth is enough to park in.

    Args:
        room_m: Room in metres from the corridor mouth, or `None` when nothing
            bounds the retreat on that side.
        geometry: Declared scene geometry.

    Returns:
        True when the retreat is unbounded or the room meets `required_room_m`.
    """
    if room_m is None:
        return True
    return room_m >= required_room_m(geometry)


def yield_retreat_room_m(
    yielder_position: tuple[float, float],
    side: float,
    static_obstacles: Sequence[StaticObstacleInput],
    geometry: SceneGeometry,
) -> float | None:
    """Free room a yielder retreating to its own side has past the corridor mouth.

    Measured in world-frame metres along `corridor.axis`, from the corridor
    mouth on `side` outward to the nearest face of a static obstacle that lies
    beyond that mouth and whose lateral extent overlaps the corridor's lateral
    band. The band is `aisle_half_width_m` either side of the yielder's own
    perpendicular coordinate: an obstacle parked in a neighbouring aisle is not
    in this robot's way. With `geometry.rear_room_band == "footprint"` (the
    dynamic-arms views) the band is the robot's own swept width instead,
    `robot.half_width_m` either side, so the racks flanking its aisle do not
    count.

    Args:
        yielder_position: The yielder's world-frame `(x, y)` in metres.
        side: Retreat direction along `corridor.axis`: `-1.0` toward decreasing
            coordinates, `+1.0` toward increasing ones.
        static_obstacles: Fixed, axis-aligned obstacles of the running scenario.
        geometry: Declared scene geometry.

    Returns:
        Room in metres from the corridor mouth, or `None` when no obstacle
        bounds the retreat on that side.
    """
    axis_index = 0 if geometry.corridor.axis == "x" else 1
    perp_index = 1 - axis_index
    mouth_coord = geometry.corridor.center_m + side * geometry.corridor.half_length_m
    band_center = yielder_position[perp_index]
    band_half_width = (
        geometry.corridor.aisle_half_width_m
        if geometry.rear_room_band == "aisle"
        else geometry.robot.half_width_m
    )
    if geometry.lane_heading_rad is not None:
        return _heading_lane_room_m(
            yielder_position, side, static_obstacles, geometry, mouth_coord, band_half_width
        )

    rooms: list[float] = []
    for obstacle in static_obstacles:
        centre = (obstacle.x, obstacle.y)
        half_extent = (obstacle.size_x_m / 2.0, obstacle.size_y_m / 2.0)
        if abs(centre[perp_index] - band_center) > band_half_width + half_extent[perp_index]:
            continue
        axis_centre = centre[axis_index]
        axis_half = half_extent[axis_index]
        # Skip obstacles that do not reach past the mouth on this side: they sit
        # inside the corridor or behind the passer, and bound no retreat here.
        if (axis_centre + side * axis_half - mouth_coord) * side <= 0.0:
            continue
        near_face = axis_centre - side * axis_half
        rooms.append(max(0.0, (near_face - mouth_coord) * side))

    return min(rooms) if rooms else None


def _heading_lane_room_m(
    yielder_position: tuple[float, float],
    side: float,
    static_obstacles: Sequence[StaticObstacleInput],
    geometry: SceneGeometry,
    mouth_coord: float,
    band_half_width: float,
) -> float | None:
    # `yield_retreat_room_m` along a heading lane (A20(2)): the same rule in
    # the lane's own frame. Each box is clipped to the swept band (the strip
    # `band_half_width` either side of the retreat line through the yielder);
    # what is left bounds the retreat when it reaches past the mouth on
    # `side`, and the room is the distance to its nearest point along the lane.
    band_center = across_m(geometry, yielder_position)
    rooms: list[float] = []
    for obstacle in static_obstacles:
        hx, hy = obstacle.size_x_m / 2.0, obstacle.size_y_m / 2.0
        corners = [
            (obstacle.x - hx, obstacle.y - hy),
            (obstacle.x + hx, obstacle.y - hy),
            (obstacle.x + hx, obstacle.y + hy),
            (obstacle.x - hx, obstacle.y + hy),
        ]
        polygon = [(along_m(geometry, c), across_m(geometry, c)) for c in corners]
        polygon = _clip_across(polygon, band_center - band_half_width, keep_above=True)
        polygon = _clip_across(polygon, band_center + band_half_width, keep_above=False)
        if not polygon:
            continue
        outward = [(u - mouth_coord) * side for u, _ in polygon]
        if max(outward) <= 0.0:
            continue
        rooms.append(max(0.0, min(outward)))
    return min(rooms) if rooms else None


def _clip_across(
    polygon: list[tuple[float, float]], bound: float, keep_above: bool
) -> list[tuple[float, float]]:
    # One Sutherland-Hodgman pass of a convex (along, across) polygon against
    # the line across == bound.
    def inside(point: tuple[float, float]) -> bool:
        return point[1] >= bound if keep_above else point[1] <= bound

    out: list[tuple[float, float]] = []
    for index, current in enumerate(polygon):
        previous = polygon[index - 1]
        if inside(current):
            if not inside(previous):
                out.append(_cut(previous, current, bound))
            out.append(current)
        elif inside(previous):
            out.append(_cut(previous, current, bound))
    return out


def _cut(
    a: tuple[float, float], b: tuple[float, float], bound: float
) -> tuple[float, float]:
    t = (bound - a[1]) / (b[1] - a[1])
    return (a[0] + t * (b[0] - a[0]), bound)


def yield_feasible(
    yielder_position: tuple[float, float],
    side: float,
    static_obstacles: Sequence[StaticObstacleInput],
    geometry: SceneGeometry,
) -> bool:
    """Whether a robot retreating to `side` can still reach its park point.

    Args:
        yielder_position: The yielder's world-frame `(x, y)` in metres.
        side: Retreat direction along `corridor.axis` (`-1.0` or `+1.0`).
        static_obstacles: Fixed, axis-aligned obstacles of the running scenario.
        geometry: Declared scene geometry.

    Returns:
        True when nothing bounds the retreat, or what bounds it leaves at least
        `required_room_m`.
    """
    return room_is_feasible(
        yield_retreat_room_m(yielder_position, side, static_obstacles, geometry), geometry
    )

"""Pillar 1: derived maneuver distances for derived-mode grounding (rev-8 A.2).

The physical quantities (park point, sidestep, escort clearance, safety radius)
come from `reasoning.rag.scene_geometry` whenever the caller declares a scene
geometry, so derived and legacy grounding share one derivation. The constants
on `GroundingParams` are the fallbacks for callers without one.
"""

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)

from reasoning.rag.scene_geometry import (
    FEASIBILITY_MARGIN_M,
    ArmGeometry,
    SceneGeometry,
    arm_geometry,
    park_offset_m,
    passer_clearance_m,
    passer_travel_m,
    pull_off_lateral_m,
)
from reasoning.vlm.models import RobotStateInput, SnapshotFrame

# Tolerance for the clearance comparisons: a requirement met exactly (1.3 m
# backup against a 1.7 m clearance from a 0.4 m standoff) must not fail on
# float round-off.
_EPS = 1e-9


class GroundingParams(BaseModel):
    """Tunable geometry parameters for derived-mode grounding (rev-8 A.2/A.3).

    `backup_clearance_m` and `escort_clearance_m` are the composed
    pass-clearance values (the spec's `2*min_distance_m + margin` form);
    defaults reproduce the verified head-on tuning: 1.3 m backup from a
    0.4 m standoff, 2.4 m escort from a 1.9 m park distance.

    `min_distance_m`, `lateral_m` and `escort_clearance_m` are fallbacks: with
    a declared `SceneGeometry` they are replaced by the scene's safety radius,
    `pull_off_lateral_m` and `passer_clearance_m` (see `maneuver_limits`).
    """

    # Forbid unknown keys: a typo in a grounding threshold must fail loudly
    # instead of silently running on the default (same rule as ClassicalParams).
    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: Literal["legacy", "derived"] = "legacy"
    min_distance_m: float = Field(default=0.45, gt=0)
    backup_clearance_m: float = Field(default=1.7, gt=0)
    escort_clearance_m: float = Field(default=0.5, gt=0)
    backup_band_m: tuple[float, float] = (0.5, 2.0)
    escort_band_m: tuple[float, float] = (1.0, 3.5)
    lateral_m: float = Field(default=0.35, gt=0)
    # Appendix A.3 requires swept segments sampled at <= 0.1 m intervals.
    sweep_step_m: float = Field(default=0.1, gt=0, le=0.1)
    # World-frame y band the whole swept path must stay inside (e.g. a mapped
    # aisle). None leaves the sweep unbounded laterally unless a declared
    # geometry supplies a band (see `retreat_candidates`).
    aisle_y_band_m: tuple[float, float] | None = None
    # World-frame x band for a yielder whose own retreat axis is y (a junction
    # arm declared `axis: y`): the N-S aisle's walls, which the lane band
    # centred on the yielder's own x does not know (B1 bottleneck_merge). It
    # takes precedence over `aisle_y_band_m` for such a yielder only; None
    # leaves every yielder on the pre-existing bands, byte for byte.
    aisle_x_band_m: tuple[float, float] | None = None
    hold_backstop_sec: float = Field(default=45.0, gt=0)
    wait_backstop_sec: float = Field(default=120.0, gt=0)
    resolution_backstop_sec: float = Field(default=150.0, gt=0)
    # `junction_clear` cost-ranked recede selection (prereg-v2 (a) Grounding):
    # chi = s * D_SPACE + t * N_f, per A-DRIVE (arXiv:2204.04910). Placeholder
    # defaults, same convention as `command_grounder.PlanRepairParams.
    # max_repair_edits`: not yet sized against live data, registered here so
    # the weighting is config, not a buried constant. s=1.0 makes distance the
    # unit cost; t=0.5 gives a follower half as much weight as one metre of
    # travel -- a gentle, not a dominant, preference against receding a robot
    # with queued followers on its own arm.
    junction_recede_cost_space_weight: float = Field(default=1.0, ge=0.0)
    junction_recede_cost_follower_weight: float = Field(default=0.5, ge=0.0)
    # How close to `SceneGeometry.junction_recede_offset_m` counts as "already
    # receded": the M1 static-error budget the intersection-resolvability
    # study measured (median <= 0.011 m, max 0.084 m), rounded up with margin.
    junction_recede_tolerance_m: float = Field(default=0.1, ge=0.0)
    # χ-epsilon verbatim rule (prereg-v2 (a0), RULED 2026-10-03): two recede
    # orders whose differently-ordered pairs all sit within this χ margin are
    # one equivalence class at VERIFICATION only -- a plan listing them in
    # the non-χ order is not a reorder problem, while dispatch stays in χ
    # order (unless prereg-v3 R3.3's `plan_dispatch_order_source:
    # model_when_verified` dispatches a verbatim plan's own order) and the
    # divergence is recorded (`command_grounder.
    # JunctionDispatchMatch.order_equivalent`). Measured on every IB10 run
    # with geometry on disk: within-run χ spread <= 5 mm, between-run
    # jam-formation margins up to 0.142 m in the nominally symmetric scene;
    # no structural difference (>= 0.5 per follower at the shipped weights)
    # ever observed (docs/reports/2026-10-03-plan-grammar-fixes.md).
    # Re-measure for any scene family whose follower counts differ.
    junction_recede_order_epsilon: float = Field(default=0.15, ge=0.0)
    # Hold duration for a recede leg's clearing command (`reverse` + the other
    # involved robots' `temporary_wait`, see `command_grounder.
    # ground_junction_clear_phases`): generous upper bound on how long the
    # remaining phases of one `junction_clear` resolution should take.
    # Placeholder, same convention as `max_repair_edits`: sized from the
    # build-order step 6 mock sweep, not yet from live data.
    junction_recede_hold_sec: float = Field(default=120.0, gt=0)
    # v3 S1 prerequisite 2 (scene design S1, "M3 dynamic arms plus a
    # node-handoff grounding"): derive a `yield`/`reverse` decision's corridor
    # axis, retreat sides and park target from the decision snapshot instead
    # of the declared `scenario_geometry` (`reasoning.rag.grounding_view`).
    # `junction_clear` never uses it (declared geometry only). False (default)
    # keeps every grounding byte-identical, and both fields stay out of the
    # artifact dump.
    dynamic_scene_arms: bool = False
    # Node handoff: an involved robot within this distance of another
    # involved robot's current task node occupies it (M5's
    # `arrived_radius_m`, the radius its arrival excusal already uses).
    dynamic_handoff_radius_m: float = Field(default=0.5, gt=0)
    # Body-to-box clearance the retreat-candidate sweep demands under a
    # dynamic-arms view (`retreat_candidates.generate_retreat_candidates`):
    # each static obstacle is grown by `robot.half_width_m` plus this. 0.0
    # (default) is the bare footprint, the sweep as it shipped. Read only
    # under the footprint band, and stays out of the artifact dump unless
    # the switch is on and the margin is set.
    retreat_box_margin_m: float = Field(default=0.0, ge=0.0)
    # S1 episode loop (2026-10-09, E1): cap each escorted passer's escort AND
    # clearance distance at its distance-to-turn -- the along-axis distance
    # from the passer to its current registry goal's coordinate on the escort
    # axis, where its box-centred route leaves that axis
    # (`grounding_view.apply_escort_headings`). E1's fixed 2.35 m carried
    # robot_5 0.4 m past its S turn. Read only with `dynamic_scene_arms`;
    # False (default) keeps every command and artifact dump byte-identical.
    escort_turn_cap: bool = False

    @model_validator(mode="after")
    def _check_bands(self) -> "GroundingParams":
        bands = {"backup_band_m": self.backup_band_m, "escort_band_m": self.escort_band_m}
        if self.aisle_y_band_m is not None:
            bands["aisle_y_band_m"] = self.aisle_y_band_m
        if self.aisle_x_band_m is not None:
            bands["aisle_x_band_m"] = self.aisle_x_band_m
        for name, (low, high) in bands.items():
            if low > high:
                raise ValueError(f"{name} lower bound {low} exceeds upper bound {high}")
        for name in ("backup_band_m", "escort_band_m"):
            if bands[name][0] < 0:
                raise ValueError(f"{name} must be non-negative, got {bands[name]}")
        return self

    @model_serializer(mode="wrap")
    def _omit_unset_x_band(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # Decision artifacts dump these params; an unset x band stays out of
        # the dump so every artifact of a scene without one is unchanged.
        data = handler(self)
        if data.get("aisle_x_band_m") is None:
            data.pop("aisle_x_band_m", None)
        # Same rule for the dynamic-arms switch: an artifact grounded with it
        # off is byte-identical to one written before it existed.
        if not data.get("dynamic_scene_arms"):
            data.pop("dynamic_scene_arms", None)
            data.pop("dynamic_handoff_radius_m", None)
            data.pop("retreat_box_margin_m", None)
            data.pop("escort_turn_cap", None)
        else:
            if not data.get("retreat_box_margin_m"):
                data.pop("retreat_box_margin_m", None)
            if not data.get("escort_turn_cap"):
                data.pop("escort_turn_cap", None)
        return data


class Derivation(BaseModel):
    """Outcome of one geometric derivation: a value or an infeasibility reason."""

    model_config = ConfigDict(frozen=True)

    feasible: bool
    value_m: float | None = None
    reason: str | None = None


class ManeuverLimits(BaseModel):
    """The physical maneuver quantities in force for one grounding call."""

    model_config = ConfigDict(frozen=True)

    min_distance_m: float = Field(gt=0)
    # 0.0 when a declared aisle is too narrow to step aside in.
    lateral_m: float = Field(ge=0)
    escort_clearance_m: float = Field(gt=0)


class RetreatAxes(BaseModel):
    """World-frame unit vectors of a yielder's retreat and robot-frame left."""

    model_config = ConfigDict(frozen=True)

    retreat: tuple[float, float]
    # Positive lateral offsets move along this vector. It is the left of the
    # robot's heading (M4 executes `pull_off_lateral_m` as a robot-frame left
    # step), with the heading taken as the reverse of `retreat`.
    left: tuple[float, float]


def maneuver_limits(params: GroundingParams, geometry: SceneGeometry | None) -> ManeuverLimits:
    """Resolve the maneuver quantities from the declared scene, else from params.

    Args:
        params: Grounding parameters (fallback constants).
        geometry: Declared scene geometry, or None.

    Returns:
        With a geometry: its `robot.safety_radius_m`, `pull_off_lateral_m`
        (rounded to the millimetre, as the legacy grounder does) and
        `passer_clearance_m`. Without one: `params.min_distance_m`,
        `params.lateral_m` and `params.escort_clearance_m`.
    """
    if geometry is None:
        return ManeuverLimits(
            min_distance_m=params.min_distance_m,
            lateral_m=params.lateral_m,
            escort_clearance_m=params.escort_clearance_m,
        )
    return ManeuverLimits(
        min_distance_m=geometry.robot.safety_radius_m,
        lateral_m=round(pull_off_lateral_m(geometry), 3),
        escort_clearance_m=passer_clearance_m(geometry),
    )


def retreat_axes(
    frame: SnapshotFrame,
    yielder_id: str,
    passer_id: str | None,
    geometry: SceneGeometry | None,
) -> RetreatAxes | None:
    """Direction the yielder backs up along, and its robot-frame left.

    Without a geometry the retreat is the reverse of the yielder's own
    heading. With one it runs along `corridor.axis`, away from the passer:
    the same side rule the legacy grounder and the yield feasibility gate
    use, so the gate's verdict and the candidates describe the same retreat.
    A yielder with a declared junction arm retreats outward along that arm
    instead (`scene_geometry.arm_geometry`), as the gate scores it.

    Args:
        frame: Current scene snapshot.
        yielder_id: Robot that retreats.
        passer_id: First robot to cross; required when `geometry` is given.
        geometry: Declared scene geometry, or None.

    Returns:
        The axes, or None when the yielder (or, with a geometry, the passer)
        is absent from the frame.
    """
    yielder = frame.find_robot(yielder_id)
    if yielder is None:
        return None
    if geometry is None:
        heading = (math.cos(yielder.theta), math.sin(yielder.theta))
    else:
        passer = frame.find_robot(passer_id) if passer_id is not None else None
        if passer is None:
            return None
        axis_index, side, _ = _yield_side(yielder, passer, geometry)
        unit = (1.0, 0.0) if axis_index == 0 else (0.0, 1.0)
        heading = (-side * unit[0], -side * unit[1])
    return RetreatAxes(retreat=(-heading[0], -heading[1]), left=(-heading[1], heading[0]))


def project_progress(
    start: tuple[float, float], current: tuple[float, float], axis_theta: float
) -> float:
    """Signed displacement projected onto a transit axis (rev-8 A.2).

    Args:
        start: World position when the maneuver began, `(x, y)`.
        current: Current world position, `(x, y)`.
        axis_theta: Transit-axis heading in radians (world frame).

    Returns:
        Progress in meters; lateral drift contributes nothing and backward
        motion is negative.
    """
    return (current[0] - start[0]) * math.cos(axis_theta) + (current[1] - start[1]) * math.sin(
        axis_theta
    )


def derive_backup_distance(
    frame: SnapshotFrame,
    yielder_id: str,
    other_ids: Sequence[str],
    params: GroundingParams,
    *,
    geometry: SceneGeometry | None = None,
    at_least_m: float | None = None,
) -> Derivation:
    """Minimum in-band retreat distance clearing every crossing robot.

    Finds the smallest `d` in `params.backup_band_m` such that the
    retreat-axis-projected separation to every robot in `other_ids` is at
    least `params.backup_clearance_m`, or `geometry.junction_backup_clearance_m`
    when the yielder has a declared arm and that override is set (J2, design
    study 2026-09-29 S1 section 3). With a declared geometry `d` must also
    reach the yielder's park point (`scene_geometry.park_offset_m` from the
    corridor centre, on the yielder's own side), which keeps the parked marker
    clear of the occluder's projection. Out-of-band requirements are
    infeasible, never clamped (rev-8 A.2).

    The minimum is exact rather than scanned: the feasible set is the band
    minus one open interval `(s - c, s + c)` per robot, so its minimum is the
    band's lower bound or some `s + c`.

    Under a dynamic-arms view (`geometry.rear_room_band == "footprint"`) only
    robots that bear on the retreat are projected: `other_ids[0]` (it fixes
    the retreat side), the lane pair (`geometry.lane_robots`), and any robot
    within the swept corridor, `2 * robot.half_width_m + FEASIBILITY_MARGIN_M`
    either side of the retreat line. A robot farther aside (S1's N-arm queue
    beside an E-W lane) is not in the backup path, and the candidate sweep
    (`retreat_candidates.generate_retreat_candidates`: every robot at
    `min_distance_m`, plus static boxes) still vetoes any retreat that would
    pass too close to it. Declared geometry keeps projecting every robot.

    Args:
        frame: Current scene snapshot.
        yielder_id: Robot that retreats.
        other_ids: Robots in the crossing order (all must be present); with a
            geometry the first one fixes the retreat side.
        params: Geometry parameters.
        geometry: Declared scene geometry, or None for the heading-based frame.
        at_least_m: Lower bound on `d` besides the band and the park point:
            the smallest feasible `d` at or above it is returned. None (the
            default) is no extra bound. `prepare_retreat_selection` deepens a
            backup through it when no candidate survives the box sweep.

    Returns:
        Feasible derivation with `value_m` (millimetre-rounded), or infeasible
        with `reason`.
    """
    yielder = frame.find_robot(yielder_id)
    if yielder is None:
        return Derivation(feasible=False, reason=f"yielder {yielder_id} not in snapshot")
    others: list[RobotStateInput] = []
    for robot_id in other_ids:
        state = frame.find_robot(robot_id)
        if state is None:
            return Derivation(feasible=False, reason=f"robot {robot_id} not in snapshot")
        others.append(state)
    passer_id = other_ids[0] if other_ids else None
    axes = retreat_axes(frame, yielder_id, passer_id, geometry)
    if axes is None:
        return Derivation(
            feasible=False, reason="no crossing robot to fix the retreat side against"
        )
    offsets = [
        (state.x - yielder.x) * axes.retreat[0] + (state.y - yielder.y) * axes.retreat[1]
        for state in _clearance_robots(yielder, others, axes, geometry)
    ]

    low, high = params.backup_band_m
    floor = 0.0
    if geometry is not None:
        floor = _park_backup_floor_m(yielder, others[0], geometry)
        if floor > high + _EPS:
            return Derivation(
                feasible=False,
                reason=(
                    f"park point needs a {floor:.3f} m backup, outside band [{low}, {high}] m"
                ),
            )
    start = max(low, floor) if at_least_m is None else max(low, floor, at_least_m)
    clearance = _backup_clearance_m(yielder_id, params, geometry)
    candidates = sorted({start} | {s + clearance for s in offsets if s + clearance > start})
    for d in candidates:
        if d > high + _EPS:
            break
        if all(abs(s - d) >= clearance - _EPS for s in offsets):
            return Derivation(feasible=True, value_m=round(d, 3))
    return Derivation(
        feasible=False,
        reason=(
            f"no backup distance in band [{low}, {high}] m satisfies clearance {clearance} m"
        ),
    )


def derive_escort_distance(
    frame: SnapshotFrame,
    passer_id: str,
    yielder_parked_xy: tuple[float, float],
    params: GroundingParams,
    *,
    geometry: SceneGeometry | None = None,
    yielder_id: str | None = None,
) -> Derivation:
    """Escort distance placing the passer past the parked yielder (rev-8 A.2).

    The distance from the passer's current position to the yielder's parked
    position, plus the escort clearance from `maneuver_limits`. Without a
    geometry it is measured along the passer's own heading (signed, so a
    passer facing away is infeasible); with one, along `corridor.axis`,
    exactly as the legacy grounder measures it, or for a passer on a crossing
    junction arm to the junction's far mouth (`scene_geometry.passer_travel_m`).
    Out-of-band requirements are infeasible, never truncated.

    Args:
        frame: Current scene snapshot.
        passer_id: Robot escorted through the conflict.
        yielder_parked_xy: World position the yielder retreats to.
        params: Geometry parameters.
        geometry: Declared scene geometry, or None.
        yielder_id: The yielder, whose declared arm (if any) fixes the axis
            the parked position is compared along.

    Returns:
        Feasible derivation with `value_m` (millimetre-rounded), or infeasible
        with `reason`.
    """
    passer = frame.find_robot(passer_id)
    if passer is None:
        return Derivation(feasible=False, reason=f"passer {passer_id} not in snapshot")
    if geometry is None:
        along = project_progress((passer.x, passer.y), yielder_parked_xy, passer.theta)
    else:
        along = passer_travel_m(
            passer_id, (passer.x, passer.y), yielder_parked_xy, geometry, yielder_id
        )
    required = along + maneuver_limits(params, geometry).escort_clearance_m
    low, high = params.escort_band_m
    if required < low - _EPS or required > high + _EPS:
        return Derivation(
            feasible=False,
            reason=f"required escort {required:.3f} m outside band [{low}, {high}] m",
        )
    return Derivation(feasible=True, value_m=round(required, 3))


def derive_queued_passer_clearance(
    frame: SnapshotFrame,
    passer_id: str,
    yielder_parked_xy: tuple[float, float],
    params: GroundingParams,
    *,
    geometry: SceneGeometry | None = None,
    yielder_id: str | None = None,
) -> Derivation:
    """Clearance for a later passer of a multi-passer yield (not the first).

    Measured exactly as `derive_escort_distance` measures the first passer's,
    but with no upper band: the band sizes ONE passer against the hold
    backstop, and a queued passer is farther back by construction, so a
    clamped or refused clearance would end its crossing before it is past the
    parked yielder. The backstops scale with the passers' budget instead, as
    the legacy grounder does. Floored at the band's lower bound.

    Args:
        frame: Current scene snapshot.
        passer_id: The queued passer.
        yielder_parked_xy: World position the yielder retreats to.
        params: Geometry parameters.
        geometry: Declared scene geometry, or None.
        yielder_id: The yielder, as for `derive_escort_distance`.

    Returns:
        Feasible derivation with `value_m` (millimetre-rounded), or infeasible
        with `reason` when the passer is not in the snapshot.
    """
    passer = frame.find_robot(passer_id)
    if passer is None:
        return Derivation(feasible=False, reason=f"passer {passer_id} not in snapshot")
    if geometry is None:
        along = project_progress((passer.x, passer.y), yielder_parked_xy, passer.theta)
    else:
        along = passer_travel_m(
            passer_id, (passer.x, passer.y), yielder_parked_xy, geometry, yielder_id
        )
    required = along + maneuver_limits(params, geometry).escort_clearance_m
    return Derivation(feasible=True, value_m=round(max(params.escort_band_m[0], required), 3))


def load_grounding_params(path: Path = Path("config/rag.yaml")) -> GroundingParams:
    """Load the `grounding:` section of the RAG config.

    Args:
        path: YAML config path.

    Returns:
        Validated params; an absent or empty section yields the defaults
        (`mode="legacy"`).

    Raises:
        FileNotFoundError: If `path` does not exist.
        pydantic.ValidationError: If the section has unknown keys or
            out-of-range values.
    """
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return GroundingParams(**(raw.get("grounding") or {}))


def _axis_index(geometry: SceneGeometry) -> int:
    return 0 if geometry.corridor.axis == "x" else 1


def _yield_side(
    yielder: RobotStateInput, passer: RobotStateInput, geometry: SceneGeometry
) -> tuple[int, float, SceneGeometry]:
    # (axis index, retreat side, corridor geometry) of the yielder: its
    # declared junction arm when it has one, else the passer-relative rule.
    resolved, arm_side = arm_geometry(geometry, yielder.robot_id)
    axis_index = _axis_index(resolved)
    if arm_side is not None:
        return axis_index, arm_side, resolved
    return axis_index, _retreat_side(yielder, passer, axis_index), resolved


def _retreat_side(yielder: RobotStateInput, passer: RobotStateInput, axis_index: int) -> float:
    # Identical to the legacy grounder and the feasibility gate, ties included.
    yielder_coord = (yielder.x, yielder.y)[axis_index]
    passer_coord = (passer.x, passer.y)[axis_index]
    return -1.0 if yielder_coord < passer_coord else 1.0


def _backup_clearance_m(
    yielder_id: str, params: GroundingParams, geometry: SceneGeometry | None
) -> float:
    # J2: a yielder retreating along a declared junction arm clears to the
    # scene's junction-scoped value instead of the shipped head-on tuning
    # (design study 2026-09-29 S1, section 3).
    if (
        geometry is not None
        and geometry.junction_backup_clearance_m is not None
        and (geometry.arms or {}).get(yielder_id) is not None
    ):
        return geometry.junction_backup_clearance_m
    return params.backup_clearance_m


def _clearance_robots(
    yielder: RobotStateInput,
    others: list[RobotStateInput],
    axes: RetreatAxes,
    geometry: SceneGeometry | None,
) -> list[RobotStateInput]:
    # The robots `derive_backup_distance` holds the clearance against. Only
    # the footprint band filters; declared scenes keep the frozen v2 rule
    # (every crossing robot).
    if geometry is None or geometry.rear_room_band != "footprint":
        return others
    lane = geometry.lane_robots or ()
    return [
        state
        for index, state in enumerate(others)
        if index == 0
        or state.robot_id in lane
        or _in_swept_corridor(yielder, state, axes, geometry)
    ]


def _in_swept_corridor(
    yielder: RobotStateInput, state: RobotStateInput, axes: RetreatAxes, geometry: SceneGeometry
) -> bool:
    # The corridor is the room fix's footprint logic applied to a robot: the
    # two bodies overlap laterally within both half-widths, plus the drift
    # margin the room gate also adds (0.38 m either side for S1).
    corridor_m = 2.0 * geometry.robot.half_width_m + FEASIBILITY_MARGIN_M
    lateral = (state.x - yielder.x) * axes.left[0] + (state.y - yielder.y) * axes.left[1]
    return abs(lateral) <= corridor_m + _EPS


def lane_conflict_robot_ids(
    frame: SnapshotFrame,
    yielder_id: str,
    robot_ids: Sequence[str],
    geometry: SceneGeometry | None,
    params: GroundingParams | None = None,
) -> list[str] | None:
    """The robots of a dynamic lane yield's conflict, among `robot_ids`.

    A lane view (`geometry.lane_robots`, footprint band) is derived from one
    pair; the conflict it describes is that pair plus any robot inside the
    yielder's swept corridor, the rule `derive_backup_distance` holds its
    clearance to: `2 * robot.half_width_m + FEASIBILITY_MARGIN_M` either side
    of the retreat line through the yielder. A robot farther aside (S1's
    N-arm queue beside an E-W lane) is not in the conflict.

    With `params` the corridor is also bounded behind the yielder by the
    clearance's reach: a robot at least `backup_band_m[1]` plus the backup
    clearance back along the retreat axis can never bind an in-band backup
    (its clearance interval misses the band), so it is not in the conflict
    either (S1 ep1: a robot dwelling at the W node 4.2 m behind the E-bay
    yielder). This drops nothing `derive_backup_distance` could hold its
    clearance to. Corridor robots ahead of the yielder (the partner's side,
    the passer queue) are never bounded.

    Args:
        frame: Current scene snapshot.
        yielder_id: The yield's (post-gate) yielder.
        robot_ids: Candidate robots, e.g. the crossing order.
        geometry: The geometry the yield is grounded on.
        params: Grounding parameters bounding the corridor behind the
            yielder; None leaves it unbounded.

    Returns:
        The robots of `robot_ids` in the conflict, in their given order: the
        yielder's lane partner, any robot inside the corridor, and any robot
        missing from `frame` (it cannot be placed, so it is not dropped).
        None when this is not a lane view the yielder belongs to (declared
        or crossing geometry, the yielder not in the lane pair) or the
        yielder or its partner is not in `frame`: nothing is scoped then.
    """
    if (
        geometry is None
        or geometry.rear_room_band != "footprint"
        or geometry.lane_robots is None
        or yielder_id not in geometry.lane_robots
    ):
        return None
    partner_id = next(rid for rid in geometry.lane_robots if rid != yielder_id)
    yielder = frame.find_robot(yielder_id)
    axes = retreat_axes(frame, yielder_id, partner_id, geometry)
    if yielder is None or axes is None:
        return None
    reach_m = (
        None
        if params is None
        else params.backup_band_m[1] + _backup_clearance_m(yielder_id, params, geometry)
    )
    kept = []
    for robot_id in robot_ids:
        state = frame.find_robot(robot_id)
        if robot_id == partner_id or state is None:
            kept.append(robot_id)
            continue
        if not _in_swept_corridor(yielder, state, axes, geometry):
            continue
        behind_m = (state.x - yielder.x) * axes.retreat[0] + (state.y - yielder.y) * axes.retreat[1]
        if reach_m is None or behind_m < reach_m - _EPS:
            kept.append(robot_id)
    return kept


def _park_backup_floor_m(
    yielder: RobotStateInput, passer: RobotStateInput, geometry: SceneGeometry
) -> float:
    # Rounded like the legacy park_coord so both paths land on the same
    # millimetre; a yielder already past its park point needs no floor.
    axis_index, side, resolved = _yield_side(yielder, passer, geometry)
    park_coord = round(resolved.corridor.center_m + side * park_offset_m(resolved), 3)
    yielder_coord = (yielder.x, yielder.y)[axis_index]
    return max(0.0, (park_coord - yielder_coord) * side)


# ---- junction_clear cost-ranked recede selection (prereg-v2 (a) Grounding) ----


def recede_axis_offset_m(
    position: tuple[float, float], arm: ArmGeometry, geometry: SceneGeometry
) -> float:
    """Signed progress of `position` outward along its own declared arm.

    The same axis convention `arm_geometry`/`derive_backup_distance` use:
    positive is outward on the arm's own `side`, measured from the corridor
    centre. A recede target (`SceneGeometry.junction_recede_offset_m`) and a
    candidate's current position are compared in this one coordinate.

    Args:
        position: World-frame `(x, y)` in metres.
        arm: The robot's declared arm.
        geometry: Declared scene geometry (for the corridor centre).

    Returns:
        Signed offset in metres; positive means already on the arm's own
        outward side of the junction centre.
    """
    axis_index = 0 if arm.axis == "x" else 1
    return (position[axis_index] - geometry.corridor.center_m) * arm.side


def recede_pocket_offset_m(geometry: SceneGeometry, rank: int) -> float | None:
    """The pocket offset for the `rank`-th recede candidate in chi order.

    `junction_recede_offset_m - rank * junction_recede_stagger_m` (step-7b
    ruling (iv), `SceneGeometry.junction_recede_stagger_m`); every rank
    shares `junction_recede_offset_m` when no stagger is declared.

    Args:
        geometry: Declared scene geometry.
        rank: Zero-based position in chi order (0 is the lead).

    Returns:
        The offset in metres, or None when no pocket is declared.

    Raises:
        ValueError: If `rank` is negative or the staggered pocket would sit
            at or inside the junction centre.
    """
    if rank < 0:
        raise ValueError(f"rank must be >= 0, got {rank}")
    offset_m = geometry.junction_recede_offset_m
    if offset_m is None:
        return None
    stagger_m = geometry.junction_recede_stagger_m or 0.0
    pocket_m = round(offset_m - rank * stagger_m, 3)
    if pocket_m <= 0.0:
        raise ValueError(f"staggered recede pocket for rank {rank} is {pocket_m} m, not outward")
    return pocket_m


def recede_distance_m(
    frame: SnapshotFrame,
    robot_id: str,
    geometry: SceneGeometry,
    *,
    offset_m: float | None = None,
) -> float | None:
    """D_SPACE: outstanding straight-line distance to the declared recede pocket.

    Unlike `derive_backup_distance`'s clearance-band search, this is plain
    arithmetic against a DECLARED target (`SceneGeometry.
    junction_recede_offset_m`, the intersection-resolvability study's C'
    owner-override |y| ~= 1.2 m): the pocket is a scene constant, not derived
    from another robot's position.

    Args:
        frame: Current scene snapshot.
        robot_id: Candidate recede robot.
        geometry: Declared scene geometry.
        offset_m: The pocket offset to measure against, for a staggered
            pocket (`recede_pocket_offset_m`); None uses the unstaggered
            `geometry.junction_recede_offset_m`, which chi ranking always
            does. Ignored when no pocket is declared at all.

    Returns:
        None when `robot_id` has no declared arm, is absent from `frame`, or
        `geometry.junction_recede_offset_m` is unset -- each means "not a
        recede candidate under this geometry", not a zero cost. Otherwise the
        outstanding distance in metres, floored at 0.0 for a robot already
        past its pocket, rounded to the millimetre.
    """
    state = frame.find_robot(robot_id)
    arm = (geometry.arms or {}).get(robot_id)
    declared_m = geometry.junction_recede_offset_m
    if state is None or arm is None or declared_m is None:
        return None
    target_m = declared_m if offset_m is None else offset_m
    current = recede_axis_offset_m((state.x, state.y), arm, geometry)
    return max(0.0, round(target_m - current, 3))


def is_at_recede_pocket(
    frame: SnapshotFrame,
    robot_id: str,
    geometry: SceneGeometry,
    params: GroundingParams,
) -> bool:
    """Whether `robot_id` already sits within `junction_recede_tolerance_m` of its pocket.

    Args:
        frame: Current scene snapshot.
        robot_id: Candidate recede robot.
        geometry: Declared scene geometry.
        params: Grounding parameters (the tolerance).

    Returns:
        False when `robot_id` is not a recede candidate under this geometry
        (`recede_distance_m` returns None), never True by default.
    """
    distance = recede_distance_m(frame, robot_id, geometry)
    return distance is not None and distance <= params.junction_recede_tolerance_m


def recede_follower_count(frame: SnapshotFrame, robot_id: str, geometry: SceneGeometry) -> int:
    """N_f: other tracked robots queued farther out on `robot_id`'s own arm.

    A-DRIVE's (arXiv:2204.04910) "followers stacked behind" the robot that
    would recede: other robots declared on the SAME arm (axis AND side)
    whose own outward offset (`recede_axis_offset_m`) is strictly greater --
    they sit between `robot_id` and its recede pocket, in the way of a
    straight recede outward.

    Args:
        frame: Current scene snapshot.
        robot_id: Candidate recede robot.
        geometry: Declared scene geometry.

    Returns:
        0 when `robot_id` has no declared arm or is absent from `frame`.
    """
    state = frame.find_robot(robot_id)
    arm = (geometry.arms or {}).get(robot_id)
    if state is None or arm is None:
        return 0
    own_offset = recede_axis_offset_m((state.x, state.y), arm, geometry)
    count = 0
    for other in frame.robots:
        if other.robot_id == robot_id:
            continue
        other_arm = (geometry.arms or {}).get(other.robot_id)
        if other_arm is None or other_arm.axis != arm.axis or other_arm.side != arm.side:
            continue
        if recede_axis_offset_m((other.x, other.y), other_arm, geometry) > own_offset:
            count += 1
    return count


def recede_cost(
    frame: SnapshotFrame,
    robot_id: str,
    geometry: SceneGeometry,
    params: GroundingParams,
) -> float | None:
    """chi = s * D_SPACE + t * N_f (prereg-v2 (a) Grounding, A-DRIVE arXiv:2204.04910).

    Args:
        frame: Current scene snapshot.
        robot_id: Candidate recede robot.
        geometry: Declared scene geometry.
        params: Grounding parameters (the chi weights).

    Returns:
        None when `robot_id` is not a recede candidate under this geometry
        (`recede_distance_m` returns None); otherwise the cost, lower is
        cheaper/preferred, rounded to six places.
    """
    distance = recede_distance_m(frame, robot_id, geometry)
    if distance is None:
        return None
    followers = recede_follower_count(frame, robot_id, geometry)
    return round(
        params.junction_recede_cost_space_weight * distance
        + params.junction_recede_cost_follower_weight * followers,
        6,
    )


def rank_recede_candidates(
    frame: SnapshotFrame,
    candidate_ids: Sequence[str],
    geometry: SceneGeometry,
    params: GroundingParams,
) -> list[str]:
    """Rank recede candidates ascending by chi (cheapest/preferred first).

    Single recede by default: the first entry is M3's preferred lone
    yielder-equivalent. A two-robot (or more) staggered sequential recede
    (`command_grounder.ground_junction_clear_phases`) simply takes this
    order's next entry once the previous one is confirmed at its pocket --
    never simultaneous.

    Args:
        frame: Current scene snapshot.
        candidate_ids: Robots to rank.
        geometry: Declared scene geometry.
        params: Grounding parameters (chi weights, tolerance).

    Returns:
        `candidate_ids` filtered to those with a resolvable cost (a
        candidate `recede_cost` returns None for is not a recede candidate at
        all under the current geometry, so it is dropped rather than ranked
        last), ordered ascending by chi; ties break by robot_id so the order
        is deterministic.
    """
    scored = [
        (robot_id, recede_cost(frame, robot_id, geometry, params)) for robot_id in candidate_ids
    ]
    ranked = sorted(
        ((robot_id, cost) for robot_id, cost in scored if cost is not None),
        key=lambda pair: (pair[1], pair[0]),
    )
    return [robot_id for robot_id, _ in ranked]


def recede_orders_equivalent(
    frame: SnapshotFrame,
    first: Sequence[str],
    second: Sequence[str],
    geometry: SceneGeometry,
    params: GroundingParams,
) -> bool:
    """Whether two recede orders are one χ-epsilon equivalence class.

    The χ-epsilon verbatim rule (prereg-v2 (a0), RULED 2026-10-03): two
    orders of the SAME recede set are equivalent when every pair of robots
    they order differently has a χ margin strictly below
    `params.junction_recede_order_epsilon`. Identical orders are trivially
    equivalent. Used at verification only; dispatch follows
    `rank_recede_candidates` unless prereg-v3 R3.3's
    `plan_dispatch_order_source: model_when_verified` dispatches a
    `vlm_verbatim` plan's own (thereby equivalent) order.

    Args:
        frame: Current scene snapshot (the one χ is ranked on).
        first: One recede order.
        second: The other recede order.
        geometry: Declared scene geometry.
        params: Grounding parameters (χ weights and the epsilon).

    Returns:
        False when the two orders name different robots, repeat a robot, or
        any robot in them has no resolvable χ (not a recede candidate).
    """
    if list(first) == list(second):
        return True
    if len(set(first)) != len(first) or sorted(first) != sorted(second):
        return False
    costs = {robot_id: recede_cost(frame, robot_id, geometry, params) for robot_id in first}
    if any(cost is None for cost in costs.values()):
        return False
    position = {robot_id: index for index, robot_id in enumerate(second)}
    for i, a in enumerate(first):
        for b in first[i + 1 :]:
            if position[a] > position[b] and abs(costs[a] - costs[b]) >= (
                params.junction_recede_order_epsilon
            ):
                return False
    return True

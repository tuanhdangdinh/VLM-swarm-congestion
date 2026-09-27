"""Pillar 1: derived maneuver distances for derived-mode grounding (rev-8 A.2).

The physical quantities (park point, sidestep, escort clearance, safety radius)
come from `reasoning.rag.scene_geometry` whenever the caller declares a scene
geometry, so derived and legacy grounding share one derivation. The constants
on `GroundingParams` are the fallbacks for callers without one.
"""

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from reasoning.rag.scene_geometry import (
    SceneGeometry,
    park_offset_m,
    passer_clearance_m,
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
    hold_backstop_sec: float = Field(default=45.0, gt=0)
    wait_backstop_sec: float = Field(default=120.0, gt=0)
    resolution_backstop_sec: float = Field(default=150.0, gt=0)

    @model_validator(mode="after")
    def _check_bands(self) -> "GroundingParams":
        bands = {"backup_band_m": self.backup_band_m, "escort_band_m": self.escort_band_m}
        if self.aisle_y_band_m is not None:
            bands["aisle_y_band_m"] = self.aisle_y_band_m
        for name, (low, high) in bands.items():
            if low > high:
                raise ValueError(f"{name} lower bound {low} exceeds upper bound {high}")
        for name in ("backup_band_m", "escort_band_m"):
            if bands[name][0] < 0:
                raise ValueError(f"{name} must be non-negative, got {bands[name]}")
        return self


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
        axis_index = _axis_index(geometry)
        side = _retreat_side(yielder, passer, axis_index)
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
) -> Derivation:
    """Minimum in-band retreat distance clearing every crossing robot.

    Finds the smallest `d` in `params.backup_band_m` such that the
    retreat-axis-projected separation to every robot in `other_ids` is at
    least `params.backup_clearance_m`. With a declared geometry `d` must also
    reach the yielder's park point (`scene_geometry.park_offset_m` from the
    corridor centre, on the yielder's own side), which keeps the parked marker
    clear of the occluder's projection. Out-of-band requirements are
    infeasible, never clamped (rev-8 A.2).

    The minimum is exact rather than scanned: the feasible set is the band
    minus one open interval `(s - c, s + c)` per robot, so its minimum is the
    band's lower bound or some `s + c`.

    Args:
        frame: Current scene snapshot.
        yielder_id: Robot that retreats.
        other_ids: Robots in the crossing order (all must be present); with a
            geometry the first one fixes the retreat side.
        params: Geometry parameters.
        geometry: Declared scene geometry, or None for the heading-based frame.

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
        for state in others
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
    start = max(low, floor)
    clearance = params.backup_clearance_m
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
) -> Derivation:
    """Escort distance placing the passer past the parked yielder (rev-8 A.2).

    The distance from the passer's current position to the yielder's parked
    position, plus the escort clearance from `maneuver_limits`. Without a
    geometry it is measured along the passer's own heading (signed, so a
    passer facing away is infeasible); with one, along `corridor.axis`,
    exactly as the legacy grounder measures it. Out-of-band requirements are
    infeasible, never truncated.

    Args:
        frame: Current scene snapshot.
        passer_id: Robot escorted through the conflict.
        yielder_parked_xy: World position the yielder retreats to.
        params: Geometry parameters.
        geometry: Declared scene geometry, or None.

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
        axis_index = _axis_index(geometry)
        along = abs((passer.x, passer.y)[axis_index] - yielder_parked_xy[axis_index])
    required = along + maneuver_limits(params, geometry).escort_clearance_m
    low, high = params.escort_band_m
    if required < low - _EPS or required > high + _EPS:
        return Derivation(
            feasible=False,
            reason=f"required escort {required:.3f} m outside band [{low}, {high}] m",
        )
    return Derivation(feasible=True, value_m=round(required, 3))


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


def _retreat_side(yielder: RobotStateInput, passer: RobotStateInput, axis_index: int) -> float:
    # Identical to the legacy grounder and the feasibility gate, ties included.
    yielder_coord = (yielder.x, yielder.y)[axis_index]
    passer_coord = (passer.x, passer.y)[axis_index]
    return -1.0 if yielder_coord < passer_coord else 1.0


def _park_backup_floor_m(
    yielder: RobotStateInput, passer: RobotStateInput, geometry: SceneGeometry
) -> float:
    # Rounded like the legacy park_coord so both paths land on the same
    # millimetre; a yielder already past its park point needs no floor.
    axis_index = _axis_index(geometry)
    side = _retreat_side(yielder, passer, axis_index)
    park_coord = round(geometry.corridor.center_m + side * park_offset_m(geometry), 3)
    yielder_coord = (yielder.x, yielder.y)[axis_index]
    return max(0.0, (park_coord - yielder_coord) * side)

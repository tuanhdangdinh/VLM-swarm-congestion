"""Pillar 2: retreat-candidate generation, swept validation, ranking (rev-8 A.3).

`rank_candidates(...)[0]` is simultaneously the stage-2 default, the stage-2
fallback, and Arm B's stage-2 answer: the classical control and the VLM choose
from the same validated set.
"""

import math
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.maneuver_geometry import GroundingParams, maneuver_limits, retreat_axes
from reasoning.rag.scene_geometry import SceneGeometry, across_m, arm_geometry
from reasoning.vlm.models import RobotStateInput, SnapshotFrame, StaticObstacleInput

_LABELS = ("A", "B", "C", "D")
_EPS = 1e-9


class RetreatCandidate(BaseModel):
    """One validated retreat pose offered to the stage-2 set-of-mark call."""

    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1, max_length=1)
    # World-frame pose after the backup and the sidestep.
    x: float
    y: float
    backup_m: float
    # Signed robot-frame lateral offset (positive = left), as M4 executes it.
    lateral_m: float
    # Minimum distance to any other robot over the whole swept path, and over
    # the sidestep segment alone. None when no other robot is in the frame.
    min_sweep_clearance_m: float | None
    lateral_clearance_m: float | None


def generate_retreat_candidates(
    frame: SnapshotFrame,
    yielder_id: str,
    backup_m: float,
    params: GroundingParams,
    *,
    geometry: SceneGeometry | None = None,
    passer_id: str | None = None,
    static_obstacles: Sequence[StaticObstacleInput] = (),
) -> list[RetreatCandidate]:
    """Generate swept-path-validated retreat candidates for the yielder.

    Candidates are left/right/far-left/far-right sidesteps (1x and 2x the
    lateral magnitude) at the derived backup distance. The backup and
    sidestep segments are sampled at `params.sweep_step_m`; every sample must
    clear every other robot and stay inside the aisle band when one applies
    (rev-8 A.3).

    The per-robot clearance floor is `min(min_distance, starting
    separation)`: a deadlock's pre-existing sub-threshold separation must not
    veto the retreat that resolves it; the sweep must simply never make any
    separation worse than that floor.

    With a declared geometry, the lateral magnitude, safety radius and retreat
    axis come from it (`maneuver_limits`, `retreat_axes`), and unless
    `params.aisle_y_band_m` overrides it the aisle band is the yielder's lane
    widened by `pull_off_lateral_m` either side, perpendicular to the
    corridor (the yielder's own junction arm, when declared), which leaves
    only the 1x variants. `aisle_y_band_m` is a world y band, so it suits only
    yielders retreating along x; a yielder whose own arm runs along y takes
    `params.aisle_x_band_m` (a world x band) instead when one is set.

    Under a dynamic-arms view (`geometry.rear_room_band == "footprint"`)
    every sample must also stay out of each static obstacle grown by the
    robot's `half_width_m` plus `params.retreat_box_margin_m` (a box the
    yielder already sits inside that grown box may not be entered deeper,
    but is no veto). There the yield gate checks rear room across the
    footprint only up to the park point, while the executed backup is sized
    by the passer clearance and can run past it, and the sidestep can land in
    a box inside the aisle (the A55-E gate jaws). Declared scenes skip this
    check, so their candidates are unchanged.

    Args:
        frame: Current scene snapshot.
        yielder_id: Robot that retreats.
        backup_m: Derived backup distance (Pillar 1).
        params: Geometry parameters.
        geometry: Declared scene geometry, or None.
        passer_id: First robot to cross; required with a geometry, since it
            fixes the retreat side.
        static_obstacles: Fixed obstacles of the running scenario, checked
            only under a footprint-band geometry.

    Returns:
        Surviving candidates labeled A.. in generation order; empty when the
        yielder or passer is absent, the aisle leaves no room to step aside,
        or nothing validates.

    Raises:
        ValueError: If `geometry` is given without `passer_id`.
    """
    if geometry is not None and passer_id is None:
        raise ValueError("passer_id is required when a geometry fixes the retreat side")
    yielder = frame.find_robot(yielder_id)
    axes = retreat_axes(frame, yielder_id, passer_id, geometry)
    if yielder is None or axes is None:
        return []
    limits = maneuver_limits(params, geometry)
    if limits.lateral_m <= 0.0:
        return []
    others = [state for state in frame.robots if state.robot_id != yielder_id]
    band = _aisle_band(yielder, params, geometry, limits.lateral_m)
    lane_bands = _heading_lane_bands(yielder, params, geometry, limits.lateral_m)
    start = (yielder.x, yielder.y)
    # Each box's floor is how deep the yielder already sits in it (0 when
    # clear), like the robot-clearance floor below: a robot pinned on a rack
    # corner may retreat along or away from the contact, never deeper.
    boxes = [
        (box, max(0.0, _depth(start, box)))
        for box in (
            _grown_boxes(
                static_obstacles, geometry.robot.half_width_m + params.retreat_box_margin_m
            )
            if geometry is not None and geometry.rear_room_band == "footprint"
            else []
        )
    ]
    parked = (start[0] + backup_m * axes.retreat[0], start[1] + backup_m * axes.retreat[1])
    backup_samples = _sample_segment(start, parked, params.sweep_step_m)

    survivors: list[RetreatCandidate] = []
    lateral = limits.lateral_m
    for offset in (lateral, -lateral, 2 * lateral, -2 * lateral):
        end = (parked[0] + offset * axes.left[0], parked[1] + offset * axes.left[1])
        lateral_samples = _sample_segment(parked, end, params.sweep_step_m)
        samples = backup_samples + lateral_samples
        if lane_bands is not None:
            if any(
                not (low - _EPS <= sample[0] * unit[0] + sample[1] * unit[1] <= high + _EPS)
                for unit, low, high in lane_bands
                for sample in samples
            ):
                continue
        elif band is not None:
            index, low, high = band
            if any(not (low - _EPS <= sample[index] <= high + _EPS) for sample in samples):
                continue
        if any(
            _depth(sample, box) > floor + _EPS for sample in samples for box, floor in boxes
        ):
            continue
        if not _sweep_clears(samples, others, limits.min_distance_m):
            continue
        survivors.append(
            RetreatCandidate(
                label=_LABELS[len(survivors)],
                x=end[0],
                y=end[1],
                backup_m=backup_m,
                lateral_m=offset,
                min_sweep_clearance_m=_min_clearance(samples, others),
                lateral_clearance_m=_min_clearance(lateral_samples, others),
            )
        )
    return survivors


def reletter_candidates(candidates: list[RetreatCandidate]) -> list[RetreatCandidate]:
    """Re-letter a subset of validated candidates A.. as their sweep would.

    `generate_retreat_candidates` letters only its survivors, in generation
    order; a later veto of some candidates re-letters the rest the same way,
    so the letters stay contiguous and positional.

    Args:
        candidates: Candidates from one `generate_retreat_candidates` call,
            in any order (e.g. ranked).

    Returns:
        New list in the same order, lettered by generation (old label) order.
    """
    letters = {
        candidate.label: _LABELS[index]
        for index, candidate in enumerate(sorted(candidates, key=lambda c: c.label))
    }
    return [
        candidate.model_copy(update={"label": letters[candidate.label]})
        for candidate in candidates
    ]


def rank_candidates(
    candidates: list[RetreatCandidate],
    transit_axis_theta: float,
    yielder_xy: tuple[float, float],
) -> list[RetreatCandidate]:
    """Deterministic geometry ranking; `ranked[0]` is the default candidate.

    Sort by sidestep clearance (descending), then distance from the transit
    corridor (descending: farther off the corridor is better), then label.
    The backup segment is shared by every candidate, so its clearance cannot
    discriminate between them; validation covers it, ranking does not.

    Args:
        candidates: Validated candidates from `generate_retreat_candidates`.
        transit_axis_theta: Heading of the conflict's transit axis.
        yielder_xy: Yielder position defining the corridor line.

    Returns:
        New list, best candidate first.
    """

    def corridor_distance(candidate: RetreatCandidate) -> float:
        dx = candidate.x - yielder_xy[0]
        dy = candidate.y - yielder_xy[1]
        # Rounded so mirror-image candidates tie exactly and fall to the label.
        return round(
            abs(-math.sin(transit_axis_theta) * dx + math.cos(transit_axis_theta) * dy), 6
        )

    def clearance(candidate: RetreatCandidate) -> float:
        value = candidate.lateral_clearance_m
        return math.inf if value is None else value

    return sorted(
        candidates, key=lambda c: (-clearance(c), -corridor_distance(c), c.label)
    )


def _aisle_band(
    yielder: RobotStateInput,
    params: GroundingParams,
    geometry: SceneGeometry | None,
    lateral_m: float,
) -> tuple[int, float, float] | None:
    # (coordinate index, low, high) the swept path must stay inside.
    if params.aisle_x_band_m is not None and geometry is not None:
        # Own-arm pattern: only a yielder retreating along y is bounded by
        # the world x band; everyone else keeps the bands below unchanged.
        if arm_geometry(geometry, yielder.robot_id)[0].corridor.axis == "y":
            return (0, *params.aisle_x_band_m)
    if params.aisle_y_band_m is not None:
        return (1, *params.aisle_y_band_m)
    if geometry is None:
        return None
    # The corridor declares no perpendicular centre; like the feasibility
    # gate's lateral band, it is taken at the yielder's own coordinate, across
    # the yielder's own junction arm when it has one.
    corridor = arm_geometry(geometry, yielder.robot_id)[0].corridor
    perp_index = 1 if corridor.axis == "x" else 0
    centre = (yielder.x, yielder.y)[perp_index]
    return (perp_index, centre - lateral_m, centre + lateral_m)


def _heading_lane_bands(
    yielder: RobotStateInput,
    params: GroundingParams,
    geometry: SceneGeometry | None,
    lateral_m: float,
) -> list[tuple[tuple[float, float], float, float]] | None:
    # The `_aisle_band` rule for a heading lane (A20(2)), as (unit, low, high)
    # bands on `sample . unit`. A diagonal backup moves on both world axes, so
    # every declared world band applies; with none declared, the band is the
    # lane widened by `lateral_m` either side, across the lane's own heading.
    # None when the geometry is not a heading lane.
    if geometry is None or geometry.lane_heading_rad is None:
        return None
    bands: list[tuple[tuple[float, float], float, float]] = []
    if params.aisle_x_band_m is not None:
        bands.append(((1.0, 0.0), *params.aisle_x_band_m))
    if params.aisle_y_band_m is not None:
        bands.append(((0.0, 1.0), *params.aisle_y_band_m))
    if bands:
        return bands
    heading = geometry.lane_heading_rad
    left = (-math.sin(heading), math.cos(heading))
    centre = across_m(geometry, (yielder.x, yielder.y))
    return [(left, centre - lateral_m, centre + lateral_m)]


def _grown_boxes(
    obstacles: Sequence[StaticObstacleInput], margin_m: float
) -> list[tuple[float, float, float, float]]:
    # (x_min, x_max, y_min, y_max) of each box grown by the robot's half-width,
    # so a sample (the robot centre) inside one means the body overlaps it.
    # Samples are `sweep_step_m` apart; every declared box is far thicker
    # than a step once grown, so none can fall between two samples.
    return [
        (
            o.x - o.size_x_m / 2.0 - margin_m,
            o.x + o.size_x_m / 2.0 + margin_m,
            o.y - o.size_y_m / 2.0 - margin_m,
            o.y + o.size_y_m / 2.0 + margin_m,
        )
        for o in obstacles
    ]


def _depth(sample: tuple[float, float], box: tuple[float, float, float, float]) -> float:
    # How far the sample is inside the box: the shortest move out of it.
    # Zero or negative when outside, so a body exactly touching a face is
    # not an overlap.
    x_min, x_max, y_min, y_max = box
    return min(sample[0] - x_min, x_max - sample[0], sample[1] - y_min, y_max - sample[1])


def _sample_segment(
    p0: tuple[float, float], p1: tuple[float, float], step_m: float
) -> list[tuple[float, float]]:
    length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    count = max(1, math.ceil(length / step_m))
    return [
        (p0[0] + (p1[0] - p0[0]) * i / count, p0[1] + (p1[1] - p0[1]) * i / count)
        for i in range(count + 1)
    ]


def _sweep_clears(
    samples: list[tuple[float, float]],
    others: list[RobotStateInput],
    min_distance_m: float,
) -> bool:
    start = samples[0]
    for other in others:
        floor = min(min_distance_m, math.hypot(other.x - start[0], other.y - start[1]))
        for sx, sy in samples:
            if math.hypot(other.x - sx, other.y - sy) < floor - _EPS:
                return False
    return True


def _min_clearance(
    samples: list[tuple[float, float]], others: list[RobotStateInput]
) -> float | None:
    if not others:
        return None
    return round(
        min(math.hypot(other.x - sx, other.y - sy) for sx, sy in samples for other in others),
        3,
    )

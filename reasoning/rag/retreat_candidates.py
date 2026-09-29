"""Pillar 2: retreat-candidate generation, swept validation, ranking (rev-8 A.3).

`rank_candidates(...)[0]` is simultaneously the stage-2 default, the stage-2
fallback, and Arm B's stage-2 answer: the classical control and the VLM choose
from the same validated set.
"""

import math

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.maneuver_geometry import GroundingParams, maneuver_limits, retreat_axes
from reasoning.rag.scene_geometry import SceneGeometry, arm_geometry
from reasoning.vlm.models import RobotStateInput, SnapshotFrame

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
    yielders retreating along x.

    Args:
        frame: Current scene snapshot.
        yielder_id: Robot that retreats.
        backup_m: Derived backup distance (Pillar 1).
        params: Geometry parameters.
        geometry: Declared scene geometry, or None.
        passer_id: First robot to cross; required with a geometry, since it
            fixes the retreat side.

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
    start = (yielder.x, yielder.y)
    parked = (start[0] + backup_m * axes.retreat[0], start[1] + backup_m * axes.retreat[1])
    backup_samples = _sample_segment(start, parked, params.sweep_step_m)

    survivors: list[RetreatCandidate] = []
    lateral = limits.lateral_m
    for offset in (lateral, -lateral, 2 * lateral, -2 * lateral):
        end = (parked[0] + offset * axes.left[0], parked[1] + offset * axes.left[1])
        lateral_samples = _sample_segment(parked, end, params.sweep_step_m)
        samples = backup_samples + lateral_samples
        if band is not None:
            index, low, high = band
            if any(not (low - _EPS <= sample[index] <= high + _EPS) for sample in samples):
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

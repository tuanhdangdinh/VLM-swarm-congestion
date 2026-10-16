"""prereg-v3 A28(ii): an escort leg must clear the parked yielder's park point.

Live E20 (docs/reports/2026-10-12-shield-fix-and-minibatch.md §6): command
`6cf402ed` parked robot_1 at its retreat point (2.156, -1.428), then M4's
raw-cmd_vel escort drove robot_3 1.843 m east along y ~ -1.30. That line
passes ~0.13 m from the park point; the yielder-passer pair is exempt from
M4's min-distance latch, so robot_3 pushed robot_1 (GT minimum 0.109 m).
Nothing in M3 compared the escort line with the park point: the escort
distance only measures how far the passer must drive to get past it.

This module sweeps every escorted passer's escort leg exactly as M4 drives
it and measures the point-to-segment distance from the park point to it.
The leg mirrors M4 (`swarm_execution.crossing_chain.plan_crossing` and
`command_bus_node`'s `drive_heading` dispatch), restated because M3 must
not import M4:

- Start: the passer's decision-snapshot position. M4 turns in place, then
  drives from its pose at admission; the passer sits on its linked
  `temporary_wait` until then.
- Heading: with both `passer_escort_heading_rad` and
  `passer_escort_reference_yaw_rad` (`grounding_view.apply_escort_headings`)
  M4 turns by their difference from its odom yaw at admission and holds
  that line, so it drives the world heading `passer_escort_heading_rad`.
  Without them M4 drives odom yaw 0, the passer's spawn heading, which M3
  cannot see; the leg then runs the way the escort distance was measured:
  along `grounding_view.escort_axis` with a geometry, along the passer's
  own heading without one (`maneuver_geometry.derive_escort_distance`).
- Length: the dispatched escort distance (`passer_escort_distance_m`, then
  `crossing_escort_m` aligned with `crossing_order`, falling back to the
  passer's clearance as `plan_crossing` does). The odometry release at
  `passer_clear_m` / `crossing_clear_m` ends the hold, not the drive; the
  passer moves no farther under raw cmd_vel than its escort distance.

Scope: the yielder is taken at its PARK POINT (`retreat_x_m`,
`retreat_y_m`), as the ruling states; its backup and pull-off are over
before any passer is admitted (M4's crossing chain admits on the yield's
hold phase). The robot footprints are not added: `min_distance_m` is the
centre-to-centre latch radius the pair is exempt from.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from reasoning.rag.grounding_view import escort_axis
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import SnapshotFrame

ESCORT_HITS_PARK_REASON = "escort_hits_park"
# `plan_crossing`'s clearance when a yield names a passer but no
# `passer_clear_m` (`crossing_chain.DEFAULT_PASSER_CLEAR_M`).
_DEFAULT_PASSER_CLEAR_M = 1.5


class EscortLeg(BaseModel):
    """One escorted passer's straight raw-cmd_vel leg and its park-point clearance."""

    model_config = ConfigDict(frozen=True)

    passer_id: str
    start_xy: tuple[float, float]
    end_xy: tuple[float, float]
    # World-frame drive heading in radians.
    heading_rad: float
    distance_m: float
    # Point-to-segment distance from the park point to the leg, in metres.
    park_clearance_m: float


def point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    """Distance from a point to the closed segment `start`-`end`.

    Args:
        point: World `(x, y)` in metres.
        start: Segment start, world `(x, y)`.
        end: Segment end, world `(x, y)`.

    Returns:
        The distance in metres (to `start` for a zero-length segment).
    """
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_sq = dx * dx + dy * dy
    t = 0.0
    if length_sq > 0.0:
        t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_sq
        t = max(0.0, min(1.0, t))
    return math.hypot(point[0] - (start[0] + t * dx), point[1] - (start[1] + t * dy))


def _float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _aligned(values: Any, length: int) -> list[float] | None:
    if not isinstance(values, list) or len(values) != length:
        return None
    try:
        return [float(value) for value in values]
    except (TypeError, ValueError):
        return None


def _escort_plan(
    parameters: Mapping[str, Any],
) -> list[tuple[str, float, float | None, float | None]]:
    # `plan_crossing`, restated: (passer, escort_m, heading, reference) for
    # every escorted passer; empty when the first passer is not escorted.
    first = parameters.get("passer_robot_id")
    escort_m = _float(parameters.get("passer_escort_distance_m"))
    if not first or escort_m is None:
        return []
    plan = [
        (
            str(first),
            escort_m,
            _float(parameters.get("passer_escort_heading_rad")),
            _float(parameters.get("passer_escort_reference_yaw_rad")),
        )
    ]
    order = parameters.get("crossing_order")
    if (
        not isinstance(order, list)
        or len(order) < 2
        or not all(isinstance(robot_id, str) and robot_id for robot_id in order)
        or len(set(order)) != len(order)
        or order[0] != first
    ):
        return plan
    clear_m = _float(parameters.get("passer_clear_m"))
    clear_m = _DEFAULT_PASSER_CLEAR_M if clear_m is None else clear_m
    clears = _aligned(parameters.get("crossing_clear_m"), len(order))
    escorts = _aligned(parameters.get("crossing_escort_m"), len(order))
    headings = _aligned(parameters.get("crossing_escort_heading_rad"), len(order))
    references = _aligned(parameters.get("crossing_escort_reference_yaw_rad"), len(order))
    for position in range(1, len(order)):
        passer_clear = clears[position] if clears is not None else clear_m
        plan.append(
            (
                order[position],
                escorts[position] if escorts is not None else passer_clear,
                headings[position] if headings is not None else None,
                references[position] if references is not None else None,
            )
        )
    return plan


def escort_legs(
    yielder_id: str,
    parameters: Mapping[str, Any],
    snapshot: SnapshotFrame,
    geometry: SceneGeometry | None,
) -> list[EscortLeg]:
    """Every escorted passer's leg of a grounded yield, with its park clearance.

    Args:
        yielder_id: The yield's yielder.
        parameters: The yield's FINAL parameters (after
            `grounding_view.apply_escort_headings`), carrying `retreat_x_m`
            and `retreat_y_m`.
        snapshot: The decision snapshot the yield was grounded on.
        geometry: The geometry it was grounded on (the dynamic view when it
            fired), or None.

    Returns:
        One leg per escorted passer in crossing order; empty when the yield
        has no escort or no park point. A passer missing from the snapshot
        has no leg.
    """
    park_x, park_y = _float(parameters.get("retreat_x_m")), _float(parameters.get("retreat_y_m"))
    yielder = snapshot.find_robot(yielder_id)
    if park_x is None or park_y is None:
        return []
    legs: list[EscortLeg] = []
    for passer_id, distance_m, heading, reference in _escort_plan(parameters):
        passer = snapshot.find_robot(passer_id)
        if passer is None:
            continue
        if heading is not None and reference is not None:
            drive = heading
        elif geometry is None or yielder is None:
            drive = passer.theta
        else:
            axis, sign = escort_axis(passer, yielder, geometry)
            drive = (0.0 if sign > 0 else math.pi) if axis == "x" else sign * math.pi / 2
        start = (passer.x, passer.y)
        end = (
            passer.x + abs(distance_m) * math.cos(drive),
            passer.y + abs(distance_m) * math.sin(drive),
        )
        legs.append(
            EscortLeg(
                passer_id=passer_id,
                start_xy=start,
                end_xy=end,
                heading_rad=drive,
                distance_m=abs(distance_m),
                park_clearance_m=point_segment_distance((park_x, park_y), start, end),
            )
        )
    return legs


def escort_park_violations(
    yielder_id: str,
    parameters: Mapping[str, Any],
    snapshot: SnapshotFrame,
    geometry: SceneGeometry | None,
    min_distance_m: float,
) -> list[EscortLeg]:
    """The escort legs that pass within `min_distance_m` of the park point.

    A leg exactly `min_distance_m` from the park point clears it ("at least
    the latch radius", A28(ii)).

    Args:
        yielder_id: The yield's yielder.
        parameters: The yield's final parameters (see `escort_legs`).
        snapshot: The decision snapshot.
        geometry: The geometry the yield was grounded on, or None.
        min_distance_m: The latch radius (`GroundingParams.min_distance_m`).

    Returns:
        The violating legs in crossing order; empty when every leg clears.
    """
    return [
        leg
        for leg in escort_legs(yielder_id, parameters, snapshot, geometry)
        if leg.park_clearance_m < min_distance_m
    ]


def park_clearance_suffix(leg: EscortLeg) -> str:
    """One leg's tag suffix, shared by the infeasible and the filtered tags.

    Args:
        leg: A leg from `escort_park_violations`.

    Returns:
        `<passer>:<clearance m, 3 dp>`.
    """
    return f"{leg.passer_id}:{leg.park_clearance_m:.3f}"


def escort_hits_park_reason(leg: EscortLeg) -> str:
    """The `yield=infeasible:` reason for one violating leg.

    Args:
        leg: A leg from `escort_park_violations`.

    Returns:
        `escort_hits_park:<passer>:<clearance m, 3 dp>`.
    """
    return f"{ESCORT_HITS_PARK_REASON}:{park_clearance_suffix(leg)}"

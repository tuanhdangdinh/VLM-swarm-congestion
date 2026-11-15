"""Escort obstacle guard: an escort's straight leg must clear the declared static boxes.

Live demo take `m5D_t01_a1` (docs/reports/2026-11-15-escort-obstacle-guard.md):
decision `a15f3fc5` escorted robot_3 due west for 1.604 m from (1.354, 0.607),
straight through rack island `obstacle_2`. M4's escort publishes raw cmd_vel
below Nav2's collision monitor and ends only on distance or deadline, so the
robot drove into the island's east face and stayed pinned there. The escort
distance (`maneuver_geometry.derive_escort_distance`), heading and turn cap
(`grounding_view.apply_escort_headings`) and the A28(ii) park-point check
(`escort_clearance`) never compared the leg with the static obstacles.

This module sweeps each escorted passer's leg, built exactly as the park
check builds it (`escort_clearance.escort_drives`: snapshot start, the
dispatched heading and distance), against every declared static obstacle
grown by `robot.half_width_m + GroundingParams.retreat_box_margin_m`: the
footprint and margin the retreat-candidate sweep already uses
(`retreat_candidates.generate_retreat_candidates`). A centre inside a grown
box means the body is within the margin of the bare box.

Rules, mirroring the retreat sweep:

- The centreline is clipped exactly against each grown box, not sampled, so
  a corner clip shorter than `sweep_step_m` is still caught.
- Touching a grown face (depth zero) is the margin met exactly, not an
  overlap.
- A passer that already starts inside a grown box may move along or away
  from it, never deeper (the retreat sweep's depth floor): a robot parked
  near a rack is not vetoed for being there.

Scope: declared boxes only (`static_obstacles`, which in the S1b floors also
carry the four walls). Undeclared geometry, such as an aisle barrier built
from the scenario yaml, is not seen. Without a scene geometry there is no
footprint, and nothing is checked.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from reasoning.rag.escort_clearance import escort_drives
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import SnapshotFrame, StaticObstacleInput

ESCORT_HITS_OBSTACLE_REASON = "escort_hits_obstacle"
_EPS = 1e-9


class ObstacleBox(BaseModel):
    """One declared static obstacle grown by the swept footprint and margin."""

    model_config = ConfigDict(frozen=True)

    obstacle_id: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """`(x_min, x_max, y_min, y_max)` in world metres."""
        return (self.x_min, self.x_max, self.y_min, self.y_max)


class EscortObstacleHit(BaseModel):
    """One escort leg whose swept footprint enters a declared obstacle."""

    model_config = ConfigDict(frozen=True)

    passer_id: str
    obstacle_id: str
    start_xy: tuple[float, float]
    # World-frame drive heading in radians.
    heading_rad: float
    # The dispatched escort distance.
    distance_m: float
    # How far along the leg the passer can drive before its grown footprint
    # enters the obstacle (0.0 when it starts inside and heads deeper).
    clear_m: float


def escort_obstacle_margin_m(geometry: SceneGeometry, params: GroundingParams) -> float:
    """The amount each declared box is grown by for the sweep.

    Args:
        geometry: The geometry the yield was grounded on.
        params: Grounding parameters (`retreat_box_margin_m`).

    Returns:
        `geometry.robot.half_width_m + params.retreat_box_margin_m`, the
        retreat-candidate sweep's box growth.
    """
    return geometry.robot.half_width_m + params.retreat_box_margin_m


def grown_obstacle_boxes(
    static_obstacles: Sequence[StaticObstacleInput], margin_m: float
) -> list[ObstacleBox]:
    """Grow every declared obstacle by `margin_m` on each side.

    Args:
        static_obstacles: Fixed, axis-aligned obstacles of the running scenario.
        margin_m: Growth per side in metres.

    Returns:
        One grown box per obstacle, in declaration order.
    """
    return [
        ObstacleBox(
            obstacle_id=o.obstacle_id,
            x_min=o.x - o.size_x_m / 2.0 - margin_m,
            x_max=o.x + o.size_x_m / 2.0 + margin_m,
            y_min=o.y - o.size_y_m / 2.0 - margin_m,
            y_max=o.y + o.size_y_m / 2.0 + margin_m,
        )
        for o in static_obstacles
    ]


def _depth(point: tuple[float, float], box: tuple[float, float, float, float]) -> float:
    x_min, x_max, y_min, y_max = box
    return min(point[0] - x_min, x_max - point[0], point[1] - y_min, y_max - point[1])


def segment_entry_m(
    start: tuple[float, float],
    heading_rad: float,
    length_m: float,
    box: tuple[float, float, float, float],
) -> float | None:
    """Where a straight segment's centre first enters a box deeper than it started.

    Args:
        start: Segment start, world `(x, y)` in metres.
        heading_rad: World-frame direction of travel.
        length_m: Segment length in metres.
        box: `(x_min, x_max, y_min, y_max)` of the (grown) box.

    Returns:
        The distance along the segment at which the centre enters the box's
        interior, or 0.0 when it starts inside and heads deeper; None when
        the segment stays outside (touching a face counts as outside), ends
        on or before the face, or starts inside and never goes deeper. A
        zero-length segment returns None.
    """
    if length_m <= _EPS:
        return None
    dx, dy = math.cos(heading_rad), math.sin(heading_rad)
    x_min, x_max, y_min, y_max = box
    depth0 = _depth(start, box)
    if depth0 > _EPS:
        # Inside: the depth along the line is the minimum of the four face
        # distances, a concave function of t, so it can only grow if it grows
        # at t = 0, along every face that is nearest at the start.
        faces = (
            (start[0] - x_min, dx),
            (x_max - start[0], -dx),
            (start[1] - y_min, dy),
            (y_max - start[1], -dy),
        )
        slope = min(rate for distance, rate in faces if distance <= depth0 + _EPS)
        return 0.0 if slope > _EPS else None
    t_low, t_high = 0.0, length_m
    for origin, rate, low, high in ((start[0], dx, x_min, x_max), (start[1], dy, y_min, y_max)):
        if abs(rate) <= _EPS:
            if not (low + _EPS < origin < high - _EPS):
                return None
            continue
        t0, t1 = (low - origin) / rate, (high - origin) / rate
        t_low, t_high = max(t_low, min(t0, t1)), min(t_high, max(t0, t1))
    if t_high - t_low <= _EPS:
        return None
    return max(0.0, t_low)


def escort_obstacle_hits(
    yielder_id: str,
    parameters: Mapping[str, Any],
    snapshot: SnapshotFrame,
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    margin_m: float,
) -> list[EscortObstacleHit]:
    """The escort legs of a grounded yield whose swept footprint enters a declared box.

    Args:
        yielder_id: The yield's yielder.
        parameters: The yield's FINAL parameters (after
            `grounding_view.apply_escort_headings`).
        snapshot: The decision snapshot the yield was grounded on.
        geometry: The geometry it was grounded on, or None.
        static_obstacles: Fixed obstacles of the running scenario.
        margin_m: Box growth (`escort_obstacle_margin_m`).

    Returns:
        One hit per blocked leg, in crossing order, naming the first box the
        leg enters (ties: declaration order); empty when every leg clears.
    """
    boxes = grown_obstacle_boxes(static_obstacles, margin_m)
    if not boxes:
        return []
    hits: list[EscortObstacleHit] = []
    for drive in escort_drives(yielder_id, parameters, snapshot, geometry):
        first: tuple[float, str] | None = None
        for box in boxes:
            entry = segment_entry_m(drive.start_xy, drive.heading_rad, drive.distance_m, box.bounds)
            if entry is not None and (first is None or entry < first[0] - _EPS):
                first = (entry, box.obstacle_id)
        if first is not None:
            hits.append(
                EscortObstacleHit(
                    passer_id=drive.passer_id,
                    obstacle_id=first[1],
                    start_xy=drive.start_xy,
                    heading_rad=drive.heading_rad,
                    distance_m=drive.distance_m,
                    clear_m=first[0],
                )
            )
    return hits


def obstacle_hit_suffix(hit: EscortObstacleHit) -> str:
    """One hit's tag suffix, shared by the infeasible and the filtered tags.

    Args:
        hit: A hit from `escort_obstacle_hits`.

    Returns:
        `<passer>:<obstacle>:<clear length m, 3 dp>`.
    """
    return f"{hit.passer_id}:{hit.obstacle_id}:{hit.clear_m:.3f}"


def escort_hits_obstacle_reason(hit: EscortObstacleHit) -> str:
    """The `yield=infeasible:` reason for one blocked leg.

    Args:
        hit: A hit from `escort_obstacle_hits`.

    Returns:
        `escort_hits_obstacle:<passer>:<obstacle>:<clear length m, 3 dp>`.
    """
    return f"{ESCORT_HITS_OBSTACLE_REASON}:{obstacle_hit_suffix(hit)}"

"""Planar footprint-proximity contacts for the simulator ground truth.

Pure geometry with no Isaac Sim or USD import, so the acceptance logger and
the offline recompute tool (`scripts/recompute_gt_contacts.py`) share one
implementation and both are unit-testable off the simulator host.

What this measures: the signed planar gap between the TurtleBot3 Burger's
URDF collision shapes, placed at a logged `base_link` pose, and (a) every
collidable box the scene builders author or (b) another robot's shapes. A
negative gap is overlap. It is a geometric proxy for contact, not a physics
contact report: the shapes are the URDF's, not the imported USD colliders,
and the robot is treated as upright (no tilt or ride-up).

Static boxes mirror, without importing, the arithmetic of
`isaac/vgu_sim/warehouse_builder.py` (`_build_walls`, `_build_rack_blocks`)
and `isaac/vgu_sim/scenario_builder.py` (`_author_box` for static and timed
box obstacles, `_author_aisle_barrier`, `_author_loop_connectors`,
`_author_rack_clearance`). Both builders read `WarehouseConfig()` defaults,
so this module does too.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import cached_property

from isaac.vgu_sim.config import (
    ROBOT_VISUAL_NO_MARKER_ASSET,
    LoopMapConfig,
    ScenarioConfig,
    WarehouseConfig,
    rack_clearance_remnants,
    rack_quadrant_rects,
)

# Identifies rows whose contact fields were computed by this module. Rows
# without the key carry the pre-2026-11-15 stub, where both contact lists were
# the literal `[]` whatever happened, so their emptiness means nothing.
CONTACT_MODEL_ID = "urdf_footprint_v1"

# A robot-obstacle or robot-robot pair counts as in contact when its footprint
# gap is at most 5 mm. Sources of slack, all millimetre scale: GT logs x/y
# rounded to 0.1 mm; the URDF primitives stand in for the imported USD
# colliders; PhysX/Newton hold resting contacts at a small positive offset; a
# robot squaring up against a face jitters by a few mm (the pinned robot_3 of
# demo take m5D_t01_a1 sits within 5 mm of its rack island in 4526 of 4534
# rows, docs/reports/2026-11-15-demo-campaign-results.md section 8.7.2). Gaps
# are logged as numbers too, so analysis never has to rely on this constant.
CONTACT_GAP_THRESHOLD_M = 0.005

# base_link sits 0.010 m above base_footprint (URDF `base_joint`), and the
# robot root is authored at z = 0.
_BASE_LINK_Z_M = 0.010

# Rack, aisle-barrier and wall heights as authored by the builders.
_RACK_HEIGHT_M = 0.9
_AISLE_BARRIER_HEIGHT_M = 0.9


@dataclass(frozen=True)
class OrientedRect:
    """A rectangle in the world plane.

    Attributes:
        cx: Center x in meters.
        cy: Center y in meters.
        half_x: Half-extent along the rectangle's own x axis, meters.
        half_y: Half-extent along the rectangle's own y axis, meters.
        yaw_rad: Rotation of the rectangle's x axis from world +x, radians.
    """

    cx: float
    cy: float
    half_x: float
    half_y: float
    yaw_rad: float = 0.0

    @cached_property
    def _cos_sin(self) -> tuple[float, float]:
        return math.cos(self.yaw_rad), math.sin(self.yaw_rad)

    @cached_property
    def corners(self) -> tuple[tuple[float, float], ...]:
        """Corner points in counter-clockwise order, world meters."""
        c, s = self._cos_sin
        out = []
        for lx, ly in (
            (self.half_x, self.half_y),
            (-self.half_x, self.half_y),
            (-self.half_x, -self.half_y),
            (self.half_x, -self.half_y),
        ):
            out.append((self.cx + c * lx - s * ly, self.cy + s * lx + c * ly))
        return tuple(out)

    @cached_property
    def axes(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """The rectangle's two unit edge normals in world coordinates."""
        c, s = self._cos_sin
        return (c, s), (-s, c)

    def point_signed_distance(self, x: float, y: float) -> float:
        """Signed distance from a world point to this rectangle.

        Args:
            x: Point x in world meters.
            y: Point y in world meters.

        Returns:
            Distance in meters, negative inside the rectangle.
        """
        c, s = self._cos_sin
        dx_w, dy_w = x - self.cx, y - self.cy
        lx = c * dx_w + s * dy_w
        ly = -s * dx_w + c * dy_w
        qx = abs(lx) - self.half_x
        qy = abs(ly) - self.half_y
        outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
        inside = min(max(qx, qy), 0.0)
        return outside + inside


@dataclass(frozen=True)
class RectPart:
    """A box collision shape of the robot, in the `base_link` frame.

    Attributes:
        name: Shape label, e.g. `chassis`.
        cx: Center x in the `base_link` frame, meters (forward positive).
        cy: Center y in the `base_link` frame, meters (left positive).
        half_x: Half-extent along `base_link` x, meters.
        half_y: Half-extent along `base_link` y, meters.
        z_min_m: Lowest world height of the shape, meters.
        z_max_m: Highest world height of the shape, meters.
    """

    name: str
    cx: float
    cy: float
    half_x: float
    half_y: float
    z_min_m: float
    z_max_m: float


@dataclass(frozen=True)
class CirclePart:
    """A vertical-cylinder collision shape of the robot, in the `base_link` frame.

    Attributes:
        name: Shape label, e.g. `lidar`.
        cx: Center x in the `base_link` frame, meters.
        cy: Center y in the `base_link` frame, meters.
        radius_m: Cylinder radius, meters.
        z_min_m: Lowest world height of the shape, meters.
        z_max_m: Highest world height of the shape, meters.
    """

    name: str
    cx: float
    cy: float
    radius_m: float
    z_min_m: float
    z_max_m: float


FootprintPart = RectPart | CirclePart

# TurtleBot3 Burger collision shapes, isaac/assets/robots/turtlebot3_burger/
# turtlebot3_burger.urdf, all child links of base_link:
#   chassis: box 0.140 x 0.140 x 0.143 at (-0.032, 0, 0.070)            (l. 63-68)
#   wheels: cylinder r 0.033, length 0.018, joints at (0, +-0.080, 0.023)
#     with rpy (-1.57, 0, 0), so the axis is along base_link y and the plan
#     view is a 0.066 x 0.018 rectangle                                  (l. 77-128)
#   caster: box 0.030 x 0.009 x 0.020 at joint (-0.081, 0, -0.004),
#     rotated -90 deg about x, so 0.030 (x) by 0.020 (y) in plan          (l. 137-149)
#   lidar: cylinder r 0.055, length 0.0315, joint (-0.032, 0, 0.172) plus
#     origin (0.015, 0, -0.0065)                                          (l. 166-186)
TURTLEBOT3_BURGER_FOOTPRINT: tuple[FootprintPart, ...] = (
    RectPart(
        "chassis", -0.032, 0.0, 0.070, 0.070,
        _BASE_LINK_Z_M + 0.070 - 0.0715, _BASE_LINK_Z_M + 0.070 + 0.0715,
    ),
    RectPart(
        "wheel_left", 0.0, 0.080, 0.033, 0.009,
        _BASE_LINK_Z_M + 0.023 - 0.033, _BASE_LINK_Z_M + 0.023 + 0.033,
    ),
    RectPart(
        "wheel_right", 0.0, -0.080, 0.033, 0.009,
        _BASE_LINK_Z_M + 0.023 - 0.033, _BASE_LINK_Z_M + 0.023 + 0.033,
    ),
    RectPart(
        "caster", -0.081, 0.0, 0.015, 0.010,
        _BASE_LINK_Z_M - 0.004 - 0.0045, _BASE_LINK_Z_M - 0.004 + 0.0045,
    ),
    CirclePart(
        "lidar", -0.032 + 0.015, 0.0, 0.055,
        _BASE_LINK_Z_M + 0.172 - 0.0065 - 0.01575,
        _BASE_LINK_Z_M + 0.172 - 0.0065 + 0.01575,
    ),
)


@dataclass(frozen=True)
class StaticBox:
    """A collidable box of the scene, as authored by the builders.

    Attributes:
        obstacle_id: Declared obstacle id for scenario obstacles, else a
            `<category>/<name>` id for derived boxes (racks, walls, barrier).
        category: One of `static_obstacle`, `timed_obstacle`, `aisle_barrier`,
            `rack`, `wall`.
        rect: Footprint of the box in the world plane.
        height_m: Box height above the floor, meters.
        active_from_sec: First sim time at which the box exists, or None.
        active_until_sec: Sim time at which the box is removed, or None.
    """

    obstacle_id: str
    category: str
    rect: OrientedRect
    height_m: float
    active_from_sec: float | None = None
    active_until_sec: float | None = None

    def is_active(self, sim_time_sec: float) -> bool:
        """Whether the box exists at `sim_time_sec` (matches `EventScheduler`).

        Args:
            sim_time_sec: Sim time in seconds.

        Returns:
            True when spawned and not yet removed.
        """
        if self.active_from_sec is not None and sim_time_sec < self.active_from_sec:
            return False
        if self.active_until_sec is not None and sim_time_sec >= self.active_until_sec:
            return False
        return True


@dataclass(frozen=True)
class ContactFrame:
    """Footprint proximity of every robot at one ground-truth row.

    Attributes:
        static_contacts: One entry per robot-box pair within the threshold,
            `{"robot_id", "obstacle_id", "gap_m"}`, sorted by robot then box.
        robot_contacts: One entry per robot pair within the threshold,
            `{"robot_ids": [a, b], "gap_m"}`, sorted by pair.
        min_static_gap_m: Smallest robot-box gap over all robots, or None
            when the scene has no active box.
        min_robot_robot_gap_m: Smallest robot-robot gap, or None with fewer
            than two robots.
        robot_min_static: Per robot, `(gap_m, obstacle_id)` of its nearest box.
        static_gaps_near: Exact gap of every robot-box pair within the near
            cutoff, keyed `(robot_id, obstacle_id)`.
        robot_gaps_near: Exact gap of every robot pair within the near cutoff,
            keyed by the sorted id pair.
        robot_pair_min: `(gap_m, (a, b))` of the closest robot pair, or None.
    """

    static_contacts: list[dict[str, object]]
    robot_contacts: list[dict[str, object]]
    min_static_gap_m: float | None
    min_robot_robot_gap_m: float | None
    robot_min_static: dict[str, tuple[float, str]] = field(default_factory=dict)
    static_gaps_near: dict[tuple[str, str], float] = field(default_factory=dict)
    robot_gaps_near: dict[tuple[str, str], float] = field(default_factory=dict)
    robot_pair_min: tuple[float, tuple[str, str]] | None = None


def _dot(p: tuple[float, float], axis: tuple[float, float]) -> float:
    return p[0] * axis[0] + p[1] * axis[1]


def _point_segment_distance(
    p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
) -> float:
    abx, aby = b[0] - a[0], b[1] - a[1]
    denom = abx * abx + aby * aby
    t = 0.0 if denom == 0.0 else ((p[0] - a[0]) * abx + (p[1] - a[1]) * aby) / denom
    t = min(1.0, max(0.0, t))
    return math.hypot(p[0] - (a[0] + t * abx), p[1] - (a[1] + t * aby))


def oriented_rect_gap(a: OrientedRect, b: OrientedRect) -> float:
    """Exact signed gap between two oriented rectangles.

    Separated rectangles return their Euclidean distance (attained between a
    vertex of one and an edge of the other, so corner-to-corner diagonals are
    exact). Overlapping ones return minus the penetration depth found by the
    separating-axis test over both rectangles' edge normals.

    Args:
        a: First rectangle.
        b: Second rectangle.

    Returns:
        Gap in meters; 0 when touching, negative when overlapping.
    """
    max_sep = -math.inf
    for axis in a.axes + b.axes:
        pa = [_dot(p, axis) for p in a.corners]
        pb = [_dot(p, axis) for p in b.corners]
        sep = max(min(pb) - max(pa), min(pa) - max(pb))
        if sep > max_sep:
            max_sep = sep
    if max_sep < 0.0:
        return max_sep
    best = math.inf
    for poly_p, poly_e in ((a.corners, b.corners), (b.corners, a.corners)):
        n = len(poly_e)
        for p in poly_p:
            for i in range(n):
                d = _point_segment_distance(p, poly_e[i], poly_e[(i + 1) % n])
                if d < best:
                    best = d
    return best


def circle_rect_gap(cx: float, cy: float, radius_m: float, rect: OrientedRect) -> float:
    """Exact signed gap between a circle and an oriented rectangle.

    Args:
        cx: Circle center x, world meters.
        cy: Circle center y, world meters.
        radius_m: Circle radius, meters.
        rect: The rectangle.

    Returns:
        Gap in meters; negative when overlapping.
    """
    return rect.point_signed_distance(cx, cy) - radius_m


def circle_circle_gap(
    a: tuple[float, float], ra: float, b: tuple[float, float], rb: float
) -> float:
    """Exact signed gap between two circles.

    Args:
        a: First center `(x, y)`, world meters.
        ra: First radius, meters.
        b: Second center `(x, y)`, world meters.
        rb: Second radius, meters.

    Returns:
        Gap in meters; negative when overlapping.
    """
    return math.hypot(a[0] - b[0], a[1] - b[1]) - ra - rb


@dataclass(frozen=True)
class _PlacedPart:
    part: FootprintPart
    rect: OrientedRect | None
    center: tuple[float, float]


def place_footprint(
    pose: tuple[float, float, float],
    footprint: Sequence[FootprintPart] = TURTLEBOT3_BURGER_FOOTPRINT,
) -> tuple[_PlacedPart, ...]:
    """Place robot collision shapes at a world `base_link` pose.

    Args:
        pose: `base_link` pose `(x, y, yaw_rad)` in world meters/radians.
        footprint: Robot shapes in the `base_link` frame.

    Returns:
        The shapes in world coordinates.
    """
    x, y, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    placed = []
    for part in footprint:
        wx = x + c * part.cx - s * part.cy
        wy = y + s * part.cx + c * part.cy
        if isinstance(part, RectPart):
            rect = OrientedRect(wx, wy, part.half_x, part.half_y, yaw)
            placed.append(_PlacedPart(part, rect, (wx, wy)))
        else:
            placed.append(_PlacedPart(part, None, (wx, wy)))
    return tuple(placed)


def _part_part_gap(a: _PlacedPart, b: _PlacedPart) -> float:
    if a.rect is not None and b.rect is not None:
        return oriented_rect_gap(a.rect, b.rect)
    if a.rect is None and b.rect is None:
        return circle_circle_gap(a.center, a.part.radius_m, b.center, b.part.radius_m)
    circle, rect = (a, b) if a.rect is None else (b, a)
    return circle_rect_gap(circle.center[0], circle.center[1], circle.part.radius_m, rect.rect)


def _placed_box_gap(placed: Sequence[_PlacedPart], box: StaticBox) -> float | None:
    best: float | None = None
    for p in placed:
        # A shape entirely above the box top cannot touch it.
        if p.part.z_min_m >= box.height_m:
            continue
        if p.rect is not None:
            gap = oriented_rect_gap(p.rect, box.rect)
        else:
            gap = circle_rect_gap(p.center[0], p.center[1], p.part.radius_m, box.rect)
        if best is None or gap < best:
            best = gap
    return best


def robot_box_gap(
    pose: tuple[float, float, float],
    box: StaticBox,
    footprint: Sequence[FootprintPart] = TURTLEBOT3_BURGER_FOOTPRINT,
) -> float | None:
    """Signed planar gap between a robot's collision shapes and one box.

    Args:
        pose: `base_link` pose `(x, y, yaw_rad)`.
        box: The box.
        footprint: Robot shapes in the `base_link` frame.

    Returns:
        Smallest gap over the shapes that reach below the box top, in meters
        (negative = overlap), or None when every shape is above the box.
    """
    return _placed_box_gap(place_footprint(pose, footprint), box)


def robot_robot_gap(
    pose_a: tuple[float, float, float],
    pose_b: tuple[float, float, float],
    footprint: Sequence[FootprintPart] = TURTLEBOT3_BURGER_FOOTPRINT,
) -> float:
    """Signed planar gap between two robots' collision shapes.

    Args:
        pose_a: First robot's `base_link` pose `(x, y, yaw_rad)`.
        pose_b: Second robot's `base_link` pose.
        footprint: Shapes of both robots in the `base_link` frame.

    Returns:
        Smallest shape-to-shape gap in meters (negative = overlap).
    """
    return _placed_pair_gap(place_footprint(pose_a, footprint), place_footprint(pose_b, footprint))


def _placed_pair_gap(a: Sequence[_PlacedPart], b: Sequence[_PlacedPart]) -> float:
    best = math.inf
    for pa in a:
        for pb in b:
            if pa.part.z_min_m >= pb.part.z_max_m or pb.part.z_min_m >= pa.part.z_max_m:
                continue
            gap = _part_part_gap(pa, pb)
            if gap < best:
                best = gap
    return best


def footprint_bounding_radius(
    footprint: Sequence[FootprintPart] = TURTLEBOT3_BURGER_FOOTPRINT,
) -> float:
    """Radius about the `base_link` origin enclosing every shape.

    Args:
        footprint: Robot shapes in the `base_link` frame.

    Returns:
        Bounding radius in meters.
    """
    radius = 0.0
    for part in footprint:
        if isinstance(part, RectPart):
            reach = max(
                math.hypot(part.cx + sx * part.half_x, part.cy + sy * part.half_y)
                for sx in (-1.0, 1.0)
                for sy in (-1.0, 1.0)
            )
        else:
            reach = math.hypot(part.cx, part.cy) + part.radius_m
        radius = max(radius, reach)
    return radius


def _axis_box(
    obstacle_id: str, category: str, x0: float, x1: float, y0: float, y1: float, height: float
) -> StaticBox:
    return StaticBox(
        obstacle_id=obstacle_id,
        category=category,
        rect=OrientedRect((x0 + x1) / 2.0, (y0 + y1) / 2.0, (x1 - x0) / 2.0, (y1 - y0) / 2.0),
        height_m=height,
    )


def loop_rack_remnants(
    warehouse: WarehouseConfig, loop_cfg: LoopMapConfig
) -> list[tuple[str, float, float, float, float, float]]:
    """The four boxes `_author_loop_connectors` authors in place of rack NE.

    Same arithmetic as `scenario_builder._author_loop_connectors`.

    Args:
        warehouse: Warehouse geometry.
        loop_cfg: Scenario loop-map geometry.

    Returns:
        `(name, x_min, x_max, y_min, y_max, height_m)` per remnant.
    """
    base_half = warehouse.nominal_aisle_width_m / 2.0
    rack_half_width = (warehouse.width_m / 2.0 - base_half) / 2.0
    rack_half_depth = (warehouse.depth_m / 2.0 - base_half) / 2.0
    ne_x_max = base_half + rack_half_width * 2.0
    ne_y_max = base_half + rack_half_depth * 2.0
    low_h = loop_cfg.connector_remnant_height_m
    aisle_y_min = loop_cfg.second_aisle_center_y_m - loop_cfg.second_aisle_width_m / 2.0
    aisle_y_max = loop_cfg.second_aisle_center_y_m + loop_cfg.second_aisle_width_m / 2.0
    aisle_x_max = loop_cfg.second_aisle_x_max_m
    conn_x_min = loop_cfg.connector_center_x_m - loop_cfg.connector_width_m / 2.0
    conn_x_max = loop_cfg.connector_center_x_m + loop_cfg.connector_width_m / 2.0
    return [
        ("top_slab", base_half, ne_x_max, aisle_y_max, ne_y_max, _RACK_HEIGHT_M),
        ("aisle_east_of_loop", aisle_x_max, ne_x_max, aisle_y_min, aisle_y_max, _RACK_HEIGHT_M),
        ("connector_west_remnant", base_half, conn_x_min, base_half, aisle_y_min, low_h),
        ("connector_east_remnant", conn_x_max, ne_x_max, base_half, aisle_y_min, low_h),
    ]


def unmodelled_obstacle_ids(scenario: ScenarioConfig) -> tuple[str, ...]:
    """Timed obstacles this module cannot represent as boxes.

    `robot_visual_no_marker` props are the robot's own meshes scaled 1.82;
    their colliders are not boxes, so they are left out of the contact set.

    Args:
        scenario: Scenario config.

    Returns:
        Their obstacle ids.
    """
    return tuple(
        obs.obstacle_id
        for obs in scenario.timed_obstacles
        if obs.asset == ROBOT_VISUAL_NO_MARKER_ASSET
    )


def scene_static_boxes(
    scenario: ScenarioConfig, warehouse: WarehouseConfig | None = None
) -> tuple[StaticBox, ...]:
    """Every collidable box the builders author for `scenario`.

    Covers the four walls, the rack blocks (the four quadrants, or the loop
    remnants replacing NE, or the rack-clearance remnants replacing all four),
    the aisle-barrier blocks, declared static obstacles and box-type timed
    obstacles (with their active window). The floor and the
    `robot_visual_no_marker` props are not included.

    Args:
        scenario: Scenario config.
        warehouse: Warehouse geometry; defaults to `WarehouseConfig()`, which
            is what both builders use.

    Returns:
        The boxes, walls first and scenario obstacles last.
    """
    wh = warehouse if warehouse is not None else WarehouseConfig()
    hw, hd = wh.width_m / 2.0, wh.depth_m / 2.0
    t = wh.wall_thickness_m / 2.0
    boxes: list[StaticBox] = [
        _axis_box("wall/north", "wall", -hw - t, hw + t, hd, hd + 2 * t, wh.wall_height_m),
        _axis_box("wall/south", "wall", -hw - t, hw + t, -hd - 2 * t, -hd, wh.wall_height_m),
        _axis_box("wall/east", "wall", hw, hw + 2 * t, -hd, hd, wh.wall_height_m),
        _axis_box("wall/west", "wall", -hw - 2 * t, -hw, -hd, hd, wh.wall_height_m),
    ]

    if scenario.rack_clearance is not None:
        for name, x0, x1, y0, y1 in rack_clearance_remnants(wh, scenario.rack_clearance):
            boxes.append(_axis_box(f"rack/{name}", "rack", x0, x1, y0, y1, _RACK_HEIGHT_M))
    else:
        for name, x0, x1, y0, y1 in rack_quadrant_rects(wh):
            if name == "NE" and scenario.loop_map is not None:
                continue
            boxes.append(_axis_box(f"rack/{name}", "rack", x0, x1, y0, y1, _RACK_HEIGHT_M))
        if scenario.loop_map is not None:
            for name, x0, x1, y0, y1, h in loop_rack_remnants(wh, scenario.loop_map):
                boxes.append(_axis_box(f"rack/NE_{name}", "rack", x0, x1, y0, y1, h))

    barrier = scenario.aisle_barrier
    if barrier is not None:
        base_half = wh.nominal_aisle_width_m / 2.0
        effective_half = barrier.effective_width_m / 2.0
        if effective_half < base_half:
            half_x = barrier.length_m / 2.0
            x0, x1 = barrier.center_x_m - half_x, barrier.center_x_m + half_x
            boxes.append(_axis_box(
                "aisle_barrier/north", "aisle_barrier", x0, x1,
                effective_half, base_half, _AISLE_BARRIER_HEIGHT_M,
            ))
            boxes.append(_axis_box(
                "aisle_barrier/south", "aisle_barrier", x0, x1,
                -base_half, -effective_half, _AISLE_BARRIER_HEIGHT_M,
            ))

    for obs in scenario.static_obstacles:
        boxes.append(StaticBox(
            obstacle_id=obs.obstacle_id,
            category="static_obstacle",
            rect=OrientedRect(
                obs.pose.x, obs.pose.y, obs.size.x_m / 2.0, obs.size.y_m / 2.0, obs.pose.yaw_rad
            ),
            height_m=obs.size.z_m,
        ))
    for obs in scenario.timed_obstacles:
        if obs.asset == ROBOT_VISUAL_NO_MARKER_ASSET:
            continue
        boxes.append(StaticBox(
            obstacle_id=obs.obstacle_id,
            category="timed_obstacle",
            rect=OrientedRect(
                obs.pose.x, obs.pose.y, obs.size.x_m / 2.0, obs.size.y_m / 2.0, obs.pose.yaw_rad
            ),
            height_m=obs.size.z_m,
            active_from_sec=obs.spawn_at_sec,
            active_until_sec=obs.remove_at_sec,
        ))
    return tuple(boxes)


def _round_gap(value: float) -> float:
    return round(float(value), 4)


def compute_contact_frame(
    poses: Mapping[str, tuple[float, float, float]],
    boxes: Sequence[StaticBox],
    sim_time_sec: float,
    *,
    threshold_m: float = CONTACT_GAP_THRESHOLD_M,
    near_cutoff_m: float | None = None,
    footprint: Sequence[FootprintPart] = TURTLEBOT3_BURGER_FOOTPRINT,
) -> ContactFrame:
    """Footprint contacts and minimum gaps for one instant.

    Exact gaps are computed only for pairs whose cheap lower bound (center
    distance minus the footprint bounding radius) does not already exceed
    both the running minimum and the cutoff, so the minima stay exact.

    Args:
        poses: Robot id to `base_link` pose `(x, y, yaw_rad)`.
        boxes: Scene boxes from `scene_static_boxes`.
        sim_time_sec: Sim time, used for timed-obstacle activity.
        threshold_m: Gap at or below which a pair is a contact entry.
        near_cutoff_m: Gap at or below which a pair's exact gap is kept in
            the `*_near` maps; defaults to `threshold_m`.
        footprint: Robot shapes in the `base_link` frame.

    Returns:
        The contact entries, minima and per-pair detail.
    """
    cutoff = threshold_m if near_cutoff_m is None else max(threshold_m, near_cutoff_m)
    radius = footprint_bounding_radius(footprint)
    active = [box for box in boxes if box.is_active(sim_time_sec)]
    robot_ids = sorted(poses)
    placed = {rid: place_footprint(poses[rid], footprint) for rid in robot_ids}

    static_contacts: list[dict[str, object]] = []
    static_near: dict[tuple[str, str], float] = {}
    robot_min_static: dict[str, tuple[float, str]] = {}
    for rid in robot_ids:
        x, y, _ = poses[rid]
        bounds = sorted(
            ((box.rect.point_signed_distance(x, y) - radius, i) for i, box in enumerate(active)),
        )
        best = math.inf
        best_id: str | None = None
        hits: list[tuple[str, float]] = []
        for lower, i in bounds:
            if lower > max(best, cutoff):
                break
            box = active[i]
            gap = _placed_box_gap(placed[rid], box)
            if gap is None:
                continue
            if gap < best:
                best, best_id = gap, box.obstacle_id
            if gap <= cutoff:
                static_near[(rid, box.obstacle_id)] = gap
            if gap <= threshold_m:
                hits.append((box.obstacle_id, gap))
        if best_id is not None:
            robot_min_static[rid] = (best, best_id)
        for obstacle_id, gap in sorted(hits):
            static_contacts.append(
                {"robot_id": rid, "obstacle_id": obstacle_id, "gap_m": _round_gap(gap)}
            )

    pair_bounds = []
    for i, a in enumerate(robot_ids):
        for b in robot_ids[i + 1:]:
            centre = math.hypot(poses[a][0] - poses[b][0], poses[a][1] - poses[b][1])
            pair_bounds.append((centre - 2.0 * radius, a, b))
    pair_bounds.sort()
    pair_best = math.inf
    pair_best_ids: tuple[str, str] | None = None
    robot_near: dict[tuple[str, str], float] = {}
    for lower, a, b in pair_bounds:
        if lower > max(pair_best, cutoff):
            break
        gap = _placed_pair_gap(placed[a], placed[b])
        if gap < pair_best:
            pair_best, pair_best_ids = gap, (a, b)
        if gap <= cutoff:
            robot_near[(a, b)] = gap
    robot_contacts = [
        {"robot_ids": [a, b], "gap_m": _round_gap(gap)}
        for (a, b), gap in sorted(robot_near.items())
        if gap <= threshold_m
    ]

    min_static = min((g for g, _ in robot_min_static.values()), default=None)
    return ContactFrame(
        static_contacts=static_contacts,
        robot_contacts=robot_contacts,
        min_static_gap_m=_round_gap(min_static) if min_static is not None else None,
        min_robot_robot_gap_m=(
            _round_gap(pair_best) if pair_best_ids is not None else None
        ),
        robot_min_static=robot_min_static,
        static_gaps_near=static_near,
        robot_gaps_near=robot_near,
        robot_pair_min=(pair_best, pair_best_ids) if pair_best_ids is not None else None,
    )

import math

import numpy as np
import pytest

from isaac.vgu_sim.config import (
    AisleBarrierConfig,
    ExpectedConflictConfig,
    Goal2D,
    LoopMapConfig,
    ObstacleSize,
    Pose2D,
    RackClearanceConfig,
    RobotScenarioConfig,
    ScenarioConfig,
    StaticObstacleConfig,
    TimedObstacleConfig,
    WarehouseConfig,
)
from isaac.vgu_sim.contact_geometry import (
    CONTACT_GAP_THRESHOLD_M,
    TURTLEBOT3_BURGER_FOOTPRINT,
    CirclePart,
    OrientedRect,
    StaticBox,
    circle_circle_gap,
    circle_rect_gap,
    compute_contact_frame,
    footprint_bounding_radius,
    oriented_rect_gap,
    robot_box_gap,
    robot_robot_gap,
    scene_static_boxes,
    unmodelled_obstacle_ids,
)


def _box(obstacle_id: str, cx: float, cy: float, sx: float, sy: float, yaw: float = 0.0,
         height: float = 0.3) -> StaticBox:
    rect = OrientedRect(cx, cy, sx / 2, sy / 2, yaw)
    return StaticBox(obstacle_id, "static_obstacle", rect, height)


def _scenario(**extra) -> ScenarioConfig:
    base = dict(
        schema_version=1,
        name="bottleneck_contact_probe",
        family="bottleneck",
        seed=1,
        duration_sec=60.0,
        robots=(
            RobotScenarioConfig(
                robot_id="robot_1",
                marker_id=1,
                spawn=Pose2D(x=-2.0, y=0.0, yaw_rad=0.0),
                goal=Goal2D(x=2.0, y=0.0),
                initial_task="t",
            ),
        ),
        expected_conflict=ExpectedConflictConfig(
            type="deadlock",
            involved_robots=("robot_1",),
            onset_window_sec=(1.0, 2.0),
            min_duration_sec=1.0,
        ),
    )
    base.update(extra)
    return ScenarioConfig(**base)


# ---- primitive gaps


def test_rect_gap_is_face_distance_when_axis_aligned_and_clear():
    a = OrientedRect(0.0, 0.0, 0.5, 0.5)
    b = OrientedRect(1.3, 0.2, 0.5, 0.5)
    assert oriented_rect_gap(a, b) == pytest.approx(0.3)


def test_rect_gap_is_euclidean_when_corner_to_corner():
    a = OrientedRect(0.0, 0.0, 0.5, 0.5)
    b = OrientedRect(1.3, 1.4, 0.5, 0.5)
    assert oriented_rect_gap(a, b) == pytest.approx(math.hypot(0.3, 0.4))


def test_rect_gap_is_zero_when_touching():
    a = OrientedRect(0.0, 0.0, 0.5, 0.5)
    b = OrientedRect(1.0, 0.3, 0.5, 0.5)
    assert oriented_rect_gap(a, b) == pytest.approx(0.0, abs=1e-12)


def test_rect_gap_is_negative_penetration_when_overlapping():
    a = OrientedRect(0.0, 0.0, 0.5, 0.5)
    b = OrientedRect(0.9, 0.0, 0.5, 0.5)
    assert oriented_rect_gap(a, b) == pytest.approx(-0.1)


def test_rect_gap_uses_rotated_corner_when_rect_is_rotated():
    # A unit square rotated 45 deg reaches sqrt(0.5) along x.
    a = OrientedRect(0.0, 0.0, 0.5, 0.5, math.pi / 4)
    b = OrientedRect(2.0, 0.0, 0.5, 0.5)
    assert oriented_rect_gap(a, b) == pytest.approx(1.5 - math.sqrt(0.5))


def test_rect_gap_is_symmetric_when_arguments_swap():
    a = OrientedRect(0.1, -0.2, 0.3, 0.1, 0.7)
    b = OrientedRect(0.6, 0.4, 0.2, 0.25, -0.3)
    assert oriented_rect_gap(a, b) == pytest.approx(oriented_rect_gap(b, a))


def test_circle_rect_gap_is_face_distance_when_clear():
    rect = OrientedRect(0.0, 0.0, 0.5, 0.5)
    assert circle_rect_gap(1.0, 0.0, 0.2, rect) == pytest.approx(0.3)


def test_circle_rect_gap_is_corner_distance_when_diagonal():
    rect = OrientedRect(0.0, 0.0, 0.5, 0.5)
    assert circle_rect_gap(0.8, 0.9, 0.1, rect) == pytest.approx(0.5 - 0.1)


def test_circle_rect_gap_is_zero_when_touching():
    rect = OrientedRect(0.0, 0.0, 0.5, 0.5)
    assert circle_rect_gap(0.0, 0.7, 0.2, rect) == pytest.approx(0.0, abs=1e-12)


def test_circle_rect_gap_is_negative_when_overlapping():
    rect = OrientedRect(0.0, 0.0, 0.5, 0.5)
    assert circle_rect_gap(0.6, 0.0, 0.2, rect) == pytest.approx(-0.1)


def test_circle_rect_gap_respects_rect_rotation():
    rect = OrientedRect(0.0, 0.0, 0.5, 0.5, math.pi / 4)
    assert circle_rect_gap(1.0, 0.0, 0.1, rect) == pytest.approx(1.0 - math.sqrt(0.5) - 0.1)


def test_circle_circle_gap_is_center_distance_minus_radii():
    assert circle_circle_gap((0.0, 0.0), 0.1, (0.3, 0.4), 0.2) == pytest.approx(0.2)


# ---- robot footprint


def test_footprint_wheels_extend_beyond_chassis_laterally():
    chassis = TURTLEBOT3_BURGER_FOOTPRINT[0]
    wheels = [p for p in TURTLEBOT3_BURGER_FOOTPRINT if p.name.startswith("wheel")]
    assert chassis.cy + chassis.half_y == pytest.approx(0.070)
    assert max(abs(w.cy) + w.half_y for w in wheels) == pytest.approx(0.089)


def test_footprint_lidar_and_caster_lie_inside_chassis_plan():
    chassis = OrientedRect(-0.032, 0.0, 0.070, 0.070)
    for part in TURTLEBOT3_BURGER_FOOTPRINT:
        if isinstance(part, CirclePart):
            assert chassis.point_signed_distance(part.cx, part.cy) + part.radius_m <= 1e-12
        elif part.name == "caster":
            inner = OrientedRect(part.cx, part.cy, part.half_x, part.half_y)
            assert all(chassis.point_signed_distance(*c) <= 0.0 for c in inner.corners)


def test_footprint_nose_reaches_38_mm_ahead_of_base_link():
    box = _box("face", 1.0, 0.0, 1.0, 1.0)  # west face at x = 0.5
    assert robot_box_gap((0.5 - 0.038, 0.0, 0.0), box) == pytest.approx(0.0, abs=1e-12)


def test_robot_box_gap_matches_demo_pin_pose_when_squared_against_island():
    # m5D_t01_a1 robot_3 pinned at (0.838, 0.572, pi) against obstacle_2
    # (centre (0.525, -0.1), 0.55 x 1.6): its nose is on the x = 0.800 face.
    island = _box("obstacle_2", 0.525, -0.1, 0.55, 1.6)
    assert robot_box_gap((0.838, 0.572, math.pi), island) == pytest.approx(0.0, abs=1e-9)


def test_robot_box_gap_is_lateral_wheel_reach_when_robot_rotated_ninety_degrees():
    box = _box("east", 1.0, 0.0, 1.0, 1.0)  # west face at x = 0.5
    # Heading +y: base_link y (wheels, 0.089) now points -x, so +x reach is 0.089 too.
    gap = robot_box_gap((0.3, 0.0, math.pi / 2), box)
    assert gap == pytest.approx(0.5 - 0.3 - 0.089)


def test_robot_box_gap_is_negative_when_robot_overlaps_box():
    box = _box("face", 1.0, 0.0, 1.0, 1.0)
    assert robot_box_gap((0.5 - 0.028, 0.0, 0.0), box) == pytest.approx(-0.010)


def test_robot_box_gap_ignores_shapes_above_box_top():
    lidar_only = (CirclePart("lidar", 0.0, 0.0, 0.05, 0.15, 0.19),)
    low_box = _box("kerb", 0.0, 0.0, 0.2, 0.2, height=0.1)
    assert robot_box_gap((0.0, 0.0, 0.0), low_box, lidar_only) is None


def test_robot_robot_gap_is_zero_when_nose_to_nose_at_76_mm():
    # docs/reports/2026-09-25-overnight-findings.md: the 0.076 m centre wedge
    # was driven nose-to-nose contact.
    assert robot_robot_gap((0.0, 0.0, 0.0), (0.076, 0.0, math.pi)) == pytest.approx(0.0, abs=1e-12)


def test_robot_robot_gap_uses_wheels_when_side_by_side():
    assert robot_robot_gap((0.0, 0.0, 0.0), (0.0, 0.2, 0.0)) == pytest.approx(0.2 - 2 * 0.089)


def test_bounding_radius_encloses_chassis_rear_corners():
    assert footprint_bounding_radius() == pytest.approx(math.hypot(0.102, 0.070))


# ---- frame computation


def test_contact_frame_lists_overlapping_box_and_omits_clear_box():
    near = _box("near", 1.0, 0.0, 1.0, 1.0)
    far = _box("far", -3.0, 0.0, 1.0, 1.0)
    frame = compute_contact_frame({"robot_1": (0.5 - 0.035, 0.0, 0.0)}, [near, far], 0.0)
    assert frame.static_contacts == [
        {"robot_id": "robot_1", "obstacle_id": "near", "gap_m": -0.003}
    ]
    assert frame.min_static_gap_m == -0.003


def test_contact_frame_has_no_entries_when_clear():
    box = _box("box", 1.0, 0.0, 1.0, 1.0)
    frame = compute_contact_frame({"robot_1": (0.0, 0.0, 0.0)}, [box], 0.0)
    assert frame.static_contacts == []
    assert frame.min_static_gap_m == pytest.approx(0.5 - 0.038)


def test_contact_frame_lists_every_box_within_threshold_when_wedged_between_two():
    west = _box("west", -0.5 - 0.102, 0.0, 1.0, 1.0)  # east face at -0.102: rear touches
    east = _box("east", 0.5 + 0.038 + 0.002, 0.0, 1.0, 1.0)  # 2 mm ahead of the nose
    frame = compute_contact_frame({"robot_1": (0.0, 0.0, 0.0)}, [east, west], 0.0)
    assert [(c["obstacle_id"], c["gap_m"]) for c in frame.static_contacts] == [
        ("east", 0.002),
        ("west", 0.0),
    ]


@pytest.mark.parametrize("offset_m, expected", [(-1e-9, 1), (1e-6, 0)])
def test_contact_frame_threshold_separates_contact_from_clear(offset_m, expected):
    box = _box("box", 0.5 + 0.038 + CONTACT_GAP_THRESHOLD_M + offset_m, 0.0, 1.0, 1.0)
    frame = compute_contact_frame({"robot_1": (0.0, 0.0, 0.0)}, [box], 0.0)
    assert len(frame.static_contacts) == expected


def test_contact_frame_minimum_is_exact_when_bounds_prune():
    boxes = [_box(f"b{i}", 2.0 + i, 0.3 * i, 0.5, 0.5, yaw=0.2 * i) for i in range(8)]
    pose = (0.4, 0.1, 0.9)
    frame = compute_contact_frame({"robot_1": pose}, boxes, 0.0)
    brute = min(robot_box_gap(pose, b) for b in boxes)
    assert frame.min_static_gap_m == round(brute, 4)


def test_contact_frame_lists_robot_pair_when_nose_to_nose():
    frame = compute_contact_frame(
        {"robot_2": (0.076, 0.0, math.pi), "robot_1": (0.0, 0.0, 0.0), "robot_3": (3.0, 0.0, 0.0)},
        [],
        0.0,
    )
    assert frame.robot_contacts == [{"robot_ids": ["robot_1", "robot_2"], "gap_m": 0.0}]
    assert frame.min_robot_robot_gap_m == 0.0
    assert frame.min_static_gap_m is None


def test_contact_frame_robot_minimum_is_none_when_single_robot():
    frame = compute_contact_frame({"robot_1": (0.0, 0.0, 0.0)}, [], 0.0)
    assert frame.min_robot_robot_gap_m is None
    assert frame.robot_contacts == []


def test_contact_frame_skips_timed_box_outside_its_window():
    box = StaticBox("timed", "timed_obstacle", OrientedRect(0.238, 0.0, 0.2, 0.2), 0.5, 5.0, 9.0)
    assert compute_contact_frame({"r": (0.0, 0.0, 0.0)}, [box], 4.99).static_contacts == []
    assert len(compute_contact_frame({"r": (0.0, 0.0, 0.0)}, [box], 5.0).static_contacts) == 1
    assert compute_contact_frame({"r": (0.0, 0.0, 0.0)}, [box], 9.0).static_contacts == []


# ---- scene boxes


def test_scene_boxes_have_walls_and_four_racks_when_scene_is_default():
    boxes = scene_static_boxes(_scenario())
    ids = [b.obstacle_id for b in boxes]
    assert ids == [
        "wall/north", "wall/south", "wall/east", "wall/west",
        "rack/NE", "rack/NW", "rack/SE", "rack/SW",
    ]
    ne = boxes[4].rect
    assert (ne.cx - ne.half_x, ne.cx + ne.half_x, ne.cy - ne.half_y, ne.cy + ne.half_y) == (
        pytest.approx((0.6, 6.0, 0.6, 4.0))
    )


def test_scene_boxes_place_walls_outside_the_floor():
    boxes = {b.obstacle_id: b for b in scene_static_boxes(_scenario())}
    north, east = boxes["wall/north"].rect, boxes["wall/east"].rect
    assert north.cy - north.half_y == pytest.approx(4.0)
    assert north.half_x == pytest.approx(6.05)
    assert east.cx - east.half_x == pytest.approx(6.0)
    assert east.half_y == pytest.approx(4.0)


def test_scene_boxes_replace_racks_when_rack_clearance_set():
    scenario = _scenario(
        rack_clearance=RackClearanceConfig(x_min_m=-2.5, x_max_m=2.5, y_min_m=-1.8, y_max_m=1.8),
        static_obstacles=(
            StaticObstacleConfig(
                obstacle_id="obstacle_2",
                pose=Pose2D(x=0.525, y=-0.1, yaw_rad=0.0),
                size=ObstacleSize(x_m=0.55, y_m=1.6, z_m=0.3),
            ),
        ),
    )
    boxes = scene_static_boxes(scenario)
    ids = [b.obstacle_id for b in boxes]
    assert "rack/NE" not in ids
    assert "rack/NE_east" in ids and "rack/NE_north" in ids
    island = boxes[-1]
    assert island.obstacle_id == "obstacle_2" and island.category == "static_obstacle"
    assert island.height_m == pytest.approx(0.3)


def test_scene_boxes_carve_ne_when_loop_map_set():
    scenario = _scenario(
        loop_map=LoopMapConfig(
            second_aisle_center_y_m=1.6,
            second_aisle_width_m=0.8,
            second_aisle_x_min_m=0.6,
            second_aisle_x_max_m=3.0,
            connector_center_x_m=2.0,
            connector_width_m=0.8,
        )
    )
    ids = [b.obstacle_id for b in scene_static_boxes(scenario)]
    assert "rack/NE" not in ids
    assert ids[-4:] == [
        "rack/NE_top_slab", "rack/NE_aisle_east_of_loop",
        "rack/NE_connector_west_remnant", "rack/NE_connector_east_remnant",
    ]


def test_scene_boxes_add_barrier_blocks_when_corridor_narrower_than_aisle():
    scenario = _scenario(
        aisle_barrier=AisleBarrierConfig(effective_width_m=0.55, center_x_m=0.0, length_m=2.0)
    )
    boxes = {b.obstacle_id: b for b in scene_static_boxes(scenario)}
    north = boxes["aisle_barrier/north"].rect
    assert north.cy - north.half_y == pytest.approx(0.275)
    assert north.cy + north.half_y == pytest.approx(0.6)
    assert north.half_x == pytest.approx(1.0)


def test_scene_boxes_skip_barrier_when_corridor_not_narrower():
    scenario = _scenario(
        aisle_barrier=AisleBarrierConfig(effective_width_m=1.2, center_x_m=0.0, length_m=2.0)
    )
    assert not any(b.category == "aisle_barrier" for b in scene_static_boxes(scenario))


def test_scene_boxes_keep_timed_box_and_list_robot_visual_as_unmodelled():
    scenario = _scenario(
        timed_obstacles=(
            TimedObstacleConfig(
                obstacle_id="crate", asset="static_box", spawn_at_sec=3.0,
                remove_at_sec=8.0, pose=Pose2D(x=1.0, y=0.0, yaw_rad=0.3),
            ),
            TimedObstacleConfig(
                obstacle_id="ghost", asset="robot_visual_no_marker", spawn_at_sec=3.0,
                pose=Pose2D(x=1.0, y=0.0, yaw_rad=0.0),
            ),
        )
    )
    timed = [b for b in scene_static_boxes(scenario) if b.category == "timed_obstacle"]
    assert [(b.obstacle_id, b.active_from_sec, b.active_until_sec) for b in timed] == [
        ("crate", 3.0, 8.0)
    ]
    assert timed[0].rect.yaw_rad == pytest.approx(0.3)
    assert unmodelled_obstacle_ids(scenario) == ("ghost",)


def _rasterize(boxes, wh: WarehouseConfig, res: float) -> np.ndarray:
    # Same cell convention as isaac/scripts/generate_warehouse_map.py.
    from isaac.scripts.generate_warehouse_map import FREE, OCCUPIED, world_to_cell

    grid = np.full((round(wh.depth_m / res), round(wh.width_m / res)), FREE, dtype=np.uint8)
    for box in boxes:
        r = box.rect
        r0, c0 = world_to_cell(r.cx - r.half_x, r.cy + r.half_y, wh, res)
        r1, c1 = world_to_cell(r.cx + r.half_x, r.cy - r.half_y, wh, res)
        grid[max(0, r0):r1, max(0, c0):c1] = OCCUPIED
    return grid


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {
            "aisle_barrier": AisleBarrierConfig(
                effective_width_m=0.55, center_x_m=0.4, length_m=2.0
            )
        },
        {
            "rack_clearance": RackClearanceConfig(
                x_min_m=-2.5, x_max_m=2.5, y_min_m=-1.8, y_max_m=1.8
            )
        },
        {
            "loop_map": LoopMapConfig(
                second_aisle_center_y_m=1.6, second_aisle_width_m=0.8,
                second_aisle_x_min_m=0.6, second_aisle_x_max_m=3.0,
                connector_center_x_m=2.0, connector_width_m=0.8,
            )
        },
        {
            "static_obstacles": (
                StaticObstacleConfig(
                    obstacle_id="o1", pose=Pose2D(x=-1.025, y=0.1, yaw_rad=0.0),
                    size=ObstacleSize(x_m=0.55, y_m=1.6, z_m=0.3),
                ),
            )
        },
    ],
    ids=["default", "aisle_barrier", "rack_clearance", "loop_map", "static_obstacles"],
)
def test_scene_boxes_match_static_map_interior_when_rasterized(extra):
    pytest.importorskip("PIL")
    from isaac.scripts.generate_warehouse_map import build_occupancy_grid

    wh = WarehouseConfig()
    res = 0.05
    scenario = _scenario(**extra)
    expected, _ = build_occupancy_grid(
        wh, [], res,
        aisle_barrier=scenario.aisle_barrier,
        static_obstacles=scenario.static_obstacles,
        loop_map=scenario.loop_map,
        rack_clearance=scenario.rack_clearance,
    )
    interior = [b for b in scene_static_boxes(scenario) if b.category != "wall"]
    got = _rasterize(interior, wh, res)
    # The map draws its walls inside the floor; the USD walls sit outside it.
    border = max(1, round(wh.wall_thickness_m / res))
    inner = (slice(border, -border), slice(border, -border))
    assert np.array_equal(got[inner], expected[inner])


def test_scene_boxes_match_usd_builders_when_pxr_available(tmp_path):
    pxr = pytest.importorskip("pxr")
    from isaac.vgu_sim import scenario_builder, warehouse_builder

    Usd, UsdGeom = pxr.Usd, pxr.UsdGeom
    scenario = _scenario(
        aisle_barrier=AisleBarrierConfig(effective_width_m=0.55, center_x_m=0.4, length_m=2.0),
        static_obstacles=(
            StaticObstacleConfig(
                obstacle_id="o1", pose=Pose2D(x=-1.0, y=0.2, yaw_rad=0.4),
                size=ObstacleSize(x_m=0.55, y_m=1.6, z_m=0.3),
            ),
        ),
    )
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Xform.Define(stage, "/World/Environment")
    UsdGeom.Xform.Define(stage, "/World/Scenario")
    warehouse_builder._build_walls(stage, WarehouseConfig())
    warehouse_builder._build_rack_blocks(stage, WarehouseConfig())
    scenario_builder._author_static_obstacles(stage, scenario)
    scenario_builder._author_aisle_barrier(stage, scenario.aisle_barrier)
    paths = {
        "wall/north": "/World/Environment/Walls/north",
        "wall/east": "/World/Environment/Walls/east",
        "rack/SW": "/World/Environment/RackBlocks/SW",
        "aisle_barrier/north": "/World/Scenario/AisleBarriers/north",
        "o1": "/World/Scenario/StaticObstacles/o1",
    }
    boxes = {b.obstacle_id: b for b in scene_static_boxes(scenario)}
    for box_id, path in paths.items():
        prim = stage.GetPrimAtPath(path)
        xf = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        for lx, ly in ((1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)):
            world = xf.Transform(pxr.Gf.Vec3d(lx, ly, 0.0))
            assert boxes[box_id].rect.point_signed_distance(world[0], world[1]) == pytest.approx(
                0.0, abs=1e-5
            ), (box_id, lx, ly)

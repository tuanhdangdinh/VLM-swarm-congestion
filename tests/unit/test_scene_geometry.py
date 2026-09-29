"""Unit tests for the declared scene geometry M3 derives yield distances from."""
import pytest
from pydantic import ValidationError

from reasoning.rag.scene_geometry import (
    ArmGeometry,
    CameraGeometry,
    CorridorGeometry,
    SceneGeometry,
    arm_geometry,
    park_offset_m,
    passer_clearance_m,
    passer_travel_m,
    pull_off_lateral_m,
    required_room_m,
    room_is_feasible,
    visibility_boundary_m,
    yield_feasible,
    yield_retreat_room_m,
)
from reasoning.vlm.models import StaticObstacleInput


def _head_on_geometry(**corridor_overrides) -> SceneGeometry:
    corridor = {
        "axis": "x",
        "center_m": 0.0,
        "half_length_m": 1.0,
        "aisle_half_width_m": 0.6,
        "occluder_height_m": 0.9,
    }
    corridor.update(corridor_overrides)
    return SceneGeometry(corridor=CorridorGeometry(**corridor))


def test_visibility_boundary_matches_head_on_geometry():
    assert visibility_boundary_m(_head_on_geometry()) == pytest.approx(1.329, abs=1e-3)


def test_park_offset_matches_head_on_geometry():
    assert park_offset_m(_head_on_geometry()) == pytest.approx(1.789, abs=1e-3)


def test_pull_off_lateral_matches_head_on_geometry():
    assert pull_off_lateral_m(_head_on_geometry()) == pytest.approx(0.36, abs=1e-9)


def test_passer_clearance_matches_head_on_geometry():
    assert passer_clearance_m(_head_on_geometry()) == pytest.approx(0.65, abs=1e-9)


def test_visibility_boundary_rejects_occluder_taller_than_camera():
    geometry = _head_on_geometry(occluder_height_m=3.5)

    with pytest.raises(ValueError):
        visibility_boundary_m(geometry)


def test_visibility_boundary_rejects_marker_plane_above_camera():
    geometry = SceneGeometry(
        corridor=CorridorGeometry(
            half_length_m=1.0, aisle_half_width_m=0.6, occluder_height_m=0.9
        ),
        camera=CameraGeometry(height_m=0.2, marker_height_m=0.21),
    )

    with pytest.raises(ValueError):
        visibility_boundary_m(geometry)


def test_visibility_boundary_grows_with_taller_occluder():
    # A taller occluder throws a longer shadow, so the yielder must park further out.
    low = visibility_boundary_m(_head_on_geometry(occluder_height_m=0.5))
    high = visibility_boundary_m(_head_on_geometry(occluder_height_m=1.5))

    assert high > low


def test_pull_off_lateral_floors_at_zero_in_narrow_aisle():
    geometry = _head_on_geometry(aisle_half_width_m=0.2)

    assert pull_off_lateral_m(geometry) == 0.0


def test_corridor_geometry_rejects_non_positive_half_length():
    with pytest.raises(ValidationError):
        CorridorGeometry(half_length_m=0.0, aisle_half_width_m=0.6, occluder_height_m=0.9)


def test_scene_geometry_is_frozen():
    geometry = _head_on_geometry()

    with pytest.raises(ValidationError):
        geometry.park_margin_m = 0.5


def test_scene_geometry_defaults_cover_camera_and_robot():
    geometry = _head_on_geometry()

    assert geometry.camera.height_m == 3.0
    assert geometry.robot.safety_radius_m == 0.45
    assert geometry.corridor.axis == "x"


# The head-on asymmetric family's west blocker, mirrored from
# isaac/config/scenarios/family/head_on_asymmetric_w0p2_eopen_o0.yaml: a 0.3 m
# box centred at x = -1.85, so its near face sits at -1.70, 0.70 m past the
# corridor mouth at x = -1.0.
WEST_BLOCKER = StaticObstacleInput(
    obstacle_id="obstacle_1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3
)
EAST_BLOCKER = StaticObstacleInput(
    obstacle_id="obstacle_1", x=1.85, y=0.0, size_x_m=0.3, size_y_m=0.3
)


def test_required_room_matches_head_on_geometry():
    assert required_room_m(_head_on_geometry()) == pytest.approx(1.079, abs=1e-3)


def test_room_is_feasible_when_retreat_is_unbounded():
    assert room_is_feasible(None, _head_on_geometry()) is True


def test_room_is_feasible_at_exactly_the_required_room():
    geometry = _head_on_geometry()

    assert room_is_feasible(required_room_m(geometry), geometry) is True


def test_retreat_room_is_none_without_obstacles():
    assert yield_retreat_room_m((-0.3, 0.0), -1.0, (), _head_on_geometry()) is None


def test_retreat_room_measures_from_mouth_to_nearest_blocker_face():
    room = yield_retreat_room_m((-0.3, 0.0), -1.0, (WEST_BLOCKER,), _head_on_geometry())

    assert room == pytest.approx(0.7, abs=1e-9)


def test_retreat_room_mirrors_on_the_east_side():
    room = yield_retreat_room_m((0.3, 0.0), 1.0, (EAST_BLOCKER,), _head_on_geometry())

    assert room == pytest.approx(0.7, abs=1e-9)


def test_retreat_room_ignores_blocker_on_the_opposite_side():
    # robot_2 retreats east; the west blocker bounds nothing in its path.
    room = yield_retreat_room_m((0.3, 0.0), 1.0, (WEST_BLOCKER,), _head_on_geometry())

    assert room is None


def test_retreat_room_ignores_obstacle_outside_the_lateral_band():
    # Same distance along x, parked one aisle over: outside the 0.6 m band.
    aside = StaticObstacleInput(
        obstacle_id="obstacle_2", x=-1.85, y=1.5, size_x_m=0.3, size_y_m=0.3
    )

    assert yield_retreat_room_m((-0.3, 0.0), -1.0, (aside,), _head_on_geometry()) is None


def test_retreat_room_takes_the_nearest_of_several_blockers():
    far = StaticObstacleInput(
        obstacle_id="obstacle_2", x=-3.0, y=0.0, size_x_m=0.3, size_y_m=0.3
    )

    room = yield_retreat_room_m((-0.3, 0.0), -1.0, (far, WEST_BLOCKER), _head_on_geometry())

    assert room == pytest.approx(0.7, abs=1e-9)


def test_yield_is_infeasible_behind_the_family_west_blocker():
    # 0.70 m of room against 1.079 m required - the 2026-09-25 R2 failure.
    assert yield_feasible((-0.3, 0.0), -1.0, (WEST_BLOCKER,), _head_on_geometry()) is False


def test_yield_is_feasible_on_the_open_side():
    assert yield_feasible((0.3, 0.0), 1.0, (WEST_BLOCKER,), _head_on_geometry()) is True


def test_yield_is_feasible_behind_a_blocker_beyond_the_required_room():
    distant = StaticObstacleInput(
        obstacle_id="obstacle_1", x=-2.3, y=0.0, size_x_m=0.3, size_y_m=0.3
    )

    assert yield_feasible((-0.3, 0.0), -1.0, (distant,), _head_on_geometry()) is True


def test_retreat_room_is_zero_for_a_blocker_straddling_the_mouth():
    straddling = StaticObstacleInput(
        obstacle_id="obstacle_1", x=-1.0, y=0.0, size_x_m=0.3, size_y_m=0.3
    )

    room = yield_retreat_room_m((-0.3, 0.0), -1.0, (straddling,), _head_on_geometry())

    assert room == pytest.approx(0.0, abs=1e-9)


def test_retreat_room_follows_the_declared_axis():
    geometry = _head_on_geometry(axis="y")
    blocker = StaticObstacleInput(
        obstacle_id="obstacle_1", x=0.0, y=-1.85, size_x_m=0.3, size_y_m=0.3
    )

    room = yield_retreat_room_m((0.0, -0.3), -1.0, (blocker,), geometry)

    assert room == pytest.approx(0.7, abs=1e-9)


def _junction_geometry(**arms) -> SceneGeometry:
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x",
            center_m=0.0,
            half_length_m=0.6,
            aisle_half_width_m=0.6,
            occluder_height_m=0.0,
        ),
        arms=arms or None,
    )


def test_arm_geometry_without_arms_returns_the_same_object():
    geometry = _head_on_geometry()

    resolved, side = arm_geometry(geometry, "robot_1")

    assert resolved is geometry
    assert side is None


def test_arm_geometry_leaves_an_unlisted_robot_on_the_corridor():
    geometry = _junction_geometry(robot_3=ArmGeometry(axis="y", side=-1))

    resolved, side = arm_geometry(geometry, "robot_1")

    assert resolved is geometry
    assert side is None


def test_arm_geometry_swaps_only_the_axis_for_a_crossing_arm():
    geometry = _junction_geometry(robot_3=ArmGeometry(axis="y", side=-1))

    resolved, side = arm_geometry(geometry, "robot_3")

    assert side == -1.0
    assert resolved.corridor.axis == "y"
    assert resolved.corridor.model_dump(exclude={"axis"}) == geometry.corridor.model_dump(
        exclude={"axis"}
    )
    assert park_offset_m(resolved) == park_offset_m(geometry)


def test_arm_side_must_be_a_unit_sign():
    with pytest.raises(ValidationError):
        ArmGeometry(axis="y", side=0)


def test_retreat_room_on_a_crossing_arm_runs_along_that_arm():
    # A box 0.9 m past the south mouth of the north-south arm bounds robot_3;
    # the same box is off the east-west lane, so it bounds nothing there.
    geometry = _junction_geometry(robot_3=ArmGeometry(axis="y", side=-1))
    box = StaticObstacleInput(obstacle_id="o", x=0.0, y=-1.65, size_x_m=0.3, size_y_m=0.3)
    resolved, side = arm_geometry(geometry, "robot_3")

    assert yield_retreat_room_m((0.0, -0.3), side, [box], resolved) == pytest.approx(0.9)
    assert yield_retreat_room_m((-0.3, 0.0), -1.0, [box], geometry) is None


def test_same_axis_passer_travels_past_the_parked_yielder():
    geometry = _junction_geometry(
        robot_1=ArmGeometry(axis="x", side=-1), robot_2=ArmGeometry(axis="x", side=1)
    )

    travel = passer_travel_m("robot_1", (-0.22, 0.0), (1.7, -0.34), geometry, "robot_2")

    assert travel == pytest.approx(1.92)


def test_crossing_passer_travels_to_the_far_junction_mouth():
    geometry = _junction_geometry(
        robot_2=ArmGeometry(axis="x", side=1), robot_3=ArmGeometry(axis="y", side=-1)
    )

    travel = passer_travel_m("robot_3", (-0.02, -0.26), (1.7, -0.34), geometry, "robot_2")

    assert travel == pytest.approx(0.6 + 0.26)


def test_crossing_passer_already_past_the_far_mouth_travels_nothing():
    geometry = _junction_geometry(
        robot_2=ArmGeometry(axis="x", side=1), robot_3=ArmGeometry(axis="y", side=-1)
    )

    assert passer_travel_m("robot_3", (0.0, 0.9), (1.7, 0.0), geometry, "robot_2") == 0.0


def test_passer_travel_without_arms_is_the_corridor_axis_distance():
    geometry = _head_on_geometry()

    assert passer_travel_m("robot_1", (0.25, 3.0), (-1.789, 0.0), geometry, "robot_2") == (
        abs(0.25 - -1.789)
    )

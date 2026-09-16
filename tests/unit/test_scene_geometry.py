"""Unit tests for the declared scene geometry M3 derives yield distances from."""
import pytest
from pydantic import ValidationError

from reasoning.rag.scene_geometry import (
    CameraGeometry,
    CorridorGeometry,
    SceneGeometry,
    park_offset_m,
    passer_clearance_m,
    pull_off_lateral_m,
    visibility_boundary_m,
)


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
    assert park_offset_m(_head_on_geometry()) == pytest.approx(1.689, abs=1e-3)


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

import pytest

from isaac.vgu_sim.scenario_builder import _aisle_barrier_geometry


def test_aisle_barrier_geometry_centers_gap_on_origin():
    north, south = _aisle_barrier_geometry(
        nominal_width_m=1.2, effective_width_m=0.55, length_m=0.8, center_x_m=0.0
    )
    north_y, north_half_y, north_half_x = north
    south_y, south_half_y, south_half_x = south

    assert north_y == pytest.approx(0.4375)
    assert north_half_y == pytest.approx(0.1625)
    assert north_half_x == pytest.approx(0.4)
    assert south_y == pytest.approx(-0.4375)
    assert south_half_y == pytest.approx(0.1625)
    assert south_half_x == pytest.approx(0.4)


def test_aisle_barrier_geometry_gap_matches_effective_width():
    nominal_width_m, effective_width_m = 1.2, 0.55
    (north_y, north_half_y, _), (south_y, south_half_y, _) = _aisle_barrier_geometry(
        nominal_width_m, effective_width_m, length_m=0.8, center_x_m=0.0
    )
    gap_width = (north_y - north_half_y) - (south_y + south_half_y)
    assert gap_width == pytest.approx(effective_width_m)


def test_aisle_barrier_geometry_rejects_effective_width_not_narrower_than_nominal():
    with pytest.raises(ValueError, match="must be in"):
        _aisle_barrier_geometry(
            nominal_width_m=1.2, effective_width_m=1.2, length_m=0.8, center_x_m=0.0
        )
    with pytest.raises(ValueError, match="must be in"):
        _aisle_barrier_geometry(
            nominal_width_m=1.2, effective_width_m=0.0, length_m=0.8, center_x_m=0.0
        )

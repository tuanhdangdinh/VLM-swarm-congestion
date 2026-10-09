"""Unit tests for the rack-clearance builder primitive (v3 S1b).

Covers the pure-Python half: `RackClearanceConfig` validation, the shared
remnant geometry (`rack_clearance_remnants`) and the Nav2 map rasterizer
(`rasterize_rack_clearance`). The USD half (`scenario_builder.
_author_rack_clearance` + `validation.validate_rack_clearance`) needs `pxr`
and is exercised on the VM by build_scenario / validate_simulation, as for
the loop map.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, world_to_cell
from isaac.vgu_sim.config import (
    LoopMapConfig,
    RackClearanceConfig,
    ScenarioConfig,
    WarehouseConfig,
    rack_clearance_remnants,
    rack_quadrant_rects,
)

BAND = dict(x_min_m=-2.5, x_max_m=2.5, y_min_m=-1.8, y_max_m=1.8)
RES = 0.05


def _area(rects) -> float:
    return sum((x1 - x0) * (y1 - y0) for _, x0, x1, y0, y1 in rects)


def _cell(grid, x, y) -> int:
    row, col = world_to_cell(x, y, WarehouseConfig(), RES)
    return int(grid[row, col])


def test_config_accepts_the_tracked_band():
    cfg = RackClearanceConfig(**BAND)
    assert (cfg.x_min_m, cfg.y_max_m) == (-2.5, 1.8)


@pytest.mark.parametrize(
    "bad",
    [
        dict(BAND, x_min_m=2.5),
        dict(BAND, y_max_m=-1.8),
        dict(BAND, x_max_m=6.0),
        dict(BAND, y_min_m=-4.0),
    ],
)
def test_config_rejects_empty_or_wall_touching_rectangles(bad):
    with pytest.raises(ValueError):
        RackClearanceConfig(**bad)


def test_config_is_frozen_and_rejects_extra_fields():
    with pytest.raises(ValueError):
        RackClearanceConfig(**BAND, z_m=1.0)


def test_quadrants_match_the_shared_rack_blocks():
    quads = rack_quadrant_rects(WarehouseConfig())
    assert [q[0] for q in quads] == ["NE", "NW", "SE", "SW"]
    assert quads[0][1:] == (0.6, 6.0, 0.6, 4.0)


def test_remnants_are_each_quadrant_minus_the_band():
    remnants = rack_clearance_remnants(WarehouseConfig(), RackClearanceConfig(**BAND))
    assert {r[0] for r in remnants} == {
        "NE_east",
        "NE_north",
        "NW_west",
        "NW_north",
        "SE_east",
        "SE_south",
        "SW_west",
        "SW_south",
    }
    quads = _area(rack_quadrant_rects(WarehouseConfig()))
    # Each quadrant loses its 1.9 x 1.2 m overlap with the band.
    assert _area(remnants) == pytest.approx(quads - 4 * 1.9 * 1.2)


def test_a_clearance_missing_a_quadrant_keeps_it_whole():
    cfg = RackClearanceConfig(x_min_m=1.0, x_max_m=2.0, y_min_m=1.0, y_max_m=2.0)
    remnants = rack_clearance_remnants(WarehouseConfig(), cfg)
    assert ("NW_whole", -6.0, -0.6, 0.6, 4.0) in remnants
    assert sum(1 for r in remnants if r[0].startswith("NE_")) == 4


def test_map_clears_the_band_and_keeps_the_remnants():
    grid, _ = build_occupancy_grid(
        WarehouseConfig(),
        obstacles=[],
        resolution_m=RES,
        rack_clearance=RackClearanceConfig(**BAND),
    )
    for x, y in [(-2.0, 1.5), (2.0, -1.5), (1.0, 1.0), (-1.0, -1.0)]:
        assert _cell(grid, x, y) == 255
    for x, y in [(-2.7, 1.5), (2.7, -1.5), (1.0, 2.0), (-1.0, -2.0)]:
        assert _cell(grid, x, y) == 0


def test_map_occupied_cells_equal_the_remnant_footprint():
    grid, _ = build_occupancy_grid(
        WarehouseConfig(),
        obstacles=[],
        resolution_m=RES,
        rack_clearance=RackClearanceConfig(**BAND),
    )
    # All four quadrants cleared (to just inside the walls), then the
    # remnant boxes marked back as plain obstacles: the same cells.
    remnant_boxes = [
        ((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0)
        for _, x0, x1, y0, y1 in rack_clearance_remnants(
            WarehouseConfig(), RackClearanceConfig(**BAND)
        )
    ]
    expected, _ = build_occupancy_grid(
        WarehouseConfig(),
        obstacles=remnant_boxes,
        resolution_m=RES,
        rack_clearance=RackClearanceConfig(x_min_m=-5.8, x_max_m=5.8, y_min_m=-3.8, y_max_m=3.8),
    )
    assert np.array_equal(grid, expected)


def test_no_clearance_leaves_the_default_grid_untouched():
    base, _ = build_occupancy_grid(WarehouseConfig(), obstacles=[], resolution_m=RES)
    again, _ = build_occupancy_grid(
        WarehouseConfig(), obstacles=[], resolution_m=RES, rack_clearance=None
    )
    assert np.array_equal(base, again)


def test_scenario_rejects_rack_clearance_with_a_loop_map():
    loop = LoopMapConfig(
        second_aisle_center_y_m=1.2,
        second_aisle_width_m=0.55,
        second_aisle_x_min_m=0.6,
        second_aisle_x_max_m=2.2,
        connector_center_x_m=1.8,
        connector_width_m=0.55,
    )
    with pytest.raises(ValueError, match="mutually exclusive"):
        ScenarioConfig.model_validate(
            {
                "schema_version": 1,
                "name": "x",
                "family": "normal_flow",
                "seed": 1,
                "duration_sec": 10.0,
                "robots": [],
                "expected_conflict": None,
                "loop_map": loop.model_dump(),
                "rack_clearance": BAND,
            }
        )

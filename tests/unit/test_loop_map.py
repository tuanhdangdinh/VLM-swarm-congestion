"""Unit tests for the loop-map builder extension (v2 build-order step 8).

Covers the pure-Python half of the loop-map carve: `LoopMapConfig`
validation (`isaac/vgu_sim/config.py`) and the Nav2 map rasterizer
(`isaac/scripts/generate_warehouse_map.py`). The USD authoring half
(`scenario_builder._author_loop_connectors`) needs `pxr` and is exercised on
the VM via `validate_simulation.py` / `validate_loop_connectors`, per
`docs/reports/2026-10-02-loop-preemption-smoke.md`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, world_to_cell, write_map
from isaac.vgu_sim.config import LoopMapConfig, WarehouseConfig

VALID_LOOP = dict(
    second_aisle_center_y_m=1.2,
    second_aisle_width_m=0.55,
    second_aisle_x_min_m=0.6,
    second_aisle_x_max_m=2.2,
    connector_center_x_m=1.8,
    connector_width_m=0.55,
)


def _cell(grid, cfg, resolution_m, x, y):
    row, col = world_to_cell(x, y, cfg, resolution_m)
    return grid[row, col]


# ---------------------------------------------------------------------------
# LoopMapConfig validation
# ---------------------------------------------------------------------------


def test_loop_map_config_accepts_the_registered_geometry():
    cfg = LoopMapConfig(**VALID_LOOP)
    assert cfg.second_aisle_center_y_m == 1.2
    assert cfg.connector_remnant_height_m == 0.3  # default


def test_loop_map_config_rejects_second_aisle_not_north_of_primary():
    with pytest.raises(ValueError, match="second_aisle_center_y_m"):
        LoopMapConfig(**{**VALID_LOOP, "second_aisle_center_y_m": 0.0})


def test_loop_map_config_rejects_second_aisle_south_edge_inside_primary_aisle():
    # center 0.5, width 0.55 -> south edge 0.225, inside the 0.6 m primary
    # aisle half-width: no room for a connector band.
    with pytest.raises(ValueError, match="north of the primary aisle"):
        LoopMapConfig(**{**VALID_LOOP, "second_aisle_center_y_m": 0.5})


def test_loop_map_config_rejects_decreasing_x_extent():
    with pytest.raises(ValueError, match="second_aisle_x_min_m must be <"):
        LoopMapConfig(**{**VALID_LOOP, "second_aisle_x_min_m": 2.2, "second_aisle_x_max_m": 0.6})


def test_loop_map_config_rejects_connector_outside_second_aisle_extent():
    with pytest.raises(ValueError, match="must sit inside"):
        LoopMapConfig(**{**VALID_LOOP, "connector_center_x_m": 3.0})


def test_loop_map_config_rejects_non_positive_width():
    with pytest.raises(ValueError):
        LoopMapConfig(**{**VALID_LOOP, "second_aisle_width_m": 0.0})


def test_loop_map_config_is_frozen_and_rejects_extra_fields():
    cfg = LoopMapConfig(**VALID_LOOP)
    with pytest.raises(Exception):
        cfg.second_aisle_center_y_m = 2.0  # type: ignore[misc]
    with pytest.raises(Exception):
        LoopMapConfig(**{**VALID_LOOP, "bogus_field": 1.0})


# ---------------------------------------------------------------------------
# rasterize_loop_map / build_occupancy_grid
# ---------------------------------------------------------------------------


def test_loop_map_none_leaves_default_grid_untouched():
    cfg = WarehouseConfig()
    grid_default, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)
    grid_explicit_none, _ = build_occupancy_grid(
        cfg, obstacles=[], resolution_m=0.05, loop_map=None
    )
    assert (grid_default == grid_explicit_none).all()


def test_loop_map_carves_second_aisle_centerline_free():
    cfg = WarehouseConfig()
    loop_cfg = LoopMapConfig(**VALID_LOOP)
    grid, res = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05, loop_map=loop_cfg)
    assert _cell(grid, cfg, res, 1.4, 1.2) == 255  # FREE


def test_loop_map_carves_connector_centerline_free():
    cfg = WarehouseConfig()
    loop_cfg = LoopMapConfig(**VALID_LOOP)
    grid, res = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05, loop_map=loop_cfg)
    assert _cell(grid, cfg, res, 1.8, 0.75) == 255  # FREE, mid-connector


def test_loop_map_leaves_far_ne_rack_occupied():
    cfg = WarehouseConfig()
    loop_cfg = LoopMapConfig(**VALID_LOOP)
    grid, res = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05, loop_map=loop_cfg)
    assert _cell(grid, cfg, res, 3.3, 2.3) == 0  # OCCUPIED, untouched rack centre


def test_loop_map_leaves_nw_rack_untouched():
    cfg = WarehouseConfig()
    loop_cfg = LoopMapConfig(**VALID_LOOP)
    grid_loop, res = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05, loop_map=loop_cfg)
    grid_default, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)
    assert _cell(grid_loop, cfg, res, -3.3, 2.3) == _cell(grid_default, cfg, res, -3.3, 2.3) == 0


def test_loop_map_leaves_second_aisle_east_of_carve_occupied():
    cfg = WarehouseConfig()
    loop_cfg = LoopMapConfig(**VALID_LOOP)
    grid, res = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05, loop_map=loop_cfg)
    assert _cell(grid, cfg, res, 2.5, 1.2) == 0  # OCCUPIED, beyond second_aisle_x_max_m


def test_loop_map_leaves_connector_band_remnants_occupied():
    cfg = WarehouseConfig()
    loop_cfg = LoopMapConfig(**VALID_LOOP)
    grid, res = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05, loop_map=loop_cfg)
    assert _cell(grid, cfg, res, 1.0, 0.75) == 0  # west-of-connector remnant
    assert _cell(grid, cfg, res, 2.3, 0.75) == 0  # east-of-connector remnant


def test_loop_map_does_not_touch_primary_aisle():
    cfg = WarehouseConfig()
    loop_cfg = LoopMapConfig(**VALID_LOOP)
    grid_loop, res = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05, loop_map=loop_cfg)
    grid_default, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)
    for x in (-2.4, -1.2, 0.0, 1.2, 1.8, 2.3):
        assert _cell(grid_loop, cfg, res, x, 0.0) == _cell(grid_default, cfg, res, x, 0.0)


# ---------------------------------------------------------------------------
# write_map orientation regression (2026-10-02 bug: an erroneous np.flipud
# mirrored every Y-asymmetric feature to the wrong side of y=0; invisible
# for every prior, Y-symmetric scenario map, first exposed by this carve).
# docs/reports/2026-10-02-loop-preemption-smoke.md, "map-orientation bug".
# ---------------------------------------------------------------------------


def test_write_map_round_trip_places_the_carve_on_the_requested_side(tmp_path):
    from PIL import Image

    cfg = WarehouseConfig()
    loop_cfg = LoopMapConfig(**VALID_LOOP)  # second aisle at y = +1.2 (north)
    grid, res = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05, loop_map=loop_cfg)
    write_map(grid, res, cfg, tmp_path, stem="t")

    img = np.array(Image.open(tmp_path / "t.pgm"))
    # Mirror the world_to_cell convention (row 0 = +y edge) exactly: this is
    # what a reader of the saved file (nav2_map_server, empirically
    # confirmed on the VM) uses row 0 for, with no additional flip.
    def file_pixel(x: float, y: float) -> int:
        row, col = world_to_cell(x, y, cfg, res)
        return int(img[row, col])

    # The carve must land at the requested north point, not its south mirror.
    assert file_pixel(1.2, 1.2) == 255
    assert file_pixel(1.2, -1.2) == 0
    assert file_pixel(1.8, 0.75) == 255
    assert file_pixel(1.8, -0.75) == 0


def test_write_map_round_trip_is_unchanged_for_a_y_symmetric_map(tmp_path):
    from PIL import Image

    cfg = WarehouseConfig()
    grid, res = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)  # no loop_map: Y-symmetric
    write_map(grid, res, cfg, tmp_path, stem="t")
    img = np.array(Image.open(tmp_path / "t.pgm"))
    # A Y-symmetric occupancy grid is invariant under the flip this bug
    # removed, so the saved file must equal its own vertical mirror.
    assert (img == np.flipud(img)).all()

import numpy as np

from isaac.vgu_sim.config import WarehouseConfig
from isaac.scripts.generate_warehouse_map import build_occupancy_grid


def test_grid_marks_perimeter_walls_occupied():
    cfg = WarehouseConfig()  # 12.0 x 8.0 m, wall_thickness_m=0.1
    grid, resolution_m = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)

    assert resolution_m == 0.05
    height_px, width_px = grid.shape
    assert width_px == round(cfg.width_m / resolution_m)
    assert height_px == round(cfg.depth_m / resolution_m)
    # Perimeter row/col occupied (value 0 = occupied in PGM map_server convention).
    assert grid[0, :].max() == 0
    assert grid[:, 0].max() == 0


def test_grid_interior_is_free():
    cfg = WarehouseConfig()
    grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)
    height_px, width_px = grid.shape
    assert grid[height_px // 2, width_px // 2] == 255  # free

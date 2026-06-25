"""Unit tests for isaac/scripts/generate_warehouse_map.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the isaac package importable from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, write_map
from isaac.vgu_sim.config import WarehouseConfig


def test_grid_marks_perimeter_walls_occupied():
    cfg = WarehouseConfig()
    grid, resolution_m = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)
    assert resolution_m == 0.05
    height_px, width_px = grid.shape
    assert width_px == round(cfg.width_m / resolution_m)   # 240
    assert height_px == round(cfg.depth_m / resolution_m)  # 160
    assert grid[0, :].max() == 0    # top row all occupied
    assert grid[:, 0].max() == 0    # left col all occupied


def test_grid_interior_is_free():
    cfg = WarehouseConfig()
    grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)
    height_px, width_px = grid.shape
    assert grid[height_px // 2, width_px // 2] == 255


def test_obstacle_marks_cells_occupied():
    cfg = WarehouseConfig()
    # Place 1m×1m obstacle at world origin (warehouse center)
    grid, _ = build_occupancy_grid(cfg, obstacles=[(0.0, 0.0, 1.0, 1.0)], resolution_m=0.05)
    height_px, width_px = grid.shape
    center_col = width_px // 2
    center_row = height_px // 2
    assert grid[center_row, center_col] == 0  # occupied


def test_write_map_creates_pgm_and_yaml(tmp_path):
    cfg = WarehouseConfig()
    grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)
    write_map(grid, 0.05, cfg, tmp_path)
    assert (tmp_path / "warehouse_map.pgm").exists()
    assert (tmp_path / "warehouse_map.yaml").exists()


def test_write_map_yaml_has_correct_origin(tmp_path):
    cfg = WarehouseConfig()
    grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)
    write_map(grid, 0.05, cfg, tmp_path)
    import yaml
    with open(tmp_path / "warehouse_map.yaml") as f:
        data = yaml.safe_load(f)
    assert data["origin"][0] == pytest.approx(-cfg.width_m / 2)
    assert data["origin"][1] == pytest.approx(-cfg.depth_m / 2)
    assert data["resolution"] == pytest.approx(0.05)

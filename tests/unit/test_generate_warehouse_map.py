"""Unit tests for isaac/scripts/generate_warehouse_map.py."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

# Make the isaac package importable from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, load_scenario, write_map
from isaac.vgu_sim.config import AisleBarrierConfig, WarehouseConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
HEAD_ON_SCENARIO = REPO_ROOT / "isaac/config/scenarios/head_on_deadlock.yaml"
BARRIER = AisleBarrierConfig(effective_width_m=0.55, center_x_m=0.0, length_m=2.0)


def _cell_at(grid, cfg: WarehouseConfig, resolution_m: float, x: float, y: float):
    col = round((x + cfg.width_m / 2) / resolution_m)
    row = round((cfg.depth_m / 2 - y) / resolution_m)
    return grid[row, col]


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


def test_grid_marks_warehouse_rack_blocks_occupied():
    cfg = WarehouseConfig()
    resolution_m = 0.05
    grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=resolution_m)

    assert _cell_at(grid, cfg, resolution_m, x=1.0, y=1.0) == 0
    assert _cell_at(grid, cfg, resolution_m, x=-1.0, y=1.0) == 0
    assert _cell_at(grid, cfg, resolution_m, x=1.0, y=-1.0) == 0
    assert _cell_at(grid, cfg, resolution_m, x=-1.0, y=-1.0) == 0


def test_grid_keeps_configured_cross_aisle_clearance_free():
    cfg = WarehouseConfig(nominal_aisle_width_m=1.2)
    resolution_m = 0.05
    grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=resolution_m)

    assert _cell_at(grid, cfg, resolution_m, x=2.0, y=0.55) == 255
    assert _cell_at(grid, cfg, resolution_m, x=2.0, y=0.65) == 0
    assert _cell_at(grid, cfg, resolution_m, x=0.55, y=2.0) == 255
    assert _cell_at(grid, cfg, resolution_m, x=0.65, y=2.0) == 0


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
    with open(tmp_path / "warehouse_map.yaml") as f:
        data = yaml.safe_load(f)
    assert data["origin"][0] == pytest.approx(-cfg.width_m / 2)
    assert data["origin"][1] == pytest.approx(-cfg.depth_m / 2)
    assert data["resolution"] == pytest.approx(0.05)


def _base_and_scenario_grids(resolution_m: float = 0.05):
    cfg = WarehouseConfig()
    base, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=resolution_m)
    scenario, _ = build_occupancy_grid(
        cfg, obstacles=[], resolution_m=resolution_m, aisle_barrier=BARRIER
    )
    return cfg, base, scenario


def _barrier_footprint_mask(shape, cfg: WarehouseConfig, resolution_m: float):
    """Boolean mask of the two barrier blocks, padded by half a cell.

    The padding absorbs the round()-to-nearest-cell rasterization the racks and
    walls also use, so the mask covers the blocks whichever way a boundary cell
    rounds.
    """
    rows, cols = shape
    x = -cfg.width_m / 2 + np.arange(cols)[None, :] * resolution_m
    y = cfg.depth_m / 2 - np.arange(rows)[:, None] * resolution_m
    pad = resolution_m / 2
    half_length = BARRIER.length_m / 2
    inner = BARRIER.effective_width_m / 2
    outer = cfg.nominal_aisle_width_m / 2
    in_x = (x >= BARRIER.center_x_m - half_length - pad) & (
        x <= BARRIER.center_x_m + half_length + pad
    )
    in_y = (abs(y) >= inner - pad) & (abs(y) <= outer + pad)
    return in_x & in_y


def test_scenario_barrier_rasterized_as_occupied():
    cfg, _, scenario = _base_and_scenario_grids()
    # Probe well inside each block, away from the cell-rounding boundaries at
    # |y| = 0.275 / 0.6 and x = +-1.0.
    for y in (0.40, 0.50, -0.40, -0.50):
        for x in (-0.9, 0.0, 0.9):
            assert _cell_at(scenario, cfg, 0.05, x=x, y=y) == 0, f"free at ({x}, {y})"


def test_scenario_barrier_occupies_expected_cell_count():
    _, base, scenario = _base_and_scenario_grids()
    added = int(((base == 255) & (scenario == 0)).sum())

    # Two blocks of 2.0 m x 0.325 m at 0.05 m/cell: 2 * 40 * 6.5 cells, each
    # block rounded to whole cells by the shared round()-to-nearest convention.
    # A range, not 480: the 6.5-cell block depth lands on a rounding tie whose
    # direction is float-representation dependent.
    assert 480 <= added <= 560


def test_scenario_map_is_additive_to_base_map():
    cfg, base, scenario = _base_and_scenario_grids()
    changed = base != scenario
    mask = _barrier_footprint_mask(scenario.shape, cfg, 0.05)

    assert not (changed & ~mask).any(), "barrier changed cells outside its footprint"
    assert (base[changed] == 255).all(), "barrier cleared a cell that was occupied"
    assert (scenario[changed] == 0).all()


def test_scenario_without_barrier_matches_base_map():
    cfg = WarehouseConfig()
    base, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)
    no_barrier, _ = build_occupancy_grid(
        cfg, obstacles=[], resolution_m=0.05, aisle_barrier=None
    )
    assert np.array_equal(base, no_barrier)


def test_scenario_aisle_core_stays_free():
    cfg, _, scenario = _base_and_scenario_grids()
    # The 0.55 m corridor itself must remain drivable, or the global planner
    # cannot route a robot through the barrier at all.
    for x in (-3.0, -1.5, 0.0, 1.5, 3.0):
        for y in (-0.25, 0.0, 0.25):
            assert _cell_at(scenario, cfg, 0.05, x=x, y=y) == 255, f"occupied at ({x}, {y})"


def test_head_on_deadlock_map_yaml_points_at_existing_image():
    map_yaml = MAPS_DIR / "warehouse_map_head_on_deadlock.yaml"
    data = yaml.safe_load(map_yaml.read_text())

    assert (map_yaml.parent / data["image"]).exists()
    assert data["resolution"] == pytest.approx(0.05)
    assert data["origin"][:2] == [-6.0, -4.0]


def test_committed_head_on_deadlock_map_matches_scenario_yaml():
    # A scenario yaml edit leaves the committed map stale and silently wrong,
    # the same trap the scenario USD has; this is the staleness guard.
    scenario = load_scenario(HEAD_ON_SCENARIO)
    cfg = WarehouseConfig()
    expected, _ = build_occupancy_grid(
        cfg, obstacles=[], resolution_m=0.05, aisle_barrier=scenario.aisle_barrier
    )
    committed = np.flipud(
        np.array(Image.open(MAPS_DIR / "warehouse_map_head_on_deadlock.pgm"))
    )

    assert np.array_equal(committed, expected)

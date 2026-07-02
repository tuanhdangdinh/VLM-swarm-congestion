# isaac/scripts/generate_warehouse_map.py
"""CLI: generate a static Nav2 occupancy-grid map from WarehouseConfig.

Usage:
    python isaac/scripts/generate_warehouse_map.py --out-dir ros2_ws/src/swarm_simulation/maps

Writes warehouse_map.pgm and warehouse_map.yaml to the specified output directory.
The map origin is at the warehouse center (world frame), matching Nav2 conventions.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.vgu_sim.config import WarehouseConfig

FREE: int = 255
OCCUPIED: int = 0


def build_occupancy_grid(
    config: WarehouseConfig,
    obstacles: list[tuple[float, float, float, float]],
    resolution_m: float,
) -> tuple[np.ndarray, float]:
    """Build a uint8 occupancy grid from warehouse dimensions and obstacle list.

    The grid uses the map_server coordinate convention:
      - Row 0 corresponds to the world +y edge (north wall).
      - Column 0 corresponds to the world -x edge (west wall).
      - World origin (0, 0) is at the warehouse center.
      - Cell (row, col) covers world coords:
          x = -config.width_m/2 + col * resolution_m
          y =  config.depth_m/2 - row * resolution_m

    Cells are FREE (255) by default. Perimeter walls, warehouse rack blocks,
    and obstacle footprints are marked OCCUPIED (0).

    Args:
        config: Warehouse geometry (width_m, depth_m, wall_thickness_m).
        obstacles: Axis-aligned obstacle boxes as
            ``(center_x, center_y, width_m, depth_m)`` in world coordinates
            (world origin at warehouse center).
        resolution_m: Meters per pixel. Must be > 0.

    Returns:
        Tuple of ``(grid, resolution_m)`` where ``grid`` is a uint8 numpy
        array with shape ``(height_px, width_px)``.
    """
    width_px = round(config.width_m / resolution_m)
    height_px = round(config.depth_m / resolution_m)
    grid = np.full((height_px, width_px), FREE, dtype=np.uint8)

    # Mark perimeter walls.
    wall_px = max(1, round(config.wall_thickness_m / resolution_m))
    # Top and bottom walls (rows)
    grid[:wall_px, :] = OCCUPIED
    grid[height_px - wall_px:, :] = OCCUPIED
    # Left and right walls (columns)
    grid[:, :wall_px] = OCCUPIED
    grid[:, width_px - wall_px:] = OCCUPIED

    # Mark static rack blocks using the same geometry as warehouse_builder.py:
    # four occupied quadrants leave a cross-shaped aisle centered at world (0, 0).
    for rack in _rack_block_obstacles(config):
        _mark_obstacle(grid, config, rack, resolution_m)

    # Mark scenario/dynamic obstacle footprints.
    for obstacle in obstacles:
        _mark_obstacle(grid, config, obstacle, resolution_m)

    return grid, resolution_m


def _rack_block_obstacles(config: WarehouseConfig) -> list[tuple[float, float, float, float]]:
    aisle_half_width = config.nominal_aisle_width_m / 2.0
    warehouse_half_width = config.width_m / 2.0
    warehouse_half_depth = config.depth_m / 2.0
    rack_half_width = (warehouse_half_width - aisle_half_width) / 2.0
    rack_half_depth = (warehouse_half_depth - aisle_half_width) / 2.0

    if rack_half_width <= 0 or rack_half_depth <= 0:
        return []

    return [
        (
            aisle_half_width + rack_half_width,
            aisle_half_width + rack_half_depth,
            rack_half_width * 2.0,
            rack_half_depth * 2.0,
        ),
        (
            -aisle_half_width - rack_half_width,
            aisle_half_width + rack_half_depth,
            rack_half_width * 2.0,
            rack_half_depth * 2.0,
        ),
        (
            aisle_half_width + rack_half_width,
            -aisle_half_width - rack_half_depth,
            rack_half_width * 2.0,
            rack_half_depth * 2.0,
        ),
        (
            -aisle_half_width - rack_half_width,
            -aisle_half_width - rack_half_depth,
            rack_half_width * 2.0,
            rack_half_depth * 2.0,
        ),
    ]


def _mark_obstacle(
    grid: np.ndarray,
    config: WarehouseConfig,
    obstacle: tuple[float, float, float, float],
    resolution_m: float,
) -> None:
    center_x, center_y, obs_width_m, obs_depth_m = obstacle
    # Convert world-frame obstacle bounds to pixel indices.
    # World x maps to column: col = (x + config.width_m/2) / resolution_m
    # World y maps to row:    row = (config.depth_m/2 - y) / resolution_m
    x_min = center_x - obs_width_m / 2
    x_max = center_x + obs_width_m / 2
    y_min = center_y - obs_depth_m / 2
    y_max = center_y + obs_depth_m / 2

    col_min = round((x_min + config.width_m / 2) / resolution_m)
    col_max = round((x_max + config.width_m / 2) / resolution_m)
    # Row increases as y decreases (row 0 = +y edge).
    row_min = round((config.depth_m / 2 - y_max) / resolution_m)
    row_max = round((config.depth_m / 2 - y_min) / resolution_m)

    height_px, width_px = grid.shape
    col_min = max(0, col_min)
    col_max = min(width_px, col_max)
    row_min = max(0, row_min)
    row_max = min(height_px, row_max)

    grid[row_min:row_max, col_min:col_max] = OCCUPIED


def write_map(grid: np.ndarray, resolution_m: float, config: WarehouseConfig, out_dir: Path) -> None:
    """Write occupancy grid to PGM and YAML files in out_dir.

    The PGM image is flipped vertically before saving because PIL row 0 is the
    top of the image, while the grid's row 0 is the world +y (north) edge —
    these happen to match, but np.flipud ensures the PGM file has the correct
    orientation when map_server loads it with origin at the bottom-left.

    Args:
        grid: uint8 occupancy grid array with shape (height_px, width_px).
        resolution_m: Meters per pixel.
        config: Warehouse geometry used to compute the map origin.
        out_dir: Directory where warehouse_map.pgm and warehouse_map.yaml are written.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    pgm_path = out_dir / "warehouse_map.pgm"
    yaml_path = out_dir / "warehouse_map.yaml"

    Image.fromarray(np.flipud(grid), mode="L").save(pgm_path)

    origin_x = -config.width_m / 2
    origin_y = -config.depth_m / 2

    map_data = {
        "image": "warehouse_map.pgm",
        "resolution": resolution_m,
        "origin": [origin_x, origin_y, 0.0],
        "negate": 0,
        "occupied_thresh": 0.65,
        "free_thresh": 0.196,
    }

    with open(yaml_path, "w") as f:
        yaml.dump(map_data, f, default_flow_style=False, sort_keys=False)


def main() -> None:
    """Entry point for the warehouse map generator CLI."""
    parser = argparse.ArgumentParser(description="Generate Nav2 static map from WarehouseConfig")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory for map files")
    parser.add_argument("--resolution-m", type=float, default=0.05, help="Meters per pixel (default: 0.05)")
    args = parser.parse_args()

    config = WarehouseConfig()
    grid, resolution_m = build_occupancy_grid(config, obstacles=[], resolution_m=args.resolution_m)
    write_map(grid, resolution_m, config, args.out_dir)
    print(f"Map written to: {args.out_dir / 'warehouse_map.pgm'} and {args.out_dir / 'warehouse_map.yaml'}")


if __name__ == "__main__":
    main()

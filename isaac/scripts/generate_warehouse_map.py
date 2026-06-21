"""Author a static nav2_map_server occupancy grid from the known warehouse
geometry (WarehouseConfig) and obstacle layout (FR6.5.x).

Static-map shortcut (spec phase2-nav2-stack.md §4 Option A): the warehouse
layout is deterministic, so a one-shot script replaces slam_toolbox.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from isaac.vgu_sim.config import WarehouseConfig

OCCUPIED = 0
FREE = 255


def build_occupancy_grid(
    config: WarehouseConfig,
    obstacles: list[tuple[float, float, float, float]],
    resolution_m: float,
) -> tuple[np.ndarray, float]:
    """Build a free/occupied grid for the warehouse perimeter and obstacles.

    Args:
        config: Warehouse dimensions and wall thickness.
        obstacles: `(center_x, center_y, width_m, depth_m)` axis-aligned boxes
            in world coordinates, world origin at the warehouse center.
        resolution_m: Meters per pixel.

    Returns:
        `(grid, resolution_m)` where `grid` is `uint8`, row 0 = world `+y` edge,
        col 0 = world `-x` edge (map_server's image-to-world convention with
        a `[-width/2, -depth/2]` origin, set to match in `write_map`).
    """
    width_px = round(config.width_m / resolution_m)
    height_px = round(config.depth_m / resolution_m)
    grid = np.full((height_px, width_px), FREE, dtype=np.uint8)

    wall_px = max(1, round(config.wall_thickness_m / resolution_m))
    grid[:wall_px, :] = OCCUPIED
    grid[-wall_px:, :] = OCCUPIED
    grid[:, :wall_px] = OCCUPIED
    grid[:, -wall_px:] = OCCUPIED

    for cx, cy, w, d in obstacles:
        x0 = round((cx - w / 2 + config.width_m / 2) / resolution_m)
        x1 = round((cx + w / 2 + config.width_m / 2) / resolution_m)
        y0 = round((cy - d / 2 + config.depth_m / 2) / resolution_m)
        y1 = round((cy + d / 2 + config.depth_m / 2) / resolution_m)
        grid[max(0, y0):min(height_px, y1), max(0, x0):min(width_px, x1)] = OCCUPIED

    return grid, resolution_m


def write_map(grid: np.ndarray, resolution_m: float, config: WarehouseConfig, out_dir: Path) -> None:
    """Write `warehouse_map.pgm` and `warehouse_map.yaml` to `out_dir`."""
    pgm_path = out_dir / "warehouse_map.pgm"
    yaml_path = out_dir / "warehouse_map.yaml"
    # PGM row 0 is the top of the image; map_server expects row 0 = +y, so flip.
    Image.fromarray(np.flipud(grid), mode="L").save(pgm_path)
    yaml_path.write_text(
        "image: warehouse_map.pgm\n"
        f"resolution: {resolution_m}\n"
        f"origin: [{-config.width_m / 2}, {-config.depth_m / 2}, 0.0]\n"
        "negate: 0\n"
        "occupied_thresh: 0.65\n"
        "free_thresh: 0.196\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--resolution-m", type=float, default=0.05)
    args = parser.parse_args()

    config = WarehouseConfig()
    # Obstacle layout: read from the scenario's timed_obstacles / static assets
    # as they're added. Empty for the Phase 2 baseline map (perimeter only);
    # Task 8's acceptance test adds a static obstacle directly in Isaac, not
    # in the map, so Nav2's costmap obstacle *layer* (not the static map)
    # must detect it via /scan — this keeps the map authoring decoupled from
    # per-scenario obstacle placement.
    grid, resolution_m = build_occupancy_grid(config, obstacles=[], resolution_m=args.resolution_m)
    write_map(grid, resolution_m, config, args.out_dir)


if __name__ == "__main__":
    main()

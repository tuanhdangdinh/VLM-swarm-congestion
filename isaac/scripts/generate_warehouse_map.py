# isaac/scripts/generate_warehouse_map.py
"""CLI: generate a static Nav2 occupancy-grid map from WarehouseConfig.

Usage:
    python isaac/scripts/generate_warehouse_map.py --out-dir ros2_ws/src/swarm_simulation/maps
    python isaac/scripts/generate_warehouse_map.py --out-dir ros2_ws/src/swarm_simulation/maps \
        --scenario isaac/config/scenarios/head_on_deadlock.yaml

Writes warehouse_map.pgm and warehouse_map.yaml to the specified output directory.
The map origin is at the warehouse center (world frame), matching Nav2 conventions.

Per-scenario maps exist because a scenario may author geometry that the default
map does not contain -- the `aisle_barrier` blocks are physical collision bodies
in Isaac, so the lidar sees corridor walls at |y| = effective_width/2 that the
default map calls open aisle. AMCL then converges to a ~1 m offset (measured
with `localization:=amcl`) and the global planner routes straight through the
blocks. Passing `--scenario` bakes those runtime bodies into their own map,
selected at launch via `nav2_robot.launch.py`'s `map_yaml` argument, leaving the
default map untouched for scenarios that add nothing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.vgu_sim.config import AisleBarrierConfig, ScenarioConfig, WarehouseConfig

FREE: int = 255
OCCUPIED: int = 0


def build_occupancy_grid(
    config: WarehouseConfig,
    obstacles: list[tuple[float, float, float, float]],
    resolution_m: float,
    aisle_barrier: AisleBarrierConfig | None = None,
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
        aisle_barrier: Scenario aisle-barrier geometry, or None for the default
            map. When given, the two barrier blocks are marked OCCUPIED on top
            of everything above.

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

    if aisle_barrier is not None:
        rasterize_aisle_barrier(grid, aisle_barrier, config, resolution_m)

    return grid, resolution_m


def rasterize_aisle_barrier(
    grid: np.ndarray,
    barrier: AisleBarrierConfig,
    config: WarehouseConfig,
    resolution_m: float,
) -> None:
    """Mark a scenario's two aisle-barrier blocks OCCUPIED on an existing grid.

    Mirrors ``isaac.vgu_sim.scenario_builder._author_aisle_barrier`` exactly, so
    the map agrees with the collision bodies Isaac authors: each block spans
    ``x`` in ``center_x_m +- length_m/2`` and ``|y|`` in
    ``[effective_width_m/2, nominal_aisle_width_m/2]``. Mutates ``grid`` in
    place and is a no-op when the requested corridor is no narrower than the
    nominal aisle, matching the builder's own early return.

    Args:
        grid: uint8 occupancy grid to mutate, shape ``(height_px, width_px)``.
        barrier: Scenario aisle-barrier geometry.
        config: Warehouse geometry supplying the nominal aisle width the blocks
            are measured against, and the grid's world-to-cell mapping.
        resolution_m: Meters per pixel of ``grid``.
    """
    base_half = config.nominal_aisle_width_m / 2.0
    effective_half = barrier.effective_width_m / 2.0
    if effective_half >= base_half:
        return

    block_half_x = barrier.length_m / 2.0
    block_half_y = (base_half - effective_half) / 2.0
    block_center_y = effective_half + block_half_y

    # _mark_obstacle takes full extents, while the USD authoring path takes
    # half-extents as a Gf.Vec3f scale -- hence the doubling here.
    for center_y in (block_center_y, -block_center_y):
        _mark_obstacle(
            grid,
            config,
            (barrier.center_x_m, center_y, block_half_x * 2.0, block_half_y * 2.0),
            resolution_m,
        )


def world_to_cell(
    x: float,
    y: float,
    config: WarehouseConfig,
    resolution_m: float,
) -> tuple[int, int]:
    """Map one world-frame point to its ``(row, col)`` grid index.

    Inverse of the convention documented on `build_occupancy_grid`: row 0 is the
    world +y edge and column 0 the world -x edge, with the world origin at the
    warehouse center. The result is rounded, not floored, and is not clamped to
    the grid bounds.

    Args:
        x: World x coordinate in meters.
        y: World y coordinate in meters.
        config: Warehouse geometry defining the grid extent.
        resolution_m: Meters per pixel.

    Returns:
        Grid index as ``(row, col)``.
    """
    col = round((x + config.width_m / 2) / resolution_m)
    row = round((config.depth_m / 2 - y) / resolution_m)
    return row, col


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
    x_min = center_x - obs_width_m / 2
    x_max = center_x + obs_width_m / 2
    y_min = center_y - obs_depth_m / 2
    y_max = center_y + obs_depth_m / 2

    # Row increases as y decreases (row 0 = +y edge), so the box's +y corner
    # gives the low row index and its -y corner the high one.
    row_min, col_min = world_to_cell(x_min, y_max, config, resolution_m)
    row_max, col_max = world_to_cell(x_max, y_min, config, resolution_m)

    height_px, width_px = grid.shape
    col_min = max(0, col_min)
    col_max = min(width_px, col_max)
    row_min = max(0, row_min)
    row_max = min(height_px, row_max)

    grid[row_min:row_max, col_min:col_max] = OCCUPIED


def write_map(
    grid: np.ndarray,
    resolution_m: float,
    config: WarehouseConfig,
    out_dir: Path,
    stem: str = "warehouse_map",
) -> None:
    """Write occupancy grid to PGM and YAML files in out_dir.

    The PGM image is flipped vertically before saving because PIL row 0 is the
    top of the image, while the grid's row 0 is the world +y (north) edge —
    these happen to match, but np.flipud ensures the PGM file has the correct
    orientation when map_server loads it with origin at the bottom-left.

    Args:
        grid: uint8 occupancy grid array with shape (height_px, width_px).
        resolution_m: Meters per pixel.
        config: Warehouse geometry used to compute the map origin.
        out_dir: Directory where the PGM and YAML files are written.
        stem: Basename without extension for both files, e.g. `warehouse_map`
            or `warehouse_map_head_on_deadlock`.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    pgm_path = out_dir / f"{stem}.pgm"
    yaml_path = out_dir / f"{stem}.yaml"

    Image.fromarray(np.flipud(grid), mode="L").save(pgm_path)

    origin_x = -config.width_m / 2
    origin_y = -config.depth_m / 2

    map_data = {
        "image": pgm_path.name,
        "resolution": resolution_m,
        "origin": [origin_x, origin_y, 0.0],
        "negate": 0,
        "occupied_thresh": 0.65,
        "free_thresh": 0.196,
    }

    with open(yaml_path, "w") as f:
        yaml.dump(map_data, f, default_flow_style=False, sort_keys=False)


def load_scenario(path: Path) -> ScenarioConfig:
    """Load and validate one scenario YAML config.

    Args:
        path: Path to a file under `isaac/config/scenarios/`.

    Returns:
        The validated scenario config.
    """
    with open(path) as f:
        return ScenarioConfig.model_validate(yaml.safe_load(f))


def main() -> None:
    """Entry point for the warehouse map generator CLI."""
    parser = argparse.ArgumentParser(description="Generate Nav2 static map from WarehouseConfig")
    parser.add_argument(
        "--out-dir", type=Path, required=True, help="Output directory for map files"
    )
    parser.add_argument(
        "--resolution-m", type=float, default=0.05, help="Meters per pixel (default: 0.05)"
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=None,
        help="Scenario YAML (isaac/config/scenarios/*.yaml). Bakes that scenario's "
        "aisle_barrier blocks into the map so AMCL and the global planner see them.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output basename without extension (default: warehouse_map, or "
        "warehouse_map_<scenario name> when --scenario is given)",
    )
    args = parser.parse_args()

    scenario = load_scenario(args.scenario) if args.scenario is not None else None
    barrier = scenario.aisle_barrier if scenario is not None else None
    default_stem = "warehouse_map" if scenario is None else f"warehouse_map_{scenario.name}"
    stem = args.output or default_stem

    config = WarehouseConfig()
    grid, resolution_m = build_occupancy_grid(
        config, obstacles=[], resolution_m=args.resolution_m, aisle_barrier=barrier
    )
    write_map(grid, resolution_m, config, args.out_dir, stem=stem)
    print(f"Map written to: {args.out_dir / f'{stem}.pgm'} and {args.out_dir / f'{stem}.yaml'}")


if __name__ == "__main__":
    main()

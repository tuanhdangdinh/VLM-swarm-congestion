# isaac/vgu_sim/scenario_builder.py
from __future__ import annotations

import os
from pathlib import Path

from isaac.vgu_sim.config import AisleBarrierConfig, ScenarioConfig, WarehouseConfig
from isaac.vgu_sim.marker_asset import author_aruco_marker
from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path, obstacle_asset_path


class ScenarioBuildError(Exception):
    pass


def build_scenario_stage(
    config: ScenarioConfig,
    *,
    warehouse_path: Path,
    warehouse_config: WarehouseConfig,
    robot_asset_path: Path,
    output_path: Path,
) -> Path:
    from pxr import Kind, Usd, UsdGeom

    if not warehouse_path.exists():
        raise ScenarioBuildError(f"Warehouse asset missing: {warehouse_path}")
    if not robot_asset_path.exists():
        raise ScenarioBuildError(f"Robot asset missing: {robot_asset_path}")

    stage = Usd.Stage.CreateNew(str(output_path))

    stage.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetTimeCodesPerSecond(60.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    world.GetPrim().SetMetadata("kind", Kind.Tokens.assembly)

    rel_warehouse = _relative_path(output_path.parent, warehouse_path)
    root_layer = stage.GetRootLayer()
    root_layer.subLayerPaths.append(str(rel_warehouse))

    stage.SetEditTarget(stage.GetRootLayer())

    UsdGeom.Xform.Define(stage, "/World/Robots")
    UsdGeom.Xform.Define(stage, "/World/ROSGraphs")

    for robot_cfg in config.robots:
        _author_robot(stage, robot_cfg, robot_asset_path, output_path.parent)

    UsdGeom.Xform.Define(stage, "/World/DynamicObstacles")
    for obs in config.timed_obstacles:
        _author_obstacle(stage, obs, output_path.parent)

    if config.aisle_barrier is not None:
        _author_aisle_barrier(stage, config.aisle_barrier, warehouse_config)

    meta = stage.DefinePrim("/World/Scenario/Metadata")
    meta.SetMetadata("customData", {
        "name": config.name,
        "seed": config.seed,
        "duration_sec": config.duration_sec,
        "schema_version": config.schema_version,
    })

    _validate_references(stage, output_path)
    stage.Save()
    return output_path


def _author_robot(stage, robot_cfg, robot_asset_path: Path, scenario_dir: Path) -> None:
    from pxr import Gf, Kind, UsdGeom

    prim_path = f"/World/Robots/{robot_cfg.robot_id}"
    robot_prim = stage.DefinePrim(prim_path)
    robot_prim.SetMetadata("kind", Kind.Tokens.component)

    rel_robot = _relative_path(scenario_dir, robot_asset_path)
    robot_prim.GetReferences().AddReference(str(rel_robot))

    xform = UsdGeom.Xformable(robot_prim)
    s = robot_cfg.spawn
    xform.AddTranslateOp().Set(Gf.Vec3d(s.x, s.y, 0.0))
    xform.AddRotateZOp().Set(float(s.yaw_rad * 180.0 / 3.141592653589793))

    goal_path = f"/World/Scenario/Goals/{robot_cfg.robot_id}_goal"
    goal_prim = UsdGeom.Sphere.Define(stage, goal_path)
    goal_prim.CreateRadiusAttr().Set(0.1)
    g = robot_cfg.goal
    UsdGeom.Xformable(goal_prim.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(g.x, g.y, 0.0))

    stage.DefinePrim(f"/World/ROSGraphs/{robot_cfg.robot_id}")

    # Per-robot ArUco marker keyed by marker_id. The imported robot USD is shared,
    # so the marker is authored per-robot here. The dictionary is resolved from the
    # single source of truth (aruco.yaml) — never hardcoded — so it can't desync
    # from generation. Texture path is relative to the scenario stage so the .usda
    # is relocatable.
    marker_png = marker_png_path(aruco_dict_name(), robot_cfg.marker_id)
    rel_marker = _relative_path(scenario_dir, marker_png)
    author_aruco_marker(stage, prim_path, str(rel_marker))


def _author_obstacle(stage, obs_cfg, scenario_dir: Path) -> None:
    from pxr import Gf, UsdGeom

    prim_path = f"/World/DynamicObstacles/{obs_cfg.obstacle_id}"
    prim = UsdGeom.Xform.Define(stage, prim_path)

    asset_path = obstacle_asset_path(obs_cfg.asset)
    rel_asset = _relative_path(scenario_dir, asset_path)
    prim.GetPrim().GetReferences().AddReference(str(rel_asset))

    p = obs_cfg.pose
    xform = UsdGeom.Xformable(prim.GetPrim())
    xform.AddTranslateOp().Set(Gf.Vec3d(p.x, p.y, 0.0))
    xform.AddRotateZOp().Set(float(p.yaw_rad * 180.0 / 3.141592653589793))

    # A static obstacle (no `remove_at_sec`, scheduled to spawn at sim start)
    # is active from the first frame: `EventScheduler` never wires real
    # activate/deactivate callbacks in `runner.py` today (it is constructed
    # with the default no-op callbacks), so an obstacle that the scheduler
    # would otherwise need to "spawn" at runtime has no way to actually
    # become visible/collidable yet. Authoring it active here is the
    # currently-correct behavior for the static, never-removed case this
    # task needs; an obstacle with `remove_at_sec` set still starts inactive
    # since the runtime activation path is the one that would need to flip
    # it, and that path is not wired.
    prim.GetPrim().SetActive(obs_cfg.spawn_at_sec <= 0.0)


def _aisle_barrier_geometry(
    nominal_width_m: float,
    effective_width_m: float,
    length_m: float,
    center_x_m: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Compute (center_y, half_extent_y, half_extent_x) for the two barrier halves.

    The barriers narrow the aisle's passable width from `nominal_width_m`
    (the warehouse's full reusable aisle) down to `effective_width_m`,
    centered on y=0, by occupying the two strips between the effective gap
    and the nominal aisle edges. Both barriers span `length_m` along x,
    centered at `center_x_m`.

    Args:
        nominal_width_m: Full nominal aisle width (e.g. `WarehouseConfig.nominal_aisle_width_m`).
        effective_width_m: Desired passable gap width after narrowing.
        length_m: Barrier extent along x.
        center_x_m: Barrier center along x.

    Returns:
        `((north_y, north_half_y, half_x), (south_y, south_half_y, half_x))`.

    Raises:
        ValueError: If `effective_width_m` is not strictly between 0 and `nominal_width_m`.
    """
    if not (0.0 < effective_width_m < nominal_width_m):
        raise ValueError(
            f"effective_width_m must be in (0, {nominal_width_m}); got {effective_width_m}"
        )
    half_nominal = nominal_width_m / 2.0
    half_effective = effective_width_m / 2.0
    half_y = (half_nominal - half_effective) / 2.0
    center_y = (half_nominal + half_effective) / 2.0
    half_x = length_m / 2.0
    return (center_y, half_y, half_x), (-center_y, half_y, half_x)


def _author_aisle_barrier(
    stage, barrier_cfg: AisleBarrierConfig, warehouse_config: WarehouseConfig
) -> None:
    from pxr import Gf, UsdGeom, UsdPhysics

    (north_y, half_y, half_x), (south_y, _, _) = _aisle_barrier_geometry(
        warehouse_config.nominal_aisle_width_m,
        barrier_cfg.effective_width_m,
        barrier_cfg.length_m,
        barrier_cfg.center_x_m,
    )
    half_h = warehouse_config.wall_height_m / 2.0

    UsdGeom.Xform.Define(stage, "/World/Environment/AisleBarrier")
    for name, y in [("north", north_y), ("south", south_y)]:
        cube = UsdGeom.Cube.Define(stage, f"/World/Environment/AisleBarrier/{name}")
        cube.CreateSizeAttr(2.0)
        cube.AddTranslateOp().Set(Gf.Vec3f(barrier_cfg.center_x_m, y, half_h))
        cube.AddScaleOp().Set(Gf.Vec3f(half_x, half_y, half_h))
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())


def _relative_path(from_dir: Path, to_path: Path) -> Path:
    try:
        return to_path.resolve().relative_to(from_dir.resolve())
    except ValueError:
        return Path(os.path.relpath(str(to_path), str(from_dir)))


def _validate_references(stage, output_path: Path) -> None:
    errors = [e for e in stage.GetCompositionErrors()]
    if errors:
        raise ScenarioBuildError(
            f"Unresolved composition errors in {output_path}: {errors}"
        )

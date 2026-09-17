# isaac/vgu_sim/scenario_builder.py
from __future__ import annotations

import math
import os
from pathlib import Path

from isaac.vgu_sim.config import ObstacleSize, ScenarioConfig, WarehouseConfig
from isaac.vgu_sim.marker_asset import author_aruco_marker
from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path
from isaac.vgu_sim.validation import validate_scenario_obstacles


class ScenarioBuildError(Exception):
    pass


def build_scenario_stage(
    config: ScenarioConfig,
    *,
    warehouse_path: Path,
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
        _author_obstacle(stage, obs)
    _author_static_obstacles(stage, config)
    if config.aisle_barrier is not None:
        _author_aisle_barrier(stage, config.aisle_barrier)

    meta = stage.DefinePrim("/World/Scenario/Metadata")
    meta.SetMetadata("customData", {
        "name": config.name,
        "family": config.family,
        "seed": config.seed,
        "duration_sec": config.duration_sec,
        "schema_version": config.schema_version,
    })

    _validate_references(stage, output_path)
    validate_scenario_obstacles(stage, config)
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


def _author_box(
    stage,
    path: str,
    translate: tuple[float, float],
    yaw_rad: float,
    size: ObstacleSize,
    color: tuple[float, float, float],
) -> None:
    """Author a collidable box of `size` standing on the floor at `translate`.

    The cube's size attribute is 2.0 (half-extent 1.0), so the scale is the
    half-extent in meters; z is raised by half the height so the box rests on
    the floor rather than straddling it.

    Args:
        stage: USD stage being authored.
        path: Prim path for the box.
        translate: World-frame `(x, y)` center in meters.
        yaw_rad: Rotation about world Z in radians.
        size: Bounding-box size in meters.
        color: Display color as `(r, g, b)` in 0..1.
    """
    from pxr import Gf, UsdGeom, UsdPhysics

    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(2.0)
    cube.CreateDisplayColorAttr([color])
    cube.AddTranslateOp().Set(
        Gf.Vec3f(float(translate[0]), float(translate[1]), float(size.z_m / 2.0))
    )
    if yaw_rad != 0.0:
        cube.AddRotateZOp().Set(float(math.degrees(yaw_rad)))
    cube.AddScaleOp().Set(
        Gf.Vec3f(float(size.x_m / 2.0), float(size.y_m / 2.0), float(size.z_m / 2.0))
    )
    UsdPhysics.CollisionAPI.Apply(cube.GetPrim())


def _author_static_obstacles(stage, config: ScenarioConfig) -> None:
    from pxr import UsdGeom

    # The root is defined even with no obstacles so downstream tooling and
    # validation can key on a stable namespace.
    UsdGeom.Xform.Define(stage, "/World/Scenario/StaticObstacles")
    for obs_cfg in config.static_obstacles:
        _author_box(
            stage,
            f"/World/Scenario/StaticObstacles/{obs_cfg.obstacle_id}",
            (obs_cfg.pose.x, obs_cfg.pose.y),
            obs_cfg.pose.yaw_rad,
            obs_cfg.size,
            (0.5, 0.5, 0.5),
        )


def _author_obstacle(stage, obs_cfg) -> None:
    prim_path = f"/World/DynamicObstacles/{obs_cfg.obstacle_id}"
    _author_box(
        stage,
        prim_path,
        (obs_cfg.pose.x, obs_cfg.pose.y),
        obs_cfg.pose.yaw_rad,
        obs_cfg.size,
        (0.8, 0.3, 0.3),
    )
    # Timed obstacles stay deactivated until the runner spawns them at
    # spawn_at_sec; the geometry is authored up front so the prim only has to
    # be reactivated.
    stage.GetPrimAtPath(prim_path).SetActive(False)


def _author_aisle_barrier(stage, barrier_cfg) -> None:
    """Add two yellow blocks above/below the robots to narrow the crossing gap."""
    from pxr import Gf, UsdGeom, UsdPhysics

    warehouse = WarehouseConfig()
    base_half = warehouse.nominal_aisle_width_m / 2.0
    effective_half = barrier_cfg.effective_width_m / 2.0
    if effective_half >= base_half:
        return

    barrier_root = UsdGeom.Xform.Define(stage, "/World/Scenario/AisleBarriers")
    barrier_root.GetPrim().SetMetadata(
        "customData",
        {
            "effective_width_m": barrier_cfg.effective_width_m,
            "center_x_m": barrier_cfg.center_x_m,
            "length_m": barrier_cfg.length_m,
        },
    )

    z_center = 0.45
    z_half = 0.45
    # No clamp to the crossing-aisle half-width: blocks longer than the
    # junction sit at y in [effective_half, base_half], which is open
    # horizontal-aisle floor in front of the racks (rack walls start at
    # |y| > base_half), so a corridor-length barrier (e.g. 2.0 m) is
    # geometrically safe. The old min(length/2, base_half-0.02) clamp
    # silently truncated a requested 2.0 m corridor to 1.16 m.
    block_half_x = barrier_cfg.length_m / 2.0
    block_half_y = (base_half - effective_half) / 2.0
    block_center_y = effective_half + block_half_y
    for name, y in (("north", block_center_y), ("south", -block_center_y)):
        _author_barrier_cube(
            stage,
            f"/World/Scenario/AisleBarriers/{name}",
            Gf.Vec3f(float(barrier_cfg.center_x_m), float(y), z_center),
            Gf.Vec3f(float(block_half_x), float(block_half_y), z_half),
        )


def _author_barrier_cube(stage, path: str, translate, scale) -> None:
    from pxr import UsdGeom, UsdPhysics

    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(2.0)
    cube.CreateDisplayColorAttr([(1.0, 0.82, 0.0)])
    cube.AddTranslateOp().Set(translate)
    cube.AddScaleOp().Set(scale)
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

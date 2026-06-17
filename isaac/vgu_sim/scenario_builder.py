# isaac/vgu_sim/scenario_builder.py
from __future__ import annotations

import os
from pathlib import Path

from isaac.vgu_sim.config import ScenarioConfig
from isaac.vgu_sim.marker_asset import author_aruco_marker
from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path


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


def _author_obstacle(stage, obs_cfg) -> None:
    from pxr import Gf, UsdGeom

    prim_path = f"/World/DynamicObstacles/{obs_cfg.obstacle_id}"
    prim = UsdGeom.Xform.Define(stage, prim_path)

    p = obs_cfg.pose
    UsdGeom.Xformable(prim.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(p.x, p.y, 0.0))
    prim.GetPrim().SetActive(False)


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

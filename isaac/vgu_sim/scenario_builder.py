# isaac/vgu_sim/scenario_builder.py
from __future__ import annotations

import math
import os
from pathlib import Path

from isaac.vgu_sim.config import (
    ROBOT_VISUAL_NO_MARKER_ASSET,
    ROBOT_VISUAL_NO_MARKER_SCALE,
    STATIC_BOX_ASSET,
    ObstacleSize,
    Pose2D,
    ScenarioConfig,
    TimedObstacleConfig,
    WarehouseConfig,
    rack_clearance_remnants,
)
from isaac.vgu_sim.load_prop_asset import author_load_prop
from isaac.vgu_sim.marker_asset import author_aruco_marker
from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path
from isaac.vgu_sim.validation import (
    validate_loop_connectors,
    validate_rack_clearance,
    validate_robot_load_prop,
    validate_scenario_obstacles,
)

# The imported robot asset's variant set. "none" composes the visual meshes
# and static collision shapes only: no articulation, rigid bodies or joints.
_ROBOT_PHYSICS_VARIANT_SET = "Physics"
_ROBOT_PHYSICS_VARIANT_NONE = "none"
_LEGACY_TIMED_BOX_COLOR = (0.8, 0.3, 0.3)
_STATIC_BOX_COLOR = (0.5, 0.5, 0.5)


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
        _author_obstacle(stage, obs, robot_asset_path, output_path.parent)
    _author_static_obstacles(stage, config)
    if config.aisle_barrier is not None:
        _author_aisle_barrier(stage, config.aisle_barrier)
    if config.loop_map is not None:
        _author_loop_connectors(stage, config.loop_map)
    if config.rack_clearance is not None:
        _author_rack_clearance(stage, config.rack_clearance)

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
    validate_loop_connectors(stage, config)
    validate_rack_clearance(stage, config)
    for robot_cfg in config.robots:
        validate_robot_load_prop(
            stage, f"/World/Robots/{robot_cfg.robot_id}", robot_cfg.loaded
        )
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

    # B2-visual pair (priority_visual_r1/r2): a visual-only pallet/load prop,
    # mounted flush to the chassis rear so it cannot occlude the marker and
    # carries no physics API so it cannot appear to Nav2, the lidar, or the
    # safety monitor (isaac.vgu_sim.load_prop_asset).
    if robot_cfg.loaded:
        author_load_prop(stage, prim_path)


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


def _author_obstacle(
    stage, obs_cfg: TimedObstacleConfig, robot_asset_path: Path, scenario_dir: Path
) -> None:
    prim_path = f"/World/DynamicObstacles/{obs_cfg.obstacle_id}"
    if obs_cfg.asset == ROBOT_VISUAL_NO_MARKER_ASSET:
        author_robot_visual_no_marker(
            stage, prim_path, obs_cfg.pose, robot_asset_path, scenario_dir
        )
    else:
        color = _STATIC_BOX_COLOR if obs_cfg.asset == STATIC_BOX_ASSET else _LEGACY_TIMED_BOX_COLOR
        _author_box(
            stage,
            prim_path,
            (obs_cfg.pose.x, obs_cfg.pose.y),
            obs_cfg.pose.yaw_rad,
            obs_cfg.size,
            color,
        )
    # Timed obstacles stay deactivated until the runner spawns them at
    # spawn_at_sec; the geometry is authored up front so the prim only has to
    # be reactivated.
    stage.GetPrimAtPath(prim_path).SetActive(False)


def author_robot_visual_no_marker(
    stage,
    prim_path: str,
    pose: Pose2D,
    robot_asset_path: Path,
    scenario_dir: Path,
    scale: float = ROBOT_VISUAL_NO_MARKER_SCALE,
):
    """Author the robot's visual meshes as an untracked, physics-free prop.

    References the same imported robot asset as the tracked robots, but selects
    its `Physics` variant `none` (no articulation, rigid bodies or joints; the
    asset's collision shapes remain as static colliders) and never authors an
    ArUco marker (markers are per-robot, see `_author_robot`), so M1 has
    nothing to detect. It lives outside `/World/Robots`, where
    `validate_robot_marker` would demand a marker. The prop is uniformly
    scaled and placed so its footprint (bounding-box center in XY) sits at
    `pose`, with `pose.yaw_rad` as its heading.

    Args:
        stage: USD stage being authored.
        prim_path: Prim path for the prop, e.g. `/World/DynamicObstacles/<id>`.
        pose: World-frame footprint center `(x, y)` in meters and heading.
        robot_asset_path: The imported robot USD (turtlebot3_burger.usda).
        scenario_dir: Directory of the scenario stage, for a relative reference.
        scale: Uniform scale applied to the robot asset.

    Returns:
        The authored prop prim (still active; the caller decides activation).

    Raises:
        ScenarioBuildError: If the asset has no `Physics` variant `none`, or
            the composed prop carries physics bodies or a marker mesh.
    """
    from pxr import Gf, Usd, UsdGeom, UsdPhysics

    prim = stage.DefinePrim(prim_path, "Xform")
    prim.GetReferences().AddReference(str(_relative_path(scenario_dir, robot_asset_path)))
    variant_set = prim.GetVariantSets().GetVariantSet(_ROBOT_PHYSICS_VARIANT_SET)
    if _ROBOT_PHYSICS_VARIANT_NONE not in variant_set.GetVariantNames():
        raise ScenarioBuildError(
            f"Robot asset {robot_asset_path} has no {_ROBOT_PHYSICS_VARIANT_SET!r} variant "
            f"{_ROBOT_PHYSICS_VARIANT_NONE!r}; a marker-less visual would carry an "
            "articulation"
        )
    variant_set.SetVariantSelection(_ROBOT_PHYSICS_VARIANT_NONE)

    for descendant in Usd.PrimRange(prim):
        if descendant.HasAPI(UsdPhysics.ArticulationRootAPI) or descendant.HasAPI(
            UsdPhysics.RigidBodyAPI
        ):
            raise ScenarioBuildError(
                f"Marker-less robot visual {prim_path} still carries physics bodies "
                f"at {descendant.GetPath()}"
            )
        if descendant.GetName() == "aruco_marker":
            raise ScenarioBuildError(f"Marker-less robot visual {prim_path} has a marker")

    # Untransformed local bound of the rendered geometry (collision guides
    # excluded), so the footprint center can be placed at `pose`.
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
    )
    local = cache.ComputeUntransformedBound(prim).ComputeAlignedRange()
    if local.IsEmpty():
        center_x, center_y = 0.0, 0.0
    else:
        mid = local.GetMidpoint()
        center_x, center_y = float(mid[0]), float(mid[1])
    cos_y, sin_y = math.cos(pose.yaw_rad), math.sin(pose.yaw_rad)
    offset_x = scale * (cos_y * center_x - sin_y * center_y)
    offset_y = scale * (sin_y * center_x + cos_y * center_y)

    xform = UsdGeom.Xformable(prim)
    xform.AddTranslateOp().Set(
        Gf.Vec3d(float(pose.x - offset_x), float(pose.y - offset_y), 0.0)
    )
    xform.AddRotateZOp().Set(float(math.degrees(pose.yaw_rad)))
    xform.AddScaleOp().Set(Gf.Vec3f(float(scale), float(scale), float(scale)))
    return prim


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


def _author_loop_connectors(stage, loop_cfg) -> None:
    """Carve the second E-W aisle + one new N-S connector into the NE rack.

    The shared `/World/Environment/RackBlocks/NE` cube (authored once in the
    warehouse asset, sublayered by every scenario) is deactivated via an
    `over` in this scenario's own root layer -- the warehouse `.usd` file on
    disk is never touched, so every other scenario's map and physics stay
    byte-identical. Four replacement cubes reconstruct NE's footprint minus
    the second-aisle strip and the new connector notch:

    - two untouched-height (0.9 m) remnants far from the carve, which carry
      no camera-occlusion risk (`docs/reports/2026-10-02-loop-preemption-
      smoke.md`, "Visibility");
    - two reduced-height (`loop_cfg.connector_remnant_height_m`) remnants
      immediately flanking the new connector, lowered so their camera
      shadow does not blanket the second aisle, while staying taller than
      the 0.182 m lidar scan plane so Nav2 still reads them as solid.

    NW/SE/SW rack blocks are untouched. `generate_warehouse_map.py`'s
    `rasterize_loop_map` must carve the identical three world rectangles
    (second aisle + connector) out of the static map, or AMCL/the global
    planner will disagree with what the lidar actually sees here, exactly
    the failure mode that module's own docstring already warns about for
    `aisle_barrier`.
    """
    from pxr import Gf, UsdGeom

    warehouse = WarehouseConfig()
    base_half = warehouse.nominal_aisle_width_m / 2.0
    rack_half_width = (warehouse.width_m / 2.0 - base_half) / 2.0
    rack_half_depth = (warehouse.depth_m / 2.0 - base_half) / 2.0
    ne_x_max = base_half + rack_half_width * 2.0
    ne_y_max = base_half + rack_half_depth * 2.0
    rack_h = 0.9
    low_h = loop_cfg.connector_remnant_height_m

    ne_prim = stage.GetPrimAtPath("/World/Environment/RackBlocks/NE")
    if not ne_prim.IsValid():
        raise ScenarioBuildError(
            "Expected /World/Environment/RackBlocks/NE from the sublayered "
            "warehouse asset before authoring a loop-map override"
        )
    ne_prim.SetActive(False)

    aisle_y_min = loop_cfg.second_aisle_center_y_m - loop_cfg.second_aisle_width_m / 2.0
    aisle_y_max = loop_cfg.second_aisle_center_y_m + loop_cfg.second_aisle_width_m / 2.0
    aisle_x_min = loop_cfg.second_aisle_x_min_m
    aisle_x_max = loop_cfg.second_aisle_x_max_m
    conn_x_min = loop_cfg.connector_center_x_m - loop_cfg.connector_width_m / 2.0
    conn_x_max = loop_cfg.connector_center_x_m + loop_cfg.connector_width_m / 2.0

    loop_root = UsdGeom.Xform.Define(stage, "/World/Scenario/LoopRackBlocks")
    loop_root.GetPrim().SetMetadata(
        "customData",
        {
            "second_aisle_center_y_m": loop_cfg.second_aisle_center_y_m,
            "second_aisle_width_m": loop_cfg.second_aisle_width_m,
            "connector_center_x_m": loop_cfg.connector_center_x_m,
            "connector_remnant_height_m": low_h,
        },
    )

    # (x_min, x_max, y_min, y_max, height) for each NE remainder, matching
    # rasterize_loop_map's three carved rectangles exactly.
    remainders = [
        ("top_slab", base_half, ne_x_max, aisle_y_max, ne_y_max, rack_h),
        ("aisle_east_of_loop", aisle_x_max, ne_x_max, aisle_y_min, aisle_y_max, rack_h),
        ("connector_west_remnant", base_half, conn_x_min, base_half, aisle_y_min, low_h),
        ("connector_east_remnant", conn_x_max, ne_x_max, base_half, aisle_y_min, low_h),
    ]
    for name, x_min, x_max, y_min, y_max, height in remainders:
        half_x = (x_max - x_min) / 2.0
        half_y = (y_max - y_min) / 2.0
        center_x = (x_min + x_max) / 2.0
        center_y = (y_min + y_max) / 2.0
        _author_rack_remnant_cube(
            stage,
            f"/World/Scenario/LoopRackBlocks/{name}",
            Gf.Vec3f(center_x, center_y, height / 2.0),
            Gf.Vec3f(half_x, half_y, height / 2.0),
        )


def _author_rack_clearance(stage, clearance_cfg) -> None:
    """Cut all four shared rack quadrants back to outside a clearance rectangle.

    The loop-map pattern (`_author_loop_connectors`) applied to every
    quadrant: each shared `/World/Environment/RackBlocks/<Q>` cube is
    deactivated via an `over` in this scenario's own root layer (the
    warehouse `.usd` on disk is never touched), and the remnants from
    `config.rack_clearance_remnants` are authored at the shared 0.9 m rack
    height under `/World/Scenario/ClearedRackBlocks`.
    `generate_warehouse_map.rasterize_rack_clearance` frees the identical
    cells, so AMCL and the planner agree with the colliders.
    """
    from pxr import Gf, UsdGeom

    warehouse = WarehouseConfig()
    rack_h = 0.9
    for quadrant in ("NE", "NW", "SE", "SW"):
        prim = stage.GetPrimAtPath(f"/World/Environment/RackBlocks/{quadrant}")
        if not prim.IsValid():
            raise ScenarioBuildError(
                f"Expected /World/Environment/RackBlocks/{quadrant} from the sublayered "
                "warehouse asset before authoring a rack-clearance override"
            )
        prim.SetActive(False)

    root = UsdGeom.Xform.Define(stage, "/World/Scenario/ClearedRackBlocks")
    root.GetPrim().SetMetadata(
        "customData",
        {
            "x_min_m": clearance_cfg.x_min_m,
            "x_max_m": clearance_cfg.x_max_m,
            "y_min_m": clearance_cfg.y_min_m,
            "y_max_m": clearance_cfg.y_max_m,
        },
    )
    for name, x0, x1, y0, y1 in rack_clearance_remnants(warehouse, clearance_cfg):
        _author_rack_remnant_cube(
            stage,
            f"/World/Scenario/ClearedRackBlocks/{name}",
            Gf.Vec3f((x0 + x1) / 2.0, (y0 + y1) / 2.0, rack_h / 2.0),
            Gf.Vec3f((x1 - x0) / 2.0, (y1 - y0) / 2.0, rack_h / 2.0),
        )


def _author_rack_remnant_cube(stage, path: str, translate, scale) -> None:
    from pxr import UsdGeom, UsdPhysics

    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(2.0)
    cube.AddTranslateOp().Set(translate)
    cube.AddScaleOp().Set(scale)
    UsdPhysics.CollisionAPI.Apply(cube.GetPrim())


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

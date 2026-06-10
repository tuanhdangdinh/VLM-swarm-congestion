# isaac/vgu_sim/warehouse_builder.py
from __future__ import annotations

from pathlib import Path

from isaac.vgu_sim.config import CameraConfig, WarehouseConfig


class WarehouseBuildError(Exception):
    pass


def build_warehouse_asset(
    config: WarehouseConfig,
    camera_config: CameraConfig,
    output_path: Path,
) -> Path:
    from pxr import Usd, UsdGeom, UsdPhysics, Gf, Kind

    stage = Usd.Stage.CreateNew(str(output_path))

    stage.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetTimeCodesPerSecond(60.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    world.GetPrim().SetMetadata("kind", Kind.Tokens.assembly)

    physics_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    physics_scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
    physics_scene.CreateGravityMagnitudeAttr().Set(9.81)

    UsdGeom.Xform.Define(stage, "/World/Environment")

    _build_floor(stage, config)
    _build_walls(stage, config)
    _build_rack_blocks(stage, config)
    _build_loading_zones(stage, config)

    UsdGeom.Xform.Define(stage, "/World/Sensors")
    UsdGeom.Xform.Define(stage, "/World/DynamicObstacles")
    UsdGeom.Xform.Define(stage, "/World/Robots")
    UsdGeom.Xform.Define(stage, "/World/Scenario")
    UsdGeom.Xform.Define(stage, "/World/Scenario/Goals")
    UsdGeom.Xform.Define(stage, "/World/Scenario/Metadata")
    UsdGeom.Xform.Define(stage, "/World/ROSGraphs")
    UsdGeom.Xform.Define(stage, "/World/ROSGraphs/Global")

    _build_overhead_camera(stage, camera_config)

    _validate_references(stage, output_path)
    stage.Save()
    return output_path


def _build_floor(stage, config: WarehouseConfig) -> None:
    from pxr import UsdGeom, UsdPhysics, Gf

    half_w = config.width_m / 2.0
    half_d = config.depth_m / 2.0

    floor = UsdGeom.Mesh.Define(stage, "/World/Environment/Floor")
    floor.CreatePointsAttr([
        Gf.Vec3f(-half_w, -half_d, 0.0),
        Gf.Vec3f( half_w, -half_d, 0.0),
        Gf.Vec3f( half_w,  half_d, 0.0),
        Gf.Vec3f(-half_w,  half_d, 0.0),
    ])
    floor.CreateFaceVertexCountsAttr([4])
    floor.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    UsdPhysics.CollisionAPI.Apply(floor.GetPrim())


def _build_walls(stage, config: WarehouseConfig) -> None:
    from pxr import UsdGeom, UsdPhysics, Gf

    hw = config.width_m / 2.0
    hd = config.depth_m / 2.0
    t = config.wall_thickness_m / 2.0
    h = config.wall_height_m

    UsdGeom.Xform.Define(stage, "/World/Environment/Walls")
    wall_defs = [
        ("north", Gf.Vec3f(0.0,  hd + t, h / 2), Gf.Vec3f(hw + t,   t,    h / 2)),
        ("south", Gf.Vec3f(0.0, -hd - t, h / 2), Gf.Vec3f(hw + t,   t,    h / 2)),
        ("east",  Gf.Vec3f(hw + t, 0.0,  h / 2), Gf.Vec3f(t,        hd,   h / 2)),
        ("west",  Gf.Vec3f(-hw - t, 0.0, h / 2), Gf.Vec3f(t,        hd,   h / 2)),
    ]
    for name, pos, half_size in wall_defs:
        cube = UsdGeom.Cube.Define(stage, f"/World/Environment/Walls/{name}")
        cube.CreateSizeAttr(2.0)
        cube.AddTranslateOp().Set(pos)
        cube.AddScaleOp().Set(half_size)
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())


def _build_rack_blocks(stage, config: WarehouseConfig) -> None:
    from pxr import UsdGeom, UsdPhysics, Gf

    aw = config.nominal_aisle_width_m / 2.0
    hw = config.width_m / 2.0
    hd = config.depth_m / 2.0
    rack_hw = (hw - aw) / 2.0
    rack_hd = (hd - aw) / 2.0
    rack_h = 0.9

    UsdGeom.Xform.Define(stage, "/World/Environment/RackBlocks")
    quadrants = [
        ("NE", Gf.Vec3f( aw + rack_hw,  aw + rack_hd, rack_h / 2)),
        ("NW", Gf.Vec3f(-aw - rack_hw,  aw + rack_hd, rack_h / 2)),
        ("SE", Gf.Vec3f( aw + rack_hw, -aw - rack_hd, rack_h / 2)),
        ("SW", Gf.Vec3f(-aw - rack_hw, -aw - rack_hd, rack_h / 2)),
    ]
    for name, pos in quadrants:
        cube = UsdGeom.Cube.Define(stage, f"/World/Environment/RackBlocks/{name}")
        cube.CreateSizeAttr(2.0)
        cube.AddTranslateOp().Set(pos)
        cube.AddScaleOp().Set(Gf.Vec3f(rack_hw, rack_hd, rack_h / 2))
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())


def _build_loading_zones(stage, config: WarehouseConfig) -> None:
    from pxr import UsdGeom, Gf

    UsdGeom.Xform.Define(stage, "/World/Environment/LoadingZones")
    for name, pos in [
        ("west",  Gf.Vec3f(-5.2, 0.0, 0.001)),
        ("east",  Gf.Vec3f( 5.2, 0.0, 0.001)),
        ("south", Gf.Vec3f(0.0, -3.2, 0.001)),
        ("north", Gf.Vec3f(0.0,  3.2, 0.001)),
    ]:
        UsdGeom.Mesh.Define(stage, f"/World/Environment/LoadingZones/{name}").AddTranslateOp().Set(pos)


def _build_overhead_camera(stage, config: CameraConfig) -> None:
    from pxr import UsdGeom, Gf

    cam_prim = UsdGeom.Camera.Define(stage, config.prim_path)

    xform = UsdGeom.Xformable(cam_prim.GetPrim())
    xform.AddTranslateOp().Set(Gf.Vec3d(*config.position_m))
    w, x, y, z = config.orientation_quat_wxyz
    if (w, x, y, z) != (1.0, 0.0, 0.0, 0.0):
        xform.AddOrientOp().Set(Gf.Quatd(w, x, y, z))

    cam_prim.CreateFocalLengthAttr().Set(config.focal_length_mm)
    cam_prim.CreateHorizontalApertureAttr().Set(config.horizontal_aperture_mm)
    cam_prim.CreateVerticalApertureAttr().Set(config.vertical_aperture_mm)
    cam_prim.CreateClippingRangeAttr().Set(Gf.Vec2f(0.1, 100.0))
    cam_prim.CreateProjectionAttr().Set(UsdGeom.Tokens.perspective)


def _validate_references(stage, output_path: Path) -> None:
    errors = [e for e in stage.GetCompositionErrors()]
    if errors:
        raise WarehouseBuildError(
            f"Unresolved composition errors in {output_path}: {errors}"
        )

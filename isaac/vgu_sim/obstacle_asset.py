# isaac/vgu_sim/obstacle_asset.py
from __future__ import annotations

from pathlib import Path


class ObstacleAssetError(Exception):
    pass


def create_box_obstacle(
    output_path: Path,
    width_m: float = 0.3,
    depth_m: float = 0.3,
    height_m: float = 0.5,
) -> Path:
    """Create a simple box obstacle as USD asset with physics.

    Args:
        output_path: Where to save the USD file.
        width_m: Obstacle width (X axis).
        depth_m: Obstacle depth (Y axis).
        height_m: Obstacle height (Z axis).

    Returns:
        Path to the generated USD file.

    Raises:
        ObstacleAssetError: If USD creation fails.
    """
    from pxr import Gf, Kind, Usd, UsdGeom, UsdPhysics

    try:
        stage = Usd.Stage.CreateNew(str(output_path))
    except Exception as e:
        raise ObstacleAssetError(f"Failed to create USD stage at {output_path}: {e}")

    stage.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetTimeCodesPerSecond(60.0)

    # Root
    root = UsdGeom.Xform.Define(stage, "/Root")
    stage.SetDefaultPrim(root.GetPrim())
    root.GetPrim().SetMetadata("kind", Kind.Tokens.assembly)

    # Box geometry
    box_prim = UsdGeom.Cube.Define(stage, "/Root/Obstacle")
    box_prim.CreateSizeAttr(2.0)

    # Position and scale
    xform = UsdGeom.Xformable(box_prim.GetPrim())
    xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, height_m / 2.0))
    xform.AddScaleOp().Set(Gf.Vec3f(width_m / 2.0, depth_m / 2.0, height_m / 2.0))

    # Physics: collision only (not dynamic)
    UsdPhysics.CollisionAPI.Apply(box_prim.GetPrim())

    # Material/visibility hint
    box_prim.GetPrim().SetMetadata("customData", {
        "obstacle_type": "box",
        "width_m": width_m,
        "depth_m": depth_m,
        "height_m": height_m,
    })

    stage.Save()
    return output_path

# isaac/vgu_sim/robot_asset.py
from __future__ import annotations

from pathlib import Path

from isaac.vgu_sim.config import RobotAssetConfig


class RobotImportError(Exception):
    pass


def import_turtlebot3(
    urdf_path: Path,
    output_root: Path,
    config: RobotAssetConfig,
    *,
    force: bool = False,
) -> Path:
    if not urdf_path.exists():
        raise RobotImportError(f"URDF not found: {urdf_path}")

    dest_dir = output_root / "turtlebot3_burger"
    interface_layer = dest_dir / "turtlebot3_burger.usda"

    if interface_layer.exists() and not force:
        raise RobotImportError(
            f"Asset already exists at {interface_layer}. Use --force to overwrite."
        )

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Must be imported here: SimulationApp must already be running.
    import omni.usd
    from isaacsim.asset.importer.urdf import URDFImporter

    importer_config = URDFImporter.Config()
    importer_config.merge_fixed_joints = False
    importer_config.make_default_prim = True
    importer_config.create_physics_scene = False
    importer_config.convex_decomp = False
    importer_config.self_collision_filter = True
    importer_config.up_vector = (0.0, 0.0, 1.0)
    importer_config.import_inertia_tensor = True
    importer_config.density = 0.0
    importer_config.output_directory = str(dest_dir)

    result = URDFImporter.import_robot(str(urdf_path), importer_config)
    if not result.success:
        raise RobotImportError(f"URDF import failed: {result.error}")

    _apply_wheel_drives(interface_layer, config)
    validate_robot_asset(interface_layer, config)

    return interface_layer


def _apply_wheel_drives(asset_path: Path, config: RobotAssetConfig) -> None:
    from pxr import Usd, UsdPhysics

    stage = Usd.Stage.Open(str(asset_path))
    for joint_name in (config.left_wheel_joint, config.right_wheel_joint):
        joint_prim = _find_prim_by_name(stage, joint_name)
        if joint_prim is None:
            raise RobotImportError(f"Wheel joint not found: {joint_name!r}")
        drive = UsdPhysics.DriveAPI.Apply(joint_prim, "angular")
        drive.GetStiffnessAttr().Set(config.wheel_drive_stiffness)
        drive.GetDampingAttr().Set(config.wheel_drive_damping)
        drive.GetTargetVelocityAttr().Set(0.0)
        drive.GetMaxForceAttr().Set(float("inf"))
    stage.Save()


def _find_prim_by_name(stage, name: str):
    for prim in stage.Traverse():
        if prim.GetName() == name:
            return prim
    return None


def validate_robot_asset(asset_path: Path, config: RobotAssetConfig) -> None:
    from pxr import Usd, UsdPhysics

    stage = Usd.Stage.Open(str(asset_path))

    art_roots = [
        p for p in stage.Traverse()
        if p.HasAPI(UsdPhysics.ArticulationRootAPI)
    ]
    if len(art_roots) != 1:
        raise RobotImportError(
            f"Expected exactly 1 ArticulationRootAPI; found {len(art_roots)}"
        )

    for joint_name in (config.left_wheel_joint, config.right_wheel_joint):
        prim = _find_prim_by_name(stage, joint_name)
        if prim is None:
            raise RobotImportError(f"Missing wheel joint: {joint_name!r}")
        if not prim.HasAPI(UsdPhysics.DriveAPI):
            raise RobotImportError(f"Wheel joint {joint_name!r} has no DriveAPI")

    layer = stage.GetRootLayer()
    if layer.metersPerUnit != 1.0:
        raise RobotImportError(
            f"metersPerUnit must be 1; got {layer.metersPerUnit}"
        )

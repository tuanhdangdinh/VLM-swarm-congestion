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

    # import_urdf() writes {robot_name}/{robot_name}.usda under usd_path
    robot_name = urdf_path.stem
    interface_layer = output_root / robot_name / f"{robot_name}.usda"

    if interface_layer.exists() and not force:
        raise RobotImportError(
            f"Asset already exists at {interface_layer}. Use --force to overwrite."
        )

    output_root.mkdir(parents=True, exist_ok=True)

    # Must be imported here: SimulationApp must already be running.
    from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig

    importer_config = URDFImporterConfig(
        urdf_path=str(urdf_path),
        usd_path=str(output_root),
        allow_self_collision=False,
        merge_mesh=False,
        collision_from_visuals=False,
    )
    importer = URDFImporter()
    importer.config = importer_config
    final_path = Path(importer.import_urdf())

    _apply_wheel_drives(final_path, config)
    _disable_fixed_base(final_path, config)
    validate_robot_asset(final_path, config)

    return final_path


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


def _disable_fixed_base(asset_path: Path, config: RobotAssetConfig) -> None:
    """Disable the fixed-base joint so the chassis is free to translate.

    The URDF importer's `fix_base=True` default authors a `PhysicsFixedJoint`
    welding base_link to the world. Spinning wheels then cannot move the chassis
    (verified: joint velocities non-zero, base pose unchanged). Setting
    `physics:jointEnabled=False` frees the base while leaving the joint prim in
    place for inspection. The other fixed joints (caster, scan) legitimately weld
    sensors to base_link and are left untouched.
    """
    from pxr import Sdf, Usd

    stage = Usd.Stage.Open(str(asset_path))
    joint_prim = _find_prim_by_name(stage, config.base_fixed_joint)
    if joint_prim is None:
        # No weld present (e.g. a future importer that defaults fix_base=False);
        # the base is already free, so there is nothing to disable.
        return
    enabled = joint_prim.GetAttribute("physics:jointEnabled")
    if not enabled:
        enabled = joint_prim.CreateAttribute(
            "physics:jointEnabled", Sdf.ValueTypeNames.Bool
        )
    enabled.Set(False)
    stage.Save()


def _find_prim_by_name(stage, name: str):
    for prim in stage.Traverse():
        if prim.GetName() == name:
            return prim
    return None


def validate_robot_asset(asset_path: Path, config: RobotAssetConfig) -> None:
    from pxr import Usd, UsdGeom, UsdPhysics

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

    base_joint = _find_prim_by_name(stage, config.base_fixed_joint)
    if base_joint is not None:
        enabled = base_joint.GetAttribute("physics:jointEnabled")
        if enabled is None or enabled.Get() is not False:
            raise RobotImportError(
                f"Fixed base joint {config.base_fixed_joint!r} is still enabled; "
                "the chassis would be welded to the world and cannot move."
            )

    meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
    if meters_per_unit != 1.0:
        raise RobotImportError(
            f"metersPerUnit must be 1; got {meters_per_unit}"
        )

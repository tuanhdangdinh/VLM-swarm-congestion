"""Author velocity drives on a robot's wheel joints.

A DifferentialController emits wheel *velocity* targets; the wheels only
respond if their USD angular drive is in velocity mode (zero stiffness,
non-zero damping). Constants come from RobotAssetConfig (M6 FR6.4.7).
"""
from __future__ import annotations

from pxr import Sdf, Usd, UsdPhysics, UsdShade

from isaac.vgu_sim.config import RobotAssetConfig

# Shared physics material carrying the wheel/floor friction. One material is
# bound to every wheel collider and the floor so the tyre-ground contact has
# traction; without it PhysX uses a frictionless default and the wheels spin in
# place (verified: vcmd/joint velocities non-zero, base pose unchanged).
_WHEEL_MATERIAL_PATH = "/World/PhysicsMaterials/RobotWheel"
_FLOOR_PRIM_PATH = "/World/Environment/Floor"


def configure_wheel_velocity_drive(
    stage: Usd.Stage,
    robot_prim_path: str,
    config: RobotAssetConfig,
) -> None:
    """Set both wheel joints to velocity drive under `robot_prim_path`.

    Args:
        stage: The USD stage holding the robot.
        robot_prim_path: Root prim of the robot subtree.
        config: Asset config supplying joint names and drive gains.

    Raises:
        ValueError: If either named wheel joint is not found in the subtree.
    """
    root = stage.GetPrimAtPath(robot_prim_path)
    by_name = {
        p.GetName(): p
        for p in Usd.PrimRange(root)
        if p.IsA(UsdPhysics.RevoluteJoint)
    }
    for label, joint_name in (
        ("wheel_left_joint", config.left_wheel_joint),
        ("wheel_right_joint", config.right_wheel_joint),
    ):
        prim = by_name.get(joint_name)
        if prim is None:
            raise ValueError(
                f"{label}={joint_name!r} not found under {robot_prim_path}"
            )
        drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
        # Velocity control: zero position stiffness, non-zero damping.
        drive.CreateStiffnessAttr(config.wheel_drive_stiffness)
        drive.CreateDampingAttr(config.wheel_drive_damping)
        drive.CreateTargetVelocityAttr(0.0)


def _ensure_wheel_material(stage: Usd.Stage, config: RobotAssetConfig) -> UsdShade.Material:
    """Create (or update) the shared wheel friction material on the stage."""
    prim = stage.GetPrimAtPath(_WHEEL_MATERIAL_PATH)
    if not prim or not prim.IsValid():
        material = UsdShade.Material.Define(stage, Sdf.Path(_WHEEL_MATERIAL_PATH))
        prim = material.GetPrim()
    else:
        material = UsdShade.Material(prim)
    phys = UsdPhysics.MaterialAPI.Apply(prim)
    phys.CreateStaticFrictionAttr(config.wheel_static_friction)
    phys.CreateDynamicFrictionAttr(config.wheel_dynamic_friction)
    phys.CreateRestitutionAttr(0.0)
    return material


def _bind_physics_material(prim: Usd.Prim, material: UsdShade.Material) -> None:
    binding = UsdShade.MaterialBindingAPI.Apply(prim)
    # "physics" purpose so it binds the rigid-body material, not the render look;
    # weakerThanDescendants leaves any per-mesh override in place.
    binding.Bind(material, UsdShade.Tokens.weakerThanDescendants, "physics")


def configure_contact_friction(
    stage: Usd.Stage,
    robot_prim_path: str,
    config: RobotAssetConfig,
) -> None:
    """Bind a friction material to the robot's wheel colliders and the floor.

    The DifferentialController spins the wheels, but a wheel only propels the
    chassis if its contact with the floor has friction. The robot asset and the
    warehouse floor ship with colliders but no physics material, so PhysX uses a
    frictionless default and the wheels slip in place. This authors a material
    from the configured friction coefficients and binds it to both contact
    surfaces.

    Args:
        stage: The USD stage holding the robot and floor.
        robot_prim_path: Root prim of the robot subtree.
        config: Asset config supplying the friction coefficients.
    """
    material = _ensure_wheel_material(stage, config)

    root = stage.GetPrimAtPath(robot_prim_path)
    for prim in Usd.PrimRange(root):
        # Wheel colliders live on a descendant of wheel_*_link (e.g. a child
        # 'cylinder' mesh that carries the CollisionAPI), not the link Xform.
        if prim.HasAPI(UsdPhysics.CollisionAPI) and "wheel" in prim.GetPath().pathString.lower():
            _bind_physics_material(prim, material)

    floor = stage.GetPrimAtPath(_FLOOR_PRIM_PATH)
    if floor and floor.IsValid() and floor.HasAPI(UsdPhysics.CollisionAPI):
        _bind_physics_material(floor, material)

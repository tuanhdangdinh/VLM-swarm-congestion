"""Author velocity drives on a robot's wheel joints.

A DifferentialController emits wheel *velocity* targets; the wheels only
respond if their USD angular drive is in velocity mode (zero stiffness,
non-zero damping). Constants come from RobotAssetConfig (M6 FR6.4.7).
"""
from __future__ import annotations

from pxr import Usd, UsdPhysics

from isaac.vgu_sim.config import RobotAssetConfig


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

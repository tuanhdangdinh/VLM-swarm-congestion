import pytest

pytest.importorskip("pxr")

from pxr import Usd, UsdGeom, UsdPhysics

from isaac.vgu_sim.config import RobotAssetConfig
from isaac.vgu_sim.robot_drive import configure_wheel_velocity_drive


def _make_stage_with_both_wheels() -> tuple[Usd.Stage, str, str]:
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/Robot")
    left_path = "/Robot/wheel_left_joint"
    right_path = "/Robot/wheel_right_joint"
    UsdPhysics.RevoluteJoint.Define(stage, left_path)
    UsdPhysics.RevoluteJoint.Define(stage, right_path)
    return stage, left_path, right_path


def test_sets_angular_drive_to_velocity_mode():
    cfg = RobotAssetConfig()
    stage, left_path, right_path = _make_stage_with_both_wheels()

    configure_wheel_velocity_drive(stage, "/Robot", cfg)

    # Both wheels must be switched to velocity drive, not just the left.
    for joint_path in (left_path, right_path):
        drive = UsdPhysics.DriveAPI.Get(stage.GetPrimAtPath(joint_path), "angular")
        assert drive.GetStiffnessAttr().Get() == cfg.wheel_drive_stiffness
        assert drive.GetDampingAttr().Get() == cfg.wheel_drive_damping


def test_missing_wheel_joint_raises():
    cfg = RobotAssetConfig()
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/Robot")  # no wheel joints

    with pytest.raises(ValueError, match="wheel_left_joint"):
        configure_wheel_velocity_drive(stage, "/Robot", cfg)

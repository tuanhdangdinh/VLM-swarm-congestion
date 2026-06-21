from pathlib import Path

import pytest
from pxr import Sdf, Usd, UsdGeom, UsdPhysics

from isaac.vgu_sim.config import RobotAssetConfig
from isaac.vgu_sim.robot_asset import (
    RobotImportError,
    _disable_fixed_base,
    validate_robot_asset,
)


def _author_robot_asset(tmp_path: Path, *, base_enabled: bool | None = None) -> Path:
    """Author a minimal turtlebot-shaped asset that satisfies validate_robot_asset.

    Mirrors the post-import asset structure the diagnosis confirmed: one
    articulation root on base_link, two driven revolute wheel joints, a
    fixed-base weld joint, plus legit fixed joints (caster, scan) that must be
    left untouched.

    Args:
        base_enabled: If None, leave `physics:jointEnabled` unauthored on
            base_joint (the importer's default — absent attribute means True).
            If a bool, author that value so the validate guard can be exercised.
    """
    asset_path = tmp_path / "turtlebot3_burger.usda"
    stage = Usd.Stage.CreateNew(str(asset_path))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    base_link = UsdGeom.Xform.Define(stage, "/turtlebot3_burger/base_link").GetPrim()
    UsdPhysics.ArticulationRootAPI.Apply(base_link)

    for joint_name in ("wheel_left_joint", "wheel_right_joint"):
        joint = UsdPhysics.RevoluteJoint.Define(
            stage, f"/turtlebot3_burger/{joint_name}"
        )
        UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "angular")

    base_joint = UsdPhysics.FixedJoint.Define(
        stage, "/turtlebot3_burger/base_joint"
    ).GetPrim()
    if base_enabled is not None:
        base_joint.CreateAttribute(
            "physics:jointEnabled", Sdf.ValueTypeNames.Bool
        ).Set(base_enabled)
    # Legit fixed joints that weld sensors/casters to base_link; must stay enabled.
    for joint_name in ("caster_back_joint", "scan_joint"):
        UsdPhysics.FixedJoint.Define(stage, f"/turtlebot3_burger/{joint_name}")

    stage.Save()
    return asset_path


def _joint_enabled(asset_path: Path, joint_name: str) -> bool | None:
    stage = Usd.Stage.Open(str(asset_path))
    prim = next(p for p in stage.Traverse() if p.GetName() == joint_name)
    attr = prim.GetAttribute("physics:jointEnabled")
    return attr.Get() if attr else None


def test_disable_fixed_base_flips_base_joint_to_false():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        asset = _author_robot_asset(Path(d))
        _disable_fixed_base(asset, RobotAssetConfig())
        assert _joint_enabled(asset, "base_joint") is False


def test_disable_fixed_base_leaves_other_fixed_joints_untouched():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        asset = _author_robot_asset(Path(d))
        _disable_fixed_base(asset, RobotAssetConfig())
        # caster/scan welds were never authored with jointEnabled, so disabling
        # the base must leave them at the schema's True default (not False).
        assert _joint_enabled(asset, "caster_back_joint") is not False
        assert _joint_enabled(asset, "scan_joint") is not False


def test_validate_passes_when_base_joint_disabled():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        asset = _author_robot_asset(Path(d), base_enabled=False)
        validate_robot_asset(asset, RobotAssetConfig())  # must not raise


def test_validate_raises_when_base_joint_still_enabled():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        asset = _author_robot_asset(Path(d), base_enabled=True)
        with pytest.raises(RobotImportError, match="welded to the world"):
            validate_robot_asset(asset, RobotAssetConfig())


def test_validate_raises_when_base_joint_enabled_unauthored():
    # The importer's actual failure mode: jointEnabled absent defaults to True.
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        asset = _author_robot_asset(Path(d), base_enabled=None)
        with pytest.raises(RobotImportError, match="welded to the world"):
            validate_robot_asset(asset, RobotAssetConfig())

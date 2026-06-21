import pytest

pytest.importorskip("pxr")

from pxr import Usd, UsdGeom

from isaac.vgu_sim.lidar import author_rtx_lidar


def test_creates_lidar_prim_under_base_scan_link():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/Robot")
    UsdGeom.Xform.Define(stage, "/Robot/Geometry/base_footprint/base_link/base_scan")

    lidar_path = author_rtx_lidar(stage, "/Robot", lidar_link="base_scan")

    assert stage.GetPrimAtPath(lidar_path).IsValid()
    assert lidar_path.startswith(
        "/Robot/Geometry/base_footprint/base_link/base_scan"
    )


def test_missing_lidar_link_raises():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/Robot")

    with pytest.raises(ValueError, match="base_scan"):
        author_rtx_lidar(stage, "/Robot", lidar_link="base_scan")

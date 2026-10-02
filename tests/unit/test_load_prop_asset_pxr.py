"""USD-authoring tests for the B2-visual load prop (needs `pxr`/Isaac Sim).

Skipped without `pxr` (`pytest.importorskip`), the project's existing
convention for `isaac.vgu_sim` authoring/validation helpers
(`tests/unit/test_m6_validation.py`). The pure geometry (mount position,
clearance) is pinned without `pxr` in `tests/unit/test_load_prop_asset.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def _stage():
    pytest.importorskip("pxr")
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World/Robots/robot_1")
    return stage


def test_load_prop_is_authored_under_base_link():
    pytest.importorskip("pxr")
    from pxr import UsdGeom

    from isaac.vgu_sim.load_prop_asset import author_load_prop

    stage = _stage()
    author_load_prop(stage, "/World/Robots/robot_1")
    cube = UsdGeom.Cube.Get(
        stage, "/World/Robots/robot_1/Geometry/base_footprint/base_link/load_prop"
    )
    assert cube, "load_prop cube not authored under base_link"


def test_load_prop_is_mounted_flush_to_the_chassis_rear():
    pytest.importorskip("pxr")
    from pxr import UsdGeom

    from isaac.vgu_sim.load_prop_asset import LOAD_PROP_CENTER_X_M, author_load_prop

    stage = _stage()
    author_load_prop(stage, "/World/Robots/robot_1")
    cube = UsdGeom.Cube.Get(
        stage, "/World/Robots/robot_1/Geometry/base_footprint/base_link/load_prop"
    )
    xf = UsdGeom.Xformable(cube).GetLocalTransformation()
    assert xf.ExtractTranslation()[0] == pytest.approx(LOAD_PROP_CENTER_X_M)


def test_load_prop_carries_no_physics_api():
    pytest.importorskip("pxr")
    from pxr import UsdGeom, UsdPhysics

    from isaac.vgu_sim.load_prop_asset import author_load_prop

    stage = _stage()
    author_load_prop(stage, "/World/Robots/robot_1")
    prim = UsdGeom.Cube.Get(
        stage, "/World/Robots/robot_1/Geometry/base_footprint/base_link/load_prop"
    ).GetPrim()
    assert not prim.HasAPI(UsdPhysics.CollisionAPI)
    assert not prim.HasAPI(UsdPhysics.RigidBodyAPI)
    assert not prim.HasAPI(UsdPhysics.MassAPI)


def test_load_prop_does_not_touch_the_aruco_marker():
    pytest.importorskip("pxr")
    from pxr import UsdGeom

    from isaac.vgu_sim.load_prop_asset import author_load_prop
    from isaac.vgu_sim.marker_asset import author_aruco_marker

    stage = _stage()
    author_aruco_marker(stage, "/World/Robots/robot_1", "markers/aruco_4x4_50/marker_1.png")
    author_load_prop(stage, "/World/Robots/robot_1")
    marker = UsdGeom.Mesh.Get(
        stage,
        "/World/Robots/robot_1/Geometry/base_footprint/base_link"
        "/aruco_marker_link/aruco_marker",
    )
    assert marker, "load_prop authoring must not disturb the marker"
    cube = UsdGeom.Cube.Get(
        stage, "/World/Robots/robot_1/Geometry/base_footprint/base_link/load_prop"
    )
    assert cube

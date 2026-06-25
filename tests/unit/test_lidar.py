"""Offline unit tests for isaac.vgu_sim.lidar USD-prim authoring.

RTX raytracing itself cannot be exercised without the renderer — these tests
cover the USD stage mutations only.
"""
from __future__ import annotations

import pytest

pxr = pytest.importorskip("pxr")
from pxr import Usd, UsdGeom  # noqa: E402 — after importorskip

from isaac.vgu_sim.lidar import author_rtx_lidar  # noqa: E402


def _stage_with_base_scan() -> Usd.Stage:
    stage = Usd.Stage.CreateInMemory()
    for path in (
        "/Robot",
        "/Robot/Geometry",
        "/Robot/Geometry/base_footprint",
        "/Robot/Geometry/base_footprint/base_link",
        "/Robot/Geometry/base_footprint/base_link/base_scan",
    ):
        UsdGeom.Xform.Define(stage, path)
    return stage


def test_creates_lidar_prim_under_base_scan_link():
    stage = _stage_with_base_scan()

    lidar_path = author_rtx_lidar(stage, "/Robot", lidar_link="base_scan")

    assert stage.GetPrimAtPath(lidar_path).IsValid()
    assert lidar_path.startswith("/Robot/Geometry/base_footprint/base_link/base_scan")


def test_lidar_prim_path_ends_with_rtx_lidar():
    stage = _stage_with_base_scan()

    lidar_path = author_rtx_lidar(stage, "/Robot", lidar_link="base_scan")

    assert lidar_path.endswith("/rtx_lidar")


def test_missing_lidar_link_raises():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/Robot")

    with pytest.raises(ValueError, match="base_scan"):
        author_rtx_lidar(stage, "/Robot", lidar_link="base_scan")


def test_lidar_authoring_is_idempotent():
    """Calling author_rtx_lidar twice on the same stage must not raise."""
    stage = _stage_with_base_scan()
    path1 = author_rtx_lidar(stage, "/Robot", lidar_link="base_scan")
    path2 = author_rtx_lidar(stage, "/Robot", lidar_link="base_scan")
    assert path1 == path2
    assert stage.GetPrimAtPath(path1).IsValid()

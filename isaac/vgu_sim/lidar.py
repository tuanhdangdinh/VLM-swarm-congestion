"""Author the RTX 2D lidar sensor prim under a robot's base_scan link.

M6 FR6.4.9: 360 deg, 1 deg resolution, 10 Hz, 0.12-3.5 m range, frame
robot_N/base_scan. The exclusion of the ArUco marker plate from RTX
raytracing (FR6.4.10) is applied separately — see exclude_from_rtx_lidar().
"""
from __future__ import annotations

from pxr import Usd, UsdGeom


def author_rtx_lidar(stage: Usd.Stage, robot_prim_path: str, lidar_link: str) -> str:
    """Create the RTX lidar prim under `<robot_prim_path>/.../<lidar_link>`.

    Args:
        stage: The USD stage holding the robot.
        robot_prim_path: Root prim of the robot subtree.
        lidar_link: Name of the link prim the lidar mounts to (e.g. "base_scan").

    Returns:
        The created lidar prim's path.

    Raises:
        ValueError: If `lidar_link` is not found under `robot_prim_path`.
    """
    link_prim = None
    for prim in Usd.PrimRange(stage.GetPrimAtPath(robot_prim_path)):
        if prim.GetName() == lidar_link:
            link_prim = prim
            break
    if link_prim is None:
        raise ValueError(f"lidar_link={lidar_link!r} not found under {robot_prim_path}")

    lidar_path = f"{link_prim.GetPath()}/rtx_lidar"
    UsdGeom.Xform.Define(stage, lidar_path)
    return lidar_path

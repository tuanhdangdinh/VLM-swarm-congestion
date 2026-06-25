"""Author the RTX 2D lidar sensor prim under a robot's base_scan link.

M6 FR6.4.9: 360 deg, 1 deg resolution, 10 Hz, 0.12–3.5 m range,
frame robot_N/base_scan. The exclusion of the ArUco marker plate from
RTX raytracing (FR6.4.10) is applied by exclude_from_rtx_lidar() once
the host-verified mechanism is known (phase2-nav2-stack.md §10).
"""
from __future__ import annotations

from pxr import Usd, UsdGeom


def author_rtx_lidar(stage: Usd.Stage, robot_prim_path: str, lidar_link: str) -> str:
    """Create the RTX lidar prim under `<robot_prim_path>/.../<lidar_link>/rtx_lidar`.

    Traverses the robot subtree depth-first for the first prim whose name
    matches `lidar_link`, then defines a child Xform named `rtx_lidar`.
    Calling this more than once on the same stage is idempotent.

    Args:
        stage: The USD stage holding the robot.
        robot_prim_path: Root prim of the robot subtree (e.g. "/World/Robots/robot_1").
        lidar_link: Name of the link prim the lidar mounts to (e.g. "base_scan").

    Returns:
        The created lidar prim's SdfPath string.

    Raises:
        ValueError: If `lidar_link` is not found anywhere under `robot_prim_path`.
    """
    root = stage.GetPrimAtPath(robot_prim_path)
    link_prim = None
    for prim in Usd.PrimRange(root):
        if prim.GetName() == lidar_link:
            link_prim = prim
            break
    if link_prim is None:
        raise ValueError(
            f"lidar_link={lidar_link!r} not found under {robot_prim_path}"
        )

    lidar_path = f"{link_prim.GetPath()}/rtx_lidar"
    UsdGeom.Xform.Define(stage, lidar_path)
    return lidar_path


def exclude_from_rtx_lidar(plate_prim: "Usd.Prim") -> None:
    """No-op: ArUco plate exclusion from RTX lidar is not needed (FR6.4.10).

    Host probe (phase2-nav2-stack.md §10, 2026-06-25) confirmed that height
    separation alone is sufficient — the marker plate sits at z=0.21 m, above
    the RPLIDAR_S2E single-elevation scan plane at z=0.172 m, so no phantom
    hit appears at the plate's bearing in `/robot_N/scan`. No RTX-visibility
    API or UsdGeom.Imageable exclusion is applied or needed.

    This function is retained as a no-op so callers that were written against
    the earlier "API TBD" interface do not break, but calling it has no effect.

    Args:
        plate_prim: The ArUco marker plate prim (unused).
    """

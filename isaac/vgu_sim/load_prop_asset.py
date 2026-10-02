# isaac/vgu_sim/load_prop_asset.py
"""The B2-visual pallet/load prop: a visual-only box rigidly mounted behind
a robot's chassis, carrying urgency through the overhead camera image alone.

Geometry (local to `base_link`, the same frame `marker_asset.MARKER_SIZE_M`/
`MARKER_HEIGHT_M` and the URDF's `aruco_marker_joint` use):

- The chassis collision box (`turtlebot3_burger.urdf`, `base_link/collision`)
  is 0.140 x 0.140 x 0.143 m centred at local `x = -0.032`, so its rear edge
  is at `x = -0.032 - 0.070 = -0.102`.
- The ArUco marker quad (`marker_asset.author_aruco_marker`) is centred at
  local `(0, 0)` at height 0.21 m, half-size 0.06 m, so its own rear edge is
  at `x = -0.06` -- forward of the chassis rear edge, i.e. the marker
  already fits entirely within the chassis footprint.
- The load prop is mounted flush to the chassis rear (front face at
  `x = -0.102`, no floating gap), so it is an addition *behind* the
  robot's existing silhouette: the marker neighbourhood is exactly what an
  empty (unloaded) robot already shows, and a nadir camera cannot occlude
  the marker with an object that never enters its footprint.
- The prop's top (world height ~0.13 m local + the 0.01 m `base_joint`
  rise) stays under the lidar's single scan plane (0.182 m world, the
  constant M1's `ROBOT_VISUAL_NO_MARKER_SCALE` comment derives from the
  same URDF's `scan_joint`), and the prop carries no `CollisionAPI`,
  `RigidBodyAPI` or `MassAPI` -- it cannot appear to Nav2, the lidar, or
  the safety monitor, by either route.

USD authoring (`author_load_prop`) needs `pxr` (Isaac Sim only); the
geometry constants and `marker_clearance_m` are plain Python and need no
simulator, so they are importable and testable from a local checkout.
"""
from __future__ import annotations

# Chassis collision box (turtlebot3_burger.urdf, base_link/collision).
BASE_LINK_COLLISION_CENTER_X_M = -0.032
BASE_LINK_COLLISION_HALF_LENGTH_M = 0.070
BASE_LINK_COLLISION_REAR_X_M = BASE_LINK_COLLISION_CENTER_X_M - BASE_LINK_COLLISION_HALF_LENGTH_M

# Marker rear edge (marker_asset.MARKER_SIZE_M, centred at local (0, 0)).
_MARKER_HALF_SIZE_M = 0.06
MARKER_REAR_X_M = 0.0 - _MARKER_HALF_SIZE_M

# The load prop's own size and mount pose, local to base_link.
LOAD_PROP_SIZE_M = (0.12, 0.14, 0.10)  # (x, y, z)
LOAD_PROP_COLOR_RGB = (0.55, 0.35, 0.15)  # pallet brown; distinct from every
# other authored box (_STATIC_BOX_COLOR grey, _LEGACY_TIMED_BOX_COLOR red,
# aisle-barrier yellow in scenario_builder.py).

# Mounted flush to the chassis rear: front face at the chassis rear edge,
# no floating gap.
LOAD_PROP_CENTER_X_M = BASE_LINK_COLLISION_REAR_X_M - LOAD_PROP_SIZE_M[0] / 2.0
LOAD_PROP_CENTER_Y_M = 0.0
# Center height chosen so the top (0.13 m) clears the floor with a visible
# profile but stays well under the 0.172 m local lidar-plane guard.
LOAD_PROP_CENTER_Z_M = 0.08

# The lidar's single scan plane, local to base_link (scan_joint z = 0.172 in
# turtlebot3_burger.urdf; `config.ROBOT_VISUAL_NO_MARKER_SCALE`'s comment
# derives the matching world-frame number, 0.182 m, from the same joint).
LIDAR_SCAN_PLANE_LOCAL_Z_M = 0.172


def load_prop_front_edge_x_m(center_x_m: float = LOAD_PROP_CENTER_X_M) -> float:
    """The prop's own front (toward the marker) edge, local x."""
    return center_x_m + LOAD_PROP_SIZE_M[0] / 2.0


def marker_clearance_m(center_x_m: float = LOAD_PROP_CENTER_X_M) -> float:
    """Gap between the marker's rear edge and the prop's front edge, in meters.

    Positive means the prop's own (x, y) footprint cannot overlap the
    marker's, regardless of camera parallax (the prop's own top sits lower
    than the marker's plane and the gap sits in the robot's own rear
    silhouette, not stretched across a wide radius from the camera axis).

    Args:
        center_x_m: The prop's mount center, local x (default: the shipped
            flush-to-chassis-rear mount).

    Returns:
        `MARKER_REAR_X_M - load_prop_front_edge_x_m(center_x_m)`.
    """
    return MARKER_REAR_X_M - load_prop_front_edge_x_m(center_x_m)


def load_prop_top_z_m(center_z_m: float = LOAD_PROP_CENTER_Z_M) -> float:
    """The prop's own top face, local z."""
    return center_z_m + LOAD_PROP_SIZE_M[2] / 2.0


def lidar_plane_clearance_m(center_z_m: float = LOAD_PROP_CENTER_Z_M) -> float:
    """Gap between the prop's top and the lidar's scan plane, in meters.

    Positive means the prop's top sits below the single plane the lidar
    scans (`LIDAR_SCAN_PLANE_LOCAL_Z_M`), so it cannot present as an
    obstacle to Nav2 even if a future change gave it a collider.
    """
    return LIDAR_SCAN_PLANE_LOCAL_Z_M - load_prop_top_z_m(center_z_m)


def author_load_prop(stage, robot_prim_path: str) -> None:
    """Author the load prop as a visual-only child of a robot's `base_link`.

    Mirrors `marker_asset.author_aruco_marker`'s placement convention (a new
    child prim directly under the referenced asset's existing `base_link`,
    so it is composed into the scenario stage and follows the chassis during
    simulation) but authors a plain coloured cube with no UV/material
    machinery, and deliberately applies no physics API: the prop must never
    appear to Nav2, the lidar, or the safety monitor (see the module
    docstring's geometry section).

    Args:
        stage: USD stage being authored.
        robot_prim_path: Robot root prim, e.g. `/World/Robots/robot_1`.

    Raises:
        AssertionError: If the authored cube unexpectedly carries a physics
            API (a defensive check; `UsdGeom.Cube.Define` never applies one).
    """
    from pxr import Gf, UsdGeom, UsdPhysics

    base_link_path = f"{robot_prim_path}/Geometry/base_footprint/base_link"
    prop_path = f"{base_link_path}/load_prop"
    cube = UsdGeom.Cube.Define(stage, prop_path)
    cube.CreateSizeAttr(2.0)
    cube.CreateDisplayColorAttr([Gf.Vec3f(*LOAD_PROP_COLOR_RGB)])
    cube.AddTranslateOp().Set(
        Gf.Vec3f(LOAD_PROP_CENTER_X_M, LOAD_PROP_CENTER_Y_M, LOAD_PROP_CENTER_Z_M)
    )
    half = tuple(s / 2.0 for s in LOAD_PROP_SIZE_M)
    cube.AddScaleOp().Set(Gf.Vec3f(*half))

    prim = cube.GetPrim()
    for api in (UsdPhysics.CollisionAPI, UsdPhysics.RigidBodyAPI, UsdPhysics.MassAPI):
        if prim.HasAPI(api):
            raise AssertionError(f"load_prop at {prop_path} unexpectedly carries {api}")

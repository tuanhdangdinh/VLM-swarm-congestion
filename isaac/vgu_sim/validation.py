# isaac/vgu_sim/validation.py
from __future__ import annotations

from pathlib import Path

from isaac.vgu_sim.config import (
    CameraConfig,
    ScenarioConfig,
    WarehouseConfig,
    rack_clearance_remnants,
)


class ValidationError(Exception):
    pass


def validate_stage_metadata(stage) -> None:
    from pxr import UsdGeom

    if stage.GetMetadata("metersPerUnit") != 1.0:
        raise ValidationError("metersPerUnit must be 1")
    if UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        raise ValidationError("upAxis must be Z")
    default_prim = stage.GetDefaultPrim()
    if not default_prim.IsValid() or default_prim.GetPath().pathString != "/World":
        raise ValidationError(
            f"defaultPrim must be /World; got {default_prim.GetPath()}"
        )


def validate_canonical_namespace(stage) -> None:
    required = [
        "/World/PhysicsScene",
        "/World/Environment",
        "/World/Environment/Floor",
        "/World/Environment/Walls",
        "/World/Environment/RackBlocks",
        "/World/Robots",
        "/World/Sensors/OverheadCamera",
        "/World/DynamicObstacles",
        "/World/Scenario",
        "/World/ROSGraphs",
        "/World/ROSGraphs/Global",
    ]
    for path in required:
        if not stage.GetPrimAtPath(path).IsValid():
            raise ValidationError(f"Required prim missing: {path}")


def validate_camera_frustum(stage, config: CameraConfig) -> None:
    import math

    cam_prim = stage.GetPrimAtPath(config.prim_path)
    if not cam_prim.IsValid():
        raise ValidationError(f"Camera prim not found: {config.prim_path}")

    height = config.position_m[2]
    fl = config.focal_length_mm
    ha = config.horizontal_aperture_mm
    va = config.vertical_aperture_mm

    hfov_rad = 2.0 * math.atan(ha / (2.0 * fl))
    vfov_rad = 2.0 * math.atan(va / (2.0 * fl))

    covered_w = 2.0 * height * math.tan(hfov_rad / 2.0)
    covered_d = 2.0 * height * math.tan(vfov_rad / 2.0)

    if covered_w < config.roi_width_m - 0.01:
        raise ValidationError(
            f"Camera covers {covered_w:.2f} m width; need >= {config.roi_width_m} m"
        )
    if covered_d < config.roi_depth_m - 0.01:
        raise ValidationError(
            f"Camera covers {covered_d:.2f} m depth; need >= {config.roi_depth_m} m"
        )


def validate_robot_marker(stage, robot_prim_path: str) -> None:
    """Assert a robot has a decodable ArUco marker quad authored on it.

    Checks the authored marker quad child (not the URDF frame): the mesh exists,
    carries an `st` primvar, and binds a material with a texture file input.

    Args:
        stage: USD stage being validated.
        robot_prim_path: Robot root prim, e.g. "/World/Robots/robot_1".

    Raises:
        ValidationError: If the marker quad, its `st` primvar, or its bound
            texture is missing.
    """
    from pxr import UsdGeom, UsdShade

    # Marker is under aruco_marker_link (physics child of base_link) so it
    # follows the robot body during simulation.
    marker_path = (
        f"{robot_prim_path}/Geometry/base_footprint/base_link"
        f"/aruco_marker_link/aruco_marker"
    )
    mesh = UsdGeom.Mesh.Get(stage, marker_path)
    if not mesh:
        raise ValidationError(f"Missing aruco_marker quad at {marker_path}")
    if not UsdGeom.PrimvarsAPI(mesh).GetPrimvar("st"):
        raise ValidationError(f"aruco_marker at {marker_path} has no 'st' primvar")
    material = UsdShade.MaterialBindingAPI(mesh).GetDirectBinding().GetMaterial()
    if not material:
        raise ValidationError(f"aruco_marker at {marker_path} has no bound material")
    tex = UsdShade.Shader.Get(stage, f"{marker_path}/Material/Texture")
    if not tex or not tex.GetInput("file") or not tex.GetInput("file").Get():
        raise ValidationError(f"aruco_marker at {marker_path} has no texture file")


def validate_robot_load_prop(stage, robot_prim_path: str, expected: bool) -> None:
    """Assert a robot's B2-visual load prop is present (or absent) and inert.

    Catches a scenario config whose `robots[].loaded` never reached the USD
    (a stale stage or a builder gap), and the one invariant the load prop
    must never violate: no physics API, so it cannot appear to Nav2, the
    lidar, or the safety monitor (isaac.vgu_sim.load_prop_asset).

    Args:
        stage: USD stage being validated.
        robot_prim_path: Robot root prim, e.g. `/World/Robots/robot_1`.
        expected: Whether this robot's config set `loaded: true`.

    Raises:
        ValidationError: If presence does not match `expected`, or a present
            prop carries `CollisionAPI`, `RigidBodyAPI` or `MassAPI`.
    """
    from pxr import UsdGeom, UsdPhysics

    prop_path = (
        f"{robot_prim_path}/Geometry/base_footprint/base_link/load_prop"
    )
    cube = UsdGeom.Cube.Get(stage, prop_path)
    if expected and not cube:
        raise ValidationError(f"robot is loaded but load_prop missing at {prop_path}")
    if not expected and cube:
        raise ValidationError(f"robot is not loaded but load_prop present at {prop_path}")
    if cube:
        prim = cube.GetPrim()
        for api in (UsdPhysics.CollisionAPI, UsdPhysics.RigidBodyAPI, UsdPhysics.MassAPI):
            if prim.HasAPI(api):
                raise ValidationError(f"load_prop at {prop_path} unexpectedly carries {api}")


def validate_scenario_obstacles(stage, config: ScenarioConfig) -> None:
    """Assert every configured obstacle has a prim authored on the stage.

    Catches a scenario config whose obstacles never reached the USD (a stale
    stage or a builder gap) at build time instead of mid-run.

    Args:
        stage: USD stage being validated.
        config: Scenario config whose obstacles must be present.

    Raises:
        ValidationError: If an expected obstacle prim path is missing, naming
            the first one found missing.
    """
    static_paths = [
        f"/World/Scenario/StaticObstacles/{obs.obstacle_id}"
        for obs in config.static_obstacles
    ]
    timed_paths = [
        f"/World/DynamicObstacles/{obs.obstacle_id}" for obs in config.timed_obstacles
    ]
    for path in static_paths + timed_paths:
        if not stage.GetPrimAtPath(path).IsValid():
            raise ValidationError(f"Configured obstacle prim missing: {path}")


def validate_loop_connectors(stage, config: ScenarioConfig) -> None:
    """Assert a `loop_map` scenario deactivated NE and authored its remnants.

    Mirrors `validate_scenario_obstacles`'s "every configured thing actually
    landed on the stage" check for the loop-map carve
    (`scenario_builder._author_loop_connectors`): catches a stale stage or a
    builder gap at build time, not mid-run.

    Args:
        stage: USD stage being validated.
        config: Scenario config whose `loop_map`, if set, must be authored.

    Raises:
        ValidationError: If `loop_map` is set but NE was left active, or any
            expected remnant cube is missing.
    """
    if config.loop_map is None:
        return

    ne_prim = stage.GetPrimAtPath("/World/Environment/RackBlocks/NE")
    if ne_prim.IsValid() and ne_prim.IsActive():
        raise ValidationError(
            "loop_map is set but /World/Environment/RackBlocks/NE is still "
            "active; _author_loop_connectors must deactivate it"
        )

    for name in (
        "top_slab",
        "aisle_east_of_loop",
        "connector_west_remnant",
        "connector_east_remnant",
    ):
        path = f"/World/Scenario/LoopRackBlocks/{name}"
        if not stage.GetPrimAtPath(path).IsValid():
            raise ValidationError(f"Configured loop-map remnant prim missing: {path}")


def validate_rack_clearance(stage, config: ScenarioConfig) -> None:
    """Assert a `rack_clearance` scenario deactivated every quadrant and authored its remnants.

    The `validate_loop_connectors` check for the S1b rack clearance
    (`scenario_builder._author_rack_clearance`).

    Args:
        stage: USD stage being validated.
        config: Scenario config whose `rack_clearance`, if set, must be authored.

    Raises:
        ValidationError: If `rack_clearance` is set but a quadrant was left
            active, or any expected remnant cube is missing.
    """
    if config.rack_clearance is None:
        return

    for quadrant in ("NE", "NW", "SE", "SW"):
        prim = stage.GetPrimAtPath(f"/World/Environment/RackBlocks/{quadrant}")
        if prim.IsValid() and prim.IsActive():
            raise ValidationError(
                f"rack_clearance is set but /World/Environment/RackBlocks/{quadrant} is "
                "still active; _author_rack_clearance must deactivate it"
            )
    for name, *_ in rack_clearance_remnants(WarehouseConfig(), config.rack_clearance):
        path = f"/World/Scenario/ClearedRackBlocks/{name}"
        if not stage.GetPrimAtPath(path).IsValid():
            raise ValidationError(f"Configured rack-clearance remnant prim missing: {path}")


def validate_no_unresolved_references(stage) -> None:
    errors = list(stage.GetCompositionErrors())
    if errors:
        raise ValidationError(f"Unresolved USD composition errors: {errors}")


def validate_scenario_stage(scenario_path: Path, config: CameraConfig | None = None) -> None:
    from pxr import Usd

    stage = Usd.Stage.Open(str(scenario_path))
    validate_no_unresolved_references(stage)
    validate_stage_metadata(stage)
    validate_canonical_namespace(stage)

    cam_config = config or CameraConfig()
    validate_camera_frustum(stage, cam_config)

    robots_root = stage.GetPrimAtPath("/World/Robots")
    for robot_prim in robots_root.GetChildren():
        validate_robot_marker(stage, robot_prim.GetPath().pathString)


def calibration_position_error(
    measured: tuple[float, float],
    ground_truth: tuple[float, float],
) -> float:
    """Euclidean distance (meters) between a measured and ground-truth XY pose.

    Args:
        measured: M1-reported world `(x, y)` for a robot.
        ground_truth: Isaac ground-truth world `(x, y)` for the same robot.

    Returns:
        The position error in meters.
    """
    dx = measured[0] - ground_truth[0]
    dy = measured[1] - ground_truth[1]
    return (dx * dx + dy * dy) ** 0.5

# isaac/vgu_sim/validation.py
from __future__ import annotations

from pathlib import Path

from isaac.vgu_sim.config import CameraConfig


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

    marker_path = f"{robot_prim_path}/aruco_marker"
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

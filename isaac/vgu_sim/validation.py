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

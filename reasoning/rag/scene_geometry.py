"""Declared scene geometry M3 derives yield maneuver distances from (no ROS2)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CorridorGeometry(BaseModel):
    """The contested corridor: the aisle segment two robots cannot share."""

    model_config = ConfigDict(frozen=True)

    axis: Literal["x", "y"] = "x"
    center_m: float = 0.0
    half_length_m: float = Field(gt=0.0)
    aisle_half_width_m: float = Field(gt=0.0)
    occluder_height_m: float = Field(ge=0.0)


class CameraGeometry(BaseModel):
    """Overhead camera mount and the plane its markers live on."""

    model_config = ConfigDict(frozen=True)

    height_m: float = Field(default=3.0, gt=0.0)
    marker_height_m: float = Field(default=0.21, ge=0.0)


class RobotGeometry(BaseModel):
    """Robot footprint, marker size, and the separation M4 enforces."""

    model_config = ConfigDict(frozen=True)

    half_width_m: float = Field(default=0.09, gt=0.0)
    marker_half_size_m: float = Field(default=0.06, ge=0.0)
    # Must equal the M4 safety monitor's min_distance_m (swarm_execution
    # config/safety.yaml); escort legs are sized to clear exactly that latch.
    safety_radius_m: float = Field(default=0.45, gt=0.0)


class SceneGeometry(BaseModel):
    """Scenario geometry a caller declares so M3 holds no scenario constants."""

    model_config = ConfigDict(frozen=True)

    corridor: CorridorGeometry
    camera: CameraGeometry = CameraGeometry()
    robot: RobotGeometry = RobotGeometry()
    park_margin_m: float = Field(default=0.3, ge=0.0)
    wall_margin_m: float = Field(default=0.15, ge=0.0)
    passer_margin_m: float = Field(default=0.2, ge=0.0)


def visibility_boundary_m(geometry: SceneGeometry) -> float:
    """Distance from the corridor centre past which a parked marker stays visible.

    The corridor's occluder (height `occluder_height_m`, ending at
    `half_length_m` from the centre) is seen by a camera at `height_m` directly
    above the centre. Its top edge projects onto the marker plane
    (`marker_height_m`) at `half_length_m * (height_m - marker_height_m) /
    (height_m - occluder_height_m)`, measured from the centre along
    `corridor.axis`.

    Args:
        geometry: Declared scene geometry.

    Returns:
        Boundary distance in metres from the corridor centre along the axis.

    Raises:
        ValueError: If the occluder reaches the camera or the marker plane sits
            at or above the camera, so the projection is undefined.
    """
    camera_to_occluder = geometry.camera.height_m - geometry.corridor.occluder_height_m
    camera_to_marker = geometry.camera.height_m - geometry.camera.marker_height_m
    if camera_to_occluder <= 0.0:
        raise ValueError(
            "occluder_height_m must be below camera height_m: "
            f"{geometry.corridor.occluder_height_m} >= {geometry.camera.height_m}"
        )
    if camera_to_marker <= 0.0:
        raise ValueError(
            "marker_height_m must be below camera height_m: "
            f"{geometry.camera.marker_height_m} >= {geometry.camera.height_m}"
        )
    return geometry.corridor.half_length_m * camera_to_marker / camera_to_occluder


def park_offset_m(geometry: SceneGeometry) -> float:
    """Offset from the corridor centre at which the yielder parks.

    `visibility_boundary_m` plus the marker's half-size (the whole marker, not
    just its centre, must clear the projected silhouette) plus `park_margin_m`.

    Args:
        geometry: Declared scene geometry.

    Returns:
        Park offset in metres from the corridor centre along `corridor.axis`.

    Raises:
        ValueError: If the visibility boundary is undefined for this geometry.
    """
    return (
        visibility_boundary_m(geometry)
        + geometry.robot.marker_half_size_m
        + geometry.park_margin_m
    )


def pull_off_lateral_m(geometry: SceneGeometry) -> float:
    """Lateral step the yielder takes off the corridor centreline.

    `aisle_half_width_m` minus the robot's `half_width_m` minus
    `wall_margin_m`, floored at 0.0 for an aisle too narrow to step aside in.

    Args:
        geometry: Declared scene geometry.

    Returns:
        Lateral offset in metres, perpendicular to `corridor.axis`.
    """
    lateral = (
        geometry.corridor.aisle_half_width_m
        - geometry.robot.half_width_m
        - geometry.wall_margin_m
    )
    return max(0.0, lateral)


def passer_clearance_m(geometry: SceneGeometry) -> float:
    """Margin added beyond the parked yielder before the passer's hold may end.

    The robot's `safety_radius_m` plus `passer_margin_m`: resuming while the
    passer is still inside the safety radius latches both robots.

    Args:
        geometry: Declared scene geometry.

    Returns:
        Clearance distance in metres.
    """
    return geometry.robot.safety_radius_m + geometry.passer_margin_m

from __future__ import annotations

from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Frame(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    image: np.ndarray
    stamp: float = Field(ge=0)
    frame_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)

    @field_validator("image")
    @classmethod
    def _image_shape(cls, v: np.ndarray) -> np.ndarray:
        if v.ndim != 3 or v.shape[2] != 3:
            raise ValueError(f"image must be (H, W, 3); got {v.shape}")
        return v


class CalibrationArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    intrinsics: np.ndarray
    distortion: np.ndarray
    homography: np.ndarray
    image_size: tuple[int, int]
    source_id: str = Field(min_length=1)
    created_at: float = Field(ge=0)

    @field_validator("intrinsics")
    @classmethod
    def _intrinsics_shape(cls, v: np.ndarray) -> np.ndarray:
        if v.shape != (3, 3):
            raise ValueError(f"intrinsics must be (3, 3); got {v.shape}")
        return v

    @field_validator("homography")
    @classmethod
    def _homography_shape(cls, v: np.ndarray) -> np.ndarray:
        if v.shape != (3, 3):
            raise ValueError(f"homography must be (3, 3); got {v.shape}")
        return v


class MarkerDetection(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    marker_id: int = Field(ge=0)
    corner_pixels: np.ndarray
    center_pixel: tuple[float, float]
    center_world: tuple[float, float]
    theta: float
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("corner_pixels")
    @classmethod
    def _corners_shape(cls, v: np.ndarray) -> np.ndarray:
        if v.shape != (4, 2):
            raise ValueError(f"corner_pixels must be (4, 2); got {v.shape}")
        return v


class RobotState(BaseModel):
    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    x: float
    y: float
    theta: float
    linear_velocity: float
    angular_velocity: float
    task: str | None
    status: Literal["MOVING", "SLOW", "STOPPED", "STALE"]
    goal: tuple[float, float] | None
    stamp: float = Field(ge=0)


class SceneState(BaseModel):
    model_config = ConfigDict(frozen=True)

    stamp: float = Field(ge=0)
    frame_id: str = Field(min_length=1)
    robots: list[RobotState]
    diagnostics: dict[str, object]


def scene_state_to_json_dict(scene_state: SceneState) -> dict[str, object]:
    return scene_state.model_dump(mode="json")

import math

import numpy as np
import pytest

from isaac.vgu_sim.calibration import camera_intrinsics
from isaac.vgu_sim.config import CameraConfig


def test_camera_intrinsics_matches_focal_aperture_resolution():
    cfg = CameraConfig()
    k = camera_intrinsics(cfg)

    fx = cfg.focal_length_mm / cfg.horizontal_aperture_mm * cfg.width
    fy = cfg.focal_length_mm / cfg.vertical_aperture_mm * cfg.height
    assert k.shape == (3, 3)
    assert math.isclose(k[0, 0], fx, rel_tol=1e-12)
    assert math.isclose(k[1, 1], fy, rel_tol=1e-12)
    assert math.isclose(k[0, 2], cfg.width / 2, rel_tol=1e-12)
    assert math.isclose(k[1, 2], cfg.height / 2, rel_tol=1e-12)
    assert k[2, 2] == 1.0

# tests/unit/test_m6_validation.py
import math
import pytest
from pxr import Usd, UsdGeom, UsdPhysics, Gf

from isaac.vgu_sim.config import CameraConfig
from isaac.vgu_sim.validation import (
    ValidationError,
    validate_camera_frustum,
    validate_stage_metadata,
    validate_canonical_namespace,
)


def _make_stage(tmp_path, *, meters_per_unit=1.0, up_axis="Z", default_prim="/World"):
    path = str(tmp_path / "test.usda")
    stage = Usd.Stage.CreateNew(path)
    stage.SetMetadata("metersPerUnit", meters_per_unit)
    if up_axis == "Z":
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    else:
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    world = UsdGeom.Xform.Define(stage, default_prim)
    stage.SetDefaultPrim(world.GetPrim())
    return stage


class TestValidateStageMetadata:
    def test_valid_stage_passes(self, tmp_path):
        stage = _make_stage(tmp_path)
        validate_stage_metadata(stage)  # no exception

    def test_wrong_meters_per_unit_fails(self, tmp_path):
        stage = _make_stage(tmp_path, meters_per_unit=100.0)
        with pytest.raises(ValidationError, match="metersPerUnit"):
            validate_stage_metadata(stage)

    def test_wrong_up_axis_fails(self, tmp_path):
        stage = _make_stage(tmp_path, up_axis="Y")
        with pytest.raises(ValidationError, match="upAxis"):
            validate_stage_metadata(stage)

    def test_wrong_default_prim_fails(self, tmp_path):
        stage = _make_stage(tmp_path, default_prim="/Foo")
        with pytest.raises(ValidationError, match="defaultPrim"):
            validate_stage_metadata(stage)


class TestValidateCameraFrustum:
    def test_default_config_passes(self, tmp_path):
        stage = _make_stage(tmp_path)
        config = CameraConfig()
        # Add camera prim so the check doesn't fail on missing prim
        UsdGeom.Camera.Define(stage, config.prim_path)
        validate_camera_frustum(stage, config)  # no exception

    def test_missing_camera_prim_fails(self, tmp_path):
        stage = _make_stage(tmp_path)
        config = CameraConfig()
        with pytest.raises(ValidationError, match="Camera prim not found"):
            validate_camera_frustum(stage, config)

    def test_insufficient_width_fails(self, tmp_path):
        stage = _make_stage(tmp_path)
        # Camera too high and narrow to cover ROI
        config = CameraConfig(
            focal_length_mm=100.0,
            horizontal_aperture_mm=5.0,
            vertical_aperture_mm=4.0,
            position_m=(0.0, 0.0, 1.0),
        )
        UsdGeom.Camera.Define(stage, config.prim_path)
        with pytest.raises(ValidationError, match="width"):
            validate_camera_frustum(stage, config)

    def test_frustum_math_correct(self):
        # Verify math: fl=10.48, ha=20.955, va=15.716, h=3.0 => ~6.0 x 4.5 coverage
        config = CameraConfig()
        fl, ha, va, h = (
            config.focal_length_mm,
            config.horizontal_aperture_mm,
            config.vertical_aperture_mm,
            config.position_m[2],
        )
        covered_w = 2.0 * h * math.tan(math.atan(ha / (2.0 * fl)))
        covered_d = 2.0 * h * math.tan(math.atan(va / (2.0 * fl)))
        assert covered_w == pytest.approx(config.roi_width_m, rel=0.05)
        assert covered_d == pytest.approx(config.roi_depth_m, rel=0.05)


def test_calibration_position_error_euclidean():
    from isaac.vgu_sim.validation import calibration_position_error

    err = calibration_position_error(measured=(1.03, -0.46), ground_truth=(1.0, -0.5))
    assert abs(err - 0.05) < 1e-9


def test_calibration_position_error_zero_on_match():
    from isaac.vgu_sim.validation import calibration_position_error

    assert calibration_position_error((2.0, 3.0), (2.0, 3.0)) == 0.0

# tests/unit/test_m6_validation.py
import math

import pytest

from isaac.vgu_sim.config import CameraConfig, ScenarioConfig
from isaac.vgu_sim.validation import (
    ValidationError,
    validate_camera_frustum,
    validate_scenario_obstacles,
    validate_stage_metadata,
)
from tests.unit.test_m6_config import VALID_HEAD_ON


def _make_stage(tmp_path, *, meters_per_unit=1.0, up_axis="Z", default_prim="/World"):
    from pxr import Usd, UsdGeom

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
        pytest.importorskip("pxr")
        stage = _make_stage(tmp_path)
        validate_stage_metadata(stage)  # no exception

    def test_wrong_meters_per_unit_fails(self, tmp_path):
        pytest.importorskip("pxr")
        stage = _make_stage(tmp_path, meters_per_unit=100.0)
        with pytest.raises(ValidationError, match="metersPerUnit"):
            validate_stage_metadata(stage)

    def test_wrong_up_axis_fails(self, tmp_path):
        pytest.importorskip("pxr")
        stage = _make_stage(tmp_path, up_axis="Y")
        with pytest.raises(ValidationError, match="upAxis"):
            validate_stage_metadata(stage)

    def test_wrong_default_prim_fails(self, tmp_path):
        pytest.importorskip("pxr")
        stage = _make_stage(tmp_path, default_prim="/Foo")
        with pytest.raises(ValidationError, match="defaultPrim"):
            validate_stage_metadata(stage)


class TestValidateCameraFrustum:
    def test_default_config_passes(self, tmp_path):
        pytest.importorskip("pxr")
        from pxr import UsdGeom

        stage = _make_stage(tmp_path)
        config = CameraConfig()
        # Add camera prim so the check doesn't fail on missing prim
        UsdGeom.Camera.Define(stage, config.prim_path)
        validate_camera_frustum(stage, config)  # no exception

    def test_missing_camera_prim_fails(self, tmp_path):
        pytest.importorskip("pxr")
        stage = _make_stage(tmp_path)
        config = CameraConfig()
        with pytest.raises(ValidationError, match="Camera prim not found"):
            validate_camera_frustum(stage, config)

    def test_insufficient_width_fails(self, tmp_path):
        pytest.importorskip("pxr")
        from pxr import UsdGeom

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


def _obstacle_scenario() -> ScenarioConfig:
    return ScenarioConfig.model_validate(
        {
            **VALID_HEAD_ON,
            "static_obstacles": [
                {
                    "obstacle_id": "blocker_west",
                    "pose": {"x": -1.85, "y": 0.0, "yaw_rad": 0.0},
                },
            ],
            "timed_obstacles": [
                {
                    "obstacle_id": "blocker_east",
                    "asset": "dynamic_obstacle.usd",
                    "spawn_at_sec": 10.0,
                    "pose": {"x": 1.0, "y": 0.0, "yaw_rad": 0.0},
                },
            ],
        }
    )


def test_validate_scenario_obstacles_raises_for_missing_prim(tmp_path):
    stage = _make_stage(tmp_path)

    with pytest.raises(
        ValidationError, match="/World/Scenario/StaticObstacles/blocker_west"
    ):
        validate_scenario_obstacles(stage, _obstacle_scenario())


def test_validate_scenario_obstacles_passes_when_prims_exist(tmp_path):
    from pxr import UsdGeom

    stage = _make_stage(tmp_path)
    UsdGeom.Cube.Define(stage, "/World/Scenario/StaticObstacles/blocker_west")
    UsdGeom.Cube.Define(stage, "/World/DynamicObstacles/blocker_east")

    validate_scenario_obstacles(stage, _obstacle_scenario())  # no exception


class TestValidateRobotLoadProp:
    def test_raises_when_loaded_but_prop_missing(self, tmp_path):
        pytest.importorskip("pxr")
        from isaac.vgu_sim.validation import validate_robot_load_prop

        stage = _make_stage(tmp_path)
        with pytest.raises(ValidationError, match="loaded but load_prop missing"):
            validate_robot_load_prop(stage, "/World/Robots/robot_1", True)

    def test_raises_when_not_loaded_but_prop_present(self, tmp_path):
        pytest.importorskip("pxr")
        from pxr import UsdGeom

        from isaac.vgu_sim.validation import validate_robot_load_prop

        stage = _make_stage(tmp_path)
        UsdGeom.Cube.Define(
            stage, "/World/Robots/robot_1/Geometry/base_footprint/base_link/load_prop"
        )
        with pytest.raises(ValidationError, match="not loaded but load_prop present"):
            validate_robot_load_prop(stage, "/World/Robots/robot_1", False)

    def test_passes_when_presence_matches_expected(self, tmp_path):
        pytest.importorskip("pxr")
        from pxr import UsdGeom

        from isaac.vgu_sim.validation import validate_robot_load_prop

        stage = _make_stage(tmp_path)
        validate_robot_load_prop(stage, "/World/Robots/robot_1", False)  # no exception
        UsdGeom.Cube.Define(
            stage, "/World/Robots/robot_1/Geometry/base_footprint/base_link/load_prop"
        )
        validate_robot_load_prop(stage, "/World/Robots/robot_1", True)  # no exception

    def test_raises_when_prop_carries_a_collider(self, tmp_path):
        pytest.importorskip("pxr")
        from pxr import UsdGeom, UsdPhysics

        from isaac.vgu_sim.validation import validate_robot_load_prop

        stage = _make_stage(tmp_path)
        cube = UsdGeom.Cube.Define(
            stage, "/World/Robots/robot_1/Geometry/base_footprint/base_link/load_prop"
        )
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        with pytest.raises(ValidationError, match="unexpectedly carries"):
            validate_robot_load_prop(stage, "/World/Robots/robot_1", True)


def test_calibration_position_error_euclidean():
    from isaac.vgu_sim.validation import calibration_position_error

    err = calibration_position_error(measured=(1.03, -0.46), ground_truth=(1.0, -0.5))
    assert abs(err - 0.05) < 1e-9


def test_calibration_position_error_zero_on_match():
    from isaac.vgu_sim.validation import calibration_position_error

    assert calibration_position_error((2.0, 3.0), (2.0, 3.0)) == 0.0

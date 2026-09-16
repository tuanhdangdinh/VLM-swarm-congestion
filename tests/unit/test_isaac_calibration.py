import math

import numpy as np
import pytest

from isaac.vgu_sim.calibration import (
    ANALYTIC_CREATED_AT,
    MARKER_HEIGHT_M,
    build_calibration_dict,
    camera_intrinsics,
    pixel_to_world_homography,
)
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


def _nadir_world_to_pixel(cfg, x, y):
    """Independent oracle: closed-form nadir projection (world -> pixel)."""
    fx = cfg.focal_length_mm / cfg.horizontal_aperture_mm * cfg.width
    fy = cfg.focal_length_mm / cfg.vertical_aperture_mm * cfg.height
    cx, cy = cfg.width / 2.0, cfg.height / 2.0
    h = cfg.position_m[2]
    u = cx + fx * x / h
    v = cy - fy * y / h
    return u, v


def _apply_h(h_mat, u, v):
    """Map a pixel through a 3x3 pixel->world homography to (X, Y)."""
    p = h_mat @ np.array([u, v, 1.0])
    return p[0] / p[2], p[1] / p[2]


def test_homography_origin_maps_to_image_center():
    cfg = CameraConfig()
    h_mat = pixel_to_world_homography(cfg)
    x, y = _apply_h(h_mat, cfg.width / 2.0, cfg.height / 2.0)
    assert abs(x) < 1e-9
    assert abs(y) < 1e-9


def test_homography_at_marker_height_scales_ground_plane_by_camera_ratio():
    cfg = CameraConfig()
    h_ground = pixel_to_world_homography(cfg)
    h_marker = pixel_to_world_homography(cfg, MARKER_HEIGHT_M)
    ratio = (cfg.position_m[2] - MARKER_HEIGHT_M) / cfg.position_m[2]

    for u, v in ((740.0, 540.0), (300.0, 120.0), (1100.0, 900.0)):
        x0, y0 = _apply_h(h_ground, u, v)
        xm, ym = _apply_h(h_marker, u, v)
        assert math.isclose(xm, x0 * ratio, rel_tol=1e-12, abs_tol=1e-12)
        assert math.isclose(ym, y0 * ratio, rel_tol=1e-12, abs_tol=1e-12)


def test_homography_plane_height_zero_matches_previous_behaviour():
    cfg = CameraConfig()
    previous = np.array(
        [
            [0.004686381798664122, 0.0, -2.9992843511450378],
            [-0.0, -0.004686307251908397, 2.2494274809160304],
            [0.0, 0.0, 1.0],
        ]
    )
    assert np.allclose(pixel_to_world_homography(cfg), previous, rtol=0, atol=1e-15)
    assert np.array_equal(
        pixel_to_world_homography(cfg),
        pixel_to_world_homography(cfg, 0.0),
    )


def test_marker_height_matches_marker_asset_constant():
    pytest.importorskip("pxr")
    from isaac.vgu_sim.marker_asset import MARKER_HEIGHT_M as asset_height

    assert MARKER_HEIGHT_M == asset_height


def test_homography_round_trip_over_roi():
    cfg = CameraConfig()
    h_mat = pixel_to_world_homography(cfg)
    xs = np.linspace(-cfg.roi_width_m / 2, cfg.roi_width_m / 2, 5)
    ys = np.linspace(-cfg.roi_depth_m / 2, cfg.roi_depth_m / 2, 5)
    for x in xs:
        for y in ys:
            u, v = _nadir_world_to_pixel(cfg, x, y)
            xr, yr = _apply_h(h_mat, u, v)
            assert abs(xr - x) < 1e-6, f"X at ({x},{y}) -> {xr}"
            assert abs(yr - y) < 1e-6, f"Y at ({x},{y}) -> {yr}"


def test_homography_one_meter_x_offset_pixel_shift():
    cfg = CameraConfig()
    fx = cfg.focal_length_mm / cfg.horizontal_aperture_mm * cfg.width
    h = cfg.position_m[2]
    u0, _ = _nadir_world_to_pixel(cfg, 0.0, 0.0)
    u1, _ = _nadir_world_to_pixel(cfg, 1.0, 0.0)
    assert abs((u1 - u0) - fx / h) < 1e-9


# === New M6 validation tests (Isaac-specific) ===


def test_build_calibration_dict_has_required_schema_keys():
    cfg = CameraConfig()
    d = build_calibration_dict(cfg)
    assert set(d.keys()) == {
        "intrinsics",
        "distortion",
        "homography",
        "image_size",
        "source_id",
        "created_at",
        "plane_height_m",
    }
    assert np.array(d["intrinsics"]).shape == (3, 3)
    assert np.array(d["homography"]).shape == (3, 3)
    assert d["distortion"] == [0.0, 0.0, 0.0, 0.0, 0.0]
    assert d["image_size"] == [cfg.width, cfg.height]
    assert d["source_id"] == "isaac_sim"
    assert d["created_at"] == ANALYTIC_CREATED_AT


def test_calibration_dict_records_plane_height():
    d = build_calibration_dict(CameraConfig())
    assert d["plane_height_m"] == MARKER_HEIGHT_M


def test_calibration_dict_records_overridden_plane_height():
    d = build_calibration_dict(CameraConfig(), 0.0)
    assert d["plane_height_m"] == 0.0


def test_build_calibration_dict_homography_not_identity():
    d = build_calibration_dict(CameraConfig())
    assert not np.allclose(np.array(d["homography"]), np.eye(3))


def test_build_calibration_dict_is_deterministic():
    assert build_calibration_dict(CameraConfig()) == build_calibration_dict(CameraConfig())


def test_exported_yaml_loads_via_swarm_perception(tmp_path):
    import yaml

    out = tmp_path / "calibration.yaml"
    out.write_text(yaml.safe_dump(build_calibration_dict(CameraConfig())))

    swarm_perception = pytest.importorskip("swarm_perception.calibration")
    artifact = swarm_perception.load_calibration(out)
    assert artifact.image_size == (1280, 960)
    assert not np.allclose(artifact.homography, np.eye(3))
    assert artifact.source_id == "isaac_sim"


def test_known_pixel_marker_maps_to_world_point_on_the_marker_plane(monkeypatch, tmp_path):
    import yaml

    pytest.importorskip("cv2")
    pipeline = pytest.importorskip("swarm_perception.pipeline")
    sp_cal = pytest.importorskip("swarm_perception.calibration")
    models = pytest.importorskip("swarm_perception.models")
    estimator_mod = pytest.importorskip("swarm_perception.state_estimator")

    cfg = CameraConfig()
    out = tmp_path / "calibration.yaml"
    out.write_text(yaml.safe_dump(build_calibration_dict(cfg)))
    calibration = sp_cal.load_calibration(out)

    u_c, v_c = cfg.width / 2.0 + 100, cfg.height / 2.0 + 60
    half = 10.0
    corners = np.array(
        [
            [u_c - half, v_c - half],
            [u_c + half, v_c - half],
            [u_c + half, v_c + half],
            [u_c - half, v_c + half],
        ],
        dtype=np.float64,
    )

    # detect_aruco_markers returns (list[int], list[np.ndarray (4,2)])
    # pipeline imports it directly, so monkeypatch on the pipeline module attribute
    def fake_detect(image, dictionary_name="DICT_4X4_50", detector_params=None):
        return [7], [corners]

    monkeypatch.setattr(pipeline, "detect_aruco_markers", fake_detect)

    frame = models.Frame(
        image=np.zeros((cfg.height, cfg.width, 3), dtype=np.uint8),
        stamp=1.0,
        frame_id="overhead_camera",
        source_id="isaac_sim",
    )
    est = estimator_mod.StateEstimator(velocity_alpha=1.0)
    scene_state, _ = pipeline.process_frame(frame, calibration, est)

    fx = cfg.focal_length_mm / cfg.horizontal_aperture_mm * cfg.width
    fy = cfg.focal_length_mm / cfg.vertical_aperture_mm * cfg.height
    # The exported homography targets the marker plane, so the oracle uses the
    # camera height above that plane, not above the floor.
    h = cfg.position_m[2] - MARKER_HEIGHT_M
    exp_x = (u_c - cfg.width / 2.0) * h / fx
    exp_y = (cfg.height / 2.0 - v_c) * h / fy

    assert len(scene_state.robots) == 1
    robot = scene_state.robots[0]
    assert robot.robot_id == "robot_7"
    assert abs(robot.x - exp_x) < 1e-3
    assert abs(robot.y - exp_y) < 1e-3

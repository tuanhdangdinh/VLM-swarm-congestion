"""Unit tests for M1 Perception & Robot ID Tracking.

Tests are organized by module and cover:
  - Pydantic model validators (models.py)
  - Geometry functions (geometry.py)
  - Calibration I/O (calibration.py)
  - Detection helpers (detection.py)
  - State estimation helpers (state_estimator.py)
  - StateEstimator.update end-to-end
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from swarm_perception.detection import filter_duplicate_detections
from swarm_perception.geometry import (
    estimate_marker_heading,
    pixel_to_world,
    pixels_to_world,
    world_to_pixel,
)
from swarm_perception.models import (
    CalibrationArtifact,
    Frame,
    MarkerDetection,
    RobotState,
    SceneState,
    scene_state_to_json_dict,
)
from swarm_perception.state_estimator import (
    StateEstimator,
    build_scene_diagnostics,
    classify_motion_status,
    estimate_velocity,
    low_pass_filter,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _identity_calibration() -> CalibrationArtifact:
    return CalibrationArtifact(
        intrinsics=np.eye(3),
        distortion=np.zeros(5),
        homography=np.eye(3),
        image_size=(640, 480),
        source_id="test",
        created_at=0.0,
    )


def _make_detection(
    marker_id: int = 0,
    center_world: tuple[float, float] = (1.0, 2.0),
    theta: float = 0.0,
    confidence: float = 1.0,
) -> MarkerDetection:
    corners = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    return MarkerDetection(
        marker_id=marker_id,
        corner_pixels=corners,
        center_pixel=(0.5, 0.5),
        center_world=center_world,
        theta=theta,
        confidence=confidence,
    )


def _make_robot_state(
    robot_id: str = "robot_0",
    x: float = 0.0,
    y: float = 0.0,
    theta: float = 0.0,
    lv: float = 0.0,
    av: float = 0.0,
    stamp: float = 0.0,
) -> RobotState:
    return RobotState(
        robot_id=robot_id,
        x=x,
        y=y,
        theta=theta,
        linear_velocity=lv,
        angular_velocity=av,
        task=None,
        status="STOPPED",
        goal=None,
        stamp=stamp,
    )


# ---------------------------------------------------------------------------
# Model validators
# ---------------------------------------------------------------------------

class TestFrameValidator:
    def test_valid_rgb(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        f = Frame(image=img, stamp=1.0, frame_id="cam", source_id="test")
        assert f.image.shape == (480, 640, 3)

    def test_rejects_grayscale(self):
        img = np.zeros((480, 640), dtype=np.uint8)
        with pytest.raises(Exception):
            Frame(image=img, stamp=1.0, frame_id="cam", source_id="test")

    def test_rejects_wrong_channels(self):
        img = np.zeros((480, 640, 4), dtype=np.uint8)
        with pytest.raises(Exception):
            Frame(image=img, stamp=1.0, frame_id="cam", source_id="test")

    def test_rejects_negative_stamp(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        with pytest.raises(Exception):
            Frame(image=img, stamp=-1.0, frame_id="cam", source_id="test")


class TestCalibrationArtifactValidator:
    def test_valid(self):
        cal = _identity_calibration()
        assert cal.homography.shape == (3, 3)
        assert cal.intrinsics.shape == (3, 3)

    def test_bad_intrinsics_shape(self):
        with pytest.raises(Exception):
            CalibrationArtifact(
                intrinsics=np.eye(4),
                distortion=np.zeros(5),
                homography=np.eye(3),
                image_size=(640, 480),
                source_id="test",
                created_at=0.0,
            )

    def test_bad_homography_shape(self):
        with pytest.raises(Exception):
            CalibrationArtifact(
                intrinsics=np.eye(3),
                distortion=np.zeros(5),
                homography=np.eye(4),
                image_size=(640, 480),
                source_id="test",
                created_at=0.0,
            )


class TestMarkerDetectionValidator:
    def test_valid(self):
        det = _make_detection()
        assert det.corner_pixels.shape == (4, 2)

    def test_bad_corners_shape(self):
        with pytest.raises(Exception):
            MarkerDetection(
                marker_id=0,
                corner_pixels=np.zeros((3, 2)),
                center_pixel=(0.0, 0.0),
                center_world=(0.0, 0.0),
                theta=0.0,
                confidence=1.0,
            )


class TestSceneStateJson:
    def test_serializable(self):
        state = SceneState(
            stamp=1.0,
            frame_id="cam",
            robots=[],
            diagnostics={"markers_detected": 0, "ids_missing": [], "dropped_frame": False},
        )
        d = scene_state_to_json_dict(state)
        assert d["stamp"] == 1.0
        assert d["robots"] == []


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

class TestPixelToWorld:
    def test_identity_homography(self):
        H = np.eye(3)
        wx, wy = pixel_to_world((100.0, 200.0), H)
        assert pytest.approx(wx) == 100.0
        assert pytest.approx(wy) == 200.0

    def test_scale_homography(self):
        H = np.diag([0.01, 0.01, 1.0])
        wx, wy = pixel_to_world((100.0, 50.0), H)
        assert pytest.approx(wx) == 1.0
        assert pytest.approx(wy) == 0.5


class TestWorldToPixel:
    def test_roundtrip_identity(self):
        H = np.eye(3)
        px, py = world_to_pixel((3.5, 7.2), H)
        assert px == 4  # rounds
        assert py == 7

    def test_roundtrip_scale(self):
        H = np.diag([0.01, 0.01, 1.0])
        wx, wy = pixel_to_world((320.0, 240.0), H)
        ux, uy = world_to_pixel((wx, wy), H)
        assert ux == 320
        assert uy == 240


class TestPixelsToWorld:
    def test_batch_identity(self):
        H = np.eye(3)
        pixels = np.array([[0.0, 0.0], [100.0, 200.0], [50.0, 75.0]])
        result = pixels_to_world(pixels, H)
        np.testing.assert_allclose(result, pixels)

    def test_batch_scale(self):
        H = np.diag([0.01, 0.01, 1.0])
        pixels = np.array([[100.0, 200.0]])
        result = pixels_to_world(pixels, H)
        assert pytest.approx(result[0, 0]) == 1.0
        assert pytest.approx(result[0, 1]) == 2.0


class TestEstimateMarkerHeading:
    def test_facing_north(self):
        # Top edge above bottom edge → heading toward +y (north), theta ≈ π/2
        corners = np.array([
            [-0.5, 1.0],   # TL
            [0.5, 1.0],    # TR
            [0.5, 0.0],    # BR
            [-0.5, 0.0],   # BL
        ])
        theta = estimate_marker_heading(corners)
        assert pytest.approx(theta, abs=1e-6) == math.pi / 2

    def test_facing_east(self):
        # Top edge to the right → heading toward +x (east), theta ≈ 0
        corners = np.array([
            [1.0, 0.5],    # TL
            [1.0, -0.5],   # TR
            [0.0, -0.5],   # BR
            [0.0, 0.5],    # BL
        ])
        theta = estimate_marker_heading(corners)
        assert pytest.approx(theta, abs=1e-6) == 0.0

    def test_facing_south(self):
        # Top edge below bottom edge → heading toward -y (south), theta ≈ -π/2
        corners = np.array([
            [-0.5, -1.0],  # TL (top edge is lower in world)
            [0.5, -1.0],   # TR
            [0.5, 0.0],    # BR
            [-0.5, 0.0],   # BL
        ])
        theta = estimate_marker_heading(corners)
        assert pytest.approx(theta, abs=1e-6) == -math.pi / 2


# ---------------------------------------------------------------------------
# Calibration I/O
# ---------------------------------------------------------------------------

class TestCalibrationIO:
    def test_save_and_load_roundtrip(self, tmp_path):
        from swarm_perception.calibration import load_calibration, save_calibration

        cal = _identity_calibration()
        path = tmp_path / "cal.yaml"
        save_calibration(cal, path)
        loaded = load_calibration(path)

        np.testing.assert_allclose(loaded.homography, cal.homography)
        np.testing.assert_allclose(loaded.intrinsics, cal.intrinsics)
        assert loaded.source_id == "test"
        assert loaded.image_size == (640, 480)

    def test_load_missing_file_raises(self, tmp_path):
        from swarm_perception.calibration import load_calibration
        from swarm_perception.frame_source import CalibrationError

        with pytest.raises(CalibrationError):
            load_calibration(tmp_path / "nonexistent.yaml")

    def test_load_incomplete_file_raises(self, tmp_path):
        from swarm_perception.calibration import load_calibration
        from swarm_perception.frame_source import CalibrationError

        p = tmp_path / "bad.yaml"
        p.write_text("intrinsics: [[1,0,0],[0,1,0],[0,0,1]]\n")
        with pytest.raises(CalibrationError):
            load_calibration(p)

    def test_load_empty_file_raises_calibration_error(self, tmp_path):
        from swarm_perception.calibration import load_calibration
        from swarm_perception.frame_source import CalibrationError

        p = tmp_path / "empty.yaml"
        p.write_text("")
        with pytest.raises(CalibrationError):
            load_calibration(p)

    def test_load_toplevel_list_raises_calibration_error(self, tmp_path):
        from swarm_perception.calibration import load_calibration
        from swarm_perception.frame_source import CalibrationError

        p = tmp_path / "list.yaml"
        p.write_text("- 1\n- 2\n")
        with pytest.raises(CalibrationError):
            load_calibration(p)


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

class TestFilterDuplicateDetections:
    def test_no_duplicates_unchanged(self):
        dets = [_make_detection(0), _make_detection(1), _make_detection(2)]
        result = filter_duplicate_detections(dets)
        ids = {d.marker_id for d in result}
        assert ids == {0, 1, 2}

    def test_keeps_highest_confidence(self):
        low = _make_detection(marker_id=5, confidence=0.6)
        high = _make_detection(marker_id=5, confidence=0.9)
        result = filter_duplicate_detections([low, high])
        assert len(result) == 1
        assert result[0].confidence == 0.9

    def test_first_seen_wins_on_tie(self):
        d1 = _make_detection(marker_id=3, confidence=1.0)
        d2 = _make_detection(marker_id=3, confidence=1.0)
        result = filter_duplicate_detections([d1, d2])
        assert len(result) == 1

    def test_empty(self):
        assert filter_duplicate_detections([]) == []


# ---------------------------------------------------------------------------
# State estimation helpers
# ---------------------------------------------------------------------------

class TestEstimateVelocity:
    def test_zero_dt_returns_zeros(self):
        prev = _make_robot_state(x=0.0, y=0.0, theta=0.0, stamp=1.0)
        lv, av = estimate_velocity(prev, (1.0, 0.0, 0.0), 1.0)
        assert lv == 0.0
        assert av == 0.0

    def test_negative_dt_returns_zeros(self):
        # Out-of-order / reordered frame (older stamp) must not produce a
        # negative speed; it should be treated like a zero delta.
        prev = _make_robot_state(x=0.0, y=0.0, theta=0.0, stamp=10.0)
        lv, av = estimate_velocity(prev, (1.0, 0.0, 0.0), 9.0)
        assert lv == 0.0
        assert av == 0.0

    def test_linear_velocity(self):
        prev = _make_robot_state(x=0.0, y=0.0, theta=0.0, stamp=0.0)
        lv, av = estimate_velocity(prev, (0.1, 0.0, 0.0), 1.0)
        assert pytest.approx(lv) == 0.1
        assert pytest.approx(av) == 0.0

    def test_angular_velocity(self):
        prev = _make_robot_state(x=0.0, y=0.0, theta=0.0, stamp=0.0)
        lv, av = estimate_velocity(prev, (0.0, 0.0, math.pi / 2), 1.0)
        assert pytest.approx(av) == math.pi / 2

    def test_angular_normalization_wraps(self):
        prev = _make_robot_state(x=0.0, y=0.0, theta=math.pi - 0.01, stamp=0.0)
        lv, av = estimate_velocity(prev, (0.0, 0.0, -(math.pi - 0.01)), 1.0)
        # dtheta should be a small positive value after wrapping, not ≈ 2π
        assert abs(av) < 0.1


class TestLowPassFilter:
    def test_alpha_one_returns_measured(self):
        assert pytest.approx(low_pass_filter(10.0, 5.0, 1.0)) == 5.0

    def test_alpha_zero_returns_previous(self):
        assert pytest.approx(low_pass_filter(10.0, 5.0, 0.0)) == 10.0

    def test_alpha_half(self):
        assert pytest.approx(low_pass_filter(0.0, 1.0, 0.5)) == 0.5


class TestClassifyMotionStatus:
    def test_stale(self):
        assert classify_motion_status(0.5, 2.0, 0.01, 0.05, 1.0) == "STALE"

    def test_stopped(self):
        assert classify_motion_status(0.005, 0.0, 0.01, 0.05, 1.0) == "STOPPED"

    def test_slow(self):
        assert classify_motion_status(0.03, 0.0, 0.01, 0.05, 1.0) == "SLOW"

    def test_moving(self):
        assert classify_motion_status(0.15, 0.0, 0.01, 0.05, 1.0) == "MOVING"

    def test_stale_takes_priority_over_moving(self):
        assert classify_motion_status(1.0, 5.0, 0.01, 0.05, 1.0) == "STALE"


class TestBuildSceneDiagnostics:
    def test_all_present(self):
        dets = [_make_detection(0), _make_detection(1)]
        d = build_scene_diagnostics(dets, {"robot_0", "robot_1"})
        assert d["markers_detected"] == 2
        assert d["ids_missing"] == []
        assert d["dropped_frame"] is False

    def test_missing_ids_sorted(self):
        dets = [_make_detection(2)]
        d = build_scene_diagnostics(dets, {"robot_0", "robot_1", "robot_2"})
        assert d["ids_missing"] == ["robot_0", "robot_1"]

    def test_dropped_frame_passthrough(self):
        d = build_scene_diagnostics([], set(), dropped_frame=True)
        assert d["dropped_frame"] is True

    def test_empty_expected(self):
        dets = [_make_detection(0)]
        d = build_scene_diagnostics(dets, set())
        assert d["ids_missing"] == []

    def test_ids_unexpected_populated_for_rogue_detections(self):
        dets = [_make_detection(1), _make_detection(2), _make_detection(20), _make_detection(37)]
        d = build_scene_diagnostics(dets, {"robot_1", "robot_2"})
        assert d["ids_unexpected"] == ["robot_20", "robot_37"]

    def test_ids_unexpected_empty_when_no_registry(self):
        dets = [_make_detection(0), _make_detection(5)]
        d = build_scene_diagnostics(dets, set())
        assert d["ids_unexpected"] == []


# ---------------------------------------------------------------------------
# StateEstimator.update
# ---------------------------------------------------------------------------

class TestStateEstimatorUpdate:
    def _estimator(self) -> StateEstimator:
        return StateEstimator(
            stopped_threshold_mps=0.01,
            slow_threshold_mps=0.05,
            stale_after_sec=1.0,
            velocity_alpha=1.0,  # raw velocity, no smoothing
        )

    def test_robot_id_format(self):
        est = self._estimator()
        det = _make_detection(marker_id=3, center_world=(0.5, 0.5))
        state = est.update([det], stamp=1.0)
        assert state.robots[0].robot_id == "robot_3"

    def test_first_frame_velocity_zero(self):
        est = self._estimator()
        det = _make_detection(marker_id=0, center_world=(1.0, 2.0))
        state = est.update([det], stamp=0.0)
        r = state.robots[0]
        assert r.linear_velocity == 0.0
        assert r.angular_velocity == 0.0

    def test_velocity_estimated_on_second_frame(self):
        est = self._estimator()
        det1 = _make_detection(marker_id=0, center_world=(0.0, 0.0))
        est.update([det1], stamp=0.0)
        det2 = _make_detection(marker_id=0, center_world=(0.1, 0.0))
        state = est.update([det2], stamp=1.0)
        r = state.robots[0]
        assert pytest.approx(r.linear_velocity, abs=1e-6) == 0.1

    def test_task_injected_from_registry(self):
        est = self._estimator()
        det = _make_detection(marker_id=1)
        registry = {"robot_1": {"task": "deliver_A", "goal": None}}
        state = est.update([det], stamp=0.0, task_registry=registry)
        assert state.robots[0].task == "deliver_A"

    def test_status_not_from_registry(self):
        est = self._estimator()
        det = _make_detection(marker_id=0)
        # Even if registry had a status-like field, status comes from velocity
        registry = {"robot_0": {"task": None, "status": "MOVING"}}  # status key ignored
        state = est.update([det], stamp=0.0, task_registry=registry)
        # First frame → STOPPED (lv=0)
        assert state.robots[0].status == "STOPPED"

    def test_missing_robot_becomes_stale(self):
        est = self._estimator()
        det = _make_detection(marker_id=0, center_world=(1.0, 1.0))
        est.update([det], stamp=0.0)
        # Second frame: robot_0 absent, stamp advances past stale_after_sec=1.0
        state = est.update([], stamp=1.5)
        assert len(state.robots) == 1
        assert state.robots[0].status == "STALE"

    def test_diagnostics_embedded(self):
        est = self._estimator()
        det = _make_detection(marker_id=0)
        state = est.update(
            [det], stamp=0.0,
            expected_robot_ids={"robot_0", "robot_1"},
        )
        assert state.diagnostics["markers_detected"] == 1
        assert state.diagnostics["ids_missing"] == ["robot_1"]

    def test_late_frame_suppressed_and_flagged_dropped(self):
        est = self._estimator()
        # In-order frame establishes state at stamp 10.0, pose x=0.0.
        est.update([_make_detection(marker_id=0, center_world=(0.0, 0.0))], stamp=10.0)
        # A late frame (older stamp) must not overwrite state, and the published
        # SceneState must be temporally consistent: no robots (so no robot stamp
        # newer than the frame stamp) and dropped_frame flagged.
        state = est.update([_make_detection(marker_id=0, center_world=(5.0, 0.0))], stamp=9.0)
        assert state.stamp == 9.0
        assert state.robots == []
        assert state.diagnostics["dropped_frame"] is True
        # No RobotState carries a stamp newer than the SceneState stamp.
        assert all(r.stamp <= state.stamp for r in state.robots)

    def test_late_frame_does_not_corrupt_subsequent_velocity(self):
        est = self._estimator()
        est.update([_make_detection(marker_id=0, center_world=(0.0, 0.0))], stamp=10.0)
        est.update([_make_detection(marker_id=0, center_world=(5.0, 0.0))], stamp=9.0)  # late
        # Next in-order frame computes velocity against the preserved 10.0 pose,
        # not the rejected late one, so no spurious spike.
        state2 = est.update(
            [_make_detection(marker_id=0, center_world=(0.01, 0.0))], stamp=10.1
        )
        assert state2.robots[0].linear_velocity == pytest.approx(0.1, abs=1e-6)
        assert state2.robots[0].stamp == 10.1

    def test_small_backward_jump_dropped_as_late_frame(self):
        est = self._estimator()  # default clock_reset_threshold_sec=1.0
        est.update([_make_detection(marker_id=0, center_world=(0.0, 0.0))], stamp=10.0)
        state = est.update([_make_detection(marker_id=0, center_world=(5.0, 0.0))], stamp=9.5)
        assert state.robots == []
        assert state.diagnostics["dropped_frame"] is True
        assert "clock_reset" not in state.diagnostics

    def test_large_backward_jump_processes_frame_as_first(self):
        est = self._estimator()
        est.update([_make_detection(marker_id=0, center_world=(0.0, 0.0))], stamp=100.0)
        state = est.update([_make_detection(marker_id=0, center_world=(1.0, 0.0))], stamp=2.0)
        assert [r.robot_id for r in state.robots] == ["robot_0"]
        assert state.robots[0].stamp == 2.0
        assert state.robots[0].x == pytest.approx(1.0)
        assert state.robots[0].linear_velocity == 0.0

    def test_large_backward_jump_flags_clock_reset_in_diagnostics(self):
        est = self._estimator()
        est.update([_make_detection(marker_id=0)], stamp=100.0)
        state = est.update([_make_detection(marker_id=0)], stamp=2.0)
        assert state.diagnostics["clock_reset"] is True
        assert state.diagnostics["clock_reset_prev_stamp"] == 100.0
        assert state.diagnostics["dropped_frame"] is False

    def test_large_backward_jump_clears_tracks_missing_from_reset_frame(self):
        est = self._estimator()
        est.update([_make_detection(0), _make_detection(1)], stamp=100.0)
        state = est.update([_make_detection(0)], stamp=2.0)
        assert {r.robot_id for r in state.robots} == {"robot_0"}

    def test_tracking_resumes_after_clock_reset(self):
        est = self._estimator()
        est.update([_make_detection(marker_id=0, center_world=(0.0, 0.0))], stamp=100.0)
        est.update([_make_detection(marker_id=0, center_world=(1.0, 0.0))], stamp=2.0)
        state = est.update([_make_detection(marker_id=0, center_world=(1.01, 0.0))], stamp=2.1)
        assert state.robots[0].linear_velocity == pytest.approx(0.1, abs=1e-6)
        assert state.diagnostics["dropped_frame"] is False
        assert "clock_reset" not in state.diagnostics

    def test_clock_reset_threshold_configurable(self):
        est = StateEstimator(velocity_alpha=1.0, clock_reset_threshold_sec=0.2)
        est.update([_make_detection(marker_id=0)], stamp=10.0)
        state = est.update([_make_detection(marker_id=0)], stamp=9.5)
        assert state.diagnostics["clock_reset"] is True

    def test_clock_reset_threshold_nonpositive_rejected(self):
        with pytest.raises(ValueError):
            StateEstimator(clock_reset_threshold_sec=0.0)

    def test_forward_path_output_unchanged_by_clock_reset_threshold(self):
        # A forward-only stream (plus a small late frame) never crosses any
        # threshold, so output must match an estimator that effectively has none.
        stamps = [0.0, 0.1, 0.2, 0.15, 0.3, 1.8, 1.9]
        default = self._estimator()
        no_reset = StateEstimator(
            stopped_threshold_mps=0.01,
            slow_threshold_mps=0.05,
            stale_after_sec=1.0,
            velocity_alpha=1.0,
            clock_reset_threshold_sec=1e9,
        )
        for i, stamp in enumerate(stamps):
            dets = [_make_detection(0, center_world=(0.01 * i, 0.0))] if i != 5 else []
            a = default.update(dets, stamp=stamp)
            b = no_reset.update(dets, stamp=stamp)
            assert a.model_dump(mode="json") == b.model_dump(mode="json")
            assert set(a.diagnostics) == {
                "markers_detected", "ids_missing", "ids_unexpected", "dropped_frame",
            }

    def test_multiple_robots(self):
        est = self._estimator()
        dets = [_make_detection(i) for i in range(4)]
        state = est.update(dets, stamp=0.0)
        ids = {r.robot_id for r in state.robots}
        assert ids == {"robot_0", "robot_1", "robot_2", "robot_3"}

    def test_goal_from_registry(self):
        est = self._estimator()
        det = _make_detection(marker_id=2)
        registry = {"robot_2": {"task": "go", "goal": {"x": 3.0, "y": 4.5}}}
        state = est.update([det], stamp=0.0, task_registry=registry)
        assert state.robots[0].goal == pytest.approx((3.0, 4.5))

    def test_frame_id_override(self):
        est = self._estimator()
        det = _make_detection(marker_id=0)
        state = est.update([det], stamp=0.0, frame_id="overhead_camera")
        assert state.frame_id == "overhead_camera"

    def test_frame_id_falls_back_to_default(self):
        est = StateEstimator(velocity_alpha=1.0, frame_id="fallback_cam")
        det = _make_detection(marker_id=0)
        state = est.update([det], stamp=0.0)
        assert state.frame_id == "fallback_cam"

    def test_rogue_markers_excluded_when_registry_provided(self):
        est = self._estimator()
        dets = [_make_detection(1), _make_detection(2), _make_detection(20), _make_detection(37)]
        registry = {"robot_1": {}, "robot_2": {}}
        state = est.update(dets, stamp=0.0, task_registry=registry,
                           expected_robot_ids={"robot_1", "robot_2"})
        ids = {r.robot_id for r in state.robots}
        assert ids == {"robot_1", "robot_2"}

    def test_rogue_markers_reported_in_ids_unexpected(self):
        est = self._estimator()
        dets = [_make_detection(1), _make_detection(2), _make_detection(20), _make_detection(37)]
        registry = {"robot_1": {}, "robot_2": {}}
        state = est.update(dets, stamp=0.0, task_registry=registry,
                           expected_robot_ids={"robot_1", "robot_2"})
        assert state.diagnostics["ids_unexpected"] == ["robot_20", "robot_37"]

    def test_rogue_marker_not_carried_forward_after_registry_filter(self):
        est = self._estimator()
        registry = {"robot_1": {}, "robot_2": {}}
        allowed = {"robot_1", "robot_2"}
        # Frame 1: rogue marker_20 appears alongside known robots
        est.update(
            [_make_detection(1), _make_detection(20)],
            stamp=0.0, task_registry=registry, expected_robot_ids=allowed,
        )
        # Frame 2: only known robots, rogue absent — must not carry forward
        state = est.update(
            [_make_detection(1), _make_detection(2)],
            stamp=0.1, task_registry=registry, expected_robot_ids=allowed,
        )
        ids = {r.robot_id for r in state.robots}
        assert "robot_20" not in ids

    def test_no_filter_when_no_registry(self):
        est = self._estimator()
        dets = [_make_detection(i) for i in range(4)]
        state = est.update(dets, stamp=0.0)
        ids = {r.robot_id for r in state.robots}
        assert ids == {"robot_0", "robot_1", "robot_2", "robot_3"}

    def test_ids_unexpected_empty_when_no_registry(self):
        est = self._estimator()
        dets = [_make_detection(0), _make_detection(5)]
        state = est.update(dets, stamp=0.0)
        assert state.diagnostics["ids_unexpected"] == []


# ---------------------------------------------------------------------------
# process_frame (end-to-end pipeline; requires OpenCV)
# ---------------------------------------------------------------------------

class TestProcessFrame:
    def _frame(self) -> Frame:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        return Frame(image=img, stamp=1.0, frame_id="overhead_camera", source_id="isaac_sim")

    def test_passes_frame_id_through(self):
        pytest.importorskip("cv2")
        from swarm_perception.pipeline import process_frame

        est = StateEstimator(velocity_alpha=1.0, frame_id="UNUSED_FALLBACK")
        scene_state, annotated = process_frame(self._frame(), _identity_calibration(), est)
        # frame_id must be the incoming image frame, not the estimator fallback
        # or the calibration source_id.
        assert scene_state.frame_id == "overhead_camera"
        assert annotated.shape == (480, 640, 3)

    def test_expected_ids_derived_from_registry(self):
        pytest.importorskip("cv2")
        from swarm_perception.pipeline import process_frame

        est = StateEstimator(velocity_alpha=1.0)
        # Blank frame → no markers detected; registry names two robots, so both
        # should surface as missing in diagnostics.
        registry = {
            "robot_0": {"task": "deliver", "goal": None},
            "robot_5": {"task": "idle", "goal": None},
        }
        scene_state, _ = process_frame(
            self._frame(), _identity_calibration(), est, task_registry=registry
        )
        assert scene_state.diagnostics["markers_detected"] == 0
        assert scene_state.diagnostics["ids_missing"] == ["robot_0", "robot_5"]

    def test_explicit_expected_ids_filter_standalone_detections(self, monkeypatch):
        pytest.importorskip("cv2")
        import swarm_perception.pipeline as pipeline_mod
        from swarm_perception.pipeline import process_frame

        def fake_detect(image, dictionary_name="DICT_4X4_50", detector_params=None):
            return [1, 2, 20], [np.zeros((4, 2)) for _ in range(3)]

        def fake_build(marker_ids, marker_corners, calibration):
            return [_make_detection(marker_id=i) for i in marker_ids]

        monkeypatch.setattr(pipeline_mod, "detect_aruco_markers", fake_detect)
        monkeypatch.setattr(pipeline_mod, "build_marker_detections", fake_build)

        est = StateEstimator(velocity_alpha=1.0)
        scene_state, _ = process_frame(
            self._frame(),
            _identity_calibration(),
            est,
            expected_robot_ids={"robot_1", "robot_2"},
        )

        assert {robot.robot_id for robot in scene_state.robots} == {"robot_1", "robot_2"}
        assert scene_state.diagnostics["ids_unexpected"] == ["robot_20"]

    def test_marker_dictionary_forwarded_to_detector(self, monkeypatch):
        pytest.importorskip("cv2")
        import swarm_perception.pipeline as pipeline_mod
        from swarm_perception.pipeline import process_frame

        captured: dict[str, object] = {}

        def fake_detect(image, dictionary_name="DICT_4X4_50", detector_params=None):
            captured["dictionary_name"] = dictionary_name
            return [], []

        monkeypatch.setattr(pipeline_mod, "detect_aruco_markers", fake_detect)
        est = StateEstimator(velocity_alpha=1.0)
        process_frame(
            self._frame(), _identity_calibration(), est, marker_dictionary="DICT_5X5_100"
        )
        assert captured["dictionary_name"] == "DICT_5X5_100"


# ---------------------------------------------------------------------------
# publish_annotated_frame (ROS-free, via fakes)
# ---------------------------------------------------------------------------

class _FakeStamp:
    def __init__(self):
        self.sec = 0
        self.nanosec = 0


class _FakeHeader:
    def __init__(self):
        self.stamp = _FakeStamp()
        self.frame_id = ""


class _FakeImageMsg:
    def __init__(self):
        self.header = _FakeHeader()


class _FakeBridge:
    def __init__(self):
        self.last_image = None
        self.last_encoding = None

    def cv2_to_imgmsg(self, image, encoding):
        self.last_image = image
        self.last_encoding = encoding
        return _FakeImageMsg()


class _FakePublisher:
    def __init__(self):
        self.published = []

    def publish(self, msg):
        self.published.append(msg)


class TestPublishAnnotatedFrame:
    def test_publishes_image_bytes_with_header(self):
        from swarm_perception.perception_node import publish_annotated_frame

        bridge = _FakeBridge()
        pub = _FakePublisher()
        img = np.zeros((4, 4, 3), dtype=np.uint8)
        publish_annotated_frame(pub, bridge, img, stamp=12.5, frame_id="overhead_camera")

        assert len(pub.published) == 1
        # Real image bytes are encoded, not JSON metadata.
        assert bridge.last_image is img
        assert bridge.last_encoding == "rgb8"
        msg = pub.published[0]
        assert msg.header.frame_id == "overhead_camera"
        assert msg.header.stamp.sec == 12
        assert msg.header.stamp.nanosec == 500_000_000

    def test_none_publisher_is_noop(self):
        from swarm_perception.perception_node import publish_annotated_frame

        bridge = _FakeBridge()
        img = np.zeros((4, 4, 3), dtype=np.uint8)
        # Should not raise.
        publish_annotated_frame(None, bridge, img, stamp=1.0, frame_id="cam")
        assert bridge.last_image is None

    def test_none_bridge_is_noop(self):
        from swarm_perception.perception_node import publish_annotated_frame

        pub = _FakePublisher()
        img = np.zeros((4, 4, 3), dtype=np.uint8)
        publish_annotated_frame(pub, None, img, stamp=1.0, frame_id="cam")
        assert pub.published == []

    def test_stamp_near_second_boundary_does_not_overflow_nanosec(self):
        from swarm_perception.perception_node import publish_annotated_frame

        bridge = _FakeBridge()
        pub = _FakePublisher()
        img = np.zeros((4, 4, 3), dtype=np.uint8)
        # Previously rounded to sec=1, nanosec=1_000_000_000 (invalid).
        publish_annotated_frame(pub, bridge, img, stamp=1.9999999999, frame_id="cam")
        msg = pub.published[0]
        assert msg.header.stamp.nanosec < 1_000_000_000
        assert (msg.header.stamp.sec, msg.header.stamp.nanosec) == (2, 0)


class TestSplitStamp:
    def test_carry_normalized(self):
        from swarm_perception.perception_node import _split_stamp

        assert _split_stamp(1.9999999999) == (2, 0)

    def test_basic(self):
        from swarm_perception.perception_node import _split_stamp

        assert _split_stamp(12.5) == (12, 500_000_000)

    def test_zero(self):
        from swarm_perception.perception_node import _split_stamp

        assert _split_stamp(0.0) == (0, 0)


class TestValidateMarkerDictionary:
    def test_valid_passes(self):
        pytest.importorskip("cv2")
        from swarm_perception.detection import validate_marker_dictionary

        validate_marker_dictionary("DICT_4X4_50")  # should not raise

    def test_invalid_raises(self):
        pytest.importorskip("cv2")
        from swarm_perception.detection import validate_marker_dictionary

        with pytest.raises(ValueError):
            validate_marker_dictionary("DICT_NOT_REAL")

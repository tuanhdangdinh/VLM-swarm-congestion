"""M1 prompt-apparatus overlays: labeled metric grid and motion trails (2026-10-04).

Both are prereg-v2 rev-6 A/B conditions, never defaults. The pins here are the
flag-off byte-identity of the annotated frame (hash recorded on the clean
`aec58cc` baseline before any apparatus code existed) and, for the flag-on
frames, structural properties rather than raw hashes (anti-aliased drawing can
differ between OpenCV builds): robot footprints untouched, overlay pixels
present, labels round-trip to world cells.
"""
import hashlib
import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest
import yaml
from swarm_perception.annotation import (
    MetricGridSpec,
    TrailHistory,
    metric_grid_cell_bounds,
    metric_grid_cell_label,
    metric_grid_spec,
    render_annotated_frame,
)
from swarm_perception.calibration import load_calibration
from swarm_perception.geometry import world_to_pixel
from swarm_perception.models import CalibrationArtifact, Frame, RobotState, SceneState
from swarm_perception.pipeline import process_frame
from swarm_perception.state_estimator import StateEstimator

_PKG = Path("ros2_ws/src/swarm_perception")
_CALIBRATION = load_calibration(str(_PKG / "config" / "calibration.yaml"))

# SHA-256 of `render_annotated_frame(_image(), _scene(), _CALIBRATION)` on the
# clean baseline (aec58cc, before the apparatus existed). Flag-off must match.
_FLAG_OFF_FRAME_SHA256 = "079de2b7ce89f15f821d783661b23773ae99ff506c0c353d5207d6e7deeeebd6"


def _image() -> np.ndarray:
    return np.random.default_rng(7).integers(0, 256, size=(960, 1280, 3), dtype=np.uint8)


def _robot(robot_id, x, y, status="STOPPED", stamp=10.0, **kw) -> RobotState:
    base = dict(
        robot_id=robot_id, x=x, y=y, theta=0.0, linear_velocity=0.0, angular_velocity=0.0,
        task=None, status=status, goal=None, stamp=stamp,
    )
    base.update(kw)
    return RobotState(**base)


def _scene(stamp: float = 10.0, robots=None) -> SceneState:
    robots = robots if robots is not None else [
        _robot("robot_1", -0.4, 0.0, "MOVING", linear_velocity=0.12, task="cross", goal=(2.0, 0.0)),
        _robot("robot_2", 0.3, 0.1, theta=3.14),
        _robot("robot_3", 1.2, -1.0, "STALE", stamp=9.0, theta=1.57, goal=(-1.0, 1.5)),
    ]
    return SceneState(stamp=stamp, frame_id="overhead_camera", robots=robots, diagnostics={})


def _footprint_pixels(robot: RobotState, radius_m: float = 0.19) -> tuple[np.ndarray, np.ndarray]:
    cx, cy = world_to_pixel((robot.x, robot.y), _CALIBRATION.homography)
    ex, _ = world_to_pixel((robot.x + radius_m, robot.y), _CALIBRATION.homography)
    r = abs(ex - cx)
    ys, xs = np.mgrid[0:960, 0:1280]
    inside = (xs - cx) ** 2 + (ys - cy) ** 2 <= r**2
    return ys[inside], xs[inside]


def _history_for(scene_robots: list[RobotState]) -> TrailHistory:
    history = TrailHistory()
    for k in range(31):
        stamp = 7.0 + 0.1 * k
        moved = [
            r.model_copy(update={"x": r.x - 1.0 * (1 - k / 30), "stamp": stamp, "status": "MOVING"})
            for r in scene_robots
        ]
        history.update(SceneState(stamp=stamp, frame_id="c", robots=moved, diagnostics={}))
    return history


class TestFlagOffByteIdentity:
    def test_flag_off_frame_matches_the_pre_apparatus_baseline(self):
        out = render_annotated_frame(_image(), _scene(), _CALIBRATION)
        assert hashlib.sha256(out.tobytes()).hexdigest() == _FLAG_OFF_FRAME_SHA256

    def test_explicit_none_overlays_match_the_baseline(self):
        out = render_annotated_frame(
            _image(), _scene(), _CALIBRATION, metric_grid=None, motion_trails=None
        )
        assert hashlib.sha256(out.tobytes()).hexdigest() == _FLAG_OFF_FRAME_SHA256

    def test_process_frame_flag_off_adds_no_diagnostics_keys(self):
        frame = Frame(
            image=np.zeros((960, 1280, 3), dtype=np.uint8), stamp=1.0, frame_id="c",
            source_id="isaac_sim",
        )
        scene, _ = process_frame(frame, _CALIBRATION, StateEstimator())
        assert "annotation_overlays" not in scene.diagnostics
        assert "metric_grid_spacing_m" not in scene.diagnostics


class TestMetricGridSpec:
    def test_shipped_calibration_grid_layout(self):
        spec = metric_grid_spec(_CALIBRATION, 0.5)
        assert (spec.x0_m, spec.y0_m, spec.n_cols, spec.n_rows) == (-3.0, 2.5, 12, 10)

    def test_grid_covers_the_visible_floor(self):
        spec = metric_grid_spec(_CALIBRATION, 0.5)
        x_min, x_max, y_min, y_max = spec.visible_extent_m
        assert spec.x0_m <= x_min and spec.x0_m + spec.n_cols * spec.spacing_m >= x_max
        assert spec.y0_m >= y_max and spec.y0_m - spec.n_rows * spec.spacing_m <= y_min

    def test_rejects_non_positive_spacing(self):
        with pytest.raises(ValueError):
            metric_grid_spec(_CALIBRATION, 0.0)

    @pytest.mark.parametrize(
        ("x", "y", "label"),
        [(-2.9, 2.4, "A1"), (-0.04, -0.006, "F6"), (0.28, 0.01, "G5"), (2.7, -2.05, "L10")],
    )
    def test_cell_label_is_letter_west_to_east_number_north_to_south(self, x, y, label):
        assert metric_grid_cell_label(metric_grid_spec(_CALIBRATION, 0.5), x, y) == label

    def test_point_outside_the_grid_has_no_label(self):
        assert metric_grid_cell_label(metric_grid_spec(_CALIBRATION, 0.5), 9.0, 0.0) is None

    def test_label_round_trips_to_world_bounds(self):
        spec = metric_grid_spec(_CALIBRATION, 0.5)
        x_min, x_max, y_min, y_max = metric_grid_cell_bounds(spec, "C4")
        assert (x_min, x_max, y_min, y_max) == (-2.0, -1.5, 0.5, 1.0)
        assert metric_grid_cell_label(spec, (x_min + x_max) / 2, (y_min + y_max) / 2) == "C4"

    @pytest.mark.parametrize("label", ["", "4C", "c4", "Z1", "A0", "A11"])
    def test_malformed_or_outside_labels_raise(self, label):
        with pytest.raises(ValueError):
            metric_grid_cell_bounds(metric_grid_spec(_CALIBRATION, 0.5), label)

    def test_more_than_26_columns_use_double_letters(self):
        spec = MetricGridSpec(
            spacing_m=0.1, x0_m=0.0, y0_m=0.0, n_cols=30, n_rows=1,
            visible_extent_m=(0.0, 3.0, -0.1, 0.0),
        )
        assert metric_grid_cell_label(spec, 2.75, -0.05) == "AB1"
        assert metric_grid_cell_bounds(spec, "AB1")[0] == pytest.approx(2.7)


class TestMetricGridDrawing:
    def _grid_frame(self, image=None):
        return render_annotated_frame(
            _image() if image is None else image, _scene(), _CALIBRATION,
            metric_grid=metric_grid_spec(_CALIBRATION, 0.5),
        )

    def test_grid_changes_pixels_off_the_robots(self):
        off = render_annotated_frame(_image(), _scene(), _CALIBRATION)
        on = self._grid_frame()
        u, _ = world_to_pixel((-2.5, 0.0), _CALIBRATION.homography)
        assert np.any(on[:, u] != off[:, u])

    @pytest.mark.parametrize("index", [0, 1, 2])
    def test_grid_never_touches_a_robot_footprint(self, index):
        off = render_annotated_frame(_image(), _scene(), _CALIBRATION)
        on = self._grid_frame()
        ys, xs = _footprint_pixels(_scene().robots[index])
        assert np.array_equal(on[ys, xs], off[ys, xs])

    def test_grid_is_recessive_blend_not_opaque(self):
        black = np.zeros((960, 1280, 3), dtype=np.uint8)
        on = render_annotated_frame(
            black, _scene(robots=[]), _CALIBRATION, metric_grid=metric_grid_spec(_CALIBRATION, 0.5)
        )
        u, _ = world_to_pixel((-2.5, 0.0), _CALIBRATION.homography)
        # Lines are alpha-blended white: visible, never full white.
        assert 40 < on[480, u].max() < 255

    def test_margin_labels_stay_at_the_frame_edges(self):
        black = np.zeros((960, 1280, 3), dtype=np.uint8)
        grid_only = render_annotated_frame(
            black, _scene(robots=[]), _CALIBRATION, metric_grid=metric_grid_spec(_CALIBRATION, 0.5)
        )
        bright = grid_only.max(axis=2) > 150
        ys, xs = np.nonzero(bright)
        assert bright.any()
        assert np.all((ys < 30) | (xs < 30))

    def test_input_frame_is_untouched(self):
        image = _image()
        before = image.copy()
        self._grid_frame(image)
        assert np.array_equal(image, before)


class TestTrailHistory:
    def test_appends_only_fresh_detections(self):
        history = TrailHistory(min_step_sec=0.1)
        history.update(_scene(stamp=1.0, robots=[_robot("robot_1", 0.0, 0.0, stamp=1.0)]))
        history.update(
            _scene(stamp=1.5, robots=[_robot("robot_1", 0.5, 0.0, "STALE", stamp=1.0)])
        )
        assert [p[1] for p in history.points("robot_1")] == [0.0]

    def test_carried_forward_non_stale_pose_is_not_appended(self):
        history = TrailHistory()
        history.update(_scene(stamp=1.0, robots=[_robot("robot_1", 0.0, 0.0, stamp=1.0)]))
        history.update(_scene(stamp=1.5, robots=[_robot("robot_1", 0.0, 0.0, stamp=1.0)]))
        assert len(history.points("robot_1")) == 1

    def test_respects_min_step(self):
        history = TrailHistory(min_step_sec=0.2)
        for k, stamp in enumerate((1.0, 1.1, 1.2, 1.3)):
            robots = [_robot("robot_1", k * 0.1, 0.0, stamp=stamp)]
            history.update(_scene(stamp=stamp, robots=robots))
        assert [p[0] for p in history.points("robot_1")] == [1.0, 1.2]

    def test_window_drops_old_positions(self):
        history = TrailHistory(window_sec=1.0, min_step_sec=0.1)
        for k in range(30):
            stamp = 0.1 * k
            history.update(_scene(stamp=stamp, robots=[_robot("robot_1", 0.0, 0.0, stamp=stamp)]))
        points = history.points("robot_1")
        assert points[-1][0] - points[0][0] <= 1.0 + 1e-9

    def test_clock_reset_clears_history(self):
        history = TrailHistory()
        history.update(_scene(stamp=5.0, robots=[_robot("robot_1", 0.0, 0.0, stamp=5.0)]))
        reset = SceneState(
            stamp=0.5, frame_id="c", robots=[_robot("robot_1", 1.0, 0.0, stamp=0.5)],
            diagnostics={"clock_reset": True},
        )
        history.update(reset)
        assert [p[1] for p in history.points("robot_1")] == [1.0]

    def test_dropped_frame_is_ignored(self):
        history = TrailHistory()
        history.update(_scene(stamp=5.0, robots=[_robot("robot_1", 0.0, 0.0, stamp=5.0)]))
        dropped = SceneState(
            stamp=4.0, frame_id="c", robots=[], diagnostics={"dropped_frame": True}
        )
        history.update(dropped)
        assert len(history.points("robot_1")) == 1

    def test_robot_leaving_the_scene_is_forgotten(self):
        history = TrailHistory()
        history.update(_scene(stamp=1.0, robots=[_robot("robot_1", 0.0, 0.0, stamp=1.0)]))
        history.update(_scene(stamp=1.2, robots=[]))
        assert history.points("robot_1") == []

    def test_rejects_bad_bounds(self):
        with pytest.raises(ValueError):
            TrailHistory(max_points=1)


class TestTrailDrawing:
    def test_trail_draws_behind_a_moving_robot_in_its_status_colour(self):
        robots = [_robot("robot_1", 0.5, 0.0)]
        scene = _scene(stamp=10.0, robots=robots)
        black = np.zeros((960, 1280, 3), dtype=np.uint8)
        on = render_annotated_frame(black, scene, _CALIBRATION, motion_trails=_history_for(robots))
        # Halfway along the trail (x = 0.0 m), the STOPPED colour (red) dominates.
        u, v = world_to_pixel((0.0, 0.0), _CALIBRATION.homography)
        pixel = on[v - 1 : v + 2, u].max(axis=0)
        assert pixel[0] > 30 and pixel[1] == 0 and pixel[2] == 0

    def test_trail_fades_older_segments_fainter(self):
        robots = [_robot("robot_1", 0.5, 0.0)]
        black = np.zeros((960, 1280, 3), dtype=np.uint8)
        on = render_annotated_frame(
            black, _scene(robots=robots), _CALIBRATION, motion_trails=_history_for(robots)
        )
        old_u, v = world_to_pixel((-0.4, 0.0), _CALIBRATION.homography)
        new_u, _ = world_to_pixel((0.2, 0.0), _CALIBRATION.homography)
        assert on[v - 1 : v + 2, old_u, 0].max() < on[v - 1 : v + 2, new_u, 0].max()

    def test_trail_never_covers_any_robot_footprint(self):
        robots = [_robot("robot_1", 0.5, 0.0), _robot("robot_2", -0.1, 0.0)]
        history = _history_for(robots[:1])
        off = render_annotated_frame(_image(), _scene(robots=robots), _CALIBRATION)
        on = render_annotated_frame(
            _image(), _scene(robots=robots), _CALIBRATION, motion_trails=history
        )
        for robot in robots:
            ys, xs = _footprint_pixels(robot)
            assert np.array_equal(on[ys, xs], off[ys, xs])

    def test_stationary_history_draws_nothing(self):
        robots = [_robot("robot_1", 0.5, 0.0)]
        history = TrailHistory()
        for k in range(10):
            history.update(_scene(stamp=1.0 + 0.1 * k, robots=[
                _robot("robot_1", 0.5, 0.0, stamp=1.0 + 0.1 * k)
            ]))
        off = render_annotated_frame(_image(), _scene(robots=robots), _CALIBRATION)
        on = render_annotated_frame(
            _image(), _scene(robots=robots), _CALIBRATION, motion_trails=history
        )
        assert np.array_equal(on, off)


class TestProcessFrameOverlayDiagnostics:
    def _frame(self, stamp=1.0):
        return Frame(
            image=np.zeros((960, 1280, 3), dtype=np.uint8), stamp=stamp, frame_id="c",
            source_id="isaac_sim",
        )

    def test_grid_on_reports_overlay_and_spacing(self):
        scene, _ = process_frame(
            self._frame(), _CALIBRATION, StateEstimator(),
            metric_grid=metric_grid_spec(_CALIBRATION, 0.5),
        )
        assert scene.diagnostics["annotation_overlays"] == ["metric_grid"]
        assert scene.diagnostics["metric_grid_spacing_m"] == 0.5

    def test_both_on_reports_both(self):
        scene, _ = process_frame(
            self._frame(), _CALIBRATION, StateEstimator(),
            metric_grid=metric_grid_spec(_CALIBRATION, 0.5), motion_trails=TrailHistory(),
        )
        assert scene.diagnostics["annotation_overlays"] == ["metric_grid", "motion_trails"]

    def test_trails_only_has_no_spacing_key(self):
        scene, _ = process_frame(
            self._frame(), _CALIBRATION, StateEstimator(), motion_trails=TrailHistory()
        )
        assert scene.diagnostics["annotation_overlays"] == ["motion_trails"]
        assert "metric_grid_spacing_m" not in scene.diagnostics

    def test_annotated_frame_stays_rgb_uint8(self):
        _, annotated = process_frame(
            self._frame(), _CALIBRATION, StateEstimator(),
            metric_grid=metric_grid_spec(_CALIBRATION, 0.5),
        )
        assert annotated.dtype == np.uint8 and annotated.shape == (960, 1280, 3)


class TestShippedAnnotationConfig:
    def test_every_overlay_ships_off(self):
        config = yaml.safe_load((_PKG / "config" / "annotation.yaml").read_text())["annotation"]
        assert config["metric_grid"] is False
        assert config["motion_trails"] is False
        assert config["metric_grid_spacing_m"] == 0.5

    def test_launch_loader_maps_the_section_to_node_params(self, tmp_path):
        launch_path = _PKG / "launch" / "perception.launch.py"
        pytest.importorskip("launch_ros")
        spec = importlib.util.spec_from_file_location("perception_launch", launch_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cfg = tmp_path / "annotation.yaml"
        cfg.write_text("annotation:\n  metric_grid: true\n  bogus: 1\n")
        assert module._load_annotation_params(str(cfg)) == {"annotation.metric_grid": True}
        assert module._load_annotation_params(str(tmp_path / "missing.yaml")) == {}


def test_calibration_fixture_is_the_shipped_overhead_camera():
    assert isinstance(_CALIBRATION, CalibrationArtifact)
    assert _CALIBRATION.image_size == (1280, 960)
    assert math.isclose(_CALIBRATION.homography[0, 0], 0.004358335072757633)

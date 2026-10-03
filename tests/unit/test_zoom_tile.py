"""Zoomed congestion-crop tile (prompt-apparatus second image, 2026-10-04)."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from swarm_orchestrator.zoom_tile import compute_zoom_crop, write_zoom_tile, zoom_tile_path
from swarm_perception.calibration import load_calibration
from swarm_perception.geometry import world_to_pixel

_CALIBRATION = load_calibration("ros2_ws/src/swarm_perception/config/calibration.yaml")
_SIZE = (1280, 960)
_HEAD_ON = {"robot_1": (-0.05, 0.0), "robot_2": (0.28, 0.01)}


def _crop(positions, margin=0.6, frame_size=_SIZE):
    return compute_zoom_crop(
        list(positions.values()), margin, _CALIBRATION.homography, _SIZE, frame_size
    )


class TestCropBounds:
    def test_crop_contains_every_robot_plus_the_margin(self):
        (x0, y0, x1, y1), bounds = _crop(_HEAD_ON)
        assert bounds == pytest.approx((-0.65, 0.88, -0.6, 0.61))
        for corner in ((bounds[0], bounds[2]), (bounds[1], bounds[3])):
            u, v = world_to_pixel(corner, _CALIBRATION.homography)
            assert x0 <= u <= x1 and y0 <= v <= y1

    def test_crop_keeps_the_frame_aspect_ratio(self):
        (x0, y0, x1, y1), _ = _crop(_HEAD_ON)
        assert (x1 - x0) / (y1 - y0) == pytest.approx(4 / 3, abs=0.01)

    def test_crop_is_clamped_inside_the_frame(self):
        (x0, y0, x1, y1), _ = _crop({"robot_1": (2.7, 2.0)})
        assert 0 <= x0 < x1 <= 1280 and 0 <= y0 < y1 <= 960
        assert x1 == 1280 and y0 == 0

    def test_far_apart_robots_cap_at_the_full_frame(self):
        crop, _ = _crop({"a": (-2.7, 0.0), "b": (2.7, 0.0)})
        assert crop == (0, 0, 1280, 960)

    def test_crop_scales_with_a_downscaled_frame(self):
        full, _ = _crop(_HEAD_ON)
        half, _ = _crop(_HEAD_ON, frame_size=(640, 480))
        assert half[0] == pytest.approx(full[0] / 2, abs=1)
        assert half[2] == pytest.approx(full[2] / 2, abs=1)

    def test_no_positions_raises(self):
        with pytest.raises(ValueError):
            compute_zoom_crop([], 0.6, _CALIBRATION.homography, _SIZE, _SIZE)


class TestWriteTile:
    def _frame(self) -> np.ndarray:
        frame = np.zeros((960, 1280, 3), dtype=np.uint8)
        frame[..., 0] = 200  # pure red in RGB
        return frame

    def test_writes_an_rgb_correct_png_of_the_registered_width(self, tmp_path):
        record = write_zoom_tile(self._frame(), "r1", tmp_path, _HEAD_ON, _CALIBRATION, 0.6, 640)
        assert record.attached and record.path == str(zoom_tile_path(tmp_path, "r1"))
        bgr = cv2.imread(record.path)
        assert bgr.shape == (480, 640, 3)
        # imread is BGR: red must land in channel 2, proving the RGB->BGR write.
        assert bgr[240, 320, 2] == 200 and bgr[240, 320, 0] == 0
        assert record.output_size == (640, 480)
        assert record.source_size == (1280, 960)
        assert record.robot_ids == ("robot_1", "robot_2")

    def test_crop_content_is_the_annotated_frame_region(self, tmp_path):
        frame = np.zeros((960, 1280, 3), dtype=np.uint8)
        u, v = world_to_pixel(_HEAD_ON["robot_1"], _CALIBRATION.homography)
        frame[v - 3 : v + 4, u - 3 : u + 4] = (0, 255, 0)
        record = write_zoom_tile(frame, "r1", tmp_path, _HEAD_ON, _CALIBRATION, 0.6, 640)
        x0, y0, x1, y1 = record.crop_px
        bgr = cv2.imread(record.path)
        tu = round((u - x0) * 640 / (x1 - x0))
        tv = round((v - y0) * 480 / (y1 - y0))
        assert bgr[tv, tu, 1] > 150

    def test_without_calibration_no_tile(self, tmp_path):
        record = write_zoom_tile(self._frame(), "r1", tmp_path, _HEAD_ON, None, 0.6, 640)
        assert not record.attached and record.reason == "calibration_unavailable"
        assert not zoom_tile_path(tmp_path, "r1").exists()

    def test_without_robots_no_tile(self, tmp_path):
        record = write_zoom_tile(self._frame(), "r1", tmp_path, {}, _CALIBRATION, 0.6, 640)
        assert not record.attached and record.reason == "no_robots"

    def test_without_frame_no_tile(self, tmp_path):
        record = write_zoom_tile(None, "r1", tmp_path, _HEAD_ON, _CALIBRATION, 0.6, 640)
        assert not record.attached and record.reason == "no_frame"

    def test_non_uniform_resize_is_refused(self, tmp_path):
        frame = np.zeros((960, 1000, 3), dtype=np.uint8)
        record = write_zoom_tile(frame, "r1", tmp_path, _HEAD_ON, _CALIBRATION, 0.6, 640)
        assert not record.attached and record.reason.startswith("frame_size_mismatch")

    def test_unwritable_destination_is_recorded_not_raised(self, tmp_path):
        blocker = tmp_path / "file"
        blocker.write_text("x")
        record = write_zoom_tile(
            self._frame(), "r1", Path(blocker) / "sub", _HEAD_ON, _CALIBRATION, 0.6, 640
        )
        assert not record.attached and record.reason

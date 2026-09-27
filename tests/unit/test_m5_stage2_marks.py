"""Stage-2 set-of-mark rendering: world->pixel placement, drawing, degradation."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml
from swarm_orchestrator.stage2_marks import (
    CandidateMarker,
    project_world_to_image,
    stage2_image_path,
)
from swarm_perception.models import CalibrationArtifact

# Pixel -> world, M1's direction: x = 0.01 (u - 320), y = -0.01 (v - 240), for a
# 640 x 480 calibration frame. World (1.0, 0.5) is therefore pixel (420, 190).
_H = np.array([[0.01, 0.0, -3.2], [0.0, -0.01, 2.4], [0.0, 0.0, 1.0]])
_LETTERS = [("A", 1.0, 0.5), ("B", -1.0, -0.5)]


def _calibration(image_size=(640, 480)) -> CalibrationArtifact:
    return CalibrationArtifact(
        intrinsics=np.eye(3),
        distortion=np.zeros(5),
        homography=_H,
        image_size=image_size,
        source_id="synthetic",
        created_at=0.0,
    )


def _write_frame(path: Path, width: int = 640, height: int = 480) -> Path:
    # Mid-grey so both the white disc and the black outline register as changes.
    cv2.imwrite(str(path), np.full((height, width, 3), 128, dtype=np.uint8))
    return path


class TestProjection:
    def test_projects_through_the_inverse_homography(self):
        [(u, v)] = project_world_to_image([(1.0, 0.5)], _H, (640, 480), (640, 480))
        assert (u, v) == pytest.approx((420.0, 190.0))

    def test_scales_to_a_downscaled_frame(self):
        [(u, v)] = project_world_to_image([(1.0, 0.5)], _H, (640, 480), (320, 240))
        assert (u, v) == pytest.approx((210.0, 95.0))


class TestRender:
    def test_writes_the_stage2_image_beside_the_frame(self, tmp_path):
        source = _write_frame(tmp_path / "req-1.png")
        marks = CandidateMarker(_calibration(), "cal.yaml").render("req-1", str(source), _LETTERS)
        assert marks.marks_drawn is True
        assert marks.reason is None
        assert marks.image_path == str(tmp_path / "req-1_stage2.png")
        assert Path(marks.image_path).is_file()
        assert marks.source_image_path == str(source)
        assert marks.calibration_path == "cal.yaml"
        assert [(m.letter, m.u, m.v) for m in marks.marks] == [
            ("A", 420, 190),
            ("B", 220, 290),
        ]

    def test_source_frame_is_left_untouched(self, tmp_path):
        source = _write_frame(tmp_path / "req-1.png")
        before = source.read_bytes()
        CandidateMarker(_calibration(), "cal.yaml").render("req-1", str(source), _LETTERS)
        assert source.read_bytes() == before

    def test_drawing_stays_at_the_candidate_positions(self, tmp_path):
        source = _write_frame(tmp_path / "req-1.png")
        marks = CandidateMarker(_calibration(), "cal.yaml").render("req-1", str(source), _LETTERS)
        drawn = cv2.imread(marks.image_path)
        changed = np.argwhere(np.any(drawn != 128, axis=2))  # rows of (v, u)
        centres = np.array([(m.v, m.u) for m in marks.marks])
        # Every changed pixel lies within the footprint ring (0.15 m = 15 px
        # here) plus its anti-aliased stroke of some candidate; nothing is
        # drawn elsewhere.
        distances = np.linalg.norm(changed[:, None, :] - centres[None, :, :], axis=2)
        assert distances.min(axis=1).max() <= 15 + 4
        for v, u in centres:
            near = np.linalg.norm(changed - np.array([v, u]), axis=1) <= 4
            assert near.any(), f"nothing drawn at candidate ({u}, {v})"

    def test_badge_is_high_contrast_white_and_black(self, tmp_path):
        source = _write_frame(tmp_path / "req-1.png")
        marks = CandidateMarker(_calibration(), "cal.yaml").render("req-1", str(source), _LETTERS)
        drawn = cv2.imread(marks.image_path)
        u, v = marks.marks[0].u, marks.marks[0].v
        badge = drawn[v - 8 : v + 9, u - 8 : u + 9]
        assert (badge == 255).all(axis=2).any()
        assert (badge == 0).all(axis=2).any()

    def test_downscaled_frame_is_marked_at_scaled_positions(self, tmp_path):
        source = _write_frame(tmp_path / "req-1.png", 320, 240)
        marks = CandidateMarker(_calibration(), "cal.yaml").render("req-1", str(source), _LETTERS)
        assert marks.marks_drawn is True
        assert marks.scale == pytest.approx((0.5, 0.5))
        assert (marks.marks[0].u, marks.marks[0].v) == (210, 95)

    def test_stage2_image_path_sits_beside_the_frame(self):
        assert stage2_image_path("/logs/frames/r9.png", "r9") == "/logs/frames/r9_stage2.png"


class TestDegradation:
    def _assert_unmarked(self, marks, source: str, reason_prefix: str) -> None:
        assert marks.marks_drawn is False
        assert marks.image_path == source
        assert marks.reason is not None and marks.reason.startswith(reason_prefix)

    def test_no_calibration_falls_back_to_the_unmarked_frame(self, tmp_path):
        source = str(_write_frame(tmp_path / "req-1.png"))
        marker = CandidateMarker.unavailable("calibration_unavailable: not found", "cal.yaml")
        marks = marker.render("req-1", source, _LETTERS)
        self._assert_unmarked(marks, source, "calibration_unavailable")
        assert not (tmp_path / "req-1_stage2.png").exists()

    def test_missing_frame_falls_back(self, tmp_path):
        source = str(tmp_path / "absent.png")
        marks = CandidateMarker(_calibration(), "cal.yaml").render("req-1", source, _LETTERS)
        self._assert_unmarked(marks, source, "frame_unreadable")

    def test_frame_aspect_mismatch_falls_back(self, tmp_path):
        source = str(_write_frame(tmp_path / "req-1.png", 640, 360))
        marks = CandidateMarker(_calibration(), "cal.yaml").render("req-1", source, _LETTERS)
        self._assert_unmarked(marks, source, "frame_size_mismatch")

    def test_candidate_outside_the_frame_falls_back(self, tmp_path):
        source = str(_write_frame(tmp_path / "req-1.png"))
        marks = CandidateMarker(_calibration(), "cal.yaml").render(
            "req-1", source, [("A", 1.0, 0.5), ("B", 9.0, 0.0)]
        )
        self._assert_unmarked(marks, source, "candidate_out_of_frame")
        assert [m.letter for m in marks.marks] == ["A", "B"]

    def test_unexpected_error_is_recorded_not_raised(self, tmp_path, monkeypatch):
        source = str(_write_frame(tmp_path / "req-1.png"))

        def _boom(*args, **kwargs):
            raise RuntimeError("disk full")

        monkeypatch.setattr(cv2, "imwrite", _boom)
        marks = CandidateMarker(_calibration(), "cal.yaml").render("req-1", source, _LETTERS)
        self._assert_unmarked(marks, source, "render_error")
        assert "disk full" in marks.reason


class TestFromPath:
    def test_loads_a_valid_calibration(self, tmp_path):
        path = tmp_path / "calibration.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "intrinsics": np.eye(3).tolist(),
                    "distortion": [0.0] * 5,
                    "homography": _H.tolist(),
                    "image_size": [640, 480],
                    "source_id": "synthetic",
                    "created_at": 0.0,
                }
            )
        )
        marker = CandidateMarker.from_path(str(path))
        assert marker.available
        assert marker.unavailable_reason is None

    def test_missing_file_is_unavailable_not_raised(self, tmp_path):
        marker = CandidateMarker.from_path(str(tmp_path / "nope.yaml"))
        assert not marker.available
        assert marker.unavailable_reason.startswith("calibration_unavailable")

    def test_repo_calibration_loads(self):
        marker = CandidateMarker.from_path("ros2_ws/src/swarm_perception/config/calibration.yaml")
        assert marker.available

"""Manifest load/save and frame re-materialization (fails loudly, never pads)."""
import pytest

from reasoning.vlm.capability_probes.manifest_io import (
    load_manifest,
    materialize_frame,
    save_manifest,
    sha256_file,
)
from reasoning.vlm.capability_probes.models import ProbeItem, ProbeManifest


def _item(frame_relpath: str, frame_sha256: str) -> ProbeItem:
    return ProbeItem(
        item_id="robot_count_000",
        probe_type="robot_count",
        run_id="run_a/ep_1",
        scenario="head_on",
        request_id="req1",
        frame_relpath=frame_relpath,
        frame_sha256=frame_sha256,
        image_width=10,
        image_height=10,
        sim_time_sec=1.0,
        reference_robot_id=None,
        question="How many robots are visible in the image?",
        options=["1", "2", "3", "4", "5"],
        correct_answer="2",
        image_choices=False,
        seed=1,
        m1_gt_max_disagreement_m=0.0,
    )


class TestManifestRoundTrip:
    def test_save_then_load_is_lossless(self, tmp_path):
        manifest = ProbeManifest(seed=99, items=[_item("run_a/ep_1/frames/req1.png", "a" * 64)])
        path = tmp_path / "manifest.json"
        save_manifest(manifest, path)
        restored = load_manifest(path)
        assert restored == manifest


class TestMaterializeFrame:
    def test_missing_frame_raises_file_not_found(self, tmp_path):
        item = _item("run_a/ep_1/frames/req1.png", "a" * 64)
        with pytest.raises(FileNotFoundError, match="frame not found"):
            materialize_frame(item, tmp_path)

    def test_hash_mismatch_raises_value_error(self, tmp_path):
        frame_dir = tmp_path / "run_a" / "ep_1" / "frames"
        frame_dir.mkdir(parents=True)
        frame_path = frame_dir / "req1.png"
        frame_path.write_bytes(b"not the frame the manifest was frozen with")
        item = _item("run_a/ep_1/frames/req1.png", "a" * 64)
        with pytest.raises(ValueError, match="hash"):
            materialize_frame(item, tmp_path)

    def test_matching_hash_returns_the_path(self, tmp_path):
        frame_dir = tmp_path / "run_a" / "ep_1" / "frames"
        frame_dir.mkdir(parents=True)
        frame_path = frame_dir / "req1.png"
        frame_path.write_bytes(b"frame bytes")
        item = _item("run_a/ep_1/frames/req1.png", sha256_file(frame_path))
        resolved = materialize_frame(item, tmp_path)
        assert resolved == frame_path

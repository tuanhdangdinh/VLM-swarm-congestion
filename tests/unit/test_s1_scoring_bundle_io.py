"""Unit tests for the A33(0) bundle reader (synthetic bundles, offline)."""

import shutil
from pathlib import Path

import pytest

from benchmarks.s1_scoring import NotAnEpisodeError, read_bundle, truncate
from benchmarks.s1_scoring.bundle_io import censor_reason

DATA = Path(__file__).parent / "data" / "s1_scoring"


def test_read_bundle_anchors_clock_at_robot_1_release_when_scene_log_empty():
    records = read_bundle(DATA / "complete")
    assert records.gt_offset_s == 0.0
    assert records.t0_m1 == 1.0
    assert records.t_end_rel == pytest.approx(24.0)


def test_read_bundle_sorts_artifacts_by_scene_stamp_not_file_name():
    records = read_bundle(DATA / "detection")
    stamps = [a["scene"]["stamp"] for a in records.artifacts]
    assert stamps == sorted(stamps)


def test_censor_reason_maps_run_manifest_states():
    assert censor_reason({"completed": True}) == "horizon"
    assert censor_reason({"aborted": True, "abort_reason": "stop_flag"}) == "stop_flag"
    assert censor_reason({"aborted": True, "abort_reason": "crash"}) == "aborted_other"
    assert censor_reason({}) == "aborted_other"


def test_truncate_relabels_censoring_when_tau_inside_observation():
    cut = truncate(read_bundle(DATA / "complete"), 10.0)
    assert cut.t_end_rel == 10.0
    assert cut.censor_reason == "common_window"
    assert all(s.t <= cut.t0_gt + 10.0 for s in cut.gt)


def test_truncate_returns_records_unchanged_when_tau_beyond_end():
    records = read_bundle(DATA / "censored")
    assert truncate(records, 100.0) is records


def test_read_bundle_refuses_bring_up_abort_without_task_stream(tmp_path):
    # A bring-up abort's attempt directory: GT and a stop-flag manifest, no tasks.
    shutil.copytree(DATA / "censored" / "gt", tmp_path / "gt")
    (tmp_path / "decisions").mkdir()
    with pytest.raises(NotAnEpisodeError):
        read_bundle(tmp_path)


def test_read_bundle_refuses_stream_without_robot_1_release(tmp_path):
    bundle = tmp_path / "b"
    shutil.copytree(DATA / "complete", bundle)
    tasks = bundle / "decisions" / "tasks_synthetic.jsonl"
    kept = [line for line in tasks.read_text().splitlines()
            if not ('"released"' in line and '"robot_1"' in line)]
    tasks.write_text("\n".join(kept) + "\n")
    with pytest.raises(NotAnEpisodeError):
        read_bundle(bundle)

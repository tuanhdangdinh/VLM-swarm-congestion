"""Item building for the v4 VLM bench on the synthetic mini-bundle."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image

from benchmarks.s1_scoring.bundle_io import NotAnEpisodeError
from benchmarks.vlm_bench.items import (
    build_bundle_items,
    est_usd_per_call,
    read_items,
    task_stream_state,
    write_items,
)
from tests.unit.vlm_bench_fixtures import BUNDLE, synthetic_items


def _copy(tmp_path: Path) -> Path:
    dest = tmp_path / BUNDLE.name
    shutil.copytree(BUNDLE, dest)
    return dest


def test_build_items_one_per_artifact_without_frames():
    items = synthetic_items()
    assert sorted(items) == ["aaaa0001", "aaaa0002", "aaaa0003", "aaaa0004", "aaaa0005"]
    assert all(item.frame_path is None for item in items.values())


def test_build_items_attaches_frame_when_dumped(tmp_path):
    bundle = _copy(tmp_path)
    (bundle / "m5_frames").mkdir()
    Image.new("RGB", (8, 8)).save(bundle / "m5_frames" / "aaaa0002.png")
    items = synthetic_items(bundle)
    assert items["aaaa0002"].frame_path == str(bundle / "m5_frames" / "aaaa0002.png")
    assert items["aaaa0003"].frame_path is None


def test_build_items_window_clusters_two_after_onset():
    items = synthetic_items()
    involved = {c.involved for c in items["aaaa0002"].gt.clusters}
    assert involved == {("robot_1", "robot_5"), ("robot_3", "robot_4")}


def test_build_items_no_cluster_before_onset():
    assert synthetic_items()["aaaa0001"].gt.clusters == ()


def test_build_items_records_grounding_params_match_file():
    item = synthetic_items()["aaaa0002"]
    assert item.grounding.params_path == "config/grounding/s1b_dynamic_shield_escort.yaml"
    assert item.grounding.params_match_file is True


def test_build_items_attaches_mc_by_seed():
    item = synthetic_items()["aaaa0002"]
    assert item.mc is not None
    assert item.mc.yielder == "robot_4"


def test_build_items_backend_failed_keeps_null_decision():
    item = synthetic_items()["aaaa0004"]
    assert item.recorded.decision is None


def test_build_items_empty_for_bundle_without_artifacts(tmp_path):
    bundle = _copy(tmp_path)
    for path in (bundle / "decisions").glob("aaaa*.json"):
        path.unlink()
    assert build_bundle_items(bundle) == []


def test_build_items_raises_when_not_an_episode(tmp_path):
    bundle = _copy(tmp_path)
    for path in (bundle / "decisions").glob("tasks_*.jsonl"):
        path.unlink()
    with pytest.raises(NotAnEpisodeError):
        build_bundle_items(bundle)


def test_items_roundtrip_jsonl(tmp_path):
    items = list(synthetic_items().values())
    write_items(items, tmp_path / "items.jsonl")
    assert read_items(tmp_path / "items.jsonl") == items


def test_task_stream_state_held_before_release():
    stream = {"nodes": {"E": [1.0, 0.0]}, "sequences": {"robot_1": ["E"]}, "dwell_sim_sec": 5.0}
    events = [
        {"event": "released", "robot_id": "robot_1", "sim_t": 10.0},
        {"event": "issued", "robot_id": "robot_1", "sim_t": 10.0, "task_index": 0,
         "node": "E", "goal": [1.0, 0.0]},
    ]
    goals, intents, held = task_stream_state(events, stream, 5.0)
    assert (goals, intents, held) == ({}, {}, {"robot_1"})


def test_task_stream_state_dwell_remaining_after_arrival():
    stream = {
        "nodes": {"E": [1.0, 0.0], "N": [0.0, 1.0]},
        "sequences": {"robot_1": ["E", "N"]},
        "dwell_sim_sec": 5.0,
    }
    events = [
        {"event": "released", "robot_id": "robot_1", "sim_t": 10.0},
        {"event": "issued", "robot_id": "robot_1", "sim_t": 10.0, "task_index": 0,
         "node": "E", "goal": [1.0, 0.0]},
        {"event": "arrived", "robot_id": "robot_1", "sim_t": 20.0, "task_index": 0},
    ]
    _, intents, _ = task_stream_state(events, stream, 22.0)
    assert intents["robot_1"].next_goal == (0.0, 1.0)
    assert intents["robot_1"].dwell_sec == pytest.approx(3.0)


def test_est_usd_per_call_none_without_cost_log(tmp_path):
    assert est_usd_per_call(tmp_path) is None


def test_est_usd_per_call_from_last_cost_line():
    assert est_usd_per_call(BUNDLE) == pytest.approx(0.01)

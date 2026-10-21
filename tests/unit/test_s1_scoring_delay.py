"""Unit tests for A33(4) per-segment delay_vs_free_flow (synthetic bundles)."""

import hashlib
import json
import math
from pathlib import Path

import pytest

from benchmarks.s1_scoring import (
    S1B_FREE_FLOW_TABLE,
    default_segment_table,
    load_segment_table,
    read_bundle,
    score_delay,
    summarize_delay,
)

DATA = Path(__file__).parent / "data" / "s1_scoring"
TABLE = load_segment_table(DATA / "free_flow_segments.json")


def test_delay_is_travel_minus_free_flow_when_segment_arrives():
    result = score_delay(read_bundle(DATA / "complete"), TABLE, "synthetic")
    seg = next(s for s in result.segments if s.segment == "A->B")
    # Departure at the first 0.2 m/s sample (rel 1.0); arrival within 0.35 m of B (rel 9.4).
    assert (seg.departure_s, seg.arrival_s) == pytest.approx((1.0, 9.4))
    assert seg.delay_s == pytest.approx(4.4)
    assert seg.reason == "scored"


def test_delay_is_lower_bound_at_t_end_when_segment_censored():
    result = score_delay(read_bundle(DATA / "censored"), TABLE, "synthetic")
    seg = next(s for s in result.segments if s.segment == "A->B")
    assert seg.reason == "censored"
    assert seg.delay_s is None
    assert seg.delay_lower_bound_s == pytest.approx(7.0 - 1.0 - 4.0)
    assert result.n_censored == 2


def test_delay_is_vacuous_without_table():
    result = score_delay(read_bundle(DATA / "complete"), None)
    assert result.vacuous
    assert {s.reason for s in result.segments} == {"no_table"}


def test_delay_is_no_baseline_when_scene_key_missing():
    result = score_delay(read_bundle(DATA / "complete"), TABLE, "mapd_5_s1b")
    assert {s.reason for s in result.segments} == {"no_baseline"}
    assert result.mean_delay_lower_bound_s is None


def test_load_segment_table_raises_without_table_id(tmp_path):
    path = tmp_path / "t.json"
    path.write_text('{"scenes": {}}')
    with pytest.raises(ValueError):
        load_segment_table(path)


def test_summarize_delay_pools_segments_across_episodes():
    results = [score_delay(read_bundle(DATA / name), TABLE, "synthetic")
               for name in ("complete", "censored")]
    summary = summarize_delay(results)
    assert (summary.n_scored, summary.n_censored) == (2, 2)
    assert summary.mean_delay_arrived_s == pytest.approx(4.4)
    assert summary.mean_delay_lower_bound_s == pytest.approx((4.4 + 4.4 + 2.0 + 1.0) / 4)


S1B_NODES = {"E": (2.3, 0.0), "N": (-0.25, 1.35), "S": (-0.25, -1.35),
             "Wm": (-2.3, -1.35), "Wp": (-2.3, 1.35)}
S1B_LEGS = sorted(f"{a}->{b}" for a in S1B_NODES for b in S1B_NODES
                  if a != b and {a, b} != {"Wp", "Wm"})


def _s1b_bundle(root: Path) -> Path:
    """One robot per S1b leg, each driving its leg straight at 0.2 m/s from sim 1.0."""
    robots = {f"robot_{i + 1}": leg.split("->") for i, leg in enumerate(S1B_LEGS)}
    (root / "decisions").mkdir(parents=True)
    (root / "gt").mkdir()
    (root / "m5_scene.jsonl").write_text("")
    events = [{"event": "stream_start", "seed": 7, "tasks_total": len(robots),
               "nodes": {k: list(v) for k, v in S1B_NODES.items()},
               "start_nodes": {r: a for r, (a, _b) in robots.items()},
               "sequences": {r: [b] for r, (_a, b) in robots.items()},
               "horizon_sim_sec": 600.0}]
    events += [{"event": "released", "robot_id": r, "sim_t": 1.0, "task_index": None,
                "node": None} for r in robots]
    events += [{"event": "issued", "robot_id": r, "sim_t": 1.0, "task_index": 0, "node": b}
               for r, (_a, b) in robots.items()]
    rows = []
    for step in range(301):
        t = round(step * 0.2, 1)
        poses = {}
        for r, (a, b) in robots.items():
            (ax, ay), (bx, by) = S1B_NODES[a], S1B_NODES[b]
            length = math.hypot(bx - ax, by - ay)
            s = min(max(t - 1.0, 0.0) * 0.2, length)
            moving = 1.0 <= t and s < length
            poses[r] = {"x": ax + (bx - ax) * s / length, "y": ay + (by - ay) * s / length,
                        "speed_mps": 0.2 if moving else 0.0, "theta": 0.0}
        rows.append({"sim_time_sec": t, "robots": poses})
    (root / "gt" / "ground_truth.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (root / "gt" / "run_manifest.json").write_text('{"completed": true, "aborted": false}')
    (root / "decisions" / "tasks_s1b.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in events))
    return root


def test_frozen_s1b_table_md5_is_pinned():
    data = S1B_FREE_FLOW_TABLE.read_bytes()
    assert hashlib.md5(data).hexdigest() == "b4002d7697f4d8f27c31792a9b269162"


def test_frozen_s1b_table_holds_exactly_the_18_s1b_legs():
    table = default_segment_table("mapd_5_s1b")
    assert table is not None
    assert table.table_id == "free_flow_s1b_2026-10-10"
    assert sorted(table.scenes["mapd_5_s1b"]) == S1B_LEGS
    assert len(S1B_LEGS) == 18


def test_default_table_is_none_for_non_mapd_scene_key():
    assert default_segment_table("synthetic") is None


def test_delay_scores_all_18_s1b_segments_with_default_table(tmp_path):
    result = score_delay(read_bundle(_s1b_bundle(tmp_path / "s1b")))
    frozen = default_segment_table("mapd_5_s1b")
    assert result.table_id == "free_flow_s1b_2026-10-10"
    assert sorted(s.segment for s in result.segments) == S1B_LEGS
    assert {s.reason for s in result.segments} == {"scored"}
    assert result.n_scored == 18
    for seg in result.segments:
        ff = frozen.lookup("mapd_5_s1b", seg.segment)
        assert seg.free_flow_s == ff
        assert seg.delay_s == pytest.approx(seg.arrival_s - seg.departure_s - ff)


def test_explicit_none_table_stays_no_table_for_s1b_scene(tmp_path):
    result = score_delay(read_bundle(_s1b_bundle(tmp_path / "s1b")), None, "mapd_5_s1b")
    assert {s.reason for s in result.segments} == {"no_table"}

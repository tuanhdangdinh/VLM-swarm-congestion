"""Pure parts of the v4 per-cluster live shadow: compute, artifact attach, trigger trace."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from swarm_orchestrator.per_cluster_shadow import (
    attach_shadow_block,
    compute_per_cluster_shadow,
    format_per_cluster_log,
    pending_block,
)
from swarm_orchestrator.trigger_trace import TriggerTrace

from benchmarks.vlm_bench.run import rebuild_request
from benchmarks.vlm_bench.variants import gf_cluster, per_cluster
from reasoning.vlm.models import ReasonerConfig
from reasoning.vlm.per_cluster_runner import FixedGroupChoiceBackend
from tests.unit.test_m5_per_cluster_live_parity import live_pipeline
from tests.unit.vlm_bench_fixtures import synthetic_items

CONFIG = ReasonerConfig(backend_id="fixed", max_attempts=2)


def _frame(tmp_path: Path) -> Path:
    path = tmp_path / "frame.png"
    Image.new("RGB", (64, 48)).save(path)
    return path


def _shadow(tmp_path: Path, **kwargs):
    item = synthetic_items()["aaaa0002"]
    request = rebuild_request(item, str(_frame(tmp_path)))
    inputs, source = live_pipeline(item).per_cluster_probe_inputs(request, "fixed")
    record = compute_per_cluster_shadow(
        request, inputs, gf_cluster.grouping_params(item), FixedGroupChoiceBackend("first"),
        CONFIG, lookups_source=source, **kwargs,
    )
    return item, record


def test_two_group_scene_records_every_slot_choice_and_the_joint_check(tmp_path):
    item, record = _shadow(tmp_path)
    assert record.status == "ok" and record.error is None
    assert record.n_slots == 2 and [s.label for s in record.slots] == ["A", "B"]
    candidates, _, _ = per_cluster.per_cluster_candidates(item)
    assert record.choices == {s.label: s.option_ids[0] for s in candidates.slots}
    assert [c.label for c in record.per_choice] == ["A", "B"]
    assert all(c.feasible and c.executed_key == c.offered_key for c in record.per_choice)
    assert record.none_feasible == {"A": False, "B": False}
    bench = per_cluster.GroundingFirstPerClusterVariant().answer_extra(
        item, candidates, record.choices
    )
    assert record.joint_check == bench["joint_check"]
    assert record.m2.parse_status == "valid" and record.m2.attempts == 1
    assert record.timings.total_ms is not None and record.timings.grounding_ms is not None


def test_record_carries_no_prompt_or_image_data(tmp_path):
    _, record = _shadow(tmp_path)
    text = json.dumps(record.model_dump(mode="json"))
    assert "base64" not in text and "user_prompt" not in text
    assert len(text) < 20000


def test_deadline_stops_before_the_m2_call_and_keeps_enumeration(tmp_path):
    ticks = iter(range(0, 10_000, 100))
    _, record = _shadow(tmp_path, deadline=50.0, clock=lambda: next(ticks))
    assert record.status == "timeout" and "before the M2 call" in record.error
    assert record.n_slots == 2 and record.m2 is None
    assert record.timings.enumeration_ms is not None and record.timings.m2_call_ms is None


def test_missing_frame_is_an_error_not_a_raise(tmp_path):
    item = synthetic_items()["aaaa0002"]
    request = rebuild_request(item, str(tmp_path / "gone.png"))
    inputs, _ = live_pipeline(item).per_cluster_probe_inputs(request, "fixed")
    record = compute_per_cluster_shadow(
        request, inputs, gf_cluster.grouping_params(item), FixedGroupChoiceBackend(), CONFIG
    )
    assert record.status == "error" and record.error.startswith("FileNotFoundError: frame missing")


def test_attach_replaces_block_in_artifact_format(tmp_path):
    artifact = tmp_path / "r1.json"
    payload = {"request_id": "r1", "per_cluster_shadow": pending_block("r1"), "z": 1}
    artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    attach_shadow_block(artifact, {"request_id": "r1", "status": "ok"})
    expected = {**payload, "per_cluster_shadow": {"request_id": "r1", "status": "ok"}}
    assert artifact.read_text() == json.dumps(expected, indent=2, sort_keys=True)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["r1.json"]


def test_log_line_has_no_reply_text(tmp_path):
    _, record = _shadow(tmp_path)
    line = format_per_cluster_log(record)
    assert line.startswith(f"per_cluster_shadow request={record.request_id} status=ok slots=2")
    assert "fixed-group-choice sanity backend" not in line


def _record(trace: TriggerTrace, directive: str, robots, in_flight=None, sim_t=1.0, rid=None):
    trace.record(directive=directive, robots=robots, reason="stall", request_id=rid,
                 in_flight=in_flight or {}, analysis_in_flight=None, sim_t=sim_t,
                 wall_t=sim_t * 2)


def test_trace_coalesces_repeats_and_closes_runs(tmp_path):
    path = tmp_path / "trace.jsonl"
    trace = TriggerTrace(path, "20261113_000000", "s1")
    _record(trace, "start_analysis", ["robot_2", "robot_1"], rid="r1")
    for t in (2.0, 3.0, 4.0):
        _record(trace, "suppressed", ["robot_1", "robot_2"], {"c1": ["robot_1"]}, sim_t=t)
    _record(trace, "start_analysis", ["robot_3", "robot_4"], {"c1": ["robot_1"]}, 5.0, "r2")
    trace.close()
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert [line["event"] for line in lines] == ["event", "event", "event_run_end", "event"]
    assert lines[0]["robots"] == ["robot_1", "robot_2"]
    assert lines[2]["count"] == 3 and lines[2]["last_sim_t"] == 4.0
    group_b = lines[3]
    assert group_b["disjoint_from_busy"] is True and group_b["in_flight"] == {"c1": ["robot_1"]}
    assert '"run_id": "20261113_000000"' in path.read_text().splitlines()[0]

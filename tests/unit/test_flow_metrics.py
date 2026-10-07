"""Unit tests for the foundations-round flow metrics (synthetic GT, offline).

Covers the free-flow table (schema, loud loader, harvest derivation),
`delay_vs_free_flow`, `conflict_dissolution`, `aperture_throughput` and the
`OutcomeClass` mapping pinned against the known IB10 episodes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import free_flow_table as fft
from scripts.coverage_scene_scores import (
    DISSOLUTION_SEPARATION_M,
    RECLOG_MIN_SEC,
    MockBackendError,
    OutcomeClass,
    aperture_region,
    aperture_throughput,
    classify_outcome,
    conflict_dissolution,
    decision_backend,
    delay_vs_free_flow,
    load_ground_truth,
    load_scenario,
    main,
    score_b1,
    score_flow,
    score_ib10,
    sustained_spell_onset,
)
from scripts.free_flow_table import (
    FreeFlowTable,
    FreeFlowTableError,
    build_table,
    derive_entries,
    load_free_flow_table,
)
from tests.unit.test_coverage_scene_scores import (
    DT,
    IB10_DESIGNED,
    _b1_gt,
    _frames,
    _hold,
    _ib10_gt,
    _ib10_record,
    _track,
    _write_gt,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
HASH = "a" * 64
HEAD_ON_GOALS = {"robot_1": (2.5, 0.0), "robot_2": (-2.5, 0.0)}


def _entry(time_sec: float, **extra) -> dict:
    return {"time_sec": time_sec, "run_id": "ff_run:20261005_000000", "gt_hash": HASH,
            "mechanism": "solo_in_space", **extra}


def _table(scenes: dict) -> FreeFlowTable:
    return FreeFlowTable.model_validate(build_table("free_flow_test", scenes))


def _write_table(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data))
    return path


# ---- free-flow table: schema and loud loader ----


def test_table_round_trips_through_the_loader(tmp_path):
    data = build_table("free_flow_v1", {"bottleneck_merge": {"robot_1": _entry(30.0)}})
    table = load_free_flow_table(_write_table(tmp_path / "t.json", data))
    assert table.lookup("bottleneck_merge", "robot_1").time_sec == 30.0
    assert table.origin_rule == "own_departure"


def test_lookup_is_none_for_a_missing_scene_or_robot():
    table = _table({"bottleneck_merge": {"robot_1": _entry(30.0)}})
    assert table.lookup("bottleneck_merge", "robot_2") is None
    assert table.lookup("t2b_flow_ordering", "robot_1") is None


def test_loader_fails_loudly_on_a_missing_file(tmp_path):
    with pytest.raises(FreeFlowTableError, match="not found"):
        load_free_flow_table(tmp_path / "absent.json")


def test_loader_fails_loudly_on_non_json(tmp_path):
    path = tmp_path / "t.json"
    path.write_text("{not json")
    with pytest.raises(FreeFlowTableError, match="not JSON"):
        load_free_flow_table(path)


def test_loader_rejects_an_empty_table(tmp_path):
    data = {"schema_version": 1, "table_id": "x", "origin_rule": "own_departure",
            "arrival_rule": "gt_within_0.35_stay_0.5", "scenes": {}}
    with pytest.raises(FreeFlowTableError, match="at least one scene"):
        load_free_flow_table(_write_table(tmp_path / "t.json", data))


def test_loader_rejects_a_foreign_origin_rule(tmp_path):
    data = build_table("x", {"s": {"robot_1": _entry(30.0)}})
    data["origin_rule"] = "common_t0"
    with pytest.raises(FreeFlowTableError):
        load_free_flow_table(_write_table(tmp_path / "t.json", data))


def test_entry_rejects_a_malformed_gt_hash():
    with pytest.raises(ValueError, match="gt_hash"):
        fft.FreeFlowEntry.model_validate({**_entry(30.0), "gt_hash": "abc"})


def test_entry_rejects_a_time_that_disagrees_with_its_endpoints():
    with pytest.raises(ValueError, match="time_sec"):
        fft.FreeFlowEntry.model_validate(
            _entry(30.0, departure_sec=10.0, arrival_sec=50.0))


def test_entry_rejects_an_unknown_mechanism():
    with pytest.raises(ValueError):
        fft.FreeFlowEntry.model_validate({**_entry(30.0), "mechanism": "staggered"})


def test_default_table_is_absent_until_committed(monkeypatch, tmp_path):
    monkeypatch.setattr(fft, "DEFAULT_TABLE_PATH", tmp_path / "free_flow_v1.json")
    assert fft.default_table() == (None, None)


def test_committed_default_table_is_schema_valid_when_present():
    if not fft.DEFAULT_TABLE_PATH.is_file():
        pytest.skip("free_flow_v1.json not harvested yet")
    table = load_free_flow_table(fft.DEFAULT_TABLE_PATH)
    for scene in table.scenes:
        load_scenario(scene)


# ---- free-flow harvest derivation ----


def _solo_in_time_gt(tmp_path: Path, *, overlap: bool = False) -> Path:
    """robot_1 traverses 0-10 s alone; robot_2 waits, then traverses 15-25 s."""
    goals = {"robot_1": (1.0, 1.0), "robot_2": (-1.0, -1.0)}
    r1 = _hold((-1.0, 1.0), 5) + _track([(-1.0, 1.0), (1.0, 1.0)], 100) + _hold((1.0, 1.0), 200)
    start2 = 50 if overlap else 150
    r2 = (_hold((1.0, -1.0), start2) + _track([(1.0, -1.0), (-1.0, -1.0)], 100)
          + _hold((-1.0, -1.0), 305 - start2 - 100))
    return _write_gt(tmp_path / "gt", _frames({"robot_1": r1, "robot_2": r2}), goals)


def test_derive_times_each_robot_from_its_own_departure(tmp_path):
    entries = derive_entries(_solo_in_time_gt(tmp_path), mechanism="solo_in_time", run_id="r")
    # 2 m at 0.2 m/s; arrival is the first sample within 0.35 m of the goal.
    assert entries["robot_1"]["departure_sec"] == pytest.approx(0.6, abs=0.11)
    assert entries["robot_2"]["departure_sec"] == pytest.approx(15.1, abs=0.11)
    assert entries["robot_1"]["time_sec"] == pytest.approx(entries["robot_2"]["time_sec"],
                                                           abs=0.11)
    assert entries["robot_1"]["time_sec"] == pytest.approx((2.0 - 0.35) / 0.2, abs=0.3)
    assert len(entries["robot_1"]["gt_hash"]) == 64


def test_derive_refuses_a_solo_in_time_traversal_with_company(tmp_path):
    with pytest.raises(ValueError, match="moved"):
        derive_entries(_solo_in_time_gt(tmp_path, overlap=True), mechanism="solo_in_time",
                       run_id="r")


def test_derive_refuses_a_solo_traversal_that_brushes_a_parked_robot(tmp_path):
    # robot_2 parked 0.3 m off robot_1's line: the M4 latch would fire.
    goals = {"robot_1": (2.0, 0.0), "robot_2": (1.0, 0.3)}
    r1 = _hold((0.0, 0.0), 5) + _track([(0.0, 0.0), (2.0, 0.0)], 100) + _hold((2.0, 0.0), 50)
    gt = _write_gt(tmp_path / "gt", _frames({"robot_1": r1, "robot_2": _hold((1.0, 0.3), 155)}),
                   goals)
    with pytest.raises(ValueError, match="not free flow"):
        derive_entries(gt, mechanism="solo_in_time", run_id="r", robots=["robot_1"])


def test_derive_refuses_a_solo_in_space_run_holding_another_robot(tmp_path):
    with pytest.raises(ValueError, match="must hold only robot_1"):
        derive_entries(_solo_in_time_gt(tmp_path), mechanism="solo_in_space", run_id="r",
                       robots=["robot_1"])


def test_derive_times_a_solo_in_space_run(tmp_path):
    goals = {"robot_2": (0.0, 2.0)}
    track = _hold((0.0, 0.0), 30) + _track([(0.0, 0.0), (0.0, 2.0)], 100) + _hold((0.0, 2.0), 50)
    gt = _write_gt(tmp_path / "gt", _frames({"robot_2": track}), goals)
    entries = derive_entries(gt, mechanism="solo_in_space", run_id="r")
    assert list(entries) == ["robot_2"]
    assert entries["robot_2"]["min_clearance_m"] is None
    assert entries["robot_2"]["time_sec"] == pytest.approx((2.0 - 0.35) / 0.2, abs=0.3)


def test_derive_refuses_a_robot_that_never_arrives(tmp_path):
    goals = {"robot_1": (5.0, 0.0)}
    gt = _write_gt(tmp_path / "gt", _frames({"robot_1": _track([(0.0, 0.0), (1.0, 0.0)], 50)}),
                   goals)
    with pytest.raises(ValueError, match="not a traversal"):
        derive_entries(gt, mechanism="solo_in_space", run_id="r")


def test_derive_cli_refuses_a_run_that_dispatched(tmp_path, capsys):
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    (decisions / "a.json").write_text(json.dumps(
        {"decision": {"congestion_detected": True}, "grounded_command_present": True}))
    code = fft.main(["derive", "--scene", "s", "--gt", str(_solo_in_time_gt(tmp_path)),
                     "--mechanism", "solo_in_time", "--run-id", "r",
                     "--decisions", str(decisions)])
    assert code == 1
    assert "dispatched" in capsys.readouterr().err


def _dispatching_artifact(**extra: object) -> str:
    return json.dumps({"decision": {"congestion_detected": True},
                       "grounded_command_present": True, **extra})


def test_count_dispatches_excludes_a_suppressed_artifact(tmp_path):
    (tmp_path / "a.json").write_text(_dispatching_artifact(
        dispatch_enabled=False, dispatch_suppressed=True))
    assert fft.count_dispatches(tmp_path) == 0


def test_count_dispatches_counts_only_the_unsuppressed_artifact(tmp_path):
    (tmp_path / "a.json").write_text(_dispatching_artifact(
        dispatch_enabled=False, dispatch_suppressed=True))
    (tmp_path / "b.json").write_text(_dispatching_artifact())
    assert fft.count_dispatches(tmp_path) == 1


def test_count_dispatches_excludes_a_dispatch_disabled_artifact_without_suppressed_flag(
    tmp_path,
):
    # Addendum A3: a log-only cell is strict zero even when the artifact
    # carries a grounded command but no `dispatch_suppressed` key.
    (tmp_path / "a.json").write_text(_dispatching_artifact(dispatch_enabled=False))
    assert fft.count_dispatches(tmp_path) == 0


def test_count_dispatches_counts_an_explicitly_dispatch_enabled_artifact(tmp_path):
    (tmp_path / "a.json").write_text(_dispatching_artifact(dispatch_enabled=True))
    assert fft.count_dispatches(tmp_path) == 1


def test_count_dispatches_ignores_a_task_stream_jsonl_beside_the_artifacts(tmp_path):
    # v2_final_run.sh copies tasks_<session>.jsonl into the decisions dir;
    # its multi-line body must neither be parsed nor counted.
    (tmp_path / "a.json").write_text(_dispatching_artifact())
    (tmp_path / "tasks_abc.jsonl").write_text(
        '{"event": "stream_start"}\n{"event": "task_done"}\n')
    assert fft.count_dispatches(tmp_path) == 1


# ---- delay_vs_free_flow ----


def _held_series(tmp_path: Path):
    """robot_1 departs at once; robot_2 is held 10 s, then takes the same trip."""
    goals = {"robot_1": (2.0, 0.0), "robot_2": (2.0, 1.0)}
    r1 = _track([(0.0, 0.0), (2.0, 0.0)], 100) + _hold((2.0, 0.0), 200)
    r2 = _hold((0.0, 1.0), 100) + _track([(0.0, 1.0), (2.0, 1.0)], 100) + _hold((2.0, 1.0), 100)
    gt = _write_gt(tmp_path / "gt", _frames({"robot_1": r1, "robot_2": r2}), goals)
    from scripts.t2b_forced_order import score_ground_truth

    return load_ground_truth(gt), score_ground_truth("x", gt)


def test_delay_is_null_without_a_table(tmp_path):
    series, run = _held_series(tmp_path)
    result = delay_vs_free_flow(series, run.arrivals_sec, run.end_sec, "s", None)
    assert result["per_robot"]["robot_1"]["delay_sec"] is None
    assert result["per_robot"]["robot_1"]["reason"] == "no_table"
    assert result["sum_sec"] is None and result["complete"] is False


def test_a_held_back_robot_carries_no_fake_delay(tmp_path):
    series, run = _held_series(tmp_path)
    travel = run.arrivals_sec["robot_1"] - 0.1
    table = _table({"s": {"robot_1": _entry(round(travel, 2)),
                          "robot_2": _entry(round(travel, 2))}})
    result = delay_vs_free_flow(series, run.arrivals_sec, run.end_sec, "s", table)
    assert result["per_robot"]["robot_1"]["delay_sec"] == pytest.approx(0.0, abs=0.11)
    assert result["per_robot"]["robot_2"]["delay_sec"] == pytest.approx(0.0, abs=0.11)
    assert result["complete"] is True
    assert result["max_sec"] == pytest.approx(0.0, abs=0.11)


def test_delay_is_actual_minus_free_flow_and_aggregates(tmp_path):
    series, run = _held_series(tmp_path)
    travel = run.arrivals_sec["robot_1"] - 0.1
    table = _table({"s": {"robot_1": _entry(round(travel - 3.0, 2)),
                          "robot_2": _entry(round(travel - 1.0, 2))}})
    result = delay_vs_free_flow(series, run.arrivals_sec, run.end_sec, "s", table)
    assert result["per_robot"]["robot_1"]["delay_sec"] == pytest.approx(3.0, abs=0.11)
    assert result["sum_sec"] == pytest.approx(4.0, abs=0.2)
    assert result["max_sec"] == pytest.approx(3.0, abs=0.11)


def test_a_robot_missing_from_the_table_nulls_the_aggregate(tmp_path):
    series, run = _held_series(tmp_path)
    table = _table({"s": {"robot_1": _entry(5.0)}})
    result = delay_vs_free_flow(series, run.arrivals_sec, run.end_sec, "s", table)
    assert result["per_robot"]["robot_2"]["reason"] == "no_baseline"
    assert result["per_robot"]["robot_2"]["delay_sec"] is None
    assert result["sum_sec"] is None
    assert result["n_scored"] == 1


def test_a_censored_robot_gets_only_a_lower_bound(tmp_path):
    series, run = _held_series(tmp_path)
    arrivals = {**run.arrivals_sec, "robot_2": None}
    table = _table({"s": {"robot_1": _entry(5.0), "robot_2": _entry(5.0)}})
    result = delay_vs_free_flow(series, arrivals, run.end_sec, "s", table)
    row = result["per_robot"]["robot_2"]
    assert row["delay_sec"] is None and row["censored"] is True
    assert row["delay_lower_bound_sec"] == pytest.approx(run.end_sec - 10.1 - 5.0, abs=0.11)
    assert result["sum_sec"] is None
    assert result["sum_lower_bound_sec"] is not None


# ---- conflict_dissolution ----


def _head_on(tmp_path: Path, *, yielder_resumes: bool = True):
    """A head-on standoff at ~10 s; robot_2 backs off east to a pull-off pocket
    (13-15 s) and holds; robot_1 passes; robot_2 then resumes toward its goal at
    25 s (or stays parked)."""
    r1 = (_track([(-1.5, 0.0), (-0.2, 0.0)], 100) + _hold((-0.2, 0.0), 50)
          + _track([(-0.2, 0.0), (2.5, 0.0)], 150) + _hold((2.5, 0.0), 300))
    r2 = (_track([(1.5, 0.0), (0.2, 0.0)], 100) + _hold((0.2, 0.0), 30)
          + _track([(0.2, 0.0), (1.2, 0.35)], 20))
    if yielder_resumes:
        r2 += _hold((1.2, 0.35), 100) + _track([(1.2, 0.35), (-2.5, 0.0)], 200) + _hold(
            (-2.5, 0.0), 150)
    else:
        r2 += _hold((1.2, 0.35), 450)
    n = min(len(r1), len(r2))
    gt = _write_gt(tmp_path / "gt", _frames({"robot_1": r1[:n], "robot_2": r2[:n]}),
                   HEAD_ON_GOALS)
    from scripts.t2b_forced_order import score_ground_truth

    return load_ground_truth(gt), score_ground_truth("x", gt)


def test_dissolution_waits_for_the_yielder_to_resume(tmp_path):
    series, run = _head_on(tmp_path)
    result = conflict_dissolution(series, ["robot_1", "robot_2"], 10.0, run.arrivals_sec)
    # robot_2 holds parked (not progressing) until t = 25 s.
    assert result["dissolved_at_sec"] == pytest.approx(25.1, abs=0.2)
    assert result["conflict_dissolution_sec"] == pytest.approx(15.1, abs=0.2)
    assert result["censored"] is False
    assert result["dissolution_final"] is True


def test_dissolution_is_distinct_from_full_resolution(tmp_path):
    series, run = _head_on(tmp_path)
    result = conflict_dissolution(series, ["robot_1", "robot_2"], 10.0, run.arrivals_sec)
    assert result["time_to_full_resolution_sec"] > result["conflict_dissolution_sec"] + 10.0
    assert result["resolution_censored"] is False


def test_a_yielder_that_never_resumes_never_dissolves(tmp_path):
    series, run = _head_on(tmp_path, yielder_resumes=False)
    result = conflict_dissolution(series, ["robot_1", "robot_2"], 10.0, run.arrivals_sec)
    assert result["dissolved_at_sec"] is None
    assert result["censored"] is True
    assert result["time_to_full_resolution_sec"] is None


def test_receding_does_not_count_as_progress(tmp_path):
    # robot_2 backing away from its goal for 2 s after the standoff (t 13-15)
    # is not progress, even well separated: the dissolution comes later.
    series, run = _head_on(tmp_path)
    result = conflict_dissolution(series, ["robot_1", "robot_2"], 10.0, run.arrivals_sec)
    assert result["dissolved_at_sec"] > 15.0


def test_no_onset_means_no_dissolution(tmp_path):
    series, run = _head_on(tmp_path)
    result = conflict_dissolution(series, ["robot_1", "robot_2"], None, run.arrivals_sec)
    assert result["conflict_dissolution_sec"] is None
    assert result["censored"] is None


def test_a_re_formed_pair_is_reported_not_erased(tmp_path):
    # Dissolved at once (1 m apart, both driving east), then robot_2 drifts in
    # to 0.3 m and both stop short of their goals for 20 s: a new clog.
    goals = {"robot_1": (5.0, 0.0), "robot_2": (5.0, 1.0)}
    r1 = _track([(0.0, 0.0), (2.0, 0.0)], 100) + _hold((2.0, 0.0), 220)
    r2 = (_track([(0.0, 1.0), (1.0, 1.0)], 50) + _track([(1.0, 1.0), (2.0, 0.3)], 50)
          + _hold((2.0, 0.3), 220))
    gt = _write_gt(tmp_path / "gt", _frames({"robot_1": r1, "robot_2": r2}), goals)
    result = conflict_dissolution(load_ground_truth(gt), ["robot_1", "robot_2"], 0.0,
                                  {"robot_1": None, "robot_2": None})
    assert result["dissolved_at_sec"] == pytest.approx(0.1, abs=0.11)
    assert result["reclogged_at_sec"] is not None
    assert result["dissolution_final"] is False


def test_a_lone_stall_after_dissolution_is_not_a_reclog(tmp_path):
    # Step-7b rerun 2's yielder: stalls 14 s alone after the release.
    goals = {"robot_1": (5.0, 0.0), "robot_2": (5.0, 1.0)}
    r1 = _track([(0.0, 0.0), (2.0, 0.0)], 100) + _hold((2.0, 0.0), 220)
    r2 = _track([(0.0, 1.0), (2.0, 1.0)], 100) + _hold((2.0, 1.0), 220)
    gt = _write_gt(tmp_path / "gt", _frames({"robot_1": r1, "robot_2": r2}), goals)
    result = conflict_dissolution(load_ground_truth(gt), ["robot_1", "robot_2"], 0.0,
                                  {"robot_1": None, "robot_2": None})
    assert result["reclogged_at_sec"] is None
    assert result["dissolution_final"] is True


def test_a_not_yet_dispatched_robot_is_neutral(tmp_path):
    # robot_2 sits at spawn (never departs, far away): robot_1 alone decides.
    goals = {"robot_1": (2.0, 0.0), "robot_2": (-3.0, 2.0)}
    r1 = _track([(0.0, 0.0), (2.0, 0.0)], 100) + _hold((2.0, 0.0), 50)
    gt = _write_gt(tmp_path / "gt", _frames({"robot_1": r1, "robot_2": _hold((0.0, 2.0), 150)}),
                   goals)
    from scripts.t2b_forced_order import score_ground_truth

    run = score_ground_truth("x", gt)
    result = conflict_dissolution(load_ground_truth(gt), ["robot_1", "robot_2"], 0.0,
                                  run.arrivals_sec)
    assert result["dissolved_at_sec"] == pytest.approx(0.1, abs=0.11)


def test_dissolution_separation_is_m4s_latch_distance():
    safety = yaml.safe_load((REPO_ROOT / "ros2_ws/src/swarm_execution/config/safety.yaml")
                            .read_text())
    assert DISSOLUTION_SEPARATION_M == _first_key(safety, "min_distance_m")


def test_reclog_window_is_m5s_stall_threshold():
    orch = yaml.safe_load((REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
                          .read_text())
    assert RECLOG_MIN_SEC == orch["stall_threshold_sec"]


def _first_key(node, key):
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = _first_key(value, key)
            if found is not None:
                return found
    return None


def test_sustained_spell_onset_matches_the_slip_rule():
    flags = [(i * DT, 10 <= i < 25) for i in range(40)]
    assert sustained_spell_onset(flags, 1.0) == pytest.approx(1.0)
    short = [(i * DT, 10 <= i < 15) for i in range(40)]
    assert sustained_spell_onset(short, 1.0) is None


# ---- aperture_throughput ----


def test_b1_throughput_matches_the_gate_flow(tmp_path):
    result = score_b1(_b1_gt(tmp_path))
    aperture = result["aperture_throughput"]
    assert aperture["n_exited"] == 3 and aperture["n_expected"] == 3
    assert aperture["complete"] is True
    assert aperture["throughput_rps"] == pytest.approx(result["gate"]["flow_per_100s"] / 100,
                                                       rel=1e-3)


def test_a_clogged_aperture_is_incomplete(tmp_path):
    result = score_b1(_b1_gt(tmp_path, robot_2_first=True))
    aperture = result["aperture_throughput"]
    assert aperture["complete"] is False
    assert aperture["n_exited"] < aperture["n_expected"]


def test_a_cell_without_an_aperture_scores_none():
    assert aperture_region(load_scenario("intersection_bottleneck")) is None
    assert aperture_region(load_scenario("t2b_flow_ordering")) is None


def test_an_oracle_declared_aperture_counts_westbound_passages(tmp_path):
    scenario = {
        "name": "synthetic",
        "oracle": {"aperture": {"x_span": [-0.5, 0.5], "lane_y": 0.0, "half_width_m": 0.3}},
        "robots": [{"robot_id": "robot_2", "spawn": {"x": 2.0, "y": 0.0},
                    "goal": {"x": -2.0, "y": 0.0}}],
    }
    goals = {"robot_2": (-2.0, 0.0)}
    gt = _write_gt(tmp_path / "gt", _frames({"robot_2": _track([(2.0, 0.0), (-2.0, 0.0)], 200)}),
                   goals)
    result = aperture_throughput(scenario, load_ground_truth(gt), 19.9)
    passage = result["passages"]["robot_2"]
    assert passage["entry_sec"] == pytest.approx(7.5, abs=0.15)
    assert passage["exit_sec"] == pytest.approx(12.5, abs=0.15)
    assert result["throughput_rps"] == pytest.approx(1 / 5.0, rel=0.05)


# ---- OutcomeClass ----


@pytest.mark.parametrize(
    ("label", "kwargs", "expected"),
    [
        # step-7b rerun 2 (ib10_7b_vi_20261003_030944): 4/4, one dispatch.
        ("7b_rerun2", dict(all_arrived=True, n_dispatches=1, fallback=False,
                           fallback_exhausted=False), OutcomeClass.RESOLVED),
        # v2 demo live episode 2 (ER-2): 4/4, one dispatch.
        ("demo_ep2", dict(all_arrived=True, n_dispatches=1, fallback=False,
                          fallback_exhausted=False), OutcomeClass.RESOLVED),
        # step-7b rerun 1 (ib10_7b_20261003_022532): 2/4 latched for good.
        ("7b_rerun1", dict(all_arrived=False, n_dispatches=1, fallback=False,
                           fallback_exhausted=False), OutcomeClass.CLOGGED),
        # step-6 episode 2 (20261002_125412): 1/4 at the 300 s cap, four
        # dispatches and a fallback, but no fallback_exhausted string in its
        # log: clogged through censoring.
        ("s6_ep2", dict(all_arrived=False, n_dispatches=4, fallback=True,
                        fallback_exhausted=False), OutcomeClass.CLOGGED),
        ("retriggered", dict(all_arrived=True, n_dispatches=2, fallback=False,
                             fallback_exhausted=False), OutcomeClass.INTERMITTENT),
        ("retried", dict(all_arrived=True, n_dispatches=1, fallback=True,
                         fallback_exhausted=False), OutcomeClass.INTERMITTENT),
        ("exhausted", dict(all_arrived=True, n_dispatches=1, fallback=True,
                           fallback_exhausted=True), OutcomeClass.CLOGGED),
        # Forcing-audit A3: no dispatch, nothing to credit -- a distinct class.
        ("no_dispatch_all_arrived", dict(all_arrived=True, n_dispatches=0, fallback=None,
                                         fallback_exhausted=None), OutcomeClass.SELF_RESOLVED),
        ("no_dispatch_censored", dict(all_arrived=False, n_dispatches=0, fallback=None,
                                      fallback_exhausted=None), OutcomeClass.CLOGGED),
        ("unknown_dispatches", dict(all_arrived=True, n_dispatches=None, fallback=None,
                                    fallback_exhausted=None), None),
        ("unknown_but_censored", dict(all_arrived=False, n_dispatches=None, fallback=None,
                                      fallback_exhausted=None), OutcomeClass.CLOGGED),
    ],
)
def test_outcome_class_mapping(label, kwargs, expected):
    assert classify_outcome(valid=True, **kwargs) == expected, label


def test_a_composite_without_m5s_log_is_not_guessed_resolved():
    # IB10's cross phase can fail into a fallback while all four still
    # arrive (intermittent); without the M5 log that cannot be ruled out.
    assert classify_outcome(valid=True, all_arrived=True, n_dispatches=1, fallback=None,
                            fallback_exhausted=None, composite=True) is None
    assert classify_outcome(valid=True, all_arrived=False, n_dispatches=1, fallback=None,
                            fallback_exhausted=None, composite=True) == OutcomeClass.CLOGGED


def test_ib10_scored_without_m5_log_has_no_class(tmp_path):
    result = score_ib10(_ib10_gt(tmp_path, IB10_DESIGNED), decisions_dir=_decisions(tmp_path, 1))
    assert result["outcome_class"] is None


def test_an_invalid_run_has_no_outcome_class():
    # step-6 live episode 1: the control stack died ~134.6 sim-s; its
    # censoring is a harness artifact, not a clog.
    assert classify_outcome(valid=False, all_arrived=False, n_dispatches=2, fallback=False,
                            fallback_exhausted=False) is None


def test_outcome_class_values_are_the_registered_strings():
    # `self_resolved` added by forcing-audit A3 (2026-10-07).
    assert [c.value for c in OutcomeClass] == [
        "resolved", "intermittent", "clogged", "self_resolved",
    ]


def test_resolved_is_never_awarded_without_a_dispatch():
    for composite in (False, True):
        assert classify_outcome(valid=True, all_arrived=True, n_dispatches=0, fallback=None,
                                fallback_exhausted=None, composite=composite) is (
            OutcomeClass.SELF_RESOLVED
        )


def test_zero_dispatch_episode_reports_self_resolved_with_its_count(tmp_path):
    result = score_ib10(_ib10_gt(tmp_path, IB10_DESIGNED),
                        decisions_dir=_decisions(tmp_path, 0, no_congestion=3),
                        m5_log=RESOLVED_M5_LOG)
    assert result["outcome_class"] == "self_resolved"
    assert result["n_dispatches"] == 0


RESOLVED_M5_LOG = (
    "dispatch request=r1 command=r1-junction-recede-robot_4 robot=robot_4\n"
    "junction_clear phase advance command=r1-junction-release completed=True "
    "phase_reached=resolved done=True\n"
)


def _decisions(tmp_path: Path, n: int, no_congestion: int = 0) -> Path:
    path = tmp_path / "decisions"
    path.mkdir()
    for i in range(n):
        record = _ib10_record(None, ["robot_4", "robot_3"])
        record["scene"]["stamp"] = 30.0 + i
        (path / f"d{i}.json").write_text(json.dumps(record))
    for i in range(no_congestion):
        (path / f"n{i}.json").write_text(json.dumps({
            "decision": {"congestion_detected": False, "strategy": "none"},
            "grounded_command_present": False, "scene": {"stamp": 190.0 + i}}))
    return path


def test_ib10_designed_episode_classes_resolved_despite_re_analyses(tmp_path):
    # The 4/4 rerun's shape: one dispatch, then no-congestion re-analyses.
    result = score_ib10(_ib10_gt(tmp_path, IB10_DESIGNED),
                        decisions_dir=_decisions(tmp_path, 1, no_congestion=4),
                        m5_log=RESOLVED_M5_LOG)
    assert result["outcome_class"] == "resolved"
    assert result["outcome_evidence"]["n_dispatches"] == 1
    assert result["n_dispatches"] == 1


def test_ib10_censored_episode_classes_clogged(tmp_path):
    stuck = dict(IB10_DESIGNED)
    stuck["robot_2"] = [(0, 1.75, 0.0), (10, 1.75, 0.0), (15, 0.25, 0.0)]
    result = score_ib10(_ib10_gt(tmp_path, stuck), decisions_dir=_decisions(tmp_path, 4))
    assert result["outcome_class"] == "clogged"


def test_ib10_harness_invalid_run_has_no_class(tmp_path):
    result = score_ib10(_ib10_gt(tmp_path, IB10_DESIGNED), decisions_dir=_decisions(tmp_path, 1),
                        invalid_reason="control stack dead at sim 134.6")
    assert result["outcome_class"] is None
    assert result["outcome_evidence"]["invalid_reason"] == "control stack dead at sim 134.6"


def test_ib10_invalid_jam_has_no_class(tmp_path):
    late = {rid: [(t + 30 if t >= 10 else t, x, y) for t, x, y in keys]
            for rid, keys in IB10_DESIGNED.items()}
    result = score_ib10(_ib10_gt(tmp_path, late, end_sec=130.0),
                        decisions_dir=_decisions(tmp_path, 1))
    assert result["outcome_class"] is None


# ---- additive-only wiring ----


B1_EXISTING_KEYS = {"scene", "t0_sec", "end_sec", "arrivals_after_t0_sec", "n_arrived",
                    "censored", "makespan_sec", "gate", "stop_time_sec", "merge", "conflict"}
FLOW_KEYS = {"delay_vs_free_flow", "conflict_dissolution", "aperture_throughput",
             "outcome_class", "n_dispatches", "backend_id", "outcome_evidence"}


def test_b1_keeps_every_existing_field_and_adds_only_flow_fields(tmp_path):
    result = score_b1(_b1_gt(tmp_path))
    assert set(result) == B1_EXISTING_KEYS | FLOW_KEYS


def test_ib10_dissolution_uses_the_formed_jam_onset(tmp_path):
    result = score_ib10(_ib10_gt(tmp_path, IB10_DESIGNED))
    assert result["conflict_dissolution"]["onset_sec"] == result["formed_jam"]["onset_sec"]
    assert result["conflict_dissolution"]["involved"] == ["robot_1", "robot_2", "robot_3",
                                                          "robot_4"]


def test_flow_cli_scores_any_cell_with_an_explicit_table(tmp_path, capsys):
    gt = _ib10_gt(tmp_path, IB10_DESIGNED)
    table = build_table("free_flow_test", {"intersection_bottleneck": {
        rid: _entry(10.0) for rid in IB10_DESIGNED}})
    path = _write_table(tmp_path / "t.json", table)
    log = tmp_path / "m5.log"
    log.write_text(RESOLVED_M5_LOG)
    assert main(["flow", "--scenario", "intersection_bottleneck", "--gt", str(gt),
                 "--free-flow", str(path), "--decisions", str(_decisions(tmp_path, 1)),
                 "--m5-log", str(log)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["delay_vs_free_flow"]["table_id"] == "free_flow_test"
    assert out["delay_vs_free_flow"]["complete"] is True
    assert all(r["delay_sec"] > 0 for r in out["delay_vs_free_flow"]["per_robot"].values())
    assert out["outcome_class"] == "resolved"


def test_flow_cli_fails_loudly_on_a_missing_explicit_table(tmp_path):
    gt = _ib10_gt(tmp_path, IB10_DESIGNED)
    with pytest.raises(FreeFlowTableError):
        main(["flow", "--scenario", "intersection_bottleneck", "--gt", str(gt),
              "--free-flow", str(tmp_path / "absent.json")])


def test_score_flow_matches_the_ib10_scorers_flow_fields(tmp_path):
    gt = _ib10_gt(tmp_path, IB10_DESIGNED)
    decisions = _decisions(tmp_path, 1)
    flow = score_flow(gt, load_scenario("intersection_bottleneck"), decisions_dir=decisions)
    ib10 = score_ib10(gt, decisions_dir=decisions)
    for key in FLOW_KEYS:
        assert flow[key] == ib10[key], key


def test_dissolution_rejects_pairs_closer_than_the_separation(tmp_path):
    # Two robots moving side by side 0.3 m apart toward their goals never
    # dissolve: the pair stays inside the latch distance.
    goals = {"robot_1": (3.0, 0.0), "robot_2": (3.0, 0.3)}
    frames = _frames({"robot_1": _track([(0.0, 0.0), (3.0, 0.0)], 200),
                      "robot_2": _track([(0.0, 0.3), (3.0, 0.3)], 200)})
    gt = _write_gt(tmp_path / "gt", frames, goals)
    result = conflict_dissolution(load_ground_truth(gt), ["robot_1", "robot_2"], 0.0,
                                  {"robot_1": None, "robot_2": None})
    assert result["dissolved_at_sec"] is None


# ---- forcing-audit A2: backend column and mock refusal ----


def _backend_decisions(tmp_path: Path, effective: str | None, diagnostic: str | None) -> Path:
    path = tmp_path / "decisions"
    path.mkdir()
    record = _ib10_record(None, ["robot_4", "robot_3"])
    if diagnostic is not None:
        record["diagnostics"] = {"backend_id": diagnostic, "attempts": 1}
    if effective is not None:
        record["reasoner_config_effective"] = {"backend_id": effective}
    (path / "d0.json").write_text(json.dumps(record))
    return path


def test_backend_id_prefers_the_effective_arm_id(tmp_path):
    # Pre-F09 successes carry the provider model id in diagnostics.
    decisions = _backend_decisions(tmp_path, "openai_gpt56_sol", "gpt-5.6-sol")
    assert decision_backend(decisions) == "openai_gpt56_sol"


def test_backend_id_falls_back_to_diagnostics(tmp_path):
    assert decision_backend(_backend_decisions(tmp_path, None, "gemini")) == "gemini"


def test_backend_id_is_none_when_no_artifact_records_one(tmp_path):
    assert decision_backend(_decisions(tmp_path, 1)) is None


def test_mock_bundle_is_refused_for_scoring(tmp_path):
    decisions = _backend_decisions(tmp_path, "mock", "mock")
    with pytest.raises(MockBackendError, match="mock backend"):
        score_flow(_ib10_gt(tmp_path, IB10_DESIGNED), load_scenario("intersection_bottleneck"),
                   decisions_dir=decisions)


def test_mock_named_only_in_diagnostics_is_still_refused(tmp_path):
    with pytest.raises(MockBackendError):
        decision_backend(_backend_decisions(tmp_path, None, "mock"))


def test_allow_mock_scores_the_bundle_and_reports_the_backend(tmp_path):
    decisions = _backend_decisions(tmp_path, "mock", "mock")
    result = score_ib10(_ib10_gt(tmp_path, IB10_DESIGNED), decisions_dir=decisions,
                        allow_mock=True)
    assert result["backend_id"] == "mock"


def test_live_bundle_row_carries_its_backend_id(tmp_path):
    decisions = _backend_decisions(tmp_path, "gemini", "gemini")
    result = score_ib10(_ib10_gt(tmp_path, IB10_DESIGNED), decisions_dir=decisions)
    assert result["backend_id"] == "gemini"


def test_flow_cli_refuses_a_mock_bundle_without_the_flag(tmp_path, capsys):
    gt = _ib10_gt(tmp_path, IB10_DESIGNED)
    decisions = _backend_decisions(tmp_path, "mock", "mock")
    argv = ["flow", "--scenario", "intersection_bottleneck", "--gt", str(gt),
            "--no-free-flow", "--decisions", str(decisions)]
    assert main(argv) == 2
    assert "--allow-mock" in capsys.readouterr().err
    assert main([*argv, "--allow-mock"]) == 0
    assert json.loads(capsys.readouterr().out)["backend_id"] == "mock"

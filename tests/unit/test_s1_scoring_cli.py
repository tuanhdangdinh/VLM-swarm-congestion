"""Unit tests for the S1 scoring CLI and the env-gated golden on a real pilot bundle."""

import json
import os
from pathlib import Path

import pytest

from benchmarks.s1_scoring import score_bundle
from benchmarks.s1_scoring.__main__ import main

DATA = Path(__file__).parent / "data" / "s1_scoring"
# The E24 bundle files the scorer reads exceed the 200 KB fixture budget, so the
# golden runs only when this variable points at batch5/s1b_E24_seed24_er2_f2.
GOLDEN_ENV = "S1_SCORING_GOLDEN_BUNDLE"


def test_cli_writes_one_episode_line_per_bundle(tmp_path):
    out = tmp_path / "r.jsonl"
    assert main([str(DATA / "complete"), str(DATA / "censored"), "--out", str(out)]) == 0
    lines = [json.loads(line) for line in out.read_text().splitlines()]
    assert [(r["kind"], r["bundle"]) for r in lines] == [
        ("episode", "complete"), ("episode", "censored")
    ]


def test_cli_appends_arm_delta_line_when_both_arms_given(tmp_path):
    out = tmp_path / "r.jsonl"
    args = ["--arm-a", str(DATA / "detection"), "--arm-b", str(DATA / "detection"),
            "--reps", "20", "--out", str(out)]
    assert main(args) == 0
    lines = [json.loads(line) for line in out.read_text().splitlines()]
    assert lines[-1]["kind"] == "arm_delta"


def test_cli_writes_not_an_episode_line_for_bring_up_abort(tmp_path):
    abort = tmp_path / "attempt_f1"
    (abort / "decisions").mkdir(parents=True)
    out = tmp_path / "r.jsonl"
    assert main([str(abort), str(DATA / "complete"), "--out", str(out)]) == 0
    kinds = [json.loads(line)["kind"] for line in out.read_text().splitlines()]
    assert kinds == ["not_an_episode", "episode"]


def test_cli_exits_2_when_only_one_arm_given(tmp_path):
    assert main(["--arm-a", str(DATA / "detection"), "--out", str(tmp_path / "r.jsonl")]) == 2


@pytest.mark.skipif(not os.environ.get(GOLDEN_ENV), reason=f"{GOLDEN_ENV} not set")
def test_golden_e24_pilot_bundle_matches_frozen_values():
    golden = json.loads((DATA / "golden_e24.json").read_text())
    e = score_bundle(Path(os.environ[GOLDEN_ENV]))
    assert e.seed == golden["seed"]
    assert e.gt_offset_s == golden["gt_offset_s"]
    assert e.t_end_rel == pytest.approx(golden["t_end_rel"], abs=1e-3)
    assert e.censor_reason == golden["censor_reason"]
    assert e.completeness.tasks_completed == golden["tasks_completed"]
    assert e.throughput.completion_times_s == pytest.approx(golden["completion_times_s"], abs=1e-3)
    assert len(e.delay.segments) == golden["n_segments"]
    got = [(round(c.conflict.onset_s, 3), list(c.conflict.involved), c.detected, c.type_label)
           for c in e.conflicts.conflicts]
    assert got == [(c["onset_s"], c["involved"], c["detected"], c["type_label"])
                   for c in golden["conflicts"]]
    assert [a.analysis_class for a in e.conflicts.analyses] == golden["analysis_classes"]
    assert e.conflicts.run_plan_quality.provenance_counts == golden["run_provenance_counts"]

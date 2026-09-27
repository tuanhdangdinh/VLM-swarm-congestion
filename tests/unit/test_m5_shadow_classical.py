"""Unit tests for M5's Arm B shadow: snapshot buffer, conversion, record, artifact."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from swarm_orchestrator.models import (
    PipelineOutcome,
    RobotView,
    SceneSnapshot,
    TerminalStage,
    load_config,
)
from swarm_orchestrator.reasoning_pipeline import write_decision_artifact
from swarm_orchestrator.shadow_classical import (
    ClassicalParamsSource,
    ClassicalShadow,
    ShadowClassicalRecord,
    SnapshotRingBuffer,
    format_shadow_log,
    load_shadow_params,
    snapshot_to_frame,
)

from reasoning.baselines import ClassicalParams, ConflictZone
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)

_GOALS = {"robot_1": (2.5, 0.0), "robot_2": (-2.5, 0.0)}


def _goal_of(robot_id: str) -> tuple[float, float] | None:
    return _GOALS.get(robot_id)


def _view(rid: str, x: float, theta: float, v: float, status: str, stamp: float) -> RobotView:
    return RobotView(
        robot_id=rid, x=x, y=0.0, theta=theta, linear_velocity=v, status=status, stamp=stamp
    )


def _scene(stamp: float, *robots: RobotView, dropped: bool = False) -> SceneSnapshot:
    return SceneSnapshot(stamp=stamp, frame_id="cam0", robots=list(robots), dropped_frame=dropped)


def _frame(stamp: float) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=stamp,
        robots=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )


def _head_on_history() -> list[SceneSnapshot]:
    """robot_1 is inside the zone at t=0; robot_2 enters at t=3; both stop by t=10."""
    scenes = []
    for step in range(0, 10):
        t = float(step)
        x1 = min(-1.4 + 0.12 * step, -0.3)
        x2 = max(2.0 - 0.2 * step, 0.3)
        scenes.append(
            _scene(
                t,
                _view("robot_1", x1, 0.0, 0.12, "MOVING", t),
                _view("robot_2", x2, math.pi, 0.2, "MOVING", t),
            )
        )
    return scenes


def _trigger_scene(stamp: float = 10.0) -> SceneSnapshot:
    return _scene(
        stamp,
        _view("robot_1", -0.3, 0.0, 0.0, "STOPPED", stamp),
        _view("robot_2", 0.3, math.pi, 0.0, "STOPPED", stamp),
    )


def _params_source() -> ClassicalParamsSource:
    return ClassicalParamsSource(
        path="config/rag.yaml", section_present=True, params=ClassicalParams(), error=None
    )


def _shadow(**kwargs) -> ClassicalShadow:
    base = {
        "params_source": _params_source(),
        "zones": (),
        "window_sec": 60.0,
        "sample_period_sec": 0.25,
    }
    base.update(kwargs)
    return ClassicalShadow(**base)


def _fed_shadow(**kwargs) -> ClassicalShadow:
    shadow = _shadow(**kwargs)
    for scene in _head_on_history():
        shadow.observe(scene, _goal_of)
    return shadow


def _vlm_decision(
    yield_robot: str | None = "robot_2", strategy: str = "yield"
) -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on",
        strategy=strategy,
        justification="vlm",
        yield_robot=yield_robot,
    )


def _evaluated(shadow: ClassicalShadow, request_id: str = "r1", episode: int = 0):
    return shadow.evaluate(request_id, _trigger_scene(), _goal_of, episode)


# ---- SnapshotRingBuffer ----


def test_buffer_stores_first_frame_when_empty():
    buffer = SnapshotRingBuffer(window_sec=60.0, sample_period_sec=0.25)
    assert buffer.add(_frame(1.0)) is True
    assert len(buffer) == 1


def test_buffer_skips_frame_when_within_sample_period():
    buffer = SnapshotRingBuffer(window_sec=60.0, sample_period_sec=0.25)
    buffer.add(_frame(1.0))
    assert buffer.add(_frame(1.1)) is False
    assert len(buffer) == 1


def test_buffer_stores_frame_when_sample_period_elapsed():
    buffer = SnapshotRingBuffer(window_sec=60.0, sample_period_sec=0.25)
    buffer.add(_frame(1.0))
    assert buffer.add(_frame(1.25)) is True
    assert [f.stamp for f in buffer.frames()] == [1.0, 1.25]


def test_buffer_expires_frames_when_older_than_window():
    buffer = SnapshotRingBuffer(window_sec=5.0, sample_period_sec=0.25)
    for stamp in (0.0, 2.0, 4.0, 6.0, 8.0):
        buffer.add(_frame(stamp))
    assert [f.stamp for f in buffer.frames()] == [4.0, 6.0, 8.0]


def test_buffer_clears_history_when_stamp_goes_backwards():
    buffer = SnapshotRingBuffer(window_sec=60.0, sample_period_sec=0.25)
    buffer.add(_frame(10.0))
    buffer.add(_frame(11.0))
    assert buffer.add(_frame(2.0)) is True
    assert [f.stamp for f in buffer.frames()] == [2.0]


def test_buffer_accepts_matches_add_decision():
    buffer = SnapshotRingBuffer(window_sec=60.0, sample_period_sec=0.25)
    buffer.add(_frame(1.0))
    assert buffer.accepts(1.1) is False
    assert buffer.accepts(1.3) is True


def test_buffer_frames_end_with_trigger_when_trigger_is_newer_than_tail():
    buffer = SnapshotRingBuffer(window_sec=60.0, sample_period_sec=0.25)
    buffer.add(_frame(1.0))
    buffer.add(_frame(1.25))
    assert [f.stamp for f in buffer.frames(latest=_frame(1.3))] == [1.0, 1.25, 1.3]
    assert len(buffer) == 2


def test_buffer_frames_end_with_trigger_when_tail_is_newer_than_trigger():
    buffer = SnapshotRingBuffer(window_sec=60.0, sample_period_sec=0.25)
    for stamp in (1.0, 1.25, 1.5):
        buffer.add(_frame(stamp))
    assert [f.stamp for f in buffer.frames(latest=_frame(1.25))] == [1.0, 1.25]


def test_buffer_frames_expire_relative_to_trigger():
    buffer = SnapshotRingBuffer(window_sec=5.0, sample_period_sec=0.25)
    for stamp in (0.0, 2.0, 4.0):
        buffer.add(_frame(stamp))
    assert [f.stamp for f in buffer.frames(latest=_frame(6.5))] == [2.0, 4.0, 6.5]


@pytest.mark.parametrize("window, period", [(0.0, 0.25), (60.0, 0.0), (1.0, 1.0)])
def test_buffer_rejects_invalid_window_or_period(window, period):
    with pytest.raises(ValueError):
        SnapshotRingBuffer(window_sec=window, sample_period_sec=period)


# ---- snapshot_to_frame ----


def test_snapshot_to_frame_maps_pose_velocity_status_and_goal():
    frame = snapshot_to_frame(_trigger_scene(), _goal_of)
    robot = frame.find_robot("robot_2")
    assert frame.stamp == 10.0
    assert (robot.x, robot.y, robot.theta) == (0.3, 0.0, math.pi)
    assert robot.linear_velocity == 0.0
    assert robot.status == "STOPPED"
    assert robot.goal == (-2.5, 0.0)


def test_snapshot_to_frame_passes_m1_velocity_through_unscaled():
    scene = _scene(1.0, _view("robot_1", 0.0, 0.0, 0.07, "MOVING", 1.0))
    assert snapshot_to_frame(scene, _goal_of).robots[0].linear_velocity == 0.07


def test_snapshot_to_frame_leaves_goal_none_when_registry_has_no_goal():
    scene = _scene(1.0, _view("robot_9", 0.0, 0.0, 0.0, "STOPPED", 1.0))
    assert snapshot_to_frame(scene, _goal_of).robots[0].goal is None


# ---- load_shadow_params ----


def test_load_shadow_params_reads_classical_section(tmp_path):
    path = tmp_path / "rag.yaml"
    path.write_text("classical:\n  r_conflict_m: 1.2\n", encoding="utf-8")
    source = load_shadow_params(path)
    assert source.section_present is True
    assert source.error is None
    assert source.params.r_conflict_m == 1.2
    assert source.path == str(path)


def test_load_shadow_params_records_error_when_section_missing(tmp_path):
    path = tmp_path / "rag.yaml"
    path.write_text("rag:\n  top_k: 3\n", encoding="utf-8")
    source = load_shadow_params(path)
    assert source.section_present is False
    assert source.params is None
    assert "classical" in source.error


def test_load_shadow_params_records_error_when_file_missing(tmp_path):
    source = load_shadow_params(tmp_path / "absent.yaml")
    assert source.params is None
    assert "not found" in source.error


def test_load_shadow_params_raises_when_section_invalid(tmp_path):
    path = tmp_path / "rag.yaml"
    path.write_text("classical:\n  r_conflict_mm: 1.2\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_shadow_params(path)


def test_load_shadow_params_reads_repo_config():
    source = load_shadow_params(Path("config/rag.yaml"))
    assert source.error is None
    assert source.params == ClassicalParams()


# ---- OrchestratorConfig shadow keys ----


def _config_raw(**overrides) -> dict:
    raw = {
        "stall_threshold_sec": 12.0,
        "progress_epsilon_m": 0.1,
        "cooldown_sec": 15.0,
        "command_timeout_sec": 20.0,
        "reasoning_backend_id": "mock",
        "frame_dump_dir": "/tmp/frames",
        "initial_tasks": {"robot_1": {"task": "t", "goal": [2.5, 0.0]}},
    }
    raw.update(overrides)
    return raw


def test_config_enables_shadow_by_default():
    config = load_config(_config_raw())
    assert config.shadow_classical is True
    assert config.shadow_classical_window_sec == 60.0
    assert config.shadow_classical_sample_period_sec == 0.25
    assert config.shadow_classical_params_path == "config/rag.yaml"
    assert config.shadow_classical_zones == ()


def test_config_rejects_window_when_not_above_stall_threshold():
    with pytest.raises(ValidationError):
        load_config(_config_raw(shadow_classical_window_sec=12.0))


def test_config_accepts_short_window_when_shadow_disabled():
    config = load_config(_config_raw(shadow_classical=False, shadow_classical_window_sec=5.0))
    assert config.shadow_classical is False


def test_config_parses_mapped_zones():
    config = load_config(
        _config_raw(
            shadow_classical_zones=[{"zone_id": "cross", "x": 0.0, "y": 1.0, "radius_m": 1.5}]
        )
    )
    assert config.shadow_classical_zones == (
        ConflictZone(zone_id="cross", x=0.0, y=1.0, radius_m=1.5),
    )


def test_repo_orchestrator_yaml_enables_shadow():
    path = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
    config = load_config(yaml.safe_load(path.read_text(encoding="utf-8")))
    assert config.shadow_classical is True
    assert config.shadow_classical_zones == ()


# ---- ClassicalShadow ----


def test_shadow_rejects_sample_period_when_not_below_arrival_tie():
    with pytest.raises(ValueError):
        _shadow(sample_period_sec=1.0)


def test_shadow_records_head_on_yield_for_normal_decision():
    record = _evaluated(_fed_shadow())
    assert record.shadow_error is None
    assert record.classification.scenario == "head_on"
    assert record.classification.blocker_kind == "robot"
    assert record.decision.strategy == "yield"
    assert record.passing_order == ["robot_1", "robot_2"]
    assert record.decision.yield_robot == "robot_2"
    assert record.params == ClassicalParams()
    assert record.params_path == "config/rag.yaml"
    assert record.comparison is None


def test_shadow_records_buffer_extent_for_censoring_checks():
    record = _evaluated(_fed_shadow())
    assert record.frame_count == 11
    assert record.oldest_stamp == 0.0
    assert record.latest_stamp == 10.0


def test_shadow_flags_censored_arrival_when_robot_starts_inside_zone():
    # _head_on_history: robot_1 is 1.4 m from the (0, 0) pair midpoint at the
    # oldest frame (inside r_conflict_m 1.5); robot_2 enters at t=3.
    record = _evaluated(_fed_shadow())
    assert record.censored_arrivals == ["robot_1"]
    # Flag only: the FCFS answer is unchanged.
    assert record.passing_order == ["robot_1", "robot_2"]
    assert record.decision.yield_robot == "robot_2"
    assert record.shadow_error is None


def test_shadow_flags_no_censored_arrival_when_both_robots_enter_in_window():
    shadow = _shadow()
    for step in range(0, 10):
        t = float(step)
        shadow.observe(
            _scene(
                t,
                _view("robot_1", min(-2.0 + 0.2 * step, -0.3), 0.0, 0.2, "MOVING", t),
                _view("robot_2", max(2.4 - 0.2 * step, 0.3), math.pi, 0.2, "MOVING", t),
            ),
            _goal_of,
        )
    record = _evaluated(shadow)
    assert record.oldest_stamp == 0.0
    assert record.censored_arrivals == []
    assert record.passing_order == ["robot_1", "robot_2"]


def test_shadow_leaves_censored_arrivals_unset_without_conflict_zone():
    shadow = _shadow()
    scene = _scene(1.0, _view("robot_1", 0.0, 0.0, 0.0, "STOPPED", 1.0))
    record = shadow.evaluate("r1", scene, _goal_of, 0)
    assert record.classification.scenario == "blocked_path"
    assert record.censored_arrivals is None


def test_shadow_keeps_decision_when_censoring_check_raises(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("table exploded")

    monkeypatch.setattr("swarm_orchestrator.shadow_classical.find_censored_arrivals", boom)
    record = _evaluated(_fed_shadow())
    assert record.decision.yield_robot == "robot_2"
    assert record.censored_arrivals is None
    assert "censoring check failed" in record.shadow_error


def test_shadow_record_validates_artifact_without_censored_arrivals():
    data = _evaluated(_fed_shadow()).model_dump(mode="json")
    del data["censored_arrivals"]
    assert ShadowClassicalRecord.model_validate(data).censored_arrivals is None


def test_shadow_classifies_trigger_snapshot_when_buffer_tail_is_older():
    shadow = _fed_shadow()
    # Only the trigger shows both robots stopped; the buffered tail has them moving.
    record = shadow.evaluate("r1", _trigger_scene(9.1), _goal_of, 0)
    assert record.classification.scenario == "head_on"
    assert record.latest_stamp == 9.1


def test_shadow_skips_dropped_frames():
    shadow = _shadow()
    shadow.observe(_trigger_scene(1.0), _goal_of)
    shadow.observe(_scene(2.0, dropped=True), _goal_of)
    record = shadow.evaluate("r1", _scene(3.0, dropped=True), _goal_of, 0)
    assert record.frame_count == 1
    assert record.classification.scenario == "head_on"


def test_shadow_counts_prior_attempts_within_episode():
    shadow = _fed_shadow()
    first = _evaluated(shadow, "r1", episode=0)
    second = _evaluated(shadow, "r2", episode=0)
    assert (first.prior_attempts, second.prior_attempts) == (0, 1)
    assert second.prior_attempts_source == "episode_analyses"


def test_shadow_resets_prior_attempts_on_new_episode():
    shadow = _fed_shadow()
    _evaluated(shadow, "r1", episode=0)
    assert _evaluated(shadow, "r2", episode=1).prior_attempts == 0


def test_shadow_flags_no_disagreement_when_vlm_agrees():
    shadow = _fed_shadow()
    record = shadow.finalize(_evaluated(shadow), _vlm_decision("robot_2"), "none")
    assert record.comparison.comparable is True
    assert record.comparison.disagreement.any_disagreement is False


def test_shadow_flags_disagreement_when_vlm_names_other_yielder():
    shadow = _fed_shadow()
    record = shadow.finalize(_evaluated(shadow), _vlm_decision("robot_1"), "none")
    disagreement = record.comparison.disagreement
    assert disagreement.yielder_match is False
    assert disagreement.strategy_match is True
    assert disagreement.any_disagreement is True


def test_shadow_compares_vlm_no_congestion_decision():
    shadow = _fed_shadow()
    vlm = CongestionDecision(
        congestion_detected=False, type="none", involved_robots=[],
        root_cause="clear", strategy="none", justification="vlm",
    )
    record = shadow.finalize(_evaluated(shadow), vlm, "congestion_detected=false")
    assert record.comparison.comparable is True
    assert record.comparison.disagreement.strategy_match is False


def test_shadow_marks_not_comparable_when_vlm_decision_is_none():
    shadow = _fed_shadow()
    record = shadow.finalize(_evaluated(shadow), None, "decision=None")
    assert record.decision.strategy == "yield"
    assert record.comparison.comparable is False
    assert record.comparison.disagreement is None
    assert "decision=None" in record.comparison.reason


def test_shadow_records_error_when_resolver_raises():
    def boom(*_args, **_kwargs):
        raise RuntimeError("classifier exploded")

    shadow = _fed_shadow(resolve_fn=boom)
    record = shadow.finalize(_evaluated(shadow), _vlm_decision(), "none")
    assert "classifier exploded" in record.shadow_error
    assert record.decision is None
    assert record.comparison.comparable is False


def test_shadow_records_error_when_comparison_raises():
    def boom(*_args, **_kwargs):
        raise RuntimeError("compare exploded")

    shadow = _fed_shadow(compare_fn=boom)
    record = shadow.finalize(_evaluated(shadow), _vlm_decision(), "none")
    assert "compare exploded" in record.shadow_error
    assert record.decision.strategy == "yield"
    assert record.comparison.comparable is False


def test_shadow_records_error_when_params_unavailable():
    source = ClassicalParamsSource(
        path="config/rag.yaml", section_present=False, params=None,
        error="classical params unavailable: no `classical:` section in config/rag.yaml",
    )
    shadow = _fed_shadow(params_source=source)
    record = _evaluated(shadow)
    assert shadow.params_error == source.error
    assert "no `classical:` section" in record.shadow_error
    assert record.decision is None
    assert record.params_section_present is False


def test_shadow_records_error_when_no_frames_available():
    record = _shadow().evaluate("r1", _scene(1.0, dropped=True), _goal_of, 0)
    assert record.shadow_error is not None
    assert record.frame_count == 0


def test_shadow_observe_records_feed_error_without_raising():
    def broken_goal(_robot_id):
        raise KeyError("registry gone")

    shadow = _shadow()
    shadow.observe(_trigger_scene(1.0), broken_goal)
    shadow.observe(_trigger_scene(2.0), _goal_of)
    record = shadow.evaluate("r1", _trigger_scene(3.0), _goal_of, 0)
    assert record.feed_errors == 1
    assert "registry gone" in record.last_feed_error
    assert record.shadow_error is None


def test_shadow_feed_error_count_resets_after_evaluation():
    def broken_goal(_robot_id):
        raise KeyError("registry gone")

    shadow = _shadow()
    shadow.observe(_trigger_scene(1.0), broken_goal)
    _evaluated(shadow, "r1")
    assert _evaluated(shadow, "r2").feed_errors == 0


def test_shadow_passes_configured_zones_to_resolver():
    seen = {}

    def spy(frames, zones, params, prior_attempts):
        seen["zones"] = list(zones)
        from reasoning.baselines import resolve_classical

        return resolve_classical(frames, zones, params, prior_attempts)

    zone = ConflictZone(zone_id="cross", x=5.0, y=5.0, radius_m=1.0)
    record = _evaluated(_fed_shadow(zones=(zone,), resolve_fn=spy))
    assert seen["zones"] == [zone]
    assert record.zone_ids == ["cross"]


# ---- format_shadow_log ----


def test_format_shadow_log_names_scenario_strategy_yielder_and_disagreement():
    shadow = _fed_shadow()
    record = shadow.finalize(_evaluated(shadow), _vlm_decision("robot_1"), "none")
    assert format_shadow_log(record) == (
        "shadow request=r1 scenario=head_on strategy=yield yield=robot_2 disagree=true"
    )


def test_format_shadow_log_reports_not_comparable_as_na():
    shadow = _fed_shadow()
    record = shadow.finalize(_evaluated(shadow), None, "decision=None")
    assert format_shadow_log(record).endswith("disagree=n/a")


def test_format_shadow_log_reports_error():
    def boom(*_args, **_kwargs):
        raise RuntimeError("classifier exploded")

    shadow = _fed_shadow(resolve_fn=boom)
    record = shadow.finalize(_evaluated(shadow), _vlm_decision(), "none")
    line = format_shadow_log(record)
    assert line.startswith("shadow request=r1 scenario=none strategy=none yield=none disagree=n/a")
    assert "error=" in line and "classifier exploded" in line


# ---- decision artifact ----


def _outcome() -> PipelineOutcome:
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    result = ReasonerResult(
        request_id="r1", decision=_vlm_decision("robot_1"), raw_text="{}", diagnostics=diag
    )
    return PipelineOutcome(
        request_id="r1", reasoner_result=result, grounded_command=None,
        terminal_stage=TerminalStage.GROUNDING, failure_reason="grounding failed: x",
    )


def _artifact(tmp_path: Path, name: str, shadow_block) -> dict:
    out = tmp_path / name
    path = write_decision_artifact(out, _outcome(), shadow_classical=shadow_block)
    return json.loads(path.read_text(encoding="utf-8"))


def test_write_decision_artifact_round_trips_shadow_classical_block(tmp_path):
    shadow = _fed_shadow()
    record = shadow.finalize(_evaluated(shadow), _vlm_decision("robot_1"), "none")
    data = _artifact(tmp_path, "a", record.model_dump(mode="json"))
    assert ShadowClassicalRecord.model_validate(data["shadow_classical"]) == record
    assert data["shadow_classical"]["passing_order"] == ["robot_1", "robot_2"]


def test_write_decision_artifact_writes_null_shadow_classical_when_disabled(tmp_path):
    assert _artifact(tmp_path, "a", None)["shadow_classical"] is None


def test_shadow_error_leaves_rest_of_artifact_unchanged(tmp_path):
    def boom(*_args, **_kwargs):
        raise RuntimeError("classifier exploded")

    good = _fed_shadow()
    good_record = good.finalize(_evaluated(good), _vlm_decision("robot_1"), "none")
    bad = _fed_shadow(resolve_fn=boom)
    bad_record = bad.finalize(_evaluated(bad), _vlm_decision("robot_1"), "none")
    with_good = _artifact(tmp_path, "good", good_record.model_dump(mode="json"))
    with_bad = _artifact(tmp_path, "bad", bad_record.model_dump(mode="json"))
    without = _artifact(tmp_path, "none", None)
    assert with_bad["shadow_classical"]["shadow_error"] is not None
    for key in without:
        if key == "shadow_classical":
            continue
        assert with_bad[key] == without[key] == with_good[key], key
    assert with_bad["decision"]["yield_robot"] == "robot_1"

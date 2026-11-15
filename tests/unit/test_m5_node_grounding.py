"""Node-level tests for M5's grounding-params startup and stage-2 logging (ROS2 stubbed)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import PipelineOutcome, RetreatStage2Record

from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _artifact,
    _config,
    _FakePipeline,
    _make_node,
    _ok_outcome,
    _trigger_real,
    node_env,
)


def _node(node_env, tmp_path, **overrides):  # noqa: F811
    node_module, _clock = node_env
    return node_module.OrchestratorNode(
        config=_config(tmp_path, t0_probe_mode=False, **overrides), pipeline=_FakePipeline()
    )


def test_startup_fails_fast_on_a_missing_grounding_file(node_env, tmp_path):  # noqa: F811
    with pytest.raises(FileNotFoundError, match="grounding params"):
        _node(node_env, tmp_path, grounding_params_path=str(tmp_path / "absent.yaml"))


def test_startup_fails_fast_on_an_invalid_grounding_section(node_env, tmp_path):  # noqa: F811
    bad = tmp_path / "rag.yaml"
    bad.write_text("grounding:\n  mode: derived\n  backup_band_m: [2.0, 0.5]\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        _node(node_env, tmp_path, grounding_params_path=str(bad))


def test_startup_logs_the_grounding_mode(node_env, tmp_path):  # noqa: F811
    path = tmp_path / "rag.yaml"
    path.write_text("grounding:\n  mode: derived\n", encoding="utf-8")
    node = _node(node_env, tmp_path, grounding_params_path=str(path),
                 stage2_retreat_selection=False)
    [line] = node.get_logger().matching("grounding mode=")
    assert line == (
        f"grounding mode=derived params={path} section_present=True "
        "aisle_y_band_m=None band_override=False stage2_retreat_selection=False"
    )


def test_startup_logs_the_escort_obstacle_guard_when_on(node_env, tmp_path):  # noqa: F811
    path = tmp_path / "rag.yaml"
    path.write_text(
        "grounding:\n  mode: derived\n  escort_obstacle_guard: true\n", encoding="utf-8"
    )
    node = _node(node_env, tmp_path, grounding_params_path=str(path),
                 stage2_retreat_selection=False)
    [line] = node.get_logger().matching("grounding mode=")
    assert line.endswith("stage2_retreat_selection=False escort_obstacle_guard=True")


def test_startup_logs_the_reverse_obstacle_guard_when_on(node_env, tmp_path):  # noqa: F811
    path = tmp_path / "rag.yaml"
    path.write_text(
        "grounding:\n  mode: derived\n  reverse_obstacle_guard: true\n", encoding="utf-8"
    )
    node = _node(node_env, tmp_path, grounding_params_path=str(path),
                 stage2_retreat_selection=False)
    [line] = node.get_logger().matching("grounding mode=")
    assert line.endswith("stage2_retreat_selection=False reverse_obstacle_guard=True")


def test_startup_logs_both_obstacle_guards_when_on(node_env, tmp_path):  # noqa: F811
    path = tmp_path / "rag.yaml"
    path.write_text(
        "grounding:\n  mode: derived\n  escort_obstacle_guard: true\n"
        "  reverse_obstacle_guard: true\n",
        encoding="utf-8",
    )
    node = _node(node_env, tmp_path, grounding_params_path=str(path),
                 stage2_retreat_selection=False)
    [line] = node.get_logger().matching("grounding mode=")
    assert line.endswith("escort_obstacle_guard=True reverse_obstacle_guard=True")


def test_startup_applies_and_logs_a_per_scenario_band(node_env, tmp_path):  # noqa: F811
    path = tmp_path / "rag.yaml"
    path.write_text("grounding:\n  mode: derived\n", encoding="utf-8")
    node = _node(node_env, tmp_path, grounding_params_path=str(path),
                 grounding_aisle_y_band_m=(-0.55, 1.0))
    assert node._grounding.params.aisle_y_band_m == (-0.55, 1.0)
    assert node._grounding.aisle_y_band_override_m == (-0.55, 1.0)
    [line] = node.get_logger().matching("grounding mode=")
    assert "aisle_y_band_m=(-0.55, 1.0) band_override=True" in line


def test_startup_applies_and_logs_a_per_scenario_x_band(node_env, tmp_path):  # noqa: F811
    path = tmp_path / "rag.yaml"
    path.write_text("grounding:\n  mode: derived\n", encoding="utf-8")
    node = _node(node_env, tmp_path, grounding_params_path=str(path),
                 grounding_aisle_x_band_m=(-0.46, 0.46))
    assert node._grounding.params.aisle_x_band_m == (-0.46, 0.46)
    assert node._grounding.params.aisle_y_band_m is None
    [line] = node.get_logger().matching("grounding mode=")
    assert "band_override=False aisle_x_band_m=(-0.46, 0.46) stage2" in line


def test_startup_fails_fast_on_an_inverted_band(node_env, tmp_path):  # noqa: F811
    with pytest.raises(ValidationError, match="aisle_y_band_m"):
        _node(node_env, tmp_path, grounding_aisle_y_band_m=(1.0, -0.55))


def test_missing_grounding_section_warns(node_env, tmp_path):  # noqa: F811
    path = tmp_path / "rag.yaml"
    path.write_text("rag:\n  top_k: 3\n", encoding="utf-8")
    node = _node(node_env, tmp_path, grounding_params_path=str(path))
    assert node.get_logger().matching("no `grounding:` section")


class _Stage2Pipeline(_FakePipeline):
    def run(self, request):
        super().run(request)
        outcome = _ok_outcome(request.request_id)
        return PipelineOutcome(
            **{
                **outcome.model_dump(),
                "stage2": RetreatStage2Record(
                    status="skipped", skip_reason="no_backend", default_label="A"
                ),
            }
        )


def test_triggered_artifact_records_grounding_and_logs_stage2(node_env, tmp_path):  # noqa: F811
    pipeline = _Stage2Pipeline()
    node, _clock = _make_node(node_env, tmp_path, pipeline, t0_probe_mode=False)

    _trigger_real(node)
    node._future.result(timeout=WAIT_SEC)
    node._on_timer()

    request_id = pipeline.run_calls[0]
    payload = _artifact(node, request_id)
    assert payload["grounding_mode"] == node._grounding.params.mode
    assert payload["grounding_params_source"]["path"] == "config/rag.yaml"
    assert payload["stage2"]["skip_reason"] == "no_backend"
    [line] = node.get_logger().matching("stage2 request=")
    assert f"stage2 request={request_id} status=skipped skip_reason=no_backend" in line


def test_default_pipeline_runs_the_shipped_grounding_mode(node_env, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.delenv("VGU_MOCK_DECISION_FILE", raising=False)
    monkeypatch.delenv("VGU_MOCK_RETREAT_CHOICE_FILE", raising=False)
    node_module, _clock = node_env
    node = node_module.OrchestratorNode(config=_config(tmp_path, t0_probe_mode=False))
    assert node._grounding.params.mode == "derived"
    assert node._pipeline._grounding_params == node._grounding.params
    # A mock with no stage-2 script cannot answer: the call is skipped.
    assert node._pipeline._retreat_chooser is None
    assert node._pipeline._stage2_enabled is True


def test_default_pipeline_gets_a_scripted_mock_stage2(node_env, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv(
        "VGU_MOCK_RETREAT_CHOICE_FILE", "config/mock_decisions/retreat_choice_b.json"
    )
    node_module, _clock = node_env
    node = node_module.OrchestratorNode(config=_config(tmp_path, t0_probe_mode=False))
    assert type(node._pipeline._retreat_chooser).__name__ == "RetreatChooser"


_REPO_CALIBRATION = "ros2_ws/src/swarm_perception/config/calibration.yaml"


def test_default_pipeline_draws_with_the_configured_calibration(node_env, tmp_path):  # noqa: F811
    node_module, _clock = node_env
    node = node_module.OrchestratorNode(
        config=_config(tmp_path, t0_probe_mode=False, stage2_calibration_path=_REPO_CALIBRATION)
    )
    assert node._marker.available
    assert node._pipeline._candidate_marker is node._marker
    assert node.get_logger().matching("stage2 marks enabled")


def test_missing_calibration_warns_and_still_starts(node_env, tmp_path):  # noqa: F811
    node_module, _clock = node_env
    node = node_module.OrchestratorNode(
        config=_config(
            tmp_path, t0_probe_mode=False, stage2_calibration_path=str(tmp_path / "absent.yaml")
        )
    )
    assert not node._marker.available
    [line] = node.get_logger().matching("stage2 marks unavailable")
    assert "calibration_unavailable" in line


def test_cleanup_removes_the_stage2_image(node_env, tmp_path):  # noqa: F811
    node = _node(node_env, tmp_path)
    frames = tmp_path / "frames"
    frames.mkdir(exist_ok=True)
    for name in ("r7.png", "r7_stage2.png"):
        (frames / name).write_bytes(b"png")
    node._cleanup_frame("r7")
    assert list(frames.iterdir()) == []


def test_cleanup_keeps_the_stage2_image_with_debug_frames(node_env, tmp_path):  # noqa: F811
    node = _node(node_env, tmp_path, keep_debug_frames=True)
    frames = tmp_path / "frames"
    frames.mkdir(exist_ok=True)
    (frames / "r7_stage2.png").write_bytes(b"png")
    node._cleanup_frame("r7")
    assert (frames / "r7_stage2.png").exists()


def test_stage2_budget_replaces_the_stage1_budget(node_env, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv(
        "VGU_MOCK_RETREAT_CHOICE_FILE", "config/mock_decisions/retreat_choice_b.json"
    )
    node_module, _clock = node_env
    node = node_module.OrchestratorNode(
        config=_config(
            tmp_path, t0_probe_mode=False, stage2_max_attempts=3, stage2_timeout_sec=5.5
        )
    )
    stage2 = node._pipeline._retreat_chooser.config
    assert (stage2.max_attempts, stage2.timeout_sec) == (3, 5.5)
    stage1 = node._pipeline._reasoner._config
    assert (stage1.max_attempts, stage1.timeout_sec) != (3, 5.5)
    # Sampling is still stage 1's.
    assert stage2.temperature == stage1.temperature


def test_stage2_budget_defaults_are_two_by_eight(node_env, tmp_path):  # noqa: F811
    config = _config(tmp_path, t0_probe_mode=False)
    assert (config.stage2_max_attempts, config.stage2_timeout_sec) == (2, 8.0)
    # The worst case fits inside one M5 command window.
    assert config.stage2_max_attempts * config.stage2_timeout_sec < config.command_timeout_sec


def test_shipped_config_bounds_stage2(node_env):  # noqa: F811
    import yaml
    from swarm_orchestrator.models import load_config

    raw = yaml.safe_load(
        open("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml", encoding="utf-8")
    )
    config = load_config(raw)
    assert (config.stage2_max_attempts, config.stage2_timeout_sec) == (2, 8.0)
    assert config.stage2_calibration_path is None


def test_letter_draws_use_the_run_seed(node_env, tmp_path):  # noqa: F811
    node_module, _clock = node_env
    node = node_module.OrchestratorNode(
        config=_config(tmp_path, t0_probe_mode=False, prompt_robot_order_seed=1234)
    )
    assert node._pipeline._stage2_letter_seed == 1234 == node._order_seed


def test_shadow_gets_the_pipeline_grounding_context(node_env, tmp_path):  # noqa: F811
    node = _node(node_env, tmp_path, shadow_classical=True)
    context = node._shadow._retreat_context
    assert context.params == node._grounding.params
    assert context.geometry == node._config.scenario_geometry
    assert context.yield_feasibility_mode == node._config.grounding_yield_feasibility

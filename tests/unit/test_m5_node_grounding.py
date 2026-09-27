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
        "stage2_retreat_selection=False"
    )


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

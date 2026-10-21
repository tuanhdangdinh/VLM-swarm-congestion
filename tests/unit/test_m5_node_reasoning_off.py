"""Tests for prereg-v3 Arm B, the Layer-2-off switch (`reasoning_enabled: false`).

The pure gate (`resolve_layer2_gate`, `should_submit_pipeline`,
`reasoning_status_line`) is tested directly; the node tests use the ROS2
stand-ins of `test_m5_node_probe`, with the real detector, registry, arrival
gate, task stream and scene log.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml
from swarm_orchestrator.models import (
    REASONING_OFF_STATUS_LINE,
    ContradictionTriggerConfig,
    load_config,
    reasoning_status_line,
    resolve_layer2_gate,
    should_submit_pipeline,
)

from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    _config,
    _FakePipeline,
    _scene_msg,
    _snapshot,
    node_env,
)
from tests.unit.test_m5_node_task_stream import (
    STAGGER,
    _feed,
    _make,
    _nav2_success,
    _positions,
    _registry,
    _task,
    _tasks_log,
)

REPO = Path(__file__).resolve().parents[2]
PINNED_ORCH = REPO / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
_CONTRADICTION_ON = ContradictionTriggerConfig(
    enabled=True, divergence_bound_m=0.5, per_event_replan_budget=1
)


def _off_node(node_env, tmp_path, pipeline=None, **overrides):  # noqa: F811
    node_module, clock = node_env
    overrides.setdefault("t0_probe_mode", False)
    config = _config(tmp_path, reasoning_enabled=False, **overrides)
    node = node_module.OrchestratorNode(config=config, pipeline=pipeline)
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    return node, clock


def _feed_stall(node, clock, scenes: int = 5) -> None:
    # A close, stopped pair that the detector flags at once with
    # stall_threshold_sec=0: on a reasoning-on node every scene would trigger.
    for k in range(scenes):
        stamp = 60.0 + k
        node._frame_stamp = stamp
        node._on_scene_state(_scene_msg(_snapshot(stamp, close=True)))
        clock.t += 1.0
        node._on_timer()


def _artifacts(tmp_path) -> list[Path]:
    return sorted((tmp_path / "decisions").glob("*.json"))


class TestConfigKey:
    def test_reasoning_enabled_defaults_true(self, tmp_path):
        assert _config(tmp_path).reasoning_enabled is True

    def test_pinned_orchestrator_yaml_parses_reasoning_enabled_true(self):
        config = load_config(yaml.safe_load(PINNED_ORCH.read_text()))
        assert config.reasoning_enabled is True

    def test_overlay_with_reasoning_enabled_false_parses_false(self):
        overlay = PINNED_ORCH.read_text() + "reasoning_enabled: false\n"
        config = load_config(yaml.safe_load(overlay))
        assert config.reasoning_enabled is False
        assert should_submit_pipeline(config) is False

    def test_reasoning_enabled_false_is_dumped_when_set(self, tmp_path):
        dumped = _config(tmp_path, reasoning_enabled=False).model_dump(mode="json")
        assert dumped["reasoning_enabled"] is False


class TestPureGate:
    def test_should_submit_pipeline_true_by_default(self, tmp_path):
        assert should_submit_pipeline(_config(tmp_path)) is True

    def test_should_submit_pipeline_false_when_reasoning_disabled(self, tmp_path):
        assert should_submit_pipeline(_config(tmp_path, reasoning_enabled=False)) is False

    def test_gate_keeps_each_flag_when_reasoning_enabled(self, tmp_path):
        config = _config(
            tmp_path, shadow_classical=True, t0_probe_mode=True,
            contradiction_trigger=_CONTRADICTION_ON,
        )
        gate = resolve_layer2_gate(config)
        assert (gate.shadow_classical, gate.t0_probe_mode, gate.contradiction_trigger) == (
            True, True, True,
        )
        assert gate.overridden == ()

    def test_gate_forces_every_path_off_when_reasoning_disabled(self, tmp_path):
        config = _config(
            tmp_path, reasoning_enabled=False, shadow_classical=True, t0_probe_mode=True,
            contradiction_trigger=_CONTRADICTION_ON,
        )
        gate = resolve_layer2_gate(config)
        assert (gate.shadow_classical, gate.t0_probe_mode, gate.contradiction_trigger) == (
            False, False, False,
        )
        assert gate.overridden == ("shadow_classical", "t0_probe_mode", "contradiction_trigger")

    def test_status_line_none_when_reasoning_enabled(self, tmp_path):
        assert reasoning_status_line(_config(tmp_path)) is None

    def test_status_line_literal_when_reasoning_disabled(self, tmp_path):
        line = reasoning_status_line(_config(tmp_path, reasoning_enabled=False))
        assert line == REASONING_OFF_STATUS_LINE
        assert line.startswith("reasoning_enabled=false layer2=off ")


class TestNoPipeline:
    def test_stall_scenes_submit_no_pipeline_when_disabled(self, node_env, tmp_path):  # noqa: F811
        pipeline = _FakePipeline()
        node, clock = _off_node(node_env, tmp_path, pipeline)
        _feed_stall(node, clock)
        assert pipeline.run_calls == []
        assert pipeline.analyze_calls == []
        assert node._future is None

    def test_stall_scenes_log_no_analysis_when_disabled(self, node_env, tmp_path):  # noqa: F811
        node, clock = _off_node(node_env, tmp_path, _FakePipeline())
        _feed_stall(node, clock)
        assert node.get_logger().matching("starting analysis") == []
        assert node.get_logger().matching("trigger suppressed") == []

    def test_stall_scenes_write_no_artifact_or_command_when_disabled(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, clock = _off_node(node_env, tmp_path, _FakePipeline())
        _feed_stall(node, clock)
        assert _artifacts(tmp_path) == []
        assert node._cmd_pub.published == []

    def test_same_stall_scenes_do_submit_when_enabled(self, node_env, tmp_path):  # noqa: F811
        node_module, clock = node_env
        pipeline = _FakePipeline()
        config = _config(tmp_path, t0_probe_mode=False)
        node = node_module.OrchestratorNode(config=config, pipeline=pipeline)
        node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)
        node._frame_stamp = 60.0
        node._on_scene_state(_scene_msg(_snapshot(60.0, close=True)))
        assert node._future is not None

    def test_default_pipeline_never_built_when_disabled(
        self, node_env, tmp_path, monkeypatch  # noqa: F811
    ):
        node_module, clock = node_env
        built: list[str] = []

        def refuse(name):
            def _refuse(*_args, **_kwargs):
                built.append(name)
                raise AssertionError(f"{name} called with reasoning_enabled=false")
            return _refuse

        for name in ("_build_default_pipeline", "build_backend", "_load_vlm_config",
                     "_build_candidate_marker"):
            monkeypatch.setattr(node_module, name, refuse(name))
        node, clock = _off_node(node_env, tmp_path, pipeline=None)
        _feed_stall(node, clock)
        assert built == []
        assert node._pipeline is None
        assert node._marker is None

    def test_manual_trigger_rejected_when_disabled(self, node_env, tmp_path):  # noqa: F811
        pipeline = _FakePipeline()
        node, _clock = _off_node(node_env, tmp_path, pipeline)
        node._latest_snapshot = _snapshot(60.0, close=True)
        response = node._on_trigger_analysis(SimpleNamespace(reason="op"), SimpleNamespace())
        assert response.accepted is False
        assert response.message == "reasoning disabled (reasoning_enabled=false)"
        assert pipeline.run_calls == []

    def test_submit_pipeline_raises_when_disabled(self, node_env, tmp_path):  # noqa: F811
        node, _clock = _off_node(node_env, tmp_path, _FakePipeline())
        with pytest.raises(RuntimeError, match="reasoning_enabled=false"):
            node._submit_pipeline("req-x", _snapshot(60.0, close=True), ["robot_1"], {})

    def test_submit_probe_raises_when_disabled(self, node_env, tmp_path):  # noqa: F811
        node, _clock = _off_node(node_env, tmp_path, _FakePipeline())
        with pytest.raises(RuntimeError, match="reasoning_enabled=false"):
            node._submit_probe("req-p", 0, _snapshot(60.0))


class TestForcedOffPaths:
    def test_shadow_probe_and_contradiction_off_when_disabled(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, _clock = _off_node(
            node_env, tmp_path, _FakePipeline(), shadow_classical=True, t0_probe_mode=True,
            contradiction_trigger=_CONTRADICTION_ON,
        )
        assert node._shadow is None
        assert node._probe_scheduler is None
        assert node._probe_executor is None
        assert node._contradictions is None

    def test_no_probe_started_on_timer_when_disabled(self, node_env, tmp_path):  # noqa: F811
        pipeline = _FakePipeline()
        node, clock = _off_node(node_env, tmp_path, pipeline, t0_probe_mode=True)
        node._latest_snapshot = _snapshot(60.0)
        node._frame_stamp = 60.0
        clock.t += 100.0
        node._latest_snapshot_at = clock.t
        node._on_timer()
        assert node._probe is None
        assert pipeline.analyze_calls == []

    def test_forced_off_flags_warned_when_disabled(self, node_env, tmp_path):  # noqa: F811
        node, _clock = _off_node(
            node_env, tmp_path, _FakePipeline(), shadow_classical=True, t0_probe_mode=True,
        )
        assert node.get_logger().matching("shadow_classical is set but forced off")
        assert node.get_logger().matching("t0_probe_mode is set but forced off")


class TestStatusLine:
    def test_status_line_logged_once_when_disabled(self, node_env, tmp_path):  # noqa: F811
        node, clock = _off_node(node_env, tmp_path, _FakePipeline())
        _feed_stall(node, clock)
        assert node.get_logger().matching("reasoning_enabled=false") == [
            REASONING_OFF_STATUS_LINE
        ]

    def test_status_line_absent_when_enabled(self, node_env, tmp_path):  # noqa: F811
        node_module, _clock = node_env
        config = _config(tmp_path, t0_probe_mode=False)
        node = node_module.OrchestratorNode(config=config, pipeline=_FakePipeline())
        assert node.get_logger().matching("reasoning_enabled=") == []


class TestStillRuns:
    def test_scene_log_written_when_disabled(self, node_env, tmp_path):  # noqa: F811
        node, clock = _off_node(
            node_env, tmp_path, _FakePipeline(), scene_log_dir=str(tmp_path / "scene"),
        )
        _feed_stall(node, clock, scenes=2)
        lines = (tmp_path / "scene" / f"{node._session_id}.jsonl").read_text().splitlines()
        assert len(lines) >= 1
        assert json.loads(lines[0])["scene"]["robots"]

    def test_task_stream_releases_when_disabled(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _make(node_env, tmp_path, reasoning_enabled=False)
        _feed(node, 50.0, _positions(node))
        clock.t += STAGGER
        node._on_timer()
        assert "start_pending" not in _registry(node)["robot_2"]
        assert _tasks_log(node)[0]["event"] == "stream_start"
        assert [r["robot_id"] for r in _tasks_log(node) if r["event"] == "released"][-1] == (
            "robot_2"
        )

    def test_arrival_dwell_and_next_task_issue_when_disabled(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, _clock, pipeline = _make(node_env, tmp_path, reasoning_enabled=False)
        goal = _task(node, "robot_1", 0).goal
        _feed(node, 50.0, _positions(node, robot_1=goal))
        _nav2_success(node, "robot_1")
        _feed(node, 55.0, _positions(node, robot_1=goal))
        entry = _registry(node)["robot_1"]
        assert entry["goal"] == list(_task(node, "robot_1", 1).goal)
        events = [r["event"] for r in _tasks_log(node)]
        assert "arrived" in events
        assert "dwell_complete" in events
        assert pipeline.run_calls == []

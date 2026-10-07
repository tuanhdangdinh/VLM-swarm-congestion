"""Node-level tests for the v3 dispatch-off probe flag (`dispatch_enabled: false`).

The full triggered pipeline runs and its artifact is written; nothing reaches
M4. Uses the ROS2 stand-ins of `test_m5_node_probe`.
"""
from __future__ import annotations

import json

from swarm_orchestrator.models import PipelineOutcome, TerminalStage
from swarm_orchestrator.reasoning_pipeline import write_decision_artifact

from reasoning.rag.command_grounder import CommandGroundingError
from tests.unit.test_m5_node_junction_clear import (  # noqa: F401  (node_env is a fixture)
    _dispatch_via_handle_outcome,
    _node,
)
from tests.unit.test_m5_node_probe import (  # noqa: F401
    _DISPATCH_ARTIFACT_KEYS,
    _TRIGGERED_ARTIFACT_KEYS,
    WAIT_SEC,
    _artifact,
    _commands,
    _FakePipeline,
    _make_node,
    _ok_outcome,
    _result,
    _trigger_real,
    node_env,
)


def _off(node_env, tmp_path, pipeline=None, **overrides):  # noqa: F811
    pipeline = pipeline or _FakePipeline()
    node, clock = _make_node(
        node_env, tmp_path, pipeline, t0_probe_mode=False, dispatch_enabled=False, **overrides
    )
    return node, clock, pipeline


def _run_trigger(node, stamp: float = 60.0) -> None:
    _trigger_real(node, stamp)
    node._future.result(timeout=WAIT_SEC)
    node._on_timer()


class TestSuppression:
    def test_full_pipeline_runs_with_dispatch_off(self, node_env, tmp_path):  # noqa: F811
        node, _clock, pipeline = _off(node_env, tmp_path)
        _run_trigger(node)
        assert len(pipeline.run_calls) == 1

    def test_no_command_published(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _pipeline = _off(node_env, tmp_path)
        _run_trigger(node)
        assert _commands(node) == []

    def test_artifact_marks_dispatch_suppressed(self, node_env, tmp_path):  # noqa: F811
        node, _clock, pipeline = _off(node_env, tmp_path)
        _run_trigger(node)
        artifact = _artifact(node, pipeline.run_calls[0])
        assert artifact["dispatch_enabled"] is False
        assert artifact["dispatch_suppressed"] is True

    def test_artifact_keeps_full_provenance(self, node_env, tmp_path):  # noqa: F811
        node, _clock, pipeline = _off(node_env, tmp_path)
        _run_trigger(node)
        artifact = _artifact(node, pipeline.run_calls[0])
        assert set(artifact) == (
            _TRIGGERED_ARTIFACT_KEYS
            | _DISPATCH_ARTIFACT_KEYS
            | {"dispatch_enabled", "dispatch_suppressed"}
        )
        assert artifact["decision"]["strategy"] == "yield"
        assert artifact["prompt"]["user_prompt"]
        assert artifact["dispatched_robot_ids"] == ["robot_2", "robot_1"]

    def test_no_command_tracked_or_robots_busy(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _pipeline = _off(node_env, tmp_path)
        _run_trigger(node)
        assert node._tracker._records == {}
        assert node._busy_robots() == set()

    def test_no_attempt_recorded(self, node_env, tmp_path):  # noqa: F811
        node, clock, _pipeline = _off(node_env, tmp_path)
        _run_trigger(node)
        contexts = node._attempts.contexts_for(["robot_1", "robot_2"], clock.t)
        assert contexts.latest is None
        assert contexts.last_failed is None

    def test_no_override_and_no_registry_republish(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _pipeline = _off(node_env, tmp_path)
        before = len(node._tasks_pub.published)
        _run_trigger(node)
        assert len(node._tasks_pub.published) == before
        assert node._registry.effective("robot_2") == ("t", (-2.5, 0.35))

    def test_suppression_logged(self, node_env, tmp_path):  # noqa: F811
        node, _clock, pipeline = _off(node_env, tmp_path)
        _run_trigger(node)
        lines = node.get_logger().matching("dispatch suppressed")
        assert lines == [
            f"dispatch suppressed request={pipeline.run_calls[0]} "
            f"command=cmd-{pipeline.run_calls[0]} would_dispatch=['robot_2', 'robot_1'] "
            "cooldown_robots=['robot_1', 'robot_2'] cooldown_sec=15.0 "
            "(dispatch_enabled=false, log-only)"
        ]

    def test_dispatch_entry_refuses_when_off(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _pipeline = _off(node_env, tmp_path)
        node._dispatch(_ok_outcome("req-direct"))
        assert _commands(node) == []
        assert node.get_logger().matching("refusing dispatch request=req-direct")

    def test_publish_site_refuses_when_off(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _pipeline = _off(node_env, tmp_path)
        node._publish_fanned_out("req-x", [("cmd", "robot_1", "yield", "{}", 20.0)])
        assert _commands(node) == []
        assert node.get_logger().matching("refusing publish request=req-x")


class _FailedPipeline(_FakePipeline):
    def run(self, request):
        self.run_calls.append(request.request_id)
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id),
            grounded_command=None,
            terminal_stage=TerminalStage.GROUNDING,
            failure_reason="no grounding",
        )


class _RefusedFilterPipeline(_FakePipeline):
    def run(self, request):
        self.run_calls.append(request.request_id)
        command = {
            "command_id": f"cmd-{request.request_id}",
            "actions": [{"robot_id": "robot_9", "action": "yield", "parameters": {}}],
            "expected_resolution_time_sec": 10.0,
            "fallback": "stop",
        }
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id),
            grounded_command=command,
            terminal_stage=TerminalStage.OK,
        )


class TestNotSuppressed:
    def test_failed_outcome_records_not_suppressed(self, node_env, tmp_path):  # noqa: F811
        node, _clock, pipeline = _off(node_env, tmp_path, _FailedPipeline())
        _run_trigger(node)
        artifact = _artifact(node, pipeline.run_calls[0])
        assert artifact["dispatch_suppressed"] is False
        assert node.get_logger().matching("dispatch suppressed") == []

    def test_registry_filter_refusal_does_not_raise(self, node_env, tmp_path):  # noqa: F811
        node, _clock, pipeline = _off(node_env, tmp_path, _RefusedFilterPipeline())
        _run_trigger(node)
        artifact = _artifact(node, pipeline.run_calls[0])
        assert artifact["dispatch_suppressed"] is False
        assert "dispatch_filter_error" in artifact
        assert node.get_logger().matching("command=none filter_error=")

    def test_registry_filter_refusal_still_raises_with_dispatch_on(
        self, node_env, tmp_path  # noqa: F811
    ):
        pipeline = _RefusedFilterPipeline()
        node, _clock = _make_node(node_env, tmp_path, pipeline, t0_probe_mode=False)
        _trigger_real(node)
        node._future.result(timeout=WAIT_SEC)
        try:
            node._on_timer()
        except CommandGroundingError:
            return
        raise AssertionError("dispatch-on refusal path changed")


class TestCadence:
    def test_cooldown_blocks_retrigger_until_it_expires(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _off(node_env, tmp_path)
        _run_trigger(node, stamp=60.0)
        clock.t += 14.9
        _trigger_real(node, stamp=61.0)
        assert node._future is None
        assert len(pipeline.run_calls) == 1
        assert node.get_logger().matching("trigger suppressed")

    def test_persisting_stall_retriggers_once_cooldown_expires(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, clock, pipeline = _off(node_env, tmp_path)
        _run_trigger(node, stamp=60.0)
        clock.t += 15.0
        _run_trigger(node, stamp=62.0)
        assert len(pipeline.run_calls) == 2
        assert _commands(node) == []

    def test_retrigger_needs_no_fresh_stall_threshold(self, node_env, tmp_path):  # noqa: F811
        # Stall evidence is not reset by a suppressed dispatch: once the
        # cooldown expires the still-standing pair re-triggers on the next
        # scene, so the log-only cadence is cooldown_sec + analysis latency.
        node, clock, pipeline = _off(node_env, tmp_path, stall_threshold_sec=12.0)
        _trigger_real(node, stamp=60.0)
        assert node._future is None
        clock.t += 12.0
        _run_trigger(node, stamp=61.0)
        assert len(pipeline.run_calls) == 1
        clock.t += 15.0
        _run_trigger(node, stamp=62.0)
        assert len(pipeline.run_calls) == 2

    def test_exhausted_set_stays_empty(self, node_env, tmp_path):  # noqa: F811
        node, clock, _pipeline = _off(node_env, tmp_path)
        for k in range(3):
            _run_trigger(node, stamp=60.0 + k)
            clock.t += 15.0
        assert node._exhausted_robots == set()


class TestJunctionQueue:
    def test_junction_queue_not_started_when_off(self, node_env, tmp_path):  # noqa: F811
        node, clock = _node(node_env, tmp_path, dispatch_enabled=False)
        _dispatch_via_handle_outcome(node, clock)
        assert node._junction_phase_queues == {}
        assert node._junction_held_robots == {}
        assert _commands(node) == []

    def test_junction_queue_started_when_on(self, node_env, tmp_path):  # noqa: F811
        node, clock = _node(node_env, tmp_path)
        _dispatch_via_handle_outcome(node, clock)
        assert len(node._junction_phase_queues) == 1


class TestDispatchOn:
    def test_artifact_has_no_dispatch_flag_keys(self, node_env, tmp_path):  # noqa: F811
        pipeline = _FakePipeline()
        node, _clock = _make_node(node_env, tmp_path, pipeline, t0_probe_mode=False)
        _run_trigger(node)
        artifact = _artifact(node, pipeline.run_calls[0])
        assert "dispatch_enabled" not in artifact
        assert "dispatch_suppressed" not in artifact
        assert [m.robot_id for m in _commands(node)] == ["robot_2", "robot_1"]

    def test_writer_bytes_unchanged_without_suppression_arg(self, tmp_path):
        outcome = _ok_outcome("req-bytes")
        default = write_decision_artifact(tmp_path / "a", outcome).read_bytes()
        explicit = write_decision_artifact(
            tmp_path / "b", outcome, dispatch_suppressed=None
        ).read_bytes()
        assert default == explicit
        assert "dispatch_suppressed" not in json.loads(default)

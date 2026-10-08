"""Scene-unchanged re-trigger suppression (prereg-v3 A12(iii)).

Pure policy and state-machine tests, then node-level tests on the ROS2
stand-ins of `test_m5_node_probe` (detector, state machine, cooldowns,
artifact write and dispatch are the real code; the pipeline is scripted).
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import (
    CongestionEvent,
    PipelineOutcome,
    ReanalysisSuppressionConfig,
    RobotView,
    SceneSnapshot,
    TaskAssignment,
    TerminalStage,
)
from swarm_orchestrator.reanalysis_suppression import ReanalysisSuppressor
from swarm_orchestrator.state_machine import (
    DirectiveKind,
    OrchestratorState,
    OrchestratorStateMachine,
)
from swarm_orchestrator.task_stream import TaskStreamEvent

from reasoning.vlm.models import ReasonerDiagnostics, ReasonerResult
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _make_node,
    _ok_outcome,
    _result,
    _run_probe,
    _scene_msg,
    node_env,
)
from tests.unit.test_m5_node_task_stream import _make as _make_stream_node

EPS = 0.05
COOLDOWN = 15.0
BASE = {"robot_1": (0.0, -0.15), "robot_2": (0.0, 0.15)}
ON = {"enabled": True, "applies_to": "all"}


class TestPolicy:
    def _armed(self) -> ReanalysisSuppressor:
        policy = ReanalysisSuppressor(EPS, COOLDOWN)
        policy.arm("r0", ["robot_1", "robot_2"], BASE, 0.0, "no_congestion")
        return policy

    def test_not_armed_never_suppresses(self):
        verdict = ReanalysisSuppressor(EPS, COOLDOWN).check(["robot_1"], BASE, 0.0)
        assert verdict.suppress is False
        assert verdict.reason == "not_armed"

    def test_identical_scene_is_suppressed(self):
        verdict = self._armed().check(["robot_2", "robot_1"], BASE, 1.0)
        assert verdict.suppress is True
        assert verdict.reason == "scene_unchanged"

    def test_sub_epsilon_jitter_is_suppressed(self):
        jitter = {"robot_1": (0.008, -0.15), "robot_2": (0.0, 0.142)}
        assert self._armed().check(["robot_1", "robot_2"], jitter, 1.0).suppress is True

    def test_epsilon_crossing_releases_and_clears(self):
        policy = self._armed()
        moved = {"robot_1": (0.0, -0.15 - EPS), "robot_2": BASE["robot_2"]}
        verdict = policy.check(["robot_1", "robot_2"], moved, 1.0)
        assert verdict.suppress is False
        assert verdict.reason == "pose_moved"
        assert verdict.max_displacement_m == pytest.approx(EPS)
        assert policy.reference is None

    def test_creep_accumulates_against_the_reference(self):
        policy = self._armed()
        for step in range(1, 5):
            creep = {"robot_1": (0.015 * step, -0.15), "robot_2": BASE["robot_2"]}
            verdict = policy.check(["robot_1", "robot_2"], creep, float(step))
        assert verdict.suppress is False
        assert verdict.reason == "pose_moved"

    def test_robot_set_change_releases(self):
        policy = self._armed()
        verdict = policy.check(["robot_1"], BASE, 1.0)
        assert (verdict.suppress, verdict.reason) == (False, "robot_set_changed")
        assert policy.reference is None

    def test_missing_robot_releases(self):
        policy = self._armed()
        verdict = policy.check(["robot_1", "robot_2"], {"robot_1": BASE["robot_1"]}, 1.0)
        assert (verdict.suppress, verdict.reason) == (False, "robot_missing")

    def test_one_avoided_analysis_counted_per_period(self):
        policy = self._armed()
        counted = [policy.check(["robot_1", "robot_2"], BASE, t).counted
                   for t in (1.0, 2.0, 15.9, 16.0, 17.0, 31.0)]
        assert counted == [True, False, False, True, False, True]
        assert policy.avoided_analyses_total == 3
        assert policy.suppressed_triggers_total == 6

    def test_artifact_block_counts_since_the_last_analysis(self):
        policy = self._armed()
        policy.check(["robot_1", "robot_2"], BASE, 1.0)
        policy.check(["robot_1", "robot_2"], BASE, 2.0)
        first = policy.take_artifact_block()
        assert first["suppressed_triggers_since_last_analysis"] == 2
        assert first["avoided_analyses_since_last_analysis"] == 1
        second = policy.take_artifact_block()
        assert second["suppressed_triggers_since_last_analysis"] == 0
        assert second["suppressed_triggers_total"] == 2


class TestConfig:
    def test_defaults_are_off_epsilon_five_cm_task_stream_only(self):
        config = ReanalysisSuppressionConfig()
        assert config.enabled is False
        assert config.pose_epsilon_m == 0.05
        assert config.applies_to == "task_stream_only"

    def test_unknown_key_is_rejected(self):
        with pytest.raises(ValidationError):
            ReanalysisSuppressionConfig(enabled=True, window=3)


def _event(robots: list[str]) -> CongestionEvent:
    return CongestionEvent(
        involved_robots=robots, stall_durations_sec=dict.fromkeys(robots, 20.0),
        detected_at=0.0, reason="test",
    )


class TestStateMachineGate:
    def test_unchanged_scene_skips_without_leaving_monitoring(self):
        machine = OrchestratorStateMachine()
        directive = machine.on_event(
            _event(["robot_1"]), set(), set(), 0.0, scene_unchanged=lambda _r: True
        )
        assert directive.kind is DirectiveKind.SCENE_UNCHANGED
        assert machine.state is OrchestratorState.MONITORING

    def test_cooldown_gate_runs_before_the_check(self):
        calls: list[list[str]] = []
        directive = OrchestratorStateMachine().on_event(
            _event(["robot_1"]), {"robot_1"}, set(), 0.0,
            scene_unchanged=lambda r: calls.append(r) or True,
        )
        assert directive.kind is DirectiveKind.SUPPRESSED
        assert calls == []

    def test_frame_gate_runs_before_the_check(self):
        calls: list[list[str]] = []
        OrchestratorStateMachine().on_event(
            _event(["robot_1"]), set(), set(), 0.0, frame_ready=False,
            scene_unchanged=lambda r: calls.append(r) or True,
        )
        assert calls == []

    def test_fold_runs_before_the_check(self):
        calls: list[list[str]] = []
        directive = OrchestratorStateMachine().on_event(
            _event(["robot_3"]), set(), {"robot_1", "robot_2"}, 0.0,
            scene_unchanged=lambda r: calls.append(r) or True,
        )
        assert directive.kind is DirectiveKind.FOLDED
        assert calls == []

    def test_changed_scene_starts_the_analysis(self):
        directive = OrchestratorStateMachine().on_event(
            _event(["robot_1"]), set(), set(), 0.0, scene_unchanged=lambda _r: False
        )
        assert directive.kind is DirectiveKind.START_ANALYSIS


def _clear(request_id: str) -> PipelineOutcome:
    return PipelineOutcome(
        request_id=request_id, reasoner_result=_result(request_id, congested=False),
        grounded_command=None, terminal_stage=TerminalStage.VLM,
        failure_reason="no congestion detected",
    )


def _no_command(request_id: str) -> PipelineOutcome:
    return PipelineOutcome(
        request_id=request_id, reasoner_result=_result(request_id),
        grounded_command=None, terminal_stage=TerminalStage.GROUNDING,
        failure_reason="grounding refused",
    )


def _failed(request_id: str) -> PipelineOutcome:
    result = ReasonerResult(
        request_id=request_id, decision=None, raw_text=None,
        diagnostics=ReasonerDiagnostics(
            request_id=request_id, backend_id="mock", attempts=2, parse_status="failed"
        ),
    )
    return PipelineOutcome(
        request_id=request_id, reasoner_result=result, grounded_command=None,
        terminal_stage=TerminalStage.VLM, failure_reason="backend failed",
    )


_OUTCOMES = {"clear": _clear, "no_command": _no_command, "failed": _failed,
             "dispatch": _ok_outcome}


class _ScriptedPipeline:
    """Answers each run with the next scripted outcome kind, holding the last."""

    def __init__(self, *kinds: str) -> None:
        self.kinds = list(kinds)
        self.run_calls: list[str] = []

    def run(self, request):
        kind = self.kinds[min(len(self.run_calls), len(self.kinds) - 1)]
        self.run_calls.append(request.request_id)
        return _OUTCOMES[kind](request.request_id)

    def analyze(self, request):
        return PipelineOutcome(
            request_id=request.request_id, reasoner_result=_result(request.request_id),
            grounded_command=None, terminal_stage=TerminalStage.PROBE,
        )


def _node(node_env, tmp_path, *kinds, **overrides):  # noqa: F811
    pipeline = _ScriptedPipeline(*(kinds or ("clear",)))
    overrides.setdefault("t0_probe_mode", False)
    overrides.setdefault("reanalysis_suppression", ON)
    node, clock = _make_node(node_env, tmp_path, pipeline, **overrides)
    return node, clock, pipeline


def _feed(node, stamp: float, positions: dict[str, tuple[float, float]]) -> None:
    snapshot = SceneSnapshot(
        stamp=stamp, frame_id="overhead_camera",
        robots=[
            RobotView(robot_id=rid, x=x, y=y, theta=0.0, linear_velocity=0.0,
                      status="STOPPED", stamp=stamp)
            for rid, (x, y) in positions.items()
        ],
    )
    node._frame_stamp = stamp
    node._on_scene_state(_scene_msg(snapshot))


def _cycle(node, clock, positions=None, advance: float = COOLDOWN + 1.0) -> None:
    """Let the cooldown pass, then deliver one (stalled) scene and finish any analysis."""
    clock.t += advance
    _feed(node, clock.t - 900.0, positions or BASE)
    if node._future is not None:
        node._future.result(timeout=WAIT_SEC)
        node._on_timer()


def _artifact(node, request_id: str) -> dict:
    path = Path(node._config.decision_log_dir) / f"{request_id}.json"
    return json.loads(path.read_text())


class TestNodeDefaultOff:
    def test_default_off_reanalyses_every_cooldown(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(
            node_env, tmp_path, reanalysis_suppression=ReanalysisSuppressionConfig()
        )
        for _ in range(3):
            _cycle(node, clock)
        assert node._suppression is None
        assert len(pipeline.run_calls) == 3
        assert node.get_logger().matching("reanalysis") == []

    def test_default_off_artifact_has_no_suppression_key(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(
            node_env, tmp_path, reanalysis_suppression=ReanalysisSuppressionConfig()
        )
        _cycle(node, clock)
        assert "reanalysis_suppression" not in _artifact(node, pipeline.run_calls[0])

    def test_task_stream_only_without_a_stream_is_inert(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(
            node_env, tmp_path, reanalysis_suppression={"enabled": True}
        )
        for _ in range(3):
            _cycle(node, clock)
        assert node._suppression is None
        assert len(pipeline.run_calls) == 3


class TestNodeSuppression:
    def test_identical_stall_after_no_congestion_is_skipped(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "clear")
        for _ in range(4):
            _cycle(node, clock)
        assert len(pipeline.run_calls) == 1
        lines = node.get_logger().matching("reanalysis suppressed reason=scene_unchanged")
        assert len(lines) == 3
        assert f"reference_request={pipeline.run_calls[0]}" in lines[0]
        assert "reference_outcome=no_congestion" in lines[0]
        assert node._machine.state is OrchestratorState.MONITORING

    def test_suppression_starts_no_cooldown(self, node_env, tmp_path):  # noqa: F811
        node, clock, _pipeline = _node(node_env, tmp_path, "clear")
        _cycle(node, clock)
        _cycle(node, clock)
        assert node._cooldown.active_robots(clock.t) == set()

    def test_log_is_throttled_to_one_line_per_cooldown(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "clear")
        _cycle(node, clock)
        _cycle(node, clock)
        for _ in range(10):
            _cycle(node, clock, advance=1.0)
        assert len(pipeline.run_calls) == 1
        assert len(node.get_logger().matching("reanalysis suppressed")) == 1
        assert node._suppression.suppressed_triggers_total == 11
        assert node._suppression.avoided_analyses_total == 1

    def test_epsilon_crossing_releases_the_analysis(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "clear")
        _cycle(node, clock)
        _cycle(node, clock)
        moved = {"robot_1": (0.06, -0.15), "robot_2": BASE["robot_2"]}
        _cycle(node, clock, positions=moved, advance=1.0)
        assert len(pipeline.run_calls) == 2
        [line] = node.get_logger().matching("reanalysis suppression reset reason=pose_moved")
        assert "max_displacement_m=0.060" in line

    def test_robot_set_change_releases_the_analysis(self, node_env, tmp_path):  # noqa: F811
        tasks = {
            "robot_1": TaskAssignment(task="t", goal=(2.5, -0.35)),
            "robot_2": TaskAssignment(task="t", goal=(-2.5, 0.35)),
            "robot_3": TaskAssignment(task="t", goal=(2.5, 0.35)),
        }
        node, clock, pipeline = _node(node_env, tmp_path, "clear", initial_tasks=tasks)
        _cycle(node, clock)
        _cycle(node, clock)
        assert len(pipeline.run_calls) == 1
        joined = dict(BASE, robot_3=(0.3, 0.15))
        _cycle(node, clock, positions=joined, advance=1.0)
        assert len(pipeline.run_calls) == 2
        assert node.get_logger().matching("reset reason=robot_set_changed")

    def test_grounding_no_command_arms(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "no_command")
        _cycle(node, clock)
        _cycle(node, clock)
        assert len(pipeline.run_calls) == 1
        assert node.get_logger().matching("outcome=no_command")

    def test_backend_failure_does_not_arm(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "failed")
        _cycle(node, clock)
        _cycle(node, clock)
        assert len(pipeline.run_calls) == 2
        assert node._suppression.reference is None

    def test_dispatch_never_arms(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "dispatch")
        _cycle(node, clock)
        command_id = f"cmd-{pipeline.run_calls[0]}"
        for robot_id in ("robot_1", "robot_2"):
            node._on_status(SimpleNamespace(command_id=command_id, robot_id=robot_id,
                                            status="COMPLETED"))
        _cycle(node, clock)
        assert len(pipeline.run_calls) == 2
        assert node._suppression.reference is None

    def test_dispatch_resets_an_armed_reference(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "clear", "clear", "dispatch")
        _cycle(node, clock)
        # Moving re-runs the analysis (clear again, re-armed at the new pose)...
        moved = {"robot_1": (0.1, -0.15), "robot_2": BASE["robot_2"]}
        _cycle(node, clock, positions=moved)
        moved_again = {"robot_1": (0.2, -0.15), "robot_2": BASE["robot_2"]}
        # ...and the third analysis dispatches, which clears the reference.
        _cycle(node, clock, positions=moved_again)
        assert len(pipeline.run_calls) == 3
        assert node._suppression.reference is None
        assert node.get_logger().matching("reanalysis suppression reset reason=pose_moved")

    def test_dispatch_suppressed_arms(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "dispatch", dispatch_enabled=False)
        for _ in range(3):
            _cycle(node, clock)
        assert len(pipeline.run_calls) == 1
        assert node.get_logger().matching("outcome=dispatch_suppressed")

    def test_artifact_reports_the_skipped_cadence(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "clear")
        for _ in range(4):
            _cycle(node, clock)
        moved = {"robot_1": (0.06, -0.15), "robot_2": BASE["robot_2"]}
        _cycle(node, clock, positions=moved, advance=1.0)
        first = _artifact(node, pipeline.run_calls[0])["reanalysis_suppression"]
        second = _artifact(node, pipeline.run_calls[1])["reanalysis_suppression"]
        assert first["avoided_analyses_since_last_analysis"] == 0
        assert second["avoided_analyses_since_last_analysis"] == 3
        assert second["avoided_analyses_total"] == 3
        assert second["pose_epsilon_m"] == EPS


class TestNodeInteractions:
    def test_cooldown_gate_is_not_counted_as_suppression(self, node_env, tmp_path):  # noqa: F811
        node, clock, _pipeline = _node(node_env, tmp_path, "clear")
        _cycle(node, clock)
        _cycle(node, clock, advance=1.0)  # still inside the 15 s cooldown
        assert node._suppression.suppressed_triggers_total == 0
        assert node.get_logger().matching("trigger suppressed robots=")

    def test_exhausted_robots_gate_before_the_check(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "clear")
        _cycle(node, clock)
        node._exhausted_robots.update({"robot_1"})
        _cycle(node, clock)
        assert node._suppression.suppressed_triggers_total == 0
        assert len(pipeline.run_calls) == 1

    def test_task_issued_to_a_reference_robot_resets(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "clear")
        _cycle(node, clock)
        # Only the reset hook is under test; the stream's own bookkeeping
        # (tasks JSONL, manifest) needs an enabled stream.
        node._record_stream_events = lambda _events: None
        node._apply_stream_events([
            TaskStreamEvent(event="issued", robot_id="robot_1", task_index=1, node="A",
                            label="delivery", goal=(1.0, 1.0), wall_t=clock.t, sim_t=1.0)
        ])
        assert node._suppression.reference is None
        assert node.get_logger().matching("reset reason=task_issued")

    def test_t0_probe_neither_consults_nor_resets(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "clear", t0_probe_mode=True)
        _cycle(node, clock)
        reference = node._suppression.reference
        assert reference is not None
        _run_probe(node, clock, at=clock.t + 30.0)
        assert node._suppression.reference is reference
        assert node._suppression.suppressed_triggers_total == 0
        assert len(pipeline.run_calls) == 1

    def test_task_stream_only_engages_with_the_stream(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make_stream_node(
            node_env, tmp_path, reanalysis_suppression={"enabled": True}
        )
        assert node._suppression is not None

    def test_manual_trigger_bypasses_and_resets(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(node_env, tmp_path, "clear")
        _cycle(node, clock)
        clock.t += COOLDOWN + 1.0
        response = node._on_trigger_analysis(SimpleNamespace(reason="op"), SimpleNamespace())
        assert response.accepted is True
        node._future.result(timeout=WAIT_SEC)
        node._on_timer()
        assert len(pipeline.run_calls) == 2
        assert node._suppression.reference is None


_CONTRADICTION_ON = {"enabled": True, "divergence_bound_m": 0.5, "per_event_replan_budget": 1}


class TestNodeContradiction:
    def _dispatch_then_fail(self, node, clock, pipeline) -> None:
        _cycle(node, clock)
        command_id = f"cmd-{pipeline.run_calls[0]}"
        node._on_status(SimpleNamespace(command_id=command_id, robot_id="robot_2",
                                        status="FAILED"))
        node._on_status(SimpleNamespace(command_id=command_id, robot_id="robot_1",
                                        status="COMPLETED"))

    def test_contradiction_analysis_bypasses_an_armed_reference(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(
            node_env, tmp_path, "dispatch", "clear", contradiction_trigger=_CONTRADICTION_ON
        )
        _cycle(node, clock)
        command_id = f"cmd-{pipeline.run_calls[0]}"
        # An armed same-set reference (e.g. left by another robot pair's
        # bookkeeping) must not gate the early re-analysis.
        node._suppression.arm("old", ["robot_1", "robot_2"], BASE, clock.t, "no_congestion")
        node._on_status(SimpleNamespace(command_id=command_id, robot_id="robot_2",
                                        status="FAILED"))
        node._on_status(SimpleNamespace(command_id=command_id, robot_id="robot_1",
                                        status="COMPLETED"))
        assert node._future is not None
        assert node.get_logger().matching("reanalysis suppression reset reason=contradiction")
        node._future.result(timeout=WAIT_SEC)
        node._on_timer()
        assert len(pipeline.run_calls) == 2

    def test_contradiction_outcome_does_not_arm(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _node(
            node_env, tmp_path, "dispatch", "clear", "clear",
            contradiction_trigger=_CONTRADICTION_ON,
        )
        self._dispatch_then_fail(node, clock, pipeline)
        node._future.result(timeout=WAIT_SEC)
        node._on_timer()
        assert node._suppression.reference is None
        # The next identical stall is a fresh stall analysis, which then arms.
        _cycle(node, clock)
        assert len(pipeline.run_calls) == 3
        _cycle(node, clock)
        assert len(pipeline.run_calls) == 3

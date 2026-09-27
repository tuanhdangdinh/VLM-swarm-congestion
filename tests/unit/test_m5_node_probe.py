"""Node-level tests for M5's T0 log-only probe mode, with ROS2 stubbed out.

This sandbox has no rclpy / cv_bridge / swarm_interfaces build, so the fixture
installs minimal stand-ins in `sys.modules` (restored afterwards, so
`tests/integration/test_m5_node.py` still skips) and imports the real
`orchestrator_node` against them. Everything past the ROS2 surface — state
machine, detector, pipeline hand-off, artifact write, dispatch — is the real code.
"""
from __future__ import annotations

import importlib
import json
import sys
import threading
import types
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from swarm_orchestrator.models import (
    OrchestratorConfig,
    PipelineOutcome,
    RobotView,
    SceneSnapshot,
    TaskAssignment,
    TerminalStage,
)
from swarm_orchestrator.presentation_order import PresentationOrderPolicy
from swarm_orchestrator.state_machine import OrchestratorState

from reasoning.vlm.models import CongestionDecision, ReasonerDiagnostics, ReasonerResult
from tests.unit.test_m5_reasoning_pipeline import _TRIGGERED_ARTIFACT_KEYS

WAIT_SEC = 5.0


class _Logger:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str]] = []

    def info(self, msg: str) -> None:
        self.lines.append(("info", msg))

    def warning(self, msg: str) -> None:
        self.lines.append(("warning", msg))

    def error(self, msg: str) -> None:
        self.lines.append(("error", msg))

    def matching(self, text: str) -> list[str]:
        return [msg for _level, msg in self.lines if text in msg]


class _Publisher:
    def __init__(self, topic: str) -> None:
        self.topic = topic
        self.published: list[object] = []

    def publish(self, msg: object) -> None:
        self.published.append(msg)


class _StubNode:
    def __init__(self, name: str) -> None:
        self._stub_logger = _Logger()
        self.publishers: dict[str, _Publisher] = {}

    def declare_parameter(self, *_args, **_kwargs) -> None:
        return None

    def create_publisher(self, _msg_type, topic, _qos) -> _Publisher:
        publisher = _Publisher(topic)
        self.publishers[topic] = publisher
        return publisher

    def create_subscription(self, *_args, **_kwargs) -> object:
        return object()

    def create_service(self, *_args, **_kwargs) -> object:
        return object()

    def create_timer(self, *_args, **_kwargs) -> object:
        return object()

    def get_logger(self) -> _Logger:
        return self._stub_logger


class _Message:
    """Stand-in for a generated ROS2 message: a bag of assignable fields."""


class _QoSProfile:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


def _stub_modules() -> dict[str, types.ModuleType]:
    def module(name: str, **attrs) -> types.ModuleType:
        mod = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(mod, key, value)
        return mod

    policy = SimpleNamespace(TRANSIENT_LOCAL="transient_local", RELIABLE="reliable",
                             BEST_EFFORT="best_effort")
    return {
        "rclpy": module("rclpy", init=lambda **_: None, spin=lambda _n: None,
                        shutdown=lambda: None),
        "rclpy.node": module("rclpy.node", Node=_StubNode),
        "rclpy.qos": module("rclpy.qos", QoSProfile=_QoSProfile, DurabilityPolicy=policy,
                            ReliabilityPolicy=policy),
        "cv_bridge": module("cv_bridge", CvBridge=lambda: SimpleNamespace()),
        "sensor_msgs": module("sensor_msgs"),
        "sensor_msgs.msg": module("sensor_msgs.msg", Image=_Message),
        "std_msgs": module("std_msgs"),
        "std_msgs.msg": module("std_msgs.msg", String=_Message),
        "swarm_interfaces": module("swarm_interfaces"),
        "swarm_interfaces.msg": module(
            "swarm_interfaces.msg", CoordinationCommand=_Message, CoordinationStatus=_Message
        ),
        "swarm_interfaces.srv": module(
            "swarm_interfaces.srv", TriggerCongestionAnalysis=_Message
        ),
    }


class _Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def monotonic(self) -> float:
        return self.t


@pytest.fixture
def node_env(monkeypatch):
    for name, mod in _stub_modules().items():
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.delitem(sys.modules, "swarm_orchestrator.orchestrator_node", raising=False)
    node_module = importlib.import_module("swarm_orchestrator.orchestrator_node")
    clock = _Clock()
    monkeypatch.setattr(node_module, "time", SimpleNamespace(monotonic=clock.monotonic))
    yield node_module, clock
    sys.modules.pop("swarm_orchestrator.orchestrator_node", None)


def _config(tmp_path: Path, **overrides) -> OrchestratorConfig:
    base = dict(
        stall_threshold_sec=0.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={
            "robot_1": TaskAssignment(task="t", goal=(2.5, -0.35)),
            "robot_2": TaskAssignment(task="t", goal=(-2.5, 0.35)),
        },
        frame_dump_dir=str(tmp_path / "frames"),
        decision_log_dir=str(tmp_path / "decisions"),
        scene_log_dir=None,
        shadow_classical=False,
        t0_probe_mode=True,
        t0_probe_interval_sec=20.0,
    )
    base.update(overrides)
    return OrchestratorConfig(**base)


def _decision(congested: bool = True) -> CongestionDecision:
    if not congested:
        return CongestionDecision(
            congestion_detected=False, type="none", involved_robots=[],
            root_cause="clear", strategy="none", justification="normal flow",
        )
    return CongestionDecision(
        congestion_detected=True, type="deadlock", involved_robots=["robot_1", "robot_2"],
        root_cause="head-on", strategy="yield", justification="x", yield_robot="robot_2",
    )


def _result(request_id: str, congested: bool = True) -> ReasonerResult:
    diag = ReasonerDiagnostics(
        request_id=request_id, backend_id="mock", attempts=1, parse_status="valid"
    )
    return ReasonerResult(
        request_id=request_id, decision=_decision(congested), raw_text="{}", diagnostics=diag
    )


def _command(request_id: str) -> dict:
    return {
        "command_id": f"cmd-{request_id}",
        "actions": [
            {"robot_id": "robot_2", "action": "yield", "parameters": {"backup_distance_m": 0.8}},
            {"robot_id": "robot_1", "action": "temporary_wait", "parameters": {}},
        ],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }


def _ok_outcome(request_id: str) -> PipelineOutcome:
    return PipelineOutcome(
        request_id=request_id,
        reasoner_result=_result(request_id),
        grounded_command=_command(request_id),
        terminal_stage=TerminalStage.OK,
    )


class _FakePipeline:
    """`run` always grounds a full command; `analyze` is the stage-1 probe path."""

    def __init__(self, analyze_outcome=None, run_gate=None, analyze_gate=None) -> None:
        self.run_calls: list[str] = []
        self.analyze_calls: list[str] = []
        self.run_entered = threading.Event()
        self.analyze_entered = threading.Event()
        self._analyze_outcome = analyze_outcome
        self._run_gate = run_gate
        self._analyze_gate = analyze_gate

    def run(self, request):
        self.run_calls.append(request.request_id)
        self.run_entered.set()
        if self._run_gate is not None:
            self._run_gate.wait(WAIT_SEC)
        return _ok_outcome(request.request_id)

    def analyze(self, request):
        self.analyze_calls.append(request.request_id)
        self.analyze_entered.set()
        if self._analyze_gate is not None:
            self._analyze_gate.wait(WAIT_SEC)
        if self._analyze_outcome is not None:
            return self._analyze_outcome(request.request_id)
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id),
            grounded_command=None,
            terminal_stage=TerminalStage.PROBE,
        )


def _snapshot(stamp: float = 50.0, close: bool = False) -> SceneSnapshot:
    # `close`: two slow robots 0.3 m apart, a close/slow pair that the detector
    # flags at once with stall_threshold_sec=0 — a real trigger.
    y1, y2 = (-0.15, 0.15) if close else (-0.35, 0.35)
    speed = 0.0 if close else 0.15
    return SceneSnapshot(
        stamp=stamp,
        frame_id="overhead_camera",
        robots=[
            RobotView(robot_id="robot_1", x=0.0, y=y1, theta=0.0,
                      linear_velocity=speed, status="MOVING", stamp=stamp),
            RobotView(robot_id="robot_2", x=0.0, y=y2, theta=3.14,
                      linear_velocity=speed, status="MOVING", stamp=stamp),
        ],
    )


def _scene_msg(snapshot: SceneSnapshot) -> SimpleNamespace:
    payload = snapshot.model_dump(mode="json")
    payload.pop("dropped_frame")
    payload["diagnostics"] = {}
    return SimpleNamespace(data=json.dumps(payload))


def _make_node(node_env, tmp_path, pipeline, **overrides):
    node_module, clock = node_env
    node = node_module.OrchestratorNode(config=_config(tmp_path, **overrides), pipeline=pipeline)
    snapshot = _snapshot()
    node._latest_snapshot = snapshot
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    node._frame_stamp = snapshot.stamp
    return node, clock


def _commands(node) -> list[object]:
    return node._cmd_pub.published


def _artifact(node, request_id: str) -> dict:
    path = Path(node._config.decision_log_dir) / f"{request_id}.json"
    return json.loads(path.read_text())


def _mark_feed_live(node, clock) -> None:
    # A live M1 feed re-delivers the scene every frame; stand in for that
    # without `_on_scene_state`, whose detector could trip on repeated scenes.
    node._latest_snapshot_at = clock.t


def _run_probe(node, clock, at: float) -> str:
    clock.t = at
    _mark_feed_live(node, clock)
    node._on_timer()
    probe = node._probe
    assert probe is not None, "probe did not start"
    probe.future.result(timeout=WAIT_SEC)
    node._on_timer()
    return probe.request_id


def _trigger_real(node, stamp: float = 60.0) -> None:
    node._frame_stamp = stamp
    node._on_scene_state(_scene_msg(_snapshot(stamp, close=True)))


def test_probe_writes_artifact_marked_probe_with_would_be_decision(node_env, tmp_path):
    node, clock = _make_node(node_env, tmp_path, _FakePipeline())

    request_id = _run_probe(node, clock, at=1020.0)

    payload = _artifact(node, request_id)
    assert payload["probe"] is True
    assert payload["probe_index"] == 0
    assert payload["terminal_stage"] == "probe"
    assert payload["decision"]["congestion_detected"] is True
    assert payload["decision"]["strategy"] == "yield"
    assert payload["prompt"]["user_prompt"]
    assert payload["scene"]["robots"][0]["robot_id"] == "robot_1"
    assert payload["episode_index"] is None


def test_triggered_artifact_scene_carries_registry_goal_and_task(node_env, tmp_path):
    pipeline = _FakePipeline()
    node, _clock = _make_node(node_env, tmp_path, pipeline, t0_probe_mode=False)

    _trigger_real(node)
    node._future.result(timeout=WAIT_SEC)
    node._on_timer()

    payload = _artifact(node, pipeline.run_calls[0])
    robots = {r["robot_id"]: r for r in payload["scene"]["robots"]}
    assert robots["robot_1"]["goal"] == [2.5, -0.35]
    assert robots["robot_1"]["task"] == "t"
    assert payload["prompt_version"] == 2
    assert "goal_x=2.50, goal_y=-0.35, task=t" in payload["prompt"]["user_prompt"]


def test_probe_artifact_scene_carries_registry_goal_and_task(node_env, tmp_path):
    node, clock = _make_node(node_env, tmp_path, _FakePipeline())

    payload = _artifact(node, _run_probe(node, clock, at=1020.0))
    robots = {r["robot_id"]: r for r in payload["scene"]["robots"]}
    assert robots["robot_2"]["goal"] == [-2.5, 0.35]
    assert robots["robot_2"]["task"] == "t"


def test_probe_logs_starting_analysis_with_t0_probe_reason(node_env, tmp_path):
    node, clock = _make_node(node_env, tmp_path, _FakePipeline())

    request_id = _run_probe(node, clock, at=1020.0)

    lines = node.get_logger().matching("starting analysis")
    assert lines == [
        f"starting analysis request={request_id} robots=['robot_1', 'robot_2'] "
        "reason=t0_probe order=id_asc probe=true probe_index=0"
    ]


def test_probe_does_not_start_before_interval(node_env, tmp_path):
    pipeline = _FakePipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline)

    clock.t = 1019.9
    node._on_timer()

    assert node._probe is None
    assert pipeline.analyze_calls == []


def test_probe_stops_after_max_probes(node_env, tmp_path):
    pipeline = _FakePipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline, t0_probe_max_probes=2)

    _run_probe(node, clock, at=1020.0)
    _run_probe(node, clock, at=1040.0)
    clock.t = 2000.0
    node._on_timer()

    assert len(pipeline.analyze_calls) == 2
    assert node._probe is None


def test_probe_congestion_decision_never_calls_grounding_pipeline(node_env, tmp_path):
    pipeline = _FakePipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline)

    _run_probe(node, clock, at=1020.0)

    assert len(pipeline.analyze_calls) == 1
    assert pipeline.run_calls == []


def test_probe_with_full_command_payload_dispatches_nothing(node_env, tmp_path):
    # Worst case for the structural layer: stage 1 hands back a congestion
    # decision AND a schema-valid grounded command. The probe path must still
    # emit nothing, because it never calls the dispatch stage at all.
    pipeline = _FakePipeline(analyze_outcome=_ok_outcome)
    node, clock = _make_node(node_env, tmp_path, pipeline)

    request_id = _run_probe(node, clock, at=1020.0)

    assert _commands(node) == []
    assert node._tracker._records == {}
    assert node._attempts._record is None
    assert node._cooldown.active_robots(clock.t) == set()
    assert node._machine.state is OrchestratorState.MONITORING
    assert node._registry.effective("robot_2")[0] == "t"
    assert node.get_logger().matching("dispatch request=") == []
    assert _artifact(node, request_id)["decision"]["congestion_detected"] is True


def test_dispatch_refuses_probe_outcome_with_logged_error(node_env, tmp_path):
    node, clock = _make_node(node_env, tmp_path, _FakePipeline())
    request_id = _run_probe(node, clock, at=1020.0)

    node._dispatch(_ok_outcome(request_id))

    assert _commands(node) == []
    assert node._tracker._records == {}
    assert node._attempts._record is None
    errors = [msg for level, msg in node.get_logger().lines if level == "error"]
    assert errors == [f"refusing dispatch request={request_id}: t0 probe outcomes are log-only"]


def test_outcome_handler_refuses_probe_outcome_at_dispatch(node_env, tmp_path):
    node, clock = _make_node(node_env, tmp_path, _FakePipeline())
    request_id = _run_probe(node, clock, at=1020.0)

    node._handle_outcome(_ok_outcome(request_id), clock.t)

    assert _commands(node) == []
    assert node.get_logger().matching(f"refusing dispatch request={request_id}")


def test_dispatch_still_publishes_triggered_outcome_in_probe_mode(node_env, tmp_path):
    node, _clock = _make_node(node_env, tmp_path, _FakePipeline())

    node._dispatch(_ok_outcome("real1"))

    assert [msg.robot_id for msg in _commands(node)] == ["robot_2", "robot_1"]


def test_probe_skipped_while_analysis_in_flight(node_env, tmp_path):
    gate = threading.Event()
    pipeline = _FakePipeline(run_gate=gate)
    node, clock = _make_node(node_env, tmp_path, pipeline)
    _trigger_real(node)
    assert pipeline.run_entered.wait(WAIT_SEC)

    clock.t = 1020.0
    node._on_timer()

    assert node._probe is None
    assert pipeline.analyze_calls == []
    assert node.get_logger().matching("t0 probe deferred reason=analysis_in_flight")
    gate.set()
    node._future.result(timeout=WAIT_SEC)
    clock.t = 1020.5
    _mark_feed_live(node, clock)
    node._on_timer()
    assert node._probe is not None


def test_real_trigger_not_delayed_by_probe_in_flight(node_env, tmp_path):
    gate = threading.Event()
    pipeline = _FakePipeline(analyze_gate=gate)
    node, clock = _make_node(node_env, tmp_path, pipeline)
    clock.t = 1020.0
    _mark_feed_live(node, clock)
    node._on_timer()
    assert pipeline.analyze_entered.wait(WAIT_SEC)

    _trigger_real(node)

    try:
        # The probe's VLM call is still blocked; the real one must not queue behind it.
        assert pipeline.run_entered.wait(WAIT_SEC)
        assert node._machine.state is OrchestratorState.ANALYZING
    finally:
        gate.set()


def test_probe_leaves_episode_draw_to_real_analyses(node_env, tmp_path):
    seed = 7
    pipeline = _FakePipeline()
    node, clock = _make_node(
        node_env, tmp_path, pipeline, prompt_robot_order="random", prompt_robot_order_seed=seed
    )
    policy = PresentationOrderPolicy(mode="random", seed=seed)
    probe_ids = [_run_probe(node, clock, at=1020.0 + 20.0 * k) for k in range(4)]

    assert node._episodes.episode_index == -1
    for index, request_id in enumerate(probe_ids):
        payload = _artifact(node, request_id)
        assert payload["robot_presentation_order"] == policy.order_for_episode(index)
        assert payload["prompt_robot_order_seed"] == seed

    _trigger_real(node)
    node._future.result(timeout=WAIT_SEC)
    real_id = pipeline.run_calls[0]
    node._on_timer()
    real = _artifact(node, real_id)
    assert real["episode_index"] == 0
    assert real["robot_presentation_order"] == policy.order_for_episode(0)


def test_probe_records_shadow_without_counting_attempt(node_env, tmp_path):
    node, clock = _make_node(node_env, tmp_path, _FakePipeline(), shadow_classical=True)

    request_id = _run_probe(node, clock, at=1020.0)

    shadow = _artifact(node, request_id)["shadow_classical"]
    assert shadow["request_id"] == request_id
    assert shadow["prior_attempts"] == 0
    assert shadow["prior_attempts_source"] == "t0_probe"


def test_probe_deferred_on_frozen_feed_past_max_snapshot_age(node_env, tmp_path):
    # Isaac exited: no scene arrives after 1020, but the frozen scene and
    # frame stamps still agree, so only the receipt age can stop the probe.
    pipeline = _FakePipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline)
    _run_probe(node, clock, at=1020.0)

    clock.t = 1040.0
    node._on_timer()

    assert node._probe is None
    assert len(pipeline.analyze_calls) == 1
    assert node.get_logger().matching("t0 probe deferred reason=snapshot_stale")


def test_probe_starts_when_snapshot_age_within_max(node_env, tmp_path):
    pipeline = _FakePipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline, t0_probe_max_snapshot_age_sec=3.0)
    node._latest_snapshot_at = 1017.0

    clock.t = 1020.0
    node._on_timer()

    assert node._probe is not None
    assert node.get_logger().matching("t0 probe deferred") == []


def test_probe_deferred_just_past_max_snapshot_age(node_env, tmp_path):
    pipeline = _FakePipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline, t0_probe_max_snapshot_age_sec=3.0)
    node._latest_snapshot_at = 1016.9

    clock.t = 1020.0
    node._on_timer()

    assert node._probe is None
    assert pipeline.analyze_calls == []


def test_probe_stale_snapshot_deferral_logged_once(node_env, tmp_path):
    node, clock = _make_node(node_env, tmp_path, _FakePipeline())
    node._latest_snapshot_at = 1000.0

    for k in range(40):
        clock.t = 1020.0 + 0.5 * k
        node._on_timer()

    assert len(node.get_logger().matching("t0 probe deferred reason=snapshot_stale")) == 1


def test_probe_resumes_when_feed_returns_after_stale_deferral(node_env, tmp_path):
    pipeline = _FakePipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline)
    node._latest_snapshot_at = 1000.0
    clock.t = 1020.0
    node._on_timer()
    assert node._probe is None

    clock.t = 1020.5
    _mark_feed_live(node, clock)
    node._on_timer()

    assert node._probe is not None


def test_probe_mode_off_by_default_never_probes(node_env, tmp_path):
    pipeline = _FakePipeline()
    node, clock = _make_node(
        node_env, tmp_path, pipeline, t0_probe_mode=OrchestratorConfig.model_fields[
            "t0_probe_mode"
        ].default
    )

    for t in range(1000, 1200):
        clock.t = float(t)
        node._on_timer()

    assert node._probe_scheduler is None
    assert node._probe_executor is None
    assert pipeline.analyze_calls == []
    assert node._future is None


def test_probe_mode_off_triggered_analysis_unchanged(node_env, tmp_path):
    pipeline = _FakePipeline()
    node, _clock = _make_node(node_env, tmp_path, pipeline, t0_probe_mode=False)

    _trigger_real(node)
    node._future.result(timeout=WAIT_SEC)
    node._on_timer()

    request_id = pipeline.run_calls[0]
    assert set(_artifact(node, request_id)) == _TRIGGERED_ARTIFACT_KEYS
    [line] = node.get_logger().matching("starting analysis")
    assert line == (
        f"starting analysis request={request_id} robots=['robot_1', 'robot_2'] "
        "reason=2 robot(s) close/slow >= 0.0s order=id_asc distance_to_goal_m={}"
    )
    assert len(_commands(node)) == 2


def test_probe_mode_requires_stage1_analyzer(node_env, tmp_path):
    node_module, _clock = node_env

    class _RunOnly:
        def run(self, request):
            raise AssertionError("unused")

    with pytest.raises(ValueError, match="analyze"):
        node_module.OrchestratorNode(config=_config(tmp_path), pipeline=_RunOnly())

"""Echo-mock apparatus (prereg-v3 A12(i)): grounding exercised end to end without an API.

The echo backend reads the stalled robots off the rendered prompt's state
block and answers a congestion decision naming them, so M3's dynamic view
runs on S1-style scenes. It must stay unreachable from live backends, mark
every artifact it produces, and (paired with the A12(iii) suppression) never
re-answer an unchanged stall forever.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from swarm_orchestrator.models import RobotView, SceneSnapshot
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    build_reasoner_request,
    write_decision_artifact,
)

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.backend_factory import build_backend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.mock_backend import EchoMockBackend, MockBackend, echo_involved_robots
from reasoning.vlm.models import (
    FailureContext,
    LlamaServerBackendConfig,
    PlanStateContext,
    PlanStateLeg,
    ReasonerConfig,
)
from reasoning.vlm.prompt_builder import build_prompt_payload
from reasoning.vlm.reasoner import Reasoner
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _config,
    _scene_msg,
    node_env,
)

# S1 plus-floor junction box, no declared arms (test_dynamic_grounding's _S1).
_S1 = SceneGeometry.model_validate({
    "corridor": {"axis": "x", "center_m": 0.0, "half_length_m": 0.6,
                 "aisle_half_width_m": 0.6, "occluder_height_m": 0.0},
})
_DYNAMIC = GroundingParams(mode="derived", dynamic_scene_arms=True)
_NODE_WP = (-2.3, 0.35)
_NODE_E = (2.3, 0.0)


def _robot(rid, x, y, theta, status="STOPPED", goal=None, speed=0.0, stamp=40.0):
    return RobotView(robot_id=rid, x=x, y=y, theta=theta, linear_velocity=speed,
                     status=status, stamp=stamp, goal=goal, task="pickup")


def _s1_lane_snapshot(**extra_robots) -> SceneSnapshot:
    # W arm +0.35 lane head-on: robot_1 eastbound toward E, robot_2 westbound
    # toward Wp; robot_3 drives freely elsewhere.
    robots = [
        _robot("robot_1", -1.6, 0.35, 0.0, goal=_NODE_E),
        _robot("robot_2", -1.2, 0.35, math.pi, goal=_NODE_WP),
        _robot("robot_3", 0.0, -1.0, math.pi / 2, status="MOVING", goal=(0.0, 1.55),
               speed=0.2),
    ]
    robots.extend(extra_robots.values())
    return SceneSnapshot(stamp=40.0, frame_id="overhead_camera", robots=robots,
                         dropped_frame=False)


_IMAGE: dict[str, str] = {}


@pytest.fixture(autouse=True)
def _frame_file(tmp_path_factory):
    # The reasoner refuses a request whose frame is missing; the echo never
    # reads it, so any file stands in.
    if "path" not in _IMAGE:
        path = tmp_path_factory.mktemp("echo") / "echo1.png"
        path.write_bytes(b"png")
        _IMAGE["path"] = str(path)


def _request(snapshot: SceneSnapshot, **overrides):
    overrides.setdefault("prompt_version", 3)
    return build_reasoner_request(
        request_id="echo1", snapshot=snapshot, image_path=_IMAGE["path"], **overrides
    )


class TestStateBlockParsing:
    def test_names_the_non_moving_robots_of_the_v3_state_block(self):
        payload = build_prompt_payload(_request(_s1_lane_snapshot()))
        assert echo_involved_robots(payload) == ["robot_1", "robot_2"]

    def test_order_is_the_presentation_order_not_the_registry(self):
        request = _request(_s1_lane_snapshot(),
                           robot_presentation_order=("robot_2", "robot_3", "robot_1"))
        assert echo_involved_robots(build_prompt_payload(request)) == ["robot_2", "robot_1"]

    def test_slow_and_stale_count_as_not_moving(self):
        # No two stalled robots within the 0.45 m latch radius, so the
        # pre-A20(3) rule names every stalled robot (A20(3) prefers an
        # engaged latch pair when there is one: test_s1b_rulings_a20).
        snapshot = _s1_lane_snapshot(
            r4=_robot("robot_4", 1.5, 0.0, math.pi, status="SLOW"),
            r5=_robot("robot_5", 2.3, 0.0, math.pi, status="STALE"),
        )
        snapshot = snapshot.model_copy(
            update={
                "robots": [
                    r.model_copy(update={"x": -0.9}) if r.robot_id == "robot_2" else r
                    for r in snapshot.robots
                ]
            }
        )
        names = echo_involved_robots(build_prompt_payload(_request(snapshot)))
        assert names == ["robot_1", "robot_2", "robot_4", "robot_5"]

    def test_plan_state_and_failure_lines_are_not_read(self):
        context = FailureContext(strategy="yield", yield_robot="robot_3",
                                 outcome_status="failed", failure_detail="robot_3 blocked")
        plan = PlanStateContext(plan_id=1, legs=[
            PlanStateLeg(robot_id="robot_3", action="yield", status="failed"),
        ])
        payload = build_prompt_payload(
            _request(_s1_lane_snapshot(), failure_context=context, plan_state=plan)
        )
        assert "robot_3" in payload.user_prompt.split("robot_id=robot_3")[1]
        assert echo_involved_robots(payload) == ["robot_1", "robot_2"]

    def test_frozen_v2_template_parses_the_same(self):
        payload = build_prompt_payload(_request(_s1_lane_snapshot(), prompt_version=2))
        assert echo_involved_robots(payload) == ["robot_1", "robot_2"]

    def test_all_moving_falls_back_to_every_listed_robot(self):
        snapshot = SceneSnapshot(stamp=1.0, frame_id="cam", robots=[
            _robot("robot_1", 0.0, 0.0, 0.0, status="MOVING", speed=0.2),
            _robot("robot_2", 1.0, 0.0, 0.0, status="MOVING", speed=0.2),
        ], dropped_frame=False)
        assert echo_involved_robots(build_prompt_payload(_request(snapshot))) == [
            "robot_1", "robot_2"]


def _echo_reasoner(**kwargs) -> Reasoner:
    return Reasoner(EchoMockBackend(**kwargs), ReasonerConfig(backend_id="mock"))


class TestEchoDecision:
    def test_default_is_deadlock_yield_by_the_first_presented_robot(self):
        result = _echo_reasoner().run(_request(_s1_lane_snapshot()))
        decision = result.decision
        assert decision.congestion_detected is True
        assert (decision.type, decision.strategy) == ("deadlock", "yield")
        assert decision.involved_robots == ["robot_1", "robot_2"]
        assert decision.yield_robot == "robot_1"

    def test_passes_the_normal_parser_and_validators(self):
        result = _echo_reasoner().run(_request(_s1_lane_snapshot()))
        assert result.diagnostics.parse_status == "valid"
        assert result.diagnostics.attempts == 1

    def test_configured_strategy_carries_no_yield_robot(self):
        decision = _echo_reasoner(strategy="reverse").run(_request(_s1_lane_snapshot())).decision
        assert decision.strategy == "reverse"
        assert decision.yield_robot is None

    def test_diagnostics_carry_the_echo_marker_and_mock_backend_id(self):
        diagnostics = _echo_reasoner().run(_request(_s1_lane_snapshot())).diagnostics
        assert diagnostics.backend_id == "mock"
        assert diagnostics.mock_mode == "echo"
        assert diagnostics.model_dump(mode="json")["mock_mode"] == "echo"

    def test_default_mock_diagnostics_have_no_marker_key(self):
        reasoner = Reasoner(MockBackend(), ReasonerConfig(backend_id="mock"))
        diagnostics = reasoner.run(_request(_s1_lane_snapshot())).diagnostics
        assert diagnostics.mock_mode is None
        assert "mock_mode" not in diagnostics.model_dump(mode="json")


def _pipeline() -> InProcessPipeline:
    return InProcessPipeline(
        reasoner=_echo_reasoner(),
        ground_fn=ground_reasoner_result,
        scene_geometry=_S1,
        grounding_params=_DYNAMIC,
        stage2_enabled=False,
    )


class TestGroundingEndToEnd:
    def test_echo_decision_grounds_through_the_dynamic_view(self):
        outcome = _pipeline().run(_request(_s1_lane_snapshot()))
        assert outcome.terminal_stage.value == "ok"
        command = outcome.grounded_command
        assert command["actions"][0]["robot_id"] == "robot_1"
        assert command["actions"][0]["action"] == "yield"
        assert "grounding=dynamic_arms:lane:x" in command["degradations"]

    def test_artifact_records_tags_and_the_echo_marker(self, tmp_path):
        snapshot = _s1_lane_snapshot()
        request = _request(snapshot)
        outcome = _pipeline().run(request)
        path = write_decision_artifact(tmp_path, outcome, request=request, snapshot=snapshot)
        payload = json.loads(Path(path).read_text())
        assert payload["diagnostics"]["backend_id"] == "mock"
        assert payload["diagnostics"]["mock_mode"] == "echo"
        assert "grounding=dynamic_arms:lane:x" in payload["grounding_degradations"]
        assert payload["decision"]["justification"].startswith("echo-mock apparatus")


class TestFactoryGuard:
    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch):
        for name in ("VGU_MOCK_ECHO", "VGU_MOCK_ECHO_TYPE", "VGU_MOCK_ECHO_STRATEGY",
                     "VGU_MOCK_DECISION_FILE"):
            monkeypatch.delenv(name, raising=False)

    def test_echo_flag_builds_the_echo_mock(self, monkeypatch):
        monkeypatch.setenv("VGU_MOCK_ECHO", "1")
        assert isinstance(build_backend("mock"), EchoMockBackend)

    def test_echo_flag_off_keeps_the_default_mock(self, monkeypatch):
        monkeypatch.setenv("VGU_MOCK_ECHO", "0")
        backend = build_backend("mock")
        assert type(backend) is MockBackend

    def test_echo_type_and_strategy_come_from_the_environment(self, monkeypatch):
        monkeypatch.setenv("VGU_MOCK_ECHO", "true")
        monkeypatch.setenv("VGU_MOCK_ECHO_TYPE", "Bottleneck")
        monkeypatch.setenv("VGU_MOCK_ECHO_STRATEGY", "temporary_wait")
        decision = Reasoner(build_backend("mock"), ReasonerConfig(backend_id="mock")).run(
            _request(_s1_lane_snapshot())).decision
        assert (decision.type, decision.strategy) == ("bottleneck", "temporary_wait")

    def test_unreachable_from_a_live_backend(self, monkeypatch):
        monkeypatch.setenv("VGU_MOCK_ECHO", "1")
        backend = build_backend(
            "llama_server", LlamaServerBackendConfig(model_id="pinned-model")
        )
        assert isinstance(backend, LlamaServerBackend)

    def test_unreachable_from_the_openai_adapter(self, monkeypatch):
        from reasoning.vlm.models import OpenAIBackendConfig
        from reasoning.vlm.openai_backend import OpenAIBackend

        monkeypatch.setenv("VGU_MOCK_ECHO", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        backend = build_backend("openai", OpenAIBackendConfig(model_id="gpt-4o-2024-08-06"))
        assert isinstance(backend, OpenAIBackend)

    def test_echo_and_decision_file_are_mutually_exclusive(self, monkeypatch, tmp_path):
        decision = tmp_path / "d.json"
        decision.write_text("{}", encoding="utf-8")
        monkeypatch.setenv("VGU_MOCK_ECHO", "1")
        monkeypatch.setenv("VGU_MOCK_DECISION_FILE", str(decision))
        with pytest.raises(ValueError, match="mutually exclusive"):
            build_backend("mock")

    def test_unknown_flag_value_fails_fast(self, monkeypatch):
        monkeypatch.setenv("VGU_MOCK_ECHO", "maybe")
        with pytest.raises(ValueError, match="VGU_MOCK_ECHO"):
            build_backend("mock")

    def test_invalid_strategy_fails_fast(self, monkeypatch):
        monkeypatch.setenv("VGU_MOCK_ECHO", "1")
        monkeypatch.setenv("VGU_MOCK_ECHO_STRATEGY", "teleport")
        with pytest.raises(ValueError, match="VGU_MOCK_ECHO_TYPE/STRATEGY"):
            build_backend("mock")

    def test_none_strategy_is_rejected(self, monkeypatch):
        monkeypatch.setenv("VGU_MOCK_ECHO", "1")
        monkeypatch.setenv("VGU_MOCK_ECHO_STRATEGY", "none")
        with pytest.raises(ValueError, match="cannot be none"):
            build_backend("mock")


_SUPPRESSION_ON = {"enabled": True, "applies_to": "all"}


def _echo_node(node_env, tmp_path, monkeypatch, **overrides):  # noqa: F811
    monkeypatch.setenv("VGU_MOCK_ECHO", "1")
    monkeypatch.delenv("VGU_MOCK_DECISION_FILE", raising=False)
    monkeypatch.delenv("VGU_MOCK_RETREAT_CHOICE_FILE", raising=False)
    node_module, clock = node_env
    overrides.setdefault("t0_probe_mode", False)
    node = node_module.OrchestratorNode(config=_config(tmp_path, **overrides))
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    return node, clock


def _stall(node, clock, advance: float) -> None:
    clock.t += advance
    stamp = clock.t - 900.0
    snapshot = SceneSnapshot(stamp=stamp, frame_id="overhead_camera", robots=[
        RobotView(robot_id="robot_1", x=0.0, y=-0.15, theta=math.pi / 2,
                  linear_velocity=0.0, status="STOPPED", stamp=stamp),
        RobotView(robot_id="robot_2", x=0.0, y=0.15, theta=-math.pi / 2,
                  linear_velocity=0.0, status="STOPPED", stamp=stamp),
    ])
    node._frame_stamp = stamp
    node._on_scene_state(_scene_msg(snapshot))
    if node._future is not None:
        node._future.result(timeout=WAIT_SEC)
        node._on_timer()


def _artifacts(node) -> list[dict]:
    return [json.loads(p.read_text())
            for p in sorted(Path(node._config.decision_log_dir).glob("*.json"))]


class TestEchoLivelockGuard:
    def test_persisting_stall_is_not_reanswered_once_suppression_arms(
        self, node_env, tmp_path, monkeypatch  # noqa: F811
    ):
        node, clock = _echo_node(
            node_env, tmp_path, monkeypatch,
            reanalysis_suppression=_SUPPRESSION_ON, dispatch_enabled=False,
        )
        for _ in range(8):
            _stall(node, clock, advance=16.0)
        artifacts = _artifacts(node)
        assert len(artifacts) == 1
        assert artifacts[0]["diagnostics"]["mock_mode"] == "echo"
        assert node._cmd_pub.published == []
        assert len(node.get_logger().matching("reanalysis suppressed")) == 7

    def test_without_suppression_the_echo_reanswers_every_cooldown(
        self, node_env, tmp_path, monkeypatch  # noqa: F811
    ):
        node, clock = _echo_node(node_env, tmp_path, monkeypatch, dispatch_enabled=False)
        for _ in range(4):
            _stall(node, clock, advance=16.0)
        assert len(_artifacts(node)) == 4

    def test_residual_dispatch_loop_is_bounded_by_cooldown_only(
        self, node_env, tmp_path, monkeypatch  # noqa: F811
    ):
        # Pins the known residual (A12(iii) clause (c)): a dispatched echo
        # command that resolves without moving anyone never arms the
        # suppression, so the unchanged stall is re-answered and re-dispatched
        # once per resolution + cooldown. Step 6 decides whether to close it.
        node, clock = _echo_node(
            node_env, tmp_path, monkeypatch, reanalysis_suppression=_SUPPRESSION_ON
        )
        dispatched: list[str] = []
        for _ in range(3):
            _stall(node, clock, advance=16.0)
            command_ids = {msg.command_id for msg in node._cmd_pub.published}
            new = sorted(command_ids - set(dispatched))
            dispatched.extend(new)
            for command_id in new:
                for robot_id in ("robot_1", "robot_2"):
                    node._on_status(SimpleNamespace(
                        command_id=command_id, robot_id=robot_id, status="FAILED"
                    ))
        assert len(dispatched) == 3
        assert node._suppression.reference is None

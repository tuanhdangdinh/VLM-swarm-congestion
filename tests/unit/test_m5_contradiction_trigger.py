"""prereg-v3 R3.4 contradiction trigger: pure predicates, the monitor, and the node wiring.

The node tests reuse the ROS2-stubbed harness of `test_m5_node_probe.py`.
"""
# ruff: noqa: F811
from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from swarm_orchestrator.contradiction_trigger import (
    ContradictionMonitor,
    evaluate_divergence,
    leg_expectation,
)
from swarm_orchestrator.models import (
    ContradictionTriggerConfig,
    OrchestratorConfig,
    PipelineOutcome,
    RobotView,
    SceneSnapshot,
    TerminalStage,
)

from tests.unit.test_m5_node_junction_clear import _fail_command
from tests.unit.test_m5_node_junction_clear import _node as _junction_node
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _commands,
    _make_node,
    _result,
    _scene_msg,
    _trigger_real,
    node_env,
)

BOUND = 0.5
_ON = ContradictionTriggerConfig(enabled=True, divergence_bound_m=BOUND)


# ---- config ----


def test_contradiction_trigger_config_defaults_off_with_budget_one():
    config = ContradictionTriggerConfig()
    assert config.enabled is False
    assert config.per_event_replan_budget == 1
    assert config.divergence_bound_m > 0.0


def test_contradiction_trigger_config_rejects_non_positive_bound():
    with pytest.raises(ValidationError):
        ContradictionTriggerConfig(divergence_bound_m=0.0)


def test_contradiction_trigger_config_rejects_unknown_key():
    with pytest.raises(ValidationError):
        ContradictionTriggerConfig(enable=True)


def test_shipped_orchestrator_yaml_keeps_both_r3_4_flags_off():
    import yaml
    from swarm_orchestrator.models import load_config

    raw = yaml.safe_load(
        Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml").read_text()
    )
    config = load_config(raw)
    assert config.contradiction_trigger.enabled is False
    assert config.contradiction_trigger.per_event_replan_budget == 1
    assert config.failure_explanation_enabled is False


def test_orchestrator_config_defaults_both_r3_4_flags_off(tmp_path):
    config = OrchestratorConfig(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={},
        frame_dump_dir=str(tmp_path),
    )
    assert config.contradiction_trigger.enabled is False
    assert config.failure_explanation_enabled is False


# ---- divergence predicates, per action type ----


def _yield_2d():
    return leg_expectation(
        "robot_2", "yield", {"retreat_x_m": -1.0, "retreat_y_m": 0.3}, ["yield", "temporary_wait"]
    )


def test_yield_with_retreat_target_approaches_that_point():
    exp = _yield_2d()
    assert exp.kind == "approach_target"
    assert exp.target_xy == (-1.0, 0.3)


def test_yield_divergence_fires_when_distance_rises_past_bound_above_best():
    exp = _yield_2d()
    # Best seen 0.2 m from target; now 0.8 m away: 0.8 > 0.2 + 0.5.
    reading = evaluate_divergence(exp, (0.0, 0.3), (-0.2, 0.3), 0.2, BOUND)
    assert reading.diverged is True
    assert reading.measured_m == pytest.approx(0.8)
    assert reading.allowed_m == pytest.approx(0.7)


def test_yield_divergence_tolerates_recession_within_bound():
    exp = _yield_2d()
    reading = evaluate_divergence(exp, (0.0, 0.3), (-0.4, 0.3), 0.2, BOUND)
    assert reading.diverged is False


def test_yield_divergence_ignores_a_slow_approach():
    exp = _yield_2d()
    # Still 1.0 m out but never farther than its best: not a contradiction.
    reading = evaluate_divergence(exp, (0.0, 0.3), (0.0, 0.3), 1.0, BOUND)
    assert reading.diverged is False


def test_yield_with_legacy_park_axis_measures_one_dimension():
    exp = leg_expectation(
        "robot_1", "yield", {"park_axis": "x", "park_coord_m": 1.8}, ["yield"]
    )
    assert exp.kind == "approach_target"
    assert exp.target_axis == "x"
    # y is ignored: 1.0 m lateral offset, x on target.
    reading = evaluate_divergence(exp, (1.0, 0.0), (1.8, 1.0), 0.0, BOUND)
    assert reading.measured_m == pytest.approx(0.0)
    assert reading.diverged is False
    assert evaluate_divergence(exp, (1.0, 0.0), (1.1, 0.0), 0.1, BOUND).diverged is True


def test_yield_without_grounded_target_is_not_watched_for_divergence():
    assert leg_expectation("robot_2", "yield", {"backup_distance_m": 0.8}, ["yield"]) is None


def test_reverse_bounds_travel_by_backup_distance_plus_bound():
    exp = leg_expectation("robot_1", "reverse", {"backup_distance_m": 0.8}, ["reverse"])
    assert exp.kind == "bounded_travel"
    assert evaluate_divergence(exp, (0.0, 0.0), (1.29, 0.0), math.inf, BOUND).diverged is False
    reading = evaluate_divergence(exp, (0.0, 0.0), (1.31, 0.0), math.inf, BOUND)
    assert reading.diverged is True
    assert reading.allowed_m == pytest.approx(1.3)


def test_reverse_is_heading_free_in_either_direction():
    exp = leg_expectation("robot_1", "reverse", {"backup_distance_m": 0.8}, ["reverse"])
    assert evaluate_divergence(exp, (0.0, 0.0), (-1.31, 0.0), math.inf, BOUND).diverged is True


def test_reverse_without_distance_uses_m4_default_backup():
    exp = leg_expectation("robot_1", "reverse", {}, ["reverse"])
    assert exp.travel_m == pytest.approx(0.3)


def test_standalone_wait_must_stay_within_bound_of_anchor():
    exp = leg_expectation(
        "robot_1", "temporary_wait", {"duration_sec": 5.0}, ["temporary_wait", "temporary_wait"]
    )
    assert exp.kind == "stationary"
    assert evaluate_divergence(exp, (0.0, 0.0), (0.0, 0.49), math.inf, BOUND).diverged is False
    assert evaluate_divergence(exp, (0.0, 0.0), (0.0, 0.51), math.inf, BOUND).diverged is True


def test_wait_linked_to_a_yield_is_not_watched():
    # M4 releases or escorts a yield's linked wait through the gap while ACTIVE.
    assert leg_expectation("robot_1", "temporary_wait", {}, ["yield", "temporary_wait"]) is None


def test_wait_linked_to_a_reverse_is_not_watched():
    assert leg_expectation("robot_1", "temporary_wait", {}, ["reverse", "temporary_wait"]) is None


def test_reroute_is_not_watched_for_divergence():
    assert leg_expectation("robot_1", "reroute", {"goal": {"x": 1, "y": 0}}, ["reroute"]) is None


# ---- monitor ----


def _monitor(budget: int = 1) -> ContradictionMonitor:
    return ContradictionMonitor(BOUND, budget)


def _watch_yield(monitor: ContradictionMonitor, command_id: str = "c1", episode: int = 0) -> None:
    monitor.watch(
        command_id,
        [
            ("robot_2", "yield", {"retreat_x_m": -1.0, "retreat_y_m": 0.0}),
            ("robot_1", "temporary_wait", {"duration_sec": 9.0}),
        ],
        episode,
        ("robot_1", "robot_2"),
    )


def _all_active(_command_id: str, _robot_id: str) -> bool:
    return True


def test_monitor_arms_leg_failed_for_a_watched_command():
    monitor = _monitor()
    _watch_yield(monitor)
    armed = monitor.on_leg_failed("c1", "robot_2")
    assert armed.cause == "leg_failed"
    assert armed.action == "yield"
    assert armed.robot_ids == ("robot_2", "robot_1")
    assert armed.trigger_robot_ids == ("robot_1", "robot_2")


def test_monitor_ignores_failure_of_an_unwatched_command():
    assert _monitor().on_leg_failed("junction-phase", "robot_2") is None


def test_monitor_arms_only_the_first_contradiction_per_command():
    monitor = _monitor()
    _watch_yield(monitor)
    monitor.on_leg_failed("c1", "robot_2")
    assert monitor.on_leg_failed("c1", "robot_1") is None


def test_monitor_skips_legs_that_are_not_active():
    monitor = _monitor()
    _watch_yield(monitor)
    armed = monitor.observe({"robot_2": (5.0, 0.0)}, lambda _c, _r: False)
    assert armed == []


def test_monitor_anchors_at_first_active_scene_and_arms_divergence():
    monitor = _monitor()
    _watch_yield(monitor)
    assert monitor.observe({"robot_2": (0.0, 0.0)}, _all_active) == []
    assert monitor.observe({"robot_2": (-0.7, 0.0)}, _all_active) == []
    armed = monitor.observe({"robot_2": (0.0, 0.0)}, _all_active)
    assert len(armed) == 1
    assert armed[0].cause == "divergence"
    assert armed[0].measured_m == pytest.approx(1.0)
    assert armed[0].allowed_m == pytest.approx(0.8)
    assert "cause=divergence" in armed[0].log_fields()


def test_monitor_skips_robots_missing_from_the_scene():
    monitor = _monitor()
    _watch_yield(monitor)
    assert monitor.observe({}, _all_active) == []


def test_take_for_resolution_hands_back_the_contradiction_once():
    monitor = _monitor()
    _watch_yield(monitor)
    monitor.on_leg_failed("c1", "robot_2")
    assert monitor.take_for_resolution("c1").cause == "leg_failed"
    assert monitor.take_for_resolution("c1") is None
    assert monitor.is_watched("c1") is False


def test_budget_is_kept_per_episode():
    monitor = _monitor(budget=1)
    assert monitor.budget_remaining(0) is True
    monitor.charge(0)
    assert monitor.budget_remaining(0) is False
    assert monitor.budget_remaining(1) is True


def test_zero_budget_never_allows_an_early_reanalysis():
    assert _monitor(budget=0).budget_remaining(0) is False


# ---- node wiring ----


class _CommandPipeline:
    """Grounds a fixed command shape, one fresh command_id per request."""

    def __init__(self, actions: list[dict]) -> None:
        self.actions = actions
        self.run_calls: list[str] = []

    def run(self, request):
        self.run_calls.append(request.request_id)
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id),
            grounded_command={
                "command_id": f"cmd-{request.request_id}",
                "actions": self.actions,
                "expected_resolution_time_sec": 18.0,
                "fallback": "stop",
            },
            terminal_stage=TerminalStage.OK,
        )

    def analyze(self, request):  # pragma: no cover - probes are off here
        raise AssertionError("no probe expected")


_YIELD_ACTIONS = [
    {"robot_id": "robot_2", "action": "yield", "parameters": {"backup_distance_m": 0.8}},
    {"robot_id": "robot_1", "action": "temporary_wait", "parameters": {"duration_sec": 9.0}},
]
_TARGETED_YIELD_ACTIONS = [
    {
        "robot_id": "robot_2",
        "action": "yield",
        "parameters": {"backup_distance_m": 0.8, "retreat_x_m": -1.0, "retreat_y_m": 0.15},
    },
    {"robot_id": "robot_1", "action": "temporary_wait", "parameters": {"duration_sec": 9.0}},
]


def _node(node_env, tmp_path, actions=None, **overrides):  # noqa: F811
    pipeline = _CommandPipeline(actions or _YIELD_ACTIONS)
    overrides.setdefault("t0_probe_mode", False)
    node, clock = _make_node(node_env, tmp_path, pipeline, **overrides)
    return node, clock, pipeline


def _finish_analysis(node) -> None:
    node._future.result(timeout=WAIT_SEC)
    node._on_timer()


def _status(node, command_id: str, robot_id: str, status: str) -> None:
    node._on_status(SimpleNamespace(command_id=command_id, robot_id=robot_id, status=status))


def _fail_yield(node, command_id: str) -> None:
    _status(node, command_id, "robot_2", "FAILED")
    _status(node, command_id, "robot_1", "COMPLETED")


def _artifact(node, request_id: str) -> dict:
    path = Path(node._config.decision_log_dir) / f"{request_id}.json"
    return json.loads(path.read_text())


def _first_dispatch(node, pipeline) -> str:
    _trigger_real(node)
    _finish_analysis(node)
    return f"cmd-{pipeline.run_calls[0]}"


def test_trigger_off_failed_leg_starts_no_early_analysis(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path)
    command_id = _first_dispatch(node, pipeline)

    _fail_yield(node, command_id)

    assert node._future is None
    assert len(pipeline.run_calls) == 1
    assert node.get_logger().matching("contradiction") == []


def test_trigger_off_artifact_has_no_trigger_keys(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path)
    _first_dispatch(node, pipeline)

    payload = _artifact(node, pipeline.run_calls[0])
    assert "trigger_source" not in payload
    assert "trigger_contradiction" not in payload


def test_trigger_on_stall_artifact_records_stall_source(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path, contradiction_trigger=_ON)
    _first_dispatch(node, pipeline)

    payload = _artifact(node, pipeline.run_calls[0])
    assert payload["trigger_source"] == "stall"
    assert "trigger_contradiction" not in payload


def test_failed_leg_fires_early_analysis_inside_cooldown(node_env, tmp_path):
    node, clock, pipeline = _node(node_env, tmp_path, contradiction_trigger=_ON)
    command_id = _first_dispatch(node, pipeline)

    _fail_yield(node, command_id)

    # The resolution just started the cooldown, yet the analysis is running.
    assert {"robot_1", "robot_2"} <= node._cooldown.active_robots(clock.t)
    assert node._future is not None
    _finish_analysis(node)
    assert len(pipeline.run_calls) == 2


def test_contradiction_artifact_records_trigger_source_and_cause(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path, contradiction_trigger=_ON)
    command_id = _first_dispatch(node, pipeline)
    _fail_yield(node, command_id)
    _finish_analysis(node)

    payload = _artifact(node, pipeline.run_calls[1])
    assert payload["trigger_source"] == "contradiction"
    assert payload["trigger_contradiction"]["cause"] == "leg_failed"
    assert payload["trigger_contradiction"]["command_id"] == command_id
    assert payload["trigger_contradiction"]["robot_id"] == "robot_2"
    assert payload["failure_context"]["outcome_status"] == "failed"


def test_contradiction_logs_structured_cause_lines(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path, contradiction_trigger=_ON)
    command_id = _first_dispatch(node, pipeline)
    _fail_yield(node, command_id)

    log = node.get_logger()
    armed = log.matching("contradiction armed")
    assert armed == [
        f"contradiction armed cause=leg_failed command={command_id} robot=robot_2 "
        "action=yield episode=0"
    ]
    fired = log.matching("contradiction trigger fired")
    assert len(fired) == 1
    assert "cause=leg_failed" in fired[0]
    assert "budget_used=1/1" in fired[0]
    assert any(
        "trigger_source=contradiction" in line for line in log.matching("starting analysis")
    )


def test_second_contradiction_in_same_episode_does_not_retrigger(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path, contradiction_trigger=_ON)
    command_id = _first_dispatch(node, pipeline)
    _fail_yield(node, command_id)
    _finish_analysis(node)
    second_command = f"cmd-{pipeline.run_calls[1]}"

    _fail_yield(node, second_command)

    assert node._future is None
    assert len(pipeline.run_calls) == 2
    suppressed = node.get_logger().matching("contradiction trigger suppressed")
    assert len(suppressed) == 1
    assert "reason=budget_exhausted" in suppressed[0]
    assert "budget_used=1/1" in suppressed[0]


def test_repeated_terminal_status_fires_only_once(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path, contradiction_trigger=_ON)
    command_id = _first_dispatch(node, pipeline)
    _fail_yield(node, command_id)
    _finish_analysis(node)

    # M4 republishes terminal statuses at 0.25 s and 0.75 s.
    _fail_yield(node, command_id)

    assert len(pipeline.run_calls) == 2
    assert node._future is None


def test_contradiction_respects_exhausted_robots(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path, contradiction_trigger=_ON)
    command_id = _first_dispatch(node, pipeline)
    node._exhausted_robots.add("robot_2")

    _fail_yield(node, command_id)

    assert node._future is None
    assert len(pipeline.run_calls) == 1
    suppressed = node.get_logger().matching("contradiction trigger suppressed")
    assert len(suppressed) == 1
    assert "reason=exhausted_robots" in suppressed[0]


def test_exhausted_suppression_does_not_spend_the_budget(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path, contradiction_trigger=_ON)
    command_id = _first_dispatch(node, pipeline)
    node._exhausted_robots.add("robot_2")

    _fail_yield(node, command_id)

    assert node._contradictions.budget_used(0) == 0


def test_contradiction_is_suppressed_while_a_junction_sequence_runs(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path, contradiction_trigger=_ON)
    command_id = _first_dispatch(node, pipeline)
    node._junction_phase_queues["other-junction-phase"] = object()

    _fail_yield(node, command_id)

    assert node._future is None
    suppressed = node.get_logger().matching("contradiction trigger suppressed")
    assert len(suppressed) == 1
    assert "reason=junction_sequence_active" in suppressed[0]
    assert node._contradictions.budget_used(0) == 0


def test_completed_command_without_contradiction_fires_nothing(node_env, tmp_path):
    node, _clock, pipeline = _node(node_env, tmp_path, contradiction_trigger=_ON)
    command_id = _first_dispatch(node, pipeline)

    _status(node, command_id, "robot_2", "COMPLETED")
    _status(node, command_id, "robot_1", "COMPLETED")

    assert node._future is None
    assert node.get_logger().matching("contradiction") == []


def _scene(stamp: float, robot_2_x: float) -> SceneSnapshot:
    return SceneSnapshot(
        stamp=stamp,
        frame_id="overhead_camera",
        robots=[
            RobotView(robot_id="robot_1", x=0.6, y=-0.15, theta=0.0,
                      linear_velocity=0.0, status="STOPPED", stamp=stamp),
            RobotView(robot_id="robot_2", x=robot_2_x, y=0.15, theta=3.14,
                      linear_velocity=0.0, status="STOPPED", stamp=stamp),
        ],
    )


def _feed(node, stamp: float, robot_2_x: float) -> None:
    node._frame_stamp = stamp
    node._on_scene_state(_scene_msg(_scene(stamp, robot_2_x)))


def test_divergent_yield_fires_early_analysis_on_resolution(node_env, tmp_path):
    node, _clock, pipeline = _node(
        node_env, tmp_path, actions=_TARGETED_YIELD_ACTIONS, contradiction_trigger=_ON
    )
    command_id = _first_dispatch(node, pipeline)
    _status(node, command_id, "robot_2", "ACTIVE")
    _feed(node, 61.0, 0.0)  # 1.0 m from the retreat target: anchor
    _feed(node, 62.0, -0.8)  # 0.2 m: best
    assert node.get_logger().matching("contradiction armed") == []
    _feed(node, 63.0, 0.0)  # 1.0 m > 0.2 + 0.5

    armed = node.get_logger().matching("contradiction armed")
    assert len(armed) == 1
    assert "cause=divergence" in armed[0]
    assert "robot=robot_2" in armed[0]
    assert node._future is None  # never mid-maneuver

    _status(node, command_id, "robot_2", "COMPLETED")
    _status(node, command_id, "robot_1", "COMPLETED")
    _finish_analysis(node)

    payload = _artifact(node, pipeline.run_calls[1])
    assert payload["trigger_source"] == "contradiction"
    assert payload["trigger_contradiction"]["cause"] == "divergence"


def test_stale_robot_is_not_evaluated_for_divergence(node_env, tmp_path):
    node, _clock, pipeline = _node(
        node_env, tmp_path, actions=_TARGETED_YIELD_ACTIONS, contradiction_trigger=_ON
    )
    command_id = _first_dispatch(node, pipeline)
    _status(node, command_id, "robot_2", "ACTIVE")
    _feed(node, 61.0, -0.8)
    stale = _scene(62.0, 3.0)
    stale = stale.model_copy(
        update={"robots": [stale.robots[0], stale.robots[1].model_copy(update={"status": "STALE"})]}
    )
    node._frame_stamp = 62.0
    node._on_scene_state(_scene_msg(stale))

    assert node.get_logger().matching("contradiction armed") == []


def test_junction_clear_sequence_is_never_watched(node_env, tmp_path):
    from tests.unit.test_m5_node_junction_clear import _dispatch_via_handle_outcome

    node, clock = _junction_node(node_env, tmp_path, contradiction_trigger=_ON)
    _dispatch_via_handle_outcome(node, clock)
    first_id = _commands(node)[0].command_id
    assert node._contradictions.is_watched(first_id) is False

    _fail_command(node, first_id)

    assert node.get_logger().matching("contradiction") == []
    assert node._future is None

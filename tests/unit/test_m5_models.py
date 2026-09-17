"""Unit tests for M5 orchestrator Pydantic contracts and parsing helpers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from swarm_orchestrator.models import (
    CongestionEvent,
    OrchestratorConfig,
    PipelineOutcome,
    TaskAssignment,
    TerminalStage,
    load_config,
    parse_scene_snapshot,
)

from reasoning.vlm.models import ReasonerDiagnostics, ReasonerResult


def test_task_assignment_holds_task_and_goal():
    a = TaskAssignment(task="pick_a", goal=(3.0, 1.5))
    assert a.task == "pick_a"
    assert a.goal == (3.0, 1.5)


def test_congestion_event_rejects_empty_robots():
    with pytest.raises(ValidationError):
        CongestionEvent(
            involved_robots=[],
            stall_durations_sec={},
            detected_at=1.0,
            reason="x",
        )


def test_congestion_event_sorts_involved_robots():
    e = CongestionEvent(
        involved_robots=["robot_2", "robot_0"],
        stall_durations_sec={"robot_0": 12.0, "robot_2": 13.0},
        detected_at=1.0,
        reason="stall",
    )
    assert e.involved_robots == ["robot_0", "robot_2"]


def test_orchestrator_config_rejects_negative_threshold():
    with pytest.raises(ValidationError):
        OrchestratorConfig(
            stall_threshold_sec=-1.0,
            progress_epsilon_m=0.1,
            cooldown_sec=15.0,
            command_timeout_sec=20.0,
            reasoning_backend_id="mock",
            initial_tasks={"robot_0": TaskAssignment(task="t", goal=(0.0, 0.0))},
            frame_dump_dir="data/logs/m5_frames",
        )


def test_load_config_parses_nested_yaml_dict_with_goal_lists():
    raw = {
        "stall_threshold_sec": 12.0,
        "progress_epsilon_m": 0.1,
        "cooldown_sec": 15.0,
        "command_timeout_sec": 20.0,
        "reasoning_backend_id": "mock",
        "frame_dump_dir": "data/logs/m5_frames",
        "initial_tasks": {
            "robot_0": {"task": "pick_a", "goal": [3.0, 1.5]},
            "robot_1": {"task": "pick_b", "goal": [4.0, 2.0]},
        },
    }
    cfg = load_config(raw)
    assert cfg.initial_tasks["robot_0"].goal == (3.0, 1.5)
    assert cfg.frame_downscale_width is None  # default
    assert cfg.decision_log_dir == "data/logs/m5_decisions"


def test_shipped_orchestrator_yaml_goals_stay_inside_camera_roi():
    # +-3.0 is exactly the camera ROI edge (roi_width_m: 6.0), so a marker at
    # its goal is half off-frame and undetectable by M1; +-2.5 keeps 0.5 m of
    # margin (~107 px at 1280 px / 6.0 m).
    path = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
    cfg = load_config(yaml.safe_load(path.read_text(encoding="utf-8")))

    assert cfg.initial_tasks["robot_1"].goal == (2.5, 0.0)
    assert cfg.initial_tasks["robot_2"].goal == (-2.5, 0.0)


def test_orchestrator_config_loads_scenario_geometry_from_yaml():
    # The shipped config declares the head_on_deadlock corridor so M3 derives
    # the yield park offset instead of using its hardcoded fallback.
    path = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
    cfg = load_config(yaml.safe_load(path.read_text(encoding="utf-8")))

    assert cfg.scenario_geometry is not None
    assert cfg.scenario_geometry.corridor.half_length_m == 1.0
    assert cfg.scenario_geometry.corridor.axis == "x"
    assert cfg.scenario_geometry.robot.safety_radius_m == 0.45


def test_orchestrator_config_without_geometry_is_none():
    cfg = load_config(_minimal_config_dict())

    assert cfg.scenario_geometry is None


def test_load_config_raises_on_missing_required_field():
    with pytest.raises(ValidationError):
        load_config({"progress_epsilon_m": 0.1})  # missing stall_threshold_sec etc.


def _minimal_config_dict():
    return {
        "stall_threshold_sec": 12.0,
        "progress_epsilon_m": 0.1,
        "cooldown_sec": 15.0,
        "command_timeout_sec": 20.0,
        "reasoning_backend_id": "mock",
        "frame_dump_dir": "data/logs/m5_frames",
        "initial_tasks": {"robot_0": {"task": "t", "goal": [0.0, 0.0]}},
    }


def test_load_config_uses_default_topic_names_when_absent():
    cfg = load_config(_minimal_config_dict())
    assert cfg.topics["scene_state"] == "/perception/scene_state"
    assert cfg.topics["trigger_analysis"] == "/orchestrator/trigger_analysis"


def test_load_config_overrides_only_named_topics():
    raw = _minimal_config_dict()
    raw["topics"] = {"scene_state": "/sim/scene_state"}
    cfg = load_config(raw)
    assert cfg.topics["scene_state"] == "/sim/scene_state"  # overridden
    assert cfg.topics["coordination_commands"] == "/coordination/commands"  # default kept


def test_parse_scene_snapshot_extracts_robots_and_dropped_frame():
    raw = json.dumps(
        {
            "stamp": 5.0,
            "frame_id": "cam0",
            "robots": [
                {
                    "robot_id": "robot_0",
                    "x": 1.0,
                    "y": 2.0,
                    "theta": 0.0,
                    "linear_velocity": 0.0,
                    "angular_velocity": 0.0,
                    "task": "pick_a",
                    "status": "STOPPED",
                    "goal": [3.0, 1.5],
                    "stamp": 5.0,
                }
            ],
            "diagnostics": {"dropped_frame": False},
        }
    )
    snap = parse_scene_snapshot(raw)
    assert snap.stamp == 5.0
    assert snap.frame_id == "cam0"
    assert snap.dropped_frame is False
    assert snap.robots[0].robot_id == "robot_0"
    assert snap.robots[0].status == "STOPPED"


def test_parse_scene_snapshot_reads_dropped_frame_true_from_diagnostics():
    raw = json.dumps(
        {"stamp": 6.0, "frame_id": "cam0", "robots": [], "diagnostics": {"dropped_frame": True}}
    )
    snap = parse_scene_snapshot(raw)
    assert snap.dropped_frame is True
    assert snap.robots == []


def test_parse_scene_snapshot_raises_on_malformed_json():
    with pytest.raises(ValueError):
        parse_scene_snapshot("{not json")


def test_pipeline_outcome_carries_terminal_stage_enum():
    diag = ReasonerDiagnostics(
        request_id="r1", backend_id="mock", attempts=1, parse_status="failed"
    )
    result = ReasonerResult(request_id="r1", decision=None, raw_text=None, diagnostics=diag)
    outcome = PipelineOutcome(
        request_id="r1",
        reasoner_result=result,
        grounded_command=None,
        terminal_stage=TerminalStage.VLM,
        failure_reason="decision=None",
    )
    assert outcome.terminal_stage is TerminalStage.VLM
    assert outcome.grounded_command is None


def _config_with(**overrides):
    base = dict(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={"robot_0": TaskAssignment(task="t", goal=(0.0, 0.0))},
        frame_dump_dir="data/logs/m5_frames",
    )
    base.update(overrides)
    return OrchestratorConfig(**base)


def test_orchestrator_config_failure_context_window_defaults_to_60():
    assert _config_with().failure_context_window_sec == 60.0


def test_orchestrator_config_rejects_failure_context_window_inside_retrigger_bound():
    # cooldown 15 + stall 12 = 27: a 27 s window can never fire
    with pytest.raises(ValidationError, match="can never fire"):
        _config_with(failure_context_window_sec=27.0)


def test_orchestrator_config_accepts_zero_failure_context_window_as_disabled():
    assert _config_with(failure_context_window_sec=0.0).failure_context_window_sec == 0.0


def test_orchestrator_config_accepts_failure_context_window_above_bound():
    assert _config_with(failure_context_window_sec=27.5).failure_context_window_sec == 27.5


def test_orchestrator_config_arrived_radius_defaults_to_half_metre():
    assert _config_with().arrived_radius_m == 0.5


def test_congestion_event_distance_to_goal_defaults_to_empty():
    event = CongestionEvent(
        involved_robots=["robot_0"],
        stall_durations_sec={"robot_0": 12.0},
        detected_at=1.0,
        reason="x",
    )
    assert event.distance_to_goal_m == {}

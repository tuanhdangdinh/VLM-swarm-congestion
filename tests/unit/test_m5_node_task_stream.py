"""Node-level tests for the v3 S1 task-stream mode (ROS2 stubbed).

Uses the ROS2 stand-ins of `test_m5_node_probe`; registry, arrival gate,
detector, artifact write and the task-stream tracker are the real code.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from swarm_orchestrator.models import RobotView, SceneSnapshot, TaskStreamConfig

from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _artifact,
    _config,
    _FakePipeline,
    node_env,
)

NODES = {"A": (2.0, 0.0), "B": (-2.0, 0.0), "C": (0.0, 1.5)}
START = {"robot_1": "B", "robot_2": "C"}
STAGGER = 4.0
DWELL = 5.0


def _stream(**overrides) -> TaskStreamConfig:
    base = dict(
        enabled=True, nodes=NODES, seed=42, start_nodes=START,
        release_stagger_wall_sec=STAGGER, dwell_sim_sec=DWELL, tasks_per_robot=3,
    )
    base.update(overrides)
    return TaskStreamConfig(**base)


def _make(node_env, tmp_path, stream: TaskStreamConfig | None = None, **overrides):  # noqa: F811
    node_module, clock = node_env
    overrides.setdefault("stall_threshold_sec", 30.0)
    config = _config(
        tmp_path,
        t0_probe_mode=False,
        task_stream=_stream() if stream is None else stream,
        **overrides,
    )
    pipeline = _FakePipeline()
    node = node_module.OrchestratorNode(config=config, pipeline=pipeline)
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    return node, clock, pipeline


def _scene(stamp: float, positions: dict[str, tuple[float, float]], dropped: bool = False):
    snapshot = SceneSnapshot(
        stamp=stamp,
        frame_id="overhead_camera",
        robots=[
            RobotView(robot_id=rid, x=xy[0], y=xy[1], theta=0.0, linear_velocity=0.0,
                      status="STOPPED", stamp=stamp)
            for rid, xy in positions.items()
        ],
    )
    payload = snapshot.model_dump(mode="json")
    payload.pop("dropped_frame")
    payload["diagnostics"] = {"dropped_frame": True} if dropped else {}
    return SimpleNamespace(data=json.dumps(payload))


def _feed(node, stamp: float, positions: dict[str, tuple[float, float]], dropped=False):
    node._frame_stamp = stamp
    node._on_scene_state(_scene(stamp, positions, dropped))


def _nav2_success(node, robot_id: str) -> None:
    node._on_status(
        SimpleNamespace(command_id="base_mission", robot_id=robot_id, status="COMPLETED")
    )


def _registry(node) -> dict:
    return json.loads(node._tasks_pub.published[-1].data)


def _tasks_log(node) -> list[dict]:
    path = node._tasks_log_path
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def _task(node, robot_id: str, index: int):
    return node._task_stream.plan.tasks[robot_id][index]


def _positions(node, robot_1=None, robot_2=None) -> dict[str, tuple[float, float]]:
    return {
        "robot_1": robot_1 if robot_1 is not None else NODES[START["robot_1"]],
        "robot_2": robot_2 if robot_2 is not None else NODES[START["robot_2"]],
    }


def _arrive_robot_1(node, stamp: float) -> None:
    goal = _task(node, "robot_1", 0).goal
    _feed(node, stamp, _positions(node, robot_1=goal))
    _nav2_success(node, "robot_1")


class TestStreamOff:
    def test_registry_payload_byte_identical_when_disabled(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path, stream=TaskStreamConfig())
        assert node._tasks_pub.published[-1].data == (
            '{"robot_1": {"goal": [2.5, -0.35], "task": "t"}, '
            '"robot_2": {"goal": [-2.5, 0.35], "task": "t"}}'
        )

    def test_no_tasks_log_when_disabled(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path, stream=TaskStreamConfig())
        _feed(node, 50.0, {"robot_1": (0.0, 0.0), "robot_2": (1.0, 0.0)})
        assert node._task_stream is None
        assert list(Path(tmp_path / "decisions").glob("tasks_*")) == []

    def test_no_task_stream_log_lines_when_disabled(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path, stream=TaskStreamConfig())
        assert node.get_logger().matching("task_stream") == []


class TestStartup:
    def test_initial_registry_carries_first_tasks_and_holds_later_robot(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, _clock, _ = _make(node_env, tmp_path)
        registry = _registry(node)
        assert registry["robot_1"]["goal"] == list(_task(node, "robot_1", 0).goal)
        assert registry["robot_1"]["task"] == "pickup"
        assert "start_pending" not in registry["robot_1"]
        assert registry["robot_2"]["start_pending"] is True
        assert registry["robot_2"]["goal"] == list(_task(node, "robot_2", 0).goal)

    def test_tasks_log_opens_with_stream_start_schedule(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        records = _tasks_log(node)
        assert records[0]["event"] == "stream_start"
        assert records[0]["seed"] == 42
        assert records[0]["start_nodes"] == START
        assert records[0]["release_offsets_wall_sec"] == {"robot_1": 0.0, "robot_2": STAGGER}
        assert records[0]["session_id"] == node._session_id
        assert [r["event"] for r in records[1:]] == ["released", "issued", "manifest"]
        assert records[2]["robot_id"] == "robot_1"

    def test_tasks_log_lives_beside_decision_artifacts(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        assert node._tasks_log_path == (
            Path(tmp_path / "decisions") / f"tasks_{node._session_id}.jsonl"
        )

    def test_release_after_stagger_issues_held_robot_first_task(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, clock, _ = _make(node_env, tmp_path)
        _feed(node, 50.0, _positions(node))
        clock.t += STAGGER
        node._on_timer()
        assert "start_pending" not in _registry(node)["robot_2"]
        released = [r for r in _tasks_log(node) if r["event"] == "released"]
        assert released[-1]["robot_id"] == "robot_2"
        assert released[-1]["sim_t"] == 50.0

    def test_release_not_before_stagger(self, node_env, tmp_path):  # noqa: F811
        node, clock, _ = _make(node_env, tmp_path)
        clock.t += STAGGER - 0.1
        node._on_timer()
        assert node._registry.is_pending("robot_2")

    def test_release_before_any_scene_is_warned_and_recorded(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, clock, _ = _make(node_env, tmp_path)
        clock.t += STAGGER
        node._on_timer()
        assert node.get_logger().matching("task_stream release before any scene")
        assert any(r["event"] == "release_before_scene" for r in _tasks_log(node))

    def test_release_after_a_scene_is_not_warned(self, node_env, tmp_path):  # noqa: F811
        node, clock, _ = _make(node_env, tmp_path)
        _feed(node, 50.0, _positions(node))
        clock.t += STAGGER
        node._on_timer()
        assert node.get_logger().matching("release before any scene") == []

    def test_start_check_warns_on_start_node_mismatch(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        _feed(node, 50.0, _positions(node, robot_1=(0.0, -1.0)))
        check = next(r for r in _tasks_log(node) if r["event"] == "start_check")
        assert check["offsets_m"]["robot_2"] == 0.0
        assert check["offsets_m"]["robot_1"] > 2.0
        assert node.get_logger().matching("task_stream start node mismatch")


class TestDwellAndIssuance:
    def test_accepted_arrival_keeps_goal_through_dwell(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        _arrive_robot_1(node, 50.0)
        _feed(node, 54.9, _positions(node, robot_1=_task(node, "robot_1", 0).goal))
        assert _registry(node)["robot_1"]["goal"] == list(_task(node, "robot_1", 0).goal)
        assert node._task_stream.phase("robot_1") == "dwelling"

    def test_dwell_end_issues_next_task_as_registry_goal(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        _arrive_robot_1(node, 50.0)
        _feed(node, 55.0, _positions(node, robot_1=_task(node, "robot_1", 0).goal))
        entry = _registry(node)["robot_1"]
        assert entry["goal"] == list(_task(node, "robot_1", 1).goal)
        assert entry["task"] == "delivery"

    def test_rejected_arrival_does_not_start_dwell(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        goal = _task(node, "robot_1", 0).goal
        _feed(node, 50.0, _positions(node, robot_1=(goal[0], goal[1] + 1.0)))
        _nav2_success(node, "robot_1")
        _feed(node, 60.0, _positions(node, robot_1=(goal[0], goal[1] + 1.0)))
        assert node._task_stream.phase("robot_1") == "traveling"
        assert _registry(node)["robot_1"]["goal"] == list(goal)

    def test_late_accepted_arrival_starts_dwell_from_that_scene(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, _clock, _ = _make(node_env, tmp_path)
        goal = _task(node, "robot_1", 0).goal
        _feed(node, 50.0, _positions(node, robot_1=(goal[0], goal[1] + 1.0)))
        _nav2_success(node, "robot_1")
        _feed(node, 52.0, _positions(node, robot_1=goal))
        assert node._task_stream.phase("robot_1") == "dwelling"
        _feed(node, 56.9, _positions(node, robot_1=goal))
        assert node._task_stream.current_task("robot_1").task_index == 0
        _feed(node, 57.0, _positions(node, robot_1=goal))
        assert node._task_stream.current_task("robot_1").task_index == 1

    def test_dropped_frame_does_not_advance_dwell(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        _arrive_robot_1(node, 50.0)
        _feed(node, 80.0, _positions(node, robot_1=_task(node, "robot_1", 0).goal), dropped=True)
        assert node._task_stream.phase("robot_1") == "dwelling"

    def test_clock_reset_warned_once_and_recorded(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        goal = _task(node, "robot_1", 0).goal
        _arrive_robot_1(node, 50.0)
        _feed(node, 3.0, _positions(node, robot_1=goal))
        _feed(node, 9.0, _positions(node, robot_1=goal))
        assert len(node.get_logger().matching("task_stream clock reset")) == 1
        resets = [r for r in _tasks_log(node) if r["event"] == "clock_reset"]
        assert resets == [resets[0]]
        assert resets[0]["prev_sim_t"] == 50.0
        assert node._task_stream.phase("robot_1") == "dwelling"

    def test_dwelling_robot_raises_no_stall(self, node_env, tmp_path):  # noqa: F811
        node, clock, pipeline = _make(node_env, tmp_path, stall_threshold_sec=2.0)
        goal = _task(node, "robot_1", 0).goal
        # 0.3 m off: inside the arrival tolerance (0.35) but outside
        # goal_reached_tolerance_m (0.15), so only the arrival mark -- held
        # because the registry goal stays the node -- excuses the dwell.
        parked = (goal[0] + 0.3, goal[1])
        _feed(node, 50.0, _positions(node, robot_1=parked))
        _nav2_success(node, "robot_1")
        for step in range(1, 5):
            clock.t += 5.0
            _feed(node, 50.0 + step, _positions(node, robot_1=parked))
        assert node._task_stream.phase("robot_1") == "dwelling"
        assert pipeline.run_calls == []

    def test_issue_mid_command_keeps_override(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        goal = _task(node, "robot_1", 0).goal
        _arrive_robot_1(node, 50.0)
        node._registry.set_override("robot_1", "yield", goal, "cmd-x")
        _feed(node, 55.0, _positions(node, robot_1=goal))
        assert _registry(node)["robot_1"]["task"] == "yield"
        assert _registry(node)["robot_1"]["goal"] == list(goal)
        node._registry.clear_override("robot_1")
        assert node._registry.effective("robot_1") == (
            "delivery", _task(node, "robot_1", 1).goal
        )

    def test_issued_record_shape(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        _arrive_robot_1(node, 50.0)
        _feed(node, 55.0, _positions(node, robot_1=_task(node, "robot_1", 0).goal))
        issued = [r for r in _tasks_log(node) if r["event"] == "issued"][-1]
        assert set(issued) == {
            "event", "robot_id", "task_index", "node", "label", "goal", "wall_t", "sim_t",
            "tasks_completed", "tasks_total", "robot_tasks_completed",
            "run_id", "session_id", "seed",
        }
        assert issued["task_index"] == 1
        assert issued["sim_t"] == 55.0
        assert issued["tasks_completed"] == 1
        assert issued["robot_tasks_completed"] == 1

    def test_manifest_record_follows_every_event_batch(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        _arrive_robot_1(node, 50.0)
        _feed(node, 55.0, _positions(node, robot_1=_task(node, "robot_1", 0).goal))
        last = _tasks_log(node)[-1]
        assert last["event"] == "manifest"
        assert last["tasks_completed"] == 1
        assert last["tasks_total"] == 6
        assert last["makespan_sim_sec"] is None

    def test_events_logged_with_task_stream_prefix(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        _arrive_robot_1(node, 50.0)
        lines = node.get_logger().matching("task_stream event=arrived robot=robot_1")
        assert len(lines) == 1


class TestEpisodeComplete:
    def test_all_queues_empty_writes_makespan(self, node_env, tmp_path):  # noqa: F811
        node, clock, _ = _make(node_env, tmp_path, stream=_stream(tasks_per_robot=1))
        _feed(node, 50.0, _positions(node))
        clock.t += STAGGER
        node._on_timer()
        goal_1 = _task(node, "robot_1", 0).goal
        goal_2 = _task(node, "robot_2", 0).goal
        _feed(node, 60.0, {"robot_1": goal_1, "robot_2": goal_2})
        _nav2_success(node, "robot_1")
        _nav2_success(node, "robot_2")
        _feed(node, 65.0, {"robot_1": goal_1, "robot_2": goal_2})
        manifest = _tasks_log(node)[-1]
        assert manifest["complete"] is True
        assert manifest["tasks_completed"] == 2
        assert manifest["makespan_sim_sec"] == 15.0
        assert node.get_logger().matching("task_stream episode complete tasks=2/2")


class TestCongestionMidStream:
    def test_artifact_scene_carries_current_task_goal_and_label(
        self, node_env, tmp_path  # noqa: F811
    ):
        node, _clock, pipeline = _make(node_env, tmp_path)
        goal = _task(node, "robot_1", 0).goal
        _arrive_robot_1(node, 50.0)
        _feed(node, 55.0, _positions(node, robot_1=goal))
        response = node._on_trigger_analysis(SimpleNamespace(reason="test"), SimpleNamespace())
        assert response.accepted is True
        node._future.result(timeout=WAIT_SEC)
        node._on_timer()
        robots = {
            r["robot_id"]: r for r in _artifact(node, pipeline.run_calls[0])["scene"]["robots"]
        }
        assert robots["robot_1"]["goal"] == list(_task(node, "robot_1", 1).goal)
        assert robots["robot_1"]["task"] == "delivery"

"""Node-level tests for M5's per-robot base-mission hold-back (`start_delay_sec`).

Uses the ROS2 stand-ins of `test_m5_node_probe`; everything past the ROS2
surface is the real orchestrator code.
"""
from __future__ import annotations

import json

import numpy as np
from swarm_orchestrator.models import RobotView, SceneSnapshot, TaskAssignment

from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    _config,
    _FakePipeline,
    _scene_msg,
    node_env,
)

DELAY_SEC = 50.0


def _tasks(delay: float) -> dict[str, TaskAssignment]:
    return {
        "robot_1": TaskAssignment(task="t", goal=(2.5, 0.0)),
        "robot_2": TaskAssignment(task="t", goal=(-2.0, 0.0)),
        "robot_3": TaskAssignment(task="t", goal=(1.85, 0.0), start_delay_sec=delay),
    }


def _make(node_env, tmp_path, delay: float = DELAY_SEC, **overrides):  # noqa: F811
    node_module, clock = node_env
    config = _config(
        tmp_path, initial_tasks=_tasks(delay), t0_probe_mode=False,
        stall_threshold_sec=12.0, **overrides,
    )
    node = node_module.OrchestratorNode(config=config, pipeline=_FakePipeline())
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    return node, clock


def _parked_robot_3(stamp: float) -> SceneSnapshot:
    # robot_3 stands still at its hold-back spot; the pair keeps moving so it
    # never stalls itself.
    return SceneSnapshot(
        stamp=stamp,
        frame_id="overhead_camera",
        robots=[
            RobotView(robot_id="robot_1", x=-1.5 + 0.05 * stamp, y=0.0, theta=0.0,
                      linear_velocity=0.15, status="MOVING", stamp=stamp),
            RobotView(robot_id="robot_2", x=1.5 - 0.05 * stamp, y=0.0, theta=3.14,
                      linear_velocity=0.15, status="MOVING", stamp=stamp),
            RobotView(robot_id="robot_3", x=-2.45, y=0.0, theta=0.0,
                      linear_velocity=0.0, status="STOPPED", stamp=stamp),
        ],
    )


def _registry(node) -> dict:
    return json.loads(node._tasks_pub.published[-1].data)


def test_held_back_robot_is_published_pending_at_startup(node_env, tmp_path):  # noqa: F811
    node, _clock = _make(node_env, tmp_path)

    registry = _registry(node)
    assert registry["robot_3"]["start_pending"] is True
    assert registry["robot_3"]["goal"] == [1.85, 0.0]
    assert "start_pending" not in registry["robot_1"]


def test_held_back_robot_standing_still_raises_no_stall(node_env, tmp_path):  # noqa: F811
    node, clock = _make(node_env, tmp_path)

    for step in range(0, 40, 2):
        clock.t = 1000.0 + step
        node._frame_stamp = float(step)
        node._on_scene_state(_scene_msg(_parked_robot_3(float(step))))

    assert node._future is None
    assert not [m for _lvl, m in node.get_logger().lines if "starting analysis" in m]


def test_timer_releases_the_robot_after_its_delay(node_env, tmp_path):  # noqa: F811
    node, clock = _make(node_env, tmp_path)
    published = len(node._tasks_pub.published)

    clock.t = 1000.0 + DELAY_SEC - 0.5
    node._on_timer()
    assert len(node._tasks_pub.published) == published

    clock.t = 1000.0 + DELAY_SEC
    node._on_timer()
    assert len(node._tasks_pub.published) == published + 1
    assert "start_pending" not in _registry(node)["robot_3"]
    assert node.get_logger().matching("base mission released robots=['robot_3']")


def test_released_robot_standing_still_stalls_again(node_env, tmp_path):  # noqa: F811
    node, clock = _make(node_env, tmp_path)
    clock.t = 1000.0 + DELAY_SEC
    node._on_timer()

    for step in range(0, 30, 2):
        clock.t = 1000.0 + DELAY_SEC + step
        node._frame_stamp = float(step)
        node._on_scene_state(_scene_msg(_parked_robot_3(float(step))))

    assert node.get_logger().matching("robots=['robot_3']")


def test_no_start_delay_publishes_the_pre_hold_back_registry(node_env, tmp_path):  # noqa: F811
    node, clock = _make(node_env, tmp_path, delay=0.0)
    published = len(node._tasks_pub.published)

    assert node._tasks_pub.published[-1].data == (
        '{"robot_1": {"goal": [2.5, 0.0], "task": "t"}, '
        '"robot_2": {"goal": [-2.0, 0.0], "task": "t"}, '
        '"robot_3": {"goal": [1.85, 0.0], "task": "t"}}'
    )
    clock.t = 5000.0
    node._on_timer()
    assert len(node._tasks_pub.published) == published

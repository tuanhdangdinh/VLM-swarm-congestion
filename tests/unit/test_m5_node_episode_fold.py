"""Node-level test: a queued follower's solo stall folds into the busy episode.

Uses the ROS2 stand-ins of `test_m5_node_probe`; everything past the ROS2
surface is the real orchestrator code.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from swarm_orchestrator.models import RobotView, SceneSnapshot, TaskAssignment

from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _config,
    _FakePipeline,
    _scene_msg,
    node_env,
)


def _tasks() -> dict[str, TaskAssignment]:
    return {
        "robot_1": TaskAssignment(task="t", goal=(2.5, 0.0)),
        "robot_2": TaskAssignment(task="t", goal=(-2.0, 0.0)),
        "robot_3": TaskAssignment(task="t", goal=(1.85, 0.0)),
    }


def _view(robot_id: str, x: float, y: float, speed: float, stamp: float) -> RobotView:
    return RobotView(robot_id=robot_id, x=x, y=y, theta=0.0, linear_velocity=speed,
                     status="MOVING" if speed else "STOPPED", stamp=stamp)


def _feed(node, clock, stamp: float, robots: list[RobotView]) -> None:
    clock.t = 1000.0 + stamp
    node._frame_stamp = stamp
    node._on_scene_state(_scene_msg(SceneSnapshot(
        stamp=stamp, frame_id="overhead_camera", robots=robots,
    )))


def _standoff(stamp: float, robot_3_x: float) -> list[RobotView]:
    # robot_1/robot_2 nose to nose (a close/slow pair); robot_3 still closing up.
    return [
        _view("robot_1", -0.12, 0.0, 0.0, stamp),
        _view("robot_2", 0.12, 0.0, 0.0, stamp),
        _view("robot_3", robot_3_x, 0.0, 0.1, stamp),
    ]


def _maneuver(stamp: float, step: int) -> list[RobotView]:
    # The pair makes progress (the yield is executing); robot_3 stands still.
    return [
        _view("robot_1", -0.12 + 0.3 * step, 0.0, 0.1, stamp),
        _view("robot_2", 0.12 - 0.3 * step, 0.0, 0.1, stamp),
        _view("robot_3", -2.45, 0.0, 0.0, stamp),
    ]


def _status(command_id: str, robot_id: str, status: str) -> SimpleNamespace:
    return SimpleNamespace(command_id=command_id, robot_id=robot_id, status=status)


def test_follower_stall_mid_maneuver_is_folded_then_analysed_in_the_same_episode(
    node_env, tmp_path,  # noqa: F811
):
    node_module, clock = node_env
    pipeline = _FakePipeline()
    node = node_module.OrchestratorNode(
        config=_config(tmp_path, initial_tasks=_tasks(), t0_probe_mode=False,
                       stall_threshold_sec=2.0),
        pipeline=pipeline,
    )
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)

    _feed(node, clock, 10.0, _standoff(10.0, -2.85))
    _feed(node, clock, 12.0, _standoff(12.0, -2.6))
    node._future.result(timeout=WAIT_SEC)
    assert len(pipeline.run_calls) == 1
    node._on_timer()
    command_id = f"cmd-{pipeline.run_calls[0]}"
    assert node._busy_robots() == {"robot_1", "robot_2"}

    # robot_3 halts at its queue spot from t=13 and stalls from t=15.
    for step in range(1, 6):
        _feed(node, clock, 12.0 + step, _maneuver(12.0 + step, step))

    assert len(pipeline.run_calls) == 1
    assert len(node.get_logger().matching("trigger folded into the in-flight episode")) == 1
    assert node._episodes.episode_index == 0

    for robot_id in ("robot_1", "robot_2"):
        node._on_status(_status(command_id, robot_id, "COMPLETED"))
    assert node._busy_robots() == set()

    _feed(node, clock, 20.0, _maneuver(20.0, 6))
    node._future.result(timeout=WAIT_SEC)
    assert len(pipeline.run_calls) == 2
    started = node.get_logger().matching("starting analysis")
    assert "robots=['robot_3']" in started[-1]
    assert node._episodes.episode_index == 0


def _artifact_order(node, request_id: str):
    import json
    from pathlib import Path

    path = Path(node._config.decision_log_dir) / f"{request_id}.json"
    return json.loads(path.read_text())["robot_presentation_order"]


def test_three_robot_random_order_draws_a_permutation_of_the_scene(
    node_env, tmp_path,  # noqa: F811
):
    from swarm_orchestrator.presentation_order import PresentationOrderPolicy

    node_module, clock = node_env
    pipeline = _FakePipeline()
    node = node_module.OrchestratorNode(
        config=_config(tmp_path, initial_tasks=_tasks(), t0_probe_mode=False,
                       stall_threshold_sec=2.0, prompt_robot_order="random",
                       prompt_robot_order_seed=4),
        pipeline=pipeline,
    )
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)

    _feed(node, clock, 10.0, _standoff(10.0, -2.85))
    _feed(node, clock, 12.0, _standoff(12.0, -2.6))
    node._future.result(timeout=WAIT_SEC)
    node._on_timer()

    scene = ["robot_1", "robot_2", "robot_3"]
    expected = PresentationOrderPolicy(mode="random", seed=4).order_for_episode(0, scene)
    assert _artifact_order(node, pipeline.run_calls[0]) == list(expected)


def test_t0_probe_draws_over_every_scene_robot(node_env, tmp_path):  # noqa: F811
    from swarm_orchestrator.presentation_order import PresentationOrderPolicy

    node_module, clock = node_env
    pipeline = _FakePipeline()
    node = node_module.OrchestratorNode(
        config=_config(tmp_path, initial_tasks=_tasks(), prompt_robot_order="random",
                       prompt_robot_order_seed=9),
        pipeline=pipeline,
    )
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    snapshot = SceneSnapshot(stamp=50.0, frame_id="overhead_camera",
                             robots=_maneuver(50.0, 1))
    node._latest_snapshot = snapshot
    node._frame_stamp = 50.0
    clock.t = 1020.0
    node._latest_snapshot_at = clock.t

    node._on_timer()
    probe = node._probe
    probe.future.result(timeout=WAIT_SEC)
    node._on_timer()

    scene = ["robot_1", "robot_2", "robot_3"]
    expected = PresentationOrderPolicy(mode="random", seed=9).order_for_episode(0, scene)
    assert _artifact_order(node, probe.request_id) == list(expected)

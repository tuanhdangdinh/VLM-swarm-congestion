"""End to end through M5's real pipeline: the T2b mock decisions reach M4 intact.

The forced-order harness depends on the default pipeline (mock backend,
reasoner, parser, legacy grounding, filter, fan-out) turning each arm's
scripted decision into a three-robot yield command. Only ROS2 is stubbed
(`test_m5_node_probe`'s stand-ins); the pipeline is the production one.
"""
from __future__ import annotations

import json

import numpy as np
import pytest
from swarm_orchestrator.models import RobotView, SceneSnapshot, TaskAssignment

from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from scripts.t2b_forced_order import ARMS, T2B_INITIAL_TASKS
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _config,
    _scene_msg,
    node_env,
)


def _tasks() -> dict[str, TaskAssignment]:
    return {
        rid: TaskAssignment(task=t["task"], goal=tuple(t["goal"]),
                            start_delay_sec=t.get("start_delay_sec", 0.0))
        for rid, t in T2B_INITIAL_TASKS.items()
    }


def _scene(stamp: float, robot_1_x: float) -> SceneSnapshot:
    # robot_2 stands at the standoff (a solo stall, as most corpus triggers
    # are); robot_1 still creeps in; robot_3 waits held back.
    def view(rid, x, theta, speed):
        return RobotView(robot_id=rid, x=x, y=0.0, theta=theta, linear_velocity=speed,
                         status="MOVING" if speed else "STOPPED", stamp=stamp)

    return SceneSnapshot(stamp=stamp, frame_id="overhead_camera", robots=[
        view("robot_1", robot_1_x, 0.0, 0.1),
        view("robot_2", 0.12, 3.14159, 0.0),
        view("robot_3", -2.45, 0.0, 0.0),
    ])


@pytest.mark.parametrize("arm", sorted(ARMS))
def test_mock_arm_dispatches_the_forced_three_robot_yield(
    arm, node_env, tmp_path, monkeypatch,  # noqa: F811
):
    node_module, clock = node_env
    rag = tmp_path / "rag.yaml"
    rag.write_text("grounding:\n  mode: legacy\n", encoding="utf-8")
    monkeypatch.setenv("VGU_MOCK_DECISION_FILE", ARMS[arm].mock_decision_file)
    geometry = SceneGeometry(corridor=CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.5, aisle_half_width_m=0.6,
        occluder_height_m=0.9,
    ))
    node = node_module.OrchestratorNode(
        config=_config(tmp_path, initial_tasks=_tasks(), t0_probe_mode=False,
                       stall_threshold_sec=2.0, grounding_params_path=str(rag),
                       scenario_geometry=geometry, stage2_retreat_selection=False),
        pipeline=None,
    )
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)

    for step, robot_1_x in enumerate((-0.9, -0.7, -0.5, -0.3)):
        clock.t = 1000.0 + step
        node._frame_stamp = 20.0 + step
        node._on_scene_state(_scene_msg(_scene(20.0 + step, robot_1_x)))
    assert node._future is not None, node.get_logger().lines
    node._future.result(timeout=WAIT_SEC)
    node._on_timer()

    started = node.get_logger().matching("starting analysis")
    assert "robots=['robot_2']" in started[0]
    sent = [(m.robot_id, m.action, json.loads(m.parameters_json or "{}"))
            for m in node._cmd_pub.published]
    spec = ARMS[arm]
    assert [(rid, action) for rid, action, _p in sent] == [
        (spec.yielder, "yield"),
        (spec.crossing_order[0], "temporary_wait"),
        (spec.crossing_order[1], "temporary_wait"),
    ]
    params = sent[0][2]
    assert params["crossing_order"] == list(spec.crossing_order)
    assert params["passer_robot_id"] == spec.crossing_order[0]
    assert len(params["crossing_clear_m"]) == 2
    assert params["crossing_clear_m"][1] > params["crossing_clear_m"][0]
    # The held-back robot is still pending (55 s): only the command moves it.
    assert json.loads(node._tasks_pub.published[-1].data)["robot_3"]["start_pending"] is True

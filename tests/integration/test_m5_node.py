"""Integration tests for the M5 orchestrator node (require a sourced ROS2 env)."""
from __future__ import annotations

import pytest

rclpy = pytest.importorskip("rclpy")

from swarm_orchestrator.models import OrchestratorConfig, TaskAssignment  # noqa: E402
from swarm_orchestrator.orchestrator_node import OrchestratorNode  # noqa: E402

pytestmark = pytest.mark.ros2


def _config(tmp_path):
    return OrchestratorConfig(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={"robot_0": TaskAssignment(task="t", goal=(10.0, 0.0))},
        frame_dump_dir=str(tmp_path),
    )


@pytest.fixture(autouse=True)
def _rclpy_lifecycle():
    rclpy.init()
    yield
    rclpy.shutdown()


def test_node_publishes_registry_on_startup(tmp_path):
    node = OrchestratorNode(config=_config(tmp_path))
    try:
        assert node.last_published_registry is not None
        assert "robot_0" in node.last_published_registry
    finally:
        node.destroy_node()


def test_scene_state_callback_does_not_crash_on_malformed_json(tmp_path):
    node = OrchestratorNode(config=_config(tmp_path))
    try:
        node._on_scene_state(_StringMsg("{not json"))  # logged + skipped, no raise
    finally:
        node.destroy_node()


class _StringMsg:
    def __init__(self, data):
        self.data = data

"""Forcing-audit A5b: the decision artifact records the robots M5 actually dispatches.

The pipeline filters a grounded command to the snapshot's robots; `_dispatch`
then filters it to the task registry (`initial_tasks`). A robot M1 tracks
with no registry task (a T3a intruder) survives the first filter and is
dropped by the second, so before the fix the artifact could not show that
M4 received fewer robots than M3 grounded.
"""
from __future__ import annotations

import json

from swarm_orchestrator.models import PipelineOutcome, TerminalStage

from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _artifact,
    _commands,
    _FakePipeline,
    _make_node,
    _result,
    _trigger_real,
    node_env,
)


def _intruder_command(request_id: str) -> dict:
    return {
        "command_id": f"cmd-{request_id}",
        "actions": [
            {
                "robot_id": "robot_2",
                "action": "yield",
                "parameters": {
                    "backup_distance_m": 0.8,
                    "crossing_order": ["robot_1", "robot_9"],
                    "crossing_clear_m": [0.5, 0.9],
                },
            },
            {
                "robot_id": "robot_1",
                "action": "temporary_wait",
                "parameters": {"duration_sec": 8.0, "linked_position": 0},
            },
            {
                "robot_id": "robot_9",
                "action": "temporary_wait",
                "parameters": {"duration_sec": 8.0, "linked_position": 1},
            },
        ],
        "expected_resolution_time_sec": 18.0,
        "fallback": "stop",
    }


class _IntruderPipeline(_FakePipeline):
    def run(self, request):
        self.run_calls.append(request.request_id)
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id),
            grounded_command=_intruder_command(request.request_id),
            terminal_stage=TerminalStage.OK,
        )


def _dispatched_artifact(node_env, tmp_path):  # noqa: F811
    pipeline = _IntruderPipeline()
    node, _clock = _make_node(node_env, tmp_path, pipeline, t0_probe_mode=False)
    _trigger_real(node)
    node._future.result(timeout=WAIT_SEC)
    node._on_timer()
    return node, _artifact(node, pipeline.run_calls[0])


def test_artifact_dispatched_robot_ids_equal_published_robot_ids(node_env, tmp_path):  # noqa: F811
    node, artifact = _dispatched_artifact(node_env, tmp_path)

    published = [msg.robot_id for msg in _commands(node)]
    assert published == ["robot_2", "robot_1"]
    assert artifact["dispatched_robot_ids"] == published
    assert artifact["dispatch_dropped_robot_ids"] == ["robot_9"]


def test_artifact_dispatched_command_records_the_pruned_crossing_order(
    node_env, tmp_path  # noqa: F811
):
    node, artifact = _dispatched_artifact(node_env, tmp_path)

    yield_msg = next(msg for msg in _commands(node) if msg.action == "yield")
    sent = json.loads(yield_msg.parameters_json)
    recorded = artifact["dispatched_command"]["actions"][0]["parameters"]
    assert recorded["crossing_order"] == sent["crossing_order"] == ["robot_1"]
    assert recorded["crossing_clear_m"] == sent["crossing_clear_m"] == [0.5]
    assert "dispatch_filter_error" not in artifact

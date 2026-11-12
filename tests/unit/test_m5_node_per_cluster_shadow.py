"""v4 Stage 1 per-cluster shadow through the real node and the real default pipeline.

Only ROS2 is stubbed (`test_m5_node_probe`'s stand-ins). The ordinary
analysis runs the production pipeline on the scripted mock decision; the
shadow's backend is injected so a test can block, fail or script it. Request
ids are made deterministic so a shadow-on and a shadow-off run of the same
scripted scene sequence can be compared field for field.
"""

from __future__ import annotations

import itertools
import json
import threading
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from swarm_orchestrator.models import PerClusterShadowConfig, RobotView, SceneSnapshot

from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _config,
    _scene_msg,
    node_env,
)

MOCK_FILE = "config/mock_decisions/head_on_yield.json"


class _ShadowBackend:
    """Scripted shadow backend; optionally blocks on a gate before answering."""

    def __init__(self, reply: Any = "first", gate: threading.Event | None = None) -> None:
        self.reply = reply
        self.gate = gate
        self.entered = threading.Event()
        self.payloads: list[PromptPayload] = []
        self.frame_existed: list[bool] = []

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        self.payloads.append(payload)
        self.frame_existed.append(Path(payload.image_path).is_file())
        self.entered.set()
        if self.gate is not None:
            self.gate.wait(WAIT_SEC)
        if isinstance(self.reply, BaseException):
            raise self.reply
        if self.reply == "first":
            from reasoning.vlm.per_cluster_choice import read_answer_keys

            keys = read_answer_keys(payload.user_prompt)
            text = json.dumps(
                {"type": "deadlock", "justification": "t",
                 "choices": {label: ids[0] for label, ids in keys.items()}}
            )
        else:
            text = self.reply
        return BackendResponse(
            text=text, backend_id="shadow", token_usage={"prompt_tokens": 11}, latency_ms=3
        )


def _scene(stamp: float) -> SceneSnapshot:
    # Two stopped robots 0.3 m apart: a close/slow pair the detector flags at
    # once with stall_threshold_sec=0, and one observed group for the shadow.
    def view(rid: str, y: float, theta: float) -> RobotView:
        return RobotView(robot_id=rid, x=0.0, y=y, theta=theta, linear_velocity=0.0,
                         status="STOPPED", stamp=stamp)

    return SceneSnapshot(stamp=stamp, frame_id="overhead_camera",
                         robots=[view("robot_1", -0.15, 1.57), view("robot_2", 0.15, -1.57)])


def _node(node_env, tmp_path, monkeypatch, shadow: bool, backend=None, **settings):  # noqa: F811
    node_module, clock = node_env
    monkeypatch.setenv("VGU_MOCK_DECISION_FILE", MOCK_FILE)
    counter = itertools.count(1)
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID(int=next(counter)))
    tmp_path.mkdir(parents=True, exist_ok=True)
    rag = tmp_path / "rag.yaml"
    rag.write_text("grounding:\n  mode: legacy\n", encoding="utf-8")
    config = _config(
        tmp_path,
        t0_probe_mode=False,
        grounding_params_path=str(rag),
        stage2_retreat_selection=False,
        shadow_classical_params_path=str(tmp_path / "absent_rag.yaml"),
        per_cluster_shadow=PerClusterShadowConfig(enabled=shadow, **settings),
    )
    node = node_module.OrchestratorNode(config=config, pipeline=None,
                                        per_cluster_backend=backend)
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    directives: list[tuple[str, tuple[str, ...]]] = []
    on_event = node._machine.on_event

    def recording(event, **kwargs):
        directive = on_event(event, **kwargs)
        directives.append((directive.kind.value, tuple(sorted(event.involved_robots))))
        return directive

    node._machine.on_event = recording
    return node, clock, directives


def _step(node, clock, stamp: float) -> None:
    clock.t += 1.0
    node._frame_stamp = stamp
    node._on_scene_state(_scene_msg(_scene(stamp)))
    if node._future is not None:
        node._future.result(timeout=WAIT_SEC)
    node._on_timer()


def _complete_all(node) -> None:
    for msg in list(node._cmd_pub.published):
        node._on_status(SimpleNamespace(command_id=msg.command_id, robot_id=msg.robot_id,
                                        status="COMPLETED"))


def _drive(node, clock) -> None:
    """Analysis, dispatch, busy suppression, resolution, cooldown, re-analysis."""
    stamp = 50.0
    for _ in range(3):
        _step(node, clock, stamp := stamp + 1.0)
    _complete_all(node)
    for _ in range(4):
        _step(node, clock, stamp := stamp + 1.0)
    clock.t += 16.0
    for _ in range(3):
        _step(node, clock, stamp := stamp + 1.0)


def _published(node) -> list[tuple[str, str, str, str]]:
    return [(m.command_id, m.robot_id, m.action, m.parameters_json)
            for m in node._cmd_pub.published]


def _state(node, clock) -> dict[str, Any]:
    return {
        "published": _published(node),
        "tracker": sorted(node._tracker._records),
        "cooldown": sorted(node._cooldown.active_robots(clock.t)),
        "registry": node.last_published_registry,
        "machine": node._machine.state.value,
    }


def _artifacts(node) -> dict[str, dict]:
    out = {}
    for path in sorted(Path(node._config.decision_log_dir).glob("*.json")):
        out[path.stem] = json.loads(path.read_text())
    return out


def _finish_shadows(node) -> None:
    for pending in list(node._pcs_pending):
        pending.future.result(timeout=WAIT_SEC)
    node._on_timer()


def test_shadow_on_dispatches_and_directs_exactly_as_shadow_off(
    node_env, tmp_path, monkeypatch  # noqa: F811
):
    off, off_clock, off_directives = _node(node_env, tmp_path / "off", monkeypatch, False)
    _drive(off, off_clock)
    gate = threading.Event()
    backend = _ShadowBackend(gate=gate)
    on, on_clock, on_directives = _node(node_env, tmp_path / "on", monkeypatch, True, backend)
    _drive(on, on_clock)
    # The first shadow is still blocked inside its M2 call: the second
    # analysis started, dispatched and was harvested regardless.
    assert backend.entered.is_set() and not gate.is_set()
    assert on_directives == off_directives
    assert [d for d, _ in on_directives].count("start_analysis") == 2
    assert _state(on, on_clock) == _state(off, off_clock)
    assert len(_published(on)) >= 4
    gate.set()
    _finish_shadows(on)
    assert _state(on, on_clock) == _state(off, off_clock)


def test_shadow_off_artifacts_have_no_shadow_key_and_no_trace(
    node_env, tmp_path, monkeypatch  # noqa: F811
):
    node, clock, _ = _node(node_env, tmp_path, monkeypatch, False)
    _drive(node, clock)
    assert node._pcs_executor is None and node._trigger_trace is None
    artifacts = _artifacts(node)
    assert artifacts and all("per_cluster_shadow" not in a for a in artifacts.values())
    assert not list(Path(node._config.decision_log_dir).glob("trigger_trace_*.jsonl"))


def test_shadow_record_replaces_pending_block(node_env, tmp_path, monkeypatch):  # noqa: F811
    gate = threading.Event()
    backend = _ShadowBackend(gate=gate)
    node, clock, _ = _node(node_env, tmp_path, monkeypatch, True, backend)
    _step(node, clock, 51.0)
    backend.entered.wait(WAIT_SEC)
    (request_id, artifact), = _artifacts(node).items()
    assert artifact["per_cluster_shadow"] == {"request_id": request_id, "status": "pending"}
    gate.set()
    _finish_shadows(node)
    block = _artifacts(node)[request_id]["per_cluster_shadow"]
    assert block["status"] == "ok" and block["request_id"] == request_id
    assert block["n_slots"] == 1 and block["choices"] == {"A": "1"}
    assert block["m2"]["token_usage"] == {"prompt_tokens": 11}
    assert set(block["timings"]) == {"enumeration_ms", "m2_call_ms", "grounding_ms", "total_ms"}
    assert block["joint_check"]["n_commands"] == 1
    assert len(node.get_logger().matching("per_cluster_shadow request=")) == 1


def test_shadow_uses_the_ordinary_frame_and_snapshot(node_env, tmp_path, monkeypatch):  # noqa: F811
    gate = threading.Event()
    backend = _ShadowBackend(gate=gate)
    node, clock, _ = _node(node_env, tmp_path, monkeypatch, True, backend)
    _step(node, clock, 51.0)
    backend.entered.wait(WAIT_SEC)
    (request_id, artifact), = _artifacts(node).items()
    frame = Path(node._config.frame_dump_dir) / f"{request_id}.png"
    # keep_debug_frames is false: the ordinary cleanup waits for the shadow.
    assert frame.is_file()
    payload = backend.payloads[0]
    assert payload.image_path == str(frame) and backend.frame_existed == [True]
    # Same rendered request (snapshot, goals, order): the shadow's prompt is
    # the ordinary prompt with the per-group section appended.
    assert payload.user_prompt.startswith(artifact["prompt"]["user_prompt"] + "\n\n")
    assert payload.system_prompt == artifact["prompt"]["system_prompt"]
    gate.set()
    _finish_shadows(node)
    block = _artifacts(node)[request_id]["per_cluster_shadow"]
    assert block["image_path"] == str(frame)
    assert block["lookups_source"] == "ordinary_grounding"
    assert [g["robots"] for g in block["groups"]] == [["robot_1", "robot_2"]]
    assert not frame.exists()


def test_backend_error_is_recorded_and_dispatch_unaffected(
    node_env, tmp_path, monkeypatch  # noqa: F811
):
    off, off_clock, _ = _node(node_env, tmp_path / "off", monkeypatch, False)
    _step(off, off_clock, 51.0)
    on, on_clock, _ = _node(node_env, tmp_path / "on", monkeypatch, True,
                            _ShadowBackend(reply=ValueError("provider down")))
    _step(on, on_clock, 51.0)
    _finish_shadows(on)
    assert _published(on) == _published(off)
    (block,) = [a["per_cluster_shadow"] for a in _artifacts(on).values()]
    assert block["status"] == "parse_failed"
    assert block["error"] == "ValueError: provider down"
    assert block["m2"]["attempts"] == on._pcs_reasoner_config.max_attempts


def test_invalid_answer_after_reask_is_recorded(node_env, tmp_path, monkeypatch):  # noqa: F811
    backend = _ShadowBackend(reply=json.dumps({"choices": {"Z": "1"}}))
    node, clock, _ = _node(node_env, tmp_path, monkeypatch, True, backend, max_attempts=2)
    _step(node, clock, 51.0)
    _finish_shadows(node)
    (block,) = [a["per_cluster_shadow"] for a in _artifacts(node).values()]
    assert block["status"] == "parse_failed" and block["m2"]["attempts"] == 2
    assert block["m2"]["parse_status"] == "failed"
    assert "invalid \"choices\"" in block["error"]
    assert len(backend.payloads) == 2
    assert len(node._cmd_pub.published) == 2


def test_timeout_records_once_and_discards_late_result(
    node_env, tmp_path, monkeypatch  # noqa: F811
):
    gate = threading.Event()
    backend = _ShadowBackend(gate=gate)
    node, clock, _ = _node(node_env, tmp_path, monkeypatch, True, backend, timeout_sec=10.0)
    _step(node, clock, 51.0)
    backend.entered.wait(WAIT_SEC)
    (request_id,) = _artifacts(node)
    clock.t += 11.0
    node._on_timer()
    block = _artifacts(node)[request_id]["per_cluster_shadow"]
    assert block["status"] == "timeout"
    frame = Path(node._config.frame_dump_dir) / f"{request_id}.png"
    assert not frame.exists()
    gate.set()
    node._pcs_pending[0].future.result(timeout=WAIT_SEC)
    node._on_timer()
    assert _artifacts(node)[request_id]["per_cluster_shadow"] == block
    assert node._pcs_pending == []
    assert node.get_logger().matching("result discarded")
    assert len(node._cmd_pub.published) == 2


def test_worker_exception_is_recorded(node_env, tmp_path, monkeypatch):  # noqa: F811
    node_module, _ = node_env

    def boom(*_args, **_kwargs):
        raise RuntimeError("shadow crashed")

    monkeypatch.setattr(node_module, "compute_per_cluster_shadow", boom)
    node, clock, _ = _node(node_env, tmp_path, monkeypatch, True, _ShadowBackend())
    _step(node, clock, 51.0)
    _finish_shadows(node)
    (block,) = [a["per_cluster_shadow"] for a in _artifacts(node).values()]
    assert block["status"] == "error"
    assert block["error"] == "worker raised: RuntimeError: shadow crashed"
    assert len(node._cmd_pub.published) == 2


def test_backlog_skip_is_recorded(node_env, tmp_path, monkeypatch):  # noqa: F811
    gate = threading.Event()
    backend = _ShadowBackend(gate=gate)
    node, clock, _ = _node(node_env, tmp_path, monkeypatch, True, backend)
    _drive(node, clock)
    blocks = {rid: a["per_cluster_shadow"] for rid, a in _artifacts(node).items()}
    statuses = sorted(b["status"] for b in blocks.values())
    assert statuses == ["pending", "skipped"]
    skipped = next(b for b in blocks.values() if b["status"] == "skipped")
    assert skipped["error"].startswith("backlog: 1 shadow(s) still running")
    gate.set()
    _finish_shadows(node)


def test_mock_without_script_gets_the_fixed_first_chooser(
    node_env, tmp_path, monkeypatch  # noqa: F811
):
    monkeypatch.delenv("VGU_MOCK_PER_CLUSTER_FILE", raising=False)
    node, clock, _ = _node(node_env, tmp_path, monkeypatch, True)
    assert type(node._pcs_backend).__name__ == "FixedGroupChoiceBackend"
    _step(node, clock, 51.0)
    _finish_shadows(node)
    (block,) = [a["per_cluster_shadow"] for a in _artifacts(node).values()]
    assert block["status"] == "ok" and block["choices"] == {"A": "1"}


def test_reasoning_off_forces_the_shadow_off(node_env, tmp_path, monkeypatch):  # noqa: F811
    node_module, _ = node_env
    config = _config(tmp_path, t0_probe_mode=False, reasoning_enabled=False,
                     per_cluster_shadow=PerClusterShadowConfig(enabled=True))
    node = node_module.OrchestratorNode(config=config, pipeline=None)
    assert node._pcs_executor is None and node._trigger_trace is None


def test_trigger_trace_records_directives_with_in_flight_commands(
    node_env, tmp_path, monkeypatch  # noqa: F811
):
    node, clock, directives = _node(node_env, tmp_path, monkeypatch, True, _ShadowBackend())
    _drive(node, clock)
    _finish_shadows(node)
    node._trigger_trace.close()
    (path,) = Path(node._config.decision_log_dir).glob("trigger_trace_*.jsonl")
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    events = [line for line in lines if line["event"] == "event"]
    ends = [line for line in lines if line["event"] == "event_run_end"]
    assert sum(1 for _ in events) + sum(e["count"] - 1 for e in ends) == len(directives)
    starts = [e for e in events if e["directive"] == "start_analysis"]
    assert len(starts) == 2 and all(e["request_id"] for e in starts)
    suppressed = [e for e in events if e["directive"] == "suppressed"]
    assert any(e["in_flight"] for e in suppressed)
    in_flight = next(e for e in suppressed if e["in_flight"])
    assert sorted(next(iter(in_flight["in_flight"].values()))) == ["robot_1", "robot_2"]
    assert all({"run_id", "session_id"} <= set(line) for line in lines)
    assert all({"sim_t", "wall_t", "busy_robots"} <= set(e) for e in events)


@pytest.mark.parametrize("bad", [{"enabled": True, "max_backlog": 0}, {"unknown": 1}])
def test_shadow_config_rejects_bad_values(bad):
    with pytest.raises(ValueError):
        PerClusterShadowConfig(**bad)

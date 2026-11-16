"""v4 refusal feedback Change 1 through the real node on the tranche-1 S1b config.

Reuses the per-cluster-shadow S1b harness (seed-4 overlay fixture, mock
pipeline, ROS2 stubbed). The md5 pins were taken at fdf333d (the base of this
branch) with the same harness, so a keys-off run here must reproduce the base
artifacts, published commands and state-machine directives byte for byte.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from tests.unit.test_m5_node_per_cluster_shadow import (  # noqa: F401  (node_env is a fixture)
    MOCK_FILE,
    S1B_OVERLAY,
    _artifacts,
    _published,
    _s1b_drive,
    _strip_paths,
    node_env,
)

# (artifacts, published, directives) md5 of the keys-off run at fdf333d.
BASE_PINS = {
    "withheld_yield": (
        "9957cb1b96167e0c10e6ebe18812d40d",
        "d751713988987e9331980363e24189ce",
        "55d8c70cc55a976ee103b925c75c2769",
    ),
    "dispatched_reverse": (
        "e58ac8ffab93756f02dfef6d8165d0db",
        "faca6d04ed8b286ada632cd97c70ea5c",
        "301f9978872a2e1aaf706f899ba88f5d",
    ),
}
DECISIONS = {
    "withheld_yield": None,
    "dispatched_reverse": {"involved_robots": ["robot_1", "robot_2"], "strategy": "reverse"},
}
S1B_OFFER = ("yield", "reroute", "convoy", "priority_override", "temporary_wait", "reverse")


def _mock_file(tmp_path: Path, decision: dict[str, Any] | None) -> str:
    if decision is None:
        return MOCK_FILE
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "decision.json"
    path.write_text(json.dumps({"congestion_detected": True, "type": "deadlock",
                                "root_cause": "t", "justification": "t", **decision}))
    return str(path)


def s1b_node(node_env, tmp_path: Path, monkeypatch, mock_file: str, **keys: Any):  # noqa: F811
    """The tranche-1 Arm A S1b node with extra top-level config keys."""
    from swarm_orchestrator.models import load_config

    node_module, clock = node_env
    clock.t = 1000.0
    monkeypatch.setenv("VGU_MOCK_DECISION_FILE", mock_file)
    counter = itertools.count(1)
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID(int=next(counter)))
    tmp_path.mkdir(parents=True, exist_ok=True)
    raw = yaml.safe_load(S1B_OVERLAY.read_text())
    raw.update(
        reasoning_backend_id="mock",
        frame_dump_dir=str(tmp_path / "frames"),
        decision_log_dir=str(tmp_path / "decisions"),
        scene_log_dir=None,
        **keys,
    )
    node = node_module.OrchestratorNode(config=load_config(raw), pipeline=None)
    node._frame_rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    directives: list[tuple[str, tuple[str, ...]]] = []
    on_event = node._machine.on_event

    def recording(event, **kwargs):
        directive = on_event(event, **kwargs)
        directives.append((directive.kind.value, tuple(sorted(event.involved_robots))))
        return directive

    node._machine.on_event = recording
    return node, clock, directives


def _md5(value: Any) -> str:
    return hashlib.md5(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _run(node_env, tmp_path, monkeypatch, case: str, **keys: Any):  # noqa: F811
    mock_file = _mock_file(tmp_path, DECISIONS[case])
    node, clock, directives = s1b_node(node_env, tmp_path / "x", monkeypatch, mock_file, **keys)
    _s1b_drive(node, clock)
    artifacts = _strip_paths(_artifacts(node), str(tmp_path / "x"))
    return node, artifacts, directives


@pytest.mark.parametrize("case", sorted(BASE_PINS))
def test_keys_absent_reproduce_base_run(case, node_env, tmp_path, monkeypatch):  # noqa: F811
    node, artifacts, directives = _run(node_env, tmp_path, monkeypatch, case)
    pins = (_md5(artifacts), hashlib.md5(json.dumps(_published(node)).encode()).hexdigest(),
            hashlib.md5(json.dumps(directives).encode()).hexdigest())
    assert pins == BASE_PINS[case]


@pytest.mark.parametrize("case", sorted(BASE_PINS))
def test_keys_explicitly_off_reproduce_base_run(
    case, node_env, tmp_path, monkeypatch  # noqa: F811
):
    node, artifacts, directives = _run(
        node_env, tmp_path, monkeypatch, case,
        prompt_offer_groundable_strategies=False,
    )
    assert _md5(artifacts) == BASE_PINS[case][0]


def test_offer_on_sends_s1b_groundable_set(node_env, tmp_path, monkeypatch):  # noqa: F811
    node, artifacts, _ = _run(node_env, tmp_path, monkeypatch, "withheld_yield",
                              prompt_offer_groundable_strategies=True)
    assert all(a["offered_strategies"] == list(S1B_OFFER) for a in artifacts.values())


def test_offer_on_prompt_has_no_junction_clear(node_env, tmp_path, monkeypatch):  # noqa: F811
    node, artifacts, _ = _run(node_env, tmp_path, monkeypatch, "withheld_yield",
                              prompt_offer_groundable_strategies=True)
    assert all("junction_clear" not in a["prompt"]["user_prompt"] for a in artifacts.values())


def test_offer_on_keeps_dispatch_and_directives(node_env, tmp_path, monkeypatch):  # noqa: F811
    for case in sorted(BASE_PINS):
        node, _, directives = _run(node_env, tmp_path / case, monkeypatch, case,
                                   prompt_offer_groundable_strategies=True)
        assert hashlib.md5(json.dumps(_published(node)).encode()).hexdigest() == BASE_PINS[case][1]
        assert hashlib.md5(json.dumps(directives).encode()).hexdigest() == BASE_PINS[case][2]


def test_offer_on_marks_offered_decision(node_env, tmp_path, monkeypatch):  # noqa: F811
    _, artifacts, _ = _run(node_env, tmp_path, monkeypatch, "dispatched_reverse",
                           prompt_offer_groundable_strategies=True)
    assert [a["decision_strategy_offered"] for a in artifacts.values()] == [True]


def test_unoffered_decision_is_counted_and_grounded_as_before(
    node_env, tmp_path, monkeypatch  # noqa: F811
):
    decision = {"involved_robots": ["robot_1", "robot_2"], "strategy": "junction_clear"}
    mock_file = _mock_file(tmp_path, decision)
    off, off_clock, off_directives = s1b_node(node_env, tmp_path / "off", monkeypatch, mock_file)
    _s1b_drive(off, off_clock)
    on, on_clock, on_directives = s1b_node(node_env, tmp_path / "on", monkeypatch, mock_file,
                                           prompt_offer_groundable_strategies=True)
    _s1b_drive(on, on_clock)
    assert _published(on) == _published(off) and on_directives == off_directives
    on_artifacts = list(_artifacts(on).values())
    assert on_artifacts and all(a["decision_strategy_offered"] is False for a in on_artifacts)
    assert on._unoffered_strategy_decisions == len(on_artifacts)
    assert on.get_logger().matching("strategy not offered")


def test_offer_requires_plan_channel():
    from swarm_orchestrator.models import load_config

    raw = yaml.safe_load(S1B_OVERLAY.read_text())
    raw.update(plan_channel_enabled=False, plan_dispatch_order_source="chi",
               prompt_offer_groundable_strategies=True)
    with pytest.raises(ValueError, match="prompt_offer_groundable_strategies"):
        load_config(raw)

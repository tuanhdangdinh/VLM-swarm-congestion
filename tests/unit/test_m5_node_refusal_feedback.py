"""v4 refusal feedback Change 2 through the real node on the tranche-1 S1b config.

Same harness and base pins as `test_m5_node_offered_strategies`. The scripted
yield is refused on this scene and withheld (`refusal_no_action`); a
`reverse` on robot_1/robot_2 is dispatched.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from tests.unit.test_m5_node_offered_strategies import (
    BASE_PINS,
    _run,
    s1b_node,
)
from tests.unit.test_m5_node_per_cluster_shadow import (  # noqa: F401  (node_env is a fixture)
    _artifacts,
    _published,
    _s1b_drive,
    _strip_paths,
    node_env,
)

FEEDBACK = {"refusal_feedback": {"enabled": True}}
HEADER = "Proposals the system withheld"


def _ordered(artifacts: dict[str, dict]) -> list[dict]:
    return sorted(artifacts.values(), key=lambda a: a["scene"]["stamp"])


def _md5(value: Any) -> str:
    return hashlib.md5(json.dumps(value).encode()).hexdigest()


def test_feedback_off_shows_withheld_plan_as_accepted(node_env, tmp_path, monkeypatch):  # noqa: F811
    # The defect Change 2 removes, pinned at the base behaviour.
    _, artifacts, _ = _run(node_env, tmp_path, monkeypatch, "withheld_yield")
    first, second = _ordered(artifacts)
    assert first["dispatch_withheld"]["reason"] == "refusal_no_action"
    assert second["plan_state"]["plan_id"] == first["plan"]["plan_id"]
    assert "Hold this plan" in second["prompt"]["user_prompt"]


def test_feedback_on_states_withheld_proposal(node_env, tmp_path, monkeypatch):  # noqa: F811
    _, artifacts, _ = _run(node_env, tmp_path, monkeypatch, "withheld_yield", **FEEDBACK)
    first, second = _ordered(artifacts)
    (proposal,) = second["refused_proposals"]
    assert proposal["strategy"] == first["decision"]["strategy"] == "yield"
    assert proposal["involved_robots"] == first["decision"]["involved_robots"]
    assert HEADER in second["prompt"]["user_prompt"]


def test_feedback_on_reason_reads_recorded_refusal(node_env, tmp_path, monkeypatch):  # noqa: F811
    from swarm_orchestrator.reasoning_pipeline import refusal_feedback_reason

    _, artifacts, _ = _run(node_env, tmp_path, monkeypatch, "withheld_yield", **FEEDBACK)
    first, second = _ordered(artifacts)
    expected = refusal_feedback_reason(
        {k: v for k, v in first["dispatch_withheld"].items() if k != "plan_withheld"},
        first["grounding_degradations"] or [],
    )
    assert second["refused_proposals"][0]["reason"] == expected


def test_feedback_on_never_shows_withheld_plan(node_env, tmp_path, monkeypatch):  # noqa: F811
    node, artifacts, _ = _run(node_env, tmp_path, monkeypatch, "withheld_yield", **FEEDBACK)
    first, second = _ordered(artifacts)
    assert "plan_state" not in second
    assert "Hold this plan" not in second["prompt"]["user_prompt"]
    assert first["dispatch_withheld"]["plan_withheld"] == first["plan"]["plan_id"]
    assert node._plan_tracker.is_withheld(first["plan"]["plan_id"])


def test_feedback_off_artifacts_carry_no_new_keys(node_env, tmp_path, monkeypatch):  # noqa: F811
    _, artifacts, _ = _run(node_env, tmp_path, monkeypatch, "withheld_yield",
                           refusal_feedback={"enabled": False})
    assert all("refused_proposals" not in a for a in artifacts.values())
    assert all("plan_withheld" not in (a.get("dispatch_withheld") or {})
               for a in artifacts.values())


@pytest.mark.parametrize("case", sorted(BASE_PINS))
def test_feedback_on_keeps_dispatch_and_directives(
    case, node_env, tmp_path, monkeypatch  # noqa: F811
):
    node, _, directives = _run(node_env, tmp_path, monkeypatch, case,
                               prompt_offer_groundable_strategies=True, **FEEDBACK)
    assert _md5(_published(node)) == BASE_PINS[case][1]
    assert _md5(directives) == BASE_PINS[case][2]


def test_feedback_on_dispatched_plan_is_shown(node_env, tmp_path, monkeypatch):  # noqa: F811
    node, artifacts, _ = _run(node_env, tmp_path, monkeypatch, "dispatched_reverse", **FEEDBACK)
    (artifact,) = artifacts.values()
    assert node._plan_tracker.shown_plan().plan_id == artifact["plan"]["plan_id"]
    assert not node._plan_tracker.is_withheld(artifact["plan"]["plan_id"])


def test_dispatch_forgets_withheld_proposals(node_env, tmp_path, monkeypatch):  # noqa: F811
    base = {"congestion_detected": True, "type": "deadlock", "root_cause": "t",
            "justification": "t", "involved_robots": ["robot_1", "robot_2"]}
    path = tmp_path / "sequence.json"
    path.write_text(json.dumps([{**base, "strategy": "yield"}, {**base, "strategy": "reverse"}]))
    node, clock, _ = s1b_node(node_env, tmp_path / "x", monkeypatch, str(path), **FEEDBACK)
    _s1b_drive(node, clock)
    artifacts = _ordered(_strip_paths(_artifacts(node), str(tmp_path / "x")))
    assert [bool(a.get("dispatch_withheld")) for a in artifacts][:2] == [True, False]
    assert artifacts[1]["refused_proposals"][0]["strategy"] == "yield"
    assert len(node._withheld) == 0


def test_withheld_then_dispatched_publishes_as_feedback_off(
    node_env, tmp_path, monkeypatch  # noqa: F811
):
    # A refused yield, then a dispatched reverse on the same pair: the plan
    # tracker (holds, plan ids attached to commands, plan-continue partners)
    # must decide exactly as with the key off, so every published parameter
    # is the same.
    base = {"congestion_detected": True, "type": "deadlock", "root_cause": "t",
            "justification": "t", "involved_robots": ["robot_1", "robot_2"]}
    path = tmp_path / "sequence.json"
    path.write_text(json.dumps([{**base, "strategy": "yield"}, {**base, "strategy": "reverse"},
                                {**base, "strategy": "yield"}, {**base, "strategy": "reverse"}]))
    runs = {}
    for name, keys in (("off", {}), ("on", {"prompt_offer_groundable_strategies": True,
                                             **FEEDBACK})):
        node, clock, directives = s1b_node(node_env, tmp_path / name, monkeypatch, str(path),
                                           **keys)
        _s1b_drive(node, clock)
        arts = _ordered(_strip_paths(_artifacts(node), str(tmp_path / name)))
        runs[name] = (_published(node), directives,
                      [(a.get("plan") or {}).get("plan_id") for a in arts],
                      [(a.get("plan") or {}).get("plan_held") for a in arts])
    # Key off, the dispatched reverse is a HOLD of the withheld yield's plan, so
    # its command carries that plan id: hiding the plan from the tracker (rather
    # than from the prompt only) would change the published parameters.
    assert runs["off"][0] and runs["off"][3][:2] == [False, True]
    assert runs["on"] == runs["off"]


def test_feedback_requires_plan_channel():
    import yaml
    from swarm_orchestrator.models import load_config

    from tests.unit.test_m5_node_per_cluster_shadow import S1B_OVERLAY

    raw = yaml.safe_load(S1B_OVERLAY.read_text())
    raw.update(plan_channel_enabled=False, plan_dispatch_order_source="chi", **FEEDBACK)
    with pytest.raises(ValueError, match="refusal_feedback"):
        load_config(raw)



def test_refusal_feedback_overlay_differs_from_shadow_overlay_only_in_the_keys():
    import yaml
    from swarm_orchestrator.models import load_config

    base = yaml.safe_load(open("config/overlays/v4_s1b_pc_shadow/orch_seed1.yaml"))
    cell = yaml.safe_load(open("config/overlays/v4_s1b_refusal_feedback/orch_seed1.yaml"))
    delta = yaml.safe_load(
        open("config/overlays/v4_s1b_refusal_feedback/refusal_feedback_delta.yaml")
    )
    assert cell == {**base, **delta}
    config = load_config(cell)
    assert config.prompt_offer_groundable_strategies and config.refusal_feedback.enabled

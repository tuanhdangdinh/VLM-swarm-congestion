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

from reasoning.rag.command_grounder import VerifiedPlan
from reasoning.vlm.models import ProposedPlanLeg
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


# Plan-block hiding (refusal_feedback on): the scripted runs below drive the
# S1b scene, then complete commands ("c"), fire the operator trigger ("t"),
# report one leg FAILED ("f") or keep driving ("d").
SEQ_BASE = {"congestion_detected": True, "type": "deadlock", "root_cause": "t",
            "justification": "t", "involved_robots": ["robot_1", "robot_2"]}
CONTRADICTION = {"contradiction_trigger": {"enabled": True}}


def _drive_steps(node, clock, state: dict[str, float], steps: int = 20) -> None:
    from tests.unit.test_m5_node_per_cluster_shadow import WAIT_SEC, _s1b_scene, _scene_msg

    for _ in range(steps):
        clock.t += 1.0
        state["stamp"] += 1.0
        node._frame_stamp = state["stamp"]
        node._on_scene_state(_scene_msg(_s1b_scene(state["stamp"])))
        if node._future is not None:
            node._future.result(timeout=WAIT_SEC)
        node._on_timer()


def _scripted(node_env, tmp_path, monkeypatch, strategies: list[str], script: str,  # noqa: F811
              **keys: Any):
    from types import SimpleNamespace

    from tests.unit.test_m5_node_per_cluster_shadow import WAIT_SEC, _complete_all

    path = tmp_path / "sequence.json"
    tmp_path.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([{**SEQ_BASE, "strategy": s} for s in strategies]))
    node, clock, directives = s1b_node(node_env, tmp_path / "x", monkeypatch, str(path), **keys)
    state = {"stamp": 100.0}
    for op in script:
        if op == "d":
            _drive_steps(node, clock, state)
        elif op == "c":
            _complete_all(node)
        elif op == "f":
            published = list(node._cmd_pub.published)
            for msg in published[-2:]:
                node._on_status(SimpleNamespace(command_id=msg.command_id,
                                                robot_id=msg.robot_id, status="ACTIVE"))
            node._on_status(SimpleNamespace(command_id=published[-1].command_id,
                                            robot_id=published[-1].robot_id, status="FAILED"))
        else:
            node._on_trigger_analysis(SimpleNamespace(reason="op"), SimpleNamespace())
            if node._future is not None:
                node._future.result(timeout=WAIT_SEC)
            clock.t += 1.0
            node._on_timer()
    artifacts = _ordered(_strip_paths(_artifacts(node), str(tmp_path / "x")))
    return node, artifacts, directives


def test_feedback_off_shows_completed_plan_with_hold_advice(node_env, tmp_path, monkeypatch):  # noqa: F811
    # The defect, pinned at the base behaviour: a finished wait plan is held.
    _, arts, _ = _scripted(node_env, tmp_path, monkeypatch, ["reverse"] * 2, "dct")
    assert [leg["status"] for leg in arts[1]["plan_state"]["legs"][:2]] == ["done", "done"]
    assert "Hold this plan" in arts[1]["prompt"]["user_prompt"]


def test_feedback_on_hides_completed_plan_block(node_env, tmp_path, monkeypatch):  # noqa: F811
    _, arts, _ = _scripted(node_env, tmp_path, monkeypatch, ["reverse"] * 2, "dct", **FEEDBACK)
    assert "plan_state" not in arts[1]
    assert "Active plan" not in arts[1]["prompt"]["user_prompt"]
    assert "Hold this plan" not in arts[1]["prompt"]["user_prompt"]


def test_feedback_on_records_hidden_plan_reason_completed(node_env, tmp_path, monkeypatch):  # noqa: F811
    _, arts, _ = _scripted(node_env, tmp_path, monkeypatch, ["reverse"] * 2, "dct", **FEEDBACK)
    hidden = arts[1]["plan_state_hidden"]
    assert hidden["reason"] == "completed"
    assert hidden["plan_state"]["plan_id"] == arts[0]["plan"]["plan_id"]


def test_feedback_on_records_hidden_plan_reason_failed(node_env, tmp_path, monkeypatch):  # noqa: F811
    # The first trigger is refused while the command is busy; the command
    # then times out, so its legs are failed and nothing is in flight.
    _, arts, _ = _scripted(node_env, tmp_path, monkeypatch, ["reverse"] * 3, "dtdt", **FEEDBACK)
    assert arts[1]["plan_state_hidden"]["reason"] == "failed"
    assert "Hold this plan" not in arts[1]["prompt"]["user_prompt"]


def test_feedback_on_contradiction_analysis_hides_failed_plan(node_env, tmp_path, monkeypatch):  # noqa: F811
    _, arts, _ = _scripted(node_env, tmp_path, monkeypatch, ["reverse"] * 4, "dfdcdtcd",
                           **FEEDBACK, **CONTRADICTION)
    (contradiction,) = [a for a in arts if a.get("trigger_source") == "contradiction"]
    assert contradiction["plan_state_hidden"]["reason"] == "failed"


def test_feedback_on_shows_plan_while_command_in_flight(node_env, tmp_path, monkeypatch):  # noqa: F811
    node, arts, _ = _scripted(node_env, tmp_path, monkeypatch, ["reverse"] * 2, "d", **FEEDBACK)
    shown, reason = node._prompt_plan_block()
    assert shown is not None and shown.plan_id == arts[0]["plan"]["plan_id"]
    assert reason is None


def test_feedback_on_shows_plan_with_queued_junction_phase(node_env, tmp_path, monkeypatch):  # noqa: F811
    from types import SimpleNamespace

    node, _, _ = _scripted(node_env, tmp_path, monkeypatch, ["reverse"], "", **FEEDBACK)
    plan = node._plan_tracker.accept_plan(VerifiedPlan(
        legs=[ProposedPlanLeg(robot_id="robot_1", action="reverse"),
              ProposedPlanLeg(robot_id="robot_2", action="reverse")],
        provenance="m3_default", edits=[],
    )).plan
    # No command record: only the queue says a later phase is still to come.
    node._plan_id_by_command_id["phase-cmd"] = plan.plan_id
    node._junction_phase_queues["phase-cmd"] = SimpleNamespace(done=False)
    assert node._prompt_plan_block() == (plan, None)


def test_feedback_on_hidden_plan_not_recorded_as_last_shown(node_env, tmp_path, monkeypatch):  # noqa: F811
    # "Changed since the last invocation" stays relative to what M2 last saw.
    node, _, _ = _scripted(node_env, tmp_path, monkeypatch, ["reverse"] * 2, "dct", **FEEDBACK)
    assert node._last_shown_plan_id is None


def test_feedback_on_hidden_plan_keeps_refusal_lines(node_env, tmp_path, monkeypatch):  # noqa: F811
    from reasoning.vlm.models import RefusedProposal
    from reasoning.vlm.prompt_builder import render_refused_proposals_block

    _, arts, _ = _scripted(node_env, tmp_path, monkeypatch, ["reverse", "yield", "reverse"],
                           "dctct", **FEEDBACK)
    third = arts[2]
    proposals = [RefusedProposal(**p) for p in third["refused_proposals"]]
    assert third["plan_state_hidden"]["reason"] == "completed"
    assert render_refused_proposals_block(proposals) in third["prompt"]["user_prompt"]


def test_feedback_off_artifacts_carry_no_hidden_plan_key(node_env, tmp_path, monkeypatch):  # noqa: F811
    _, arts, _ = _scripted(node_env, tmp_path, monkeypatch, ["reverse"] * 2, "dct")
    assert all("plan_state_hidden" not in a for a in arts)


def _dispatch_view(node, arts: list[dict], directives: list) -> tuple:
    tracker = node._plan_tracker
    return (
        _published(node), directives,
        [((a.get("plan") or {}).get("plan_id"), (a.get("plan") or {}).get("plan_held"),
          a.get("dispatched_command"), a.get("dispatch_withheld", {}).get("reason"),
          a.get("reanalysis_suppression"), a.get("trigger_source")) for a in arts],
        {pid: plan.model_dump(mode="json") for pid, plan in tracker._plans.items()},
        tracker.plan_holds,
    )


@pytest.mark.parametrize("strategies,script,keys", [
    (["reverse"] * 4, "dctctct", {}),
    (["reverse", "yield", "reverse", "yield"], "dctctct", {}),
    (["temporary_wait"] * 4, "dtdtct", {}),
    (["reverse"] * 4, "dfdcdtcd", CONTRADICTION),
])
def test_feedback_on_hiding_keeps_dispatch_tracker_and_triggers(
    strategies, script, keys, node_env, tmp_path, monkeypatch  # noqa: F811
):
    views = {}
    for name, extra in (("off", {}), ("on", FEEDBACK)):
        node, arts, directives = _scripted(node_env, tmp_path / name, monkeypatch, strategies,
                                           script, **keys, **extra)
        views[name] = _dispatch_view(node, arts, directives)
    assert views["on"] == views["off"]

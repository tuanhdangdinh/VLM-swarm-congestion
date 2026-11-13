"""Offline replay of the v4 refusal-feedback keys (bench `refusal_feedback` variant)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from benchmarks.vlm_bench.refusal_feedback_replay import episode_feedback_states, read_m5_log
from benchmarks.vlm_bench.run import rebuild_request, replay_items
from benchmarks.vlm_bench.variants import get_variant
from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig
from reasoning.vlm.prompt_builder import build_prompt_payload
from tests.unit.vlm_bench_fixtures import synthetic_items

LOG_PREFIX = "[orchestrator_node-1] [INFO] [{t}] [orchestrator_node]: "
NO_YIELDER = "yield refused: no feasible yielder (robot_2 0.00 m retreat room < 1.70 m required)"
JC_TAGS = [
    "junction_clear=fallback:no_candidates",
    "junction_geometry=shipped_unsolved:missing=junction_recede_offset_m",
]


def _legs(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"robot_id": rid, "action": action, "status": "pending"} for rid, action in pairs]


def _artifact(rid: str, stamp: float, **fields: Any) -> dict[str, Any]:
    return {"request_id": rid, "scene": {"stamp": stamp, "robots": []}, **fields}


def _decision(strategy: str, involved: list[str]) -> dict[str, Any]:
    return {"congestion_detected": True, "strategy": strategy, "involved_robots": involved,
            "yield_robot": None}


def _bundle(tmp_path: Path) -> Path:
    """Dispatched yield, withheld junction_clear, a re-ask shown the withheld plan, a reverse."""
    plan1 = _legs(("robot_1", "yield"), ("robot_2", "cross"))
    plan2 = _legs(("robot_2", "yield"), ("robot_3", "cross"), ("robot_4", "cross"))
    plan3 = _legs(("robot_2", "reverse"), ("robot_3", "reverse"))
    arts = [
        _artifact("a" * 32, 10.0, decision=_decision("yield", ["robot_1", "robot_2"]),
                  plan={"plan_id": 1, "plan_held": False, "provenance": "m3_default",
                        "legs": plan1},
                  dispatched_command={"command_id": "c1"},
                  dispatched_robot_ids=["robot_1", "robot_2"]),
        _artifact("b" * 32, 20.0,
                  decision=_decision("junction_clear", ["robot_2", "robot_3", "robot_4"]),
                  plan_state={"plan_id": 1, "legs": [{**leg, "status": "done"} for leg in plan1],
                              "changed_robot_ids": []},
                  plan={"plan_id": 2, "plan_held": False, "provenance": "m3_default",
                        "legs": plan2},
                  dispatched_command={"command_id": "c2"},
                  dispatched_robot_ids=["robot_2", "robot_3", "robot_4"],
                  dispatch_withheld={"reason": "refusal_no_action", "refusal_reason": NO_YIELDER,
                                     "would_dispatch_robot_ids": ["robot_2", "robot_3",
                                                                  "robot_4"]},
                  grounding_degradations=JC_TAGS),
        _artifact("c" * 32, 30.0, decision=_decision("reverse", ["robot_2", "robot_3"]),
                  plan_state={"plan_id": 2, "legs": plan2, "changed_robot_ids": []},
                  plan={"plan_id": 3, "plan_held": False, "provenance": "m3_default",
                        "legs": plan3},
                  dispatched_command={"command_id": "c3"},
                  dispatched_robot_ids=["robot_2", "robot_3"]),
        _artifact("d" * 32, 40.0, decision={"congestion_detected": False, "strategy": "none",
                                            "involved_robots": []},
                  plan_state={"plan_id": 3, "legs": plan3, "changed_robot_ids": []}),
    ]
    bundle = tmp_path / "bundle"
    (bundle / "decisions").mkdir(parents=True)
    lines = []
    for index, art in enumerate(arts):
        (bundle / "decisions" / f"{art['request_id']}.json").write_text(json.dumps(art))
        start, end = 100.0 + 30 * index, 108.0 + 30 * index
        robots = (art["decision"]["involved_robots"] or ["robot_2", "robot_3"])
        lines.append(LOG_PREFIX.format(t=f"{start:.6f}")
                     + f"starting analysis request={art['request_id']} robots={robots} reason=x")
        lines.append(LOG_PREFIX.format(t=f"{end:.6f}")
                     + f"decision artifact written: data/x/{art['request_id']}.json")
    (bundle / "m5.log").write_text("\n".join(lines) + "\n")
    return bundle


def test_read_m5_log_parses_start_and_write_times(tmp_path):
    times = read_m5_log(_bundle(tmp_path))
    assert times.start["b" * 32] == (130.0, ["robot_2", "robot_3", "robot_4"])
    assert times.written["b" * 32] == 138.0


def test_withheld_decision_stated_in_next_overlapping_prompt(tmp_path):
    states = episode_feedback_states(_bundle(tmp_path))
    (proposal,) = states["c" * 32].refused_proposals
    assert proposal.strategy == "junction_clear"
    assert proposal.reason.startswith("this scene declares no junction recovery geometry")


def test_withheld_plan_replaced_by_last_dispatched_plan(tmp_path):
    state = episode_feedback_states(_bundle(tmp_path))["c" * 32]
    assert state.live_plan_was_withheld
    assert state.plan_state is not None and state.plan_state.plan_id == 1
    assert state.plan_state_source == "reconstructed"
    assert [leg.status for leg in state.plan_state.legs] == ["done", "done"]


def test_dispatch_forgets_withheld_proposal(tmp_path):
    state = episode_feedback_states(_bundle(tmp_path))["d" * 32]
    assert state.refused_proposals == ()
    assert state.plan_state is not None and state.plan_state.plan_id == 3


def test_expired_proposal_not_stated(tmp_path):
    states = episode_feedback_states(_bundle(tmp_path), window_sec=5.0)
    assert states["c" * 32].refused_proposals == ()


def test_variant_is_registered():
    assert get_variant("refusal_feedback").name == "refusal_feedback"


class _Scripted:
    def __init__(self) -> None:
        self.payloads: list[PromptPayload] = []

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        self.payloads.append(payload)
        text = json.dumps({"reasoning": "r", "congestion_detected": False, "type": "none",
                           "involved_robots": [], "root_cause": "c", "strategy": "none",
                           "justification": "j"})
        return BackendResponse(text=text, backend_id="scripted")


def test_replay_sends_offered_strategies_without_junction_clear(tmp_path):
    item = synthetic_items()["aaaa0002"]
    rendered = build_prompt_payload(rebuild_request(item, str(tmp_path / "x.png"))).user_prompt
    prompt = item.prompt.model_copy(
        update={"user_sha256": hashlib.sha256(rendered.encode()).hexdigest()}
    )
    item = item.model_copy(update={"prompt": prompt})
    backend = _Scripted()
    _, info = replay_items(
        [item], "gemini", "refusal_feedback", cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: backend,
    )
    row = info["per_item"][item.item_id]
    assert "junction_clear" not in row["offered_strategies"]
    assert backend.payloads and "junction_clear" not in backend.payloads[0].user_prompt
    sent = hashlib.sha256(backend.payloads[0].user_prompt.encode()).hexdigest()
    assert row["prompt_sha256"] == sent

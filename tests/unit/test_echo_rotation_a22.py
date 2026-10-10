"""prereg-v3 A22: the echo rotates its named pair after a refusal (apparatus only).

S1b E5 showed the A21 one-cluster echo STARVING: it re-named the closest
engaged pair [r1, r5] in all three analyses, every one refused, and the
second cluster {r3, r4} was never analysed. A22 rules that after a refusal on
the named pair the echo names the NEXT engaged pair (closest first, ties by
presentation), and once every engaged pair has been refused in the current
epoch it falls back to the pre-A20 all-stalled rule. A dispatch ends the
epoch. Live backends carry no hook, so scored arms are untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reasoning.vlm.mock_backend import (
    EchoMockBackend,
    EchoRobot,
    echo_engaged_pairs,
    echo_select,
    echo_selection,
)
from reasoning.vlm.models import PromptPayload
from tests.unit.test_churn_a21 import _cycle, _YieldPipeline
from tests.unit.test_echo_mock import _echo_node
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    _make_node,
    node_env,
)
from tests.unit.test_s1b_rulings_a20 import _decision, _ground, _refusal

E5 = json.loads(
    (Path(__file__).parent / "data/echo_rotation_a22/e5_scenes.json").read_text()
)["analyses"]

# E3-like: r1+r4 latched in the west passage (0.30 m), r3+r5 at N (0.35 m);
# robot_2 moving.
TWO_CLUSTERS = [
    EchoRobot("robot_1", -1.79, -0.08, True),
    EchoRobot("robot_2", -0.10, 1.40, False),
    EchoRobot("robot_3", -0.30, 1.05, True),
    EchoRobot("robot_4", -1.85, 0.21, True),
    EchoRobot("robot_5", 0.05, 1.10, True),
]


def _payload(analysis: dict) -> PromptPayload:
    return PromptPayload(
        system_prompt="s",
        user_prompt="Robot states:\n" + "\n".join(analysis["state_lines"]) + "\n",
        image_path="frame.png",
        known_robot_ids=analysis["known_robot_ids"],
    )


def _involved(backend: EchoMockBackend, analysis: dict) -> list[str]:
    return backend.decision_for(_payload(analysis))["involved_robots"]


def _executable_yield(analysis: dict, involved: list[str]) -> str | None:
    command = _ground(analysis["rows"], _decision(involved))
    if _refusal(command) is not None:
        return None
    return next(a["robot_id"] for a in command["actions"] if a["action"] == "yield")


# ---- the pure selection ----


def test_engaged_pairs_order_closest_first():
    assert echo_engaged_pairs(TWO_CLUSTERS) == [("robot_1", "robot_4"), ("robot_3", "robot_5")]


def test_selection_without_refusals_is_the_a21_closest_pair():
    selection = echo_selection(TWO_CLUSTERS)
    assert selection.robot_ids == ["robot_1", "robot_4"]
    assert selection.rule == "closest_pair"
    assert echo_select(TWO_CLUSTERS) == ["robot_1", "robot_4"]


def test_selection_rotates_past_a_refused_pair():
    selection = echo_selection(TWO_CLUSTERS, {frozenset({"robot_1", "robot_4"})})
    assert selection.robot_ids == ["robot_3", "robot_5"]
    assert (selection.rule, selection.refused_skipped) == ("rotated_pair", 1)


def test_selection_falls_back_to_all_stalled_when_every_pair_is_refused():
    refused = {frozenset({"robot_1", "robot_4"}), frozenset({"robot_3", "robot_5"})}
    selection = echo_selection(TWO_CLUSTERS, refused)
    assert selection.robot_ids == ["robot_1", "robot_3", "robot_4", "robot_5"]
    assert (selection.rule, selection.refused_skipped) == ("all_refused_fallback", 2)


def test_refused_pair_memory_survives_a_presentation_order_change():
    reversed_order = list(reversed(TWO_CLUSTERS))
    selection = echo_selection(reversed_order, {frozenset({"robot_1", "robot_4"})})
    assert selection.robot_ids == ["robot_5", "robot_3"]


def test_refused_pair_no_longer_engaged_is_ignored():
    selection = echo_selection(TWO_CLUSTERS, {frozenset({"robot_2", "robot_3"})})
    assert selection.robot_ids == ["robot_1", "robot_4"]
    assert selection.rule == "closest_pair"


# ---- the backend's epoch memory ----


def test_backend_remembers_a_refusal_and_names_the_next_pair():
    backend = EchoMockBackend()
    first, second = E5[0], E5[1]
    assert _involved(backend, first) == ["robot_1", "robot_5"]
    backend.note_dispatch_outcome(refused=True, dispatched=False)
    assert backend.refused_pairs == {frozenset({"robot_1", "robot_5"})}
    decision = backend.decision_for(_payload(second))
    assert decision["involved_robots"] == ["robot_3", "robot_4"]
    assert decision["yield_robot"] == "robot_3"
    assert "A22 rotation: rotated_pair" in decision["justification"]


def test_backend_dispatch_ends_the_epoch():
    backend = EchoMockBackend()
    _involved(backend, E5[0])
    backend.note_dispatch_outcome(refused=True, dispatched=False)
    assert _involved(backend, E5[1]) == ["robot_3", "robot_4"]
    backend.note_dispatch_outcome(refused=False, dispatched=True)
    assert backend.refused_pairs == frozenset()
    assert _involved(backend, E5[2]) == ["robot_1", "robot_5"]


def test_backend_outcome_without_dispatch_or_refusal_keeps_the_epoch():
    backend = EchoMockBackend()
    _involved(backend, E5[0])
    backend.note_dispatch_outcome(refused=True, dispatched=False)
    _involved(backend, E5[1])
    backend.note_dispatch_outcome(refused=False, dispatched=False)
    assert backend.refused_pairs == {frozenset({"robot_1", "robot_5"})}


def test_backend_default_justification_is_unchanged():
    decision = EchoMockBackend().decision_for(_payload(E5[0]))
    assert decision["justification"] == "echo-mock apparatus (A12(i)); not a model decision."


# ---- E5 replay: the second cluster now gets analysed ----


def test_e5_live_refusals_reproduce_on_this_tree():
    for analysis in E5:
        assert analysis["live_involved"] == ["robot_1", "robot_5"]
        command = _ground(analysis["rows"], _decision(analysis["live_involved"]))
        assert _refusal(command) == analysis["live_refusal"]


def test_e5_replay_rotation_reaches_the_second_cluster_with_an_executable_yield():
    backend = EchoMockBackend()
    named = []
    for analysis in E5:
        involved = _involved(backend, analysis)
        named.append(involved)
        refused = _executable_yield(analysis, involved) is None
        backend.note_dispatch_outcome(refused=refused, dispatched=not refused)
        if not refused:
            break
    # Live (A21): [r1, r5] x3, refused x3, {r3, r4} never analysed.
    assert named == [["robot_1", "robot_5"], ["robot_3", "robot_4"]]
    assert _executable_yield(E5[1], ["robot_3", "robot_4"]) == "robot_3"


def test_e5_replay_all_refused_sequence_rotates_then_falls_back():
    # Counterfactual where every naming is refused: E5's third scene has three
    # engaged pairs (r1+r5 0.36 m, r3+r4 0.37 m, r1+r2 0.38 m).
    backend = EchoMockBackend()
    third = E5[2]
    sequence = []
    for _ in range(4):
        sequence.append(_involved(backend, third))
        backend.note_dispatch_outcome(refused=True, dispatched=False)
    assert sequence == [
        ["robot_1", "robot_5"],
        ["robot_3", "robot_4"],
        ["robot_1", "robot_2"],
        ["robot_1", "robot_2", "robot_3", "robot_4", "robot_5"],
    ]


# ---- M5 wiring ----


class _NotingYieldPipeline(_YieldPipeline):
    def __init__(self) -> None:
        super().__init__()
        self.notes: list[tuple[bool, bool]] = []

    def note_dispatch_outcome(self, refused: bool, dispatched: bool) -> None:
        self.notes.append((refused, dispatched))


def test_node_notes_a_dispatch(node_env, tmp_path):  # noqa: F811
    pipeline = _NotingYieldPipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline, t0_probe_mode=False)
    _cycle(node, clock)
    assert len(node._cmd_pub.published) == 2
    assert pipeline.notes == [(False, True)]


def test_node_notes_a_withheld_dispatch_as_refused(node_env, tmp_path):  # noqa: F811
    pipeline = _NotingYieldPipeline()
    node, clock = _make_node(
        node_env, tmp_path, pipeline, t0_probe_mode=False,
        reanalysis_suppression={"enabled": True, "applies_to": "all"},
        churn_bound={"enabled": True, "budget_k": 1, "window_sim_sec": 600.0,
                     "alternation_max": 5},
    )
    node._churn.record(0.0, ("yield", "robot_1", "robot_2"), frozenset({"robot_1", "robot_2"}))
    _cycle(node, clock)
    assert node._cmd_pub.published == []
    assert pipeline.notes == [(True, False)]


def test_node_without_the_hook_runs_unchanged(node_env, tmp_path):  # noqa: F811
    pipeline = _YieldPipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline, t0_probe_mode=False)
    _cycle(node, clock)
    assert len(node._cmd_pub.published) == 2


def test_default_pipeline_wires_the_echo_hook(node_env, tmp_path, monkeypatch):  # noqa: F811
    node, _ = _echo_node(node_env, tmp_path, monkeypatch)
    observer = node._pipeline._dispatch_outcome_observer
    assert isinstance(observer.__self__, EchoMockBackend)
    assert observer.__func__ is EchoMockBackend.note_dispatch_outcome


def test_default_pipeline_without_echo_has_no_hook(node_env, tmp_path, monkeypatch):  # noqa: F811
    node, _ = _echo_node(node_env, tmp_path, monkeypatch)
    monkeypatch.delenv("VGU_MOCK_ECHO")
    node_module, _ = node_env
    plain = node_module.OrchestratorNode(config=node._config)
    assert plain._pipeline._dispatch_outcome_observer is None


@pytest.mark.parametrize(
    "module, name",
    [
        ("reasoning.vlm.gemini_backend", "GeminiBackend"),
        ("reasoning.vlm.openai_backend", "OpenAIBackend"),
        ("reasoning.vlm.anthropic_backend", "AnthropicBackend"),
        ("reasoning.vlm.llama_server_backend", "LlamaServerBackend"),
        ("reasoning.vlm.mock_backend", "MockBackend"),
    ],
)
def test_live_and_scripted_backends_have_no_rotation_hook(module, name):
    import importlib

    cls = getattr(importlib.import_module(module), name)
    assert not hasattr(cls, "note_dispatch_outcome")


def test_pipeline_without_observer_ignores_notes():
    from swarm_orchestrator.reasoning_pipeline import InProcessPipeline

    pipeline = InProcessPipeline(reasoner=None, ground_fn=lambda *a, **k: None)
    pipeline.note_dispatch_outcome(True, False)


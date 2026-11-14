"""Plan-grammar rules condition (prompt v3.5, 2026-11-15): two generic grammar sentences.

The condition adds exactly two lines to the v3.4 `_PLAN_GRAMMAR` block and
nothing else. Off (the default) every prompt stays byte-identical to the
pinned v3.4 prompts; v1/v2 are frozen and ignore it.
"""

from __future__ import annotations

import dataclasses
import difflib

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import AnnotationOverlayReport, plan_order_status_line
from swarm_orchestrator.reasoning_pipeline import build_prompt_conditions, build_reasoner_request

from reasoning.vlm.models import ReasonerRequest
from reasoning.vlm.prompt_builder import (
    _PLAN_GRAMMAR,
    _PLAN_GRAMMAR_RULES,
    _PLAN_GRAMMAR_V35,
    build_prompt_payload,
)
from scripts.replay_live_decisions import reconstruct_request
from tests.unit.test_m5_node_apparatus import _node, _RecordingPipeline, _run_trigger
from tests.unit.test_m5_node_probe import _artifact, _config, node_env  # noqa: F401
from tests.unit.test_m5_reasoning_pipeline import _snapshot
from tests.unit.test_prompt_apparatus_v3 import _CONDITIONS
from tests.unit.test_prompt_builder_v3 import _pinned_requests
from tests.unit.test_replay_live_decisions import fc_artifact  # noqa: F401  (fixture)

_SENTENCES = (
    "Name each robot exactly once: its one leg is its whole role in the resolution.",
    'A "cross" leg must come after the "yield" leg that releases it.',
)
_LIST_ORDER_LINE = "The list order is the execution order — the robot that acts first comes first."


def _fixtures() -> dict[str, ReasonerRequest]:
    requests = dict(_pinned_requests())
    base = requests["baseline"]
    for name, update in _CONDITIONS.items():
        requests[f"apparatus_{name}"] = base.model_copy(update=update)
    return requests


def _render(request: ReasonerRequest, **update: object) -> str:
    return build_prompt_payload(request.model_copy(update=update)).user_prompt


def test_rules_constant_is_the_two_sentences():
    assert _PLAN_GRAMMAR_RULES == "\n".join(_SENTENCES)


def test_v35_grammar_inserts_the_rules_after_the_list_order_line():
    assert _PLAN_GRAMMAR_V35 == _PLAN_GRAMMAR.replace(
        _LIST_ORDER_LINE, _LIST_ORDER_LINE + "\n" + _PLAN_GRAMMAR_RULES, 1
    )
    assert _LIST_ORDER_LINE in _PLAN_GRAMMAR


def test_request_defaults_to_rules_off():
    assert _pinned_requests()["baseline"].plan_grammar_rules is False


@pytest.mark.parametrize("name", list(_fixtures()))
def test_rules_off_renders_byte_identically_to_default(name: str):
    request = _fixtures()[name]
    assert _render(request, plan_grammar_rules=False) == _render(request)


@pytest.mark.parametrize("name", list(_fixtures()))
def test_rules_on_adds_exactly_the_two_sentences(name: str):
    request = _fixtures()[name]
    off = _render(request).splitlines()
    on = _render(request, plan_grammar_rules=True).splitlines()
    ops = [op for op in difflib.SequenceMatcher(a=off, b=on).get_opcodes() if op[0] != "equal"]
    assert len(ops) == 1
    tag, i1, i2, j1, j2 = ops[0]
    assert tag == "insert"
    assert on[j1:j2] == list(_SENTENCES)
    assert off[i1 - 1] == _LIST_ORDER_LINE


@pytest.mark.parametrize("version", [1, 2])
def test_frozen_templates_ignore_the_rules(version: int):
    request = _pinned_requests()["baseline"].model_copy(update={"prompt_version": version})
    assert _render(request, plan_grammar_rules=True) == _render(request)


def test_rules_name_no_robot_strategy_or_order():
    text = _PLAN_GRAMMAR_RULES.lower()
    for word in ("robot_", "junction", "first", "north", "south", "east", "west", "chi"):
        assert word not in text


def test_build_reasoner_request_passes_rules_through():
    request = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", prompt_version=3, plan_grammar_rules=True
    )
    assert request.plan_grammar_rules is True


def test_prompt_conditions_omit_rules_when_off():
    request = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png", prompt_version=3)
    dumped = _conditions(request).model_dump(mode="json")
    assert "plan_grammar_rules" not in dumped


def test_prompt_conditions_record_rules_when_on():
    request = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", prompt_version=3, plan_grammar_rules=True
    )
    dumped = _conditions(request).model_dump(mode="json")
    assert dumped["plan_grammar_rules"] is True


def _conditions(request: ReasonerRequest):
    return build_prompt_conditions(
        request=request,
        overlays=AnnotationOverlayReport(),
        prompt_metric_grid=False,
        prompt_motion_trails=False,
        prompt_zoom_tile=False,
        zoom_tile=None,
        permutation_votes=1,
        prompt_candidate_options=False,
    )


def test_replay_reconstructs_the_rules_from_prompt_conditions(fc_artifact):  # noqa: F811
    live = reconstruct_request(dataclasses.replace(fc_artifact, prompt_version=3)).model_copy(
        update={"plan_grammar_rules": True}
    )
    stored = dataclasses.replace(
        fc_artifact,
        prompt_version=3,
        prompt_conditions=_conditions(live).model_dump(mode="json"),
    )
    rebuilt = build_prompt_payload(reconstruct_request(stored)).user_prompt
    assert rebuilt == build_prompt_payload(live).user_prompt
    assert _SENTENCES[0] in rebuilt


class TestStatusLine:
    def test_default_config_logs_nothing_new(self, tmp_path):
        assert plan_order_status_line(_config(tmp_path)) is None

    def test_plan_channel_alone_logs_nothing_new(self, tmp_path):
        assert plan_order_status_line(_config(tmp_path, plan_channel_enabled=True)) is None

    def test_demo_condition_line_names_every_key(self, tmp_path):
        config = _config(
            tmp_path,
            plan_channel_enabled=True,
            plan_dispatch_order_source="model_when_verified",
            prompt_plan_grammar_rules=True,
        )
        assert plan_order_status_line(config) == (
            "plan order condition plan_dispatch_order_source=model_when_verified "
            "prompt_plan_grammar_rules=True prompt_candidate_options=False"
        )

    def test_candidate_options_alone_is_logged(self, tmp_path):
        config = _config(tmp_path, plan_channel_enabled=True, prompt_candidate_options=True)
        assert plan_order_status_line(config) == (
            "plan order condition plan_dispatch_order_source=chi "
            "prompt_plan_grammar_rules=False prompt_candidate_options=True"
        )


class TestConfig:
    def test_defaults_off(self, tmp_path):
        assert _config(tmp_path).prompt_plan_grammar_rules is False

    def test_requires_plan_channel(self, tmp_path):
        with pytest.raises(ValidationError, match="plan_channel_enabled"):
            _config(tmp_path, prompt_plan_grammar_rules=True)


class TestNode:
    def test_flag_off_request_carries_no_rules(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(node_env, tmp_path, pipeline, plan_channel_enabled=True)
        request_id = _run_trigger(node)
        assert pipeline.requests[0].plan_grammar_rules is False
        payload = _artifact(node, request_id)
        assert "plan_grammar_rules" not in payload["prompt_conditions"]
        assert _SENTENCES[0] not in payload["prompt"]["user_prompt"]

    def test_flag_on_renders_and_records_the_rules(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(
            node_env,
            tmp_path,
            pipeline,
            plan_channel_enabled=True,
            prompt_plan_grammar_rules=True,
        )
        request_id = _run_trigger(node)
        assert pipeline.requests[0].plan_grammar_rules is True
        payload = _artifact(node, request_id)
        assert payload["prompt_conditions"]["plan_grammar_rules"] is True
        assert payload["prompt_version"] == 3
        for sentence in _SENTENCES:
            assert sentence in payload["prompt"]["user_prompt"]

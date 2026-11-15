"""Held-robot state condition (2026-11-15): mark robots the task registry still holds back.

On, each listed robot's state line ends with `start_pending=true` and one
generic note follows the state lines. Off (None, the default) or an empty list,
every prompt stays byte-identical; v1/v2 are frozen and ignore it.
"""

from __future__ import annotations

import dataclasses
import difflib

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import (
    AnnotationOverlayReport,
    TaskAssignment,
    plan_order_status_line,
)
from swarm_orchestrator.reasoning_pipeline import build_prompt_conditions, build_reasoner_request

from reasoning.vlm.models import ReasonerRequest
from reasoning.vlm.prompt_builder import (
    _HELD_ROBOT_NOTE,
    _HELD_ROBOT_TOKEN,
    build_prompt_payload,
)
from scripts.replay_live_decisions import reconstruct_request
from tests.unit.test_m5_node_apparatus import _node, _RecordingPipeline, _run_trigger
from tests.unit.test_m5_node_probe import _artifact, _config, node_env  # noqa: F401
from tests.unit.test_m5_reasoning_pipeline import _snapshot
from tests.unit.test_prompt_apparatus_v3 import _CONDITIONS
from tests.unit.test_prompt_builder_v3 import _pinned_requests
from tests.unit.test_replay_live_decisions import fc_artifact  # noqa: F401  (fixture)

_NOTE = (
    "start_pending=true: the system has not yet released this robot to start its task; "
    "once released, it starts driving toward its goal_x, goal_y."
)


def _fixtures() -> dict[str, ReasonerRequest]:
    requests = dict(_pinned_requests())
    base = requests["baseline"]
    for name, update in _CONDITIONS.items():
        requests[f"apparatus_{name}"] = base.model_copy(update=update)
    return requests


def _render(request: ReasonerRequest, **update: object) -> str:
    return build_prompt_payload(request.model_copy(update=update)).user_prompt


def _held(request: ReasonerRequest) -> str:
    return request.robot_states[-1].robot_id


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


def test_note_constant_is_the_one_sentence():
    assert _HELD_ROBOT_NOTE == _NOTE
    assert _HELD_ROBOT_TOKEN == "start_pending=true"


def test_request_defaults_to_off():
    assert _pinned_requests()["baseline"].held_robot_ids is None


@pytest.mark.parametrize("name", list(_fixtures()))
def test_off_renders_byte_identically_to_default(name: str):
    request = _fixtures()[name]
    assert _render(request, held_robot_ids=None) == _render(request)


@pytest.mark.parametrize("name", list(_fixtures()))
def test_on_with_no_held_robot_renders_byte_identically(name: str):
    request = _fixtures()[name]
    assert _render(request, held_robot_ids=[]) == _render(request)


@pytest.mark.parametrize("name", list(_fixtures()))
def test_on_marks_only_the_held_line_and_adds_the_note(name: str):
    request = _fixtures()[name]
    held = _held(request)
    off = _render(request).splitlines()
    on = _render(request, held_robot_ids=[held]).splitlines()
    ops = [op for op in difflib.SequenceMatcher(a=off, b=on).get_opcodes() if op[0] != "equal"]
    changed = [(off[i1:i2], on[j1:j2]) for _, i1, i2, j1, j2 in ops]
    old_lines = [line for old, _ in changed for line in old]
    new_lines = [line for _, new in changed for line in new]
    assert len(old_lines) == 1
    assert old_lines[0].startswith(f"- robot_id={held},")
    assert new_lines == [old_lines[0] + ", start_pending=true", _NOTE]


def test_note_renders_once_for_several_held_robots():
    request = _pinned_requests()["baseline"]
    ids = [s.robot_id for s in request.robot_states]
    prompt = _render(request, held_robot_ids=ids)
    assert prompt.count(_NOTE) == 1
    assert prompt.count(", start_pending=true") == len(ids)


@pytest.mark.parametrize("version", [1, 2])
def test_frozen_templates_ignore_it(version: int):
    request = _pinned_requests()["baseline"].model_copy(update={"prompt_version": version})
    assert _render(request, held_robot_ids=[_held(request)]) == _render(request)


def test_request_rejects_unknown_robot():
    base = _pinned_requests()["baseline"].model_dump()
    with pytest.raises(ValidationError, match="held_robot_ids must be distinct robots"):
        ReasonerRequest(**{**base, "held_robot_ids": ["robot_99"]})


def test_request_rejects_duplicate_robot():
    request = _pinned_requests()["baseline"]
    held = _held(request)
    with pytest.raises(ValidationError, match="held_robot_ids must be distinct robots"):
        ReasonerRequest(**{**request.model_dump(), "held_robot_ids": [held, held]})


def test_note_names_no_robot_strategy_order_or_provider():
    text = _NOTE.lower()
    for word in (
        "robot_",
        "yield",
        "cross",
        "wait",
        "first",
        "order",
        "east",
        "west",
        "corridor",
        "convoy",
        "gemini",
        "claude",
        "gpt",
    ):
        assert word not in text


def test_build_reasoner_request_passes_it_through():
    request = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", prompt_version=3, held_robot_ids=["robot_0"]
    )
    assert request.held_robot_ids == ["robot_0"]


def test_prompt_conditions_omit_it_when_off():
    request = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png", prompt_version=3)
    assert "held_robot_ids" not in _conditions(request).model_dump(mode="json")


def test_prompt_conditions_record_an_empty_list_when_on_and_none_held():
    request = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", prompt_version=3, held_robot_ids=[]
    )
    assert _conditions(request).model_dump(mode="json")["held_robot_ids"] == []


def test_prompt_conditions_record_the_held_ids_when_on():
    request = build_reasoner_request(
        "r1", _snapshot(), "/tmp/r1.png", prompt_version=3, held_robot_ids=["robot_0"]
    )
    assert _conditions(request).model_dump(mode="json")["held_robot_ids"] == ["robot_0"]


def test_replay_reconstructs_it_from_prompt_conditions(fc_artifact):  # noqa: F811
    base = reconstruct_request(dataclasses.replace(fc_artifact, prompt_version=3))
    live = base.model_copy(update={"held_robot_ids": [_held(base)]})
    stored = dataclasses.replace(
        fc_artifact,
        prompt_version=3,
        prompt_conditions=_conditions(live).model_dump(mode="json"),
    )
    rebuilt = build_prompt_payload(reconstruct_request(stored)).user_prompt
    assert rebuilt == build_prompt_payload(live).user_prompt
    assert _NOTE in rebuilt


def test_config_defaults_off(tmp_path):
    assert _config(tmp_path).prompt_held_robot_state is False


def test_config_requires_plan_channel(tmp_path):
    with pytest.raises(ValidationError, match="prompt_held_robot_state"):
        _config(tmp_path, prompt_held_robot_state=True)


def test_status_line_absent_when_off_by_default(tmp_path):
    assert plan_order_status_line(_config(tmp_path, plan_channel_enabled=True)) is None


def test_status_line_unchanged_when_off(tmp_path):
    config = _config(tmp_path, plan_channel_enabled=True, prompt_plan_grammar_rules=True)
    assert "held_robot" not in plan_order_status_line(config)


def test_status_line_names_it_when_on(tmp_path):
    config = _config(tmp_path, plan_channel_enabled=True, prompt_held_robot_state=True)
    assert plan_order_status_line(config) == (
        "plan order condition plan_dispatch_order_source=chi "
        "prompt_plan_grammar_rules=False prompt_candidate_options=False "
        "prompt_held_robot_state=True"
    )


def _delayed_tasks() -> dict[str, TaskAssignment]:
    return {
        "robot_1": TaskAssignment(task="t", goal=(2.5, -0.35)),
        "robot_2": TaskAssignment(task="t", goal=(-2.5, 0.35), start_delay_sec=600.0),
    }


def test_node_flag_off_request_carries_no_held_state(node_env, tmp_path):  # noqa: F811
    pipeline = _RecordingPipeline()
    node, _ = _node(
        node_env, tmp_path, pipeline, plan_channel_enabled=True, initial_tasks=_delayed_tasks()
    )
    request_id = _run_trigger(node)
    assert pipeline.requests[0].held_robot_ids is None
    payload = _artifact(node, request_id)
    assert "held_robot_ids" not in payload["prompt_conditions"]
    assert _HELD_ROBOT_TOKEN not in payload["prompt"]["user_prompt"]


def test_node_flag_on_marks_the_registry_held_robot(node_env, tmp_path):  # noqa: F811
    pipeline = _RecordingPipeline()
    node, _ = _node(
        node_env,
        tmp_path,
        pipeline,
        plan_channel_enabled=True,
        prompt_held_robot_state=True,
        initial_tasks=_delayed_tasks(),
    )
    request_id = _run_trigger(node)
    assert pipeline.requests[0].held_robot_ids == ["robot_2"]
    payload = _artifact(node, request_id)
    assert payload["prompt_conditions"]["held_robot_ids"] == ["robot_2"]
    prompt = payload["prompt"]["user_prompt"]
    assert prompt.count(", start_pending=true") == 1
    assert _NOTE in prompt


def test_node_flag_on_with_nothing_held_renders_no_note(node_env, tmp_path):  # noqa: F811
    pipeline = _RecordingPipeline()
    node, _ = _node(node_env, tmp_path, pipeline, plan_channel_enabled=True,
                    prompt_held_robot_state=True)
    request_id = _run_trigger(node)
    assert pipeline.requests[0].held_robot_ids == []
    payload = _artifact(node, request_id)
    assert payload["prompt_conditions"]["held_robot_ids"] == []
    assert _NOTE not in payload["prompt"]["user_prompt"]

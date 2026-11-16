"""Shared M2 per-group contract on plain inputs: slots, choices model, parser, prompt section."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from reasoning.vlm.executable_options import (
    OUTSIDE,
    ClusterCandidateSet,
    ClusterOption,
    ObservedGroup,
)
from reasoning.vlm.models import PromptPayload
from reasoning.vlm.per_cluster_choice import (
    NONE_FEASIBLE,
    build_slots,
    choices_model,
    chosen_options,
    compose_per_cluster_payload,
    extract_json_object,
    group_decisions,
    parse_per_cluster_answer,
    read_answer_keys,
)


def _option(section: str, strategy: str, robots: tuple[str, ...], yielder: str | None = None):
    return ClusterOption(
        strategy=strategy, robots=robots, yield_robot=yielder,
        key=(strategy, *robots), separation_m=1.0, text=f"{strategy} {' '.join(robots)}",
        section=section, scope="group", base_key=(strategy, *robots),
    )


def _base() -> ClusterCandidateSet:
    return ClusterCandidateSet(
        item_id="req-1",
        threshold_m=1.5,
        groups=(
            ObservedGroup(label="A", robots=("robot_1", "robot_2"), min_separation_m=1.0),
            ObservedGroup(label="B", robots=("robot_3", "robot_4"), min_separation_m=1.0),
        ),
        options=(
            _option("A", "yield", ("robot_1", "robot_2"), "robot_1"),
            _option("A", "reverse", ("robot_1", "robot_2")),
            _option("B", "temporary_wait", ("robot_3", "robot_4")),
        ),
    )


def _reply(choices: object) -> str:
    return json.dumps({"type": "deadlock", "justification": "j", "choices": choices})


def test_build_slots_numbers_options_globally_per_group():
    candidates, order, seed = build_slots(_base())
    assert candidates.allowed() == {"A": ["1", "2", NONE_FEASIBLE], "B": ["3", NONE_FEASIBLE]}
    assert candidates.item_id == "req-1"
    assert (order, seed) == (None, None)


def test_build_slots_shuffles_within_groups_only():
    candidates, order, seed = build_slots(_base(), shuffle_seed=7)
    assert sorted(order) == [1, 2, 3]
    assert order[2] == 3
    assert seed is not None
    assert [o.section for o in candidates.base.options] == ["A", "A", "B"]


def test_build_slots_opaque_ids_avoid_none_feasible():
    candidates, _, _ = build_slots(_base(), option_ids="opaque")
    ids = [i for s in candidates.slots for i in s.option_ids]
    assert len(set(ids)) == 3
    assert NONE_FEASIBLE not in ids


def test_build_slots_outside_fallback_without_groups():
    base = ClusterCandidateSet(
        item_id="req-1", threshold_m=1.5,
        options=(_option(OUTSIDE, "reverse", ("robot_1", "robot_2")),),
    )
    candidates, _, _ = build_slots(base)
    assert candidates.labels == (OUTSIDE,)
    assert candidates.slots[0].robots == ("robot_1", "robot_2")


def test_choices_model_forbids_extra_and_cross_slot_ids():
    model = choices_model(build_slots(_base())[0])
    assert model.model_validate({"A": "1", "B": NONE_FEASIBLE})
    with pytest.raises(ValidationError):
        model.model_validate({"A": "3", "B": "3"})
    with pytest.raises(ValidationError):
        model.model_validate({"A": "1", "B": "3", "C": "1"})


def test_parse_per_cluster_answer_accepts_integer_ids():
    parsed = parse_per_cluster_answer(_reply({"A": 2, "B": "3"}), build_slots(_base())[0])
    assert parsed.status == "choices"
    assert parsed.choices == {"A": "2", "B": "3"}


def test_parse_per_cluster_answer_rejects_missing_key():
    parsed = parse_per_cluster_answer(_reply({"A": "1"}), build_slots(_base())[0])
    assert parsed.status == "parse_failure"
    assert "B" in (parsed.error or "")


def test_group_decisions_map_choices_to_option_decisions():
    candidates = build_slots(_base())[0]
    decisions = group_decisions(candidates, {"A": "1", "B": NONE_FEASIBLE}, {"type": "bottleneck"})
    assert decisions["B"] is None
    assert decisions["A"]["strategy"] == "yield"
    assert decisions["A"]["yield_robot"] == "robot_1"
    assert decisions["A"]["type"] == "bottleneck"
    assert chosen_options(candidates, {"A": "2", "B": "3"})["A"].strategy == "reverse"


def test_prompt_section_states_the_answer_keys():
    candidates = build_slots(_base())[0]
    base = PromptPayload(system_prompt="s", user_prompt="u", image_path="x.png", known_robot_ids=[])
    payload = compose_per_cluster_payload(base, candidates)
    assert payload.user_prompt.startswith("u\n\n")
    assert read_answer_keys(payload.user_prompt) == candidates.allowed()


def test_extract_json_object_tolerates_think_block_and_fence():
    text = '<think>hmm</think>\n```json\n{"choices": {"A": "1"}}\n```'
    assert extract_json_object(text) == {"choices": {"A": "1"}}

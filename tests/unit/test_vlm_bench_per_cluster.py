"""Grounding-first per-cluster choice (`gf-per-cluster-v1`): slots, contract, scoring, replay."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest
from pydantic import ValidationError

from benchmarks.vlm_bench.grounder_offline import ground_command, ground_decision
from benchmarks.vlm_bench.models import BenchItem, GroundingOutcome
from benchmarks.vlm_bench.run import rebuild_request, replay_items
from benchmarks.vlm_bench.scoring import score_group_decisions, score_item
from benchmarks.vlm_bench.variants import (
    NONE_FEASIBLE,
    PER_CLUSTER_VARIANT,
    FixedGroupChoiceBackend,
    FixedOptionBackend,
    compose_per_cluster_payload,
    executed_key_v2,
    generate_cluster_candidates,
    get_variant,
    list_variants,
    parse_per_cluster_answer,
    per_cluster_candidates,
    render_per_cluster_section,
)
from benchmarks.vlm_bench.variants.gf_cluster import OUTSIDE
from benchmarks.vlm_bench.variants.per_cluster import (
    choices_model,
    chosen_options,
    group_decisions,
    joint_check,
    read_answer_keys,
)
from benchmarks.vlm_bench.variants.per_cluster_report import (
    oracle_combos,
    per_cluster_row,
    render_per_cluster_summary,
)
from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig
from reasoning.vlm.prompt_builder import build_prompt_payload
from tests.unit.vlm_bench_fixtures import synthetic_items


def _item(request_id: str = "aaaa0002") -> BenchItem:
    return synthetic_items()[request_id]


def _with_live_hash(item: BenchItem, tmp_path) -> BenchItem:
    rendered = build_prompt_payload(rebuild_request(item, str(tmp_path / "x.png"))).user_prompt
    prompt = item.prompt.model_copy(
        update={"user_sha256": hashlib.sha256(rendered.encode()).hexdigest()}
    )
    return item.model_copy(update={"prompt": prompt})


def _all_moving(item: BenchItem) -> BenchItem:
    robots = [{**r, "status": "MOVING"} for r in item.scene["robots"]]
    return item.model_copy(update={"scene": {**item.scene, "robots": robots}})


class _NoGT:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"the slot builder read item.gt.{name}")


class _Scripted:
    def __init__(self, texts: list[str]) -> None:
        self.texts = list(texts)
        self.calls = 0

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        self.calls += 1
        return BackendResponse(text=self.texts.pop(0), backend_id="scripted")


def _reply(choices: dict[str, Any]) -> str:
    return json.dumps({"type": "deadlock", "justification": "test", "choices": choices})


def test_per_cluster_candidates_one_slot_per_observed_group():
    candidates, _, _ = per_cluster_candidates(_item())
    assert candidates.labels == ("A", "B")
    assert [s.robots for s in candidates.slots] == [("robot_3", "robot_4"), ("robot_1", "robot_5")]


def test_per_cluster_slots_equal_v2_sections_and_numbers():
    item = _item()
    v2 = generate_cluster_candidates(item, True, "drop", "drop")
    candidates, _, _ = per_cluster_candidates(item)
    for slot in candidates.slots:
        numbers = [n for n, o in enumerate(v2.options, start=1) if o.section == slot.label]
        assert slot.option_ids == tuple(str(n) for n in numbers)
        assert slot.options == tuple(v2.options[n - 1] for n in numbers)
    assert candidates.n_options == len(v2.options)


def test_per_cluster_candidates_never_reads_gt():
    item = _item()
    blind = item.model_copy(update={"gt": _NoGT()})
    for ids in ("numbered", "opaque"):
        assert per_cluster_candidates(blind, option_ids=ids)[0].model_dump(
            mode="json"
        ) == per_cluster_candidates(item, option_ids=ids)[0].model_dump(mode="json")


def test_per_cluster_candidates_no_group_scene_gets_outside_slot():
    candidates, _, _ = per_cluster_candidates(_all_moving(_item()))
    assert candidates.labels == (OUTSIDE,)
    assert candidates.slots[0].options


def test_opaque_ids_follow_the_option_not_the_position():
    item = _item()
    plain, _, _ = per_cluster_candidates(item, option_ids="opaque")
    shuffled, order, _ = per_cluster_candidates(item, option_ids="opaque", shuffle_seed=3)
    ids = {o.key: i for s in plain.slots for i, o in zip(s.option_ids, s.options, strict=True)}
    for slot in shuffled.slots:
        for option_id, option in zip(slot.option_ids, slot.options, strict=True):
            assert ids[option.key] == option_id
    assert order is not None and len(set(ids.values())) == len(ids)


def test_shuffle_keeps_options_within_their_slot():
    item = _item()
    plain, _, _ = per_cluster_candidates(item)
    shuffled, _, _ = per_cluster_candidates(item, shuffle_seed=11)
    for a, b in zip(plain.slots, shuffled.slots, strict=True):
        assert {o.key for o in a.options} == {o.key for o in b.options}


def test_choices_model_requires_every_group_key():
    candidates, _, _ = per_cluster_candidates(_item())
    model = choices_model(candidates)
    with pytest.raises(ValidationError):
        model.model_validate({"A": "1"})
    assert model.model_validate({"A": "1", "B": NONE_FEASIBLE}).model_dump() == {
        "A": "1", "B": NONE_FEASIBLE,
    }


def test_parse_per_cluster_answer_accepts_integer_numbered_ids():
    candidates, _, _ = per_cluster_candidates(_item())
    parsed = parse_per_cluster_answer(_reply({"A": 1, "B": 8}), candidates)
    assert parsed.status == "choices" and parsed.choices == {"A": "1", "B": "8"}


def test_parse_per_cluster_answer_rejects_missing_group():
    candidates, _, _ = per_cluster_candidates(_item())
    parsed = parse_per_cluster_answer(_reply({"A": 1}), candidates)
    assert parsed.status == "parse_failure" and "B" in parsed.error


def test_parse_per_cluster_answer_rejects_id_from_other_group():
    candidates, _, _ = per_cluster_candidates(_item())
    parsed = parse_per_cluster_answer(_reply({"A": 8, "B": 8}), candidates)
    assert parsed.status == "parse_failure" and "A" in parsed.error


def test_parse_per_cluster_answer_rejects_extra_key():
    candidates, _, _ = per_cluster_candidates(_item())
    parsed = parse_per_cluster_answer(_reply({"A": 1, "B": 8, "C": 2}), candidates)
    assert parsed.status == "parse_failure" and "C" in parsed.error


def test_parse_per_cluster_answer_rejects_missing_choices_object():
    candidates, _, _ = per_cluster_candidates(_item())
    parsed = parse_per_cluster_answer('{"option": 1}', candidates)
    assert parsed.status == "parse_failure" and "choices" in parsed.error


def test_parse_per_cluster_answer_accepts_none_feasible_everywhere():
    candidates, _, _ = per_cluster_candidates(_item())
    parsed = parse_per_cluster_answer(
        _reply({"A": NONE_FEASIBLE, "B": NONE_FEASIBLE}), candidates
    )
    assert parsed.status == "choices"
    assert group_decisions(candidates, parsed.choices) == {"A": None, "B": None}


def test_render_per_cluster_section_states_its_answer_keys():
    for ids in ("numbered", "opaque"):
        candidates, _, _ = per_cluster_candidates(_item(), option_ids=ids)
        text = render_per_cluster_section(candidates)
        assert read_answer_keys(text) == candidates.allowed()
        assert "Group A: robot_3, robot_4" in text


def test_group_decisions_reground_to_their_option_keys():
    item = _item()
    candidates, _, _ = per_cluster_candidates(item)
    for slot in candidates.slots:
        for option_id, option in zip(slot.option_ids, slot.options, strict=True):
            other = {s.label: NONE_FEASIBLE for s in candidates.slots}
            decision = group_decisions(candidates, {**other, slot.label: option_id})[slot.label]
            command = ground_command(item, decision)
            assert executed_key_v2(decision["strategy"], command) == option.key


def test_score_group_decisions_union_covers_split_clusters():
    item = _item()
    candidates, _, _ = per_cluster_candidates(item)
    decisions = group_decisions(candidates, {"A": "5", "B": "8"})
    score = score_group_decisions(item, decisions, "test", ground_decision)
    assert score.covered and score.positive and score.grounding.feasible
    assert set(score.involved) == {"robot_1", "robot_3", "robot_4", "robot_5"}
    assert score.decision["group_decisions"] == decisions


def test_score_group_decisions_all_none_scores_negative():
    item = _item()
    score = score_group_decisions(item, {"A": None, "B": None}, "test", ground_decision)
    assert score.valid and not score.positive and not score.covered


def test_score_group_decisions_single_choice_matches_score_item():
    item = _item()
    candidates, _, _ = per_cluster_candidates(item)
    decisions = group_decisions(candidates, {"A": "1", "B": NONE_FEASIBLE})
    combined = score_group_decisions(item, decisions, "test", ground_decision)
    single = score_item(item, decisions["A"], "test", ground_decision, with_cost=False)
    for field in ("covered", "cluster_recalls", "matched_conflict", "f1_matched", "yielder",
                  "mc_yielder", "mc_agree", "involved"):
        assert getattr(combined, field) == getattr(single, field)


def test_score_group_decisions_infeasible_option_makes_row_infeasible():
    item = _item()
    candidates, _, _ = per_cluster_candidates(item)
    decisions = group_decisions(candidates, {"A": "1", "B": "8"})
    refusing = decisions["B"]

    def ground(it, decision):
        if decision is refusing:
            return GroundingOutcome(feasible=False, refusal_reason="yield refused: test")
        return ground_decision(it, decision)

    score = score_group_decisions(item, decisions, "test", ground)
    assert not score.grounding.feasible
    assert score.grounding.refusal_reason == "yield refused: test"


def test_score_group_decisions_yielder_comes_from_option_with_mc_pair():
    item = _item()
    candidates, _, _ = per_cluster_candidates(item)
    a_yield = next(
        i for i, o in zip(candidates.slots[0].option_ids, candidates.slots[0].options, strict=True)
        if o.strategy == "yield"
    )
    decisions = group_decisions(candidates, {"A": a_yield, "B": "8"})
    score = score_group_decisions(item, decisions, "test", ground_decision)
    assert score.yielder == decisions["A"]["yield_robot"]


def test_joint_check_flags_robot_addressed_by_two_commands():
    item = _item()
    candidates, _, _ = per_cluster_candidates(item)
    a = next(o for o in candidates.slots[0].options if "robot_2" in o.robots)
    b = next(o for o in candidates.slots[1].options if "robot_2" in o.robots)
    check = joint_check(item, {"A": a, "B": b})
    assert check.n_commands == 2 and "robot_2" in check.shared_robots and check.exact_conflict


def test_joint_check_single_command_has_no_conflict():
    item = _item()
    candidates, _, _ = per_cluster_candidates(item)
    check = joint_check(item, {"A": candidates.slots[0].options[0], "B": None})
    assert check.n_commands == 1 and not check.exact_conflict and not check.path_proximity


def test_joint_check_never_reads_gt():
    item = _item()
    candidates, _, _ = per_cluster_candidates(item)
    chosen = chosen_options(candidates, {"A": "1", "B": "8"})
    blind = item.model_copy(update={"gt": _NoGT()})
    assert joint_check(blind, chosen) == joint_check(item, chosen)


def test_fixed_group_choice_backend_answers_first_option_per_group():
    candidates, _, _ = per_cluster_candidates(_item())
    payload = PromptPayload(
        system_prompt="s", user_prompt=render_per_cluster_section(candidates),
        image_path="x.png", known_robot_ids=[],
    )
    reply = FixedGroupChoiceBackend("first").analyze(payload, ReasonerConfig(backend_id="x"))
    parsed = parse_per_cluster_answer(reply.text, candidates)
    assert parsed.choices == {"A": "1", "B": "8"}


def test_replay_per_cluster_first_choice_scores_the_union(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    scores, info = replay_items(
        [item], "gemini", PER_CLUSTER_VARIANT, cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: FixedGroupChoiceBackend("first"),
    )
    row = info["per_item"][item.item_id]
    candidates, _, _ = per_cluster_candidates(item)
    base = build_prompt_payload(rebuild_request(item, str(tmp_path / "neutral_1280x720.png")))
    composed = compose_per_cluster_payload(base, candidates).user_prompt
    assert row["prompt_sha256"] == hashlib.sha256(composed.encode()).hexdigest()
    assert row["choices"] == {"A": "1", "B": "8"}
    assert row["chosen_v2_numbers"] == {"A": 1, "B": 8}
    assert row["joint_check"]["n_commands"] == 2
    assert info["candidate_generator_version"] == "gf-per-cluster-v1"
    assert info["candidate_generator"]["option_ids"] == "numbered"
    first_a, first_b = candidates.slots[0].options[0], candidates.slots[1].options[0]
    assert set(scores[0].involved) == set(first_a.robots) | set(first_b.robots)
    assert scores[0].grounding.feasible and scores[0].covered


def test_replay_per_cluster_none_feasible_everywhere_scores_negative(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    scores, _ = replay_items(
        [item], "gemini", PER_CLUSTER_VARIANT, cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: FixedGroupChoiceBackend("none_feasible"),
    )
    assert scores[0].valid and not scores[0].positive


def test_replay_per_cluster_reasks_on_missing_group(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    backend = _Scripted([_reply({"A": 1}), _reply({"A": 1, "B": NONE_FEASIBLE})])
    scores, info = replay_items(
        [item], "gemini", PER_CLUSTER_VARIANT, cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: backend,
    )
    row = info["per_item"][item.item_id]
    assert backend.calls == 2 and row["parse_status"] == "invalid" and row["attempts"] == 2
    assert row["choices"] == {"A": "1", "B": NONE_FEASIBLE}
    assert scores[0].positive


def test_replay_per_cluster_fails_after_max_attempts(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    backend = _Scripted([_reply({"A": 1})] * 6)
    scores, info = replay_items(
        [item], "gemini", PER_CLUSTER_VARIANT, cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: backend,
    )
    assert not scores[0].valid
    assert info["per_item"][item.item_id]["parse_status"] == "failed"


def test_replay_per_cluster_rejects_section_flags(tmp_path):
    with pytest.raises(ValueError, match="span"):
        replay_items(
            [_item()], "gemini", PER_CLUSTER_VARIANT, cache_dir=tmp_path,
            backend_factory=lambda _id, _raw: FixedGroupChoiceBackend(), cross_group="keep",
        )


def test_replay_opaque_ids_rejected_for_grounding_first(tmp_path):
    with pytest.raises(ValueError, match="opaque"):
        replay_items(
            [_item()], "gemini", "grounding_first", cache_dir=tmp_path,
            backend_factory=lambda _id, _raw: FixedOptionBackend(1), option_ids="opaque",
        )


def test_registry_lists_per_cluster_variant():
    assert PER_CLUSTER_VARIANT in list_variants()
    assert get_variant(PER_CLUSTER_VARIANT).generator_version == "gf-per-cluster-v1"


def test_oracle_combos_coverage_rule_names_both_split_clusters():
    item = _item()
    candidates, _, _ = per_cluster_candidates(item)
    combos = oracle_combos(item, candidates)
    combo, score = combos["coverage"]
    assert score.covered and all(o is not None for o in combo)


def test_oracle_combos_single_rule_chooses_at_most_one_group():
    item = _item()
    candidates, _, _ = per_cluster_candidates(item)
    combo, _ = oracle_combos(item, candidates)["single"]
    assert sum(1 for o in combo if o is not None) <= 1


def test_per_cluster_row_marks_split_stratum():
    row = per_cluster_row(_item())
    assert row["stratum"] == "split" and row["slots"] == {"A": 7, "B": 6}
    assert row["first"]["choice"] == {"A": 1, "B": 8}


def test_render_per_cluster_summary_lists_rules_and_chooser():
    rows = [per_cluster_row(i) for i in synthetic_items().values()]
    text = render_per_cluster_summary(rows)
    assert "oracle `coverage`" in text and "first option in every group" in text

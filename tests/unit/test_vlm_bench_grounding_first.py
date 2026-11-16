"""Grounding-first prompt variant: candidate sets, composition, option parsing, replay."""

from __future__ import annotations

import hashlib
import json

from benchmarks.vlm_bench.grounder_offline import ground_command, ground_decision
from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.run import rebuild_request, replay_items
from benchmarks.vlm_bench.variants import (
    CandidateSet,
    ExecutableOption,
    FixedOptionBackend,
    compose_payload,
    executed_key,
    generate_candidates,
    get_variant,
    list_variants,
    parse_option_answer,
    render_candidate_section,
    shuffle_candidates,
)
from benchmarks.vlm_bench.variants.candidate_report import candidate_row, render_candidate_summary
from reasoning.vlm.prompt_builder import build_prompt_payload
from tests.unit.vlm_bench_fixtures import synthetic_items


def _item(request_id: str = "aaaa0002") -> BenchItem:
    return synthetic_items()[request_id]


def _with_live_hash(item: BenchItem, tmp_path) -> BenchItem:
    # The fixture's stored hash is not the live builder's; replay skips on mismatch.
    rendered = build_prompt_payload(rebuild_request(item, str(tmp_path / "x.png"))).user_prompt
    prompt = item.prompt.model_copy(
        update={"user_sha256": hashlib.sha256(rendered.encode()).hexdigest()}
    )
    return item.model_copy(update={"prompt": prompt})


def _reply(option: object) -> str:
    return json.dumps(
        {
            "congestion_detected": True,
            "type": "bottleneck",
            "involved_robots": ["robot_1", "robot_2", "robot_3"],
            "root_cause": "two robots meet in the aisle",
            "strategy": "yield",
            "justification": "the closest executable yield",
            "option": option,
        }
    )


def test_generate_candidates_finds_feasible_yield_pairs():
    yields = {o.robots for o in generate_candidates(_item()).options if o.strategy == "yield"}
    assert yields == {("robot_2", "robot_4"), ("robot_4", "robot_5"), ("robot_2", "robot_3")}


def test_generate_candidates_yield_options_ground_unswapped():
    item = _item()
    for option in generate_candidates(item).options:
        if option.strategy == "yield":
            outcome = ground_decision(item, option.decision())
            assert outcome.feasible and outcome.grounded_yielder == option.yield_robot


def test_generate_candidates_excludes_waypointless_reroute():
    item = _item()
    probe = {
        "congestion_detected": True, "type": "deadlock", "involved_robots": ["robot_1"],
        "root_cause": "x", "strategy": "reroute", "justification": "x",
    }
    assert ground_decision(item, probe).feasible  # the lenient bench metric accepts it
    assert all(o.strategy != "reroute" for o in generate_candidates(item).options)


def test_generate_candidates_excludes_refused_reverse():
    pairs = {o.robots for o in generate_candidates(_item()).options if o.strategy == "reverse"}
    assert ("robot_1", "robot_3") not in pairs
    assert ("robot_2", "robot_3") in pairs


def test_generate_candidates_empty_when_no_option_exists():
    item = _item()
    scene = {**item.scene, "robots": item.scene["robots"][:1]}
    assert generate_candidates(item.model_copy(update={"scene": scene})).options == ()


def test_generate_candidates_lists_wait_last_only_when_included():
    item = _item()
    with_wait = generate_candidates(item).options
    strategies = [o.strategy for o in with_wait]
    first_wait = strategies.index("temporary_wait")
    assert set(strategies[first_wait:]) == {"temporary_wait"}
    assert all(o.resolving for o in generate_candidates(item, include_wait=False).options)


def test_option_decision_regrounds_to_probe_key():
    item = _item()
    for option in generate_candidates(item).options:
        decision = option.decision()
        assert executed_key(decision["strategy"], ground_command(item, decision)) == option.key


def test_compose_payload_keeps_baseline_prompt_verbatim(tmp_path):
    item = _item()
    base = build_prompt_payload(rebuild_request(item, str(tmp_path / "x.png")))
    candidates = generate_candidates(item)
    composed = compose_payload(base, candidates)
    assert composed.user_prompt.startswith(base.user_prompt + "\n\n")
    assert composed.system_prompt == base.system_prompt
    assert f"\n1) {candidates.options[0].text}\n" in composed.user_prompt
    assert f"\n{len(candidates.options) + 1}) none of the above" in composed.user_prompt


def test_parse_option_answer_maps_valid_number_to_option_decision():
    candidates = generate_candidates(_item())
    parsed = parse_option_answer(_reply(2), candidates)
    option = candidates.options[1]
    assert parsed.status == "option"
    assert parsed.decision["involved_robots"] == list(option.robots)
    assert parsed.decision["strategy"] == option.strategy
    assert parsed.decision["type"] == "bottleneck"
    assert parsed.model_involved == ("robot_1", "robot_2", "robot_3")


def test_parse_option_answer_accepts_numeric_string():
    assert parse_option_answer(_reply("1"), generate_candidates(_item())).status == "option"


def test_parse_option_answer_none_word_gives_negative_decision():
    parsed = parse_option_answer(_reply("none"), generate_candidates(_item()))
    assert parsed.status == "none"
    assert parsed.decision["congestion_detected"] is False
    assert parsed.decision["strategy"] == "none"


def test_parse_option_answer_none_number_gives_negative_decision():
    candidates = generate_candidates(_item())
    parsed = parse_option_answer(_reply(len(candidates.options) + 1), candidates)
    assert parsed.status == "none"
    assert parsed.decision["congestion_detected"] is False


def test_parse_option_answer_out_of_range_records_failure():
    parsed = parse_option_answer(_reply(999), generate_candidates(_item()))
    assert parsed.status == "parse_failure"
    assert parsed.decision is None
    assert "999" in parsed.error


def test_parse_option_answer_missing_field_records_failure():
    parsed = parse_option_answer('{"strategy": "yield"}', generate_candidates(_item()))
    assert (parsed.status, parsed.error) == ("parse_failure", 'missing "option" field')


def test_parse_option_answer_non_json_records_failure():
    assert parse_option_answer("option 1", generate_candidates(_item())).status == (
        "parse_failure"
    )


def test_replay_fixed_option_one_feasible_on_items_with_options(tmp_path):
    items = [_with_live_hash(item, tmp_path) for item in synthetic_items().values()]
    scores, info = replay_items(
        items, "gemini", "grounding_first", cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: FixedOptionBackend(1),
    )
    assert len(scores) == len(items) and info["skipped_prompt_mismatch"] == []
    for score in scores:
        assert info["per_item"][score.item_id]["n_candidates"] >= 1
        assert score.positive and score.grounding.feasible
    assert info["candidate_generator_version"] == "gf-candidates-v1"


def test_replay_records_composed_prompt_hash(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    _, info = replay_items(
        [item], "gemini", "grounding_first", cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: FixedOptionBackend(1),
    )
    base = build_prompt_payload(rebuild_request(item, str(tmp_path / "neutral_1280x720.png")))
    composed = compose_payload(base, generate_candidates(item)).user_prompt
    expected = hashlib.sha256(composed.encode()).hexdigest()
    assert info["per_item"][item.item_id]["prompt_sha256"] == expected


def test_replay_out_of_range_option_records_parse_failure(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    scores, info = replay_items(
        [item], "gemini", "grounding_first", cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: FixedOptionBackend(999),
    )
    assert scores[0].decision is None and not scores[0].valid
    assert "parse_failure" in scores[0].note
    assert info["per_item"][item.item_id]["parse_status"] == "failed"


def test_replay_fixed_none_scores_negative(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    scores, _ = replay_items(
        [item], "gemini", "grounding_first", cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: FixedOptionBackend("none"),
    )
    assert scores[0].valid and not scores[0].positive


def test_registry_lists_baseline_and_grounding_first():
    assert list_variants() == [
        "baseline", "grounding_first", "grounding_first_per_cluster", "refusal_feedback"
    ]
    assert get_variant("grounding_first").generator_version == "gf-candidates-v1"


def test_candidate_row_matches_recorded_wait_on_executed_key():
    row = candidate_row(_item("aaaa0001"))
    assert row["recorded_executed_key"] == ["temporary_wait", "robot_1", "robot_2"]
    assert (row["in_set_all"], row["in_set_resolving"]) == (True, False)


def test_candidate_summary_counts_recorded_positives():
    rows = [candidate_row(item) for item in synthetic_items().values()]
    text = render_candidate_summary(rows)
    assert "recorded positives: 3" in text
    assert "| incl. temporary_wait |" in text


def test_candidate_row_cluster_flag_false_without_gt_clusters():
    item = _item()
    item = item.model_copy(update={"gt": item.gt.model_copy(update={"clusters": ()})})
    row = candidate_row(item)
    assert row["any_resolving"] and not row["any_resolving_in_cluster"]


def _dummy_set(item_id: str, n: int = 8) -> CandidateSet:
    options = tuple(
        ExecutableOption(
            strategy="temporary_wait", robots=(f"robot_{i}", "robot_x"),
            key=("temporary_wait", f"robot_{i}"), separation_m=float(i), text=f"wait {i}",
        )
        for i in range(n)
    )
    return CandidateSet(item_id=item_id, options=options)


def test_shuffle_candidates_same_seed_and_item_gives_same_order():
    _, first, seed_a = shuffle_candidates(_dummy_set("bundle:a"), 20261023)
    _, second, seed_b = shuffle_candidates(_dummy_set("bundle:a"), 20261023)
    assert first == second and seed_a == seed_b
    assert sorted(first) == list(range(1, 9))


def test_shuffle_candidates_different_items_get_different_orders():
    orders = {shuffle_candidates(_dummy_set(f"bundle:{i}"), 20261023)[1] for i in range(5)}
    assert len(orders) > 1


def test_shuffle_candidates_keeps_none_last():
    permuted, order, _ = shuffle_candidates(_dummy_set("bundle:a"), 7)
    section = render_candidate_section(permuted)
    assert "9) none of the above" in section
    assert permuted.options[0].text == f"wait {order[0] - 1}"


def test_replay_shuffled_fixed_option_one_maps_to_presented_slot(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    scores, info = replay_items(
        [item], "gemini", "grounding_first", cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: FixedOptionBackend(1), shuffle_seed=20261023,
    )
    row = info["per_item"][item.item_id]
    original = generate_candidates(item).options[row["option_order"][0] - 1]
    assert row["option_number"] == 1 and row["original_option"] == row["option_order"][0]
    assert scores[0].decision["involved_robots"] == list(original.robots)
    assert scores[0].decision["yield_robot"] == original.yield_robot
    assert info["shuffle_seed"] == 20261023 and row["shuffle_item_seed"] is not None


def test_replay_shuffle_seed_rejected_for_baseline(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    try:
        replay_items(
            [item], "gemini", "baseline", cache_dir=tmp_path,
            backend_factory=lambda _id, _raw: FixedOptionBackend(1), shuffle_seed=1,
        )
    except ValueError as exc:
        assert "grounding_first" in str(exc)
    else:
        raise AssertionError("expected ValueError")

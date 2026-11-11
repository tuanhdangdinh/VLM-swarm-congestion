"""Grounding-first v2 (`gf-candidates-v2`): observed groups, group options, sections, replay."""

from __future__ import annotations

import hashlib
import math
from typing import Any

from benchmarks.vlm_bench.grounder_offline import ground_command
from benchmarks.vlm_bench.models import BenchItem, GTContext
from benchmarks.vlm_bench.run import rebuild_request, replay_items
from benchmarks.vlm_bench.variants import (
    ClusterOption,
    FixedOptionBackend,
    compose_cluster_payload,
    executed_key,
    executed_key_v2,
    generate_cluster_candidates,
    get_variant,
    gf_cluster,
    observed_groups,
    parse_option_answer,
    render_cluster_section,
    shuffle_cluster_candidates,
)
from benchmarks.vlm_bench.variants.cluster_report import (
    cluster_candidate_row,
    oracle_choices,
    render_cluster_summary,
)
from benchmarks.vlm_bench.variants.gf_cluster import (
    OUTSIDE,
    SPAN,
    GroupingParams,
    grouping_params,
)
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


def _with_robots(item: BenchItem, **changes: dict[str, Any]) -> BenchItem:
    robots = [{**r, **changes.get(r["robot_id"], {})} for r in item.scene["robots"]]
    return item.model_copy(update={"scene": {**item.scene, "robots": robots}})


class _NoGT:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"the generator read item.gt.{name}")


def _dump(candidates) -> dict[str, Any]:
    return candidates.model_dump(mode="json")


def test_observed_groups_links_stopped_robots_within_threshold():
    groups = observed_groups(_item())
    assert [(g.label, g.robots) for g in groups] == [
        ("A", ("robot_3", "robot_4")),
        ("B", ("robot_1", "robot_5")),
    ]


def test_observed_groups_moving_robot_joins_without_bridging():
    # robot_2 (MOVING) is 1.0 m from robot_1 and robot_3; it joins robot_3's
    # group but does not pull robot_1 (2.0 m from robot_3) in.
    (group,) = observed_groups(_item("aaaa0001"))
    assert group.robots == ("robot_2", "robot_3", "robot_4", "robot_5")
    assert group.attached == ("robot_2",)


def test_observed_groups_threshold_comes_from_recorded_r_conflict():
    item = _item()
    params = {**item.classical.params, "r_conflict_m": 0.4}
    item = item.model_copy(
        update={"classical": item.classical.model_copy(update={"params": params})}
    )
    assert grouping_params(item).threshold_m == 0.4
    assert [g.robots for g in observed_groups(item)] == [("robot_3", "robot_4")]


def test_observed_groups_boundary_distance_is_inside():
    item = _item()
    pose = {r["robot_id"]: (r["x"], r["y"]) for r in item.scene["robots"]}
    exact = math.dist(pose["robot_1"], pose["robot_5"])
    groups = observed_groups(item, GroupingParams(threshold_m=exact))
    assert ("robot_1", "robot_5") in [g.robots for g in groups]


def test_observed_groups_stale_robot_seeds_a_group():
    item = _with_robots(_item(), robot_3={"status": "STALE"})
    assert ("robot_3", "robot_4") in [g.robots for g in observed_groups(item)]


def test_generate_cluster_candidates_never_reads_gt():
    item = _item()
    blind = item.model_copy(update={"gt": _NoGT()})
    for off, cross in (("drop", "drop"), ("keep", "keep")):
        assert _dump(generate_cluster_candidates(blind, True, off, cross)) == _dump(
            generate_cluster_candidates(item, True, off, cross)
        )


def test_generate_cluster_candidates_same_with_empty_gt():
    item = _item()
    stripped = item.model_copy(update={"gt": GTContext()})
    assert _dump(generate_cluster_candidates(stripped, True, "keep", "keep")) == _dump(
        generate_cluster_candidates(item, True, "keep", "keep")
    )


def test_cluster_option_decision_regrounds_to_its_key():
    for request_id in ("aaaa0001", "aaaa0002"):
        item = _item(request_id)
        for option in generate_cluster_candidates(item, True, "keep", "keep").options:
            decision = option.decision()
            command = ground_command(item, decision)
            assert executed_key_v2(decision["strategy"], command) == option.key
            assert executed_key(decision["strategy"], command) == option.base_key


def test_cluster_options_are_unique_on_executed_key():
    options = generate_cluster_candidates(_item(), True, "keep", "keep").options
    assert len({o.key for o in options}) == len(options)


def test_group_yield_probe_names_passers_nearest_first(monkeypatch):
    item = _with_robots(_item("aaaa0001"), robot_2={"status": "STOPPED"})
    probes: list[dict[str, Any]] = []

    def fake_ground(_item: BenchItem, decision: dict[str, Any]) -> dict[str, Any]:
        probes.append(decision)
        return {"actions": []}  # executes nothing: every probe is dropped

    monkeypatch.setattr(gf_cluster, "ground_command", fake_ground)
    gf_cluster.generate_cluster_candidates(item)
    group_yields = [
        p for p in probes if p["strategy"] == "yield" and len(p["involved_robots"]) > 2
    ]
    by_yielder = {p["yield_robot"]: p for p in group_yields}
    probe = by_yielder["robot_3"]
    # robot_2 and robot_4 are 1.0 m from robot_3 (ties break on id), robot_1 and robot_5 2.0 m.
    assert probe["involved_robots"] == ["robot_3", "robot_2", "robot_4", "robot_1", "robot_5"]
    assert probe["crossing_order"] == ["robot_2", "robot_4", "robot_1", "robot_5", "robot_3"]


def test_cluster_option_decision_keeps_crossing_order():
    option = ClusterOption(
        strategy="yield", robots=("robot_3", "robot_4", "robot_5"), yield_robot="robot_3",
        key=("yield", "robot_3", "robot_4", "robot_5"), separation_m=0.5, text="x",
        section="A", scope="group", crossing_order=("robot_4", "robot_5", "robot_3"),
        base_key=("yield", "robot_3", "robot_4", "robot_5"),
    )
    decision = option.decision({"type": "bottleneck"})
    assert decision["crossing_order"] == ["robot_4", "robot_5", "robot_3"]
    assert decision["involved_robots"] == ["robot_3", "robot_4", "robot_5"]
    assert decision["type"] == "bottleneck"


def test_executed_key_v2_appends_unlinked_holds():
    command = {
        "actions": [
            {"action": "yield", "robot_id": "robot_3",
             "parameters": {"passer_robot_id": "robot_4", "crossing_order": ["robot_4"]}},
            {"action": "temporary_wait", "robot_id": "robot_4",
             "parameters": {"linked_position": 0}},
            {"action": "temporary_wait", "robot_id": "robot_5", "parameters": {}},
            {"action": "temporary_wait", "robot_id": "robot_2", "parameters": {}},
        ],
        "degradations": ["order=lane_scoped:robot_2,robot_5"],
    }
    assert executed_key("yield", command) == ("yield", "robot_3", "robot_4")
    assert executed_key_v2("yield", command) == (
        "yield", "robot_3", "robot_4", "hold", "robot_2", "robot_5"
    )


def test_executed_key_v2_equals_v1_without_holds():
    command = {
        "actions": [
            {"action": "yield", "robot_id": "robot_3",
             "parameters": {"crossing_order": ["robot_4", "robot_5"]}},
            {"action": "temporary_wait", "robot_id": "robot_4",
             "parameters": {"linked_position": 0}},
            {"action": "temporary_wait", "robot_id": "robot_5",
             "parameters": {"linked_position": 1}},
        ],
    }
    assert executed_key_v2("yield", command) == executed_key("yield", command)
    assert executed_key_v2("yield", command) == ("yield", "robot_3", "robot_4", "robot_5")


def test_offgroup_and_cross_group_flags_drop_their_sections():
    item = _item()
    dropped = {o.section for o in generate_cluster_candidates(item).options}
    kept = {o.section for o in generate_cluster_candidates(item, True, "keep", "keep").options}
    assert dropped == {"A", "B"}
    assert SPAN in kept and kept <= {"A", "B", SPAN, OUTSIDE}


def test_outside_section_kept_when_scene_has_no_group():
    moving = {f"robot_{i}": {"status": "MOVING"} for i in range(1, 6)}
    item = _with_robots(_item(), **moving)
    candidates = generate_cluster_candidates(item, True, "drop", "drop")
    assert candidates.groups == ()
    assert candidates.options and {o.section for o in candidates.options} == {OUTSIDE}


def test_partial_pairs_listed_under_their_group():
    # robot_2 (MOVING, 0.5+ m away) is in no group; its pairs with robot_3/4 go under A.
    options = generate_cluster_candidates(_item()).options
    partial = [o for o in options if o.scope == "pair_partial" and "robot_2" in o.robots]
    assert partial and {o.section for o in partial} == {"A", "B"}
    for option in partial:
        group = {"A": {"robot_3", "robot_4"}, "B": {"robot_1", "robot_5"}}[option.section]
        assert set(option.robots) - {"robot_2"} <= group


def test_sections_are_contiguous_with_waits_last_in_each():
    options = generate_cluster_candidates(_item(), True, "keep", "keep").options
    sections = [o.section for o in options]
    order = list(dict.fromkeys(sections))
    assert sections == sorted(sections, key=order.index)
    assert order[:2] == ["A", "B"]
    for name in order:
        strategies = [o.strategy for o in options if o.section == name]
        if "temporary_wait" in strategies:
            first = strategies.index("temporary_wait")
            assert set(strategies[first:]) == {"temporary_wait"}


def test_group_wait_precedes_pair_waits():
    options = [o for o in generate_cluster_candidates(_item()).options if o.section == "A"]
    waits = [o for o in options if o.strategy == "temporary_wait"]
    assert waits[0].scope == "group" and waits[0].robots == ("robot_3", "robot_4")


def test_include_wait_false_lists_only_resolving_options():
    options = generate_cluster_candidates(_item(), False, "keep", "keep").options
    assert options and all(o.resolving for o in options)


def test_render_cluster_section_headers_and_ranges():
    candidates = generate_cluster_candidates(_item(), True, "keep", "keep")
    text = render_cluster_section(candidates)
    counts = candidates.section_counts()
    a, b = counts["A"], counts["B"]
    assert f"Group A: robot_3, robot_4 (options 1-{a})" in text
    assert f"Group B: robot_1, robot_5 (options {a + 1}-{a + b})" in text
    assert "Pairs spanning two observed groups" in text
    assert "within 1.50 m" in text
    n = len(candidates.options)
    assert f"{n + 1}) none of the above" in text
    assert f"{n}) {candidates.options[-1].text}" in text


def test_shuffle_cluster_candidates_stays_within_sections():
    candidates = generate_cluster_candidates(_item(), True, "keep", "keep")
    permuted, order, seed = shuffle_cluster_candidates(candidates, 20261023)
    again = shuffle_cluster_candidates(candidates, 20261023)
    assert (order, seed) == (again[1], again[2])
    assert sorted(order) == list(range(1, len(candidates.options) + 1))
    assert order != tuple(range(1, len(order) + 1))
    assert [o.section for o in permuted.options] == [o.section for o in candidates.options]
    for slot, original in enumerate(order):
        assert permuted.options[slot] == candidates.options[original - 1]
    assert f"{len(order) + 1}) none of the above" in render_cluster_section(permuted)


def test_parse_option_answer_maps_cluster_option():
    candidates = generate_cluster_candidates(_item())
    parsed = parse_option_answer('{"option": 1, "type": "deadlock"}', candidates)
    assert parsed.status == "option"
    assert parsed.decision["involved_robots"] == list(candidates.options[0].robots)


def test_registry_grounding_first_still_reports_v1():
    assert get_variant("grounding_first").generator_version == "gf-candidates-v1"


def test_replay_v2_fixed_option_one_records_generator_and_prompt(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    scores, info = replay_items(
        [item], "gemini", "grounding_first", cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: FixedOptionBackend(1), generator="v2",
    )
    row = info["per_item"][item.item_id]
    candidates = generate_cluster_candidates(item)
    base = build_prompt_payload(rebuild_request(item, str(tmp_path / "neutral_1280x720.png")))
    composed = compose_cluster_payload(base, candidates).user_prompt
    assert info["candidate_generator_version"] == "gf-candidates-v2"
    assert info["candidate_generator"]["offgroup"] == "drop"
    assert row["prompt_sha256"] == hashlib.sha256(composed.encode()).hexdigest()
    assert row["grouping_threshold_m"] == 1.5
    assert row["groups"] == {"A": ["robot_3", "robot_4"], "B": ["robot_1", "robot_5"]}
    assert row["n_candidates"] == len(candidates.options)
    assert scores[0].positive and scores[0].grounding.feasible
    assert scores[0].decision["involved_robots"] == list(candidates.options[0].robots)


def test_replay_v2_shuffled_maps_presented_slot_to_original(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    scores, info = replay_items(
        [item], "gemini", "grounding_first", cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: FixedOptionBackend(1), shuffle_seed=7,
        generator="v2", offgroup="keep", cross_group="keep",
    )
    row = info["per_item"][item.item_id]
    candidates = generate_cluster_candidates(item, True, "keep", "keep")
    original = candidates.options[row["option_order"][0] - 1]
    assert row["original_option"] == row["option_order"][0]
    assert scores[0].decision["involved_robots"] == list(original.robots)


def test_replay_v1_run_info_has_no_v2_fields(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    _, info = replay_items(
        [item], "gemini", "grounding_first", cache_dir=tmp_path,
        backend_factory=lambda _id, _raw: FixedOptionBackend(1),
    )
    assert "candidate_generator" not in info
    assert "groups" not in info["per_item"][item.item_id]


def test_replay_generator_v2_rejected_for_baseline(tmp_path):
    item = _with_live_hash(_item(), tmp_path)
    try:
        replay_items(
            [item], "gemini", "baseline", cache_dir=tmp_path,
            backend_factory=lambda _id, _raw: FixedOptionBackend(1), generator="v2",
        )
    except ValueError as exc:
        assert "grounding_first" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_replay_unknown_generator_rejected(tmp_path):
    try:
        replay_items(
            [_item()], "gemini", "grounding_first", cache_dir=tmp_path,
            backend_factory=lambda _id, _raw: FixedOptionBackend(1), generator="v3",
        )
    except ValueError as exc:
        assert "v3" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_oracle_choices_coverage_rule_covers_both_clusters():
    item = _item()
    options = generate_cluster_candidates(item, True, "keep", "keep").options
    choices = oracle_choices(item, options)
    number, score = choices["coverage"]
    assert number is not None and score.covered
    assert set(options[number - 1].robots) & {"robot_1", "robot_5"}
    assert set(options[number - 1].robots) & {"robot_3", "robot_4"}


def test_oracle_choices_empty_list_answers_none():
    number, score = oracle_choices(_item(), ())["match"]
    assert number is None and score.valid and not score.positive


def test_cluster_candidate_row_counts_executed_not_listed():
    row = cluster_candidate_row(_item("aaaa0003"))
    # The recorded 4-robot wait spans both observed groups: unlisted in v1 and in v2.
    assert row["executed_not_listed_v1"] and not row["in_set_all"]
    assert row["groups"] == {"A": ["robot_3", "robot_4"], "B": ["robot_1", "robot_5"]}
    assert row["agreement"]["all_contained"]


def test_render_cluster_summary_lists_configs():
    rows = {"v2 (drop outside, drop span)": [cluster_candidate_row(i)
                                              for i in synthetic_items().values()]}
    text = render_cluster_summary(rows)
    assert "| gf-candidates-v1 |" in text
    assert "| v2 (drop outside, drop span) |" in text
    assert "Oracle choice, rule `match`" in text

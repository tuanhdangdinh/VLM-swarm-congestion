"""Bench adapters equal the shared reasoning code on the same item, and old import paths hold."""

from __future__ import annotations

from functools import partial
from typing import Any

from swarm_orchestrator import reasoning_pipeline

from benchmarks.vlm_bench.grounder_offline import item_config, item_frame, probe_inputs
from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.variants import gf_cluster, grounding_first, per_cluster
from reasoning.rag import cluster_options, grounding_provenance, joint_check
from reasoning.vlm import executable_options, per_cluster_choice
from tests.unit.vlm_bench_fixtures import synthetic_items


class _NoGT:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"the adapter read item.gt.{name}")


def _blind(request_id: str) -> BenchItem:
    item = synthetic_items()[request_id]
    return item.model_copy(update={"gt": _NoGT()})


def _dump(model) -> dict[str, Any]:
    return model.model_dump(mode="json")


def test_shared_generator_on_plain_inputs_equals_bench_adapter():
    for request_id in ("aaaa0001", "aaaa0002"):
        item = synthetic_items()[request_id]
        blind = _blind(request_id)
        shared = cluster_options.generate_cluster_candidates(
            item_frame(blind),
            blind.item_id,
            gf_cluster.grouping_params(blind),
            partial(cluster_options.ground_probe, probe_inputs(blind)),
            True,
            "keep",
            "keep",
        )
        bench = gf_cluster.generate_cluster_candidates(item, True, "keep", "keep")
        assert _dump(shared) == _dump(bench)


def test_shared_slots_equal_bench_per_cluster_candidates():
    item = synthetic_items()["aaaa0002"]
    base = gf_cluster.generate_cluster_candidates(item, True, "drop", "drop")
    for option_ids, seed in (("numbered", None), ("opaque", 3)):
        shared = per_cluster_choice.build_slots(base, option_ids, seed)
        bench = per_cluster.per_cluster_candidates(item, True, option_ids, seed)
        assert _dump(shared[0]) == _dump(bench[0])
        assert shared[1:] == bench[1:]


def test_shared_joint_check_equals_bench_adapter():
    item = synthetic_items()["aaaa0002"]
    candidates, _, _ = per_cluster.per_cluster_candidates(item)
    chosen = {s.label: s.options[0] if s.options else None for s in candidates.slots}
    shared = joint_check.joint_check(
        item_frame(item),
        chosen,
        partial(cluster_options.ground_probe, probe_inputs(item)),
        item_config(item).scenario_geometry,
    )
    assert shared == per_cluster.joint_check(item, chosen)


def test_orchestrator_reexports_are_the_shared_helpers():
    assert reasoning_pipeline.summarize_yield_grounding is (
        grounding_provenance.summarize_yield_grounding
    )
    assert reasoning_pipeline.empty_reroute_fallback is grounding_provenance.empty_reroute_fallback
    assert reasoning_pipeline.YieldGroundingProvenance is (
        grounding_provenance.YieldGroundingProvenance
    )


def test_bench_reexports_are_the_shared_objects():
    assert gf_cluster.ClusterOption is executable_options.ClusterOption
    assert gf_cluster.ClusterCandidateSet is executable_options.ClusterCandidateSet
    assert gf_cluster.GroupingParams is cluster_options.GroupingParams
    assert gf_cluster.executed_key_v2 is cluster_options.executed_key_v2
    assert grounding_first.executed_key is cluster_options.executed_key
    assert grounding_first.CandidateSet is executable_options.CandidateSet
    assert grounding_first.extract_json_object is per_cluster_choice.extract_json_object
    assert per_cluster.choices_model is per_cluster_choice.choices_model
    assert per_cluster.parse_per_cluster_answer is per_cluster_choice.parse_per_cluster_answer
    assert per_cluster.JointCheck is joint_check.JointCheck

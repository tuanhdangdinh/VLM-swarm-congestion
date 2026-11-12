"""Live-vs-bench parity of the per-cluster shadow's inputs on recorded items.

The live side never sees a `BenchItem`: the recorded episode's M5 config
builds an `InProcessPipeline` exactly as the node does (geometry, static
obstacles, yield mode, grounding params, registry priorities, registry
lookups), the request is rebuilt through the production builder
(`run.rebuild_request`), and `InProcessPipeline.per_cluster_probe_inputs`
yields the probe inputs. They must equal the bench adapter
`grounder_offline.probe_inputs(item)`, and the candidate set and joint check
built from them must equal the bench's.

Synthetic items always run; the recorded 187-item file
(`data/bench/v4/items_live31.jsonl`, gitignored) runs on a fixed sample when
present. The full 187 run is `scripts/per_cluster_shadow_offline.py`.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

import pytest
from swarm_orchestrator.models import registry_priorities
from swarm_orchestrator.reasoning_pipeline import InProcessPipeline

from benchmarks.vlm_bench.grounder_offline import item_config, probe_inputs
from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.run import load, rebuild_request
from benchmarks.vlm_bench.variants import gf_cluster, per_cluster
from reasoning.rag import cluster_options
from reasoning.rag.cluster_options import ProbeInputs
from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.joint_check import joint_check
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_shield import RobotTaskIntent
from reasoning.vlm.per_cluster_choice import build_slots
from tests.unit.vlm_bench_fixtures import synthetic_items

ITEMS = Path("data/bench/v4/items_live31.jsonl")
REAL_SAMPLE_STRIDE = 16


def live_pipeline(item: BenchItem) -> InProcessPipeline:
    """The pipeline the node builds for the item's episode (no reasoner needed).

    Args:
        item: A recorded item (its overlay, params and registry state).

    Returns:
        The pipeline, with registry lookups answering the recorded state.
    """
    config = item_config(item)
    params = (
        GroundingParams(**item.grounding.params) if item.grounding.params is not None else None
    )
    goals = dict(item.grounding.goal_references)
    intents = {
        rid: RobotTaskIntent(**intent.model_dump())
        for rid, intent in item.grounding.task_intents.items()
    }
    return InProcessPipeline(
        reasoner=None,
        ground_fn=ground_reasoner_result,
        scene_geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        grounding_params=params,
        priorities=registry_priorities(config.initial_tasks),
        goal_reference_of=goals.get,
        task_intent_of=intents.get,
    )


def live_inputs(item: BenchItem, image_path: str = "frame.png") -> ProbeInputs:
    """The shadow's probe inputs for the item, built only from live objects.

    Args:
        item: A recorded item.
        image_path: Image the rebuilt request names (never read here).

    Returns:
        `InProcessPipeline.per_cluster_probe_inputs` on the rebuilt request.
    """
    request = rebuild_request(item, image_path)
    inputs, _ = live_pipeline(item).per_cluster_probe_inputs(request, "bench")
    return inputs


def parity_mismatches(item: BenchItem) -> list[str]:
    """Where the live constructor's inputs, candidates or joint check differ from the bench.

    Args:
        item: A recorded item.

    Returns:
        The names of the differing parts (empty on parity).
    """
    live = live_inputs(item)
    bench = probe_inputs(item)
    out: list[str] = []
    if live.model_dump(mode="json") != bench.model_dump(mode="json"):
        out.append("probe_inputs")
    grouping = gf_cluster.grouping_params(item)
    live_base = cluster_options.generate_cluster_candidates(
        live.snapshot, item.item_id, grouping, partial(cluster_options.ground_probe, live),
        True, "drop", "drop",
    )
    live_slots, _, _ = build_slots(live_base)
    bench_slots, _, _ = per_cluster.per_cluster_candidates(item)
    if live_slots.model_dump(mode="json") != bench_slots.model_dump(mode="json"):
        out.append("candidates")
    chosen = {s.label: s.options[0] if s.options else None for s in bench_slots.slots}
    live_check = joint_check(
        live.snapshot, chosen, partial(cluster_options.ground_probe, live), live.geometry
    )
    if live_check != per_cluster.joint_check(item, chosen):
        out.append("joint_check")
    return out


def _real_sample() -> list[Any]:
    if not ITEMS.is_file():
        return []
    items = load(ITEMS)
    return items[::REAL_SAMPLE_STRIDE]


@pytest.mark.parametrize("request_id", sorted(synthetic_items()))
def test_live_constructor_matches_bench_on_synthetic_items(request_id):
    assert parity_mismatches(synthetic_items()[request_id]) == []


@pytest.mark.skipif(not ITEMS.is_file(), reason="recorded bench items are gitignored")
@pytest.mark.parametrize("index", range(len(_real_sample())))
def test_live_constructor_matches_bench_on_recorded_items(index):
    item = _real_sample()[index]
    assert parity_mismatches(item) == [], item.item_id


def test_live_inputs_read_the_registry_through_the_pipeline_lookups():
    item = synthetic_items()["aaaa0002"]
    pipeline = live_pipeline(item)
    request = rebuild_request(item, "frame.png")
    inputs, source = pipeline.per_cluster_probe_inputs(request, "bench")
    assert source == "recomputed"
    assert inputs.snapshot.robots == list(request.robot_states)


@pytest.mark.skipif(not ITEMS.is_file(), reason="recorded bench items are gitignored")
def test_node_grouping_radius_equals_every_recorded_item():
    from swarm_orchestrator.shadow_classical import load_shadow_params

    live = load_shadow_params(Path("config/rag.yaml")).params.r_conflict_m
    assert {gf_cluster.grouping_params(item).threshold_m for item in load(ITEMS)} == {live}

"""v4 offline VLM bench (spec `docs/specs/v4_vlm_bench.md`; exploratory, never v3 confirmatory).

CLI: `python -m benchmarks.vlm_bench build-items|score|replay ...`.
"""

from benchmarks.vlm_bench.backends import CachedBackend, RecordedBackend, cache_key
from benchmarks.vlm_bench.classical_ref import classical_decision, reproduces_recorded
from benchmarks.vlm_bench.grounder_offline import (
    executable_yielders,
    ground_decision,
    refusal_class,
)
from benchmarks.vlm_bench.items import (
    build_bundle_items,
    load_mc_references,
    read_items,
    task_stream_state,
    write_items,
)
from benchmarks.vlm_bench.models import BenchItem, GroundingOutcome, GTCluster, ItemScore
from benchmarks.vlm_bench.run import (
    PROMPT_VARIANTS,
    rebuild_request,
    replay_items,
    score_items,
    write_run,
)
from benchmarks.vlm_bench.scoring import (
    Summary,
    cluster_recalls,
    coverage,
    score_item,
    summarize,
    yielder_agrees,
)

__all__ = [
    "PROMPT_VARIANTS",
    "BenchItem",
    "CachedBackend",
    "GTCluster",
    "GroundingOutcome",
    "ItemScore",
    "RecordedBackend",
    "Summary",
    "build_bundle_items",
    "cache_key",
    "classical_decision",
    "cluster_recalls",
    "coverage",
    "executable_yielders",
    "ground_decision",
    "load_mc_references",
    "read_items",
    "rebuild_request",
    "refusal_class",
    "replay_items",
    "reproduces_recorded",
    "score_item",
    "score_items",
    "summarize",
    "task_stream_state",
    "write_items",
    "write_run",
    "yielder_agrees",
]

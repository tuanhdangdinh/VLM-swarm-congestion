"""Offline check of the v4 per-cluster live shadow on recorded bench items (zero network).

For every item: the live-vs-bench parity of the shadow's inputs, candidate
set and joint check (`tests/unit/test_m5_per_cluster_live_parity.py`'s
`parity_mismatches`), then one full `compute_per_cluster_shadow` on the live
constructor's inputs with the zero-network first-option chooser, which
times enumeration and grounding as the live worker would run them (the M2
call itself is ~0 ms here). Prints a JSON summary: mismatches, the timing
distribution, and per-bundle counts of analyses with two or more slots.

Usage (from the repo root, PYTHONPATH as for the unit tests):
    python scripts/per_cluster_shadow_offline.py data/bench/v4/items_live31.jsonl OUT.jsonl
"""

from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image
from swarm_orchestrator.per_cluster_shadow import compute_per_cluster_shadow

from benchmarks.vlm_bench.run import load, rebuild_request
from benchmarks.vlm_bench.variants import gf_cluster
from reasoning.vlm.models import ReasonerConfig
from reasoning.vlm.per_cluster_runner import FixedGroupChoiceBackend
from tests.unit.test_m5_per_cluster_live_parity import live_pipeline, parity_mismatches


def _quantiles(values: list[int]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}

    def q(p: float) -> float:
        return float(ordered[min(len(ordered) - 1, int(round(p * (len(ordered) - 1))))])

    return {
        "n": len(ordered),
        "min": float(ordered[0]),
        "p50": q(0.5),
        "p90": q(0.9),
        "p95": q(0.95),
        "max": float(ordered[-1]),
        "mean": round(statistics.fmean(ordered), 1),
    }


def main(items_path: str, out_path: str) -> int:
    """Run the check and write one JSONL row per item.

    Args:
        items_path: Bench items JSONL.
        out_path: Per-item rows.

    Returns:
        Exit code (1 when any parity mismatch was found).
    """
    items = load(Path(items_path))
    rows = []
    config = ReasonerConfig(backend_id="fixed-group-choice", max_attempts=1)
    with tempfile.TemporaryDirectory() as scratch:
        frame = Path(scratch) / "frame.png"
        Image.new("RGB", (64, 48)).save(frame)
        for item in items:
            mismatches = parity_mismatches(item)
            request = rebuild_request(item, str(frame))
            start = time.monotonic()
            inputs, source = live_pipeline(item).per_cluster_probe_inputs(request, "offline")
            record = compute_per_cluster_shadow(
                request,
                inputs,
                gf_cluster.grouping_params(item),
                FixedGroupChoiceBackend("first"),
                config,
                lookups_source=source,
            )
            wall_ms = int((time.monotonic() - start) * 1000)
            rows.append(
                {
                    "item_id": item.item_id,
                    "bundle": Path(item.bundle).name,
                    "mismatches": mismatches,
                    "dynamic_goal_refs": len(inputs.goal_references),
                    "task_intents": len(inputs.task_intents),
                    "status": record.status,
                    "n_slots": record.n_slots,
                    "n_options": record.n_options,
                    "joint_exact_conflict": record.joint_exact_conflict,
                    "joint_path_proximity": (
                        None
                        if record.joint_check is None
                        else bool(record.joint_check["path_proximity"])
                    ),
                    "timings": record.timings.model_dump(),
                    "wall_ms": wall_ms,
                }
            )
    Path(out_path).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    per_bundle: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        per_bundle[row["bundle"]]["analyses"] += 1
        per_bundle[row["bundle"]]["two_plus_slots"] += int(row["n_slots"] >= 2)
    summary = {
        "n_items": len(rows),
        "parity_mismatch_items": [r["item_id"] for r in rows if r["mismatches"]],
        "mismatch_kinds": Counter(k for r in rows for k in r["mismatches"]),
        "items_with_goal_refs": sum(1 for r in rows if r["dynamic_goal_refs"]),
        "items_with_task_intents": sum(1 for r in rows if r["task_intents"]),
        "status": Counter(r["status"] for r in rows),
        "slots": Counter(r["n_slots"] for r in rows),
        "exact_conflict_on_two_plus": sum(
            1 for r in rows if r["n_slots"] >= 2 and r["joint_exact_conflict"]
        ),
        "path_proximity_on_two_plus": sum(
            1 for r in rows if r["n_slots"] >= 2 and r["joint_path_proximity"]
        ),
        "enumeration_ms": _quantiles([r["timings"]["enumeration_ms"] for r in rows]),
        "grounding_ms": _quantiles(
            [r["timings"]["grounding_ms"] for r in rows if r["timings"]["grounding_ms"] is not None]
        ),
        "total_ms": _quantiles([r["timings"]["total_ms"] for r in rows]),
        "wall_ms_incl_inputs": _quantiles([r["wall_ms"] for r in rows]),
        "per_bundle": {b: dict(c) for b, c in sorted(per_bundle.items())},
    }
    print(json.dumps(summary, indent=1, sort_keys=True, default=dict))
    return 1 if summary["parity_mismatch_items"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

"""Shared paths and helpers for the VLM bench tests (synthetic mini-bundle)."""

from __future__ import annotations

from pathlib import Path

from benchmarks.vlm_bench.items import build_bundle_items, load_mc_references
from benchmarks.vlm_bench.models import BenchItem

DATA = Path(__file__).parent / "data" / "vlm_bench"
BUNDLE = DATA / "s1b_E90_seed90_synth_a1"
MC_FILE = DATA / "mc_seeds_synth.jsonl"


def synthetic_items(bundle: Path = BUNDLE) -> dict[str, BenchItem]:
    """Build the synthetic bundle's items, keyed by request id.

    Args:
        bundle: The bundle to build (defaults to the committed fixture).

    Returns:
        Request id -> item.
    """
    items = build_bundle_items(bundle, load_mc_references([MC_FILE]))
    return {item.request_id: item for item in items}

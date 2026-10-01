"""Deterministic, balanced item sampling, independent of filesystem scanning.

Pure functions over already-scored candidates (a candidate already carries
its GT-derived answer; building candidates from `data/logs/vm_runs` is
`scripts/build_capability_probe_manifest.py`'s job, not this module's), so
item selection is unit-testable without real run logs.
"""
from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")


def balanced_sample(
    candidates: Sequence[T],
    balance_key: Callable[[T], str],
    scene_key: Callable[[T], str],
    target: int,
    seed: int,
    max_per_scene: int,
) -> list[T]:
    """Deterministically sample up to `target` items, balanced and scene-capped.

    Candidates are grouped by `balance_key` (e.g. the correct answer, so one
    answer value cannot dominate the item set) and drawn round-robin across
    groups, group order and within-group order both seeded, while capping how
    many items any one `scene_key` (e.g. the source VM-run id) contributes, so
    one long run cannot supply most of a probe type's items.

    Args:
        candidates: Already GT-scored candidate items for one probe type.
        balance_key: Grouping key balanced across (e.g. `lambda c: c.correct_answer`).
        scene_key: Source-scene key capped per item (e.g. `lambda c: c.run_id`).
        target: Maximum number of items to select.
        seed: Selection seed; the same `candidates` list and `seed` always
            produce the same selection, independent of scan order within a
            group (groups are internally shuffled) but not independent of the
            groups' own membership.
        max_per_scene: Maximum items any one `scene_key` value may contribute.

    Returns:
        The selected items, in selection order (round-robin across groups);
        fewer than `target` when the candidate pool is exhausted.
    """
    rng = random.Random(seed)
    groups: dict[str, list[T]] = {}
    for candidate in candidates:
        groups.setdefault(balance_key(candidate), []).append(candidate)
    for group in groups.values():
        rng.shuffle(group)
    group_keys = sorted(groups)
    rng.shuffle(group_keys)

    cursors = {key: 0 for key in group_keys}
    scene_counts: dict[str, int] = {}
    selected: list[T] = []
    progressed = True
    while len(selected) < target and progressed:
        progressed = False
        for key in group_keys:
            if len(selected) >= target:
                break
            items = groups[key]
            while cursors[key] < len(items):
                candidate = items[cursors[key]]
                cursors[key] += 1
                scene = scene_key(candidate)
                if scene_counts.get(scene, 0) >= max_per_scene:
                    continue
                selected.append(candidate)
                scene_counts[scene] = scene_counts.get(scene, 0) + 1
                progressed = True
                break
    return selected

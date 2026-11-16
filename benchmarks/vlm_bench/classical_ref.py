"""Classical reference: the M5 shadow's chooser (`resolve_classical`) re-run on bench items.

The shadow's ring buffer is rebuilt from `m5_scene.jsonl` at item-build time
(`items._history_frames`); the thresholds are the ones the live shadow
recorded, the zones come from the episode overlay, and `prior_attempts` is the
recorded value (it is an input to the policy, not an output).
"""

from __future__ import annotations

from typing import Any

from benchmarks.vlm_bench.grounder_offline import item_config
from benchmarks.vlm_bench.models import BenchItem
from reasoning.baselines import ClassicalParams, resolve_classical
from reasoning.vlm.models import RobotStateInput, SnapshotFrame


def item_history(item: BenchItem) -> list[SnapshotFrame]:
    """The item's classical history window as `SnapshotFrame`s, oldest first.

    Args:
        item: The bench item.

    Returns:
        The frames.
    """
    frames = []
    for raw in item.classical.frames:
        robots = [
            RobotStateInput(
                robot_id=r["robot_id"],
                x=r["x"],
                y=r["y"],
                theta=r["theta"],
                linear_velocity=r.get("linear_velocity"),
                status=r.get("status"),
                goal=None if r.get("goal") is None else tuple(r["goal"]),
            )
            for r in raw["robots"]
        ]
        frames.append(
            SnapshotFrame(
                stamp=raw["stamp"], robots=robots, held_robot_ids=tuple(raw["held_robot_ids"])
            )
        )
    return frames


def classical_decision(item: BenchItem) -> dict[str, Any] | None:
    """Run the classical chooser on one item.

    Args:
        item: The bench item.

    Returns:
        The classical decision as a dict, or None when the item carries no
        recorded params or no frames (the live shadow then recorded an error).
    """
    if item.classical.params is None or not item.classical.frames:
        return None
    params = ClassicalParams(**item.classical.params)
    zones = item_config(item).shadow_classical_zones
    resolution = resolve_classical(
        item_history(item), zones, params, item.classical.prior_attempts
    )
    return resolution.decision.model_dump(mode="json")


def reproduces_recorded(item: BenchItem, decision: dict[str, Any] | None) -> bool | None:
    """Whether a re-run matches the live shadow on (detected, strategy, yielder, involved).

    Args:
        item: The bench item.
        decision: The re-run classical decision.

    Returns:
        None when either side is missing; else the match flag.
    """
    recorded = item.classical.recorded_decision
    if recorded is None or decision is None:
        return None
    keys = ("congestion_detected", "strategy", "yield_robot")
    same = all(recorded.get(k) == decision.get(k) for k in keys)
    return same and set(recorded.get("involved_robots") or ()) == set(
        decision.get("involved_robots") or ()
    )

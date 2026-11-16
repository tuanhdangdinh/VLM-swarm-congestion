"""Offline M3: the real `ground_reasoner_result` on a bench item, no network.

Inputs are exactly what the live `InProcessPipeline` passed, rebuilt from the
item: the episode overlay (geometry, static obstacles, feasibility mode,
registry priorities), the grounding params the artifact recorded, and goal
references / task intents rebuilt from the task stream. Stage 2 is not run
(`retreat_choice=None`): a refusal is decided before stage 2, so feasibility
does not depend on it.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from swarm_orchestrator.models import OrchestratorConfig, load_config, registry_priorities
from swarm_orchestrator.reasoning_pipeline import empty_reroute_fallback, summarize_yield_grounding

from benchmarks.vlm_bench.models import BenchItem, GroundingOutcome
from reasoning.rag.cluster_options import ProbeInputs, ground_probe
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_shield import RobotTaskIntent
from reasoning.vlm.models import RobotStateInput, SnapshotFrame

_CLASS_RE = re.compile(r"yield refused:\s*([^:;(]+)")


def refusal_class(reason: str | None) -> str | None:
    """Coarse refusal class: the text after `yield refused:` up to the next `:`.

    Args:
        reason: A refusal reason or a yield-degradation tag.

    Returns:
        E.g. "no shared lane", "ambiguous lane"; the tag before `:` for a
        reroute fallback; None for None.
    """
    if reason is None:
        return None
    match = _CLASS_RE.match(reason)
    if match:
        return match.group(1).strip()
    return reason.split(":", 1)[0].strip()


@lru_cache(maxsize=64)
def _config(overlay_key: str, overlay_json: str) -> OrchestratorConfig:
    import json

    return load_config(json.loads(overlay_json))


def item_config(item: BenchItem) -> OrchestratorConfig:
    """The episode's M5 config, parsed from the item's overlay (cached).

    Args:
        item: The bench item.

    Returns:
        The validated orchestrator config.
    """
    import json

    blob = json.dumps(item.grounding.overlay, sort_keys=True)
    return _config(item.bundle, blob)


def item_frame(item: BenchItem) -> SnapshotFrame:
    """The analysed scene as the grounder sees it (`snapshot_frame_from_request`).

    Args:
        item: The bench item.

    Returns:
        The frame, robots in stored order with registry goals and tasks.
    """
    robots = [
        RobotStateInput(
            robot_id=r["robot_id"],
            x=r["x"],
            y=r["y"],
            theta=r["theta"],
            linear_velocity=r.get("linear_velocity", 0.0),
            status=r.get("status"),
            task=r.get("task"),
            goal=None if r.get("goal") is None else tuple(r["goal"]),
        )
        for r in item.scene["robots"]
    ]
    return SnapshotFrame(stamp=item.stamp, robots=robots)


def probe_inputs(item: BenchItem) -> ProbeInputs:
    """The shared probe inputs of one item: what the live pipeline passed to M3.

    Reads the scene, the overlay, the recorded grounding params, goal
    references and task intents; never `item.gt`. Task intents are converted
    only when the params pass them on (dynamic scene arms with the retreat
    shield), as before the move.

    Args:
        item: The bench item.

    Returns:
        The inputs `reasoning.rag.cluster_options.ground_probe` takes.
    """
    config = item_config(item)
    params = (
        GroundingParams(**item.grounding.params) if item.grounding.params is not None else None
    )
    frame = item_frame(item)
    dynamic = params is not None and params.dynamic_scene_arms
    return ProbeInputs(
        request_id=item.request_id,
        backend_id="bench",
        snapshot=frame,
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        params=params,
        priorities=registry_priorities(config.initial_tasks),
        goal_references=dict(item.grounding.goal_references) if dynamic else {},
        task_intents=(
            {
                rid: RobotTaskIntent(**intent.model_dump())
                for rid, intent in item.grounding.task_intents.items()
            }
            if dynamic and params.retreat_shield
            else {}
        ),
    )


def ground_command(item: BenchItem, decision: dict[str, Any]) -> dict[str, Any]:
    """The grounded M3 command of one positive decision on the item's scene.

    Args:
        item: The bench item.
        decision: A positive decision dict (`CongestionDecision` fields).

    Returns:
        The command `ground_reasoner_result` returns, stage 2 not run
        (`reasoning.rag.cluster_options.ground_probe` on `probe_inputs(item)`).

    Raises:
        Exception: Whatever the grounder raises; callers record it like the
            live `GROUNDING` terminal stage.
    """
    return ground_probe(probe_inputs(item), decision)


def outcome_of(command: dict[str, Any]) -> GroundingOutcome:
    """The bench's feasibility reading of one grounded command.

    Args:
        command: A grounded command.

    Returns:
        Infeasible when the yield gate refused or the yield degraded to an
        empty-waypoint reroute; feasible otherwise.
    """
    provenance = summarize_yield_grounding(command)
    reason = provenance.refusal_reason or empty_reroute_fallback(command)
    return GroundingOutcome(
        feasible=reason is None,
        refusal_reason=reason,
        refusal_class=refusal_class(reason),
        grounded_yielder=provenance.grounded_to,
        action_kinds=tuple(a.get("action") for a in command.get("actions") or []),
    )


def ground_decision(item: BenchItem, decision: dict[str, Any] | None) -> GroundingOutcome | None:
    """Ground one decision on the item's scene with the episode's M3 inputs.

    Args:
        item: The bench item.
        decision: A decision dict (`CongestionDecision` fields).

    Returns:
        None for a missing or negative decision; else the outcome. Grounding
        exceptions are recorded as infeasible with `error` set, as the live
        pipeline records a `GROUNDING` terminal stage.
    """
    if not decision or not decision.get("congestion_detected"):
        return None
    try:
        command = ground_command(item, decision)
    except Exception as exc:  # recorded like the live GROUNDING terminal stage
        return GroundingOutcome(feasible=False, error=f"{type(exc).__name__}: {exc}")
    return outcome_of(command)


def executable_yielders(item: BenchItem, decision: dict[str, Any]) -> tuple[str, ...]:
    """The geometry oracle: involved robots M3 grounds as the yielder unchanged.

    For each robot y in the decision's involved set, the decision is grounded
    with `strategy="yield"` and `yield_robot=y`; y is executable when the
    grounder neither refuses nor swaps it (the grounded `yield` action's robot
    is y). This is the S1 MC's resolvability rule
    (`scripts/s1_grounding_replay.py`).

    Args:
        item: The bench item.
        decision: The decision whose involved set is probed.

    Returns:
        The executable yielders, in involved-set order.
    """
    out: list[str] = []
    for robot_id in decision.get("involved_robots") or ():
        probe = {
            k: v for k, v in decision.items() if k not in ("crossing_order", "proposed_plan")
        }
        probe.update(strategy="yield", yield_robot=robot_id)
        outcome = ground_decision(item, probe)
        if outcome is not None and outcome.feasible and outcome.grounded_yielder == robot_id:
            out.append(robot_id)
    return tuple(out)

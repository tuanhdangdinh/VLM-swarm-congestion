"""Offline v4 refusal feedback: rebuild a recorded episode's prompts with both keys on.

Change 1 (`prompt_offer_groundable_strategies`) needs only the item's own
geometry and params. Change 2 (`refusal_feedback`) is sequential: what a
prompt states depends on the episode's earlier outcomes. This module replays
them in order through the production pieces M5 uses live
(`WithheldMemory`, `refusal_feedback_reason`, `PlanTracker.shown_plan`), from the
bundle's decision artifacts and its M5 log (wall times and trigger robot sets
of `starting analysis` / `decision artifact written` lines).

What is reconstructed rather than recorded: the plan-state block. The live
tracker's leg statuses come from M4 status messages, which are not in the
artifacts; a plan's statuses are taken from the latest recorded prompt that
showed that same plan (else all `pending`), and `plan_state_source` says which.
The model's answers are the recorded ones throughout: the episode is NOT
re-simulated, so every later scene is the scene that followed the live
(feedback-off) answers.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from swarm_orchestrator.command_lifecycle import WithheldMemory
from swarm_orchestrator.plan_tracker import PlanTracker
from swarm_orchestrator.reasoning_pipeline import refusal_feedback_reason

from benchmarks.vlm_bench.grounder_offline import item_config
from benchmarks.vlm_bench.models import BenchItem
from reasoning.rag.command_grounder import VerifiedPlan, groundable_strategies
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.plan_metrics import compute_plan_churn
from reasoning.vlm.models import (
    PlanStateContext,
    PlanStateLeg,
    ProposedPlanLeg,
    ReasonerRequest,
    RefusedProposal,
)

_LOG_TS = r"\[(\d+\.\d+)\]"
_START_RE = re.compile(_LOG_TS + r".*starting analysis request=([0-9a-f]+) robots=(\[[^\]]*\])")
_WRITTEN_RE = re.compile(_LOG_TS + r".*decision artifact written: .*?([0-9a-f]{32})\.json")
PlanStateSource = Literal["none", "recorded", "reconstructed", "acceptance"]


@dataclass(frozen=True)
class FeedbackState:
    """What one analysis's prompt states under `refusal_feedback`."""

    refused_proposals: tuple[RefusedProposal, ...]
    plan_state: PlanStateContext | None
    plan_state_source: PlanStateSource
    # The live prompt's plan was a plan M5 never dispatched (the Change 2 defect).
    live_plan_was_withheld: bool


@dataclass
class _LogTimes:
    start: dict[str, tuple[float, list[str]]] = field(default_factory=dict)
    written: dict[str, float] = field(default_factory=dict)


def read_m5_log(bundle: Path) -> _LogTimes:
    """Wall times and trigger robots of every analysis in a bundle's `m5.log`.

    Args:
        bundle: The episode bundle.

    Returns:
        Per request id: `(start wall time, trigger robots)` and the artifact
        write wall time. Empty when the log is absent.
    """
    times = _LogTimes()
    path = Path(bundle) / "m5.log"
    if not path.is_file():
        return times
    for line in path.read_text(errors="replace").splitlines():
        if (match := _START_RE.search(line)) is not None:
            times.start[match.group(2)] = (float(match.group(1)), ast.literal_eval(match.group(3)))
        elif (match := _WRITTEN_RE.search(line)) is not None:
            times.written[match.group(2)] = float(match.group(1))
    return times


def _artifacts(bundle: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((Path(bundle) / "decisions").glob("*.json")):
        data = json.loads(path.read_text())
        if isinstance(data, dict) and "request_id" in data and "scene" in data:
            out.append(data)
    return out


def _dispatched(artifact: dict[str, Any]) -> bool:
    return bool(artifact.get("dispatched_command")) and not artifact.get("dispatch_withheld")


def _plan_context(
    tracker: PlanTracker,
    live_of: dict[int, int],
    statuses: dict[int, dict[str, str]],
    last_shown: int | None,
) -> tuple[PlanStateContext | None, PlanStateSource, int | None]:
    active = tracker.shown_plan()
    if active is None:
        return None, "none", last_shown
    live_id = live_of[active.plan_id]
    known = statuses.get(live_id)
    legs = [
        PlanStateLeg(
            robot_id=leg.robot_id, action=leg.action,
            status=(known or {}).get(leg.robot_id, "pending"),  # type: ignore[arg-type]
        )
        for leg in active.legs
    ]
    changed: tuple[str, ...] = ()
    if last_shown is not None and last_shown != active.plan_id:
        previous = tracker.plan(last_shown)
        if previous is not None:
            changed = tuple(
                compute_plan_churn(
                    previous.as_proposed_plan(), active.as_proposed_plan()
                ).changed_robot_ids
            )
    context = PlanStateContext(plan_id=live_id, legs=legs, changed_robot_ids=changed)
    return context, ("reconstructed" if known is not None else "acceptance"), active.plan_id


def episode_feedback_states(
    bundle: Path, window_sec: float = 300.0, max_entries: int = 3
) -> dict[str, FeedbackState]:
    """Replay one episode's outcomes through M5's refusal-feedback pieces, in order.

    Args:
        bundle: The episode bundle (decision artifacts plus `m5.log`).
        window_sec: `refusal_feedback.window_sec` (wall seconds, as live).
        max_entries: `refusal_feedback.max_entries`.

    Returns:
        Per request id, the proposals and plan state its prompt would carry.
        The plan-state `plan_id` is the live id of the plan shown.
    """
    times = read_m5_log(bundle)
    artifacts = sorted(_artifacts(bundle), key=lambda a: a["scene"]["stamp"])
    memory = WithheldMemory(window_sec, max_entries)
    tracker = PlanTracker()
    live_of: dict[int, int] = {}
    statuses: dict[int, dict[str, str]] = {}
    withheld_live_ids: set[int] = set()
    last_shown: int | None = None
    out: dict[str, FeedbackState] = {}
    for art in artifacts:
        rid = art["request_id"]
        start, robots = times.start.get(rid, (art["scene"]["stamp"], None))
        if robots is None:
            robots = list((art.get("decision") or {}).get("involved_robots") or [])
        recorded = art.get("plan_state")
        if recorded is not None:
            statuses[recorded["plan_id"]] = {
                leg["robot_id"]: leg["status"] for leg in recorded["legs"]
            }
        context, source, last_shown = _plan_context(tracker, live_of, statuses, last_shown)
        if context is not None and recorded is not None and recorded["plan_id"] == context.plan_id:
            source = "recorded"
        out[rid] = FeedbackState(
            refused_proposals=tuple(memory.proposals_for(robots, start)),
            plan_state=context,
            plan_state_source=source,
            live_plan_was_withheld=(
                recorded is not None and recorded["plan_id"] in withheld_live_ids
            ),
        )
        end = times.written.get(rid, start)
        plan = art.get("plan")
        if plan is not None:
            verified = VerifiedPlan(
                legs=[ProposedPlanLeg(robot_id=leg["robot_id"], action=leg["action"])
                      for leg in plan["legs"]],
                provenance=plan["provenance"],
                edits=[],
            )
            acceptance = tracker.accept_plan(verified)
            if not acceptance.held:
                live_of[acceptance.plan.plan_id] = plan["plan_id"]
                if not _dispatched(art):
                    tracker.mark_withheld(acceptance.plan.plan_id)
            if not _dispatched(art) and not plan.get("plan_held"):
                withheld_live_ids.add(plan["plan_id"])
        withheld = art.get("dispatch_withheld")
        decision = art.get("decision") or {}
        if withheld and decision.get("involved_robots"):
            proposal = RefusedProposal(
                strategy=decision["strategy"],
                involved_robots=tuple(decision["involved_robots"]),
                yield_robot=decision.get("yield_robot"),
                reason=refusal_feedback_reason(withheld, art.get("grounding_degradations") or []),
            )
            robots_of = set(decision["involved_robots"])
            robots_of |= set(withheld.get("would_dispatch_robot_ids", []))
            memory.record(proposal, robots_of, end)
        elif _dispatched(art):
            memory.forget_overlapping(art.get("dispatched_robot_ids") or [])
    return out


def offered_for(item: BenchItem) -> tuple[str, ...]:
    """The strategy set Change 1 offers on the item's scene (its live geometry and params).

    Args:
        item: The bench item.

    Returns:
        `command_grounder.groundable_strategies` for it.
    """
    return groundable_strategies(
        item_config(item).scenario_geometry, GroundingParams(**item.grounding.params)
    )


def feedback_request(
    request: ReasonerRequest,
    item: BenchItem,
    state: FeedbackState | None,
    *,
    offer: bool = True,
) -> ReasonerRequest:
    """The item's live request with Change 1 and (given a state) Change 2 applied.

    Args:
        request: The live request, rebuilt by `run.rebuild_request`.
        item: The bench item.
        state: The item's `episode_feedback_states` entry; None leaves the
            plan state and proposals as recorded (Change 1 only).
        offer: Apply Change 1.

    Returns:
        A new request; every other field is the live one.
    """
    update: dict[str, Any] = {}
    if offer:
        update["offered_strategies"] = offered_for(item)
    if state is not None:
        update["plan_state"] = state.plan_state
        update["refused_proposals"] = list(state.refused_proposals) or None
    return ReasonerRequest.model_validate({**request.model_dump(), **update})


_STATE_CACHE: dict[tuple[str, float, int], dict[str, FeedbackState]] = {}


def cached_episode_states(
    bundle: str, window_sec: float = 300.0, max_entries: int = 3
) -> dict[str, FeedbackState]:
    """`episode_feedback_states`, computed once per bundle and setting.

    Args:
        bundle: The bundle path.
        window_sec: As `episode_feedback_states`.
        max_entries: As `episode_feedback_states`.

    Returns:
        The states by request id.
    """
    key = (bundle, window_sec, max_entries)
    if key not in _STATE_CACHE:
        _STATE_CACHE[key] = episode_feedback_states(Path(bundle), window_sec, max_entries)
    return _STATE_CACHE[key]


def items_by_episode(items: Sequence[BenchItem]) -> dict[str, list[BenchItem]]:
    """Group items by bundle, each in scene-stamp order.

    Args:
        items: Bench items.

    Returns:
        Bundle path -> its items.
    """
    groups: dict[str, list[BenchItem]] = {}
    for item in items:
        groups.setdefault(item.bundle, []).append(item)
    return {bundle: sorted(group, key=lambda i: i.stamp) for bundle, group in groups.items()}

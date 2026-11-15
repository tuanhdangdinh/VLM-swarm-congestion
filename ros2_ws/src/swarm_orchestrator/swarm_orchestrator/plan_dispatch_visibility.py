"""M5's record of plan-versus-dispatch differences, behind `plan_dispatch_mismatch_visibility`.

ROS2-free glue between `orchestrator_node` and the pure comparison in
`reasoning.rag.plan_dispatch_mismatch`: it builds the decision artifact's
`plan_dispatch_mismatch` and `reverse_dispatch` blocks and the log lines M5
emits, and keeps a side ledger of what each dispatch did to each plan leg.

The ledger exists because M5's `PlanTracker` marks a leg from the M4 status
of whatever command its robot ran (`orchestrator_node._apply_plan_leg_status`),
so a `wait` leg whose robot was reversed reads `done`, and a `reverse` leg a
node handoff dropped stays `pending` though it was never sent. Those tracker
statuses feed the prompt-v3 plan-state block and the hold rule
(`plan_tracker._is_hold`), so correcting them would change model input and
plan ids. They are left exactly as they are; the corrected reading lives only
in this ledger, the artifact's `leg_status` record and M5's log.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.plan_dispatch_mismatch import (
    DEFINITION_VERSION,
    LegEffect,
    PlanDispatchMismatch,
    classify_plan_dispatch,
    dispatched_provenance,
    leg_effects,
    reverse_dispatch,
)
from swarm_orchestrator.models import PipelineOutcome


class LegEffectEntry(BaseModel):
    """The latest dispatch's effect on one accepted-plan leg."""

    model_config = ConfigDict(frozen=True)

    effect: LegEffect
    ran: str
    reason: str
    request_id: str = Field(min_length=1)


class LegEffectLedger:
    """Per plan and robot, what the latest dispatch under that plan did to the leg.

    Touched only on the rclpy callback thread (`_handle_outcome`,
    `_on_status`), like the node's other dispatch-side tables.
    """

    def __init__(self) -> None:
        self._entries: dict[int, dict[str, LegEffectEntry]] = {}

    def entry(self, plan_id: int, robot_id: str) -> LegEffectEntry | None:
        """Return the latest effect recorded for one leg, or None."""
        return self._entries.get(plan_id, {}).get(robot_id)

    def commit(self, plan_id: int, entries: Mapping[str, LegEffectEntry]) -> None:
        """Record one dispatch's effects (later dispatches overwrite earlier ones).

        Args:
            plan_id: The plan the dispatch was attached to.
            entries: Per robot, the effect on that robot's leg.
        """
        self._entries.setdefault(plan_id, {}).update(entries)


def effective_leg_status(status: str, entry: LegEffectEntry | None) -> str:
    """The leg status a reader should use, given the tracker's and the ledger's.

    Args:
        status: The tracker's leg status.
        entry: The ledger's latest effect on that leg, or None.

    Returns:
        `overridden` when the leg's robot ran a different action; `not_sent`
        while a leg whose action was never dispatched is still `pending`;
        otherwise the tracker's status.
    """
    if entry is None or entry.effect == "as_planned":
        return status
    if entry.effect == "overridden":
        return "overridden"
    return "not_sent" if status == "pending" else status


class PlanDispatchVisibility(BaseModel):
    """Everything the key adds for one decision: artifact blocks, log lines, ledger update."""

    model_config = ConfigDict(frozen=True)

    mismatch_block: dict[str, Any]
    reverse_block: dict[str, Any] | None = None
    warning_lines: tuple[str, ...] = ()
    info_lines: tuple[str, ...] = ()
    plan_id: int
    ledger_entries: dict[str, LegEffectEntry] = Field(default_factory=dict)


def _known_robot_ids(
    outcome: PipelineOutcome, request_robot_ids: Sequence[str] | None
) -> list[str]:
    if request_robot_ids:
        return list(request_robot_ids)
    ids: dict[str, None] = {}
    for leg in outcome.plan.legs if outcome.plan is not None else ():
        ids[leg.robot_id] = None
    for action in (outcome.grounded_command or {}).get("actions", []):
        ids[action["robot_id"]] = None
    return list(ids)


def build_plan_dispatch_visibility(
    outcome: PipelineOutcome,
    *,
    dispatch_command: Mapping[str, Any] | None,
    dropped_robot_ids: Sequence[str],
    withheld_reason: str | None,
    request_robot_ids: Sequence[str] | None,
    ledger: LegEffectLedger,
) -> PlanDispatchVisibility | None:
    """Compare one plan-channel outcome with what M5 dispatches for it.

    Args:
        outcome: The pipeline outcome (its `plan` must be set).
        dispatch_command: The command M5 fans out after the task-registry
            filter (`RegistryDispatch.command`), or None.
        dropped_robot_ids: Robots that filter removed.
        withheld_reason: `dispatch_withheld.reason` when M5 withholds it.
        request_robot_ids: The request's robot ids (the scene), if known.
        ledger: The node's leg-effect ledger, read (never written) here.

    Returns:
        None when the outcome carries no plan or no decision.
    """
    plan = outcome.plan
    decision = outcome.reasoner_result.decision
    if plan is None or decision is None:
        return None
    strategy = decision.strategy
    known = _known_robot_ids(outcome, request_robot_ids)
    request_id = outcome.request_id
    if outcome.plan_verified_legs is None:
        # Never fall back to `plan.legs`: on a hold they are the active
        # plan's, not the ones `dispatch_matches_plan` was computed on.
        return PlanDispatchVisibility(
            mismatch_block={
                "definition_version": DEFINITION_VERSION,
                "error": "verified legs unavailable",
            },
            plan_id=plan.plan_id,
        )
    phases = (
        None
        if outcome.junction_phases is None
        else [phase.model_dump(mode="json") for phase in outcome.junction_phases.phases]
    )
    mismatch = classify_plan_dispatch(
        strategy,
        outcome.plan_verified_legs,
        dispatch_command,
        known,
        withheld_reason=withheld_reason,
        dropped_robot_ids=dropped_robot_ids,
        junction_phases=phases,
        order_equivalent=plan.order_equivalent,
    )
    effects = leg_effects(plan.legs, mismatch)
    reasons = {item.subject: item.reason for item in mismatch.items}
    entries = {
        robot_id: LegEffectEntry(
            effect=effect,
            ran=ran,
            reason="" if effect == "as_planned" else reasons.get(robot_id, "unattributed"),
            request_id=request_id,
        )
        for robot_id, (effect, ran) in effects.items()
    }
    leg_status = []
    for leg in plan.legs:
        entry = entries.get(leg.robot_id) or ledger.entry(plan.plan_id, leg.robot_id)
        leg_status.append(
            {
                "robot_id": leg.robot_id,
                "action": leg.action,
                "status": leg.status,
                "effective_status": effective_leg_status(leg.status, entry),
                "ran": None if entry is None else entry.ran,
                "reason": None if entry is None or not entry.reason else entry.reason,
                "effect_request_id": None if entry is None else entry.request_id,
            }
        )
    provenance = dispatched_provenance(plan.provenance, mismatch)
    block = {
        "definition_version": DEFINITION_VERSION,
        "strategy": strategy,
        "matches": mismatch.matches,
        "provenance": plan.provenance,
        "provenance_dispatched": provenance,
        "verbatim_dispatched": (
            mismatch.matches if plan.provenance == "vlm_verbatim" else None
        ),
        "kinds": list(mismatch.kinds),
        "robots": list(mismatch.robots),
        "items": [item.model_dump(mode="json") for item in mismatch.items],
        "excluded": [item.model_dump(mode="json") for item in mismatch.excluded],
        "tags": mismatch.tags(),
        "planned": mismatch.planned,
        "dispatched": mismatch.dispatched,
        "withheld": mismatch.withheld,
        "per_robot_equal": mismatch.per_robot_equal,
        "leg_status": leg_status,
    }
    trace = reverse_dispatch(strategy, dispatch_command, withheld_reason=withheld_reason)
    info_lines: list[str] = []
    if trace is not None:
        if trace.status == "executed":
            info_lines.append(
                f"reverse executed request={request_id} "
                f"robots={','.join(trace.reversed_robot_ids)} dispatched=reverse"
            )
        else:
            robots = trace.waiting_robot_ids or tuple(
                a["robot_id"] for a in (dispatch_command or {}).get("actions", [])
            )
            info_lines.append(
                f"reverse refused request={request_id} robots={','.join(robots)} "
                f"dispatched={trace.dispatched} reason={trace.reason}"
            )
    return PlanDispatchVisibility(
        mismatch_block=block,
        reverse_block=None if trace is None else trace.model_dump(mode="json"),
        warning_lines=tuple(_warning_lines(request_id, plan.plan_id, mismatch)),
        info_lines=tuple(info_lines),
        plan_id=plan.plan_id,
        ledger_entries=entries,
    )


def _warning_lines(
    request_id: str, plan_id: int, mismatch: PlanDispatchMismatch
) -> list[str]:
    # `reason` last: it can carry free text with spaces (a substituted wait's
    # refusal sentence), so every key before it stays machine-splittable.
    return [
        f"plan dispatch mismatch request={request_id} strategy={mismatch.strategy} "
        f"robot={item.subject} planned={item.planned} dispatched={item.dispatched} "
        f"kind={item.kind} plan_id={plan_id} reason={item.reason}"
        for item in mismatch.items
    ]


def leg_status_line(
    plan_id: int, robot_id: str, leg_action: str, recorded: str, entry: LegEffectEntry
) -> str | None:
    """The log line for a tracker status that the ledger contradicts, or None.

    Args:
        plan_id: The plan whose leg M5 just marked.
        robot_id: The leg's robot.
        leg_action: The leg's action.
        recorded: The tracker status just written.
        entry: The ledger's latest effect on that leg.

    Returns:
        One `plan leg status` line when the leg's robot ran a different
        action than the leg; None otherwise.
    """
    if entry.effect != "overridden":
        return None
    return (
        f"plan leg status plan_id={plan_id} robot={robot_id} leg={leg_action} "
        f"recorded={recorded} effective=overridden ran={entry.ran} "
        f"request={entry.request_id}"
    )

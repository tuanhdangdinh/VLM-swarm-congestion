"""Pure plan-quality scorer for the (a0) universal `proposed_plan` channel.

Computes the prereg-v2 "Plan-quality metrics" registered for every v2
decision (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, "(a0)
Universal proposed_plan channel"): emission, agreement, edit distance,
provenance, oracle-order agreement (scored PRE-repair), and the building
blocks of the plan-stability metric (churn between two plans, and whether a
revision is incremental or wholesale against a registered fraction).

No ROS2, no backend I/O: every function here is a pure function of a
`CongestionDecision` and the `command_grounder.VerifiedPlan` already computed
for it (or of plain `ProposedPlanLeg` sequences), so it can be re-run offline
over a stored decision artifact as well as live. Replan count and the
evidence-driven/unforced revision cause need M5's per-leg execution-status
tracking, which is the next build-order step; this module only provides their
pure building blocks (`compute_plan_churn`, `classify_revision_cause`),
callable once that state exists.

The verbatim-pilot rulings (2026-10-06, A/C/D) add derived, metrics-only
surfaces: the `repaired_order_only` sub-class, `verbatim_dispatch_matched`,
`strategy_correct` with its stratified table, held-robot exclusion from the
oracle order, and `score_decision_artifact` for re-scoring stored artifacts.
"""

from collections.abc import Collection, Iterable, Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.command_grounder import (
    PlanEdit,
    PlanProvenance,
    PlanRejectionStage,
    VerifiedPlan,
)
from reasoning.vlm.models import CongestionDecision, PlanLegStatus, ProposedPlanLeg

# Whether a replan followed at least one leg execution failure since the last
# invocation (rev 4, "Re-planning as measured behavior").
RevisionCause = Literal["evidence_driven", "unforced"]
# Whether a replan's churn stays below the registered fraction of legs.
RevisionType = Literal["incremental", "wholesale"]


class PlanDecisionMetrics(BaseModel):
    """Per-decision plan-quality metrics ((i)-(v) of the registered set)."""

    model_config = ConfigDict(frozen=True)

    # (i) plan emission rate: a parseable plan was supplied (present, every
    # robot_id known), whether or not it refines the strategy. Split from
    # `consistent` on 2026-10-03 so "the model proposed nothing" and "the
    # model proposed a plan that breaks the consistency rule" stop reading
    # as the same score; before the split this field meant "parseable AND
    # consistent", i.e. today's `consistent is True`.
    emitted: bool
    # Whether the emitted plan passed the (a0) consistency rule (and agreed
    # with the decision's own yield_robot/crossing_order) -- i.e. reached the
    # feasibility audit. True even when it then needed repair or exceeded the
    # repair bound. None when nothing was emitted.
    consistent: bool | None
    # (ii) plan agreement rate: executed verbatim, no repair needed. Always
    # False when `consistent` is not True.
    agreement: bool
    # (iii) plan edit distance: repairs applied. 0 for `vlm_verbatim`,
    # `len(verified.edits)` for `repaired`. None when there is no finite
    # distance to report: the plan was not emitted (nothing to measure from),
    # or it WAS emitted but no repair within the bound was found
    # (`repair_bound_exceeded`) -- that case must not read as 0, which would
    # be indistinguishable from a verbatim plan and bias a mean edit distance
    # low.
    edit_distance: int | None = Field(default=None, ge=0)
    # (iv) executed-plan provenance.
    provenance: PlanProvenance
    # Structured reason `emitted` is False (`absent`/`unknown_robot`),
    # `consistent` is False (`inconsistent`), or a consistent plan still
    # ended up `m3_default` (`repair_bound_exceeded`); None when the
    # executed plan is vlm_verbatim or repaired.
    rejection_stage: PlanRejectionStage | None
    # (v) oracle-order agreement, scored against the VLM's PROPOSED order
    # before any repair (never the executed/repaired order): None when no
    # oracle was registered for this cell, or no consistent plan was emitted
    # to score. Still gated on consistency after the 2026-10-03 split, so its
    # population is unchanged by it.
    oracle_order_agreement: bool | None
    # Metrics-only sub-class of `repaired` (verbatim-pilot ruling A,
    # 2026-10-06): True when every repair edit is a `reorder`, i.e. the plan
    # was verbatim up to list order. `provenance` itself stays `repaired`.
    # None unless `provenance == "repaired"`.
    repaired_order_only: bool | None = None
    # Ruling C: "executed verbatim" -- `vlm_verbatim` AND M5 dispatched those
    # same legs (`PlanDispatchInfo.dispatch_matches_plan`). None when the
    # plan is not `vlm_verbatim` or the dispatch match is unknown.
    verbatim_dispatch_matched: bool | None = None
    # Ruling C: the decided strategy is one of the cell oracle's
    # `accepted_strategies`; the stratum for "provenance conditioned on
    # strategy-vs-oracle correctness". None when the cell registers no
    # accepted strategies.
    strategy_correct: bool | None = None


def score_plan_decision(
    decision: CongestionDecision,
    verified: VerifiedPlan,
    *,
    oracle_order: Sequence[str] | None = None,
    held_robot_ids: Collection[str] = (),
    dispatch_matches_plan: bool | None = None,
    accepted_strategies: Collection[str] | None = None,
) -> PlanDecisionMetrics:
    """Score one decision's plan against the registered per-decision metrics.

    Args:
        decision: The decision whose `proposed_plan` was audited.
        verified: `command_grounder.verify_and_repair_plan`'s output for it.
        oracle_order: Ground-truth execution order for this cell (T2b's
            `correct_order`, B2's priority-first, B3's convoy order, IB10's
            inside-first), restricted to the robots it names; None where the
            cell registers no oracle.
        held_robot_ids: Robots that can only receive `continue` at decision
            time (e.g. B1's robot_3 before its `start_delay_sec` release).
            Excluded from the oracle order before scoring (verbatim-pilot
            ruling D); the caller derives them from the cell's goal table.
        dispatch_matches_plan: The stored `PlanDispatchInfo.
            dispatch_matches_plan` for this decision, or None when unknown.
        accepted_strategies: The cell oracle's `accepted_strategies`, or
            None where the cell registers none.

    Every field is recomputed from `decision` and `verified`, never read from
    a stored metrics record, so a decision artifact written before a field
    existed (e.g. `consistent`) still scores: re-run
    `verify_and_repair_plan` on its stored decision and snapshot, then call
    this, or rebuild it from the stored plan block via
    `score_decision_artifact`.

    Returns:
        The per-decision metrics.
    """
    emitted = verified.rejection_stage not in ("absent", "unknown_robot")
    consistent = (verified.rejection_stage != "inconsistent") if emitted else None
    agreement = consistent is True and verified.provenance == "vlm_verbatim"
    edit_distance: int | None
    if verified.provenance == "repaired":
        edit_distance = len(verified.edits)
    elif verified.provenance == "vlm_verbatim":
        edit_distance = 0
    else:
        # m3_default: either not emitted (no plan to measure), or emitted but
        # `repair_bound_exceeded` (no finite distance was found) -- neither
        # case is a 0-edit agreement.
        edit_distance = None
    return PlanDecisionMetrics(
        emitted=emitted,
        consistent=consistent,
        agreement=agreement,
        edit_distance=edit_distance,
        provenance=verified.provenance,
        rejection_stage=verified.rejection_stage,
        oracle_order_agreement=_score_oracle_order(
            decision, consistent is True, oracle_order, held_robot_ids
        ),
        repaired_order_only=(
            is_order_only_repair(verified.edits) if verified.provenance == "repaired" else None
        ),
        verbatim_dispatch_matched=(
            dispatch_matches_plan if verified.provenance == "vlm_verbatim" else None
        ),
        strategy_correct=strategy_matches_oracle(decision.strategy, accepted_strategies),
    )


def is_order_only_repair(edits: Sequence[PlanEdit]) -> bool:
    """Whether a repair changed only the list order (ruling A's sub-class).

    A `swap` re-assigns roles between positions and a `substitute` changes an
    action, so either one disqualifies; an empty edit list is not a repair.

    Args:
        edits: The repaired plan's `VerifiedPlan.edits`.

    Returns:
        True when there is at least one edit and every edit is a `reorder`.
    """
    return bool(edits) and all(edit.op == "reorder" for edit in edits)


def strategy_matches_oracle(
    strategy: str, accepted_strategies: Collection[str] | None
) -> bool | None:
    """Whether a decided strategy is one the cell's oracle accepts.

    Args:
        strategy: The decision's `strategy`.
        accepted_strategies: The cell oracle's `accepted_strategies` (IB10,
            convoy, loop-detour cells), or None where none is registered.

    Returns:
        None when no accepted set is registered, else membership.
    """
    if accepted_strategies is None:
        return None
    return strategy in accepted_strategies


def _score_oracle_order(
    decision: CongestionDecision,
    scorable: bool,
    oracle_order: Sequence[str] | None,
    held_robot_ids: Collection[str],
) -> bool | None:
    if oracle_order is None or not scorable or decision.proposed_plan is None:
        return None
    # Ruling D: a held robot can only be given `continue`, which the proposed
    # order drops, so keeping it in the oracle made agreement False by
    # construction (pilot B1 triggers). With one robot left the comparison
    # only checks that robot is named with an active role.
    oracle_robots = [robot_id for robot_id in oracle_order if robot_id not in held_robot_ids]
    if not oracle_robots and len(oracle_robots) != len(oracle_order):
        # Every oracle robot is held: nothing left to order. Only the held
        # exclusion returns None here; an empty registered oracle keeps its
        # pre-ruling result.
        return None
    # A "continue" leg carries no sequencing information, so it is not part
    # of the proposed order even when the robot is named with that action.
    proposed_order = [
        leg.robot_id
        for leg in decision.proposed_plan
        if leg.robot_id in oracle_robots and leg.action != "continue"
    ]
    if sorted(proposed_order) != sorted(oracle_robots):
        # The VLM's plan omits or misnames one of the oracle's robots: it
        # cannot agree with an order it does not fully name. False, not
        # None -- a plan WAS emitted, it just cannot be compared cleanly.
        return False
    return proposed_order == oracle_robots


# `verify_and_repair_plan`'s `rejection_reason` prefixes. `rejection_stage`
# is not persisted in the decision artifact's plan block, so an offline
# re-score recovers it from these (round-trip pinned in test_plan_metrics).
_UNPARSEABLE_PREFIX = "plan unparseable"
_BOUND_EXCEEDED_PREFIX = "repair distance exceeds bound"


def _rejection_stage_from_block(
    decision: CongestionDecision, plan_block: Mapping[str, Any]
) -> PlanRejectionStage | None:
    if plan_block.get("provenance") != "m3_default":
        return None
    if decision.proposed_plan is None:
        return "absent"
    reason = plan_block.get("rejection_reason") or ""
    if reason.startswith(_UNPARSEABLE_PREFIX):
        return "unknown_robot"
    if reason.startswith(_BOUND_EXCEEDED_PREFIX):
        return "repair_bound_exceeded"
    return "inconsistent"


def score_decision_artifact(
    artifact: Mapping[str, Any],
    *,
    oracle_order: Sequence[str] | None = None,
    held_robot_ids: Collection[str] = (),
    accepted_strategies: Collection[str] | None = None,
) -> PlanDecisionMetrics | None:
    """Score one stored M5 decision artifact from its `decision` and `plan` blocks.

    The offline join for the registered analysis "provenance conditioned on
    strategy-vs-oracle correctness" (verbatim-pilot ruling C): everything it
    needs is already stored -- `decision.strategy`, and the plan block's
    `provenance`, `edits`, `rejection_reason` and `dispatch_matches_plan` --
    so no new artifact field is required. The cell-level inputs come from
    the run's scenario oracle and goal table: no artifact records which
    robots were still held at decision time, so the caller derives
    `held_robot_ids` from the goal table's `start_delay_sec`. A `plan_held`
    decision is scored like any other, so a per-accepted-plan count must
    filter holds out first (see `compute_episode_plan_stability`).

    Args:
        artifact: One parsed `decisions/<request_id>.json`.
        oracle_order: Forwarded to `score_plan_decision`.
        held_robot_ids: Forwarded to `score_plan_decision`.
        accepted_strategies: Forwarded to `score_plan_decision`.

    Returns:
        The metrics, or None when the artifact carries no decision or no plan
        block (plan channel off, or nothing was dispatched).
    """
    decision_block = artifact.get("decision")
    plan_block = artifact.get("plan")
    if not decision_block or not plan_block:
        return None
    decision = CongestionDecision.model_validate(decision_block)
    verified = VerifiedPlan(
        legs=[
            ProposedPlanLeg(robot_id=leg["robot_id"], action=leg["action"])
            for leg in plan_block.get("legs") or []
        ],
        provenance=plan_block["provenance"],
        edits=[PlanEdit.model_validate(edit) for edit in plan_block.get("edits") or []],
        rejection_reason=plan_block.get("rejection_reason"),
        rejection_stage=_rejection_stage_from_block(decision, plan_block),
    )
    return score_plan_decision(
        decision,
        verified,
        oracle_order=oracle_order,
        held_robot_ids=held_robot_ids,
        dispatch_matches_plan=plan_block.get("dispatch_matches_plan"),
        accepted_strategies=accepted_strategies,
    )


StrategyStratum = Literal["strategy_correct", "strategy_incorrect", "strategy_unscored"]


class ProvenanceStratum(BaseModel):
    """Provenance counts within one strategy-correctness stratum."""

    model_config = ConfigDict(frozen=True)

    plans: int = Field(default=0, ge=0)
    vlm_verbatim: int = Field(default=0, ge=0)
    repaired: int = Field(default=0, ge=0)
    # Subset of `repaired`.
    repaired_order_only: int = Field(default=0, ge=0)
    m3_default: int = Field(default=0, ge=0)
    # Subsets of `vlm_verbatim`; verbatim plans with an unknown dispatch match
    # are in neither.
    verbatim_dispatch_matched: int = Field(default=0, ge=0)
    verbatim_dispatch_mismatched: int = Field(default=0, ge=0)


def tabulate_provenance_by_strategy_correctness(
    metrics: Iterable[PlanDecisionMetrics],
) -> dict[StrategyStratum, ProvenanceStratum]:
    """Provenance conditioned on strategy-vs-oracle correctness (ruling C).

    Verbatim under a wrong or unconstrained strategy (the pilot's gpt-4o
    IB10 `reverse` plans) lands in `strategy_incorrect`, so it cannot
    inflate the correct-strategy verbatim rate.

    Args:
        metrics: Per-decision metrics, e.g. from `score_decision_artifact`.

    Returns:
        One stratum per correctness value; every key is always present.
    """
    counts: dict[StrategyStratum, dict[str, int]] = {
        key: dict.fromkeys(ProvenanceStratum.model_fields, 0)
        for key in ("strategy_correct", "strategy_incorrect", "strategy_unscored")
    }
    for item in metrics:
        stratum: StrategyStratum = (
            "strategy_unscored"
            if item.strategy_correct is None
            else "strategy_correct"
            if item.strategy_correct
            else "strategy_incorrect"
        )
        row = counts[stratum]
        row["plans"] += 1
        row[item.provenance] += 1
        if item.repaired_order_only:
            row["repaired_order_only"] += 1
        if item.verbatim_dispatch_matched is True:
            row["verbatim_dispatch_matched"] += 1
        elif item.verbatim_dispatch_matched is False:
            row["verbatim_dispatch_mismatched"] += 1
    return {key: ProvenanceStratum(**row) for key, row in counts.items()}


class PlanChurn(BaseModel):
    """Churn between two successive accepted plans (stability building block).

    `revision_type` needs a registered churn-fraction threshold (the design
    spec's "incremental ... below a registered fraction of legs ... else
    wholesale"); this module takes it as a parameter rather than freezing a
    value, since the spec explicitly defers sizing it.
    """

    model_config = ConfigDict(frozen=True)

    # Robots whose action differs between the two plans, including a robot
    # only one of the two plans names (a scene-wide completion difference, or
    # a robot entering/leaving the tracked set): there is no prior/current
    # action to compare it against, so it counts as changed.
    changed_robot_ids: tuple[str, ...]
    # len(changed_robot_ids) / union size; 0.0 for two empty plans.
    churn_fraction: float = Field(ge=0.0, le=1.0)
    revision_type: RevisionType


def compute_plan_churn(
    previous: Sequence[ProposedPlanLeg],
    current: Sequence[ProposedPlanLeg],
    *,
    incremental_fraction_bound: float = 0.5,
) -> PlanChurn:
    """Churn between two successive plans, over the union of robots they name.

    Args:
        previous: The prior accepted plan's legs.
        current: The current accepted plan's legs.
        incremental_fraction_bound: Churn at or below this fraction of the
            union is `"incremental"`, above it `"wholesale"`. Placeholder
            default (0.5): the spec registers the fraction but does not size
            it, matching the repair-distance bound's "to be sized later".

    Returns:
        The churn summary.
    """
    previous_by_robot = {leg.robot_id: leg.action for leg in previous}
    current_by_robot = {leg.robot_id: leg.action for leg in current}
    union = sorted(set(previous_by_robot) | set(current_by_robot))
    changed = tuple(
        robot_id
        for robot_id in union
        if previous_by_robot.get(robot_id) != current_by_robot.get(robot_id)
    )
    fraction = len(changed) / len(union) if union else 0.0
    revision_type: RevisionType = (
        "incremental" if fraction <= incremental_fraction_bound else "wholesale"
    )
    return PlanChurn(
        changed_robot_ids=changed, churn_fraction=fraction, revision_type=revision_type
    )


def classify_revision_cause(failed_robot_ids: Sequence[str]) -> RevisionCause:
    """Whether a replan follows at least one leg execution failure.

    A pure classifier over the caller-supplied failure set; this module has
    no access to M5's per-leg execution-status tracking (`pending/active/
    done/failed`, the next build-order step), so the caller (M5, once that
    tracking exists) determines `failed_robot_ids` itself.

    Args:
        failed_robot_ids: Robots whose leg was reported `failed` since the
            last invocation that produced the prior plan.

    Returns:
        `"evidence_driven"` when at least one leg failed, else `"unforced"`
        (a revision with nothing reported failed -- dithering).
    """
    return "evidence_driven" if failed_robot_ids else "unforced"


class EpisodePlanStability(BaseModel):
    """Aggregate plan-stability building blocks over one episode's plans."""

    model_config = ConfigDict(frozen=True)

    replan_count: int = Field(ge=0)
    # One entry per consecutive pair, in episode order; empty for a
    # single-plan (no replan) episode.
    churns: list[PlanChurn] = Field(default_factory=list)


def compute_episode_plan_stability(
    plans: Sequence[Sequence[ProposedPlanLeg]],
    *,
    incremental_fraction_bound: float = 0.5,
) -> EpisodePlanStability:
    """Stability building blocks across one episode's sequence of accepted plans.

    `replan_count` counts only GENUINELY DIFFERENT accepted plans (the hold
    ruling, 2026-10-02): a caller building `plans` from an artifact stream or
    from `PlanTracker` must supply one entry per distinct accepted `plan_id`
    -- i.e. skip every decision whose `PlanDispatchInfo.plan_held` is True
    (or, from `PlanTracker.accept_plan`'s own return value, every
    `PlanAcceptance` with `held=True`) -- NOT one entry per analysis. A hold
    re-affirms the active plan rather than accepting a new one, so it must
    never inflate this count; this is what makes the step-4 smoke's "zero
    unforced replans" criterion well-defined on a two-robot head-on where the
    VLM is re-asked the same question more than once.

    Args:
        plans: Each GENUINELY ACCEPTED plan (`VerifiedPlan.legs`), in the
            order it was adopted during the episode -- holds excluded, not
            one entry per analysis.
        incremental_fraction_bound: Forwarded to `compute_plan_churn` for
            every consecutive pair.

    Returns:
        The replan count (`len(plans) - 1`, floored at 0) and the
        per-transition churn list. `revision_cause` is deliberately absent:
        it needs M5's per-leg execution status; see `classify_revision_cause`.
    """
    churns = [
        compute_plan_churn(
            plans[i - 1], plans[i], incremental_fraction_bound=incremental_fraction_bound
        )
        for i in range(1, len(plans))
    ]
    return EpisodePlanStability(replan_count=max(0, len(plans) - 1), churns=churns)


def any_leg_exhausted(statuses: Sequence[PlanLegStatus]) -> bool:
    """Whether a tracked plan reached the terminal `exhausted` outcome on any leg.

    Freeze-blocking finding 5 (step-7a fix): `exhausted` means the
    `junction_clear` composite's own documented fallback ALSO failed, after
    an earlier phase already had -- `orchestrator_node._mark_fallback_
    exhausted` is the only writer of this status. Scored alongside
    `JunctionPhaseReached`'s existing ordinal (`swarm_orchestrator.
    junction_phase_queue`): together they make "the fallback itself failed"
    a distinguishable, scorable episode outcome instead of an
    indistinguishable plain `failed`. A pure function over whatever leg
    statuses the caller supplies (a live `TrackedPlan.legs`, or a stored
    decision artifact's `PlanDispatchInfo.legs`, re-read offline), matching
    this module's existing building-block convention.

    Args:
        statuses: Every leg's `PlanLegStatus` of one tracked plan.

    Returns:
        True when at least one status is `"exhausted"`.
    """
    return "exhausted" in statuses

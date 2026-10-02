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
"""

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.command_grounder import PlanProvenance, PlanRejectionStage, VerifiedPlan
from reasoning.vlm.models import CongestionDecision, ProposedPlanLeg

# Whether a replan followed at least one leg execution failure since the last
# invocation (rev 4, "Re-planning as measured behavior").
RevisionCause = Literal["evidence_driven", "unforced"]
# Whether a replan's churn stays below the registered fraction of legs.
RevisionType = Literal["incremental", "wholesale"]


class PlanDecisionMetrics(BaseModel):
    """Per-decision plan-quality metrics ((i)-(v) of the registered set)."""

    model_config = ConfigDict(frozen=True)

    # (i) plan emission rate: a parseable, consistent plan was supplied.
    # True even when the plan later needed repair, or the repair distance
    # exceeded the bound -- emission is about reaching feasibility
    # auditing, not about surviving it.
    emitted: bool
    # (ii) plan agreement rate: executed verbatim, no repair needed. Always
    # False when `emitted` is False.
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
    # Structured reason `emitted` is False, or why an emitted plan still
    # ended up `m3_default` (`repair_bound_exceeded`); None when the
    # executed plan is vlm_verbatim or repaired.
    rejection_stage: PlanRejectionStage | None
    # (v) oracle-order agreement, scored against the VLM's PROPOSED order
    # before any repair (never the executed/repaired order): None when no
    # oracle was registered for this cell, or no plan was emitted to score.
    oracle_order_agreement: bool | None


def score_plan_decision(
    decision: CongestionDecision,
    verified: VerifiedPlan,
    *,
    oracle_order: Sequence[str] | None = None,
) -> PlanDecisionMetrics:
    """Score one decision's plan against the registered per-decision metrics.

    Args:
        decision: The decision whose `proposed_plan` was audited.
        verified: `command_grounder.verify_and_repair_plan`'s output for it.
        oracle_order: Ground-truth execution order for this cell (T2b's
            `correct_order`, B2's priority-first, B3's convoy order, IB10's
            inside-first), restricted to the robots it names; None where the
            cell registers no oracle.

    Returns:
        The per-decision metrics.
    """
    emitted = verified.rejection_stage not in ("absent", "unknown_robot", "inconsistent")
    agreement = emitted and verified.provenance == "vlm_verbatim"
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
        agreement=agreement,
        edit_distance=edit_distance,
        provenance=verified.provenance,
        rejection_stage=verified.rejection_stage,
        oracle_order_agreement=_score_oracle_order(decision, emitted, oracle_order),
    )


def _score_oracle_order(
    decision: CongestionDecision, emitted: bool, oracle_order: Sequence[str] | None
) -> bool | None:
    if oracle_order is None or not emitted or decision.proposed_plan is None:
        return None
    oracle_robots = list(oracle_order)
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

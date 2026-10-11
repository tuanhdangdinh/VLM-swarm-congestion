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
prereg-v3 A21 adds the `repaired_lane_scope_only` sub-class under the
A17-bis family rule (a mechanically separable repair cause is its own
stratum). prereg-v3 A27(iv) registers the dispatch match READ with
retreat-shielded robots excluded (`shield_excluded_dispatch_match`), the raw
match co-reported.
"""

from collections.abc import Collection, Iterable, Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.command_grounder import (
    LANE_SCOPED_HOLD_PREFIX,
    PlanEdit,
    PlanProvenance,
    PlanRejectionStage,
    VerifiedPlan,
    project_dispatched_legs,
)
from reasoning.rag.retreat_shield import SHIELD_TAG
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
    # prereg-v3 A21 sub-class of `repaired`: True when every repair edit is
    # a lane-scoped off-lane hold (`is_lane_scope_only_repair`), i.e. the
    # plan was verbatim except for crossing robots dispatch holds outside
    # the yield's lane conflict. None unless `provenance == "repaired"`.
    repaired_lane_scope_only: bool | None = None
    # Ruling C: "executed verbatim" -- `vlm_verbatim` AND M5 dispatched those
    # same legs (`PlanDispatchInfo.dispatch_matches_plan`). None when the
    # plan is not `vlm_verbatim` or the dispatch match is unknown.
    verbatim_dispatch_matched: bool | None = None
    # prereg-v3 A27(iv), the registered reading: `verbatim_dispatch_matched`
    # with retreat-shielded robots left out of the dispatch comparison
    # (`shield_excluded_dispatch_match`). Set only by
    # `score_decision_artifact`, which sees the dispatched command; None
    # otherwise, and when the plan is not `vlm_verbatim`.
    verbatim_dispatch_matched_shield_excluded: bool | None = None
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
        repaired_lane_scope_only=(
            is_lane_scope_only_repair(verified.edits)
            if verified.provenance == "repaired"
            else None
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


def is_lane_scope_only_repair(edits: Sequence[PlanEdit]) -> bool:
    """Whether a repair only released dispatch's lane-scoped off-lane holds.

    prereg-v3 A21: `verify_and_repair_plan` substitutes a `cross` or
    `continue` leg on a robot dispatch holds outside the yield's lane
    conflict (`order=lane_scoped:<ids>`) to `wait`, with an edit reason
    starting `command_grounder.LANE_SCOPED_HOLD_PREFIX`. Composed with any
    other edit (e.g. the yielder `swap`) the repair is not in this class.

    Args:
        edits: The repaired plan's `VerifiedPlan.edits`.

    Returns:
        True when there is at least one edit and every edit is such a
        substitute.
    """
    return bool(edits) and all(
        edit.op == "substitute" and edit.reason.startswith(LANE_SCOPED_HOLD_PREFIX)
        for edit in edits
    )


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
# A grounding-view or partner-retry refusal (prereg-v3 A16, A16(v)): the
# verifier records stage `repair_bound_exceeded` with the refusal's reason.
_UNREPAIRABLE_PREFIX = "plan unrepairable"


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
    if reason.startswith((_BOUND_EXCEEDED_PREFIX, _UNREPAIRABLE_PREFIX)):
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
    metrics = score_plan_decision(
        decision,
        verified,
        oracle_order=oracle_order,
        held_robot_ids=held_robot_ids,
        dispatch_matches_plan=plan_block.get("dispatch_matches_plan"),
        accepted_strategies=accepted_strategies,
    )
    if verified.provenance != "vlm_verbatim":
        return metrics
    return metrics.model_copy(
        update={
            "verbatim_dispatch_matched_shield_excluded": (
                shield_excluded_dispatch_match(artifact).excluded
            )
        }
    )


def shielded_robot_ids(command: Mapping[str, Any] | None) -> frozenset[str]:
    """Robots a dispatched command holds as retreat-shield bystanders.

    Args:
        command: A dispatched grounded command, or None.

    Returns:
        The ids named by its `grounding=retreat_shield:<id>` degradation tags;
        empty for None or an unshielded command.
    """
    prefix = f"{SHIELD_TAG}:"
    return frozenset(
        tag[len(prefix):]
        for tag in (command or {}).get("degradations") or []
        if isinstance(tag, str) and tag.startswith(prefix)
    )


def dispatch_matches_plan_excluding(
    plan_legs: Sequence[Mapping[str, Any]],
    command: Mapping[str, Any],
    known_robot_ids: Sequence[str],
    excluded: Collection[str] = (),
) -> bool:
    """`command_grounder.plan_matches_dispatch` with some robots left out of both sides.

    Args:
        plan_legs: The plan block's legs (`robot_id`, `action`).
        command: The dispatched command.
        known_robot_ids: Every robot of the decision's scene.
        excluded: Robots dropped from the plan and the projected dispatch.

    Returns:
        True when every remaining robot's projected dispatched action equals
        its plan leg's action. With nothing excluded this is exactly the live
        `plan_matches_dispatch`.
    """
    dispatched = project_dispatched_legs(dict(command), known_robot_ids)
    plan_by_robot = {leg["robot_id"]: leg["action"] for leg in plan_legs}
    skip = set(excluded)
    return {r: a for r, a in dispatched.items() if r not in skip} == {
        r: a for r, a in plan_by_robot.items() if r not in skip
    }


class ShieldExcludedMatch(BaseModel):
    """One decision's dispatch match, raw and with shielded robots excluded (A27(iv))."""

    model_config = ConfigDict(frozen=True)

    # The stored live `PlanDispatchInfo.dispatch_matches_plan`.
    raw: bool | None
    # The registered reading: shielded robots left out of the comparison (the
    # A21 lane-scope precedent: a shield wait projects as `wait` where the
    # model's plan says `continue`). Equal to `raw` when nothing is shielded.
    excluded: bool | None
    shielded: tuple[str, ...] = ()
    # Whether every shielded robot's plan leg is `continue` (the expected
    # case: the shield never holds a robot the model gave an active leg).
    shielded_legs_continue: bool | None = None


def shield_excluded_dispatch_match(artifact: Mapping[str, Any]) -> ShieldExcludedMatch:
    """Re-read one stored decision artifact's dispatch match with shielded robots excluded.

    Only a decision whose dispatched command carries retreat-shield tags is
    recomputed; every other one returns its stored value for both readings.
    A recomputed raw match that disagrees with the stored value means the
    artifact's plan or command was not the one the live match saw.

    Args:
        artifact: One parsed `decisions/<request_id>.json`.

    Returns:
        The raw and shield-excluded readings.

    Raises:
        ValueError: The recomputed raw match differs from the stored one.
    """
    plan = artifact.get("plan") or {}
    raw = plan.get("dispatch_matches_plan")
    command = artifact.get("dispatched_command")
    shielded = shielded_robot_ids(command)
    if not shielded or raw is None or not command:
        return ShieldExcludedMatch(raw=raw, excluded=raw)
    legs = plan.get("legs") or []
    known = [r["robot_id"] for r in (artifact.get("scene") or {}).get("robots", [])]
    recomputed = dispatch_matches_plan_excluding(legs, command, known)
    if recomputed != raw:
        raise ValueError(
            f"artifact {artifact.get('request_id')}: recomputed dispatch match "
            f"{recomputed} != stored {raw}"
        )
    plan_by_robot = {leg["robot_id"]: leg["action"] for leg in legs}
    return ShieldExcludedMatch(
        raw=raw,
        excluded=dispatch_matches_plan_excluding(legs, command, known, shielded),
        shielded=tuple(sorted(shielded)),
        shielded_legs_continue=all(plan_by_robot.get(r) == "continue" for r in shielded),
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
    # Subset of `repaired` (prereg-v3 A21).
    repaired_lane_scope_only: int = Field(default=0, ge=0)
    m3_default: int = Field(default=0, ge=0)
    # Subsets of `vlm_verbatim`; verbatim plans with an unknown dispatch match
    # are in neither.
    verbatim_dispatch_matched: int = Field(default=0, ge=0)
    verbatim_dispatch_mismatched: int = Field(default=0, ge=0)
    # prereg-v3 A27(iv): the registered reading, shielded robots excluded;
    # `verbatim_dispatch_matched` above stays the co-reported raw count.
    verbatim_dispatch_matched_shield_excluded: int = Field(default=0, ge=0)


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
        if item.repaired_lane_scope_only:
            row["repaired_lane_scope_only"] += 1
        if item.verbatim_dispatch_matched is True:
            row["verbatim_dispatch_matched"] += 1
        elif item.verbatim_dispatch_matched is False:
            row["verbatim_dispatch_mismatched"] += 1
        if item.verbatim_dispatch_matched_shield_excluded is True:
            row["verbatim_dispatch_matched_shield_excluded"] += 1
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

"""Pure M5 plan-state tracker (prereg-v2 rev 4, "Plan lifecycle").

ROS2-free logic behind the orchestrator's plan channel
(`reasoning_pipeline.InProcessPipeline`, behind `plan_channel_enabled`):
assigns the monotonic `plan_id` every accepted plan gets -- "every accepted
plan (including `m3_default` ones -- every executed resolution has a plan)"
-- tracks each leg's execution status (`pending`/`active`/`done`/`failed`),
and computes which of a superseded plan's legs must be retired, and in what
order, when a new plan replaces the active one.

Cancellation order reuses the ordered-release DIRECTION
`swarm_execution.crossing_chain` encodes for a single in-flight command's
live admission state (passers are admitted one at a time in
`crossing_order`; the hold ends only once the LAST one has cleared) rather
than its runtime machinery: this module compares two whole PLANS, never a
live timer/odometry state, so there is nothing here to duplicate from that
module. A plan's own leg list is already in that same execution/admission
order (`_derive_default_plan`'s convention: `[yielder, *crossing_order,
...continue-robots]`), so undoing it safely -- without stranding a robot
mid-maneuver waiting on a clearance signal from a robot whose command just
changed -- means retiring whichever leg was admitted LAST first:
cancellation order is the REVERSE of the superseded plan's own leg order,
restricted to legs not already terminal.

Hold semantics (ruling 2026-10-02, `docs/implementation_notes.md`): not
every `accept_plan` call is a replan. When the new analysis's verified plan
names the exact same action for every one of the active plan's REMAINING
(non-`done`) legs, this is a re-affirmation of the resolution already in
progress, not a new one -- `plan_id` stays unchanged, `plan_holds` counts it,
and leg statuses are untouched. This is what makes "zero unforced replans"
on a clean two-robot head-on well-defined: a post-resolution re-check that
still proposes the same thing is a hold, not churn, and `replan_count`
(`plan_metrics`/episode stability) counts only plans that DO consume a new
`plan_id` -- genuinely different accepted plans. REFINEMENT (2026-10-02,
from the step-4 smoke; landed with build-order step 5): if any leg of the
active plan has reached `failed`, an identical re-issue is never a hold --
see `_is_hold`.

This module never dispatches a command or touches a ROS2 topic; node code
converts and delegates (CLAUDE.md "ROS2 Code": keep callbacks thin).

`PlanTracker` is used from two different threads in `orchestrator_node.py`:
`accept_plan` runs on the pipeline's worker thread (`InProcessPipeline.run`,
submitted to a `ThreadPoolExecutor`), while `set_leg_status` and
`plan_state_context` run on the rclpy spin thread (`_on_status`, and request
building before the next dispatch). Every public method therefore holds an
internal lock for its whole body -- a `set_leg_status` call straddling an
`accept_plan` call must not observe or leave a torn `self._active`.
"""
from __future__ import annotations

import threading
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.command_grounder import PlanEdit, PlanProvenance, VerifiedPlan
from reasoning.rag.plan_metrics import compute_plan_churn
from reasoning.vlm.models import (
    PlanLegAction,
    PlanLegStatus,
    PlanStateContext,
    PlanStateLeg,
    ProposedPlanLeg,
)

# The state machine M5 reports a leg's execution through. `pending` (accepted,
# not yet dispatched/admitted), `active` (dispatched and in flight), `done`,
# `failed`, and `exhausted` are terminal -- once a leg reaches one of these
# three, it never changes status again (a new maneuver for that robot is a
# NEW plan's NEW leg, not a status change on the old one). `exhausted`
# (step-7a fix, freeze-blocking finding 5) is M5 (`orchestrator_node.
# _mark_fallback_exhausted`) observing a `junction_clear` fallback's own
# terminal outcome being a failure, for every robot the fallback addressed
# -- including one still `pending` (e.g. held through every phase, never
# individually resolved, same precedent as the existing `pending -> failed`
# transition below) and one already `failed` from an earlier phase.
_TERMINAL_STATUSES: frozenset[PlanLegStatus] = frozenset({"done", "failed", "exhausted"})

_VALID_TRANSITIONS: dict[PlanLegStatus, frozenset[PlanLegStatus]] = {
    "pending": frozenset({"pending", "active", "done", "failed", "exhausted"}),
    "active": frozenset({"active", "done", "failed", "exhausted"}),
    "done": frozenset({"done"}),
    "failed": frozenset({"failed", "exhausted"}),
    "exhausted": frozenset({"exhausted"}),
}


class TrackedLeg(BaseModel):
    """One leg of a tracked plan, with M5's own execution status."""

    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    action: PlanLegAction
    status: PlanLegStatus = "pending"


class TrackedPlan(BaseModel):
    """A plan M5 has accepted and is tracking."""

    model_config = ConfigDict(frozen=True)

    plan_id: int = Field(ge=1)
    legs: tuple[TrackedLeg, ...]
    provenance: PlanProvenance
    edits: tuple[PlanEdit, ...] = ()

    def leg_for(self, robot_id: str) -> TrackedLeg | None:
        """Return this plan's leg for `robot_id`, or None if it names none."""
        return next((leg for leg in self.legs if leg.robot_id == robot_id), None)

    def as_proposed_plan(self) -> list[ProposedPlanLeg]:
        """Project to the `{robot_id, action}` shape `plan_metrics` functions take."""
        return [ProposedPlanLeg(robot_id=leg.robot_id, action=leg.action) for leg in self.legs]

    def to_plan_state_context(self, changed_robot_ids: Sequence[str] = ()) -> PlanStateContext:
        """Project to the prompt-v3 plan-state block's input shape."""
        return PlanStateContext(
            plan_id=self.plan_id,
            legs=[
                PlanStateLeg(robot_id=leg.robot_id, action=leg.action, status=leg.status)
                for leg in self.legs
            ],
            changed_robot_ids=tuple(changed_robot_ids),
        )


class Supersession(BaseModel):
    """One plan replacing another: which of the old plan's legs to retire, in order."""

    model_config = ConfigDict(frozen=True)

    superseded_plan_id: int = Field(ge=1)
    new_plan_id: int = Field(ge=1)
    # Robots whose OLD leg must be cancelled, in dependency order (the
    # superseded plan's own leg order, reversed -- see module docstring).
    # Empty when the new plan carries every old non-terminal leg forward
    # unchanged (a pure extension, not a cancellation).
    cancel_order: tuple[str, ...]


class PlanAcceptance(BaseModel):
    """Result of `PlanTracker.accept_plan`: the new plan, and how to retire the old one."""

    model_config = ConfigDict(frozen=True)

    plan: TrackedPlan
    # None for the episode's first accepted plan; set whenever a plan was
    # already active (explicit supersession, never an implicit/blind one).
    # Always None when `held` is True -- a hold supersedes nothing.
    supersedes: Supersession | None = None
    # Hold semantics (ruling 2026-10-02): True when this call re-affirmed the
    # active plan rather than accepting a new one -- `plan` is then the SAME
    # `TrackedPlan` that was already active (same `plan_id`, same leg
    # statuses), not a new object, and no `plan_id` was consumed.
    held: bool = False


def _is_hold(active: TrackedPlan, verified_legs: Sequence[ProposedPlanLeg]) -> bool:
    """Whether `verified_legs` is IDENTICAL to `active`'s REMAINING (non-`done`) legs.

    Hold semantics (ruling 2026-10-02): a new analysis whose verified plan
    names the exact same action, in the exact same order, for every one of
    the active plan's non-terminal-by-completion legs is a re-affirmation,
    not a replan -- "revise only for a reason" (the plan-state prompt
    advice) needs exactly this read to be well-defined. Order matters: a
    REORDER repair (the same per-robot actions, a different execution
    sequence) is exactly one of the revisions the plan-stability metric
    means to catch, so it must not be absorbed into a hold. A new plan
    naming an extra robot the active plan's remaining legs do not cover
    (a scene-wide completion gaining a robot M1 only now confirms, say) is
    likewise not identical, so it is a replan too -- `filtered` below can
    only equal `remaining` when it is the same length.

    Restricted to non-`done` legs on purpose: a robot whose leg already
    finished does not need to be named again (or named the same way) for
    the new plan to count as holding the resolution it is still carrying
    out; what the new plan says about an already-`done` robot is dropped
    from the comparison entirely, never compared. A plan with no remaining
    legs (every leg `done`) is never a hold -- there is nothing left to
    re-affirm, so any plan accepted at that point is judged a fresh one on
    its own merits.

    REFINEMENT (2026-10-02, spec `docs/superpowers/specs/2026-09-30-
    prereg-v2-design.md` "(a0) Hold semantics", from the step-4 smoke): if
    ANY leg of `active` has reached `failed` since it was accepted, an
    identical re-issue is never a hold, whatever the remaining-legs
    comparison says -- a retry is a response to evidence
    (`plan_metrics.classify_revision_cause` would call it
    `evidence_driven`), and counting it as a hold would hide exactly the
    revision the plan-stability metric exists to see. This replaces the
    FLAGGED (not fixed) gap pinned at CORE landing: "non-`done`" legs
    included `failed`, so an identical re-issue after a failure read as a
    hold under the un-refined wording.

    Args:
        active: The currently active tracked plan.
        verified_legs: The new analysis's verified (post-repair) legs, in
            their proposed execution order.

    Returns:
        True when no leg of `active` has `failed`, and `verified_legs`, with
        every already-`done` robot's leg dropped, is the exact same ordered
        `(robot_id, action)` sequence as `active`'s remaining legs.
    """
    if any(leg.status == "failed" for leg in active.legs):
        return False
    remaining = [(leg.robot_id, leg.action) for leg in active.legs if leg.status != "done"]
    if not remaining:
        return False
    done_ids = {leg.robot_id for leg in active.legs if leg.status == "done"}
    filtered = [
        (leg.robot_id, leg.action) for leg in verified_legs if leg.robot_id not in done_ids
    ]
    return filtered == remaining


def _cancel_order(old: TrackedPlan, new: TrackedPlan) -> list[str]:
    new_action_by_robot: dict[str, PlanLegAction] = {leg.robot_id: leg.action for leg in new.legs}
    candidates = {
        leg.robot_id
        for leg in old.legs
        if leg.status not in _TERMINAL_STATUSES
        and new_action_by_robot.get(leg.robot_id) != leg.action
    }
    # Reverse of the OLD plan's own leg order: a plan's leg list IS its
    # execution/admission order, so retiring it safely means starting from
    # whichever leg was admitted LAST (module docstring).
    return [leg.robot_id for leg in reversed(old.legs) if leg.robot_id in candidates]


class PlanTracker:
    """Owns the plan_id counter and every plan accepted so far this session.

    Pure Python, no ROS2: one instance per M5 process, held and delegated to
    by `reasoning_pipeline.InProcessPipeline`, never touching a topic or a
    command directly.
    """

    def __init__(self) -> None:
        self._next_plan_id = 1
        self._active: TrackedPlan | None = None
        self._plans: dict[int, TrackedPlan] = {}
        # Hold semantics (ruling 2026-10-02): counts `accept_plan` calls that
        # re-affirmed the active plan instead of accepting a new one. Never
        # consumes a `plan_id` -- `replan_count` (plan_metrics / episode
        # stability) is meant to count only genuinely different accepted
        # plans, which is exactly the plans that DO get a new `plan_id`.
        self._plan_holds = 0
        # v4 refusal feedback (`shown_plan`): which plan each accepted plan
        # superseded (None for the session's first), and the plans M5 never
        # dispatched. Read only by `shown_plan`/`is_withheld`; no decision
        # this tracker makes depends on them.
        self._predecessor: dict[int, int | None] = {}
        self._withheld: set[int] = set()
        # Not reentrant: no method below calls another public method of this
        # class while holding it (module docstring explains why one is needed
        # at all).
        self._lock = threading.Lock()

    @property
    def active_plan(self) -> TrackedPlan | None:
        """The currently active plan, or None before the first is accepted."""
        with self._lock:
            return self._active

    @property
    def plan_holds(self) -> int:
        """Count of `accept_plan` calls that re-affirmed the active plan (ruling 2026-10-02)."""
        with self._lock:
            return self._plan_holds

    def plan(self, plan_id: int) -> TrackedPlan | None:
        """Look up a plan (active or superseded) by id, e.g. for a late status update."""
        with self._lock:
            return self._plans.get(plan_id)

    def accept_plan(self, verified: VerifiedPlan) -> PlanAcceptance:
        """Assign the next monotonic `plan_id` to `verified` and retire the old active plan.

        Called for every v2-channel decision, whatever `verified.provenance`
        is: "every accepted plan (including `m3_default` ones) ... every
        executed resolution has a plan" (prereg-v2 (a0)) -- EXCEPT a hold
        (ruling 2026-10-02): when `verified.legs` names the exact same action
        for every one of the active plan's REMAINING (non-`done`) legs, this
        call records a HOLD instead -- the active `plan_id` is unchanged, no
        new `TrackedPlan` is created, `plan_holds` is incremented, and leg
        statuses are left exactly as they were (a hold never resets them). A
        genuinely different plan is still a replan (explicit supersession);
        its non-terminal legs that the new plan does not carry forward
        unchanged are retired in dependency order (`_cancel_order`).

        Args:
            verified: `command_grounder.verify_and_repair_plan`'s output for
                the decision just dispatched.

        Returns:
            On a hold: the unchanged active plan, `supersedes=None`,
            `held=True`. Otherwise: the new tracked plan plus, when one was
            already active, the `Supersession` describing how to retire it.
        """
        with self._lock:
            if self._active is not None and _is_hold(self._active, verified.legs):
                self._plan_holds += 1
                return PlanAcceptance(plan=self._active, held=True)
            plan_id = self._next_plan_id
            self._next_plan_id += 1
            legs = tuple(
                TrackedLeg(robot_id=leg.robot_id, action=leg.action, status="pending")
                for leg in verified.legs
            )
            new_plan = TrackedPlan(
                plan_id=plan_id,
                legs=legs,
                provenance=verified.provenance,
                edits=tuple(verified.edits),
            )
            self._plans[plan_id] = new_plan
            previous = self._active
            self._predecessor[plan_id] = None if previous is None else previous.plan_id
            self._active = new_plan
            if previous is None:
                return PlanAcceptance(plan=new_plan)
            return PlanAcceptance(
                plan=new_plan,
                supersedes=Supersession(
                    superseded_plan_id=previous.plan_id,
                    new_plan_id=new_plan.plan_id,
                    cancel_order=tuple(_cancel_order(previous, new_plan)),
                ),
            )

    def mark_withheld(self, plan_id: int) -> bool:
        """Record that M5 never dispatched the outcome this plan was accepted for.

        v4 refusal feedback. `accept_plan` runs in the pipeline worker, before
        M5 decides whether the outcome is dispatched, so a withheld outcome's
        plan becomes the active plan. The mark changes nothing the tracker
        decides (`active_plan`, holds, supersession, leg statuses and plan ids
        are exactly as without it, so dispatch is unaffected); it only steers
        `shown_plan`, which the prompt's plan-state block reads.

        Args:
            plan_id: The plan accepted (not held) for the undispatched outcome.

        Returns:
            True when the plan is known and was not marked before.
        """
        with self._lock:
            if plan_id not in self._plans or plan_id in self._withheld:
                return False
            self._withheld.add(plan_id)
            return True

    def is_withheld(self, plan_id: int) -> bool:
        """Whether `mark_withheld` marked this plan."""
        with self._lock:
            return plan_id in self._withheld

    def shown_plan(self) -> TrackedPlan | None:
        """The plan the prompt may present as active: the latest one M5 dispatched.

        Walks back from `active_plan` through the plans each superseded,
        skipping every plan marked withheld, so a withheld plan is never
        presented as accepted. Equals `active_plan` when nothing is marked.

        Returns:
            That plan with its current leg statuses, or None when every plan
            in the chain was withheld (or none was accepted).
        """
        with self._lock:
            plan_id = None if self._active is None else self._active.plan_id
            while plan_id is not None and plan_id in self._withheld:
                plan_id = self._predecessor.get(plan_id)
            return None if plan_id is None else self._plans[plan_id]

    def set_leg_status(self, plan_id: int, robot_id: str, status: PlanLegStatus) -> TrackedLeg:
        """Update one leg's execution status, enforcing the state machine.

        Args:
            plan_id: The tracked plan the leg belongs to (active or
                superseded -- a superseded plan's just-cancelled legs still
                need their terminal status recorded).
            robot_id: The robot whose leg changed.
            status: The new status.

        Returns:
            The updated leg.

        Raises:
            KeyError: If `plan_id` is unknown, or names no leg for `robot_id`.
            ValueError: If `status` is not a valid transition from the leg's
                current one (`pending` -> any; `active` -> `active`/`done`/
                `failed`; `done`/`failed` are terminal).
        """
        with self._lock:
            plan = self._require_plan(plan_id)
            leg = plan.leg_for(robot_id)
            if leg is None:
                raise KeyError(f"plan {plan_id} has no leg for {robot_id!r}")
            if status not in _VALID_TRANSITIONS[leg.status]:
                raise ValueError(
                    f"plan {plan_id} robot {robot_id!r}: invalid leg status transition "
                    f"{leg.status!r} -> {status!r}"
                )
            updated_leg = leg.model_copy(update={"status": status})
            updated_legs = tuple(
                updated_leg if existing.robot_id == robot_id else existing
                for existing in plan.legs
            )
            updated_plan = plan.model_copy(update={"legs": updated_legs})
            self._plans[plan_id] = updated_plan
            if self._active is not None and self._active.plan_id == plan_id:
                self._active = updated_plan
            return updated_leg

    def plan_state_context(
        self, plan_id: int, *, since_plan_id: int | None
    ) -> PlanStateContext:
        """Project a tracked plan to the prompt-v3 plan-state block's input shape.

        `changed_robot_ids` ("what changed since the last invocation") is
        computed relative to `since_plan_id`, not stored on the plan itself:
        the same plan can be shown unchanged across several invocations (no
        replan happened), and each of those renders must show an EMPTY
        change set, not the diff from when the plan was first accepted. The
        caller supplies which plan_id it last rendered (its own
        per-invocation bookkeeping); this method stays a pure function of
        its arguments.

        Args:
            plan_id: The plan to render (normally `self.active_plan.plan_id`).
            since_plan_id: The plan_id shown at the PREVIOUS invocation, or
                None for the episode's first invocation. Equal to `plan_id`
                means nothing changed since last time.

        Returns:
            The plan-state block's input, including `changed_robot_ids`.

        Raises:
            KeyError: If `plan_id`, or a non-None `since_plan_id`, is unknown.
        """
        with self._lock:
            plan = self._require_plan(plan_id)
            if since_plan_id is None or since_plan_id == plan_id:
                return plan.to_plan_state_context(())
            previous = self._require_plan(since_plan_id)
            churn = compute_plan_churn(previous.as_proposed_plan(), plan.as_proposed_plan())
            return plan.to_plan_state_context(churn.changed_robot_ids)

    def _require_plan(self, plan_id: int) -> TrackedPlan:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise KeyError(f"unknown plan_id {plan_id}")
        return plan

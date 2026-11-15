"""Pure plan-versus-dispatch comparison behind `plan_dispatch_mismatch_visibility`.

`command_grounder.plan_matches_dispatch` records one boolean per decision
(`PlanDispatchInfo.dispatch_matches_plan`) and nothing else: no tag, no log
line, and `plan.provenance` still reads `vlm_verbatim` when the dispatched
command moved a robot the accepted plan did not (decision `95066420`,
`docs/reports/2026-11-15-plan-dispatch-mismatch-visibility.md`). This module
says WHAT differs, per robot, so M5 can tag it, log it and record a corrected
provenance reading beside the untouched `plan.provenance`. It never changes a
command, a plan, a prompt or a provenance value.

Per robot, both sides are reduced to one action kind:

- dispatched: `command_grounder.project_dispatched_legs` (the same projection
  `plan_matches_dispatch` uses), refined in one place: the passer of a `yield`
  with `passer_escort_distance_m > 0` is `escort`, not `cross`. A withheld
  decision (`dispatch_withheld`) dispatches nothing (`continue` for all), and
  a robot the task-registry filter dropped gets `continue`.
- planned: the leg's action; a robot the plan does not name is `continue`.

Kinds belong to four classes: motion (`reverse`, `yield`, `reroute`),
pass (`cross`, `escort`), hold (`wait`) and none (`continue`). An `escort`
satisfies a `cross` leg; any other pair must be equal. A difference is:

- `unplanned_motion`: a motion command (or an escort) the leg did not ask for;
- `motion_differs`: the leg asked for one motion and got another;
- `planned_motion_not_sent`: the leg asked for a motion and got none;
- `hold_differs`: every other difference between pass, hold and none (a
  planned `wait` that was never sent, a `continue` robot held, a planned
  `cross` held on an unlinked wait).

Two differences are recorded as `excluded`, never as a mismatch, because a
registered reading already rules them a comparison artefact:

- a retreat-shield wait on a robot whose leg is `continue` (prereg-v3
  A27(iv), `plan_metrics.shield_excluded_dispatch_match`);
- a `junction_clear` recede order that differs from the plan's within the
  chi-epsilon equivalence class (`order_equivalent`, ruled 2026-10-03).

Summary items name a yielder or passer set that differs (`yielder_differs`,
`passer_differs`) and an order the plan defines that dispatch does not follow
(`order_differs`: a yield's `crossing_order` against the plan's `cross` legs;
a `junction_clear` recede order outside the equivalence class).
"""
from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.command_grounder import project_dispatched_legs
from reasoning.rag.retreat_shield import SHIELD_TAG

# Bumped whenever a rule above changes, so recorded blocks stay comparable.
DEFINITION_VERSION = 1
# The degradation-tag key (`command_grounder.DEGRADATION_TAGS`). Recorded only
# in the artifact's `plan_dispatch_mismatch.tags`, never appended to the
# command's own `degradations`: that list feeds the failure-explanation line
# of later prompts (`AttemptMemory.record`), which must not change.
OVERRIDE_TAG = "plan=overridden"

MismatchKind = Literal[
    "unplanned_motion",
    "motion_differs",
    "planned_motion_not_sent",
    "hold_differs",
    "yielder_differs",
    "passer_differs",
    "order_differs",
]
# Effect of one dispatch on one accepted-plan leg, for the leg-status record.
LegEffect = Literal["as_planned", "overridden", "not_sent"]

_MOTION = frozenset({"reverse", "yield", "reroute"})
_PASS = frozenset({"cross", "escort"})
_HOLD = frozenset({"wait"})
_NONE = "continue"
# Degradation tags that refuse a strategy as a whole and carry no robot id.
_REFUSAL_PREFIXES = (
    "reverse=infeasible",
    "yield=infeasible",
    "distances=unavailable",
    "strategy=unsupported",
)


def action_class(kind: str) -> str:
    """Return the class of one per-robot action kind.

    Args:
        kind: A plan leg action or a dispatched kind (`escort` included).

    Returns:
        `motion`, `pass`, `hold` or `none`. An unrecognised dispatched kind
        counts as `motion`: it is a command M4 executes.
    """
    if kind == _NONE:
        return "none"
    if kind in _HOLD:
        return "hold"
    if kind in _PASS:
        return "pass"
    return "motion"


def kinds_agree(planned: str, dispatched: str) -> bool:
    """Whether one robot's dispatched kind carries out its planned leg.

    Args:
        planned: The leg's action.
        dispatched: The dispatched kind.

    Returns:
        True when equal, or when an escorted passer carries out a `cross` leg.
    """
    return planned == dispatched or (planned == "cross" and dispatched == "escort")


class MismatchItem(BaseModel):
    """One difference between a plan and what was dispatched."""

    model_config = ConfigDict(frozen=True)

    kind: MismatchKind
    # The robot, or `yielder` / `passer` / `order` for a summary item.
    subject: str = Field(min_length=1)
    planned: str
    dispatched: str
    # Evidence for the difference: the withheld reason, `registry_dropped`,
    # the degradation tags naming the robot, the substituted wait's reason,
    # the strategy template's rule, or `unattributed`.
    reason: str


class ExcludedDifference(BaseModel):
    """A difference a registered reading rules a comparison artefact."""

    model_config = ConfigDict(frozen=True)

    subject: str = Field(min_length=1)
    planned: str
    dispatched: str
    rule: str


class PlanDispatchMismatch(BaseModel):
    """What differs between one decision's accepted plan and its dispatch."""

    model_config = ConfigDict(frozen=True)

    strategy: str
    matches: bool
    items: tuple[MismatchItem, ...] = ()
    excluded: tuple[ExcludedDifference, ...] = ()
    # Per robot: the dispatched kind, after the withheld / registry filter.
    dispatched: dict[str, str]
    # Per robot: the planned kind (`continue` for a robot the plan omits).
    planned: dict[str, str]
    withheld: str | None = None
    # The plain per-robot equality `plan_matches_dispatch` computes, over the
    # same legs and the command BEFORE withholding (absent legs unequal): the
    # fidelity check against the recorded `dispatch_matches_plan`.
    per_robot_equal: bool

    @property
    def kinds(self) -> tuple[MismatchKind, ...]:
        """The distinct mismatch kinds, in first-seen order."""
        return tuple(dict.fromkeys(item.kind for item in self.items))

    @property
    def robots(self) -> tuple[str, ...]:
        """The robots named by a per-robot mismatch item, in first-seen order."""
        return tuple(
            dict.fromkeys(item.subject for item in self.items if item.subject in self.planned)
        )

    def tags(self) -> list[str]:
        """The `plan=overridden:<strategy>:<subject>:<planned>-><dispatched>` tags."""
        return [
            f"{OVERRIDE_TAG}:{self.strategy}:{item.subject}:{item.planned}->{item.dispatched}"
            for item in self.items
        ]


def _leg_pairs(plan_legs: Sequence[Any]) -> list[tuple[str, str]]:
    pairs = []
    for leg in plan_legs:
        if isinstance(leg, Mapping):
            pairs.append((str(leg["robot_id"]), str(leg["action"])))
        else:
            pairs.append((leg.robot_id, leg.action))
    return pairs


def _escorted_passers(command: Mapping[str, Any]) -> set[str]:
    escorted = set()
    for action in command.get("actions", []):
        params = action.get("parameters") or {}
        if action.get("action") == "yield" and (params.get("passer_escort_distance_m") or 0) > 0:
            passer = params.get("passer_robot_id")
            if passer:
                escorted.add(str(passer))
    return escorted


def dispatched_kinds(
    command: Mapping[str, Any] | None, known_robot_ids: Sequence[str]
) -> dict[str, str]:
    """Project one dispatched command onto per-robot kinds, escorts refined.

    Args:
        command: The dispatched command, or None for nothing dispatched.
        known_robot_ids: Every robot of the scene.

    Returns:
        `{robot_id: kind}` for every known robot.
    """
    if not command:
        return dict.fromkeys(known_robot_ids, _NONE)
    projected = project_dispatched_legs(dict(command), known_robot_ids)
    for robot_id in _escorted_passers(command):
        if projected.get(robot_id) == "cross":
            projected[robot_id] = "escort"
    return projected


def _junction_dispatched_kinds(
    phases: Sequence[Mapping[str, Any]], known_robot_ids: Sequence[str]
) -> tuple[dict[str, str], list[str]]:
    # `command_grounder.junction_clear_dispatch_match`'s reconstruction: each
    # robot's kind from the phase that acts on it, a phase's held robots
    # excluded from its own contribution.
    kinds = dict.fromkeys(known_robot_ids, _NONE)
    order: list[str] = []
    for phase in phases:
        command = phase.get("command") or {}
        held = set(phase.get("held_robot_ids") or ())
        acted = {action["robot_id"] for action in command.get("actions", [])}
        for robot_id, kind in dispatched_kinds(command, known_robot_ids).items():
            if robot_id in acted and robot_id not in held:
                kinds[robot_id] = kind
        for action in command.get("actions", []):
            robot_id = action["robot_id"]
            if action["action"] == "reverse" and robot_id not in held and robot_id not in order:
                order.append(robot_id)
    return kinds, order


def _robot_tags(degradations: Sequence[str], robot_id: str) -> list[str]:
    tagged = []
    for tag in degradations:
        key, _, suffix = tag.partition(":")
        if key in ("grounding=node_handoff", "grounding=node_handoff_regrounded"):
            # `<arriver>-><occupant>`: the handoff explains only the occupant's
            # change (under `reverse` it is dropped from the reversing set).
            suffix = suffix.rpartition("->")[2]
        tokens = suffix.replace("->", ",").replace(":", ",").split(",")
        if robot_id in tokens:
            tagged.append(tag)
    return tagged


def _substitution_reason(command: Mapping[str, Any] | None, robot_id: str) -> str | None:
    for action in (command or {}).get("actions", []):
        params = action.get("parameters") or {}
        if action.get("robot_id") == robot_id and params.get("requested_strategy") is not None:
            return f"substituted:{params.get('reason') or params['requested_strategy']}"
    return None


def _template_reason(strategy: str, planned: str, dispatched: str) -> str | None:
    # The two legacy templates that never read the plan
    # (`command_grounder._ground_legacy`): `reverse` backs out every robot of
    # the view-filtered `involved_robots`, `reroute` reroutes its first robot
    # and waits the rest.
    if strategy == "reverse" and dispatched == "reverse":
        return "template:reverse_acts_on_involved_robots"
    if strategy == "reroute" and dispatched == "reroute":
        return "template:reroute_acts_on_first_involved_robot"
    if strategy == "reroute" and planned == "reroute" and dispatched == "wait":
        return "template:reroute_waits_the_other_involved_robots"
    return None


def _reason(
    strategy: str,
    robot_id: str,
    planned: str,
    dispatched: str,
    command: Mapping[str, Any] | None,
    degradations: Sequence[str],
    withheld: str | None,
    dropped: Collection[str],
) -> str:
    if withheld is not None:
        return f"withheld:{withheld}"
    if robot_id in dropped:
        return "registry_dropped"
    evidence = _robot_tags(degradations, robot_id)
    substituted = _substitution_reason(command, robot_id)
    if substituted is not None:
        evidence.extend(tag for tag in degradations if tag.startswith(_REFUSAL_PREFIXES))
        evidence.append(substituted)
    template = _template_reason(strategy, planned, dispatched)
    if template is not None:
        evidence.append(template)
    return "|".join(dict.fromkeys(evidence)) if evidence else "unattributed"


def _per_robot_kind(planned: str, dispatched: str) -> MismatchKind:
    planned_class, dispatched_class = action_class(planned), action_class(dispatched)
    if dispatched_class == "motion" or (dispatched == "escort" and planned != "cross"):
        return "motion_differs" if planned_class == "motion" else "unplanned_motion"
    if planned_class == "motion":
        return "planned_motion_not_sent"
    return "hold_differs"


def _role_items(
    planned: Mapping[str, str], dispatched: Mapping[str, str], strategy: str
) -> list[MismatchItem]:
    items = []
    planned_yielders = sorted(r for r, kind in planned.items() if kind == "yield")
    dispatched_yielders = sorted(r for r, kind in dispatched.items() if kind == "yield")
    if (planned_yielders or dispatched_yielders) and planned_yielders != dispatched_yielders:
        items.append(
            MismatchItem(
                kind="yielder_differs",
                subject="yielder",
                planned=",".join(planned_yielders) or "none",
                dispatched=",".join(dispatched_yielders) or "none",
                reason=f"strategy={strategy}",
            )
        )
    planned_passers = sorted(r for r, kind in planned.items() if kind == "cross")
    dispatched_passers = sorted(r for r, kind in dispatched.items() if kind in _PASS)
    if dispatched_yielders and planned_passers != dispatched_passers:
        items.append(
            MismatchItem(
                kind="passer_differs",
                subject="passer",
                planned=",".join(planned_passers) or "none",
                dispatched=",".join(dispatched_passers) or "none",
                reason=f"strategy={strategy}",
            )
        )
    return items


def _yield_crossing_order(command: Mapping[str, Any] | None) -> list[str] | None:
    for action in (command or {}).get("actions", []):
        order = (action.get("parameters") or {}).get("crossing_order")
        if action.get("action") == "yield" and order:
            return [str(robot_id) for robot_id in order]
    return None


def classify_plan_dispatch(
    strategy: str,
    plan_legs: Sequence[Any],
    command: Mapping[str, Any] | None,
    known_robot_ids: Sequence[str],
    *,
    withheld_reason: str | None = None,
    dropped_robot_ids: Collection[str] = (),
    junction_phases: Sequence[Mapping[str, Any]] | None = None,
    order_equivalent: bool = False,
) -> PlanDispatchMismatch:
    """Compare one decision's accepted plan with what M5 dispatches for it.

    Args:
        strategy: The decision's strategy.
        plan_legs: The legs the plan channel compares (`VerifiedPlan.legs`),
            as models or `{robot_id, action}` mappings.
        command: The command M5 fans out after the task-registry filter
            (`RegistryDispatch.command`, the artifact's `dispatched_command`);
            None when nothing was grounded or the filter refused it.
        known_robot_ids: Every robot of the decision's scene.
        withheld_reason: The `dispatch_withheld.reason`, when M5 withheld
            the command; nothing is then dispatched.
        dropped_robot_ids: Robots the task-registry filter removed.
        junction_phases: For a `junction_clear` sequence, every phase as a
            `{command, held_robot_ids}` mapping; `command` is then phase 0.
        order_equivalent: `PlanDispatchInfo.order_equivalent` (the chi-epsilon
            rule) for a `junction_clear` sequence.

    Returns:
        The per-robot items, the excluded artefacts and the overall verdict.
    """
    known = list(known_robot_ids)
    legs = _leg_pairs(plan_legs)
    plan_by_robot = dict(legs)
    planned = {robot_id: plan_by_robot.get(robot_id, _NONE) for robot_id in known}
    for robot_id, action in legs:
        planned.setdefault(robot_id, action)
    if junction_phases is not None:
        before_withhold, dispatched_order = _junction_dispatched_kinds(junction_phases, known)
        degradations = [
            tag
            for phase in junction_phases
            for tag in (phase.get("command") or {}).get("degradations") or []
        ]
    else:
        before_withhold = dispatched_kinds(command, known)
        dispatched_order = None
        degradations = list((command or {}).get("degradations") or [])
    for robot_id in planned:
        before_withhold.setdefault(robot_id, _NONE)
    # `project_dispatched_legs` has no `escort`: undo the refinement here.
    per_robot_equal = {
        r: "cross" if before_withhold[r] == "escort" else before_withhold[r] for r in known
    } == plan_by_robot
    dispatched = dict(before_withhold)
    dropped = set(dropped_robot_ids)
    for robot_id in dropped:
        dispatched[robot_id] = _NONE
    if withheld_reason is not None:
        dispatched = dict.fromkeys(dispatched, _NONE)
    shielded = {
        tag[len(SHIELD_TAG) + 1:] for tag in degradations if tag.startswith(f"{SHIELD_TAG}:")
    }
    items: list[MismatchItem] = []
    excluded: list[ExcludedDifference] = []
    for robot_id, planned_kind in planned.items():
        dispatched_kind = dispatched[robot_id]
        if kinds_agree(planned_kind, dispatched_kind):
            continue
        if (
            withheld_reason is None
            and robot_id in shielded
            and planned_kind == _NONE
            and dispatched_kind == "wait"
        ):
            excluded.append(
                ExcludedDifference(
                    subject=robot_id,
                    planned=planned_kind,
                    dispatched=dispatched_kind,
                    rule="retreat_shield_bystander:A27(iv)",
                )
            )
            continue
        items.append(
            MismatchItem(
                kind=_per_robot_kind(planned_kind, dispatched_kind),
                subject=robot_id,
                planned=planned_kind,
                dispatched=dispatched_kind,
                reason=_reason(
                    strategy,
                    robot_id,
                    planned_kind,
                    dispatched_kind,
                    command,
                    degradations,
                    withheld_reason,
                    dropped,
                ),
            )
        )
    items.extend(_role_items(planned, dispatched, strategy))
    plan_cross_order = [robot_id for robot_id, action in legs if action == "cross"]
    if junction_phases is not None:
        plan_recede = [robot_id for robot_id, action in legs if action == "reverse"]
        if (
            withheld_reason is None
            and dispatched_order is not None
            and sorted(plan_recede) == sorted(dispatched_order)
            and plan_recede != dispatched_order
        ):
            if order_equivalent:
                excluded.append(
                    ExcludedDifference(
                        subject="order",
                        planned=",".join(plan_recede),
                        dispatched=",".join(dispatched_order),
                        rule="junction_recede_order_epsilon",
                    )
                )
            else:
                items.append(
                    MismatchItem(
                        kind="order_differs",
                        subject="order",
                        planned=",".join(plan_recede),
                        dispatched=",".join(dispatched_order),
                        reason="junction_recede_order_outside_epsilon",
                    )
                )
    else:
        crossing = _yield_crossing_order(command)
        if (
            withheld_reason is None
            and crossing is not None
            and sorted(crossing) == sorted(plan_cross_order)
            and crossing != plan_cross_order
        ):
            items.append(
                MismatchItem(
                    kind="order_differs",
                    subject="order",
                    planned=",".join(plan_cross_order),
                    dispatched=",".join(crossing),
                    reason="yield_crossing_order",
                )
            )
    return PlanDispatchMismatch(
        strategy=strategy,
        matches=not items,
        items=tuple(items),
        excluded=tuple(excluded),
        dispatched=dispatched,
        planned=planned,
        withheld=withheld_reason,
        per_robot_equal=per_robot_equal,
    )


def dispatched_provenance(provenance: str, mismatch: PlanDispatchMismatch) -> str:
    """The corrected provenance reading recorded beside `plan.provenance`.

    Args:
        provenance: The verifier's `plan.provenance` (left untouched).
        mismatch: This decision's comparison.

    Returns:
        `overridden` for a `vlm_verbatim` plan whose dispatch differs from it;
        otherwise `provenance` unchanged (a `repaired` or `m3_default` plan
        already says it is not the model's plan as written).
    """
    if provenance == "vlm_verbatim" and not mismatch.matches:
        return "overridden"
    return provenance


def leg_effects(
    plan_legs: Sequence[Any], mismatch: PlanDispatchMismatch
) -> dict[str, tuple[LegEffect, str]]:
    """What one dispatch did to each leg of the plan it was attached to.

    Compared against the ACCEPTED plan's legs (on a hold, the active plan,
    statuses included), not against this decision's own verified legs: these
    are the legs M5's tracker will mark from M4's status reports.

    Args:
        plan_legs: The accepted plan's legs (`PlanDispatchInfo.legs`), each
            with `robot_id`, `action` and `status`.
        mismatch: This decision's comparison (its `dispatched` kinds are used).

    Returns:
        `{robot_id: (effect, dispatched_kind)}` for each leg this dispatch
        carried out (`as_planned`), contradicted (`overridden`) or skipped
        while the leg still waited for it (`not_sent`, leg `pending`). A leg
        this dispatch did not touch for another reason (already terminal, or
        a `continue` leg left alone) is absent.
    """
    effects: dict[str, tuple[LegEffect, str]] = {}
    for leg in plan_legs:
        robot_id = leg["robot_id"] if isinstance(leg, Mapping) else leg.robot_id
        action = leg["action"] if isinstance(leg, Mapping) else leg.action
        status = leg["status"] if isinstance(leg, Mapping) else leg.status
        dispatched_kind = mismatch.dispatched.get(robot_id, _NONE)
        if dispatched_kind != _NONE:
            effect: LegEffect = (
                "as_planned" if kinds_agree(action, dispatched_kind) else "overridden"
            )
            effects[robot_id] = (effect, dispatched_kind)
        elif action != _NONE and status == "pending":
            effects[robot_id] = ("not_sent", _NONE)
    return effects


class ReverseDispatch(BaseModel):
    """Whether a `reverse` decision's command backed robots out or was refused."""

    model_config = ConfigDict(frozen=True)

    status: Literal["executed", "refused", "withheld"]
    reversed_robot_ids: tuple[str, ...] = ()
    waiting_robot_ids: tuple[str, ...] = ()
    # The refusal's reason: the substituted waits' `reason`, the strategy's
    # refusal tags, or the withheld reason; None when executed.
    reason: str | None = None
    dispatched: str


def reverse_dispatch(
    strategy: str, command: Mapping[str, Any] | None, *, withheld_reason: str | None = None
) -> ReverseDispatch | None:
    """Tell an executed `reverse` from a refused one, from the command itself.

    A refused reverse goes out as `temporary_wait` actions with
    `requested_strategy: reverse` under the SAME `<request_id>-reverse`
    command id an executed one uses, so the `dispatch` log lines alone cannot
    tell them apart. Cv `6a05a618` shows the refusal can carry no tag at all
    (`degradations` absent), hence the action parameters are read first.

    Args:
        strategy: The decision's strategy.
        command: The command M5 fans out (or would, when withheld).
        withheld_reason: The `dispatch_withheld.reason`, when withheld.

    Returns:
        None unless `strategy == "reverse"` and a command exists.
    """
    if strategy != "reverse" or not command:
        return None
    actions = command.get("actions", [])
    reversed_ids = tuple(a["robot_id"] for a in actions if a.get("action") == "reverse")
    waiting = tuple(a["robot_id"] for a in actions if a.get("action") == "temporary_wait")
    if withheld_reason is not None:
        return ReverseDispatch(
            status="withheld",
            reversed_robot_ids=(),
            waiting_robot_ids=(),
            reason=withheld_reason,
            dispatched="none",
        )
    if reversed_ids:
        return ReverseDispatch(
            status="executed",
            reversed_robot_ids=reversed_ids,
            waiting_robot_ids=waiting,
            dispatched="reverse",
        )
    reasons = [
        str((a.get("parameters") or {}).get("reason"))
        for a in actions
        if (a.get("parameters") or {}).get("requested_strategy") == "reverse"
        and (a.get("parameters") or {}).get("reason")
    ]
    reasons.extend(
        tag for tag in command.get("degradations") or [] if tag.startswith(_REFUSAL_PREFIXES)
    )
    return ReverseDispatch(
        status="refused",
        waiting_robot_ids=waiting,
        reason="|".join(dict.fromkeys(reasons)) or "unattributed",
        dispatched="temporary_wait" if waiting else "none",
    )

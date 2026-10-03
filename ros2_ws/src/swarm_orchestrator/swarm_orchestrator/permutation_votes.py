"""Permutation voting over robot presentation order (prereg-v2 rev 6 apparatus; no rclpy).

The registered first-slot / robot_1 presentation-order prior (2026-09-25
presentation-order finding) is cancelled per decision rather than per
dataset: the SAME request is rendered under N cyclic shifts of its robot
presentation order, each shift is a complete, ordinary `Reasoner.run` call
(its own attempts, re-asks and refusal mitigation, exactly the single-call
policy), and the decision is majority-voted.

Vote: the tuple (congestion_detected, type, strategy, yield_robot). Calls
whose decision is None (exhausted retries, refusals) abstain.

Tie rule (registered, per the brief): among the keys tied for the most
votes, the key voted by the call whose RENDERED order matches the registry
order wins -- M5's task-registry robot order (`initial_tasks` order,
restricted to the request's robots; robots the registry does not name
follow in ascending id). Fallback, so the rule is total: when no tied call
rendered the registry order (it abstained, or no cyclic shift of the drawn
base equals it -- possible with 3+ robots under a `random` or `id_desc`
draw), the key held by the EARLIEST call wins (call 0 is the drawn order).
`tie_resolved_by` records which branch fired.

The winning call's `ReasonerResult` is returned whole: `proposed_plan`,
`reasoning`, `root_cause`, `justification`, `crossing_order` and
`blocker_kind` are that one call's answer, never merged across calls.

With fewer robots than votes the shifts wrap (`k mod n`): a two-robot scene
under three votes renders [A, B], [B, A], [A, B] -- the base order twice.
`distinct_orders` records this so the effective counterbalancing is
visible per decision.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
)
from reasoning.vlm.prompt_builder import build_prompt_payload, order_robot_states

TIE_RULE = "registry_order_call_first:fallback_earliest_call"


class _Runs(Protocol):
    def run(self, request: ReasonerRequest) -> ReasonerResult: ...


class VoteKey(BaseModel):
    """The fields a permutation vote is taken on."""

    model_config = ConfigDict(frozen=True)

    congestion_detected: bool
    type: str
    strategy: str
    yield_robot: str | None = None


class PermutationCall(BaseModel):
    """One shifted call of a permutation vote, as recorded in the artifact."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    shift: int = Field(ge=0)
    order: tuple[str, ...]
    system_sha256: str
    user_sha256: str
    vote: VoteKey | None
    decision: CongestionDecision | None
    raw_text: str | None
    diagnostics: ReasonerDiagnostics


class VoteCount(BaseModel):
    """How many calls cast one vote key, and which."""

    model_config = ConfigDict(frozen=True)

    vote: VoteKey
    count: int = Field(ge=1)
    call_indices: tuple[int, ...]


class PermutationVoteRecord(BaseModel):
    """The `permutation_votes` artifact block."""

    model_config = ConfigDict(frozen=True)

    votes_requested: int = Field(ge=1)
    distinct_orders: int = Field(ge=1)
    tie_rule: str = TIE_RULE
    # None when every call abstained (the outcome is then call 0's failure).
    winner_index: int | None
    winner_vote: VoteKey | None
    tie_broken: bool
    # The registry order the tie rule looks for, and which branch resolved a
    # tie: "registry_order", "earliest_call" (fallback), or None (no tie).
    registry_order: tuple[str, ...] | None = None
    tie_resolved_by: str | None = None
    vote_counts: list[VoteCount]
    # Sum of every call's backend attempts: the realised cost multiplier.
    total_backend_attempts: int = Field(ge=0)
    calls: list[PermutationCall]


def cyclic_shift_orders(base_order: list[str], votes: int) -> list[tuple[str, ...]]:
    """Return the `votes` cyclic shifts of a presentation order, shift 0 first.

    Args:
        base_order: Robot ids in the request's own presentation order.
        votes: Number of calls.

    Returns:
        One order per call; shift k is `base[k mod n:] + base[:k mod n]`.
    """
    n = len(base_order)
    if n == 0:
        return [() for _ in range(votes)]
    return [tuple(base_order[k % n :] + base_order[: k % n]) for k in range(votes)]


def vote_key(decision: CongestionDecision | None) -> VoteKey | None:
    """Project a decision onto the voted fields; None abstains."""
    if decision is None:
        return None
    return VoteKey(
        congestion_detected=decision.congestion_detected,
        type=decision.type,
        strategy=decision.strategy,
        yield_robot=decision.yield_robot,
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def shifted_request(
    request: ReasonerRequest, order: tuple[str, ...], shift: int
) -> ReasonerRequest:
    """The request one call of the vote sends.

    Args:
        request: The episode's request (call 0, unchanged).
        order: This call's explicit presentation order.
        shift: This call's shift index; 0 returns `request` itself so call 0's
            prompt is byte-identical to the single-call condition's.

    Returns:
        The request with its presentation order replaced (shift > 0).
    """
    if shift == 0:
        return request
    return request.model_copy(update={"robot_presentation_order": order})


def registry_presentation_order(
    registry_order: tuple[str, ...] | list[str], robot_ids: list[str]
) -> tuple[str, ...]:
    """The registry order restricted to a request's robots.

    Args:
        registry_order: M5's task-registry robot ids, in registry order.
        robot_ids: The request's robots.

    Returns:
        Registry-named robots in registry order, then the rest in ascending id.
    """
    present = set(robot_ids)
    named = [rid for rid in registry_order if rid in present]
    return tuple(named + sorted(present - set(named)))


def run_permutation_votes(
    reasoner: _Runs,
    request: ReasonerRequest,
    votes: int,
    registry_order: tuple[str, ...] | list[str] | None = None,
) -> tuple[ReasonerResult, PermutationVoteRecord, ReasonerRequest]:
    """Run one decision as `votes` presentation-order-shifted calls and vote.

    Calls run sequentially on the caller's (worker) thread, so the worst-case
    wall time is `votes x max_attempts x timeout_sec`.

    Args:
        reasoner: The stage-1 reasoner (`Reasoner.run`).
        request: The episode's request; its order is shift 0.
        votes: Number of calls (>= 1).
        registry_order: M5's task-registry robot order for the tie rule;
            None skips the registry branch (earliest call breaks ties).

    Returns:
        `(winning result, vote record, winning call's request)`. With no
        voting call, call 0's failed result and request.

    Raises:
        ValueError: If `votes` < 1, or as `Reasoner.run` raises for invalid input.
    """
    if votes < 1:
        raise ValueError(f"votes must be >= 1, got {votes}")
    base = [
        s.robot_id
        for s in order_robot_states(request.robot_states, request.robot_presentation_order)
    ]
    orders = cyclic_shift_orders(base, votes)
    calls: list[PermutationCall] = []
    results: list[ReasonerResult] = []
    requests: list[ReasonerRequest] = []
    for index, order in enumerate(orders):
        call_request = shifted_request(request, order, index)
        payload = build_prompt_payload(call_request)
        result = reasoner.run(call_request)
        results.append(result)
        requests.append(call_request)
        calls.append(
            PermutationCall(
                index=index,
                shift=index % max(1, len(base)),
                order=order,
                system_sha256=_sha256(payload.system_prompt),
                user_sha256=_sha256(payload.user_prompt),
                vote=vote_key(result.decision),
                decision=result.decision,
                raw_text=result.raw_text,
                diagnostics=result.diagnostics,
            )
        )
    tally: Counter[VoteKey] = Counter(call.vote for call in calls if call.vote is not None)
    first_index: dict[VoteKey, int] = {}
    for call in calls:
        if call.vote is not None:
            first_index.setdefault(call.vote, call.index)
    counts = sorted(
        (
            VoteCount(
                vote=key,
                count=count,
                call_indices=tuple(c.index for c in calls if c.vote == key),
            )
            for key, count in tally.items()
        ),
        key=lambda vc: (-vc.count, first_index[vc.vote]),
    )
    target = (
        None
        if registry_order is None
        else registry_presentation_order(registry_order, [s.robot_id for s in request.robot_states])
    )
    winner_index: int | None = None
    winner_vote: VoteKey | None = None
    tie_broken = False
    tie_resolved_by: str | None = None
    if counts:
        top = counts[0].count
        tied = [vc for vc in counts if vc.count == top]
        tie_broken = len(tied) > 1
        winner_vote = tied[0].vote
        winner_index = first_index[winner_vote]
        if tie_broken:
            tied_votes = {vc.vote for vc in tied}
            registry_call = next(
                (
                    call
                    for call in calls
                    if target is not None and call.order == target and call.vote in tied_votes
                ),
                None,
            )
            if registry_call is not None:
                winner_vote, winner_index = registry_call.vote, registry_call.index
                tie_resolved_by = "registry_order"
            else:
                tie_resolved_by = "earliest_call"
    record = PermutationVoteRecord(
        votes_requested=votes,
        distinct_orders=len(set(orders)),
        winner_index=winner_index,
        winner_vote=winner_vote,
        tie_broken=tie_broken,
        registry_order=target,
        tie_resolved_by=tie_resolved_by,
        vote_counts=counts,
        total_backend_attempts=sum(call.diagnostics.attempts for call in calls),
        calls=calls,
    )
    chosen = 0 if winner_index is None else winner_index
    return results[chosen], record, requests[chosen]


def permutation_votes_log(request_id: str, record: PermutationVoteRecord) -> str:
    """One structured log line summarising a vote."""
    votes: list[Any] = [
        None if call.vote is None else f"{call.vote.strategy}/{call.vote.yield_robot}"
        for call in record.calls
    ]
    return (
        f"permutation votes request={request_id} n={record.votes_requested} "
        f"distinct_orders={record.distinct_orders} votes={votes} "
        f"winner={record.winner_index} tie_broken={record.tie_broken} "
        f"attempts={record.total_backend_attempts}"
    )

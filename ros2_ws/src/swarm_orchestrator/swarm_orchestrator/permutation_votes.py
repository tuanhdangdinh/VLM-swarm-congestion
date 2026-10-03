"""Permutation voting over robot presentation order (prereg-v2 rev 6 apparatus; no rclpy).

The registered first-slot / robot_1 presentation-order prior (2026-09-25
presentation-order finding) is cancelled per decision rather than per
dataset: the SAME request is rendered under N cyclic shifts of its robot
presentation order, each shift is a complete, ordinary `Reasoner.run` call
(its own attempts, re-asks and refusal mitigation, exactly the single-call
policy), and the decision is majority-voted.

Vote: the tuple (congestion_detected, type, strategy, yield_robot). Calls
whose decision is None (exhausted retries, refusals) abstain.

Ballot rule (apparatus ruling, 2026-10-04): the majority is taken over
DISTINCT rendered orders, one ballot each. With fewer robots than votes the
shifts wrap (`k mod n`): a two-robot scene under three votes renders
[A, B], [B, A], [A, B], so the base order is rendered twice. A duplicated
order's voting calls are reconciled first: if they agree on the voted
fields, the order casts ONE ballot; if any two disagree, the order casts NO
ballot and the record sets `intra_order_inconsistency` with the disagreeing
call indices (a measured T=0 same-prompt divergence). An abstaining call is
not a disagreement: the order's ballot is reconciled over the calls that
voted, and an order whose calls all abstained casts no ballot. Each ballot
is represented by its earliest voting call.

Tie rule (REVISED 2026-10-04): among the keys tied for the most ballots,
the EARLIEST tied ballot's representative call wins, full stop. Call 0 is
the episode's randomized draw, so this is unbiased across episodes and
deterministic within one. The former registry-order preference is dropped:
the registry order is id_asc, the rendering the presentation-order finding
tied to the first-slot/robot_1 priors, so preferring it would resolve every
two-robot inter-order disagreement toward the biased order. The registry
order is still recorded (`registry_order`) but never decides anything.

The winning ballot's representative call's `ReasonerResult` is returned
whole: `proposed_plan`, `reasoning`, `root_cause`, `justification`,
`crossing_order` and `blocker_kind` are that one call's answer, never merged
across calls. When no ballot survives, the returned result has
`decision=None`, so nothing is grounded or dispatched.
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

TIE_RULE = "earliest_tied_ballot"
BALLOT_RULE = "one_ballot_per_distinct_order:duplicates_reconciled_disagreement_voids"
NO_BALLOT_ERROR = "permutation_vote_no_ballot"


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


class Ballot(BaseModel):
    """One distinct rendered order's reconciled ballot."""

    model_config = ConfigDict(frozen=True)

    order: tuple[str, ...]
    vote: VoteKey
    # Every voting call of this order (all agree); abstaining calls excluded.
    call_indices: tuple[int, ...]
    # The earliest voting call: its result is returned if this ballot wins.
    representative_index: int = Field(ge=0)


class OrderInconsistency(BaseModel):
    """A duplicated order whose voting calls disagreed, so it cast no ballot."""

    model_config = ConfigDict(frozen=True)

    order: tuple[str, ...]
    call_indices: tuple[int, ...]


class VoteCount(BaseModel):
    """How many ballots one vote key received, and from which calls."""

    model_config = ConfigDict(frozen=True)

    vote: VoteKey
    # Ballots (distinct orders), not calls.
    count: int = Field(ge=1)
    # Every call behind those ballots, duplicated-order calls included.
    call_indices: tuple[int, ...]


class PermutationVoteRecord(BaseModel):
    """The `permutation_votes` artifact block."""

    model_config = ConfigDict(frozen=True)

    votes_requested: int = Field(ge=1)
    distinct_orders: int = Field(ge=1)
    ballot_rule: str = BALLOT_RULE
    tie_rule: str = TIE_RULE
    # None when no ballot survived (every call abstained, or every order
    # that voted was intra-order inconsistent); the outcome is then a
    # decision=None result.
    winner_index: int | None
    winner_vote: VoteKey | None
    tie_broken: bool
    # M5's registry order, recorded for analysis only (it decides nothing),
    # and "earliest_call" when a tie was broken, else None.
    registry_order: tuple[str, ...] | None = None
    tie_resolved_by: str | None = None
    ballots: list[Ballot] = Field(default_factory=list)
    # Always written: False is a measurement, not an absent field.
    intra_order_inconsistency: bool = False
    inconsistent_orders: list[OrderInconsistency] = Field(default_factory=list)
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
        registry_order: M5's task-registry robot order, recorded on the
            record only; it never affects the outcome (revised tie rule).

    Returns:
        `(winning result, vote record, winning call's request)`: the winning
        ballot's representative call. With no surviving ballot, a
        decision=None result (call 0's own failure when every call
        abstained) and call 0's request.

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
    ballots, inconsistent = reconcile_ballots(calls)
    target = (
        None
        if registry_order is None
        else registry_presentation_order(registry_order, [s.robot_id for s in request.robot_states])
    )
    winner, tie_broken, tie_resolved_by = _elect(ballots)
    counts = _vote_counts(ballots)
    record = PermutationVoteRecord(
        votes_requested=votes,
        distinct_orders=len(set(orders)),
        winner_index=None if winner is None else winner.representative_index,
        winner_vote=None if winner is None else winner.vote,
        tie_broken=tie_broken,
        registry_order=target,
        tie_resolved_by=tie_resolved_by,
        ballots=ballots,
        intra_order_inconsistency=bool(inconsistent),
        inconsistent_orders=inconsistent,
        vote_counts=counts,
        total_backend_attempts=sum(call.diagnostics.attempts for call in calls),
        calls=calls,
    )
    if winner is not None:
        chosen = winner.representative_index
        return results[chosen], record, requests[chosen]
    return _no_ballot_result(results[0], inconsistent), record, requests[0]


def reconcile_ballots(
    calls: list[PermutationCall],
) -> tuple[list[Ballot], list[OrderInconsistency]]:
    """Reduce the calls to one ballot per distinct rendered order.

    Args:
        calls: Every call of the vote, in call order.

    Returns:
        `(ballots, inconsistencies)`: ballots sorted by representative call,
        inconsistencies in order of first call. An order whose voting calls
        agree casts one ballot; one whose voting calls disagree casts none and
        is listed as inconsistent; one whose calls all abstained appears in
        neither.
    """
    by_order: dict[tuple[str, ...], list[PermutationCall]] = {}
    for call in calls:
        by_order.setdefault(call.order, []).append(call)
    ballots: list[Ballot] = []
    inconsistent: list[OrderInconsistency] = []
    for order, group in by_order.items():
        voting = [call for call in group if call.vote is not None]
        if not voting:
            continue
        indices = tuple(call.index for call in voting)
        if len({call.vote for call in voting}) > 1:
            inconsistent.append(OrderInconsistency(order=order, call_indices=indices))
            continue
        ballots.append(
            Ballot(
                order=order,
                vote=voting[0].vote,
                call_indices=indices,
                representative_index=voting[0].index,
            )
        )
    ballots.sort(key=lambda ballot: ballot.representative_index)
    return ballots, inconsistent


def _elect(ballots: list[Ballot]) -> tuple[Ballot | None, bool, str | None]:
    """Majority over ballots; a tie goes to the earliest tied ballot. `(winner, tied, branch)`."""
    if not ballots:
        return None, False, None
    tally = Counter(ballot.vote for ballot in ballots)
    top = max(tally.values())
    tied_votes = {vote for vote, count in tally.items() if count == top}
    # Ballots are sorted by representative call, so the first is the earliest.
    winner = next(ballot for ballot in ballots if ballot.vote in tied_votes)
    if len(tied_votes) == 1:
        return winner, False, None
    return winner, True, "earliest_call"


def _vote_counts(ballots: list[Ballot]) -> list[VoteCount]:
    first: dict[VoteKey, int] = {}
    for ballot in ballots:
        first.setdefault(ballot.vote, ballot.representative_index)
    return sorted(
        (
            VoteCount(
                vote=vote,
                count=sum(1 for b in ballots if b.vote == vote),
                call_indices=tuple(
                    sorted(i for b in ballots if b.vote == vote for i in b.call_indices)
                ),
            )
            for vote in first
        ),
        key=lambda vc: (-vc.count, first[vc.vote]),
    )


def _no_ballot_result(
    call_zero: ReasonerResult, inconsistent: list[OrderInconsistency]
) -> ReasonerResult:
    """Call 0's failure, or -- when calls voted but no ballot survived -- a decision=None result.

    The voided calls' own decisions stay in the record's `calls`; none is
    returned, so the pipeline cannot ground or dispatch a voided decision.
    """
    if call_zero.decision is None and not inconsistent:
        return call_zero
    voided = [list(item.call_indices) for item in inconsistent]
    diagnostics = call_zero.diagnostics.model_copy(
        update={
            "error_type": NO_BALLOT_ERROR,
            "error_message": f"no order cast a ballot; intra-order inconsistent calls {voided}",
        }
    )
    return call_zero.model_copy(
        update={"decision": None, "raw_text": None, "diagnostics": diagnostics}
    )


def permutation_votes_log(request_id: str, record: PermutationVoteRecord) -> str:
    """One structured log line summarising a vote."""
    votes: list[Any] = [
        None if call.vote is None else f"{call.vote.strategy}/{call.vote.yield_robot}"
        for call in record.calls
    ]
    return (
        f"permutation votes request={request_id} n={record.votes_requested} "
        f"distinct_orders={record.distinct_orders} votes={votes} "
        f"ballots={len(record.ballots)} "
        f"intra_order_inconsistency={record.intra_order_inconsistency} "
        f"winner={record.winner_index} tie_broken={record.tie_broken} "
        f"attempts={record.total_backend_attempts}"
    )

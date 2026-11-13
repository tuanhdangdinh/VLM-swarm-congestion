"""Command lifecycle and cooldown tracking for M5 (no rclpy)."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple

from reasoning.vlm.models import RefusedProposal

_TERMINAL = frozenset({"COMPLETED", "FAILED", "TIMED_OUT"})
_STATUS_MAP = {
    "active": "ACTIVE",
    "completed": "COMPLETED",
    "failed": "FAILED",
}


class CommandState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass
class CommandRecord:
    """Bookkeeping for one dispatched coordination command (multi-robot)."""

    command_id: str
    robot_ids: list[str]
    dispatched_at: float
    timeout_sec: float
    fallback: str
    request_id: str
    robot_states: dict[str, CommandState] = field(default_factory=dict)
    # Per-robot dispatched action name, read back when the command resolves
    # (the failure-explanation line names the leg that failed).
    actions: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.robot_states:
            self.robot_states = {rid: CommandState.PENDING for rid in self.robot_ids}


class CommandTracker:
    """Tracks per-robot lifecycle for dispatched commands and detects timeouts."""

    def __init__(self) -> None:
        self._records: dict[str, CommandRecord] = {}

    def register(self, record: CommandRecord) -> None:
        self._records[record.command_id] = record

    def state_of(self, command_id: str, robot_id: str) -> CommandState | None:
        record = self._records.get(command_id)
        return None if record is None else record.robot_states.get(robot_id)

    def apply_status(self, command_id: str, robot_id: str, status: str) -> None:
        """Apply an M4 status string to a robot; unknown strings are ignored."""
        record = self._records.get(command_id)
        if record is None or robot_id not in record.robot_states:
            return
        mapped = _STATUS_MAP.get(status.lower())
        if mapped is None:
            return
        record.robot_states[robot_id] = CommandState[mapped]

    def is_resolved(self, command_id: str) -> bool:
        record = self._records.get(command_id)
        if record is None:
            return False
        return all(s.name in _TERMINAL for s in record.robot_states.values())

    def robots_of(self, command_id: str) -> list[str]:
        record = self._records.get(command_id)
        return [] if record is None else list(record.robot_ids)

    def actions_of(self, command_id: str) -> dict[str, str]:
        """Return the per-robot dispatched action names of a command (empty if unknown)."""
        record = self._records.get(command_id)
        return {} if record is None else dict(record.actions)

    def fallback_of(self, command_id: str) -> str | None:
        record = self._records.get(command_id)
        return None if record is None else record.fallback

    def check_timeouts(self, now: float) -> list[str]:
        """Mark unresolved commands past their deadline TIMED_OUT; return their ids.

        A command with any robot ACTIVE is never timed out here: M4 guarantees
        every ACTIVE command terminates on its own (backup has an
        odometry-progress safety deadline, wait/hold use bounded timers), so
        liveness is delegated to M4. Only a command whose non-terminal robots
        are all still PENDING past the deadline is expired, which covers a
        lost dispatch that M4 never received.
        """
        timed_out: list[str] = []
        for command_id, record in self._records.items():
            if self.is_resolved(command_id):
                continue
            has_active = any(
                state is CommandState.ACTIVE for state in record.robot_states.values()
            )
            if has_active:
                continue
            if now - record.dispatched_at >= record.timeout_sec:
                for rid, state in record.robot_states.items():
                    if state.name not in _TERMINAL:
                        record.robot_states[rid] = CommandState.TIMED_OUT
                timed_out.append(command_id)
        return timed_out


class CooldownTracker:
    """Single owner of per-robot re-trigger cooldowns (FR5.2.2)."""

    def __init__(self, cooldown_sec: float) -> None:
        self._cooldown_sec = cooldown_sec
        self._until: dict[str, float] = {}

    def start(self, robot_ids: list[str], now: float) -> None:
        deadline = now + self._cooldown_sec
        for rid in robot_ids:
            self._until[rid] = deadline

    def active_robots(self, now: float) -> set[str]:
        return {rid for rid, until in self._until.items() if until > now}


def summarize_outcome(states: dict[str, CommandState]) -> str:
    """Collapse per-robot terminal states into one attempt outcome.

    Callers must pass terminal states only (`_resolve_command` runs once every
    robot is COMPLETED, FAILED or TIMED_OUT); non-terminal states are not
    distinguished from COMPLETED here.

    Args:
        states: Terminal `CommandState` per robot of a resolved command.

    Returns:
        `"timed_out"` if any robot timed out, else `"failed"` if any failed,
        else `"completed"`.
    """
    values = set(states.values())
    if CommandState.TIMED_OUT in values:
        return "timed_out"
    if CommandState.FAILED in values:
        return "failed"
    return "completed"


def summarize_executed_strategy(actions: list[str], strategy: str) -> str | None:
    """Name the maneuver M3 actually fanned out, as opposed to the decided strategy.

    A strategy normally fans out as its own action for the lead robot plus
    `temporary_wait` for the others (yield/reroute), so the decided strategy's
    action being present means it ran as decided. A strategy M3 refused fans
    out without that action — a refused yield as `temporary_wait` for everyone —
    and is named by what ran instead.

    Args:
        actions: The per-robot action names of one grounded command.
        strategy: The decided strategy the command was grounded from.

    Returns:
        `strategy` if any action equals it, else the single action name when all
        agree, else `"mixed"`; `None` when there are no actions.
    """
    if not actions:
        return None
    if strategy in actions:
        return strategy
    distinct = set(actions)
    return actions[0] if len(distinct) == 1 else "mixed"


@dataclass
class AttemptRecord:
    """The last dispatched coordination attempt, kept for re-analysis context."""

    command_id: str
    robot_ids: list[str]
    strategy: str
    yield_robot: str | None
    dispatched_at: float
    resolved_at: float | None = None
    outcome_status: str | None = None
    executed_strategy: str | None = None
    # Failure-explanation sources (prereg-v3 R3.4), all already in M5's
    # lifecycle or the decision artifact; read only behind
    # `failure_explanation_enabled`. Per robot of the command that resolved
    # the attempt (the last phase, for a junction_clear sequence):
    # `(action, terminal CommandState value)`.
    leg_outcomes: dict[str, tuple[str | None, str]] = field(default_factory=dict)
    # The artifact's `yield_refusal_reason` and `grounding_degradations`.
    refusal_reason: str | None = None
    degradations: list[str] = field(default_factory=list)
    # Robots whose Nav2 arrival M5 rejected after this attempt was dispatched,
    # with M1's distance from the goal (None when M1 had no estimate).
    arrival_rejections: dict[str, float | None] = field(default_factory=dict)


class AttemptContexts(NamedTuple):
    """The attempts a new analysis is told about (failure-context depth policy)."""

    # The most recent resolved attempt, or None when there is nothing to report.
    latest: AttemptRecord | None
    # The most recent failed attempt when it is not `latest`; None when `latest`
    # is itself the failure, or when nothing has failed.
    last_failed: AttemptRecord | None


def _is_failure(record: AttemptRecord) -> bool:
    # Any resolved non-completed outcome: summarize_outcome ranks timed_out above
    # failed, so a command where one robot FAILED and another TIMED_OUT reports
    # timed_out and must still count.
    return record.resolved_at is not None and record.outcome_status != "completed"


class AttemptMemory:
    """Memory of the latest attempt plus the latest failed one (rev-8 A.1).

    One in-flight slot is enough because the state machine allows a single
    in-flight cycle. The latest record becomes visible only after `resolve`,
    stays visible for `window_sec` after resolution for any overlapping robot
    set, and is dropped on expiry, on an analysis for a disjoint robot set (no
    cross-episode memory), or when a new attempt is recorded.

    A failed attempt superseded by a newer one is kept in a second slot, so a
    later successful maneuver cannot displace it from the prompt (runs
    20260924_201328 and L4 re-yielded the same infeasible robot once a completed
    `temporary_wait` had displaced the failed yield). It lives exactly as long
    as the latest record: it is dropped together with it, and its own
    resolution time does not start a separate window. `window_sec <= 0`
    disables the memory.
    """

    def __init__(self, window_sec: float) -> None:
        self._window_sec = window_sec
        self._record: AttemptRecord | None = None
        self._last_failed: AttemptRecord | None = None
        # Queued followers folded into the current episode (T2b): their later
        # analysis overlaps the remembered attempt although no command named
        # them. Dropped with the memory.
        self._folded: set[str] = set()

    def fold(self, robot_ids: list[str]) -> None:
        """Count a queued follower as part of the remembered attempt's scope.

        Args:
            robot_ids: The follower folded into the in-flight episode.
        """
        if self._record is not None:
            self._folded |= set(robot_ids)

    def record(
        self,
        command_id: str,
        robot_ids: list[str],
        strategy: str,
        yield_robot: str | None,
        now: float,
        executed_strategy: str | None = None,
        refusal_reason: str | None = None,
        degradations: list[str] | None = None,
    ) -> None:
        """Remember a freshly dispatched attempt, superseding any earlier one.

        A superseded attempt that resolved as a failure becomes the remembered
        last failed attempt, replacing any older failure. `refusal_reason` and
        `degradations` are M3's yield refusal and degradation tags for the
        grounded command, kept for the failure-explanation line.
        """
        if self._record is not None and _is_failure(self._record):
            self._last_failed = self._record
        self._record = AttemptRecord(
            command_id=command_id,
            robot_ids=list(robot_ids),
            strategy=strategy,
            yield_robot=yield_robot,
            dispatched_at=now,
            executed_strategy=executed_strategy,
            refusal_reason=refusal_reason,
            degradations=list(degradations or []),
        )

    def resolve(
        self,
        command_id: str,
        outcome_status: str,
        now: float,
        leg_outcomes: dict[str, tuple[str | None, str]] | None = None,
    ) -> None:
        """Finalize the remembered attempt; a superseded command id is ignored.

        Re-entrant: the node resolves a command once per status message after it
        turns terminal, so only the first call stamps `resolved_at` (the window and
        the elapsed-seconds wording are measured from the first resolution) while
        `outcome_status` (and `leg_outcomes`, when given) keep the latest value.
        """
        if self._record is None or self._record.command_id != command_id:
            return
        if self._record.resolved_at is None:
            self._record.resolved_at = now
        self._record.outcome_status = outcome_status
        if leg_outcomes is not None:
            self._record.leg_outcomes = dict(leg_outcomes)

    def note_arrival_rejection(self, robot_id: str, distance_m: float | None) -> None:
        """Record that M5 rejected a Nav2 arrival for a robot of the remembered attempt.

        Args:
            robot_id: The robot whose arrival was rejected.
            distance_m: M1's distance from the goal, or None without an estimate.
        """
        if self._record is not None and robot_id in self._record.robot_ids:
            self._record.arrival_rejections[robot_id] = distance_m

    def context_for(self, robot_ids: list[str], now: float) -> AttemptRecord | None:
        """Return the resolved attempt relevant to a new analysis, or None."""
        return self.contexts_for(robot_ids, now).latest

    def contexts_for(self, robot_ids: list[str], now: float) -> AttemptContexts:
        """Return the latest attempt and, when different, the latest failed one.

        Args:
            robot_ids: Robots the new analysis involves.
            now: Monotonic time of the new analysis.

        Returns:
            `AttemptContexts`; `last_failed` is set only when `latest` is set,
            is not itself a failure, and the failed attempt overlaps `robot_ids`.
        """
        record = self._record
        if record is None or record.resolved_at is None:
            return AttemptContexts(None, None)
        expired = self._window_sec <= 0.0 or now - record.resolved_at > self._window_sec
        if expired or not set(robot_ids) & (set(record.robot_ids) | self._folded):
            self._record = None
            self._last_failed = None
            self._folded = set()
            return AttemptContexts(None, None)
        failed = self._last_failed
        if _is_failure(record) or failed is None or not set(robot_ids) & set(failed.robot_ids):
            return AttemptContexts(record, None)
        return AttemptContexts(record, failed)


# Stored withheld proposals per shown entry: expiry bounds the memory in time,
# this bounds it in size when many disjoint robot sets are refused at once.
_WITHHELD_STORE_FACTOR = 4


@dataclass
class _WithheldEntry:
    proposal: RefusedProposal
    robot_ids: frozenset[str]
    recorded_at: float


class WithheldMemory:
    """Decisions M5 withheld, for the next prompt about an overlapping robot set.

    v4 refusal feedback (Change 2). `AttemptMemory` remembers only dispatched
    attempts, so a withheld decision (`dispatch_withheld`) left no trace in
    the next prompt. This keeps the most recent ones: identical proposals
    (strategy, involved robots, yielder, reason) fold into one entry whose
    `times` counts them and whose expiry restarts; an entry expires
    `window_sec` after its latest repeat, or at once when M5 dispatches to an
    overlapping robot set (the scene the refusal was about has been acted on).
    A query for a disjoint set neither shows nor drops an entry.
    """

    def __init__(self, window_sec: float, max_entries: int) -> None:
        self._window_sec = window_sec
        self._max_entries = max_entries
        self._entries: list[_WithheldEntry] = []

    def __len__(self) -> int:
        return len(self._entries)

    def record(self, proposal: RefusedProposal, robot_ids: Iterable[str], now: float) -> None:
        """Remember one withheld decision, folding it into an identical earlier one.

        Args:
            proposal: The decision as the prompt will state it (`times` ignored).
            robot_ids: The robots it concerns (involved plus would-be commanded).
            now: Monotonic time of the outcome.
        """
        key = proposal.model_copy(update={"times": 1})
        times = 1
        kept: list[_WithheldEntry] = []
        for entry in self._entries:
            if entry.proposal.model_copy(update={"times": 1}) == key:
                times += entry.proposal.times
            else:
                kept.append(entry)
        kept.append(
            _WithheldEntry(
                proposal=key.model_copy(update={"times": times}),
                robot_ids=frozenset(robot_ids) | frozenset(proposal.involved_robots),
                recorded_at=now,
            )
        )
        self._entries = kept[-self._max_entries * _WITHHELD_STORE_FACTOR :]

    def forget_overlapping(self, robot_ids: Iterable[str]) -> int:
        """Drop every entry sharing a robot with a dispatched command.

        Args:
            robot_ids: The robots M5 just dispatched to.

        Returns:
            How many entries were dropped.
        """
        robots = set(robot_ids)
        kept = [entry for entry in self._entries if not entry.robot_ids & robots]
        dropped = len(self._entries) - len(kept)
        self._entries = kept
        return dropped

    def proposals_for(self, robot_ids: Iterable[str], now: float) -> list[RefusedProposal]:
        """The withheld proposals to state for a new analysis, oldest first.

        Args:
            robot_ids: Robots the new analysis involves.
            now: Monotonic time of the new analysis.

        Returns:
            At most `max_entries` unexpired proposals sharing a robot with
            `robot_ids`, the most recent ones, in recording order.
        """
        self._entries = [
            entry for entry in self._entries if now - entry.recorded_at <= self._window_sec
        ]
        robots = set(robot_ids)
        shown = [entry.proposal for entry in self._entries if entry.robot_ids & robots]
        return shown[-self._max_entries :]

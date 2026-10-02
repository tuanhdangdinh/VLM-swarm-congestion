"""Pure M5 phase queue for `junction_clear`'s recede-then-yield dispatch sequence.

ROS2-free: `orchestrator_node.py` constructs one `JunctionPhaseQueue` per
dispatched `junction_clear` decision (keyed by the FIRST phase's
`command_id`) and calls `on_resolved` from its existing `_on_status`
handler, alongside -- never instead of -- the normal `_resolve_command` flow
it already runs for every command. This module never touches `PlanTracker`
or re-invokes M2/M3: "M5's phase queue... phases advance by updating leg
status, not by issuing a new plan, so no replan is counted" (prereg-v2 (a)
M5, build-order step 5 design note) -- the ENTIRE phase sequence, including
the plain-`yield` fallback, is precomputed once at decision time
(`reasoning.rag.command_grounder.ground_junction_clear_phases`, from the one
snapshot the triggering decision was made on). This queue only decides
WHICH precomputed command to dispatch next; it never derives one.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from reasoning.rag.command_grounder import JunctionClearPhasePlan

# Ordinal partial-credit vocabulary for the resolution-scored IB10 cell
# (prereg-v2 (a) Scoring: "phase reached is the ordinal partial score"):
# "recede" (a recede phase is the active/awaited one), "cross" (the
# yield-axis phase is active/awaited), "resolved" (every phase completed),
# "fallback" (a phase FAILED; the plain-`yield` fallback is active/awaited,
# or has itself resolved -- the fallback is a terminal step either way, not
# a phase of its own to score further).
JunctionPhaseReached = Literal["recede", "cross", "resolved", "fallback"]


class JunctionPhaseAdvance(BaseModel):
    """What to do next after one dispatched command resolved."""

    model_config = ConfigDict(frozen=True)

    # None when the resolved command_id is not this queue's CURRENT active
    # command (a stale or foreign status): the caller's normal
    # command-resolution flow runs unchanged, this queue is simply not
    # involved. Also None once `done` -- nothing further to dispatch.
    command: dict[str, Any] | None
    phase_reached: JunctionPhaseReached
    # True once this queue has nothing further to dispatch: every phase
    # resolved COMPLETED, or a FAILED phase's fallback has itself resolved
    # (COMPLETED or FAILED -- "falls back to v1 behavior" is itself the
    # terminal step, never retried). The caller may discard the queue.
    done: bool


class JunctionPhaseQueue:
    """Tracks one `junction_clear` decision's precomputed phase sequence.

    Dispatch order: `start()` exactly once, then `on_resolved` for every
    terminal status (`COMPLETED`/`FAILED`, including a timeout) the caller's
    own command tracker reports, until `done` is True.
    """

    def __init__(self, plan: JunctionClearPhasePlan) -> None:
        self._phases = list(plan.phases)
        self._fallback_command = plan.fallback_command
        self._index = 0
        self._active_command_id: str | None = None
        self._fallback_dispatched = False
        self._done = False

    def start(self) -> dict[str, Any]:
        """Return the first phase's command. Call exactly once, before any `on_resolved`.

        Returns:
            `plan.phases[0].command`, as grounded at decision time.
        """
        command = self._phases[0].command
        self._active_command_id = command["command_id"]
        return command

    @property
    def done(self) -> bool:
        """Whether this queue has nothing further to dispatch."""
        return self._done

    @property
    def phase_reached(self) -> JunctionPhaseReached:
        """The furthest phase this queue has DISPATCHED, not necessarily resolved yet."""
        if self._fallback_dispatched:
            return "fallback"
        if self._index >= len(self._phases):
            return "resolved"
        return self._phases[self._index].label

    def on_resolved(self, command_id: str, completed: bool) -> JunctionPhaseAdvance:
        """Advance the queue on one dispatched command's terminal status.

        Args:
            command_id: The resolved command's id, from the caller's own
                command tracker (`CoordinationStatus.command_id`).
            completed: True for an overall-COMPLETED resolution, False for
                FAILED (the caller's own `_on_timer` already treats a
                timeout as FAILED before this is called).

        Returns:
            `command=None` when `command_id` is not this queue's current
            active command, or the queue is already `done` (ignore -- the
            caller's normal flow is unaffected either way); otherwise the
            next command to dispatch (a later recede phase, the yield-axis
            phase, or the fallback on a FAILED phase), or `command=None,
            done=True` when there is nothing further.
        """
        if self._done or command_id != self._active_command_id:
            return JunctionPhaseAdvance(
                command=None, phase_reached=self.phase_reached, done=self._done
            )
        if self._fallback_dispatched:
            # The fallback command's own resolution: nothing further is
            # queued either way -- "falls back to v1 behavior" is itself
            # the terminal step, never retried.
            self._done = True
            return JunctionPhaseAdvance(command=None, phase_reached="fallback", done=True)
        if not completed:
            # Failure at any phase falls back to v1 behavior for the
            # remaining robots (M5 spec section), never a retry of the
            # SAME recede or a later phase.
            self._fallback_dispatched = True
            self._active_command_id = self._fallback_command["command_id"]
            return JunctionPhaseAdvance(
                command=self._fallback_command, phase_reached="fallback", done=False
            )
        self._index += 1
        if self._index >= len(self._phases):
            self._done = True
            return JunctionPhaseAdvance(command=None, phase_reached="resolved", done=True)
        next_command = self._phases[self._index].command
        self._active_command_id = next_command["command_id"]
        return JunctionPhaseAdvance(
            command=next_command, phase_reached=self._phases[self._index].label, done=False
        )

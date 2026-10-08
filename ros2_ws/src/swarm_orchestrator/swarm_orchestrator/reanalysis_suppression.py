"""Scene-unchanged re-trigger suppression for stall-triggered analyses (no rclpy).

prereg-v3 A12(iii): in S1 pilot episode 1 a persistent five-robot stall was
re-analysed every ~16.5 wall-s (cooldown + call time), 216 times, with the
scene unchanged and nothing dispatched. The cooldown and exhausted-robot sets
only space such re-analyses out; this policy skips them while the evidence
they would be given is the same as last time.

Predicate (shipped default; frozen at Step 6): a stall-triggered analysis is
skipped when, against the reference recorded by the last EXECUTED
stall-triggered analysis,

(a) the trigger's robot set equals the reference set,
(b) every one of those robots' M1 position is within `pose_epsilon_m` of its
    reference position (the reference is never re-based on a skipped
    trigger, so slow creep accumulates until it crosses epsilon), and
(c) that analysis dispatched nothing: the model answered (a valid decision)
    but the answer was no-congestion, grounded to no command, or was
    dispatch-suppressed (`dispatch_enabled: false`).

A backend failure (no decision) never arms the reference: the model has not
answered this scene yet. Anything that breaks (a)-(b) clears the reference,
as does a dispatch, a contradiction-triggered or manual analysis, or a new
task issued to a reference robot (its registry goal, which the prompt
renders, changed). The node consults this only where the state machine would
otherwise start an analysis, so cooldowns, the exhausted set, busy gating and
folding keep precedence, and contradiction triggers, junction phases and T0
probes never reach it.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

SuppressionReason = Literal[
    "scene_unchanged", "not_armed", "robot_set_changed", "robot_missing", "pose_moved"
]


@dataclass(frozen=True)
class SuppressionReference:
    """What the last executed, nothing-dispatched stall analysis saw."""

    request_id: str
    robot_ids: frozenset[str]
    positions: dict[str, tuple[float, float]]
    armed_at: float
    # Why nothing was dispatched: no_congestion, no_command, dispatch_suppressed.
    outcome: str


@dataclass(frozen=True)
class SuppressionVerdict:
    """The policy's answer for one would-be analysis."""

    suppress: bool
    reason: SuppressionReason
    # Largest reference-robot displacement, None when not compared.
    max_displacement_m: float | None = None
    # True for the first suppression of each `count_period_sec` window: that
    # trigger stands for one avoided analysis (one cooldown's worth of cadence).
    counted: bool = False
    reference: SuppressionReference | None = None


class ReanalysisSuppressor:
    """Holds the suppression reference and the episode's suppression counters."""

    def __init__(self, pose_epsilon_m: float, count_period_sec: float) -> None:
        self._epsilon = pose_epsilon_m
        self._period = count_period_sec
        self._reference: SuppressionReference | None = None
        self._last_counted_at: float | None = None
        self.suppressed_triggers_total = 0
        self.avoided_analyses_total = 0
        self._suppressed_since = 0
        self._avoided_since = 0

    @property
    def reference(self) -> SuppressionReference | None:
        """The armed reference, or None when every trigger may run."""
        return self._reference

    def arm(
        self,
        request_id: str,
        robot_ids: Iterable[str],
        positions: Mapping[str, tuple[float, float]],
        now: float,
        outcome: str,
    ) -> SuppressionReference:
        """Record the scene of an executed stall analysis that dispatched nothing.

        Args:
            request_id: The analysis that answered.
            robot_ids: Its trigger's robot set.
            positions: M1 (x, y) of every robot in that analysis's scene.
            now: Monotonic time of the outcome.
            outcome: Why nothing was dispatched (for the log and artifact).

        Returns:
            The new reference.
        """
        robots = frozenset(robot_ids)
        self._reference = SuppressionReference(
            request_id=request_id,
            robot_ids=robots,
            positions={rid: positions[rid] for rid in robots if rid in positions},
            armed_at=now,
            outcome=outcome,
        )
        self._last_counted_at = None
        return self._reference

    def reset(self) -> SuppressionReference | None:
        """Clear the reference; returns the one cleared, or None if none was armed."""
        cleared, self._reference = self._reference, None
        self._last_counted_at = None
        return cleared

    def check(
        self,
        robot_ids: Iterable[str],
        positions: Mapping[str, tuple[float, float]],
        now: float,
    ) -> SuppressionVerdict:
        """Decide whether one would-be stall analysis is skipped.

        A verdict that does not suppress clears the reference (except
        `not_armed`, where there is none), so the analysis it lets through
        sets the next one.

        Args:
            robot_ids: The trigger's robot set.
            positions: M1 (x, y) of every robot in the current scene.
            now: Monotonic time.

        Returns:
            The verdict.
        """
        reference = self._reference
        if reference is None:
            return SuppressionVerdict(suppress=False, reason="not_armed")
        if frozenset(robot_ids) != reference.robot_ids:
            self.reset()
            return SuppressionVerdict(
                suppress=False, reason="robot_set_changed", reference=reference
            )
        if any(rid not in positions or rid not in reference.positions
               for rid in reference.robot_ids):
            self.reset()
            return SuppressionVerdict(suppress=False, reason="robot_missing", reference=reference)
        moved = max(
            (math.dist(positions[rid], reference.positions[rid]) for rid in reference.robot_ids),
            default=0.0,
        )
        if moved >= self._epsilon:
            self.reset()
            return SuppressionVerdict(
                suppress=False, reason="pose_moved", max_displacement_m=moved,
                reference=reference,
            )
        self.suppressed_triggers_total += 1
        self._suppressed_since += 1
        counted = self._last_counted_at is None or now - self._last_counted_at >= self._period
        if counted:
            self._last_counted_at = now
            self.avoided_analyses_total += 1
            self._avoided_since += 1
        return SuppressionVerdict(
            suppress=True, reason="scene_unchanged", max_displacement_m=moved,
            counted=counted, reference=reference,
        )

    def take_artifact_block(self) -> dict[str, Any]:
        """The artifact block for the analysis about to be recorded.

        Counts since the previous executed analysis, then restarts them, so
        summing the per-artifact counts over an episode gives the totals.
        """
        block = {
            "pose_epsilon_m": self._epsilon,
            "suppressed_triggers_since_last_analysis": self._suppressed_since,
            "avoided_analyses_since_last_analysis": self._avoided_since,
            "suppressed_triggers_total": self.suppressed_triggers_total,
            "avoided_analyses_total": self.avoided_analyses_total,
        }
        self._suppressed_since = 0
        self._avoided_since = 0
        return block

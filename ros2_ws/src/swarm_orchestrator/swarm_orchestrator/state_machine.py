"""Pure transition logic for the M5 orchestrator state machine (no rclpy, no I/O)."""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from swarm_orchestrator.models import CongestionEvent, PipelineOutcome, TerminalStage


class OrchestratorState(str, Enum):
    MONITORING = "monitoring"
    ANALYZING = "analyzing"
    DISPATCHING = "dispatching"


class DirectiveKind(str, Enum):
    START_ANALYSIS = "start_analysis"
    SUPPRESSED = "suppressed"
    IGNORED = "ignored"
    DISPATCH = "dispatch"
    COOLDOWN = "cooldown"
    NONE = "none"
    # A queued follower's solo stall while another robot pair's command is in
    # flight: joins that episode instead of opening an analysis mid-maneuver.
    FOLDED = "folded"


def is_queued_follower(robots: list[str], busy_robots: set[str]) -> bool:
    """Whether a stall is a queued follower's, to fold into the busy episode.

    A single stalled robot outside a command that is moving two or more other
    robots (T2b: `robot_3` stalled behind a yield it is not part of). Analysing
    it now would open a new episode, and command the follower, in the middle of
    that maneuver. With two robots in the scene a command moving two robots
    covers every robot, so this is never true there.

    Args:
        robots: The event's involved robots.
        busy_robots: Robots of every unresolved dispatched command.

    Returns:
        True for a solo stall disjoint from a busy set of at least two robots.
    """
    return len(robots) == 1 and len(busy_robots) >= 2 and not set(robots) & busy_robots


@dataclass(frozen=True)
class Directive:
    """An instruction returned to the node, which performs the side effects."""

    kind: DirectiveKind
    request_id: str | None = None
    robots: list[str] = field(default_factory=list)
    outcome: PipelineOutcome | None = None


class OrchestratorStateMachine:
    """Single in-flight reasoning cycle with cooldown/active-command gating."""

    def __init__(self) -> None:
        self.state = OrchestratorState.MONITORING
        self._active_request_id: str | None = None
        self._active_robots: list[str] = []
        self._failures: dict[str, int] = defaultdict(int)

    def failure_count(self, robot_id: str) -> int:
        return self._failures[robot_id]

    def on_event(
        self,
        event: CongestionEvent,
        cooldown_robots: set[str],
        busy_robots: set[str],
        now: float,
        frame_ready: bool = True,
    ) -> Directive:
        """Handle a congestion event; only MONITORING starts a new cycle."""
        if self.state is not OrchestratorState.MONITORING:
            return Directive(kind=DirectiveKind.IGNORED)
        if not frame_ready:
            return Directive(kind=DirectiveKind.SUPPRESSED, robots=event.involved_robots)
        gated = set(event.involved_robots) & (cooldown_robots | busy_robots)
        if gated:
            return Directive(kind=DirectiveKind.SUPPRESSED, robots=event.involved_robots)
        if is_queued_follower(event.involved_robots, busy_robots):
            return Directive(kind=DirectiveKind.FOLDED, robots=event.involved_robots)
        request_id = uuid.uuid4().hex
        self.state = OrchestratorState.ANALYZING
        self._active_request_id = request_id
        self._active_robots = list(event.involved_robots)
        return Directive(
            kind=DirectiveKind.START_ANALYSIS,
            request_id=request_id,
            robots=event.involved_robots,
        )

    def on_outcome(self, outcome: PipelineOutcome, now: float) -> Directive:
        """Handle a completed pipeline run; returns DISPATCH or COOLDOWN."""
        robots = self._active_robots
        if outcome.terminal_stage is TerminalStage.OK and outcome.grounded_command is not None:
            self.state = OrchestratorState.DISPATCHING
            directive = Directive(
                kind=DirectiveKind.DISPATCH,
                request_id=outcome.request_id,
                robots=robots,
                outcome=outcome,
            )
            # Node performs dispatch; cycle returns to MONITORING immediately after.
            self.state = OrchestratorState.MONITORING
            self._clear_active()
            return directive
        for rid in robots:
            self._failures[rid] += 1
        self.state = OrchestratorState.MONITORING
        self._clear_active()
        return Directive(kind=DirectiveKind.COOLDOWN, request_id=outcome.request_id, robots=robots)

    def on_command_resolved(self, robots: list[str], all_completed: bool) -> None:
        """Update failure counters when a dispatched command resolves."""
        for rid in robots:
            if all_completed:
                self._failures[rid] = 0
            else:
                self._failures[rid] += 1

    def _clear_active(self) -> None:
        self._active_request_id = None
        self._active_robots = []

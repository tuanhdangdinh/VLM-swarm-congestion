"""Progress-based congestion detection for M5 (no rclpy)."""
from __future__ import annotations

import math
from collections.abc import Callable

from swarm_orchestrator.models import CongestionEvent, OrchestratorConfig, SceneSnapshot

GoalLookup = Callable[[str], tuple[float, float] | None]


def is_congested(wait_time_sec: float, threshold_sec: float) -> bool:
    """Return True when an observed wait time has reached the stall threshold."""
    return wait_time_sec >= threshold_sec


class _Progress:
    __slots__ = ("min_distance", "last_improved_at")

    def __init__(self, distance: float, now: float) -> None:
        self.min_distance = distance
        self.last_improved_at = now


class CongestionDetector:
    """Tracks per-robot distance-to-goal progress and emits stall events.

    A robot is stalled when its minimum observed distance-to-goal has not improved
    by more than `progress_epsilon_m` for at least `stall_threshold_sec`, while it
    has a goal and a non-STALE status.
    """

    def __init__(self, config: OrchestratorConfig) -> None:
        self._config = config
        self._progress: dict[str, _Progress] = {}

    def update(
        self,
        scene: SceneSnapshot,
        goal_of: GoalLookup,
        now: float,
    ) -> CongestionEvent | None:
        """Advance per-robot progress timers and emit an event on stall.

        Args:
            scene: Latest scene projection from M1.
            goal_of: Maps a robot id to its effective goal, or None if it has none.
            now: Monotonic clock in seconds.

        Returns:
            A `CongestionEvent` if one or more robots crossed the stall threshold,
            else None. On a dropped/late frame the call is a no-op (state held).
        """
        if scene.dropped_frame:
            return None

        stalled: dict[str, float] = {}
        seen: set[str] = set()
        for robot in scene.robots:
            seen.add(robot.robot_id)
            goal = goal_of(robot.robot_id)
            if goal is None or robot.status == "STALE":
                self._progress.pop(robot.robot_id, None)
                continue
            distance = math.dist((robot.x, robot.y), goal)
            state = self._progress.get(robot.robot_id)
            if state is None:
                self._progress[robot.robot_id] = _Progress(distance, now)
                continue
            if distance < state.min_distance - self._config.progress_epsilon_m:
                state.min_distance = distance
                state.last_improved_at = now
            stall = now - state.last_improved_at
            if is_congested(stall, self._config.stall_threshold_sec):
                stalled[robot.robot_id] = stall

        # Forget robots no longer present so they do not linger as stale state.
        for rid in self._progress.keys() - seen:
            self._progress.pop(rid, None)

        if not stalled:
            return None
        return CongestionEvent(
            involved_robots=sorted(stalled),
            stall_durations_sec=stalled,
            detected_at=now,
            reason=f"{len(stalled)} robot(s) stalled >= {self._config.stall_threshold_sec}s",
        )

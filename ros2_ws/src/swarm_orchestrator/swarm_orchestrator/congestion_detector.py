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
    has a goal, a non-STALE status, and is not within `goal_reached_tolerance_m` of
    that goal (an arrived robot is stationary by definition, not stalled). The
    close/slow-pair check is the exception: it includes STALE robots and robots at
    their goal, since two robots genuinely jammed next to a goal are still a real
    standoff — proximity, not goal distance, is the evidence there.
    """

    def __init__(self, config: OrchestratorConfig) -> None:
        self._config = config
        self._progress: dict[str, _Progress] = {}
        self._close_pair_since: dict[tuple[str, str], float] = {}
        self._arrived: dict[str, tuple[float, float]] = {}

    def mark_arrived(self, robot_id: str, goal: tuple[float, float]) -> None:
        """Record that M4 reported `robot_id` reached `goal` (Nav2 success).

        The robot is then excused from progress-stall evidence while M1 keeps
        it within `arrived_radius_m` of that goal; the mark lapses once it is
        seen farther away or its effective goal changes.

        Args:
            robot_id: Robot whose base-mission goal succeeded.
            goal: The goal it reached, as `(x, y)` in metres.
        """
        self._arrived[robot_id] = (float(goal[0]), float(goal[1]))
        self._progress.pop(robot_id, None)

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
        distances: dict[str, float] = {}
        seen: set[str] = set()
        for robot in scene.robots:
            seen.add(robot.robot_id)
            goal = goal_of(robot.robot_id)
            if goal is None or robot.status == "STALE":
                self._progress.pop(robot.robot_id, None)
                continue
            distance = math.dist((robot.x, robot.y), goal)
            arrived_goal = self._arrived.get(robot.robot_id)
            if arrived_goal is not None:
                if arrived_goal == goal and distance <= self._config.arrived_radius_m:
                    self._progress.pop(robot.robot_id, None)
                    continue
                self._arrived.pop(robot.robot_id, None)
            if distance <= self._config.goal_reached_tolerance_m:
                # Arrived: clear any bookkeeping from a stall en route so a robot
                # that reaches its goal stops being reported, not just stops
                # accruing further stall time.
                self._progress.pop(robot.robot_id, None)
                continue
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
                distances[robot.robot_id] = distance

        close_stalled = self._update_close_slow_pairs(scene, now)
        stalled.update(close_stalled)

        # Forget robots no longer present so they do not linger as stale state.
        for rid in self._progress.keys() - seen:
            self._progress.pop(rid, None)

        if not stalled:
            return None
        reason = (
            f"{len(stalled)} robot(s) close/slow >= {self._config.stall_threshold_sec}s"
            if close_stalled
            else f"{len(stalled)} robot(s) stalled >= {self._config.stall_threshold_sec}s"
        )
        return CongestionEvent(
            involved_robots=sorted(stalled),
            stall_durations_sec=stalled,
            detected_at=now,
            reason=reason,
            distance_to_goal_m=distances,
        )

    def _update_close_slow_pairs(
        self, scene: SceneSnapshot, now: float
    ) -> dict[str, float]:
        close_pairs: set[tuple[str, str]] = set()
        slow_robots: dict[str, float] = {}
        # STALE robots keep their last-known position/velocity (StateEstimator
        # carries them forward frozen, it does not drop them). Excluding STALE
        # here creates a blind spot exactly when it matters most: two robots
        # close enough to occlude each other's ArUco marker in the overhead
        # camera go STALE together, which is itself strong proximity evidence.
        robots = list(scene.robots)
        for robot in robots:
            if abs(robot.linear_velocity) <= self._config.proximity_slow_speed_mps:
                slow_robots[robot.robot_id] = 0.0

        stalled: dict[str, float] = {}
        for i, first in enumerate(robots):
            if first.robot_id not in slow_robots:
                continue
            for second in robots[i + 1:]:
                if second.robot_id not in slow_robots:
                    continue
                distance = math.dist((first.x, first.y), (second.x, second.y))
                if distance > self._config.proximity_threshold_m:
                    continue
                pair = tuple(sorted((first.robot_id, second.robot_id)))
                close_pairs.add(pair)
                started = self._close_pair_since.setdefault(pair, now)
                duration = now - started
                if is_congested(duration, self._config.stall_threshold_sec):
                    stalled[pair[0]] = max(stalled.get(pair[0], 0.0), duration)
                    stalled[pair[1]] = max(stalled.get(pair[1], 0.0), duration)

        for pair in set(self._close_pair_since) - close_pairs:
            self._close_pair_since.pop(pair, None)
        return stalled

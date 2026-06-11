from collections.abc import Callable
from dataclasses import dataclass

from isaac.vgu_sim.config import TimedObstacleConfig


@dataclass(order=True)
class _Event:
    time_sec: float
    obstacle_id: str
    action: str  # "spawn" or "remove"


class EventScheduler:
    """Schedules timed obstacle activation/deactivation against simulation time.

    The scheduler is side-effect-free on its own: callers provide optional
    callbacks to execute actual USD prim activation. In host-only tests the
    callbacks are omitted and only state tracking is verified.
    """

    def __init__(
        self,
        obstacles: list[TimedObstacleConfig] | tuple[TimedObstacleConfig, ...],
        activate_fn: Callable[[str], None] | None = None,
        deactivate_fn: Callable[[str], None] | None = None,
    ) -> None:
        self._obstacles = list(obstacles)
        self._activate_fn = activate_fn or (lambda _: None)
        self._deactivate_fn = deactivate_fn or (lambda _: None)
        self._active: set[str] = set()
        self._applied: set[tuple[str, str]] = set()
        self._events: list[_Event] = self._build_events()

    def _build_events(self) -> list[_Event]:
        events: list[_Event] = []
        for obs in self._obstacles:
            events.append(_Event(obs.spawn_at_sec, obs.obstacle_id, "spawn"))
            if obs.remove_at_sec is not None:
                events.append(_Event(obs.remove_at_sec, obs.obstacle_id, "remove"))
        events.sort()
        return events

    def reset(self) -> None:
        """Restore all obstacles to inactive state and clear applied tracking."""
        for obs_id in list(self._active):
            self._deactivate_fn(obs_id)
        self._active.clear()
        self._applied.clear()

    def apply_due_events(self, simulation_time_sec: float) -> tuple[str, ...]:
        """Apply all events whose time <= simulation_time_sec.

        Args:
            simulation_time_sec: Current simulation clock time in seconds.

        Returns:
            Obstacle IDs of events applied during this call.
        """
        applied_ids: list[str] = []
        for event in self._events:
            if event.time_sec > simulation_time_sec:
                break
            key = (event.obstacle_id, event.action)
            if key in self._applied:
                continue
            self._applied.add(key)
            if event.action == "spawn":
                self._activate_fn(event.obstacle_id)
                self._active.add(event.obstacle_id)
            else:
                self._deactivate_fn(event.obstacle_id)
                self._active.discard(event.obstacle_id)
            applied_ids.append(event.obstacle_id)
        return tuple(applied_ids)

    def is_active(self, obstacle_id: str) -> bool:
        """Return True if the obstacle is currently active.

        Args:
            obstacle_id: The obstacle identifier to check.

        Returns:
            True if the obstacle has been spawned and not yet removed.
        """
        return obstacle_id in self._active

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from isaac.vgu_sim.config import TimedObstacleConfig

# Where scenario_builder authors timed obstacles (deactivated until spawn).
TIMED_OBSTACLE_ROOT = "/World/DynamicObstacles"


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


def timed_obstacle_prim_path(obstacle_id: str) -> str:
    """Return the stage path scenario_builder authors a timed obstacle at.

    Args:
        obstacle_id: The timed obstacle's identifier.

    Returns:
        The obstacle's prim path under `TIMED_OBSTACLE_ROOT`.
    """
    return f"{TIMED_OBSTACLE_ROOT}/{obstacle_id}"


def prim_activation_callbacks(
    get_stage: Callable[[], Any],
) -> tuple[Callable[[str], None], Callable[[str], None]]:
    """Build scheduler callbacks that toggle a timed obstacle prim's active flag.

    scenario_builder authors each timed obstacle's geometry and collision up
    front and deactivates the prim, so spawning is `SetActive(True)` and
    removal is `SetActive(False)`. The stage is looked up at call time rather
    than captured: the runner's `SimulationContext.reset()` reloads the stage
    after the scheduler is built.

    Args:
        get_stage: Returns the live USD stage.

    Returns:
        `(activate_fn, deactivate_fn)` for `EventScheduler`.

    Raises:
        RuntimeError: From either callback, if the obstacle's prim is not on
            the stage (a stale scenario USD); a silent no-op would leave the
            run without its obstacle.
    """

    def _set_active(obstacle_id: str, active: bool) -> None:
        path = timed_obstacle_prim_path(obstacle_id)
        prim = get_stage().GetPrimAtPath(path)
        if not prim.IsValid():
            raise RuntimeError(f"timed obstacle prim missing: {path}")
        prim.SetActive(active)

    return (
        lambda obstacle_id: _set_active(obstacle_id, True),
        lambda obstacle_id: _set_active(obstacle_id, False),
    )

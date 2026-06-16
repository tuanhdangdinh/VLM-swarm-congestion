"""Coordination task/status registry owned by M5 and published to M1 (no rclpy)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from swarm_orchestrator.models import OrchestratorConfig, TaskAssignment


@dataclass
class _Override:
    action: str
    goal: tuple[float, float]
    command_id: str


@dataclass
class _Entry:
    base: TaskAssignment
    override: _Override | None = None


@dataclass
class TaskRegistry:
    """Per-robot base assignment plus optional active coordination override.

    The published JSON always carries the *effective* task and goal: the override
    while one is active, the base assignment otherwise.
    """

    entries: dict[str, _Entry] = field(default_factory=dict)

    def load_initial(self, config: OrchestratorConfig) -> None:
        """Populate base assignments from config (called once at startup)."""
        self.entries = {rid: _Entry(base=assignment) for rid, assignment in config.initial_tasks.items()}

    def assign(self, robot_id: str, task: str, goal: tuple[float, float]) -> None:
        """Set or replace a robot's base mission assignment."""
        self.entries[robot_id] = _Entry(base=TaskAssignment(task=task, goal=goal))

    def set_override(
        self, robot_id: str, action: str, goal: tuple[float, float], command_id: str
    ) -> None:
        """Apply a coordination override for a robot (no-op if robot unknown)."""
        entry = self.entries.get(robot_id)
        if entry is None:
            return
        entry.override = _Override(action=action, goal=goal, command_id=command_id)

    def clear_override(self, robot_id: str) -> None:
        """Remove a robot's override so its effective goal reverts to the base."""
        entry = self.entries.get(robot_id)
        if entry is not None:
            entry.override = None

    def effective(self, robot_id: str) -> tuple[str, tuple[float, float]] | None:
        """Return the (task, goal) currently in effect for a robot, or None."""
        entry = self.entries.get(robot_id)
        if entry is None:
            return None
        if entry.override is not None:
            return entry.override.action, entry.override.goal
        return entry.base.task, entry.base.goal

    def to_json(self) -> str:
        """Serialize the effective registry as deterministic JSON sorted by robot id."""
        payload = {}
        for robot_id in sorted(self.entries):
            task, goal = self.effective(robot_id)  # type: ignore[misc]
            payload[robot_id] = {"task": task, "goal": [goal[0], goal[1]]}
        return json.dumps(payload, sort_keys=True)

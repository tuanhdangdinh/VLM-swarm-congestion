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
    while one is active, the base assignment otherwise. A robot whose base
    assignment has a `start_delay_sec` is *pending* until that delay has passed
    since `load_initial`; its entry then also carries `"start_pending": true`,
    which M4's base-mission driver reads as "do not drive this robot yet".
    """

    entries: dict[str, _Entry] = field(default_factory=dict)
    # robot_id -> monotonic time its base mission is released (pending robots only).
    release_at: dict[str, float] = field(default_factory=dict)

    def load_initial(self, config: OrchestratorConfig, now: float = 0.0) -> None:
        """Populate base assignments from config (called once at startup).

        Args:
            config: Orchestrator config holding `initial_tasks`.
            now: Monotonic time of M5's start, from which each
                `start_delay_sec` is counted.
        """
        self.load_assignments(config.initial_tasks, now)

    def load_assignments(self, tasks: dict[str, TaskAssignment], now: float = 0.0) -> None:
        """Populate base assignments from an explicit mapping (startup only).

        Args:
            tasks: Robot id -> base assignment; the task stream passes each
                robot's first task here instead of `initial_tasks`.
            now: Monotonic time from which each `start_delay_sec` is counted.
        """
        self.entries = {rid: _Entry(base=assignment) for rid, assignment in tasks.items()}
        self.release_at = {
            rid: now + assignment.start_delay_sec
            for rid, assignment in tasks.items()
            if assignment.start_delay_sec > 0.0
        }

    def is_pending(self, robot_id: str) -> bool:
        """Return whether a robot's base mission is still held back."""
        return robot_id in self.release_at

    def release_due(self, now: float) -> list[str]:
        """Release every pending robot whose start delay has elapsed.

        Args:
            now: Current monotonic time.

        Returns:
            The robots released by this call, sorted; empty when none were due.
        """
        due = sorted(rid for rid, at in self.release_at.items() if at <= now)
        for rid in due:
            del self.release_at[rid]
        return due

    def assign(self, robot_id: str, task: str, goal: tuple[float, float]) -> None:
        """Set or replace a robot's base mission assignment."""
        self.entries[robot_id] = _Entry(base=TaskAssignment(task=task, goal=goal))

    def set_base(self, robot_id: str, task: str, goal: tuple[float, float]) -> None:
        """Replace a robot's base mission, keeping any active override.

        Unlike `assign`, an in-flight coordination command keeps its override,
        so a task-stream advance mid-command does not drop it; the effective
        goal falls through to the new base once the override clears. A
        no-op for an unknown robot.
        """
        entry = self.entries.get(robot_id)
        if entry is None:
            return
        entry.base = entry.base.model_copy(update={"task": task, "goal": goal})

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

    def mission_task(self, robot_id: str) -> str | None:
        """Return a robot's base mission task label, ignoring any override.

        The M2 prompt renders this label: an override's task is the dispatched
        coordination action (e.g. "yield"), which would tell the VLM what M5
        last did instead of what the robot is for.
        """
        entry = self.entries.get(robot_id)
        return None if entry is None else entry.base.task

    def mission_goal(self, robot_id: str) -> tuple[float, float] | None:
        """Return a robot's base mission goal, ignoring any override.

        Under the task stream this is the robot's CURRENT task node:
        `set_base` advances it even while a coordination override is
        active, whereas `effective` keeps returning the goal the override
        captured at dispatch. M3's node-handoff rule reads this one.
        """
        entry = self.entries.get(robot_id)
        return None if entry is None else entry.base.goal

    def to_json(self) -> str:
        """Serialize the effective registry as deterministic JSON sorted by robot id."""
        payload = {}
        for robot_id in sorted(self.entries):
            task, goal = self.effective(robot_id)  # type: ignore[misc]
            payload[robot_id] = {"task": task, "goal": [goal[0], goal[1]]}
            if robot_id in self.release_at:
                payload[robot_id]["start_pending"] = True
        return json.dumps(payload, sort_keys=True)

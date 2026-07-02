"""Command lifecycle and cooldown tracking for M5 (no rclpy)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

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

    def fallback_of(self, command_id: str) -> str | None:
        record = self._records.get(command_id)
        return None if record is None else record.fallback

    def check_timeouts(self, now: float) -> list[str]:
        """Mark unresolved commands past their deadline TIMED_OUT; return their ids."""
        timed_out: list[str] = []
        for command_id, record in self._records.items():
            if self.is_resolved(command_id):
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

from __future__ import annotations

from typing import Protocol

from swarm_perception.models import Frame


class FrameSourceTimeoutError(TimeoutError):
    """Raised by FrameSource.read when no frame arrives before timeout_sec."""


class CalibrationError(ValueError):
    """Raised when a calibration artifact is missing or invalid."""


class FrameSource(Protocol):
    def open(self) -> None: ...
    def read(self, timeout_sec: float | None = None) -> Frame: ...
    def close(self) -> None: ...

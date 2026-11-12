"""JSONL trace of every congestion event's directive and the in-flight commands (no rclpy).

The v4 Stage 1 shadow cell must settle the design note's Section 2 branch:
does an event naming only a second group ever start an analysis while the
first group's command still runs? The M5 log names suppressions only in
part (fold lines are throttled, IGNORED is silent), so each event is
recorded here with its directive, the unresolved commands and their robots,
the stamp of M1's scene (sim-s under Isaac) and M5's monotonic time.

The detector re-fires on every scene while robots stay stalled, so
consecutive events with the same key (directive kind, robots, request id,
in-flight command ids) are one run: its first event is written at once as an
`event` line, and when a different key arrives an `event_run_end` line
closes it with the count and the last stamps. A node that stops mid-run
leaves the run's `event` line without its end line; nothing is dropped.
Every line carries `run_id` and `session_id` (default `json.dumps` spacing).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class TriggerTrace:
    """Coalescing JSONL writer for congestion-event directives."""

    def __init__(self, path: str | Path, run_id: str | None, session_id: str) -> None:
        """Open the trace (the file is appended to, created on the first line).

        Args:
            path: The JSONL file.
            run_id: `VGU_RUN_ID`, or None.
            session_id: The M5 session.
        """
        self.path = Path(path)
        self._envelope = {"run_id": run_id, "session_id": session_id}
        self._key: tuple[Any, ...] | None = None
        self._run: dict[str, Any] | None = None
        self.lines_written = 0

    def record(
        self,
        *,
        directive: str,
        robots: Sequence[str],
        reason: str | None,
        request_id: str | None,
        in_flight: Mapping[str, Sequence[str]],
        analysis_in_flight: str | None,
        sim_t: float | None,
        wall_t: float,
        source: str = "stall",
    ) -> None:
        """Record one event; writes only when it starts a new run.

        Args:
            directive: The state machine's directive kind (its value).
            robots: The event's involved robots.
            reason: The detector's reason string.
            request_id: The analysis it started, for START_ANALYSIS.
            in_flight: Unresolved command id -> its robots, at this event.
            analysis_in_flight: The request id of the analysis on the worker
                (the state machine's ANALYZING), or None.
            sim_t: The scene stamp (sim-s under Isaac).
            wall_t: M5's monotonic time.
            source: `stall` or `manual`.

        Raises:
            OSError: If the trace cannot be appended to.
        """
        robots_sorted = sorted(robots)
        commands = {cid: sorted(rs) for cid, rs in sorted(in_flight.items())}
        key = (
            directive,
            tuple(robots_sorted),
            request_id,
            tuple(commands),
            analysis_in_flight,
            source,
        )
        if key == self._key and self._run is not None:
            self._run["count"] += 1
            self._run["last_sim_t"] = sim_t
            self._run["last_wall_t"] = wall_t
            return
        self._close_run()
        busy = sorted({r for rs in commands.values() for r in rs})
        line = {
            "event": "event",
            "directive": directive,
            "source": source,
            "robots": robots_sorted,
            "reason": reason,
            "request_id": request_id,
            "in_flight": commands,
            "busy_robots": busy,
            "disjoint_from_busy": bool(busy) and not set(robots_sorted) & set(busy),
            "analysis_in_flight": analysis_in_flight,
            "sim_t": sim_t,
            "wall_t": wall_t,
        }
        self._write(line)
        self._key = key
        self._run = {"count": 1, "first_sim_t": sim_t, "last_sim_t": sim_t,
                     "first_wall_t": wall_t, "last_wall_t": wall_t,
                     "directive": directive, "robots": robots_sorted}

    def close(self) -> None:
        """Close the open run, if any (end of session).

        Raises:
            OSError: If the trace cannot be appended to.
        """
        self._close_run()

    def _close_run(self) -> None:
        run = self._run
        self._run = None
        self._key = None
        if run is None or run["count"] < 2:
            return
        self._write({"event": "event_run_end", **run})

    def _write(self, line: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._envelope | line, sort_keys=True) + "\n")
        self.lines_written += 1


__all__ = ["TriggerTrace"]

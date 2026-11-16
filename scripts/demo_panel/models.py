"""Pydantic contracts for the demo terminal transcript.

The terminal pane shows only (a) original log lines selected by one fixed
`grep` filter, (b) `[… N similar lines]` markers for collapsed safety-latch
repeats, and (c) real read-only commands (`jq`, `grep`, `awk`) run on the
bundle's files, followed by their actual output. Each item records where it
came from, so the saved `transcript.json` can be checked against the bundle.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ItemKind = Literal["log", "marker", "command", "output"]
ItemStyle = Literal[
    "m5", "m4", "warn", "command", "output", "marker", "dim", "decision", "action", "check"
]


class TerminalItem(BaseModel):
    """One logical terminal line (it may wrap onto several screen rows).

    Attributes:
        kind: `log` (an original log line), `marker` (collapsed repeats),
            `command` (a `$ ...` prompt line) or `output` (that command's
            stdout line).
        text: Exact text shown (log line or command output byte-for-byte,
            decoded as UTF-8).
        sim_time: Sim time at which the line is due.
        time_basis: How `sim_time` was obtained.
        source: `file:line` for log lines, the command for outputs/markers.
        style: Colour class.
    """

    model_config = ConfigDict(frozen=True)

    kind: ItemKind
    text: str
    sim_time: float
    time_basis: Literal["mapped_wall", "pre_scene", "after_scene", "with_command"]
    source: str
    style: ItemStyle


class TimeMapInfo(BaseModel):
    """Description of the wall-to-sim mapping and its measured error."""

    model_config = ConfigDict(frozen=True)

    method: str
    offset_wall_minus_monotonic: float | None
    anchor_count: int = Field(ge=0)
    anchor_spread_wall_sec: float | None
    max_abs_error_sim_sec: float | None
    error_checks: tuple[str, ...] = ()
    uncertain: bool
    note: str


class Transcript(BaseModel):
    """Everything the terminal pane will show for one bundle."""

    model_config = ConfigDict(frozen=True)

    bundle_name: str
    bundle_dir: str
    filter_command: str
    items: tuple[TerminalItem, ...]
    calls: tuple[tuple[float, float, float], ...] = Field(
        description="(request sim, response sim, true wall seconds) per model call"
    )
    blocks: tuple[tuple[float, int], ...] = Field(
        description="(sim time, item count) of each command block printed with the clock held"
    )
    time_map: TimeMapInfo
    sim_end: float

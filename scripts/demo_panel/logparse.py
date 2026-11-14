"""Pure parsers for the ROS2 launch logs and side logs found in a run bundle.

Every parser takes one raw message string (or one raw file line) and returns a
small frozen record or None; callers keep the raw 1-based line number so each
extracted value can be traced back to `file:line`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_ROS_LINE = re.compile(
    r"^(?:\[(?P<proc>[^\]]+)\] )?\[(?P<level>[A-Z]+)\] \[(?P<wall>\d+\.\d+)\] "
    r"\[(?P<node>[^\]]+)\]: (?P<msg>.*)$"
)
_STARTING = re.compile(
    r"^starting analysis request=(?P<request>[0-9a-f]+) robots=\[(?P<robots>[^\]]*)\] "
    r"reason=(?P<reason>.*?) order=(?P<order>\S+)(?: distance_to_goal_m=(?P<dist>\{.*\}))?$"
)
_ARTIFACT = re.compile(r"^decision artifact written: (?P<path>\S+?/(?P<request>[0-9a-f]+)\.json)$")
_DISPATCH = re.compile(
    r"^dispatch request=(?P<request>\S+) command=(?P<command>\S+) robot=(?P<robot>\S+)"
    r" plan_id=(?P<plan_id>\S+)$"
)
_NO_DISPATCH = re.compile(
    r"^request=(?P<request>[0-9a-f]+) no dispatch stage=(?P<stage>\S+) reason=(?P<reason>.*)$"
)
_PHASE = re.compile(
    r"^junction_clear phase advance command=(?P<command>\S+) completed=(?P<completed>\S+) "
    r"phase_reached=(?P<phase>\S+) done=(?P<done>\S+)$"
)
_CMD_RESOLVED = re.compile(r"^command (?P<command>\S+) resolved status=(?P<status>\S+)$")
_ARRIVAL = re.compile(
    r"^robot (?P<robot>\S+) arrived at base goal (?P<goal>\([^)]*\)) distance_m=(?P<dist>\S+)"
    r" check=(?P<check>\S+)$"
)
_LAYER2_OFF = re.compile(r"^reasoning_enabled=false layer2=off\b.*$")
_STATUS = re.compile(
    r"^status published command=(?P<command>\S+) robot=(?P<robot>\S+) status=(?P<status>\S+)$"
)
_EXEMPT = re.compile(r"^exempt pairs changed pairs=(?P<pairs>\S+)$")
_SAFETY_STOP = re.compile(r"^safety stop robot=(?P<robot>\S+) reason=(?P<reason>\S+)$")
_SAFETY_START = re.compile(r"^Safety monitor started (?P<params>.*)$")
_CROSSING = re.compile(
    r"^crossing_chain (?P<what>gate_admit|gate_cleared|gate_release) command=(?P<command>\S+) "
    r"yielder=(?P<yielder>\S+)(?: passer=(?P<passer>\S+))?.*?sim_t=(?P<sim_t>\d+\.\d+)$"
)
_SIM_T = re.compile(r"\bsim_t=(?P<sim_t>\d+\.\d+)\b")
_COST = re.compile(
    r"^(?P<hms>\d{2}:\d{2}:\d{2}) analyses=(?P<analyses>\d+) artifacts=(?P<artifacts>\d+) "
    r"billed_calls=(?P<billed>\d+) est_usd=(?P<usd>\d+\.\d+)$"
)
_KV = re.compile(r"(?P<key>[A-Za-z_]+)=(?P<value>\S+)")


@dataclass(frozen=True)
class RosLine:
    """One parsed ROS2 launch-log line."""

    proc: str | None
    level: str
    wall: float
    node: str
    msg: str


def read_raw_lines(path: Path) -> list[str]:
    """Read a text file as raw lines without trailing newlines.

    Args:
        path: File to read.

    Returns:
        Lines in file order; index `i` is raw line number `i + 1`.
    """
    return path.read_text(errors="replace").splitlines()


def parse_ros_line(raw: str) -> RosLine | None:
    """Parse one ROS2 launch-log line carrying a wall-clock stamp.

    Args:
        raw: Raw log line, e.g. `[proc] [INFO] [1794638416.6] [node]: msg`.

    Returns:
        The parsed line, or None for lines without the stamped format.
    """
    m = _ROS_LINE.match(raw.rstrip())
    if m is None:
        return None
    return RosLine(
        proc=m.group("proc"),
        level=m.group("level"),
        wall=float(m.group("wall")),
        node=m.group("node"),
        msg=m.group("msg"),
    )


def iter_ros_lines(lines: list[str]) -> list[tuple[int, RosLine]]:
    """Return `(raw_line_number, RosLine)` for every stamped line.

    Args:
        lines: Raw file lines (index 0 is line 1).

    Returns:
        Parsed stamped lines with their 1-based raw line numbers.
    """
    out: list[tuple[int, RosLine]] = []
    for i, raw in enumerate(lines, start=1):
        parsed = parse_ros_line(raw)
        if parsed is not None:
            out.append((i, parsed))
    return out


def _robot_list(text: str) -> list[str]:
    return [t.strip().strip("'\"") for t in text.split(",") if t.strip()]


def parse_starting_analysis(msg: str) -> dict[str, object] | None:
    """Parse an M5 `starting analysis request=...` message.

    Args:
        msg: Message part of the log line.

    Returns:
        Dict with `request`, `robots`, `reason`, `order`, `distance` (raw
        text or None), or None when the message is not this kind.
    """
    m = _STARTING.match(msg)
    if m is None:
        return None
    return {
        "request": m.group("request"),
        "robots": _robot_list(m.group("robots")),
        "reason": m.group("reason"),
        "order": m.group("order"),
        "distance": m.group("dist"),
    }


def parse_artifact_written(msg: str) -> str | None:
    """Return the request id of a `decision artifact written:` message, else None."""
    m = _ARTIFACT.match(msg)
    return m.group("request") if m else None


def parse_dispatch(msg: str) -> dict[str, str] | None:
    """Parse an M5 `dispatch request=... command=... robot=...` message."""
    m = _DISPATCH.match(msg)
    return m.groupdict() if m else None


def parse_no_dispatch(msg: str) -> dict[str, str] | None:
    """Parse an M5 `request=... no dispatch stage=... reason=...` message."""
    m = _NO_DISPATCH.match(msg)
    return m.groupdict() if m else None


def parse_phase_advance(msg: str) -> dict[str, str] | None:
    """Parse an M5 `junction_clear phase advance ...` message."""
    m = _PHASE.match(msg)
    return m.groupdict() if m else None


def parse_command_resolved(msg: str) -> dict[str, str] | None:
    """Parse an M5 `command <id> resolved status=<s>` message."""
    m = _CMD_RESOLVED.match(msg)
    return m.groupdict() if m else None


def parse_arrival(msg: str) -> dict[str, str] | None:
    """Parse an M5 `robot <id> arrived at base goal ...` message."""
    m = _ARRIVAL.match(msg)
    return m.groupdict() if m else None


def is_layer2_off(msg: str) -> bool:
    """Return True for M5's `reasoning_enabled=false layer2=off ...` startup message."""
    return _LAYER2_OFF.match(msg) is not None


def parse_status_published(msg: str) -> dict[str, str] | None:
    """Parse an M4 command-bus `status published command=... status=...` message."""
    m = _STATUS.match(msg)
    return m.groupdict() if m else None


def parse_exempt_pairs(msg: str) -> str | None:
    """Return the `pairs=` value of an M4 `exempt pairs changed` message, else None."""
    m = _EXEMPT.match(msg)
    return m.group("pairs") if m else None


def parse_safety_stop(msg: str) -> dict[str, str] | None:
    """Parse an M4 `safety stop robot=... reason=...` message."""
    m = _SAFETY_STOP.match(msg)
    return m.groupdict() if m else None


def parse_safety_start(msg: str) -> dict[str, str] | None:
    """Parse the M4 `Safety monitor started k=v ...` message into its key/values.

    Args:
        msg: Message part of the log line.

    Returns:
        Mapping of parameter name to raw value text, or None.
    """
    m = _SAFETY_START.match(msg)
    if m is None:
        return None
    return {kv.group("key"): kv.group("value") for kv in _KV.finditer(m.group("params"))}


def parse_crossing_chain(msg: str) -> dict[str, str] | None:
    """Parse an M4 `crossing_chain gate_*` message (carries its own `sim_t=`)."""
    m = _CROSSING.match(msg)
    return m.groupdict() if m else None


def parse_sim_t(msg: str) -> float | None:
    """Return the `sim_t=<seconds>` value embedded in a message, if any."""
    m = _SIM_T.search(msg)
    return float(m.group("sim_t")) if m else None


def parse_cost_line(raw: str) -> dict[str, str] | None:
    """Parse one `cost.log` poll line (`HH:MM:SS analyses=.. billed_calls=.. est_usd=..`)."""
    m = _COST.match(raw.strip())
    return m.groupdict() if m else None


def parse_condition(text: str) -> dict[str, str]:
    """Parse `CONDITION.txt` (`key=value` tokens separated by spaces)."""
    return {kv.group("key"): kv.group("value") for kv in _KV.finditer(text)}

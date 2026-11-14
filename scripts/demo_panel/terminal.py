"""Build the terminal transcript for one bundle from its own files.

The transcript is made of three things only:

1. Original log lines from `m5.log` and `m4.log` selected by the fixed
   `FILTER_PATTERN` and ordered by their own wall stamp. The selection is the
   output of a real shell command (`filter_command`), run with `subprocess`,
   so the terminal shows exactly what that command prints.
2. `[… N similar lines]` markers replacing repeats of the M4 safety-latch line
   (`safety stop robot=<id> reason=<r>`, ~40 Hz per robot while latched): the
   first line of each distinct message in a latch episode is shown verbatim,
   later identical messages (same text apart from the wall stamp) are counted
   and the count is printed every `MARKER_PERIOD_SIM_SEC` sim seconds and when
   the episode ends.
3. At each `decision artifact written` line, a block of real read-only
   commands (`jq`, `awk`) on `decisions/<request_id>.json`, printed as `$ cmd`
   followed by the command's actual stdout; and, when `cost.log` exists, a
   `grep` for the poll line where `billed_calls` first reached that count.
"""

from __future__ import annotations

import datetime as dt
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.demo_panel import logparse as lp
from scripts.demo_panel.bundle import Bundle, TimeContext
from scripts.demo_panel.models import TerminalItem, Transcript

FILTER_PATTERN = (
    "session_id=|reasoning_enabled=|starting analysis|decision artifact written|"
    "dispatch request=|no dispatch|phase advance|arrived at base goal|"
    "Safety monitor started|command received|exempt pairs changed|crossing_chain|safety stop"
)
LOG_FILES = ("m5.log", "m4.log")
COLLAPSE_PATTERN = re.compile(r"\]: safety stop robot=\S+ reason=\S+$")
LATCH_GAP_WALL_SEC = 2.0
MARKER_PERIOD_SIM_SEC = 10.0
_STAMP_FIELD = re.compile(r"\[\d+\.\d+\]")


def filter_command() -> str:
    """Shell command (run inside the bundle directory) that selects the log lines.

    `sort -s -t'[' -k4,4n` orders the merged lines by their wall stamp (the
    fourth `[`-separated field of `[proc] [LEVEL] [stamp] [node]: msg`),
    keeping file order for equal stamps.
    """
    files = " ".join(LOG_FILES)
    return f"grep -hE {shlex.quote(FILTER_PATTERN)} {files} | sort -s -t'[' -k4,4n"


def run_shell(command: str, cwd: Path) -> list[str]:
    """Run a read-only shell command in `cwd` and return its stdout lines.

    Args:
        command: Command line for `bash -c`.
        cwd: Working directory (the bundle).

    Returns:
        Stdout split into lines (UTF-8, undecodable bytes replaced).

    Raises:
        RuntimeError: The command exits with a status other than 0 or 1
            (grep's "no match" is 1).
    """
    proc = subprocess.run(
        ["bash", "-c", command], cwd=cwd, capture_output=True, env={"LC_ALL": "C", "PATH": _path()}
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"{command!r} failed: {proc.stderr.decode(errors='replace')}")
    return proc.stdout.decode("utf-8", errors="replace").splitlines()


def _path() -> str:
    dirs = []
    for tool in ("jq", "grep", "sort", "awk", "bash"):
        found = shutil.which(tool)
        if found is None:
            raise RuntimeError(f"required tool {tool!r} not found on PATH")
        dirs.append(str(Path(found).parent))
    return ":".join(dict.fromkeys(dirs + ["/usr/bin", "/bin"]))


def python_filter(lines_by_file: dict[str, list[str]]) -> list[str]:
    """Pure-Python equivalent of `filter_command`, used to cross-check it in tests.

    Args:
        lines_by_file: Raw lines of each file in `LOG_FILES`.

    Returns:
        Matching lines ordered by wall stamp (file order kept for ties).
    """
    rx = re.compile(FILTER_PATTERN)
    matched = [ln for f in LOG_FILES for ln in lines_by_file.get(f, []) if rx.search(ln)]

    def key(ln: str) -> float:
        parsed = lp.parse_ros_line(ln)
        return parsed.wall if parsed else float("-inf")

    return sorted(matched, key=key)


def mask_stamp(line: str) -> str:
    """Line text with its `[<wall stamp>]` field blanked, for repeat detection."""
    return _STAMP_FIELD.sub("[*]", line, count=1)


def style_of(line: str) -> str:
    """Colour class for a log line: WARN/ERROR, else by process (m5 vs m4)."""
    parsed = lp.parse_ros_line(line)
    if parsed and parsed.level in ("WARN", "ERROR"):
        return "warn"
    if parsed and parsed.node == "orchestrator_node":
        return "m5"
    return "m4"


def decision_commands(request_id: str, has_plan: bool) -> list[str]:
    """Concise read-only `jq` commands that print a decision artifact's key fields.

    One short command per topic, each printing one or two lines: the request
    (prompt version, a hash prefix and size, and the prompt's first line,
    which states the task; the prompt itself is not dumped), the model call
    (backend, served model, latency, attempts, total tokens), the model's
    decision (strategy, involved robots, its one-sentence justification), and
    M3's grounding (plan provenance and reason, degradations, dispatch order).

    Args:
        request_id: Request id (file stem in `decisions/`).
        has_plan: Whether the artifact's `plan` is non-null (grounding ran).

    Returns:
        Shell commands to run inside the bundle directory.
    """
    f = f"decisions/{request_id}.json"
    cmds = [
        "jq -r '\"prompt v\\(.prompt_version) sha256=\\(.prompt.user_sha256[:12]) "
        f"\\(.prompt.user_prompt | length) chars\"' {f}",
        f"jq -r .prompt.user_prompt {f} | head -n 1",
        "jq -c '.diagnostics | {backend_id, served_model, latency_ms, attempts, "
        f"total_tokens: .token_usage.total_tokens}}' {f}",
        'jq -r \'.decision | "strategy=\\(.strategy) involved=\\(.involved_robots | join(","))", '
        f".justification' {f}",
    ]
    if has_plan:
        cmds.append(
            "jq -r '\"provenance=\\(.plan.provenance) reason=\\(.plan.rejection_reason) "
            'degradations=\\(.diagnostics.decision_degradations // [] | join(",")) '
            f'dispatch_order=\\(.dispatched_robot_ids // [] | join(","))"\' {f}'
        )
    return cmds


@dataclass
class _Latch:
    shown: set[str]
    pending: int
    last_wall: float
    last_marker_sim: float


def _place(tc: TimeContext, wall: float) -> tuple[float, str]:
    if tc.wmap is None:
        return 0.0, "pre_scene"
    s = tc.wmap.wall_to_sim(wall)
    if s is not None:
        return s, "mapped_wall"
    lo = tc.wmap.clock.monotonic_range[0] + tc.wmap.offset
    if wall < lo:
        return 0.0, "pre_scene"
    return tc.wmap.clock.sim_range[1], "after_scene"


def build_transcript(b: Bundle, tc: TimeContext, sim_end: float) -> Transcript:
    """Build the terminal transcript for a bundle.

    Args:
        b: Loaded bundle.
        tc: Its wall-to-sim mapping.
        sim_end: Last sim second of the episode.

    Returns:
        The transcript (items in display order).
    """
    cmd = filter_command()
    lines = run_shell(cmd, b.root)
    line_no = _line_numbers(b)
    items: list[TerminalItem] = []
    calls: list[tuple[float, float, float]] = []
    blocks: list[tuple[float, int]] = []
    starts: dict[str, tuple[float, float]] = {}
    latch: _Latch | None = None
    billed_seen = 0

    def flush_marker(sim: float, basis: str) -> None:
        nonlocal latch
        if latch is not None and latch.pending:
            items.append(
                TerminalItem(
                    kind="marker",
                    text=f"[… {latch.pending} similar lines]",
                    sim_time=sim,
                    time_basis=basis,  # type: ignore[arg-type]
                    source="collapsed 'safety stop' repeats",
                    style="marker",
                )
            )
            latch.pending = 0
            latch.last_marker_sim = sim

    for raw in lines:
        parsed = lp.parse_ros_line(raw)
        if parsed is None:
            continue
        billed_seen = _cost_items(b, tc, items, blocks, billed_seen, parsed.wall)
        sim, basis = _place(tc, parsed.wall)
        if latch is not None and parsed.wall - latch.last_wall > LATCH_GAP_WALL_SEC:
            last_sim, last_basis = _place(tc, latch.last_wall)
            flush_marker(last_sim, last_basis)
            latch = None
        if COLLAPSE_PATTERN.search(raw):
            if latch is None:
                latch = _Latch(set(), 0, parsed.wall, sim)
            latch.last_wall = parsed.wall
            masked = mask_stamp(raw)
            if masked in latch.shown:
                latch.pending += 1
                if sim - latch.last_marker_sim >= MARKER_PERIOD_SIM_SEC:
                    flush_marker(sim, basis)
                continue
            latch.shown.add(masked)
        items.append(
            TerminalItem(
                kind="log",
                text=raw,
                sim_time=sim,
                time_basis=basis,  # type: ignore[arg-type]
                source=line_no.get(raw, "?"),
                style=style_of(raw),  # type: ignore[arg-type]
            )
        )
        st = lp.parse_starting_analysis(parsed.msg)
        if st is not None:
            starts[str(st["request"])] = (sim, parsed.wall)
        req = lp.parse_artifact_written(parsed.msg)
        if req is not None and req in b.decisions:
            if req in starts:
                calls.append((starts[req][0], sim, parsed.wall - starts[req][1]))
            dec = b.decisions[req][1]
            n_before = len(items)
            for c in decision_commands(req, dec.get("plan") is not None):
                items.extend(_command_items(c, b.root, sim))
            blocks.append((sim, len(items) - n_before))
    if latch is not None:
        last_sim, last_basis = _place(tc, latch.last_wall)
        flush_marker(last_sim, last_basis)
    return Transcript(
        bundle_name=b.name,
        bundle_dir=str(b.root),
        filter_command=cmd,
        items=tuple(items),
        calls=tuple(calls),
        blocks=tuple(blocks),
        time_map=tc.info,
        sim_end=sim_end,
    )


def _command_items(command: str, cwd: Path, sim: float) -> list[TerminalItem]:
    out = [
        TerminalItem(
            kind="command",
            text=f"$ {command}",
            sim_time=sim,
            time_basis="with_command",
            source="command",
            style="command",
        )
    ]
    for ln in run_shell(command, cwd):
        out.append(
            TerminalItem(
                kind="output",
                text=ln,
                sim_time=sim,
                time_basis="with_command",
                source=command,
                style="output",
            )
        )
    return out


def _cost_items(
    b: Bundle,
    tc: TimeContext,
    items: list[TerminalItem],
    blocks: list[tuple[float, int]],
    billed_seen: int,
    up_to_wall: float,
) -> int:
    """Print `cost.log` poll lines whose billed count rose, once their time is reached."""
    if not b.cost or not b.manifest.get("started_at_utc"):
        return billed_seen
    day = dt.datetime.fromisoformat(b.manifest["started_at_utc"].replace("Z", "+00:00")).date()
    for raw in b.cost:
        c = lp.parse_cost_line(raw)
        if c is None or int(c["billed"]) <= billed_seen:
            continue
        h, m, s = (int(x) for x in c["hms"].split(":"))
        wall = dt.datetime(
            day.year, day.month, day.day, h, m, s, tzinfo=dt.timezone.utc
        ).timestamp()
        if wall > up_to_wall:
            break
        billed_seen = int(c["billed"])
        sim, _ = _place(tc, wall)
        n_before = len(items)
        items.extend(
            _command_items(f"grep -m1 ' billed_calls={billed_seen} ' cost.log", b.root, sim)
        )
        blocks.append((sim, len(items) - n_before))
    return billed_seen


def _line_numbers(b: Bundle) -> dict[str, str]:
    out: dict[str, str] = {}
    for fname, lines in (("m5.log", b.m5), ("m4.log", b.m4)):
        for i, raw in enumerate(lines, start=1):
            out.setdefault(raw, f"{fname}:{i}")
    return out

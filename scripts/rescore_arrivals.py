#!/usr/bin/env python3
"""Offline position-verified re-scoring of M5 base-goal arrivals (FR5.1.9).

Before `4f39899`, M5 logged `robot <id> arrived at base goal (x, y)` whenever
M4 relayed Nav2's own success report (`bt_navigator` "Goal succeeded"), with no
position check. Run `20260925_124609` showed a false success: Nav2 (and M5)
declared `robot_2` arrived while M1 placed it 0.59 m from the goal. `4f39899`
added `swarm_orchestrator/arrival.py::classify_arrival` to gate *future* runs
on M1's position estimate; this script re-scores every run recorded *before*
that fix against the same rule, offline, plus an independent ground-truth
cross-check.

For every `arrived at base goal` line in a run's M5 log this script finds:

1. The M1 (scene-log) position estimate nearest the report time (must be
   within `--max-age-sec`, mirroring `arrival_estimate_max_age_sec`), and the
   `classify_arrival` verdict for it at `--tolerance-m`.
2. The ground-truth position at that same moment, found by nearest-position
   match (not nearest-time-in-file) against the robot's own GT trajectory
   using the M1 estimate as the reference point. Ground truth's `sim_time_sec`
   is not calibrated to the M5 log's wall-clock timestamps anywhere in the
   recorded data (no shared epoch field), and the GT stream is capped at 3001
   rows regardless of run length, so a wall-clock/sim-time regression would be
   unreliable for the runs whose resolution time exceeds the cap (confirmed:
   `E1`/`20260925_124609`). Nearest-position match sidesteps that: it asks
   "where was the robot, in truth, when it was near the position M1 saw
   near the report" rather than "what GT row shares this wall-clock instant".
   The M1-to-matched-GT-position residual doubles as a per-event sanity check
   (small residual proves the match landed on the right dwell segment) and
   contributes to the M1-vs-GT bias reported alongside it.
3. Ground truth's own minimum distance to goal anywhere in the run, for
   context independent of any report event.

`classify_arrival` is imported directly from
`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/arrival.py` (verified
importable without `rclpy`), so the offline verdict is exactly the function
`ArrivalGate` runs online, not a reimplementation.

Each position-verified arrival (`within_tolerance`) is also checked against
the scenario's static obstacle boxes, read from the run's scenario YAML under
`--scenarios-dir`. A goal parked close to a box (the `_bshort` blocked-side
goal sits 0.20 m from the box near face) lets the tolerance band reach inside
the box, so the `box_overlap` column flags an accepted M1 position within
`ROBOT_HALF_WIDTH_M` of any box. It is a reporting flag only: the verdict is
unchanged.

Scene-log clock eras. Before merge `97634be`, M1 scene stamps were wall-clock
epoch seconds, directly comparable with the M5 log's `[<epoch>]` timestamps.
From `97634be` on, the Isaac camera publishes sim-time stamps, so scene stamps
are sim seconds (~10-300) while M5 events stay wall-clock (~1.79e9); joining
them raw scored every arrival `stale_estimate` with an "age" of ~1.79e9 s and
raised nothing (`simtime_shadow_val` validation, finding F4). `resolve_scene_clock`
detects the era per run: when the scene log's median stamp lies within
`CLOCK_RECONCILE_WINDOW_SEC` of the M5 log's own wall-clock span the run is
wall era and stamps are used unchanged; otherwise it is sim era and each
scene stamp is mapped to wall time through the scene log's `t` column
(M5's `time.monotonic()` at receipt) plus the host's wall-minus-monotonic
offset. That offset is derived per run, never hardcoded: each `starting
analysis request=<id>` line carries a wall time, the matching decision
artifact carries the sim stamp of the scene it analysed, and interpolating
that stamp on the scene log's `(stamp, t)` series gives the monotonic time of
the same instant. The median over analyses is the offset (matches the VM's
measured `time.time() - time.monotonic()` within ~6 ms on both validation
runs). Sim era without usable anchors, inconsistent anchors, or any arrival
event outside the (mapped) scene-log span by more than
`CLOCK_RECONCILE_WINDOW_SEC` raises `ClockReconciliationError`, which aborts
the whole re-score before any CSV is written.

Ground-truth join and the M1 stamp lag: ground truth is matched by nearest
position (item 2 above), never by time, so no clock correction is applied to
it. Post-`97634be` M1 stamps and ground truth's `sim_time_sec` share the sim
clock, but M1 stamps trail the ground-truth state they depict by a constant
~0.45 sim-s (per-row interpolation, median 0.451/0.454 s on the two
`simtime_shadow_val` runs); any future time-based M1-to-GT join must shift M1
stamps by -0.45 s first.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import re
import statistics
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
_SWARM_ORCHESTRATOR = REPO_ROOT / "ros2_ws" / "src" / "swarm_orchestrator"
for _p in (REPO_ROOT, _SWARM_ORCHESTRATOR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from swarm_orchestrator.arrival import ArrivalCheck, classify_arrival  # noqa: E402

STAMP_RE = re.compile(r"^\d{8}_\d{6}$")

ARRIVAL_RE = re.compile(
    r"\[(?P<ts>\d+\.\d+)\].*?robot (?P<robot>\S+) arrived at base goal "
    r"\((?P<gx>-?[\d.]+), (?P<gy>-?[\d.]+)\)"
)
# Post-4f39899 gate log lines. Zero matches across every run in this dataset
# (verified before writing this script: the gate was not wired into any of
# the runs it re-scores), kept so a future re-run over newer logs is handled
# without code changes rather than silently mis-scored.
REJECTED_RE = re.compile(
    r"\[(?P<ts>\d+\.\d+)\].*?arrival rejected robot=(?P<robot>\S+) "
    r"distance_m=(?P<dist>\S+) tolerance_m=(?P<tol>\S+) reason=(?P<reason>\S+)"
)
ACCEPTED_LATE_RE = re.compile(
    r"\[(?P<ts>\d+\.\d+)\].*?arrival accepted late robot=(?P<robot>\S+) "
    r"distance_m=(?P<dist>\S+)"
)
STARTING_ANALYSIS_RE = re.compile(r"\[(?P<ts>\d+\.\d+)\].*?starting analysis")
ANALYSIS_REQUEST_RE = re.compile(
    r"\[(?P<ts>\d+\.\d+)\].*?starting analysis request=(?P<request>[0-9A-Za-z_-]+)"
)
SESSION_ID_RE = re.compile(r"session_id=(?P<sid>[0-9a-f]+) run_id=")
LOG_EPOCH_RE = re.compile(r"\[(?P<ts>\d+\.\d+)\]")

DEFAULT_TOLERANCE_M = 0.35
DEFAULT_MAX_AGE_SEC = 2.0
# Far above any legitimate M1-estimate age (`max_age_sec` is 2 s) and far
# below the ~1.79e9 s sim-vs-wall gap, so a genuinely stale estimate still
# scores `stale_estimate` while an unreconciled clock cannot.
CLOCK_RECONCILE_WINDOW_SEC = 60.0
# Anchors disagreeing by more than this (median absolute deviation) mean the
# analysis lines and artifacts do not describe one consistent clock.
CLOCK_ANCHOR_MAX_MAD_SEC = 1.0
DECISION_DIR_NAMES = ("decisions", "m5_decisions")
DEFAULT_SCENARIOS_DIR = REPO_ROOT / "isaac" / "config" / "scenarios"
# Half of a ~0.35 m chassis envelope. Deliberately conservative: the Nav2
# footprint (swarm_simulation/config/nav2_params.yaml) is only 0.14 x 0.18 m, so
# a flag means "the pose is close enough to a box to review", not proof of
# contact.
ROBOT_HALF_WIDTH_M = 0.175

CSV_FIELDS = [
    "stamp",
    "scenario",
    "backend",
    "order_mode",
    "gate_mode",
    "robot_id",
    "event_index",
    "event_kind",
    "m5_reported_epoch",
    "goal_x",
    "goal_y",
    "m1_estimate_x",
    "m1_estimate_y",
    "m1_estimate_age_sec",
    "m1_estimate_status",
    "m1_dist_m",
    "m1_verdict",
    "gt_matched_sim_time_sec",
    "gt_matched_x",
    "gt_matched_y",
    "gt_dist_m",
    "gt_match_residual_m",
    "gt_min_dist_m",
    "m1_minus_gt_bias_m",
    "flipped",
    "robot_arrived_m1",
    "robot_arrived_gt",
    "run_both_arrived_m1",
    "run_both_arrived_gt",
    "first_starting_analysis_epoch",
    "resolution_sec",
    "no_scene_log",
    "box_overlap",
    "box_overlap_obstacle",
    "clock_era",
    "clock_offset_sec",
    "clock_anchor_count",
    "clock_anchor_spread_sec",
]

ClockEra = Literal["wall", "sim", "n/a"]


@dataclass(frozen=True)
class SceneSample:
    stamp: float
    x: float
    y: float
    status: str


@dataclass(frozen=True)
class GTRow:
    sim_time_sec: float
    x: float
    y: float
    dist_to_goal_m: float
    goal: tuple[float, float]


@dataclass(frozen=True)
class ArrivalEvent:
    ts: float
    robot_id: str
    goal: tuple[float, float] | None
    kind: str  # "reported" | "rejected" | "accepted_late"


@dataclass(frozen=True)
class ObstacleBox:
    """One static obstacle's footprint on the ground plane, in world metres."""

    obstacle_id: str
    x: float
    y: float
    yaw_rad: float
    half_x_m: float
    half_y_m: float


@dataclass(frozen=True)
class ClockResolution:
    """How one run's scene-log stamps relate to its M5 log's wall clock.

    `offset_sec` is the derived wall-minus-monotonic offset, set only in the
    sim era (the wall era uses scene stamps unchanged).
    """

    era: ClockEra
    offset_sec: float | None = None
    anchor_count: int = 0
    anchor_spread_sec: float | None = None


class RunDataError(RuntimeError):
    """A run directory is missing a file this script needs, or has more than one."""


class ClockReconciliationError(RuntimeError):
    """Scene-log stamps and M5 event times cannot be put on one clock.

    Deliberately not a `RunDataError`: `main` skips runs with missing files
    but aborts the whole re-score on this, so a clock mismatch can never turn
    into a CSV of `stale_estimate` rows.
    """


def find_run_dirs(runs_dir: Path) -> list[Path]:
    """Return every `<STAMP>` run directory under `runs_dir`, sorted.

    Args:
        runs_dir: Directory holding one subdirectory per VM run plus stray
            summary files (e.g. `ARM_A_PILOT_SUMMARY.txt`), which are skipped.

    Returns:
        Run directories sorted by stamp (chronological).
    """
    return sorted(
        (p for p in runs_dir.iterdir() if p.is_dir() and STAMP_RE.match(p.name)),
        key=lambda p: p.name,
    )


def _one_file(candidates: list[Path], label: str, run_dir: Path) -> Path | None:
    candidates = [c for c in candidates if "aborted" not in str(c)]
    if not candidates:
        return None
    if len(candidates) > 1:
        raise RunDataError(
            f"{run_dir.name}: ambiguous {label} ({[str(c) for c in candidates]})"
        )
    return candidates[0]


def locate_m5_log(run_dir: Path) -> Path:
    """Find the run's single M5 orchestrator log.

    Args:
        run_dir: One `data/logs/vm_runs/<STAMP>` directory.

    Returns:
        Path to the M5 log.

    Raises:
        RunDataError: No M5 log found, or more than one candidate (excluding
            paths containing "aborted").
    """
    candidates = list(run_dir.glob("component_logs/*m5*.log")) + list(
        run_dir.glob(f"fc_{run_dir.name}_m5.log")
    )
    found = _one_file(candidates, "M5 log", run_dir)
    if found is None:
        raise RunDataError(f"{run_dir.name}: no M5 log found")
    return found


def locate_scene_files(run_dir: Path, session_id: str | None) -> list[Path]:
    """Find the run's own scene-log JSONL file, by session id.

    `scene_log_dir` is a fixed path in `orchestrator.yaml`, not per-run, so a
    run directory's `scene/` can carry leftover files from earlier sessions
    on the same machine (confirmed on the `L1`-`L5` runs: 6-10 stray files
    each, one real). Selecting by the M5 log's own `session_id=` line (the
    same key the ER-2 pilot's extractor uses to avoid mtime-ordering bugs)
    is the only reliable way to pick the right one.

    Args:
        run_dir: One run directory.
        session_id: This run's M5 session id, from `parse_session_id`, or
            None if the log did not carry one (falls back to "all files").

    Returns:
        The scene-log file(s) for this run's own session (normally exactly
        one; empty if none match).
    """
    candidates = sorted(run_dir.glob("scene/*.jsonl")) + sorted(run_dir.glob("m5_scene/*.jsonl"))
    if session_id is None:
        return candidates
    return [p for p in candidates if p.stem == session_id]


def locate_gt_file(run_dir: Path) -> Path:
    """Find the run's ground-truth JSONL file.

    Args:
        run_dir: One run directory.

    Returns:
        Path to the ground-truth file.

    Raises:
        RunDataError: No ground-truth file found, or more than one (some
            runs nest it one level deeper under `<scenario>-seed42-rep000/`).
    """
    candidates = list(run_dir.glob("ground_truth/**/ground_truth.jsonl")) + list(
        run_dir.glob("simulation/**/ground_truth.jsonl")
    )
    found = _one_file(candidates, "ground truth file", run_dir)
    if found is None:
        raise RunDataError(f"{run_dir.name}: no ground truth file found")
    return found


def parse_session_id(m5_log_text: str) -> str | None:
    """Return this run's M5 session id, from its `session_id=... run_id=...` line."""
    match = SESSION_ID_RE.search(m5_log_text)
    return match.group("sid") if match else None


def locate_orchestrator_yaml(run_dir: Path) -> Path | None:
    """Find the run's recorded orchestrator config, if any.

    Args:
        run_dir: One run directory.

    Returns:
        `orchestrator.yaml.used` or `orchestrator.yaml`, or None for the
        oldest runs (E0, R1-R4), which predate this capture.
    """
    for name in ("orchestrator.yaml.used", "orchestrator.yaml"):
        candidate = run_dir / name
        if candidate.is_file():
            return candidate
    return None


def locate_scenario_yaml(scenario: str, scenarios_dir: Path) -> Path | None:
    """Find the scenario YAML a run was launched with, by scenario name.

    Args:
        scenario: Scenario name from `extract_metadata` (`"unknown"` when not
            recoverable); a trailing `.yaml` or a directory prefix is tolerated.
        scenarios_dir: Root searched recursively, normally
            `isaac/config/scenarios` (family variants live one level down).

    Returns:
        The single matching YAML, or None if the name is unknown, absent, or
        ambiguous.
    """
    if scenario == "unknown":
        return None
    matches = sorted(scenarios_dir.rglob(f"{Path(scenario).stem}.yaml"))
    return matches[0] if len(matches) == 1 else None


def load_obstacle_boxes(scenario_yaml: Path) -> list[ObstacleBox]:
    """Read a scenario YAML's `static_obstacles` as ground-plane boxes.

    Args:
        scenario_yaml: Path from `locate_scenario_yaml`.

    Returns:
        One box per static obstacle; empty when the scenario declares none.
    """
    data = yaml.safe_load(scenario_yaml.read_text()) or {}
    return [
        ObstacleBox(
            obstacle_id=obstacle["obstacle_id"],
            x=obstacle["pose"]["x"],
            y=obstacle["pose"]["y"],
            yaw_rad=obstacle["pose"].get("yaw_rad", 0.0),
            half_x_m=obstacle["size"]["x_m"] / 2.0,
            half_y_m=obstacle["size"]["y_m"] / 2.0,
        )
        for obstacle in data.get("static_obstacles") or []
    ]


def overlapping_obstacle(
    position: tuple[float, float],
    boxes: list[ObstacleBox],
    half_width_m: float = ROBOT_HALF_WIDTH_M,
) -> str | None:
    """Return the first box whose span, grown by `half_width_m`, holds `position`.

    Each box is expanded by `half_width_m` on every side in its own frame, so
    a robot centre inside the expanded span means the chassis reaches into
    the box.

    Args:
        position: Robot centre `(x, y)` in world metres.
        boxes: Obstacle boxes from `load_obstacle_boxes`.
        half_width_m: Robot half-width added to each box half-extent.

    Returns:
        The overlapping box's `obstacle_id`, or None when the pose is clear.
    """
    for box in boxes:
        dx, dy = position[0] - box.x, position[1] - box.y
        cos_yaw, sin_yaw = math.cos(box.yaw_rad), math.sin(box.yaw_rad)
        local_x = cos_yaw * dx + sin_yaw * dy
        local_y = -sin_yaw * dx + cos_yaw * dy
        if abs(local_x) <= box.half_x_m + half_width_m and (
            abs(local_y) <= box.half_y_m + half_width_m
        ):
            return box.obstacle_id
    return None


def parse_arrival_events(m5_log_text: str) -> list[ArrivalEvent]:
    """Extract every M5-reported arrival-related event from an M5 log.

    Args:
        m5_log_text: Full text of one run's M5 orchestrator log.

    Returns:
        Events in log order: `"reported"` for the legacy (pre-gate)
        unconditional arrival line, plus `"rejected"` / `"accepted_late"` for
        the post-`4f39899` gate lines where present. `goal` is None for the
        gate lines, which do not print it.
    """
    events: list[ArrivalEvent] = []
    for m in ARRIVAL_RE.finditer(m5_log_text):
        events.append(
            ArrivalEvent(
                ts=float(m.group("ts")),
                robot_id=m.group("robot"),
                goal=(float(m.group("gx")), float(m.group("gy"))),
                kind="reported",
            )
        )
    for m in REJECTED_RE.finditer(m5_log_text):
        events.append(
            ArrivalEvent(
                ts=float(m.group("ts")), robot_id=m.group("robot"), goal=None, kind="rejected"
            )
        )
    for m in ACCEPTED_LATE_RE.finditer(m5_log_text):
        events.append(
            ArrivalEvent(
                ts=float(m.group("ts")), robot_id=m.group("robot"), goal=None, kind="accepted_late"
            )
        )
    events.sort(key=lambda e: e.ts)
    return events


def parse_first_starting_analysis(m5_log_text: str) -> float | None:
    """Return the epoch timestamp of the first `starting analysis` line, if any."""
    match = STARTING_ANALYSIS_RE.search(m5_log_text)
    return float(match.group("ts")) if match else None


def parse_log_epochs(m5_log_text: str) -> list[float]:
    """Return every `[<epoch>]` wall-clock timestamp in an M5 log, in log order."""
    return [float(m.group("ts")) for m in LOG_EPOCH_RE.finditer(m5_log_text)]


def parse_analysis_requests(m5_log_text: str) -> list[tuple[float, str]]:
    """Return `(wall_ts, request_id)` for every `starting analysis request=` line."""
    return [
        (float(m.group("ts")), m.group("request"))
        for m in ANALYSIS_REQUEST_RE.finditer(m5_log_text)
    ]


def _iter_scene_records(scene_files: list[Path]):
    for path in scene_files:
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def load_scene_clock(scene_files: list[Path]) -> list[tuple[float, float | None]]:
    """Read each scene-log record's `(scene stamp, monotonic t)` pair, in file order.

    Args:
        scene_files: Scene-log files for one run (see `locate_scene_files`).

    Returns:
        Pairs in the order M5 wrote them; `t` is M5's `time.monotonic()` when
        it received the scene, or None if the record has no `t`.
    """
    return [
        (record["scene"]["stamp"], record.get("t")) for record in _iter_scene_records(scene_files)
    ]


def stamp_to_monotonic(
    clock: list[tuple[float, float]], stamp: float, extrapolate: bool = False
) -> float | None:
    """Map a scene stamp to M5's monotonic receipt time by linear interpolation.

    Args:
        clock: `(stamp, t)` pairs sorted by strictly increasing stamp.
        stamp: Scene stamp to map, on the same clock as `clock`'s stamps.
        extrapolate: Extend the first/last segment for stamps outside the
            logged range (used for robot stamps older than the first logged
            scene); otherwise such stamps return None.

    Returns:
        Monotonic seconds, or None when `stamp` is out of range and
        `extrapolate` is False, or `clock` is empty.
    """
    if not clock:
        return None
    stamps = [s for s, _ in clock]
    if len(clock) == 1:
        if stamp == stamps[0]:
            return clock[0][1]
        return clock[0][1] + (stamp - stamps[0]) if extrapolate else None
    i = bisect.bisect_left(stamps, stamp)
    if i < len(stamps) and stamps[i] == stamp:
        return clock[i][1]
    if (i == 0 or i == len(stamps)) and not extrapolate:
        return None
    i = min(max(i, 1), len(stamps) - 1)
    (s0, t0), (s1, t1) = clock[i - 1], clock[i]
    return t0 + (stamp - s0) * (t1 - t0) / (s1 - s0)


def detect_clock_era(scene_stamps: list[float], log_epochs: list[float]) -> ClockEra:
    """Classify a run's scene stamps as wall-clock or sim-time.

    Wall era when the scene log's stamp span overlaps the M5 log's own
    wall-clock span widened by `CLOCK_RECONCILE_WINDOW_SEC` (the scene log is
    written by that same M5 process, so wall-clock stamps must fall inside its
    lifetime); sim era otherwise. Overlap, not containment: captured M5 logs
    can end well before the scene log does (`bshort_gpt4o/20260926_204952`'s
    log stops ~430 s before its last scene row).

    Args:
        scene_stamps: Every scene-level stamp in the run's scene log.
        log_epochs: Every wall-clock timestamp in the run's M5 log.

    Returns:
        `"n/a"` when either list is empty, else `"wall"` or `"sim"`.
    """
    if not scene_stamps or not log_epochs:
        return "n/a"
    lo = min(log_epochs) - CLOCK_RECONCILE_WINDOW_SEC
    hi = max(log_epochs) + CLOCK_RECONCILE_WINDOW_SEC
    if min(scene_stamps) <= hi and max(scene_stamps) >= lo:
        return "wall"
    return "sim"


def _load_artifact_scene_stamp(run_dir: Path, request_id: str) -> float | None:
    for name in DECISION_DIR_NAMES:
        path = run_dir / name / f"{request_id}.json"
        if not path.is_file():
            continue
        try:
            scene = json.loads(path.read_text(errors="replace")).get("scene")
        except json.JSONDecodeError:
            return None
        return scene.get("stamp") if isinstance(scene, dict) else None
    return None


def derive_wall_offset(
    run_dir: Path, m5_log_text: str, clock: list[tuple[float, float]]
) -> tuple[float, int, float]:
    """Derive the host's wall-minus-monotonic offset from the run's own records.

    Each analysis contributes one anchor: the wall time of its `starting
    analysis request=<id>` line minus the monotonic time at which M5 received
    the analysed scene, found by interpolating the artifact's scene stamp on
    the scene log's `(stamp, t)` series. The line is logged in the same scene
    callback that received the snapshot, so the two instants differ only by
    request-building time (a few ms).

    Args:
        run_dir: One run directory, holding `decisions/` or `m5_decisions/`.
        m5_log_text: Full text of the run's M5 log.
        clock: `(stamp, t)` pairs sorted by strictly increasing stamp.

    Returns:
        `(offset_sec, anchor_count, anchor_spread_sec)`: the median anchor,
        how many anchors were usable, and their max-min spread.

    Raises:
        ClockReconciliationError: No usable anchor, or anchors whose median
            absolute deviation exceeds `CLOCK_ANCHOR_MAX_MAD_SEC`.
    """
    anchors: list[float] = []
    for wall_ts, request_id in parse_analysis_requests(m5_log_text):
        stamp = _load_artifact_scene_stamp(run_dir, request_id)
        if stamp is None:
            continue
        monotonic = stamp_to_monotonic(clock, stamp)
        if monotonic is not None:
            anchors.append(wall_ts - monotonic)
    if not anchors:
        raise ClockReconciliationError(
            f"{run_dir.name}: scene stamps are sim-time but no clock anchor is usable "
            "(needs `starting analysis request=` lines whose decision artifact in "
            f"{'/'.join(DECISION_DIR_NAMES)} carries a scene stamp inside the scene log's range)"
        )
    offset = statistics.median(anchors)
    mad = statistics.median(abs(a - offset) for a in anchors)
    if mad > CLOCK_ANCHOR_MAX_MAD_SEC:
        raise ClockReconciliationError(
            f"{run_dir.name}: {len(anchors)} clock anchors disagree (median absolute "
            f"deviation {mad:.3f} s > {CLOCK_ANCHOR_MAX_MAD_SEC} s)"
        )
    return offset, len(anchors), max(anchors) - min(anchors)


def resolve_scene_clock(
    run_dir: Path, m5_log_text: str, scene_files: list[Path]
) -> tuple[ClockResolution, Callable[[float], float] | None]:
    """Detect the run's clock era and, in the sim era, build the stamp mapping.

    Args:
        run_dir: One run directory.
        m5_log_text: Full text of the run's M5 log.
        scene_files: The run's scene-log files (may be empty).

    Returns:
        `(resolution, to_wall)`: `to_wall` maps a scene or robot stamp to
        wall-clock epoch seconds in the sim era, and is None otherwise
        (stamps are used unchanged).

    Raises:
        ClockReconciliationError: Sim-era stamps that cannot be mapped
            (non-monotonic stamps, no or inconsistent anchors).
    """
    records = load_scene_clock(scene_files) if scene_files else []
    era = detect_clock_era([s for s, _ in records], parse_log_epochs(m5_log_text))
    if era != "sim":
        return ClockResolution(era=era), None
    if any(t is None for _, t in records):
        raise ClockReconciliationError(
            f"{run_dir.name}: sim-time scene stamps but some scene-log records lack the "
            "monotonic `t` column; cannot map them to wall time"
        )
    if any(b[0] <= a[0] for a, b in zip(records, records[1:], strict=False)):
        raise ClockReconciliationError(
            f"{run_dir.name}: sim-time scene stamps are not strictly increasing in log "
            "order (clock reset mid-session?); cannot map them to wall time"
        )
    offset, count, spread = derive_wall_offset(run_dir, m5_log_text, records)

    def to_wall(stamp: float) -> float:
        # Interpolating the robot's own stamp (not subtracting its sim-second
        # age from a wall time) keeps a STALE robot's age in wall seconds.
        return stamp_to_monotonic(records, stamp, extrapolate=True) + offset

    resolution = ClockResolution(
        era="sim", offset_sec=offset, anchor_count=count, anchor_spread_sec=spread
    )
    return resolution, to_wall


def check_events_reconciled(
    run_name: str,
    events: list[ArrivalEvent],
    scene_by_robot: dict[str, list[SceneSample]],
    era: ClockEra,
) -> None:
    """Refuse to score events that fall outside the scene log's time span.

    Args:
        run_name: Run directory name, for the error message.
        events: Arrival events to be scored (wall-clock `ts`).
        scene_by_robot: Scene samples on the wall clock (after any mapping).
        era: The run's detected era, for the error message.

    Raises:
        ClockReconciliationError: An event lies more than
            `CLOCK_RECONCILE_WINDOW_SEC` outside the span of scene stamps.
    """
    stamps = [s.stamp for series in scene_by_robot.values() for s in series]
    if not stamps or not events:
        return
    lo, hi = min(stamps), max(stamps)
    for event in events:
        if not lo - CLOCK_RECONCILE_WINDOW_SEC <= event.ts <= hi + CLOCK_RECONCILE_WINDOW_SEC:
            raise ClockReconciliationError(
                f"{run_name}: {event.robot_id} arrival at {event.ts:.3f} is outside the "
                f"scene-log span [{lo:.3f}, {hi:.3f}] +/- {CLOCK_RECONCILE_WINDOW_SEC} s "
                f"(clock era {era}); scene stamps and M5 events are not on one clock"
            )


def load_scene_log(
    scene_files: list[Path], to_wall: Callable[[float], float] | None = None
) -> dict[str, list[SceneSample]]:
    """Load and merge scene-log JSONL files into per-robot sample series.

    Args:
        scene_files: Scene-log files for one run (see `locate_scene_files`).
        to_wall: Stamp-to-wall-clock mapping from `resolve_scene_clock` for
            sim-era runs; None keeps stamps as logged (wall era).

    Returns:
        Robot id -> samples sorted by `stamp`, on the M5 log's wall clock.
    """
    samples: dict[str, list[SceneSample]] = {}
    for record in _iter_scene_records(scene_files):
        for robot in record["scene"]["robots"]:
            stamp = robot["stamp"] if to_wall is None else to_wall(robot["stamp"])
            samples.setdefault(robot["robot_id"], []).append(
                SceneSample(stamp=stamp, x=robot["x"], y=robot["y"], status=robot["status"])
            )
    for series in samples.values():
        series.sort(key=lambda s: s.stamp)
    return samples


def load_ground_truth(gt_file: Path) -> dict[str, list[GTRow]]:
    """Load a ground-truth JSONL file into per-robot rows sorted by sim time.

    Args:
        gt_file: Path from `locate_gt_file`.

    Returns:
        Robot id -> GT rows sorted by `sim_time_sec`.
    """
    rows: dict[str, list[GTRow]] = {}
    for line in gt_file.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        sim_t = record["sim_time_sec"]
        for robot_id, robot in record["robots"].items():
            rows.setdefault(robot_id, []).append(
                GTRow(
                    sim_time_sec=sim_t,
                    x=robot["x"],
                    y=robot["y"],
                    dist_to_goal_m=robot["distance_to_goal_m"],
                    goal=(robot["goal_x"], robot["goal_y"]),
                )
            )
    for series in rows.values():
        series.sort(key=lambda r: r.sim_time_sec)
    return rows


def nearest_scene_sample(samples: list[SceneSample], ts: float) -> SceneSample | None:
    """Return the scene sample nearest `ts` in absolute time, or None if empty."""
    if not samples:
        return None
    return min(samples, key=lambda s: abs(s.stamp - ts))


def nearest_gt_by_position(rows: list[GTRow], xy: tuple[float, float]) -> tuple[GTRow, float]:
    """Return the GT row whose position is nearest `xy`, and that distance.

    Nearest-position match (not nearest-time) is used because `sim_time_sec`
    has no calibrated correspondence to the M5 log's epoch timestamps in the
    recorded data (see module docstring). `xy` is normally the M1 estimate
    near the report time, so the returned row approximates "ground truth at
    the same moment M1 saw this position" without needing a clock mapping.

    Args:
        rows: One robot's GT rows for the run (must be non-empty).
        xy: Reference position, in metres.

    Returns:
        `(matched_row, residual_m)` where `residual_m` is the distance
        between `xy` and the matched row's position — small residuals
        corroborate the match; large ones flag a dwell-segment mismatch.
    """
    best = min(rows, key=lambda r: math.dist((r.x, r.y), xy))
    return best, math.dist((best.x, best.y), xy)


def extract_metadata(run_dir: Path, orchestrator_yaml: Path | None) -> dict[str, str]:
    """Best-effort scenario/backend/order/gate metadata for one run.

    Args:
        run_dir: One run directory.
        orchestrator_yaml: Result of `locate_orchestrator_yaml`, if any.

    Returns:
        Dict with keys `scenario`, `backend`, `order_mode`, `gate_mode`;
        values are `"unknown"` (scenario/backend/order) or `"n/a (pre-gate)"`
        (gate) when not recoverable — the four oldest runs (E0, R1-R4)
        predate both the recorded scenario line format used here and the
        gate feature itself.
    """
    meta = {
        "scenario": "unknown",
        "backend": "unknown",
        "order_mode": "unknown",
        "gate_mode": "n/a (pre-gate)",
    }
    if orchestrator_yaml is not None:
        text = orchestrator_yaml.read_text(errors="replace")
        m = re.search(r"^reasoning_backend_id:\s*(\S+)", text, re.MULTILINE)
        if m:
            meta["backend"] = m.group(1)
        m = re.search(r"^prompt_robot_order:\s*(\S+)", text, re.MULTILINE)
        if m:
            meta["order_mode"] = m.group(1)
        m = re.search(r'^grounding_yield_feasibility:\s*"?(\w+)"?', text, re.MULTILINE)
        if m:
            meta["gate_mode"] = m.group(1)
    # Top-level *.log only (not component_logs/): the "starting Isaac Sim" /
    # "reasoning_backend_id: X -> Y" lines this looks for live in whichever
    # launcher-style log the run happened to be captured under -- observed
    # names include launcher.log, launcher_g0.log, fc_step1.log and
    # step_r1.log across this dataset's runs.
    log_candidates = sorted(run_dir.glob("*.log"))
    for log_path in log_candidates:
        text = log_path.read_text(errors="replace")
        if meta["scenario"] == "unknown":
            m = re.search(r"starting Isaac Sim (\S+) \(headless", text)
            if m:
                meta["scenario"] = m.group(1)
        if meta["backend"] == "unknown":
            m = re.search(r"reasoning_backend_id:\s*\S+\s*->\s*(\S+)", text)
            if m:
                meta["backend"] = m.group(1)
    return meta


@dataclass
class EventRow:
    """One CSV row: one M5-reported arrival-related event, fully scored."""

    values: dict[str, object] = field(default_factory=dict)


def score_run(
    run_dir: Path,
    tolerance_m: float,
    max_age_sec: float,
    scenarios_dir: Path = DEFAULT_SCENARIOS_DIR,
) -> tuple[list[EventRow], list[str]]:
    """Re-score every arrival event in one run against M1 and ground truth.

    Args:
        run_dir: One `data/logs/vm_runs/<STAMP>` directory.
        tolerance_m: Position tolerance corroborating an arrival (mirrors
            `arrival_position_tolerance_m`).
        max_age_sec: Oldest M1 estimate still considered corroborating
            (mirrors `arrival_estimate_max_age_sec`).
        scenarios_dir: Root holding the scenario YAMLs, searched for the run's
            scenario to read its static obstacle boxes.

    Returns:
        `(rows, notes)`: per-event CSV rows, and human-readable notes about
        fallbacks taken for this run (e.g. no scene log).

    Raises:
        ClockReconciliationError: The scene log's stamps cannot be put on the
            M5 log's wall clock (see `resolve_scene_clock` and
            `check_events_reconciled`).
    """
    notes: list[str] = []
    m5_log_path = locate_m5_log(run_dir)
    m5_text = m5_log_path.read_text(errors="replace")
    events = parse_arrival_events(m5_text)
    first_analysis_ts = parse_first_starting_analysis(m5_text)
    session_id = parse_session_id(m5_text)

    scene_files = locate_scene_files(run_dir, session_id)
    if session_id is not None and not scene_files:
        notes.append(f"no scene file matched session_id={session_id}")
    clock, to_wall = resolve_scene_clock(run_dir, m5_text, scene_files)
    if clock.era == "sim":
        notes.append(
            f"sim-time scene stamps mapped to wall clock: wall = t + {clock.offset_sec:.3f} "
            f"(wall-minus-monotonic from {clock.anchor_count} analysis anchors, "
            f"spread {clock.anchor_spread_sec:.3f} s)"
        )
    scene_by_robot = load_scene_log(scene_files, to_wall) if scene_files else {}
    no_scene_log = not scene_files
    if no_scene_log:
        notes.append("no scene log found; M1 verdict falls back to ground truth only")
    check_events_reconciled(
        run_dir.name, [e for e in events if e.kind == "reported"], scene_by_robot, clock.era
    )

    gt_file = locate_gt_file(run_dir)
    gt_by_robot = load_ground_truth(gt_file)
    gt_min_dist: dict[str, float] = {
        robot_id: min(r.dist_to_goal_m for r in rows) for robot_id, rows in gt_by_robot.items()
    }

    orchestrator_yaml = locate_orchestrator_yaml(run_dir)
    meta = extract_metadata(run_dir, orchestrator_yaml)
    scenario_yaml = locate_scenario_yaml(meta["scenario"], scenarios_dir)
    boxes = load_obstacle_boxes(scenario_yaml) if scenario_yaml is not None else []
    if scenario_yaml is None and meta["scenario"] != "unknown":
        notes.append(f"scenario {meta['scenario']} not found under {scenarios_dir}")

    # First accepted-report epoch per robot, by each rule, for the run-level
    # outcome and the "first analysis -> last accepted arrival" timing.
    first_accepted_m1: dict[str, float] = {}
    first_accepted_gt: dict[str, float] = {}

    rows: list[EventRow] = []
    reported_events = [e for e in events if e.kind == "reported"]
    per_robot_index: dict[str, int] = {}
    for event in reported_events:
        idx = per_robot_index.get(event.robot_id, 0)
        per_robot_index[event.robot_id] = idx + 1

        goal = event.goal or (
            gt_by_robot[event.robot_id][0].goal if event.robot_id in gt_by_robot else None
        )

        sample = None
        if event.robot_id in scene_by_robot:
            sample = nearest_scene_sample(scene_by_robot[event.robot_id], event.ts)
        m1_estimate_age = abs(sample.stamp - event.ts) if sample else None
        m1_position = (sample.x, sample.y) if sample else None

        if goal is not None:
            check: ArrivalCheck = classify_arrival(
                reported_goal=goal,
                estimated_position=m1_position,
                tolerance_m=tolerance_m,
                estimate_age_sec=m1_estimate_age,
                max_estimate_age_sec=max_age_sec,
            )
        else:
            check = ArrivalCheck(accepted=True, distance_m=None, reason="no_estimate")
            notes.append(f"{event.robot_id}: no goal recoverable for event at {event.ts}")

        gt_row = gt_dist = gt_residual = None
        if m1_position is not None and event.robot_id in gt_by_robot:
            gt_row, gt_residual = nearest_gt_by_position(gt_by_robot[event.robot_id], m1_position)
            gt_dist = gt_row.dist_to_goal_m
        elif event.robot_id in gt_by_robot and goal is not None:
            # No M1 estimate at all: fall back to GT's own final resting
            # position (the robot does not move again after a reported
            # arrival in every run inspected for this dataset).
            gt_row = gt_by_robot[event.robot_id][-1]
            gt_dist = gt_row.dist_to_goal_m
            gt_residual = None
            notes.append(
                f"{event.robot_id}: no M1 estimate near report at {event.ts}; "
                "GT distance taken from the run's final GT row"
            )

        gt_accepted = gt_dist is not None and gt_dist <= tolerance_m

        if check.accepted and check.reason == "within_tolerance":
            first_accepted_m1.setdefault(event.robot_id, event.ts)
        elif check.reason in ("no_estimate", "stale_estimate"):
            # Legacy pass-through: unverified, not evidence either way.
            pass
        if gt_accepted:
            first_accepted_gt.setdefault(event.robot_id, event.ts)

        bias = None
        if check.distance_m is not None and gt_dist is not None:
            bias = check.distance_m - gt_dist

        # Only a position-verified accept has a pose the verdict rests on;
        # pass-through accepts and rejects carry no claim to check.
        box_overlap: bool | None = None
        box_overlap_obstacle: str | None = None
        if boxes and check.reason == "within_tolerance" and m1_position is not None:
            box_overlap_obstacle = overlapping_obstacle(m1_position, boxes)
            box_overlap = box_overlap_obstacle is not None
            if box_overlap:
                notes.append(
                    f"WARNING {event.robot_id}: accepted arrival at "
                    f"({m1_position[0]:.3f}, {m1_position[1]:.3f}) overlaps "
                    f"{box_overlap_obstacle} (box grown by {ROBOT_HALF_WIDTH_M} m)"
                )

        row = EventRow(
            values={
                "stamp": run_dir.name,
                "scenario": meta["scenario"],
                "backend": meta["backend"],
                "order_mode": meta["order_mode"],
                "gate_mode": meta["gate_mode"],
                "robot_id": event.robot_id,
                "event_index": idx,
                "event_kind": event.kind,
                "m5_reported_epoch": event.ts,
                "goal_x": goal[0] if goal else None,
                "goal_y": goal[1] if goal else None,
                "m1_estimate_x": m1_position[0] if m1_position else None,
                "m1_estimate_y": m1_position[1] if m1_position else None,
                "m1_estimate_age_sec": m1_estimate_age,
                "m1_estimate_status": sample.status if sample else None,
                "m1_dist_m": check.distance_m,
                "m1_verdict": check.reason,
                "gt_matched_sim_time_sec": gt_row.sim_time_sec if gt_row else None,
                "gt_matched_x": gt_row.x if gt_row else None,
                "gt_matched_y": gt_row.y if gt_row else None,
                "gt_dist_m": gt_dist,
                "gt_match_residual_m": gt_residual,
                "gt_min_dist_m": gt_min_dist.get(event.robot_id),
                "m1_minus_gt_bias_m": bias,
                "flipped": bool(check.distance_m is not None and not check.accepted),
                "robot_arrived_m1": None,  # filled once all events are scored
                "robot_arrived_gt": None,
                "run_both_arrived_m1": None,
                "run_both_arrived_gt": None,
                "first_starting_analysis_epoch": first_analysis_ts,
                "resolution_sec": None,
                "no_scene_log": no_scene_log,
                "box_overlap": box_overlap,
                "box_overlap_obstacle": box_overlap_obstacle,
                "clock_era": clock.era,
                "clock_offset_sec": clock.offset_sec,
                "clock_anchor_count": clock.anchor_count,
                "clock_anchor_spread_sec": clock.anchor_spread_sec,
            }
        )
        rows.append(row)

    # Ground truth and the reported events are authoritative on which robots
    # exist; the scene log is excluded here because M1 can emit a spurious
    # extra id from a marker misdetection (e.g. "robot_17" in
    # `20260924_205009`) that never appears in ground truth or in any report,
    # and including it would make every run look permanently short one robot.
    robots_in_run = set(gt_by_robot) | {e.robot_id for e in reported_events}
    both_arrived_m1 = all(r in first_accepted_m1 for r in robots_in_run) and bool(robots_in_run)
    both_arrived_gt = all(r in first_accepted_gt for r in robots_in_run) and bool(robots_in_run)
    resolution_sec: float | str | None = None
    if first_analysis_ts is not None:
        if both_arrived_m1:
            resolution_sec = max(first_accepted_m1.values()) - first_analysis_ts
        else:
            missing = sorted(robots_in_run - set(first_accepted_m1))
            partial = ", ".join(
                f"{r} @ {first_accepted_m1[r] - first_analysis_ts:.1f}s"
                for r in sorted(first_accepted_m1)
            )
            resolution_sec = f"n/a (missing {missing}; accepted so far: {partial or 'none'})"

    for row in rows:
        rid = row.values["robot_id"]
        row.values["robot_arrived_m1"] = rid in first_accepted_m1
        row.values["robot_arrived_gt"] = rid in first_accepted_gt
        row.values["run_both_arrived_m1"] = both_arrived_m1
        row.values["run_both_arrived_gt"] = both_arrived_gt
        row.values["resolution_sec"] = resolution_sec

    return rows, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, default=Path("data/logs/vm_runs"))
    parser.add_argument("--tolerance-m", type=float, default=DEFAULT_TOLERANCE_M)
    parser.add_argument("--max-age-sec", type=float, default=DEFAULT_MAX_AGE_SEC)
    parser.add_argument("--scenarios-dir", type=Path, default=DEFAULT_SCENARIOS_DIR)
    parser.add_argument(
        "--out", type=Path, default=Path("data/logs/vm_runs/ARRIVALS_RESCORED.csv")
    )
    args = parser.parse_args()

    run_dirs = find_run_dirs(args.runs_dir)
    if not run_dirs:
        print(f"no run directories found under {args.runs_dir}", file=sys.stderr)
        return 1

    all_rows: list[EventRow] = []
    for run_dir in run_dirs:
        try:
            rows, notes = score_run(
                run_dir, args.tolerance_m, args.max_age_sec, args.scenarios_dir
            )
        except RunDataError as exc:
            print(f"SKIP {run_dir.name}: {exc}", file=sys.stderr)
            continue
        except ClockReconciliationError as exc:
            print(f"ERROR {exc}; aborting, no CSV written", file=sys.stderr)
            return 2
        for note in notes:
            print(f"{run_dir.name}: {note}", file=sys.stderr)
        all_rows.extend(rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row.values)

    n_runs = len({row.values["stamp"] for row in all_rows})
    n_flipped = sum(1 for row in all_rows if row.values["flipped"])
    n_overlap = sum(1 for row in all_rows if row.values["box_overlap"])
    print(
        f"scored {len(all_rows)} arrival events across {n_runs} runs; "
        f"{n_flipped} flipped (Nav2-reported, rejected at {args.tolerance_m} m); "
        f"{n_overlap} accepted inside a box grown by {ROBOT_HALF_WIDTH_M} m -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

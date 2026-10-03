#!/usr/bin/env python3
"""Ground-truth scorers for the coverage scenes B1, B2 and B3.

The unified scene design (`docs/superpowers/specs/2026-09-29-unified-scene-design.md`)
registers per-scene metrics that the arrival re-scorer does not compute. This
tool computes them offline from Isaac's `ground_truth.jsonl` (sim time, true
poses, 10 Hz), following the T2b forced-order scorer, whose arrival rule it
reuses (`scripts/t2b_forced_order.py`: within 0.35 m of the goal and never
farther than 0.5 m afterwards; t0 is the first sample with any robot faster
than 0.03 m/s).

Subcommands:

- `conflict --scenario S --gt DIR`: the GT bottleneck-conflict timeline for an
  aperture scene (B1 `bottleneck_merge`, B3 `convoy_counterflow`), from
  `isaac.vgu_sim.oracle.bottleneck_conflict_active`, against the scenario's
  `expected_conflict.onset_window_sec`.
- `b1 --gt DIR`: B1 gate flow (robots exiting the gate's far mouth per
  100 sim-s, first entry to last exit, lane crossings only), per-robot stop
  time (speed < 0.02 m/s summed over spells >= 1 s, t0 to arrival), makespan
  (t0 to the last arrival), the merge mode and synchrony, and the conflict
  timeline.
- `b2 --run MEMBER:SEED:DIR ...`: B2 %CP, per episode (the urgent robot makes
  the final x = 0 crossing toward its goal first) and per seed-matched pair
  (divergent-and-correct: urgent first in both members). A `:DECISIONS` suffix
  adds the decision-level route read off the run's first yield-deciding M5
  artifact.
- `b3 --gt DIR`: B3 first-to-slip (`convoy_counterflow_slip`) -- which
  platoon member (`oracle.platoon`) is first to sustain a departure from its
  own GT position at conflict onset (`slip_onset_sec`), its identity
  (`first_slipper`) and latency relative to the conflict onset, plus the
  conflict timeline.
- `ib10 --gt DIR [--decisions DIR] [--m5-log F] [--m4-log F] [--scene F]`:
  the IB10 `junction_clear` resolution oracle (`intersection_bottleneck`
  `oracle:` block) -- the formed-jam validity gate, chi-pair correctness
  (proposed and executed), inside-first order, the phase-reached ordinal
  with the `fallback`/`fallback_exhausted` flags, CrossingChain release
  attribution and yielder-last, position-verified arrivals, the derived
  `outcome_rank`, the tracked-band check and the STALE-streak
  instrumentation.
- `loop --scenario S --gt DIR [--decisions DIR] [--scene F] [--sampler F]`:
  one loop-detour run (prereg-v2 (b), `loop_detour_*`): robot_1's
  time-to-goal (censored when it never arrives), its stall onset and pose,
  whether and when it entered the loop (y > 0.6), the first dispatched
  decision's strategy and stamp, the self-detour flag (entered the loop
  with no reroute dispatched before it -- Nav2 pre-empting the decision
  layer), the decision's oracle correctness and `outcome_rank`, the
  tracked-band check and the STALE streaks.
- `loop-cost --table F`: turn a `scripts/strategy_regret.py score` cost
  table for a `loop_detour_*` scene into the scenario's `oracle.cost`
  record (`LoopDetourCostRecord`), validated.

Definitions fixed before any smoke run (2026-09-29; B3 first-to-slip added
2026-10-02; IB10 frozen 2026-10-03, step-7b Part 3); see each function.

Usage:
    python3 scripts/coverage_scene_scores.py conflict --scenario convoy_counterflow --gt runs/x/gt
    python3 scripts/coverage_scene_scores.py b1 --gt runs/b1_smoke/gt --out b1.json
    python3 scripts/coverage_scene_scores.py b2 --run r1:42:runs/r1/gt --run r2:42:runs/r2/gt
    python3 scripts/coverage_scene_scores.py b3 --gt runs/b3_slip_smoke/gt --out b3.json
    python3 scripts/coverage_scene_scores.py ib10 --gt runs/ib10/gt \
        --decisions runs/ib10/decisions --m5-log runs/ib10/m5.log \
        --m4-log runs/ib10/m4.log --scene runs/ib10/scene.jsonl
    python3 scripts/coverage_scene_scores.py loop --scenario loop_detour_permanent \
        --gt runs/perm_wait/gt --decisions runs/perm_wait/decisions \
        --scene runs/perm_wait/m5_scene.jsonl --sampler runs/perm_wait/sampler.jsonl
    python3 scripts/coverage_scene_scores.py loop-cost --table perm_cost_table.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from isaac.vgu_sim.oracle import (  # noqa: E402
    bottleneck_conflict_active,
    intersection_conflict_active,
)
from reasoning.rag.maneuver_geometry import (  # noqa: E402
    load_grounding_params,
    rank_recede_candidates,
)
from reasoning.rag.scene_geometry import SceneGeometry  # noqa: E402
from reasoning.vlm.models import RobotStateInput, SnapshotFrame  # noqa: E402
from scripts.strategy_regret import SCENES  # noqa: E402
from scripts.t2b_forced_order import score_ground_truth  # noqa: E402

SCENARIOS_DIR = REPO_ROOT / "isaac" / "config" / "scenarios"
# Design, B1 metrics: "GT speed < 0.02 m/s summed over >= 1 s spells".
STOP_SPEED_MPS = 0.02
STOP_MIN_SPELL_SEC = 1.0
# Transit speed (tuning basket), used only to extrapolate a robot that
# latched short of its merge reference point.
TRANSIT_SPEED_MPS = 0.15
# B1 design reference points: robot_1 reaches the merge ~(0.10, 0), robot_2
# its latch pose ~(0.15, 0.45); dt = t(robot_2) - t(robot_1), designed +1.4 s.
B1_MERGE_REFERENCE = {"robot_1": (0.10, 0.0), "robot_2": (0.15, 0.45)}
B1_REACHED_M = 0.05
# A perpendicular latch: robot_2 still heading down its arm (design: -70 to
# -90 deg), taken as within 45 deg of -90 deg.
B1_PERPENDICULAR_HEADING_DEG = (-135.0, -45.0)
# B3 first-to-slip (design docs/superpowers/specs/2026-09-30-prereg-v2-design.md
# "(e)"): a platoon member "slips" once its departure from its own GT position
# at conflict onset is sustained for at least this long, past this threshold.
SLIP_DISPLACEMENT_THRESHOLD_M = 0.05
SLIP_HOLD_MIN_SEC = 1.0
# IB10 (step-7b Part 3): `isaac.vgu_sim.oracle.intersection_conflict_active`'s
# own membership radius, re-read here only to count robots inside it at onset.
IB10_JAM_RADIUS_M = 1.0
# M1's verified tracked band (intersection_bottleneck.yaml header): |x| <= 2.5,
# |y| <= 1.80 (the study's abort criterion for the N-S arms).
IB10_TRACKED_BAND_M = (2.5, 1.80)
# Ordinal partial score (oracle.phase_ordinal); 0 when no junction_clear
# phase was ever dispatched.
IB10_PHASE_NONE = "none"
# Loop-detour family (prereg-v2 (b)): the primary aisle's north edge; any
# robot_1 GT sample (or Nav2 global-plan pose) north of it is in the
# connector band / far aisle, i.e. on the loop.
LOOP_ENTRY_Y_M = 0.6
# M1's verified tracked band for the loop map (y-extent report Run B and the
# loop smoke's coverage probe): |x| <= 2.5, |y| <= 2.0.
LOOP_TRACKED_BAND_M = (2.5, 2.0)
_PHASE_ADVANCE_RE = re.compile(r"junction_clear phase advance .*phase_reached=(\w+) done=(\w+)")
_GATE_RE = re.compile(
    r"crossing_chain (gate_admit|gate_cleared|gate_release) command=(\S+) yielder=(\S+)"
    r"(?: passer=(\S+))?.*?(?:reason=(\w+) )?sim_t=([-\d.]+)"
)


@dataclass(frozen=True)
class Sample:
    """One robot at one ground-truth instant."""

    t: float
    x: float
    y: float
    theta: float
    speed: float
    distance_to_goal: float | None


def load_ground_truth(gt_dir: Path) -> dict[str, list[Sample]]:
    """Load `ground_truth.jsonl` into per-robot samples sorted by sim time.

    Args:
        gt_dir: Directory holding `ground_truth.jsonl`.

    Returns:
        Robot id -> samples.

    Raises:
        ValueError: If the file holds no samples.
    """
    series: dict[str, list[Sample]] = {}
    text = (gt_dir / "ground_truth.jsonl").read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        for robot_id, robot in row["robots"].items():
            series.setdefault(robot_id, []).append(
                Sample(
                    t=row["sim_time_sec"], x=robot["x"], y=robot["y"],
                    theta=robot.get("theta", 0.0), speed=robot["speed_mps"],
                    distance_to_goal=robot.get("distance_to_goal_m"),
                )
            )
    if not series:
        raise ValueError(f"{gt_dir}: empty ground truth")
    for samples in series.values():
        samples.sort(key=lambda s: s.t)
    return series


def load_scenario(name: str, scenarios_dir: Path = SCENARIOS_DIR) -> dict[str, Any]:
    """Read a scenario YAML by name (top level, then `family/`)."""
    for path in (scenarios_dir / f"{name}.yaml", scenarios_dir / "family" / f"{name}.yaml"):
        if path.is_file():
            return yaml.safe_load(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"scenario {name!r} not under {scenarios_dir}")


def gate_span(scenario: dict[str, Any]) -> tuple[float, float]:
    """The aperture's world x span from the scenario's `aisle_barrier`."""
    barrier = scenario["aisle_barrier"]
    half = barrier["length_m"] / 2.0
    return (barrier["center_x_m"] - half, barrier["center_x_m"] + half)


def lane_half_width(scenario: dict[str, Any]) -> float:
    """Half the aperture's effective width (0.275 m for C55)."""
    return scenario["aisle_barrier"]["effective_width_m"] / 2.0


def _instants(series: dict[str, list[Sample]]) -> list[tuple[float, dict[str, Sample]]]:
    by_time: dict[float, dict[str, Sample]] = {}
    for robot_id, samples in series.items():
        for sample in samples:
            by_time.setdefault(sample.t, {})[robot_id] = sample
    return sorted(by_time.items())


def conflict_timeline(
    series: dict[str, list[Sample]], span: tuple[float, float]
) -> dict[str, Any]:
    """Evaluate `bottleneck_conflict_active` at every GT instant.

    Args:
        series: Per-robot GT samples.
        span: The aperture's x span.

    Returns:
        `onset_sec` (first active instant), `active_sec` (sum of active sample
        periods), `last_active_sec`, `n_intervals` and the `intervals` list
        of `[start, end]` sim-s.
    """
    intervals: list[list[float]] = []
    active_sec = 0.0
    previous_t: float | None = None
    for t, robots in _instants(series):
        ids = sorted(robots)
        active = bottleneck_conflict_active(
            [(robots[r].x, robots[r].y) for r in ids],
            [robots[r].speed for r in ids],
            span,
            distances_to_goal=[robots[r].distance_to_goal for r in ids],
        )
        if active:
            if intervals and intervals[-1][1] == previous_t:
                intervals[-1][1] = t
            else:
                intervals.append([t, t])
            if previous_t is not None:
                active_sec += t - previous_t
        previous_t = t
    return {
        "onset_sec": intervals[0][0] if intervals else None,
        "last_active_sec": intervals[-1][1] if intervals else None,
        "active_sec": round(active_sec, 2),
        "n_intervals": len(intervals),
        "intervals": [[round(a, 2), round(b, 2)] for a, b in intervals],
    }


def score_conflict(scenario: dict[str, Any], series: dict[str, list[Sample]]) -> dict[str, Any]:
    """The conflict timeline checked against the scenario's expected conflict.

    Args:
        scenario: The scenario YAML as a dict (needs `aisle_barrier`).
        series: Per-robot GT samples.

    Returns:
        The timeline plus `onset_window_sec`, `onset_in_window` and
        `min_duration_met` (longest interval >= `min_duration_sec`).
    """
    timeline = conflict_timeline(series, gate_span(scenario))
    expected = scenario.get("expected_conflict") or {}
    window = expected.get("onset_window_sec")
    onset = timeline["onset_sec"]
    longest = max((b - a for a, b in timeline["intervals"]), default=0.0)
    return {
        **timeline,
        "onset_window_sec": window,
        "onset_in_window": (
            None if window is None or onset is None else window[0] <= onset <= window[1]
        ),
        "longest_interval_sec": round(longest, 2),
        "min_duration_met": longest >= expected.get("min_duration_sec", 0.0),
    }


def stop_time_sec(
    samples: list[Sample], start: float, end: float,
    speed_mps: float = STOP_SPEED_MPS, min_spell_sec: float = STOP_MIN_SPELL_SEC,
) -> float:
    """Sum of stopped spells of at least `min_spell_sec` inside [start, end].

    Args:
        samples: One robot's GT samples.
        start: Window start (sim-s), normally t0.
        end: Window end (sim-s), normally the robot's arrival or the episode end.
        speed_mps: A sample slower than this is stopped.
        min_spell_sec: Shorter spells are not counted.

    Returns:
        Stopped seconds.
    """
    window = [s for s in samples if start <= s.t <= end]
    total = 0.0
    spell_start: float | None = None
    last_t: float | None = None
    for sample in window:
        if sample.speed < speed_mps:
            if spell_start is None:
                spell_start = sample.t
            last_t = sample.t
            continue
        if spell_start is not None and last_t - spell_start >= min_spell_sec:
            total += last_t - spell_start
        spell_start = None
    if spell_start is not None and last_t - spell_start >= min_spell_sec:
        total += last_t - spell_start
    return round(total, 2)


def gate_passage(
    samples: list[Sample], span: tuple[float, float], half_width: float, lane_y: float = 0.0
) -> tuple[float | None, float | None]:
    """A robot's eastbound passage through the gate, lane crossings only.

    The exit is the LAST eastward crossing of the far mouth (x = span high)
    made inside the lane (|y - lane_y| < half_width); the entry is the last
    eastward crossing of the near mouth, inside the lane, before that exit.

    Args:
        samples: One robot's GT samples.
        span: The aperture's x span.
        half_width: The lane's half width.
        lane_y: The lane centreline's y.

    Returns:
        `(entry_sec, exit_sec)`; None where the crossing never happened.
    """
    def crossings(x_mouth: float) -> list[float]:
        out = []
        for a, b in zip(samples, samples[1:], strict=False):
            if a.x < x_mouth <= b.x and abs(b.y - lane_y) < half_width:
                out.append(b.t)
        return out

    exits = crossings(span[1])
    if not exits:
        return None, None
    exit_t = exits[-1]
    entries = [t for t in crossings(span[0]) if t <= exit_t]
    return (entries[-1] if entries else None), exit_t


def _reference_time(samples: list[Sample], ref: tuple[float, float], until: float) -> float | None:
    window = [s for s in samples if s.t <= until]
    if not window:
        return None
    closest = min(window, key=lambda s: math.dist((s.x, s.y), ref))
    shortfall = max(0.0, math.dist((closest.x, closest.y), ref) - B1_REACHED_M)
    return closest.t + shortfall / TRANSIT_SPEED_MPS


def b1_merge(
    series: dict[str, list[Sample]], onset: float | None, t0: float,
    span: tuple[float, float], half_width: float,
) -> dict[str, Any]:
    """B1 merge synchrony and mode.

    `merge_dt_sec` = t(robot_2) - t(robot_1) at the design's reference points
    (robot_1 the merge (0.10, 0), robot_2 its latch pose (0.15, 0.45)), each
    taken as the robot's closest approach up to the conflict onset plus, for a
    robot that stopped short, the remaining distance at 0.15 m/s; positive
    means robot_1 led (designed +1.4 s).

    `merge_mode`: `no_event` without a conflict before robot_1 exits the gate;
    `follower_latch` when robot_2 is inside the lane east of robot_1 at onset
    (it turned into the gate first); `perpendicular_latch` when robot_2 heads
    within 45 deg of -90 deg at onset; `other` otherwise.
    `robot_2_east_of_robot_1` at onset separates the level-or-past sub-case
    (d) (False), which Arm B reads `blocked_path [robot_1]`.

    Args:
        series: Per-robot GT samples.
        onset: Conflict onset (sim-s) or None.
        t0: First departure.
        span: The gate's x span.
        half_width: The lane's half width.

    Returns:
        The merge record.
    """
    r1, r2 = series["robot_1"], series["robot_2"]
    _entry, r1_exit = gate_passage(r1, span, half_width)
    record: dict[str, Any] = {"onset_sec": onset}
    if onset is None or (r1_exit is not None and r1_exit < onset):
        record["merge_mode"] = "no_event"
        return record
    at = {rid: min(series[rid], key=lambda s: abs(s.t - onset)) for rid in ("robot_1", "robot_2")}
    p1, p2 = at["robot_1"], at["robot_2"]
    heading2 = math.degrees(math.atan2(math.sin(p2.theta), math.cos(p2.theta)))
    t_r1 = _reference_time(r1, B1_MERGE_REFERENCE["robot_1"], onset)
    t_r2 = _reference_time(r2, B1_MERGE_REFERENCE["robot_2"], onset)
    if abs(p2.y) < half_width and p2.x > p1.x:
        mode = "follower_latch"
    elif B1_PERPENDICULAR_HEADING_DEG[0] <= heading2 <= B1_PERPENDICULAR_HEADING_DEG[1]:
        mode = "perpendicular_latch"
    else:
        mode = "other"
    record.update(
        merge_mode=mode,
        merge_dt_sec=None if t_r1 is None or t_r2 is None else round(t_r2 - t_r1, 2),
        standoff_robot_1=[round(p1.x, 3), round(p1.y, 3)],
        standoff_robot_2=[round(p2.x, 3), round(p2.y, 3)],
        robot_2_heading_deg=round(heading2, 1),
        standoff_gap_m=round(math.dist((p1.x, p1.y), (p2.x, p2.y)), 3),
        robot_2_east_of_robot_1=p2.x > p1.x,
        onset_after_t0_sec=round(onset - t0, 2),
    )
    return record


def score_b1(gt_dir: Path, scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    """All B1 metrics for one run.

    Args:
        gt_dir: The run's ground-truth directory.
        scenario: The scenario dict (default: `bottleneck_merge.yaml`).

    Returns:
        Arrivals, makespan, gate flow, per-robot stop time, merge record and
        conflict timeline.
    """
    scenario = scenario or load_scenario("bottleneck_merge")
    series = load_ground_truth(gt_dir)
    run = score_ground_truth("b1", gt_dir)
    span, half = gate_span(scenario), lane_half_width(scenario)
    passages = {rid: gate_passage(samples, span, half) for rid, samples in series.items()}
    entries = [e for e, x in passages.values() if e is not None and x is not None]
    exits = [x for _e, x in passages.values() if x is not None]
    flow = None
    if exits and entries and max(exits) > min(entries):
        flow = round(len(exits) / (max(exits) - min(entries)) * 100.0, 3)
    arrivals = {rid: (None if at is None else round(at - run.t0_sec, 2))
                for rid, at in run.arrivals_sec.items()}
    stops = {
        rid: stop_time_sec(
            series[rid], run.t0_sec,
            run.end_sec if run.arrivals_sec.get(rid) is None else run.arrivals_sec[rid],
        )
        for rid in sorted(series)
    }
    conflict = score_conflict(scenario, series)
    return {
        "scene": scenario.get("name"),
        "t0_sec": run.t0_sec,
        "end_sec": run.end_sec,
        "arrivals_after_t0_sec": arrivals,
        "n_arrived": sum(v is not None for v in arrivals.values()),
        "censored": run.censored,
        "makespan_sec": None if run.censored else round(
            max(run.arrivals_sec.values()) - run.t0_sec, 2),
        "gate": {
            "span_x": list(span),
            "passages": {rid: {"entry_sec": e, "exit_sec": x} for rid, (e, x) in
                         sorted(passages.items())},
            "n_exited": len(exits),
            "flow_per_100s": flow,
        },
        "stop_time_sec": stops,
        "merge": b1_merge(series, conflict["onset_sec"], run.t0_sec, span, half),
        "conflict": conflict,
    }


def final_crossing(samples: list[Sample], x_line: float, direction: float) -> float | None:
    """Time of a robot's final crossing of `x_line` in `direction`, if it stays past.

    A crossing counts only if the robot is still past the line at its last
    sample: a yielder that pokes past x = 0 at the standoff and then backs
    away never scores its early crossing.

    Args:
        samples: One robot's GT samples.
        x_line: The line's world x.
        direction: +1 for eastbound, -1 for westbound.

    Returns:
        Sim time of the last crossing toward the goal, or None.
    """
    if not samples or (samples[-1].x - x_line) * direction < 0:
        return None
    last = None
    for a, b in zip(samples, samples[1:], strict=False):
        if (a.x - x_line) * direction < 0 <= (b.x - x_line) * direction:
            last = b.t
    return last


def first_passer(
    series: dict[str, list[Sample]], x_line: float = 0.0
) -> tuple[str | None, dict[str, float | None]]:
    """Which robot made the final crossing of `x_line` toward its goal first.

    Args:
        series: Per-robot GT samples; each robot's direction is the sign of
            its net x travel (first to last sample), i.e. toward its goal.
        x_line: The line's world x (0 for the corridor centre).

    Returns:
        `(first passer or None, crossing times)`; a tie goes to the lower id.
    """
    times: dict[str, float | None] = {}
    for robot_id, samples in series.items():
        direction = 1.0 if samples[-1].x >= samples[0].x else -1.0
        times[robot_id] = final_crossing(samples, x_line, direction)
    crossed = {r: t for r, t in times.items() if t is not None}
    if not crossed:
        return None, times
    return min(crossed, key=lambda r: (crossed[r], r)), times


def _far_mouth_first(series: dict[str, list[Sample]], half_length: float) -> str | None:
    times = {
        "robot_1": final_crossing(series["robot_1"], half_length, 1.0),
        "robot_2": final_crossing(series["robot_2"], -half_length, -1.0),
    }
    crossed = {r: t for r, t in times.items() if t is not None}
    return min(crossed, key=lambda r: (crossed[r], r)) if crossed else None


def decision_route(decisions_dir: Path, urgent: str) -> dict[str, Any]:
    """The decision-level first passer from the run's dispatched decision.

    The dispatched decision is the artifact with a detected congestion, a
    grounded command and a `yield` or `priority_override` strategy. A
    once-style mock run has exactly one; with several (a live run), the
    first by file name is used, which is not analysis order: pass a
    directory holding only the scored analysis in that case.

    Args:
        decisions_dir: The run's copied M5 decision artifacts.
        urgent: The member's urgent robot (the registry maximum).

    Returns:
        `route` (`yield` | `priority_override` | None) and `first_passer`.
    """
    for path in sorted(decisions_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        decision = record.get("decision") or {}
        if not decision.get("congestion_detected") or not record.get("grounded_command_present"):
            continue
        strategy = decision.get("strategy")
        involved = decision.get("involved_robots") or []
        if strategy == "yield":
            others = [r for r in involved if r != decision.get("yield_robot")]
            return {"route": "yield", "first_passer": others[0] if others else None,
                    "artifact": path.name}
        if strategy == "priority_override":
            return {"route": "priority_override", "first_passer": urgent, "artifact": path.name}
    return {"route": None, "first_passer": None, "artifact": None}


def score_b2_episode(
    member: str, gt_dir: Path, decisions_dir: Path | None = None
) -> dict[str, Any]:
    """%CP for one B2 episode.

    Args:
        member: `r1` or `r2` (scenario `priority_urgent_<member>`).
        gt_dir: The run's ground-truth directory.
        decisions_dir: Optional decision artifacts for the decision-level route.

    Returns:
        The urgent robot, the GT first passer at x = 0 and at the far mouths,
        `cp` (urgent first; None when neither robot crossed) and the route.
    """
    scenario = load_scenario(f"priority_urgent_{member}")
    urgent = scenario["oracle"]["urgent_robot"]
    series = load_ground_truth(gt_dir)
    passer, times = first_passer(series)
    half_length = scenario["aisle_barrier"]["length_m"] / 2.0
    result: dict[str, Any] = {
        "member": member,
        "urgent_robot": urgent,
        "first_passer": passer,
        "crossing_sec": times,
        "cp": None if passer is None else passer == urgent,
        "far_mouth_first_passer": _far_mouth_first(series, half_length),
    }
    if decisions_dir is not None:
        route = decision_route(decisions_dir, urgent)
        result["decision"] = {**route, "cp": None if route["first_passer"] is None
                              else route["first_passer"] == urgent}
    return result


def score_b2(episodes: list[tuple[str, int, dict[str, Any]]]) -> dict[str, Any]:
    """Aggregate B2 episodes into per-member %CP and the pair-level rate.

    Args:
        episodes: `(member, seed, score_b2_episode result)` per run.

    Returns:
        Per-member `cp_rate` (over episodes with a first passer), and the
        pairs matched by seed with `divergent_and_correct` (urgent first in
        both members) and its rate.
    """
    members: dict[str, dict[str, Any]] = {}
    for member in sorted({m for m, _s, _e in episodes}):
        scored = [e["cp"] for m, _s, e in episodes if m == member and e["cp"] is not None]
        members[member] = {
            "n": sum(1 for m, _s, _e in episodes if m == member),
            "n_scored": len(scored),
            "cp_rate": None if not scored else round(sum(scored) / len(scored), 3),
        }
    by_seed: dict[int, dict[str, dict[str, Any]]] = {}
    for member, seed, episode in episodes:
        by_seed.setdefault(seed, {})[member] = episode
    pairs = []
    for seed, both in sorted(by_seed.items()):
        if {"r1", "r2"} <= set(both):
            cps = (both["r1"]["cp"], both["r2"]["cp"])
            pairs.append({
                "seed": seed,
                "first_passers": {m: both[m]["first_passer"] for m in ("r1", "r2")},
                "divergent_and_correct": None if None in cps else all(cps),
            })
    scored_pairs = [p["divergent_and_correct"] for p in pairs
                    if p["divergent_and_correct"] is not None]
    return {
        "members": members,
        "pairs": pairs,
        "divergent_and_correct_rate": (
            None if not scored_pairs else round(sum(scored_pairs) / len(scored_pairs), 3)
        ),
    }


def slip_onset_sec(
    samples: list[Sample], hold_point: tuple[float, float],
    threshold_m: float = SLIP_DISPLACEMENT_THRESHOLD_M,
    min_sustained_sec: float = SLIP_HOLD_MIN_SEC,
) -> float | None:
    """First sim time a robot's departure from `hold_point` is sustained.

    Mirrors `stop_time_sec`'s spell rule, inverted: a sample "departed" when
    it is more than `threshold_m` from `hold_point`. The first departed spell
    that lasts at least `min_sustained_sec` is the slip; its onset is the
    spell's first sample, so a poke-and-return shorter than the window never
    counts and jitter below `threshold_m` is ignored outright. The criterion
    reads only the robot's own GT track, so a scripted command (e.g. a
    hold-back release) cannot by itself trigger it -- only sustained actual
    motion does.

    Args:
        samples: One robot's GT samples.
        hold_point: The robot's queued/standoff position, normally its GT
            position closest to the conflict onset.
        threshold_m: A sample farther than this from `hold_point` counts as
            departed.
        min_sustained_sec: Shorter departed spells do not count as a slip.

    Returns:
        The slip onset time (sim-s), or None if the robot never sustains a
        departure.
    """
    spell_start: float | None = None
    last_t: float | None = None
    for sample in samples:
        departed = math.dist((sample.x, sample.y), hold_point) > threshold_m
        if departed:
            if spell_start is None:
                spell_start = sample.t
            last_t = sample.t
            continue
        if spell_start is not None and last_t - spell_start >= min_sustained_sec:
            return spell_start
        spell_start = None
    if spell_start is not None and last_t - spell_start >= min_sustained_sec:
        return spell_start
    return None


def first_slipper(
    series: dict[str, list[Sample]], platoon: tuple[str, ...], onset_sec: float,
) -> tuple[str | None, dict[str, float | None]]:
    """Which platoon member is first to sustain departure from its onset position.

    Each member's hold point is its own GT position closest to `onset_sec`
    (the robot_1 lead's standoff pose, the held robot_3/robot_4's spawn), so
    every platoon member is read uniformly regardless of whether it was
    moving or queued at onset. Only samples at or after `onset_sec` are
    scanned for a slip, so a lead robot's own approach to the standoff
    (necessarily far from a not-yet-reached hold point) is never mistaken
    for a slip.

    Args:
        series: Per-robot GT samples; only `platoon` members are read (the
            yielder is excluded by construction).
        platoon: The platoon robot ids (`oracle.platoon`).
        onset_sec: The conflict onset (`score_conflict`'s `onset_sec`).

    Returns:
        `(first slipper or None, slip onset times)`; a tie goes to the lower id.
    """
    hold_points = {
        rid: (p.x, p.y)
        for rid in platoon
        for p in (min(series[rid], key=lambda s: abs(s.t - onset_sec)),)
    }
    # Samples before onset_sec are the approach/queueing phase, not candidates
    # for a slip; a lead robot still closing on the standoff is routinely far
    # from its (not-yet-reached) onset position, which would otherwise read
    # as an immediate false departure at its very first GT sample.
    after_onset = {
        rid: [s for s in series[rid] if s.t >= onset_sec] for rid in platoon
    }
    onsets = {rid: slip_onset_sec(after_onset[rid], hold_points[rid]) for rid in platoon}
    slipped = {r: t for r, t in onsets.items() if t is not None}
    if not slipped:
        return None, onsets
    return min(slipped, key=lambda r: (slipped[r], r)), onsets


def score_b3(gt_dir: Path, scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    """B3 first-to-slip identity and latency, plus the conflict timeline.

    Args:
        gt_dir: The run's ground-truth directory.
        scenario: The scenario dict (default: `convoy_counterflow_slip.yaml`,
            falling back to `convoy_counterflow.yaml`'s geometry since both
            share the same `platoon`/gate; pass explicitly to score a v1
            `convoy_counterflow` run against this question).

    Returns:
        The conflict timeline, the platoon, `first_slipper`, each member's
        slip onset time, and `first_slip_latency_sec` (the first slipper's
        onset minus the conflict onset; None if either is unscored).
    """
    scenario = scenario or load_scenario("convoy_counterflow_slip")
    series = load_ground_truth(gt_dir)
    conflict = score_conflict(scenario, series)
    onset = conflict["onset_sec"]
    platoon = tuple(scenario["oracle"]["platoon"])
    slipper: str | None = None
    onsets: dict[str, float | None] = dict.fromkeys(platoon)
    if onset is not None:
        slipper, onsets = first_slipper(series, platoon, onset)
    latency = None
    if slipper is not None and onset is not None and onsets[slipper] is not None:
        latency = round(onsets[slipper] - onset, 2)
    return {
        "scene": scenario.get("name"),
        "conflict": conflict,
        "platoon": list(platoon),
        "first_slipper": slipper,
        "slip_onset_sec": onsets,
        "first_slip_latency_sec": latency,
    }


def _ib10_series_instants(series: dict[str, list[Sample]]):
    for t, robots in _instants(series):
        ids = sorted(robots)
        yield t, ids, robots


def formed_jam(series: dict[str, list[Sample]], scenario: dict[str, Any]) -> dict[str, Any]:
    """The IB10 formed-jam validity gate.

    `intersection_conflict_active` (>= 3 robots within 1.0 m of the origin,
    mean speed < 0.03 m/s) evaluated at every GT instant, as
    `conflict_timeline` does for the aperture scenes. The gate passes when
    the onset lies inside `expected_conflict.onset_window_sec`, the longest
    active interval lasts at least `min_duration_sec`, and at least
    `oracle.jam_robots_in_radius` robots are inside the radius at onset (the
    jam forms first, with every robot in it). A run that fails the gate is
    invalid, not a failed resolution.

    Args:
        series: Per-robot GT samples.
        scenario: The scenario YAML as a dict (needs `oracle` and
            `expected_conflict`).

    Returns:
        The timeline, `robots_in_radius_at_onset`, the three gate checks and
        `valid`.
    """
    intervals: list[list[float]] = []
    previous_t: float | None = None
    in_radius_at_onset = 0
    for t, ids, robots in _ib10_series_instants(series):
        active = intersection_conflict_active(
            [(robots[r].x, robots[r].y) for r in ids], [robots[r].speed for r in ids]
        )
        if active:
            if not intervals:
                in_radius_at_onset = sum(
                    1 for r in ids if math.hypot(robots[r].x, robots[r].y) < IB10_JAM_RADIUS_M
                )
            if intervals and intervals[-1][1] == previous_t:
                intervals[-1][1] = t
            else:
                intervals.append([t, t])
        previous_t = t
    expected = scenario.get("expected_conflict") or {}
    window = expected.get("onset_window_sec")
    onset = intervals[0][0] if intervals else None
    longest = max((b - a for a, b in intervals), default=0.0)
    onset_in_window = None if window is None or onset is None else window[0] <= onset <= window[1]
    min_duration_met = bool(intervals) and longest >= expected.get("min_duration_sec", 0.0)
    needed = scenario["oracle"]["jam_robots_in_radius"]
    return {
        "onset_sec": onset,
        "onset_window_sec": window,
        "onset_in_window": onset_in_window,
        "longest_interval_sec": round(longest, 2),
        "min_duration_met": min_duration_met,
        "robots_in_radius_at_onset": in_radius_at_onset,
        "robots_in_radius_needed": needed,
        "valid": bool(onset_in_window) and min_duration_met and in_radius_at_onset >= needed,
    }


def _ib10_geometry() -> SceneGeometry:
    spec = SCENES["intersection_bottleneck"]
    return SceneGeometry(
        corridor=spec.corridor,
        arms=spec.scenario_geometry_arms,
        junction_recede_offset_m=spec.junction_recede_offset_m,
    )


def dispatched_junction_decision(decisions_dir: Path) -> dict[str, Any] | None:
    """The run's first dispatched `junction_clear` decision artifact.

    The dispatched decision has a detected congestion, a grounded command and
    the `junction_clear` strategy; with several, the earliest by its scene
    stamp is the trigger the composite ran from.

    Args:
        decisions_dir: The run's copied M5 decision artifacts.

    Returns:
        The artifact, or None when the run dispatched no `junction_clear`.
    """
    found = []
    for path in sorted(decisions_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        decision = record.get("decision") or {}
        if (
            decision.get("congestion_detected")
            and record.get("grounded_command_present")
            and decision.get("strategy") == "junction_clear"
        ):
            found.append(((record.get("scene") or {}).get("stamp", 0.0), path.name, record))
    if not found:
        return None
    _stamp, name, record = min(found, key=lambda item: (item[0], item[1]))
    return {**record, "_artifact": name}


def chi_order(record: dict[str, Any], recede_pair: list[str]) -> list[str]:
    """The chi-ranked recede order at the dispatched decision's own snapshot.

    Recomputed with M3's own `rank_recede_candidates` (chi weights from
    `config/rag.yaml`, geometry from `strategy_regret.SCENES`), never read
    back from the executed plan, so the executed order is scored against an
    independent reference.

    Args:
        record: The dispatched decision artifact (its `scene` snapshot).
        recede_pair: `oracle.recede_pair`.

    Returns:
        `recede_pair` in ascending chi order.
    """
    scene = record["scene"]
    frame = SnapshotFrame(
        stamp=max(0.0, float(scene.get("stamp") or 0.0)),
        robots=[
            RobotStateInput(
                robot_id=robot["robot_id"], x=robot["x"], y=robot["y"],
                theta=robot.get("theta", 0.0), status=robot.get("status"),
            )
            for robot in scene["robots"]
        ],
    )
    params = load_grounding_params(REPO_ROOT / "config" / "rag.yaml")
    return rank_recede_candidates(frame, recede_pair, _ib10_geometry(), params)


def _recede_legs(legs: list[dict[str, Any]] | None) -> list[str] | None:
    if legs is None:
        return None
    return [leg["robot_id"] for leg in legs if leg.get("action") == "reverse"]


def score_chi_pair(record: dict[str, Any], oracle: dict[str, Any]) -> dict[str, Any]:
    """Chi-pair correctness of the proposed (pre-repair) and executed plans.

    A plan's recede set is its `reverse` legs. `*_pair_correct`: that set is
    exactly `oracle.recede_pair`. `*_order_correct`: its order equals
    `chi_order` at the trigger snapshot. The proposed fields are None when
    the decision carried no `proposed_plan` (strategy token only, the
    `m3_default` contract).

    Args:
        record: The dispatched decision artifact.
        oracle: The scenario's `oracle:` block.

    Returns:
        The chi order, both recede lists, the four correctness flags, the
        executed provenance and the grounded yielder.
    """
    pair = list(oracle["recede_pair"])
    reference = chi_order(record, pair)
    proposed = _recede_legs((record.get("decision") or {}).get("proposed_plan"))
    plan = record.get("plan") or {}
    executed = _recede_legs(plan.get("legs"))
    yielder = next(
        (leg["robot_id"] for leg in plan.get("legs") or [] if leg.get("action") == "yield"), None
    )

    def pair_ok(legs: list[str] | None) -> bool | None:
        return None if legs is None else sorted(legs) == sorted(pair)

    def order_ok(legs: list[str] | None) -> bool | None:
        return None if legs is None else legs == reference

    return {
        "artifact": record.get("_artifact"),
        "chi_order": reference,
        "proposed_recede": proposed,
        "proposed_pair_correct": pair_ok(proposed),
        "proposed_order_correct": order_ok(proposed),
        "executed_recede": executed,
        "executed_pair_correct": pair_ok(executed),
        "executed_order_correct": order_ok(executed),
        "provenance": plan.get("provenance"),
        "yielder": yielder,
    }


def junction_crossing(
    samples: list[Sample], axis: str, direction: float
) -> float | None:
    """Time of a robot's final crossing of the junction centre toward its goal.

    `final_crossing` along the robot's own travel axis: the line through the
    centre perpendicular to the axis, crossed in `direction`, counting only
    a crossing after which the robot stays past the line.

    Args:
        samples: One robot's GT samples.
        axis: `x` or `y`, the robot's travel axis.
        direction: +1 or -1, the sign of its goal coordinate minus its spawn.

    Returns:
        Sim time of the final crossing, or None.
    """
    if axis == "x":
        return final_crossing(samples, 0.0, direction)
    swapped = [
        Sample(t=s.t, x=s.y, y=s.x, theta=s.theta, speed=s.speed,
               distance_to_goal=s.distance_to_goal)
        for s in samples
    ]
    return final_crossing(swapped, 0.0, direction)


def score_inside_first(
    series: dict[str, list[Sample]], scenario: dict[str, Any], yielder: str | None
) -> dict[str, Any]:
    """Inside-first order from GT final junction crossings.

    Inside robots are `oracle.inside_pair` minus the grounded yielder; the
    recede robots are `oracle.recede_pair`. `inside_first` is True when
    every inside robot crossed and every recede robot's crossing (if any)
    is later than the last inside crossing, False when a recede robot
    crossed first, None when an inside robot never crossed. `yielder_last`
    (descriptive, not part of the oracle: M4 releases the yielder and the
    second recede robot on the same gate) is True when the yielder crossed
    after every other robot that crossed.

    Args:
        series: Per-robot GT samples.
        scenario: The scenario dict (robots' spawns and goals, the oracle).
        yielder: The executed plan's yielder, or None.

    Returns:
        Per-robot crossing times, the crossing order and both flags.
    """
    oracle = scenario["oracle"]
    times: dict[str, float | None] = {}
    for robot in scenario["robots"]:
        rid = robot["robot_id"]
        dx = robot["goal"]["x"] - robot["spawn"]["x"]
        dy = robot["goal"]["y"] - robot["spawn"]["y"]
        axis = "x" if abs(dx) >= abs(dy) else "y"
        direction = math.copysign(1.0, dx if axis == "x" else dy)
        times[rid] = junction_crossing(series[rid], axis, direction)
    inside = [r for r in oracle["inside_pair"] if r != yielder]
    recede = list(oracle["recede_pair"])
    inside_times = [times[r] for r in inside]
    if any(t is None for t in inside_times):
        inside_first = None
    else:
        last_inside = max(inside_times)
        inside_first = all(times[r] is None or times[r] > last_inside for r in recede)
    yielder_last = None
    if yielder is not None and times.get(yielder) is not None:
        others = [t for r, t in times.items() if r != yielder and t is not None]
        yielder_last = all(times[yielder] > t for t in others)
    crossed = sorted((t, r) for r, t in times.items() if t is not None)
    return {
        "crossing_sec": {r: (None if t is None else round(t, 2)) for r, t in times.items()},
        "crossing_order": [r for _t, r in crossed],
        "inside_robots": inside,
        "inside_first": inside_first,
        "yielder_last": yielder_last,
    }


def phase_reached(m5_log: str) -> dict[str, Any]:
    """The phase-reached ordinal and the fallback flags from M5's log.

    `recede` is reached once any `-junction-recede-` command is dispatched
    (phase 0 has no advance line of its own); every later phase is read off
    `junction_clear phase advance ... phase_reached=<p>` lines. The ordinal
    is the highest of `oracle.phase_ordinal` reached (`none` 0, `recede` 1,
    `cross` 2, `release` 3, `resolved` 4); `fallback` (a phase failed and
    the plain-yield fallback ran) and `fallback_exhausted` (M5's
    `outcome=fallback_exhausted`: that fallback failed too) are flags.

    Args:
        m5_log: The run's M5 (orchestrator) log text.

    Returns:
        `phase_reached`, `phase_ordinal`, `fallback`, `fallback_exhausted`
        and the advance sequence.
    """
    ordinal = ("none", "recede", "cross", "release", "resolved")
    reached = IB10_PHASE_NONE
    if re.search(r"dispatch request=\S+ command=\S+-junction-recede-", m5_log):
        reached = "recede"
    sequence = []
    fallback = False
    for match in _PHASE_ADVANCE_RE.finditer(m5_log):
        phase, done = match.group(1), match.group(2) == "True"
        sequence.append({"phase_reached": phase, "done": done})
        if phase == "fallback":
            fallback = True
        elif phase in ordinal and ordinal.index(phase) > ordinal.index(reached):
            reached = phase
    return {
        "phase_reached": reached,
        "phase_ordinal": ordinal.index(reached),
        "fallback": fallback,
        "fallback_exhausted": "outcome=fallback_exhausted" in m5_log,
        "advances": sequence,
    }


def release_attribution(
    m4_log: str,
    *,
    yielder: str | None = None,
    receders: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """CrossingChain gate events of the `-junction-release` command (step-7b ruling iii).

    `yielder_last` (step-7b ruling vi) reads the same events: a receder's
    release time is its own `gate_release` or, when it is held by a linked
    wait instead, the yielder's `gate_admit` naming it; the yielder is last
    when its own `gate_release` is strictly later than every receder's
    release time.

    Args:
        m4_log: The run's M4 log text.
        yielder: The executed plan's yielder, or None.
        receders: `oracle.recede_pair`.

    Returns:
        The release command's gate events in log order and, per held robot,
        its release `reason` (`clearance` or `hold_timer`). `ordered_release`
        is True when every held robot was released by `clearance`, None when
        no release-command gate event was logged. `yielder_last` is None when
        the yielder's release or every receder's release time is missing.
    """
    events = []
    for match in _GATE_RE.finditer(m4_log):
        kind, command, held, passer, reason, sim_t = match.groups()
        if "-junction-release" not in command:
            continue
        events.append({
            "event": kind, "command": command, "yielder": held, "passer": passer,
            "reason": reason, "sim_t": float(sim_t),
        })
    releases = {e["yielder"]: e for e in events if e["event"] == "gate_release"}
    reasons = {robot: e["reason"] for robot, e in releases.items()}
    yielder_last = None
    if yielder is not None and yielder in releases:
        times = []
        for robot in receders:
            if robot in releases:
                times.append(releases[robot]["sim_t"])
                continue
            admits = [
                e["sim_t"] for e in events
                if e["event"] == "gate_admit" and e["yielder"] == yielder and e["passer"] == robot
            ]
            if admits:
                times.append(admits[0])
        if times:
            yielder_last = all(releases[yielder]["sim_t"] > t for t in times)
    return {
        "events": events,
        "release_reason": reasons,
        "ordered_release": None if not reasons else all(
            r == "clearance" for r in reasons.values()
        ),
        "yielder_last": yielder_last,
    }


def outcome_rank(
    jam_valid: bool, phase_ordinal: int | None, n_arrived: int, all_arrived: bool
) -> tuple[int, int, int] | None:
    """The derived episode ranking (step-7b ruling vii).

    The phase ordinal stays M5's process label; success stays arrivals-based.
    The rank orders episodes lexicographically by (every robot arrived, phase
    ordinal, arrivals), so (ordinal 4, 4/4) always ranks strictly above
    (ordinal 4, partial) and any full success above any partial one.

    Args:
        jam_valid: The formed-jam gate (`formed_jam`'s `valid`).
        phase_ordinal: `phase_reached`'s ordinal, or None without the M5 log.
        n_arrived: Position-verified arrivals.
        all_arrived: Whether every robot arrived.

    Returns:
        The rank tuple; None for an invalid run or an unknown phase.
    """
    if not jam_valid or phase_ordinal is None:
        return None
    return (int(all_arrived), phase_ordinal, n_arrived)


def tracked_band(series: dict[str, list[Sample]], t0: float) -> dict[str, Any]:
    """Each robot's largest |x| and |y| after t0, against M1's tracked band."""
    extent = {
        rid: (
            round(max((abs(s.x) for s in samples if s.t >= t0), default=0.0), 3),
            round(max((abs(s.y) for s in samples if s.t >= t0), default=0.0), 3),
        )
        for rid, samples in sorted(series.items())
    }
    return {
        "max_abs_xy": {rid: list(xy) for rid, xy in extent.items()},
        "band": list(IB10_TRACKED_BAND_M),
        "in_band": all(
            x <= IB10_TRACKED_BAND_M[0] and y <= IB10_TRACKED_BAND_M[1]
            for x, y in extent.values()
        ),
    }


def stale_streaks(scene_log: Path) -> dict[str, dict[str, float]]:
    """Longest STALE streak per robot in M5's scene log (step-6 instrumentation rule).

    Args:
        scene_log: The run's `m5_scene/<session>.jsonl`.

    Returns:
        Per robot: `rows`, `stale_rows`, `longest_streak_rows` and
        `longest_streak_sec` (stamp span of that streak).
    """
    out: dict[str, dict[str, Any]] = {}
    for line in scene_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        # A STALE robot's own stamp freezes at its last fresh detection, so
        # the streak span is read off the scene's stamp instead.
        stamp = record["scene"]["stamp"]
        for robot in record["scene"]["robots"]:
            state = out.setdefault(robot["robot_id"], {
                "rows": 0, "stale_rows": 0, "longest_streak_rows": 0,
                "longest_streak_sec": 0.0, "_run": 0, "_start": None,
            })
            state["rows"] += 1
            if robot["status"] == "STALE":
                state["stale_rows"] += 1
                state["_run"] += 1
                if state["_start"] is None:
                    state["_start"] = stamp
                if state["_run"] > state["longest_streak_rows"]:
                    state["longest_streak_rows"] = state["_run"]
                    state["longest_streak_sec"] = round(stamp - state["_start"], 2)
            else:
                state["_run"], state["_start"] = 0, None
    return {
        rid: {k: v for k, v in state.items() if not k.startswith("_")}
        for rid, state in sorted(out.items())
    }


def score_ib10(
    gt_dir: Path,
    *,
    decisions_dir: Path | None = None,
    m5_log: str | None = None,
    m4_log: str | None = None,
    scene_log: Path | None = None,
    scenario: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Every IB10 `junction_clear` resolution criterion for one run.

    `resolved` (episode success) is the formed-jam gate passing and all
    robots position-verified at their goals (`score_ground_truth`'s arrival
    rule); None when the gate fails (the run is invalid, not scored).

    Args:
        gt_dir: The run's ground-truth directory.
        decisions_dir: The run's M5 decision artifacts (chi-pair).
        m5_log: The run's M5 log text (phase reached, fallback flags).
        m4_log: The run's M4 log text (release attribution).
        scene_log: The run's M5 scene log (STALE streaks).
        scenario: The scenario dict (default: `intersection_bottleneck.yaml`).

    Returns:
        The scored record; a section is None when its input was not given.
    """
    scenario = scenario or load_scenario("intersection_bottleneck")
    series = load_ground_truth(gt_dir)
    run = score_ground_truth("ib10", gt_dir)
    jam = formed_jam(series, scenario)
    record = (
        None if decisions_dir is None else dispatched_junction_decision(decisions_dir)
    )
    chi = None if record is None else score_chi_pair(record, scenario["oracle"])
    yielder = None if chi is None else chi["yielder"]
    arrivals = {rid: (None if at is None else round(at - run.t0_sec, 2))
                for rid, at in run.arrivals_sec.items()}
    n_arrived = sum(v is not None for v in arrivals.values())
    all_arrived = n_arrived == len(arrivals)
    phase = None if m5_log is None else phase_reached(m5_log)
    return {
        "scene": scenario.get("name"),
        "t0_sec": run.t0_sec,
        "end_sec": run.end_sec,
        "formed_jam": jam,
        "chi_pair": chi,
        "order": score_inside_first(series, scenario, yielder),
        "phase": phase,
        "release": None if m4_log is None else release_attribution(
            m4_log, yielder=yielder, receders=scenario["oracle"]["recede_pair"]
        ),
        "arrivals_after_t0_sec": arrivals,
        "n_arrived": n_arrived,
        "all_arrived": all_arrived,
        "tracked_band": tracked_band(series, run.t0_sec),
        "stale_streaks": None if scene_log is None else stale_streaks(scene_log),
        "resolved": all_arrived if jam["valid"] else None,
        "outcome_rank": None if phase is None else outcome_rank(
            jam["valid"], phase["phase_ordinal"], n_arrived, all_arrived
        ),
    }


def first_dispatch(decisions_dir: Path) -> dict[str, Any] | None:
    """The run's first dispatched decision (any strategy), by scene stamp.

    Args:
        decisions_dir: The run's copied M5 decision artifacts.

    Returns:
        `{"stamp", "strategy", "artifact"}`, or None when nothing was
        dispatched (no artifact with a detected congestion and a grounded
        command).
    """
    found = []
    for path in sorted(decisions_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        decision = record.get("decision") or {}
        if decision.get("congestion_detected") and record.get("grounded_command_present"):
            stamp = (record.get("scene") or {}).get("stamp", 0.0)
            found.append((stamp, path.name, decision.get("strategy")))
    if not found:
        return None
    stamp, name, strategy = min(found)
    return {"stamp": stamp, "strategy": strategy, "artifact": name}


def stall_onset(
    samples: list[Sample], start: float, end: float,
    speed_mps: float = STOP_SPEED_MPS, min_spell_sec: float = STOP_MIN_SPELL_SEC,
) -> Sample | None:
    """The first sample of the first stopped spell of at least `min_spell_sec`.

    Same spell rule as `stop_time_sec` (speed < 0.02 m/s for >= 1 s).

    Args:
        samples: One robot's GT samples.
        start: Window start (sim-s), normally t0.
        end: Window end (sim-s).
        speed_mps: A sample slower than this is stopped.
        min_spell_sec: Shorter spells do not count.

    Returns:
        The spell's first sample, or None when the robot never stalls.
    """
    spell: Sample | None = None
    for sample in samples:
        if not start <= sample.t <= end:
            continue
        if sample.speed < speed_mps:
            if spell is None:
                spell = sample
            elif sample.t - spell.t >= min_spell_sec:
                return spell
        else:
            spell = None
    return None


def score_loop(
    gt_dir: Path,
    scenario: dict[str, Any],
    *,
    decisions_dir: Path | None = None,
    scene_log: Path | None = None,
    sampler_log: Path | None = None,
    robot_id: str = "robot_1",
) -> dict[str, Any]:
    """One loop-detour run (prereg-v2 (b), build-order step 8 phase 2).

    Time-to-goal follows the T2b arrival rule (`score_ground_truth`); a run
    that never arrives is censored (time to the episode end, a lower
    bound). `self_detour` is the pre-emption failure the family's design
    control exists to prevent: robot_1 on the loop with no `reroute`
    dispatched before it got there. `outcome_rank` orders episodes
    (arrived first, then faster), mirroring IB10's derived rank.

    Args:
        gt_dir: The run's ground-truth directory.
        scenario: The scenario dict (its `oracle` scores the decision).
        decisions_dir: The run's M5 decision artifacts.
        scene_log: The run's M5 scene log (STALE streaks).
        sampler_log: The run's `loop_family_sampler.py` JSONL.
        robot_id: The decision robot.

    Returns:
        The scored record; a section is None when its input was not given.
    """
    series = load_ground_truth(gt_dir)
    run = score_ground_truth("loop", gt_dir)
    samples = series[robot_id]
    arrival = run.arrivals_sec.get(robot_id)
    censored = arrival is None
    time_to_goal = round((run.end_sec if censored else arrival) - run.t0_sec, 2)
    stall = stall_onset(samples, run.t0_sec, run.end_sec if censored else arrival)
    on_loop = next((s for s in samples if s.y > LOOP_ENTRY_Y_M), None)
    dispatch = None if decisions_dir is None else first_dispatch(decisions_dir)
    reroute_at = (
        dispatch["stamp"] if dispatch is not None and dispatch["strategy"] == "reroute" else None
    )
    self_detour = None
    if on_loop is not None and decisions_dir is not None:
        self_detour = reroute_at is None or on_loop.t < reroute_at
    elif on_loop is None:
        self_detour = False
    oracle = scenario.get("oracle") or {}
    accepted = oracle.get("accepted_strategies")
    label = None if dispatch is None else dispatch["strategy"]
    plans = None
    if sampler_log is not None and sampler_log.is_file():
        rows = [json.loads(line) for line in sampler_log.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        before = [r for r in rows if reroute_at is None or (r.get("sim") or 0.0) < reroute_at]
        bottlenecks = [r["global_gap_bottleneck"] for r in rows
                       if r.get("global_gap_bottleneck") is not None]
        plans = {
            "rows": len(rows),
            "plan_rows": sum(1 for r in rows if r.get("plan")),
            "plan_on_loop_before_reroute": sum(
                1 for r in before if (r.get("plan") or {}).get("entered_second_aisle")
            ),
            "max_global_gap_bottleneck": max(bottlenecks) if bottlenecks else None,
            "min_global_gap_bottleneck": min(bottlenecks) if bottlenecks else None,
        }
    return {
        "scene": scenario.get("name"),
        "t0_sec": run.t0_sec,
        "end_sec": run.end_sec,
        "arrived": not censored,
        "time_to_goal_sec": time_to_goal,
        "censored": censored,
        "stall": None if stall is None else {
            "onset_sec": round(stall.t, 2), "x": round(stall.x, 3), "y": round(stall.y, 3),
        },
        "entered_loop_sec": None if on_loop is None else round(on_loop.t, 2),
        "max_y": round(max(s.y for s in samples), 3),
        "dispatch": dispatch,
        "self_detour": self_detour,
        "plans": plans,
        "decision_correct": (
            None if accepted is None or label is None else label in accepted
        ),
        "outcome_rank": (int(not censored), -time_to_goal),
        "tracked_band": {
            "max_abs_x": round(max(abs(s.x) for s in samples), 3),
            "max_abs_y": round(max(abs(s.y) for s in samples), 3),
            "in_band": all(
                abs(s.x) <= LOOP_TRACKED_BAND_M[0] and abs(s.y) <= LOOP_TRACKED_BAND_M[1]
                for s in samples
            ),
        },
        "stale_streaks": None if scene_log is None else stale_streaks(scene_log),
    }


def loop_cost_record(table: dict[str, Any]) -> dict[str, Any]:
    """A loop-detour cell's `oracle.cost` record from its strategy cost table.

    Args:
        table: `scripts/strategy_regret.py score` output for a
            `loop_detour_*` scene (arms `wait` and `reroute`).

    Returns:
        The record as validated `LoopDetourCostRecord` fields.

    Raises:
        ValueError: If an arm is missing, the faster arm is censored, or the
            record fails validation.
    """
    from isaac.vgu_sim.config import LoopDetourCostRecord

    arms = table["arms"]
    missing = {"wait", "reroute"} - set(arms)
    if missing:
        raise ValueError(f"cost table lacks arms {sorted(missing)}")
    wait, reroute = arms["wait"], arms["reroute"]
    winner_arm = "wait" if wait["mean_total_sec"] <= reroute["mean_total_sec"] else "reroute"
    loser_arm = "reroute" if winner_arm == "wait" else "wait"
    win, lose = arms[winner_arm], arms[loser_arm]
    record = {
        "metric": "time_to_goal_sec",
        "wait_time_to_goal_sec": wait["mean_total_sec"],
        "wait_censored": bool(wait["censored"]),
        "reroute_time_to_goal_sec": reroute["mean_total_sec"],
        "reroute_censored": bool(reroute["censored"]),
        "winner": "temporary_wait" if winner_arm == "wait" else "reroute",
        "margin": round(lose["mean_total_sec"] / win["mean_total_sec"] - 1.0, 4),
        "threshold": 0.20,
        "n_per_arm": min(wait["n"], reroute["n"]),
        "run_ids": [*wait["run_ids"], *reroute["run_ids"]],
    }
    return LoopDetourCostRecord(**record).model_dump(mode="json")


def _dump(result: Any, out: str | None) -> None:
    text = json.dumps(result, indent=2)
    print(text)
    if out:
        Path(out).write_text(text + "\n", encoding="utf-8")


def _cmd_conflict(args: argparse.Namespace) -> int:
    scenario = load_scenario(args.scenario)
    _dump(score_conflict(scenario, load_ground_truth(Path(args.gt))), args.out)
    return 0


def _cmd_b1(args: argparse.Namespace) -> int:
    _dump(score_b1(Path(args.gt)), args.out)
    return 0


def _cmd_b2(args: argparse.Namespace) -> int:
    episodes = []
    for item in args.run:
        parts = item.split(":")
        if len(parts) not in (3, 4) or parts[0] not in ("r1", "r2"):
            raise SystemExit(f"--run must be r1|r2:<seed>:<gt dir>[:<decisions dir>]; got {item!r}")
        decisions = Path(parts[3]) if len(parts) == 4 else None
        episode = score_b2_episode(parts[0], Path(parts[2]), decisions)
        episode["seed"] = int(parts[1])
        episodes.append((parts[0], int(parts[1]), episode))
    _dump({"episodes": [e for _m, _s, e in episodes], **score_b2(episodes)}, args.out)
    return 0


def _cmd_b3(args: argparse.Namespace) -> int:
    _dump(score_b3(Path(args.gt)), args.out)
    return 0


def _cmd_ib10(args: argparse.Namespace) -> int:
    def text(path: str | None) -> str | None:
        return None if path is None else Path(path).read_text(encoding="utf-8", errors="replace")

    _dump(
        score_ib10(
            Path(args.gt),
            decisions_dir=None if args.decisions is None else Path(args.decisions),
            m5_log=text(args.m5_log),
            m4_log=text(args.m4_log),
            scene_log=None if args.scene is None else Path(args.scene),
        ),
        args.out,
    )
    return 0


def _cmd_loop(args: argparse.Namespace) -> int:
    def path(value: str | None) -> Path | None:
        return None if value is None else Path(value)

    _dump(
        score_loop(
            Path(args.gt),
            load_scenario(args.scenario),
            decisions_dir=path(args.decisions),
            scene_log=path(args.scene),
            sampler_log=path(args.sampler),
        ),
        args.out,
    )
    return 0


def _cmd_loop_cost(args: argparse.Namespace) -> int:
    table = json.loads(Path(args.table).read_text(encoding="utf-8"))
    _dump(loop_cost_record(table), args.out)
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    conflict = sub.add_parser("conflict", help="GT bottleneck-conflict timeline (B1, B3)")
    conflict.add_argument("--scenario", required=True)
    conflict.add_argument("--gt", required=True)
    conflict.add_argument("--out")
    conflict.set_defaults(func=_cmd_conflict)
    b1 = sub.add_parser("b1", help="B1 gate flow, stop time, makespan, merge")
    b1.add_argument("--gt", required=True)
    b1.add_argument("--out")
    b1.set_defaults(func=_cmd_b1)
    b2 = sub.add_parser("b2", help="B2 %%CP per episode and per seed-matched pair")
    b2.add_argument("--run", action="append", required=True)
    b2.add_argument("--out")
    b2.set_defaults(func=_cmd_b2)
    b3 = sub.add_parser("b3", help="B3 first-to-slip identity and latency")
    b3.add_argument("--gt", required=True)
    b3.add_argument("--out")
    b3.set_defaults(func=_cmd_b3)
    ib10 = sub.add_parser("ib10", help="IB10 junction_clear resolution oracle")
    ib10.add_argument("--gt", required=True)
    ib10.add_argument("--decisions")
    ib10.add_argument("--m5-log")
    ib10.add_argument("--m4-log")
    ib10.add_argument("--scene")
    ib10.add_argument("--out")
    ib10.set_defaults(func=_cmd_ib10)
    loop = sub.add_parser("loop", help="one loop-detour run (prereg-v2 (b))")
    loop.add_argument("--scenario", required=True)
    loop.add_argument("--gt", required=True)
    loop.add_argument("--decisions")
    loop.add_argument("--scene")
    loop.add_argument("--sampler")
    loop.add_argument("--out")
    loop.set_defaults(func=_cmd_loop)
    loop_cost = sub.add_parser("loop-cost", help="a loop-detour cell's oracle.cost record")
    loop_cost.add_argument("--table", required=True)
    loop_cost.add_argument("--out")
    loop_cost.set_defaults(func=_cmd_loop_cost)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

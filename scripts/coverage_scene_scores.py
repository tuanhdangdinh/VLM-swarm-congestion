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

Definitions fixed before any smoke run (2026-09-29); see each function.

Usage:
    python3 scripts/coverage_scene_scores.py conflict --scenario convoy_counterflow --gt runs/x/gt
    python3 scripts/coverage_scene_scores.py b1 --gt runs/b1_smoke/gt --out b1.json
    python3 scripts/coverage_scene_scores.py b2 --run r1:42:runs/r1/gt --run r2:42:runs/r2/gt
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from isaac.vgu_sim.oracle import bottleneck_conflict_active  # noqa: E402
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
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

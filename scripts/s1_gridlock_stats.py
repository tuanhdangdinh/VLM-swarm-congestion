"""Measure S1 clogged-regime episode outcomes (time-to-gridlock and friends).

Implements the S1a mini-program measures pre-registered in the S1b first-light
VM NOTES (rule 5, 2026-10-09): time-to-gridlock is the first sim-s, relative
to robot_1's release, after which every unfinished robot is static (GT 20 s
position range < 3 cm) or latch-held (GT centre gap < 0.45 m) to the end.
Also reports the latch-pair formation sequence, the final cluster composition
(connected components of to-end latch pairs), task counts, self-free events
(transient latch intervals and ended static runs), and the outcome class
{complete, partial, gridlock, censored}. Robots that finish their queue
(``robot_done``) are excluded from the gridlock condition.

The encounter definition, GT/M1 clock mapping and interval machinery are
``scripts/s1_live_conflict_stats.py``'s, imported directly so the two reports
stay comparable.

Usage:
    python scripts/s1_gridlock_stats.py <bundle_dir> [<bundle_dir> ...]

Prints one JSON object per bundle.
"""

from __future__ import annotations

import glob
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s1_live_conflict_stats as slcs

STATIC_WINDOW_S = 20.0
STATIC_RANGE_M = 0.03


def _static_flags(times: list[float], xs: list[float], ys: list[float]) -> list[bool]:
    """Per sample: is the position range within the next 20 s below 3 cm."""
    n = len(times)
    flags = [False] * n
    j_hi = 0
    for i in range(n):
        while j_hi < n and times[j_hi] <= times[i] + STATIC_WINDOW_S:
            j_hi += 1
        wx = xs[i:j_hi]
        wy = ys[i:j_hi]
        flags[i] = (max(wx) - min(wx)) < STATIC_RANGE_M and (max(wy) - min(wy)) < STATIC_RANGE_M
    return flags


def _static_runs(times: list[float], flags: list[bool]) -> list[tuple[float, float]]:
    """Maximal runs of static samples, as (start, end-of-window) times."""
    runs: list[tuple[float, float]] = []
    start: float | None = None
    for t, f in zip(times, flags, strict=True):
        if f and start is None:
            start = t
        elif not f and start is not None:
            runs.append((start, t))
            start = None
    if start is not None:
        runs.append((start, times[-1]))
    return runs


def _components(pairs: list[tuple[str, str]]) -> list[list[str]]:
    parent: dict[str, str] = {}

    def find(r: str) -> str:
        parent.setdefault(r, r)
        while parent[r] != r:
            parent[r] = parent[parent[r]]
            r = parent[r]
        return r

    for a, b in pairs:
        parent[find(a)] = find(b)
    comps: dict[str, list[str]] = {}
    for r in parent:
        comps.setdefault(find(r), []).append(r)
    return sorted((sorted(m) for m in comps.values()), key=lambda m: (-len(m), m))


def analyse_gridlock(bundle: Path) -> dict:
    """Return the clogged-regime outcome statistics of one S1 bundle."""
    base = slcs.analyse(bundle)
    gt = slcs._jl(bundle / "gt" / "ground_truth.jsonl")
    tasks = slcs._jl(Path(sorted(glob.glob(str(bundle / "decisions" / "tasks_*.jsonl")))[0]))
    t0_gt = base["t0_m1_sim"] - base["gt_offset_s"]
    end_gt = gt[-1]["sim_time_sec"]

    tasks_total = next(
        (r["tasks_total"] for r in tasks if r.get("tasks_total") is not None), None
    )
    tasks_completed = sum(1 for r in tasks if r.get("event") == "dwell_complete")
    finishers = sorted({r["robot_id"] for r in tasks if r.get("event") == "robot_done"})

    robots = sorted(gt[0]["robots"], key=lambda r: int(r.split("_")[1]))
    unfinished = [r for r in robots if r not in finishers]

    # Per-robot earliest to-end latch onset (GT encounter intervals).
    latch_to_end_onset: dict[str, float] = {}
    for row in base["gt_encounters"]:
        if row["to_episode_end"]:
            for r in row["pair"].split("+"):
                onset = row["onset_rel_s"]
                latch_to_end_onset[r] = min(latch_to_end_onset.get(r, math.inf), onset)

    per_robot: dict[str, dict] = {}
    self_free_static: list[dict] = []
    for r in robots:
        times = [s["sim_time_sec"] for s in gt]
        xs = [s["robots"][r]["x"] for s in gt]
        ys = [s["robots"][r]["y"] for s in gt]
        flags = _static_flags(times, xs, ys)
        runs = _static_runs(times, flags)
        # Static-to-end onset: the last run, if it reaches the final sample.
        static_onset = None
        if runs and flags[-1] and runs[-1][1] >= times[-1]:
            static_onset = runs[-1][0] - t0_gt
        for start, stop in runs:
            if stop < times[-1] and stop - start >= STATIC_WINDOW_S:
                self_free_static.append(
                    {
                        "robot": r,
                        "static_from_rel_s": round(start - t0_gt, 1),
                        "moved_again_rel_s": round(stop - t0_gt, 1),
                    }
                )
        latch_onset = latch_to_end_onset.get(r)
        held_candidates = [v for v in (static_onset, latch_onset) if v is not None]
        static_rounded = round(static_onset, 1) if static_onset is not None else None
        per_robot[r] = {
            "static_to_end_onset_rel_s": static_rounded,
            "latch_to_end_onset_rel_s": round(latch_onset, 1) if latch_onset is not None else None,
            "held_from_rel_s": round(min(held_candidates), 1) if held_candidates else None,
        }

    held = [per_robot[r]["held_from_rel_s"] for r in unfinished]
    censored = any(v is None for v in held) or not unfinished
    gridlock_rel = None if censored else max(held)

    if tasks_total is not None and tasks_completed == tasks_total:
        outcome = "complete"
    elif censored:
        outcome = "censored"
    elif tasks_completed > 0:
        outcome = "partial"
    else:
        outcome = "gridlock"

    m1_perm_pairs = [
        tuple(row["pair"].split("+"))
        for row in base["m1_latch_encounters"]
        if row["to_episode_end"]
    ]
    gt_perm_pairs = [
        tuple(row["pair"].split("+")) for row in base["gt_encounters"] if row["to_episode_end"]
    ]
    transient = [row for row in base["gt_encounters"] if not row["to_episode_end"]]

    return {
        "bundle": str(bundle),
        "gt_end_rel_s": round(end_gt - t0_gt, 1),
        "tasks_completed": tasks_completed,
        "tasks_total": tasks_total,
        "finishers": finishers,
        "first_latch_m1_rel_s": base["m1_first_latch_rel_s"],
        "first_encounter_gt_rel_s": base["gt_first_encounter_rel_s"],
        "latch_formation_sequence_m1": base["m1_latch_encounters"],
        "gt_encounters": base["gt_encounters"],
        "per_robot": per_robot,
        "gridlock_rel_s": gridlock_rel,
        "censored": censored,
        "outcome_class": outcome,
        "final_clusters_m1": _components(m1_perm_pairs),
        "final_clusters_gt": _components(gt_perm_pairs),
        "self_free_latch_intervals": transient,
        "self_free_static_runs": self_free_static,
        "gt_cluster_first_k_rel_s": base["gt_cluster_first_k_rel_s"],
    }


def main() -> None:
    """Entry point."""
    for arg in sys.argv[1:]:
        print(json.dumps(analyse_gridlock(Path(arg))))


if __name__ == "__main__":
    main()

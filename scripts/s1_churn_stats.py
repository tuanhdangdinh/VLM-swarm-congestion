"""Classify S1 episodes by coordination churn (prereg-v3 A21(a): measure first).

A21 classified S1b pilot 2's E3 as a coordination-level LIVELOCK: the
coordinator kept breaking latches inside one cluster without any task
progress. This scorer measures that, with ZERO behaviour change (it only
reads bundles), on the same definitions M5's default-off bound uses
(`swarm_orchestrator.churn`: dispatch identity, latch cluster, alternation).

Definitions (all times on the M1 scene clock, the clock M4/M5 log `sim_t` on;
GT encounter intervals map onto it through the bundle's fitted GT offset, as
in `s1_live_conflict_stats.py`):

* CLEARING DISPATCH: a dispatched command with a non-wait action
  (`churn.dispatch_identity` is not None). All-wait fan-outs are excluded.
* ACTIVE WINDOW of a clearing dispatch: from its `dispatch request` line to
  the last terminal M4 status (COMPLETED/FAILED/CANCELLED) of its clearing
  robots, else to the next clearing dispatch or `expected_resolution_time_sec`.
* LATCH BREAK: the end of a transient GT encounter interval (centre gap
  < 0.45 m, the S1 MC definition) before the episode end. It is
  DISPATCH-ATTRIBUTED when it ends inside a clearing dispatch's active window
  (+ `ATTRIBUTION_GRACE_S`) and the pair intersects that dispatch's latch
  cluster (`churn.latch_cluster` on the dispatch's own scene).
* RESOLUTION EVENT: a clearing dispatch with >= 1 attributed latch break. It
  is PRODUCTIVE when a robot of its cluster makes task progress (a tasks-JSONL
  `arrived` or `dwell_complete`) after its first attributed break, before the
  cluster's next clearing dispatch and within `PRODUCTIVE_WINDOW_S`.

The mechanical predicate (derived from E3 vs A1; A1 resolved then progressed,
E3 resolved without progress):

* `intermittent`: >= 2 UNPRODUCTIVE resolution events (repeated resolution
  without progress: the coordination livelock);
* `resolved`: >= 1 productive resolution event and fewer than 2 unproductive;
* `clogged`: no productive resolution event and at most one unproductive one
  (nothing the coordinator did produced flow, and it did not keep churning);
* None when the evidence is missing (no GT, no tasks JSONL): never guessed.

This `churn_class` is a separate axis from `s1_gridlock_stats.outcome_class`
(complete/partial/gridlock/censored) and from the v2 flow scorer's
`OutcomeClass` (whose `intermittent` requires every robot to arrive).

Churn metrics: clearing dispatches, latch breaks (all / attributed),
dispatches per attributed latch break, alternation count (A-B-A completions
over the clearing-dispatch identity sequence), identity repeats at lookback 1
(the pre-A21 identical-run check) and 2, the longest identical run, and the
resolution-time share (union of active windows / episode span from robot_1's
release to the GT end). The pre-registered gate events (rule 4: gate_admit ->
gate_release) are reported beside it as a cross-check.

Usage:
    PYTHONPATH=.:ros2_ws/src/swarm_orchestrator \\
        python scripts/s1_churn_stats.py <bundle_dir> [<bundle_dir> ...]

Prints one JSON object per bundle.
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ros2_ws/src/swarm_orchestrator"))

import s1_live_conflict_stats as slcs  # noqa: E402
import s1b_episode_stats as eps  # noqa: E402
from swarm_orchestrator.churn import (  # noqa: E402
    alternation_count,
    dispatch_identity,
    identity_repeats,
    identity_robots,
    latch_cluster,
    longest_identical_run,
)

# A latch can read as broken a few GT samples after the command's terminal
# status (GT clock offset residue, 10 Hz sampling).
ATTRIBUTION_GRACE_S = 2.0
# S1-1's tail-gridlock window (`s1b_episode_stats._TAIL_S`): progress later
# than this after a break is not credited to it.
PRODUCTIVE_WINDOW_S = 120.0
_TERMINAL = ("COMPLETED", "FAILED", "CANCELLED")


def _artifacts_by_prefix(bundle: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in glob.glob(str(bundle / "decisions" / "*.json")):
        data = json.loads(Path(path).read_text())
        rid = data.get("request_id") or data.get("diagnostics", {}).get("request_id")
        rid = rid or Path(path).stem
        out[rid[:8]] = data
    return out


def _terminal_times(m4: list[str], pts: list[tuple[float, float]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for line in m4:
        m = re.search(r"status published command=(\S+) robot=(\S+) status=(\S+)", line)
        if not m or m.group(3) not in _TERMINAL:
            continue
        wall = eps._wall(line)
        sim = None if wall is None else eps._sim_at(pts, wall)
        if sim is not None:
            out.setdefault(m.group(1), {})[m.group(2)] = sim
    return out


def _union_length(intervals: list[tuple[float, float]]) -> float:
    total = 0.0
    current: tuple[float, float] | None = None
    for start, end in sorted(intervals):
        if current is None or start > current[1]:
            if current is not None:
                total += current[1] - current[0]
            current = (start, end)
        else:
            current = (current[0], max(current[1], end))
    if current is not None:
        total += current[1] - current[0]
    return total


def classify_churn(productive: int, unproductive: int) -> str:
    """The A21 churn class from counts of productive/unproductive resolution events."""
    if unproductive >= 2:
        return "intermittent"
    if productive >= 1:
        return "resolved"
    return "clogged"


def analyse_churn(bundle: Path) -> dict[str, Any]:
    """Return the churn classification and metrics of one S1 bundle."""
    out: dict[str, Any] = {"bundle": bundle.name}
    if not (bundle / "gt" / "ground_truth.jsonl").exists() or not glob.glob(
        str(bundle / "decisions" / "tasks_*.jsonl")
    ):
        out["churn_class"] = None
        out["missing"] = "gt or tasks jsonl"
        return out
    base = slcs.analyse(bundle)
    episode = eps.analyse(bundle)
    t0 = base["t0_m1_sim"]
    end_sim = base["gt_end_rel_s"] + t0
    m4 = (bundle / "m4.log").read_text(errors="replace").splitlines()
    m5 = (bundle / "m5.log").read_text(errors="replace").splitlines()
    pts = eps._wall_to_sim(m4 + m5)
    terminal = _terminal_times(m4, pts)
    arts = _artifacts_by_prefix(bundle)

    clearing: list[dict[str, Any]] = []
    for d in episode["dispatches"]:
        art = arts.get(d["request"], {})
        command = art.get("dispatched_command")
        identity = dispatch_identity(command)
        if identity is None or d["sim_t"] is None:
            continue
        positions = {
            r["robot_id"]: (r["x"], r["y"]) for r in (art.get("scene") or {}).get("robots", [])
        }
        cluster = latch_cluster(identity, positions)
        clearing.append(
            {
                "request": d["request"],
                "sim_t": d["sim_t"],
                "identity": identity,
                "cluster": cluster,
                "command_id": (command or {}).get("command_id"),
                "expected_s": (command or {}).get("expected_resolution_time_sec") or 150.0,
            }
        )
    for i, c in enumerate(clearing):
        times = terminal.get(c["command_id"], {})
        ends = [t for rid, t in times.items() if rid in identity_robots(c["identity"])]
        nxt = clearing[i + 1]["sim_t"] if i + 1 < len(clearing) else end_sim
        c["active_end"] = max(ends) if ends else min(nxt, c["sim_t"] + c["expected_s"])

    breaks = []
    for row in base["gt_encounters"]:
        if row["to_episode_end"]:
            continue
        t_break = row["onset_rel_s"] + row["duration_s"] + t0
        pair = frozenset(row["pair"].split("+"))
        owner = next(
            (
                c for c in clearing
                if c["sim_t"] <= t_break <= c["active_end"] + ATTRIBUTION_GRACE_S
                and pair & c["cluster"]
            ),
            None,
        )
        breaks.append(
            {"pair": row["pair"], "break_sim_t": round(t_break, 1),
             "dispatch": None if owner is None else owner["request"]}
        )

    tasks = []
    for path in glob.glob(str(bundle / "decisions" / "tasks_*.jsonl")):
        tasks += [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    progress = sorted(
        (e["sim_t"], e["robot_id"]) for e in tasks
        if e.get("event") in ("arrived", "dwell_complete") and e.get("sim_t") is not None
    )

    events = []
    for i, c in enumerate(clearing):
        mine = [b for b in breaks if b["dispatch"] == c["request"]]
        if not mine:
            continue
        first = min(b["break_sim_t"] for b in mine)
        nxt = next(
            (n["sim_t"] for n in clearing[i + 1 :] if n["cluster"] & c["cluster"]), end_sim
        )
        horizon = min(nxt, first + PRODUCTIVE_WINDOW_S)
        credited = [
            (t, rid) for t, rid in progress if first <= t <= horizon and rid in c["cluster"]
        ]
        events.append(
            {
                "request": c["request"],
                "identity": "/".join(c["identity"]),
                "cluster": sorted(c["cluster"]),
                "breaks": len(mine),
                "first_break_sim_t": first,
                "productive": bool(credited),
                "progress": [f"{rid}@{t:.1f}" for t, rid in credited],
            }
        )
    productive = sum(e["productive"] for e in events)
    unproductive = len(events) - productive
    identities = [c["identity"] for c in clearing]
    attributed = sum(1 for b in breaks if b["dispatch"] is not None)
    active = [(c["sim_t"], min(c["active_end"], end_sim)) for c in clearing]
    span = end_sim - t0
    gate = episode["resolution_events"]
    out.update(
        {
            "churn_class": classify_churn(productive, unproductive),
            "resolution_events": len(events),
            "productive_resolution_events": productive,
            "unproductive_resolution_events": unproductive,
            "clearing_dispatches": len(clearing),
            "dispatches_total": episode["dispatched"],
            "latch_breaks": len(breaks),
            "latch_breaks_attributed": attributed,
            "dispatches_per_latch_break": (
                round(len(clearing) / attributed, 2) if attributed else None
            ),
            "alternation_count": alternation_count(identities),
            "identity_repeats_lookback1": identity_repeats(identities, 1),
            "identity_repeats_lookback2": identity_repeats(identities, 2),
            "longest_identical_run": longest_identical_run(identities),
            "resolution_time_share": round(_union_length(active) / span, 3) if span > 0 else None,
            "tasks_completed": episode["tasks_completed"],
            "gate_events": len(gate),
            "gate_events_with_arrival_after_admit": sum(
                1 for g in gate if g["arrivals_after_admit"] > 0
            ),
            "identity_sequence": [
                f"{c['sim_t']:.0f}:{'/'.join(c['identity'])}" for c in clearing
            ],
            "events": events,
        }
    )
    return out


def main() -> None:
    """Entry point."""
    for arg in sys.argv[1:]:
        print(json.dumps(analyse_churn(Path(arg)), default=str))


if __name__ == "__main__":
    main()

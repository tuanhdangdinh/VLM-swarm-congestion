"""Score an S1 echo episode's Layer-2 activity (S1b pilot wave, rules 4, 6, 7).

Pre-registered in the VM NOTES (rules 4 and 6-7, 2026-10-10). Reads one bundle
(``ep_run.sh`` layout: m4.log, m5.log, decisions/, gt/, m5_scene.jsonl) and
reports:

* analyses (``starting analysis``), withheld (``refusal withheld`` and
  ``empty reroute withheld``), dispatched (``dispatch request``), suppressed
  reanalyses and suppression arms by outcome;
* every dispatched command: per-robot actions, empty-waypoint reroute
  fallbacks (rule 6a), the longest run of consecutive near-identical
  dispatches (same per-robot actions; rule 6b) and their sim spacing;
* RESOLUTION EVENTS: executed yields, i.e. a ``crossing_chain gate_admit``
  followed by ``gate_release`` (rule 4), with yielder, passer, reason and the
  tasks completed after the admit;
* prereg-v3 A19 waiver activity (``latch waiver armed/released``, rule 7),
  joined to the yielder's GT motion and the GT min centre distance to each
  waived partner while the command was ACTIVE;
* task-stream outcome: arrivals, robot_done finishers, tasks completed.

Usage:
    python scripts/s1b_episode_stats.py <bundle_dir> [...]

Prints one JSON object per bundle.
"""

from __future__ import annotations

import bisect
import glob
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import s1_live_conflict_stats as slcs  # noqa: E402

_SIM_T = re.compile(r"sim_t=([0-9.]+)")
_WALL = re.compile(r"^\[[^]]+\] \[[A-Z]+\] \[([0-9.]+)\]")


def _wall(line: str) -> float | None:
    m = _WALL.match(line)
    return float(m.group(1)) if m else None


def _artifacts(bundle: Path) -> dict[str, dict]:
    out = {}
    for path in glob.glob(str(bundle / "decisions" / "*.json")):
        data = json.loads(Path(path).read_text())
        rid = data.get("diagnostics", {}).get("request_id") or Path(path).stem
        out[rid] = data
    return out


def _signature(command: dict | None) -> tuple:
    if not command:
        return ()
    return tuple(sorted((a["robot_id"], a["action"]) for a in command.get("actions", [])))


def _empty_reroute_fallback(command: dict | None) -> bool:
    if not command:
        return False
    tags = command.get("degradations", [])
    fallback = any(
        t.startswith("retreat=no-valid-candidate") or t.startswith("yield=infeasible:")
        for t in tags
    )
    empty = any(
        a["action"] == "reroute" and not a.get("parameters", {}).get("waypoints")
        for a in command.get("actions", [])
    )
    return fallback and empty


def _wall_to_sim(m4_lines: list[str]) -> list[tuple[float, float]]:
    pts = []
    for line in m4_lines:
        m = _SIM_T.search(line)
        w = _wall(line)
        if m and w is not None:
            pts.append((w, float(m.group(1))))
    return sorted(pts)


def _sim_at(pts: list[tuple[float, float]], wall: float) -> float | None:
    if not pts:
        return None
    walls = [p[0] for p in pts]
    i = bisect.bisect_left(walls, wall)
    lo = pts[max(i - 1, 0)]
    hi = pts[min(i, len(pts) - 1)]
    if hi[0] == lo[0]:
        return lo[1]
    return lo[1] + (wall - lo[0]) * (hi[1] - lo[1]) / (hi[0] - lo[0])


def analyse(bundle: Path) -> dict:
    """Score one episode bundle."""
    m4 = (bundle / "m4.log").read_text(errors="replace").splitlines()
    m5 = (bundle / "m5.log").read_text(errors="replace").splitlines()
    m5_text = "\n".join(m5)
    arts = _artifacts(bundle)
    pts = _wall_to_sim(m4 + m5)

    analyses = re.findall(r"starting analysis request=([0-9a-f]+)", m5_text)
    refusal_withheld = re.findall(r"refusal withheld request=([0-9a-f]+)", m5_text)
    empty_withheld = re.findall(r"empty reroute withheld request=([0-9a-f]+)", m5_text)
    dispatched_ids = []
    for line in m5:
        m = re.search(r"dispatch request=([0-9a-f]+) command=(\S+)", line)
        if m and m.group(1) not in dispatched_ids:
            dispatched_ids.append(m.group(1))
    armed_outcomes = Counter(re.findall(r"reanalysis suppression armed .*?outcome=(\S+)", m5_text))

    dispatched = []
    for rid in dispatched_ids:
        art = arts.get(rid, {})
        cmd = art.get("dispatched_command")
        line = next((ln for ln in m5 if f"dispatch request={rid}" in ln), "")
        dispatched.append(
            {
                "request": rid[:8],
                "sim_t": None if _wall(line) is None else _sim_at(pts, _wall(line)),
                "actions": [f"{r}:{a}" for r, a in _signature(cmd)],
                "empty_reroute_fallback": _empty_reroute_fallback(cmd),
                "tags": [
                    t
                    for t in (cmd or {}).get("degradations", [])
                    if t.startswith(("grounding=", "yield_robot=", "retreat=", "yield="))
                ],
            }
        )
    longest, run = 0, 0
    prev = None
    for d in dispatched:
        sig = tuple(d["actions"])
        run = run + 1 if sig == prev else 1
        prev = sig
        longest = max(longest, run)

    admits = {}
    for line in m4:
        m = re.search(
            r"gate_admit command=(\S+) yielder=(\S+) passer=(\S+) clear_m=(\S+) "
            r"escort_m=(\S+) sim_t=([0-9.]+)",
            line,
        )
        if m:
            admits.setdefault(m.group(1), []).append(
                {"yielder": m.group(2), "passer": m.group(3), "clear_m": m.group(4),
                 "escort_m": m.group(5), "admit_sim_t": float(m.group(6))}
            )
    releases = {}
    for line in m4:
        m = re.search(
            r"gate_release command=(\S+) yielder=(\S+) reason=(\S+) sim_t=([0-9.]+)", line
        )
        if m:
            releases.setdefault(m.group(1), []).append(
                {"reason": m.group(3), "release_sim_t": float(m.group(4))}
            )
    statuses: dict[str, dict[str, str]] = {}
    for line in m4:
        m = re.search(
            r"command_bus_node\]: status published command=(\S+) robot=(\S+) status=(\S+)", line
        )
        if m and m.group(3) in ("COMPLETED", "FAILED", "CANCELLED"):
            statuses.setdefault(m.group(1), {})[m.group(2)] = m.group(3)

    task_events = []
    for path in glob.glob(str(bundle / "decisions" / "tasks_*.jsonl")):
        task_events += [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    arrivals = [e for e in task_events if e.get("event") == "arrived"]
    done = sorted({e["robot_id"] for e in task_events if e.get("event") == "robot_done"})

    resolution = []
    for command, adm in admits.items():
        for a in adm:
            rel = next(
                (r for r in releases.get(command, []) if r["release_sim_t"] >= a["admit_sim_t"]),
                None,
            )
            after = [
                e for e in arrivals
                if e.get("sim_t") is not None and e["sim_t"] >= a["admit_sim_t"]
            ]
            resolution.append(
                {
                    "command": command[:8],
                    **a,
                    "release": rel,
                    "statuses": statuses.get(command, {}),
                    "arrivals_after_admit": len(after),
                    "passer_arrived_after_admit": any(
                        e["robot_id"] == a["passer"] for e in after
                    ),
                }
            )

    gt = slcs._jl(bundle / "gt" / "ground_truth.jsonl")
    gt_t = [r["sim_time_sec"] for r in gt]
    scene = [r for r in slcs._jl(bundle / "m5_scene.jsonl") if r["scene"].get("stamp") is not None]
    off = slcs._gt_offset(gt, scene) if gt and scene else 0.0

    def gt_at(t: float) -> dict:
        i = bisect.bisect_left(gt_t, t)
        return gt[min(max(i, 0), len(gt) - 1)]["robots"]

    waivers = []
    for line in m4:
        m = re.search(r"latch waiver armed robot=(\S+) command=(\S+) partners=(\S+)", line)
        if not m:
            continue
        robot, command, partners = m.group(1), m.group(2), m.group(3).split(",")
        start = _sim_at(pts, _wall(line))
        end_line = next(
            (
                ln for ln in m4
                if f"status published command={command} robot={robot} status=" in ln
                and re.search(r"status=(COMPLETED|FAILED|CANCELLED)", ln)
            ),
            None,
        )
        end = _sim_at(pts, _wall(end_line)) if end_line else (gt_t[-1] + off if gt_t else None)
        released = [
            ln for ln in m4 if f"latch waiver released robot={robot} command={command}" in ln
        ]
        info = {"robot": robot, "command": command[:8], "partners": partners,
                "start_sim_t": start, "end_sim_t": end,
                "end_status": re.search(r"status=(\S+)", end_line).group(1) if end_line else None,
                "released": [re.search(r"partner=(\S+)", ln).group(1) for ln in released]}
        if gt and start is not None and end is not None:
            g0 = gt_at(start - off)[robot]
            g15 = gt_at(min(start + 15.0, end) - off)[robot]
            span = [r["robots"] for r in gt if start - off <= r["sim_time_sec"] <= end - off]
            moved = math.hypot(g15["x"] - g0["x"], g15["y"] - g0["y"])
            info["yielder_moved_15s_m"] = round(moved, 3)
            info["gt_min_gap_to_partner_m"] = {
                p: round(min(math.hypot(s[robot]["x"] - s[p]["x"], s[robot]["y"] - s[p]["y"])
                             for s in span), 3) if span else None
                for p in partners
            }
        waivers.append(info)

    yields = [d for d in dispatched if any(a.endswith(":yield") for a in d["actions"])]
    return {
        "bundle": bundle.name,
        "analyses": len(analyses),
        "withheld_refusal": len(refusal_withheld),
        "withheld_empty_reroute": len(empty_withheld),
        "dispatched": len(dispatched),
        "dispatched_yields": len(yields),
        "dispatched_empty_reroute_fallbacks": sum(d["empty_reroute_fallback"] for d in dispatched),
        "longest_identical_dispatch_run": longest,
        "suppressed_reanalyses": m5_text.count("reanalysis suppressed reason"),
        "suppression_armed": dict(armed_outcomes),
        "dispatches": dispatched,
        "resolution_events": resolution,
        "executed_resolution_events": sum(1 for r in resolution if r["release"] is not None),
        "waivers": waivers,
        "waiver_lines": sum("latch waiver" in ln for ln in m4),
        "tasks_completed": len(arrivals),
        "robot_done": done,
        "gt_offset_s": off,
    }


def main() -> None:
    """Entry point."""
    for b in sys.argv[1:]:
        print(json.dumps(analyse(Path(b)), default=str))


if __name__ == "__main__":
    main()

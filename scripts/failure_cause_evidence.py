"""Offline evidence sheets for the frozen five-robot S1b failure-cause rubric.

Rubric: `docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md` section 7,
frozen at `b70d925` (branch `demo/campaign-kits`). Methods note:
`docs/reports/2026-11-15-failure-cause-evidence-tool.md`.

Read-only on every bundle; writes only under `--out`. No VM, no API call. It
never reads a report (rubric 7.7): outcome fields enter only through a static
input file at render time, and only into the full (reconciliation) sheets.

Subcommands (run one at a time; each is one Python process):

- `episode --bundle B --label L --stratum S --arm A|B [--params-from B2]`:
  one bundle's mechanical inputs (failure units, event timeline, T1 decision
  substitution with its fidelity gate, T2 straight-move geometry, T3
  execution check, contacts) as `full/<L>/evidence.json`.
- `render`: rater sheets (events sheet and GT-only sheet, unlinked opaque ids),
  the key file, full Markdown sheets, the interception-table input, the
  coverage table and the leak check.

Code trees (asserted at start, recorded in every sheet):

- A33 scorer: this tree's `benchmarks/s1_scoring` (byte-identical to the
  registered `3c71503`): `bundle_io.read_bundle`, `conflicts.conflict_episodes`,
  `conflicts.classify_analysis`, `conflicts.match_analysis`, `ConflictParams()`.
- T1 grounder: v7n `demo/validation-guard-contacts` @ `a412949`:
  `reasoning.rag.command_grounder.ground_reasoner_result`,
  `swarm_orchestrator.reasoning_pipeline.yield_refusal_fan_out` /
  `empty_reroute_fallback`, `swarm_orchestrator.models.load_config`.
- Contact geometry: v7m `feat/gt-contact-logging` @ `b5eaee5`, imported by
  path: `isaac.vgu_sim.contact_geometry` (`scene_static_boxes`,
  `compute_contact_frame`, `robot_box_gap`, `TURTLEBOT3_BURGER_FOOTPRINT`) and
  `scripts/recompute_gt_contacts.recompute_bundle`.

Usage (repo root of this tree):
    /path/to/.venv/bin/python -B scripts/failure_cause_evidence.py episode \\
        --bundle <dir> --label E12 --stratum pilot --arm A --out <dir>
    /path/to/.venv/bin/python -B scripts/failure_cause_evidence.py render --out <dir>
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib
import itertools
import json
import math
import re
import secrets
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parents[1]
V7N = Path("/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7n")
V7M = Path("/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7m")
T1_COMMIT = "a412949"
T1_GROUNDER_MD5 = "951c23b7f2e0168dab10022abccff77a"
CONTACT_COMMIT = "b5eaee5"

# Rubric 7.7 frozen parameters (quoted from section 7).
STALL_MOVE_M = 0.05  # lone stall: moved less than 0.05 m ...
STALL_WINDOW_S = 60.0  # ... over the last 60 sim-s; chain rule 60 sim-s; X2 60 s
STALE_MIN_S = 10.0  # X4
EXEC_FRACTION = 0.5  # T3: < 50 % counts as not executed
CONTACT_M = 0.005  # X5 / G5 contact gap
MIN_DISTANCE_M = 0.45  # T2 / X3 min_distance_m
T2_MARGIN_M = 0.05  # T2: half-width + 0.05 m

# Tool parameters (not in the rubric; fixed before either validation case was
# looked at, and listed in the methods note).
T2_STEP_M = 0.01
T2_MAX_M = 3.0
NEAR_M = 0.05  # "near" for a stalled leg: footprint gap at or below 0.05 m
PIN_STILL_S = 10.0  # pinned/stalled: moved < 0.05 m over the last 10 s of the leg
STOPPED_MPS = 0.05  # GT speed below which a robot is stopped (X3)
LATCH_SPAN_GAP_S = 2.0  # safety-stop lines closer than this join one span
BACKUP_SPEED_MPS = 0.1  # nav2_adapter.backup default (v7n nav2_adapter.py:180)
DEADLINE_FACTOR = 15.0  # nav2_adapter._DEADLINE_FACTOR (v7n nav2_adapter.py:176)
DEADLINE_FLOOR_S = 30.0
SNAP_TOL_S = 1.0  # t0 snapshot: first m5_scene row within 1 s after t0
GUARD_KEYS = ("escort_obstacle_guard", "escort_park_clearance")
FIDELITY_IGNORED = {"plan_id", "backup_facing_rad", "backup_reference_yaw_rad"}
MOTION_KINDS = {"reverse", "backup", "escort", "reroute"}


# --------------------------------------------------------------------------
# imports pinned to their trees
# --------------------------------------------------------------------------


def _git(tree: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(tree), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_trees() -> dict[str, Any]:
    """Import the scorer (this tree), grounder (v7n) and contact code (v7m), and assert where each came from."""
    sys.path.insert(0, str(HERE))
    scorer_io = importlib.import_module("benchmarks.s1_scoring.bundle_io")
    # The scorer's conflicts module imports `reasoning.rag.plan_metrics`; it
    # must resolve to the T1 tree like every other `reasoning` import.
    sys.path[:0] = [
        str(V7N),
        str(V7N / "ros2_ws/src/swarm_orchestrator"),
        str(V7N / "ros2_ws/src/swarm_execution"),
    ]
    for name in [m for m in sys.modules if m == "reasoning" or m.startswith("reasoning.")]:
        del sys.modules[name]
    grounder = importlib.import_module("reasoning.rag.command_grounder")
    params_mod = importlib.import_module("reasoning.rag.maneuver_geometry")
    vlm_models = importlib.import_module("reasoning.vlm.models")
    pipeline = importlib.import_module("swarm_orchestrator.reasoning_pipeline")
    orch_models = importlib.import_module("swarm_orchestrator.models")
    conflicts = importlib.import_module("benchmarks.s1_scoring.conflicts")
    if "isaac" in sys.modules:
        raise SystemExit("isaac imported before the contact tree was put first")
    sys.path.insert(0, str(V7M))
    contact = importlib.import_module("isaac.vgu_sim.contact_geometry")
    isaac_config = importlib.import_module("isaac.vgu_sim.config")
    sys.path.insert(0, str(V7M / "scripts"))
    recompute = importlib.import_module("recompute_gt_contacts")
    checks = {
        "scorer": (scorer_io.__file__, HERE),
        "conflicts": (conflicts.__file__, HERE),
        "grounder": (grounder.__file__, V7N),
        "pipeline": (pipeline.__file__, V7N),
        "contact": (contact.__file__, V7M),
        "recompute": (recompute.__file__, V7M),
    }
    for name, (path, root) in checks.items():
        if not str(Path(path).resolve()).startswith(str(root)):
            raise SystemExit(f"{name} resolved to {path}, expected under {root}")
    if _git(V7N, "rev-parse", "--short", "HEAD") != T1_COMMIT:
        raise SystemExit("v7n HEAD is not a412949")
    if _git(V7N, "status", "--short", "--", "reasoning", "ros2_ws"):
        raise SystemExit("v7n reasoning/ros2_ws not clean")
    if _md5(Path(grounder.__file__)) != T1_GROUNDER_MD5:
        raise SystemExit("command_grounder.py md5 differs from the rubric's")
    if _git(V7M, "rev-parse", "--short", "HEAD") != CONTACT_COMMIT:
        raise SystemExit("v7m HEAD is not b5eaee5")
    provenance = {
        "scorer_tree": f"{HERE} @ {_git(HERE, 'rev-parse', '--short', 'HEAD')}",
        "scorer_files_equal_3c71503": _git(
            HERE, "diff", "--stat", "3c71503", "HEAD", "--", "benchmarks/s1_scoring"
        ) == "",
        "t1_tree": f"{V7N} @ {T1_COMMIT}",
        "t1_command_grounder_md5": T1_GROUNDER_MD5,
        "contact_tree": f"{V7M} @ {CONTACT_COMMIT}",
        "tool_md5": _md5(Path(__file__)),
        "functions": {
            "units": "benchmarks.s1_scoring.bundle_io.read_bundle; "
            "benchmarks.s1_scoring.conflicts.conflict_episodes(ConflictParams())",
            "matching": "conflicts.classify_analysis + conflicts.match_analysis",
            "t1": "reasoning.rag.command_grounder.ground_reasoner_result (v7n a412949)",
            "withheld": "swarm_orchestrator.reasoning_pipeline.yield_refusal_fan_out, "
            "empty_reroute_fallback (v7n a412949)",
            "contacts": "isaac.vgu_sim.contact_geometry.compute_contact_frame / "
            "scene_static_boxes (v7m b5eaee5); recompute_gt_contacts.recompute_bundle",
        },
    }
    return {
        "io": scorer_io, "conflicts": conflicts, "grounder": grounder,
        "params": params_mod, "vlm": vlm_models, "pipeline": pipeline,
        "orch": orch_models, "contact": contact, "isaac_config": isaac_config,
        "recompute": recompute, "provenance": provenance,
    }


# --------------------------------------------------------------------------
# pure helpers (unit-tested without the trees)
# --------------------------------------------------------------------------


def lone_stalls(
    gt: list[tuple[float, dict[str, tuple[float, float]]]],
    fu_robots: set[str],
    dwelling_at_end: set[str],
    move_m: float = STALL_MOVE_M,
    window_s: float = STALL_WINDOW_S,
) -> list[dict[str, Any]]:
    """Rubric 7.1 lone stalls from GT samples `(t, {robot: (x, y)})` on one clock.

    A robot is a lone stall when every pose over the last `window_s` before the
    last sample lies within `move_m` of its final pose, it is not dwelling at a
    task node at censoring, and it is in no to-end conflict. The stationary run
    starts at the earliest sample after which every pose stays within `move_m`
    of the final pose (tool reading of "start of the stationary run").

    Args:
        gt: GT samples in time order.
        fu_robots: Robots already in a to-end conflict FU.
        dwelling_at_end: Robots dwelling at a task node at censoring.
        move_m: Movement bound.
        window_s: Window before censoring.

    Returns:
        One dict per lone stall: robot, onset, end, max deviation in the window.
    """
    if not gt:
        return []
    t_end = gt[-1][0]
    out = []
    robots = sorted(gt[-1][1], key=lambda r: (len(r), r))
    for rid in robots:
        if rid in fu_robots:
            continue
        fx, fy = gt[-1][1][rid]
        window = [(t, p[rid]) for t, p in gt if t >= t_end - window_s and rid in p]
        dev = max(math.hypot(x - fx, y - fy) for _, (x, y) in window)
        if dev >= move_m:
            continue
        onset = t_end
        for t, p in reversed(gt):
            if rid not in p:
                break
            x, y = p[rid]
            if math.hypot(x - fx, y - fy) >= move_m:
                break
            onset = t
        out.append({
            "robot": rid, "onset": onset, "end": t_end, "max_dev_window_m": round(dev, 4),
            "dwelling_at_end": rid in dwelling_at_end,
            "excluded": rid in dwelling_at_end,
        })
    return out


def task_phase_at(
    events: list[dict[str, Any]], robot: str, t: float, dwell_s: float
) -> dict[str, Any]:
    """Reconstruct one robot's task-stream phase at M1-clock time `t` from `tasks_*.jsonl` events.

    Args:
        events: The stream's `released`/`issued`/`arrived`/`dwell_complete` rows.
        robot: Robot id.
        t: M1-clock time.
        dwell_s: The stream's `dwell_sim_sec`.

    Returns:
        `phase` (held, traveling, dwelling, finished), `index`, `node`,
        `goal`, `dwell_left_s`.
    """
    state: dict[str, Any] = {"phase": "held", "index": None, "node": None, "goal": None,
                             "dwell_left_s": None, "dwell_from": None}
    for e in events:
        if e.get("robot_id") != robot or e.get("sim_t") is None or e["sim_t"] > t:
            continue
        ev = e.get("event")
        if ev == "issued":
            state.update(phase="traveling", index=e.get("task_index"), node=e.get("node"),
                         goal=tuple(e["goal"]) if e.get("goal") else None, dwell_from=None)
        elif ev == "arrived":
            state.update(phase="dwelling", dwell_from=e["sim_t"])
        elif ev == "dwell_complete":
            state.update(phase="between", dwell_from=None)
    if state["phase"] == "between":
        state["phase"] = "finished"
    if state["phase"] == "traveling":
        state["dwell_left_s"] = dwell_s
    elif state["phase"] == "dwelling":
        state["dwell_left_s"] = max(0.0, dwell_s - (t - state["dwell_from"]))
    return state


def fit_wall_to_sim(anchors: list[tuple[float, float]]) -> dict[str, Any] | None:
    """Least-squares line sim = a * wall + b over `(wall, sim)` anchors (rubric 7.1)."""
    if len(anchors) < 2:
        return None
    n = len(anchors)
    mw = sum(w for w, _ in anchors) / n
    ms = sum(s for _, s in anchors) / n
    var = sum((w - mw) ** 2 for w, _ in anchors)
    if var == 0:
        return None
    a = sum((w - mw) * (s - ms) for w, s in anchors) / var
    b = ms - a * mw
    resid = [abs(s - (a * w + b)) for w, s in anchors]
    return {
        "a": a, "b": b, "n": n, "max_resid_s": round(max(resid), 3),
        "wall_span": [round(min(w for w, _ in anchors), 1), round(max(w for w, _ in anchors), 1)],
        "rtf": round(a, 4),
    }


def collapse_spans(times: list[float], gap_s: float) -> list[tuple[float, float, int]]:
    """Join sorted times into spans whose consecutive gaps are at most `gap_s`."""
    spans: list[tuple[float, float, int]] = []
    for t in sorted(times):
        if spans and t - spans[-1][1] <= gap_s:
            s, _, n = spans[-1]
            spans[-1] = (s, t, n + 1)
        else:
            spans.append((t, t, 1))
    return spans


def contract_checks(decision: dict[str, Any]) -> dict[str, Any]:
    """Rubric 7.3 C1-C3 on a parsed decision (mechanical; V4j is left to raters)."""
    strategy = decision.get("strategy")
    plan = decision.get("proposed_plan")
    involved = list(decision.get("involved_robots") or [])
    legs = [leg for leg in plan if isinstance(leg, dict)] if isinstance(plan, list) else []
    out: dict[str, Any] = {"plan_present": bool(legs), "C1": None, "C2": None, "C3": None}
    if not legs:
        return out
    if strategy == "reverse":
        rev = sorted({leg["robot_id"] for leg in legs if leg.get("action") == "reverse"})
        out["C1"] = rev != sorted(set(involved))
        out["C1_detail"] = {"reverse_legs": rev, "involved": sorted(set(involved))}
    elif strategy == "yield":
        ylegs = [leg["robot_id"] for leg in legs if leg.get("action") == "yield"]
        out["C2"] = len(ylegs) != 1 or ylegs[0] != decision.get("yield_robot")
        out["C2_detail"] = {"yield_legs": ylegs, "yield_robot": decision.get("yield_robot")}
    elif strategy == "reroute":
        lead = involved[0] if involved else None
        out["C3"] = not any(
            leg.get("action") == "reroute" and leg.get("robot_id") == lead for leg in legs
        )
        out["C3_detail"] = {"involved_0": lead}
    return out


def command_kinds(command: dict[str, Any] | None) -> dict[str, list[str]]:
    """Per-robot motion kinds of a grounded command (yield -> backup, passer -> escort)."""
    out: dict[str, list[str]] = defaultdict(list)
    for a in (command or {}).get("actions") or []:
        rid, act = a.get("robot_id"), a.get("action")
        p = a.get("parameters") or {}
        if act == "yield":
            out[rid].append("backup")
            passer = p.get("passer_robot_id")
            if passer and (p.get("passer_escort_distance_m") or 0) > 0:
                out[passer].append("escort")
        elif act == "reroute":
            out[rid].append("reroute" if p.get("waypoints") else "reroute_empty")
        elif act == "temporary_wait":
            out[rid].append("wait")
        else:
            out[rid].append(str(act))
    return dict(out)


def strip_actions(command: dict[str, Any]) -> list[dict[str, Any]]:
    """Actions with the fidelity gate's ignored keys removed (plan_id, A25 keys)."""
    return [
        {**a, "parameters": {
            k: v for k, v in (a.get("parameters") or {}).items() if k not in FIDELITY_IGNORED
        }}
        for a in command.get("actions") or []
    ]


def reproduces(out: dict[str, Any] | None, live: dict[str, Any]) -> bool:
    """Rubric 7.4 fidelity gate: same actions and degradations, plan_id and A25 keys aside."""
    return out is not None and strip_actions(out) == strip_actions(live) and (
        out.get("degradations") or []
    ) == (live.get("degradations") or [])


def hypothesis_set(candidates: list[str]) -> list[dict[str, Any]]:
    """Rubric 7.4 H over `candidates` (FU robots plus the two nearest others).

    Returns:
        Hypothetical decision fields: strategy, involved_robots, yield_robot,
        crossing_order, and a compact id.
    """
    rs = sorted(candidates, key=lambda r: (len(r), r))
    hs: list[dict[str, Any]] = []
    # The schema requires crossing_order to be a permutation of
    # involved_robots; the recorded convention puts the passers first and the
    # yielder last, so "a crossing order of at most 4 robots" is read as at
    # most 3 passers plus the yielder.
    for y in rs:
        for p in rs:
            if p != y:
                hs.append({"id": f"Y:{y}>{p}", "strategy": "yield", "involved": [y, p],
                           "yield_robot": y, "crossing_order": [p, y]})
    for y in rs:
        others = [r for r in rs if r != y]
        for k in range(2, min(3, len(others)) + 1):
            for order in itertools.permutations(others, k):
                hs.append({"id": f"Y:{y}>{'>'.join(order)}", "strategy": "yield",
                           "involved": [y, *order], "yield_robot": y,
                           "crossing_order": [*order, y]})
    subsets = [list(c) for k in (1, 2) for c in itertools.combinations(rs, k)]
    if len(rs) > 2:
        subsets.append(list(rs))
    for s in subsets:
        hs.append({"id": f"R:{'+'.join(s)}", "strategy": "reverse", "involved": s,
                   "yield_robot": None, "crossing_order": None})
    for lead in rs:
        rest = [r for r in rs if r != lead]
        hs.append({"id": f"RR:{lead}", "strategy": "reroute", "involved": [lead, *rest],
                   "yield_robot": None, "crossing_order": None})
    hs.append({"id": "W", "strategy": "temporary_wait", "involved": list(rs),
               "yield_robot": None, "crossing_order": None})
    for strat, tag in (("convoy", "CV"), ("priority_override", "PO"), ("junction_clear", "JC")):
        for lead in rs:
            rest = [r for r in rs if r != lead]
            hs.append({"id": f"{tag}:{lead}", "strategy": strat, "involved": [lead, *rest],
                       "yield_robot": None, "crossing_order": None})
    return hs


def chain_links(
    legs: list[dict[str, Any]], fu_robots: set[str], t0: float, window_s: float = STALL_WINDOW_S
) -> dict[str, list[str]]:
    """Mechanical chain linkage of dispatched legs to one FU (rubric 7.5 step 2, and the end-window variant).

    Args:
        legs: Each with `leg_id`, `robot`, `dispatch_rel`, `start_rel`, `end_rel`.
        fu_robots: The FU's robots.
        t0: The FU onset (rel-s).
        window_s: The rubric's 60 sim-s.

    Returns:
        `rubric`: legs whose robot is in the FU and that were dispatched in
        [t0 - 60, t0] or were executing at t0; `end_window`: legs whose robot is
        in the FU and that ended in [t0 - 60, t0].
    """
    rubric, end_window = [], []
    for leg in legs:
        if leg["robot"] not in fu_robots:
            continue
        d, s, e = leg.get("dispatch_rel"), leg.get("start_rel"), leg.get("end_rel")
        executing = s is not None and s <= t0 and (e is None or e >= t0)
        if (d is not None and t0 - window_s <= d <= t0) or executing:
            rubric.append(leg["leg_id"])
        if e is not None and t0 - window_s <= e <= t0:
            end_window.append(leg["leg_id"])
    return {"rubric": rubric, "end_window": end_window}


LEAK_PATTERNS = [
    r"\barm\s*[ab]\b", r"\barm[ab]\b", r"l2off", r"\ber-?2\b", r"\bgemini", r"conft1",
    r"confirmatory", r"\becho\b", r"\bE(?:[1-9]|[12][0-9]|3[01])\b", r"\bm5[dv]\b",
    r"attribution", r"churn_class", r"primary cause", r"conclusion", r"data/logs",
    r"/users/", r"vgu-vlm-swarm", r"reasoning_enabled", r"\btranche", r"\bpilot",
    r"\bdemo\b", r"run_id", r"session_id", r"\bseed",
]


def leak_hits(text: str, extra: list[str]) -> list[str]:
    """Forbidden tokens found in a rater sheet (word-aware; `extra` are literal seeds, ids, names)."""
    hits = []
    low = text.lower()
    for pat in LEAK_PATTERNS:
        for m in re.finditer(pat, low, flags=re.IGNORECASE):
            hits.append(f"{pat}:{low[max(0, m.start() - 20):m.end() + 20]!r}")
    for lit in extra:
        if lit and lit.lower() in low:
            hits.append(f"literal:{lit}")
    return hits


def rater_view(full: dict[str, Any], did: dict[str, str]) -> dict[str, Any]:
    """The events sheet raters may see: full sheet minus arm, ids, outcomes, guard verdicts.

    Args:
        full: The full evidence sheet.
        did: request_id -> opaque decision id (D1, D2, ...).

    Returns:
        The filtered sheet (JSON-ready).
    """
    def sub(text: Any) -> Any:
        if isinstance(text, str):
            for rid, d in did.items():
                text = text.replace(rid, d).replace(rid[:8], d)
            return text
        if isinstance(text, list):
            return [sub(x) for x in text]
        if isinstance(text, dict):
            return {sub(k): sub(v) for k, v in text.items() if k not in _RATER_DROP}
        return text

    keep = {k: full[k] for k in (
        "censor", "clock", "units", "decisions", "legs", "fidelity", "t1", "t2",
        "contacts", "stale_spans", "latch", "nav2",
    ) if k in full}
    return sub(keep)


_RATER_DROP = {
    "bundle", "label", "stratum", "arm", "seed", "run_id", "session_id",
    "outcome", "guard_verdict", "backend_id", "model_id", "served_model", "reasoner_config",
    "params_source", "paths", "cost",
}


def gt_view(full: dict[str, Any]) -> dict[str, Any]:
    """The GT-only sheet (arm-blind by construction: FUs, T2, X3/X5 from GT, contacts)."""
    units = []
    for u in full.get("units", []):
        units.append({k: u[k] for k in (
            "fu", "kind", "robots", "t0_rel", "end_rel", "pairs", "excluded", "flags",
            "x3_gt", "gt_contacts",
        ) if k in u})
    # Only the onset snapshot: analysis snapshots exist in Layer-2-on arms only.
    t2 = {fu: {k: v for k, v in rows.items() if k == "t0"}
          for fu, rows in (full.get("t2") or {}).items()}
    c = full.get("contacts") or {}
    return {
        "censor": {"t_end_rel": full["censor"]["t_end_rel"]},
        "units": units,
        "t2": t2,
        "contacts": {k: c.get(k) for k in (
            "recompute_verdicts", "recompute_robot_min_static_gap",
            "recompute_min_robot_robot_gap", "recompute_events", "spans_within_0.05m_rel",
            "declared_boxes", "undeclared_builder_boxes")},
    }


# --------------------------------------------------------------------------
# bundle readers
# --------------------------------------------------------------------------

_WALL = re.compile(r"\[(\d{9,10}\.\d+)\]")
_SIMT = re.compile(r"sim_t=([0-9.]+)")


def _wall(line: str) -> float | None:
    m = _WALL.search(line)
    return float(m.group(1)) if m else None


def parse_m4(path: Path) -> dict[str, Any]:
    """Stream `m4.log` into event lists (wall stamps; `sim_t=` anchors kept)."""
    out: dict[str, Any] = {
        "anchors": [], "received": [], "handover": [], "status": [], "gate": [],
        "escort": [], "exempt": [], "waiver": [], "detail": [], "safety_stop": defaultdict(list),
        "base_goal": [], "present": path.is_file(),
    }
    if not path.is_file():
        return out
    rx = {
        "received": re.compile(r"command received command=(\S+) robot=(\S+) action=(\S+)"),
        "handover": re.compile(
            r"controller stop robot=(\S+) command=(\S+) action=(\S+) reason=(\w+) sim_t=([0-9.]+)"
        ),
        "status": re.compile(r"status published command=(\S+) robot=(\S+) status=(\w+)"),
        "gate": re.compile(r"crossing_chain (gate_\w+) command=(\S+) (.*)"),
        "escort": re.compile(r"escort (robot_\d+): (\w+) (.*)"),
        "exempt": re.compile(r"exempt pairs changed pairs=(\S+)"),
        "waiver": re.compile(r"latch waiver(s changed| armed| released) (.*)"),
        "stop": re.compile(r"safety stop robot=(\S+) reason=(\S+)"),
        "base": re.compile(r"base goal reached robot=(\S+)"),
    }
    with path.open(errors="replace") as fh:
        for line in fh:
            if "safety stop robot=" in line:
                m = rx["stop"].search(line)
                w = _wall(line)
                if m and w is not None:
                    out["safety_stop"][(m.group(1), m.group(2))].append(w)
                continue
            if "republished" in line or "cancel-all" in line:
                continue
            w = _wall(line)
            s = _SIMT.search(line)
            if s and w is not None:
                out["anchors"].append((w, float(s.group(1))))
            for key in ("received", "handover", "status", "gate", "escort", "exempt",
                        "waiver", "base"):
                m = rx[key].search(line)
                if m:
                    out["base_goal" if key == "base" else key].append((w, *m.groups()))
                    break
            if ("timed out" in line or "stall_abort" in line or "FAILED" in line) and (
                "race guard" not in line
            ):
                out["detail"].append((w, line.strip().split("]: ", 1)[-1][:240]))
    return out


def parse_nav2(bundle: Path) -> list[tuple[float, str, str]]:
    """Nav2 abort / no-progress lines: (wall, robot, text)."""
    out = []
    for path in sorted(bundle.glob("nav2_r*.log")):
        robot = "robot_" + path.stem.split("_r")[-1]
        with path.open(errors="replace") as fh:
            for line in fh:
                if "Failed to make progress" in line or "Aborting handle" in line or (
                    "aborted" in line.lower() and "goal" in line.lower()
                ):
                    w = _wall(line)
                    if w is not None:
                        out.append((w, robot, line.strip().split("]: ", 1)[-1][:160]))
    return out


def parse_m5(path: Path) -> list[tuple[float, str, str]]:
    """M5 dispatch / withheld / analysis-start lines: (wall, kind, text)."""
    out = []
    if not path.is_file():
        return out
    keys = ("dispatch request=", "refusal withheld", "starting analysis", "yield refused",
            "command ", "churn")
    with path.open(errors="replace") as fh:
        for line in fh:
            if "trigger suppressed" in line or "reanalysis suppressed" in line:
                continue
            if any(k in line for k in keys):
                w = _wall(line)
                if w is not None:
                    out.append((w, next(k for k in keys if k in line).strip(),
                                line.strip().split("]: ", 1)[-1][:300]))
    return out


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


# --------------------------------------------------------------------------
# episode computation
# --------------------------------------------------------------------------


class Episode:
    """Everything the sheet needs for one bundle."""

    def __init__(self, trees: dict[str, Any], bundle: Path, args: argparse.Namespace) -> None:
        self.T = trees
        self.bundle = bundle
        self.args = args
        import yaml  # noqa: PLC0415

        self.yaml = yaml
        self.records = trees["io"].read_bundle(bundle)
        self.raw_config = yaml.safe_load((bundle / "orchestrator.overlaid.yaml").read_text())
        self.config = trees["orch"].load_config(self.raw_config)
        self.scenario = trees["isaac_config"].ScenarioConfig.model_validate(
            yaml.safe_load((bundle / "scenario.yaml").read_text())
        )
        self.boxes = trees["contact"].scene_static_boxes(self.scenario)
        self.declared = {o.obstacle_id for o in self.config.static_obstacles}
        self.chassis = tuple(
            p for p in trees["contact"].TURTLEBOT3_BURGER_FOOTPRINT if p.name == "chassis"
        )
        geometry = self.config.scenario_geometry
        self.half_width = geometry.robot.half_width_m if geometry is not None else 0.09
        tasks = sorted(bundle.glob("decisions/tasks_*.jsonl"))
        self.tasks = read_jsonl(tasks[0]) if tasks else []
        self.stream = next((r for r in self.tasks if r.get("event") == "stream_start"), {})
        self.task_events = [r for r in self.tasks if r.get("event") in (
            "released", "issued", "arrived", "dwell_complete")]
        self.dwell_s = float(self.stream.get("dwell_sim_sec") or 0.0)
        self.scene = read_jsonl(bundle / "m5_scene.jsonl")
        self.scene_t = [r["scene"]["stamp"] for r in self.scene if r.get("scene", {}).get("stamp")
                        is not None]
        self.gt_rows = read_jsonl(bundle / "gt" / "ground_truth.jsonl")
        self.m4 = parse_m4(bundle / "m4.log")
        self.fit = fit_wall_to_sim(self.m4["anchors"])
        self.nav2 = parse_nav2(bundle)
        self.m5 = parse_m5(bundle / "m5.log")
        self.artifacts = self.records.artifacts
        self.rel = self.records.m1_to_rel
        self.offset = self.records.gt_offset_s

    # clocks ---------------------------------------------------------------

    def wall_to_sim(self, w: float | None) -> float | None:
        if w is None or self.fit is None:
            return None
        return self.fit["a"] * w + self.fit["b"]

    def wall_to_sim_local(self, w: float | None) -> float | None:
        """Piecewise-linear wall->sim between the neighbouring m4 anchors (T3 windows only)."""
        if w is None:
            return None
        anchors = sorted(self.m4["anchors"])
        walls = [a for a, _ in anchors]
        i = bisect.bisect_left(walls, w)
        if 0 < i < len(anchors) and walls[i] > walls[i - 1]:
            (w0, s0), (w1, s1) = anchors[i - 1], anchors[i]
            return s0 + (s1 - s0) * (w - w0) / (w1 - w0)
        return self.wall_to_sim(w)

    def sim_to_rel(self, s: float | None) -> float | None:
        return None if s is None else round(self.rel(s), 3)

    def wall_to_rel(self, w: float | None) -> float | None:
        return self.sim_to_rel(self.wall_to_sim(w))

    def gt_rel(self, t_gt: float) -> float:
        return round(self.records.gt_to_rel(t_gt), 3)

    # GT -------------------------------------------------------------------

    def gt_series(self) -> list[tuple[float, dict[str, tuple[float, float, float, float]]]]:
        return [
            (self.records.gt_to_rel(r["sim_time_sec"]), {
                rid: (v["x"], v["y"], v.get("theta", 0.0), float(v.get("speed_mps") or 0.0))
                for rid, v in r["robots"].items()
            })
            for r in self.gt_rows
        ]

    def contact_frames(self) -> list[Any]:
        c = self.T["contact"]
        frames = []
        for r in self.gt_rows:
            poses = {rid: (v["x"], v["y"], v.get("theta", 0.0)) for rid, v in r["robots"].items()}
            frames.append(c.compute_contact_frame(
                poses, self.boxes, r["sim_time_sec"], near_cutoff_m=NEAR_M
            ))
        return frames

    # units ----------------------------------------------------------------

    def units(self, gts) -> tuple[list[dict[str, Any]], list[Any], list[Any]]:
        conf = self.T["conflicts"]
        params = conf.ConflictParams()
        episodes = conf.conflict_episodes(self.records, params)
        analyses = []
        for a in self.artifacts:
            an = conf.classify_analysis(self.records, a)
            an = an.model_copy(update={"matched_conflict": conf.match_analysis(an, episodes, params)})
            analyses.append(an)
        units = []
        fu_robots: set[str] = set()
        for ep in episodes:
            if not ep.to_end:
                continue
            fu_robots |= set(ep.involved)
            units.append({
                "fu": f"FU{len(units) + 1}", "kind": "conflict", "conflict_index": ep.index,
                "robots": list(ep.involved), "t0_rel": round(ep.onset_s, 3),
                "end_rel": round(ep.end_s, 3), "pairs": [list(p) for p in ep.pairs],
                "excluded": False, "flags": [],
            })
        t_end_m1 = self.records.t0_m1 + self.records.t_end_rel
        dwelling = {
            rid for rid in self.stream.get("sequences", {})
            if task_phase_at(self.task_events, rid, t_end_m1, self.dwell_s)["phase"] == "dwelling"
        }
        finished = {
            rid for rid in self.stream.get("sequences", {})
            if task_phase_at(self.task_events, rid, t_end_m1, self.dwell_s)["phase"] == "finished"
        }
        series = [(t, {rid: (p[0], p[1]) for rid, p in poses.items()}) for t, poses in gts]
        for ls in lone_stalls(series, fu_robots, dwelling):
            flags = []
            if ls["robot"] in finished:
                flags.append("finished_all_or_between_tasks_at_censor (tool flag; rubric silent)")
            if ls["dwelling_at_end"]:
                flags.append("dwelling_at_censor -> excluded by rubric 7.1")
            units.append({
                "fu": f"FU{len(units) + 1}", "kind": "lone_stall", "robots": [ls["robot"]],
                "t0_rel": round(ls["onset"], 3), "end_rel": round(ls["end"], 3), "pairs": [],
                "excluded": ls["excluded"], "flags": flags,
                "max_dev_window_m": ls["max_dev_window_m"],
            })
        return units, episodes, analyses

    # snapshots ------------------------------------------------------------

    def snapshot_at(self, t_m1: float) -> dict[str, Any] | None:
        i = bisect.bisect_left(self.scene_t, t_m1)
        if i < len(self.scene_t) and self.scene_t[i] - t_m1 <= SNAP_TOL_S:
            return self.scene[i]["scene"]
        return None

    def intents_at(self, t_m1: float) -> dict[str, Any]:
        RobotTaskIntent = importlib.import_module("reasoning.rag.retreat_shield").RobotTaskIntent
        nodes = self.stream.get("nodes") or {}
        seqs = self.stream.get("sequences") or {}
        out = {}
        for rid, seq in seqs.items():
            ph = task_phase_at(self.task_events, rid, t_m1, self.dwell_s)
            if ph["phase"] not in ("traveling", "dwelling") or ph["index"] is None:
                continue
            goal = ph["goal"] or tuple(nodes.get(ph["node"], (0.0, 0.0)))
            nxt = seq[ph["index"] + 1] if ph["index"] + 1 < len(seq) else None
            out[rid] = RobotTaskIntent(
                goal=(float(goal[0]), float(goal[1])),
                next_goal=None if nxt is None else tuple(float(v) for v in nodes[nxt]),
                dwell_sec=ph["dwell_left_s"] or 0.0,
            )
        return out

    # grounding ------------------------------------------------------------

    def ground(self, decision: dict[str, Any], scene: dict[str, Any], params: Any,
               yf: str, label: str | None, intents: dict[str, Any] | None) -> dict[str, Any]:
        V = self.T["vlm"]
        frame = V.SnapshotFrame(stamp=scene["stamp"], robots=[
            V.RobotStateInput(robot_id=r["robot_id"], x=r["x"], y=r["y"], theta=r["theta"],
                              status=r["status"],
                              goal=None if r.get("goal") is None else tuple(r["goal"]))
            for r in scene["robots"]
        ])
        result = V.ReasonerResult(
            request_id="replay", decision=V.CongestionDecision.model_validate(decision),
            raw_text="{}", diagnostics=V.ReasonerDiagnostics(
                request_id="replay", backend_id="replay", attempts=1, parse_status="valid"),
        )
        kwargs: dict[str, Any] = {}
        if intents is not None:
            kwargs["task_intents"] = intents
        return self.T["grounder"].ground_reasoner_result(
            result,
            robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
            geometry=self.config.scenario_geometry,
            static_obstacles=self.config.static_obstacles,
            yield_feasibility_mode=yf,
            snapshot=frame,
            params=params,
            retreat_choice=None if label is None else V.RetreatChoiceDecision(
                retreat_choice=label, justification="replay"),
            goal_references={s.robot_id: s.goal for s in frame.robots if s.goal is not None},
            **kwargs,
        )

    def withheld(self, command: dict[str, Any] | None) -> str | None:
        P = self.T["pipeline"]
        r = P.yield_refusal_fan_out(command)
        if r is not None:
            return f"refusal_no_action:{r}"
        e = P.empty_reroute_fallback(command)
        return None if e is None else f"empty_reroute:{e}"

    def fidelity(self) -> dict[str, Any]:
        """Re-ground every recorded decision three ways (rubric gate as written, +stage 2, +task intents)."""
        rows = []
        for a in self.artifacts:
            rid = a.get("request_id")
            d = a.get("decision")
            live = a.get("dispatched_command")
            if not d or not d.get("congestion_detected"):
                continue
            if not a.get("grounding_mode") or not live:
                rows.append({"request_id": rid, "status": "U:T1_no_record"})
                continue
            P = self.T["params"].GroundingParams(**a["grounding_params_source"]["params"])
            yf = a.get("grounding_yield_feasibility") or self.config.grounding_yield_feasibility
            label = (a.get("stage2") or {}).get("grounded_label")
            row: dict[str, Any] = {"request_id": rid, "strategy": d.get("strategy")}
            for name, lab, intents in (
                ("as_written", None, None),
                ("plus_stage2", label, None),
                ("plus_stage2_intents", label, self.intents_at(a["scene"]["stamp"])),
            ):
                try:
                    out = self.ground(d, a["scene"], P, yf, lab, intents)
                    ok = reproduces(out, live)
                    row[name] = "reproduced" if ok else "differs"
                    if not ok:
                        row[name + "_diff"] = _diff_summary(out, live)
                except Exception as exc:  # noqa: BLE001 - recorded, never hidden
                    row[name] = f"error:{type(exc).__name__}:{exc}"[:200]
            rows.append(row)
        rated = [r for r in rows if "as_written" in r]
        rates = {
            k: f"{sum(r.get(k) == 'reproduced' for r in rated)}/{len(rated)}"
            for k in ("as_written", "plus_stage2", "plus_stage2_intents")
        }
        return {"rows": rows, "rates": rates,
                "episode_usable": {k: bool(rated) and all(r.get(k) == "reproduced" for r in rated)
                                   for k in ("as_written", "plus_stage2", "plus_stage2_intents")},
                "n_no_record": sum(1 for r in rows if r.get("status") == "U:T1_no_record")}

    def params_for(self, t_m1: float) -> tuple[Any, str, str] | None:
        """Grounding params at time t: the latest artifact at or before t, else the first after, else the paired bundle's."""
        arts = [a for a in self.artifacts if (a.get("grounding_params_source") or {}).get("params")]
        src_bundle = self.bundle.name
        if not arts and self.args.params_from:
            other = Path(self.args.params_from)
            arts = []
            for p in sorted((other / "decisions").glob("*.json")):
                a = json.loads(p.read_text())
                if (a.get("grounding_params_source") or {}).get("params") and a.get("scene"):
                    arts.append(a)
            arts.sort(key=lambda a: a["scene"]["stamp"])
            src_bundle = other.name
        if not arts:
            return None
        before = [a for a in arts if a["scene"]["stamp"] <= t_m1]
        a = before[-1] if before else arts[0]
        yf = a.get("grounding_yield_feasibility") or self.config.grounding_yield_feasibility
        return (self.T["params"].GroundingParams(**a["grounding_params_source"]["params"]), yf,
                f"{src_bundle}:{a['request_id'][:8]}")

    def t1(self, scene: dict[str, Any], fu_robots: list[str], t_m1: float,
           recorded: dict[str, Any] | None) -> dict[str, Any]:
        """T1 over H at one snapshot: as written, with task intents, and every guard on."""
        present = {r["robot_id"]: (r["x"], r["y"]) for r in scene["robots"]}
        fu = [r for r in fu_robots if r in present]
        if not fu:
            return {"status": "U:fu_robot_absent_from_snapshot"}
        others = sorted(
            (min(math.dist(present[o], present[f]) for f in fu), o)
            for o in present if o not in fu
        )
        cands = fu + [o for _, o in others[:2]]
        pf = self.params_for(t_m1)
        if pf is None:
            return {"status": "U:no_grounding_params"}
        params, yf, src = pf
        if recorded is not None:
            params = self.T["params"].GroundingParams(
                **recorded["grounding_params_source"]["params"])
            yf = recorded.get("grounding_yield_feasibility") or yf
            src = f"{self.bundle.name}:{recorded['request_id'][:8]}"
        guards = params.model_copy(update={k: True for k in GUARD_KEYS})
        intents = self.intents_at(t_m1)
        out: dict[str, Any] = {"candidates": cands, "params_source": src, "variants": {}}
        for vname, prm, ints in (
            ("as_written", params, None),
            ("plus_intents", params, intents),
            ("all_guards_on", guards, None),
        ):
            motion, motion_any, errors, rows = [], [], 0, []
            for h in hypothesis_set(cands):
                dec = {
                    "reasoning": "hypothetical", "congestion_detected": True, "type": "deadlock",
                    "involved_robots": h["involved"], "root_cause": "hypothetical",
                    "strategy": h["strategy"], "justification": "hypothetical",
                    "yield_robot": h["yield_robot"], "blocker_kind": "robot",
                    "crossing_order": h["crossing_order"], "proposed_plan": None,
                }
                try:
                    cmd = self.ground(dec, scene, prm, yf, None, ints)
                except Exception as exc:  # noqa: BLE001 - counted and kept, never dropped
                    errors += 1
                    rows.append({"h": h["id"], "error": f"{type(exc).__name__}: {exc}"[:200]})
                    continue
                kinds = command_kinds(cmd)
                wh = self.withheld(cmd)
                fu_kinds = {r: kinds.get(r, []) for r in fu}
                strict = wh is None and any(set(v) & MOTION_KINDS for v in fu_kinds.values())
                loose = wh is None and any(
                    set(v) & (MOTION_KINDS | {"reroute_empty"}) for v in fu_kinds.values())
                if strict:
                    motion.append(h["id"])
                if loose:
                    motion_any.append(h["id"])
                rows.append({"h": h["id"], "kinds": kinds, "withheld": wh,
                             "tags": [t for t in cmd.get("degradations") or [] if "=" in t][:6]})
            out["variants"][vname] = {
                "n_h": len(rows), "n_errors": errors, "n_motion": len(motion),
                "nonempty": bool(motion), "motion": motion,
                "n_motion_counting_empty_reroute": len(motion_any),
                "_rows": rows,
            }
        return out

    # T2 -------------------------------------------------------------------

    def t2(self, scene: dict[str, Any], fu_robots: list[str], t_m1: float) -> dict[str, Any]:
        """Rubric 7.4 T2 at one snapshot (straight moves along 8 headings; chassis box)."""
        c = self.T["contact"]
        t_gt = t_m1 - self.offset
        boxes = [b for b in self.boxes if b.is_active(t_gt)]
        poses = {r["robot_id"]: (r["x"], r["y"], r["theta"]) for r in scene["robots"]}
        need = self.half_width + T2_MARGIN_M
        per_robot = {}
        best = None
        for rid in fu_robots:
            if rid not in poses:
                continue
            x0, y0, th = poses[rid]
            others = {o: p for o, p in poses.items() if o != rid}
            start_static = min(
                (g for g in (c.robot_box_gap((x0, y0, th), b, self.chassis) for b in boxes)
                 if g is not None), default=math.inf)
            start_robot = min(
                (c.robot_robot_gap((x0, y0, th), p, self.chassis) for p in others.values()),
                default=math.inf)
            headings = {}
            for k in range(8):
                h = k * math.pi / 4
                verdict = {"feasible": False, "distance_m": None, "blocked_by": None}
                d = 0.0
                while d <= T2_MAX_M + 1e-9:
                    pose = (x0 + d * math.cos(h), y0 + d * math.sin(h), th)
                    sg = min(((g, b.obstacle_id) for b in boxes
                              if (g := c.robot_box_gap(pose, b, self.chassis)) is not None),
                             default=(math.inf, None))
                    rg = min(((c.robot_robot_gap(pose, p, self.chassis), o)
                              for o, p in others.items()), default=(math.inf, None))
                    if sg[0] < need:
                        verdict["blocked_by"] = f"box:{sg[1]}@{d:.2f}"
                        break
                    if rg[0] < need:
                        verdict["blocked_by"] = f"robot:{rg[1]}@{d:.2f}"
                        break
                    if d > 0 and all(math.dist(pose[:2], p[:2]) >= MIN_DISTANCE_M
                                     for p in others.values()):
                        verdict.update(feasible=True, distance_m=round(d, 2))
                        break
                    d += T2_STEP_M
                headings[str(k * 45)] = verdict
                if verdict["feasible"] and (best is None or verdict["distance_m"] < best[0]):
                    best = (verdict["distance_m"], rid, k * 45)
            per_robot[rid] = {
                "start_gap_static_m": round(start_static, 4),
                "start_gap_robot_m": round(start_robot, 4),
                "start_within_required_clearance": start_static < need or start_robot < need,
                "headings": headings,
            }
        return {
            "result": best is not None,
            "shortest": None if best is None else {
                "robot": best[1], "heading_deg": best[2], "distance_m": best[0]},
            "required_gap_m": round(need, 3), "footprint": "URDF chassis box (v7m)",
            "per_robot": per_robot,
        }

    # legs -----------------------------------------------------------------

    def legs(self, gts, frames) -> list[dict[str, Any]]:
        """Every published command's per-robot leg with the T3 execution check."""
        status = defaultdict(list)
        for w, cmd, robot, st in self.m4["status"]:
            status[(cmd, robot)].append((w, st))
        handover = {}
        for w, robot, cmd, action, reason, simt in self.m4["handover"]:
            if reason == "handover" and (cmd, robot) not in handover:
                handover[(cmd, robot)] = float(simt)
        received = {}
        for w, cmd, robot, action in self.m4["received"]:
            received.setdefault((cmd, robot), w)
        gate_admit = {}
        for w, kind, cmd, rest in self.m4["gate"]:
            if kind == "gate_admit":
                m = re.search(r"passer=(\S+).*?sim_t=([0-9.]+)", rest)
                if m:
                    gate_admit[(cmd, m.group(1))] = float(m.group(2))
        escort_end = {}
        for w, robot, st, text in self.m4["escort"]:
            if st in ("COMPLETED", "FAILED", "CANCELED", "CANCELLED"):
                escort_end.setdefault(robot, []).append((w, st, text))
        detail = self.m4["detail"]
        t_end = self.records.t_end_rel
        out = []
        for a in self.artifacts:
            live = a.get("dispatched_command")
            if not live or a.get("dispatch_withheld"):
                continue
            cmd = live.get("command_id")
            dispatch_rel = self.sim_to_rel(a["scene"]["stamp"])
            for act in live.get("actions") or []:
                rid, kind = act["robot_id"], act["action"]
                p = act.get("parameters") or {}
                legs_here = []
                if kind == "yield":
                    legs_here.append(("backup", rid, p.get("backup_distance_m")))
                    passer = p.get("passer_robot_id")
                    if passer and (p.get("passer_escort_distance_m") or 0) > 0:
                        legs_here.append(("escort", passer, p.get("passer_escort_distance_m")))
                elif kind == "reverse":
                    legs_here.append(("reverse", rid, p.get("backup_distance_m")))
                elif kind == "reroute":
                    legs_here.append(("reroute", rid, None))
                else:
                    legs_here.append(("wait", rid, None))
                for lk, robot, dist in legs_here:
                    sts = status.get((cmd, robot if lk != "escort" else rid), [])
                    if lk == "escort":
                        start_sim = gate_admit.get((cmd, robot))
                        ends = [e for e in escort_end.get(robot, [])
                                if start_sim is None or (self.wall_to_sim(e[0]) or 0) >= start_sim - 1]
                        end_w = ends[0][0] if ends else None
                        terminal = ends[0][1] if ends else None
                        term_text = ends[0][2] if ends else None
                    else:
                        start_sim = handover.get((cmd, robot))
                        if start_sim is None and (cmd, robot) in received:
                            start_sim = self.wall_to_sim(received[(cmd, robot)])
                        terms = [(w, s) for w, s in sts if s not in ("ACTIVE", "PENDING")]
                        end_w = terms[0][0] if terms else None
                        terminal = terms[0][1] if terms else None
                        term_text = None
                    active_w = next((w for w, s in sts if s == "ACTIVE"), None)
                    start_rel = self.sim_to_rel(start_sim)
                    end_rel = self.wall_to_rel(end_w)
                    end_rel_local = self.sim_to_rel(self.wall_to_sim_local(end_w))
                    leg = {
                        "leg_id": f"{a['request_id'][:8]}:{robot}:{lk}",
                        "request_id": a["request_id"], "command_id": cmd, "robot": robot,
                        "kind": lk, "commanded_m": dist, "dispatch_rel": dispatch_rel,
                        "start_rel": start_rel, "end_rel": end_rel,
                        "end_rel_source": "m4 terminal line, wall->sim fit" if end_w else None,
                        "end_rel_local": end_rel_local,
                        "escort_admitted": None if lk != "escort" else start_sim is not None,
                        "received_by_m4": (cmd, robot if lk != "escort" else rid) in received,
                        "m4_terminal": terminal, "m4_terminal_text": term_text,
                        "m4_statuses": [s for _, s in sts],
                        "wall_elapsed_active_to_terminal_s": (
                            round(end_w - active_w, 1) if end_w and active_w else None),
                    }
                    if lk in ("backup", "reverse", "escort"):
                        leg.update(self.exec_check(leg, gts, frames, t_end))
                        if lk in ("backup", "reverse") and dist:
                            dl = max(DEADLINE_FACTOR * abs(dist) / BACKUP_SPEED_MPS,
                                     DEADLINE_FLOOR_S)
                            el = leg["wall_elapsed_active_to_terminal_s"]
                            leg["deadline_wall_s"] = round(dl, 1)
                        else:
                            dl, el = None, None
                        explicit = (term_text and "timed out" in term_text) or any(
                            "timed out" in txt and robot in txt for w, txt in detail
                            if end_w and w and abs(w - end_w) < 2.0)
                        leg["ended_by_deadline"] = bool(terminal == "FAILED" and (
                            explicit or (dl is not None and el is not None and el >= dl - 1.0)))
                    out.append(leg)
        return out

    def exec_check(self, leg: dict[str, Any], gts, frames, t_end: float) -> dict[str, Any]:
        """T3 for one motion leg: GT displacement, contacts, pin/stall tags (orthogonal fields)."""
        s = leg["start_rel"]
        if s is None:
            if leg["kind"] == "escort":
                return {"t3": "not_started", "tags": ["escort_not_admitted (no gate_admit line)"]}
            return {"t3": "U:no_leg_start"}
        # The window end uses the local anchor interpolation: the rubric's
        # single fit has residuals of up to ~2 s, a large part of a 13 s leg.
        e = leg["end_rel_local"] if leg["end_rel_local"] is not None else t_end
        rid = leg["robot"]
        idx = [i for i, (t, poses) in enumerate(gts) if s <= t <= e and rid in poses]
        if not idx:
            return {"t3": "U:no_gt_in_window"}
        x0, y0 = gts[idx[0]][1][rid][:2]
        disp = [math.hypot(gts[i][1][rid][0] - x0, gts[i][1][rid][1] - y0) for i in idx]
        moved = max(disp)
        final = disp[-1]
        best_s = (math.inf, None, None)
        best_r = (math.inf, None, None)
        contact_rows = defaultdict(list)
        for i in idx:
            f = frames[i]
            t = gts[i][0]
            ms = f.robot_min_static.get(rid)
            if ms and ms[0] < best_s[0]:
                best_s = (ms[0], ms[1], t)
            for (a, b), g in f.robot_gaps_near.items():
                if rid in (a, b):
                    other = b if a == rid else a
                    if g < best_r[0]:
                        best_r = (g, other, t)
                    if g <= CONTACT_M:
                        contact_rows[f"robot:{other}"].append(t)
            for (r2, box), g in f.static_gaps_near.items():
                if r2 == rid and g <= CONTACT_M:
                    contact_rows[f"box:{box}"].append(t)
            if best_r[0] == math.inf and f.robot_pair_min and rid in (f.robot_pair_min[1] or ()):
                pass
        dt = 0.1
        contacts = {k: [(round(a, 2), round(b, 2)) for a, b, _ in collapse_spans(v, 2 * dt + 1e-6)]
                    for k, v in contact_rows.items()}
        t_last = gts[idx[-1]][0]
        tail = [i for i in idx if gts[i][0] >= t_last - PIN_STILL_S]
        xf, yf = gts[idx[-1]][1][rid][:2]
        still = max(math.hypot(gts[i][1][rid][0] - xf, gts[i][1][rid][1] - yf) for i in tail)
        still_tail = (t_last - gts[tail[0]][0]) >= PIN_STILL_S - 0.2 and still < STALL_MOVE_M
        f_last = frames[idx[-1]]
        end_static = f_last.robot_min_static.get(rid)
        end_robot = min(((g, b if a == rid else a) for (a, b), g in f_last.robot_gaps_near.items()
                         if rid in (a, b)), default=(math.inf, None))
        tags = []
        if leg["m4_terminal"] == "COMPLETED":
            tags.append("completed")
        commanded = leg["commanded_m"]
        frac = moved / commanded if commanded else None
        if frac is not None and frac < EXEC_FRACTION:
            tags.append("not_executed(<50%)")
        pinned = None
        if still_tail and end_static and end_static[0] <= CONTACT_M:
            spans = contacts.get(f"box:{end_static[1]}", [])
            pin_from = spans[-1][0] if spans else None
            kind = "declared" if end_static[1] in self.declared else "undeclared"
            pinned = {"on": f"box:{end_static[1]}", "box_declared": kind == "declared",
                      "from_rel": pin_from, "until_rel": round(t_last, 2),
                      "duration_s": None if pin_from is None else round(t_last - pin_from, 1)}
            tags.append(f"pinned_on_{kind}_box:{end_static[1]}")
        elif still_tail and end_robot[0] <= CONTACT_M:
            spans = contacts.get(f"robot:{end_robot[1]}", [])
            pin_from = spans[-1][0] if spans else None
            pinned = {"on": f"robot:{end_robot[1]}", "from_rel": pin_from,
                      "until_rel": round(t_last, 2),
                      "duration_s": None if pin_from is None else round(t_last - pin_from, 1)}
            tags.append(f"pinned_on_robot:{end_robot[1]}")
        elif (still_tail and leg["m4_terminal"] != "COMPLETED"
              and (end_static is None or end_static[0] > NEAR_M) and end_robot[0] > NEAR_M):
            tags.append("stalled_clear(no robot or box within 0.05 m)")
        return {
            "t3": "computed",
            "gt_moved_max_m": round(moved, 3), "gt_moved_final_m": round(final, 3),
            "fraction_of_commanded": None if frac is None else round(frac, 3),
            "min_static_gap_m": None if best_s[1] is None else round(best_s[0], 4),
            "min_static_box": best_s[1],
            "min_static_box_declared": None if best_s[1] is None else best_s[1] in self.declared,
            "min_static_at_rel": None if best_s[2] is None else round(best_s[2], 2),
            "min_robot_gap_m": None if best_r[1] is None else round(best_r[0], 4),
            "min_robot_other": best_r[1],
            "min_robot_at_rel": None if best_r[2] is None else round(best_r[2], 2),
            "contacts_in_window": contacts, "still_last_10s": still_tail,
            "pinned": pinned, "tags": tags,
            "window_rel": [round(s, 2), round(e, 2)],
            "window_end_censored": leg["end_rel"] is None,
        }

    # contacts / latch / stale ---------------------------------------------

    def contacts_summary(self, frames, gts) -> dict[str, Any]:
        rec = self.T["recompute"].recompute_bundle(self.bundle)
        events = []
        for key in ("static_pairs", "robot_pairs"):
            for pair, summ in (rec.get(key) or {}).items():
                for ev in summ.get("events") or []:
                    events.append({"pair": pair, "pair_verdict": summ.get("verdict"),
                                   "category": summ.get("category"),
                                   "start_rel": self.gt_rel(ev["start_sim_s"]),
                                   "end_rel": self.gt_rel(ev["end_sim_s"]), **ev})
        sub = defaultdict(list)
        for f, (t, _) in zip(frames, gts, strict=True):
            for (rid, box), g in f.static_gaps_near.items():
                if g <= NEAR_M:
                    sub[f"{rid}|box:{box}"].append((t, g))
            for (a, b), g in f.robot_gaps_near.items():
                if g <= NEAR_M:
                    sub[f"{a}|{b}"].append((t, g))
        submargin = {}
        for k, rows in sub.items():
            spans = collapse_spans([t for t, _ in rows], 0.25)
            submargin[k] = [
                {"from_rel": round(a, 2), "to_rel": round(b, 2),
                 "min_gap_m": round(min(g for t, g in rows if a <= t <= b), 4),
                 "contact": min(g for t, g in rows if a <= t <= b) <= CONTACT_M}
                for a, b, _ in spans
            ]
        return {
            "recompute_summary_keys": sorted(rec.keys()),
            "recompute_verdicts": {"static": rec.get("static_verdict"),
                                   "robot_robot": rec.get("robot_robot_verdict")},
            "recompute_robot_min_static_gap": rec.get("robot_min_static_gap"),
            "recompute_min_robot_robot_gap": rec.get("min_robot_robot_gap"),
            "recompute_unmodelled_obstacles": rec.get("unmodelled_obstacles"),
            "recompute_events": events[:300],
            "spans_within_0.05m_rel": submargin,
            "declared_boxes": sorted(self.declared),
            "builder_boxes": [b.obstacle_id for b in self.boxes],
            "undeclared_builder_boxes": [b.obstacle_id for b in self.boxes
                                         if b.obstacle_id not in self.declared],
        }

    def latch(self) -> dict[str, Any]:
        spans = {}
        for (rid, reason), ws in self.m4["safety_stop"].items():
            sp = collapse_spans(ws, LATCH_SPAN_GAP_S)
            spans[f"{rid}|{reason}"] = [
                {"from_rel": self.wall_to_rel(a), "to_rel": self.wall_to_rel(b), "lines": n}
                for a, b, n in sp
            ]
        exempt = [{"rel": self.wall_to_rel(w), "pairs": pairs}
                  for w, pairs in self.m4["exempt"]]
        waiver = [{"rel": self.wall_to_rel(w), "event": kind.strip(), "text": text[:160]}
                  for w, kind, text in self.m4["waiver"]]
        return {"safety_stop_spans": spans, "exempt_changes": exempt, "waiver_events": waiver}

    def stale_spans(self) -> dict[str, list[dict[str, Any]]]:
        out = defaultdict(list)
        open_: dict[str, float] = {}
        last = None
        for row in self.scene:
            sc = row.get("scene") or {}
            st = sc.get("stamp")
            if st is None:
                continue
            last = st
            seen = set()
            for r in sc.get("robots") or []:
                seen.add(r["robot_id"])
                if r.get("status") == "STALE":
                    open_.setdefault(r["robot_id"], st)
                elif r["robot_id"] in open_:
                    a = open_.pop(r["robot_id"])
                    out[r["robot_id"]].append((a, st))
            for rid in list(open_):
                if rid not in seen:
                    out[rid].append((open_.pop(rid), st))
        for rid, a in open_.items():
            out[rid].append((a, last))
        return {rid: [{"from_rel": self.sim_to_rel(a), "to_rel": self.sim_to_rel(b),
                       "duration_s": round(b - a, 2), "ge_10s": b - a >= STALE_MIN_S}
                      for a, b in v] for rid, v in out.items()}

    # decisions ------------------------------------------------------------

    def decisions(self, analyses) -> list[dict[str, Any]]:
        by_rid = {a.request_id: a for a in analyses}
        out = []
        for a in self.artifacts:
            rid = a.get("request_id")
            d = a.get("decision") or None
            diag = a.get("diagnostics") or {}
            plan = a.get("plan") or {}
            live = a.get("dispatched_command")
            wh = a.get("dispatch_withheld")
            an = by_rid.get(rid)
            tags = list((live or {}).get("degradations") or [])
            pp = (d or {}).get("proposed_plan")
            g = {
                "G2_m3_default_with_plan": plan.get("provenance") == "m3_default" and bool(pp),
                "G3_plan_nulled_by_parser": any(
                    "proposed_plan" in str(x) for x in diag.get("decision_degradations") or []),
                "G4_role_change_tags": [t for t in tags if any(
                    k in t for k in ("node_handoff", "rear_exempt", "regrounded", "swap",
                                     "yield_robot="))]
                + ([f"yield_robot_grounded_from={a.get('yield_robot_grounded_from')}"]
                   if a.get("yield_robot_grounded_from") else []),
                "G6_verbatim_contradicted": plan.get("provenance") == "vlm_verbatim"
                and plan.get("dispatch_matches_plan") is False,
            }
            decided = set((d or {}).get("involved_robots") or [])
            dispatched = set(a.get("dispatched_robot_ids") or [])
            if live and d and decided and dispatched and decided - dispatched:
                g["G4_robots_dropped"] = sorted(decided - dispatched)
            out.append({
                "request_id": rid, "sim_s": a["scene"]["stamp"],
                "t_rel": self.sim_to_rel(a["scene"]["stamp"]),
                "analysis_class": an.analysis_class if an else None,
                "matched_conflict_index": an.matched_conflict if an else None,
                "parse_status": diag.get("parse_status"), "attempts": diag.get("attempts"),
                "refusal_category": diag.get("refusal_category"),
                "error_type": diag.get("error_type"),
                "terminal_stage": a.get("terminal_stage"), "failure_reason": a.get("failure_reason"),
                "decision_degradations": diag.get("decision_degradations"),
                "raw_text": a.get("raw_text"),
                "decision": d,
                "contract": contract_checks(d) if d else None,
                "plan": {k: plan.get(k) for k in (
                    "provenance", "edits", "rejection_reason", "plan_held", "plan_id",
                    "dispatch_matches_plan", "order_equivalent", "legs")} if plan else None,
                "grounding": {
                    "mode": a.get("grounding_mode"),
                    "yield_feasibility": a.get("grounding_yield_feasibility"),
                    "stage2_label": (a.get("stage2") or {}).get("grounded_label"),
                    "stage2_status": (a.get("stage2") or {}).get("status"),
                    "yield_refusal_reason": a.get("yield_refusal_reason"),
                    "yield_regrounded_reason": a.get("yield_regrounded_reason"),
                    "yield_robot_grounded_from": a.get("yield_robot_grounded_from"),
                    "degradations": tags,
                    "actions": [{"robot": x["robot_id"], "action": x["action"],
                                 "params": {k: v for k, v in (x.get("parameters") or {}).items()
                                            if k in ("backup_distance_m", "passer_robot_id",
                                                     "passer_escort_distance_m", "reason",
                                                     "retreat_choice", "crossing_order",
                                                     "fresh_latch_fast_fail", "waypoints",
                                                     "retreat_shield_hold")}}
                                for x in (live or {}).get("actions") or []],
                    "dispatched_robot_ids": a.get("dispatched_robot_ids"),
                    "withheld": wh,
                    "published": bool(live) and not wh,
                    "junction_phases": bool(a.get("junction_phases")),
                },
                "mechanical_flags": g,
            })
        return out

    # run ------------------------------------------------------------------

    def run(self) -> dict[str, Any]:
        gts = self.gt_series()
        frames = self.contact_frames()
        units, episodes, analyses = self.units(gts)
        decisions = self.decisions(analyses)
        legs = self.legs(gts, frames)
        fid = self.fidelity()
        fid_by = {r["request_id"]: r for r in fid["rows"]}
        stale = self.stale_spans()
        contacts = self.contacts_summary(frames, gts)
        latch = self.latch()
        nav2 = [{"robot": r, "rel": self.wall_to_rel(w), "wall": w, "text": t}
                for w, r, t in self.nav2]
        t1_out: dict[str, Any] = {}
        t2_out: dict[str, Any] = {}
        art_by = {a["request_id"]: a for a in self.artifacts}
        for u in units:
            if u["excluded"]:
                continue
            robots = set(u["robots"])
            t0_m1 = self.records.t0_m1 + u["t0_rel"]
            snaps = []
            if u["kind"] == "conflict":
                on_fu = [d for d in decisions if d["matched_conflict_index"] == u["conflict_index"]]
            else:
                on_fu = [d for d in decisions if d["analysis_class"] == "positive"
                         and robots & set((d["decision"] or {}).get("involved_robots") or [])
                         and d["t_rel"] is not None and d["t_rel"] >= u["t0_rel"]]
            u["analyses_on_fu"] = [d["request_id"] for d in on_fu]
            positives_in_stall = [
                d["request_id"] for d in decisions if d["analysis_class"] == "positive"
                and robots & set((d["decision"] or {}).get("involved_robots") or [])
                and d["t_rel"] is not None and u["t0_rel"] <= d["t_rel"] <= u["end_rel"]
            ]
            u["v1_input"] = {
                "a33_matched_positive_analyses": len(on_fu) if u["kind"] == "conflict" else None,
                "lone_stall_positive_naming_robot": positives_in_stall
                if u["kind"] == "lone_stall" else None,
            }
            snap0 = self.snapshot_at(t0_m1)
            snaps.append(("t0", snap0, t0_m1, None))
            for d in on_fu:
                art = art_by[d["request_id"]]
                snaps.append((d["request_id"], art["scene"], art["scene"]["stamp"], art))
            t1_rows, t2_rows = {}, {}
            for key, scene, t_m1, art in snaps:
                if scene is None:
                    t1_rows[key] = {"status": "U:no_snapshot"}
                    t2_rows[key] = {"status": "U:no_snapshot"}
                    continue
                recorded = art if art is not None and art.get("grounding_params_source") else None
                r = self.t1(scene, u["robots"], t_m1, recorded)
                if key == "t0":
                    r["fidelity"] = {k: ("episode_gate_pass" if fid["episode_usable"][k]
                                         else "U:T1_fidelity" if fid["rows"]
                                         else "unverifiable_in_bundle")
                                     for k in ("as_written", "plus_stage2_intents")}
                else:
                    fr = fid_by.get(key, {})
                    if fr.get("status") == "U:T1_no_record":
                        r["fidelity"] = {"as_written": "U:T1_no_record",
                                         "plus_stage2_intents": "U:T1_no_record"}
                    else:
                        r["fidelity"] = {
                            "as_written": "pass" if fr.get("as_written") == "reproduced"
                            else "U:T1_fidelity",
                            "plus_stage2_intents": "pass"
                            if fr.get("plus_stage2_intents") == "reproduced" else "U:T1_fidelity",
                        }
                r["snapshot_rel"] = self.sim_to_rel(t_m1 if key != "t0" else scene["stamp"])
                t1_rows[key] = r
                t2_rows[key] = self.t2(scene, u["robots"], t_m1)
                t2_rows[key]["snapshot_rel"] = r["snapshot_rel"]
            t1_out[u["fu"]] = t1_rows
            t2_out[u["fu"]] = t2_rows
            u["chain"] = chain_links(
                [l for l in legs if l["kind"] != "wait" or True], robots, u["t0_rel"])
            u["chain_start_rel"] = min(
                (l["dispatch_rel"] for l in legs if l["leg_id"] in u["chain"]["rubric"]
                 and l["dispatch_rel"] is not None), default=None)
            u["x3_gt"] = self.x3_gt(u, gts)
            u["gt_contacts"] = {
                k: v for k, v in contacts["spans_within_0.05m_rel"].items()
                if set(k.split("|")[0:1]) & robots or (
                    not k.split("|")[1].startswith("box:") and set(k.split("|")) & robots)
            }
            u["x2_input"] = self.x2_input(u, gts, legs, latch)
            u["timeline"] = self.timeline(u, decisions, legs, stale, contacts, latch, nav2)
            u["evidence_gate"] = {
                "t0_snapshot": snap0 is not None,
                "decision_artifacts": bool(self.artifacts),
                "m4_log": self.m4["present"],
            }
        return {
            "label": self.args.label, "bundle": str(self.bundle), "stratum": self.args.stratum,
            "arm": self.args.arm, "seed": self.records.seed,
            "run_id": self.stream.get("run_id"), "session_id": self.stream.get("session_id"),
            "provenance": self.T["provenance"],
            "censor": {"reason_a33": self.records.censor_reason,
                       "t_end_rel": round(self.records.t_end_rel, 3),
                       "cut_short_stop_rule": self.records.censor_reason == "stop_flag"},
            "clock": {
                "rel_s": "GT sim-s minus robot_1 release on the GT clock (A33(0)); "
                "= M1/ROS sim-s minus t0_m1",
                "t0_m1_sim_s": self.records.t0_m1, "gt_offset_s": self.offset,
                "wall_to_sim_fit_m4": self.fit,
                "wall_mapping": "linear fit over m4.log sim_t= lines (rubric 7.1)"
                if self.fit else "U:no_m4_clock_anchor (m4.log has fewer than 2 sim_t= lines)",
            },
            "units": units, "decisions": decisions, "legs": legs, "fidelity": fid,
            "t1": t1_out, "t2": t2_out, "contacts": contacts, "stale_spans": stale,
            "latch": latch, "nav2": nav2,
            "m5_lines": [{"rel": self.wall_to_rel(w), "kind": k, "text": t} for w, k, t in self.m5
                         if k != "command "][:400],
        }

    def timeline(self, u, decisions, legs, stale, contacts, latch, nav2) -> list[dict[str, Any]]:
        """Rubric 7.1 events touching the FU's robots, from 60 s before t0 (or the chain start) to censoring, in time order."""
        robots = set(u["robots"])
        start = u["t0_rel"] - STALL_WINDOW_S
        if u.get("chain_start_rel") is not None:
            start = min(start, u["chain_start_rel"])
        ev: list[dict[str, Any]] = []
        for d in decisions:
            dec = d.get("decision") or {}
            g = d.get("grounding") or {}
            touched = set(dec.get("involved_robots") or []) | {
                a["robot"] for a in g.get("actions") or []}
            if not (touched & robots or d["request_id"] in u.get("analyses_on_fu", [])):
                continue
            ev.append({"rel": d["t_rel"], "type": "analysis", "ref": d["request_id"],
                       "summary": f"{d.get('analysis_class')} strategy={dec.get('strategy')} "
                       f"involved={dec.get('involved_robots')} yield={dec.get('yield_robot')}"})
            if g.get("actions"):
                ev.append({"rel": d["t_rel"], "type": "withheld" if g.get("withheld") else
                           "dispatched", "ref": d["request_id"],
                           "summary": ", ".join(f"{a['robot']}:{a['action']}"
                                                for a in g["actions"])
                           + (f" withheld={g['withheld'].get('reason')}" if g.get("withheld")
                              else "")})
        for leg in legs:
            if leg["robot"] not in robots or leg["kind"] == "wait":
                continue
            if leg.get("start_rel") is not None:
                ev.append({"rel": leg["start_rel"], "type": "m4_leg_start", "ref": leg["leg_id"],
                           "summary": f"{leg['kind']} commanded={leg.get('commanded_m')}"})
            if leg.get("end_rel") is not None:
                ev.append({"rel": leg["end_rel"], "type": "m4_terminal", "ref": leg["leg_id"],
                           "summary": f"{leg.get('m4_terminal')} {leg.get('m4_terminal_text') or ''}"
                           f" moved={leg.get('gt_moved_max_m')} tags={leg.get('tags')} "
                           f"deadline={leg.get('ended_by_deadline')}"})
        for rid, spans in stale.items():
            if rid in robots:
                for sp in spans:
                    ev.append({"rel": sp["from_rel"], "type": "m1_stale", "ref": rid,
                               "summary": f"STALE {sp['duration_s']} s"})
        for key, spans in contacts["spans_within_0.05m_rel"].items():
            a, b = key.split("|")
            if a in robots or (not b.startswith("box:") and b in robots):
                for sp in spans:
                    ev.append({"rel": sp["from_rel"], "type": "gt_contact" if sp["contact"]
                               else "gt_submargin", "ref": key,
                               "summary": f"to {sp['to_rel']} min gap {sp['min_gap_m']} m"})
        for x in latch["exempt_changes"]:
            if x["rel"] is not None and any(r in x["pairs"] for r in robots):
                ev.append({"rel": x["rel"], "type": "exempt_change", "ref": "-",
                           "summary": x["pairs"]})
        for key, spans in latch["safety_stop_spans"].items():
            if key.split("|")[0] in robots:
                for sp in spans:
                    ev.append({"rel": sp["from_rel"], "type": "safety_stop_span",
                               "ref": key.split("|")[0],
                               "summary": f"to {sp['to_rel']} ({sp['lines']} lines)"})
        for n in nav2:
            if n["robot"] in robots:
                ev.append({"rel": n["rel"], "type": "nav2", "ref": n["robot"],
                           "summary": n["text"][:120]})
        keep = [e for e in ev if e["rel"] is None or e["rel"] >= start]
        return sorted(keep, key=lambda e: (math.inf if e["rel"] is None else e["rel"], e["type"]))

    def x3_gt(self, u: dict[str, Any], gts) -> list[dict[str, Any]]:
        """X3 GT input: FU pairs within min_distance_m and both stopped from some time to censoring."""
        out = []
        robots = sorted(u["robots"], key=lambda r: (len(r), r))
        for a, b in itertools.combinations(robots, 2):
            since = None
            for t, poses in reversed(gts):
                if a not in poses or b not in poses:
                    break
                pa, pb = poses[a], poses[b]
                close = math.dist(pa[:2], pb[:2]) < MIN_DISTANCE_M
                stopped = pa[3] < STOPPED_MPS and pb[3] < STOPPED_MPS
                if not (close and stopped):
                    break
                since = t
            if since is not None:
                out.append({"pair": [a, b], "close_and_stopped_from_rel": round(since, 2),
                            "until_rel": round(gts[-1][0], 2)})
        return out

    def x2_input(self, u, gts, legs, latch) -> list[dict[str, Any]]:
        """X2 input: stationary >= 60 s while no M4 command leg covers the robot (inferred active Nav2 goal).

        Each run also states how much of it the robot's own safety-stop spans
        cover (a latched robot has its Nav2 goal cancelled by M4's safety
        monitor, so such a run is not under an active goal).
        """
        out = []
        stops = defaultdict(list)
        for key, spans in latch["safety_stop_spans"].items():
            for sp in spans:
                if sp["from_rel"] is not None and sp["to_rel"] is not None:
                    stops[key.split("|")[0]].append((sp["from_rel"], sp["to_rel"]))
        for rid in u["robots"]:
            busy = [(l["start_rel"], l["end_rel"] if l["end_rel"] is not None else math.inf)
                    for l in legs if l["robot"] == rid and l["start_rel"] is not None]
            run_start, anchor = None, None
            for t, poses in gts:
                if rid not in poses:
                    continue
                p = poses[rid][:2]
                covered = any(a <= t <= b for a, b in busy)
                m1 = self.records.t0_m1 + t
                ph = task_phase_at(self.task_events, rid, m1, self.dwell_s)["phase"]
                ok = not covered and ph == "traveling"
                if ok and anchor is not None and math.dist(p, anchor) < STALL_MOVE_M:
                    continue
                if run_start is not None and t - run_start >= STALL_WINDOW_S:
                    out.append(self._x2_row(rid, run_start, t, stops, False))
                run_start, anchor = (t, p) if ok else (None, None)
            if run_start is not None and gts[-1][0] - run_start >= STALL_WINDOW_S:
                out.append(self._x2_row(rid, run_start, gts[-1][0], stops, True))
        return out

    @staticmethod
    def _x2_row(rid, a, b, stops, to_censor) -> dict[str, Any]:
        cover = sum(max(0.0, min(b, y) - max(a, x)) for x, y in stops.get(rid, []))
        return {"robot": rid, "from_rel": round(a, 2), "to_rel": round(b, 2),
                "duration_s": round(b - a, 1), "to_censor": to_censor,
                "safety_stop_cover_fraction": round(cover / (b - a), 3) if b > a else None}


def _diff_summary(out: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    so, sl = strip_actions(out), strip_actions(live)
    res: dict[str, Any] = {}
    if [a["robot_id"] for a in so] != [a["robot_id"] for a in sl]:
        res["robots"] = [[a["robot_id"] for a in so], [a["robot_id"] for a in sl]]
    for x, y in zip(so, sl):
        if x != y:
            keys = sorted(set(x["parameters"]) | set(y["parameters"]))
            res.setdefault("params", []).append({
                "robot": y["robot_id"], "action": [x["action"], y["action"]],
                "keys": [k for k in keys if x["parameters"].get(k) != y["parameters"].get(k)][:8],
            })
    do, dl = out.get("degradations") or [], live.get("degradations") or []
    if do != dl:
        res["degradations_only_replay"] = [t for t in do if t not in dl]
        res["degradations_only_live"] = [t for t in dl if t not in do]
    return res


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def _strip_private(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_private(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_strip_private(x) for x in obj]
    return obj


def md_sheet(sheet: dict[str, Any], title: str, rater: bool) -> str:
    """Readable Markdown of one evidence sheet."""
    L = [f"# Evidence Sheet {title}", ""]
    c = sheet.get("censor", {})
    L.append(f"- Censoring: t_end {c.get('t_end_rel')} rel-s"
             + (f", reason {c.get('reason_a33')}" if "reason_a33" in c else ""))
    clk = sheet.get("clock", {})
    if clk:
        L.append(f"- Clock: all times rel-s ({clk.get('rel_s')}); wall mapping: "
                 f"{clk.get('wall_mapping')}"
                 + (f", fit n={clk['wall_to_sim_fit_m4']['n']} max residual "
                    f"{clk['wall_to_sim_fit_m4']['max_resid_s']} s"
                    if clk.get("wall_to_sim_fit_m4") else ""))
    if not rater and "outcome" in sheet:
        L.append(f"- Outcome fields (frozen, copied): {json.dumps(sheet['outcome'])}")
    L += ["", "## Failure Units", "",
          "| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |",
          "|---|---|---|---|---|---|---|---|"]
    for u in sheet.get("units", []):
        L.append(f"| {u['fu']} | {u['kind']} | {', '.join(u['robots'])} | {u['t0_rel']} | "
                 f"{u['end_rel']} | {u['excluded']} | "
                 f"{', '.join((u.get('chain') or {}).get('rubric', [])) or '-'} | "
                 f"{'; '.join(u.get('flags') or []) or '-'} |")
    for u in sheet.get("units", []):
        if u.get("excluded"):
            continue
        L += ["", f"### {u['fu']}", ""]
        if u.get("pairs"):
            L.append(f"- Pairs: {u['pairs']}")
        if "evidence_gate" in u:
            L.append(f"- Evidence gate inputs: {u['evidence_gate']}")
        if u.get("chain_start_rel") is not None:
            L.append(f"- Chain start (earliest qualifying dispatch): {u['chain_start_rel']} rel-s")
        if "v1_input" in u:
            L.append(f"- V1 input: {u['v1_input']}")
        if u.get("x3_gt"):
            L.append(f"- X3 GT input (pair < 0.45 m and both stopped to censoring): {u['x3_gt']}")
        if u.get("x2_input"):
            L.append(f"- X2 input (stationary >= 60 s, no M4 leg, task traveling): {u['x2_input']}")
        gc = {k: v for k, v in (u.get("gt_contacts") or {}).items()
              if any(s["contact"] for s in v)}
        if gc:
            L.append(f"- GT contacts (gap <= 0.005 m) of FU robots: "
                     + "; ".join(f"{k}: " + ", ".join(f"[{s['from_rel']}, {s['to_rel']}] "
                                                     f"{s['min_gap_m']}" for s in v if s["contact"])
                                 for k, v in gc.items()))
        if u.get("timeline"):
            L += ["", "Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):",
                  "", "| rel-s | Event | Ref | Detail |", "|---|---|---|---|"]
            L += [f"| {e['rel']} | {e['type']} | {e['ref']} | {str(e['summary'])[:160]} |"
                  for e in u["timeline"]]
        t1 = (sheet.get("t1") or {}).get(u["fu"], {})
        t2 = (sheet.get("t2") or {}).get(u["fu"], {})
        if t1:
            L += ["", "| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written "
                  "| T1 +intents | T1 all guards on | T2 | T2 shortest |",
                  "|---|---|---|---|---|---|---|---|"]
            for key, r in t1.items():
                v = r.get("variants") or {}
                cell = lambda n: (f"{v[n]['n_motion']}/{v[n]['n_h']}" if n in v  # noqa: E731
                                  else r.get("status", "-"))
                t2r = t2.get(key, {})
                fid = r.get("fidelity") or {}
                L.append(f"| {key} | {r.get('snapshot_rel', '-')} | "
                         f"{fid.get('as_written', '-')} / {fid.get('plus_stage2_intents', '-')} | "
                         f"{cell('as_written')} | {cell('plus_intents')} | {cell('all_guards_on')} | "
                         f"{t2r.get('result', t2r.get('status', '-'))} | {t2r.get('shortest')} |")
    L += ["", "## Decisions", ""]
    for d in sheet.get("decisions", []):
        dec = d.get("decision") or {}
        g = d.get("grounding") or {}
        L.append(f"### {d['request_id']} at {d['t_rel']} rel-s ({d.get('analysis_class')})")
        L.append("")
        L.append(f"- Parse: {d.get('parse_status')}, attempts {d.get('attempts')}, refusal "
                 f"{d.get('refusal_category')}, error {d.get('error_type')}, decision degradations "
                 f"{d.get('decision_degradations')}, terminal stage {d.get('terminal_stage')}")
        if dec:
            L.append(f"- Decision: strategy {dec.get('strategy')}, involved "
                     f"{dec.get('involved_robots')}, yield_robot {dec.get('yield_robot')}, "
                     f"crossing_order {dec.get('crossing_order')}, type {dec.get('type')}")
            L.append(f"- Plan legs (model): {dec.get('proposed_plan')}")
            L.append(f"- Justification: {dec.get('justification')}")
            L.append(f"- Contract C1-C3: {d.get('contract')}")
        if d.get("plan"):
            p = d["plan"]
            L.append(f"- Plan verifier: provenance {p.get('provenance')}, edits {p.get('edits')}, "
                     f"rejection {p.get('rejection_reason')}, held {p.get('plan_held')}, "
                     f"dispatch_matches_plan {p.get('dispatch_matches_plan')}")
        L.append(f"- Grounding: published {g.get('published')}, withheld {g.get('withheld')}, "
                 f"yield refusal {g.get('yield_refusal_reason')}, regrounded "
                 f"{g.get('yield_regrounded_reason')}, from {g.get('yield_robot_grounded_from')}")
        L.append(f"- Degradation tags: {g.get('degradations')}")
        L.append(f"- Actions: {[(a['robot'], a['action'], a['params']) for a in g.get('actions') or []]}")
        L.append(f"- Mechanical flags: {d.get('mechanical_flags')}")
        L.append("")
    L += ["## Dispatched Legs (T3)", "",
          "| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | "
          "Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for leg in sheet.get("legs", []):
        if leg["kind"] == "wait":
            continue
        L.append(
            f"| {leg['leg_id']} | {leg['kind']} | {leg.get('commanded_m')} | "
            f"{leg.get('dispatch_rel')} | {leg.get('start_rel')} | {leg.get('end_rel')} | "
            f"{leg.get('m4_terminal')} | {leg.get('gt_moved_max_m')} | "
            f"{leg.get('fraction_of_commanded')} | {leg.get('min_static_gap_m')} "
            f"({leg.get('min_static_box')}) | {leg.get('min_robot_gap_m')} "
            f"({leg.get('min_robot_other')}) | {'; '.join(leg.get('tags') or []) or '-'} | "
            f"{leg.get('ended_by_deadline')} |")
    stale = {k: v for k, v in (sheet.get("stale_spans") or {}).items() if any(
        s["ge_10s"] for s in v)}
    L += ["", "## Perception STALE Spans of 10 s or More", "",
          json.dumps(stale) if stale else "none"]
    L += ["", "## Nav2 Abort Lines", ""]
    L += [f"- {n['robot']} {n['rel']} rel-s: {n['text']}" for n in sheet.get("nav2", [])] or ["none"]
    lat = sheet.get("latch") or {}
    L += ["", "## Safety Latch", "",
          f"- Exempt changes: {lat.get('exempt_changes')}",
          f"- Safety-stop spans: "
          + "; ".join(f"{k}: {len(v)} spans" for k, v in (lat.get('safety_stop_spans') or {}).items())]
    return "\n".join(L) + "\n"


def cmd_render(out: Path) -> None:
    """Rater sheets, key, full Markdown, interception input, coverage, leak check."""
    full_dir = out / "full"
    labels = sorted(p.name for p in full_dir.iterdir() if (p / "evidence.json").is_file())
    key_path = out / "key" / "key.json"
    key = json.loads(key_path.read_text()) if key_path.is_file() else {}
    outcomes_path = out / "inputs" / "outcomes.json"
    outcomes = json.loads(outcomes_path.read_text()) if outcomes_path.is_file() else {}
    episodes = json.loads((out / "inputs" / "episodes.json").read_text())
    stall = {}
    stall_path = out / "replay" / "stall_abort.json"
    if stall_path.is_file():
        stall = json.loads(stall_path.read_text())
    used = {v for e in key.values() for v in (e.get("events_id"), e.get("gt_id"))}

    def new_id(prefix: str) -> str:
        while True:
            s = f"{prefix}-{secrets.token_hex(3)}"
            if s not in used:
                used.add(s)
                return s

    leak_literals = []
    for e in episodes:
        leak_literals += [e["label"], Path(e["bundle"]).name]
    for lab in labels:
        sheet = json.loads((full_dir / lab / "evidence.json").read_text())
        leak_literals += [str(sheet.get("seed") or ""), str(sheet.get("run_id") or ""),
                          str(sheet.get("session_id") or "")]
    coverage = []
    inter_rows = []
    leaks = {}
    for lab in labels:
        sheet = json.loads((full_dir / lab / "evidence.json").read_text())
        if lab not in key:
            key[lab] = {"events_id": new_id("EV"), "gt_id": new_id("GT"),
                        "bundle": sheet["bundle"], "stratum": sheet["stratum"],
                        "arm": sheet["arm"]}
        ids = key[lab]
        did = {d["request_id"]: f"D{i + 1}" for i, d in enumerate(sheet["decisions"])}
        key[lab]["decision_ids"] = {v: k for k, v in did.items()}
        sheet["outcome"] = outcomes.get(lab)
        (full_dir / lab / "sheet.md").write_text(md_sheet(_strip_private(sheet), lab, rater=False))
        rv = _strip_private(rater_view(sheet, did))
        gv = _strip_private(gt_view(sheet))
        for kind, view, oid in (("rater", rv, ids["events_id"]), ("rater_gt", gv, ids["gt_id"])):
            d = out / kind / oid
            d.mkdir(parents=True, exist_ok=True)
            text = json.dumps(view, indent=1, sort_keys=True)
            (d / "sheet.json").write_text(text)
            md = md_sheet(view, oid, rater=True)
            (d / "sheet.md").write_text(md)
            hits = leak_hits(text + md, [x for x in leak_literals if len(x) >= 4])
            leaks[oid] = hits
        cov = coverage_row(sheet)
        coverage.append({"label": lab, **cov})
        inter_rows += interception_rows(sheet, out, stall)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(json.dumps(key, indent=1, sort_keys=True))
    inter = out / "interception"
    inter.mkdir(parents=True, exist_ok=True)
    (inter / "legs.json").write_text(json.dumps(inter_rows, indent=1))
    cols = ["label", "leg_id", "kind", "commanded_m", "guard_verdict", "guard_repro",
            "m4_terminal", "gt_moved_max_m", "min_static_gap_m", "min_static_box",
            "contact", "pinned_on", "pinned_duration_s", "ended_by_deadline", "tags",
            "fu_rubric_window", "fu_end_window", "stall_abort"]
    lines = ["\t".join(cols)] + ["\t".join(str(r.get(c, "")) for c in cols) for r in inter_rows]
    (inter / "legs.tsv").write_text("\n".join(lines) + "\n")
    (out / "coverage.json").write_text(json.dumps(coverage, indent=1))
    (out / "leak_check.json").write_text(json.dumps(leaks, indent=1, sort_keys=True))
    n_hits = sum(len(v) for v in leaks.values())
    print(f"rendered {len(labels)} episodes; interception rows {len(inter_rows)}; leak hits {n_hits}")


def coverage_row(sheet: dict[str, Any]) -> dict[str, Any]:
    fid = sheet["fidelity"]
    units = [u for u in sheet["units"] if not u["excluded"]]
    t1_status = []
    for fu, rows in sheet["t1"].items():
        for key, r in rows.items():
            t1_status.append((r.get("fidelity") or {}).get("as_written") or r.get("status"))
    legs = [l for l in sheet["legs"] if l["kind"] in ("backup", "reverse", "escort")]
    return {
        "stratum": sheet["stratum"], "arm": sheet["arm"],
        "censor": sheet["censor"]["reason_a33"],
        "n_fu": len(units), "n_excluded_units": len(sheet["units"]) - len(units),
        "n_decisions": len(sheet["decisions"]),
        "fidelity_rates": fid["rates"], "episode_t1_usable": fid["episode_usable"],
        "t1_snapshot_status": dict(sorted({s: t1_status.count(s) for s in set(t1_status)}.items(),
                                          key=lambda kv: str(kv[0]))),
        "t0_snapshot_missing": sum(1 for u in units if not u["evidence_gate"]["t0_snapshot"]),
        "m4_log": bool(units and units[0]["evidence_gate"]["m4_log"]),
        "wall_fit": sheet["clock"]["wall_to_sim_fit_m4"] is not None,
        "n_motion_legs": len(legs),
        "legs_t3_unusable": sum(1 for l in legs if str(l.get("t3", "")).startswith("U:")),
        "legs_end_censored": sum(1 for l in legs if l.get("window_end_censored")),
        "contact_recompute": bool(sheet["contacts"].get("recompute_summary_keys")),
    }


def _guard_tables(out: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    table: dict[tuple[str, str, str], dict[str, str]] = {}
    for name in ("escort", "reverse"):
        path = out / "replay" / f"{name}_replay.tsv"
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            f = line.split("\t")
            if len(f) < 6 or "skipped" in line:
                continue
            if name == "reverse":
                table[(f[0], f[1], f[2])] = {"verdict": f[6], "repro": f[5], "leg": f[4],
                                              "physical": f[8] if len(f) > 8 else ""}
            else:
                passer = re.match(r"(robot_\d+)", f[5])
                if f[2] != "dispatched" or not passer:
                    continue
                table[(f[0], f[1], passer.group(1))] = {
                    "verdict": f[9], "repro": f[8], "leg": f"own:{f[6]} kit:{f[7]}"}
    return table


def interception_rows(sheet: dict[str, Any], out: Path, stall: dict[str, Any]) -> list[dict[str, Any]]:
    guards = _guard_tables(out)
    bname = Path(sheet["bundle"]).name
    rows = []
    units = [u for u in sheet["units"] if not u["excluded"]]
    for leg in sheet["legs"]:
        if leg["kind"] not in ("escort", "reverse"):
            continue
        g = guards.get((bname, leg["request_id"][:8], leg["robot"]), {})
        contact = any(k.startswith("box:") for k in (leg.get("contacts_in_window") or {}))
        rows.append({
            "label": sheet["label"], "stratum": sheet["stratum"], "arm": sheet["arm"],
            "leg_id": leg["leg_id"], "kind": leg["kind"], "commanded_m": leg.get("commanded_m"),
            "guard_verdict": g.get("verdict", "not in replay output"),
            "guard_repro": g.get("repro", ""), "guard_live_leg_check": g.get("leg", ""),
            "m4_terminal": leg.get("m4_terminal"), "gt_moved_max_m": leg.get("gt_moved_max_m"),
            "min_static_gap_m": leg.get("min_static_gap_m"),
            "min_static_box": leg.get("min_static_box"),
            "contact": contact,
            "pinned_on": (leg.get("pinned") or {}).get("on"),
            "pinned_duration_s": (leg.get("pinned") or {}).get("duration_s"),
            "ended_by_deadline": leg.get("ended_by_deadline"), "tags": leg.get("tags"),
            "fu_rubric_window": [u["fu"] for u in units if leg["leg_id"] in u["chain"]["rubric"]],
            "fu_end_window": [u["fu"] for u in units if leg["leg_id"] in u["chain"]["end_window"]],
            "stall_abort": stall.get(f"{bname}|{leg['request_id'][:8]}|{leg['robot']}|{leg['kind']}",
                                     ""),
        })
    return rows


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def cmd_episode(args: argparse.Namespace) -> None:
    out = Path(args.out)
    bundle = Path(args.bundle).resolve()
    if str(out.resolve()).startswith(str(bundle)) or "/data/logs/" in str(out.resolve()):
        raise SystemExit("output must lie outside every bundle and data/logs tree")
    trees = load_trees()
    ep = Episode(trees, bundle, args)
    sheet = ep.run()
    d = out / "full" / args.label
    d.mkdir(parents=True, exist_ok=True)
    dump = out / "dumps" / args.label
    dump.mkdir(parents=True, exist_ok=True)
    (dump / "t1_rows.json").write_text(json.dumps(
        {fu: {k: {v: r.get("variants", {}).get(v, {}).get("_rows") for v in
                  ("as_written", "plus_intents", "all_guards_on")} for k, r in rows.items()}
         for fu, rows in sheet["t1"].items()}))
    (d / "evidence.json").write_text(json.dumps(_strip_private(sheet), indent=1, default=str))
    units = [u for u in sheet["units"] if not u["excluded"]]
    print(f"{args.label}: units {len(units)} (+{len(sheet['units']) - len(units)} excluded), "
          f"decisions {len(sheet['decisions'])}, legs {len(sheet['legs'])}, "
          f"fidelity {sheet['fidelity']['rates']}")


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("episode")
    e.add_argument("--bundle", required=True)
    e.add_argument("--label", required=True)
    e.add_argument("--stratum", required=True)
    e.add_argument("--arm", required=True)
    e.add_argument("--params-from", default=None)
    e.add_argument("--out", required=True)
    r = sub.add_parser("render")
    r.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "episode":
        cmd_episode(args)
    else:
        cmd_render(Path(args.out))


if __name__ == "__main__":
    main()

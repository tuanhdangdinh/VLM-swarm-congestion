"""Ground-truth precedent check for the IB10 recede order.

Question: in recorded four-robot IB10 episodes that dispatched `junction_clear`, did the
rank-1 (shallower-pocket, chi order second) robot ever physically start backing out
before the rank-0 robot, and how close did robots get in episodes of each executed order?

Definitions (all computed from episode bundle files, read-only):
  * t0: first GT sample with any robot above 0.03 m/s (same rule as the frozen scorer,
    `scripts/t2b_forced_order.py`), so numbers match `score_ibs.py`.
  * distance: centre-to-centre from GT x/y over all robot pairs (same as
    `score_ibs.py::gt_min_pairwise`), never the `robot_robot_contacts` field.
  * recede window: from the first recede-phase dispatch to the first dispatch of the
    cross phase (or the last GT sample when no cross phase was dispatched).
  * wall-to-sim time: M5/M4 log lines carry ROS wall-clock epochs, GT carries sim time.
    The map is built from `m5_scene.jsonl` (monotonic `t` against scene sim stamp),
    anchored by the "starting analysis request=<id>" log line of the junction_clear
    request against that request's snapshot stamp.
  * start of receding for a robot: first GT sample at or after the reference time where
    its distance from the centre (0, 0) exceeds its distance at the reference time by
    more than START_THRESHOLD_M (0.05 m). Reference time is the first recede dispatch
    (common reference, used for "who moved first") and also the robot's own recede
    dispatch (own reference).
  * phases: from the artifact's `junction_phases` when present, else recovered from the
    `<request_id>-junction-{recede-<robot>,cross,release}` command ids in m4.log/m5.log.
  * overlap: second receder's own-ref start earlier than the first receder's last moving
    GT sample (> 0.03 m/s) before the second recede dispatch; no tolerance.
  * arrival / resolved: within 0.35 m of goal and never beyond 0.5 m afterwards, all four.

Usage:
    python ib10_recede_order_precedent.py --out OUT.json \
        --per-analysis per_analysis.jsonl [--exclude NAME ...] ROOT [ROOT ...]
Each ROOT is either a directory of bundles or a single bundle (has `decisions/`).
Directories starting with `_backup_` are ignored.
"""

from __future__ import annotations

import argparse
import bisect
import itertools
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any

START_THRESHOLD_M = 0.05
DEPARTURE_SPEED_MPS = 0.03
ARRIVAL_TOLERANCE_M = 0.35
ARRIVAL_STAY_M = 0.5

M5_DISPATCH_RE = re.compile(
    r"\[(\d+\.\d+)\] \[orchestrator_node\]: dispatch request=(\S+) command=(\S+) robot=(\S+)"
)
M5_START_RE = re.compile(r"\[(\d+\.\d+)\] \[orchestrator_node\]: starting analysis request=(\S+)")
M5_RESOLVED_RE = re.compile(
    r"\[(\d+\.\d+)\] \[orchestrator_node\]: command (\S+) resolved status=(\S+)"
)
M4_RECV_RE = re.compile(
    r"\[(\d+\.\d+)\] \[command_bus_node\]: command received command=(\S+) robot=(\S+) action=(\S+)"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts, skipping blank lines."""
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def find_bundles(roots: list[Path], exclude: set[str]) -> list[Path]:
    """Expand root arguments into episode bundle directories."""
    out: list[Path] = []
    for root in roots:
        if (root / "decisions").is_dir():
            out.append(root)
            continue
        for child in sorted(root.iterdir()):
            if (
                child.is_dir()
                and not child.name.startswith("_backup_")
                and child.name not in exclude
                and (child / "decisions").is_dir()
            ):
                out.append(child)
    return [b for b in out if b.name not in exclude]


def load_gt(bundle: Path) -> list[dict[str, Any]]:
    """Load GT rows (sorted by sim time); empty list when GT is missing."""
    path = bundle / "gt" / "ground_truth.jsonl"
    if not path.is_file():
        return []
    return sorted(read_jsonl(path), key=lambda r: r["sim_time_sec"])


def gt_t0(rows: list[dict[str, Any]]) -> float | None:
    """First sample time with any robot faster than DEPARTURE_SPEED_MPS."""
    for row in rows:
        if any(r["speed_mps"] > DEPARTURE_SPEED_MPS for r in row["robots"].values()):
            return row["sim_time_sec"]
    return None


def arrivals(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    """Per-robot arrival time (frozen-scorer rule: within 0.35 m, never beyond 0.5 m after)."""
    out: dict[str, float | None] = {}
    for rid in sorted(rows[0]["robots"]):
        series = [
            (r["sim_time_sec"], r["robots"][rid]["distance_to_goal_m"])
            for r in rows
            if rid in r["robots"]
        ]
        out[rid] = None
        for i, (t, d) in enumerate(series):
            if d <= ARRIVAL_TOLERANCE_M and all(
                later <= ARRIVAL_STAY_M for _t, later in series[i:]
            ):
                out[rid] = t
                break
    return out


def min_pairwise(rows: list[dict[str, Any]], lo: float, hi: float) -> dict[str, Any]:
    """Minimum centre-to-centre distance over all pairs for samples with lo <= t <= hi."""
    best: dict[str, Any] = {"min_m": None, "t": None, "pair": None}
    for row in rows:
        t = row["sim_time_sec"]
        if t < lo or t > hi:
            continue
        robots = row["robots"]
        for a, b in itertools.combinations(sorted(robots), 2):
            d = math.hypot(robots[a]["x"] - robots[b]["x"], robots[a]["y"] - robots[b]["y"])
            if best["min_m"] is None or d < best["min_m"]:
                best = {"min_m": round(d, 4), "t": t, "pair": f"{a}+{b}"}
    return best


def contacts_in(rows: list[dict[str, Any]], lo: float, hi: float) -> dict[str, Any]:
    """Count GT samples in [lo, hi] listing robot_robot_contacts and collect distinct entries."""
    n = 0
    missing = sum(1 for row in rows if "robot_robot_contacts" not in row)
    seen: list[str] = []
    first_t = None
    for row in rows:
        if lo <= row["sim_time_sec"] <= hi and row.get("robot_robot_contacts"):
            n += 1
            first_t = row["sim_time_sec"] if first_t is None else first_t
            for c in row["robot_robot_contacts"]:
                s = json.dumps(c, sort_keys=True)
                if s not in seen and len(seen) < 6:
                    seen.append(s)
    return {
        "samples_with_contacts": n,
        "first_t": first_t,
        "examples": seen,
        "gt_rows_missing_contacts_key": missing,
        "gt_rows_total": len(rows),
    }


class TimeMap:
    """Maps ROS wall-clock epochs to sim time using m5_scene.jsonl and one anchor."""

    def __init__(
        self, bundle: Path, request_id: str, anchor_stamp: float, m5_lines: list[str]
    ) -> None:
        self.ok = False
        scene = bundle / "m5_scene.jsonl"
        if not scene.is_file():
            return
        recs = [
            (d["t"], d["scene"]["stamp"])
            for d in read_jsonl(scene)
            if isinstance(d.get("scene"), dict) and d["scene"].get("stamp") is not None
        ]
        anchor_epoch = None
        for line in m5_lines:
            m = M5_START_RE.search(line)
            if m and m.group(2) == request_id:
                anchor_epoch = float(m.group(1))
                break
        if not recs or anchor_epoch is None:
            return
        self.t = [r[0] for r in recs]
        self.s = [r[1] for r in recs]
        anchor_t = min(recs, key=lambda r: abs(r[1] - anchor_stamp))[0]
        self.offset = anchor_epoch - anchor_t
        self.ok = True

    def sim(self, epoch: float) -> float:
        """Interpolate sim time at a wall epoch (clamped at the ends)."""
        t = epoch - self.offset
        i = bisect.bisect_left(self.t, t)
        if i <= 0:
            return self.s[0]
        if i >= len(self.t):
            return self.s[-1]
        t0, t1, s0, s1 = self.t[i - 1], self.t[i], self.s[i - 1], self.s[i]
        return s0 if t1 == t0 else s0 + (s1 - s0) * (t - t0) / (t1 - t0)


def radial_start(
    rows: list[dict[str, Any]], rid: str, ref_t: float, threshold: float
) -> dict[str, Any]:
    """First time at/after ref_t that robot rid is more than threshold farther from (0,0) than at ref_t."""
    ref = None
    for row in rows:
        if row["sim_time_sec"] <= ref_t and rid in row["robots"]:
            ref = row
    if ref is None:
        return {"ref_t": ref_t, "start_t": None, "ref_radius_m": None}
    r0 = math.hypot(ref["robots"][rid]["x"], ref["robots"][rid]["y"])
    start = None
    first_move = None
    for row in rows:
        if row["sim_time_sec"] < ref_t or rid not in row["robots"]:
            continue
        rob = row["robots"][rid]
        if first_move is None and rob["speed_mps"] > DEPARTURE_SPEED_MPS:
            first_move = row["sim_time_sec"]
        if math.hypot(rob["x"], rob["y"]) - r0 > threshold:
            start = row["sim_time_sec"]
            break
    return {
        "ref_t": round(ref_t, 3),
        "start_t": start,
        "ref_radius_m": round(r0, 4),
        "first_speed_gt_0p03_t": first_move,
    }


def summary_lookup(bundle: Path) -> dict[str, Any]:
    """Resolved flag and cross-check fields from a sibling summary dir or the bundle's ib10_score.json."""
    out: dict[str, Any] = {}
    for base in (bundle.parent.parent, bundle.parent.parent.parent):
        for name in ("summary", "summary_rerun"):
            f = base / name / "episodes.jsonl"
            if f.is_file():
                for row in read_jsonl(f):
                    if row.get("bundle") == bundle.name:
                        out = {
                            "source": str(f),
                            "status": row.get("status"),
                            "success": row.get("success"),
                            "resolved_frozen": row.get("resolved_frozen"),
                            "all_arrived": (row.get("frozen") or {}).get("all_arrived"),
                            "frozen_chi_pair": (row.get("frozen") or {}).get("chi_pair"),
                            "t0_sec": row.get("t0_sec"),
                            "gt_min_pairwise_m": row.get("gt_min_pairwise_m"),
                            "gt_min_pairwise_at_sec": row.get("gt_min_pairwise_at_sec"),
                            "gt_min_pairwise_pair": row.get("gt_min_pairwise_pair"),
                        }
    sc = bundle / "ib10_score.json"
    if sc.is_file() and not out:
        d = json.loads(sc.read_text())
        out = {
            "source": str(sc),
            "resolved_frozen": d.get("resolved"),
            "all_arrived": d.get("all_arrived"),
            "frozen_chi_pair": d.get("chi_pair"),
        }
    return out


def pick_junction_artifacts(bundle: Path) -> list[dict[str, Any]]:
    """Dispatched four-robot junction_clear decision artifacts, by snapshot stamp.

    Pre-November artifacts lack the `junction_phases` field, so phases are recovered from the
    `<request_id>-junction-{recede-<robot>,cross,release}` command ids in the logs instead.
    """
    found = []
    for f in sorted((bundle / "decisions").glob("*.json")):
        a = json.loads(f.read_text())
        if (a.get("decision") or {}).get("strategy") != "junction_clear" or not a.get(
            "grounded_command_present"
        ):
            continue
        if len((a.get("scene") or {}).get("robots") or []) != 4:
            continue
        found.append(a)
    return sorted(found, key=lambda a: (a.get("scene") or {}).get("stamp") or 0.0)


def analyse(
    bundle: Path, art: dict[str, Any] | None, n_arts: int, chi_by_req: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Analyse one junction_clear dispatch (artifact) of a bundle; returns a JSON-safe record."""
    rec: dict[str, Any] = {"bundle": bundle.name, "path": str(bundle)}
    rows = load_gt(bundle)
    rec["has_gt"] = bool(rows)
    rec["n_junction_clear_artifacts_in_bundle"] = n_arts
    if art is None:
        rec["status"] = "no_four_robot_junction_clear"
        return rec
    rid = art["request_id"]
    rec["request_id"] = rid
    rec["snapshot_stamp"] = (art.get("scene") or {}).get("stamp")
    jp_phases = (art.get("junction_phases") or {}).get("phases") or []
    rec["artifact_has_junction_phases"] = bool(jp_phases)
    rec["phases_recede_order"] = [p["robot_id"] for p in jp_phases if p["label"] == "recede"]
    legs = (art.get("plan") or {}).get("legs") or []
    rec["plan_legs_recede_order"] = [
        leg["robot_id"] for leg in legs if leg.get("action") == "reverse"
    ]
    chi = chi_by_req.get(rid) or {}
    rec["chi_order"] = chi.get("chi_order")
    rec["chi_costs"] = chi.get("chi_costs")
    rec["dispatch_order_source"] = art.get("dispatch_order_source")
    rec["provenance"] = (art.get("plan") or {}).get("provenance")

    m5_lines = (
        (bundle / "m5.log").read_text(errors="replace").splitlines()
        if (bundle / "m5.log").is_file()
        else []
    )
    m4_lines = (
        (bundle / "m4.log").read_text(errors="replace").splitlines()
        if (bundle / "m4.log").is_file()
        else []
    )
    cid_re = re.compile(re.escape(rid) + r"-junction-(recede-(robot_\d+)|cross|release)$")
    cids: dict[str, str] = {}
    for line in m4_lines + m5_lines:
        for tok in re.findall(r"command=(\S+)", line):
            m = cid_re.match(tok)
            if m:
                cids[("recede:" + m.group(2)) if m.group(2) else m.group(1)] = tok
    rec["phase_labels_from_logs"] = sorted(cids)
    first_m5: dict[str, float] = {}
    for line in m5_lines:
        m = M5_DISPATCH_RE.search(line)
        if m and m.group(3) not in first_m5:
            first_m5[m.group(3)] = float(m.group(1))
    first_m4: dict[str, float] = {}
    for line in m4_lines:
        m = M4_RECV_RE.search(line)
        if m and m.group(2) in cids.values() and m.group(2) not in first_m4:
            first_m4[m.group(2)] = float(m.group(1))
    recede_keys = [k for k in cids if k.startswith("recede:")]
    rec["m5_recede_dispatch_order"] = [
        k[7:]
        for k in sorted(
            (k for k in recede_keys if cids[k] in first_m5), key=lambda k: first_m5[cids[k]]
        )
    ]
    rec["m4_recede_received_order"] = [
        k[7:]
        for k in sorted(
            (k for k in recede_keys if cids[k] in first_m4), key=lambda k: first_m4[cids[k]]
        )
    ]
    executed = rec["m4_recede_received_order"] or rec["m5_recede_dispatch_order"]
    rec["executed_recede_order"] = executed
    rec["order_sources_agree"] = rec["m5_recede_dispatch_order"] == rec[
        "m4_recede_received_order"
    ] and (not jp_phases or rec["m4_recede_received_order"] == rec["phases_recede_order"])
    rec["plan_legs_match_dispatch"] = rec["plan_legs_recede_order"] == executed
    rec["executed_matches_chi"] = (
        (executed == rec["chi_order"]) if rec["chi_order"] and executed else None
    )
    if len(executed) == 2 and rec["chi_order"] and len(rec["chi_order"]) == 2:
        rec["rank1_robot"] = rec["chi_order"][1]
        rec["rank0_robot"] = rec["chi_order"][0]

    resolved = summary_lookup(bundle)
    rec["summary_crosscheck"] = resolved
    fcp = resolved.get("frozen_chi_pair") or {}
    if fcp.get("artifact") == f"{rid}.json":
        rec["frozen_scorer_chi_order"] = fcp.get("chi_order")
        rec["chi_order_matches_frozen_scorer"] = fcp.get("chi_order") == rec["chi_order"]
        rec["frozen_scorer_executed_recede_from_plan_legs"] = fcp.get("executed_recede")
    if not rows:
        rec["status"] = "missing_gt"
        return rec

    t0 = gt_t0(rows)
    arr = arrivals(rows)
    rec["t0_sec"] = t0
    rec["gt_end_sec"] = rows[-1]["sim_time_sec"]
    rec["arrivals_sec"] = arr
    rec["resolved_all_four_arrived"] = all(v is not None for v in arr.values())
    rec["episode_min_pairwise"] = min_pairwise(rows, t0 if t0 is not None else 0.0, float("inf"))

    tm = TimeMap(bundle, rid, (art.get("scene") or {}).get("stamp"), m5_lines)
    rec["time_map_ok"] = tm.ok
    if not tm.ok:
        rec["status"] = "no_time_map"
        return rec
    rec_cids = [cids[f"recede:{r}"] for r in executed if f"recede:{r}" in cids]
    t_first = {
        c: tm.sim(first_m4.get(c, first_m5.get(c)))
        for c in rec_cids
        if c in first_m4 or c in first_m5
    }
    t1 = min(t_first.values())
    cross = cids.get("cross")
    t_cross = tm.sim(first_m5[cross]) if cross in first_m5 else None
    window_hi = t_cross if t_cross is not None else rows[-1]["sim_time_sec"]
    rec["recede_window_sim"] = {
        "start": round(t1, 3),
        "end": round(window_hi, 3),
        "end_is_cross_dispatch": t_cross is not None,
    }
    rec["recede_window_min_pairwise"] = min_pairwise(rows, t1, window_hi)
    rec["recede_window_min_pairwise_includes_standing_jam"] = True
    last_before = max((r_["sim_time_sec"] for r_ in rows if r_["sim_time_sec"] <= t1), default=None)
    if last_before is not None:
        at_dispatch = min_pairwise(rows, last_before, last_before)
        rec["min_pairwise_at_last_sample_before_first_dispatch"] = at_dispatch
        rec["window_min_minus_standing_jam_min_m"] = round(
            rec["recede_window_min_pairwise"]["min_m"] - at_dispatch["min_m"], 4
        )
    rec["recede_window_contacts"] = contacts_in(rows, t1, window_hi)
    first_starts = [
        v for v in (radial_start(rows, r, t1, START_THRESHOLD_M)["start_t"] for r in executed) if v
    ]
    if first_starts:
        rec["min_pairwise_from_first_recede_start_to_cross"] = min_pairwise(
            rows, min(first_starts), window_hi
        )
    rec["episode_contacts_after_t0"] = contacts_in(rows, t0, float("inf"))

    starts: dict[str, Any] = {}
    for r in executed:
        own_t = t_first.get(cids.get(f"recede:{r}"), t1)
        starts[r] = {
            "own_dispatch_sim": round(own_t, 3),
            "common_ref": radial_start(rows, r, t1, START_THRESHOLD_M),
            "own_ref": radial_start(rows, r, own_t, START_THRESHOLD_M),
        }
    rec["recede_starts"] = starts
    cs = {r: v["common_ref"]["start_t"] for r, v in starts.items()}
    if executed and all(v is not None for v in cs.values()):
        first_mover = min(cs, key=lambda r: cs[r])
        rec["gt_first_mover"] = first_mover
        rec["gt_first_mover_matches_dispatch_first"] = first_mover == executed[0]
        if rec.get("rank1_robot"):
            rec["rank1_started_before_rank0"] = cs[rec["rank1_robot"]] < cs[rec["rank0_robot"]]
        if len(executed) == 2:
            second = executed[1]
            rec["second_common_ref_start_minus_own_dispatch_s"] = round(
                cs[second] - starts[second]["own_dispatch_sim"], 2
            )
            rec["second_started_before_own_dispatch"] = (
                cs[second] < starts[second]["own_dispatch_sim"]
            )
            first = executed[0]
            moving = [
                row["sim_time_sec"]
                for row in rows
                if cs[first] <= row["sim_time_sec"] <= starts[second]["own_dispatch_sim"]
                and row["robots"][first]["speed_mps"] > DEPARTURE_SPEED_MPS
            ]
            rec["first_receder_last_moving_t_before_second_dispatch"] = (
                max(moving) if moving else None
            )
            res_t = None
            for line in m5_lines:
                m = M5_RESOLVED_RE.search(line)
                if m and m.group(2) == cids.get(f"recede:{first}"):
                    res_t = tm.sim(float(m.group(1)))
                    break
            rec["first_recede_m5_resolved_sim"] = None if res_t is None else round(res_t, 3)
            own_start_second = starts[second]["own_ref"]["start_t"]
            rec["second_own_ref_start_t"] = own_start_second
            rec["overlap_second_started_before_first_finished"] = (
                own_start_second is not None and moving != [] and own_start_second < max(moving)
            )
            rec["start_lag_first_after_dispatch_s"] = round(cs[executed[0]] - t1, 2)
        rec.setdefault("start_lag_first_after_dispatch_s", round(cs[executed[0]] - t1, 2))
    else:
        rec["gt_first_mover"] = None
        rec["status"] = "start_not_detected"
        return rec
    rec["status"] = "ok"
    return rec


def stats(vals: list[float]) -> dict[str, Any]:
    """n/min/median/max of a list (None-safe)."""
    if not vals:
        return {"n": 0}
    return {
        "n": len(vals),
        "min": min(vals),
        "median": round(statistics.median(vals), 4),
        "max": max(vals),
        "values": sorted(vals),
    }


def summarise(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Summary block over analysable episodes."""
    ok = [r for r in recs if r.get("status") == "ok"]
    two = [r for r in ok if len(r["executed_recede_order"]) == 2]
    with_chi = [r for r in ok if "rank1_started_before_rank0" in r]
    out: dict[str, Any] = {
        "n_records": len(recs),
        "n_analysable_dispatches": len(ok),
        "n_two_recede_dispatches": len(two),
        "n_bundles_with_two_recede_dispatch": len({r["bundle"] for r in two}),
        "status_counts": {
            s: sum(1 for r in recs if r.get("status") == s)
            for s in sorted({r.get("status") for r in recs})
        },
        "n_with_chi_order": len(with_chi),
        "n_rank1_started_after_rank0": sum(
            1 for r in with_chi if not r["rank1_started_before_rank0"]
        ),
        "n_rank1_physically_first": sum(1 for r in with_chi if r["rank1_started_before_rank0"]),
        "n_executed_order_differs_from_chi": sum(
            1 for r in ok if r.get("executed_matches_chi") is False
        ),
        "n_gt_first_mover_differs_from_dispatch_first": sum(
            1 for r in ok if not r["gt_first_mover_matches_dispatch_first"]
        ),
        "n_order_sources_disagree": sum(1 for r in ok if not r["order_sources_agree"]),
        "n_plan_legs_differ_from_dispatch": sum(1 for r in ok if not r["plan_legs_match_dispatch"]),
        "n_second_common_ref_start_before_own_dispatch": sum(
            1 for r in ok if r.get("second_started_before_own_dispatch")
        ),
        "n_overlap_second_started_before_first_finished": sum(
            1 for r in ok if r.get("overlap_second_started_before_first_finished")
        ),
        "n_chi_checked_against_frozen_scorer": sum(
            1 for r in ok if "chi_order_matches_frozen_scorer" in r
        ),
        "n_chi_mismatch_vs_frozen_scorer": sum(
            1 for r in ok if r.get("chi_order_matches_frozen_scorer") is False
        ),
        "n_gt_contacts_key_missing_rows": sum(
            r["recede_window_contacts"]["gt_rows_missing_contacts_key"] for r in ok
        ),
        "n_recede_window_min_within_0p002_of_standing_jam_min": sum(
            1
            for r in two
            if r.get("window_min_minus_standing_jam_min_m") is not None
            and r["window_min_minus_standing_jam_min_m"] > -0.002
        ),
        "by_executed_first_robot": {},
    }
    for first in ("robot_3", "robot_4"):
        g = [r for r in two if r["executed_recede_order"][0] == first]
        out["by_executed_first_robot"][first] = {
            "episodes": [r["bundle"] for r in g],
            "recede_window_min_pairwise_m": stats(
                [r["recede_window_min_pairwise"]["min_m"] for r in g]
            ),
            "episode_min_pairwise_m": stats([r["episode_min_pairwise"]["min_m"] for r in g]),
            "n_with_recede_window_contacts": sum(
                1 for r in g if r["recede_window_contacts"]["samples_with_contacts"]
            ),
            "n_resolved": sum(1 for r in g if r["resolved_all_four_arrived"]),
        }
    return out


def main(argv: list[str]) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("roots", nargs="+", type=Path, help="bundle root dirs (or single bundles)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument(
        "--per-analysis",
        type=Path,
        required=True,
        help="per_analysis.jsonl with chi_order per request_id",
    )
    ap.add_argument("--exclude", nargs="*", default=[], help="bundle directory names to skip")
    args = ap.parse_args(argv)
    chi = {r["request_id"]: r for r in read_jsonl(args.per_analysis)}
    bundles = find_bundles(args.roots, set(args.exclude))
    recs = []
    for b in bundles:
        arts = pick_junction_artifacts(b)
        recs.extend(analyse(b, a, len(arts), chi) for a in arts or [None])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "definitions": {
                    "start_threshold_m": START_THRESHOLD_M,
                    "t0": "first GT sample with any speed_mps > 0.03",
                    "distance": "centre-to-centre from GT x/y, all pairs, t >= t0 for the episode minimum",
                    "recede_window": "first recede dispatch (m4 received, else m5) to cross-phase dispatch (m5)",
                    "starts_receding": "first GT sample >= reference time where hypot(x,y) exceeds its value at the last sample <= reference time by more than 0.05 m; common_ref = first recede dispatch (used for who moved first), own_ref = the robot's own recede dispatch",
                    "first_finish": "last GT sample between the first receder's start and the second recede dispatch with speed_mps > 0.03; m5 'resolved status' of the first recede command is also recorded",
                    "overlap": "second receder own_ref start earlier than first receder's last moving sample; no tolerance applied",
                    "wall_to_sim": "dispatch sim times are INFERRED via m5_scene.jsonl (t vs scene stamp) anchored at the 'starting analysis request=' log line vs the artifact snapshot stamp; error about a few tenths of a sim-second; GT start times are exact GT samples",
                    "phase_fallback": "artifacts lacking junction_phases (Oct bundles): phase commands recovered from <request_id>-junction-{recede-<robot>,cross,release} ids in m4/m5 logs",
                    "chi_source": "per_analysis.jsonl chi_order by request_id, cross-checked against frozen scorer chi_pair (summary episodes.jsonl or ib10_score.json) when its artifact matches",
                },
                "episodes": recs,
                "summary": summarise(recs),
            },
            indent=1,
        )
    )
    for r in recs:
        print(
            r["bundle"],
            (r.get("request_id") or "")[:8],
            r.get("status"),
            r.get("chi_order"),
            r.get("executed_recede_order"),
            r.get("gt_first_mover"),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

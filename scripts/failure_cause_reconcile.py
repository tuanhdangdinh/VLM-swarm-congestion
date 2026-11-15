"""Reconciliation of the two failure-cause rating passes and the interception table.

Governing documents (not edited here):

- rubric `docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md` section 7
  (frozen at `b70d925`);
- rating protocol `docs/reports/2026-11-15-failure-cause-rating-protocol.md`
  (`b7a3d25`);
- round-2 note `docs/reports/2026-11-15-failure-cause-rating-round2.md`
  (`89d9bf3` ... `8671843`).

Report: `docs/reports/2026-11-15-failure-cause-reconciliation.md`.

Read-only on the bundles, the rating files and every existing evidence file;
writes only under `data/experiments/2026-11-15-failure-cause-evidence/reconciliation/`.
No VM, no API call.

Subcommands (one Python process each, run one at a time):

- `geometry`: per bundle, the A33 pair intervals (centre gap < 0.45 m) from
  GT, for sensitivity S1, and T2 recomputed at every T2 snapshot of round 1
  and round 2 both as written (regression against the sheets) and with the
  start-inside rule (sensitivity S2). Imports the evidence tool's `Episode`
  and code trees (`scripts/failure_cause_evidence.py`, unchanged) and writes
  `reconciliation/geometry.json`.
- `build`: everything else, from files only: final codes per rater,
  agreement, reconciled codes, cause tables, S1/S2/S3 tables, the
  interception tables (stall-abort column from
  `reconciliation/stall_abort_replay_1016e0b.tsv`, produced by the committed
  v7p replay entry point) and the thesis placeholder values.

Usage (repo root):
    .venv/bin/python -B scripts/failure_cause_reconcile.py geometry
    .venv/bin/python -B scripts/failure_cause_reconcile.py build
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parents[1]
EVID = HERE / "data/experiments/2026-11-15-failure-cause-evidence"
OUT = EVID / "reconciliation"
CHANGE_LIST = Path(
    "/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v6d/docs/reports/"
    "2026-11-15-thesis-report-change-list.md"
)
STALL_TSV = OUT / "stall_abort_replay_1016e0b.tsv"

CONTACT_M = 0.005  # rubric X5/G5 contact gap; guard report "contact"
MARGIN_M = 0.05  # guard margin; guard report justified/false-positive split
S1_BOX_M = 0.05  # protocol S1: within 0.05 m of the same box
S2_EPS_M = 1e-6  # S2: "never deeper" tolerance on the footprint gap
MOTION_LEG_KINDS = {"backup", "reverse", "escort"}  # legs with a motion end (S1)
COLUMNS = ("A", "B", "H", "S", "N")
COLUMN_NAMES = {
    "A": "tranche 1 Arm A", "B": "tranche 1 Arm B", "H": "ER-2 pilots, horizon",
    "S": "ER-2 pilots, stop rule", "N": "November takes",
}
STRATA = {"T": ("A", "B"), "P": ("H", "S"), "N": ("N",)}
STRATUM_NAMES = {"T": "prereg-v3 tranche 1", "P": "ER-2 pilots", "N": "November takes"}

# Reconciliation rulings. Each names the clause, quotes it, and says whether the
# text decides (adopt a rater's code) or not (U with the clause named).
RULINGS: dict[str, dict[str, str]] = {
    "R-TIE": {
        "clause": "7.5 step 5",
        "quote": "If one event carries several codes, the primary is the most upstream: "
                 "V before G before X. Exception: G5 precedes the X code of the same leg, "
                 "because the leg itself was unsafe.",
        "ruling": "The clause orders classes only. It gives no order between two G codes "
                  "on one event; rater A's pipeline order (A2) and rater B's code-number "
                  "order (B13, not in B's log) are both readings the text does not make. "
                  "Not decided by the text.",
        "decides": "no",
        "u_code": "U:unresolved_tie_order_7.5_step5",
    },
    "R-X3T": {
        "clause": "7.1 Event; 7.2 X3; 7.5 steps 4 and 6",
        "quote": "7.1: \"Event. Any of: an analysis (decision artifact), a dispatched or "
                 "withheld command, an M4 primitive terminal status, a Nav2 abort line, an "
                 "M1 STALE interval, or a GT contact or sub-margin interval from the "
                 "recompute.\" \"Codes are assigned per event.\" 7.2 X3: \"after a command "
                 "completes, a non-exempt pair stays within min_distance_m until censoring "
                 "and both robots are stopped\". 7.5 step 4: \"a command outcome coded X1-X5 "
                 "by T3\". Step 6: \"If that event was a completed command followed by a "
                 "pinned pair, the code is X3.\"",
        "ruling": "A pinned-pair interval is not an event in 7.1's list, and codes are "
                  "assigned per event. Steps 4 and 6 attach X3 to the command outcome (the "
                  "completed command). X3 therefore sits at the command's M4 terminal "
                  "status (completion), not at the start of the pinned interval. Decided by "
                  "the text: rater A's reading (A10).",
        "decides": "yes",
    },
    "R-G1W": {
        "clause": "7.2 G1",
        "quote": "G1 refused a decision that is contract-consistent and T2-feasible",
        "ruling": "The clause requires a refusal, not a withheld or unpublished command. "
                  "At EV-7bda3f D1 every action of the decision (reverse robot_2, reverse "
                  "robot_3) was refused by the grounder, recorded as \"reverse refused: both "
                  "robots outside the corridor on the same side\" and replaced by waits; C1 "
                  "is False and T2 at D1 is True. Rater A's extra condition (published "
                  "False, A's R5) is not in the clause. Decided by the text: rater B's G1 "
                  "(B10, not in B's log) at 14.267, before the X3 at 23.705.",
        "decides": "yes",
    },
    "R-G4M": {
        "clause": "7.2 G4",
        "quote": "G4 roles changed so the dispatch differs from the decision (handoff, rear "
                 "exemption, swap, robots dropped)",
        "ruling": "The clause needs the dispatch to differ from the decision. Where the only "
                  "evidence is a `node_handoff` tag and the dispatch matches the plan "
                  "(dispatch_matches_plan True, same yielder), the dispatch does not differ, "
                  "so G4 is not met. Decided by the text: rater B's reading (B15).",
        "decides": "yes",
    },
    "R-G4D": {
        "clause": "7.2 G4 with 7.5 step 5",
        "quote": "G4 roles changed so the dispatch differs from the decision (handoff, ...)",
        "ruling": "Here the dispatch does differ (G6 flag set, dispatch_matches_plan False), "
                  "but by added waits, while the yielder is unchanged and a `node_handoff` "
                  "tag is present. Whether the handoff is a role change that makes the "
                  "dispatch differ is not fixed by the text; if it is, G4 and G6 sit on one "
                  "event and step 5 does not order them (R-TIE). Not decided by the text.",
        "decides": "no",
        "u_code": "U:unresolved_G4_handoff_7.2",
    },
    "R-S3-37a": {
        "clause": "7.2 G4, then 7.2 G5 / X5 placement",
        "quote": "G5 ... the recomputed GT gap of a commanded leg falls below 0.005 m; "
                 "X5 GT contact (recomputed gap < 0.005 m) not attributable to a G5 leg",
        "ruling": "Under R-G4M rater A's S3 code (G4) falls. Rater A's own recorded "
                  "alternative is then G5 (robot_4's backup, placed at its leg start 33.6), "
                  "rater B's code is X5 (robot_2's contact at 35.97). Adopting G5 would take "
                  "a code neither rater gave as S3, and the order turns on where G5 sits in "
                  "time, which neither rater's log settles the same way. Left U.",
        "decides": "no",
        "u_code": "U:unresolved_G5_placement_S3",
    },
}

# Disagreements on the final primary code (verified against the rating files at build).
PRIMARY_RESOLUTION: dict[tuple[str, str], dict[str, str]] = {
    ("EV-2c719b", "FU1"): {"ruling": "R-TIE", "ambiguity_A": "A2", "ambiguity_B": "B13 (cited in B's record; absent from B's ambiguities.md)"},
    ("EV-6f1277", "FU1"): {"ruling": "R-TIE", "ambiguity_A": "A2", "ambiguity_B": "B13 (cited in B's record; absent from B's ambiguities.md)"},
    ("EV-7bda3f", "FU1"): {"ruling": "R-G1W", "adopt": "B", "ambiguity_A": "R5 (G1 needs a withheld or unpublished command); A7 alternative", "ambiguity_B": "B10 (cited in B's record; absent from B's ambiguities.md)"},
    ("EV-cb3996", "FU2"): {"ruling": "R-X3T", "adopt": "A", "ambiguity_A": "A10 (X3 at completion; ALT[X3-at-pin-start]=X2)", "ambiguity_B": "B4 (X3 at the later of leg end and pin start)"},
    ("EV-298037", "FU2"): {"ruling": "R-X3T", "adopt": "A", "ambiguity_A": "A10 (ALT[X3-at-pin-start]=V1)", "ambiguity_B": "B4 and B8 (V1 at t0; B8 absent from B's ambiguities.md)"},
}
S3_RESOLUTION: dict[tuple[str, str], dict[str, str]] = {
    **PRIMARY_RESOLUTION,
    ("EV-0bdad6", "FU1"): {"ruling": "R-G4D", "ambiguity_A": "A6 / A2", "ambiguity_B": "B15"},
    ("EV-a6761e", "FU1"): {"ruling": "R-G4D", "ambiguity_A": "A6 / A2", "ambiguity_B": "B15"},
    ("EV-a6761e", "FU2"): {"ruling": "R-G4D", "ambiguity_A": "A6 / A2", "ambiguity_B": "B15"},
    ("EV-62b8d0", "FU1"): {"ruling": "R-G4M", "adopt": "B", "ambiguity_A": "A6 (A's note gives X1 under the other reading)", "ambiguity_B": "B15"},
    ("EV-37a70e", "FU1"): {"ruling": "R-S3-37a", "ambiguity_A": "A6 (A's note gives G5 under the other reading); R6", "ambiguity_B": "B15; B4"},
}

# Stall-abort report (v7p 1016e0b) section 6.4: primitives silent because the
# robot was latch-held when it stopped (wheels zeroed; detector idle by design).
LATCH_HELD_REQ8 = {"63f8d1ce", "984e3bdf", "ede6d209", "150b95a6", "09647748", "93100ae3",
                   "f06c33b3", "56b599af", "8066f542", "1feb2c4e", "07da775d"}
LATCH_AT_FACE = {("d5541ff0", "robot_2"), ("ea23b1a7", "robot_1")}


# --------------------------------------------------------------------------
# pure helpers (unit-tested in tests/unit/test_failure_cause_reconcile.py)
# --------------------------------------------------------------------------


def code_class(code: str) -> str:
    """Return the primary class of a cause code.

    Args:
        code: A rubric code such as `G4`, `EG1`, `U:T1_fidelity` or `V4j`.

    Returns:
        One of `V`, `G`, `X`, `EG`, `U`, `N`.
    """
    if code.startswith("U"):
        return "U"
    if code.startswith("EG"):
        return "EG"
    if code.startswith("N"):
        return "N"
    return code[0]


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    """Cohen's kappa for two raters over the same items.

    Args:
        a: Rater A's labels.
        b: Rater B's labels, same order and length.

    Returns:
        Kappa, or None where it is undefined (chance agreement equals 1, for
        example when every item falls in one category for both raters).
    """
    if len(a) != len(b) or not a:
        raise ValueError("label lists must be non-empty and of equal length")
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if math.isclose(pe, 1.0):
        return None
    return (po - pe) / (1.0 - pe)


def agreement(a: list[str], b: list[str]) -> dict[str, Any]:
    """Raw agreement and kappa for paired labels.

    Args:
        a: Rater A's labels.
        b: Rater B's labels.

    Returns:
        `n`, `agree`, `raw` (fraction) and `kappa` (None when undefined).
    """
    if not a:
        return {"n": 0, "agree": 0, "raw": None, "kappa": None}
    agree = sum(x == y for x, y in zip(a, b))
    k = cohen_kappa(a, b)
    return {"n": len(a), "agree": agree, "raw": round(agree / len(a), 4),
            "kappa": None if k is None else round(k, 4)}


def determined(code: str) -> str:
    """Map a code to `determined` or `undetermined`.

    Args:
        code: A primary code.

    Returns:
        `undetermined` for U codes, else `determined`.
    """
    return "undetermined" if code_class(code) == "U" else "determined"


def final_codes(r1: list[dict[str, Any]], r2: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Assemble one rater's final primary code per failure unit.

    Args:
        r1: The rater's round-1 unit records (`phase2_events.json` records).
        r2: The rater's round-2 records (`round2_events.json` records).

    Returns:
        Per (sheet, unit): round-1 code, final code (round 2 where in scope),
        S3 code (the final code where the rater gives none), step, contributing
        codes, and whether the unit was in round-2 scope.

    Raises:
        ValueError: if a round-2 record's round-1 code disagrees with round 1.
    """
    by2 = {(x["sheet_id"], x["unit_id"]): x for x in r2}
    out = {}
    for x in r1:
        if not x["unit_id"].startswith("FU") or x["primary_code"].startswith("NOT_FU"):
            continue
        key = (x["sheet_id"], x["unit_id"])
        rec = {"round1": x["primary_code"], "final": x["primary_code"],
               "s3": x["primary_code"], "step": x["step_fired"],
               "contributing": list(x.get("contributing_codes") or []), "in_scope": False}
        if key in by2:
            y = by2[key]
            if y["round1_primary_code"] != x["primary_code"]:
                raise ValueError(f"round-1 code mismatch at {key}")
            rec.update(final=y["round2_primary_code"], s3=y.get("s3_primary_code")
                       or y["round2_primary_code"], step=y["step_fired"],
                       contributing=list(y.get("contributing_codes") or []), in_scope=True)
        out[key] = rec
    return out


def reconcile(a: str, b: str, resolution: dict[str, str] | None) -> dict[str, str]:
    """Reconcile two codes under the recorded ruling.

    Args:
        a: Rater A's code.
        b: Rater B's code.
        resolution: The ruling entry for this unit, or None when the codes agree.

    Returns:
        `code`, `basis` (`agreed`, `text`, or `unresolved`) and `ruling`.

    Raises:
        ValueError: on a disagreement with no ruling.
    """
    if a == b:
        return {"code": a, "basis": "agreed", "ruling": ""}
    if resolution is None:
        raise ValueError(f"no ruling for disagreement {a} / {b}")
    rule = RULINGS[resolution["ruling"]]
    if rule["decides"] == "yes":
        code = a if resolution["adopt"] == "A" else b
        return {"code": code, "basis": "text", "ruling": resolution["ruling"]}
    return {"code": rule["u_code"], "basis": "unresolved", "ruling": resolution["ruling"]}


def episode_primary(units: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Rubric 7.5 episode primary: the unit with the earliest t0.

    Ties are broken by unit size (larger first is not stated; the rubric says
    "by FU size", read here as the larger unit), then the lowest robot id.

    Args:
        units: Units with `t0_rel`, `robots`.

    Returns:
        The deciding unit, or None for an episode with no unit.
    """
    if not units:
        return None
    return sorted(units, key=lambda u: (u["t0_rel"], -len(u["robots"]),
                                        min(int(r.split("_")[1]) for r in u["robots"])))[0]


def s1_links(
    legs: list[dict[str, Any]], robots: list[str], t0: float,
    box_spans: dict[str, list[dict[str, Any]]], pair_ivs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Protocol S1 (persistent-state chain rule) links of motion legs to one unit.

    A leg links when its robot is in the unit, its motion ended at or before
    t0, and from that end to t0 the robot stayed continuously within 0.05 m of
    one box (one span of the sheet's 0.05 m sub-margin spans covering the whole
    interval) or within 0.45 m centre distance of one robot (one A33 pair
    interval covering it), with no later command to that robot in between.

    Args:
        legs: The bundle's legs (`leg_id`, `robot`, `kind`, `dispatch_rel`,
            `end_rel_local`/`end_rel`).
        robots: The unit's robots.
        t0: The unit's onset, rel-s.
        box_spans: `spans_within_0.05m_rel` of the full sheet.
        pair_ivs: Pair intervals (`pair`, `onset_s`, `end_s`) from GT.

    Returns:
        One entry per linked leg with the persistent state that links it.
    """
    out = []
    for leg in legs:
        if leg["kind"] not in MOTION_LEG_KINDS or leg["robot"] not in robots:
            continue
        end = leg.get("end_rel_local", leg.get("end_rel"))
        if end is None or end > t0:
            continue
        r = leg["robot"]
        later = [x["leg_id"] for x in legs if x["robot"] == r and x.get("dispatch_rel") is not None
                 and end < x["dispatch_rel"] <= t0]
        if later:
            continue
        states = []
        for key, spans in box_spans.items():
            who, other = key.split("|", 1)
            if who != r or not other.startswith("box:"):
                continue
            states += [{"kind": "box", "with": other[4:], "from": s["from_rel"], "to": s["to_rel"]}
                       for s in spans if s["from_rel"] <= end and s["to_rel"] >= t0]
        for iv in pair_ivs:
            if r in iv["pair"] and iv["onset_s"] <= end and iv["end_s"] >= t0:
                other = iv["pair"][0] if iv["pair"][1] == r else iv["pair"][1]
                states.append({"kind": "robot", "with": other, "from": iv["onset_s"],
                               "to": iv["end_s"]})
        if states:
            out.append({"leg_id": leg["leg_id"], "robot": r, "dispatch_rel": leg["dispatch_rel"],
                        "motion_end_rel": end, "state": states})
    return out


def s2_blocked(gap: float, start_gap: float, need: float, eps: float = S2_EPS_M) -> bool:
    """S2 start-inside rule for one object along a straight move.

    A robot that starts inside the required clearance of an object may move
    along or away from it, never deeper; an object it starts clear of blocks
    as written (gap below the required clearance).

    Args:
        gap: Footprint gap to the object at the current pose.
        start_gap: The gap at the start pose.
        need: Required clearance (half-width + 0.05 m).
        eps: Tolerance for "deeper".

    Returns:
        True when the object blocks the move at this pose.
    """
    if gap >= need:
        return False
    if start_gap >= need:
        return True
    return gap < start_gap - eps


def blocked_robots(verdict: str) -> dict[str, float]:
    """Robots a guard verdict blocks, with their clear length.

    Args:
        verdict: `guard_verdict` of the interception input.

    Returns:
        Robot id to clear length in metres (empty when not refused).
    """
    return {m.group(1): float(m.group(3)) for m in re.finditer(
        r"(?:reverse|escort)_hits_obstacle:(robot_\d+):([^:;)]+):([0-9.]+)", verdict)}


def guard_leg_outcome(leg: dict[str, Any], clear_m: float | None) -> str:
    """Physical outcome of a leg a guard refuses (guard report v7l section 8.6 split).

    Args:
        leg: Interception leg with `m4_terminal`, `gt_moved_max_m`,
            `min_static_gap_m`, `min_robot_gap_m`, `pinned_on`.
        clear_m: The blocked leg's clear length; None for a co-refused leg whose
            own path is clear.

    Returns:
        `contact_or_pinned`, `submargin_graze`, `false_positive`, `untested`, or
        for a co-refused clear leg `co_refused_clear:<outcome>`.
    """
    gaps = [g for g in (leg.get("min_static_gap_m"), leg.get("min_robot_gap_m")) if g is not None]
    gap = min(gaps) if gaps else None
    if clear_m is None:
        return f"co_refused_clear:{leg.get('m4_terminal') or 'no_terminal'}"
    if leg.get("pinned_on") or (gap is not None and gap <= CONTACT_M):
        return "contact_or_pinned"
    if gap is not None and gap < MARGIN_M:
        return "submargin_graze"
    moved = leg.get("gt_moved_max_m") or 0.0
    if leg.get("m4_terminal") == "COMPLETED" or moved >= clear_m:
        return "false_positive"
    return "untested"


def stall_leg_outcome(leg: dict[str, Any], fired: bool, ran: bool) -> str:
    """Physical outcome class of a leg under the stall abort.

    Args:
        leg: Interception leg.
        fired: Whether the committed detector fired in the replay.
        ran: Whether the replay found a primitive for the leg that moved
            (False for escorts never admitted or never driven).

    Returns:
        For a fired leg `contact_or_pinned` or `false_positive`; otherwise
        `not_fired` or `no_primitive_ran`.
    """
    gaps = [g for g in (leg.get("min_static_gap_m"), leg.get("min_robot_gap_m")) if g is not None]
    gap = min(gaps) if gaps else None
    if fired:
        if leg.get("pinned_on") or (gap is not None and gap <= CONTACT_M):
            return "contact_or_pinned"
        return "false_positive"
    return "not_fired" if ran else "no_primitive_ran"


def table_counts(units: list[dict[str, Any]], field: str) -> dict[str, dict[str, int]]:
    """Count units per column by the class of one code field.

    Args:
        units: Units with `column` and the field.
        field: Field holding a code.

    Returns:
        Column to class to count.
    """
    out: dict[str, dict[str, int]] = {c: collections.Counter() for c in COLUMNS}
    for u in units:
        out[u["column"]][code_class(u[field])] += 1
    return {c: dict(v) for c, v in out.items()}


# --------------------------------------------------------------------------
# geometry (S1 pair intervals, S2 T2) through the evidence tool's trees
# --------------------------------------------------------------------------


def _load_tool() -> Any:
    path = HERE / "scripts" / "failure_cause_evidence.py"
    spec = importlib.util.spec_from_file_location("failure_cause_evidence", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["failure_cause_evidence"] = mod
    spec.loader.exec_module(mod)
    return mod


def t2_variant(ep: Any, fce: Any, scene: dict[str, Any], fu_robots: list[str], t_m1: float,
               start_inside: bool) -> dict[str, Any]:
    """T2 at one snapshot, as written or with the S2 start-inside rule.

    The as-written branch is the evidence tool's `Episode.t2` loop; the S2
    branch differs only in the blocking test (`s2_blocked`), applied per box
    and per other robot.

    Args:
        ep: The tool's `Episode`.
        fce: The tool module (constants).
        scene: The snapshot.
        fu_robots: The unit's robots.
        t_m1: Snapshot time on the M1 clock.
        start_inside: Apply the S2 rule.

    Returns:
        `result`, `shortest` and per-robot start-inside flags.
    """
    c = ep.T["contact"]
    t_gt = t_m1 - ep.offset
    boxes = [b for b in ep.boxes if b.is_active(t_gt)]
    poses = {r["robot_id"]: (r["x"], r["y"], r["theta"]) for r in scene["robots"]}
    need = ep.half_width + fce.T2_MARGIN_M
    best = None
    inside = {}
    for rid in fu_robots:
        if rid not in poses:
            continue
        x0, y0, th = poses[rid]
        others = {o: p for o, p in poses.items() if o != rid}
        start_box = {b.obstacle_id: c.robot_box_gap((x0, y0, th), b, ep.chassis) for b in boxes}
        start_rob = {o: c.robot_robot_gap((x0, y0, th), p, ep.chassis) for o, p in others.items()}
        inside[rid] = any(g is not None and g < need for g in start_box.values()) or any(
            g < need for g in start_rob.values())
        for k in range(8):
            h = k * math.pi / 4
            d = 0.0
            while d <= fce.T2_MAX_M + 1e-9:
                pose = (x0 + d * math.cos(h), y0 + d * math.sin(h), th)
                hit = False
                for b in boxes:
                    g = c.robot_box_gap(pose, b, ep.chassis)
                    if g is None:
                        continue
                    g0 = start_box[b.obstacle_id]
                    g0 = math.inf if g0 is None else g0
                    if (s2_blocked(g, g0, need) if start_inside else g < need):
                        hit = True
                        break
                if not hit:
                    for o, p in others.items():
                        g = c.robot_robot_gap(pose, p, ep.chassis)
                        if (s2_blocked(g, start_rob[o], need) if start_inside else g < need):
                            hit = True
                            break
                if hit:
                    break
                if d > 0 and all(math.dist(pose[:2], p[:2]) >= fce.MIN_DISTANCE_M
                                 for p in others.values()):
                    if best is None or round(d, 2) < best[0]:
                        best = (round(d, 2), rid, k * 45)
                    break
                d += fce.T2_STEP_M
    return {"result": best is not None,
            "shortest": None if best is None else {"robot": best[1], "heading_deg": best[2],
                                                   "distance_m": best[0]},
            "start_within_required_clearance": inside}


def cmd_geometry() -> None:
    """Pair intervals and T2 (as written and S2) for every bundle."""
    fce = _load_tool()
    trees = fce.load_trees()
    key = json.loads((EVID / "key/key.json").read_text())
    out: dict[str, Any] = {"tool_md5": fce._md5(HERE / "scripts/failure_cause_evidence.py"),
                           "provenance": trees["provenance"], "episodes": {}}
    for label in sorted(key):
        k = key[label]
        args = argparse.Namespace(label=label, stratum=k["stratum"], arm=k["arm"],
                                  params_from=None)
        ep = fce.Episode(trees, Path(k["bundle"]), args)
        full = json.loads((EVID / "full" / label / "evidence.json").read_text())
        r2 = json.loads((EVID / "full_round2" / label / "round2.json").read_text())
        pairs = [{"pair": list(iv.pair), "onset_s": round(iv.onset_s, 3),
                  "end_s": round(iv.end_s, 3)} for iv in trees["conflicts"].pair_intervals(ep.records)]
        art_by = {a["request_id"]: a for a in ep.artifacts}
        snaps = []
        for u in full["units"]:
            if u["excluded"]:
                continue
            for skey, row in full["t2"].get(u["fu"], {}).items():
                if "result" not in row:
                    continue
                if skey == "t0":
                    t_m1 = ep.records.t0_m1 + u["t0_rel"]
                    scene = ep.snapshot_at(t_m1)
                else:
                    scene = art_by[skey]["scene"]
                    t_m1 = scene["stamp"]
                snaps.append((u["fu"], skey, "round1", u["robots"], scene, t_m1, row))
            for rid, s in r2["units"].get(u["fu"], {}).get("t1_new_snapshots", {}).items():
                if not s.get("t2") or "result" not in s["t2"]:
                    continue
                scene = art_by[rid]["scene"]
                snaps.append((u["fu"], rid, "round2", u["robots"], scene, scene["stamp"], s["t2"]))
        rows = []
        for fu, skey, rnd, robots, scene, t_m1, sheet_row in snaps:
            aw = t2_variant(ep, fce, scene, robots, t_m1, start_inside=False)
            s2 = t2_variant(ep, fce, scene, robots, t_m1, start_inside=True)
            rows.append({
                "unit": fu, "snapshot": skey, "round": rnd,
                "snapshot_rel": sheet_row.get("snapshot_rel"),
                "sheet_result": sheet_row["result"], "sheet_shortest": sheet_row.get("shortest"),
                "as_written_recomputed": aw["result"], "as_written_shortest": aw["shortest"],
                "regression_equal": aw["result"] == sheet_row["result"]
                and aw["shortest"] == sheet_row.get("shortest"),
                "s2_result": s2["result"], "s2_shortest": s2["shortest"],
                "start_inside": s2["start_within_required_clearance"],
            })
        out["episodes"][label] = {"pair_intervals": pairs, "t2_rows": rows}
        print(f"{label}: pair intervals {len(pairs)}, T2 snapshots {len(rows)}, "
              f"regression {sum(r['regression_equal'] for r in rows)}/{len(rows)}, "
              f"S2 changes {sum(r['s2_result'] != r['sheet_result'] for r in rows)}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "geometry.json").write_text(json.dumps(out, indent=1))


# --------------------------------------------------------------------------
# build: reconciliation, tables, interception, thesis values (files only)
# --------------------------------------------------------------------------


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _column(stratum: str, arm: str, cut_short: bool) -> str:
    if stratum == "prereg_v3_tranche1":
        return "A" if arm == "A" else "B"
    if stratum == "pilot_er2":
        return "S" if cut_short else "H"
    return "N"


def _u_kind(code: str) -> str:
    if code.startswith("U:unresolved"):
        return "reading unresolved at reconciliation"
    return "missing evidence"


def _agree_block(units: list[dict[str, Any]], fa: str, fb: str) -> dict[str, Any]:
    a = [u[fa] for u in units]
    b = [u[fb] for u in units]
    return {
        "code": agreement(a, b),
        "class": agreement([code_class(x) for x in a], [code_class(x) for x in b]),
        "determined": agreement([determined(x) for x in a], [determined(x) for x in b]),
    }


def _groups(units: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    g: dict[str, list[dict[str, Any]]] = {c: [u for u in units if u["column"] == c] for c in COLUMNS}
    for s, cols in STRATA.items():
        g[f"stratum_{s}"] = [u for u in units if u["column"] in cols]
    g["ALL"] = list(units)
    return g


def _read_stall(path: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    out = {}
    for line in path.read_text().splitlines():
        f = line.split("\t")
        bundle, cmd, robot, prim, window = f[0], f[1], f[2], f[3], f[4]
        req8, kind = cmd.split("-", 1)
        replay = next(x for x in f if x.startswith("replay="))
        fired = "FIRED" in f
        start = float(window.split("-")[0])
        abort = float(replay.split("@")[1]) if fired else None
        leg_kind = {"reverse": "reverse"}.get(kind, prim) if prim == "backup" else prim
        out[(bundle, req8, robot, leg_kind)] = {
            "bundle": bundle, "req8": req8, "robot": robot, "primitive": prim, "command_kind": kind,
            "start_sim": start, "fired": fired, "abort_sim": abort,
            "time_to_abort_s": None if abort is None else round(abort - start, 1),
            "replay": replay, "live": next(x for x in f if x.startswith("live=")),
            "detail": f[f.index("FIRED") + 1] if fired else "",
            "min_ratio": next((x for x in f if x.startswith("min_ratio=")), ""),
        }
    return out


def _leg_physical(leg: dict[str, Any]) -> str:
    gaps = [g for g in (leg.get("min_static_gap_m"), leg.get("min_robot_gap_m")) if g is not None]
    gap = min(gaps) if gaps else None
    if leg.get("pinned_on") or (gap is not None and gap <= CONTACT_M):
        return "contact_or_pinned"
    if gap is not None and gap < MARGIN_M:
        return "submargin_graze"
    if leg.get("m4_terminal") == "COMPLETED":
        return "completed_clear"
    if leg.get("m4_terminal") is None and not leg.get("gt_moved_max_m"):
        return "no_motion"
    return "not_completed_no_contact"


def _thesis_ids() -> list[str]:
    text = CHANGE_LIST.read_text()
    sec = text[text.index("## 11. Failure-Cause"):text.index("## Source Key")]
    return sorted(set(re.findall(r"TBD-[A-Za-z0-9-]+?(?=:)", sec)) - {"TBD-ID"})


def cmd_build() -> None:  # noqa: C901, PLR0912, PLR0915
    """Reconcile, tabulate, join the interception table and fill the thesis values."""
    key = json.loads((EVID / "key/key.json").read_text())
    ev2ep = {v["events_id"]: e for e, v in key.items()}
    gt2ev = {v["gt_id"]: v["events_id"] for v in key.values()}
    full = {e: json.loads((EVID / "full" / e / "evidence.json").read_text()) for e in key}
    geom = json.loads((OUT / "geometry.json").read_text())
    rating_files = sorted((EVID / "ratings").glob("rater_*/*"))
    rater_md5 = {str(p.relative_to(EVID)): _md5(p) for p in rating_files}
    checks: dict[str, Any] = {}

    # ---- units and parked robots from the full sheets
    units: dict[tuple[str, str], dict[str, Any]] = {}
    parked = []
    for e, sheet in full.items():
        k = key[e]
        col = _column(k["stratum"], k["arm"], sheet["censor"]["cut_short_stop_rule"])
        for u in sheet["units"]:
            if u["excluded"]:
                continue
            rec = {"sheet_id": k["events_id"], "unit_id": u["fu"], "episode": e,
                   "stratum": k["stratum"], "arm": k["arm"], "column": col,
                   "cut_short_stop_rule": sheet["censor"]["cut_short_stop_rule"],
                   "kind": u["kind"], "robots": u["robots"], "t0_rel": u["t0_rel"],
                   "chain_rubric": u["chain"]["rubric"], "chain_start_rel": u["chain_start_rel"]}
            if any(f.startswith("finished_all_or_between_tasks_at_censor") for f in u["flags"]):
                parked.append(rec)
            else:
                units[(k["events_id"], u["fu"])] = rec

    # ---- raters
    fin, r1recs, p1 = {}, {}, {}
    for r in "AB":
        d = EVID / "ratings" / f"rater_{r}"
        r1 = json.loads((d / "phase2_events.json").read_text())["records"]
        r2 = json.loads((d / "round2_events.json").read_text())["records"]
        r1recs[r] = {(x["sheet_id"], x["unit_id"]): x for x in r1}
        fin[r] = final_codes(r1, r2)
        p1j = json.loads((d / "phase1_gt.json").read_text())
        p1[r] = {(x["sheet_id"], x["unit_id"]): x for x in
                 p1j["records"] + p1j.get("parked_finished_not_FU", [])}
        checks[f"round2_set_equals_in_scope_{r}"] = sorted(
            (x["sheet_id"], x["unit_id"]) for x in r2) == sorted(
            (x["sheet_id"], x["unit_id"]) for x in json.loads(
                (EVID / "rater_round2/in_scope_units.json").read_text())["units"])
    checks["unit_sets_equal_A_B_tool"] = set(fin["A"]) == set(fin["B"]) == set(units)
    checks["n_units"] = len(units)
    parked_a = sorted(k for k, x in r1recs["A"].items() if str(x["primary_code"]).startswith("NOT_FU"))
    parked_b = sorted((x["sheet_id"], x["unit_id"]) for x in json.loads(
        (EVID / "ratings/rater_B/phase2_events.json").read_text())["parked_finished_not_FU"])
    checks["parked_sets_equal_A_B_tool"] = parked_a == parked_b == sorted(
        (p["sheet_id"], p["unit_id"]) for p in parked)
    # Phase-1 GT codes: identical fields between raters, and onsets equal the full sheets.
    p1_diff = []
    for gk in sorted(p1["A"]):
        a, b = p1["A"][gk], p1["B"][gk]
        pairs = [("is_failure_unit", "is_failure_unit"), ("T2_t0", "T2_t0"),
                 ("X3_gt_input_present", "X3_gt_condition"), ("t0_rel", "t0_rel"),
                 ("kind", "kind"), ("robots", "robots"),
                 ("X5_candidate_gt_contact", None), ("EG2_candidate_undeclared_contact", None)]
        for fa, fb in pairs:
            va = a.get(fa)
            if fa == "X5_candidate_gt_contact":
                vb = bool(b.get("X5_gt_candidates"))
            elif fa == "EG2_candidate_undeclared_contact":
                va, vb = bool(va), "EG2" in (b.get("gt_context_codes") or [])
            else:
                vb = b.get(fb)
            if va != vb:
                p1_diff.append({"gt_unit": gk, "field": fa, "A": va, "B": vb})
        ev = gt2ev[gk[0]]
        fu = next(u for u in full[ev2ep[ev]]["units"] if u["fu"] == gk[1])
        if abs(fu["t0_rel"] - a["t0_rel"]) > 1e-6:
            p1_diff.append({"gt_unit": gk, "field": "t0 vs full sheet", "A": a["t0_rel"],
                            "B": fu["t0_rel"]})
    checks["phase1_differences"] = p1_diff
    checks["phase1_units_compared"] = len(p1["A"])

    # ---- per-unit records with both raters' codes
    for k, u in units.items():
        for r in "AB":
            f = fin[r][k]
            u[f"{r}_round1"], u[f"{r}_final"], u[f"{r}_s3"] = f["round1"], f["final"], f["s3"]
            u[f"{r}_step"], u[f"{r}_contributing"] = f["step"], f["contributing"]
            u["in_round2_scope"] = f["in_scope"]
    ulist = sorted(units.values(), key=lambda u: (COLUMNS.index(u["column"]), u["episode"],
                                                  u["unit_id"]))

    # ---- disagreements and reconciliation
    dis_final = [k for k, u in units.items() if u["A_final"] != u["B_final"]]
    dis_s3 = [k for k, u in units.items() if u["A_s3"] != u["B_s3"]]
    checks["primary_disagreements_have_rulings"] = sorted(dis_final) == sorted(PRIMARY_RESOLUTION)
    checks["s3_disagreements_have_rulings"] = sorted(dis_s3) == sorted(S3_RESOLUTION)
    if not (checks["primary_disagreements_have_rulings"] and checks["s3_disagreements_have_rulings"]):
        raise SystemExit(f"rulings do not match disagreements: {dis_final} / {dis_s3}")
    for k, u in units.items():
        rp = reconcile(u["A_final"], u["B_final"], PRIMARY_RESOLUTION.get(k))
        rs = reconcile(u["A_s3"], u["B_s3"], S3_RESOLUTION.get(k))
        u["reconciled"], u["reconciled_basis"], u["reconciled_ruling"] = rp["code"], rp["basis"], rp["ruling"]
        u["reconciled_class"] = code_class(rp["code"])
        u["s3_reconciled"], u["s3_basis"], u["s3_ruling"] = rs["code"], rs["basis"], rs["ruling"]
        if u["reconciled_class"] == "U":
            u["u_kind"] = _u_kind(rp["code"])
        sa = {u["A_final"], *u["A_contributing"]}
        sb = {u["B_final"], *u["B_contributing"]}
        drop = {u["reconciled"], "N0"}
        u["contributing_intersection"] = sorted(c for c in (sa & sb) - drop if not c.startswith("U"))
        u["contributing_union"] = sorted(c for c in (sa | sb) - drop if not c.startswith("U"))
        u["context_codes"] = ["N0"] if u["arm"] == "B" else []

    def dis_row(k: tuple[str, str], fa: str, fb: str, table: dict) -> dict[str, Any]:
        u = units[k]
        res = table[k]
        rule = RULINGS[res["ruling"]]
        rr = reconcile(u[fa], u[fb], res)
        return {"sheet_id": k[0], "unit_id": k[1], "episode": u["episode"],
                "column": u["column"], "A_code": u[fa], "B_code": u[fb],
                "A_step": u["A_step"], "B_step": u["B_step"],
                "A_ambiguity": res["ambiguity_A"], "B_ambiguity": res["ambiguity_B"],
                "ruling": res["ruling"], "clause": rule["clause"], "decided_by_text": rule["decides"],
                "reconciled": rr["code"], "reason": rule["ruling"]}

    disagreements = [dis_row(k, "A_final", "B_final", PRIMARY_RESOLUTION) for k in sorted(dis_final)]
    s3_disagreements = [dis_row(k, "A_s3", "B_s3", S3_RESOLUTION) for k in sorted(dis_s3)]
    r1_dis = []
    for k, u in sorted(units.items()):
        if u["A_round1"] != u["B_round1"]:
            why = ("A R3 (walk continued at a decision without a T1 row) vs B B2 (U:T1_not_run); "
                   "evidence gap closed by round 2") if "U:T1_not_run" in (
                u["A_round1"], u["B_round1"]) else "same split as the final disagreement"
            r1_dis.append({"sheet_id": k[0], "unit_id": k[1], "episode": u["episode"],
                           "A": u["A_round1"], "B": u["B_round1"], "explained_by": why,
                           "final_A": u["A_final"], "final_B": u["B_final"]})

    # ---- agreement
    groups = _groups(ulist)
    agree = {g: {"final": _agree_block(us, "A_final", "B_final"),
                 "round1": _agree_block(us, "A_round1", "B_round1"),
                 "s3": _agree_block(us, "A_s3", "B_s3"),
                 "disagreements_final": sum(u["A_final"] != u["B_final"] for u in us),
                 "disagreements_left_U": sum(u["A_final"] != u["B_final"]
                                             and u["reconciled_class"] == "U" for u in us)}
             for g, us in groups.items()}

    # ---- cause tables
    ep_units: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for u in ulist:
        ep_units[u["episode"]].append(u)
    ep_primary = {}
    ties = []
    for e, us in ep_units.items():
        t0s = sorted(u["t0_rel"] for u in us)
        if len(t0s) > 1 and math.isclose(t0s[0], t0s[1]):
            ties.append(e)
        p = episode_primary(us)
        ep_primary[e] = {"unit": p["unit_id"], "code": p["reconciled"],
                         "class": p["reconciled_class"], "column": p["column"],
                         "A": p["A_final"], "B": p["B_final"]}
    checks["episode_primary_t0_ties"] = ties
    episodes_by_col = collections.defaultdict(list)
    for e, k in key.items():
        episodes_by_col[_column(k["stratum"], k["arm"],
                                full[e]["censor"]["cut_short_stop_rule"])].append(e)
    classes = ("V", "G", "X", "EG", "U")
    primary_table = {}
    for c in COLUMNS:
        us = [u for u in ulist if u["column"] == c]
        row = {}
        for cl in classes:
            row[cl] = {"units": sum(u["reconciled_class"] == cl for u in us),
                       "episodes": sum(1 for e in episodes_by_col[c]
                                       if e in ep_primary and ep_primary[e]["class"] == cl)}
            row[cl]["A_units"] = sum(code_class(u["A_final"]) == cl for u in us)
            row[cl]["B_units"] = sum(code_class(u["B_final"]) == cl for u in us)
        row["total"] = {"units": len(us), "episodes_with_unit": sum(
            1 for e in episodes_by_col[c] if e in ep_units), "episodes": len(episodes_by_col[c])}
        row["parked_not_units"] = sum(p["column"] == c for p in parked)
        row["codes"] = dict(collections.Counter(u["reconciled"] for u in us))
        row["contributing_intersection"] = {cl: sum(any(code_class(x) == cl for x in
                                                        u["contributing_intersection"]) for u in us)
                                            for cl in ("V", "G", "X", "EG")}
        row["contributing_union"] = {cl: sum(any(code_class(x) == cl for x in u["contributing_union"])
                                             for u in us) for cl in ("V", "G", "X", "EG")}
        row["contributing_codes_intersection"] = dict(collections.Counter(
            x for u in us for x in u["contributing_intersection"]))
        row["undetermined"] = dict(collections.Counter(u["reconciled"] for u in us
                                                       if u["reconciled_class"] == "U"))
        row["s3"] = {cl: sum(code_class(u["s3_reconciled"]) == cl for u in us) for cl in classes}
        row["s3_codes"] = dict(collections.Counter(u["s3_reconciled"] for u in us))
        row["s3_changed_units"] = sum(u["s3_reconciled"] != u["reconciled"] for u in us)
        primary_table[c] = row
    for u in ulist:
        checks.setdefault("units_per_column", collections.Counter())[u["column"]] += 1
    checks["units_per_column"] = dict(checks["units_per_column"])
    checks["primary_table_row_sums"] = all(
        sum(primary_table[c][cl]["units"] for cl in classes) == primary_table[c]["total"]["units"]
        for c in COLUMNS)
    checks["primary_table_episode_sums"] = all(
        sum(primary_table[c][cl]["episodes"] for cl in classes)
        == primary_table[c]["total"]["episodes_with_unit"] for c in COLUMNS)
    checks["arm_B_has_no_V_or_G"] = all(
        primary_table["B"][cl]["units"] == 0 and primary_table["B"]["contributing_union"][cl] == 0
        for cl in ("V", "G"))

    # dominance check (report wording rule)
    dominance = {}
    for s, cols in STRATA.items():
        us = [u for u in ulist if u["column"] in cols]
        det = [u for u in us if u["reconciled_class"] != "U"]
        res = {}
        for who, field in (("A", "A_final"), ("B", "B_final"), ("reconciled", "reconciled")):
            cnt = collections.Counter(code_class(u[field]) for u in us if code_class(u[field]) != "U")
            top = cnt.most_common()
            res[who] = {"counts": dict(cnt), "unique_top": top[0][0] if top and (
                len(top) == 1 or top[0][1] > top[1][1]) else None}
        same = len({res[w]["unique_top"] for w in res}) == 1 and res["A"]["unique_top"] is not None
        dominance[s] = {"units": len(us), "determined": len(det),
                        "undetermined": len(us) - len(det), **res,
                        "one_class_exceeds_others_in_all_three": same}

    # ---- S1 (mechanical)
    s1 = []
    for u in ulist:
        if u["arm"] != "A":
            continue
        sheet = full[u["episode"]]
        pairs = geom["episodes"][u["episode"]]["pair_intervals"]
        links = s1_links(sheet["legs"], u["robots"], u["t0_rel"],
                         sheet["contacts"]["spans_within_0.05m_rel"], pairs)
        extra = [x for x in links if x["leg_id"] not in u["chain_rubric"]]
        starts = [x["dispatch_rel"] for x in extra if x["dispatch_rel"] is not None]
        new_start = min([*starts, *([u["chain_start_rel"]] if u["chain_start_rel"] is not None else [])],
                        default=None)
        u["s1_links"] = [x["leg_id"] for x in links]
        u["s1_additional_links"] = [x["leg_id"] for x in extra]
        u["s1_walk_start_moves"] = bool(extra) and (
            u["chain_start_rel"] is None or (new_start is not None and new_start < u["chain_start_rel"]))
        if extra:
            s1.append({"sheet_id": u["sheet_id"], "unit_id": u["unit_id"], "episode": u["episode"],
                       "column": u["column"], "robots": u["robots"], "t0_rel": u["t0_rel"],
                       "primary_chain_start_rel": u["chain_start_rel"],
                       "s1_chain_start_rel": new_start, "walk_start_moves": u["s1_walk_start_moves"],
                       "additional_links": extra, "reconciled_primary": u["reconciled"]})
    for u in ulist:
        u.setdefault("s1_links", [])
        u.setdefault("s1_additional_links", [])
        u.setdefault("s1_walk_start_moves", False)
    m5d = units[(key["m5D_t01_a1"]["events_id"], "FU2")]
    checks["s1_validation_m5D_escort_links_FU2"] = "a15f3fc5:robot_3:escort" in m5d["s1_additional_links"]

    # ---- S2 (mechanical)
    s2_rows = []
    n_t2 = 0
    for e, g in geom["episodes"].items():
        dec_by = {d["request_id"]: d for d in full[e]["decisions"]}
        for r in g["t2_rows"]:
            n_t2 += 1
            if r["s2_result"] == r["sheet_result"]:
                continue
            u = units.get((key[e]["events_id"], r["unit"]))
            d = dec_by.get(r["snapshot"])
            gr = (d or {}).get("grounding") or {}
            s2_rows.append({
                "episode": e, "sheet_id": key[e]["events_id"], "unit_id": r["unit"],
                "snapshot": "t0" if r["snapshot"] == "t0" else next(
                    dk for dk, v in key[e]["decision_ids"].items() if v == r["snapshot"]),
                "round": r["round"], "as_written": r["sheet_result"], "s2": r["s2_result"],
                "s2_shortest": r["s2_shortest"], "start_inside": r["start_inside"],
                "decision_published": gr.get("published"), "decision_withheld": gr.get("withheld"),
                "decision_t_rel": (d or {}).get("t_rel"),
                "unit_reconciled_primary": u["reconciled"] if u else None,
            })
    checks["s2_regression_as_written_equal"] = all(
        r["regression_equal"] for g in geom["episodes"].values() for r in g["t2_rows"])
    checks["s2_snapshots"] = n_t2

    # ---- rule properties
    t1_onset_nonempty = []
    v2_rows = {"rows": 0, "rows_with_robot_in_every_motion_label": 0}

    def robots_of(label: str) -> set[str]:
        return set(re.findall(r"robot_\d+", label))

    for e, sheet in full.items():
        for fu, rows in sheet["t1"].items():
            for skey, row in rows.items():
                var = (row.get("variants") or {}).get("as_written")
                if not var:
                    continue
                if skey == "t0":
                    t1_onset_nonempty.append(bool(var.get("nonempty")))
                mot = var.get("motion") or []
                if mot:
                    v2_rows["rows"] += 1
                    if set.intersection(*[robots_of(m) for m in mot]):
                        v2_rows["rows_with_robot_in_every_motion_label"] += 1
        r2 = json.loads((EVID / "full_round2" / e / "round2.json").read_text())
        for fu, uu in r2["units"].items():
            for rid, s in (uu.get("t1_new_snapshots") or {}).items():
                for vname in ("as_written", "S3_stage2_label_and_task_intents"):
                    mot = ((s.get("t1") or {}).get(vname) or {}).get("t1", {}).get("motion") or []
                    if mot:
                        v2_rows["rows"] += 1
                        if set.intersection(*[robots_of(m) for m in mot]):
                            v2_rows["rows_with_robot_in_every_motion_label"] += 1
    all_codes = [c for u in ulist for c in (u["A_final"], u["B_final"], u["A_s3"], u["B_s3"],
                                           *u["A_contributing"], *u["B_contributing"])]
    rule_props = {
        "t1_onset_snapshots": len(t1_onset_nonempty),
        "t1_onset_nonempty": sum(t1_onset_nonempty),
        "EG1_or_G7_anywhere_in_either_raters_codes": sum(c in ("EG1", "G7") for c in all_codes),
        "V2_anywhere_in_either_raters_codes": sum(c == "V2" for c in all_codes),
        "t1_motion_rows_checked_for_V2": v2_rows,
        "units_reconciled_U_T1_fidelity": sum(u["reconciled"] == "U:T1_fidelity" for u in ulist),
        "units_s3_U_T1_fidelity": sum(u["s3_reconciled"] == "U:T1_fidelity" for u in ulist),
        "units_with_s1_additional_link": len(s1),
        "units_whose_walk_start_moves_under_s1": sum(x["walk_start_moves"] for x in s1),
    }

    # ---- interception
    legs = json.loads((EVID / "interception/legs.json").read_text())
    stall = _read_stall(STALL_TSV)
    checks["stall_tsv_identical_to_provisional"] = (
        sorted((EVID / "replay/stall_abort_replay.tsv").read_text().splitlines())
        == sorted(STALL_TSV.read_text().splitlines()))
    checks["stall_tsv_bundles"] = len({v["bundle"] for v in stall.values()})
    leg_rows = []
    for l in legs:
        e = l["label"]
        sheet_leg = next(x for x in full[e]["legs"] if x["leg_id"] == l["leg_id"])
        req8, robot, kind = l["leg_id"].split(":")
        bundle = Path(key[e]["bundle"]).name
        st = stall.get((bundle, req8, robot, kind))
        blocked = blocked_robots(l["guard_verdict"]) if l["guard_verdict"].startswith("refused") else {}
        refused = l["guard_verdict"].startswith("refused")
        leg = {**l, "min_robot_gap_m": sheet_leg.get("min_robot_gap_m")}
        esc = kind == "escort" and refused
        rev = kind == "reverse" and refused
        fired = bool(st and st["fired"])
        ran = st is not None and not (l["m4_terminal"] is None
                                      and (l.get("gt_moved_max_m") or 0.0) <= 0.05)
        phys = _leg_physical(leg)
        # The guards test declared boxes; their justified/false-positive split uses the
        # box gap only (v7l 8.6). The stall abort judges any stall, robot contact included.
        phys_box = _leg_physical({**leg, "min_robot_gap_m": None})
        guard_class = guard_leg_outcome({**leg, "min_robot_gap_m": None},
                                        blocked.get(robot)) if refused else ""
        prov = l.get("stall_abort") or ""
        prov_fired = "FIRED" in prov
        reasons = []
        if not (esc or rev or fired) and phys != "completed_clear":
            if l.get("m4_terminal") is None:
                reasons.append("never admitted or no terminal line; no motion to judge")
            if req8 in LATCH_HELD_REQ8:
                reasons.append("robot latch-held when it stopped (stall abort idle by design, SA 6.4)")
            if (req8, robot) in LATCH_AT_FACE:
                reasons.append("reached the box face as the latch engaged (SA 6.4)")
            if not reasons:
                reasons.append(f"not refused by a guard and stall abort silent ({st['min_ratio'] if st else 'no replay row'})")
        leg_rows.append({
            "episode": e, "stratum": l["stratum"], "column": _column(
                l["stratum"], "A", full[e]["censor"]["cut_short_stop_rule"]),
            "leg_id": l["leg_id"], "kind": kind, "m4_terminal": l["m4_terminal"],
            "gt_moved_max_m": l["gt_moved_max_m"], "min_static_gap_m": l["min_static_gap_m"],
            "min_robot_gap_m": leg["min_robot_gap_m"], "pinned_on": l["pinned_on"],
            "ended_by_deadline": l["ended_by_deadline"], "tags": l["tags"],
            "physical": phys, "physical_box": phys_box, "guard_verdict": l["guard_verdict"],
            "escort_guard_refuses": esc, "reverse_guard_refuses": rev,
            "guard_leg_role": ("blocked" if robot in blocked else "co_refused_clear") if refused else "",
            "guard_outcome": guard_class,
            "stall_abort_fires": fired, "stall_time_to_abort_s": st["time_to_abort_s"] if st else None,
            "stall_abort_sim_s": st["abort_sim"] if st else None,
            "stall_replay": st["replay"] if st else "no replay row",
            "stall_outcome": stall_leg_outcome(leg, fired, ran),
            "stall_provisional": prov, "stall_differs_from_provisional": prov_fired != fired,
            "any_mechanism": esc or rev or fired,
            "caught_by": [m for m, f in (("escort_guard", esc), ("reverse_guard", rev),
                                          ("stall_abort", fired)) if f],
            "fu_primary_chain": l["fu_rubric_window"], "fu_s1": [],
            "not_caught_reason": "; ".join(reasons),
        })
    checks["legs_chain_window_equals_full_sheet_chain"] = all(
        sorted(r["fu_primary_chain"]) == sorted(
            u["unit_id"] for u in ulist if u["episode"] == r["episode"]
            and r["leg_id"] in u["chain_rubric"]) for r in leg_rows)
    checks["legs"] = len(leg_rows)
    checks["legs_per_stratum"] = dict(collections.Counter(r["stratum"] for r in leg_rows))
    checks["stall_differs_from_provisional"] = [r["leg_id"] for r in leg_rows
                                                if r["stall_differs_from_provisional"]]
    by_leg = {(r["episode"], r["leg_id"]): r for r in leg_rows}
    for u in ulist:
        for lid in u["s1_links"]:
            if (u["episode"], lid) in by_leg:
                by_leg[(u["episode"], lid)]["fu_s1"].append(u["unit_id"])
    # stall-abort fires on primitives outside the 57-leg set (yield backups / pull-offs)
    leg_ids = {(Path(key[r["episode"]]["bundle"]).name, r["leg_id"].split(":")[0], r["leg_id"].split(":")[1])
               for r in leg_rows}
    extra_fires = [v for v in stall.values() if v["fired"] and (v["bundle"], v["req8"], v["robot"]) not in leg_ids]

    # per-unit interception
    bundle2ep = {Path(v["bundle"]).name: e for e, v in key.items()}
    unit_rows = []
    for u in ulist:
        if u["arm"] != "A":
            continue
        row = {"sheet_id": u["sheet_id"], "unit_id": u["unit_id"], "episode": u["episode"],
               "column": u["column"], "reconciled": u["reconciled"],
               "reconciled_class": u["reconciled_class"]}
        for rule, field in (("primary", "fu_primary_chain"), ("s1", None)):
            if field:
                linked = [r for r in leg_rows if r["episode"] == u["episode"]
                          and u["unit_id"] in r[field]]
            else:
                linked = [r for r in leg_rows if r["episode"] == u["episode"]
                          and (u["unit_id"] in r["fu_primary_chain"] or u["unit_id"] in r["fu_s1"])]
            mech = {m: [r["leg_id"] for r in linked if m in r["caught_by"]]
                    for m in ("escort_guard", "reverse_guard", "stall_abort")}
            caught = [r for r in linked if r["any_mechanism"]]
            cat = ("intercepted" if caught else "linked_none_intercepted" if linked
                   else "no_linked_leg")
            row[f"{rule}_linked_legs"] = [r["leg_id"] for r in linked]
            row[f"{rule}_category"] = cat
            # physical record of the intercepted linked legs (box gap for guard-only legs)
            phys = sorted({(r["physical"] if r["stall_abort_fires"] else r["physical_box"])
                           for r in caught})
            row[f"{rule}_intercepted_physical"] = phys
            row[f"{rule}_intercepted_justified"] = any(
                p in ("contact_or_pinned", "submargin_graze") for p in phys)
            for m, v in mech.items():
                row[f"{rule}_{m}"] = v
        links_all = set(u["chain_rubric"])
        row["stall_fires_on_linked_primitive_outside_57"] = [
            f"{v['req8']}:{v['robot']}:{v['primitive']}" for v in extra_fires
            if bundle2ep[v["bundle"]] == u["episode"] and any(
                lid.startswith(f"{v['req8']}:{v['robot']}:") for lid in links_all)]
        unit_rows.append(row)

    def mech_panel(col_set: tuple[str, ...]) -> dict[str, Any]:
        lr = [r for r in leg_rows if r["column"] in col_set]
        ur = [r for r in unit_rows if r["column"] in col_set]
        panel: dict[str, Any] = {"legs": len(lr), "units": len(ur)}
        for m, pred in (("ESC", lambda r: r["escort_guard_refuses"]),
                        ("REV", lambda r: r["reverse_guard_refuses"]),
                        ("STL", lambda r: r["stall_abort_fires"]),
                        ("ANY", lambda r: r["any_mechanism"])):
            sel = [r for r in lr if pred(r)]
            key_m = {"ESC": "escort_guard", "REV": "reverse_guard", "STL": "stall_abort"}.get(m)
            ph = collections.Counter(
                r["physical_box"] if m in ("ESC", "REV") or (m == "ANY" and not r["stall_abort_fires"])
                else r["physical"] for r in sel)
            panel[m] = {
                "L": len(sel),
                "contact_or_pinned": ph["contact_or_pinned"],
                "submargin_graze": ph["submargin_graze"],
                "J": ph["contact_or_pinned"] + ph["submargin_graze"],
                "F": ph["completed_clear"],
                "UT": ph["not_completed_no_contact"] + ph["no_motion"],
                "blocked_split": dict(collections.Counter(
                    r["guard_outcome"] for r in sel if r["guard_leg_role"] == "blocked"))
                if m in ("ESC", "REV") else None,
                "co_refused_clear": sum(r["guard_leg_role"] == "co_refused_clear" for r in sel)
                if m in ("ESC", "REV") else None,
                "P": sum(1 for r in ur if (r[f"primary_{key_m}"] if key_m else
                                           r["primary_category"] == "intercepted")),
                "S": sum(1 for r in ur if (r[f"s1_{key_m}"] if key_m else
                                           r["s1_category"] == "intercepted")),
            }
        for rule in ("primary", "s1"):
            cats = collections.Counter(r[f"{rule}_category"] for r in ur)
            panel[f"categories_{rule}"] = dict(cats)
            panel[f"intercepted_with_justified_leg_{rule}"] = sum(
                r[f"{rule}_intercepted_justified"] for r in ur)
            panel[f"intercepted_by_class_{rule}"] = dict(collections.Counter(
                r["reconciled_class"] for r in ur if r[f"{rule}_category"] == "intercepted"))
            panel[f"category_by_class_{rule}"] = {
                cat: dict(collections.Counter(r["reconciled_class"] for r in ur
                                              if r[f"{rule}_category"] == cat))
                for cat in ("intercepted", "linked_none_intercepted", "no_linked_leg")}
        panel["units_with_stall_fire_on_linked_yield_primitive"] = [
            f"{r['episode']} {r['unit_id']}: {r['stall_fires_on_linked_primitive_outside_57']}"
            for r in ur if r["stall_fires_on_linked_primitive_outside_57"]]
        panel["overlap"] = {
            "legs_caught_by_more_than_one": [r["leg_id"] for r in lr if len(r["caught_by"]) > 1],
            "legs_only_stall_abort": [r["leg_id"] for r in lr if r["caught_by"] == ["stall_abort"]],
            "legs_failed_pinned_stalled_or_deadline_not_caught": [
                {"leg_id": r["leg_id"], "episode": r["episode"], "physical": r["physical"],
                 "m4_terminal": r["m4_terminal"], "reason": r["not_caught_reason"]}
                for r in lr if not r["any_mechanism"] and (
                    r["m4_terminal"] != "COMPLETED" or r["pinned_on"] or r["ended_by_deadline"])],
        }
        return panel

    panels = {"A": mech_panel(("A",)), "P": mech_panel(("H", "S")), "N": mech_panel(("N",)),
              "H": mech_panel(("H",)), "S": mech_panel(("S",))}
    for p, cols in (("A", ("A",)), ("P", ("H", "S")), ("N", ("N",))):
        pan = panels[p]
        for rule in ("primary", "s1"):
            cats = pan[f"categories_{rule}"]
            tot = sum(cats.values())
            checks[f"interception_{p}_{rule}_any_plus_none_eq_tot"] = (
                cats.get("intercepted", 0) + cats.get("linked_none_intercepted", 0)
                + cats.get("no_linked_leg", 0) == tot == pan["units"]
                == sum(primary_table[c]["total"]["units"] for c in cols))
        for m in ("ESC", "REV", "STL", "ANY"):
            mm = pan[m]
            if m != "STL":
                checks[f"interception_{p}_{m}_J_F_UT_sum"] = mm["J"] + mm["F"] + mm["UT"] == mm["L"]
        checks[f"interception_{p}_ANY_bounds"] = max(pan[m]["L"] for m in ("ESC", "REV", "STL")) <= \
            pan["ANY"]["L"] <= sum(pan[m]["L"] for m in ("ESC", "REV", "STL"))
    blocked_all = collections.Counter(r["guard_outcome"] for r in leg_rows
                                      if r["guard_leg_role"] == "blocked" and r["reverse_guard_refuses"])
    checks["reverse_blocked_split_vs_v7l_8.6"] = dict(blocked_all)
    episodes_with_legs = sorted({r["episode"] for r in leg_rows})
    l2on = sorted(e for e, k in key.items() if k["arm"] == "A")
    denominator = {
        "layer2_on_episodes": len(l2on), "episodes_with_reverse_or_escort_leg": len(episodes_with_legs),
        "episodes_without": sorted(set(l2on) - set(episodes_with_legs)),
        "motion_legs_in_episodes_without": {e: [x["leg_id"] for x in full[e]["legs"]
                                                if x["kind"] != "wait"]
                                            for e in sorted(set(l2on) - set(episodes_with_legs))},
        "legs_any_kind_in_episodes_without": {e: len(full[e]["legs"])
                                              for e in sorted(set(l2on) - set(episodes_with_legs))},
        "stall_replay_bundles_with_rows": checks["stall_tsv_bundles"],
        "october_layer2_on_bundles_with_legs": sum(1 for e in episodes_with_legs
                                                   if not e.startswith("m5")),
    }

    # ---- fidelity (thesis R01-R03)
    fid = collections.Counter()
    for e, sheet in full.items():
        if key[e]["arm"] != "A":
            continue
        for r in sheet["fidelity"]["rows"]:
            if r.get("status") == "U:T1_no_record":
                continue
            fid["n"] += 1
            fid["as_written"] += r.get("as_written") == "reproduced"
            fid["plus_stage2_intents"] += r.get("plus_stage2_intents") == "reproduced"

    # ---- thesis values
    tv: dict[str, Any] = {}
    colmap = {"A": "A", "B": "B", "H": "H", "S": "S", "N": "N"}

    def put(pid: str, value: Any, source: str, note: str = "") -> None:
        tv[pid] = {"value": value, "source": source, **({"note": note} if note else {})}

    for c in COLUMNS:
        pt = primary_table[c]
        for cl in classes:
            if c == "B" and cl in ("V", "G"):
                continue
            put(f"TBD-T1-{cl}-{c}", f"{pt[cl]['units']} ({pt[cl]['episodes']})",
                f"reconciliation report, Table R1, row {cl}, column {COLUMN_NAMES[c]}")
        put(f"TBD-T1-TOT-{c}", f"{pt['total']['units']} ({pt['total']['episodes_with_unit']})",
            f"Table R1, total row, column {COLUMN_NAMES[c]}")
        put(f"TBD-T1-PARK-{c}", pt["parked_not_units"], f"Table R1, parked row, {COLUMN_NAMES[c]}")
        for cl in ("V", "G", "X", "EG"):
            if c == "B" and cl in ("V", "G"):
                continue
            put(f"TBD-T1-c{cl}-{c}", pt["contributing_intersection"][cl],
                f"Table R1c (contributing, codes both raters recorded), {COLUMN_NAMES[c]}",
                f"union of both raters' codes: {pt['contributing_union'][cl]}")
        if c != "B":
            put(f"TBD-T1-S1-{c}", None, "Table R1s (S1)",
                "Cannot be filled as defined: S1 is computed mechanically as a change of the "
                "command-unit link set; assigning a new primary would need re-rating, which the "
                f"protocol does not do. Units whose link set changes: "
                f"{sum(1 for x in s1 if x['column'] == c)}; of these, walk start moves: "
                f"{sum(1 for x in s1 if x['column'] == c and x['walk_start_moves'])}.")
        put(f"TBD-T1-S2-{c}", 0, "Table R1s (S2)",
            "Mechanical: S2 changes T2 only at the snapshots listed in Table R1s; none can change a "
            "primary (step 3 never assigns EG1/G7 because T1 is non-empty at every onset, and no "
            "changed decision snapshot lies before its unit's primary deviation on the walk).")
    for g, gcode in (("A", "A"), ("B", "B"), ("H", "H"), ("S", "S"), ("N", "N"), ("ALL", "ALL")):
        a = agree[gcode]
        put(f"TBD-T2-{g}-U", a["final"]["code"]["n"], f"Table R2, row {g}",
            "agreement on the raters' final codes (round 2 where in scope), before "
            "reconciliation; round-1 agreement is in the report beside it")
        put(f"TBD-T2-{g}-RC", a["final"]["class"]["raw"], f"Table R2, row {g}, final codes")
        put(f"TBD-T2-{g}-K", "n/a" if a["final"]["class"]["kappa"] is None
            else a["final"]["class"]["kappa"], f"Table R2, row {g}",
            "n/a: undefined (one category)" if a["final"]["class"]["kappa"] is None else "")
        put(f"TBD-T2-{g}-RF", a["final"]["code"]["raw"], f"Table R2, row {g}")
        put(f"TBD-T2-{g}-D", a["disagreements_final"], f"Table R2, row {g}")
        put(f"TBD-T2-{g}-DU", a["disagreements_left_U"], f"Table R2, row {g}")
    for p in ("A", "P", "N"):
        pan = panels[p]
        put(f"TBD-T3{p}-DEN-L", pan["legs"], f"Table R3, panel {p}, leg denominator")
        for m in ("ESC", "REV", "STL", "ANY"):
            mm = pan[m]
            put(f"TBD-T3{p}-{m}-L", mm["L"], f"Table R3, panel {p}, row {m}")
            put(f"TBD-T3{p}-{m}-J", mm["J"], f"Table R3, panel {p}, row {m}",
                f"contact or pinned {mm['contact_or_pinned']}, sub-margin graze {mm['submargin_graze']}")
            put(f"TBD-T3{p}-{m}-F", mm["F"], f"Table R3, panel {p}, row {m}")
            if m == "STL":
                put(f"TBD-T3{p}-{m}-UT", "n/a", f"Table R3, panel {p}, row {m}",
                    "Not defined for the stall abort: it fires only on a primitive that ran; a leg "
                    "that never reached an obstacle is either not fired or had no primitive.")
            else:
                put(f"TBD-T3{p}-{m}-UT", mm["UT"], f"Table R3, panel {p}, row {m}")
            put(f"TBD-T3{p}-{m}-P", mm["P"], f"Table R3, panel {p}, row {m}, primary chain rule")
            put(f"TBD-T3{p}-{m}-S", mm["S"], f"Table R3s, panel {p}, row {m}, S1")
        for rule, suf in (("primary", "P"), ("s1", "S")):
            cats = pan[f"categories_{rule}"]
            put(f"TBD-T3{p}-NONE-{suf}", cats.get("linked_none_intercepted", 0)
                + cats.get("no_linked_leg", 0), f"Table R3{'s' if suf == 'S' else ''}, panel {p}")
            put(f"TBD-T3{p}-NOL-{suf}", cats.get("no_linked_leg", 0),
                f"Table R3{'s' if suf == 'S' else ''}, panel {p}",
                "no linked leg among the 57 dispatched reverse/escort legs")
            put(f"TBD-T3{p}-LNI-{suf}", cats.get("linked_none_intercepted", 0),
                f"Table R3{'s' if suf == 'S' else ''}, panel {p}")
            put(f"TBD-T3{p}-TOT-{suf}", pan["units"], f"Table R3{'s' if suf == 'S' else ''}, panel {p}")
    put("TBD-R01", fid["as_written"], "full sheets fidelity rows, Layer-2-on episodes (ET table)")
    put("TBD-R02", fid["n"], "full sheets fidelity rows, Layer-2-on episodes (ET table)")
    put("TBD-R03", fid["plus_stage2_intents"], "full sheets fidelity rows (ET table, last column)")
    for pid, cols in (("TBD-R04", ("A",)), ("TBD-R05", ("B",)), ("TBD-R06", ("H", "S")),
                      ("TBD-R07", ("N",)), ("TBD-W01", ("A",)), ("TBD-W02", ("B",))):
        put(pid, sum(primary_table[c]["total"]["units"] for c in cols), "Table R1, total row")
    sentences = []
    for s, d in dominance.items():
        rc = d["reconciled"]["counts"]
        parts = ", ".join(f"{cl} {rc.get(cl, 0)}" for cl in ("V", "G", "X", "EG"))
        if s == "N":
            sentences.append(
                f"In the November takes ({d['units']} units), the {d['determined']} determined units "
                f"are both decision codes (V4) and {d['undetermined']} are undetermined; with four "
                "units this is not a finding about a dominant class.")
        elif s == "T":
            sentences.append(
                f"In tranche 1, no class has the most primary units in both raters' codes and after "
                f"reconciliation: of {d['units']} units {d['undetermined']} are undetermined, and the "
                f"{d['determined']} determined ones split {parts} (all in Arm A; "
                "the 10 Arm B units are undetermined for lack of a clock anchor).")
        else:
            sentences.append(
                f"In the {STRATUM_NAMES[s]}, no class has the most primary units in both raters' "
                f"codes and after reconciliation: of {d['units']} units "
                f"{d['undetermined']} are undetermined and the {d['determined']} determined ones "
                f"split {parts}.")
    put("TBD-R08", " ".join(sentences), "Table R1 and the dominance check (agreement.json)")
    al = agree["ALL"]["final"]["class"]
    put("TBD-R09", al["agree"], "Table R2, all strata (agreement statistic only)")
    put("TBD-R10", al["n"], "Table R2, all strata")
    put("TBD-R11", "n/a" if al["kappa"] is None else al["kappa"], "Table R2, all strata")
    put("TBD-R12", agree["ALL"]["disagreements_final"], "Table R2, all strata")
    put("TBD-R13", None, "Table R1s", "Cannot be filled as defined (no re-rating under S1). "
        f"Units whose link set changes, Layer-2-on strata: {len(s1)}; walk start moves: "
        f"{sum(x['walk_start_moves'] for x in s1)}.")
    put("TBD-R14", 0, "Table R1s (S2)", "Mechanical; see TBD-T1-S2-*.")
    put("TBD-R15", sum(panels[p]["ANY"]["P"] for p in ("A", "P", "N")), "Table R3, ANY rows summed",
        "per stratum: " + ", ".join(f"{p} {panels[p]['ANY']['P']}" for p in ("A", "P", "N")))
    put("TBD-R16", sum(panels[p]["units"] for p in ("A", "P", "N")), "Table R3, TOT summed",
        "per stratum: " + ", ".join(f"{p} {panels[p]['units']}" for p in ("A", "P", "N")))
    put("TBD-R17", sum(panels[p]["ANY"]["S"] for p in ("A", "P", "N")), "Table R3s, ANY rows summed",
        "per stratum: " + ", ".join(f"{p} {panels[p]['ANY']['S']}" for p in ("A", "P", "N")))
    for pid, fld in (("TBD-R18", "L"), ("TBD-R19", "J"), ("TBD-R20", "F"), ("TBD-R21", "UT")):
        put(pid, sum(panels[p]["ANY"][fld] for p in ("A", "P", "N")), f"Table R3, ANY rows, {fld}",
            "per stratum: " + ", ".join(f"{p} {panels[p]['ANY'][fld]}" for p in ("A", "P", "N")))
    put("TBD-R22", sum(panels[p]["categories_primary"].get("linked_none_intercepted", 0)
                       + panels[p]["categories_primary"].get("no_linked_leg", 0)
                       for p in ("A", "P", "N")), "Table R3, NONE rows summed",
        "per stratum: " + ", ".join(
            f"{p} {panels[p]['categories_primary'].get('linked_none_intercepted', 0) + panels[p]['categories_primary'].get('no_linked_leg', 0)}"
            for p in ("A", "P", "N")))
    for pid in ("TBD-R23", "TBD-R24", "TBD-R25", "TBD-R26", "TBD-R27"):
        put(pid, None, "PV section 6 (plan-dispatch mismatch visibility report)",
            "Not a reconciliation output: the value comes from the PV recomputation on "
            "fix/plan-dispatch-mismatch-visibility, which this task did not read or rerun.")
    put("TBD-E01", "docs/reports/2026-11-15-failure-cause-reconciliation.md (branch "
        "analysis/failure-cause-classification; commit filled in by the follow-up commit)",
        "git log of the report")
    ids = _thesis_ids()
    checks["thesis_ids_in_change_list"] = len(ids)
    checks["thesis_ids_missing"] = sorted(set(ids) - set(tv))
    checks["thesis_ids_extra"] = sorted(set(tv) - set(ids))
    for pid in checks["thesis_ids_missing"]:
        put(pid, "n/a by construction" if pid in ("TBD-T1-V-B", "TBD-T1-G-B") else None,
            "not produced", "placeholder not mapped")

    # ---- write
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reconciled_units.json").write_text(json.dumps({
        "rubric": "b70d925 section 7", "protocol": "b7a3d25", "round2_note": "89d9bf3..8671843",
        "rulings": RULINGS, "units": ulist, "parked_not_units": parked,
        "episode_primary": ep_primary,
    }, indent=1, default=list))
    (OUT / "agreement.json").write_text(json.dumps({
        "rating_file_md5": rater_md5, "agreement": agree, "disagreements_final": disagreements,
        "disagreements_s3": s3_disagreements, "disagreements_round1": r1_dis,
        "dominance_check": dominance,
    }, indent=1, default=list))
    (OUT / "tables.json").write_text(json.dumps({
        "primary_table": primary_table, "s1": s1, "s2": s2_rows, "rule_properties": rule_props,
        "interception_panels": panels, "denominator": denominator,
        "stall_fires_outside_57_legs": extra_fires, "fidelity": dict(fid), "checks": checks,
    }, indent=1, default=list))
    (OUT / "thesis_values.json").write_text(json.dumps(dict(sorted(tv.items())), indent=1))
    cols = ["episode", "stratum", "column", "leg_id", "kind", "m4_terminal", "gt_moved_max_m",
            "min_static_gap_m", "min_robot_gap_m", "pinned_on", "ended_by_deadline", "physical",
            "physical_box",
            "escort_guard_refuses", "reverse_guard_refuses", "guard_leg_role", "guard_outcome",
            "stall_abort_fires", "stall_time_to_abort_s", "stall_outcome",
            "stall_differs_from_provisional", "caught_by", "fu_primary_chain", "fu_s1",
            "not_caught_reason", "guard_verdict", "stall_replay"]
    (OUT / "interception_by_leg.tsv").write_text("\n".join(
        ["\t".join(cols)] + ["\t".join(str(r[c]) for c in cols) for r in leg_rows]) + "\n")
    ucols = list(unit_rows[0].keys())
    (OUT / "interception_by_unit.tsv").write_text("\n".join(
        ["\t".join(ucols)] + ["\t".join(str(r[c]) for c in ucols) for r in unit_rows]) + "\n")
    print(json.dumps(checks, indent=1, default=list))


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("geometry")
    sub.add_parser("build")
    args = ap.parse_args()
    if args.cmd == "geometry":
        cmd_geometry()
    else:
        cmd_build()


if __name__ == "__main__":
    main()

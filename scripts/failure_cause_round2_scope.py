"""Round-2 in-scope unit list for the failure-cause rating (Round-2 note, scope section).

Reads the round-2 evidence (`full_round2/`, `key/key.json`) and both raters'
round-1 records (`ratings/rater_{A,B}/phase2_events.json`); writes only
`rater_round2/in_scope_units.json` (rater-facing: sheet, unit, criteria,
decision ids) and `full_round2/scope_detail.json` (with per-rater sources and
round-1 codes). It never modifies a rating file. The evidence tool
(`failure_cause_evidence.py`) does not read ratings; only this step does.

Criteria (identical for both raters):

- (a) a decision with a new round-2 T1 row lies on the unit's walk: at or after
  the mechanical walk start (chain start if the chain rule fires, else t0), or
  is on the unit's timeline and named by either rater's round-1 record for that
  unit (rows for decisions before the timeline start never count);
- (b) T1 at onset was `U:T1_fidelity` as written;
- (c) the unit is on a sheet without an m4 clock anchor, only when the
  scene-log mapping is applied (`--with-clock`).

Usage:
    python -B scripts/failure_cause_round2_scope.py --out <evidence dir> [--with-clock]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_DREF = re.compile(r"\bD(\d+)\b")


def rater_decision_refs(record: dict[str, Any]) -> set[str]:
    """D-ids named anywhere in one rater record (evidence, event codes, notes)."""
    return {f"D{m}" for m in _DREF.findall(json.dumps(record))}


def unit_scope(
    unit: dict[str, Any], new_rows: dict[str, float], refs: dict[str, set[str]],
    with_clock: bool, no_anchor_sheet: bool,
) -> dict[str, Any]:
    """Criteria (a)/(b)/(c) for one unit.

    Args:
        unit: Round-2 unit (`t0_rel`, `chain_start_rel`, `t0_fidelity_both_ways`).
        new_rows: D-id -> t_rel of the unit's new T1 snapshots on its timeline.
        refs: rater name -> D-ids that rater's record for this unit names.
        with_clock: Whether the scene-log clock mapping is applied.
        no_anchor_sheet: Whether the sheet has no m4 clock anchor.

    Returns:
        `criteria` (sorted list of a/b/c), `a_decisions`, and per-source detail.
    """
    start = unit["chain_start_rel"] if unit.get("chain_start_rel") is not None else unit["t0_rel"]
    mech = sorted((d for d, t in new_rows.items() if t >= start - 1e-9),
                  key=lambda d: new_rows[d])
    by_rater = {r: sorted(set(new_rows) & ids, key=lambda d: new_rows[d]) for r, ids in refs.items()}
    a = sorted(set(mech).union(*by_rater.values()), key=lambda d: new_rows[d]) if new_rows else []
    crit = []
    if a:
        crit.append("a")
    if unit.get("t0_fidelity_both_ways"):
        crit.append("b")
    if with_clock and no_anchor_sheet:
        crit.append("c")
    return {"criteria": crit, "a_decisions": a, "a_mechanical": mech, "a_by_rater": by_rater,
            "walk_start_mechanical_rel": start}


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--with-clock", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    key = json.loads((out / "key" / "key.json").read_text())
    raters = {}
    for r in ("A", "B"):
        recs = json.loads((out / "ratings" / f"rater_{r}" / "phase2_events.json").read_text())
        raters[r] = {(x["sheet_id"], x["unit_id"]): x for x in recs["records"]}
    rater_list, detail = [], []
    for lab, ids in sorted(key.items(), key=lambda kv: kv[1]["events_id"]):
        r2 = json.loads((out / "full_round2" / lab / "round2.json").read_text())
        did = {v: k for k, v in ids["decision_ids"].items()}
        no_anchor = r2["clock"]["m4_fit"] is None
        for fu, u in r2["units"].items():
            new_rows = {did[rid]: s["t_rel"] for rid, s in u["t1_new_snapshots"].items()
                        if s["on_timeline"]}
            recs = {r: raters[r].get((ids["events_id"], fu)) for r in raters}
            refs = {r: rater_decision_refs(x) if x else set() for r, x in recs.items()}
            sc = unit_scope(u, new_rows, refs, args.with_clock, no_anchor)
            rater_refs_without_t1 = {
                r: sorted(x for x in v if x not in new_rows) for r, v in refs.items()}
            row = {"sheet_id": ids["events_id"], "unit_id": fu, **sc,
                   "round1_primary": {r: (x or {}).get("primary_code") for r, x in recs.items()},
                   "rater_refs_without_new_row": rater_refs_without_t1}
            detail.append({"label": lab, **row})
            if sc["criteria"]:
                rater_list.append({"sheet_id": ids["events_id"], "unit_id": fu,
                                   "criteria": sc["criteria"], "decisions_a": sc["a_decisions"]})
    (out / "rater_round2" / "in_scope_units.json").write_text(json.dumps({
        "rule": "Round-2 note, scope section: (a) walk passes a decision with a new T1 row; "
                "(b) T1 at onset U:T1_fidelity as written; (c) clock mapping applied "
                f"({'applied' if args.with_clock else 'not applied, so (c) is empty'}).",
        "n_in_scope": len(rater_list), "units": rater_list}, indent=1))
    (out / "full_round2" / "scope_detail.json").write_text(json.dumps(detail, indent=1))
    print(f"in scope {len(rater_list)} of {len(detail)} units")


if __name__ == "__main__":
    main()

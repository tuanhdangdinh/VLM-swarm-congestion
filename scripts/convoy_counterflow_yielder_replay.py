#!/usr/bin/env python3
"""Offline replay of the counterflow yielder swap (2026-11-15). No model calls.

Report: docs/reports/2026-11-15-convoy-non-arrival-and-yielder-feasibility.md.

Grounds recorded decisions through M5's in-process pipeline in three arms:
``off`` (both keys off), ``hold`` (`hold_queued_crossers` only, the
`fix/convoy-hold-queued-robots` behaviour) and ``fix`` (hold plus
`yield_counterflow_swap`). It reuses the queued-crosser replay's stimuli,
pipeline construction and comparison fields
(`scripts/convoy_queued_crosser_replay.py`), never calls a backend and never
writes into the bundles or into another experiment's directory.

Parts:

* ``first``: the first-trigger decisions of live convoy takes 1-5 (takes 4-5
  from the `cvh` kit, recorded with the hold on), the scripted smoke and the
  44 stored prompt-check answers.
* ``later``: every later recorded decision of the five convoy takes.
* ``other``: every recorded decision of the head-on, intersection and
  five-robot campaign bundles.

Usage:
    python scripts/convoy_counterflow_yielder_replay.py {first,later,other} --docs-root <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convoy_held_robot_plan_check as cv  # noqa: E402
import convoy_queued_crosser_replay as rp  # noqa: E402
import vlm_order_channel_plan_check as pc  # noqa: E402

from reasoning.vlm.models import ReasonerResult  # noqa: E402

EXPERIMENT = "2026-11-15-convoy-counterflow-yielder-replay"
DEFAULT_OUT = pc.REPO_ROOT / "data" / "experiments" / EXPERIMENT
HOLD_REPLAY = pc.REPO_ROOT / "data" / "experiments" / rp.EXPERIMENT
CAMPAIGN = rp.CAMPAIGN
HOLD_TAKES = ("cvH_t04_a2", "cvH_t05_a1")
ARMS = {"off": (False, False), "hold": (True, False), "fix": (True, True)}
# The smoke's executed order (v7f cvL_e01_armC_a1): yield robot_2, then the
# platoon nose to tail.
RESOLVING = {"yielder": "robot_2", "crossing_order": ["robot_1", "robot_3", "robot_4"],
             "linked": {"robot_1": 0, "robot_3": 1, "robot_4": 2}}


def make_pipeline(s: pc.Stimulus, hold: bool, swap: bool) -> pc.InProcessPipeline:
    """`rp.make_pipeline` with the counterflow key."""
    cfg = s.config
    return pc.InProcessPipeline(
        reasoner=None,
        ground_fn=pc.ground_reasoner_result,
        scene_geometry=cfg.scenario_geometry,
        static_obstacles=cfg.static_obstacles,
        yield_feasibility_mode=s.yfm,
        grounding_params=s.params,
        retreat_chooser=None,
        stage2_enabled=cfg.stage2_retreat_selection,
        candidate_marker=None,
        priorities=pc.registry_priorities(cfg.initial_tasks),
        plan_tracker=pc.PlanTracker() if cfg.plan_channel_enabled else None,
        registry_order=tuple(cfg.initial_tasks),
        dispatch_order_source=s.artifact.get("plan_dispatch_order_source") or "chi",
        hold_queued_crossers=hold,
        yield_counterflow_swap=swap,
    )


def run_arms(s: pc.Stimulus, request: Any, result: ReasonerResult) -> dict[str, Any]:
    """The outcome per arm."""
    return {
        arm: make_pipeline(s, hold, swap)._run_from_result(request, result)
        for arm, (hold, swap) in ARMS.items()
    }


def structure(cmd: dict[str, Any] | None) -> dict[str, Any] | None:
    """Yielder, crossing order and linked waits of a grounded yield."""
    if cmd is None:
        return None
    yields = [a for a in cmd["actions"] if a["action"] == "yield"]
    if len(yields) != 1:
        return {"kind": ",".join(sorted({a["action"] for a in cmd["actions"]}))}
    p = yields[0]["parameters"]
    return {
        "kind": "yield",
        "yielder": yields[0]["robot_id"],
        "crossing_order": p.get("crossing_order") or [p.get("passer_robot_id")],
        "linked": {
            a["robot_id"]: a["parameters"]["linked_position"]
            for a in cmd["actions"]
            if a["action"] == "temporary_wait" and "linked_position" in a["parameters"]
        },
        "grounded_from": p.get("yield_robot_grounded_from"),
        "regrounded_reason": p.get("yield_regrounded_reason"),
    }


def resolving(st: dict[str, Any] | None) -> bool:
    """The smoke-shaped sequence: yielder, order and linked waits."""
    return st is not None and all(st.get(k) == v for k, v in RESOLVING.items())


def _first_answers(docs: Path) -> list[tuple[str, str, pc.Stimulus, Any, ReasonerResult]]:
    stimuli = {s.request_id: s for s in cv.load_stimuli(docs)}
    answers = []
    for s in stimuli.values():
        answers.append((f"recorded:{s.cls}", "C", s, s.request("C"), pc.recorded_result(s)))
    for take in HOLD_TAKES:
        bundle = docs / CAMPAIGN / "cvh" / "runs" / take
        arts = [json.loads(p.read_text()) for p in sorted((bundle / "decisions").glob("*.json"))]
        arts.sort(key=lambda a: (a.get("scene") or {}).get("stamp") or 0.0)
        s = rp._stimulus_for(bundle, arts[0], str(bundle.relative_to(docs)))
        answers.append(("recorded:live_cvH", "C", s, s.base_request(), pc.recorded_result(s)))
    for line in (rp.PROMPT_CHECK / "calls.jsonl").read_text().splitlines():
        rec = json.loads(line)
        s = stimuli[rec["request_id"]]
        answers.append((f"stored:{rec['key']}", rec["condition"], s, s.request(rec["condition"]),
                        ReasonerResult(**rec["result"])))
    return answers


def cmd_first(args: argparse.Namespace) -> int:
    """First triggers: three arms, the smoke comparison, the gates."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    answers = _first_answers(Path(args.docs_root))
    smoke = next(a for a in answers if a[0] == "recorded:smoke_armC")
    smoke_cmd = smoke[2].artifact["dispatched_command"]
    committed = {}
    for line in (HOLD_REPLAY / "first.jsonl").read_text().splitlines():
        r = json.loads(line)
        committed[(r["source"], r["episode"], r["condition"])] = r
    rows = []
    for source, condition, s, request, result in answers:
        dec = result.decision
        row: dict[str, Any] = {"source": source, "condition": condition, "episode": s.label,
                               "cls": s.cls}
        if dec is None or not dec.congestion_detected:
            row["valid"] = False
            rows.append(row)
            continue
        outcomes = run_arms(s, request, result)
        row.update({"valid": True, "strategy": dec.strategy, "model_yielder": dec.yield_robot,
                    "involved": sorted(dec.involved_robots)})
        for arm, o in outcomes.items():
            r = rp.outcome_row(o)
            row[arm] = {**r, "struct": structure(o.grounded_command)}
        recorded = s.artifact.get("dispatched_command")
        rec_sig = pc.command_sig(recorded)
        reproduce_arm = "hold" if source == "recorded:live_cvH" else "off"
        if source.startswith("recorded:"):
            row["reproduces_recorded"] = {
                "arm": reproduce_arm,
                "ok": pc.command_sig(outcomes[reproduce_arm].grounded_command) == rec_sig,
            }
        prior = committed.get((source, s.label, condition))
        if prior is not None:
            # Compared after a JSON round trip (the committed rows were read back).
            row["hold_equals_committed_on"] = prior["on"]["sig"] == json.loads(
                json.dumps(row["hold"]["sig"], default=str)
            )
        fix_cmd = outcomes["fix"].grounded_command
        st = row["fix"]["struct"]
        row["fix_resolving"] = resolving(st)
        if fix_cmd is not None and st and st.get("kind") == "yield":
            mine, ref = rp.gate_fields(fix_cmd), rp.gate_fields(smoke_cmd)
            row["fix_vs_smoke_diff"] = {k: [mine[k], ref[k]] for k in mine if mine[k] != ref[k]}
            # The fix's command for a swapped answer must equal hold-only
            # grounding of the same answer with the feasible yielder named.
            if st.get("grounded_from") is not None:
                named = result.model_copy(update={"decision": dec.model_copy(
                    update={"yield_robot": st["yielder"],
                            "involved_robots": [st["yielder"], *[r for r in dec.involved_robots
                                                                if r != st["yielder"]]],
                            "crossing_order": None})})
                direct = make_pipeline(s, True, False)._run_from_result(request, named)
                row["fix_equals_hold_of_feasible_yielder"] = (
                    _strip(fix_cmd) == _strip(direct.grounded_command)
                )
        rows.append(row)
    (out / "first.jsonl").write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))
    summary = summarize_first(rows)
    (out / "first_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


def _strip(cmd: dict[str, Any] | None) -> Any:
    if cmd is None:
        return None
    actions = []
    for a in cmd["actions"]:
        p = {k: v for k, v in a.get("parameters", {}).items()
             if k not in ("yield_robot_grounded_from", "yield_regrounded_reason", "plan_id")}
        actions.append({**a, "parameters": p})
    tags = [t for t in cmd.get("degradations", []) if not t.startswith("yield=counterflow")]
    return {**{k: v for k, v in cmd.items() if k != "degradations"}, "actions": actions,
            "degradations": tags}


def summarize_first(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts per group and model yielder."""
    table: dict[str, Any] = {}
    for r in rows:
        group = r["source"].split(":")[0] if r["source"].startswith("recorded") else (
            f"stored|{r['condition']}|{r['cls']}")
        if r["source"].startswith("recorded"):
            group = r["source"]
        if not r.get("valid"):
            table.setdefault(group, {}).setdefault("invalid", 0)
            table[group]["invalid"] += 1
            continue
        key = f"{group}|model={r['model_yielder'] if r['strategy'] == 'yield' else r['strategy']}"
        t = table.setdefault(group, {}).setdefault(key, {
            "n": 0, "resolving": {a: 0 for a in ARMS}, "swapped_fix": 0, "refused_fix": 0,
            "prov_fix": {}, "match_fix": 0, "equals_hold_feasible": 0, "edits_fix": {},
            "reproduces_recorded": 0, "hold_equals_committed_on": 0, "fix_yielder": {}})
        t["n"] += 1
        for arm in ARMS:
            t["resolving"][arm] += int(resolving(r[arm]["struct"]))
        st = r["fix"]["struct"] or {}
        t["fix_yielder"][str(st.get("yielder"))] = t["fix_yielder"].get(str(st.get("yielder")), 0) + 1
        t["swapped_fix"] += int(st.get("grounded_from") is not None)
        t["refused_fix"] += int(any("counterflow_refused" in d for d in r["fix"]["degradations"] or []))
        p = str(r["fix"]["provenance"])
        t["prov_fix"][p] = t["prov_fix"].get(p, 0) + 1
        t["match_fix"] += int(bool(r["fix"]["dispatch_matches_plan"]))
        t["equals_hold_feasible"] += int(bool(r.get("fix_equals_hold_of_feasible_yielder")))
        ops = ",".join(sorted(e[0] for e in r["fix"]["edits"] or [])) or "none"
        t["edits_fix"][ops] = t["edits_fix"].get(ops, 0) + 1
        t["reproduces_recorded"] += int(bool((r.get("reproduces_recorded") or {}).get("ok")))
        t["hold_equals_committed_on"] += int(bool(r.get("hold_equals_committed_on")))
    return table


def replay_bundles(docs: Path, rels: list[str], skip_first: bool) -> list[dict[str, Any]]:
    """Hold vs fix (and off) for every (or every later) recorded decision."""
    rows = []
    for rel in rels:
        bundle = docs / rel
        arts = [json.loads(p.read_text()) for p in sorted((bundle / "decisions").glob("*.json"))]
        arts.sort(key=lambda a: (a.get("scene") or {}).get("stamp") or 0.0)
        for idx, art in enumerate(arts):
            if skip_first and idx == 0:
                continue
            s = rp._stimulus_for(bundle, art, rel)
            result = pc.recorded_result(s)
            row: dict[str, Any] = {"bundle": bundle.name, "request_id": art["request_id"][:8],
                                   "stamp": (art.get("scene") or {}).get("stamp"),
                                   "mode": art.get("grounding_mode")}
            dec = result.decision
            if dec is None or not dec.congestion_detected:
                row["skipped"] = "no congestion decision"
                rows.append(row)
                continue
            outcomes = run_arms(s, s.base_request(), result)
            o = {arm: rp.outcome_row(x) for arm, x in outcomes.items()}
            recorded_arm = "hold" if bundle.name in HOLD_TAKES else "off"
            row.update({
                "strategy": dec.strategy,
                "recorded_arm": recorded_arm,
                "recorded_reproduced": pc.command_sig(outcomes[recorded_arm].grounded_command)
                == pc.command_sig(art.get("dispatched_command")),
                "fix_kind": o["fix"]["structure"]["kind"],
                "fix_identical_to_hold": o["fix"] == o["hold"],
                "fix_identical_to_off": o["fix"] == o["off"],
                "diff_hold_fix": {k: [o["hold"][k], o["fix"][k]] for k in o["fix"]
                                  if o["fix"][k] != o["hold"][k]},
            })
            rows.append(row)
    return rows


def _write(out: Path, name: str, rows: list[dict[str, Any]]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.jsonl").write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))
    done = [r for r in rows if "skipped" not in r]
    summary = {
        "decisions": len(rows),
        "replayed": len(done),
        "fix_identical_to_hold": sum(r["fix_identical_to_hold"] for r in done),
        "fix_identical_to_off": sum(r["fix_identical_to_off"] for r in done),
        "recorded_reproduced": sum(r["recorded_reproduced"] for r in done),
        "per_bundle": {},
        "changed": [r for r in done if not r["fix_identical_to_hold"]],
    }
    for r in done:
        b = summary["per_bundle"].setdefault(r["bundle"], {"n": 0, "fix_eq_hold": 0, "repro": 0})
        b["n"] += 1
        b["fix_eq_hold"] += int(r["fix_identical_to_hold"])
        b["repro"] += int(r["recorded_reproduced"])
    (out / f"{name}_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "changed"}, indent=1))
    for c in summary["changed"]:
        print(json.dumps(c, default=str)[:800])


def cmd_later(args: argparse.Namespace) -> int:
    """Later recorded decisions of the five convoy takes."""
    rels = [f"{CAMPAIGN}/cv/runs/{t}" for t in rp.CONVOY_TAKES]
    rels += [f"{CAMPAIGN}/cvh/runs/{t}" for t in HOLD_TAKES]
    _write(Path(args.out), "later", replay_bundles(Path(args.docs_root), rels, skip_first=True))
    return 0


def cmd_other(args: argparse.Namespace) -> int:
    """Head-on, intersection and five-robot campaign bundles."""
    root = Path(args.docs_root)
    rels = []
    for scn in ("ho", "ib", "m5"):
        for d in sorted((root / CAMPAIGN / scn / "runs").glob(f"{scn}D_t*_a*")):
            if d.is_dir() and (d / "decisions").is_dir():
                rels.append(str(d.relative_to(root)))
    _write(Path(args.out), "other", replay_bundles(root, rels, skip_first=False))
    return 0


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("first", "later", "other"):
        p = sub.add_parser(name)
        p.add_argument("--docs-root", required=True)
        p.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    return {"first": cmd_first, "later": cmd_later, "other": cmd_other}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

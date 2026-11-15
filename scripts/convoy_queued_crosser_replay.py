#!/usr/bin/env python3
"""Offline replay of the queued corridor-crosser hold (2026-11-15). No model calls.

Report: docs/reports/2026-11-15-convoy-queued-crosser-hold.md.

Grounds recorded decisions through M5's in-process pipeline (`InProcessPipeline.
_run_from_result`, the artifact's own config and grounding params, a fresh plan
tracker, no stage-2 call) twice, with `hold_queued_crossers` off and on, and
compares. It reuses the plan-check runner's `Stimulus` rebuild and signatures
(`scripts/vlm_order_channel_plan_check.py`) and the convoy check's stimuli and
structure classifier (`scripts/convoy_held_robot_plan_check.py`). It never
calls a backend and never writes into the bundles or the prompt-check data.

Parts:

* ``first``: the three live takes' recorded first decisions, the scripted
  smoke decision and the 44 stored prompt-check answers
  (`data/experiments/2026-11-15-convoy-held-robot-prompt-check/calls.jsonl`)
  on their first-trigger snapshots.
* ``later``: every later recorded decision of the three convoy takes, on its
  own recorded snapshot.
* ``other``: every recorded decision of the head-on, intersection and
  five-robot campaign bundles.

Usage:
    python scripts/convoy_queued_crosser_replay.py first --docs-root <dir>
    python scripts/convoy_queued_crosser_replay.py later --docs-root <dir>
    python scripts/convoy_queued_crosser_replay.py other --docs-root <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convoy_held_robot_plan_check as cv  # noqa: E402
import vlm_order_channel_plan_check as pc  # noqa: E402

from reasoning.rag.command_grounder import QUEUED_CROSSER_PREFIX  # noqa: E402
from reasoning.vlm.models import CongestionDecision, ReasonerResult  # noqa: E402

EXPERIMENT = "2026-11-15-convoy-queued-crosser-replay"
DEFAULT_OUT = pc.REPO_ROOT / "data" / "experiments" / EXPERIMENT
PROMPT_CHECK = pc.REPO_ROOT / "data" / "experiments" / cv.EXPERIMENT
CAMPAIGN = "vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign"
CONVOY_TAKES = ("cvD_t01_a1", "cvD_t02_a1", "cvD_t03_a1")


def make_pipeline(s: pc.Stimulus, hold: bool) -> pc.InProcessPipeline:
    """`pc.make_pipeline` with the artifact's dispatch-order mode and the hold key."""
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
    )


def outcome_row(outcome: Any) -> dict[str, Any]:
    """The fields compared between key off and key on."""
    cmd = outcome.grounded_command
    plan = outcome.plan
    return {
        "terminal": str(outcome.terminal_stage),
        "failure": outcome.failure_reason,
        "structure": cv.classify(cmd),
        "sig": pc.outcome_sig(outcome),
        "degradations": None if cmd is None else cmd.get("degradations"),
        "provenance": None if plan is None else plan.provenance,
        "edits": (
            None if plan is None else [(e.op, list(e.robot_ids), e.reason) for e in plan.edits]
        ),
        "dispatch_matches_plan": None if plan is None else plan.dispatch_matches_plan,
        "plan_legs": None if plan is None else [(leg.robot_id, leg.action) for leg in plan.legs],
    }


def both(s: pc.Stimulus, request: Any, result: ReasonerResult) -> tuple[Any, Any]:
    """The outcome with the key off and with it on."""
    off = make_pipeline(s, False)._run_from_result(request, result)
    on = make_pipeline(s, True)._run_from_result(request, result)
    return off, on


def all_four(s: pc.Stimulus, result: ReasonerResult, yielder: str) -> ReasonerResult:
    """The same answer with the decision naming all four robots, passer first."""
    dec = result.decision
    passer = "robot_1" if yielder == "robot_2" else "robot_2"
    named = CongestionDecision(
        **{
            **dec.model_dump(),
            "involved_robots": list(cv.ALL_FOUR),
            "yield_robot": yielder,
            "crossing_order": [passer, "robot_3", "robot_4", yielder],
        }
    )
    return result.model_copy(update={"decision": named})


def _strip_trace(cmd: dict[str, Any]) -> dict[str, Any]:
    out = []
    for a in cmd["actions"]:
        p = {k: v for k, v in a.get("parameters", {}).items()
             if k not in ("queued_crossers_added", "plan_id")}
        out.append({**a, "parameters": p})
    return {**{k: v for k, v in cmd.items() if k != "degradations"}, "actions": out}


def gate_fields(cmd: dict[str, Any]) -> dict[str, Any]:
    """Robots, actions, linked positions and the yield's gate parameters."""
    y = next(a for a in cmd["actions"] if a["action"] == "yield")
    p = y["parameters"]
    return {
        "robots": sorted(a["robot_id"] for a in cmd["actions"]),
        "actions": {a["robot_id"]: a["action"] for a in cmd["actions"]},
        "linked_position": {
            a["robot_id"]: a["parameters"].get("linked_position")
            for a in cmd["actions"] if a["action"] == "temporary_wait"
        },
        "wait_duration_sec": sorted({
            a["parameters"].get("duration_sec")
            for a in cmd["actions"] if a["action"] == "temporary_wait"
        }),
        "yielder": y["robot_id"],
        "yield_keys": sorted(
            k for k in p if k not in ("plan_id", "queued_crossers_added", "reason")
        ),
        **{k: p.get(k) for k in (
            "crossing_order", "passer_robot_id", "backup_distance_m", "park_coord_m",
            "pull_off_lateral_m", "hold_sec", "passer_clear_m", "crossing_clear_m",
        )},
        "expected_resolution_time_sec": cmd["expected_resolution_time_sec"],
    }


def cmd_first(args: argparse.Namespace) -> int:
    """Part 1: first-trigger answers, off vs on, and the smoke comparison."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stimuli = {s.request_id: s for s in cv.load_stimuli(Path(args.docs_root))}
    smoke = next(s for s in stimuli.values() if s.cls == "smoke_armC")
    smoke_cmd = smoke.artifact["dispatched_command"]
    rows: list[dict[str, Any]] = []
    answers: list[tuple[str, str, pc.Stimulus, Any, ReasonerResult]] = []
    for s in stimuli.values():
        answers.append((f"recorded:{s.cls}", "C", s, s.request("C"), pc.recorded_result(s)))
    for line in (PROMPT_CHECK / "calls.jsonl").read_text().splitlines():
        rec = json.loads(line)
        s = stimuli[rec["request_id"]]
        answers.append((f"stored:{rec['key']}", rec["condition"], s, s.request(rec["condition"]),
                        ReasonerResult(**rec["result"])))
    for source, condition, s, request, result in answers:
        dec = result.decision
        row: dict[str, Any] = {"source": source, "condition": condition, "episode": s.label,
                               "cls": s.cls}
        if dec is None or not dec.congestion_detected:
            row["valid"] = False
            rows.append(row)
            continue
        off, on = both(s, request, result)
        row.update({"valid": True, "strategy": dec.strategy, "yield_robot": dec.yield_robot,
                    "involved": sorted(dec.involved_robots), "off": outcome_row(off),
                    "on": outcome_row(on)})
        if source.startswith("recorded:"):
            row["off_reproduces_recorded"] = (
                pc.command_sig(off.grounded_command)
                == pc.command_sig(s.artifact.get("dispatched_command"))
            )
        g = row["on"]["structure"]
        if g.get("full_sequence") and on.grounded_command is not None:
            named = make_pipeline(s, False)._run_from_result(
                request, all_four(s, result, g["yielder"])
            )
            row["on_equals_all_four_named"] = (
                _strip_trace(on.grounded_command) == _strip_trace(named.grounded_command)
            )
            mine, ref = gate_fields(on.grounded_command), gate_fields(smoke_cmd)
            row["vs_smoke_diff"] = {k: [mine[k], ref[k]] for k in mine if mine[k] != ref[k]}
            row["on_edits_all_prefixed"] = all(
                e[2].startswith(QUEUED_CROSSER_PREFIX) for e in row["on"]["edits"] or []
            )
        rows.append(row)
    (out / "first.jsonl").write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))
    summary = summarize_first(rows)
    (out / "first_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


def summarize_first(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts per group: full sequence off/on by yielder, provenance, plan match."""
    table: dict[str, Any] = {}
    for r in rows:
        if r["source"].startswith("recorded:"):
            groups = [f"recorded|{r['cls']}"]
        else:
            groups = [f"stored|{r['condition']}|{r['cls']}", f"stored|all|{r['cls']}"]
        for key in groups:
            t = table.setdefault(key, {"n": 0, "valid": 0, "full_off": 0, "full_on": 0,
                                       "full_on_y2": 0, "full_on_y1": 0, "yielder_on": {},
                                       "prov_off": {}, "prov_on": {}, "match_on": 0,
                                       "equals_all_four": 0, "edits_prefixed": 0,
                                       "withheld": 0, "kind_on": {}})
            t["n"] += 1
            if not r.get("valid"):
                continue
            t["valid"] += 1
            off, on = r["off"], r["on"]
            t["full_off"] += int(bool(off["structure"].get("full_sequence")))
            y = on["structure"].get("yielder")
            t["yielder_on"][str(y)] = t["yielder_on"].get(str(y), 0) + 1
            t["kind_on"][on["structure"]["kind"]] = t["kind_on"].get(on["structure"]["kind"], 0) + 1
            if on["structure"].get("full_sequence"):
                t["full_on"] += 1
                t["full_on_y2"] += int(y == "robot_2")
                t["full_on_y1"] += int(y == "robot_1")
            for side, k in ((off, "prov_off"), (on, "prov_on")):
                p = str(side["provenance"])
                t[k][p] = t[k].get(p, 0) + 1
            t["match_on"] += int(bool(on["dispatch_matches_plan"]))
            t["equals_all_four"] += int(bool(r.get("on_equals_all_four_named")))
            t["edits_prefixed"] += int(bool(r.get("on_edits_all_prefixed")))
            t["withheld"] += int(any("augment_withheld" in d for d in on["degradations"] or []))
    return table


def _stimulus_for(bundle: Path, art: dict[str, Any], rel: str) -> pc.Stimulus:
    config = pc.load_config(yaml.safe_load((bundle / "orchestrator.overlaid.yaml").read_text()))
    params = pc.GroundingParams(**art["grounding_params_source"]["params"])
    yfm = art.get("grounding_yield_feasibility") or config.grounding_yield_feasibility
    frame = bundle / "frames" / f"{art['request_id']}.png"
    return pc.Stimulus("replay", bundle, rel, art["request_id"], art, config, params, yfm, frame)


def replay_bundles(docs_root: Path, rels: list[str], skip_first: bool) -> list[dict[str, Any]]:
    """Off vs on for every (or every later) recorded decision of each bundle, one at a time."""
    rows = []
    for rel in rels:
        bundle = docs_root / rel
        arts = [json.loads(p.read_text()) for p in sorted((bundle / "decisions").glob("*.json"))]
        arts.sort(key=lambda a: (a.get("scene") or {}).get("stamp") or 0.0)
        for idx, art in enumerate(arts):
            if skip_first and idx == 0:
                continue
            s = _stimulus_for(bundle, art, rel)
            result = pc.recorded_result(s)
            row: dict[str, Any] = {"bundle": bundle.name, "request_id": art["request_id"][:8],
                                   "stamp": (art.get("scene") or {}).get("stamp"),
                                   "mode": art.get("grounding_mode")}
            dec = result.decision
            if dec is None or not dec.congestion_detected:
                row["skipped"] = "no congestion decision"
                rows.append(row)
                continue
            request = s.base_request()
            off, on = both(s, request, result)
            o, n = outcome_row(off), outcome_row(on)
            row.update({
                "strategy": dec.strategy, "involved": sorted(dec.involved_robots),
                "recorded_sig_reproduced_off": pc.command_sig(off.grounded_command)
                == pc.command_sig(art.get("dispatched_command")),
                "off_kind": o["structure"]["kind"], "on_kind": n["structure"]["kind"],
                "identical": o == n,
                "diff": {k: [o[k], n[k]] for k in o if o[k] != n[k]},
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
        "identical": sum(r["identical"] for r in done),
        "recorded_reproduced_off": sum(r["recorded_sig_reproduced_off"] for r in done),
        "changed": [
            {k: r[k] for k in ("bundle", "request_id", "stamp", "strategy", "off_kind",
                               "on_kind", "diff")}
            for r in done if not r["identical"]
        ],
    }
    (out / f"{name}_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "changed"}))
    for c in summary["changed"]:
        print(json.dumps(c, default=str)[:600])


def cmd_later(args: argparse.Namespace) -> int:
    """Part 2: later recorded decisions of the three convoy takes."""
    rels = [f"{CAMPAIGN}/cv/runs/{t}" for t in CONVOY_TAKES]
    _write(Path(args.out), "later", replay_bundles(Path(args.docs_root), rels, skip_first=True))
    return 0


def cmd_other(args: argparse.Namespace) -> int:
    """Part 3: head-on, intersection and five-robot campaign bundles."""
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

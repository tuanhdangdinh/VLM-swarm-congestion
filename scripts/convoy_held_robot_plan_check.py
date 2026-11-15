#!/usr/bin/env python3
"""Paid offline check of the held-robot state prompt condition on convoy (2026-11-15).

Pre-registration and results: docs/reports/2026-11-15-convoy-held-robot-prompt-check.md.

Reuses the plan-check runner (`scripts/vlm_order_channel_plan_check.py`): its
`Stimulus` rebuild, `GuardedBackend` cost ledger and stop rules, the shipped
`Reasoner`, and its offline M5/M3 replay (`make_pipeline(...)._run_from_result`
with each artifact's own legacy grounding params). Only the stimuli, the two
conditions and the convoy-specific classification are new here.

Conditions:

* ``C`` (control): the live first-trigger prompt as recorded (rebuilt from the
  artifact; must match the stored `user_sha256`).
* ``H`` (treatment): the same request plus `held_robot_ids`, the robots M5's
  task registry held back at that request. The recorded artifacts predate the
  field, so the set is taken from bundle evidence: robots with
  `start_delay_sec > 0` in the bundle's `orchestrator.overlaid.yaml` whose
  `start delay elapsed ... released robots=[...]` line in `m5.log` comes after
  this request's first `dispatch` line.

Usage (key read by the adapter from the env var; load it the repo's way):
    set -a; source <repo>/.env; set +a
    python scripts/convoy_held_robot_plan_check.py gates --docs-root <dir>
    python scripts/convoy_held_robot_plan_check.py run --docs-root <dir> --rep 0 --cap 0.48
    python scripts/convoy_held_robot_plan_check.py analyze --docs-root <dir>
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vlm_order_channel_plan_check as pc  # noqa: E402

from reasoning.vlm.models import ReasonerRequest, ReasonerResult  # noqa: E402
from reasoning.vlm.prompt_builder import build_prompt_payload  # noqa: E402

EXPERIMENT = "2026-11-15-convoy-held-robot-prompt-check"
DEFAULT_OUT = pc.REPO_ROOT / "data" / "experiments" / EXPERIMENT
ALL_FOUR = ("robot_1", "robot_2", "robot_3", "robot_4")

# (class, bundle path relative to --docs-root, first-trigger request_id prefix,
# replicates per condition).
STIMULI: tuple[tuple[str, str, str, int], ...] = (
    ("live_cvD", "vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/cv/runs/cvD_t01_a1",
     "35084986", 6),
    ("live_cvD", "vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/cv/runs/cvD_t02_a1",
     "759bdb94", 6),
    ("live_cvD", "vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/cv/runs/cvD_t03_a1",
     "ab6a10c5", 6),
    ("smoke_armC", "vgu-vlm-swarm-v7f/data/logs/vm_runs/convoy_live/runs/cvL_e01_armC_a1",
     "39f28463", 4),
)


class ConvoyStimulus(pc.Stimulus):
    """A convoy first-trigger snapshot plus its evidence-derived held set."""

    held: list[str]
    reps: int

    def request(self, condition: str) -> ReasonerRequest:
        """Control `C` is the recorded request; `H` adds the held robots."""
        base = self.base_request()
        if condition == "C":
            return base
        if condition == "H":
            return ReasonerRequest(**{**base.model_dump(), "held_robot_ids": list(self.held)})
        raise ValueError(f"unknown condition {condition!r}")


def held_from_evidence(bundle: Path, config: Any, request_id: str) -> list[str]:
    """Robots with a start delay whose release is logged after this request's dispatch."""
    delayed = sorted(r for r, t in config.initial_tasks.items() if t.start_delay_sec > 0)
    lines = (bundle / "m5.log").read_text().splitlines()
    dispatch = next(i for i, x in enumerate(lines) if f"dispatch request={request_id}" in x)
    released: list[str] = []
    for i, line in enumerate(lines):
        m = re.search(r"start delay elapsed, base mission released robots=(\[.*\])", line)
        if m:
            if i < dispatch:
                raise RuntimeError(f"{bundle.name}: release logged before the first dispatch")
            released += ast.literal_eval(m.group(1))
    if sorted(released) != delayed:
        raise RuntimeError(f"{bundle.name}: released {released} != delayed {delayed}")
    return delayed


def load_stimuli(docs_root: Path) -> list[ConvoyStimulus]:
    """Load the four stimuli; raise when anything is missing or inconsistent."""
    out = []
    for cls, rel, prefix, reps in STIMULI:
        bundle = docs_root / rel
        matches = sorted((bundle / "decisions").glob(f"{prefix}*.json"))
        if len(matches) != 1:
            raise FileNotFoundError(f"{rel}: expected one artifact {prefix}*, got {len(matches)}")
        art = json.loads(matches[0].read_text())
        config = pc.load_config(
            yaml.safe_load((bundle / "orchestrator.overlaid.yaml").read_text())
        )
        params = pc.GroundingParams(**art["grounding_params_source"]["params"])
        yfm = art.get("grounding_yield_feasibility") or config.grounding_yield_feasibility
        frame = bundle / "frames" / f"{art['request_id']}.png"
        if not frame.is_file():
            raise FileNotFoundError(frame)
        s = ConvoyStimulus(cls, bundle, rel, art["request_id"], art, config, params, yfm, frame)
        s.held = held_from_evidence(bundle, config, art["request_id"])
        s.reps = reps
        out.append(s)
    return out


def classify(cmd: dict[str, Any] | None) -> dict[str, Any]:
    """Structure of one grounded command: yielder, linked waits, crossing order."""
    if cmd is None:
        return {"kind": "none"}
    actions = cmd.get("actions", [])
    yields = [a for a in actions if a["action"] == "yield"]
    linked = sorted(
        a["robot_id"]
        for a in actions
        if a["action"] == "temporary_wait" and "linked_position" in a.get("parameters", {})
    )
    out: dict[str, Any] = {
        "kind": "yield" if yields else ",".join(sorted({a["action"] for a in actions})),
        "robots": sorted(a["robot_id"] for a in actions),
        "linked_waits": linked,
    }
    if len(yields) == 1:
        y = yields[0]
        others = sorted(set(ALL_FOUR) - {y["robot_id"]})
        order = y["parameters"].get("crossing_order") or [y["parameters"].get("passer_robot_id")]
        out.update(
            {
                "yielder": y["robot_id"],
                "crossing_order": order,
                # The smoke structure: one yield, linked waits for all other
                # robots, all of them in the crossing order.
                "full_sequence": linked == others and sorted(order) == others,
            }
        )
    return out


def names_all_four_with_roles(result: ReasonerResult) -> bool:
    """The decision involves all four robots and no plan leg gives a robot `continue`."""
    dec = result.decision
    if dec is None or sorted(dec.involved_robots) != list(ALL_FOUR):
        return False
    if dec.proposed_plan:
        return all(leg.action != "continue" for leg in dec.proposed_plan)
    return True


def ground(s: ConvoyStimulus, request: ReasonerRequest, result: ReasonerResult) -> Any:
    """M5's `chi` pipeline offline on the artifact's own config and legacy params."""
    return pc.make_pipeline(s, "chi")._run_from_result(request, result)


def cmd_gates(args: argparse.Namespace) -> int:
    """Free gates: prompt rebuild sha, recorded-decision replay, reasoner config."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    vlm = yaml.safe_load((pc.REPO_ROOT / "config" / "models.yaml").read_text())["vlm"]
    rc = pc.describe_effective_sampling(
        pc.resolve_reasoner_config(vlm, "gemini"), pc.load_backend_config(vlm, "gemini")
    ).model_dump(mode="json")
    rows, ok = [], True
    for s in load_stimuli(Path(args.docs_root)):
        stored = s.artifact["prompt"]["user_sha256"]
        control = build_prompt_payload(s.request("C")).user_prompt
        treat = build_prompt_payload(s.request("H")).user_prompt
        o = ground(s, s.request("C"), pc.recorded_result(s))
        rec = s.artifact.get("dispatched_command")
        reproduced = pc.command_sig(o.grounded_command) == pc.command_sig(rec)
        # The Arm C smoke ran the scripted mock arm: no live config to compare.
        live_rc = s.artifact["reasoner_config_effective"] if s.cls == "live_cvD" else rc
        rc_diff = {
            k: (rc.get(k), live_rc.get(k))
            for k in ("model_id", "temperature", "top_p", "top_k", "thinking_level",
                      "max_tokens", "max_attempts", "payload_format")
            if rc.get(k) != live_rc.get(k)
        }
        row = {
            "episode": s.label,
            "request_id": s.request_id,
            "held": s.held,
            "control_matches_stored": pc.sha256_text(control) == stored,
            "stored_user_sha256": stored,
            "H_user_sha256": pc.sha256_text(treat),
            "H_minus_C_chars": len(treat) - len(control),
            "recorded_command_reproduced": reproduced,
            "recorded_structure": classify(rec),
            "reasoner_config_diff_vs_live": rc_diff,
        }
        ok &= row["control_matches_stored"] and reproduced and not rc_diff
        rows.append(row)
        print(json.dumps(row))
    (out / "gates.json").write_text(json.dumps(rows, indent=1) + "\n")
    print("GATES", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_run(args: argparse.Namespace) -> int:
    """One replicate: one call per stimulus per condition (C then H), resumable."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    calls_path = out / "calls.jsonl"
    ledger = pc.Ledger(out / "ledger.json", args.cap)
    done = pc.load_done(calls_path)
    vlm = yaml.safe_load((pc.REPO_ROOT / "config" / "models.yaml").read_text())["vlm"]
    adapter = pc.backend_adapter(vlm, "gemini")
    reasoner_config = pc.resolve_reasoner_config(vlm, "gemini")
    backend_config = pc.load_backend_config(vlm, "gemini")
    guard = pc.GuardedBackend(
        pc.build_backend(adapter, backend_config), adapter, "gemini", ledger, args.cap,
        reasoner_config.max_tokens,
    )
    reasoner = pc.Reasoner(
        guard, reasoner_config, pc.describe_effective_sampling(reasoner_config, backend_config)
    )
    for s in load_stimuli(Path(args.docs_root)):
        if args.rep >= s.reps:
            continue
        for condition in ("C", "H"):
            key = f"gemini|{condition}|{args.rep}|{s.request_id}"
            if key in done:
                continue
            if guard.stop_reason is not None:
                print(f"STOP: {guard.stop_reason}")
                return 0
            request = s.request(condition)
            guard.attempts = []
            started = time.time()
            result = reasoner.run(request)
            usd = sum(a.get("usd", 0.0) for a in guard.attempts)
            if not any("usd" in a for a in guard.attempts) and guard.stop_reason is not None:
                print(f"STOP: {guard.stop_reason} (no call made for {key})")
                return 0
            record = {
                "key": key,
                "condition": condition,
                "rep": args.rep,
                "cls": s.cls,
                "episode": s.label,
                "request_id": s.request_id,
                "user_sha256": pc.sha256_text(build_prompt_payload(request).user_prompt),
                "frame_sha256": pc.sha256_file(s.frame),
                "model_id": getattr(backend_config, "model_id", None),
                "reasoner_config": reasoner_config.model_dump(mode="json"),
                "wall_start": round(started, 1),
                "attempts": guard.attempts,
                "result": result.model_dump(mode="json"),
                "usd": round(usd, 6),
                "stop_reason": guard.stop_reason,
            }
            with calls_path.open("a") as fh:
                fh.write(json.dumps(record) + "\n")
            dec = result.decision
            print(
                f"{key[:48]:48} parse={result.diagnostics.parse_status} "
                f"strategy={dec.strategy if dec else None} "
                f"involved={len(dec.involved_robots) if dec else 0} "
                f"usd={usd:.4f} ledger={ledger.spent:.4f}"
            )
            time.sleep(args.pace)
    print(f"done rep={args.rep}; ledger {ledger.spent:.4f}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Ground every stored answer offline and tabulate per condition."""
    out = Path(args.out)
    stimuli = {s.request_id: s for s in load_stimuli(Path(args.docs_root))}
    rows = []
    for line in (out / "calls.jsonl").read_text().splitlines():
        rec = json.loads(line)
        s = stimuli[rec["request_id"]]
        result = ReasonerResult(**rec["result"])
        row: dict[str, Any] = {
            k: rec[k] for k in ("key", "condition", "rep", "cls", "episode", "usd")
        }
        row["n_attempts"] = len(rec["attempts"])
        row["billed"] = any("usd" in a for a in rec["attempts"])
        dec = result.decision
        row["valid"] = dec is not None
        if dec is not None:
            row.update(
                {
                    "strategy": dec.strategy,
                    "involved": sorted(dec.involved_robots),
                    "yield_robot": dec.yield_robot,
                    "crossing_order": dec.crossing_order,
                    "plan": [(x.robot_id, x.action) for x in dec.proposed_plan or []] or None,
                    "names_all_four_with_roles": names_all_four_with_roles(result),
                    "reasoning": (dec.reasoning or "")[:400]
                    if hasattr(dec, "reasoning") else None,
                }
            )
            if dec.strategy != "none":
                o = ground(s, s.request(rec["condition"]), result)
                cmd = o.grounded_command
                row["terminal"] = str(o.terminal_stage)
                row["failure"] = o.failure_reason
                row["provenance"] = None if o.plan is None else o.plan.provenance
                row["yield_refusal"] = pc.yield_refusal_fan_out(o.grounded_command)
                row["grounded"] = classify(cmd)
            else:
                row["grounded"] = {"kind": "none"}
        rows.append(row)
    with (out / "analysis.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")
    table: dict[str, dict[str, Any]] = {}
    for r in rows:
        for key in (f"{r['condition']}|all", f"{r['condition']}|{r['episode']}"):
            t = table.setdefault(key, {"n": 0, "valid": 0, "names_all_four": 0,
                                       "full_seq": 0, "full_seq_y2": 0, "full_seq_y1": 0,
                                       "grounded_yielder": {}, "strategy": {}, "kind": {}})
            t["n"] += 1
            if not r["valid"]:
                continue
            t["valid"] += 1
            t["names_all_four"] += int(bool(r.get("names_all_four_with_roles")))
            g = r.get("grounded") or {}
            t["strategy"][r["strategy"]] = t["strategy"].get(r["strategy"], 0) + 1
            t["kind"][g.get("kind")] = t["kind"].get(g.get("kind"), 0) + 1
            y = g.get("yielder")
            t["grounded_yielder"][str(y)] = t["grounded_yielder"].get(str(y), 0) + 1
            if g.get("full_sequence"):
                t["full_seq"] += 1
                t["full_seq_y2"] += int(y == "robot_2")
                t["full_seq_y1"] += int(y == "robot_1")
    (out / "summary.json").write_text(json.dumps(table, indent=1, sort_keys=True) + "\n")
    for k in sorted(table):
        print(k, json.dumps(table[k], sort_keys=True))
    print("usd_ledger", round(sum(r.get("usd") or 0.0 for r in rows), 4), "calls", len(rows))
    return 0


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("gates", "run", "analyze"):
        p = sub.add_parser(name)
        p.add_argument("--docs-root", required=True)
        p.add_argument("--out", default=str(DEFAULT_OUT))
        if name == "run":
            p.add_argument("--rep", type=int, required=True)
            p.add_argument("--cap", type=float, required=True, help="ledger cap (1.25x list)")
            p.add_argument("--pace", type=float, default=1.0)
    args = ap.parse_args()
    return {"gates": cmd_gates, "run": cmd_run, "analyze": cmd_analyze}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

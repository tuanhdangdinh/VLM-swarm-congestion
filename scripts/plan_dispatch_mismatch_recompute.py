"""Offline recomputation of plan-dispatch mismatches over recorded decision artifacts.

Read-only: applies `reasoning.rag.plan_dispatch_mismatch.classify_plan_dispatch`
to every recorded decision that carries a plan block, one bundle at a time,
and writes a separate JSON table. Recorded artifacts are never modified; the
corrected counts are a recomputation beside them, not a rewrite of them.

Usage:
    python scripts/plan_dispatch_mismatch_recompute.py --out <table.json> \
        --campaign <demo_campaign dir> --october <vm_runs dir>

Rules:
- Bundles are the parents of `decisions/` directories; any path component
  starting with `_backup` is skipped. A campaign bundle without
  `RESTORE OK` in `RESTORE.txt` is skipped as unfinished, and so is every
  campaign bundle while a `run_dmc.sh` process is running.
- Artifacts are deduplicated by `request_id` (first seen wins: campaign
  roots in the order given, then October).
- Kept: a `decision` and a `plan` block. The legs compared are the verified
  legs `dispatch_matches_plan` was computed on: a non-held plan block's legs;
  on a hold, the block's non-`done` legs (the hold rule) plus each `done`
  robot's own proposed leg (`continue` when unnamed). Held non-verbatim
  decisions are flagged `legs=held_approx`.
- Fidelity gate: for non-`junction_clear` decisions with nothing dropped,
  `per_robot_equal` must equal the recorded `dispatch_matches_plan`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reasoning.rag.command_grounder import project_dispatched_legs  # noqa: E402
from reasoning.rag.plan_dispatch_mismatch import (  # noqa: E402
    classify_plan_dispatch,
    dispatched_kinds,
)

_MOTION = ("reverse", "yield", "reroute")


def _run_dmc_running() -> bool:
    out = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True).stdout
    return any("run_dmc.sh" in line for line in out.splitlines())


def _bundles(root: Path) -> Iterator[Path]:
    for decisions in sorted(root.rglob("decisions")):
        if not decisions.is_dir():
            continue
        rel = decisions.relative_to(root).parts
        if any(part.startswith("_backup") for part in rel):
            continue
        yield decisions.parent


def _finished(bundle: Path) -> bool:
    restore = bundle / "RESTORE.txt"
    return restore.exists() and "RESTORE OK" in restore.read_text(errors="replace")


def _series(root_kind: str, root: Path, bundle: Path) -> str:
    rel = bundle.relative_to(root).parts
    if root_kind == "campaign":
        # Roots are `demo_campaign/<scenario>/runs`.
        return f"campaign/{root.parent.name}"
    if rel[0] == "batch6":
        return "october/batch6 (prereg-v3 tranche 1, registered)"
    return f"october/{rel[0]}"


def _verified_legs(
    artifact: dict[str, Any], known: list[str]
) -> tuple[list[dict[str, str]], str]:
    plan = artifact["plan"]
    legs = [{"robot_id": leg["robot_id"], "action": leg["action"]} for leg in plan["legs"]]
    if not plan.get("plan_held"):
        return legs, "plan_block"
    done = {leg["robot_id"] for leg in plan["legs"] if leg.get("status") == "done"}
    kept = [leg for leg in legs if leg["robot_id"] not in done]
    if plan["provenance"] == "vlm_verbatim":
        # Verbatim legs are the proposed legs, scene-wide completed.
        proposed = {
            leg["robot_id"]: leg["action"]
            for leg in (artifact["decision"].get("proposed_plan") or [])
        }
        kept += [{"robot_id": r, "action": proposed.get(r, "continue")} for r in sorted(done)]
        return kept, "held_verbatim"
    command = artifact.get("dispatched_command")
    if plan.get("dispatch_matches_plan") is True and command:
        # A recorded match means every verified leg equals the projected
        # dispatch, the done robots' included.
        projected = project_dispatched_legs(dict(command), known)
        kept += [{"robot_id": r, "action": projected.get(r, "continue")} for r in sorted(done)]
        return kept, "held_from_recorded_match"
    kept += [{"robot_id": r, "action": "continue"} for r in sorted(done)]
    return kept, "held_approx"


def _row(artifact: dict[str, Any], series: str, bundle: str) -> dict[str, Any]:
    decision = artifact["decision"]
    plan = artifact["plan"]
    strategy = decision["strategy"]
    known = [robot["robot_id"] for robot in (artifact.get("scene") or {}).get("robots", [])]
    legs, legs_source = _verified_legs(artifact, known)
    withheld = artifact.get("dispatch_withheld")
    command = artifact.get("dispatched_command")
    phases = (artifact.get("junction_phases") or {}).get("phases")
    dropped = artifact.get("dispatch_dropped_robot_ids") or []
    # Artifacts written before forcing-audit A5b (2026-10-07) record no
    # dispatched command: not comparable. A `junction_clear` with no phase
    # sequence (no groundable recede set) is one ordinary command, compared
    # as one, as the live `plan_matches_dispatch` branch does.
    comparable = command is not None or withheld is not None
    sequence = phases if strategy == "junction_clear" and phases else None
    result = classify_plan_dispatch(
        strategy,
        legs,
        command,
        known,
        withheld_reason=None if withheld is None else withheld.get("reason"),
        dropped_robot_ids=dropped,
        junction_phases=sequence,
        order_equivalent=bool(plan.get("order_equivalent")),
    )
    # The report's scan reading: the MODEL's proposed legs (not the verified
    # ones) against the dispatched command, motion legs only.
    proposed = {leg["robot_id"]: leg["action"] for leg in (decision.get("proposed_plan") or [])}
    sent = (
        dispatched_kinds(command, known)
        if command and withheld is None and sequence is None
        else {}
    )
    return {
        "series": series,
        "bundle": bundle,
        "request_id": artifact["request_id"],
        "strategy": strategy,
        "robots_in_scene": len(known),
        "provenance": plan["provenance"],
        "plan_held": bool(plan.get("plan_held")),
        "legs_source": legs_source,
        "model_plan": bool(proposed),
        "dispatch_record": command is not None or withheld is not None,
        "comparable": comparable,
        "withheld": None if withheld is None else withheld.get("reason"),
        "recorded_dispatch_matches_plan": plan.get("dispatch_matches_plan"),
        "per_robot_equal": result.per_robot_equal,
        "fidelity_checked": sequence is None and not dropped and command is not None,
        "matches": result.matches,
        "motion_matches": not any(
            item.kind in ("unplanned_motion", "motion_differs", "planned_motion_not_sent")
            for item in result.items
        ),
        "kinds": list(result.kinds),
        "items": [item.model_dump(mode="json") for item in result.items],
        "excluded": [item.model_dump(mode="json") for item in result.excluded],
        "proposed_reverse_legs_sent": sorted(r for r, k in sent.items() if k == "reverse"),
        "proposed_reverse_legs_unplanned": sorted(
            r for r, k in sent.items() if k == "reverse" and proposed.get(r) != "reverse"
        ),
        "proposed_legs_for_unplanned": {
            r: proposed.get(r, "absent")
            for r, k in sent.items()
            if k == "reverse" and proposed.get(r) != "reverse"
        },
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_series: dict[str, Any] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["series"]].append(row)
    for series, items in sorted(grouped.items()):
        verbatim = [r for r in items if r["provenance"] == "vlm_verbatim" and r["comparable"]]
        kinds: Counter[str] = Counter()
        kind_legs: Counter[str] = Counter()
        for row in items:
            if not row["comparable"]:
                continue
            for kind in row["kinds"]:
                kinds[f"{row['strategy']}:{kind}"] += 1
            for item in row["items"]:
                kind_legs[f"{row['strategy']}:{item['kind']}"] += 1
        by_series[series] = {
            "bundles": len({r["bundle"] for r in items}),
            "decisions_with_plan": len(items),
            "not_comparable": sum(not r["comparable"] for r in items),
            "verbatim_not_comparable": sum(
                r["provenance"] == "vlm_verbatim" and not r["comparable"] for r in items
            ),
            "with_model_plan": sum(r["model_plan"] for r in items),
            "five_robot": sum(r["robots_in_scene"] == 5 for r in items),
            "verbatim_recorded": len(verbatim),
            "verbatim_and_recorded_match": sum(
                bool(r["recorded_dispatch_matches_plan"]) for r in verbatim
            ),
            "verbatim_corrected": sum(r["matches"] for r in verbatim),
            "verbatim_motion_only": sum(r["motion_matches"] for r in verbatim),
            "decisions_with_mismatch": sum(
                not r["matches"] for r in items if r["comparable"]
            ),
            "mismatch_decisions_by_strategy_kind": dict(sorted(kinds.items())),
            "mismatch_items_by_strategy_kind": dict(sorted(kind_legs.items())),
            "verbatim_mismatched_request_ids": [
                f"{r['request_id'][:8]}:{r['strategy']}:{','.join(r['kinds'])}"
                for r in verbatim
                if not r["matches"]
            ],
        }
    return by_series


def main() -> int:
    """Run the recomputation and write the table."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--campaign", type=Path, action="append", default=[])
    parser.add_argument("--october", type=Path, action="append", default=[])
    args = parser.parse_args()
    campaign_live = _run_dmc_running()
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    duplicates = 0
    roots = [("campaign", root) for root in args.campaign] + [
        ("october", root) for root in args.october
    ]
    for kind, root in roots:
        for bundle in _bundles(root):
            if kind == "campaign" and (campaign_live or not _finished(bundle)):
                skipped.append(f"{bundle} (unfinished or run_dmc.sh running)")
                continue
            series = _series(kind, root, bundle)
            for path in sorted((bundle / "decisions").glob("*.json")):
                try:
                    artifact = json.loads(path.read_text())
                except (OSError, ValueError) as exc:
                    skipped.append(f"{path}: {exc}")
                    continue
                request_id = artifact.get("request_id")
                if not request_id or not artifact.get("decision") or not artifact.get("plan"):
                    continue
                if request_id in seen:
                    duplicates += 1
                    continue
                seen.add(request_id)
                rows.append(_row(artifact, series, str(bundle.relative_to(root))))
    fidelity_failures = [
        f"{r['series']}:{r['request_id'][:8]} per_robot_equal={r['per_robot_equal']} "
        f"recorded={r['recorded_dispatch_matches_plan']} legs={r['legs_source']}"
        for r in rows
        if r["fidelity_checked"] and r["per_robot_equal"] != r["recorded_dispatch_matches_plan"]
    ]
    table = {
        "run_dmc_running_at_start": campaign_live,
        "duplicates_skipped": duplicates,
        "skipped": skipped,
        "fidelity_failures": fidelity_failures,
        "series": _summary(rows),
        "rows": rows,
    }
    args.out.write_text(json.dumps(table, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in table.items() if k != "rows"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

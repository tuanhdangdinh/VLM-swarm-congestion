"""Per-analysis and per-episode tables for live S1b episodes (prereg-v3 A22 batch).

Reads one or more S1b episode bundles (the VM `ep_run.sh` layout) and prints
one JSON object per bundle with the E6 capture schema:

* per analysis, in M5 `starting analysis` order (decision artifacts are
  written at terminal stage, so mtime order is not analysis order):
  sim_t (the artifact scene's M1 stamp), trigger robots, strategy / type /
  involved / yield_robot, the GT-free latch clusters of the artifact's own
  scene (M1 positions, < 0.45 m components) and which of them the decision
  names, the proposed plan's active (non-`continue`) legs and the clusters
  they touch (`plan_addresses_both` = active legs in >= 2 distinct
  multi-robot clusters), plan provenance
  / edits / `dispatch_matches_plan`, the M5 outcome (dispatched actions or
  `dispatch_withheld` reason + refusal), and billed tokens and estimated cost
  (published ER-2 rate: input $1/1M, output + thought $5/1M, every reasoner
  attempt plus any stage-2 call; a lower bound: a timed-out call records no
  usage);
* per episode: provenance counts and vb AND dispatch_matched; the first
  analysis's outcome and whether it is a FIRST-CONFLICT YIELD (A22 rule 11
  (c): the first analysis dispatches a yield that reaches gate_admit); cost
  total; plus `s1_churn_stats`, `s1_gridlock_stats` and `s1b_episode_stats`
  outputs (resolution events, churn, tasks, wandering vs park).

Usage:
    PYTHONPATH=.:ros2_ws/src/swarm_orchestrator \\
        python scripts/s1b_live_batch_stats.py <bundle_dir> [...]
"""

from __future__ import annotations

import glob
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ros2_ws/src/swarm_orchestrator"))

import s1_churn_stats as churn  # noqa: E402
import s1_gridlock_stats as grid  # noqa: E402
import s1b_episode_stats as eps  # noqa: E402

LATCH_M = 0.45
_START = re.compile(r"starting analysis request=([0-9a-f]+) robots=(\[[^\]]*\])")


def _usage(block: Any) -> list[dict]:
    if not isinstance(block, dict):
        return []
    attempts = block.get("attempt_token_usage")
    if attempts:
        return [u for u in attempts if isinstance(u, dict)]
    usage = block.get("token_usage")
    return [usage] if isinstance(usage, dict) else []


def _cost(usage: dict) -> float:
    prompt = usage.get("prompt_tokens") or 0
    out = (usage.get("completion_tokens") or 0) + (usage.get("thought_tokens") or 0)
    return prompt * 1e-6 + out * 5e-6


def artifact_cost(artifact: dict) -> tuple[float, int]:
    """Estimated USD and billed-call count of one decision artifact (cost_watch's sum)."""
    calls = _usage(artifact.get("diagnostics"))
    stage2 = artifact.get("stage2")
    if isinstance(stage2, dict):
        for key in ("response", "diagnostics", "result"):
            calls += _usage(stage2.get(key))
        calls += _usage(stage2)
    return sum(_cost(u) for u in calls), len(calls)


def latch_clusters(robots: list[dict]) -> list[set[str]]:
    """Connected components (size >= 2) of the < 0.45 m graph over one scene."""
    pos = {r["robot_id"]: (r["x"], r["y"]) for r in robots}
    ids = sorted(pos)
    parent = {i: i for i in ids}

    def find(i: str) -> str:
        while parent[i] != i:
            i = parent[i]
        return i

    for a in ids:
        for b in ids:
            if a < b and math.dist(pos[a], pos[b]) < LATCH_M:
                parent[find(a)] = find(b)
    comps: dict[str, set[str]] = {}
    for i in ids:
        comps.setdefault(find(i), set()).add(i)
    return sorted((c for c in comps.values() if len(c) >= 2), key=sorted)


def _touched(robots: list[str], clusters: list[set[str]]) -> list[int]:
    return sorted({k for k, c in enumerate(clusters) if set(robots) & c})


def analyse_batch_episode(bundle: Path) -> dict[str, Any]:
    """Return the per-analysis table and episode aggregates of one live S1b bundle."""
    arts: dict[str, dict] = {}
    for path in glob.glob(str(bundle / "decisions" / "*.json")):
        data = json.loads(Path(path).read_text())
        arts[(data.get("request_id") or Path(path).stem)[:8]] = data
    m5 = (bundle / "m5.log").read_text(errors="replace").splitlines()
    episode = eps.analyse(bundle)
    admitted = {e["command"] for e in episode["resolution_events"] if e.get("admit_sim_t")}
    rows = []
    for line in m5:
        match = _START.search(line)
        if not match:
            continue
        rid = match.group(1)[:8]
        art = arts.get(rid, {})
        decision = art.get("decision") or {}
        scene = (art.get("scene") or {}).get("robots", [])
        clusters = latch_clusters(scene)
        involved = list(decision.get("involved_robots") or [])
        plan_legs = decision.get("proposed_plan") or []
        active = [leg["robot_id"] for leg in plan_legs if leg.get("action") != "continue"]
        plan = art.get("plan") or {}
        withheld = art.get("dispatch_withheld")
        command = art.get("dispatched_command")
        usd, calls = artifact_cost(art)
        rows.append(
            {
                "request": rid,
                # The scene the analysis saw (M1 clock), as the A21 report tabulates.
                "sim_t": round((art.get("scene") or {}).get("stamp") or 0.0, 1),
                "trigger": json.loads(match.group(2).replace("'", '"')),
                "backend_id": (art.get("diagnostics") or {}).get("backend_id"),
                "parse_status": (art.get("diagnostics") or {}).get("parse_status"),
                "congestion": decision.get("congestion_detected"),
                "type": decision.get("type"),
                "strategy": decision.get("strategy"),
                "involved": involved,
                "yield_robot": decision.get("yield_robot"),
                "scene_clusters": [sorted(c) for c in clusters],
                "clusters_named": _touched(involved, clusters),
                "plan_proposed": bool(plan_legs),
                "plan_active_legs": [
                    f"{leg['robot_id']}:{leg['action']}" for leg in plan_legs
                    if leg.get("action") != "continue"
                ],
                "plan_clusters": _touched(active, clusters),
                "plan_addresses_both": len(_touched(active, clusters)) >= 2,
                "provenance": plan.get("provenance"),
                "plan_edits": len(plan.get("edits") or []),
                "dispatch_matches_plan": plan.get("dispatch_matches_plan"),
                "outcome": (
                    f"withheld:{withheld.get('reason')}" if withheld
                    else ("dispatched" if command else "none")
                ),
                "refusal": (
                    (withheld or {}).get("refusal_reason") or art.get("yield_refusal_reason")
                ),
                "dispatched_actions": [
                    f"{a['robot_id']}:{a['action']}" for a in (command or {}).get("actions", [])
                ],
                "gate_admit": rid in admitted,
                "billed_calls": calls,
                "est_usd": round(usd, 5),
            }
        )
    prov: dict[str, int] = {}
    for r in rows:
        prov[str(r["provenance"])] = prov.get(str(r["provenance"]), 0) + 1
    vb_matched = sum(
        1 for r in rows if r["provenance"] == "vlm_verbatim" and r["dispatch_matches_plan"]
    )
    first = rows[0] if rows else None
    first_yield = bool(
        first and first["outcome"] == "dispatched"
        and any(a.endswith(":yield") for a in first["dispatched_actions"]) and first["gate_admit"]
    )
    return {
        "bundle": bundle.name,
        "analyses": rows,
        "n_analyses": len(rows),
        "provenance_counts": prov,
        "vb_and_dispatch_matched": vb_matched,
        "dispatched_analyses": sum(1 for r in rows if r["outcome"] == "dispatched"),
        "any_plan_addresses_both": any(r["plan_addresses_both"] for r in rows),
        "first_conflict_yield": first_yield,
        "est_usd_total": round(sum(r["est_usd"] for r in rows), 4),
        "billed_calls_total": sum(r["billed_calls"] for r in rows),
        "churn": churn.analyse_churn(bundle),
        "gridlock": grid.analyse_gridlock(bundle),
        "episode": episode,
    }


def main() -> None:
    """Entry point."""
    for arg in sys.argv[1:]:
        print(json.dumps(analyse_batch_episode(Path(arg)), default=str))


if __name__ == "__main__":
    main()

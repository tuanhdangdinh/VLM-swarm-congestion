"""Replay S1 Monte Carlo first conflicts through the plan verifier and dispatch.

The plan-channel parity measurement behind prereg-v3 A16(v), A17, A18 and
A21: for each MC first-conflict scene (`s1_mc.run_episode`, state `--delay`
sim-s after the first encounter, the scene a stall-triggered analysis sees),
an echo-style yield decision is grounded through the real
`ground_reasoner_result` (derived dispatch, the floor's overlay, static
obstacles and grounding file), and the same decision carrying a SCRIPTED
plan (the decided yielder yields, every other involved robot crosses) is
audited by `verify_and_repair_plan`. The two are compared with
`plan_matches_dispatch`.

Two echo conventions pick the involved robots (yielder first):

- `legacy`: every robot not MOVING (else every robot), in snapshot order,
  the first one yields -- the pre-A20 convention the A16(v)/A17/A18 MC
  figures were measured with;
- `a20`: `s1_grounding_replay.echo_names`, the live echo's selection
  (A20(3) latch-pair preference, `prompt_robot_order: id_asc`).

Every scene with a remaining plan/dispatch mismatch is assigned ONE cause,
checked in this order:

- `default_plan_vs_dispatch`: the plan-absent default (`m3_default`, "plan
  absent") already disagrees with dispatch -- the verdict reads the default
  plan's derivation, so this is its one hole (A18 residual (3));
- `non_retry_refusal:<tag>`: dispatch refused the yield (no `yield` action)
  on a refusal the verdict leaves alone by design (A18 residual (2)); `<tag>`
  is the command's `yield=...` degradation up to its first `:`;
- `off_lane_hold`: every mismatching robot is one the command holds outside
  the yield's lane conflict (`order=lane_scoped:<ids>`), dispatched `wait`
  while the plan gives it another action (A18 residual (1));
- `other`.

Deterministic: the seeds are `s1_mc.mc_seeds(n)`, and nothing samples.
Imports resolve against THIS script's checkout (`parents[1]`), so a copy
placed in another worktree's `scripts/` measures that worktree's code.

Usage (repo root):
    python scripts/plan_parity_mc_replay.py --floor s1a --echo legacy [--n 400]
        [--per-seed out.jsonl]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
for _path in (
    REPO / "ros2_ws/src/swarm_execution",
    REPO / "ros2_ws/src/swarm_orchestrator",
    REPO / "scripts",
    REPO,
):
    sys.path.insert(0, str(_path))

import s1_grounding_replay as R  # noqa: E402
import s1_mc as M  # noqa: E402
from swarm_orchestrator.models import load_config  # noqa: E402
from swarm_orchestrator.reasoning_pipeline import load_grounding_source  # noqa: E402

from reasoning.rag import command_grounder as cg  # noqa: E402
from reasoning.vlm.models import (  # noqa: E402
    CongestionDecision,
    ProposedPlanLeg,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)

# The off-lane hold's edit-reason prefix (A21); absent on trees predating it.
_LANE_HOLD_PREFIX = getattr(cg, "LANE_SCOPED_HOLD_PREFIX", "lane_scoped hold:")


def legacy_echo_names(rows: list[dict[str, Any]]) -> list[str]:
    """The pre-A20 echo convention: stalled robots in snapshot order, else all.

    Args:
        rows: The scene's snapshot rows.

    Returns:
        Involved robot ids, the first one the yielder.
    """
    stalled = [r["robot_id"] for r in rows if r["status"] != "MOVING"]
    return stalled or [r["robot_id"] for r in rows]


def _frame(rows: list[dict[str, Any]]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(
                robot_id=r["robot_id"],
                x=r["x"],
                y=r["y"],
                theta=r["theta"],
                status=r["status"],
                goal=tuple(r["goal"]),
            )
            for r in rows
        ],
    )


def _echo_decision(involved: list[str], **extra: Any) -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=involved,
        root_cause="echo",
        strategy="yield",
        justification="echo",
        yield_robot=involved[0],
        **extra,
    )


def _scripted_plan(involved: list[str]) -> list[ProposedPlanLeg]:
    return [
        ProposedPlanLeg(robot_id=involved[0], action="yield"),
        *(ProposedPlanLeg(robot_id=r, action="cross") for r in involved[1:]),
    ]


def _lane_scoped_ids(command: dict[str, Any]) -> set[str]:
    # Measurement only: the verifier itself never parses this tag.
    for tag in command.get("degradations", []):
        if tag.startswith("order=lane_scoped:"):
            return set(tag.removeprefix("order=lane_scoped:").split(","))
    return set()


def mismatch_cause(
    plan_legs: list[ProposedPlanLeg],
    default_legs: list[ProposedPlanLeg],
    command: dict[str, Any],
    known: list[str],
) -> str:
    """Classify why a verified plan's legs differ from the dispatched command.

    Args:
        plan_legs: The verified plan's legs.
        default_legs: The plan-absent default's legs for the same decision.
        command: The dispatched command.
        known: Every robot in the scene.

    Returns:
        One cause label (see the module docstring).
    """
    if not cg.plan_matches_dispatch(default_legs, command, known):
        return "default_plan_vs_dispatch"
    dispatched = cg.project_dispatched_legs(command, known)
    if "yield" not in dispatched.values():
        refusal = next(
            (t for t in command.get("degradations", []) if t.startswith("yield=")), "yield=?"
        )
        return f"non_retry_refusal:{refusal.split(':', 1)[0]}"
    planned = {leg.robot_id: leg.action for leg in plan_legs}
    differing = {rid for rid in known if dispatched[rid] != planned.get(rid)}
    held = _lane_scoped_ids(command)
    if differing and differing <= held and all(dispatched[rid] == "wait" for rid in differing):
        return "off_lane_hold"
    return "other"


def _floor_inputs(floor_name: str):
    scenario = R.FLOORS[floor_name]
    raw = yaml.safe_load(R.ORCH.read_text())
    overlay = R._overlay(scenario)
    raw.update(overlay)
    config = load_config(raw)
    params = load_grounding_source(REPO / overlay["grounding_params_path"]).params
    delta = overlay["task_stream"]["release_stagger_sim_sec"]
    if floor_name == "s1a":
        floor = M.s1a_floor()
    else:
        import s1b_layout as L  # noqa: PLC0415

        floor = L.s1b_floor(scenario)
    return config, params, delta, floor


def replay(floor_name: str, n: int, echo: str, delay: float) -> tuple[dict, list[dict]]:
    """Run the replay over `n` MC seeds of one floor.

    Args:
        floor_name: `s1a` or `s1b`.
        n: Number of MC seeds (`s1_mc.mc_seeds`).
        echo: `legacy` or `a20` (module docstring).
        delay: Snapshot delay after the first encounter, sim-s.

    Returns:
        `(summary, per_seed)`: the floor summary and one record per scene.
    """
    config, params, delta, floor = _floor_inputs(floor_name)
    mode = config.grounding_yield_feasibility
    routes = M.build_routes(floor, "grid")
    names = legacy_echo_names if echo == "legacy" else R.echo_names
    records: list[dict] = []
    skipped: Counter = Counter()
    for seed in M.mc_seeds(n):
        ep = M.run_episode(
            floor, routes, seed, delta=delta, finished="park", freeze=True, snapshot_delay=delay
        )
        rows = ep["first_snapshot"]
        if rows is None:
            skipped["no_snapshot"] += 1
            continue
        involved = names(rows)
        if len(involved) < 2:
            skipped["no_pair"] += 1
            continue
        frame = _frame(rows)
        known = [r["robot_id"] for r in rows]
        diag = ReasonerDiagnostics(
            request_id="r", backend_id="mock", attempts=1, parse_status="valid"
        )
        command = cg.ground_reasoner_result(
            ReasonerResult(
                request_id="r", decision=_echo_decision(involved), raw_text="{}", diagnostics=diag
            ),
            robot_positions={r["robot_id"]: (r["x"], r["y"]) for r in rows},
            geometry=config.scenario_geometry,
            static_obstacles=config.static_obstacles,
            yield_feasibility_mode=mode,
            snapshot=frame,
            params=params,
        )
        verify_kwargs = {
            "geometry": config.scenario_geometry,
            "static_obstacles": config.static_obstacles,
            "yield_feasibility_mode": mode,
            "grounding_params": params,
        }
        verified = cg.verify_and_repair_plan(
            _echo_decision(involved, proposed_plan=_scripted_plan(involved)),
            frame,
            **verify_kwargs,
        )
        default = cg.verify_and_repair_plan(_echo_decision(involved), frame, **verify_kwargs)
        matched = cg.plan_matches_dispatch(verified.legs, command, known)
        records.append(
            {
                "seed": seed,
                "involved": involved,
                "provenance": verified.provenance,
                "matched": matched,
                "cause": None
                if matched
                else mismatch_cause(verified.legs, default.legs, command, known),
                "edits": [(e.op, list(e.robot_ids)) for e in verified.edits],
                "lane_hold_edits": sum(
                    e.reason.startswith(_LANE_HOLD_PREFIX) for e in verified.edits
                ),
                "rejection_reason": verified.rejection_reason,
                "lane_scoped": sorted(_lane_scoped_ids(command)),
                # Joins a baseline run: a verifier-only change keeps it fixed.
                "command_sha": hashlib.sha256(
                    json.dumps(command, sort_keys=True).encode()
                ).hexdigest()[:16],
            }
        )
    return summarise(floor_name, echo, mode, records, skipped), records


def summarise(
    floor_name: str, echo: str, mode: str, records: list[dict], skipped: Counter
) -> dict:
    """Tabulate one floor's per-scene records.

    Args:
        floor_name: The floor replayed.
        echo: The echo convention.
        mode: The yield feasibility mode the floor's config pins.
        records: `replay`'s per-scene records.
        skipped: Seeds with no scene or no pair.

    Returns:
        The summary block printed as JSON.
    """
    scenes = len(records)
    prov = Counter(r["provenance"] for r in records)
    by_match = Counter((r["provenance"], r["matched"]) for r in records)
    causes = Counter((r["provenance"], r["cause"]) for r in records if not r["matched"])
    shapes = Counter(
        str(tuple(op for op, _ in r["edits"])) for r in records if r["provenance"] == "repaired"
    )
    lane_only = sum(
        1
        for r in records
        if r["provenance"] == "repaired" and r["lane_hold_edits"] == len(r["edits"])
    )
    bound = sum(
        1 for r in records if (r["rejection_reason"] or "").startswith("repair distance exceeds")
    )
    vb_matched = by_match[("vlm_verbatim", True)]
    return {
        "floor": floor_name,
        "echo": echo,
        "mode": mode,
        "scenes": scenes,
        "skipped": dict(skipped),
        "provenance": {k: prov[k] for k in ("vlm_verbatim", "repaired", "m3_default")},
        "vb_matched": vb_matched,
        "vb_matched_rate": round(vb_matched / scenes, 4) if scenes else None,
        "vb_mismatched": by_match[("vlm_verbatim", False)],
        "repaired_matched": by_match[("repaired", True)],
        "repaired_mismatched": by_match[("repaired", False)],
        "m3_matched": by_match[("m3_default", True)],
        "m3_mismatched": by_match[("m3_default", False)],
        "mismatch_causes": {f"{p}|{c}": k for (p, c), k in sorted(causes.items())},
        "off_lane_hold_mismatches": sum(
            k for (_, c), k in causes.items() if c == "off_lane_hold"
        ),
        "lane_scoped_scenes": sum(1 for r in records if r["lane_scoped"]),
        "repaired_lane_hold_only": lane_only,
        "repaired_with_lane_hold_edit": sum(1 for r in records if r["lane_hold_edits"]),
        "repaired_edit_shapes": dict(sorted(shapes.items())),
        "repair_distance_exceeded": bound,
    }


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--floor", choices=sorted(R.FLOORS), required=True)
    ap.add_argument("--echo", choices=("legacy", "a20"), required=True)
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--delay", type=float, default=2.5)
    ap.add_argument("--per-seed", type=Path, default=None, help="write one JSON line per scene")
    args = ap.parse_args()
    summary, records = replay(args.floor, args.n, args.echo, args.delay)
    if args.per_seed is not None:
        args.per_seed.write_text("".join(json.dumps(r) + "\n" for r in records))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

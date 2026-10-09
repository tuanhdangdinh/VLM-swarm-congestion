"""Replay S1 Monte Carlo first conflicts through M3 as the echo mock would.

Gate G5a ("first conflict resolvable by one yield") counted a conflict as
resolvable when EITHER robot had the rear room. M3 does not search for that
robot: the echo mock (A12(i), `reasoning.vlm.mock_backend`) names the
robots the prompt reports STOPPED/SLOW/STALE, in presentation order
(`prompt_robot_order: id_asc`), and makes the first one the yielder; M3 then
re-roles node handoffs, keeps the named yielder whenever its 0.95 m room
gate passes, and only then sweeps retreat candidates. This replays each MC
first-conflict scene (state `--delay` sim-s after the first encounter, the
scene a stall-triggered analysis sees) through the real
`ground_reasoner_result` with the floor's overlay, static obstacles and
grounding file in swap mode, and counts EXECUTABLE yields, plus each refusal's
reason class and how many refusals report a 0.00 m room.

Usage (repo root; ROS packages on the path as in the unit tests):
    PYTHONPATH=.:ros2_ws/src/swarm_orchestrator:ros2_ws/src/swarm_execution \\
        python scripts/s1_grounding_replay.py --floor s1b [--n 400] [--pull 0.35]

`--pull G` moves the first-conflict pair toward each other until their
centres are G m apart (live latches sit at 0.30-0.42 m, the MC freezes at
< 0.45).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import s1_mc as M  # noqa: E402

FLOORS = {
    "s1a": REPO / "isaac/config/scenarios/mapd_5.yaml",
    "s1b": REPO / "isaac/config/scenarios/mapd_5_s1b.yaml",
}
ORCH = REPO / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"


def _overlay(path: Path) -> dict:
    lines = path.read_text().splitlines()
    begin = lines.index("#   --- M5 overlay begin ---")
    end = lines.index("#   --- M5 overlay end ---")
    return yaml.safe_load("\n".join(line[4:] for line in lines[begin + 1 : end]))


def _grounder(scenario: Path):
    from swarm_orchestrator.models import load_config
    from swarm_orchestrator.reasoning_pipeline import load_grounding_source

    from reasoning.rag.command_grounder import ground_reasoner_result
    from reasoning.vlm.models import (
        CongestionDecision,
        ReasonerDiagnostics,
        ReasonerResult,
        RobotStateInput,
        SnapshotFrame,
    )

    raw = yaml.safe_load(ORCH.read_text())
    overlay = _overlay(scenario)
    raw.update(overlay)
    config = load_config(raw)
    params = load_grounding_source(REPO / overlay["grounding_params_path"]).params

    def ground(rows: list[dict]) -> dict | None:
        stalled = [r["robot_id"] for r in rows if r["status"] != "MOVING"]
        involved = stalled or [r["robot_id"] for r in rows]
        if len(involved) < 2:
            return None
        frame = SnapshotFrame(
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
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=involved,
            root_cause="echo",
            strategy="yield",
            justification="echo",
            yield_robot=involved[0],
        )
        diag = ReasonerDiagnostics(
            request_id="r", backend_id="mock", attempts=1, parse_status="valid"
        )
        result = ReasonerResult(request_id="r", decision=decision, raw_text="{}", diagnostics=diag)
        return ground_reasoner_result(
            result,
            robot_positions={r["robot_id"]: (r["x"], r["y"]) for r in rows},
            geometry=config.scenario_geometry,
            static_obstacles=config.static_obstacles,
            yield_feasibility_mode=config.grounding_yield_feasibility,
            snapshot=frame,
            params=params,
        )

    return ground


def _pull(rows: list[dict], pair: list[str], gap: float) -> list[dict]:
    a = next(r for r in rows if r["robot_id"] == pair[0])
    b = next(r for r in rows if r["robot_id"] == pair[1])
    d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
    if d <= gap or d == 0:
        return rows
    k = (d - gap) / 2 / d
    ux, uy = (b["x"] - a["x"]) * k, (b["y"] - a["y"]) * k
    a2 = dict(a, x=a["x"] + ux, y=a["y"] + uy)
    b2 = dict(b, x=b["x"] - ux, y=b["y"] - uy)
    return [a2 if r is a else b2 if r is b else r for r in rows]


def classify(command: dict | None) -> str:
    """executable_yield / empty_reroute / refused / other."""
    if command is None:
        return "no_pair"
    actions = command.get("actions", [])
    if any(a["action"] == "yield" for a in actions):
        return "executable_yield"
    if any(
        a["action"] == "reroute" and not a.get("parameters", {}).get("waypoints") for a in actions
    ):
        return "empty_reroute"
    if any("refused" in str(a.get("parameters", {}).get("reason", "")) for a in actions):
        return "refused"
    return "other"


def refusal_kind(command: dict) -> str | None:
    """The refusal's reason class (its text up to the first `(`, `:` or `;`), or None."""
    for action in command.get("actions", []):
        reason = str(action.get("parameters", {}).get("reason", ""))
        if reason.startswith("yield refused: "):
            body = reason.removeprefix("yield refused: ")
            cuts = [i for i in (body.find("("), body.find(":"), body.find(";")) if i >= 0]
            return body[: min(cuts, default=len(body))].strip()
    return None


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", choices=sorted(FLOORS), default="s1b")
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--delay", type=float, default=2.5)
    ap.add_argument("--pull", type=float, default=None)
    args = ap.parse_args()
    scenario = FLOORS[args.floor]
    delta = _overlay(scenario)["task_stream"]["release_stagger_sim_sec"]
    if args.floor == "s1a":
        floor = M.s1a_floor()
    else:
        import s1b_layout as L  # noqa: PLC0415

        floor = L.s1b_floor(scenario)
    routes = M.build_routes(floor, "grid")
    ground = _grounder(scenario)
    outcomes: Counter = Counter()
    yielders: Counter = Counter()
    refusals: Counter = Counter()
    zero_room = 0
    for seed in M.mc_seeds(args.n):
        ep = M.run_episode(
            floor,
            routes,
            seed,
            delta=delta,
            finished="park",
            freeze=True,
            snapshot_delay=args.delay,
        )
        rows = ep["first_snapshot"]
        if rows is None:
            outcomes["no_snapshot"] += 1
            continue
        if args.pull is not None:
            rows = _pull(rows, ep["encounters"][0]["pair"], args.pull)
        command = ground(rows)
        label = classify(command)
        outcomes[label] += 1
        if label == "refused":
            refusals[refusal_kind(command) or "other"] += 1
            zero_room += any(
                " 0.00 m" in str(a.get("parameters", {}).get("reason", ""))
                for a in command["actions"]
            )
        if label == "executable_yield":
            y = next(a["robot_id"] for a in command["actions"] if a["action"] == "yield")
            yielders["in_first_pair" if y in ep["encounters"][0]["pair"] else "other"] += 1
    n = sum(outcomes.values())
    print(
        json.dumps(
            {
                "floor": args.floor,
                "n": n,
                "delay": args.delay,
                "pull": args.pull,
                "outcomes": dict(outcomes),
                "executable_rate": outcomes["executable_yield"] / n,
                "executable_yielder": dict(yielders),
                "refusal_reasons": dict(refusals.most_common()),
                "refusals_reporting_0.00_m": zero_room,
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()

"""Re-ground live S1 analyses with and without a declared junction (A16(iii)).

For every decision artifact of an episode bundle whose decision is a yield,
this rebuilds the request from the artifact's own scene (registry goals
attached), feeds the STORED decision through the production
`InProcessPipeline` with the bundle's overlaid orchestrator config and its
grounding file, and:

1. checks the shipped re-grounding reproduces the live command (actions and
   degradations); without that match the counterfactual means nothing;
2. re-grounds with `scenario_geometry.junction_declared` flipped to True --
   the pre-guard crossing view -- and classifies what the guard changed.

Usage (repo root; ROS packages on the path as in the unit tests):
    PYTHONPATH=.:ros2_ws/src/swarm_orchestrator:ros2_ws/src/swarm_execution \\
        python scripts/s1b_guard_counterfactual.py <bundle_dir> [...]

Prints one JSON object per bundle.
"""

from __future__ import annotations

import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml
from swarm_orchestrator.models import RobotView, SceneSnapshot, load_config
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    build_reasoner_request,
    load_grounding_source,
)

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.vlm.models import CongestionDecision, ReasonerDiagnostics, ReasonerResult

REPO = Path(__file__).resolve().parents[1]


def _kind(command: dict | None) -> str:
    if not command:
        return "none"
    actions = command.get("actions", [])
    if any(a["action"] == "yield" for a in actions):
        return "executable_yield"
    if any(a["action"] == "reroute" and not a.get("parameters", {}).get("waypoints")
           for a in actions):
        return "empty_reroute"
    if any(str(a.get("parameters", {}).get("reason", "")).startswith("yield refused:")
           for a in actions):
        return "refused"
    return "other"


def _refusal_class(command: dict | None) -> str | None:
    for tag in (command or {}).get("degradations", []):
        m = re.match(r"yield=infeasible:yield refused: ([a-z -]+)", tag)
        if m:
            return m.group(1).strip()
    return None


def _yield_room(command: dict | None) -> dict:
    for a in (command or {}).get("actions", []):
        if a["action"] == "yield":
            p = a["parameters"]
            return {"yielder": a["robot_id"], "backup_m": p.get("backup_distance_m"),
                    "passer_clear_m": p.get("passer_clear_m"),
                    "crossing_order": p.get("crossing_order")}
    return {}


def _actions(command: dict) -> list[dict]:
    return [
        {**a, "parameters": {k: v for k, v in a.get("parameters", {}).items() if k != "plan_id"}}
        for a in command.get("actions", [])
    ]


def _pipeline(config, params, geometry, goals):
    class _Stored:
        result: ReasonerResult | None = None

        def run(self, _request):
            return self.result

    stored = _Stored()
    pipe = InProcessPipeline(
        reasoner=stored,
        ground_fn=ground_reasoner_result,
        scene_geometry=geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        grounding_params=params,
        stage2_enabled=config.stage2_retreat_selection,
        goal_reference_of=lambda rid: goals.get(rid),
    )
    return pipe, stored


def analyse(bundle: Path) -> dict:
    """Re-ground every yield analysis of one bundle, shipped and junction-declared."""
    raw = yaml.safe_load((bundle / "orchestrator.overlaid.yaml").read_text())
    config = load_config(raw)
    params = load_grounding_source(REPO / config.grounding_params_path).params
    declared = config.scenario_geometry.model_copy(update={"junction_declared": True})
    rows = []
    for path in sorted(glob.glob(str(bundle / "decisions" / "*.json"))):
        art = json.loads(Path(path).read_text())
        decision = art.get("decision")
        if not decision or decision.get("strategy") != "yield":
            continue
        scene = art["scene"]
        robots = [
            RobotView(
                robot_id=r["robot_id"], x=r["x"], y=r["y"], theta=r["theta"],
                linear_velocity=r.get("linear_velocity", 0.0), status=r["status"],
                stamp=r.get("stamp", scene["stamp"]),
                goal=None if r.get("goal") is None else tuple(r["goal"]),
                task=r.get("task"),
            )
            for r in scene["robots"]
        ]
        snapshot = SceneSnapshot(
            stamp=scene["stamp"], frame_id=scene.get("frame_id", "cam"), robots=robots,
            dropped_frame=bool(scene.get("dropped_frame", False)),
        )
        goals = {r.robot_id: r.goal for r in robots if r.goal is not None}
        request = build_reasoner_request(
            request_id=art["request_id"], snapshot=snapshot, image_path="/tmp/x.png"
        )
        diag = ReasonerDiagnostics(
            request_id=art["request_id"], backend_id="mock", attempts=1, parse_status="valid"
        )
        result = ReasonerResult(
            request_id=art["request_id"], decision=CongestionDecision(**decision),
            raw_text="{}", diagnostics=diag,
        )
        out = {}
        for label, geometry in (("shipped", config.scenario_geometry), ("declared", declared)):
            pipe, stored = _pipeline(config, params, geometry, goals)
            stored.result = result
            outcome = pipe.run(request)
            out[label] = outcome.grounded_command
        live = art.get("dispatched_command")
        # The live plan tracker stamps `plan_id` on every action; the replay
        # runs without one, so it is the only field left out of the match.
        reproduced = (
            out["shipped"] is not None and live is not None
            and _actions(out["shipped"]) == _actions(live)
            and out["shipped"].get("degradations") == live.get("degradations")
        )
        rows.append({
            "request": art["request_id"][:8],
            "withheld": (art.get("dispatch_withheld") or {}).get("reason"),
            "reproduced": reproduced,
            "live_kind": _kind(live),
            "live_refusal": _refusal_class(live),
            "declared_kind": _kind(out["declared"]),
            "declared_refusal": _refusal_class(out["declared"]),
            "declared_yield": _yield_room(out["declared"]),
            "shipped_actions": None if reproduced else _actions(out["shipped"] or {}),
            "live_actions": None if reproduced else _actions(live or {}),
            "declared_view_tags": [
                t for t in (out["declared"] or {}).get("degradations", [])
                if t.startswith("grounding=dynamic_arms")
            ],
        })
    changed = [r for r in rows if r["live_refusal"] == "no declared junction"]
    return {
        "bundle": bundle.name,
        "yield_analyses": len(rows),
        "reproduced": sum(r["reproduced"] for r in rows),
        "live_refusal_classes": dict(Counter(r["live_refusal"] for r in rows)),
        "guard_refusals": len(changed),
        "guard_refusals_declared_kind": dict(Counter(r["declared_kind"] for r in changed)),
        "rows": rows,
    }


def main() -> None:
    """Entry point."""
    for b in sys.argv[1:]:
        print(json.dumps(analyse(Path(b)), default=str))


if __name__ == "__main__":
    main()

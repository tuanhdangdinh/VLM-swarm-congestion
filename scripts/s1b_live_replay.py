"""Re-ground live S1 yield analyses on the current tree, with and without the A20(1) boxes.

For every decision artifact of an episode bundle whose decision is a yield,
this rebuilds the request from the artifact's own scene (registry goals
attached) and feeds the STORED decision through the production
`InProcessPipeline` (`s1b_guard_counterfactual._pipeline`) twice:

1. with the bundle's own overlaid orchestrator config: on the tree the
   bundle ran on this must reproduce the live command (actions and
   degradations); on a later tree the difference is what the code change
   does to that live scene;
2. for S1b bundles, with the CURRENT `mapd_5_s1b.yaml` header's
   `scenario_geometry` swapped in (the A20(1) junction boxes).

Usage (repo root; ROS packages on the path as in the unit tests):
    PYTHONPATH=.:ros2_ws/src/swarm_orchestrator:ros2_ws/src/swarm_execution \\
        python scripts/s1b_live_replay.py <bundle_dir> [...]

Prints one line per yield analysis: bundle, request, reproduced/DIFFERS, and
for each config the kind, refusal class, yield roles and view tags.
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import yaml
from swarm_orchestrator.models import RobotView, SceneSnapshot, load_config
from swarm_orchestrator.reasoning_pipeline import build_reasoner_request, load_grounding_source

from reasoning.vlm.models import CongestionDecision, ReasonerDiagnostics, ReasonerResult

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import s1_grounding_replay as G  # noqa: E402
import s1b_guard_counterfactual as C  # noqa: E402


def _summary(command: dict) -> tuple:
    tags = [
        t
        for t in command.get("degradations", [])
        if "dynamic_arms" in t or "handoff" in t or "regrounded" in t
    ]
    return C._kind(command), C._refusal_class(command), C._yield_room(command), tags


def replay(bundle: Path) -> list[str]:
    """One line per yield analysis of `bundle`."""
    raw = yaml.safe_load((bundle / "orchestrator.overlaid.yaml").read_text())
    config = load_config(raw)
    params = load_grounding_source(REPO / config.grounding_params_path).params
    overlay = G._overlay(REPO / "isaac/config/scenarios/mapd_5_s1b.yaml")
    boxes = (
        load_config({**raw, "scenario_geometry": overlay["scenario_geometry"]})
        if "s1b" in bundle.name
        else config
    )
    lines = []
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
        for label, cfg in (("bundle_overlay", config), ("boxes_overlay", boxes)):
            pipe, stored = C._pipeline(cfg, params, cfg.scenario_geometry, goals)
            stored.result = result
            out[label] = pipe.run(request).grounded_command
        live = art.get("dispatched_command")
        reproduced = (
            live is not None
            and C._actions(out["bundle_overlay"]) == C._actions(live)
            and out["bundle_overlay"].get("degradations") == live.get("degradations")
        )
        lines.append(
            f"{bundle.name} {art['request_id'][:8]} "
            f"{'reproduced' if reproduced else 'DIFFERS'} "
            f"|bundle: {_summary(out['bundle_overlay'])} |boxes: {_summary(out['boxes_overlay'])}"
        )
    return lines


def main() -> None:
    """Entry point."""
    for bundle in sys.argv[1:]:
        print("\n".join(replay(Path(bundle))))


if __name__ == "__main__":
    main()

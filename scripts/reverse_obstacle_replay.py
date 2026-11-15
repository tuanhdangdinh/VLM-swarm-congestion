"""Offline replay of recorded `reverse` decisions with the reverse obstacle guard off and on.

Report: docs/reports/2026-11-15-escort-obstacle-guard.md, section 8. Read-only
on the bundles; no VM, no API call. Sibling of `escort_obstacle_replay.py`.

For every decision artifact of each bundle given whose decided strategy is
`reverse` and whose dispatched command carries at least one `reverse` action
(junction_clear recede phases are a different manoeuvre and are skipped):

1. Leg check on the LIVE dispatched legs (snapshot pose, heading theta + pi,
   the dispatched `backup_distance_m`; `escort_obstacles.reverse_obstacle_hits`)
   against the bundle's declared `static_obstacles`, grown by
   `robot.half_width_m` plus the bundle's own `retreat_box_margin_m`.
2. Re-grounding of the stored decision through `ground_reasoner_result` on
   this tree, with the artifact's own grounding params, the bundle's scenario
   geometry and static obstacles, and the snapshot goals: guard off (must
   reproduce the live actions, M5's `plan_id` aside) and guard on (the
   verdict). Only derived-mode artifacts re-ground.
3. Physical record per reversing robot: M4's last published status for the
   command (`m4.log`), and from ground truth the distance moved from the
   pose at M4's handover (`handoff guard ... reason=handover sim_t=`) until
   the leg's distance is reached, the robot turns back, or 150 s pass. With
   `--contact-root DIR` (a checkout carrying `isaac/vgu_sim/contact_geometry.py`,
   e.g. the GT contact-recompute branch) the minimum URDF-footprint gap to
   every box the scene builders author is measured over that window too.

Usage (repo root):
    PYTHONPATH=.:ros2_ws/src/swarm_orchestrator:ros2_ws/src/swarm_execution \\
        python scripts/reverse_obstacle_replay.py [--contact-root DIR] <bundle_dir> [...]

Prints one tab-separated row per reversing robot.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from swarm_orchestrator.models import load_config

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.escort_obstacles import reverse_obstacle_hits
from reasoning.rag.grounding_view import resolve_grounding_view
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)

# M5's plan id is added after grounding.
_IGNORED = {"plan_id"}
_WINDOW_SEC = 150.0


def _frame(scene: dict[str, Any]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=scene["stamp"],
        robots=[
            RobotStateInput(
                robot_id=r["robot_id"],
                x=r["x"],
                y=r["y"],
                theta=r["theta"],
                status=r["status"],
                goal=None if r.get("goal") is None else tuple(r["goal"]),
            )
            for r in scene["robots"]
        ],
    )


def _actions(command: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **a,
            "parameters": {k: v for k, v in (a.get("parameters") or {}).items() if k not in _IGNORED},
        }
        for a in command.get("actions", [])
    ]


def _reground(artifact: dict[str, Any], config: Any, params: GroundingParams) -> dict[str, Any]:
    frame = _frame(artifact["scene"])
    diag = ReasonerDiagnostics(request_id="r", backend_id="mock", attempts=1, parse_status="valid")
    result = ReasonerResult(
        request_id=artifact["request_id"],
        decision=CongestionDecision.model_validate(artifact["decision"]),
        raw_text="{}",
        diagnostics=diag,
    )
    return ground_reasoner_result(
        result,
        robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=artifact.get("grounding_yield_feasibility")
        or config.grounding_yield_feasibility,
        snapshot=frame,
        params=params,
        goal_references={s.robot_id: s.goal for s in frame.robots if s.goal is not None},
    )


def _ground_truth(bundle: Path) -> list[tuple[float, dict[str, Any]]]:
    for name in ("gt/ground_truth.jsonl", "ground_truth/ground_truth.jsonl"):
        path = bundle / name
        if path.is_file():
            rows = []
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    rows.append((float(row["sim_time_sec"]), row["robots"]))
            return rows
    return []


def _static_boxes(bundle: Path, contact: Any) -> tuple[Any, ...]:
    if contact is None:
        return ()
    config_module = importlib.import_module("isaac.vgu_sim.config")
    scenario = config_module.ScenarioConfig.model_validate(
        yaml.safe_load((bundle / "scenario.yaml").read_text(encoding="utf-8"))
    )
    return contact.scene_static_boxes(scenario)


def _physical(
    rows: list[tuple[float, dict[str, Any]]],
    robot_id: str,
    distance_m: float,
    t0: float,
    contact: Any,
    boxes: tuple[Any, ...],
) -> str:
    start: tuple[float, float] | None = None
    moved = 0.0
    best: tuple[float, str, float] | None = None
    for t, robots in rows:
        if t < t0 or robot_id not in robots:
            continue
        r = robots[robot_id]
        if start is None:
            start = (r["x"], r["y"])
        displacement = math.hypot(r["x"] - start[0], r["y"] - start[1])
        if displacement < moved - 0.05:
            break
        moved = max(moved, displacement)
        for box in boxes:
            active_from = getattr(box, "active_from_sec", None)
            active_until = getattr(box, "active_until_sec", None)
            if (active_from is not None and t < active_from) or (
                active_until is not None and t >= active_until
            ):
                continue
            gap = contact.robot_box_gap((r["x"], r["y"], r["theta"]), box)
            if gap is not None and (best is None or gap < best[0]):
                best = (gap, box.obstacle_id, t)
        if displacement >= distance_m - 0.005 or t > t0 + _WINDOW_SEC:
            break
    if start is None:
        return "no GT"
    text = f"moved {moved:.3f} m"
    if best is not None:
        text += f"; min footprint gap {best[0]:.4f} m ({best[1]}, sim {best[2]:.1f} s)"
    return text


def replay(bundle: Path, contact: Any) -> list[str]:
    """One row per reversing robot of each dispatched `reverse` decision in `bundle`."""
    config = load_config(yaml.safe_load((bundle / "orchestrator.overlaid.yaml").read_text()))
    m4_log = bundle / "m4.log"
    m4 = m4_log.read_text(errors="replace") if m4_log.is_file() else ""
    gt = None
    boxes: tuple[Any, ...] = ()
    rows: list[str] = []
    for path in sorted((bundle / "decisions").glob("*.json")):
        if path.name.startswith("tasks_"):
            continue
        artifact = json.loads(path.read_text())
        decision = artifact.get("decision") or {}
        live = artifact.get("dispatched_command") or {}
        legs = [
            (a["robot_id"], float(a["parameters"]["backup_distance_m"]))
            for a in live.get("actions", [])
            if a.get("action") == "reverse"
        ]
        if decision.get("strategy") != "reverse" or not legs:
            continue
        if gt is None:
            gt = _ground_truth(bundle)
            boxes = _static_boxes(bundle, contact)
        params = GroundingParams(**artifact["grounding_params_source"]["params"])
        frame = _frame(artifact["scene"])
        geometry = config.scenario_geometry
        if geometry is not None:
            geometry = resolve_grounding_view(
                CongestionDecision.model_validate(decision), frame, geometry, params,
                {s.robot_id: s.goal for s in frame.robots if s.goal is not None},
            ).geometry
        half = geometry.robot.half_width_m if geometry is not None else 0.09
        hits = {
            hit.robot_id: hit
            for hit in reverse_obstacle_hits(
                legs, frame, config.static_obstacles, half + params.retreat_box_margin_m
            )
        }
        if artifact.get("grounding_mode") != "derived" or params.mode != "derived":
            verdict, repro = "n/a (legacy mode)", "-"
        else:
            off = _reground(artifact, config, params)
            on = _reground(artifact, config, params.model_copy(update={"reverse_obstacle_guard": True}))
            repro = (
                "reproduced"
                if _actions(off) == _actions(live)
                and off.get("degradations", []) == live.get("degradations", [])
                else "DIFFERS"
            )
            if on == off:
                verdict = "unchanged"
            else:
                tags = [t for t in on.get("degradations", []) if "reverse_hits_obstacle" in t]
                verdict = "refused: " + "; ".join(t.split(":", 1)[1] for t in tags)
        command_id = live.get("command_id", "")
        for robot_id, distance_m in legs:
            handover = re.search(
                rf"controller stop robot={robot_id} command={re.escape(command_id)} "
                r"action=reverse reason=handover sim_t=([0-9.]+)",
                m4,
            )
            t0 = float(handover.group(1)) if handover else float(artifact["scene"]["stamp"])
            statuses = re.findall(
                rf"status published command={re.escape(command_id)} robot={robot_id} "
                r"status=(\w+)",
                m4,
            )
            hit = hits.get(robot_id)
            rows.append(
                "\t".join(
                    [
                        bundle.name,
                        artifact["request_id"][:8],
                        robot_id,
                        f"L={distance_m:.3f}",
                        "leg clear" if hit is None else f"leg hits {hit.obstacle_id}@{hit.clear_m:.3f}",
                        repro,
                        verdict,
                        f"M4 {statuses[-1] if statuses else 'no status'}",
                        _physical(gt or [], robot_id, distance_m, t0, contact, boxes),
                    ]
                )
            )
    return rows


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contact-root", type=Path, default=None)
    parser.add_argument("bundles", nargs="+", type=Path)
    args = parser.parse_args()
    contact = None
    if args.contact_root is not None:
        # This tree's `isaac` package has no contact_geometry module, so the
        # other checkout must come first; the M3 packages are already
        # imported from this tree, and only `isaac` is resolved after this.
        if "isaac" in sys.modules:
            raise SystemExit("isaac was imported before --contact-root could take effect")
        sys.path.insert(0, str(args.contact_root.resolve()))
        contact = importlib.import_module("isaac.vgu_sim.contact_geometry")
    for path in args.bundles:
        if not path.is_dir():
            continue
        if not (path / "orchestrator.overlaid.yaml").is_file():
            print(f"{path.name}\tskipped: no orchestrator.overlaid.yaml")
            continue
        for row in replay(path, contact):
            print(row)


if __name__ == "__main__":
    main()

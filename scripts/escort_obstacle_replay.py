"""Offline replay of recorded escort decisions with the escort obstacle guard off and on.

Report: docs/reports/2026-11-15-escort-obstacle-guard.md. Read-only on the
bundles; no VM, no API call.

For every decision artifact of each bundle given whose dispatched command
(or, for `junction_clear`, any phase or fallback command) carries an escort:

1. Leg check on the LIVE dispatched leg (snapshot start, dispatched heading
   and distance, `escort_clearance.escort_drives`): the minimum
   centreline-to-bare-box distance over the bundle's declared
   `static_obstacles`, and whether the leg enters a box grown by
   `robot.half_width_m` plus the bundle's own `retreat_box_margin_m`, and
   plus the kit margin 0.05 m.
2. Re-grounding of the stored decision through `ground_reasoner_result` on
   this tree, with the artifact's own grounding params, the bundle's
   scenario geometry and static obstacles, the stored stage-2 label and the
   snapshot goals: guard off (must reproduce the live yield action) and
   guard on (the verdict). Only derived-mode yields re-ground; legacy and
   `junction_clear` rows get the leg check only.

Usage (repo root):
    PYTHONPATH=.:ros2_ws/src/swarm_orchestrator:ros2_ws/src/swarm_execution \\
        python scripts/escort_obstacle_replay.py <bundle_dir> [...]

Prints one tab-separated row per escort.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from swarm_orchestrator.models import load_config

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.escort_clearance import escort_drives
from reasoning.rag.escort_obstacles import escort_obstacle_hits, grown_obstacle_boxes
from reasoning.rag.grounding_view import resolve_grounding_view
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RetreatChoiceDecision,
    RobotStateInput,
    SnapshotFrame,
)

KIT_MARGIN_M = 0.05
# M5's plan id and the A26(ii) fast-fail mark are added after grounding.
_IGNORED = {"plan_id", "fresh_latch_fast_fail", "retreat_shield_hold"}


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


def _escort_commands(artifact: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    dispatched = artifact.get("dispatched_command")
    if dispatched:
        out.append(("dispatched", dispatched))
    phases = artifact.get("junction_phases") or {}
    for index, phase in enumerate(phases.get("phases") or []):
        if phase.get("command"):
            out.append((f"phase{index}", phase["command"]))
    if phases.get("fallback_command"):
        out.append(("fallback", phases["fallback_command"]))
    return [
        (where, command)
        for where, command in out
        if any(
            (a.get("parameters") or {}).get("passer_escort_distance_m") is not None
            for a in command.get("actions", [])
            if a.get("action") == "yield"
        )
    ]


def _yield(command: dict[str, Any]) -> dict[str, Any] | None:
    return next((a for a in command.get("actions", []) if a.get("action") == "yield"), None)


def _stripped(parameters: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in parameters.items() if k not in _IGNORED}


def _bare_distance(drive: Any, obstacles: Any) -> tuple[float, str]:
    best = (math.inf, "-")
    for box in grown_obstacle_boxes(obstacles, 0.0):
        # Sampled at 1 mm: a reporting figure, not the guard's test.
        steps = max(1, int(drive.distance_m / 0.001))
        for i in range(steps + 1):
            t = drive.distance_m * i / steps
            x = drive.start_xy[0] + t * math.cos(drive.heading_rad)
            y = drive.start_xy[1] + t * math.sin(drive.heading_rad)
            dx = max(box.x_min - x, 0.0, x - box.x_max)
            dy = max(box.y_min - y, 0.0, y - box.y_max)
            d = math.hypot(dx, dy)
            if d < best[0]:
                best = (d, box.obstacle_id)
    return best


def _outcome(bundle: Path, request_id: str) -> str:
    # Admission and M4's odometry release of the escorted passer; the
    # escort's own end (distance or deadline) is not logged per command.
    log = bundle / "m4.log"
    if not log.is_file():
        return "no m4.log"
    text = log.read_text(errors="replace")
    admitted = f"gate_admit command={request_id}" in text
    cleared = re.search(rf"gate_cleared command={request_id}\S* .*?moved_m=([0-9.]+)", text)
    parts = ["admitted" if admitted else "not admitted"]
    parts.append(f"cleared, moved {cleared.group(1)} m" if cleared else "never cleared")
    return ", ".join(parts)


def _reground(
    artifact: dict[str, Any], config: Any, params: GroundingParams
) -> dict[str, Any]:
    frame = _frame(artifact["scene"])
    label = (artifact.get("stage2") or {}).get("grounded_label")
    diag = ReasonerDiagnostics(request_id="r", backend_id="mock", attempts=1, parse_status="valid")
    result = ReasonerResult(
        request_id="r",
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
        retreat_choice=(
            None
            if label is None
            else RetreatChoiceDecision(retreat_choice=label, justification="replay")
        ),
        goal_references={s.robot_id: s.goal for s in frame.robots if s.goal is not None},
    )


def replay(bundle: Path) -> list[str]:
    """One row per escort in `bundle`."""
    config = load_config(yaml.safe_load((bundle / "orchestrator.overlaid.yaml").read_text()))
    rows: list[str] = []
    for path in sorted((bundle / "decisions").glob("*.json")):
        if path.name.startswith("tasks_"):
            continue
        artifact = json.loads(path.read_text())
        for where, command in _escort_commands(artifact):
            action = _yield(command)
            assert action is not None
            live = action["parameters"]
            params = GroundingParams(**artifact["grounding_params_source"]["params"])
            frame = _frame(artifact["scene"])
            decision = CongestionDecision.model_validate(artifact["decision"])
            geometry = config.scenario_geometry
            if decision.strategy == "yield" and geometry is not None:
                geometry = resolve_grounding_view(
                    decision, frame, geometry, params,
                    {s.robot_id: s.goal for s in frame.robots if s.goal is not None},
                ).geometry
            drives = escort_drives(action["robot_id"], live, frame, geometry)
            half = geometry.robot.half_width_m if geometry is not None else 0.09
            own = escort_obstacle_hits(
                action["robot_id"], live, frame, geometry, config.static_obstacles,
                half + params.retreat_box_margin_m,
            )
            kit = escort_obstacle_hits(
                action["robot_id"], live, frame, geometry, config.static_obstacles,
                half + KIT_MARGIN_M,
            )
            bare = [_bare_distance(d, config.static_obstacles) for d in drives]
            leg = "; ".join(
                f"{d.passer_id} ({d.start_xy[0]:.3f},{d.start_xy[1]:.3f}) "
                f"h={d.heading_rad:.3f} L={d.distance_m:.3f} "
                f"min_bare={b[0]:.3f}({b[1]})"
                for d, b in zip(drives, bare, strict=True)
            ) or "no leg"
            hits = lambda hs: (  # noqa: E731
                "clear" if not hs else ", ".join(
                    f"{h.passer_id}->{h.obstacle_id}@{h.clear_m:.3f}" for h in hs
                )
            )
            verdict = "-"
            repro = "-"
            if where != "dispatched":
                verdict = "n/a (junction_clear phase; not re-grounded)"
            elif artifact.get("grounding_mode") != "derived" or params.mode != "derived":
                verdict = "n/a (legacy mode)"
            elif decision.strategy not in ("yield", "convoy", "priority_override"):
                verdict = f"n/a ({decision.strategy})"
            else:
                off = _reground(artifact, config, params)
                on = _reground(
                    artifact, config, params.model_copy(update={"escort_obstacle_guard": True})
                )
                off_yield = _yield(off)
                repro = (
                    "reproduced"
                    if off_yield is not None
                    and _stripped(off_yield["parameters"]) == _stripped(live)
                    else "DIFFERS"
                )
                if on == off:
                    verdict = "unchanged"
                elif _yield(on) is None:
                    cause = [t for t in on.get("degradations", []) if "escort_hits_obstacle" in t]
                    verdict = "refused: " + (cause[0] if cause else str(on.get("degradations")))
                else:
                    verdict = "changed: " + json.dumps(
                        {
                            k: (off_yield or {}).get("parameters", {}).get(k)
                            for k in ("retreat_choice", "passer_escort_distance_m")
                        }
                    ) + " -> " + json.dumps(
                        {
                            k: _yield(on)["parameters"].get(k)
                            for k in ("retreat_choice", "passer_escort_distance_m")
                        }
                    )
            rows.append(
                "\t".join(
                    [
                        bundle.name,
                        artifact["request_id"][:8],
                        where,
                        str(artifact.get("grounding_mode")),
                        f"margin_own={params.retreat_box_margin_m}",
                        leg,
                        f"own:{hits(own)}",
                        f"kit:{hits(kit)}",
                        repro,
                        verdict,
                        _outcome(bundle, artifact["request_id"]),
                    ]
                )
            )
    return rows


def main() -> None:
    """Entry point."""
    for bundle in sys.argv[1:]:
        path = Path(bundle)
        if not path.is_dir():
            continue
        if not (path / "orchestrator.overlaid.yaml").is_file():
            print(f"{path.name}\tskipped: no orchestrator.overlaid.yaml")
            continue
        for row in replay(path):
            print(row)


if __name__ == "__main__":
    main()

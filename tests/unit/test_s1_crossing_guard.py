"""prereg-v3 A16(iii): the dynamic crossing view requires a DECLARED junction.

The dynamic-arms view's crossing branch builds arms on the declared corridor
box. On S1a that box is the real plus-junction; on the open S1b floor (the
same box declared, no junction there) it anchored to S1a's junction and
grounded phantom geometry for 57/400 MC first conflicts (7 of them as
"executable" yields, 1 as a fabricated 0.00 m refusal). Absent a declaration
(`SceneGeometry.junction_declared`) a crossing yield now refuses honestly,
which `refusal_no_action` withholds like every other `yield refused:` fan-out.

Fixtures (`data/s1_crossing_guard/fixtures.json`) are two such S1b first
conflicts with what feat/v3-integration@56836a4 grounded for them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from swarm_orchestrator.models import load_config
from swarm_orchestrator.reasoning_pipeline import load_grounding_source, yield_refusal_fan_out

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.grounding_view import derive_dynamic_arms
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ORCH = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
SCENARIOS = {
    "s1a": REPO_ROOT / "isaac/config/scenarios/mapd_5.yaml",
    "s1b": REPO_ROOT / "isaac/config/scenarios/mapd_5_s1b.yaml",
}
CASES = json.loads(
    (Path(__file__).parent / "data" / "s1_crossing_guard" / "fixtures.json").read_text()
)["cases"]


def _floor(floor: str):
    lines = SCENARIOS[floor].read_text().splitlines()
    begin = lines.index("#   --- M5 overlay begin ---")
    end = lines.index("#   --- M5 overlay end ---")
    overlay = yaml.safe_load("\n".join(line[4:] for line in lines[begin + 1 : end]))
    raw = yaml.safe_load(ORCH.read_text())
    raw.update(overlay)
    config = load_config(raw)
    params = load_grounding_source(REPO_ROOT / overlay["grounding_params_path"]).params
    return config, params


def _frame(rows: list[dict[str, Any]]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(
                robot_id=r["robot_id"], x=r["x"], y=r["y"], theta=r["theta"],
                status=r["status"], goal=tuple(r["goal"]),
            )
            for r in rows
        ],
    )


def _decision(involved: list[str], strategy: str = "yield") -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=True, type="deadlock", involved_robots=involved,
        root_cause="echo", strategy=strategy, justification="echo",
        yield_robot=involved[0] if strategy == "yield" else None,
    )


def _ground(name: str, *, junction_declared: bool | None = None) -> dict:
    case = CASES[name]
    config, params = _floor(case["floor"])
    geometry = config.scenario_geometry
    if junction_declared is not None:
        # The pre-guard view: S1a's declared corridor box as the only
        # junction, so S1b's A20(1) boxes are cleared with the flag.
        geometry = geometry.model_copy(
            update={"junction_declared": junction_declared, "junction_boxes": None}
        )
    frame = _frame(case["rows"])
    diag = ReasonerDiagnostics(request_id="r", backend_id="mock", attempts=1, parse_status="valid")
    result = ReasonerResult(
        request_id="r", decision=_decision(case["involved"]), raw_text="{}", diagnostics=diag
    )
    return ground_reasoner_result(
        result,
        robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
        geometry=geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        snapshot=frame,
        params=params,
    )


def test_s1a_declares_its_junction_and_s1b_declares_its_crossing_boxes():
    # prereg-v3 A20(1): S1b now declares its real crossings (test_s1b_rulings_a20).
    assert _floor("s1a")[0].scenario_geometry.junction_declared is True
    assert _floor("s1a")[0].scenario_geometry.junction_boxes is None
    s1b = _floor("s1b")[0].scenario_geometry
    assert s1b.junction_declared is True
    assert [box.name for box in s1b.junction_boxes] == ["NW", "SW", "N", "S"]


def test_fabricated_crossing_room_now_refuses_with_its_true_reason():
    case = CASES["s1b_seed22"]
    assert any(" 0.00 m" in tag for tag in case["baseline_degradations"])

    command = _ground("s1b_seed22")

    # A20(1): seed 22's pair sits at island_w's SW corner, outside every
    # declared S1b crossing box, so it still refuses, naming the boxes.
    reason = (
        "yield refused: no declared junction: robot_1 runs along y and robot_4 along x "
        "(a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no "
        "retreat room was measured"
    )
    assert yield_refusal_fan_out(command) == reason
    assert "grounding=dynamic_arms:crossing_refused:robot_1,robot_4" in command["degradations"]
    assert not any(" 0.00 m" in tag for tag in command["degradations"])


def test_phantom_executable_crossing_yield_now_refuses():
    case = CASES["s1b_seed15"]
    assert case["baseline_label"] == "executable_yield"
    assert "grounding=dynamic_arms:crossing" in case["baseline_degradations"]

    command = _ground("s1b_seed15")

    assert not any(a["action"] == "yield" for a in command["actions"])
    assert yield_refusal_fan_out(command).startswith("yield refused: no declared junction:")
    assert {a["robot_id"] for a in command["actions"]} == set(case["involved"])


@pytest.mark.parametrize("name", sorted(CASES))
def test_declaring_the_junction_restores_the_old_grounding(name: str):
    command = _ground(name, junction_declared=True)

    assert command["degradations"] == CASES[name]["baseline_degradations"]


def test_reverse_keeps_the_declared_geometry_without_a_junction():
    case = CASES["s1b_seed22"]
    config, params = _floor("s1b")

    arms = derive_dynamic_arms(
        _decision(case["involved"], strategy="reverse"),
        _frame(case["rows"]),
        config.scenario_geometry,
        params,
    )

    assert arms.refusal_reason is None
    assert arms.geometry == config.scenario_geometry
    assert arms.tags[-1] == "grounding=dynamic_arms:crossing_undeclared"

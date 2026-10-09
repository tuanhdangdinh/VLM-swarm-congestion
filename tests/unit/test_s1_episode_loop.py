"""S1 episode loop fixes from the E1 closed-loop episode (2026-10-09).

E1 (`s1r_E1_seed1_echo`, seed 978442588, echo mock) ran 46 analyses. 44 of
them refused the yield, each dispatching an all-robot 8 s `temporary_wait`
that cancelled Nav2 goals before any recovery could fire and kept the
scene-unchanged suppression from arming (0 suppressed lines). Fix 1
(`refusal_no_action`, task stream only) withholds such a refusal. The one
executable yield (`cb78cd48`) escorted robot_5 a fixed 2.35 m, 0.4 m past
its S turn. Fix 2 (`escort_turn_cap`, dynamic mode only) caps the escort and
clearance at the passer's distance to its turn.

The poses below are the E1 decision artifacts' `scene` blocks, verbatim.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from swarm_orchestrator.models import (
    PipelineOutcome,
    ReanalysisSuppressionConfig,
    TerminalStage,
    load_config,
)
from swarm_orchestrator.reasoning_pipeline import (
    load_grounding_source,
    yield_refusal_fan_out,
)

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.grounding_view import apply_escort_headings
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _make_node,
    _result,
    node_env,
)
from tests.unit.test_m5_node_task_stream import _make as _make_stream_node
from tests.unit.test_m5_reanalysis_suppression import BASE, COOLDOWN, _feed

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPD = REPO_ROOT / "isaac/config/scenarios/mapd_5.yaml"
ORCH = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
GROUNDING_FILE = REPO_ROOT / "config/grounding/s1_dynamic.yaml"

Pose = tuple[float, float, float]

# E1 artifact cb78cd48 (M1 stamp 48.47): the one executable yield.
_CB78: dict[str, Pose] = {
    "robot_1": (1.6605256627206582, 0.045761790314885475, 0.04758234750964273),
    "robot_2": (-0.047941685800333755, 1.4752729544370227, 0.2573198000065904),
    "robot_3": (-0.5753002296040073, -0.5284397214933204, -3.066733992238548),
    "robot_4": (-0.42384808582567957, 0.658098127385496, 0.9760296868249412),
    "robot_5": (2.0004757983957537, 0.0, 3.141592653589793),
}
_CB78_GOALS = {
    "robot_1": (2.3, 0.0),
    "robot_2": (0.0, 1.55),
    "robot_3": (-2.3, 0.35),
    "robot_4": (0.0, 1.55),
    "robot_5": (0.0, -1.55),
}
# E1 artifact 0d771703 (M1 stamp 186.13): one of the 44 identical refusals.
_REFUSED: dict[str, Pose] = {
    "robot_1": (0.6777211038138121, -0.22662981870229004, -0.33666985947977973),
    "robot_2": (-0.046852102032144294, 1.4752729544370227, 0.2509988595140578),
    "robot_3": (-0.5742106458358179, -0.5273501550572518, -3.044340992618844),
    "robot_4": (-0.1438250574010016, 1.072133373091603, 0.9964842413481819),
    "robot_5": (-0.4576251826395512, -0.15798713322996194, -1.7635000754914252),
}
_REFUSED_GOALS = {
    "robot_1": (2.3, 0.0),
    "robot_2": (-2.3, 0.35),
    "robot_3": (-2.3, 0.35),
    "robot_4": (0.0, 1.55),
    "robot_5": (0.0, -1.55),
}
_E1_REFUSAL = (
    "yield refused: no feasible yielder (robot_4 0.00 m, robot_2 0.00 m, robot_1 0.00 m, "
    "robot_3 0.00 m, robot_5 0.00 m retreat room < 0.95 m required)"
)
_FIVE = ["robot_1", "robot_2", "robot_3", "robot_4", "robot_5"]


def _overlay() -> dict[str, Any]:
    lines = MAPD.read_text().splitlines()
    begin = lines.index("#   --- M5 overlay begin ---")
    end = lines.index("#   --- M5 overlay end ---")
    return yaml.safe_load("\n".join(line[4:] for line in lines[begin + 1:end]))


def _shipped_params() -> GroundingParams:
    return load_grounding_source(GROUNDING_FILE).params


def _ground(
    poses: dict[str, Pose],
    goals: dict[str, tuple[float, float]],
    involved: list[str],
    params: GroundingParams,
) -> dict[str, Any]:
    raw = yaml.safe_load(ORCH.read_text())
    raw.update(_overlay())
    config = load_config(raw)
    frame = SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=theta, goal=goals[rid])
            for rid, (x, y, theta) in poses.items()
        ],
    )
    decision = CongestionDecision(
        congestion_detected=True, type="deadlock", involved_robots=involved,
        root_cause="echo", strategy="yield", justification="echo", yield_robot="robot_1",
    )
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    result = ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)
    return ground_reasoner_result(
        result,
        robot_positions={rid: (x, y) for rid, (x, y, _t) in poses.items()},
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        snapshot=frame,
        params=params,
        goal_references=goals,
    )


# ---- Phase 1 diagnosis, pinned ----


def test_e1_refusal_reproduces_through_the_ambiguous_declared_fallback():
    # robot_4 (the N-node arriver) heads 57 deg, outside the 30 deg axis snap,
    # so the view keeps the declared x-axis junction box with the aisle band:
    # each flanking rack's face sits on the declared mouth (x = +-0.6) and
    # every robot reads 0.00 m, byte-identical to the live artifact.
    command = _ground(_REFUSED, _REFUSED_GOALS, _FIVE, _shipped_params())
    assert "grounding=dynamic_arms:ambiguous" in command["degradations"]
    assert "grounding=node_handoff:robot_4->robot_2" in command["degradations"]
    assert yield_refusal_fan_out(command) == _E1_REFUSAL


# ---- Fix 1: refusal fan-out detection ----


def test_refusal_fan_out_detects_the_e1_refusal_waits():
    command = _ground(_REFUSED, _REFUSED_GOALS, _FIVE, _shipped_params())
    assert {a["action"] for a in command["actions"]} == {"temporary_wait"}
    assert yield_refusal_fan_out(command) == _E1_REFUSAL


def test_refusal_fan_out_ignores_a_lane_scoped_yield_with_off_lane_waits():
    command = _ground(
        _CB78, _CB78_GOALS, ["robot_1", "robot_2", "robot_3", "robot_5"], _shipped_params()
    )
    assert command["actions"][0]["action"] == "yield"
    assert any(
        (a["parameters"] or {}).get("requested_strategy") == "yield"
        for a in command["actions"][1:]
    )
    assert yield_refusal_fan_out(command) is None


def test_refusal_fan_out_ignores_a_non_refusal_wait_fan_out():
    command = {
        "command_id": "c-convoy",
        "actions": [
            {"robot_id": rid, "action": "temporary_wait",
             "parameters": {"duration_sec": 8.0, "requested_strategy": "convoy"}}
            for rid in ("robot_1", "robot_2")
        ],
    }
    assert yield_refusal_fan_out(command) is None


def test_refusal_fan_out_none_command_is_none():
    assert yield_refusal_fan_out(None) is None


# ---- Fix 1: node behaviour ----


def _refusal_command(request_id: str) -> dict[str, Any]:
    reason = "yield refused: no feasible yielder (robot_2 0.00 m, robot_1 0.00 m)"
    return {
        "command_id": f"cmd-{request_id}",
        "actions": [
            {"robot_id": rid, "action": "temporary_wait",
             "parameters": {"duration_sec": 8.0, "requested_strategy": "yield",
                            "reason": reason}}
            for rid in ("robot_2", "robot_1")
        ],
        "expected_resolution_time_sec": 8.0,
        "fallback": "stop",
    }


class _RefusingPipeline:
    def __init__(self) -> None:
        self.run_calls: list[str] = []

    def run(self, request):
        self.run_calls.append(request.request_id)
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id),
            grounded_command=_refusal_command(request.request_id),
            terminal_stage=TerminalStage.OK,
        )

    def analyze(self, request):  # pragma: no cover - probe mode is off here
        raise AssertionError("no probe expected")


def _node(node_env, tmp_path, *, withhold: bool, suppression=True):  # noqa: F811
    pipeline = _RefusingPipeline()
    node, clock = _make_node(
        node_env, tmp_path, pipeline,
        t0_probe_mode=False,
        refusal_no_action=withhold,
        reanalysis_suppression=(
            {"enabled": True, "applies_to": "all"} if suppression
            else ReanalysisSuppressionConfig()
        ),
    )
    # The task-stream gate is covered by its own tests below; a stream-off
    # node exercises the outcome handling without the stream's bookkeeping.
    node._refusal_no_action = withhold
    return node, clock, pipeline


def _cycle(node, clock, advance: float = COOLDOWN + 1.0) -> None:
    clock.t += advance
    _feed(node, clock.t - 900.0, BASE)
    if node._future is not None:
        node._future.result(timeout=WAIT_SEC)
        node._on_timer()


def _artifact(node, request_id: str) -> dict:
    path = Path(node._config.decision_log_dir) / f"{request_id}.json"
    return json.loads(path.read_text())


def test_withheld_refusal_publishes_nothing(node_env, tmp_path):  # noqa: F811
    node, clock, pipeline = _node(node_env, tmp_path, withhold=True)
    _cycle(node, clock)
    assert len(pipeline.run_calls) == 1
    assert node._cmd_pub.published == []
    assert node.get_logger().matching("refusal withheld request=")


def test_withheld_refusal_is_recorded_in_the_artifact(node_env, tmp_path):  # noqa: F811
    node, clock, pipeline = _node(node_env, tmp_path, withhold=True)
    _cycle(node, clock)
    artifact = _artifact(node, pipeline.run_calls[0])
    assert artifact["dispatch_withheld"] == {
        "reason": "refusal_no_action",
        "refusal_reason": "yield refused: no feasible yielder (robot_2 0.00 m, robot_1 0.00 m)",
        "would_dispatch_robot_ids": ["robot_2", "robot_1"],
    }
    assert "dispatch_suppressed" not in artifact


def test_withheld_refusal_arms_the_suppression(node_env, tmp_path):  # noqa: F811
    node, clock, pipeline = _node(node_env, tmp_path, withhold=True)
    for _ in range(4):
        _cycle(node, clock)
    assert len(pipeline.run_calls) == 1
    assert node.get_logger().matching("outcome=refusal_no_action")
    assert node._suppression.suppressed_triggers_total == 3
    assert node._suppression.avoided_analyses_total > 0


def test_withheld_refusal_starts_a_cooldown(node_env, tmp_path):  # noqa: F811
    node, clock, _pipeline = _node(node_env, tmp_path, withhold=True, suppression=False)
    _cycle(node, clock)
    assert node._cooldown.active_robots(clock.t) == {"robot_1", "robot_2"}


def test_withheld_refusal_counts_no_failure(node_env, tmp_path):  # noqa: F811
    node, clock, _pipeline = _node(node_env, tmp_path, withhold=True)
    _cycle(node, clock)
    assert node._machine.failure_count("robot_1") == 0
    assert node._machine.failure_count("robot_2") == 0


def test_default_off_refusal_still_dispatches_and_never_arms(node_env, tmp_path):  # noqa: F811
    node, clock, pipeline = _node(node_env, tmp_path, withhold=False)
    _cycle(node, clock)
    assert len(node._cmd_pub.published) == 2
    assert "dispatch_withheld" not in _artifact(node, pipeline.run_calls[0])
    assert node._suppression.reference is None
    assert node.get_logger().matching("refusal withheld") == []


def test_refusal_no_action_without_a_stream_is_inert(node_env, tmp_path):  # noqa: F811
    node, _clock = _make_node(
        node_env, tmp_path, _RefusingPipeline(), t0_probe_mode=False, refusal_no_action=True
    )
    assert node._refusal_no_action is False
    assert node.get_logger().matching("refusal_no_action is set but task_stream is disabled")


def test_refusal_no_action_engages_with_the_stream(node_env, tmp_path):  # noqa: F811
    node, _clock, _ = _make_stream_node(node_env, tmp_path, refusal_no_action=True)
    assert node._refusal_no_action is True


def test_stream_node_defaults_to_dispatching_refusals(node_env, tmp_path):  # noqa: F811
    node, _clock, _ = _make_stream_node(node_env, tmp_path)
    assert node._refusal_no_action is False


# ---- Fix 2: escort capped at the passer's turn ----

# The live cb78 yield action (E1 artifact `dispatched_command`, plan_id
# dropped): the uncapped escort M4 actually ran.
_CB78_LIVE_YIELD = {
    "backup_distance_m": 1.36,
    "backup_line_hold": True,
    "crossing_order": ["robot_5"],
    "hold_sec": 45.0,
    "passer_clear_m": 2.35,
    "passer_escort_distance_m": 2.35,
    "passer_escort_heading_rad": 3.141593,
    "passer_escort_reference_yaw_rad": 3.141593,
    "passer_robot_id": "robot_5",
    "pull_off_lateral_m": -0.36,
    "reason": "echo",
    "retreat_choice": "B",
    "retreat_x_m": 0.301,
    "retreat_y_m": -0.314,
}
_CB78_INVOLVED = ["robot_1", "robot_2", "robot_3", "robot_5"]


def test_cap_off_keeps_the_e1_escort_byte_identical():
    params = _shipped_params().model_copy(update={"escort_turn_cap": False})
    command = _ground(_CB78, _CB78_GOALS, _CB78_INVOLVED, params)
    assert command["actions"][0]["parameters"] == _CB78_LIVE_YIELD
    assert not any(t.startswith("grounding=escort_turn_cap") for t in command["degradations"])


def test_cap_stops_the_e1_escort_at_robot_5s_turn():
    # robot_5 at x = 2.0005 heading west to S (0, -1.55): its route leaves
    # the x axis at x = 0, 2.000 m away, short of the 2.35 m clearance value.
    command = _ground(_CB78, _CB78_GOALS, _CB78_INVOLVED, _shipped_params())
    parameters = command["actions"][0]["parameters"]
    assert parameters["passer_escort_distance_m"] == pytest.approx(2.0)
    assert parameters["passer_clear_m"] == pytest.approx(2.0)
    assert parameters["passer_escort_heading_rad"] == pytest.approx(math.pi, abs=1e-6)
    assert "grounding=escort_turn_cap:robot_5:2.35->2.0" in command["degradations"]
    # Only the escort and clearance move; every other yield parameter is the live one.
    unchanged = {
        k: v for k, v in parameters.items()
        if k not in ("passer_escort_distance_m", "passer_clear_m")
    }
    expected = {
        k: v for k, v in _CB78_LIVE_YIELD.items()
        if k not in ("passer_escort_distance_m", "passer_clear_m")
    }
    assert unchanged == expected


def _escort_command(escort: float, clear: float, **extra: Any) -> dict[str, Any]:
    return {
        "command_id": "c1",
        "actions": [
            {"robot_id": "robot_1", "action": "yield",
             "parameters": {"passer_robot_id": "robot_2", "passer_escort_distance_m": escort,
                            "passer_clear_m": clear, **extra}},
        ],
    }


def _escort_frame(passer: Pose, goal: tuple[float, float]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id="robot_1", x=-0.5, y=0.0, theta=0.0, goal=(2.3, 0.0)),
            RobotStateInput(robot_id="robot_2", x=passer[0], y=passer[1], theta=passer[2],
                            goal=goal),
        ],
    )


_CAP_ON = GroundingParams(mode="derived", dynamic_scene_arms=True, escort_turn_cap=True)


def _geometry():
    raw = yaml.safe_load(ORCH.read_text())
    raw.update(_overlay())
    return load_config(raw).scenario_geometry


def test_cap_does_not_bite_when_the_turn_is_beyond_the_clearance():
    # Goal Wp on the escort axis, 3.3 m west: the clearance value stands.
    frame = _escort_frame((1.0, 0.0, math.pi), (-2.3, 0.35))
    command = apply_escort_headings(_escort_command(2.35, 2.35), frame, _geometry(), _CAP_ON)
    parameters = command["actions"][0]["parameters"]
    assert parameters["passer_escort_distance_m"] == 2.35
    assert parameters["passer_clear_m"] == 2.35
    assert "degradations" not in command


def test_cap_applies_to_every_aligned_crossing_list_entry():
    frame = SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id="robot_1", x=-0.5, y=0.0, theta=0.0, goal=(2.3, 0.0)),
            RobotStateInput(robot_id="robot_2", x=1.5, y=0.0, theta=math.pi, goal=(0.0, -1.55)),
            RobotStateInput(robot_id="robot_3", x=2.2, y=0.0, theta=math.pi, goal=(-2.3, 0.35)),
        ],
    )
    command = _escort_command(
        2.35, 2.35,
        crossing_order=["robot_2", "robot_3"],
        crossing_escort_m=[2.35, 3.0],
        crossing_clear_m=[2.35, 3.0],
    )
    capped = apply_escort_headings(command, frame, _geometry(), _CAP_ON)
    parameters = capped["actions"][0]["parameters"]
    # robot_2 turns S at x = 0 (1.5 m); robot_3 runs on to Wp (4.5 m > 3.0).
    assert parameters["passer_escort_distance_m"] == 1.5
    assert parameters["passer_clear_m"] == 1.5
    assert parameters["crossing_escort_m"] == [1.5, 3.0]
    assert parameters["crossing_clear_m"] == [1.5, 3.0]
    assert capped["degradations"] == ["grounding=escort_turn_cap:robot_2:2.35->1.5"]


def test_cap_flag_off_leaves_the_heading_pass_unchanged():
    frame = _escort_frame((1.5, 0.0, math.pi), (0.0, -1.55))
    params = GroundingParams(mode="derived", dynamic_scene_arms=True)
    command = apply_escort_headings(_escort_command(2.35, 2.35), frame, _geometry(), params)
    parameters = command["actions"][0]["parameters"]
    assert parameters["passer_escort_distance_m"] == 2.35
    assert parameters["passer_clear_m"] == 2.35


def test_cap_key_stays_out_of_the_dump_when_off():
    assert "escort_turn_cap" not in GroundingParams(dynamic_scene_arms=True).model_dump()
    assert "escort_turn_cap" not in GroundingParams(escort_turn_cap=True).model_dump()
    dumped = GroundingParams(dynamic_scene_arms=True, escort_turn_cap=True).model_dump()
    assert dumped["escort_turn_cap"] is True


def test_shipped_s1_file_turns_the_cap_on():
    assert _shipped_params().escort_turn_cap is True

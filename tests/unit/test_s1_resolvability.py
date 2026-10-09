"""M3 resolvability fixes from the S1b first-light replay (prereg-v3 A14(iii), A15(iv)).

`scripts/s1_grounding_replay.py` measured how often M3 grounds an executable
yield on the Monte Carlo first conflicts: 0.405 (S1b) / 0.345 (S1a). Two
mechanisms capped it, plus one dispatch hole:

1. The ambiguous branch (A14(iii)). A heading more than 30 deg off both axes,
   or two robots side by side on parallel lanes, fell back to the declared
   geometry, whose corridor mouths sit on rack faces: a fabricated ~0.00 m
   room and a false `no feasible yielder` refusal. The view now lends an
   ambiguous PASSER the pair's bearing axis (and hands the yield from an
   ambiguous yielder to a lane-aligned partner that faces it), and refuses
   everything else with its true reason, measuring no room.
2. The swap gate kept a yielder whose retreat sweep then found nothing,
   grounding an empty `reroute` that M4 runs as a no-op. The partner is now
   tried before the yield degrades; if neither has a retreat, it is refused.
3. `refusal_no_action` now also withholds an empty-reroute fallback.

The fixture scenes are replay first conflicts (`data/s1_resolvability/`),
each with what feat/v3-integration@d470470 grounded for it.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from swarm_orchestrator.models import PipelineOutcome, TerminalStage, load_config
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    build_reasoner_request,
    empty_reroute_fallback,
    load_grounding_source,
    yield_refusal_fan_out,
)

from reasoning.rag.command_grounder import (
    degradation_cause,
    ground_reasoner_result,
    resolve_yield_roles,
    verify_and_repair_plan,
)
from reasoning.rag.grounding_view import backup_follows_retreat, resolve_grounding_view
from reasoning.rag.maneuver_geometry import GroundingParams, retreat_axes
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ProposedPlanLeg,
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
from tests.unit.test_m5_reanalysis_suppression import BASE, COOLDOWN, _feed

REPO_ROOT = Path(__file__).resolve().parents[2]
ORCH = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
SCENARIOS = {
    "s1a": REPO_ROOT / "isaac/config/scenarios/mapd_5.yaml",
    "s1b": REPO_ROOT / "isaac/config/scenarios/mapd_5_s1b.yaml",
}
FIXTURES = json.loads(
    (Path(__file__).parent / "data" / "s1_resolvability" / "replay_fixtures.json").read_text()
)["cases"]


def _overlay(floor: str) -> dict[str, Any]:
    lines = SCENARIOS[floor].read_text().splitlines()
    begin = lines.index("#   --- M5 overlay begin ---")
    end = lines.index("#   --- M5 overlay end ---")
    return yaml.safe_load("\n".join(line[4:] for line in lines[begin + 1 : end]))


def _floor(floor: str) -> tuple[Any, GroundingParams]:
    raw = yaml.safe_load(ORCH.read_text())
    overlay = _overlay(floor)
    raw.update(overlay)
    config = load_config(raw)
    params = load_grounding_source(REPO_ROOT / overlay["grounding_params_path"]).params
    return config, params


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
    # The echo mock's decision: the stalled robots in id order, the first yields.
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


def _reasoner_result(decision: CongestionDecision) -> ReasonerResult:
    diag = ReasonerDiagnostics(request_id="r", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(request_id="r", decision=decision, raw_text="{}", diagnostics=diag)


def _ground_case(name: str, *, mode: str = "swap", params: GroundingParams | None = None):
    case = FIXTURES[name]
    config, shipped = _floor(case["floor"])
    frame = _frame(case["rows"])
    return ground_reasoner_result(
        _reasoner_result(_echo_decision(case["involved"])),
        robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=mode,
        snapshot=frame,
        params=params or shipped,
    )


def _yield(command: dict[str, Any]) -> dict[str, Any] | None:
    return next((a for a in command["actions"] if a["action"] == "yield"), None)


def _yield_action_ids(command: dict[str, Any]) -> list[tuple[str, str]]:
    return [(a["robot_id"], a["action"]) for a in command["actions"]]


# ---- Item 1: bearing-axis fallback (primary) ----


def test_ambiguous_partner_lent_the_bearing_axis_grounds_the_yield():
    # S1b seed 113: robot_3 heads 45 deg; robot_1 runs along the pair's y
    # bearing. Baseline: refused, robot_3 0.00 m (fabricated).
    command = _ground_case("s1b_bearing_lane_exec")
    assert FIXTURES["s1b_bearing_lane_exec"]["baseline"].endswith("0.77 m required)")
    assert _yield(command)["robot_id"] == "robot_1"
    assert "grounding=dynamic_arms:bearing_lane:robot_3:45" in command["degradations"]
    assert "grounding=dynamic_arms:lane:y" in command["degradations"]


def test_ambiguous_yielder_hands_the_yield_to_its_facing_partner():
    # S1b seed 34: the named yielder robot_3 heads 34 deg; robot_5 faces it
    # along the x bearing and yields instead.
    command = _ground_case("s1b_heading_regrounded_exec")
    assert _yield(command)["robot_id"] == "robot_5"
    assert "grounding=heading_regrounded:robot_3->robot_5" in command["degradations"]
    assert "grounding=dynamic_arms:bearing_lane:robot_3:34" in command["degradations"]


def test_an_ambiguous_robot_never_yields_on_the_bearing_lane():
    # Wherever the fallback grounded a yield, the yielder's own heading backs
    # it along the swept retreat axis (M4 backs up along -heading).
    for name in ("s1b_bearing_lane_exec", "s1b_heading_regrounded_exec"):
        case = FIXTURES[name]
        config, params = _floor(case["floor"])
        frame = _frame(case["rows"])
        command = _ground_case(name)
        action = _yield(command)
        view = resolve_grounding_view(
            _echo_decision(case["involved"]), frame, config.scenario_geometry, params
        )
        axes = retreat_axes(
            frame, action["robot_id"], action["parameters"]["passer_robot_id"], view.geometry
        )
        assert axes is not None
        assert backup_follows_retreat(frame.find_robot(action["robot_id"]), axes.retreat)


def test_lent_partner_never_takes_the_yield_by_the_rear_swap():
    # robot_1 leads on the x lane facing away from robot_2 (rear-inconsistent);
    # robot_2 heads 40 deg, so it was only lent the axis: it must not yield.
    poses = {"robot_1": (-1.0, 0.0, 0.0), "robot_2": (-1.45, 0.05, math.radians(40))}
    frame = SnapshotFrame(
        stamp=1.0,
        robots=[RobotStateInput(robot_id=r, x=x, y=y, theta=t) for r, (x, y, t) in poses.items()],
    )
    config, params = _floor("s1b")
    view = resolve_grounding_view(
        _echo_decision(["robot_1", "robot_2"]), frame, config.scenario_geometry, params
    )
    assert view.decision.yield_robot == "robot_1"
    assert view.tags == (
        "grounding=dynamic_arms:bearing_lane:robot_2:40",
        "grounding=dynamic_arms:rear_inconsistent:robot_1",
        "grounding=dynamic_arms:lane:x",
    )


# ---- Item 1: honest refusal (residual) ----


@pytest.mark.parametrize(
    ("name", "reason", "tag"),
    [
        (
            "s1b_ambiguous_refused",
            "yield refused: ambiguous lane: robot_4 heads 34 deg off both axes (beyond the "
            "30 deg snap), and robot_2's x lane crosses the pair's y bearing; no retreat room "
            "was measured",
            "grounding=dynamic_arms:ambiguous_refused:robot_4:34",
        ),
        (
            "s1a_ambiguous_refused",
            "yield refused: ambiguous lane: robot_2 heads 45 deg off both axes (beyond the "
            "30 deg snap), and robot_1's x lane crosses the pair's y bearing; no retreat room "
            "was measured",
            "grounding=dynamic_arms:ambiguous_refused:robot_2:45",
        ),
        (
            "s1b_parallel_refused",
            "yield refused: no shared lane: robot_2 and robot_5 both run along y but sit 61 deg "
            "across it (side by side); no retreat room was measured",
            "grounding=dynamic_arms:parallel_refused:robot_2,robot_5:61",
        ),
        (
            "s1a_parallel_refused",
            "yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 45 deg "
            "across it (side by side); no retreat room was measured",
            "grounding=dynamic_arms:parallel_refused:robot_1,robot_3:45",
        ),
    ],
)
def test_unplaceable_lanes_refuse_with_their_true_reason(name: str, reason: str, tag: str):
    assert " 0.00 m" in FIXTURES[name]["baseline"]
    command = _ground_case(name)
    assert yield_refusal_fan_out(command) == reason
    assert tag in command["degradations"]
    assert f"yield=infeasible:{reason}" in command["degradations"]
    assert {a["robot_id"] for a in command["actions"]} == set(FIXTURES[name]["involved"])


def test_both_ambiguous_headings_refuse_with_both_offsets():
    poses = {"robot_1": (-1.0, 0.0, math.radians(40)), "robot_2": (-0.6, 0.1, math.radians(225))}
    frame = SnapshotFrame(
        stamp=1.0,
        robots=[RobotStateInput(robot_id=r, x=x, y=y, theta=t) for r, (x, y, t) in poses.items()],
    )
    config, params = _floor("s1b")
    view = resolve_grounding_view(
        _echo_decision(["robot_1", "robot_2"]), frame, config.scenario_geometry, params
    )
    assert view.refusal_reason == (
        "yield refused: ambiguous lane: robot_1 heads 40 deg and robot_2 heads 45 deg off both "
        "axes (beyond the 30 deg snap); no retreat room was measured"
    )
    assert view.tags == (
        "grounding=dynamic_arms:ambiguous_refused:robot_1:40",
        "grounding=dynamic_arms:ambiguous_refused:robot_2:45",
    )


def test_view_refusal_defaults_the_plan_to_waits_and_rejects_a_yield_plan():
    case = FIXTURES["s1b_ambiguous_refused"]
    config, params = _floor("s1b")
    frame = _frame(case["rows"])
    plan = verify_and_repair_plan(
        _echo_decision(case["involved"]),
        frame,
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        grounding_params=params,
    )
    actions = {leg.robot_id: leg.action for leg in plan.legs}
    assert plan.provenance == "m3_default"
    assert {actions[r] for r in case["involved"]} == {"wait"}
    proposed = _echo_decision(
        case["involved"],
        proposed_plan=[
            ProposedPlanLeg(robot_id=case["involved"][0], action="yield"),
            ProposedPlanLeg(robot_id=case["involved"][1], action="cross"),
        ],
    )
    rejected = verify_and_repair_plan(
        proposed,
        frame,
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        grounding_params=params,
    )
    assert rejected.provenance == "m3_default"
    assert rejected.rejection_reason.startswith("plan unrepairable: yield refused: ambiguous")


def test_pipeline_skips_stage2_for_a_view_refusal():
    from swarm_orchestrator.models import RobotView, SceneSnapshot

    case = FIXTURES["s1b_ambiguous_refused"]
    config, params = _floor("s1b")
    snapshot = SceneSnapshot(
        stamp=5.0,
        frame_id="cam0",
        robots=[
            RobotView(
                robot_id=r["robot_id"], x=r["x"], y=r["y"], theta=r["theta"],
                linear_velocity=0.0, status=r["status"], stamp=5.0, goal=tuple(r["goal"]),
            )
            for r in case["rows"]
        ],
        dropped_frame=False,
    )
    request = build_reasoner_request(request_id="r1", snapshot=snapshot, image_path="/tmp/r1.png")

    class _Reasoner:
        def run(self, _request):
            return _reasoner_result(_echo_decision(case["involved"]))

    pipe = InProcessPipeline(
        reasoner=_Reasoner(),
        ground_fn=ground_reasoner_result,
        scene_geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        grounding_params=params,
        stage2_enabled=False,
    )
    outcome = pipe.run(request)
    assert outcome.stage2.status == "skipped"
    assert outcome.stage2.skip_reason == "yield_refused"
    assert yield_refusal_fan_out(outcome.grounded_command).startswith(
        "yield refused: ambiguous lane"
    )


def test_switch_off_keeps_the_declared_fallback_byte_identical():
    # Dynamic arms off: no view refusal, no bearing lane, no sweep re-grounding.
    case = FIXTURES["s1b_ambiguous_refused"]
    _, shipped = _floor("s1b")
    off = shipped.model_copy(update={"dynamic_scene_arms": False})
    command = _ground_case("s1b_ambiguous_refused", params=off)
    assert not any(t.startswith("grounding=") for t in command.get("degradations", []))
    assert not any(t.startswith("yield_robot=sweep") for t in command.get("degradations", []))
    config, _ = _floor("s1b")
    view = resolve_grounding_view(
        _echo_decision(case["involved"]), _frame(case["rows"]), config.scenario_geometry, off
    )
    assert view.refusal_reason is None and view.tags == ()


# ---- Item 2: swap to the partner when the retreat sweep fails ----


@pytest.mark.parametrize(
    ("name", "kept", "partner"),
    [("s1b_sweep_regrounded_exec", "robot_2", "robot_4"),
     ("s1a_sweep_regrounded_exec", "robot_1", "robot_3")],
)
def test_sweep_failure_hands_the_yield_to_the_partner(name: str, kept: str, partner: str):
    assert FIXTURES[name]["baseline"] == "empty reroute (retreat=no-valid-candidate)"
    command = _ground_case(name)
    action = _yield(command)
    assert action["robot_id"] == partner
    assert f"yield_robot=sweep_regrounded:{kept}->{partner}" in command["degradations"]
    assert action["parameters"]["yield_robot_grounded_from"] == kept
    assert action["parameters"]["yield_regrounded_reason"] == (
        f"yield re-grounded: {kept} has no retreat candidate surviving the sweep; {partner} "
        "has an executable retreat"
    )
    assert action["parameters"]["passer_robot_id"] == kept


@pytest.mark.parametrize(
    ("name", "kept", "partner"),
    [("s1b_both_fail_sweep", "robot_2", "robot_4"), ("s1a_both_fail_sweep", "robot_1", "robot_3")],
)
def test_both_sweeps_failing_refuses_instead_of_an_empty_reroute(
    name: str, kept: str, partner: str
):
    command = _ground_case(name)
    reason = (
        f"yield refused: no executable retreat ({kept} has no retreat candidate surviving the "
        f"sweep; {partner} has no retreat candidate surviving the sweep)"
    )
    assert yield_refusal_fan_out(command) == reason
    assert not any(a["action"] == "reroute" for a in command["actions"])
    assert empty_reroute_fallback(command) is None


def test_roles_and_command_agree_on_the_sweep_regrounded_yielder():
    # Stage 2 and the default plan resolve roles through `resolve_yield_roles`
    # on the same view, so they see the same yielder the command runs.
    case = FIXTURES["s1b_sweep_regrounded_exec"]
    config, params = _floor("s1b")
    frame = _frame(case["rows"])
    view = resolve_grounding_view(
        _echo_decision(case["involved"]), frame, config.scenario_geometry, params
    )
    roles = resolve_yield_roles(
        view.decision,
        frame,
        geometry=view.geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        params=params,
    )
    assert roles.yielder_id == "robot_4"
    assert roles.crossing_order == ["robot_2"]
    plan = verify_and_repair_plan(
        _echo_decision(case["involved"]),
        frame,
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        grounding_params=params,
    )
    assert {leg.robot_id: leg.action for leg in plan.legs}["robot_4"] == "yield"


def test_view_marks_the_node_handoff_occupant_as_exempt():
    # robot_1 dwells on N, robot_2 arrives behind it: robot_2 yields, and the
    # partner retry may never hand the yield to robot_1.
    poses = {"robot_1": (0.0, 1.55, math.pi / 2), "robot_2": (0.0, 1.12, math.pi / 2)}
    frame = SnapshotFrame(
        stamp=1.0,
        robots=[RobotStateInput(robot_id=r, x=x, y=y, theta=t) for r, (x, y, t) in poses.items()],
    )
    config, params = _floor("s1a")
    goals = {"robot_1": (0.0, 1.55), "robot_2": (0.0, 1.55)}
    view = resolve_grounding_view(
        _echo_decision(["robot_1", "robot_2"]), frame, config.scenario_geometry, params, goals
    )
    assert view.decision.yield_robot == "robot_2"
    assert view.geometry.handoff_occupant == "robot_1"
    assert config.scenario_geometry.handoff_occupant is None


def test_refuse_mode_never_sweep_regrounds():
    command = _ground_case("s1b_sweep_regrounded_exec", mode="refuse")
    assert _yield_action_ids(command)[0] == ("robot_2", "reroute")
    assert "retreat=no-valid-candidate" in command["degradations"]


def test_declared_geometry_never_sweep_regrounds():
    # A footprint view is required: the shipped declared-mode reroute stays.
    case = FIXTURES["s1b_sweep_regrounded_exec"]
    config, params = _floor("s1b")
    frame = _frame(case["rows"])
    decision = _echo_decision(case["involved"])
    geometry: SceneGeometry = config.scenario_geometry
    assert geometry.rear_room_band == "aisle"
    roles = resolve_yield_roles(
        decision,
        frame,
        geometry=geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        params=params,
    )
    assert not any(d.startswith("yield_robot=sweep_regrounded") for d in roles.degradations)


def test_partner_facing_away_is_not_handed_the_yield():
    # Same-direction pair on the S1b x lane: robot_1 (rear) faces robot_2,
    # its room gate passes but its 1.3 m backup would enter the west wall;
    # robot_2 leads, facing away, so M4 would back it into robot_1. Refused
    # with both reasons.
    poses = {"robot_1": (-1.35, -0.95, 0.0), "robot_2": (-0.95, -0.95, 0.0)}
    frame = SnapshotFrame(
        stamp=1.0,
        robots=[RobotStateInput(robot_id=r, x=x, y=y, theta=t) for r, (x, y, t) in poses.items()],
    )
    config, params = _floor("s1b")
    command = ground_reasoner_result(
        _reasoner_result(_echo_decision(["robot_1", "robot_2"])),
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode="swap",
        snapshot=frame,
        params=params,
    )
    reason = yield_refusal_fan_out(command)
    assert reason is not None and reason.startswith("yield refused: no executable retreat")
    assert reason.endswith("robot_2 would back up off its retreat axis)")


def test_new_tags_have_a_registered_cause():
    for tag in (
        "yield_robot=sweep_regrounded:robot_2->robot_4",
        "grounding=heading_regrounded:robot_3->robot_5",
        "grounding=dynamic_arms:bearing_lane:robot_3:45",
        "grounding=dynamic_arms:ambiguous_refused:robot_4:34",
        "grounding=dynamic_arms:parallel_refused:robot_2,robot_5:61",
    ):
        assert degradation_cause(tag) is None
    assert degradation_cause("yield=infeasible:yield refused: no executable retreat (x)") == (
        "infeasible_geometry"
    )


def test_no_fixture_refusal_reports_a_zero_room():
    for name in FIXTURES:
        reason = yield_refusal_fan_out(_ground_case(name))
        assert reason is None or " 0.00 m" not in reason


# ---- Item 3: the empty-reroute fallback is withheld ----


def test_empty_reroute_fallback_detects_the_grounded_fallback():
    command = _ground_case("s1b_sweep_regrounded_exec", mode="refuse")
    assert empty_reroute_fallback(command) == "retreat=no-valid-candidate"


def test_empty_reroute_fallback_ignores_an_m2_reroute_and_a_declared_detour():
    m2_reroute = {
        "command_id": "c",
        "actions": [
            {"robot_id": "robot_1", "action": "reroute", "parameters": {"waypoints": []}},
            {"robot_id": "robot_2", "action": "temporary_wait",
             "parameters": {"duration_sec": 15.0}},
        ],
        "degradations": [],
    }
    assert empty_reroute_fallback(m2_reroute) is None
    detour = {
        **m2_reroute,
        "actions": [
            {"robot_id": "robot_1", "action": "reroute",
             "parameters": {"waypoints": [{"x": 1.0, "y": 2.0}]}},
            m2_reroute["actions"][1],
        ],
        "degradations": ["retreat=no-valid-candidate"],
    }
    assert empty_reroute_fallback(detour) is None
    assert empty_reroute_fallback(None) is None


def _empty_reroute_command(request_id: str) -> dict[str, Any]:
    return {
        "command_id": f"{request_id}-reroute",
        "actions": [
            {"robot_id": "robot_2", "action": "reroute", "parameters": {"waypoints": []}},
            {"robot_id": "robot_1", "action": "temporary_wait",
             "parameters": {"duration_sec": 15.0}},
        ],
        "expected_resolution_time_sec": 15.0,
        "fallback": "stop",
        "degradations": ["retreat=no-valid-candidate"],
    }


class _ReroutingPipeline:
    def __init__(self) -> None:
        self.run_calls: list[str] = []

    def run(self, request):
        self.run_calls.append(request.request_id)
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id),
            grounded_command=_empty_reroute_command(request.request_id),
            terminal_stage=TerminalStage.OK,
        )

    def analyze(self, request):  # pragma: no cover - probe mode is off here
        raise AssertionError("no probe expected")


def _node(node_env, tmp_path, *, withhold: bool):  # noqa: F811
    pipeline = _ReroutingPipeline()
    node, clock = _make_node(
        node_env, tmp_path, pipeline,
        t0_probe_mode=False,
        refusal_no_action=withhold,
        reanalysis_suppression={"enabled": True, "applies_to": "all"},
    )
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


def test_withheld_empty_reroute_publishes_nothing_and_records_its_reason(
    node_env, tmp_path  # noqa: F811
):
    node, clock, pipeline = _node(node_env, tmp_path, withhold=True)
    _cycle(node, clock)
    assert node._cmd_pub.published == []
    assert node.get_logger().matching("empty reroute withheld request=")
    assert node.get_logger().matching("refusal withheld request=") == []
    assert _artifact(node, pipeline.run_calls[0])["dispatch_withheld"] == {
        "reason": "empty_reroute",
        "fallback_reason": "retreat=no-valid-candidate",
        "would_dispatch_robot_ids": ["robot_2", "robot_1"],
    }


def test_withheld_empty_reroute_arms_the_suppression(node_env, tmp_path):  # noqa: F811
    node, clock, pipeline = _node(node_env, tmp_path, withhold=True)
    for _ in range(3):
        _cycle(node, clock)
    assert len(pipeline.run_calls) == 1
    assert node.get_logger().matching("outcome=empty_reroute")
    assert node._machine.failure_count("robot_2") == 0


def test_default_off_empty_reroute_still_dispatches(node_env, tmp_path):  # noqa: F811
    node, clock, pipeline = _node(node_env, tmp_path, withhold=False)
    _cycle(node, clock)
    assert len(node._cmd_pub.published) == 2
    assert "dispatch_withheld" not in _artifact(node, pipeline.run_calls[0])

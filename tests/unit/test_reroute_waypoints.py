"""Loop-map reroute grounding (prereg-v2 (b), build-order step 8 phase 2).

`SceneGeometry.reroute_waypoints` names the far-aisle detour a `reroute`
follows on the loop map. These pins hold the additive contract: a declared
detour reaches M4 as `waypoints` in both grounding modes, and every scene
that declares none still grounds the pre-loop-map goal re-send
(`waypoints: []`), byte-identical.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)

LOOP_WAYPOINTS = ((0.3, 1.2), (1.8, 1.2))


def _geometry(waypoints=None) -> SceneGeometry:
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x", center_m=0.0, half_length_m=1.0, aisle_half_width_m=0.6,
            occluder_height_m=0.9,
        ),
        reroute_waypoints=waypoints,
    )


def _result(strategy: str = "reroute", robots: tuple[str, ...] = ("robot_1",)) -> ReasonerResult:
    decision = CongestionDecision(
        congestion_detected=True,
        type="anomaly",
        involved_robots=list(robots),
        root_cause="a blocker on robot_1's lane",
        strategy=strategy,
        justification="j",
    )
    return ReasonerResult(
        request_id="req-loop",
        decision=decision,
        raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="req-loop", backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


def _snapshot() -> SnapshotFrame:
    return SnapshotFrame(
        stamp=30.0,
        robots=[
            RobotStateInput(robot_id="robot_1", x=0.5, y=0.1, theta=0.0, linear_velocity=0.0,
                            status="STOPPED", task="cross_narrow_aisle", goal=(2.3, 0.0)),
        ],
    )


def _reroute_params(command: dict) -> dict:
    (action,) = [a for a in command["actions"] if a["action"] == "reroute"]
    return action["parameters"]


def test_legacy_reroute_forwards_the_declared_detour():
    command = ground_reasoner_result(_result(), geometry=_geometry(LOOP_WAYPOINTS))
    assert _reroute_params(command)["waypoints"] == [
        {"x": 0.3, "y": 1.2}, {"x": 1.8, "y": 1.2},
    ]


def test_derived_reroute_forwards_the_declared_detour():
    command = ground_reasoner_result(
        _result(),
        geometry=_geometry(LOOP_WAYPOINTS),
        snapshot=_snapshot(),
        params=GroundingParams(mode="derived"),
    )
    assert _reroute_params(command)["waypoints"] == [
        {"x": 0.3, "y": 1.2}, {"x": 1.8, "y": 1.2},
    ]
    assert command["degradations"] == []


def test_reroute_without_declared_detour_is_the_goal_resend():
    assert _reroute_params(ground_reasoner_result(_result(), geometry=_geometry()))[
        "waypoints"
    ] == []


def test_reroute_without_geometry_is_the_goal_resend():
    assert _reroute_params(ground_reasoner_result(_result()))["waypoints"] == []


def test_declared_detour_is_byte_identical_off_the_reroute_action():
    # The field only touches the reroute action: a two-robot reroute's
    # partner wait, and every other strategy, ground identically with or
    # without it.
    for strategy in ("reroute", "temporary_wait", "yield", "reverse"):
        robots = ("robot_1", "robot_2")
        plain = ground_reasoner_result(_result(strategy, robots), geometry=_geometry())
        loop = ground_reasoner_result(_result(strategy, robots), geometry=_geometry(LOOP_WAYPOINTS))
        if strategy == "reroute":
            assert plain["actions"][1:] == loop["actions"][1:]
            continue
        assert plain == loop, strategy


def test_empty_waypoint_list_is_rejected():
    with pytest.raises(ValidationError):
        _geometry(())


def test_default_geometry_declares_no_detour():
    assert _geometry().reroute_waypoints is None

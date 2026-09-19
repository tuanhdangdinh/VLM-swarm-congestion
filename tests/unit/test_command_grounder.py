import pytest

from reasoning.rag.command_grounder import (
    CommandGroundingError,
    filter_command_robot_ids,
    ground_reasoner_result,
    resolve_robot_order,
    validate_coordination_command,
)
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import CongestionDecision, ReasonerDiagnostics, ReasonerResult


def test_validate_coordination_command_accepts_valid_payload():
    command = {
        "command_id": "cmd-001",
        "actions": [{"robot_id": "robot_1", "action": "yield", "parameters": {"duration_sec": 3}}],
        "expected_resolution_time_sec": 5,
        "fallback": "stop_and_wait",
    }

    assert validate_coordination_command(command) == command


def test_validate_coordination_command_rejects_missing_actions():
    with pytest.raises(CommandGroundingError):
        validate_coordination_command(
            {
                "command_id": "cmd-001",
                "expected_resolution_time_sec": 5,
                "fallback": "stop_and_wait",
            }
        )


def _result(strategy="yield", robots=None, yield_robot=None):
    robots = robots or ["robot_1", "robot_2"]
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=robots,
        root_cause="head-on aisle conflict",
        strategy=strategy,
        justification="robots are stopped face to face",
        yield_robot=yield_robot,
    )
    diagnostics = ReasonerDiagnostics(
        request_id="req1",
        backend_id="openai",
        attempts=1,
        parse_status="valid",
    )
    return ReasonerResult(
        request_id="req1",
        decision=decision,
        raw_text="{}",
        diagnostics=diagnostics,
    )


def test_ground_yield_decision_to_single_backing_yield_action():
    command = ground_reasoner_result(_result("yield"))

    assert command["command_id"] == "req1-yield"
    # Yield emits two actions: robot_1 backs up and holds, robot_2 waits briefly
    # so M5 cannot dispatch a competing command during the backup window.
    actions = command["actions"]
    assert len(actions) == 2
    yielder = actions[0]
    passer = actions[1]
    assert yielder["robot_id"] == "robot_1"
    assert yielder["action"] == "yield"
    assert yielder["parameters"]["backup_distance_m"] == 1.3
    # Upper-bound backstop; the hold actually ends when the passer's odometry
    # shows passer_clear_m of displacement (event-driven early completion).
    assert yielder["parameters"]["hold_sec"] == 45.0
    assert yielder["parameters"]["passer_robot_id"] == "robot_2"
    assert yielder["parameters"]["passer_clear_m"] == 2.4
    assert yielder["parameters"]["passer_escort_distance_m"] == 2.4
    assert "reason" in yielder["parameters"]
    # A straight backup alone re-blocks the passer's path in this scenario, so
    # the yielder also steps laterally (robot-frame offset, positive = left;
    # executed as a raw-cmd_vel sidestep, not a Nav2 goal).
    assert yielder["parameters"]["pull_off_lateral_m"] == 0.35
    assert passer["robot_id"] == "robot_2"
    assert passer["action"] == "temporary_wait"
    # Generous safety upper bound: the M4 command bus releases this wait the
    # moment the linked yield reaches a terminal status, so this constant is
    # only reached if that terminal-status signal is lost.
    assert passer["parameters"]["duration_sec"] == 120.0
    assert command["fallback"] == "stop"
    # Generous safety upper bound: M5 no longer expires commands whose
    # robots are ACTIVE, so this only bounds the PENDING/lost-dispatch case.
    assert command["expected_resolution_time_sec"] == 150.0


def test_passing_wait_is_upper_bound_constant():
    command = ground_reasoner_result(_result("yield"))

    passer = command["actions"][1]
    # Fixed safety upper bounds, not motion-duration estimates: correct at
    # any Isaac Sim realtime factor because the normal path resolves via
    # event-driven release (Task 3) / non-expiry of ACTIVE commands (Task 1).
    assert passer["parameters"]["duration_sec"] == 120.0
    assert command["expected_resolution_time_sec"] == 150.0


def test_resolve_robot_order_moves_yield_robot_to_front():
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on aisle conflict",
        strategy="yield",
        justification="robot_2 has more room to back into",
        yield_robot="robot_2",
    )

    assert resolve_robot_order(decision) == ["robot_2", "robot_1"]


def test_resolve_robot_order_returns_involved_robots_unchanged_when_yield_robot_none():
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on aisle conflict",
        strategy="yield",
        justification="robot_1 has a clearer retreat path",
    )

    assert resolve_robot_order(decision) == ["robot_1", "robot_2"]


def test_ground_yield_decision_uses_explicit_yield_robot_as_the_yielder():
    command = ground_reasoner_result(_result("yield", yield_robot="robot_2"))

    actions = command["actions"]
    assert actions[0]["robot_id"] == "robot_2"
    assert actions[0]["action"] == "yield"
    assert actions[1]["robot_id"] == "robot_1"
    assert actions[1]["action"] == "temporary_wait"


def _yield_params(
    yielder_xy: tuple[float, float] | None,
    passer_xy: tuple[float, float] | None,
) -> dict:
    positions = {}
    if yielder_xy is not None:
        positions["robot_1"] = yielder_xy
    if passer_xy is not None:
        positions["robot_2"] = passer_xy
    command = ground_reasoner_result(_result("yield"), robot_positions=positions)
    return command["actions"][0]["parameters"]


def test_yield_positions_west_approach_parks_at_negative_x():
    # Nose-to-nose standoff near x=0: the yielder is west of the passer, so it
    # parks at -1.8 (camera-visible, clear of the corridor).
    params = _yield_params((-0.04, 0.0), (0.08, 0.0))

    assert params["park_x_m"] == -1.8
    assert params["backup_distance_m"] == pytest.approx(1.76)
    assert params["passer_escort_distance_m"] == pytest.approx(2.53)
    assert params["passer_clear_m"] == pytest.approx(2.53)


def test_yield_positions_east_approach_parks_at_positive_x():
    params = _yield_params((0.5, 0.0), (-0.3, 0.0))

    assert params["park_x_m"] == 1.8
    assert params["backup_distance_m"] == pytest.approx(1.3)
    assert params["passer_escort_distance_m"] == pytest.approx(2.75)


def test_yield_positions_stall_onset_escort_clears_park():
    # Planner-stall onset at ~1 m separation: the escort must still carry the
    # passer past the parked yielder plus the 0.45 m safety radius.
    params = _yield_params((-0.47, 0.0), (0.59, 0.0))

    assert params["backup_distance_m"] == pytest.approx(1.33)
    assert params["passer_escort_distance_m"] == pytest.approx(3.04)
    assert params["passer_escort_distance_m"] >= abs(0.59 - params["park_x_m"]) + 0.45


def test_yield_backup_clamped_when_already_past_park():
    # -1.9 is genuinely beyond the -1.8 park point; at -1.6 it would now land
    # inside park and pass via the MIN_BACKUP_M clamp instead of this branch.
    params = _yield_params((-1.9, 0.0), (0.2, 0.0))

    assert params["backup_distance_m"] == 0.3


def test_yield_escort_clamped_at_max():
    # The escort must fit under the 45 s hold backstop at 0.1 m/s (4.5 m).
    params = _yield_params((-0.1, 0.0), (12.0, 0.0))

    assert params["passer_escort_distance_m"] == 4.0
    assert params["passer_clear_m"] == 4.0


def test_yield_without_positions_uses_legacy_constants():
    params = ground_reasoner_result(_result("yield"))["actions"][0]["parameters"]

    assert params["backup_distance_m"] == 1.3
    assert params["passer_escort_distance_m"] == 2.4
    assert params["passer_clear_m"] == 2.4
    assert params["pull_off_lateral_m"] == 0.35
    assert "park_x_m" not in params


def test_yield_missing_passer_position_uses_legacy_constants():
    params = _yield_params((-0.04, 0.0), None)

    assert params["backup_distance_m"] == 1.3
    assert params["passer_escort_distance_m"] == 2.4
    assert "park_x_m" not in params


def test_yield_scene_aware_command_validates_against_schema():
    # ground_reasoner_result validates before returning, so reaching this
    # assertion proves the extra park_x_m parameter passes the M3 schema.
    command = ground_reasoner_result(
        _result("yield"), robot_positions={"robot_1": (-0.04, 0.0), "robot_2": (0.08, 0.0)}
    )

    assert set(command) == {
        "command_id",
        "actions",
        "expected_resolution_time_sec",
        "fallback",
    }
    assert command["actions"][0]["parameters"]["pull_off_lateral_m"] == 0.35


def _geometry(axis: str = "x") -> SceneGeometry:
    # Mirrors scenario_geometry in swarm_orchestrator/config/orchestrator.yaml.
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis=axis,
            center_m=0.0,
            half_length_m=1.0,
            aisle_half_width_m=0.6,
            occluder_height_m=0.9,
        )
    )


def test_yield_with_geometry_parks_at_derived_offset():
    # 1.329 visibility boundary + 0.06 marker half-size + 0.4 margin = 1.789,
    # derived from the declared geometry rather than the 1.8 fallback.
    positions = {"robot_1": (-0.04, 0.0), "robot_2": (0.08, 0.0)}

    command = ground_reasoner_result(
        _result("yield"), robot_positions=positions, geometry=_geometry()
    )
    params = command["actions"][0]["parameters"]

    assert params["park_axis"] == "x"
    assert params["park_coord_m"] == pytest.approx(-1.789)
    assert params["park_x_m"] == pytest.approx(-1.789)
    assert params["backup_distance_m"] == pytest.approx(1.749)
    assert params["passer_escort_distance_m"] == pytest.approx(2.519)
    assert params["passer_clear_m"] == pytest.approx(2.519)
    assert params["pull_off_lateral_m"] == 0.36


def test_yield_with_geometry_on_y_axis_uses_y_coordinates():
    # Corridor along y: the axis coordinate is index 1, and park_x_m would be
    # misleading, so only the axis-tagged keys are emitted.
    positions = {"robot_1": (0.0, -0.04), "robot_2": (0.0, 0.08)}

    command = ground_reasoner_result(
        _result("yield"), robot_positions=positions, geometry=_geometry(axis="y")
    )
    params = command["actions"][0]["parameters"]

    assert params["park_axis"] == "y"
    assert params["park_coord_m"] == pytest.approx(-1.789)
    assert "park_x_m" not in params
    assert params["backup_distance_m"] == pytest.approx(1.749)


def test_yield_without_geometry_keeps_fallback_constants():
    # Regression guard for the verified pre-geometry behaviour.
    positions = {"robot_1": (-0.04, 0.0), "robot_2": (0.08, 0.0)}

    params = ground_reasoner_result(_result("yield"), robot_positions=positions)["actions"][0][
        "parameters"
    ]

    assert params["park_x_m"] == -1.8
    assert params["pull_off_lateral_m"] == 0.35
    assert "park_axis" not in params
    assert "park_coord_m" not in params


def _assert_yield_refused(command: dict, robot_ids: list[str]) -> None:
    assert set(command) == {"command_id", "actions", "expected_resolution_time_sec", "fallback"}
    actions = command["actions"]
    assert [action["robot_id"] for action in actions] == robot_ids
    for action in actions:
        assert action["action"] == "temporary_wait"
        params = action["parameters"]
        assert params["duration_sec"] == 8.0
        assert params["requested_strategy"] == "yield"
        assert params["reason"] == (
            "yield refused: both robots outside the corridor on "
            "the same side; a reverse would traverse it"
        )
        assert "park_x_m" not in params
        assert "park_coord_m" not in params
        assert "park_axis" not in params
    assert command["expected_resolution_time_sec"] == 8.0


def test_yield_refused_when_both_robots_beyond_corridor_same_side():
    # Run C (2026-09-16): both robots ended up west of the corridor after a
    # yield. Refuse rather than park the yielder on the far (east) side.
    positions = {"robot_1": (-1.75, 0.0), "robot_2": (-2.07, 0.0)}

    command = ground_reasoner_result(
        _result("yield"), robot_positions=positions, geometry=_geometry()
    )

    _assert_yield_refused(command, ["robot_1", "robot_2"])


def test_yield_refused_symmetric_on_east_side():
    positions = {"robot_1": (1.9, 0.0), "robot_2": (2.3, 0.0)}

    command = ground_reasoner_result(
        _result("yield"), robot_positions=positions, geometry=_geometry()
    )

    _assert_yield_refused(command, ["robot_1", "robot_2"])


def test_yield_allowed_when_one_robot_inside_corridor():
    # Passer at -0.5 sits inside the corridor (half_length_m=1.0), so the
    # guard must not fire even though the yielder is already beyond it.
    positions = {"robot_1": (-1.75, 0.0), "robot_2": (-0.5, 0.0)}

    command = ground_reasoner_result(
        _result("yield"), robot_positions=positions, geometry=_geometry()
    )
    params = command["actions"][0]["parameters"]

    assert command["actions"][0]["action"] == "yield"
    assert params["park_coord_m"] == pytest.approx(-1.789)
    assert params["backup_distance_m"] == pytest.approx(0.3)
    assert command["expected_resolution_time_sec"] == 150.0


def test_yield_allowed_when_robots_straddle_corridor():
    positions = {"robot_1": (-1.2, 0.0), "robot_2": (1.3, 0.0)}

    command = ground_reasoner_result(
        _result("yield"), robot_positions=positions, geometry=_geometry()
    )
    params = command["actions"][0]["parameters"]

    assert command["actions"][0]["action"] == "yield"
    assert params["park_coord_m"] == pytest.approx(-1.789)
    assert params["backup_distance_m"] == pytest.approx(0.589)
    assert command["expected_resolution_time_sec"] == 150.0


def test_yield_guard_not_applied_without_geometry():
    # Same same-side positions as the refused case above, but with no
    # `geometry` the legacy fallback path applies unchanged.
    positions = {"robot_1": (-1.75, 0.0), "robot_2": (-2.07, 0.0)}

    command = ground_reasoner_result(_result("yield"), robot_positions=positions)
    params = command["actions"][0]["parameters"]

    assert command["actions"][0]["action"] == "yield"
    assert params["park_x_m"] == 1.8
    assert params["backup_distance_m"] == 2.5
    assert params["passer_escort_distance_m"] == 4.0
    assert command["expected_resolution_time_sec"] == 150.0


def test_ground_reverse_decision_to_backing_reverse_action():
    command = ground_reasoner_result(_result("reverse", ["robot_2"]))

    assert command["actions"] == [
        {
            "robot_id": "robot_2",
            "action": "reverse",
            "parameters": {
                "backup_distance_m": 1.3,
            },
        }
    ]


def test_reverse_refused_when_both_robots_beyond_corridor_same_side():
    # Run 3 (2026-09-17): robot_2 parked at its goal (-2.46) and robot_1 at -1.22,
    # both west of the corridor; a reverse drove robot_2 back into the aisle.
    positions = {"robot_1": (-1.22, 0.0), "robot_2": (-2.46, 0.0)}

    command = ground_reasoner_result(
        _result("reverse"), robot_positions=positions, geometry=_geometry()
    )

    assert [action["robot_id"] for action in command["actions"]] == ["robot_1", "robot_2"]
    for action in command["actions"]:
        assert action["action"] == "temporary_wait"
        assert action["parameters"]["duration_sec"] == 8.0
        assert action["parameters"]["requested_strategy"] == "reverse"
        assert action["parameters"]["reason"] == (
            "reverse refused: both robots outside the corridor on "
            "the same side; backing up would re-enter it"
        )
    assert command["command_id"] == "req1-reverse"
    assert command["expected_resolution_time_sec"] == 8.0


def test_reverse_allowed_when_one_robot_inside_corridor():
    positions = {"robot_1": (-1.75, 0.0), "robot_2": (-0.5, 0.0)}

    command = ground_reasoner_result(
        _result("reverse"), robot_positions=positions, geometry=_geometry()
    )

    assert [action["action"] for action in command["actions"]] == ["reverse", "reverse"]


def test_reverse_guard_not_applied_without_geometry():
    positions = {"robot_1": (-1.22, 0.0), "robot_2": (-2.46, 0.0)}

    command = ground_reasoner_result(_result("reverse"), robot_positions=positions)

    assert [action["action"] for action in command["actions"]] == ["reverse", "reverse"]


def test_filter_command_robot_ids_drops_hallucinated_robot_actions():
    command = ground_reasoner_result(_result("temporary_wait", ["robot_1", "robot_20"]))

    filtered = filter_command_robot_ids(command, {"robot_1", "robot_2"})

    assert [action["robot_id"] for action in filtered["actions"]] == ["robot_1"]


def test_filter_command_robot_ids_rejects_all_hallucinated_robot_actions():
    command = ground_reasoner_result(_result("temporary_wait", ["robot_20"]))

    with pytest.raises(CommandGroundingError, match="no actions for known robots"):
        filter_command_robot_ids(command, {"robot_1", "robot_2"})

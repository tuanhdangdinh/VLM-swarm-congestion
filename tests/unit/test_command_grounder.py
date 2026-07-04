import pytest

from reasoning.rag.command_grounder import (
    CommandGroundingError,
    filter_command_robot_ids,
    ground_reasoner_result,
    validate_coordination_command,
)
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


def _result(strategy="yield", robots=None):
    robots = robots or ["robot_1", "robot_2"]
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=robots,
        root_cause="head-on aisle conflict",
        strategy=strategy,
        justification="robots are stopped face to face",
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


def test_filter_command_robot_ids_drops_hallucinated_robot_actions():
    command = ground_reasoner_result(_result("temporary_wait", ["robot_1", "robot_20"]))

    filtered = filter_command_robot_ids(command, {"robot_1", "robot_2"})

    assert [action["robot_id"] for action in filtered["actions"]] == ["robot_1"]


def test_filter_command_robot_ids_rejects_all_hallucinated_robot_actions():
    command = ground_reasoner_result(_result("temporary_wait", ["robot_20"]))

    with pytest.raises(CommandGroundingError, match="no actions for known robots"):
        filter_command_robot_ids(command, {"robot_1", "robot_2"})

import pytest

from reasoning.rag.command_grounder import CommandGroundingError, validate_coordination_command


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

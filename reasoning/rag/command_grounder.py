from typing import Any

from jsonschema import Draft202012Validator

from reasoning.schemas import load_schema


class CommandGroundingError(ValueError):
    """Raised when a grounded command is incomplete or invalid."""


def validate_coordination_command(command: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema("coordination_command")
    errors = sorted(Draft202012Validator(schema).iter_errors(command), key=str)
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise CommandGroundingError(f"Command failed schema validation: {messages}")
    return command

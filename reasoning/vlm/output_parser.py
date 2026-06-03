import json
from typing import Any

from jsonschema import Draft202012Validator

from reasoning.schemas import load_schema


class VLMOutputParseError(ValueError):
    """Raised when VLM output is not valid coordination-decision JSON."""


def parse_vlm_decision(text: str) -> dict[str, Any]:
    """Parse and validate a VLM decision JSON string."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise VLMOutputParseError(f"VLM output is not valid JSON: {exc}") from exc

    schema = load_schema("vlm_decision")
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise VLMOutputParseError(f"VLM output failed schema validation: {messages}")
    return payload

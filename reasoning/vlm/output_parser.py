import json
import re
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from reasoning.schemas import load_schema
from reasoning.vlm.models import CongestionDecision


class VLMOutputParseError(ValueError):
    """Raised when VLM output is not valid coordination-decision JSON."""


class DecisionValidationError(ValueError):
    """Raised when a parsed decision references unknown robot IDs."""


class BackendTimeoutError(RuntimeError):
    """Raised by invoke_backend when the backend call exceeds timeout_sec."""


def parse_decision_text(text: str) -> CongestionDecision:
    """Extract JSON from raw VLM text and validate it as a CongestionDecision.

    Tolerates markdown code fences and surrounding prose. Enforces the
    no-congestion invariant and deduplicates involved_robots.

    Args:
        text: Raw assistant text from a VLM backend.

    Returns:
        Validated, normalized decision.

    Raises:
        VLMOutputParseError: On JSON decode failure, schema violation, or a
            self-contradictory no-congestion decision.
    """
    candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.DOTALL)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise VLMOutputParseError("VLM output contains no JSON object.") from None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise VLMOutputParseError(f"VLM output is not valid JSON: {exc}") from exc

    try:
        decision = CongestionDecision(**parsed)
    except (TypeError, ValidationError) as exc:
        raise VLMOutputParseError(f"VLM output failed schema validation: {exc}") from exc

    if not decision.congestion_detected:
        if decision.type != "none" or decision.strategy != "none" or decision.involved_robots:
            raise VLMOutputParseError(
                "congestion_detected=false requires type='none', strategy='none', "
                "involved_robots=[]."
            )

    deduped: list[str] = []
    for robot_id in decision.involved_robots:
        if robot_id not in deduped:
            deduped.append(robot_id)
    return decision.model_copy(update={"involved_robots": deduped})


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

import json
import re
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from reasoning.schemas import load_schema
from reasoning.vlm.errors import (
    BackendTimeoutError,
    DecisionValidationError,
    RetreatLabelError,
    VLMOutputParseError,
)
from reasoning.vlm.models import CongestionDecision, RetreatChoiceDecision

# Re-exported for backward compatibility; canonical home is reasoning.vlm.errors.
__all__ = [
    "BackendTimeoutError",
    "DecisionValidationError",
    "RetreatLabelError",
    "VLMOutputParseError",
    "parse_decision_text",
    "parse_retreat_choice_text",
    "parse_vlm_decision",
    "validate_involved_robots",
]


def _extract_json_object(text: str) -> Any:
    """Extract one JSON value from raw VLM text (think blocks/fences tolerated)."""
    # Cosmos Reason 2 emits a <think>...</think> chain-of-thought before the answer.
    # Drop it before JSON extraction; the trace itself can contain braces that would
    # otherwise corrupt the find("{")/rfind("}") fallback below.
    without_think = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    candidate = re.sub(
        r"^```(?:json)?\s*|\s*```$", "", without_think.strip(), flags=re.DOTALL
    )
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise VLMOutputParseError("VLM output contains no JSON object.") from None
        try:
            return json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise VLMOutputParseError(f"VLM output is not valid JSON: {exc}") from exc


def parse_decision_text(text: str) -> CongestionDecision:
    """Extract JSON from raw VLM text and validate it as a CongestionDecision.

    Tolerates markdown code fences and surrounding prose. Enforces the
    congestion/strategy invariant in both directions. Enum lowercasing and
    involved_robots deduplication are handled by CongestionDecision validators.

    Args:
        text: Raw assistant text from a VLM backend.

    Returns:
        Validated, normalized decision.

    Raises:
        VLMOutputParseError: On JSON decode failure, schema violation, or a
            self-contradictory decision.
    """
    parsed = _extract_json_object(text)

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
    elif decision.type == "none" or decision.strategy == "none" or not decision.involved_robots:
        raise VLMOutputParseError(
            "congestion_detected=true requires a non-'none' type and strategy and "
            "at least one involved robot."
        )
    return decision


def validate_involved_robots(
    decision: CongestionDecision,
    known_robot_ids: set[str],
) -> None:
    """Enforce that every referenced robot ID exists in the input scene.

    Args:
        decision: Parsed decision to check.
        known_robot_ids: All robot IDs present in the request.

    Raises:
        DecisionValidationError: If any involved robot ID is unknown.
    """
    unknown = set(decision.involved_robots) - known_robot_ids
    if unknown:
        raise DecisionValidationError(f"Unknown robot IDs: {sorted(unknown)}")


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


def parse_retreat_choice_text(text: str, valid_labels: set[str]) -> RetreatChoiceDecision:
    """Parse a stage-2 retreat-choice response and validate its label.

    Args:
        text: Raw assistant text from the stage-2 VLM call.
        valid_labels: Letters of the candidates actually rendered (e.g. {"A", "B"}).

    Returns:
        Validated choice with the label uppercased.

    Raises:
        VLMOutputParseError: On JSON failure or schema violation (the
            measurement plan's `parse_failure`).
        RetreatLabelError: When the letter is not among the rendered
            candidates (`invalid_label`). Either way the caller grounds the
            geometry-best candidate instead (`retreat=default:*`).
    """
    parsed = _extract_json_object(text)
    try:
        choice = RetreatChoiceDecision(**parsed)
    except (TypeError, ValidationError) as exc:
        raise VLMOutputParseError(f"retreat choice failed schema validation: {exc}") from exc
    if choice.retreat_choice not in valid_labels:
        raise RetreatLabelError(
            f"retreat_choice {choice.retreat_choice!r} not among candidates "
            f"{sorted(valid_labels)}."
        )
    return choice

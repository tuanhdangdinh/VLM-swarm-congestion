import json
import re
from typing import Any, get_args

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from reasoning.schemas import load_schema
from reasoning.vlm.errors import (
    BackendTimeoutError,
    DecisionValidationError,
    RetreatLabelError,
    VLMOutputParseError,
)
from reasoning.vlm.models import (
    BlockerKind,
    CongestionDecision,
    ProposedPlanLeg,
    RetreatChoiceDecision,
    is_permutation,
)

# Re-exported for backward compatibility; canonical home is reasoning.vlm.errors.
__all__ = [
    "DECISION_DEGRADATION_TAGS",
    "BackendTimeoutError",
    "DecisionValidationError",
    "RetreatLabelError",
    "VLMOutputParseError",
    "parse_decision_text",
    "parse_decision_with_degradations",
    "parse_retreat_choice_text",
    "parse_vlm_decision",
    "validate_involved_robots",
]

# Stage-1 degradation tags for the optional prompt-v2 fields, and the
# measurement-plan cause each counts toward. An invalid value is nulled and
# tagged; the rest of the decision stands, so an optional field never costs a
# re-ask. An ABSENT value is None with no tag: whether None counts as
# `invalid_label` is the scorer's call, made only where a tier scores the field
# (T3a for `blocker_kind`, T2b for `crossing_order`).
DECISION_DEGRADATION_TAGS: dict[str, str] = {
    "blocker_kind=default:invalid_label": "invalid_label",
    "crossing_order=default:non_permutation": "non_permutation_order",
    # (a0) proposed_plan: structurally malformed raw JSON (not a list, a leg
    # missing robot_id/action, an action outside PlanLegAction, or a robot
    # repeated) nulls the whole field rather than failing the decision. An
    # unknown robot_id (relative to the tracked scene) and a plan inconsistent
    # with the strategy token are NOT tagged here: both need the scene roster
    # M3's verify/repair engine has and this parser does not, so they are
    # M3-side rejections (`m3_default` provenance with a logged reason), never
    # a stage-1 parse degradation.
    "proposed_plan=default:invalid_structure": "invalid_plan_structure",
}
_BLOCKER_KINDS: frozenset[str] = frozenset(get_args(BlockerKind))


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


def _dedupe(values: list[Any]) -> list[Any]:
    seen: list[Any] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


def _sanitize_optional_fields(parsed: Any) -> list[str]:
    """Null invalid prompt-v2 optional fields in place; return their tags."""
    if not isinstance(parsed, dict):
        return []
    tags: list[str] = []
    kind = parsed.get("blocker_kind")
    if kind is not None and not (isinstance(kind, str) and kind.lower() in _BLOCKER_KINDS):
        parsed["blocker_kind"] = None
        tags.append("blocker_kind=default:invalid_label")
    order = parsed.get("crossing_order")
    if order is not None:
        involved = parsed.get("involved_robots")
        if isinstance(order, list) and not order:
            # An empty list is how a model says "no order to give".
            parsed["crossing_order"] = None
        elif not (
            isinstance(order, list)
            and all(isinstance(robot_id, str) for robot_id in order)
            and isinstance(involved, list)
            # Checked against the deduplicated list the model validator sees.
            and is_permutation(order, _dedupe(involved))
        ):
            parsed["crossing_order"] = None
            tags.append("crossing_order=default:non_permutation")
    plan = parsed.get("proposed_plan")
    if plan is not None:
        if isinstance(plan, list) and not plan:
            # An empty list is how a model says "no plan to give", same
            # convention as an empty crossing_order.
            parsed["proposed_plan"] = None
        else:
            try:
                if not isinstance(plan, list):
                    raise ValueError("proposed_plan must be a list")
                legs = [ProposedPlanLeg(**leg) for leg in plan]
                robot_ids = [leg.robot_id for leg in legs]
                if len(robot_ids) != len(set(robot_ids)):
                    raise ValueError("duplicate robot_id in proposed_plan")
            except (TypeError, ValueError, ValidationError):
                parsed["proposed_plan"] = None
                tags.append("proposed_plan=default:invalid_structure")
    return tags


def parse_decision_with_degradations(text: str) -> tuple[CongestionDecision, list[str]]:
    """Parse a decision, nulling invalid optional prompt-v2 fields instead of failing.

    `blocker_kind` outside the vocabulary and a `crossing_order` that is not a
    permutation of the involved robots each parse to None and add their
    `DECISION_DEGRADATION_TAGS` entry. Everything else follows
    `parse_decision_text`.

    Args:
        text: Raw assistant text from a VLM backend.

    Returns:
        The validated decision and its degradation tags (empty when none).

    Raises:
        VLMOutputParseError: On JSON decode failure, schema violation of a
            core field, or a self-contradictory decision.
    """
    parsed = _extract_json_object(text)
    degradations = _sanitize_optional_fields(parsed)

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
    return decision, degradations


def parse_decision_text(text: str) -> CongestionDecision:
    """Extract JSON from raw VLM text and validate it as a CongestionDecision.

    Tolerates markdown code fences and surrounding prose. Enforces the
    congestion/strategy invariant in both directions. Enum lowercasing and
    involved_robots deduplication are handled by CongestionDecision validators.
    Invalid optional prompt-v2 fields parse to None; use
    `parse_decision_with_degradations` to learn which.

    Args:
        text: Raw assistant text from a VLM backend.

    Returns:
        Validated, normalized decision.

    Raises:
        VLMOutputParseError: On JSON decode failure, schema violation, or a
            self-contradictory decision.
    """
    return parse_decision_with_degradations(text)[0]


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
            candidates (`invalid_label`); its `choice` holds the parsed
            answer. Either way the caller grounds the geometry-best candidate
            instead (`retreat=default:*`).
    """
    parsed = _extract_json_object(text)
    try:
        choice = RetreatChoiceDecision(**parsed)
    except (TypeError, ValidationError) as exc:
        raise VLMOutputParseError(f"retreat choice failed schema validation: {exc}") from exc
    if choice.retreat_choice not in valid_labels:
        raise RetreatLabelError(
            f"retreat_choice {choice.retreat_choice!r} not among candidates "
            f"{sorted(valid_labels)}.",
            choice=choice,
        )
    return choice

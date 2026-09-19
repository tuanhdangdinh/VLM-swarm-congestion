import json

import pytest
from pydantic import ValidationError

from reasoning.vlm.models import CongestionDecision, ReasonerRequest
from reasoning.vlm.output_parser import (
    DecisionValidationError,  # noqa: F401
    VLMOutputParseError,
    parse_decision_text,
    parse_vlm_decision,
)


def test_parse_vlm_decision_accepts_valid_payload():
    payload = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2"],
        "root_cause": "head-on aisle conflict",
        "strategy": "yield",
        "justification": "robot_1 has a clearer retreat path",
    }

    assert parse_vlm_decision(json.dumps(payload)) == payload


def test_parse_vlm_decision_rejects_invalid_json():
    with pytest.raises(VLMOutputParseError):
        parse_vlm_decision("not json")


_VALID = """```json
{
  "congestion_detected": true,
  "type": "deadlock",
  "involved_robots": ["robot_1", "robot_1", "robot_2"],
  "root_cause": "head-on aisle conflict",
  "strategy": "yield",
  "justification": "robot_1 has a clearer retreat path"
}
```"""


def test_parse_decision_text_strips_code_fence_and_dedupes():
    decision = parse_decision_text(_VALID)
    assert decision.type == "deadlock"
    assert decision.involved_robots == ["robot_1", "robot_2"]


def test_parse_decision_text_strips_think_trace_with_braces():
    text = (
        "<think>I will return {\"foo\": 1} as a placeholder while reasoning.</think>\n"
        '```json\n{"congestion_detected": false, "type": "none", '
        '"involved_robots": [], "root_cause": "clear", "strategy": "none", '
        '"justification": "empty"}\n```'
    )
    decision = parse_decision_text(text)
    assert decision.congestion_detected is False
    assert decision.type == "none"


def test_parse_decision_text_extracts_json_from_prose():
    text = 'Here is my answer: {"congestion_detected": false, "type": "none", "involved_robots": [], "root_cause": "clear", "strategy": "none", "justification": "empty scene"}'  # noqa: E501
    decision = parse_decision_text(text)
    assert decision.congestion_detected is False


def test_parse_decision_text_rejects_bad_enum():
    text = '{"congestion_detected": true, "type": "jam", "involved_robots": ["robot_1"], "root_cause": "x", "strategy": "yield", "justification": "y"}'  # noqa: E501
    with pytest.raises(VLMOutputParseError):
        parse_decision_text(text)


def test_parse_decision_text_rejects_invariant_violation():
    text = '{"congestion_detected": false, "type": "deadlock", "involved_robots": [], "root_cause": "x", "strategy": "none", "justification": "y"}'  # noqa: E501
    with pytest.raises(VLMOutputParseError):
        parse_decision_text(text)


def test_parse_decision_text_rejects_false_with_involved_robots():
    text = '{"congestion_detected": false, "type": "none", "involved_robots": ["robot_1"], "root_cause": "x", "strategy": "none", "justification": "y"}'  # noqa: E501
    with pytest.raises(VLMOutputParseError):
        parse_decision_text(text)


def test_parse_decision_text_rejects_non_json():
    with pytest.raises(VLMOutputParseError):
        parse_decision_text("no json here")


def test_parse_decision_text_rejects_true_with_type_none():
    text = '{"congestion_detected": true, "type": "none", "involved_robots": ["robot_1"], "root_cause": "x", "strategy": "yield", "justification": "y"}'  # noqa: E501
    with pytest.raises(VLMOutputParseError):
        parse_decision_text(text)


def test_parse_decision_text_rejects_true_with_empty_involved_robots():
    text = '{"congestion_detected": true, "type": "deadlock", "involved_robots": [], "root_cause": "x", "strategy": "yield", "justification": "y"}'  # noqa: E501
    with pytest.raises(VLMOutputParseError):
        parse_decision_text(text)


def test_parse_decision_text_lowercases_enum_values():
    text = '{"congestion_detected": true, "type": "DEADLOCK", "involved_robots": ["robot_1"], "root_cause": "x", "strategy": "YIELD", "justification": "y"}'  # noqa: E501
    decision = parse_decision_text(text)
    assert decision.type == "deadlock"
    assert decision.strategy == "yield"


def test_congestion_decision_dedupes_involved_robots_at_model_level():
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_1", "robot_2"],
        root_cause="x",
        strategy="yield",
        justification="y",
    )
    assert decision.involved_robots == ["robot_1", "robot_2"]


def test_reasoner_request_has_no_prompt_context_field():
    assert "prompt_context" not in ReasonerRequest.model_fields


def test_congestion_decision_yield_robot_defaults_to_none():
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on aisle conflict",
        strategy="yield",
        justification="robot_1 has a clearer retreat path",
    )
    assert decision.yield_robot is None


def test_congestion_decision_accepts_yield_robot_in_involved_robots():
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on aisle conflict",
        strategy="yield",
        justification="robot_2 has more room to back into",
        yield_robot="robot_2",
    )
    assert decision.yield_robot == "robot_2"


def test_congestion_decision_rejects_yield_robot_not_in_involved_robots():
    with pytest.raises(ValidationError):
        CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2"],
            root_cause="head-on aisle conflict",
            strategy="yield",
            justification="robot_3 has more room to back into",
            yield_robot="robot_3",
        )


def test_parse_decision_text_yield_strategy_without_yield_robot_still_parses():
    # Backward compatibility: historical artifacts and models that omit the
    # field must still parse even when strategy is "yield".
    text = '{"congestion_detected": true, "type": "deadlock", "involved_robots": ["robot_1", "robot_2"], "root_cause": "x", "strategy": "yield", "justification": "y"}'  # noqa: E501
    decision = parse_decision_text(text)
    assert decision.yield_robot is None


def test_parse_decision_text_accepts_yield_robot_field():
    text = '{"congestion_detected": true, "type": "deadlock", "involved_robots": ["robot_1", "robot_2"], "root_cause": "x", "strategy": "yield", "justification": "y", "yield_robot": "robot_2"}'  # noqa: E501
    decision = parse_decision_text(text)
    assert decision.yield_robot == "robot_2"

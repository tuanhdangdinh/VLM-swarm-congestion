import json

import pytest

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

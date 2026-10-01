import json

import pytest
from pydantic import ValidationError

from reasoning.vlm.models import CongestionDecision, ReasonerRequest
from reasoning.vlm.output_parser import (
    DECISION_DEGRADATION_TAGS,
    DecisionValidationError,  # noqa: F401
    VLMOutputParseError,
    parse_decision_text,
    parse_decision_with_degradations,
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


def test_congestion_decision_rejects_yield_robot_with_empty_involved_robots():
    with pytest.raises(ValidationError):
        CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=[],
            root_cause="x",
            strategy="yield",
            justification="y",
            yield_robot="robot_1",
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


# ---- prompt-v2 bundle: blocker_kind and crossing_order ----


def _decision_json(**extra: object) -> str:
    payload = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2", "robot_3"],
        "root_cause": "x",
        "strategy": "yield",
        "justification": "y",
        "yield_robot": "robot_3",
        **extra,
    }
    return json.dumps(payload)


def _model(**extra: object) -> CongestionDecision:
    return CongestionDecision(**json.loads(_decision_json(**extra)))


def test_congestion_decision_new_fields_default_to_none():
    decision = _model()
    assert decision.blocker_kind is None
    assert decision.crossing_order is None


def test_congestion_decision_lowercases_blocker_kind():
    assert _model(blocker_kind="Object").blocker_kind == "object"


def test_congestion_decision_rejects_unknown_blocker_kind():
    with pytest.raises(ValidationError):
        _model(blocker_kind="wall")


def test_congestion_decision_accepts_crossing_order_permutation():
    order = ["robot_2", "robot_1", "robot_3"]
    assert _model(crossing_order=order).crossing_order == order


def test_congestion_decision_rejects_crossing_order_missing_a_robot():
    with pytest.raises(ValidationError):
        _model(crossing_order=["robot_2", "robot_1"])


def test_congestion_decision_rejects_crossing_order_with_duplicates():
    with pytest.raises(ValidationError):
        _model(crossing_order=["robot_2", "robot_2", "robot_1", "robot_3"])


def test_parse_decision_with_degradations_absent_fields_carry_no_tag():
    decision, tags = parse_decision_with_degradations(_decision_json())
    assert decision.blocker_kind is None and decision.crossing_order is None
    assert tags == []


def test_parse_decision_with_degradations_keeps_valid_fields():
    decision, tags = parse_decision_with_degradations(
        _decision_json(blocker_kind="ROBOT", crossing_order=["robot_1", "robot_2", "robot_3"])
    )
    assert decision.blocker_kind == "robot"
    assert decision.crossing_order == ["robot_1", "robot_2", "robot_3"]
    assert tags == []


def test_parse_decision_with_degradations_nulls_invalid_blocker_kind_with_tag():
    decision, tags = parse_decision_with_degradations(_decision_json(blocker_kind="wall"))
    assert decision.blocker_kind is None
    assert tags == ["blocker_kind=default:invalid_label"]
    # The rest of the decision survives: a bad optional field never re-asks.
    assert decision.strategy == "yield" and decision.yield_robot == "robot_3"


def test_parse_decision_with_degradations_nulls_non_string_blocker_kind_with_tag():
    _, tags = parse_decision_with_degradations(_decision_json(blocker_kind=3))
    assert tags == ["blocker_kind=default:invalid_label"]


def test_parse_decision_with_degradations_keeps_a_valid_reasoning_string():
    decision, tags = parse_decision_with_degradations(
        _decision_json(reasoning="robot_1 and robot_2 are nose to nose in the aisle.")
    )
    assert decision.reasoning == "robot_1 and robot_2 are nose to nose in the aisle."
    assert tags == []


def test_parse_decision_with_degradations_nulls_non_string_reasoning_with_tag():
    decision, tags = parse_decision_with_degradations(_decision_json(reasoning=3))
    assert decision.reasoning is None
    assert tags == ["reasoning=default:invalid_type"]


def test_parse_decision_with_degradations_truncates_overlong_reasoning_with_tag():
    from reasoning.vlm.models import REASONING_MAX_LENGTH

    overlong = "x" * (REASONING_MAX_LENGTH + 500)
    decision, tags = parse_decision_with_degradations(_decision_json(reasoning=overlong))
    assert decision.reasoning == "x" * REASONING_MAX_LENGTH
    assert tags == ["reasoning=truncated"]


def test_congestion_decision_rejects_an_overlong_reasoning_constructed_directly():
    from reasoning.vlm.models import REASONING_MAX_LENGTH

    with pytest.raises(ValidationError):
        _model(reasoning="x" * (REASONING_MAX_LENGTH + 1))


def test_parse_decision_with_degradations_nulls_non_permutation_order_with_tag():
    decision, tags = parse_decision_with_degradations(
        _decision_json(crossing_order=["robot_1", "robot_4", "robot_3"])
    )
    assert decision.crossing_order is None
    assert tags == ["crossing_order=default:non_permutation"]


def test_parse_decision_with_degradations_nulls_non_list_order_with_tag():
    _, tags = parse_decision_with_degradations(_decision_json(crossing_order="robot_1"))
    assert tags == ["crossing_order=default:non_permutation"]


def test_parse_decision_with_degradations_checks_order_against_deduped_involved():
    text = _decision_json(
        involved_robots=["robot_1", "robot_1", "robot_2", "robot_3"],
        crossing_order=["robot_3", "robot_1", "robot_2"],
    )
    decision, tags = parse_decision_with_degradations(text)
    assert decision.crossing_order == ["robot_3", "robot_1", "robot_2"]
    assert tags == []


def test_parse_decision_with_degradations_treats_empty_order_as_absent():
    decision, tags = parse_decision_with_degradations(_decision_json(crossing_order=[]))
    assert decision.crossing_order is None
    assert tags == []


def test_parse_decision_with_degradations_reports_both_tags_in_field_order():
    _, tags = parse_decision_with_degradations(
        _decision_json(blocker_kind="wall", crossing_order=["robot_1"])
    )
    assert tags == [
        "blocker_kind=default:invalid_label",
        "crossing_order=default:non_permutation",
    ]


def test_parse_decision_text_degrades_new_fields_instead_of_failing():
    decision = parse_decision_text(_decision_json(blocker_kind="wall", crossing_order=["x"]))
    assert decision.blocker_kind is None and decision.crossing_order is None


def test_parse_decision_with_degradations_still_rejects_core_violations():
    with pytest.raises(VLMOutputParseError):
        parse_decision_with_degradations(_decision_json(strategy="teleport"))


def test_decision_degradation_tags_map_to_measurement_plan_causes():
    assert DECISION_DEGRADATION_TAGS == {
        "blocker_kind=default:invalid_label": "invalid_label",
        "crossing_order=default:non_permutation": "non_permutation_order",
        "proposed_plan=default:invalid_structure": "invalid_plan_structure",
        "reasoning=default:invalid_type": "invalid_reasoning",
        "reasoning=truncated": "reasoning_truncated",
    }


def test_vlm_decision_schema_accepts_the_optional_contract_fields():
    payload = json.loads(
        _decision_json(blocker_kind="object", crossing_order=["robot_1", "robot_2", "robot_3"])
    )
    assert parse_vlm_decision(json.dumps(payload)) == payload


def test_vlm_decision_schema_accepts_null_optional_fields():
    payload = json.loads(_decision_json(blocker_kind=None, crossing_order=None, yield_robot=None))
    assert parse_vlm_decision(json.dumps(payload)) == payload


def test_vlm_decision_schema_rejects_unknown_blocker_kind():
    with pytest.raises(VLMOutputParseError):
        parse_vlm_decision(_decision_json(blocker_kind="wall"))

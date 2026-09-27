import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from reasoning.schemas import load_schema
from reasoning.vlm import RetreatChoiceDecision as ExportedRetreatChoiceDecision
from reasoning.vlm import parse_retreat_choice_text as exported_parser
from reasoning.vlm.errors import RetreatLabelError, VLMOutputParseError
from reasoning.vlm.models import RetreatChoiceDecision
from reasoning.vlm.output_parser import parse_retreat_choice_text


class TestRetreatChoiceDecision:
    def test_label_uppercased_on_construction(self):
        assert RetreatChoiceDecision(retreat_choice="b", justification="j").retreat_choice == "B"

    def test_multicharacter_label_rejected_by_model(self):
        with pytest.raises(ValidationError):
            RetreatChoiceDecision(retreat_choice="AB", justification="j")

    def test_model_is_frozen(self):
        choice = RetreatChoiceDecision(retreat_choice="A", justification="j")
        with pytest.raises(ValidationError):
            choice.retreat_choice = "B"  # type: ignore[misc]


class TestRetreatChoiceSchema:
    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(load_schema("retreat_choice"))

    def test_schema_accepts_a_lettered_answer(self):
        validator = Draft202012Validator(load_schema("retreat_choice"))
        assert validator.is_valid({"retreat_choice": "c", "justification": "j"})

    def test_schema_rejects_extra_keys_and_non_letters(self):
        validator = Draft202012Validator(load_schema("retreat_choice"))
        assert not validator.is_valid({"retreat_choice": "E", "justification": "j"})
        assert not validator.is_valid(
            {"retreat_choice": "A", "justification": "j", "strategy": "yield"}
        )


class TestParseRetreatChoiceText:
    def test_plain_json_parses(self):
        choice = parse_retreat_choice_text(
            '{"retreat_choice": "B", "justification": "clears the aisle"}',
            valid_labels={"A", "B"},
        )
        assert choice.retreat_choice == "B"
        assert choice.justification == "clears the aisle"

    def test_lowercase_label_normalized(self):
        choice = parse_retreat_choice_text(
            '{"retreat_choice": "a", "justification": "left is clear"}',
            valid_labels={"A", "B"},
        )
        assert choice.retreat_choice == "A"

    def test_think_block_and_fences_tolerated(self):
        text = (
            "<think>{not json} weighing A vs B</think>\n"
            '```json\n{"retreat_choice": "A", "justification": "j"}\n```'
        )
        choice = parse_retreat_choice_text(text, valid_labels={"A", "B"})
        assert choice.retreat_choice == "A"

    def test_surrounding_prose_tolerated(self):
        text = 'Answer: {"retreat_choice": "B", "justification": "j"} done.'
        assert parse_retreat_choice_text(text, valid_labels={"A", "B"}).retreat_choice == "B"

    def test_label_outside_candidate_set_rejected(self):
        with pytest.raises(VLMOutputParseError, match="not among candidates"):
            parse_retreat_choice_text(
                '{"retreat_choice": "C", "justification": "j"}',
                valid_labels={"A", "B"},
            )

    def test_label_outside_candidate_set_raises_label_error(self):
        # The measurement plan counts invalid_label apart from parse_failure,
        # so the caller must be able to tell the two apart by type.
        with pytest.raises(RetreatLabelError):
            parse_retreat_choice_text(
                '{"retreat_choice": "C", "justification": "j"}',
                valid_labels={"A", "B"},
            )

    def test_multicharacter_label_rejected(self):
        with pytest.raises(VLMOutputParseError):
            parse_retreat_choice_text(
                '{"retreat_choice": "AB", "justification": "j"}',
                valid_labels={"A", "B"},
            )

    def test_non_json_rejected(self):
        with pytest.raises(VLMOutputParseError):
            parse_retreat_choice_text("I choose candidate A", valid_labels={"A"})

    def test_non_json_is_not_a_label_error(self):
        with pytest.raises(VLMOutputParseError) as excinfo:
            parse_retreat_choice_text("I choose candidate A", valid_labels={"A"})
        assert not isinstance(excinfo.value, RetreatLabelError)

    def test_missing_justification_rejected(self):
        with pytest.raises(VLMOutputParseError):
            parse_retreat_choice_text('{"retreat_choice": "A"}', valid_labels={"A"})

    def test_json_array_rejected(self):
        with pytest.raises(VLMOutputParseError):
            parse_retreat_choice_text('["A"]', valid_labels={"A"})

    def test_public_exports(self):
        assert ExportedRetreatChoiceDecision is RetreatChoiceDecision
        assert exported_parser is parse_retreat_choice_text

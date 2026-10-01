"""Parsing a backend's raw text into a scored letter choice."""
from reasoning.vlm.capability_probes.answer_parser import parse_probe_answer

_LETTERS = ["A", "B", "C"]


class TestWellFormedAnswers:
    def test_strict_json_object(self):
        letter, cause = parse_probe_answer('{"choice": "B"}', _LETTERS)
        assert (letter, cause) == ("B", None)

    def test_lowercase_letter_is_uppercased(self):
        letter, cause = parse_probe_answer('{"choice": "b"}', _LETTERS)
        assert (letter, cause) == ("B", None)

    def test_bare_single_letter(self):
        letter, cause = parse_probe_answer("C", _LETTERS)
        assert (letter, cause) == ("C", None)

    def test_json_with_surrounding_prose(self):
        text = 'Sure, here is my answer:\n{"choice": "A"}\nHope that helps!'
        letter, cause = parse_probe_answer(text, _LETTERS)
        assert (letter, cause) == ("A", None)

    def test_fenced_json_block(self):
        text = '```json\n{"choice": "A"}\n```'
        letter, cause = parse_probe_answer(text, _LETTERS)
        assert (letter, cause) == ("A", None)


class TestFailureModes:
    def test_empty_string_is_empty_response(self):
        assert parse_probe_answer("", _LETTERS) == (None, "empty_response")

    def test_none_is_empty_response(self):
        assert parse_probe_answer(None, _LETTERS) == (None, "empty_response")

    def test_whitespace_only_is_empty_response(self):
        assert parse_probe_answer("   \n  ", _LETTERS) == (None, "empty_response")

    def test_prose_with_no_json_or_bare_letter_is_parse_failure(self):
        letter, cause = parse_probe_answer("I think it is the second one.", _LETTERS)
        assert letter is None
        assert cause == "parse_failure"

    def test_multi_letter_word_is_parse_failure(self):
        letter, cause = parse_probe_answer("AB", _LETTERS)
        assert cause == "parse_failure"

    def test_letter_outside_the_valid_set_is_invalid_letter(self):
        letter, cause = parse_probe_answer('{"choice": "Z"}', _LETTERS)
        assert (letter, cause) == ("Z", "invalid_letter")

    def test_malformed_json_falls_back_to_parse_failure(self):
        letter, cause = parse_probe_answer('{"choice": "A"', _LETTERS)
        assert letter is None
        assert cause == "parse_failure"

    def test_choice_key_missing_is_parse_failure(self):
        letter, cause = parse_probe_answer('{"answer": "A"}', _LETTERS)
        assert letter is None
        assert cause == "parse_failure"

import pytest
from pydantic import ValidationError

from reasoning.baselines.shadow import compare_decisions
from reasoning.vlm.models import CongestionDecision


def _decision(**overrides: object) -> CongestionDecision:
    base: dict[str, object] = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2"],
        "root_cause": "standoff",
        "strategy": "yield",
        "justification": "j",
        "yield_robot": "robot_1",
    }
    base.update(overrides)
    return CongestionDecision(**base)


class TestCompareDecisions:
    def test_compare_identical_decisions_have_no_disagreement(self):
        record = compare_decisions(_decision(), _decision())
        assert (
            record.strategy_match,
            record.type_match,
            record.yielder_match,
            record.any_disagreement,
        ) == (True, True, True, False)

    def test_compare_strategy_mismatch_flagged(self):
        record = compare_decisions(_decision(strategy="reroute", yield_robot=None), _decision())
        assert (record.strategy_match, record.any_disagreement) == (False, True)

    def test_compare_type_mismatch_flagged(self):
        record = compare_decisions(_decision(type="bottleneck"), _decision())
        assert (record.type_match, record.any_disagreement) == (False, True)

    def test_compare_yielder_mismatch_flagged(self):
        record = compare_decisions(_decision(yield_robot="robot_2"), _decision())
        assert (record.yielder_match, record.any_disagreement) == (False, True)

    def test_compare_yielder_absent_on_one_side_flagged(self):
        record = compare_decisions(_decision(yield_robot=None), _decision())
        assert record.yielder_match is False

    def test_compare_yielder_absent_on_both_sides_matches(self):
        record = compare_decisions(_decision(yield_robot=None), _decision(yield_robot=None))
        assert record.yielder_match is True

    def test_compare_ignores_free_text_fields(self):
        vlm = _decision(root_cause="the VLM's words", justification="more words")
        record = compare_decisions(vlm, _decision())
        assert record.any_disagreement is False

    def test_disagreement_record_is_frozen(self):
        record = compare_decisions(_decision(), _decision())
        with pytest.raises(ValidationError):
            record.strategy_match = False

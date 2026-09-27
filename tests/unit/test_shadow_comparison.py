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


class TestCompareBlockerKindAndOrder:
    _THREE = ["robot_1", "robot_2", "robot_3"]

    def _three(self, **overrides: object) -> CongestionDecision:
        return _decision(involved_robots=self._THREE, yield_robot="robot_3", **overrides)

    def test_blocker_kind_matches_when_equal(self):
        record = compare_decisions(_decision(blocker_kind="robot"), _decision(blocker_kind="robot"))
        assert record.blocker_kind_match is True
        assert record.any_disagreement is False

    def test_blocker_kind_mismatch_is_a_disagreement(self):
        record = compare_decisions(
            _decision(blocker_kind="transient"), _decision(blocker_kind="object")
        )
        assert (record.blocker_kind_match, record.any_disagreement) == (False, True)

    def test_blocker_kind_absent_on_vlm_side_is_not_comparable(self):
        record = compare_decisions(_decision(), _decision(blocker_kind="robot"))
        assert record.blocker_kind_match is None
        assert record.any_disagreement is False

    def test_blocker_kind_absent_on_classical_side_is_not_comparable(self):
        record = compare_decisions(_decision(blocker_kind="robot"), _decision())
        assert record.blocker_kind_match is None

    def test_classical_blocker_kind_keyword_overrides_the_decision_field(self):
        record = compare_decisions(
            _decision(blocker_kind="object"), _decision(), classical_blocker_kind="object"
        )
        assert record.blocker_kind_match is True

    def test_order_matches_when_equal(self):
        order = ["robot_2", "robot_1", "robot_3"]
        record = compare_decisions(
            self._three(crossing_order=order), self._three(crossing_order=order)
        )
        assert (record.order_match, record.any_disagreement) == (True, False)

    def test_order_mismatch_is_a_disagreement(self):
        record = compare_decisions(
            self._three(crossing_order=["robot_1", "robot_2", "robot_3"]),
            self._three(crossing_order=["robot_2", "robot_1", "robot_3"]),
        )
        assert (record.order_match, record.any_disagreement) == (False, True)

    def test_order_absent_on_either_side_is_not_comparable(self):
        order = ["robot_1", "robot_2", "robot_3"]
        with_order = self._three(crossing_order=order)
        assert compare_decisions(self._three(), with_order).order_match is None
        assert compare_decisions(with_order, self._three()).order_match is None

    def test_classical_passing_order_keyword_supplies_a_two_robot_order(self):
        record = compare_decisions(
            _decision(crossing_order=["robot_2", "robot_1"]),
            _decision(),
            classical_passing_order=["robot_2", "robot_1"],
        )
        assert record.order_match is True

"""Wilson confidence intervals and per-probe-type aggregation."""
import pytest

from reasoning.vlm.capability_probes.models import ProbeAnswerRecord
from reasoning.vlm.capability_probes.scorer import score_records, wilson_interval


class TestWilsonInterval:
    def test_zero_items_returns_the_unit_interval(self):
        assert wilson_interval(0, 0) == (0.0, 1.0)

    def test_zero_successes_known_value(self):
        lo, hi = wilson_interval(0, 10)
        assert lo == pytest.approx(0.0, abs=1e-6)
        assert hi == pytest.approx(0.2775, abs=1e-3)

    def test_all_successes_known_value(self):
        lo, hi = wilson_interval(10, 10)
        assert lo == pytest.approx(0.7225, abs=1e-3)
        assert hi == pytest.approx(1.0, abs=1e-6)

    def test_half_successes_is_centered_near_phat(self):
        lo, hi = wilson_interval(5, 10)
        assert lo < 0.5 < hi

    def test_bounds_stay_within_unit_interval(self):
        for successes, n in [(0, 1), (1, 1), (3, 7), (20, 20)]:
            lo, hi = wilson_interval(successes, n)
            assert 0.0 <= lo <= hi <= 1.0

    def test_narrower_interval_with_more_items_at_same_rate(self):
        lo_small, hi_small = wilson_interval(5, 10)
        lo_large, hi_large = wilson_interval(50, 100)
        assert (hi_large - lo_large) < (hi_small - lo_small)


def _record(
    item_id: str, probe_type: str, correct: bool, failure_cause: str | None = None
) -> ProbeAnswerRecord:
    return ProbeAnswerRecord(
        item_id=item_id,
        probe_type=probe_type,
        backend_id="mock",
        raw_text='{"choice": "A"}',
        parsed_letter="A",
        correct_letter="A" if correct else "B",
        correct=correct,
        failure_cause=failure_cause,
        latency_ms=5,
        attempts=1,
    )


class TestScoreRecords:
    def test_aggregates_one_summary_per_probe_type(self):
        records = [
            _record("robot_count_000", "robot_count", True),
            _record("robot_count_001", "robot_count", False),
            _record("left_right_000", "left_right", True),
        ]
        chance = {
            "robot_count_000": 0.2,
            "robot_count_001": 0.2,
            "left_right_000": 0.5,
        }
        summary = score_records(records, chance, backend_id="mock", manifest_seed=42)
        by_type = {s.probe_type: s for s in summary.by_type}
        assert by_type["robot_count"].n == 2
        assert by_type["robot_count"].correct == 1
        assert by_type["robot_count"].accuracy == pytest.approx(0.5)
        assert by_type["left_right"].n == 1
        assert by_type["left_right"].correct == 1
        assert summary.n_items == 3
        assert summary.backend_id == "mock"
        assert summary.manifest_seed == 42

    def test_mean_chance_rate_for_varying_option_counts(self):
        records = [
            _record("nearest_first_000", "nearest_first", True),
            _record("nearest_first_001", "nearest_first", True),
        ]
        chance = {"nearest_first_000": 1 / 2, "nearest_first_001": 1 / 4}
        summary = score_records(records, chance, backend_id="mock", manifest_seed=1)
        assert summary.by_type[0].chance_rate == pytest.approx(0.375)

    def test_empty_records_yields_empty_summary(self):
        summary = score_records([], {}, backend_id="mock", manifest_seed=1)
        assert summary.by_type == []
        assert summary.n_items == 0

    def test_failure_cause_counts_separate_refusals_from_wrong_answers(self):
        records = [
            _record("robot_count_000", "robot_count", True),
            _record("robot_count_001", "robot_count", False),
            _record("robot_count_002", "robot_count", False, failure_cause="refusal"),
            _record("robot_count_003", "robot_count", False, failure_cause="parse_failure"),
        ]
        chance = dict.fromkeys(
            ["robot_count_000", "robot_count_001", "robot_count_002", "robot_count_003"], 0.2
        )
        summary = score_records(records, chance, backend_id="mock", manifest_seed=1)
        counts = summary.by_type[0].failure_cause_counts
        assert counts == {"none": 2, "refusal": 1, "parse_failure": 1}

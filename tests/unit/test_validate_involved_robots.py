import pytest

from reasoning.vlm.models import CongestionDecision
from reasoning.vlm.output_parser import (
    DecisionValidationError,
    validate_involved_robots,
)


def _decision(involved: list[str], detected: bool = True) -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=detected,
        type="deadlock" if detected else "none",
        involved_robots=involved,
        root_cause="x",
        strategy="yield" if detected else "none",
        justification="y",
    )


def test_validate_involved_robots_accepts_known_ids():
    validate_involved_robots(_decision(["robot_1"]), {"robot_1", "robot_2"})


def test_validate_involved_robots_rejects_unknown_id():
    with pytest.raises(DecisionValidationError):
        validate_involved_robots(_decision(["robot_9"]), {"robot_1"})


def test_validate_involved_robots_accepts_empty_when_no_congestion():
    validate_involved_robots(_decision([], detected=False), {"robot_1"})

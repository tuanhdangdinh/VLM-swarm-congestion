"""Tests for the (a0) `proposed_plan` schema contract: models.py, the raw-text
sanitization in output_parser.py, and the JSON schema sync.

Backward compatibility is the load-bearing property here: every assertion
that an absent `proposed_plan` parses exactly as before is a regression
guard, not a nice-to-have.
"""

import json

import pytest
from pydantic import ValidationError

from reasoning.vlm.models import CongestionDecision, ProposedPlanLeg
from reasoning.vlm.output_parser import (
    DECISION_DEGRADATION_TAGS,
    parse_decision_text,
    parse_decision_with_degradations,
    parse_vlm_decision,
)


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


class TestBackwardCompatibility:
    def test_absent_proposed_plan_defaults_to_none(self):
        decision = parse_decision_text(_decision_json())
        assert decision.proposed_plan is None

    def test_decision_without_proposed_plan_key_parses_identically_to_before(self):
        # No `proposed_plan` key at all (not even null): the exact shape of
        # every artifact collected before this field existed.
        payload = json.loads(_decision_json())
        assert "proposed_plan" not in payload
        decision = CongestionDecision(**payload)
        assert decision.proposed_plan is None

    def test_null_proposed_plan_is_accepted(self):
        decision = parse_decision_text(_decision_json(proposed_plan=None))
        assert decision.proposed_plan is None


class TestProposedPlanSchema:
    def test_valid_plan_parses_into_typed_legs(self):
        decision = parse_decision_text(
            _decision_json(
                proposed_plan=[
                    {"robot_id": "robot_3", "action": "yield"},
                    {"robot_id": "robot_1", "action": "cross"},
                ]
            )
        )
        assert decision.proposed_plan == [
            ProposedPlanLeg(robot_id="robot_3", action="yield"),
            ProposedPlanLeg(robot_id="robot_1", action="cross"),
        ]

    def test_action_is_lowercased(self):
        decision = parse_decision_text(
            _decision_json(proposed_plan=[{"robot_id": "robot_1", "action": "YIELD"}])
        )
        assert decision.proposed_plan[0].action == "yield"

    def test_unrecognised_action_nulls_the_whole_plan(self):
        decision, tags = parse_decision_with_degradations(
            _decision_json(proposed_plan=[{"robot_id": "robot_1", "action": "teleport"}])
        )
        assert decision.proposed_plan is None
        assert tags == ["proposed_plan=default:invalid_structure"]

    def test_duplicate_robot_in_raw_text_nulls_the_whole_plan(self):
        decision, tags = parse_decision_with_degradations(
            _decision_json(
                proposed_plan=[
                    {"robot_id": "robot_1", "action": "yield"},
                    {"robot_id": "robot_1", "action": "cross"},
                ]
            )
        )
        assert decision.proposed_plan is None
        assert "proposed_plan=default:invalid_structure" in tags

    def test_malformed_leg_shape_nulls_the_whole_plan(self):
        decision, tags = parse_decision_with_degradations(
            _decision_json(proposed_plan=[{"robot_id": "robot_1"}])
        )
        assert decision.proposed_plan is None
        assert "proposed_plan=default:invalid_structure" in tags

    def test_non_list_proposed_plan_nulls_the_whole_plan(self):
        decision, tags = parse_decision_with_degradations(
            _decision_json(proposed_plan={"robot_id": "robot_1", "action": "yield"})
        )
        assert decision.proposed_plan is None
        assert "proposed_plan=default:invalid_structure" in tags

    def test_empty_list_means_no_plan_without_a_tag(self):
        decision, tags = parse_decision_with_degradations(_decision_json(proposed_plan=[]))
        assert decision.proposed_plan is None
        assert tags == []

    def test_other_core_fields_still_parse_when_plan_is_sanitized(self):
        # A malformed plan must not take the rest of the decision down with it.
        decision = parse_decision_text(
            _decision_json(proposed_plan=[{"robot_id": "robot_1", "action": "nonsense"}])
        )
        assert decision.congestion_detected is True
        assert decision.strategy == "yield"
        assert decision.involved_robots == ["robot_1", "robot_2", "robot_3"]


class TestEachRobotAtMostOnce:
    def test_direct_construction_rejects_duplicate_robot(self):
        with pytest.raises(ValidationError):
            CongestionDecision(
                congestion_detected=True,
                type="deadlock",
                involved_robots=["robot_1", "robot_2"],
                root_cause="x",
                strategy="yield",
                justification="j",
                proposed_plan=[
                    ProposedPlanLeg(robot_id="robot_1", action="yield"),
                    ProposedPlanLeg(robot_id="robot_1", action="continue"),
                ],
            )

    def test_direct_construction_accepts_distinct_robots(self):
        decision = CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2"],
            root_cause="x",
            strategy="yield",
            justification="j",
            proposed_plan=[
                ProposedPlanLeg(robot_id="robot_1", action="yield"),
                ProposedPlanLeg(robot_id="robot_2", action="cross"),
            ],
        )
        assert len(decision.proposed_plan) == 2


class TestVlmDecisionSchemaSync:
    def test_schema_accepts_a_valid_proposed_plan(self):
        payload = json.loads(
            _decision_json(
                proposed_plan=[
                    {"robot_id": "robot_3", "action": "yield"},
                    {"robot_id": "robot_1", "action": "cross"},
                ]
            )
        )
        assert parse_vlm_decision(json.dumps(payload)) == payload

    def test_schema_accepts_null_proposed_plan(self):
        payload = json.loads(_decision_json(proposed_plan=None))
        assert parse_vlm_decision(json.dumps(payload)) == payload

    def test_schema_rejects_unknown_action(self):
        with pytest.raises(Exception):  # noqa: B017 - VLMOutputParseError wraps jsonschema's
            parse_vlm_decision(_decision_json(proposed_plan=[{"robot_id": "r", "action": "nope"}]))

    def test_schema_rejects_additional_leg_properties(self):
        with pytest.raises(Exception):  # noqa: B017
            parse_vlm_decision(
                _decision_json(
                    proposed_plan=[{"robot_id": "r", "action": "yield", "extra": 1}]
                )
            )


def test_degradation_tags_registered_for_proposed_plan():
    assert "proposed_plan=default:invalid_structure" in DECISION_DEGRADATION_TAGS
    assert DECISION_DEGRADATION_TAGS["proposed_plan=default:invalid_structure"] == (
        "invalid_plan_structure"
    )

import json

import pytest

from reasoning.vlm.output_parser import VLMOutputParseError, parse_vlm_decision


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

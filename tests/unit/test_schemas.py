from jsonschema import Draft202012Validator

from reasoning.schemas import load_schema


def test_schemas_are_valid_draft_2020_12():
    for name in ["robot_state", "vlm_decision", "coordination_command"]:
        Draft202012Validator.check_schema(load_schema(name))

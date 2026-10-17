"""prereg-v3 A30: the E24-E26 grounding overlay is the shield file plus the escort/park switch.

`config/grounding/s1b_dynamic_shield_escort.yaml` must equal the pinned
`s1b_dynamic_shield.yaml` key for key, with exactly one added key
(`escort_park_clearance: true`), and must load through the real
`load_grounding_source` with the shield, its margin, the B3 fast-fail and the
escort/park filter all on (precedent: `test_a26_retreat_shield.py`).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from swarm_orchestrator.reasoning_pipeline import load_grounding_source

from reasoning.rag.maneuver_geometry import GroundingParams

REPO_ROOT = Path(__file__).resolve().parents[2]
ESCORT_FILE = REPO_ROOT / "config/grounding/s1b_dynamic_shield_escort.yaml"
SHIELD_FILE = REPO_ROOT / "config/grounding/s1b_dynamic_shield.yaml"
_ESCORT_KEYS = {"escort_park_clearance": True}


def test_escort_file_is_the_pinned_shield_file_plus_one_key():
    escort = yaml.safe_load(ESCORT_FILE.read_text())["grounding"]
    shield = yaml.safe_load(SHIELD_FILE.read_text())["grounding"]
    assert {k: v for k, v in escort.items() if k not in _ESCORT_KEYS} == shield
    assert {k: escort[k] for k in _ESCORT_KEYS} == _ESCORT_KEYS


def test_escort_file_loads_with_shield_fast_fail_and_park_filter_on():
    params = load_grounding_source(ESCORT_FILE).params
    assert params.mode == "derived"
    assert params.retreat_shield is True
    assert params.retreat_shield_margin_m == 0.05
    assert params.retreat_fast_fail is True
    assert params.escort_park_clearance is True
    assert params.dynamic_scene_arms is True


def test_escort_file_differs_from_the_shield_params_only_in_the_switch():
    params = load_grounding_source(ESCORT_FILE).params
    defaults = {k: GroundingParams.model_fields[k].default for k in _ESCORT_KEYS}
    assert params.model_copy(update=defaults) == load_grounding_source(SHIELD_FILE).params

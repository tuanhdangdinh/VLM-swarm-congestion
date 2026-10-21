"""prereg-v3 A30: the E24-E26 grounding overlay is the shield file plus the escort/park switch.

`config/grounding/s1b_dynamic_shield_escort.yaml` must equal the pinned
`s1b_dynamic_shield.yaml` key for key, with exactly one added key
(`escort_park_clearance: true`), and must load through the real
`load_grounding_source` with the shield, its margin, the B3 fast-fail and the
escort/park filter all on (precedent: `test_a26_retreat_shield.py`).

prereg-v3 A32 (owner ruling R1, 2026-10-21) promotes this overlay to the
registered shield config for confirmatory S1b cells, so its bytes are pinned
by md5 next to the pinned shield file's, and its non-comment content must be
the shield file's plus exactly the one line `  escort_park_clearance: true`.
"""

from __future__ import annotations

import difflib
import hashlib
from pathlib import Path

import yaml
from swarm_orchestrator.reasoning_pipeline import load_grounding_source

from reasoning.rag.maneuver_geometry import GroundingParams

REPO_ROOT = Path(__file__).resolve().parents[2]
ESCORT_FILE = REPO_ROOT / "config/grounding/s1b_dynamic_shield_escort.yaml"
SHIELD_FILE = REPO_ROOT / "config/grounding/s1b_dynamic_shield.yaml"
_ESCORT_KEYS = {"escort_park_clearance": True}
ESCORT_MD5 = "409688866d25289309e081dcb9433037"
SHIELD_MD5 = "ee5fe68f54298f4fd2ba1625a82968d3"


def _content_lines(path: Path) -> list[str]:
    # Comments and blank lines are provenance, not configuration.
    return [
        line
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def test_escort_overlay_bytes_match_the_registered_md5():
    assert hashlib.md5(ESCORT_FILE.read_bytes()).hexdigest() == ESCORT_MD5


def test_shield_file_bytes_match_the_pinned_md5():
    assert hashlib.md5(SHIELD_FILE.read_bytes()).hexdigest() == SHIELD_MD5


def test_escort_overlay_content_is_the_shield_content_plus_one_line():
    diff = list(
        difflib.unified_diff(_content_lines(SHIELD_FILE), _content_lines(ESCORT_FILE), n=0)
    )
    changes = [line for line in diff[2:] if not line.startswith("@@")]
    assert changes == ["+  escort_park_clearance: true"]


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

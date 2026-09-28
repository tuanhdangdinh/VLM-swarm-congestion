"""Pins scripts/vm/fc_launch.sh's DRY_RUN command sequence.

The two-robot goldens under tests/unit/data/fc_launch/ were recorded from the
launcher BEFORE its robot loop (tree 3ebb7ea, hard-coded robot_1/robot_2), so
a two-robot scenario must keep producing byte-identical commands. The
three-robot cases check the loop itself.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "vm" / "fc_launch.sh"
GOLDEN_DIR = Path(__file__).parent / "data" / "fc_launch"

# case name -> (scenario, extra env)
TWO_ROBOT_CASES: dict[str, tuple[str, dict[str, str]]] = {
    "head_on_deadlock": ("head_on_deadlock", {}),
    "wopen_eopen": ("head_on_asymmetric_wopen_eopen_o0", {}),
    "obstacle_in_candidate_mock": (
        "obstacle_in_candidate",
        {
            "MOCK_DECISION_FILE": "config/mock_decisions/obstacle_in_candidate_yield_once.json",
            "MOCK_RETREAT_CHOICE_FILE": "config/mock_decisions/retreat_choice_b.json",
        },
    ),
    "normal_flow_record": ("normal_flow", {"RECORD": "1"}),
    "blocked_path_object": ("blocked_path_object", {}),
}

_CLEARED_ENV = (
    "BACKEND_ID", "MOCK_DECISION_FILE", "MOCK_RETREAT_CHOICE_FILE", "MODALITY",
    "RECORD", "REC_SEC", "SIM_SEC", "SEED", "CONTAINER", "REPO",
)


def dry_run(scenario: str, extra_env: dict[str, str]) -> str:
    """Run the launcher in DRY_RUN mode and return its normalized output."""
    env = {k: v for k, v in os.environ.items() if k not in _CLEARED_ENV}
    # The host-python spawn parse needs pyyaml: the venv's interpreter first.
    env["PATH"] = f"{Path(sys.executable).parent}:{env.get('PATH', '')}"
    env.update({"DRY_RUN": "1", "SCENARIO": scenario, **extra_env})
    completed = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
    return normalize(completed.stdout + completed.stderr)


def normalize(text: str) -> str:
    """Drop the per-run clock, stamp and checkout path from launcher output."""
    text = re.sub(r"^\[fc-launch \d\d:\d\d:\d\d\] ", "[fc-launch] ", text, flags=re.M)
    text = re.sub(r"\d{8}_\d{6}", "<STAMP>", text)
    return text.replace(str(ROOT), "<REPO>")


@pytest.mark.parametrize("case", sorted(TWO_ROBOT_CASES))
def test_two_robot_dry_run_matches_pre_loop_golden(case):
    scenario, extra_env = TWO_ROBOT_CASES[case]
    golden = (GOLDEN_DIR / f"{case}.txt").read_text(encoding="utf-8")
    assert dry_run(scenario, extra_env) == golden

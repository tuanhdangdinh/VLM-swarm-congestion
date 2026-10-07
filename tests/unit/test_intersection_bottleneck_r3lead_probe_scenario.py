"""Pins for the validation-only robot_3-lead IB10 probe scenario.

The probe must differ from `intersection_bottleneck.yaml` only in `name`, its
header and robot_3's spawn (0.15 m outward on robot_3's own arm); derivation in
the probe yaml's header.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import load_scenario

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = REPO_ROOT / "isaac/config/scenarios"
PARENT = SCENARIOS_DIR / "intersection_bottleneck.yaml"
PROBE = SCENARIOS_DIR / "intersection_bottleneck_r3lead_probe.yaml"

# Verified M1 tracked band on y (docs/reports/2026-10-01-m1-y-extent-
# verification.md Rev 2).
TRACKED_Y = 2.0


def test_probe_differs_from_parent_only_in_name_and_robot_3_spawn():
    parent = yaml.safe_load(PARENT.read_text())
    probe = yaml.safe_load(PROBE.read_text())

    assert probe.pop("name") == "intersection_bottleneck_r3lead_probe"
    parent.pop("name")
    probe_r3 = next(r for r in probe["robots"] if r["robot_id"] == "robot_3")
    parent_r3 = next(r for r in parent["robots"] if r["robot_id"] == "robot_3")
    assert probe_r3["spawn"] == {"x": 0.0, "y": -1.90, "yaw_rad": parent_r3["spawn"]["yaw_rad"]}
    probe_r3["spawn"] = parent_r3["spawn"]

    assert probe == parent


def test_probe_nudge_is_outward_on_robot_3_arm_and_inside_tracked_band():
    parent = {r.robot_id: r for r in load_scenario(PARENT).robots}
    probe = {r.robot_id: r for r in load_scenario(PROBE).robots}

    nudge = parent["robot_3"].spawn.y - probe["robot_3"].spawn.y
    assert abs(nudge - 0.15) < 1e-9
    assert probe["robot_3"].spawn.x == parent["robot_3"].spawn.x
    assert abs(probe["robot_3"].spawn.y) <= TRACKED_Y


def test_probe_header_marks_validation_only():
    header = PROBE.read_text().split("schema_version:", 1)[0]

    assert "VALIDATION-ONLY PROBE: DO NOT COLLECT" in header
    assert "Excluded from every confirmatory" in header
    assert "MAP_SCENARIO=intersection_bottleneck" in header
    assert "build_scenario" in header

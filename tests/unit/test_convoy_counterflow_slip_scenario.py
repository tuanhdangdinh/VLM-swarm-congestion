"""Tests for the B3 first-to-slip variant `convoy_counterflow_slip`.

The variant is byte-identical to the v1 `convoy_counterflow` cell except
`name` and `oracle` (prereg-v2 design docs/superpowers/specs/
2026-09-30-prereg-v2-design.md, "(e) B3 first-to-slip"); these tests pin that
inheritance (geometry, map) and the new oracle shape. The GT-scorer behaviour
itself (`slip_onset_sec`, `first_slipper`, `score_b3`) is pinned in
`tests/unit/test_coverage_scene_scores.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import load_scenario
from isaac.vgu_sim.config import OracleConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = REPO_ROOT / "isaac/config/scenarios"
SLIP_PATH = SCENARIOS / "convoy_counterflow_slip.yaml"
V1_PATH = SCENARIOS / "convoy_counterflow.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"


def _scenario():
    return load_scenario(SLIP_PATH)


class TestInheritsV1Geometry:
    def test_members_differ_only_in_name_and_oracle(self):
        slip, v1 = (yaml.safe_load(p.read_text()) for p in (SLIP_PATH, V1_PATH))
        slip.pop("name"), v1.pop("name")
        slip.pop("oracle"), v1.pop("oracle")
        assert slip == v1

    def test_geometry_matches_v1(self):
        slip, v1 = _scenario(), load_scenario(V1_PATH)

        def pose(s):
            return [(r.robot_id, r.spawn, r.goal) for r in s.robots]

        assert pose(slip) == pose(v1)
        assert slip.aisle_barrier == v1.aisle_barrier
        assert slip.expected_conflict == v1.expected_conflict
        assert slip.timed_obstacles == v1.timed_obstacles == ()
        assert slip.static_obstacles == v1.static_obstacles == ()
        assert slip.duration_sec == v1.duration_sec

    def test_map_equals_the_v1_map(self):
        def grid(name):
            data = yaml.safe_load((MAPS_DIR / f"warehouse_map_{name}.yaml").read_text())
            return np.array(Image.open(MAPS_DIR / data["image"]))

        assert np.array_equal(
            grid("convoy_counterflow_slip"), grid("convoy_counterflow")
        )


class TestFirstSlipperOracle:
    def test_oracle_is_the_strategy_label_shape_plus_first_slipper(self):
        scenario = _scenario()
        oracle = scenario.oracle
        assert isinstance(oracle, OracleConfig)
        assert oracle.correct_strategy == "convoy"
        assert oracle.platoon == ("robot_1", "robot_3", "robot_4")
        assert oracle.first_slipper == "robot_1"

    def test_first_slipper_is_the_platoon_lead_under_the_designed_order(self):
        # Degeneracy note (scenario header): under the designed execution,
        # first_slipper is implied by correct_order[0]; the question is
        # scored anyway for identity-divergence detection and latency.
        oracle = _scenario().oracle
        assert oracle.first_slipper == oracle.correct_order[0]

    def test_oracle_round_trips_through_json_dump(self):
        from isaac.vgu_sim.config import ScenarioConfig

        cfg = _scenario()
        assert ScenarioConfig.model_validate(cfg.model_dump(mode="json")) == cfg

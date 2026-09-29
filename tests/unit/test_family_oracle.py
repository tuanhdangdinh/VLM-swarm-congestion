import math
from pathlib import Path

import pytest
import yaml

from isaac.vgu_sim import family_oracle as fo
from isaac.vgu_sim.config import HeadOnAsymmetricParams, OracleConfig
from reasoning.baselines.classical_reasoner import load_classical_params, resolve_classical
from reasoning.rag.scene_geometry import SceneGeometry, park_offset_m
from reasoning.vlm.models import RobotStateInput, SnapshotFrame

ORCHESTRATOR_YAML = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")


@pytest.fixture
def geometry() -> SceneGeometry:
    return fo.load_scene_geometry(ORCHESTRATOR_YAML)


def test_load_scene_geometry_reads_m5_block(geometry):
    assert geometry.corridor.half_length_m == pytest.approx(1.0)
    assert park_offset_m(geometry) == pytest.approx(1.79, abs=0.02)


def test_required_room_matches_spec_value(geometry):
    assert fo.required_room_m(geometry) == pytest.approx(1.08, abs=0.02)


def test_open_side_is_feasible(geometry):
    assert fo.side_feasible(None, geometry) is True


def test_blocker_0p2_is_infeasible(geometry):
    assert fo.side_feasible(0.2, geometry) is False


def test_blocker_beyond_required_room_is_feasible(geometry):
    assert fo.side_feasible(0.6, geometry) is True   # 0.5 + 0.6 = 1.1 >= 1.08


def test_fcfs_full_tie_yields_robot_2():
    # Arm B's id tie-break passes robot_1 first, so robot_2 yields
    # (test_decide_head_on_breaks_full_tie_by_robot_id); corrected 2026-09-29.
    assert fo.fcfs_yielder(0.0) == "robot_2"


def test_fcfs_tie_matches_arm_b_on_a_symmetric_standoff():
    frames = [
        SnapshotFrame(stamp=t, robots=[
            RobotStateInput(robot_id="robot_1", x=-x, y=0.0, theta=0.0,
                            linear_velocity=0.0 if t else 0.15, goal=(2.5, 0.0)),
            RobotStateInput(robot_id="robot_2", x=x, y=0.0, theta=math.pi,
                            linear_velocity=0.0 if t else 0.15, goal=(-2.5, 0.0)),
        ])
        for t, x in ((0.0, 1.5), (10.0, 0.12))
    ]
    resolution = resolve_classical(frames, [], load_classical_params(Path("config/rag.yaml")))
    assert resolution.decision.yield_robot == fo.fcfs_yielder(0.0)


def test_fcfs_later_arriver_yields():
    assert fo.fcfs_yielder(0.4) == "robot_2"


def test_west_blocker_center(geometry):
    assert fo.blocker_center_x_m("west", 0.2, 0.0, geometry) == pytest.approx(-1.85)


def test_east_blocker_center(geometry):
    assert fo.blocker_center_x_m("east", 0.2, 0.0, geometry) == pytest.approx(1.85)


def test_west_blocker_oracle_agrees_with_fcfs(geometry):
    oracle = fo.compute_oracle(HeadOnAsymmetricParams(blocker_west_m=0.2), geometry)
    assert oracle.correct_yielder == "robot_2"
    assert oracle.feasible_yielders == ("robot_2",)
    assert oracle.fcfs_yielder == "robot_2"
    assert oracle.contrasts_fcfs is False
    assert "robot_1 cannot park" in oracle.rationale


def test_east_blocker_oracle_contrasts_fcfs(geometry):
    oracle = fo.compute_oracle(HeadOnAsymmetricParams(blocker_east_m=0.2), geometry)
    assert oracle.correct_yielder == "robot_1"
    assert oracle.fcfs_yielder == "robot_2"
    assert oracle.contrasts_fcfs is True


def test_open_variant_keeps_its_recorded_yielder(geometry):
    # The correction changes the FCFS fact, never the recorded answer.
    oracle = fo.compute_oracle(HeadOnAsymmetricParams(), geometry)
    assert oracle.correct_yielder == "robot_1"
    assert oracle.fcfs_yielder == "robot_2"
    assert set(oracle.feasible_yielders) == {"robot_1", "robot_2"}
    assert oracle.rationale == (
        "both sides can park (required room 1.08 m); the recorded answer is "
        "robot_1 (Arm B's FCFS full tie yields robot_2)"
    )


def test_double_blocker_has_no_oracle(geometry):
    params = HeadOnAsymmetricParams(blocker_west_m=0.2, blocker_east_m=0.2)
    assert fo.compute_oracle(params, geometry) is None


FAMILY_DIR = Path("isaac/config/scenarios/family")


@pytest.mark.parametrize(
    "scenario_yaml", sorted(p.name for p in FAMILY_DIR.glob("head_on_asymmetric_*.yaml"))
)
def test_recomputed_oracle_matches_committed_yaml(scenario_yaml, geometry):
    # The three family yamls are frozen at prereg-v1; their `oracle:` blocks are
    # the pre-registered answers. Recomputing them here is the regression guard
    # that moving the feasibility math into reasoning/rag/scene_geometry.py left
    # the oracle numerically identical. Isaac is not importable on every dev
    # machine, so this goes through `family_oracle` directly rather than the
    # generator script.
    raw = yaml.safe_load((FAMILY_DIR / scenario_yaml).read_text())
    params = HeadOnAsymmetricParams(**raw["parameters"])

    recomputed = fo.compute_oracle(params, geometry)

    assert recomputed is not None
    assert recomputed.model_dump(mode="json") == OracleConfig(**raw["oracle"]).model_dump(
        mode="json"
    )

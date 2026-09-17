from pathlib import Path

import pytest
import yaml

from isaac.scripts import generate_head_on_family as gen
from isaac.vgu_sim.config import HeadOnAsymmetricParams, ScenarioConfig

ORCHESTRATOR_YAML = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")


@pytest.fixture
def geometry():
    return gen.load_scene_geometry(ORCHESTRATOR_YAML)


@pytest.fixture
def base() -> ScenarioConfig:
    return gen.load_scenario(gen.BASE_SCENARIO)


def test_variant_id_prints_open_and_p_floats():
    assert gen.variant_id(HeadOnAsymmetricParams(blocker_west_m=0.2)) == "w0p2_eopen_o0"
    assert gen.variant_id(HeadOnAsymmetricParams()) == "wopen_eopen_o0"


def test_grid_v1_has_four_cells():
    assert [gen.variant_id(p) for p in gen.grid_v1()] == [
        "w0p2_e0p2_o0",
        "w0p2_eopen_o0",
        "wopen_e0p2_o0",
        "wopen_eopen_o0",
    ]


def test_build_variant_skips_double_blocker(base, geometry):
    params = HeadOnAsymmetricParams(blocker_west_m=0.2, blocker_east_m=0.2)
    assert gen.build_variant(base, params, geometry) is None


def test_build_variant_west_places_static_blocker_at_minus_1p85(base, geometry):
    config = gen.build_variant(base, HeadOnAsymmetricParams(blocker_west_m=0.2), geometry)

    assert len(config.static_obstacles) == 1
    obstacle = config.static_obstacles[0]
    assert obstacle.obstacle_id == "blocker_west"
    assert obstacle.pose.x == -1.85
    assert obstacle.pose.y == 0.0
    assert (obstacle.size.x_m, obstacle.size.y_m, obstacle.size.z_m) == (0.3, 0.3, 0.5)
    assert [r.spawn for r in config.robots] == [r.spawn for r in base.robots]


def test_build_variant_open_matches_base_geometry(base, geometry):
    config = gen.build_variant(base, HeadOnAsymmetricParams(), geometry)

    assert config.static_obstacles == ()
    assert config.aisle_barrier == base.aisle_barrier
    assert config.oracle.correct_yielder == "robot_1"


def test_render_yaml_round_trips(base, geometry):
    config = gen.build_variant(base, HeadOnAsymmetricParams(blocker_west_m=0.2), geometry)

    text = gen.render_yaml(config, geometry)

    assert ScenarioConfig.model_validate(yaml.safe_load(text)) == config


def test_manifest_rows_mark_tier_and_contrast(base, geometry):
    configs = [gen.build_variant(base, p, geometry) for p in gen.grid_v1()]

    rows = gen.manifest_rows([c for c in configs if c is not None])

    assert len(rows) == 3
    by_variant = {row["variant"]: row for row in rows}
    assert by_variant["w0p2_eopen_o0"]["tier"] == "T2a"
    assert by_variant["w0p2_eopen_o0"]["contrasts_fcfs"] == "true"
    assert by_variant["wopen_e0p2_o0"]["tier"] == "T2a"
    assert by_variant["wopen_e0p2_o0"]["contrasts_fcfs"] == "false"
    assert by_variant["wopen_eopen_o0"]["tier"] == "T1"
    assert by_variant["wopen_eopen_o0"]["contrasts_fcfs"] == "false"


def test_write_family_writes_three_yamls_and_manifest(tmp_path):
    written = gen.write_family(tmp_path, ORCHESTRATOR_YAML)

    assert sorted(p.name for p in written) == [
        "head_on_asymmetric_w0p2_eopen_o0.yaml",
        "head_on_asymmetric_wopen_e0p2_o0.yaml",
        "head_on_asymmetric_wopen_eopen_o0.yaml",
    ]
    assert (tmp_path / "family_manifest.csv").is_file()


def test_committed_family_matches_generator_output(tmp_path):
    gen.write_family(tmp_path, ORCHESTRATOR_YAML)
    generated = {p.name for p in tmp_path.iterdir()}
    committed = {p.name for p in gen.FAMILY_DIR.iterdir() if p.is_file()}

    assert committed == generated
    for name in sorted(generated):
        assert (gen.FAMILY_DIR / name).read_text() == (tmp_path / name).read_text(), name

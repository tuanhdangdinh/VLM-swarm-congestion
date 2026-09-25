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
    written = gen.write_family(tmp_path, ORCHESTRATOR_YAML, goal_modes=("beyond",))

    assert sorted(p.name for p in written) == [
        "head_on_asymmetric_w0p2_eopen_o0.yaml",
        "head_on_asymmetric_wopen_e0p2_o0.yaml",
        "head_on_asymmetric_wopen_eopen_o0.yaml",
    ]
    assert (tmp_path / "family_manifest.csv").is_file()


def test_variant_id_inserts_gshort_before_arrival_offset():
    params = HeadOnAsymmetricParams(blocker_west_m=0.2)

    assert gen.variant_id(params, "opponent_spawn") == "w0p2_eopen_gshort_o0"
    assert gen.variant_id(params, "beyond") == gen.variant_id(params)


def test_grid_gshort_covers_only_single_blocker_cells():
    assert [gen.variant_id(p, "opponent_spawn") for p in gen.grid_gshort()] == [
        "w0p2_eopen_gshort_o0",
        "wopen_e0p2_gshort_o0",
    ]


def test_build_variant_opponent_spawn_puts_each_goal_on_the_other_spawn(base, geometry):
    params = HeadOnAsymmetricParams(blocker_west_m=0.2)

    config = gen.build_variant(base, params, geometry, "opponent_spawn")

    goals = {r.robot_id: (r.goal.x, r.goal.y) for r in config.robots}
    spawns = {r.robot_id: r.spawn.x for r in config.robots}
    assert goals == {"robot_1": (1.5, 0.0), "robot_2": (-1.5, 0.0)}
    assert goals["robot_1"][0] == spawns["robot_2"]
    assert goals["robot_2"][0] == spawns["robot_1"]


def test_build_variant_opponent_spawn_keeps_goals_clear_of_the_blocker(base, geometry):
    params = HeadOnAsymmetricParams(blocker_west_m=0.2)

    config = gen.build_variant(base, params, geometry, "opponent_spawn")

    blocker = config.static_obstacles[0]
    near_face_x = blocker.pose.x + blocker.size.x_m / 2.0
    # robot_2 crosses west; its goal must stop short of the box, not past it.
    robot_2_goal_x = next(r.goal.x for r in config.robots if r.robot_id == "robot_2")
    assert robot_2_goal_x > near_face_x


def test_build_variant_opponent_spawn_leaves_the_oracle_unchanged(base, geometry):
    for params in gen.grid_gshort():
        beyond = gen.build_variant(base, params, geometry, "beyond")
        gshort = gen.build_variant(base, params, geometry, "opponent_spawn")

        assert gshort.oracle == beyond.oracle, params
        assert gshort.static_obstacles == beyond.static_obstacles, params
        assert [r.spawn for r in gshort.robots] == [r.spawn for r in beyond.robots], params
        assert gshort.parameters == beyond.parameters, params


def test_build_variant_default_goal_mode_matches_beyond(base, geometry):
    params = HeadOnAsymmetricParams(blocker_west_m=0.2)

    assert gen.build_variant(base, params, geometry) == gen.build_variant(
        base, params, geometry, "beyond"
    )


def test_write_family_default_goal_mode_reproduces_committed_v1_bytes(tmp_path):
    gen.write_family(tmp_path, ORCHESTRATOR_YAML, goal_modes=("beyond",))

    for name in (
        "head_on_asymmetric_w0p2_eopen_o0.yaml",
        "head_on_asymmetric_wopen_e0p2_o0.yaml",
        "head_on_asymmetric_wopen_eopen_o0.yaml",
    ):
        assert (gen.FAMILY_DIR / name).read_text() == (tmp_path / name).read_text(), name


def test_committed_manifest_has_five_rows_with_v1_first():
    rows = (gen.FAMILY_DIR / gen.MANIFEST_NAME).read_text().splitlines()

    assert len(rows) == 6  # header + 5 variants
    assert [r.split(",")[1] for r in rows[1:]] == [
        "w0p2_eopen_o0",
        "wopen_e0p2_o0",
        "wopen_eopen_o0",
        "w0p2_eopen_gshort_o0",
        "wopen_e0p2_gshort_o0",
    ]


@pytest.mark.parametrize(
    ("name", "goals"),
    [
        (
            "head_on_asymmetric_w0p2_eopen_gshort_o0",
            {"robot_1": (1.5, 0.0), "robot_2": (-1.5, 0.0)},
        ),
        (
            "head_on_asymmetric_wopen_e0p2_gshort_o0",
            {"robot_1": (1.5, 0.0), "robot_2": (-1.5, 0.0)},
        ),
    ],
)
def test_committed_gshort_yaml_round_trips(name, goals):
    config = gen.load_scenario(gen.FAMILY_DIR / f"{name}.yaml")

    assert config.name == name
    assert config.family == "head_on"
    assert {r.robot_id: (r.goal.x, r.goal.y) for r in config.robots} == goals
    assert config.oracle is not None
    assert config.parameters is not None


def test_committed_family_matches_generator_output(tmp_path):
    gen.write_family(tmp_path, ORCHESTRATOR_YAML)
    generated = {p.name for p in tmp_path.iterdir()}
    committed = {p.name for p in gen.FAMILY_DIR.iterdir() if p.is_file()}

    assert committed == generated
    for name in sorted(generated):
        assert (gen.FAMILY_DIR / name).read_text() == (tmp_path / name).read_text(), name

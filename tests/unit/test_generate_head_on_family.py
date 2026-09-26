from pathlib import Path

import pytest
import yaml

from isaac.scripts import generate_head_on_family as gen
from isaac.vgu_sim.config import HeadOnAsymmetricParams, ScenarioConfig
from reasoning.rag.scene_geometry import park_offset_m, passer_clearance_m

ORCHESTRATOR_YAML = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
# Half the robot's extent along the corridor axis, from the Nav2 footprint
# `[[-0.07, -0.09], [0.07, 0.09]]` in swarm_simulation/config/nav2_params.yaml.
# `scene_geometry` declares only `half_width_m`, so the along-axis half-length
# has to come from the footprint that Nav2 and the costmaps actually use.
ROBOT_HALF_LENGTH_M = 0.07
# swarm_orchestrator/config/orchestrator.yaml `arrival_position_tolerance_m`.
ARRIVAL_POSITION_TOLERANCE_M = 0.35


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


def test_committed_manifest_has_seven_rows_with_v1_first():
    rows = (gen.FAMILY_DIR / gen.MANIFEST_NAME).read_text().splitlines()

    assert len(rows) == 8  # header + 7 variants
    assert [r.split(",")[1] for r in rows[1:]] == [
        "w0p2_eopen_o0",
        "wopen_e0p2_o0",
        "wopen_eopen_o0",
        "w0p2_eopen_gshort_o0",
        "wopen_e0p2_gshort_o0",
        "w0p2_eopen_bshort_o0",
        "wopen_e0p2_bshort_o0",
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


def test_variant_id_inserts_bshort_before_arrival_offset():
    params = HeadOnAsymmetricParams(blocker_west_m=0.2)

    assert gen.variant_id(params, "blocked_short") == "w0p2_eopen_bshort_o0"


def test_write_family_through_gshort_reproduces_committed_gshort_bytes(tmp_path):
    # Adding a third mode must leave the frozen v1 and gshort artifacts alone:
    # restricting the modes is documented to yield a strict manifest prefix.
    gen.write_family(tmp_path, ORCHESTRATOR_YAML, goal_modes=("beyond", "opponent_spawn"))

    for name in (
        "head_on_asymmetric_w0p2_eopen_o0.yaml",
        "head_on_asymmetric_wopen_e0p2_o0.yaml",
        "head_on_asymmetric_wopen_eopen_o0.yaml",
        "head_on_asymmetric_w0p2_eopen_gshort_o0.yaml",
        "head_on_asymmetric_wopen_e0p2_gshort_o0.yaml",
    ):
        assert (gen.FAMILY_DIR / name).read_text() == (tmp_path / name).read_text(), name


@pytest.mark.parametrize(
    ("params", "goals"),
    [
        (
            HeadOnAsymmetricParams(blocker_west_m=0.2),
            {"robot_1": (2.6, 0.0), "robot_2": (-1.5, 0.0)},
        ),
        (
            HeadOnAsymmetricParams(blocker_east_m=0.2),
            {"robot_1": (1.5, 0.0), "robot_2": (-2.6, 0.0)},
        ),
    ],
)
def test_build_variant_blocked_short_shortens_only_the_blocked_side_goal(
    base, geometry, params, goals
):
    config = gen.build_variant(base, params, geometry, "blocked_short")

    assert {r.robot_id: (r.goal.x, r.goal.y) for r in config.robots} == goals


def test_build_variant_blocked_short_mirrors_west_and_east(base, geometry):
    # A sign error in the blocked-side lookup would shorten the wrong goal on
    # exactly one side, which only a mirror comparison catches.
    west = gen.build_variant(
        base, HeadOnAsymmetricParams(blocker_west_m=0.2), geometry, "blocked_short"
    )
    east = gen.build_variant(
        base, HeadOnAsymmetricParams(blocker_east_m=0.2), geometry, "blocked_short"
    )

    west_goals = {r.robot_id: r.goal.x for r in west.robots}
    east_goals = {r.robot_id: r.goal.x for r in east.robots}
    assert west_goals["robot_1"] == -east_goals["robot_2"]
    assert west_goals["robot_2"] == -east_goals["robot_1"]


def test_build_variant_blocked_short_leaves_the_oracle_unchanged(base, geometry):
    for params in gen.grid_gshort():
        beyond = gen.build_variant(base, params, geometry, "beyond")
        bshort = gen.build_variant(base, params, geometry, "blocked_short")

        assert bshort.oracle == beyond.oracle, params
        assert bshort.static_obstacles == beyond.static_obstacles, params
        assert [r.spawn for r in bshort.robots] == [r.spawn for r in beyond.robots], params
        assert bshort.parameters == beyond.parameters, params


def test_build_variant_blocked_short_rejects_a_cell_without_one_blocked_side(base, geometry):
    with pytest.raises(ValueError, match="exactly one blocked side"):
        gen.build_variant(base, HeadOnAsymmetricParams(), geometry, "blocked_short")


def test_blocked_short_passer_goal_clears_the_yielder_park_point(base, geometry):
    # The gshort west losses: the passer's goal fell INSIDE the park point, so
    # the arrived passer sat in the yielder's return path. Here it must not.
    config = gen.build_variant(
        base, HeadOnAsymmetricParams(blocker_west_m=0.2), geometry, "blocked_short"
    )

    park = park_offset_m(geometry)
    passer_goal_x = next(r.goal.x for r in config.robots if r.robot_id == "robot_1")
    assert park == pytest.approx(1.789, abs=1e-3)
    assert passer_goal_x - park >= 0.6


@pytest.mark.parametrize(
    ("params", "passer"),
    [
        (HeadOnAsymmetricParams(blocker_west_m=0.2), "robot_1"),
        (HeadOnAsymmetricParams(blocker_east_m=0.2), "robot_2"),
    ],
)
def test_blocked_short_passer_goal_clears_the_escort_endpoint_by_drift_margin(
    base, geometry, params, passer
):
    # M3 escorts the passer to park + passer_clearance_m. A goal short of that
    # makes the passer double back toward the yielder, which is how gshort H2
    # latched at 0.430 m. At +-2.5 the goal cleared it by only 0.061 m, less
    # than the ~0.1 m odometry drift FEASIBILITY_MARGIN_M budgets for.
    config = gen.build_variant(base, params, geometry, "blocked_short")

    escort_end_x = park_offset_m(geometry) + passer_clearance_m(geometry)
    passer_goal_x = next(r.goal.x for r in config.robots if r.robot_id == passer)
    assert escort_end_x == pytest.approx(2.439, abs=1e-3)
    assert abs(passer_goal_x) - escort_end_x >= 0.15


def test_blocked_short_yielder_goal_stops_short_of_the_blocker_box(base, geometry):
    config = gen.build_variant(
        base, HeadOnAsymmetricParams(blocker_west_m=0.2), geometry, "blocked_short"
    )

    blocker = config.static_obstacles[0]
    near_face_x = blocker.pose.x + blocker.size.x_m / 2.0
    yielder_goal_x = next(r.goal.x for r in config.robots if r.robot_id == "robot_2")
    chassis_front_x = yielder_goal_x - ROBOT_HALF_LENGTH_M
    assert near_face_x == pytest.approx(-1.70, abs=1e-6)
    assert yielder_goal_x - near_face_x == pytest.approx(0.20, abs=1e-6)
    # Goal-centre gap 0.20 m less the chassis half-length leaves 0.13 m of air.
    assert chassis_front_x - near_face_x == pytest.approx(0.13, abs=1e-6)


def test_arrival_tolerance_band_reaches_inside_the_blocker_box(base, geometry):
    # Documented hazard, NOT a reason to move the goal: M5 accepts an arrival
    # anywhere within arrival_position_tolerance_m of the goal, and the far
    # edge of that band puts the chassis inside the box. The box is baked
    # lethal into the Nav2 static map, so this is an acceptance-check risk
    # rather than a driving one -- score box clearance from ground truth.
    config = gen.build_variant(
        base, HeadOnAsymmetricParams(blocker_west_m=0.2), geometry, "blocked_short"
    )

    blocker = config.static_obstacles[0]
    near_face_x = blocker.pose.x + blocker.size.x_m / 2.0
    far_face_x = blocker.pose.x - blocker.size.x_m / 2.0
    yielder_goal_x = next(r.goal.x for r in config.robots if r.robot_id == "robot_2")
    worst_accepted_x = yielder_goal_x - ARRIVAL_POSITION_TOLERANCE_M
    assert worst_accepted_x - ROBOT_HALF_LENGTH_M < near_face_x
    assert worst_accepted_x > far_face_x


@pytest.mark.parametrize(
    ("name", "goals"),
    [
        (
            "head_on_asymmetric_w0p2_eopen_bshort_o0",
            {"robot_1": (2.6, 0.0), "robot_2": (-1.5, 0.0)},
        ),
        (
            "head_on_asymmetric_wopen_e0p2_bshort_o0",
            {"robot_1": (1.5, 0.0), "robot_2": (-2.6, 0.0)},
        ),
    ],
)
def test_committed_bshort_yaml_round_trips(name, goals):
    config = gen.load_scenario(gen.FAMILY_DIR / f"{name}.yaml")

    assert config.name == name
    assert config.family == "head_on"
    assert {r.robot_id: (r.goal.x, r.goal.y) for r in config.robots} == goals
    assert config.oracle is not None
    assert config.parameters is not None


def test_committed_bshort_yaml_carries_initial_tasks_guidance():
    text = (gen.FAMILY_DIR / "head_on_asymmetric_w0p2_eopen_bshort_o0.yaml").read_text()

    assert "initial_tasks" in text
    assert "robot_1: { task: cross_narrow_aisle, goal: [2.6, 0] }" in text
    assert "robot_2: { task: cross_narrow_aisle, goal: [-1.5, 0] }" in text


def test_committed_family_matches_generator_output(tmp_path):
    gen.write_family(tmp_path, ORCHESTRATOR_YAML)
    generated = {p.name for p in tmp_path.iterdir()}
    committed = {p.name for p in gen.FAMILY_DIR.iterdir() if p.is_file()}

    assert committed == generated
    for name in sorted(generated):
        assert (gen.FAMILY_DIR / name).read_text() == (tmp_path / name).read_text(), name

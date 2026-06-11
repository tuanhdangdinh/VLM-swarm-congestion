from pathlib import Path

import pytest

from isaac.vgu_sim.paths import (
    component_asset_path,
    robot_asset_path,
    run_output_dir,
    scenario_config_path,
    scenario_output_path,
    warehouse_asset_path,
)


def test_robot_asset_path_is_under_isaac():
    p = robot_asset_path()
    assert p == Path("isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.usda")


def test_warehouse_asset_path():
    p = warehouse_asset_path()
    assert p == Path("isaac/assets/warehouse/warehouse_base.usd")


def test_scenario_config_path():
    p = scenario_config_path("head_on_deadlock")
    assert p == Path("isaac/config/scenarios/head_on_deadlock.yaml")


def test_scenario_output_path():
    p = scenario_output_path("head_on_deadlock")
    assert p == Path("isaac/scenarios/head_on_deadlock.usd")


def test_run_output_dir():
    p = run_output_dir(Path("data/logs/simulation"), "head_on_deadlock", seed=42, rep=0)
    assert p == Path("data/logs/simulation/head_on_deadlock-seed42-rep000")


def test_paths_are_relative():
    for p in [robot_asset_path(), warehouse_asset_path(),
              scenario_config_path("dynamic_anomaly"), scenario_output_path("dynamic_anomaly")]:
        assert not p.is_absolute(), f"{p} must be relative"


def test_component_asset_paths():
    assert component_asset_path("rack_block") == Path("isaac/assets/warehouse/rack_block.usd")
    assert component_asset_path("aisle_barrier") == Path("isaac/assets/warehouse/aisle_barrier.usd")
    assert component_asset_path("dynamic_obstacle") == Path("isaac/assets/warehouse/dynamic_obstacle.usd")
    assert component_asset_path("loading_zone") == Path("isaac/assets/warehouse/loading_zone.usd")


def test_unknown_component_raises():
    with pytest.raises(ValueError, match="Unknown component"):
        component_asset_path("unknown_thing")

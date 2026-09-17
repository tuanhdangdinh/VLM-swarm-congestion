from pathlib import Path

import pytest
from pxr import Usd, UsdGeom, UsdPhysics

from isaac.vgu_sim.config import ScenarioConfig
from isaac.vgu_sim.scenario_builder import build_scenario_stage
from tests.unit.test_m6_config import VALID_HEAD_ON


def _empty_stage(path: Path) -> Path:
    stage = Usd.Stage.CreateNew(str(path))
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    stage.Save()
    return path


def test_scenario_builder_authors_aisle_barrier_when_configured(tmp_path):
    scenario = ScenarioConfig.model_validate(
        {
            **VALID_HEAD_ON,
            "aisle_barrier": {
                "effective_width_m": 0.4,
                "center_x_m": 0.0,
                "length_m": 0.9,
            },
        }
    )
    warehouse = _empty_stage(tmp_path / "warehouse.usd")
    robot = _empty_stage(tmp_path / "robot.usd")
    output = tmp_path / "scenario.usd"

    build_scenario_stage(
        scenario,
        warehouse_path=warehouse,
        robot_asset_path=robot,
        output_path=output,
    )

    stage = Usd.Stage.Open(str(output))
    barriers = stage.GetPrimAtPath("/World/Scenario/AisleBarriers")
    north = stage.GetPrimAtPath("/World/Scenario/AisleBarriers/north")
    south = stage.GetPrimAtPath("/World/Scenario/AisleBarriers/south")

    assert barriers.IsValid()
    assert north.IsValid()
    assert south.IsValid()
    assert north.HasAPI(UsdPhysics.CollisionAPI)
    assert south.HasAPI(UsdPhysics.CollisionAPI)

    cache = UsdGeom.BBoxCache(0, [UsdGeom.Tokens.default_], useExtentsHint=False)
    north_box = cache.ComputeWorldBound(north).ComputeAlignedBox()
    south_box = cache.ComputeWorldBound(south).ComputeAlignedBox()

    assert north_box.GetMin()[0] == pytest.approx(-0.45)
    assert north_box.GetMax()[0] == pytest.approx(0.45)
    assert north_box.GetMin()[1] == pytest.approx(0.2)
    assert north_box.GetMax()[1] == pytest.approx(0.6)
    assert south_box.GetMin()[1] == pytest.approx(-0.6)
    assert south_box.GetMax()[1] == pytest.approx(-0.2)


def _build(scenario: ScenarioConfig, tmp_path: Path):
    warehouse = _empty_stage(tmp_path / "warehouse.usd")
    robot = _empty_stage(tmp_path / "robot.usd")
    output = tmp_path / "scenario.usd"

    build_scenario_stage(
        scenario,
        warehouse_path=warehouse,
        robot_asset_path=robot,
        output_path=output,
    )
    return Usd.Stage.Open(str(output))


def test_scenario_builder_authors_static_obstacle_as_collision_cube(tmp_path):
    scenario = ScenarioConfig.model_validate(
        {
            **VALID_HEAD_ON,
            "static_obstacles": [
                {
                    "obstacle_id": "blocker_west",
                    "pose": {"x": -1.85, "y": 0.0, "yaw_rad": 0.0},
                },
            ],
        }
    )

    stage = _build(scenario, tmp_path)
    prim = stage.GetPrimAtPath("/World/Scenario/StaticObstacles/blocker_west")

    assert prim.IsValid()
    assert UsdGeom.Cube(prim)
    assert prim.HasAPI(UsdPhysics.CollisionAPI)
    assert prim.IsActive()
    assert tuple(prim.GetAttribute("xformOp:translate").Get()) == pytest.approx(
        (-1.85, 0.0, 0.25)
    )
    assert tuple(prim.GetAttribute("xformOp:scale").Get()) == pytest.approx(
        (0.15, 0.15, 0.25)
    )
    assert tuple(prim.GetAttribute("primvars:displayColor").Get()[0]) == pytest.approx(
        (0.5, 0.5, 0.5)
    )


def test_scenario_builder_authors_timed_obstacle_geometry_inactive(tmp_path):
    scenario = ScenarioConfig.model_validate(
        {
            **VALID_HEAD_ON,
            "timed_obstacles": [
                {
                    "obstacle_id": "blocker_east",
                    "asset": "dynamic_obstacle.usd",
                    "spawn_at_sec": 10.0,
                    "pose": {"x": 1.0, "y": 0.0, "yaw_rad": 0.0},
                },
            ],
        }
    )

    stage = _build(scenario, tmp_path)
    prim = stage.GetPrimAtPath("/World/DynamicObstacles/blocker_east")

    assert prim.IsValid()
    assert UsdGeom.Cube(prim)
    assert prim.HasAPI(UsdPhysics.CollisionAPI)
    assert prim.IsActive() is False
    assert tuple(prim.GetAttribute("xformOp:scale").Get()) == pytest.approx(
        (0.15, 0.15, 0.25)
    )
    assert tuple(prim.GetAttribute("primvars:displayColor").Get()[0]) == pytest.approx(
        (0.8, 0.3, 0.3)
    )


def test_scenario_builder_defines_empty_static_obstacles_root(tmp_path):
    scenario = ScenarioConfig.model_validate(VALID_HEAD_ON)

    stage = _build(scenario, tmp_path)
    root = stage.GetPrimAtPath("/World/Scenario/StaticObstacles")

    assert root.IsValid()
    assert list(root.GetChildren()) == []

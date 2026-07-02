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

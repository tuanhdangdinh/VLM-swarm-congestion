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


def _fake_robot_asset(path: Path, *, with_none_variant: bool = True) -> Path:
    """A stand-in for the imported robot USD: a `Physics` variant set whose
    `physx` variant (the asset default) applies an articulation root, and a
    body cube offset from the root like the burger's (-0.032 m in x)."""
    stage = Usd.Stage.CreateNew(str(path))
    root = UsdGeom.Xform.Define(stage, "/turtlebot3_burger").GetPrim()
    stage.SetDefaultPrim(root)
    body = UsdGeom.Cube.Define(stage, "/turtlebot3_burger/Geometry/base_link/body")
    body.CreateSizeAttr(0.1)
    body.AddTranslateOp().Set((-0.032, 0.0, 0.05))
    UsdGeom.Xform.Define(stage, "/turtlebot3_burger/Geometry/base_link/aruco_marker_link")
    variant_set = root.GetVariantSets().AddVariantSet("Physics")
    names = ("none", "physx") if with_none_variant else ("physx",)
    for name in names:
        variant_set.AddVariant(name)
    variant_set.SetVariantSelection("physx")
    with variant_set.GetVariantEditContext():
        UsdPhysics.ArticulationRootAPI.Apply(root)
    stage.Save()
    return path


def _robot_visual_scenario(yaw_rad: float = 0.0) -> ScenarioConfig:
    return ScenarioConfig.model_validate(
        {
            **VALID_HEAD_ON,
            "timed_obstacles": [
                {
                    "obstacle_id": "blocker",
                    "asset": "robot_visual_no_marker",
                    "spawn_at_sec": 10.0,
                    "remove_at_sec": 20.0,
                    "pose": {"x": -0.5, "y": 0.2, "yaw_rad": yaw_rad},
                },
            ],
        }
    )


def _build_with_robot(scenario: ScenarioConfig, tmp_path: Path, **asset_kwargs):
    warehouse = _empty_stage(tmp_path / "warehouse.usd")
    robot = _fake_robot_asset(tmp_path / "robot.usda", **asset_kwargs)
    output = tmp_path / "scenario.usd"
    build_scenario_stage(
        scenario, warehouse_path=warehouse, robot_asset_path=robot, output_path=output
    )
    return Usd.Stage.Open(str(output))


def test_robot_visual_obstacle_references_robot_asset_inactive(tmp_path):
    stage = _build_with_robot(_robot_visual_scenario(), tmp_path)
    prim = stage.GetPrimAtPath("/World/DynamicObstacles/blocker")

    assert prim.IsValid()
    assert prim.IsActive() is False
    assert prim.GetMetadata("references").GetAddedOrExplicitItems()[0].assetPath == "robot.usda"


def test_robot_visual_obstacle_selects_physics_none_variant(tmp_path):
    stage = _build_with_robot(_robot_visual_scenario(), tmp_path)
    prim = stage.GetPrimAtPath("/World/DynamicObstacles/blocker")
    prim.SetActive(True)

    assert prim.GetVariantSets().GetVariantSet("Physics").GetVariantSelection() == "none"
    assert not any(p.HasAPI(UsdPhysics.ArticulationRootAPI) for p in Usd.PrimRange(prim))


def test_robot_visual_obstacle_has_no_marker_mesh(tmp_path):
    stage = _build_with_robot(_robot_visual_scenario(), tmp_path)
    prim = stage.GetPrimAtPath("/World/DynamicObstacles/blocker")
    prim.SetActive(True)

    assert not any(p.GetName() == "aruco_marker" for p in Usd.PrimRange(prim))


@pytest.mark.parametrize("yaw_rad", [0.0, 1.5707963267948966, 2.5])
def test_robot_visual_obstacle_footprint_center_sits_at_pose(tmp_path, yaw_rad):
    from isaac.vgu_sim.config import ROBOT_VISUAL_NO_MARKER_SCALE

    stage = _build_with_robot(_robot_visual_scenario(yaw_rad), tmp_path)
    prim = stage.GetPrimAtPath("/World/DynamicObstacles/blocker")
    prim.SetActive(True)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
    mid = box.GetMidpoint()

    assert (mid[0], mid[1]) == pytest.approx((-0.5, 0.2))
    assert box.GetSize()[2] == pytest.approx(0.1 * ROBOT_VISUAL_NO_MARKER_SCALE)


def test_robot_visual_obstacle_is_not_a_tracked_robot(tmp_path):
    stage = _build_with_robot(_robot_visual_scenario(), tmp_path)

    assert [p.GetName() for p in stage.GetPrimAtPath("/World/Robots").GetChildren()] == [
        "robot_1",
        "robot_2",
    ]


def test_robot_visual_obstacle_requires_physics_none_variant(tmp_path):
    from isaac.vgu_sim.scenario_builder import ScenarioBuildError

    with pytest.raises(ScenarioBuildError, match="none"):
        _build_with_robot(_robot_visual_scenario(), tmp_path, with_none_variant=False)


def test_static_box_obstacle_is_grey_inactive_cube(tmp_path):
    scenario = ScenarioConfig.model_validate(
        {
            **VALID_HEAD_ON,
            "timed_obstacles": [
                {
                    "obstacle_id": "crate",
                    "asset": "static_box",
                    "spawn_at_sec": 10.0,
                    "pose": {"x": -0.5, "y": 0.0, "yaw_rad": 0.0},
                    "size": {"x_m": 0.25, "y_m": 0.32, "z_m": 0.35},
                },
            ],
        }
    )

    stage = _build(scenario, tmp_path)
    prim = stage.GetPrimAtPath("/World/DynamicObstacles/crate")

    assert UsdGeom.Cube(prim)
    assert prim.HasAPI(UsdPhysics.CollisionAPI)
    assert prim.IsActive() is False
    assert tuple(prim.GetAttribute("primvars:displayColor").Get()[0]) == pytest.approx(
        (0.5, 0.5, 0.5)
    )


def test_committed_dynamic_anomaly_timed_obstacles_stay_legacy_red_boxes(tmp_path):
    # Pins the default: scenarios authored before the built-in assets existed
    # (asset = a never-referenced file name) still build the same red box.
    from isaac.scripts.generate_warehouse_map import load_scenario

    repo = Path(__file__).resolve().parents[2]
    for name in ("dynamic_anomaly", "dynamic_anomaly_v2"):
        scenario = load_scenario(repo / f"isaac/config/scenarios/{name}.yaml")
        (tmp_path / name).mkdir()
        stage = _build(scenario, tmp_path / name)
        for obs in scenario.timed_obstacles:
            prim = stage.GetPrimAtPath(f"/World/DynamicObstacles/{obs.obstacle_id}")
            assert UsdGeom.Cube(prim), (name, obs.obstacle_id)
            assert tuple(prim.GetAttribute("primvars:displayColor").Get()[0]) == pytest.approx(
                (0.8, 0.3, 0.3)
            )

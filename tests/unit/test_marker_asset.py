import pytest
from pxr import Sdf, Usd, UsdGeom, UsdShade

from isaac.vgu_sim.marker_asset import (
    MARKER_HEIGHT_M,
    MARKER_SIZE_M,
    author_aruco_marker,
)


def _stage():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World/Robots/robot_1")
    return stage


def test_marker_quad_is_a_mesh_with_st_primvar():
    stage = _stage()
    author_aruco_marker(stage, "/World/Robots/robot_1", "markers/aruco_4x4_50/marker_1.png")
    mesh = UsdGeom.Mesh.Get(stage, "/World/Robots/robot_1/aruco_marker")
    assert mesh, "marker mesh not authored"
    st = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("st")
    assert st and len(st.Get()) == 4


def test_marker_quad_sized_and_raised():
    stage = _stage()
    author_aruco_marker(stage, "/World/Robots/robot_1", "markers/aruco_4x4_50/marker_1.png")
    mesh = UsdGeom.Mesh.Get(stage, "/World/Robots/robot_1/aruco_marker")
    pts = mesh.GetPointsAttr().Get()
    half = MARKER_SIZE_M / 2.0
    # USD stores points as float32, so compare with tolerance, not exact equality.
    assert max(p[0] for p in pts) == pytest.approx(half)
    assert min(p[0] for p in pts) == pytest.approx(-half)
    xf = UsdGeom.Xformable(mesh).GetLocalTransformation()
    assert xf.ExtractTranslation()[2] == pytest.approx(MARKER_HEIGHT_M)


def test_marker_material_binds_expected_texture():
    stage = _stage()
    tex_path = "markers/aruco_4x4_50/marker_7.png"
    author_aruco_marker(stage, "/World/Robots/robot_1", tex_path)
    shader = UsdShade.Shader.Get(
        stage, "/World/Robots/robot_1/aruco_marker/Material/Texture"
    )
    assert shader
    assert shader.GetInput("file").Get().path == tex_path
    mesh = UsdGeom.Mesh.Get(stage, "/World/Robots/robot_1/aruco_marker")
    bound = UsdShade.MaterialBindingAPI(mesh).GetDirectBinding().GetMaterial()
    assert bound


def test_author_robot_adds_marker_with_id_texture(tmp_path):
    from isaac.vgu_sim.config import Goal2D, Pose2D, RobotScenarioConfig
    from isaac.vgu_sim.scenario_builder import _author_robot

    stage = Usd.Stage.CreateNew(str(tmp_path / "scene.usda"))
    robot_asset = tmp_path / "turtlebot3_burger.usda"
    robot_asset.write_text("#usda 1.0\n")  # minimal referenceable stub

    cfg = RobotScenarioConfig(
        robot_id="robot_2",
        marker_id=2,
        spawn=Pose2D(x=0.0, y=0.0, yaw_rad=0.0),
        goal=Goal2D(x=1.0, y=1.0),
        initial_task="idle",
    )
    _author_robot(stage, cfg, robot_asset, tmp_path)

    shader = UsdShade.Shader.Get(
        stage, "/World/Robots/robot_2/aruco_marker/Material/Texture"
    )
    assert shader
    assert shader.GetInput("file").Get().path.endswith("marker_2.png")

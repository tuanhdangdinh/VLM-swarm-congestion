from __future__ import annotations

from pxr import Gf, Sdf, UsdGeom, UsdShade

# Physical marker size (m). Converged with aruco.yaml and the parity test.
MARKER_SIZE_M = 0.12
# Marker frame height (m). Mirrors aruco_marker_joint in turtlebot3_burger.urdf;
# above the lidar (base_scan at z=0.172) so a nadir camera is not occluded.
MARKER_HEIGHT_M = 0.21


def author_aruco_marker(stage, robot_prim_path: str, texture_path: str):
    """Author a UV-mapped marker quad and emissive material under a robot prim.

    The marker is placed under aruco_marker_link (a physics child of base_link)
    so it follows the robot body during simulation. Placing it at the robot root
    level would leave it frozen at the spawn position while the chassis moves.

    Args:
        stage: USD stage being authored.
        robot_prim_path: Robot root prim, e.g. "/World/Robots/robot_1".
        texture_path: Marker PNG path, relative to the scenario stage.

    Returns:
        The authored `UsdGeom.Mesh` quad.
    """
    # aruco_marker_link is at the correct height inside the physics hierarchy.
    parent_path = (
        f"{robot_prim_path}/Geometry/base_footprint/base_link/aruco_marker_link"
    )
    marker_path = f"{parent_path}/aruco_marker"
    mesh = UsdGeom.Mesh.Define(stage, marker_path)

    h = MARKER_SIZE_M / 2.0
    mesh.CreatePointsAttr([(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)])
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    mesh.CreateNormalsAttr([(0, 0, 1)] * 4)
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)

    st = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying
    )
    st.Set([(0, 0), (1, 0), (1, 1), (0, 1)])

    xformable = UsdGeom.Xformable(mesh)
    # Zero offset — aruco_marker_link is already positioned at marker height.
    xformable.AddTranslateOp().Set(Gf.Vec3d(0, 0, 0))
    # The quad points + UV layout above place the ArUco printed-top edge (corners
    # 0-1, which M1's geometry.estimate_marker_heading treats as robot-forward) at
    # +90 deg from the robot prim's forward (+x) axis. Left uncorrected, M1 reports
    # a heading pi/2 off the authored yaw (verified: yaw 0 -> theta +pi/2). Rotate
    # the marker -90 deg about Z so printed-top aligns with robot-forward and the
    # detected heading matches the authored yaw, restoring parity with M1's tested
    # corner convention (tests/unit/test_perception.py top-edge cases).
    xformable.AddRotateZOp().Set(-90.0)

    _bind_emissive_texture(stage, mesh, f"{marker_path}/Material", texture_path)
    return mesh


def _bind_emissive_texture(stage, mesh, material_path: str, texture_path: str) -> None:
    material = UsdShade.Material.Define(stage, material_path)

    pbr = UsdShade.Shader.Define(stage, f"{material_path}/Surface")
    pbr.CreateIdAttr("UsdPreviewSurface")
    pbr.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0, 0, 0))
    pbr.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    pbr.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

    reader = UsdShade.Shader.Define(stage, f"{material_path}/stReader")
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    reader_out = reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    tex = UsdShade.Shader.Define(stage, f"{material_path}/Texture")
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_path)
    tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(reader_out)
    tex_out = tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    # Emissive so the black/white contrast is lighting-independent.
    pbr.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_out)
    surface_out = pbr.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(surface_out)

    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim())
    UsdShade.MaterialBindingAPI(mesh).Bind(material)

# ArUco Markers on Simulated Robots — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render a decodable, per-`marker_id` ArUco tag on each simulated TurtleBot so M1 perception can identify robots from the overhead camera, unblocking the M6→M1→M2 chain.

**Architecture:** A dev-venv script generates `DICT_4X4_50` marker PNGs (dictionary read from M1's `aruco.yaml`). Isaac scene authoring (`scenario_builder`) draws an explicit UV-mapped quad above the lidar on each robot and binds an emissive per-id material to it. Prerequisite asset fixes (expanded URDF + vendored meshes) make the robot importable. Size 0.12 m is converged across the authored quad, `aruco.yaml`, and tests.

**Tech Stack:** Python 3.11, `opencv-contrib-python` (`cv2.aruco`), USD (`pxr`: `UsdGeom`/`UsdShade`), pytest, NVIDIA Isaac Sim 6.0 (import + render only).

**Spec:** `docs/superpowers/specs/2026-06-17-aruco-markers-on-sim-robots-design.md`

**Commit convention (project rule, CLAUDE.md):** Conventional Commits, subject < 72 chars, **no `Co-Authored-By` trailer.**

---

## File Structure

| File | Create/Modify | Responsibility |
|---|---|---|
| `isaac/vgu_sim/paths.py` | Modify | Marker dict-slug + asset-dir/png path helpers |
| `scripts/generate_aruco_markers.py` | Create | Generate marker PNGs (dictionary from `aruco.yaml`) |
| `isaac/assets/markers/aruco_4x4_50/marker_<1..49>.png` | Create (generated, committed) | Marker textures |
| `ros2_ws/src/swarm_perception/config/aruco.yaml` | Modify | Align `marker_size_m` 0.08→0.12 |
| `isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.urdf` | Modify | Expand xacro, local mesh paths, raise marker joint, drop box visual |
| `isaac/assets/robots/turtlebot3_burger/meshes/*.stl` | Create (vendored) | The 4 referenced meshes |
| `isaac/vgu_sim/marker_asset.py` | Create | `author_aruco_marker()` USD quad + emissive material |
| `isaac/vgu_sim/scenario_builder.py` | Modify | Call `author_aruco_marker` from `_author_robot` |
| `isaac/vgu_sim/validation.py` | Modify | Validate the authored marker quad child |
| `tests/unit/test_aruco_generation.py` | Create | Generation determinism + dict-from-config |
| `tests/unit/test_aruco_parity.py` | Create | Full round-trip: each PNG → correct id |
| `tests/unit/test_marker_asset.py` | Create | `author_aruco_marker` quad/st/material |
| `tests/simulation/test_robot_asset_prereqs.py` | Create | URDF expanded + local meshes exist |

---

## Task 0: Branch and commit the spec

**Files:** none (git only)

- [ ] **Step 1: Branch off main**

Run:
```bash
git checkout -b feat/m6-aruco-markers
```

- [ ] **Step 2: Commit the approved spec**

```bash
git add docs/superpowers/specs/2026-06-17-aruco-markers-on-sim-robots-design.md
git commit -m "docs: spec for ArUco markers on simulated robots"
```

---

## Task 1: Path helpers for marker assets

**Files:**
- Modify: `isaac/vgu_sim/paths.py`
- Test: `tests/unit/test_aruco_generation.py` (path helpers section)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_aruco_generation.py`:
```python
from pathlib import Path

from isaac.vgu_sim import paths


def test_marker_dict_slug_strips_prefix_and_lowercases():
    assert paths.marker_dict_slug("DICT_4X4_50") == "aruco_4x4_50"


def test_marker_png_path_uses_slug_and_id():
    p = paths.marker_png_path("DICT_4X4_50", 7)
    assert p == Path("isaac/assets/markers/aruco_4x4_50/marker_7.png")


def test_aruco_dict_name_reads_single_source_of_truth():
    # The configured dictionary is read from M1's aruco.yaml — one source for
    # generation AND scene authoring, so the two cannot desync.
    assert paths.aruco_dict_name() == "DICT_4X4_50"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_aruco_generation.py -v`
Expected: FAIL — `AttributeError: module 'isaac.vgu_sim.paths' has no attribute 'marker_dict_slug'`

- [ ] **Step 3: Implement the helpers**

Add `import yaml` to the imports of `isaac/vgu_sim/paths.py`, then append:
```python
# Single source of truth for the ArUco dictionary: M1's perception config. Both
# the generator and the scenario authoring resolve the dictionary from here.
ARUCO_CONFIG_PATH = Path("ros2_ws/src/swarm_perception/config/aruco.yaml")


def aruco_dict_name(config_path: Path = ARUCO_CONFIG_PATH) -> str:
    cfg = yaml.safe_load(config_path.read_text())
    return cfg["aruco"]["dictionary"]


def marker_dict_slug(dictionary_name: str) -> str:
    return "aruco_" + dictionary_name.removeprefix("DICT_").lower()


def marker_assets_dir(dictionary_name: str) -> Path:
    return _ASSETS / "markers" / marker_dict_slug(dictionary_name)


def marker_png_path(dictionary_name: str, marker_id: int) -> Path:
    return marker_assets_dir(dictionary_name) / f"marker_{marker_id}.png"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_aruco_generation.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/paths.py tests/unit/test_aruco_generation.py
git commit -m "feat: marker asset path helpers derived from dictionary name"
```

---

## Task 2: Marker generation script

**Files:**
- Create: `scripts/generate_aruco_markers.py`
- Test: `tests/unit/test_aruco_generation.py` (generation section)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_aruco_generation.py`:
```python
import cv2

from scripts.generate_aruco_markers import generate_markers


def test_generate_writes_all_ids_and_is_deterministic(tmp_path):
    generate_markers("DICT_4X4_50", tmp_path, ids=range(1, 50))
    files = sorted(p.name for p in tmp_path.glob("*.png"))
    assert files == [f"marker_{i}.png" for i in range(1, 50)]

    first = (tmp_path / "marker_1.png").read_bytes()
    generate_markers("DICT_4X4_50", tmp_path, ids=[1])  # regenerate
    assert (tmp_path / "marker_1.png").read_bytes() == first  # deterministic


def test_generated_marker_is_square(tmp_path):
    generate_markers("DICT_4X4_50", tmp_path, ids=[3])
    img = cv2.imread(str(tmp_path / "marker_3.png"), cv2.IMREAD_GRAYSCALE)
    assert img.shape[0] == img.shape[1]


def test_unsupported_dictionary_raises(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="NOT_A_DICT"):
        generate_markers("NOT_A_DICT", tmp_path, ids=[1])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_aruco_generation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.generate_aruco_markers'`

- [ ] **Step 3: Implement the script**

Create `scripts/generate_aruco_markers.py`:
```python
#!/usr/bin/env python3
"""Generate ArUco marker PNGs for the simulated robots.

Run in the project venv (needs cv2.aruco; NOT Isaac's embedded python):
    python -m scripts.generate_aruco_markers

The dictionary is read from M1's aruco.yaml so the simulator and M1 cannot
desync. Output goes to isaac/assets/markers/<slug>/marker_<id>.png.
"""
from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path

import cv2

from isaac.vgu_sim.paths import aruco_dict_name, marker_assets_dir


def _dict_const(dictionary_name: str) -> int:
    const = getattr(cv2.aruco, dictionary_name, None)
    if not isinstance(const, int):
        raise ValueError(f"Unsupported ArUco dictionary name: {dictionary_name!r}")
    return const


def generate_markers(
    dictionary_name: str,
    out_dir: Path,
    *,
    ids: Iterable[int] = range(1, 50),
    side_px: int = 512,
    quiet_px: int = 64,
) -> None:
    """Write deterministic marker PNGs (black marker + white quiet zone)."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(_dict_const(dictionary_name))
    out_dir.mkdir(parents=True, exist_ok=True)
    for marker_id in ids:
        marker = cv2.aruco.generateImageMarker(aruco_dict, marker_id, side_px)
        bordered = cv2.copyMakeBorder(
            marker, quiet_px, quiet_px, quiet_px, quiet_px,
            cv2.BORDER_CONSTANT, value=255,  # white quiet zone for detection
        )
        cv2.imwrite(str(out_dir / f"marker_{marker_id}.png"), bordered)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ArUco marker PNGs")
    parser.add_argument("--side-px", type=int, default=512)
    args = parser.parse_args()
    name = aruco_dict_name()
    out = marker_assets_dir(name)
    generate_markers(name, out, side_px=args.side_px)
    print(f"Wrote markers for {name} to {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_aruco_generation.py -v`
Expected: PASS (all generation + path tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_aruco_markers.py tests/unit/test_aruco_generation.py
git commit -m "feat: ArUco marker PNG generator reading dictionary from aruco.yaml"
```

---

## Task 3: Generate and commit the marker assets

**Files:**
- Create (generated): `isaac/assets/markers/aruco_4x4_50/marker_1.png` … `marker_49.png`

- [ ] **Step 1: Run the generator**

Run:
```bash
python -m scripts.generate_aruco_markers
```
Expected: prints `Wrote markers for DICT_4X4_50 to isaac/assets/markers/aruco_4x4_50`

- [ ] **Step 2: Verify 49 PNGs exist**

Run: `ls isaac/assets/markers/aruco_4x4_50/*.png | wc -l`
Expected: `49`

- [ ] **Step 3: Commit the assets**

```bash
git rm --cached isaac/assets/markers/aruco_4x4_50/.gitkeep 2>/dev/null || true
git add isaac/assets/markers/aruco_4x4_50/marker_*.png
git commit -m "feat: commit generated DICT_4X4_50 marker textures"
```

---

## Task 4: Parity round-trip test (generation ↔ M1)

**Files:**
- Test: `tests/unit/test_aruco_parity.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_aruco_parity.py`:
```python
"""Every generated marker PNG must decode to its own id under M1's configured dict."""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import pytest

from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path

# M1 perception is a ROS2 package; add its src to the path to import detection.
_PERCEPTION_SRC = Path("ros2_ws/src/swarm_perception")
if str(_PERCEPTION_SRC) not in sys.path:
    sys.path.insert(0, str(_PERCEPTION_SRC))

from swarm_perception.detection import detect_aruco_markers  # noqa: E402


@pytest.mark.parametrize("marker_id", range(1, 50))
def test_generated_marker_decodes_to_its_id(marker_id: int):
    name = aruco_dict_name()
    png = marker_png_path(name, marker_id)
    img = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
    assert img is not None, f"missing {png} (run scripts.generate_aruco_markers)"
    ids, _ = detect_aruco_markers(img, dictionary_name=name)
    assert ids == [marker_id]
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/unit/test_aruco_parity.py -q`
Expected: PASS (49 parametrized cases). If any FAIL, generation and M1 disagree — stop and investigate the dictionary mapping before continuing.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_aruco_parity.py
git commit -m "test: round-trip parity of generated markers against M1 detector"
```

---

## Task 5: Align M1 `aruco.yaml` marker size

**Files:**
- Modify: `ros2_ws/src/swarm_perception/config/aruco.yaml`
- Test: `tests/unit/test_aruco_generation.py` (config section)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_aruco_generation.py`:
```python
import yaml
from pathlib import Path


def test_aruco_config_size_matches_sim_marker():
    cfg = yaml.safe_load(Path("ros2_ws/src/swarm_perception/config/aruco.yaml").read_text())
    assert cfg["aruco"]["marker_size_m"] == 0.12
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_aruco_generation.py::test_aruco_config_size_matches_sim_marker -v`
Expected: FAIL — `assert 0.08 == 0.12`

- [ ] **Step 3: Edit the config**

In `ros2_ws/src/swarm_perception/config/aruco.yaml`, change:
```yaml
  marker_size_m: 0.08
```
to:
```yaml
  marker_size_m: 0.12
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_aruco_generation.py::test_aruco_config_size_matches_sim_marker -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ros2_ws/src/swarm_perception/config/aruco.yaml tests/unit/test_aruco_generation.py
git commit -m "fix: align M1 aruco marker_size_m to 0.12 (sim physical size)"
```

---

## Task 6: Robot-asset prerequisites (expanded URDF + vendored meshes + raised marker frame)

**Files:**
- Modify: `isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.urdf`
- Create (vendored): `isaac/assets/robots/turtlebot3_burger/meshes/burger_base.stl`, `left_tire.stl`, `right_tire.stl`, `lds.stl`
- Test: `tests/simulation/test_robot_asset_prereqs.py`

> This task is partly manual asset work (acquire meshes, expand xacro). The test makes the result verifiable offline. The STLs come from the upstream `turtlebot3_description` package (ROBOTIS, Apache-2.0): `meshes/bases/burger_base.stl`, `meshes/wheels/left_tire.stl`, `meshes/wheels/right_tire.stl`, `meshes/sensors/lds.stl`.

- [ ] **Step 1: Write the failing test**

Create `tests/simulation/test_robot_asset_prereqs.py`:
```python
from pathlib import Path

import pytest

URDF = Path("isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.urdf")
MESH_DIR = Path("isaac/assets/robots/turtlebot3_burger/meshes")
MESHES = ["burger_base.stl", "left_tire.stl", "right_tire.stl", "lds.stl"]


def test_urdf_has_no_xacro_or_namespace_tokens():
    text = URDF.read_text()
    assert "${" not in text
    assert "xacro" not in text


def test_urdf_references_only_local_meshes():
    text = URDF.read_text()
    assert "package://" not in text


@pytest.mark.parametrize("name", MESHES)
def test_vendored_mesh_exists_and_nonempty(name: str):
    p = MESH_DIR / name
    assert p.exists() and p.stat().st_size > 0


def test_marker_joint_raised_above_lidar():
    text = URDF.read_text()
    # aruco_marker_joint origin z must clear the lidar (base_scan at z=0.172).
    assert 'name="aruco_marker_joint"' in text
    assert 'xyz="0 0 0.21"' in text


def test_marker_link_has_no_box_visual():
    # The marker is now an authored USD quad; the URDF link is a frame only.
    text = URDF.read_text()
    marker_block = text.split('name="aruco_marker_link"', 1)[1]
    assert "<box" not in marker_block.split("</link>", 1)[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/simulation/test_robot_asset_prereqs.py -v`
Expected: FAIL (xacro tokens present, `package://` present, meshes missing, joint at 0.10, box present).

- [ ] **Step 3: Expand the URDF**

Edit `turtlebot3_burger.urdf`:
- Delete the xacro plumbing: the `xmlns:xacro="http://ros.org/wiki/xacro"` attribute on `<robot>`, the `<xacro:arg name="namespace" .../>` line, and the `<xacro:property name="namespace" .../>` line.
- Replace every `${namespace}` with empty string (e.g. `${namespace}base_link` → `base_link`) throughout link/joint names and parent/child refs.

(Equivalent one-shot if the `xacro` CLI is installed: rename to `turtlebot3_burger.urdf.xacro`, run `xacro turtlebot3_burger.urdf.xacro -o turtlebot3_burger.urdf`, then delete the `.xacro`. Hand-editing is fine — the file is small.)

- [ ] **Step 4: Vendor the meshes and rewrite paths**

Place the four STLs under `isaac/assets/robots/turtlebot3_burger/meshes/` (filenames exactly as in `MESHES`). In the URDF, rewrite each `<mesh filename="package://turtlebot3_description/meshes/.../<file>.stl" .../>` to a local relative path, e.g.:
```xml
<mesh filename="meshes/burger_base.stl" scale="0.001 0.001 0.001"/>
<mesh filename="meshes/left_tire.stl" scale="0.001 0.001 0.001"/>
<mesh filename="meshes/right_tire.stl" scale="0.001 0.001 0.001"/>
<mesh filename="meshes/lds.stl" scale="0.001 0.001 0.001"/>
```

- [ ] **Step 5: Raise the marker joint and drop the box visual**

In the `aruco_marker_joint`, change the origin from `xyz="0 0 0.10"` to `xyz="0 0 0.21"` (clears the lidar at z=0.172). In `aruco_marker_link`, delete the `<visual>…<box .../>…</visual>` block, leaving the link as a frame only:
```xml
<link name="aruco_marker_link"/>
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/simulation/test_robot_asset_prereqs.py -v`
Expected: PASS (all cases)

- [ ] **Step 7: Commit**

```bash
git add isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.urdf \
        isaac/assets/robots/turtlebot3_burger/meshes/*.stl \
        tests/simulation/test_robot_asset_prereqs.py
git commit -m "fix: expand turtlebot3 URDF, vendor meshes, raise marker frame above lidar"
```

---

## Task 7: `author_aruco_marker` — USD quad + emissive material

**Files:**
- Create: `isaac/vgu_sim/marker_asset.py`
- Test: `tests/unit/test_marker_asset.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_marker_asset.py`:
```python
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
    assert max(p[0] for p in pts) == half and min(p[0] for p in pts) == -half
    xf = UsdGeom.Xformable(mesh).GetLocalTransformation()
    assert xf.ExtractTranslation()[2] == MARKER_HEIGHT_M


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_marker_asset.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'isaac.vgu_sim.marker_asset'`

- [ ] **Step 3: Implement the authoring helper**

Create `isaac/vgu_sim/marker_asset.py`:
```python
from __future__ import annotations

from pxr import Gf, Sdf, UsdGeom, UsdShade

# Physical marker size (m). Converged with aruco.yaml and the parity test.
MARKER_SIZE_M = 0.12
# Marker frame height (m). Mirrors aruco_marker_joint in turtlebot3_burger.urdf;
# above the lidar (base_scan at z=0.172) so a nadir camera is not occluded.
MARKER_HEIGHT_M = 0.21


def author_aruco_marker(stage, robot_prim_path: str, texture_path: str):
    """Author a UV-mapped marker quad + emissive material under a robot prim.

    Args:
        stage: USD stage being authored.
        robot_prim_path: e.g. "/World/Robots/robot_1".
        texture_path: marker PNG path, relative to the scenario stage.

    Returns:
        The authored `UsdGeom.Mesh` quad.
    """
    marker_path = f"{robot_prim_path}/aruco_marker"
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

    UsdGeom.Xformable(mesh).AddTranslateOp().Set(Gf.Vec3d(0, 0, MARKER_HEIGHT_M))

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_marker_asset.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/marker_asset.py tests/unit/test_marker_asset.py
git commit -m "feat: author_aruco_marker USD quad with emissive per-id material"
```

---

## Task 8: Wire the marker into `_author_robot`

**Files:**
- Modify: `isaac/vgu_sim/scenario_builder.py`
- Test: `tests/unit/test_marker_asset.py` (integration section)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_marker_asset.py`:
```python
from pathlib import Path


def test_author_robot_adds_marker_with_id_texture(tmp_path):
    from pxr import Usd, UsdGeom, UsdShade

    from isaac.vgu_sim.config import Goal2D, Pose2D, RobotScenarioConfig
    from isaac.vgu_sim.scenario_builder import _author_robot

    stage = Usd.Stage.CreateNew(str(tmp_path / "scene.usda"))
    robot_asset = tmp_path / "turtlebot3_burger.usda"
    robot_asset.write_text("#usda 1.0\n")  # minimal referenceable stub

    cfg = RobotScenarioConfig(
        robot_id="robot_2",
        marker_id=2,
        spawn=Pose2D(x=0.0, y=0.0, theta=0.0),
        goal=Goal2D(x=1.0, y=1.0),
        initial_task="idle",
    )
    _author_robot(stage, cfg, robot_asset, tmp_path)

    shader = UsdShade.Shader.Get(
        stage, "/World/Robots/robot_2/aruco_marker/Material/Texture"
    )
    assert shader
    assert shader.GetInput("file").Get().path.endswith("marker_2.png")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_marker_asset.py::test_author_robot_adds_marker_with_id_texture -v`
Expected: FAIL — no `aruco_marker/Material/Texture` prim authored.

- [ ] **Step 3: Wire it in**

In `isaac/vgu_sim/scenario_builder.py`, add the import near the top:
```python
from isaac.vgu_sim.marker_asset import author_aruco_marker
from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path
```
At the end of `_author_robot(...)` (after the goal/ROSGraphs prims are defined), append:
```python
    # Per-robot ArUco marker keyed by marker_id. The imported robot USD is shared,
    # so the marker is authored per-robot here. The dictionary is resolved from the
    # single source of truth (aruco.yaml) — never hardcoded — so it can't desync
    # from generation. Texture path is relative to the scenario stage so the .usda
    # is relocatable.
    marker_png = marker_png_path(aruco_dict_name(), robot_cfg.marker_id)
    rel_marker = _relative_path(scenario_dir, marker_png)
    author_aruco_marker(stage, prim_path, str(rel_marker))
```

> Note: `_author_robot`'s parameters are `(stage, robot_cfg, robot_asset_path, scenario_dir)` and it already computes `prim_path = f"/World/Robots/{robot_cfg.robot_id}"`. Reuse both. `Path` is already imported in `scenario_builder.py`; if not, add `from pathlib import Path`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_marker_asset.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/scenario_builder.py tests/unit/test_marker_asset.py
git commit -m "feat: author per-robot ArUco marker in _author_robot"
```

---

## Task 9: Validate the marker in `validation.py`

**Files:**
- Modify: `isaac/vgu_sim/validation.py`
- Test: `tests/unit/test_marker_asset.py` (validation section)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_marker_asset.py`:
```python
def test_validate_marker_passes_for_authored_quad():
    from pxr import Usd, UsdGeom

    from isaac.vgu_sim.marker_asset import author_aruco_marker
    from isaac.vgu_sim.validation import validate_robot_marker

    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World/Robots/robot_1")
    author_aruco_marker(stage, "/World/Robots/robot_1", "markers/aruco_4x4_50/marker_1.png")
    validate_robot_marker(stage, "/World/Robots/robot_1")  # must not raise


def test_validate_marker_fails_when_missing():
    import pytest
    from pxr import Usd, UsdGeom

    from isaac.vgu_sim.validation import ValidationError, validate_robot_marker

    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/World/Robots/robot_1")
    with pytest.raises(ValidationError, match="aruco_marker"):
        validate_robot_marker(stage, "/World/Robots/robot_1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_marker_asset.py -k validate_marker -v`
Expected: FAIL — `cannot import name 'validate_robot_marker'`

- [ ] **Step 3: Implement the validator**

In `isaac/vgu_sim/validation.py` (reuse the existing `ValidationError`), add:
```python
def validate_robot_marker(stage, robot_prim_path: str) -> None:
    """Assert a robot has a decodable ArUco marker quad authored on it.

    Checks the authored marker quad child (not the URDF frame): the mesh exists,
    carries an `st` primvar, and binds a material with a texture file input.

    Raises:
        ValidationError: If the marker quad, its `st` primvar, or its bound
            texture is missing.
    """
    from pxr import UsdGeom, UsdShade

    marker_path = f"{robot_prim_path}/aruco_marker"
    mesh = UsdGeom.Mesh.Get(stage, marker_path)
    if not mesh:
        raise ValidationError(f"Missing aruco_marker quad at {marker_path}")
    if not UsdGeom.PrimvarsAPI(mesh).GetPrimvar("st"):
        raise ValidationError(f"aruco_marker at {marker_path} has no 'st' primvar")
    material = UsdShade.MaterialBindingAPI(mesh).GetDirectBinding().GetMaterial()
    if not material:
        raise ValidationError(f"aruco_marker at {marker_path} has no bound material")
    tex = UsdShade.Shader.Get(stage, f"{marker_path}/Material/Texture")
    if not tex or not tex.GetInput("file") or not tex.GetInput("file").Get():
        raise ValidationError(f"aruco_marker at {marker_path} has no texture file")
```

> If `ValidationError` is not already importable at module top in `validation.py`, it is defined there (used by `validate_scenario_stage`); reuse the existing class, do not redefine it.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_marker_asset.py -k validate_marker -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Call it from `validate_scenario_stage`**

In `validation.py`, inside `validate_scenario_stage`'s per-robot loop (where it already iterates `/World/Robots/<id>` prims), add a call:
```python
        validate_robot_marker(stage, robot_prim.GetPath().pathString)
```
(Match the existing loop variable name; if the function validates robots by config rather than by prim iteration, call `validate_robot_marker(stage, f"/World/Robots/{robot.robot_id}")` for each configured robot.)

- [ ] **Step 6: Run the full isaac/unit suite**

Run: `pytest tests/unit/test_marker_asset.py tests/unit/test_aruco_generation.py tests/unit/test_aruco_parity.py tests/simulation/test_robot_asset_prereqs.py -q`
Expected: PASS (all)

- [ ] **Step 7: Commit**

```bash
git add isaac/vgu_sim/validation.py tests/unit/test_marker_asset.py
git commit -m "feat: validate authored ArUco marker quad per robot"
```

---

## Task 10: On-Isaac acceptance (manual, on the Windows/Isaac 6.0 box)

**Files:** none (runtime verification)

> These steps require Isaac Sim 6.0 + ROS 2 Jazzy and cannot run in the dev venv. They are the real proof the markers render and are detected. Record results in the run manifest / a short note.

- [ ] **Step 1: Re-import the robot asset**

Run (PowerShell, on the Isaac box):
```powershell
%ISAAC_SIM_ROOT%\python.bat -m isaac.scripts.import_turtlebot3 --urdf isaac\assets\robots\turtlebot3_burger\turtlebot3_burger.urdf --force
```
Expected: writes `turtlebot3_burger.usda` with **no missing-mesh warnings** and no `${...}` errors.

- [ ] **Step 2: Build a scenario and confirm the marker prim**

Build a scenario (e.g. `head_on_deadlock`) via the existing scenario build path, then confirm each robot has `/World/Robots/<id>/aruco_marker` with a bound material and that `validate_scenario_stage` passes.

- [ ] **Step 3: Run and check M1 sees the markers**

Launch the sim + perception (`perception.launch.py use_camera_node:=false`) on a shared `ROS_DOMAIN_ID`, then:
```bash
ros2 topic echo /perception/scene_state --once
```
Expected: `robots` is **non-empty** with the expected `robot_id`s — the real end-to-end proof. If empty, the marker renders too small/occluded at the default camera; the deferred lever is a camera retune (out of scope here).

- [ ] **Step 4: Record the result**

Note pass/fail and any per-robot id mismatches (the known M1-`robot_id` vs Isaac-`robot_id` naming gap is tracked separately).

---

## Notes for the executor

- **Run order matters:** Task 3 (generate assets) must run before Task 4 (parity) and before any Isaac build that references the PNGs.
- **`marker_id` ↔ `robot_id` naming** is a known, separately-tracked gap (M1 keys robots by decoded marker id; Isaac names robots independently). Do not "fix" it inside this plan.
- **No camera retune** here; detectability at 0.12 m is an accepted, empirically-validated risk (Task 10 Step 3).
- If `scenario_builder._author_robot`'s actual signature differs from `(stage, robot_cfg, robot_asset_path, scenario_dir)`, adapt the Task 8 call site to the real parameter names — the behavior (author a per-robot marker keyed by `robot_cfg.marker_id`) is what matters.

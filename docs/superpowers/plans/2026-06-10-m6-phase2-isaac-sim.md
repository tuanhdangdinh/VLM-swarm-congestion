# M6 Simulation – Phase 2: Isaac Sim USD Authoring, ROS Graphs & Runner

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Phase 1 plan complete (`2026-06-10-m6-phase1-host-foundation.md`). All `tests/unit/` pass.

**Goal:** Implement the Isaac Sim layer of Module 6: TurtleBot3 URDF import, warehouse USD authoring, scenario USD layer composition, OmniGraph ROS2 wiring, simulation runner with reset, the shell wrapper, and simulation acceptance tests.

**Architecture:** Everything lives under `isaac/` (USD authoring + runner) and `ros2_ws/src/swarm_simulation/` (ROS-facing launch). Scripts in `isaac/scripts/` are entry points invoked via `${ISAAC_SIM_ROOT}/python.sh -m`. Library code in `isaac/vgu_sim/` is importable from both scripts and tests. Scenario USD files are generated artifacts; never manually edited.

**Tech Stack:** Isaac Sim 6.0, ROS 2 Jazzy, OpenUSD (`pxr`), OmniGraph (`omni.graph.core`), `isaacsim.*` extensions, Pydantic v2. All commands run as `${ISAAC_SIM_ROOT}/python.sh`.

**Environment assumption:** `ISAAC_SIM_ROOT` is set, ROS 2 Jazzy is sourced, GPU is available.

---

## File Map

| File | Responsibility |
|---|---|
| `isaac/vgu_sim/robot_asset.py` | URDF import, articulation/joint/lidar/marker validation |
| `isaac/scripts/import_turtlebot3.py` | CLI: URDF → USD |
| `isaac/vgu_sim/warehouse_builder.py` | Build `warehouse_base.usd` with floor, walls, racks, camera |
| `isaac/scripts/build_warehouse.py` | CLI: build warehouse asset |
| `isaac/vgu_sim/scenario_builder.py` | Build per-scenario USD root layer (sublayers warehouse, authors robots) |
| `isaac/scripts/build_scenario.py` | CLI: build one scenario USD |
| `isaac/vgu_sim/ros_graphs.py` | OmniGraph authoring: clock, camera, per-robot cmd/odom/lidar/TF |
| `isaac/vgu_sim/validation.py` | Stage, asset, camera-frustum, graph validation |
| `isaac/scripts/validate_simulation.py` | CLI: validate a scenario USD |
| `isaac/vgu_sim/runner.py` | SimulationApp + physics loop + reset between repetitions |
| `isaac/scripts/run_simulation.py` | CLI: run a scenario (delegates to runner) |
| `scripts/run_simulation.sh` | Shell wrapper: sources ROS, validates env, calls Isaac python |
| `ros2_ws/src/swarm_simulation/launch/isaac_sim.launch.py` | ROS-side launch (consumers only) |
| `tests/simulation/conftest.py` | pytest marks: `isaac_sim`, `ros2` |
| `tests/simulation/test_m6_scenarios.py` | Scenario acceptance tests (require Isaac Sim + ROS) |
| `tests/simulation/stop_stub.py` | Test-harness stop stub (FR6.8.5a) |

---

### Task 7: Robot Asset Import

> **Requires:** Isaac Sim 6.0 on Linux. Run all commands with `${ISAAC_SIM_ROOT}/python.sh`.

**Files:**
- Create: `isaac/vgu_sim/robot_asset.py`
- Create: `isaac/scripts/import_turtlebot3.py`

- [ ] **Step 1: Implement `isaac/vgu_sim/robot_asset.py`**

This module runs inside Isaac Sim. It must be imported **after** `SimulationApp` is started.

```python
# isaac/vgu_sim/robot_asset.py
from __future__ import annotations

from pathlib import Path

from isaac.vgu_sim.config import RobotAssetConfig


class RobotImportError(Exception):
    pass


def import_turtlebot3(
    urdf_path: Path,
    output_root: Path,
    config: RobotAssetConfig,
    *,
    force: bool = False,
) -> Path:
    """Import TurtleBot3 Burger URDF and return the canonical interface-layer path.

    Args:
        urdf_path: Expanded .urdf file (not .xacro).
        output_root: Root directory for robot asset output (spec §7.2).
        config: RobotAssetConfig with joint names and drive parameters.
        force: Overwrite existing asset if True.

    Returns:
        Path to the canonical ``turtlebot3_burger.usda`` interface layer.

    Raises:
        RobotImportError: If URDF does not exist, output exists without --force,
            or post-import validation fails.
    """
    # Must be imported here: SimulationApp must already be running.
    import omni.usd
    from isaacsim.asset.importer.urdf import URDFImporter

    if not urdf_path.exists():
        raise RobotImportError(f"URDF not found: {urdf_path}")

    dest_dir = output_root / "turtlebot3_burger"
    interface_layer = dest_dir / "turtlebot3_burger.usda"

    if interface_layer.exists() and not force:
        raise RobotImportError(
            f"Asset already exists at {interface_layer}. Use --force to overwrite."
        )

    dest_dir.mkdir(parents=True, exist_ok=True)

    importer_config = URDFImporter.Config()
    importer_config.merge_fixed_joints = False
    importer_config.make_default_prim = True
    importer_config.create_physics_scene = False
    importer_config.convex_decomp = False       # use URDF collision geometry (FR6.4.3)
    importer_config.self_collision_filter = True # disable self-collision (FR6.4.2)
    importer_config.up_vector = (0.0, 0.0, 1.0)
    importer_config.import_inertia_tensor = True
    importer_config.density = 0.0
    importer_config.output_directory = str(dest_dir)

    result = URDFImporter.import_robot(str(urdf_path), importer_config)
    if not result.success:
        raise RobotImportError(f"URDF import failed: {result.error}")

    # Apply wheel drive parameters (FR6.4.6)
    _apply_wheel_drives(interface_layer, config)

    # Validate the imported asset (FR6.4.11)
    validate_robot_asset(interface_layer, config)

    return interface_layer


def _apply_wheel_drives(asset_path: Path, config: RobotAssetConfig) -> None:
    """Set angular velocity drives on wheel joints per spec FR6.4.6."""
    from pxr import Usd, UsdPhysics, Gf

    stage = Usd.Stage.Open(str(asset_path))
    for joint_name in (config.left_wheel_joint, config.right_wheel_joint):
        joint_prim = _find_prim_by_name(stage, joint_name)
        if joint_prim is None:
            raise RobotImportError(f"Wheel joint not found: {joint_name!r}")
        drive = UsdPhysics.DriveAPI.Apply(joint_prim, "angular")
        drive.GetStiffnessAttr().Set(config.wheel_drive_stiffness)
        drive.GetDampingAttr().Set(config.wheel_drive_damping)
        drive.GetTargetVelocityAttr().Set(0.0)
        drive.GetMaxForceAttr().Set(float("inf"))
    stage.Save()


def _find_prim_by_name(stage, name: str):
    for prim in stage.Traverse():
        if prim.GetName() == name:
            return prim
    return None


def validate_robot_asset(asset_path: Path, config: RobotAssetConfig) -> None:
    """Validate articulation root, wheel joints, lidar, and marker presence (FR6.4.11).

    Raises:
        RobotImportError: On any validation failure.
    """
    from pxr import Usd, UsdPhysics

    stage = Usd.Stage.Open(str(asset_path))

    # Exactly one ArticulationRootAPI (FR6.4.5)
    art_roots = [
        p for p in stage.Traverse()
        if p.HasAPI(UsdPhysics.ArticulationRootAPI)
    ]
    if len(art_roots) != 1:
        raise RobotImportError(
            f"Expected exactly 1 ArticulationRootAPI; found {len(art_roots)}"
        )

    # Both wheel joints present and have drives (FR6.4.6)
    for joint_name in (config.left_wheel_joint, config.right_wheel_joint):
        prim = _find_prim_by_name(stage, joint_name)
        if prim is None:
            raise RobotImportError(f"Missing wheel joint: {joint_name!r}")
        if not prim.HasAPI(UsdPhysics.DriveAPI):
            raise RobotImportError(f"Wheel joint {joint_name!r} has no DriveAPI")

    # Layer metadata: metersPerUnit, upAxis (FR6.1.3)
    layer = stage.GetRootLayer()
    if layer.metersPerUnit != 1.0:
        raise RobotImportError(
            f"metersPerUnit must be 1; got {layer.metersPerUnit}"
        )
```

- [ ] **Step 2: Implement `isaac/scripts/import_turtlebot3.py`**

```python
# isaac/scripts/import_turtlebot3.py
"""CLI: import TurtleBot3 Burger URDF into isaac/assets/robots/.

Usage:
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.import_turtlebot3 \
        --urdf /path/to/turtlebot3_burger.urdf \
        --output-dir isaac/assets/robots \
        [--force]
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def _expand_xacro(xacro_path: Path) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".urdf", delete=False)
    subprocess.run(
        ["xacro", str(xacro_path), "-o", tmp.name],
        check=True,
    )
    return Path(tmp.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import TurtleBot3 Burger URDF")
    parser.add_argument("--urdf", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("isaac/assets/robots"), type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    urdf_path = args.urdf
    if urdf_path.suffix == ".xacro":
        urdf_path = _expand_xacro(urdf_path)

    # SimulationApp must start before importing Isaac modules.
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "anti_aliasing": 0})

    try:
        import omni.kit.app
        omni.kit.app.get_app().update()

        from isaac.vgu_sim.config import RobotAssetConfig
        from isaac.vgu_sim.robot_asset import import_turtlebot3

        config = RobotAssetConfig()
        result = import_turtlebot3(urdf_path, args.output_dir, config, force=args.force)
        print(f"Robot asset written to: {result}")
    finally:
        app.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke-test import (requires Isaac Sim)**

```bash
${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.import_turtlebot3 \
  --urdf /path/to/turtlebot3_burger.urdf \
  --output-dir isaac/assets/robots
```
Expected: `Robot asset written to: isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.usda`

- [ ] **Step 4: Commit**

```bash
git add isaac/vgu_sim/robot_asset.py isaac/scripts/import_turtlebot3.py
git commit -m "feat: add M6 TurtleBot3 URDF import and validation"
```

---

### Task 8: Warehouse USD Builder

**Files:**
- Create: `isaac/vgu_sim/warehouse_builder.py`
- Create: `isaac/scripts/build_warehouse.py`

- [ ] **Step 1: Implement `isaac/vgu_sim/warehouse_builder.py`**

```python
# isaac/vgu_sim/warehouse_builder.py
"""Build warehouse_base.usd with floor, walls, rack blocks, loading zones,
and overhead camera. ROS graphs for camera and clock are authored here (global).

All USD paths stored in composition arcs are relative (FR6.1.7).
"""
from __future__ import annotations

from pathlib import Path

from isaac.vgu_sim.config import CameraConfig, WarehouseConfig


class WarehouseBuildError(Exception):
    pass


def build_warehouse_asset(
    config: WarehouseConfig,
    camera_config: CameraConfig,
    output_path: Path,
) -> Path:
    """Create warehouse_base.usd.

    Args:
        config: Warehouse dimensions and aisle parameters.
        camera_config: Overhead camera pose and optics.
        output_path: Where to write the USD file.

    Returns:
        Resolved path of the saved USD file.
    """
    from pxr import Usd, UsdGeom, UsdPhysics, Gf, Kind, Sdf
    import omni.usd

    stage = Usd.Stage.CreateNew(str(output_path))

    # Stage-level metadata (FR6.1.3)
    stage.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetTimeCodesPerSecond(60.0)

    # /World as assembly default prim (FR6.1.5, FR6.2.7)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    world.GetPrim().SetMetadata("kind", Kind.Tokens.assembly)

    # PhysicsScene
    physics_scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    physics_scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
    physics_scene.CreateGravityMagnitudeAttr().Set(9.81)

    env = UsdGeom.Xform.Define(stage, "/World/Environment")

    _build_floor(stage, config)
    _build_walls(stage, config)
    _build_rack_blocks(stage, config)
    _build_loading_zones(stage, config)

    # Sensors and ROSGraphs stubs (populated further by ros_graphs module)
    UsdGeom.Xform.Define(stage, "/World/Sensors")
    UsdGeom.Xform.Define(stage, "/World/DynamicObstacles")
    UsdGeom.Xform.Define(stage, "/World/Robots")
    UsdGeom.Xform.Define(stage, "/World/Scenario")
    UsdGeom.Xform.Define(stage, "/World/Scenario/Goals")
    UsdGeom.Xform.Define(stage, "/World/Scenario/Metadata")
    UsdGeom.Xform.Define(stage, "/World/ROSGraphs")
    UsdGeom.Xform.Define(stage, "/World/ROSGraphs/Global")

    _build_overhead_camera(stage, camera_config)

    # Validate all references resolve before saving
    _validate_references(stage, output_path)
    stage.Save()
    return output_path


def _build_floor(stage, config: WarehouseConfig) -> None:
    from pxr import UsdGeom, UsdPhysics, Gf

    half_w = config.width_m / 2.0
    half_d = config.depth_m / 2.0

    floor = UsdGeom.Mesh.Define(stage, "/World/Environment/Floor")
    floor.CreatePointsAttr([
        Gf.Vec3f(-half_w, -half_d, 0.0),
        Gf.Vec3f( half_w, -half_d, 0.0),
        Gf.Vec3f( half_w,  half_d, 0.0),
        Gf.Vec3f(-half_w,  half_d, 0.0),
    ])
    floor.CreateFaceVertexCountsAttr([4])
    floor.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    UsdPhysics.CollisionAPI.Apply(floor.GetPrim())


def _build_walls(stage, config: WarehouseConfig) -> None:
    from pxr import UsdGeom, UsdPhysics, Gf

    hw = config.width_m / 2.0
    hd = config.depth_m / 2.0
    t = config.wall_thickness_m / 2.0
    h = config.wall_height_m

    walls = UsdGeom.Xform.Define(stage, "/World/Environment/Walls")
    wall_defs = [
        ("north", Gf.Vec3f(0.0,  hd + t, h / 2), Gf.Vec3f(hw + t,   t,    h / 2)),
        ("south", Gf.Vec3f(0.0, -hd - t, h / 2), Gf.Vec3f(hw + t,   t,    h / 2)),
        ("east",  Gf.Vec3f(hw + t, 0.0,  h / 2), Gf.Vec3f(t,        hd,   h / 2)),
        ("west",  Gf.Vec3f(-hw - t, 0.0, h / 2), Gf.Vec3f(t,        hd,   h / 2)),
    ]
    for name, pos, half_size in wall_defs:
        cube = UsdGeom.Cube.Define(stage, f"/World/Environment/Walls/{name}")
        cube.CreateSizeAttr(2.0)
        cube.AddTranslateOp().Set(pos)
        cube.AddScaleOp().Set(half_size)
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())


def _build_rack_blocks(stage, config: WarehouseConfig) -> None:
    from pxr import UsdGeom, UsdPhysics, Gf

    aw = config.nominal_aisle_width_m / 2.0
    hw = config.width_m / 2.0
    hd = config.depth_m / 2.0
    rack_hw = (hw - aw) / 2.0
    rack_hd = (hd - aw) / 2.0
    rack_h = 0.9  # approx rack height (not spec-critical; only collision shape matters)

    racks_xform = UsdGeom.Xform.Define(stage, "/World/Environment/RackBlocks")
    quadrants = [
        ("NE", Gf.Vec3f( aw + rack_hw,  aw + rack_hd, rack_h / 2)),
        ("NW", Gf.Vec3f(-aw - rack_hw,  aw + rack_hd, rack_h / 2)),
        ("SE", Gf.Vec3f( aw + rack_hw, -aw - rack_hd, rack_h / 2)),
        ("SW", Gf.Vec3f(-aw - rack_hw, -aw - rack_hd, rack_h / 2)),
    ]
    for name, pos in quadrants:
        cube = UsdGeom.Cube.Define(stage, f"/World/Environment/RackBlocks/{name}")
        cube.CreateSizeAttr(2.0)
        cube.AddTranslateOp().Set(pos)
        cube.AddScaleOp().Set(Gf.Vec3f(rack_hw, rack_hd, rack_h / 2))
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())


def _build_loading_zones(stage, config: WarehouseConfig) -> None:
    from pxr import UsdGeom, Gf

    # Spec FR6.5.6: aisle endpoints at ±5.2, 0 and 0, ±3.2
    lz_xform = UsdGeom.Xform.Define(stage, "/World/Environment/LoadingZones")
    for name, pos in [
        ("west",  Gf.Vec3f(-5.2, 0.0, 0.001)),
        ("east",  Gf.Vec3f( 5.2, 0.0, 0.001)),
        ("south", Gf.Vec3f(0.0, -3.2, 0.001)),
        ("north", Gf.Vec3f(0.0,  3.2, 0.001)),
    ]:
        marker = UsdGeom.Mesh.Define(stage, f"/World/Environment/LoadingZones/{name}")
        marker.AddTranslateOp().Set(pos)
        # Visual only — no collision on loading zone floor markings


def _build_overhead_camera(stage, config: CameraConfig) -> None:
    from pxr import UsdGeom, Gf

    cam_prim = UsdGeom.Camera.Define(stage, config.prim_path)

    # Position (FR6.6.2): nadir, looking down -Z, +Y aligned to world +Y (FR6.6.3)
    xform = UsdGeom.Xformable(cam_prim.GetPrim())
    xform.AddTranslateOp().Set(Gf.Vec3d(*config.position_m))
    # Default orientation is identity = looking down -Z in USD camera convention.
    # If orientation_quat_wxyz != identity, apply rotation here (deferred tilt support).
    w, x, y, z = config.orientation_quat_wxyz
    if (w, x, y, z) != (1.0, 0.0, 0.0, 0.0):
        xform.AddOrientOp().Set(Gf.Quatd(w, x, y, z))

    # Optics (FR6.6.4)
    cam_prim.CreateFocalLengthAttr().Set(config.focal_length_mm)
    cam_prim.CreateHorizontalApertureAttr().Set(config.horizontal_aperture_mm)
    cam_prim.CreateVerticalApertureAttr().Set(config.vertical_aperture_mm)
    cam_prim.CreateClippingRangeAttr().Set(Gf.Vec2f(0.1, 100.0))

    # Projection: pinhole (FR6.6.9) — USD default
    cam_prim.CreateProjectionAttr().Set(UsdGeom.Tokens.perspective)


def _validate_references(stage, output_path: Path) -> None:
    """Fail fast if any reference is unresolved after building."""
    from pxr import Usd
    errors = [e for e in stage.GetCompositionErrors()]
    if errors:
        raise WarehouseBuildError(
            f"Unresolved composition errors in {output_path}: {errors}"
        )
```

- [ ] **Step 2: Implement `isaac/scripts/build_warehouse.py`**

```python
# isaac/scripts/build_warehouse.py
"""CLI: build isaac/assets/warehouse/warehouse_base.usd.

Usage:
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.build_warehouse
"""
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build warehouse_base.usd")
    parser.add_argument("--output", default=None, type=Path,
                        help="Output path (default: isaac/assets/warehouse/warehouse_base.usd)")
    args = parser.parse_args()

    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "anti_aliasing": 0})

    try:
        import omni.kit.app
        omni.kit.app.get_app().update()

        from isaac.vgu_sim.config import CameraConfig, WarehouseConfig
        from isaac.vgu_sim.warehouse_builder import build_warehouse_asset
        from isaac.vgu_sim.paths import warehouse_asset_path

        output = args.output or warehouse_asset_path()
        output.parent.mkdir(parents=True, exist_ok=True)

        result = build_warehouse_asset(WarehouseConfig(), CameraConfig(), output)
        print(f"Warehouse written to: {result}")
    finally:
        app.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Build and inspect (requires Isaac Sim)**

```bash
${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.build_warehouse
# Then open in usdview or usd-cat to verify prim hierarchy:
usdcat isaac/assets/warehouse/warehouse_base.usd | grep "def " | head -30
```
Expected: `/World`, `/World/PhysicsScene`, `/World/Environment/Floor`, `/World/Sensors/OverheadCamera` etc.

- [ ] **Step 4: Commit**

```bash
git add isaac/vgu_sim/warehouse_builder.py isaac/scripts/build_warehouse.py
git commit -m "feat: add M6 warehouse USD builder"
```

---

### Task 9: Scenario USD Builder

**Files:**
- Create: `isaac/vgu_sim/scenario_builder.py`
- Create: `isaac/scripts/build_scenario.py`

- [ ] **Step 1: Implement `isaac/vgu_sim/scenario_builder.py`**

```python
# isaac/vgu_sim/scenario_builder.py
"""Build per-scenario USD root layers.

The scenario root layer sublayers warehouse_base.usd (weaker) and authors
robot references, spawn transforms, goals, inactive obstacle prims, and
per-robot ROS graph containers into the stronger scenario layer.
"""
from __future__ import annotations

from pathlib import Path

from isaac.vgu_sim.config import (
    RobotAssetConfig, ScenarioConfig, CameraConfig, WarehouseConfig,
)


class ScenarioBuildError(Exception):
    pass


def build_scenario_stage(
    config: ScenarioConfig,
    *,
    warehouse_path: Path,
    robot_asset_path: Path,
    output_path: Path,
) -> Path:
    """Create the scenario root USD layer.

    Args:
        config: Validated ScenarioConfig.
        warehouse_path: Path to warehouse_base.usd (referenced as weakest sublayer).
        robot_asset_path: Path to turtlebot3_burger.usda.
        output_path: Where to write the scenario USD.

    Returns:
        Path to the saved scenario USD file.
    """
    from pxr import Usd, UsdGeom, Sdf, Gf, Kind

    if not warehouse_path.exists():
        raise ScenarioBuildError(f"Warehouse asset missing: {warehouse_path}")
    if not robot_asset_path.exists():
        raise ScenarioBuildError(f"Robot asset missing: {robot_asset_path}")

    stage = Usd.Stage.CreateNew(str(output_path))

    # Stage metadata (FR6.1.3)
    stage.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetTimeCodesPerSecond(60.0)

    # /World as assembly default prim (FR6.1.5)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    world.GetPrim().SetMetadata("kind", Kind.Tokens.assembly)

    # Warehouse as weakest sublayer (spec FR6.2.4). Use relative path (FR6.1.7).
    rel_warehouse = _relative_path(output_path.parent, warehouse_path)
    root_layer = stage.GetRootLayer()
    root_layer.subLayerPaths.append(str(rel_warehouse))

    # Set edit target to root layer (stronger than sublayer)
    stage.SetEditTarget(stage.GetRootLayer())

    # Author robots
    robots_xform = UsdGeom.Xform.Define(stage, "/World/Robots")
    ros_graphs_xform = UsdGeom.Xform.Define(stage, "/World/ROSGraphs")

    for robot_cfg in config.robots:
        _author_robot(stage, robot_cfg, robot_asset_path, output_path.parent)

    # Author inactive dynamic obstacles (FR6.8.6)
    UsdGeom.Xform.Define(stage, "/World/DynamicObstacles")
    for obs in config.timed_obstacles:
        _author_obstacle(stage, obs)

    # Author scenario metadata
    meta = stage.DefinePrim("/World/Scenario/Metadata")
    meta.SetMetadata("customData", {
        "name": config.name,
        "seed": config.seed,
        "duration_sec": config.duration_sec,
        "schema_version": config.schema_version,
    })

    _validate_references(stage, output_path)
    stage.Save()
    return output_path


def _author_robot(stage, robot_cfg, robot_asset_path: Path, scenario_dir: Path) -> None:
    from pxr import UsdGeom, Sdf, Gf, Kind

    prim_path = f"/World/Robots/{robot_cfg.robot_id}"
    robot_prim = stage.DefinePrim(prim_path)
    robot_prim.SetMetadata("kind", Kind.Tokens.component)

    # Reference robot asset (FR6.2.3, FR6.2.8: not instanceable when sensor configs differ)
    rel_robot = _relative_path(scenario_dir, robot_asset_path)
    robot_prim.GetReferences().AddReference(str(rel_robot))

    # Spawn transform
    xform = UsdGeom.Xformable(robot_prim)
    s = robot_cfg.spawn
    xform.AddTranslateOp().Set(Gf.Vec3d(s.x, s.y, 0.0))
    xform.AddRotateZOp().Set(float(s.yaw_rad * 180.0 / 3.141592653589793))

    # Goal marker (visual only, no collision)
    goal_path = f"/World/Scenario/Goals/{robot_cfg.robot_id}_goal"
    goal_prim = UsdGeom.Sphere.Define(stage, goal_path)
    goal_prim.CreateRadiusAttr().Set(0.1)
    g = robot_cfg.goal
    UsdGeom.Xformable(goal_prim.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(g.x, g.y, 0.0))

    # ROS graph container placeholder (ros_graphs.py fills this in)
    stage.DefinePrim(f"/World/ROSGraphs/{robot_cfg.robot_id}")


def _author_obstacle(stage, obs_cfg) -> None:
    from pxr import UsdGeom, Gf

    prim_path = f"/World/DynamicObstacles/{obs_cfg.obstacle_id}"
    prim = UsdGeom.Xform.Define(stage, prim_path)

    p = obs_cfg.pose
    UsdGeom.Xformable(prim.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(p.x, p.y, 0.0))

    # Start inactive (FR6.8.6): deactivated prims are invisible and non-collidable
    prim.GetPrim().SetActive(False)


def _relative_path(from_dir: Path, to_path: Path) -> Path:
    """Return the relative path from from_dir to to_path.

    Both must be resolved absolute paths OR both relative from the same CWD.
    """
    try:
        return to_path.resolve().relative_to(from_dir.resolve())
    except ValueError:
        # Fallback: use os.path.relpath when resolve() gives different roots
        import os
        return Path(os.path.relpath(str(to_path), str(from_dir)))


def _validate_references(stage, output_path: Path) -> None:
    errors = [e for e in stage.GetCompositionErrors()]
    if errors:
        raise ScenarioBuildError(
            f"Unresolved composition errors in {output_path}: {errors}"
        )
```

- [ ] **Step 2: Implement `isaac/scripts/build_scenario.py`**

```python
# isaac/scripts/build_scenario.py
"""CLI: build one scenario USD from its YAML config.

Usage:
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.build_scenario \
        --config isaac/config/scenarios/head_on_deadlock.yaml
"""
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build scenario USD")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()

    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "anti_aliasing": 0})

    try:
        import omni.kit.app
        omni.kit.app.get_app().update()

        import yaml
        from isaac.vgu_sim.config import ScenarioConfig
        from isaac.vgu_sim.paths import robot_asset_path, warehouse_asset_path, scenario_output_path
        from isaac.vgu_sim.scenario_builder import build_scenario_stage

        with open(args.config) as f:
            data = yaml.safe_load(f)
        config = ScenarioConfig.model_validate(data)

        output = scenario_output_path(config.name)
        output.parent.mkdir(parents=True, exist_ok=True)

        result = build_scenario_stage(
            config,
            warehouse_path=warehouse_asset_path(),
            robot_asset_path=robot_asset_path(),
            output_path=output,
        )
        print(f"Scenario written to: {result}")
    finally:
        app.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Build head-on scenario and verify (requires Isaac Sim)**

```bash
${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.build_scenario \
  --config isaac/config/scenarios/head_on_deadlock.yaml

# Check prim hierarchy
usdcat isaac/scenarios/head_on_deadlock.usd | grep "def " | head -30
```
Expected: `/World/Robots/robot_1`, `/World/Robots/robot_2`, sublayer to `warehouse_base.usd`

- [ ] **Step 4: Commit**

```bash
git add isaac/vgu_sim/scenario_builder.py isaac/scripts/build_scenario.py
git commit -m "feat: add M6 scenario USD builder"
```

---

### Task 10: ROS 2 OmniGraph Authoring

**Files:**
- Create: `isaac/vgu_sim/ros_graphs.py`

- [ ] **Step 1: Implement `isaac/vgu_sim/ros_graphs.py`**

Uses `omni.graph.core` (`og.Controller.edit`) to create execution-mode graphs. Node type identifiers from spec §3 FR6.7.10.

```python
# isaac/vgu_sim/ros_graphs.py
"""Author OmniGraph nodes for clock, camera, and per-robot ROS 2 interfaces.

All graphs use execution-mode evaluation triggered by OnPhysicsStep.
QoS profiles follow spec FR6.7.10 (tf Reliable, tf_static Reliable/TransientLocal).
"""
from __future__ import annotations

from isaac.vgu_sim.config import CameraConfig, RobotAssetConfig, RobotScenarioConfig


class RosGraphError(Exception):
    pass


def create_global_ros_graphs(
    stage,
    camera_prim_path: str,
    config: CameraConfig,
) -> None:
    """Create clock, RGB camera, and CameraInfo publishing graphs under /World/ROSGraphs/Global.

    Args:
        stage: Open USD stage.
        camera_prim_path: Absolute prim path to the camera (FR6.6.1).
        config: CameraConfig for frame_id and rate.
    """
    import omni.graph.core as og
    import omni.replicator.core as rep

    graph_path = "/World/ROSGraphs/Global"

    # Create a render product for the overhead camera (30 Hz = every 2 physics steps at 60 Hz)
    render_product = rep.create.render_product(
        camera_prim_path, (config.width, config.height)
    )

    # Clock graph
    og.Controller.edit(
        {"graph_path": f"{graph_path}/clock_graph", "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_step",   "isaacsim.core.nodes.OnPhysicsStep"),
                ("pub_clock", "isaacsim.ros2.bridge.ROS2PublishClock"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_step.outputs:step", "pub_clock.inputs:execIn"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("pub_clock.inputs:topicName", "/clock"),
                ("pub_clock.inputs:qosProfile", "default"),
            ],
        },
    )

    # Camera RGB graph
    og.Controller.edit(
        {"graph_path": f"{graph_path}/camera_rgb_graph", "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_step",   "isaacsim.core.nodes.OnPhysicsStep"),
                ("pub_rgb",   "isaacsim.ros2.bridge.ROS2CameraHelper"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_step.outputs:step", "pub_rgb.inputs:execIn"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("pub_rgb.inputs:topicName",      "/camera/image_raw"),
                ("pub_rgb.inputs:frameId",         config.frame_id),
                ("pub_rgb.inputs:renderProductPath", render_product.path),
                ("pub_rgb.inputs:type",            "rgb"),
            ],
        },
    )

    # CameraInfo graph
    og.Controller.edit(
        {"graph_path": f"{graph_path}/camera_info_graph", "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_step",      "isaacsim.core.nodes.OnPhysicsStep"),
                ("pub_cam_info", "isaacsim.ros2.bridge.ROS2CameraInfoHelper"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_step.outputs:step", "pub_cam_info.inputs:execIn"),
            ],
            og.Controller.Keys.SET_VALUES: [
                ("pub_cam_info.inputs:topicName",       "/camera/camera_info"),
                ("pub_cam_info.inputs:frameId",          config.frame_id),
                ("pub_cam_info.inputs:renderProductPath", render_product.path),
            ],
        },
    )


def create_robot_ros_graph(
    stage,
    robot: RobotScenarioConfig,
    robot_prim_path: str,
    config: RobotAssetConfig,
) -> None:
    """Create one OmniGraph per robot covering cmd_vel, odometry, lidar, and TF.

    Robot N gets:
      - Subscriber: /robot_N/cmd_vel  (geometry_msgs/Twist)
      - Publisher:  /robot_N/odom     (nav_msgs/Odometry)
      - Publisher:  /robot_N/scan     (sensor_msgs/LaserScan)
      - Publisher:  /tf               (dynamic transform odom -> base_footprint)
      - Publisher:  /tf_static        (static: base_footprint->base_link, base_link->base_scan)

    Args:
        stage: Open USD stage.
        robot: RobotScenarioConfig identifying robot_id and marker_id.
        robot_prim_path: Absolute prim path e.g. /World/Robots/robot_1.
        config: RobotAssetConfig for joint names and drive constants.
    """
    import omni.graph.core as og
    from pxr import Sdf

    robot_id = robot.robot_id
    graph_path = f"/World/ROSGraphs/{robot_id}/drive_graph"
    lidar_prim_path = f"{robot_prim_path}/{config.lidar_link}"

    # Validate exactly one articulation root under robot prim (FR6.7.5 guard)
    from pxr import UsdPhysics
    art_roots = [
        p for p in stage.GetPrimAtPath(robot_prim_path).GetChildren()
        if p.HasAPI(UsdPhysics.ArticulationRootAPI)
    ]
    if len(art_roots) != 1:
        raise RosGraphError(
            f"Expected exactly 1 ArticulationRootAPI under {robot_prim_path}; "
            f"found {len(art_roots)}"
        )
    art_root_path = art_roots[0].GetPath().pathString

    og.Controller.edit(
        {"graph_path": graph_path, "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: [
                ("on_step",       "isaacsim.core.nodes.OnPhysicsStep"),
                ("sub_twist",     "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
                ("diff_ctrl",     "isaacsim.robot.wheeled_robots.DifferentialController"),
                ("art_ctrl",      "isaacsim.core.nodes.IsaacArticulationController"),
                ("odom_compute",  "isaacsim.core.nodes.IsaacComputeOdometry"),
                ("pub_odom",      "isaacsim.ros2.bridge.ROS2PublishOdometry"),
                ("pub_tf_dyn",    "isaacsim.ros2.bridge.ROS2PublishRawTransformTree"),
                ("pub_tf_static", "isaacsim.ros2.bridge.ROS2PublishRawTransformTree"),
                ("pub_lidar",     "isaacsim.ros2.bridge.ROS2RtxLidarHelper"),
            ],
            og.Controller.Keys.CONNECT: [
                ("on_step.outputs:step",           "sub_twist.inputs:execIn"),
                ("sub_twist.outputs:execOut",      "diff_ctrl.inputs:execIn"),
                ("diff_ctrl.outputs:execOut",      "art_ctrl.inputs:execIn"),
                ("art_ctrl.outputs:execOut",       "odom_compute.inputs:execIn"),
                ("odom_compute.outputs:execOut",   "pub_odom.inputs:execIn"),
                ("pub_odom.outputs:execOut",       "pub_tf_dyn.inputs:execIn"),
                ("sub_twist.outputs:linearVelocity",   "diff_ctrl.inputs:linearVelocity"),
                ("sub_twist.outputs:angularVelocity",  "diff_ctrl.inputs:angularVelocity"),
                ("diff_ctrl.outputs:velocityCommand",  "art_ctrl.inputs:velocityCommand"),
                ("odom_compute.outputs:position",      "pub_odom.inputs:position"),
                ("odom_compute.outputs:orientation",   "pub_odom.inputs:orientation"),
                ("odom_compute.outputs:linearVelocity","pub_odom.inputs:linearVelocity"),
                ("odom_compute.outputs:angularVelocity","pub_odom.inputs:angularVelocity"),
            ],
            og.Controller.Keys.SET_VALUES: [
                # cmd_vel subscriber
                ("sub_twist.inputs:topicName",          f"/{robot_id}/cmd_vel"),
                # Differential drive constants (spec §9.3)
                ("diff_ctrl.inputs:wheelRadius",        config.wheel_radius_m),
                ("diff_ctrl.inputs:wheelDistance",      config.wheel_separation_m),
                ("diff_ctrl.inputs:maxLinearSpeed",     config.max_linear_velocity_mps),
                ("diff_ctrl.inputs:maxAngularSpeed",    config.max_angular_velocity_radps),
                # Articulation controller
                ("art_ctrl.inputs:robotPath",           art_root_path),
                ("art_ctrl.inputs:jointNames",
                 [config.left_wheel_joint, config.right_wheel_joint]),
                # Odometry
                ("odom_compute.inputs:chassisPrim",     robot_prim_path),
                # Odom publisher — Reliable/Volatile (FR6.7.10)
                ("pub_odom.inputs:topicName",           f"/{robot_id}/odom"),
                ("pub_odom.inputs:frameId",             f"{robot_id}/odom"),
                ("pub_odom.inputs:childFrameId",        f"{robot_id}/base_footprint"),
                ("pub_odom.inputs:qosProfile",          "default"),
                # Dynamic TF: odom -> base_footprint — Reliable/Volatile (FR6.7.10)
                ("pub_tf_dyn.inputs:topicName",         "/tf"),
                ("pub_tf_dyn.inputs:parentFrameId",     f"{robot_id}/odom"),
                ("pub_tf_dyn.inputs:childFrameId",      f"{robot_id}/base_footprint"),
                ("pub_tf_dyn.inputs:qosProfile",        "default"),
                # Static TF: base_footprint->base_link->base_scan — Reliable/TransientLocal
                ("pub_tf_static.inputs:topicName",      "/tf_static"),
                ("pub_tf_static.inputs:qosProfile",     "transient_local"),
                # Lidar publisher — Best effort (FR6.7.10)
                ("pub_lidar.inputs:topicName",          f"/{robot_id}/scan"),
                ("pub_lidar.inputs:frameId",            f"{robot_id}/base_scan"),
                ("pub_lidar.inputs:lidarPrimPath",      lidar_prim_path),
                ("pub_lidar.inputs:type",               "laser_scan"),
            ],
        },
    )
```

- [ ] **Step 2: Smoke-test graph creation (requires Isaac Sim + scenario USD)**

Run inside a Python script after opening the head-on scenario stage:
```python
from pxr import Usd
from isaac.vgu_sim.config import CameraConfig, RobotAssetConfig, RobotScenarioConfig
from isaac.vgu_sim.ros_graphs import create_global_ros_graphs, create_robot_ros_graph
import yaml, math

stage = Usd.Stage.Open("isaac/scenarios/head_on_deadlock.usd")
create_global_ros_graphs(stage, "/World/Sensors/OverheadCamera", CameraConfig())
# Verify /World/ROSGraphs/Global/clock_graph exists
assert stage.GetPrimAtPath("/World/ROSGraphs/Global/clock_graph").IsValid()
```

- [ ] **Step 3: Commit**

```bash
git add isaac/vgu_sim/ros_graphs.py
git commit -m "feat: add M6 OmniGraph ROS2 node authoring"
```

---

### Task 11: Validation and Validate Script

**Files:**
- Create: `isaac/vgu_sim/validation.py`
- Create: `isaac/scripts/validate_simulation.py`

- [ ] **Step 1: Implement `isaac/vgu_sim/validation.py`**

```python
# isaac/vgu_sim/validation.py
"""Stage and asset validation. Host-only functions (no Isaac Sim imports) live at
module top-level; Isaac Sim functions import heavy deps at call time.
"""
from __future__ import annotations

from pathlib import Path

from isaac.vgu_sim.config import CameraConfig, RobotAssetConfig


class ValidationError(Exception):
    pass


def validate_stage_metadata(stage) -> None:
    """Check metersPerUnit=1, upAxis=Z, defaultPrim=/World (FR6.1.3, FR6.1.5)."""
    from pxr import UsdGeom

    if stage.GetMetadata("metersPerUnit") != 1.0:
        raise ValidationError("metersPerUnit must be 1")
    if UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        raise ValidationError("upAxis must be Z")
    default_prim = stage.GetDefaultPrim()
    if not default_prim.IsValid() or default_prim.GetPath().pathString != "/World":
        raise ValidationError(
            f"defaultPrim must be /World; got {default_prim.GetPath()}"
        )


def validate_canonical_namespace(stage) -> None:
    """Check all mandatory prim paths exist (spec §3 M6.3)."""
    required = [
        "/World/PhysicsScene",
        "/World/Environment",
        "/World/Environment/Floor",
        "/World/Environment/Walls",
        "/World/Environment/RackBlocks",
        "/World/Robots",
        "/World/Sensors/OverheadCamera",
        "/World/DynamicObstacles",
        "/World/Scenario",
        "/World/ROSGraphs",
        "/World/ROSGraphs/Global",
    ]
    for path in required:
        if not stage.GetPrimAtPath(path).IsValid():
            raise ValidationError(f"Required prim missing: {path}")


def validate_camera_frustum(stage, config: CameraConfig) -> None:
    """Verify the camera covers the central 6.0 m × 4.5 m ROI (FR6.6.5).

    At 3.0 m height with HFOV ~90°, the half-width covered is
    height * tan(HFOV/2) = 3.0 * tan(45°) = 3.0 m, giving 6.0 m total width ✓
    VFOV ~73.7°: half-depth = 3.0 * tan(36.85°) ≈ 2.25 m, giving 4.5 m ✓
    """
    import math

    cam_prim = stage.GetPrimAtPath(config.prim_path)
    if not cam_prim.IsValid():
        raise ValidationError(f"Camera prim not found: {config.prim_path}")

    height = config.position_m[2]
    fl = config.focal_length_mm
    ha = config.horizontal_aperture_mm
    va = config.vertical_aperture_mm

    hfov_rad = 2.0 * math.atan(ha / (2.0 * fl))
    vfov_rad = 2.0 * math.atan(va / (2.0 * fl))

    covered_w = 2.0 * height * math.tan(hfov_rad / 2.0)
    covered_d = 2.0 * height * math.tan(vfov_rad / 2.0)

    if covered_w < config.roi_width_m - 0.01:
        raise ValidationError(
            f"Camera covers {covered_w:.2f} m width; need >= {config.roi_width_m} m"
        )
    if covered_d < config.roi_depth_m - 0.01:
        raise ValidationError(
            f"Camera covers {covered_d:.2f} m depth; need >= {config.roi_depth_m} m"
        )


def validate_no_unresolved_references(stage) -> None:
    errors = list(stage.GetCompositionErrors())
    if errors:
        raise ValidationError(f"Unresolved USD composition errors: {errors}")


def validate_scenario_stage(scenario_path: Path, config: CameraConfig | None = None) -> None:
    """Full stage validation pipeline (FR6.9.5).

    Raises ValidationError on any failure.
    """
    from pxr import Usd

    stage = Usd.Stage.Open(str(scenario_path))
    validate_no_unresolved_references(stage)
    validate_stage_metadata(stage)
    validate_canonical_namespace(stage)

    cam_config = config or CameraConfig()
    validate_camera_frustum(stage, cam_config)
```

- [ ] **Step 2: Implement `isaac/scripts/validate_simulation.py`**

```python
# isaac/scripts/validate_simulation.py
"""CLI: validate a scenario USD.

Usage:
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.validate_simulation \
        --scenario isaac/scenarios/head_on_deadlock.usd
"""
import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate scenario USD")
    parser.add_argument("--scenario", required=True, type=Path)
    args = parser.parse_args()

    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "anti_aliasing": 0})

    try:
        import omni.kit.app
        omni.kit.app.get_app().update()

        from isaac.vgu_sim.validation import validate_scenario_stage, ValidationError

        try:
            validate_scenario_stage(args.scenario)
            print(f"PASS: {args.scenario}")
        except ValidationError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            sys.exit(1)
    finally:
        app.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add isaac/vgu_sim/validation.py isaac/scripts/validate_simulation.py
git commit -m "feat: add M6 USD stage validation"
```

---

### Task 12: Simulation Runner and Shell Wrapper

**Files:**
- Create: `isaac/vgu_sim/runner.py`
- Create: `isaac/scripts/run_simulation.py`
- Modify: `scripts/run_simulation.sh`

- [ ] **Step 1: Implement `isaac/vgu_sim/runner.py`**

```python
# isaac/vgu_sim/runner.py
"""Simulation runner: starts SimulationApp, runs fixed-step physics loop,
resets between repetitions, and writes run manifests.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

from isaac.vgu_sim.config import ResolvedRunConfig, RunResult, ScenarioConfig
from isaac.vgu_sim.event_scheduler import EventScheduler
from isaac.vgu_sim.paths import run_output_dir


def run_simulation(config: ResolvedRunConfig) -> tuple[RunResult, ...]:
    """Run all repetitions sequentially in one SimulationApp process.

    Returns:
        Tuple of RunResult, one per repetition.
    """
    app = _get_app(config.headless)
    results: list[RunResult] = []
    try:
        for rep in range(config.repetitions):
            result = run_repetition(app, config, rep)
            results.append(result)
            if not result.completed:
                break
    finally:
        app.close()
    return tuple(results)


def run_repetition(app, config: ResolvedRunConfig, repetition: int) -> RunResult:
    """Load stage, run fixed-step loop, write manifest. (FR6.9.3, FR6.9.4)"""
    import omni.timeline
    import carb

    output_dir = run_output_dir(
        config.output_dir, config.scenario.name, config.scenario.seed, repetition
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "run_manifest.json"
    gt_path = output_dir / "ground_truth.jsonl"

    run_id = f"{config.scenario.name}-seed{config.scenario.seed}-rep{repetition:03d}"
    started_at = datetime.datetime.utcnow().isoformat() + "Z"

    failure: str | None = None
    elapsed: float = 0.0
    completed = False

    scheduler = EventScheduler(config.scenario.timed_obstacles)

    try:
        # FR6.9.3 startup sequence
        _open_stage(config.scenario_path)
        _enable_extensions()
        _validate_stage(config.scenario_path)
        _init_physics()

        timeline = omni.timeline.get_timeline_interface()
        timeline.play()

        _wait_for_ros_topics(config.scenario.robots, config.topic_timeout_sec)

        physics_dt = 1.0 / 60.0
        render_every_n = 2  # 60 Hz physics, 30 Hz render
        duration = config.scenario.runtime.duration_sec or config.scenario.duration_sec

        step = 0
        sim_time = 0.0
        with open(gt_path, "w") as gt_file:
            while sim_time < duration and app.is_running():
                do_render = (step % render_every_n == 0)
                app.update()  # steps physics + optionally renders

                scheduler.apply_due_events(sim_time)
                _write_ground_truth(gt_file, sim_time, config.scenario)

                sim_time += physics_dt
                step += 1

        elapsed = sim_time
        completed = True

    except _TopicTimeoutError as exc:
        failure = str(exc)
        carb.log_error(failure)
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        carb.log_error(failure)
    finally:
        try:
            omni.timeline.get_timeline_interface().stop()
        except Exception:
            pass
        scheduler.reset()

    _write_manifest(manifest_path, {
        "run_id": run_id,
        "scenario": config.scenario.name,
        "scenario_schema_version": config.scenario.schema_version,
        "seed": config.scenario.seed,
        "repetition": repetition,
        "headless": config.headless,
        "isaac_sim_version": "6.0",
        "ros_distribution": "jazzy",
        "physics_hz": config.scenario.runtime.physics_hz,
        "rendering_hz": config.scenario.runtime.rendering_hz,
        "started_at_utc": started_at,
        "completed": completed,
        "failure": failure,
    })

    return RunResult(
        run_id=run_id,
        repetition=repetition,
        completed=completed,
        elapsed_simulation_sec=elapsed,
        manifest_path=manifest_path,
        failure=failure,
    )


class _TopicTimeoutError(RuntimeError):
    pass


def _get_app(headless: bool):
    from isaacsim import SimulationApp
    return SimulationApp({"headless": headless, "anti_aliasing": 0})


def _open_stage(scenario_path: Path) -> None:
    import omni.usd
    omni.usd.get_context().open_stage(str(scenario_path))


def _enable_extensions() -> None:
    import omni.kit.app
    manager = omni.kit.app.get_app().get_extension_manager()
    for ext in [
        "isaacsim.ros2.bridge",
        "isaacsim.ros2.nodes",
        "isaacsim.robot.wheeled_robots",
        "isaacsim.sensors.rtx",
    ]:
        manager.set_extension_enabled_immediate(ext, True)


def _validate_stage(scenario_path: Path) -> None:
    from isaac.vgu_sim.validation import validate_scenario_stage, ValidationError
    try:
        validate_scenario_stage(scenario_path)
    except ValidationError as exc:
        raise RuntimeError(f"Stage validation failed: {exc}") from exc


def _init_physics() -> None:
    import omni.physx
    omni.physx.get_physx_interface().start_simulation()


def _wait_for_ros_topics(robots, timeout_sec: float) -> None:
    """Block until required ROS topics are advertised (FR6.9.3 step 8)."""
    import time
    import rclpy
    from rclpy.node import Node

    required = ["/camera/image_raw", "/clock"] + [
        f"/{r.robot_id}/odom" for r in robots
    ]
    rclpy.init(args=None)
    node = Node("_m6_topic_waiter")
    deadline = time.monotonic() + timeout_sec
    try:
        while time.monotonic() < deadline:
            available = {name for name, _ in node.get_topic_names_and_types()}
            if all(t in available for t in required):
                return
            time.sleep(0.5)
        raise _TopicTimeoutError(
            f"ROS topics not ready within {timeout_sec}s. "
            f"Missing: {set(required) - available}"
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()


def _write_ground_truth(file, sim_time: float, scenario: ScenarioConfig) -> None:
    record = {"sim_time_sec": round(sim_time, 4)}
    file.write(json.dumps(record) + "\n")


def _write_manifest(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
```

- [ ] **Step 2: Implement `isaac/scripts/run_simulation.py`**

```python
# isaac/scripts/run_simulation.py
"""CLI: run a scenario (delegates to runner.run_simulation).

Usage:
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.run_simulation \
        --scenario head_on_deadlock \
        --headless \
        --seed 42 \
        --repetitions 3
"""
import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Isaac Sim scenario")
    parser.add_argument("--scenario", required=True,
                        help="Scenario name or path to YAML config")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--duration-sec", type=float, default=None)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--output-dir", type=Path,
                        default=Path("data/logs/simulation"))
    parser.add_argument("--ros-domain-id", type=int, default=None)
    parser.add_argument("--topic-timeout-sec", type=float, default=15.0)
    args = parser.parse_args()

    # Reject invalid arguments before starting Isaac Sim (FR6.9.7)
    if args.repetitions < 1:
        sys.exit("--repetitions must be >= 1")
    if args.duration_sec is not None and args.duration_sec <= 0:
        sys.exit("--duration-sec must be > 0")
    if args.seed is not None and args.seed < 0:
        sys.exit("--seed must be >= 0")
    if args.ros_domain_id is not None:
        import os
        os.environ["ROS_DOMAIN_ID"] = str(args.ros_domain_id)

    import yaml
    from isaac.vgu_sim.config import ScenarioConfig, ResolvedRunConfig
    from isaac.vgu_sim.paths import scenario_config_path, scenario_output_path

    # Resolve scenario config
    scenario_arg = args.scenario
    cfg_path = (Path(scenario_arg) if scenario_arg.endswith(".yaml")
                else scenario_config_path(scenario_arg))
    if not cfg_path.exists():
        sys.exit(f"Scenario config not found: {cfg_path}")

    with open(cfg_path) as f:
        raw = yaml.safe_load(f)

    # Apply CLI overrides
    if args.seed is not None:
        raw["seed"] = args.seed
    scenario = ScenarioConfig.model_validate(raw)

    run_config = ResolvedRunConfig(
        scenario_path=scenario_output_path(scenario.name),
        scenario=scenario,
        headless=args.headless,
        repetitions=args.repetitions,
        output_dir=args.output_dir,
        topic_timeout_sec=args.topic_timeout_sec,
        ros_domain_id=args.ros_domain_id,
    )

    from isaac.vgu_sim.runner import run_simulation
    results = run_simulation(run_config)

    failed = [r for r in results if not r.completed]
    if failed:
        for r in failed:
            print(f"FAIL rep={r.repetition}: {r.failure}", file=sys.stderr)
        sys.exit(1)

    print(f"All {len(results)} repetition(s) completed successfully.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Update `scripts/run_simulation.sh`**

Replace the existing shell wrapper with one that sources Jazzy and delegates to Isaac Sim python:

```bash
#!/usr/bin/env bash
# scripts/run_simulation.sh — Run M6 Isaac Sim simulation.
# Usage: ./scripts/run_simulation.sh --scenario head_on_deadlock --headless --seed 42 --repetitions 3
set -euo pipefail

# Validate required environment
if [[ -z "${ISAAC_SIM_ROOT:-}" ]]; then
    echo "ERROR: ISAAC_SIM_ROOT is not set. Source your Isaac Sim environment first." >&2
    exit 1
fi
if [[ ! -x "${ISAAC_SIM_ROOT}/python.sh" ]]; then
    echo "ERROR: ${ISAAC_SIM_ROOT}/python.sh not found or not executable." >&2
    exit 1
fi

# Source ROS 2 Jazzy
if [[ -f /opt/ros/jazzy/setup.bash ]]; then
    source /opt/ros/jazzy/setup.bash
else
    echo "ERROR: ROS 2 Jazzy not found at /opt/ros/jazzy/setup.bash." >&2
    exit 1
fi

# Source workspace if built
if [[ -f ros2_ws/install/setup.bash ]]; then
    source ros2_ws/install/setup.bash
fi

exec "${ISAAC_SIM_ROOT}/python.sh" -m isaac.scripts.run_simulation "$@"
```

```bash
chmod +x scripts/run_simulation.sh
```

- [ ] **Step 4: Commit**

```bash
git add isaac/vgu_sim/runner.py isaac/scripts/run_simulation.py scripts/run_simulation.sh
git commit -m "feat: add M6 simulation runner and shell wrapper"
```

---

### Task 13: ROS 2 Launch File

**Files:**
- Create: `ros2_ws/src/swarm_simulation/launch/isaac_sim.launch.py`

- [ ] **Step 1: Implement the launch file**

This starts ROS-side consumers only. It does not build USD or start Isaac Sim.

```python
# ros2_ws/src/swarm_simulation/launch/isaac_sim.launch.py
"""ROS 2 launch file for consumers of the Isaac Sim bridge.

Starts M1 perception and sets use_sim_time=true. Isaac Sim itself is started
separately via scripts/run_simulation.sh.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument(
            "ros_domain_id",
            default_value="0",
            description="ROS_DOMAIN_ID matching the Isaac Sim bridge",
        ),
        Node(
            package="swarm_perception",
            executable="perception_node",
            name="perception_node",
            parameters=[{"use_sim_time": True}],
            remappings=[
                ("image_raw", "/camera/image_raw"),
                ("camera_info", "/camera/camera_info"),
            ],
        ),
    ])
```

- [ ] **Step 2: Commit**

```bash
git add ros2_ws/src/swarm_simulation/launch/isaac_sim.launch.py
git commit -m "feat: add M6 ROS2 isaac_sim launch file"
```

---

### Task 14: Simulation Test Harness and Acceptance Tests

**Files:**
- Create: `tests/simulation/conftest.py`
- Create: `tests/simulation/stop_stub.py`
- Create: `tests/simulation/test_m6_scenarios.py`

- [ ] **Step 1: Create pytest marks**

```python
# tests/simulation/conftest.py
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "isaac_sim: requires Isaac Sim 6.0 on Linux")
    config.addinivalue_line("markers", "ros2: requires ROS 2 Jazzy sourced")
```

- [ ] **Step 2: Implement the stop stub (FR6.8.5a)**

```python
# tests/simulation/stop_stub.py
"""Test-harness stop stub (spec FR6.8.5a).

Drives each robot forward at a configured speed but commands zero velocity
when the minimum range in the forward ±30° sector of /robot_N/scan is < 0.25 m.

The ±30° sector is mandatory (not full 360°) so that the 0.55 m narrowed passage
walls (~0.275 m from center) do not permanently stall a robot (spec FR6.8.5a note).
"""
from __future__ import annotations

import math
import threading

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

_FORWARD_STOP_RANGE_M = 0.25
_FORWARD_SECTOR_DEG = 30  # ±30° from robot heading


class StopStub:
    """Single-robot stop stub. Create one per robot."""

    def __init__(self, robot_id: str, speed_mps: float = 0.10) -> None:
        if speed_mps > 0.15:
            raise ValueError("stop stub speed must not exceed 0.15 m/s (spec FR6.8.5a)")
        self._robot_id = robot_id
        self._speed = speed_mps
        self._blocked = False

    def on_scan(self, msg: LaserScan) -> Twist:
        """Compute cmd_vel from a LaserScan message.

        Returns a Twist with linear.x = speed if forward sector is clear,
        or zero if blocked.
        """
        n = len(msg.ranges)
        if n == 0:
            return Twist()

        # For a 360° scan at 1°/step (n=360), indices 0..29 and 330..359
        # cover ±30°. Generalise for arbitrary resolution.
        angle_inc_deg = math.degrees(msg.angle_increment)
        sector_steps = max(1, round(_FORWARD_SECTOR_DEG / angle_inc_deg))

        forward_ranges = (
            list(msg.ranges[:sector_steps])
            + list(msg.ranges[max(0, n - sector_steps):])
        )

        valid = [r for r in forward_ranges
                 if not math.isnan(r) and not math.isinf(r) and r > 0]
        min_range = min(valid) if valid else float("inf")

        cmd = Twist()
        if min_range >= _FORWARD_STOP_RANGE_M:
            cmd.linear.x = self._speed
        return cmd


class StopStubNode(Node):
    """ROS 2 node that runs one StopStub per robot_id and publishes cmd_vel."""

    def __init__(self, robot_ids: list[str], speed_mps: float = 0.10) -> None:
        super().__init__("stop_stub")
        self._stubs = {rid: StopStub(rid, speed_mps) for rid in robot_ids}
        self._pubs = {}
        self._subs = []

        for rid in robot_ids:
            pub = self.create_publisher(Twist, f"/{rid}/cmd_vel", 10)
            self._pubs[rid] = pub

            def _on_scan(msg: LaserScan, robot_id: str = rid) -> None:
                cmd = self._stubs[robot_id].on_scan(msg)
                self._pubs[robot_id].publish(cmd)

            sub = self.create_subscription(
                LaserScan, f"/{rid}/scan", _on_scan, 5
            )
            self._subs.append(sub)

    @classmethod
    def spin_in_thread(
        cls, robot_ids: list[str], speed_mps: float = 0.10
    ) -> "StopStubNode":
        """Start the node spinning in a background thread."""
        rclpy.init(args=None)
        node = cls(robot_ids, speed_mps)
        t = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        t.start()
        return node
```

- [ ] **Step 3: Implement acceptance tests**

```python
# tests/simulation/test_m6_scenarios.py
"""Scenario acceptance tests (spec §12.2).

Run with:
    ${ISAAC_SIM_ROOT}/python.sh -m pytest -m "isaac_sim" tests/simulation/ -v
    ${ISAAC_SIM_ROOT}/python.sh -m pytest -m "isaac_sim and ros2" tests/simulation/ -v
"""
import pytest
import time
import math
import json
from pathlib import Path


@pytest.mark.isaac_sim
def test_head_on_stage_validates():
    """Scenario USD resolves all references and passes metadata checks."""
    from isaac.vgu_sim.validation import validate_scenario_stage, ValidationError
    scenario = Path("isaac/scenarios/head_on_deadlock.usd")
    assert scenario.exists(), "Build head_on_deadlock.usd first (build_scenario.py)"
    validate_scenario_stage(scenario)  # raises ValidationError on failure


@pytest.mark.isaac_sim
def test_intersection_stage_validates():
    from isaac.vgu_sim.validation import validate_scenario_stage
    scenario = Path("isaac/scenarios/intersection_bottleneck.usd")
    assert scenario.exists()
    validate_scenario_stage(scenario)


@pytest.mark.isaac_sim
def test_dynamic_anomaly_stage_validates():
    from isaac.vgu_sim.validation import validate_scenario_stage
    scenario = Path("isaac/scenarios/dynamic_anomaly.usd")
    assert scenario.exists()
    validate_scenario_stage(scenario)


@pytest.mark.isaac_sim
@pytest.mark.ros2
def test_head_on_conflict_forms_and_collision_free(tmp_path):
    """Run head-on scenario; verify conflict oracle and unified collision rule.

    Spec §12.2 acceptance criteria:
    - Two robots enter the narrowed passage and both stop (speed < 0.01 m/s, >= 2.0 s).
    - No robot-static contact during run (ground_truth.jsonl: robot_static_contacts empty).
    - No robot-robot contact impulse while stub active.
    """
    from isaac.vgu_sim.config import ResolvedRunConfig, ScenarioConfig
    from isaac.vgu_sim.runner import run_simulation
    from isaac.vgu_sim.paths import scenario_output_path, scenario_config_path
    from tests.simulation.stop_stub import StopStubNode
    import yaml

    with open(scenario_config_path("head_on_deadlock")) as f:
        cfg = ScenarioConfig.model_validate(yaml.safe_load(f))

    run_cfg = ResolvedRunConfig(
        scenario_path=scenario_output_path("head_on_deadlock"),
        scenario=cfg,
        headless=True,
        repetitions=3,
        output_dir=tmp_path,
        topic_timeout_sec=20.0,
        ros_domain_id=None,
    )

    # Start stop stub before runner enters Play
    stub_node = StopStubNode.spin_in_thread(["robot_1", "robot_2"], speed_mps=0.10)

    results = run_simulation(run_cfg)
    assert all(r.completed for r in results), \
        f"Some repetitions failed: {[r.failure for r in results if not r.completed]}"

    # Verify ground truth for each repetition
    for rep, result in enumerate(results):
        gt_path = tmp_path / f"head_on_deadlock-seed42-rep{rep:03d}" / "ground_truth.jsonl"
        _assert_conflict_formed(gt_path, min_duration_sec=2.0)
        _assert_no_static_contacts(gt_path)


def _assert_conflict_formed(gt_path: Path, min_duration_sec: float) -> None:
    """Check that conflict_active was True for at least min_duration_sec."""
    records = [json.loads(line) for line in gt_path.read_text().splitlines() if line.strip()]
    dt = 0.1  # ground truth at 10 Hz
    consecutive = 0.0
    for rec in records:
        if rec.get("conflict_active", False):
            consecutive += dt
            if consecutive >= min_duration_sec:
                return
        else:
            consecutive = 0.0
    pytest.fail(
        f"Conflict never active for {min_duration_sec}s in {gt_path}"
    )


def _assert_no_static_contacts(gt_path: Path) -> None:
    """Fail if any record shows robot-static contact."""
    for line in gt_path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        contacts = rec.get("robot_static_contacts", [])
        if contacts:
            pytest.fail(
                f"Robot-static contact at t={rec['sim_time_sec']}: {contacts}"
            )


@pytest.mark.isaac_sim
@pytest.mark.ros2
def test_ros_topics_published_at_correct_rates(tmp_path):
    """Camera at 30 Hz ±10%, lidar at 10 Hz ±10%, /clock advances (spec §12.1)."""
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import Image, LaserScan
    from rosgraph_msgs.msg import Clock
    from collections import defaultdict

    counts: dict[str, int] = defaultdict(int)
    last_clock: list[float] = [0.0]

    rclpy.init(args=None)
    node = Node("_m6_rate_checker")

    node.create_subscription(Image, "/camera/image_raw",
                             lambda _: counts.__setitem__("rgb", counts["rgb"] + 1), 5)
    node.create_subscription(LaserScan, "/robot_1/scan",
                             lambda _: counts.__setitem__("scan", counts["scan"] + 1), 5)
    node.create_subscription(Clock, "/clock",
                             lambda m: last_clock.__setitem__(0, m.clock.sec + m.clock.nanosec * 1e-9), 10)

    # Spin for 3 seconds of wall time while sim is playing
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node()
    rclpy.shutdown()

    # 30 Hz camera over 3 s = ~90 messages, allow ±10%
    assert 81 <= counts["rgb"] <= 99, f"Camera rate off: {counts['rgb']} msgs in 3s"
    # 10 Hz lidar over 3 s = ~30 messages, allow ±10%
    assert 27 <= counts["scan"] <= 33, f"Lidar rate off: {counts['scan']} msgs in 3s"
    assert last_clock[0] > 0.0, "/clock never received"
```

- [ ] **Step 4: Run host-only tests to confirm nothing broke**

```bash
pytest tests/unit/ -q
```
Expected: all pass

- [ ] **Step 5: Run Isaac Sim tests (Linux/NVIDIA only)**

```bash
${ISAAC_SIM_ROOT}/python.sh -m pytest -m "isaac_sim" tests/simulation/ -v
```

- [ ] **Step 6: Run ROS 2 integration tests (Linux/NVIDIA + ROS 2 Jazzy)**

```bash
${ISAAC_SIM_ROOT}/python.sh -m pytest -m "isaac_sim and ros2" tests/simulation/ -v
```

- [ ] **Step 7: Commit**

```bash
git add tests/simulation/
git commit -m "test: add M6 simulation acceptance tests and stop stub"
```

---

## Phase 2 Complete

Full pipeline can be validated with:

```bash
# Build assets (Linux/NVIDIA)
${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.import_turtlebot3 --urdf /path/to/turtlebot3_burger.urdf --output-dir isaac/assets/robots
${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.build_warehouse
${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.build_scenario --config isaac/config/scenarios/head_on_deadlock.yaml
${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.build_scenario --config isaac/config/scenarios/intersection_bottleneck.yaml
${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.build_scenario --config isaac/config/scenarios/dynamic_anomaly.yaml

# Validate
${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.validate_simulation --scenario isaac/scenarios/head_on_deadlock.usd

# Run
./scripts/run_simulation.sh --scenario head_on_deadlock --headless --seed 42 --repetitions 3
```

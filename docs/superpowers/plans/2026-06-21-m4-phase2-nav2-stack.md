# M4 Phase 2 — Nav2 Stack & Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A robot autonomously navigates to an `(x, y, yaw)` goal via Nav2 — RTX lidar feeding a clean costmap, a static warehouse map, ground-truth localization, a namespaced per-robot Nav2 stack, and a real `Nav2Adapter` action-client wrapper — matching the acceptance test in `docs/specs/module4/phase2-nav2-stack.md` §8.

**Architecture:** Extend Phase 1's per-robot Isaac graph (`isaac/vgu_sim/ros_graphs.py`) with an RTX 2D lidar publishing `/<robot_id>/scan` (M6 FR6.4.9). Author a static occupancy-grid map from the known warehouse geometry (`WarehouseConfig` + `isaac/assets/obstacles/`). Use ground-truth `map → <robot_id>/odom` (a static identity transform — see Task 5's rationale) instead of AMCL. Bring up one namespaced Nav2 stack per robot under `/<robot_id>/...`, sharing `/tf`/`/tf_static`/`map`. Replace the placeholder `Nav2Adapter` with an action-client wrapper around `/<robot_id>/navigate_to_pose` and `/<robot_id>/follow_waypoints`.

**Tech Stack:** Isaac Sim 6.0 embedded Python, OmniGraph, `isaacsim.sensors.rtx`, ROS 2 Jazzy in the `ros:jazzy` container, `nav2_bringup`/`navigation2` (Jazzy container packages), `rclpy.action`, pytest.

**Correction (2026-06-22):** the earlier host-Humble retarget is superseded. The intended runtime for this GCP setup is **Isaac Sim on the Ubuntu 22.04 host using its bundled internal Jazzy bridge libraries** plus **ROS 2/Nav2 nodes inside the `ros:jazzy` Docker container**. Host `/opt/ros/humble` may exist and Isaac's `setup_ros_env.sh` auto-selects Humble on Ubuntu 22.04 when `ROS_DISTRO` is unset, but that is not the project runtime. Launch Isaac-side processes with `ROS_DISTRO=jazzy` when they must match container participants, and keep Nav2/M1/M5/M4 in the Jazzy container. The original apt blocker remains true only for **host apt** (`ros-jazzy-*` is unavailable on Jammy); it does not block the container path.

---

## Non-Goals (read before starting)

Phase 2's own acceptance test (spec §8) is **adapter-direct**: "a single `NavigateToPose` goal drives the robot to within tolerance of a free-space goal with obstacles present." It does not exercise the command bus or safety monitor. This plan does **not**:

- Implement `command_bus_node.py` or `safety_monitor_node.py` logic. Both remain scaffolds — they have their own unwritten specs (`command-bus.md`, `safety-monitor.md`, README §2) and are Phase 3 concerns.
- Make `Nav2Adapter` publish `CoordinationStatus`. Per the spec's boundary rule (§7): "The adapter surfaces raw action feedback only to the command bus, never to M5 directly." `Nav2Adapter` returns/yields goal-lifecycle data to its *caller*; translating that into `CoordinationStatus` on `/coordination/status` is the command bus's job, built later.
- Build the safety-monitor `cmd_vel` hard-stop override. README §7 flags this as an open question that "gates the Phase 3 safety handoff" — explicitly out of scope here.
- Wire M5/M3 into the command path. That is Phase 3 (`phase3-closed-loop.md`), gated on M3 grounding, which is unimplemented.

If you find yourself writing `/coordination/status` publishing logic or M5 wiring while working this plan, stop — that's scope creep into Phase 3.

---

## Reality Check

Like Phase 1, most of this plan is Isaac/ROS 2 systems work that can only be exercised on the **GCP Isaac Sim host**, not a local red-green pytest loop. Tasks are tagged:

- **[OFFLINE]** — pure Python/data authoring, real TDD, runs on any dev machine.
- **[HOST]** — requires the GCP Isaac Sim host; "red/green" means observing ROS 2 topic/action behavior.

Facts already resolved by Phase 1 — do not re-derive:

1. **`cmd_vel` is plain `Twist`, not `TwistStamped`.** `phase1-drive-chain.md` §2a(a): `ROS2SubscribeTwist` has no stamp input. Nav2's controller must run with `use_stamped_cmd_vel:=false`.
2. **CORRECTED 2026-06-22 (Task 5 falsified the original claim below — do not re-derive the correction, only the original wrong premise is struck through):** ~~`/<robot_id>/odom` is already ground truth... `map → <robot_id>/odom` is a static identity transform~~. Task 5 verified `/robot_1/odom` for real (300 in-process `Odometry` reads over 10s) and found it reads `≈ (0,0,0)` throughout while the chassis's true world pose (cross-checked independently) stays at the spawn pose `x=-0.6`. `IsaacComputeOdometry` is **spawn-relative** (zeroed at node-init), not absolute-world — it has no accumulating drift (confirmed, that part of the original claim holds), but its zero-reference is the spawn pose, not the map origin. **Corrected consequence: `map → <robot_id>/odom` must be a static transform equal to each robot's spawn pose** (`x, y, yaw` from the scenario config), not identity. See `docs/specs/module4/phase2-nav2-stack.md` §5's correction section for full evidence and a second, independent blocking finding (`/odom`/dynamic `/tf` stamped `0` continuously, which `tf2` drops — blocks the TF chain regardless of the `map→odom` value, root cause not yet found).
3. **Fabric/world-pose investigation is settled** (`docs/reports/2026-06-21-m6-fabric-sync-investigation.md`). Do not re-fight the Fabric-vs-pxr-USD sync issue; it only matters for the RTX *camera*, not for `/odom`/`/scan`, which read physics state directly.
4. **ArUco marker is under `aruco_marker_link`**, a physics child of `base_link` (`isaac/vgu_sim/marker_asset.py:29`). The RTX lidar exclusion in Task 2 targets this same subtree.

Two real unknowns this plan resolves with explicit go/no-go gates, in risk order:

- **Task 1:** does `ros-jazzy-navigation2`/`nav2-bringup` actually install and launch in the `ros:jazzy` container? (CLAUDE.md "optional heavyweight dependency" — confirm before building anything on top of it.)
- **Task 2:** can the ArUco marker plate be excluded from RTX lidar *raytracing* (not just PhysX collision)? This is the spec's and README's top-listed risk. If this fails, Phase 2 cannot proceed as specified and needs a design escalation (e.g., moving the marker below the scan plane is not an option — FR6.4.10 already requires it above the scan plane for camera visibility).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `isaac/vgu_sim/lidar.py` | RTX 2D lidar sensor authoring + ArUco-plate RTX-visibility exclusion helper | Create |
| `isaac/vgu_sim/ros_graphs.py` | Add `/<robot_id>/scan` publish subgraph to `create_robot_ros_graph` | Modify |
| `isaac/scripts/generate_warehouse_map.py` | Author `map.yaml` + `map.pgm` from `WarehouseConfig` + `isaac/assets/obstacles/` layout | Create |
| `ros2_ws/src/swarm_simulation/maps/warehouse_map.yaml`, `warehouse_map.pgm` | Static occupancy-grid map | Regenerate (replaces the stale Gazebo-era placeholder — current `warehouse_map.yaml` has no matching `.pgm` and predates the 12m×8m `WarehouseConfig` geometry) |
| `ros2_ws/src/swarm_simulation/launch/nav2_robot.launch.py` | Per-robot namespaced Nav2 bringup (`nav2_bringup`'s `bringup_launch.py` with `namespace`, `use_namespace:=true`) + shared `map_server` + static `map → <robot_id>/odom` identity TF | Create |
| `ros2_ws/src/swarm_simulation/config/nav2_params.yaml` | Templated Nav2 params (controller, planner, costmaps, BT navigator); `max_vel_x` capped at `safety.yaml`'s `0.2`, `use_stamped_cmd_vel: false` | Create |
| `ros2_ws/src/swarm_execution/swarm_execution/nav2_adapter.py` | `Nav2Adapter`: `send_goal`, `send_waypoints`, `cancel` action-client wrapper | Rewrite |
| `ros2_ws/src/swarm_execution/package.xml` | Add `nav2_msgs` dependency | Modify |
| `tests/unit/test_nav2_adapter.py` | Unit tests with a fake/mocked `rclpy.action.ActionClient` | Create |
| `tests/simulation/test_m4_phase2_nav2.py` | [HOST] documented-skip acceptance test (mirrors `test_m4_phase1_drive.py`'s pattern) | Create |
| `docs/specs/module4/phase2-nav2-stack.md` | Record verified facts from Tasks 1, 2, 5, 6 | Modify (append "Verified" subsections, same pattern as phase1 §2a) |
| `docs/specs/module4/README.md` | Flip Phase 2 status, update gap-analysis rows | Modify |

---

## Task 1 — [HOST] Dependency gate: confirm Nav2 installs in the container

**Why first:** `navigation2`/`nav2-bringup` is the one optional heavyweight dependency this entire phase rests on (CLAUDE.md "Dependencies" rule). If it doesn't install cleanly in the `ros:jazzy` container, every later task is blocked and the plan needs rework before any Isaac authoring happens.

**Files:**
- Modify: `docs/specs/module4/phase2-nav2-stack.md` (append "## 9. Verified host setup")

- [ ] **Step 1: On the GCP Isaac host, install the packages.**

```bash
sudo apt-get update
sudo apt-get install -y ros-jazzy-navigation2 ros-jazzy-nav2-bringup
```

- [ ] **Step 2: Verify the install with a smoke launch (no Isaac, no map yet).**

```bash
ros2 launch nav2_bringup bringup_launch.py --show-args
```

Expected: prints the launch arguments (`namespace`, `use_namespace`, `map`, `params_file`, `use_sim_time`, etc.) without error. This confirms the package and its launch files resolve.

- [ ] **Step 3: Record the verified package versions.**

```bash
apt list --installed 2>/dev/null | grep nav2
```

Append the output and the install commands to `phase2-nav2-stack.md` §9. If install fails, stop and report — do not substitute a different package set without updating this plan.

- [ ] **Step 4: Commit.**

```bash
git add docs/specs/module4/phase2-nav2-stack.md
git commit -m "docs: record verified Nav2 Jazzy package install in ROS container"
```

---

## Task 2 — [HOST] RTX lidar vs ArUco plate — go/no-go gate

**Why second:** This is the spec's and README's top-listed risk (README §7: "RTX lidar vs ArUco plate (highest risk)"). RTX lidar raytraces *rendered* geometry, not PhysX colliders, so disabling collision on the marker plate does nothing. If the plate (or its mount) can't be excluded from RTX visibility, every downstream costmap/Nav2 task is built on a phantom-obstacle scan and the whole phase needs a different approach. Resolve this **before** investing in map authoring or Nav2 bringup.

**Files:**
- Create: `isaac/vgu_sim/lidar.py`
- Test: `tests/unit/test_lidar.py` (offline USD-prim assertions only — RTX raytracing itself cannot be unit-tested without the renderer)

- [ ] **Step 1: Write the failing offline test for the authoring helper's prim setup.**

```python
from pxr import Usd, UsdGeom

from isaac.vgu_sim.lidar import author_rtx_lidar


def test_creates_lidar_prim_under_base_scan_link():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/Robot")
    UsdGeom.Xform.Define(stage, "/Robot/Geometry/base_footprint/base_link/base_scan")

    lidar_path = author_rtx_lidar(stage, "/Robot", lidar_link="base_scan")

    assert stage.GetPrimAtPath(lidar_path).IsValid()
    assert lidar_path.startswith(
        "/Robot/Geometry/base_footprint/base_link/base_scan"
    )


def test_missing_lidar_link_raises():
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/Robot")

    with pytest.raises(ValueError, match="base_scan"):
        author_rtx_lidar(stage, "/Robot", lidar_link="base_scan")
```

Add `import pytest` at the top; mark `pytest.importorskip("pxr")` if `pxr` is unavailable off-host.

- [ ] **Step 2: Run to verify failure.**

Run: `pytest tests/unit/test_lidar.py -v`
Expected: FAIL — `ModuleNotFoundError: isaac.vgu_sim.lidar`.

- [ ] **Step 3: Implement the prim-authoring half (no RTX-exclusion logic yet — that's Step 5, resolved from a host probe).**

```python
"""Author the RTX 2D lidar sensor prim under a robot's base_scan link.

M6 FR6.4.9: 360 deg, 1 deg resolution, 10 Hz, 0.12-3.5 m range, frame
robot_N/base_scan. The exclusion of the ArUco marker plate from RTX
raytracing (FR6.4.10) is applied separately — see exclude_from_rtx_lidar().
"""
from __future__ import annotations

from pxr import Usd, UsdGeom


def author_rtx_lidar(stage: Usd.Stage, robot_prim_path: str, lidar_link: str) -> str:
    """Create the RTX lidar prim under `<robot_prim_path>/.../<lidar_link>`.

    Args:
        stage: The USD stage holding the robot.
        robot_prim_path: Root prim of the robot subtree.
        lidar_link: Name of the link prim the lidar mounts to (e.g. "base_scan").

    Returns:
        The created lidar prim's path.

    Raises:
        ValueError: If `lidar_link` is not found under `robot_prim_path`.
    """
    link_prim = None
    for prim in Usd.PrimRange(stage.GetPrimAtPath(robot_prim_path)):
        if prim.GetName() == lidar_link:
            link_prim = prim
            break
    if link_prim is None:
        raise ValueError(f"lidar_link={lidar_link!r} not found under {robot_prim_path}")

    lidar_path = f"{link_prim.GetPath()}/rtx_lidar"
    UsdGeom.Xform.Define(stage, lidar_path)
    return lidar_path
```

- [ ] **Step 4: Run to verify pass.**

Run: `pytest tests/unit/test_lidar.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: [HOST] Wire the real RTX lidar sensor and probe for the ArUco-exclusion mechanism.** On the GCP host, in the Script Editor against a loaded `head_on_deadlock` scenario:

```python
import omni.kit.commands

# Create the RTX lidar sensor via the documented isaacsim.sensors.rtx command.
# Verify the exact command/config name against isaacsim.sensors.rtx docs for
# this Isaac Sim build before transcribing — this command signature is
# version-sensitive (CLAUDE.md External Library Verification).
result, lidar_prim = omni.kit.commands.execute(
    "IsaacSensorCreateRtxLidar",
    path="/World/Robots/robot_1/Geometry/base_footprint/base_link/base_scan/rtx_lidar",
    parent=None,
    config="OS1_REV7_128ch10hz1024res",  # placeholder — replace with a 2D/360deg config or custom params matching FR6.4.9
)
print(result, lidar_prim)
```

Then probe RTX-visibility exclusion options for the marker plate prim
(`/World/Robots/robot_1/Geometry/base_footprint/base_link/aruco_marker_link/aruco_marker`).
Try, in order, and record which one actually removes the plate from
`/robot_1/scan` ranges:

1. `UsdGeom.Imageable(plate_prim).MakeInvisible()` — likely excludes it from the RGB camera too (breaks M1); test but expect this to be the wrong tool.
2. RTX-specific render-visibility purpose/collection (check `isaacsim.sensors.rtx` docs for a lidar-only visibility flag, e.g. a `primvars:` tag or `RtxSensor` exclusion API — verify against the installed extension's API, do not guess the attribute name).
3. If no selective per-sensor exclusion exists: mount the lidar above the plate's RTX bounding geometry, or restrict the lidar's vertical FOV/range to a plane that physically misses the plate height (FR6.4.10's own suggested fallback: "the marker plate must sit above the scan plane").

- [ ] **Step 6: Verify the go/no-go.** Publish a held-still robot and dump `/robot_1/scan`:

```bash
ros2 topic echo /robot_1/scan --once
```

**Go:** ranges show only true environment obstacles (walls, other robots) at expected distances; no near-zero-range return at the marker's bearing from the lidar.
**No-go:** a phantom short-range obstacle appears at the plate's bearing. If no-go after trying all three options in Step 5, **stop and escalate** — do not proceed to Task 3 with a known-dirty scan; report which options were tried and their exact failure mode.

- [ ] **Step 7: Record the verified mechanism in the spec.**

```markdown
## 10. Verified RTX lidar / ArUco exclusion (Isaac Sim 6.0)

- RTX lidar sensor command: <exact command + config from Step 5>
- ArUco-plate exclusion mechanism: <exact API/attribute that worked>
- Verification: `/robot_1/scan --once` clean, no phantom return at plate bearing.
```

- [ ] **Step 8: Commit.**

```bash
git add isaac/vgu_sim/lidar.py tests/unit/test_lidar.py docs/specs/module4/phase2-nav2-stack.md
git commit -m "feat: author RTX lidar prim, verify ArUco-plate exclusion (FR6.4.9-10)"
```

---

## Task 3 — [OFFLINE] Author the static warehouse map

**Files:**
- Create: `isaac/scripts/generate_warehouse_map.py`
- Test: `tests/unit/test_generate_warehouse_map.py`
- Output (regenerated by running the script, not hand-edited): `ros2_ws/src/swarm_simulation/maps/warehouse_map.yaml`, `warehouse_map.pgm`

- [ ] **Step 1: Write the failing test for the occupancy-grid builder.**

```python
import numpy as np

from isaac.vgu_sim.config import WarehouseConfig
from isaac.scripts.generate_warehouse_map import build_occupancy_grid


def test_grid_marks_perimeter_walls_occupied():
    cfg = WarehouseConfig()  # 12.0 x 8.0 m, wall_thickness_m=0.1
    grid, resolution_m = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)

    assert resolution_m == 0.05
    height_px, width_px = grid.shape
    assert width_px == round(cfg.width_m / resolution_m)
    assert height_px == round(cfg.depth_m / resolution_m)
    # Perimeter row/col occupied (value 0 = occupied in PGM map_server convention).
    assert grid[0, :].max() == 0
    assert grid[:, 0].max() == 0


def test_grid_interior_is_free():
    cfg = WarehouseConfig()
    grid, _ = build_occupancy_grid(cfg, obstacles=[], resolution_m=0.05)
    height_px, width_px = grid.shape
    assert grid[height_px // 2, width_px // 2] == 255  # free
```

- [ ] **Step 2: Run to verify failure.**

Run: `pytest tests/unit/test_generate_warehouse_map.py -v`
Expected: FAIL — `ModuleNotFoundError: isaac.scripts.generate_warehouse_map`.

- [ ] **Step 3: Implement the grid builder and the CLI that writes `map.yaml`/`map.pgm`.**

```python
"""Author a static nav2_map_server occupancy grid from the known warehouse
geometry (WarehouseConfig) and obstacle layout (FR6.5.x).

Static-map shortcut (spec phase2-nav2-stack.md §4 Option A): the warehouse
layout is deterministic, so a one-shot script replaces slam_toolbox.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from isaac.vgu_sim.config import WarehouseConfig

OCCUPIED = 0
FREE = 255


def build_occupancy_grid(
    config: WarehouseConfig,
    obstacles: list[tuple[float, float, float, float]],
    resolution_m: float,
) -> tuple[np.ndarray, float]:
    """Build a free/occupied grid for the warehouse perimeter and obstacles.

    Args:
        config: Warehouse dimensions and wall thickness.
        obstacles: `(center_x, center_y, width_m, depth_m)` axis-aligned boxes
            in world coordinates, world origin at the warehouse center.
        resolution_m: Meters per pixel.

    Returns:
        `(grid, resolution_m)` where `grid` is `uint8`, row 0 = world `+y` edge,
        col 0 = world `-x` edge (map_server's image-to-world convention with
        a `[-width/2, -depth/2]` origin, set to match in `write_map`).
    """
    width_px = round(config.width_m / resolution_m)
    height_px = round(config.depth_m / resolution_m)
    grid = np.full((height_px, width_px), FREE, dtype=np.uint8)

    wall_px = max(1, round(config.wall_thickness_m / resolution_m))
    grid[:wall_px, :] = OCCUPIED
    grid[-wall_px:, :] = OCCUPIED
    grid[:, :wall_px] = OCCUPIED
    grid[:, -wall_px:] = OCCUPIED

    for cx, cy, w, d in obstacles:
        x0 = round((cx - w / 2 + config.width_m / 2) / resolution_m)
        x1 = round((cx + w / 2 + config.width_m / 2) / resolution_m)
        y0 = round((cy - d / 2 + config.depth_m / 2) / resolution_m)
        y1 = round((cy + d / 2 + config.depth_m / 2) / resolution_m)
        grid[max(0, y0):min(height_px, y1), max(0, x0):min(width_px, x1)] = OCCUPIED

    return grid, resolution_m


def write_map(grid: np.ndarray, resolution_m: float, config: WarehouseConfig, out_dir: Path) -> None:
    """Write `warehouse_map.pgm` and `warehouse_map.yaml` to `out_dir`."""
    pgm_path = out_dir / "warehouse_map.pgm"
    yaml_path = out_dir / "warehouse_map.yaml"
    # PGM row 0 is the top of the image; map_server expects row 0 = +y, so flip.
    Image.fromarray(np.flipud(grid), mode="L").save(pgm_path)
    yaml_path.write_text(
        "image: warehouse_map.pgm\n"
        f"resolution: {resolution_m}\n"
        f"origin: [{-config.width_m / 2}, {-config.depth_m / 2}, 0.0]\n"
        "negate: 0\n"
        "occupied_thresh: 0.65\n"
        "free_thresh: 0.196\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--resolution-m", type=float, default=0.05)
    args = parser.parse_args()

    config = WarehouseConfig()
    # Obstacle layout: read from the scenario's timed_obstacles / static assets
    # as they're added. Empty for the Phase 2 baseline map (perimeter only);
    # Task 8's acceptance test adds a static obstacle directly in Isaac, not
    # in the map, so Nav2's costmap obstacle *layer* (not the static map)
    # must detect it via /scan — this keeps the map authoring decoupled from
    # per-scenario obstacle placement.
    grid, resolution_m = build_occupancy_grid(config, obstacles=[], resolution_m=args.resolution_m)
    write_map(grid, resolution_m, config, args.out_dir)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify pass.**

Run: `pytest tests/unit/test_generate_warehouse_map.py -v`
Expected: PASS (2 tests). Add `Pillow` and `numpy` to `requirements.txt` if not already present (check first — M1 already uses `numpy`/OpenCV, `Pillow` is likely new; document why per CLAUDE.md "Dependencies").

- [ ] **Step 5: Generate the real map files and replace the stale placeholder.**

```bash
python isaac/scripts/generate_warehouse_map.py --out-dir ros2_ws/src/swarm_simulation/maps
```

Expected: `warehouse_map.pgm` and `warehouse_map.yaml` written to `ros2_ws/src/swarm_simulation/maps/`, overwriting the old placeholder `warehouse_map.yaml` (which referenced a `.pgm` that never existed and predates the current 12m×8m `WarehouseConfig`).

- [ ] **Step 6: Commit.**

```bash
git add isaac/scripts/generate_warehouse_map.py tests/unit/test_generate_warehouse_map.py ros2_ws/src/swarm_simulation/maps/
git commit -m "feat: author static warehouse occupancy-grid map from WarehouseConfig"
```

---

## Task 4 — [HOST] Wire the RTX lidar into the per-robot Isaac graph

**Files:**
- Modify: `isaac/vgu_sim/ros_graphs.py` — `create_robot_ros_graph`, using the verified mechanism from Task 2.

- [ ] **Step 1: Call the Task 2 lidar-authoring helper, then add a `ROS2RtxLidarHelper`-style publish node to the graph.** Use the exact node type and exclusion mechanism recorded in `phase2-nav2-stack.md` §10 (Task 2 Step 7) — do not re-guess.

```python
from isaac.vgu_sim.lidar import author_rtx_lidar

lidar_prim_path = author_rtx_lidar(stage, robot_prim_path, config.lidar_link)
```

Add the corresponding `isaacsim.sensors.rtx` ROS publish node (e.g. `OmniGraph` node such as `ROS2RtxLidarHelper` or `IsaacComputeRTXLidarFlatScan` — verify the exact type against the installed extension before transcribing) to the existing `og.Controller.edit` `CREATE_NODES`/`CONNECT`/`SET_VALUES` call, publishing `sensor_msgs/LaserScan` on `topicName=f"/{robot_id}/scan"`, `frameId=f"{robot_id}/base_scan"`.

- [ ] **Step 2: [HOST] Verify `/scan` end-to-end on the running graph, repeating Task 2's go/no-go check** (the standalone probe vs. the production graph wiring can differ):

```bash
ros2 topic hz /robot_1/scan
ros2 topic echo /robot_1/scan --once
```

Expected: ~10 Hz, 360 points (1 deg resolution), ranges `0.12-3.5 m`, no phantom return at the marker bearing.

- [ ] **Step 3: Commit.**

```bash
git add isaac/vgu_sim/ros_graphs.py
git commit -m "feat: publish /robot_id/scan via RTX lidar (FR6.4.9)"
```

---

## Task 5 — [HOST] Ground-truth localization: verify and wire `map → odom`

**Files:**
- Create: `ros2_ws/src/swarm_simulation/launch/nav2_robot.launch.py` (static TF portion only in this task; Nav2 bringup added in Task 6)

- [ ] **Step 1: [HOST] Verify the Reality Check's claim #2 before wiring anything.** With `robot_1` spawned at `x=-0.6, y=0.0` per `head_on_deadlock.yaml`, before any motion:

```bash
ros2 topic echo /robot_1/odom --once
```

Expected: `pose.pose.position.x ≈ -0.6`, matching the scenario's world-frame spawn coordinate exactly (not `≈ 0.0`, which would mean `/odom` is spawn-relative and this task's identity-transform shortcut is wrong). If it reads `≈ 0.0`, **stop** — `map → odom` is not identity; it must instead be a static transform equal to the spawn pose, and `phase2-nav2-stack.md` §5 needs a correction noting `/odom` is spawn-relative, not absolute-world.

- [ ] **Step 2: Author the static `map → <robot_id>/odom` identity transform.** Create the launch file:

```python
"""Per-robot Nav2 bringup: static map->odom TF (ground-truth shortcut, see
phase2-nav2-stack.md S5) plus the namespaced Nav2 stack (added in Task 6).
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    robot_id = LaunchConfiguration("robot_id")
    return LaunchDescription(
        [
            DeclareLaunchArgument("robot_id", description="e.g. robot_1"),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="map_to_odom_ground_truth",
                # Ground-truth shortcut (deliberate PoC, not real-robot path):
                # IsaacComputeOdometry reads the chassis's true world pose
                # directly (verified Task 5 Step 1), so map and <robot_id>/odom
                # are numerically the same frame and this transform is exact
                # identity, not an approximation.
                arguments=["0", "0", "0", "0", "0", "0", "map", [robot_id, "/odom"]],
            ),
        ]
    )
```

- [ ] **Step 3: [HOST] Launch and verify the TF chain resolves `map → <robot_id>/base_link`.**

```bash
ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_1
ros2 run tf2_ros tf2_echo map robot_1/base_link
```

Expected: prints a transform whose translation matches the robot's known world position (cross-check against `/robot_1/odom`).

- [ ] **Step 4: Commit.**

```bash
git add ros2_ws/src/swarm_simulation/launch/nav2_robot.launch.py
git commit -m "feat: ground-truth map->odom static TF (PoC localization shortcut)"
```

---

## Task 6 — [HOST] Per-robot namespaced Nav2 bringup

**Files:**
- Create: `ros2_ws/src/swarm_simulation/config/nav2_params.yaml`
- Modify: `ros2_ws/src/swarm_simulation/launch/nav2_robot.launch.py`

- [ ] **Step 1: Author `nav2_params.yaml`.** Controller `DWB`, planner `NavFn`, both costmaps fed by `/<robot_id>/scan`, BT navigator, behavior server. Key values pinned from the spec and `safety.yaml`:

```yaml
controller_server:
  ros__parameters:
    use_sim_time: true
    controller_frequency: 20.0
    FollowPath:
      plugin: "dwb_core::DWBLocalPlanner"
      max_vel_x: 0.2   # safety.yaml max_linear_velocity_mps cap, NOT the 0.22 mechanical max
      min_vel_x: 0.0
      max_vel_theta: 2.84
      use_stamped_cmd_vel: false   # verified Phase 1: ROS2SubscribeTwist takes plain Twist

planner_server:
  ros__parameters:
    use_sim_time: true
    GridBased:
      plugin: "nav2_navfn_planner::NavfnPlanner"

local_costmap:
  local_costmap:
    ros__parameters:
      use_sim_time: true
      global_frame: odom
      robot_base_frame: base_link
      width: 3
      height: 3
      resolution: 0.05
      footprint: "[[-0.07, -0.09], [-0.07, 0.09], [0.07, 0.09], [0.07, -0.09]]"
      plugins: ["obstacle_layer", "inflation_layer"]
      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        observation_sources: scan
        scan:
          topic: scan
          max_obstacle_height: 2.0
          obstacle_max_range: 3.5

global_costmap:
  global_costmap:
    ros__parameters:
      use_sim_time: true
      global_frame: map
      robot_base_frame: base_link
      footprint: "[[-0.07, -0.09], [-0.07, 0.09], [0.07, 0.09], [0.07, -0.09]]"
      plugins: ["static_layer", "obstacle_layer", "inflation_layer"]
      static_layer:
        plugin: "nav2_costmap_2d::StaticLayer"
      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        observation_sources: scan
        scan:
          topic: scan
          max_obstacle_height: 2.0
          obstacle_max_range: 3.5

bt_navigator:
  ros__parameters:
    use_sim_time: true
    global_frame: map
    robot_base_frame: base_link

behavior_server:
  ros__parameters:
    use_sim_time: true
```

Note: `footprint` `0.14 m × 0.18 m` per spec §3 ("Burger base"), expressed as half-extents `0.07/0.09` around the robot center.

- [ ] **Step 2: Extend the launch file with the namespaced bringup and shared `map_server`.** Verify the namespaced-bringup convention against the installed Jazzy `nav2_bringup` source (`bringup_launch.py`) before transcribing — multi-robot conventions change across distros (spec §3, README §7 "second-hardest part"):

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description() -> LaunchDescription:
    robot_id = LaunchConfiguration("robot_id")
    nav2_bringup_dir = get_package_share_directory("nav2_bringup")
    sim_dir = get_package_share_directory("swarm_simulation")

    return LaunchDescription(
        [
            DeclareLaunchArgument("robot_id", description="e.g. robot_1"),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="map_to_odom_ground_truth",
                arguments=["0", "0", "0", "0", "0", "0", "map", [robot_id, "/odom"]],
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([nav2_bringup_dir, "launch", "bringup_launch.py"])
                ),
                launch_arguments={
                    "namespace": robot_id,
                    "use_namespace": "true",
                    "map": PathJoinSubstitution([sim_dir, "maps", "warehouse_map.yaml"]),
                    "params_file": PathJoinSubstitution([sim_dir, "config", "nav2_params.yaml"]),
                    "use_sim_time": "true",
                    "slam": "false",
                }.items(),
            ),
        ]
    )
```

`map_server` is launched once per robot include by default in `bringup_launch.py`; if the verified Jazzy convention instead expects one shared `map_server` outside any namespace (common for multi-robot), split it out into its own non-namespaced `Node` here and record which convention was verified in the spec.

- [ ] **Step 3: [HOST] Bring up `robot_1`'s stack and confirm the action server is live.**

```bash
ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_1
ros2 action list | grep robot_1
```

Expected: `/robot_1/navigate_to_pose` and `/robot_1/follow_waypoints` listed.

- [ ] **Step 4: Record the verified bringup convention in the spec.**

```markdown
## 11. Verified per-robot Nav2 bringup (Jazzy)

- Bringup mechanism: <exact convention verified in Step 2/3>
- map_server: <per-robot include vs. shared single instance>
```

- [ ] **Step 5: Commit.**

```bash
git add ros2_ws/src/swarm_simulation/launch/nav2_robot.launch.py ros2_ws/src/swarm_simulation/config/nav2_params.yaml docs/specs/module4/phase2-nav2-stack.md
git commit -m "feat: namespaced per-robot Nav2 bringup with shared map/tf"
```

---

## Task 7 — [OFFLINE] `Nav2Adapter` implementation

**Files:**
- Modify: `ros2_ws/src/swarm_execution/swarm_execution/nav2_adapter.py`
- Modify: `ros2_ws/src/swarm_execution/package.xml` (add `<depend>nav2_msgs</depend>`)
- Test: `tests/unit/test_nav2_adapter.py`

**Interfaces (per spec §7 — implement exactly these three methods, no `CoordinationStatus` publishing):**
- `send_goal(robot_id: str, x: float, y: float, yaw: float) -> GoalHandle` — pre-empts any active goal for that robot.
- `send_waypoints(robot_id: str, waypoints: list[tuple[float, float]]) -> GoalHandle`
- `cancel(robot_id: str) -> None`

- [ ] **Step 1: Write the failing unit tests using a fake action client (no real ROS 2 action server needed).**

```python
from unittest.mock import MagicMock

import pytest

from swarm_execution.nav2_adapter import Nav2Adapter


class _FakeGoalHandle:
    def __init__(self):
        self.accepted = True
        self.cancel_goal_async = MagicMock()


class _FakeActionClient:
    def __init__(self):
        self.sent_goals = []
        self._handle = _FakeGoalHandle()

    def send_goal_async(self, goal_msg):
        self.sent_goals.append(goal_msg)
        future = MagicMock()
        future.result.return_value = self._handle
        return future

    def wait_for_server(self, timeout_sec=None):
        return True


@pytest.fixture
def adapter():
    a = Nav2Adapter.__new__(Nav2Adapter)  # bypass rclpy Node.__init__ in this offline test
    a._clients = {}
    a._active_goals = {}
    a._make_client = lambda robot_id, action_name: _FakeActionClient()
    return a


def test_send_goal_creates_one_client_per_robot(adapter):
    adapter.send_goal("robot_1", x=1.0, y=2.0, yaw=0.0)
    assert "robot_1" in adapter._clients


def test_send_goal_preempts_previous_goal(adapter):
    adapter.send_goal("robot_1", x=1.0, y=2.0, yaw=0.0)
    first_handle = adapter._active_goals["robot_1"]
    adapter.send_goal("robot_1", x=3.0, y=4.0, yaw=0.0)
    first_handle.cancel_goal_async.assert_called_once()


def test_cancel_calls_cancel_goal_async(adapter):
    adapter.send_goal("robot_1", x=1.0, y=2.0, yaw=0.0)
    handle = adapter._active_goals["robot_1"]
    adapter.cancel("robot_1")
    handle.cancel_goal_async.assert_called_once()


def test_cancel_unknown_robot_is_a_noop(adapter):
    adapter.cancel("robot_9")  # must not raise
```

- [ ] **Step 2: Run to verify failure.**

Run: `pytest tests/unit/test_nav2_adapter.py -v`
Expected: FAIL — `AttributeError`/`ImportError` against the current one-method placeholder.

- [ ] **Step 3: Implement `Nav2Adapter`.**

```python
"""Action-client wrapper around per-robot Nav2 (M4 spec phase2-nav2-stack.md S7).

This is the ONLY component that talks to Nav2 directly. It does not publish
CoordinationStatus or talk to M5 -- that translation belongs to the command
bus (Phase 3, command-bus.md), per the spec's boundary rule.
"""
from __future__ import annotations

from nav2_msgs.action import FollowWaypoints, NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node


class Nav2Adapter(Node):
    """Per-robot Nav2 action-client wrapper: send_goal, send_waypoints, cancel."""

    def __init__(self) -> None:
        super().__init__("nav2_adapter")
        self._clients: dict[str, ActionClient] = {}
        self._waypoint_clients: dict[str, ActionClient] = {}
        self._active_goals: dict[str, object] = {}

    def _make_client(self, robot_id: str, action_name: str) -> ActionClient:
        action_type = NavigateToPose if action_name == "navigate_to_pose" else FollowWaypoints
        return ActionClient(self, action_type, f"/{robot_id}/{action_name}")

    def send_goal(self, robot_id: str, x: float, y: float, yaw: float):
        """Send a NavigateToPose goal, pre-empting any active goal for robot_id."""
        if robot_id in self._active_goals:
            self._active_goals[robot_id].cancel_goal_async()

        client = self._clients.setdefault(robot_id, self._make_client(robot_id, "navigate_to_pose"))
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.orientation.z, goal_msg.pose.pose.orientation.w = _yaw_to_quat_zw(yaw)

        future = client.send_goal_async(goal_msg)
        handle = future.result()
        self._active_goals[robot_id] = handle
        return handle

    def send_waypoints(self, robot_id: str, waypoints: list[tuple[float, float]]):
        """Send a FollowWaypoints goal for a route (M3 reroute/convoy)."""
        client = self._waypoint_clients.setdefault(
            robot_id, self._make_client(robot_id, "follow_waypoints")
        )
        goal_msg = FollowWaypoints.Goal()
        for x, y in waypoints:
            pose = _pose_at(x, y)
            goal_msg.poses.append(pose)
        future = client.send_goal_async(goal_msg)
        handle = future.result()
        self._active_goals[robot_id] = handle
        return handle

    def cancel(self, robot_id: str) -> None:
        """Cancel robot_id's active goal, if any. No-op if none is active."""
        handle = self._active_goals.get(robot_id)
        if handle is not None:
            handle.cancel_goal_async()


def _yaw_to_quat_zw(yaw: float) -> tuple[float, float]:
    import math

    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def _pose_at(x: float, y: float):
    from geometry_msgs.msg import PoseStamped

    pose = PoseStamped()
    pose.header.frame_id = "map"
    pose.pose.position.x = x
    pose.pose.position.y = y
    return pose
```

- [ ] **Step 4: Add the `nav2_msgs` dependency.**

In `ros2_ws/src/swarm_execution/package.xml`, add inside the existing `<depend>` block:

```xml
<depend>nav2_msgs</depend>
```

- [ ] **Step 5: Run to verify pass.**

Run: `pytest tests/unit/test_nav2_adapter.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit.**

```bash
git add ros2_ws/src/swarm_execution/swarm_execution/nav2_adapter.py ros2_ws/src/swarm_execution/package.xml tests/unit/test_nav2_adapter.py
git commit -m "feat: implement Nav2Adapter as a per-robot action-client wrapper"
```

---

## Task 8 — [HOST] Acceptance test: single goal with an obstacle present

**Files:**
- Create: `tests/simulation/test_m4_phase2_nav2.py`

- [ ] **Step 1: Place a static obstacle in `robot_1`'s direct path for the test scenario.** Reuse the existing `isaac/assets/obstacles/dynamic_obstacle.usd` asset, spawned statically (no timed removal) between `robot_1`'s spawn (`x=-0.6`) and a test goal a few meters down the aisle — close enough to force the local planner to deviate, far enough that a straight-line path would clip it. Record the exact pose used.

- [ ] **Step 2: Write the acceptance test, mirroring `test_m4_phase1_drive.py`'s documented-skip pattern** (no `isaac_host` fixture exists yet):

```python
import pytest

from swarm_execution.nav2_adapter import Nav2Adapter

GOAL_X, GOAL_Y, GOAL_YAW = 2.0, 0.0, 0.0
TOLERANCE_M = 0.15


@pytest.mark.isaac_sim
@pytest.mark.ros2
@pytest.mark.skip(
    reason=(
        "No isaac_host/ros2 test harness exists yet for action-based goals. "
        "Manual HOST procedure: launch head_on_deadlock with the static "
        "obstacle from Task 8 Step 1 in robot_1's path, launch "
        "nav2_robot.launch.py robot_id:=robot_1, instantiate Nav2Adapter, "
        "call send_goal('robot_1', 2.0, 0.0, 0.0), poll /robot_1/odom until "
        "the goal result callback fires or 60s elapse, assert the final "
        "position is within 0.15m of the goal and that /robot_1/local_plan "
        "deviated around the obstacle (nonzero lateral excursion) rather "
        "than driving through it."
    )
)
def test_robot_reaches_goal_around_static_obstacle(isaac_host):
    adapter = Nav2Adapter()
    adapter.send_goal("robot_1", GOAL_X, GOAL_Y, GOAL_YAW)
    isaac_host.wait_for_goal_result("robot_1", timeout_sec=60.0)
    final = isaac_host.odom("robot_1")
    assert final.distance_to_xy(GOAL_X, GOAL_Y) < TOLERANCE_M
```

- [ ] **Step 3: [HOST] Run the manual procedure documented in the skip reason and record the result.** Append a verification report similar to `docs/reports/2026-06-19-m4-phase1-task6-tf-watchdog-verification.md`, including: final position vs. goal, whether the obstacle was avoided (not driven through), and `/robot_1/scan` cleanliness during the run (Task 2/4's gate still holding under motion, not just at rest).

- [ ] **Step 4: Confirm the test collects and skips cleanly in CI.**

Run: `pytest tests/simulation/test_m4_phase2_nav2.py -v`
Expected: `1 skipped`.

- [ ] **Step 5: Commit.**

```bash
git add tests/simulation/test_m4_phase2_nav2.py
git commit -m "test: M4 Phase 2 Nav2 goal-with-obstacle acceptance test"
```

---

## Task 9 — [HOST] Extend to `robot_2` — confirm multi-robot namespacing

**Files:**
- No new files; this re-runs Tasks 4-8's launch/verification with a second robot to confirm the namespaced design generalizes (README §7: "second-hardest part").

- [ ] **Step 1: [HOST] Bring up both robots' Nav2 stacks simultaneously.**

```bash
ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_1 &
ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_2 &
ros2 action list | grep navigate_to_pose
```

Expected: both `/robot_1/navigate_to_pose` and `/robot_2/navigate_to_pose` listed; no TF or `/scan` topic collisions (`ros2 topic list | grep scan` shows both `/robot_1/scan` and `/robot_2/scan` publishing independently).

- [ ] **Step 2: Send simultaneous goals and confirm independent costmaps.** Send `robot_1` and `robot_2` to goals on opposite sides of the static obstacle from Task 8; confirm each robot's `/robot_N/local_costmap/costmap` only reflects its own `/robot_N/scan`, not the other robot's.

- [ ] **Step 3: Record the result in the spec.**

```markdown
## 12. Verified multi-robot namespacing

Both robots' Nav2 stacks and /scan topics confirmed independent under
simultaneous bringup. No cross-robot costmap contamination observed.
```

- [ ] **Step 4: Commit.**

```bash
git add docs/specs/module4/phase2-nav2-stack.md
git commit -m "docs: verify multi-robot Nav2 namespacing under simultaneous bringup"
```

---

## Task 10 — Update docs and close the gap-analysis row

**Files:**
- Modify: `docs/specs/module4/README.md`

- [ ] **Step 1:** In README §2 change the Phase 2 row Status `Planned → Done`. In §3.2, update the four Phase-2 gap-analysis rows ("RTX 2D lidar", "Warehouse occupancy-grid map", "Nav2 install + per-robot bringup", "Localization (map → odom)") from their current "Absent"/"Specified, not built" state to reference this plan and the verified-facts sections appended in Tasks 1-2, 5-6, 9. Leave the `Nav2Adapter.send_waypoints` row's status note updated from `NotImplementedError` to "Implemented (Task 7)".

- [ ] **Step 2: Commit.**

```bash
git add docs/specs/module4/README.md
git commit -m "docs: mark M4 Phase 2 Nav2 stack implemented"
```

---

## Self-Review

- **Spec coverage** (`phase2-nav2-stack.md`): §2 lidar → Tasks 2, 4 (FR6.4.9-10, with the explicit go/no-go gate the README flags as highest risk); §3 namespacing → Tasks 6, 9; §4 map → Task 3 (Option A); §5 localization → Task 5 (Option A, simplified by the Phase-1-verified fact that `/odom` is already ground truth — documented as a deliberate deviation from "publish a small ground-truth publisher" to "static identity transform," with a verification step that fails loudly if the underlying assumption is wrong); §6 Nav2 parameters → Task 6 (`max_vel_x: 0.2` pinned to `safety.yaml`, `use_stamped_cmd_vel: false` resolved from Phase 1, not re-verified); §7 `Nav2Adapter` → Task 7 (exact three methods, explicit non-goal on `CoordinationStatus`); §8 testing → Task 8.
- **Non-goals enforced:** command bus and safety monitor are explicitly out of scope (stated up front and reiterated in Task 7's interface contract) per the advisor-confirmed scope cut — Phase 2's own acceptance test is adapter-direct.
- **Risk-ordered sequencing:** Task 1 (dependency gate) and Task 2 (lidar/ArUco go-no-go) come before any map/Nav2 investment, per the spec's own risk ranking — a dirty `/scan` or a failed Nav2 install would invalidate every later task.
- **No re-derivation of settled facts:** Twist-vs-TwistStamped (Phase 1 §2a(a)) and the Fabric/world-pose investigation are referenced, not re-investigated. The `/odom`-is-ground-truth claim is treated as a hypothesis requiring one verification step (Task 5 Step 1), not blind reuse, since it changes the Phase 2 spec's own design (publisher → static transform).
- **Type/interface consistency:** `Nav2Adapter.send_goal`/`send_waypoints`/`cancel` signatures in Task 7 match the spec §7 interface exactly; Task 8's acceptance test calls `send_goal` with the same signature.
- **Single-robot-first, multi-robot-last:** Tasks 4-8 build and verify `robot_1` only; Task 9 isolates the namespacing risk to one dedicated task rather than threading it through every earlier task, per the advisor's sequencing.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-21-m4-phase2-nav2-stack.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks. Tasks 1, 2, 4, 5, 6, 8, 9 are **[HOST]** and need the GCP Isaac Sim host; Tasks 3 and 7 are **[OFFLINE]** and can run anywhere, anytime. Task 2 is a hard go/no-go gate — if it fails, stop and replan before Tasks 3-9.
2. **Inline Execution** — execute in this session with checkpoints; Tasks 3 and 7 can be done immediately, the [HOST] tasks batched for a sim session.

Which approach?

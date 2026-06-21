# M6 Isaac Sim Headless Rendering — Fabric Sync Investigation

**Date:** 2026-06-21
**Branch:** feat/m4-phase1-drive-chain
**Goal:** Produce an MP4 showing TurtleBot robots visually driving in the `head_on_deadlock` scenario via the M1 annotated overhead camera pipeline.

---

## Problem Statement

Robots were physically moving (confirmed via odometry: 0.56m travel), but the overhead RTX camera showed a completely frozen scene. M1 annotations appeared at fixed spawn positions regardless of physics simulation progress.

---

## Root Cause Chain

Three separate bugs combined to produce the frozen camera:

### Bug 1: ArUco Marker Outside Physics Hierarchy

`author_aruco_marker()` placed the marker mesh as a direct child of the static robot root Xform:

```
/World/Robots/robot_1/aruco_marker   ← WRONG: never moves
```

Physics only moves `base_link` and its descendants. The robot root Xform is a static container. The visible ArUco squares — the most prominent feature in the overhead camera — were frozen at spawn while the chassis moved underneath them.

**Fix:** Place the mesh under `aruco_marker_link`, which is a physics child of `base_link`:

```
/World/Robots/robot_1/Geometry/base_footprint/base_link/aruco_marker_link/aruco_marker
```

Set translate offset to zero (aruco_marker_link is already at the correct height z≈0.22m).

### Bug 2: Fabric Not Receiving Newton Physics Positions

Isaac Sim 6.0 uses two separate data stores:

- **pxr USD stage** — Newton writes physics results here (`updateToUsd=True` by default)
- **Fabric (usdrt)** — The RTX renderer reads from here via `omni.hydra.usdrt_delegate`

These are NOT automatically synchronized for Newton articulations. The RTX camera was rendering the Fabric state, which never updated, so the scene was frozen despite pxr USD having correct positions.

**Investigation path:**

| Probe | Finding |
|---|---|
| `probe_usd_default.py` | pxr USD x-displacement: 0.56m ✅ Newton writes correctly |
| `probe_usd_default.py` | Camera mean_diff: 0.027 (static) ❌ Renderer sees frozen Fabric |
| `probe_manual_fabric_sync.py` | Manual `fa.Set(usdrt.Gf.Vec3d(...))` after each step → still static |
| `probe_fabric_notice.py` | `enable_fabric_usd_notice_handler` → Fabric x-displacement: 0.56m ✅ |
| `probe_fabric_notice.py` | Camera still static ❌ (local vs world coordinate issue) |
| `probe_world_fabric.py` | Write WORLD pos to Fabric after each step → robots visually move ✅ |

**Root cause detail:** `base_link` has `omni:fabric:resetXformStack=True`, which tells the renderer to treat Fabric's `xformOp:translate` as a **world-space** position. The `enable_fabric_usd_notice_handler` syncs the **local** USD translate (near zero) to Fabric — placing the robot at x≈0 instead of its actual world position (x=±0.6). The manual world-position write overrides this.

**Working fix:**

```python
# After opening stage, before play()
from isaacsim.core.simulation_manager import SimulationManager
SimulationManager.enable_fabric_usd_notice_handler(stage_id, True)

# After each app.update():
xf = UsdGeom.Xformable(base_link_usd_prim)
t = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
fabric_attr = base_link_usdrt_prim.GetAttribute("xformOp:translate")
fabric_attr.Set((float(t[0]), float(t[1]), float(t[2])))
```

**What does NOT work:**
- `omni.physx.fabric` extension + `updateToUsd=False`: handles PhysX rigid bodies only, not Newton articulations
- `isaacsim.physics.fabric`: does not exist in any extension registry in Isaac Sim 6.0
- `SimulationManager.enable_fabric(True)`: requires `omni.physxfabric` Python module, absent in some builds

### Bug 3: Validation Path Mismatch Causing Silent Crash

After fixing the marker placement (Bug 1), the scenario USDs were rebuilt. But `validation.py:validate_robot_marker` still checked the old path:

```python
marker_path = f"{robot_prim_path}/aruco_marker"  # OLD: root level
```

When called from `_record()`, this raised `ValidationError` → wrapped as `RuntimeError` → Kit's exception handler consumed it before any `print()` calls, producing **zero output** and a clean shutdown. Looked identical to a normal exit.

**Symptom:** Isaac Sim starts, loads extensions, then shuts down after ~27s with no error message.

**Fix:** Update `validate_robot_marker` to match the new path:

```python
marker_path = (
    f"{robot_prim_path}/Geometry/base_footprint/base_link"
    f"/aruco_marker_link/aruco_marker"
)
```

**Lesson:** Always update `validation.py` in sync with `marker_asset.py`. A path mismatch produces a silent crash indistinguishable from a clean exit.

---

## Secondary Finding: STALE vs STOPPED Annotation on Collision

After the fixes, the video showed robots moving and converging correctly. However, when robots stopped face-to-face (the deadlock scenario), their annotation boxes turned **grey** (STALE) rather than **red** (STOPPED).

**Cause:** When two robots are stacked at the same position, their ArUco markers physically overlap. ArUco detection can only decode one marker at a time. The occluded robot stops receiving detections. After `stale_after_sec=1.0s` (10 frames at 10fps capture), its StateEstimator entry transitions to STALE.

The detected robot: `velocity_alpha=0.3` smoothing means estimated velocity decays slowly after a stop event (`v_new = 0.3 * measured + 0.7 * old`). It may briefly pass through SLOW (yellow) but can also reach STALE before the smoothed velocity crosses `stopped_threshold_mps=0.01`.

**Fix (not yet applied):** In `record_m1_drive.py`:
- Increase `stale_after_sec` from `1.0` to `3.0`
- Decrease `velocity_alpha` from `0.3` to `0.15` for faster convergence

---

## Files Changed

| File | Change |
|---|---|
| `isaac/vgu_sim/marker_asset.py` | Move marker mesh to `aruco_marker_link` physics child |
| `isaac/vgu_sim/validation.py` | Update `validate_robot_marker` to new marker path |
| `isaac/scripts/record_m1_drive.py` | Replace `omni.physx.fabric` approach with notice handler + world-pos Fabric write |
| `isaac/scripts/probe_world_fabric.py` | Probe confirming the working Fabric fix |
| `isaac/scripts/probe_fabric_notice.py` | Probe for `enable_fabric_usd_notice_handler` |
| `isaac/scripts/probe_manual_fabric_sync.py` | Probe for manual Fabric position write |
| `isaac/scripts/probe_usd_default.py` | Probe confirming Newton writes correctly to pxr USD |
| `isaac/scripts/probe_newton_fabric.py` | Probe confirming `isaacsim.physics.fabric` does not exist |

---

## Outcome

- `data/logs/recordings/m1_drive.mp4`: 120 frames, 12s, 10fps
- M1 detects both robots throughout
- Robots visually drive from x=±0.6 to deadlock at x≈−0.08 (0.52m travel visible in camera)
- Commit: `b86e744`

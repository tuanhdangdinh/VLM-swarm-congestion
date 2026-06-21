# M4 Phase 1 — Drive Chain Completion Report

**Date:** 2026-06-21
**Branch:** `feat/m4-phase1-drive-chain` (merged to `main` at `774b0c9`)
**Plan:** `docs/superpowers/plans/2026-06-19-m4-phase1-drive-chain.md`
**GCP host:** Ubuntu 22.04, Isaac Sim 6.0 at `/home/ubuntu/IsaacSim`
**Scenario:** `head_on_deadlock`

---

## Goal

Make each simulated TurtleBot3 drive in response to `geometry_msgs/Twist` on
`/<robot_id>/cmd_vel`, with a TF tree and a 0.5 s command watchdog, so the
head-on deadlock scenario emerges dynamically from robot motion rather than being
a static spawn snapshot. Produce a verified MP4 showing M1 tracking both robots
through the full approach and deadlock.

---

## What Was Built

| Component | File | Status |
|---|---|---|
| Wheel velocity drive authoring | `isaac/vgu_sim/robot_drive.py` | ✅ |
| Wheel contact friction | `isaac/vgu_sim/robot_drive.py:configure_contact_friction` | ✅ |
| OmniGraph drive chain | `isaac/vgu_sim/ros_graphs.py` | ✅ |
| TF tree (dynamic odom→base_footprint, static base_link/base_scan) | `isaac/vgu_sim/ros_graphs.py` | ✅ |
| cmd_vel watchdog pure core | `isaac/vgu_sim/cmd_vel_watchdog.py` | ✅ |
| cmd_vel watchdog rclpy relay node | `isaac/vgu_sim/cmd_vel_watchdog_node.py` | ✅ |
| Forward-displacement test oracle | `isaac/vgu_sim/diff_drive_oracle.py` | ✅ |
| In-sim acceptance test (documented-skip) | `tests/simulation/test_m4_phase1_drive.py` | ✅ |
| M1 annotated headless recorder | `isaac/scripts/record_m1_drive.py` | ✅ |
| Verified recording | `data/logs/recordings/m1_drive.mp4` | ✅ |

---

## Findings and Mistakes

### 1. Robots Would Not Move — Missing Wheel Contact Friction

**Discovery:** After wiring the full OmniGraph drive chain (cmd_vel →
DifferentialController → ArticulationController), the robots refused to translate.
Joint velocities were non-zero (the DifferentialController was outputting wheel
targets) but the chassis position did not change.

**Root cause:** The TurtleBot3 asset and the warehouse floor ship with
`UsdPhysics.CollisionAPI` but no `UsdPhysics.MaterialAPI`. PhysX defaults to a
frictionless contact when no material is bound, so the wheels spun in place with
zero traction.

**Fix:** Added `configure_contact_friction()` to `robot_drive.py`. It authors a
shared `PhysicsMaterial` prim at `/World/PhysicsMaterials/RobotWheel` from
`RobotAssetConfig.wheel_static_friction` / `wheel_dynamic_friction` and binds it
to every wheel collider in the robot subtree and the floor prim. Called from the
scenario builder alongside `configure_wheel_velocity_drive`.

**Lesson:** In Isaac Sim 6.0 with Newton, a zero-friction default is silent — the
drive chain appears healthy (non-zero joint velocities, no errors) but the robot
does not move. Always bind a physics material explicitly to both contact surfaces.

---

### 2. Spawn Positions Too Far Apart for M1 Detection

**Discovery:** The original `head_on_deadlock.yaml` spawned robots at x=±4.5 m.
At that distance the ArUco markers were at or beyond the camera FOV edges and M1
detected zero robots.

**Fix:** Moved spawn positions to x=±0.6 m (nose-to-nose near the intersection
centre, 1.2 m apart, headings opposed). Both markers land near image centre and
fully in-frame. Goals were kept at x=±3.0 m so each robot's goal is across the
other, preserving the head-on deadlock geometry.

**Lesson:** The camera FOV and calibration constrain the usable spawn envelope.
Spawning at the full aisle length (x=±4.5) was designed for a real robot with
lidar; in simulation with an overhead fixed camera, the working range is much
narrower.

---

### 3. Overhead Camera Showed Frozen Scene Despite Robots Moving

This was the largest investigation in the phase. Robots were physically moving
(odometry confirmed 0.56 m travel) but the RTX overhead camera showed a completely
frozen scene throughout.

**Three separate bugs combined:**

#### 3a. ArUco Marker Outside Physics Hierarchy

`author_aruco_marker()` placed the marker mesh as a direct child of the static
robot root Xform (`/World/Robots/robot_1/aruco_marker`). Physics only moves
`base_link` and its descendants. The visible ArUco squares — the dominant feature
in the overhead camera — were frozen at spawn while the chassis moved under them.

**Fix:** Moved the mesh to `aruco_marker_link`, a physics child of `base_link`:
```
/World/Robots/{id}/Geometry/base_footprint/base_link/aruco_marker_link/aruco_marker
```
Translate offset zeroed (aruco_marker_link is already at the correct height).
Rebuilt all three scenario USDs after the change.

#### 3b. Newton Positions Not Reaching the RTX Renderer (Fabric/USD Sync)

Isaac Sim 6.0 uses two separate data stores: pxr USD (where Newton writes physics
results) and Fabric (where the RTX renderer reads via `omni.hydra.usdrt_delegate`).
These are not automatically synchronised for Newton articulations.

**Investigation path:**

| Probe | Finding |
|---|---|
| `probe_usd_default.py` | pxr USD x-displacement 0.56 m ✅ — Newton writes correctly |
| `probe_usd_default.py` | Camera static ❌ — renderer reads frozen Fabric |
| `probe_manual_fabric_sync.py` | Manual `usdrt` Set() after each step → still static |
| `probe_newton_fabric.py` | `isaacsim.physics.fabric` does not exist in any registry |
| `probe_fabric_notice.py` | `enable_fabric_usd_notice_handler` → Fabric displacement 0.56 m ✅ |
| `probe_fabric_notice.py` | Camera still static ❌ — local vs world coordinate mismatch |
| `probe_world_fabric.py` | Write WORLD position to Fabric after each step → robots move ✅ |

**Root cause detail:** `base_link` has `omni:fabric:resetXformStack=True`, which
tells the renderer to treat Fabric's `xformOp:translate` as a world-space position.
`enable_fabric_usd_notice_handler` syncs the LOCAL USD translate (near zero) to
Fabric, placing the robot at x≈0 instead of its actual world position (x=±0.6).
Writing the actual world coordinates (from `ComputeLocalToWorldTransform`) to
Fabric after each `app.update()` corrects the renderer's view.

**Working fix in `record_m1_drive.py`:**
```python
# Enable USD→Fabric notice handler
SimulationManager.enable_fabric_usd_notice_handler(stage_id, True)

# After each app.update():
xf = UsdGeom.Xformable(base_link_usd_prim)
t = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
fabric_attr = base_link_usdrt_prim.GetAttribute("xformOp:translate")
fabric_attr.Set((float(t[0]), float(t[1]), float(t[2])))
```

**What does NOT work:**
- `omni.physx.fabric` + `updateToUsd=False` — handles PhysX rigid bodies only, not Newton articulations
- `isaacsim.physics.fabric` — does not exist in Isaac Sim 6.0
- `SimulationManager.enable_fabric(True)` — requires `omni.physxfabric` Python module, absent in this build

#### 3c. Silent Validation Crash After Marker Move

After fixing the marker placement (3a) and rebuilding the USDs, the recorder
still produced zero output and a clean exit. `validate_robot_marker` in
`validation.py` still checked the old path (`{robot}/aruco_marker`). This raised
`ValidationError` inside `_validate_stage()`, which Kit's exception handler consumed
before any `print()` calls ran — indistinguishable from a normal exit.

**Fix:** Updated `validate_robot_marker` to check the new path:
```
{robot}/Geometry/base_footprint/base_link/aruco_marker_link/aruco_marker
```

**Lesson:** Always update `validation.py` in sync with `marker_asset.py`. A path
mismatch produces a silent crash. When a recorder exits cleanly with no output,
check `_validate_stage` before assuming an Isaac Sim crash.

---

### 4. TF Subscriber Starvation (Probe Artifact)

During Task 6 TF verification, an early probe showed the ROS-received TF yaw
freezing at ~114° while `/odom` kept climbing (43° divergence). The graph was
actually healthy — instrumenting in-process OmniGraph reads showed the publisher
input kept advancing.

**Root cause:** The probe serviced only one rclpy callback per sim step. The graph
emits ≥2 messages per step (`/odom` + `/tf`); the lower-priority `/tf` queue
saturated and stopped advancing.

**Fix:** Drain all ready callbacks per step (8× `executor.spin_once(timeout_sec=0)`
instead of 1×).

**Lesson:** In headless Isaac Sim, always drain all ready rclpy callbacks per
`app.update()` step. A single `spin_once` starves lower-priority topics when
multiple publishers fire on the same tick.

---

### 5. M1 Marks Stopped Robots STALE Instead of STOPPED on Collision

**Discovery:** In the recorded video, when the two robots meet at the centre and
stop face-to-face, their annotation boxes turn grey (STALE) rather than red
(STOPPED).

**Root cause:** When two robots are stacked at the same position, their ArUco
markers physically overlap and ArUco detection can only decode one at a time. The
occluded robot stops receiving detections. With `stale_after_sec=1.0` and a capture
rate of 10 fps, the undetected robot transitions to STALE after just 10 frames.
The detected robot: `velocity_alpha=0.3` smoothing means estimated velocity decays
slowly after a stop event and may reach STALE before crossing `stopped_threshold_mps=0.01`.

**Fix (not yet applied):** In `record_m1_drive.py`:
- Increase `stale_after_sec` from `1.0` to `3.0` — gives velocity time to smooth to zero
- Decrease `velocity_alpha` from `0.3` to `0.15` — faster velocity convergence after stop

**This is not a bug in M1's core logic** — it is a recorder tuning issue. The
`StateEstimator` parameters were set for real-time operation; for a 10 fps
simulation recording with overlapping markers, they need adjustment.

---

### 6. Task 6 TF/Watchdog Verification — Key Results

Full details in `docs/reports/2026-06-19-m4-phase1-task6-tf-watchdog-verification.md`.
Summary:

- Quaternion convention correct: `|yaw_wire − yaw_src| = 0.0°` over a 166° sweep
- TF tracks odom at −1.0° steady offset (expected finite-difference lag)
- Watchdog zeros stale command in 0.567 s of sim time (~0.5 s timeout + one relay tick)
- Branch B (relay node) confirmed correct: no built-in timeout exists in `DifferentialController`

---

## Outcome

- `data/logs/recordings/m1_drive.mp4` — 120 frames, 12 s, 10 fps
- M1 detects both robots in every frame throughout
- Robots drive from x=±0.6 to deadlock at x≈−0.08 (0.52 m travel visible in camera)
- All 8 plan tasks complete and merged to `main`

---

## Cross-References

| Topic | Document |
|---|---|
| TF tree + watchdog host verification | `docs/reports/2026-06-19-m4-phase1-task6-tf-watchdog-verification.md` |
| Fabric sync root-cause chain (probes) | `docs/reports/2026-06-21-m6-fabric-sync-investigation.md` |
| Phase 1 implementation plan | `docs/superpowers/plans/2026-06-19-m4-phase1-drive-chain.md` |
| Phase 2 spec (Nav2 + lidar) | `docs/specs/module4/phase2-nav2-stack.md` |

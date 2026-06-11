# M1 ↔ Isaac Sim Camera Wiring — Design

**Date:** 2026-06-11 · **Status:** Approved (design) · **Module:** M1 Perception × M6 Simulation

---

## 1. Problem & Goal

M1 Perception is implemented and its ROS2 plumbing already subscribes to the
canonical `/camera/image_raw`. The live Isaac scene (`isaac/vgu_sim`) already
publishes `/camera/image_raw` and `/camera/camera_info` with `frame_id =
overhead_camera`. The pipeline, topics, and contract are therefore in place.

The single remaining gap is **calibration**: the shipped
`ros2_ws/src/swarm_perception/config/calibration.yaml` carries a placeholder
**identity homography** and placeholder intrinsics, so M1's world-frame
coordinates are meaningless against the actual Isaac overhead camera.

**Goal:** generate a correct intrinsics `K` and pixel→world homography `H` from
the live `CameraConfig`, and prove the result matches Isaac ground truth.

### Out of scope (separate responsibilities)

- TurtleBot USD assets and top-mounted ArUco markers — **M6**, assumed present.
- Isaac ROS2 bridge / OmniGraph publishing — **M6**, already done
  (`isaac/vgu_sim/ros_graphs.py`).
- Any change to the camera topic contract — none needed; both sides already use
  `/camera/image_raw` + `/camera/camera_info`.

### Context: legacy retirement (completed before this design)

The Phase-1 `tools/isaac_scene/` ASCII scene generator was a superseded
prototype that authored a *different* overhead camera (z=14, focal 18). It was
removed (along with its untracked test, the `data/generated/` output dir, and
the `generate-isaac-scene` Makefile target) so this work anchors solely on the
live `isaac/vgu_sim` camera definition. `isaac/vgu_sim` (library) and
`isaac/scripts` (Isaac-booting CLIs) are a healthy library/CLI split and remain.

---

## 2. Source of Truth

`isaac/vgu_sim/config.py::CameraConfig` is the single source of truth for the
overhead camera:

| Field | Value |
|---|---|
| `prim_path` | `/World/Sensors/OverheadCamera` |
| `frame_id` | `overhead_camera` |
| `width × height` | 1280 × 960 |
| `fps` | 30 |
| `position_m` | (0.0, 0.0, 3.0) |
| `orientation_quat_wxyz` | (1, 0, 0, 0) — nadir / straight down |
| `focal_length_mm` | 10.48 |
| `horizontal_aperture_mm` | 20.955 |
| `vertical_aperture_mm` | 15.716 (square-pixel) |
| ROI | 6.0 × 4.5 m |

The config's own comment states *"CameraInfo K and M1 homography must match"* —
this design satisfies that by deriving both calibration and (the already-built)
`camera_info` graph from the same object.

---

## 3. Architecture

| Unit | Type | Responsibility | Runs on |
|---|---|---|---|
| `isaac/vgu_sim/calibration.py` | new | Pure function `CameraConfig → CalibrationArtifact`. No `omni`/`pxr`. | Mac |
| `isaac/scripts/export_calibration.py` | new | Thin CLI writing `calibration.yaml` from `CameraConfig`. | Anywhere |
| `ros2_ws/src/swarm_perception/config/calibration.yaml` | regenerate | Real `K` + `H`, replacing the identity placeholder. | — |
| `tests/unit/test_isaac_calibration.py` | new | Synthetic round-trip + spot checks + determinism. | Mac |
| `tests/unit/test_perception.py` (extend) | edit | Marker-at-known-pixel → `RobotState.(x,y)` matches expected world point. | Mac |
| In-sim validation procedure | new (doc + helper) | M1 `SceneState` vs Isaac ground truth, ≤ tolerance. | Isaac (Windows) |

**Co-location rationale:** camera and calibration both derive from the same
`CameraConfig`, so they cannot drift. The generator is pure math with no Isaac
imports, so it is fully unit-testable on the Mac.

**`camera_info` note:** M1 keeps reading the static `calibration.yaml` rather
than subscribing to `/camera/camera_info`, because the ground-plane homography
is not part of a `CameraInfo` message (K/D/R/P only). Both artifacts come from
the same `CameraConfig`, so they stay consistent by construction.

---

## 4. Calibration Math

All analytic — no image capture.

### 4.1 Intrinsics `K`

```
fx = focal_length_mm / horizontal_aperture_mm * width   = 10.48/20.955 * 1280 ≈ 640.1
fy = focal_length_mm / vertical_aperture_mm   * height  = 10.48/15.716 * 960  ≈ 640.2
cx = width  / 2 = 640.0
cy = height / 2 = 480.0
K  = [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
```

Distortion = zeros (ideal sim pinhole; matches the existing no-op `undistort`).

### 4.2 Pixel→world homography `H`

For a nadir camera at height `h = 3.0` over the ground plane `z = 0`, with
camera world XY `(Cx, Cy) = (0, 0)`:

```
X = Cx + (u - cx) * h / fx
Y = Cy ± (v - cy) * h / fy        # sign fixed by USD camera axes

H = [[ h/fx,    0,   Cx - cx*h/fx ],
     [   0,  ±h/fy,  Cy ∓ cy*h/fy ],
     [   0,    0,         1       ]]
```

**Axis convention.** USD cameras look down local −Z with image +x→right,
+y→up. The resulting world XY sign/axis mapping is **not** asserted by
inspection — the generator is derived from the same projection model used by the
round-trip test (§5.1), so any wrong sign or X/Y swap fails on the Mac before
touching Isaac.

**Generalization.** Implement the full projective derivation (using the pose
quaternion), then verify it collapses to the nadir formulas above. This makes
the `orientation_quat_wxyz` tilt the config already anticipates work later with
no further change; a tilted planar view still yields a valid homography.

---

## 5. Testing & Validation

### 5.1 Unit (Mac, no Isaac) — `tests/unit/test_isaac_calibration.py`

A self-contained synthetic projector (world→pixel via `K` + pose) paired with
the generator's pixel→world `H`:

- **Round-trip:** N ground points across the ROI → pixels → back through `H` →
  error < 1e-6 m. Catches the axis-sign bug.
- **Spot checks:** `(0,0)` → image center `(640,480)`; `+1 m` in X → pixel shift
  `fx/h ≈ 213 px`.
- **Determinism:** same `CameraConfig` → identical `calibration.yaml` bytes.
- **Consistency:** generated `K` equals the `K` the `camera_info` graph would
  publish from the same config.

### 5.2 Integration (Mac, no Isaac) — extend `test_perception.py`

Feed `process_frame` a synthetic frame with an ArUco marker at a known pixel,
using the generated calibration → assert `RobotState.(x,y)` equals the world
point for that pixel. Proves calibration flows through the real M1 pipeline,
offline.

### 5.3 Sim validation (Windows/Isaac) — documented procedure + helper

- Launch sim + `perception.launch.py use_camera_node:=false`.
- Place one marked robot at a known world pose (scenario/oracle).
- Compare M1's published `SceneState (x,y)` vs Isaac ground truth via existing
  `isaac/vgu_sim/oracle.py` / `validation.py`.
- **Pass:** position error ≤ **5 cm** (≈ one marker half-width); refine after the
  first real run.

### 5.4 Error handling

The generator validates `CameraConfig` invariants (h > 0, apertures > 0, square
pixels within ε) and raises `CalibrationError` (consistent with the existing
calibration module). No silent fallback to identity.

---

## 6. Acceptance Criteria

1. `calibration.yaml` is regenerated from `CameraConfig` with non-identity `K`
   and `H`.
2. `test_isaac_calibration.py` round-trip passes (< 1e-6 m).
3. Integration test maps a known marker pixel to the correct world point through
   the real pipeline.
4. In-sim, M1 `SceneState (x,y)` matches ground truth within the documented
   tolerance.
5. Regenerating from an unchanged `CameraConfig` is byte-stable.

---

## 7. In-sim validation procedure (runbook)

Run on the Isaac Sim host (Windows). Prerequisite: `calibration.yaml` has been
regenerated (Task 4) and the workspace rebuilt (`colcon build --packages-select
swarm_perception`).

1. Launch the simulation (publishes `/camera/image_raw`, `/camera/camera_info`,
   and one marked robot at a known world pose):
   `./scripts/run_simulation.sh <scenario>`  (or the PowerShell equivalent).
2. In a second shell, launch M1 against the external camera:
   `ros2 launch swarm_perception perception.launch.py use_camera_node:=false`.
3. Read M1 output: `ros2 topic echo /perception/scene_state` and take a
   robot's `(x, y)`.
4. Read ground truth for the same robot from the scenario/oracle
   (`isaac/vgu_sim/oracle.py`).
5. Compute `calibration_position_error(measured, ground_truth)`.
6. **Pass:** error <= 0.05 m (one marker half-width). Refine the tolerance
   after the first real run and record the observed value here.

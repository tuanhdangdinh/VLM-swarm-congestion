# Design: ArUco markers on simulated robots (M6 → M1 enablement)

**Date:** 2026-06-17
**Status:** Approved (pending spec review)
**Scope owner:** M6 simulation (`isaac/vgu_sim`, robot URDF asset), with a one-line M1
config alignment and an offline parity test touching M1 (`swarm_perception`)

---

## Problem

M1 perception identifies robots and estimates their world poses **solely** via ArUco
detection. The TurtleBot3 URDF asset
(`isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.urdf`) already declares an
`aruco_marker_link` — a flat, visual-only mount on top of the robot — but it is a **plain
white box (`0.055 × 0.055 × 0.001 m` at z = 0.10) with no ArUco texture.** Two problems
follow:

1. **No decodable pattern.** The overhead camera renders a blank white square; M1 finds no
   ArUco code, so `SceneState.robots` is empty and M2 reasons over an empty scene.
2. **Too small to detect.** At 0.055 m and the default camera (3 m height, 1280 px, 6 m
   ROI ≈ 4.7 mm/px), the marker spans ~13 px ≈ ~2 px/module — far below reliable ArUco
   detection even before texturing.
3. **Occluded by the lidar.** The marker joint is at z = 0.10, but the lidar (`base_scan`)
   sits at z = 0.172 (collision cylinder radius 0.055, centered x = −0.032) — i.e. *above*
   the marker and overlapping most of its footprint. From a nadir overhead camera the lidar
   occludes the center/left of a 0.12 m tag, breaking decode.

Note: `marker_id` (validated 1..N, unique, ordered in `RobotScenarioConfig`) is used
**only** for that validation — ROS topics and USD prim paths key off `robot_id`, not
`marker_id`. This design is the first consumer of `marker_id` as a rendered identity.

## Goals

- Each robot in a built scenario carries a flat, horizontal, **textured** ArUco tag keyed
  to its `marker_id`, large enough to be detectable, reusing the existing
  `aruco_marker_link` mount.
- Marker dictionary parity with M1 is enforced by having the generator read the dictionary
  **name** from M1's `aruco.yaml` (single source of truth), so a config change can't
  silently desync the two sides.
- A single physical marker size (0.12 m) across the authored USD quad, M1's `aruco.yaml`,
  and the detection test.

## Non-goals (explicitly out of scope)

- **No camera retune.** Detectability at 0.12 m is still marginal (~4–4.5 px/module) and is
  accepted as a known risk to validate empirically once rendering. Not changing
  `CameraConfig` or recomputing calibration here.
- **No M1 detector/calibration code changes.** M1 already targets `DICT_4X4_50` and the
  1280×960 camera (`calibration.yaml` is generated from the same `CameraConfig`). The only
  M1 touch is a one-line `aruco.yaml` value alignment (below).
- **No reconciliation of M1-derived `robot_id` vs Isaac's `robot_id` naming.** M1 reports
  robots keyed by what it derives from `marker_id`; Isaac names robots separately. Flagged,
  not fixed, here.
- No M5/M3/M4 work.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Marker mount | Reuse the URDF `aruco_marker_link` as a **mount frame**, raised above the lidar; author an explicit UV quad on it (don't texture the imported box) |
| Asset production | Standalone gen script (dev venv, `opencv-contrib`) → committed PNGs |
| Physical size | **0.12 m** across the authored USD quad, M1 `aruco.yaml`, and tests; the URDF provides only the marker-frame height |
| Per-id texture | Bound **per-robot** in `_author_robot` (the imported USD is shared) |
| Detectability | Accept as known risk; no camera change |
| PNG distribution | **Commit** the generated PNGs into the repo |
| Parity test | Full clean-image round-trip over all generated ids |

---

## Components & data flow

```
scripts/generate_aruco_markers.py   (dev venv, opencv-contrib, run once)
  reads dictionary name from ros2_ws/.../config/aruco.yaml
        │  writes
        ▼
isaac/assets/markers/aruco_4x4_50/marker_<id>.png   (committed)
        │  bound as per-robot USD texture override
        ▼
turtlebot3_burger.urdf (aruco_marker_link resized to 0.12)
        │  import_turtlebot3  →  turtlebot3_burger.usda (shared asset)
        ▼
scenario_builder._author_robot()  → per-robot material override on aruco_marker_link
        ▼
USD scenario stage → Isaac render → /camera/image_raw → M1 detection
```

### 1. Marker generation — `scripts/generate_aruco_markers.py`

- Dev-venv script (mirrors `scripts/generate_obstacle_windows.py`, but runs in the project
  venv — it needs `cv2.aruco`, not guaranteed in Isaac's embedded interpreter).
- **Reads the dictionary name from M1's `aruco.yaml`** (`aruco.dictionary`), not hardcoded,
  so generator and M1 cannot desync. Map the name → `cv2.aruco` predefined constant (e.g.
  `DICT_4X4_50` → `cv2.aruco.DICT_4X4_50`) via a small lookup; fail loudly on an unsupported
  name.
- For each id in `1..49`:
  `cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(<dict>), id, side_px)`
  with a white quiet-zone border ≥ 1 module (ArUco requires it). `side_px` default `512`
  (texture resolution, independent of physical size). Output square PNGs to
  `isaac/assets/markers/<dict_slug>/marker_<id>.png`, where `<dict_slug>` is **derived from
  the configured dictionary name** (e.g. `DICT_4X4_50` → `aruco_4x4_50`) — the directory is
  not hardcoded, so it tracks the config. Idempotent; committed.
- **API verification at implementation:** confirm `generateImageMarker` (OpenCV ≥ 4.7; older
  builds use `drawMarker`) against the pinned `opencv-contrib-python`.

### 2. URDF — reposition the marker mount above the lidar

- In `turtlebot3_burger.urdf`, **raise `aruco_marker_joint` above the lidar**: change its
  origin from `z = 0.10` to **`z ≈ 0.21`** (clear of the lidar top — `base_scan` at 0.172
  plus the `lds.stl` extent; verify the exact clearance against the mesh). The tag becomes
  the topmost prim, so a nadir camera sees it unoccluded. This is realistic — warehouse
  robots mount the fiducial on a top plate above all sensors. (Offsetting in x/y instead was
  rejected: a 0.12 m tag barely fits the 0.14 m base, so it can't clear the lidar laterally.)
- **Do not rely on texturing the URDF `<box>`.** A thin imported box has no guaranteed
  planar UVs, so a material override could render a solid/garbled image. Treat
  `aruco_marker_link` as a **mount frame only** — remove its `<box>` visual (or leave it
  unused) and author an explicit UV-mapped quad in USD (§3).
- The marker height is therefore a **property of the robot asset** (the joint origin), not
  scenario config. (This supersedes the earlier "per-scenario config knob" idea; if
  per-scenario variation is ever needed, override the marker prim's transform in
  `_author_robot` — deferred, YAGNI.) Physical size lives in the authored quad (§3), set to
  0.12 m.
- `turtlebot3_burger.usda` must be generated from the edited URDF via `import_turtlebot3`
  (runs in Isaac). The `.usda` is not currently present, so import is a required step
  regardless — **and gated on the Prerequisites below.**

### 2a. Prerequisites for a successful import (acceptance criteria)

These are pre-existing M6 robot-import blockers that sit directly in this work's path; the
ArUco work cannot be validated until they pass.

- **Xacro expansion (decided: commit a pre-expanded `.urdf`).** The current file contains
  `xmlns:xacro`, `<xacro:arg/property name="namespace">`, and `${namespace}` substitutions,
  but `import_turtlebot3.py` only runs `xacro` when the input suffix is `.xacro`. Run `xacro`
  once and **commit a clean `turtlebot3_burger.urdf`** with no `xacro`/`${...}` constructs
  (namespace resolved to empty); that committed file is the source of truth and the import
  script works unchanged. Acceptance: the imported file contains no `xacro`/`${...}` tokens.
- **Mesh resolution (decided: vendor the STLs).** All visuals reference
  `package://turtlebot3_description/meshes/*.stl`, not in this repo. **Vendor all four
  referenced STLs** (`burger_base`, `left_tire`, `right_tire`, `lds`) under
  `isaac/assets/robots/turtlebot3_burger/` and
  rewrite the `<mesh filename>` paths to local references (relative or `file://`). Acceptance:
  a clean import resolves every mesh with no missing-asset warnings, with no dependency on a
  `turtlebot3_description` ROS package.

### 3. Scene authoring — `isaac/vgu_sim/scenario_builder.py`

The imported `turtlebot3_burger.usda` is **shared by every robot**, so the marker geometry
and texture cannot be baked into the asset — both are authored per-robot. In
`_author_robot()`, after referencing the robot USD, author under the robot's
`aruco_marker_link` (`/World/Robots/<robot_id>/.../aruco_marker_link`):

- **An explicit marker quad** — a `UsdGeom.Mesh` with 4 verts / 1 face, lying in the XY
  plane (normal +Z), scaled to **0.12 m**, with **explicit `st` (UV) primvars** mapping the
  texture 1:1 onto the face. Authoring the quad ourselves (rather than texturing the imported
  URDF box) guarantees correct, decode-ready UVs.
- **A per-id `UsdShade.Material`** with a `UsdUVTexture` reading `marker_<marker_id>.png`,
  connected to **`emissiveColor`** of a `UsdPreviewSurface` (`diffuseColor` black,
  `roughness` 1, `metallic` 0). Emissive makes the black/white contrast lighting-independent
  — important at this pixel budget. Texture wrap = clamp. Bound to the quad.
- Authored at the per-robot prim path (as an `over`/child of the referenced asset) so each
  robot gets its own marker without touching the shared asset. Texture path resolved relative
  to the scenario stage (reuse `_relative_path`). Position/orientation come from the
  `aruco_marker_link` frame (raised above the lidar per §2).
- **API verification at implementation:** confirm `UsdGeom.Mesh` `st` primvar authoring and
  the `UsdShade` `emissiveColor` connection against Isaac Sim 6.0 / USD before writing.

### 4. M1 config alignment — `ros2_ws/src/swarm_perception/config/aruco.yaml`

- Change `aruco.marker_size_m` from `0.08` to **`0.12`** so all three sources agree. M1 does
  **not** consume `marker_size_m` today (grep-confirmed), so this is hygiene against a future
  pose-scale (`solvePnP`) trap, not a runtime change. This is the only M1-side edit.

### 5. Paths & validation

- Add the marker asset directory to `paths.py` (alongside robot/obstacle asset paths).
- `validation.py`: assert each robot has the **authored marker quad child** under
  `aruco_marker_link` (not the link itself), that the quad carries an `st` primvar, and that
  it has a bound material referencing a texture file that exists on disk. Fail-fast
  `ValidationError`, matching existing stage validation. The runner already calls
  `_validate_stage` before stepping, so a missing/broken marker surfaces at run start.

---

## Testing

1. **Generation-script unit test** (`tests/unit/`): generating writes exactly ids 1..49;
   output is deterministic (same bytes on re-run); each PNG is a valid square of the expected
   side; the dictionary name is taken from `aruco.yaml`. Real `cv2.aruco`, offline.

2. **Full clean-image round-trip parity test** (`tests/unit/`, offline, no Isaac): for
   **every** generated `marker_<id>.png`, place it on a plain background at a realistic size
   and feed it through M1's `swarm_perception.detection`; assert it recovers **the dictionary
   configured in `aruco.yaml`** (not a hardcoded literal) and the **correct id** for all ids.
   Cheap proof that generation ↔ M1 agree on dictionary and id mapping, independent of the
   simulator.

3. **Scene-authoring validation test** (`tests/`): unit-test `_author_robot` against a stub
   stage; assert the per-robot marker quad exists, has usable **`st` primvars**, binds the
   right `marker_<id>.png` via an emissive material, and that `validation.py` rejects a stage
   whose marker mesh/material/texture is missing or whose mesh lacks `st`. Mirrors the
   existing scenario_builder / validation test approach (no live Isaac).

4. **Import prerequisite checks** (acceptance, not unit): the URDF handed to the importer
   contains no `xacro`/`${...}` constructs, and a clean import resolves every mesh with no
   missing-asset warnings (§2a). These gate the on-sim run; verify on the Isaac machine.

---

## Risks & open items

- **Detectability (accepted risk):** ~4–4.5 px/module at 0.12 m / default camera. The
  round-trip test proves dictionary/id parity on clean images but **not** that detection
  survives the rendered overhead view at this pixel budget. First on-sim validation (camera
  frame → M1 → non-empty `SceneState.robots`) is the real check; the deferred lever on
  failure is a camera retune.
- **Occlusion (addressed):** marker raised above the lidar (§2). Still verify on first render
  that nothing (lidar mesh, antennas) clips the tag from the nadir view.
- **Xacro/mesh import gating:** §2a must pass before any marker work can be validated on-sim;
  treat as a prerequisite milestone, not part of the marker authoring itself. (Approach
  decided: pre-expanded `.urdf` + vendored STLs.)
- **Lighting:** emissive binding mitigates wash-out; confirm on first render.
- **`robot_id` naming mismatch:** M1 keys robots by marker-derived id; Isaac names robots
  independently. Flagged for a separate task.
- **OpenCV / USD API drift:** `generateImageMarker` and the `UsdShade` emissive binding are
  version-sensitive and will be verified against the pinned libs / Isaac 6.0 before coding
  (per CLAUDE.md external-library-verification).
- **Importer prim naming:** the mesh prim path under `aruco_marker_link` depends on the URDF
  importer; located programmatically at authoring time, not hardcoded.

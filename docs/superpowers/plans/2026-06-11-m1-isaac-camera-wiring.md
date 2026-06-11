# M1 ↔ Isaac Sim Camera Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a correct intrinsics `K` and pixel→world homography `H` from the live `isaac/vgu_sim` `CameraConfig`, write them into `swarm_perception`'s `calibration.yaml`, and prove M1's world-frame output matches Isaac ground truth.

**Architecture:** A pure-math module `isaac/vgu_sim/calibration.py` turns a `CameraConfig` into a YAML-serializable calibration dict (no `omni`/`pxr`, Mac-runnable). A thin CLI `isaac/scripts/export_calibration.py` writes it to the package config. The homography is derived from the full projective model (camera pose → ground-plane z=0 mapping, inverted), verified by a synthetic round-trip test that collapses to the closed-form nadir formulas.

**Tech Stack:** Python, NumPy, Pydantic (existing `CameraConfig`), PyYAML, pytest. Reuses `swarm_perception.calibration.load_calibration` and `swarm_perception.pipeline.process_frame`.

**Design spec:** `docs/superpowers/specs/2026-06-11-m1-isaac-camera-wiring-design.md`

---

## Background an implementer needs

**The camera (single source of truth):** `isaac/vgu_sim/config.py::CameraConfig` — a frozen Pydantic model. Construct the default with `CameraConfig()`. Relevant fields: `width=1280`, `height=960`, `position_m=(0.0, 0.0, 3.0)`, `orientation_quat_wxyz=(1.0,0.0,0.0,0.0)` (nadir), `focal_length_mm=10.48`, `horizontal_aperture_mm=20.955`, `vertical_aperture_mm=15.716`.

**The target file:** `ros2_ws/src/swarm_perception/config/calibration.yaml`. Its schema (consumed by `swarm_perception.calibration.load_calibration`) requires exactly these keys: `intrinsics` (3×3 list), `distortion` (length-5 list), `homography` (3×3 list), `image_size` ([w, h]), `source_id` (non-empty str), `created_at` (float ≥ 0). Today it ships an **identity** homography and placeholder intrinsics — that is the bug.

**The math (derived, do not re-derive):**

Intrinsics:
```
fx = focal_length_mm / horizontal_aperture_mm * width
fy = focal_length_mm / vertical_aperture_mm   * height
cx = width / 2
cy = height / 2
K  = [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
```

Homography (general projective form, valid for any pose; collapses to nadir):
```
R_cw   = quat_to_rotation_matrix(orientation_quat_wxyz)   # camera-local axes → world
R_wc   = R_cw.T                                            # world → camera-local (USD: +X right, +Y up, −Z forward)
R_flip = diag(1, -1, -1)                                   # USD camera coords → OpenCV coords (+X right, +Y down, +Z forward)
M      = K @ R_flip @ R_wc
C      = array(position_m)
H_w2p  = column_stack([ M[:,0], M[:,1], -(M @ C) ])        # world-plane (X,Y,1) → pixel
H      = inv(H_w2p); H = H / H[2,2]                        # pixel → world (X,Y)
```

Quaternion (w,x,y,z) → rotation matrix:
```
R = [[1-2(y²+z²),   2(xy-wz),   2(xz+wy)],
     [  2(xy+wz), 1-2(x²+z²),   2(yz-wx)],
     [  2(xz-wy),   2(yz+wx), 1-2(x²+y²)]]
```

**Independent oracle for tests (nadir closed form, h = position z, Cx=Cy=0):**
```
u = cx + fx * X / h          X = (u - cx) * h / fx
v = cy - fy * Y / h          Y = (cy - v) * h / fy
```
Tests use this closed form to check the general-projective implementation — a wrong sign or axis swap fails immediately, on the Mac.

**Determinism:** the calibration is *analytic*, not captured, so `created_at` is a fixed constant `0.0` (sentinel meaning "derived, not time-stamped"). This makes regeneration byte-stable.

**Import boundary:** `isaac/vgu_sim/calibration.py` must NOT import `swarm_perception` (keeps the sim package decoupled from M1). It returns a plain dict; tests load it back through `swarm_perception.calibration.load_calibration` to prove schema compatibility.

**Run tests with:** `python -m pytest <path> -v` from the repo root.

---

## File Structure

- **Create** `isaac/vgu_sim/calibration.py` — pure functions: `camera_intrinsics`, `_quat_to_rotation_matrix`, `pixel_to_world_homography`, `build_calibration_dict`. No `omni`/`pxr`/`swarm_perception` imports.
- **Create** `isaac/scripts/export_calibration.py` — CLI writing `calibration.yaml` from `CameraConfig`.
- **Modify** `ros2_ws/src/swarm_perception/config/calibration.yaml` — regenerated (real K + H).
- **Create** `tests/unit/test_isaac_calibration.py` — unit + integration tests.
- **Modify** `isaac/vgu_sim/validation.py` — add `calibration_position_error` helper.
- **Modify** `docs/specs/module6_simulation.md` OR design spec — add the in-sim validation procedure (Task 6 documents where).

---

## Task 1: Intrinsics from CameraConfig

**Files:**
- Create: `isaac/vgu_sim/calibration.py`
- Test: `tests/unit/test_isaac_calibration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_isaac_calibration.py
import math

import numpy as np
import pytest

from isaac.vgu_sim.calibration import camera_intrinsics
from isaac.vgu_sim.config import CameraConfig


def test_camera_intrinsics_matches_focal_aperture_resolution():
    cfg = CameraConfig()
    k = camera_intrinsics(cfg)

    fx = cfg.focal_length_mm / cfg.horizontal_aperture_mm * cfg.width
    fy = cfg.focal_length_mm / cfg.vertical_aperture_mm * cfg.height
    assert k.shape == (3, 3)
    assert math.isclose(k[0, 0], fx, rel_tol=1e-12)
    assert math.isclose(k[1, 1], fy, rel_tol=1e-12)
    assert math.isclose(k[0, 2], cfg.width / 2, rel_tol=1e-12)
    assert math.isclose(k[1, 2], cfg.height / 2, rel_tol=1e-12)
    assert k[2, 2] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_isaac_calibration.py::test_camera_intrinsics_matches_focal_aperture_resolution -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'isaac.vgu_sim.calibration'`

- [ ] **Step 3: Write minimal implementation**

```python
# isaac/vgu_sim/calibration.py
"""Analytic camera calibration derived from the live CameraConfig.

Pure math: no Isaac (`omni`/`pxr`) and no `swarm_perception` imports, so this
runs and is fully unit-testable on any host (e.g. macOS).
"""
from __future__ import annotations

import numpy as np

from isaac.vgu_sim.config import CameraConfig


def camera_intrinsics(config: CameraConfig) -> np.ndarray:
    """Build the 3x3 pinhole intrinsics matrix from the camera config.

    Args:
        config: Overhead camera configuration.

    Returns:
        The 3x3 intrinsics matrix `K`.
    """
    fx = config.focal_length_mm / config.horizontal_aperture_mm * config.width
    fy = config.focal_length_mm / config.vertical_aperture_mm * config.height
    cx = config.width / 2.0
    cy = config.height / 2.0
    return np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_isaac_calibration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/calibration.py tests/unit/test_isaac_calibration.py
git commit -m "feat: derive overhead camera intrinsics from CameraConfig"
```

---

## Task 2: Pixel→world homography

**Files:**
- Modify: `isaac/vgu_sim/calibration.py`
- Test: `tests/unit/test_isaac_calibration.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_isaac_calibration.py`:

```python
from isaac.vgu_sim.calibration import pixel_to_world_homography


def _nadir_world_to_pixel(cfg, x, y):
    """Independent oracle: closed-form nadir projection (world -> pixel)."""
    fx = cfg.focal_length_mm / cfg.horizontal_aperture_mm * cfg.width
    fy = cfg.focal_length_mm / cfg.vertical_aperture_mm * cfg.height
    cx, cy = cfg.width / 2.0, cfg.height / 2.0
    h = cfg.position_m[2]
    u = cx + fx * x / h
    v = cy - fy * y / h
    return u, v


def _apply_h(h_mat, u, v):
    """Map a pixel through a 3x3 pixel->world homography to (X, Y)."""
    p = h_mat @ np.array([u, v, 1.0])
    return p[0] / p[2], p[1] / p[2]


def test_homography_origin_maps_to_image_center():
    cfg = CameraConfig()
    h_mat = pixel_to_world_homography(cfg)
    x, y = _apply_h(h_mat, cfg.width / 2.0, cfg.height / 2.0)
    assert abs(x) < 1e-9
    assert abs(y) < 1e-9


def test_homography_round_trip_over_roi():
    cfg = CameraConfig()
    h_mat = pixel_to_world_homography(cfg)
    xs = np.linspace(-cfg.roi_width_m / 2, cfg.roi_width_m / 2, 5)
    ys = np.linspace(-cfg.roi_depth_m / 2, cfg.roi_depth_m / 2, 5)
    for x in xs:
        for y in ys:
            u, v = _nadir_world_to_pixel(cfg, x, y)
            xr, yr = _apply_h(h_mat, u, v)
            assert abs(xr - x) < 1e-6, f"X at ({x},{y}) -> {xr}"
            assert abs(yr - y) < 1e-6, f"Y at ({x},{y}) -> {yr}"


def test_homography_one_meter_x_offset_pixel_shift():
    cfg = CameraConfig()
    fx = cfg.focal_length_mm / cfg.horizontal_aperture_mm * cfg.width
    h = cfg.position_m[2]
    u0, _ = _nadir_world_to_pixel(cfg, 0.0, 0.0)
    u1, _ = _nadir_world_to_pixel(cfg, 1.0, 0.0)
    assert abs((u1 - u0) - fx / h) < 1e-9
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_isaac_calibration.py -v -k homography`
Expected: FAIL — `ImportError: cannot import name 'pixel_to_world_homography'`

- [ ] **Step 3: Write the implementation**

Add to `isaac/vgu_sim/calibration.py`:

```python
def _quat_to_rotation_matrix(quat_wxyz: tuple[float, float, float, float]) -> np.ndarray:
    """Convert a (w, x, y, z) unit quaternion to a 3x3 rotation matrix.

    The rotation maps camera-local axes into world axes (camera-to-world).
    """
    w, x, y, z = quat_wxyz
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def pixel_to_world_homography(config: CameraConfig) -> np.ndarray:
    """Compute the pixel->world (ground plane z=0) homography for the camera.

    Uses the full projective model so a tilted mount (non-identity
    `orientation_quat_wxyz`) yields a valid homography; for the default nadir
    pose it reduces to the closed-form overhead mapping.

    Args:
        config: Overhead camera configuration.

    Returns:
        The 3x3 homography `H` mapping pixel `(u, v, 1)` to world `(X, Y, 1)`.
    """
    k = camera_intrinsics(config)
    r_cw = _quat_to_rotation_matrix(config.orientation_quat_wxyz)
    r_wc = r_cw.T
    r_flip = np.diag([1.0, -1.0, -1.0])  # USD camera coords -> OpenCV coords
    m = k @ r_flip @ r_wc
    cam_center = np.array(config.position_m, dtype=np.float64)
    h_w2p = np.column_stack([m[:, 0], m[:, 1], -(m @ cam_center)])
    h_p2w = np.linalg.inv(h_w2p)
    return h_p2w / h_p2w[2, 2]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_isaac_calibration.py -v`
Expected: PASS (all four tests)

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/calibration.py tests/unit/test_isaac_calibration.py
git commit -m "feat: derive pixel-to-world homography from camera pose"
```

---

## Task 3: Assemble the calibration dict

**Files:**
- Modify: `isaac/vgu_sim/calibration.py`
- Test: `tests/unit/test_isaac_calibration.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_isaac_calibration.py`:

```python
from isaac.vgu_sim.calibration import ANALYTIC_CREATED_AT, build_calibration_dict


def test_build_calibration_dict_has_required_schema_keys():
    cfg = CameraConfig()
    d = build_calibration_dict(cfg)
    assert set(d.keys()) == {
        "intrinsics",
        "distortion",
        "homography",
        "image_size",
        "source_id",
        "created_at",
    }
    assert np.array(d["intrinsics"]).shape == (3, 3)
    assert np.array(d["homography"]).shape == (3, 3)
    assert d["distortion"] == [0.0, 0.0, 0.0, 0.0, 0.0]
    assert d["image_size"] == [cfg.width, cfg.height]
    assert d["source_id"] == "isaac_sim"
    assert d["created_at"] == ANALYTIC_CREATED_AT


def test_build_calibration_dict_homography_not_identity():
    d = build_calibration_dict(CameraConfig())
    assert not np.allclose(np.array(d["homography"]), np.eye(3))


def test_build_calibration_dict_is_deterministic():
    assert build_calibration_dict(CameraConfig()) == build_calibration_dict(CameraConfig())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_isaac_calibration.py -v -k build_calibration_dict`
Expected: FAIL — `ImportError: cannot import name 'build_calibration_dict'`

- [ ] **Step 3: Write the implementation**

Add to `isaac/vgu_sim/calibration.py`:

```python
# Analytic calibration is derived, not captured, so it carries a fixed
# timestamp sentinel. This keeps regenerated calibration.yaml byte-stable.
ANALYTIC_CREATED_AT = 0.0


def build_calibration_dict(config: CameraConfig) -> dict[str, object]:
    """Build a YAML-serializable calibration mapping for `swarm_perception`.

    The returned dict matches the schema consumed by
    `swarm_perception.calibration.load_calibration`.

    Args:
        config: Overhead camera configuration.

    Returns:
        Mapping with intrinsics, distortion, homography, image_size, source_id,
        and created_at.
    """
    k = camera_intrinsics(config)
    h_mat = pixel_to_world_homography(config)
    return {
        "intrinsics": k.tolist(),
        "distortion": [0.0, 0.0, 0.0, 0.0, 0.0],
        "homography": h_mat.tolist(),
        "image_size": [config.width, config.height],
        "source_id": "isaac_sim",
        "created_at": ANALYTIC_CREATED_AT,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_isaac_calibration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add isaac/vgu_sim/calibration.py tests/unit/test_isaac_calibration.py
git commit -m "feat: assemble swarm_perception calibration dict from CameraConfig"
```

---

## Task 4: Export CLI + regenerate calibration.yaml

**Files:**
- Create: `isaac/scripts/export_calibration.py`
- Modify: `ros2_ws/src/swarm_perception/config/calibration.yaml`
- Test: `tests/unit/test_isaac_calibration.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_isaac_calibration.py`. This test verifies the written
YAML loads through M1's own loader and is non-identity:

```python
def test_exported_yaml_loads_via_swarm_perception(tmp_path):
    import yaml

    from isaac.vgu_sim.calibration import build_calibration_dict

    out = tmp_path / "calibration.yaml"
    out.write_text(yaml.safe_dump(build_calibration_dict(CameraConfig())))

    swarm_perception = pytest.importorskip("swarm_perception.calibration")
    artifact = swarm_perception.load_calibration(out)
    assert artifact.image_size == (1280, 960)
    assert not np.allclose(artifact.homography, np.eye(3))
    assert artifact.source_id == "isaac_sim"
```

- [ ] **Step 2: Run test to verify it fails or skips**

Run: `python -m pytest tests/unit/test_isaac_calibration.py::test_exported_yaml_loads_via_swarm_perception -v`
Expected: PASS if `swarm_perception` is importable, else SKIP. (It exercises only existing code; this guards the YAML contract before we add the CLI.)

- [ ] **Step 3: Write the CLI**

```python
# isaac/scripts/export_calibration.py
"""CLI: write swarm_perception's calibration.yaml from the live CameraConfig.

Runs anywhere (pure math, no Isaac Sim required):

    python -m isaac.scripts.export_calibration
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from isaac.vgu_sim.calibration import build_calibration_dict
from isaac.vgu_sim.config import CameraConfig

DEFAULT_OUTPUT = Path("ros2_ws/src/swarm_perception/config/calibration.yaml")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export overhead-camera calibration.yaml")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = build_calibration_dict(CameraConfig())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=True)
    print(f"Calibration written to: {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Regenerate the real calibration file**

Run: `python -m isaac.scripts.export_calibration`
Expected output: `Calibration written to: ros2_ws/src/swarm_perception/config/calibration.yaml`

Then verify it is no longer identity:
Run: `python -c "from swarm_perception.calibration import load_calibration as L; import numpy as np; a=L('ros2_ws/src/swarm_perception/config/calibration.yaml'); print('homography identity?', np.allclose(a.homography, np.eye(3)))"`
Expected: `homography identity? False`

(If `swarm_perception` is not importable in your shell, source the ROS2 workspace or run from an environment where `tests/unit/test_perception.py` already imports it.)

- [ ] **Step 5: Run the full calibration test file**

Run: `python -m pytest tests/unit/test_isaac_calibration.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add isaac/scripts/export_calibration.py ros2_ws/src/swarm_perception/config/calibration.yaml tests/unit/test_isaac_calibration.py
git commit -m "feat: export analytic calibration.yaml and regenerate it"
```

---

## Task 5: Integration test through the real M1 pipeline

**Files:**
- Test: `tests/unit/test_isaac_calibration.py`

This proves the generated calibration flows correctly through
`swarm_perception.pipeline.process_frame`. It mocks ArUco detection to return a
marker at a known pixel, then asserts the resulting `RobotState.(x, y)` matches
the **independent nadir oracle** (not the generated `H`).

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_isaac_calibration.py`:

```python
def test_known_pixel_marker_maps_to_expected_world_point(monkeypatch, tmp_path):
    import yaml

    pytest.importorskip("cv2")
    pipeline = pytest.importorskip("swarm_perception.pipeline")
    sp_cal = pytest.importorskip("swarm_perception.calibration")
    models = pytest.importorskip("swarm_perception.models")
    estimator_mod = pytest.importorskip("swarm_perception.state_estimator")

    from isaac.vgu_sim.calibration import build_calibration_dict

    cfg = CameraConfig()
    out = tmp_path / "calibration.yaml"
    out.write_text(yaml.safe_dump(build_calibration_dict(cfg)))
    calibration = sp_cal.load_calibration(out)

    # Put a small square marker centered 100 px right and 60 px below center.
    u_c, v_c = cfg.width / 2.0 + 100, cfg.height / 2.0 + 60
    half = 10.0
    corners = np.array(
        [
            [u_c - half, v_c - half],
            [u_c + half, v_c - half],
            [u_c + half, v_c + half],
            [u_c - half, v_c + half],
        ],
        dtype=np.float64,
    )

    def fake_detect(image, dictionary_name="DICT_4X4_50", detector_params=None):
        return [7], [corners]

    monkeypatch.setattr(pipeline, "detect_aruco_markers", fake_detect)

    frame = models.Frame(
        image=np.zeros((cfg.height, cfg.width, 3), dtype=np.uint8),
        stamp=1.0,
        frame_id="overhead_camera",
        source_id="isaac_sim",
    )
    est = estimator_mod.StateEstimator(velocity_alpha=1.0)
    scene_state, _ = pipeline.process_frame(frame, calibration, est)

    # Independent oracle: nadir inverse projection of the marker center.
    fx = cfg.focal_length_mm / cfg.horizontal_aperture_mm * cfg.width
    fy = cfg.focal_length_mm / cfg.vertical_aperture_mm * cfg.height
    h = cfg.position_m[2]
    exp_x = (u_c - cfg.width / 2.0) * h / fx
    exp_y = (cfg.height / 2.0 - v_c) * h / fy

    assert len(scene_state.robots) == 1
    robot = scene_state.robots[0]
    assert abs(robot.x - exp_x) < 1e-3
    assert abs(robot.y - exp_y) < 1e-3
```

- [ ] **Step 2: Run test to verify it fails (or guides you)**

Run: `python -m pytest tests/unit/test_isaac_calibration.py::test_known_pixel_marker_maps_to_expected_world_point -v`
Expected: Initially may FAIL if the mocked `detect_aruco_markers` return shape or robot-id mapping differs. Inspect `swarm_perception/pipeline.py` `process_frame` and `detection.py` to confirm the `(ids, corners)` contract and how a marker id becomes `RobotState.robot_id`; adjust `fake_detect`'s return and the assertion (`scene_state.robots[0]`) to match. The world-coordinate assertion itself must pass unchanged — that is the real check.

- [ ] **Step 3: Make it pass**

Align the mock with the real detection contract discovered in Step 2 (the
function name to patch, the return tuple shape, and how `id=7` surfaces as a
robot). Do not weaken the `exp_x`/`exp_y` tolerance.

- [ ] **Step 4: Run the full file**

Run: `python -m pytest tests/unit/test_isaac_calibration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_isaac_calibration.py
git commit -m "test: verify calibration through M1 process_frame pipeline"
```

---

## Task 6: In-sim validation helper + documented procedure

**Files:**
- Modify: `isaac/vgu_sim/validation.py`
- Test: `tests/unit/test_m6_validation.py`
- Modify: `docs/superpowers/specs/2026-06-11-m1-isaac-camera-wiring-design.md`

The unit/integration tests prove the math offline. This task adds the helper and
the written procedure for the on-Isaac (Windows) end-to-end check.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_m6_validation.py`:

```python
def test_calibration_position_error_euclidean():
    from isaac.vgu_sim.validation import calibration_position_error

    err = calibration_position_error(measured=(1.03, -0.46), ground_truth=(1.0, -0.5))
    assert abs(err - 0.05) < 1e-9


def test_calibration_position_error_zero_on_match():
    from isaac.vgu_sim.validation import calibration_position_error

    assert calibration_position_error((2.0, 3.0), (2.0, 3.0)) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_m6_validation.py -v -k calibration_position_error`
Expected: FAIL — `ImportError: cannot import name 'calibration_position_error'`

- [ ] **Step 3: Write the helper**

Add to `isaac/vgu_sim/validation.py`:

```python
def calibration_position_error(
    measured: tuple[float, float],
    ground_truth: tuple[float, float],
) -> float:
    """Euclidean distance (meters) between a measured and ground-truth XY pose.

    Args:
        measured: M1-reported world `(x, y)` for a robot.
        ground_truth: Isaac ground-truth world `(x, y)` for the same robot.

    Returns:
        The position error in meters.
    """
    dx = measured[0] - ground_truth[0]
    dy = measured[1] - ground_truth[1]
    return (dx * dx + dy * dy) ** 0.5
```

(Place it near the existing validation helpers; match the file's import style —
add `import math` only if you prefer `math.hypot`, otherwise the inline form
above needs no new imports.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_m6_validation.py -v -k calibration_position_error`
Expected: PASS

- [ ] **Step 5: Document the procedure**

Append a "## 7. In-sim validation procedure (runbook)" section to
`docs/superpowers/specs/2026-06-11-m1-isaac-camera-wiring-design.md` with:

```markdown
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
```

- [ ] **Step 6: Commit**

```bash
git add isaac/vgu_sim/validation.py tests/unit/test_m6_validation.py docs/superpowers/specs/2026-06-11-m1-isaac-camera-wiring-design.md
git commit -m "feat: add calibration position-error helper and in-sim runbook"
```

---

## Task 7: Full regression

**Files:** none (verification only)

- [ ] **Step 1: Run the whole unit suite**

Run: `python -m pytest tests/unit -q`
Expected: all pass (the new `test_isaac_calibration.py` tests plus the existing
133, minus none removed). No regressions in `test_perception.py` or
`test_m6_*.py`.

- [ ] **Step 2: Lint**

Run: `ruff check isaac/vgu_sim/calibration.py isaac/scripts/export_calibration.py tests/unit/test_isaac_calibration.py`
Expected: no errors.

- [ ] **Step 3: Final commit (if lint produced fixes)**

```bash
git add -A
git commit -m "chore: lint calibration module"
```

---

## Self-Review notes (spec coverage)

- Spec §3 (intrinsics K) → Task 1. ✅
- Spec §4.2 (homography H, projective + nadir collapse, axis convention) → Task 2. ✅
- Spec §3 architecture (calibration dict, no swarm_perception import, determinism) → Task 3. ✅
- Spec §3 (`isaac/scripts/export_calibration.py`, regenerate calibration.yaml) → Task 4. ✅
- Spec §5.1 (unit: round-trip, spot checks, determinism, K-consistency) → Tasks 1–3. ✅
- Spec §5.2 (integration through process_frame) → Task 5. ✅
- Spec §5.3 (in-sim validation procedure + oracle helper) → Task 6. ✅
- Spec §5.4 (error handling / CalibrationError) → see note below.
- Spec §6 acceptance criteria 1–5 → Tasks 4, 2, 5, 6, 3 respectively. ✅

**Note on Spec §5.4 (CameraConfig validation):** `CameraConfig` is a frozen
Pydantic model whose fields are already constrained at construction, so invalid
apertures/height cannot reach `build_calibration_dict`. The spec's
`CalibrationError`-on-invalid-config requirement is therefore satisfied upstream
by Pydantic validation; no extra guard is added (YAGNI). If `CameraConfig` ever
loosens those constraints, add an explicit check in `build_calibration_dict`.
```

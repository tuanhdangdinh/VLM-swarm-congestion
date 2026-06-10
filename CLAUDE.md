# CLAUDE.md

**Prepared:** 2026-06-05

**Revision history:**

- Initial draft: architecture overview, file layout, commands, and development standards for Claude Code.
- Rev 2 (2026-06-10): reformatted to follow `docs/standards/doc_style.md`.

---

## Project Overview

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**VGU VLM Swarm** is a ROS2-based research scaffold for warehouse swarm coordination using a hybrid two-layer architecture:

- **Layer 1 (Fast, 20–50 Hz):** Local reactive control. M4 (ROS2 execution) dispatches Nav2 commands to robots.
- **Layer 2 (Slow, 0.5–2 Hz):** Centralized semantic reasoning. M2 (VLM) analyzes the scene and detects congestion; M3 (RAG) grounds that decision into concrete commands; M5 (Orchestrator) manages the pipeline and task registry.

The five-module architecture:

- **M1 Perception & Robot ID Tracking:** Converts overhead camera frames → robot state vectors (world-frame position, velocity, status) + annotated frame for M2.
- **M2 VLM Semantic Reasoning:** Analyzes scene image + state → detects congestion type and recommends strategy (yield, reroute, convoy, etc.).
- **M3 RAG Action Grounding:** Translates semantic decision → concrete command via LLM + vector-store retrieval.
- **M4 ROS2 Execution & Safety:** Dispatches commands, runs per-robot client, enforces safety invariants (min distance, speed limits).
- **M5 Orchestrator:** Central state machine. Owns task/status registry; triggers M2→M3→M4 pipeline on congestion timeout.

**M1 (Perception)** is fully implemented. Start here to understand the pattern: modular functions in `swarm_perception/`, Pydantic models for contracts, ROS2 node integration in `perception_node.py`.

---

## File Layout

```text
.
├── ros2_ws/                          # ROS2 workspace (colcon build here)
│   └── src/
│       ├── swarm_perception/         # M1: camera, calibration, ArUco, state est., annotation
│       │   ├── swarm_perception/     # Package code
│       │   │   ├── models.py         # Pydantic contracts
│       │   │   ├── geometry.py       # Homography transforms
│       │   │   ├── calibration.py    # Camera calibration
│       │   │   ├── detection.py      # ArUco marker detection
│       │   │   ├── state_estimator.py # Robot tracking
│       │   │   ├── annotation.py     # Scene annotation
│       │   │   ├── pipeline.py       # End-to-end process_frame
│       │   │   ├── perception_node.py # ROS2 PerceptionNode
│       │   │   └── camera_node.py    # ROS2 CameraNode
│       │   ├── launch/               # ROS2 launch configs
│       │   ├── config/               # Calibration, ArUco, camera params
│       │   ├── setup.py              # ament_python build config
│       │   └── package.xml           # ROS2 dependencies
│       ├── swarm_interfaces/         # Shared ROS2 messages
│       ├── swarm_orchestrator/       # M5: state machine, task registry
│       └── swarm_simulation/         # M6: Isaac Sim ROS-facing launch, scenarios
│
├── reasoning/                        # Non-ROS2 Python (M2, M3)
│   ├── vlm/                          # M2: VLM backend adapters, prompt builder
│   ├── rag/                          # M3: knowledge base, retriever, grounding
│   └── schemas/                      # Shared JSON schemas
│
├── tests/                            # Test suites
│   ├── unit/                         # Unit tests (offline)
│   ├── integration/                  # Integration tests (ROS2)
│   └── simulation/                   # Scenario tests
│
├── docs/                             # Design docs, specs
├── config/                           # Central configuration
├── data/                             # Calibration, knowledge base, logs
├── benchmarks/                       # Baseline planners, metrics
└── scripts/                          # Shell helpers
```

---

## Common Commands

### Python & Unit Tests

```bash
# Setup (one-time)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Run all tests
make test

# Run a single test file
pytest tests/unit/test_perception.py

# Run a single test function
pytest tests/unit/test_perception.py::TestStateEstimatorUpdate::test_frame_id_override

# Lint
make lint
```

### ROS2 Build & Launch

```bash
# Build all ROS2 packages
make build-ros2

# Build a single package
colcon build --packages-select swarm_perception

# Run perception stack (M1 only)
ros2 launch swarm_perception perception.launch.py

# Run with external camera source (Isaac Sim bridge)
ros2 launch swarm_perception perception.launch.py use_camera_node:=false

# Run full simulation
./scripts/run_simulation.sh
```

---

## M1 Perception — Architecture Essentials

### Data Flow

1. **Camera:** Frame from `FrameSource` → undistorted via intrinsics.
2. **Detection:** ArUco markers → `MarkerDetection` (world-frame position, heading).
3. **State Estimation:** Track robots, estimate velocity, inject task/status.
4. **Annotation:** Draw status-colored boxes, velocity arrows, goals.
5. **Output:** `SceneState` (robots + diagnostics) and annotated frame → M2, M5.

### Pydantic Contracts

All cross-module data use immutable Pydantic v2 models with field validators:

- **`Frame`** — RGB image `(H, W, 3)`, stamp, frame_id, source_id.
- **`CalibrationArtifact`** — intrinsics `(3,3)`, homography `(3,3)`, distortion, image_size.
- **`MarkerDetection`** — marker_id, corner_pixels `(4,2)`, center_world, theta, confidence.
- **`RobotState`** — robot_id, x, y, theta, linear_velocity, angular_velocity, task, status (MOVING/SLOW/STOPPED/STALE), goal, stamp.
- **`SceneState`** — stamp, frame_id, robots[], diagnostics{}.

**Key invariant:** `RobotState.stamp ≤ SceneState.stamp`. Late frames (stamp < last_stamp) are suppressed and return an empty robot list with `dropped_frame=True`.

### ROS2 Integration

**PerceptionNode** subscribes to `/camera/image_raw` (sensor_msgs/Image), publishes:

- `/perception/scene_state` (JSON string of SceneState)
- `/perception/annotated_frame` (sensor_msgs/Image RGB bytes)
- `/perception/status` (JSON diagnostics)

Subscribes to:

- `/coordination/tasks` (JSON task registry from M5)

**Fail-fast startup checks:**

- Calibration file exists and is valid YAML mapping.
- Marker dictionary is supported.

---

## Development Standards

### Type Hints

Every public function must have full type hints. Use `X | Y` not `Optional[X]`. Use built-in generics (`list[str]`, `dict[str, int]`), not `typing.List`, etc.

```python
def classify_motion_status(
    linear_velocity: float,
    age_sec: float,
    stopped_threshold_mps: float,
    slow_threshold_mps: float,
    stale_after_sec: float,
) -> Literal["MOVING", "SLOW", "STOPPED", "STALE"]:
    ...
```

### Imports

Order as: stdlib, third-party, then local, with one blank line between groups.

```python
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from swarm_perception.geometry import pixel_to_world
```

### Docstrings

Use Google style on every public function and class:

```python
def pixel_to_world(pixel: tuple[float, float], homography: np.ndarray) -> tuple[float, float]:
    """Transform one pixel coordinate into world-frame meters.

    Args:
        pixel: Pixel coordinate as `(u, v)`.
        homography: Matrix mapping image coordinates to world coordinates.

    Returns:
        World coordinate as `(x, y)` in meters.
    """
```

### Module Boundaries

Keep ownership clear:

- M1 perception → `ros2_ws/src/swarm_perception`
- M2 VLM → `reasoning/vlm`
- M3 RAG → `reasoning/rag`
- M4 execution → `ros2_ws/src/swarm_execution`
- M5 orchestration → `ros2_ws/src/swarm_orchestrator`
- M6 simulation → `ros2_ws/src/swarm_simulation` and `benchmarks`

### Scope & Discipline

Do exactly what the task asks. Do not refactor unrelated modules, change topic names without updating specs, or add external dependencies without documenting why.

### ROS2 Code

Keep node callbacks thin. Convert ROS2 messages to internal models, call pure functions, then publish results. Put reusable logic outside node classes when it can be tested without ROS2.

### Error Handling

- Public boundary functions may raise documented errors (`CalibrationError`, `ValueError`, `FileNotFoundError`).
- Runtime failures from external systems should appear in diagnostics or result objects, not crash the node.
- Do not swallow exceptions silently.

### Tests

- Name tests `test_<behavior>_<condition>`.
- Test one behavior per function.
- Mock external systems (ROS2 runtime, OpenCV, VLM servers) in unit tests.
- Mark or document integration tests so they are not confused with fast unit tests.

### Commit Messages

Use Conventional Commits: `type: summary`. Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. Subject line under 72 characters. No body; reasoning belongs in PR or spec.

---

## Important Gotchas

1. **Single camera assumption:** M1 assumes overhead camera. Multi-camera fusion is out of scope.

2. **Task registry ownership:** M5 owns the registry. M1.3 reads tasks/goals but doesn't write. Status (MOVING/SLOW/STOPPED/STALE) is derived locally, never from registry.

3. **Homography ground-plane-only:** We don't compute full 6-DOF pose. Heading is derived from ArUco corner ordering after homography.

4. **FrameSource abstraction:** Hardware, Isaac Sim bridge, Gazebo, or video all implement the protocol. StateEstimator is frame-source-agnostic.

5. **Late frames suppressed:** Out-of-order frames with `stamp < _last_stamp` are dropped (return empty robot list, `dropped_frame=True`). M2/M5 must tolerate occasional missing frames.

6. **Package vs runtime deps:** Package.xml declares ROS deps; setup.py declares Python runtime deps. This keeps rosdep clean and local dev simple.

---

## References

- **Module decomposition:** `docs/modules.md`
- **M1 implementation spec:** `docs/specs/module1_perception.md`
- **Coding standards:** `docs/standards/coding_style.md`
- **Documentation standards:** `docs/standards/doc_style.md`
- **Shared schemas:** `reasoning/schemas/`

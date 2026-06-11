# CLAUDE.md

**Prepared:** 2026-06-05

**Revision history:**

- Initial draft: architecture overview, file layout, commands, and development standards for Claude Code.
- Rev 2 (2026-06-10): reformatted to follow `docs/standards/doc_style.md`.
- Rev 3 (2026-06-11): synced Development Standards with `docs/standards/coding_style.md`; added `isaac/` to File Layout; expanded Module Boundaries, Error Handling, ROS2, Logging, Pydantic, OpenCV, VLM/RAG, Dependencies, Secrets, and External Library Verification sections.

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
│       └── swarm_simulation/         # M6: ROS2-facing launch, scenarios, maps
│
├── isaac/                            # M6: Isaac Sim Python runtime (runs inside Isaac Sim's embedded Python)
│   ├── vgu_sim/                      # Scene builder, USD authoring, OmniGraph wiring
│   ├── assets/                       # USD and mesh assets
│   ├── scenarios/                    # Scenario configs consumed by vgu_sim
│   ├── scripts/                      # Standalone runner and helpers
│   └── config/                       # Isaac Sim runtime configuration
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

Every public function and method signature must have full type hints. Use `X | Y`, not `Optional[X]` or `Union[X, Y]`. Use built-in generics (`list[str]`, `dict[str, int]`, `tuple[float, float]`), not `typing.List`, etc. Use `Protocol` for pluggable boundaries such as `FrameSource` and `VLMBackend`. Private helpers may omit type hints only when the surrounding code remains obvious and local.

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

### Pydantic Models

Use Pydantic v2 for module contracts that cross package, ROS2, logging, or backend boundaries.

```python
class RobotStateInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    x: float
    y: float
    theta: float
```

Rules:

- Use `ConfigDict(frozen=True)` for immutable data contracts.
- Add `arbitrary_types_allowed=True` when a model contains `np.ndarray`.
- Use `field_validator` for array shapes, enum normalization, and schema invariants.
- Use `.model_dump(mode="json")` for JSON-safe serialization.
- Do not pass raw provider responses or ROS2 message objects across reasoning module boundaries; convert them into Pydantic models or plain dicts first.

### Imports

Order as: stdlib, third-party, then local, with one blank line between groups. No wildcard imports. Re-export intentionally public APIs from `__init__.py`. Do not import private helpers from sibling modules.

```python
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from swarm_perception.geometry import pixel_to_world
```

### Docstrings

Use Google style on every public function and class. One-line summary first, ending with a period. Blank line between summary and `Args`. Add `Raises` only when the function deliberately raises as part of its public contract. Private helpers do not need docstrings unless they encode a non-obvious algorithm.

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
- M6 simulation → `ros2_ws/src/swarm_simulation` (ROS2 launch/config), `isaac/vgu_sim` (Isaac Sim scene authoring), and `benchmarks`

### Scope & Discipline

Do exactly what the task asks. Do not:

- Refactor unrelated modules while implementing one module.
- Change ROS2 topic names without updating specs and launch/config files.
- Change shared schemas without checking downstream consumers.
- Add a VLM backend without keeping it behind the backend interface.
- Add external dependencies without documenting why.
- Reformat generated files or simulator assets unless the task requires it.

### ROS2 Code

Keep node callbacks thin. Convert ROS2 messages to internal models, call pure functions, then publish results. Put reusable logic outside node classes when it can be tested without ROS2. Use explicit topic names from specs/config — do not hardcode alternate names in source. Use launch/config files for parameters such as camera topic, marker dictionary, thresholds, model endpoint, and safety limits. Message definitions in `swarm_interfaces` are shared contracts; update specs, tests, and consumers when changing them. Avoid blocking VLM/RAG calls inside high-rate perception or safety callbacks.

### OpenCV and Geometry

- Treat camera frames as RGB at M1 boundaries. Convert to BGR only at OpenCV drawing/detection boundaries, and convert back before publishing.
- Use `opencv-contrib-python` when `cv2.aruco` is needed.
- Normalize OpenCV ArUco corner arrays to shape `(4, 2)` before constructing `MarkerDetection`.
- Keep coordinate conventions explicit: pixel coordinates as `(u, v)`, world coordinates as `(x, y)` in meters, heading in radians in the world frame.
- Homography helpers must document direction: pixel-to-world or world-to-pixel.

### VLM and RAG Code

- Keep VLM providers pluggable behind `VLMBackend`.
- Backend-specific code owns HTTP payloads, auth, image encoding, and provider response parsing into `BackendResponse`.
- Prompt building, retry policy, output parsing, and decision validation must remain backend-agnostic.
- Use `temperature=0.0` for classification workloads unless a spec says otherwise.
- Validate VLM output with Pydantic before forwarding it to M3 or M5.
- Do not log base64 images, secrets, or full provider payloads unless a debugging artifact is explicitly requested.

### Error Handling

- Public boundary functions may raise documented errors (`CalibrationError`, `FrameSourceTimeoutError`, `ValueError`, `FileNotFoundError`).
- Runtime failures from external systems should appear in diagnostics or result objects, not crash the node.
- M1 per-frame detection failures should appear in diagnostics, not crash the node.
- M2 backend/model failures should return `ReasonerResult(decision=None)` after bounded retries; invalid caller inputs may raise before backend invocation.
- Do not swallow exceptions silently.

### Logging

- Prefer structured key-value logging for ROS2 node events and reasoning traces.
- Include `request_id`, `frame_id`, `robot_id`, `backend_id`, or `command_id` when available.
- Do not log secrets, API keys, raw `.env` contents, or full base64 image data.
- Keep VLM reasoning traces in explicit JSONL/debug artifacts when needed, not in high-rate ROS2 logs.

### Comments

Comments explain why a non-obvious constraint exists; do not restate the code. Avoid section-divider comments.

### Tests

- Unit-test pure logic first: geometry, homography, state estimation, schema validation, VLM output parsing, and command grounding.
- Mock external systems (ROS2 runtime, Isaac Sim, HTTP VLM servers, ChromaDB, model APIs) in unit tests.
- Integration tests may exercise ROS2 nodes or local VLM servers, but must be marked or documented so they are not confused with fast unit tests.
- Name tests `test_<behavior>_<condition>`.
- Test one behavior per function.

### Dependencies

- Python runtime dependencies go in `pyproject.toml` and `requirements.txt`.
- ROS2 package dependencies go in each package's `package.xml`.
- Optional heavyweight dependencies should remain optional until the module that requires them is implemented.
- Do not assume `uv` is available. Use `make` commands unless a task requires a lower-level command.

### Secrets and Local Paths

- Never commit `.env`, API keys, tokens, or private model credentials.
- Read secrets from environment variables.
- Do not hardcode local absolute paths to model files, Isaac Sim installs, or datasets. Put placeholders in config and document required environment setup.

### External Library Verification

Before implementing against version-sensitive APIs, verify current official docs or primary repositories. This applies especially to:

- Isaac Sim ROS2 camera helpers.
- OpenCV ArUco APIs.
- ROS2 message and launch APIs.
- llama.cpp `llama-server`.
- NVIDIA Cosmos Reason2.
- ChromaDB and embedding libraries.

Record important setup facts in the relevant spec or setup document.

### Commit Messages

Use Conventional Commits: `type: summary`. Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. Subject line under 72 characters. No body; reasoning belongs in the PR description, spec, or module implementation report. No `Co-Authored-By` trailer.

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

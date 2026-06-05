# Coding Style Guide

---

## Tooling

- **Python version:** 3.10 or newer.
- **Formatter/linter:** Ruff, configured in `pyproject.toml`.
- **Tests:** `pytest` for pure Python tests.
- **ROS2 build:** `colcon build` through `make build-ros2`.
- **Standard commands:**
  - `make lint`
  - `make test`
  - `make build-ros2`
- **Dependency files:** update `pyproject.toml`, `requirements.txt`, and ROS2
  `package.xml` files when adding runtime dependencies.

Do not assume `uv` is available. Use the project Makefile commands unless a task
requires a lower-level command.

---

## Project Boundaries

The repository has three main implementation areas:

- `ros2_ws/src/` - ROS2 packages for interfaces, perception, execution,
  orchestration, and simulation.
- `reasoning/` - VLM, RAG, schemas, and non-ROS reasoning utilities.
- `config/`, `docs/`, `benchmarks/`, `scripts/`, `tests/` - shared configuration,
  documentation, evaluation, automation, and tests.

Keep module ownership clear:

- M1 perception code lives under `swarm_perception`.
- M2 VLM reasoning code lives under `reasoning/vlm`.
- M3 RAG grounding code lives under `reasoning/rag`.
- M4 execution and safety code lives under `swarm_execution`.
- M5 orchestration code lives under `swarm_orchestrator`.
- M6 simulation assets live under `swarm_simulation` and `benchmarks`.

---

## Scope

Do exactly what the task asks. Do not:

- Refactor unrelated modules while implementing one module.
- Change ROS2 topic names without updating specs and launch/config files.
- Change shared schemas without checking downstream consumers.
- Add a VLM backend without keeping it behind the backend interface.
- Add external dependencies without documenting why.
- Reformat generated files or simulator assets unless the task requires it.

---

## Type Hints

Every public function and method signature must have full type hints.

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

Rules:

- Use `X | Y`; do not use `Optional[X]` or `Union[X, Y]`.
- Use `list[str]`, `dict[str, int]`, and `tuple[float, float]`; do not use
  `List`, `Dict`, or `Tuple` from `typing`.
- Use `Protocol` for pluggable boundaries such as `FrameSource` and
  `VLMBackend`.
- Private helpers may omit type hints only when the surrounding code remains
  obvious and local.

---

## Pydantic Models

Use Pydantic v2 for module contracts that cross package, ROS2, logging, or
backend boundaries.

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
- Use `field_validator` for array shapes, enum normalization, and schema
  invariants.
- Use `.model_dump(mode="json")` for JSON-safe serialization.
- Do not pass raw provider responses or ROS2 message objects across reasoning
  module boundaries; convert them into Pydantic models or plain dicts first.

---

## ROS2 Code

- Keep ROS2 node callbacks thin. Convert ROS2 messages to internal models, call
  pure functions/classes, then publish results.
- Put reusable logic outside node classes whenever it can be tested without ROS2.
- Use explicit topic names from specs/config. Do not hardcode alternate names in
  source files.
- Use launch/config files for parameters such as camera topic, marker dictionary,
  thresholds, model endpoint, and safety limits.
- Message definitions in `swarm_interfaces` are shared contracts. Update specs,
  tests, and consumers when changing them.
- Avoid blocking VLM/RAG calls inside high-rate perception or safety callbacks.

---

## OpenCV and Geometry

- Treat camera frames as RGB at M1 boundaries. Convert to BGR only at OpenCV
  drawing/detection boundaries when required, and convert back before publishing
  RGB outputs.
- Use `opencv-contrib-python` when `cv2.aruco` is needed.
- Normalize OpenCV ArUco corner arrays to shape `(4, 2)` before constructing
  `MarkerDetection`.
- Keep coordinate conventions explicit:
  - pixel coordinates: `(u, v)`
  - world coordinates: `(x, y)` in meters
  - heading: radians in the world frame
- Homography helpers must document direction: pixel-to-world or world-to-pixel.

---

## VLM and RAG Code

- Keep VLM providers pluggable behind `VLMBackend`.
- Backend-specific code owns HTTP payloads, auth, image encoding, and provider
  response parsing into `BackendResponse`.
- Prompt building, retry policy, output parsing, and decision validation must
  remain backend-agnostic.
- Use deterministic defaults for classification workloads: `temperature=0.0`
  unless a spec says otherwise.
- Validate VLM output with Pydantic before forwarding it to M3 or M5.
- Do not log base64 images, secrets, or full provider payloads unless a debugging
  artifact is explicitly requested.

---

## Imports

Order imports as stdlib, third-party, then local, with one blank line between
groups.

```python
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from swarm_perception.geometry import pixel_to_world
```

Rules:

- No wildcard imports.
- Re-export intentionally public APIs from `__init__.py`.
- Do not import private helpers from sibling modules.

---

## Error Handling

- Public boundary functions may raise documented configuration or contract errors
  such as `CalibrationError`, `FrameSourceTimeoutError`, `ValueError`, or
  `FileNotFoundError`.
- Runtime failures from external systems should be converted into diagnostics or
  failure result objects when the caller can continue safely.
- M1 per-frame detection failures should appear in diagnostics, not crash the
  node.
- M2 backend/model failures should return `ReasonerResult(decision=None)` after
  bounded retries; invalid caller inputs may raise before backend invocation.
- Do not swallow exceptions silently.

---

## Logging

- Prefer structured key-value logging for ROS2 node events and reasoning traces.
- Event strings should be short and static.
- Include `request_id`, `frame_id`, `robot_id`, `backend_id`, or `command_id`
  when available.
- Do not log secrets, API keys, raw `.env` contents, or full base64 image data.
- Keep VLM reasoning traces in explicit JSONL/debug artifacts when needed, not
  in high-rate ROS2 logs.

---

## Comments and Docstrings

- Comments explain why a non-obvious constraint exists; do not restate the code.
- Avoid section-divider comments.
- Public functions and classes use Google-style docstrings.
- Private helpers do not need docstrings unless they encode a non-obvious
  algorithm or convention.

---

## Tests

- Unit-test pure logic first: geometry, homography, state estimation, schema
  validation, VLM output parsing, and command grounding.
- Mock external systems in unit tests: ROS2 runtime, Isaac Sim, HTTP VLM servers,
  ChromaDB, and model APIs.
- Integration tests may exercise ROS2 nodes, simulated camera streams, or local
  VLM servers, but they must be marked or documented so they are not confused
  with fast unit tests.
- Name tests `test_<behavior>_<condition>`.
- Test one behavior per test function.

---

## Dependencies

- Python runtime dependencies go in `pyproject.toml` and `requirements.txt`.
- ROS2 package dependencies go in each package's `package.xml`.
- Optional heavyweight dependencies should remain optional until the module that
  requires them is implemented.
- Prefer official packages and primary project docs when adding dependencies.

---

## Secrets and Local Paths

- Never commit `.env`, API keys, tokens, or private model credentials.
- Read secrets from environment variables.
- Do not hardcode local absolute paths to model files, Isaac Sim installs, or
  datasets. Put placeholders in config and document required environment setup.

---

## External Library Verification

Before implementing against version-sensitive APIs, verify current official docs
or primary repositories. This applies especially to:

- Isaac Sim ROS2 camera helpers.
- OpenCV ArUco APIs.
- ROS2 message and launch APIs.
- llama.cpp `llama-server`.
- NVIDIA Cosmos Reason2.
- ChromaDB and embedding libraries.

Record important setup facts in the relevant spec or setup document.

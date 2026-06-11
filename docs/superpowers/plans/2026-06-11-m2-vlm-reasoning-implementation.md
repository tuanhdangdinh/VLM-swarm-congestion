# M2 VLM Reasoning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the `reasoning/vlm/` code in line with the existing spec `docs/specs/module2_vlm_reasoning.md` — a stateless `Reasoner.run` pipeline (prompt → backend → parse → validate → retry/re-ask) behind a pluggable `VLMBackend` Protocol.

**Architecture:** M2 is a stateless request/response service. `Reasoner.run(ReasonerRequest) -> ReasonerResult` orchestrates a pure prompt builder, a timeout-guarded backend call, a tolerant JSON parser, and referential-integrity validation, with a bounded retry/re-ask loop. Backends (`MockBackend`, `LlamaServerBackend`) sit behind a `VLMBackend` Protocol and are selected by a factory. No ROS2, no M3 calls.

**Tech Stack:** Python 3.11, Pydantic v2, `requests`, `jsonschema` (legacy path), `concurrent.futures` (stdlib timeout), pytest.

---

## Context for the Engineer

You are implementing M2 of a ROS2 warehouse-swarm research scaffold. M2 takes an annotated overhead image + robot states from M1 and asks a Vision-Language Model whether congestion exists, classifies it, and recommends a strategy. The **spec is authoritative**: `docs/specs/module2_vlm_reasoning.md`. Read §7 (Function Specifications), §8 (Prompt Templates), and §11 (Error Handling) before starting.

**Current state of `reasoning/vlm/` (mid-migration):**
- `models.py` — has all Pydantic models already (`ReasonerRequest`, `PromptPayload`, `CongestionDecision`, `BackendResponse`, `ReasonerDiagnostics`, `ReasonerResult`, `ReasonerConfig`, `LlamaServerBackendConfig`). One mismatch: `LlamaServerBackendConfig.model_path` is required in code but absent from the spec. Fix in Task 1.
- `backend_base.py` — **stale**: defines `VLMBackend` as an ABC with `analyze(request: VLMRequest)`. No external consumers. Replace with a Protocol in Task 2.
- `prompt_builder.py` — **legacy only**: `build_scene_prompt() -> str`. No external consumers. Replace in Task 3.
- `output_parser.py` — has legacy `parse_vlm_decision() -> dict` and `VLMOutputParseError`. Keep both; add new functions in Tasks 4–5.
- `llama_server_backend.py` — already matches the spec's `analyze(payload, config) -> BackendResponse` signature and has `is_ready`. Minor alignment in Task 9.
- `__init__.py` — bare docstring. Add re-exports in Task 10.

**Conventions (from CLAUDE.md):**
- Type hints on every public signature. Use `X | Y`, built-in generics.
- Pydantic v2 with `ConfigDict(frozen=True)`.
- Google-style docstrings on public functions/classes.
- Imports: stdlib, third-party, local — one blank line between groups.
- Conventional Commits: `type: summary`, ≤72 chars, no body, no `Co-Authored-By`.
- Run `make lint` and `make test` before declaring done.

**Test commands:**
- Single test: `pytest tests/unit/test_reasoner.py::test_name -v`
- M2 unit suite: `pytest tests/unit/test_vlm_output_parser.py tests/unit/test_prompt_builder.py tests/unit/test_reasoner.py tests/unit/test_validate_involved_robots.py -v`
- Full suite: `make test`

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `reasoning/vlm/models.py` | All Pydantic data contracts | Modify (Task 1) |
| `reasoning/vlm/backend_base.py` | `VLMBackend` Protocol | Replace (Task 2) |
| `reasoning/vlm/prompt_builder.py` | `build_prompt_payload`, `format_robot_state_lines` | Replace (Task 3) |
| `reasoning/vlm/output_parser.py` | `parse_decision_text`, `validate_involved_robots`, exceptions, legacy `parse_vlm_decision` | Modify (Tasks 4–5) |
| `reasoning/vlm/mock_backend.py` | `MockBackend` deterministic test backend | Create (Task 6) |
| `reasoning/vlm/reasoner.py` | `Reasoner`, `invoke_backend`, `build_reask_prompt`, `build_failed_result`, `write_reasoner_log` | Create (Tasks 7–8) |
| `reasoning/vlm/backend_factory.py` | `build_backend` factory | Create (Task 9) |
| `reasoning/vlm/llama_server_backend.py` | llama.cpp HTTP adapter | Modify (Task 9) |
| `reasoning/vlm/__init__.py` | Public re-exports | Modify (Task 10) |
| `tests/unit/test_prompt_builder.py` | Prompt builder tests | Create (Task 3) |
| `tests/unit/test_vlm_output_parser.py` | Parser tests | Extend (Task 4) |
| `tests/unit/test_validate_involved_robots.py` | Referential-integrity tests | Create (Task 5) |
| `tests/unit/test_reasoner.py` | Reasoner orchestration tests | Create (Tasks 6–8) |

---

## Task 1: Reconcile `LlamaServerBackendConfig` with the spec

**Files:**
- Modify: `reasoning/vlm/models.py`
- Test: `tests/unit/test_reasoner.py` (create with one config test)

The spec's `LlamaServerBackendConfig` (§7.1) has no `model_path` field, but `config/models.yaml` includes one. Pydantic ignores unknown keys by default (no `extra="forbid"`), so we make `model_path` an optional documented field rather than a required one, keeping config loading working with or without it.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_reasoner.py`:

```python
from reasoning.vlm.models import LlamaServerBackendConfig


def test_llama_config_loads_without_model_path():
    config = LlamaServerBackendConfig(model_id="cosmos-reason2-8b")
    assert config.base_url == "http://127.0.0.1:8080/v1"
    assert config.model_path is None
    assert config.mmproj_path is None


def test_llama_config_accepts_optional_paths():
    config = LlamaServerBackendConfig(
        model_id="cosmos-reason2-8b",
        model_path="/models/cosmos.gguf",
        mmproj_path="/models/mmproj.gguf",
    )
    assert config.model_path == "/models/cosmos.gguf"
    assert config.mmproj_path == "/models/mmproj.gguf"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_reasoner.py::test_llama_config_loads_without_model_path -v`
Expected: FAIL — `ValidationError` (model_path currently required with `min_length=1`).

- [ ] **Step 3: Make `model_path` optional**

In `reasoning/vlm/models.py`, change the `LlamaServerBackendConfig` body:

```python
class LlamaServerBackendConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str = "http://127.0.0.1:8080/v1"
    model_id: str = Field(min_length=1)
    model_path: str | None = None  # server-startup concern; not used per-request
    mmproj_path: str | None = None  # path to mmproj GGUF for vision; None = text-only
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_reasoner.py -v`
Expected: PASS (both config tests).

- [ ] **Step 5: Commit**

```bash
git add reasoning/vlm/models.py tests/unit/test_reasoner.py
git commit -m "refactor: make LlamaServerBackendConfig.model_path optional"
```

---

## Task 2: Replace the stale `VLMBackend` ABC with a Protocol

**Files:**
- Replace: `reasoning/vlm/backend_base.py`
- Test: `tests/unit/test_reasoner.py` (add a structural test)

The current `backend_base.py` defines an ABC with an obsolete `analyze(request: VLMRequest)` signature that nothing uses. Replace the whole file with the spec's Protocol (§7.6), whose method is `analyze(payload: PromptPayload, config: ReasonerConfig) -> BackendResponse`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_reasoner.py`:

```python
from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig


def test_vlmbackend_is_runtime_checkable_protocol():
    class Dummy:
        def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
            return BackendResponse(text="{}", backend_id="dummy")

    assert isinstance(Dummy(), VLMBackend)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_reasoner.py::test_vlmbackend_is_runtime_checkable_protocol -v`
Expected: FAIL — current `VLMBackend` is an ABC (not runtime-checkable Protocol); `isinstance` against it without registration raises `TypeError` or returns False.

- [ ] **Step 3: Replace the file**

Overwrite `reasoning/vlm/backend_base.py`:

```python
from typing import Protocol, runtime_checkable

from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig


@runtime_checkable
class VLMBackend(Protocol):
    """Common interface for pluggable VLM providers.

    Implementations own HTTP/transport, image encoding, and provider response
    parsing into a `BackendResponse`. Prompt building and output parsing stay
    backend-agnostic.
    """

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Run one VLM call and return the raw model output.

        Args:
            payload: Fully-rendered system/user prompt and image reference.
            config: Runtime decoding settings (temperature, max_tokens, timeout).

        Returns:
            Backend response carrying the raw assistant text and metadata.
        """
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_reasoner.py::test_vlmbackend_is_runtime_checkable_protocol -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add reasoning/vlm/backend_base.py tests/unit/test_reasoner.py
git commit -m "refactor: replace VLMBackend ABC with runtime-checkable Protocol"
```

---

## Task 3: Implement the prompt builder

**Files:**
- Replace: `reasoning/vlm/prompt_builder.py`
- Test: `tests/unit/test_prompt_builder.py` (create)

Implement `format_robot_state_lines` and `build_prompt_payload` per spec §7.4 and the templates in §8.1–§8.2. Replace the legacy `build_scene_prompt` (no consumers).

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_prompt_builder.py`:

```python
import json

from reasoning.vlm.models import ReasonerRequest, RobotStateInput
from reasoning.vlm.prompt_builder import (
    SYSTEM_PROMPT,
    build_prompt_payload,
    format_robot_state_lines,
)


def _request() -> ReasonerRequest:
    return ReasonerRequest(
        request_id="req-1",
        image_path="/tmp/frame.png",
        frame_id="overhead_camera",
        stamp=12.5,
        robot_states=[
            RobotStateInput(robot_id="robot_2", x=1.0, y=2.0, theta=1.57, status="MOVING"),
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
        ],
    )


def test_format_robot_state_lines_includes_required_fields():
    lines = format_robot_state_lines([RobotStateInput(robot_id="robot_1", x=1.2, y=0.4, theta=1.57)])
    assert lines == ["robot_id=robot_1, x=1.20, y=0.40, theta=1.57"]


def test_format_robot_state_lines_appends_optional_fields_when_present():
    lines = format_robot_state_lines(
        [RobotStateInput(robot_id="robot_1", x=1.2, y=0.4, theta=1.57, status="MOVING", task="deliver_A", linear_velocity=0.15, angular_velocity=0.0)]
    )
    assert lines == [
        "robot_id=robot_1, x=1.20, y=0.40, theta=1.57, status=MOVING, task=deliver_A, linear_velocity=0.15, angular_velocity=0.00"
    ]


def test_build_prompt_payload_sorts_robots_and_collects_ids():
    payload = build_prompt_payload(_request())
    assert payload.known_robot_ids == ["robot_1", "robot_2"]
    # robot_1 line appears before robot_2 line (sorted)
    assert payload.user_prompt.index("robot_id=robot_1") < payload.user_prompt.index("robot_id=robot_2")


def test_build_prompt_payload_is_deterministic():
    assert build_prompt_payload(_request()).user_prompt == build_prompt_payload(_request()).user_prompt


def test_build_prompt_payload_uses_fixed_system_prompt():
    assert build_prompt_payload(_request()).system_prompt == SYSTEM_PROMPT


def test_build_prompt_payload_embeds_known_ids_json():
    payload = build_prompt_payload(_request())
    assert json.dumps(["robot_1", "robot_2"]) in payload.user_prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_prompt_builder.py -v`
Expected: FAIL — `ImportError` (`SYSTEM_PROMPT`, `build_prompt_payload`, `format_robot_state_lines` not defined).

- [ ] **Step 3: Replace `prompt_builder.py`**

Overwrite `reasoning/vlm/prompt_builder.py`:

```python
import json

from reasoning.vlm.models import PromptPayload, ReasonerRequest, RobotStateInput

SYSTEM_PROMPT = (
    "You are a warehouse swarm robotics traffic controller.\n"
    "Your task is to analyze overhead camera views of autonomous mobile robots\n"
    "and detect congestion patterns such as deadlocks, bottlenecks, crowding,\n"
    "and anomalies. You always respond with only valid JSON — no other text."
)

_USER_TEMPLATE = """Analyze the overhead warehouse scene for congestion or deadlock.

Robot states (sorted by ID):
{robot_state_block}

Known robot IDs: {known_robot_ids_json}

Return ONLY a JSON object with exactly these fields:
{{
  "congestion_detected": <true|false>,
  "type": <"none"|"deadlock"|"bottleneck"|"crowding"|"anomaly">,
  "involved_robots": [<robot_id strings, must be from known IDs only>],
  "root_cause": "<one sentence>",
  "strategy": <"none"|"yield"|"reroute"|"convoy"|"priority_override"|"temporary_wait"|"reverse">,
  "justification": "<one or two sentences>"
}}

Rules:
- Only use robot IDs from the known list above.
- When congestion_detected is false: type must be "none", strategy must be "none", involved_robots must be [].
- Return ONLY the JSON object. Do not include any text, markdown, or explanation."""


def format_robot_state_lines(robot_states: list[RobotStateInput]) -> list[str]:
    """Render robot states as deterministic key=value lines for the prompt.

    Args:
        robot_states: Robot states to render (caller sorts beforehand).

    Returns:
        One comma-separated line per robot; optional fields omitted when None.
    """
    lines: list[str] = []
    for state in robot_states:
        parts = [
            f"robot_id={state.robot_id}",
            f"x={state.x:.2f}",
            f"y={state.y:.2f}",
            f"theta={state.theta:.2f}",
        ]
        if state.status is not None:
            parts.append(f"status={state.status}")
        if state.task is not None:
            parts.append(f"task={state.task}")
        if state.linear_velocity is not None:
            parts.append(f"linear_velocity={state.linear_velocity:.2f}")
        if state.angular_velocity is not None:
            parts.append(f"angular_velocity={state.angular_velocity:.2f}")
        lines.append(", ".join(parts))
    return lines


def build_prompt_payload(request: ReasonerRequest) -> PromptPayload:
    """Build a deterministic, fully-rendered prompt payload from a request.

    Args:
        request: Validated reasoning request from M5/M1.

    Returns:
        Frozen `PromptPayload` with fixed system prompt and dynamic user prompt.
    """
    sorted_states = sorted(request.robot_states, key=lambda s: s.robot_id)
    known_ids = [s.robot_id for s in sorted_states]
    lines = format_robot_state_lines(sorted_states)
    block = "\n".join(f"- {line}" for line in lines) or "- no robots observed"
    user_prompt = _USER_TEMPLATE.format(
        robot_state_block=block,
        known_robot_ids_json=json.dumps(known_ids),
    )
    return PromptPayload(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        image_path=request.image_path,
        known_robot_ids=known_ids,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_prompt_builder.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add reasoning/vlm/prompt_builder.py tests/unit/test_prompt_builder.py
git commit -m "feat: add deterministic VLM prompt payload builder"
```

---

## Task 4: Implement `parse_decision_text` and decision exceptions

**Files:**
- Modify: `reasoning/vlm/output_parser.py`
- Test: `tests/unit/test_vlm_output_parser.py` (extend)

Add the tolerant Pydantic parser per spec §7.5, the `DecisionValidationError` and `BackendTimeoutError` exception classes (§7.5 "Exception Classes"), while keeping the legacy `parse_vlm_decision` and existing `VLMOutputParseError` untouched.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_vlm_output_parser.py`:

```python
from reasoning.vlm.output_parser import (
    DecisionValidationError,
    parse_decision_text,
)

_VALID = """```json
{
  "congestion_detected": true,
  "type": "deadlock",
  "involved_robots": ["robot_1", "robot_1", "robot_2"],
  "root_cause": "head-on aisle conflict",
  "strategy": "yield",
  "justification": "robot_1 has a clearer retreat path"
}
```"""


def test_parse_decision_text_strips_code_fence_and_dedupes():
    decision = parse_decision_text(_VALID)
    assert decision.type == "deadlock"
    assert decision.involved_robots == ["robot_1", "robot_2"]


def test_parse_decision_text_extracts_json_from_prose():
    text = 'Here is my answer: {"congestion_detected": false, "type": "none", "involved_robots": [], "root_cause": "clear", "strategy": "none", "justification": "empty scene"}'
    decision = parse_decision_text(text)
    assert decision.congestion_detected is False


def test_parse_decision_text_rejects_bad_enum():
    text = '{"congestion_detected": true, "type": "jam", "involved_robots": ["robot_1"], "root_cause": "x", "strategy": "yield", "justification": "y"}'
    with pytest.raises(VLMOutputParseError):
        parse_decision_text(text)


def test_parse_decision_text_rejects_invariant_violation():
    text = '{"congestion_detected": false, "type": "deadlock", "involved_robots": [], "root_cause": "x", "strategy": "none", "justification": "y"}'
    with pytest.raises(VLMOutputParseError):
        parse_decision_text(text)


def test_parse_decision_text_rejects_false_with_involved_robots():
    text = '{"congestion_detected": false, "type": "none", "involved_robots": ["robot_1"], "root_cause": "x", "strategy": "none", "justification": "y"}'
    with pytest.raises(VLMOutputParseError):
        parse_decision_text(text)


def test_parse_decision_text_rejects_non_json():
    with pytest.raises(VLMOutputParseError):
        parse_decision_text("no json here")
```

Add `DecisionValidationError` to the import on line 5 only after Step 3 exists; for now this import drives the failure.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_vlm_output_parser.py -v`
Expected: FAIL — `ImportError` (`DecisionValidationError`, `parse_decision_text` not defined).

- [ ] **Step 3: Extend `output_parser.py`**

Add to `reasoning/vlm/output_parser.py`. First add imports `import re` (top, stdlib group) and `from reasoning.vlm.models import CongestionDecision`. Add the exception classes after `VLMOutputParseError`:

```python
class DecisionValidationError(ValueError):
    """Raised when a parsed decision references unknown robot IDs."""


class BackendTimeoutError(RuntimeError):
    """Raised by invoke_backend when the backend call exceeds timeout_sec."""
```

Then add the parser function:

```python
def parse_decision_text(text: str) -> CongestionDecision:
    """Extract JSON from raw VLM text and validate it as a CongestionDecision.

    Tolerates markdown code fences and surrounding prose. Enforces the
    no-congestion invariant and deduplicates involved_robots.

    Args:
        text: Raw assistant text from a VLM backend.

    Returns:
        Validated, normalized decision.

    Raises:
        VLMOutputParseError: On JSON decode failure, schema violation, or a
            self-contradictory no-congestion decision.
    """
    candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.DOTALL)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise VLMOutputParseError("VLM output contains no JSON object.")
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise VLMOutputParseError(f"VLM output is not valid JSON: {exc}") from exc

    try:
        decision = CongestionDecision(**parsed)
    except (TypeError, ValidationError) as exc:
        raise VLMOutputParseError(f"VLM output failed schema validation: {exc}") from exc

    if not decision.congestion_detected:
        if decision.type != "none" or decision.strategy != "none" or decision.involved_robots:
            raise VLMOutputParseError(
                "congestion_detected=false requires type='none', strategy='none', "
                "involved_robots=[]."
            )

    deduped: list[str] = []
    for robot_id in decision.involved_robots:
        if robot_id not in deduped:
            deduped.append(robot_id)
    return decision.model_copy(update={"involved_robots": deduped})
```

Add `from pydantic import ValidationError` to the third-party import group.

- [ ] **Step 4: Update the test import line**

Ensure the top of `tests/unit/test_vlm_output_parser.py` imports both legacy and new symbols:

```python
from reasoning.vlm.output_parser import (
    DecisionValidationError,
    VLMOutputParseError,
    parse_decision_text,
    parse_vlm_decision,
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_vlm_output_parser.py -v`
Expected: PASS (2 legacy + 6 new).

- [ ] **Step 6: Commit**

```bash
git add reasoning/vlm/output_parser.py tests/unit/test_vlm_output_parser.py
git commit -m "feat: add tolerant CongestionDecision parser with invariant checks"
```

---

## Task 5: Implement `validate_involved_robots`

**Files:**
- Modify: `reasoning/vlm/output_parser.py`
- Test: `tests/unit/test_validate_involved_robots.py` (create)

Per spec §7.5: every ID in `involved_robots` must exist in the known set.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_validate_involved_robots.py`:

```python
import pytest

from reasoning.vlm.models import CongestionDecision
from reasoning.vlm.output_parser import (
    DecisionValidationError,
    validate_involved_robots,
)


def _decision(involved: list[str], detected: bool = True) -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=detected,
        type="deadlock" if detected else "none",
        involved_robots=involved,
        root_cause="x",
        strategy="yield" if detected else "none",
        justification="y",
    )


def test_validate_involved_robots_accepts_known_ids():
    validate_involved_robots(_decision(["robot_1"]), {"robot_1", "robot_2"})


def test_validate_involved_robots_rejects_unknown_id():
    with pytest.raises(DecisionValidationError):
        validate_involved_robots(_decision(["robot_9"]), {"robot_1"})


def test_validate_involved_robots_accepts_empty_when_no_congestion():
    validate_involved_robots(_decision([], detected=False), {"robot_1"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_validate_involved_robots.py -v`
Expected: FAIL — `ImportError` (`validate_involved_robots` not defined).

- [ ] **Step 3: Add the function to `output_parser.py`**

```python
def validate_involved_robots(
    decision: CongestionDecision,
    known_robot_ids: set[str],
) -> None:
    """Enforce that every referenced robot ID exists in the input scene.

    Args:
        decision: Parsed decision to check.
        known_robot_ids: All robot IDs present in the request.

    Raises:
        DecisionValidationError: If any involved robot ID is unknown.
    """
    unknown = set(decision.involved_robots) - known_robot_ids
    if unknown:
        raise DecisionValidationError(f"Unknown robot IDs: {sorted(unknown)}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_validate_involved_robots.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add reasoning/vlm/output_parser.py tests/unit/test_validate_involved_robots.py
git commit -m "feat: add referential-integrity check for involved_robots"
```

---

## Task 6: Implement `MockBackend`

**Files:**
- Create: `reasoning/vlm/mock_backend.py`
- Test: `tests/unit/test_reasoner.py` (extend)

Per spec §7.7: deterministic test backend with single-response, default-response, and sequence modes.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_reasoner.py`:

```python
from reasoning.vlm.mock_backend import MockBackend

_PAYLOAD = PromptPayload(
    system_prompt="sys",
    user_prompt="usr",
    image_path="/tmp/frame.png",
    known_robot_ids=["robot_1"],
)
_CONFIG = ReasonerConfig(backend_id="mock")


def test_mock_backend_default_returns_no_congestion_json():
    response = MockBackend().analyze(_PAYLOAD, _CONFIG)
    assert response.backend_id == "mock"
    assert '"congestion_detected": false' in response.text


def test_mock_backend_returns_configured_text_and_records_payload():
    backend = MockBackend(response_text='{"ok": true}')
    response = backend.analyze(_PAYLOAD, _CONFIG)
    assert response.text == '{"ok": true}'
    assert backend.last_payload is _PAYLOAD
    assert backend.last_config is _CONFIG


def test_mock_backend_sequence_advances_then_holds_last():
    backend = MockBackend(response_sequence=["first", "second"])
    assert backend.analyze(_PAYLOAD, _CONFIG).text == "first"
    assert backend.analyze(_PAYLOAD, _CONFIG).text == "second"
    assert backend.analyze(_PAYLOAD, _CONFIG).text == "second"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_reasoner.py -k mock_backend -v`
Expected: FAIL — `ModuleNotFoundError: reasoning.vlm.mock_backend`.

- [ ] **Step 3: Create `mock_backend.py`**

```python
from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig

_DEFAULT_RESPONSE = (
    '{"congestion_detected": false, "type": "none", "involved_robots": [], '
    '"root_cause": "No congestion detected.", "strategy": "none", '
    '"justification": "Scene is clear."}'
)


class MockBackend:
    """Deterministic VLM backend for offline tests.

    Returns a fixed response, a default no-congestion decision, or a scripted
    sequence (holding the last entry once exhausted). Records the most recent
    payload and config for assertions.
    """

    def __init__(
        self,
        response_text: str | None = None,
        backend_id: str = "mock",
        latency_ms: int = 0,
        response_sequence: list[str] | None = None,
    ) -> None:
        self._response_text = response_text
        self._backend_id = backend_id
        self._latency_ms = latency_ms
        self._sequence = list(response_sequence) if response_sequence else None
        self._index = 0
        self.last_payload: PromptPayload | None = None
        self.last_config: ReasonerConfig | None = None

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Return a canned response and record the inputs."""
        self.last_payload = payload
        self.last_config = config
        if self._sequence is not None:
            text = self._sequence[min(self._index, len(self._sequence) - 1)]
            self._index += 1
        elif self._response_text is not None:
            text = self._response_text
        else:
            text = _DEFAULT_RESPONSE
        return BackendResponse(
            text=text,
            backend_id=self._backend_id,
            latency_ms=self._latency_ms,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_reasoner.py -k mock_backend -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add reasoning/vlm/mock_backend.py tests/unit/test_reasoner.py
git commit -m "feat: add deterministic MockBackend for VLM tests"
```

---

## Task 7: Implement `invoke_backend`, `build_reask_prompt`, `build_failed_result`

**Files:**
- Create: `reasoning/vlm/reasoner.py`
- Test: `tests/unit/test_reasoner.py` (extend)

Per spec §7.3. Define the three helper functions before the `Reasoner` class (Task 8).

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_reasoner.py`:

```python
import time

import pytest

from reasoning.vlm.models import BackendResponse, ReasonerRequest, RobotStateInput
from reasoning.vlm.output_parser import BackendTimeoutError
from reasoning.vlm.reasoner import (
    build_failed_result,
    build_reask_prompt,
    invoke_backend,
)


def test_invoke_backend_fills_latency_when_missing():
    backend = MockBackend(response_text="{}", latency_ms=0)
    # MockBackend reports latency_ms=0, so invoke_backend measures wall-clock.
    response = invoke_backend(backend, _PAYLOAD, ReasonerConfig(backend_id="mock"))
    assert response.latency_ms is not None and response.latency_ms >= 0


def test_invoke_backend_raises_on_timeout():
    class SlowBackend:
        def analyze(self, payload, config):
            time.sleep(0.2)
            return BackendResponse(text="{}", backend_id="slow")

    config = ReasonerConfig(backend_id="slow", timeout_sec=0.01)
    with pytest.raises(BackendTimeoutError):
        invoke_backend(SlowBackend(), _PAYLOAD, config)


def test_build_reask_prompt_appends_error_and_preserves_fields():
    reask = build_reask_prompt(_PAYLOAD, "bad enum")
    assert reask.system_prompt == _PAYLOAD.system_prompt
    assert reask.image_path == _PAYLOAD.image_path
    assert reask.known_robot_ids == _PAYLOAD.known_robot_ids
    assert "bad enum" in reask.user_prompt
    assert reask.user_prompt.startswith(_PAYLOAD.user_prompt)


def test_build_failed_result_has_none_decision():
    request = ReasonerRequest(
        request_id="req-9",
        image_path="/tmp/frame.png",
        frame_id="cam",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )
    result = build_failed_result(
        request=request,
        backend_id="mock",
        attempts=2,
        error_type="VLMOutputParseError",
        error_message="bad",
        raw_text="garbage",
    )
    assert result.decision is None
    assert result.raw_text == "garbage"
    assert result.diagnostics.parse_status == "failed"
    assert result.diagnostics.attempts == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_reasoner.py -k "invoke_backend or reask or failed_result" -v`
Expected: FAIL — `ModuleNotFoundError: reasoning.vlm.reasoner`.

- [ ] **Step 3: Create `reasoner.py` with the helpers**

```python
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path

from reasoning.vlm.models import (
    BackendResponse,
    PromptPayload,
    ReasonerConfig,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
)
from reasoning.vlm.output_parser import BackendTimeoutError

_REASK_SUFFIX = (
    "\n\nYour previous response was invalid: {error_message}\n"
    "Please return ONLY a valid JSON object matching the schema above.\n"
    "Do not include any text, markdown, or explanation outside the JSON."
)


def invoke_backend(
    backend: "VLMBackendLike",
    payload: PromptPayload,
    config: ReasonerConfig,
) -> BackendResponse:
    """Call a VLM backend with an outer thread-level timeout and latency timing.

    Args:
        backend: Any object with an `analyze(payload, config)` method.
        payload: Rendered prompt payload.
        config: Runtime config; `timeout_sec` bounds the call.

    Returns:
        The backend response, with `latency_ms` filled from wall-clock time when
        the backend did not report it.

    Raises:
        BackendTimeoutError: If the call exceeds `config.timeout_sec`.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(backend.analyze, payload, config)
        start = time.monotonic()
        try:
            response = future.result(timeout=config.timeout_sec)
        except FutureTimeoutError as exc:
            raise BackendTimeoutError(
                f"Backend timed out after {config.timeout_sec}s"
            ) from exc
        elapsed_ms = int((time.monotonic() - start) * 1000)
    if not response.latency_ms:
        return response.model_copy(update={"latency_ms": elapsed_ms})
    return response


def build_reask_prompt(payload: PromptPayload, error_message: str) -> PromptPayload:
    """Build a corrective prompt after invalid output, preserving fixed fields.

    Args:
        payload: The payload whose response failed.
        error_message: Human-readable description of the failure.

    Returns:
        A new frozen payload with the corrective suffix appended.
    """
    return payload.model_copy(
        update={"user_prompt": payload.user_prompt + _REASK_SUFFIX.format(error_message=error_message)}
    )


def build_failed_result(
    request: ReasonerRequest,
    backend_id: str,
    attempts: int,
    error_type: str | None,
    error_message: str | None,
    raw_text: str | None = None,
) -> ReasonerResult:
    """Construct a safe failure result with decision=None after exhausted retries.

    Args:
        request: The originating request.
        backend_id: Configured backend identifier.
        attempts: Total backend calls made.
        error_type: Last error class name, if any.
        error_message: Last error message, if any.
        raw_text: Last raw model text, preserved for audit.

    Returns:
        A `ReasonerResult` with `decision=None` and `parse_status='failed'`.
    """
    return ReasonerResult(
        request_id=request.request_id,
        decision=None,
        raw_text=raw_text,
        diagnostics=ReasonerDiagnostics(
            request_id=request.request_id,
            backend_id=backend_id,
            attempts=attempts,
            parse_status="failed",
            error_type=error_type,
            error_message=error_message,
        ),
    )
```

Replace the `"VLMBackendLike"` forward-reference annotation with the real Protocol import:

```python
from reasoning.vlm.backend_base import VLMBackend
```

and change the `invoke_backend` signature parameter to `backend: VLMBackend`. (The `VLMBackendLike` string above is a placeholder; do not keep it.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_reasoner.py -k "invoke_backend or reask or failed_result" -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add reasoning/vlm/reasoner.py tests/unit/test_reasoner.py
git commit -m "feat: add invoke_backend, reask, and failed-result helpers"
```

---

## Task 8: Implement `Reasoner.run` and `write_reasoner_log`

**Files:**
- Modify: `reasoning/vlm/reasoner.py`
- Test: `tests/unit/test_reasoner.py` (extend)

Per spec §7.2 (`Reasoner.run` algorithm) and §7.3 (`write_reasoner_log`).

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_reasoner.py`:

```python
from reasoning.vlm.reasoner import Reasoner, write_reasoner_log

_GOOD = (
    '{"congestion_detected": true, "type": "deadlock", '
    '"involved_robots": ["robot_1"], "root_cause": "x", '
    '"strategy": "yield", "justification": "y"}'
)
_BAD = "not json"


def _request_with_image(tmp_path) -> ReasonerRequest:
    image = tmp_path / "frame.png"
    image.write_bytes(b"\x89PNG\r\n")
    return ReasonerRequest(
        request_id="req-1",
        image_path=str(image),
        frame_id="cam",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )


def test_run_returns_decision_on_first_try(tmp_path):
    reasoner = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock"))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is not None
    assert result.decision.type == "deadlock"
    assert result.diagnostics.parse_status == "valid"
    assert result.diagnostics.attempts == 1


def test_run_reasks_then_succeeds(tmp_path):
    backend = MockBackend(response_sequence=[_BAD, _GOOD])
    reasoner = Reasoner(backend, ReasonerConfig(backend_id="mock", max_attempts=2))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.attempts == 2
    assert result.diagnostics.parse_status == "invalid"


def test_run_exhausts_attempts_returns_none(tmp_path):
    backend = MockBackend(response_sequence=[_BAD, _BAD])
    reasoner = Reasoner(backend, ReasonerConfig(backend_id="mock", max_attempts=2))
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is None
    assert result.diagnostics.parse_status == "failed"


def test_run_no_reask_when_disabled(tmp_path):
    backend = MockBackend(response_sequence=[_BAD, _GOOD])
    reasoner = Reasoner(
        backend, ReasonerConfig(backend_id="mock", max_attempts=2, allow_reask=False)
    )
    result = reasoner.run(_request_with_image(tmp_path))
    assert result.decision is None
    assert result.diagnostics.attempts == 1


def test_run_rejects_duplicate_robot_ids(tmp_path):
    image = tmp_path / "frame.png"
    image.write_bytes(b"\x89PNG\r\n")
    request = ReasonerRequest(
        request_id="req-1",
        image_path=str(image),
        frame_id="cam",
        stamp=1.0,
        robot_states=[
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_1", x=1.0, y=1.0, theta=0.0),
        ],
    )
    with pytest.raises(ValueError):
        Reasoner(MockBackend(), ReasonerConfig(backend_id="mock")).run(request)


def test_run_rejects_missing_image():
    request = ReasonerRequest(
        request_id="req-1",
        image_path="/nonexistent/frame.png",
        frame_id="cam",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )
    with pytest.raises(FileNotFoundError):
        Reasoner(MockBackend(), ReasonerConfig(backend_id="mock")).run(request)


def test_write_reasoner_log_appends_jsonl(tmp_path):
    log = tmp_path / "trace.jsonl"
    reasoner = Reasoner(MockBackend(response_text=_GOOD), ReasonerConfig(backend_id="mock"))
    result = reasoner.run(_request_with_image(tmp_path))
    write_reasoner_log(log, _request_with_image(tmp_path), result)
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["request_id"] == "req-1"
    assert record["parse_status"] == "valid"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_reasoner.py -k "run_ or write_reasoner_log" -v`
Expected: FAIL — `ImportError` (`Reasoner`, `write_reasoner_log` not defined).

- [ ] **Step 3: Add `Reasoner` and `write_reasoner_log` to `reasoner.py`**

Add imports at the top (merge with existing groups):

```python
from reasoning.vlm.output_parser import (
    BackendTimeoutError,
    DecisionValidationError,
    VLMOutputParseError,
    parse_decision_text,
    validate_involved_robots,
)
from reasoning.vlm.prompt_builder import build_prompt_payload
```

Add the class and logging function:

```python
class Reasoner:
    """Stateless M2 reasoning orchestrator: prompt → backend → parse → validate."""

    def __init__(self, backend: VLMBackend, config: ReasonerConfig) -> None:
        self._backend = backend
        self._config = config

    def run(self, request: ReasonerRequest) -> ReasonerResult:
        """Execute one complete reasoning pass with bounded retry/re-ask.

        Args:
            request: Validated reasoning request.

        Returns:
            A `ReasonerResult` with a decision, or `decision=None` on failure.

        Raises:
            ValueError: If robot IDs are not unique.
            FileNotFoundError: If `image_path` does not exist.
        """
        robot_ids = [s.robot_id for s in request.robot_states]
        if len(robot_ids) != len(set(robot_ids)):
            raise ValueError("Duplicate robot_id values in request.robot_states")
        if not Path(request.image_path).is_file():
            raise FileNotFoundError(f"image_path does not exist: {request.image_path}")

        payload = build_prompt_payload(request)
        known_ids = set(robot_ids)
        attempts = 0
        last_raw: str | None = None
        last_error_type: str | None = None
        last_error_msg: str | None = None

        while attempts < self._config.max_attempts:
            attempts += 1
            try:
                response = invoke_backend(self._backend, payload, self._config)
                last_raw = response.text
                decision = parse_decision_text(response.text)
                validate_involved_robots(decision, known_ids)
                return ReasonerResult(
                    request_id=request.request_id,
                    decision=decision,
                    raw_text=last_raw,
                    diagnostics=ReasonerDiagnostics(
                        request_id=request.request_id,
                        backend_id=response.backend_id,
                        attempts=attempts,
                        latency_ms=response.latency_ms,
                        parse_status="valid" if attempts == 1 else "invalid",
                        error_type=last_error_type,
                        error_message=last_error_msg,
                    ),
                )
            except BackendTimeoutError as exc:
                last_error_type, last_error_msg = "BackendTimeoutError", str(exc)
                continue
            except (VLMOutputParseError, DecisionValidationError) as exc:
                last_error_type, last_error_msg = type(exc).__name__, str(exc)
                if self._config.allow_reask and attempts < self._config.max_attempts:
                    payload = build_reask_prompt(payload, str(exc))
                elif not self._config.allow_reask:
                    break

        return build_failed_result(
            request=request,
            backend_id=self._config.backend_id,
            attempts=attempts,
            error_type=last_error_type,
            error_message=last_error_msg,
            raw_text=last_raw,
        )


def write_reasoner_log(
    output_path: str | Path,
    request: ReasonerRequest,
    result: ReasonerResult,
) -> None:
    """Append one request/response record to a JSONL trace file.

    Args:
        output_path: Destination JSONL file (opened in append mode).
        request: The originating request.
        result: The reasoning result to record.
    """
    record = {
        "request_id": request.request_id,
        "image_path": request.image_path,
        "frame_id": request.frame_id,
        "stamp": request.stamp,
        "robot_ids": [s.robot_id for s in request.robot_states],
        "backend_id": result.diagnostics.backend_id,
        "attempts": result.diagnostics.attempts,
        "latency_ms": result.diagnostics.latency_ms,
        "parse_status": result.diagnostics.parse_status,
        "raw_text": result.raw_text,
        "decision": result.decision.model_dump(mode="json") if result.decision else None,
        "error_type": result.diagnostics.error_type,
        "error_message": result.diagnostics.error_message,
    }
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, default=str) + "\n")
```

Note on the `allow_reask=False` path: when reask is disabled, the loop breaks after the first parse failure so `attempts` stays at 1 (matches `test_run_no_reask_when_disabled`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_reasoner.py -v`
Expected: PASS (all reasoner tests).

- [ ] **Step 5: Commit**

```bash
git add reasoning/vlm/reasoner.py tests/unit/test_reasoner.py
git commit -m "feat: add Reasoner.run orchestrator and JSONL trace logging"
```

---

## Task 9: Add the backend factory and confirm `LlamaServerBackend` conforms

**Files:**
- Create: `reasoning/vlm/backend_factory.py`
- Modify: `reasoning/vlm/llama_server_backend.py`
- Test: `tests/unit/test_reasoner.py` (extend)

Per spec §7.1 (`build_backend`) and §7.8. `LlamaServerBackend.analyze(payload, config)` already matches the Protocol; the only change is making its constructor accept the optional `model_path` field that config carries (ignored at runtime) so a `LlamaServerBackendConfig` can be splatted in cleanly via the factory.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_reasoner.py`:

```python
from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.backend_factory import build_backend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.models import LlamaServerBackendConfig


def test_build_backend_returns_mock():
    backend = build_backend("mock", LlamaServerBackendConfig(model_id="x"))
    assert isinstance(backend, VLMBackend)


def test_build_backend_returns_llama_server():
    config = LlamaServerBackendConfig(model_id="cosmos", base_url="http://127.0.0.1:8080/v1")
    backend = build_backend("llama_server", config)
    assert isinstance(backend, LlamaServerBackend)
    assert isinstance(backend, VLMBackend)


def test_build_backend_rejects_unknown_id():
    with pytest.raises(ValueError):
        build_backend("nope", LlamaServerBackendConfig(model_id="x"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_reasoner.py -k build_backend -v`
Expected: FAIL — `ModuleNotFoundError: reasoning.vlm.backend_factory`.

- [ ] **Step 3: Create `backend_factory.py`**

```python
from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import LlamaServerBackendConfig

BackendConfig = LlamaServerBackendConfig  # extend to a union as backends are added


def build_backend(backend_id: str, backend_config: BackendConfig) -> VLMBackend:
    """Construct a concrete VLM backend from its identifier and config.

    Args:
        backend_id: Selector, e.g. "mock" or "llama_server".
        backend_config: Backend-specific connection config.

    Returns:
        A backend instance satisfying the `VLMBackend` Protocol.

    Raises:
        ValueError: If `backend_id` is not recognized.
    """
    if backend_id == "mock":
        return MockBackend()
    if backend_id == "llama_server":
        return LlamaServerBackend(
            base_url=backend_config.base_url,
            model_id=backend_config.model_id,
            mmproj_path=backend_config.mmproj_path,
        )
    raise ValueError(f"Unknown backend_id: {backend_id!r}")
```

- [ ] **Step 4: Confirm `LlamaServerBackend` is unchanged-compatible**

`LlamaServerBackend.__init__(base_url, model_id, mmproj_path)` already matches the factory call. No edit needed unless `make lint` flags the existing file. Verify by import only — the test in Step 1 covers `isinstance(..., VLMBackend)`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_reasoner.py -k build_backend -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add reasoning/vlm/backend_factory.py tests/unit/test_reasoner.py
git commit -m "feat: add VLM backend factory"
```

---

## Task 10: Public re-exports and full-suite verification

**Files:**
- Modify: `reasoning/vlm/__init__.py`
- Test: full suite + lint

Re-export the intentional public API per CLAUDE.md ("Re-export intentionally public APIs from `__init__.py`").

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_reasoner.py`:

```python
def test_public_api_is_importable_from_package():
    from reasoning.vlm import (
        CongestionDecision,
        MockBackend,
        Reasoner,
        ReasonerConfig,
        ReasonerRequest,
        ReasonerResult,
        build_backend,
    )

    assert Reasoner is not None
    assert build_backend is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_reasoner.py::test_public_api_is_importable_from_package -v`
Expected: FAIL — `ImportError` (names not exported from package).

- [ ] **Step 3: Populate `__init__.py`**

Overwrite `reasoning/vlm/__init__.py`:

```python
"""M2 VLM semantic reasoning: prompt building, backend adapters, parsing, orchestration."""

from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.backend_factory import build_backend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    BackendResponse,
    CongestionDecision,
    LlamaServerBackendConfig,
    PromptPayload,
    ReasonerConfig,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
    RobotStateInput,
)
from reasoning.vlm.output_parser import (
    BackendTimeoutError,
    DecisionValidationError,
    VLMOutputParseError,
    parse_decision_text,
    validate_involved_robots,
)
from reasoning.vlm.prompt_builder import build_prompt_payload, format_robot_state_lines
from reasoning.vlm.reasoner import (
    Reasoner,
    build_failed_result,
    build_reask_prompt,
    invoke_backend,
    write_reasoner_log,
)

__all__ = [
    "BackendResponse",
    "BackendTimeoutError",
    "CongestionDecision",
    "DecisionValidationError",
    "LlamaServerBackend",
    "LlamaServerBackendConfig",
    "MockBackend",
    "PromptPayload",
    "Reasoner",
    "ReasonerConfig",
    "ReasonerDiagnostics",
    "ReasonerRequest",
    "ReasonerResult",
    "RobotStateInput",
    "VLMBackend",
    "VLMOutputParseError",
    "build_backend",
    "build_failed_result",
    "build_prompt_payload",
    "build_reask_prompt",
    "format_robot_state_lines",
    "invoke_backend",
    "parse_decision_text",
    "validate_involved_robots",
    "write_reasoner_log",
]
```

- [ ] **Step 4: Run the full M2 suite**

Run: `pytest tests/unit/test_vlm_output_parser.py tests/unit/test_prompt_builder.py tests/unit/test_reasoner.py tests/unit/test_validate_involved_robots.py -v`
Expected: PASS (all M2 unit tests).

- [ ] **Step 5: Run lint and the whole test suite**

Run: `make lint && make test`
Expected: lint clean; full suite green (the 144 prior tests plus the new M2 tests).

- [ ] **Step 6: Commit**

```bash
git add reasoning/vlm/__init__.py tests/unit/test_reasoner.py
git commit -m "feat: re-export M2 public API from reasoning.vlm package"
```

---

## Self-Review Notes

**Spec coverage check:**
- §7.1 models → Task 1 (`model_path` reconciliation; other models already present).
- §7.6 `VLMBackend` Protocol → Task 2.
- §7.4 prompt builder (`build_prompt_payload`, `format_robot_state_lines`), §8.1–§8.2 templates → Task 3.
- §7.5 `parse_decision_text`, exceptions, invariant check, dedupe → Task 4; `validate_involved_robots` → Task 5; legacy `parse_vlm_decision` preserved (untouched).
- §7.7 `MockBackend` (single/default/sequence modes) → Task 6.
- §7.3 `invoke_backend`, `build_reask_prompt`, `build_failed_result`, `write_reasoner_log` → Tasks 7–8.
- §7.2 `Reasoner.run` algorithm (validate → loop → retry vs re-ask → fail) → Task 8.
- §7.1 `build_backend` factory, §7.8 `LlamaServerBackend` conformance → Task 9.
- §11 error handling: duplicate IDs, missing image, timeout retry, parse re-ask, exhausted → `decision=None` → covered by Task 8 tests.

**Deferred (out of scope for this plan, matches spec):** ROS2 node wrapper (§5 "indicative"), live-backend scenario tests (§13 "Scenario Tests" require a running llama-server or curated frames), and the `confidence` field (§14, explicitly deferred). The `BackendTimeoutError`-retry path is unit-tested via `invoke_backend`; an end-to-end "timeout then succeed" Reasoner test is omitted because it requires a flaky timing-based backend — the retry branch is exercised structurally by the parse-failure re-ask tests plus the timeout test on `invoke_backend`.

**Type consistency:** `analyze(payload, config) -> BackendResponse` is used identically in the Protocol (Task 2), `MockBackend` (Task 6), the factory (Task 9), and `LlamaServerBackend` (existing). `parse_decision_text -> CongestionDecision`, `validate_involved_robots(decision, set[str]) -> None`, and `Reasoner.run(ReasonerRequest) -> ReasonerResult` are consistent across tasks.

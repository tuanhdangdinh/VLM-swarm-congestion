# Failure-Context Closed Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When M5 re-analyzes a congestion episode, the VLM prompt carries a "previous attempt" block (strategy, yielder, outcome, detail) so its next decision is deliberate instead of memoryless.

**Architecture:** M5 keeps a single-slot `AttemptMemory` beside `CooldownTracker`: an attempt is recorded at dispatch, finalized when the command resolves, and handed to the next analysis for an overlapping robot set inside a time window. `reasoning_pipeline.build_failure_context` projects that record into the M2 `FailureContext` model, which `prompt_builder` renders into a slot in the existing user prompt (empty when absent, so today's prompt is unchanged byte-for-byte). The attached context is written into the decision artifact for RQ5 measurement. No new orchestrator state; the detector re-firing after cooldown *is* the re-analysis.

**Tech Stack:** Python 3.10, Pydantic v2, pytest, ruff; ROS2 Jazzy node (`rclpy`) wired but not unit-tested; live check on the GCP VM inside the `vgu_ros` container.

**Spec:** `docs/superpowers/specs/2026-09-17-failure-context-closed-loop-design.md` (Phase 2 slice of `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`, Appendix A.1/A.5).

## Global Constraints

- Type hints: `X | None`, built-in generics; Google-style docstrings on public functions/classes (`docs/standards/coding_style.md`, `CLAUDE.md`).
- Pydantic contracts are `ConfigDict(frozen=True)`; serialize with `.model_dump(mode="json")`.
- `command_lifecycle.py` must not import from `reasoning.*` (spec: Contracts → M5 side).
- The context-less prompt must remain byte-identical to today's (spec: The loop, step 4).
- `failure_context_window_sec` default `60.0`; `0` disables; `0 < window <= cooldown_sec + stall_threshold_sec` is rejected at config load (spec: Timing constraint).
- `outcome_status` precedence: `timed_out` if any robot timed out, else `failed` if any failed, else `completed` (spec: The loop, step 2).
- `failure_detail` strings, verbatim from the spec: `"<strategy> completed <since_resolve> s ago; congestion re-detected for the same robots"` and `"<strategy> <outcome> after <run_time> s; congestion re-detected for the same robots"` with `run_time = resolved_at - dispatched_at`; seconds rendered with `:.0f`.
- Tests: `test_<behavior>_<condition>`, one behavior per test; unit tests run offline (`make test` = `pytest`; `make lint` = `ruff check .`, line length 100).
- Commit messages: Conventional Commits, subject line only, under 72 chars, no body, no trailers (`CLAUDE.md` → Commit Messages).
- Do not touch `GroundingParams.mode`, M3, the command schema, or `OrchestratorStateMachine`.
- `docs/implementation_notes.md`: append-only, newest first under the matching section, absolute dates, link evidence.

---

## File map

| File | Responsibility in this plan |
|---|---|
| `reasoning/vlm/models.py` | `FailureContext` model; `ReasonerRequest.failure_context` |
| `reasoning/vlm/prompt_builder.py` | `render_failure_context_block`; `{failure_context_block}` slot |
| `reasoning/vlm/__init__.py` | export the two names above |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py` | `AttemptRecord`, `summarize_outcome`, `AttemptMemory` (pure, no `reasoning.*`) |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` | `build_failure_context`; `failure_context` kwarg on `build_reasoner_request` and `write_decision_artifact` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` | `OrchestratorConfig.failure_context_window_sec` + bound validator |
| `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml` | the new key |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | three wiring sites + pending-context slot + two log lines |
| `tests/unit/test_prompt_builder.py`, `test_m5_command_lifecycle.py`, `test_m5_reasoning_pipeline.py`, `test_m5_models.py` | tests |
| `docs/specs/module2_vlm_reasoning.md`, `docs/specs/module5_orchestrator.md`, rev-8 spec, Phase 1 plan, `docs/implementation_notes.md` | docs kept in sync |

---

### Task 1: `FailureContext` model and `ReasonerRequest.failure_context`

**Files:**
- Modify: `reasoning/vlm/models.py:6-27`
- Test: `tests/unit/test_prompt_builder.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `FailureContext(strategy: str, yield_robot: str | None = None, crossing_order: list[str] | None = None, outcome_status: str, failure_detail: str)` (frozen); `ReasonerRequest.failure_context: FailureContext | None = None`. Tasks 2, 4, 6 rely on these exact names.

- [ ] **Step 1: Write the failing tests**

Replace the import block at the top of `tests/unit/test_prompt_builder.py` (lines 1–8) with:

```python
import json

import pytest
from pydantic import ValidationError

from reasoning.vlm.models import FailureContext, ReasonerRequest, RobotStateInput
from reasoning.vlm.prompt_builder import (
    SYSTEM_PROMPT,
    build_prompt_payload,
    format_robot_state_lines,
)
```

Append to the end of the file:

```python
def test_reasoner_request_failure_context_defaults_to_none():
    assert _request().failure_context is None


def test_failure_context_optional_role_fields_default_to_none():
    ctx = FailureContext(
        strategy="yield",
        outcome_status="failed",
        failure_detail="yield failed after 12 s; congestion re-detected for the same robots",
    )
    assert ctx.yield_robot is None
    assert ctx.crossing_order is None


def test_failure_context_is_frozen():
    ctx = FailureContext(strategy="yield", outcome_status="failed", failure_detail="d")
    with pytest.raises(ValidationError):
        ctx.strategy = "reverse"


def test_failure_context_rejects_empty_strategy():
    with pytest.raises(ValidationError):
        FailureContext(strategy="", outcome_status="failed", failure_detail="d")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/test_prompt_builder.py -v -k "failure_context"`
Expected: FAIL — `ImportError: cannot import name 'FailureContext'`.

- [ ] **Step 3: Implement the model and the field**

In `reasoning/vlm/models.py`, insert after `RobotStateInput` (after line 17) and before `ReasonerRequest`:

```python
class FailureContext(BaseModel):
    """Prior-attempt summary injected into re-analysis prompts (Reflexion-lite)."""

    model_config = ConfigDict(frozen=True)

    strategy: str = Field(min_length=1)
    yield_robot: str | None = None
    crossing_order: list[str] | None = None
    outcome_status: str = Field(min_length=1)
    failure_detail: str = Field(min_length=1)
```

In `ReasonerRequest`, add after `robot_states: list[RobotStateInput]`:

```python
    failure_context: FailureContext | None = None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/test_prompt_builder.py -v`
Expected: all 12 tests PASS (8 existing + 4 new).

- [ ] **Step 5: Commit**

```bash
git add reasoning/vlm/models.py tests/unit/test_prompt_builder.py
git commit -m "feat: add FailureContext and ReasonerRequest.failure_context"
```

---

### Task 2: Render the previous-attempt block in the user prompt

**Files:**
- Modify: `reasoning/vlm/prompt_builder.py:13-64` (template) and `:98-120` (`build_prompt_payload`)
- Modify: `reasoning/vlm/__init__.py:13-28` and `:37-67`
- Test: `tests/unit/test_prompt_builder.py`

**Interfaces:**
- Consumes: `FailureContext`, `ReasonerRequest.failure_context` (Task 1).
- Produces: `render_failure_context_block(context: FailureContext) -> str` — multi-line block, no leading/trailing newline. `build_prompt_payload` unchanged in signature. `crossing_order` is deliberately not rendered in this slice (always `None`).

- [ ] **Step 1: Write the failing tests**

Change the `prompt_builder` import in `tests/unit/test_prompt_builder.py` to:

```python
from reasoning.vlm.prompt_builder import (
    SYSTEM_PROMPT,
    build_prompt_payload,
    format_robot_state_lines,
    render_failure_context_block,
)
```

Append to the end of the file:

```python
def _completed_yield() -> FailureContext:
    return FailureContext(
        strategy="yield",
        yield_robot="robot_1",
        outcome_status="completed",
        failure_detail="yield completed 31 s ago; congestion re-detected for the same robots",
    )


def test_render_failure_context_block_includes_strategy_outcome_and_detail():
    block = render_failure_context_block(_completed_yield())
    assert block.startswith("Previous attempt in this episode:")
    assert "- strategy=yield, yield_robot=robot_1, outcome=completed" in block
    assert (
        "- detail: yield completed 31 s ago; congestion re-detected for the same robots"
        in block
    )
    assert block.endswith("unless the scene has changed.")
    assert not block.startswith("\n") and not block.endswith("\n")


def test_render_failure_context_block_omits_yield_robot_when_none():
    block = render_failure_context_block(
        FailureContext(
            strategy="temporary_wait",
            outcome_status="timed_out",
            failure_detail="temporary_wait timed_out after 20 s; congestion re-detected for the same robots",  # noqa: E501
        )
    )
    assert "- strategy=temporary_wait, outcome=timed_out" in block
    assert "yield_robot" not in block


def test_build_prompt_payload_places_failure_block_before_guidance_when_set():
    request = _request().model_copy(update={"failure_context": _completed_yield()})
    prompt = build_prompt_payload(request).user_prompt
    ids = prompt.index("Known robot IDs:")
    block = prompt.index("Previous attempt in this episode:")
    guidance = prompt.index("Guidance:")
    assert ids < block < guidance
    assert 'Known robot IDs: ["robot_1", "robot_2"]\n\nPrevious attempt' in prompt
    assert "unless the scene has changed.\n\nGuidance:" in prompt


def test_build_prompt_payload_seam_is_unchanged_when_failure_context_none():
    prompt = build_prompt_payload(_request()).user_prompt
    assert 'Known robot IDs: ["robot_1", "robot_2"]\n\nGuidance:' in prompt
    assert "Previous attempt" not in prompt
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/test_prompt_builder.py -v`
Expected: FAIL — `ImportError: cannot import name 'render_failure_context_block'`.

- [ ] **Step 3: Implement the slot and the renderer**

In `reasoning/vlm/prompt_builder.py`, change the import to:

```python
from reasoning.vlm.models import FailureContext, PromptPayload, ReasonerRequest, RobotStateInput
```

In `_USER_TEMPLATE`, replace the two lines

```text
Known robot IDs: {known_robot_ids_json}

Guidance:
```

with

```text
Known robot IDs: {known_robot_ids_json}
{failure_context_block}
Guidance:
```

(The slot swallows the blank line; `build_prompt_payload` supplies `""` or `"\n<block>\n"`, so both renderings keep exactly one blank line on each side.)

Add after `_USER_TEMPLATE`:

```python
_FAILURE_CONTEXT_ADVICE = (
    "If the previous strategy did not clear the congestion, prefer a different "
    "strategy unless the scene has changed."
)


def render_failure_context_block(context: FailureContext) -> str:
    """Render the previous-attempt block for a re-analysis prompt (rev-8 A.1).

    Args:
        context: Prior-attempt summary supplied by M5.

    Returns:
        A multi-line block with no leading or trailing newline.
    """
    attempt = f"strategy={context.strategy}"
    if context.yield_robot is not None:
        attempt += f", yield_robot={context.yield_robot}"
    attempt += f", outcome={context.outcome_status}"
    return "\n".join(
        [
            "Previous attempt in this episode:",
            f"- {attempt}",
            f"- detail: {context.failure_detail}",
            _FAILURE_CONTEXT_ADVICE,
        ]
    )
```

In `build_prompt_payload`, replace the `user_prompt = _USER_TEMPLATE.format(...)` call with:

```python
    failure_block = (
        ""
        if request.failure_context is None
        else "\n" + render_failure_context_block(request.failure_context) + "\n"
    )
    user_prompt = _USER_TEMPLATE.format(
        robot_state_block=block,
        known_robot_ids_json=json.dumps(known_ids),
        failure_context_block=failure_block,
    )
```

In `reasoning/vlm/__init__.py`: add `FailureContext,` to the `reasoning.vlm.models` import block (alphabetical, after `CongestionDecision`); change the `prompt_builder` import to
`from reasoning.vlm.prompt_builder import build_prompt_payload, format_robot_state_lines, render_failure_context_block`
(wrap in parentheses to stay under 100 columns); add `"FailureContext",` and `"render_failure_context_block",` to `__all__` in sorted position.

- [ ] **Step 4: Run the tests and lint**

Run: `pytest tests/unit/test_prompt_builder.py -v && ruff check reasoning/vlm`
Expected: 16 tests PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add reasoning/vlm/prompt_builder.py reasoning/vlm/__init__.py tests/unit/test_prompt_builder.py
git commit -m "feat: render previous-attempt block in the VLM user prompt"
```

---

### Task 3: `AttemptMemory` and `summarize_outcome` in `command_lifecycle.py`

**Files:**
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py` (append after `CooldownTracker`, line 118)
- Test: `tests/unit/test_m5_command_lifecycle.py`

**Interfaces:**
- Consumes: `CommandState` (existing).
- Produces:
  - `AttemptRecord(command_id: str, robot_ids: list[str], strategy: str, yield_robot: str | None, dispatched_at: float, resolved_at: float | None = None, outcome_status: str | None = None)` (dataclass).
  - `summarize_outcome(states: dict[str, CommandState]) -> str`.
  - `AttemptMemory(window_sec: float)` with `record(command_id, robot_ids, strategy, yield_robot, now) -> None`, `resolve(command_id, outcome_status, now) -> None`, `context_for(robot_ids, now) -> AttemptRecord | None`.
  Tasks 4 and 6 rely on these exact names.

- [ ] **Step 1: Write the failing tests**

Change the import block of `tests/unit/test_m5_command_lifecycle.py` to:

```python
from swarm_orchestrator.command_lifecycle import (
    AttemptMemory,
    CommandRecord,
    CommandState,
    CommandTracker,
    CooldownTracker,
    summarize_outcome,
)
```

Append to the end of the file:

```python
def _memory(window: float = 60.0) -> AttemptMemory:
    memory = AttemptMemory(window_sec=window)
    memory.record("c1", ["robot_1", "robot_2"], "yield", "robot_1", now=0.0)
    return memory


def test_attempt_memory_returns_none_before_resolve_without_clearing():
    memory = _memory()
    assert memory.context_for(["robot_1"], now=5.0) is None
    memory.resolve("c1", "completed", now=10.0)
    assert memory.context_for(["robot_1"], now=11.0) is not None


def test_attempt_memory_returns_record_within_window_for_overlapping_robots():
    memory = _memory()
    memory.resolve("c1", "completed", now=10.0)
    record = memory.context_for(["robot_2", "robot_3"], now=40.0)
    assert record is not None
    assert record.command_id == "c1"
    assert record.strategy == "yield"
    assert record.yield_robot == "robot_1"
    assert record.outcome_status == "completed"
    assert record.resolved_at == 10.0


def test_attempt_memory_returns_none_after_window_expires():
    memory = _memory(window=60.0)
    memory.resolve("c1", "completed", now=10.0)
    assert memory.context_for(["robot_1"], now=70.5) is None
    # expiry clears the slot; an earlier `now` cannot resurrect it
    assert memory.context_for(["robot_1"], now=20.0) is None


def test_attempt_memory_clears_on_disjoint_robot_set():
    memory = _memory()
    memory.resolve("c1", "failed", now=10.0)
    assert memory.context_for(["robot_9"], now=20.0) is None
    assert memory.context_for(["robot_1"], now=21.0) is None


def test_attempt_memory_new_record_supersedes_previous():
    memory = _memory()
    memory.resolve("c1", "failed", now=10.0)
    memory.record("c2", ["robot_1", "robot_2"], "reverse", None, now=30.0)
    assert memory.context_for(["robot_1"], now=31.0) is None
    memory.resolve("c2", "completed", now=50.0)
    record = memory.context_for(["robot_1"], now=60.0)
    assert record is not None and record.command_id == "c2"


def test_attempt_memory_resolve_ignores_superseded_command():
    memory = _memory()
    memory.record("c2", ["robot_1"], "reverse", None, now=30.0)
    memory.resolve("c1", "timed_out", now=35.0)
    assert memory.context_for(["robot_1"], now=36.0) is None


def test_attempt_memory_window_zero_disables():
    memory = _memory(window=0.0)
    memory.resolve("c1", "completed", now=10.0)
    assert memory.context_for(["robot_1"], now=11.0) is None


def test_summarize_outcome_precedence_timed_out_over_failed_over_completed():
    completed, failed, timed_out = (
        CommandState.COMPLETED,
        CommandState.FAILED,
        CommandState.TIMED_OUT,
    )
    assert summarize_outcome({"a": completed, "b": completed}) == "completed"
    assert summarize_outcome({"a": completed, "b": failed}) == "failed"
    assert summarize_outcome({"a": failed, "b": timed_out}) == "timed_out"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/test_m5_command_lifecycle.py -v`
Expected: FAIL — `ImportError: cannot import name 'AttemptMemory'`.

- [ ] **Step 3: Implement**

Append to `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py`:

```python
def summarize_outcome(states: dict[str, CommandState]) -> str:
    """Collapse per-robot terminal states into one attempt outcome.

    Args:
        states: Terminal `CommandState` per robot of a resolved command.

    Returns:
        `"timed_out"` if any robot timed out, else `"failed"` if any failed,
        else `"completed"`.
    """
    values = set(states.values())
    if CommandState.TIMED_OUT in values:
        return "timed_out"
    if CommandState.FAILED in values:
        return "failed"
    return "completed"


@dataclass
class AttemptRecord:
    """The last dispatched coordination attempt, kept for re-analysis context."""

    command_id: str
    robot_ids: list[str]
    strategy: str
    yield_robot: str | None
    dispatched_at: float
    resolved_at: float | None = None
    outcome_status: str | None = None


class AttemptMemory:
    """Single-slot memory of the last attempt for failure-context feedback (rev-8 A.1).

    One slot is enough because the state machine allows a single in-flight cycle.
    The record becomes visible only after `resolve`, stays visible for
    `window_sec` after resolution for any overlapping robot set, and is dropped
    on expiry, on an analysis for a disjoint robot set (no cross-episode memory),
    or when a new attempt is recorded. `window_sec <= 0` disables the memory.
    """

    def __init__(self, window_sec: float) -> None:
        self._window_sec = window_sec
        self._record: AttemptRecord | None = None

    def record(
        self,
        command_id: str,
        robot_ids: list[str],
        strategy: str,
        yield_robot: str | None,
        now: float,
    ) -> None:
        """Remember a freshly dispatched attempt, superseding any earlier one."""
        self._record = AttemptRecord(
            command_id=command_id,
            robot_ids=list(robot_ids),
            strategy=strategy,
            yield_robot=yield_robot,
            dispatched_at=now,
        )

    def resolve(self, command_id: str, outcome_status: str, now: float) -> None:
        """Finalize the remembered attempt; a superseded command id is ignored."""
        if self._record is None or self._record.command_id != command_id:
            return
        self._record.resolved_at = now
        self._record.outcome_status = outcome_status

    def context_for(self, robot_ids: list[str], now: float) -> AttemptRecord | None:
        """Return the resolved attempt relevant to a new analysis, or None."""
        record = self._record
        if record is None or record.resolved_at is None:
            return None
        if not set(robot_ids) & set(record.robot_ids):
            self._record = None
            return None
        if self._window_sec <= 0.0 or now - record.resolved_at > self._window_sec:
            self._record = None
            return None
        return record
```

- [ ] **Step 4: Run the tests and lint**

Run: `pytest tests/unit/test_m5_command_lifecycle.py -v && ruff check ros2_ws/src/swarm_orchestrator`
Expected: all PASS (12 existing + 8 new); ruff clean.

- [ ] **Step 5: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py tests/unit/test_m5_command_lifecycle.py
git commit -m "feat: M5 attempt memory for previous-attempt context"
```

---

### Task 4: `build_failure_context`, request pass-through, artifact key

**Files:**
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py:17-22` (imports), `:71-95` (`build_reasoner_request`), `:137-165` (`write_decision_artifact`)
- Test: `tests/unit/test_m5_reasoning_pipeline.py`

**Interfaces:**
- Consumes: `AttemptRecord` (Task 3), `FailureContext` (Task 1).
- Produces: `build_failure_context(record: AttemptRecord, now: float) -> FailureContext`; `build_reasoner_request(request_id, snapshot, image_path, failure_context: FailureContext | None = None)`; `write_decision_artifact(output_dir, outcome, failure_context: FailureContext | None = None)`. Task 6 relies on these.

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_m5_reasoning_pipeline.py`, extend the imports:

```python
from swarm_orchestrator.command_lifecycle import AttemptRecord
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    build_failure_context,
    build_reasoner_request,
    dump_frame_png,
    fan_out_command,
    write_decision_artifact,
)

from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    FailureContext,
    ReasonerDiagnostics,
    ReasonerResult,
)
```

Append to the end of the file:

```python
# ---- failure context ----

def _attempt(status: str = "completed", resolved_at: float = 100.0) -> AttemptRecord:
    return AttemptRecord(
        command_id="c1",
        robot_ids=["robot_1", "robot_2"],
        strategy="yield",
        yield_robot="robot_1",
        dispatched_at=40.0,
        resolved_at=resolved_at,
        outcome_status=status,
    )


def _ok_outcome() -> PipelineOutcome:
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on aisle conflict",
        strategy="yield",
        justification="both robots are stopped in opposing directions",
    )
    result = ReasonerResult(
        request_id="r1",
        decision=decision,
        raw_text='{"congestion_detected": true}',
        diagnostics=ReasonerDiagnostics(
            request_id="r1", backend_id="openai", attempts=1, parse_status="valid"
        ),
    )
    return PipelineOutcome(
        request_id="r1",
        reasoner_result=result,
        grounded_command={"command_id": "c1", "actions": []},
        terminal_stage=TerminalStage.OK,
    )


def test_build_failure_context_names_yielder_and_seconds_since_completion():
    ctx = build_failure_context(_attempt(), now=131.0)
    assert ctx.strategy == "yield"
    assert ctx.yield_robot == "robot_1"
    assert ctx.outcome_status == "completed"
    assert ctx.failure_detail == (
        "yield completed 31 s ago; congestion re-detected for the same robots"
    )


def test_build_failure_context_reports_run_time_for_timed_out_attempt():
    ctx = build_failure_context(_attempt(status="timed_out", resolved_at=60.0), now=90.0)
    assert ctx.outcome_status == "timed_out"
    assert ctx.failure_detail == (
        "yield timed_out after 20 s; congestion re-detected for the same robots"
    )


def test_build_reasoner_request_passes_failure_context_through():
    ctx = FailureContext(strategy="yield", outcome_status="failed", failure_detail="d")
    with_ctx = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png", failure_context=ctx)
    without = build_reasoner_request("r1", _snapshot(), "/tmp/r1.png")
    assert with_ctx.failure_context == ctx
    assert without.failure_context is None


def test_write_decision_artifact_records_failure_context(tmp_path):
    ctx = FailureContext(
        strategy="yield", yield_robot="robot_1", outcome_status="completed", failure_detail="d"
    )
    path = write_decision_artifact(tmp_path, _ok_outcome(), failure_context=ctx)
    payload = json.loads(path.read_text())
    assert payload["failure_context"] == {
        "strategy": "yield",
        "yield_robot": "robot_1",
        "crossing_order": None,
        "outcome_status": "completed",
        "failure_detail": "d",
    }


def test_write_decision_artifact_writes_null_failure_context_when_absent(tmp_path):
    payload = json.loads(write_decision_artifact(tmp_path, _ok_outcome()).read_text())
    assert payload["failure_context"] is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/test_m5_reasoning_pipeline.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_failure_context'`.

- [ ] **Step 3: Implement**

In `reasoning_pipeline.py`, extend the imports:

```python
from reasoning.vlm.models import (
    FailureContext,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
    RobotStateInput,
)
from swarm_orchestrator.command_lifecycle import AttemptRecord
from swarm_orchestrator.models import (
    PipelineOutcome,
    SceneSnapshot,
    TerminalStage,
)
```

Replace `build_reasoner_request` with:

```python
def build_reasoner_request(
    request_id: str,
    snapshot: SceneSnapshot,
    image_path: str,
    failure_context: FailureContext | None = None,
) -> ReasonerRequest:
    """Project a SceneSnapshot plus a dumped image path into a ReasonerRequest."""
    robot_states = [
        RobotStateInput(
            robot_id=r.robot_id,
            x=r.x,
            y=r.y,
            theta=r.theta,
            linear_velocity=r.linear_velocity,
            status=r.status,
            goal=r.goal if hasattr(r, "goal") else None,
        )
        for r in snapshot.robots
    ]
    return ReasonerRequest(
        request_id=request_id,
        image_path=image_path,
        frame_id=snapshot.frame_id,
        stamp=snapshot.stamp,
        robot_states=robot_states,
        failure_context=failure_context,
    )


def build_failure_context(record: AttemptRecord, now: float) -> FailureContext:
    """Project M5's last resolved attempt into the M2 previous-attempt block (rev-8 A.1).

    Args:
        record: A resolved `AttemptRecord` from `AttemptMemory.context_for`.
        now: Monotonic time of the new analysis, for the elapsed-seconds wording.

    Returns:
        A `FailureContext` whose `failure_detail` follows the spec wording.
    """
    resolved_at = record.resolved_at if record.resolved_at is not None else now
    status = record.outcome_status if record.outcome_status is not None else "unknown"
    if status == "completed":
        detail = (
            f"{record.strategy} completed {now - resolved_at:.0f} s ago; "
            "congestion re-detected for the same robots"
        )
    else:
        detail = (
            f"{record.strategy} {status} after {resolved_at - record.dispatched_at:.0f} s; "
            "congestion re-detected for the same robots"
        )
    return FailureContext(
        strategy=record.strategy,
        yield_robot=record.yield_robot,
        outcome_status=status,
        failure_detail=detail,
    )
```

In `write_decision_artifact`, change the signature to

```python
def write_decision_artifact(
    output_dir: str | Path,
    outcome: PipelineOutcome,
    failure_context: FailureContext | None = None,
) -> Path:
```

and add to the `payload` dict, after `"raw_text": result.raw_text,`:

```python
        "failure_context": (
            None if failure_context is None else failure_context.model_dump(mode="json")
        ),
```

- [ ] **Step 4: Run the tests and lint**

Run: `pytest tests/unit/test_m5_reasoning_pipeline.py -v && ruff check ros2_ws/src/swarm_orchestrator`
Expected: all PASS (existing + 5 new); ruff clean.

- [ ] **Step 5: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py tests/unit/test_m5_reasoning_pipeline.py
git commit -m "feat: attach and log previous-attempt context in the M5 pipeline adapter"
```

---

### Task 5: `failure_context_window_sec` config with re-trigger bound check

**Files:**
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py:8` (import) and `:41-72` (`OrchestratorConfig`)
- Modify: `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`
- Test: `tests/unit/test_m5_models.py`

**Interfaces:**
- Produces: `OrchestratorConfig.failure_context_window_sec: float` (default `60.0`). Task 6 reads it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_m5_models.py`:

```python
def _config_with(**overrides):
    base = dict(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={"robot_0": TaskAssignment(task="t", goal=(0.0, 0.0))},
        frame_dump_dir="data/logs/m5_frames",
    )
    base.update(overrides)
    return OrchestratorConfig(**base)


def test_orchestrator_config_failure_context_window_defaults_to_60():
    assert _config_with().failure_context_window_sec == 60.0


def test_orchestrator_config_rejects_failure_context_window_inside_retrigger_bound():
    # cooldown 15 + stall 12 = 27: a 27 s window can never fire
    with pytest.raises(ValidationError, match="can never fire"):
        _config_with(failure_context_window_sec=27.0)


def test_orchestrator_config_accepts_zero_failure_context_window_as_disabled():
    assert _config_with(failure_context_window_sec=0.0).failure_context_window_sec == 0.0


def test_orchestrator_config_accepts_failure_context_window_above_bound():
    assert _config_with(failure_context_window_sec=27.5).failure_context_window_sec == 27.5
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/test_m5_models.py -v -k failure_context_window`
Expected: `defaults_to_60` FAILS with `AttributeError`; `rejects_...` FAILS (no error raised).

- [ ] **Step 3: Implement**

In `models.py`, change the pydantic import to:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
```

In `OrchestratorConfig`, add after `frame_downscale_width`:

```python
    # Seconds after a command resolves during which its attempt is attached to a
    # re-analysis for overlapping robots as `failure_context` (rev-8 A.1). 0 disables
    # (RQ5 memoryless control). Must exceed cooldown + stall threshold or it can
    # never fire — enforced below.
    failure_context_window_sec: float = Field(default=60.0, ge=0.0)
```

Add after the existing `_non_empty_robot_ids` validator:

```python
    @model_validator(mode="after")
    def _failure_context_window_can_fire(self) -> OrchestratorConfig:
        window = self.failure_context_window_sec
        bound = self.cooldown_sec + self.stall_threshold_sec
        if 0.0 < window <= bound:
            raise ValueError(
                f"failure_context_window_sec={window} can never fire: a re-detection "
                f"takes at least cooldown_sec + stall_threshold_sec = {bound} s; set it "
                "above that bound, or 0 to disable"
            )
        return self
```

In `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`, add after `command_timeout_sec: 20.0`:

```yaml
# Window after a command resolves in which the attempt is fed back to the VLM
# as "previous attempt" context on re-analysis. Must exceed cooldown_sec +
# stall_threshold_sec (27 s here) or it can never fire; 0 disables it (the RQ5
# memoryless control).
failure_context_window_sec: 60.0
```

- [ ] **Step 4: Run the tests and lint**

Run: `pytest tests/unit/test_m5_models.py -v && ruff check ros2_ws/src/swarm_orchestrator`
Expected: all PASS, including `test_shipped_orchestrator_yaml_goals_stay_inside_camera_roi` (it loads the shipped yaml); ruff clean.

- [ ] **Step 5: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml tests/unit/test_m5_models.py
git commit -m "feat: failure_context_window_sec config with re-trigger bound check"
```

---

### Task 6: Wire the node (record → resolve → attach → audit)

**Files:**
- Modify: `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py:21-28` (imports), `:37-45` (imports), `:110-116` (`__init__`), `:182` and `:226` (call sites), `:254-283` (`_submit_pipeline`, `_handle_outcome`), `:293-302` (`_dispatch`), `:325-336` (`_resolve_command`)

**Interfaces:**
- Consumes: `AttemptMemory`, `summarize_outcome` (Task 3); `build_failure_context`, kwargs (Task 4); `failure_context_window_sec` (Task 5); `FailureContext` (Task 1).
- Produces: no new public API. No unit test (spec decision: node wiring is verified live in Task 8). Lint must pass.

- [ ] **Step 1: Imports and construction**

Change these import lines:

```python
from reasoning.vlm.models import (
    AnthropicBackendConfig,
    FailureContext,
    LlamaServerBackendConfig,
    OpenAIBackendConfig,
    ReasonerConfig,
)
```

```python
from swarm_orchestrator.command_lifecycle import (
    AttemptMemory,
    CommandRecord,
    CommandTracker,
    CooldownTracker,
    summarize_outcome,
)
```

```python
from swarm_orchestrator.reasoning_pipeline import (
    InProcessPipeline,
    ReasoningPipeline,
    build_failed_outcome,
    build_failure_context,
    build_reasoner_request,
    dump_frame_png,
    fan_out_command,
    write_decision_artifact,
)
```

In `__init__`, after `self._cooldown = CooldownTracker(self._config.cooldown_sec)` add:

```python
        self._attempts = AttemptMemory(self._config.failure_context_window_sec)
```

and after `self._future: Future[PipelineOutcome] | None = None` add:

```python
        # Context attached to the in-flight request; consumed by _handle_outcome so
        # the decision artifact records exactly what the VLM was told.
        self._pending_failure_context: FailureContext | None = None
```

- [ ] **Step 2: Pass the event's robots into `_submit_pipeline`**

Line 182 (`_on_scene_state`) becomes:

```python
            self._submit_pipeline(directive.request_id, snapshot, event.involved_robots)
```

Line 226 (`_on_trigger_analysis`) becomes:

```python
            self._submit_pipeline(directive.request_id, snapshot, event.involved_robots)
```

- [ ] **Step 3: Attach in `_submit_pipeline`, audit in `_handle_outcome`**

Replace `_submit_pipeline` with:

```python
    def _submit_pipeline(self, request_id: str, snapshot, robots: list[str]) -> None:
        frame = self._frame_rgb
        downscale = self._config.frame_downscale_width
        dump_dir = self._config.frame_dump_dir
        now = time.monotonic()
        attempt = self._attempts.context_for(robots, now)
        failure_context = None if attempt is None else build_failure_context(attempt, now)
        self._pending_failure_context = failure_context
        if attempt is not None and failure_context is not None:
            self.get_logger().info(
                f"request={request_id} failure_context attached command={attempt.command_id} "
                f"strategy={failure_context.strategy} outcome={failure_context.outcome_status}"
            )

        def task() -> PipelineOutcome:
            image_path = str(Path(dump_dir) / f"{request_id}.png")
            dump_frame_png(frame, image_path, downscale)
            request = build_reasoner_request(
                request_id, snapshot, image_path, failure_context=failure_context
            )
            return self._pipeline.run(request)

        self._future = self._executor.submit(task)
```

In `_handle_outcome`, replace the first `try:` block with:

```python
        failure_context = self._pending_failure_context
        self._pending_failure_context = None
        try:
            artifact_path = write_decision_artifact(
                self._config.decision_log_dir, outcome, failure_context=failure_context
            )
            self.get_logger().info(f"decision artifact written: {artifact_path}")
        except OSError as exc:
            self.get_logger().error(f"decision artifact write failed: {exc}")
```

- [ ] **Step 4: Record in `_dispatch`, finalize in `_resolve_command`**

In `_dispatch`, immediately after the `self._tracker.register(CommandRecord(...))` call (after line 302), add:

```python
        yield_robot = next((m[1] for m in messages if m[2] == "yield"), None)
        self._attempts.record(
            grounded["command_id"],
            robot_ids,
            outcome.reasoner_result.decision.strategy,
            yield_robot,
            time.monotonic(),
        )
```

(`messages` tuples are `(command_id, robot_id, action, params_json, timeout)`; a `DISPATCH` directive guarantees `decision` is present.)

Replace `_resolve_command` with:

```python
    def _resolve_command(self, command_id: str) -> None:
        robots = self._tracker.robots_of(command_id)
        for robot_id in robots:
            self._registry.clear_override(robot_id)
        states = {
            r: s for r in robots if (s := self._tracker.state_of(command_id, r)) is not None
        }
        outcome_status = summarize_outcome(states)
        now = time.monotonic()
        self._attempts.resolve(command_id, outcome_status, now)
        self.get_logger().info(f"command {command_id} resolved status={outcome_status}")
        self._machine.on_command_resolved(robots, outcome_status == "completed")
        self._cooldown.start(robots, now)
        self._publish_registry()
```

(`_resolve_command` only runs once every robot is terminal, so `outcome_status == "completed"` is exactly the previous `all_completed`.)

- [ ] **Step 5: Lint and the full offline suite**

Run: `ruff check . && pytest`
Expected: ruff clean; all unit tests PASS (`tests/integration` needs a sourced ROS2 env and is expected to be skipped/deselected locally as today).

- [ ] **Step 6: Commit**

```bash
git add ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py
git commit -m "feat: M5 attaches previous-attempt context on re-analysis"
```

---

### Task 7: Docs kept in sync

**Files:**
- Modify: `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` (revision list after the Rev 8.1 bullet; end of the A.1 "Failure-context feedback" bullet, lines 593–603)
- Modify: `docs/specs/module5_orchestrator.md` (mermaid block lines 76–101; FR5.4 list after FR5.4.5; config table near line 250; validation sentence near line 360; defaults near line 467)
- Modify: `docs/specs/module2_vlm_reasoning.md` (FR2.1 list after FR2.1.5, line 105; `ReasonerRequest` block lines 287–294)
- Modify: `docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md` (under the `### Task 5:` heading, line 871)
- Modify: `docs/implementation_notes.md` (top of the "Congestion-Resolution Experiment" section, line 40; top of the "M2 VLM / M5 Orchestrator Pipeline" section, line 110)

- [ ] **Step 1: Rev-8 spec — rev 8.2**

After the `- Rev 8.1 (2026-09-16): ...` bullet add:

```markdown
- Rev 8.2 (2026-09-17): episode boundary for failure-context feedback fixed as
  a time window after command resolution, any outcome (design:
  `2026-09-17-failure-context-closed-loop-design.md`).
```

At the end of the A.1 "Failure-context feedback (Reflexion-lite)" bullet, after "no cross-episode memory.", append:

```markdown
  Episode boundary (rev 8.2): the previous attempt is retained for
  `failure_context_window_sec` after its command resolves, whatever the
  outcome (a `completed` yield that did not clear the standoff is fed back
  too), and is dropped on expiry or when an analysis starts for a disjoint
  robot set.
```

- [ ] **Step 2: Module 5 spec**

In the mermaid block, after the line
`TRK -->|"resolved (COMPLETED/FAILED/TIMED_OUT)"| CD["start cooldown for robots"]`
add:

```text
    TRK -->|"resolved → AttemptMemory.resolve"| AM["AttemptMemory (last attempt, windowed)"]
    AM -.->|"failure_context on re-analysis"| PIPE
```

After FR5.4.5 add:

```markdown
- FR5.4.6 (2026-09-17) Keep the last dispatched attempt (strategy, yielder,
  outcome) in a single-slot `AttemptMemory`. When a new analysis starts for an
  overlapping robot set within `failure_context_window_sec` of that command's
  resolution — whatever the outcome — attach it to the `ReasonerRequest` as
  `failure_context` and record it in the decision artifact. The memory is
  dropped on expiry, on an analysis for a disjoint robot set, or when a new
  attempt is dispatched; `0` disables it (RQ5 memoryless control). Design:
  `docs/superpowers/specs/2026-09-17-failure-context-closed-loop-design.md`.
```

In the config table (the row block containing `| cooldown_sec | float | ...`) add a row:

```markdown
| failure_context_window_sec | float | seconds after command resolution in which the last attempt is attached to a re-analysis as `failure_context`; 0 disables (RQ5 memoryless control) |
```

In the validation sentence that reads `` `stall_threshold_sec`/`cooldown_sec`/`command_timeout_sec` ≥ 0. `` append the sentence:
`` `failure_context_window_sec` is 0 or greater than `cooldown_sec + stall_threshold_sec` (a smaller window can never fire). ``

In the defaults line containing `` `cooldown_sec = 15.0`, `command_timeout_sec = 20.0`, `` add `` `failure_context_window_sec = 60.0`, `` after `command_timeout_sec = 20.0`,.

- [ ] **Step 3: Module 2 spec**

After FR2.1.5 add:

```markdown
- FR2.1.6 (2026-09-17) When `ReasonerRequest.failure_context` is set, render a
  "Previous attempt in this episode" block (strategy, yielder if any, outcome,
  detail, one neutral escalation sentence) between the known-ID list and the
  guidance. When absent the prompt is byte-identical to the context-less prompt.
  Prompt context only; the output fields and enum vocabulary are unchanged.
```

In the `ReasonerRequest` code block add after `robot_states: list[RobotStateInput]`:

```python
    failure_context: FailureContext | None = None
```

and add a validation bullet:

```markdown
- `failure_context` is supplied by M5 only on re-analysis of an episode with a
  resolved prior attempt (M5 FR5.4.6); M2 treats it as prompt context.
```

- [ ] **Step 4: Phase 1 plan — supersession note**

Directly under the `### Task 5: Prompt blocks — failure context, motion table, annotation scheme, role-field instructions` heading add:

```markdown
> **2026-09-17:** the failure-context portion of this task (`FailureContext`,
> `ReasonerRequest.failure_context`, `render_failure_context_block`) landed via
> `docs/superpowers/plans/2026-09-17-failure-context-closed-loop.md` with a
> minimal template slot instead of the sectioned rebuild below. When executing
> this task, keep those names and add only the motion-table, annotation-scheme
> and role-field pieces on top.
```

- [ ] **Step 5: Implementation notes (landed, host verification pending)**

At the top of the "Congestion-Resolution Experiment" section (before the 2026-07-11 entry):

```markdown
- **2026-09-17** — Phase 2 slice landed ahead of Phase 1: failure-context
  feedback (rev-8 A.1) is wired end-to-end — `AttemptMemory` in M5, `FailureContext`
  + prompt block in M2, context recorded in decision artifacts. Episode rule =
  time window after resolution, any outcome (rev 8.2). Design:
  `docs/superpowers/specs/2026-09-17-failure-context-closed-loop-design.md`;
  plan: `docs/superpowers/plans/2026-09-17-failure-context-closed-loop.md`.
  Host verification pending (see M2/M5 section).
```

At the top of the "M2 VLM / M5 Orchestrator Pipeline" section (before the 2026-09-17 goal-tolerance entry):

```markdown
- **2026-09-17** — **Previous-attempt context on re-analysis** (commits
  `feat: add FailureContext…` through `feat: M5 attaches previous-attempt
  context…`). M5 records each dispatched attempt (`strategy`, `yield_robot` =
  the robot whose fanned-out action is `yield`), finalizes it on resolution with
  `timed_out > failed > completed` precedence, and attaches it to the next
  `ReasonerRequest` for overlapping robots inside `failure_context_window_sec`
  (default 60 s; must exceed cooldown + stall threshold = 27 s, enforced at
  config load; 0 = off). The prompt gains a "Previous attempt in this episode"
  block; the artifact gains `failure_context`. **Why:** runs G/H re-derived
  every cooldown with no memory (rev-8 A.1, run 12). Host check pending: force
  a re-analysis via `/orchestrator/trigger_analysis` inside the window and
  confirm `failure_context != null` in the artifact.
```

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md docs/specs/module5_orchestrator.md docs/specs/module2_vlm_reasoning.md docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md docs/implementation_notes.md
git commit -m "docs: sync M2/M5 specs and notes for failure-context closed loop"
```

---

### Task 8: Live verification on the VM and evidence note

**Files:**
- Modify: `docs/implementation_notes.md` (append the evidence entry at the top of the M2/M5 section)

**Facts you need (verified 2026-09-17):** VM `vgu-canary-base-isaac-workstation-vm`, project `summer-flux-501516-n6`, public IP `34.68.133.240`, SSH key `~/Documents/IsaacAutomator/state/canary-base/key.pem`, login user `ubuntu`. The repo copy at `/home/ubuntu/vgu-vlm-swarm` is **not** a git checkout. ROS2 runs only inside the `vgu_ros` container (`ros:jazzy`), which mounts that directory at `/ws`; the host has no `/opt/ros`. The M5 launch recipe is `scripts/run_phase3_demo.sh` (starts Isaac, M1, M4, M5 with the `openai` backend; key sourced from `/ws/.env`). The trigger service is `/orchestrator/trigger_analysis` (`swarm_interfaces/srv/TriggerCongestionAnalysis`, request field `reason`, response `accepted`/`analysis_id`/`message`); it bypasses cooldown but is rejected while a command is active, so it can be retried until accepted.

- [ ] **Step 1: Offline gate**

Run: `make test && make lint`
Expected: all unit tests PASS; ruff clean.

- [ ] **Step 2: Ship only the touched files**

```bash
KEY=~/Documents/IsaacAutomator/state/canary-base/key.pem
VM=ubuntu@34.68.133.240
R=/home/ubuntu/vgu-vlm-swarm
rsync -av -e "ssh -i $KEY" reasoning/vlm/models.py reasoning/vlm/prompt_builder.py reasoning/vlm/__init__.py "$VM:$R/reasoning/vlm/"
rsync -av -e "ssh -i $KEY" \
  ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py \
  ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py \
  ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py \
  ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py \
  "$VM:$R/ros2_ws/src/swarm_orchestrator/swarm_orchestrator/"
rsync -av -e "ssh -i $KEY" ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml "$VM:$R/ros2_ws/src/swarm_orchestrator/config/"
```

- [ ] **Step 3: Rebuild M5 inside the container**

```bash
ssh -i $KEY $VM "sudo docker exec vgu_ros bash -lc 'source /opt/ros/jazzy/setup.bash && cd /ws/ros2_ws && colcon build --packages-select swarm_orchestrator 2>&1 | tail -5'"
```

Expected: `Summary: 1 package finished`.

- [ ] **Step 4: Run the closed loop**

Start the demo in the background with a recording window long enough for a yield to resolve (run 6 completed at T+2 m 16 s):

```bash
ssh -i $KEY $VM "cd $R && nohup ./scripts/run_phase3_demo.sh --rec-sec 420 > /tmp/phase3_demo_driver.log 2>&1 &"
```

Find the M5 log name and wait for the first dispatch and the resolve line from Task 6:

```bash
ssh -i $KEY $VM "grep -o 'phase3_demo_[0-9_]*_m5.log' /tmp/phase3_demo_driver.log | head -1"
# then, substituting the name:
ssh -i $KEY $VM "sudo docker exec vgu_ros bash -lc 'grep -E \"dispatch request=|resolved status=\" /tmp/<M5_LOG>'"
```

Expected within ~3 minutes: `dispatch request=... command=... robot=robot_1`, then `command <id> resolved status=completed` (or `failed`/`timed_out`).

- [ ] **Step 5: Force a re-analysis inside the window**

Within 60 s of the resolve line, call the trigger; retry every 10 s until `accepted: True`:

```bash
ssh -i $KEY $VM "sudo docker exec vgu_ros bash -lc 'source /opt/ros/jazzy/setup.bash && source /ws/ros2_ws/install/setup.bash && export FASTRTPS_DEFAULT_PROFILES_FILE=/ws/config/dds/fastdds.xml && ros2 service call /orchestrator/trigger_analysis swarm_interfaces/srv/TriggerCongestionAnalysis \"{reason: failure-context check}\"'"
```

Then confirm the attach log line and the artifact:

```bash
ssh -i $KEY $VM "sudo docker exec vgu_ros bash -lc 'grep \"failure_context attached\" /tmp/<M5_LOG>'"
ssh -i $KEY $VM "cd $R/data/logs/m5_decisions && f=\$(ls -t | head -1) && python3 -c \"import json;d=json.load(open('\$f'));print('\$f');print(json.dumps(d['failure_context'],indent=2));print(d['decision'])\""
```

Pass criteria (spec: Verification):

1. M5 log contains `failure_context attached command=<id> strategy=yield outcome=<status>`.
2. The newest artifact has `failure_context != null` with that strategy/outcome and a `failure_detail` matching the spec wording.
3. The same artifact's `raw_text`/decision is a valid decision (`parse_status: valid`); note whether the strategy changed versus the first decision.
4. Separately record whether a **natural** re-detection (a `starting analysis request=... reason=...stalled` line, not `manual trigger`) occurred inside the window. Do not claim it unless seen.

If the trigger is rejected with `trigger rejected: suppressed`, the frame is stale or robots are busy — wait and retry; if rejected past the 60 s window, restart from Step 4.

- [ ] **Step 6: Evidence note and commit**

At the top of the "M2 VLM / M5 Orchestrator Pipeline" section of `docs/implementation_notes.md` add an entry with the measured facts — fill every angle bracket from the run, no placeholders left in the committed text:

```markdown
- **2026-09-17** — **Failure-context attach verified on the VM** (run
  <HH:MM>–<HH:MM> UTC, gpt-4o): first decision `<type>/<strategy>` →
  `<status>` at T+<m>m<s>s → manual trigger at +<n> s → artifact
  `data/logs/m5_decisions/<request_id>.json` has
  `failure_context = {strategy: <…>, yield_robot: <…>, outcome_status: <…>}`;
  second decision `<type>/<strategy>` (<changed | unchanged> vs. the first).
  Natural re-detection inside the window: <observed | not observed>. This
  closes the "host check pending" item in the entry below.
```

```bash
git add docs/implementation_notes.md
git commit -m "docs: log failure-context attach verified on the VM"
```

Finally, stop the VM if the user is done with it (it bills while `RUNNING`): tell the user rather than stopping it unasked.

---

## Self-review (done at plan-writing time)

- **Spec coverage:** Scope → Tasks 1–6; Episode rule → Task 3 (`context_for`) + Task 5 (off-switch); Where memory lives → Task 3; The loop steps 1–5 → Tasks 6, 6, 6+4, 2, 4+6; Timing constraint → Task 5; Prompt block wording → Task 2; `failure_detail` wording → Task 4; Contracts → Tasks 1, 3, 4, 5; Testing → Tasks 1–5; Verification → Task 8; Files touched / docs kept in sync → Task 7. No gaps.
- **Placeholders:** the only angle brackets are in Task 8's log-name substitution and the evidence template, which are explicitly filled from the live run before commit.
- **Type consistency:** `AttemptMemory.record(command_id, robot_ids, strategy, yield_robot, now)`, `resolve(command_id, outcome_status, now)`, `context_for(robot_ids, now) -> AttemptRecord | None` are identical in Tasks 3, 4 (tests) and 6; `build_failure_context(record, now) -> FailureContext`, `build_reasoner_request(..., failure_context=)`, `write_decision_artifact(..., failure_context=)` identical in Tasks 4 and 6; `FailureContext` field names identical in Tasks 1, 2, 4, 7.

# Failure-Context Closed Loop — Design (Phase 2 slice)

**Prepared:** 2026-09-17

**Revision history:**

- Initial draft: M5 attempt memory + M2 previous-attempt prompt block; approved in chat (user, 2026-09-17).
- Rev 2 (2026-09-17): corrected the orchestrator config path to `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`; module-5 requirement landed as FR5.4.6 (FR5.4.5 already existed).
- Rev 3 (2026-09-17): after the final review and the first live run — the detail names the executed maneuver when M3 degraded the decided strategy; the closing advice explicitly allows `congestion_detected=false` (rev-8 spec 8.3).

**Status:** Approved for implementation. This is a narrow slice of Phase 2
(M5/M1 integration) of the rev-8 research design, landed ahead of Phase 1
because it is the smallest change that makes the VLM's re-analysis
deliberate instead of memoryless.

**Parent spec:** `2026-07-05-general-spatial-congestion-resolution-design.md`,
Appendix A.1 "Failure-context feedback (Reflexion-lite)" and A.5 (evidence-
dependent escalation). Reasoning-side interface: Phase 1 plan
`2026-07-08-congestion-reasoner-phase1-core.md`, Task 5.

---

## Problem

M5's state machine runs a single in-flight reasoning cycle
(`state_machine.py:38`): a congestion event starts analysis, the pipeline
returns one decision, M5 dispatches one command, the robots enter cooldown,
and the machine returns to `MONITORING` having forgotten what it attempted.
When the congestion detector fires again for the same robots, the VLM
re-derives from scratch.

Evidence:

- Rev-8 A.1 cites run 12: the VLM switched strategies without knowing its
  yield had failed.
- `implementation_notes.md` 2026-09-17: in runs G and H, parked robots
  re-triggered analysis every cooldown and gpt-4o eventually yielded two
  robots sitting at their goals. The goal-tolerance fix removed that trigger
  but not the underlying memorylessness.
- On the current VM, 354 decision artifacts produced 18 commands; the
  dominant pattern is one command per run. Nothing in the loop asks whether
  that one command worked.

The mechanism is already specified (A.1) and its reasoning-side half is
already planned (Task 5: `FailureContext`, `ReasonerRequest.failure_context`,
`render_failure_context_block`) but not landed. The M5 wiring belongs to
Phase 2, which has no plan. This document is that plan's first slice.

---

## Decision

### Scope

Reasoning side (Task 5's failure-context subset) plus minimal M5 wiring.
The live Arm A prompt changes; this is allowed (no `prereg-v1` tag exists)
and required (RQ5 is defined as failure feedback changing subsequent
decisions). `GroundingParams.mode` stays `legacy`; no motion table, no
`blocker_kind`, no sectioned-template rebuild.

### Episode rule (extends rev-8 wording; recorded as rev 8.2)

Rev 8 says the block appears "after a failed or expired resolution" and
covers "the current episode's prior attempt(s) only". The episode boundary
is left to Phase 2. Decision: **time-windowed, any outcome.**

- M5 keeps the last dispatched attempt for `failure_context_window_sec`
  after the command resolves, regardless of `COMPLETED` / `FAILED` /
  `TIMED_OUT`.
- If a new analysis starts for an overlapping robot set inside that window,
  the attempt is attached as `FailureContext` with `outcome_status` carrying
  the real status (a `completed` yield that did not clear the standoff is the
  case the strict reading misses; see the 2026-09-16 yield-refusal note,
  which waits on exactly such a post-resolution re-detection).
- Memory is cleared on window expiry, on an analysis for a **disjoint**
  robot set (no cross-episode memory), or when a new dispatch supersedes it.
- `failure_context_window_sec = 0` disables the feature. This is the
  memoryless control the rev-8 ablation axis ("with/without failure
  context") requires.

Rejected: strict `FAILED`/`TIMED_OUT`-only (misses completed-but-ineffective
attempts) and robot-set-only with no timer (unbounded; violates no
cross-episode memory).

### Where memory lives

- **Chosen: `AttemptMemory` in `command_lifecycle.py` beside
  `CooldownTracker`.** Same shape (robot ids + monotonic time, `now`
  injected), pure, ROS-free, unit-testable. Single slot: the machine allows
  one in-flight cycle, so one record suffices.
- Rejected: folding into `OrchestratorStateMachine` (its contract is
  timeless transitions; would force `now` plumbing and grow the class).
- Rejected: re-reading the previous decision artifact from disk (file I/O on
  the reasoning path; needs a robots→artifact index; the artifact cannot know
  the M4 outcome, which arrives later). The spec's audit intent is met the
  other way round: the attached context is written into the new artifact.

### The loop

1. **Record at dispatch** (`orchestrator_node._dispatch`, beside
   `tracker.register`): `memory.record(command_id, robot_ids, strategy,
   yield_robot, now)`. `strategy` is `outcome.reasoner_result.decision.strategy`.
   `yield_robot` is the robot whose fanned-out action is `"yield"` (M3 emits
   that literal, `command_grounder.py:289`), else `None`.
2. **Finalize at resolve** (`orchestrator_node._resolve_command`):
   `memory.resolve(command_id, summarize_outcome(states), now)`. Precedence:
   `timed_out` if any robot timed out, else `failed` if any failed, else
   `completed`. An unknown or superseded `command_id` is a no-op so a stale
   command resolving late cannot clobber a newer attempt.
3. **Consult at re-analysis** (`orchestrator_node._submit_pipeline`, which
   gains the event's robots): `record = memory.context_for(robots, now)`;
   if present, `failure_context = build_failure_context(record, now)` and
   `build_reasoner_request(..., failure_context=...)`. One structured `info`
   log line at attach time (`request_id`, strategy, outcome, elapsed).
4. **Render** (`prompt_builder`): the block occupies a `{failure_context_block}`
   slot between *Known robot IDs* and *Guidance*; empty string when `None`,
   so a request without context renders today's prompt byte-for-byte.
5. **Audit** (`write_decision_artifact(..., failure_context=...)`): adds
   `"failure_context": {...} | null` so RQ5 measurement can separate
   memoryful from memoryless decisions.

The VLM/grounding-failure `COOLDOWN` path records nothing (no attempt was
made) and leaves existing memory untouched, which is the correct episode
semantics: yield completed → re-analysis says none → re-detect inside the
window still sees the yield.

### Timing constraint

A re-detection after a resolved command takes at least
`cooldown_sec + stall_threshold_sec` (15 + 12 = 27 s on the current
`orchestrator.yaml`). A window at or below that can never fire, silently.
Default `failure_context_window_sec: 60.0`; `OrchestratorConfig` rejects
`0 < window <= cooldown_sec + stall_threshold_sec` at load with a message
that states the bound (fail-fast, like the existing startup checks).

### Prompt block wording

```text
Previous attempt in this episode:
- strategy=yield, yield_robot=robot_1, outcome=completed
- detail: yield completed 31 s ago; congestion re-detected for the same robots
If the congestion is no longer present, report congestion_detected=false. If it
persists and the previous strategy did not clear it, prefer a different
strategy unless the scene has changed.
```

`yield_robot=` is omitted when `None`. The closing sentences are guidance
only; the output fields and enum vocabulary are unchanged, which keeps the
rev-8 A.1 containment claim ("adds prompt context only") true. Rev 3 made the
`congestion_detected=false` option explicit because the first live run showed
the memoryful VLM rotating strategies on stalls that were no longer congestion.

`failure_detail` is built by M5 from the record: `"<strategy> completed
<since_resolve> s ago; congestion re-detected for the same robots"` for
`completed`, and `"<strategy> <outcome> after <run_time> s; congestion
re-detected for the same robots"` for `failed`/`timed_out`, where
`run_time = resolved_at - dispatched_at`. Rev 3: when the maneuver M3 fanned
out differs from the decided strategy (`AttemptRecord.executed_strategy`,
derived by `summarize_executed_strategy` from the action names — `yield` if any
action is `yield`, else the single action name, else `mixed`), the phrase
` (executed as <executed>)` is inserted before the semicolon, e.g. `"yield
completed 15 s ago (executed as temporary_wait); …"`.

---

## Contracts

### Reasoning side (`reasoning/vlm/`)

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

`ReasonerRequest.failure_context: FailureContext | None = None` (after
`robot_states`). `crossing_order` stays `None` in this slice; the field
exists so the Phase 1 plan's frozen interface is honored verbatim.
`prompt_builder.render_failure_context_block(context: FailureContext) -> str`.
Both exported from `reasoning.vlm`.

### M5 side (`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/`)

`command_lifecycle.py` (no `reasoning.*` imports):

```python
@dataclass
class AttemptRecord:
    command_id: str
    robot_ids: list[str]
    strategy: str
    yield_robot: str | None
    dispatched_at: float
    resolved_at: float | None = None
    outcome_status: str | None = None


def summarize_outcome(states: dict[str, CommandState]) -> str: ...


class AttemptMemory:
    def __init__(self, window_sec: float) -> None: ...
    def record(self, command_id: str, robot_ids: list[str], strategy: str,
               yield_robot: str | None, now: float) -> None: ...
    def resolve(self, command_id: str, outcome_status: str, now: float) -> None: ...
    def context_for(self, robot_ids: list[str], now: float) -> AttemptRecord | None: ...
```

`reasoning_pipeline.py`: `build_failure_context(record: AttemptRecord,
now: float) -> FailureContext`; `build_reasoner_request(request_id, snapshot,
image_path, failure_context: FailureContext | None = None)`;
`write_decision_artifact(output_dir, outcome, failure_context: FailureContext
| None = None)`.

`models.py`: `OrchestratorConfig.failure_context_window_sec: float =
Field(default=60.0, ge=0.0)` plus a `model_validator` enforcing the timing
constraint.

`ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`: `failure_context_window_sec: 60.0` with a comment
stating the bound and that `0` disables (RQ5 memoryless control).

---

## Explicitly not changed (YAGNI)

- No new orchestrator state; the detector re-firing after cooldown is the
  re-analysis.
- `OrchestratorStateMachine`, `CooldownTracker`, `CommandTracker` behavior.
- M3 grounding, `GroundingParams.mode`, the command schema.
- Task 5's motion table, `ANNOTATION_SCHEME_SENTENCE`, `blocker_kind`, and
  the sectioned template rebuild.
- Decision artifacts still carry no `run_id` (known gap, separate item).

---

## Testing

TDD; one behavior per test; `test_<behavior>_<condition>`.

- `tests/unit/test_prompt_builder.py`: block renders strategy, outcome and
  detail; omits `yield_robot` when `None`; block appears before *Guidance*
  when set; prompt is byte-identical to a context-less request when `None`.
  Existing eight tests pass unchanged.
- `tests/unit/test_m5_command_lifecycle.py`: `context_for` returns the
  record within the window for overlapping robots; returns `None` after
  expiry; clears on a disjoint set; returns `None` before resolve; a new
  `record` supersedes; a late `resolve` for a superseded command is ignored;
  window `0` disables; `summarize_outcome` precedence.
- `tests/unit/test_m5_reasoning_pipeline.py`: `build_reasoner_request`
  passes the context through; `build_failure_context` names the yielder and
  elapsed seconds; `write_decision_artifact` records the context and writes
  `null` when absent.
- Config validator: rejects a window inside the bound; accepts `0` and
  values above it. Placed beside existing `OrchestratorConfig` tests, or in a
  new `tests/unit/test_m5_config.py` if none exist.
- Node wiring has no rclpy unit test today and gains none; it is verified
  live.

---

## Verification (live, GCP VM `vgu-canary-base-isaac-workstation-vm`)

1. `make test` locally.
2. rsync only the touched files to `/home/ubuntu/vgu-vlm-swarm` (not a git
   checkout) and `colcon build --packages-select swarm_orchestrator`.
3. Run `head_on_deadlock` with the `openai` backend (gpt-4o).
4. Deterministic check: after the first yield resolves, publish to the
   existing manual trigger (`_on_trigger_analysis`) for `robot_1`, `robot_2`
   inside the window. Pass = the new artifact has `failure_context != null`
   with the expected strategy/outcome, the attach log line is present, and
   the raw prompt in the reasoner trace contains the block.
5. Report separately whether a **natural** re-detection occurred; do not
   claim it unless observed (the 2026-09-16 notes say that trigger has not
   yet been exercised live).

---

## Files touched

- `reasoning/vlm/models.py`, `reasoning/vlm/prompt_builder.py`,
  `reasoning/vlm/__init__.py`
- `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py`,
  `reasoning_pipeline.py`, `models.py`, `orchestrator_node.py`
- `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`
- Tests listed above.

Docs kept in sync (required by project standards):

- `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`:
  rev 8.2 line in its revision list and one sentence in A.1 naming the
  time-windowed episode rule.
- `docs/specs/module5_orchestrator.md`: new FR5.4.6 (attempt memory, window,
  off-switch) and the attach step in the data-flow diagram.
- `docs/specs/module2_vlm_reasoning.md`: `ReasonerRequest.failure_context`
  and the prompt block.
- `docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md`:
  supersession note on Task 5's failure-context portion.
- `docs/implementation_notes.md`: dated entries under the experiment section
  and the M2/M5 section, with verification evidence.

Commits: Conventional Commits, split reasoning side / M5 side / docs.

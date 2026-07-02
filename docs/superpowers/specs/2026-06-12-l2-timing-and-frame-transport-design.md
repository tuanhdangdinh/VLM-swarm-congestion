# Layer 2 Timing Budget & Annotated-Frame Transport — Design

**Prepared:** 2026-06-12
**Status:** Design approved (brainstormed; frame-transport half and revised timing half reviewed)
**Scope:** M1 (`swarm_perception`), M2 (`reasoning/vlm`), spec updates to M2/M5 docs, one doc-drift fix.

---

## 1. Problem

The architecture review of the two-layer design surfaced three gaps:

1. **Unbounded Layer 2 cycle time.** `Reasoner.run` retries up to
   `max_attempts` times, each bounded only by the per-attempt `timeout_sec`.
   With the current code defaults (`timeout_sec=30.0`, `max_attempts=2`) one
   analysis cycle can take ~60 s, during which M5 is single-in-flight and
   blind to new congestion — far outside the 0.5–2 Hz Layer 2 envelope and
   several Nav2 recovery cycles (≈5–10 s) long. There is no single number M5
   can budget against. Additionally, the M2 spec and code disagree on the
   `timeout_sec` default (15.0 in the spec vs 30.0 in
   `reasoning/vlm/models.py`).
2. **Annotated-frame transport overhead.** M1 publishes 1280×960 RGB frames on
   `/perception/annotated_frame` at full camera rate (~30 FPS), while M5
   consumes at most ~2 Hz into a single-slot latest-frame buffer (M5 spec
   FR5.3.6). ~93% of the DDS image traffic is wasted.
3. **Doc drift.** The diagram in `docs/modules.md` labels M6 as
   "(Gazebo/Webots)" while M6.1 and `docs/specs/module6_simulation.md`
   specify Isaac Sim.

## 2. Decisions

| # | Decision | Alternatives rejected |
|---|---|---|
| D1 | Throttle annotated-frame publishing at the source via an M1 node parameter | Separate low-rate topic (new topic name in contracts); `topic_tools` throttle node (invisible moving part); subscriber-side QoS only (no bandwidth saving) |
| D2 | Enforce a total reasoning deadline inside M2 (`ReasonerConfig.total_deadline_sec`) | Spec-only documentation (unenforced convention); M5-side watchdog (stale-result race, M2 stays unbounded) |
| D3 | Coherent timing stack `timeout_sec=6.0`, `max_attempts=2`, `total_deadline_sec=13.0`; enforce only `total_deadline_sec >= timeout_sec` | Original proposal (`total_deadline_sec=45.0` with asserts `< command_timeout_sec` and `< cooldown_sec`) was self-contradictory: 45 fails both checks against M5's planned 20.0/15.0 defaults, and those cross-timer asserts compare independent phases (reasoning duration vs M4 execution window vs post-resolution suppression) |

## 3. Design

### 3.1 Annotated-frame publish throttling (M1)

`PerceptionNode` gains one ROS2 parameter:

- `annotated_frame_publish_hz: float`, **default `0.0` = publish every frame**
  (current behavior preserved; throttling is opt-in via launch/config).

Behavior: when the parameter is > 0, `on_frame` skips
`publish_annotated_frame` unless at least `1.0 / hz` seconds have elapsed
since the last published annotated frame, measured by **frame stamp**, not
wall clock — identical behavior under sim time (`/clock`) and in offline
tests. `SceneState` and diagnostics publishing stay full-rate; only the image
topic is decimated.

Implementation shape (matches the M1 pattern of pure logic + thin node):

```python
def should_publish_annotated(
    stamp: float,
    last_published_stamp: float | None,
    publish_hz: float,
) -> bool:
    """Return True when the annotated frame at `stamp` should be published."""
```

- Pure function in `swarm_perception/annotation.py` (no `rclpy`), unit-tested
  directly.
- `publish_hz <= 0` → always `True`.
- First frame (`last_published_stamp is None`) → always `True`.
- Node holds `_last_annotated_pub_stamp` and consults the helper in
  `on_frame` before calling `publish_annotated_frame`.

Operational value: `5.0` Hz set in `perception.launch.py` / config — above
M5's consumption rate and its freshness gate (publish period 0.2 s ≪
`frame_scene_max_skew_sec` 1.0 s), at ~1/6th the DDS traffic.

Spec updates: M1 spec documents the parameter; M5 spec FR5.3.6 gets a
one-line cross-reference that `frame_scene_max_skew_sec` must be ≥ the
annotated-frame publish period.

### 3.2 Total reasoning deadline (M2)

**Config.** `ReasonerConfig` (spec + `reasoning/vlm/models.py`) changes:

| field | old | new |
|---|---|---|
| `timeout_sec` | 15.0 (spec) / 30.0 (code) — drifted | `6.0` in both |
| `max_attempts` | 2 | 2 (unchanged) |
| `total_deadline_sec` | — | new: `Field(default=13.0, gt=0)` |

A Pydantic `model_validator` enforces the one meaningful internal invariant:
`total_deadline_sec >= timeout_sec` (at least one full attempt fits).
Without it, attempt 1 is clamped below `timeout_sec` and attempt 2 / re-ask
silently never fires.

**Mechanics.** `Reasoner.run` computes `deadline = time.monotonic() +
config.total_deadline_sec` on entry. Each retry-loop iteration:

1. `remaining = deadline - time.monotonic()`; if `remaining <= 0`, break to
   the existing `build_failed_result` path.
2. Clamp the per-attempt budget: `attempt_config = config.model_copy(
   update={"timeout_sec": min(config.timeout_sec, remaining)})` (config stays
   frozen) and pass `attempt_config` to `invoke_backend`.

No new error type: a spent budget surfaces as the existing `decision=None`
failure with the last recorded error. `invoke_backend` is unchanged — its
per-attempt executor + `future.result(timeout)` already hard-bounds each
attempt, and `LlamaServerBackend` independently bounds the HTTP call via
`requests` timeout, so abandoned worker threads remain bounded.

Worst-case cycle time becomes
`min(max_attempts × timeout_sec, total_deadline_sec)` — one hard number M5
budgets against.

**Cross-timer guidance (M5 spec, documented — not asserted).** The intended
ordering is `total_deadline_sec (13) < cooldown_sec (15) <
command_timeout_sec (20)`: acting and waiting should dominate thinking, and
the ANALYZING blind window stays comparable to one Nav2 recovery cycle.
These are independent phases, so the ordering is rationale for choosing
config values, not a startup invariant.

**Latency-validation precondition (M2 spec, new note under the config
table).** The defaults assume single-attempt llama-server latency ≤ ~6 s for
a vision request. This is unverified on real hardware. Before the first
integrated run, measure actual backend latency — the JSONL trace
(`write_reasoner_log`) already records `latency_ms` — and if P95 exceeds
`timeout_sec`, scale the whole stack together (`timeout_sec`,
`total_deadline_sec`, and M5's `cooldown_sec` / `command_timeout_sec`),
explicitly accepting the larger blind window. A `timeout_sec` below real
latency is the worst failure mode: every attempt times out and Layer 2
silently never produces a decision.

### 3.3 Doc drift fix

`docs/modules.md` diagram (line 10): "(Gazebo/Webots)" → "(Isaac Sim)".

## 4. Error Handling

Unchanged semantics, restated for the new paths:

- Invalid caller inputs (duplicate robot IDs, missing image) still raise
  before any backend invocation.
- Backend failures — including deadline exhaustion — still degrade to
  `ReasonerResult(decision=None)`; M5 dispatches nothing and Layer 1 stays in
  control.
- `total_deadline_sec < timeout_sec` is rejected at config construction
  (Pydantic `ValidationError`), consistent with fail-fast startup.
- Throttling never raises: out-of-range parameter values degrade to
  "publish every frame" (`<= 0`) and the helper is total over its inputs.

## 5. Testing

**M1 (unit, offline):**

- `should_publish_annotated` truth table: first frame, exactly-at-period,
  just-under-period, `publish_hz=0` always-publish, stamp regression
  (late frame) does not publish.
- Node-level: with `annotated_frame_publish_hz=5.0`, feeding stamped frames
  at 30 Hz publishes SceneState every frame but annotated frames at ~5 Hz.

**M2 (unit, offline):** uses a test-local `_SleepingBackend` fake that sleeps
past its given timeout — **not** a `delay_sec` hook on the shared
`MockBackend`, which stays deterministic and instant.

- `test_run_returns_none_decision_when_total_deadline_spent`: stalled backend
  → `decision=None` within `total_deadline_sec` (wall-clock asserted with
  margin).
- `test_run_clamps_attempt_timeout_to_remaining_budget`: a recording fake
  asserts attempt 2's effective `timeout_sec` equals the remaining budget,
  not the configured per-attempt value.
- `test_reasoner_config_rejects_deadline_below_timeout`: construction with
  `total_deadline_sec < timeout_sec` raises `ValidationError`.

Existing M2 tests must pass unchanged apart from the default-value updates.

## 6. Out of Scope

- M4 implementation (tracked separately; precondition for end-to-end runs).
- Executor-reuse refactor in `invoke_backend` (HTTP timeout already bounds
  abandoned threads; documented behavior in M2 spec §invoke_backend).
- M5-side pipeline watchdog (made unnecessary by the in-M2 deadline).
- Spatial congestion clustering, escalation policy, multi-camera (per M5
  spec).

## 7. Files Touched

| file | change |
|---|---|
| `ros2_ws/src/swarm_perception/swarm_perception/perception_node.py` | parameter + throttle check in `on_frame` |
| `ros2_ws/src/swarm_perception/swarm_perception/annotation.py` | `should_publish_annotated` helper |
| `ros2_ws/src/swarm_perception/launch/` + `config/` | set `annotated_frame_publish_hz: 5.0` |
| `reasoning/vlm/models.py` | `timeout_sec` default 6.0, `total_deadline_sec`, `model_validator` |
| `reasoning/vlm/reasoner.py` | deadline computation + per-attempt clamp in `run` |
| `docs/specs/module1_perception.md` | document the new parameter |
| `docs/specs/module2_vlm_reasoning.md` | config table, `run()` algorithm, latency-validation note (resolves 15/30 drift) |
| `docs/specs/module5_orchestrator.md` | timing-budget guidance note; FR5.3.6 cross-reference |
| `docs/modules.md` | Gazebo/Webots → Isaac Sim |
| `tests/unit/` | new tests per §5 |

# M5 Orchestrator — Implementation Report

**Prepared:** 2026-06-16

**Scope:** What was actually built for Module 5 (Orchestrator), as merged to `main`
(merge commit `779d7ec`). This report describes the delivered code, not the plan or
spec. It records deviations from the spec and what remains unverified.

**References:** spec `docs/specs/module5_orchestrator.md`; plan
`docs/superpowers/plans/2026-06-12-m5-orchestrator.md`.

---

## 1. Summary

M5 went from a scaffold (an enum, a 2-line `is_congested` helper, a 22-line node)
to a working orchestrator: a numeric stall detector, a gated state machine, an
in-process M2→M3 pipeline run off the spin thread, command-lifecycle tracking, a
task/status registry, and a thin ROS2 node wiring it together. All decision logic
lives in pure, `rclpy`-free modules unit-tested offline on macOS; the node is glue.

- **Pure-logic modules:** 7 files, ~790 lines, fully unit-tested.
- **ROS2 node:** 319 lines, integration-tested behind `importorskip("rclpy")`.
- **Tests:** 53 M5 unit tests (all passing), plus 2 ros2-marked integration tests
  (skip without a sourced ROS2 env).
- **Full suite at merge:** 279 passed, 2 skipped; ruff clean; pure modules import
  no `rclpy`.

---

## 2. Delivered files

All paths under `ros2_ws/src/swarm_orchestrator/`.

| File | Lines | Role |
|---|---:|---|
| `swarm_orchestrator/models.py` | 175 | Pydantic contracts, `parse_scene_snapshot`, `load_config`, `DEFAULT_TOPICS` |
| `swarm_orchestrator/congestion_detector.py` | 88 | Progress-based stall detector (the FR5.1 numeric trigger) |
| `swarm_orchestrator/task_registry.py` | 73 | Base assignment + coordination override + effective + deterministic JSON |
| `swarm_orchestrator/command_lifecycle.py` | 104 | `CommandState`, `CommandRecord`, `CommandTracker`, `CooldownTracker` |
| `swarm_orchestrator/state_machine.py` | 106 | `OrchestratorStateMachine` + `Directive` (pure transitions) |
| `swarm_orchestrator/reasoning_pipeline.py` | 184 | `InProcessPipeline`, frame dump, request build, command fan-out |
| `swarm_orchestrator/orchestrator_node.py` | 319 | Thin ROS2 node (topics, trigger service, worker thread) |
| `swarm_orchestrator/__init__.py` | 60 | Public re-exports (no `rclpy` pulled in) |
| `config/orchestrator.yaml` | — | Rewritten to the runtime config schema |
| `launch/orchestrator.launch.py` | — | Passes `config_file` from the package share dir |
| `package.xml` | — | Added `std_msgs`, `sensor_msgs`, `cv_bridge` deps |

Tests (under `tests/`):

| File | Tests |
|---|---:|
| `unit/test_m5_models.py` | 12 |
| `unit/test_m5_congestion_detector.py` | 7 |
| `unit/test_m5_task_registry.py` | 5 |
| `unit/test_m5_command_lifecycle.py` | 8 |
| `unit/test_m5_state_machine.py` | 8 |
| `unit/test_m5_reasoning_pipeline.py` | 13 |
| `integration/test_m5_node.py` | 2 (ros2-marked, skip offline) |

Also `pyproject.toml`: added `swarm_orchestrator` to the pytest `pythonpath` and
registered the `ros2` marker.

---

## 3. What each module actually does

### 3.1 Data models (`models.py`)
Immutable Pydantic v2 contracts: `TaskAssignment`, `OrchestratorConfig`,
`RobotView`, `SceneSnapshot`, `CongestionEvent`, `PipelineOutcome`, plus the
`TerminalStage` enum. `parse_scene_snapshot` projects an M1 `SceneState` JSON
string into M5's internal `SceneSnapshot`, reading `dropped_frame` from
`diagnostics` and raising `ValueError` on malformed JSON. `load_config` builds a
frozen config from a parsed-YAML dict, accepts list-form goals, and merges
configured `topics` over `DEFAULT_TOPICS` so partial overrides keep the rest.

### 3.2 Congestion detector (`congestion_detector.py`)
`CongestionDetector.update(scene, goal_of, now)` tracks per-robot
distance-to-goal progress. A robot is **stalled** when its minimum observed
distance has not improved by more than `progress_epsilon_m` for at least
`stall_threshold_sec`, while it has a goal and a non-`STALE` status. On a
`dropped_frame` the call is a no-op (timers held, FR5.1.4). Emits a
`CongestionEvent` listing all stalled robots, or `None`. The detector takes an
injected `goal_of` callable rather than the registry object (see §5).

### 3.3 Task registry (`task_registry.py`)
Per-robot base assignment plus an optional active override. `effective(robot_id)`
returns the override while active, else the base. `to_json()` serializes the
*effective* registry deterministically, sorted by robot id, for publishing to M1.

### 3.4 Command lifecycle (`command_lifecycle.py`)
`CommandTracker` tracks per-robot states for each dispatched command, maps M4
status strings (`active`/`completed`/`failed`; unknown ignored), reports
resolution only when all robots are terminal, and marks unresolved commands
`TIMED_OUT` past their deadline. `CooldownTracker` owns per-robot re-trigger
cooldowns (works even when no command was dispatched, e.g. a pipeline failure).

### 3.5 State machine (`state_machine.py`)
`OrchestratorStateMachine` enforces a single in-flight reasoning cycle. `on_event`
starts analysis only from `MONITORING` and only when the involved robots are not
in cooldown or busy and a fresh frame is available — otherwise `SUPPRESSED`
(`MONITORING`) or `IGNORED` (already `ANALYZING`). `on_outcome` returns `DISPATCH`
on a valid grounded command, else `COOLDOWN` and increments per-robot failure
counters. `on_command_resolved` resets/raises counters on completion/failure. The
machine generates the per-cycle `request_id`.

### 3.6 Reasoning pipeline (`reasoning_pipeline.py`)
`InProcessPipeline.run` calls M2 then M3 grounding in-process and always returns a
`PipelineOutcome` (never raises): VLM-terminal on `decision=None` / no congestion /
**any reasoner exception**, GROUNDING-terminal on a grounding **or schema-validation**
failure, OK only on a validated command. Also provides `build_reasoner_request`,
`dump_frame_png` (RGB→BGR + optional aspect-preserving downscale), `fan_out_command`
(grounded dict → per-robot tuples with the fallback-timeout rule), and
`build_failed_outcome` (synthetic failed result when no `ReasonerResult` exists).

### 3.7 ROS2 node (`orchestrator_node.py`)
Thin glue. Reads all topic/service names from config. Subscribes to scene state,
annotated frame, and coordination status; publishes commands and the task registry;
serves `/orchestrator/trigger_analysis`. Reasoning runs on a
`ThreadPoolExecutor(max_workers=1)`; a 0.5 s timer drives timeout checks and polls
the future. Callbacks are thin (parse → pure logic → publish). The worker-future
read is guarded so a worker exception is logged, converted to a failed outcome, and
never leaves the machine stuck in `ANALYZING`.

---

## 4. Spec coverage (FR map)

- **FR5.1.\*** Detector: progress tracking, STALE/no-goal exclusion, dropped-frame
  hold, multi-robot events, effective-goal lookup. ✅
- **FR5.2.\*** State machine: single in-flight, cooldown/busy/frame gating,
  `request_id`, failure counters. ✅
- **FR5.3.\*** `ReasoningPipeline` Protocol + `InProcessPipeline`, `PipelineOutcome`,
  terminal stages, background executor, latest-frame buffer/dump. ✅
- **FR5.4.\*** `CommandTracker`, timeout, resolution, `fan_out_command`, dispatch,
  fallback retained on the record. ✅
- **FR5.5.\*** Registry base+override, effective, deterministic JSON, publish on
  startup/change. ✅
- **FR5.6.\*** Thin callbacks, periodic timer, config-driven topics/thresholds/
  timeouts/backend, fail-fast `load_config`. ✅
- **Edge cases E1–E8** covered (malformed JSON skip, dropped-frame hold,
  decision=None / no-congestion, grounding/schema failure, M4 FAILED/TIMED_OUT,
  command timeout, invalid-config fail-fast, no-frame/stale-frame suppression). ✅

---

## 5. Deviations from the spec

1. **Detector dependency injection.** The spec sketches
   `update(scene, task_registry, now)`. The implementation injects a
   `goal_of: Callable[[str], tuple|None]` instead of the whole `TaskRegistry`, to
   avoid a module cycle and keep the unit test trivial. Same behavior
   (effective-goal lookup), looser coupling.

2. **M3 is a stub this milestone.** The node's default `ground_fn` raises
   `NotImplementedError` because M3 (RAG grounding) is not yet implemented, so the
   dispatch path is unreachable in the default build. The pipeline's
   schema-validation step is wired and tested via an injected `ground_fn`, ready
   for a real M3.

3. **Manual trigger bypasses cooldown.** `/orchestrator/trigger_analysis` is an
   operator/test override: it bypasses the progress detector and per-robot
   cooldown, but still respects single-in-flight, busy-robot, and frame-freshness
   gating. (Reversible to cooldown-respecting if desired.)

---

## 6. Code-review fixes applied

Three findings from review were validated against code + spec and fixed before
merge:

1. **Unhandled M2 exceptions** — `reasoner.run` is now inside the pipeline `try`
   and the node guards `future.result()`, so an unexpected exception can no longer
   crash the timer callback or strand the machine in `ANALYZING`.
2. **Missing command validation** — grounded commands are now schema-validated with
   `validate_coordination_command` before reaching OK; the dead/misleading import
   in the node was removed.
3. **Missing configurable interfaces** — added a `topics` config dict (defaults +
   partial override) and wired the `/orchestrator/trigger_analysis` service.

---

## 7. Verification status

**Verified offline (macOS, no ROS2):**
- 53 M5 unit tests pass; full suite 279 passed / 2 skipped at merge.
- `ruff check` clean on the package and M5 tests.
- Pure modules import no `rclpy` (NFR5.3); `orchestrator_node.py` byte-compiles.

**Not yet verified (requires a sourced ROS2 environment):**
- `colcon build` of `swarm_orchestrator`.
- The 2 ros2-marked node integration tests (`tests/integration/test_m5_node.py`).
- The `/orchestrator/trigger_analysis` service end-to-end, and live topic wiring.

**Out of scope / pre-existing:** 3 M6 simulation tests
(`tests/simulation/test_m6_scenarios.py`) fail independently of M5; they stem from
modified `isaac/config/scenarios/*.yaml` and are unrelated to this module.

---

## 8. Commit history

Merged via `779d7ec` (`--no-ff`). Underlying commits:

```
2334524 chore: wire M5 test path, ros2 marker, and package deps
6ec1278 feat: add M5 orchestrator data models and parsing helpers
55bac23 feat: implement M5 progress-based congestion detector
389b3f2 feat: extend M5 task registry with coordination overrides and JSON
a9f17be feat: add M5 command tracker and cooldown tracker
8c4c032 feat: implement M5 orchestrator state machine
a0470d5 feat: add M5 reasoning pipeline adapter, frame dump, and fan-out
7e3f105 feat: implement M5 orchestrator ROS2 node, config, and launch
82c2cb3 chore: lint fixes for M5 orchestrator
5bcadf6 fix: catch M2 failures and validate grounded commands in M5 pipeline
8c094cf feat: configurable M5 topics, trigger service, and worker-failure guard
```

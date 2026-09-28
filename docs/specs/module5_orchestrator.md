# Module 5 — Orchestrator — Implementation Spec

**Status:** Implementation target — design approved · **Level:** Implementation · **Source:** `project_proposal.md` §4.1, §4.6
**Layer:** 2 (semantic reasoning controller) · **Producers consumed:** M1 (perception), M2 (VLM), M3 (RAG), M4 (status) · **Consumers:** M1 (task registry), M4 (commands)

---

## 1. Overview

M5 is the central state machine that realizes the proposal's core principle:
**"Layer 2 intervenes only when Layer 1 fails."** It watches the perception
stream, decides *when* a jam is real, runs the M2→M3 reasoning pipeline, dispatches
the resulting commands to M4, tracks their lifecycle, and owns the task/status
registry that feeds M1.3.

**In scope:** congestion detection (progress-based stall timing), the
analyze→ground→dispatch state machine, in-process invocation of M2 and M3,
command fan-out and lifecycle tracking, cooldown/dedup gating, and the
coordination-task registry published to M1.

**Out of scope:** perception/state estimation (M1), the VLM decision itself (M2),
command grounding logic (M3), per-robot execution and safety enforcement (M4), and
mission planning. M5 does **not** assign initial mission goals — those load from
scenario/launch config at startup. M5 manages *coordination overrides* only.

**Trigger-policy ownership (§4.1):** M5 is the sole owner of *when* M2 runs. M2 and
M3 are stateless request/response services; M5 supplies the request and decides
whether to act on the result. Layer 1 (Nav2 via M4) runs continuously and is never
paused by M5 — coordination commands modulate it, they do not replace it.

**Integration principle:** M2 and M3 are non-ROS2 Python under `reasoning/`. M5
invokes them **in-process** (`reasoning.vlm.Reasoner.run` and the M3 grounding
entry point) on a background executor, behind a `ReasoningPipeline` Protocol so the
node logic stays unit-testable with a mock. The `/reasoning/analyze` ROS2 action
described in the M2 spec §5 is an alternative deployment and is **not** used here;
this is the deliberate, approved deviation for M5.

---

## 2. Inputs & Outputs

**Inputs**
- `SceneState` from M1 (`/perception/scene_state`, JSON `std_msgs/String`) — robot
  positions, headings, velocities, status, task strings, and the per-frame
  `dropped_frame` diagnostic. Parsed in the node into the internal `SceneSnapshot`
  projection (§4); M5 does **not** import `swarm_perception` models.
- Annotated frame from M1 (`/perception/annotated_frame`, `sensor_msgs/Image`,
  RGB) — buffered as a latest-frame slot together with its `frame_id`/stamp.
  `ReasonerRequest.image_path` is mandatory for M2, so at trigger time the
  background pipeline task writes the buffered frame to disk and passes that path
  (FR5.3.6). No frame buffered, or buffered frame stale beyond the skew limit →
  the trigger is suppressed (E9/E10).
- `CoordinationStatus` from M4 (`/coordination/status`) — per-command execution
  progress (`command_id`, `robot_id`, `status`, `detail`).
- Optional manual trigger: `TriggerCongestionAnalysis` service
  (`/orchestrator/trigger_analysis`) for operators/tests to force an analysis cycle.
- `OrchestratorConfig` from launch/config: thresholds, cooldowns, command timeouts,
  reasoning backend selection, frame dump location, and the initial task
  assignments per robot — task string **and goal coordinates** (the detector's
  distance-to-goal needs goal positions, and config is their single source; M1's
  `RobotState.goal` is itself read back from M5's registry).

**Outputs**
- `CoordinationCommand` messages to M4 (`/coordination/commands`) — **one per
  robot**, fanned out from the single grounded command produced by M3.
- Task/status registry to M1 (`/coordination/tasks`, JSON `std_msgs/String`) —
  per-robot **effective** task strings and goals for M1.3 annotation: the base
  mission assignment, overlaid by the active coordination override while a
  dispatched command is unresolved (FR5.5.4). Without the overlay, M1 frames and
  M2 prompts would show stale goals during the very interventions M5 issues.
- `OrchestratorDiagnostics` (logging/observability) — current state, last
  `request_id`, trigger reason, pipeline latency, dispatch/lifecycle counters.

### 2.1 Data Flow

```mermaid
flowchart TD
    AF[["/perception/annotated_frame"]] --> BUF["latest-frame buffer"]
    BUF -.->|"written to image_path at trigger"| PIPE
    SS[["/perception/scene_state (SceneState JSON)"]] --> DET
    DET["CongestionDetector.update"]
    CFG[("OrchestratorConfig")] -.-> DET
    DET -->|"CongestionEvent | None"| SM["OrchestratorStateMachine"]
    SM -->|"not gated → ANALYZING"| PIPE
    SM -->|"gated by cooldown / active cmd"| MON["stay MONITORING"]
    PIPE["ReasoningPipeline.run (background executor)"]
    PIPE --> M2["reasoning.vlm.Reasoner.run"]
    M2 -->|"ReasonerResult"| PIPE
    PIPE -->|"decision present → GROUNDING"| M3["reasoning.rag grounding"]
    M3 -->|"grounded command dict"| PIPE
    PIPE -->|"PipelineOutcome"| SM2["OrchestratorStateMachine (result handoff)"]
    SM2 -->|"success → DISPATCHING"| FAN["fan-out → N CoordinationCommand"]
    FAN --> CMD[["/coordination/commands → M4"]]
    FAN --> TRK["CommandTracker.register (PENDING)"]
    ST[["/coordination/status ← M4"]] --> TRK
    TRK -->|"resolved (COMPLETED/FAILED/TIMED_OUT)"| CD["start cooldown for robots"]
    TRK -->|"resolved → AttemptMemory.resolve"| AM["AttemptMemory (last attempt, windowed)"]
    AM -.->|"failure_context on re-analysis"| PIPE
    SM2 -->|"any failure → diagnostics + cooldown"| CD
    CD --> MON2["return to MONITORING"]
    FAN -->|"set overrides (involved robots)"| REG["TaskRegistry → /coordination/tasks → M1"]
    TRK -->|"resolved → clear overrides"| REG
```

When the detector returns `None`, or M2 returns `congestion_detected=false`
/ `decision=None`, M5 dispatches nothing and Layer 1 stays in control.

---

## 3. Functional Requirements

### M5.1 Congestion Detector
- FR5.1.1 Track each robot's **distance-to-goal progress** over time, not raw
  motion status. A robot is *stalled* when its minimum observed distance-to-goal
  has not improved by more than `progress_epsilon_m` for at least
  `stall_threshold_sec`, while it has an active task with a goal.
- FR5.1.2 Set `stall_threshold_sec` longer than Nav2's recovery cycle (≈5–10 s) so
  Layer 2 backstops Layer 1 rather than pre-empting it.
- FR5.1.3 Exclude `STALE` robots as trigger evidence; they carry no reliable
  position. Robots with no goal/task are not candidates for stall.
- FR5.1.4 **Hold detector state on dropped frames.** When `SceneState` indicates a
  late/suppressed frame (`dropped_frame=True` or empty robot list with the
  diagnostic set), do not advance timers or interpret the gap as progress/recovery.
- FR5.1.5 Emit a `CongestionEvent` (involved robot IDs, per-robot stall durations,
  `detected_at`, trigger reason) when one or more robots cross the stall threshold.
  Implemented as a pure stateful class:
  `CongestionDetector.update(scene_state, task_registry, now) -> CongestionEvent | None`,
  thresholds injected from config, **no `rclpy` import**.
- FR5.1.6 Spatial clustering (require N robots jammed within a radius) is a future
  refinement and explicitly out of scope for this milestone.
- FR5.1.7 (2026-09-17) Exclude robots within `goal_reached_tolerance_m` (default
  0.15 m, > Nav2's 0.1 m `xy_goal_tolerance`) of their effective goal from stall
  evidence, clearing any existing progress bookkeeping the same way `STALE`
  robots are handled. Runs C, D, G, H showed an arrived robot reads as
  permanently "stalled" (distance never improves because it is parked), which
  triggered spurious re-analysis cycles and, in run H, a bad `yield` that moved
  a parked robot off its goal. The close/slow-pair check is unaffected — two
  robots genuinely jammed at a goal are still flagged.
- FR5.1.8 (2026-09-17) Treat M4's arrival report (`CoordinationStatus` with
  `command_id="base_mission"`, `status="COMPLETED"`) as authoritative: the
  detector marks the robot arrived at its current effective goal and excuses it
  from progress-stall evidence while M1 still places it within
  `arrived_radius_m` (default 0.5 m) of that goal; the mark lapses when the
  robot is seen farther away or its effective goal changes. A robot that merely
  stalls short of its goal is never excused (Nav2 must have confirmed arrival).
  `CongestionEvent.distance_to_goal_m` carries each stalled robot's M1
  distance, and the `starting analysis` log prints it, so M1's offset at the
  goal is measurable. **Why:** run 4 (2026-09-17) fired `2 robot(s) stalled`
  every cooldown for 9 min on two robots parked at their goals (31 needless VLM
  calls) — M1's estimate exceeded `goal_reached_tolerance_m` where ground truth
  said 0.04–0.08 m. The close/slow-pair check is unaffected.
- FR5.1.9 (2026-09-25) **Position-verify M4's arrival report before acting on
  it** when `arrival_position_check` is true (the default). On `base_mission`
  COMPLETED, cross-check the reported goal against M1's latest estimate for
  that robot (`arrival.classify_arrival`, §7.8):
  - within `arrival_position_tolerance_m` (default 0.35 m) →
    `within_tolerance`, accepted: mark arrived (FR5.1.8), end the episode, and
    log `robot <id> arrived at base goal (x, y) distance_m=<d> check=<reason>`;
  - beyond it → `beyond_tolerance`, **rejected**: do *not* mark the robot
    arrived, do *not* end the episode, and log `arrival rejected robot=<id> …
    (Nav2 reported success)`. The robot stays stall-eligible, so a robot
    stalled short of its goal can still trigger an analysis cycle;
  - no estimate, an estimate older than `arrival_estimate_max_age_sec`
    (default 2.0 s), or a `STALE` robot (whose position M1 carries forward
    frozen) → `no_estimate`/`stale_estimate`, accepted but logged as
    unverified. An M1 outage must not block every arrival in a run.

  A rejected arrival is held pending and re-checked on each scene: once M1
  itself places the robot within tolerance of the same effective goal it is
  accepted late (`arrival accepted late robot=… distance_m=…`), once, with no
  second Nav2 success required. The pending mark is dropped if the effective
  goal changes, and a dropped/late frame resolves nothing (FR5.1.4). Running
  accepted/rejected/late event tallies ride on those two log lines.

  **Episode closure follows the verdict.** `EpisodeOrderTracker.end_episode`
  now fires only on an accepted (or late-accepted) arrival, so a rejected one
  leaves the episode open and the next `order_for` on those robots reuses its
  index and drawn order rather than drawing again. This is what FR5.3.9 already
  specifies ("the drawn order is constant across every re-analysis of one
  episode") — a false success was splitting one real episode into two draws —
  but it means `prompt_robot_order: random` draw sequences are not comparable
  across this change.

  **Why:** the arrival report is the primary outcome measure of the congestion
  experiment, so a Nav2 false success becomes a false "episode succeeded". In
  run 20260925_124609 `bt_navigator` reported success for robot_2 while M1 put
  it 0.59 m from the goal — M5's own later analyses logged
  `distance_to_goal_m={'robot_2': 0.59}` 21 times. The tolerance must exceed
  M1's ≈0.1 m camera bias at the goal (0.15 m measured vs 0.06 m ground truth,
  2026-09-17) and stay at or below `arrived_radius_m` (enforced in
  `OrchestratorConfig`). Stall behaviour changes only in the
  `arrival_position_tolerance_m < d ≤ arrived_radius_m` band, where a false
  success was previously excused from stall evidence; at 0.59 m the FR5.1.8
  mark already lapsed, so there the harm was the arrival log line and the
  episode end, not stall suppression.

### M5.2 Orchestrator State Machine
- FR5.2.1 Maintain an explicit node-visible state:
  `MONITORING | ANALYZING | DISPATCHING`. The approved logical pipeline is
  `analyze → ground`, but because M2 and M3 run inside one bundled background call
  (FR5.3.2), grounding is **not** a separately observable node state — it is a
  sub-phase of `ANALYZING`, surfaced via `PipelineOutcome.terminal_stage` for
  diagnostics (see §8). Only `MONITORING` consumes new congestion events; events
  arriving in other states are ignored (single in-flight cycle).
- FR5.2.2 On a `CongestionEvent` in `MONITORING`, transition to `ANALYZING` only if
  the involved robots are **not** under cooldown and have **no** active command.
  Otherwise remain in `MONITORING`.
- FR5.2.3 Generate a `request_id` per cycle and thread it through M2, M3, dispatch,
  diagnostics, and logs for end-to-end traceability (C2).
- FR5.2.4 On pipeline success with `congestion_detected=true` and a valid grounded
  command, transition `ANALYZING → DISPATCHING`, fan out commands, then return to
  `MONITORING`.
- FR5.2.5 On `congestion_detected=false` or `decision=None`, dispatch nothing,
  record the outcome, start a short cooldown for the involved robots, and return to
  `MONITORING`.
- FR5.2.6 The state machine is pure transition logic over injected inputs (event,
  pipeline outcome, status update, clock) with **no `rclpy`** and no I/O.
- FR5.2.7 Maintain a per-robot **consecutive-failure counter**: incremented when a
  cycle involving the robot ends in failure (M2 `decision=None`, grounding failure,
  M4 `FAILED`/`TIMED_OUT`), reset on a cycle that resolves `COMPLETED`. Exposed in
  `OrchestratorDiagnostics`. No escalation behavior is built on it this milestone;
  it exists so a future escalation policy (§14) is a pure threshold check.

### M5.3 Reasoning Pipeline Adapter
- FR5.3.1 Expose a `ReasoningPipeline` Protocol with one method
  `run(request: ReasonerRequest) -> PipelineOutcome`, backend/transport agnostic.
- FR5.3.2 `InProcessPipeline` is the default adapter: it calls
  `reasoning.vlm.Reasoner.run`, and on a present decision with
  `congestion_detected=true`, calls the M3 grounding entry point, validating the
  result with `reasoning.rag.command_grounder.validate_coordination_command`.
- FR5.3.3 The pipeline runs on a **background executor**, never on the node's
  high-rate callback/spin thread. Results are handed back thread-safely.
- FR5.3.4 `PipelineOutcome` carries: the M2 `ReasonerResult` (decision +
  diagnostics), the grounded command dict (or `None`), a terminal stage marker
  (`vlm | grounding | ok`), and a failure reason when unsuccessful.
- FR5.3.5 M3 is currently a stub; M5 depends on the M3 **contract** (a
  `coordination_command`-schema dict) behind this Protocol, so M5 can be built and
  unit-tested against a mock pipeline before M3 is implemented.
- FR5.3.6 Maintain a **latest-frame buffer** fed by `/perception/annotated_frame`
  (single slot: frame bytes + `frame_id` + stamp). The raw buffered bytes are
  handed to the background pipeline task, which writes the PNG to
  `config.frame_dump_dir/<request_id>.png` **before** calling `Reasoner.run` and
  passes that path as `ReasonerRequest.image_path` (mandatory in the M2 contract).
  No disk I/O or PNG encoding on the node's spin thread. The frame is RGB at the
  M1 boundary; convert to BGR at the `cv2.imwrite` boundary (annotation status
  *colors* are semantic — a swapped-channel dump corrupts what M2 reads). If
  `config.frame_downscale_width` is set, downscale (preserving aspect) before
  writing to bound base64 payload size. Delete the file when the cycle resolves
  unless `config.keep_debug_frames` is true. If no frame has been received yet, or
  the buffered-frame stamp lags the scene-state stamp by more than
  `frame_scene_max_skew_sec`, suppress the trigger (E9/E10).

- FR5.3.7 (2026-09-17) Every decision artifact
  (`decision_log_dir/<request_id>.json`) records, besides the M2 result and
  grounding outcome: `run_id` (from `VGU_RUN_ID`, exported by the launcher;
  `null` if unset), `session_id` (per M5 process), `failure_context`, the
  **rendered prompt** (`system_prompt`, `user_prompt`, SHA-256 of each —
  rebuilt by the pure prompt builder from the exact `ReasonerRequest` sent, so
  a re-ask suffix on retry is not captured), the M1 `scene` snapshot the
  request was built from, and the detector's `distance_to_goal_m`. The request
  is built on the callback thread so the artifact and the worker share one
  object. Independently of triggers, M5 appends one scene snapshot per
  `scene_log_period_sec` to `scene_log_dir/<session_id>.jsonl` (`t`,
  `session_id`, `run_id`, `scene`) for offline trajectory reconstruction;
  `scene_log_dir: null` disables it. **Why:** the run-3 investigation could not
  reconstruct what the VLM was told nor prove M1's distance at a goal — both
  were unlogged.

- FR5.3.8 (2026-09-19) `build_reasoner_request` (`reasoning_pipeline.py`)
  forwards `config.static_obstacles` and `config.prompt_static_obstacles` into
  `ReasonerRequest.static_obstacles` / `include_static_obstacles` unchanged,
  the same pass-through `prompt_pairwise_geometry` already has. `static_obstacles`
  is configuration mirrored by hand from the scenario yaml, the same
  relationship `scenario_geometry` (config table below) already has to the
  scenario's aisle barrier — it must be set per scenario, since a list left
  over from another scenario would describe obstacles that are not there. Its
  `obstacle_id` values render verbatim into the VLM prompt (M2 FR2.1.8), so
  they must stay non-semantic (e.g. `obstacle_1`, not the scenario yaml's
  `blocker_west`) and must **not** be synced to the scenario yaml's
  descriptive obstacle names — only the geometry is mirrored, never the
  naming, because an id stating the object's role or side would hand the
  model the inference the modality exists to measure. `prompt_static_obstacles`
  defaults false for the reason `prompt_pairwise_geometry` documents at
  rev-8.5: every decision artifact collected before 2026-09-19 was produced
  without this channel, and an on-by-default flag would silently break
  comparability with all of them on this axis. This is narrower than full
  prompt comparability with that corpus — M2 FR2.1.9's `yield_robot` field
  landed in the same window as a permanent, non-switchable prompt change, so
  the pre-2026-09-19 corpus is not reproducible even with
  `prompt_static_obstacles` off (see M2 FR2.1.8/FR2.1.9).

- FR5.3.9 (2026-09-25) `prompt_robot_order` selects the order the VLM prompt
  lists robots in: the fixed `id_asc` (default) and `id_desc`, or `random`,
  which draws one of the two **per congestion episode** so a single run is
  counterbalanced internally. `presentation_order.py` owns the draw:
  `PresentationOrderPolicy(mode, seed).order_for_episode(k)` is pure and
  deterministic — the same seed and episode index always yield the same order,
  and consecutive episodes are independent draws off one `random.Random(seed)`
  stream — while `EpisodeOrderTracker` holds the episode and hands every
  re-analysis inside it the same order. An episode opens on the first analysis
  whose robot set is disjoint from the tracked one and closes when any of its
  robots reports an arrival. It deliberately does **not** reuse `AttemptMemory`'s
  scope: that memory is disabled at `failure_context_window_sec: 0` (the RQ5
  memoryless control), which would make every re-analysis look like a new
  episode and re-draw inside one deadlock. `prompt_robot_order_seed: null`
  derives the seed from `VGU_RUN_ID`, falling back to the M5 session id, via
  SHA-256 rather than `hash()`, whose string hashing `PYTHONHASHSEED`
  randomizes per process; paired runs launched with the same run id therefore
  draw the same sequence. **Why:** the 2026-09-25 probe showed `yield_robot`
  follows the presentation slot (`docs/reports/2026-09-25-presentation-order-probe.md`),
  so the order must be a randomized, auditable condition rather than a fixed
  property of the corpus. Every decision artifact records
  `robot_presentation_order` (the effective order, read off the request that
  rendered the prompt, so it can never disagree with the persisted prompt
  hashes), `prompt_robot_order_mode`, `prompt_robot_order_seed` and
  `episode_index`; the `starting analysis` log line carries `order=`. The 1 Hz
  scene log does not: most snapshots fall outside any episode, so the fields
  would be null on nearly every line.
  **Three or more robots (2026-09-28, T2b).** The episode also tracks its
  *members*: the analysed sets plus every robot a dispatched command names and
  every queued follower folded into it. A single stalled robot outside the
  robots of an in-flight command that moves two or more robots is **folded**
  (`DirectiveKind.FOLDED`, `state_machine.is_queued_follower`): no analysis
  starts mid-maneuver, the robot joins the episode's members and
  `AttemptMemory`'s scope, and its next stall after the command resolves is
  analysed inside the same episode. Once an episode has three or more members,
  overlap is tested against the members and the episode closes on the **last**
  member's arrival. A two-robot scene cannot reach three members or fold
  (a command moving two robots covers both), so every two-robot rule above is
  unchanged (pinned against the pre-change tracker in
  `tests/unit/test_m5_presentation_order.py`).
- FR5.3.10 (2026-09-25) Every decision artifact records the outcome of M3's
  yield feasibility gate (`grounding_yield_feasibility`, FR3.x in
  `docs/specs/module3_rag_grounding.md`): the configured mode under that key,
  plus `yield_robot_grounded_from`, `yield_regrounded_reason` and
  `yield_refusal_reason` read back off the grounded command by
  `summarize_yield_grounding` (`reasoning_pipeline.py`). **Why:** with the gate
  on, the robot that executes a yield need not be the robot M2 named, and
  `decision.yield_robot` alone would silently misattribute that. The mode is
  recorded even on cycles where the gate did not fire, so an artifact set stays
  partitionable by the condition it was collected under. A swap or a refusal
  also emits one M5 INFO line — `yield re-grounded request=<id> from=<a>
  to=<b> reason=<…>` / `yield refused request=<id> reason=<…>` — so a run that
  changed executor is legible without opening the artifacts.

- FR5.3.11 (2026-09-25) Every decision artifact records
  `reasoner_config_effective`: the sampling parameters the call actually ran
  under — `backend_id`, `model_id`, `temperature`, `top_p`, `top_k`,
  `presence_penalty`, `max_attempts`, `max_tokens`, gemini's `seed` and
  `thinking_level`, and the `unsupported_sampling` subset the backend reported
  dropping (M2 `EffectiveSamplingConfig`). Values are the *configured* ones,
  described by `describe_effective_sampling(reasoner_config, backend_config)`
  and handed to the `Reasoner` at construction, never echoed back by a
  provider. **Why:** no artifact in the corpus proved gpt-4o ran greedily; the
  temperature lived only in `config/models.yaml`, which is not captured per
  run. Separately, `keep_raw_frames` (with `keep_debug_frames`) also dumps M1's
  *input* frame as `frame_dump_dir/<request_id>_raw.png`, downscaled exactly
  like the annotated dump, from a best-effort depth-1 subscription to
  `raw_frame_topic` whose newest frame is snapshotted on the callback thread at
  submit time; M5 logs `raw frame skew_sec=<raw − annotated>`. The M2 request
  is unchanged — it still carries the annotated frame — so an annotated-vs-raw
  replay has both frames of one instant. A missing raw frame is logged and
  skipped, never raised: debug evidence must not fail an analysis.
- FR5.3.12 (2026-09-27) `t0_probe_mode` (default **false**) runs the T0
  negative-control probes of the congestion-resolution design
  (`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`,
  "Scenario battery", T0): every `t0_probe_interval_sec` (default 20.0; cap
  `t0_probe_max_probes`, 0 = unlimited) M5 runs the M2 analysis **off-trigger**
  on the latest scene in **log-only** mode. A probe is built with the same
  `build_reasoner_request` and frame dump as a triggered analysis, writes the
  same decision artifact plus `probe: true` and `probe_index`, gets an Arm B
  shadow record (`prior_attempts_source: t0_probe`), and logs
  `starting analysis request=<id> robots=[…] reason=t0_probe order=<o> probe=true
  probe_index=<k>`. **No command may be emitted**, enforced in two layers: (1)
  structurally, the probe path calls only `InProcessPipeline.analyze` (M2
  only, terminal stage `probe`) and records the outcome in
  `_handle_probe_outcome`, which never reaches the state machine, cooldowns,
  `AttemptMemory`, the tracker, the registry or `_dispatch`; (2) defensively,
  `_dispatch` refuses any request id in the `ProbeLedger` with an ERROR line
  `refusing dispatch request=<id>: t0 probe outcomes are log-only`. Probes do
  not perturb triggered analyses: they carry no failure context (its wording
  asserts congestion was re-detected, and reading `AttemptMemory` can clear
  it), leave `EpisodeOrderTracker` alone (probe *k* renders
  `PresentationOrderPolicy(mode, seed).order_for_episode(k)`; the artifact's
  `episode_index` is null), use a shadow path that neither counts an attempt
  nor consumes feed errors, and run on their own single-worker executor, so a
  real trigger that fires while a probe is in flight starts at once. A probe
  never starts while a triggered analysis is in flight, while the previous
  probe is unfinished, or without a fresh frame; a due probe that is blocked
  stays due and fires on the first free timer tick (`t0 probe deferred
  reason=<r>` is logged once per reason). With the mode off, every artifact
  and log line is byte-identical to before (probe keys are written only for
  probes). `scripts/rescore_arrivals.py` times resolution from the first
  `starting analysis` line and does not yet skip `reason=t0_probe`; do not
  rescore T0 runs with it.

### M5.4 Command Lifecycle & Fan-out
- FR5.4.1 Translate the single grounded command (schema: `command_id`, `actions[]`,
  `expected_resolution_time_sec`, `fallback`) into **N** ROS2 `CoordinationCommand`
  messages, one per `actions[i].robot_id` (see §9.2 mapping table).
- FR5.4.2 Track each dispatched command in a `CommandTracker` keyed by
  `command_id`, with per-robot `CommandState`
  (`PENDING → ACTIVE → COMPLETED | FAILED | TIMED_OUT`).
- FR5.4.3 Mark a command `TIMED_OUT` if no resolving `CoordinationStatus` arrives
  within its `timeout_sec` (derived from `expected_resolution_time_sec`).
- FR5.4.4 A command is *resolved* when all its robots reach a terminal state. On
  resolution, start the cooldown for those robots so the same jam is not
  re-triggered immediately.
- FR5.4.5 Retain the grounded command's `fallback` string with the record for
  diagnostics and future escalation; this milestone does not auto-execute fallback.
- FR5.4.6 (2026-09-17) Keep the last dispatched attempt (decided strategy, the
  maneuver actually fanned out — the decided strategy if its own action ran,
  else the single action name, else `mixed` — yielder, outcome) in a single-slot
  `AttemptMemory`. When a new analysis starts for an
  overlapping robot set within `failure_context_window_sec` of that command's
  resolution — whatever the outcome — attach it to the `ReasonerRequest` as
  `failure_context` and record it in the decision artifact. The memory is
  dropped on expiry, on an analysis for a disjoint robot set, or when a new
  attempt is dispatched; `0` disables it (RQ5 memoryless control). Design:
  `docs/superpowers/specs/2026-09-17-failure-context-closed-loop-design.md`.

### M5.5 Task / Status Registry
- FR5.5.1 Own the registry published on `/coordination/tasks` (JSON). Each entry
  holds the **base** mission assignment (task string + goal coordinates) and an
  optional **active coordination override** (action + override goal, `command_id`).
  The published JSON carries the **effective** task and goal: the override while
  one is active, the base assignment otherwise.
- FR5.5.2 Load initial per-robot base assignments (task **and goal**) from
  `OrchestratorConfig` at startup and publish once at startup and on change. M5
  never derives motion status (MOVING/SLOW/STOPPED/STALE) — that stays local to M1.
  A `TaskAssignment.start_delay_sec > 0` (added 2026-09-28 for T2b's queued
  `robot_3`) holds that robot's base mission back: until the delay has passed
  since M5 started (wall clock, like the stall and cooldown timers) its entry
  also carries `"start_pending": true`, M4's base-mission driver does not drive
  it, and it gives no progress-stall or arrival evidence; it stays in the
  registry, so M1 keeps tracking it, and the prompt still shows its goal. The
  timer then republishes the registry without the flag. Absent or 0 publishes
  exactly the pre-existing JSON.
- FR5.5.3 Provide deterministic JSON serialization (sorted by `robot_id`) so the
  published registry is reproducible and diff-friendly.
- FR5.5.4 On command dispatch, set the override for each involved robot; when the
  command resolves (`COMPLETED`/`FAILED`/`TIMED_OUT`), clear the override so the
  effective goal **reverts to the base assignment**. Every override change
  republishes the registry.

### M5.6 ROS2 Node
- FR5.6.1 Keep callbacks thin: convert messages → models, call pure logic, publish.
  No reasoning/HTTP work in the subscription callback path.
- FR5.6.2 Use a periodic timer to drive command-timeout checks and to poll the
  background pipeline future for completion.
- FR5.6.3 Read all topic names, thresholds, timeouts, backend selection, and initial
  tasks from launch/config — no hardcoded alternates in source.
- FR5.6.4 Fail-fast at startup on invalid config (missing thresholds, unknown
  backend id, malformed initial-task map).

---

## 4. Data Structures / Schemas (contract C1)

New Pydantic v2 frozen models (`swarm_orchestrator/models.py`). Existing ROS2
messages (`CoordinationCommand`, `CoordinationStatus`, `RobotState`) and reasoning
models (`ReasonerRequest`, `ReasonerResult`, `CongestionDecision`) are reused, not
redefined.

**`OrchestratorConfig`** (frozen)

| field | type | notes |
|---|---|---|
| stall_threshold_sec | float | > Nav2 recovery cycle; default ≈ 12.0 |
| progress_epsilon_m | float | min distance-to-goal improvement counted as progress |
| cooldown_sec | float | per-robot re-trigger suppression after resolution/failure |
| failure_context_window_sec | float | seconds after command resolution in which the last attempt is attached to a re-analysis as `failure_context`; 0 disables (RQ5 memoryless control) |
| command_timeout_sec | float | fallback timeout when grounded value absent |
| reasoning_backend_id | str | passed through to M2 backend factory |
| initial_tasks | dict[str, TaskAssignment] | robot_id → base task + goal (+ optional `start_delay_sec`, FR5.5.2), loaded at startup |
| frame_dump_dir | str | directory for trigger-time frame PNGs (FR5.3.6) |
| scene_log_dir | str or null | directory for the per-session 1 Hz scene JSONL (FR5.3.7); null disables |
| scene_log_period_sec | float | scene-log period, default 1.0 (FR5.3.7) |
| arrived_radius_m | float | radius within which an M4-reported arrival excuses a robot from stall evidence, default 0.5 (FR5.1.8) |
| arrival_position_check | bool | (2026-09-25) cross-check M4's `base_mission` arrival report against M1's position before marking the robot arrived, default **true** (FR5.1.9) |
| arrival_position_tolerance_m | float | (2026-09-25) max M1 distance-to-goal that corroborates a reported arrival, default 0.35; must be > 0 and ≤ `arrived_radius_m` (FR5.1.9) |
| arrival_estimate_max_age_sec | float | (2026-09-25) oldest M1 estimate still allowed to corroborate an arrival, default 2.0; beyond it the arrival is accepted unverified (FR5.1.9) |
| prompt_pairwise_geometry | bool | include the derived pairwise distance/facing lines in the VLM prompt, default true (M2 FR2.1.7; ablation axis) |
| prompt_static_obstacles | bool | (2026-09-19) render `static_obstacles` below as world-frame boxes in the VLM prompt, default **false** (M2 FR2.1.8; ablation axis) |
| static_obstacles | tuple[StaticObstacleInput, ...] | (2026-09-19) fixed obstacles mirrored from the scenario yaml for the prompt only, rendered when `prompt_static_obstacles` is true; default empty |
| prompt_robot_order | `"id_asc"` \| `"id_desc"` \| `"random"` | (2026-09-25) order the VLM prompt lists robots in, default `id_asc`; `random` draws per congestion episode (FR5.3.9; ablation axis) |
| prompt_robot_order_seed | int \| None | (2026-09-25) seed for the `random` draw; null derives it from `VGU_RUN_ID`, falling back to the session id, so paired runs share the sequence (FR5.3.9) |
| grounding_yield_feasibility | `"off"` \| `"swap"` \| `"refuse"` | (2026-09-25) whether M3 may move a yield off the robot M2 named when that robot is boxed in; default `"off"`, and a no-op unless both `static_obstacles` and `scenario_geometry` are set (FR5.3.10; M3 spec §yield feasibility; experimental condition) |
| t0_probe_mode | bool | (2026-09-27) run T0 log-only VLM probes off-trigger; default **false** (FR5.3.12) |
| t0_probe_interval_sec | float | (2026-09-27) seconds between probe starts, > 0, default 20.0 (FR5.3.12) |
| t0_probe_max_probes | int | (2026-09-27) probes per M5 process, ≥ 0, default 0 = unlimited (FR5.3.12) |
| keep_debug_frames | bool | retain dumped frames after cycle resolution; default false |
| keep_raw_frames | bool | (2026-09-25) with `keep_debug_frames`, also dump M1's input frame as `<request_id>_raw.png` beside the annotated one; default **false** (FR5.3.11) |
| raw_frame_topic | str | (2026-09-25) camera topic the raw dump subscribes to (M1's `image_topic`), default `/camera/image_raw`; read only when `keep_raw_frames` is on (FR5.3.11) |
| frame_scene_max_skew_sec | float | max frame/scene stamp skew; beyond it the trigger is suppressed (E10) |
| frame_downscale_width | int \| None | optional pre-dump downscale width; None = full resolution |
| topics | dict[str, str] | resolved topic names (defaults in §5) |

**`TaskAssignment`** (frozen)

| field | type | notes |
|---|---|---|
| task | str | task string shown by M1.3 |
| goal | tuple[float, float] | world-frame goal `(x, y)` in meters |

**`SceneSnapshot`** / **`RobotView`** (frozen) — M5's internal projection of the
M1 `SceneState` JSON, parsed in the node. `RobotView`: `robot_id`, `x`, `y`,
`theta`, `linear_velocity`, `status`, `stamp`. `SceneSnapshot`: `stamp`,
`frame_id`, `robots: list[RobotView]`, `dropped_frame: bool`. Defined locally so
`swarm_orchestrator` does not import `swarm_perception` models (C1: modules stay
independently upgradeable behind the JSON contract).

**`CongestionEvent`** (frozen)

| field | type | notes |
|---|---|---|
| involved_robots | list[str] | stalled robot IDs (sorted) |
| stall_durations_sec | dict[str, float] | per-robot stall time at detection |
| detected_at | float | monotonic timestamp |
| reason | str | human-readable trigger reason |

**`CommandRecord`** (mutable tracker entry)

| field | type | notes |
|---|---|---|
| command_id | str | grounded command id |
| robot_states | dict[str, CommandState] | per-robot lifecycle state |
| dispatched_at | float | dispatch timestamp |
| timeout_sec | float | resolution deadline |
| fallback | str | retained fallback strategy |
| request_id | str | originating analysis cycle |

**`PipelineOutcome`** (frozen)

| field | type | notes |
|---|---|---|
| request_id | str | cycle correlation id |
| reasoner_result | ReasonerResult | M2 output (decision may be None) |
| grounded_command | dict \| None | M3 `coordination_command` dict |
| terminal_stage | enum | `vlm \| grounding \| ok` |
| failure_reason | str \| None | set when not `ok` |

**`OrchestratorDiagnostics`** (frozen) — current state, last `request_id`, last
trigger reason, pipeline latency, dispatch count, active-command count, and
per-robot consecutive-failure counts (FR5.2.7).

---

## 5. Interfaces

**ROS2 topics & services** (default names; overridable via config)

| direction | name | type | role |
|---|---|---|---|
| sub | `/perception/scene_state` | `std_msgs/String` (SceneState JSON) | perception input from M1 |
| sub | `/perception/annotated_frame` | `sensor_msgs/Image` (RGB) | latest-frame buffer for M2 image input (FR5.3.6) |
| sub | `/coordination/status` | `swarm_interfaces/CoordinationStatus` | execution feedback from M4 |
| pub | `/coordination/commands` | `swarm_interfaces/CoordinationCommand` | per-robot commands to M4 |
| pub | `/coordination/tasks` | `std_msgs/String` (registry JSON) | task/status registry to M1 |
| srv | `/orchestrator/trigger_analysis` | `swarm_interfaces/TriggerCongestionAnalysis` | manual analysis trigger |

The `/coordination/commands` name (plural) is the established contract in
`docs/modules.md` §M4.1, `docs/isaac_vlm_pipeline.md`, and `project_proposal.md` §M4.
Changing any of these requires updating those specs, launch/config, and M4.

**Message field reuse.** M5 dispatches against the existing `CoordinationCommand.msg`
(`command_id`, `robot_id`, `action`, `parameters_json`, `timeout_sec`) and consumes
the existing `CoordinationStatus.msg` (`command_id`, `robot_id`, `status`, `detail`).
The grounded-command schema has no per-robot `timeout_sec`; M5 derives it from
`expected_resolution_time_sec` (§9.2). No new `.msg` fields are required for this
milestone. If a future need arises (e.g., propagating `fallback` to M4), it is
flagged here as a contract change, **not** silently added.

---

## 6. Package Layout

```text
ros2_ws/src/swarm_orchestrator/swarm_orchestrator/
├── __init__.py
├── models.py             # Pydantic contracts (§4)
├── congestion_detector.py # CongestionDetector (extend existing stub) (§7.2)
├── state_machine.py       # OrchestratorStateMachine (§7.3)
├── command_lifecycle.py   # CommandState (exists) + CommandTracker (§7.4)
├── task_registry.py       # TaskRegistry (extend existing stub) (§7.5)
├── presentation_order.py  # PresentationOrderPolicy + EpisodeOrderTracker (FR5.3.9)
├── arrival.py             # classify_arrival + ArrivalGate (FR5.1.9) (§7.8)
├── reasoning_pipeline.py  # ReasoningPipeline Protocol + InProcessPipeline (§7.6)
└── orchestrator_node.py   # thin ROS2 node (§7.7)
```

Pure-logic modules import no `rclpy`. The node imports everything and wires ROS2.

---

## 7. Function Specifications

### 7.1 Data Models (`models.py`)
Implement the §4 models as frozen Pydantic v2 (`ConfigDict(frozen=True)`), with
`field_validator`s for: non-empty `involved_robots`, sorted serialization, and
`stall_threshold_sec`/`cooldown_sec`/`command_timeout_sec` ≥ 0.
`failure_context_window_sec` is 0 or greater than
`cooldown_sec + stall_threshold_sec` (a smaller window can never fire).
`initial_tasks` keys must be non-empty strings.

### 7.2 `CongestionDetector` (`congestion_detector.py`)
Stateful class holding per-robot progress history. Retain the existing pure helper
`is_congested(wait_time_sec, threshold_sec)` for the stall comparison.

```python
class CongestionDetector:
    def __init__(self, config: OrchestratorConfig) -> None: ...
    def update(
        self,
        scene: SceneSnapshot,
        task_registry: TaskRegistry,
        now: float,
    ) -> CongestionEvent | None:
        """Advance per-robot progress timers and emit an event on stall."""
```

Behavior: for each robot with an active task+goal and status ≠ `STALE`, compute
distance-to-goal; track the running minimum and the time it was last improved by
`> progress_epsilon_m`. Stall duration = `now − last_improved_at`. On a dropped/late
frame, return early without mutating timers (FR5.1.4). Emit an event when any
robot's stall duration ≥ `stall_threshold_sec`.

### 7.3 `OrchestratorStateMachine` (`state_machine.py`)
Pure transition object. Methods return the next state and an optional action
directive (e.g., "start analysis", "dispatch", "cooldown"); the node performs side
effects. No `rclpy`, no threads, no I/O. Inputs: current state, optional
`CongestionEvent`, optional `PipelineOutcome`, optional resolved-command signal, and
`now`. Enforces single in-flight cycle (FR5.2.1) and cooldown/active-command gating
(FR5.2.2).

### 7.4 `CommandTracker` + `CooldownTracker` (`command_lifecycle.py`)
`CommandTracker` extends the existing `CommandState` enum: `register(record)`,
`apply_status(status)` (PENDING→ACTIVE→terminal), `check_timeouts(now)` → list of
timed-out commands, `is_resolved(command_id)`.

`CooldownTracker` is the **single owner** of cooldowns — they start both from
command resolution (a record exists) and from pipeline failures where nothing was
dispatched (no record exists), so they cannot live inside `CommandTracker`:
`start(robot_ids, now)`, `active_robots(now) -> set[str]`. The state machine
consults it for FR5.2.2 gating.

### 7.5 `TaskRegistry` (`task_registry.py`)
Extends the existing dataclass: entries become base `TaskAssignment` (task + goal)
plus an optional override slot (`action`, override goal, `command_id`).
`load_initial(config)`, `set_override(robot_id, action, goal, command_id)`,
`clear_override(robot_id)`, `effective(robot_id) -> (task, goal)`, and `to_json()`
(deterministic, sorted by `robot_id`, publishes effective values). The existing
`assign` updates the base assignment.

### 7.6 `ReasoningPipeline` (`reasoning_pipeline.py`)
Protocol + `InProcessPipeline`. The adapter constructs the M2 `Reasoner` from
config, calls `run`, and on a congestion decision invokes M3 grounding +
`validate_coordination_command`. Backend/HTTP details belong to M2/M3; the adapter
only orchestrates and packages a `PipelineOutcome`. Failures from either stage are
caught and reported via `failure_reason`, never raised past the adapter.

### 7.7 `OrchestratorNode` (`orchestrator_node.py`)
Thin node. The scene-state subscription parses JSON into `SceneSnapshot` and calls
`CongestionDetector.update` + `OrchestratorStateMachine`; the annotated-frame
subscription only swaps the latest-frame buffer (no copy beyond the message data,
no disk I/O in the callback). On a "start analysis" directive, hand the buffered
frame bytes + `request_id` to the background pipeline task, which writes the PNG
(RGB→BGR at the `cv2.imwrite` boundary, FR5.3.6), builds the `ReasonerRequest`,
and runs the pipeline; the node stores the future. A periodic
timer polls the future, runs `check_timeouts`, and publishes registry changes. On
pipeline completion, feed the `PipelineOutcome` back into the state machine and, on
success, fan out `CoordinationCommand`s and set registry overrides (FR5.5.4).
Structured logs include `request_id`, `command_id`, `robot_id`. A `base_mission`
COMPLETED status goes through `ArrivalGate` (§7.8) rather than straight to
`CongestionDetector.mark_arrived`; the node supplies M1's latest view of the
robot plus its age, measured from the monotonic receipt time of the latest
snapshot (M1 stamps are on a different clock), and only logs and ends the
episode on the verdict it gets back.

### 7.8 `ArrivalGate` (`arrival.py`)
Pure module, no `rclpy`. One helper and one stateful gate implementing FR5.1.9.

```python
def classify_arrival(
    reported_goal: tuple[float, float],
    estimated_position: tuple[float, float] | None,
    tolerance_m: float,
    estimate_age_sec: float | None,
    max_estimate_age_sec: float,
) -> ArrivalCheck: ...


class ArrivalGate:
    def __init__(self, config: OrchestratorConfig, mark_arrived: MarkArrived) -> None: ...
    def on_nav2_success(
        self,
        robot_id: str,
        goal: tuple[float, float],
        estimate: RobotView | None,
        estimate_age_sec: float | None,
    ) -> ArrivalDecision: ...
    def on_scene(
        self, scene: SceneSnapshot, goal_of: GoalLookup
    ) -> list[ArrivalDecision]: ...
```

`ArrivalCheck` is frozen Pydantic: `accepted: bool`, `distance_m: float | None`,
`reason: "within_tolerance" | "beyond_tolerance" | "no_estimate" |
"stale_estimate"`. `ArrivalDecision` wraps it with `robot_id`, `goal`, and
`late`; its `check` is `None` when `arrival_position_check` is false, which is
the pre-FR5.1.9 unverified path. The gate owns the accepted/rejected/late
tallies (`counts`) and the pending-rejection set (`pending_robots`); it calls
the injected `mark_arrived` itself, so an arrival it rejects never reaches the
detector.

---

## 8. State Transition Table

| state | input | guard | next state | action |
|---|---|---|---|---|
| MONITORING | CongestionEvent | robots free of cooldown & active cmd, fresh frame buffered | ANALYZING | submit pipeline (task dumps frame) |
| MONITORING | CongestionEvent | no frame buffered, or frame stale beyond skew limit | MONITORING | log suppressed (E9/E10) |
| MONITORING | CongestionEvent | robots gated | MONITORING | log suppressed |
| MONITORING | None | — | MONITORING | — |
| ANALYZING | PipelineOutcome(stage=ok) | — | DISPATCHING | fan-out + dispatch |
| ANALYZING | PipelineOutcome(no congestion / decision=None) | — | MONITORING | cooldown(robots) + failure counts |
| ANALYZING | PipelineOutcome(failure) | — | MONITORING | diagnostics + cooldown + failure counts |
| DISPATCHING | dispatch complete | — | MONITORING | register records + set registry overrides |
| any | CoordinationStatus | — | (unchanged) | tracker.apply_status; on resolution: clear overrides + cooldown + update failure counts |
| any | timeout tick | command past deadline | (unchanged) | mark TIMED_OUT + clear overrides + cooldown + failure counts |

GROUNDING is an internal sub-stage of the pipeline run (within ANALYZING from the
node's perspective); it is surfaced via `PipelineOutcome.terminal_stage` for
diagnostics rather than as a node-visible state.

---

## 9. Algorithms & Parameters

### 9.1 Stall detection (per robot, per frame)
1. Skip if frame dropped/late (hold state).
2. Skip robots with no goal or status `STALE`.
3. `d = euclidean(position, goal)`.
4. If `d < min_distance[robot] − progress_epsilon_m`: update `min_distance`,
   `last_improved_at = now`.
5. `stall = now − last_improved_at`; flag if `stall ≥ stall_threshold_sec`.
6. Emit `CongestionEvent` for all flagged robots.

Defaults: `stall_threshold_sec = 12.0`, `progress_epsilon_m = 0.10`,
`cooldown_sec = 15.0`, `command_timeout_sec = 20.0`, `failure_context_window_sec = 60.0`,
`frame_dump_dir = data/logs/m5_frames`, `keep_debug_frames = false`,
`frame_scene_max_skew_sec = 1.0`, `frame_downscale_width = None` (full 1280×960;
set e.g. 800 if backend latency from the ~2 MB base64 payload becomes a problem).
All overridable via config.

Distance-to-goal uses the robot's **effective** goal from the registry
(override while active, base otherwise), so a robot making progress toward a
coordination waypoint is not counted as stalled against its mission goal.

### 9.2 Grounded command → ROS2 fan-out

| M3 grounded field | ROS2 `CoordinationCommand` field | rule |
|---|---|---|
| `command_id` | `command_id` | shared across all fan-out messages |
| `actions[i].robot_id` | `robot_id` | one message per action |
| `actions[i].action` | `action` | verbatim |
| `actions[i].parameters` | `parameters_json` | `json.dumps(parameters, sort_keys=True)` |
| `expected_resolution_time_sec` | `timeout_sec` | fallback to `config.command_timeout_sec` if 0/absent |
| `fallback` | — | retained in `CommandRecord`, not sent this milestone |

---

## 10. Non-Functional Requirements
- NFR5.1 The subscription/spin path must never block on M2/M3; all reasoning runs on
  a background executor (FR5.3.3).
- NFR5.2 Single in-flight reasoning cycle: at most one pipeline future active at a
  time; new events while busy are ignored (not queued) this milestone.
- NFR5.3 Pure-logic modules import no `rclpy` and are fully unit-testable on macOS.
- NFR5.4 Every dispatched command and every analysis cycle is traceable by
  `request_id`/`command_id` in structured logs (C2).
- NFR5.5 No secrets, base64 images, or full provider payloads in logs.

## 11. Error Handling & Edge Cases
- E1 **Malformed `SceneState` JSON** → log + skip frame; do not advance timers or
  crash the node.
- E2 **Dropped/late frame** → hold detector state (FR5.1.4); never read as recovery.
- E3 **M2 `decision=None` / `congestion_detected=false`** → no dispatch, cooldown,
  back to MONITORING (FR5.2.5).
- E4 **M3 grounding failure / schema-invalid command** → caught in adapter,
  `failure_reason` set, cooldown, back to MONITORING. No partial dispatch.
- E5 **M4 reports FAILED/TIMED_OUT** → mark record, start cooldown; M5 re-triggers
  only after cooldown if the jam persists. Layer 1 keeps recovering.
- E6 **Command timeout (no status)** → tracker marks `TIMED_OUT`, cooldown applied.
- E7 **Robot referenced in a grounded action but absent from current scene** →
  dispatch is still sent (M4 filters by robot id); logged as a warning.
- E8 **Invalid config at startup** → raise and fail fast (FR5.6.4).
- E9 **Trigger before any annotated frame arrives** → suppress the analysis cycle
  and log; do not invoke M2 without an image (the `ReasonerRequest` contract
  requires `image_path`).
- E10 **Frame/scene stamp skew beyond `frame_scene_max_skew_sec`** → treat as E9:
  suppress the trigger and log both stamps. A stale buffered frame (e.g., the
  annotated stream died while scene-state kept flowing) would have the VLM reason
  over an image that does not show the jam. This matches the M2 spec's edge-case
  table: stamp matching/rejection is M5's responsibility; M2 only checks existence.

## 12. Dependencies
- Runtime: `pydantic` v2, `rclpy` (node only), `reasoning.vlm`, `reasoning.rag`
  (in-process), `opencv-contrib-python` (PNG encode + RGB→BGR + optional downscale,
  FR5.3.6), stdlib `json`/`concurrent.futures`/`threading`.
- ROS2 package deps in `package.xml`: `rclpy`, `std_msgs`, `sensor_msgs` (annotated
  frame), `cv_bridge` (Image → ndarray), `swarm_interfaces`. **No dependency on `swarm_perception`** — M5 parses
  the SceneState JSON into its own `SceneSnapshot` projection (§4).
- **M3 (RAG) is a prerequisite for live operation** but not for building/testing M5:
  the `ReasoningPipeline` Protocol allows a mock until M3 lands.
- No new external dependencies introduced.

## 13. Testing & Validation

### Unit tests (`tests/unit/`, offline, no ROS2)
- `test_m5_congestion_detector.py` — progress-based stall, threshold timing, STALE
  exclusion, dropped-frame hold, multi-robot events, no-goal robots ignored.
- `test_m5_state_machine.py` — every transition in §8, cooldown/active-command
  gating, single in-flight enforcement, no-frame/stale-frame suppression (E9/E10),
  failure-counter increment/reset (FR5.2.7).
- `test_m5_command_lifecycle.py` — PENDING→ACTIVE→terminal, timeout detection,
  resolution → cooldown; `CooldownTracker` start/expiry, cooldown without a
  command record (pipeline-failure path).
- `test_m5_task_registry.py` — initial load with goals, assignment, override
  set/clear and effective-goal revert, deterministic JSON.
- `test_m5_reasoning_pipeline.py` — `InProcessPipeline` with mocked M2/M3:
  ok / no-congestion / vlm-failure / grounding-failure outcomes; fan-out mapping
  (§9.2); frame dump writes BGR-converted PNG at the expected path, optional
  downscale preserves aspect, cleanup honors `keep_debug_frames`.

### Node integration tests (`tests/integration/`, marked `ros2`)
- Scene-state → trigger → mocked pipeline → command publication on
  `/coordination/commands`.
- Status feedback updates lifecycle; timeout tick marks `TIMED_OUT`.
- Registry published on `/coordination/tasks` at startup and on change.

All external systems (M2 backend, M3 store, ROS2 runtime) are mocked in unit tests;
integration tests are marked so they are not confused with fast unit tests.

---

## 14. Open Questions / Future Work
- Spatial clustering for jam confirmation (FR5.1.6).
- Auto-execution of grounded `fallback` and a safe-stop escalation path after
  repeated failures for the same jam — implementable as a threshold check over the
  per-robot consecutive-failure counters (FR5.2.7).
- Queuing/coalescing concurrent congestion events instead of single in-flight.
- **Scenario task sequences** (deliberately deferred): scenarios may define
  per-robot task *sequences*; M5 would advance a robot to its next scenario-defined
  task on completion (registry bookkeeping, not mission planning — needed for
  throughput metrics). This milestone supports a single base assignment per robot.

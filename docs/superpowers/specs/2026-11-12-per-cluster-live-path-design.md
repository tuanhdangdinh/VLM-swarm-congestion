# Per-Cluster Choice: Live Execution Path (Design Note)

**Prepared:** 2026-11-12

**Revision history:**

- Initial draft: live behaviour read from code, four options compared, recommendation (one call, per-group grounding, joint gate, serialize on conflict) with a staged rollout, measurement plan and owner rulings.
- Rev 2 (2026-11-12): Stage 0 status recorded in Scope and Status (landed on `feat/v4-per-cluster-parity`); no other text changed.

---

## Scope and Status

- **What this is.** A design note for running the v4 "per-cluster choice"
  lever (`grounding_first_per_cluster`) in the live loop. It is not an
  implementation plan and changes no code.
- **Exploratory v4 only.** Everything here is default-off. It must not change
  pinned prereg-v3 behaviour or configs (A32: rag e18c723c, s1b_dynamic
  535f5281, s1b_dynamic_shield ee5fe68f, s1b_dynamic_shield_escort 40968886,
  install `safety.yaml` 59839662), and nothing it produces pools with A32-A36.
- **Code base read.** Branch `feat/v4-per-cluster` at 76c6401. File:line
  references are to that tree. Statements marked *inferred* were not
  verified in code or by a run.
- **Stage 0 status (2026-11-12): landed** on `feat/v4-per-cluster-parity`
  (d568726, 17105d0, e1676d4, ce72984; not pushed). The exit criterion holds:
  `candidates` v2 md5 a84e4444 and per-cluster md5 f333fb8e reproduce, the
  144 bench tests pass, and the full unit suite's failing-id set is unchanged
  (57 ids, flag-off goldens among the passing tests). The shared code is in
  `reasoning/rag/{cluster_options,joint_check,grounding_provenance}.py` and
  `reasoning/vlm/{executable_options,per_cluster_choice}.py`. The ask/re-ask
  runner stays in the bench, and probing is passed in as a
  `ground(decision)` callable. Evidence and deviations:
  `docs/implementation_notes.md`, 2026-11-12 Stage 0 entry. Stages 1-2 are
  not started.

---

## 1. Problem and Evidence

The v2 grounding-first prompt asks for one option per scene. On the 137
recorded positives, the models covered 6-9 of the 61 two-cluster items, and
1-2 of the 44 whose clusters fall in different observed groups
(`docs/reports/2026-10-24-v4-gf-cluster-candidates.md`, Rev 2).

Asking for one choice per observed group fixes that offline
(`docs/reports/2026-11-12-v4-per-cluster-choice.md`, Rev 3):

| 137 recorded positives | ER-2 v2 to per-cluster | Sonnet 5.5 v2 to per-cluster |
|---|---|---|
| cluster coverage | 0.496 to 0.832 | 0.620 to 0.934 |
| split two-cluster items (of 44) | 2 to 33 | 2 to 38 |
| mean per-cluster recall | 0.50 to 0.75 | 0.62 to 0.82 |

The limits matter as much as the gain:

- **Text only.** Every replay sent a neutral grey image.
- **One run per configuration.** No same-prompt repeat of R7 exists.
- **Tuned on the same items.** The grouping rules were chosen on the same 187
  items they are scored on.
- **The gain belongs to the format.** Within a slot, the models match the
  generator's default-ordered first option and do not beat it (slot F1 0.79
  and 0.85, against 0.827 for the first option). The oracle's slot F1 is
  0.886.
- **Involvement F1 is not an outcome.** It counts which robots are named, not
  whether the conflict clears.
- **Joint safety is unknown.** The joint check is partial: it covers exact
  clashes plus a timing-free straight-line heuristic.

The report's "Joint Feasibility and Single Dispatch" section concluded that
live M5 handles one command per decision. Section 2 sharpens that conclusion.

---

## 2. Current Live Behaviour

### One Cycle, One Decision, One Command

- **One event per scene.** `CongestionDetector.update` returns a single
  `CongestionEvent` whose `involved_robots` is every stalled robot in the
  scene (`congestion_detector.py:118-131`). Two clusters produce one event.
- **One analysis in flight.** Only `MONITORING` starts a cycle
  (`state_machine.py:99-100`). The node holds one `_future` and one set of
  `_pending_*` fields (`orchestrator_node.py:1170-1196`), harvested in
  `_on_timer` (`orchestrator_node.py:1050-1059`).
- **The decision names one strategy.** `CongestionDecision` carries one
  `strategy`, one `involved_robots` list and one `yield_robot`
  (`reasoning/vlm/models.py:429-458`). The answer is parsed only as that
  model (`reasoner.py:497`).
- **One grounded command per outcome.** `InProcessPipeline._run_from_result`
  grounds one command (`reasoning_pipeline.py:1604-1618`).
  `PipelineOutcome.grounded_command` is a single dict
  (`swarm_orchestrator/models.py:848`).
- **One dispatch per outcome.** `on_outcome` returns one `DISPATCH`
  (`state_machine.py:123-134`). `_dispatch` registers one `CommandRecord`
  and publishes one `command_id`, fanned out per robot
  (`orchestrator_node.py:1478-1517`, `reasoning_pipeline.py:829-846`).

### Concurrency the Gates Already Allow (Sharpens the Report)

The report read "single dispatch" as a limit of the dispatch machinery. The
gates do not impose it: by the code, several commands on disjoint robot sets
can be live at once. This has not been observed in a run; no local log was
available to check it.

- **The state machine returns to MONITORING at dispatch time, not at
  resolution** (`state_machine.py:131-133`).
- **The busy gate is a per-robot intersection test** against the union of
  all unresolved commands (`state_machine.py:103-105`;
  `orchestrator_node.py:2517-2522`). An event disjoint from every busy robot
  starts a new analysis while earlier commands are still executing.
- **The tracker holds many records.** `CommandTracker` keeps one record per
  `command_id` (`command_lifecycle.py:67-75`), and `_resolve_command` acts on
  one `command_id` at a time (`orchestrator_node.py:1933-1990`).
- **M4 keeps a per-robot slot.** The command bus tracks the in-flight command
  per robot. It busy-rejects (`FAILED`, "robot busy") only a command for a
  robot that is already held by a different command
  (`command_bus_node.py:118-138`).

What then happens to group B depends on one fact that is *inferred, not
verified*: whether A's commanded robots stay in the detector's stalled set
while A's command runs.

- **Why they probably stay.** A's robots keep their own goal, because the
  override goal is the effective goal (`orchestrator_node.py:1572`, `1582`;
  `task_registry.py:140-147`). Progress is still measured against that goal
  (`congestion_detector.py:103-109`), and nothing in the node resets the
  detector at dispatch (its only calls are `orchestrator_node.py:406-407`,
  `750`). A yielder backing away therefore does not improve.
- **Why this is not settled.** The solo-follower fold (`state_machine.py:34-50`,
  `106-107`) was built for events that name only a robot outside the busy
  set, so commanded robots were expected to drop out in some scenes. It was
  never exercised live (0 `trigger folded` in the 2026-09-29 T2b smoke entry
  of `docs/implementation_notes.md`).

The two branches lead to different answers:

- **Branch 1 (A's robots stay stalled; the likelier reading).**
  Serialization comes from three places other than the dispatch gates:
  1. The next event names A's robots and B's together, and the busy gate
     suppresses it.
  2. `_resolve_command` starts a cooldown on A's robots
     (`orchestrator_node.py:1985`; `cooldown_sec: 15.0` in
     `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml:25`). Events
     naming them stay suppressed until it expires.
  3. The next analysis is scene-wide again. B's earlier choice is discarded
     and B is decided afresh, with one strategy for the whole scene.
- **Branch 2 (A's robots drop out).** Once B's robots cross the stall
  threshold, an event naming only B starts its own analysis, and its command
  runs concurrently with A's today. The prompt is still scene-wide
  (`orchestrator_node.py:1149-1164`), so B is not guaranteed a decision about
  B. Under this branch the lever's timing value is smaller: it saves one
  analysis cycle and the stall wait, not A's whole command.

The fold absorbs only a single stalled robot outside a busy set of two or
more, so it does not cover a second group of two or more. The stage-1 shadow
logs (Section 5) settle the branch at no extra cost: they record, for each
multi-group scene, whether a group-B-only event ever starts an analysis.

### Plan Channel and junction_clear

- **The plan is scene-wide but tracking-only.** With `plan_channel_enabled`
  (default false, `swarm_orchestrator/models.py:466`; false in
  `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml:329`; on in the
  item overlays),
  `verify_and_repair_plan` runs and `PlanTracker.accept_plan` tracks the
  result (`reasoning_pipeline.py:1632-1784`). Only the decision's grounded
  command is dispatched.
- **A two-yield plan is rejected (verified).** `_is_consistent` requires
  exactly one `yield` leg for strategy `yield` (`command_grounder.py:3460-3461`).
  A plan that fails it falls back to `m3_default`, with rejection stage
  `inconsistent` (`command_grounder.py:4968-4979`). The report listed this as
  inferred.
- **The tracker has one active plan.** `accept_plan` either holds the active
  plan or supersedes it (`plan_tracker.py:273-325`). A second group's
  decision, completed scene-wide with `continue` legs, differs from A's
  remaining legs, so it is not a hold (`plan_tracker.py:160-216`). It takes a
  new `plan_id` and supersedes A's plan.
- **Supersession is recorded, not executed.** `cancel_order` is computed
  (`plan_tracker.py:219-231`) and copied into the artifact
  (`reasoning_pipeline.py:1776-1780`). A search of `ros2_ws/src` and
  `reasoning` found no code that acts on it.
- **A cross-group exemption exists today (verified in code).** A plan-tagged
  `reverse` leg gets `plan_continue_partners`: the plan's `continue` robots
  that are also in the triggering event (`orchestrator_node.py:1648-1665`).
  M4 then exempts the reversing robot against them (`safety.py:206-211`,
  `235-240`). The trigger set is the whole scene-wide event and the plan is
  scene-wide, so on a two-cluster scene with the plan channel on, a reverse
  in cluster A is already exempt against cluster B's `continue` robots. Any
  per-group path must not inherit this, and it may deserve its own look
  outside v4.
- **`junction_clear` precomputes its phases.** It is the only path that
  dispatches several commands from one decision. Its queue never re-grounds:
  every phase is built once from the decision's snapshot
  (`junction_phase_queue.py:8-14`). Later phases are dispatched without an
  attempt record (`orchestrator_node.py:1723-1729`). While any queue is live,
  the contradiction trigger is suppressed (`orchestrator_node.py:2067-2068`).

### Where the Response Schema Is Fixed

| Layer | Today | Per-item keys possible without a live change |
|---|---|---|
| `VLMBackend.analyze(payload, config)` | `PromptPayload` has no schema field (`reasoning/vlm/models.py:288-298`) | no |
| Gemini | `force_schema` loads the static `vlm_decision` schema once, at construction (`gemini_backend.py:87-101`), and sends it as `response_format` (`gemini_backend.py:219-223`); `force_schema: false` (`config/models.yaml:66`, `189`) | no |
| Anthropic | no schema or structured-output field is sent (a search of `anthropic_backend.py` finds none) | no |
| Parser | `Reasoner.run` parses `CongestionDecision` only (`reasoner.py:497`) | no |

There is a precedent for a second contract: stage 2 has its own model and its
own schema file (`RetreatChoiceDecision`, `reasoning/vlm/models.py:557`;
`reasoning/schemas/retreat_choice.schema.json`; `reasoning/vlm/retreat_chooser.py`).

### Bench and Live Differ on Stage 2

- **Bench:** option probes ground with stage 2 not run
  (`grounder_offline.py:100-147`, docstring at 108). The retreat therefore
  comes from M3's own ranking.
- **Live:** a derived-mode yield runs the stage-2 retreat chooser, a second
  VLM call (`reasoning_pipeline.py:1568-1588`).
- **Consequence:** the park an option names offline need not be the park live
  dispatch executes.

---

## 3. Requirements and Non-Goals

**Requirements**

- **R1. One decision per group.** Every observed group gets an explicit
  decision, either an option or `none_feasible`, from one M2 answer. The
  artifact records each one.
- **R2. Safety unchanged.** The following stay as they are:
  - M4 `min_distance_m` and its latch;
  - the 0.20 m floor swap with its pre-arm and post-arm gates (A28(i));
  - A27 shield de-exemption;
  - the escort/park filter where it is registered (A29, A32 R1).

  No exemption may span two groups. This includes the plan-continue
  exemption that already does so today (Section 2): a per-group path must
  not inherit it.
- **R3. Pinned v3 behaviour unchanged.** All new behaviour sits behind new
  flags, default off. With the flags off, artifacts are byte-identical (the
  `_omit_unset` pattern used throughout `models.py`). No pinned config file is
  edited; pilots use new overlay files.
- **R4. M4 untouched.** The design must not need wire or `swarm_execution`
  changes. Section 2 shows that disjoint concurrent commands already work
  there.
- **R5. Bench/live parity (shared-function principle, A13(iii)).** The
  following run as the same code offline and live:
  - grouping;
  - option enumeration and probing;
  - slot construction;
  - the answer contract;
  - the joint check.
- **R6. Observability.** Each artifact records, per group:
  - the label, the robots and the option ids shown;
  - the choice and the grounded command id;
  - the joint-check verdict and the dispatch disposition (dispatched,
    serialized, dropped, or `none_feasible`).

  Each command carries its group label, so scorers can attribute outcomes to
  a group without re-deriving the groups.

**Non-goals**

- Changing M2 or M3 behaviour for single-group scenes.
- Per-item response schemas (that would mean a `PromptPayload` change).
- Improving within-slot choice quality.
- Three or more groups. No recorded positive has more than two slots; the
  design should not fail on three, but it is not tuned for them.

---

## 4. Design Options

### (A) One Call, Sequential Sub-Decisions

**How it works.** One M2 call returns the per-group map. M5 expands it into
an ordered queue of ordinary single-command decisions and dispatches them one
at a time, each after the previous one resolves.

**What breaks or must be added.**

- **A sibling queue, not `JunctionPhaseQueue`.** The junction queue
  precomputes commands and never re-grounds (`junction_phase_queue.py:8-14`).
  It also skips attempt records and silences the contradiction trigger.
  Re-validating each step on the fresh scene therefore needs a new queue.
  That queue re-grounds when its turn comes, either on the spin thread or via
  a second executor slot.
- **No gain in timing.** Group B still waits for A's whole command. The only
  gain over today is that B's choice survives instead of being re-asked.
- **Repeats E3's pattern.** It serializes interventions across clusters,
  which is the pattern A21 classified as E3's coordination livelock: "serial
  pairwise intervention on a multi-conflict scene can oscillate
  indefinitely".

### (B) One Call, Concurrent Dispatch for Disjoint Groups

**How it works.** One M2 call returns the per-group map. Each group decision
is grounded alone through the existing M3 path. A joint gate runs on the
grounded commands. If it passes, the commands dispatch at once, each under
its own `command_id` and `CommandRecord`.

**What it uses and what breaks.**

- **Existing machinery:** the busy union, per-command resolution and M4's
  per-robot slots (Section 2).
- **Exact conflicts cannot run.** A shared robot would be busy-rejected by M4
  (`command_bus_node.py:118-138`). Such cases need serialization or a drop,
  which brings in A's queue for those cases.
- **Plan channel.** The single-active-plan tracker would make the group
  commands supersede each other. Plan-tagged group commands would also leak
  `plan_continue_partners` across groups.
- **Group commands must therefore be plan-less.** With no `plan_id`, the
  partner list is skipped (`orchestrator_node.py:1648-1649`) and M4 keeps
  every cross-group pair under the latch (`safety.py:206-211`). That is the
  safe default.

### (C) Per-Group Reasoning Cycles

**How it works.** The detector, or a splitter after it, emits one event per
observed group. The existing single-command pipeline runs once per group, so
a two-group scene costs N VLM calls. Suppression is scoped to the group.

**What breaks or must be added.**

- **Smallest change to M5.** The busy gate is already per robot.
- **The prompt still changes.** The prompt is built from the whole snapshot
  (`orchestrator_node.py:1149-1164`), so the model must be told which group
  it is deciding for. That is a new prompt, not the one R7 measured.
- **Slower, and more cycles.** Calls are serial (single in-flight), so group
  B's decision starts only after A's call returns. Analyses per episode
  double on multi-group scenes, which consumes the run's analysis budget
  (`MAX_ANALYSES`, cited at `orchestrator_node.py:859-860`) and the cost cap
  (A32 R2).
- **E3 exposure.** Cycles alternate between clusters, which is the A21 E3
  pattern.
- **Weak bench parity.** R7 measured one call over all groups; C asks about
  one group at a time.

### (D) Composite Plan Through the Plan Channel

**How it works.** One decision carries a scene-wide `proposed_plan` with one
yield per group, and M5 dispatches its legs.

**Not viable as is (verified).**

- **The verifier rejects it.** It refuses a `yield` plan with two yield legs
  (`command_grounder.py:3460-3461`, `4968-4979`).
- **Nothing dispatches legs.** Only the grounded command is dispatched.
- **Two contract changes would be needed:** a new strategy, or a new
  consistency rule, in M3; and a leg dispatcher in M5. Both would touch the
  v3 plan-stability measurement.
- **Recorded for completeness only.**

### Comparison

| | (A) one call, serial | (B) one call, concurrent if disjoint | (C) per-group cycles | (D) composite plan |
|---|---|---|---|---|
| M2 | new per-group contract and runner (stage-2 precedent) | same as A | new "decide for group X" prompt; decision model unchanged | `proposed_plan` with several yields |
| M3 | shared option enumeration (stage 0) | same as A, plus joint gate | shared grouping only | consistency rule and leg grounding |
| M5 | sibling queue with re-grounding at dispatch | per-group fan-out; A's queue for conflicts | event splitter; group-scoped suppression | leg dispatcher; tracker semantics |
| M4 | none | none | none | none if legs map to existing actions (*inferred*) |
| Schema and consumers | new artifact block; `vlm_decision` untouched | same as A | `CongestionEvent` scope changes; scorers that assume one event per scene (*not checked*) | `vlm_decision` plus plan scorers |
| Joint feasibility | sequential, so only a re-ground on the fresh scene | joint gate before dispatch; serialize on conflict | none; each cycle sees the other's command only as scene state | verifier would have to model it |
| Failure and timeout | a failed step drops the rest of the queue (proposal) | per command, as today; serialized remainder as in A | as today, per group | one plan, all-or-nothing (*inferred*) |
| Churn, livelock, suppression | E3-like serial pattern; per-cluster churn bound applies | fewest alternation opportunities; churn bound per latch cluster (`churn.py:19-23`) | most E3 exposure; doubles analyses | single plan has nothing to alternate (A21) |
| Bench parity | high (same call) | high (same call, same joint check) | low (different prompt) | none |
| Test surface | contract, queue, re-ground | contract, gate, fan-out, plan-less tagging | splitter, prompt, suppression | verifier, tracker, dispatcher |
| Effort | medium | medium-high | low-medium | high |
| Risk | low safety risk, little timing gain | joint-safety unknowns (Section 6) | livelock, cost, parity | v3 measurement contamination |

---

## 5. Recommendation and Staged Rollout

**Recommendation.** Use a single M2 call returning the per-group map (the R7
contract), ground each group alone, and run a joint gate:

- **Pass:** dispatch concurrently as plan-less group commands (B).
- **Exact conflict:** serialize the later group behind the first, re-grounded
  on the fresh scene at its turn (A's queue).

Whether concurrency is enabled at all is an owner ruling (Section 8, ruling
2), decided on stage-1 joint-flag rates. Serialize-only (pure A) is the
fallback setting of the same build.

Reasons, strongest first:

1. **Concurrency is where the lever's timing value lies, and it is cheap
   live.** Section 2 shows that the state machine, tracker and M4 gates
   already admit disjoint commands together. Under the likelier branch, the
   serialization comes from the scene-wide event and the cooldown, and this
   design bypasses both by dispatching every group from one outcome. Under
   the other branch the gain is smaller but not zero (Section 2).
2. **It matches what was measured.** One call over all groups is the R7
   prompt and contract, so the shared-function parity can be exact. C would
   measure a different prompt.
3. **It does not repeat A21's livelock pattern.** One scene-level answer
   decides both groups at once. A and C alternate interventions between
   clusters, as in E3.

### Stage 0: Parity Refactor (No VM Time)

- **Move the shared code.** Move `observed_groups`, the option enumeration
  and probing, slot construction, `choices_model` and the parser, and
  `joint_check` into `reasoning/`:
  - grouping, enumeration and joint check under `reasoning/rag`, beside
    `derive_candidate_options` (`command_grounder.py:5319`), the existing
    default-off precedent for M3-derived options in a prompt
    (`orchestrator_node.py:2624-2632`);
  - the contract and the runner under `reasoning/vlm`, alongside
    `retreat_chooser`.
- **Dependency direction.** The "executes as asked" rule (`executed_key`,
  `grounding_first.py:169-205`) calls `outcome_of`, which uses
  `summarize_yield_grounding` and `empty_reroute_fallback` from
  `swarm_orchestrator.reasoning_pipeline` (`grounder_offline.py:17-18`,
  `160-161`). Code moved under `reasoning/` must not import
  `swarm_orchestrator`, so those two pure helpers move down into
  `reasoning/rag` too, and `swarm_orchestrator` re-exports them.
- **Inputs must change.** Today the inputs are a `BenchItem` and
  `benchmarks.*` imports (`gf_cluster.py:62-63`, `per_cluster.py:51-53`).
  They must become a `SnapshotFrame`, `GroundingParams`, geometry, obstacles,
  yield mode, priorities, goal references, task intents and the classical
  `r_conflict_m`. The bench then wraps the shared code.
- **Exit criterion:**
  - `candidates` v2 md5 a84e4444 and per-cluster md5 f333fb8e reproduce;
  - the 144 bench tests pass;
  - flag-off orchestrator goldens are unchanged.
- **Cost:** zero GPU.

### Stage 1: Live Shadow (Compute and Log, Dispatch Nothing New)

- **What it does.** On each triggered analysis in an exploratory cell, the
  worker also builds the slots, makes the per-group call and grounds each
  choice. It runs the joint gate and writes a `per_cluster_shadow` artifact
  block, the R6 fields. The ordinary decision dispatches as today.
- **Billing.** It is a second billed M2 call, so it cannot run in pinned v3
  cells.
- **Frames.** Set `keep_debug_frames: true` so frames persist (see Section 7).
- **Exit criterion:**
  - per-group parse validity of at least 95% after re-ask;
  - artifact completeness 100%;
  - added worker latency measured;
  - joint-gate flag rates on live multi-group scenes reported;
  - the Section 2 branch settled (does a group-B-only event ever start an
    analysis while A's command runs);
  - at least about 10 multi-group analyses observed.

  The thresholds are proposals for the owner to set.
- **Cost (*estimate*):** 4-6 S1b episodes at about 55 GPU-min each, so about
  4-6 GPU-h. M2 spend is roughly doubled per analysis.

### Stage 2: Gated Live Dispatch Pilot

- **What it does.** Dispatch per Section 6, in new exploratory overlays only.
  The floor swap and pre/post arm gates are mandatory (A28(i)).
- **Design.** Seeds are paired against the same cell with the lever off.
- **Exit and kill criteria:** Section 7.
- **Cost (*estimate*):** 6 paired seeds, so 12 episodes, about 11 GPU-h. More
  if stage 1 shows that multi-group scenes are rare per episode.

---

## 6. Joint Feasibility and Timing Live

**What the offline `joint_check` covers** (`per_cluster.py:537-581`):

- **Exact:**
  - one robot addressed by two commands, a hold in one and a move in the
    other included;
  - two retreat points closer than 0.45 m.
- **Heuristic:** straight-line motion segments within 0.45 m of the other
  command's segments or robots (`per_cluster.py:491-534`).

**What it does not cover:**

- timing and order;
- Nav2 paths after the escort;
- swept footprints;
- M4 latch interaction.

On R7 it fired an exact conflict on 2 of 39 (ER-2) and 2 of 44 (Sonnet)
multi-command answers, and any flag on 5 and 7.

**Proposed live gate**, the same function as the bench (stage 0):

1. **Exact tier:**
   - shared robot;
   - retreat points closer than 0.45 m;
   - new: one group's escort leg passing within 0.45 m of the other group's
     park point, reusing `escort_park_violations`
     (`reasoning/rag/escort_clearance.py:215`). The A29 filter checks this
     only within one command.

   Any exact hit means no concurrency.
2. **Heuristic tier.** A path-proximity flag means serialize, not reject.
   *Inferred* to be conservative, because M4 still latches cross-group pairs
   at `min_distance_m`. The cost is that a wrong flag only delays the second
   group.
3. **Ordering rule when two groups interact.** The group whose command has
   the shorter `expected_resolution_time_sec` goes first. Ties go to slot
   order (size, then closest pair, `gf_cluster.py:241-247`). The point is to
   free the shared space soonest. This is a proposal.
4. **On an exact conflict, serialize**: the second group waits for the first
   command's resolution, then is re-grounded on the latest snapshot and
   re-gated. It is dropped (logged, no dispatch) when its group no longer
   exists in the observed grouping of that snapshot.
   - Re-ask is rejected: it adds an M2 round trip and the contract then
     depends on other slots (report, Owner Rulings).
   - Dropping the lower-priority group outright discards a valid choice that
     serialization can still use.
5. **Timing.**
   - Concurrent group commands start within one dispatch call.
   - A serialized group bypasses the event path (its robots would be
     suppressed by the busy gate). M5 dispatches it from `_resolve_command`,
     as `_advance_junction_phase` does, with its own attempt record and an
     age limit. The proposed age limit is `command_timeout_sec` (20 s,
     `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml:26`); past it,
     the group is dropped.

---

## 7. Measurement Plan

**Pilot metrics** (lever on against off, paired seeds):

- **Mechanism:**
  - second-group wait: sim-seconds from the second cluster's onset to its
    first dispatched command;
  - the share of multi-group analyses that dispatched both groups,
    serialized, or dropped one.
- **Outcome:**
  - tasks completed per episode;
  - per-cluster latch-break time;
  - A33 productive events, with admitted kept distinct from productive
    (A28(iii)).
- **Churn (A21):**
  - dispatches per latch-break;
  - alternation count;
  - churn-bound would-withhold counts at 3/130/0.
- **Safety:**
  - contacts (GT distance below 0.18 m);
  - floor and B3 firings;
  - minimum cross-group separation.
- **Health:**
  - per-group parse validity;
  - `none_feasible` rate;
  - M2 spend per episode;
  - added latency.

**Involvement F1 is secondary.** It is reported for comparability only and is
not an outcome.

**Persist frames.**

- **Why frames are missing.** `keep_debug_frames` is false by default
  (`ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml:63`), and
  `_cleanup_frame` deletes the dumped frame after each outcome
  (`orchestrator_node.py:2565-2571`). This is consistent with `frames/`
  being empty in every bundle. *Not verified:* `scripts/vm/v2_overlay.py`
  sets it true for some cells, and why those bundles were still empty is
  unknown.
- **What to change.** Future v4 runs should set `keep_debug_frames: true` and
  check that the bundle collector copies the frames. Without frames, the
  text-only limit of R1-R7 cannot be lifted offline.

**What counts as the lever failing:**

- second-group wait does not fall;
- tasks per episode do not rise beyond seed-to-seed variation;
- any added contact or floor firing;
- alternation or churn rises.

Any one of these counts. A safety signal stops the pilot at once.

---

## 8. Open Owner Rulings

1. **Take the lever live at all?**
   - *Recommended:* approve stages 0-1 now; decide stage 2 on the stage-1
     exit.
   - *Consequence:* "no" keeps it a bench diagnostic of under-selection, at
     zero VM cost.
2. **Dispatch mode in the pilot.**
   - *Recommended:* concurrent when the gate passes, serialize on any flag,
     decided after stage-1 flag rates.
   - *Consequences:* serialize-only (A) is safer but tests little beyond
     today's timing. Concurrent tests the lever's actual value, with the
     residual joint risk in Section 9.
3. **Stage 2 retreat for group yields.**
   - *Recommended:* pin the option's probed park (pass its retreat label)
     and skip stage 2, so the park the model was shown is the park executed.
   - *Consequence:* keeping stage 2 adds a VLM call per yield, and the
     dispatched park can differ from the option text.
4. **Plan channel on multi-group cycles.**
   - *Recommended:* group commands are plan-less. Multi-group cycles do not
     enter `PlanTracker`, and plan-stability metrics are reported as
     undefined on them.
   - *Consequence:* the alternative (per-group plan slots) changes v3 tracker
     semantics. Plan-tagging under today's tracker supersedes plans and
     carries the cross-group exemption (Section 2).
   - *Side effect:* the next analysis's plan-state block will show the last
     accepted plan, which is stale once plan-less group commands have run.
     It should be suppressed, or marked stale, on episodes where a
     multi-group cycle ran.
5. **Partial-pair options and the `outside` fallback slot.**
   - *Recommended:* keep both, serializing when a no-group robot is shared.
   - *Consequence:* removing partial pairs loses the 6 one-slot split items
     they reach.
6. **Cells and configs.**
   - *Recommended:* new exploratory S1b overlays copied from the registered
     shield-escort config, never editing pinned files.
   - *Consequence:* pilot results are not comparable with A36 tranche 1
     beyond description.
7. **Option ids.**
   - *Recommended:* numbered, matching R7.
   - *Consequence:* opaque ids would be a second change against the measured
     prompt.

---

## 9. Risks and Unknowns

- **Joint safety beyond the gate is unknown.** Timing, Nav2 replanning after
  an escort and swept footprints are unchecked. M4's per-pair latch is the
  backstop (`safety.py:206-211`: no cross-command partners). *Inferred:* two
  concurrent groups can latch each other at 0.45 m and stall, which would
  show up as churn, not contact.
- **Not verified in code:**
  - whether commanded robots leave the stalled set while their command runs
    (Section 2, the two branches); this sets today's baseline for group B;
  - the latency of synchronous option probing (dozens of
    `ground_reasoner_result` calls per analysis);
  - how `benchmarks/s1_scoring` joins artifacts to commands, so whether it
    attributes two commands from one request;
  - whether every downstream scorer tolerates two `command_id`s per
    `request_id`.
- **Offline evidence limits** (Section 1): text-only, one run per
  configuration, tuned on the same items, slot choice at the default
  ordering's level. A live gain could come from the default ordering alone,
  not from the model. A pilot arm with the first option in every group
  (zero M2 for the choice) would separate the two. It is listed as an
  optional ruling, not part of the recommendation.
- **Grouping drift.** Observed groups are recomputed per snapshot. A
  serialized group may dissolve or merge before its turn (handled by drop),
  and group labels are not stable across snapshots.
- **Cost.** Stage 1 doubles M2 calls per analysis. Under the $0.10 episode
  cap (A32 R2), episodes may be cut earlier.
- **Thread model.** Grounding several decisions and re-grounding a
  serialized one must not block the rclpy spin thread. Whether the single
  executor slot (`orchestrator_node.py:1196`) needs widening is open.

---

## References

- Offline result: `docs/reports/2026-11-12-v4-per-cluster-choice.md` (Rev 3);
  `docs/reports/2026-10-24-v4-gf-cluster-candidates.md` (Rev 2);
  `docs/specs/v4_vlm_bench.md`.
- Bench code: `benchmarks/vlm_bench/variants/{gf_cluster,per_cluster}.py`,
  `benchmarks/vlm_bench/grounder_offline.py`.
- prereg-v3 design (on `feat/v3-design`):
  `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`, addenda A13(iii),
  A21, A28, A29, A32.
- Specs: `docs/specs/module2_vlm_reasoning.md`,
  `docs/specs/module3_rag_grounding.md`, `docs/specs/module5_orchestrator.md`,
  `docs/specs/module4/safety-monitor.md`.

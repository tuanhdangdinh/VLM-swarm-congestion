# Convoy and S6 Live Experiments: Feasibility and Scope

**Prepared:** 2026-11-13

**Revision history:**

- Initial draft: read-only feasibility study and scope for matched VLM-on / VLM-off live experiments on `convoy_counterflow` (`_slip`) and `s6_dual_conflict`. Nothing was run on a VM and no paid API was called. Every threshold, n and cap in this document is a proposal for the owner.

---

## 1. Verdict

| Scene | Verdict | One-line reason |
|---|---|---|
| `convoy_counterflow_slip` | **GO, conditional** | M3 at 68e67b5 grounds the designed oracle command exactly. Run it only after the safety fix is tested, and start with a scripted oracle-order episode on the fixed runtime. |
| `convoy_counterflow` (v1 name) | **Fold into `_slip`** | It is the same physical scene (geometry pinned byte-identical). Run one scene and score both questions. |
| `s6_dual_conflict` | **NO-GO as a resolution experiment** | Under the recorded S6 overlay, M3 at 68e67b5 refuses every pair-B command (verified). The only config that grounds pair B (dynamic arms) sends it into racks or onto a likely latch, as far as checked. A matched outcome contrast would measure the scene, not the model. |

Status of the evidence:

- **Verified** means read from code at 68e67b5, from recorded bundles, or from offline runs of the 68e67b5 code on recorded inputs. Those runs used an exported copy in the scratchpad; no worktree was touched.
- **Inference** means reasoned from that evidence but not observed.

Both labels are used throughout.

---

## 2. Sources Checked

| Source | Used for |
|---|---|
| `isaac/config/scenarios/{convoy_counterflow,convoy_counterflow_slip,s6_dual_conflict}.yaml` at `68e67b5` | Geometry, timing, M5 settings, oracles. Blob hashes are identical on every branch, including `feat/v4-vlm-bench`. Only `feat/v3-s6-map` (`a295923`) holds an older S6 version (pre-pose-ruling spawns). |
| `docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` and the IB10 kit (v7a, read only) | Model for the design, caps and kit. Also the RTF and slot timing of the smoke. |
| `docs/reports/2026-10-08-s6-first-light.md` and its bundles in `data/logs/vm_runs/s6_first_light/` | S6 history, the overlay `s6_orchestrator.yaml`, four live ER-2 decision artifacts and the M5 trace. |
| `2026-10-06-layer2off-pilot.md`, `2026-10-03-loop-family-and-visual-pass.md`, `2026-10-05-flow-metrics.md` | Convoy history: VLM-off clog, oracle-only references, goal-stack latch recurrence. |
| `docs/implementation_notes.md` (2026-09-29 to 2026-10-04 entries) | B3 dispatch gap, goal-table fix ±0.30 → ±0.36, measured minima. |
| `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md` lines 92–103 | The registered B3 censoring valve. |
| `docs/superpowers/specs/2026-10-06-v3-scene-design.md` (feat/v3-design) lines 815–905 | S6 feasibility analysis: "a second-aisle head-on is not resolvable with axis-aligned escorts". |
| Code at `68e67b5` | M3 grounder, plan verifier, M5 state machine, M4 safety exemptions, config models, scorers. |
| Not read | `2026-10-06-verbatim-pilot.md`, `2026-10-03-step7b-oracle-freeze.md` and `2026-10-04-battery-v2-results.md` beyond grep: none of them contain convoy or S6 outcome data. `2026-10-06-prereg-v3-design.md` was not opened. S6's "decision-scored" status is taken from the scene yaml, the v3 scene design and the first-light report. |

Offline checks run for this scope (scripts and outputs are in the scratchpad `checks/` folder, not committed):

- **Loader check.** `load_overlays.py` loads the earlier overlays through the 68e67b5 `load_config` and `GroundingParams`.
- **Re-grounding.** `reground.py` and `reground_full.py` re-ground recorded and scripted decisions. They call 68e67b5's `ground_reasoner_result` and `verify_and_repair_plan`, the same two calls `reasoning_pipeline.py:1604-1650` makes.
- **Map check.** The S6 maneuver endpoints were checked against `warehouse_map_s6_dual_conflict.pgm`.
- **Latch distances.** The robot_1–robot_3 GT minimum was computed for every local convoy bundle.

---

## 3. Shared Facts

### Runtime and VM

- **Fix branch.** `fix/safety-exemption-scope` (worktree v7c) sits at 68e67b5 with **no commits and no working-tree changes** (verified). The key name and semantics of the fix are unknown, so every fix assertion in §8 is a placeholder.
- **RTF is not stable** (verified from `m5_scene.jsonl`, sim stamp vs wall `t`):

  | Run | VM | RECORD | RTF |
  |---|---|---|---|
  | IB10 live smoke `ib10L_e01_armA_a2` | current | 0 | **0.297** |
  | Layer-2-off B3 `l2_03_b3_s42` | old | 0 | 0.225 |
  | Battery harvest `b2_convoy_on` | old | unverified (frame snapshots on) | 0.288 |
  | S6 live pilot | old | 1 | 0.219 |

  - The gap cannot be attributed to the VM alone.
  - Every `start_delay_sec`, the 12 s stall threshold and the 15 s cooldown are **wall** time (`task_registry`, `orchestrator.yaml`), so their sim-time effect moves with RTF.
- **Slot wall clock.** The IB10 smoke slot took 19.1 min for 300 sim-s, including bring-up and restore (16:28:48 → 16:47:54). The E02 Arm B slot took 22.6 min (17:01:10 → 17:23:48) (verified, driver logs).
- **Seeds are labels.** `seed` is read only for run naming and the manifest (`isaac/vgu_sim/runner.py:94,100,260`, `scenario_builder.py:92`). Nothing in the scenario schema randomizes or jitters spawns (`grep jitter|random` in `isaac/vgu_sim/config.py`: none) (verified).
  - The brief's assumption that spawn jitter is already supported does **not hold**.

### Pipeline mechanics

- **One decision, one command.**
  - M5 grounds the dispatched command from the decision's fields: strategy, `yield_robot`, `involved_robots` and `crossing_order` (`reasoning_pipeline.py:1604-1615`).
  - The `proposed_plan` is only verified, for provenance and `dispatch_matches_plan` (`:1636-1650`). A plan cannot add a second maneuver.
- **Plan consistency rule.**
  - A `yield` plan must carry exactly one `yield` leg (`command_grounder.py:3460-3461`, `_is_consistent`). A two-yield plan under `yield` is rejected to `m3_default`.
  - `reverse` and `convoy` plans are unconstrained (verified).
- **Busy gate.**
  - An event is suppressed if any of its robots is in an unresolved command or in cooldown (`state_machine.py:103-105`).
  - A one-robot stall beside a busy set of two or more robots is folded (`:34-50`).
  - Cooldown starts on the event's robots (`orchestrator_node.py:1387`).
- **M4 exemption paths** (`safety.py:186-251`, `CLEARING_ACTIONS = {yield, reverse}`):
  - **E1:** a `reverse` (or a yield without a passer order) is exempt against **every** member of its own command.
  - **E2:** a yielder that is backing up or pulling off is exempt against every member and every passer.
  - **E3:** from the hold on, passers are admitted one by one, each after the previous passer's linked wait COMPLETED.
  - **E4:** two passers are never exempt from each other.
  - **E5:** the A19 latch waiver (`capture_latch_partners`, `:558-605`) is not gated by any key.
  - **Lane-scoped holds.** M4 has no notion of them (no `lane_scoped` in `swarm_execution`). A hold member is an ordinary command member, so E1/E2 cover it.
- **Off switches.**
  - `reasoning_enabled: false` (VLM-off) loads `initial_tasks` and runs base missions with no detection, M2, M3 or dispatch (`models.py:536-544`).
  - `dispatch_enabled: false` runs M2/M3 and logs the decision but never dispatches (`models.py:517-523`). Both exist at 68e67b5 (verified).

---

## 4. Convoy (`convoy_counterflow_slip`)

### 4.1 Runnable at 68e67b5?

| Item | Finding | Status |
|---|---|---|
| Scene files | The yaml, map (`warehouse_map_convoy_counterflow_slip.*`) and pinned tests are tracked at 68e67b5. `_slip` differs from v1 only in `name` and `oracle`. | Verified |
| USD | Must be built on the current VM, as root, checked by file existence and `validate_simulation`, as `build_ib.sh` does. Every earlier build was on the deleted VM. | Verified need |
| Overlay | `layer2off_pilot/overlays/b3_orchestrator.yaml` (`a6473853`) loads through the 68e67b5 `load_config`. It carries the four-robot `initial_tasks` (robot_3 and robot_4 `start_delay_sec: 120`), `corridor.half_length_m 0.5`, `plan_channel_enabled false` and `task_stream` off. The keys it lacks come up at their defaults. | Verified |
| Comparability with IB10 Arm A | A loader dump-diff against `ib10_armA.yaml` differs, outside `initial_tasks`, only in `keep_debug_frames` and `plan_channel_enabled` (both false in the convoy overlay; set them true), `scenario_geometry` (scene data) and `shadow_classical_zones`. `grounding_params_path` is the same string in both, so convoy needs its own legacy file (§6). | Verified |
| Grounding mode | The scene was designed and every 4/4 run made under **legacy** grounding (`b3_rag.yaml`, `63f50f91`, `grounding.mode: legacy`; loads at 68e67b5). The shipped `config/rag.yaml` is `derived`. | Verified |
| Legacy re-ground | On a recorded convoy snapshot (`b2_convoy_on`, stamp 28.7), the oracle-order mock grounds to the designed command: `yield` robot_2, backup 1.028 m, park x 1.124, lateral 0.36, order [robot_1, robot_3, robot_4], escorts 1.863 / 3.684 / 4.256 m (the yaml header gives 1.00–1.08, 1.124 and 1.89–1.97 / 3.674 / 4.244). The `convoy` label aliases to the same command (`strategy=aliased:convoy`). | Verified |
| Derived re-ground | robot_2 parks at x 1.611, y −0.358, and the escorts grow to 2.35 / 4.171 / 4.743 m. robot_4 would be escorted from x −2.48 to about 2.26, past its own goal (1.85) and 0.41 m from the (2.45, +0.36) goal: a latch. The yield-robot_1 alternative turns into a `reroute`. | Verified grounding; latch is inference |
| VLM-off arm | Supported (`reasoning_enabled: false`, as IB10 Arm B). The only prior is n = 1, clogged 0/4: every robot froze in the 0.45 m latch within 1 s of onset. That run used the mock "no congestion" backend on the v2 tree, not `reasoning_enabled: false`. | Verified |
| Live-model history | None. Every 4/4 convoy run is a scripted oracle-order mock (`layer2off-pilot.md` §B3 provenance). | Verified |

**Known defect, the goal-stack latch (not fixed in code).**

- The ±0.36 goal table is the only fix, and it is scene data.
- The mechanism is unchanged at 68e67b5: a passer–passer pair is never exempt (E4), and robot_3, back on its base mission, passes the parked robot_1.
- GT robot_1–robot_3 minimum after t = 60 s in every local ±0.36 bundle: 0.4746 and 0.4628 (`b3_fix` s42/s43), 0.4847 (B3DEMO), 0.4579 and 0.4735 (harvest off/on). All are clean, but by only **8–35 mm** (verified).
- One more ±0.36 run latched at 0.4448 m (loop-family visual pass, reported; its bundle is not on this disk).
- Observed rate: 1 latch in 6 oracle runs, all on the old VM. The rate at RTF 0.30 is unknown.

### 4.2 The decision the scene asks for, and what M3 does with it

At the first trigger, robot_1 and robot_2 stand nose to nose at the A55-J gate. robot_3 and robot_4 are still at spawn, held by the 120 wall-s start delay. The prompt shows all four robots STOPPED, with goals.

| Model answer | 68e67b5 legacy grounding (verified) | Expected outcome |
|---|---|---|
| `yield` robot_2, all four involved, with or without `crossing_order` | Oracle command. Without an order, M3 queues by gate distance, which gives [r1, r3, r4]. | Designed resolution (oracle runs 5 of 6 clean). |
| `convoy`, all four | The same command, tagged `aliased:convoy`. | Same. |
| `yield` robot_2 with only robot_1 and robot_2 involved (Arm B's shape) | `yield` robot_2 plus robot_1's wait. robot_3 and robot_4 are not commanded. | Bystander latch: censored by construction (yaml lines 95–98). |
| `yield` robot_1, all four | Alternative order. robot_2 is escorted west to x −1.774, 0.13 m from the held robot_3. | Latch: censored (yaml oracle rationale). |
| `reverse`, all four | All four robots reverse 1.3 m. E1 exempts every pair. | No resolution; unvalidated motion. |

- **Decision deadline (inference).**
  - The first dispatched command must name robot_3 and robot_4 before their wall-clock release. Once released uncommanded, they close in: robot_4 reached 0.433 m of robot_3 within about 4 s (layer2off). That passer pair can never be exempt, so the latch is permanent.
  - Designed timing: dispatch by about 75 wall-s, release at 120 wall-s. At RTF 0.30 the release lands about 36 sim-s after M5 starts, against 25–31 at the design RTF.
  - Log the dispatch and release wall times in every episode.
- **Plan channel.**
  - Provenance labels need `plan_channel_enabled: true` (prompt v3). Every convoy run so far had it off. Dispatch does not read the plan, so the channel changes the prompt and the bookkeeping, not the command (verified code path).
  - A plan hold (`plan_held`) under re-analysis has not been exercised on convoy. The oracle episode covers it.

### 4.3 Horizon, wall clock and bring-up

| Item | Value |
|---|---|
| Horizon | `duration_sec: 260` (the yaml governs Isaac). The last arrival (robot_2 returning) came at **201.0–205.3 sim-s** in the five local ±0.36 oracle bundles (GT, `score_ground_truth` rule; verified), so there is **55–59 s of slack**. The layer2off "237.7" figure is total delay summed over robots, not a makespan. |
| Wall per slot (estimate) | 260 / RTF plus about 2.5 min overhead: **17 min** at 0.297, **22 min** at 0.225. Arm B uses the same slot, since Isaac runs the full horizon. |
| Bring-up | Parallel (`fc_launch.sh` default), as IB10. The layer2off onset of 29.1 sim-s sits inside the window. |
| Jam validity | `score_conflict` (`coverage_scene_scores.py:316-341`): `onset_in_window` [15, 50] and `min_duration_met` (≥ 2.0 s), from the yaml `expected_conflict`. |

### 4.4 Outcome definitions to freeze before any run (proposals)

| Outcome | Definition |
|---|---|
| Valid jam | `onset_in_window` and `min_duration_met`, both true on GT. |
| Resolved (primary) | Valid jam AND all four robots arrived under `score_ground_truth`'s position rule, inside 260 sim-s. |
| Episode success | Resolved AND zero M4 `hard_contact_floor_m=0.2 pairs=` stops AND GT minimum pairwise centre distance after t0 ≥ 0.18 m. |
| Time to full resolution | Last arrival minus the GT conflict onset. Censored at the horizon. |
| Plan provenance | Per dispatch: `vlm_verbatim`, `repaired` or `m3_default`. Episode label as in IB10 §4. |
| Refusals and degradations | Counts by reason string from each artifact: `grounding_degradations`, `plan.rejection_reason`, `plan.edits[].reason`, `strategy=aliased:*`. |
| Decision content | Whether robot_3 and robot_4 are in `involved_robots`; the yielder; the strategy label (`convoy` vs `yield`, scored apart); and whether the executed GT crossing order is [r1, r3, r4]. |
| `first_slipper` and latency | Reported only (`score_b3`). The identity is degenerate under correct execution and meaningless in Arm B. |
| Goal-stack latch label | GT robot_1–robot_3 < 0.45 m at any time after robot_3's own escort leg ends (its M4 `resume base mission robot=robot_3` line, or else its GT escort end near x 1.774), with M4 `min_distance_violation` lines for the pair. It must not wait for "all escorts COMPLETED": in the latched runs `escort robot_4: COMPLETED` never printed. Per the prereg-v1 valve this is *apparatus-censored*. **Owner decision:** the primary outcome counts it as not resolved (proposal), with a sensitivity line that excludes it. |
| Late dispatch label | Arm A: first dispatch after the robot_3 / robot_4 release. Counted as a failure (proposal) and reported. |

**Scorer work** (none of it changes frozen code):

- Write a kit wrapper `score_convoy.py` modelled on `score_ib.py`. It calls the pinned `score_b3` and adds:
  - the success rule, floor stops, GT minimum pairwise distance and time to resolution;
  - attribution, refusal counts, the two labels above and the executed order (from `final_crossing` / `first_passer`).
- Pass `allow_mock` for the oracle episode, or `score_b3` raises `MockBackendError`.
- Adapt `cond_ib.py`'s Arm A checks:
  - the gemini model id;
  - the artifact's `grounding_mode == "legacy"` and `grounding_params_source.path` = the convoy file;
  - drop the IB10 pull-off check.

---

## 5. S6 (`s6_dual_conflict`)

### 5.1 Runnable at 68e67b5?

| Item | Finding | Status |
|---|---|---|
| Scene | The yaml, map and tests are tracked. Its header still reads "AUTHORED, NOT RUN" although it ran twice on 2026-10-08. | Verified |
| Overlay | `s6_first_light/_vm_driver/s6_orchestrator.yaml` (`3d9fda63`) loads at 68e67b5: `plan_channel_enabled true`, D = 16 wall-s on robot_3 and robot_4, the T1 corridor `half_length_m 1.0`, `config/rag.yaml` (derived). | Verified |
| Start delay D | Derived for RTF 0.21–0.24. The pilot's re-derivation pointed to about 20 wall-s. At RTF 0.30 the per-run D\* scales to roughly 13–18 wall-s (inference). It must be re-measured on this VM before any run. | Inference |
| VLM-off arm | Supported. The mock no-intervention run held both jams for all 150 s. | Verified |
| Scorer | None committed. `DualConflictOracleConfig` (`isaac/vgu_sim/config.py:894`) is a config only. The pilot was scored by the uncommitted `s6_analyze.py` in the run's driver folder. `score_conflict` reads the single `aisle_barrier` span, so it cannot see pair B. The multi-event scorer (design build item 7) was never built. | Verified |
| Known defect | Probable wall touch: in the pilot, robot_4 reached x 2.098 (chassis rear about 2.200, the aisle end). | Reported |

### 5.2 Can one decision, or a sequence, resolve both pairs?

Each case below re-grounds a recorded snapshot (decision 2, stamp 51.9, both pairs stopped) through the 68e67b5 grounder (verified). The last column is inference except where marked.

| Decision | Derived (recorded overlay) | Derived + `dynamic_scene_arms` | Consequence |
|---|---|---|---|
| Pair B only: `yield` / `reverse` robot_3 or robot_4 | Refused: "both robots outside the corridor on the same side". `temporary_wait` for robot_3 and robot_4. | Grounds a yield. robot_4's yield retreats to (2.74, 1.60). robot_3's yield retreats to (−0.42, 1.54) and escorts robot_4 2.35 m, to about −1.07. | (2.74, 1.60) and (−1.07, 1.2) are **occupied** on the S6 map (verified). The overlay declares no static obstacles, so M3 cannot see the racks. |
| Pair B, robot_3 yields, with the S1b escort cap (`config/grounding/s1b_dynamic.yaml`) | — | The escort is capped at 1.284 m and ends at robot_4's goal (0, 1.2), which is free. | robot_3's return to (2.05, 1.2) passes robot_4 parked at its goal at a **0.19 m** nominal straight-line closest approach. Both are un-commanded by then, so a permanent latch is likely. The same params put robot_2's retreat at y −0.72, inside the rack (verified occupied). |
| Pair A only: `yield` robot_2 or robot_1 | Executable yield (T1 head-on shape). | Same. | Pair A can resolve, with at most **2 of 4** arrivals. |
| All four, `yield` robot_2 (decision 2 verbatim) | `yield` infeasible ("no backup distance … clearance 1.7 m") → `reroute` robot_2 plus waits. | `yield` robot_2, with robot_3 and robot_4 as lane-scoped holds. | Derived: worse than the pair-A-only answer. The map has no detour (header), so the reroute cannot progress. |
| All four, two-yield plan | Plan rejected (`m3_default`: "not refined by actions ['yield','cross','yield','cross']") → `reroute`. | Rejected → `yield` robot_2 plus lane holds. | One command can carry only one yield. |
| All four, `reverse` (decision 3) | Four-robot `reverse`, no degradation. | Same. | E1 exempts pairs across both clusters. |

**Sequence (verified from the pilot `m5.log`).**

- Trigger sets span both pairs, for example `['robot_2','robot_3','robot_4']` and all four. Every such trigger was `suppressed` while any member was busy.
- So analyses serialize: four in 150 s at scene stamps 38.7, 51.9, 82.0 and 133.9.
- Two serialized T1-scale resolutions would not fit in the 150 s horizon.
- Extending `duration_sec` means a yaml edit, a new md5, a re-pin of `tests/unit/test_s6_dual_conflict_scenario.py`, and a USD rebuild for safety.

**Conclusion (inference, consistent with the v3 scene design).**

- Under the recorded overlay, pair B cannot be resolved at 68e67b5 under any decision: every pair-B command is refused (verified).
- Dynamic arms is a new, unvalidated config for S6. Only its default retreat (`retreat=default:no_choice`) was checked here. The S6 overlay has stage-2 retreat selection on, and a stage-2 candidate was not checked.
- Per-cluster dispatch (v4) would fix "one decision, two pairs", not pair B's geometry.
- The grounding also *inverts* the decision score. The answer that names both pairs grounds to a worse command than the pair-A-only answer. A VLM-on outcome on S6 would therefore penalize the better decision.

### 5.3 What S6 can still deliver

| Option | What it measures | Cost | Recommendation |
|---|---|---|---|
| S6-0: do not run | — | 0 | **Default.** Report S6 execution as out of reach at 68e67b5, with this evidence. |
| S6-D: decision-only live, `dispatch_enabled: false` | The PROPOSED oracle (named / addressed both) on the first trigger and on re-analyses, with no execution. | About 11–14 min per slot; Gemini about $0.01–0.05 per episode. Needs D re-measured and the committed decision scorer. | Only if the thesis needs a live S6 decision rate. This is not a matched contrast (Arm B makes no decisions). |
| S6-R: offline replay of the four recorded prompts and frames | Decision stability on fixed stimuli. | No VM; paid API, which needs owner approval. | Cheapest way to an S6 decision n. |
| S6′: redesign (groundable pair B, racks declared as static obstacles, dynamic arms, goals off the return path) | Real dual-conflict resolution. | New scene, new pins and pilots. | Out of scope for this tranche. |

If the owner overrides and runs S6 with execution, three things must exist first:

- a per-pair GT jam-validity gate and pair-level arrivals, which is new scorer work;
- the S6 USD built on this VM, as root, with a file-existence check;
- D re-measured at the current RTF (a mock timing pilot, n ≥ 3).

Even then, report the outcome per pair, never as one resolved / not-resolved bit.

---

## 6. Design Proposal (convoy)

### Arms and order

| Item | Proposal |
|---|---|
| Arm A | Layer 2 on, live `gemini-robotics-er-2-preview`, legacy grounding, `plan_channel_enabled: true`. |
| Arm B | Arm A's overlay plus `reasoning_enabled: false`. |
| Runtime | 68e67b5 plus the safety fix, key on. Grounding comes from a kit-installed `config/rag_convoy_legacy.yaml` via `grounding_params_path`, so the pinned `config/rag.yaml` (`e18c723c`) stays untouched. If the shipped file is swapped instead, add it to the restore list. |
| Floor | The 0.20 m `hard_contact_floor_m` swap (`safety_floor020.yaml`, `c41913f0`) is installed for every convoy arm, as for IB10. The success rule depends on it, and convoy has never run with it. |
| Invocation 1 (smoke) | **O1** scripted oracle-order mock (`convoy_counterflow_oracle_order_once.json`, plan channel on, key on) → **A1** live. The chain stops for owner inspection. |
| O1 mechanics | O1 is a third arm, "M" (mock). Its overlay is Arm A's with the mock backend and the decision file wired in, the way the v2 sweeps used `scripts/strategy_regret.py`'s mock paths. `cond_ib.py`'s Arm A gate rejects mock artifacts, so add an Arm M gate: every artifact names the mock backend, and the first decision's request matches the decision file. Score it with `allow_mock`. |
| Gate after O1 | Resolved 4/4, zero floor stops, GT minimum ≥ 0.18 m, release after dispatch, exempt pairs (robot_2, robot_3) and (robot_2, robot_4) seen during their escorts (§8). On a goal-stack latch: report it, no re-run, owner rules. On any other O1 failure: no live episode; the failure is execution, not the model. |
| Invocation 2 | Interleaved, fixed in advance: B1 A2 B2 A3 B3 A4 B4 A5 B5. A1 counts if it passes the harness gates (the IB10 smoke rule). |
| n | **5 per arm** (proposal), matching IB10. A cheaper variant is 5 A / 3 B, justified only if IB10's Arm B shows identical freezes. |

### Why n = 5, and what varies

- **Arm B is near-deterministic.** Every layer-2-off cell froze within 1 s of onset. Its repeats are replicates, not samples.
- **Arm A has one legitimate source of variation: model sampling.**
  - ER-2 runs at temperature 0.6, top_k 20, top_p 0.95, all recorded as `unsupported_sampling` and not settable.
  - The S6 pilot gave four different answers to similar scenes.
  - Trigger timing (Nav2 departure jitter of up to 1.9 sim-s in S6) and RTF add small state variation.
- **There is no spawn jitter** (§3). The only way to vary poses would be authored pose variants, each a new yaml, USD, map and pin set: out of scope.
- Report counts only, as IB10 §6 does. These are not independent samples.

### Exclusions (proposal, IB10 §5 plus)

- Bring-up abort: retry up to 3 times.
- Invalid jam: excluded and reported.
- Harness failure: excluded; the chain stops.
- Truncated: counted only if all four robots had arrived.
- Gemini probe failure: stop.
- Goal-stack latch: labelled, counted per the owner's §4.4 ruling, never re-run.
- Late dispatch: counted as a failure.

### Caps and cost (estimates)

| Item | Estimate |
|---|---|
| Slots | 11 (O1 + 5 A + 5 B) at 17–22 min = **3.1–4.0 GPU-h** |
| Per-invocation overhead (VM start, snapshot, USD build, restore, stop) | About 0.5–0.75 h × 2 (estimate, from the IB10 kit's 45 min teardown reserve) |
| Convoy total | **About 4.2–5.5 GPU-h** on the L4 VM |
| Gemini | About $0.02–0.05 per Arm A episode. IB10 smoke: 2 analyses, $0.0106. A resolved convoy run re-analyses about 6–7 times after clearing (mock bundles). Total about $0.1–0.3. |
| Caps | 6 h wall per invocation; $0.50 per episode; $3.00 total (the IB10 values). `MAX_ANALYSES=0`. |

### Kit changes (from the IB10 kit)

- `ib_env.sh`: `SCEN=convoy_counterflow_slip` and its yaml md5. Pin `scene_geometry.py`, `command_grounder.py`, `safety.py` and the fix's files at the fixed-runtime md5s. Drop the IB10-only pins.
- `build_ib.sh`: unchanged logic.
- Overlays: Arm A and Arm B generated from `b3_orchestrator.yaml` plus `plan_channel_enabled: true` and `keep_debug_frames: true`, with every key asserted by the deployed loader (`ARM_CHECK.txt`).
- The condition gate and the scorer as in §4.4.
- Add per-episode log lines: dispatch wall time, release wall time, and the release sim time read from GT departures.

---

## 7. The Intersection Bridge

The convoy runs need the fixed runtime. The IB10 results come from plain 68e67b5.

| Option | Content | Cost | What it buys |
|---|---|---|---|
| **Bridge-2 (recommended)** | 2 IB10 VLM-on episodes on the fixed runtime, key on, in convoy invocation 1 after O1. The IB10 USD is built in the same invocation. | About 40 GPU-min + about 10 min build; Gemini under $0.05 | Shows whether IB10's resolution survives the fix. The fix targets exactly IB10's open caveat: `junction_clear` phases name all four robots, so E1/E2 cover cross-cluster pairs. Never pooled with the 5+5 run. |
| Limitation only | State in the thesis: "convoy on 68e67b5+fix (key on), IB10 on 68e67b5". | 0 | Defensible for VLM-off arms (next bullet), weak for VLM-on, since the fix changes the exemption scope IB10 relies on. |

- **The fix should not change a VLM-off arm, if it only narrows exemptions.** Exemptions arise only from ACTIVE clearing commands (`CoordinationTracker.exemption`, `safety.py:517-556`), and Arm B dispatches none. Under that condition, Arm B results carry across both runtimes (inference from code). The fix's actual semantics are unknown, so confirm this once the fix lands.
- A VLM-on bridge is the only part with real exposure.

---

## 8. Safety-Fix Interaction

The fix branch has no code yet, so the rows below are what each scene *exercises*. The assertions become concrete once the key exists.

| Path (§3) | Convoy | S6 (if ever run) | IB10 bridge |
|---|---|---|---|
| E1, `reverse` against all members | Only if the model answers `reverse` with all four. | Recorded decision 3 dispatched exactly this across both pairs. | `junction_clear` recede phases. |
| E2, backing-up yielder against all members | robot_2 against robot_1, robot_3 and robot_4, while robot_3 and robot_4 are about 2 m away, outside robot_2's latch cluster at dispatch. | `yield` robot_2 against lane-held robot_3 and robot_4 (cross-cluster). | Release yield. |
| E3, progressive passer admission | **Load-bearing.** robot_3 and robot_4 pass the parked robot_2 at lateral 0.36 < 0.45. | — | Phased release. |
| E4, passer–passer never exempt | Goal-stack residual (robot_1–robot_3). | — | — |
| E5, A19 waiver | Inert: robot_2 starts latched only to robot_1, a member. | Possible if a yielder starts latched across pairs. | Untested on IB10 (IB10 spec §9 lists it as smoke-tested only). |

- **Critical requirement on the fix (inference).**
  - A cluster scope that takes robot_3 and robot_4 out of robot_2's admissible partners because they were not in robot_2's latch cluster at dispatch would latch robot_3 against the parked robot_2. That breaks the convoy by construction: Arm B's censoring mechanism, inside Arm A.
  - The fix's unit tests should replay the convoy command sequence (O1's command, statuses in order) before any VM time.
- **Per-episode assertions (proposal):**
  - the key-on line from the **deployed** loader, in `ARM_CHECK.txt` and M4's startup line;
  - every exempt-pair or waiver line classified as same-command admitted passer, same-cluster, or cross-cluster-denied (format TBD with the fix);
  - for convoy, (robot_2, robot_3) and (robot_2, robot_4) appear as admitted during their escorts, and no cross-cluster denial names them;
  - zero floor stops.

---

## 9. Risks and Cheapest Checks

| Risk | Scene | Cheapest check (no VM unless noted) |
|---|---|---|
| The fix's cluster scope breaks E3 for late passers | Convoy | Unit test on the fix branch, replaying O1's command and status sequence through `CoordinationTracker`. |
| Legacy grounding drifts in a live snapshot (the model's answer, different poses) | Convoy | Done here for 9 decisions. Extend with the A1 artifact offline after the smoke. |
| Goal-stack latch rate on the new VM | Convoy | None offline. O1 plus the 5 A episodes give the rate. Pre-agree the §4.4 ruling. |
| Release-before-dispatch at RTF 0.30 | Convoy | Read O1's logs. Owner choice: keep the registered 120 wall-s (proposal), or rescale it to about 85–90 wall-s to keep the designed sim time, which deviates from the goal row. |
| Plan channel on alters dispatch or holds a plan | Convoy | O1 runs with the channel on. Offline: re-ground with `PlanTracker` on the O1 artifacts. |
| 260 s horizon too tight at a higher dispatch latency | Convoy | Low risk: the oracle's last arrival at 201–205 sim-s leaves 55–59 s. Check O1's last arrival; if under 30 s of slack, the owner rules on a horizon amendment before the follow-up. |
| Pair B unresolvable | S6 | Settled here (map check plus re-ground). No VM spend. |
| D wrong at the new RTF | S6 (S6-D only) | A RECORD-off timing pilot, n ≥ 3, mock backend (from the first-light report). |

---

## 10. Open Owner Decisions

1. **Bridge:** Bridge-2 (about 50 GPU-min) or limitation only.
2. **Goal-stack latch:** count it as not resolved (proposal), or exclude it per the prereg-v1 valve.
3. **Convoy grounding:** legacy (proposal; the only validated mode), or derived for parity with IB10, which the re-ground shows is likely to latch robot_4.
4. **Hold-back:** keep 120 wall-s, or rescale for RTF 0.30.
5. **n:** 5/5 (proposal) or 5 A / 3 B.
6. **Late dispatch:** count it as a failure (proposal) or exclude it.
7. **S6:** S6-0 (proposal), S6-D, S6-R, or schedule S6′.
8. **Header correction:** fix the stale "AUTHORED, NOT RUN" header in `s6_dual_conflict.yaml` (a docs-only edit; it changes the yaml md5 and the pins).

---

## 11. What Could Not Be Determined

- **The safety fix's key name, scope rule and log format.** The branch is empty.
- **The goal-stack latch rate on the current VM**, and whether RTF 0.30 helps or hurts it.
- **Whether a live ER-2 includes the held robot_3 and robot_4 in its first convoy decision.** That is the experiment's question; no live convoy artifact exists.
- **The 0.4448 m loop-family latch.** Its bundle is not on this disk, so only the reported value is used.
- **Plan-hold behaviour under convoy re-analyses.** Not traced in code.
- **RTF variance on the current VM.** One measurement only (0.297).
- **The VM's hourly rate.** Cost is given in GPU-hours only.

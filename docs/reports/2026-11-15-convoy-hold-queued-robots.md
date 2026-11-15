# Convoy Queued-Robot Hold (Grounding Fix b)

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: default-off M3 hold of uncommanded corridor-crossers; tests; offline replay (3 parts); per-take estimate; live-retake kit requirements.

---

## Summary

- **Defect (verified earlier, campaign report section 5).** In all three live convoy takes, ER-2's first decision named only the standoff pair, robot_1 and robot_2. Legacy grounding commands only the robots a decision names. So when M5's 120 s start delay ran out, robot_3 and robot_4 were released with no command, followed the passer through the gate, and all four latched under M4's 0.45 m distance. A facts-only prompt note did not change this: 0 of 44 answers named them (`docs/reports/2026-11-15-convoy-held-robot-prompt-check.md`).
- **Fix (built; unit-tested; replayed offline).** New `OrchestratorConfig` key `grounding_hold_queued_crossers`, default off. With the key on, a legacy-mode corridor yield also holds every robot that:
  - the decision does not name;
  - stands outside the single declared corridor;
  - has its goal past the far mouth.
- **How each added robot is held.** It gets a linked wait, appended to the crossing order after the model's named passer(s), nearest to the gate first. It is grounded exactly as if the decision had named it. The model's strategy, yielder and named passer are untouched, and every existing check still runs.
- **Transparency.**
  - Each added robot is tagged `crossing_order=augmented:<id>:goal_across_corridor`.
  - The added robots are listed on the yield (`queued_crossers_added`) and in the artifact (`grounding_queued_crossers_added`).
  - Plan legs that disagree with the hold are repaired. The edits are `substitute` edits whose reason starts `queued crosser hold:`, so the provenance reads `repaired`, not `vlm_verbatim`.
- **Replay (verified by running, offline, no model calls).**
  - All 47 first-trigger answers (3 live takes and 44 stored answers) were replayed. Every one of the 46 yields becomes the four-robot sequence. Every one is identical to grounding a decision that named all four robots, apart from the trace key and the tags.
  - All 33 later convoy decisions are unchanged.
  - All 15 head-on, intersection and five-robot decisions are unchanged.
- **Per-take estimate (inferred).** With the prompt key off, the model picks robot_2 as yielder in 12 of 18 answers. That is the variant that resolved in the smoke (n = 1). robot_1 is picked in 6 of 18, and the scene file says that variant latches. So the realistic chance of a resolving first sequence is about two in three per take, times an unmeasured live success rate for that structure.
- **Not done:** no live run; no kit or runtime-delta directory touched; no push.

---

## 1. Defect

- **Recorded first decisions** (live takes 1–3; v7j `demo_campaign/cv/runs/cvD_t0{1,2,3}_a1`):
  - all three are `yield`, with `involved_robots` [robot_1, robot_2];
  - the yielder is robot_2, robot_1 and robot_2 for takes 1, 2 and 3;
  - the plans give robot_3 and robot_4 `continue` (takes 1 and 3) or `wait` (take 2).
- **Legacy grounding** (`_ground_legacy`) builds the command from `resolve_robot_order(decision)` only. So the queued robots got no action.
- **Plan verification hid the gap.** It accepted takes 1 and 3 as `vlm_verbatim`, and also take 2, with `dispatch_matches_plan=false`.
- **What resolved (smoke, v7f `convoy_live/runs/cvL_e01_armC_a1`).**
  - The scripted decision named all four robots, and its command was yield robot_2, with linked waits robot_1 → 0, robot_3 → 1 and robot_4 → 2, and crossing order [robot_1, robot_3, robot_4].
  - `gate_admit` ran in that order, and the scene resolved 4/4.

---

## 2. Design

### 2.1 Choice: Hold Uncommanded Corridor-Crossers (Not Honour Plan `wait` Legs)

**Chosen.** Hold the robots by geometry, whatever the model wrote for them.

- **The rule does not depend on the model.** The honour-the-plan variant would have helped only when the plan says `wait`: 16 of 22 answers with the prompt note, and only 2 of 22 without it. The live convoy kit runs without the note, and take 1 and take 3 said `continue`.
- **A wait leg would also need its own release rule.** A plain `wait` leg on a queued robot is not tied to the yield. Honouring it as a timed wait would still release the robot mid-crossing, or need new M4 sequencing. Appending the robot to the existing ordered crossing reuses M4's verified `crossing_chain` release, which is the smoke's mechanism.
- **Only one variant was built.**

### 2.2 The Predicate

The predicate uses only runtime state the grounder already receives: each robot's snapshot pose and goal, and the declared `scenario_geometry` corridor. It has no scenario constants and no robot ids.

- **`scene_geometry.traverses_corridor(position, goal, geometry)`** is true when:
  - the robot stands outside the corridor (|along − `center_m`| > `half_length_m`); and
  - its goal lies past the far mouth (sign(robot side) × goal along < −`half_length_m`).
  - It reads the corridor axis only. That is the single-corridor assumption every legacy check already makes (`_beyond_corridor_same_side`).
- **`scene_geometry.is_single_corridor(geometry)`** limits the predicate to a plain declared corridor. It is false with any of:
  - `arms`;
  - `junction_declared`;
  - `junction_boxes`;
  - a dynamic-view `junction_box`, `lane_robots` or `lane_heading_rad`.
- **Held / start-pending state was checked and is not used.**
  - M5's registry knows it (`TaskRegistry.is_pending`).
  - But the frame M3 grounds on (`retreat_stage2.snapshot_frame_from_request`) has an empty `held_robot_ids`.
  - The request carries held ids only under the prompt key `prompt_held_robot_state`.
  - Using it would need new M5 → M3 plumbing. It is also not needed: a released robot whose goal is across the gate traverses it all the same.

### 2.3 Where the Hold Applies

- **`command_grounder.queued_crosser_outcome(decision, snapshot, geometry, ...)`** decides which robots are added. It returns nothing unless all of these hold:
  - the (alias- and view-resolved) decision is a `yield`;
  - the scene is a single corridor;
  - the yield the decision asks for would itself ground.
- **"Would itself ground" means every existing check runs first, unchanged:** the feasibility gate, the first-passer check on the named order, and the corridor same-side check.
- **Order.** Qualifying robots are sorted by distance from the corridor centre along the axis (ties by id), then appended after the named passer order.
- **First-passer check on the extended order.** If the extended order fails the first-passer check, nothing is added. The model's pair yield is then grounded exactly as with the key off, and tagged `crossing_order=augment_withheld:<ids>:<refusal>`. Holding the queued robots never turns a groundable yield into a refusal.
- **Refusals are unchanged.** A refused yield's wait fan-out stays on the decision's own robots, so later-trigger refusals are byte-identical.
- **Scope: legacy mode only (`params.mode == "legacy"` or None).** In derived mode, and for junction or dynamic geometry, the key is a no-op by construction. Every head-on, intersection and five-robot campaign bundle grounds in derived mode (section 5.3), so the key cannot change them.
  - This scoping was chosen before the replay, not forced by it.
  - It is not evidence that the idea would be harmless in derived scenes.
- **M4 is unchanged.** The added robots get only `temporary_wait` with `linked_position` (the existing multi-passer convention). Their clearances and backstops come from the existing multi-passer sizing.

---

## 3. Provenance and Tagging Decision

The precedent is `verify_and_repair_plan`'s A21 off-lane hold (`LANE_SCOPED_HOLD_PREFIX`). In that case, dispatch holds robots outside the decision's roles, and the plan is repaired toward the hold by one `substitute` per robot, with a reason prefix that `plan_metrics` can separate. The new hold follows it.

- **Default plan.** With the key on, `verify_and_repair_plan` resolves the same `queued_crosser_outcome` on the alias-resolved decision and gives each added robot `cross` in M3's default plan. `cross` is what `project_dispatched_legs` reads a linked wait beside a yield as.
- **New check in `_plan_problems`.** Any leg on an added robot other than `cross` fails with reason `queued crosser hold: dispatch holds <id> in the yield's crossing order (goal across the corridor)`.
- **Repair.** `_repair_plan` may only substitute an added robot's leg to `cross`. It never swaps or reorders it into another robot's role: in the first test run, a swap benched the named passer. Each edit reason starts `QUEUED_CROSSER_PREFIX = "queued crosser hold:"`.
- **The result:**
  - a plan with `continue` or `wait` for the queued robots reads `repaired`, with exactly 2 `substitute` edits;
  - an absent plan reads `m3_default`, with `cross` legs for them;
  - `dispatch_matches_plan` is true in both cases.
  - A plan that already says `cross` for them stays `vlm_verbatim`. The model wrote those legs, but the command tag still records that the grounder added the robots to the command.
- **Command and artifact records:**
  - one tag per added robot, `crossing_order=augmented:<id>:goal_across_corridor`, registered in `DEGRADATION_TAGS` (cause None, provenance);
  - or one `crossing_order=augment_withheld:<ids>:<refusal>` tag;
  - the yield parameter `queued_crossers_added` (inert in M4, like `park_x_m`);
  - the artifact key `grounding_queued_crossers_added`, written only when something was added.
- **How a scorer tells the cases apart.**
  - "The model named all robots": the key is absent, and the decision's `involved_robots` has four robots.
  - "The grounder added queued robots": the key is present, with the two tags and the `queued crosser hold:` edits.

---

## 4. Key, Files and Tests

**Key.** `grounding_hold_queued_crossers: bool = False` (`OrchestratorConfig`). M5 passes `hold_queued_crossers=True` to `ground_reasoner_result` and `verify_and_repair_plan` only when the key is on. With it off, neither call changes, so every command, plan verdict and artifact is byte-identical; existing fake `ground_fn`s in tests are unaffected. The grounding params YAML is not touched, so the registered `config/grounding/cvl_convoy_legacy.yaml` stays byte-identical.

**Startup line.** When the key is on, `plan_order_status_line` gains the suffix ` grounding_hold_queued_crossers=True`. With the key alone on, the line is exactly:

```text
plan order condition plan_dispatch_order_source=chi prompt_plan_grammar_rules=False prompt_candidate_options=False grounding_hold_queued_crossers=True
```

**Files changed (commit `10b4807`; base `demo/campaign-kits` at `4e5476b`).**

| File | Change | md5 at base | md5 now | md5 at VM pin `68e67b5` |
|---|---|---|---|---|
| `reasoning/rag/command_grounder.py` | outcome, tags, legacy hold, verifier hold | `cfbd1fb8…` | `691d1730dfa141149284c9eaae44b608` | `cfbd1fb8…` (= base) |
| `reasoning/rag/scene_geometry.py` | `traverses_corridor`, `is_single_corridor` | `f0a3bd7e…` | `eda27ce7525e2bbb8f5fbe2bf854d296` | `f0a3bd7e…` (= base) |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` | key, startup suffix | `3a0edecd…` | `575e7abb577650108a54e552623c9d80` | `273bbf7f…` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | pass the key to the pipeline | `71ae0073…` | `ad9a46c65dc95e6b968e976d25c0ac8d` | `e1b3b289…` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` | pipeline flag, artifact key | `e65f594c…` | `76185f21e84a6c1ab43a3d3789291813` | `39a51bfc…` |

**Relative to the VM pin `68e67b5`:**

- The two `reasoning/rag` files are unchanged between the pin and the base. This branch is their only diff from the pin.
- The three M5 files already differ from the pin at the base, by the campaign runtime delta and the held-robot prompt condition (`2f83faf`, md5s in the prompt-check report section 5). This branch adds only the hold to them.
- `reasoning/vlm/models.py` (`52cba14c…`) and `reasoning/vlm/prompt_builder.py` (`f2f33b77…`) are unchanged from the base.
- New non-runtime file: `scripts/convoy_queued_crosser_replay.py`.

**Tests (`tests/unit/test_queued_crosser_hold.py`, 51 new; the snapshots of live takes 1 and 2 are inlined).**

- **Predicate:**
  - goal past the far mouth;
  - goal on the same side;
  - goal inside the corridor;
  - robot inside the corridor;
  - unknown goal;
  - y axis;
  - shifted centre;
  - the single-corridor test for a plain corridor, arms, a declared junction and a lane view.
- **Grounding, using the recorded first-trigger frames:**
  - a pair decision becomes yield plus linked waits for all three others, with all three in the crossing order, for robot_2 (take 1) and for robot_1 (take 2);
  - equality with the decision that names all four, for both yielders;
  - tags; `queued_crossers_added`; the model's yielder and passer stay first; nearest-to-the-gate order;
  - a decision naming all four is unchanged;
  - goals that stay on the robot's side add nothing;
  - key off is identical;
  - a refused yield keeps its fan-out on the named robots;
  - holding withheld when it would trip the first-passer check;
  - no-ops in derived mode, with arms, for non-yield strategies and with no snapshot;
  - with the feasibility gate in `swap` or `refuse` mode, the hold equals the named-all-four command, and adds nothing when the gate refuses the yield.
- **Verification:**
  - key off keeps `vlm_verbatim`;
  - with `continue` or `wait` legs, the plan is repaired with 2 prefixed `substitute` edits;
  - plan and dispatch match for `continue`, `wait` and absent plans;
  - an absent plan gets `cross` defaults;
  - a plan naming all four is unchanged;
  - derived-mode no-op.
- **M5:**
  - the pipeline dispatches the full sequence with a matching repaired plan;
  - the default pipeline passes no new keyword;
  - with the key off, the dispatch is unchanged;
  - the artifact key is present when the hold adds robots and absent when off;
  - config defaults off;
  - startup-line cases;
  - `_build_default_pipeline` receives the key.

**Unit suite (verified by running, one process, after the live run had ended).**

| | Failed | Passed | Skipped | Collection errors (`pxr`) |
|---|---|---|---|---|
| Base `demo/campaign-kits` `4e5476b` | 57 | 7100 | 151 | 3 |
| This branch | 57 | 7151 | 151 | 3 |

The failing ids (FAILED plus ERROR, 60 lines) are identical; `diff` is empty. One of them, `test_write_decision_artifact_preserves_m2_result_on_grounding_failure`, fails on the base too (checked separately).

---

## 5. Offline Replay (Verified by Running; No Model Calls)

**Harness.** `scripts/convoy_queued_crosser_replay.py {first,later,other} --docs-root /Users/tuanhdangdinh/Documents`.

- It runs M5's `InProcessPipeline._run_from_result` on each artifact's own config, legacy or derived grounding params and feasibility mode, with a fresh plan tracker and no stage-2 call.
- It runs each decision twice, with the key off and on.
- It reuses the stimuli and classifier of `scripts/convoy_held_robot_plan_check.py` and the signatures of `scripts/vlm_order_channel_plan_check.py`.
- Outputs are in `data/experiments/2026-11-15-convoy-queued-crosser-replay/`, written there only, never into the bundles or the prompt-check data. Summary md5s: `first_summary.json` `68bbc8f7`, `later_summary.json` `9285b8de`, `other_summary.json` `bd858c9f`.

### 5.1 First Triggers

**Gate.** With the key off, the replay reproduces the recorded dispatched command of all 3 live first decisions and the smoke, 4 of 4 (`command_sig`).

| Answers | n | Full sequence, key off | Full sequence, key on | ... robot_2 yields | ... robot_1 yields | Equals the "named all four" grounding | Provenance off → on | Plan matches dispatch (on) |
|---|---|---|---|---|---|---|---|---|
| Recorded live first decisions (takes 1–3) | 3 | 0 | **3** | 2 (takes 1, 3) | 1 (take 2) | 3 | `vlm_verbatim` 3 → `repaired` 3 | 3 |
| Stored C (control prompt), live takes | 18 | 0 | **18** | 12 | 6 | 18 | `vlm_verbatim` 18 → `repaired` 18 | 18 |
| Stored H (held-state prompt), live takes | 18 | 0 | **17** | 10 | 7 | 17 | 17 `vlm_verbatim` + 1 `repaired` → `repaired` 18 | 17 |
| Stored C, smoke frame | 4 | 0 | 4 | 1 | 3 | 4 | `vlm_verbatim` → `repaired` | 4 |
| Stored H, smoke frame | 4 | 0 | 4 | 1 | 3 | 4 | `vlm_verbatim` → `repaired` | 4 |
| Recorded smoke (scripted, names all four) | 1 | 1 | 1 (unchanged) | 1 | 0 | 1 | `m3_default` → `m3_default` | 1 |

- **The one H answer without a full sequence** is the take-2 `reverse` (strategy reverse): its key-on outcome is identical to key off, since the hold applies to yields only.
- **Edits.** 46 of 47 key-on plans carry exactly 2 edits, `substitute` robot_3 and robot_4 to `cross`, both prefixed `queued crosser hold:`. Of these, 28 pairs replaced `continue` and 18 replaced `wait`. The `reverse` answer keeps its one pre-existing edit.
- **No refusals.** No hold was withheld (0 of 47), and no grounding refusal occurred.

**Per stimulus, stored answers (key on), yielder:**

| Stimulus | C: robot_2 / robot_1 | H: robot_2 / robot_1 / reverse |
|---|---|---|
| take 1 (`cvD_t01_a1`) | 6 / 0 | 4 / 2 / 0 |
| take 2 (`cvD_t02_a1`) | 2 / 4 | 1 / 4 / 1 |
| take 3 (`cvD_t03_a1`) | 4 / 2 | 5 / 1 / 0 |
| smoke frame | 1 / 3 | 1 / 3 / 0 |

**Field-by-field comparison with the smoke's dispatched command.** Compared fields: robots, action per robot, `linked_position`, wait durations, yielder, the yield's parameter key set, crossing order, passer, backup, park coordinate, lateral, `hold_sec`, `passer_clear_m`, `crossing_clear_m` and `expected_resolution_time_sec`.

- **robot_2 yields, on the smoke frame (2 answers): no difference at all.**
- **robot_2 yields, on the take frames (24 answers, including takes 1 and 3).** The same robots, actions, linked waits (robot_1 → 0, robot_3 → 1, robot_4 → 2), crossing order, passer, park coordinate 1.124, lateral 0.36, `hold_sec` 137.9, wait 367.7 s, resolution 459.6 s and parameter keys. Only the three pose-dependent distances differ:
  - `backup_distance_m`: take 1 0.903, take 3 0.88, smoke 1.003;
  - `passer_clear_m` / `crossing_clear_m[0]`: 1.898 / 1.807 against 1.971;
  - `crossing_clear_m[1:]` for robot_3 / robot_4: 3.683–3.684 / 4.256 against 3.683 / 4.256 (equal within 1 mm).
  These come from each frame's own standoff poses, which the smoke's decision would also have been sized from.
- **robot_1 yields (20 answers).** Mirrored roles: yield robot_1, park −1.124, crossing order [robot_2, robot_3, robot_4], wait 360.0 s, hold 135.0, resolution 450.0. The `crossing_clear_m` for robot_3 / robot_4 is 1.435 / 2.008 against 3.683 / 4.256.
  - Those clearances are measured from each queued robot's position to the west park point. But the queued robots stand west of the gate on the yielder's side and must drive east, so the values do not describe their crossing.
  - The same values come out for a decision that names all four with robot_1 yielding (equality column). So this is existing multi-passer sizing, not the hold.
  - It is the structure the scene file says latches: robot_2 is escorted west toward robot_3 and robot_4 waiting at x ≈ −1.9 and −2.5.
  - **M4 exemption check (verified from code, not run).** On take 2's frame, robot_2's escort is 1.904 m west from x = 0.130, ending at x ≈ −1.774, about 0.135 m short of the held robot_3 at x = −1.909. With the key on, robot_3 is a member of the yield command. M4's clearing exemption (`swarm_execution/safety.py`, `CoordinationTracker.exemption` → `admitted_partners`) pairs only the clearing robot, the yielder, with its partners. The escorted passer's action is a linked `temporary_wait`, which is not a clearing action, so the robot_2–robot_3 pair keeps the full 0.45 m latch, as with the key off. Inferred outcome: robot_2's escort latches about 0.45 m from robot_3, the censored-alternative latch, not a contact.
  - **What does change on this branch (verified from code).** While the yielder robot_1 backs up, it is exempt against every member of its command (`backing_up=True`), which now includes robot_3 and robot_4. Its park point at −1.124 leaves 0.785 m along x to robot_3, plus a 0.36 m lateral pull-off, so the 0.45 m latch would not have fired anyway. The `hard_contact_floor_m` backstop still applies. With the key off, robot_3 was outside the command and protected throughout.

### 5.2 Later Triggers

| Bundle | Later decisions | Key-off reproduces recorded dispatch | Key on identical to key off |
|---|---|---|---|
| `cvD_t01_a1` | 11 | 11 | 11 |
| `cvD_t02_a1` | 11 | 11 | 11 |
| `cvD_t03_a1` | 11 | 11 | 11 |

All 33 ground to `temporary_wait` (refusals and no-template waits) both ways, byte for byte, including plan provenance and edits. The refused yields stay refused for the same reasons, the corridor same-side check and the first-passer check; the hold only acts on a yield that grounds.

**Limit.** These snapshots come from takes in which robot_3 and robot_4 were never held, so they show the post-latch states of the uncorrected takes. With the key on, a live retake's later triggers would see different states (for example, the queued robots still waiting under the first command), which no recorded snapshot covers.

### 5.3 Other Scenarios

| Scenario (bundles) | Decisions replayed | Grounding mode | Key on identical to key off | Key-off reproduces recorded dispatch |
|---|---|---|---|---|
| Head-on `hoD_t01_a1` | 2 | derived | 2 | 1 |
| Intersection `ibD_t01_a2` … `ibD_t05_a1` | 5 (4 artifacts with no congestion decision skipped) | derived | 5 | 5 |
| Five-robot `m5D_t01_a1` | 8 | derived | 8 | 6 |

- **Nothing changes.** All three scenarios ground in derived mode, and the intersection also declares `arms`. The key is a no-op there by construction (section 2.3).
- **Five-robot needs no extra scoping.** The legacy-only, single-corridor scope already excludes it.
- **The 3 non-reproduced recorded dispatches** (1 head-on, 2 five-robot) are a replay limitation unrelated to the key: the recorded stage-2 retreat choice and M5's task-intent lookups are not fed offline. Both arms of the comparison run the same offline pipeline.

---

## 6. What Offline Replay Shows and Does Not Show; Per-Take Estimate

**Shows (verified).** Which commands M5 would dispatch for each recorded decision with the key on:

- the robots, roles, linked positions, crossing order and gate parameters;
- the plan provenance;
- that nothing else changes.

**Does not show.** That the scene resolves live: M4 execution, Nav2 and the timing after the 120 s release are not exercised. The robot_2 variant has resolved once (smoke, n = 1, not owner-accepted). The robot_1 variant is expected to latch even with the queued robots held: the scene file names it as the censored alternative, and live take 2 showed robot_2 escorted west into the queued robots.

**Per-take estimate (inferred).**

- The retake's first decision would be grounded as a full sequence in essentially every yield answer (46 of 46 yields here).
- **Whether it resolves depends on the model's yielder.**
  - With the control prompt, which the current kit runs: robot_2 in 12 of 18 stored answers (Wilson 95 % CI about 44–84 %), and in 2 of 3 live first decisions.
  - With the held-state prompt: 10 of 18.
- The share varies by take frame: 6/6, 2/6 and 4/6. Take 2's frame, with robot_2 at 0.13 m and a 0.26 m pair gap, draws robot_1 more often.
- **Realistic per-take chance of a resolving sequence:** about 2/3, times the live success rate of the robot_2 four-robot sequence. That rate is unmeasured (1 of 1 in the smoke), so a retake is a coin with roughly two-to-one odds of reaching the smoke-shaped command, not a guaranteed resolution.

---

## 7. What the Convoy Kit Needs for a Live Retake (Described Only; No Kit or Delta Modified)

- **Overlay.** A new delta directory, for example `runtime_delta_cvhold/`, whose `overlay_fragment.yaml` holds the single line:

  ```yaml
  grounding_hold_queued_crossers: true
  ```

  The `cv` profile's `DELTA_SUBDIR` would point at it. The base overlay `cvl_l2on.yaml` (`7e3ab552`) and `config/grounding/cvl_convoy_legacy.yaml` stay byte-identical. Keep `prompt_held_robot_state` off unless the owner wants both conditions; the estimate above is for off.
- **Runtime delta (`delta_files.tsv`).** Seven files. Kinds follow the existing convention: `reasoning/` files are `live` (assumed for `reasoning/rag/`, the same mount as `reasoning/vlm/`).

  | File | md5 | Kind |
  |---|---|---|
  | `reasoning/rag/command_grounder.py` | `691d1730dfa141149284c9eaae44b608` | live |
  | `reasoning/rag/scene_geometry.py` | `eda27ce7525e2bbb8f5fbe2bf854d296` | live |
  | `reasoning/vlm/models.py` | `52cba14c5f94b50567f1766cbcd4ff17` | live |
  | `reasoning/vlm/prompt_builder.py` | `f2f33b778360c5a0f4a6cd82b10c42b5` | live |
  | `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` | `575e7abb577650108a54e552623c9d80` | pkg:swarm_orchestrator |
  | `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | `ad9a46c65dc95e6b968e976d25c0ac8d` | pkg:swarm_orchestrator |
  | `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` | `76185f21e84a6c1ab43a3d3789291813` | pkg:swarm_orchestrator |

  - The two `reasoning/vlm` files are at the `2f83faf` md5s. With their keys off they render every prompt byte-identically (prompt-check report section 5).
  - The delta needs a new `DELTA_ID`.
- **Arm check (`arm_expect.tsv`).** Keep the four inert rows and add:

  ```text
  c.grounding_hold_queued_crossers	True
  c.prompt_held_robot_state	False
  ```

  The registered `want_arm` is unchanged, because the grounding path and mode stay `config/grounding/cvl_convoy_legacy.yaml legacy`.
- **Condition gate (`cond_dmc.py` plus the `cv` `scenario.json`):**
  - Replace `m5_line_absent:plan order condition` with `m5_line:` and the exact startup line in section 4.
  - On the **first** decision artifact by scene stamp, check:
    - `grounding_mode == "legacy"`;
    - either `grounding_queued_crossers_added == ["robot_3", "robot_4"]` with both `crossing_order=augmented:` tags in `grounding_degradations`, or the key absent and `decision.involved_robots` naming all four;
    - `dispatched_robot_ids` covers all four robots;
    - for provenance, require the `queued crosser hold:` edits when the plan gave a queued robot anything but `cross`. Do not require "not `vlm_verbatim`" outright: a plan that already said `cross` for the queued robots stays `vlm_verbatim` while the grounder still added them to the command (section 3). The gate and the classifier should key on `grounding_queued_crossers_added`, not on provenance.
  - Later artifacts carry no requirement: refusals ground as before.
- **Horizon.** 260 sim-s (`cv/spec/profile_dmc.sh`). The smoke's arrivals were 59.1–163.9 s after its t0 (campaign report 5.3), so the sequence fits. Inferred, since the smoke was a different episode.
- **Take classifier and labels.** A resolved take with added robots must not be labelled VLM-driven. Suggested label: "Resolved — grounder held the queued robots; model chose strategy and yielder". The rule can be keyed on the first artifact's `grounding_queued_crossers_added` plus the `queued crosser hold:` edit prefix. The caption should state that robot_3 and robot_4's roles came from M3, not from the model. A take where the model named all four itself (key absent) would be classified by the existing rules.
- **Registration.** As the campaign report section 5.5 notes, this changes the registered convoy experiment's Arm A only through an amendment. Nothing in v7f was touched.

---

## 8. Verified and Inferred

| Claim | Status |
|---|---|
| With the key on, a pair yield in the recorded convoy frames grounds into yield plus linked waits for all three others, with all three in the crossing order, for either yielder | verified (unit tests; replay 46/46 yields) |
| The held command equals the command of a decision naming all four, except for the trace key and tags | verified (unit tests; replay 46/46) |
| With the key off, every command, plan verdict and artifact is byte-identical | verified (unit tests; later and other replays identical; full suite failing set identical) |
| Later convoy triggers are unchanged | verified (33/33) |
| Head-on, intersection and five-robot are unchanged | verified (15/15, derived mode, so a no-op by construction) |
| Provenance reads `repaired` with prefixed edits when the model left the queued robots out | verified (46/46 plans) |
| The robot_2 sequence resolves live | inferred (smoke n = 1) |
| The robot_1 sequence latches | inferred (scene file; live take 2 dynamics) |
| About 2/3 per-take chance of reaching the resolving structure | inferred (12/18 control answers choose robot_2) |
| The escorted passer is not latch-exempt against a held queued robot (robot_1-yields branch) | verified from code (`admitted_partners`); the resulting latch is inferred |
| Held/start-pending state is not available to M3 | verified (code: `snapshot_frame_from_request`, request field only under the prompt key) |

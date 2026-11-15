# Plan-Dispatch Mismatch Visibility

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: the owner-approved option 1 (logging and provenance only) behind `plan_dispatch_mismatch_visibility`. Covers the mismatch definition, the provenance decision with a reader audit, tests, the offline recomputation over the recorded decisions, the leg-status and prompt-feedback issue, and what a kit needs to enable the key.

---

## Scope

- **Defect source.** `vgu-vlm-swarm-v7j/docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md` (branch `demo/campaign-kits`, `b70d925`), Part A.
- **Owner decision (2026-11-15).** "Plan-dispatch mismatch: option 1, logging and provenance correction only. No prompt or grounding changes." The standing constraints apply:
  - every change is isolated and default-off until validated, and fully traceable;
  - recorded artifacts are never rewritten; corrected counts are a separate recomputation.
- **Branch.** `fix/plan-dispatch-mismatch-visibility`, cut from `8933863`: the VM pin `68e67b5` plus the safety-exemption fix, which touches M4 only. Between `68e67b5` and `8933863`, `reasoning/` and `swarm_orchestrator` are unchanged. Nothing from other fix branches is merged in.
- **Evidence grades.** "Verified" means unit-tested or recomputed from recorded artifacts here. "Inferred" means reasoned from code. No VM, gcloud or API call was made, and nothing was pushed.

---

## 1. The Defect at This Base

The Part A references point at the `a412949` tree. At `8933863` the same code is at these places:

| Fact | Location at `8933863` |
|---|---|
| The `reverse` and `reroute` legacy templates act on `resolve_robot_order(decision)`, which is `involved_robots` for every strategy other than `yield`. The plan is not read. | `reasoning/rag/command_grounder.py:139` (`resolve_robot_order`), `:1097-1152` (`reverse`), `:1154-1170` (`reroute`) |
| The verifier leaves `reverse` unconstrained, and its verdict is `vlm_verbatim`. | `command_grounder.py:3441` (`_is_consistent`), `:5012` |
| `dispatch_matches_plan` is computed after grounding as per-robot equality, with no tag and no log line. | `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py:1759-1761`; `command_grounder.py:5051` (`project_dispatched_legs`), `:5104` (`plan_matches_dispatch`) |
| `agreement` counts a verbatim plan whatever was dispatched. | `reasoning/rag/plan_metrics.py:160` |
| M5 marks a leg from the robot's command status, whatever action ran. | `orchestrator_node.py:920-951` (`_apply_plan_leg_status`) |
| Leg statuses feed the prompt-v3 plan-state block and the hold rule. | `reasoning/vlm/prompt_builder.py:307-326, 635`; `plan_tracker.py:160` (`_is_hold`); `orchestrator_node.py:1145` |

---

## 2. Definition: "Dispatch Differs From the Plan"

The pure function is `classify_plan_dispatch` in `reasoning/rag/plan_dispatch_mismatch.py`. Its inputs are:

- this decision's verified legs, the same legs `dispatch_matches_plan` uses;
- the command M5 actually fans out, after the task-registry filter;
- the withheld reason and the robots the registry filter dropped;
- for a `junction_clear` sequence, every phase.

**Per-robot kinds.** Both sides are reduced to one kind per robot:

- The dispatched kind is `project_dispatched_legs`, the existing projection, with one refinement: the passer of a `yield` with `passer_escort_distance_m > 0` is `escort`.
- A withheld decision dispatches `continue` (nothing) to every robot.
- A robot the task-registry filter dropped gets `continue`.

**Classes.** Each kind belongs to one class:

- motion: `reverse`, `yield`, `reroute`;
- pass: `cross`, `escort`;
- hold: `wait`;
- none: `continue`.

An `escort` carries out a `cross` leg. Every other pair must be equal.

| Kind | When | Example (verified, fixture) |
|---|---|---|
| `unplanned_motion` | A motion command, or an escort, that the leg did not ask for | m5V `95066420`: robot_5 planned `continue`, dispatched `reverse` |
| `motion_differs` | The leg asked for one motion and got another | synthetic only |
| `planned_motion_not_sent` | The leg asked for a motion and got none. The reason is given. | m5V `b07a700f`: robot_4 planned `reverse`, got nothing, reason `grounding=node_handoff:robot_1->robot_4`. E16 `df2ed72f`: robot_3/robot_4 planned `reroute`, got 15 s waits, reason `template:reroute_waits_the_other_involved_robots` |
| `hold_differs` | Any other difference between pass, hold and none | cv `759bdb94`: robot_3/robot_4 planned `wait`, never commanded |
| `yielder_differs` / `passer_differs` | The set of yield robots or passing robots differs (summary items) | synthetic; also the `junction_clear` yielder gap |
| `order_differs` | A yield's `crossing_order` differs from the order of the plan's `cross` legs, or a `junction_clear` recede order falls outside the chi-epsilon class | batch2: 1 yield |

**Reasons.** Each item carries the evidence for it, taken from the command and not guessed:

- `withheld:<reason>` or `registry_dropped`;
- the degradation tags that name the robot (`node_handoff` counts only for the occupant on the right-hand side);
- a substituted wait's own `reason`, plus the strategy's refusal tags;
- the template rule, for example `template:reverse_acts_on_involved_robots` or `template:reroute_acts_on_first_involved_robot`;
- `unattributed` when nothing names a cause.

**Excluded as registered artefacts** (recorded in `excluded`, not counted as a mismatch):

- A retreat-shield wait on a robot whose leg is `continue`. This is the registered A27(iv) reading (`plan_metrics.shield_excluded_dispatch_match`).
- A `junction_clear` recede order that differs from the plan's within the chi-epsilon equivalence class (`order_equivalent`, ruled 2026-10-03).

### 2.1 The Seven "Yield With No Motion Involved" Decisions

Recomputed from the artifacts (verified):

| Decision | What differs | Verdict |
|---|---|---|
| m5D `03bba450`, m5D `a15f3fc5`, E20 `c18ade97`, E20 `f269ab37`, E21 `04457772`, E28 `3c234140` | Only retreat-shield waits (`grounding=retreat_shield:<id>`) on robots whose leg is `continue`. Yielder, passer, escort and crossing order all match the plan. | **Comparison artefact.** The registered A27(iv) reading already excludes shielded robots. The plan grammar has no vocabulary for an M3 safety hold, and the shield does not change the resolution. These stay `vlm_verbatim`. |
| cv `759bdb94` (convoy take 2) | robot_3 and robot_4 have plan legs `wait`, but the yield command never addressed them (no tag, no shield). | **True mismatch** (`hold_differs`). The plan said hold, and the robots were left under Nav2. The campaign report already describes these as "the two queued robots, never commanded". Recorded as overridden. |

So the report's 15 silent decisions split as follows. 8 are true motion mismatches (5 `reverse`, 3 `reroute`), 1 is a true hold mismatch (`759bdb94`), and 6 are shield artefacts.

---

## 3. Provenance Decision and Reader Audit

**Decision: a companion field. `plan.provenance` is never changed.** The new block is a top-level artifact key `plan_dispatch_mismatch`, written only with the key on. It carries:

- `provenance` (a copy of the recorded value);
- `provenance_dispatched`: `overridden` for a `vlm_verbatim` plan whose dispatch differs, otherwise the recorded value;
- `verbatim_dispatched`;
- `matches`, `kinds`, `robots`, `items`, `excluded` and `tags`;
- the per-robot `planned` and `dispatched` kinds, `withheld` and `per_robot_equal`;
- `leg_status`.

A new enum value was rejected because pinned readers would break or silently change meaning:

| Reader | Uses `provenance` how | With the key on it sees |
|---|---|---|
| `reasoning_pipeline.py:1709-1711` (`model_when_verified`) | `== "vlm_verbatim"` gates the junction dispatch order. This is behaviour. | Unchanged. A new value would have changed dispatch. |
| `plan_tracker.TrackedPlan.provenance`, `PlanDispatchInfo.provenance` (typed `PlanProvenance`) | Literal validation | Unchanged |
| `plan_metrics.score_plan_decision` / `score_decision_artifact` | `agreement`, `edit_distance`, `verbatim_dispatch_matched`; rebuilds `VerifiedPlan` from the block | Unchanged, byte-identical (test `test_registered_metric_is_identical_with_key_on_and_off`). The corrected reading is the new `score_dispatch_agreement`. |
| `plan_metrics.tabulate_provenance_by_strategy_correctness` | `row[item.provenance] += 1` over fixed columns | Unchanged. A new value would raise `KeyError`. |
| `benchmarks/s1_scoring/conflicts.py:358` (registered A33 scorer, `provenance_counts`) | Counter of the values | Unchanged |
| `scripts/s1b_live_batch_stats.py`, `scripts/plan_parity_mc_replay.py`, `scripts/coverage_scene_scores.py`, `scripts/junction_clear_repair_bound_sweep.py`, `scripts/strategy_regret.py` | Counts over the three values, or `vlm_verbatim` checks | Unchanged. Their "verbatim AND dispatch_matched" readings still use the recorded `dispatch_matches_plan`. With the key on, the corrected count is `plan_dispatch_mismatch.verbatim_dispatched`. |
| Demo campaign `take_class_dmc.py` (md5 `cb70f53e…`, identical in all 8 kit copies under `v7j/…/demo_campaign`) | `plan.provenance == "vlm_verbatim"` for `junction_clear`, plus its own log-based leg check | Unchanged. Its log-based yielder and recede check is already stricter than `dispatch_matches_plan`. |
| Unit tests pinning `provenance` (`test_plan_metrics.py`, `test_plan_verifier.py`, `test_m5_reasoning_pipeline.py` and others) | Exact values | Unchanged |

**Agreement metric**, both definitions:

- **Original (registered, unchanged):** `agreement = consistent AND provenance == vlm_verbatim` (`plan_metrics.py:160`).
- **Corrected (key on, from the block):** `agreement_dispatched = agreement AND plan_dispatch_mismatch.matches`, and `verbatim_dispatched = vlm_verbatim AND matches` (`plan_metrics.score_dispatch_agreement`). It returns None for an artifact without the block, so key-off metrics are byte-identical.

---

## 4. The Key and What It Changes

The key is `plan_dispatch_mismatch_visibility` in the orchestrator config. It defaults to `false` and is named beside `plan_dispatch_order_source`. M5 refuses to start with it on and `plan_channel_enabled` off.

**With the key on**, for every plan-channel decision (verified by the node tests):

1. **Artifact.** The decision gains the `plan_dispatch_mismatch` block (section 3). A `reverse` decision also gains a `reverse_dispatch` block with `status` (`executed`, `refused` or `withheld`), `reversed_robot_ids`, `waiting_robot_ids`, `reason` and `dispatched`.
2. **Tags.** Each item gives a `plan=overridden:<strategy>:<robot|yielder|passer|order>:<planned>-><dispatched>` tag. The key is registered in `command_grounder.DEGRADATION_TAGS` (cause `None`).
   - The tags are recorded only in the block, never in the command's `degradations`.
   - That list feeds `AttemptMemory.record` and so the failure-explanation line of later prompts (`orchestrator_node.py:1505`, `reasoning_pipeline.py:580-618`).
3. **WARN line.** M5 logs one WARN line per item, at dispatch:

   ```text
   plan dispatch mismatch request=<id> strategy=<s> robot=<r> planned=<a> dispatched=<b> kind=<k> plan_id=<n> reason=<evidence>
   ```

   - `reason` is last because it can contain spaces.
   - A withheld decision gives one summary line instead (`robot=<ids> planned=<r:a,...> dispatched=none kind=withheld reason=withheld:<reason>`), since M5 already logs `refusal withheld`.
4. **Reverse trace.** A reader of `m5.log` alone can now tell an executed reverse from a refused one. Both use the same `<request_id>-reverse` command id.

   ```text
   reverse executed request=<id> robots=<ids> dispatched=reverse
   reverse refused request=<id> robots=<ids> dispatched=temporary_wait reason=<refusal reason>
   ```

   - The refusal is read from the substituted waits' `requested_strategy: reverse` and `reason`, plus the refusal tags. Cv `6a05a618` shows the refusal can carry no tag at all.
   - `reason` was moved last for the same reason as above. The order the task proposed was `robots, reason, dispatched`.
5. **Leg-status record.** A node-side ledger records what each dispatch did to each accepted-plan leg: `as_planned`, `overridden` (ran a different action) or `not_sent` (a pending leg whose action was never dispatched, with the reason).
   - Each artifact's `leg_status` lists each leg's tracker `status` beside `effective_status`, `ran`, `reason` and the request that caused it.
   - When M4 completes or fails an overridden leg, M5 logs `plan leg status plan_id=… robot=… leg=wait recorded=done effective=overridden ran=reverse request=…`.
6. **Startup line.** The `grounding mode=…` line gains the suffix ` plan_dispatch_mismatch_visibility=true`, only when the key is on.

**Not changed, key on or off:**

- **Prompts:** no template, plan-state or failure-context change.
- **Grounding:** the `reverse` and `reroute` templates are untouched.
- **Dispatch:** published commands are byte-identical to the key-off ones and to base (section 5).
- **Plan verification and provenance.**
- **The `PlanTracker`:** leg statuses, holds and plan ids.
- **Every registered metric.**

**Key off:** artifacts, log lines and published commands are byte-identical to `8933863`. This is verified by a cross-tree run in section 5.

### 4.1 Leg Status and Prompt Feedback: Remaining Known Issue

Correcting the tracker's leg status would change model input, so it was not done.

- **What the statuses feed.** `PlanTracker` statuses are rendered into the prompt-v3 plan-state block (`prompt_builder.py:307-326`, "- robot_1: wait (done)"). They also decide the hold rule (`_is_hold` drops `done` legs), and through that the plan ids attached to dispatched commands.
- **What would change.** Marking `95066420`'s predecessor legs `overridden` or `not_sent` in the tracker would change:
  - the text of later prompts (new status words in the plan-state block);
  - hold-versus-replan outcomes;
  - plan ids.
- **What was done instead.** As instructed, the correction exists only in the artifact's `leg_status` record and the log. The tracker and everything it feeds are untouched (test `test_key_on_leaves_tracker_statuses_and_prompt_plan_state_unchanged`).
- **Still open for the owner.** The model is still shown "robot_1: wait (done)" when robot_1 backed out 1.3 m, and "robot_4: reverse (pending)" for a reverse M5 never sent. Fixing what the model sees needs a prompt-input change, which the owner excluded.

---

## 5. Tests and Identity Checks

**New tests: 46** (all verified passing):

- `tests/unit/test_plan_dispatch_mismatch.py` (26, parametrised cases counted). The pure function on every kind; the recorded `95066420`, `b07a700f`, `df2ed72f`, `03bba450`, `759bdb94` and `6a05a618`; the withheld and registry-drop cases; yielder, passer and order; the junction epsilon and yielder gap; `leg_effects`; `reverse_dispatch`; tag registration.
- `tests/unit/test_m5_node_plan_dispatch_visibility.py` (20, parametrised cases counted). Real `OrchestratorNode._handle_outcome` with the real `PlanTracker`, replaying the m5V chain `b07a700f` → statuses → `95066420`, and cv `6a05a618`. It covers:
  - the default, the validator and the startup suffix;
  - the companion provenance, tags and WARN line;
  - `not_sent` and `overridden` leg records and the `plan leg status` line;
  - the reverse executed and refused lines;
  - corrected agreement, with the registered metric identical on and off;
  - tracker and plan-state identity on and off;
  - published-command identity on and off;
  - "the artifact only adds the two keys" and "the log only adds the new lines";
  - explicit off equal to an absent key;
  - a failing check never blocks dispatch;
  - the withheld summary line.
- **Fixtures.** `tests/unit/data/plan_dispatch_mismatch/*.json` are minimal copies of six recorded artifacts. Each names its source bundle in `_fixture_source`. The bundles were only read.

**Cross-tree identity (verified).** A deterministic replay (uuid and order seed pinned) of the six fixtures through the node, with the key off, was run in the base tree (`8933863`, a detached scratch worktree) and in this branch.

- The 6 artifacts, 25 log lines and 16 published messages are byte-identical.
- With the key on, the 16 published messages are still byte-identical to base.
- The log differs only by the startup suffix and the new lines.

**Targeted existing suites (verified).** `test_m5_reasoning_pipeline`, `test_m5_node_probe`, `test_m5_node_plan_channel`, `test_plan_metrics`, `test_command_grounder_derived`, `test_apparatus_overlay`, `test_dispatch_order_source`, `test_m5_node_junction_clear`, `test_a27_shield_fix` and `test_m5_plan_tracker`: 455 pass and 1 fails.

- The failure is `test_write_decision_artifact_preserves_m2_result_on_grounding_failure`.
- It fails identically at `8933863`: a free-text `strategy` fails `CongestionDecision` validation. It predates this branch.

**Full unit suite.** See the hand-back. It was gated on the Mac's swap headroom.

---

## 6. Offline Recomputation (Read-Only)

**Script.** `scripts/plan_dispatch_mismatch_recompute.py` processes one bundle at a time and writes a separate JSON table. No recorded artifact is modified.

**Bundles.**

- Campaign: `v7j/…/demo_campaign/{ib,cv,ho,m5,m5v,cvh}/runs/*`.
- October: `v3/data/logs/vm_runs/**`.
- `_backup_*` paths are skipped.
- A campaign bundle is read only with `RESTORE OK` in `RESTORE.txt` and no `run_dmc.sh` running. At scan time none was running, and every campaign bundle with decisions had finished. `cvH_t04_a1`, a bring-up abort, has no plan-carrying decisions.

**Rules.**

- Deduplicated by `request_id`, campaign first (0 duplicates).
- Verified legs:
  - a non-held block's legs;
  - on a hold, the non-done legs plus, for verbatim decisions, the done robots' own proposed legs;
  - for a held non-verbatim decision with a recorded match, the projected dispatch.
- **Fidelity gate.** For every comparable decision without a phase sequence, `per_robot_equal` must equal the recorded `dispatch_matches_plan`: **0 failures** over all rows (verified).
- 2 `step7b_prefix_rescue` artifacts predate the recorded `dispatched_command` and are not comparable.

### 6.1 Per Series (Verified)

The columns are:

- **plans:** decisions with a plan block.
- **vb rec:** recorded `vlm_verbatim`.
- **vb ∧ rec match:** verbatim AND the recorded `dispatch_matches_plan`, the raw reading.
- **vb corrected:** verbatim AND this definition matches (shield and epsilon exclusions applied). This is the key-on `verbatim_dispatched`.
- **vb motion-only:** verbatim with no motion-kind item, for comparison.
- **mism:** decisions with at least one item, among comparable decisions.
- **Mismatch decisions by strategy:kind:** decision counts per strategy and kind. A decision with two kinds counts under both; `junction_clear N` sums that strategy's kinds.

| Series | Bundles | Plans | vb rec | vb ∧ rec match | **vb corrected** | vb motion-only | Mism | Mismatch decisions by strategy:kind |
|---|---|---|---|---|---|---|---|---|
| campaign/ib | 5 | 5 | 1 | 1 | **1** | 1 | 0 | — |
| campaign/cv | 3 | 36 | 3 | 2 | **2** | 3 | 11 | junction_clear:planned_motion_not_sent 9, reverse:hold_differs 1, yield:hold_differs 1 |
| campaign/m5 | 1 | 8 | 2 | 0 | **2** | 2 | 6 | yield:hold_differs 4, junction_clear:hold_differs 2, junction_clear:planned_motion_not_sent 1 |
| campaign/m5v (validation) | 1 | 9 | 1 | 0 | **0** | 0 | 9 | reverse:unplanned_motion 2, reverse:planned_motion_not_sent 2, reverse:hold_differs 1, yield:hold_differs 4, junction_clear:hold_differs 1 |
| campaign/cvh (convoy takes 4–5, new) | 2 | 12 | 0 | 0 | **0** | 0 | 3 | reverse:planned_motion_not_sent 1, reverse:hold_differs 1, junction_clear:hold_differs 1 |
| october/s1b_pilot | 3 | 16 | 0 | 0 | 0 | 0 | 15 | yield:hold_differs 15 |
| october/s1b_pilot2 | 2 | 16 | 0 | 0 | 0 | 0 | 7 | yield:hold_differs 7 |
| october/churn_wave | 2 | 8 | 1 | 1 | **1** | 1 | 5 | yield:hold_differs 4, junction_clear 2 |
| october/live_batch | 3 | 10 | 3 | 2 | **2** | 2 | 7 | reverse:planned_motion_not_sent 1, yield:hold_differs 3, junction_clear 4 |
| october/resume | 2 | 13 | 2 | 1 | **1** | 1 | 8 | reverse:unplanned_motion 1, yield:hold_differs 6, junction_clear:hold_differs 1 |
| october/batch2 | 6 | 33 | 10 | 5 | **5** | 5 | 21 | reverse:unplanned_motion 2, reverse:planned_motion_not_sent 4, reverse:hold_differs 2, reroute:planned_motion_not_sent 2, reroute:unplanned_motion 1, yield:hold_differs 2, yield:order_differs 1, junction_clear 18 |
| october/batch3 | 3 | 21 | 6 | 3 | **5** | 5 | 12 | yield:hold_differs 3, junction_clear 13 |
| october/batch4 | 3 | 13 | 3 | 1 | **2** | 2 | 8 | yield:hold_differs 3, junction_clear 9 |
| october/batch5 | 3 | 16 | 2 | 1 | **1** | 1 | 9 | reverse:planned_motion_not_sent 2, yield:hold_differs 2, junction_clear 9 |
| **october/batch6: prereg-v3 tranche 1 (registered, kept separate)** | 5 | 26 | 2 | 0 | **1** | 1 | 14 | yield:hold_differs 11, yield:planned_motion_not_sent 3, reroute:planned_motion_not_sent 1, reroute:unplanned_motion 1, junction_clear 3 |
| october/ib10_closure | 5 | 5 | 5 | 5 | **5** | 5 | 0 | — |
| october/ib10_remedy | 8 | 8 | 8 | 8 | **8** | 8 | 0 | — |
| october/v3_step0 | 2 | 2 | 2 | 2 | **2** | 2 | 0 | — |
| october/step7b_prefix_rescue | 2 | 2 | 0 comparable (2 verbatim not comparable) | — | — | — | — | — |
| october/env_audit | 2 | 8 | 0 | 0 | 0 | 0 | 8 | yield:hold_differs 8 |
| october/s1_resume | 2 | 51 | 0 | 0 | 0 | 0 | 5 | yield:hold_differs 5 |
| october/s1a_anchor | 3 | 26 | 0 | 0 | 0 | 0 | 12 | yield:hold_differs 11, yield:unplanned_motion 1 |

**Reading the table.**

- Most `hold_differs` and `junction_clear` items are withheld refusals. 398 of 468 robot-items (all series, `cvh` included) carry `withheld:` reasons. The plan was never dispatched to anyone, and M5 already logs `refusal withheld`.
- The prereg-v3 tranche-1 row is a recomputation beside the registered results, not a rescore of them. Its corrected verbatim count is 1 of 2 (E28 `64d5ef0a` `reroute` is overridden; E28 `3c234140` is a shield artefact).

### 6.2 Reconciliation With the Part A Numbers (Verified)

Part A's scope is the 12 pinned campaign bundles plus v3 (`cvh` excluded). It compared the model's `proposed_plan` legs.

- **10 of 33 reverse legs: reproduced.** 15 dispatched commands with a reverse action and a model plan, 33 reverse legs, 10 to robots whose proposed leg was not `reverse` (5 `wait`, 4 `cross`, 1 `continue`), in 7 commands.
  - Against the verified legs (this definition) the count is 8 legs.
  - E13 `652ac9ac` robot_5 and E17 `150b95a6` robot_3 had their proposed `cross` legs repaired, and the repaired leg matches the dispatch.
  - m5V `b07a700f` robot_1 and robot_2 stay overridden: repaired to `wait`, but reversed.
- **3 of 3 reroutes: reproduced.** `8e1e9b74`, `df2ed72f` and `64d5ef0a` all mismatch.
- **15 silent decisions: reproduced.** These are `vlm_verbatim` with recorded `dispatch_matches_plan=false`, outside `junction_clear`: 5 `reverse`, 3 `reroute`, 7 `yield`. Under this definition:
  - **9 are overridden:** the 5 reverse, the 3 reroute, and cv `759bdb94`;
  - **6 stay verbatim** (shield artefacts, section 2.1).
  - The 4 silent `junction_clear` decisions (`0f26edcc`, `73e4445c`, `0c4ad5c8`, `35a161ad`) were all withheld. They are overridden with reason `withheld:refusal_no_action`.

### 6.3 Effect on the Demo Campaign's "6 Accepted Plans" (Verified)

| Reading | ib | cv | m5 | Total (cvh adds 0) |
|---|---|---|---|---|
| Recorded `vlm_verbatim` (the campaign figure) | 1 | 3 | 2 | **6** |
| Raw: verbatim AND recorded `dispatch_matches_plan` | 1 | 2 | 0 | 3 |
| Registered A27(iv): shield-excluded | 1 | 2 | 2 | 5 |
| **This definition (key-on `verbatim_dispatched`)** | 1 | 2 | 2 | **5** |
| Motion-only | 1 | 3 | 2 | 6 |

- Under this definition the figure becomes **5**. Convoy take 2's `759bdb94` drops out: its plan held the two queued robots, and dispatch never commanded them.
- The five-robot "2 of 8, both executed as named" stands (shield artefacts only).
- The intersection take-5 plan is unaffected.
- The recorded `plan.provenance` values and the campaign report are not edited.

---

## 7. What a Kit Needs to Enable It

1. **Overlay key.** Set `plan_dispatch_mismatch_visibility: true` in the orchestrator overlay fragment, with `plan_channel_enabled: true`. M5 refuses to start otherwise.
2. **Runtime delta.** These are the files that differ from the VM pin `68e67b5`. `8933863` has the same md5s for every file below, and the kinds follow the campaign `delta_files.tsv` convention.

| relpath | md5 at pin `68e67b5` | md5 on this branch | kind |
|---|---|---|---|
| `reasoning/rag/plan_dispatch_mismatch.py` | (new) | `a610a40e4c2da8e821253b2aeb54a481` | live |
| `reasoning/rag/command_grounder.py` | `cfbd1fb882e5cf9d3b9f45c6e8f67aec` | `dca7f64b77a428bcf288fee9614db092` | live (one `DEGRADATION_TAGS` entry) |
| `reasoning/rag/plan_metrics.py` | `9d3c148705a6ebb3c2bd22ed1109ed09` | `869c29652fd907fe2c5faa47f48865a7` | live (offline scoring only) |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/plan_dispatch_visibility.py` | (new) | `90df7c3f5964f26e385f03b2b3fb834e` | pkg:swarm_orchestrator |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` | `273bbf7f7d01755226506fd892a380fa` | `dfb616700a0bd111f8acddf022ed1a69` | pkg:swarm_orchestrator |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | `e1b3b289ec05e3c21921fa0253829542` | `0dbbe019fa5a49c5329690dd88859943` | pkg:swarm_orchestrator |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` | `39a51bfc0de66a42b6f6ac4c78a60478` | `e486d69429eaef808d4afc6cbedf50eb` | pkg:swarm_orchestrator |
| `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml` | `677a4cd0b65bcd4acd974e41c961a039` | `c3d98aff9a08f3b1c284f345ad19b856` | pkg:swarm_orchestrator (comment plus `false` line) |

A kit that also carries another branch's `command_grounder.py` (for example the v7n guard tree, md5 `951c23b7…`) must merge the one `"plan=overridden": None` entry into that file rather than copy this branch's file over it.

3. **Colcon rebuild** of `swarm_orchestrator`. Its package files are installed, not live-mounted (VM harness trap: colcon-built versus live-mounted paths). The `reasoning/` files are live under `/ws`.
4. **Arm-check assertions** (the `arm_expect.tsv` form, evaluated by the deployed loader):
   - `c.plan_dispatch_mismatch_visibility` → `True` and `c.plan_channel_enabled` → `True`;
   - an md5 line per delta file;
   - plus an `m5.log` check that the `grounding mode=` startup line ends with ` plan_dispatch_mismatch_visibility=true`.

   A key-off arm must assert the suffix is absent.

---

## 8. Not Done

- No live or VM validation. The key stays default-off until a kit run validates it.
- No prompt, grounding, verifier or dispatch change, by the owner's decision. The plan is still not read for `reverse` and `reroute` (the Part A grounding fix stays unbuilt).
- The prompt still shows tracker leg statuses that can be wrong (section 4.1).
- Withheld decisions count as mismatches in `matches` (nothing was dispatched). A reader who wants only dispatched commands can filter on `withheld`.

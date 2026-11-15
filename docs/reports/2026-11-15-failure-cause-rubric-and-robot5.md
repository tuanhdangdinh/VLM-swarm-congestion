# robot_5's Unplanned Reverse, and a Failure-Cause Rubric for Five-Robot S1b

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: Part A traces why `m5V_t01_a1` decision `95066420` reversed robot_5 although the model's plan said `continue`, and counts the pattern over every recorded plan-carrying decision. Part B inventories the five-robot S1b episodes on this Mac, maps evidence to cause classes, fixes a cause-classification rubric before any case-by-case reading, and scopes a post-fix comparison. Read-only analysis: no VM, no API call, no runtime code change, no bundle edited.

---

## Scope and Evidence Rules

- **Read-only.** Every bundle was read in place. Nothing was written under any `data/logs` tree. The scans ran one bundle at a time in a single process, with their scripts and output in the session scratchpad (not kept). Section 3 states their rules so they can be rerun.
- **Code tree of the run.** `m5V_t01_a1` ran from worktree `vgu-vlm-swarm-v7n`, branch `demo/validation-guard-contacts` @ `a412949` (reasoning code last changed in `4bbe4db`; `reasoning/rag/command_grounder.py` md5 `951c23b7f2e0168dab10022abccff77a`). Every file:line in Part A is at that tree.
- **Labels.** "Verified" means read from a file or recomputed here. "Inferred" means reasoned from verified facts and not tested.
- **Bundles.**
  - Validation take: `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/m5v/runs/m5V_t01_a1/`.
  - Campaign bundles: `…/demo_campaign/{ib,cv,ho,m5,m5v}/runs/*`. `cvh/runs` is empty.
  - October bundles: `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v3/data/logs/vm_runs/`.

---

## Part A — Why robot_5 Was Reversed

### 1. The Answer

- **The answer.** The `reverse` strategy is grounded from `involved_robots`, never from the plan. The model listed robot_4 and robot_5 as involved, so the legacy reverse template, which derived mode falls through to, backed both robots out 1.3 m. The model's plan leg `robot_5: continue` was checked only by a comparison that writes `dispatch_matches_plan: false` into the artifact. That comparison has no tag, no log line and no effect on dispatch.
- **Was the model's answer consistent?** No, by the prompt's own definition: "reverse: the involved robots back straight out along their own lanes". But the contract invited the mistake. `involved_robots` is never defined. The plan grammar puts no constraint on a `reverse` plan. The prompt says the plan is verified "before anything is dispatched". The model was also told to hold an active plan that the system itself had built and mis-recorded.
- **Safety.** robot_5's reverse came within 19.1 mm of `obstacle_1`, one of the take's two near-misses. In the October and campaign bundles, 10 dispatched reverse legs went to robots whose plan said `continue`, `wait` or `cross`. One of those legs ended in a static contact and two in sub-margin grazes (section 3.3).

**Classification:** grounding design (primary: the plan is not consulted for `reverse` or `reroute`) plus contract ambiguity (contributing), with a self-inconsistent model answer under a strict reading. Two recording defects hide it: the verifier's label and the plan-leg status update. Section 4 gives the reasoning and the fix at each level.

### 2. Trace of Decision `95066420` (Verified)

#### 2.1 The Model's Raw Output and the Parsed Decision

From `decisions/95066420efa54188962f5c4f68806a4c.json`:

- **`raw_text`** (ER-2 `gemini-robotics-er-2-preview`, 1 attempt, `finish_reason=completed`, `parse_status=valid`, temperature 0.6):

```json
{
  "reasoning": "Robot 4 and Robot 5 are in a head-on deadlock within 0.37 meters of each other, each facing the other in a stopped state. We should execute the active recovery plan where Robot 4 reverses to clear the path for Robot 5.",
  "congestion_detected": true,
  "type": "deadlock",
  "involved_robots": ["robot_4", "robot_5"],
  "root_cause": "Robot 4 and Robot 5 are stopped head-on in a narrow passage.",
  "strategy": "reverse",
  "justification": "Robot 4 and Robot 5 are physically blocking each other in a head-on deadlock; Robot 4 must reverse out of the passage so that Robot 5 can continue.",
  "yield_robot": null,
  "blocker_kind": "robot",
  "crossing_order": null,
  "proposed_plan": [
    {"robot_id": "robot_4", "action": "reverse"},
    {"robot_id": "robot_5", "action": "continue"},
    {"robot_id": "robot_1", "action": "continue"},
    {"robot_id": "robot_2", "action": "continue"},
    {"robot_id": "robot_3", "action": "continue"}
  ]
}
```

- **The parsed `decision`** is identical field for field: strategy `reverse`, `involved_robots` [robot_4, robot_5], `yield_robot` null, `crossing_order` null, the same five legs. The parser nulled nothing, and `diagnostics.decision_degradations` is `[]`.
- **What was dispatched:** `dispatched_command.command_id` `95066420…-reverse`, actions robot_4 `reverse` and robot_5 `reverse`, each with `backup_distance_m` 1.3, `backup_line_hold` true, `fresh_latch_fast_fail` true and `plan_id` 2. `degradations` is `["grounding=dynamic_arms:lane:y"]`; `dispatched_robot_ids` is [robot_4, robot_5]. `m5.log` lines 731–732 show one `dispatch … robot=` line for each.

#### 2.2 Where the Plan State in the Prompt Came From (the Hold Chain)

The prompt for `95066420` contained this block (artifact `prompt.user_prompt` and `plan_state`):

```text
Active plan (plan_id=2):
- robot_4: reverse (pending)
- robot_3: reverse (done)
- robot_1: wait (done)
- robot_2: wait (done)
- robot_5: continue (pending)
Changed since the last invocation: robot_2, robot_3, robot_4
Hold this plan unless the scene has changed or a leg above is failed: ...
```

It also carried a failure context: "reverse completed 21 s ago; congestion re-detected for the same robots ... prefer a different strategy unless the scene has changed".

Plan 2 was created 19 sim-s earlier by decision `b07a700f`:

| Robot | `b07a700f` model leg | Plan 2 leg (verifier, `repaired`) | `b07a700f` dispatched | Plan 2 status when `95066420` ran |
|---|---|---|---|---|
| robot_1 | cross | wait (substituted: "cross leg has no preceding yield leg") | **reverse** | wait **done** |
| robot_2 | cross | wait (same edit) | **reverse** | wait **done** |
| robot_3 | reverse | reverse | reverse | reverse done |
| robot_4 | reverse | reverse | **nothing** | reverse **pending** |
| robot_5 | continue | continue | nothing | continue pending |

- **Why robot_4 got nothing.** `b07a700f`'s grounding tag is `grounding=node_handoff:robot_1->robot_4`. Under `reverse`, a node handoff drops the occupant from the reversing set: "only the robots that are not on the node back away from it" (`reasoning/rag/grounding_view.py:303-317`). `m5.log` lines 201–203 dispatch robot_1, robot_2 and robot_3 only.
- **Why robot_1's and robot_2's `wait` legs read `done`.** M5 maps each robot's M4 command status onto that robot's plan leg, whatever action the robot actually ran (`orchestrator_node.py:931-957`, `_apply_plan_leg_status`). robot_1 and robot_2 completed reverses, so their `wait` legs became `done`. The plan-state block therefore told the model that two robots had waited when they had backed out 1.3 m. It also listed a robot_4 reverse as pending that M5 had never sent.
- **Why `95066420` is a hold.** `_is_hold` (`plan_tracker.py:160-215`) compares the new verified legs, with the robots whose legs are `done` dropped, against the active plan's remaining legs. Both read robot_4 `reverse`, robot_5 `continue`. That is a hold (`plan.plan_held: true`, `plan_id` 2). The model's answer is the remaining-legs plan it was told to hold, plus a strategy and an involved set.

#### 2.3 The Plan Verifier's Verdict and the Dispatch Comparison

The artifact's `plan` block reads: `provenance: vlm_verbatim`, `edits: []`, `rejection_reason: null`, `plan_held: true`, `dispatch_matches_plan: false`, `order_equivalent: false`.

- **The verifier did not flag the contradiction.** `verify_and_repair_plan` (`command_grounder.py:4922-5209`) ran three checks:
  - its consistency rule `_is_consistent` returns True for `reverse` with any legs (`command_grounder.py:3597-3626`: "`reverse`, `convoy`, `priority_override` and `none` are left unconstrained because the spec is silent on them");
  - `_plan_disagrees_with_decision_fields` checks only `yield` (`command_grounder.py:3542-3594`);
  - the feasibility audit `_plan_problems` checks reverse legs only for the same-side corridor rule (`command_grounder.py:3999-4013`).

  The verdict is `vlm_verbatim` at line 5173.
- **The `false` comes from a separate comparison.** After grounding, the pipeline compares this decision's verified legs with the projection of the command actually dispatched (`reasoning_pipeline.py:1792-1794`, `plan_matches_dispatch`, `command_grounder.py:5265-5290`). robot_5's leg `continue` does not equal its dispatched `reverse`, so the result is False.
- **The `plan` block mixes two plans.** On a hold, `provenance` is this decision's verdict (`reasoning_pipeline.py:1798`). `legs` are the already-active plan 2's legs with their live statuses (`reasoning_pipeline.py:1799`; `models.py:824-831`). Plan 2 itself was born `repaired`.

#### 2.4 Which Field Drives Who Reverses

The code path is verified:

1. `InProcessPipeline` grounds the decision first (`reasoning_pipeline.py:1637-1651`, `self._ground_fn(result, …)`). The plan is verified only afterwards (lines 1671-1687).
2. `_ground_derived` (`command_grounder.py:2417`) sends every strategy other than `yield` and `junction_clear` to the legacy template (lines 2545-2551; docstring line 2431: "Non-yield strategies reuse the legacy templates").
3. `_ground_legacy` takes `robot_ids = resolve_robot_order(decision)` (line 835). For any strategy other than `yield`, that is `involved_robots` unchanged (`command_grounder.py:146-176`).
4. The `reverse` branch (`command_grounder.py:1104-1152`) gives every robot in `robot_ids` a `reverse` of `backup_distance_m` 1.3 (line 853). It applies only the same-side refusal (lines 1106-1128) and the tracked-band clamp (lines 1131-1144).
5. Before that, the dynamic-arms grounding view may shrink the set: a node handoff (`grounding_view.py:303-317`) or a rear exemption. So "every involved robot reverses" means "every robot of the view-filtered involved set". `b07a700f` involved 4 and reversed 3; `ea23b1a7` involved 5 and reversed 3.

`proposed_plan` is read nowhere on this path. This is by design: `models.py:842-849` (on `PlanDispatchInfo.dispatch_matches_plan`) says "the engine measures what the VLM proposed, it does not drive what M4 receives". The one plan-to-dispatch path, `plan_dispatch_order_source: model_when_verified`, covers only the `junction_clear` recede order (`reasoning_pipeline.py:1742-1790`), and this run had it `chi` (`plan_dispatch_order_source: chi`). The same holds for `reroute`: the legacy template reroutes `robot_ids[0]` and waits the rest (`command_grounder.py:1161-1179`), whatever the plan's `reroute` legs say.

#### 2.5 What the Prompt Contract Says Each Field Means

Prompt v3, `reasoning/vlm/prompt_builder.py`:

| Text | Line | Bearing on `95066420` |
|---|---|---|
| `"involved_robots": list of robot_id strings, from the known IDs only` | 106 | No meaning is given: "robots in the conflict" and "robots the strategy acts on" are both readings |
| `"reverse": the involved robots back straight out along their own lanes` | 116 | Listing robot_5 under `reverse` means robot_5 backs out |
| head-on guidance: `strategy="yield" (the robot named in yield_robot backs up) or strategy="reverse" (both back up to clear)` | 90-92 | Only one robot backing up is `yield` with `yield_robot=robot_4` |
| plan invitation: "The system verifies it and, if needed, minimally repairs it before anything is dispatched" | 218-224 | Implies the plan is what gets dispatched |
| plan grammar: `"continue": proceed unchanged; not part of the resolution` | 249 | robot_5 `continue` conflicts with robot_5 involved under `reverse` |
| `- any other strategy: no constraint on the legs` | 258 | Tells the model a `reverse` plan may reverse any subset |
| plan-state advice "Hold this plan unless …" | 352-357 | The model was told to keep robot_4 reverse / robot_5 continue |

- **Reading.** Under the literal definitions on lines 106, 116 and 90-92, the answer contradicts itself: `strategy` plus `involved_robots` says both robots back up, while `justification` and the plan say only robot_4 does. The consistent encoding of the stated intent was `yield` with `yield_robot=robot_4`.
- **What made the mistake likely** (inferred). Lines 218-224 and 258 tell the model that a `reverse` plan may name any subset and will be verified before dispatch. Line 106 leaves "involved" open, and robot_5 is involved in the conflict. The plan-state block, built by the system, already encoded "robot_4 reverse, robot_5 continue", and the model was told to hold it.
- **So:** the model's answer was self-inconsistent under the strict contract, and the system discarded the part of it (the plan) that the prompt had invited the model to rely on.

#### 2.6 How the Artifact and Logs Record It

| Channel | What it shows | Visible? |
|---|---|---|
| `plan.provenance` | `vlm_verbatim` | Misleading: reads as "executed verbatim" |
| `plan.dispatch_matches_plan` | `false` | The only signal; needs a reader who knows to look |
| `plan.edits`, `plan.rejection_reason` | `[]`, null | Silent |
| `dispatched_command.degradations` | `grounding=dynamic_arms:lane:y` only | Silent: no tag for an overridden leg |
| `m5.log` | two `dispatch … robot=` lines and the `plan_id`; no line mentions the plan/dispatch difference | Silent |
| `plan_metrics.score_plan_decision` | `agreement` is True whenever `consistent` and `vlm_verbatim` (`plan_metrics.py:160`); only `verbatim_dispatch_matched` (line 189-191) carries the False | Half: the registered "agreement" reading counts this decision as agreement |
| Plan-state block of the next prompt | leg statuses follow command status, not action (section 2.2) | Wrong |

### 3. How Often the Pattern Occurs (Verified by Scan)

#### 3.1 Scan Rules (Rerunnable)

- **Bundles.** Every directory named `decisions` under the three roots, excluding any path with a `_backup*` component:
  - campaign (`…/v7j/data/logs/vm_runs/demo_campaign`): 14 bundles;
  - October and earlier (`…/v3/data/logs/vm_runs`): 138;
  - the main checkout (`…/vgu-vlm-swarm/data/logs/vm_runs`): 249. This root is outside the task's named scope; it is reported separately below.
- **Artifacts.** Deduplicated by `request_id` in the order campaign, v3, main; 191 main-checkout artifacts were duplicates.
- **Kept.** Decisions with `congestion_detected` true, a non-empty model `proposed_plan`, and a dispatch record (`dispatched_command` or `dispatch_withheld`).
- **Per-robot dispatched kind.**
  - `yield` gives `backup`, `reverse` gives `reverse`, `reroute` gives `reroute`.
  - A `temporary_wait` with `linked_position` is `linked_wait`; any other is `wait`.
  - The `passer_robot_id` of a `yield` with `passer_escort_distance_m` > 0 is `escort`.
  - A withheld decision gives every robot `none`.
- **Model leg.** Read from `proposed_plan`, or `absent`.
- **Disagreements counted.**
  - **U** — the robot got motion (`reverse`/`backup`/`escort`/`reroute`) and its leg was `continue`, `wait`, `absent` or `cross`. An escort of a `cross` leg is agreement.
  - **W** — the leg asked for motion (`reverse`/`yield`/`reroute`) and the robot got `wait`, `linked_wait` or `none`.
  - **X** — different motion.
- **`junction_clear`** is kept apart: its `dispatched_command` is phase 0 of a phase queue (`reasoning_pipeline.py:1725-1731`), so it is not comparable leg by leg.

#### 3.2 Counts

In scope (campaign + v3, deduplicated), non-`junction_clear`, plan-carrying decisions with a dispatch record: **123** (campaign 37, v3 86). 94 of them have at least one per-robot disagreement of any kind. Most of those are documented refusals or yielder swaps, separated below.

| Strategy | Pattern | Robot-legs | Commands | Visible in the artifact? |
|---|---|---|---|---|
| `reverse` | **U: reversed, plan said `continue`** | 1 | 1 (`95066420`) | `dispatch_matches_plan` only |
| `reverse` | **U: reversed, plan said `wait`** | 5 | 3 (E13 `ea23b1a7` r1, r3; E17 `9cf93ebe` r4, r5; E11 `c417cbff` r5) | `dispatch_matches_plan` only (all three `vlm_verbatim`) |
| `reverse` | **U: reversed, plan said `cross`** | 4 | 3 (m5V `b07a700f` r1, r2; E13 `652ac9ac` r5; E17 `150b95a6` r3) | Plan `repaired` (cross → wait), but dispatch reversed them anyway; `dispatch_matches_plan` false |
| `reverse` | W: plan reverse, robot got nothing | 6 | 6 (m5V `b07a700f` r4; E13 `652ac9ac` r4, `ea23b1a7` r5; E17 `150b95a6` r4, `fc52c0ed` r4; E10 `d5541ff0` r4) | `node_handoff` / `rear_exempt` tags name the change; no "robot dropped" tag |
| `reverse` | W: plan reverse, robot got a wait | 30 | 15 | Same-side refusal tag `reverse=infeasible:…`, or plan `repaired` to wait (convoy takes) |
| `reroute` | **U: rerouted, plan said `wait`** | 2 | 2 (E16 `df2ed72f` r1; E28 `64d5ef0a` r2, a tranche-1 Arm A episode) | `dispatch_matches_plan` only (`vlm_verbatim`, no tag) |
| `reroute` | **W: plan reroute, robot got a wait** | 5 | 3 (E14 `8e1e9b74`, E16 `df2ed72f`, E28 `64d5ef0a`) | Same |
| `yield` | U: backup, plan said `cross` / X: plan yield, got escort | 13 / 11 | 13 | Yielder swap by the feasibility gate; plan `repaired` or `m3_default`, regrounding tags |
| `yield` | W: plan yield, robot got nothing (withheld) or a wait | 38 / 15 | 38 withheld / — | Refusal reason in `dispatch_withheld` / `yield_refusal_reason`; provenance `m3_default` or `repaired` |
| `yield` | U: escort, plan said `continue`/`wait` | **0** | 0 | — |
| `convoy`, `priority_override`, `temporary_wait` | W | 5 | 5 | Plan `repaired` / aliased yield refusals |

Denominators for the two strategies the plan cannot steer:

- **`reverse`.** 15 in-scope dispatched commands carry a reverse action and a model plan, with 33 reverse legs. **10 legs (30 %) in 7 commands** went to robots whose plan leg was not `reverse`: 1 `continue`, 5 `wait`, 4 `cross`. Across all in-scope `reverse` decisions with a plan, the model's set of `reverse` legs differed from `involved_robots` in 11 of 30. (The main checkout adds 2 of 7.) In every one, the extra robots were in `involved_robots` but not given `reverse`.
- **`reroute`.** All 3 in-scope plan-carrying `reroute` commands disagree with their plan (3 of 3). The template rerouted `involved_robots[0]`, not the plan's `reroute` robot(s).
- **Silent subset** (`provenance` `vlm_verbatim` with `dispatch_matches_plan` false): in scope, `reverse` 5 (`95066420`, `ea23b1a7`, `9cf93ebe`, `d5541ff0`, `c417cbff`), `reroute` 3, `yield` 11. The 11 yields carry no motion disagreement by the rules above; their mismatch is between `continue` and a hold, for example the retreat-shield waits of m5D `03bba450` (inferred for the others from the scan's empty U/W/X rows). Plus 4 `junction_clear` (all held and withheld).
- **Main checkout, out of scope.** s6 `46b0f4dd` reversed r1 and r3 against plan `cross` legs (repaired to wait). s6 `ce07876a`/`cefc787f` rerouted a planned yielder (tagged `yield=infeasible`). `verbatim_pilot/vp04_gpt_ho_s42` `5be8bb7d` is a `reroute` with `dispatch_matches_plan` false.

#### 3.3 Safety Relevance (Verified From the Reverse-Guard Replay Table)

The per-leg ground-truth gaps to declared boxes are taken from `vgu-vlm-swarm-v7l/docs/reports/2026-11-15-escort-obstacle-guard.md` section 8.5 (URDF footprint, v7m contact geometry). Of the 10 unplanned reverse legs:

- **contact:** E13 `ea23b1a7` robot_1 (plan `wait`), FAILED after 0.550 m, gap 0.000 m (rack/NW_west);
- **sub-margin grazes:** m5V `95066420` robot_5 (plan `continue`), 19.1 mm; E13 `652ac9ac` robot_5 (plan `cross`), 17.9 mm;
- **clear:** the other legs, where the table reports them (for example `b07a700f` r1 0.241 m and r2 0.082 m, `9cf93ebe` r5 0.312 m, `150b95a6` r3 0.368 m).

Honouring the plan would have kept those three robots still. The other robot of the same command could still have touched: robot_4 of `95066420` passed at 5.5 mm under its own planned reverse. With `reverse_obstacle_guard` on, the guard would have refused `95066420`, `652ac9ac` and `ea23b1a7` as whole commands (same table). No rate is claimed: n is small, and the planned legs were not compared.

### 4. Classification and Fix Options (None Implemented)

| Level | Finding | Class | Fix (not built) |
|---|---|---|---|
| Model | `reverse` + both robots involved, with a plan and justification that move only one: self-inconsistent under prompt lines 106/116/90-92 | model inconsistency (contributing) | — (addressed through the contract) |
| Prompt contract | `involved_robots` undefined; the reverse grammar is unconstrained (line 258); the invitation says the plan is verified before dispatch (218-224); reroute has no channel naming the rerouting robot except list order, which the prompt never states | contract ambiguity (contributing) | Define `involved_robots` as "the robots the strategy acts on". Add grammar rules: for `reverse`, the `reverse` legs are exactly the involved robots; for `reroute`, the rerouting robot is listed first in `involved_robots` and its leg is `reroute`. Word the invitation so it does not promise plan-driven dispatch. This changes the registered prompt bytes and needs an offline ER-2 check on recorded snapshots. |
| Verifier and recording | `vlm_verbatim` is recorded for a plan that dispatch contradicts. No tag, no log line, and `agreement` counts it. Leg statuses follow command status, not the action actually run (`orchestrator_node.py:931-957`), so the next prompt's plan state is wrong. | defect (recording) | (1) In `_is_consistent`, treat a `reverse` plan whose `reverse` set differs from the involved set as inconsistent, giving `m3_default` with that reason. (2) Compare plan legs with the grounded command before the verdict is written: a leg contradicted by its dispatched action gives a non-verbatim provenance (e.g. `overridden`), a tag `plan=overridden:<robot>:<leg>-><dispatched>` and one M5 WARN line. (3) Mark a leg `done` only when its robot ran that leg's action, otherwise `failed`/`superseded`, and render the dispatched actions in the plan-state block. |
| Grounding | `reverse` and `reroute` are grounded from `involved_robots` order only; the plan is never read (by design, `models.py:842-849`) | grounding design (primary) | Behind a new default-off key, on the `model_when_verified` precedent: for a consistent, verified plan, reverse only the robots whose leg is `reverse` (the view filter, same-side refusal, clamp and `reverse_obstacle_guard` still apply), and reroute the plan's `reroute` robot. This changes registered S1b grounding, so it needs a registration amendment or nothing. |

---

## Part B — Failure-Cause Rubric for Five-Robot S1b Episodes

### 5. Inventory (Neutral Descriptors Only)

#### 5.1 Prior Exposure (Disclosed Before the Rubric)

Before writing sections 6 and 7, this author had read:

- the tranche-1 results (2026-10-21 report §2-§7);
- the demo-campaign narratives for `m5D_t01_a1` (section 8) and the convoy takes (section 5);
- the validation report for `m5V_t01_a1`;
- the per-command reverse-guard GT table (v7l §8.5);
- the aggregates' `attribution` and `churn_class` fields (`batch2/agg_b2.json`, printed while locating outcome fields);
- Part A's scan.

The rubric was written after these, not blind to them. Part A's classification of `95066420`, and the two illustrations in section 7.8, were decided before the rubric existed. They are not coding outputs of it.

**Raters must not be shown:** any report's "cause", "primary cause" or "conclusion" text; the `a_attribution`, `churn_class` and `attribution` fields of `agg_b*.json`; Part A of this report; section 7.8.

#### 5.2 Series and Pooling Status

| Series | Episodes (label prefix) | Source report (`docs/reports/`, v7j) | Bundle root | Arm / backend | Kit (runtime) | Pooling status |
|---|---|---|---|---|---|---|
| S1b pilot 1 | E1, E2 | `2026-10-10-s1b-pilot.md` | v3 `s1b_pilot/` | echo mock (apparatus) | per report | pilot, excluded from every confirmatory count |
| S1b pilot 2 | E3, E4 | `2026-10-10-s1b-pilot2.md` | v3 `s1b_pilot2/` | echo mock | per report | pilot |
| Churn and first live | E5 (echo), E6 (ER-2) | `2026-10-10-churn-and-first-live.md` | v3 `churn_wave/` | echo / Layer 2 on | p3 | pilot |
| A22 live batch | E7, E8, E10 | `2026-10-11-s1b-live-batch.md` | v3 `live_batch/` | Layer 2 on | p4 | pilot |
| Bring-up and resume | E9, E11 | `2026-10-11-bringup-and-resume.md` | v3 `resume/` | Layer 2 on | p5 | pilot |
| Live batch 2 | E12-E17 | `2026-10-11-live-batch2.md` | v3 `batch2/` | Layer 2 on | p6 | pilot |
| Shield and batch 3 | E18-E20 | `2026-10-12-shield-and-batch3.md` | v3 `batch3/` | Layer 2 on | p7 | pilot |
| A27 mini-batch | E21-E23 | `2026-10-12-shield-fix-and-minibatch.md` | v3 `batch4/` | Layer 2 on | p8 | pilot |
| A30 mini-batch | E24-E26 | `2026-10-17-escort-filter-minibatch.md` | v3 `batch5/` | Layer 2 on | p9 | pilot |
| **prereg-v3 tranche 1** | **E27-E31 × Arm A / Arm B** | `2026-10-21-s1b-confirmatory-tranche1.md` | v3 `batch6/` | A: Layer 2 on (ER-2); B: Layer-2-off classical (`reasoning_enabled: false`) | p10, runtime `1624db1` (delta_p10) | **REGISTERED (`confirmatory=1`, `tag=confirmatory_t1`). Never pooled with any other row.** |
| v4 per-cluster shadow | pos21-pos27, Arm A | `2026-11-13-v4-stage1-shadow-results.md` (v6d) | v6d `data/logs/vm_runs/v4_s1b_pc_shadow/runs/` | Layer 2 on, `tag=v4_s1b_pc_shadow`, `confirmatory=0` | v4 kit | exploratory; not read further here |
| Environment audit | ea_E2 ×2 | `2026-10-09-env-audit.md` | v3 `env_audit/runs/` | echo mock | per report | audit; not an episode series |
| Demo campaign | `m5D_t01_a1` | `2026-11-15-demo-campaign-results.md` §8 | v7j `demo_campaign/m5/runs/` | Layer 2 on (ER-2), `confirmatory=0` | delta `4843a776…` | demo; never pooled |
| Validation | `m5V_t01_a1` | v7n `2026-11-15-validation-guard-contacts-results.md` | v7j `demo_campaign/m5v/runs/` | Layer 2 on, guard on, `confirmatory=0` | delta `dde5befb…` | validation; never pooled or scored |

No scripted (default-plan) baseline arm exists for S1b. The echo mock of E1-E5 is apparatus: it names engaged pairs by a fixed rule (`2026-10-11-s1b-live-batch.md` §1). The scripted-default precedent is IB10 Arm C (`2026-11-14-ib10-safety-default-arm-results.md`), a different cell.

#### 5.3 Per-Episode Descriptors

The counts come from the bundles (verified).

- **dec** — decision artifacts.
- **pos** — artifacts with `congestion_detected` true.
- **disp / wh** — dispatched / withheld (`dispatch_withheld` set).
- **Evidence columns** — GT `gt/ground_truth.jsonl`, `m4.log`, `m5.log`, `rec/*.mp4`. `frames/` is empty in every bundle listed.
- **Outcome columns** — copied from the named scorer file, never rescored:
  - **[T]** `batch6/scores_t1/s1_scoring.jsonl`, the registered A33 scorer at `3c71503` with free-flow table `b4002d76`.
  - **[P]** `batch6/s1_scoring_pilots.jsonl`, a later re-scoring of the pilots with the same frozen scorer, labelled "pilot smoke" by its kit. It is not the pilots' own batch readout, which is in each batch's `agg_b*.json` and report.
  - **[R]** the source report's figure; no A33 scoring.

| Episode (bundle) | Seed | Arm | dec / pos / disp / wh | GT / m4 / m5 / rec | Tasks / 25, censor, t_end_rel (source) |
|---|---|---|---|---|---|
| E1 `s1b_E1_seed1_echo` | 978442588 | echo | 8 / 8 / 0 / 8 | 1/1/1/0 | not in a scorer file located; see report [R] |
| E2 `s1b_E2_seed2_echo_a3` | 1181837745 | echo | 5 / 5 / 0 / 5 | 1/1/1/0 | [R] |
| E3 `s1b_E3_seed3_echo_a2` | 537191633 | echo | 10 / 10 / 9 / 1 | 1/1/1/0 | [R] |
| E4 `s1b_E4_seed4_echo_a1` | 90907664 | echo | 6 / 6 / 0 / 6 | 1/1/1/0 | [R] |
| E5 `s1b_E5_seed5_echo_a1` | 1912308941 | echo | 3 / 3 / 0 / 3 | 1/1/1/0 | [R] |
| E6 `s1b_E6_seed6_er2_a3` | 645184162 | A | 5 / 5 / 3 / 2 | 1/1/1/0 | 4, horizon, 577.4 [P] |
| E7 `s1b_E7_seed7_er2_a1` | 625495160 | A | 4 / 4 / 1 / 3 | 1/1/1/0 | 0, horizon, 576.7 [P] |
| E8 `s1b_E8_seed8_er2_a1` | 267370882 | A | 4 / 4 / 1 / 3 | 1/1/1/0 | 3, horizon, 577.3 [P] |
| E9 `s1b_E9_seed9_er2_b1` | 568275074 | A | 7 / 7 / 1 / 6 | 1/1/1/0 | 4, horizon, 569.7 [P] |
| E10 `s1b_E10_seed10_er2_a1` | 790328501 | A | 40 / 2 / 2 / 0 | 1/1/1/0 | 1, **stop_flag**, 210.1 [P] |
| E11 `s1b_E11_seed11_er2_b1` | 1380451483 | A | 9 / 6 / 5 / 1 | 1/1/1/0 | 6, horizon, 571.2 [P] |
| E12 `s1b_E12_seed12_er2_c1` | 1404977387 | A | 7 / 4 / 1 / 3 | 1/1/1/0 | 3, horizon, 570.1 [P] |
| E13 `s1b_E13_seed13_er2_c1` | 9984182 | A | 4 / 4 / 3 / 1 | 1/1/1/0 | 1, horizon, 569.8 [P] |
| E14 `s1b_E14_seed14_er2_c1` | 1198395108 | A | 4 / 4 / 3 / 1 | 1/1/1/0 | 1, horizon, 572.1 [P] |
| E15 `s1b_E15_seed15_er2_c1` | 1730051314 | A | 3 / 3 / 2 / 1 | 1/1/1/0 | 1, horizon, 571.4 [P] |
| E16 `s1b_E16_seed16_er2_c1` | 1094022857 | A | 4 / 4 / 3 / 1 | 1/1/1/0 | 3, horizon, 570.1 [P] |
| E17 `s1b_E17_seed17_er2_c1` | 1554234675 | A | 14 / 14 / 8 / 6 | 1/1/1/0 | 9, **stop_flag**, 269.0 [P] |
| E18 `s1b_E18_seed18_er2_d1` | 1648691287 | A | 9 / 9 / 4 / 5 | 1/1/1/0 | 1, horizon, 568.2 [P] |
| E19 `s1b_E19_seed19_er2_d1` | 1509617270 | A | 6 / 6 / 1 / 5 | 1/1/1/0 | 3, horizon, 569.9 [P] |
| E20 `s1b_E20_seed20_er2_d1` | 447088698 | A | 7 / 6 / 5 / 1 | 1/1/1/0 | 8, horizon, 570.9 [P] |
| E21 `s1b_E21_seed21_er2_e1` | 2107305794 | A | 4 / 4 / 1 / 3 | 1/1/1/0 | 1, horizon, 570.5 [P] |
| E22 `s1b_E22_seed22_er2_e2` | 1949376341 | A | 4 / 3 / 2 / 1 | 1/1/1/0 | 3, horizon, 572.7 [P] |
| E23 `s1b_E23_seed23_er2_e1` | 1256773113 | A | 6 / 6 / 2 / 4 | 1/1/1/0 | 6, **stop_flag**, 170.9 [P] |
| E24 `s1b_E24_seed24_er2_f2` | 1151798991 | A | 6 / 4 / 2 / 2 | 1/1/1/0 | 6, **stop_flag**, 108.8 [P] |
| E25 `s1b_E25_seed25_er2_f2` | 1556492460 | A | 6 / 6 / 3 / 3 | 1/1/1/0 | 4, **stop_flag**, 144.3 [P] |
| E26 `s1b_E26_seed26_er2_f1` | 387918679 | A | 6 / 6 / 3 / 3 | 1/1/1/0 | 1, **stop_flag**, 102.3 [P] |
| **E27 A** `…armA_er2_confT1_a1` | 978442588 | A | 11 / 9 / 5 / 4 | 1/1/1/0 | 8, horizon, 570.7 [T] |
| **E27 B** `…armB_l2off_confT1_a2` | 978442588 | B | 0 | 1/1/1/0 | 5, horizon, 571.1 [T] |
| **E28 A** | 1181837745 | A | 4 / 4 / 2 / 2 | 1/1/1/0 | 2, horizon, 568.8 [T] |
| **E28 B** | 1181837745 | B | 0 | 1/1/1/0 | 1, horizon, 570.4 [T] |
| **E29 A** | 537191633 | A | 5 / 5 / 2 / 3 | 1/1/1/0 | 0, horizon, 570.1 [T] |
| **E29 B** | 537191633 | B | 0 | 1/1/1/0 | 0, horizon, 570.7 [T] |
| **E30 A** | 90907664 | A | 5 / 5 / 1 / 4 | 1/1/1/0 | 5, horizon, 570.7 [T] |
| **E30 B** | 90907664 | B | 0 | 1/1/1/0 | 6, horizon, 572.0 [T] |
| **E31 A** | 1912308941 | A | 3 / 3 / 2 / 1 | 1/1/1/0 | 1, horizon, 569.2 [T] |
| **E31 B** | 1912308941 | B | 0 | 1/1/1/0 | 0, horizon, 571.2 [T] |
| `m5D_t01_a1` | 2107305794 | A | 8 / 8 / 2 / 6 | 1/1/1/1 | 1 of 5 arrived (GT 0.3 m), tasks 1/25, 600 sim-s horizon [R] |
| `m5V_t01_a1` | 2107305794 | A (guard on) | 9 / 9 / 4 / 5 | 1/1/1/1 | 2 of 5 arrived (GT 0.3 m), unresolved at 600 sim-s [R] |
| v4 shadow pos21-27 (7 bundles) | per CONDITION | A | 4 / 7 / 11 / 6 / 13 / 6 / 3 dec | 1/1/–/0 | not read [R: v6d report] |

**Notes.**

- **Bring-up aborts and dead attempts** are not episodes. They have no `m5.log`, or the report marks them aborted: E2 `abort1`/`a2_abort`, E3 `a1`, E6 `a1`/`a2` (bringup), E9 `a1`-`a3`, E11 `a1`-`a3`, E22 `e1`, E24 `f1`, E25 `f1`, E27 B `a1`.
- **Rows marked [P] stop_flag** are cut short by the batch's stop rule, not censored at the horizon. Section 7.6 gives the rule.
- **GT contact fields.** Every October bundle's GT contact lists are hard-coded `[]` (`isaac/vgu_sim/acceptance_logging.py:99-100`). Only `m5V_t01_a1` has logged contact fields (`contact_model: urdf_footprint_v1`). No October bundle has a recording.
- **Bundle count.** This scan found 399 `decisions` directories over the three roots (14 + 138 + 249), not the reverse-guard replay's "375 bundles". The replay counted bundles, not directories, and its exact rule is not reproduced here.

---

### 6. Evidence Available per Cause Class

| Class | Recorded signals that can establish it | Cannot be established from the logs alone |
|---|---|---|
| **V — VLM decision** | `raw_text` and the parsed `decision`. `involved_robots` against the A33 GT conflict set (involved-set F1, per [T]/[P]). Missed detection (`congestion_detected` false while a GT conflict is open; A33 recall). Strategy against the cell oracle's `accepted_strategies` (`plan_metrics.strategy_matches_oracle`). Yielder with no retreat room while another robot has room (the gate's own measurement in `yield_refusal_reason`). Self-inconsistency by the contract rules of section 7.3 (V4). `diagnostics` (refusal, parse failure, `backend_failed`) | Whether a "correct" decision would have resolved the scene (needs T1 offline, or T4 live) |
| **G — grounding / verification** | Refusal reasons (`dispatch_withheld.refusal_reason`, `yield_refusal_reason`, `reverse=infeasible:*`). `plan.provenance`, `edits`, `rejection_reason`. Parser nulling (`proposed_plan=default:invalid_structure`). Role changes (`grounding=node_handoff*`, `rear_exempt`, `yield_robot=*regrounded`, swap). `dispatch_matches_plan`. Unsafe-but-admitted legs: escort or reverse legs crossing a declared box, by the offline guard replays (`v7l scripts/escort_obstacle_replay.py`, `reverse_obstacle_replay.py`) and the contact recompute (`v7m scripts/recompute_gt_contacts.py`) | Whether a missing strategy (no template), rather than geometry, blocked resolution (needs T1 and T2) |
| **X — execution** | `m4.log` primitive terminal status (COMPLETED / FAILED / timed out), `fresh_latch_fast_fail`, `safety stop` / `min_distance_violation` lines, `exempt pairs changed` lines. `nav2_r*.log` (aborts, "Failed to make progress"). GT motion against the commanded distance. M1 `STALE` / lost-TF lines (`m1.log`, `m5_scene.jsonl`). Robot-static contact only by recompute for October bundles | Why Nav2 stalled internally; contact in October bundles without the recompute; anything visual (no October recordings) |
| **E — environment geometry** | Declared boxes and corridor (`scenario.yaml`). Recorded poses. The gate's retreat-room measurements ("no feasible yielder (... < 0.77 m required)") — these are the grounder's own and are not grounder-independent. T2 below is the independent check | Whether the scene was unsolvable for every policy: only a live oracle run (T4) can show solvability; T2 can show only that no straight clearing move exists |

**Unsolvable versus strategy-less.** "Geometry made it unsolvable for any policy" and "grounding lacked a strategy" are told apart by two offline tests, T1 and T2 (section 7.4). If T2 finds a clearing move but T1 (every hypothetical decision through the pinned grounder) yields none, the grounder lacked the strategy (G7). If T2 finds none, the class is geometry (E1). If T1 finds a motion the recorded decision did not ask for, the decision is implicated. The convoy diagnosis is the precedent: 76 hypothetical decisions were grounded, and the scripted oracle decision resolved the scene.

---

### 7. The Rubric (Frozen at the Commit That Adds This File)

This section is self-contained. It is frozen at the commit that first adds this file (`git log --diff-filter=A -- docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md`). Any later change is a dated revision with its reason, written before any coding pass it affects.

#### 7.1 Units

- **Episode.** One bundle that ran to its end condition: horizon, stop rule or deadline. Bring-up aborts are excluded and listed.
- **Failure unit (FU).** Defined from GT, so it exists in every arm. An FU is either:
  - an A33 GT conflict, as scored by the frozen A33 scorer (`benchmarks/s1_scoring` @ `3c71503`), whose robots had not all cleared it at the censoring point; or
  - a "lone stall": a robot whose GT pose moved less than 0.05 m over the last 60 sim-s before censoring, while not dwelling at a task node and not part of an FU above.

  Each FU has an onset time t0: the A33 conflict onset, or the start of the lone stall's stationary run.
- **Event.** Any of: an analysis (decision artifact), a dispatched or withheld command, an M4 primitive terminal status, a Nav2 abort line, an M1 STALE interval, or a GT contact or sub-margin interval from the recompute. Events are ordered by sim time; wall-clock lines are mapped with the linear fit over `sim_t=` lines in `m4.log`.
- **Codes are assigned per event.** Each FU gets one **primary** and zero or more **contributing** codes. Each episode gets one primary and a contributing set.

#### 7.2 Cause Codes

- **V — VLM decision** (Layer-2-on arms; for a scripted arm the same codes are prefixed S):
  - V1 missed: no positive analysis naming at least 2 of the FU's robots within the A33 detection window after t0;
  - V2 omitted robot: a positive analysis whose `involved_robots` misses an FU robot that T1 shows must act (it appears in every motion-producing hypothetical);
  - V3 infeasible role: the named yielder or reverser is refused for room while T1 shows another robot of the FU feasible in that role;
  - V4 self-inconsistent: by the contract rules C1-C3 of section 7.3;
  - V5 strategy outside the cell's `accepted_strategies`, where the cell registers any;
  - V6 no usable answer: refusal, parse failure or `backend_failed`.
- **G — grounding / verification:**
  - G1 refused a decision that is contract-consistent and T2-feasible;
  - G2 default substituted for a plan (`m3_default` with a plan present);
  - G3 plan nulled by the parser;
  - G4 roles changed so the dispatch differs from the decision (handoff, rear exemption, swap, robots dropped);
  - G5 an admitted leg crosses a declared box grown by half-width + `retreat_box_margin_m` (guard replay), or the recomputed GT gap of a commanded leg falls below 0.005 m;
  - G6 plan contradicted by dispatch while recorded `vlm_verbatim`;
  - G7 no strategy: T1 is empty while T2 is not.
- **X — execution:**
  - X1 M4 primitive FAILED or timed out;
  - X2 Nav2 abort, or no progress for at least 60 sim-s under an active Nav2 goal;
  - X3 latch pinned: after a command completes, a non-exempt pair stays within `min_distance_m` until censoring and both robots are stopped;
  - X4 perception: a commanded or FU robot STALE, or its TF lost, for at least 10 sim-s;
  - X5 GT contact (recomputed gap < 0.005 m) not attributable to a G5 leg;
  - X6 harness or apparatus (a gate failed, a recorder fault that stopped M-nodes, the run's own stop rule).
- **E — environment geometry:**
  - E1 T2 is empty at t0: no robot of the FU has a straight clearing move;
  - E2 an undeclared obstacle (present in the USD or scene builder, absent from `static_obstacles`) is in contact with an FU robot by the recompute.
- **N — no Layer-2 action by design** (Layer-2-off arm only): N0. It is a context code, never primary.
- **U — undetermined:** U plus the named missing evidence, for example `U:no_snapshot`, `U:T1_not_run`, `U:no_recording_for_contact`, `U:live_only_T4`.

#### 7.3 Contract Rules for V4 (Prompt v3 Wording, Lines Cited in Section 2.5)

- **C1.** strategy `reverse`: the set of `reverse` legs in `proposed_plan` differs from `involved_robots`, or `justification` names an involved robot as continuing or passing.
- **C2.** strategy `yield`: the plan has more or fewer than one `yield` leg, or its yield leg differs from `yield_robot`. This is the verifier's own rule.
- **C3.** strategy `reroute`: no `reroute` leg is on `involved_robots[0]`.

#### 7.4 Counterfactual Tests

| Test | What it computes | Offline? |
|---|---|---|
| **T1 — decision substitution** | On the snapshot of each analysis on the FU, and on the t0 snapshot (`m5_scene.jsonl`), ground every hypothetical decision in the fixed set H through the episode's own pinned grounder, with the bundle's own params, geometry and goals. **Output:** the subset of H whose command gives at least one FU robot a non-refused reverse/yield/escort/reroute leg. Computed with guards as run, plus a sensitivity column with every guard on (not used for the primary). | yes (a grounder replay) |
| **H** (frozen) | Over the FU's robots plus the two nearest other robots: every yielder/passer pair; every multi-passer yield with every crossing order of at most 4 robots; every `reverse` of each 1-robot and 2-robot subset and the full set; `reroute` with each lead; `temporary_wait`; `convoy`, `priority_override` and `junction_clear` with each lead | — |
| **T2 — geometric clearing move** (grounder-independent) | Is there a robot r of the FU and one of 8 headings (multiples of 45°) along which r's footprint (URDF chassis box) can translate straight to a pose at least `min_distance_m` (0.45 m centre distance) from every other robot? The swept footprint must stay at least half-width + 0.05 m from every scene box the builder authors (declared or not) and from every other robot's footprint. **Output:** true/false, plus the shortest move | yes (geometry only) |
| **T3 — execution check** | For each dispatched leg: M4 terminal status; GT displacement against the commanded distance (< 50 % counts as not executed); recomputed minimum gap; latch lines | yes |
| **T4 — live oracle** | Rerun from the same seed with a scripted decision drawn from T1's motion set | live only; never required for coding, and named in U when it would decide |

#### 7.5 Primary-Cause Rule (Applied per FU, in This Order; the First Rule That Fires Decides)

1. **Evidence gate.** If the snapshot for t0, the decision artifacts or `m4.log` needed by a later step are missing, the primary is `U:<missing>`. Stop.
2. **Onset geometry.** If T2(t0) is false, the primary is E1. If T2(t0) is true and T1(t0) is empty, the primary is G7.
3. **First deviation.** Walk the FU's events from t0 in time order and stop at the first deviation:
   - an analysis coded V1-V6, judged against T1 at that snapshot: V2 and V3 need T1 non-empty;
   - a grounding outcome coded G1-G6;
   - a command outcome coded X1-X5 by T3.

   The primary is that deviation's code.
4. **Ties.** If one event carries several codes, the primary is the most upstream: V before G before X. Exception: G5 precedes the X code of the same leg, because the leg itself was unsafe.
5. **Recoverability loss.** If no deviation is found before T1 becomes empty for every remaining snapshot of the FU, the primary is the code of the last event before T1 first became empty. If that event was a completed command followed by a pinned pair, the code is X3.
6. **Fallback.** If none of steps 1-5 fires, the primary is `U:no_deviation_found`.

**Contributing codes.** Every other code observed on the FU's events, including V4/G6 on events after the primary.

**Episode primary.** The primary of the FU with the earliest t0. Ties are broken by FU size, then by the lowest robot id. **Episode contributing.** The union of all FUs' codes.

#### 7.6 Special Cases

- **Layer-2-off (Arm B).** No V or G event exists, so those codes are "not applicable by construction", never "absent". Steps 1, 2, 3 (X codes only) and 5 apply unchanged. Every FU carries N0 as contributing. T1 is still computed and reported as "a Layer-2 action was available" (yes/no); it is never used to assign V or G. The arms are therefore compared on the E, X and U codes and on outcome fields only. V and G are reported within Layer-2-on arms.
- **Scripted / default-plan arm.** Coded exactly like Layer 2 on, with S1-S6 in place of V1-V6.
- **Echo mock (E1-E5).** Coded like a scripted arm (S codes). Kept as its own arm type in every table.
- **Stop-rule censoring (`stop_flag`).** FUs open at the stop are coded as usual, with X6 added as contributing. The episode's outcome fields stay as scored, and stop-flag episodes are tabulated separately from horizon episodes.
- **Multi-cause FUs.** Only one primary; every other code is contributing. Reports give primary counts and contributing counts side by side, never summed.
- **Missing static-contact evidence.** October bundles use the recompute (`v7m scripts/recompute_gt_contacts.py`) for X5/G5/E2. If it was not run on a bundle, the code is `U:no_contact_recompute`, never "no contact".

#### 7.7 Rater Procedure and Frozen Fields

- **Mechanical first.** One script computes FUs, t0, T1, T2 and T3 for every episode before any rating. It is committed with its md5 and must not read any report.
- **Two independent passes.** Two separate agents, each given only this section 7, the script output and the bundle, apply 7.5 and 7.6.
  - Blinding to arm is feasible only for the GT-derived fields (FU list, T2, X3/X5 from GT). Decision artifacts reveal the arm, so V/G coding cannot be blind.
  - Raters do not see the material listed in 5.1.
- **Reconciliation.** Report agreement on the primary class (V/G/X/E/U) as raw agreement and Cohen's κ, and on the full code. List every disagreement with both codes and the reconciled code. Reconcile by discussion against the rubric text; if that fails, a third agent decides, and the disagreement stays listed.
- **Frozen before coding.** The outcome fields of section 5.3, exactly as in their named source files: tasks completed, completeness status, `censor_reason`, `t_end_rel`; A33 conflicts, detections, involved-set F1, type accuracy; GT minimum pair distance. Also frozen: the parameters stated in this section (0.05 m, 60 s, 10 s, 50 %, 0.005 m, 0.45 m, H). No outcome is rescored, and no series is pooled across the rows of section 5.2.

#### 7.8 Worked Template (Illustrations Decided Before This Rubric; Not Coding Outputs)

| Episode | FU (robots, t0) | Arm | Event (sim s, id) | Event codes | T1 non-empty? | T2 | Primary | Contributing | Evidence / U |
|---|---|---|---|---|---|---|---|---|---|
| *illustration:* `m5D_t01_a1` | {robot_2, robot_3}, ≈103 | A | 138.7 `a15f3fc5` escort robot_3 | G5 (`escort_hits_obstacle:robot_3:obstacle_2:0.414` by replay), X1 (escort FAILED, deadline) | not computed | not computed | *(as documented: G5, the escort segment crossed `obstacle_2`)* | X1, X3 | demo report §8.7; guard replay |
| *illustration:* `cvD_t0{1,2,3}_a1` (convoy, not S1b) | {robot_1-robot_4}, first trigger | A | first decision (pair only) | V2 (the platoon was omitted) | yes (the oracle decision grounds and resolves) | — | *(as documented: V2)* | G7 for the later post-latch decisions (72 of 76 hypotheticals gave waits), X3 | demo report §5.4-5.5 |
| (blank row for coding) | | | | | | | | | |

---

### 8. Scoping Note: a Post-Fix Comparison With Equivalent Safety Mechanisms

#### 8.1 Mechanisms and Their Validation State (2026-11-15)

| Mechanism | Layer, key | Branch / evidence | Validation state | Acts in a Layer-2-off arm? |
|---|---|---|---|---|
| Safety-exemption scope fix | M4, `safety.scoped_clearing_exemption` | v7c `fix/safety-exemption-scope` (`8933863`), `docs/reports/2026-11-14-safety-exemption-fix.md` | unit tests + replay over 68 bundles; no live run | **No** (inferred): it scopes exemptions that dispatched yield/reverse commands create, and Layer-2-off dispatches none |
| Escort obstacle guard | M3, `escort_obstacle_guard` | v7l, merged into v7n; live in `m5V_t01_a1` | 1 live validation take (n = 1), offline replay of 24 October escorts (only E18 `1feb2c4e` changes) | **No**: M3 is not run |
| Reverse obstacle guard | M3, `reverse_obstacle_guard` (default off) | v7l §8 | unit tests + offline replay of 17 reverse commands (14 refused, 10 justified); no live run | **No** |
| GT contact logging | M6, always on | v7m `feat/gt-contact-logging`; validated in `m5V_t01_a1` (6001/6001 rows match the recompute) | 1 live take | **Yes** (measurement only, both arms) |
| Queued-robot hold | M3, `grounding_hold_queued_crossers` (default off) | v7o `fix/convoy-hold-queued-robots` (`d85d1ed`) | unit tests + offline replay | **No**. Its report scopes it to a *legacy-mode corridor yield*. S1b runs derived grounding, so it is inferred inert in S1b. |
| M4 stall abort | M4 | v7p `fix/m4-stall-abort` | **no committed or uncommitted work found** (HEAD `8933863`, equal to v7c's) | Not known; inferred no if it aborts only M4 primitives |

**Plainly:** a Layer-2-off arm dispatches no escorts, reverses or yields. Every new mechanism except contact logging is inert there by construction, so "equivalent mechanisms" is automatic for Layer-2-off: both arms share the M4 latch, the 0.20 m floor, Nav2 and the GT logging. Equivalence matters only for a baseline that dispatches M3 commands: a scripted or default-plan arm (the IB10 Arm C pattern, which S1b does not have). There, every M3 and M4 guard must be keyed identically in both arms.

#### 8.2 Offline Versus Live

- **Answerable offline from the existing bundles.**
  - Which historical commands each guard would refuse or shorten. This is done for escorts and reverses.
  - Which exemptions the scoped fix would change. This is done over 68 bundles.
  - T1/T2 per FU.
  - What a scripted default-plan decision would have grounded to on each recorded snapshot.
- **Only by new live runs.**
  - Whether a scene then resolves. A refused reverse becomes an 8 s wait fan-out, which changes every later state.
  - Arrival counts under the fixed stack.
  - Whether the refusals trade contacts for more stalls.

#### 8.3 Candidate Designs (Exploratory; None Approved)

| Design | Seeds | Arms | Episodes | VM (chain) | API |
|---|---|---|---|---|---|
| D1 same seeds | tranche-1 positions 1-5 (already spent, so reuse burns nothing) | A (ER-2, all guards on) + B (Layer-2-off) | 10 | ≈ 9.3 h chain (tranche 1: 9 h 18 min for 10 + 1 abort) plus boot and prep | ≈ $0.21-0.45 (tranche-1 Arm A $0.024-0.086 per episode; m5D $0.0675, m5V $0.0692) |
| D1+C | positions 1-5 | A + B + C (scripted default plan, guards on) | 15 | ≈ 14 h | ≈ $0.21-0.45 (C makes no calls) |
| D2 fresh seeds | extension positions ≥ 28 (21-27 are used by E21-E26 and the v4 shadow) | A + B (± C) | 10-15 | as D1 | as D1 |

- **Per-take wall.** A single five-robot take costs about 64-69 min of VM wall from start to TERMINATED: ledger `m5` 3833 s and `m5v` 4144 s. GPU stockouts added 24-35 min before VM start on both days and are not booked.
- **Seed rule.** Positions 6-20 of `config/s1_seeds.yaml` are reserved for the registered prereg-v3 continuation. Any exploratory design must not use them.
- **Status rule.** Every such run is `confirmatory=0`, carries its own tag, and is **never pooled** with prereg-v3 tranche 1 or its continuation. Its comparison with tranche 1 is descriptive, side by side, with tranche 1's results preserved as scored.

#### 8.4 Open Questions for the Owner

1. Is the rubric (section 7) accepted as frozen, or revised first? A revision must come before the mechanical script runs.
2. Should the T1/T2 script be built (offline, no VM) before any coding pass? Coding without it falls back to `U:T1_not_run` for most FUs.
3. Should the scope include the echo pilots (E1-E5) and the v4 shadow bundles, or only E6-E31 plus the two November takes?
4. Part A: which fix level, if any? Prompt, verifier/recording, or plan-driven `reverse`/`reroute` grounding. The last two change registered S1b behaviour and need an amendment.
5. Post-fix comparison: which design (D1, D1+C, D2), and is a scripted S1b arm wanted at all?

---

## References

- Bundles: listed in section 5.2.
- Code at v7n `a412949`: `reasoning/rag/command_grounder.py`, `reasoning/rag/grounding_view.py`, `reasoning/rag/plan_metrics.py`, `reasoning/vlm/prompt_builder.py`, `reasoning/vlm/models.py`, `reasoning/vlm/output_parser.py`, `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/{reasoning_pipeline.py,plan_tracker.py,orchestrator_node.py,models.py}`.
- Reports: `vgu-vlm-swarm-v7l/docs/reports/2026-11-15-escort-obstacle-guard.md` (§8); `vgu-vlm-swarm-v7n/docs/reports/2026-11-15-validation-guard-contacts-results.md`; `docs/reports/2026-11-15-demo-campaign-results.md` (§5, §8); `docs/reports/2026-10-21-s1b-confirmatory-tranche1.md`; the October reports of section 5.2; `vgu-vlm-swarm-v7o/docs/reports/2026-11-15-convoy-hold-queued-robots.md`; `docs/reports/2026-11-14-safety-exemption-fix.md`.
- Ledger: `data/logs/vm_runs/demo_campaign/ledger/campaign_ledger.tsv`.

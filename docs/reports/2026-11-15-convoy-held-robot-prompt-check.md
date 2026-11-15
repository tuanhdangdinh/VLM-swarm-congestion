# Convoy Held-Robot Prompt Check

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: pre-registration (section 1), written and committed before any paid call (`4ba2175`).
- Rev 2 (2026-11-15): results (sections 2–5): 44 ER-2 calls, $0.2990 list; no-go.

---

## Summary

- **State available (verified from code).** M5's task registry knows which robots are held at request time. The new default-off condition `prompt_held_robot_state` states it truthfully. Commit `2f83faf`, 54 new tests; the unit suite fails exactly as before.
- **Paid check (verified by running).** 44 ER-2 calls, 22 per condition, $0.2990 at list price. In both conditions, 0 of 22 answers grounded into the smoke's four-robot sequence. Every answer named only robot_1 and robot_2 in `involved_robots`.
- **What the sentence did change.** Plans gave both queued robots `wait` instead of `continue` in 16 of 22 answers, against 2 of 22 in the control. Legacy grounding commands only the robots the decision names, so those `wait` legs reach no command. All 44 grounded commands name robot_1 and robot_2 only.
- **Verdict: no-go for a live convoy retake** under the pre-registered rule: P = 0 of 18 under both conditions. The estimated per-take chance of the oracle structure is about 0, with a 95 % upper bound of about 17 % (section 4).

---

## 1. Pre-Registration (2026-11-15, Before Any Paid Call)

**Question.** In the three live convoy takes (`docs/reports/2026-11-15-demo-campaign-results.md` section 5), ER-2's first decision named only the standoff pair. The prompt showed robot_3 and robot_4 as `STOPPED`, with no sign that M5 was holding them back (section 5.3 there). Does stating that hold-back state make ER-2's first answer ground into the command that resolved the scripted smoke? That command is a yield by robot_2, linked waits for robot_1, robot_3 and robot_4, and a crossing order covering all three.

**Is the state available at request time? Yes, as live M5 state (verified from code).**

- M5's `TaskRegistry` holds every robot with `start_delay_sec > 0`, or a task-stream hold, in `release_at` until it is released. `is_pending` reads it (`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/task_registry.py:76-78`).
- Release happens in M5's own timer (`orchestrator_node.py:1017-1021`, `_on_timer` → `release_due`). The registry publishes `start_pending: true` for held robots (`task_registry.py:177`), which M4's base mission obeys (`swarm_execution/base_mission.py` `on_registry`).
- The request is built in the same node from the same registry (`orchestrator_node.py` `_submit_pipeline` → `_apparatus_inputs`, the new read at line 2609). No new plumbing across modules is needed. Branch 2a applies.
- The goals are already in the prompt (`goal_x`, `goal_y` on every state line), so branch 2b's alternative adds nothing.

**The condition (commit `2f83faf`, `feat: add default-off held-robot state prompt condition`).**

- Config key: `prompt_held_robot_state: bool = False`. It requires `plan_channel_enabled` (v3 only), like the other prompt conditions.
- Request field: `ReasonerRequest.held_robot_ids: list[str] | None`. None means off. M5 fills it with `sorted(r for r in snapshot robots if registry.is_pending(r))`.
- Rendered text, v3 only, and only when at least one listed robot is in the scene:
  - Each held robot's state line ends with `, start_pending=true`.
  - One note follows the state lines, verbatim:

    > start_pending=true: the system has not yet released this robot to start its task; once released, it starts driving toward its goal_x, goal_y.

  - The note is facts only. It names no robot, strategy, role or order.
- Artifact: `prompt_conditions.held_robot_ids`, omitted when off. Replay (`scripts/replay_live_decisions.py` `_apparatus_kwargs`) rebuilds the prompt from it.
- Startup line: `plan_order_status_line` now also logs when only this key is on, with the suffix ` prompt_held_robot_state=True`. Every earlier line is unchanged.
- Off, or on with an empty list, the prompt is byte-identical (tests).

**Stimuli (4 first-trigger snapshots).**

| Stimulus | Bundle | Request | Stored `user_sha256` | Treatment `user_sha256` |
|---|---|---|---|---|
| take 1 | v7j `demo_campaign/cv/runs/cvD_t01_a1` | `35084986` | `24b34947…` | `3fb81862…` |
| take 2 | v7j `demo_campaign/cv/runs/cvD_t02_a1` | `759bdb94` | `8e44f2ab…` | `f1b379c9…` |
| take 3 | v7j `demo_campaign/cv/runs/cvD_t03_a1` | `ab6a10c5` | `5ca37656…` | `df03e11f…` |
| smoke | v7f `convoy_live/runs/cvL_e01_armC_a1` | `39f28463` | `6163da99…` | `a4a486fb…` |

The treatment adds 182 characters. No other convoy first-trigger stimulus with a recorded prompt and frame exists. The smoke's answer was scripted, so its stimulus is the real prompt and frame, not a model answer.

**Held set.** The recorded artifacts predate the field, so the set comes from bundle evidence:

- robots with `start_delay_sec > 0` in the bundle's `orchestrator.overlaid.yaml` (robot_3 and robot_4, 120 s);
- whose `start delay elapsed, base mission released robots=[...]` line in `m5.log` comes after this request's first `dispatch` line (69–82 wall-s after it in all four bundles).

The result is `[robot_3, robot_4]` on all four.

**Free gates (passed; `data/experiments/2026-11-15-convoy-held-robot-prompt-check/gates.json`).**

- The rebuilt control prompt matches the stored `user_sha256` on 4 of 4.
- An offline replay of each recorded first decision reproduces its dispatched command, 4 of 4. It runs the M5 `chi` pipeline with the artifact's own legacy grounding params, which is the runner's `make_pipeline` and `_run_from_result`. The smoke's replayed command has the target structure.
- The effective ER-2 config equals the live takes' config: `gemini-robotics-er-2-preview`, temperature 0.6, top_p 0.95, top_k 20, thinking low, 2048 tokens, 2 attempts, payload v1.

**Conditions.**

- `C`: the recorded live prompt, rebuilt.
- `H`: the same request plus `held_robot_ids=[robot_3, robot_4]`.
- Same frame, same model and sampling.

**n.**

- 6 replicates per condition on each live take, 4 on the smoke: 22 calls per condition, 44 in all.
- Replicates run in order (rep 0 to 5). Each rep is C then H for every stimulus.
- Harness: `scripts/convoy_held_robot_plan_check.py`. It reuses `vlm_order_channel_plan_check.py`'s `Stimulus`, `GuardedBackend`, `Ledger`, shipped `Reasoner` and offline replay.

**Budget.**

- Expected about $0.0067 per call at list price, from the takes' recorded usage (about 2.9k input and 0.75k output and thought tokens, at $1 / $5 per M), so about $0.30 for 44 calls.
- The ledger counts 1.25 × list. Its cap is 0.48, which is $0.384 at list price, under the hard cap of $0.40. It stops before any attempt whose reserve would cross that cap.
- If it stops early, the analysis uses all billed calls and also reports complete replicates only.

**Measures (per condition; the primary is on the 3 live takes, n = 18 per condition).**

1. **Primary (P).** The answer's grounded command, from the offline `chi` replay with the artifact's legacy params, has the smoke structure (`full_sequence`):
   - exactly one `yield`;
   - linked `temporary_wait` (`linked_position`) for all three other robots;
   - all three in the yield's `crossing_order`;
   - and the yielder is **robot_2** (the variant known to resolve).
2. The same structure with **robot_1** yielding. The scene file says this variant latches. It is counted separately, never toward go.
3. The answer names all four robots with roles: `involved_robots` is all four, and no plan leg is `continue`.
4. Strategy mix, the grounded yielder, grounding refusals and `m3_default` fallbacks.
5. Everything above on the smoke stimulus (n = 4 per condition), reported separately.

**Go rule for a live convoy retake, fixed now.** Go only if, on the 3 live takes:

- P under H is at least 9 of 18; and
- P under H exceeds P under C by at least 6.

Otherwise no-go. The per-take chance estimate will be H's P share times an assumed probability that this structure resolves live. The smoke resolved 1 of 1, and the scene file says the robot_2 variant resolves; that probability is inferred, not measured.

**Not changed.** Grounding, verification, safety, feasibility and parser code; the convoy kit; the runtime delta.

---

## 2. Results (Verified by Running, 2026-11-15)

All 44 calls were billed and completed; each was answered on its first attempt with `parse_status=valid`, served `gemini-robotics-er-2-preview`, 0 refusals. The data is in `data/experiments/2026-11-15-convoy-held-robot-prompt-check/`: `calls.jsonl`, `analysis.jsonl`, `summary.json` and `ledger.json`.

| Measure | C, 3 takes (n = 18) | H, 3 takes (n = 18) | C, smoke (n = 4) | H, smoke (n = 4) |
|---|---|---|---|---|
| **P: full sequence, robot_2 yields** | **0** | **0** | 0 | 0 |
| Full sequence, robot_1 yields | 0 | 0 | 0 | 0 |
| Names all four with roles | 0 | 0 | 0 | 0 |
| `involved_robots` = robot_1 and robot_2 only | 18 | 18 | 4 | 4 |
| Strategy | yield 18 | yield 17, reverse 1 | yield 4 | yield 4 |
| Grounded yielder robot_2 / robot_1 / none | 12 / 6 / 0 | 10 / 7 / 1 | 1 / 3 / 0 | 1 / 3 / 0 |
| Plan gives robot_3 and robot_4 both `wait` (exploratory, not pre-registered) | 2 | 14 | 0 | 2 |
| Non-null `crossing_order` (always the pair only) | 13 of 22 overall | 18 of 22 overall | — | — |
| Provenance | `vlm_verbatim` 22 of 22 overall | 21 verbatim, 1 `repaired` of 22 overall | — | — |
| Grounding refusals | 0 | 0 | 0 | 0 |
| Grounded command's robots | robot_1, robot_2 (all 22) | robot_1, robot_2 (all 22) | — | — |

Per take, the grounded yielder for C then H was:

- take 1: robot_2 in 6 of 6, then 4 of 6;
- take 2: robot_1 in 4 of 6, then 4 of 6, with 1 `reverse`;
- take 3: robot_2 in 4 of 6, then 5 of 6.

The H answers gave both queued robots `wait` in 2, 6 and 6 of 6 on takes 1–3. The smoke stimulus gives the same picture (0 of 4 in both conditions).

**The control reproduces the live behaviour.** C answered with the pair only in 22 of 22, as the three live takes did (3 of 3).

**What the sentence changed, and why it does not matter here.** These counts are exploratory, not a pre-registered measure. They were tabulated inline from the `plan`, `reasoning`, `crossing_order` and `grounded` fields of `analysis.jsonl`, not by the committed harness.

- Under H the plans mark the held robots `wait` (16 of 22 overall). Only 1 of 22 reasonings mentions them as "pending robots" ("after which the pending robots can proceed").
- `involved_robots` and `crossing_order` never include them.
- Legacy grounding builds the command from the decision's named robots, the yielder and one passer. Plan verification accepts the `wait` legs (`vlm_verbatim`), but no `temporary_wait` for robot_3 or robot_4 reaches the command. This is verified offline for all 44 answers, with the same path that reproduced the four recorded first commands.
- Released at about 120 s, robot_3 and robot_4 would again drive their own Nav2 goals through the gate, which is the latch of the three live takes.
- There is recorded evidence for this. Live take 2's first answer already gave both queued robots `wait` (campaign report section 5.3). It grounded to the pair only, and the scene latched (section 5.2 there). So the typical treatment answer has been seen not to resolve. It was one take with robot_1 yielding, so for the robot_2 case this remains an inference.

**Grounding can sequence all four once the decision names them (verified offline, free; an ad hoc check with no committed script).** The same snapshots were grounded with hand-written decisions that name all four robots, with and without a plan. All of them produced a full sequence: yield, linked waits for the other three, and all three in the crossing order. This held with robot_2 and with robot_1 as the yielder. So the gap is that the model names the pair only, not the grounder refusing the four-robot answer.

---

## 3. Spend

- 44 calls; 130 576 input tokens and 33 691 output and thought tokens.
- That is **$0.2990 at list price** ($1 / $5 per M), against the $0.40 hard cap.
- The ledger (1.25 × list) reads $0.3738, against its 0.48 cap.
- No other paid calls were made.

---

## 4. Go/No-Go

**No-go (pre-registered rule).** P under H is 0 of 18, below the threshold of 9 of 18. H − C is 0, below the threshold of +6.

**Per-take chance estimate.**

- The oracle structure appears in 0 of 18 treated first answers, so the point estimate is about 0.
- Rule of three: 3/18 gives a 95 % upper bound of about 17 % for that structure.
- Even if the structure appears, it would still have to resolve live. The smoke resolved 1 of 1, which is n = 1, so that probability is inferred.
- So a live retake has well under a 17 % chance of resolving 4 of 4 through the first decision. The basis is these 18 answers, at the live sampling and on the three real first-trigger frames and prompts.

**What would change the picture (owner decision; not done here).**

- Fix (b) of the campaign report, section 5.5: M3 holds every uncommanded robot whose goal lies across the corridor with a linked wait. Alternatively, the plan's `wait` legs could be honoured in legacy grounding.
- Under H, the model already writes those `wait` legs in 16 of 22 answers.
- Both options change M3 or verification code, which this cycle was not allowed to touch.

---

## 5. What a Convoy Retake Kit Would Need (Described Only; Kit and Delta Not Modified)

**Overlay.**

- Convoy runs from `runtime_delta_inert/`. Its fragment is empty, and its expectations hold the four B3 keys at their defaults (see `runtime_delta/README.md`). The shared `runtime_delta/` carries B3 and is for `ib` only.
- A retake needs a new delta directory (for example `runtime_delta_cvheld/`) whose `overlay_fragment.yaml` holds the single line `prompt_held_robot_state: true`. The `cv` profile's `DELTA_SUBDIR` would point at it; `eff_ov_dmc.sh` appends the fragment to the base overlay, and refuses a key the base already sets.
- The convoy base overlay `cvl_l2on.yaml` (`7e3ab552`) already has `plan_channel_enabled: true`: the arm check's 7th field reads `True`.
- Keep `plan_dispatch_order_source` at `chi` and the B3 keys off.

**Runtime delta.** The same five files as the current campaign delta, at the `2f83faf` md5s:

| File | Kind | Current delta md5 | New md5 |
|---|---|---|---|
| `reasoning/vlm/models.py` | live | `2025f18179c9f3b05a81072027c32637` | `52cba14c5f94b50567f1766cbcd4ff17` |
| `reasoning/vlm/prompt_builder.py` | live | `a9ad857cf8355cd9f5601124b0b814b2` | `f2f33b778360c5a0f4a6cd82b10c42b5` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` | pkg:swarm_orchestrator | `73f3fa4f35ceab61a5df646a71a902a6` | `3a0edecd4406e1174e58e4ff4639db31` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | pkg:swarm_orchestrator | `37a6bbadf91cb8c9def21d6f625c8bfe` | `71ae007388a7ddea754387479e3bf752` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` | pkg:swarm_orchestrator | `49fff7ab8fb460b9a94ea198cf5b523a` | `e65f594c0fdf1d891b54b810e4024b60` |

- The "current" column equals `git show 2f83faf~1:<path> | md5` for all five files (verified). So the new delta is the current one plus this change only.
- The new delta has a new `DELTA_ID`. `scripts/replay_live_decisions.py` changed too, but it is not runtime.
- With the key off, these files render every prompt byte-identically (tests). Moving `runtime_delta/` and `runtime_delta_inert/` to the new md5s would change their IDs too, without changing their prompts.

**Arm check.** The new directory's `arm_expect.tsv` keeps the inert rows and adds one:

- `c.prompt_held_robot_state	True`
- `c.plan_dispatch_order_source	chi`
- `c.prompt_plan_grammar_rules	False`
- `c.prompt_candidate_options	False`

The registered `want_arm` stays `True True True 0.5 config/grounding/cvl_convoy_legacy.yaml legacy True 120.0`.

**Condition gate (`cond_dmc.py` plus the `cv` `scenario.json`).**

- Replace `m5_line_absent:plan order condition` with:
  `m5_line:plan order condition plan_dispatch_order_source=chi prompt_plan_grammar_rules=False prompt_candidate_options=False prompt_held_robot_state=True`.
  That exact line is unit-tested (`test_status_line_names_it_when_on`).
- On the **first** decision artifact by scene stamp, check:
  - `prompt_conditions.held_robot_ids == ["robot_3", "robot_4"]`;
  - `prompt.user_prompt` contains the note sentence verbatim;
  - it contains `, start_pending=true` (with the leading comma and space) exactly twice, at the end of robot_3's and robot_4's state lines. The bare token appears a third time, because the note itself starts with it.
- `prompt_contains` cannot be used as is: it checks every artifact, and after the 120 s release no robot is held, so the note is truthfully absent from later prompts. This needs a new first-artifact check kind, or the gate fails.
- Every artifact must carry a `prompt_conditions.held_robot_ids` list, possibly empty, which proves the key reached M5 for each request.

---

## 6. Verified and Inferred

| Claim | Status |
|---|---|
| Held state is live M5 registry state at request time | verified (code; node unit test with a `start_delay_sec` robot) |
| Off, or with an empty list, the prompt is byte-identical; replay rebuilds the condition | verified (unit tests) |
| Unit suite delta | verified: 57 failed / 7046 passed / 151 skipped before, 57 / 7100 / 151 after, identical failing set (the 3 `pxr` collection-error files excluded both times) |
| robot_3 and robot_4 were held at all four first triggers | verified (overlay `start_delay_sec` 120; release logged 69–82 wall-s after the first dispatch) |
| Control prompts and recorded first commands reproduce | verified (4 of 4 each) |
| 0 of 44 answers ground into a four-robot sequence; H shifts the queued robots' legs to `wait` (16 of 22 against 2 of 22) | verified by running |
| Legacy grounding sequences all four when the decision names them, for either yielder | verified offline on the same snapshots |
| A retake would latch again as in takes 1–3 | inferred (same first-decision structure as the live takes) |
| A per-take chance under 17 % | inferred (rule of three on 0 of 18) |

**Known limit of the note (from code; not tested live).**

- The clause "once released, it starts driving toward its goal_x, goal_y" is exact when no coordination command owns the robot. That is the case at every first trigger here.
- When a command owns a held robot, M4's base mission does not drive it at release; it waits until the command ends. In the smoke, robot_3 was released 82 wall-s after the dispatch while on a linked wait, and it moved only when admitted.
- The wording was not changed, because that would void this check.

**Scope of the null.** It covers this one facts-only sentence, with the existing guidance unchanged. The guidance-sentence variant of fix (a) (campaign report section 5.5: "robots queued behind a standoff ... belong in `involved_robots`") prescribes roles, so the facts-only rule excludes it. It remains untested.

# A21 Churn Wave: Churn Measurement, the Last Pre-Live Gate, and the First Live ER-2 Episode on S1b

**Prepared:** 2026-10-10

**Revision history:**

- Initial draft: A21 build (churn measurement, default-off bound, A18 off-lane plan hold, two apparatus minors), the churn classification of every existing S1/S1b bundle, echo episode E5 (seed 5) and the first live Gemini Robotics-ER 2 episode E6 (seed 6) on S1b.

---

## Summary

**Headline: the first live ER-2 episode on S1b (E6, seed 6) resolved twice, never oscillated, and then clogged.** It cost an estimated $0.034 for 5 calls.

| E6 question | Answer |
|---|---|
| Decisions | 5 analyses, all parsed, 0 refusals: reverse, yield, junction_clear, reverse, yield. 3 dispatched, 2 withheld (`refusal_no_action`) |
| One cluster or both? | **One cluster, every time** (S, N, S, S, S). The model switched cluster when the stall trigger moved, and never went back and forth inside one |
| Did any plan address both clusters (the S6-in-S1 question)? | **No.** 4 plans were proposed; each had active legs in one cluster only, with every other robot on `continue` |
| Resolution | **2 productive resolutions.** The yield 83baf2e4 released on **clearance**, the first S1b release not on the 45 s backstop; passer robot_4 then reached E. A reverse later freed robot_1, which reached Wm |
| Churn class | **resolved**: 3 resolution events, 2 productive; alternation 0; resolution-time share 0.198 |
| Provenance (full parity stack) | vb 1 / repaired 2 / m3_default 2. **vb∧dispatch_matched = 1/5**, the first live one on S1b. The one mismatch is a withheld junction_clear fallback (A18 residual (2)) |
| Outcome | 4/25 tasks, partial, gridlock 173.2 rel-s, final clusters {r1, r3, r5} + {r2, r4}, 0 finishers |
| Attribution (A21(c)) | **INDETERMINATE under the pre-registered opportunity rule**: no cluster received 3 or more clearing dispatches (the most was 2). Provisional, n = 1, cross-seed. Direction: no livelock under real-model choice |

**The other results:**

- **Build.** Four items, merged into `feat/v3-integration` as `347fe99` and `3ff77ea`. Suite delta is zero: 62 / 6363 / 153 / 3 → 62 / 6435 / 153 / 3, with identical failing ids.
- **Churn table.** All 11 existing bundles classify as expected with no tuning: E3 is the only `intermittent`, A1 the only `resolved`, and the rest are `clogged`.
- **The A18 off-lane gate is closed.**
  - vb-mismatched under the legacy echo: S1a 36 → 0, S1b 13 → 1.
  - With the A21 echo, vb∧matched is S1a 0.3775 and S1b 0.455, with 0 vb-mismatched on both floors.
- **E5 (echo, seed 5).** The one-cluster echo removed E3's cross-cluster livelock by construction, but it did so by **starving** the second cluster. The echo named [r1, r5] three times and was refused three times; {r3, r4} was never analysed. Gridlock came at 28.0 rel-s with 0 tasks, class `clogged`.

PILOT-ONLY, RECORD = 0. API spend was an estimated $0.034 (E6 only), against a $1.00 cap.

---

## 1. Build (Local, Merged into `feat/v3-integration`)

| Item | Commits | What shipped |
|---|---|---|
| 1. Churn measurement (A21(a)) | `37788e3` (feat/v3-churn) | `scripts/s1_churn_stats.py`: `churn_class` plus churn metrics. It only reads bundles |
| 2. Bound, default-off (A21(b)) | `37788e3` | `swarm_orchestrator/churn.py`, the one definition both the scorer and M5 call. `churn_bound: {enabled: false, budget_k: null, window_sim_sec: null, alternation_max: null}` |
| 3. Last pre-live gate (A18 residual (1)) | `b9e0950`, `2c58aa9` (feat/v3-offlane-hold) | A plan's `cross`/`continue` leg on a robot that dispatch holds lane-scoped is repaired by `substitute` to `wait`, one edit per robot. New stratum `repaired_lane_scope_only`; MC replay committed |
| 4. Apparatus minors | `2c45b6e` (feat/v3-churn) | The echo names ONE cluster (the closest engaged pair's two members). The ambiguous-lane refusal names the 45 deg cap when the cap refused |

Merges are `347fe99` and `3ff77ea`. The suite was compared against a fresh `0b659d2` worktree, with no stash:

| Tree | Failed / passed / skipped / errors |
|---|---|
| `0b659d2` (baseline) | 62 / 6363 / 153 / 3 |
| feat/v3-churn | 62 / 6389 / 153 / 3 |
| feat/v3-offlane-hold | 62 / 6409 / 153 / 3 |
| merged `3ff77ea` | 62 / 6435 / 153 / 3 |

The failing-id set is identical in every row: environment-only failures plus 3 `pxr` collection errors. The one deliberate test edit is A20's "every latch member" echo test, re-pinned to the A21 one-pair rule.

### 1.1 Churn Definitions (`swarm_orchestrator/churn.py`)

| Term | Definition |
|---|---|
| Dispatch identity | A yield is `(yield, yielder, first passer)`. Any other clearing command is the sorted `robot:action` list of its non-wait actions. An all-wait command is not a clearing dispatch |
| Latch cluster | The identity's robots, grown by the < 0.45 m latch graph of the dispatch's own scene. Two dispatches share a cluster when their clusters intersect, so E3's alternating {r2, r5} / {r3, r5} yields fall in one cluster |
| Alternation | A-B-A completions over the identity sequence. `identity_repeats(lookback)` generalises the old check: lookback 1 is the identical-run check, lookback 2 also counts period-2 alternation |
| Resolution event | A clearing dispatch that broke at least one GT latch interval (< 0.45 m) inside its active window (dispatch to its robots' last terminal M4 status, + 2 s), on a pair that intersects its cluster |
| Productive | A robot of the cluster makes task progress (`arrived` / `dwell_complete`) after the break, before the cluster's next clearing dispatch, and within 120 s |
| `churn_class` | **intermittent**: 2 or more unproductive events. **resolved**: at least 1 productive and fewer than 2 unproductive. **clogged**: otherwise |

**The predicate was derived from E3 vs A1, then run without tuning.** A1 resolved and then progressed; E3 kept resolving without progress. The predicate is built on latch breaks, not gate events, so a reverse, reroute or convoy can count. The gate events are reported as a cross-check column.

`churn_class` is a new axis. Two existing classifiers are unchanged:

- `s1_gridlock_stats.outcome_class`;
- the v2 flow scorer's `OutcomeClass`, whose `intermittent` requires every robot to arrive.

### 1.2 The Bound (Default-Off, Values Unset)

- **Off (the default).** M5 constructs no `ChurnLedger`, logs nothing and writes no artifact key. The pinned `orchestrator.yaml` loads to the default.
- **Validation.** `enabled: true` without all three values is a validation error, and unknown keys are rejected.
- **On.** A clearing dispatch is withheld in the same way a refusal is (`dispatch_withheld.reason` `churn_budget` / `churn_alternation`, a cooldown, and the suppression arms) in two cases:
  - its cluster already used `budget_k` dispatches inside `window_sim_sec`;
  - it would push the window's alternations past `alternation_max`.
- **Not enabled in this wave.** Per A21(b), the values are to be frozen from churn data.

### 1.3 The Off-Lane Plan Hold (A18 Residual (1))

**Where the hold set comes from.** `verify_and_repair_plan` reads the final roles' `off_lane` from the same `_resolve_yield_outcome` call that the A18 identity verdict uses. It never parses the `order=lane_scoped:` tag.

**What counts as a problem.** A `cross` or `continue` leg on a held robot, whether written explicitly or produced by lenient completion.

**The repair.** The leg becomes `wait`, with the edit reason `lane_scoped hold: <id>: <cross|continue> substituted to wait; dispatch holds <id> outside the yield's lane conflict`. Dispatch is byte-identical on all 1600 MC scenes.

**The fix moves scenes out of vb, not up within it.** The fixed scenes leave vb for repaired∧matched, so vb∧matched does not rise; the closure shows up as vb-mismatched dropping to about 0.

| Floor / echo (400 MC first conflicts, scripted plan) | vb / rep / m3, before → after | vb∧matched | vb mismatched | Off-lane mismatches |
|---|---|---|---|---|
| S1a legacy (A18's convention) | 106/55/239 → 70/91/239 | 70 (0.175) | **36 → 0** | 70 → 0 |
| S1b legacy | 132/99/169 → 120/111/169 | 119 (0.2975) | 13 → 1 | 59 → 0 |
| S1a a20 echo | 122/47/231 → 122/47/231 | 122 (0.305) | 0 | 33 → 0 |
| S1b a20 echo | 154/95/151 → 154/95/151 | 154 (0.385) | 0 | 24 → 0 |
| **S1a, final tree (A21 echo)** | 151/20/229 | **151 (0.3775)** | **0** | 0 |
| **S1b, final tree (A21 echo)** | 182/72/146 | **182 (0.455)** | **0** | 0 |

**What still mismatches on the final tree:** S1a has 3 no-passer refusals (A18 residual (2)); S1b has 1 default-plan-vs-dispatch case (residual (3)).

The legacy S1a row reproduces A18 exactly (106/55/239, 36/106). The legacy S1b row differs from A18's 126/101/173 because A20(1) and A20(2) landed after A18.

**Residuals:**

- A17(v)(d), same-side pairing with an off-lane partner (S1b seeds 276 and 304), still mismatches.
- Composed swap + hold repairs (S1a 14-17, S1b 11-28 depending on the echo) fit no single-cause stratum. They need an A17-bis family ruling.
- 1 swap + 3 substitutes sits exactly on the repair bound.
- `reverse` and `reroute` legs on held robots are not flagged.

### 1.4 Apparatus Minors

**The one-pair echo.** It supersedes A20(3)'s "every latch member" rule. MC executable rates: S1b 0.6125 → 0.635, S1a 0.4075 → 0.42. **S1a echo comparability changes again.**

On E3's 10 live scenes, run as a same-scene counterfactual, it names [r1, r4] 10/10 and refuses all 10 (side by side), which closes the cross-cluster handoff path.

**The cap text.** E4's 4 handoff-arriver refusals now read: `..., and robot_1 is the node-handoff arriver, but it heads 49 deg off the pair's y bearing (beyond the 45 deg heading-lane cap); no retreat room was measured`. The `yield refused: ambiguous lane:` prefix and the tags are unchanged, so the refusal classifiers still bucket it.

---

## 2. Churn Classification of Every Existing Bundle

Definitions are those of section 1.1. "Gate" counts the pre-registered rule-4 events (gate_admit → gate_release), with the number followed by an arrival in brackets.

| Floor | Episode | outcome_class | **churn_class** | Res. events (prod/unprod) | Clearing disp. | Latch breaks (attr/all) | Disp. per attr. break | Alternations | Repeats lb1/lb2 | Longest identical run | Res.-time share | Gate (arrival) | Tasks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1a | ep1 | partial | clogged | 0 (0/0) | 0 | 0/0 | — | 0 | 0/0 | 0 | 0.0 | 0 (0) | 2 |
| S1a | E1 | partial | clogged | 1 (0/1) | 1 | 2/2 | 0.5 | 0 | 0/0 | 1 | 0.095 | 1 (0) | 1 |
| S1a | E2 | gridlock | clogged | 0 (0/0) | 0 | 0/0 | — | 0 | 0/0 | 0 | 0.0 | 0 (0) | 0 |
| S1a | A1 | partial | **resolved** | 1 (1/0) | 2 | 1/1 | 2.0 | 0 | 0/0 | 1 | 0.277 | 1 (1) | 2 |
| S1a | A2 | gridlock | clogged | 0 (0/0) | 1 | 0/0 | — | 0 | 0/0 | 1 | 0.005 | 0 (0) | 0 |
| S1a | A3 | gridlock | clogged | 0 (0/0) | 12 | 0/0 | — | 0 | 11/11 | 12 | 0.801 | 0 (0) | 0 |
| S1a | A3-rerun | gridlock | clogged | 1 (0/1) | 1 | 1/1 | 1.0 | 0 | 0/0 | 1 | 0.005 | 0 (0) | 0 |
| S1b | E1 | partial | clogged | 0 (0/0) | 0 | 0/0 | — | 0 | 0/0 | 0 | 0.0 | 0 (0) | 5 |
| S1b | E2 | partial | clogged | 0 (0/0) | 0 | 0/0 | — | 0 | 0/0 | 0 | 0.0 | 0 (0) | 1 |
| S1b | E3 | gridlock | **intermittent** | 9 (0/9) | 9 | 9/9 | 1.0 | **6** | 0/**6** | 1 | **0.914** | 4 (0) | 0 |
| S1b | E4 | partial | clogged | 0 (0/0) | 0 | 0/0 | — | 0 | 0/0 | 0 | 0.0 | 0 (0) | 5 |
| S1b | **E5** (this wave) | gridlock | clogged | 0 (0/0) | 0 | 0/0 | — | 0 | 0/0 | 0 | 0.0 | 0 (0) | 0 |
| S1b | **E6** (this wave, live) | partial | **resolved** | 3 (2/1) | 3 | 6/7 | 0.5 | 0 | 0/0 | 1 | 0.198 | 1 (1) | 4 |

**The two loop checks catch different failures.** A3's 12 identical reroutes read as identical-run 12 / alternation 0. E3's livelock reads as identical-run 1 / alternation 6. The lookback-2 repeat count catches both.

"E1, E2" in the brief is ambiguous, so both pairs are in the table: the S1a resume pair (`s1r_E1/E2`, extracted from the tgz bundles) and the S1b pilot-1 pair.

`s1b_episode_stats._wander_park` crashed on pilot ep1, whose wall-clock stagger issued tasks with no sim stamp. It now skips those tasks.

---

## 3. VM Deploy and Pre-registration

| Step | Result |
|---|---|
| Pre-registration | Rules 9 (E5) and 10 (E6) appended to `~/v3_s1b/NOTES.md` before any wave data, including the E6 attribution criteria and hard stops. Copy: `data/logs/vm_runs/churn_wave/NOTES.md` (md5 `b272be4a`) |
| Scenarios | `mapd_5_s1b_seed{5,6}.yaml` regenerated from the unchanged VM `mapd_5_s1b.yaml` (`728e58df`). Built alone, as root (`build_s56.sh`): rc 0, USD newer than yaml (`e170acf0` / `6d0ac8e7`), spawns equal the draws, validate rc 0 |
| Overlays | Rebuilt from the A20 header source (the NOTES line-107 trap), so they carry the 4 boxes. They already carry `plan_channel_enabled: true`, as E3/E4 did. Parsed on the deployed tree inside `vgu_ros`: boxes, plan channel, suppression, `refusal_no_action`, and `churn_bound` off with every value None |
| Deploy p3a (before E5) | `347fe99`, 5 files (including the new `churn.py`). Pre-image md5 OK, source / live-mount / installed OK, both packages rebuilt |
| Deploy p3b (after E5, before E6) | `3ff77ea`, `command_grounder.py` + `plan_metrics.py`. It acts only on a model-PROPOSED plan leg, and the echo proposes none, so E5 could not be affected by it |
| Pins | `orchestrator.yaml` `1f656533` (src + installed), `rag.yaml` `e18c723c`, `s1_dynamic` `66900e13`, `s1b_dynamic` `535f5281`. Untouched, RESTORE OK after every run |
| E6 hard stops | MAX_ANALYSES = 40, enforced twice: the `ep_run` sidecar, and `cost_watch.py` at the 40th analysis. The estimated-cost cap is $0.80. **Neither fired** |

---

## 4. E5: The One-Cluster Echo (Seed 5)

| Measure | E5 (`s1b_E5_seed5_echo_a1`, STAMP 20261010_113728) | E3 for comparison |
|---|---|---|
| Analyses / withheld / dispatched | 3 / 3 / 0 (199 suppressed) | 10 / 1 / 9 |
| Echo named | [r1, r5] ×3 (the closest pair, Wp, node handoff) | both clusters, 9/10 |
| Grounding | refused ×3, `no executable retreat`: r1's escort is 0.874 m, outside the [1.0, 3.5] band (×2), or no candidate survives the sweep (×1); r5 is the handoff occupant | 9 executable yields in the OTHER cluster |
| Clusters | r1+r5 at 11.5 rel-s, r3+r4 at 12.1 (SW), r1+r2 at 28.0, all permanent. Final clusters {r1, r2, r5} + {r3, r4} | {r1, r4} + the oscillating N trio |
| Churn | clogged; 0 dispatches; alternation 0 | intermittent; alternation 6 |
| Gridlock / tasks / outcome | 28.0 rel-s / 0 / gridlock | 576.1 / 0 / gridlock |

**Verdict: the one-cluster echo changed the E3-class dynamic, but only by starving the second cluster.** It removed the cross-cluster handoff path, as predicted: 0 yields outside the named pair. It replaced that path with starvation:

- The closest pair was unresolvable, so it was refused every time.
- The scene did not change, so it stayed suppressed.
- The second cluster {r3, r4} was therefore never analysed in 600 sim-s.

**This is a new apparatus finding.** One-cluster naming combined with scene-unchanged suppression has no way to move on to the other cluster.

**First-conflict prediction.** The MC first encounter (r1+r5 at 10.5) held live (11.5). The MC echo named [r3, r4] → executable, while live it named [r1, r5] → refused. First-conflict yields across all pilots are now 0/5 live against 4/5 MC.

---

## 5. E6: The First Live ER-2 Episode on S1b (Seed 6) — Headline

**Run.** `s1b_E6_seed6_er2_a3`, STAMP 20261010_123811, tree `3ff77ea`.

**Model.** `gemini-robotics-er-2-preview`, `thinking_level: low`, no sampling parameters sent.

**Bring-up.** Attempts 1 and 2 were Nav2 bring-up aborts, both clean with $0 spent:

- robot_4 `bt_navigator` get_state failure;
- robot_3 `controller_server` bond timeout.

**Gates.** GATE OK, RESTORE OK, 0 tracebacks. `diagnostics.backend_id` was gemini on 5/5; parse valid 5/5; 1 attempt each; 0 refusals.

### 5.1 Per-Analysis Decisions

| # | sim-s | Model decision | Plan (provenance) | M3 / M5 outcome | Result |
|---|---|---|---|---|---|
| 1 | 34.6 | reverse r1+r3 (S: "head-on, 0.31 m") | 1:reverse 3:reverse, rest continue (**vb, matched**) | dispatched r1, r3 reverse | both FAILED; the latch broke for about 4 s; unproductive |
| 2 | 75.7 | yield r4 ("previous reverse failed", N) | 4:yield 2:cross → **repaired** (1 swap: room gate, r4 0.68 < 0.74 m), matched | dispatched r2 yield (node handoff) | **EXECUTED YIELD**: gate_admit 108.1 → release 134.5 on **clearance**; r4 reached E at 149.9, r2 reached Wp at 152.4. **Productive** |
| 3 | 134.2 | junction_clear r1/r3/r5 (S) | 3:reverse 1:yield 5:cross → **repaired** (2 substitutes), **mismatched** | junction_clear fell back (no candidates, `shipped_unsolved` geometry) → derived yield refused `no feasible yielder (0.00 m ×3)` → **withheld** | — |
| 4 | 156.9 | reverse r1/r3/r5 (S), no `proposed_plan` | **m3_default** (plan absent), matched | dispatched r3 + r5 reverse (node handoff r3 → r1) | r5 COMPLETED, r3 FAILED; latches broke; r1 reached Wm at 177.3. **Productive** |
| 5 | 197.9 | yield r1 to r5 (S) | 1:yield 5:cross → **m3_default** (`plan unrepairable: no shared lane`), matched | refused, side by side 47 deg → **withheld**, then suppressed to H | — |

### 5.2 The Questions the Brief Asked

**Does a real model name one cluster, both, or oscillate?**

- It named one cluster in 5/5 analyses.
- It followed the stall trigger between clusters (S → N → S → S → S). That is never a back-and-forth inside one cluster.
- The justifications cite the failure context ("previous reverse failed") and switch strategy accordingly: reverse → yield, then reverse → junction_clear → reverse → yield.

**Does any plan address both clusters (the S6-in-S1 question)?** No. Each of the 4 proposed plans has active legs in one cluster and `continue` everywhere else. Analysis 4 proposed no plan at all.

**Provenance with the full parity stack:**

| Provenance | Count | Notes |
|---|---|---|
| vb | 1 | matched |
| repaired | 2 | one is a room-gate swap, matched; one is the junction_clear substitutes, mismatched |
| m3_default | 2 | both matched |

- **vb∧dispatch_matched = 1/5**, the first real-world value on S1b.
- The one mismatch is A18 residual (2): a non-retry refusal (the junction_clear fallback) where the plan keeps an active `reverse` leg against all-wait dispatch, and that dispatch was then withheld.
- The off-lane hold was not exercised: 0 lane-scoped commands.

**Resolution and churn:**

- 3 clearing dispatches, 7 latch breaks (6 attributed), 3 resolution events (2 productive).
- Alternation 0; resolution-time share 0.198. Class **resolved**, against E3's intermittent and E5's clogged.
- The clearance release of 83baf2e4 is the first S1b yield not released by the 45 s backstop.

**Tasks and finishers (wandering vs park):**

- 4/25 tasks (r4 E; r2 Wp then N; r1 Wm); 0 finishers.
- 3 occupied-node arrivals, none with a finisher as occupant.
- Tail gridlock: last progress at 182.3 sim-s.
- Gridlock 173.2 rel-s; final clusters {r1, r3, r5} + {r2, r4}.
- 6 of the 7 latch breaks fell inside a dispatch's active window. The seventh is a 3.4 s r1+r3 encounter at 185.5-188.9 sim-s, just after r1 left its Wm dwell: a contact while moving, not a static latch freeing itself. Robots also made small motions (> 3 cm) out of static runs while still latched.

**Cost:**

- 5 billed calls, an estimated **$0.0335** in total. Each call was about 3.1-3.5k prompt tokens (including 1064 image tokens), 0.3k completion and 0.2k thought.
- The estimate uses the published ER-2 rate (input $1/1M, output + thought $5/1M); this billing basis is not confirmed for this model.
- One stage-2 retreat call timed out (`degraded`) and recorded no usage.

### 5.3 Attribution (A21(c), Pre-Registered Criteria, PROVISIONAL)

**Verdict: INDETERMINATE.** The opportunity rule needs at least 3 clearing dispatches into one cluster. E6 had at most 2 (the S cluster) before the episode clogged on refusals and suppression.

**What E6 does show, at n = 1 and cross-seed:**

- Under real-model decisions there was **no alternation** and the episode classifies **resolved**.
- The model's cluster choice matches the one-cluster echo's shape. In the same-scene echo counterfactual on E6's scenes, the echo names the same cluster 5/5, and the subset pair 3/5.
- So nothing here points to architecture-churn.
- The E3 livelock has **not reproduced** under either the corrected echo (E5) or the real model (E6).

**Why this is not an apparatus verdict.**

- E5's echo never got an opportunity to churn either, so the comparison is not discriminating.
- On E6's scenes, the echo counterfactual would have dispatched an executable yield in 4/5 scenes, where the model chose reverse, junction_clear, or a yield that was refused.
- The two decision sources therefore differ more in **strategy** than in cluster choice.

---

## 6. Findings for the Owner / Step 6

1. **The livelock did not recur.** It is gone under both the corrected echo and the real model, but neither run had the opportunity the pre-registered rule needs. The A21(b) bound has nothing to be frozen from yet: productive-resolution counts now exist only for A1 (1) and E6 (2).
2. **Echo starvation (new, apparatus).** One-pair naming plus scene-unchanged suppression never reaches a second cluster when the closest pair is unresolvable (E5: {r3, r4} never analysed in 600 sim-s). This is a cell-design choice for echo arms. Options: rotate the named pair on suppression, or name the trigger's cluster.
3. **Under ER-2, junction_clear on S1b falls back to legacy grounding.** The geometry is `shipped_unsolved` (`junction_recede_offset_m`, `junction_backup_clearance_m` missing). The result is a `no feasible yielder (0.00 m ×3)` refusal and a mismatched repaired plan.
   - This is the A18 residual (4) domain, live.
   - It is also a 0.00 m reading of the kind A16 eliminated on the yield path.
4. **The model mostly does not yield.** Of 5 analyses: reverse ×2, junction_clear ×1, yield ×2. The derived echo yields wherever it can. Any S1b arm comparison has to read **strategy mix**, not just cluster choice.
5. **The first productive S1b resolution came from a real model.** The ER-2 yield (after an M3 swap) released on clearance, and both robots reached their nodes. The headline invariant held: vb∧matched 1/5, with no raw-vb claims.
6. **Bring-up reliability.** 2 Nav2 aborts in a row on E6, with stagger 6, were each a different known class (bond timeout, get_state). That makes 2 aborts in 4 launches this wave.

---

## 7. VM End State

- **Power and processes.** RUNNING, idle (13:38Z). No run_simulation, fc_launch, ep_run, chain, live_watch, cost_watch, Kit or bag processes. GPU 0 %, 136 MiB. `vgu_ros` is up.
- **Configs.** `orchestrator.yaml` `1f656533` (src + installed), `rag.yaml` `e18c723c`, `s1_dynamic` `66900e13`, `s1b_dynamic` `535f5281`.
- **Hygiene.** PAUSE and STOP_CHAIN are absent; no leftover GT directories; 0 root-owned files under `~/v3_s1b`, `m5_decisions` or `m5_scene`.
- **Tree.** The previous tree plus the `347fe99` and `3ff77ea` runtime deltas. Pre-images are in `~/v3_s1b/p3/deploy{,_b}/pre`.
- **New VM-only files.**
  - `mapd_5_s1b_seed{5,6}` yaml + USD;
  - `overlays/s1b_orch_seed{5,6}.yaml`;
  - `chain_p3.sh`;
  - `~/v3_s1b/p3/*`.
- **Notes.** `~/v3_s1b/NOTES.md` md5 `b272be4a`, copied to `data/logs/vm_runs/churn_wave/NOTES.md`.
- **Bundles.** `data/logs/vm_runs/churn_wave/` (gitignored), together with the VM kit scripts.
- **API.** An estimated $0.034.

---

## References

- Spec: prereg-v3 A18-A21 (`feat/v3-design`, `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`).
- Prior report: `docs/reports/2026-10-10-s1b-pilot2.md` (E3's livelock, the A20 echo/handoff interaction).
- Code:
  - `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/churn.py`, `models.py` (`ChurnBoundConfig`), `orchestrator_node.py` (`_churn_check`);
  - `reasoning/rag/command_grounder.py` (`_plan_dispatch_outcome`, `_plan_off_lane_holds`, `LANE_SCOPED_HOLD_PREFIX`), `plan_metrics.py` (`repaired_lane_scope_only`);
  - `reasoning/vlm/mock_backend.py` (`echo_select`), `reasoning/rag/grounding_view.py` (`_heading_lane_cap_blocker`).
- Scripts: `scripts/s1_churn_stats.py`, `scripts/plan_parity_mc_replay.py`, `scripts/s1b_live_replay.py`, `scripts/s1_gridlock_stats.py`, `scripts/s1b_episode_stats.py`.
- Tests: `tests/unit/test_churn_a21.py`, `tests/unit/test_plan_offlane_hold.py`.

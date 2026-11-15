# Session Wrap-Up, 13–15 November 2026

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: index of every result produced on 2026-11-13..15 (where it lives, evidence grade, caveat), safety-mechanism status, branches and worktrees, deliverables, budget, open owner decisions, and placeholder blocks for the two jobs still in progress.

---

## How to Read This Document

- **What it is.** An index. Every number is quoted from the source named in the same row; the source is the record. Nothing was re-run for this page except read-only git commands, `du`, `md5` and the campaign ledger's `status` command.
- **Snapshot.** Git facts and the ledger were read at 2026-11-15T13:49Z. Two jobs were still running (section 8); their outcomes are left as `[[PENDING: …]]` blocks.
- **Evidence grades used here:**
  - *registered pilot*: the analysis plan was fixed before the runs; such runs are never pooled with later exploratory runs;
  - *exploratory live*: a closed-loop simulation run (Isaac Sim) with the real model, small n, analysis not fixed in advance or fixed only for that run;
  - *illustrative demo*: a single recorded take chosen to show the pipeline; never a rate;
  - *offline replay*: recorded decisions or poses re-processed by code, with no new simulation;
  - *code reading*: established by reading the source.
- **Everything is simulation** unless marked.

### Names Used in This Document

The canonical naming glossary is `docs/guides/naming_glossary.md` on `demo/campaign-kits`, written by another job and checked against the thesis's own names. At the time of writing it existed only as an uncommitted draft in the v7j worktree; the names below were aligned with that draft (for example "central layer", not "coordination layer", and "registered as confirmatory" only for the 21 October five-robot pilot). **The glossary supersedes this table** once committed.

| Name in this document | Internal ids (repo) |
|---|---|
| Four-robot intersection | `intersection_bottleneck`, IB10, `ib`, labels `ibD`/`ibS`/`ibL` |
| Four-robot convoy counterflow scene (two robots queued behind a head-on pair) | convoy counterflow, `convoy_counterflow_slip`, `cv`, labels `cvD`/`cvH`/`cvL` |
| Two-robot head-on corridor with obstacle | `head_on_asymmetric_w0p2_eopen_bshort_o0`, head-on family, `ho`, `hoD` |
| Five-robot pickup-and-delivery scene | `mapd_5_s1b`, S1b, `m5`, `m5D`/`m5V`, episodes E6–E31 |
| Intersection run 1: central layer on vs off (13 Nov) | IB10 live resolution, Arm A vs Arm B |
| Intersection run 2: live VLM vs scripted default plan (14 Nov) | IB10 safety default arm, Arm A vs Arm C |
| Registered five-robot pilot (21 Oct; 10 episodes, registered as confirmatory) | prereg-v3 tranche 1, `batch6`, E27–E31 Arm A / Arm B |
| Exploratory five-robot pilots (10–17 Oct; 21 episodes) | E6–E26: `batch2`–`batch5`, `live_batch`, `resume`, `churn_wave` |
| Demonstration campaign, demonstration takes (14–15 Nov UTC) | demo campaign (`demo_campaign/`); "take N" as in the reports |
| Five-robot validation take | `m5V_t01_a1` (kit `m5v`) |
| Scripted safety tests | kit `sft`, branch `test/safety-mechanisms-scripted` |
| Earlier recorded head-on run (30 Sep) | ER2LIVE, bundle `ER2LIVE_20260930_152222` |
| Head-on re-score (recorded September runs) | `docs/head-on-vlm-vs-rule` re-score |
| Offline prompt replay: robot labels swapped | swapped-ID replay |
| Offline prompt replay: answer format changed to JSON only | JSON-only replay |
| Offline prompt replay: clearer image annotation | improved-annotation replay |
| Plan-order prompt check (offline) | `vlm-order-channel-plan-check` (prompt variants A, B, A3, B3) |
| central layer on / off | Layer 2 on / off (Arm A / Arm B) |
| scripted default plan, no model call | Arm C |
| perception (M1), VLM reasoning (M2), grounding and plan verification (M3), execution and safety monitor (M4), orchestrator (M5) | M1–M5 |
| Gemini Robotics-ER 2 (the VLM), "ER-2" | `gemini-robotics-er-2-preview` |
| plan accepted unchanged / repaired / grounder default | `vlm_verbatim` / `repaired` / `m3_default` |
| failure unit | one unresolved conflict or stalled robot at the end of an episode (FU) |
| cause classes: decision, grounding and verification, execution, environment geometry, undetermined | V, G, X, EG, U |
| escort obstacle guard / reverse obstacle guard / stall abort / geometric contact logging / queued-robot hold / plan-dispatch mismatch record / safety-exemption scope fix | keys in section 3 |

**Other shorthand kept for traceability** (each stands for exactly this):

- **Episode and take ids.** `E6`–`E31` are five-robot episodes (E27–E31 the registered pilot, E6–E26 the exploratory pilots); `e01`–`e10` are intersection-run episode slots (for example `e09`); `E18 1feb2c4e` is an episode id plus a decision (request) id.
- **Prompt variants A, B, A3, B3** of the plan-order prompt check, defined in that report (sections 4 and 10); B3, the variant the live intersection takes used, is B plus the release sentence and the candidate-options block.
- **Designs D1, D1+C, D2:** candidate post-fix five-robot comparisons (same seeds, same seeds plus a scripted arm, fresh seeds; rubric report 8.3).
- **P1–P5:** the five exemption paths traced in the safety-exemption work; the fix covers P1–P3.
- **"The gate":** the yield feasibility gate, which replaces a named yielder that has no room to back up. **"Latch":** M4's 0.45 m proximity stop.
- **W** is `fix/deadlock-collision-resolution`, the main working branch; **the pin** is commit `68e67b5` (`feat/v3-integration`), the code every November run deployed.

---

## 1. Bottom Line for the Thesis

In simulation, the full central layer (congestion trigger, a call to Gemini Robotics-ER 2, grounding and plan verification, phased dispatch) cleared a four-robot intersection jam that the robots' local control alone never cleared (4 of 5 episodes against 0 of 5), but a scripted arm that skipped the model call and ran the grounder's default plan cleared it as well (4 of 4 valid, 5 of 5 after a post hoc re-run) with the same executed plan; these are exploratory pilots, not independent samples. ER-2 returned a valid, parseable decision in all 67 demonstration analyses, but its plan was accepted unchanged in 6 of 65 plan-channel analyses (5 once a dispatch that contradicted the plan is not counted as accepted), and it changed the executed commands relative to the default once, by swapping the order of two near-equivalent back-out manoeuvres (a 0.010 m difference against a 0.15 m tolerance). In the two-robot head-on corridor the grounder's feasibility gate, not the model, made the executed yielder correct (79 of 79 runs, 37 model choices overturned), and pre-registered offline replays found no model that chose the yielder from the scene rather than from labels or listing order. The evidence does not support that the VLM improves outcomes, uses the image, or that the pipeline handles congestion outside the intersection: the four-robot convoy was unresolved in 5 of 5 takes and the five-robot take resolved 1 of 5 robots. A two-rater failure-cause classification of the five-robot runs names no dominant cause and leaves a large share undetermined (registered pilot 12 of 18 units, of which 10 of 10 in the central-layer-off arm for lack of a clock anchor and 2 of 8 with the layer on; exploratory pilots 13 of 33). Safety evidence is robot-pair centre distance plus an offline geometric recompute; one sustained robot-obstacle contact was confirmed, obstacle contacts also came from reverse manoeuvres in October runs, and the mechanisms built to stop them are validated offline only (live validation in progress, section 8).

Sources: thesis evidence register (v6d `docs/reports/2026-11-13-thesis-evidence-register.md`, "VLM Contribution", Recommended Thesis Wording 1–6, updated 2026-11-15 in Rev 8) and the rows of section 2.

---

## 2. Results Table

Short source names: `DC` demo campaign results (v7j `docs/reports/2026-11-15-demo-campaign-results.md`, last commit `4cacf55`); `REG` evidence register (above). Every other source is named in full.

| # | Result (n) | Grade | Source (path, section, commit) | Caveat that must travel with it |
|---|---|---|---|---|
| R1 | Intersection run 1: central layer on resolved 4/5 (16/20 arrivals), off 0/5 (0/20); attribution 4 repaired, 1 grounder default, 0 plan accepted unchanged | registered exploratory pilot, n = 5 per arm | v7a `docs/reports/2026-11-13-ib10-live-resolution-results.md`, results; `5f098b7` | One scene, about three near-repeat trajectories: not independent samples, no p-value. Supports "the pipeline clears the jam", not "the VLM's plan clears it" |
| R2 | Intersection run 2: VLM arm 5/5 (mean 115.96 s from onset); scripted default plan, no model call 4/4 valid (mean 117.80 s), 5/5 after a post hoc re-run (mean 117.86 s); every VLM-arm first dispatch re-grounds to exactly the scripted plan | exploratory pilot, n = 5 per arm | v7d `docs/reports/2026-11-14-ib10-safety-default-arm-results.md`, "Plan equality", re-run addendum; `dead48d` | Cite both scripted-arm figures. The scripted arm was handed strategy and robot set; it dispatches about 3.4 s later. Never pooled with experiment 1 |
| R3 | Safety-exemption scope fix (M4 safety fix): key-off exemption timelines identical to the pinned tracker in 68/68 bundles (673 changes); key on loses 6 exemptions (1 in experiment 1 e09, 5 in older sets); armed live in experiment 2 and never fired (all counters 0) | offline replay; unit tests (64); live armed, not exercised | v7c `docs/reports/2026-11-14-safety-exemption-fix.md`, Replay Regression, Open Items; `8933863`; REG row "IB10 safety smoke" | A what-if on trajectories recorded under key-off behaviour; not a live validation |
| R4 | Head-on re-score (recorded September runs): the VLM's yielder correct, gpt-4o west 5/23, east 10/12; ER-2 west 12/30, east 11/13; never above the better trivial baseline; with the feasibility gate on, the executed yielder was correct in 79/79 runs, 37 of them model picks overturned | post hoc re-score of pilot data | branch `docs/head-on-vlm-vs-rule` `docs/reports/2026-11-14-head-on-vlm-vs-rule-rescore.md`, Headline, lines 185–222; `1f77bf1` | Not pre-registered; the gate column is derived from artifact fields, not checked against M4 logs |
| R5 | Plan-influence trace: the model's plan changed dispatch in 0 of 39 gated four-robot analyses; 14 plans accepted unchanged, 8 dispatched as written | offline replay (trace; each claim labelled verified/inferred) | v7i `docs/reports/2026-11-15-vlm-plan-influence-trace.md`, Answers, B, D, E; `1400533` | The order-dispatch flag was never on in those runs; the model's decision fields changed execution against the scripted default in 18 dispatches in 4 episodes, and where judged (2 episodes) the outcome was worse |
| R6 | Plan-order prompt check (offline), ER-2: plan accepted unchanged A 2/40, B 2/40, A3 6/40, B3 14/29; first-trigger "demo event" A 0/38, B 1/38, A3 0/38, B3 7/27 | offline replay, pre-registered cycles | v7j `docs/reports/2026-11-15-vlm-order-channel-plan-check.md`, sections 4, 10.3; `7586857` | One scene, near-identical snapshots. Shows control over the back-out order, not a better order; order biased toward ascending robot id (inferred) |
| R7 | Offline Sonnet 5.5 check (B3 prompt): 16/16 valid, 11 accepted unchanged, 1/15 first triggers would qualify as VLM-driven (yielder gap) | offline replay, pre-registered (`b103ff4`) | same report, section 11; `DC` 3.4–3.5 | No Sonnet live take was run (no-go) |
| R8 | Four-robot convoy, held-robot state in the prompt: 0/18 primary and 0/22 answers per condition grounded into the four-robot sequence (44 calls) | offline replay, pre-registered | v7j `docs/reports/2026-11-15-convoy-held-robot-prompt-check.md`, sections 2–4; `4d6f057` | A prompt-only fix is a no-go; no retake was run on it |
| R9 | Offline prompt replays on scene use (14 Nov): robot labels swapped: no model meets the pre-registered rule, gpt-4o follows the first-listed slot 85/96; answer format changed to JSON only: Sonnet answered 146/146, correct yielder 46/96 in the grey pair, ER-2 not assessable; clearer image annotation: every verdict not assessable (provider limits), ER-2 lead 55/67 | offline replay, pre-registered | swapid `docs/reports/2026-11-14-head-on-swapped-id-replay-results.md` (`bc26ae0`); jsononly `docs/reports/2026-11-14-head-on-json-only-replay-results.md` (`29696f9`); swapid `docs/reports/2026-11-14-improved-annotation-replay-results.md` (`abc28fe`) | Two robots, first decision only, nothing executed. The 55/67 lead is not evidence of image use |
| R10 | Demonstration takes, four-robot intersection: 5 valid takes (1 bring-up abort); take 1 unresolved (3/4 arrived), takes 2–4 grounder-default resolution, take 5 VLM-driven execution (4/4): plan accepted unchanged, back-out order robot_3 → robot_4 against default robot_4 → robot_3 | illustrative demo | `DC` sections 1–2, 7; Final Summary | Take 5 is a near-tie (0.010 m against 0.15 m tolerance); only the timing of two back-outs changed; chosen for its label; 1 of 5 takes |
| R11 | Demonstration takes, four-robot convoy: 5 takes, all unresolved. Takes 1–3: 0/4 arrived; the model named only the head-on pair, the two queued robots (never commanded) followed through and latched; 33 later proposals ran as 8 s waits. Takes 4–5 with the queued-robot hold: 1/4 arrived each; the hold kept the queued robots as designed, but the model chose robot_1 as yielder both times and robot_2's escort latched 0.418/0.419 m from the held robot_3 | illustrative demo, n = 3 + 2 | `DC` sections 5, 12; Final Summary | Two separated causes: uncommanded queued robots (takes 1–3, fixed by the hold) and the yielder choice (takes 4–5, the scene's latching variant). n = 2 for the hold: no rate |
| R12 | Demonstration take, two-robot head-on corridor: resolved 2/2 by the default plan (grounder-corrected): the gate swapped the model's yielder robot_1 (0.70 m retreat room < 1.08 m) to robot_2 | illustrative demo, n = 1 | `DC` section 6 | The model's first strategy (`reverse`) ran and did not clear the scene |
| R13 | Demonstration take, five-robot pickup-and-delivery scene: 1/5 arrived; 2 of 8 decisions executed as named, 6 withheld by grounding refusals; decision 2's escort drove robot_3 into rack island `obstacle_2` (within 5 mm in 4526 of 4534 ground-truth rows from sim 146.7 s) | illustrative demo, n = 1; contact by offline recompute | `DC` sections 8, 8.7 | "Unresolved" partly reflects an escort path error (no obstacle check on that path), not only the model or the refusals |
| R14 | Earlier recorded head-on run (30 Sep): the model named robot_2 as yielder, the gate kept it, executed, 2/2 arrived | illustrative demo, n = 1 | `DC` section 11 | Selected because it qualifies; older code `3959d7f`; escort and Nav2 recovery are the system's; the stage-2 pick was the first of two mirror-equivalent options |
| R15 | Demonstration three-way count: valid response 67/67; plan accepted unchanged 6 of 65 plan-channel analyses; changed executed behaviour 1 (intersection only). Corrected by the mismatch definition: 5 accepted (raw reading 3, motion-only 6); the drop is convoy take 2's `759bdb94` | illustrative demo; corrected count by offline recompute | `DC` Final Summary (Rev 11); v7r `docs/reports/2026-11-15-plan-dispatch-mismatch-visibility.md` section 6.3; `93655fc` | The denominators differ: `DC`'s 65 counts the 4 intersection "no congestion" answers; v7r's plan-block decisions are 61 (ib 5, cv 36, m5 8, convoy takes 4–5 12). The validation take is outside both |
| R16 | Plan-dispatch mismatch: `reverse` and `reroute` are grounded from `involved_robots`, never from the plan; 10 of 33 reverse legs (7 commands) went to robots whose plan was not `reverse`; 3 of 3 reroutes disagree; 15 "silent" accepted-unchanged decisions, of which 9 are overridden under the new definition. Corrected accepted-unchanged counts per series: intersection takes 1, convoy takes 1–3 2, five-robot take 2, five-robot validation take 0, convoy takes 4–5 0; registered five-robot pilot 1 of 2 recorded; October series in v7r table 6.1 | code reading; offline recompute (fidelity gate 0 failures on 269 exact rows) | v7j `docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md` Part A, sections 1–4 (`b70d925`); v7r report sections 1, 6.1–6.2 (`93655fc`) | The registered pilot's row is a recomputation beside the registered result, not a rescore. The record is behind a default-off key; no prompt or grounding change was made |
| R17 | Ground-truth contact fields were hard-coded empty; offline recompute over 44 bundles: 1 sustained robot-obstacle contact (five-robot take, robot_3), 2 brief grazes within noise, no robot-robot footprint contact (closest 82.1 mm); positive control recovered | offline replay (geometric footprint, 10 Hz) | v7m `docs/reports/2026-11-15-gt-contact-logging.md` section 5; `b5eaee5`; `DC` 10.2 | Footprint proximity, not physics contact. Robot gap figures differ slightly from `DC` 8.7.2 (−0.2 mm vs −0.16 mm; E30 graze 1.2 mm vs 0.97 mm) |
| R18 | Five-robot validation take (five-robot pickup-and-delivery scene, escort obstacle guard on, geometric contact logging on): contact fields on 6001/6001 rows, all reproduced exactly offline; no contact event; closest obstacle approach 5.5 mm under a VLM-named `reverse`; no escort was grounded, so the escort guard never fired; 2/5 arrived | exploratory live, validation only, n = 1 | v7n `docs/reports/2026-11-15-validation-guard-contacts-results.md` sections 1–5; `a412949` | Verdicts: contact logging "partially validated" (no live contact occurred; builder-parity test not run); escort guard "validated as armed and harmless only" |
| R19 | Escort obstacle guard, offline replay: refuses five-robot take decision 2 (`a15f3fc5`, clear 0.414 m) and October E18 `1feb2c4e`; every other campaign escort unchanged; of 24 October escort commands only E18 changes. Of the 2 refusals, 1 justified (contact), 1 untested (never drove) | offline replay; 33 test functions | v7l `docs/reports/2026-11-15-escort-obstacle-guard.md` section 4; `DC` 10.1; v7q reconciliation 7.2 | Declared obstacles only; no M4 backstop; the E18 margin rule awaits the owner. `DC` 8.7.4 counts 19 admitted October escorts (a different scope from the 24 commands) |
| R20 | Reverse obstacle guard, historical replay: 17 dispatched reverses with declared obstacles; 14 refused: 10 justified (8 contact, 2 sub-margin graze), 3 untested, 1 false positive (1/14 = 7 %, at most 4/14); robot level 6 of 17 blocked legs false positives (35 %). In October runs 10 of the 14 refused commands had a leg FAILED live, 7 pinned on an obstacle face until the 195 s deadline | offline replay; 25 test functions (29 cases) + 2 node tests | v7l report section 8 (8.5, 8.6); `92158d3` | Criterion: only the 0.05 m threshold was fixed before the gaps were printed. Shows reverses drove into obstacles in October runs; does not show a refusal would have resolved the scene |
| R21 | Stall abort, offline replay of 221 raw-velocity primitives (48 bundles): fires on all 10 contact stalls, 2.3–3.0 sim-s after contact; 0 of 191 contact-free completed primitives fire; 2 completed primitives in contact would end FAILED; 19 of 21 silent live failures were held by the safety latch | offline replay (reconstructed commands); 79 test functions | v7p `docs/reports/2026-11-15-m4-stall-abort.md` sections 6.2–6.4; `1016e0b` | The reconciliation recompute covers a narrower set (100 primitives in 25 central-layer-on bundles, 10 fires), with identical lines to its provisional column. Stale-odometry abort has no live evidence |
| R22 | Failure-cause classification, five-robot runs: 55 failure units in 33 episodes, two raters; undetermined share registered pilot 12/18 (coordination on 2/8, off 10/10), October pilots 13/33, November takes 2/4; agreement on the final code 50/55 (kappa 0.895), class 53/55 (kappa 0.948), round 1 32/55; no class leads in both raters and after reconciliation in every stratum, so no dominant cause is stated | registered rubric (frozen `b70d925`), exploratory post hoc coding | v7q `docs/reports/2026-11-15-failure-cause-reconciliation.md` sections 1, 2, 4.1–4.3, 6; `a1bcf53` | Strata never pooled. Rule properties shape the result: the environment-geometry codes cannot fire at onset (the decision-substitution test (T1) motion set is never empty), the coordination-off units lack a clock anchor, 15 units fail the decision-substitution-test fidelity gate. The clock mapping failed its pre-declared test and is not applied |
| R23 | Interception table (would escort guard, reverse guard or stall abort have acted on a linked leg?): registered pilot 0/8 units; October pilots 9/33 intercepted (5 with a justified leg), 24 none applies; November takes 1/4 (2/4 under the persistent-state link (sensitivity analysis)). Legs, October pilots: reverse guard refuses 29 (9 justified, 15 false positive, 5 untested, counting co-refused legs) | offline replay | v7q reconciliation section 7; `a1bcf53` | Says what would have been refused or aborted, not that the scene would then resolve. None of the three mechanisms is validated live as firing |
| R24 | Queued-robot hold, offline replay: 46 of 46 first-trigger yields ground into the four-robot sequence; 33 later convoy and 15 other-scenario decisions unchanged | offline replay; 51 tests (report) | v7o `docs/reports/2026-11-15-convoy-hold-queued-robots.md` Summary, sections 5–6; `d85d1ed` | Per-take chance of a resolving first sequence about 2/3 (model picks robot_2 in 12/18) times an unmeasured live success rate; live result is R11 takes 4–5 |
| R25 | Errata issued 2026-11-15 to older reports: contact wording (v7d `f30869e`, `04a1956`; v7a `88aad36`, `3cb947e`; v6d `b534d17`; v7j `d076a54`, `7586857`); model-plan statements (v7a `5f098b7` e09, v7d `dead48d` e03, mirrored on v7j `41f1e13`); `DC` Rev 8 exception-row span 266.5–268.0 s; `DC` Rev 10 hard-floor metric (centre distance 0.2643 m, not 0.186 m body gap) | docs only | `DC` 8.7.6, 10.2, 11.5; commits listed | No number or verdict changed by the errata |
| R26 | Read-only audit count: about 110 decisions in 71 recorded bundles dispatched without swap, repair, substitution or default | unverified | `DC` 11.4 | Parts do not reconcile (ER-2 79; reverse 41 + yield 40 = 81 of about 110); cite only as an unverified audit count |

---

## 3. Safety Mechanisms Status

Owner rule: every new safety mechanism stays default-off, and they are enabled one at a time; the first validation run of a new mechanism does not enable it together with other new mechanisms (v7p report, Scope).

| Mechanism | Branch (worktree) | Key, default | Tests | Offline replay | Live status | Known limits |
|---|---|---|---|---|---|---|
| Safety-exemption scope fix (M4) | `fix/safety-exemption-scope` (v7c) | `safety.scoped_clearing_exemption`, off | 64 | 68/68 key-off identity; key on loses 6 exemptions | armed in intersection run 2, never fired | Third-robot path only; P4/P5 out of scope |
| Escort obstacle guard (M3) | `fix/escort-obstacle-guard` (v7l) | `grounding.escort_obstacle_guard`, off | 33 functions (35 cases) | refuses 2 (1 justified, 1 untested) | armed once (five-robot validation take), never fired | declared obstacles only; legacy grounding not covered; E18 margin rule open |
| Reverse obstacle guard (M3) | `fix/escort-obstacle-guard` (v7l, §8) | `grounding.reverse_obstacle_guard`, off | 25 functions (29 cases) + 2 | 14 of 17 refused; 10 justified, 3 untested, 1 false positive | never run live. [[PENDING: SFT-1 — scripted safety test verdict for the reverse obstacle guard]] | refuses, does not shorten; refusal dispatches 8 s waits; square-corner and open-arm over-approximation |
| Stall abort (M4) | `fix/m4-stall-abort` (v7p) | `safety.stall_abort.enabled`, off | 79 functions | 10/10 contact stalls, 0/191 false fires | never run live. [[PENDING: SFT-2 — scripted safety test verdict for the stall abort]] | raw-velocity primitives only; latch-held robots never judged; `input_stale` untested live |
| Geometric contact logging (simulation) | `feat/gt-contact-logging` (v7m) | none: always on | 54 | 44 bundles recomputed | partially validated (five-robot validation take: fields 6001/6001; no live contact). [[PENDING: SFT-3 — whether the scripted tests produced a logged contact entry]] | not default-off (changes ground-truth rows); footprint proximity, not physics contact; builder-parity test never ran |
| Queued-robot hold (M3) | `fix/convoy-hold-queued-robots` (v7o) | `grounding_hold_queued_crossers`, off | 51 (+ gate-mode tests at `d85d1ed`) | 46/46 yields become the four-robot sequence | used in convoy takes 4–5: worked as built, both takes unresolved | legacy corridor yield only; inert in derived grounding |
| Plan-dispatch mismatch record (M5/M3) | `fix/plan-dispatch-mismatch-visibility` (v7r) | `plan_dispatch_mismatch_visibility`, off | 48 | 0 fidelity failures on exact rows | never run live | logging only; prompt still shows wrong leg statuses; full unit suite not run (swap floor) |

The scripted safety-test branch (`test/safety-mechanisms-scripted`, v7s) merges the escort and reverse obstacle guards, contact logging and the stall abort; whether its takes enable them one at a time is part of placeholder SFT-4 (section 8).

---

## 4. Branches and Worktrees

Read-only snapshot at 2026-11-15T13:49Z (`git worktree list`, `git log -1`, `git status --porcelain`, `git show-ref refs/remotes/origin/<b>`; no fetch). "Pushed": no branch in this table has a local remote-tracking ref, so all are **unpushed**. The three earlier v4 branches outside this table do have remotes (as of the last fetch): `feat/v4-gf-cluster` `c16b1a7` 0/0, `feat/v4-vlm-bench` `7850f5a` 0/0, `feat/v4-per-cluster` `48234f2` ahead 1 (Stage 7, unchanged since the plan). Stage numbers refer to the consolidation plan (v7j `docs/superpowers/plans/2026-11-15-branch-consolidation.md`, section 3, with its 2026-11-15 addendum).

| Branch | Worktree | Tip (hash, date, subject) | Base | Clean | Contains | Stage |
|---|---|---|---|---|---|---|
| `fix/safety-exemption-scope` | v7c | `8933863` 2026-11-14 docs: record key-off identity re-run over 68 bundles | pin `68e67b5` | yes | safety-exemption scope fix | 1 |
| `feat/ib10-live-resolution` | v7a | `5f098b7` 2026-11-15 docs: correct e09 model plan statements (erratum) | pin | yes | intersection run 1 | 2 |
| `feat/ib10-safety-default-arm` | v7d | `dead48d` 2026-11-15 docs: correct e03 model plan statements (erratum) | `fix/safety-exemption-scope` | yes | intersection run 2 | 2 |
| `docs/head-on-vlm-vs-rule` | none | `1f77bf1` 2026-11-14 docs: re-score head-on VLM yielder against position rule | `9ca0932` | n/a | head-on re-score | 3 |
| `exp/head-on-swapped-id-replay` | swapid | `abc28fe` 2026-11-14 docs: lead improved-annotation results with grey-control check | `docs/head-on-vlm-vs-rule` | yes | labels-swapped and clearer-annotation replays | 3 |
| `exp/head-on-json-only-replay` | jsononly | `29696f9` 2026-11-14 docs: mark ER-2 verdicts not assessable, add option-3 notes | `docs/head-on-vlm-vs-rule` | yes | JSON-only replay | 3 |
| `docs/vlm-plan-influence-trace` | v7i | `1400533` 2026-11-15 docs: add smoke bundles and fix counts in plan influence trace | `9ca0932` | yes | plan-influence trace | 3 |
| `demo/ib10-recorded-demo` | v7h | `64e9b83` 2026-11-15 docs: record IB10 recorded demo outcome (D1 bring-up abort) | `9ca0932` | yes | recorded intersection demo attempt | 3 |
| `feat/convoy-live-resolution` | v7f | `5c7bf22` 2026-11-14 docs: log convoy live-resolution registration and kit | `9ca0932` | yes | registered convoy experiment (unrun) | 3 |
| `fix/escort-obstacle-guard` | v7l | `92158d3` 2026-11-15 docs: correct reverse guard replay windows and scope notes | `fix/safety-exemption-scope` | yes | escort and reverse obstacle guards | 4 |
| `feat/gt-contact-logging` | v7m | `b5eaee5` 2026-11-15 docs: add G4 robot-robot positive control to contact report | `fix/safety-exemption-scope` | yes | geometric contact logging | 4 |
| `fix/m4-stall-abort` (new) | v7p | `1016e0b` 2026-11-15 docs: revise M4 stall abort report after review | `8933863` | yes | stall abort | 4 (new) |
| `fix/plan-dispatch-mismatch-visibility` (new) | v7r | `93655fc` 2026-11-15 test: pin pipeline carrying verified legs for the record | `8933863` | yes | mismatch record | 4 (new) |
| `demo/vlm-order-channel` | v7k | `52aea51` 2026-11-15 docs: log demo runtime delta refresh in implementation notes | `docs/vlm-plan-influence-trace` | yes | order-channel prompt rules, plan check | 5 |
| `demo/campaign-kits` | v7j | `4cacf55` 2026-11-15 docs: update presentation cut md5s after wording fix (before this commit) | `demo/ib10-recorded-demo` | yes | demonstration campaign, reports, this index | 5 |
| `analysis/failure-cause-classification` (new) | v7q | `0b6a91b` 2026-11-15 docs: add both raters' failure-cause rating records | `demo/campaign-kits@b70d925` | yes | classification, interception table | 5 (new) |
| `demo/validation-guard-contacts` (tip moved since the plan) | v7n | `a412949` 2026-11-15 docs: correct stockout count and reverse finding in validation report | `demo/campaign-kits@cc1313d` + v7l + v7m | yes | five-robot validation take | 5 |
| `test/safety-mechanisms-scripted` (new, **in progress**) | v7s | `99edbf3` 2026-11-15 test: add scripted safety-test decision and reverse-guard grounding (was `af5a9df` minutes earlier) | `demo/validation-guard-contacts@a412949` + v7l + v7p | yes at 13:49Z (2 untracked at the first look: `config/grounding/sft_s1b_reverse_guard.yaml`, `config/mock_decisions/sft_reverse_r5_r3_r1_once.json`) | scripted safety tests | 5 (new) |
| `fix/convoy-hold-queued-robots` | v7o | `d85d1ed` 2026-11-15 test: cover queued-crosser hold under feasibility gate modes | `demo/campaign-kits@4e5476b` | yes | queued-robot hold | 5 |
| `fix/convoy-yielder-feasibility` (new, **in progress**) | v7t | `d85d1ed` (no own commit yet) | `fix/convoy-hold-queued-robots@d85d1ed` | **no**: modified `reasoning/rag/command_grounder.py`, `swarm_orchestrator/models.py`, `orchestrator_node.py`, `reasoning_pipeline.py`; untracked `tests/unit/test_counterflow_yielder.py` | convoy yielder feasibility fix | 5 (new) |
| `feat/demo-panel-renderer` | v7g | `d43028d` 2026-11-15 docs: note presentation profile follow-up fixes | `feat/convoy-live-resolution` | yes | demo video renderer | 6 |
| `feat/v4-per-cluster-parity` | v6d | `f39bc8c` 2026-11-15 docs: add failure-cause thesis text shells to change list (before this session's register commit) | `feat/v4-per-cluster` | yes | evidence register, thesis change list | 7 |
| `feat/v4-refusal-feedback` | v7b | `384e948` 2026-11-14 docs: record finished-plan hiding for refusal feedback | `feat/v4-per-cluster` | yes | refusal feedback | 7 |
| `docs/thesis` | thesis | `7e589d8` 2026-11-15 docs: draw neutral failure-cause conclusions in ch1, ch7, ch8 (`b647829` at the first look, with `thesis/chapters/06-results.typ` modified) | v4 line | yes at 13:49Z | thesis; the report-writer session is integrating these results (read-only here) | 7 (optional) |

**Other worktrees with uncommitted or untracked files:**

- Main checkout `vgu-vlm-swarm` (`fix/deadlock-collision-resolution`): 16 untracked entries: `reports/`, `uv.lock`, and 14 `research_notes/` entries.
- `.claude/worktrees/m4-phase2-nav2-stack`: 6 modified (`isaac/vgu_sim/cmd_vel_watchdog.py`, `cmd_vel_watchdog_node.py`, `swarm_simulation/config/nav2_params.yaml`, `launch/nav2_robot.launch.py`, `tests/unit/test_cmd_vel_watchdog.py`, `test_nav2_params.py`) and 1 untracked session transcript.
- v7t: see the table (job in progress, not touched).

[[PENDING: TIPS-1 — final tips of `test/safety-mechanisms-scripted` and `fix/convoy-yielder-feasibility` (hash, date, subject, clean yes/no) after both jobs finish]]

---

## 5. Deliverables

All files below are **git-ignored and exist only on this Mac**; no off-machine copy exists (section 7).

| Deliverable | Path | md5 (where recorded) |
|---|---|---|
| Engineering cut, per take (5) | v7g `data/demo/campaign/`: `ibD_t05_a1_panel.mp4`, `cvD_t01_a1_panel.mp4`, `hoD_t01_a1_panel.mp4`, `m5D_t01_a1_panel.mp4`, `ER2LIVE_20260930_panel.mp4` | `fdf07a82fcb657b738c44a89bfbe3dae`, `824319447d05aaef6623158d00d2818f`, `2aa6534ad508d3440e51822fdcd3f0f0`, `33e9f5eedd7fb56edd007d8b728ea8c0`, `93cbfe7108e6a9ca9a71fc4c7c79bd47` (`DC` Final Summary) |
| Engineering combined | v7g `data/demo/campaign/demo_campaign_combined.mp4` (v3) | `de8cb6ed07e42008b8acb3f9274352db` (`DC` 9) |
| Presentation cut, per take (5) | v7g `data/demo/campaign/presentation/*_presentation.mp4` | `8c09f71fa34b727b82d6757692df76d7` (intersection), `f96210bc7958884a49b8f17ca7bc287e` (convoy), `32176fba6aeb7411a0036da51baf34f1` (head-on), `a51992a27877f2d801cb56f522ab34a6` (five-robot), `cfabf6cda7424d511e3cf3dc9f762722` (earlier recorded head-on run) (`DC` 13.1 as of `4cacf55`, which updated the md5s after the wording-fix re-render) |
| Presentation combined | v7g `data/demo/campaign/presentation/presentation_combined.mp4` | `ce8f4101b16e544372b2798cf2ce3c20` (`DC` 13.1 as of `4cacf55`) |
| Per-scenario demo package | `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-demo-package/` (`00_README.md`; one folder per scenario with videos, stills, logs, `other_takes.md`) | per-file md5 in each scenario `README.md` |
| Thesis figures: scene stills (14), clean and original | package `figures_for_report/scene_clean/` and each scenario's `images/scene_original/` | per-file md5 in `figures_for_report/README.md` |
| Thesis figures: take 5 decision flow, simple (main text) and detailed (appendix) | package `figures_for_report/flow_diagram/vlm_flow_take5_simple.{pdf,png,typ}`, `vlm_flow_take5.{pdf,png,typ}` | simple pdf `f0933aa00205b87db1cab2ac519a25e5`, png `b837b64c7727c344ef5338a9338f86bf`; detailed pdf `cbdfcaf2ec203cc1c39a276cacffe5d8`, png `359b3c7d152e392fa2d853094b054338` (computed for this page) |
| Escort-into-island stills | v7j `docs/reports/assets/2026-11-15-demo-campaign/` (tracked) and package `figures_for_report/escort_into_island/` | — |

The demo package README states that the report "does not describe a stall abort under that name"; the stall abort is described in v7p (R21), so that sentence is stale.

**Evidence directory sizes** (`du -sh`, one call each, 2026-11-15):

| Directory | Size |
|---|---|
| v7j `data/logs` (campaign bundles, kits, ledger) | 1.0 G |
| v7g `data/demo` (all video cuts) | 375 M |
| demo package | 318 M |
| v7a `data/logs/vm_runs` (intersection run 1) | 417 M |
| v7d `data/logs/vm_runs` (intersection run 2) | 281 M |
| v7q `data/experiments/2026-11-15-failure-cause-evidence` | 52 M |

---

## 6. Budget

Campaign ledger (`ledger_dmc.py status`, kit copy `cvh/kit`, read at 2026-11-15T13:49Z, 57 rows, no row from the scripted safety tests or the convoy rerun yet):

| Item | Value |
|---|---|
| VM seconds | **25,667 s of 43,200 s**: intersection 8,239; convoy 8,149; head-on 1,302; five-robot 3,833; five-robot validation take 4,144 |
| API spend booked | **$2.8637 of $10**: intersection $2.3335 (includes the $2.00 offline booking and the $0.2705 Sonnet check), convoy $0.3751, head-on $0.0164, five-robot $0.0685, five-robot validation take $0.0702 |

**Spend the reports record but the ledger does not book:**

- Convoy held-robot prompt check: $0.2990 at list price, $0.3738 in the check's own ledger units (list × 1.25) (`CH` section 3). Not in the campaign ledger.
- The $2.00 offline booking (registration section 10.5: "roughly $1.6–2.0") is consistent with the plan check's reported ledger spends $1.384 and $0.583 (sum $1.967; plan-check report lines 153 and 467). That mapping is inferred.
- Outside the campaign: intersection run 2's VLM arm $0.056; the 14 November offline prompt replays ran on their own provider budgets and are not totalled here.
- GPU stockouts before VM start (about 24 min five-robot, about 26 min convoy take 5, about 34.5 min five-robot validation take) are not VM seconds and are not booked.

**Reconciliation.** Booked $2.8637; with the unbooked convoy check added, $3.2375 if it is counted in its ledger units, or $3.1627 if counted at list price. The owner-brief figures quoted in the reports fit this: "≈ $3.07" (validation report section 5) equals $2.6975 + $0.3738, and "≈ $3.2" (registration 12.4) equals $2.8637 + $0.3738; both matches are inferred. **Range: $2.86–$3.24 of $10.**

[[PENDING: BUDGET-1 — VM seconds and API spend of the scripted safety tests (kit `sft`) and of any convoy rerun (kit `cvy`), and the new ledger totals]]

---

## 7. Open Decisions for the Owner

Collected from the reports; no recommendation beyond theirs.

| Decision | Source |
|---|---|
| Integration target (W, `main`, or a new branch from the pin), pushing branches as backups, tagging the pin | consolidation plan Q1–Q3 |
| Geometric contact logging: land always-on or behind a key | consolidation plan Q4 |
| Off-machine backup of evidence and videos (about 1.0 G + 375 M + 318 M + 417 M + 281 M + 52 M here, plus the older directories in Q5) | consolidation plan Q5; demo package README |
| Disposable worktrees (check each `data/` for unique evidence first) | consolidation plan Q6 |
| `docs/thesis` on the integration branch or separate | consolidation plan Q7 |
| Escort obstacle guard: E18 margin rule (a/b/c); registration amendment before any scored use | `DC` 10.1; v7l report section 4 |
| Reverse obstacle guard: shorten instead of refuse; withhold instead of 8 s waits. The brief calls shortening "approved, not built"; the guard report calls it "an open owner option" (8.8). No approval record was found | v7l report 8.8 |
| Other manoeuvre checks (junction recede and release legs, declared-geometry yield back-out and pull-off): each needs its own key, test and replay. The brief calls these "approved, not built"; the guard report gives them as a recommendation (8.2). No approval record was found | v7l report 8.2 |
| Stall abort follow-ups: hold an aborted backup with a short wait?; bag `/clock` and `/odom` in the first live take; the deterministic live validation proposal | v7p report sections 7, 9 |
| Plan state shown to the model ("robot_1: wait (done)" after a 1.3 m back-out) needs a prompt-input change, excluded so far | v7r report 4.1, 8 |
| Plan-dispatch fix level beyond the record: prompt contract, verifier, or plan-driven `reverse`/`reroute` grounding (registration amendment) | rubric report Part A section 4, 8.4 Q4 |
| Convoy: yielder feasibility (the robot_1 variant latches under the hold); convoy fix options (a)–(c) need a registration amendment for the registered convoy experiment | `DC` 5.5, 12.4; v7o report 6 |
| Intersection options-detail wording: render the detail so it cannot be read as an action, or narrow parser tolerance (a third fix cycle) | `DC` 2.5 |
| Log-filter lines in the engineering panel (`yield re-grounded`, `dispatch_order_source`, refusal lines) | `DC` Final Summary |
| Intersection yielder gap stays open by owner decision | `DC` Final Summary |
| Post-fix live comparison: design D1, D1+C or D2, scope and budget; whether a scripted five-robot arm is wanted | rubric report 8.3–8.4 |
| Clock mapping for the coordination-off arm: failed its pre-declared test (5 of 28 bundles above 2.0 s), not applied | v7q reconciliation section 8 |
| Unverified audit count (R26): re-check or cite as unverified | `DC` 11.4; `REG` |
| Builder-parity test of the authored obstacle boxes (`pxr`): skipped in both convoy invocations and not run in the validation take; a rerun needs pytest inside Isaac's Python or a Kit context, which needs its own approval; the owner's request is unmet | `DC` 12.5; v7n report 2.5 |
| Demo package `needs_decision/fig_intersection_panel_dispatch_t33p07.png`: keep as the "format of the demonstration videos" figure, or drop | package `figures_for_report/README.md` |

---

## 8. In Progress as of Writing

### 8.1 Scripted Safety Tests

Worktree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7s`, branch `test/safety-mechanisms-scripted`, kit `sft` (exists under v7j `data/logs/vm_runs/demo_campaign/sft/`; not read). Tests the escort and reverse obstacle guards and the stall abort with scripted (mock) decisions. Not touched by this session.

```text
[[PENDING: SFT — to be filled by a later pass]]
SFT-1  reverse obstacle guard: verdict (fired as expected / did not fire / not run), evidence lines, report path + commit
SFT-2  stall abort: verdict, abort line(s), time from contact to abort, FAILED status, false-positive control result
SFT-3  escort obstacle guard and geometric contact logging: verdict per mechanism; logged contact entry seen yes/no
SFT-4  whether mechanisms were enabled one at a time (owner rule), per take
SFT-5  VM seconds and API spend booked (ledger rows)
SFT-6  branch tip (hash, date, subject), clean yes/no
```

### 8.2 Convoy Non-Arrival Inspection and Yielder-Feasibility Fix

Worktree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7t`, branch `fix/convoy-yielder-feasibility` (at `d85d1ed` with uncommitted changes, section 4), kit `cvy` (not present under `demo_campaign/` at 13:49Z). Not touched by this session.

```text
[[PENDING: CVY — to be filled by a later pass]]
CVY-1  inspection finding: why robot_2 did not arrive in convoy takes 4-5, report path + commit
CVY-2  fix: key name, default, tests, offline replay result
CVY-3  rerun go/no-go and who decided it
CVY-4  rerun outcome (arrivals, label), if run
CVY-5  VM seconds and API spend booked
CVY-6  branch tip (hash, date, subject), clean yes/no
```

---

## 9. What to Do Next, in Order

1. Let the two jobs finish (section 8).
2. Fill every `[[PENDING: …]]` block here (SFT, CVY, TIPS-1, BUDGET-1), in the evidence register (rung f) and in the consolidation plan addendum.
3. Owner review of section 7.
4. Consolidation per the plan and its 2026-11-15 addendum (re-run `git merge-tree` against the integration branch before each stage).
5. Off-machine backup of the evidence directories, the videos and the demo package, before any worktree is removed.

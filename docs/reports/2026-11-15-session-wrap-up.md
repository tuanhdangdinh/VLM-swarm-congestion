# Session Wrap-Up, 13–15 November 2026

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: index of every result produced on 2026-11-13..15 (where it lives, evidence grade, caveat), safety-mechanism status, branches and worktrees, deliverables, budget, open owner decisions, and placeholder blocks for the two jobs still in progress.
- Rev 2 (2026-11-15): reader-facing name "central layer" replaced by "coordination layer" (owner decision of 2026-11-15); open-decisions section records the owner's in-session approval of reverse shortening and the per-manoeuvre guards.
- Rev 3 (2026-11-15): final pass after both jobs finished. Filled the placeholder blocks for the scripted safety tests, the convoy inspection and rerun, the final branch tips and the budget (section 8 now records the results); added results rows R27–R29; updated the bottom line, the safety status table (plus a row for the counterflow yielder correction), branch tips, deliverables (absolute paths), budget, open decisions and next steps; corrected 14 statements made stale by the two jobs (for example "live validation in progress", "convoy unresolved in 5 of 5", "67 of 67", "builder-parity test never ran"); added section 10, "Thesis Report Session", including the owner's research-question ruling and the independent thesis review (copied to `docs/reports/2026-11-15-thesis-independent-review.md`). Historical mentions of "central layer" in Rev 2 and in "Names Used in This Document" are kept as history.

---

## How to Read This Document

- **What it is.** An index. Every number is quoted from the source named in the same row; the source is the record. Nothing was re-run for this page except read-only git commands, `du`, `md5` and the campaign ledger's `status` command.
- **Snapshot.** Git facts and the ledger were first read at 2026-11-15T13:49Z, while two jobs were still running. Rev 3 re-read them at about 15:45Z, after both jobs had finished (section 8); the thesis branch was re-read last (section 10), while its session was still committing.
- **Evidence grades used here:**
  - *registered pilot*: the analysis plan was fixed before the runs; such runs are never pooled with later exploratory runs;
  - *exploratory live*: a closed-loop simulation run (Isaac Sim) with the real model, small n, analysis not fixed in advance or fixed only for that run;
  - *illustrative demo*: a single recorded take chosen to show the pipeline; never a rate;
  - *offline replay*: recorded decisions or poses re-processed by code, with no new simulation;
  - *code reading*: established by reading the source.
- **Everything is simulation** unless marked.

### Names Used in This Document

The canonical naming glossary is `docs/guides/naming_glossary.md` on `demo/campaign-kits`, written by another job and checked against the thesis's own names. It was committed as `8565fe0` while this page was being written; the names below follow it (for example "coordination layer" for Layer 2, as the owner decided on 2026-11-15, replacing the glossary's first choice "central layer"; "coordination command" and "coordination exemption" stay M4's execution-level terms; "registered as confirmatory" only for the 21 October five-robot pilot). **The glossary supersedes this table.**

| Name in this document | Internal ids (repo) |
|---|---|
| Four-robot intersection | `intersection_bottleneck`, IB10, `ib`, labels `ibD`/`ibS`/`ibL` |
| Four-robot convoy counterflow scene (two robots queued behind a head-on pair) | convoy counterflow, `convoy_counterflow_slip`, `cv`, labels `cvD`/`cvH`/`cvL` |
| Two-robot head-on corridor with obstacle | `head_on_asymmetric_w0p2_eopen_bshort_o0`, head-on family, `ho`, `hoD` |
| Five-robot pickup-and-delivery scene | `mapd_5_s1b`, S1b, `m5`, `m5D`/`m5V`, episodes E6–E31 |
| Intersection run 1: coordination layer on vs off (13 Nov) | IB10 live resolution, Arm A vs Arm B |
| Intersection run 2: live VLM vs scripted default plan (14 Nov) | IB10 safety default arm, Arm A vs Arm C |
| Registered five-robot pilot (21 Oct; 10 episodes, registered as confirmatory) | prereg-v3 tranche 1, `batch6`, E27–E31 Arm A / Arm B |
| Exploratory five-robot pilots (10–17 Oct; 21 episodes) | E6–E26: `batch2`–`batch5`, `live_batch`, `resume`, `churn_wave` |
| Demonstration campaign, demonstration takes (14–15 Nov UTC) | demo campaign (`demo_campaign/`); "take N" as in the reports |
| Five-robot validation take | `m5V_t01_a1` (kit `m5v`) |
| Scripted safety tests | kit `sft`, branch `test/safety-mechanisms-scripted`, takes `sfT_t01_a1` (reverse guard on) and `sfT_t02_a1` (stall abort on) |
| Convoy rerun (demonstration take with the queued-robot hold and the counterflow yielder correction) | kit `cvy`, take `cvY_t01_a2`, branch `fix/convoy-yielder-feasibility` |
| counterflow yielder correction | `grounding_yield_counterflow_swap` |
| Earlier recorded head-on run (30 Sep) | ER2LIVE, bundle `ER2LIVE_20260930_152222` |
| Head-on re-score (recorded September runs) | `docs/head-on-vlm-vs-rule` re-score |
| Offline prompt replay: robot labels swapped | swapped-ID replay |
| Offline prompt replay: answer format changed to JSON only | JSON-only replay |
| Offline prompt replay: clearer image annotation | improved-annotation replay |
| Plan-order prompt check (offline) | `vlm-order-channel-plan-check` (prompt variants A, B, A3, B3) |
| coordination layer on / off | Layer 2 on / off (Arm A / Arm B) |
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

In simulation, the full coordination layer (congestion trigger, a call to Gemini Robotics-ER 2, grounding and plan verification, phased dispatch) cleared a four-robot intersection jam that the robots' local control alone never cleared (4 of 5 episodes against 0 of 5), but a scripted arm that skipped the model call and ran the grounder's default plan cleared it as well (4 of 4 valid, 5 of 5 after a post hoc re-run) with the same executed plan; these are exploratory pilots, not independent samples. ER-2 returned a valid, parseable decision in all 69 demonstration analyses, but its plan was accepted unchanged in 6 of 65 plan-channel analyses of the first twelve takes (5 once a dispatch that contradicted the plan is not counted as accepted; the convoy rerun added 2 analyses, neither accepted unchanged), and it changed the executed commands relative to the default once, by swapping the order of two near-equivalent back-out manoeuvres (a 0.010 m difference against a 0.15 m tolerance). In the two-robot head-on corridor the grounder's feasibility gate, not the model, made the executed yielder correct (79 of 79 runs, 37 model choices overturned), and pre-registered offline replays found no model that chose the yielder from the scene rather than from labels or listing order. The evidence does not support that the VLM improves outcomes, uses the image, or that the pipeline handles congestion outside the intersection: the four-robot convoy was unresolved in 5 of 6 takes, and the one resolved take (the convoy rerun, n = 1) is a grounder result: the queued-robot hold held the two queued robots, the model chose the strategy and, this time, the feasible yielder itself, and the counterflow yielder correction was armed but did not fire, so it is untested live; this is not evidence that the VLM resolves convoy congestion. In the five-robot take 1 of 5 robots arrived. A two-rater failure-cause classification of the five-robot runs names no dominant cause and leaves a large share undetermined (registered pilot 12 of 18 units, of which 10 of 10 in the coordination-layer-off arm for lack of a clock anchor and 2 of 8 with the layer on; exploratory pilots 13 of 33). Safety evidence is robot-pair centre distance plus an offline geometric recompute; one sustained robot-obstacle contact was confirmed, obstacle contacts also came from reverse manoeuvres in October runs. Of the mechanisms built to stop them, the reverse obstacle guard and the stall abort were each validated live once in a scripted safety test (scripted decision, one new mechanism on per take, n = 1 each, declared obstacle boxes only), and geometric contact logging recorded its first live contact, equal row by row to the offline recompute; the escort obstacle guard stays validated offline only (armed once live, never fired).

Sources: thesis evidence register (v6d `docs/reports/2026-11-13-thesis-evidence-register.md`, "VLM Contribution", Recommended Thesis Wording 1–6, updated 2026-11-15 in Rev 8 and Rev 10) and the rows of section 2 (R27–R29 for the two finished jobs).

---

## 2. Results Table

Short source names: `DC` demo campaign results (v7j `docs/reports/2026-11-15-demo-campaign-results.md`, last commit `4cacf55` at Rev 2; `3866ec1` after section 14, the convoy rerun; `781598d` after section 14.9, its videos); `REG` evidence register (above); `SFT` scripted safety-test results (v7s `docs/reports/2026-11-15-safety-mechanism-scripted-tests-results.md`, `74dd45c`); `CVY` convoy non-arrival and yielder-feasibility report (v7t `docs/reports/2026-11-15-convoy-non-arrival-and-yielder-feasibility.md`, created `886a90f`, last changed `272ad4a`). Every other source is named in full.

| # | Result (n) | Grade | Source (path, section, commit) | Caveat that must travel with it |
|---|---|---|---|---|
| R1 | Intersection run 1: coordination layer on resolved 4/5 (16/20 arrivals), off 0/5 (0/20); attribution 4 repaired, 1 grounder default, 0 plan accepted unchanged | registered exploratory pilot, n = 5 per arm | v7a `docs/reports/2026-11-13-ib10-live-resolution-results.md`, results; `5f098b7` | One scene, about three near-repeat trajectories: not independent samples, no p-value. Supports "the pipeline clears the jam", not "the VLM's plan clears it" |
| R2 | Intersection run 2: VLM arm 5/5 (mean 115.96 s from onset); scripted default plan, no model call 4/4 valid (mean 117.80 s), 5/5 after a post hoc re-run (mean 117.86 s); every VLM-arm first dispatch re-grounds to exactly the scripted plan | exploratory pilot, n = 5 per arm | v7d `docs/reports/2026-11-14-ib10-safety-default-arm-results.md`, "Plan equality", re-run addendum; `dead48d` | Cite both scripted-arm figures. The scripted arm was handed strategy and robot set; it dispatches about 3.4 s later. Never pooled with experiment 1 |
| R3 | Safety-exemption scope fix (M4 safety fix): key-off exemption timelines identical to the pinned tracker in 68/68 bundles (673 changes); key on loses 6 exemptions (1 in experiment 1 e09, 5 in older sets); armed live in experiment 2 and never fired (all counters 0) | offline replay; unit tests (64); live armed, not exercised | v7c `docs/reports/2026-11-14-safety-exemption-fix.md`, Replay Regression, Open Items; `8933863`; REG row "IB10 safety smoke" | A what-if on trajectories recorded under key-off behaviour; not a live validation |
| R4 | Head-on re-score (recorded September runs): the VLM's yielder correct, gpt-4o west 5/23, east 10/12; ER-2 west 12/30, east 11/13; never above the better trivial baseline; with the feasibility gate on, the executed yielder was correct in 79/79 runs, 37 of them model picks overturned | post hoc re-score of pilot data | branch `docs/head-on-vlm-vs-rule` `docs/reports/2026-11-14-head-on-vlm-vs-rule-rescore.md`, Headline, lines 185–222; `1f77bf1` | Not pre-registered; the gate column is derived from artifact fields, not checked against M4 logs |
| R5 | Plan-influence trace: the model's plan changed dispatch in 0 of 39 gated four-robot analyses; 14 plans accepted unchanged, 8 dispatched as written | offline replay (trace; each claim labelled verified/inferred) | v7i `docs/reports/2026-11-15-vlm-plan-influence-trace.md`, Answers, B, D, E; `1400533` | The order-dispatch flag was never on in those runs; the model's decision fields changed execution against the scripted default in 18 dispatches in 4 episodes, and where judged (2 episodes) the outcome was worse |
| R6 | Plan-order prompt check (offline), ER-2: plan accepted unchanged A 2/40, B 2/40, A3 6/40, B3 14/29; first-trigger "demo event" A 0/38, B 1/38, A3 0/38, B3 7/27 | offline replay, pre-registered cycles | v7j `docs/reports/2026-11-15-vlm-order-channel-plan-check.md`, sections 4, 10.3; `7586857` | One scene, near-identical snapshots. Shows control over the back-out order, not a better order; order biased toward ascending robot id (inferred) |
| R7 | Offline Sonnet 5.5 check (B3 prompt): 16/16 valid, 11 accepted unchanged, 1/15 first triggers would qualify as VLM-driven (yielder gap) | offline replay, pre-registered (`b103ff4`) | same report, section 11; `DC` 3.4–3.5 | No Sonnet live take was run (no-go) |
| R8 | Four-robot convoy, held-robot state in the prompt: 0/18 primary and 0/22 answers per condition grounded into the four-robot sequence (44 calls) | offline replay, pre-registered | v7j `docs/reports/2026-11-15-convoy-held-robot-prompt-check.md`, sections 2–4; `4d6f057` | A prompt-only fix is a no-go; no retake was run on it |
| R9 | Offline prompt replays on scene use (14 Nov): robot labels swapped: no model meets the pre-registered rule, gpt-4o follows the first-listed slot 85/96; answer format changed to JSON only: Sonnet answered 146/146, correct yielder 46/96 in the grey pair, ER-2 not assessable; clearer image annotation: every verdict not assessable (provider limits), ER-2 lead 55/67 | offline replay, pre-registered | swapid `docs/reports/2026-11-14-head-on-swapped-id-replay-results.md` (`bc26ae0`); jsononly `docs/reports/2026-11-14-head-on-json-only-replay-results.md` (`29696f9`); swapid `docs/reports/2026-11-14-improved-annotation-replay-results.md` (`abc28fe`) | Two robots, first decision only, nothing executed. The 55/67 lead is not evidence of image use |
| R10 | Demonstration takes, four-robot intersection: 5 valid takes (1 bring-up abort); take 1 unresolved (3/4 arrived), takes 2–4 grounder-default resolution, take 5 VLM-driven execution (4/4): plan accepted unchanged, back-out order robot_3 → robot_4 against default robot_4 → robot_3 | illustrative demo | `DC` sections 1–2, 7; Final Summary | Take 5 is a near-tie (0.010 m against 0.15 m tolerance); only the timing of two back-outs changed; chosen for its label; 1 of 5 takes |
| R11 | Demonstration takes, four-robot convoy: 5 takes, all unresolved. Takes 1–3: 0/4 arrived; the model named only the head-on pair, the two queued robots (never commanded) followed through and latched; 33 later proposals ran as 8 s waits. Takes 4–5 with the queued-robot hold: 1/4 arrived each; the hold kept the queued robots as designed, but the model chose robot_1 as yielder both times and robot_2's escort latched 0.418/0.419 m from the held robot_3 | illustrative demo, n = 3 + 2 | `DC` sections 5, 12; Final Summary | Two separated causes: uncommanded queued robots (takes 1–3, fixed by the hold) and the yielder choice (takes 4–5, the scene's latching variant). n = 2 for the hold: no rate. Rev 3: a sixth convoy take, the rerun, resolved (R29); convoy now 6 valid takes, 5 unresolved, 1 resolved |
| R12 | Demonstration take, two-robot head-on corridor: resolved 2/2 by the default plan (grounder-corrected): the gate swapped the model's yielder robot_1 (0.70 m retreat room < 1.08 m) to robot_2 | illustrative demo, n = 1 | `DC` section 6 | The model's first strategy (`reverse`) ran and did not clear the scene |
| R13 | Demonstration take, five-robot pickup-and-delivery scene: 1/5 arrived; 2 of 8 decisions executed as named, 6 withheld by grounding refusals; decision 2's escort drove robot_3 into rack island `obstacle_2` (within 5 mm in 4526 of 4534 ground-truth rows from sim 146.7 s) | illustrative demo, n = 1; contact by offline recompute | `DC` sections 8, 8.7 | "Unresolved" partly reflects an escort path error (no obstacle check on that path), not only the model or the refusals |
| R14 | Earlier recorded head-on run (30 Sep): the model named robot_2 as yielder, the gate kept it, executed, 2/2 arrived | illustrative demo, n = 1 | `DC` section 11 | Selected because it qualifies; older code `3959d7f`; escort and Nav2 recovery are the system's; the stage-2 pick was the first of two mirror-equivalent options |
| R15 | Demonstration three-way count: valid response 67/67; plan accepted unchanged 6 of 65 plan-channel analyses; changed executed behaviour 1 (intersection only). Corrected by the mismatch definition: 5 accepted (raw reading 3, motion-only 6); the drop is convoy take 2's `759bdb94` | illustrative demo; corrected count by offline recompute | `DC` Final Summary (Rev 11); v7r `docs/reports/2026-11-15-plan-dispatch-mismatch-visibility.md` section 6.3; `93655fc` | The denominators differ: `DC`'s 65 counts the 4 intersection "no congestion" answers; v7r's plan-block decisions are 61 (ib 5, cv 36, m5 8, convoy takes 4–5 12). The validation take is outside both. Rev 3: with the convoy rerun valid responses are 69 of 69 (`DC` three-way table, Rev 13); the rerun adds 2 analyses, 0 accepted unchanged (1 `repaired` yield, 1 "no congestion"; `DC` 14.2 and the convoy row of the three-way table). `DC` still states "6 of the 65"; 6 of 67 would be a derived figure. v7r's 61 and its corrected 5 predate the rerun and were not recomputed; since the rerun's plan was repaired, it cannot add an accepted-unchanged plan under either definition (inferred) |
| R16 | Plan-dispatch mismatch: `reverse` and `reroute` are grounded from `involved_robots`, never from the plan; 10 of 33 reverse legs (7 commands) went to robots whose plan was not `reverse`; 3 of 3 reroutes disagree; 15 "silent" accepted-unchanged decisions, of which 9 are overridden under the new definition. Corrected accepted-unchanged counts per series: intersection takes 1, convoy takes 1–3 2, five-robot take 2, five-robot validation take 0, convoy takes 4–5 0; registered five-robot pilot 1 of 2 recorded; October series in v7r table 6.1 | code reading; offline recompute (fidelity gate 0 failures on 269 exact rows) | v7j `docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md` Part A, sections 1–4 (`b70d925`); v7r report sections 1, 6.1–6.2 (`93655fc`) | The registered pilot's row is a recomputation beside the registered result, not a rescore. The record is behind a default-off key; no prompt or grounding change was made |
| R17 | Ground-truth contact fields were hard-coded empty; offline recompute over 44 bundles: 1 sustained robot-obstacle contact (five-robot take, robot_3), 2 brief grazes within noise, no robot-robot footprint contact (closest 82.1 mm); positive control recovered | offline replay (geometric footprint, 10 Hz) | v7m `docs/reports/2026-11-15-gt-contact-logging.md` section 5; `b5eaee5`; `DC` 10.2 | Footprint proximity, not physics contact. Robot gap figures differ slightly from `DC` 8.7.2 (−0.2 mm vs −0.16 mm; E30 graze 1.2 mm vs 0.97 mm) |
| R18 | Five-robot validation take (five-robot pickup-and-delivery scene, escort obstacle guard on, geometric contact logging on): contact fields on 6001/6001 rows, all reproduced exactly offline; no contact event; closest obstacle approach 5.5 mm under a VLM-named `reverse`; no escort was grounded, so the escort guard never fired; 2/5 arrived | exploratory live, validation only, n = 1 | v7n `docs/reports/2026-11-15-validation-guard-contacts-results.md` sections 1–5; `a412949` | Verdicts: contact logging "partially validated" (no live contact occurred; builder-parity test not run); escort guard "validated as armed and harmless only". Superseded for contact logging by R27 (Rev 3): a live contact was recorded and the builder-parity test passed |
| R19 | Escort obstacle guard, offline replay: refuses five-robot take decision 2 (`a15f3fc5`, clear 0.414 m) and October E18 `1feb2c4e`; every other campaign escort unchanged; of 24 October escort commands only E18 changes. Of the 2 refusals, 1 justified (contact), 1 untested (never drove) | offline replay; 33 test functions | v7l `docs/reports/2026-11-15-escort-obstacle-guard.md` section 4; `DC` 10.1; v7q reconciliation 7.2 | Declared obstacles only; no M4 backstop; the E18 margin rule awaits the owner. `DC` 8.7.4 counts 19 admitted October escorts (a different scope from the 24 commands) |
| R20 | Reverse obstacle guard, historical replay: 17 dispatched reverses with declared obstacles; 14 refused: 10 justified (8 contact, 2 sub-margin graze), 3 untested, 1 false positive (1/14 = 7 %, at most 4/14); robot level 6 of 17 blocked legs false positives (35 %). In October runs 10 of the 14 refused commands had a leg FAILED live, 7 pinned on an obstacle face until the 195 s deadline | offline replay; 25 test functions (29 cases) + 2 node tests | v7l report section 8 (8.5, 8.6); `92158d3` | Criterion: only the 0.05 m threshold was fixed before the gaps were printed. Shows reverses drove into obstacles in October runs; does not show a refusal would have resolved the scene |
| R21 | Stall abort, offline replay of 221 raw-velocity primitives (48 bundles): fires on all 10 contact stalls, 2.3–3.0 sim-s after contact; 0 of 191 contact-free completed primitives fire; 2 completed primitives in contact would end FAILED; 19 of 21 silent live failures were held by the safety latch | offline replay (reconstructed commands); 79 test functions | v7p `docs/reports/2026-11-15-m4-stall-abort.md` sections 6.2–6.4; `1016e0b` | The reconciliation recompute covers a narrower set (100 primitives in 25 coordination-layer-on bundles, 10 fires), with identical lines to its provisional column. Stale-odometry abort has no live evidence |
| R22 | Failure-cause classification, five-robot runs: 55 failure units in 33 episodes, two raters; undetermined share registered pilot 12/18 (coordination on 2/8, off 10/10), October pilots 13/33, November takes 2/4; agreement on the final code 50/55 (kappa 0.895), class 53/55 (kappa 0.948), round 1 32/55; no class leads in both raters and after reconciliation in every stratum, so no dominant cause is stated | registered rubric (frozen `b70d925`), exploratory post hoc coding | v7q `docs/reports/2026-11-15-failure-cause-reconciliation.md` sections 1, 2, 4.1–4.3, 6; `a1bcf53` | Strata never pooled. Rule properties shape the result: the environment-geometry codes cannot fire at onset (the decision-substitution test (T1) motion set is never empty), the coordination-off units lack a clock anchor, 15 units fail the decision-substitution-test fidelity gate. The clock mapping failed its pre-declared test and is not applied |
| R23 | Interception table (would escort guard, reverse guard or stall abort have acted on a linked leg?): registered pilot 0/8 units; October pilots 9/33 intercepted (5 with a justified leg), 24 none applies; November takes 1/4 (2/4 under the persistent-state link (sensitivity analysis)). Legs, October pilots: reverse guard refuses 29 (9 justified, 15 false positive, 5 untested, counting co-refused legs) | offline replay | v7q reconciliation section 7; `a1bcf53` | Says what would have been refused or aborted, not that the scene would then resolve. None of the three mechanisms was validated live as firing when this was written; since then the reverse obstacle guard and the stall abort have each fired once in a scripted live test (R27), the escort obstacle guard still has not. The reverse guard's high false-positive share here (15 of 29 October-pilot legs) is the reason reverse shortening matters (section 7) |
| R24 | Queued-robot hold, offline replay: 46 of 46 first-trigger yields ground into the four-robot sequence; 33 later convoy and 15 other-scenario decisions unchanged | offline replay; 51 tests (report) | v7o `docs/reports/2026-11-15-convoy-hold-queued-robots.md` Summary, sections 5–6; `d85d1ed` | Per-take chance of a resolving first sequence about 2/3 (model picks robot_2 in 12/18) times an unmeasured live success rate; live result is R11 takes 4–5 |
| R25 | Errata issued 2026-11-15 to older reports: contact wording (v7d `f30869e`, `04a1956`; v7a `88aad36`, `3cb947e`; v6d `b534d17`; v7j `d076a54`, `7586857`); model-plan statements (v7a `5f098b7` e09, v7d `dead48d` e03, mirrored on v7j `41f1e13`); `DC` Rev 8 exception-row span 266.5–268.0 s; `DC` Rev 10 hard-floor metric (centre distance 0.2643 m, not 0.186 m body gap) | docs only | `DC` 8.7.6, 10.2, 11.5; commits listed | No number or verdict changed by the errata |
| R26 | Read-only audit count: about 110 decisions in 71 recorded bundles dispatched without swap, repair, substitution or default | unverified | `DC` 11.4 | Parts do not reconcile (ER-2 79; reverse 41 + yield 40 = 81 of about 110); cite only as an unverified audit count |
| R27 | Scripted safety tests (Rev 3), five-robot pickup-and-delivery scene, two takes, one new mechanism on per take, contact logging on in both. Reverse obstacle guard: PASS, refused the scripted reverse at sim 40.83 s (`reverse_hits_obstacle:robot_5:obstacle_3:0.293`, predicted 0.295–0.349), three 8 s waits completed, maximum backward displacement 0.000 m, no contact. Stall abort: PASS, contact with `rack/NW_west` at GT 46.30 s, abort 2.21 s later (registered limit 5.0 s; the replay predicted 2.3–3.0 s), status FAILED with the stall reason, one zero twist; robot_1's clear reverse COMPLETED without abort. Contact logging: first live contact recorded (24 rows), logged rows equal the offline recompute (1017 and 1313 rows, 0 mismatches); the simulator-only builder-parity test ran and passed for the first time | safety test, scripted (mock) decision, n = 1 per mechanism; registered before the VM start (`b000103`) | `SFT` sections 2–6; `74dd45c` | Not VLM behaviour, not a demo, never pooled. Declared boxes only; odometry is a simulator physics pose. Not shown: `input_stale`, turn-phase, escort and pull-off stalls, latch-held robots (blind spot), the junction fallback path. robot_3's reverse in the stall take FAILED through the existing latch fast-fail, not the stall abort. Escort obstacle guard: no take (a blocked escort was reproducible in 1 of 3 recorded snapshots), still armed-once and offline-only. Full unit suite on the merged tree pending (targeted suites 1670 passed, 0 failed) |
| R28 | Convoy non-arrival inspection and counterflow yielder correction (Rev 3): takes 1–3 failed because the queued robots were released uncommanded, takes 4–5 because the model chose the platoon-side yielder robot_1; the existing feasibility gate never fires in the convoy (0 of 49 first-trigger yields, no static obstacles declared). Fix `grounding_yield_counterflow_swap` (default off, `a0311b0`): offline, first-trigger yields grounding into the resolving sequence: 1 / 27 / 49 of 49 with neither key / hold only / hold + correction; 43 later convoy and 15 other-scene decisions unchanged | offline replay (no model calls); 51 unit tests; code reading | `CVY` Summary, sections 1–5 | Offline only; the robot_2 sequence had resolved live once (scripted smoke). Thin goal-side margin (smoke 0.495 m against the 0.45 m latch). Full unit suite pending (swap below 2 GB) |
| R29 | Convoy rerun (Rev 3), queued-robot hold and counterflow yielder correction both on: 1 valid take (1 bring-up abort), resolved, 4/4 arrived (75.3, 116.4, 158.1, 180.1 sim-s); label "Resolved — grounder held the queued robots; model chose strategy and yielder"; the model named only robot_1 and robot_2 and chose robot_2 to yield; the hold added robot_3 and robot_4; closest non-exempted pair 0.497 m (0.047 m above the latch); 0 hard-floor stops; no contact in the offline recompute (closest static 0.0185 m, robot_2 on its return) | illustrative demo, n = 1 | `DC` section 14 (`2cafbf7`, `3866ec1`) | A grounder result, not a VLM one, and not evidence that the VLM resolves convoy congestion. The yielder correction was armed and did not fire, because with robot_2 yielding every crossing robot starts on the opposite side: it is untested live. The model chose robot_1 in 3 of the 5 earlier live first decisions. Convoy is now 6 valid takes: 5 unresolved, 1 resolved |

---

## 3. Safety Mechanisms Status

Owner rule: every new safety mechanism stays default-off, and they are enabled one at a time; the first validation run of a new mechanism does not enable it together with other new mechanisms (v7p report, Scope).

| Mechanism | Branch (worktree) | Key, default | Tests | Offline replay | Live status | Known limits |
|---|---|---|---|---|---|---|
| Safety-exemption scope fix (M4) | `fix/safety-exemption-scope` (v7c) | `safety.scoped_clearing_exemption`, off | 64 | 68/68 key-off identity; key on loses 6 exemptions | armed in intersection run 2, never fired | Third-robot path only; P4/P5 out of scope |
| Escort obstacle guard (M3) | `fix/escort-obstacle-guard` (v7l) | `grounding.escort_obstacle_guard`, off | 33 functions (35 cases) | refuses 2 (1 justified, 1 untested) | armed once (five-robot validation take), never fired | declared obstacles only; legacy grounding not covered; E18 margin rule open |
| Reverse obstacle guard (M3) | `fix/escort-obstacle-guard` (v7l, §8) | `grounding.reverse_obstacle_guard`, off | 25 functions (29 cases) + 2 | 14 of 17 refused; 10 justified, 3 untested, 1 false positive | validated live once (scripted safety test, R27): refused a forced reverse into a declared wall, waits completed, no backward motion, no contact; it also named a second blocked leg (robot_1 into the south wall, turning heading) | refuses, does not shorten; refusal dispatches 8 s waits; square-corner and open-arm over-approximation (false positives in the replays); undeclared geometry not covered; not tested on a real VLM decision |
| Stall abort (M4) | `fix/m4-stall-abort` (v7p) | `safety.stall_abort.enabled`, off | 79 functions | 10/10 contact stalls, 0/191 false fires | validated live once (scripted safety test, R27): aborted 2.21 s after a forced pin against an authored rack, FAILED with the stall reason, one zero twist; did not fire on a clear leg | raw-velocity primitives only; latch-held robots never judged; `input_stale`, turn-phase, escort and pull-off stalls untested live; post-review commit `7438929` checked by six M4 test files, not by a full suite |
| Geometric contact logging (simulation) | `feat/gt-contact-logging` (v7m) | none: always on | 54 | 44 bundles recomputed | validated on a live contact (scripted safety tests, R27): the first live contact was logged (24 rows) and every logged row equals the offline recompute (0 mismatches in both takes); five-robot validation take earlier: fields 6001/6001, no contact | not default-off (changes ground-truth rows); footprint proximity, not physics contact; builder-parity test passed once inside a Kit app (scripted safety-test session), skipped again in the convoy rerun |
| Queued-robot hold (M3) | `fix/convoy-hold-queued-robots` (v7o) | `grounding_hold_queued_crossers`, off | 51 (+ gate-mode tests at `d85d1ed`) | 46/46 yields become the four-robot sequence | used in convoy takes 4–5: worked as built, both takes unresolved; used in the convoy rerun: held robot_3 and robot_4 until their own admission, take resolved (R29) | legacy corridor yield only; inert in derived grounding |
| Counterflow yielder correction (M3, Rev 3) | `fix/convoy-yielder-feasibility` (v7t) | `grounding_yield_counterflow_swap`, off | 51 | 49/49 first-trigger yields become the resolving sequence (hold only 27/49) | armed in the convoy rerun, did not fire (the model's yielder was already feasible): untested live | legacy single-corridor yield only; hands the yield only to another named robot, else refuses; full unit suite pending |
| Plan-dispatch mismatch record (M5/M3) | `fix/plan-dispatch-mismatch-visibility` (v7r) | `plan_dispatch_mismatch_visibility`, off | 48 | 0 fidelity failures on exact rows | never run live | logging only; prompt still shows wrong leg statuses; full unit suite not run (swap floor) |

The scripted safety-test branch (`test/safety-mechanisms-scripted`, v7s) merges the escort and reverse obstacle guards, contact logging and the stall abort. Its two takes kept the owner rule: exactly one new key on per take (reverse guard alone, then stall abort alone), verified through the deployed loaders, the startup lines and the artifact parameters (`SFT` section 7); contact logging, which has no key, was on in both. The convoy rerun enabled the queued-robot hold and the counterflow yielder correction together; the hold had already run without the correction in takes 4–5, so the correction was the only new key in that take (`DC` 14, registration section 13).

---

## 4. Branches and Worktrees

Read-only snapshot at 2026-11-15T13:49Z, every tip re-checked at about 15:45Z for Rev 3 (`git worktree list`, `git log -1`, `git status --porcelain`, `git show-ref refs/remotes/origin/<b>`; no fetch). Rows whose tip or state changed say so. "Pushed": no branch in this table has a local remote-tracking ref, so all are **unpushed**. The three earlier v4 branches outside this table do have remotes (as of the last fetch): `feat/v4-gf-cluster` `c16b1a7` 0/0, `feat/v4-vlm-bench` `7850f5a` 0/0, `feat/v4-per-cluster` `48234f2` ahead 1 (Stage 7, unchanged since the plan). Stage numbers refer to the consolidation plan (v7j `docs/superpowers/plans/2026-11-15-branch-consolidation.md`, section 3, with its 2026-11-15 addendum).

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
| `demo/campaign-kits` | v7j | `781598d` 2026-11-15 docs: record convoy rerun videos and combined video v2 (the render job's commit; before this pass's commits; `4cacf55` at Rev 2) | `demo/ib10-recorded-demo` | yes | demonstration campaign, convoy rerun (`DC` 14), glossary, reports, this index | 5 |
| `analysis/failure-cause-classification` (new) | v7q | `0b6a91b` 2026-11-15 docs: add both raters' failure-cause rating records | `demo/campaign-kits@b70d925` | yes | classification, interception table | 5 (new) |
| `demo/validation-guard-contacts` (tip moved since the plan) | v7n | `a412949` 2026-11-15 docs: correct stockout count and reverse finding in validation report | `demo/campaign-kits@cc1313d` + v7l + v7m | yes | five-robot validation take | 5 |
| `test/safety-mechanisms-scripted` (new, finished) | v7s | `74dd45c` 2026-11-15 docs: report scripted safety-mechanism test results (registration `b000103`; `99edbf3` at Rev 2) | `demo/validation-guard-contacts@a412949` + v7l (merge `527707a`) + v7p (merge `af5a9df`) | yes | scripted safety tests and their report | 5 (new) |
| `fix/convoy-hold-queued-robots` | v7o | `d85d1ed` 2026-11-15 test: cover queued-crosser hold under feasibility gate modes | `demo/campaign-kits@4e5476b` | yes | queued-robot hold | 5 |
| `fix/convoy-yielder-feasibility` (new, finished) | v7t | `272ad4a` 2026-11-15 docs: correct cvy budget wording and add verification (feature `a0311b0`, replay `a7635b7`, report `886a90f`; no own commit at Rev 2) | `fix/convoy-hold-queued-robots@d85d1ed` | yes | counterflow yielder correction, offline replay, report, `cvy` kit | 5 (new) |
| `feat/demo-panel-renderer` | v7g | `51d9b1a` 2026-11-15 docs: note queued-robot hold line in presentation renderer (`d43028d` at Rev 2) | `feat/convoy-live-resolution` | yes at 15:52Z (one modified file earlier, while the render job ran) | demo video renderer | 6 |
| `feat/v4-per-cluster-parity` | v6d | `2582f45` 2026-11-15 docs: apply reader-facing names to register and change list (before this pass's register commit; `f39bc8c` at Rev 2) | `feat/v4-per-cluster` | yes | evidence register, thesis change list | 7 |
| `feat/v4-refusal-feedback` | v7b | `384e948` 2026-11-14 docs: record finished-plan hiding for refusal feedback | `feat/v4-per-cluster` | yes | refusal feedback | 7 |
| `docs/thesis` | thesis | `e1bbce6` 2026-11-15 docs: add physical testbed setup and Appendix D configs (`7e589d8` at Rev 2; moved five times during this pass, section 10) | v4 line | **no** at 15:49Z: `thesis/chapters/08-conclusion.typ` modified (the report-writer session, working) | thesis; the report-writer session's own work (read-only here) | 7 (optional) |

**Final tips of the two finished jobs** (re-read at 15:45Z; neither has a remote-tracking ref, so both are unpushed):

- `test/safety-mechanisms-scripted` (v7s): `74dd45c` 2026-11-15 22:33 +0700 "docs: report scripted safety-mechanism test results"; clean.
- `fix/convoy-yielder-feasibility` (v7t): `272ad4a` 2026-11-15 21:17 +0700 "docs: correct cvy budget wording and add verification"; clean.

**Other worktrees with uncommitted or untracked files** (15:45Z):

- Main checkout `vgu-vlm-swarm` (`fix/deadlock-collision-resolution`): 16 untracked entries: `reports/`, `uv.lock`, and 14 `research_notes/` entries.
- `.claude/worktrees/m4-phase2-nav2-stack`: 7 entries: 6 modified (`isaac/vgu_sim/cmd_vel_watchdog.py`, `cmd_vel_watchdog_node.py`, `swarm_simulation/config/nav2_params.yaml`, `launch/nav2_robot.launch.py`, `tests/unit/test_cmd_vel_watchdog.py`, `test_nav2_params.py`) and 1 untracked session transcript (not re-listed file by file).
- thesis: see the table (another session's work in progress, not touched).

---

## 5. Deliverables

All files below are **git-ignored and exist only on this Mac**; no off-machine copy exists (section 7). Paths are absolute (Rev 3); `V` = `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7g/data/demo/campaign/`. md5s are quoted from the reports or the render job's final `.md5` files (the render job finished and committed at 15:51Z).

| Deliverable | Path | md5 (where recorded) |
|---|---|---|
| Engineering cut, per take (5) | `V` + `ibD_t05_a1_panel.mp4`, `cvD_t01_a1_panel.mp4`, `hoD_t01_a1_panel.mp4`, `m5D_t01_a1_panel.mp4`, `ER2LIVE_20260930_panel.mp4` | `fdf07a82fcb657b738c44a89bfbe3dae`, `824319447d05aaef6623158d00d2818f`, `2aa6534ad508d3440e51822fdcd3f0f0`, `33e9f5eedd7fb56edd007d8b728ea8c0`, `93cbfe7108e6a9ca9a71fc4c7c79bd47` (`DC` Final Summary) |
| Engineering combined | `V` + `demo_campaign_combined.mp4` (v3) | `de8cb6ed07e42008b8acb3f9274352db` (`DC` 9) |
| Convoy rerun take, engineering and presentation cuts (Rev 3) | `V` + `cvY_t01_a2_panel.mp4`; `V` + `presentation/cvY_t01_a2_presentation.mp4` | engineering `92fc06a855ae0527479d1bfe49af2fbc`; presentation `60c4ee7c46e9f6ded4f8f3496589e1e0` (the render job's final `.md5` files; `DC` Rev 14, section 14.9, `781598d`). The presentation caption was corrected before this render: the correction did not fire because, with robot_2 yielding, every crossing robot starts on the opposite side (not "room to back out") |
| Presentation cut, per take (5) | `V` + `presentation/*_presentation.mp4` | `8c09f71fa34b727b82d6757692df76d7` (intersection), `f96210bc7958884a49b8f17ca7bc287e` (convoy), `32176fba6aeb7411a0036da51baf34f1` (head-on), `a51992a27877f2d801cb56f522ab34a6` (five-robot), `cfabf6cda7424d511e3cf3dc9f762722` (earlier recorded head-on run) (`DC` 13.1 as of `4cacf55`, which updated the md5s after the wording-fix re-render) |
| Presentation combined | `V` + `presentation/presentation_combined.mp4` | v2 with the convoy rerun: `3d45c8d850952f9b7013bd154957034a` (render job's `presentation_combined.md5`; `DC` Rev 14). The Rev 12 version is kept as `V` + `presentation/presentation_combined_v1.mp4`, `ce8f4101b16e544372b2798cf2ce3c20` |
| Per-scenario demo package | `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-demo-package/` (`00_README.md`; one folder per scenario with videos, stills, logs, `other_takes.md`) | per-file md5 in each scenario `README.md` |
| Thesis figures: scene stills (14), clean and original | `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-demo-package/figures_for_report/scene_clean/` and each scenario's `images/scene_original/` | per-file md5 in `figures_for_report/README.md` |
| Thesis figures: take 5 decision flow, simple (main text) and detailed (appendix) | `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-demo-package/figures_for_report/flow_diagram/vlm_flow_take5_simple.{pdf,png,typ}`, `vlm_flow_take5.{pdf,png,typ}` | simple pdf `f0933aa00205b87db1cab2ac519a25e5`, png `b837b64c7727c344ef5338a9338f86bf`; detailed pdf `cbdfcaf2ec203cc1c39a276cacffe5d8`, png `359b3c7d152e392fa2d853094b054338` (computed for this page) |
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

Campaign ledger, Rev 3 (`ledger_dmc.py status` from the kit copies `sft/kit` and `cvy/kit`, read-only at about 15:40Z; ledger md5 `70ad267505afc85828ccd4ecefef2983` unchanged before and after; 65 rows plus header). Both kit copies print the same campaign line but different per-scenario caps, and neither lists the keys `m5v`, `cvy` or `sft`; those three are taken from the ledger's own rows and the reports. At Rev 2 (13:49Z, kit copy `cvh/kit`) the totals were 25,667 s and $2.8637.

| Item | Value |
|---|---|
| VM seconds | **29,172 s of 43,200 s**: intersection 8,239; convoy 8,149; head-on 1,302; five-robot 3,833; five-robot validation take 4,144; convoy rerun (`cvy`) 1,556 (share 7,200 s, registration 13.6); scripted safety tests (`sft`) 1,949 (cap 7,200 s). The parts sum to the campaign line |
| API spend booked | **$2.8784 of $10**: intersection $2.3335 (includes the $2.00 offline booking and the $0.2705 Sonnet check), convoy $0.3751, head-on $0.0164, five-robot $0.0685, five-robot validation take $0.0702, convoy rerun $0.0147 (take $0.0132 + probes $0.0015), scripted safety tests $0 (mock backend, no probes) |
| Ledger rows of the two jobs | `cvy`: wall 1556 (VM start 14:27Z to TERMINATED 14:53Z), bring-up abort `cvY_t01_a1`, valid `cvY_t01_a2`. `sft`: wall 1949 (to TERMINATED 15:30:51Z), takes `sfT_t01_a1`, `sfT_t02_a1`, spend 0.0000. Each also spent about 2 min in one failed (stockout) start, not booked |

**Spend the reports record but the ledger does not book:**

- Convoy held-robot prompt check: $0.2990 at list price, $0.3738 in the check's own ledger units (list × 1.25) (`CH` section 3). Not in the campaign ledger.
- The $2.00 offline booking (registration section 10.5: "roughly $1.6–2.0") is consistent with the plan check's reported ledger spends $1.384 and $0.583 (sum $1.967; plan-check report lines 153 and 467). That mapping is inferred.
- Outside the campaign: intersection run 2's VLM arm $0.056; the 14 November offline prompt replays ran on their own provider budgets and are not totalled here.
- GPU stockouts before VM start (about 24 min five-robot, about 26 min convoy take 5, about 34.5 min five-robot validation take) are not VM seconds and are not booked.

**Reconciliation.** Booked $2.8784; with the unbooked convoy check added, $3.2522 if it is counted in its ledger units, or $3.1774 if counted at list price. (At Rev 2: $2.8637, $3.2375, $3.1627.) The owner-brief figures quoted in the reports fit the Rev 2 totals: "≈ $3.07" (validation report section 5) equals $2.6975 + $0.3738, and "≈ $3.2" (registration 12.4) equals $2.8637 + $0.3738; both matches are inferred. **Range: $2.88–$3.25 of $10.**

**Remaining:** 14,028 s of VM time and about $6.75–$7.12 of API budget under the campaign caps (derived from the lines above).

---

## 7. Open Decisions for the Owner

Collected from the reports; no recommendation beyond theirs.

| Decision | Source |
|---|---|
| Integration target (W, `main`, or a new branch from the pin), pushing branches as backups, tagging the pin | consolidation plan Q1–Q3 |
| Geometric contact logging: land always-on or behind a key | consolidation plan Q4 |
| Off-machine backup of evidence and videos (about 1.0 G + 375 M + 318 M + 417 M + 281 M + 52 M at Rev 2, plus the `sft` and `cvy` bundles and the new renders since, plus the older directories in Q5) | consolidation plan Q5; demo package README |
| Disposable worktrees (check each `data/` for unique evidence first) | consolidation plan Q6 |
| `docs/thesis` on the integration branch or separate | consolidation plan Q7 |
| Escort obstacle guard: E18 margin rule (a/b/c); registration amendment before any scored use | `DC` 10.1; v7l report section 4 |
| Reverse obstacle guard: shortening (APPROVED by the owner in session on 2026-11-15; approved but not yet built). Source: the owner's pasted plan of that date, summarised: shorten the reverse when a useful and safe distance remains, strict refusal as the fallback; a refused reverse keeps the 8-second wait with explicit logs; mechanisms default-off and not enabled together in a first validation run. The earlier note that no report records the approval is superseded by this entry (the guard report still calls it an open option, 8.8). Why it matters: in the interception table the guard refuses 29 October-pilot legs, 15 of them false positives (R23), and every refusal becomes an 8 s wait | owner's pasted plan, 2026-11-15; v7l report 8.8; v7q reconciliation 7.2 |
| Other manoeuvre checks (junction recede and release legs, declared-geometry yield back-out and pull-off): APPROVED by the owner in session on 2026-11-15 to be done one at a time, each with its own key, test and replay, starting with yield back-outs (the yield back-out guard is approved but not yet built); stall abort prioritised. Source: the owner's pasted plan of 2026-11-15. The earlier note that no approval record was found is superseded by this entry | owner's pasted plan, 2026-11-15; v7l report 8.2 |
| Stall abort follow-ups: hold an aborted backup with a short wait?; bag `/clock` and `/odom` in a later live take. The deterministic live validation was done as the scripted safety test (R27). Not yet exercised live: `input_stale`, turn-phase, escort and pull-off stalls, latch-held robots | v7p report sections 7, 9; `SFT` 4 |
| Plan state shown to the model ("robot_1: wait (done)" after a 1.3 m back-out) needs a prompt-input change, excluded so far | v7r report 4.1, 8 |
| Plan-dispatch fix level beyond the record: prompt contract, verifier, or plan-driven `reverse`/`reroute` grounding (registration amendment) | rubric report Part A section 4, 8.4 Q4 |
| Convoy: the yielder-feasibility fix is built (counterflow yielder correction, default off) and ran armed in the convoy rerun, which resolved without it firing; whether to test the correction live (a take where the model names robot_1, or a scripted decision), and whether the hold and the correction go into the registered convoy experiment (registration amendment needed; its VLM arm is unrun) | `DC` 5.5, 12.4, 14; v7o report 6; `CVY` 5.6–5.7 |
| Intersection options-detail wording: render the detail so it cannot be read as an action, or narrow parser tolerance (a third fix cycle) | `DC` 2.5 |
| Log-filter lines in the engineering panel (`yield re-grounded`, `dispatch_order_source`, refusal lines) | `DC` Final Summary |
| Intersection yielder gap stays open by owner decision | `DC` Final Summary |
| Post-fix live comparison: design D1, D1+C or D2, scope and budget; whether a scripted five-robot arm is wanted | rubric report 8.3–8.4 |
| Clock mapping for the coordination-off arm: failed its pre-declared test (5 of 28 bundles above 2.0 s), not applied | v7q reconciliation section 8 |
| Unverified audit count (R26): re-check or cite as unverified | `DC` 11.4; `REG` |
| Builder-parity test of the authored obstacle boxes (`pxr`): done. It ran and passed for the first time inside a started Kit app in the scripted safety-test session (`1 passed`); it was skipped again in the convoy rerun (bare `python.sh`). Open only: whether the Kit-app method should replace the bare step in the kits | `SFT` 5; `DC` 12.5, 14.1 |
| Escort obstacle guard live: no take could force a blocked escort reproducibly (1 of 3 recorded snapshots); decide whether to test it live at all | `SFT` 4 |
| Full unit suites pending on four branches: plan-dispatch mismatch record (v7r), counterflow yielder correction (v7t), the scripted safety-test merged tree (v7s; targeted suites 1670 passed) and the stall abort's post-review commit `7438929` (v7p; full suite verified at `1dbac68` only). Each was blocked by the 2 GB free-swap rule | v7r report (Full unit suite); `CVY` 4; `SFT` 6; v7p report, verified/inferred table ("Full unit suite") |
| Thesis independent review: open SHOULD FIX items not checked here (section 10.4) | `docs/reports/2026-11-15-thesis-independent-review.md` 7.3 |
| Demo package `needs_decision/fig_intersection_panel_dispatch_t33p07.png`: keep as the "format of the demonstration videos" figure, or drop | package `figures_for_report/README.md` |

---

## 8. The Two Jobs That Were Running (Finished; Filled in Rev 3)

At Rev 2 both jobs were still running and this section held placeholder blocks. Both have finished; the items below are quoted from their reports. Neither worktree was touched by this session.

### 8.1 Scripted Safety Tests

Worktree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7s`, branch `test/safety-mechanisms-scripted`, kit `sft` (v7j `data/logs/vm_runs/demo_campaign/sft/`, git-ignored). Report `SFT` (`74dd45c`); registration `docs/superpowers/specs/2026-11-15-safety-mechanism-scripted-tests.md` (`b000103`, committed before the VM start). Two takes in one VM session (14:58–15:30Z), five-robot pickup-and-delivery scene, the same scripted reverse of robot_5, robot_3 and robot_1 in both.

| Item | Result (`SFT` section) |
|---|---|
| Reverse obstacle guard (take 1, `sfT_t01_a1`) | **PASS** (2). Refused at sim 40.83 s with `reverse_hits_obstacle:robot_5:obstacle_3:0.293` (predicted 0.295–0.349), three 8 s waits dispatched and COMPLETED, 0 reverse hand-overs, maximum backward displacement 0.000 m for all three robots over 10 s, 0 contact rows (closest static approach 29.7 mm). Unexpected: a second tag for robot_1 into the south wall `obstacle_6` (0.841), because robot_1 was turning (heading 0.453 rad); the refusal was decided by robot_5 either way |
| Stall abort (take 2, `sfT_t02_a1`) | **PASS** (3). robot_5 pinned on `rack/NW_west` from GT 46.30 s; `stall abort … reason=stall … measured_m=0.071 expected_min_m=0.075` at sim 49.133, 2.21 s after contact (registered limit 5.0 s; the replay predicted 2.3–3.0 s); status FAILED with the reason text; one zero twist and no backup-like twist in the next 5 s; robot_1's clear reverse COMPLETED without abort. robot_3's reverse FAILED through the existing latch fast-fail (robot_2 re-approached it), not through the stall abort |
| Escort obstacle guard | **No take** (4): a blocked escort was reproducible in 1 of 3 recorded snapshots, so it stays armed once live (five-robot validation take) and validated offline only |
| Geometric contact logging | First live contact recorded (24 rows) and equal to the offline recompute row by row in both takes (1017 and 1313 rows, 0 mismatches) (2, 3). The simulator-only builder-parity test ran and passed for the first time, inside a started Kit app (5) |
| One mechanism enabled per take (owner rule) | Yes: take 1 reverse guard alone, take 2 stall abort alone, verified by the deployed loaders, the startup lines and the artifact parameters (2, 3, 7); contact logging (no key) on in both |
| VM and API | 1,949 s booked under `sft` (cap 7,200 s); $0 (mock backend, 0 tokens); 1 stockout start, 0 bring-up aborts, restore OK (1) |
| Unit tests | Targeted suites on the merged tree 1670 passed, 129 skipped, 0 failed; full unit suite **pending** (swap rule not met) (6) |
| Tip | `74dd45c` 2026-11-15 22:33 +0700, clean, unpushed |
| Limits | n = 1 per mechanism; scripted decision, not VLM behaviour, never pooled; declared boxes only; odometry is a simulator physics pose; latch-held robots (blind spot), `input_stale` and other stall paths not exercised |

### 8.2 Convoy Non-Arrival Inspection, Yielder-Feasibility Fix and Rerun

Worktree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7t`, branch `fix/convoy-yielder-feasibility`; rerun kit `cvy` (v7j `data/logs/vm_runs/demo_campaign/cvy/`, git-ignored).

| Item | Result |
|---|---|
| Inspection | Takes 1–3: the model named only the standoff pair, so the queued robots were released uncommanded and followed through the gate; all four latched. Takes 4–5: the hold kept the queued robots, but the model chose robot_1, the platoon-side robot, as yielder, so robot_2 was escorted toward the held robot_3 and latched 0.418 / 0.419 m from it. The existing feasibility gate scores only static-obstacle retreat room and never fires in the convoy (0 of 49 first-trigger yields) (`CVY` Summary, 1, 2.1) |
| Fix | Counterflow yielder correction, key `grounding_yield_counterflow_swap`, default off (`a0311b0`): when a legacy single-corridor yield has a crosser waiting on the yielder's park side, the yield is handed to another named robot whose crossers all start opposite it, else refused. 51 unit tests; offline, first-trigger yields grounding into the resolving sequence 1 / 27 / 49 of 49 for neither key / hold only / hold + correction; 43 later convoy and 15 other-scene decisions unchanged; full unit suite pending (`CVY` 3–5) |
| Rerun decision | Run on the owner's request ("also inspect why robots in convoy demo did not come to destination, if ok rerun the demo", `DC` 14); registered as registration section 13 (`e71c90e`), wall share amended to 7,200 s before the VM start (`8e316fd`) |
| Rerun outcome | One valid take `cvY_t01_a2` (one bring-up abort before it): **resolved, 4/4 arrived**, label "Resolved — grounder held the queued robots; model chose strategy and yielder". The model chose robot_2 itself; the hold added robot_3 and robot_4; the correction was armed and did not fire, because with robot_2 yielding every crossing robot starts on the opposite side, so it is untested live. Closest non-exempted pair 0.497 m; 0 hard-floor stops; no contact in the offline recompute (`DC` 14.2–14.5) |
| VM and API | 1,556 s booked under `cvy` (share 7,200 s), $0.0147 (`DC` 14.1, 14.7) |
| Tip | `272ad4a` 2026-11-15 21:17 +0700, clean, unpushed; the rerun's report section is on v7j (`2cafbf7`, `3866ec1`) |
| Limits | n = 1, illustrative; a grounder result, not evidence that the VLM resolves convoy congestion; the goal-side margin held by 0.047 m |

---

## 9. What to Do Next, in Order

1. Owner review of section 7 (open decisions, including the new rows for the counterflow yielder correction, the escort guard live test and the pending full unit suites).
2. Run the four pending full unit suites (section 7) once the 2 GB free-swap rule can be met, one process at a time.
3. Build reverse shortening and the yield back-out guard (both approved, not built), each default-off with its own key, test and replay, enabled one at a time.
4. Off-machine backup of the evidence directories, the videos and the demo package (including the `sft` and `cvy` bundles), before any worktree is removed.
5. Consolidation per the plan and its 2026-11-15 addendum, now with the two finished branches placed in Stage 5 (re-run `git merge-tree` against the integration branch before each stage).
6. Thesis: the report-writer session's open items from the independent review (section 10.4); confirm with that session the points listed in 10.5.

---

## 10. Thesis Report Session

The report-writer session works on branch `docs/thesis`, worktree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-thesis`. Everything here was read with read-only git commands; nothing in that tree was edited. The session was still committing during this pass: its tip moved `fbc5d00` → `87a6d7d` → `f59ffe8` → `e8ee52e` → `a38d5fc` → `e1bbce6` between 15:20Z and 15:47Z. Facts below are pinned to **`e1bbce6`** (2026-11-15 22:46:26 +0700, "docs: add physical testbed setup and Appendix D configs"), clean at 15:47Z; at 15:49Z `thesis/chapters/08-conclusion.typ` was modified again (uncommitted, not read).

### 10.1 State

- **Tip** `e1bbce6`; 70 commits on 2026-11-15 (since 00:00 local time, up to `e1bbce6`).
- **Nothing is pushed:** `docs/thesis` has no upstream (`git rev-parse @{u}` fails) and no remote branch contains the tip.
- **Word count.** Raw `wc -w` of the chapter sources at `e1bbce6`, Typst markup included (so an overcount): chapters 00–08 31,605; chapters 01–08 30,742. The independent review measured about 30,060 for chapters 00–08 at `231baac` by its own method. Both are at or slightly above the top of the 25,000–30,000-word target; a markup-free count was not made.

### 10.2 What Its Commits Did on 2026-11-15 (Grouped)

- **Front matter:** title page retitled "Project Report" (`573d17a`); acknowledgements added (`2bf9b1a`, later extended, `e6e8fa9`); copyright page added (`b44ba52`); declaration-of-authorship page dropped (`4d30900`); abstract written, shortened, then fixed (`a5340b5`, `24190f9`, `88d8cfe`, `231baac`, `a38d5fc`).
- **Over-claim removal:** chapters 1–5 corrected, contact and "collision-free" wording removed (`222666d`, `d500e36`, `b11f805`, `266aaac`).
- **Chapters written:** Chapter 5 analysis and methods (`869c869`), Chapter 6 results and appendix B (`846f7c7`), Chapter 7 discussion (`479f54f`), Chapter 8 conclusion and future work (`449c492`).
- **Failure-cause method and results:** method section and shells (`ccab070`), results and interception tables filled (`eb73f0d`), rating procedure (`9fece0a`), neutral conclusions in Chapters 1, 7, 8 (`7e589d8`).
- **Figures and stills:** take 5 decision-flow figures and campaign stills (`9d22c9a`); demonstration stills moved to appendix B (`4030ecf`).
- **Corrected plan counts:** plan-dispatch corrected counts (`2531c04`); denominators fixed (`a38d5fc`).
- **Appendices:** appendix B (`12fdc38`, `846f7c7`); appendix C with the recorded VLM prompts (`9b71aa3`, `36655f8`); appendix D for the physical testbed (stub `3495526`, content `e1bbce6`).
- **Naming pass and length cut:** reader-facing names and "coordination layer" applied chapter by chapter, and every chapter tightened toward the 25,000–30,000-word target (`a2e42e0` to `9d6a5c5`, 21:19–21:35 +0700), then fixes to restored scope and evidence links (`b8439b3` to `7316233`).
- **After the cut:** review follow-ups and the restored abstract hardware clause (`231baac`); convoy rerun take added, hardware and pilot-plan claims fixed (`8945bb8`, `fbc5d00`); scope narrowed to RQ1–RQ3, review fixes, scripted safety tests added (`87a6d7d`); campaign take count (`f59ffe8`); RQ4/RQ5 worded "not tested" with the exploratory runs noted (`e8ee52e`); denominators, safety wording and abstract length (`a38d5fc`); physical testbed setup and appendix D configurations (`e1bbce6`).

### 10.3 Owner Decisions That Reached This Side

| Decision | Date | Where recorded | State at `e1bbce6` |
|---|---|---|---|
| (a) Reader-facing names, Layer 2 = "coordination layer" | 2026-11-15 | Naming glossary Rev 3 (v7j `docs/guides/naming_glossary.md`, `7a045d9`); this index Rev 2; evidence register Rev 9 | Applied in the chapters (naming commits above) |
| (b) Report length 25,000–30,000 words | 2026-11-15 | Not found in any committed document in v7j, v6d or the thesis tree; the independent review cites it as "the 25–30 k target". To confirm with the report-writer session where it is recorded | About 30.7–31.6 k raw words (10.1) |
| (c) Research-question scope: RQ4 and RQ5 moved to Future Work, RQ1–RQ3 answered in Chapter 8 | 2026-11-15 (owner's words in the planning session's brief; quoted in 10.3.1) | Owner's instruction relayed by the planning session; the thesis records it in its Introduction's "Scope change" paragraph | **Applied** (`87a6d7d`, wording refined in `e8ee52e`), see 10.3.1 |
| (c′) Ruling on (c): the two questions **were** in the first registered design with planned tests, so the thesis must not say "not preregistered"; say "not tested" and mention the exploratory runs as not reported as evidence | 2026-11-15 | Planning session (ruling after it checked tag `prereg-v1`, `569d95c`); thesis Evidence Index rows 1.03, 1.16, 5.01 | **Applied** (`e8ee52e`); "not preregistered" does not occur in the thesis chapters |
| (d) Independent review of the thesis | 2026-11-15 | Copied to v7j `docs/reports/2026-11-15-thesis-independent-review.md` (this pass), reviewing `88d8cfe` working tree to `231baac` | MUST FIX items all addressed, see 10.4 |

#### 10.3.1 Research-Question Scope at `e1bbce6`

The owner's instruction (2026-11-15): "RQ4 and RQ5 were not preregistered. I prefer to narrow the thesis to the research questions actually investigated. Please move RQ4 and RQ5 to Future Work rather than retaining them as unanswered core research questions. Keep RQ1–RQ3 as the main research questions, and ensure they are explicitly answered in Chapter 8 with the appropriate evidence and limitations. Make the scope adjustment transparent, without implying that RQ4 and RQ5 were tested or that the change was preregistered. Align the Abstract, Introduction, Research Questions, Methodology, Discussion, and Conclusion with the revised scope. Do not change the experimental results or weaken the negative findings."

The first clause turned out to be factually wrong: the first registered design (tag `prereg-v1`, `569d95c`, 30 September 2026) lists RQ1–RQ5 with planned tests; no confirmatory data were collected under it and no later design tested the two. The owner then ruled (c′) as above.

What the tree shows:

- **Research questions:** Chapter 1 lists RQ1–RQ3 only; RQ4 and RQ5 occur only in Evidence Index rows 1.03 and 5.01, which describe the first design.
- **Transparency sentence** (Chapter 1, "Scope change"): "No confirmatory data were collected under that design, and no later design tested the two. They were not tested in this work: no registered or controlled comparison addressed them. Exploratory runs before that design was tagged touched both, with first blocker-kind answers in a funded battery and two gpt-4o recovery runs on a blocked head-on scene #ev("1.16"); they are not reported as evidence here. Both questions were moved to Future Work (@sec:concl-future) when this report was finalised; the narrowing was made after the experiments, is part of no registered design, and changes no result."
- **Methodology:** "Those two were not tested; the exploratory runs that touched them before the tag are not reported as evidence #ev("1.16"). Moving them to Future Work when this report was finalised narrowed the scope after the experiments, is part of no registered design, and changes no result."
- **Chapter 8:** answers RQ1 ("answered in part"), RQ2 ("negative for the model") and RQ3 ("negative at the decision level") by number, and says "two further questions from the first registered design were not tested and are future work"; Future Work carries "Semantic advantage" and "Closed-loop adaptation", each marked as moved from the research questions.
- **Discussion:** the wrong plan-state feedback shown to the model ("wait (done)" for a robot that backed out) is stated as a limitation (Chapter 7).
- **Abstract:** asks whether the VLM classifies the jam, chooses strategies that clear it, and names an effective yielder and order (the three questions).
- **Evidence Index:** scripted safety tests = row 6.86; convoy rerun = rows 6.84 (take) and 6.85 (non-arrival and correction); row 6.16 cites the evidence register at `2582f45`; row 1.16 cites the pre-tag exploratory runs.

### 10.4 Independent Review: MUST FIX Items at `e1bbce6`

The review (copied this pass; reviewed `88d8cfe` working tree to `231baac`) listed three MUST FIX items. Facts at `e1bbce6`:

1. **Abstract hardware sentence** (scenario E had a FAILED robot): addressed. The abstract now reads "the model chose a bounded back-out each time and all but one robot recorded it complete (one run each, no goals, illustrative)" (the "all but one" wording since `8945bb8`).
2. **Chapter 8 answers the questions by number:** addressed for RQ1–RQ3 (10.3.1); RQ4/RQ5 are no longer research questions.
3. **The two `#todo[VERIFY]` boxes in Chapter 5 and the VERIFY text in row 5.12:** addressed. No `[VERIFY]` and no `#todo` remain in the chapters or evidence files at `e1bbce6` (the Appendix D `#todo` stub of `f59ffe8` was replaced by content in `e1bbce6`); row 5.12 now gives the reason (the v1/v2 track stopped when its host VM was deleted on 2026-11-12).

Not checked here: the review's SHOULD FIX and NICE items. Its section 4.3 ("scripted safety tests: still registered only") is stale since `74dd45c`; the thesis cites the results as row 6.86. Its "convoy rerun not integrated" point is also superseded (rows 6.84, 6.85).

### 10.5 Hardware Material and Items to Confirm

- **Physical testbed.** The report-writer session is merging physical-testbed (Zenoh) material from the owner's team into Chapter 4, Chapter 6 and appendix D, cited as team notes that are not in the repository; this session has no source for it and has not checked it. In the tree at `e1bbce6`: appendix D says its configurations are "taken from the team's testbed notes, which are not in the repository"; Chapter 4 says "the code that ran is not in the repository's history" and that the hardware runs "are never pooled with the simulation results". The Chapter 6 part was not checked.
- **To confirm with the report-writer session:** where the 25,000–30,000-word decision is recorded; whether the further cut is planned (raw counts are above 30,000); whether the former RQ4 check (blocker-kind answers in the tagged overnight-findings report, "Funded battery 1") was verified by that session against the tagged tree; and its own hand-back of decisions, which was requested and not seen here.

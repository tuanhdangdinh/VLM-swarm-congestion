# Head-On Asymmetric Family - VLM Yielder vs Position-Only Rule, Offline Re-Score

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: offline re-score of every recorded live decision on the head-on asymmetric family, plus the September replay call logs, against the scenario oracle, the position-only classical rule and M3's grounded yielder. Includes the robot_1 / first-listed confound 2x2.

---

## Question

In the recorded head-on asymmetric family, does M2 (the VLM) name the oracle-correct
yielder more often than a position-only rule? If it does, is the advantage real, or
is it explained by the models' known preference for `robot_1` or for the
first-listed robot?

**Evidence grade:** pilot data, seed mostly 42, post-hoc analysis. The analysis was not
pre-registered. No API was called, no VM was used, and no evidence file was modified.
Counts accompany every proportion. The report gives no p-values and no intervals.

---

## Data Used and Excluded

### Live decision artifacts

All `decisions/` and `m5_decisions/` directories under `data/logs/vm_runs` were
scanned in five trees: `vgu-vlm-swarm`, `-v3`, `-v6d`, `-v7a` and `-v7d`. Each
bundle's scenario was read from `run_manifest.json` (`scenario`) and from
`CONDITION.txt` (`scenario=` or `variant=`).

| Set | Bundles | Artifacts | Reason |
|---|---|---|---|
| Not a head-on asymmetric variant (intersection, `head_on_deadlock`, priority scenes, free-flow) | 316 | 2,541 (with the next row) | out of scope |
| No scenario record (`intersection_smoke/_rescore`, `t2b_smoke/_rescore`) | 4 | (included above) | out of scope |
| Head-on asymmetric, scripted `mock` backend (`layer2off_pilot`, `v3_step0`, `battery_v2_harvest`, `apparatus_smoke`, `harness_optionb`, `m4fix/M1`, `funded_battery1`, `s1_resume`) | 13 | 143 | the decision is a script, not a model |
| **Head-on asymmetric, real model** | **93** | **859** | **analysed** |

No `request_id` appears twice. No T0 probe artifact falls in the analysed set.
`head_on_asymmetric_wopen_eopen_o0` has **no live data**. The 2026-09-19 runs A and B
cited in `docs/reports/2026-09-18-head-on-family-validity.md` are not on disk, so
they are not re-verified.

Two gpt-4o model labels are merged into `gpt-4o`. `openai` (15 artifacts) is the
2026-09-24/25 backend id, which predates `reasoner_config_effective`.
`gpt-4o-2024-08-06` (12 artifacts) is the `served_model` of the 2026-09-30 and
2026-10-06 runs.

### Oracle, verified per variant

`correct_yielder` and `fcfs_yielder` were read from each variant's `oracle:` block in
`isaac/config/scenarios/family/head_on_asymmetric_*.yaml` (v7d tree). They agree with
`family_manifest.csv`:

| Variant | Blocker | Correct yielder (only feasible one) | Manifest `fcfs_yielder` | Manifest label = oracle? |
|---|---|---|---|---|
| `w0p2_eopen_o0`, `_bshort_o0`, `_gshort_o0` | west, x = -1.85 | `robot_2` | `robot_2` | yes |
| `wopen_e0p2_o0`, `_bshort_o0`, `_gshort_o0` | east, x = +1.85 | `robot_1` | `robot_2` | no |
| `wopen_eopen_o0` | none | `robot_1` (both feasible) | `robot_2` | n/a, no data |

The blocker coordinate rendered in each prompt's `Static obstacles:` block was checked
against the variant's blocker: 837 artifacts agree, and the 22 without obstacle text
cannot be checked this way. No artifact disagrees. M3's
`yield_regrounded_reason` text names the same feasible robot wherever it fired.
The September replay rows' own `correct_yielder` also agrees, in 1,686 of 1,686
artifact replays and 540 of 540 synthetic-probe calls.

`robot_1` always spawns west and `robot_2` always spawns east. So in this family,
**"`robot_1` is correct" and "the blocker is east" are the same event.** A model that
always names `robot_1` scores 100% on east variants and 0% on west variants.

### Offline replay call logs (separate strata, never pooled with live)

| Set | Calls | Model | Order manipulated? | Use here |
|---|---|---|---|---|
| `2026-09-25-frame-replay/calls.jsonl` (batch 1: arms R, grey, O, M, S, D) | 894 | gpt-4o | yes (O, S) | 2x2 on 6 real standoff scenes |
| `2026-09-26-batch2-replay/calls.jsonl` (S2, X, F) | 792 | gpt-4o | yes (S2) | 2x2; split into pre-rewrite (187) and post-rewrite (605) by the `image_fallback_after_attempts` field |
| `2026-09-25-presentation-order/*/calls.jsonl` | 540 | gpt-4o, gpt-4o-mini, ER-2 | yes | separate synthetic-image stratum |
| `2026-09-25-refusals/calls.jsonl` | 240 | gpt-4o, gpt-4o-mini | no (stored order) | refusal counts and a near-empty 2x2 |

All files are under `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-thesis/data/experiments/`.

---

## Method

- **Positive analysis.** `congestion_detected = true` and the decision names a
  yielder, in `yield_robot` or in a `yield` leg of `proposed_plan`. All 97 live
  positives carry it in `yield_robot`, all with `strategy = yield`. The parsed
  `yield_robot` matched the last `yield_robot` in `raw_text` wherever both exist, so
  the decision field holds M2's raw answer, before any M3 re-grounding.
- **Independence unit: the run (bundle).** "Run level" means the first positive
  analysis per run, ordered by `scene.stamp`. Grouping by `(bundle, episode_index)`
  gives the same 92 units, because no run has positives in two M5 episodes.
  Analysis-level counts are also shown; analyses within a run are not independent.
- **First-listed robot** was parsed from the rendered `Robot states` block of
  `prompt.user_prompt`, not from `scene.robots`. It agrees with
  `robot_presentation_order` on all 840 artifacts that carry an order.
  - The 19 artifacts of 2026-09-24 (overnight runs R1-R4) carry no order field. The
    order was configured but not recorded: the overnight report §B lists R1, R3 and
    R4 as `id_desc` and R2 as `id_asc`. The prompts confirm it, because
    `20260924_195708`, `_203437` and `_205009` list `robot_2` first, despite the
    header `sorted by ID`.
  - No analysed prompt contains a "first listed" clause.
- **Rule yielder (position-only).** Three sources:
  1. `recorded_shadow`: the recorded `shadow_classical.decision`, present from
     about 2026-09-27 (29 of the 92 run-level units).
  2. `recomputed_scene_log`: `reasoning.baselines.classical_reasoner.resolve_classical`
     (v7e tree, `config/rag.yaml` params) run on the scene-log history of the
     artifact's own `session_id`, over the 60 s before `scene.stamp`, plus the decision
     scene (63 of the 92).
  3. The manifest label `fcfs_yielder`, which is static per variant.

  Where the rule's latest-frame classification is not `head_on`, it names no yielder.
  That is reported as "rule none", not dropped.
- **M3-grounded ("dispatched") yielder.** `dispatched_command` is absent from every
  positive head-on artifact, so this column is always **derived**:
  - no grounded command, or `yield_refusal_reason` set: no yielder;
  - `yield_robot_grounded_from` set (swap): the robot named "feasible" in
    `yield_regrounded_reason`;
  - otherwise: M2's yielder.

  This is M3's output. Dispatch itself was not checked against M4 logs.
- **Image condition.** `fallback_neutral` = `diagnostics.image_fallback_used`.
  `real_frame` = `frames/<id>.png` or `m5_frames/<id>.png` exists (never `_raw`).
  `frame_not_archived` = no PNG kept (all runs before 2026-09-25 06:35). That label
  does not mean no image was sent.

### What each hypothesis predicts in the 2x2

Cells are crossed by which robot is correct and which robot is listed first. The
entry is P(model names `robot_1`).

| Hypothesis | correct r1, first r1 | correct r1, first r2 | correct r2, first r1 | correct r2, first r2 |
|---|---|---|---|---|
| ID prior only (always `robot_1`) | 1 | 1 | 1 | 1 |
| Slot prior only (always first-listed) | 1 | 0 | 1 | 0 |
| Scene use only (always correct) | 1 | 1 | 0 | 0 |

The **decisive cell is "correct r2, first r1"**: both positional priors point at
`robot_1` and only the scene points at `robot_2`. A low P(`robot_1`) there is the only
pattern that cannot come from either bias.

---

## Results

### Outcome census (all 859 live analyses)

| Variant | Model | Runs | Analyses | No decision | Parse invalid or failed | Negative | Congestion, no yielder (strategies) | Positive |
|---|---|---|---|---|---|---|---|---|
| `w0p2_eopen` | gpt-4o | 15 | 170 | 60 | 75 | 81 | 12 (reverse 5, wait 4, reroute 3) | 17 |
| `w0p2_eopen` | ER-2 | 11 | 136 | 0 | 0 | 115 | 10 (reverse 10) | 11 |
| `wopen_e0p2` | gpt-4o | 9 | 105 | 9 | 25 | 86 | 1 (reroute 1) | 9 |
| `wopen_e0p2` | ER-2 | 7 | 92 | 0 | 0 | 76 | 9 (reverse 8, reroute 1) | 7 |
| `w0p2_eopen_bshort` | gpt-4o | 9 | 49 | 0 | 5 | 34 | 5 (wait 4, reroute 1) | 10 |
| `w0p2_eopen_bshort` | ER-2 | 16 | 104 | 0 | 0 | 79 | 9 (reverse 9) | 16 |
| `wopen_e0p2_bshort` | gpt-4o | 3 | 11 | 0 | 3 | 8 | 0 | 3 |
| `wopen_e0p2_bshort` | ER-2 | 3 | 21 | 0 | 0 | 14 | 4 (reverse 3, reroute 1) | 3 |
| `w0p2_eopen_gshort` | ER-2 | 3 | 55 | 0 | 0 | 44 | 7 (reverse 4, reroute 2, priority 1) | 4 |
| `wopen_e0p2_gshort` | ER-2 | 3 | 28 | 0 | 0 | 21 | 4 (reverse 3, reroute 1) | 3 |
| `w0p2_eopen_bshort` | 8 other models, 1-2 runs each | 14 | 88 | 21 | 26 | 40 | 13 (qwen3-vl wait 13) | 14 |

The "other models" row covers Claude Sonnet 5.5, deepseek-flash, gemini-3.8-flash,
glm-5.3-flash, gpt-5.1, gpt-5.6-sol, molmo2-er and qwen3-vl-8b.

- gpt-4o's no-decision rows are refusals and one outage. `20260925_181526` (F1) alone
  contributes 46 artifacts with no decision: the account had no credit, and every
  call failed at transport.
- Claude Sonnet 5.5 had 21 analyses with no decision.
- Some positives were decided on a re-ask: 5 gpt-4o positives (attempts 2-3) and
  2 Sonnet positives. Two positives used the neutral fallback image.
- No negative, non-yield or no-decision analysis is dropped silently. Each appears
  in the table above and in `live_analyses.jsonl`.

### Headline: run level, by blocker side

West means `w0p2_*` (correct `robot_2`; the manifest FCFS label agrees). East means
`wopen_e0p2_*` (correct `robot_1`; the manifest label disagrees). Each run's first
positive analysis is counted.

| Model | Side | Runs | VLM correct | VLM names `robot_1` | Rule correct, recorded shadow | Rule correct, recomputed (unvalidated) | Manifest-FCFS correct | Always-`robot_1` correct | M3-grounded correct |
|---|---|---|---|---|---|---|---|---|---|
| gpt-4o | west | 23 | 5/23 (0.22) | 18/23 | 5/6 | 10/17 | 23/23 | 0/23 | 18/22 (0.82), 1 none |
| gpt-4o | east | 12 | 10/12 (0.83) | 10/12 | no data | 5/12 | 0/12 | 12/12 | 12/12 |
| ER-2 | west | 30 | 12/30 (0.40) | 18/30 | 2/6, 3 none | 10/20, 1 none | 30/30 | 0/30 | 29/30 (0.97) |
| ER-2 | east | 13 | 11/13 (0.85) | 11/13 | no data | 6/12, 1 none | 0/13 | 13/13 | 13/13 |
| 8 other models | west | 14 | 11/14 (0.79) | 3/14 | 5/14 | - | 14/14 | 0/14 | 14/14 |
| 8 other models | east | 0 | - | - | - | - | - | - | - |

A recorded shadow exists only on `w0p2_eopen_bshort` runs (29 of the 92 units).
Every east-variant, base-west and `gshort` rule number is a recomputation. The M3
column is derived for all 92 units: 54 as named, 37 swapped and 1 refused.

Reading the table:

- **Where the manifest rule is right (west), gpt-4o and ER-2 are worse than it:**
  5/23 and 12/30 against 23/23 and 30/30.
- **Where it is wrong (east), the VLMs win (10/12, 11/13 against 0/12, 0/13).** But
  "always `robot_1`" also wins there, at 12/12 and 13/13. In every gpt-4o and ER-2
  row, the VLM's score sits between the always-`robot_1` baseline and chance, never
  above the better baseline.
- **The recorded live rule is not the manifest rule, but this is shown only on
  `w0p2_eopen_bshort`.** That variant is the only one with a recorded shadow.
  - All variants have `arrival_offset_m = 0`, so both robots reach the conflict zone
    in the same tie window, and FCFS falls to the commitment tiebreak, which depends
    on sub-second path differences.
  - On the 30 positive real-model artifacts with a recorded shadow, it named
    `robot_2` 12 times, `robot_1` 14 times and no yielder 4 times.
  - At each bundle's first `head_on` shadow, over 39 bundles (28 real-model, 11 mock;
    the rule does not read the backend), it named `robot_2` in 21 and `robot_1` in 18.
  - So "the rule is about a coin flip" rests on about 39 west `bshort` runs.
- **The recomputed rule is not a usable substitute.** On real-model artifacts that
  carry a recorded shadow, the scene-log recomputation agrees with it on 27 of 50
  where either names a yielder, and on 19 of 30 positives. That is close to what
  two unrelated near-50/50 answers would give. The recorded ring buffer samples
  every 0.25 s; the scene log is sparser. **The rule's live behaviour on east
  variants therefore has no recorded evidence.** "The rule is wrong on east" is
  verified only for the manifest label.
- **M3 decides correctness in the deployed system.** With the `swap` gate on, the
  grounded yielder was correct in 79/79 runs, and 37 of those 79 were M2 picks the
  gate overturned. The misses in the M3 column all come from runs with the gate
  `off`, from before the gate existed, or `refuse`d.

### Per variant and model

`live_tables.txt` holds the per-variant tables at analysis level and run level. The
rule column below mixes sources and should be read with the fidelity caveat above;
"recomputed" means unvalidated. The run-level rows for the two main models:

| Variant | Model | Runs | VLM correct | Rule correct [source] | M3 correct |
|---|---|---|---|---|---|
| `w0p2_eopen` | gpt-4o | 14 | 2/14 | 8/14 [recomputed] | 9/13, 1 none |
| `w0p2_eopen` | ER-2 | 11 | 6/11 | 6/11 [recomputed] | 10/11 |
| `wopen_e0p2` | gpt-4o | 9 | 8/9 | 4/9 [recomputed] | 9/9 |
| `wopen_e0p2` | ER-2 | 7 | 6/7 | 4/6, 1 none [recomputed] | 7/7 |
| `w0p2_eopen_bshort` | gpt-4o | 9 | 3/9 | 7/9 [6 shadow, 3 recomputed] | 9/9 |
| `w0p2_eopen_bshort` | ER-2 | 16 | 6/16 | 4/12, 4 none [9 shadow, 7 recomputed] | 16/16 |
| `wopen_e0p2_bshort` | gpt-4o | 3 | 2/3 | 1/3 [recomputed] | 3/3 |
| `wopen_e0p2_bshort` | ER-2 | 3 | 2/3 | 2/3 [recomputed] | 3/3 |
| `w0p2_eopen_gshort` | ER-2 | 3 | 0/3 | 2/3 [recomputed] | 3/3 |
| `wopen_e0p2_gshort` | ER-2 | 3 | 3/3 | 0/3 [recomputed] | 3/3 |

`w0p2_eopen` gpt-4o counts 15 runs in the census but 14 here, because F1 produced no
positive.

At analysis level (all positives, not independent), VLM correct is: gpt-4o west
6/27 and east 10/12; ER-2 west 12/31 and east 11/13. The direction matches the run
level.

### Stratification by order and image

`live_tables.txt` has the full order x image x obstacle-text table. The points that
matter:

- **gpt-4o, live, by first-listed robot.**
  - First-listed `robot_1`: names `robot_1` in 17 of 20 runs. The three exceptions
    are `20260925_005754`, `calibration/20260928_112237`, and `_115147`, which was
    decided on the neutral fallback image after two refusals.
  - First-listed `robot_2`: names `robot_1` in 11 of 15 runs.
- **Image strata.** Run-level units: `real_frame` 73, `frame_not_archived` 17,
  `fallback_neutral` 2. Restricting to real frames does not change the pattern
  (2x2 below). Run level, by first-listed robot and image (VLM correct / names
  `robot_1`):

| Model | Side | First listed | Real frame | Frame not archived | Fallback image |
|---|---|---|---|---|---|
| gpt-4o | west | `robot_1` | 1/7 correct, 6/7 `robot_1` | 1/5, 4/5 | 1/1, 0/1 |
| gpt-4o | west | `robot_2` | 1/7, 6/7 | 1/3, 2/3 | - |
| gpt-4o | east | `robot_1` | 7/7, 7/7 | - | - |
| gpt-4o | east | `robot_2` | 0/2, 0/2 | 3/3, 3/3 | - |
| ER-2 | west | `robot_1` | 6/13, 7/13 | 2/4, 2/4 | - |
| ER-2 | west | `robot_2` | 3/12, 9/12 | 1/1, 0/1 | - |
| ER-2 | east | `robot_1` | 8/8, 8/8 | - | - |
| ER-2 | east | `robot_2` | 2/4, 2/4 | 1/1, 1/1 | - |
- **Obstacle text off.** `20260925_043512` and `_045004` (gpt-4o, west) carry no
  obstacle text. Both named `robot_1`.

### The confound 2x2

Entries are P(model names `robot_1`) as k/n, with the number of distinct scenes in
brackets for replays. Live cells are at run level unless marked.

| Stratum | correct r1, first r1 | correct r1, first r2 | **correct r2, first r1** | correct r2, first r2 |
|---|---|---|---|---|
| Live gpt-4o, runs | 7/7 | 3/5 | **10/13** | 8/10 |
| Live gpt-4o, analyses, attempt 1 only | 7/7 | 2/4 | **11/14** | 7/9 |
| Live gpt-4o, runs, goal-bearing prompt era | EMPTY | EMPTY | **2/4** | 1/2 |
| Live ER-2, runs | 8/8 | 3/5 | **9/17** | 9/13 |
| Live ER-2, runs, goal-bearing prompt era | EMPTY | EMPTY | **0/3** | 3/4 |
| Live 8 other models, runs (pooled only for this line) | EMPTY | EMPTY | **1/3** | 2/11 |
| Replay batch 1, gpt-4o, real frame + text, attempt 1 | 44/45 [3] | 31/35 [3] | **43/43 [3]** | 2/34 [3] |
| Replay batch 2 pre-rewrite, same cell definition | 5/5 [1] | 4/6 [1] | **14/14 [3]** | 11/17 [3] |
| Replay batch 2 post-rewrite, same | 21/21 [3] | 5/7 [2] | **EMPTY** | 4/6 [2] |
| Replay batch 1, grey image + text, attempt 1 | 17/18 [3] | 16/18 [3] | **18/18 [3]** | 9/18 [3] |
| Replay batch 1, real frame, text off, attempt 1 | 9/9 [2] | 10/13 [3] | **12/12 [2]** | 9/14 [3] |
| Synthetic probe gpt-4o, T = 0.0 | 10/10 | 2/10 | **10/10** | 3/10 |
| Synthetic probe gpt-4o, T = 0.6 | 19/19 | 11/20 | **17/20** | 8/20 |
| Synthetic probe gpt-4o-mini, T = 0.0 | 10/10 | 0/10 | **10/10** | 0/10 |
| Synthetic probe ER-2 (seeded) | 4/4 | 1/3 | **2/2** | 3/4 |
| Refusal probe gpt-4o, synthetic or grey image | EMPTY | EMPTY | **24/24 [1]** | 0/1 [1] |

The 8 other models are pooled on that line only to show which cells exist. Per
model, each has 1-2 runs, all on `w0p2_eopen_bshort`. The full per-model table is in
`live_tables.txt`.

What the table says:

- **The decisive cell.** Wherever gpt-4o is measured, P(`robot_1`) in "correct r2,
  first r1" is near 1.
  - Replays: 43/43 in batch 1 and 14/14 in batch 2 pre-rewrite.
  - Live: 10/13 runs. The three exceptions are an early run and two calibration
    runs, one of them on the fallback image.
  - Synthetic probe: 10/10 and 17/20.

  Nowhere does gpt-4o name `robot_2` when both priors point at `robot_1`, except in
  those three live runs. **The data contain no evidence that gpt-4o uses the scene
  when doing so would mean overriding both priors.**
- **Batch 1 is the only place gpt-4o tracks the scene, and only where the two priors
  disagree.** It names the correct robot in 31/35 ("correct r1, first r2", against
  the slot) and 32/34 ("correct r2, first r2", against the ID). That fits a choice of
  `robot_1` whenever ID and slot agree, with the scene breaking the tie only when
  they conflict.
- **Batch 2 does not replicate batch 1's last cell:** 11/17 `robot_1`, and per scene
  0/5, 5/6 and 6/6. The tie-break effect depends on the scene.
- **The live runs cannot settle that cell.** Live gpt-4o names `robot_1` in 8 of 10
  runs there, but that count is not like-for-like:
  - two of the 8 are re-ask decisions (`063520`, `155433`);
  - one has no obstacle text (`045004`);
  - two are the batch-2 replayed scenes themselves (`160951`, `162451`).

  On the attempt-1, text-on, non-replayed runs it is 3 of 5 `robot_1`.
- **ER-2 is not slot-anchored. It carries a weaker `robot_1` preference.**
  - On east variants it names `robot_1` in 11/13 runs; on west variants it names
    `robot_2` in only 12/30.
  - The decisive cell is 9/17 `robot_1`, so 8/17 correct. The cell where the slot
    favours the correct robot is worse, at 4/13 correct.
  - This is no slot effect, plus some side sensitivity: P(`robot_1`) is 0.60 west
    against 0.85 east. Its west accuracy, 12/30, is still below one half.
  - There is no counterbalanced ER-2 replay on real frames.
- **The 8 newer models were run only on the west `bshort` variant.** Their good
  west score (11/14) cannot be told apart from a `robot_2` preference, because no
  east run exists. Two things in their data stand out:
  - Their prompts carry goals. On `bshort` scenes the robot with the shorter goal
    (|x| = 1.5) is always the correct yielder: `robot_2` in `w0p2_eopen_bshort`,
    `robot_1` in `wopen_e0p2_bshort`. That gives a non-obstacle cue aligned with the
    oracle.
  - Over the full `justification`, `reasoning` and `root_cause` text of the 28
    goal-era positives, one decision ties the yielder to the fixed obstacle:
    gpt-5.6-sol `gs01` ("robot_1's western retreat is constrained by the fixed
    obstacle"). Its second run, `gs02`, does not mention it. Three decisions cite
    clear space behind `robot_2` (gemini-3.8-flash `ha01`, ER-2 `vp02` and `vp03`).
    gpt-5.1 `mw03` names the obstacle on the wrong side, qwen3-vl `mw02` says the
    robots are "not near any fixed obstacles", and 12 decisions mention goals.

### Empty cells

| Model or stratum | Empty cells | Consequence |
|---|---|---|
| 8 newer models (Sonnet 5.5, gpt-5.6-sol, gemini-3.8-flash, gpt-5.1, glm, molmo2-er, qwen3-vl, deepseek-flash) | both "correct r1" cells, for every model; and, per model, every cell outside the 1-2 runs they have | No live or replay data on an east variant. Their west accuracy cannot be separated from a `robot_2` or goal-cue preference. |
| gpt-4o and ER-2, goal-bearing prompt era | both "correct r1" cells | No east run in the goal-bearing prompt era. |
| ER-2 on real frames, counterbalanced replay | all four | Never run. Only live draws and the synthetic probe exist. |
| gpt-4o replay batch 2 post-rewrite | correct r2, first r1 | No west `id_asc` cell in the 101-call remainder. |
| Refusal probe | both "correct r1" cells | All 240 calls replay west-variant artifacts. |
| `wopen_eopen_o0` (both feasible) | all, live | Never run live; only the synthetic probe. |
| Classical rule, recorded shadow | every east-variant, base-west and `gshort` run | The shadow was recorded only on `w0p2_eopen_bshort`. Rule numbers elsewhere are unvalidated recomputations. |

The question cannot be answered from existing data for any model other than gpt-4o,
and partly for ER-2.

---

## Reconciliation With the September Findings

The note being checked reads: "gpt-4o choice = first-slot prior + robot_1 prior +
feasibility evidence; obstacle TEXT is used but only visible under id_desc (0.96
feasible vs chance); under id_asc robot_1 always". Its sources are
`docs/reports/2026-09-25-frame-replay.md` Rev 3, Arm S, and the overnight report
`docs/reports/2026-09-25-overnight-findings.md` §L and §T. Every number below was
recounted from the `calls.jsonl` files or the live artifacts.

| Claim | September figure | Recount here | Verdict |
|---|---|---|---|
| P(feasible) 0.96 under `id_desc`, real frame, text on | 25/26 (Rev 3, batch 1) | 25/26, 5 scenes (one east scene refused on every attempt 1) | Number holds, but **batch 1 only** |
| Same cell, batch 2 | 10/23 (Rev 4) | 10/23, 4 scenes | Holds. It is **below** batch 2's own side-blind baseline. |
| Same cell, batches 1 + 2 pooled | 35/49 (Rev 4) | 35/49 | Holds |
| Same cell, post-rewrite remainder | 5/7 (Rev 5) | 5/7, 2 scenes | Holds |
| Removing obstacle text drops batch 1 to | 15/27 | 15/27 | Holds |
| Arm O, P(`robot_1`) | 47/48 `id_asc`, 22/47 `id_desc` | 47/48, 22/47 | Holds |
| "Under `id_asc`, `robot_1` always" | 124/125 (Rev 3), 83/83 (Rev 4) | replay attempt 1, real frame + text: 87/88 (b1), 19/19 (b2 pre), 21/21 (b2 post). Live gpt-4o runs with first-listed `robot_1`: 17/20. | Holds in replay. Live, it is 17 of 20. |
| "First-slot prior" | synthetic probe, P(`robot_1` \| `id_desc`) 0.25 | Synthetic gpt-4o: 2/10 and 3/10 at T = 0 under first-listed `robot_2`. Real-frame replay, east scenes under `id_desc`: 31/35 `robot_1`. Live, first-listed `robot_2`: 11/15 `robot_1`. | **Visible only on the synthetic stimulus.** On real frames, gpt-4o does not follow the slot away from `robot_1`. |
| Overnight §L.3 refinement: real-frame replays "reproduce the live pattern" | qualitative | Joined by `request_id`, the live decision equals the replay's attempt-1 majority at the stored order on 9 of the 12 replayed scenes. Two of the three mismatches are the west `id_desc` scenes that matter: `53264de9` (replay 2/11 `robot_1`, live `robot_1`) and `810c9104` (0/5, live `robot_1`). Both live decisions are **re-ask** outputs (attempts = 2). The third mismatch, `3120c65f`, is a live minority draw (replay 14/17 `robot_1`, live `robot_2`). | **Holds where the comparison is like-for-like. Untestable on the two scenes that carry the `id_desc` competence claim**, because live answered them from a re-ask prompt. |
| Overnight §L.2: live gpt-4o `robot_1` 9/11, 5/6 under `id_desc` | 9/11, 5/6 | On disk, base variants, run level: 20/23 `robot_1`; 9/11 among runs whose prompt lists `robot_2` first | Direction holds, with more runs |

Agreement and disagreement in one place:

- **Agreement.** The `robot_1` (ID) prior is the dominant term for gpt-4o. In
  batch 1, the obstacle text moves the choice only when ID and slot conflict.
  Live gpt-4o runs whose prompt lists `robot_2` first, west, base variant: 6 of 7
  named `robot_1`; the exception is R1 (`20260924_195708`).
- **Disagreement, number vs number.**
  - The note's "0.96" is a batch-1 figure, 25/26. The same analysis gives 10/23 in
    batch 2 and 35/49 pooled. The September document already says this in its own
    Rev 4; the note predates that revision.
  - The note's "first-slot prior" is 2/10 `robot_1` under first-listed `robot_2` on
    the synthetic stimulus. It is 31/35 `robot_1` on real-frame east scenes and 11/15
    in live runs. Outside the synthetic probe, no slot prior separate from the ID
    prior is measurable.
  - "Under `id_asc`, `robot_1` always" is 127/128 in replay but 17/20 live.

---

## Conclusion

**Existing data do not show that the VLM helps choose the yielder on this family.**

- For gpt-4o and ER-2, the VLM beats a position-only rule only on east variants.
  There, always naming `robot_1` does at least as well: 12/12 and 13/13 against the
  VLM's 10/12 and 11/13.
- On west variants both models do worse than the manifest rule: 5/23 and 12/30
  against 23/23 and 30/30.
- The one cell that could show scene use beyond the two biases is "correct `robot_2`,
  `robot_1` listed first". There gpt-4o names `robot_1` in every replay (57/57,
  attempt 1) and in 10 of 13 live runs. ER-2 is near chance there (8/17 correct).

The "advantage" in the cells where the rule is wrong is the `robot_1` bias meeting a
scenario family in which `robot_1` is the correct answer whenever the blocker is east.

The comparison with a "position-only rule" also needs care:

- The manifest's `fcfs_yielder` is a design label.
- The classical FCFS rule as recorded live names the two robots about equally
  often (21 `robot_2` / 18 `robot_1` at first detection, west `bshort` only). That
  is expected on arrival-symmetric scenes, where FCFS falls to a timing tiebreak.
- Neither the VLM nor the rule supplies the right yielder on this family. **M3's
  feasibility gate does:** it was correct in 79/79 runs where it was on, overturning
  37 wrong M2 picks.

What the data can support:

- gpt-4o's yielder choice on these scenes is explained by a `robot_1` preference.
  In batch 1, the obstacle text breaks ties between that preference and the slot,
  but this does not replicate in batch 2 or in the live runs.
- ER-2 has a weaker `robot_1` preference and no slot preference.

What the data cannot support:

- Any claim, either way, about scene use by the 8 newer models. Their two cells
  with `robot_1` correct are empty, and their goal-bearing prompts carry an
  oracle-aligned goal cue on `bshort` scenes.
- Any claim about the classical rule's live answer on east variants. There is no
  recorded shadow there, and the recomputation does not reproduce the recorded
  shadow where both exist.
- Any claim about ER-2 on counterbalanced real frames.
- Any statement about `wopen_eopen`.

---

## Minimal Offline Replay to Fill the Empty Cells

No new data were collected for this report. What would close the gaps at the lowest
cost:

1. **Stimuli.** The 12 genuine-standoff artifacts already reconstructable with a
   SHA-verified prompt: batch 1 `53264de9`, `5e7b5a59`, `2c3fbfa5` (west) and
   `61119197`, `d053d0dc`, `3120c65f` (east); batch 2 `810c9104`, `42fb0cb8`,
   `d4b96fbd` (west) and `189ae2a6`, `e4b1bd03`, `618a9f29` (east).
   - These are base `o0` variants, so their goals are symmetric (+-2.5 m) and carry
     no goal-distance cue.
   - Render the prompt version each model ran live; for v2/v3 prompts, take goals
     from the scenario yaml.
2. **Arm A, order (fills the "correct r1" cells).** Both orders, real frame, obstacle
   text on, attempt 1 only, 2 replicates: 12 x 2 x 2 = 48 calls per model. Models:
   ER-2, gemini-3.8-flash, gpt-5.6-sol and Claude Sonnet 5.5, so 192 calls. The four
   remaining models can run at 1 replicate (24 calls each).
3. **Arm B, ID relabel (breaks "`robot_1` = west spawn").** Same 12 scenes, robot
   IDs swapped in the text, both orders, 2 replicates: 48 calls per model.
   - Use the raw frame for batch 2 and a grey image for batch 1, because the drawn
     ID labels would contradict the relabel.
   - Run it for the same four models plus gpt-4o: 240 calls.
   - Only this arm can tell an ID prior from a side preference.
4. **Volume and cost.** About 430 calls (about 530 with the four remaining models at
   1 replicate). Recorded per-call costs are about $0.0056 for gpt-4o (frame replay
   Rev 2: $3.97 / 708) and $0.004 for ER-2 (presentation-order Rev 2:
   $0.73 / 180). At an assumed upper bound of $0.02 per call for the other models,
   the total stays under about $8. The Gemini monthly cap and the OpenAI balance
   need checking first.
5. **Analysis.** The 2x2 per model, plus the relabel contrast. Report per scene,
   with the scene as the unit (6 per side).

---

## Limitations

- **Pilot data, post hoc.** Seeds are mostly 42, with 1-3 runs per cell for most
  models. No conclusion here was pre-registered.
- **The live 2x2 mixes apparatus states.** It pools:
  - gate `off`, `swap` and pre-gate runs;
  - obstacle text on and off (2 runs off);
  - re-asked and first-attempt decisions;
  - failure-context prompts. Most ER-2 first positives follow a `reverse`, and their
    prompts carry the previous attempt.
  - pre-goal and goal-bearing prompt versions.

  The strata that `live_tables.txt` reports separately do not change the
  decisive-cell reading.
- **Rule recomputation does not reproduce the recorded shadow:** 27/50 where either
  names a yielder, 19/30 on positives. Every `recomputed_scene_log` number is
  unvalidated. The coin-flip reading rests on the recorded shadow alone, which
  exists only for west `bshort` runs.
- **The M3 column is derived, not observed.** `dispatched_command` is absent from
  every positive artifact, and M4 execution logs were not joined.
- **The replays are gpt-4o only** and rest on 12 scenes (3 per side per batch). The
  replicate counts in the replay table are not independent; the scene is the unit.
- **The oracle optimises `min_total_time_to_goal`.** Here the correct yielder is also
  the only feasible one, but none of the prompts asks the model to check feasibility.

---

## Reproducibility

Scripts and outputs are under
`data/logs/vm_runs/head_on_vlm_vs_rule_analysis/` in the v7e worktree (gitignored).

| File | Contents |
|---|---|
| `extract_live.py` | scans the five `vm_runs` trees and writes `live_analyses.jsonl` (all 1,002 rows, mock included and flagged) and `live_bundles.json` (inclusion and exclusion per bundle) |
| `analyze_live.py` | writes `live_tables.txt` and `per_analysis_table.jsonl` |
| `per_analysis_table.jsonl` | one row per positive live analysis: bundle path, `request_id`, variant, model, order, first-listed robot, image condition, VLM yielder, rule yielder and source, M3-grounded yielder and source, oracle yielder |
| `analyze_replays.py` | writes `replay_tables.txt` and `replay_calls_scored.jsonl` |

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7e
PY=/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/.venv/bin/python
$PY data/logs/vm_runs/head_on_vlm_vs_rule_analysis/extract_live.py
$PY data/logs/vm_runs/head_on_vlm_vs_rule_analysis/analyze_live.py
$PY data/logs/vm_runs/head_on_vlm_vs_rule_analysis/analyze_replays.py
```

The scripts import only `reasoning.baselines.classical_reasoner` and
`reasoning.vlm.models`. They build no backend and read no `.env`.

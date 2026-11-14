# Improved-Annotation Replay - Pre-Registered Design

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: design frozen before the first paid call. Implements the recommended design of `docs/reports/2026-11-14-improved-annotation-test-scope.md` (Rev 2), with the owner's choices (prompt-line factor run alongside) and the differences listed under "Differences From the Scope".

---

## Question

On the head-on standoff scenes, with **no obstacle text** in the prompt, does a model
name the physically correct yielder from the camera frame once the frame is easier to
read (Type L), and does a neutral task-knowledge sentence in the prompt change that?

**Evidence grade:** a small designed offline experiment. Twenty-four scenes from one
scenario family at seed 42 (two visual layouts: blocked west, blocked east), two
robots, first decision only, no execution. Counts only: no p-values, no confidence
intervals. These rows are a new stratum, never pooled with earlier replays or live
runs.

**Authorisation:** owner instruction 2026-11-14, "run it, with the prompt line
alongside". Paid model API calls for this experiment only. Hard cap **$12.00 total and
$6.00 per model**. No VM, no cloud/ssh/gcloud, no push.

---

## Stimuli

The 24 scenes of the scope: the first SHA-verified genuine standoff of each run
(`select_standoff_artifacts`, failure-context artifacts excluded). `load_scenes` in
`scripts/render_annotation_variants.py` re-derives them and **asserts**, before any
call: the exact 24 request prefixes below; prompt v1; no failure context, last-failed
context or plan state; `robot_1` west of `robot_2` in every scene snapshot (the
scoring depends on it); 12 scenes per side; every annotated frame present.

- "Original" = the 12 stimuli of the swapped-ID replay (2026-09-25 pilot runs).
  "Extra" = the 12 ER-2 live runs of the same two scenario cells (2026-09-25).
  `20260925_181526` stays excluded (its live decision failed to parse), as in the
  scope.
- The correct yielder is the robot away from the blocker: the **east** robot
  (`robot_2`) when the blocker is west, the **west** robot (`robot_1`) when it is east.
- Every scene snapshot has both robots `STOPPED`. Some robots carry a small speed
  (up to 0.0088 m/s), so M1 drew a velocity arrow in some frames. The arrows are in the
  stored frames and are not touched by any variant.

The scene list with run, side, raw-frame availability and image md5s is in the
appendix.

---

## Factors and Cells

All cells: obstacle text **off** (`include_static_obstacles=False`), original robot
IDs, prompt v1, both listing orders (`id_asc`, `id_desc`), all 24 scenes, the shipped
reasoner and backend configs of `config/models.yaml`, unchanged.

### Image factor (4 levels)

| Level | Image | Type | Size sent |
|---|---|---|---|
| `C_ref` | the annotated frame M2 received live, unchanged | reference | 1280 x 960 |
| `D_ref` | neutral mid-grey (RGB 128), one file for all scenes | states-only control | 1280 x 960 |
| `L2` | the annotated frame with the 1-px labels inpainted away and redrawn as large white-on-black panels pushed apart, 3-px boxes, then a fixed crop u 0-1280, v 280-680 and a Lanczos 1.6x upscale | **L** (no fact added) | 2048 x 640 |
| `K1` | L2 plus a cyan outline of the declared obstacle's ground footprint (M5 `static_obstacles`) and the text `obstacle_1`, then the same crop | **K** (knowledge injection) | 2048 x 640 |

- The renderer is `scripts/render_annotation_variants.py`, promoted from the scope
  prototype with the same geometry and drawing constants. One fix was made before any
  call (see "Differences From the Scope").
- **K1 placement.** The system holds no obstacle height (`StaticObstacleInput` has
  none), so K1 outlines the ground footprint. In the image this lands on the box's
  shaded side face and base, on the corridor-centre side of the bright top face, not
  on the top face. This is kept as is: it is all the system could draw.
- K1 adds the outline **and** the label `obstacle_1`, as the scope specified. The
  tests check that K1 differs from L2 only inside the outline and label boxes.
- K1 results are reported only as **"annotation reading"**, never as image use.

### Prompt-line factor (2 levels)

- **Sentence (the scope's exact wording):** `A robot that backs up needs free floor behind it.`
- **Placement (fixed here; the scope left it open):** appended, after one space, to the
  end of the head-on Guidance bullet, immediately after
  `strategy="reverse" (both back up to clear).` That bullet is where the prompt
  defines both back-up strategies. Nothing else in the prompt changes.
- The sentence names no obstacle, side, image or specific robot, and states no scene
  fact.
- Mechanism: `Reasoner.run` builds its own payloads, so the runner inserts the line
  into the payload the backend receives (`PromptLineProxy`), on **every** attempt,
  including re-asks and gpt-4o's grey-image fallback. The recorded prompt hash is the
  hash of what was sent. `prompt_v1.py` is not modified.
- `+P` denotes a cell with the line.

### Cells, priority and budget cut

Priority order as instructed: `L2`, `D_ref`, `L2+P`, `D_ref+P`, `C_ref`, `K1`,
`C_ref+P`, `K1+P`.

| Cell | Image | Line | Grey control | Planned |
|---|---|---|---|---|
| `L2` | L2 | no | `D_ref` | yes |
| `D_ref` | grey | no | - | yes |
| `L2+P` | L2 | yes | `D_ref+P` | yes |
| `D_ref+P` | grey | yes | - | yes |
| `C_ref` | annotated | no | `D_ref` | yes |
| `K1` | K1 | no | `D_ref` | yes |
| `C_ref+P` | annotated | yes | `D_ref+P` | yes |
| `K1+P` | K1 | yes | `D_ref+P` | **cut before any call** |

Replicates per scene x order: **gpt-4o 2, ER-2 4**. Runs per cell: gpt-4o 96, ER-2 192.

---

## Models

| `backend_id` | Model | Effective reasoner config (as shipped) |
|---|---|---|
| `gemini` | `gemini-robotics-er-2-preview` | shared block: max_attempts 2, re-ask on, no image fallback, max_tokens 2048, thinking_level low; temperature/top_p/top_k not sent (Interactions API) |
| `openai` | `gpt-4o-2024-08-06` | temperature 0.0, max_attempts 4, grey fallback after 2, max_tokens 2048 |

The effective config, the served model string of every attempt, the commit, UTC
start/end timestamps, the shuffled sequence index, the block and the seed are recorded
on every row.

---

## Calls, Cost and Budget

### Planned cost (rates and per-run costs from the swapped-ID replay ledger)

Rates (per MTok, input / output): gpt-4o $2.50 / $10.00; ER-2 $1.00 / $5.00, thought
tokens charged as output. Measured mean per run in that ledger: ER-2 $0.0040 in
both the frame and grey cells; gpt-4o $0.0065 (frame, text off), $0.0061 (grey, text
off). For gpt-4o, the 2048 x 640 image costs 8 tiles instead of 4 (scope), about
$0.0085 per run [inferred]. ER-2 billed the same image tokens for every image size
seen so far, so its variant cost is taken as $0.0040 [inferred]. The line adds about
12 tokens (negligible).

| Cell | gpt-4o runs | gpt-4o $ | ER-2 runs | ER-2 $ |
|---|---|---|---|---|
| `L2` | 96 | 0.82 | 192 | 0.77 |
| `D_ref` | 96 | 0.59 | 192 | 0.77 |
| `L2+P` | 96 | 0.82 | 192 | 0.77 |
| `D_ref+P` | 96 | 0.59 | 192 | 0.77 |
| `C_ref` | 96 | 0.62 | 192 | 0.77 |
| `K1` | 96 | 0.82 | 192 | 0.77 |
| `C_ref+P` | 96 | 0.62 | 192 | 0.77 |
| **Planned (7 cells)** | **672** | **4.87** | **1,344** | **5.38** |
| `K1+P` (cut) | 96 | 0.82 | 192 | 0.77 |
| Full set (8 cells) | 768 | 5.68 | 1,536 | **6.14** |

- **Why `K1+P` is cut.** The full set costs about $6.14 for ER-2, above its $6.00 cap.
  The per-run pre-check also reserves one worst-case run (ER-2: 2 x (3,000 x $1 +
  2,048 x $5) / 1M = $0.026; gpt-4o: 4 x (3,000 x $2.50 + 2,048 x $10) / 1M = $0.11),
  so gpt-4o's full set ($5.68 against an effective $5.89) leaves too little margin for
  an inferred per-run cost. `K1+P` is the lowest priority, so it is cut for both
  models, which keeps the two models' cell sets identical.
- **Planned total:** about $10.25 plus two probes (about $0.002), against $12.00.
- **API calls:** about 720 for gpt-4o (about 1.07 attempts per run with real-frame
  refusals) and about 1,350 for ER-2.
- **Wall time:** the two providers run in parallel, one process each. ER-2 about
  1,344 x (7.1 s + 1 s pace), about 3.0 h; gpt-4o about 672 x (3.4 s + 1 s), about
  50 min.

### Budget rules

- **Per-run pre-check (as before):** before every run, the worst case of that run is
  computed (`max_attempts x (max(3,000, 1.2 x the largest prompt seen) x input rate +
  max_tokens x output rate)`). The run is skipped and the model stops cleanly if model
  spend + worst case exceeds $6.00, or total spend (both models' ledgers plus probes) +
  worst case exceeds $12.00.
- **Post-pilot projection (new, stated now):** after a model's pilot, the runner
  projects: spend so far + 1.10 x the sum, over each remaining cell, of (that cell's
  mean pilot cost per run x its remaining runs). If the projection exceeds $6.00 minus
  one worst-case run, cells are cut from the **bottom of the priority list** until it
  fits. The decision and every projection step are written to `budget_<model>.json`
  before the main phase. A cell cut here keeps only its 4 pilot rows and is reported
  as "cut for budget, not assessable".
- **If the cap still binds mid-run:** blocks run replicate by replicate, so a stop
  loses the tail of the current replicate block across cells. Any cell with fewer
  runs than planned is **not assessable** under rules 1-3. Its counts are still
  reported.

---

## Execution Order

1. **Probe** one minimal paid call per provider (ER-2 for Gemini, gpt-4o for OpenAI):
   a short text prompt with a 64 x 64 grey PNG. Logged in `probes.jsonl` and counted in
   the total.
2. Per model, one process each, in parallel:
   1. **Pilot:** for each of the 7 cells, replicate 1 of scenes `810c9104` (west) and
      `189ae2a6` (east), both orders: 28 runs, in a seeded random order.
   2. **Pilot rule** per cell (below), then the **post-pilot projection**.
   3. **Main:** replicate block 1, then 2 (then 3 and 4 for ER-2). Each block holds
      every (cell, scene, order) of that replicate not already in the pilot, in a
      seeded random order. Cells are therefore interleaved throughout the run, so
      provider drift over the 1-3 h is spread across cells, not confounded with them.
   4. Seed: `random.Random(f"20261114|<backend_id>|<block>")`, block in `pilot`,
      `rep1`, ... Each row records `seq`, `block` and `seed`.
3. **Resumable:** a row whose key (`backend_id|cell|request_id|order|r<rep>`) is in
   `calls_<model>.jsonl` is skipped.
4. **Integrity before each run:** the stimulus image's md5 must equal the manifest's,
   and the rendered prompt's md5 (base or `+P`) must equal the manifest's, or the run
   aborts. After the call, `prompt_sent_matches` records whether attempt 1's sent prompt
   is exactly the expected text.

---

## Stop Rules

- **Provider probe:** on HTTP 401, 402, 403 or 429, that provider is skipped and the
  status recorded. No retry around it, no key or account switch, no substitute model.
- **Quota or credit during the batch:** HTTP 402, or 429 with a quota, billing,
  spend-cap or credit marker, stops that provider at once. A plain 429 that persists
  past the transient budget also stops it.
- **Transient errors:** at most 2 transient failures (429, 5xx, timeout, connection)
  per run. They are counted in the ledger (`transient_retries`).
- **Pilot rule:** if 3 or more of a cell's 4 pilot runs end with no decision (terminal
  refusal, parse failure, error) or used the image fallback, that cell stops after the
  pilot for that model and is reported as such.
- **Spend:** the budget rules above.

---

## Outcomes and Scoring

- **Physical robot.** Original IDs throughout: `robot_1` = west robot, `robot_2` =
  east robot (asserted per scene).
- **Outcome per run** (final decision): `correct`, `wrong`, `no_yielder` (a valid
  decision naming no robot; strategy recorded), `refusal` (terminal), `parse_failure`,
  `error`. **Denominator: all runs.** Every non-correct outcome counts as not correct
  and is tabulated per cell. Nothing is dropped.
- **Secondary strata:** attempt-1 outcome; gpt-4o runs decided after the grey-image
  fallback, reported separately and as an exclusion check.
- **Scene level:** per scene x order, correct replicates out of r (r = 2 gpt-4o,
  r = 4 ER-2). A scene is **"mostly correct"** in a side x order cell when at least 75%
  of its r replicates there are correct (gpt-4o 2/2, ER-2 3/4).

---

## Decision Rules (fixed before any call; counts only)

Per model. Each side x order cell holds the 12 scenes of that side, so it has 12 x r
runs (gpt-4o 24, ER-2 48). A grey control is "the same-session grey cell with the same
prompt": `D_ref` for no-line cells, `D_ref+P` for `+P` cells.

1. **Image use** of a Type L or reference cell V (`L2`, `C_ref`, `L2+P`, `C_ref+P`).
   All three must hold:
   - **runs:** in each of the 4 side x order cells, at least 75% of the planned runs
     correct (gpt-4o **18/24**, ER-2 **36/48**);
   - **scenes:** in each of the 4 side x order cells, at least **8 of the 12 scenes**
     of that side mostly correct (gpt-4o 2/2, ER-2 3/4). Over the 24 scenes this means
     at least 8 of 12 per side, separately under each order;
   - **control:** P(correct | V) minus P(correct | its grey control) of at least
     **0.25**, both over all runs of the cell (gpt-4o 96, ER-2 192).

   Requiring both sides defeats a pure `robot_1` or `robot_2` preference, because the
   correct label flips with the side. Requiring both orders defeats a slot preference.
2. **Legibility effect:** `L2` passes rule 1, `C_ref` fails it, and P(`L2`) -
   P(`C_ref`) is at least **0.15**. The same rule is applied to `L2+P` against
   `C_ref+P` and reported beside it.
3. **Annotation reading (Type K):** rule 1 applied to `K1` against `D_ref`. A pass is
   reported under its own heading and **never counts as image use** for the thesis
   sentence.
4. **Prompt-line effect**, defined in advance as the changes in overall P(correct):
   `L2+P - L2`, `D_ref+P - D_ref`, and `C_ref+P - C_ref`. Each is also reported per side
   and per side x order.
   - **The `D_ref+P` check comes first in every interpretation of a `+P` result.**
     With the grey image, nothing in the prompt or the image tells the two sides
     apart except pose decimals. If the line raises correctness with the grey image,
     the line itself (with the states) is leaking the answer or shifting a bias, and
     any `L2+P` gain must be read against it.
   - **Line-alone flag (stated now):** it fires if `D_ref+P - D_ref` is at least 0.15
     overall (a leak), or if either side's P(correct) changes by at least 0.25 in
     absolute value (a bias shift, which may cancel overall).
   - **"Image use with the line"** is rule 1 for `L2+P` against `D_ref+P`, so the
     line's own effect is already subtracted by the control clause. **"Line-dependent
     image use"** is `L2+P` passing while `L2` fails. If the line-alone flag fires, the
     report states it before any `+P` result.
5. **ER-2 conditional image use** (secondary, ER-2 only; per cell V in `L2`, `C_ref`,
   `L2+P`, `C_ref+P`, and `K1` as annotation reading). Among the runs that **name a
   yielder** (outcome `correct` or `wrong`), orders pooled:
   - **assessable** only if, on **each** side: at least 12 named runs, from at least 6
     of that side's 12 scenes, with at least 4 named runs in each order; otherwise
     "not assessable";
   - named-correct share at least **0.80 on each side**;
   - and either the grey control (same prompt) is not assessable on the same criteria,
     or V's conditional accuracy (named-correct over all named runs, sides pooled)
     exceeds the control's by at least **0.25**.

   The naming rate per cell is always reported beside it. A pass supports only "when
   ER-2 commits to one yielder, the choice follows the image", not "ER-2's decision
   policy uses the image". No free-text mining of `reverse` answers, and no
   forced-choice arm.
6. **Not assessable:** a cell stopped at its pilot, cut for budget, incomplete, or
   with fewer than 20 decisions (any strategy). A rule needing such a cell, or its
   grey control, is "not assessable".

**What the counts can carry.** Replicates within a scene are dependent (gpt-4o at
temperature 0 mostly repeats itself), which is why the scene clause exists. The 24
scenes are two visual layouts with pose jitter. A pass means "the model can tell a
left-blocked from a right-blocked corridor in this rendering", nothing more general.

---

## Exclusions

None after the run. Every run is in `calls_<model>.jsonl` and in the counts. A
stimulus would be excluded only if it failed the asserted checks before the run (none
did).

---

## Analysis Code

`scripts/analyze_improved_annotation.py` is written, tested on synthetic rows
(`tests/unit/test_replay_improved_annotation.py`) and committed **with this design,
before the first call**. It prints the ledger, a census and strategy distribution per
cell (including `reverse` with no yielder), P(correct) per side x order with
scene-level counts, the named-yielder table, every verdict above, the prompt-line
effects with the `D_ref+P` check first, the gpt-4o fallback-excluded and attempt-1
tables, the scene-level table, and the same-day drift comparison. Any later change to
it is reported as a deviation.

**Same-day drift comparison.** On the original 12 scenes, `C_ref` and `D_ref` are
shown side by side with the swapped-ID replay's `C_real_notext` and `D_grey_notext`
(same text-off prompts: the 24 base-prompt SHA-256s equal that replay's recorded
`prompt_user_sha256`, checked by a test). Never pooled. That replay used 2 replicates
for both models; this one uses 4 for ER-2.

---

## Tests and Checks Done Before Any Call

`tests/unit/test_render_annotation_variants.py` and
`tests/unit/test_replay_improved_annotation.py`: offline, no network. They read the
stored frames from the main checkout's untracked `data/logs/vm_runs`. 148 tests pass
with **0 skipped**; with the earlier replay suites, 221 pass. They prove, for all 24
scenes:

- **Type L:** every pixel L2 changes before the crop lies inside the robot label/box
  zone (robot u +- 160 px, from 110 px above the robots to just below their boxes),
  and the obstacle's top-face columns are byte-identical; the sent L2 image is exactly
  the declared crop and upscale of that frame (2048 x 640).
- **L2 keeps each robot's overlay colour** as drawn in the frame.
- **K1 = L2 plus only the outline and its label:** every pixel K1 changes relative to
  L2 lies inside the outline box or the label box, and at least one changes.
- **Determinism:** two renders give identical pixels and PNG bytes; the pixel md5 and
  the file md5 equal the manifest.
- **Prompts:** no prompt (base or `+P`, both orders) contains "obstacle" or "1.85";
  every `+P` prompt equals its base prompt with exactly ` A robot that backs up needs
  free floor behind it.` inserted once; the prompt is identical across the four image
  levels; prompt md5s equal the manifest.
- **Proxy:** with a mocked backend, a `+P` run sends the line exactly once on every
  attempt, through a re-ask and a grey-image fallback; a base run never sends it.
- Run construction (counts, no duplicate keys, seeded order), the post-pilot cut from
  the bottom of the priority list, the pilot rule, scoring, and every decision rule on
  synthetic rows.

**Contact sheet inspection** (`contact_sheet.jpg`, all 24 L2 and K1 stimuli, plus
full-resolution crops of the robot region in 7 scenes):

- No label panel covers the obstacle, a barrier or a corridor end. The crop keeps both
  corridor ends, the obstacle and both robots in all 24 scenes.
- The obstacle is at the left end in the 12 west scenes and at the right end in the
  12 east scenes.
- K1's outline sits on the box's shaded side face and base, on the corridor-centre side
  of the top face, in all 24 scenes. Expected and kept (see "K1 placement").
- `61119197`: robot_1 was drawn in M1's SLOW yellow in the stored frame (the M5
  snapshot says STOPPED). The prototype left a yellow ghost of the old label and
  redrew the box red. Fixed before any call (below); after the fix the panel and box
  are yellow and no ghost remains.
- `7b0fbf9e`: the two boxes abut, as in the stored frame; the panels stay separate.
- Velocity arrows from M1 are visible in several frames. They are in `C_ref` too and
  are unchanged by L2.

---

## Differences From the Scope

1. **Prompt line run alongside** (owner's choice), replacing the scope's "phase 2 only
   if L2 fails". Cells `L2+P`, `D_ref+P` and `C_ref+P` run in the same session,
   interleaved with the rest. Placement fixed above.
2. **`K1+P` cut** for budget, as computed above. `L1` and `L2swap` are not run (scope
   defaults).
3. **Caps** are the owner's $12.00 / $6.00, not the scope's proposed $9.00 / $4.50.
4. **Renderer fix: overlay colour.** The prototype inpainted only red label pixels and
   redrew every box in STOPPED red. In `61119197` robot_1's overlay is SLOW yellow, so
   the prototype left a partial yellow label and changed the box colour, which alters
   what the frame shows. The promoted renderer reads each robot's colour from its box
   edges, inpaints label pixels of that colour, and draws the box and panel border in
   it. The other 23 scenes render pixel-identically to the prototype (L2 and K1, all
   24 compared; only `61119197` differs), and `810c9104_L2.png` is byte-identical to
   the scope's example file.
5. **Scope statement corrected:** the scope said "no arrow is drawn on these stopped
   robots". M1 draws an arrow when |linear_velocity| > 0.001 m/s; in the M5 snapshots
   that holds for at least one robot in 13 of the 24 scenes, and arrows are visible in
   several frames. This changes no variant.
6. **Pilot** scenes are the scope's (`810c9104`, `189ae2a6`); the runs within the pilot
   and within each replicate block are shuffled with a recorded seed instead of
   "interleaved scene by scene".
7. **Parallel providers** with per-model `calls_<model>.jsonl` and
   `ledger_<model>.jsonl`; the total-cap check reads both ledgers and the probes.

---

## Outputs

| Item | Location |
|---|---|
| Renderer | `scripts/render_annotation_variants.py` |
| Runner | `scripts/replay_improved_annotation.py` (reuses `scripts/replay_swapped_ids.py`, unmodified) |
| Analysis | `scripts/analyze_improved_annotation.py`; output `analysis.txt` |
| Tests | `tests/unit/test_render_annotation_variants.py`, `tests/unit/test_replay_improved_annotation.py` |
| Data (`data/experiments/2026-11-14-improved-annotation-replay/`) | `manifest.json`, `contact_sheet.jpg`, `grey_1280x960.png`, `probes.jsonl`, `calls_<model>.jsonl`, `ledger_<model>.jsonl`, `budget_<model>.json`, `analysis.txt` (all tracked) |
| Stimulus PNGs | `stimuli/` (48 files, 27 MB): **not tracked** (`.gitignore`); regenerated byte-identically by `--write-manifest` and pinned by the md5s below |
| Report | `docs/reports/2026-11-14-improved-annotation-replay-results.md` |

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-swapid
PY=/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/.venv/bin/python
RUNS=/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/data/logs/vm_runs
$PY scripts/replay_improved_annotation.py --runs-dir $RUNS --write-manifest
$PY scripts/replay_improved_annotation.py --runs-dir $RUNS --probe-only
$PY scripts/replay_improved_annotation.py --runs-dir $RUNS --model gemini
$PY scripts/replay_improved_annotation.py --runs-dir $RUNS --model openai
$PY scripts/analyze_improved_annotation.py > data/experiments/2026-11-14-improved-annotation-replay/analysis.txt
```

---

## Appendix: Stimulus and Prompt Manifest

`data/experiments/2026-11-14-improved-annotation-replay/manifest.json` (md5
`c527aa7d3bb271a2ba3bac3fa418b3e0`) holds, per scene: request id, run, side, correct
robot, raw-frame flag, stored order; the file and pixel md5 of `C_ref`, `L2` and
`K1`; and, per order, the md5 of the base prompt and of the `+P` prompt plus the base
prompt's SHA-256. It also holds the grey image md5, the sentence, its anchor, the seed,
the planned cells, the priority list, the replicates and the pilot scenes.

Grey image `grey_1280x960.png`: md5 `70de6cf74d80bec60dc33666a93f477d` (byte-identical
to the swapped-ID replay's grey image).

File md5 of each stimulus image:

| Scene | Run | Blocker | Correct | Raw | `C_ref` | `L2` | `K1` |
|---|---|---|---|---|---|---|---|
| `53264de9` | 20260925_063520 | west | east | no | `a4109eb947655bbee40d010510acbaf4` | `242fb99d0d53ab2e45f26ad1cb694058` | `9c5420826555dad3e75313cd22c8a37d` |
| `5e7b5a59` | 20260925_065143 | west | east | no | `2fc667245acb825b04b0b3edf9d86afa` | `3031909a5e309449c6500b6956eb1d64` | `60eb262641f97757e663ac6c35d214a8` |
| `2c3fbfa5` | 20260925_070637 | west | east | no | `8b6cbc9359e74362ff72b7c08ae107cf` | `e9fbc26af6304f0b0925ef25c626379e` | `a4e7d68f3ca32f88bba17bb137ded465` |
| `61119197` | 20260925_072130 | east | west | no | `0daabacdb1766e64b90726050fca6b9f` | `c50eac99add962bd2eba158b1308b324` | `64f6039a9b29ea172f7ebb7bd84ad3ef` |
| `d053d0dc` | 20260925_073621 | east | west | no | `98f254598bfbacda4746467a60a9a133` | `182159852db5a921a4b45ce8cfc02469` | `1363620a8513887d327f80fd70c6b86f` |
| `3120c65f` | 20260925_075116 | east | west | no | `9175e604a6d1f3edd286c3889caf481f` | `8a08bfb70db51b9ae695358e9a2f3964` | `c81537c70b0032e23e7fbd349e1604e6` |
| `810c9104` | 20260925_155433 | west | east | yes | `f28ca2c11a016e664cafca8286a4dbe7` | `3fde4c9b5b804e3825689bdb91c19c53` | `f08ce8fad8a0c0b8b2634335d89feaef` |
| `42fb0cb8` | 20260925_160951 | west | east | yes | `fd0d41a9896687eb627d40a9234afdc9` | `52d45013659c32d90560545f2438b3bf` | `27562ff60a6ec7ef6454288e9925f597` |
| `d4b96fbd` | 20260925_162451 | west | east | yes | `0fa40f4836504ef3198ea29d7b905c49` | `f2b1451c7facdc2919b518a67abcb5e0` | `78b8fb587e49a5391658cda489eed088` |
| `189ae2a6` | 20260925_163949 | east | west | yes | `a626215a6af4453b996ae16a1f7b20e8` | `af8c25665ecf530f2d293b2889ed33bf` | `ced4ab4f7a2b5e86d329f0c4b7cf114c` |
| `e4b1bd03` | 20260925_165442 | east | west | yes | `c412b42f32a50a0dff2fcbf8a286a4bf` | `38ff8296c739326772195af854258d5f` | `bf75cde67aaa2fbf0f10f4b364482d34` |
| `618a9f29` | 20260925_170938 | east | west | yes | `f9ec8159463397a1fe8d60ae99a642a6` | `be766793cebf3a902fa6879839597a41` | `6dd010f75d9bb74463e7677e327af3ef` |
| `710c40e5` | 20260925_124609 | west | east | no | `74612c46f17e19e38cc5f2fee84da723` | `82283ec3cd5c7b2065abb44427d35cdf` | `e002acd229484e74c00b7e5efc612c9f` |
| `7b0fbf9e` | 20260925_130115 | west | east | no | `6cfd4f7c5ff2d07a835b7b779f263694` | `a49427ba9e55a3d107b7b4d34d6780fd` | `b13001933617659728ce848bba4b1609` |
| `ea126abd` | 20260925_132335 | west | east | no | `17cc675661ae2ea279d2c055b257e7c7` | `88a3508b693002d83e6ed6f92e617df3` | `426f30ba3768e5a78d759d9a7562a11f` |
| `bb48067c` | 20260925_133841 | east | west | no | `2100cacc03a32f2fb4c12821495e4d2a` | `feca2c3a8b379ba04b3768fac121225f` | `8132f34cddd079008707a2676235ad2f` |
| `d592a820` | 20260925_135334 | east | west | no | `21c1af1f3d492778dc8934575ec8a6bd` | `9a7f2f2b5816cad53c8668ebe294fca9` | `085cf5aea2eda24556a39d9d9a68ec05` |
| `32aec602` | 20260925_140824 | east | west | no | `6121a851372a5d7a451f2d101b1aa557` | `23f0e13d233f713efa0df917cdcc1a08` | `f30e740221858b0f0b932bacafeb3fe5` |
| `bc56a57a` | 20260925_183343 | west | east | yes | `0134e4f76d2d98383e4cbc9ab9da1871` | `b892bebc41e97ead55c188e5f126f52c` | `9930393df38780f0c3adb3910ae4a58b` |
| `920ec0d9` | 20260925_184840 | west | east | yes | `4b3081396a4c193a8bf066e0b4f55fa7` | `eb4b6e30c63102c562e15870c1da3de6` | `718240883bd641355f376e498fd14573` |
| `8027a8a2` | 20260925_190322 | west | east | yes | `db5f9bd54be4a7f71df795a4d0472188` | `ed1607d2da437599d22ac3768678e5e2` | `a9afce4b293e6167d46d143c1065a4fb` |
| `41d72639` | 20260925_191810 | east | west | yes | `02a3a629356a45aaf3391269ae3ddd21` | `f3537c04e80a6914911cfefd7903634f` | `0adf9ffb83a31e8f1de3206f2bd0d044` |
| `653be8f3` | 20260925_193307 | east | west | yes | `549f7a6ebbab5f972b30f1c80568a0dd` | `0606ab867f7a767fa61660b8ecc83d98` | `fd145bb6e216997e541c5d3726c41479` |
| `f94cb7ed` | 20260925_194800 | east | west | yes | `945f33e34b3b78dfb1054b0ba1bbc1ed` | `fd34c6c286fa692f0db0b0ff5481f2a6` | `9f60d2fee4b957c4b24dc8fa5c2cf0e7` |

The 96 prompt md5s (24 scenes x 2 orders x base/`+P`) are in `manifest.json`.

---

## Amendments

None yet.

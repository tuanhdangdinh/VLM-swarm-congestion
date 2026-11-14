# Improved-Annotation Replay - Results

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: results of the pre-registered offline replay (design `docs/superpowers/specs/2026-11-14-improved-annotation-replay-design.md`, Rev 2 with amendment 1). Both providers stopped on account limits part-way; every pre-stated verdict is not assessable; descriptive counts and the ER-2 replicate-1 indication are reported.

---

## Question and Answer

**Question.** On the 24 head-on standoff scenes, with no obstacle text in the prompt,
does a model name the physically correct yielder from the camera frame once the frame
is easier to read (Type L, `L2`)? Does a neutral sentence, "A robot that backs up needs
free floor behind it.", change that?

**Answer under the pre-registered rules: not assessable.** Neither model completed
its runs.

- **OpenAI:** stopped at 15:29 UTC with "no credits remaining". gpt-4o has 231 of 672
  runs.
- **Gemini:** stopped at 16:08 UTC by the project's monthly spending cap. ER-2 has 457
  of 1,344 runs.
- Both stops are pre-stated stop rules, and neither provider was retried.
- Every cell is incomplete, so rule 6 makes every verdict "not assessable". This is a
  **missing result, not a negative one.**

**What the incomplete data show** (descriptive, not a verdict):

- **ER-2 with the line and a legible frame (`L2+P`)** named the correct robot in
  **55 of 67 runs**. All 55 of its named yielders were correct, on both sides and
  under both orders (west side 30/30, east side 25/25).
  - Without the line, `L2` was 11/64. The grey control with the line, `D_ref+P`, was
    8/67, against `D_ref` 7/66.
  - So **the line alone does not move ER-2 with the grey image, but it does with the
    frame.** The shipped frame plus the line (`C_ref+P`) gave 43/66.
  - On the one complete balanced subset (replicate 1, 48 runs per cell), `L2+P` was
    10, 7, 10 and 10 correct of 12 in the four side x order cells. The 7/12 cell misses
    the pre-stated 9/12 share, so even this subset does not meet the rule's shares.
- **gpt-4o** still follows the first-listed robot in every cell. Under `id_asc` it
  chose the first-listed robot in 109 of 110 named runs. Its partial cells show no
  side-consistent signal with or without the line.

**Evidence grade:** a small designed offline experiment, pre-registered before the
first paid call, **stopped part-way by account limits** and amended once (before any
table was read). Twenty-four scenes, one scenario family, seed 42, two visual layouts,
two robots, first decision only, no execution. Counts only. A new stratum, never
pooled.

---

## Design as Frozen

Full design in the spec (pre-registration commit `21d1ddd`; amendment 1 `b9ef9dd`).

| Item | Value |
|---|---|
| Scenes | 24 SHA-verified first standoffs (12 blocked west, 12 blocked east): the 12 swapped-ID replay stimuli plus 12 from the 2026-09-25 ER-2 live runs. `robot_1` is the west robot in all 24 (asserted). |
| Prompt | prompt v1, obstacle text off, original IDs, both orders (`id_asc`, `id_desc`) |
| Image levels | `C_ref` annotated frame; `D_ref` grey; `L2` legible labels + fixed crop/upscale (Type L); `K1` = L2 + obstacle footprint outline and `obstacle_1` (Type K) |
| Line | "A robot that backs up needs free floor behind it." appended to the head-on Guidance bullet after `strategy="reverse" (both back up to clear).`, inserted on every attempt |
| Cells | `L2`, `D_ref`, `L2+P`, `D_ref+P`, `C_ref`, `K1`, `C_ref+P`; `K1+P` cut before any call (ER-2's full set, $6.14, exceeded its $6.00 cap) |
| Replicates | gpt-4o 2, ER-2 4, per scene x order (planned 96 / 192 runs per cell) |
| Order | 28-run pilot per model, then replicate blocks, each shuffled with a recorded seed (`20261114`), so cells are interleaved in time |
| Caps | $12.00 total, $6.00 per model |

**Pre-stated rules** (spec, "Decision Rules"):

1. **Image use (rule 1).** In each side x order cell, at least 75% of runs correct
   (gpt-4o 18/24, ER-2 36/48). In each, at least 8 of the side's 12 scenes mostly
   correct (2/2 or 3/4). And at least 0.25 above the same-prompt grey control.
2. **Legibility (rule 2).** `L2` passes, `C_ref` fails, and the difference is at
   least 0.15.
3. **Annotation reading (rule 3).** Rule 1 for `K1`, never counted as image use.
4. **Prompt-line effect (rule 4).** `L2+P - L2` and `D_ref+P - D_ref`. The `D_ref+P`
   check is read first. The line-alone flag fires at +0.15 overall or ±0.25 on a side.
5. **ER-2 conditional image use (rule 5).** At least 12 named runs per side, from at
   least 6 scenes, at least 4 per order. At least 0.80 correct on each side. At least
   0.25 above the grey control where that control is assessable.
6. **Not assessable.** A cell stopped, cut, incomplete, or with fewer than 20
   decisions.

**Checks done before any call:**

- **Tests.** 148 offline tests passed with 0 skipped, covering for all 24 scenes:
  - the Type L change zone;
  - the fixed crop;
  - K1 = L2 plus only the outline and label;
  - determinism and the md5 manifest;
  - text-off prompts;
  - `+P` = base plus exactly the one sentence, on every attempt.
- **Drift baseline.** The 24 base prompts of the original 12 scenes are byte-identical
  (SHA-256) to the earlier replay's text-off prompts.
- **Contact sheet.** All 48 L2/K1 stimuli were inspected. Labels never cover the
  obstacle. The crop keeps both robots and both corridor ends. K1's outline sits on the
  box's shaded side face (kept, as designed).

---

## Deviations

1. **Both providers stopped on account limits (amendment 1).**
   - **OpenAI:** HTTP 429 "You have no credits remaining", at 15:29:52 UTC, after 231
     runs.
   - **Gemini:** HTTP 429 "temporarily rate-limited to prevent exceeding its monthly
     spending cap", at 16:08:31 UTC, after 457 runs.
   - The experiment's own caps were never approached (total $3.50 of $12.00).
   - No re-probe, retry or substitute was made.
2. **Amendment 1, analysis code after rows existed, before any table was read.**
   - `conditional_rule` and `line_alone_flag` now return "not assessable" on
     incomplete cells. As frozen, they lacked the completeness check that rule 6
     requires.
   - The two provider-stop rows (one per model) are excluded as non-outcomes.
   - The runner re-runs such keys on resume.
   - An ER-2 replicate-1 "indication" view was added, using the same shares at r = 1.
     It is an indication only and carries no verdict.
   - Already seen before the amendment: the gpt-4o pooled census (121 correct, 109
     wrong) and individual progress lines.
3. **Renderer fix before any call** (design, "Differences From the Scope"): scene
   `61119197`'s robot_1 was drawn in M1's SLOW yellow. The prototype left a yellow
   label ghost and recoloured the box red. The promoted renderer keeps each robot's
   frame colour. The other 23 scenes are pixel-identical to the prototype.
4. **Scope correction:** M1 velocity arrows are present in several frames (the scope
   said none). They are unchanged between `C_ref` and `L2`.
5. **`K1+P` cut before any call** for budget (ER-2 cap). `L1` and `L2swap` were not
   run (scope defaults).
6. **Pilot rows.** 4 of each cell's runs are the pilot, run before the main shuffle.

---

## Results: Gemini ER-2 (`gemini-robotics-er-2-preview`, 457 runs)

- Every one of the 457 runs was served as `gemini-robotics-er-2-preview`.
- All 457 attempt-1 prompts matched the manifest exactly.
- 0 refusals, 0 parse failures, 0 model errors.
- The pilot rule stopped no cell.
- Runs per cell: 62-67 of the planned 192.

### Outcome and strategy census

| Cell | Runs | Correct | Wrong | `reverse`, no yielder | Named yielders | Named correct |
|---|---|---|---|---|---|---|
| `D_ref` | 66 | 7 | 7 | 52 | 14 | 7/14 |
| `D_ref+P` | 67 | 8 | 7 | 52 | 15 | 8/15 |
| `C_ref` | 62 | 12 | 5 | 45 | 17 | 12/17 |
| `C_ref+P` | 66 | 43 | 1 | 22 | 44 | 43/44 |
| `L2` | 64 | 11 | 9 | 44 | 20 | 11/20 |
| `L2+P` | 67 | **55** | **0** | 12 | 55 | **55/55** |
| `K1` (annotation reading) | 65 | 30 | 4 | 31 | 34 | 30/34 |

Every non-correct, non-wrong run is `reverse` with no yielder. No other outcome
occurred.

### P(correct) by side x order (runs; [scenes mostly correct])

All data, replicates 1-2. Cells hold unequal numbers of runs, because the stop cut
replicate 2.

| Blocker | Order | `D_ref` | `D_ref+P` | `C_ref` | `C_ref+P` | `L2` | `L2+P` | `K1` |
|---|---|---|---|---|---|---|---|---|
| west | `id_asc` | 0/18 | 0/19 | 2/15 | 12/21 | 2/17 | **16/18** | 5/12 |
| west | `id_desc` | 0/16 | 1/17 | 3/15 | 11/15 | 1/15 | **14/19** | 8/19 |
| east | `id_asc` | 3/16 | 2/14 | 3/17 | 11/15 | 3/16 | **13/16** | 9/17 |
| east | `id_desc` | 4/16 | 5/17 | 4/15 | 9/15 | 5/16 | **12/14** | 8/17 |
| all | all | 7/66 | 8/67 | 12/62 | 43/66 | 11/64 | **55/67** | 30/65 |

Among named yielders, by blocked side:

| Cell | West side correct | East side correct | Named runs choosing the west robot |
|---|---|---|---|
| `D_ref` | 0/7 | 7/7 | 14/14 |
| `D_ref+P` | 1/8 | 7/7 | 14/15 |
| `C_ref` | 5/8 | 7/9 | 10/17 |
| `C_ref+P` | 23/23 | 20/21 | 20/44 |
| `L2` | 3/5 | 8/15 | 10/20 |
| `L2+P` | **30/30** | **25/25** | 25/55 |
| `K1` | 13/14 | 17/20 | 18/34 |

With the grey image, ER-2's rare named yielders are almost always the west robot
(`robot_1`): 28 of 29 across `D_ref` and `D_ref+P`, so they are correct only on the
east side. With `L2+P` and `C_ref+P`, the named robot follows the blocked side.

### Replicate 1 only (amendment 1 indication; 48 runs per cell, complete and balanced)

| Blocker | Order | `D_ref` | `D_ref+P` | `C_ref` | `C_ref+P` | `L2` | `L2+P` | `K1` |
|---|---|---|---|---|---|---|---|---|
| west | `id_asc` | 0/12 | 0/12 | 2/12 | 8/12 | 1/12 | 10/12 | 5/12 |
| west | `id_desc` | 0/12 | 1/12 | 3/12 | 9/12 | 1/12 | **7/12** | 5/12 |
| east | `id_asc` | 3/12 | 2/12 | 3/12 | 8/12 | 1/12 | 10/12 | 7/12 |
| east | `id_desc` | 3/12 | 3/12 | 3/12 | 7/12 | 4/12 | 10/12 | 7/12 |
| all | all | 6/48 | 6/48 | 11/48 | 32/48 | 7/48 | **37/48** | 24/48 |

Rule 1's shares at r = 1 (at least 9/12 in every side x order cell, and at least 0.25
above the grey control) are **met by no cell**:

- `L2+P` misses only through west `id_desc` (7/12). Its margin over `D_ref+P` is
  +0.65.
- `C_ref+P` misses in three cells (8, 8 and 7 of 12). Its margin is +0.54.
- `K1` does not reach 9/12 in any cell. Its margin over `D_ref` is +0.38.
- `L2` (+0.02) and `C_ref` (+0.10) are close to the grey control.

The `L2+P` runs show no time trend: 2/4 in the pilot (both misses were `reverse`),
35/44 in the replicate-1 block, 18/19 in the partial replicate-2 block.

### Verdicts

| Rule | Verdict |
|---|---|
| 1. Image use: `L2`, `C_ref`, `L2+P`, `C_ref+P` | **not assessable** (every cell 62-67 of 192 runs) |
| 2. Legibility: `L2` vs `C_ref`, `L2+P` vs `C_ref+P` | **not assessable** |
| 3. Annotation reading: `K1` | **not assessable** |
| 4. `D_ref+P` line-alone check | **not assessable**. Descriptively: `D_ref+P - D_ref` = +0.01 overall, +0.03 west side, +0.01 east side. Below both flag thresholds, and the strategy mix is unchanged (52 `reverse` in each). |
| 4. Line effect, descriptive | `L2+P - L2` = +0.65; `C_ref+P - C_ref` = +0.46 |
| 5. ER-2 conditional image use | **not assessable**. `L2+P`, `C_ref+P` and `K1` meet the naming minimums, but their grey controls are incomplete, and rule 6 applies to the whole rule |

---

## Results: gpt-4o (`gpt-4o-2024-08-06`, 231 runs)

- All 231 runs, and all 240 billed attempts, were served as `gpt-4o-2024-08-06`.
- All attempt-1 prompts matched the manifest.
- Cells hold 29-37 of the planned 96 runs, on **different scene/order subsets**. So
  only within-cell counts are shown, and no cross-cell contrast is interpreted.
- Attempt-1 refusals: `C_ref` 4, `C_ref+P` 2, `D_ref+P` 1. Two runs were decided after
  the grey fallback (`C_ref`, `D_ref+P`). Excluding them changes no count by more than
  1.

### Descriptive table (runs; partial cells)

| Blocker | Order | `D_ref` | `D_ref+P` | `C_ref` | `C_ref+P` | `L2` | `L2+P` | `K1` |
|---|---|---|---|---|---|---|---|---|
| west | `id_asc` | 0/8 | 0/7 | 0/7 | 0/5 | 1/10 | 0/5 | 0/9 |
| west | `id_desc` | 3/8 | 1/7 | 6/11 | 4/7 | 2/11 | 2/5 | 1/9 |
| east | `id_asc` | 7/7 | 11/12 | 8/8 | 7/7 | 9/9 | 10/10 | 7/7 |
| east | `id_desc` | 7/11 | 5/7 | 5/9 | 4/10 | 7/7 | 8/9 | 6/9 |
| all | all | 17/34 | 17/33 | 19/35 | 15/29 | 19/37 | 20/29 | 14/34 |

- gpt-4o named a yielder in 230 of 231 runs; one `D_ref+P` run answered no congestion.
- **Slot:** under `id_asc` it chose the first-listed robot (`robot_1`, west) in
  **109 of 110** named runs, in every cell. The west-blocked `id_asc` cell, where the
  first-listed robot is the wrong one, is 1 of 51 correct across all cells.
- **Label:** under `id_desc` it chose the west robot (`robot_1`) in 81 of 120.
  Overall the west robot was chosen in 190 of 230.

### Verdicts

Every rule is **not assessable** (incomplete cells). Descriptively, the pattern is the
swapped-ID replay's: the slot, then the `robot_1` label, decide. Neither the legible
frame nor the line visibly changes it in these partial cells.

---

## Same-Day Drift Check (original 12 scenes; side by side, never pooled)

Earlier swapped-ID replay (same day; its rows carry no timestamps, and its data were
committed at 14:16 UTC; 2 replicates) against this run (partial, 15:13-16:08 UTC).

| Model | Blocker | Order | earlier `C_real_notext` | this `C_ref` | earlier `D_grey_notext` | this `D_ref` |
|---|---|---|---|---|---|---|
| ER-2 | west | `id_asc` | 0/12 | 0/6 | 1/12 | 0/9 |
| ER-2 | west | `id_desc` | 3/12 | 1/7 | 0/12 | 0/9 |
| ER-2 | east | `id_asc` | 2/12 | 1/10 | 0/12 | 0/9 |
| ER-2 | east | `id_desc` | 5/12 | 2/7 | 1/12 | 1/7 |
| gpt-4o | west | `id_asc` | 0/12 | 0/5 | 0/12 | 0/5 |
| gpt-4o | west | `id_desc` | 7/12 | 3/6 | 5/12 | 1/4 |
| gpt-4o | east | `id_asc` | 12/12 | 5/5 | 11/12 | 5/5 |
| gpt-4o | east | `id_desc` | 7/12 | 3/5 | 8/12 | 4/5 |

- **ER-2:** `reverse` share earlier 37/48 (frame) and 41/48 (grey); here 25/30 and
  30/34.
- **gpt-4o:** named a yielder in every run in both sessions.
- No change of pattern is visible between the two sessions. The counts are small.

---

## Cost Ledger

From `ledger_<model>.jsonl` and `probes.jsonl`, priced from recorded token usage
(gpt-4o $2.50 / $10.00 per MTok; ER-2 $1.00 / $5.00, thought tokens as output).

| Model | Runs | API calls | Spend | Per run |
|---|---|---|---|---|
| ER-2 | 458 (1 stop row) | 458 | $1.88 | $0.0041 |
| gpt-4o | 232 (1 stop row) | 241 | $1.62 | $0.0070 |
| Probes | 2 | 2 | $0.002 | |
| **Total** | **690** | **701** | **$3.50** | |

- Caps $12.00 total and $6.00 per model were never approached.
- The only failed calls were the two account-limit 429s, each counted once as a
  transient retry in the ledger. No other transient errors occurred.
- ER-2's mean wall time was 7.2 s per run, as before.
- **Finishing the design** needs 441 gpt-4o runs (about $3.08) and 887 ER-2 runs
  (about $3.64), about $6.70, for about $10.20 overall.

---

## Limitations

- **Incomplete.** Every cell holds roughly a third of its planned runs. The ER-2 view
  uses the one balanced subset (replicate 1). gpt-4o's cells are unbalanced subsets.
- **One scenario family, two layouts, one seed, two robots.** The obstacle sits at the
  same pixels in every scene of a side, so a model could learn nothing general from
  these 24 scenes. Conversely, the blocked side could correlate with any fixed image
  feature, not only the obstacle: the corridor ends, fixtures, shadows.
- **First decision only.** Offline, no M3 gate, no execution.
- **Provider preprocessing.**
  - gpt-4o downsizes the 1280 x 960 frame to 1024 x 768 and keeps the 2048 x 640 crop
    at native size (documented rule).
  - ER-2's resampling to its fixed image-token budget is undocumented.
- **Replicates are dependent** within a scene, and ER-2 takes no temperature.
- **The line changes the prompt.** The `+P` cells test "image with the line", not the
  shipped prompt.
  - The `D_ref+P` control shows that the line does not by itself change ER-2's
    correctness or its `reverse` share with a grey image.
  - That control is incomplete, so the check is descriptive.
- **Analysis code timing.**
  - Written, tested and committed with the design before the first call (`21d1ddd`).
  - Amended after rows existed but before any table was read (`b9ef9dd`): the
    completeness gate, stop-row exclusion and replicate-1 view.
  - Already seen before the amendment: the gpt-4o pooled census and progress lines.
- **Pilot rows** (4 per cell) ran first, outside the shuffle.

---

## What the Thesis May and May Not Say

In plain words: we prepared a fair test of whether a model can see which end of the
corridor is blocked once the robot labels are made readable. We also tested whether one
neutral sentence ("a robot that backs up needs free floor behind it") changes that. The
run was cut off by the providers' billing limits after about a third of the planned
calls. Under the rules we fixed in advance, the test therefore gives **no verdict**.

The partial data contain the first strong lead of its kind in this project. With the
readable frame and the sentence together, Gemini ER-2 picked the robot with free space
behind it in 55 of 67 runs and never picked the wrong one. With the same sentence and a
blank grey image it did no better than before (8 of 67). With the readable frame but no
sentence it also did no better (11 of 64).

That pattern suggests ER-2 can read the blocked side from the picture when told that
backing up needs room. But it is incomplete. It misses the pre-set bar in one of four
cells of the only complete subset. And it comes from two fixed layouts of one scenario.
gpt-4o showed no such effect and kept choosing by listing order.

The thesis **may** say:

- the pre-registered improved-annotation test was run but stopped by provider billing
  limits, and gives no verdict;
- in the incomplete data, ER-2 with legible labels plus the neutral back-up sentence
  named the correct yielder in 55/67 runs (55/55 named, both sides, both orders);
  without the sentence, or with a grey image, it did not (11/64; 8/67);
- the grey-image control with the sentence did not move, so the sentence did not
  supply the answer by itself;
- gpt-4o's choice still follows the listing order under every variant tested.

The thesis **may not** say:

- that ER-2 (or any VLM) uses the image to choose the yielder: no pre-stated rule was
  assessable, and even the complete replicate-1 subset misses the pre-set share in one
  cell;
- anything beyond these two layouts of one head-on scenario, or about closed-loop
  behaviour.

**If the completed run gives other outcomes:**

| Outcome | What the thesis may say |
|---|---|
| "L2 fails, K1 passes" | The model reads a system-drawn overlay. This does **not** support the thesis sentence, because the fact came from M5's geometry. |
| "Passes only with the prompt line" (`L2+P` passes, `L2` fails, and the `D_ref+P` check is clean) | Line-dependent image use: the model uses the picture only when the task states that backing up needs room. That is a property of the prompt plus the model, not of the shipped prompt. It would be the first positive evidence of image use here. It is narrow: one family, two layouts, one sentence. |
| No rule passes | The current conclusion stands: the yielder comes from M3's feasibility gate, not from M2. |

---

## Reproducibility

| Item | Location (branch `exp/head-on-swapped-id-replay`) |
|---|---|
| Design and amendment 1 | `docs/superpowers/specs/2026-11-14-improved-annotation-replay-design.md` (`21d1ddd`, `b9ef9dd`) |
| Renderer | `scripts/render_annotation_variants.py` |
| Runner | `scripts/replay_improved_annotation.py` (resumable; reuses `scripts/replay_swapped_ids.py`) |
| Analysis | `scripts/analyze_improved_annotation.py`; output `analysis.txt` |
| Tests | `tests/unit/test_render_annotation_variants.py`, `tests/unit/test_replay_improved_annotation.py` (151 pass, 0 skipped) |
| Data (`data/experiments/2026-11-14-improved-annotation-replay/`) | `manifest.json`, `contact_sheet.jpg`, `grey_1280x960.png`, `probes.jsonl`, `calls_{gemini,openai}.jsonl` (every attempt's text, tokens, served model, timestamps, seq; no images or keys), `ledger_*.jsonl`, `budget_*.json`, `analysis.txt` |
| Stimulus PNGs | not tracked; regenerated byte-identically by `--write-manifest` |

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-swapid
PY=/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/.venv/bin/python
$PY scripts/analyze_improved_annotation.py
```

**To finish the design**, the owner must top up OpenAI and raise the Gemini project
spend cap, and a dated amendment must record the session gap before the first resumed
call. Then run `scripts/replay_improved_annotation.py --runs-dir <vm_runs> --model
gemini` (and `--model openai`); the runner resumes on its keys.

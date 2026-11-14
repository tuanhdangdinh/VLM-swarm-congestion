# Head-On JSON-Only Replay - Results

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: results of the pre-registered JSON-only stratum (design `docs/superpowers/specs/2026-11-14-head-on-json-only-replay-design.md`), with the owner's prompt-compatibility gate and the opt-in `reasoning_extraction` no-retry option.

---

## Question and Answer

**Question.** With the `<think>` answer-format block of prompt v1 replaced by a
JSON-only line, for every model alike:

1. Does any of ER-2, gpt-4o or Sonnet 5.5 pick the head-on yielder from the scene,
   rather than from the label or the listing slot?
2. Is one shared prompt text usable by every provider?

**Answer.**

- **Shared prompt.** Two of the three providers were tested, and both accept it: ER-2
  and Sonnet each answered 8 of 8 compatibility-pilot runs on attempt 1, with no
  refusal, no parse failure and no fallback. Sonnet then answered all 146 runs (0
  refusals, against 44 of 64 attempt-1 refusals under the v1 ending). gpt-4o could not
  be tested: the OpenAI account has no credits (probe HTTP 429,
  `insufficient_quota`).
- **Live prompt.** The current production prompt (v3.4) ends with the same JSON-only
  line. ER-2 and Sonnet each answered one call of it on attempt 1.
- **Scene use.** Not supported for Sonnet, now assessable for it for the first time:
  46/96 correct in the grey pair. Not assessable for ER-2: Google's spend cap stopped
  it after 50 of the 96 grey-pair runs. Descriptively, it still answers `reverse` in 46
  of those 50, and one combination is already at 2/12, so even if the missing runs had
  all been correct it could not have passed (at most 14/24).
- **Sonnet's prior.** On the grey image Sonnet mostly names the robot labelled
  `robot_2`: 76 of 96 grey-pair runs. Because of that, its correctness tracks where the
  label `robot_2` sits, not the blocker. The pre-registered label-bias rule narrowly
  does not fire: P(`robot_1`) is 0.27 in `A_grey` against a threshold of 0.25, and 0.15
  in `B_grey`.

**Evidence grade:** a small designed offline experiment, pre-registered and committed
before the first paid call, with no amendment. 12 scenes from one family at seed 42,
two robots, first decision only, no execution. Two provider stops cut the design (see
"Deviations"). Counts only; no p-values and no intervals. A new stratum, never pooled.

---

## Compatibility Pilot and Live-Prompt Check

The owner gate: 8 runs per provider over both sides, both orders and all five cells,
with pass criteria fixed in advance.

| Provider | Runs | Answered on attempt 1 | Provider refusals | Parse failures | Fallback used | Served model | Gate |
|---|---|---|---|---|---|---|---|
| Google, ER-2 | 8 | 8 | 0 | 0 | 0 | `gemini-robotics-er-2-preview` | **passed** |
| OpenAI, gpt-4o | 0 | - | - | - | - | - | **not run**: probe HTTP 429 `insufficient_quota` / `credit_balance_exhausted` |
| Anthropic, Sonnet 5.5 | 8 | 8 | 0 | 0 | 0 | `claude-sonnet-5-5` | **passed** |

- **One text per stimulus.** For each of the 54 cells that both ER-2 and Sonnet ran,
  attempt 1's user, system and image SHA-256 are identical across the two providers.
  For all 200 rows, attempt 1's user and system SHA-256 equal the pre-registered
  manifest, and its image SHA-256 equals the manifest's grey or frame hash. The manifest itself proves
  the diff against v1 is exactly the answer-format block, for all 72 stimulus x order
  x ID/text prompts.
- **What differs between providers.** Only transport, owned by the backends: where the
  system text goes, whether the image comes before or after the text, and each
  provider's thinking control (design, "One Prompt for Every Provider", with file:line).
  No backend adds prompt text: the recorded `payload_format.json_guidance` is
  `prompt_only` on every row, and no JSON mode or `response_format` is sent.
- **Live-prompt check (v3.4).** One call per provider, outside every table. Stimulus
  `53264de9`, `id_asc`, annotated frame, obstacle text on. ER-2 answered on attempt 1
  (`yield`, `robot_1`). Sonnet answered on attempt 1 (`yield`, `robot_2`; 3,830 input
  tokens). gpt-4o was not tested.
  - v3.4's last line is byte-identical to the JSON-only line used here, preceded by the
    same `...must be non-empty.` and one blank line.
  - Its body differs: a `reasoning` field, `blocker_kind`, `crossing_order` and
    `proposed_plan` in the schema, plus its own guidance lines.
  - So "today's live prompt is accepted" rests on n = 1 per provider and holds for two
    providers only.

---

## Design as Frozen

- The 12 SHA-verified standoff stimuli of the swapped-ID replay, both orders, 2
  replicates, 48 runs per cell per model.
- Cells, in priority tiers: `A_grey` + `B_grey` (tier 1), `A_real` (tier 2), then
  `C_real_notext` + `D_grey_notext` (tier 3). Within a model and tier, runs are
  interleaved by a seeded shuffle (`run_order.json`).
- The prompt is the stored v1 prompt with the answer-format block replaced by "Write
  ONLY the final JSON object, with no surrounding text or markdown." The replacement is
  made in the runner's backend-agnostic prompt layer, on every attempt.
- Each model runs its shipped retry config plus
  `final_refusal_categories = ("reasoning_extraction",)`.
- Scoring, outcome classes and decision rules are those of the swapped-ID design,
  unchanged.
- Caps: $5.00 in total and $2.00 per model. A tier starts only if it fits whole.
- Pre-registration commit `071257a` (runner `62c40c7`, reasoner option `b72891e`). Every
  row records commit `071257a`.

---

## Deviations

1. **gpt-4o not run.** The OpenAI probe returned HTTP 429 "You have no credits
   remaining" (`insufficient_quota`, `credit_balance_exhausted`). Under the probe rule
   the provider was skipped, with no retry and no substitution. Consequences:
   - gpt-4o has no compatibility pilot, no live check, no tables and no answer-format
     comparison;
   - the cross-provider identity check covers two providers.
2. **ER-2 stopped after 54 runs.** On its 54th design run, Gemini returned HTTP 429
   "Your project is temporarily rate-limited to prevent exceeding its monthly spending
   cap". The quota rule stopped the provider at once.
   - ER-2 has its 8 pilot runs and 46 tier-1 runs (45 answered, 1 `error` row,
     counted). That is 50 of the 96 grey-pair runs; tiers 2 and 3 were not run.
   - The account cap, not this job's spend, ended it: ER-2 had spent $0.21 here.
     Another job was making Gemini calls on the same project at the same time
     (inferred, not checked).
3. **Sonnet's tier 3 cut by the tier rule, as estimated in advance.** With $1.1379
   spent, 94 runs x $0.0077 x 1.15 + one worst-case run ($0.1099) would pass $2.00. So
   Sonnet has `C_real_notext` and `D_grey_notext` only from the pilot (1 run each), and
   its image-use rule is not assessable.
4. **Pre-registered rules that never fired.** The `reasoning_extraction` option never
   fired: there was no refusal of any kind, so its savings are unobserved (unit-tested
   only). The cell rule and the Sonnet rule never fired.
5. `scripts/analyze_swapped_ids.py` counts the probe and live-check calls in its
   per-model `network_calls`. Its run counts come from `calls.jsonl` and are correct.

No amendment was made; every stop above follows a rule written before the first call.

---

## The `reasoning_extraction` No-Retry Option (Option 3)

- **What it is.** `ReasonerConfig.final_refusal_categories`
  (`reasoning/vlm/models.py:1012`; logic in `reasoning/vlm/reasoner.py:514-538`;
  commit `b72891e`). A provider refusal whose category is listed ends the call on that
  attempt as a refusal result: no re-ask, no image fallback,
  `error_type = "FinalRefusal"`, and the category and reason are kept in diagnostics.
  Other refusals and parse failures follow the existing policy. The code is
  backend-agnostic; backends still only report the category.
- **Scope.** Default empty. No shipped config enables it (pinned by a test). It was
  enabled only in this experiment's runner, for `reasoning_extraction`, identically
  for every model; in practice only Anthropic returns that category.
- **Effect on the October ruling.** It changes October's retry-parity ruling
  (`docs/reports/2026-10-06-roster-validation.md`, ruling 1) only while it is enabled.
  The owner approved it on 2026-11-14 ("I approve options 2 and 3").
- **Not lossless.** A refusal that a later attempt would have answered is lost. The
  brief states that October recovered 4 decisions on later attempts; that figure is
  copied from the brief, not re-derived. In this stratum the option never fired:
  Sonnet did not refuse once.
- **Tests.** 17 unit tests (`tests/unit/test_reasoner_final_refusal.py`). They cover
  default-off behaviour identical to before (attempt sequence, fallback, late
  recovery); a stop after the listed category, also after an earlier parse failure;
  unlisted, uncategorised and text-pattern refusals not being final; the result and
  diagnostics shape; and config validation.

---

## Results per Model

### Claude Sonnet 5.5 (`claude-sonnet-5-5`, 146 runs, all served as that model)

Every run answered on attempt 1: no refusal, no re-ask, no fallback. The strategy is
`yield` in 146/146 runs. Mean cost per run $0.0077 (2,914 input and 189 output tokens;
0 thinking tokens).

Outcome census:

| Cell | Runs | Correct | Wrong |
|---|---|---|---|
| `A_grey` | 48 | 19 | 29 |
| `B_grey` | 48 | 27 | 21 |
| `A_real` | 48 | 18 | 30 |
| `C_real_notext` (pilot only) | 1 | 1 | 0 |
| `D_grey_notext` (pilot only) | 1 | 1 | 0 |

P(names the physically correct robot), runs [scenes with 2/2 of 6]:

| Blocker | Order | `A_real` | `A_grey` | `B_grey` |
|---|---|---|---|---|
| west | `id_asc` | 6/12 [1] | 10/12 [4] | 0/12 [0] |
| west | `id_desc` | 1/12 [0] | 5/12 [1] | 5/12 [1] |
| east | `id_asc` | 6/12 [1] | 1/12 [0] | 12/12 [6] |
| east | `id_desc` | 5/12 [2] | 3/12 [0] | 10/12 [5] |

Grey-pair label x slot combinations (24 runs, 12 scenes each):

| Combination | Correct | Scenes 2/2 |
|---|---|---|
| label right, slot right | 1/24 | 0/12 |
| label right, slot wrong | 8/24 | 1/12 |
| label wrong, slot right | 15/24 | 6/12 |
| label wrong, slot wrong | 22/24 | 10/12 |

"Label right" means `robot_1` sits on the correct robot, so "label wrong" means
`robot_2` does. Sonnet is right mostly when `robot_2` is the correct robot. The `A_real`
combinations are 6/12, 5/12, 1/12 and 6/12 (scenes 1, 2, 0 and 1 of 6).

Marginal effects (grey pair, 96 runs, all naming a yielder; 0.5 = no effect):

- label: 20/96 chose `robot_1` (`A_grey` 13/48, `B_grey` 7/48), so 76/96 chose
  `robot_2`;
- slot: 34/96 chose the first-listed robot. `id_asc`: 3/48 (it picks the second-listed
  robot, `robot_2`). `id_desc`: 31/48 (the first-listed robot is `robot_2`);
- scene: 46/96 chose the correct robot.

`robot_2` choices by order: `A_grey` 21/24 (`id_asc`) and 14/24 (`id_desc`); `B_grey`
24/24 and 17/24. On the annotated frame (`A_real`) the preference is gone: `robot_1`
28/48, first-listed 20/48, correct 18/48.

Verdicts:

| Rule | Verdict |
|---|---|
| Scene use | **not supported** (combinations 1/24, 8/24, 15/24, 22/24) |
| Label bias | **not supported by the rule**: P(`robot_1`) 0.27 in `A_grey` and 0.15 in `B_grey`; the `robot_2` threshold (at most 0.25 in both) is missed in `A_grey` by 0.02. Descriptively, `robot_2` is chosen 76/96 times |
| Slot bias | not supported (P(first-listed) 0.06 under `id_asc`, 0.65 under `id_desc`) |
| Real-frame secondary | fails (6/12, 5/12, 1/12, 6/12) |
| Image use | **not assessable** (`C_real_notext` and `D_grey_notext` cut; 1 run each) |

Scene-level table: `analysis.txt`, "Scene level, anthropic".

### Gemini ER-2 (`gemini-robotics-er-2-preview`, 54 runs)

| Cell | Runs | Correct | Wrong | No yielder (`reverse`) | Error |
|---|---|---|---|---|---|
| `A_grey` | 25 | 2 | 0 | 23 | 0 |
| `B_grey` | 25 | 0 | 1 | 23 | 1 (provider stop) |
| `A_real` (pilot) | 2 | 0 | 0 | 2 | 0 |
| `C_real_notext` (pilot) | 1 | 0 | 0 | 1 | 0 |
| `D_grey_notext` (pilot) | 1 | 0 | 0 | 1 | 0 |

- The grey-pair combinations hold 12, 12, 12 and 14 runs instead of 24 each: 2/12,
  0/12, 0/12 and 0/14 correct.
- All 3 named yielders carry `robot_1` and all came under `id_asc`, so label and slot
  cannot be told apart.
- Every answer came on attempt 1. Mean cost per run $0.0038 (1,965 input tokens, 135
  output tokens, 253 thought tokens).

Verdicts:

| Rule | Verdict |
|---|---|
| Scene use | **not assessable**: `A_grey` and `B_grey` were stopped by the provider at 25 of 48 runs each (design: a rule is not assessable if a cell it needs stopped). Descriptively, "label right, slot right" is 2/12, so even if all 12 missing runs were correct it would reach 14/24, below 18 |
| Label bias | **not assessable** (provider stop). `analysis.txt` prints the mechanical output, "SUPPORTED toward robot_1", which rests on 2 + 1 named yielders, all under `id_asc`, where label and slot coincide |
| Slot bias | **not assessable** (provider stop; no named yielder under `id_desc`) |
| Real-frame secondary | not assessable (2 runs) |
| Image use | not assessable (1 run each in C and D) |

---

## Sonnet's Refusal Rate Under the New Ending

| Stratum | Runs | Attempt-1 refusals | Refused attempts | Runs with a decision | Spend per run |
|---|---|---|---|---|---|
| v1 ending (swapped-ID replay) | 64 | 44 | 176 of 196 | 20 | $0.020 |
| JSON-only ending (this stratum) | 146 | 0 | 0 of 146 | 146 | $0.0077 |

This replicates the inspection's finding at n = 146: the `<think>` answer-format block
is what Sonnet refuses.

---

## Answer-Format Side by Side (Not Pooled)

These are the same scenes, orders and replicates, a few hours apart. The difference
mixes the answer format, the loss of the reasoning step, and provider drift.

| Model | Cell | Stratum | Runs | Correct | Named a yielder | `robot_1` / named | First-listed / named | `reverse` |
|---|---|---|---|---|---|---|---|---|
| ER-2 | `A_grey` | v1 | 48 | 2 | 4 | 4/4 | 3/4 | 44 |
| ER-2 | `A_grey` | JSON-only | 25 | 2 | 2 | 2/2 | 2/2 | 23 |
| ER-2 | `B_grey` | v1 | 48 | 2 | 4 | 4/4 | 4/4 | 44 |
| ER-2 | `B_grey` | JSON-only | 25 (1 error) | 0 | 1 | 1/1 | 1/1 | 23 |
| ER-2 | `A_real` | v1 | 48 | 5 | 7 | 5/7 | 4/7 | 41 |
| ER-2 | `A_real` | JSON-only | 2 | 0 | 0 | - | - | 2 |
| Sonnet | `A_real` | v1 | 48 (30 refused) | 10 | 18 | 12/18 | 9/18 | 0 |
| Sonnet | `A_real` | JSON-only | 48 | 18 | 48 | 28/48 | 20/48 | 0 |
| Sonnet | `A_grey` / `B_grey` | v1 | 4 / 4 (pilot) | 0 / 0 | 1 / 0 | 0/1 / - | 0/1 / - | 0 |
| Sonnet | `A_grey` / `B_grey` | JSON-only | 48 / 48 | 19 / 27 | 48 / 48 | 13/48 / 7/48 | 17/48 / 17/48 | 0 |

- **ER-2.** No visible answer-format effect on its main habit. It rarely names a
  yielder under either ending (grey pair: 8/96 in v1, 3/50 here) and otherwise
  answers `reverse`. The JSON-only cells beyond the grey pair have 1-2 runs.
- **gpt-4o.** Not run; no comparison.
- **Sonnet.** v1 `A_real` decisions are the 18 runs Sonnet did not refuse, a selected
  subset, so the two `A_real` rows are not comparable as rates. The full table is in
  `analysis.txt`.

---

## Cost Ledger

| Provider | Paid calls | Spend |
|---|---|---|
| Google (ER-2) | 56: probe, 54 runs (one returned the cap 429, unbilled), live check | $0.2131 |
| OpenAI (gpt-4o) | 1 probe (HTTP 429, unbilled) | $0.0000 |
| Anthropic (Sonnet 5.5) | 148: probe, 146 runs, live check | $1.1379 |
| **Total** | | **$1.3510** of the $5.00 cap |

The only failed call was the Gemini spend-cap 429. It is flagged `transient_retry`
in its attempt row and stopped the provider, so no retry followed. The ledger is
`ledger.jsonl` (running totals per row).

---

## Surprises

- Sonnet's grey-image prior is toward the label `robot_2`. gpt-4o's v1-stratum prior
  was toward the first-listed slot, and ER-2's few named yielders are `robot_1`. The
  three models have three different non-scene defaults.
- The annotated frame removes Sonnet's `robot_2` preference (28/48 `robot_1`) but does
  not make it correct (18/48).
- The gate's main risk was gpt-4o refusing annotated frames, but gpt-4o never ran.
  Both cuts are account limits on the provider side.

---

## Limitations

- 12 scenes, one family (head-on asymmetric), one seed (42), two robots, first decision
  only, no execution. The pairs of replicates are not independent: outcomes are close
  to fixed per exact request.
- Only Sonnet has a complete tier 1 and tier 2. ER-2 has about half of tier 1 and pilot
  runs elsewhere. gpt-4o has nothing.
- This condition has no reasoning step. A result here does not show what any model
  does when it reasons first, and the v1 comparison confounds that with the ending.
- The comparison with v1 spans a few hours of provider drift. Served-model strings did
  not change.
- The live-prompt check is n = 1 per provider, on one stimulus.
- The `reasoning_extraction` no-retry option did not fire, so its live effect is
  unobserved.

---

## What the Thesis May and May Not Say

The thesis may say that Sonnet 5.5's refusals on the head-on prompt came from the
`<think>` answer-format block. With a JSON-only ending, applied identically to every
model, it answered all 146 runs. ER-2 and Sonnet both accepted that shared prompt and
the current v3.4 prompt. Under that ending Sonnet does not pick the head-on yielder from
the scene (46/96 on the grey pair), and its grey-image choices follow the label
`robot_2` (76/96), short of the pre-registered label-bias threshold. The thesis may not
say that the shared prompt works for every provider, because gpt-4o was not tested. It
may not draw any conclusion about image use for Sonnet or ER-2 from this stratum
(cells cut). It may not claim an answer-format effect on yielder choice for ER-2 or
gpt-4o. It may not pool these rows with the v1 stratum or the live runs.

---

## Reproducibility

| Item | Location (branch `exp/head-on-json-only-replay`) |
|---|---|
| Design | `docs/superpowers/specs/2026-11-14-head-on-json-only-replay-design.md` (commit `071257a`) |
| Reasoner option | `reasoning/vlm/models.py:1012`, `reasoning/vlm/reasoner.py:514-538` (commit `b72891e`); tests `tests/unit/test_reasoner_final_refusal.py` |
| Runner and tests | `scripts/replay_json_only.py`, `tests/unit/test_replay_json_only.py` (commit `62c40c7`) |
| Analysis | `scripts/analyze_swapped_ids.py --out-dir <data dir>` plus `scripts/analyze_json_only.py`; output `analysis.txt` |
| Data | `data/experiments/2026-11-14-head-on-json-only-replay/`: `calls.jsonl` (200 rows; every attempt's raw text and sent hashes; no images, no keys), `ledger.jsonl`, `probes.jsonl`, `live_v34_check.jsonl`, `prompt_manifest.json`, `run_order.json`, the grey image; `sonnet_inspection/` (`docs/reports/2026-11-14-sonnet-refusal-inspection.md`) |

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-jsononly
PY=/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/.venv/bin/python
$PY scripts/replay_json_only.py --runs-dir <main checkout>/data/logs/vm_runs --phase check
$PY scripts/analyze_swapped_ids.py --out-dir data/experiments/2026-11-14-head-on-json-only-replay
$PY scripts/analyze_json_only.py
```

The paid phases (`probe`, `pilot`, `live`, `batch`) need provider keys in the
environment and resume by skipping recorded keys.

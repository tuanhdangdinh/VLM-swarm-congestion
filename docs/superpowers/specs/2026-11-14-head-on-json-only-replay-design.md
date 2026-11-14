# Head-On JSON-Only Replay - Pre-Registered Design

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: design frozen before the first paid call. It repeats the swapped-ID replay (`docs/superpowers/specs/2026-11-14-head-on-swapped-id-replay-design.md`, Rev 3) with a JSON-only answer ending for all three models. It also adds the owner's prompt-compatibility gate and the opt-in `reasoning_extraction` no-retry option.

---

## Question

The swapped-ID replay sent the stored v1 prompt, which ends with a `<think>`
answer-format block. Claude Sonnet 5.5 refused that block (`reasoning_extraction`), so
its rules were "not assessable"
(`docs/reports/2026-11-14-sonnet-refusal-inspection.md`). This replay asks the same
question with one change: the block is replaced by the JSON-only line, for every model.

1. On the 12 head-on standoff scenes, under a JSON-only ending, does any of ER-2,
   gpt-4o or Sonnet 5.5 pick the oracle-correct yielder from the scene, rather than
   from the label `robot_1` or the first-listed slot?
2. Owner addition (2026-11-14, verbatim: "make sure that prompt can you for every
   provider", read as "make sure the prompt can be used for every provider"): is one
   shared prompt text accepted by all three providers? Does the current production
   prompt (v3.4) answer the same question?

**Evidence grade:** a small designed offline experiment. 12 scenes from one family at
seed 42, two robots, first decision only, no execution, one stimulus seed. Counts
only; no p-values and no intervals. This is a new stratum: it is never pooled with the
v1-prompt stratum run earlier today, with the September replays or with live runs.

**Authorisation:** owner, 2026-11-14 (verbatim): "I approve options 2 and 3." Option 2
is this stratum; option 3 is the no-retry option below. Hard cap $5.00 in total and
$2.00 per model, counting every paid call of this job (probes, pilot, live check,
diagnostics, batch). No VM, no cloud commands, no push.

---

## Prompt Condition

- **Base text.** For each stimulus, cell and order, the user prompt is the stored v1
  prompt exactly as the swapped-ID replay rendered it. It is rendered by
  `build_reasoner_request` → `build_prompt_payload` (`prompt_version=1`), with labels
  swapped in the scene for `B_grey` and the obstacle block off for C and D.
- **The one change.** The rendered block, from `Answer using the following format:`
  through `...write ONLY the final JSON object, with no surrounding text or markdown.`
  (`reasoning/vlm/prompt_v1.py:91-98`), is replaced by:

  ```text
  Write ONLY the final JSON object, with no surrounding text or markdown.
  ```

  This is October's diagnostic wording, and it is byte-identical to the closing line
  of the current builder (v3.4, `reasoning/vlm/prompt_builder.py:140`). After the
  change, the last two lines of the prompt are `...must be non-empty.` and the
  JSON-only line, separated by one blank line, exactly as in v3.4.
- **Where it is applied.** In the runner's prompt-condition layer
  (`PromptConditionProxy` in `scripts/replay_json_only.py`). The layer sits between
  the production `Reasoner` and the backend, and the same code runs for every model.
  It is not keyed on the backend, and no backend file changes. It rewrites only that
  block on every attempt. A re-ask suffix after the block and the neutral-image
  fallback pass through unchanged (unit-tested).
- **No reasoning step.** Unlike the v1 condition, this prompt asks for no visible
  reasoning before the JSON. The v1 schema has no `reasoning` field.
- **System prompt and image.** Unchanged: `You are a helpful assistant.`; the annotated
  frame or the grey 1280 x 960 PNG (SHA-256 `26044d57…`, byte-identical to the
  swapped-ID replay's).

### Prompt manifest

`data/experiments/2026-11-14-head-on-json-only-replay/prompt_manifest.json`, made
offline by `--phase check` before any paid call. It has 72 entries: 12 scenes x 2
orders x (original IDs with text, swapped IDs with text, original IDs without text).
Each entry records the v1 user SHA-256, the JSON-only user SHA-256, the system SHA-256
and the removed-block SHA-256. For every entry it checks
`v1 == head + block` and `sent == head + JSON_ONLY_LINE` with nothing after the block,
so the diff is exactly the block. All 72 pass, and all 72 JSON-only texts are distinct.
The grey image and the 12 frames are recorded by SHA-256. The unit test
`test_manifest_diff_is_block_only_for_all_12_stimuli` repeats the check.

---

## One Prompt for Every Provider (Owner Gate 1)

- **One text per stimulus.** Each attempt row records `sent_user_sha256`,
  `sent_system_sha256` and `sent_image_sha256`, hashed from the payload actually
  handed to the backend. The analysis checks that for every (cell, scene, order,
  replicate), attempt 1's three hashes are identical across ER-2, gpt-4o and Sonnet
  and equal the manifest. Any mismatch is reported.
- **No backend appends text to the prompt.** Each adapter places the same
  `system_prompt`, `user_prompt` and image bytes in its own wire format:

| Backend (file) | System text | User text and image | Other fields sent for this arm |
|---|---|---|---|
| `GeminiBackend` (`gemini_backend.py:212-228`) | `system_instruction` (215) | `input`: text part first, then image part (216) | `generation_config`: `thinking_level: low`, `max_output_tokens` (207-208). `response_format` (220) only with `force_schema`, which is `false` for `gemini`. `seed` and `store` unset |
| `OpenAIBackend` (`openai_backend.py:96-121, 222-240`) | `messages[0]` role `system` (238) | `messages[1]`: text part first (229), then `image_url` with `detail: "high"` (234) | `temperature: 0.0`, `top_p` (99-100), `max_tokens`, `stream: false`. No `response_format`, `reasoning_effort` or `thinking` for `openai` |
| `AnthropicBackend` (`anthropic_backend.py:93-104, 160-176`) | top-level `system` (95) | `messages[0]`: image block first (165-173), then text block (175) | `max_tokens`, `thinking: {type: between_tools}` (102). No `output_config` (no `effort` set). No sampling fields |

  - The differences are transport only: where the system text goes, the order of the
    image and text parts, OpenAI's `detail: "high"`, each provider's thinking control,
    and the image encoding (base64 PNG in all three). No adapter has JSON-mode or
    `json_guidance` text, and none prepends or appends prompt text.
- **Text-pattern refusal detection** (`reasoner.py` `is_refusal`) and the parser are
  shared code, applied identically.

---

## Retry Policy and the No-Retry Option (Option 3)

- Each model runs its shipped `config/models.yaml` reasoner config. ER-2: 2 attempts,
  re-ask, no image fallback, `max_tokens` 2048. gpt-4o: 4 attempts, re-ask,
  `temperature` 0.0, grey fallback after 2. Sonnet: 4 attempts, re-ask, grey fallback
  after 2.
- **Added for this experiment only:**
  `final_refusal_categories = ("reasoning_extraction",)`. This is a new, default-off
  `ReasonerConfig` field (commit `b72891e`, `reasoning/vlm/models.py:1012`, logic
  `reasoning/vlm/reasoner.py:514-538`). A provider refusal carrying a listed category
  ends the run on that attempt as a refusal result: no re-ask, no image fallback,
  `error_type = "FinalRefusal"`, and the category and reason are kept in diagnostics.
  Other refusals, uncategorised refusals, text-pattern refusals and parse failures
  follow the existing policy.
  - It applies to all three models identically. In practice only Anthropic returns
    this category. gpt-4o's structured refusals carry no category, and ER-2 returned
    none in the swapped-ID replay.
  - It changes October's retry-parity ruling only while enabled. No shipped config
    enables it (pinned by `test_final_refusal_categories_absent_from_every_shipped_config`).
  - It is not lossless: in October, 4 decisions were recovered on later attempts.
- The effective config, with the option and `answer_format: json_only`, the served
  model string and the commit are recorded on every row.

---

## Stimuli and Cells

The 12 SHA-verified standoff stimuli of the swapped-ID replay (its "Stimuli" table), both
listing orders, 2 replicates, 48 runs per cell per model. Cells and their scoring are
unchanged from that design:

| Priority | Cell | IDs | Image | Obstacle text |
|---|---|---|---|---|
| tier 1 | `A_grey` | original | grey | on |
| tier 1 | `B_grey` | swapped | grey | on |
| tier 2 | `A_real` | original | annotated frame | on |
| tier 3 | `C_real_notext` | original | annotated frame | off |
| tier 3 | `D_grey_notext` | original | grey | off |

Up to 240 runs per model, 720 in total. Physical-robot scoring, the outcome classes
(`correct`, `wrong`, `no_yielder`, `refusal`, `parse_failure`, `error`), the
all-runs denominator and the attempt-1 secondary outcome are as in the swapped-ID
design.

---

## Execution Order

1. **Offline check** (`--phase check`): stimuli SHA-verified, manifest written, run
   order written to `run_order.json`. No network.
2. **Probe** (`--phase probe`): one minimal call per provider (ER-2, gpt-4o, Sonnet;
   short text and a 64 x 64 grey PNG). On HTTP 401, 402, 403, or 429 with a quota
   marker, that provider is skipped and reported; no retry, no key or model
   substitution.
3. **Compatibility pilot** (`--phase pilot`, owner gate 2): 8 runs per provider, all
   on replicate 1, using the west scene `53264de9` and the east scene `61119197`:

| # | Cell | Scene (side) | Order |
|---|---|---|---|
| 1 | `A_grey` | `53264de9` (west) | `id_asc` |
| 2 | `A_grey` | `61119197` (east) | `id_desc` |
| 3 | `B_grey` | `53264de9` (west) | `id_desc` |
| 4 | `B_grey` | `61119197` (east) | `id_asc` |
| 5 | `A_real` | `53264de9` (west) | `id_desc` |
| 6 | `A_real` | `61119197` (east) | `id_asc` |
| 7 | `C_real_notext` | `53264de9` (west) | `id_asc` |
| 8 | `D_grey_notext` | `61119197` (east) | `id_desc` |

   That is 4 west, 4 east, 4 per order and every cell. Pilot rows count toward their
   cell's 48 as long as the wording is not revised.
4. **Live-prompt check** (`--phase live`, owner gate 3): one `Reasoner.run` per provider
   on the current production prompt, rendered by the current builder at
   `prompt_version=3` (v3.4) with no transform. Stimulus `53264de9`, `id_asc`, annotated
   frame, obstacle text on, the same retry config. Rows go to `live_v34_check.jsonl`,
   outside every table; spend goes to the ledger.
5. **Batch** (`--phase batch`), only for providers that passed the pilot. Tier 1 runs
   for ER-2, then gpt-4o, then Sonnet; then tier 2 in the same model order; then
   tier 3. Within a model and tier the remaining runs are interleaved in a seeded
   order: `random.Random(f"20261114|{backend_id}|tier{n}").shuffle`, recorded in
   `run_order.json` (92, 46 and 94 runs per model).
6. All phases are resumable: a recorded key is skipped.

---

## Compatibility-Pilot Pass Criteria (Fixed in Advance)

A provider passes only if all of these hold over its 8 pilot runs:

- **No provider-level refusal or content-filter stop on any attempt.** A provider-level
  refusal is `BackendResponse.refusal` (Anthropic `stop_reason: refusal`, OpenAI
  `message.refusal` or a refusal finish reason, Gemini's refusal channel). A
  content-filter stop is a finish reason of `content_filter`, `safety`,
  `prohibited_content`, `blocklist`, `spii` or `refusal`.
- **At least 7 of 8 runs end with a valid decision on attempt 1**, parsed and validated
  by the production parser.
- **No run uses the grey-image fallback.**
- **No attempt needs a retry for format** (a parse or validation failure that was not a
  refusal).

The one run allowed to miss attempt 1 can therefore only be a transport error or a
text-pattern refusal.

**If a provider fails:**

- Stop. No batch call to any provider, and the prompt is not adjusted for that provider
  alone.
- Diagnose what in the shared prompt it rejects, offline plus at most 6 extra paid calls
  (`diagnostics.jsonl`, outside every table).
- Then either propose ONE revised shared wording, written as a dated amendment and
  committed before any further call, and re-pilot all three providers with it; or
  report that no single wording was found. At most two shared-wording revisions; after
  that, stop and report. Under a revised wording the old pilot rows stay in
  `calls.jsonl` with `wording_rev` 0 and are excluded from every table.
- **Pre-stated case: gpt-4o refusing the annotated frame.** gpt-4o refused the annotated
  frame on attempt 1 in 11/96 runs of the v1 stratum and never on grey (144 runs). Its
  pilot has 3 annotated-frame runs. Suppose its only failures are refusals on
  annotated-frame runs. The diagnosis then re-sends each refused run's exact text with
  the grey image (within the 6 calls). If every re-send answers, the refusal is
  attributed to the image channel, not to the shared wording: a wording revision
  cannot address it. The result is recorded as "image-channel failure, shared wording
  accepted", and the batch is not started without a dated amendment that states this
  and is committed first.

---

## Stop and Cap Rules

- **Quota or credit during a phase.** HTTP 401 or 403, HTTP 402, or HTTP 429 with a
  quota, billing, spend-cap or credit marker: that provider stops at once and is
  reported. Pacing is at least 1.0 s between calls. Each run allows at most 2
  transient retries (429, 5xx, timeout, connection), counted in the ledger. A plain
  429 that persists past that budget stops the provider.
- **Per-run worst case.** Before every run:
  `max_attempts x (prompt bound x input rate + max_tokens x output rate)`. The prompt
  bound is 3,000 tokens or 1.2 x the largest prompt seen for that model. The run is not
  started if model spend + worst case > $2.00, or total spend + worst case > $5.00.
- **Tier rule.** A tier starts for a model only if all its remaining runs fit:
  `remaining x mean cost per run (this model, this stratum so far) x 1.15 + one
  worst-case run` must not exceed either cap after current spend. Otherwise the tier
  is not started for that model; it is cut from the bottom and reported. A tier
  stopped by the per-run guard partway through is reported as partial.
- **Cell rule (all models).** If more than 4 of a cell's first 8 runs, in execution
  order and counting pilot rows, end with no decision or use the fallback, that
  model's cell stops.
- **Sonnet rule.** If more than 4 of the first 8 Sonnet runs of any cell are refused on
  attempt 1, Sonnet stops entirely and is reported.
- **Exclusions.** None after the run. Every run is in `calls.jsonl` and in the counts.

### Rates and cost estimate

Rates per MTok (input / output) as in the swapped-ID design: ER-2 $1.00 / $5.00, thought
tokens charged as output; gpt-4o $2.50 / $10.00; Sonnet 5.5 $2.00 / $10.00. An attempt
with no recorded usage is charged one worst-case attempt unless it was an HTTP status
error.

| Item | Basis (v1-stratum ledger and Sonnet diagnostic, 2026-11-14) | Expected |
|---|---|---|
| ER-2, 240 runs | $0.0040 per run (1.0 call per run) | about $0.97 |
| gpt-4o, 240 runs | $0.0061-0.0069 per run; the JSON-only output is shorter | about $1.40-1.55 |
| Sonnet tiers 1-2, 144 runs | about $0.0076 per answered run (2,917 in, about 180 out); $0.006 per final refusal | about $1.10 |
| Sonnet tier 3, 96 runs | as above | about $0.73 but **expected to be cut** by the tier rule (about $1.10 + 94 x $0.0076 x 1.15 + $0.11 > $2.00) |
| Probes and live check | 3 tiny calls + 3 v3.4 calls (about 1.7 x the v1 prompt length) | about $0.04 |

Expected total about $3.5-3.7, under the $5.00 cap. Expected cut: Sonnet's tier 3
(`C_real_notext`, `D_grey_notext`), so Sonnet's image-use rule would be not assessable.

---

## Decision Rules (Stated in Advance)

The rules are those of the swapped-ID design, unchanged, applied to this stratum alone:

- **Scene use is supported** for a model only if, in each of the four label x slot
  combinations of the grey pair (`A_grey`, `B_grey`), it names the physically correct
  robot in at least 18 of 24 runs **and** in both replicates in at least 9 of the 12
  scenes. This includes the combination where label and slot both point to the wrong
  robot. Otherwise it is not supported.
- **Label bias** toward `robot_1` (or `robot_2`) is supported if P(chosen label =
  `robot_1`) is at least 0.75 (or at most 0.25) among yield-naming runs in **both**
  `A_grey` and `B_grey`.
- **Slot bias** is supported if P(chosen = first-listed) is at least 0.75 among
  yield-naming runs under **both** orders in the grey pair.
- **Real frame (secondary).** The four-combination table for `A_real` (12 runs and 6
  scenes per combination; thresholds 9/12 runs and 4/6 scenes with 2/2). Label and side
  are confounded there.
- **Image use** is supported only if both of these hold:
  - in `C_real_notext`, in each side x order cell, at least 9 of 12 runs are correct,
    with both replicates correct in at least 4 of 6 scenes;
  - P(correct) in C exceeds P(correct) in D by at least 0.25 (absolute; 48 runs each).
- **Not assessable.** A rule is not assessable for a model if any cell it needs stopped,
  was cut, or has fewer than 20 runs with a decision.
- **ER-2's `reverse` without a yielder.** `reverse` names nobody. It is reported as
  `no_yielder`, counted in the denominator and never dropped. The strategy census is
  reported per cell.

### Added in advance for this stratum

- **Answer-format effect (ER-2 and gpt-4o).** For each cell present in both strata, the
  headline counts of the v1-prompt stratum (swapped-ID replay, run earlier today on the
  same scenes, orders and replicates) are reported side by side with this stratum.
  The headline counts are: the outcome census, P(correct), the number of runs naming a
  yielder, P(label `robot_1`) and P(first-listed) among those, and the strategy census.
  They are never pooled and no test is run. The difference is confounded with a few
  hours of provider drift and with the loss of the reasoning step (v1 asked for a
  `<think>` block; this condition asks for none). It is labelled the effect of the
  answer-format condition, not of the wording alone.
- **Sonnet.** Its attempt-1 refusal rate per cell under the JSON-only ending, beside the
  v1 stratum's (44/64 runs). Sonnet's v1 stratum had decisions only in `A_real` (18 of
  48), so the side-by-side is limited to that.
- **Live-prompt check.** Reported per provider: answered or refused, attempts, category,
  served model. With n = 1 per provider it shows only whether today's live prompt is
  accepted at all. Its body differs from the JSON-only v1 prompt: v3.4 adds a
  `reasoning` field, `blocker_kind`, `crossing_order` and `proposed_plan` to the
  schema, its own guidance lines and the list-order line. Only the closing line is
  shared.

---

## Outputs

- `data/experiments/2026-11-14-head-on-json-only-replay/`, tracked like the earlier
  experiments:
  - `calls.jsonl` holds one row per run: every attempt's raw text, refusal flags and
    category, tokens, latency, error, and the sent user, system and image SHA-256;
    plus the effective config, served model and commit. No base64 and no key material.
  - `ledger.jsonl`, `probes.jsonl`, `live_v34_check.jsonl`, `diagnostics.jsonl` (if
    any), `prompt_manifest.json`, `run_order.json`, the grey image and `analysis.txt`.
- `scripts/replay_json_only.py` (runner), unit tests `tests/unit/test_replay_json_only.py`
  and `tests/unit/test_reasoner_final_refusal.py`. Analysis: `scripts/analyze_swapped_ids.py
  --out-dir <this dir>` for the pre-registered tables, plus a short comparison script for
  the side-by-side and the identity check.
- Report: `docs/reports/2026-11-14-head-on-json-only-replay-results.md`.

---

## Amendments

None yet. Any change is a dated amendment committed before the calls it affects.

# Sonnet 5.5 Refusal Inspection

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: the session's Sonnet 5.5 refusal inspection (scratch report and raw call ledger), committed as a report with its counts re-derived from the ledgers.

---

## Summary

In the swapped-ID replay (`docs/reports/2026-11-14-head-on-swapped-id-replay-results.md`)
Claude Sonnet 5.5 refused most calls. This report records why.

- **What the API returns.** HTTP 200, billed, `stop_reason: "refusal"`,
  `stop_details.category: "reasoning_extraction"`. The explanation text says the request
  "seems to violate Anthropic's Terms of Service restrictions on reverse engineering or
  duplicating model outputs". `AnthropicBackend` copies the category through
  (`reasoning/vlm/anthropic_backend.py:145-154, 203-209`).
- **Trigger.** The v1 prompt's answer-format block
  (`reasoning/vlm/prompt_v1.py:91-98`): "Answer using the following format: `<think>` …
  `</think>` Immediately after the `</think>` tag, write ONLY the final JSON object …".
  The replay sent it because it replays stored v1 artifacts. The current builder (v3.4)
  already removed the block (`reasoning/vlm/prompt_builder.py:54-64`).
- **Why retries did not help.** Every retry carries the same block. Attempt 1 was refused
  in 44 of 64 runs, and attempts 2-4 were refused in 132 of 132.
- **gpt-4o is different.** Its refusals in the same experiment need the annotated frame
  (0 refusals in 144 grey-image runs, 11 attempt-1 refusals in 96 annotated-frame runs),
  so they have another trigger.

**Evidence grade:** a diagnostic, not an experiment. On one cell, 11 paid calls, with
2-3 calls per variant. The outcome is close to fixed for one exact request, so repeats
add little. The finding is firm because it replicates three times: the October roster
diagnostic (block present refused 3/3, removed answered 3/3, three scenes, real frames),
the v3.4 sanity replay (3/3 answered), and these calls.

---

## Variant Test (2026-11-14)

Cell: scene `53264de9`, `id_asc`, obstacle text on, grey 1280 x 960 image, shipped
`AnthropicBackend` and `anthropic` config (`thinking: between_tools`, `max_tokens`
2048). Re-derived from `sonnet_inspection/ledger.jsonl`: 11 calls, $0.0832.

| Variant | Thinking | Calls | Result | Input / output tokens per call |
|---|---|---|---|---|
| Shipped v1 prompt | `between_tools` | 2 | refused 2/2 (`reasoning_extraction`) | 3,019 / 0 |
| Block replaced by "Write ONLY the final JSON object, with no surrounding text or markdown." | `between_tools` | 3 | answered 3/3, JSON only | 2,917 / 176-181 |
| Shipped v1 prompt | adaptive | 2 | refused 2/2 (`reasoning_extraction`) | 3,020 / 0 |
| Block replaced by the JSON-only line | adaptive | 2 | answered 2/2 | 2,918 / 219-228 |
| Block replaced by "First explain, in two or three plain sentences, the evidence for your decision. Then write the final JSON object, with no markdown." | `between_tools` | 2 | answered 2/2 (explanation then JSON) | 2,931 / 406-432 |

- The scratch report says the adaptive JSON-only answers used 0 thinking tokens. The
  ledger rows hold no `thinking_tokens` field and only `text` content blocks, which is
  consistent with that but does not show it directly (copied, not re-derived).
- In the two tagless-explanation answers, Sonnet described the image as a uniform grey
  frame. The image was grey by design.

---

## Ruled Out as Sufficient

Copied from the scratch report; the variant table above supports the first two:

- the image (the refusal occurs with a grey image);
- the system prompt (unchanged across variants);
- the robot-control or safety wording, the required JSON format and the prompt length
  (all unchanged between the refused and the answered variant);
- harness or transport (requests go through the shipped backend; `wire_request_shape.json`
  shows the body: image block, then text block, `system` field, `thinking`, `max_tokens`).

---

## Recorded Data From the Swapped-ID Replay

Re-derived from `data/experiments/2026-11-14-head-on-swapped-id-replay/calls.jsonl`
(Sonnet rows) and `ledger.jsonl`:

| Quantity | Value |
|---|---|
| Sonnet runs | 64 (48 `A_real`, 4 pilot runs in each of the other four cells) |
| Attempts (network calls) in those runs | 196 |
| Attempt 1 refused | 44 / 64 |
| Attempts 2-4 refused | 132 / 132 |
| Runs with a decision | 20 (11 correct, 9 wrong); 44 terminal refusals |
| Answered outputs containing a `<think>` block | 20 / 20 |
| Spend of the 64 runs | $1.2937, of which refused retries (attempts 2-4) $0.8054 |
| Ledger total for Sonnet | $1.3121 over 200 network calls (196 run attempts, 1 probe, 3 diagnostic calls) |
| Cells with two replicates whose attempt-1 refusal differed between replicates | 2 of 24 |

- The scratch report gave "about $0.79 of $1.31" for refused retries. The re-derived
  figure is $0.81 of the $1.29 spent on runs. The difference comes from what the base
  includes (with or without the probe and the diagnostic calls).
- The scratch report also says that listing order and image both shift the outcome and
  that the deciding feature was not identified (copied, not re-derived).

---

## gpt-4o Has a Different Trigger

Re-derived from the same `calls.jsonl` (gpt-4o, same v1 prompt, block present):

| Cell | Runs | Attempt-1 refusals | Refused attempts |
|---|---|---|---|
| `A_real` (annotated frame) | 48 | 5 | 8 |
| `C_real_notext` (annotated frame) | 48 | 6 | 7 |
| `A_grey`, `B_grey`, `D_grey_notext` (grey) | 144 | 0 | 0 |

The September frame replay found 0/120 grey against 22/60 real frame
(`docs/reports/2026-09-25-frame-replay.md`, copied). gpt-4o's refusals need the real
frame; Sonnet's are driven by the text. gpt-4o reports them through
`message.refusal`, with no category.

---

## Options Put to the Owner

Copied from the scratch report:

- A. JSON-only ending for Sonnet only: a per-model prompt fork, forbidden by October
  owner ruling 3 (`docs/reports/2026-10-06-roster-validation.md`); it also confounds the
  model with the reasoning step.
- B. JSON-only (v3.4-style) ending for all three models as a new pre-registered
  stratum (about $3; not poolable with the v1 results). Recommended.
- C. A tagless "explain briefly, then JSON" ending for all models: keeps a visible
  reasoning step; tested only 2 times on Sonnet.
- D. API thinking: does not fix the shipped prompt (refused 2/2).
- G. Leave Sonnet out ("not assessable").
- Hygiene: treat `reasoning_extraction` as final on attempt 1, which saves most of the
  refusal spend but changes the retry-parity ruling (owner decision).

Owner decision, 2026-11-14 (verbatim): "I approve options 2 and 3." These are B and the
hygiene item. They are implemented in
`docs/superpowers/specs/2026-11-14-head-on-json-only-replay-design.md`.

---

## Evidence Files

`data/experiments/2026-11-14-head-on-json-only-replay/sonnet_inspection/`, copied from
the session scratch directory and checked for key material first (none: the scripts
read the key from the environment by name only):

| File | Content |
|---|---|
| `ledger.jsonl` | the 11 diagnostic calls: variant, stop reason and details, usage, served model, provider request id, text |
| `probe.py.txt` | the diagnostic script (renamed so it is not linted or run; paths are the session's) |
| `render.py.txt`, `scene_diff.py.txt` | offline rendering of the cell and the 12-scene prompt diff |
| `system_prompt.txt`, `user_prompt_53264de9_id_asc.txt` | the exact prompt texts |
| `wire_request_shape.json` | the request body shape, base64 omitted |

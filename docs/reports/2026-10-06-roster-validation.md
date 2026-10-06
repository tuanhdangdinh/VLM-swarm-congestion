# Roster Validation: Sonnet 5.5, DeepSeek Flash, and the Dynamics Battery on Four New Arms

**Prepared:** 2026-10-06

**Revision history:**

- Initial draft: rulings 1 and 2 applied, Sonnet 5.5 validated to the full standard, DeepSeek to the pilot standard, battery v2 (main, 59 items) run on Qwen, Sonnet and DeepSeek, gpt-5.1 aborted on exhausted OpenAI credits; consolidated six-backend table.

---

## Summary

The contract is the main checkout's `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`: the "Model-wiring RESULTS + RULINGS (2026-10-06)" block (rulings 1–4) and the validation standard in the "Model-wiring ruling" block. The base context is `docs/reports/2026-10-06-model-wiring.md`. Branch `feat/v2-roster-validation`, cut from `feat/prereg-v2-composite` at `4426ea0`.

**Headlines:**

- **Sonnet 5.5 refuses the deployed stage-1 prompt.**
  - 91/96 live attempts (94.8%) and 21/26 decisions (80.8%, terminal after 4 attempts) were refused.
  - Every refusal is HTTP 200 `stop_reason: "refusal"`, category `reasoning_extraction`.
  - The same model answered 119/119 probe calls with 0 refusals.
  - The grey-image fallback does not help: 42/45 grey-image attempts were also refused. The refusal is locked to the prompt text, not the frame, which is the opposite of gpt-4o's frame-locked profile.
  - A diagnostic replay, n = 3, labelled diagnostic and outside every table, isolates the trigger: the v3.3 prompt's Cosmos-style `<think> … </think>` answer-format block. The recorded prompt was refused 3/3; the same prompt without that block answered 3/3.
  - Anthropic's documentation names exactly this pattern as a `reasoning_extraction` trigger, and bills such refusals.
  - Ruling 3 forbids per-model prompt forks, so this is **STOP item 1**.
- **conflict_prediction, the only type that has separated backends:**
  - **DeepSeek Flash 19/20 [0.76, 0.99]**, the best ever recorded. GT-yes 10/10 and GT-no 9/10, with a "yes" rate of 11/20, so this is not an always-yes artifact.
  - **Sonnet 16/20** with the same false-alarm shape as ER-2: GT-no 6/10, "yes" rate 14/20.
  - **Qwen 15/20** with the opposite shape: GT-yes 5/10, GT-no 10/10, "yes" rate 5/20. It misses real conflicts.
  - All three sit above gpt-4o's chance-level 9/20, but every interval overlaps ER-2's 16/20.
  - **gpt-5.1 is unanswered:** its run aborted at item 28/59 on exhausted OpenAI credits (**STOP item 2**).
- **Probe battery v1:** Sonnet 60/60 and DeepSeek 60/60, joining ER-2 at ceiling. v1 still cannot rank backends.
- **Head-on, all resolved 2/2:**
  - **DeepSeek s42:** 146.5 s delay. It named the wrong yielder (robot_1 under `id_asc`), and the swap gate repaired it with 1 edit. 0 refusals and 0 transport errors.
  - **Sonnet s42:** 366.6 s delay. 14 terminally refused decisions came first. The first answered trigger, at sim 134 s, named robot_1 and was repaired.
  - **Sonnet s43:** 222.3 s delay. The trigger was answered on the grey-image attempt with a verbatim, correct plan, so it is a frame-free decision.
  - For reference: the other arms' resolved head-on episodes fall at 143.8–153.3 s; layer-2-off head-on is censored at ≥ 531 s.
- **Wiring verified live:**
  - Sonnet: `unsupported_sampling` recorded on every artifact; `thinking_tokens` 0 on every answered call; refusals classified as refusals, never as transport errors; parity config (4 attempts, grey fallback on attempt 3) active in the effective block.
  - DeepSeek: the served model is `deepseek-flash` on every call; image tokens are **738 per 1280×960 frame on all 119 probe calls**, within the ≤ 1024 budget.
- **Spend:** about **$1.54** in total (Sonnet about $1.49, of which about $0.76 is estimated refused-call and stage-2 billing). The $10 hard stop was never in play.

**STOP items for the owner:**

1. **Sonnet 5.5 cannot run the registered single prompt.**
   - The `<think>` block exists for Cosmos Reason 2, which is DEFERRED to v3, so no v2 arm needs it.
   - Removing it would be a global v3.4 re-pin that changes every arm's comparability. Ruling 3 forbids a Sonnet-only fork.
   - Anthropic's documentation also lists a `reasoning` JSON field (the v3 schema's first field) as a common trigger. At n = 1 its removal alone did not lift the refusal, but that is no evidence the field is safe.
   - Options as facts, not a recommendation:
     - keep Sonnet as a measured-refusal arm;
     - drop it;
     - re-pin the prompt globally.
2. **OpenAI credits are exhausted** (HTTP 429 `no credits remaining`, 14:38Z).
   - gpt-5.1's dynamics run stopped at 28/59, so its conflict_prediction is unanswered.
   - The same account carries the frozen gpt-4o pin, so **any gpt-4o collection is blocked too**.
   - Finishing gpt-5.1 costs about $0.05 after a top-up.
3. **The VM `.env` did not have the new keys.**
   - The brief said both `.env` files had them, but `/home/ubuntu/vgu-vlm-swarm/.env` (`/ws/.env`) had neither `ANTHROPIC_API_KEY` nor `DEEPSEEK_API_KEY`. Only the main checkout's local `.env` did.
   - I appended exactly those two lines from the local file over SSH stdin (never echoed, mode 600 kept) and presence-checked them inside `vgu_ros`. They stay there.
4. **DeepSeek is not at refusal-mitigation parity.** Ruling 1 covered Sonnet only; DeepSeek still has 2 attempts and no grey fallback. With 0 refusals observed this is moot here, but a refusal profile measured under it is not parity-comparable.
5. **Sonnet's episode cost is an estimate.** Refused decisions record no `token_usage` (the failed-result path drops it), and `reasoning_extraction` refusals are billed. Recording usage on refused attempts is a small follow-up that was not done (out of scope).

---

## PART 0: Rulings Applied

Commits on `feat/v2-roster-validation`:

- `e3f8dbd` — rulings 1 and 2.
- `66e4f44` — Anthropic `thinking_tokens` in per-call usage. This is the brief's "watch thinking-token billing" item; without it the usage breakdown was dropped.

| Ruling | Change | Pin test |
|---|---|---|
| 1: Sonnet parity | `anthropic.reasoner` gains `max_attempts: 4` and `image_fallback_after_attempts: 2`, plus a comment citing the ruling | `test_anthropic_arm_has_hosted_arm_parity_attempts_and_image_fallback` (against the gpt-4o pin's values) |
| 2: DeepSeek re-pin | `deepseek.model_id: deepseek-flash`. The comment now says the `-exp` id is retired, the budget is ≤ 1024 tokens per image, and the 384-token note is obsolete | `test_deepseek_arm_rides_the_openai_adapter_with_thinking_disabled` (updated), `test_deepseek_arm_is_not_pinned_to_the_retired_exp_id` |
| Usage | `AnthropicBackend._extract_usage` adds `thinking_tokens` from `usage.output_tokens_details` when reported | `test_anthropic_usage_records_thinking_tokens_when_reported` |

**Live model listings** (`GET /v1/models`, 2026-10-06 14:3xZ; `preflight/local_*_listmodels.txt`):

- **Anthropic:** 13 ids. `claude-sonnet-5-5` is listed first and is the only Sonnet 5.5 id, so there was no STOP.
- **DeepSeek:** exactly `["deepseek-flash", "deepseek-v4-pro"]`. The API reports `deepseek-flash` as the served `model` on every call (preflight, 119 probes, 5 episode calls). The legacy `-exp` name is absent from the listing.

**Full suite:** 63 failed / 5,187 passed / 153 skipped / 3 errors, against 63 / 5,184 / 153 / 3 at `4426ea0`, with the same flags (`--continue-on-collection-errors`). The sorted failed/error node IDs are identical (`diff` empty), and the +3 passes are the new tests.

---

## Preflights and Live Wiring Checks

Every preflight goes through `scripts/preflight_backend.py --list-models`, which resolves the arm through `backend_factory`. Each ran locally and inside `vgu_ros`, and all four reported `PREFLIGHT OK`.

| Check | Sonnet 5.5 | DeepSeek Flash |
|---|---|---|
| Effective block | `max_attempts 4`, `image_fallback_after_attempts 2`, `thinking_mode between_tools` | `max_attempts 2`, no fallback, `thinking_mode disabled` |
| Sampling | not sent; `unsupported_sampling` = {temperature 0.0, top_p 0.95, top_k 20, presence_penalty 0.0} on every call | temperature 0.0 sent |
| Thinking evidence | content blocks `["text"]`; `output_tokens_details.thinking_tokens` 0 | no `reasoning_content` in the message; `finish_reason: stop` |
| Image tokens | (not separable) | 1280×960 frame = **738**; 640×480 tile = 207 (text-only control differential, `preflight/raw_diag.txt`) |

**DeepSeek per-call image accounting.** Every probe call's prompt was re-sent text-only with the identical system and user text (`capability_probes/roster_validation_20261006/deepseek_image_tokens.{py,jsonl}`).

- Image tokens = probe `prompt_tokens` − control `prompt_tokens`.
- The result was **738 on all 119 calls**: every frame is 1280×960, and the value is constant and below 1,024.
- The 5 episode calls ran 2,405–2,559 prompt tokens, which includes the same 738-token frame.

---

## Probe Battery v1 (60 Items)

Frozen inputs, unchanged from the model-wiring round:

- `manifest_v1.json` (sha256 `9659782d…`, verified);
- prompt version 1;
- one call per item, temperature 0, ≥ 3 s pacing;
- the runner's own attempt policy (1 attempt, no fallback).

| Backend | Overall | locate | left_right | robot_count | nearest_first | Refusals |
|---|---|---|---|---|---|---|
| Gemini ER-2 | 60/60 [0.94, 1.00] | 15/15 | 15/15 | 15/15 | 15/15 | 0 |
| gpt-4o | 58/60 [0.89, 0.99] | 15/15 | 13/15 | 15/15 | 15/15 | 0 |
| Qwen3-VL-8B | 57/60 [0.86, 0.98] | 15/15 | 14/15 | 15/15 | 13/15 | 0 |
| gpt-5.1 | 54/60 [0.80, 0.95] | 15/15 | 13/15 | 11/15 | 15/15 | 0 |
| **Sonnet 5.5** | **60/60** [0.94, 1.00] | 15/15 | 15/15 | 15/15 | 15/15 | 0 |
| **DeepSeek Flash** | **60/60** [0.94, 1.00] | 15/15 | 15/15 | 15/15 | 15/15 | 0 |

**Caveat beside the Sonnet row.** The probe template contains neither the `<think>` block nor a `reasoning` field. Sonnet's perception and dynamics scores are valid, but its 0/119 probe refusal rate **does not transfer** to the deployed stage-1 path.

---

## Battery v2 (Dynamics, Main 59 Items)

Frozen inputs:

- `manifest_v2.json`, sha256 `faf1953b…` (verified before any call);
- `--subset main`, the frozen v1 template, one call per item, ≥ 3 s pacing.

Logs root: the main checkout's `data/logs/vm_runs` (frames hash-checked by the runner). ER-2 and gpt-4o are the 2026-10-04 runs (`docs/reports/2026-10-04-battery-v2-results.md`). Qwen ran through an SSH tunnel to the VM's llama-server with no Isaac running (peak 7,809 MiB, minimum free 16,284 MiB).

| Backend | Main (59) | Excluding temporal_order (40) | motion_direction | **conflict_prediction** | GT-yes | GT-no | "yes" answers | temporal_order ⚠ | Refusals / errors |
|---|---|---|---|---|---|---|---|---|---|
| Gemini ER-2 | 48/59 [0.70, 0.89] | 36/40 [0.77, 0.96] | 20/20 [0.84, 1.00] | 16/20 [0.58, 0.92] | 10/10 | 6/10 | 14/20 | 12/19 [0.41, 0.81] | 0 / 0 |
| gpt-4o | 26/59 [0.32, 0.57] | 25/40 [0.47, 0.76] | 16/20 [0.58, 0.92] | 9/20 [0.26, 0.66] | 7/10 | 2/10 | 13/20 | 1/19 [0.01, 0.25] | 2 refusals / 11 unparsed |
| **Qwen3-VL-8B** | 38/59 [0.52, 0.75] | 32/40 [0.65, 0.90] | 17/20 [0.64, 0.95] | **15/20** [0.53, 0.89] | 5/10 | 10/10 | **5/20** | 6/19 [0.15, 0.54] | 0 / 0 |
| **Sonnet 5.5** | 48/59 [0.70, 0.89] | 36/40 [0.77, 0.96] | 20/20 [0.84, 1.00] | **16/20** [0.58, 0.92] | 10/10 | 6/10 | 14/20 | 12/19 [0.41, 0.81] | 0 / 0 |
| **DeepSeek Flash** | 43/59 [0.60, 0.83] | 34/40 [0.71, 0.93] | 15/20 [0.53, 0.89] | **19/20** [0.76, 0.99] | 10/10 | 9/10 | 11/20 | 9/19 [0.27, 0.68] | 0 / 0 |
| gpt-5.1 (**PARTIAL**, aborted on credits) | — | — | 16/20 | 5/7 answered (+1 credit error) | 4/4 | 1/3 | — | not reached | 0 / 1 |

Chance rates are motion_direction 0.40, conflict_prediction 0.50 and temporal_order 0.50. The gpt-5.1 row is excluded from every comparison; it is shown only so the partial data is visible.

**Reading the headline question.** Where do the newcomers land on conflict_prediction?

- **DeepSeek: 19/20.**
  - Its only miss is `main_conflict_prediction_009`, a GT-no item Sonnet also missed.
  - Its CI [0.76, 0.99] clears gpt-4o's upper bound of 0.66, and its point estimate tops ER-2.
  - It overlaps ER-2 [0.58, 0.92], so at n = 20 it is not distinguishable from ER-2.
- **Sonnet: 16/20, matching ER-2's totals and sub-splits by coincidence.**
  - Per item, the two disagree on 4/59 items: 2 of them conflict items (`_009` vs `_019`) and 2 temporal_order items.
  - Both answer "yes" too readily, with 4 false alarms on GT-no items each.
- **Qwen: 15/20, but by never predicting conflicts.**
  - It is perfect on GT-no (10/10) and at chance on GT-yes (5/10). It answered "yes" only 5 times.
  - Its accuracy beats gpt-4o's, but the error mode, false negatives, is the dangerous one for a coordinator that must anticipate jams.
- **All three newcomers separate from gpt-4o's chance profile on point estimates.** Only DeepSeek's interval excludes gpt-4o's.

**Known caveats, carried forward:**

- **⚠ temporal_order is QUARANTINED.** It is reported but must not be read as capability.
  - The lower id is correct in 15/19 items, so a "pick the lower id" rule scores 15/19. Every backend is at or below that baseline: ER-2 12, Sonnet 12, DeepSeek 9, Qwen 6, gpt-4o 1.
  - M1's lagging status colour is also a static cue.
- **motion_direction is an arrow confound.** M1 draws a heading arrow and a status colour, so the item reads off a static annotation.
  - DeepSeek's weakness is on **robot targets: 4/8**, against 11/12 on edge targets.
  - Its v1 fine labels are perfect (60/60), so the weakness is relational ("toward robot X"), not perception.
- **Manifest stamp caveat** (spec, 2026-10-06 append-only).
  - For the decision-frame items, the M1 state that drew the frame lies 0.20 s before to 0.23 s after the decision's scene stamp.
  - The manifest's "exact M1 state" pairing and the 0.1 s GT gate were therefore applied at the wrong stamp for those items. This caveat applies to every v2 citation here.

Runs (gitignored): `data/logs/capability_probes/roster_validation_20261006/<backend>__{v1,v2main}/`. The gpt-5.1 partial is `openai_gpt51__v2main/*_aborted.jsonl`.

---

## Head-On Episodes

### Apparatus

The apparatus is identical to the model-wiring round:

- Cell `head_on_asymmetric_w0p2_eopen_bshort_o0`, overlay `ho_orchestrator.yaml` **md5 `b571636a…` verbatim** (plan channel on, `prompt_robot_order: random`, gate `swap`, `MODALITY=on`).
- Prompt v3.3 (the list-order line was present in every stage-1 prompt). `RECORD=0`, `REC_SEC` 1000, `SIM_SEC` 1200.

**Tree.** The VM's `b5cafe4` tree plus the 16-file branch delta at `66e4f44`:

- shipped by `git archive` with `touch`;
- `reasoning/` and `scripts/` `__pycache__` purged;
- `swarm_orchestrator` purge-rebuilt;
- `DEPLOY MD5 MATCH LOCAL`; `.pyc` body check 49/49.
- The first decision artifact's effective block showed `max_attempts: 4` and `deepseek-flash`, which rules out the live-mount versus colcon trap.

**Drivers.** `_vm_driver/rv_{deploy,run,chain,instcheck}.sh`, copied from the model-wiring `mw_*.sh` with paths changed. Every gate is kept:

- pristine-config refusal;
- `pgrep` empty before launch;
- `GATE OK` from the `logs saved to` line;
- `M5 STARTED`;
- `RESTORE OK` with source and installed md5s;
- GT moved per run;
- chain abort on 429 or a failed restore.

All three runs passed every gate, and each settle was clear in 10 s, so no PID kill was needed.

### Plan Metrics Against Every Head-On Row

The scorers are as before:

- `_analysis/plan_table.py`, which uses the project's `score_plan_decision`;
- `coverage_scene_scores.py flow`.

"yld" means the pre-repair yielder matches `correct_yielder` robot_2. The emission and consistency columns count dispatched plans.

| Episode | Prompt | Order | Trigger answered at (sim s) | Trigger provenance (edits) | yld | Emitted / consistent | Outcome (arrivals) | Delay sum (s) | Dissolution (s) |
|---|---|---|---|---|---|---|---|---|---|
| **Sonnet s42** (`rv01`) | v3.3 | id_desc | 134.3 (after 14 terminal refusals from 26.9) | repaired, 1 (swap) | ✗ | 1/1 / 1/1 | resolved (2/2) | **366.6** | 176.3 |
| **Sonnet s43** (`rv02`) | v3.3 | id_desc | 60.1, **on the grey-image attempt** (after 4 terminal refusals from 27.6) | vlm_verbatim, 0 | ✓ | 1/1 / 1/1 | resolved (2/2) | **222.3** | 104.9 |
| **DeepSeek s42** (`rv03`) | v3.3 | id_asc | 26.5 (first call) | repaired, 1 (swap) | ✗ | 1/1 / 1/1 | resolved (2/2) | **146.5** | 67.2 |
| gpt-5.1 s42 (`mw03`) | v3.3 | id_desc | 26.9 | vlm_verbatim, 0 | ✓ | 1/1 / 1/1 | resolved (2/2) | 143.8 | 66.4 |
| Qwen s42 (`mw01`) | v3.3 | id_desc | 26.9 | m3_default (absent) | ✓ | 0/12 / — | clogged (1/2) | ≥ 320.6 | 69.8 |
| Qwen s43 (`mw02`) | v3.3 | id_asc | 27.9 | m3_default (absent) | ✓ | 0/3 / — | intermittent (2/2) | 183.6 | 70.0 |
| ER-2 s42 / s43 / s44 (`vp01–03`) | v3.2 | desc / asc / asc | about 27 | repaired 1 (swap) / repaired 1 (reorder) / verbatim 0 | ✗ / ✓ / ✓ | 1/1 each | resolved ×3 | 149.8 / 148.9 / 147.4 | 69.1 / 66.2 / 67.6 |
| gpt-4o s42 / s43 (`vp04–05`) | v3.2 | desc / asc | about 27 | repaired 1 (swap) ×2 | ✗ ×2 | 2/2, 1/1 | intermittent / resolved | 153.3 / 147.9 | 68.1 / 68.9 |
| Layer-2-off head-on (reference) | — | — | none | — | — | — | clogged (0/2) | ≥ 531 (censored) | — |

Per-arm reading (descriptive; n is 1–2 per arm):

- **Sonnet.** Refusal delays intervention, and the delay shows up in the outcome.
  - In s42 the robots sat latched 107 s before the first answered trigger. Its delay is 2.4× the other resolved arms', and the robots did not arrive until the 183 s and 226 s marks after t0.
  - In s43 the answered trigger came on attempt 3, the grey image. That decision was therefore made **without the scene image**: from the robot-state text and geometry block only.
  - Both resolutions came from a single dispatch, through the M3 gate in s42 and verbatim in s43.
  - Post-resolution re-checks: 2 answered `none`, the rest refused, with no dispatch.
- **DeepSeek.** The cleanest new-arm intervention, on the first call with no refusals.
  - It named robot_1 under `id_asc`. That is the same choice gpt-4o made in both pilot episodes, and the presentation-order finding's robot_1/first-slot prior under `id_asc`. The registered swap gate re-grounded it (robot_1 has 0.70 m < 1.08 m retreat room), as designed.
  - Four post-resolution re-checks answered `none`.
- **Stage 2** (retreat choice) answered in all three runs with 0 refusals.

**Comparability.** The ER-2 and gpt-4o rows ran v3.2 on `a8fc1bc`; every other row ran v3.3 (ruling 4 caveat). The outcome metrics are comparable; provenance and edit counts are not like-for-like across that boundary.

---

## Refusal Accounting

| Arm | Stage-1 decisions / attempts | Refused attempts | Terminal refusals | Grey fallback fired | Answers on the grey attempt | Stage-2 answered / refused | Probe refusals (v1 + v2) |
|---|---|---|---|---|---|---|---|
| **Sonnet 5.5** (`rv01` + `rv02`) | 26 / 96 | **91 (94.8%)**, all `reasoning_extraction` | **21/26 (80.8%)** | 24 decisions | 3 | 2 / 0 | 0/119 |
| DeepSeek Flash (`rv03`) | 5 / 5 | 0 | 0 | — (not configured) | — | 1 / 0 | 0/119 |
| gpt-5.1 (`mw03`) | 5 / 5 | 0 | 0 | 0 | 0 | 1 / 0 | 0/60 + 0/28 |
| Qwen3-VL-8B (`mw01–02`) | 17 / 17 | 0 | 0 | — | — | 2 / 0 | 0/60 + 0/59 |
| gpt-4o (verbatim pilot, head-on + IB10) | 20 / 21 | 1 | 0 | 0 | 0 | 4 / 0 | 0/60 + 6/139 |
| ER-2 (verbatim pilot) | 32 calls | 0 | 0 | — | — | — | 0/60 + 0/139 |

**Sonnet split by image.**

- Real-frame attempts: 49/51 refused.
- Grey-image attempts (attempts 3–4): 42/45 refused.
- First attempts: 25/26 decisions refused.
- The 5 answered decisions came on attempt 1 (once), attempt 2 (once, real frame, after the re-ask suffix) and attempt 3 (3 times, grey).
- Within one episode, identical inputs were sometimes refused and sometimes answered. That is consistent with a classifier sitting near its threshold under no temperature control.

**Sonnet refusal diagnostic** (DIAGNOSTIC ONLY; not a prompt fork; excluded from every table; `vm_runs/roster_validation/sonnet_refusal_diag/`).

- **Setup.** The recorded stage-1 prompt and annotated frame were replayed through the shipped `anthropic` arm. Three decisions were used: `e666b28b`, sim 26.9 `id_desc`; `704179f6`, 42.0 `id_desc`; `218c3672`, 215.2 `id_asc`.
- **Results:**

  | Condition | Result |
  |---|---|
  | A: recorded prompt | refused 3/3, `reasoning_extraction`, output_tokens 0 |
  | B: `<think>` block replaced by "Write ONLY the final JSON object, with no surrounding text or markdown." | answered 3/3, valid decisions |
  | C (n = 1): think block kept, `reasoning` JSON field removed | refused **mid-stream** after 150 output tokens of `<think>` text |
  | D (n = 1): both removed | answered |

- **Documentation** (`anthropic_docs_refusals_excerpt_20261006.md`, from `platform.claude.com/docs/en/build-with-claude/refusals-and-fallback`):
  - `reasoning_extraction`: "The request asks the model to reproduce its internal reasoning in the response text".
  - Common triggers include "A `<thinking>`, `<reasoning>`, or scratchpad section that the model fills in before it answers" and "A `reasoning`, `thinking`, or `trace` field in JSON output".
  - Refusals before any output in this category "are billed like any other request".
- **Not used:** no server-side `fallbacks` parameter is sent. It would re-route a refusal to a different model inside the arm (wiring decision, model-wiring report).

**Transport (DeepSeek).**

- There were 0 connection errors and 0 malformed bodies in 249 DeepSeek calls:
  - 119 probe calls;
  - 119 text-only controls;
  - 5 stage-1 calls and 1 stage-2 call;
  - 5 preflight and diagnostic calls.
- The research note's 1–3% silent-close rate did not occur at this n, so **the retry path was not exercised live**.
- It is covered by `test_openai_adapter_maps_a_silently_closed_connection_to_a_transport_error` and `test_openai_adapter_maps_a_truncated_body_to_a_transport_error`: both map to `ConnectionError`, which `Reasoner` retries within `max_attempts` and never counts as a refusal (`reasoner.py`, the `except (BackendTimeoutError, ConnectionError)` branch).
- With DeepSeek's 2 attempts, a single drop consumes the only retry.

---

## Six-Backend Consolidated Table

| | Gemini ER-2 | gpt-4o | Qwen3-VL-8B | gpt-5.1 | **Sonnet 5.5** | **DeepSeek Flash** |
|---|---|---|---|---|---|---|
| Served model | `gemini-robotics-er-2-preview` | `gpt-4o-2024-08-06` | `qwen3-vl-8b-instruct-q4_k_m` | `gpt-5.1-2025-11-13` | `claude-sonnet-5-5` | `deepseek-flash` |
| Standard reached | baseline | baseline | full | pilot | **full** (refusal-dominated) | **pilot** |
| Probes v1 (60) | 60 | 58 | 57 | 54 | **60** | **60** |
| v2 motion_direction (20) | 20 | 16 | 17 | 16 (partial run) | **20** | **15** (robot targets 4/8) |
| v2 **conflict_prediction** (20) | **16** | 9 (chance) | **15** (yes-rate 5/20) | unanswered (credits) | **16** (yes-rate 14/20) | **19** |
| v2 temporal_order ⚠ (19; lower-id rule = 15) | 12 | 1 | 6 | not reached | 12 | 9 |
| Head-on episodes | s42/s43/s44 | s42/s43 | s42/s43 | s42 | s42/s43 | s42 |
| Plan emission (dispatched) | 3/3 | 3/3 | **0/15** | 1/1 | 2/2 | 1/1 |
| Plan consistency | 3/3 | 3/3 | — | 1/1 | 2/2 | 1/1 |
| Trigger provenance (edits) | rep 1 / rep 1 / verb 0 | rep 1 / rep 1 | m3_default ×2 | verbatim 0 | rep 1 / verbatim 0 | rep 1 |
| Correct yielder pre-repair | 2/3 | 0/2 | 2/2 | 1/1 | 1/2 | 0/1 |
| Outcome | resolved ×3 | intermittent, resolved | clogged, intermittent | resolved | resolved ×2 | resolved |
| Delay sum (s) | 149.8 / 148.9 / 147.4 | 153.3 / 147.9 | ≥ 320.6 / 183.6 | 143.8 | **366.6 / 222.3** | 146.5 |
| Stage-1 refused attempts | 0 | 1/21 | 0/17 | 0/5 | **91/96** | 0/5 |
| Probe refusals (v1 + v2) | 0/199 | 6/199 | 0/119 | 0/88 | 0/119 | 0/119 |
| Prompt for episodes | v3.2 | v3.2 | v3.3 | v3.3 | v3.3 | v3.3 |
| Cost actuals (this report's work) | — | — | $0 | $0.029 | about $1.49 | about $0.022 |

---

## Cost Actuals

Rates:

- **Sonnet 5.5:** $2 / $10 per MTok (claude-api reference table, cached 2026-09-25).
- **DeepSeek Flash:** $0.15 / $0.60 per MTok off-peak, double at peak (pricing page, fetched 2026-10-06, `preflight/deepseek_pricing_20261006.html`). Every call ran 14:36–15:36Z on a Tuesday, which is off-peak (peak is 01–04 and 06–10 UTC).
- **gpt-5.1:** $1.25 / $10.

| Item | Tokens (in / out) | USD |
|---|---|---|
| Sonnet preflights (local, container, raw-shape diagnostic) | about 5,050 / 41 | 0.010 |
| Sonnet probes v1 (60) | 107,763 / 2,943 | 0.245 |
| Sonnet probes v2 main (59) | 105,002 / 11,678 | 0.327 |
| Sonnet `rv01`: 2 answered attempts (logged) + 67 refused (**estimated** at about 4.1k input each; measured 3,994–4,219 in replays) + 1 stage-2 (est.) | about 285k / about 1.1k | about 0.58 (est.) |
| Sonnet `rv02`: 3 answered (logged) + 24 refused (est.) + 1 stage-2 (est.) | about 113k / about 1.9k | about 0.25 (est.) |
| Sonnet refusal diagnostic (8 calls, logged) | 31,890 / 1,513 | 0.079 |
| **Sonnet subtotal** | | **about 1.49** |
| DeepSeek preflights and diagnostic | about 3,400 / 40 | 0.001 |
| DeepSeek probes v1 + v2 | 102,627 / 714 | 0.016 |
| DeepSeek text-only controls (119) | 14,805 / 119 | 0.002 |
| DeepSeek `rv03` (5 stage-1 logged + 1 stage-2 est.) | about 14k / about 2.2k | 0.003 |
| **DeepSeek subtotal** | | **about 0.022** (≤ 0.044 at peak rates) |
| gpt-5.1 v2 partial (28 calls; the 429 is not billed) | 20,222 / 403 | 0.029 |
| Qwen (local) | — | 0 |
| **Total** | | **about $1.54** of the $10 hard stop |

VM time ran 14:39–15:45Z (about 1 h 6 min): deploy, three episodes, the Qwen battery, then restore.

---

## VM State After the Work

- **Source tree:** restored. `RESTORE MD5 MATCH PREDEPLOY`, and an independent check of the 16 delta paths against `git show b5cafe4:` matched. The 3 files new in the delta were removed.
- **Installed tree:**
  - `swarm_orchestrator` was rebuilt.
  - The installed-vs-source check passed 126/126.
  - The `.pyc` body check passed 49/49.
  - The full installed snapshot (non-`__pycache__`) is identical before and after.
  - `orchestrator.yaml` is `1f656533…` in source and installed; `rag.yaml` is `e18c723c…`.
- **Processes:** `ps` count 0 for `fc_launch`, `run_simulation`, `isaac.scripts` and `llama-server`. The GPU is at 0% / 171 MiB.
- **Docker:** `vgu_ros` only, and the image list is `ros:jazzy` only. The llama.cpp image was removed and the GGUFs kept at `/home/ubuntu/models/qwen3vl/`.
- **Left on disk:**
  - `/home/ubuntu/roster_validation/` (drivers, chain log, runs).
  - The `/ws/.env` key lines appended for this round (STOP item 3).
- **Instance:** left RUNNING as found.

---

## Artifacts

In the main checkout (gitignored):

- `data/logs/vm_runs/roster_validation/runs/rv0{1,2,3}_*/`: each run's bundle (GT, node logs, decisions, `m5_scene.jsonl`, frames, overlay, sidecar, `vram.csv`, and the `CONDITION`, `GATE`, `M5_STARTED` and `RESTORE` files).
- `data/logs/vm_runs/roster_validation/_vm_driver/`: the drivers, the deploy tar and md5 lists, and the mirrored VM-side manifests (`vm_side/`), chain log, Qwen start and server logs, and VRAM samples (`vm_side_top/`).
- `data/logs/vm_runs/roster_validation/preflight/`: listings, preflights, the raw-shape diagnostic and the DeepSeek pricing snapshot.
- `data/logs/vm_runs/roster_validation/sonnet_refusal_diag/`: the replay script, inputs, per-decision results and the documentation excerpt.
- `data/logs/vm_runs/roster_validation/_analysis/`: `*_plans.json`, `*_flow.json` and `plan_table.py`.
- `data/logs/capability_probes/roster_validation_20261006/`: the per-arm JSONL, summaries, stdout and stderr, plus the DeepSeek image-token script and JSONL.

No key value appears in any artifact or transcript: keys are read from the environment, and the VM `.env` lines were piped over SSH stdin, never printed.

# PILOT: Per-Arm Provider-Side Reasoning Dose on Battery-v2 conflict_prediction

**Prepared:** 2026-10-07

**Status:** PILOT. It is exploratory and EXCLUDED from all confirmatory counts. The registration is in the prereg-v2 design spec, "Reasoning-dose pilot (registered 2026-10-06)".

**Revision history:**

- Rev 0 (pre-registration, committed before any API call, `28d453c`): dose matrix, item set, scoring, low-dose reuse test, and the decision rule with exact numbers.
- Rev 1: results. Reuse verification, the dose table, McNemar results, the frozen settings, changed answers, spend. The rule text above "Results" is unchanged from Rev 0.

---

## Summary

- **The rule adopts no higher dose. Every arm keeps its pin.** gpt-5.1 stays at `reasoning_effort: none`, Sonnet 5.5 at `between_tools`, ER-2 at `thinking_level: low` and DeepSeek at thinking `disabled`. ER-2 does not pass the rule, so there is **no owner flag**.
- **Net change on conflict_prediction, H minus primary L:**

  | Arm | Net | Exact McNemar p |
  |---|---|---|
  | gpt-5.1 | 0 | 1.0 |
  | Sonnet | 0 | 1.0 |
  | ER-2 | +1 | 1.0 |
  | DeepSeek | **−13** | 0.0002 |

  No arm reaches the +3 margin. Every H median latency is under 15 s; DeepSeek's 10.4 s is censored by the cap.
- **DeepSeek with thinking on fails because it runs out of tokens.**
  - At effort `low`, thinking still uses about 1.8k–2k tokens. 14 of 20 calls hit the pinned `max_tokens: 2048` (`finish_reason: length`): 12 came back empty and 2 were unparseable. Rev 0 declared that a truncated answer counts as wrong.
  - The 6 calls that finished were all correct, and all six were GT-yes items.
  - This is what happens when the thinking dose meets the shared token cap, not a measure of how well DeepSeek reasons when it thinks. It would not change the verdict even uncapped: L is 19/20, so net is at most +1. It is still a trap: switching DeepSeek's thinking on without raising `max_tokens` breaks the arm.
- **Sonnet's minimum thinking-on dose never thought.** At adaptive + effort `low`, `thinking_tokens` was 0 and the response held only a `text` block on 20/20 calls.
  - The H arm was therefore the same as no thinking.
  - The 4 answers that changed (2 each way) are run-to-run variation. Sonnet takes no temperature, and its stored-vs-fresh L also differs on 3 items.
  - Sonnet writes its visible reasoning into the text block at both doses, about 300 output tokens.
- **Reuse is verified byte-wise.**
  - For gpt-5.1 (both segments), ER-2 and DeepSeek, all 20 request bodies at each stored run's commit equal the bodies at HEAD.
  - The 20 live L-retest bodies equal them too.
  - The probe path never touches the v3 template.
- **Spend:** **$0.50** of the $5 hard stop. That is $0.49 for the eight 20-call runs and $0.01 for the four smoke calls. Sonnet accounts for $0.27.

---

## Decision Rule (Fixed Before Any API Call)

### Doses

Each arm has a lower dose L, which is the current pin in `config/models.yaml`, and a higher dose H. H is the smallest documented provider-side step above the pin.

| Arm | L (pin) | H | Basis for H |
|---|---|---|---|
| gpt-5.1 (`openai_gpt51`) | `reasoning_effort: none`, temperature 0.0 | `reasoning_effort: low`. `temperature` and `top_p` are omitted, because GPT-5.1 returns HTTP 400 on sampling fields at any effort other than `none`. | The next documented effort above `none` |
| Sonnet 5.5 (`anthropic`) | `thinking: {type: between_tools}`, thinking off | `thinking: {type: adaptive}` + `output_config: {effort: low}` | The brief asked for a small thinking budget, but `budget_tokens` returns 400 on Sonnet 5.5 (claude-api reference, cached 2026-09-25), so no budget can be set. Adaptive thinking at the lowest documented effort (`low`) is the minimum thinking-on dose. |
| ER-2 (`gemini`) | `thinking_level: low` | `thinking_level: medium` | The documented levels for `gemini-robotics-er-2-preview` are `minimal, low, medium, high` (ai.google.dev thinking guide, fetched 2026-10-06). `medium` is one step up, and the Robotics-ER page recommends it for "a good balance between latency and performance". |
| DeepSeek (`deepseek`) | `thinking: {type: disabled}` | `thinking: {type: enabled}` + `reasoning_effort: low` | When thinking is enabled, DeepSeek defaults to effort `high`. That is not a small step, so H uses the lowest documented effort (`low/high/max`), to match the other arms' smallest-step doses. |

`max_tokens` stays at the pinned 2048 in both doses. Thinking tokens share that cap, so a truncated answer, or one with no text, scores as wrong. Every call records its `stop_reason` / `finish_reason`.

The overrides live only in a pilot copy of `models.yaml`, kept outside `config/` and passed with `--models-yaml`. Its sha256 is recorded below. `config/models.yaml` is not edited.

### Items and Calls

- The items are the 20 `conflict_prediction` items of the battery-v2 `main` subset (`manifest_v2.json`, SHA `faf1953b…`): 10 GT-yes and 10 GT-no.
- The prompt is the frozen capability-probe prompt v1, with the same seeded lettering.
- Each item gets one call, with no re-ask and no grey-image fallback. This is the runner's standing policy.
- Each call records:
  - wall-clock latency of `analyze()`;
  - input, output and thinking/reasoning tokens;
  - the request body, with images replaced by their sha256;
  - the served model.
- Before each H run there is one smoke call per H config, on a conflict_prediction item, excluded from scoring. It checks four things:
  - the request is accepted;
  - the thinking-token field is present;
  - DeepSeek accepts an image with thinking enabled;
  - whether DeepSeek ignores or rejects `temperature`.
- For this pilot, any HTTP 4xx is fatal: the arm stops, the cause is fixed, and the whole arm-dose is re-run. Other transport errors follow the runner policy. They score `backend_error` (wrong) and are reported item by item.

### Low-Dose Source

- **Primary L, reused from storage.** The stored L results for gpt-5.1, ER-2 and DeepSeek are reused only if the full request body for each of the 20 items is byte-identical at the stored run's commit and at HEAD. The bodies are captured through a fake `requests.post`, with the image payloads hashed.
  - gpt-5.1: 15/20, from two segments at `66e4f44` and `a0db9f6`. Both segments must match.
  - ER-2: 16/20, at `23e36c5`.
  - DeepSeek: 19/20, at `66e4f44`.
  - Any mismatch means L is re-run fresh and becomes the primary.
- **Sonnet's primary L is a fresh run under HEAD** (brief).
- **Same-day retest.** A same-day L retest (20 calls) is run for every arm. It is the latency source for L, because the stored records carry `latency_ms: null`, and it is the drift/noise reading. The rule is applied against the primary L. The verdict against the retest L is reported beside it, and any disagreement goes to the owner.

### Rule

- **net** = (H correct) − (L correct) on the 20 paired items. Refusals, unparsed answers and backend errors all count as wrong.
- **Registered margin: net ≥ +3 (of 20).**
- **Registered latency bound: the median per-call wall-clock latency of the 20 H calls is ≤ 15.0 s.** This is the orchestrator's re-analysis `cooldown_sec: 15.0` (`ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`). It is a PROXY: a probe call is one short single-image prompt, and a stage-1 episode call carries the v3.4 prompt and differs in latency.
- **Adopt H for an arm only if both hold.** Otherwise the arm keeps L.
- **ER-2 exception.** ER-2's config is v1-frozen. If H passes for ER-2, it is NOT adopted; it is flagged as an owner decision.
- An exact two-sided McNemar test on the discordant pairs is reported for every arm. It is not part of the decision.

### Ceilings, Stated in Advance

- DeepSeek's primary L is 19/20, so net is at most +1. The rule cannot adopt DeepSeek's H by construction. The arm runs anyway for the latency, token and answer-change record.
- ER-2's net is at most +4 and gpt-5.1's at most +5. Sonnet's ceiling depends on its fresh L.

### Budget

- Hard stop: **$5**.
- Cost is computed from per-call usage at list prices, with thinking/reasoning tokens billed as output:
  - gpt-5.1: $1.25 / $10 per MTok.
  - Sonnet 5.5: $2 / $10.
  - ER-2: $1.00 / $5.00 (the battery-v2 report's rates).
  - DeepSeek Flash: $0.15 / $0.60 off-peak, doubled at peak (01–04 and 06–10 UTC).

---

## Results

Run on 2026-10-06, 16:41–16:46 UTC (local 2026-10-06 23:41–23:46, UTC+7), on branch `feat/v2-dose-pilot`. The code was `b46540d`, which is the dose knobs on top of the v3.4 tip `b092f87`. Artifacts are in `data/logs/capability_probes/reasoning_dose_pilot_20261007/`:

| File | Contents |
|---|---|
| `models_pilot.yaml` | Pilot model config, sha256 `e4555700…`. It is HEAD's `config/models.yaml` (`2f13d255…`) with four H sections appended, and the L sections are byte-identical. |
| `dose_driver.py` | Wraps the runner's own `prepare_item` / `run_item`, and adds wall-clock latency, sent bodies, raw usage and stop reasons. |
| `capture_request_bodies.py` | Reconstructs the request bodies offline for the reuse check. |
| `analyze_dose.py` → `analysis.json` / `analysis.txt` | Applies the decision rule and writes the results. |
| `runs/<L\|H>__<backend>/` | One directory per run: per-item records, `*_calls.jsonl` and a summary. |
| `runs/smoke__*/` | One unscored call per H config. |

DeepSeek calls ran at 16:42–16:46 UTC, which is off-peak.

### Low-Dose Reuse Verification

**Prompt independence.**
- `scripts/capability_probes.py` builds every probe prompt with `reasoning.vlm.capability_probes.prompt`. That is the frozen v1 template, `CAPABILITY_PROBE_PROMPT_VERSION = 1`, SHA-pinned in `tests/unit/test_capability_probe_prompt.py`.
- It imports nothing from `prompt_builder`, `prompt_v1`, `prompt_v2` or `stage2_prompt`. Its one `reasoning.vlm.reasoner` import is `is_refusal`, a text check.
- The three adapters read only `PromptPayload.system_prompt`, `user_prompt` and the image paths.
- So the v3.3 → v3.4 re-pin cannot reach a probe call. Sonnet's 91/96 refusals were stage-1 episodes under v3.3. Its stored probe run had 0 refusals.

**Byte-wise bodies.** For each arm, `capture_request_bodies.py` imports the runner and adapters from a detached worktree at the stored run's commit, using that commit's own `config/models.yaml`, and does the same at HEAD. A fake `requests.post` records the URL and the JSON body. Base64 images are replaced by their sha256, key order is kept, and all 20 items are captured.

| Stored L run | Commit | Identical bodies at HEAD |
|---|---|---|
| gpt-5.1 `openai_gpt51_20261006T161416Z_merged.jsonl`, segment 1 | `66e4f44` | 20/20 |
| gpt-5.1, segment 2 (after the credit gap) | `a0db9f6` | 20/20 |
| ER-2 `gemini_20261004T181526Z.jsonl` | `23e36c5` | 20/20 |
| DeepSeek `deepseek_20261006T143930Z.jsonl` | `66e4f44` | 20/20 |

- HEAD bodies were captured before and after the knob commit `b46540d`, and they are identical, so the pins did not move.
- The bodies actually sent in the live L retests equal the captured HEAD bodies, 20/20 on every arm including Sonnet.
- The stored results are therefore the primary L, as registered. Sonnet's primary L is the fresh run.

### Dose Table

All figures are over the same 20 paired items. "Retest L" is today's L run. Latency is the wall-clock time of `analyze()`, one call, as a probe-call PROXY. The stored records carry no latency.

| Arm | L → H | Primary L | Retest L | H | GT-yes / GT-no correct (L → H) | "yes" answers (L → H) |
|---|---|---|---|---|---|---|
| gpt-5.1 | `none` → `low` (sampling omitted) | 15 (stored) | 16 | **15** | 10/5 → 9/6 | 15 → 13 |
| Sonnet 5.5 | `between_tools` → adaptive + effort `low` | 17 (fresh) | 17 (same run) | **17** | 10/7 → 10/7 | 13 → 13 |
| ER-2 | `low` → `medium` | 16 (stored) | 16 | **17** | 10/6 → 10/7 | 14 → 13 |
| DeepSeek | `disabled` → enabled + effort `low` | 19 (stored) | 18 | **6** | 10/9 → 6/0 | 11 → 6 |

| Arm | Median latency L / H | H p90 / max | Thinking tokens, median L / H (H max) | H calls with thinking > 0 | H stop reasons | Cost per call L / H |
|---|---|---|---|---|---|---|
| gpt-5.1 | 2.30 s / 2.42 s | 3.65 s / 7.82 s | 0 / 52.5 (521) | 20/20 | `stop` 20 | $0.00110 / $0.00191 |
| Sonnet 5.5 | 4.77 s / 4.09 s | 4.70 s / 6.08 s | 0 / 0 (0) | **0/20** | `end_turn` 20 | $0.00705 / $0.00636 |
| ER-2 | 6.59 s / 7.53 s | 11.30 s / 14.24 s | 161 / 356 (1,922) | 20/20 | `completed` 20 | $0.00251 / $0.00424 |
| DeepSeek | 1.47 s / 10.39 s ⚠ | 10.77 s / 10.81 s | 0 / 2,048 (2,048) | 20/20 | **`length` 14**, `stop` 6 | $0.00013 / $0.00129 |

⚠ DeepSeek's H latency is censored: 14 calls stopped at the 2048-token cap, so its uncapped latency is higher.

Notes on the token counts:
- gpt-5.1 reports `reasoning_tokens` in `completion_tokens_details`.
- Sonnet reports `output_tokens_details.thinking_tokens`. Its output is about 300 tokens at both doses, all visible text.
- ER-2 reports `total_thought_tokens`.
- DeepSeek reports `completion_tokens_details.reasoning_tokens`. `reasoning_content` runs to about 7k characters.

### McNemar and the Rule

Here b counts the items only H got right, and c the items only L got right.

| Arm | Net vs primary L (b / c) | Exact p | Net vs retest L (b / c) | Exact p | Margin ≥ +3 | H median ≤ 15 s | Verdict |
|---|---|---|---|---|---|---|---|
| gpt-5.1 | 0 (2 / 2) | 1.000 | −1 (1 / 2) | 1.000 | no | yes | **keep `none`** |
| Sonnet 5.5 | 0 (2 / 2) | 1.000 | 0 (2 / 2) | 1.000 | no | yes | **keep `between_tools`** |
| ER-2 | +1 (1 / 0) | 1.000 | +1 (1 / 0) | 1.000 | no | yes | **keep `low`** (no owner flag) |
| DeepSeek | −13 (0 / 13) | 0.00024 | −12 (0 / 12) | 0.00049 | no | yes (censored) | **keep `disabled`** |

- **The rule gives the same answer against both baselines.** Measured against the retest L instead of the primary L, every arm still keeps L, so nothing goes to the owner on that count.
- **Drift: the same-day retest against the stored L.**
  - gpt-5.1: +1, with 1 item changed. That is at temperature 0.
  - Sonnet: +1, with 3 items changed. Sonnet takes no sampling fields.
  - ER-2: 0, with no item changed.
  - DeepSeek: −1, with 1 item changed.
- **Run-to-run variation is the same size as the H effects.** About ±1 net and 1–3 items changed is noise. That noise is as large as every H effect except DeepSeek's truncation collapse.

---

## Frozen Per-Arm Reasoning Settings (for collection)

| Arm | Setting frozen | Basis |
|---|---|---|
| gpt-5.1 (`openai_gpt51`) | `reasoning_effort: none`, temperature 0.0, `max_completion_tokens` 2048 | `low`: net 0, median 2.42 s. The margin fails. |
| Sonnet 5.5 (`anthropic`) | `thinking: {type: between_tools}`, no effort sent, `max_tokens` 2048 | Adaptive + `low`: net 0, and 0/20 calls thought. The margin fails. |
| ER-2 (`gemini`) | `thinking_level: low` (the v1-frozen pin is unchanged) | `medium`: net +1, median 7.53 s. The margin fails, so there is no owner flag. |
| DeepSeek (`deepseek`) | `thinking: {type: disabled}`, temperature 0.0, `max_tokens` 2048 | Enabled + `low`: net −13, with 14/20 truncated at 2048. The margin fails, and could not pass by construction. |

- `config/models.yaml` is unchanged, because every frozen setting is the existing pin.
- The knobs added in `b46540d` exist but no pin uses them:
  - `OpenAIBackendConfig.omit_sampling`;
  - `reasoning_tokens` in OpenAI-compatible `token_usage`;
  - the ER-2 `minimal` / `medium` levels.

---

## Answers That Changed With Dose (verbatim, against the primary L)

**gpt-5.1.** Four items changed: 2 got better and 2 got worse. Every answer is a bare letter at both doses. Effort `low` used a median of 52 reasoning tokens and left no visible trace.

| Item | GT | L (`none`) | H (`low`) |
|---|---|---|---|
| `_009` | no | `{"choice":"B"}` = yes ✗ | `{"choice": "A"}` = no ✓ |
| `_015` | no | `{"choice": "B"}` = no ✓ | `{"choice": "A"}` = yes ✗ |
| `_017` | no | `{"choice":"B"}` = yes ✗ | `{"choice": "A"}` = no ✓ |
| `_018` | yes | `{"choice": "B"}` = yes ✓ | `{"choice": "A"}` = no ✗ |

The letter-to-option mapping is seeded per item. That is why "B" means "yes" on `_009` and "no" on `_015`.

**ER-2.** One item changed, and it got better.
- `main_conflict_prediction_019`, GT no.
- L `low`: `{"choice": "A"}` (yes) ✗.
- H `medium`: `{"choice": "B"}` (no) ✓.
- `medium` thought for a median of 356 tokens, against 161 at `low`. That is the whole difference: one GT-no false alarm went away.

**Sonnet 5.5.** Four items changed: 2 got better and 2 got worse. No call thought at either dose, so these are re-samples. Opening text, verbatim:

- **`_001`** (GT no; L no ✓ → H yes ✗).
  - L: "…The vertical offset of 160 px is ≈0.63 m, which is already larger than 0.5 m. Both robots move horizontally toward each other, so the vertical offset stays ~160 px…"
  - H: "…A small robot of about 10 cm would put the scale at about 400 px/m, which makes the 160 px offset 0.4 m. That is under 0.5 m, so they could pass within range…"
  - Same scene, same pixel estimates, and a different guessed scale flips the answer. This is the scale-ambiguity failure mode in the model's own words.
- **`_009`** (GT no; L yes ✗ → H no ✓).
  - L: "…If the robot is ~0.1 m, then 40 px = 0.1 m, so 132 px ≈ 0.33 m — within 0.5 m. If the robot is ~0.2 m, 132 px ≈ 0.66 m."
  - H: "…On that scale, the 0.5 m threshold is about 128 px. The current distance is sqrt(132² + 270²) ≈ 300 px, or about 1.2 m. Robot_3 would need to close roughly 170 px…"
- **`_013`** (GT no; L no ✓ → H yes ✗).
  - Both read "Robot_3 … heading right … Robot_1 … no visible heading arrow" at about 488 px.
  - H: "Robot_3 would need to cover about 2 m in 10 s, or 0.2 m/s", and it answers yes.
- **`_019`** (GT no; L yes ✗ → H no ✓).
  - L reasons for about 600 characters ("…If robot_3 moves right at modest speed, it could reach robot_1 within 10 s, but uncertain…") and answers yes.
  - H answers with a bare `{"choice": "B"}`.

**DeepSeek.** 14 items changed; 13 got worse and 1 stayed wrong. Twelve are `""`, an empty answer after `finish_reason: length` with 2,048 reasoning tokens. Two are unparseable visible text cut off mid-answer after 1,772 and 1,851 reasoning tokens. Item `_016`'s text opens:

> "Looking at the image, I can identify the two robots in the corridor: - **robot_1** is on the left side, with a green arrow pointing to the right (east), i.e. moving toward the centre. - **robot_2** is on the right side, with a green arrow pointing to the left (west)…"

The visible answer ignores the "strict JSON only" instruction once thinking is on. The 6 calls that finished were all correct.

---

## Spend

| Item | USD |
|---|---|
| Smoke calls (4, one per H config) | 0.012 |
| gpt-5.1: L retest / H | 0.022 / 0.038 |
| Sonnet 5.5: L / H | 0.141 / 0.127 |
| ER-2: L retest / H | 0.050 / 0.085 |
| DeepSeek: L retest / H (off-peak) | 0.003 / 0.026 |
| **Total** | **0.50** of the $5 hard stop |

Rates are the Rev-0 list prices, with thinking and reasoning tokens billed as output.

---

## Open Items

1. **The DeepSeek thinking trap.** If thinking is ever enabled on the DeepSeek arm, `max_tokens` must rise well above 2048, because effort `low` still reasons for about 2k tokens. Its probe latency would then exceed the 10.4 s censored median. This is a constraint on future configs, not a pilot finding to act on now.
2. **No Sonnet thinking contrast was measured.** The minimum documented thinking-on dose (adaptive + `low`) chose not to think on 20/20 calls, so the pilot measured no thinking contrast for Sonnet. A real contrast would need effort `medium` or higher. That dose is not registered; registering it would be the owner's call. Under the Garg prior and the 4.1–4.8 s base latency, a gain at a higher effort would have to be large to pay for itself.
3. **The latency proxy.** These latencies come from single-image probe calls with short prompts. Stage-1 episode calls carry the v3.4 prompt and longer outputs. ER-2's H p90 of 11.3 s and max of 14.2 s sit close to the 15 s bound even on probes.
4. **Merge note.** `b46540d` edits `reasoning/vlm/openai_backend.py`, `models.py` and `backend_factory.py` additively. A concurrent branch is wiring the new arms, so expect textual conflicts there and in `docs/implementation_notes.md`.

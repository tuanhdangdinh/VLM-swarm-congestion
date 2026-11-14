# Head-On Swapped-ID Replay - Pre-Registered Design

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: design frozen before the first paid call. Implements the replay proposed in the final section of `docs/reports/2026-11-14-head-on-vlm-vs-rule-rescore.md`, with the differences listed under "Differences From the Re-Score Proposal".
- Rev 2 (2026-11-14): amendments 1 and 2 (owner instructions mid-run): the model list is cut to one model per provider (ER-2, gpt-4o, Sonnet 5.5); a Sonnet real-frame stop on any image fallback.
- Rev 3 (2026-11-14): amendment 3 (owner: "add the image-only cell, inspect the sonnet first"): Sonnet fallback cause recorded; Cell C (image only) and Cell D (states only) added with their decision rule; the amendment-2 Sonnet stop is withdrawn.

---

## Question

On the head-on asymmetric standoff scenes, does any current model choose the
oracle-correct yielding robot from the scene (the obstacle side), rather than from a
preference for the label `robot_1` or for the first-listed robot?

**Evidence grade:** a small designed offline experiment. Twelve scenes from one
scenario family at seed 42, two robots, first decision only, no execution. No
p-values and no confidence intervals. Rows are a new stratum and are never pooled
with the September replays or with live runs.

**Authorisation:** owner instruction 2026-11-14, "run the $8 replay". Hard total cap
$10.00, per-model cap $3.00. No VM, no cloud commands, no push.

---

## Stimuli

The 12 genuine-standoff artifacts already used in the September replays. Each one
re-renders byte-identically (SHA-256) through `build_reasoner_request` at its stored
order, and each annotated frame exists. This was checked on 2026-11-14 before this
document was written (130/130 artifacts of the 12 pilot runs matched; 0 missing
images).

| Batch | Run | Request (prefix) | Blocker | Oracle yielder (label, original IDs) | Correct physical robot |
|---|---|---|---|---|---|
| 1 | `20260925_063520` | `53264de9` | west (x = -1.85) | `robot_2` | east robot |
| 1 | `20260925_065143` | `5e7b5a59` | west | `robot_2` | east robot |
| 1 | `20260925_070637` | `2c3fbfa5` | west | `robot_2` | east robot |
| 1 | `20260925_072130` | `61119197` | east (x = +1.85) | `robot_1` | west robot |
| 1 | `20260925_073621` | `d053d0dc` | east | `robot_1` | west robot |
| 1 | `20260925_075116` | `3120c65f` | east | `robot_1` | west robot |
| 2 | `20260925_155433` | `810c9104` | west | `robot_2` | east robot |
| 2 | `20260925_160951` | `42fb0cb8` | west | `robot_2` | east robot |
| 2 | `20260925_162451` | `d4b96fbd` | west | `robot_2` | east robot |
| 2 | `20260925_163949` | `189ae2a6` | east | `robot_1` | west robot |
| 2 | `20260925_165442` | `e4b1bd03` | east | `robot_1` | west robot |
| 2 | `20260925_170938` | `618a9f29` | east | `robot_1` | west robot |

- "West robot" is the robot that spawned west (`robot_1` under the original IDs);
  "east robot" spawned east (`robot_2`). The correct yielder is the only robot with
  free retreat room: the one on the side away from the blocker.
- All 12 render prompt v1. The v1 prompt has no goals, no failure context and no
  plan state on these artifacts, and its obstacle block names no robot. Robot labels
  appear only in the robot-state lines, the pairwise-geometry line and the
  known-ID list.
- Raw (unannotated) frames exist only for batch 2 (0 `_raw.png` files in the batch-1
  runs), so the raw frame cannot be the Arm B image for all scenes.

---

## Arms and Image Conditions

| Arm | IDs in the text | Image | Orders | Replicates | Runs per model |
|---|---|---|---|---|---|
| `A_real` | original | the annotated frame sent live | `id_asc`, `id_desc` | 2 | 48 |
| `A_grey` (control) | original | neutral mid-grey (RGB 128) PNG, same size as the frame | both | 2 | 48 |
| `B_grey` | swapped | the same grey PNG | both | 2 | 48 |

- **Arm B swap.** `robot_1` and `robot_2` are exchanged in `scene.robots[*].robot_id`
  before `build_reasoner_request`. Positions, headings, statuses and velocities stay
  with the physical robot. The prompt builder then renders every label occurrence
  (state lines, geometry line, known IDs) from the swapped scene; nothing is
  string-replaced in the prompt. The obstacle block is unchanged. Under the swap the
  oracle-correct label flips; correctness is scored on the physical robot.
- **Why grey for B.** The annotated frame draws the original labels, which would
  contradict the swap. Raw frames do not exist for batch 1. Arm B therefore uses one
  image condition, grey, for all 12 scenes.
- **Why `A_grey`.** It holds the image constant across the label swap, so the
  label contrast is `A_grey` against `B_grey`. `A_real` is reported beside it and
  fills the real-frame cells; within `A_real`, the label and the blocker side are
  confounded as in all earlier data.
- Obstacle text is on in every arm.

Total: 144 `Reasoner.run` calls per model.

---

## Models

Each runs only if its provider's probe passes. Backends and configs are the existing
sections of `config/models.yaml`; no new backend is written.

| Order | `backend_id` | Model | Effective reasoner config (as shipped) |
|---|---|---|---|
| 1 | `gemini` | `gemini-robotics-er-2-preview` | shared block: max_attempts 2, re-ask on, no image fallback; max_tokens 2048; thinking_level low; temperature/top_p/top_k not sent (Interactions API has no such fields) |
| 2 | `openai` | `gpt-4o-2024-08-06` | temperature 0.0, max_attempts 4, grey fallback after 2 |
| 3 | `gemini_flash` | `gemini-3.8-flash` | max_attempts 4, grey fallback after 2, max_tokens 16384, thinking_level low; sampling not sent |
| 4 | `openai_gpt56sol` | `gpt-5.6-sol` | reasoning_effort none, temperature 0.0, max_attempts 4, grey fallback after 2 |
| 5 | `anthropic` | `claude-sonnet-5-5` | thinking between_tools, sampling not sent, max_attempts 4, grey fallback after 2 |

- The effective config (`describe_effective_sampling`), served model and git commit
  are recorded on every row.
- One design call is one `Reasoner.run` under the model's shipped retry policy.
  That is up to 2 (ER-2) or 4 (others) billed attempts.
- Expected Sonnet behaviour: `docs/reports/2026-10-06-roster-validation.md` found
  Sonnet 5.5 refuses this prompt family (91/96 attempts), locked to the `<think>`
  answer-format block, not the image. v1 carries that block. The prompt is not
  forked per model; the pilot stop rule below bounds the spend.

---

## Execution Order

1. **Probe** one minimal call per provider (OpenAI with gpt-4o, Gemini with ER-2,
   Anthropic with Sonnet): a short text prompt and a 64 x 64 grey PNG. These are paid
   and are logged in the ledger.
2. Per model, in the order above:
   1. **Pilot:** for each arm, 4 runs, replicate 1: west scene `53264de9` and east
      scene `61119197`, each under `id_asc` and `id_desc`.
   2. **Main:** the remaining runs, replicate 1 before replicate 2; within a
      replicate, scene by scene, then order, then arm. The pilot runs count towards
      the 48 per arm.
3. The run is resumable: a row whose key (`backend_id|arm|request_id|order|rep`) is in
   `calls.jsonl` is skipped.

---

## Stop Rules

- **Provider probe.** HTTP 401, 402, 403 or 429 on the probe: skip every model of that
  provider, record the status, continue with the others. No retry around it and no
  key or account switch.
- **Quota or credit during the batch.** HTTP 402, or HTTP 429 carrying a quota,
  billing, spend-cap or credit marker: stop that provider at once. A plain 429 that
  is still failing after the transient budget below is also treated as persistent
  and stops that provider.
- **Transient errors.** At most 2 transient failures (429, 5xx, timeout, connection)
  per run. After that, the recording proxy refuses further network calls in that run,
  and the run is recorded with its error. Retried calls are counted in the ledger.
- **Pilot rule (all models).** If 3 or more of an arm's 4 pilot runs end with no
  decision (terminal refusal, parse failure, error) or with `image_fallback_used`,
  that model's arm stops after the pilot and is reported as such.
- **Spend.** Before every run, the worst-case cost of that run is computed:
  `max_attempts x (3,000 input tokens, or the largest prompt seen, x input rate +
  max_tokens x output rate)`. The run is skipped if model ledger + worst case
  exceeds $3.00 or total ledger + worst case exceeds $10.00; the model, or the whole
  batch, then stops cleanly.

### Rates (per MTok, input / output; repo-recorded list prices)

| Model | Rate | Source |
|---|---|---|
| gpt-4o | $2.50 / $10.00 | `scripts/replay_live_decisions.py`, battery-v2 report |
| ER-2 | $1.00 / $5.00, thought tokens charged as output | battery-v2 report |
| gemini-3.8-flash | $0.75 / $3.75, thought tokens charged as output | `docs/reports/2026-10-07-hypothesis-arms.md` |
| gpt-5.6-sol | $4.00 / $20.00 (promotional, through at least 2026-11-21) | `docs/reports/2026-10-07-gpt56-sol-swap.md` |
| Sonnet 5.5 | $2.00 / $10.00 | `docs/reports/2026-10-06-roster-validation.md` |

An attempt with no recorded usage (error, timeout) is charged one worst-case attempt.

### Cost estimate

| Model | Basis | Expected |
|---|---|---|
| ER-2 | about $0.004 per run | about $0.60 |
| gpt-4o | about $0.0055 per attempt, about 1.3 attempts per run with real-frame refusals | about $1.00 |
| gemini-3.8-flash | about $0.01 per attempt including thinking | about $1.50 |
| gpt-5.6-sol | about $0.0065 per attempt | about $0.95 |
| Sonnet 5.5 | pilot 12 runs x up to 4 refused attempts x about $0.007 | about $0.35 if it stops at the pilot; about $1-4 if it answers |
| Probes | 3 tiny calls | under $0.01 |

Expected total about $4-6 against the $10.00 cap.

---

## Outcomes and Scoring

Per run the record holds: key, request id, scene, side, arm, order, replicate, model,
backend id, effective config, served model, image condition, fallback flag and
attempt, every attempt's raw text, refusal flag, tokens, latency and error, the
parsed final decision, attempt-1 decision, and the scoring fields below. No base64
image and no key material is stored.

- **Named yielder:** `decision.yield_robot` when non-null. Otherwise the outcome is
  one of `no_yielder` (a valid decision naming nobody; strategy recorded),
  `refusal` (terminal refusal), `parse_failure`, `error`.
- **Physical mapping.** Arm A: `robot_1` = west robot, `robot_2` = east robot.
  Arm B: `robot_1` = east robot, `robot_2` = west robot. Per row:
  `chosen_label`, `chosen_physical`, `first_listed_physical`, `correct_physical`,
  `robot1_physical`.
- **Primary outcome:** the final decision of the run. Denominator: all runs.
  `no_yielder`, refusals, parse failures and errors count as not correct and are
  tabulated, never dropped.
- **Secondary:** the attempt-1 decision only; and runs whose decision came after the
  image fallback, which are their own stratum.

### Tables per model

1. P(names the physically correct robot) in the 2 x 2 x 2 of blocker side x listing
   order x arm (`A_grey`, `B_grey`), with counts; the `A_real` 2 x 2 beside it.
2. The four label x slot combinations. For each run: does the label `robot_1` sit on
   the correct robot ("label right"), and is the correct robot listed first ("slot
   right")? In the grey pair, each combination holds 24 runs over all 12 scenes.
3. Three marginal effects over the 96 grey-pair runs (balanced by design, so 0.5 is
   no effect), among runs that name a yielder:
   - label effect: P(chosen robot carries the label `robot_1`);
   - slot effect: P(chosen robot is the first-listed one);
   - scene effect: P(chosen robot is the physically correct one).
   Also, per arm, P(chosen label = `robot_1`) in `A_grey` and in `B_grey`.
4. Every result also at scene level: per scene x arm x order, k/2 correct.

### Decision rules, stated in advance

- **Scene use is supported** for a model only if, in each of the four label x slot
  combinations of the grey pair, it names the physically correct robot in at least
  18 of 24 runs **and** in both replicates in at least 9 of the 12 scenes. This
  includes the combination where both label and slot point to the wrong robot.
  Otherwise scene use is not supported.
- **Label bias** toward `robot_1` (or `robot_2`) is supported if P(chosen label =
  `robot_1`) is at least 0.75 (or at most 0.25) among yield-naming runs in **both**
  `A_grey` and `B_grey`: the chosen label stays the same when the IDs are swapped.
- **Slot bias** is supported if P(chosen = first-listed) is at least 0.75 among
  yield-naming runs under **both** orders in the grey pair.
- **Real frame (secondary).** The same four-combination table is reported for
  `A_real` (12 runs and 6 scenes per combination; thresholds 9/12 runs and 4/6 scenes
  with 2/2). Because label and side are confounded there, passing it shows scene use
  OR a side preference, not scene use alone.
- A model whose arm stopped at the pilot, or which has fewer than 20 runs with a
  decision in an arm, gets "not assessable" for any rule needing that arm.

---

## Exclusions

None after the run. Every run appears in `calls.jsonl` and in the counts. A stimulus
would be excluded only if its prompt failed the SHA check at its stored order before
the run (none did).

---

## Differences From the Re-Score Proposal

- Arm B uses a grey image for all 12 scenes, not raw frames for batch 2 and grey for
  batch 1, so that Arm B has one image condition; the `A_grey` control is added.
- Every model receives prompt v1 (what the scenes ran live), not the prompt version
  each model ran live. One prompt builder and one prompt for all models.
- gpt-4o is in Arm A as well as Arm B. The remaining four models of the re-score
  (gpt-5.1, glm, molmo2-er, qwen3-vl, deepseek-flash) are not run.

---

## Amendments

### Amendment 1 (2026-11-14, owner: "shorten the model api test list, choose the candidates")

Recorded mid-run. At that point ER-2 had completed all 144 runs and gpt-4o 120 of
144; no run of any other model had started. The session lead's list was ER-2,
gpt-4o and gpt-5.6-sol. The batch process was stopped between two runs, with no call
in flight. It was superseded before any further call by amendment 2.

### Amendment 2 (2026-11-14, owner correction: one model per provider)

Final model list, replacing the "Models" table for the verdict:

| Provider | `backend_id` | Model |
|---|---|---|
| Google | `gemini` | `gemini-robotics-er-2-preview` |
| OpenAI | `openai` | `gpt-4o-2024-08-06` |
| Anthropic | `anthropic` | `claude-sonnet-5-5` |

- `gemini_flash` and `openai_gpt56sol` are dropped. Neither had a single run when
  they were dropped, so no partial rows exist for them.
- The Anthropic probe was made before the first run (HTTP 200, `probes.jsonl`). It
  is not repeated.
- **Sonnet real-frame stop.** After Sonnet's 4 `A_real` pilot runs, `A_real` stops if
  any of them used the image fallback (stricter than the general pilot rule). If it
  fires, the cause is investigated offline from the recorded rows and the code, with
  no extra spend and no change to runtime backend code. Sonnet's grey arms still run,
  each under the general pilot rule. The report states which Sonnet cells exist.
- Execution: gpt-4o's 24 remaining runs, then Sonnet. Caps, rates, scoring and
  decision rules are unchanged.

### Amendment 3 (2026-11-14, owner: "add the image-only cell, inspect the sonnet first")

Recorded before any Sonnet design run and before any Cell C or D call. At this point
ER-2 had 144/144 runs, gpt-4o 133/144, Sonnet 0.

**Sonnet inspection (done first).**

- Recorded artifacts: the 26 Sonnet decisions of `roster_validation/runs/rv01_sonnet_ho_s42`
  and `rv02_sonnet_ho_s43` (`w0p2_eopen_bshort`). All 26 carry
  `refusal_category = reasoning_extraction`. 24 used the fallback: 21 ended
  `failed` and 3 `invalid`. Of the other two, one was `invalid` without fallback and
  one `valid`.
- Code path: `Reasoner.run` (`reasoning/vlm/reasoner.py:487-496`) treats
  `BackendResponse.refusal` as a parse failure. At lines 526-536 a refusal on attempt
  >= `image_fallback_after_attempts` (2 for `anthropic`) swaps in the neutral image
  (`_should_fall_back`, lines 588-599). The fallback fires **only** after a
  refusal. `AnthropicBackend` sets `refusal = stop_reason == "refusal"`
  (`reasoning/vlm/anthropic_backend.py:145-146`) and sends the frame as a base64
  `image/png` block (lines 164-185).
- Three diagnostic calls (`sonnet_diagnostic.jsonl`; outside every table) on
  `53264de9`, `id_asc`, real frame, obstacle text on:
  - image sent: PNG 1280 x 960, 681,362 bytes, base64 908,484 characters;
  - 3/3 HTTP 200, `stop_reason: refusal`, category `reasoning_extraction`;
  - 3,019 input tokens and 0 output tokens billed per call.
- Cause: (a), a model refusal, not a harness or request artefact. The image is
  delivered within limits and the provider answers with a documented refusal. The
  trigger is the `<think>` answer-format block of the prompt
  (`docs/reports/2026-10-06-roster-validation.md`: removing it lifted the refusal
  3/3), not the image. The fallback is the shipped mitigation reacting to those
  refusals.
- Consequence: the amendment-2 Sonnet stop-on-any-fallback is **withdrawn**. Sonnet's
  real-frame cells run, and fallbacks and refusals are counted per run as data.
  Every Sonnet arm stays under the general pilot rule (stop after the 4 pilot runs if
  3 or more end with no decision or used the fallback). Sonnet's grey arms run under
  the same rule.

**Cell C, "image only", and Cell D, "states only".**

| Cell | IDs | Image | Obstacle text | Orders | Replicates | Runs per model |
|---|---|---|---|---|---|---|
| `C_real_notext` | original | annotated frame | off | both | 2 | 48 |
| `D_grey_notext` | original | grey | off | both | 2 | 48 |

- Text off uses the September switch: `include_static_obstacles=False` in
  `reconstruct_request` (the replay's `obstacle_text` factor). Checked on all 12
  stimuli: the rendered prompts contain no obstacle line, no `1.85`, and the word
  "obstacle" nowhere. After masking every decimal number, the 12 prompts are
  byte-identical within each order. So in Cell C the only thing that tells a
  west-blocked scene from an east-blocked one is the image (plus pose decimals).
- Frames: on a 12-frame contact sheet, the blocker (a light-grey box with its
  shadow) is visible to a human in **12 of 12** frames, on the side the oracle
  states: left in the 6 west-blocked frames, right in the 6 east-blocked ones. No
  scene is excluded from the image-use test.
- Same pilot cells, pilot rule, scoring (physical robot, all-runs denominator) and
  caps as the other arms.
- **Question:** can the correct yielder be read from the image alone?
- **Decision rule, stated before the first Cell C call.** "Image use" is supported
  for a model only if both hold:
  - in Cell C, in each of the four side x order cells, it names the physically
    correct robot in at least 9 of 12 runs, with both replicates correct in at least
    4 of the 6 scenes;
  - its Cell C overall P(correct) exceeds its own Cell D overall P(correct) by at
    least 0.25 (absolute; both over 48 runs).

  Otherwise image use is not supported. A model whose Cell C or D arm stopped at the
  pilot, or which has fewer than 20 decisions in either, is "not assessable".
  Counts only, call and scene level.
- **Budget priority:** Arms A and B for all three models, then Cell C for all three,
  then Cell D. The run stops cleanly at the cap; anything not run is reported.

---

## Outputs

- `data/experiments/2026-11-14-head-on-swapped-id-replay/calls.jsonl` (tracked, like
  the September experiments), `ledger.jsonl` (running spend), `probes.jsonl`,
  the grey image, and the analysis output.
- `scripts/replay_swapped_ids.py`, unit tests in
  `tests/unit/test_replay_swapped_ids.py` (offline, mocked backend).
- Report: `docs/reports/2026-11-14-head-on-swapped-id-replay-results.md`.

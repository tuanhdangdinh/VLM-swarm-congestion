# Capability-Probe Battery: Live Baseline Results

**Prepared:** 2026-10-04

**Revision history:**

- Initial draft: wired the runner to the pinned models, ran the frozen
  battery once per backend (Gemini ER-2 first, then gpt-4o), and scored the
  results. These are the pre-collection baseline runs the v2 freeze cites.

---

## Summary

This report covers prereg-v2 build-order step 10's live runs
(`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, "Capability-probe
battery"). It also covers freeze-time follow-up (a), the model pin, and
records the numbers for follow-up (c). Follow-up (b), the owner's
confirmation of the left/right operationalization, is still open and is
not decided here.

| Backend (served model) | Overall | locate_robot | left_right | robot_count | nearest_first | Refusals |
|---|---|---|---|---|---|---|
| Gemini ER-2 (`gemini-robotics-er-2-preview`) | 60/60 | 15/15 | 15/15 | 15/15 | 15/15 | 0/60 |
| gpt-4o (`gpt-4o-2024-08-06`) | 58/60 | 15/15 | **13/15** | 15/15 | 15/15 | **0/60** |

Headline findings:

- **The battery is at its ceiling.**
  - Gemini ER-2 scored 15/15 on all four primitives.
  - gpt-4o scored 15/15 on three of them, every type except `left_right`.
  - At n=15, a perfect score's Wilson 95% lower bound is 0.796.
  - The battery shows that neither backend has a primitive deficit below
    roughly 80% on these frames.
  - It cannot rank the two backends against each other.
- **The only errors are gpt-4o's 2 misses on `left_right`.** Both have the
  same profile:
  - the robot is among the six closest to the centre line (margins 0.46 m
    and 0.64 m);
  - the chosen answer was letter A, listed first.
- **gpt-4o refused 0 of 60 calls on real annotated frames.** The project's
  record for the congestion prompt is 19–38% refusals. The difference is
  analysed under "Refusal Analysis" below.
- **The `nearest_first` prior question is settled for this battery.**
  - Both backends answered correctly on all 8 items where `robot_1` was
    offered but wrong.
  - Both answered correctly on all 5 items where the first-listed option
    was wrong.
  - Neither the robot_1 prior nor the first-slot prior shows up.
- **The LRR-Bench "near-chance left/right" expectation is not reproduced.**
  The question this battery asks matches LRR-Bench's basic *Position* task.
  The paper's own Tables II and III show GPT-4o scoring 78–80 there,
  against 95 for humans. LRR-Bench's near-chance results come from its
  composite-position and 3D movement tasks (see the "left_right vs
  LRR-Bench" section below).
- **API spend: about $0.25 in total** (Gemini $0.104, gpt-4o $0.141,
  preflights about $0.003). The $10 stop threshold was never in play.

---

## Frozen Inputs (Quoted for the Freeze Record)

| Input | Pin |
|---|---|
| Manifest | `reasoning/vlm/capability_probes/manifest_v1.json`, SHA-256 `9659782d710a5c286b420fe17e256d8045eac3459638a4714b8757f51b34dbdb`, last changed in `0d2e667`, seed `20261002`, 60 items (15 per type) |
| Prompt version | `CAPABILITY_PROBE_PROMPT_VERSION = 1` |
| Prompt template SHA-256 | `b1af71e8e4bc4000bf8dc05aab31282517d8ed50b46929fe25d64fa9a69397df` |
| System prompt SHA-256 | `bdbf03f8f1325e50bdb821bf509d031999dd17430fe3bd9ea422ddc046356d24` |
| Rendered fixtures | text-choice `841728fb…`, image-choice `5c572948…` (`tests/unit/test_capability_probe_prompt.py`) |

The manifest and prompt were not edited or regenerated. All four prompt pin
tests pass on the branch. Before any call was made, all 60 frames were
re-materialized from the main checkout's `data/logs/vm_runs/` and checked:
`scripts/audit_capability_probe_manifest.py --logs-root …` printed
`OK: all 60 items passed every check`, with no missing or drifted frame.
`run_battery` repeats the hash check for every item before it builds the
backend.

---

## Run Configuration

| Field | Gemini | gpt-4o |
|---|---|---|
| Configured `model_id` (from `config/models.yaml`) | `gemini-robotics-er-2-preview` | `gpt-4o-2024-08-06` |
| Served model (per call, from the response) | `gemini-robotics-er-2-preview` ×60 | `gpt-4o-2024-08-06` ×60 |
| temperature | 0.0 configured, **dropped by the API** (no field), recorded per call in `unsupported_sampling` | 0.0 |
| top_p / max_tokens | 0.95 dropped / 2048 | 0.95 / 2048 |
| thinking_level | `low` | n/a |
| Attempts per item | 1 (runner policy; no re-ask, no grey-image fallback) | 1 |
| Pacing | ≥3 s between call starts | ≥3 s |
| Run directory (gitignored) | `data/logs/capability_probes/gemini_20261003T201320Z/` | `data/logs/capability_probes/openai_20261003T201935Z/` |
| Wall time | 370 s | 281 s |

The run stamps are UTC, which is why they read 2026-10-03; local time was
2026-10-04. Each directory holds:

- the per-item JSONL;
- `*_summary.json`, which includes the `reasoner_config_effective` block,
  `served_model_counts`, `manifest_sha256` and `prompt_version`;
- the grid-overlay copies;
- the runner's stdout and stderr.

A scan of every output file for key prefixes, base64 PNG headers and
`data:image` returned no matches.

The shipped openai reasoner block configures `max_attempts: 4` and
`image_fallback_after_attempts: 2`. These are deliberately **not** applied.
They act only inside `Reasoner`, and the battery calls `backend.analyze`
once per item. The summary's effective block therefore records
`max_attempts: 1` and `image_fallback_after_attempts: null`.

### Preflight

Before the battery, one minimal call went to each backend through
`build_backend`, configured by `load_backend_settings`:

- **Stimulus:** a 1280×960 neutral-grey PNG and a two-option colour question,
  not a manifest item.
- **Gemini:** served `gemini-robotics-er-2-preview`, answered
  `{"choice": "A"}` correctly, used 1099 input tokens, 11 output tokens and
  22 thought tokens.
- **gpt-4o:** served `gpt-4o-2024-08-06`, answered correctly, used 809 input
  and 10 output tokens.

The OpenAI account had credit (memory had recorded credits exhausted on
2026-09-25).

---

## Accuracy per Backend and Probe Type

All CIs are Wilson 95% intervals (`reasoning/vlm/capability_probes/scorer.py`).

### Gemini ER-2

| Probe type | Correct | Accuracy | Wilson 95% CI | Chance | Failure causes |
|---|---|---|---|---|---|
| locate_robot | 15/15 | 100% | [0.796, 1.000] | 0.111 | none |
| left_right | 15/15 | 100% | [0.796, 1.000] | 0.500 | none |
| robot_count | 15/15 | 100% | [0.796, 1.000] | 0.200 | none |
| nearest_first | 15/15 | 100% | [0.796, 1.000] | 0.478 | none |
| **overall** | 60/60 | 100% | [0.940, 1.000] | | |

### gpt-4o

| Probe type | Correct | Accuracy | Wilson 95% CI | Chance | Failure causes |
|---|---|---|---|---|---|
| locate_robot | 15/15 | 100% | [0.796, 1.000] | 0.111 | none |
| left_right | 13/15 | 87% | [0.621, 0.963] | 0.500 | none (2 valid but wrong letters) |
| robot_count | 15/15 | 100% | [0.796, 1.000] | 0.200 | none |
| nearest_first | 15/15 | 100% | [0.796, 1.000] | 0.478 | none |
| **overall** | 58/60 | 97% | [0.886, 0.991] | | |

### Per-Stratum Breakdown

| Stratum | Gemini | gpt-4o |
|---|---|---|
| `robot_count`, true count 2 / 3 / 4 | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 |
| `locate_robot`, cell 1 / 3 / 4 / 5 | 3/3, 4/4, 4/4, 4/4 | 3/3, 4/4, 4/4, 4/4 |
| `left_right`, correct = left / right | 7/7, 8/8 | 6/7 [0.49, 0.97], 7/8 [0.53, 0.98] |

---

## Refusal and Parse-Failure Analysis

### Refusal and Parse-Failure Classification

The runner tags refusals before it parses the answer:

1. If `reasoning.vlm.reasoner.is_refusal` matches the text, the record is
   tagged `failure_cause="refusal"`.
2. Otherwise the text goes to `parse_probe_answer`, which returns
   `empty_response`, `parse_failure` or `invalid_letter`.
3. A transport exception becomes `backend_error`, with `error_type` and
   `error_message`.

The existing test
`test_a_refusal_is_tagged_separately_from_a_parse_failure` covers this
split, so no new classification was needed. `is_refusal` is shared M2
behaviour and was left unchanged.

The phrase matching has one known gap. OpenAI's structured
`message.refusal` field reaches the runner only as text (`OpenAIBackend`
falls back to it when `content` is null). A structured refusal in a new
phrasing would therefore be tagged `parse_failure`. This did not happen in
this run: every one of the 120 responses parsed to a valid letter.

### Observed Refusal and Failure Counts

| Backend | refusal | parse_failure | empty_response | invalid_letter | backend_error |
|---|---|---|---|---|---|
| Gemini | 0/60 | 0 | 0 | 0 | 0 |
| gpt-4o | **0/60** (Wilson upper bound 0.060) | 0 | 0 | 0 | 0 |

Both backends wrapped their JSON in a fenced ```` ```json ```` block, and
the parser read it correctly every time.

### gpt-4o Refusals Against the Project's History

The project has measured gpt-4o refusals on realistic annotated frames at
19–38% of first attempts (`docs/reports/2026-09-25-frame-replay.md`,
`docs/reports/2026-09-25-gpt4o-refusals.md`). In this battery, gpt-4o
refused none of 60 single attempts on real annotated M1 frames: 45 raw
frames, plus 15 with the grid overlay. The upper bound of 6% sits below the
historical range.

This does **not** show that the frame alone is harmless. Two things changed
together, and the battery cannot separate them:

1. **The task text.** The probes ask neutral visual questions with a closed
   answer set. The congestion prompt asks the model to decide robot
   commands.
2. **The frame distribution.** The manifest's legibility filters keep only
   frames with robots ≥70 px apart, edge-clear, with no STALE robots and no
   overlapping labels. Congestion-onset frames are the opposite: robots
   close together, boxes touching.

What the result does establish is narrower. On this battery, refusal does
not confound the gpt-4o numbers, so the gpt-4o and Gemini columns can be
compared directly.

---

## Answer-Letter Distributions (Position-Bias Check)

Letters and listing order are drawn per item from independent seeded
streams (`letters.py`), so neither letter A nor the first-listed option is
tied to the correct answer.

| Probe type | Correct letters | Gemini answered | gpt-4o answered |
|---|---|---|---|
| robot_count | A3 B3 C2 D6 E1 | identical to correct | identical to correct |
| locate_robot | A2 B1 C4 D2 E3 H2 I1 | identical to correct | identical to correct |
| nearest_first | A8 B7 | identical to correct | identical to correct |
| left_right | A6 B9 | identical to correct | **A8 B7** |

| Probe type | First-listed option correct | Gemini chose first-listed | gpt-4o chose first-listed |
|---|---|---|---|
| robot_count | 3/15 | 3/15 | 3/15 |
| locate_robot | n/a (image choices) | n/a | n/a |
| nearest_first | 10/15 | 10/15 | 10/15 |
| left_right | 6/15 | 6/15 | **8/15** |

**Gemini** shows no letter or slot bias. Its answers match the correct
distribution exactly, because it scored 60/60.

**gpt-4o** departs only on `left_right`, and both of its errors fall the
same way. Both error items listed letter A first, and gpt-4o answered A,
the first-listed option, on both. The items list options in two orders:
9 list A first and 6 list B first. Counted either way, the result is the
same. Letter A was wrong on 9 items and the first-listed option was wrong
on 9 items, and gpt-4o chose it 2 times out of 9 in each case. That is
2/9, Wilson CI [0.06, 0.55].

The direction is the same as the project's recorded gpt-4o first-slot prior
(`docs/reports/2026-09-25-presentation-order-probe.md`). Two events cannot
establish a bias: the interval includes values far below a coin flip. They
are logged as consistent with that prior, not as evidence for it.

---

## nearest_first: Prior vs Spatial Attribution (Follow-up (c))

The manifest's `nearest_first` answers lean toward robot_2. The correct
answers are robot_1 ×4, robot_2 ×7, robot_3 ×2 and robot_4 ×2, from 5
scenes. The spec asks that errors on this type be checked against the
project's recorded priors before they are blamed on spatial reasoning:

- the gpt-4o robot_1 prior;
- the first-slot prior.

In the breakdown below, a perfect score on a row means the model answered
against that prior on every item where the prior was wrong.

| Breakdown | Gemini | gpt-4o |
|---|---|---|
| Correct = robot_1 | 4/4 [0.51, 1.00] | 4/4 [0.51, 1.00] |
| Correct = robot_2 | 7/7 [0.65, 1.00] | 7/7 [0.65, 1.00] |
| Correct = robot_3 | 2/2 [0.34, 1.00] | 2/2 [0.34, 1.00] |
| Correct = robot_4 | 2/2 [0.34, 1.00] | 2/2 [0.34, 1.00] |
| robot_1 offered (12 items): chose robot_1 | 4/12 (= the 4 where it is correct) | 4/12 (= the 4 where it is correct) |
| robot_1 offered but wrong (8 items): chose robot_1 | 0/8 [0.00, 0.32] | 0/8 [0.00, 0.32] |
| First-listed option wrong (5 items: `_003`, `_006`, `_009`, `_010`, `_013`) | 5/5 correct | 5/5 correct |
| Lowest-id option chosen | 7/15 (= the 7 where it is correct) | 7/15 (= the 7 where it is correct) |

For this battery, neither prior can explain the `nearest_first` answers.
Every pick follows the ground truth, including the 8 items that set
robot_1 against the correct answer and the 5 that set the first-listed slot
against it.

The robot_2 lean therefore needs no further attribution here. It would have
mattered only if errors had appeared. It still bounds what the result
generalizes to: 5 scenes, at most 3 candidates per item, and a 0.3 m
nearest-vs-second-nearest margin enforced by the builder
(`ground_truth.NEAREST_FIRST_MARGIN_M`).

---

## left_right vs LRR-Bench

**The expectation.** The spec motivates the left/right probe with
"published benchmarks put left/right discrimination near chance
(LRR-Bench)" (arXiv:2507.20174).

**The result.** Neither backend shows near-chance left/right
discrimination:

| Backend | Score | Wilson 95% CI |
|---|---|---|
| Gemini | 15/15 | [0.80, 1.00] |
| gpt-4o | 13/15 | [0.62, 0.96] |

Both lower bounds are above 0.5. That clears chance, but the claim is
modest: at n=15 the interval is roughly ±17 pp.

**Why this is not a contradiction.** The battery's operationalization
(owner confirmation pending, follow-up (b)) asks which image half of a
top-down frame a labelled robot is in. That corresponds to LRR-Bench's
*absolute position* category, specifically its basic "Position" task,
which asks where an object is in the image (centre, top-left and so on).
The paper's own results, checked against the primary source
(arxiv.org/html/2507.20174v1, Tables II and III), point the same way:

- The paper says that for absolute position, "only the simplest task
  Position achieves a score close to humans".
- It says models "score close to zero on all 3D spatial understanding
  tasks except for the task Depth".
- On Position, GPT-4o scores 78.0 when it reasons first and 80.0 when it
  answers directly. Humans score 95.0, and the best models (Qwen2.5) reach
  92.

So the near-chance and near-zero results in LRR-Bench belong to its
composite position tasks (Position Combination, Position Sequence) and its
3D tasks (camera and object movement, rotation, heading). The battery does
not probe any of these. A gpt-4o score of 13/15 (87%) on a single-object,
two-way image-half question sits in the same range as its LRR-Bench
Position score.

**Wording fix (for the freeze owner).** The spec should cite LRR-Bench for
**composite-position and movement/heading** deficits, not for basic
left/right. It currently says "published benchmarks put left/right
discrimination near chance" in the "Capability-probe battery" block, and
"near-chance left/right discrimination results" in the marked-choice-rule
paragraph. Both overstate the paper for the question this battery asks.

The "best model only 55.33%" figure in
`research_notes/VLM centralized multi robot coordination/vlm_scene_coordination.md`
does not appear anywhere in the v1 HTML (a string search for `55.33`
returned nothing). It may come from a later version or a different
aggregate, and it should be re-sourced before anyone quotes it. This
report does not edit the spec.

### gpt-4o's Two Misses

Both misses are on the near-boundary end of the margin distribution.
Margins are the GT world-x distance from the centre-column line, recomputed
with the audit script's own loaders. Across the 15 items they range from
0.34 m to 2.45 m. All items clear the registered 0.30 m bound.

| Item | Scenario | Robot | Correct | gpt-4o | Margin | Margin rank (of 15) |
|---|---|---|---|---|---|---|
| `left_right_004` | `priority_urgent_r1` | robot_2 | right | left (A, first-listed) | 0.46 m | 2 (tied) |
| `left_right_009` | `alternative_seed43` | robot_1 | left | right (A, first-listed) | 0.64 m | 6 |

The rendered frames suggest a further pattern:

- In both frames, the named robot sits inside the aisle section bounded by
  the yellow barriers, close to the centre line.
- In both, its velocity arrow points across that line, toward the half the
  model chose.

With n=2, this is a hypothesis for the v2 analysis, not a finding.
Candidate explanations:

- a heading-arrow cue;
- the first-slot prior;
- near-boundary difficulty.

Gemini answered both items correctly.

---

## Interpretation Caveats for the Freeze

- **Ceiling.** On three of four probe types the battery cannot tell the
  two backends apart, because both scored 15/15. On the fourth,
  `left_right`, their intervals overlap. With 15/15, all we can say is that a primitive's
  accuracy is very probably ≥80% on clean frames.
- **Frames are clean by construction.** Every item passed the builder's
  legibility, occlusion, M1-vs-GT-agreement and margin filters. The
  battery measures primitives on legible frames. It does not measure them
  on the crowded, touching-box frames typical at congestion onset.
- **Follow-up (c) coverage limits:**
  - `locate_robot` covers only 4 of the 9 grid cells (1, 3, 4, 5), so
    perfect scores say nothing about the corner cells or bottom-row cells
    0, 2, 6, 7, 8.
  - `nearest_first` comes from 5 scenes, with the robot_2 lean noted above.
- **What the battery means for v2 plan-metric failures.** It is the
  instrument for pinning plan-metric failures on primitive deficits.
  - On its evidence, plan-metric failures in v2 cannot be blamed on
    inability to count, locate, or order robots by distance in legible
    frames, for either backend.
  - gpt-4o's left/right near the centre line is the one primitive with a
    measured (small, wide-CI) gap.
- **Gemini temperature.** Gemini's decoding is not temperature-controlled.
  The API has no such field: the configured 0.0 was dropped and the drop
  recorded per call. Gemini's 60/60 is therefore a single draw at the
  provider's default sampling, with `thinking_level: low`.
- **Latency.** Latency is not recorded per call (`latency_ms` is null).
  Neither hosted backend fills `BackendResponse.latency_ms`, and only
  `Reasoner` times calls. Per-call latency would need runner-side timing;
  wall times are given in the run configuration table.

---

## API Spend

Prices are list prices per 1M tokens, as of 2026-10-04:

- gpt-4o-2024-08-06: $2.50 input, $10.00 output.
- Gemini Robotics-ER 2 preview: $1.00 input, $5.00 output, with thought
  tokens billed as output (ai.google.dev pricing page).

| Backend | Input tokens | Output tokens (incl. thought) | Cost |
|---|---|---|---|
| Gemini | 71,641 | 6,421 | $0.104 |
| gpt-4o | 54,061 | 536 | $0.141 |
| Preflights (2 calls) | 1,908 | 43 | ≈$0.003 |
| **Total** | | | **≈$0.25** |

Before the runs, the projection from the preflight token counts was about
$0.15 per backend. The stop threshold was $10.

---

## Code Changes

Commit `7ba1170`, on `feat/v2-probes-live`:

- `scripts/capability_probes.py`:
  - **Model pin.** New `load_backend_settings` routes `openai`/`gemini`
    through `resolve_reasoner_config` and `backend_section`, following the
    `scripts/probe_presentation_order.py` precedent, with temperature
    forced to 0.0.
  - **Effective-config record.** `run_battery` builds the backend from the
    pinned config and records `reasoner_config_effective` with
    `max_attempts: 1`.
  - **Pacing.** New `--min-interval-sec`, which spaces calls out and never
    retries.
  - **Fatal-error abort.** The run stops with `BatteryAbortedError` on
    auth or exhausted-quota errors, writing the partial records to
    `*_aborted.jsonl` first. HTTP 429 rate limits are still scored, not
    aborted.
  - **Record keying.** `backend_id` is now always the selector (previously
    the model id on success).
- `reasoning/vlm/capability_probes/models.py`, additive optional fields:
  - `ProbeAnswerRecord` gains `configured_model_id`, `served_model`,
    `token_usage`, `unsupported_sampling`, `parsed_option`,
    `option_by_letter` and `listing_order`.
  - `ProbeRunSummary` gains `reasoner_config_effective`,
    `served_model_counts`, `manifest_sha256` and `prompt_version`.
- `tests/unit/test_capability_probes_runner.py`: 14 new tests.
  - Real `config/models.yaml` pins for both backends.
  - Temperature 0.
  - Mock-backed `run_battery` wiring, with `build_backend` monkeypatched
    to capture the config.
  - Served model and usage recorded.
  - Gemini's dropped sampling recorded.
  - Lettering recorded.
  - Quota abort vs scored rate limit.

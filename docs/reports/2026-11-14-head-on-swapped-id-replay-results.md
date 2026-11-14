# Head-On Swapped-ID Replay - Results

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: results of the pre-registered offline replay (design `docs/superpowers/specs/2026-11-14-head-on-swapped-id-replay-design.md`, Rev 3), Arms A and B plus the amendment-3 Cells C and D, for Gemini ER-2, gpt-4o and Claude Sonnet 5.5.

---

## Question and Answer

**Question.** On the 12 head-on asymmetric standoff scenes, does any current model
choose the oracle-correct yielder from the scene (the blocker side) rather than from
a preference for the label `robot_1` or for the first-listed robot?

**Answer.** No. None of the three models meets the pre-registered "scene use" rule.
None meets the "image use" rule. The models fail in three different ways:

- **gpt-4o** follows the first-listed slot (85/96 grey-pair runs that name a yielder
  pick the first-listed robot). Its `robot_1` preference does not survive the ID swap
  (P(`robot_1`) 33/48 with original IDs, 24/48 with swapped IDs). Removing the
  obstacle text and showing only the frame changes nothing (26/48 correct against
  24/48 with neither text nor image).
- **ER-2** mostly does not name a yielder: `reverse` in 129 of 144 Arm A/B runs. Its
  few named yielders are always `robot_1` in the grey arms (8/8). In Cell C (frame
  without obstacle text) it named a yielder in 11 of 48 runs, and 10 of those 11 were
  correct. That is the only scene-consistent signal in the data, but it rests on 11
  runs and fails the pre-registered rule.
- **Sonnet 5.5** refuses (`reasoning_extraction`) most calls on this prompt: 30/48
  real-frame runs, and 14 of 16 pilot runs in the other arms. Every arm except
  `A_real` stopped at its pilot, so its rules are not assessable. In its 18 answered
  real-frame runs it named the correct robot 10 times.

**Evidence grade:** a small designed offline experiment, pre-registered before the
first paid call, with three dated amendments made mid-run (all listed below). It
uses 12 scenes from one scenario family at seed 42, two robots, first decision only,
no execution. Counts only; no p-values and no intervals. These rows are a new stratum,
never pooled with the September replays or live runs.

---

## Design as Frozen

The full design is in the spec. In short:

| Item | Value |
|---|---|
| Stimuli | 12 SHA-verified standoff artifacts from the 2026-09-25 pilots: 6 west-blocked (correct = east robot) and 6 east-blocked (correct = west robot). Prompt v1, no goals, no failure context. |
| `A_real` | original IDs, annotated frame, obstacle text on |
| `A_grey` | original IDs, grey image (1280 x 960, RGB 128), obstacle text on |
| `B_grey` | `robot_1` and `robot_2` exchanged in `scene.robots[*].robot_id`, grey image, obstacle text on |
| `C_real_notext` (amendment 3) | original IDs, annotated frame, obstacle text off |
| `D_grey_notext` (amendment 3) | original IDs, grey image, obstacle text off |
| Per arm | 12 scenes x 2 orders (`id_asc`, `id_desc`) x 2 replicates = 48 runs |
| One run | one `Reasoner.run` under the model's shipped retry policy (ER-2: 2 attempts, no fallback; gpt-4o and Sonnet: 4 attempts, grey-image fallback after 2) |
| Scoring | on the physical robot (west or east spawn); `no_yielder`, refusals, parse failures and errors count as not correct |
| Pilot rule | per model and arm: 4 runs (scenes `53264de9` and `61119197`, both orders); the arm stops if 3 or more end with no decision or used the fallback |

**Pre-stated rules:**

- **Scene use:** in each of the four label x slot combinations of the grey pair,
  at least 18/24 runs correct **and** both replicates correct in at least 9/12 scenes.
- **Label bias:** P(chosen = `robot_1`) is at least 0.75 (or at most 0.25) among
  yield-naming runs in both `A_grey` and `B_grey`.
- **Slot bias:** P(chosen = first-listed) is at least 0.75 among yield-naming runs
  under both orders in the grey pair.
- **Image use (amendment 3):** in Cell C, at least 9/12 runs and 4/6 scenes with 2/2
  correct in each side x order cell, **and** P(correct) in C minus P(correct) in D is
  at least 0.25.
- An arm with fewer than 20 decisions is "not assessable".

**Checks done before any call:**

- **ID swap.** Under the swap, the `id_asc` prompt equals the original `id_desc`
  prompt with the labels exchanged, and vice versa. The obstacle lines are
  unchanged. Only `robot_id` changes in the scene. This is tested in
  `tests/unit/test_replay_swapped_ids.py` (22 offline tests with a mocked backend).
  The 130 existing replay and prompt tests also pass.
- **Text off (Cell C).** On all 12 scenes, the rendered prompt has no obstacle line,
  no `1.85` and no "obstacle". After masking every decimal, the 12 prompts are
  byte-identical within each order. So the image is the only side cue apart from the
  pose decimals.
- **Frames.** On a contact sheet of the 12 annotated frames, the blocker (a
  light-grey box) is visible in **12 of 12**, on the oracle side. No scene had to be
  excluded from the image test.

---

## Deviations

Each was recorded at the time it happened, in the spec's "Amendments" section or
here.

1. **Worktree.** The work ran in `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-swapid`
   (branch `exp/head-on-swapped-id-replay`, created from `docs/head-on-vlm-vs-rule`),
   not in `vgu-vlm-swarm-v7e`. At 20:14:56 another session checked out `main` in the
   v7e worktree, about 4 minutes after this branch was created there. A separate
   worktree on the same branch avoided a clash.
2. **Model list (amendments 1 and 2, owner instructions).** The designed list had
   five models. It was cut to one model per provider: ER-2, gpt-4o and Sonnet 5.5.
   `gemini-3.8-flash` and `gpt-5.6-sol` were dropped before either had a single run,
   so there are **no partial rows** for them. At the cut, ER-2 had 144/144 runs and
   gpt-4o 120/144. The batch was stopped between two runs, with no call in flight
   (ledger rows = 3 probes + 264 runs).
3. **Cells C and D (amendment 3, owner instruction).** They were added after Arms A
   and B were designed, and committed before their first call. The order was A/B for
   all models, then C, then D.
4. **Sonnet stop rule.** Amendment 2 added "Sonnet `A_real` stops on any fallback".
   Amendment 3 withdrew it after the inspection below found the fallback to be the
   shipped response to model refusals. Sonnet then ran under the general pilot rule
   only.
5. **OpenAI key.** The coordinator reported that the OpenAI key was replaced at about
   13:16 UTC. All probes ran after that, and the OpenAI probe returned HTTP 200 on its
   first try, so no probe failed and nothing needed a re-probe.
6. **Probe code fix.** The first probe attempt crashed before any network call
   (`PromptPayload` needs `known_robot_ids`). Fixed in `fe60cfe`, before any paid
   call.
7. **Prompt version.** Every model saw prompt v1, the version the scenes ran live.
   The re-score had proposed each model's own live prompt version.
8. **Sonnet diagnostics.** Three extra Sonnet calls were made by direct backend calls
   (`sonnet_diagnostic.jsonl`). They are outside every table, and their $0.018 is in
   the ledger.

---

## Results per Model

Run-level counts. "2/2 scenes" means scenes where both replicates were correct.
Primary outcome: the final decision of the run. Attempt-1-only tables are in
`analysis.txt`; they change no verdict (see Refusals and Fallbacks).

### gpt-4o (`gpt-4o-2024-08-06`, 240 runs, all served as that snapshot)

P(names the physically correct robot), runs [scenes 2/2 of 6]:

| Blocker | Order | `A_real` | `A_grey` | `B_grey` | `C_real_notext` | `D_grey_notext` |
|---|---|---|---|---|---|---|
| west | `id_asc` | 0/12 [0] | 0/12 [0] | **12/12 [6]** | 0/12 [0] | 0/12 [0] |
| west | `id_desc` | 6/12 [3] | 5/12 [1] | 1/12 [0] | 7/12 [3] | 5/12 [1] |
| east | `id_asc` | 12/12 [6] | 12/12 [6] | **1/12 [0]** | 12/12 [6] | 11/12 [5] |
| east | `id_desc` | 4/12 [1] | 2/12 [0] | 12/12 [6] | 7/12 [2] | 8/12 [3] |

The swap moves the correct answer exactly where the slot points. West `id_asc` goes
from 0/12 to 12/12, and east `id_asc` from 12/12 to 1/12. The model follows the
first-listed robot, not the blocked side.

Grey pair, label x slot combinations (24 runs and 12 scenes each):

| Label `robot_1` on the correct robot? | Correct robot listed first? | Correct | Scenes 2/2 |
|---|---|---|---|
| yes | yes | 24/24 | 12/12 |
| yes | no | 3/24 | 0/12 |
| no | yes | 17/24 | 7/12 |
| no | no | **1/24** | **0/12** |

Marginal effects (grey pair, 96 runs, all naming a yielder; 0.5 = no effect):

- label: 57/96 chose the robot labelled `robot_1`;
- slot: **85/96** chose the first-listed robot (`id_asc` 47/48, `id_desc` 38/48);
- scene: 45/96 chose the physically correct robot.

The `robot_1` share is 33/48 with original IDs and 24/48 with swapped IDs. Its
residual pull shows only where label and slot disagree: 3/24 against 17/24 in the
two mixed combinations.

**Verdicts:**

| Rule | Verdict |
|---|---|
| Scene use | **not supported** (1/24 when both priors point to the wrong robot) |
| Label bias | not supported (0.69 in `A_grey`, 0.50 in `B_grey`) |
| Slot bias | **supported** (0.98 `id_asc`, 0.79 `id_desc`) |
| Real-frame secondary | fails (0/12 in the "both wrong" combination) |
| Image use | **not supported**: Cell C 26/48 against Cell D 24/48; Cell C fails in 3 of 4 side x order cells |

### Gemini ER-2 (`gemini-robotics-er-2-preview`, 240 runs)

ER-2 answers a head-on standoff with `strategy = reverse` (both back up) in most
runs. Outcome census:

| Arm | Correct | Wrong | No yielder (`reverse`) |
|---|---|---|---|
| `A_real` | 5 | 2 | 41 |
| `A_grey` | 2 | 2 | 44 |
| `B_grey` | 2 | 2 | 44 |
| `C_real_notext` | **10** | **1** | 37 |
| `D_grey_notext` | 2 | 5 | 41 |

- In the grey pair, every one of its 8 named yielders carries the label `robot_1`
  (4/4 in `A_grey`, 4/4 in `B_grey`), and 7 of the 8 came under `id_asc`.
- In Cell C, its 11 named yielders were correct 10 times: west 3/3 and east 7/8,
  spread over 6 scenes. In Cell D it was correct 2 of 7.

**Verdicts:**

| Rule | Verdict |
|---|---|
| Scene use | **not supported** (grey-pair combinations 4/24, 0/24, 0/24, 0/24) |
| Label bias | **supported toward `robot_1` under the letter of the rule** (P = 1.0 in both arms), but this rests on 4 + 4 named yielders out of 96 runs; read it as "when it names one, it is `robot_1`" |
| Slot bias | not supported (`id_desc` has 1 named run) |
| Real-frame secondary | fails |
| Image use | **not supported**: Cell C 10/48 against Cell D 2/48, a difference of 0.17 below the 0.25 margin, and no side x order cell reaches 9/12 |

### Claude Sonnet 5.5 (`claude-sonnet-5-5`, 64 runs)

Which Sonnet cells exist:

| Arm | Runs | Answered | Refused (terminal) | Stopped at pilot? |
|---|---|---|---|---|
| `A_real` | 48 | 18 | 30 | no (pilot 2/4 failed) |
| `A_grey` | 4 | 1 | 3 | yes |
| `B_grey` | 4 | 0 | 4 | yes |
| `C_real_notext` | 4 | 1 | 3 | yes |
| `D_grey_notext` | 4 | 0 | 4 | yes |

- Every refusal is `reasoning_extraction`. Every terminal refusal went through the
  grey fallback on attempt 3, and none was rescued by it. Every one of the 20
  answers came on attempt 1. So no Sonnet decision was made on a fallback image.
- `A_real`, answered runs only: correct 10/18 (west 4/10, east 6/8); `robot_1`
  12/18; first-listed 9/18.
- Refusals by cell in `A_real`: west `id_asc` 9/12, west `id_desc` 5/12, east
  `id_asc` 8/12, east `id_desc` 8/12.
- **Verdicts:** scene use, label bias, slot bias, real-frame secondary and image use
  are all **not assessable** (fewer than 20 decisions in each arm the rules need).

---

## Sonnet Fallback: Cause

The owner asked for an offline inspection first, plus at most 3 diagnostic calls.

- **Recorded artifacts.** The 26 Sonnet decisions of
  `data/logs/vm_runs/roster_validation/runs/rv01_sonnet_ho_s42` and `rv02_sonnet_ho_s43`
  (main checkout) all carry `refusal_category = reasoning_extraction`. 24 used the
  fallback.
- **Code path.**
  - `reasoning/vlm/anthropic_backend.py:145-146` sets
    `refusal = stop_reason == "refusal"`. Lines 164-185 send the frame as a base64
    `image/png` block, image first.
  - `reasoning/vlm/reasoner.py:487-496` turns a provider refusal into a parse
    failure.
  - At `reasoner.py:526-536`, a refusal on attempt >= `image_fallback_after_attempts`
    (2 in the `anthropic` section of `config/models.yaml`) swaps in the neutral image
    (`_should_fall_back`, lines 588-599). The fallback cannot fire without a refusal.
- **Diagnostic calls** (`53264de9`, `id_asc`, real frame, obstacle text on):
  - the image was sent: PNG 1280 x 960, 681,362 bytes, 908,484 base64 characters;
  - 3/3 returned HTTP 200 with `stop_reason: refusal` and `reasoning_extraction`;
  - each billed 3,019 input tokens and 0 output tokens.
- **Cause:** (a), the model refuses; not a harness or request artefact. The trigger
  documented in `docs/reports/2026-10-06-roster-validation.md` is the prompt's
  `<think>` answer-format block. Removing it lifted the refusal 3/3 there.
- **Observed here:** the refusal is frequent but not certain. 30/48 real-frame runs
  were refused, and 14 of the 16 grey and text-off pilot runs. Refusal is therefore
  at least as common without the frame as with it. No runtime code was changed.

---

## Refusals and Fallbacks

| Model | Arm | Attempt-1 refusals | Runs decided after fallback | Terminal refusals |
|---|---|---|---|---|
| gpt-4o | `A_real` | 5 | 3 (correct 2, wrong 1) | 0 |
| gpt-4o | `C_real_notext` | 6 | 1 (wrong) | 0 |
| gpt-4o | grey arms | 0 | 0 | 0 |
| ER-2 | all | 0 | 0 (no fallback configured) | 0 |
| Sonnet | all | 44 | 0 | 44 |

- **gpt-4o.** Its refusals appear only with the real frame, as in September. With
  the 4 fallback rows excluded, or on attempt 1 only, every gpt-4o verdict is
  unchanged. For example, Cell C on attempt 1 is 25/48 correct with 6 refusals.
- **Errors.** There were no transport errors, no 429s and no retries in any run.

---

## Cost Ledger

From `ledger.jsonl`, priced from recorded token usage at the spec's rates. The
ledger includes the 3 probes and the 3 Sonnet diagnostics.

| Model | Runs | API calls | Spend |
|---|---|---|---|
| ER-2 | 240 | 241 | $0.97 |
| gpt-4o | 240 | 256 | $1.55 |
| Sonnet 5.5 | 64 | 200 | $1.31 |
| **Total** | **544** | **697** | **$3.84** |

- The $10.00 total cap and $3.00 per-model caps were never reached.
- About $1.07 of Sonnet's spend is billed refusals: 44 runs x 4 attempts x about
  $0.006.
- The two dropped models cost $0.

---

## Comparison With Earlier Strata (Side by Side, Not Pooled)

Entries are P(names `robot_1`) in the re-score's 2x2 (correct robot x first-listed
robot), original IDs, obstacle text on.

| Stratum | correct r1, first r1 | correct r1, first r2 | correct r2, first r1 | correct r2, first r2 |
|---|---|---|---|---|
| Sept batch 1, gpt-4o, real frame, attempt 1 | 44/45 | 31/35 | 43/43 | 2/34 |
| **This run, gpt-4o, `A_real`, final** | 12/12 | **4/12** | 12/12 | 6/12 |
| Sept batch 1, gpt-4o, grey, attempt 1 | 17/18 | 16/18 | 18/18 | 9/18 |
| **This run, gpt-4o, `A_grey`, final** | 12/12 | **2/12** | 12/12 | 7/12 |
| Live gpt-4o, runs (re-score) | 7/7 | 3/5 | 10/13 | 8/10 |
| Live ER-2, runs (re-score) | 8/8 | 3/5 | 9/17 | 9/13 |

The decisive cell (correct `robot_2`, `robot_1` listed first) agrees with every
earlier stratum: gpt-4o names `robot_1` 12/12 here, 43/43 in batch 1 and 10/13 live.

One cell disagrees with September. With `robot_1` correct but `robot_2` listed
first, batch 1 named `robot_1` 31/35 (real) and 16/18 (grey); this run names it
4/12 and 2/12. Two differences between the strata are known; neither is tested:

- September ran the floating `gpt-4o` alias. The `gpt-4o-2024-08-06` pin dates from
  `569d95c` (2026-09-30), and the September rows record only `model_id: "openai"`.
- September ran the shipped max_attempts of that date.

Either way, the September tie-break by the obstacle text does not appear here. That
fits the re-score's finding that batch 2 did not replicate it either.

ER-2 live was near chance in the decisive cell (8/17 correct). Offline, ER-2 mostly
does not name a yielder, so that cell (west, `id_asc`) holds 1/12 correct in `A_real`
and 0/12 in `A_grey`.

---

## Limitations

- **12 scenes, one family, seed 42, two robots.** These are base `o0` variants with
  symmetric goals, and `robot_1` always spawns west. In Arm A the label and the side
  are confounded by construction. Only the grey pair separates them, and it does so
  in the text alone.
- **Offline first decision only.** No M3 gate, no execution, no closed loop.
- **Replicates are not independent.** gpt-4o runs at temperature 0 and its replicates
  mostly agree. Every result is therefore given at scene level as well.
- **Sampling not controlled for two models.** ER-2's Interactions API and Sonnet 5.5
  accept no temperature, so their configured values were recorded but not sent.
- **One prompt for every model.** Prompt v1 contains a `<think>` block, which
  triggers Sonnet's refusals. A Sonnet-specific prompt was out of scope.
- **Different images across the label contrast.** The verdict compares `A_grey` with
  `B_grey`, which share one image. `A_real` against `B_grey` would confound the
  image with the label and is not used for any verdict.
- **The image test fixes one frame per scene.** The annotation draws robot labels,
  and the blocker is visible in all 12 frames. Image use was tested only as "with no
  obstacle text, does the frame move the choice", against a grey-image control.
- **Amended mid-run.** The model list and Cells C/D changed by owner instruction after
  the first paid calls. The Arm A/B design, scoring and rules did not change.

---

## What the Thesis Can and Cannot Claim

The thesis can claim the following, as a small pre-registered offline experiment:

- On these head-on standoffs, none of the three tested models picks the yielder from
  the blocked side.
- gpt-4o's choice follows the first-listed robot. Swapping the labels moves its
  answer exactly with the listing, not with the scene.
- Removing the obstacle text and leaving only the camera frame does not move gpt-4o.
- ER-2 mostly declines to name a yielder at all and answers `reverse`.
- Sonnet 5.5 refuses the deployed prompt too often to be assessed.

This strengthens the re-score's conclusion: on this family, the correct yielder comes
from M3's feasibility gate, not from M2.

The thesis cannot claim:

- any of this for other scenes, robot counts, prompt versions or seeds;
- anything about Sonnet's scene use under a prompt it would answer;
- that ER-2 reads the blocker from the image. Its 10/11 correct named yielders in
  Cell C are a lead for a larger test, not evidence; they fail the stated rule.
- that the September `id_desc` tie-break effect is wrong. Here it did not reappear,
  with a pinned snapshot that may differ from September's alias.

---

## Reproducibility

| Item | Location (branch `exp/head-on-swapped-id-replay`) |
|---|---|
| Design and amendments | `docs/superpowers/specs/2026-11-14-head-on-swapped-id-replay-design.md` |
| Runner | `scripts/replay_swapped_ids.py` (reuses `scripts/replay_live_decisions.py`, unmodified) |
| Analysis | `scripts/analyze_swapped_ids.py`; output `data/experiments/2026-11-14-head-on-swapped-id-replay/analysis.txt` |
| Tests | `tests/unit/test_replay_swapped_ids.py` |
| Data | `calls.jsonl` (544 rows: every attempt's raw text, tokens, latency, effective config, served model, commit; no images or keys), `ledger.jsonl`, `probes.jsonl`, `sonnet_diagnostic.jsonl`, `grey_1280x960.png` |
| Commits | pre-registration `a410257`; probe fix `fe60cfe`; amendments 1-2 `f231c12`; amendment 3 `e975249`. Rows record the commit they ran under. |

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-swapid
PY=/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/.venv/bin/python
$PY scripts/replay_swapped_ids.py --runs-dir <main checkout>/data/logs/vm_runs --check-only
$PY scripts/analyze_swapped_ids.py
```

A paid re-run needs the provider keys in the environment (`set -a; source .env;
set +a`). It resumes, skipping recorded keys.

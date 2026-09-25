# gpt-4o Safety Refusals in M2 - Census, Stimulus Reconstruction, and Offline Replay

**Prepared:** 2026-09-25

**Revision history:**

- Initial draft: census of every local decision artifact, stimulus diff of the three obstacles-OFF refusals, and a 240-call offline replay/ablation probe against `gpt-4o`.

---

## Purpose

Three M2 analyses in tonight's obstacles-OFF `gpt-4o` runs were reported as
returning `"I'm sorry, I can't assist with that."` instead of the JSON
decision. The census below finds 12 such terminal refusals, spread across both
obstacle conditions, plus 11 more that a re-ask recovered — so the reported
symptom understated both the rate and the scope. Each refusal costs a re-ask
and burns an analysis slot, so Arm A collection needs the rate and, if
possible, the trigger. This report answers three questions:

- How often does it actually happen, and is it specific to a backend, to the
  static-obstacle prompt channel, or to the failure-context block?
- What exactly was the stimulus, and how does it differ from an adjacent
  analysis that succeeded?
- Does the stimulus reproduce offline, and does any prompt ablation move the
  rate?

All work is local and offline: no VM was touched, and no production prompt or
backend code was modified. The probe lives in `scripts/probe_refusals.py`;
artifacts are under `data/experiments/2026-09-25-refusals/`.

---

## Census

`scripts/probe_refusals.py census` reads every decision artifact under
`data/logs/vm_runs/` (163 artifacts across 19 runs; both the older
`m5_decisions/` and the current `decisions/` layouts). A refusal is counted when
`raw_text` matches `I('m| am) sorry.{0,20}I can'?t assist`, which covers both
observed phrasings; the "but" variant appears in 2 of 12 cases and was missed by
the literal string used in the tasking.

Two instrumentation notes shape the reading:

- `Reasoner` records `diagnostics.backend_id` as the **configured** id
  (`"openai"`) on a failed result and the **backend-reported** id (`"gpt-4o"`)
  on a successful one. Grouping on the raw field splits one model into two
  rows; this report folds them together.
- `prompt_static_obstacles` is derived per artifact from the rendered prompt
  (presence of the `Static obstacles (world-frame axis-aligned boxes):` header)
  rather than from `orchestrator.yaml.used`, because the five `20260924_*` runs
  predate that file. Where both exist they agree.

### Headline corrections

**1. There were 12 terminal refusals, not 3, and they are not confined to the
obstacles-OFF runs.** Nine of the 12 occurred in obstacle-ON `gpt-4o` analyses.
Every `gpt-4o` parse failure in the entire local corpus is a safety refusal —
there is no other failure mode in the data.

**2. The terminal rate understates the per-call rate by half.** Eleven further
`gpt-4o` artifacts carry `parse_status="invalid"` with `attempts=2` and
`error_message="VLM output contains no JSON object."` — the identical signature
of the 12 terminal cases, but with the re-ask recovering. Counting attempt 1
rather than the final outcome:

| quantity | gpt-4o | ER-2 |
|---|---|---|
| analyses | 101 | 62 |
| attempt-1 non-JSON | 23 (22.8%) | 0 |
| recovered by the re-ask | 11 of 23 (48%) | n/a |
| terminal (`decision=None`) | 12 (11.9%) | 0 |

Attempt-1 text is not persisted anywhere — `Reasoner.run` keeps only the last
attempt's `raw_text` — so "non-JSON on attempt 1" is inferred to be a refusal
from the shared error signature plus the fact that no other non-JSON failure
mode appears in 163 artifacts. That inference is strong but not proof.

Two consequences. First, the **per-call** refusal rate is ~23%, and the 11.9%
figure is the *both attempts refused* rate. Second, refusals are positively
correlated within a request: the marginal rate is 0.228 but the conditional
rate on the re-ask is 0.52, so the re-ask does not reset the model's stance.
`gpt-4o` 23/101 vs ER-2 0/62, Fisher p = 8.9e-06.

| backend | obstacles | total | attempt-1 non-JSON | terminal refusals |
|---|---|---|---|---|
| gpt-4o | ON | 77 | 20 (26.0%) | 9 (11.7%) |
| gpt-4o | OFF | 24 | 3 (12.5%) | 3 (12.5%) |
| gpt-4o | pooled | 101 | 23 (22.8%) | 12 (11.9%) |
| gemini-robotics-er-2-preview | ON | 59 | 0 | 0 |
| gemini-robotics-er-2-preview | OFF | 3 | 0 | 0 |
| gemini-robotics-er-2-preview | pooled | 62 | 0 | 0 |

The obstacle channel has no effect on terminal refusals (9/77 vs 3/24, Fisher
p = 1.0). The backend contrast is the only clean effect in the census
(12/101 vs 0/62, p = 0.0037 terminal; 23/101 vs 0/62, p = 8.9e-06 on attempt 1).

### Per run

| run | backend | obstacles | total | attempt-1 non-JSON | terminal | fc block | solo | pair |
|---|---|---|---|---|---|---|---|---|
| 20260924_193112 | gpt-4o | OFF | 2 | 0 | 0 | 1 | 1 | 1 |
| 20260924_195708 | gpt-4o | ON | 5 | 3 | 2 | 3 | 5 | 0 |
| 20260924_201328 | gpt-4o | ON | 4 | 0 | 0 | 3 | 2 | 2 |
| 20260924_203437 | gpt-4o | ON | 5 | 2 | 1 | 3 | 5 | 0 |
| 20260924_205009 | gpt-4o | ON | 5 | 3 | 3 | 3 | 5 | 0 |
| 20260925_002713 | gpt-4o | ON | 6 | 3 | 0 | 3 | 6 | 0 |
| 20260925_004252 | gpt-4o | ON | 24 | 3 | 0 | 3 | 23 | 1 |
| 20260925_005754 | gpt-4o | ON | 5 | 0 | 0 | 3 | 5 | 0 |
| 20260925_011246 | gpt-4o | ON | 4 | 0 | 0 | 3 | 2 | 2 |
| 20260925_012747 | gpt-4o | ON | 19 | 6 | 3 | 8 | 17 | 2 |
| 20260925_021549 | ER-2 | OFF | 3 | 0 | 0 | 2 | 3 | 0 |
| 20260925_023122 | ER-2 | ON | 8 | 0 | 0 | 5 | 6 | 2 |
| 20260925_024628 | ER-2 | ON | 9 | 0 | 0 | 5 | 7 | 2 |
| 20260925_030129 | ER-2 | ON | 5 | 0 | 0 | 3 | 4 | 1 |
| 20260925_035042 | ER-2 | ON | 7 | 0 | 0 | 3 | 6 | 1 |
| 20260925_040539 | ER-2 | ON | 7 | 0 | 0 | 6 | 5 | 2 |
| 20260925_042022 | ER-2 | ON | 23 | 0 | 0 | 5 | 22 | 1 |
| 20260925_043512 | gpt-4o | OFF | 7 | 1 | 1 | 4 | 6 | 1 |
| 20260925_045004 | gpt-4o | OFF | 15 | 2 | 2 | 4 | 2 | 13 |

Two runs the terminal count scores as clean — `20260925_002713` and
`20260925_004252` — each had 3 attempt-1 refusals that the re-ask recovered.

### Failure context and stall type

| backend | fc block | stall | total | attempt-1 non-JSON | terminal |
|---|---|---|---|---|---|
| gpt-4o | yes | solo | 33 | 11 | 8 |
| gpt-4o | yes | pair | 8 | 2 | 2 |
| gpt-4o | no | solo | 46 | 9 | 2 |
| gpt-4o | no | pair | 14 | 1 | 0 |
| ER-2 | yes | solo + pair | 29 | 0 | 0 |
| ER-2 | no | solo + pair | 33 | 0 | 0 |

Solo vs pair stall is a null (terminal 10/79 vs 2/22, p = 1.0).

**The failure-context association is an artifact of scoring only terminal
failures.** On terminal refusals it looks strong — 10/41 with the block vs 2/60
without, Fisher p = 0.0030. On the attempt-1 outcome it flattens to 13/41 vs
10/60, p = 0.094. The same happens to the only other pooled split that looked
real: refusals by wall-clock window were 6/21 in the 24 Sep 19:31-20:50 runs vs
6/80 after midnight (p = 0.013), but on attempt 1 that is 8/21 vs 15/80
(p = 0.080). The prompt template is byte-identical across both windows.

What the failure-context block does predict is **non-recovery**: of the 23
attempt-1 refusals, 10 of 13 with the block persisted through the re-ask
against 2 of 10 without it (Fisher p = 0.012, n = 23). That is a small sample
and the same run-clustering caveat applies — three short early runs carry much
of it — but it is the only surviving prompt-side signal, and it points at the
re-ask rather than at the first call.

Per-run stratification of the terminal-refusal fc split, showing the clustering
that inflates the pooled test:

| run | refusal with fc | refusal without fc |
|---|---|---|
| 20260924_195708 | 2/3 | 0/2 |
| 20260924_203437 | 1/3 | 0/2 |
| 20260924_205009 | 3/3 | 0/2 |
| 20260925_012747 | 2/8 | 1/11 |
| 20260925_043512 | 0/4 | 1/3 |
| 20260925_045004 | 2/4 | 0/11 |

---

## Stimulus Reconstruction

Each artifact stores the rendered `system_prompt` and `user_prompt` with their
SHA-256, but **no reference to an image file**. The overhead frames
(`data/logs/m5_frames/`) exist only on the simulation VM and are not available
locally, so the exact stimulus cannot be rebuilt: replay is text-faithful and
image-substituted (see below).

A second gap matters more for interpretation. `Reasoner.run` overwrites its
payload with the re-ask prompt on attempt 2 but the artifact persists the
**attempt-1** prompt, while `raw_text` holds only the **last** attempt's text.
All 12 refusals have `attempts = 2`, so the string that was actually refused was
produced by the *re-ask* prompt, and attempt 1's response is not recorded
anywhere — not in the artifacts and not in the M5 logs. Whether attempt 1 also
refused, or was merely malformed and the "Your previous response was invalid"
suffix induced the refusal, is unrecoverable from the artifacts. The replay
therefore runs both the stored prompt and its re-ask form.

### Diffs against a non-refused prompt from the same run

The three obstacles-OFF refusals named in the tasking are `a35f1ff9`
(`20260925_043512`, solo stall, no fc) and `2ddffe4c` / `ba3b2f47`
(`20260925_045004`, pair stall, fc present).

`2ddffe4c` and `ba3b2f47` are the same scene one tick apart — they differ from
each other in a single character:

```text
- robot_id=robot_2, x=-1.61, y=-0.23, theta=-2.79, status=STOPPED, linear_velocity=0.00
+ robot_id=robot_2, x=-1.61, y=-0.23, theta=-2.79, status=STOPPED, linear_velocity=0.01
```

And the successful analysis `099e3c33` from the same run, same fc block, same
stall type, differs from `2ddffe4c` by two characters:

```text
- robot_id=robot_2, x=-1.61, y=-0.23, theta=-2.80, status=STOPPED, linear_velocity=0.00
+ robot_id=robot_2, x=-1.61, y=-0.23, theta=-2.79, status=STOPPED, linear_velocity=0.00
```

Nothing else differs: no wording change, no failure-context change, no distance
change. Three essentially identical prompts, two refused and one answered.

`a35f1ff9` differs more from its matched control `9f257ee1` because the scene
differs — it is the tight head-on configuration (0.28 m, mutually facing, both
STOPPED) while the control is 1.44 m apart and one robot is MOVING:

```text
- robot_1 <-> robot_2: distance 1.44 m; robot_1 faces robot_2: no; robot_2 faces robot_1: yes
+ robot_1 <-> robot_2: distance 0.28 m; robot_1 faces robot_2: yes; robot_2 faces robot_1: yes
```

Across all 101 `gpt-4o` artifacts there are 85 distinct prompt SHAs and no SHA
appears both refused and answered, so no exact-duplicate natural experiment
exists in the corpus.

---

## Replay and Ablations

### Apparatus

`scripts/probe_refusals.py replay` reads the rendered `system_prompt` and
`user_prompt` straight out of each artifact and sends them through the
production path — `build_backend("openai", ...)`, `invoke_backend`, then
`parse_decision_text` — with `max_attempts=1` and `allow_reask=False` so each
call is scored independently. The prompt builder is never re-run, so every
ablation is a string transform on a copy of the recorded text; production prompt
code is untouched. Prompt copies are under
`data/experiments/2026-09-25-refusals/prompts/`.

Because `OpenAIBackend._build_messages` always attaches an image and
`ReasonerRequest.image_path` has `min_length=1`, there is no text-only path
through the production backend without editing it. The image factor is
therefore bracketed rather than removed: a crude synthetic top-down render of
the artifact's recorded robot poses (the `overhead` arm) and a neutral grey
640x480 field (the `grey` arm).

30 cells, n = 8 each, 240 calls, order shuffled with a fixed seed and paced at
5 s (12 req/min, leaving headroom under the shared 20 req/min cap):

- 3 refusal prompts x {overhead T=0.0, overhead T=0.6, re-ask T=0.0,
  re-ask T=0.6, grey T=0.0}
- 3 matched control prompts x {overhead T=0.0, overhead T=0.6, re-ask T=0.0}
- 6 ablations on `2ddffe4c` at T=0.0: drop failure context, drop the `<think>`
  instruction, three wording groups, and `gpt-4o-mini`

The re-ask arm reconstructs attempt 2 by appending the production
`_REASK_SUFFIX` with the observed `error_message`, since the recorded refusals
were attempt-2 responses.

### Result

**Zero refusals in 240 calls. Every cell is 0/8, every call parsed, no HTTP
errors and no policy blocks.**

| cell group | calls | refusals | parsed |
|---|---|---|---|
| refusal prompts, overhead, T=0.0 / 0.6 | 48 | 0 | 48 |
| refusal prompts, re-ask, T=0.0 / 0.6 | 48 | 0 | 48 |
| refusal prompts, grey image, T=0.0 | 24 | 0 | 24 |
| control prompts, overhead, T=0.0 / 0.6 | 48 | 0 | 48 |
| control prompts, re-ask, T=0.0 | 24 | 0 | 24 |
| ablation: no failure context | 8 | 0 | 8 |
| ablation: no `<think>` instruction | 8 | 0 | 8 |
| ablation: wording group `collision` | 8 | 0 | 8 |
| ablation: wording group `motion` | 8 | 0 | 8 |
| ablation: wording group `authority` | 8 | 0 | 8 |
| ablation: `gpt-4o-mini` | 8 | 0 | 8 |
| **total** | **240** | **0** | **240** |

Per-cell numbers are in `summary.csv`; every call, including its full response
text and token usage, is in `calls.jsonl`.

The wording groups substitute neutral synonyms for the vocabulary that could
plausibly read as physical-harm or coercion language, one group per cell:

- `collision`: `deadlock(s)` → `mutual block(s)`, `standoff` →
  `face-to-face stop`, `physically conflicting` → `spatially overlapping`,
  `blocked` → `obstructed`
- `motion`: `backs up` → `moves rearward`, `back up to clear` →
  `move rearward to clear`, `reverse` → `rearward`
- `authority`: `priority_override` → `priority_first`, `unsafe` → `irregular`,
  `anomaly` / `anomalies` → `unusual_pattern` / `unusual patterns`

Sanity check that the ablation text reached the API: `gpt-4o` responses in the
`collision` cell reason in the substituted vocabulary ("...constitute a mutual
block"), confirming the rewritten prompt, not the original, was sent.

### Power

At the census attempt-1 refusal rate of 22.8%, the chance of seeing zero
refusals in 240 independent calls is `0.772^240` ≈ 1e-27. Even against the
conservative terminal rate of 11.9% it is `0.881^240` ≈ 1e-13. Pooled across
the 120 refusal-sourced calls alone the figure is ≈ 1e-14. This is not an
underpowered null.

---

## Trigger Hypothesis

**Best supported: a per-call stochastic refusal intrinsic to hosted `gpt-4o`,
at roughly 23% per call with ~50% persistence across an immediate re-ask, not
caused by any content of the rendered prompt.**

Evidence for, in descending strength:

- **Near-identical prompts disagree.** `2ddffe4c` and `ba3b2f47` differ by one
  character and both refused; `099e3c33`, two characters away with the same fc
  block and the same stall type, answered normally. No prompt-level rule can
  separate them.
- **Every prompt-side split collapses once attempt 1 is scored.** Obstacles is a
  null outright (p = 1.0). Failure context (p = 0.0030 → 0.094) and wall-clock
  window (p = 0.013 → 0.080) both lose significance when the 11 recovered cases
  are counted, and the fc split reverses sign in `20260925_043512`.
- **Replay is a total null.** 240 calls over the exact stored prompt text of
  three refusing and three non-refusing analyses, at two temperatures, with and
  without the re-ask suffix, and across two image arms, produced zero refusals
  and zero parse failures. At the census attempt-1 rate of 22.8% the
  probability of that under a text-driven trigger is ~1e-27.
- **No ablation moved anything**, including the three wording groups chosen to
  strip the physical-harm and coercion vocabulary (`deadlock`, `standoff`,
  `blocked`, `reverse`, `back up`, `unsafe`, `priority_override`). There is no
  evidence any of those words is implicated.
- **The backend contrast is the one robust effect.** ER-2 has 0 of 62 across
  the same scenes, prompts and episode structure.

Evidence strength: **moderate-to-strong for the negative claims** (prompt text
is not the trigger; obstacles, stall type, `<think>`, and the tested vocabulary
are ruled out at this sample size), **weaker for the positive claim**, because
the replay does not hold three things fixed and this report cannot separate
them:

1. **The real image.** M5 sends M1's *annotated* overhead frame at full
   resolution (`frame_downscale_width: null`) — status-coloured boxes, velocity
   arrows, ID labels. Those PNGs live under the VM's `frame_dump_dir` and are
   not available locally, so the replay substituted a crude synthetic top-down
   render and a neutral grey field. An image-side trigger would look exactly
   like this null.
2. **The wall-clock window and serving route.** The live refusals span three
   sessions over nine hours from the VM; the replay ran in one 20-minute window
   from a laptop.
3. **The unrecorded attempt-1 response.** The inference that attempt-1
   non-JSON was a refusal rests on the shared error signature, not on text.

The non-recovery signal (10/13 with fc vs 2/10 without) is the one prompt-side
result that survived, and it concerns the *re-ask*, not the first call. It is
n = 23 and run-clustered; treat it as a hypothesis to test, not a finding.

---

## Cost

| item | value |
|---|---|
| API calls | 240 (232 `gpt-4o`, 8 `gpt-4o-mini`) |
| `gpt-4o` tokens | 316,816 prompt / 39,902 completion |
| `gpt-4o-mini` tokens | 120,944 prompt / 917 completion |
| total | $1.21 at list prices |
| wall clock | ~20 min at a 5 s pace (12 req/min, inside the shared 20 req/min cap) |

`gpt-4o-mini` bills the same synthetic image at ~15k tokens per call against
`gpt-4o`'s ~1.3k, which is why 8 calls dominate the prompt-token count on that
row; it does not change the conclusion, only the unit economics of using mini
for image work.

The census itself costs nothing — it is pure artifact analysis and answers the
most actionable question in the report.

---

## Recommendation for Arm A

**1. Raise `vlm.reasoner.max_attempts` from 2 to 4 (do this).** The census
measures the recovery directly: one re-ask already rescues 11 of 23 refusals.
At the observed 0.52 persistence per extra attempt, a third attempt takes the
terminal rate from 11.9% to roughly 6% and a fourth to roughly 3%, at a cost of
one extra call only on the ~23% of analyses that need it. This is the single
highest-value change and it needs no new evidence.

**2. On a refusal, resend the original prompt instead of the re-ask (test
this).** The re-ask suffix ("Your previous response was invalid: …") is designed
for malformed JSON, not for a refusal, and the failure-context result suggests
the re-ask does not reset the model's stance. Detecting the refusal signature in
`Reasoner.run` and retrying with the unmodified payload — optionally with a
fresh `system_prompt` — is a small, well-scoped change worth an A/B.

**3. Persist every attempt's `raw_text`, not just the last (do this).** This
investigation could not tell whether attempt 1 refused because the artifact
keeps only `last_raw`. A per-attempt list in the artifact would have answered
the central question for free, and would let Arm A report the per-call refusal
rate directly instead of inferring it.

**4. Do not change the prompt wording.** No tested wording group moved the rate,
and the near-identical-prompt evidence argues the text is not the lever.

**5. Do not switch the Arm A backend to ER-2 on this evidence alone.** ER-2's
0/62 is the cleanest contrast in the census, but the ER-2 backend is still
gated on the two pre-registered confounds (the Interactions API drops sampling
control, and ER-2 opens with `reverse` on every asymmetric scene, so its first
decision is not comparable to `gpt-4o`'s). The refusal rate is an argument to
add to that gate, not to bypass it.

**6. Next experiment, if the trigger still matters.** Copy the 12 refusing
`request_id`.png frames plus matched non-refusing frames off the VM and re-run
`scripts/probe_refusals.py replay` against the real images. That is the one arm
this report could not run, and it is the only remaining way to separate an
image-side trigger from a purely stochastic one.

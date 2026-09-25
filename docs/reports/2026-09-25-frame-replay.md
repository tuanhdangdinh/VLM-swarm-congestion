# Real-Frame Replay of Live M5 Decisions - Refusal Trigger and Order Sensitivity

**Prepared:** 2026-09-25

**Revision history:**

- Initial draft: prompt-reconstruction integrity over the six Arm A pilot runs, a 108-call real-frame refusal arm, and a 12-call presentation-order arm truncated by an exhausted API credit balance.
- Rev 2 (2026-09-25): credits restored; completes Arm R to all 74 artifacts and adds the paired grey sub-arm, the full Arm O and Arm M. The grey arm settles the refusal trigger within one design (0/120 vs 22/60); Arm O finds a large order effect on real stimuli and, under `id_desc` only, obstacle-side sensitivity; Arm M finds `max_attempts=4` more than halves the terminal refusal rate.
- Rev 3 (2026-09-25): adds Arm S, a within-artifact `order` x `obstacle text` x `image` ablation on the six genuine-standoff artifacts, and Arm D, a downscaled-frame refusal check. The obstacle **text** block carries the `id_desc` side signal (removing it: P(feasible) 0.962 -> 0.556, p = 8.8e-4); the frame amplifies it; the robot states carry nothing. Still 0/288 traces cite the blocker, so trace silence is not evidence a channel is unused. Downscaling frames triples terminal refusals.

---

## Purpose

Two open questions could be settled with the real stimuli the Arm A pilot
captured, because those runs stored the exact scene snapshot, the rendered
prompt with its SHA-256, the presentation order **and** the annotated overhead
PNG that M2 actually received.

- **Refusals.** `gpt-4o` refuses (`"I'm sorry, (but) I can't assist with
  that."`) on roughly 23% of live attempt-1 calls
  (`docs/reports/2026-09-25-gpt4o-refusals.md`), yet replaying the byte-identical
  prompts with synthetic or grey images produced **0 refusals in 240 calls**. The
  one untested difference was the real camera frame.
- **Order sensitivity.** The offline probe on synthetic images said `gpt-4o`
  follows the presentation slot; live it looks ID-anchored (`robot_1` in 9/11
  overall, 5/6 under `id_desc`). See
  `docs/reports/2026-09-25-overnight-findings.md` §L.3.

All work is local. No VM was touched, and no production prompt, backend or
reasoner code was modified: the probe imports `build_reasoner_request`,
`build_prompt_payload` and `Reasoner` and drives them unchanged. The probe is
`scripts/replay_live_decisions.py`; artifacts are under
`data/experiments/2026-09-25-frame-replay/`.

---

## Headline

**The real annotated frame is the refusal trigger.** With the prompt text
byte-identical to what M5 sent (SHA-256 verified) and the real PNG attached,
`gpt-4o` refuses on **27 of 108 attempt-1 calls (25.0%)** — statistically
indistinguishable from the live rate on the very same stimuli (8 of 36
artifacts, 22.2%, Fisher p = 0.83), with the terminal and re-ask-recovery rates
also reproducing the live census within noise. That within-design pairing is the
primary result: the deployed refusal behaviour reproduces offline as soon as the
real frame is attached. Set against the earlier probe's **0 of 240** refusals on
artifact-verbatim prompts with synthetic images, the image is the variable that
moves the rate — though that contrast is across two experiments, not within one
(see Interpretation).

**The order question is unresolved.** The API credit balance was exhausted
mid-run, so Arm O ran at n = 1 per cell (12 calls) instead of n = 8 (96). Its
direction is consistent with the live ID-anchored reading and against the
offline slot-anchored reading, but at that n it is not evidence. Arms M and the
grey sub-arm did not run at all.

> Superseded by Rev 2. Credits were restored and every arm ran to its planned
> design. The grey sub-arm settles the refusal trigger within one design
> (0/120 grey vs 22/60 real frame, p = 1.5e-12), so the cross-experiment 0/240
> comparison qualified above is no longer load-bearing. Arm O at full n finds a
> large order effect (P(`robot_1`) 0.979 under `id_asc` vs 0.468 under
> `id_desc`, p = 5.0e-9) that is *neither* the live ID-anchored nor the
> synthetic slot-following reading. Arm R's own numbers below are for the
> 36-artifact subset; Rev 2 has all 74. Read Rev 2 for every quantity.

---

## Reconstruction Integrity

For each of the 74 decision artifacts across the six pilot runs
(`20260925_063520`, `065143`, `070637`, `072130`, `073621`, `075116`) the probe
rebuilt the request exactly as M5 did: `SceneSnapshot(**scene)`, the real frame
path, `FailureContext(**failure_context)` where the artifact carried one, and
`include_pairwise_geometry` / `include_static_obstacles` / `static_obstacles`
read from that run's own `orchestrator.yaml.used`, at the artifact's stored
`robot_presentation_order`.

| quantity | count |
|---|---|
| artifacts | 74 |
| rendered `user_prompt` SHA-256 equals stored `prompt.user_sha256` | **74 (100%)** |
| mismatches | 0 |
| matched prompts with a missing frame PNG | 0 |
| artifacts carrying a rendered failure-context block | 19 |

The failure-context artifacts reconstruct exactly as well as the first-of-episode
ones, because M5 persists `failure_context` as a structured field rather than
only as rendered text. No artifact had to be excluded, and the order-replay arm
did **not** have to be restricted to first-of-episode decisions as the tasking
allowed for.

Only the stored-order render is SHA-asserted. The flipped-order cell in Arm O is
by construction a new render; its SHA is recorded as provenance, not compared.

---

## Method

`Reasoner.run` keeps only the **last** attempt's text — attempt 1 is overwritten
by the re-ask — which is the same instrumentation hole the refusal census
flagged. Rather than re-implement the retry loop and risk drifting from it, the
probe wraps the backend in a recording proxy satisfying the `VLMBackend`
Protocol. Production retry, re-ask and parse semantics stay byte-exact; the proxy
records every attempt's text, refusal flag, parse outcome, latency and tokens,
and owns rate pacing (per API call, not per `Reasoner.run`), 429 back-off and the
auth/quota aborts.

Configuration is the shipped one, read from `config/models.yaml`:
`gpt-4o`, `temperature 0.0`, `max_attempts 2`, `allow_reask true`.

A refusal is counted when the assistant text matches
`I('m| am) sorry.{0,20}I can'?t assist`, the same regex the census uses. For live
artifacts, attempt 1 is scored a refusal when `raw_text` matches directly
(terminal) or when `parse_status` is `invalid`/`failed` with
`error_message="VLM output contains no JSON object."` (re-ask recovered) — the
census established that this is the only non-JSON failure mode in the corpus.

---

## Arm R - Refusal Rate With Real Frames

108 replays: 36 artifacts x 3 replicates, stored order, real frame, shipped
retry policy, 0 transport errors.

| quantity | value |
|---|---|
| replays | 108 |
| **attempt-1 refusals** | **27 (25.0%)** |
| terminal refusals (refused on entry, no decision) | 12 (11.1%) |
| re-ask recovered | 15 of 27 (55.6%) |
| artifacts refusing at least once | 13 of 36 (36.1%) |
| artifacts refusing on every replicate | 4 of 36 (11.1%) |

### The image is the variable

| stimulus | attempt-1 refusals | n | same artifacts as this arm? |
|---|---|---|---|
| **real annotated frame (this arm)** | **27 (25.0%)** | 108 calls | - |
| live pipeline, these same artifacts | 8 (22.2%) | 36 analyses | yes |
| live pipeline, all `gpt-4o` artifacts (census) | 23 (22.8%) | 101 analyses | superset |
| synthetic / grey image (2026-09-25 probe) | 0 (0.0%) | 240 calls | **no** — earlier runs |

Real frame against the live rate on the same stimuli: p = 0.83, i.e. the replay
reproduces live behaviour. The terminal rate (11.1%) matches the census's live
11.9%, and the re-ask recovery (55.6%) matches its 48%. This is the within-design
comparison and it needs no cross-experiment assumption.

Real frame against the synthetic-image probe: Fisher p = 1.2e-13. This contrast
is **across two experiments**. Both replayed prompts verbatim from decision
artifacts through the same production path, model and temperature, but the
synthetic probe drew its prompts from the earlier 19-run corpus rather than these
six pilot runs, and some of its cells replayed the re-ask prompt. The prompts are
therefore artifact-verbatim within each probe, not byte-identical between the two
rows. The planned grey sub-arm would have supplied the paired within-design
version of this contrast and did not run.

### The refusal is stimulus-locked, not random

Replays are grouped by whether the *live* call on that same artifact refused on
attempt 1.

| live attempt-1 | replays | attempt-1 refusals | rate |
|---|---|---|---|
| refused | 24 | 13 | 0.542 |
| did not refuse | 84 | 14 | 0.167 |

Fisher p = **8.0e-4**. At the artifact level (did this artifact ever refuse in
three replays?) the 2x2 is 6 / 2 / 7 / 21, p = 0.016. So particular frames carry
elevated refusal probability that persists across sessions — but the mapping is
stochastic, not deterministic: only 4 of 36 artifacts refused on all three
replicates, and two artifacts that refused live never refused in replay.

### Failure-context block

| failure-context block | replays | attempt-1 refusals | rate |
|---|---|---|---|
| present | 36 | 11 | 0.306 |
| absent | 72 | 16 | 0.222 |

Consistent with the census's null on this axis; this arm does not have the power
to separate it from the artifact-level clustering above.

### Coverage

Arm R completed 36 of the 74 artifacts before the credit balance ran out, in
analysis order: all 23 of `20260925_063520`, all 8 of `065143`, and 5 of 7 of
`070637`. Every covered artifact has its full n = 3, so no cell is partial. All
three covered runs are the `head_on_asymmetric_w0p2_eopen_o0` variant (obstacle
at x = -1.85); the three east-obstacle runs are uncovered. The two variants'
prompts differ only in the sign of one obstacle coordinate, and the census found
no obstacle-channel effect on refusals (p = 1.0), so this is unlikely to bias the
rate — but it is an untested assumption here.

---

## Arm O - Order Sensitivity on Real Stimuli (underpowered)

The six first-yield artifacts (one per run, each the run's first `yield`
decision, all first-of-episode with no failure-context block) x
`{id_asc, id_desc}`. Planned n = 8 (96 calls); **delivered n = 1 (12 calls)**
before the credit balance was exhausted.

`correct` is the robot whose retreat direction is unobstructed. M3's own
feasibility gate recorded the mapping in these very artifacts — *"yield
re-grounded: robot_1 has 0.70 m retreat room < 1.08 m required; robot_2
feasible"* on the west-obstacle runs — and the two east-obstacle runs needed no
regrounding when `robot_1` was named. `robot_1` enters from the west and retreats
west, `robot_2` from the east and retreats east, so a west obstacle
(x = -1.85) makes `robot_2` correct and an east obstacle (x = +1.85) makes
`robot_1` correct.

| run | artifact | stored order | replay order | decision | `yield_robot` | first-listed | correct | attempt 1 refused |
|---|---|---|---|---|---|---|---|---|
| `063520` | `53264de9` | `id_desc` | `id_asc` | yield | `robot_1` | yes | no | no |
| `063520` | `53264de9` | `id_desc` | `id_desc` | yield | `robot_2` | yes | yes | yes |
| `065143` | `5e7b5a59` | `id_asc` | `id_asc` | yield | `robot_1` | yes | no | no |
| `065143` | `5e7b5a59` | `id_asc` | `id_desc` | none (terminal refusal) | - | - | - | yes |
| `070637` | `2c3fbfa5` | `id_asc` | `id_asc` | yield | `robot_1` | yes | no | no |
| `070637` | `2c3fbfa5` | `id_asc` | `id_desc` | yield | `robot_2` | yes | yes | no |
| `072130` | `61119197` | `id_asc` | `id_asc` | yield | `robot_1` | yes | yes | no |
| `072130` | `61119197` | `id_asc` | `id_desc` | yield | `robot_1` | no | yes | yes |
| `073621` | `d053d0dc` | `id_asc` | `id_asc` | yield | `robot_1` | yes | yes | no |
| `073621` | `d053d0dc` | `id_asc` | `id_desc` | yield | `robot_1` | no | yes | no |
| `075116` | `3120c65f` | `id_desc` | `id_asc` | yield | `robot_1` | yes | yes | yes |
| `075116` | `3120c65f` | `id_desc` | `id_desc` | yield | `robot_1` | no | yes | no |

Pooled over the 11 cells that produced a yield:

| quantity | `id_asc` | `id_desc` | Fisher (two-sided) |
|---|---|---|---|
| P(`yield_robot` = `robot_1`) | 6/6 (100%) | 3/5 (60%) | **p = 0.18** |
| P(`yield_robot` = first-listed) | 6/6 (100%) | 2/5 (40%) | - |
| P(`yield_robot` = correct) | 8/11 (72.7%) pooled | | |

Restricting to cells whose attempt 1 was not a refusal (the re-ask changes the
prompt, so a recovered cell is a different stimulus) leaves 8 cells: `id_asc`
5/5, `id_desc` 2/3, p = 0.375.

**This arm does not answer the question.** At n = 1 per cell, p = 0.18 is what a
null looks like. What can be said is only directional: the `id_desc` column sits
at 0.60 for `robot_1`, far above the offline synthetic probe's 0.25 and near the
live 5/6, so nothing here contradicts the §L.3 reading that the deployed
pipeline is ID-anchored where the synthetic probe was slot-anchored. It does not
establish it. Note also that 4 of the 6 `id_desc` cells are ones where
`robot_1` is also the *correct* yielder, so ID-anchoring and feasibility are
confounded in exactly the way the overnight report's standing caveat warns about.

---

## Arm M - Retry Policy

**Not run.** Arm M was gated on refusals reproducing in Arm R, which they did
(27/108), but the credit balance was exhausted before it could start. The
relevant quantity is nonetheless visible in Arm R under the shipped policy:
the re-ask recovered 15 of 27 refusals (55.6%), leaving a terminal rate of
11.1%.

---

## Deviations From the Plan

| planned | delivered | reason |
|---|---|---|
| Arm R: 74 artifacts x n=3 (~222 replays) | 36 artifacts x n=3 (108 replays) | OpenAI credit balance exhausted mid-run |
| Grey paired sub-arm: 20 artifacts, n=6 | not run | same |
| Arm O: 6 artifacts x 2 orders x n=8 (96) | n=1 (12) | same |
| Arm M: 3 policies x n=6 | not run | same |
| budget ~450 calls | 151 API calls, $0.85 | same |

The failure surfaced as HTTP 429 with `insufficient_quota` /
`credit_balance_exhausted` — the same status code as a rate limit. The probe's
back-off ladder treated it as one and spent about four minutes per cell before
recording a dead row. Five such rows were purged from `calls.jsonl`, and the
probe now classifies the quota codes as a `QuotaAbort` that stops the run
immediately, alongside the existing 401/403 `AuthAbort`. Every cell is keyed and
skipped if already recorded, so a resume costs nothing once credits are restored:

```bash
source .venv/bin/activate && set -a && source .env && set +a
python scripts/replay_live_decisions.py --arm R    --n 3 --pace-sec 3.0
python scripts/replay_live_decisions.py --arm grey --n 3 --pace-sec 3.0
python scripts/replay_live_decisions.py --arm O    --n 8 --pace-sec 3.0
python scripts/replay_live_decisions.py --arm M    --n 6 --pace-sec 3.0
python scripts/replay_live_decisions.py --arm analyze
```

The Arm O rows were collected in the same session, through the same production
path and configuration, as a 12-call pilot before the main arms; they are merged
into `calls.jsonl` and are not a separate condition.

---

## Interpretation

**Is the real frame the refusal trigger? Yes, and the evidence is strong.** The
within-design result carries it on its own: with prompts byte-identical to the
live ones by SHA-256, the shipped backend, model, temperature and retry policy,
and the real frame attached, the replay rate lands on top of the live rate for
the same artifacts (25.0% vs 22.2%, p = 0.83) and reproduces the live terminal
and recovery rates. Live refusal behaviour is fully reproducible offline once
the real frame is present. Layered on top, the earlier probe's 0/240 on
artifact-verbatim prompts with synthetic images says the image is what moves the
rate. The refusal is a property of the annotated overhead frame, not of the task
wording.

Two qualifications. First, the 0/240 contrast is cross-experiment — different
source runs, some re-ask cells — rather than a grey arm run inside this design;
the planned paired real-vs-grey sub-arm would have made the image attribution
airtight within one design and was not run. Second, *which*
property of the frame does it is untested — candidates are the drawn robot-ID
labels and status-coloured boxes, the overhead surveillance framing, or
something about photographic realism that the crude plan-view render lacked.
Nothing here discriminates among those.

**Does order sensitivity on real stimuli match live or offline?** Unresolved.
The direction favours the live ID-anchored reading, but n = 1 per cell cannot
carry that claim, and the design confounds ID with feasibility in 4 of 6
`id_desc` cells.

---

## Recommendation for the Arm A Retry Policy

- **Keep the re-ask.** It recovers 55.6% of refusals at the cost of one extra
  call on roughly a quarter of analyses. Without it the terminal rate is 25%
  rather than 11%.
- **Raise `max_attempts` to 3 or 4 for `gpt-4o` runs.** The census put the
  conditional refusal rate on the re-ask at 0.52, so refusals are positively
  correlated within a request and a second re-ask should still clear a
  meaningful share. Arm M was designed to measure exactly this and is the first
  thing to run when credits return; until then the change is a hypothesis, not a
  measured improvement.
- **Budget for it.** At 25% attempt-1 refusal and 11% terminal, an Arm A run of
  `k` analyses loses about `0.11k` decision slots outright and pays about
  `1.25k` calls. Size the pilot accordingly.
- **Prefer ER-2 for any arm where a lost analysis is expensive.** The census has
  it at 0/62 against `gpt-4o`'s 23/101.
- **Do not attribute a `gpt-4o` parse failure to the prompt.** Every
  non-JSON failure in the corpus is a safety refusal, and this report shows the
  trigger is the image.

---

## Cost

| quantity | value |
|---|---|
| `Reasoner` runs | 120 |
| API calls (attempts) | 151 |
| prompt tokens | 263,142 |
| completion tokens | 19,031 |
| estimated spend | **$0.85** |

Against a planned ~450-call budget, roughly a third was spent before the credit
balance ran out. The remaining arms should cost about $2 more.

---

## Artifacts

| path | contents |
|---|---|
| `scripts/replay_live_decisions.py` | the probe: reconstruction, integrity check, four arms, analysis |
| `tests/unit/test_replay_live_decisions.py` | reconstruction SHA fixtures and refusal-detection tests |
| `data/experiments/2026-09-25-frame-replay/calls.jsonl` | one row per `Reasoner` run, with every attempt |
| `data/experiments/2026-09-25-frame-replay/summary.csv` | per-cell aggregation |

The pilot PNGs are not copied; rows reference them by run and `request_id`.

---

## Rev 2 - Complete Arms

Credits were restored and every arm ran to its planned design. All Rev 1
sections above are left as written; this section supersedes them where the
numbers differ, because Arm R now covers all 74 artifacts rather than 36.

`546` `Reasoner` runs, `708` API calls, 0 transport errors, 0 quota aborts.

### Arm R, complete

| quantity | Rev 1 (36 artifacts) | **Rev 2 (all 74)** |
|---|---|---|
| replays | 108 | **222** |
| attempt-1 refusals | 27 (25.0%) | **42 (18.9%)** |
| terminal refusals | 12 (11.1%) | **22 (9.9%)** |
| re-ask recovered | 15/27 (55.6%) | **20/42 (47.6%)** |
| artifacts refusing at least once | 13/36 (36.1%) | **21/74 (28.4%)** |
| artifacts refusing on every replicate | 4/36 (11.1%) | **5/74 (6.8%)** |

The pooled rate fell from 25.0% to 18.9% because the three runs added in Rev 2
include `20260925_075116`, which contributes 26 of the 74 artifacts at a much
lower rate (6/78, 7.7%). Per-run rates range from 7.7% to 33.3%. The live rate
over all 74 is 10/74 (13.5%); replay 42/222 (18.9%). The stimulus-locking result
strengthens considerably:

| live attempt-1 | replays | attempt-1 refusals | rate |
|---|---|---|---|
| refused | 30 | 18 | **0.600** |
| did not refuse | 192 | 24 | **0.125** |

Fisher p = **5.4e-8**.

### Grey sub-arm - the frame is the trigger, within one design

The 10 live-refused artifacts and 10 matched live-valid controls, same prompts,
n = 6, with a neutral mid-grey PNG of identical dimensions (1280x960) in place of
the annotated frame. The real-frame half is Arm R's n = 3 on the same artifacts.

| artifact group | image | replays | attempt-1 refusals | rate |
|---|---|---|---|---|
| live-refused | real frame | 30 | 18 | 0.600 |
| live-refused | **grey** | 60 | **0** | **0.000** |
| live-valid | real frame | 30 | 4 | 0.133 |
| live-valid | **grey** | 60 | **0** | **0.000** |
| pooled | real frame | 60 | 22 | 0.367 |
| pooled | **grey** | 120 | **0** | **0.000** |

Fisher p = **1.5e-12**. Not one of the 120 grey calls refused, including 60 on
the very prompts that refuse 60% of the time with their own frame attached. No
grey call produced a non-refusal parse failure either.

This is the within-design result Rev 1 lacked. The prompt text is byte-identical
between the two image arms by construction — only `image_path` differs — so the
attribution needs no cross-experiment assumption. **Removing the frame removes
the refusal completely.**

### Arm O - order sensitivity on real stimuli

Six first-yield artifacts x `{id_asc, id_desc}` x n = 8, temperature 0.0, 96
runs. `P` columns are over the cell's yield decisions.

| run | artifact | order | n | yields | P(`robot_1`) | P(first-listed) | P(correct) |
|---|---|---|---|---|---|---|---|
| `063520` west | `53264de9` | `id_asc` | 8 | 8 | 1.000 | 1.000 | 0.000 |
| `063520` west | `53264de9` | `id_desc` | 8 | 8 | 0.250 | 0.750 | 0.750 |
| `065143` west | `5e7b5a59` | `id_asc` | 8 | 8 | 1.000 | 1.000 | 0.000 |
| `065143` west | `5e7b5a59` | `id_desc` | 8 | 7 | 0.000 | 1.000 | 1.000 |
| `070637` west | `2c3fbfa5` | `id_asc` | 8 | 8 | 1.000 | 1.000 | 0.000 |
| `070637` west | `2c3fbfa5` | `id_desc` | 8 | 8 | 0.000 | 1.000 | 1.000 |
| `072130` east | `61119197` | `id_asc` | 8 | 8 | 0.875 | 0.875 | 0.875 |
| `072130` east | `61119197` | `id_desc` | 8 | 8 | 1.000 | 0.000 | 1.000 |
| `073621` east | `d053d0dc` | `id_asc` | 8 | 8 | 1.000 | 1.000 | 1.000 |
| `073621` east | `d053d0dc` | `id_desc` | 8 | 8 | 0.875 | 0.125 | 0.875 |
| `075116` east | `3120c65f` | `id_asc` | 8 | 8 | 1.000 | 1.000 | 1.000 |
| `075116` east | `3120c65f` | `id_desc` | 8 | 8 | 0.625 | 0.375 | 0.625 |

Pooled:

| quantity | `id_asc` | `id_desc` | Fisher (two-sided) |
|---|---|---|---|
| P(`yield_robot` = `robot_1`) | 47/48 (97.9%) | 22/47 (46.8%) | **5.0e-9** |
| attempt-1-only subset | 44/45 (97.8%) | 16/37 (43.2%) | **1.2e-8** |
| P(`yield_robot` = first-listed) | 47/48 (97.9%) | 25/47 (53.2%) | - |
| P(`yield_robot` = correct) | 23/48 (47.9%) | 41/47 (87.2%) | **5.9e-5** |

**There is a large, highly significant order effect on real stimuli.** Flipping
the presentation order collapses P(`robot_1`) from 0.979 to 0.468. The effect
survives restricting to cells whose attempt 1 was not a refusal, so it is not a
re-ask artifact.

**But it is not pure slot-following.** Under `id_asc` the first-listed bias
saturates at 97.9%. Under `id_desc` the model picks the first-listed robot only
53.2% of the time — and what it does instead tracks the obstacle:

| order | west-obstacle runs | east-obstacle runs | Fisher |
|---|---|---|---|
| `id_asc`, P(`robot_1`) | 24/24 | 23/24 | p = 1.0 |
| `id_desc`, P(`robot_1`) | 2/23 | 20/24 | **p = 2.2e-7** |

Under `id_asc` the obstacle side makes no difference at all; under `id_desc` it
makes almost all the difference, and the model lands on the *correct* (feasible)
yielder 87.2% of the time.

**Do not read this as "the model uses the obstacle."** Three things argue
against it.

- **No decision ever mentions it.** Across all 95 Arm O decisions, zero
  justifications or root causes cite an obstacle, blocker, barrier or the
  rendered coordinate — and zero of the raw `<think>` traces do either, on a
  strict `obstacle|blocker|barrier|obstruct|1\.85` match. This reproduces the
  overnight report's null over 360 offline calls and 4 live runs. Whatever
  drives the `id_desc` split, the model does not report reasoning about the
  obstacle.
- **The unit of replication is the artifact, not the call.** Three artifacts per
  obstacle side, with rates clustered hard within each. The effective n behind
  p = 2.2e-7 is 3 vs 3.
- **Obstacle side is confounded with everything else about the run.** Different
  scenes, different frames, different robot offsets. `robot_1` is always the
  west-positioned robot here (x ≈ -0.13 to -0.23) and `robot_2` always east
  (x ≈ +0.12 to +0.17), so "picks `robot_2` on west-obstacle runs and `robot_1`
  on east-obstacle runs" is observationally identical to any rule keyed on
  position sign, heading sign, annotated status colour, or the obstacle's
  coordinate — and to plain per-run idiosyncrasy.

The defensible statement is narrow: **under `id_desc` the yielder choice
covaries strongly with obstacle side, and under `id_asc` it does not, because
the first-position bias saturates.** The mechanism is open. The counterbalanced
live design, with obstacle side varied within a fixed scene, remains the
decisive test.

**Does this match live ID-anchoring or the synthetic slot-following?** Neither
cleanly, and it supersedes the framing of
`docs/reports/2026-09-25-overnight-findings.md` §L.3. The synthetic offline probe
put P(`robot_1` | `id_desc`) at 0.25; the real-stimulus replay puts it at 0.468;
the live sample was 5/6. Under the replay's own `id_desc` distribution, drawing
5 or more `robot_1` in 6 live runs has probability **0.082** — unlikely but not
significant, so the live observation is consistent with sampling noise rather
than with a distinct ID-anchored regime. The live `id_desc` sample also mixes
obstacle sides, which the replay shows is the dominant term under that order, so
n = 6 cannot separate the two. §L.3's "the offline probe does not predict live
order sensitivity" overstates what n = 6 can support; the real-stimulus estimate
sits between the two and the obstacle side is the variable that was missing.

### Arm M - retry policy

The six strongest Arm-R refusers (`1db82597`, `2163b6ea`, `5c1c6c1b`,
`6f91c49b`, `d2156797`, `fb53a88f`) x three policies x n = 6, 108 runs.

| policy | runs | attempt-1 refusals | terminal | terminal rate | mean attempts |
|---|---|---|---|---|---|
| re-ask as shipped (`max_attempts=2`) | 36 | 28 | 16 | 0.444 | 1.78 |
| retry with the ORIGINAL prompt | 36 | 28 | 24 | 0.667 | 1.81 |
| **`max_attempts=4`** | 36 | 26 | **7** | **0.194** | 2.36 |

Conditional on attempt 1 having refused — the quantity the policy acts on:

| policy | refused attempt 1 | still terminal | conditional rate |
|---|---|---|---|
| re-ask as shipped | 28 | 16 | 0.571 |
| retry with the ORIGINAL prompt | 28 | 24 | **0.857** |
| **`max_attempts=4`** | 26 | 7 | **0.269** |

Pairwise: shipped vs original-prompt p = 0.037; shipped vs `max_attempts=4`
p = 0.031; original-prompt vs `max_attempts=4` p = 2.1e-5.

Two clear results. **The re-ask suffix does real work** — retrying the identical
prompt leaves 85.7% terminal against the re-ask's 57.1%, so the corrective
wording, not merely a second sample, is what recovers the call. And **raising
`max_attempts` to 4 more than halves the terminal rate again**, from 57.1% to
26.9%, for 2.36 calls per analysis instead of 1.78.

### Recommendation for Arm A (supersedes Rev 1)

- **Set `max_attempts: 4` for the `gpt-4o` reasoner** in `config/models.yaml`.
  Measured, not hypothesised: terminal refusals fall from 57.1% to 26.9% of
  refused analyses, at +0.6 calls per analysis on the refusing subset. On the
  full Arm R population this takes the terminal rate from 9.9% to roughly 4-5%.
- **Keep `allow_reask: true`.** The corrective suffix is the active ingredient;
  a plain retry is worse than the shipped policy.
- **Do not change the prompt to chase refusals.** The grey arm shows the text is
  not the trigger.
- **Keep `prompt_robot_order: random`** so the first-position bias is
  counterbalanced within a run. What is solid here is the *bias*, not a better
  default: under `id_asc` the model named `robot_1` on 47 of 48 samples
  regardless of feasibility, and on the west-obstacle runs that is the
  infeasible robot every time (P(correct) = 0.0 in three of six cells). That is
  a real cost of a fixed first slot.
  **Do not read this as a recommendation to flip the default to `id_desc`.**
  `id_desc` scored P(correct) = 0.872, but that pools three west artifacts
  (where first-listed happens to be the feasible robot) with three east ones —
  exactly the alignment the overnight report's standing caveat warns is a
  coincidence of scenario design. On n = 3 per side, with no decision citing the
  obstacle, flipping the default would be chasing an artifact. Counterbalance
  instead, and let the counterbalanced live design settle it.
- **ER-2 remains the safer backend** where a lost analysis is expensive (0/62
  refusals in the census).

### Cost (cumulative)

| quantity | value |
|---|---|
| `Reasoner` runs | 546 |
| API calls | 708 |
| prompt tokens | 1,228,740 |
| completion tokens | 90,073 |
| **estimated spend** | **$3.97** |

Against the ~450-call plan: 708 calls, because Arm R was completed to all 74
artifacts (+114 runs beyond the original 36-artifact state) so that the grey
pairing had a complete real-frame half and the primary arm covered every run.

### Deviations in Rev 2

| planned | delivered | reason |
|---|---|---|
| resume Arm O, grey, M | done at full n | - |
| (not requested) Arm R completion | +114 runs, all 74 artifacts | the grey pairing needs a real-frame half for all 20 of its artifacts; 10 of them sat in runs Arm R had not reached |
| Arm M "on the refusing artifacts" | 6 of the 21 that ever refused | 21 x 3 x 6 = 378 runs; the six strongest refusers give 28 refused attempt-1s per policy, enough to separate the three arms at p < 0.05 |

---

## Rev 3 - Which Channel Carries the Side Signal

Rev 2 left one mechanism open: under `id_desc` the yielder choice covaried with
obstacle side (west 2/23 `robot_1` vs east 20/24) while **no** decision or
`<think>` trace cited the obstacle. Rev 2 could not say whether the side signal
arrives through the rendered obstacle-text block, the annotated frame, or the
robot states themselves, because obstacle side was confounded with run identity.

Rev 3 answers it with a within-artifact ablation. The same standoff artifacts are
replayed under a fully crossed design, so a channel that stops carrying the
signal cannot be explained by per-run idiosyncrasy. Two new arms:

- **Arm S** — order `{id_asc, id_desc}` x obstacle text `{on, off}` x image
  `{real frame, neutral grey}`, n = 6, on every genuine-standoff artifact.
  288 runs.
- **Arm D** — the 10 live-refused artifacts at full resolution against a 640 px-wide
  downscale, stored order, n = 3. 60 runs.

All Rev 1 and Rev 2 sections are left as written. Nothing below supersedes them;
Arm S is a new design on a six-artifact subset, and its `id_desc` / text-on /
real-frame cell is the condition Arm O already measured.

### Configuration

The shipped `openai` reasoner now carries `max_attempts: 4` (raised from 2 on
2026-09-25 on Arm M's evidence), so **both new arms ran at `max_attempts = 4`,
`allow_reask: true`, `temperature 0.0`, `gpt-4o`**. Arm O ran at
`max_attempts = 2`. Attempt 1 is identical under either setting, but a refused
attempt 1 now gets up to three corrective re-asks, and the re-ask prompt is a
different stimulus. **Every decision contrast below therefore leads with the
attempt-1-only subset**, with the pooled figures shown alongside; the two agree
throughout.

### Artifact selection

An artifact is a genuine standoff when both robots are stationary (`STOPPED`, or
speed < 0.02 m/s), their separation is <= 0.6 m, and each faces the other. Distance
and facing are read off the line `format_pairwise_geometry_lines` renders into the
prompt, so the filter applies the rule the prompt itself states rather than a
second implementation of it.

| quantity | count |
|---|---|
| reconstructable artifacts across the six pilot runs | 74 |
| genuine standoffs | **6** |
| west-blocked (`w0p2_eopen`, obstacle x = -1.85, feasible yielder `robot_2`) | **3** |
| east-blocked (`wopen_e0p2`, obstacle x = +1.85, feasible yielder `robot_1`) | **3** |
| standoffs carrying a failure-context block | 0 |

Three per side meets the stated floor, but only just: the effective unit of
replication for any *side* comparison is three artifacts, not eighteen calls.
The failure-context exclusion is a no-op here because none of the six carries a
block, so no covariate is needed.

The filter independently recovered exactly the six Arm O artifacts
(`53264de9`, `5e7b5a59`, `2c3fbfa5`, `61119197`, `d053d0dc`, `3120c65f`) — one
per run, each that run's first `yield`. That is a useful check on the filter, and
it means Rev 3 introduces **no new scenes**: every cell below manipulates the
input channels of stimuli Arm O already characterised. The remaining 68
artifacts are not near misses; the next-closest pair sits more than 0.8 m apart.

All 288 Arm S runs returned `congestion_detected=true` with `strategy="yield"`,
so every cell's denominator is its full n and no cell loses samples to a
non-yield answer.

### The eight cells

`P(feasible)` is the share of yields naming the robot whose retreat is
unobstructed. It is the summary statistic for side-tracking: **any side-blind
rule — always `robot_1`, always first-listed, or a coin flip — scores 0.5 pooled
over the two sides**, because the feasible robot is first-listed on west runs and
second-listed on east runs. Only a rule that responds to the obstacle can beat
0.5. (That baseline is exactly 0.5 when the two sides contribute equally, which
holds in every pooled row at 18/18; the attempt-1 rows are mildly unbalanced —
`id_desc` / on / real is west 14 vs east 12, where always-`robot_1` would score
0.462.) `side p` is the Fisher test of west vs east P(`robot_1`) within that cell.

**Attempt-1 only (primary).**

| order | obstacle text | image | n | yields | P(`robot_1`) | P(feasible) | west P(`robot_1`) | east P(`robot_1`) | side p |
|---|---|---|---|---|---|---|---|---|---|
| `id_asc` | on | real | 32 | 32 | 1.000 | 0.562 | 1.000 | 1.000 | 1.0 |
| `id_asc` | on | grey | 36 | 36 | 0.972 | 0.472 | 1.000 | 0.944 | 1.0 |
| `id_asc` | off | real | 21 | 21 | 1.000 | 0.429 | 1.000 | 1.000 | 1.0 |
| `id_asc` | off | grey | 36 | 36 | 1.000 | 0.500 | 1.000 | 1.000 | 1.0 |
| `id_desc` | **on** | **real** | 26 | 26 | 0.500 | **0.962** | 0.071 | 1.000 | **2.7e-6** |
| `id_desc` | on | grey | 36 | 36 | 0.694 | 0.694 | 0.500 | 0.889 | **0.028** |
| `id_desc` | off | real | 27 | 27 | 0.704 | 0.556 | 0.643 | 0.769 | 0.68 |
| `id_desc` | off | grey | 36 | 36 | 0.583 | 0.583 | 0.500 | 0.667 | 0.50 |

**Pooled (includes re-ask-derived decisions), n = 36 per cell.**

| order | obstacle text | image | yields | P(`robot_1`) | P(feasible) | west P(`robot_1`) | east P(`robot_1`) | side p |
|---|---|---|---|---|---|---|---|---|
| `id_asc` | on | real | 36 | 1.000 | 0.500 | 1.000 | 1.000 | 1.0 |
| `id_asc` | on | grey | 36 | 0.972 | 0.472 | 1.000 | 0.944 | 1.0 |
| `id_asc` | off | real | 36 | 1.000 | 0.500 | 1.000 | 1.000 | 1.0 |
| `id_asc` | off | grey | 36 | 1.000 | 0.500 | 1.000 | 1.000 | 1.0 |
| `id_desc` | **on** | **real** | 36 | 0.556 | **0.944** | 0.111 | 1.000 | **4.2e-8** |
| `id_desc` | on | grey | 36 | 0.694 | 0.694 | 0.500 | 0.889 | **0.028** |
| `id_desc` | off | real | 36 | 0.694 | 0.583 | 0.611 | 0.778 | 0.47 |
| `id_desc` | off | grey | 36 | 0.583 | 0.583 | 0.500 | 0.667 | 0.50 |

The `id_desc` / on / real cell reproduces Arm O closely (Arm O: west 2/23, east
20/24; here west 2/18, east 18/18), so the replication holds across sessions and
across the `max_attempts` change. Its attempt-1-only row rests on five of the six
artifacts: every replicate of the east artifact `61119197` refused on attempt 1,
so it contributes only to the pooled row. The two rows agree regardless.

### The three contrasts, under `id_desc`

| contrast | P(feasible) | Fisher (two-sided) |
|---|---|---|
| **(a)** real frame, obstacle text **on vs off** | 25/26 (96.2%) vs 15/27 (55.6%) | **p = 8.8e-4** |
| **(b)** obstacle text on, image **real vs grey** | 25/26 (96.2%) vs 25/36 (69.4%) | **p = 0.0095** |
| **(c)** states only (text off + grey) | 21/36 (58.3%), side p = 0.50 | — |

Pooled, the same three read 34/36 vs 21/36 (p = 5.6e-4), 34/36 vs 25/36
(p = 0.012), and 21/36 with side p = 0.50.

- **(a) Removing the obstacle text destroys the side signal.** With the real
  frame unchanged and only the `Static obstacles:` block (and the guidance clause
  *"Fixed obstacles in the scene are listed above and are the only ones present;
  a robot can neither occupy nor drive through one"*) withheld, P(feasible) falls
  from 0.962 to 0.556 and the west-vs-east split goes from p = 2.7e-6 to
  p = 0.68. The manipulation is within-artifact: the same six scenes, the same
  frames.
- **(b) Removing the image attenuates it but does not abolish it.** With the text
  kept and a mid-grey PNG of identical dimensions in place of the frame,
  P(feasible) falls to 0.694 and a weaker side association survives
  (west 9/18 vs east 16/18, p = 0.028).
- **(c) The robot states alone carry nothing detectable.** Text off and grey
  image leaves P(feasible) at 0.583 with side p = 0.50 — indistinguishable from
  the 0.5 a side-blind rule scores.

### `id_asc` control

The first-position default is unbroken in **every** channel condition, so no
manipulation broke the design.

| obstacle text | image | P(`yield_robot` = `robot_1`) | P(feasible) |
|---|---|---|---|
| on | real | 32/32 (100%) | 18/32 (56.2%) |
| on | grey | 35/36 (97.2%) | 17/36 (47.2%) |
| off | real | 21/21 (100%) | 9/21 (42.9%) |
| off | grey | 36/36 (100%) | 18/36 (50.0%) |

Under `id_asc` the model names `robot_1` on 124 of 125 attempt-1 yields whatever
the obstacle text or the image says, and P(feasible) sits at chance in all four
cells. The first slot saturates the choice and leaves no room for the obstacle
channel to act — which is why the Rev 2 effect appeared under `id_desc` only.

### Obstacle mentions

`<think>` traces and the `root_cause` / `justification` fields were scanned for
`obstacle|blocker|barrier|obstruct|wall|box|crate|1.85`.

| order | obstacle text | image | runs | `<think>` mentions | decision-field mentions |
|---|---|---|---|---|---|
| `id_asc` | on | real | 36 | 0 | 0 |
| `id_asc` | on | grey | 36 | 0 | 0 |
| `id_asc` | off | real | 36 | 0 | 0 |
| `id_asc` | off | grey | 36 | 0 | 0 |
| `id_desc` | on | real | 36 | 0 | 0 |
| `id_desc` | on | grey | 36 | **6** | 0 |
| `id_desc` | off | real | 36 | 0 | 0 |
| `id_desc` | off | grey | 36 | 0 | 0 |

**Zero of 288 runs cite the blocker specifically** — no `obstacle_1`, no `1.85`,
no "blocker", "barrier" or "crate" anywhere in any attempt's text. The six
mentions are all the same generic hedge in one cell, e.g. *"either robot could
yield, but typically the one with more space or fewer obstacles behind should
yield. In this case, robot_1 should yield"* — and on the west artifacts where it
appears, `robot_1` is the **infeasible** robot. So even the one cell that
verbalises the concept does not apply it.

### Arm D - frame resolution and refusals

The 10 live-refused artifacts, stored order, n = 3, full-resolution 1280x960
frame against a 640x480 Lanczos downscale written to
`data/experiments/2026-09-25-frame-replay/images/down640_*.png`.

| image | runs | attempt-1 refusals | terminal refusals | mean attempts | decisions returned |
|---|---|---|---|---|---|
| real (1280x960) | 30 | 15 (50.0%) | 5 (16.7%) | 1.87 | 25 |
| **down640 (640x480)** | 30 | **23 (76.7%)** | **17 (56.7%)** | 3.50 | 9 |

Attempt-1 refusal: Fisher p = 0.060. Terminal refusal: Fisher p = **0.0028**.

The marginal terminal contrast is partly mechanical — more attempt-1 refusals
give more chances to end terminal — so the sharper quantity is **recovery
conditional on a refused attempt 1**, which is not downstream of the attempt-1
rate. The re-ask ladder cleared **10 of 15** full-res refusals but only **6 of
23** downscaled ones: Fisher p = **0.020**. Downscaled refusals are both more
frequent and harder to talk the model out of.

**Downscaling does not mitigate the refusal; it makes it worse.** The direction
is the opposite of the "the model balks at a high-resolution surveillance frame"
hypothesis, and the terminal-rate effect is significant while the attempt-1 one
is marginal. The full-res half (15/30) is consistent with Arm R's 18/30 on the
same artifacts in an earlier session, so the baseline reproduces.

### Interpretation

**Which channel carries the side signal? The obstacle text block, with the frame
as an amplifier.** The ranking is unambiguous and, unlike Rev 2's, it is
within-artifact:

1. The obstacle text is **necessary**. Withhold it and the association is gone
   (p = 0.68 with the real frame, p = 0.50 with grey), while every other input is
   byte-identical.
2. The text alone is **not sufficient at full strength**. With grey in place of
   the frame the effect survives but halves (P(feasible) 0.694, side p = 0.028).
   Something in the annotated frame — plausibly which robot is visibly nearer the
   blocked end — sharpens a coordinate the model otherwise uses weakly.
3. The robot states carry **nothing measurable** on their own (P(feasible) 0.583,
   side p = 0.50). The task framing that "the signal might be in the positions
   themselves" is not supported.

The evidence for (1) is strong. Rev 2's standing objection — that obstacle side
is confounded with artifact identity, three per side — cannot explain it, because
the ablation holds the artifact fixed and changes one block of prompt text.
Per-run idiosyncrasy does not switch itself off when a paragraph is deleted.

The evidence for (2) is **moderate, and structurally weaker than (a)'s**, because
the two arms of contrast (b) cannot be treated alike in either analysis. The
real-frame arm refuses; the grey arm never does (0/144). Under attempt-1-only the
real arm is therefore *conditioned on non-refusal*, and Rev 2 established that
refusal is stimulus-locked at the artifact level (p = 5.4e-8), so that
conditioning is not random with respect to the artifact. Pooling removes the
conditioning but adds re-ask-derived stimuli to the real arm alone, since a grey
call never re-asks. There is no version of (b) in which both arms see the same
selection. Contrast (a) does not have this problem: both arms carry the real
frame and drop comparable numbers of attempt-1 samples (10 and 9 of 36). That
the pooled and attempt-1-only versions of (b) agree is reassuring but is not a
substitute for a symmetric design.

The evidence for (3) is a null on 36 runs and should be read as "no detectable
contribution", not "none".

**What this means for "geometry unused" claims — read carefully.** The overnight
report and Rev 2 both leaned on a verbalisation null: across 360 offline calls,
4 live runs and 95 Arm O decisions, nothing ever cited the obstacle. Rev 3 adds
288 more runs to that null — **0 specific blocker citations in 288** — and at the
same time shows that the obstacle block is *causally load-bearing*. Those two
facts are not in tension: **tracking the obstacle side without naming it is
exactly what a model that uses a prompt field without verbalising it looks
like.** The correct statement is now:

- The obstacle channel **is used**, under `id_desc`, and demonstrably so.
- The traces are **not a reliable instrument** for whether it is used. A
  verbalisation null must not be reported as evidence that a channel is ignored.
  Any earlier phrasing along the lines of "the model does not use the rendered
  geometry" should be narrowed to "the model does not *report* using it".
- The channel is **masked by the presentation-order bias**. Under `id_asc` the
  first slot wins 124 of 125 times and the obstacle block buys nothing. Whatever
  competence exists is only expressed when the positional default does not
  already determine the answer — which is itself an argument for counterbalancing
  order rather than for trusting the obstacle channel.

**What Rev 3 still cannot say.** Which obstacle side maps to which robot is still
carried by three artifacts per side, so the *direction* of the mapping rests on
n = 3 vs 3; only its *dependence on the text block* is established within-artifact.
And "the frame amplifies" is a black box: the arm does not discriminate between
the drawn goal markers, the robots' visible offsets, and photographic realism.
The counterbalanced live design, with obstacle side varied inside a fixed scene,
remains the decisive test for the mapping.

**Refusals, a third replication.** Arm S re-runs the grey contrast as a
by-product: **38 of 144 real-frame runs refused on attempt 1 (26.4%) against 0 of
144 grey runs (Fisher p = 4.4e-13)**, on prompts that differ only in
`image_path`. Together with Rev 2's 0/120 and Arm D's resolution effect, the
annotated frame is confirmed as the trigger, and higher resolution is not the
aggravating factor.

### Recommendations (additions to Rev 2)

- **Keep `prompt_robot_order: random`.** Rev 3 strengthens the Rev 2 argument: a
  fixed `id_asc` slot does not merely bias the answer, it *suppresses* the one
  input channel that carries feasibility information.
- **Do not cite trace silence as evidence a prompt channel is unused.** Use an
  ablation. This probe is the template: hold the artifact fixed, remove one
  block, test the behavioural association.
- **Do not downscale frames to dodge refusals.** It triples the terminal refusal
  rate (16.7% -> 56.7%, p = 0.0028).
- **Obstacle text stays on** for any arm whose outcome depends on naming a
  feasible yielder, and its effect should be reported as order-dependent.

### Deviations from the plan

| planned | delivered | reason |
|---|---|---|
| "more than one scene per side"; < 3 per side to be flagged | exactly 3 per side, 6 artifacts | the corpus contains only 6 genuine standoffs; the filter recovered them all |
| 8 cells x n_artifacts x 6, ~500-700 calls, $4-6 | 288 Arm S runs + 60 Arm D runs = 493 API calls, $2.66 | 6 artifacts rather than the ~10-14 the estimate assumed; n = 6 kept, because the binding limit is artifacts per side, not replicates |
| failure-context artifacts excluded or carried as a covariate | exclusion, and it is a no-op | none of the six standoffs carries a block |
| `max_attempts` "per config — record the effective value" | **4** | `config/models.yaml` raised it on Arm M's evidence; attempt-1-only is therefore the primary analysis |
| Fisher tests per contrast | per-cell side-association tests **and** between-cell tests on P(feasible) | text-on vs text-off pooled over sides answers a different question; the side x choice interaction is the quantity at issue |

### Cost

| quantity | Arms S + D | cumulative (all arms) |
|---|---|---|
| `Reasoner` runs | 348 | 894 |
| API calls | 493 | 1,201 |
| prompt tokens | 808,952 | 2,037,692 |
| completion tokens | 63,475 | 153,548 |
| transport errors | 0 | 0 |
| **estimated spend** | **$2.66** | **$6.63** |

### Artifacts added

| path | contents |
|---|---|
| `data/experiments/2026-09-25-frame-replay/images/down640_*.png` | the 10 downscaled frames used by Arm D |
| `data/experiments/2026-09-25-frame-replay/calls.jsonl` | 348 new rows, keyed `S`/`D` with the obstacle-text factor appended; existing rows untouched |
| `data/experiments/2026-09-25-frame-replay/summary.csv` | regenerated with `obstacle_text` and `think_obstacle_mentions` columns |

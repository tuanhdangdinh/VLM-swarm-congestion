# Real-Frame Replay of Live M5 Decisions - Refusal Trigger and Order Sensitivity

**Prepared:** 2026-09-25

**Revision history:**

- Initial draft: prompt-reconstruction integrity over the six Arm A pilot runs, a 108-call real-frame refusal arm, and a 12-call presentation-order arm truncated by an exhausted API credit balance.

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

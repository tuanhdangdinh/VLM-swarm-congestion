# v4 Grounding-First v2: Cluster-Level Candidates, Ceiling on 31 Live S1b Episodes

**Prepared:** 2026-10-23

**Revision history:**

- Initial draft: `gf-candidates-v2` generator, zero-cost ceiling, oracle choice and fixed-option sanity replay.
- Rev 2 (2026-11-12): the four real-model replays (R5a/R5b ER-2, R6a/R6b Sonnet 5.5) were run; added the Real-Model Replay Results section, interpretation items 8-13, evidence notes under Owner Rulings, and Rev 2 limits. The Rev 1 sections are kept unchanged.

---

## Scope

This report covers v4 lever 2, cluster-level candidate enumeration for the
grounding-first `replay` variant of the offline bench
(`docs/specs/v4_vlm_bench.md`). It follows the v1 ceiling report
(`docs/reports/2026-10-23-v4-grounding-first-candidates.md`) and the first
real-model replays (`docs/reports/2026-10-23-v4-replay-er2.md`, conclusion 8).

- **Zero API calls (Rev 1 sections).** No key was loaded and no network
  backend ran for the ceiling, oracle and fixed-option sections. The
  fixed-option runs use the zero-network `FixedOptionBackend` with caches in a
  scratch directory, never under `data/bench/cache`. **Rev 2:** the real-model
  replays in the Results section did call the Gemini and Anthropic APIs.
- **Exploratory v4 only.** Nothing here pools with or replaces any prereg-v3
  confirmatory measure (A32-A36).
- **Items.** The same 187 items as every v4 report: `items_live31.jsonl`,
  md5 f1dc2ccb (137 recorded positives).
- **Code.** `benchmarks/vlm_bench/variants/gf_cluster.py` (generator) and
  `variants/cluster_report.py` (GT-scored report), commit db673fe; tests
  `tests/unit/test_vlm_bench_gf_cluster.py`, commit c09268c. v1 is unchanged
  and stays the default (`--generator v1`).

---

## Design

### Observed Grouping

The generator builds proximity groups from the scene state alone. It never
reads `item.gt`; a test replaces `gt` with an object that raises on any
attribute access and gets identical output.

| Rule | Value |
|---|---|
| Seeds | robots with status STOPPED, SLOW or STALE |
| Link | two seeds at separation `<=` threshold (the classical chooser's boundary) |
| Group | connected component of size ≥ 2 |
| MOVING robots | join the nearest group with a member within the threshold, but link nothing (no bridging) |
| Threshold | the episode's recorded classical `r_conflict_m` (`item.classical.params`), 1.5 m on all 187 items |
| Labels | A, B, ... by size desc, then closest pair, then ids |

STALE robots seed groups for the reason the `CongestionDetector` close/slow
pair rule includes them: two robots close enough to occlude each other's
marker go STALE together. Only the threshold is a fixed system parameter.
The seed rule (STALE included) and the MOVING-attach rule were set after an
exploratory GT-agreement sweep on these same 187 items, so they are not
independent of the GT. The sweep is reproduced as the sensitivity table in
the Ceiling section. Attach is the choice that moves the numbers; adding STALE
barely does.

### Options

Every option is probed with the real offline M3 (`grounder_offline.ground_command`,
recorded params, overlay, goal references and task intents, no stage 2) and
kept only when M3 executes it as asked, the v1 rule.

| Option | Probe | Kept when |
|---|---|---|
| `yield(Y, passers = group − Y)` | involved `(Y, passers nearest Y first)`, `crossing_order` = passers then Y | M3 grounds a `yield` for Y itself |
| `reverse(group)` | involved = group | a `reverse` action and no `reverse=infeasible` tag |
| v1 pairs inside the group | as v1 | as v1 |
| `reroute(r)`, r in the group | as v1 | waypoints on every reroute |
| v1 pairs with one robot in the group and one in no group | as v1 | as v1 |
| `temporary_wait(group)`, then pair waits | as v1 | always; last in the group |

**Multi-passer yield is supported by M3.** All 187 items ground in derived
mode, and `resolve_yield_roles` honours a full `crossing_order`. Two recorded
ER-2 decisions already executed real 2-passer chains (E17 `6d37a549`, E29
`5622ed9c`). Over all items the default set lists 169 group yields, 100 of
them naming 3-5 robots; 78 execute as multi-passer chains.

**Holds.** M3 can execute a group yield as a smaller crossing and hold the
rest with an unlinked `temporary_wait`: a lane-scoped crossing
(`order=lane_scoped`) or the A26 retreat shield (a bystander whose route
crosses the retreat). v1's `executed_key` ignores these holds. v2 adds
`executed_key_v2`, the v1 key plus a `("hold", ...)` segment, and the option
text names the held robots ("robot_2 holds in place, not in the crossing").
120 listed options carry holds: 44 group yields (21 lane, 15 shield, 8 both)
and 76 pair yields (shield only). They count as "executes as asked" because
the yielder is unchanged and the holds are stated.

### Sections and Prompt

- **Order.** Groups by size desc. Inside a group, group yields (nearest passer
  first), group reverse, in-group pair yields and reverses (closest first),
  reroutes, partial pairs, then waits.
- **Spans two groups.** Pairs with one robot in each of two groups go into
  their own section, flag `--gf-cross-group keep|drop` (default drop).
- **Outside any group.** Pairs with neither robot in a group, and reroutes of
  such robots, go into the outside section, flag `--gf-offgroup keep|drop`
  (default drop). When a scene has no observed group (4/187 items), the
  outside section is kept whatever the flag says, so the model still gets
  options.
- **Prompt.** The live prompt, verbatim, plus a header per section ("Group A:
  robot_1, robot_3, robot_4 (options 1-6)") and the v1 answer instruction. N+1
  is "none of the above".
- **Deduplication.** On `executed_key_v2`, in listing order, so a group option
  wins over a pair that executes the same command.
- **Shuffle.** `--shuffle-options --seed` permutes within each section;
  sections keep their order and "none" stays N+1.
- **Involved set.** The chosen option's robots: the whole group for a group
  option. `ClusterOption.decision()` also carries the `crossing_order`, and a
  test re-grounds every option back to its key.
- **Provenance.** The run config records `gf-candidates-v2`, the grouping rule
  and threshold source, both flags, and per item the threshold, the groups,
  the option count per section, the candidate count and the composed-prompt
  SHA-256.

### v1 Unchanged

- `candidates` v1 output md5 ee3943f0, identical to the v1 report.
- A fresh v1 fixed-option-1 replay reproduces all 187 composed-prompt SHA-256
  values and candidate counts of `run_gf_fixed1.config.json` (v6a, git
  d242828).

---

## Candidate-Set Ceiling (Zero Cost)

The command was `python -m benchmarks.vlm_bench candidates --generator v2`.
Output: `data/bench/v4/candidates_gf_v2.{jsonl,md}` (jsonl md5 a84e4444, default
flags). The `.md` holds every table below plus the per-item lists.

"Inside" means what M3 executes for the recorded ER-2 decision equals a listed
option's v1 executed key (the definition the v1 report used).

| Set (137 recorded positives) | Options mean (median, range) | Resolving mean | Recorded inside (all / resolving) | ≥ 1 resolving | Resolving inside one GT cluster | v1 executed-not-listed now listed |
|---|---|---|---|---|---|---|
| v1 | 19.3 (19, 10-26) | 9.3 | 36 / 33 | 136 | 120 | 0/15 |
| v2 default (drop outside, drop span) | 15.7 (15, 7-29) | 7.5 | **47 / 36** | 136 | 118 | **11/15** |
| v2, keep outside | 17.3 (19, 7-29) | 8.4 | 47 / 36 | 136 | 119 | 11/15 |
| v2, keep span | 19.2 (20, 9-29) | 9.2 | 47 / 36 | 136 | 118 | 11/15 |
| v2, keep both | 20.7 (20, 11-29) | 10.0 | 47 / 36 | 136 | 119 | 11/15 |

- The 11 extra "inside" decisions are 8 recorded 3-5 robot waits, now listed
  as group waits, and 3 resolving decisions: two multi-passer yields (E17
  `6d37a549`, E29 `5622ed9c`) and one 3-mover reverse (E13 `ea23b1a7`). No
  decision that was inside v1 is lost.
- **Still unlisted (4 of 15):**
  - three span two observed groups: E7 `c7aeaac1` (reverse over robots 1-4;
    groups {2,4}, {1,3}), E15 `1f5a4363` (wait over 1, 3, 4, 5; groups
    {2,3,5}, {1,4}) and E17 `9cf93ebe` (reverse over 2-5; groups {2,5}, {3,4});
  - one is a strict subset of a 4-robot group: E20 `079074e5` (wait over
    2, 4, 5; group {1,2,4,5}).
- One positive has no resolving option (E12 `b035a168`, all five robots in
  one group).

### Oracle Choice

The oracle picks, per item, the listed option that a GT-informed chooser would
choose, and scores it with the bench's own `score_item`. GT is read only here,
in `cluster_report.py`, never in the generator. Three rules bound the ceiling:

- **match**, the brief's "best matches GT": the highest Jaccard of the
  option's robots with the union of the active GT clusters, then coverage,
  then matched F1;
- **coverage**: coverage first, then matched F1, then mean per-cluster recall;
- **f1**: matched involved F1 first, then coverage.

On v1, `match` reduces to `coverage`. Every pair whose two robots both lie in
the union has the same Jaccard score, so the coverage tie-break decides.

| Recorded positives (137) | Rule | Coverage | Mean cluster recall | Involved F1 matched | Yielder vs MC |
|---|---|---|---|---|---|
| v1 | match / coverage | **1.000** | 0.548 | 0.672 | 0.778 (14/18) |
| v1 | f1 | 0.620 | 0.579 | 0.871 | 0.842 (16/19) |
| v2 default | match | 0.715 | 0.704 | 0.905 | 0.800 (20/25) |
| v2 default | coverage | 0.766 | 0.704 | 0.899 | 0.900 (18/20) |
| v2 default | f1 | 0.613 | 0.676 | **0.964** | 0.957 (22/23) |
| v2, keep span | match | 0.810 | 0.704 | 0.858 | 0.800 (20/25) |
| v2, keep span | coverage | 1.000 | 0.688 | 0.779 | 0.875 (14/16) |

M3 feasibility is 1.000 in every oracle row, by construction. The
keep-outside rows equal the corresponding drop-outside rows to three decimals
(see the `.md`).

**Coverage ceiling by active GT cluster count** (recorded positives, rule
`coverage`):

| Set | 1 cluster (76) | 2 clusters (61) | 2 clusters, one group touches both (17) | 2 clusters, split across groups (44) |
|---|---|---|---|---|
| v1 | 76 | 61 | 17 | 44 |
| v2 default | 76 | 29 | 17 | 12 |
| v2, keep span | 76 | 61 | 17 | 44 |

### Observed Groups vs Active GT Clusters

All 185 items with at least one active cluster (289 clusters), default rule:

| GT cluster size | n | Equal to a group | Contained in a group | ≥ 2 robots in one group | ≥ 1 robot in a group |
|---|---|---|---|---|---|
| 2 | 146 | 112 | 140 | 140 | 140 |
| 3 | 97 | 68 | 82 | 95 | 95 |
| 4 | 20 | 4 | 9 | 20 | 20 |
| 5 | 26 | 15 | 15 | 26 | 26 |
| all | 289 | **199** | **246** | 281 | 281 |

- **Per item.** Every active cluster sits inside one observed group on
  142/185 items. One group touches every active cluster on 99/185.
- **Groups per item.** 0 groups on 4 items, 1 on 98, 2 on 85.
- **Why agreement is high.** The GT clusters (A33(5) contact episodes) and the
  observed groups both come from scene geometry, so part of this agreement is
  definitional. It is not a leak: the generator reads no GT field (tested).

**Grouping-rule sensitivity.** These are the same rules as the exploratory
sweep that preceded the default's seed and attach choices:

| Rule | Clusters equal | Contained | Items, every cluster contained | Items, one group touches all |
|---|---|---|---|---|
| **default**: 1.5 m (`r_conflict_m`), +STALE, MOVING attach | 199/289 | 246/289 | 142/185 | 99/185 |
| 0.5 m (M5 `proximity_threshold_m`), +STALE, attach | 219/289 | 219/289 | 117/185 | 87/185 |
| 1.0 m, +STALE, attach | 212/289 | 231/289 | 128/185 | 91/185 |
| 2.0 m, +STALE, attach | 166/289 | 261/289 | 157/185 | 114/185 |
| 1.5 m, +STALE, no attach | 192/289 | 219/289 | 118/185 | 96/185 |
| 1.5 m, STOPPED/SLOW only, attach | 198/289 | 245/289 | 141/185 | 98/185 |
| 1.5 m, STOPPED/SLOW only, no attach | 195/289 | 207/289 | 109/185 | 94/185 |

### Hypothesis (b): the Closest Pair Off-Conflict

v1's option 1 (generator order, the closest executable yield) has both robots
inside one active GT cluster on 103/137 positives. On those items the closest
pair is on-conflict; on 34 it is not. v2's option 1 is inside one cluster on
83/137, because a group option names 3-5 robots that can exceed a 2-robot
cluster.

---

## Fixed-Option Sanity Replay (FakeBackend, Option 1)

The command was `replay --prompt-variant grounding_first --generator v2
--fixed-option 1 --backend gemini` with a scratch `--cache-dir`, at git
c09268c. Every base prompt reproduced its stored hash (0 skipped), with 165
cache misses and 22 hits (identical prompts), as in v1. The outputs are
`data/bench/v4/run_gf2_fixed1_<offgroup>_<crossgroup>.*`; the default jsonl
md5 is 1ee79f5a.

Option 1 is always a group option or the first in-group option, so the four
flag settings give identical option-1 scores. Option 1 was a yield on 129
items, a reverse on 52 and a wait on 6, naming 2.98 robots on average (v1:
2.0).

| Recorded positives (137) | Recorded ER-2 | v1 option 1 | v2 option 1 | v2 oracle (match) | v2 oracle (coverage) |
|---|---|---|---|---|---|
| M3 feasibility | 0.496 (68/137) | 1.000 | 1.000 | 1.000 | 1.000 |
| yield feasibility | 0.444 (24/54) | 1.000 (122/122) | 1.000 (88/88) | 1.000 (66/66) | 1.000 (62/62) |
| yielder vs M3 oracle | 0.458 (11/24) | 1.000 (122/122) | 1.000 (88/88) | n/a | n/a |
| cluster coverage | 0.686 (94/137) | 0.526 (72/137) | **0.672 (92/137)** | 0.715 (98/137) | 0.766 (105/137) |
| mean per-cluster recall | 0.710 | 0.423 | **0.618** | 0.704 | 0.704 |
| involved F1, matched (n) | 0.911 (136) | 0.733 (124) | **0.802 (136)** | 0.905 (137) | 0.899 (137) |
| involved F1, unconditional | 0.904 | 0.663 | 0.796 | 0.905 | 0.899 |
| yielder vs MC first conflict | 0.467 (7/15) | 0.759 (22/29) | 0.793 (23/29) | 0.800 (20/25) | 0.900 (18/20) |

The oracle columns were scored without the geometry oracle, hence n/a; every
listed yielder is executable by construction. Over all 187 items, v2 option 1
gives feasibility 187/187, coverage 99/185
(v1: 75/185), recall 0.584 (v1: 0.398) and matched F1 0.835 (v1: 0.750).

---

## Real-Model Replay Commands (Run 2026-11-12)

**Status (Rev 2):** all four commands below were run on 2026-11-12 at git
8a373bb (items md5 f1dc2ccb) and completed on 187/187 items with zero
API-error rows. The results are in the next section. The text below is the
Rev 1 plan, kept as written ("owner's API key" and "cap" refer to the state
before the runs). The ER-2 runs used `--cache-dir data/bench/cache/r5a` and
`r5b`, the Sonnet runs `r6a` and `r6b`.

Each command needs the owner's API key in the environment. The ER-2 runs also
need the Gemini monthly spend cap raised (see the 2026-10-23 replay report).
Run them from the repo root with the repo venv. Run both span settings, so the
owner can pick the span default with data in hand (see Owner Rulings).

```bash
python -m benchmarks.vlm_bench replay --backend gemini --prompt-variant grounding_first \
  --generator v2 --items data/bench/v4/items_live31.jsonl \
  --out data/bench/v4/run_r5a_er2_gf2.jsonl --summary data/bench/v4/run_r5a_er2_gf2.md \
  --cache-dir data/bench/cache/r5a
python -m benchmarks.vlm_bench replay --backend gemini --prompt-variant grounding_first \
  --generator v2 --gf-cross-group keep --items data/bench/v4/items_live31.jsonl \
  --out data/bench/v4/run_r5b_er2_gf2_span.jsonl --summary data/bench/v4/run_r5b_er2_gf2_span.md \
  --cache-dir data/bench/cache/r5b
python -m benchmarks.vlm_bench replay --backend anthropic --prompt-variant grounding_first \
  --generator v2 --items data/bench/v4/items_live31.jsonl \
  --out data/bench/v4/run_r6a_sonnet55_gf2.jsonl --summary data/bench/v4/run_r6a_sonnet55_gf2.md \
  --cache-dir data/bench/cache/r6a
python -m benchmarks.vlm_bench replay --backend anthropic --prompt-variant grounding_first \
  --generator v2 --gf-cross-group keep --items data/bench/v4/items_live31.jsonl \
  --out data/bench/v4/run_r6b_sonnet55_gf2_span.jsonl \
  --summary data/bench/v4/run_r6b_sonnet55_gf2_span.md --cache-dir data/bench/cache/r6b
```

Add `--shuffle-options --seed 20261023` for a within-section position check.
That doubles the cost of the run it is added to.

**Cost estimate.** It scales the v1 grounding-first token counts by the ratio
of mean composed-prompt length:

- v2 default / v1 = 0.997;
- v2 keep span / v1 = 1.043;
- measured over the 187 rebuilt prompts, system prompt included.

| Run | Basis | Billed calls | Est $ |
|---|---|---|---|
| R5a ER-2 v2 default | R2: $0.879 / 110 calls | 165 | ~1.32 |
| R5b ER-2 v2 keep span | same, ×1.043 | 165 | ~1.38 |
| R6a Sonnet 5.5 v2 default | R4b: $2.556 / 165 calls | 165 | ~2.55 |
| R6b Sonnet 5.5 v2 keep span | same, ×1.043 | 165 | ~2.67 |
| All four | | 660 | **~7.9** |

These are formula estimates in the 2026-10-23 report's method, not invoices.

---

## Real-Model Replay Results (Rev 2, 2026-11-12)

Four runs at git 8a373bb on `items_live31.jsonl` (md5 f1dc2ccb), each complete
at 187/187 items with zero API-error rows. Files:
`data/bench/v4/run_{r5a_er2_gf2,r5b_er2_gf2_span,r6a_sonnet55_gf2,r6b_sonnet55_gf2_span}.{jsonl,md,config.json}`
(untracked). Comparison rows R1, R2, R4a and R4b are the existing full-187
runs of the 2026-10-23 report. R3 (shuffled) is omitted; it matched R2 within
0.01 on every headline metric.

| Id | Backend / model | Variant | Generator | Cross-group span pairs |
|---|---|---|---|---|
| R5a | `gemini` / gemini-robotics-er-2-preview | grounding_first | v2 | drop (default) |
| R5b | same | grounding_first | v2 | keep |
| R6a | `anthropic` / claude-sonnet-5-5 | grounding_first | v2 | drop (default) |
| R6b | same | grounding_first | v2 | keep |

**Run provenance (read before using the numbers).**

- **R5a and R5b are each a two-part run.** About 78 answers came from a first
  attempt earlier the same night, which stopped on HTTP 402 (prepaid credits
  depleted). The rest were served after a top-up, with the cache resuming the
  finished items. Failed calls were not cached. The two parts are not
  distinguishable in the output, so a small drift between the parts is not
  separable from the model's own variation.
- **R6a and R6b are single clean runs.** An earlier R6 attempt failed on every
  call with HTTP 401 (stale key) and billed nothing.
- ER-2 has no temperature control and Sonnet 5.5's `temperature` is never
  sent (see the 2026-10-23 report), so none of the four runs is seeded.

### Method and Reproduction Check

The run `.md` summaries compute coverage and F1 over each run's own positives
(183 for R6a, 158 for R5a). They are not comparable with the Rev 2 tables of
`docs/reports/2026-10-23-v4-replay-er2.md`, which use the 137 recorded
positives. The tables below use the Rev 2 method:
`data/bench/v4/analysis_20261023/analyze.py` (untracked; the bench's own
`summarize` and `ground_command`), restricted to the 137 recorded-positive
items, with `valid / positive` counted inside that set. "Cluster coverage" is
covered items over all 137 (a "none" answer counts as uncovered), as in
Rev 2.

Before the new runs were read, the same script reproduced every R1, R2, R4a
and R4b figure of the Rev 2 137-item table, for example R2 coverage 0.474
(65/137), recall 0.443, matched F1 0.840 (113), MC yielder 22/25, and R4b
0.577 (79/137), 0.497, 0.807 (130), 21/25. On the all-187 subset it also gives
R2 coverage over positives 0.436 (68/156), matched F1 0.830, MC 22/26 and R4b
0.474 (82/173), 0.804, 21/26. Those all-187 figures are the 0.436 and 0.474
that circulate in project notes. They are not on the 137-item basis, and the
137-item values for the same runs are 0.474 and 0.577. This report uses the
137-item basis throughout.

The extra splits (cluster count, option kind, option 1, held robots) come from
three untracked scripts in `data/bench/v4/analysis_20261112/` (`extras.py`,
`paired.py`, `rulings.py`). They read `item.gt` and the bench's
`_cluster_agreement`, so they are analysis only, never generator input. The
split counts reproduce the Rev 1 figures: 76 one-cluster and 61 two-cluster
positives, of which 17 have one group touching both clusters and 44 are split.
Regenerating each item's option list with the run's flags matched the
recorded candidate count on 137/137 items in all four runs, so the chosen
option number maps to the option the model saw.

### Headline Table (137 Recorded Positives)

| Metric | Recorded ER-2 | R1 ER-2 base | R2 ER-2 GF v1 | R5a ER-2 GF v2 drop | R5b ER-2 GF v2 keep | R4a Sonnet base | R4b Sonnet GF v1 | R6a Sonnet GF v2 drop | R6b Sonnet GF v2 keep |
|---|---|---|---|---|---|---|---|---|---|
| valid / positive | 137 / 137 | 137 / 131 | 137 / 114 | 137 / 116 | 137 / 115 | 137 / 128 | 137 / 130 | 137 / 137 | 137 / 137 |
| M3 feasibility, lenient | 0.496 (68/137) | 0.519 (68/131) | 1.000 (114/114) | 1.000 (116/116) | 1.000 (115/115) | 0.625 (80/128) | 1.000 (130/130) | 1.000 (137/137) | 1.000 (137/137) |
| M3 feasibility, strict | 0.372 (51/137) | 0.374 (49/131) | 1.000 (114/114) | 1.000 (116/116) | 1.000 (115/115) | 0.523 (67/128) | 1.000 (130/130) | 1.000 (137/137) | 1.000 (137/137) |
| cluster coverage | 0.686 (94/137) | 0.642 (88/137) | 0.474 (65/137) | 0.496 (68/137) | 0.504 (69/137) | 0.664 (91/137) | 0.577 (79/137) | 0.620 (85/137) | 0.599 (82/137) |
| mean per-cluster recall | 0.710 | 0.649 | 0.443 | 0.500 | 0.498 | 0.713 | 0.497 | 0.621 | 0.611 |
| involved F1, matched (n) | 0.911 (136) | 0.898 (131) | 0.840 (113) | 0.850 (116) | 0.856 (115) | 0.917 (128) | 0.807 (130) | 0.861 (137) | 0.875 (137) |
| involved F1, unconditional | 0.904 | 0.859 | 0.693 | 0.720 | 0.719 | 0.857 | 0.766 | 0.861 | 0.875 |
| yielder vs MC first conflict | 0.467 (7/15) | 0.273 (3/11) | 0.880 (22/25) | 0.875 (21/24) | 0.870 (20/23) | 0.391 (9/23) | 0.840 (21/25) | 0.875 (21/24) | 0.769 (20/26) |
| "none" or negative answers | 0 | 6 | 23 | 21 | 22 | 9 | 7 | 0 | 0 |

- **Lenient vs strict.** Strict means the grounded command executes the
  decision as asked, as in Rev 2. They coincide at 1.0 for every grounding-first
  run, by construction.
- **Yielder vs MC.** The denominator is the items where the MC oracle has a
  first-conflict yielder and the run named one, so it differs per run (23-26
  for the GF runs). One item moves the rate by about 0.04.
- **Matched F1.** Its n is the items that have both an answer and a GT match.
  It is not comparable across rows with different n (R2 113, R5a 116); the
  unconditional row counts every item, with 0 for a missing answer.
- **"None" or negative.** For the baseline runs these are
  `congestion_detected=false` answers; for the GF runs "none of the above".
  Parse failures: 0 in every GF run. A baseline `junction_clear` is a
  positive answer that M3 refuses (R1 31, R4a 7 on the 137), not a negative.
- Over all 187 items, "none" or negative is 29 / 29 (R5a, R5b) and 4 / 3 (R6a,
  R6b), against 31 (R2) and 14 (R4b).

### Strategy Mix (137 Recorded Positives)

| Run | yield | reverse | temporary_wait | junction_clear | Other |
|---|---|---|---|---|---|
| Recorded | 54 | 25 | 13 | 39 | reroute 3, priority_override 2, convoy 1 |
| R1 | 56 | 28 | 9 | 31 | reroute 6, convoy 1 |
| R2 | 70 | 18 | 26 | 0 | none 23 |
| R5a | 70 | 29 | 17 | 0 | none 21 |
| R5b | 68 | 26 | 21 | 0 | none 22 |
| R4a | 75 | 21 | 19 | 7 | reroute 3, priority_override 3 |
| R4b | 70 | 29 | 31 | 0 | none 7 |
| R6a | 68 | 31 | 38 | 0 | none 0 |
| R6b | 69 | 31 | 37 | 0 | none 0 |

No grounding-first run chose `reroute`. The v2 runs are not more yield-heavy
than v1: yield counts are within 2 of the matching v1 run. Sonnet answers
`temporary_wait` more often than ER-2 under v2 (37-38 vs 17-21).

### Coverage by Active GT Cluster Count

Covered items over the recorded positives in each stratum. The last two rows
are the oracle ceilings from the Candidate-Set Ceiling section (rule
`coverage`).

| Run | 1 cluster (76) | 2 clusters (61) | 2 clusters, one group touches both (17) | 2 clusters, split across groups (44) |
|---|---|---|---|---|
| R1 ER-2 base | 72 (0.947) | 16 (0.262) | 7 | 9 |
| R2 ER-2 GF v1 | 62 (0.816) | 3 (0.049) | 3 | 0 |
| R5a ER-2 GF v2 drop | 60 (0.789) | 8 (0.131) | 6 | 2 |
| R5b ER-2 GF v2 keep | 61 (0.803) | 8 (0.131) | 6 | 2 |
| R4a Sonnet base | 68 (0.895) | 23 (0.377) | 9 | 14 |
| R4b Sonnet GF v1 | 71 (0.934) | 8 (0.131) | 5 | 3 |
| R6a Sonnet GF v2 drop | 76 (1.000) | 9 (0.148) | 7 | 2 |
| R6b Sonnet GF v2 keep | 76 (1.000) | 6 (0.098) | 5 | 1 |
| Oracle ceiling, v2 drop | 76 | 29 | 17 | 12 |
| Oracle ceiling, v2 keep span | 76 | 61 | 17 | 44 |

The split uses GT, so it is analysis only. The 1-cluster and 2-cluster cells
sum to the headline coverage (for example R6a 76 + 9 = 85).

### What the Models Chose

The chosen option is mapped back through the regenerated list. A "group"
option is a group yield, group reverse or group wait. Its robot count is the
whole group, so a 2-robot group option names the same two robots as a pair.

| Run | Answered | Group | Pair | Partial pair | Span pair | None | Option 1 chosen (of 137) | Involved ≥ 3 robots |
|---|---|---|---|---|---|---|---|---|
| R2 ER-2 GF v1 | 114 | n/a | 114 | n/a | n/a | 23 | 62 (0.453) | 0 |
| R5a ER-2 v2 drop | 116 | 75 | 37 | 4 | 0 (dropped) | 21 | 50 (0.365) | 35 |
| R5b ER-2 v2 keep | 115 | 75 | 37 | 2 | 1 | 22 | 48 (0.350) | 34 |
| R4b Sonnet GF v1 | 130 | n/a | 130 | n/a | n/a | 7 | 65 (0.474) | 0 |
| R6a Sonnet v2 drop | 137 | 96 | 32 | 9 | 0 (dropped) | 0 | 55 (0.401) | 56 |
| R6b Sonnet v2 keep | 137 | 93 | 38 | 6 | 0 | 0 | 53 (0.387) | 50 |

- **Group over pair.** Group options are 65% of ER-2 answers (75/116) and 70%
  of Sonnet answers (96/137) under drop. About half of them are 2-robot
  groups: only 35 of 116 (ER-2) and 56 of 137 (Sonnet) answers name three or
  more robots. v1 answers name 2 (mean involved 2.0 for R2 and R4b).
- **Covered by kind.** A group pick covers no more than a pair pick: R5a 42/75
  vs 23/37; R6a 58/96 vs 20/32 (partial pairs 3/4 and 7/9).
- **Option 1.** In v2 it is a group option whenever a group exists. Both models
  choose it less than under v1 (ER-2 0.453 → 0.365; Sonnet 0.474 → 0.401). A
  fixed option-1 chooser covers 92/137 (0.672); every realised run is below
  that. The no-first-slot-bias finding of the 2026-10-23 report was shown for
  v1 and ER-2 only. v2 was not shuffled here, so its option-1 share is not
  separated from position.
- **Span pairs.** The keep runs chose a span-section option on 1 of 137
  answers (R5b) and 0 of 137 (R6b), although keep lists more options (mean
  19.2 vs 15.7 per item over the 137, from the ceiling table) and the prompt is
  3-4% longer in input tokens.

### Realised vs the Oracle Ceilings

The oracle rows are the Candidate-Set Ceiling and fixed-option rows above. The
oracle chooses with GT, so its rows bound the option list, not a model.

| 137 recorded positives | Coverage | Mean recall | Matched F1 (n) | F1 unconditional |
|---|---|---|---|---|
| Oracle v2 drop, rule `match` | 0.715 | 0.704 | 0.905 (137) | 0.905 |
| Oracle v2 drop, rule `coverage` | 0.766 | 0.704 | 0.899 (137) | 0.899 |
| Oracle v2 drop, rule `f1` | 0.613 | 0.676 | 0.964 (137) | 0.964 |
| Fixed option 1 (v2) | 0.672 | 0.618 | 0.802 (136) | 0.796 |
| R5a ER-2 v2 drop | 0.496 | 0.500 | 0.850 (116) | 0.720 |
| R6a Sonnet v2 drop | 0.620 | 0.621 | 0.861 (137) | 0.861 |
| Oracle v2 keep span, rule `match` | 0.810 | 0.704 | 0.858 (137) | 0.858 |
| Oracle v2 keep span, rule `coverage` | 1.000 | 0.688 | 0.779 (137) | 0.779 |
| R5b ER-2 v2 keep | 0.504 | 0.498 | 0.856 (115) | 0.719 |
| R6b Sonnet v2 keep | 0.599 | 0.611 | 0.875 (137) | 0.875 |

- Realised coverage is 0.50-0.62 against drop ceilings of 0.72-0.77 and a keep
  ceiling of 1.0. The gap is a choice problem, as Rev 1 interpretation 2
  expected.
- Sonnet's unconditional F1 (0.861 drop, 0.875 keep) is above the fixed
  option-1 chooser (0.796). The oracle rows optimise one metric each, so a
  realised F1 can sit above an oracle row that optimised coverage (R6b 0.875 vs
  the keep `match` row 0.858).
- Realised mean recall (0.50 ER-2, 0.61-0.62 Sonnet) is at or below the fixed
  option-1 chooser's 0.618 and below every oracle row.

### Same-Prompt Variation (a Noise Guide, Not an Estimate)

R5a/R5b and R6a/R6b were run with separate caches. Where the composed prompt
is byte-identical between the drop and keep run (no span section for that
item), the two answers are independent calls on the same prompt.

| Pair | Identical-prompt items (of 137 positives) | Decision differs | Covered flag differs |
|---|---|---|---|
| R5a vs R5b (ER-2) | 92 | 14 (0.15) | 10 |
| R6a vs R6b (Sonnet) | 92 | 19 (0.21) | 3 |

"Decision differs" compares strategy, involved set and yielder. On the 45
items whose prompt differs (a span section exists), decisions differ on 11
(ER-2) and 16 (Sonnet), 0.24 and 0.36. So at identical prompts a re-ask
changes the decision on 15-21% of items, and the span option's effect is not
clearly above that. Net coverage differences of a few items are within it.

Paired coverage flips, only-first vs only-second: R2 vs R5a 8 vs 11; R4b vs
R6a 4 vs 10; R5a vs R5b 5 vs 6; R6a vs R6b 4 vs 1; R5a vs R6a 4 vs 21. R5a and
R5b are each a mix of two sessions, so the ER-2 pair is a looser guide than
the Sonnet pair.

### All 187 Items

| Metric | R2 | R5a | R5b | R4b | R6a | R6b |
|---|---|---|---|---|---|---|
| valid / positive | 187 / 156 | 187 / 158 | 187 / 158 | 187 / 173 | 187 / 183 | 187 / 184 |
| M3 feasibility, lenient / strict | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 |
| cluster coverage (valid, ≥ 1 cluster) | 0.368 (68/185) | 0.384 (71/185) | 0.395 (73/185) | 0.443 (82/185) | 0.481 (89/185) | 0.465 (86/185) |
| involved F1, matched | 0.830 | 0.883 | 0.892 | 0.804 | 0.891 | 0.902 |
| yielder vs MC first conflict | 22/26 | 21/24 | 20/23 | 21/26 | 21/25 | 20/26 |

The 50 items beyond the 137 are the 38 E10 backend-failed items and 12
recorded negatives. The run `.md` files print coverage "over positives" (for
example R6a 0.486, 89/183). That figure is over each run's own positives and
must not be set beside the 137-item rows.

### Cost

Not stamped in the run files. Estimated from `token_usage` in each cache
directory (every cache file is one billed call), with the 2026-10-23 report's
method: ER-2 $1/M input and $5/M output plus thought tokens; Sonnet 5.5 $2/M
input and $10/M output. The same calculation reproduces the stamped R2 $1.309
and R4b $2.556 from their caches.

| Run | Cache files (billed calls) | Tokens in / out (+thought) | Est $ | Rev 1 forecast |
|---|---|---|---|---|
| R5a | 165 | 673,106 / 52,011 (+67,694) | 1.272 | ~1.32 |
| R5b | 166 | 698,710 / 51,866 (+71,730) | 1.317 | ~1.38 |
| R6a | 165 | 864,598 / 81,653 | 2.546 | ~2.55 |
| R6b | 165 | 892,384 / 82,913 | 2.614 | ~2.67 |
| All four | 661 | | **~7.75** | ~7.9 |

These are estimates, not invoices. Whether the HTTP 402 and 401 failures
billed anything cannot be verified from the files; calls refused before
generation normally bill nothing. Keep-span input tokens were 3.2-3.8% above
drop (ER-2 698,710 vs 673,106; Sonnet 892,384 vs 864,598), a little under the
4.3% forecast from prompt length.

---

## Interpretation (Conservative)

1. Feasibility 1.0 holds by construction for v2 too. All 3,963 options listed under keep/keep across the 187 items (78 of them multi-passer yields) re-ground to their own `executed_key_v2`. This shows the mapping is lossless, not that a model chooses well.
2. Hypothesis (a) does not hold for coverage as the bench defines it. Under `min_overlap = 1`, a pair that takes one robot from each cluster covers a two-cluster item, so v1 pairs already reach oracle coverage 137/137. v1 reaches coverage 1.0 (at F1 0.67) or matched F1 0.87 (at coverage 0.62), but not both. The real-replay coverage loss (0.38-0.58) is a choice problem, not a listing limit.
3. On 2-cluster items, coverage and matched F1 pull in opposite directions. The v2 default (group options) raises the F1 ceiling to 0.90-0.96 but caps coverage at 0.72-0.77, only a little above the recorded ER-2 0.686; keeping span pairs restores the coverage ceiling to 1.0 and lowers the F1 ceiling to 0.78-0.86.
4. v2 lifts the F1 ceiling (0.87 → 0.96) and what a naive chooser gets: a fixed option-1 chooser goes from recall 0.42 to 0.62, coverage 0.53 → 0.67 and matched F1 0.73 → 0.80, against recorded ER-2 0.71 / 0.69 / 0.91.
5. Observed groups match the active GT clusters well (246/289 contained, 199 equal). The binding limit is that 44/61 two-cluster positives have their clusters in different observed groups. This agreement is partly definitional, since both come from geometry.
6. Hypothesis (b) is weaker than assumed: v1's closest-pair option 1 is inside one active cluster on 103/137 positives. Whether a real model's choices improve under v2 needs the replays above.
7. (Rev 1) One fixed chooser and three GT oracles on one item set; no model was asked. Nothing in the Rev 1 sections estimates model behaviour or variance. Items 8-13 add the real-model runs.
8. (Rev 2) v2 recovers little of the coverage that v1 grounding-first lost. On the 137 recorded positives ER-2 goes 0.474 (R2) → 0.496 / 0.504 (R5a / R5b), against 0.642 for its baseline (R1). Sonnet goes 0.577 (R4b) → 0.620 / 0.599 (R6a / R6b), against 0.664 for its baseline (R4a). Net gains are 3-6 items, with paired flips of 11 vs 8 (R2 → R5a) and 10 vs 4 (R4b → R6a), and a same-prompt re-ask flips the covered flag on up to 10 of 92 items (ER-2). Mean recall moves more (ER-2 0.443 → 0.50; Sonnet 0.497 → 0.61-0.62, equal to a fixed option-1 chooser's 0.618). Matched F1 stays at or above its v1 value (ER-2 0.840 → 0.85; Sonnet 0.807 → 0.86-0.875), with n differing across ER-2 rows. Neither model beats the fixed option-1 chooser on coverage (0.672). Where the gain sits is inferred from the strata: Sonnet's comes from one-cluster items (71 → 76 of 76) and from "none" falling 7 → 0, ER-2's from two-cluster items (3 → 8) while its one-cluster coverage did not rise (62 → 60-61).
9. (Rev 2) Two-cluster items are not solved. Both models cover 6-9 of 61 (ceilings 29 drop, 61 keep), and 1-2 of 44 split items. The free-form baselines cover more (R1 16/61, R4a 23/61) by naming larger sets. Group options are 65-70% of v2 answers but about half of those are 2-robot groups, and a group pick covers no more often than a pair pick. The lever lists cluster-level options, and the models mostly do not use them to name a whole cluster, on one run each.
10. (Rev 2) Keep vs drop span pairs made no measurable difference. Coverage is 69 vs 68 (ER-2) and 82 vs 85 (Sonnet); a span-pair option was chosen on 1 and 0 of 137 answers; the split-item coverage is the same to within one item. Decisions differ on 25 (ER-2) and 35 (Sonnet) of 137 items between the drop and keep runs, but a re-ask on an identical prompt already differs on 14 and 19 of 92. The keep ceiling advantage (1.0 vs 0.766) is not used by either model. Keep costs about 3-4% more input tokens.
11. (Rev 2) Under v2, Sonnet 5.5 is ahead of ER-2 on coverage (0.620 vs 0.496 drop; 0.599 vs 0.504 keep), recall (0.62 vs 0.50) and unconditional F1 (0.86-0.875 vs 0.72). The gap is mostly "none": ER-2 answers it on 21-22 of 137, Sonnet on 0, and each "none" is an uncovered item. Among answered items coverage is close (ER-2 0.586 and 0.600, Sonnet 0.620 and 0.599; computed from the tables, not a separate run). MC yielder agreement is the same under drop (21/24 each). Sonnet names larger sets (56 vs 35 answers with three or more robots). Whether ER-2's "none" would shrink with a different "none" instruction is not tested.
12. (Rev 2) Against the oracle, realised coverage is 0.50-0.62 vs ceilings of 0.72-0.77 (drop) and 1.0 (keep). The ceiling gap reflects choice, not listing, as in item 2, and it is not closed by listing groups.
13. (Rev 2) Strict and lenient M3 feasibility are 1.0 in all four runs, by construction, as in item 1. Yielder agreement with the MC oracle is 0.77-0.88 for every GF run, in line with R2 and R4b.

---

## Owner Rulings Needed

- **Span-pair default.** `--gf-cross-group drop` (the brief's within-group
  design, coverage ceiling 0.766) or `keep` (coverage ceiling 1.0, F1 ceiling
  0.78-0.86)? The replay commands above run both.
  - *Rev 2 evidence.* The two settings gave the same realised coverage within
    noise (ER-2 0.496 / 0.504, Sonnet 0.620 / 0.599) and a span pair was
    chosen on 1 and 0 of 137 answers, so the ceiling difference was not
    realised by either model. Keep adds about 3-4% input tokens. This is one
    run per setting.
- **Coverage target.** Is `min_overlap = 1` coverage the right target for a
  lever meant to "name the whole cluster"? Mean per-cluster recall or matched
  F1 may be the better primary metric for v2.
  - *Rev 2 evidence.* The metrics disagree on what v2 did. Recall rose more
    than coverage (Sonnet 0.497 → 0.62, coverage 0.577 → 0.60-0.62; ER-2 0.443
    → 0.50, coverage 0.474 → 0.50), and matched F1 held or rose. Against the
    baselines, v2 is still below on coverage and recall (Sonnet baseline 0.664
    and 0.713) and below on matched F1 (ER-2 baseline 0.898, Sonnet 0.917).
- **Credit for held or unmoved robots.** A group option's involved set names
  robots that M3 only holds (lane-scoped, shield) or does not move (the
  "not moved" robots of a group reverse). The bench scores the involved set,
  so these robots earn coverage and F1 credit. Accept, or score the executed
  set instead?
  - *Rev 2 evidence.* Of the options chosen, 30 (R5a), 32 (R5b), 36 (R6a)
    and 33 (R6b) carry holds. Scoring those options with the held robots
    removed from the involved set flips coverage on 0, 0, 2 and 1 items
    (approximate: it removes only the listed holds, not the "not moved"
    robots of a group reverse, which were not examined).
- **No-group fallback.** On 4 items with no observed group, the outside
  section is kept despite `--gf-offgroup drop`. This is a deviation from the
  brief, made so those items still have options.
  - *Rev 2 evidence.* Of the 4 no-group items, 2 are recorded positives. All
    four runs answered both and covered both (2/2); no "none" on them. Two
    items are too few to say more.
- **Union-of-groups wait.** Not implemented. A single hold over every observed
  group would let one option cover split two-cluster items without pair
  options. Should it be added?
  - *Rev 2 evidence.* The need exists in the data: the models cover 1-2 of 44
    split two-cluster positives, and a pair option from the span section was
    almost never chosen. Whether a union-of-groups wait would be chosen was
    not tested. Chosen `temporary_wait` is already common under v2 (17-21
    ER-2, 37-38 Sonnet of 137).

---

## Approximations and Limits

- **Status labels.** The grouping uses M1 status labels (STOPPED, SLOW,
  STALE), not a velocity threshold. MOVING robots attach without bridging.
- **Threshold and rules.** The threshold is the recorded classical
  `r_conflict_m`, which is 1.5 m on every item, so it was never varied in
  practice. The seed and MOVING-attach rules were chosen after a GT-agreement
  sweep on the same 187 items. Attach raises containment from 219 to 246
  clusters (items with every cluster contained: 118 → 142); a held-out item
  set would be needed to check it.
- **Holds count as executed.** Options with lane-scoped or shield holds
  count as executing as asked, because the yielder is unchanged and the holds
  are named in the text and the key. v1's `executed_key` (unchanged) ignores
  holds.
- **Partial pairs.** Pairs with one robot in a group and one in no group are
  listed under that group, below its in-group pairs.
- **Stage 2 is not run.** A yield option names the default retreat, as in v1.
- **Oracle rules.** The oracle rows use GT to choose. They bound what a chooser
  could reach on this option list; they are not a model result. The `match`
  rule's union-Jaccard is one reading of "best matches GT".
- **What "inside" measures.** It uses v1's key, so the 15
  executed-not-listed count is comparable with the v1 report. On the v2 key
  the in-set count is in the jsonl (`in_set_all_v2key`).
- **Output files.** `data/bench/` is gitignored. The candidate and run files
  live in the worktree `vgu-vlm-swarm-v6b`. The Rev 2 run files and analysis
  scripts live in the worktree `vgu-vlm-swarm-v6a` (`data/bench/v4/`,
  `data/bench/v4/analysis_20261112/`).

### Rev 2 Limits

- **One run per configuration.** There is no variance estimate. The
  same-prompt table is a rough guide only (92 items, independent calls in
  separate caches), and differences of a few items on 137 are within it.
- **R5a and R5b are two-session runs.** About 78 answers each come from an
  earlier attempt the same night; the rest were served after a top-up.
- **Text-only.** Every replay used the neutral grey image, not the annotated
  frame the live call saw. ER-2 has no temperature control and Sonnet's
  temperature is not sent.
- **Exploratory v4 only.** These are pilot and tranche-1 scenes. Nothing here
  pools with or replaces a prereg-v3 confirmatory measure (A32-A36).
- **The rules were partly tuned on these same 187 items.** The seed and
  MOVING-attach rules were chosen after a GT-agreement sweep on this set, so
  the v2 numbers are not held-out.
- **v2 is unshuffled.** Position effects were checked for v1 and ER-2 only.
- **The splits use GT.** The one-cluster / two-cluster and touch / split rows
  come from the GT clusters and are analysis, not something a model saw.
- **Cost is an estimate.** It follows the earlier report's formula; the
  provider bill was not checked.

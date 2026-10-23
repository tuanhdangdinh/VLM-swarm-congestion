# v4 Grounding-First v2: Cluster-Level Candidates, Ceiling on 31 Live S1b Episodes

**Prepared:** 2026-10-23

**Revision history:**

- Initial draft: `gf-candidates-v2` generator, zero-cost ceiling, oracle choice and fixed-option sanity replay.

---

## Scope

This report covers v4 lever 2, cluster-level candidate enumeration for the
grounding-first `replay` variant of the offline bench
(`docs/specs/v4_vlm_bench.md`). It follows the v1 ceiling report
(`docs/reports/2026-10-23-v4-grounding-first-candidates.md`) and the first
real-model replays (`docs/reports/2026-10-23-v4-replay-er2.md`, conclusion 8).

- **Zero API calls.** No key was loaded and no network backend ran. The
  fixed-option runs use the zero-network `FixedOptionBackend` with caches in a
  scratch directory, never under `data/bench/cache`.
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

## Real-Model Replay Commands (Not Run)

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

## Interpretation (Conservative)

1. Feasibility 1.0 holds by construction for v2 too. All 3,963 options listed under keep/keep across the 187 items (78 of them multi-passer yields) re-ground to their own `executed_key_v2`. This shows the mapping is lossless, not that a model chooses well.
2. Hypothesis (a) does not hold for coverage as the bench defines it. Under `min_overlap = 1`, a pair that takes one robot from each cluster covers a two-cluster item, so v1 pairs already reach oracle coverage 137/137. v1 reaches coverage 1.0 (at F1 0.67) or matched F1 0.87 (at coverage 0.62), but not both. The real-replay coverage loss (0.38-0.58) is a choice problem, not a listing limit.
3. On 2-cluster items, coverage and matched F1 pull in opposite directions. The v2 default (group options) raises the F1 ceiling to 0.90-0.96 but caps coverage at 0.72-0.77, only a little above the recorded ER-2 0.686; keeping span pairs restores the coverage ceiling to 1.0 and lowers the F1 ceiling to 0.78-0.86.
4. v2 lifts the F1 ceiling (0.87 → 0.96) and what a naive chooser gets: a fixed option-1 chooser goes from recall 0.42 to 0.62, coverage 0.53 → 0.67 and matched F1 0.73 → 0.80, against recorded ER-2 0.71 / 0.69 / 0.91.
5. Observed groups match the active GT clusters well (246/289 contained, 199 equal). The binding limit is that 44/61 two-cluster positives have their clusters in different observed groups. This agreement is partly definitional, since both come from geometry.
6. Hypothesis (b) is weaker than assumed: v1's closest-pair option 1 is inside one active cluster on 103/137 positives. Whether a real model's choices improve under v2 needs the replays above.
7. One fixed chooser and three GT oracles on one item set; no model was asked. Nothing here estimates model behaviour or variance.

---

## Owner Rulings Needed

- **Span-pair default.** `--gf-cross-group drop` (the brief's within-group
  design, coverage ceiling 0.766) or `keep` (coverage ceiling 1.0, F1 ceiling
  0.78-0.86)? The replay commands above run both.
- **Coverage target.** Is `min_overlap = 1` coverage the right target for a
  lever meant to "name the whole cluster"? Mean per-cluster recall or matched
  F1 may be the better primary metric for v2.
- **Credit for held or unmoved robots.** A group option's involved set names
  robots that M3 only holds (lane-scoped, shield) or does not move (the
  "not moved" robots of a group reverse). The bench scores the involved set,
  so these robots earn coverage and F1 credit. Accept, or score the executed
  set instead?
- **No-group fallback.** On 4 items with no observed group, the outside
  section is kept despite `--gf-offgroup drop`. This is a deviation from the
  brief, made so those items still have options.
- **Union-of-groups wait.** Not implemented. A single hold over every observed
  group would let one option cover split two-cluster items without pair
  options. Should it be added?

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
  live in the worktree `vgu-vlm-swarm-v6b`.

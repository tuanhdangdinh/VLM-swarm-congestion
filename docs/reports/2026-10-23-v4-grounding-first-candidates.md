# v4 Grounding-First: Candidate-Set Ceiling on 31 Live S1b Episodes

**Prepared:** 2026-10-23

**Revision history:**

- Initial draft: candidate-set ceiling and fixed-option sanity replay, with zero API calls.
- Rev 2 (2026-10-23): added the cluster-conditioned ceiling row; tightened the interpretation.

---

## Scope

This report covers v4 lever 1, "grounding-first", which the owner approved on
2026-10-23. It is a `replay` prompt variant of the offline bench
(`docs/specs/v4_vlm_bench.md`). Its code is in
`benchmarks/vlm_bench/variants/grounding_first.py` (commit f888420), and its
tests are in `tests/unit/test_vlm_bench_grounding_first.py` (commit d242828).

- Zero API calls were made. **The real-model replay is pending an API key**,
  because none is set on this machine.
- The run is **exploratory v4 only**. Nothing here pools with or replaces any
  prereg-v3 confirmatory measure (A32-A36).
- The items are the same 187 as in the baseline: `items_live31.jsonl`, md5
  f1dc2ccb.

---

## Design

Before the model is asked, the variant enumerates the item's executable
options. It uses the real offline M3, `grounder_offline.ground_command`, which
calls `ground_reasoner_result` with the episode's recorded params, overlay,
goal references and task intents. Stage 2 is not run.

| Probe | Kept when |
|---|---|
| `yield(Y, P)`, every ordered pair | M3 grounds a `yield` action for Y itself: not refused, not swapped, not degraded to a reroute (the oracle's rule) |
| `reverse(a, b)`, every unordered pair | the command has a `reverse` action and no `reverse=infeasible` tag |
| `reroute(r)` | every reroute action carries waypoints |
| `temporary_wait(a, b)` | always (listed last) |

The variant then builds the prompt and maps the answer back:

- **Not offered.** `junction_clear` is not offered: every probe on these
  scenes falls back to a yield (`junction_geometry=shipped_unsolved`).
  `convoy` and `priority_override` are not offered either. Each one either
  aliases to a yield that is already listed or degrades to a wait.
- **Deduplication.** Options are deduplicated on what M3 executes
  (`executed_key`). Within each strategy group they are ordered closest pair
  first.
- **Prompt.** The prompt is the live builder's output, verbatim (its hash is
  checked against the stored prompt for every variant), plus a numbered option
  list and a closing "N+1) none of the above". It also tells the model to add an
  `"option"` field to the same JSON object.
- **Answer mapping.** The option number becomes the probe decision itself (the
  probed pair, the strategy and the yielder). Re-grounding that decision gives
  the probe's executed key, and a test checks this.
- **"none".** This answer scores as a negative decision.
- **Bad answers.** An out-of-range or missing option is recorded as a parse
  failure and triggers a re-ask; it never crashes the run.
- **Provenance.** The run config records the variant, the generator version
  (`gf-candidates-v1`), and the candidate count and composed-prompt SHA-256 for
  each item.

---

## Candidate-Set Ceiling (Zero Cost)

The run is `python -m benchmarks.vlm_bench candidates`. Its output is
`data/bench/v4/candidates_gf_v1.{jsonl,md}`; the jsonl md5 is ee3943f0.

"Inside" means that what M3 executes for the **recorded** ER-2 decision equals
one listed option's executed key. Membership is matched on what M3 executes,
not on the strategy label.

| Option set, over the 137 recorded positives | Set size: mean (median, range) | Recorded decision inside | ≥ 1 option |
|---|---|---|---|
| Resolving (yield / reverse / reroute) | 9.3 (9, 0-16) | **33/137** | **136/137** |
| Including temporary_wait | 19.3 (19, 10-26) | 36/137 | 137/137 (trivial) |
| Resolving, both probed robots in one active GT cluster | n/a | n/a | **120/137** |
| Resolving, at least one robot in an active GT cluster | n/a | n/a | 136/137 |

The 136/137 row counts options on any pair of the five robots, including pairs
outside the conflict. The cluster-conditioned 120/137 is the tighter bound on
what the lever can fix.

The recorded answers execute the way they were asked less often than the
baseline feasibility suggests:

- **Lenient vs strict.** The baseline's M3 feasibility counts 68/137 recorded
  positives as feasible. Under the stricter candidate rule only 51/137 execute
  as asked. The 17 extra are 11 reverses that M3 turned into waits, 3
  waypoint-less reroutes, and 3 convoy/priority_override decisions degraded to
  waits.
- **Executed but not listed.** 15 of the 51 execute but are not in the set
  because they involve 3-5 robots (waits 10, reverses 3, multi-passer yields
  2). Options cover pairs only.

| Recorded strategy | n | Inside (resolving) | ≥ 1 resolving option | ≥ 1 executable yield |
|---|---|---|---|---|
| yield | 54 | 22/54 | 54/54 | 47/54 |
| junction_clear | 39 | 0/39 | 38/39 | 35/39 |
| reverse | 25 | 11/25 | 25/25 | 25/25 |
| temporary_wait | 13 | 0/13 | 13/13 | 9/13 |
| reroute / priority_override / convoy | 6 | 0/6 | 6/6 | 6/6 |

---

## Fixed-Option Sanity Ceiling (FakeBackend, Option 1)

The run is `replay --prompt-variant grounding_first --fixed-option 1 --backend
gemini`. It used a zero-network backend, and its responses were cached in a
scratch directory, never under `data/bench/cache`. The output is
`data/bench/v4/run_gf_fixed1.*`, jsonl md5 75fc33cb, at git d242828.

- All 187 base prompts reproduced their stored hash, so no item was skipped.
- Option 1 was a yield on 163 items, a reverse on 21, and a wait on 3. The
  three wait items are the ones with no resolving option.

| Over the 137 recorded positives | Recorded ER-2 | Option 1 always |
|---|---|---|
| M3 feasibility | 0.496 (68/137) | 1.000 (137/137) |
| yield feasibility | 0.444 (24/54) | 1.000 (122/122) |
| yielder vs M3 oracle | 0.458 (11/24) | 1.000 (122/122) |
| cluster coverage | 0.686 (94/137) | 0.526 (72/137) |
| involved F1, matched (n) | 0.911 (136) | 0.733 (124) |
| involved F1, unconditional | 0.904 | 0.663 |
| yielder vs MC first conflict | 0.467 (7/15) | 0.759 (22/29) |

Over all 187 items, option 1 gives feasibility 187/187, coverage 75/185 and
matched F1 0.750 (170 matched).

---

## Interpretation (Conservative)

1. Feasibility 1.0 is true by construction: it shows the list-to-decision path is lossless, not that a model chooses well.
2. On 120/137 positives a resolving option lies inside an active GT conflict; ER-2 already picks a listed option on 33.
3. The set also holds off-conflict pairs, so choice quality binds: option 1 drops coverage (0.53 vs 0.69) and F1 (0.73 vs 0.91).
4. Reverse is permissive (M3 checks only the same-side refusal), so "executable" means M3's definition, not a physical guarantee.
5. Fixed closest-first order invites a first-slot prior; check it before reading the real ER-2 replay, which awaits an API key.

---

## Approximations and Limits

- Stage 2 is not run. A yield option names the default retreat that M3
  dispatches (letter, park point, backup, side-step). It does not list the
  alternative letters or the sweep clearance, which the grounded command does
  not expose.
- Options are pairs only, plus one robot for a reroute. Multi-passer yields,
  `junction_clear` and multi-robot waits are not enumerated.
- Membership is decided on the executed key. A recorded yield that M3 swapped
  to a listed yielder counts as inside.
- The bench's own M3-feasibility metric is unchanged (lenient). The stricter
  rule applies only to building the candidate set and to the "inside" column.
- On a backend error the variant's retry loop backs off like `Reasoner.run`.
  On an unreadable option it re-asks with the parse error. It does not use the
  `Reasoner`'s neutral-image refusal fallback.

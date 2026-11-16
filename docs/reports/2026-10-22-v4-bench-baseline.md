# v4 Offline VLM Bench: Baseline on 31 Live S1b Episodes

**Prepared:** 2026-10-22

**Revision history:**

- Initial draft: inventory, recorded ER-2 baseline, and classical reference, with zero API calls.

---

## Scope

This is the first run of the offline bench (`docs/specs/v4_vlm_bench.md`,
code `benchmarks/vlm_bench/`). It scores the recorded Gemini Robotics-ER-2
answers and a re-run of the classical shadow chooser on the same scenes.

- Zero API calls were made.
- The run is **exploratory v4 only**. The scenes are pilots E6-E26 and S1b
  tranche 1 E27-E31, which are neither unseen nor representative.
- None of these numbers replaces or pools with any prereg-v3 confirmatory
  measure (A32-A36).

---

## Inventory

The 31 episodes come from the following sources:

- `batch5/live21.txt` (E6-E26);
- `batch6` E27-E31, Arm A and Arm B. E27 B is attempt a2; a1 is not an
  episode under A33(0).

The Arm B bundles have no decision artifacts. All bundles are under
`vgu-vlm-swarm-v3/data/logs/vm_runs/`, untracked.

| Batch dir | Episodes | Items | Backend-failed | Frames | Grounding file (md5) |
|---|---|---|---|---|---|
| churn_wave | E6 | 5 | 0 | none | `s1b_dynamic.yaml` (535f5281) |
| live_batch | E7, E8, E10 | 48 | 38 (E10) | none | `s1b_dynamic.yaml` |
| resume | E9, E11 | 16 | 0 | none | `s1b_dynamic.yaml` |
| batch2 | E12-E17 | 36 | 0 | none | `s1b_dynamic.yaml` |
| batch3 | E18-E20 | 22 | 0 | none | `s1b_dynamic_shield.yaml` (ee5fe68f) |
| batch4 | E21-E23 | 14 | 0 | none | `s1b_dynamic_shield.yaml` |
| batch5 | E24-E26 | 18 | 0 | none | `s1b_dynamic_shield_escort.yaml` (40968886) |
| batch6 | E27-E31 A (+5 B, 0 items) | 28 | 0 | none | `s1b_dynamic_shield_escort.yaml` |

- **N = 187 items:** 149 with a valid decision and 137 positive.
- **Frames:** none in any batch. Every `frames/` directory is empty, and M5's
  `m5_frames` dumps stayed on the VM. The bench is therefore text-only on this
  data.
- **Grounding inputs:**
  - Every artifact's recorded `GroundingParams` equals the params of its file
    in this tree.
  - The escort md5 matches A36(1).
- **MC references:** these attach to the 118 items from seed-keyed
  `mc_seeds_*.jsonl` files (E12-E31).

---

## Fidelity Checks

- **Offline M3 reproduces live refusals on 137/137 positives.** The refused or
  not-refused outcome matches live for every positive. The grounder is the
  real `ground_reasoner_result` with the recorded params, plus goal references
  and task intents rebuilt from the task stream. Stage 2 is not run.
- **The classical re-run reproduces the live shadow record on 184/187 items**
  (same detected flag, strategy, yielder and involved set). The history is
  rebuilt from `m5_scene.jsonl` at 0.25 s decimation, and goals come from the
  task stream.

---

## Results (Pooled)

Run files are under `data/bench/v4/`, untracked:

- `run_recorded.jsonl` (md5 bb534d5a);
- `run_classical.jsonl` (md5 4c517821).

Each has a `.config.json`. Items are `items_live31.jsonl` (md5 f1dc2ccb) at git
aa3dd6d.

"Classical (common)" restricts the classical run to the 149 items whose
recorded answer is valid.

| Metric | Recorded ER-2 | Classical (all 187) | Classical (common 149) |
|---|---|---|---|
| positives | 137 | 185 | 147 |
| M3 feasibility (positives) | 0.496 (68/137) | 0.881 (163/185) | 0.857 (126/147) |
| M3 feasibility (yields only) | 0.444 (24/54) | 0.421 (16/38) | 0.432 (16/37) |
| cluster coverage (≥ 1 cluster) | 0.639 (94/147) | 0.535 (99/185) | 0.673 (99/147) |
| mean per-cluster recall | 0.660 | 0.468 | n/r |
| involved F1, matched (n) | 0.911 (136) | 0.746 (181) | 0.766 (143) |
| involved F1, unconditional | 0.843 | 0.730 | 0.746 |
| yielder vs M3 oracle | 0.458 (11/24), oracle empty 30 | 0.688 (11/16), empty 22 | 0.688 (11/16), empty 21 |
| yielder vs live shadow | 0.389 (7/18) | n/a (self) | n/a |
| yielder vs MC first conflict | 0.467 (7/15) | 0.625 (5/8) | 0.625 (5/8) |
| FP rate (no GT conflict in window) | 0.000 (0/2) | 0.000 (0/2) | n/r |
| unmatched positives (A33) | 1 | 4 | n/r |
| mean tokens / latency | 4048 / 8754 ms | n/a | n/a |
| est $ (cost.log, all items) | 1.2512 | 0 | 0 |

Additional recorded-mode results:

- **Refusal histogram, recorded:**
  - no feasible yielder 39;
  - no executable retreat 11;
  - no shared lane 10;
  - ambiguous lane 6;
  - `yield=infeasible` (escort hits park) 3.
- **Refusal histogram, classical (all):**
  - no shared lane 15;
  - ambiguous lane 3;
  - `yield=infeasible` 3;
  - no executable retreat 1.
- **Strategies:**
  - ER-2: yield 54, junction_clear 39, reverse 25, temporary_wait 13,
    reroute 3, priority_override 2, convoy 1;
  - classical: reroute 137, yield 38, temporary_wait 10.
- **Plan quality, recorded (A33(6) `plan_quality`, 137 scored):**
  - (i-a) emission 0.883;
  - (i-b) consistency 0.983;
  - (ii) agreement 0.212;
  - (iii) mean edit distance 1.00;
  - (iv) provenance: vlm_verbatim 29, repaired 49, m3_default 59;
  - (v) null;
  - (vi) replans 86.

---

## Per-Batch Breakdown (Recorded ER-2)

| Metric | churn_wave | live_batch | resume | batch2 | batch3 | batch4 | batch5 | batch6 |
|---|---|---|---|---|---|---|---|---|
| items / valid / positive | 5/5/5 | 48/10/10 | 16/16/13 | 36/36/33 | 22/22/21 | 14/14/13 | 18/18/16 | 28/28/26 |
| M3 feasibility | 3/5 | 4/10 | 6/13 | 20/33 | 10/21 | 5/13 | 8/16 | 12/26 |
| yield feasibility | 1/2 | 1/4 | 1/7 | 6/8 | 5/7 | 3/6 | 3/5 | 4/15 |
| cluster coverage | 1/5 | 7/10 | 3/15 | 27/36 | 20/21 | 9/14 | 10/18 | 17/28 |
| F1 matched | 1.000 | 0.931 | 0.985 | 0.865 | 0.880 | 0.952 | 0.937 | 0.893 |
| yielder vs oracle | 0/1 | 0/1 | 1/1 | 3/6 | 3/5 | 2/3 | 0/3 | 2/4 |

Classical, per batch: M3 feasibility is 5/5, 42/48, 15/15, 24/36, 21/21,
14/14, 18/18 and 24/28, and coverage is 1/5, 6/48, 8/15, 18/36, 20/21,
10/14, 13/18 and 23/28. The full tables are in `data/bench/v4/run_*.md`.

---

## Interpretation (Conservative)

1. These are pilot and tranche-1 scenes used for a tool shake-down. Nothing
   here is an effect estimate.
2. Half of ER-2's positive decisions (69/137) are refused or degraded by M3,
   and the top classes are geometric: no feasible yielder, no executable
   retreat, no shared lane. This agrees with A36(4)(iii).
3. Yield-only feasibility is similar for ER-2 (0.44) and the classical chooser
   (0.43). Classical's higher overall feasibility comes from `reroute`. Its
   reroutes carry no waypoints and are no-ops at M4, which this metric does
   not count as a refusal.
4. The M3 oracle finds no executable yielder for 30 of 54 ER-2 yields. The
   prompt's choice of yielder is therefore often moot; the scene rather than
   the yielder is the binding constraint.
5. ER-2 names the right robots when it matches (F1 0.91). It misses a second
   simultaneous cluster in about a third of multi-cluster items (coverage
   0.64).
6. The FP rate is uninformative: only 2 items have no GT conflict in the A33
   window.

---

## Approximations and Limits

- Stage 2 is not re-run (`retreat_choice = None`). A refusal is decided before
  stage 2, which is why the 137/137 reproduction holds.
- The classical history window is rebuilt from the scene log, not the live
  ring buffer, and reproduces the live shadow on 184/187 items.
- `est $` uses `cost.log` `est_usd / billed_calls × attempts` per item. It is
  approximate, and E10's 38 failed items are counted.
- The geometry oracle probes only the decision's own involved set.
- Replay is implemented and unit-tested with a fake backend but was not run.
  No frames exist, so a replay would use the neutral image.

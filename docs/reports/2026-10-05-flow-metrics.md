# Foundations-Round Flow Metrics: Scorer Fields, Free-Flow Harvest Blocker, Re-Score

**Prepared:** 2026-10-05

**Revision history:**

- Initial draft: Part 1 scorer fields landed, Part 2 free-flow harvest
  stopped before the VM on a design-level finding, Part 3 local re-score of
  the known IB10 and B1 episodes.

**commit:** branch `feat/v2-flow-metrics` (worktree
`/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v2-fm`), branched from
`feat/prereg-v2-composite` at `10f9b62`; code `af14b4d`.

---

## Summary

This round implements the metrics adopted in the prereg-v2 spec block
"Foundations round adopted (2026-10-05)" (main checkout,
`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`). Definitions and
citations come from `reports/Swarm congestion foundations.md` section 2.

| Part | Status |
|---|---|
| 1. Scorer fields | **Landed.** `delay_vs_free_flow`, `conflict_dissolution`, `aperture_throughput` and `outcome_class`, with `outcome_evidence`. They are added to the `b1`, `b3`, `ib10` and `loop` scorers and to a new generic `flow` subcommand. Additive only. 56 new tests. Full local suite zero-delta. |
| 2. Free-flow harvest (VM) | **STOPPED before the VM: design-level finding.** Solo-in-time staggering cannot produce a free-flow traversal in 5 of the 6 v2-scored cells. In each of those 5 cells, some robot's path or goal is another robot's spawn. The VM was not touched, no table was committed and there was zero API spend. Options are listed below. |
| 3. Re-score (local) | **Done.** Expected classes hold: step-7b 4/4 rerun `resolved`, step-6 episode 2 `clogged`, demo ep2 `resolved`. Delays are `null` (`no_table`) everywhere. The scorers never invent a baseline. |

---

## Part 1: Scorer Fields

Code: `scripts/coverage_scene_scores.py` (fields and wiring) and
`scripts/free_flow_table.py` (table schema, loud loader, harvest builder).
Tests: `tests/unit/test_flow_metrics.py` (56 tests plus one skip; the skip
validates the committed table and runs only once that table exists).

Every scorer keeps its existing fields byte-for-byte. A test pins B1's full
key set as the old set plus the five new keys.

### `delay_vs_free_flow`

- **Definition:** for each robot, `(accepted arrival − own departure) −
  free-flow time` for the same cell and robot.
- **Episode aggregates:** `sum_sec` and `max_sec`. Both are null unless every
  robot scored.
- **Citation:** Greenshields 1935 / LWR. Free-flow speed is the zero-density
  intercept of the fundamental diagram, so delay against a single-robot
  baseline is exactly the flow-theoretic quantity.
- **Origin rule `own_departure`:** a robot's own first GT sample above
  0.03 m/s. The common t0 is not used. Otherwise a scripted hold would count
  as delay: T2b r3 55 s, B1 r3 80 s, B3 r3/r4 120 s. A test pins this
  (`test_a_held_back_robot_carries_no_fake_delay`).
- **Arrival rule:** the T2b GT rule (within 0.35 m, never beyond 0.5 m
  after), on sim time. M5's `ArrivalGate` log lines carry wall-clock ROS
  stamps (for example `[1791010558.64]` in the demo ep2 `m5.log`). At RTF
  ~0.27 that would be a ~3.7× error, so those lines can corroborate an
  arrival but never time it.
- **Never fabricated:**
  - `no_table`: no table was given.
  - `no_baseline`: the table lacks this cell or robot.
  - `never_departed`: the robot never moved.
  - `censored`: the robot never arrived. Its `delay_lower_bound_sec` is
    charged to the episode end. `sum_lower_bound_sec` is filled only when
    every robot has a baseline.
- **Table loading:** the CLI loads `--free-flow F` loudly (a missing or
  invalid file raises `FreeFlowTableError`). Without `--free-flow` it falls
  back to the committed `config/free_flow/free_flow_v1.json` when that file
  exists. Library callers pass the table explicitly.

### `conflict_dissolution`

- **Onset:** taken from the existing oracle conventions.
  - IB10: `formed_jam` onset (`intersection_conflict_active`).
  - Any `aisle_barrier` cell: `conflict_timeline` onset
    (`bottleneck_conflict_active`).
  - Other cells: None.
- **Dissolution:** the onset of the first spell of at least 1.0 s (the B3
  slip window) in which two conditions both hold:
  - every involved robot is at least 0.45 m from every other involved robot;
  - each involved robot is arrived or progressing (≥ 0.03 m/s with its
    distance to goal shrinking).
- **Robot states:** a receding or holding robot is not progressing. A robot
  that has not yet departed under a scripted hold-back is neutral.
- **Spell logic:** the slip spell rule is now the shared
  `sustained_spell_onset`. `slip_onset_sec` delegates to it, and its
  behaviour is unchanged (existing tests pass).
- **Citation:** Aguilar et al., Science 361 (2018), cluster-dissolution time.
  Jam duration in arXiv:2403.08683 is the related measure.
- **Separation constant:** `DISSOLUTION_SEPARATION_M = 0.45` is M4's latch
  distance. A test pins it to `swarm_execution/config/safety.yaml`.
- **Reported alongside:**
  - `time_to_full_resolution_sec`: onset to the last involved robot's
    arrival. It is kept separate from dissolution.
  - `reclogged_at_sec` and `dissolution_final`: a cluster that re-forms after
    dissolving is reported rather than erased.
- **Re-clog rule:** two involved robots, neither yet arrived, are back inside
  0.45 m for at least `RECLOG_MIN_SEC = 12.0`. That is M5's
  `stall_threshold_sec`, also pinned by a test.
- **Ruling: re-clog needs a pair, not a lone stall.**
  - The first draft counted any post-dissolution failure. That flagged a
    false re-clog in every resolved IB10 episode.
  - In step-7b rerun 2, the yielder stops alone for 14 s (sim 194-208) after
    its release. No robot is within 2 m, and M5 logs
    `trigger suppressed robots=['robot_1']`.
  - That is a lone navigation stall, not a cluster, so a re-clog now requires
    two robots.

### `aperture_throughput`

- **Definition:** robots/s through the registered aperture over the active
  window, from the first lane entry to the last lane exit. Each robot is
  counted in its own travel direction (`gate_passage`, mirrored for
  westbound robots).
- **Citation:** dos Passos, Duquesne & Marcolino, arXiv:2201.09335.
  Throughput stays finite while per-robot arrival time diverges.
- **Scope:** B1 uses its `aisle_barrier` gate. Other cells can opt in with an
  `oracle.aperture` mapping. The oracle models are `extra="forbid"`, so no
  shipped scenario declares one yet, and adding one is a schema change.
- **Additional fields:**
  - `n_expected`: robots whose spawn and goal lie on opposite sides of the
    aperture.
  - `complete`: whether every expected robot passed.
  - `horizon_throughput_rps`: exits divided by the time from first entry to
    episode end. This is the rate that goes to zero for a clogged aperture.
- **Check:** for B1, `throughput_rps` equals the existing
  `gate.flow_per_100s / 100`. This was verified on synthetic and real runs.

### `outcome_class`

`OutcomeClass` has three values (`resolved`, `intermittent`, `clogged`) and
one mapping, `classify_outcome`, shared by every scorer:

| Condition (checked in order) | Class |
|---|---|
| Run invalid: IB10 formed-jam gate failed, or `--invalid-reason` given | `null` |
| `fallback_exhausted` | `clogged` |
| Any robot censored at the horizon | `clogged` |
| All arrived, and ≥ 2 dispatched decisions or a `fallback` phase | `intermittent` |
| All arrived, dispatch count unknown | `null` (never guessed) |
| All arrived, ≤ 1 dispatched decision, no fallback | `resolved` |

- **Citations:**
  - `intermittent`: Zuriguel et al., Sci Rep 2014. The flow stops and
    restarts, with heavy-tailed but finite resolution times.
  - `clogged`: the same paper's divergence criterion, where the mean time
    between passages diverges (tail exponent ≤ 2; also arXiv:2004.04413).
- **Re-trigger:** a second *dispatched* decision, meaning
  `congestion_detected` together with `grounded_command_present`.
  No-congestion re-analyses do not count. The 4/4 rerun has four
  post-dispatch no-congestion analyses and must still class `resolved`.

---

## Part 2: Free-Flow Harvest, Stopped Before the VM

### The finding

Solo-in-time staggering means one run per scene, with robots released one at
a time while the others stay parked. Before its turn a parked robot sits at
its spawn. After its turn it sits at its goal.

M4's 0.45 m min-distance latch covers *every* pair, idle bystanders included
(`swarm_execution/safety.py`, `detect_proximity_violations`: only the pairs
in a command's exemption are skipped). A traversal that passes within 0.45 m
of a parked robot therefore latches, or it has to detour. Either way the time
is not free flow.

A session-local check (not committed) tried every release order for each
scene. It
measured the nominal path (spawn to goal, and B1 robot_2 via its N arm)
against each parked robot:

| Scene | Duration (s) | Best release order | Min clearance (m) | Binding pair | Verdict |
|---|---|---|---|---|---|
| `head_on_asymmetric_w0p2_eopen_bshort_o0` | 300 | r1 > r2 | 0.00 | r1 vs parked r2 at spawn | BLOCKED |
| `t2b_flow_ordering` | 300 | r1 > r2 > r3 | 0.00 | r1 vs parked r2 at spawn | BLOCKED |
| `bottleneck_merge` (B1) | 200 | r1 > r3 > r2 | 0.60 | r3 vs parked r1 at goal | CLEAN |
| `priority_visual_r1` / `_r2` | 200 | r1 > r2 | 0.00 | r1 vs parked r2 at spawn | BLOCKED |
| `convoy_counterflow_slip` | 260 | r1 > r3 > r4 > r2 | 0.00 | r4 vs parked r2 at spawn | BLOCKED |
| `intersection_bottleneck` (IB10) | 300 | any | 0.00 | every goal is the opposite robot's spawn | BLOCKED (any order) |
| `obstacle_in_candidate` | 300 | r1 > r2 | 0.00 | r1 vs parked r2 at spawn | BLOCKED |
| `priority_urgent_r1` | 200 | r1 > r2 | 0.00 | r1 vs parked r2 at spawn | BLOCKED |
| `dynamic_anomaly_v2` | 200 | r1 > r2 | 0.70 | r1 vs parked r2 at spawn | CLEAN geometrically, but the timed pallet is the cell's anomaly and stays on robot_1's lane |
| `blocked_path_object` / `_transient` | 180 | r2 > r1 | 1.75 | r1 vs parked r2 at goal | CLEAN geometrically, but the blocker on robot_1's lane is the cell's point |

These are swap scenes. Each robot's goal lies at or past another robot's
spawn on the same centreline:

- **IB10:** strictly circular. r1's goal is r2's spawn and r3's goal is r4's
  spawn, so no release order works at all.
- **Head-on family and B2 / B2-visual:** robot_2's goal is robot_1's spawn,
  so robot_1 must go first. It would then meet a parked robot_2 0.5 m past
  the gate mouth.
- **T2b and B3:** fail by the same pattern (table above).

Only B1 admits a clean solo-in-time run. Its robot_2 must go last, because
its goal at (1.9, 0) is 0.2 m past the gate exit, and the 0.60 m clearance it
then leaves is above the latch.

The two anomaly cells would time a traversal that includes their own
blocker. Their free-flow baseline needs the blocker removed, so they need a
variant run either way.

`priority_visual_r1` and `_r2` share spawns and goals. The load prop is
visual-only, with no `CollisionAPI`, `RigidBodyAPI` or `MassAPI`
(`isaac/vgu_sim/load_prop_asset.py`), so one baseline covers both members.
`priority_urgent_r1` has the same geometry too.

### Why a B1-only run was not taken

A B1-only harvest cannot meet Part 3's IB10 sanity check. If the ruling picks
solo-in-space for the other cells, B1 should probably be harvested the same
way so the table uses a single mechanism (or record `mechanism` per entry,
which the schema already supports). Spending a VM session before the ruling
risks rework.

### Options for the ruling

1. **Solo in space (recommended; the spec's literal wording).** The spec
   says "one single-robot free-flow run per cell". This means one run per
   robot, with the other robots absent.
   - **Per-robot variants:** each needs a scenario variant
     (`<scene>__solo_<robot>.yaml`) and a USD rebuild (the stale-USD trap).
   - **Maps:** fc_launch derives `MAP` from `SCENARIO`, so each variant needs
     a map copy. The map depends only on the barrier and static obstacles, so
     a byte copy is enough.
   - **M5 config:** an `initial_tasks` overlay with the solo robot only.
   - **Anomaly cells:** they additionally drop their blocker.
   - **Run count:** about 16 runs, with B1 done as one solo-in-time run or
     three solo runs:

     | Cell | Runs |
     |---|---|
     | Head-on | 2 |
     | T2b | 3 |
     | B1 | 1 (solo-in-time) or 3 |
     | B2-visual (r1 covers r2) | 2 |
     | B3 | 4 |
     | IB10 | 4 |

   - **Wall time:** about 3.5-4.5 h of VM wall time at about 15 min a run.
   - **Ready now:** the builder (`free_flow_table.py derive --mechanism
     solo_in_space`) and the schema already handle this.
2. **Solo in time with off-floor parking.** Rewrite the waiting robots'
   spawns to remote poses. Within each run, every robot traverses from its
   real spawn in turn. This still needs one scenario variant per release
   slot, because a robot's spawn is its traversal origin. It saves no
   variants over option 1 and adds more moving parts.
3. **Free flow by symmetry/measurement on existing runs.** For example, take
   the first passer's unobstructed transit in conflict episodes. This is
   rejected: it is not free flow, since the robot was dispatched into the
   conflict.

The harvest tooling is already built and tested: schema, loud loader,
`derive`, `build`, `check`, the zero-dispatch check and the solo-traversal
check. Only the run mechanism needs the ruling.

---

## Part 3: Re-Score of the Known Episodes

Re-scored with a session-local driver that calls the committed scorers. The
equivalent per-episode CLI is `coverage_scene_scores.py ib10 --gt G
--decisions D --m5-log L [--invalid-reason R]` and `... b1 --gt G
--decisions D --m5-log L`.
There is no table, so every robot's delay reason is `no_table`.

Bundles used:

- `data/logs/vm_runs/ib10_smoke/*` and `data/logs/vm_runs/v2_demo/*` from
  the main checkout;
- the step-7b reruns from the predecessor session's scratchpad copies
  (`.../scratchpad/step7b/ib10_7b_{,vi_}2026100*`).

### IB10 outcome classes and dissolution

Times are in sim-s. Onset and dissolution are absolute; the dissolution
duration and full resolution are measured from onset.

| Episode | Arrived | Dispatches | Fallback | Exhausted | **Class** | Onset | Dissolved at | Dissolution (s) | Final | Re-clog at | Full resolution (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| step-6 run A (mock) | 1/4 | 1 | no | no | `clogged` | 27.3 | — | censored | — | — | censored |
| step-6 run B (mock) | 1/4 | 1 | no | no | `clogged` | 28.2 | — | censored | — | — | censored |
| step-6 live ep1 (ER-2) | 1/4 | 2 | no | no | `null` (harness-invalid: stack dead at sim ~134.6) | 27.1 | — | censored | — | — | censored |
| **step-6 live ep2 (ER-2)** | 1/4 | 4 | yes | no | **`clogged`** | 28.8 | — | censored | — | — | censored |
| step-7b rerun 1 (mock) | 2/4 | 1 | no | no | `clogged` | 26.6 | 139.7 | 113.1 | **no** | 143.0 | censored |
| **step-7b rerun 2 (mock)** | 4/4 | 1 | no | no | **`resolved`** | 27.1 | 185.5 | 158.4 | yes | — | 192.8 |
| v2 demo ep1 (scripted) | 4/4 | 1 | no | no | `resolved` | 31.6 | 189.8 | 158.2 | yes | — | 192.6 |
| **v2 demo ep2 (live ER-2)** | 4/4 | 1 | no | no | **`resolved`** | 29.3 | 184.6 | 155.3 | yes | — | 190.3 |

Full resolution is `time_to_full_resolution_sec` (onset to the last
involved robot's accepted arrival).

**Sanity: all three expected classes hold.** The 4/4 rerun classes
`resolved`, step-6 episode 2 `clogged`, and demo ep2 `resolved`.

- **Step-6 episode 2 is clogged through censoring.** Its m5.log carries a
  `phase_reached=fallback` advance but no `outcome=fallback_exhausted` string.
  That string postdates step 6.
- **Live episode 1 is classed `null`, not `clogged`.** Its GT after sim
  ~134.6 is a dead-stack artifact (step-6 report, rev 3), so it is passed
  with an `invalid_reason`.
- **Step-7b rerun 1 shows why `dissolution_final` exists.** The release
  opened the cluster at 139.7 s. The second receder and the yielder then
  latched for good at 143.0 s (0.416 m), which matches the step-7b report's
  "latch for good 3 s later".

On the resolved IB10 episodes, dissolution comes 32-35 s before full
resolution (rerun 2: 185.5 vs 219.9 sim-s absolute). Dissolution is late in
absolute terms because of the step-7b ruling (vi) chain: the yielder
re-enters last, and dissolution needs every involved robot progressing. The
yielder holds in its pocket until the chain releases it at 185.8 (gate log).
The remaining ~34 s is the yielder's own drive home, which includes its lone
14 s stall. This is the registered definition working as specified, not a
defect.

### IB10 travel times (spawn to accepted arrival, own departure)

These are the inputs `delay_vs_free_flow` will subtract the baseline from
once the table exists. Each cell is departure (sim-s) / travel (s); "—" means
the robot never arrived (censored).

| Episode | robot_1 | robot_2 | robot_3 | robot_4 |
|---|---|---|---|---|
| step-6 run A | 17.3 / — | 17.1 / 79.5 | 17.2 / — | 17.4 / — |
| step-6 run B | 18.2 / — | 18.3 / 102.3 | 18.3 / — | 18.3 / — |
| step-6 live ep2 | 17.8 / — | 17.8 / 71.1 | 19.7 / — | 17.7 / — |
| step-7b rerun 1 | 16.7 / — | 16.7 / 75.7 | 16.7 / — | 16.8 / 122.7 |
| step-7b rerun 2 | 16.9 / 203.0 | 17.0 / 77.0 | 17.0 / 170.7 | 17.2 / 136.0 |
| v2 demo ep1 | 21.3 / 202.9 | 21.1 / 77.8 | 21.7 / 138.1 | 21.4 / 170.6 |
| v2 demo ep2 | 19.3 / 200.3 | 19.2 / 73.4 | 19.7 / 132.6 | 19.3 / 167.6 |

**Plausibility, indicative only (not a baseline).** Every IB10 path is 3.5 m.

- At B1's near-unobstructed lead transit (robot_1, 3.5 m in ~21 s after t0,
  `B1FIX_S42`), solo IB10 times should be roughly 20-25 s.
- On that estimate, the IB10 delays will all be positive and large:
  - about 50 s for the passer robot_2;
  - about 110-180 s for the receders and the yielder.
- That ordering matches the composite: the yielder re-enters last.

The free-flow harvest replaces this estimate. No number from it enters any
table.

### B1 aperture throughput and classes (extra validation of the aperture field on real runs)

Window and dissolution are in seconds.

| Run | Arrivals after t0 (r1, r2, r3) | Exits / expected | Window | Throughput (rps) | Horizon rate (rps) | `flow_per_100s` | Dispatches | Class | Onset | Dissolution |
|---|---|---|---|---|---|---|---|---|---|---|
| B1FIX_S42 | 21.2, 20.3, — | 2/3 | 10.0 | 0.200 | 0.0114 | 20.0 | 1 | `clogged` | — | — |
| B1FIX_S43R | 59.8, 122.5, — | 3/3 | 78.1 | 0.0384 | 0.0213 | 3.841 | 1 | `clogged` | 23.6 | 94.5 |
| B1FIX_S43 | 109.1, 124.8, — | 2/3 | 26.2 | 0.0763 | 0.0233 | 7.634 | 1 | `clogged` | 24.4 | 93.4 |
| B1S1 (bscene smoke) | —, —, — | 0/3 | — | — | — | — | 1 | `clogged` | 28.3 | censored |

`throughput_rps` equals `flow_per_100s / 100` in every run.

- **`B1FIX_S42` is a clear case of throughput hiding a clog.** Its window
  rate is the highest of the four (0.200 rps), yet only 2 of 3 robots exited:
  robot_3 is stuck at the gate at 1.02 m.
- **The horizon rate shows it.** That rate falls for clogged apertures, which
  is why both rates are reported.
- **`B1FIX_S43R` is a near miss.** All three robots exited, but robot_3
  parked 0.363 m from its goal, just outside the 0.35 m rule. It is therefore
  censored, and the episode classes `clogged`. This is an arrival-rule
  boundary case worth knowing about before the B1 collection.

---

## Verification

Full local suite on a clean detached baseline (`/tmp/fm_baseline_10f9b62`, at
`10f9b62`), run as
`pytest -q -p no:cacheprovider --continue-on-collection-errors`:

| Tree | Failed | Passed | Skipped | Errors |
|---|---|---|---|---|
| Baseline | 63 | 4903 | 153 | 3 |
| Branch | 63 | 4959 | 154 | 3 |

- **Zero-delta:** the failing-test-name sets are byte-identical.
- **Pre-existing failures and errors:** 3 `pxr` collection errors and the
  `t2b_forced_order` margin-placeholder failures, among others.
- **Branch changes:** +56 passing tests, plus 1 skip (the
  committed-table check).
- **Lint:** `ruff check` is clean on every touched file.

---

## VM State

The VM was not touched: no deploy, no run, no config edit. Its state is
whatever the battery-v2 session left: pristine and restored
(`orchestrator.yaml` `1f656533…`, `rag.yaml` `e18c723c…`). API spend was
zero.

---

## Open Items

- **Ruling needed on the harvest mechanism** (Part 2 options). After the
  ruling, the work is: harvest, then `free_flow_table.py build` to
  `config/free_flow/free_flow_v1.json`, then re-run this re-score with the
  table. The skip in `test_flow_metrics.py` becomes a live schema check at
  that point.
- **Remainder cells:** `dynamic_anomaly_v2` and `blocked_path_*` need
  blocker-free variants for a meaningful free-flow baseline (see the
  Part 2 feasibility table).
- **`oracle.aperture`** is supported by the scorer but not admitted by the
  `extra="forbid"` oracle models. Declaring an aperture on any cell other
  than B1 is a schema change.

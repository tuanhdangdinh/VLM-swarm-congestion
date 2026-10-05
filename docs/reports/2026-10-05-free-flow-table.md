# Free-Flow Baseline Harvest: `free_flow_v1` (Solo-in-Space)

**Prepared:** 2026-10-05

**Revision history:**

- Initial draft: generator and variants built, 22 solo runs harvested on the VM, `free_flow_v1` frozen, Part-3 delay re-score filled in.

**commit:** branch `feat/v2-freeflow-harvest` (worktree
`/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v2-ff`), branched from
`feat/prereg-v2-composite` at `b264e9d`. Code and variants are in `b3a4c99`, and the
table is in `fc8c704`.

---

## Summary

This harvest implements the free-flow baseline ruled in the prereg-v2 spec
(main checkout, `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`,
"Foundations round adopted (2026-10-05)", METHOD RULED). Under that ruling,
each robot traverses its cell's course ALONE, on a generated per-robot
scenario variant with its own USD build. Blocker cells run without their
blockers. A single method covers the whole table.
`docs/reports/2026-10-05-flow-metrics.md` Part 2 explains why solo-in-time was
ruled out.

| Item | Result |
|---|---|
| Generator | `scripts/make_free_flow_variants.py` emits 22 variants plus `manifest.json` into `isaac/config/scenarios/free_flow/`. 144 unit tests (`tests/unit/test_free_flow_variants.py`). |
| Runs | **22 of 22 valid.** The 8 cells are the 6 v2-scored cells plus `obstacle_in_candidate` and `dynamic_anomaly_v2`. Every run passed every check: zero decision artifacts (so zero dispatches), one M5 accepted arrival, GT `completed: true`, `RESTORE OK`, and zero jump-back warnings. |
| Table | `config/free_flow/free_flow_v1.json`: 11 scenes and 28 entries. 22 entries are measured. 6 entries carry the `priority_visual_r1` measurements under the three registered identical cells. The schema test now runs (no longer skipped), and the loader check is green. |
| Re-score | Every delay is positive. On IB10 the passer's delay (50–81 s) is below every held robot's delay or censored lower bound in every episode. In the three resolved episodes it is 52–57 s against measured delays of 112–182 s. |
| Suite | Zero-delta against a clean detached baseline (`b264e9d`): the same 66 failing/erroring test ids, and +149 passing. |
| VM | Restored: 764 pre-deploy paths are md5-identical, the variant USDs are removed, and the configs are pristine. GPU idle. Zero API spend. |

No cell was deferred.

---

## Method

### Variants (generated, not hand-written)

`scripts/make_free_flow_variants.py` writes
`<cell>_ff_<robot_id>.yaml` for each registered cell
(`FREE_FLOW_CELLS`) and each of its robots. Each variant contains:

- **The robot.** Only that robot's entry, copied from the parent unchanged
  (spawn, goal, marker, `loaded`, `initial_task`).
- **The course.** The parent's `aisle_barrier`, `loop_map` and static/timed
  obstacles are kept. The exception is `BLOCKER_CELLS` (`obstacle_in_candidate`,
  `dynamic_anomaly_v2`, `blocked_path_object`, `blocked_path_transient`), whose
  blockers are stripped. The variants dropped `candidate_box` and `pallet_1`.
  The head-on cell's `blocker_west` is course geometry, not a blocker-cell
  blocker. It is kept and asserted by a test.
- **Conflict fields.** `family: normal_flow`, `expected_conflict: null`, and
  no `oracle` or `parameters`. `ScenarioConfig` would reject a parent's
  conflict or oracle that names robots the variant no longer has. The same
  pattern is already used by the single-robot `m1_y_extent_probe_*` scenes.
- **Duration.** `duration_sec: 120.0`, with `runtime.duration_sec` cleared.
  The Isaac runner reads `runtime.duration_sec or duration_sec`.
  `run_simulation --duration-sec` is a dead flag: it is parsed but never
  wired into `ResolvedRunConfig`. Verified in code. The comment in
  `t2b_flow_ordering.yaml` that says "fc_launch's --duration-sec overrides
  this" is wrong.
- **Provenance.** A header records the parent path and the parent's sha256.

`manifest.json` records, per variant:

- the parent and its sha256;
- the robot;
- `map_scenario`;
- the stripped obstacle ids;
- the single M5 `initial_tasks` line, with no `start_delay_sec`. The
  `own_departure` origin makes a hold irrelevant.

The VM driver needs no yaml parsing. `--check` fails if any committed file
differs from the generator output, and a test pins this.

The tests pin:

- one variant per robot of every cell (22);
- the robot copied verbatim;
- the `_ff_robot_N` name scheme;
- every variant validating as conflict-free;
- the parent course kept;
- blocker stripping, including a `blocked_path_object` dry generation;
- refusal of a timed obstacle on a non-blocker cell;
- the map equality below;
- the M5 line patching the VM-pristine `orchestrator.yaml` (taken from the
  `fix/deadlock-collision-resolution` blob, md5 `1f656533`);
- the B2-visual identity checks;
- a committed-table traceability test: every entry's `run_id` names the solo
  variant of its scene, or of the scene that covers it.

### Maps are reused, not regenerated

Nav2 maps rasterize only racks, barriers, loop carves and static obstacles.
Timed obstacles are never baked (`generate_warehouse_map.build_occupancy_grid`),
and no blocker cell has a static obstacle. So for all 22 variants, the
occupancy grid equals the parent's grid and the committed parent `.pgm`
pixel for pixel (`test_variant_map_is_byte_identical_to_the_parent_map`).

`fc_launch.sh` gained two things:

- `MAP_SCENARIO`, defaulting to `SCENARIO`. The two-robot DRY_RUN goldens are
  byte-unchanged.
- A third scenario lookup, `isaac/config/scenarios/free_flow/`.

The variants run on their parent's installed map. No map file was added to
colcon's install tree. On the VM, the 16 installed parent map files were
md5-verified equal to the branch before any run.

### VM driver

`scripts/vm/free_flow_run.sh` runs one variant, following
`v2_final_run.sh`'s conventions. `scripts/vm/free_flow_batch.sh` runs the
variants in order and stops at the first run without `RESTORE OK`. The
driver:

- refuses unless the variant USD exists and is newer than its yaml;
- runs the pristine-md5 gate;
- waits until `pgrep -f '[r]un_simulation'` is EMPTY. The literal lives only
  in the script file, never on an SSH line;
- patches the M5 line with `patch_initial_tasks.py --set`. fc_launch's own
  `swarm_orchestrator` build installs it, and the installed block is captured
  per run in `installed_initial_tasks.txt`;
- runs with `BACKEND_ID=mock` and no decision file, so the mock answers no
  congestion and no API is called;
- restores verbatim with a fresh mtime, rebuilds, and checks the src and
  installed md5s (`RESTORE.txt`).

The driver also shortens each run. Isaac stops at the variant's 120 sim-s on
its own. Once the Isaac process has exited, the driver ends fc_launch's
`REC_SEC` M5 tail, so cleanup starts at once. `REC_SEC=900` remains a safety
cap. Isaac exited on its own in all 22 runs (`ISAAC_EXIT.txt`), so no Isaac
outlived its run.

Each run took about 5.3 min of wall time. The 22 runs plus one calibration
gap took 1 h 57 min (09:11–11:09 UTC).

Each run directory also holds an `EVIDENCE.txt`:

- M5 log line count;
- accepted and rejected arrivals;
- decision-file count;
- GT `completed`;
- jump-back warnings.

### Deploy

The VM tree was in its pre-deploy state, matching the step-7b / loop-family
era. That is the tree the IB10 step-7b episodes ran on.

- **Nothing that runs a solo traversal changed.** Nav2 config/launch, M4,
  `isaac/vgu_sim` and the maps all show no change since step-7b (`7070813`).
  The only branch delta in that area is the flag-off M1 `annotation.yaml`.
- **Only this harvest's files were deployed.** That is 27 files, extracted
  from a `git archive` of `b3a4c99` with `tar -m`, reset to `root:root`, and
  touched:
  - the 22 variants and the manifest;
  - `fc_launch.sh`;
  - `build_scenario.py`;
  - the two drivers.
- **Deployed md5s were verified.** The VM's `fc_launch.sh` and
  `build_scenario.py` were first confirmed byte-equal to the branch's
  pre-change versions, so the deploy changed only this harvest's edits.
- **No colcon package was touched**, so the build-cache trap could not fire.
- **Backup:** `/home/ubuntu/ff_predeploy_backup/` holds the originals tarball,
  a 764-path pre-deploy md5 snapshot, and the USD and scenario listings.
- **USDs:** built in one SimulationApp session. `build_scenario --config`
  now takes several configs. All 22 were written in 19 s, and each was
  verified to exist and be newer than its yaml.

---

## Results: `free_flow_v1`

All entries use the `solo_in_space` mechanism, origin `own_departure`, and
arrival rule `gt_within_0.35_stay_0.5`. Times are in sim-seconds.

Column notes:

- **Departure** and **Arrival** are the GT sim times.
- **Path:** the straight spawn-to-goal distance.
- **Speed:** the effective free-flow speed, `(path − 0.35) / time`.
- **M5 arrival:** the `distance_m` on M5's accepted-arrival line.
- **Run (stamp):** the fc_launch stamp. Each run's bundle is
  `data/logs/vm_runs/free_flow/<cell>_ff_<robot>/` in the main checkout
  (gitignored; 14 MB).

| Cell | Robot | **Time** | Departure | Arrival | Path (m) | Speed (m/s) | M5 arrival | Run (stamp) | GT sha256 |
|---|---|---|---|---|---|---|---|---|---|
| `head_on_asymmetric_w0p2_eopen_bshort_o0` | robot_1 | **25.0** | 10.5 | 35.5 | 4.10 | 0.150 | 0.10 | `20261005_091147` | `c5a083696716…` |
| | robot_2 | **17.5** | 11.5 | 29.0 | 3.00 | 0.151 | 0.09 | `20261005_091759` | `875c7fb294fa…` |
| `t2b_flow_ordering` | robot_1 | **24.2** | 10.7 | 34.9 | 4.00 | 0.151 | 0.09 | `20261005_092318` | `7f6d25ad3e10…` |
| | robot_2 | **20.8** | 11.1 | 31.9 | 3.50 | 0.151 | 0.08 | `20261005_092834` | `5993f98904c1…` |
| | robot_3 | **26.2** | 12.3 | 38.5 | 4.30 | 0.151 | 0.10 | `20261005_093353` | `6ba66f526b27…` |
| `bottleneck_merge` (B1) | robot_1 | **20.7** | 11.7 | 32.4 | 3.46 | 0.150 | 0.08 | `20261005_093912` | `5d0d8e416e51…` |
| | robot_2 | **18.1** | 11.8 | 29.9 | 2.58 | 0.123 (N arm, not straight) | 0.07 | `20261005_094431` | `802366e16102…` |
| | robot_3 | **30.5** | 11.3 | 41.8 | 4.91 | 0.149 | 0.08 | `20261005_094945` | `5124ec214b7d…` |
| `priority_visual_r1` (B2-visual) | robot_1 (loaded) | **24.4** | 12.7 | 37.1 | 4.00 | 0.150 | 0.08 | `20261005_095459` | `d0cd0bbc1586…` |
| | robot_2 | **24.2** | 10.7 | 34.9 | 4.00 | 0.151 | 0.07 | `20261005_100016` | `bf783ab82f2c…` |
| `convoy_counterflow_slip` (B3) | robot_1 | **22.4** | 13.9 | 36.3 | 3.67 | 0.148 | 0.14 | `20261005_100535` | `be961a71103a…` |
| | robot_2 | **18.8** | 12.3 | 31.1 | 3.20 | 0.152 | 0.07 | `20261005_101054` | `937cb7a56ecb…` |
| | robot_3 | **27.6** | 11.9 | 39.5 | 4.36 | 0.145 | 0.22 | `20261005_101608` | `072b8c205952…` |
| | robot_4 | **26.2** | 12.7 | 38.9 | 4.32 | 0.152 | 0.09 | `20261005_102122` | `dba18df92f7f…` |
| `intersection_bottleneck` (IB10) | robot_1 | **20.9** | 12.0 | 32.9 | 3.50 | 0.151 | 0.09 | `20261005_102635` | `57818d99375a…` |
| | robot_2 | **20.9** | 12.2 | 33.1 | 3.50 | 0.151 | 0.08 | `20261005_103150` | `fe988a2572d6…` |
| | robot_3 | **20.7** | 12.6 | 33.3 | 3.50 | 0.152 | 0.08 | `20261005_103704` | `fd9501c5458c…` |
| | robot_4 | **20.9** | 12.3 | 33.2 | 3.50 | 0.151 | 0.05 | `20261005_104221` | `6bad30702093…` |
| `obstacle_in_candidate` (blocker stripped) | robot_1 | **14.3** | 11.6 | 25.9 | 2.50 | 0.150 | 0.06 | `20261005_104738` | `91d954645222…` |
| | robot_2 | **30.9** | 11.8 | 42.7 | 5.00 | 0.150 | 0.08 | `20261005_105257` | `dba7a0664d94…` |
| `dynamic_anomaly_v2` (pallet stripped) | robot_1 | **31.0** | 10.4 | 41.4 | 5.00 | 0.150 | 0.06 | `20261005_105821` | `ff3dab6b75ff…` |
| | robot_2 | **30.9** | 10.6 | 41.5 | 5.00 | 0.150 | 0.07 | `20261005_110342` | `e63e94d0a387…` |

The table also carries `priority_visual_r2`, `priority_urgent_r1` and
`priority_urgent_r2`. Each holds robot_1 24.4 and robot_2 24.2, with the same
`run_id` and `gt_hash` as `priority_visual_r1` (see the identity section
below).

### Sanity of the harvest itself

- **One speed everywhere.** The effective free-flow speed is
  0.145–0.152 m/s in 21 of 22 runs. Free flow is the DWB cruise speed, not
  the 0.22 m/s cap. The exception is B1 robot_2, whose real route turns
  through the junction from the N arm, so its straight-line "speed"
  understates it.
- **Repeat courses agree.**
  - The 4.0 m courses of T2b r1, B2-visual r1 and B2-visual r2 time at
    24.2, 24.4 and 24.2 s.
  - IB10's four symmetric arms time at 20.7–20.9 s.
  - The two 5.0 m lanes of `dynamic_anomaly_v2` time at 31.0 and 30.9 s.
  - Agreement across courses is therefore about 0.2 s. This is cross-course
    agreement, not replication: each entry is a single run (n = 1).
- **Departure is M5's dispatch, not a spawn-settle blip.** Departures fall at
  10.4–13.9 sim-s, which is the M5 start ("all components started", about
  25 wall-s after Isaac's topics went live). The first GT sample has speed 0 by
  construction, and no run shows an earlier mover.
- **Zero dispatches.** No run wrote a decision artifact: M5 never triggered an
  analysis, let alone dispatched. `derive --decisions` confirms 0 for every
  run.
- **The solo guard held.** Every GT holds exactly one robot. A new
  `derive_entries` check raises otherwise (`b3a4c99`, tested).

---

## Identity Verification: `priority_visual_r1` Covers Three Cells

This is identity, not mirror symmetry. All of the following were checked
against the yamls and are pinned by
`test_priority_visual_r1_covers_its_registered_cells`.

- **Robots.** `priority_visual_r1`, `priority_visual_r2`, `priority_urgent_r1`
  and `priority_urgent_r2` have identical robot ids, spawns and goals:
  - robot_1 from (−1.5, 0) to (2.5, 0);
  - robot_2 from (1.5, 0, yaw π) to (−2.5, 0).
- **Course.** All four have identical `aisle_barrier` (0.55 × 2.0 m at
  x = 0), no static or timed obstacles, and no loop map.
- **Maps.** All four `warehouse_map_*.pgm` files are byte-identical (md5
  `96113d92…`). Their yamls differ only in the `image:` line.
- **What differs.**
  - The visual pair: only which robot carries `loaded: true`. The load prop
    is visual-only. `isaac/vgu_sim/load_prop_asset.py` authors it without
    `CollisionAPI`, `RigidBodyAPI` or `MassAPI`, and asserts their absence at
    build time. It sits above the lidar plane. Nav2, the lidar and the physics
    cannot see it.
  - The urgent pair: only `initial_task` (urgent vs routine). That is an
    M5/VLM label with no effect on a solo Nav2 traversal.
- **The prop does not change the time.** robot_1 was measured loaded (24.4 s)
  and robot_2 unloaded (24.2 s) on mirror-identical 4.0 m courses. T2b
  robot_1, unloaded on the same 4.0 m eastbound course, times 24.2 s. So the
  prop's effect is within the 0.2 s cross-course agreement.

---

## Delay Re-Score of the Known Episodes (Part 3, Filled In)

This is the Part-3 re-score from `docs/reports/2026-10-05-flow-metrics.md`
re-run with `free_flow_v1`. It uses a session-local driver that calls the
committed `score_ib10` / `score_b1` on the same bundles. Without a table it
reproduced Part 3's classes and travel times exactly. The CLI with no
`--free-flow` now picks up the committed table (`table_id: free_flow_v1`).

Delay is `(accepted arrival − own departure) − free-flow time`, in seconds.
"≥" marks a censored robot's lower bound, charged to the episode end. Outcome
classes are unchanged from Part 3.

### IB10 (free flow 20.9 / 20.9 / 20.7 / 20.9 s)

| Episode | Class | robot_1 | robot_2 (passer) | robot_3 | robot_4 | Sum | Max |
|---|---|---|---|---|---|---|---|
| step-6 run A (mock) | `clogged` | ≥ 261.8 | **58.6** | ≥ 262.1 | ≥ 261.7 | ≥ 844.2 | — |
| step-6 run B (mock) | `clogged` | ≥ 260.9 | **81.4** | ≥ 261.0 | ≥ 260.8 | ≥ 864.1 | — |
| step-6 live ep1 (ER-2) | `null` (harness-invalid) | ≥ 262.2 | **51.6** | ≥ 261.6 | ≥ 262.1 | ≥ 837.5 | — |
| step-6 live ep2 (ER-2) | `clogged` | ≥ 261.3 | **50.2** | ≥ 259.6 | ≥ 261.4 | ≥ 832.5 | — |
| step-7b rerun 1 (mock) | `clogged` | ≥ 248.3 | **54.8** | ≥ 248.5 | 101.8 | ≥ 653.4 | — |
| **step-7b rerun 2 (mock)** | `resolved` | 182.1 | **56.1** | 150.0 | 115.1 | **503.3** | 182.1 |
| v2 demo ep1 (scripted) | `resolved` | 182.0 | **56.9** | 117.4 | 149.7 | **506.0** | 182.0 |
| **v2 demo ep2 (live ER-2)** | `resolved` | 179.4 | **52.5** | 111.9 | 146.7 | **490.5** | 179.4 |

### B1 (free flow 20.7 / 18.1 / 30.5 s)

| Run | Class | robot_1 | robot_2 | robot_3 | Sum |
|---|---|---|---|---|---|
| B1FIX_S42 | `clogged` | 0.5 | 0.4 | ≥ 130.9 | ≥ 131.8 |
| B1FIX_S43R | `clogged` | 39.1 | 104.4 | ≥ 98.6 | ≥ 242.1 |
| B1FIX_S43 | `clogged` | 88.4 | 106.7 | ≥ 56.9 | ≥ 252.0 |

### Sanity

1. **Every delay is positive.** That holds for all 24 measured delays and all
   17 censored lower bounds. The smallest are B1FIX_S42's lead pair (0.5 and
   0.4 s). Those robots crossed nearly unobstructed, so this is the expected
   near-zero case, and it is the strongest calibration of the table: an
   independent multi-robot run reproduces the solo time to within 0.5 s.
2. **The IB10 passer is the least delayed.** robot_2's delay (50.2–81.4 s)
   is below every held robot's delay or lower bound in every episode. In the
   three resolved episodes it is 52–57 s against 112–182 s. The yielder
   (robot_1) carries the largest delay, about 180 s, in all three resolved
   episodes. That matches the step-7b ruling (vi) chain, in which the yielder
   re-enters last.
3. **Part 3's estimate is confirmed.** It predicted about 50 s for the passer
   and 110–180 s for the receders and yielder from a 20–25 s solo guess. The
   measured solo IB10 time is 20.7–20.9 s.

---

## Deferred / Not Harvested

- **No cell in the requested set was deferred.** All 8 cells (22 runs) ran in
  one healthy session.
- **`blocked_path_object` / `_transient` were not in this run list.** The
  generator handles them, since `blocked_path_*` are registered blocker cells
  and a test dry-generates one. Adding them to `FREE_FLOW_CELLS` and running 4
  more variants is about 25 min of VM time. Their robot_2 goal is the north
  pocket (0.0, 1.75) in both the scenario yaml and the M5 goal table, so no
  goal ruling is needed.
- **`convoy_counterflow` (B3 non-slip) is not in the table.** It was not in
  the run list and is not registered as covered by
  `convoy_counterflow_slip`; covering it would need a geometry check and a
  ruling.

---

## Verification

Full local suite, run as `pytest -q -p no:cacheprovider
--continue-on-collection-errors`, on a clean detached baseline
(`/tmp/ff_baseline_b264e9d` at `b264e9d`):

| Tree | Failed | Passed | Skipped | Errors |
|---|---|---|---|---|
| Baseline `b264e9d` | 63 | 4962 | 154 | 3 |
| Branch `fc8c704` | 63 | 5111 | 153 | 3 |

- **Zero-delta.** The 66 failing and erroring test ids (ANSI-stripped) are
  identical between the two trees.
- **Where the +149 come from:**
  - 144 from `test_free_flow_variants.py`;
  - 2 from the fc_launch dry-run free-flow cases;
  - 2 from the solo-in-space derive guard;
  - 1 from the committed-table schema test, which no longer skips. That is
    the 154 → 153 skip change.
- **Lint.** `ruff check` is clean on every new file. The two E501 lines in
  `test_fc_launch_dry_run.py` predate this branch.

---

## VM State

| Check | Result |
|---|---|
| Pre-deploy md5 snapshot (764 paths) | All OK. No tracked path exists that was absent before the deploy. |
| `isaac/scenarios/` and `isaac/config/scenarios/` listings | Identical to pre-deploy. The 22 variant USDs and the `free_flow/` dir were removed, along with the variants' `data/logs/simulation/*_ff_*` dirs. |
| `orchestrator.yaml` | Source `1f656533…` and installed `1f656533…`. |
| `config/rag.yaml` | `e18c723c…` |
| Isaac / fc_launch processes | None |
| GPU | 0 %, 171 MiB, 0 compute apps |
| Instance | Still RUNNING, left as found. It bills while running; stopping it is the owner's call. |

The run bundles remain on the VM under `data/logs/vm_runs/free_flow/`
(untracked, as in prior sessions). The backup remains at
`/home/ubuntu/ff_predeploy_backup/`. API spend was zero: mock backend, and no
analyses were triggered.

---

## Open Items

- Optional extension: harvest `blocked_path_*` (4 runs, about 25 min) by
  adding them to `FREE_FLOW_CELLS`.
- Ruling needed: whether `convoy_counterflow` is covered by
  `convoy_counterflow_slip`.
- The `t2b_flow_ordering.yaml` header claim that fc_launch's
  `--duration-sec` overrides the yaml duration is wrong. The flag is dead.
  The comment is left untouched, since changing it is a scenario-file edit.

---

## References

- Spec ruling: main checkout
  `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, "Foundations round
  adopted (2026-10-05)".
- Method analysis and Part 3: `docs/reports/2026-10-05-flow-metrics.md`.
- Tooling:
  - `scripts/free_flow_table.py`
  - `scripts/make_free_flow_variants.py`
  - `scripts/vm/free_flow_run.sh`
  - `scripts/vm/free_flow_batch.sh`
  - `scripts/vm/fc_launch.sh` (`MAP_SCENARIO`, `free_flow/` lookup)
- Table: `config/free_flow/free_flow_v1.json`.
- Run logs: main checkout `data/logs/vm_runs/free_flow/`, which also holds
  the batch logs `ff_batch_b1.log` and `ff_batch_b2.log` and the build log
  `ff_build_usd.log`.

# v3 Step 0 VM Re-Baseline: Stages 1–5 on `071f9c1`

**Prepared:** 2026-10-08

**Revision history:**

- Initial draft: resumed the Step 0 wave from the stage-1 stop (`docs/reports/2026-10-08-v3-step0-stop.md`) under the coordinator rulings. The VM was redeployed to `feat/v3-integration@071f9c1`, the stage-1 acceptance smoke passed on the cell's registered goals, and stages 2–5 ran as written in the batch driver, plus one IB10 replicate.

---

## Summary

All runs used the mock backend, with zero API calls. Tree: `feat/v3-integration@071f9c1`, with `orchestrator.yaml` kept at the VM-pinned `1f656533` (Deviations 1).

| Stage | Outcome |
|---|---|
| Redeploy `a823aeb` → `071f9c1` | **Verified.** 12 files shipped, 0 installed mismatches, 0 orphans. The 868-file manifest check gives exactly 1 FAILED (the pinned `orchestrator.yaml`) and 0 MISSING. M5 loaded the pinned yaml on every run: 0 `Traceback` lines across all 32 bundled `m5.log` files. |
| 1. Acceptance smoke, registered goals | **PASS.** Both arrivals accepted (0.10 / 0.09 m). Phantom-closure signature 0. Option B tail active. Audit keys present, including `071f9c1`'s `plan_dispatch_order_source: chi`. Cycle 825 s. |
| 2. `free_flow_v2`, 22 legs | **22 / 22 valid.** Per-leg deltas against `free_flow_v1` are −0.8 to +0.2 s (mean −0.07 s). 20 of 22 are within ±0.5 s and all are within the registered ±1.5 s. |
| 3a. T3c ×3 (`s42`, `s43`, `s44`) | **Fix-branch timing reproduces.** robot_1 arrives 13.1–14.2 s after the pallet is removed (fix branch 13.6 s, pre-fix 32.0 s). No post-resume pause. 2 / 2 arrivals in each run. |
| 3b. `loop_detour_transient` | **Route anomaly: never arrived.** robot_1 self-detoured into the second aisle, then sat wedged at the second-aisle mouth corner from sim 34 s to the end (240 s). It was nowhere near the box, so this is not box-hugging. Bag evidence: 0 closed aisle columns. |
| 3b. `blocked_path_transient` | **No anomaly.** robot_1 held west of the blocker and arrived 29.0 s after its removal. 2 / 2 arrivals. |
| 4. IB10 scripted composite | **FAIL: 1 / 4 arrivals, reproduced in a replicate (1 / 4)** (fix branch 4 / 4). The release-phase passer robot_4 drove into a held robot_3 while their pair was exempt from the safety monitor's min-distance check. When the exemption lapsed, a min-distance safety stop latched both robots until the episode ended. Both runs formed chi [robot_4, robot_3]. `junction_phases` is present. The R3.3 flag was not engaged. |
| 5. Wedge re-check | **The wedge persists on the merged tree.** `perm_wait`: never arrived, 193.6 s of mouth dwell (pre-fix: never arrived, more than 150 s). `diag_costmap`: never arrived by the stack teardown at ≈ 214 s, 164.9 s of mouth dwell (pre-fix: one 15 s pause, then arrived 55.9 s after t0). |

**Verdict.** The stage-1 gate passed, and stages 2–5 ran in full. Two findings need coordinator attention:

- **IB10 regressed from 4 / 4 to 1 / 4, reproduced in a replicate,** through a passer–yielder contact inside the release phase's safety exemption.
- **The DWB corner wedge at the loop map's second-aisle mouth is not removed by A′+H.** It now appears in all three loop-map runs: `ldt`, `perm_wait` and `diag_costmap`.

Neither finding is attributed to a cause here. The rulings forbid pre-fix attribution arms.

---

## Method

### Redeploy

| Item | Value |
|---|---|
| VM | `vgu-vgu-thule-base-isaac-workstation-vm` (us-central1-c), Isaac Sim 6.0.1, container `vgu_ros` |
| Tree before | `feat/v3-integration@a823aeb` (stop report) |
| Ship | The 12 files of `git diff --name-only a823aeb 071f9c1` minus `orchestrator.yaml`: 7 modified and 5 new. They were taken from a `git archive` of `071f9c1` (not the worktree, whose HEAD is the docs commit `73795f3`), copied in and `touch`ed. Backup: `deploy2/backup/mod_files.tar`. No rsync and no `--delete`. |
| Rebuild | `swarm_orchestrator` was the only changed `ros2_ws` package. Its `build/`, `site-packages` and `share` were removed, then rebuilt with `colcon build --merge-install`. `reasoning/rag` is live-mounted and was shipped without a rebuild. |
| Installed verification | 22 installed files are md5-equal to source. 0 mismatches and 0 orphans. The new module `contradiction_trigger.py` is present in installed `site-packages` (trap 17). |
| Tree identity | `md5sum -c` against the 868-file `071f9c1` manifest (built from `git archive`, excluding `__pycache__`) gives exactly 1 FAILED (`orchestrator.yaml`, pinned) and 0 MISSING. |
| Config load | Before deploying, the pinned `1f656533` yaml and the three stage overlays (IB10 `35734f4e`, T3c `237ada05`, T3a `f6e5b48c`) were each loaded through `071f9c1`'s `load_config`. All four give `plan_dispatch_order_source=chi`, `contradiction_trigger.enabled=false` and `failure_explanation_enabled=false`. Live, M5 started on every run, with 0 `Traceback` lines across the 32 bundled `m5.log` files (smoke, 22 free-flow legs, 3 T3c, 2 transient, 2 IB10, 2 wedge). |

Installed md5s after deploy:

| File | md5 |
|---|---|
| `swarm_orchestrator/reasoning_pipeline.py` | `b9c32532…` |
| `swarm_orchestrator/orchestrator_node.py` | `9c86d5c4…` |
| `swarm_orchestrator/models.py` | `efa1d166…` |
| `swarm_orchestrator/command_lifecycle.py` | `37793a04…` |
| `swarm_orchestrator/contradiction_trigger.py` | `3eaaa9dc…` (new) |
| `reasoning/rag/command_grounder.py` | `5839d2b1…` |
| `reasoning/rag/maneuver_geometry.py` | `c098de18…` |
| `swarm_orchestrator/config/orchestrator.yaml` (src and installed) | `1f656533…` (VM-pinned) |
| Nav2, perception and harness files | unchanged from the stop report (`nav2_params.yaml` `cbc33745`, `nav2_robot.launch.py` `9cf43a58`, `camera_localizer.py` `3cdc250f`, `camera_localizer_node.py` `65a9cc2a`, `fc_launch.sh` `30986057`, `runner.py` `4a59bf92`, `rag.yaml` `e18c723c`) |

### Drivers

- **`batch3.sh`.** This is the stop report's `batch.sh` (md5 `1deeb063`) with two changes: a new header, and an added `smokereg` step. The stage 2–5 steps are byte-identical.
- **`smokereg`.** It runs `v2_final_run.sh` with `OVERLAY_FILE=deploy2/headon_bshort_orchestrator.yaml`, which brings the pristine pre-check, the fresh-mtime restore, the rebuild and the `RESTORE OK` check. It also runs a 1 Hz process sidecar and a live dump of the four costmaps' parameters.
- **Stage-1 overlay (`74b908d4`).** It is `1f656533` with only the `initial_tasks` block changed to the cell header's registered goals: robot_1 → (2.6, 0) and robot_2 → (−1.5, 0). The diff is exactly those two lines. During the run, the installed copy was `82341dc5`, which is the overlay after `fc_launch.sh`'s `reasoning_backend_id: mock` rewrite; that rewrite was verified offline.
- **Launch order.** Stages 2 and 3a ran as separate batch invocations. Stages 3b–5 ran from one chain script (`chain35.sh`) that waited for 3a's `BATCH COMPLETE`. Each step kept the batch's `pgrep -f '[r]un_simulation'` empty gate. Every run ended `RESTORE OK` (src and installed `1f656533`, rag `e18c723c`).

### Scoring

- Every number below is GT-only (Isaac clock) or same-clock, so no GT↔ROS offset fit is needed (trap 18).
- Arrivals count both M5 acceptance strings: `arrived at base goal` and `arrival accepted late`.
- Scripts: the committed `scripts/free_flow_table.py derive_entries` and `scripts/coverage_scene_scores.py ib10`. Session tools in the local bundle's `_analysis/`: `smoke_reg.py`, `ff_compare.py`, `t3c_timing.py`, `route_anom.py`, `dwell.py`, `bag_costmap.py` and `closed_cols.py`.
- The seed is only a label. It names the GT directory and is never used as a random seed in `isaac/vgu_sim`, so `t3c43` / `t3c44` and the IB10 replicate are pure replicates.

---

## Stage 1: Acceptance Smoke (Registered Goals)

Cell `head_on_asymmetric_w0p2_eopen_bshort_o0`, mock `head_on_yield_robot_2_once.json`, `REC_SEC=1000`, `SIM_SEC=1200`, seed 42. Run `headon_reg_s42` (`20261007_083338`).

| Criterion | Result |
|---|---|
| Run completes | GT 3001 lines, last `sim_time_sec` 300.0, manifest `completed: true`. `GATE OK`, and M5 demonstrably ran. |
| **Both arrivals accepted (M5)** | **2 / 2.** robot_1 (2.6, 0) at 0.10 m and robot_2 (−1.5, 0) at 0.09 m, both `within_tolerance`. 0 rejected. GT arrivals 86.5 / 108.8 sim-s. |
| **Phantom-closure signature** | **0.** No spec defines it for a non-probe run, so here it means a planner failure caused by lethal marks in free aisle space. There were 4 `Failed to create plan` lines, all explained: robot_1 had 3, at sim 16.8–20.9 s, while robot_2 was physically head-on inside the 0.55 m aisle (0.85–2.1 m ahead), which is real occupancy. robot_2 had 1, at sim 91.1 s: a NavFn `Failed to create a plan from potential when a legal potential was found` that recovered 1 s later after a costmap clear. The `a823aeb` smokes had 4 / 0 and 4 / 3. |
| **Option B tail active** | `Isaac exited …; ending the M5 tail after 10s grace (735s into the tail)`. Isaac was gone 0 s after the wrapper exited. |
| **Audit keys** | The grounded `yield` artifact carries `dispatched_command`, `dispatched_robot_ids` and `dispatch_dropped_robot_ids`, plus `plan_dispatch_order_source: "chi"` and `dispatch_order_source: "chi"`. Those two prove `071f9c1`'s code ran, not just that it was installed. `trigger_source` is absent, as expected with the trigger off. `junction_phases` and `dispatch_filter_error` are absent by design on this scene. |
| **Cycle ≤ ~860 s** | **825 s** from `fc_launch` launch to exit (the wrapper took 828 s). The `a823aeb` smokes took 844 / 853 s; the Option B smoke took 838 s. |
| Other | 2 analyses: 1 grounded `yield` and 1 `none`. `reasoner_config_effective.backend_id = mock`, and M5 shows 0 `openai` or `http` mentions. All four costmaps report `clearing: True`, `marking: True`, raytrace and obstacle range 3.5. robot_2 never routes around `blocker_west` (min clearance 0.288 m), by design of the registered goals. |

**The north-grind finding stands as a finding, not a gate.** On the off-design pristine goals, robot_2 took the north side of `blocker_west` in both `a823aeb` smokes. It pressed against the box face for 170–190 s, and in `s42` it never arrived (stop report, Results). That is the same DWB press-against-a-face family as the stage-5 wedge below.

---

## Stage 2: `free_flow_v2` vs `free_flow_v1`

The USDs were built in one SimulationApp session, and all 22 are newer than their yamls. Every leg shows:

- `GATE OK`;
- exactly 1 accepted M5 arrival and 0 decision artifacts, so 0 dispatches;
- GT `completed: True`;
- 0 jump-back warnings and 0 planner or progress failures;
- `RESTORE OK`.

Each leg took about 5.5 min of wall time.

Times are `derive_entries` solo-in-space values (own departure, `gt_within_0.35_stay_0.5`), in sim-seconds.

| Leg | v1 | **v2** | Δ | v2 run |
|---|---|---|---|---|
| head-on `bshort` robot_1 | 25.0 | **25.0** | 0.0 | `20261007_085026` |
| head-on `bshort` robot_2 | 17.5 | **17.6** | +0.1 | `085554` |
| `t2b_flow_ordering` robot_1 | 24.2 | **24.3** | +0.1 | `090125` |
| `t2b_flow_ordering` robot_2 | 20.8 | **20.8** | 0.0 | `090653` |
| `t2b_flow_ordering` robot_3 | 26.2 | **26.3** | +0.1 | `091225` |
| `bottleneck_merge` robot_1 | 20.7 | **20.7** | 0.0 | `091757` |
| `bottleneck_merge` robot_2 | 18.1 | **17.4** | −0.7 | `092325` |
| `bottleneck_merge` robot_3 | 30.5 | **30.4** | −0.1 | `092857` |
| `priority_visual_r1` robot_1 | 24.4 | **24.2** | −0.2 | `093427` |
| `priority_visual_r1` robot_2 | 24.2 | **24.2** | 0.0 | `093953` |
| `convoy_counterflow_slip` robot_1 | 22.4 | **22.2** | −0.2 | `094522` |
| `convoy_counterflow_slip` robot_2 | 18.8 | **18.9** | +0.1 | `095055` |
| `convoy_counterflow_slip` robot_3 | 27.6 | **26.8** | −0.8 | `095623` |
| `convoy_counterflow_slip` robot_4 | 26.2 | **26.4** | +0.2 | `100151` |
| `intersection_bottleneck` robot_1 | 20.9 | **20.9** | 0.0 | `100719` |
| `intersection_bottleneck` robot_2 | 20.9 | **21.0** | +0.1 | `101246` |
| `intersection_bottleneck` robot_3 | 20.7 | **20.7** | 0.0 | `101813` |
| `intersection_bottleneck` robot_4 | 20.9 | **20.9** | 0.0 | `102342` |
| `obstacle_in_candidate` robot_1 | 14.3 | **14.2** | −0.1 | `102906` |
| `obstacle_in_candidate` robot_2 | 30.9 | **30.9** | 0.0 | `103432` |
| `dynamic_anomaly_v2` robot_1 | 31.0 | **30.9** | −0.1 | `104003` |
| `dynamic_anomaly_v2` robot_2 | 30.9 | **30.9** | 0.0 | `104531` |

**Reading.**

- **Free flow is unchanged by the merged tree.** The largest deltas are B1 robot_2 (−0.7 s) and B3 robot_3 (−0.8 s). B1 robot_2 is the turning route; the fix branch's spot check also read −0.8 s there.
- **Departure** times are 10.0–13.2 sim-s in v2 against 10.4–13.9 in v1. That is the same M5-start band; t2b robot_2 departed 0.4 s before v1's earliest.
- **`free_flow_v2` table.** No new table file was written or committed. The numbers above are the measured re-baseline. Freezing a `free_flow_v2.json` is a separate commit if the coordinator wants one.

---

## Stage 3: T3c and the Transient Cells

### T3c (`dynamic_anomaly_v2`, A/B against frozen numbers)

Run with overlay `237ada05`, mock default (no dispatch), `REC_SEC=750`. The A arm is the frozen pre-fix number from `docs/reports/2026-10-05-costmap-fix-validation.md`; no pre-fix arm was run.

| Quantity | Frozen V1 (09-27) | Pre-fix `t3c_prefix_s42` | Fix branch `t3c_fix_s42` | **v3 `s42`** | **v3 `s43`** | **v3 `s44`** |
|---|---|---|---|---|---|---|
| Run (stamp) | — | `20261005_151856` | `20261005_172712` | `20261007_105148` | `110126` | `111109` |
| robot_1 stall (sim, x) | 30.6, −0.08 | 30.8, 0.09 | 30.8, 0.40 | 31.0, 0.10 | 30.7, 0.13 | 30.9, 0.11 |
| robot_1 x at removal (110.0) | 0.04 | 0.50 | 0.73 | 0.42 | 0.33 | 0.54 |
| Resume after removal | +2.3 s | +2.6 s | +4.9 s | +3.0 s | +2.8 s | +2.5 s |
| Post-resume pause ≥ 3 s | 18.4 s | 17.0 s | none | **none** | **none** | **none** |
| **robot_1 arrival after removal** | +35.1 s | +32.0 s | +13.6 s | **+13.9 s** | **+14.2 s** | **+13.1 s** |
| robot_1 / robot_2 GT arrival | 145.1 / 45.4 | 142.0 / 44.6 | 123.6 / 42.6 | 123.9 / 43.9 | 124.2 / 44.1 | 123.1 / 44.4 |
| nav2_r1 create-plan / progress failures / clears / goal failed | 84 / 1 / 68 / 5 | 88 / 1 / 72 / 5 | 73 / 0 / 59 / 4 | 88 / 0 / 71 / 5 | 84 / 0 / 67 / 5 | 85 / 0 / 68 / 5 |
| M5 analyses / dispatches | 15 / 0 | 16 / 0 | 13 / 0 | 11 / 0 | 12 / 0 | 13 / 0 |

**Reading.**

- **The fix's T3c shift reproduces 3 / 3 on the merged tree.** The post-removal pause stays gone, and the arrival lands 13.1–14.2 s after removal: a spread of 1.1 s around the fix branch's 13.6 s.
- **Stall position varies.** The stall sits 0.10–0.13 m into the lane, nearer the pre-fix value than the fix branch's 0.40. The x at removal ranges 0.33–0.54. These are between-run variation in where DWB settles against the pallet, and they do not move the arrival.
- **Run health.** 0 safety stops (the M4 log has only the startup lines), 2 / 2 accepted arrivals in every run, 0 bring-up aborts.

### Transient cells (v3 re-baselines, not frozen edits)

These values are **v3 re-baselines**. They are not edits of any frozen v2 number: no frozen v2 value was located for either cell. Any earlier, v2-era reference for these cells would carry the never-clearing costmap (the fix report's T3c section explains why), while these runs had `clearing: true`. Both runs carried an observer-only bag (Deviations 3).

| Quantity | `loop_detour_transient` (`loop_transient_s42`, `20261007_112105`) | `blocked_path_transient` (`blocked_transient_s42`, `20261007_113054`) |
|---|---|---|
| Blocker (GT clock) | marker-less robot visual at (1.0, −0.095), present 0–45 s | marker-less robot visual at (−0.5, 0), present 16–70 s |
| robot_1 departure | 12.1 | 15.0 |
| **robot_1 outcome** | **Never arrived. Censored at the 240 s horizon.** | **Arrived 99.0 s** (29.0 s after removal) |
| robot_2 | — | arrived 18.5 s (north pocket) |
| M5 accepted / rejected | 0 / 0 | 2 / 0 |
| M5 analyses / dispatches | 15 / 1 (`temporary_wait`) | 7 / 1 (`temporary_wait`) |
| Min GT distance from robot_1 to the blocker while present | 0.969 m | 0.869 m |
| Time < 0.12 m from the blocker (box-hugging) | 0 s | 0 s |
| robot_1 max \|y\| | 0.978 (entered the second aisle) | 0.116 |
| Stationary spells ≥ 5 s | 11 spells, all at the second-aisle mouth (0.557–0.580, 0.893–0.975), 34.0–240 s, total 184.2 s, longest 40.6 s | 4 spells while blocked, west of the box (x −1.80 to −1.50), 47.2 s in total |
| nav2_r1 create-plan / progress failures | 0 / **8** | 54 / 0 (the box fills the aisle until 70 s) |

**Route-anomaly watch (stage 3).**

- **`loop_detour_transient` shows an around-obstacle route anomaly.** It is not box-hugging; it is a **corner wedge after a self-detour**.
  - **The self-detour.** NavFn's first plan at 12.2 s went direct. From the next sample on, plans went round the loop. This matches the pre-fix loop-family runs, which detoured robustly.
  - **The wedge.** robot_1 reached the second-aisle mouth at 34 s and never left, with 8 `Failed to make progress` aborts. This happened even though the blocker vanished at 45 s.
- **Costmap evidence from the observer bag** (`transient/loop_transient_s42/bag/`, `_analysis/closed_cols.py`, `_analysis/bag_costmap.py`):
  - **No phantom closure.** 0 closed second-aisle columns over all 209 global-costmap states (x 0.65–1.5, y 0.6–1.5, the `max_closed.py` definition rebuilt from the raw bag).
  - **New lethal cells against the first full grid** sit only along the static block edges of the mouth: x 0.53 (y 0.63–0.88), a y 0.98 row (x 0.93–1.38), and x 1.58 (y 0.58–0.83). None crosses the aisle.
  - **The global plan was valid throughout.** 417 of 426 recorded plans run through the second aisle at y ≈ 1.04–1.14.
  - **Reading:** a DWB local minimum at the mouth corner, not a costmap closure. robot_1 held at y 0.89–0.98 against the block's north edge while the plan ran about 0.15 m north of it.
  - **Not done:** no pre-fix attribution arm was run, per the ruling.
- **`blocked_path_transient` shows no anomaly.**
  - **Blocker phase.** robot_1 waited west of the box, never closer than 0.87 m. The blocker's marks cleared after removal, and robot_1 crossed in 29 s.
  - **Residual marks.** Lethal cells persist after removal at y −0.12 to −0.17, x −1.1 to −0.3, inside the free band whose inflated wall edge is at y −0.22. They narrow but never close the aisle.
  - **What they are is not established.** Their source (wall-face returns or otherwise) is not asserted here.

---

## Stage 4: IB10 Scripted Composite

`intersection_bottleneck`, overlay `35734f4e`, mock `intersection_junction_clear_vlm_verbatim_once.json`, `REC_SEC=1400`. Scored with `scripts/coverage_scene_scores.py ib10 --allow-mock`.

| Criterion (7b rerun 2) | Fix branch `ib10_s42` (`20261005_162933`) | **v3 `ib10_s42`** (`20261007_113945`) | **v3 replicate `ib10_s42_rep2`** |
|---|---|---|---|
| Formed-jam gate | valid, onset 34.9, longest 15.4, 4 / 4 | valid, onset 34.6, longest 17.5, 4 / 4 | valid, onset 32.7, longest 15.3, 4 / 4 |
| chi-pair | chi [r3, r4], proposed [r4, r3], `order_equivalent`, verbatim | chi = proposed = executed **[robot_4, robot_3]**, `vlm_verbatim`, yielder robot_1 | chi = proposed = executed **[robot_4, robot_3]**, `vlm_verbatim`, yielder robot_1 |
| R3.3 flag engaged? | — (pre-R3.3) | **No:** `plan_dispatch_order_source: chi` and per-decision `dispatch_order_source: chi`; the executed order equals the chi order | **No** (`chi` / `chi`) |
| Phase reached | resolved (recede → cross → release → resolved) | **release; never resolved**, no fallback | **release; never resolved**, no fallback |
| Gate transits (sim) | r3 admit → cleared 17.7 s; r4 13.8 s; yielder release 136.5 | admit robot_4 (passer, yielders r3 + r1) at 105.7; cleared r3 and r1 at 148.0; admit robot_3 (passer for r1) at 148.0, **never cleared** | admit robot_4 at 101.7; cleared r3 and r1 at 149.4; admit robot_3 at 149.4, **never cleared** |
| Inside-first / ordered release | True / True | True / True | True / True |
| **Arrivals** | **4 / 4** | **1 / 4** (robot_2 only) | **1 / 4** (robot_2 only) |
| Arrival times after t0 (r2 / r3 / r4 / r1) | 77.2 / 97.8 / 114.1 / 128.4 | 78.0 / — / — / — (r4 stopped 0.39 m from its goal) | 75.9 / — / — / — (r4 stopped 0.38 m from its goal) |
| Last arrival after t0 | 128.4 | robot_2 at 78.0; three robots censored | robot_2 at 75.9; three robots censored |
| `junction_phases` in the artifact | present | **present** (`phases` ×4, `fallback_command`, `fallback_held_robot_ids`) | **present** (same three keys) |
| `outcome_rank` | (1, 4, 4) | (0, 3, 1) | (0, 3, 1) |

**Mechanism in `ib10_s42`.** Evidence is from GT plus the M4 log.

1. **Sim 105.7: the release phase starts.** The gate admits robot_4 as the passer, heading south to (0, −1.75). robot_3 (yielder, `yield` with passer robot_4) and robot_1 are held. The safety monitor's exempt pairs become `robot_1+robot_4, robot_3+robot_4`.
2. **robot_3 sat in robot_4's lane.** It stayed at its recede pocket (0.01, −1.01) on the south arm, in robot_4's path, and did not move until contact.
3. **Sim ~120: contact.** robot_4 reached robot_3 with a centre distance of 0.08–0.09 m. From 120 to 148 it pushed robot_3 south-west to (−0.32, −1.47) and stopped at (−0.23, −1.43). No min-distance stop fired, because the pair was exempt.
4. **Sim 148.0: the exemption ends.** robot_3's release `yield` completed (gate cleared r3 / r1), and the gate admitted robot_3 as the next passer. The exempt pair `robot_3+robot_4` was dropped. The safety monitor then issued continuous `min_distance_violation` stops on both robots from that moment to the episode end: ROS wall stamps 1791373789.6 to 1791374471.8, that is 682 s. With 0.09 m < 0.45 m, the pair can never separate.

**Reading.**

- **The registered `ib10_s42` result is FAIL.** It is a resolution failure through a physical passer–yielder contact inside a sanctioned safety exemption, not a jam-formation or grounding failure: the jam, the chi pair, the phases and the R3.3 audit are all correct.
- **The lead flipped.** The fix-branch run released robot_3 first (chi [r3, r4]). This run released robot_4 first.
- **n = 1 cannot separate a systematic regression from an order- or timing-dependent outcome.** A robot_4-led release resolved in 7b rerun 2 (r4 arrived at 136.3, before r3 at 170.8). The replicate (Deviations 4) settles part of it. **`ib10_s42_rep2` reproduced the failure in detail.** The chi order was again [robot_4, robot_3]. robot_3 held at (−0.00, −1.02), never faster than 0.0002 m/s before contact. robot_4 came within 0.2 m at sim 115.0, with a minimum centre distance of 0.089 m at 131.9. The final poses were within 0.02 m of `ib10_s42`'s, and the same latched safety stop followed. **On this tree, a robot_4-led release fails systematically (n = 2).** What remains open is why the jam now forms with chi [robot_4, robot_3] in both runs, where the fix branch had [robot_3, robot_4], and whether a robot_3-led release would still pass here.
- **What `071f9c1` touched.** It changed the M5 and M3 code paths: `command_lifecycle`, `reasoning_pipeline`, `orchestrator_node` and `command_grounder`, each documented as byte-identical with its flag off. It did not touch M4, the safety monitor or Nav2. Any attribution between `071f9c1`, A′+H and ordering is a separate decision.

---

## Stage 5: Wedge Re-Check

These are the two scenarios in which the wedge was observed pre-fix, re-run on the merged tree with their recorded recipes (batch steps `permwait` and `diagcm`). They are scored with `_analysis/dwell.py` against goal (2.3, 0): GT stationary spells of at least 5 s, and the mouth region x 0.0–0.7, y 0.6–1.0.

| Quantity | `perm_wait_s42` pre-fix (`20261003_041339`) | **`perm_wait_s42` v3** (`20261007_120115`) | `diag_costmap_s42` pre-fix (`20261003_054917`) | **`diag_costmap_s42` v3** (`20261007_121119`) |
|---|---|---|---|---|
| Mock | wait once | wait once | silent (default) | silent (default) |
| Outcome | never arrived (censored 228.3 s) | **never arrived** (censored at 240 s) | **arrived 55.9 s after t0** | **never arrived** (censored at the stack teardown, ≈ 214 s) |
| Mouth dwell | > 150 s at (0.47–0.56, 0.68–0.93) | **193.6 s** in 5 spells at (0.566–0.578, 0.942–0.969), longest 81.6 s | one 15 s pause | **164.9 s** in 3 spells at (0.458–0.532, 0.851–0.869), longest 98.4 s (GT truncated at 214.0 s) |
| robot_1 max \|y\| | — | 1.137 | — | 0.88 |
| nav2_r1 progress failures | — | 9 | — | 8 (log truncated at the tail cap; see below) |
| M5 analyses / dispatches | — | 11 / 1 (`temporary_wait`) | — | 25 / 0 |

**Reading.**

- **A′+H does not remove the DWB corner wedge at the second-aisle mouth.** `perm_wait` wedges as it did pre-fix, at a slightly different spot, about 0.05–0.3 m north. `diag_costmap`, which pre-fix passed the mouth after a 15 s pause, now wedges for 164.9 s and never arrives before the stack teardown.
- **`loop_detour_transient` (stage 3) has the same signature,** with 0 closed columns in its bag.
- **This is the same press-against-a-face local minimum as the north grind** in the stop report.
- **n = 1 per scenario, and no pre-fix arm.** The worsening in `diag_costmap` is therefore not attributed to `clearing: true` or anything else. It is a lead for the coordinator.
- **`diag_costmap`'s capture is partial, and its numbers are cut at the teardown.**
  - **What happened.** Its `REC_SEC=450` cap ended the M5 tail at 440 s while Isaac was still running. fc_launch's cleanup then restarted `vgu_ros`, killing Nav2, M4 and M5, while Isaac kept simulating.
  - **When.** The last M5 scene is ROS-stamped 215.0, and the last Nav2 `scene_stamp` is 213.9.
  - **What GT holds.** GT has 2401 lines to 240 s, because writes continued into the moved directory. Rows after about 214 s come from a robot with no controller.
  - **Scoring.** The dwell figures above therefore use GT truncated at 214.0 s. Untruncated, the figure would be 167.7 s and max \|y\| 0.935.
  - **Still comparable.** Pre-fix ran with the same 450 s cap and arrived at t0 + 55.9 s, well inside it.
  - **Manifest.** No `run_manifest.json` reached the bundle.

---

## Deviations

1. **`orchestrator.yaml` kept at the VM-pinned `1f656533`**, not `071f9c1`'s `c72a7ca` version. `071f9c1` adds only default-off keys (`plan_dispatch_order_source: "chi"`, `contradiction_trigger.enabled: false`, `failure_explanation_enabled: false`), each with a Pydantic default. The pinned file and the three overlays load under `071f9c1`'s models with those defaults, and every driver asserts `1f656533`. This is the same deviation as the stop report's.
2. **Stage-1 goals-only overlay** `74b908d4` (the registered `bshort` goals on `1f656533`), run through `v2_final_run.sh`'s `OVERLAY_FILE`. Its installed form during the run was `82341dc5`, after `fc_launch`'s backend rewrite. This is the cell header's own prescribed convention, not a hand edit of the shipped config.
3. **Observer bags on `ldt` and `bpt`.** These recorded `/robot_1/global_costmap/costmap` and `costmap_updates`, `/robot_1/local_costmap/costmap` and `/robot_1/plan`, for `BAG_SEC` 480 / 360. They were passed through `v2_final_run.sh`'s existing `BAG_TOPICS` env with the step unchanged. They exist to supply the costmap evidence the route-anomaly watch requires. The local-costmap renders used an assumed odom→map shift, so no local-costmap coordinate is cited.
4. **One IB10 replicate** (`ib10_s42_rep2`, `RETRY=_rep2`, same overlay, mock and tree) after the registered run failed. It is not a pre-fix or attribution arm.
5. **Chained launch.** Stages 3b–5 ran from one chain script after 3a. Every step kept its own drain and restore gates.
6. **`free_flow_v2` not frozen.** The measurements are reported. No table file was written.
7. **The branch moved during the wave again.** Another session merged S1 task-stream and S6 dual-conflict onto `feat/v3-integration` (`02bcd6e` … `11fa31a`). Those commits touch `swarm_orchestrator` (including `orchestrator.yaml`), `scripts/vm/v2_final_run.sh`, `isaac/vgu_sim/config.py` and `scripts/free_flow_table.py`.
   - **On the VM.** The VM holds `071f9c1`, as ruled. None of these commits ran here.
   - **Effect on this report's scoring.** None. The only scoring-side change is `count_dispatches` ignoring `dispatch_suppressed`, which is not used above. `derive_entries` and the IB10 scorer are unchanged.

---

## Open Questions (coordinator rulings)

1. **IB10.** Rule on whether the release-phase exemption contact (passer admitted while the yielder still sits in its lane) blocks v3. Also rule on whether to fund an attribution arm (`a823aeb` or pre-fix, ordered by lead), now that the replicate reproduced the failure with the same robot_4 lead.
2. **Corner wedge.** The wedge now hits every loop-map run: `ldt`, `perm_wait` and `diag_costmap`. Pre-fix it hit `perm_wait` hard but `diag_costmap` only for 15 s. Is a pre-fix `diag_costmap` / `ldt` arm wanted to attribute the worsening, or a DWB-side fix (critic or recovery tuning) scoped instead?
3. **`free_flow_v2`.** Should the 22 measured legs be frozen as `config/free_flow/free_flow_v2.json`? All are within ±0.8 s of v1.

---

## VM End State

- **Processes.** No `run_simulation`, `fc_launch`, batch or chain processes. GPU at 0 %, 171 MiB. `vgu_ros` up.
- **Tree.** `feat/v3-integration@071f9c1` stays deployed. `md5sum -c` against the 868-file manifest gives only `orchestrator.yaml` FAILED (VM-pinned `1f656533`, src and installed) and 0 MISSING. The installed md5s match the Method table.
- **Notes.** `NOTES.md` is at `/home/ubuntu/v3_step0/NOTES.md`, with a copy at `/home/ubuntu/vgu-vlm-swarm/V3_STEP0_NOTES.md`. Two hand-typed timestamps in it (stage 1 and stage 3) were wrong; they are corrected by an appended line, and all later entries use `date -u`.
- **Leftovers.**
  - The 22 free-flow variant USDs (`isaac/scenarios/*_ff_robot_*.usd`) built in this wave are **kept**, because they are valid for this tree. v1 removed its own.
  - 18 of the 20 pre-existing GT leftovers remain under `data/logs/simulation/`. The drivers moved the other two to `t3c/_rescued_*` and `transient/_rescued_*`.
  - Launch `.pyc` files were rewritten at run start (trap 19; harmless).
- **Left alone.** `/home/ubuntu/gpt56_sol_swap/` and `/home/ubuntu/shutdown_timing_probe/` were not touched.
- **Billing.** The VM is **still RUNNING and billing**. It was not stopped.

---

## References

- **Bundles.** VM `/home/ubuntu/v3_step0/` (`deploy2/`, `smoke/headon_reg_s42/`, `free_flow/`, `t3c/`, `transient/`, `ib10/`, `wedge/`, `batch3.sh`, `chain35.sh`, `NOTES.md`). Local gitignored copy in this worktree at `data/logs/vm_runs/v3_step0/`, with the `_analysis/` scripts.
- **Reports.** `docs/reports/2026-10-08-v3-step0-stop.md` (stage 1 stop, north grind); `docs/reports/2026-10-05-costmap-fix-validation.md` (fix-branch IB10 / T3c / rotation numbers); `docs/reports/2026-10-05-free-flow-table.md` (`free_flow_v1`); `docs/reports/2026-10-03-loop-family-and-visual-pass.md` (pre-fix `perm_wait` / `diag_costmap`).

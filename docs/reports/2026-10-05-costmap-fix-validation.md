# Costmap Fix A′ + H: Build, Live Validation and GT-Offset Audit (Parked, v3)

**Prepared:** 2026-10-05

**Revision history:**

- Initial draft: GT-offset audit of every GT-joined analysis artifact; the ruled fix A′ + H built with unit tests; offline replay of A′ on the probe bags; live validation on the VM (rotation probe ×2, waypoint reroute ×2, IB10 composite, free-flow spot checks ×3, loop pre-emption re-smoke ×2, T3c pre/post-fix A/B, IB10 pre-fix A/B); VM restored to the pre-fix pristine state.

---

## Summary

Branch `feat/v3-costmap-fix`, cut from `feat/prereg-v2-composite` at `a8fc1bc`. **PARKED for v3: not merged into the v2 line, not pushed.** Contract: the prereg-v2 design spec's "SOURCE ATTRIBUTED + FIX RULED (2026-10-05)" block (main checkout) and `docs/reports/2026-10-05-costmap-source-probe.md` (Rev 2), referred to below as "the probe report".

| Item | Outcome |
|---|---|
| **Part 0: GT-offset audit** | **No frozen number changes; no STOP.** Every v2-merged scorer is GT-only or offset-free (UNAFFECTED), except two BIASED consumers whose bias changes nothing: `score_loop.self_detour` (biased toward True by the GT clock offset; real margins 6.4–10.7 s) and the battery-v2 GT derivations (frame stamp used as GT time). Re-deriving all 139 battery-v2 items and all 60 battery-v1 items at shifts 0.30 / 0.45 / 0.55 s gives **0 answer flips**. The bias only moves eligibility margins (up to 18 / 41 temporal_order items fall under the registered 0.5 s "after the later event" floor at 0.30 s). |
| **The −0.45 s join offset, decomposed** | It is **mostly GT clock, not M1 latency, and the GT clock offset is scene-dependent**. Measured in the ROS domain against drift-free odometry: GT clock offset **0.300 s** in every single-robot loop-map run (4 runs), **0.500 s** in the 4-robot IB10 run (all four robots, residual < 0.1 mm). M1's own upstream latency on fresh detections is **0.005–0.075 s** (median ≈ 0.02 s) in both regimes. The probe report's "0.300 s" is therefore not a constant; the "M1 upstream 0.04–0.20 s" was inflated by carried-forward rows (below). |
| **A′ as built (refined)** | `camera_localizer.odom_lookup_stamp`: odometry is paired at the **robot entry's own stamp** (its last fresh detection), minus `m1_latency_compensation_sec` (measured default **0.01 s**). The bags show the dominant error was not latency: during fast turns M1 loses the marker for up to 0.6 s (`markers_detected: 0`) and carries the old pose forward with a frozen robot stamp while the scene stamp advances. The old `Time()` pairing (and the probe's option A, keyed on the scene stamp) composed that frozen pose with fresh odometry, up to 0.46 rad of yaw error. This refines the brief's "query odom at the M1 scene stamp" wording. |
| **H as built** | `obstacle_layer.scan.clearing: true`, `marking: true`, `raytrace_max_range: 3.5` on **both** costmaps (`nav2_params.yaml`). Verified live through `ros2 param get` in every probe run. |
| Offline replay (probe bags) | A′ alone, with clearing **off**: **0 / 0 / 0** closed columns at fast rotation (as-is 13 / 6 / 13; option A 7 / 0 / 9). A′ + H: 0 / 0 / 0. Over-compensating (d = 0.15 s) re-opens the defect: 8 / 0 / 12. |
| **1. Rotation probe** (`rot_a_s42`, `rot_a_s43`) | **PASS ×2.** 0 closed columns at every recorded grid of every phase (pre-fix 12 / 13). Max registration yaw error at fast rotation 0.083 / 0.061 rad (pre-fix 0.50 / 0.43). |
| **2. Waypoint reroute** (`wp_fwd_s42`, `wp_fwd_s43`) | **PASS ×2 — the reroute gap is closed.** WP0 reached 0.074 / 0.068 m, WP1 0.072 / 0.075 m, reroute `COMPLETED`, no watchdog, base arrival accepted (0.09 m / 0.09 m), 0 closed aisle columns in 164 / 163 crops. Pre-fix: WP1 never reached (0.90 / 0.96 m), watchdog kill, aisle closed from sim 18. |
| **3a. IB10 composite** (`ib10_s42`) | **PASS** on the 7b rerun-2 criteria: jam valid, 4/4, yielder last (GT and gate log), phases recede→cross→release→resolved, ordered release, in band, `outcome_rank` (1, 4, 4). **Timing shifts (same-tree pre-fix A/B):** last arrival 128.4 s after t0 vs 183.9 s pre-fix (−55.5 s); each released passer's junction transit roughly halves (robot_3 17.7 vs 38.2 s, robot_4 13.8 vs 32.3 s between gate events). |
| **3b. Free-flow spot checks** | **PASS ×3** (±1.5 s registered): head-on r1 25.0 s (Δ 0.0), B1 r2 17.3 s (Δ −0.8; the turning route), IB10 r1 21.0 s (Δ +0.1) against `free_flow_v1`. 0 dispatches each. |
| **3c. Loop pre-emption re-smoke** | **PASS ×2 — the phase-1 conclusion survives H.** Baseline: GT max \|y\| 0.010, 0 / 1161 sampled plans enter the second aisle. Blocker: GT max \|y\| 0.206, 0 / 388 plans in the second aisle, blocker still sub-lethal (99 / 99, as in phase 1). Positive control SUCCEEDED, 0 dispatches, arrival 28.8 / 29.4 s after t0 (phase 1: 28.9 / 29.2). |
| **3d. T3c `dynamic_anomaly_v2`** | **Outcome timing shifts as expected (quantified, not a FAIL).** Same pre-fix tree, mock, seed: the 17.0 s post-removal stall at x ≈ 1.15 (frozen V1: 18.4 s) **disappears**; robot_1 arrives **13.6 s** after the pallet's removal instead of **32.0 s** (V1 35.1 s), i.e. 18.4 s earlier. The obstacle-window behaviour is unchanged: stall at sim 30.8 in both, planner failures throughout the window, M5 triggers (13 vs 16 analyses), both arrivals accepted, 0 safety stops. |
| Suite | Baseline `a8fc1bc` (throwaway worktree) vs branch, same venv: 63 failed / 153 skipped / 3 errors on both; passed 5117 → 5129 (+12 new tests: 9 localizer, 3 costmap params). Failing/erroring name sets identical (66 = 66). |
| VM | **Restored to the PRE-FIX pristine state; the fix lives only in the branch.** Source = `a8fc1bc` manifest (742 files) except the pristine `orchestrator.yaml`; installed `swarm_perception` / `swarm_simulation` md5-identical to the pre-deploy snapshot (170 files); configs `1f656533…` (source and installed) / `e18c723c…`; temporary free-flow USDs removed; two pre-existing GT leftovers the drivers had moved aside put back. `pgrep` (Isaac, fc_launch, `isaac.scripts`, bag) empty, GPU 0 % / 171 MiB, VM left RUNNING idle as found. |

---

## Part 0: GT-Offset Audit

### Method

`scripts/gt_offset_audit.py` (new) re-derives frozen artifacts with the GT lookup time shifted onto the GT clock: `battery-v2` re-gates and re-derives every `manifest_v2.json` item (command windows, which open at decision `scene.stamp`s, move by the clock offset too); `battery-v1` re-runs the v1 manifest auditor with its GT lookup shifted; `loop` prints `self_detour`'s GT-vs-ROS margin. Shifts: 0.30 s (clock, single robot), 0.45 s (the empirical join offset), 0.55 s (clock 0.50 under 4-robot load plus M1 latency). At shift 0 the re-derivation reproduces 139 / 139 frozen answers.

### Consumer classification

| Consumer | What it joins | Class | Quantified |
|---|---|---|---|
| `coverage_scene_scores.py` `b1`, `b3` (slip onset), `ib10`, `conflict`, `flow` (`delay_vs_free_flow`, `conflict_dissolution`, `aperture_throughput`, `outcome_class`) | GT samples only; M4 gate `sim_t` compared only with M4 gate `sim_t`; M5 log for phase/dispatch counts | UNAFFECTED (GT-only) | — |
| `coverage_scene_scores.py` `loop` → `self_detour` | GT loop-entry time vs first decision `scene.stamp` (ROS) | **BIASED** toward True by the clock offset | Entry − dispatch margins on every existing loop run: −10.7 s (`perm_reroute_s42`, a real self-detour), +6.6 s, +6.4 s; none within 0.3–0.5 s. No outcome changes |
| `coverage_scene_scores.py` `loop` → `plans` | sampler `sim` (node clock) vs decision stamp | UNAFFECTED (same clock) | — |
| `free_flow_table.py` (`free_flow_v1`) | GT only (own departure → GT arrival) | UNAFFECTED | — |
| `rescore_arrivals.py` | GT matched by nearest **position**; scene stamps mapped to wall via M5 monotonic anchors; omitted-queue GT gap pairs GT rows at equal GT times | UNAFFECTED (offset-free); its −0.45 s note is documentation only, never applied | — |
| `t2b_forced_order.py`, `strategy_regret.py`, `m1_y_extent_probe_analysis.py` | GT only (y-extent: static robots vs authored spawn) | UNAFFECTED | — |
| Battery v1 (`build_capability_probe_manifest.py`, `audit_capability_probe_manifest.py`, `scanning.nearest_gt_row`) | decision `scene.stamp` used as GT time (0.5 s tolerance) | BIASED in principle, immaterial | 60 / 60 items pass the full audit at 0.30 / 0.45 / 0.55 s; max GT displacement 0.08 m against 0.3 m margins |
| Battery v2 (`episode_v2`, `dynamics`, `build_capability_probe_manifest_v2.py`) | frame stamp used as GT time (0.1 s tolerance) for motion, conflict horizon and temporal-event windows | **BIASED** (eligibility only) | **0 answer flips** at every shift. Eligibility drops at 0.30 / 0.45 / 0.55 s: motion_direction 1 / 2 / 2 (`ambiguous_option`), conflict_prediction 0 / 4 / 6 (`threshold_unreachable`, `command_in_horizon`), temporal_order 18 / 23 / 23 (`outside_window`: the frame sits closer than the registered 0.5 s after the later event; 7 of 19 main items at 0.30 s) |
| `visual_pass_crops.py` | snapshot stamp used as GT time | BIASED in principle, immaterial | every phase used (spawn, standoff `auto`, goal `end`) is stationary; worst case at 0.22 m/s × 0.5 s × 229 px/m = 25 px against the 70 px crop half-width |
| Ad-hoc `_analysis/` scripts | t2b smoke `analyze_t2b.py` and the T1 basket join M1 to GT at stamp − 0.45 s | offset-absorbed (M1↔GT joins) — correct to ±0.05 s in 2-robot scenes, off by ~0.06–0.15 s elsewhere (see decomposition) | v1-era diagnostics, not frozen scores |
| Waypoints / probe `_analysis/lag.py`, `m1vgt.py` | M1 vs GT at equal time | already corrected in the probe report Rev 2 | — |

**STOP-clause ruling.** No v2-merged scorer is biased in a way that changes a frozen number: the only BIASED scorers either never come within the bias of their decision threshold (`self_detour`) or change eligibility margins without changing any answer (battery v2, `temporal_order` already ruled "not a capability score"). Work continued.

**Recommendation for v3 (not applied).** Battery-v2-style derivations should look GT up at `stamp − clock_offset(run)` with the offset fitted per run from odometry (the probe's `_fit_gt_offset`), not a constant; the temporal_order 0.5 s floor is currently ~0.3–0.5 s looser than registered.

### Decomposing the −0.45 s M1↔GT join offset

`data/logs/vm_runs/costmap_fix/_analysis/clock_decomposition.py`: three per-robot fits on moving samples, each minimising mean position error, with M1's constant position bias (median at rest) removed.

| Run | Robots | GT clock offset (odom vs GT) | Total (fresh M1 vs GT) | M1 latency (fresh M1 vs odom, ROS only) |
|---|---|---|---|---|
| `cp_a_s42` (probe) | 1 | 0.300 | 0.315 | 0.015 |
| `cp_b_s42` (probe) | 1 | 0.300 | 0.335 | 0.035 |
| `cp_a_s43` (probe) | 1 | 0.300 | 0.320 | 0.020 |
| `rot_a_s42` (fix) | 1 | 0.300 | 0.310 | 0.010 |
| `ib10_s42` (fix) | 4 | **0.500** (all four robots, residual < 0.1 mm) | 0.505–0.575 | 0.005–0.075 |
| `ib10_prefix_s42_r4` (pre-fix) | 4 | **0.500** (all four robots) | 0.490–0.585 | −0.010–0.085 |

The same x-crossing estimator that produced −0.45 s (`simtime_shadow_val`, 2-robot) gives 0.451 / 0.454 s there and 0.451 / 0.499 s on the 2- / 4-robot battery-v2 harvests (`_analysis/join_offset_eras.txt`), against 0.35–0.38 s on the single-robot probes. The empirical join offset is therefore the GT clock offset (0.3 s for 1 robot, 0.5 s for 4) plus a few tens of milliseconds of M1 latency; the standing "0.300 + ~0.15 M1" decomposition is wrong in its second term. An analysis that needs GT at a ROS time must fit the offset per run.

---

## Part 1: The Fix

### A′ — `swarm_perception/camera_localizer.py`, `camera_localizer_node.py`

- `odom_lookup_stamp(scene_state, robot_id, latency)` (pure, unit-tested): the robot entry's own `stamp` minus `latency`; the scene stamp only when the entry carries no stamp; None when the robot is absent.
- The node looks odometry up at that time (`lookup_transform` with no wait: the listener shares the node's executor). An extrapolation miss **holds** the previous correction and is counted (`stamped_lookup_failures`); it never falls back to `Time()`, which is the defect. STALE entries still hold in `CameraLocalizer.update`.
- Parameters: `odom_lookup` (`stamped` default; `latest` restores the pre-fix pairing for A/B only) and `m1_latency_compensation_sec` (default 0.01 s, validated to [0, 1)). The launch file passes neither, so the node defaults apply; the launch docstring records the supersession.
- **Why the robot stamp.** In the three probe bags 138–141 of ~850 fast-rotation rows per run were carried forward (`markers_detected: 0`), up to 0.6 s old. Fitting on fresh rows only, the M1 latency is −0.015…0.060 s (median 0.0075 s; `scripts/m1_latency_fit.py`, `_analysis/m1_latency_fit.txt`), and the residual is M1 heading noise (mean 0.025 rad, max ~0.1 rad), not lag. The probe report's "M1 upstream 0.04–0.20 s" came from carried rows.
- **Live health (the fix re-pairs; it does not just hold).** Final localizer counters per robot match the same scenes pre-fix: `updates=5100 holds=0` in both rotation-A seeds' pre-fix probe and `rot_a_s42`, `wp_fwd_s42/43`; IB10 8100–8340 updates per robot (pre-fix 8100–8400); T3c 5640–5700. `stamped_lookup_failures` are 0–18 per robot (the first scene before odometry TF exists, `at stamp≈5.4–6.0`), except two benign cases where a robot's last fresh detection was older than the 10 s TF cache (`extrapolation into the past`, which holds): IB10 robot_1 at spawn (76; its known spawn STALE) and `rot_a_s43`'s undetected park pose (700, all inside the static phase). Every committed `ros2_ws` file md5-equals the deployed one.
- **The default d.** Measured on ROS-clean data only (no GT clock): median 0.0075 s → 0.01 s. Multi-robot ROS-domain fits (IB10, 0.005–0.075 s) agree. The offline sweep shows over-compensation is harmful (d = 0.15 s re-opens 8 / 12 columns with clearing off).

### H — `swarm_simulation/config/nav2_params.yaml`

`local_costmap` and `global_costmap` `obstacle_layer.scan`: `marking: true`, `clearing: true`, `raytrace_max_range: 3.5` (= `obstacle_max_range`). Pinned by three tests in `tests/unit/test_nav2_params_config.py`.

### Tooling and tests

| File | Change |
|---|---|
| `tests/unit/test_camera_localizer.py` | +9: fresh / carried / missing-stamp / absent / unstamped / boolean-stamp / STALE / default-latency, and the carried-pose invariant (fresh and carried rows give the same correction; the pre-fix pairing is off by −ω × age) |
| `tests/unit/test_nav2_params_config.py` | +3: clearing on both costmaps, raytrace ≥ obstacle range |
| `scripts/gt_offset_audit.py` | Part 0 re-derivations |
| `scripts/m1_latency_fit.py` | ROS-domain M1 latency fit (fresh rows when `robot_stamp` is exported) |
| `scripts/vm/costmap_bag_export.py` | scene rows gain `robot_stamp` and `markers_detected` |
| `scripts/costmap_source_analysis.py` | `aprime` localizer replay (imports the node's own `odom_lookup_stamp`) and the latency sweep |
| `scripts/vm/v2_final_run.sh` | `OVERLAY_FILE` (prebuilt orchestrator.yaml, for IB10 / T3c) and `BAG_TOPICS` / `BAG_SEC` |

---

## Part 2: Live Validation

All runs: mock backend, zero API spend, VM `vgu-vgu-thule-base-isaac-workstation-vm`, container `vgu_ros`. Every run passed the `pgrep -f run_simulation`-empty gate (0 s each), `GATE OK: logs saved to present`, M5 started (arrival lines present), and `RESTORE OK` with orchestrator `1f656533…` (source and installed) and rag `e18c723c…`. Bundles: main checkout `data/logs/vm_runs/costmap_fix/`.

### Deploy

- **Pre-fix pristine recorded first.** The VM tree md5-matched `a8fc1bc` on all 742 tracked non-doc files except the pristine `orchestrator.yaml` (`_vm_driver/prefix_source_manifest_a8fc1bc.txt`); the installed `swarm_perception` / `swarm_simulation` trees (170 files) were snapshotted (`_vm_driver/costmap_fix_prefix_installed.txt`). Configs pristine: `1f656533…` / `e18c723c…`.
- **Tooling first** (no runtime effect): `scripts/vm/v2_final_run.sh` and `scripts/vm/costmap_bag_export.py` via `git archive` + `tar -xmf` + `touch`, md5-verified; overlays for IB10 / T3c to `/home/ubuntu/costmap_fix_overlays/`. The pre-fix T3c A/B run (`t3c_prefix_s42`) ran here.
- **Fix** (`_vm_driver/deploy_ros.sh`): the four `ros2_ws` files from the branch tip, `touch`, **both packages' `build/` caches purged and their installed copies removed**, `colcon build --merge-install --packages-select swarm_perception swarm_simulation`, then source == installed md5 for all four (`camera_localizer.py` `3cdc250f…`, `camera_localizer_node.py` `65a9cc2a…`, `nav2_params.yaml` `cbc33745…`, `nav2_robot.launch.py` `9cf43a58…`). `DEPLOY VERIFIED`.
- **Live confirmation.** Every probe run's `params.txt` shows `clearing: True`, `marking: True`, `raytrace_max_range: 3.5`, `obstacle_max_range: 3.5` on both `/robot_1/global_costmap/global_costmap` and `/robot_1/local_costmap/local_costmap` (the `<robot_namespace>` rewrite does not bypass the edit), and the localizer logs `odom_lookup_mode=stamped m1_latency_compensation_sec=0.01`.
- **TF API check** (version-sensitive, CLAUDE.md): in the `vgu_ros` Jazzy container a `tf2_ros.Buffer` lookup at `rclpy.time.Time(nanoseconds=…)` interpolates between stamps (0.05 at the midpoint) and raises `ExtrapolationException` past the newest sample, as the node assumes.

### 1. Rotation probe (the probe's fast-rotation case)

`scripts/vm/costmap_probe.sh`, park A, phases `static:100, rot:1.0:6.283:4, rot:0.3:20.944:4` (identical to `cp_a_s42` / `cp_a_s43`). Max closed columns over **every** recorded grid (`_analysis/max_closed.py`), and the bag replay:

| Run | Static | Fast rot (ω 0.81) | Slow rot (ω 0.15) | Max reg. yaw err, fast (rad) | New aisle cells at fast-rot end | Verdict |
|---|---|---|---|---|---|---|
| `cp_a_s42` (pre-fix) | 0 | **12** | 0 | 0.502 | 178 | — |
| `cp_a_s43` (pre-fix) | 0 | **13** | 0 | 0.431 | 172 | — |
| `rot_a_s42` | 0 | **0** | 0 | 0.083 | 25 | **PASS** |
| `rot_a_s43` | 0 | **0** | 0 | 0.061 | 23 | **PASS** |

Observation: in `rot_a_s43` M1 did not detect robot_1's marker at the park pose for most of the static phase (2,269 STALE rows; the known sub-pixel ArUco-phase dropout at a fixed pose). The localizer held its correction there, as designed. The fast-rotation phase had fresh detections (179 fresh, 64 carried rows), so A′ was exercised.

### 2. Waypoint reroute (`wp_fwd`, the original goal)

`scripts/vm/waypoints_validation.sh`, `loop_map_preemption_probe_baseline` + overlay `loop_permanent`, mock `loop_detour_reroute_once.json`, trigger at M1 x = −1.0, `REC_SEC=600`. Two seeds (no reverse-direction configuration exists).

| Run | WP0 min dist | WP1 min dist | Reroute | Watchdog | Base arrival | GT arrival (t0) | Max closed aisle cols | Verdict |
|---|---|---|---|---|---|---|---|---|
| `wp_fwd_s42` (pre-fix) | 0.054 m | 0.904 m | FAILED | fired | rejected 0.39 m | — | (not recorded) | FAIL |
| `wp_fwd_s43` (pre-fix) | 0.082 m | 0.955 m | FAILED | fired | accepted 0.03 m (after the watchdog) | 90.5 (12.5) | 17 (from sim 18.1) | FAIL |
| `wp_fwd_s42` | 0.074 m | 0.072 m | **COMPLETED** | none | **accepted 0.09 m** | 51.8 (10.8) | **0** / 164 crops | **PASS** |
| `wp_fwd_s43` | 0.068 m | 0.075 m | **COMPLETED** | none | **accepted 0.09 m** | 54.4 (11.9) | **0** / 163 crops | **PASS** |

Both legs were driven (`current_waypoint=0` at sim 21.3 / 24.3, `=1` at 33.6 / 37.2), and robot_1 traversed the second aisle to WP1 and on to the base goal. **The declared reroute through the second aisle now completes end to end.**

### 3. Re-validation batch

All runs on the post-fix VM (installed md5s verified above), driven by `_vm_driver/batch.sh`, which waits for `pgrep -f run_simulation` EMPTY before every run and stops at the first unclean restore (none occurred).

#### 3a. IB10 composite (scripted)

`intersection_bottleneck`, the step-7b / v2-demo IB10 overlay (`_vm_driver/overlays/ib10_orchestrator.yaml`, byte-equivalent to `v2_demo/overlays/ep1_orchestrator.yaml` as parsed), mock `intersection_junction_clear_vlm_verbatim_once.json`, `REC_SEC=1400`, run `ib10_s42` (`20261005_162933`), scored with `coverage_scene_scores.py ib10`:

| Criterion (7b rerun 2) | 7b rerun 2 | `ib10_s42` (fix) | `ib10_prefix_s42_r4` (same-tree pre-fix A/B) |
|---|---|---|---|
| Formed-jam gate | valid, onset 27.1, longest 17.0, 4/4 | valid, onset 34.9, longest 15.4, 4/4 | valid, onset 33.3, longest 15.8, 4/4 |
| chi-pair | pair and order correct, `vlm_verbatim` | pair correct; chi order at the snapshot [robot_3, robot_4] vs proposed [robot_4, robot_3]; `order_equivalent: true` (within the registered 0.15 χ-epsilon, so kept verbatim) | identical: chi [robot_3, robot_4], proposed [robot_4, robot_3], `order_equivalent: true`, verbatim |
| Inside-first | True | True (robot_2 86.2 → robot_3 112.8 → robot_4 129.2 → robot_1 143.1) | True (82.9 → 130.1 → 164.9 → 197.2) |
| Phase reached | resolved, no fallback | resolved, no fallback (recede → cross → release → resolved) | resolved, no fallback |
| Ordered release | True | True (robot_4, robot_1 `clearance`) | True |
| Yielder last (gate log and GT) | True | **True** (gate release 136.5 after robot_4's 122.7) | True (172.3 after 140.0) |
| Arrivals | 4/4 | **4/4** (accepted 0.06–0.09 m) | 4/4 |
| Arrival times after t0 (r2 / r3 / r4 / r1) | 77.1 / 170.8 / 136.3 / 203.0 | 77.2 / 97.8 / 114.1 / 128.4 | 75.5 / 116.8 / 151.4 / 183.9 |
| Tracked band / STALE | in band / max streak 1 row | in band / max streak 5 rows (1.23 s, robot_1) | in band / max streak 19 rows (robot_1) |
| `outcome_rank` | (1, 4, 4) | **(1, 4, 4)** | (1, 4, 4) |

**Verdict: PASS.** The chi-order mismatch is the between-run jam asymmetry the 2026-10-03 plan-grammar ruling registered (`order_equivalent`); the pre-fix v2-demo scripted episode (`ep1_scripted`, 2026-10-03) shows the same chi order [robot_3, robot_4]. **Timing shift (v3 must know).** The same-tree pre-fix run reaches the same outcome and order, but the release-phase transits are about twice as long: robot_3's gate (admit → cleared) 38.2 s pre-fix vs 17.7 s under the fix, robot_4's 32.3 vs 13.8 s, last arrival 183.9 vs 128.4 s after t0. The likely mechanism is H: the receded robots' lidar trails no longer persist as lethal marks in the passers' costmaps (the 7b report's "lead paused ~20 sim-s before passing"). Getting the pre-fix A/B took four attempts on the restored VM: three aborted at Nav2 bring-up (twice robot_2 `Aborting bringup` after a 4 s bond timeout, once a `change_state` response timeout under load average ~17); each abort's lingering Isaac was killed by PID, its restore verified (`RESTORE OK`), and the bundle kept as `*_ABORTED_*`. None of the aborted attempts counts; their `GATE OK` lines are the known cleanup-path false positive.

#### 3b. Free-flow spot checks

`free_flow_run.sh` (solo-in-space), variant USDs rebuilt for the check and removed afterwards, `free_flow_table.py derive` (GT only):

| Variant | `free_flow_v1` | Fix | Δ | Verdict |
|---|---|---|---|---|
| head-on `_bshort` r1 | 25.0 | 25.0 | 0.0 | PASS |
| B1 `bottleneck_merge` r2 (turning route) | 18.1 | 17.3 | −0.8 | PASS |
| IB10 r1 | 20.9 | 21.0 | +0.1 | PASS |

#### 3c. Loop pre-emption re-smoke

`loop_preemption_probe.sh baseline` / `blocker` (phase-1 driver, positive control, plan sampler), scored by `_analysis/loop_smoke.py`; the phase-1 bundles re-scored with the same tool for the reference column:

| Run | GT max \|y\| | Plans entering the second aisle | Blocker / gap cost (global) | Positive control | Dispatches | Arrival after t0 | Verdict |
|---|---|---|---|---|---|---|---|
| baseline, phase 1 | 0.030 | 0 / 968 | — | SUCCEEDED | 0 | 28.9 | — |
| blocker, phase 1 | 0.224 | 0 / 194 | 99 / 99 | SUCCEEDED | 0 | 29.2 | — |
| baseline, fix | 0.010 | 0 / 1161 | — | SUCCEEDED | 0 | 28.8 | **PASS** |
| blocker, fix | 0.206 | 0 / 388 | 99 / 99 | SUCCEEDED | 0 | 29.4 | **PASS** |

No self-detour with the sub-lethal blocker. Clearing does not weaken the blocker's marking: the narrowed gap stays at cost 99 (inscribed, not lethal) exactly as in phase 1.

#### 3d. T3c — see the next section.

---

## T3c Timing Shift (H-specific risk)

`dynamic_anomaly_v2` (pallet_1 spawns at 30.0 and is removed at 110.0, Isaac/GT clock), normal-flow lanes, mock default (no dispatch), seed 42, `REC_SEC=750`. A same-tree pre-fix run was added (`t3c_prefix_s42`, before the deploy) so the shift is attributable to the fix; the frozen expectation is the 2026-09-27 V1 smoke (gemini, all calls HTTP 429, so also dispatch-free). Measured by `_analysis/t3c_timing.py` from GT:

| Quantity | Frozen V1 (09-27) | Pre-fix (`t3c_prefix_s42`) | Fix (`t3c_fix_s42`) | Shift (fix − pre-fix) |
|---|---|---|---|---|
| robot_1 stall (sim, x) | 30.6, −0.08 | 30.8, 0.09 | 30.8, 0.40 | stalls 0.31 m nearer the pallet |
| robot_1 x at removal (110.0) | 0.04 | 0.50 | 0.73 | — |
| Resume after removal | +2.3 s | +2.6 s | +4.9 s | +2.3 s |
| Post-resume pause ≥ 3 s | 18.4 s at x 1.13 | 17.0 s at x 1.15 | **none** | **−17.0 s** |
| robot_1 arrival after removal | +35.1 s | +32.0 s | **+13.6 s** | **−18.4 s** |
| robot_1 / robot_2 GT arrival | 145.1 / 45.4 | 142.0 / 44.6 | 123.6 / 42.6 | −18.4 / −2.0 |
| nav2_r1: create-plan failures / progress failures / clears / goal failed | 84 / 1 / 68 / 5 | 88 / 1 / 72 / 5 | 73 / 0 / 59 / 4 | — |
| M5 analyses / dispatches | 15 / 0 | 16 / 0 | 13 / 0 | — |

**What changed and why.** The V1 summary's own hypothesis for the 120–138 pause was "stale local-costmap marks of the removed box until the progress-checker abort/recovery cleared them". With `clearing: true` those marks are raytraced away by the next scans through the vacated space, so the pause vanishes and the post-removal transit shrinks from ~32 s to ~14 s (≈ 2.1 m at 0.15 m/s). The window itself behaves the same: the pallet is present and lethal, planning fails throughout it, the stall triggers M5. **Implication for v3:** any T3c (and `loop_detour_transient`, `blocked_path_transient`) number frozen under v2 encodes the never-clearing costmap; a transient blocker's "cost after removal" is ~18 s smaller under the fix, and the expected_conflict window ([30, 50], min 12 s) is unaffected.

---

## Parked Status

`feat/v3-costmap-fix` stays local and unmerged. Per the spec ruling, v2 and v1 run as-is: no v2 scored cell exercises the defect, and the v2 frozen results are internally consistent under pre-fix behaviour. v3 inherits this branch with its re-validation evidence; the timing shifts recorded here (IB10, T3c) are what any v3 comparison against v2 numbers must account for.

---

## Verification

- **Local suite.** `pytest -q --continue-on-collection-errors -p no:cacheprovider -rfE`, one venv (main checkout `.venv`). Clean detached worktree at `a8fc1bc` (removed afterwards): 63 failed / 5117 passed / 153 skipped / 3 errors. Branch: 63 failed / 5129 passed / 153 skipped / 3 errors. The failing and erroring name sets are identical (66 = 66, `diff` empty); +12 passes are the new tests. `ruff check` clean on every new or changed Python file.
- **Per run** (all 13 counted runs): `pgrep -f run_simulation` EMPTY before launch (0 s waits); `GATE OK: logs saved to present` (or, for the loop driver, its `logs saved to` line plus `restore verified: all copies pristine`); M5 started (arrival / analysis lines); `RESTORE OK` with orchestrator `1f656533…` in source AND installed and rag `e18c723c…`. No run dispatched an API call (`BACKEND_ID=mock`).
- **GT-offset trap** respected in every analysis here: GT-only quantities stay on the GT clock; ROS-vs-GT comparisons use the per-run fitted offset (`clock_decomposition.py`), never a constant.
- **Counted runs:** `t3c_prefix_s42` (`20261005_151856`), `rot_a_s42` (`153401`), `rot_a_s43` (`155059`), `wp_fwd_s42` (`160710`), `wp_fwd_s43` (`161821`), `ib10_s42` (`162933`), free-flow head-on r1 (`165509`), B1 r2 (`170023`), IB10 r1 (`170537`), loop `baseline_20261005_171051`, `blocker_20261005_171902`, `t3c_fix_s42` (`172712`), `ib10_prefix_s42_r4` (post-restore, pre-fix A/B). Aborted, not counted: `ib10_prefix_s42_ABORTED_nav2_r2_bringup`, `ib10_prefix_s42_r2_ABORTED_nav2_r2_bringup`, `ib10_prefix_s42_r3_ABORTED_nav2_lifecycle_timeout`.

---

## References

- Contract: `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (main checkout), "SOURCE ATTRIBUTED + FIX RULED (2026-10-05)".
- `docs/reports/2026-10-05-costmap-source-probe.md` (Rev 2); `docs/reports/2026-10-05-follow-waypoints-validation.md` (Rev 2); `docs/reports/2026-10-03-step7b-oracle-freeze.md` (IB10 rerun-2 criteria); `docs/reports/2026-10-05-free-flow-table.md`; `docs/reports/2026-10-02-loop-preemption-smoke.md`; T3c smoke `data/logs/vm_runs/t3c_v2/T3C_V2_SUMMARY.txt`.
- Run bundles and analysis: main checkout `data/logs/vm_runs/costmap_fix/` (`rotation/`, `waypoints/`, `ib10_s42/`, `free_flow/`, `loop/`, `t3c_prefix_s42/`, `t3c_fix_s42/`, `_analysis/`, `_vm_driver/`).

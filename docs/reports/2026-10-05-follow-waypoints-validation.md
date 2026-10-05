# M4 follow_waypoints: Diagnosis and Live Validation of the Declared Reroute

**Prepared:** 2026-10-05

**Revision history:**

- Initial draft: diagnosis of the `perm_reroute_s42` stall, the M4 waypoint-progress logging change, two blocker-free validation runs (both FAIL, same shared root cause), one head-on regression run (PASS), and a STOP on the fix, which needs a change to a shared component.
- Rev 2 (same day, review pass): the first aisle closure came with ≤ 0.06 rad of map→odom yaw error, so the localizer is restated as a demonstrated contributor, not the sole phantom source. Also: the option ranking now favours C, the (d) wording is no longer a message-pairing claim, and the watchdog interval and leg count are corrected.

---

## Summary

Branch `feat/v2-waypoints`, cut from `feat/prereg-v2-composite` at `fb54ebb`.

| Item | Outcome |
|---|---|
| `follow_waypoints` plumbing (M3 grounding → M4 → waypoint follower → bt_navigator) | **Works.** Five live legs were exercised: the original run's leg 0, plus legs 0 and 1 in each validation run. Every leg was accepted, forwarded and planned. In both validation runs waypoint 0 was reached, 0.054 m and 0.082 m from the declared pose. Hypotheses (a)–(e) are all refuted (table below). |
| Root cause of "reroute is a no-op" | **Shared, upstream of M4.** Phantom lethal cells fill the 0.55 m second aisle in the shared *global* costmap. These are cells free in the static map with nothing physically there, marked at 2–3.3 m range. The planner cannot reach the declared waypoint 1 (`Failed to create plan`), falls back to a 0.5 m-tolerance plan, and drives the robot into the remnant corner at the aisle mouth. There DWB settles on a near-zero twist and the robot stays wedged until M4's 120 s watchdog fires. This chain is directly evidenced. **The phantom source is partly established:**<br>• *Demonstrated contributor:* the camera localizer (`swarm_perception/camera_localizer_node.py`) pairs a 0.3–0.45 s old M1 pose with the *latest* odometry. That injects up to 0.6 rad of yaw error into `map -> robot_1/odom` during in-place rotations; it is also the dominant correlate of the closures after WP0.<br>• *Not explained by it:* the first closure (sim 18.1 s) came with at most 0.06 rad of map→odom yaw error. A second phantom source is not excluded, for example low or ground returns from chassis pitch or lidar beam spread on grazing far-wall hits. |
| Fix | **STOP (not applied).** Every candidate fix touches a shared component (the localizer, global-costmap or DWB parameters) or is a scene-scoped Nav2 overlay that needs a protocol ruling. The blast-radius analysis is below. |
| M4 code change landed | Log-only: `send_waypoints` now logs each change of `current_waypoint` (`36d26de`). The plain NavigateToPose path is byte-identical (pinned). |
| Validation run 1, `wp_fwd_s42` | **FAIL.** WP0 reached; leg 1 was never driven; watchdog kill at 120.5 wall-s; base arrival rejected (0.39 m > 0.35 m). |
| Validation run 2, `wp_fwd_s43` (replication) | **FAIL**, same signature. Watchdog kill at 121.4 wall-s. The base mission later arrived (0.03 m, accepted). Costmap evidence captured: the aisle was closed from sim 18 s on. |
| Regression run, `reg_pv_r1_s42` (head-on yield) | **PASS.** The command flow is identical to the known-good `pv_r1_s42`. 2/2 arrivals accepted, 0 contacts, 0 STALE. |
| STALE | 0 STALE rows on every robot in all three runs. |
| Suite | Baseline `fb54ebb` and branch run on the same venv: 63 failed / 153 skipped / 3 errors in both. Passed: 5111 at baseline, 5115 on the branch (+4 new pins). The failing-name sets are identical. |
| VM | Idle: `pgrep` empty, GPU 0 % / 171 MiB. Configs are pristine in source and installed (`1f656533…` / `e18c723c…`). The tree equals the branch tip `46492d6` except the pristine `orchestrator.yaml`. |

---

## Diagnosis of the original failure (`perm_reroute_s42`)

Evidence: `data/logs/vm_runs/waypoints_validation/_source_perm_reroute_s42/` (a copy of the VM bundle `loop_family/perm_reroute_s42`, without images).

**The robot was wedged before the reroute existed.** The GT trajectory (`gt/ground_truth.jsonl`) shows robot_1 on Nav2's own self-detour. At sim 31.3 s it is at (0.29, 0.92) heading −0.08 rad. It then turns clockwise to −1.29 rad, and from sim 33.4 s it is frozen at (0.314, 0.899) to the millimetre. M5 triggered on "1 robot(s) stalled >= 12.0s" and dispatched `reroute` at sim 36.3 s, into a robot that was already stuck. The "0.3 m short of waypoint 1" in the earlier report is only the distance from that frozen pose to (0.30, 1.20). The robot never moved toward the waypoint at all.

**The waypoint path ran correctly up to the controller.** `nav2_r1.log`:

1. The follower logged `Received follow waypoint request with 2 waypoints`.
2. bt_navigator logged `Begin navigating from current location (0.31, 0.91) to (0.30, 1.20)`.
3. The sampler recorded an 11-pose plan ending at (0.3, 1.2).
4. The controller logged `Passing new path` at 1 Hz, then `Failed to make progress` twice, until the watchdog cancel.

The same wedge occurs under plain NavigateToPose in both sibling runs:

- `perm_wait_s42`: frozen at (0.104, 0.934) from sim 30 s, wedged more than 150 s overall.
- `diag_costmap_s42`: frozen at (0.415, 0.991) for 18 sim-s, then recovered.

| Hypothesis | Verdict | Evidence |
|---|---|---|
| (a) Waypoint acceptance tolerance tighter than DWB's stopping error | Refuted | The follower forwards each waypoint as a NavigateToPose goal and uses the same goal checker (0.1 m). The robot moved 0 m. In both validation runs WP0 was accepted at 0.054 / 0.082 m. |
| (b) Jazzy int/float parameter trap in `waypoint_follower` | Refuted | `nav2_params.yaml` passes only `use_sim_time`. The node configured and activated, and logged `Waypoint pause duration is set to zero, disabling task executor plugin`. |
| (c) Watchdog measuring progress against the final goal | Refuted | `CommandBusNode._arm_nav_watchdog` is a pure monotonic deadline of max(3 × 20 s, 120 s) = 120 s from ACTIVE; it never measures progress. It fired at 121.3 / 120.5 / 121.4 wall-s after ACTIVE (original / run 1 / run 2), which is correct given zero motion. |
| (d) Stop/pause at waypoint vs the collision monitor's `stop_pub_timeout` | Refuted | The pause executor is disabled. The collision monitor never logged `Robot to stop due to forward_stop polygon` in any of the three runs, and that string is in the installed `libcollision_monitor_core.so`. Nonzero commands pass through: in the wedge windows the probe recorded equal sample counts on both topics (456 / 443), and only 2 / 6 `cmd_vel` zeros fall within 0.1 s of a nonzero `cmd_vel_nav`. The probe's Python receive stamps are jittered by its `/tf` load, so this is not a strict message-by-message pairing. Either way, DWB's own output was already near zero (below). |
| (e) Wrong frame or unreachable waypoint from M3 | Refuted as an M3 defect | The waypoints are in the `map` frame, and (0.3, 1.2) and (1.8, 1.2) are free in the static map. WP1 became unreachable only through the dynamic costmap (below). |

---

## Root cause (shared): phantom global-costmap marks close the second aisle

**1. The yaw error, and why it scales with turn rate.** `CameraLocalizerNode._lookup_odom_pose` uses `Time()`, the latest odom, by design: its comment dates from when camera stamps were system time. M1's heading lags the true heading by 0.3–0.45 s. So `map -> odom` absorbs `−ω × lag`, plus M1 heading noise. Measured as M1 θ − GT θ against GT ω (`_analysis/lag.py`; every rotating sample has the sign opposite to ω):

| Run | Max \|M1 θ − GT θ\| | Typical implied lag | Where |
|---|---|---|---|
| `perm_reroute_s42` | 0.594 rad (ω −1.33) | 0.36–0.45 s | aisle mouth, (0.3–0.45, 0.8–0.9) |
| `perm_wait_s42` | 0.592 rad | 0.27–0.43 s | aisle mouth |
| `diag_costmap_s42` | 0.245 rad (ω −0.63) | 0.39 s | aisle mouth, at the start of its 18 s freeze |
| `wp_fwd_s42` | 0.592 rad (ω −1.24) | 0.34–0.48 s | WP0, during the rotation to waypoint yaw 0 |

The probe recorded the published TF directly. In `wp_fwd_s42`, `map -> robot_1/odom` yaw was 0.000 before motion, at most 0.117 rad over sim 10–22 s, and 0.168 / 0.326 / 0.592 rad at sim 35.07 / 35.33 / 37.63 s. That is the rotate-to-goal at WP0.

**2. Phantom marks fill the aisle.** The probe for run 2 added a full-grid plus incremental-update crop of `/robot_1/global_costmap/costmap`. It covered x ∈ [0.4, 2.1], y ∈ [0.6, 1.5], and the "closed" metric counts aisle columns (x 0.65–1.5) whose cheapest cell across the aisle is ≥ 99. The prediction, registered before the run, was that free aisle cells read ≥ 99 within seconds of a map→odom yaw spike of ≥ 0.15 rad. In `wp_fwd_s43`:

| sim (s) | Closed columns / 17 | Max \|map→odom yaw\|, prior 3 s | Robot |
|---|---|---|---|
| 8.0 (first full grid) | 0 (bottleneck 0) | 0.000 | spawn |
| 18.07 | 5 (first closure) | **0.060** | (−1.54, 0.00), primary aisle |
| 19.20 | 8 | 0.060 | (−1.38, −0.01) |
| 20.20 | 8 | 0.194 (spike at 19.67, after the first closure) | (−1.23, −0.02) |
| 24.43 | 15 | 0.149 | turning toward WP0 |
| 34.20 | 16 (every aisle and connector cell lethal) | 0.044 | at WP0 |
| 38.53 | 0 (bottleneck 80; raytraced open) | 0.436 | rotating at WP0 |
| 39.60 | 13 | 0.466 | turning south |
| 76.83 | 0 (after recovery cleared the costmap) | 0.017 | wedge |
| 77.97 / 79.03 | 2 / 4 | 0.008 / 0.155 | leaving the wedge |

**The prediction fails for the first closure.** The aisle first closed at sim 18.07 s (5 columns) and reached 8 columns by 19.2 s. Over the 3 s before each, the map→odom yaw error was at most 0.06 rad; the 0.194 rad spike came at 19.67 s, after both. The new lethal cells at 18.07 s:

- form a filled blob over x ≈ 0.95–1.6 and y ≈ 0.98–1.43, plus the junction cells west of the remnant;
- lie 2.07–3.28 m from the robot;
- are not a thin rotated wall segment or a single fixed-range arc, so their shape does not discriminate the two candidate sources.

At 3 m range, 0.06 rad displaces a return by 0.18 m. That is about half of the 0.39 m inscribed-free band, so accumulated small jitter could contribute, but this is not shown. A second phantom source is therefore **not excluded**: low or ground returns from chassis pitch, or RTX beam spread on grazing hits against the far 0.9 m aisle wall.

The prediction does hold for the later, larger events:

- the rotation spikes at 37.5–39.6 s re-closed the aisle after a raytrace had reopened it (38.53 s, bottleneck 80);
- after the recovery cleared the costmap at 76.8 s, the 79.03 s closure followed a 0.152 rad spike;
- the small 2-column closure at 77.97 s is not explained.

Renders of the crop are in `probe.jsonl` (`kind: costmap_crop`). At sim 34.2 s the aisle is solid lethal from x 0.55 to 2.05 in the band that is free in the static map.

**3. The planner substitutes a tolerance goal, and the robot wedges.** Leg 1 starts at sim 35.0 / 35.8 s. About 1.5–2 s later the planner logs `GridBased plugin failed to plan from (0.28, 1.15) to (1.80, 1.20): "Failed to create plan with tolerance of: 0.500000"` (run 1, sim 36.5 s; run 2, sim 37.8 s). It then serves plans ending at (1.75, 1.0), (1.7, 0.95) and (1.6, 0.8): connector cells within 0.5 m of WP1, reached via the primary aisle. The robot turns south into the remnant corner, where the controller finds 219–419 valid trajectories but chooses vx 0–0.0095, wz ±0.079 for about 35 s. That is the smallest rotation sample, and the robot does not physically turn at that rate (`evaluation` rows). This DWB local minimum is a **secondary shared finding** that is not chased here. A *new* goal frees it at once: the base-mission resend at sim 79 in both runs. The progress-checker aborts do not.

---

## The change that landed (M4, log-only)

`ros2_ws/src/swarm_execution/swarm_execution/nav2_adapter.py` (`36d26de`):

- `send_waypoints` passes a `feedback_callback` to `send_goal_async`.
- `_on_waypoint_feedback` logs `waypoint leg progress robot=<id> current_waypoint=<k> of=<n> target=(x, y) sim_t=<s>` once per change of index.

**Protocol note (M4):**

- **Additive and log-only.** No status, timing, cancel or watchdog behaviour changes.
- **The plain NavigateToPose path is byte-identical.** `send_goal` still calls `send_goal_async(goal_msg)` with no keyword arguments, pinned by `test_send_goal_passes_no_feedback_callback`.
- **New pins** in `tests/unit/test_nav2_adapter.py`, four in total:
  - one log line per leg change;
  - a progress reset per route;
  - an out-of-range index logged without a target;
  - the `send_goal` no-kwargs pin above.
- **Live confirmation.** The regression run's `m4.log` has 0 `waypoint leg` lines. Its M4 command and status sequence matches `pv_r1_s42` line for line.

**Tooling (v2-only, VM):**

- `scripts/vm/waypoints_validation.sh` wraps `v2_final_run.sh`, which keeps every standing trap.
- `scripts/vm/waypoint_probe.py` fires one manual trigger at M1 x ≥ `TRIGGER_X` on `/orchestrator/trigger_analysis`. A blocker-free map gives M5's stall detector nothing to fire on. The probe also records `cmd_vel_nav`, `cmd_vel`, odom, `map -> odom`, DWB `evaluation`, follower feedback and status, and the costmap crop.
- Commits: `84fc339`, `46492d6`.

**Blast radius of the landed change:** none outside `follow_waypoints`, the only caller of `send_waypoints`. No shared Nav2 parameter, no M3 change, and no scenario or USD change were made.

---

## Validation runs

Common setup for both runs:

- Scenario `loop_map_preemption_probe_baseline`: the validated-navigable loop map with no blocker. Its USD was used unchanged, with no yaml edit.
- `OVERLAY=loop_permanent`: robot_1 goal (2.3, 0), `reroute_waypoints [[0.3, 1.2], [1.8, 1.2]]`.
- Mock `loop_detour_reroute_once.json`; the M3 grounding mode is the shipped `derived`.
- `TRIGGER_X=-1.0`, `REC_SEC=600`.

The M3 grounding of the declared detour was confirmed live: the follower received 2 waypoints and its first leg went to (0.30, 1.20).

**Run 1, `wp_fwd_s42` (seed 42, stamp `20261005_120558`).** All times are sim seconds unless marked wall.

| Event | Time | Evidence |
|---|---|---|
| Manual trigger at M1 x = −0.999 (MOVING); accepted | 22.2 | `probe.jsonl` `trigger_sent` / `trigger_response` |
| Reroute ACTIVE; leg 0 → (0.30, 1.20) | 22.4 / 22.5 | `m4.log` |
| WP0 reached: GT (0.263, 1.152), 0.054 m at closest approach | 33.0–35.2 | GT |
| Rotation to waypoint yaw 0 (wz to −1.03); map→odom yaw spike 0.168 → 0.326 rad | 34–35.3 | probe |
| Leg 1 → (1.80, 1.20) | 35.0 | `m4.log` `current_waypoint=1` |
| Planner fails to (1.80, 1.20), switches to tolerance plans | 36.5 | `nav2_r1.log`, `sampler.jsonl` |
| Turned south and wedged at (0.31, 0.94), then (0.35, 0.77) | 40–79 | GT |
| Progress aborts | 55.0, 75.1 | `nav2_r1.log` |
| Watchdog FAILED; base mission resumed | 79.0 (120.5 wall-s after ACTIVE) | `m4.log` |
| Nav2 "goal reached" at (2.083, 0.291), a tolerance-substituted endpoint; **M5 arrival rejected**, 0.39 m > 0.35 m | 92.1 | `m5.log` |

Closest GT approach to WP1 (1.8, 1.2) was 0.904 m. Leg 1 was never driven. No latch fired: there is one robot and no safety hold. There were 0 contacts.

**Run 2, `wp_fwd_s43` (seed 43, stamp `20261005_122227`; replication with costmap capture).**

| Event | Time | Evidence |
|---|---|---|
| Aisle first closes in the global costmap (robot in the primary aisle) | 18.07 | probe `costmap_crop` |
| Manual trigger at M1 x = −0.989; accepted | 22.6 | probe |
| Reroute ACTIVE; leg 0 → (0.30, 1.20) | 22.8 / 22.9 | `m4.log` |
| WP0 reached: GT (0.263, 1.126), 0.082 m | 34–36 | GT |
| Leg 1 → (1.80, 1.20) | 35.8 | `m4.log` |
| Planner fails to (1.80, 1.20) | 37.8 | `nav2_r1.log` |
| Wedged at (0.312, 0.750) | 42–76 | GT |
| Progress aborts | 55.9, 75.9 | `nav2_r1.log` |
| Watchdog FAILED; base mission resumed | 78.9 (121.4 wall-s after ACTIVE) | `m4.log` |
| Base goal reached; **M5 arrival accepted**, 0.03 m | 95.0 | `m5.log` |

Closest GT approach to WP1 was 0.955 m. There were 0 contacts.

**Verdict:** both runs FAIL the PASS bar. In each, leg 1 was never traversed and the watchdog killed the route; run 1 also had no position-verified arrival.

**Watchdog margin:** leg 0 took 12.5 sim-s, about 26 wall-s. The full declared route from x = −1.0 is about 3.3 m, which is roughly 60 wall-s at this run's real-time factor. A healthy run would therefore fit the 120 s deadline with about 2× margin.

---

## Regression run: head-on yield (`reg_pv_r1_s42`)

`priority_visual_r1`, pristine config (`OVERLAY=none`), mock `priority_visual_r1_yield_once.json`, seed 42, no probe (`PROBE=0`), stamp `20261005_123449`. It is compared with the known-good `visual_pass/pv_r1_s42` (`20261003_045905`, same driver and conditions).

| Check | `pv_r1_s42` (known good) | `reg_pv_r1_s42` (this tree) |
|---|---|---|
| First analysis | robot_2 stalled, d = 2.62 | robot_2 stalled, d = 2.60 |
| Decision / grounding | `yield` robot_2, derived, terminal ok | identical |
| M4 command/status sequence (ids masked) | yield(robot_2) ACTIVE, temporary_wait(robot_1) ACTIVE, robot_2 ACTIVE ×2, COMPLETED robot_2, COMPLETED robot_1 | identical, line for line |
| Re-analyses after resolution | 4 (robot_2) | 4 (robot_2) |
| Arrivals (M5 position check) | robot_1 0.06 m, robot_2 0.08 m, both within tolerance | robot_1 0.05 m, robot_2 0.08 m, both within tolerance |
| GT within 0.15 m of goal | robot_1 85.0 s, robot_2 131.6 s | robot_1 86.4 s, robot_2 134.1 s |
| Contacts (robot-robot / static) | 0 / 0 | 0 / 0 |
| `waypoint leg` lines in `m4.log` | 0 | 0 |
| STALE rows | 0 / 0 | 0 / 0 |

**PASS:** the ordinary path is unchanged.

---

## STALE instrumentation

From `m5_scene.jsonl` (`_analysis/stale.py`):

| Run | Rows (robot_1 / robot_2) | STALE rows | Max STALE streak |
|---|---|---|---|
| `wp_fwd_s42` | 345 / — | 0 | 0 |
| `wp_fwd_s43` | 338 / — | 0 | 0 |
| `reg_pv_r1_s42` | 432 / 432 | 0 | 0 |

That includes the 35–40 s stationary wedge dwells. No STALE flag was raised.

---

## Fix options and blast radius (STOP: none applied)

Every scene launched by `fc_launch.sh` runs `nav2_robot.launch.py localization:=camera` with one shared `nav2_params.yaml`. Every validated and frozen result therefore depends on the current localizer and costmap behaviour, including:

- the v1 head-on family;
- T1 / T2b / T3a / T3b / T3c;
- B2 / B3;
- the composite and junction scenes;
- the `free_flow_v1` table frozen today.

| Option | Scope | Blast radius | Expected effect |
|---|---|---|---|
| A. Localizer: look up odom at the M1 scene stamp (TF buffer) instead of `Time()` | M1 shared node | **Every scene, every robot.** It changes `map -> odom` and so global-costmap registration and global plans everywhere. Every frozen table and validated scene would need re-validation. | Removes the lag term (the 0.3–0.6 rad rotation spikes). Leaves M1 heading noise (≤ 0.2 rad observed while driving straight). |
| B. Localizer: low-pass or rate-limit the yaw correction, or hold during fast rotation | M1 shared node | Same as A | Bounds both lag and noise. Slower to correct a real bias. |
| C. Global costmap obstacle layer: shorter `obstacle_max_range` / `raytrace_max_range`, or obstacle layer off in the global costmap | Shared Nav2 parameter | Every scene's global planning, including the T3a/T3b blockers that rely on global obstacle marks | Removes long-range phantoms: 0.2 rad at 3 m is 0.6 m of displacement, while 0.2 rad at 1 m is 0.2 m. |
| D. Lower DWB `max_vel_theta` (1.5 rad/s) or the RotateToGoal speed | Shared Nav2 parameter | Every Nav2-driven motion and its timing, including the free-flow speeds and the arrival rotations | Shrinks only the rotation term. The straight-driving closure at sim 18 s in run 2 remains. |
| E. Scene-scoped Nav2 params for the loop family only (C or D applied via a per-scenario params file) | fc_launch / launch plumbing, default-off | No other scene, but the loop family would run a different Nav2 configuration from every other family | A protocol call. The loop-family numbers would not be comparable to the rest. |
| F. M4: waypoint yaw = bearing to the next waypoint, or `navigate_through_poses` instead of `follow_waypoints` | M4, `follow_waypoints` only | None beyond reroute | Moves or softens the stop-and-rotate at WP0, but the error scales with ω and the turn into the aisle is required. Run 2's aisle was already closed at sim 18 s, before any waypoint rotation, so **F cannot fix this alone**. It is listed as a candidate aggravator fix, not applied. |
| G. Waypoint geometry (for example, WP0 moved into the junction) | M3 / overlay | None beyond reroute | Not attempted. The localizer term scales with ω, not with where the turn happens, so this only moves the spike. The first closure happened in the primary aisle before any reroute. A pass would hide the defect, not fix it. |

**Ranking.** C is the only option that covers both candidate phantom sources, because it bounds how far any long-range return can be misplaced. A and B remove only the localizer term, which is demonstrated for the rotation spikes but does not explain the first closure. D shrinks only the rotation term.

**Decision needed.** The coordinator must choose between a shared change (C, possibly with A), which means re-validating the frozen scenes, and scoping the loop family's Nav2 (E). A cheap way to settle the open source question before choosing is a static-robot probe, with no rotation and no motion, that watches the second-aisle crop. Also add a full-grid dump to separate arcs from rotated walls. Also flagged:

- **DWB corner local minimum.** Near-zero twist with hundreds of valid trajectories; only a new goal frees it.
- **The M5 arrival gate correctly caught a tolerance-substituted Nav2 "success".** In run 1, Nav2 reported success at 0.39 m.

---

## Verification

- **Local suite.** `pytest -q --continue-on-collection-errors -p no:cacheprovider`, one venv, run on a clean detached worktree at `fb54ebb` and on the branch. 63 failed / 153 skipped / 3 errors on both; 5111 → 5115 passed. The failing-name sets are identical (`diff` empty). The +4 are the new `test_nav2_adapter.py` pins.
- **Deploy.**
  - `git archive` of the branch tip was extracted with `tar -xzmf` into `/home/ubuntu/vgu-vlm-swarm`.
  - The pristine `orchestrator.yaml` and `rag.yaml` were restored from verbatim backups, with `touch`.
  - The md5 manifest (826 files) matches everywhere except the pristine `orchestrator.yaml`. No VM-only Python modules exist under `ros2_ws/src`, `reasoning` or `scripts`.
  - `colcon build --merge-install` covered swarm_interfaces, swarm_perception, swarm_execution, swarm_orchestrator and swarm_simulation.
  - The installed `nav2_adapter.py` md5 equals the source (`81b1574f…`), and an import smoke ran inside the container.
- **Per run.** Each run passed:
  - the `pgrep -f run_simulation`-empty gate (0 s wait each time; the previous Isaac had exited);
  - `GATE OK: logs saved to present`;
  - M5 confirmed started (dispatch and analysis lines in `m5.log`);
  - `RESTORE OK`, with source and installed `orchestrator.yaml` at `1f656533…` and `rag.yaml` at `e18c723c…`.

  Run 1 moved an older leftover ground-truth directory aside (`_rescued_loop_map_preemption_probe_baseline-seed42-rep000_1791201958`), as the driver is designed to.
- **VM at close-out (12:50 UTC).** `pgrep` for Isaac/run_simulation is empty and the GPU is at 0 % / 171 MiB. The VM is left running and idle, as found.

---

## References

- Original failure: `docs/reports/2026-10-03-loop-family-and-visual-pass.md` (Part A, `perm_reroute_s42`).
- Run bundles: `data/logs/vm_runs/waypoints_validation/{wp_fwd_s42,wp_fwd_s43,reg_pv_r1_s42}/`. The source bundle copy is in `_source_perm_reroute_s42/`, and the analysis scripts are in `_analysis/`.
- Known-good regression baseline: VM `data/logs/vm_runs/visual_pass/pv_r1_s42/`.
- Code: `ros2_ws/src/swarm_execution/swarm_execution/nav2_adapter.py`, `ros2_ws/src/swarm_perception/swarm_perception/camera_localizer_node.py` (`_lookup_odom_pose`), `ros2_ws/src/swarm_simulation/config/nav2_params.yaml`.
- Tooling: `scripts/vm/waypoints_validation.sh`, `scripts/vm/waypoint_probe.py`.

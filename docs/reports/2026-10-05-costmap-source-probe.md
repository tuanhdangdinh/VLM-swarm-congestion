# Costmap Source Probe: What Marks the Loop Map's Second Aisle Lethal

**Prepared:** 2026-10-05

**Revision history:**

- Initial draft: source attribution for the phantom lethal cells that close the 0.55 m second aisle in the shared global costmap. Covers the obstacle-layer configuration finding, a geometry forward model of run 2's first closure, three VM probe runs (static plus two rotation rates, two park poses, one replication), a bag-replay attribution, and the fix recommendation matrix. Diagnosis only: no fix applied.

---

## Summary

Branch `feat/v2-costmap-probe`, cut from `feat/prereg-v2-composite` at `62c01ac`. It follows `docs/reports/2026-10-05-follow-waypoints-validation.md` (Rev 2), referred to below as "the waypoints report".

| Item | Outcome |
|---|---|
| **Attribution** | **One error source plus one amplifier, on top of a fixed, non-closing geometry narrowing.**<br>• **Source: camera-localizer lag registration.** `map -> robot_1/odom` carries `−ω × L`, with L fitted at 0.43–0.60 s. Every lidar return is rotated by that error about the robot before marking.<br>• **Amplifier: the obstacle layer never clears.** `clearing` is `false` in both costmaps (the Jazzy default; `nav2_params.yaml` never sets it; verified live). Each mis-registered return is therefore permanent until a ClearEntireCostmap.<br>• **Geometry:** legitimate returns from the north wall (y = 1.475) and the 0.3 m remnant's north face (y = 0.925) land in half-cells the static map leaves free. RTX range-noise tails, integrated over about 1000 scans, add one more row. Together these narrow the aisle by about one row per side but **never closed a column**: 0 / 17 in every static phase and in the zero-error forward model. |
| Run 2's "unexplained" first closure (sim 18.07 s) | **Explained by the localizer term.** The waypoints report's "≤ 0.06 rad" came from a probe whose rows ran about 2 s behind their content and caught about 20 % of the `map -> odom` publishes. The content-stamped M1−GT heading error was −0.146 rad at sim 17.07. A GT-driven forward model (lag 0.48 s, plus the 0.3 s future-stamp delay) reproduces the closure at the same costmap update: 7 columns predicted vs 5 observed, 72 new cells vs 71. The error comes from DWB's ±0.1 rad weave while "driving straight" (GT ω up to 0.37 rad/s). Geometry alone predicts 0 columns. |
| Static-robot probe (the decider) | **No closure in 280 stationary sim-s** across 3 runs and 2 park poses. The marks that do accumulate are 71–87 % GT-registered real returns, plus 8–30 cells of M1 heading flicker (max 0.03–0.12 rad). |
| Rotation probe | **Closure tracks ω × L.** One commanded 1.0 rad/s turn (actual 0.78 rad/s; max yaw error 0.64–0.75 rad) closes **12 / 6 / 13 columns within 2–4 sim-s**. A commanded 0.3 rad/s turn (actual 0.15 rad/s; yaw error ≤ 0.19 rad) adds about 100 registration-only cells but closes 0 columns in 25 s. Marks stop growing the moment the rotation stops. |
| Shares, run 2, pre-clear (sim 37.5 s, 333 new aisle-crop cells) | Geometry (ideal ray-cast) **17 %** (56 cells); localizer-lag registration **72 %** (241 cells); not reproduced **11 %** (36 cells), consistent with the range-noise and M1-noise terms the forward model omits. Closure: geometry 0 / 17 columns, lag model 17 / 17. |
| Replay validation | Re-projecting every recorded scan through the recorded TF, as the costmap does, reproduces the recorded new lethal cells at **recall 0.98–1.00** and precision 0.73–1.00 in all 9 phases. No third source is needed: unexplained aisle cells are 0–6 per phase, and almost no beam returned where no geometry exists at rest (5 / 198 / 0 of 288–360 k beams per run). |
| Fix recommendation | See the matrix. **H** (`clearing: true` with `raytrace_max_range` ≥ `obstacle_max_range`) or **A** (stamp-matched localizer lookup) each removes the closures in the counterfactual replays; **A + H** covers both terms. C alone fails as soon as the robot is within 2 m of the aisle. Every option except E/F/G is a shared change that touches every live-Nav2 frozen v2 result. |
| Suite | Baseline `62c01ac` and branch, same venv: 63 failed / 153 skipped / 3 errors on both. Passed 5115 → 5117 (+2 new overlay pins). The failing-name sets are identical (66 = 66, `diff` empty). |
| VM | Idle: `pgrep` empty, GPU 0 % / 171 MiB. Configs pristine in source and installed (`1f656533…` / `e18c723c…`). The tree equals the branch tip for every file changed since `46492d6`, except the pristine `orchestrator.yaml`. |

---

## Corrections to the waypoints report (Rev 2)

These change the premise this probe was asked to test:

1. **The global costmap never raytraced anything open.** The sim 38.53 s row ("0 closed, bottleneck 80; raytraced open") is a full clear. `nav2_r1.log` has `Received request to clear entirely the global_costmap` at wall `1791203069.38`, which is sim 37.8 on the probe's own wall→sim map. It is the BT recovery after `Failed to create plan` at sim 37.8. The sim 76.83 s reopening is the same thing (wall `1791203151.54`, sim 75.9). With `clearing: false` (next section), a clear is the only way a mark ever leaves.
2. **The probe's time base was saturated.** `waypoint_probe.py` subscribed to `/tf` at depth 100 alongside full-rate twists and odometry in one Python executor:
   - Odometry row content ran **1.9–2.0 s behind** the row's own sim stamp throughout the motion. This was found by matching each row's odom displacement to the ground-truth trajectory, which agrees to the millimetre once shifted.
   - It recorded 390 `map_odom` rows in about 96 sim-s, from a 20 Hz publisher whose value changes with every camera update. That is about 20 % of the publishes. The C++ bag recorder in this probe captured 2991 in about 150 sim-s, the full 20 Hz.
   - So "max \|map→odom yaw\| ≤ 0.06 rad over the prior 3 s" compared the closure against sparse samples from about 2 s earlier. It is not evidence of a small error.
   - The content-stamped M1−GT heading error from `m5_scene.jsonl` was **−0.146 rad at sim 17.07** (`_analysis/m1vgt.py`), one second before the first closure.
   - The costmap crop rows themselves were timely to about 1 s: the clear at sim 37.8 shows up in the 38.53 row.

---

## Finding 1: the obstacle layer only ever marks

Neither costmap sets `clearing` or `marking` for its `scan` source:

- Jazzy `nav2_costmap_2d/plugins/obstacle_layer.cpp` declares `marking` default `true`, `clearing` default `false`, `obstacle_max_range` 2.5 and `raytrace_max_range` 3.0.
- `ros2_ws/src/swarm_simulation/config/nav2_params.yaml` overrides only `topic`, `max_obstacle_height` and `obstacle_max_range: 3.5`.

Read live on the VM (`ros2 param get`, `cp_a_s42/params.txt`), identical for the global and local costmaps:

```text
obstacle_layer.scan.clearing: False      obstacle_layer.scan.marking: True
obstacle_layer.scan.raytrace_max_range: 3.0   obstacle_layer.scan.obstacle_max_range: 3.5
obstacle_layer.footprint_clearing_enabled: True   global inflation_radius: 0.1 (local 0.07)
footprint_padding: 0.01   update_frequency: 5.0   publish_frequency: 1.0
```

Consequences:

- **Every mark is permanent until a ClearEntireCostmap.** In run 2 the aisle-crop lethal count only ever grows: 114 → 127 → … → 447. It drops only at the two recovery clears.
- **Every transient error integrates.** A closure is the union of every mis-registered scan since the last clear, not the error of the moment.
- **Turning clearing on with the shipped default would still leave a gap.** `raytrace_max_range` (3.0) < `obstacle_max_range` (3.5), so returns marked 3.0–3.5 m away could still never be cleared. Run 2's first-closure cells lay 2.07–3.28 m from the robot.
- **The local costmap also never clears.** It is a rolling window, so marks leave by scrolling off, not by raytrace. This is a candidate contributor to the DWB corner local minimum flagged in the waypoints report; not chased here.

---

## Finding 2: run 2's first closure, predicted vs observed (no VM)

`scripts/costmap_source_analysis.py BUNDLE` works as follows:

- It replays run 2's ground-truth pose at the lidar's 10 Hz.
- It ray-casts a 360-beam, 1°, single-plane scan against the loop map's physical geometry at the 0.182 m scan plane. The geometry is `scenario_builder._author_loop_connectors`'s four NE remainders, all solid at that height, including the 0.3 m connector remnants.
- It registers each hit with one of two believed poses and marks cells without ever clearing:
  - **`gt`:** zero localization error, so geometry only.
  - **`lag`:** the localizer's pairing. `believed(t) = GT(τ) ⊕ GT(t_c)⁻¹ ⊕ GT(t)`, with `t_c = t − 0.3 s` (the `map -> odom` future-stamp) and `τ = t_c − L`.
- It scores the result cell by cell against the probe's crop, re-applying the 0.08 m inscribed inflation.

**Geometry check (item 3 of the brief).** From the primary aisle at about (−1.55, 0):

- The NW rack corner (−0.6, 0.6), the remnant's top-west corner (0.6, 0.925) and the 3.5 m horizon leave only the **north wall's south face (y = 1.475)** visible inside the crop, at x ≈ 0.8–1.6 and grazing incidence of about 23–35°. The remnant's west face (x = 0.6) is also visible.
- The remnant's north face (y = 0.925) is not visible from these poses.
- A 0.182 m beam cannot clear the 0.3 m remnant without about 3° of upward pitch, and if it did it would hit the 0.9 m slab face, which is also at y = 1.475.
- So no legitimate return can land in the aisle interior (y ≈ 1.0–1.4) from these poses. Legitimate returns mark only:
  - the y = 1.475 half-cell row (the static map leaves the cell straddling the face free);
  - the x = 0.575 column of the N–S strip (the x = 0.6 face sits on a cell boundary).

Forward-model results:

| sim (s) | Observed new cells / closed cols | Geometry only (`gt`) | Lag model (L 0.48 s, D 0.3 s) |
|---|---|---|---|
| 17.07 | 40 / 0 | 13 / 0 | 24 / 0 (22 matched) |
| **18.07** | **71 / 5** | 21 / **0** | 72 / **7** (32 matched) |
| 19.20 | 94 / 8 | 29 / 0 | 88 / 8 |
| 24.43 | 241 / 15 | 33 / 0 | 247 / 14 |
| 34.20 | 300 / 16 | 58 / 0 | 335 / 17 |
| 37.50 | 333 / 17 | 58 / 0 (56 matched) | 350 / 17 (297 matched; recall 0.89, precision 0.85) |

The model's peak yaw error before the closure is −0.157 rad at sim 17.5. The M1−GT sample at 17.07 is −0.146 rad. The source is DWB weaving while "driving straight": GT θ swings ±0.1 rad, |ω| up to 0.37 rad/s. At 2–3.3 m, 0.15 rad moves a north-wall return 0.25–0.45 m into the 0.55 m aisle.

Sweeping L ∈ {0.3, 0.45, 0.6} s and D ∈ {0, 0.3} s gives first-closure counts of 0–10 columns at 18.07 (`L 0.45 / D 0.3` gives exactly 5), with recall at 37.5 of 0.82–0.93. The result does not hinge on one parameter choice.

Crop at sim 18.07, x 0.425–2.075 (columns) by y 0.625–1.475 (rows). Legend: `S` static, `B` observed and predicted, `O` observed only, `P` predicted only.

```text
lag model (L 0.48 s)                         geometry only
1.475 .............O.O.O................   1.475 .........PPPPBPBPBPPPPP...........
1.425 ...........P.OB.PO.P..............   1.425 .............OO..O................
1.375 ...........O..O.OO................   1.375 ...........O..O.OO................
1.325 .........P.P..B.P.B..P............   1.325 ..............O...O...............
1.275 ..........P.B.POPO.P.O............   1.275 ............O..O.O...O............
1.225 ............PO.P.P.BO.P...........   1.225 .............O.....OO.............
1.175 ...........PP.PBPP.PP.............   1.175 ...............O..................
1.125 .P...........PP.B.P..P............   1.125 ................O.................
1.075 OB...........PPPP.B.BP.P..........   1.075 OO................O.O.............
1.025 OPO.........O.OPOBP..POP..........   1.025 O.O.........O.O.OO....O...........
0.975 OBBOO............O.POOP...........   0.975 OOOOO............O..OO............
0.925 .BBBO.OO..........O..O............   0.925 .OOBO.OO..........O..O............
0.875 OBBBSSSSSSSSSSSSSSSSSS...........S   0.875 OOOBSSSSSSSSSSSSSSSSSS...........S
```

The model puts its blob in the observed region at the observed update. Its cell-level recall at 18.07 is only 0.45, because exact cells depend on the unmodelled M1 heading noise and range noise. The aggregate (count, region, onset, column count) is what it reproduces, and the VM replay below closes that gap with recorded data.

---

## Finding 3: the VM probes

### Design

The scenario is `loop_map_preemption_probe_baseline`: loop map, no blocker, mock backend, zero API, with its USD and map unchanged. It is driven by the new `scripts/vm/costmap_probe.sh`, which wraps `v2_final_run.sh` and so keeps every standing trap.

1. M5 drives robot_1 to a park goal (`v2_overlay.py` scenes `costmap_probe_a` / `costmap_probe_b`):
   - **A** = (−1.55, 0): the primary-aisle vantage of run 2's first closure, 2–3.5 m from the aisle interior.
   - **B** = (0.3, 1.2): WP0, at the aisle mouth, looking down the aisle.
2. `scripts/vm/costmap_probe.py` waits for the park (still for 3 s within 0.25 m of the goal). Then, per phase, it calls `/robot_1/global_costmap/clear_entirely_global_costmap` and marks the phase on `/costmap_probe/phase`:
   - **static** for 100 s (A) or 80 s (B);
   - **rot 1.0 rad/s** for 6.283 s plus a 4 s hold;
   - **rot 0.3 rad/s** for 20.944 s plus a 4 s hold.

   Rotation goes on raw `/robot_1/cmd_vel`; Nav2 is idle by then.
3. `ros2 bag record` (C++, mcap) captures `/robot_1/scan`, `/tf`, `/tf_static`, `/robot_1/odom`, `/perception/scene_state`, `/robot_1/cmd_vel`, the global costmap with its updates, and the markers. Nothing is lost to a Python queue.
4. `scripts/vm/costmap_bag_export.py` (in-container, rosbag2_py) writes JSONL keyed on header sim stamps. For each grid update it gives the full-grid set of new lethal cells relative to the first full grid.
5. `costmap_source_analysis.py RUN --replay` re-projects every recorded scan three ways:
   - **`tf`:** through the recorded `map -> odom` and `odom -> base_footprint` at the scan stamp, plus the recorded `base_scan` mount, exactly as the costmap does;
   - **`gt`:** at the ground-truth pose, giving real returns including range noise;
   - **ideal:** an exact ray-cast at the ground-truth pose.

Runs (all GATE OK, RESTORE OK, M5 arrival accepted 0.10 / 0.10 / 0.11 m, all phases completed):

| Run | Park | Seed | Stamp | Parked at (sim) |
|---|---|---|---|---|
| `cp_a_s42` | A | 42 | `20261005_131748` | 21.1 |
| `cp_b_s42` | B | 42 | `20261005_133451` | 36.5 |
| `cp_a_s43` | A (replication) | 43 | `20261005_135124` | 20.9 |

### Attribution per phase (aisle crop x 0.4–2.1, y 0.6–1.5, at the phase's last grid)

Column meanings:

- **Observed** — new lethal cells in the recorded grid.
- **Ideal geom** — matched by the exact ray-cast.
- **Range noise** — matched only by the measured returns at the GT pose.
- **Registration** — matched only through the recorded TF.
- **Unexpl** — matched by none of the three projections.
- **TF-replay recall** — the replay's recall on the whole grid.

| Run / phase | Max \|yaw err\| (rad) | Observed | Ideal geom | Range noise | Registration | Unexpl | TF-replay recall (whole grid) | Closed cols |
|---|---|---|---|---|---|---|---|---|
| A s42 static 100 s | 0.045 | 70 | 17 | 44 | 8 | 1 | 0.993 | **0** |
| A s42 rot ω 0.78 | 0.705 | 178 | 22 | 46 | 107 | 6 | 0.987 | **12** |
| A s42 rot ω 0.15 | 0.165 | 152 | 24 | 30 | 100 | 0 | 0.992 | **0** |
| B s42 static 80 s | 0.120 | 104 | 51 | 23 | 30 | 0 | 0.998 | **0** |
| B s42 rot ω 0.78 | 0.630 | 277 | 52 | 50 | 174 | 1 | 0.988 | **6** |
| B s42 rot ω 0.15 | 0.184 | 163 | 55 | 12 | 96 | 0 | 0.997 | **0** |
| A s43 static 100 s | 0.026 | 71 | 14 | 46 | 11 | 0 | 0.998 | **0** |
| A s43 rot ω 0.78 | 0.676 | 172 | 25 | 40 | 108 | 2 | 0.989 | **13** |
| A s43 rot ω 0.15 | 0.181 | 153 | 25 | 28 | 99 | 2 | 0.987 | **0** |

Read-outs:

- **Static.** Nothing closes, at either vantage, in either seed.
  - The marks are the y = 1.475 north-wall half-cell row, the y = 0.925 remnant-face half-cell row (from B), the x = 0.575 strip column, and range-noise tails one row in from the north wall.
  - The RTX range residual at rest has median −0.3 mm, MAD 1.3 cm and p95 5 cm. A 6 cm short return at 25° incidence lands one row in, and over 1000 never-cleared scans those tails fill the row.
  - Static M1 heading flicker (two-level, −0.022 / +0.002 rad at B, occasional 0.1 rad) adds 8–30 cells.
  - Beam check at rest: returns with no geometry inside range were 5 / 198 / 0 out of 288–360 k beams per run. **No ground or pitch returns.**
  - The "missing" beams are RTX dropouts, encoded as `-1.0` and dropped by laser_geometry, so they cannot mark. There were 18–29 per scan.
- **The geometry narrowing budget.** Lethal y = 0.925 and y = 1.475 rows plus inflation leave rows 1.025–1.375 at cost < 99. With the range-noise row at 1.425 that falls to 1.025–1.325, a 0.30–0.35 m inscribed-free band. That is real, never closes alone, and is what makes a 0.1–0.2 m registration smear sufficient.

Timeline of the fast rotation at A s42. Each cell reads `t since clear: closed cols / new crop cells / max |yaw err| since previous grid`. Full timelines for all runs are in `_analysis/rotation_timelines.txt`.

```text
1.0s:0c/46n/0.34  2.0s:0c/71n/0.46  3.1s:6c/96n/0.73  4.1s:12c/122n/0.63  5.1s:12c/145n/0.47
6.2s:12c/164n/0.64  7.2s:12c/174n/0.56  [rotation ends]  8.3s:12c/178n/0.01  9.4s:12c/178n/0.01
```

Fitted lag (least squares of yaw error on −ω, rotating samples):

| Run | ω 0.78 | ω 0.15 (M1 noise comparable to the signal) |
|---|---|---|
| A s42 | 0.48 s | 0.62 s |
| B s42 | 0.60 s | 0.64 s |
| A s43 | 0.43 s | 0.64 s |

Commanded 1.0 / 0.3 rad/s produced 0.78 / 0.15 rad/s in sim. The tables use the actual rates.

Why the slow rotation never closes while run 2's similar-sized weave errors did:

- A one-way rotation has a fixed-sign error, so it smears the visible wall one way only. From A that is south from the north wall, rows 1.125–1.375.
- Run 2's weave alternated sign while the robot translated, sweeping marks across the whole width from changing ranges and bearings.

The forward model reproduces both behaviours with the same lag.

---

## Source shares

| Source | Mechanism | Share of marks | Share of closure |
|---|---|---|---|
| Localizer lag registration (M1 shared node) | `Time()` odom lookup pairs a 0.3–0.6 s old M1 pose with the latest odom; the error is −ω × L, sampled 0.3 s later by the future-stamped TF | Run 2 pre-clear: **72 %**. VM rotation phases: 59–66 % of aisle marks | **All observed closures.** Run 2: 17 / 17 columns modelled. VM: 12 / 6 / 13 columns, at fast rotation only |
| No-clearing accumulation (shared Nav2 params) | `clearing: false` default; `raytrace_max_range` 3.0 < `obstacle_max_range` 3.5 | Amplifier: makes every share above permanent | Necessary: with clearing on (raytrace 3.5 m) every VM closure and run 2's end state replay to 0 columns |
| Legitimate geometry (half-cell faces) | Faces at y = 0.925 / 1.475 fall in cells the static map rasterizes free | Run 2: **17 %**. VM static: 14–51 cells per phase | **0** columns in every run and model |
| RTX range-noise tails | p95 5 cm range error, integrated over never-cleared scans | VM: 12–50 cells per phase; part of run 2's unexplained 11 % | 0 alone; narrows the band by one more row |
| M1 heading noise at rest | Two-level flicker, max 0.03–0.12 rad | VM static: 8–30 cells | 0 at rest |
| Ground returns, pitch, beam spread | — | Not observed (5 / 198 / 0 non-geometry returns of 288–360 k beams at rest) | — |

---

## Fix recommendation matrix (diagnosis only: none applied)

"Counterfactual closed cols" are replay results (`--replay --counterfactual`, `_analysis/*_counterfactual.txt`). Each one re-projects the **recorded** scans and TF through a re-implementation of the obstacle layer's per-scan clear-then-mark. The forward-model row uses run 2 with L 0.48 s. These are simulations of the costmap logic, not Nav2 runs, so any chosen option needs a live re-validation.

| Option | Scope | Fixes | Counterfactual closed cols: VM fast rotation A s42 / B / A s43 | Run 2 forward, at 18.07 / 24.43 / 37.8 | Re-validation cost (frozen v2 results touched) |
|---|---|---|---|---|---|
| As configured | — | — | 13 / 6 / 13 | 7 / 14 / 17 | — |
| **A.** Localizer: odom lookup at the M1 scene stamp (TF buffer) instead of `Time()` | M1 shared node | The lag term, which is the dominant source | Bound (perfect localizer, GT registration): 1 / 3 / 1. The residual is intra-sweep motion plus noise tails, with clearing still off | Bound: 0 / 0 / 0 (geometry only) | **All live-Nav2 results.** `map -> odom` also rotates the global path handed to DWB. Touches the `free_flow_v1` table (frozen today), the v1 head-on family, T1 / T2b / T3a / T3b / T3c, B2 / B3, the IB10 composite / junction step-7b PASS, and the loop family. M5 arrival checks (M1 positions) and GT scoring do not change. Offline artifacts (capability-probe manifest, battery-v2 frames, presentation-order probe) are untouched unless re-harvested. |
| **B.** Localizer: low-pass / rate-limit the yaw correction, or hold it while \|ω\| is large | M1 shared node | Bounds the lag term and noise | Not simulated; between A and as-configured | Not simulated | Same as A |
| **C.** Global `obstacle_max_range` 2.5 / 2.0 (or obstacle layer off globally) | Shared Nav2 param | Long lever arm only | 2.5 m: 0 / **6** / 0. 2.0 m: 0 / **6** / 0. B's aisle is within 2 m | 2.5 m: 0 / 7 / **17**. 2.0 m: 0 / 0 / **17**. It fails once the robot reaches the aisle mouth | All live-Nav2 results. T3a / T3b blockers would be first marked later or, with the layer off, only locally |
| **H** (new). `clearing: true`, `raytrace_max_range` ≥ `obstacle_max_range` (3.5) | Shared Nav2 param, global (and arguably local) | The amplifier: mis-registered marks are raytraced away by later correct scans | Raytrace 3.5: 0 / 0 / 0. Raytrace 3.0 (default): 6 / 0 / 7 | Raytrace 3.5: 0 / 1 / 0. Raytrace 3.0: **7** / 1 / 0 | All live-Nav2 results, **and the largest behaviour change.** Today a removed timed blocker, and every other robot's trail, stays lethal in the global costmap until a recovery clear. Every multi-robot result (head-on, T-family, B2 / B3, IB10) and every transient-blocker scene (`loop_detour_transient`, T3c) currently depends on that persistence |
| **A + H** | Both shared | Both terms | A bound + H (raytrace 3.5): 0 / 0 / 0 | 0 / 0 / 0 (geometry-only bound) | Union of A and H |
| **D.** Lower `max_vel_theta` / RotateToGoal speed | Shared Nav2 param | Rotation spikes only; ω × L scales down | Not simulated; slow rotation (0.15 rad/s) closed 0 in all runs | The weave term (ω ≤ 0.37) remains, so the first closure remains | All live-Nav2 results, including every rotation's timing and the free-flow arrival rotations |
| **E.** Any of C / D / H scoped to the loop family (per-scenario params file) | fc_launch plumbing, default-off | Same as the chosen option, loop scenes only | Same as the chosen option | Same as the chosen option | No other scene, but a protocol ruling is needed: loop-family numbers would come from a different Nav2 configuration than every other family |
| **F.** M4: waypoint yaw = bearing to the next waypoint, or `navigate_through_poses` | M4 `follow_waypoints` only | Removes the stop-and-rotate at WP0 | n/a | Does not touch the 18.07 closure, which happens in the primary aisle before any waypoint | Loop reroute results only. **Cannot fix alone** |
| **G.** Waypoint geometry (WP0 elsewhere) | M3 / overlay | Moves the rotation spike | n/a | Same as F | Loop reroute results only. Hides the defect |
| **I** (new). Rasterize the boundary half-cells occupied, or snap the loop-map faces to cell boundaries | Map generator (`rasterize_loop_map`, loop maps only) | Makes the legitimate one-row narrowing explicit in the static map | No closure change (geometry closes 0 alone) | 0 | Loop-family maps only. **Not recommended as a fix**: the narrowing is real geometry |

**Reading the matrix.**

- The closure needs both the lag term and the never-clearing layer. Removing either one removes it, in every counterfactual except H at the default raytrace range, which leaves the 3.0–3.5 m band uncleared.
- **H (with raytrace 3.5 m) is the single change that zeroes every case tested**, but it has the widest behavioural blast radius, because persistence of other robots and removed blockers is baked into every frozen multi-robot result.
- **A** removes the root error at its source. It leaves a 1–3-column residual during fast rotations while clearing stays off.
- **E scoping H to the loop family** is the narrowest change that fixes the loop family, at the cost of a protocol ruling.

---

## Secondary observations

- **Local costmap `clearing: false` as well.** Rolling-window marks persist until they scroll off. Untested candidate for the DWB "near-zero twist in the remnant corner" local minimum in the waypoints report.
- **Commanded vs actual yaw rate.** Raw `cmd_vel` of 1.0 / 0.3 rad/s produced 0.78 / 0.15 rad/s in sim. Not chased; only the measured rates are used here.
- **RTX dropouts.** 18–29 of 360 beams per scan return `-1.0` where geometry exists within 0.6–2 m. They cannot mark, but they also could never clear, if clearing were turned on.
- **Static map vs costmap resolution.** The costmap reports its resolution as float32 (0.0500000007). Re-rasterizing at that value shifts the generator's output by a row; the analysis rounds to 0.05 to match the shipped map.

---

## Tooling (v2-only)

Probe tooling only; no shared component changed:

| File | Role | Commit |
|---|---|---|
| `scripts/vm/costmap_probe.sh` | VM driver: wraps `v2_final_run.sh`; adds params dump, bag record, probe, bag stop, export, copy-out | `681f5c6` |
| `scripts/vm/costmap_probe.py` | In-container phase controller (park wait, clear, static / rotate, markers) | `681f5c6` |
| `scripts/vm/costmap_bag_export.py` | In-container rosbag2_py → JSONL exporter | `681f5c6`, `83cef79` (marker-key fix) |
| `scripts/vm/v2_overlay.py` | Scenes `costmap_probe_a` / `costmap_probe_b`, which set only robot_1's park goal | `681f5c6` |
| `scripts/costmap_source_analysis.py` | Forward model, bag replay attribution, counterfactuals | `681f5c6`, `83cef79`, `f6bc0b0` |
| `tests/unit/test_apparatus_overlay.py` | +2 pins: the probe scenes set only robot_1's goal | `681f5c6` |

Reproduce the analysis with:

```bash
P=.venv/bin/python; D=data/logs/vm_runs
$P scripts/costmap_source_analysis.py $D/waypoints_validation/wp_fwd_s43 --model lag --lag 0.48 --delay 0.3 --show 18.067
$P scripts/costmap_source_analysis.py $D/waypoints_validation/wp_fwd_s43 --model gt
$P scripts/costmap_source_analysis.py $D/waypoints_validation/wp_fwd_s43 --counterfactual --lag 0.48 --delay 0.3
$P scripts/costmap_source_analysis.py $D/costmap_probe/cp_a_s42 --replay
$P scripts/costmap_source_analysis.py $D/costmap_probe/cp_a_s42 --replay --counterfactual
```

---

## Verification

- **Local suite.** `pytest -q --continue-on-collection-errors -p no:cacheprovider -rfE`, one venv. A clean detached worktree at `62c01ac` and the branch both give 63 failed / 153 skipped / 3 errors. Passed: 5115 → 5117, the +2 being the new overlay pins. The failing and erroring name sets are identical (`diff` empty). `ruff check` is clean on every new or changed file.
- **Deploy (delta).** The VM tree sat at `46492d6`. Only the files changed since then were shipped:
  - two docs commits and the probe tooling;
  - nothing under `ros2_ws/src`, so no colcon rebuild was needed and no module was deleted (the build-cache purge was not applicable).

  The method was `git archive` of exactly that file list, then `tar -xzmf`, then `touch`. The md5 of every shipped file equals the local file. The exporter fix was re-shipped the same way. After the last run, the tip's delta was re-shipped and re-verified (8 / 8 md5 match).
- **Per run.** Each run passed:
  - the `pgrep -f run_simulation`-empty gate (0 s wait each time);
  - `GATE OK: logs saved to present`;
  - M5 confirmed started (arrival line in `m5.log`);
  - `RESTORE OK`, with source and installed `orchestrator.yaml` at `1f656533…` and `rag.yaml` at `e18c723c…`;
  - the bag stopped by SIGINT before fc_launch's container restart (`Recording stopped`), then exported and copied out.

  Run A s42's in-run export failed on a marker-key collision. It was re-exported from the host-copied bag after the fix, so no data was lost.
- **VM at close-out (14:10 UTC).** `pgrep` for Isaac, fc_launch and `isaac.scripts` is empty. The GPU is at 0 % / 171 MiB, and there is no bag or probe process in the container. The VM is left running and idle, as found.

---

## References

- Predecessor: `docs/reports/2026-10-05-follow-waypoints-validation.md` (Rev 2). Its `_analysis/m1vgt.py` and `lag.py` are in `data/logs/vm_runs/waypoints_validation/_analysis/`.
- Run bundles: `data/logs/vm_runs/costmap_probe/{cp_a_s42,cp_b_s42,cp_a_s43}/`. Each holds `bag/`, `export.jsonl`, `phases.jsonl`, `params.txt`, `gt/` and the logs.
- Analysis outputs: `data/logs/vm_runs/costmap_probe/_analysis/`:
  - `*_replay.{txt,json}`;
  - `*_counterfactual.txt`;
  - `rotation_timelines.txt`;
  - `wp_fwd_s43_model_{gt,lag048}.json`;
  - `wp_fwd_s43_counterfactual.txt`.
- Config: `ros2_ws/src/swarm_simulation/config/nav2_params.yaml` (`local_costmap` / `global_costmap` `obstacle_layer`).
- Localizer: `ros2_ws/src/swarm_perception/swarm_perception/camera_localizer_node.py` (`_lookup_odom_pose`, `_publish_map_to_odom` future stamp).
- Geometry: `isaac/vgu_sim/scenario_builder.py` (`_author_loop_connectors`), `isaac/scripts/generate_warehouse_map.py` (`rasterize_loop_map`).
- Upstream default: ros-navigation/navigation2 `jazzy`, `nav2_costmap_2d/plugins/obstacle_layer.cpp` (`clearing` default `false`).

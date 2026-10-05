# Costmap Source Probe: What Marks the Loop Map's Second Aisle Lethal

**Prepared:** 2026-10-05

**Revision history:**

- Initial draft: source attribution for the phantom lethal cells that close the 0.55 m second aisle in the shared global costmap. Covers the obstacle-layer configuration finding, a geometry forward model of run 2's first closure, three VM probe runs (static plus two rotation rates, two park poses, one replication), a bag-replay attribution, and the fix recommendation matrix. Diagnosis only: no fix applied.
- Rev 2 (same day, review pass): the GT log runs 0.300 s behind ROS stamps, so every GT-vs-ROS number is now re-timed. The localizer lag is decomposed in-domain. Run 2's forward model now uses its own recorded `map -> odom` samples instead of a smooth lag model, and option A is re-simulated honestly from the recorded M1 stream. A alone does **not** clear the closures; the matrix and shares are corrected.

---

## Summary

Branch `feat/v2-costmap-probe`, cut from `feat/prereg-v2-composite` at `62c01ac`. It follows `docs/reports/2026-10-05-follow-waypoints-validation.md` (Rev 2), referred to below as "the waypoints report".

All times are ROS sim stamps unless marked. The GT log's `sim_time_sec` is re-timed by its fitted +0.300 s offset (see Corrections).

| Item | Outcome |
|---|---|
| **Attribution** | **One error source plus one amplifier, on top of a fixed, non-closing geometry narrowing.**<br>• **Source: camera-localizer registration error.** It equals the `map -> robot_1/odom` yaw itself, because Isaac's odometry is drift-free and the spawn yaw is 0. It is −ω × L, with an effective L of 0.14–0.35 s, made of two parts:<br>  – M1's own upstream latency (M1 pose vs truth at its own scene stamp): 0.04–0.20 s;<br>  – the localizer's `Time()` pairing (scene arrival − scene stamp): median 0.10–0.32 s, max 0.43 s.<br>• **Amplifier: the obstacle layer never clears.** `clearing` is `false` in both costmaps (the Jazzy default; `nav2_params.yaml` never sets it; verified live). Every mis-registered return stays until a ClearEntireCostmap.<br>• **Geometry:** legitimate returns from the north wall (y = 1.475) and the 0.3 m remnant's north face (y = 0.925) land in half-cells the static map leaves free. RTX range-noise tails, integrated over about 1000 scans, add about one more row. These narrow the aisle but **never closed a column**: 0 / 17 in every static phase and in the zero-error model. |
| Run 2's "unexplained" first closure (sim 18.07) | **Explained by the recorded registration error.** The waypoints report's "≤ 0.06 rad" came from a probe whose rows ran about 2 s behind their content (measured against the localizer's own log) and caught about 20 % of the `map -> odom` publishes. Its −0.194 rad sample, logged at 19.67, happened at about 17.5, **before** the closure. Re-timed and replayed through the scene geometry, run 2's own recorded `map -> odom` samples reproduce the onset at the same costmap update: 0 → 8–10 columns predicted vs 0 → 5 observed, for every re-timing shift from 1.7 to 2.3 s. Geometry alone predicts 0. |
| Static-robot probe (the decider) | **No closure in 280 stationary sim-s** across 3 runs and 2 park poses. Marks there are 69–87 % GT-registered real returns (geometry plus range-noise tails), and 8–32 cells come from M1 heading flicker (registration error max 0.02–0.03 rad). |
| Rotation probe | **Closure tracks ω × L.** One commanded 1.0 rad/s turn (actual 0.81 rad/s; registration error max 0.39–0.50 rad) closes **12 / 6 / 13 columns within 2–4 s**. A commanded 0.3 rad/s turn (actual 0.15 rad/s; error ≤ 0.14 rad) adds about 95 registration-only cells but closes 0 columns in 25 s. Marks stop growing the moment the rotation stops. |
| Shares, run 2 pre-clear (sim 37.5, 333 new aisle-crop cells) | Geometry (ideal ray-cast) **17 %** (56 cells). Registration through the recorded `map -> odom` **66 %** (221 cells). Not reproduced **17 %** (56 cells), consistent with the 80 % of `map -> odom` publishes that probe missed plus range-noise tails. In the VM runs, where the full TF is recorded, the unreproduced share is 0–5 cells per phase. Closure: geometry 0 / 17 columns, recorded-TF model 17 / 17. |
| Replay validation | Re-projecting every recorded scan through the recorded TF, as the costmap does, reproduces the recorded new lethal cells at **recall 0.987–0.998** and precision 0.73–1.00 in all 9 phases. There are no ground or pitch returns: 5 / 198 / 0 non-geometry returns at rest, out of 288–360 k beams per run. |
| Fix recommendation | See the matrix. Replay counterfactuals:<br>• **H** (`clearing: true` with `raytrace_max_range` ≥ `obstacle_max_range`): 0 / 0 / 0 at fast rotation; run 2 has a 2-column transient at 18.07, then 0.<br>• **A** (stamp-matched odom lookup): **7 / 0 / 9**, because M1's own upstream latency remains.<br>• **A + H:** 0 / 0 / 0.<br>• A perfect-timing localizer: 0 / 0 / 0 even with clearing off.<br>• C (range cap) fails within 2 m of the aisle.<br>Every option except E / F / G is a shared change that touches every live-Nav2 frozen v2 result. |
| Suite | Baseline `62c01ac` and branch, same venv: 63 failed / 153 skipped / 3 errors on both. Passed 5115 → 5117 (+2 new overlay pins). The failing-name sets are identical (66 = 66, `diff` empty). |
| VM | Idle: `pgrep` empty, GPU 0 % / 171 MiB. Configs pristine in source and installed (`1f656533…` / `e18c723c…`). The tree equals the branch tip for every file changed since `46492d6`, except the pristine `orchestrator.yaml`. |

---

## Corrections to the waypoints report (Rev 2) and to GT-based timing generally

1. **The global costmap never raytraced anything open.** The sim 38.53 row ("0 closed, bottleneck 80; raytraced open") is a full clear: `nav2_r1.log` has `Received request to clear entirely the global_costmap` at wall `1791203069.38`, which is sim 37.8 on the probe's own wall→sim map. It is the BT recovery after `Failed to create plan`. The 76.83 reopening is the same (wall `1791203151.54`, sim 75.9). With `clearing: false` (Finding 1), a clear is the only way a mark ever leaves.
2. **The waypoint probe's time base was saturated.** `waypoint_probe.py` ran `/tf` (depth 100), full-rate twists and odometry through one Python executor:
   - Odometry rows ran **1.9–2.0 s behind** their content.
   - `map_odom` rows ran **2.1–2.3 s behind**. This was measured by matching three uniquely valued rows to the localizer's own `camera_localizer … map_odom=(…) scene_stamp=…` log lines.
   - It recorded 390 `map_odom` rows in about 96 sim-s from a 20 Hz publisher, about 20 %. This probe's C++ bag recorder captured the full 20 Hz.
   - So "max \|map→odom yaw\| ≤ 0.06 rad over the prior 3 s" compared the closure with sparse samples from about 2 s earlier.
   - The −0.194 rad sample logged at 19.67 happened at about 17.4–17.6, **before** the first closure. The costmap crop rows themselves were timely to about 1 s (the 37.8 clear shows in the 38.53 row).
3. **The GT log runs 0.300 s behind ROS stamps.** Isaac's odometry at ROS stamp t equals the ground-truth pose at GT time t − 0.300 s, with a residual of 0.2 mm, in all three runs. Scan-matching each lidar scan to the map during rotation independently gives an offset of 0.345–0.355 s, which is 0.3 s plus about half a 0.1 s sweep.
   - Consequence: every "M1 vs GT at the M1 stamp" comparison over-states M1 latency by 0.3 s. That covers `_analysis/lag.py` and `m1vgt.py`, the waypoints report's "M1 heading lags 0.3–0.45 s", and this report's initial draft (fitted L 0.43–0.60 s, max error 0.63–0.75 rad).
   - In the ROS domain the effective lag is 0.14–0.35 s, and the fast-rotation registration error is max 0.39–0.50 rad.
   - The bag-replay validation is unaffected, because it uses only recorded ROS data.

---

## Finding 1: the obstacle layer only ever marks

Neither costmap sets `clearing` or `marking` for its `scan` source:

- Jazzy `nav2_costmap_2d/plugins/obstacle_layer.cpp` declares `marking` default `true`, `clearing` default `false`, `obstacle_max_range` 2.5 and `raytrace_max_range` 3.0.
- `ros2_ws/src/swarm_simulation/config/nav2_params.yaml` overrides only `topic`, `max_obstacle_height` and `obstacle_max_range: 3.5`.

Read live on the VM (`ros2 param get`, `cp_a_s42/params.txt`), identical for the global and local costmaps except the inflation radius:

```text
obstacle_layer.scan.clearing: False      obstacle_layer.scan.marking: True
obstacle_layer.scan.raytrace_max_range: 3.0   obstacle_layer.scan.obstacle_max_range: 3.5
obstacle_layer.footprint_clearing_enabled: True   global inflation_radius: 0.1 (local 0.07)
footprint_padding: 0.01   update_frequency: 5.0   publish_frequency: 1.0
```

Consequences:

- **Every mark is permanent until a ClearEntireCostmap.** In run 2 the aisle-crop lethal count only ever grows: 114 → 127 → … → 447. It drops only at the two recovery clears.
- **Every transient error integrates.** A closure is the union of every mis-registered scan since the last clear.
- **Turning clearing on with the shipped default would still leave a gap.** `raytrace_max_range` (3.0) < `obstacle_max_range` (3.5), so marks made 3.0–3.5 m away could never be cleared. Run 2's first-closure cells lay 2.07–3.28 m from the robot.
- **The local costmap also never clears**, beyond scrolling off its rolling window. It is a candidate contributor to the DWB corner local minimum in the waypoints report; not chased here.

---

## Finding 2: run 2's first closure, reproduced from its own recorded TF (no VM)

`scripts/costmap_source_analysis.py BUNDLE --model {gt,recorded}` works as follows:

- It replays run 2's ground-truth pose at the lidar's 10 Hz.
- It ray-casts a 360-beam, 1°, single-plane scan against the loop map's physical geometry at the 0.182 m plane. The geometry is `scenario_builder._author_loop_connectors`'s four NE remainders, all solid at that height, including the 0.3 m connector remnants.
- It registers each hit and marks cells without ever clearing. Registration is either at truth (`gt`, geometry only) or through the probe's own `map -> odom` samples (`recorded`).
  - The recorded samples are re-timed by the probe's receive lag ("shift", 1.7–2.3 s) and the GT offset (0.3 s).
  - They are composed with the true odometry, which is drift-free.
- It scores the result cell by cell against the probe's crop, re-applying the 0.08 m inscribed inflation.

**Geometry check (item 3 of the brief).** From the primary aisle at about (−1.55, 0):

- The NW rack corner (−0.6, 0.6), the remnant's top-west corner (0.6, 0.925) and the 3.5 m horizon leave only the **north wall's south face (y = 1.475)** visible inside the crop, at x ≈ 0.8–1.6 and 23–35° grazing incidence. The remnant's west face (x = 0.6) is also visible.
- The remnant's north face (y = 0.925) is not visible from these poses.
- A 0.182 m beam cannot clear the 0.3 m remnant without about 3° of upward pitch, and if it did it would hit the 0.9 m slab, which is also at y = 1.475.
- So no legitimate return lands in the aisle interior (y ≈ 1.0–1.4) from these poses. Legitimate returns mark only:
  - the y = 1.475 half-cell row (the static map leaves the cell straddling the face free);
  - the x = 0.575 strip column (the x = 0.6 face sits on a cell boundary).

Results:

| sim | Observed new cells / closed cols | Geometry only (`gt`) | Recorded TF, shift 1.7 / 1.9 / 2.1 / 2.3 s (closed cols) | Recorded TF, shift 1.9 (cells, matched) |
|---|---|---|---|---|
| 17.07 | 40 / 0 | 13 / 0 | 0 / 0 / 0 / 4 | 32, 22 |
| **18.07** | **71 / 5** | 21 / **0** | **8 / 10 / 8 / 8** | 78, 34 |
| 19.20 | 94 / 8 | 29 / 0 | 11 / 10 / 9 / 8 | 96, 52 |
| 24.43 | 241 / 15 | 33 / 0 | 11 / 10 / 9 / 8 | 218, 178 |
| 37.50 | 333 / 17 | 58 / 0 (56 matched) | 17 / 17 / 17 / 17 | 299, 277 (recall 0.83, precision 0.93) |

The registration error that does it is DWB's weave while "driving straight": GT θ swings ±0.1 rad and |ω| reaches 0.37 rad/s. Combined with the pairing jitter (max 0.43 s), that produced the −0.194 rad sample just before the closure. At 2–3.3 m range, 0.15–0.2 rad moves a north-wall return 0.3–0.6 m into the 0.55 m aisle.

A smooth −ω × L model with the in-domain L (0.3 s) does **not** close the aisle by 18.07 (0 columns). It does close it by 24.43 (11) and 37.5 (17). So the first closure needs the actual spiky error, which the recorded samples carry even at a 20 % capture rate.

Crop at sim 18.07, x 0.425–2.075 (columns) by y 0.625–1.475 (rows). Legend: `S` static, `B` observed and predicted, `O` observed only, `P` predicted only.

```text
recorded TF (shift 1.9 s)                    geometry only
1.475 .............O.O.O................   1.475 .........PPPPBPBPBPPPPP...........
1.425 .........P.P.BBPPOP.P.............   1.425 .............OO..O................
1.375 ...........O..B.BO.P..............   1.375 ...........O..O.OO................
1.325 ..........P.P.BPP.BP.P............   1.325 ..............O...O...............
1.275 ............O..B.O...O............   1.275 ............O..O.O...O............
1.225 ...........P.OP.PPPOBP............   1.225 .............O.....OO.............
1.175 ...........P.PPOP.P..P............   1.175 ...............O..................
1.125 .............P.PO.P.P.............   1.125 ................O.................
1.075 OO...........P....B.B..P..........   1.075 OO................O.O.............
1.025 OPB.........O.O.BOP.PPO...........   1.025 O.O.........O.O.OO....O...........
0.975 OBBOO........PPPPO..OO.P..........   0.975 OOOOO............O..OO............
0.925 .BBBO.OO.........PBP.B............   0.925 .OOBO.OO..........O..O............
0.875 OBBBSSSSSSSSSSSSSSSSSSPP.........S   0.875 OOOBSSSSSSSSSSSSSSSSSS...........S
```

The cell-level recall at 18.07 is about 0.5: exact cells depend on the TF samples the probe missed. The onset, region and column count are reproduced. The VM bag replay below closes that gap with complete recorded data.

---

## Finding 3: the VM probes

### Design

The scenario is `loop_map_preemption_probe_baseline`: loop map, no blocker, mock backend, zero API, with its USD and map unchanged. It is driven by the new `scripts/vm/costmap_probe.sh`, which wraps `v2_final_run.sh` and so keeps every standing trap.

1. M5 drives robot_1 to a park goal (`v2_overlay.py` scenes `costmap_probe_a` / `costmap_probe_b`):
   - **A** = (−1.55, 0): run 2's first-closure vantage, 2–3.5 m from the aisle interior.
   - **B** = (0.3, 1.2): WP0, at the aisle mouth, looking down the aisle.
2. `scripts/vm/costmap_probe.py` waits for the park (still for 3 s within 0.25 m of the goal). Then, per phase, it calls `/robot_1/global_costmap/clear_entirely_global_costmap` and marks the phase on `/costmap_probe/phase`:
   - **static** for 100 s (A) or 80 s (B);
   - **rot 1.0 rad/s** for 6.283 s plus a 4 s hold;
   - **rot 0.3 rad/s** for 20.944 s plus a 4 s hold.

   Rotation goes on raw `/robot_1/cmd_vel`; Nav2 is idle by then.
3. `ros2 bag record` (C++, mcap) captures `/robot_1/scan`, `/tf`, `/tf_static`, `/robot_1/odom`, `/perception/scene_state`, `/robot_1/cmd_vel`, the global costmap with its updates, and the markers.
4. `scripts/vm/costmap_bag_export.py` (in-container, rosbag2_py) writes JSONL on header stamps. Each grid update carries the full-grid set of new lethal cells relative to the first full grid.
5. `costmap_source_analysis.py RUN --replay` re-projects every recorded scan three ways:
   - **`tf`:** through the recorded `map -> odom` and `odom -> base_footprint` at the scan stamp, plus the recorded `base_scan` mount, exactly as the costmap does;
   - **`gt`:** at the re-timed ground-truth pose, giving real returns including range noise;
   - **ideal:** an exact ray-cast at that pose.

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

| Run / phase | Max \|registration yaw err\| (rad) | Observed | Ideal geom | Range noise | Registration | Unexpl | TF-replay recall (whole grid) | Closed cols |
|---|---|---|---|---|---|---|---|---|
| A s42 static 100 s | 0.031 | 70 | 12 | 49 | 8 | 1 | 0.993 | **0** |
| A s42 rot ω 0.81 | 0.502 | 178 | 22 | 28 | 124 | 5 | 0.987 | **12** |
| A s42 rot ω 0.15 | 0.123 | 152 | 24 | 34 | 94 | 0 | 0.992 | **0** |
| B s42 static 80 s | 0.022 | 104 | 40 | 32 | 32 | 0 | 0.998 | **0** |
| B s42 rot ω 0.81 | 0.382 | 277 | 52 | 33 | 191 | 1 | 0.988 | **6** |
| B s42 rot ω 0.15 | 0.140 | 163 | 55 | 12 | 96 | 0 | 0.997 | **0** |
| A s43 static 100 s | 0.026 | 71 | 14 | 46 | 11 | 0 | 0.998 | **0** |
| A s43 rot ω 0.81 | 0.431 | 172 | 25 | 26 | 121 | 2 | 0.989 | **13** |
| A s43 rot ω 0.15 | 0.137 | 153 | 25 | 32 | 95 | 2 | 0.993 | **0** |

Read-outs:

- **Static.** Nothing closes, at either vantage, in either seed.
  - The marks are the y = 1.475 north-wall half-cell row, the y = 0.925 remnant-face half-cell row (from B), the x = 0.575 strip column, and range-noise tails one row in from the north wall.
  - The RTX range residual at rest has median −0.3 mm, MAD 1.3 cm and p95 5 cm. Over 1000 never-cleared scans those tails fill the next row.
  - M1 heading flicker at rest (std 0.002–0.011 rad, max 0.02–0.03 rad registration error) adds 8–32 cells.
  - Beam check: 5 / 198 / 0 returns with no geometry inside range at rest, out of 288–360 k beams per run. **No ground or pitch returns.** The "missing" beams, 18–29 per scan, are RTX dropouts encoded as `-1.0`; laser_geometry drops them, so they cannot mark.
- **The geometry narrowing budget.** Lethal y = 0.925 and y = 1.475 rows plus inflation leave rows 1.025–1.375 at cost < 99. With the range-noise row at 1.425 that falls to 1.025–1.325, a 0.30–0.35 m inscribed-free band. It never closes alone, and it is why a 0.1–0.2 m registration smear suffices.

Timeline of the fast rotation at A s42. Each cell reads `t since clear: closed cols / new crop cells / max |registration yaw err| since previous grid`. All runs are in `_analysis/rotation_timelines.txt`.

```text
1.0s:0c/46n/0.10  2.0s:0c/71n/0.22  3.1s:6c/96n/0.49  4.1s:12c/122n/0.39  5.1s:12c/145n/0.23
6.2s:12c/164n/0.39  7.2s:12c/174n/0.46  [rotation ends]  8.3s:12c/178n/0.01  9.4s:12c/178n/0.01
```

### Lag decomposition (ROS domain)

| Run / phase | Effective L (regression of yaw err on −ω) | M1 upstream (M1 θ vs truth at its own stamp) | Pairing: scene arrival − stamp (median / p90 / max) | Max \|err\| |
|---|---|---|---|---|
| A s42 rot 0.81 | 0.18 s | 0.10 s | 0.10 / 0.31 / 0.38 s | 0.50 rad |
| A s42 rot 0.15 | 0.32 s | 0.17 s | 0.14 / 0.35 / 0.40 s | 0.13 rad |
| B s42 rot 0.81 | 0.30 s | 0.04 s | 0.32 / 0.38 / 0.41 s | 0.39 rad |
| B s42 rot 0.15 | 0.35 s | 0.20 s | 0.11 / 0.33 / 0.40 s | 0.14 rad |
| A s43 rot 0.81 | 0.14 s | 0.07 s | 0.10 / 0.13 / 0.35 s | 0.47 rad |
| A s43 rot 0.15 | 0.35 s | 0.19 s | 0.17 / 0.34 / 0.40 s | 0.13 rad |

Arrival is the bag receive time mapped to sim through the odometry rows. The cross-check holds: the recorded `map -> odom` equals M1(s) ⊕ odom(arrival)⁻¹ to within 0–0.04 rad. That confirms the localizer does no other processing (`camera_localizer.py` is a pure SE(2) composition).

Both parts are material. Pairing dominates at B's fast turn; M1's upstream latency is 0.04–0.20 s everywhere.

Commanded 1.0 / 0.3 rad/s produced 0.81 / 0.15 rad/s in sim. The tables use the actual rates.

**Why the slow rotation never closes while run 2's weave did.** A one-way rotation has a fixed-sign error, so it smears the visible wall one way only. From A that is south from the north wall, rows 1.125–1.375. Run 2's weave alternated sign while the robot translated, sweeping marks across the whole width from changing ranges and bearings.

---

## Source shares

| Source | Mechanism | Share of marks | Share of closure |
|---|---|---|---|
| Localizer registration error (M1 shared node, plus M1 latency) | `map -> odom` = M1(s) ⊕ odom(arrival)⁻¹. The error is −ω × (M1 upstream 0.04–0.20 s + pairing 0.10–0.43 s), used 0.3 s later via the future stamp | Run 2 pre-clear: **66 %** (sparse TF; up to 83 % with the unreproduced share). VM rotation phases: 59–70 % of aisle marks | **All observed closures.** Run 2: 0 → 8–10 columns at the onset update, 17 / 17 by 37.5. VM: 12 / 6 / 13 columns, at fast rotation only |
| No-clearing accumulation (shared Nav2 params) | `clearing: false` default; `raytrace_max_range` 3.0 < `obstacle_max_range` 3.5 | Amplifier: makes every share above permanent | Necessary for persistence: with clearing on (raytrace 3.5 m) every VM closure replays to 0, and run 2 to a 2-column transient, then 0 |
| Legitimate geometry (half-cell faces) | Faces at y = 0.925 / 1.475 fall in cells the static map rasterizes free | Run 2: **17 %**. VM: 12–55 cells per phase | **0** columns in every run and model |
| RTX range-noise tails | p95 5 cm range error, integrated over never-cleared scans | VM: 12–49 cells per phase; part of run 2's unreproduced 17 % | 0 alone; narrows the band by one more row |
| M1 heading noise at rest | std 0.002–0.011 rad, max 0.02–0.03 rad registration error | VM static: 8–32 cells | 0 at rest |
| Ground returns, pitch, beam spread | — | Not observed (5 / 198 / 0 of 288–360 k beams at rest) | — |

---

## Fix recommendation matrix (diagnosis only: none applied)

"Counterfactual closed cols" are replay results (`--replay --counterfactual`, `_analysis/*_counterfactual.txt`):

- Each re-projects the **recorded** scans through a re-implementation of the obstacle layer's per-scan clear-then-mark.
- Localizer variants re-derive `map -> odom` from the **recorded** M1 scene stream. Each scene becomes active at its arrival plus the 0.3 s future stamp. The as-is pairing re-derivation gives 13 / 7 / 9 against the observed 12 / 6 / 13.
- The run 2 column uses the recorded-TF forward model (shift 1.9 s). Run 2's M1 stream was not recorded at full rate, so localizer variants are "n/a" there.

These simulate the costmap logic; they are not Nav2 runs. Any chosen option needs a live re-validation.

| Option | Scope | Fixes | Counterfactual closed cols: VM fast rotation A s42 / B / A s43 (slow and static: 0 in every variant) | Run 2, at 18.07 / 24.43 / 37.8 | Re-validation cost (frozen v2 results touched) |
|---|---|---|---|---|---|
| As configured | — | — | 13 / 6 / 13 | 10 / 10 / 17 | — |
| **A.** Localizer: odom lookup at the M1 scene stamp (TF buffer) instead of `Time()` | M1 shared node | The pairing part only | **7 / 0 / 9** | n/a | **All live-Nav2 results.** `map -> odom` also rotates the global path handed to DWB. Touches the `free_flow_v1` table (frozen today), the v1 head-on family, T1 / T2b / T3a / T3b / T3c, B2 / B3, the IB10 composite / junction step-7b PASS, and the loop family. M5 arrival checks (M1 positions) and GT scoring do not change. Offline artifacts (capability-probe manifest, battery-v2 frames, presentation-order probe) are untouched unless re-harvested. |
| **A′** (new). A plus compensation of M1's own upstream latency: look odom up at the stamp minus the measured M1 latency, or fix the camera / scene stamping upstream | M1 shared node (and possibly the camera stamp path) | Both lag parts | Bound (perfect-timing localizer, `map -> odom` fixed at spawn): **0 / 0 / 0**. M1 noise at rest adds only 8–32 non-closing cells | n/a | Same as A; a stamping fix upstream would also shift every M1-stamp-based log |
| **B.** Low-pass / rate-limit the yaw correction, or hold it while \|ω\| is large | M1 shared node | Bounds both parts and the noise | Not simulated; a hold during rotation tends toward the A′ bound | n/a | Same as A |
| **C.** Global `obstacle_max_range` 2.5 / 2.0 (or obstacle layer off globally) | Shared Nav2 param | Long lever arm only | 2.5 m: 0 / **6** / 0. 2.0 m: 0 / **6** / 0. B's aisle is within 2 m | 2.5 m: 0 / 0 / **17**. 2.0 m: 0 / 0 / **17**. Fails once the robot reaches the aisle mouth | All live-Nav2 results. T3a / T3b blockers would be first marked later or, with the layer off, only locally |
| **H** (new). `clearing: true`, `raytrace_max_range` ≥ `obstacle_max_range` (3.5) | Shared Nav2 param, global (and arguably local) | The amplifier: mis-registered marks are raytraced away by later correct scans | Raytrace 3.5: **0 / 0 / 0**. Raytrace 3.0 (default): 6 / 0 / 7 | Raytrace 3.5: 2 / 0 / 0. Raytrace 3.0: 9 / 0 / 0 | All live-Nav2 results, and **plausibly the largest behaviour change** (inferred from `clearing: false`, not measured here). Today a removed timed blocker, and every other robot's lidar trail, should stay lethal in the global costmap until a recovery clear. Every multi-robot result (head-on, T-family, B2 / B3, IB10) and every transient-blocker scene (`loop_detour_transient`, T3c) may currently depend on that persistence |
| **A + H** | Both shared | Pairing plus amplifier | **0 / 0 / 0** | n/a | Union of A and H |
| **D.** Lower `max_vel_theta` / RotateToGoal speed | Shared Nav2 param | Rotation spikes only | Not simulated; slow rotation (0.15 rad/s) closed 0 in every run | The weave term remains, so the onset remains | All live-Nav2 results, including every rotation's timing and the free-flow arrival rotations |
| **E.** Any of C / D / H scoped to the loop family (per-scenario params file) | fc_launch plumbing, default-off | Same as the chosen option, loop scenes only | Same as the chosen option | Same as the chosen option | No other scene, but a protocol ruling is needed: loop-family numbers would come from a different Nav2 configuration than every other family |
| **F.** M4: waypoint yaw = bearing to the next waypoint, or `navigate_through_poses` | M4 `follow_waypoints` only | The stop-and-rotate at WP0 | n/a | Does not touch the 18.07 onset, which happens in the primary aisle before any waypoint | Loop reroute results only. **Cannot fix alone** |
| **G.** Waypoint geometry (WP0 elsewhere) | M3 / overlay | Moves the rotation spike | n/a | Same as F | Loop reroute results only. Hides the defect |
| **I** (new). Rasterize the boundary half-cells occupied, or snap the loop-map faces to cell boundaries | Map generator (`rasterize_loop_map`, loop maps only) | Makes the legitimate narrowing explicit in the static map | No closure change (geometry closes 0 alone) | 0 | Loop-family maps only. **Not recommended as a fix**: the narrowing is real geometry |

**Reading the matrix.**

- Closure needs the registration error **and** the never-clearing layer; removing either removes it.
- **A alone is insufficient** (7 / 0 / 9), because M1's own 0.04–0.20 s upstream latency remains. Only the perfect-timing bound (A′) reaches 0 with clearing off.
- **H with raytrace 3.5 m** zeroes every VM case and leaves run 2 a 2-column transient at the onset. It has the widest likely behavioural blast radius.
- **A + H**, or **A′**, covers the source.
- **E scoping H to the loop family** is the narrowest change that fixes the loop family, at the cost of a protocol ruling.

---

## Secondary observations

- **Local costmap `clearing: false` as well.** Rolling-window marks persist until they scroll off. Untested candidate for the DWB corner local minimum.
- **GT log clock offset (+0.300 s vs ROS stamps).** Any project analysis that compares ROS-stamped data (M1 scene stamps, odometry, TF) with `ground_truth.jsonl` at equal numeric times is biased by ω × 0.3 s in heading and v × 0.3 s in position. M1's arrival-gate distances use M1 positions only and are unaffected; position-vs-GT checks at speed (for example the y-extent probe's M1 bias numbers) may carry about 0.045 m along the motion at 0.15 m/s. Not audited here.
- **Commanded vs actual yaw rate.** Raw `cmd_vel` of 1.0 / 0.3 rad/s produced 0.81 / 0.15 rad/s in sim. Not chased.
- **RTX dropouts.** 18–29 of 360 beams per scan return `-1.0` where geometry exists within 0.6–2 m. They cannot mark, and under H they would not clear either.
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
| `scripts/costmap_source_analysis.py` | Forward models (`gt` / `lag` / `recorded`), bag replay attribution, GT re-timing, localizer re-derivation, counterfactuals | `681f5c6`, `83cef79`, `f6bc0b0`, `db40763`, `c568964` |
| `tests/unit/test_apparatus_overlay.py` | +2 pins: the probe scenes set only robot_1's goal | `681f5c6` |

Reproduce the analysis with:

```bash
P=.venv/bin/python; D=data/logs/vm_runs
$P scripts/costmap_source_analysis.py $D/waypoints_validation/wp_fwd_s43 --model recorded --tf-shift 1.9 --show 18.067
$P scripts/costmap_source_analysis.py $D/waypoints_validation/wp_fwd_s43 --model gt
$P scripts/costmap_source_analysis.py $D/waypoints_validation/wp_fwd_s43 --counterfactual --model recorded --tf-shift 1.9
$P scripts/costmap_source_analysis.py $D/costmap_probe/cp_a_s42 --replay
$P scripts/costmap_source_analysis.py $D/costmap_probe/cp_a_s42 --replay --counterfactual
```

---

## Verification

- **Local suite.** `pytest -q --continue-on-collection-errors -p no:cacheprovider -rfE`, one venv. A clean detached worktree at `62c01ac` (removed afterwards) and the branch both give 63 failed / 153 skipped / 3 errors. Passed: 5115 → 5117, the +2 being the new overlay pins. The failing and erroring name sets are identical (`diff` empty). `ruff check` is clean on every new or changed file.
- **Deploy (delta).** The VM tree sat at `46492d6`. Only the files changed since then were shipped:
  - docs and the probe tooling;
  - nothing under `ros2_ws/src`, so no colcon rebuild was needed and no module was deleted (the build-cache purge was not applicable).

  The method was `git archive` of exactly that file list, then `tar -xzmf`, then `touch`. The md5 of every shipped file equals the local file. The exporter fix was re-shipped the same way. After the final commit, the tip's delta was re-shipped and re-verified by md5.
- **Per run.** Each run passed:
  - the `pgrep -f run_simulation`-empty gate (0 s wait each time);
  - `GATE OK: logs saved to present`;
  - M5 confirmed started (arrival line in `m5.log`);
  - `RESTORE OK`, with source and installed `orchestrator.yaml` at `1f656533…` and `rag.yaml` at `e18c723c…`;
  - the bag stopped by SIGINT before fc_launch's container restart (`Recording stopped`), then exported and copied out.

  Run A s42's in-run export failed on a marker-key collision. It was re-exported from the host-copied bag after the fix, so no data was lost.
- **VM at close-out.** `pgrep` for Isaac, fc_launch and `isaac.scripts` is empty. The GPU is at 0 % / 171 MiB, and there is no bag or probe process in the container. The VM is left running and idle, as found.

---

## References

- Predecessor: `docs/reports/2026-10-05-follow-waypoints-validation.md` (Rev 2). Its `_analysis/` scripts are in `data/logs/vm_runs/waypoints_validation/_analysis/`; note the GT offset correction above.
- Run bundles: `data/logs/vm_runs/costmap_probe/{cp_a_s42,cp_b_s42,cp_a_s43}/`. Each holds `bag/`, `export.jsonl`, `phases.jsonl`, `params.txt`, `gt/` and the logs.
- Analysis outputs: `data/logs/vm_runs/costmap_probe/_analysis/`:
  - `*_replay.{txt,json}`;
  - `*_counterfactual.txt`;
  - `rotation_timelines.txt`;
  - `wp_fwd_s43_model_{gt,lag048,recorded_*}.json`;
  - `wp_fwd_s43_counterfactual.txt`.
- Config: `ros2_ws/src/swarm_simulation/config/nav2_params.yaml` (`local_costmap` / `global_costmap` `obstacle_layer`).
- Localizer: `ros2_ws/src/swarm_perception/swarm_perception/camera_localizer_node.py` (`_lookup_odom_pose`, `_publish_map_to_odom` future stamp) and `camera_localizer.py`.
- Geometry: `isaac/vgu_sim/scenario_builder.py` (`_author_loop_connectors`), `isaac/scripts/generate_warehouse_map.py` (`rasterize_loop_map`).
- Upstream default: ros-navigation/navigation2 `jazzy`, `nav2_costmap_2d/plugins/obstacle_layer.cpp` (`clearing` default `false`).

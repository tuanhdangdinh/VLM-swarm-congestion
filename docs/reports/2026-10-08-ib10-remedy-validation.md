# IB10 Release-Lane Remedy: VM Validation Arm

**Prepared:** 2026-10-08

**Revision history:**

- Initial draft: merge of `feat/v3-release-fix@7f0f002` into `feat/v3-integration` (`56a6658`), then the VM validation arm from `2026-10-08-ib10-lead-flip-diagnosis.md` §5(d). That covers 4 baseline runs (remedy off) and 4 remedy runs (pull-off 0.33 / side −1 / floor 0.20), all with the first IB10 costmap, plan and scan bags. Mock backend only, zero API.

---

## Summary

| Question | Answer |
|---|---|
| Merge | `56a6658` (`chore: merge v3 IB10 release-lane remedy into v3 integration`). The tree equals `7f0f002`. Full suite: 62 failed + 3 collection errors = **65 ids, identical** to `v3int_m5.fail`; **5836 passed** (5777 + 59 tests added by the merged branch), 153 skipped. |
| Is the release defect lead-agnostic on `56a6658` with the remedy off? | **Yes.** 4 / 4 baseline runs contacted under **both** leads: robot_4 ×3 at 0.082 / 0.085 / 0.093 m GT centre distance, robot_3 ×1 at 0.077 m. Each run pushed the held robot 0.56–0.64 m and latched until the episode end, with 1 / 4 M5 arrivals. The fix-branch robot_3 near miss (0.191 m) was not a robot_3 property. |
| Mechanism (first IB10 costmap bags) | **Confirmed, with a scan-dropout component the diagnosis did not have.** The held robot appears in the lead's costmaps as a lethal blob only 0.15–0.20 m wide in x (its LDS head plus inflation). It then **drops out of the lead's `/scan` at 0.32–0.35 m centre distance** in all 4 runs. The clearing costmap erases it (global blob gone at 0.12–0.32 m), and the lead's plan collapses onto the held robot: the planned lateral offset fell from 0.19–0.27 m at the 1.0 m gap to 0.00–0.14 m at the 0.2 m gap. |
| Does the remedy make the release lead-agnostic? | **Not demonstrated.** All 4 remedy runs were **robot_4-led**. The 3 runs that reached the pass resolved cleanly: 4 / 4 arrivals, outcome rank (1, 4, 4), closest pass 0.386 / 0.435 / 0.436 m GT, floor silent, receder released on `clearance`. **A robot_3-led release under the remedy was never observed.** robot_3 led 1 of 8 runs on this tree (1 of 10 across v3), not the ~50 / 50 the diagnosis assumed. Robot_3 is the lead that matters for the −x side check. |
| Rule C | **Fired on remedy run 4, the last scheduled run.** The contact was **not** the remedy pair: the lead/held minimum was 0.551 m and the lead never reached the held robot. The yielder robot_1 left its release hold and drove into the junction, where it met the lead at **0.138 m GT** (contact). The floor latched robot_1+robot_4 at M1 0.200, but the /tf join puts the latch at TF 0.175–0.136 m, i.e. at or after contact. The junction then froze: 1 / 4 arrivals, held receder released on `hold_timer`. Cause: a cross→release handoff race, an orphaned Nav2 `FollowPath` after a cancel (section 5). Its precursor (a late second `resume base mission`) is pre-existing, in 9 of 10 IB10 bundles; the orphan itself occurred once, in a remedy run, so a remedy contribution to handoff timing is not excluded at n = 1. |
| Did 0.33 / −x / 0.20 survive? | **0.33:** yes for robot_4 leads; do not raise it (11–23 mm left to the wall-safe bound). **−x:** sign mapping confirmed live; unfalsified for robot_4 leads, **untested for robot_3 leads**. **0.20:** silent in all 3 clean passes (M1 ≥ 0.387 m), but in its one true positive it fired **at or after** contact at about 0.3 m/s closing speed, then froze the pair. It is not a contact preventer. Numbers in section 6. |

---

## 1. Merge (Part 1)

- `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v3`, `feat/v3-integration@19a1859` + `feat/v3-release-fix@7f0f002`, which was branched from `19a1859`. The merge is `git merge --no-ff`. Commit `56a6658` has a subject-only message (no body, no trailers), and `git diff 7f0f002 56a6658` is empty.
- Suite: `pytest -q -rfE -p no:cacheprovider --continue-on-collection-errors` under the main checkout's `.venv`, with `--continue-on-collection-errors` as the `v3int_m5` baseline used. Output: `62 failed, 5836 passed, 153 skipped, 3 errors`. The sorted FAILED / ERROR id list (`/private/tmp/claude-501/v3int_m6.fail`) equals `v3int_m5.fail` exactly (65 ids, `diff` empty).
- No stash was used, and no other worktree or `implementation_notes.md` was touched.

---

## 2. Method

### Deploy (`071f9c1` → `56a6658`)

| Item | Value |
|---|---|
| VM | `vgu-vgu-thule-base-isaac-workstation-vm` (us-central1-c), Isaac Sim 6.0.1, container `vgu_ros` |
| Pre-state | `md5sum -c` of the step-0 `071f9c1` 868-file manifest: only `orchestrator.yaml` FAILED (pinned) |
| Ship | All 36 files of `git diff --name-only 071f9c1 56a6658` except `orchestrator.yaml` (19 modified, 17 new), from `git archive 56a6658`, copied in and `touch`ed. Backup is `deploy/backup/mod_files.tar`. No rsync and no `--delete`. |
| Rebuild | **Purge + rebuild** of `swarm_orchestrator` and `swarm_execution` (`build/`, site-packages, egg-info and `share/` removed), plus a plain rebuild of `swarm_simulation` to install the two new S6 map files. `nav2_params.yaml` (`cbc33745`) and `nav2_robot.launch.py` (`9cf43a58`) are unchanged. |
| Installed verification | 35 installed files md5-equal to source; 0 mismatches and 0 orphans. Container view of the live-mounted M3 files is equal. |
| Key installed md5 | `command_bus_node.py` `6807c9f0`, `crossing_chain.py` `54ea180f`, `safety.py` `fe39e93e`, `safety_monitor_node.py` `bc345e40`, `command_grounder.py` `9c2e5b09` (live), `scene_geometry.py` `94bf2e37` (live), `maneuver_geometry.py` `c098de18` (live), `safety.yaml` `59839662` |
| Tree identity | `md5sum -c` against the 885-file `56a6658` manifest: only `orchestrator.yaml` FAILED (VM-pinned `1f656533`, src and installed) |
| Config load (offline, under `56a6658`) | Pinned `1f656533`, base overlay `35734f4e` and remedy overlay `0d0cfbfa` all load. All give `plan_dispatch_order_source=chi`, `task_stream.enabled=False` and `dispatch_enabled=True`, so the S1 / S6 code is deployed but off. Offline re-grounding of v3 `ib10_s42` (robot_4 lead) and fix `ib10_s42` (robot_3 lead) under the remedy overlay gives the held receder `pull_off_lateral_m` +0.33 (robot_3) / −0.33 (robot_4), both mapping to world −x, plus `passer_reference_at_dispatch: true` and robot_1 `crossing_clear_m [2.65, 2.076]`. |

### Conditions

| | Baseline (A) | Remedy (B) |
|---|---|---|
| Overlay | `35734f4e` (the step-0 IB10 overlay) | `0d0cfbfa` = `35734f4e` + `junction_release_pull_off_m: 0.33`, `junction_release_pull_off_side: -1` (the only diff) |
| `safety.yaml` (install-wide) | pristine `59839662` (`hard_contact_floor_m: 0.0`) | `c41913f0` (`hard_contact_floor_m: 0.20`), swapped in by `swap_safety.sh` (plain `cp` + `touch`, purge, rebuild, md5 of src and installed) and restored afterwards |
| Common | scenario `intersection_bottleneck`, mock `intersection_junction_clear_vlm_verbatim_once.json`, `REC_SEC=1400`, `SIM_SEC=1800`, seed label 42, `orchestrator.yaml` pinned `1f656533` | same |

### Driver gates (`run_wave.sh`, every run)

- `pgrep -f '[r]un_simulation'` drain before each run.
- Overlay md5 check, plus `safety.yaml` md5 on **src and installed**, before each run.
- `v2_final_run.sh`, with its own pristine refusal, fresh-mtime restore, rebuild and `RESTORE OK`.
- A gate on M4's startup line `hard_contact_floor_m=` (0.0 baseline, 0.2 remedy).
- `NOTES.md` line per run.
- Stop when both leads have appeared, at 4 runs, or (remedy) on any `hard_contact_floor` latch or GT lead/held contact.

### Bags

- `/robot_{3,4}/{local,global}_costmap/{costmap,costmap_updates}`, `/robot_{3,4}/plan`, `/robot_{3,4}/scan`, `/robot_{3,4}/odom`, `/tf`, `/tf_static` (mcap).
- Recording ran for 900 s from Nav2-live, which covers sim ≈ 18–257.
- All 16 topics were non-empty in every bag. The bag spans every held-robot gate release except m4's `hold_timer` release (237.8 vs bag end 225.9), which came after the frozen contact.
- Poses for the bag metrics come from the bag's own `/tf` (`map → rN/odom → rN/base_footprint`), so they are same-clock, with no GT join.

### Scoring

- GT geometry is GT-internal. M4 `sim_t` only bounds windows, with ≥ 1 s margins.
- Contacts are distance-based (< 0.18 m centre), never `robot_robot_contacts` (trap 20).
- Arrivals count both M5 acceptance strings. The committed `coverage_scene_scores.py ib10 --allow-mock` gives the scorer arrivals and `outcome_rank`.
- Analysis scripts are gitignored, in `data/logs/vm_runs/ib10_remedy/_analysis/` and `_vm_driver/`.

---

## 3. Phase A: Baseline (Remedy Off)

Both leads appeared by run 4.

| Run (stamp) | Lead | χ r3 / r4 (margin) | GT min centre (t) | M1 min | Lead − held x at gap 0.6 / 0.4 / 0.2 m | Held pushed during hold | Held gate release (admit → release) | Arrivals M5 / scorer | `outcome_rank` |
|---|---|---|---|---|---|---|---|---|---|
| b1 (`20261007_135750`) | robot_4 | 0.980 / 0.972 (0.008) | **0.082** (131.5) | 0.147 | +0.010 / +0.039 / +0.073 | 0.564 m | `clearance` 144.5 (41.4 s) | 1 / 1 | (0, 3, 1) |
| b2 (`20261007_142134`) | robot_4 | 0.930 / 0.924 (0.006) | **0.085** (131.4) | 0.128 | +0.100 / +0.096 / +0.101 | 0.562 m | `clearance` 151.2 (46.6 s) | 1 / 1 | (0, 3, 1) |
| b3 (`20261007_144355`) | robot_4 | 0.971 / 0.843 (0.128) | **0.093** (126.0) | 0.128 | +0.136 / +0.143 / +0.147 | 0.638 m | `clearance` 168.3 (64.6 s) | 1 / 1 | (0, 3, 1) |
| b4 (`20261007_150614`) | **robot_3** | 0.855 / 0.856 (0.001) | **0.077** (130.3) | 0.119 | −0.054 / −0.010 / +0.026 | 0.568 m | `clearance` 131.2 (29.8 s) | 1 / 2 | (0, 3, 2) |

- Every run formed a valid jam (onset 33.2–35.5 s) and executed χ = proposed = dispatched order (`vlm_verbatim`, `dispatch_order_source: chi`).
- Every run ended the same way as step-0 `ib10_s42`: the lead pushed the held receder inside the release exemption until its 2.65 m odometry gate cleared, then the min-distance latch held both robots to the episode end (73,558–93,290 `min_distance_violation` lines).
- b4's lead (robot_3) reached its goal in GT (scorer arrival 104.8 s after t0), but M5 never accepted it once latched.
- **The baseline defect is lead-agnostic on this tree.** With a robot_3 lead (b4) it contacted at 0.077 m, the tightest of all. That rules out "robot_3 leads pass" (fix_s42's 0.191 m was a draw).

---

## 4. The Pass in the Lead's Costmaps, Plan and Scan

First IB10 costmap evidence (diagnosis §4 gap). Taken from the lead's bag on the approach, at the first sample where the along-arm gap |Δy| ≤ g. "Blob" is the set of cost ≥ 99 cells within 0.22 m of the held robot's centre, given as an x-extent relative to that centre. In remedy runs the −x edge of the blob is the aisle wall.

| Run | Global-costmap blob x-extent at the 0.6 m gap | Lead's plan x (rel. held) where it crosses held y, at gap 1.0 / 0.6 / 0.4 / 0.2 | Lead's actual x (rel. held) at the same gaps | Held robot's last scan return / first scan without it (centre distance) | Held blob gone from global / local costmap at centre |
|---|---|---|---|---|---|
| b1 | −0.083 … +0.117 | 0.225 / 0.222 / 0.170 / 0.095 | −0.008 / +0.009 / +0.038 / +0.072 | 0.335 / 0.322 | 0.129 / 0.132 |
| b2 | −0.078 … +0.072 | 0.234 / 0.229 / 0.178 / 0.102 | +0.112 / +0.100 / +0.097 / +0.103 | 0.348 / 0.337 | 0.122 / 0.193 |
| b3 | −0.079 … +0.071 | 0.271 / 0.262 / 0.178 / 0.143 | +0.128 / +0.138 / +0.144 / +0.147 | 0.350 / 0.335 | 0.216 / 0.245 |
| b4 (robot_3 lead) | −0.075 … +0.075 | 0.185 / 0.185 / 0.166 / **0.000** | −0.147 / −0.049 / −0.010 / +0.023 | 0.366 / 0.351 | 0.321 / 0.325 |
| m1 | wall … +0.117 | 0.621 / 0.552 / 0.392 / 0.394 | +0.341 / +0.360 / +0.379 / +0.385 | never lost (last at 0.385) | never |
| m2 | wall … +0.126 | 0.548 / 0.584 / 0.445 / 0.450 | +0.263 / +0.396 / +0.431 / +0.443 | never lost (last at 0.434) | never |
| m3 | wall … +0.118 | 0.603 / 0.625 / 0.440 / 0.442 | +0.393 / +0.439 / +0.453 / +0.447 | never lost (last at 0.437) | never |

**Reading.**

1. **The planner sees only the LDS head.** Before dropout, the held robot's lethal footprint is 0.15–0.20 m wide in x. That is the 7 cm head plus local 0.07 / global 0.10 inflation, narrower than the 0.18 m side-by-side contact separation. This confirms the diagnosis's lidar-plane hypothesis directly.
2. **New: the held robot drops out of the lead's scan at 0.32–0.35 m centre distance**, in 4 / 4 baseline runs. In b1 the raw scan's last return from it was at 0.40 m lidar range (sim 115.7); from 115.9 there is no return within ±40° closer than 0.69 m. The scan message reports `range_min` 0.12 m, so the cause of this blind band is **not established**.
   - `clearing: true` (fix H) then raytraces the cells away. The plan, which still held 0.19–0.27 m at the 1.0 m gap, collapses to 0.00–0.14 m, and the lead drives through.
   - This is the "no close-range reaction" the diagnosis asked the bag to explain. It also explains why post-fix passes are flat: the costmap loses the robot exactly when it matters.
3. **Under the remedy the pass happens above the dropout band.** The held robot sits at x ≈ −0.34 and the lead stays at x ≈ +0.04…+0.11, so the closest approach is 0.386–0.437 m. The held robot never leaves the scan or the costmap, and the plan keeps 0.39–0.45 m.
   - **m1's margin over the dropout band is small:** it passed at 0.386 m against a last-seen range of 0.335–0.366 m in the baseline runs.

---

## 5. Phase B: Remedy On (Pull-Off 0.33, Side −1, Floor 0.20)

| Run (stamp) | Lead | χ r3 / r4 (margin) | Seed at dispatch (sim) | Hold start (pull-off took) | Held Δx (pulled side) | Lead/held GT min (t), lead side | M1 min (lead/held) | Lead − held x at gap 0.6 / 0.4 / 0.2 | Held release | robot_1 release | Floor lines | All-pairs GT min | Arrivals M5 / scorer | `outcome_rank` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| m1 (`20261007_154935`) | robot_4 | 1.012 / 0.956 (0.056) | 103.90 | 117.40 (13.5 s) | −0.347 (−x) | **0.386** (119.2), +x | 0.387 | +0.360 / +0.376 / +0.384 | `clearance` 122.5 | `clearance` 136.2 | 0 | 0.386 (r3+r4) | **4 / 4** | (1, 4, 4) |
| m2 (`20261007_160932`) | robot_4 | 0.972 / 0.904 (0.068) | 103.13 | 116.53 (13.4 s) | −0.345 (−x) | **0.435** (117.0), +x | 0.438 | +0.393 / +0.428 / +0.443 | `clearance` 120.8 | `clearance` 134.7 | 0 | 0.435 (r3+r4) | **4 / 4** | (1, 4, 4) |
| m3 (`20261007_162919`) | robot_4 | 0.986 / 0.971 (0.015) | 105.73 | 119.23 (13.5 s) | −0.349 (−x) | **0.436** (120.1), +x | 0.439 | +0.442 / +0.454 / +0.446 | `clearance` 123.5 | `clearance` 137.3 | 0 | 0.436 (r3+r4) | **4 / 4** | (1, 4, 4) |
| m4 (`20261007_164915`) | robot_4 | 0.979 / 0.947 (0.032) | 104.23 | 117.77 (13.5 s) | −0.345 (−x) | 0.551 (242.7): no pass | 0.604 | — (lead stopped at y = +0.14) | **`hold_timer` 237.8** | none | **2** (`robot_1+robot_4@0.200`) | **0.138 (r1+r4, 111.1)** | 1 / 1 | (0, 3, 1) |

- Every remedy run's artifact release phase carries `pull_off_lateral_m: 0.33` and `passer_reference_at_dispatch: true` on robot_3's yield, plus robot_1 `crossing_clear_m [2.65, 2.076]`.
- Every run logged `hard_contact_floor_m=0.2` at M4 startup and exactly one `crossing_chain reference_seeded … yielder=robot_3 passer=robot_4`.
- Arrival times after t0 in m1–m3:
  - robot_2 76.3–77.9, robot_4 97.0–99.2, robot_3 113.6–115.7, robot_1 128.2–129.6 s.
  - The fix-branch 4 / 4 had 77.2 / 97.8 / 114.1 / 128.4.
  - Remedy m1–m3 logged 11,289–16,341 `min_distance_violation` lines outside the release (the fix-branch 4 / 4 had 10,949).

**Acceptance per run (brief §B).**

| Criterion | m1 | m2 | m3 | m4 |
|---|---|---|---|---|
| Remedy evidence lines: `reference_seeded`; `pull_off_lateral_m` in the artifact's release phase; `hard_contact_floor_m=0.2` at startup | yes | yes | yes | yes |
| Receder released on `clearance` (not `hold_timer`) | yes (5.1 s after hold start) | yes (4.3 s) | yes (4.2 s) | **no (`hold_timer`)** |
| No floor latch during the pass | yes | yes | yes | **no** (latched on robot_1+robot_4) |
| Min pass separation ≥ ≈ 0.20 m, floor silent | 0.386 | 0.435 | 0.436 | n/a (no pass) |
| 4 / 4 arrivals | yes | yes | yes | **no (1 / 4)** |
| Pulled-off side vs lead pass side (falsification) | −x / +x: consistent | −x / +x | −x / +x | −x / no pass |

**Seed and gate.**

- The odometry reference was taken at dispatch in 4 / 4 runs.
- The lateral leg was complete before the lead reached the 0.6 m gap in every run: held Δx was already −0.345…−0.349 at that gap.
- The sidestep's final rotate and hold start came 13.4–13.5 s after dispatch, only 0.5–1.8 s before the lead's closest approach.
- The lead's gate cleared at 2.653–2.654 m from the seed, and robot_1's hypotenuse gate (2.076) cleared at 2.078–2.081 m.

### Run m4: Rule C

- **What happened.**
  - At sim 104.17 robot_1's cross-phase yield completed (`gate_release … junction-cross reason=clearance`). The coordination client logged `resume base mission robot=robot_1 goal=(1.75, 0.0)`.
  - The release-phase yield arrived 0.12 s later. It went ACTIVE, command_bus cancelled all goals (`goals_canceling=0`), and the gate admitted the lead (robot_4) at 104.267.
  - At +0.24 s **the client logged a second `resume base mission`**, followed by client cancel-alls (`goals_canceling=1`).
  - In `nav2_r1`, three `navigate_to_pose` goals each began and were cancelled. On the third, **`controller_server` logged "Received a goal, begin computing control effort" at …202.3876, and the BT goal was cancelled 36 ms later (…202.4237) with no controller-side cancel.** The orphaned `FollowPath` drove robot_1 at about 0.16 m/s from its parked pocket (−1.02, −0.375) into the junction.
  - robot_4 was crossing the junction southbound on its release. GT centre distance was 0.623 at 109.0, 0.258 at 110.5, 0.145 at 111.0 and **0.138 at 111.1**, a contact. Both robots stopped at 111.5.
- **The floor.**
  - The safety monitor latched both robots with `reason=hard_contact_floor … pairs=robot_1+robot_4@0.200`.
  - Joining the latch's wall stamp to sim through the bag's `/tf` (receive time vs header stamp; median of the 20 nearest odom→base_footprint transforms, ±0.2 s jitter) gives a latch at **sim 111.53 (111.3–111.75)**.
  - The TF centre distance at that time was 0.175–0.136 m (`remedy/ib10_remedy_r4/LATCH_JOIN.txt`). It fired on an M1 sample at 0.200 but, by the time it acted, the pair was already at or inside contact separation. The closing speed was about 0.30 m/s.
  - The pair never separated afterwards. robot_3's hold ran out (`hold_timer` 237.8), and only robot_2 arrived.
- **Not the remedy pair.**
  - robot_3 had pulled off to x = −0.337 and stayed there (held displacement 0.043 m).
  - The lead was stopped 1.2 m short of it.
  - The lead's scan saw robot_1 until 0.336 m centre distance and lost it at 0.310 m, the same dropout band as section 4 (`BAG_PASS_lead_vs_robot_1.json`).
- **Precursor pre-existing; remedy contribution not excluded.**
  - The second `resume base mission` after the release yield arrived (0.13–0.27 s later) is present in **9 of 10** IB10 bundles: b1–b4, m1, m3, m4 and step-0 `ib10_s42` / `_rep2`.
  - In every other run, robot_1 moved ≤ 0.008 m during the 25 s after its release admit. m4 is the only run where a `FollowPath` outlived the cancel.
  - The remedy changes neither robot_1's command shape (only its `crossing_clear_m`) nor the M5 phase timing. It does add work to command_bus on the same release dispatch (robot_3's seed odometry subscription). The orphan occurred in 1 / 4 remedy runs vs 0 / 6 non-remedy runs, so a remedy contribution to the handoff timing is **not excluded at n = 1**. The mechanism sits in the coordination client and Nav2.
- **Rule C was applied.** The driver halted the phase on the floor latch (`STOP rule C`). This coincided with the last scheduled run. No value was tuned.

---

## 6. Falsification Check and Step 6 Freeze Numbers

**Falsification (−x rule).**

- **Pulled-off side:** −x in 4 / 4 (Δx −0.345…−0.349, measured from GT, not assumed). This confirms live M4's left-positive sidestep convention: robot_3, facing north, was commanded +0.33 and moved to world −x.
- **Lead pass side:** +x in 3 / 3 complete passes (lead − held x +0.386…+0.436 at closest approach). m4 had no pass. **No run falsified −x.**
- **The test is one-sided.** Every remedy lead was robot_4. The robot_3 lead is the risky case: fix_s42's robot_3 lead passed on −x (−0.121 → −0.190), and b4's robot_3 lead approached from x = −0.147 at the 1.0 m gap. With the held robot at −0.34, such a lead would have about 0.19 m of lateral room, near the scan-dropout band.

**Freeze numbers (Step 6).**

| Parameter | Proposed | Measured on the VM | Status |
|---|---|---|---|
| `junction_release_pull_off_m` | 0.33 | Held Δx −0.345…−0.349 (overshoot +15…19 mm); held x at hold −0.337…−0.349 against the wall-safe bound −0.36 (`aisle_half_width_m` 0.6 − `half_width_m` 0.09 − `wall_margin_m` 0.15). **11–23 mm left to the bound.** Pull-off-to-hold 13.4–13.5 s. | Survived (robot_4 leads). Do not raise. |
| `junction_release_pull_off_side` | −1 | Sign mapping correct live; lead passed +x 3 / 3 | Unfalsified for robot_4 leads; **robot_3 leads untested** |
| `hard_contact_floor_m` | 0.20 | Silent in 3 clean passes (M1 lead/held min 0.387–0.439; no other pair below 0.20). One true positive (m4) latched at M1 0.200, when the TF distance was already 0.175–0.136 m, and the GT pair stopped at 0.138. | Silent as designed, but **not protective at ~0.3 m/s closing**. Once latched, an inseparable pair freezes permanently. |
| `passer_reference_at_dispatch` | on with pull-off | Seeded at dispatch 4 / 4; lead gate 2.653–2.654 m | Works |
| robot_1 hypotenuse `crossing_clear_m` | 2.076 | Cleared at 2.078–2.081 m, 13.7–13.9 s after the held receder's release | Works |
| Predicted pass separation | ≥ 0.33 − 0.118 − 0.011 ≈ 0.20 m | **0.386–0.436 m** (GT), 0.387–0.439 (M1) | The prediction assumed the baseline skim. Under the remedy the held robot stays visible and the planner keeps ~0.4 m. |

---

## 7. Verdict

1. **The release defect is lead-agnostic on `56a6658`.** 4 / 4 baseline contacts, robot_3 lead included (0.077 m). The bag shows why: the held robot is only a 0.15–0.20 m LDS-head blob, then drops out of the lead's scan at 0.32–0.35 m, the clearing costmap erases it, and the plan runs through it.
2. **The remedy fixes robot_4-led releases.** In 3 / 3 complete passes the held robot pulled off to −x, the lead passed on +x at 0.386–0.436 m (above the dropout band), the floor stayed silent, both gates released on clearance, and the episode resolved 4 / 4 with fix-branch arrival times.
3. **Lead-agnostic remedy: not demonstrated.** No robot_3-led remedy run occurred (robot_3 led 1 / 8 here, 1 / 10 on v3). That is the falsification-relevant direction.
4. **One remedy-phase failure (m4), attributed to a cross→release handoff race.** An orphaned Nav2 `FollowPath` drove the held yielder (robot_1) into the lead. The precursor is pre-existing (9 / 10 bundles); a remedy contribution to the handoff timing is not excluded at n = 1. The 0.20 floor latched only at or after contact and froze the junction.

---

## 8. Deviations

1. **`orchestrator.yaml` kept at the VM-pinned `1f656533`**, as in step 0. Both overlays load under `56a6658` with model defaults (offline check).
2. **The baseline is `56a6658` with the remedy off, not `071f9c1`.** The S1 task-stream / S6 code merged since step 0 is deployed but disabled (`task_stream.enabled=False`, `dispatch_enabled=True`).
3. **Plain rebuild of `swarm_simulation`** to install the S6 maps. Its Nav2 files have unchanged md5s.
4. **Two voided remedy attempts** (`remedy/VOID_*`, `VOID2_*`), both Nav2 bring-up aborts:
   - **Attempt 1:** robot_1 `planner_server` `change_state` response timeout. Its bring-up overlapped an in-container bag analysis.
   - **Attempt 2:** robot_2 `controller_server` bond timeout after 4 s (`NAV2_BRINGUP_FAILED`).
   - In both, no M4 or M5 process started. `GATE OK` printed anyway (trap 16a), and the driver's floor-line gate caught it.
   - The wrapper's bag subshell was killed by PID so the wrapper could restore (`RESTORE OK`), and a bag watchdog was added. After that, no container work was done during bring-up.
5. **Bag topics extended** with `/robot_{3,4}/odom`, `/tf` and `/tf_static`, beyond the diagnosis list, to get same-clock poses (fixing the step-0 "assumed odom→map shift" caveat).
6. **Driver stop rule (remedy):** its contact check covered the lead/held pair only. m4's robot_1+robot_4 contact was caught by the floor-latch arm of rule C. All-pairs GT minima are reported in section 5.
7. **Run budget:** 8 scored runs, 2 voids and deploy overhead, about 3 h 20 min of VM time.

---

## 9. Open Questions (Coordinator Rulings)

1. **robot_3-led remedy validation.**
   - At the observed robot_3-lead rate of 1 / 8, P(≥ 1 robot_3 lead) is 66 % in 8 runs, 77 % in 11 and 90 % in 17. At 1 / 10 those figures are 57 %, 69 % and 83 %.
   - The lead cannot be forced (χ rank 0 of the live jam).
   - Fund more remedy replicates, or rule on a way to bias departure stagger. The diagnosis correlates the lead with the later departer.
2. **The cross→release handoff race (M4 coordination client / Nav2 orphaned `FollowPath`).**
   - It is pre-existing, with its precursor in 9 / 10 bundles, and it bit once in 10.
   - Its precursor predates the remedy, and any v3 IB10 cell inherits it. Whether the remedy's extra release-dispatch work (the seed subscription) shifts the race's odds is not established at n = 1.
   - It needs a fix ticket. Candidates are making the client drop a late `resume base mission` while a new command is ACTIVE, and cancelling `FollowPath` on the controller server as well as the BT goal.
3. **The floor's role.**
   - 0.20 on M1 poses fires too late to prevent a 0.3 m/s closing contact, and a latched contact pair can never separate.
   - Rule whether the floor is meant as a push limiter (it would have stopped the 28 s pushes in b1–b4) or a contact preventer, which would need a larger value or a speed-aware margin.
4. **The scan blind band at 0.32–0.35 m.**
   - Its cause (RTX lidar config vs the 0.12 m `range_min` in the message) is not established.
   - It bounds any pass-geometry remedy from below. Remedy passes cleared it by only 0.02–0.10 m.

---

## 10. VM End State

- **`safety.yaml`:** restored pristine via `swap_safety.sh MODE=pristine`; src = installed = `59839662` (`SWAP OK`).
- **Tree:** `md5sum -c` against the 885-file `56a6658` manifest gives only `orchestrator.yaml` FAILED (pinned `1f656533`, src and installed). Installed `swarm_execution` / `swarm_orchestrator` `.py` equal source (0 mismatches).
- **Processes and resources:** no `run_simulation`, `fc_launch`, driver, watchdog or bag processes. GPU 0 %, 171 MiB; `vgu_ros` up.
- **Leftovers:** no GT leftover from this wave; the 18 pre-existing ones remain. Left alone: an unrelated host loop from 2026-09-24 (PID 58079), `/home/ubuntu/gpt56_sol_swap/` and `/home/ubuntu/shutdown_timing_probe/`.
- **Notes:** `/home/ubuntu/v3_ib10rv/NOTES.md`.
- **Billing:** the VM is **still RUNNING and billing**; it was not stopped.

---

## Evidence and Files

- **Wave dir (VM):** `/home/ubuntu/v3_ib10rv/`: `base/`, `remedy/`, `deploy/` (ship list, md5s, `deploy3.log`, backup), `overlays/` (`ib10_base_orchestrator.yaml` `35734f4e`, `ib10_remedy_orchestrator.yaml` `0d0cfbfa`, `safety_floor020.yaml` `c41913f0`), `run_wave.sh`, `swap_safety.sh`, `chain_remedy.sh`, `bag_watchdog.sh`, `NOTES.md`.
- **Local copy (gitignored):** `data/logs/vm_runs/ib10_remedy/` in this worktree, with `base/`, `remedy/`, `_vm_driver/` and `_analysis/`:
  - `ib10_rv_analyze.py`: GT / M1 / M4 metrics.
  - `bag_pass_summary.py`, plus `_vm_driver/bag_pass.py`: in-container costmap / plan / scan pass analysis.
  - `_vm_driver/latch_join.py`, `race_scan.py`, `scan_probe.py`.
- **Per-run files:** `QUICK.json`, `ib10_score.json`, `BAG_PASS_r022.json` (0.22 m blob radius) and `bag_info.txt`.

**Bags index** (mcap, `bag/` in each run dir; 16 topics, 0 empty):

| Run | Stamp | Size | Messages | Duration |
|---|---|---|---|---|
| b1 | `20261007_135750` | 37 MB | 58,204 | 895 s |
| b2 | `20261007_142134` | 35 MB | 59,908 | 887 s |
| b3 | `20261007_144355` | 36 MB | 61,384 | 897 s |
| b4 | `20261007_150614` | 36 MB | 56,451 | 887 s |
| m1 | `20261007_154935` | 38 MB | 66,564 | 895 s |
| m2 | `20261007_160932` | 39 MB | 68,145 | 897 s |
| m3 | `20261007_162919` | 39 MB | 67,283 | 897 s |
| m4 | `20261007_164915` | 36 MB | 59,175 | 897 s |

- **Related:**
  - `docs/reports/2026-10-08-ib10-lead-flip-diagnosis.md`: the arm spec (§5(d)) and §4 pass geometry.
  - `docs/reports/2026-10-08-v3-step0-rebaseline.md`: Stage 4.
  - Remedy commits `306a0d2` (pull-off), `1507ec5` (floor), `7f0f002`, merge `56a6658`.

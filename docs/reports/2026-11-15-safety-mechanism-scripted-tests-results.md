# Safety-Mechanism Scripted Tests: Results

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: Phase 0–3 results of the registered scripted safety-test session (two takes, one VM session).

---

## Scope and Label

- **SAFETY TEST, n = 1 per mechanism.** The decisions are SCRIPTED (mock backend, `config/mock_decisions/sft_reverse_r5_r3_r1_once.json`) to force the tested situation. This is not a demo, not VLM behaviour and not experiment evidence. Never pool it.
- **Registration:** `docs/superpowers/specs/2026-11-15-safety-mechanism-scripted-tests.md` (`b000103`, committed before the VM started). The criteria below are that file's, evaluated by `verdict_sft.py` (md5 `21151463`, unchanged since registration).
- **Tree:** `test/safety-mechanisms-scripted` (v7s) = `a412949` + `fix/escort-obstacle-guard` `92158d3` (merge `527707a`) + `fix/m4-stall-abort` `1016e0b` (merge `af5a9df`) + test inputs `99edbf3`.
- **Kit:** `demo_campaign/sft/` on v7j (gitignored). Runtime delta `runtime_delta_sft/`: `DELTA_ID d49170f2`, 21 files.
- **Guards** act only on DECLARED obstacle boxes, in derived grounding. **Odometry** is a simulator physics pose.

## 1. Session

| Item | Value |
|---|---|
| VM start | 1 failed start (stockout, about 2 min), up 14:58:22Z |
| VM TERMINATED | 15:30:51Z, verified by the driver and independently with `gcloud ... describe` |
| Wall booked (ledger `sft`) | 1949 s of the 7200 s cap. Campaign total 29,172 s of 43,200 s, after the `cvy` convoy rerun. |
| API spend | $0 (mock backend, no probe; every artifact `backend_id mock`, 0 tokens) |
| Bring-up aborts | 0 |
| Harness failures | 0. Restore `RESTORE_DMC OK`: pins at v3, installed packages == snapshot, added files and their bytecode removed, pxr scratch/target removed. |
| Real-time factor | 0.155 (R), 0.157 (S) |
| Horizon stop | Isaac stop flag at GT 101.5 s (R) and 131.1 s (S) |
| Bundles | `demo_campaign/sft/runs/sfT_t01_a1` (R), `sfT_t02_a1` (S). Manifest `MANIFEST_20261115T145600Z.md5`: 87 files, md5 `4f74a895bed96a4b5e4448f43e2c2681`. |

The VM was used first by the owner-approved `cvy` convoy rerun. This session started only after that driver ended (`DONE result=ok`) and the VM was TERMINATED. The ledger admission was re-read before the start: 7200 s fits.

## 2. Take 1, Arm R: Reverse Obstacle Guard ON (Escort Guard and Stall Abort Off)

**Configuration:**

- Arm check through the deployed loaders: `reverse_obstacle_guard True`, `escort_obstacle_guard False`, stall abort `False`, installed safety file `65fb84a3`.
- Condition gate: all checks pass. M4 printed `Command bus started.` with no suffix. M5 printed `... stage2_retreat_selection=True reverse_obstacle_guard=True`.

**Injected decision:**

- At the first analysis (sim 40.83 s), the scripted reverse of robot_5, robot_3, robot_1.
- robot_5's snapshot was (-2.067, 1.358, -0.049), inside the predicted envelope.

**Grounded result:**

- Three 8 s `temporary_wait`s with `requested_strategy reverse`.
- Tags: `reverse=infeasible:reverse_hits_obstacle:robot_5:obstacle_3:0.293` (predicted 0.295–0.349) and `reverse=infeasible:reverse_hits_obstacle:robot_1:obstacle_6:0.841`.

**Verdict: PASS.**

| Criterion | Evidence |
|---|---|
| R1 structured refusal | robot_5 / obstacle_3 tag; the waits as registered |
| R2 waits received | M5 dispatched to all three; M4 COMPLETED for each; 0 reverse hand-overs; 0 stall aborts |
| R3 no motion toward the box (GT) | Maximum backward displacement 0.000 m for all three over 10 s |
| R4 no static contact | 0 contact rows. The logged rows equal the offline recompute row by row (1017 rows, 0 mismatches). Closest static approach in the take: 29.7 mm. |

**Unexpected:**

- The second tag. robot_1's snapshot heading was 0.453 rad, versus -0.26 to -0.07 in the three recorded runs, because it was turning in the jam. Its backward leg therefore pointed into the declared south wall `obstacle_6`.
- The refusal is decided by robot_5 either way. The extra tag shows the guard naming every blocked leg.

## 3. Take 2, Arm S: Stall Abort ON (Both Grounding Guards Off)

**Configuration:**

- Before the take, `rearm_stall_sft.sh` installed the stall-on file `2ffc80c7` and rebuilt `swarm_execution`.
- Arm check: stall `True`, both guards `False`.
- Condition gate passes. M4 printed `Command bus started. stall_abort=True window_s=3.0 min_progress_ratio=0.25 grace_s=1.5 stale_input_s=1.0 min_linear_mps=0.03 min_angular_radps=0.15 min_expected_m=0.06 min_expected_rad=0.3`. M5's grounding line ends `stage2_retreat_selection=True`.

**Injected decision:**

- The same scripted reverse at sim 41.50 s.
- robot_5's snapshot was (-2.038, 1.397, 0.050).
- Grounded as three 1.3 m reverses with `backup_line_hold`.

**Verdict: PASS.**

| Criterion | Evidence |
|---|---|
| Situation arose | robot_5 hand-over at sim 41.83 s. Not in `/safety/holds` at the contact (observer). |
| Contact | First logged GT contact `rack/NW_west` at GT 46.30 s (ROS ≈ 46.92 s at the estimated offset 0.62 s). A sustained contact of 24 rows until GT 48.6 s. |
| S1 abort in time | `stall abort robot=robot_5 command=1a205fbd…-reverse primitive=backup phase=backup reason=stall mode=linear commanded_m=0.300 measured_m=0.071 expected_min_m=0.075 window_s=3.00 commanded_rate=0.100 sim_t=49.133`. Delay 2.21 s (registered ≤ 5.0 s; the replay predicted 2.3–3.0 s). |
| S2 FAILED status | `status published … robot=robot_5 status=FAILED`, after the abort line |
| S3 reason text | Observer: `stall_abort: commanded 0.100 m/s for 3.0 s, measured 0.071 m (expected >= 0.075 m)` |
| S4 one zero twist | One zero twist on `/robot_5/cmd_vel` within 0.5 s; no backup-like twist in the next 5 s |
| S5 contact logged | 1313 GT rows equal the offline recompute (`scripts/recompute_gt_contacts.py` at v7m `b5eaee5`) row by row: 0 mismatches, 24 rows with the contact. This is the logger's first live contact event. |
| S6 clear leg | robot_1's reverse ended COMPLETED with no abort. robot_3 had no stall abort. |

**Observation (not a criterion):**

- After the FAILED, the existing Nav2 failure path resumed robot_5's base mission. It drove east from (-2.398, 1.401) to (-0.322, 1.315) in 20 s.

**Unexpected:**

- robot_3's reverse ended FAILED through the existing B3 fresh-latch fast-fail at sim 46.7 s (`robot_3 latched during backup held_for=2.3s co_held=robot_2`). robot_2 re-approached it, which is the risk named in the registration.
- That is the existing B3 mechanism, not the stall abort. While held, robot_3 was not judged, as designed.
- The measured progress ratio at the abort was 0.237, just under the 0.25 threshold, as expected for a pin (the first window still contained about 0.7 s of motion).

## 4. Per Mechanism

| Mechanism | State | What was shown | What was not shown |
|---|---|---|---|
| Reverse obstacle guard | **VALIDATED LIVE** (n = 1) | Refused a forced reverse whose leg crosses a declared wall, with the structured reason; the robots waited; GT shows no motion toward the box and no contact. Its non-firing on clear legs is shown offline (`b07a700f`, hoD) and by the unchanged robot_3 leg here. | Undeclared geometry; partial refusal; behaviour on a real VLM decision |
| Stall abort | **VALIDATED LIVE** (n = 1) | Fired 2.2 s after a forced physical pin against an authored rack; FAILED with the reason; a zero twist; did not fire on the clear robot_1 leg (COMPLETED). | `input_stale` (none occurred); turn-phase stalls; escort and pull-off primitives; latch-held robots (blind spot, unchanged); the junction fallback path |
| Escort obstacle guard | **ARMED ONLY** (no take) | Blocks offline only (m5D decision 2). Phase 0: a first-trigger blocked escort was reproducible in 1 of 3 recorded snapshots. | Live |
| GT contact logging | Live contact positively recorded and equal to the offline recompute | Both takes | — |

## 5. `pxr` Builder-Parity Test

`test_scene_boxes_match_usd_builders_when_pxr_available` RAN and PASSED for the first time:

- result `1 passed, 43 deselected in 0.75s`;
- run inside a started Kit app (`src/pxr_kit_pytest.py`, SimulationApp headless), 18 s elapsed, in the deploy step;
- pytest 8.3.4 from `pip --target ~/dmc_sft/pytest_target`, which the restore removed;
- Isaac's site-packages listing was unchanged.

Log: `demo_campaign/sft/vm/pxr_test/`.

## 6. Merged-Tree Checks (Phase 1)

- **Targeted suites, verified by running:** 1670 passed, 129 skipped, 0 failed on the merged tree. These are the stall abort's 3 files, `test_nav2_adapter`, `test_command_bus_node`, `test_safety_monitor`, escort/reverse guard, m5 node grounding, A28/A29, plan verifier, contact geometry, acceptance logging, recompute and hard floor. They include each branch's key-off identity tests.
- **Offline replays reproduce their reports:**
  - the escort guard refuses m5D `a15f3fc5` (`escort_hits_obstacle:robot_3:obstacle_2:0.414`);
  - the reverse guard refuses `95066420` (0.305 / 0.844);
  - the stall abort fires on m5D robot_3's escort at 149.6 s.
- **Full unit suite:** PENDING. The resource rule (≥ 2 GB swap free) was not met in a 30-minute bounded wait, because swap free peaked at 1518 MB.
- **Kit dry tests:** `TEST_DRY_DMC sft OK` (9 sections) and `TEST_RESTORE_DMC OK` (9 cases, including a whole fake repo tree equal to its pre-snapshot state after the rearm).

## 7. Verified and Inferred

| Claim | Status |
|---|---|
| Both verdicts PASS on the registered criteria | Verified (`VERDICT.txt` in each bundle; re-run on the Mac after the pull) |
| Exactly one new key on per take | Verified (deployed-loader arm check + startup lines + artifact params) |
| Logged contact rows equal the recompute | Verified (row by row, both takes) |
| VM TERMINATED, restored to the pin | Verified |
| The guard would refuse undeclared geometry | Not shown (it cannot) |
| GT offset 0.62 s | Estimated from M1 vs GT (median pose error 7.3 mm) |

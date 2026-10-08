# S6 First Light: Dual-Conflict Scene Verification and Demo Episodes

**Prepared:** 2026-10-08

**Revision history:**

- Initial draft: the first VM runs of `s6_dual_conflict`. Covers the USD build and validators, one recorded mock mechanism run, one recorded live Gemini Robotics-ER 2 pilot episode, the start-delay D re-derivation, and two demo videos.

---

## Summary

| Question | Answer |
|---|---|
| Does the scene build and validate? | **Yes.** `build_scenario` wrote `isaac/scenarios/s6_dual_conflict.usd` (md5 `16d08acb`). The loop-connector and obstacle validators run inside the build, and `validate_simulation` passed. Read back from the USD, the spawns are at the amended A1 poses: robot_3 at (0.25, 1.2) and robot_4 at (2.05, 1.2). |
| Do both jams form in overlapping windows? | **Yes, in 2 of 2 runs.** B formed first both times: B − A standoff was −0.3 sim-s (mock) and −1.9 sim-s (live). Both jams then held, through the end of the run in mock and until execution started in live. |
| Should D = 16 wall-s move? | **Yes, up, to about 20 wall-s (provisional).** 16 s formed both jams in both runs, but B led each time. In the live run, M1 still showed pair A moving at the first trigger. The 16 s delay delivers only an 11–13 wall-s lag between the pairs, because M5 starts the delay clock 3–5 wall-s before it dispatches pair A. The per-run D\* is 17.4 (mock) and 24.7 (live). |
| M1 on markers 3 and 4 | **100% FRESH** in every window (0 STALE, 0 absent; 449–471 scene rows per robot per run). M1−GT error at the second-aisle poses: median ≤ 0.008 m, max 0.023 m. |
| Live decision: both pairs named, both addressed? | **No and no.** The first triggered decision named only pair B: `deadlock`, `involved_robots [robot_3, robot_4]`. Its plan was `reverse` robot_3, `reverse` robot_4, `continue` robot_1, `continue` robot_2. Oracle result: named A false / B true, addressed A false / B true, `addresses_both` false. When it fired, M1 still reported robot_1 and robot_2 as MOVING (0.13 and 0.06 m/s). |
| Arm B | **Mock: `unknown` on 35 / 35 analyses**, as A2 registered; the scenario was `unknown` and the type fell back to `anomaly`. **Live: on the scored first decision, Arm B returned `head_on [robot_3, robot_4]`, not `unknown`.** The classical crowding rule counts only stopped robots, and pair A was still moving. Live decisions 2 and 3 were `unknown`, and decision 4 was `head_on [robot_1, robot_2]`. |
| Videos | `s6_dual_jam_mock_20261008_004220.mp4` (654 s) and `s6_live_er2_20261008_010035.mp4` (633 s), both retimed to wall clock. |
| Cost | 4 ER-2 calls, no stage-2 calls. 12,315 prompt tokens and 2,597 output plus thought tokens: about $0.01–0.04, depending on the preview's price. |

The live episode is a **PILOT / demo episode**. It is excluded from every confirmatory count, and its execution is unscored by design (spec option (a)). Its run_id is STAMP `20261008_010035`. Its artifacts sit in the VM's shared `data/logs/m5_decisions/` and carry no pilot label of their own.

### Checklist

| Item | Check | Verdict | Evidence |
|---|---|---|---|
| 1 | USD build + `validate_loop_connectors` / `validate_scenario_obstacles` + amended poses | **PASS** | Built as root: USD `16d08acb`, `validate_simulation` PASS. Spawns read back at robot_3 (0.25, 1.2), robot_4 (2.05, 1.2). The first attempt, as `ubuntu`, wrote nothing yet returned rc 0. |
| Brief step 2 | Hand overlay + four-stack lifecycle gate | **PASS (2 / 2)** | Overlay `3d9fda63`, installed copy grepped. Nav2 4/4 active at the first poll in both runs, no void. `RESTORE OK` × 2. |
| Brief step 3 | Both jams form in overlapping windows | **PASS (2 / 2)** | B − A standoff −0.3 sim-s (mock) and −1.9 sim-s (live). Both held. |
| 4 | M1 tracks markers 3 / 4 at the second-aisle poses, including the hold | **PASS** | 100% FRESH, 0 STALE. M1−GT median ≤ 0.008 m, max 0.023 m. |
| 5 | robot_4 spawn clean | **PASS** | Max pre-release displacement 0.4 mm, 0.0045 m/s. |
| 6 | Re-derive D | **MOVE: 16 → about 20 wall-s (provisional)** | Per-run D\* 17.4 / 24.7. The delay clock starts 3–5 wall-s before A is dispatched. |
| 7 | Single Nav2 route, no self-detour | **PASS** | Every plan stays in its own aisle; robot_3 / robot_4 y ⊂ [0.93, 1.39]. |
| 8 | What the first trigger shows | **FINDING** | Single-robot stall set `['robot_3']` in both runs; it is not rendered into the prompt. |
| Live | Both pairs named / both addressed (PROPOSED oracle) | **FAIL / FAIL** | The scored decision named and addressed B only. |
| Arm B | A2 expectation `unknown` | **Mock: confirmed (35 / 35). Live scored decision: NOT confirmed** | Live returned `head_on [robot_3, robot_4]`. |

---

## 1. Inputs and Deviations

### Sources

- Scenario: `isaac/config/scenarios/s6_dual_conflict.yaml`. The VM copy (md5 `f0bb5b57`) equals the `0f10791` copy, which descends from `11fa31a` (the A1 pose amendment), so no redeploy was needed.
- Rulings: prereg-v3 rev 3 addenda A1 (poses, provisional D) and A2 (Arm-B degeneracy registered), on `feat/v3-design`. Oracle: `DualConflictOracleConfig` in `isaac/vgu_sim/config.py`, criterion_status `proposed`, plan_source `model_raw`.
- **The S6 build handover checklist was not found on disk** (searched every worktree, branch and report). Item numbers 1, 4, 5, 6, 7 and 8 below come from the task brief; brief steps 2 and 3 are reported under their own names. No content was invented for checklist items 2 and 3.

### VM tree

| Item | Value |
|---|---|
| VM | `vgu-vgu-thule-base-isaac-workstation-vm`, Isaac Sim 6.0.1, container `vgu_ros` |
| Code | `feat/v3-integration@0f10791`. `md5sum -c` against the 888-file `0f10791` manifest, before and after the wave: only `orchestrator.yaml` FAILED (VM-pinned `1f656533`, source and installed). |
| S6 map | Installed `warehouse_map_s6_dual_conflict.pgm` / `.yaml` md5 `96125c97` / `40756ffb`, equal to source |
| Wave dir | `/home/ubuntu/v3_s6_first_light/` (driver, overlay, pristine copy, runs, `NOTES.md`) |

### Deviations

1. **`plan_channel_enabled: true`** was added to the overlay. The pinned v2-era `orchestrator.yaml` lacks the key (default false, prompt v2), and prompt v2 carries no `proposed_plan` invitation. The S6 oracle scores the model's raw `proposed_plan`. The v2 live demo and the verbatim pilot used the same setting. The same overlay was used for both runs.
2. `keep_debug_frames` and `keep_raw_frames` were set true to capture prompt frames.
3. Both runs had RECORD on. Overall RTF was 0.214 (mock) and 0.219 (live), inside the 0.21–0.24 four-stack band.
4. Live run cost cap: `MAX_ANALYSES=6` (an Isaac stop flag after the 6th analysis). It was never reached; Isaac ran its full 150 sim-s.
5. ER-2's sampling fields are recorded under `unsupported_sampling` (temperature 0.6, top_k 20, top_p 0.95; thinking_level low), as in every ER-2 run so far.

---

## 2. Build and Bring-Up

### Item 1: USD build and validators — PASS

- **Attempt 1, run as `ubuntu`, failed silently.** `build_scenario` returned rc 0, but no USD was written: `isaac/scenarios/` is root-owned, and Kit's fast shutdown swallowed the error. `validate_simulation` also returned 0 against the missing file. **A build rc of 0 is not evidence; check that the file exists.**
- **Attempt 2, run as root**, logged `Scenario written to: isaac/scenarios/s6_dual_conflict.usd` (2026-10-08 00:40:47 UTC, 5283 B, md5 `16d08acb`).
  - `validate_scenario_obstacles` and `validate_loop_connectors` run inside `build_scenario_stage`, before `stage.Save()`, so the write itself proves both passed.
  - `validate_simulation` logged `PASS`.
- USD spawn read-back (`usd_spawns.py`): robot_1 (−1.5, 0) rotZ 0, robot_2 (1.5, 0) rotZ 180, **robot_3 (0.25, 1.2) rotZ 0, robot_4 (2.05, 1.2) rotZ 180**.
- Offline `check_s6_feasibility.py`: 11 PASS, plus 1 FAIL that is expected. The FAIL is `arm_b_head_on_not_crowded` (robot_2 to robot_3 is 1.389–1.459 m), the A2-registered crowding issue.

### Brief step 2: overlay and four-stack bring-up — applied, 2 / 2 clean

- The overlay `s6_orchestrator.yaml` (md5 `3d9fda63`) is the pristine `1f656533` with three changes:
  - its `initial_tasks` block replaced via `patch_initial_tasks.py --set` with the header's four-robot snippet (robot_3 and robot_4 carry `start_delay_sec: 16.0`);
  - debug and raw frames enabled;
  - `plan_channel_enabled: true`.
- Before applying it, the overlay was loaded through `swarm_orchestrator.models.load_config`: `plan_dispatch_order_source=chi`, `task_stream.enabled=False`, `dispatch_enabled=True`.
- After `fc_launch`'s rebuild, the installed copy was grepped: the start-delay lines and the plan channel were present.
- The driver (`s6_run.sh`, derived from v2_demo's `v2demo_run.sh`) did the following:
  - refused a non-pristine source or installed config;
  - gated on `pgrep [r]un_simulation`;
  - restored with a fresh mtime, rebuilt and md5-checked;
  - started the `/robot_{1..4}/plan` bag only 15 s after `Nav2 lifecycle active 4/4`.
- `fc_launch`'s lifecycle gate passed at its first poll in both runs: no `Aborting bringup`, no void. Both runs logged `RESTORE OK` (source and installed `1f656533`, rag `e18c723c`).

### Recorder trap found and fixed

Under Option B, the M5 tail ends 10 s after Isaac exits, and cleanup's `docker restart` then SIGKILLs the in-container recorder before it writes the mp4 trailer. At about 0.5 fps, the 2000-frame segment never rolls, so the whole video would be lost.

The driver's host sidecar now SIGTERMs `record_topic_video.py` as soon as Isaac's process is gone (`ISAAC_EXIT_GRACE_SEC=45`). Both runs logged `stop requested signal=15` and then `WROTE`: 371 frames / 654.3 s (mock) and 322 / 633.2 s (live). Every RECORD=1 run since Option B needs this, or an equivalent fix in `fc_launch`.

---

## 3. Mock Mechanism Run

`s6_mock_r1`, STAMP `20261008_004220`. Mock backend with its default no-congestion answer: 35 analyses, no dispatch. GT `completed: true`, 150 sim-s.

### Brief step 3: both jams form in overlapping windows — PASS

All times are GT sim-s. The table includes the live run for comparison.

| Pair | Run | Departures | Standoff | Close | Standoff gap | Held until |
|---|---|---|---|---|---|---|
| A | mock | r2 26.0, r1 26.4 | **34.6** | 8.6 | 0.394 m | end of run (150) |
| B | mock | r3 29.3, r4 29.3 | **34.3** | 5.0 | 0.264 m | end of run (150) |
| A | live | r1 28.2, r2 30.1 | **37.9** | 9.7 | 0.308 m | 82.6 (execution) |
| B | live | r3 31.0, r4 31.0 | **36.0** | 5.0 | 0.248 m | 82.7 (execution) |

- Standoff is defined as both GT speeds below 0.02 m/s and the gap within 0.03 m of its minimum over the next 20 s. Close is measured from the pair's first departure.
- Both standoff gaps sit **below the design's g range [0.32, 0.45]**, B's at 0.25–0.26 m. This does not change formation, but the close-time arithmetic should use g ≈ 0.25–0.40.
- The minimum centre distance over both runs was 0.148 m (robot_3 / robot_4 during live execution, at 138.6 s). That is above the 0.076 m nose-to-nose contact distance, so there was no contact. GT `robot_robot_contacts` is diagnostic only (A8).
- M5's start falls at sim 25–28 s (the first A departure is 26.0 / 28.2), not the design's ~20 s.

### Item 6: D re-derivation — D should move up, to about 20 wall-s (provisional)

| Quantity | Mock | Live |
|---|---|---|
| Overall RTF (scene log) | 0.214 | 0.219 |
| Nav2 `Begin navigating`, A → B (wall-s) | 12.1–13.4 | 11.2–11.5 |
| B departure lag (GT, first A departure → B departure) | 3.3 sim-s | 2.8 sim-s |
| Lag needed (close_A − close_B) | 3.6 sim-s | 4.7 sim-s |
| B − A standoff | **−0.3 sim-s** | **−1.9 sim-s** |
| First-trigger window (12 wall-s × RTF) | 2.6 sim-s | 2.6 sim-s |
| D\* = 16 + (A − B standoff) / RTF | **17.4 wall-s** | **24.7 wall-s** |

- **Mechanism.**
  - `start_delay_sec` is counted from `time.monotonic()` at M5 node init (`orchestrator_node.py`, `started_at`).
  - Pair A's goals reach Nav2 3–5 wall-s later. Taking that origin as the release time minus 16 s, robot_2 / robot_1 `Begin navigating` came 3.0 / 4.2 s after it in mock, and robot_1 / robot_2 came 4.8 / 5.0 s after it in live.
  - So the delivered A → B lag is 11–13 wall-s, not 16. The design's "the unheld pair departs at M5's start" assumption does not hold.
- **The live run adds in-robot jitter on top.** robot_2's Nav2 began 0.15 wall-s after robot_1's, yet its GT departure came 1.9 sim-s later. That stretches close_A to 9.7 s. No choice of D removes that jitter.
- **Why it matters even though both jams formed.**
  - In both runs the first trigger fired after A's GT standoff: by 2.2 s in mock (scene stamp 36.8) and by 0.77 s in live (38.67). Correcting for the ~0.5 s GT clock offset (trap 18), the live margin is only about 0.3 s.
  - In the live run, M1's filtered velocities still reported robot_1 at 0.13 m/s and robot_2 at 0.06 m/s (MOVING). Pair A was therefore not perceivably jammed when the scored decision was taken (§4).
- **Perceived-state margin rule.** The first trigger fires about 12 wall-s (≈ 2.6 sim-s) after the leading pair's standoff. The trailing pair reads STOPPED in M1 only 0.6–1.3 sim-s after its own GT standoff (item 4). Both jams therefore read as jammed at the first trigger only when |B − A| + M1 lag < 12 · RTF, which needs |B − A| ≲ 1.3 sim-s.
  - Mock: 0.3 + 1.17 = 1.5 < 2.6. Both jams were perceived.
  - Live: 1.9 + 1.17 = 3.1 > 2.6. A was not perceived as jammed, which is what happened.
- **Verdict.** Centre B on A rather than let B lead. The pooled mean offset is −1.1 sim-s, or about +5 wall-s at RTF 0.217, which gives D ≈ 20–21. The two runs differ by 1.6 sim-s, about 60% of the trigger window, so n = 2 cannot pin D. A RECORD-off timing pilot (n ≥ 3) that also logs M5's A-dispatch wall time should fix it before the Step 6 freeze. An alternative is to count the delay from A's dispatch in M5, but that is a code change.

### Item 5: robot_4 spawn — PASS

| Robot | Max displacement, 0–24 sim-s | Max speed, 0–24 sim-s |
|---|---|---|
| robot_4 (2.05, 1.2, π) | **0.4 mm** | 0.0045 m/s |
| robot_1, robot_2, robot_3 | 0.1 mm | 0.000 m/s |

This is identical in both runs: no depenetration jolt, and robot_4's first GT row is (2.0501, 1.2). GT `robot_static_contacts` is empty.

### Item 7: Nav2 single route, no self-detour — PASS

`/robot_N/plan` bags (mock: 96 plans; live: 488 plans):

| Robot | Mock plan bounds | First-plan length vs straight line |
|---|---|---|
| robot_1 | x [−1.15, 2.50], y [−0.32, 0.15] | 3.88 (straight-line run along the primary aisle; plan starts after departure) |
| robot_2 | x [−2.50, 0.95], y [−0.20, 0.18] | 3.57 |
| robot_3 | x [0.25, 2.05], **y [0.93, 1.35]** | 1.75 vs 1.80 |
| robot_4 | x [0.00, 2.05], **y [0.99, 1.39]** | 2.16 vs 2.05 |

- Every plan stays in its own aisle. robot_3 and robot_4 never enter the connector (y < 0.925), and robots 1 and 2 never leave the primary aisle.
- The live pre-dispatch plans are the same: robot_4 2.16, robot_3 1.78. The live robot_3's later plans reach x = −0.25 during the executed `reverse` (in the N-S strip); that is execution, not a self-detour.
- GT agrees: robots 3 and 4 stayed in y [1.12, 1.24] in both runs.

### Item 4: M1 tracking of markers 3 and 4 — PASS

The scene log (`m5_scene.jsonl`) was joined to GT at a 0.5 s offset (trap 18).

| Run | Robot | Window | Rows | FRESH | STALE | M1−GT median / max (m) |
|---|---|---|---|---|---|---|
| mock | robot_3 | whole run | 471 | 100% | 0 | 0.007 / 0.017 |
| mock | robot_4 | whole run | 471 | 100% | 0 | 0.008 / 0.023 |
| mock | robot_3 / robot_4 | First scene row → B departure (held at spawn, ROS 24.97–29.3) | 10 each | 100% STOPPED | 0 | 0.008 / 0.010 |
| live | robot_3 / robot_4 | First scene row → B departure (ROS 28.13–31.0) | 6 each | 100% STOPPED | 0 | 0.008 / 0.010 |
| mock | robot_3 / robot_4 | B standoff → end | 439 | 100% | 0 | 0.007 / 0.016 |
| live | robot_3 / robot_4 | whole run | 449 | 100% | 0 | 0.007–0.008 / 0.021–0.023 |

Robots 1 and 2 were also 100% FRESH. The hold window in the scene log is short, because the log starts at M5 start and the robots sit at spawn from t = 0.

M1's lag from a GT standoff to its first STOPPED report, with GT shifted +0.5 s onto ROS stamps:

| Robot | Mock lag | Live lag |
|---|---|---|
| robot_1 | 1.17 s | 1.17 s |
| robot_2 | 0.97 s | 0.70 s |
| robot_3 | 0.63 s | 0.60 s |
| robot_4 | 1.27 s | 0.97 s |

The range is 0.6–1.3 sim-s. Throughout, M1 places markers 3 and 4 within 0.01 m at (0.25, 1.2) and (2.05, 1.2).

### Item 8: what the first trigger shows — single-robot stall set

| Run | First analysis | Trigger | Scene stamp | Next analysis |
|---|---|---|---|---|
| mock | `879c51bc` | `robots=['robot_3'] reason=1 robot(s) stalled >= 12.0s` | 36.8 | 15.3 wall-s later: `4 robot(s) close/slow`, all four |
| live | `d824685c` | `robots=['robot_3'] reason=1 robot(s) stalled >= 12.0s` | 38.67 | 60.1 wall-s later: `4 robot(s) close/slow`, all four |

- **Yes: in both runs the first trigger's stalled set names a single robot of a single pair, robot_3 of B.**
- That set is not rendered into the prompt: prompt v3 contains no "stall" or "trigger" text. The prompt lists all four robots' states and all six pairwise-geometry lines. The stalled set appears only in M5's log line and in the artifact's `distance_to_goal_m` keys.
- What the model saw therefore depends on M1's per-robot state at the snapshot:
  - mock: robot_1 SLOW 0.01 m/s, robot_2 STOPPED (both pairs read as jammed);
  - live: robot_1 MOVING 0.13 m/s, robot_2 MOVING 0.06 m/s (pair A still read as approaching at 0.31 m).

### Arm B in the mock run

On all 35 analyses, `shadow_classical.classification` was `scenario: unknown`, `congestion_type: anomaly`, involving all four robots. The decision was `temporary_wait` or `reroute`, with root cause "classical: unclassified stall of robot_1, robot_2, robot_3, robot_4". This is the A2-registered degeneracy.

---

## 4. Live ER-2 Episode (PILOT / Demo, Excluded From Confirmatory Counts)

`s6_live_er2_pilot`, STAMP `20261008_010035`. Backend `gemini`, model `gemini-robotics-er-2-preview`, thinking_level low; key sourced inside the container from `/ws/.env`. Prompt v3, `id_asc`. 4 analyses, GT `completed: true`.

### Scored (first triggered) decision `d824685c` — verbatim summary

- `congestion_detected: true`, `type: deadlock`, **`involved_robots: [robot_3, robot_4]`**, `strategy: reverse`, `blocker_kind: robot`, `yield_robot: null`.
- reasoning: "Robots robot_3 and robot_4 are stopped within 0.25 meters of each other and facing head-on in a narrow aisle, constituting a deadlock. Both robots need to reverse to clear the narrow passage."
- `proposed_plan` (raw, as scored): `reverse robot_3`, `reverse robot_4`, `continue robot_1`, `continue robot_2`.
- Provenance: `plan.provenance: repaired`. M3 substituted `reverse` with `wait` for both B robots ("both outside the corridor on the same side; a reverse would traverse it"), as expected for the ungroundable B conflict. Under `plan_source: model_raw` the raw plan is what is scored.
- Latency 4175 ms; 2944 prompt / 277 completion / 363 thought tokens.

### Oracle (PROPOSED), scored by `DualConflictOracleConfig`

| Decision | Scene stamp | Named A / B | Addressed A / B | `addresses_both` | Plan provenance |
|---|---|---|---|---|---|
| **1 (scored)** | 38.67 | **False / True** | **False / True** | **False** | repaired (raw plan scored) |
| 2 | 51.93 | True / True | True / True | True | `vlm_verbatim` (`yield` r2, `cross` r1, `wait` r3 / r4) |
| 3 | 82.0 | True / True | True / True | True | repaired (`reverse` r2 / r4, `cross` r1 / r3) |
| 4 | 133.9 | True / True | (True / True on raw legs) | **no plan under the rule** (`m3_default`) | plan rejected as inconsistent |

**Both pairs named: NO. Both addressed: NO.** The first decision is a correct single-conflict answer to the scene M1 reported: pair A was still MOVING at 0.31 m (§3, item 8).

Detection latency per conflict, from GT standoff to the first trigger's scene stamp:

- **B:** 2.67 sim-s on raw stamps (≈ 2.2 after the 0.5 s GT clock correction).
- **A**, the trailing pair: 0.77 sim-s raw (≈ 0.3 corrected). A had not yet been perceived as stopped: M1 first reported robot_2 STOPPED at ROS 39.1 and robot_1 at 39.57, both after the 38.67 snapshot.

Re-analyses 2–4, by which time both pairs read as stopped, all named both pairs. This is unscored context only.

### Arm B on the live episode

| Decision | Arm B classification |
|---|---|
| 1 (scored) | **`head_on`, `deadlock`, `[robot_3, robot_4]`**, centre (1.16, 1.21), yield robot_4 |
| 2, 3 | `unknown` → `anomaly`, all four robots |
| 4 | `head_on`, `deadlock`, `[robot_1, robot_2]` |

- **The A2 expectation (`unknown`) is NOT confirmed on the scored decision of this episode.**
- Mechanism, confirmed in code: `classical_reasoner._head_on_pair` checks crowding only against robots in its `stopped` list. That list is built from M1's `|linear_velocity| < stopped_speed_mps` (0.05), on the same snapshot the request was built from. robot_1 (0.13 m/s) and robot_2 (0.06 m/s) were not in it, so B was uncrowded.
- A2's degeneracy holds only once both pairs read as stopped, which happened in mock (35 / 35) and on live decisions 2–3. That makes the A2 registration timing-dependent; it is an input to the D fix and to Step 6.

### Execution (unscored by design)

- Dispatches:
  - d1: `reverse` to robot_3 and robot_4, executed as `temporary_wait`, completed.
  - d2: `reroute` to all four, executed mixed, failed.
  - d3: `reverse` to all four.
  - d4: `reroute` to robot_2.
- robot_3 arrived at (2.05, 1.2), 0.10 m from goal, `within_tolerance`. No other arrivals in 150 sim-s.
- No robot-robot contact: minimum centre distance 0.148 m.
- **Probable wall touch:** robot_4 reached GT x = 2.098 during execution. Its chassis rear extends 0.102 m behind base_link, which puts it at about x = 2.200, the second aisle's east wall. GT `robot_static_contacts` is empty, but that field does not rule a touch out.

---

## 5. Videos and Bundles

All paths are under `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/data/logs/vm_runs/s6_first_light/`:

| File | Content |
|---|---|
| `s6_dual_jam_mock_20261008_004220.mp4` | Mechanism: both jams forming and holding. 654 s wall clock; 371 frames stamped at 3.824 fps, achieved 0.567 fps, `setpts=6.7441*PTS,fps=4`. |
| `s6_live_er2_20261008_010035.mp4` | Live ER-2 decision and execution. 633 s wall clock; 322 frames stamped at 2.829 fps, achieved 0.509 fps, `setpts=5.5631*PTS,fps=4`. |
| `s6_mock_r1/`, `s6_live_er2_pilot/` | Run bundles: GT, logs, decisions, frames, `m5_scene.jsonl`, plan bag, `fc_run/annotated_*.mp4` with `concat_list.txt` / `annotated_concat.mp4`, `s6_analysis.json`, `plan_bag_summary.txt` |
| `_vm_driver/` | `s6_run.sh`, launch scripts, overlay, `s6_analyze.py`, `s6_extra.py`, `plan_bag.py`, the USD build script and log, oracle scores, and a copy of the VM `NOTES.md` |

Each video is a single segment (`concat_list.txt` lists one file), retimed by the `fc_launch.sh` header procedure, as the v2_demo workflow did.

---

## 6. VM End State

- `orchestrator.yaml` source and installed: `1f656533`; `rag.yaml` `e18c723c`.
- The 888-file `0f10791` manifest still FAILs only `orchestrator.yaml` (pinned).
- New on the VM: `isaac/scenarios/s6_dual_conflict.usd` (root-owned, md5 `16d08acb`).
- No `run_simulation`, `fc_launch`, driver, recorder or bag processes. GPU 0%, 171 MiB. No GT leftover.
- `gpt56_sol_swap/`, `shutdown_timing_probe/` and PID 58079 were untouched.
- The VM is still **RUNNING (billing)**.

---

## 7. Open Items

1. **D:** move the provisional 16 wall-s to about 20, then re-measure with a RECORD-off timing pilot (n ≥ 3) that logs M5's A-dispatch wall time. Alternatively, count the start delay from A's dispatch.
2. **First trigger is a single-robot stall** in both runs. Whether the scored decision sees both jams depends on M1's velocity filter at that snapshot. Step 6 should decide whether "first triggered" requires both pairs to read STOPPED in the prompt state, or whether the trigger should be the close/slow trigger.
3. **A2 is timing-dependent:** Arm B returns `head_on` for the leading pair whenever the trailing pair is still moving at the trigger.
4. **Standoff gaps of 0.25–0.39 m** sit below the design's 0.32–0.45 m g band. Update the formation arithmetic accordingly.
5. **Harness:** the RECORD=1 recorder needs a stop before cleanup under Option B (sidecar here, or move it into `fc_launch`). Builds into `isaac/scenarios/` must run as root and be checked by file existence, not rc.

---

## References

- `isaac/config/scenarios/s6_dual_conflict.yaml`, `isaac/scripts/check_s6_feasibility.py`, `isaac/vgu_sim/config.py` (`DualConflictOracleConfig`)
- `docs/superpowers/specs/2026-10-06-v3-scene-design.md` (S6) and `docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (rev 3 addenda A1, A2), on `feat/v3-design`
- `reasoning/baselines/classical_reasoner.py` (`_head_on_pair`), `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` (`started_at`), `task_registry.py`
- `docs/reports/2026-10-08-ib10-closure.md` (driver and gate precedent)

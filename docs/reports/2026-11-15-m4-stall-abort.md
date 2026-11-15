# M4 Execution-Side Stall Abort: Design, Tests and Offline Replay

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: Step-1 facts, the detector and its M4 wiring behind `safety.stall_abort.enabled` (default off), parameter derivation from recorded runs, unit, node and replay tests, replay over 221 recorded primitives, limits, kit needs and a live-validation proposal.

---

## Scope

- **Owner requirement (2026-11-15, prioritised):** detect commanded motion without corresponding measured movement, cancel the manoeuvre, issue a safe stop and record the reason. Test genuine stalls and false-positive cases. Changes isolated, default off, fully traceable; not enabled together with other new safety mechanisms in the first validation run.
- **Branch:** `fix/m4-stall-abort`, cut from 8933863 (the VM pin 68e67b5 plus the safety-exemption fix). `nav2_adapter.py`, `command_bus_node.py`, `package.xml` and `config/safety.yaml` are byte-identical between 68e67b5 and 8933863. Kept separate from `fix/escort-obstacle-guard` and `feat/gt-contact-logging`.
- **Change:** M4 only (`ros2_ws/src/swarm_execution`). M5, M3 and the shared interfaces are untouched. No new message or field.
- **Evidence grade:**
  - unit and node tests with mocked ROS;
  - offline replay of 221 recorded primitives through the real adapter code;
  - recorded rosbags for the odometry facts;
  - **no live run**.
- Bundles were read only. No VM, no gcloud, no API call, no push.

---

## 1. Defect

M4's raw-cmd_vel primitives end only on their odometry target or on an OS-monotonic deadline of `max(15 × naive, 30 s)` wall seconds. Nothing notices that the robot has stopped moving while its wheels are still commanded.

- **m5D escort** (`docs/reports/2026-11-15-demo-campaign-results.md` §8.7 on v7j). Escort `a15f3fc5` drove robot_3 into rack island `obstacle_2` at GT 146.9 s (ROS sim 147.3 s, section 2.3). It was held there until the escort's deadline, 335.0 wall-s after the start.
- **October reverses** (`docs/reports/2026-11-15-escort-obstacle-guard.md` §8 on v7l). Backups pinned on box faces until their 195 wall-s deadline.

The grounding-side guards on the other branches see only declared obstacles. This mechanism is the execution-side backstop for anything else.

---

## 2. Facts (Step 1)

### 2.1 Raw-cmd_vel Primitives (Verified by Code Reading at 8933863)

| Primitive | Used for | Publishes | Feedback | Ends | Status to M5 |
|---|---|---|---|---|---|
| `Nav2Adapter.backup` | yield backup; `reverse`; `junction_clear` recede | `/<robot>/cmd_vel` at 20 Hz on the node clock: −0.1 m/s plus a heading servo (odom y = 0, or the start line under `backup_line_hold`) | `/<robot>/odom`: distance from the first sample | `COMPLETED` at the distance; `FAILED` at `max(15·L/0.1, 30)` wall-s (`backup timed out: moved …`), or the B3 fresh-latch check | the yield/reverse leg's `CoordinationStatus`; a FAILED also releases the command's linked waits (`released: yield failed`) |
| `Nav2Adapter.sidestep` | yield pull-off; `junction_clear` release pull-off (backup 0 m) | turn ±0.5 rad/s, drive 0.1 m/s, turn back | odom yaw (turns), distance (drive) | `COMPLETED` after turn back; `FAILED` at `max((π/0.5 + L/0.1)·15, 30)` wall-s or B3 | the yield leg (via `_on_pull_off_result`) |
| `Nav2Adapter.drive_heading` | escorted passer | turn ±0.5 rad/s to the heading, then 0.1 m/s with a line servo | odom yaw, distance | `COMPLETED` at the distance; `FAILED` at `max((π/0.5 + L/0.1)·15, 30)` wall-s | **none**: `on_escort` only logs `escort <robot>: <status> <detail>`. The passer's linked wait ends when the yielder's hold ends |
| hold, wait, temporary_wait, stop | yielder hold, linked waits | nothing (cancel only) | none | timers | the leg's status |

- **Command path.** Nav2's controller publishes `cmd_vel_nav`, the collision monitor forwards it to `cmd_vel` (`nav2_params.yaml`), and the Isaac relay `cmd_vel_watchdog_node.py` forwards `/cmd_vel` to `/cmd_vel_safe`, the only topic the drive graph reads. The raw primitives publish `/cmd_vel` directly, so they bypass the collision monitor.
- **Safety latch and hard floor.** The safety monitor (a separate node, separate `Nav2Adapter`) publishes a zero `Twist` on `/cmd_vel` at 40 Hz and the held set on `/safety/holds`. The relay zeroes `cmd_vel_safe` for every held robot whatever `/cmd_vel` says. The monitor's adapter cannot cancel the command bus's primitive timer, so **a latched robot's primitive keeps publishing non-zero `/cmd_vel` while its wheels receive zero**.
- **M1 pose in M4.** Only the safety monitor reads `/perception/scene_state`. The command bus does not.
- **M5 on FAILED** (`orchestrator_node._on_status`):
  - the command tracker resolves the command (`command … resolved status=failed`);
  - the contradiction trigger, if enabled, arms `leg_failed`;
  - the next analysis of the same robots carries `failure_context` (e.g. `reverse failed after 195 s`);
  - M5 **never reads `CoordinationStatus.detail`**.
- **The coordination client** resumes the base mission under Nav2 on any terminal status of the robot's command.
- **Not logged anywhere** (m4.log, m5.log): the status detail, so the backup's final `moved … m` and the escort's distance are not recorded. M4's `status published` line carries the status only.

### 2.2 Which Measurement Shows "No Movement" When Pinned

| Source | What the recorded data show | Usable? |
|---|---|---|
| `/<robot>/odom` | `IsaacComputeOdometry` on the chassis prim (`isaac/vgu_sim/ros_graphs.py:292-320`, `chassisPrim` = articulation root), stamped by `IsaacReadSimulationTime`. It is a physics pose, not wheel integration. **(a)** In 13 IB10 bundles with rosbags (26 robot-runs), odometry mapped to the world with the spawn pose matches GT to **0.1 mm maximum** over whole runs, at a clock offset of exactly 0.50 s (`scripts/stall_abort_odom_check.py`). **(b)** Two robots pinned on rack corners (v3 `s1_resume` bags): commanded 0.105 m/s + 1.19 rad/s for 1.07 s, odometry moved **0.3 mm** and 0.003 rad; commanded 0.161 m/s + 0.69 rad/s for 1.23 s, odometry moved **1.4 mm** and 0.019 rad. **(c)** All 8 deadline failures below ended on the wall deadline (191.4-209.5 s and 335.0 s, m4.log) rather than the odometry target. With wheel-integrated odometry, 0.1 m/s for 35-65 sim-s would have passed every 1.3-1.6 m target and they would have read COMPLETED. | **yes**: the abort uses it |
| M4's own distance (primitive feedback) | Not logged (2.1). Inferred from (c): it stayed below target. | same signal as `/odom` |
| GT (`base_link`, 10 Hz) | Robot at the face; footprint gap ≤ 0 at every abort (v7m `contact_geometry`, section 6.2). | offline only; the replay's proxy for `/odom` (equal to 0.1 mm per (a)) |
| M1 (`m5_scene.jsonl`) | m5D robot_3: last MOVING sample at 147.07 s, then **STALE** (530 samples) for the whole pinned period, because the island hid the marker (§8.7.2 of the campaign report). E12 `d374802a` and E20 `6cf402ed` also go STALE right after the abort. The others read SLOW/STOPPED with about 1 cm noise, at about 4 Hz. | **no**: it goes STALE exactly when needed |

**Stale or missing input.** A stale measurement is read neither as "no movement" nor as "moving". Odometry older than `stale_input_s` (1.0 sim-s), or none since the primitive started, is its own abort reason (`input_stale`). This holds even on a tick that publishes nothing, because a primitive that cannot see its own odometry cannot verify anything. Recorded odometry arrives every 0.033 sim-s (maximum gap in every bag), so 1.0 s is 30 missed messages, or 5.9 wall-s at RTF 0.17.

### 2.3 Time Base

- **Primitive ticks** are `create_timer(0.05)` on the node clock. The command bus runs with `use_sim_time` (`execution.launch.py`), so they tick in sim time. **The deadlines** are `time.monotonic()`, wall time.
- **Odometry stamps** are Isaac sim time, the same clock as `/clock`.
- **Choice: sim seconds throughout.** Command samples carry the node clock, and the window is measured between odometry header stamps. The verdict is then the same at any real-time factor (unit and node tests at RTF 0.17 and 1.0). A frozen sim freezes both clocks, so nothing fires; the monotonic deadline still covers that case.
- **GT clock.** GT time = ROS sim time − offset. GT starts after Isaac's ROS topic wait (`isaac/vgu_sim/runner.py:186-206`). The offset is 0.50 s in every bag run. The replay estimates it per bundle by aligning M1's sim-stamped poses with GT (0.48 and 0.52 s on two bag runs, against the exact 0.50 s). All times in this report are ROS sim time unless marked GT.

### 2.4 Legitimate "Commanded but Not Moving"

| Situation | Handling |
|---|---|
| Turn in place | Judged on rotation, not exempted. Recorded turns reach 0.33 rad/s against 0.5 commanded, a progress ratio of 0.64-0.67. The pinned bag turns reached 0.003-0.022. |
| Ramp-up after start or phase change | `grace_s` 1.5 s from the start of each commanded mode. Recorded backups reach 0.08 m/s by 0.34 s (median), 0.61 s (max, 63 exact-start backups). |
| Safety latch or hard floor | The detector sees the command **gated to zero while the robot is in `/safety/holds`**, which is what the relay sends the wheels. A hold release restarts the grace period. |
| Hold, wait, zero command | Idle: not judged. |
| Very low commanded speed | Below 0.03 m/s or 0.15 rad/s: idle. Windows commanding under 0.06 m or 0.3 rad are not judged. |
| Brief perception or odometry dropout | The window is anchored on odometry stamps, so a gap below 1.0 s only delays the next judgement. M1 is not used. |
| End of the manoeuvre | The primitives do not decelerate: they stop on the target tick. Expected progress integrates the command actually sent, so any taper shrinks the expectation with it (unit test). |

---

## 3. Design

- **Pure detector** (`swarm_execution/stall_abort.py`, no ROS imports).
  - `StallDetector.on_odom(stamp, x, y, yaw)` and `observe(now, v, w, held)`.
  - Each tick's command is classified `linear` (|v| ≥ 0.03), `angular` (|w| ≥ 0.15, no linear) or `idle`. A mode change, including a hold, restarts the grace.
  - Over the last `window_s` of odometry inside one mode, after the grace, it compares measured net progress with commanded net progress: straight-line displacement against |∫v dt|, or signed yaw change against |∫w dt|.
  - Verdicts: `stall` (ratio < `min_progress_ratio`) or `input_stale` (odometry older than `stale_input_s`). Each is a frozen Pydantic `StallVerdict` with its numbers.
  - `StallWatch` binds one detector to a robot, command and primitive. It gates the command with an `is_held` callable, logs once and fires once.
- **Adapter** (`nav2_adapter.py`).
  - `backup`, `sidestep` and `drive_heading` take `stall_watch: StallWatch | None = None`.
  - Every odometry sample is forwarded with its header stamp (`odom_stamp_sec`).
  - Every tick's twist is judged before it is published. On a verdict the primitive ends through its existing `_finish("FAILED", detail)`: timer cancelled, odometry unsubscribed, **one zero `Twist` published**. After that nothing raw is published, so the relay keeps the wheels at zero.
  - With `None`, the code paths, commands and logs are those of 8933863 (node tests compare the full command streams).
- **Command bus** (`command_bus_node.py`).
  - Loads `safety.stall_abort` from the installed `config/safety.yaml`. With the key on, it subscribes `/safety/holds` once (shared with B3's `FreshLatchWatch`) and passes a `StallWatch` to every backup, pull-off and escort.
  - **Backup and pull-off:** the verdict travels the existing FAILED path unchanged. The leg is FAILED with the detail, and linked waits are released `released: yield failed`.
  - **Escort:** it has no status channel (2.1). On a `stall_abort:` FAILED, the passer's still-active linked wait is ended **FAILED with the same detail** (`_fail_wait`), so M5 and the logs no longer read COMPLETED for an aborted transit. The yielder's hold is untouched. An escort FAILED on its deadline keeps today's behaviour.
  - No auto-retry. Latch, exemptions, floor, B3 and the deadlines are unchanged.
- **Reason and log line.**
  - Detail (on the wire in `CoordinationStatus.detail`): `stall_abort: commanded 0.100 m/s for 3.0 s, measured 0.068 m (expected >= 0.075 m)`, or `stall_abort: input_stale no odometry for 1.05 s (bound 1.00 s)`.
  - One WARN line per abort: `stall abort robot=robot_3 command=<id> primitive=escort phase=drive reason=stall mode=linear commanded_m=0.300 measured_m=0.068 expected_min_m=0.075 window_s=3.00 commanded_rate=0.100 sim_t=149.600`. A turn uses `_rad` keys; `input_stale` uses `odom_age_s=` and `bound_s=`.
- **Traceability.**
  - In m4.log an aborted primitive shows the `stall abort` line, then (backup and pull-off) `status published … status=FAILED`, or (escort) `escort <robot>: FAILED stall_abort: …` and the wait's `status published … status=FAILED`.
  - An executed primitive shows `COMPLETED` (or, for escorts, `escort <robot>: COMPLETED escort complete: moved …`).
  - M5 records only `failed`. The reason is in the status detail and the m4.log line, joined by command id. M5 was not changed, so no new cross-module contract exists.
- **Key.**
  - `safety.stall_abort.enabled`: on only for a literal YAML `true`. Absent from the base `safety.yaml`, which is unchanged; the fragment is `config/safety/stall_abort.fragment.yaml`.
  - The startup line `Command bus started.` gains a suffix only when on.
  - An unreadable file means off, with a `stall_abort config unreadable` warning. That warning appears only when the installed file cannot be read, a case in which the safety monitor already warns.
  - An enabled block with an invalid parameter fails the node at startup.
  - The safety monitor reads the same file and ignores the block.
- **Dependency.** `stall_abort.py` imports pydantic. `package.xml` gains `<exec_depend>python3-pydantic</exec_depend>`. The M4 nodes run in the same container as `swarm_perception`, which already requires it (`run_gemini_er2_demo.sh`: one `ROS_SETUP` for M1, M4 and M5).

---

## 4. Parameters and Their Derivation

All values are from the replay of section 6 (221 primitives) and the bags of section 2.2.

| Parameter | Default | Physical meaning | Derivation |
|---|---|---|---|
| `window_s` | 3.0 s | progress window | 0.30 m commanded at 0.10 m/s. A hard stop fires about 0.72 × window after contact (measured 2.3-3.0 s). That is long enough that the 10 Hz GT and the about 1 cm/0.4 s servo wiggle cannot matter. |
| `min_progress_ratio` | 0.25 | stall when measured < 0.25 × commanded | Contact-free completed primitives: linear minimum **0.85** (median 0.91), angular minimum **0.64** (median 0.66). Pinned plateaus (the lowest ratio over the pinned span, run with a 0.01 threshold): **0.002-0.09**. 0.25 is close to the geometric mean of 0.09 and 0.85 (0.28): ×2.8 above the highest pinned plateau, ×3.4 below the lowest normal travel window, ×2.6 below the lowest normal turn. |
| `grace_s` | 1.5 s | no window may start earlier after a mode change | ramp to 0.08 m/s: median 0.34 s, max 0.61 s (63 exact-start backups) |
| `stale_input_s` | 1.0 s | odometry older than this is stale | odometry period 0.033 s in every bag |
| `min_linear_mps` | 0.03 m/s | below: not linear motion | primitives command 0.10 m/s; the servo never lowers it |
| `min_angular_radps` | 0.15 rad/s | below (and no linear): idle | primitives turn at 0.50 rad/s |
| `min_expected_m` / `min_expected_rad` | 0.06 m / 0.3 rad | windows commanding less are not judged | 20 % of a full window at the primitive's speed |

---

## 5. Tests

- **New files** (75 functions; red first: the detector tests ran against a missing module, an import error):
  - `tests/unit/test_stall_abort.py` (36), the detector, config, log line and suffix:
    - genuine stalls: pinned from start; pinned mid-manoeuvre (the m5D pattern, 0.09 m/s then stopped); slow creep; blocked turn; pinned reverse;
    - false-positive cases: normal drive; turn in place; ramp-up; safety hold zeroing the command; release within grace; zero-command wait; below-minimum speed; brief odometry dropout; deceleration at the end; noisy measurements; turn-to-drive phase change; RTF 0.17 against 1.0;
    - stale input: long dropout, no odometry ever, stale with zero command;
    - config validation and the literal-`true` rule.
  - `tests/unit/test_stall_abort_node.py` (29 with fakes; uses the replay script's `ReplayNode`):
    - adapter: pinned backup ends FAILED with a zero twist, cancelled timer, removed subscription and one log line; key off keeps driving; **command stream identical with and without the watch** (backup and escort); no odometry → `input_stale`; frozen header stamps → `input_stale`; held robot not aborted; blocked sidestep turn → `phase=turn_out mode=angular`; pinned escort drive aborts within 5.9 + 3.0 s; same sim fire time at RTF 0.17 and 1.0 with the wall deadline patched;
    - command bus: no `stall_watch` kwarg with the key off (and on a node without config); watch on backup, pull-off and escort with it on; backup stall → leg FAILED with the reason and linked wait released; **escort stall → passer wait FAILED with the reason, yielder untouched**; escort deadline FAILED leaves the wait as before; `/safety/holds` gates the watch and a corrupt message keeps the previous set; one holds subscription shared with B3; startup line unchanged with the key off;
    - loader: base file off, merged fragment on, unreadable file off with a warning; fragment pinned to the code defaults; base `safety.yaml` has no `stall_abort` key.
  - `tests/unit/test_stall_abort_replay.py` (10), section 6, on the committed fixtures `tests/unit/data/stall_abort/replay_episodes.jsonl.gz` (221 episodes, 440 KB, md5 `7b7821fe87883b95019e5dc0260e53d6`), `expected.json` and `pinned_bag_samples.json`.
- **Existing M4 tests unchanged and passing:** `test_nav2_adapter`, `test_command_bus_node`, `test_safety_monitor`.
- **Full unit suite** (`pytest tests/unit --continue-on-collection-errors`, repo `.venv`, under the resource rule):

  | | failed | passed | skipped | errors |
  |---|---|---|---|---|
  | Before (8933863) | 57 | 6967 | 151 | 3 |
  | After (this branch) | 57 | 7042 | 151 | 3 |

  - The failing and erroring ids are identical (diffed): the 57 known failures and the 3 `pxr` collection errors.
  - The 75 new passes are the 75 new test functions.

---

## 6. Offline Replay

### 6.1 Method

`scripts/stall_abort_replay.py` (module docstring) rebuilds every raw-cmd_vel primitive of a bundle from m4.log and the decision artifacts. It runs each one through the **real `Nav2Adapter` primitive** with a `StallWatch` attached.

- **Commands.** The recorded command stream does not exist: `/cmd_vel` is not bagged in any bundle used here. The replay regenerates it with the primitive's own logic on the recorded poses, so the commands are those M4 computed live, up to the start alignment.
- **Start times.**
  - exact `sim_t=` stamps (hand-over 82, `gate_admit` 40);
  - the replayed backup's own completion for chained pull-offs (45);
  - the GT motion onset for October-7 bundles without hand-over lines (53; turn onset for zero-backup pull-offs);
  - mapped wall time (1).
- **End times.** The next status line, mapped wall→sim by interpolation between neighbouring `sim_t` anchors (+2 s slack for COMPLETED; the replay stops itself on the target).
- **Poses.** GT, or the bag's `/odom` for 35 IB10 episodes. Holds come from the relay's `hold engaged/released` lines in isaac.log.
- **Scope searched:**
  - the 12 campaign bundles with m4.log (v7j: m5D, m5V, cvD ×3, cvH, hoD, ibD ×5);
  - 23 October S1b bundles with m4.log (v3 `batch2`-`batch6`, `churn_wave`, `live_batch`, `resume`);
  - 13 IB10 bag bundles (v3 `ib10_remedy`, `ib10_closure`).
- **Result:** 221 primitives (105 backups, 57 pull-offs, 31 escorts among the completed; 28 not completed).
- **Contact check.** v7m `isaac/vgu_sim/contact_geometry.py` (`b5eaee5`, every authored box plus robot pairs, URDF footprint), read-only.

### 6.2 Must Fire: Primitives Pinned in Contact

| Case | Primitive | Contact (gap) | Contact onset | Abort | Lag | Live end | Sim-s saved | Wall-s at abort / deadline (est.) |
|---|---|---|---|---|---|---|---|---|
| m5D `a15f3fc5` robot_3 | escort, drive | `obstacle_2` (0.0 mm) | 147.3 | **149.6** | 2.3 | FAILED 203.3 | 53.7 | 56 / 335.0 |
| E17 `9cf93ebe` robot_2 | reverse | `obstacle_2` (0.0) | 214.6 | 217.0 | 2.4 | FAILED 244.6 | 27.6 | 48 / 195.1 |
| E18 `8bf906be` robot_5 | reverse | rack/SW_west (−1.6) | 145.0 | 148.1 | 3.0 | FAILED 169.6 | 21.5 | 76 / 195.3 |
| E6 `93100ae3` robot_3 | reverse | rack/SW_west (0.0) | 44.6 | 47.1 | 2.4 | FAILED 71.6 | 24.5 | 61 / 195.3 |
| E6 `a3bbc017` robot_3 | reverse | rack/SW_south (−1.4) | 168.7 | 171.4 | 2.7 | FAILED 195.3 | 23.9 | 68 / 195.2 |
| E7 `c7aeaac1` robot_4 | reverse | rack/NW_west (0.0) | 46.3 | 48.6 | 2.3 | FAILED 80.4 | 31.8 | 45 / 195.2 |
| E17 `6745a136` robot_3 | yield backup | `obstacle_1` (−1.5) | 153.7 | 156.5 | 2.8 | FAILED 177.1 | 20.6 | 82 / 191.4 |
| E11 `7a47f2f7` robot_4 | yield backup | `obstacle_1` (−1.9) | 70.6 | 73.6 | 2.9 | FAILED 102.1 | 28.6 | 56 / 209.5 |
| E12 `d374802a` robot_2 | reverse | rack/NW_north (−1.5) | 58.9 | 61.8 | 2.9 | **COMPLETED** about 62.6 | — | — |
| E20 `6cf402ed` robot_3 | escort, drive | **robot_1** (−0.2), pushing the parked yielder | 252.6 | 255.3 | 2.7 | **COMPLETED** about 263.4 | — | — |

Columns:

- Contact onset: the first GT row with a footprint gap ≤ 5 mm.
- Lag: abort minus contact onset, sim-s.
- Live end: mapped ROS sim time of the primitive's terminal line.
- Wall at abort: start + (abort − start) × (live wall duration / live sim duration), assuming constant RTF within the episode. The deadlines are measured from m4.log.

- **Every abort is a physical contact**, and every abort fires 2.3-3.0 sim-s after contact onset, at 0.22-0.25 of commanded progress. The verdict is `stall` in every case; no `input_stale` occurs on recorded data.
- **Against the owner's list.** Of the October reverses named as pinned or in contact (v7l §8.6), 5 of the 7 deadline failures fire (`9cf93ebe`, `8bf906be`, `93100ae3`, `a3bbc017`, `c7aeaac1`). `ea23b1a7` robot_1 and `d5541ff0` robot_2 stay silent because the robot was latch-held, so its wheels were zeroed, when it stopped (section 6.4). Two October **yield** backups the reverse guard does not cover (`6745a136`, `7a47f2f7`) also fire.
- **Behaviour change on two completed primitives.** Both pressed into something until the primitive scraped free or completed:
  - `d374802a` robot_2 (the reverse guard's "contact" case) would end FAILED about 0.8 s before its live completion;
  - `6cf402ed` robot_3 pushed the parked robot_1 (footprint overlap 0.2 mm, centre distance 0.158 m) for about 3.5 s; it would end FAILED 8 s early, and its wait FAILED.
  
  These are aborts on genuine contact, not false positives, but they change the outcome of two recorded primitives.

### 6.3 Must Not Fire: Completed Primitives

- **Completed primitives:** 193, all three groups, real odometry in 35 of them. With the 2 contact cases of 6.2 excluded, **0 of 191 fire**.
  - **Closest margins (lowest judged ratio):** travel **0.848** (S1b E28 yield backup), turns **0.638** (S1b E29 pull-off turn), against the 0.25 threshold.
  - **By group:**

    | Group | Bundles | Completed | Lowest travel ratio | Lowest turn ratio |
    |---|---|---|---|---|
    | campaign (Nov) | 12 | 53 | 0.887 | 0.640 |
    | S1b (Oct) | 23 | 66 | 0.848 | 0.638 |
    | IB10 bags (Oct) | 13 | 74 | 0.894 | 0.638 |

  - **By primitive:** backups 105 (judged 103), pull-offs 57 (57 turns, 9 drives judged), escorts 31 (30). Primitives shorter than grace plus window are never judged while moving freely (3 short recedes).
- **Replay alignment, not detector behaviour.** 5 COMPLETED backups in E13 and E17 do not reach their target inside the mapped window (anchors are sparse late in those runs). They are counted as "no fire", which they are. Earlier iterations of the replay showed artificial fires from late or early starts in October-7 bundles. They were fixed in the replay, by onset-based starts, not by changing the detector.

### 6.4 Neither: Live Failures or No Terminal Line, Not Fired (21)

- **19 of the 21 were latch-held when they stopped.** The relay's `hold engaged` for the robot falls within 1.5 s before its last motion (or covers the whole primitive). Their nearest robot's footprint gap is 0.20-0.35 m: a bystander latch.
  - **No wheel command reached them, so silence is correct by design:**
    - cvD ×3 and cvH convoy escorts (`35084986`, `759bdb94`, `ab6a10c5`, `08f4dca0`): latched against robot_3 or robot_1 at 0.41-0.44 m centre distance. This answers "cause not examined" in the campaign report §8.7.4;
    - S1b backups `63f8d1ce`, `984e3bdf`, `ea23b1a7` r1, `ede6d209` r3/r4, `150b95a6`, `09647748`, `93100ae3` r1, `f06c33b3` r4;
    - S1b escort `56b599af`;
    - escorts `8066f542`, `1feb2c4e` and `07da775d`, held from before admission and never moved.
  - **`d5541ff0` robot_2 and `ea23b1a7` robot_1** reached a box face (−0.4 mm and 7.6 mm) at the moment the latch engaged. They then sat latched until the 195 s deadline. That is B3's domain (fresh-latch fast-fail), not this key.
- **The other 2, S1b pull-offs `c5a5e687` robot_1 and `6d37a549` robot_1.** The hold engaged about 1 s after the last measured motion (the turn-back stopped 0.22 rad short in `c5a5e687`). That is too short for a 3 s window, so they are silent.

---

## 7. Limits

- **Only raw-cmd_vel primitives** (backup, pull-off, escort). Nav2 legs (reroute, navigate, base mission) are not watched; they have Nav2's progress checker and collision monitor.
- **Progress, not contact.** A robot sliding along a face or pushing something that yields at 25 % or more of commanded speed is not detected. The m5V grazes (5.5 and 19 mm, completed) are not stalls.
- **Latch-held robots are never judged.** A primitive latched at a face still runs to its deadline (6.4).
- **Odometry must be a physics pose.** True for Isaac's `IsaacComputeOdometry` (2.2). On a real robot with wheel odometry, wheel slip reads as motion, and the detector would need IMU, visual odometry or M1.
- **Clock.** It needs `use_sim_time` on the command bus (as launched). A wall node clock against sim-stamped odometry gives an immediate, loud `input_stale` abort. A frozen sim fires nothing; the monotonic deadline remains.
- **Holds arrive by message.** `/safety/holds` is published on change and at 1 Hz. A missed engage message gives at most about 1 s of apparent stall, below the about 2.2 s a hard stop needs. A missed release keeps the detector idle (conservative).
- **After an abort the robot is not kept parked by this mechanism.** The FAILED status makes the coordination client resume the base mission under Nav2 (existing behaviour for every FAILED). No further raw command is published. Owner question: should an aborted robot instead be held, e.g. by a short wait?
- **The replay is a reconstruction.** Commands are regenerated, starts and ends are aligned (6.1), and holds are mapped from wall time. Turn-phase stalls are covered by unit and node tests and the pinned bags only; no recorded raw-primitive turn was pinned.
- **Not run live.**

---

## 8. What a Kit Needs to Enable It Alone

- **Overlay.** Merge the `safety.stall_abort` block of `config/safety/stall_abort.fragment.yaml` into the safety file the kit installs. Leave every other key byte-identical; the base `safety.yaml` is unchanged.
- **Runtime delta vs the pin (68e67b5 = 8933863 for these files).** Colcon-rebuild `swarm_execution`; the installed copy is what runs.

  | File | md5 (this branch) | md5 at the pin |
  |---|---|---|
  | `ros2_ws/src/swarm_execution/swarm_execution/nav2_adapter.py` | `aa070a77266cd1d1f64651942febaed8` | `f139305c873b9b4997fb08a525845c11` |
  | `ros2_ws/src/swarm_execution/swarm_execution/command_bus_node.py` | `ba6d7a13393ef4e7bf833690711a2673` | `caad9edc40394557159d5d916e1e2aff` |
  | `ros2_ws/src/swarm_execution/swarm_execution/stall_abort.py` (new) | `8dd7b9739d87b44e6cbb81752e9d19b1` | — |
  | `ros2_ws/src/swarm_execution/package.xml` (adds `python3-pydantic`) | `e77c52ceda66bfc7dbfdaea44967814b` | `2cf264526f5c5eb9c88807669291477a` |
  | `config/safety/stall_abort.fragment.yaml` (new, merged into the installed safety file) | `f1ffd432821b3c71547f97c70d90181b` | — |

- **Arm check, per episode.** m4.log contains `Command bus started. stall_abort=True window_s=3.0 min_progress_ratio=0.25 grace_s=1.5 stale_input_s=1.0 min_linear_mps=0.03 min_angular_radps=0.15 min_expected_m=0.06 min_expected_rad=0.3`, and no `stall_abort config unreadable`. An older tree prints `Command bus started.` alone, so the check fails loud.
- **Alone.** Escort and reverse obstacle guards, contact logging, B3 fast-fail, the 0.20 m floor and the scoped exemption stay at the configuration of the reference run being compared, and no other new key is on.
- **Post-take gate:**
  - **Each abort line has its FAILED.** Every `stall abort robot=R command=C` line is followed by `status published command=C robot=R status=FAILED` (backup, pull-off) or `escort R: FAILED stall_abort:` plus the wait's FAILED (escort).
  - **Each abort was a contact.** GT shows contact (footprint gap ≤ 5 mm) within 3.5 s before each abort, and GT speed below 0.01 m/s within 1 s after it.
  - **No abort on free motion.** No `stall abort` on a primitive whose GT shows free motion. Run `scripts/stall_abort_replay.py` on the bundle: replayed fires must equal the live `stall abort` lines.
  - **Counts.** Report the numbers of `input_stale` and `stall` aborts.

---

## 9. Proposal: Deterministic Live Validation (Describe Only; Not Built)

- **Label:** SAFETY TEST, not an experiment cell. Mock backend (`config/mock_decisions`), so there is no API call.
- **Scene.** One robot in an open aisle, with a static box authored 0.6 m behind it.
  - In run A the box is declared in `static_obstacles`.
  - In run B it is authored but undeclared, i.e. not given to grounding, so the grounding guards cannot see it.
  - A second robot is placed outside every latch radius, so no hold can mask the test.
- **Scripted decision.** A mock `reverse` with `backup_distance_m` 1.3 drives the robot backward into the box. An escort variant (a mock `yield` with `passer_escort_distance_m` through the box) covers `drive_heading`.
- **Takes:**
  1. Key on, box present. Expect contact at about 0.55 m of travel, then `stall abort … reason=stall` within about 3 sim-s, the leg FAILED with the reason, GT speed 0 within 1 s, and M5 `resolved status=failed`.
  2. Key off, same scene. Expect FAILED `backup timed out` at 195 wall-s: the control.
  3. Key on, box removed. Expect COMPLETED with no `stall abort` line: the false-positive control.
- **Gate.** The section 8 checks, plus the replayed fire time within ±0.5 s of the live one.

---

## 10. Verified and Inferred

| Claim | Status |
|---|---|
| `/odom` is the chassis physics pose and equals GT to 0.1 mm | verified (26 robot-runs, `scripts/stall_abort_odom_check.py`; graph code) |
| Pinned robots' odometry shows no movement under commanded wheels | verified (2 recorded bags, 0.3 and 1.4 mm); inferred for the deadline failures from their deadline ending (status detail not logged) |
| M1 goes STALE when pinned against the m5D island | verified (`m5_scene.jsonl`) |
| GT clock = ROS sim − 0.50 s (bag runs); per-bundle offset 0.47-0.64 s estimated from M1 | verified (bags); estimated (others, ±0.03 s) |
| The detector fires on all 10 contact stalls 2.3-3.0 sim-s after contact, and on none of 191 contact-free completed primitives | verified by replay (reconstructed commands; section 6.1 caveats) |
| The 19 quiet live failures were latch-held | verified (relay hold lines mapped to sim time, GT) |
| Key off is unchanged | verified (tests: no kwarg passed, identical command streams, startup line) |
| The abort saves 20-54 sim-s (45-82 wall-s instead of 191-335 wall-s) | estimated (constant-RTF mapping) |
| Live behaviour | not run |
| Full unit suite after the change | verified: 57 failed / 7042 passed / 151 skipped / 3 errors, failing ids identical to the baseline |

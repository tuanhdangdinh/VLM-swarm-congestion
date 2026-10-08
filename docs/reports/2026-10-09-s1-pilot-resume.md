# S1 Pilot Resume: New-VM Bring-Up, Environment Smoke, Echo Episode 1 and Pin Stop

**Prepared:** 2026-10-09

**Revision history:**

- Initial draft: bring-up of the new Isaac VM, the Phase 2 environment smoke against the old-VM reference, and the first closed-loop S1 echo-mock episode on `feat/v3-integration@4bfcd43`, which ended the program at the pin stop rule.

---

## Summary

The new VM is project-ready, and the environment smoke passed on its first attempt. It matches the old VM like for like: RTF 0.396 against 0.397 and a cycle of 840 s against 825–838 s.

Episode E1 (seed 978442588, echo mock, suppression on) gave the **first closed-loop run of the A13 chain**. One executable yield ran end to end:

- backup line-hold;
- relative escort;
- gate-clearance release of the yielder and both off-lane waits.

Two robots were then **physically pinned** by the pre-registered commanded-vs-moved test, so the stop rule fired:

- robot_3 at the SW rack corner, the same pose and leg as the 2026-10-08 pilot;
- robot_1 at the gate_S jaw corner, a **new** pin class. robot_1 drove into the jaw while resuming its base mission from the yield's sidestep park pose.

E1 was left to run to its horizon for data. **E2 and the live E3 were not run.** Live API spend was 2 preflight calls, under $0.01.

| Question | Answer |
|---|---|
| Bring-up | **Met.** The tree is `4bfcd43` (903-file manifest OK). Three shims are documented in [Bring-Up](#1-bring-up): the old-VM orchestrator pin, the robot-asset folder move, and kit-cache ownership. No launcher shim was needed. |
| Isaac build on this box | Local **source** build of tag `v6.0.1` (`045ca8b5`, "Isaac Sim Update 6.0.1"). VERSION reads `6.0.1-rc.7+mr.0.045ca8b5.local`. The running Kit stamps are App 'Isaac-Sim Python' Version 6.0.1, Kit `110.1.2+production.326809.f9bf0dda.gl`, Kernel `210.1.11+release.13746.80f6dc72.gl`. These are **identical, string for string, to the old VM's Kit log** (step-0 smoke `kit_20261007_083354.log`), so `rc.7` is only this source tree's VERSION label. |
| Environment smoke (attempt 1/3) | **PASS.** 2/2 arrivals accepted (0.10 / 0.09 m), M1 0 STALE, audit keys present, Option B tail ended 10 s after Isaac exited, 0 jump-back warnings. |
| Smoke timing vs old VM | Cycle **840 s** (old 825 / 838). RTF by M1 scene stamp vs M5 wall clock: **0.3963** (old bundle, same metric: 0.3967). GT arrivals 85.5 / 107.6 sim-s (old 86.5 / 108.8). |
| fastShutdown / Option B | `--/app/fastShutdown=True` on every boot command line. This is **the same default as the old VM**. `SimulationApp.close` → process gone took ≤ 2 s in the smoke and ≤ 3 s in E1, against 1–2 s on the old VM. The stop flag → exit took 2.2 s. The Option B tail ended 10 s (smoke) and 45 s (E1 grace) after exit, as on the old VM, so there is no regression at poll resolution. A new rc.7 shutdown watchdog hung one asset-import `close()` for 120 s (see Caveats). |
| E1 gate (echo) | **OK.** The first artifact carries `mock_mode=echo`. Dispatches happened. |
| A13(iv) closed loop | See [A13(iv) Verdicts](#4-a13iv-residual-verdicts). Backup line-hold, escort tracking and the M4 release path **work**. The sidestep park is safe, but the post-yield resume from it **pins at the jaw**. |
| Stop rule | **FIRED** on robot_3 (SW rack) and robot_1 (gate_S jaw). E2 and E3 were not run. |
| Live costs | E3 was not run. Preflight: 2 calls, about 2.3k tokens, under $0.01. |

This is **pilot-only**. `mapd_5` is not registered, every run was RECORD=0, and nothing here enters a scored dataset.

---

## 1. Bring-Up

### Box

| Item | Value |
|---|---|
| VM | `vgu-vgu-thu-base-isaac-workstation-vm`, project `project-5b0644ea-c6bd-4d13-a4a`, `asia-southeast1-b`. The old VM was not touched. |
| Host | Ubuntu 22.04.5, kernel 6.8.0-1070-gcp, NVIDIA L4 24 GB, driver 595.91.07, Docker 29.8.2, 32 GB RAM |
| Isaac | `/home/ubuntu/IsaacSim` → `/home/ubuntu/IsaacSim-source/_build/linux-x86_64/release`, a local source build of tag `v6.0.1`, commit `045ca8b5` |
| SSH user | `tuanhdangdinh` (sudo). `/home/ubuntu` is mode 0750, so everything runs through `sudo`, and Isaac through `sudo -H -u ubuntu` as `fc_launch` does |

### Phase 0: warm-up

- **GUI first boot.** `autorun.sh` started the GUI Kit (`isaacsim.exp.full.kit`) on boot.
  - It spent about 280 s in the RtPso async compile and logged "App is loaded" at **410.6 s**.
  - After that it idled at about 380% CPU while rendering the viewport.
  - It was stopped with SIGTERM and exited cleanly in 1 s.
  - `autorun.sh` relaunches this GUI on **every** VM start, so the drivers now refuse to launch while `pgrep -f '[k]it/kit '` is non-empty.
- **Headless first boot.** The GUI warm-up does **not** warm the headless app.
  - The first `run_simulation` boot spent 83 RtPso wait lines (more than 335 s) compiling.
  - It listed `/camera/image_raw` only after **493 s**.
  - `fc_launch`'s 300 s camera wait would have voided a cold smoke. A standalone warm-up boot, with `fc_launch`'s exact environment and a stop flag, was therefore run first.
- **Warm boots.** Every later boot showed 0 RtPso lines, and Isaac had topics live within about 40 s.

### Phase 1: steps and shims

| Step | Result |
|---|---|
| Tree | `git archive 4bfcd43` was extracted to `/home/ubuntu/vgu-vlm-swarm`, owned by ubuntu, the old VM's `REPO`. All files were `touch`ed, and the 903-file md5 manifest is OK. No rsync was used. |
| **Shim 1: pristine orchestrator** | The git copy (`677a4cd0`) was replaced by the **old-VM pin `1f656533`**. The repo driver `scripts/vm/v2_final_run.sh` hard-codes that md5, and the step-0 smoke overlay `74b908d4` is pin plus goals. `load_config` on the pin plus the seed-1 S1 overlay equals `load_config` on git plus the same delta across all 61 fields. As on the old VM, the manifest fails on exactly this one file. |
| Secrets | `.env` was piped over ssh stdin to `/home/ubuntu/vgu-vlm-swarm/.env` (= `/ws/.env`), ubuntu 600. Its md5 equals the Mac source. It was checked by key name only (GEMINI, OPENAI, ANTHROPIC, DEEPSEEK, ZHIPUAI). |
| Container | `docker run -d --name vgu_ros --restart unless-stopped --network host --ipc=host -v /home/ubuntu/vgu-vlm-swarm:/ws -w /ws ros:jazzy sleep infinity`, using image `ros@sha256:066420e0…`. It follows the 2026-09-16 recipe plus `python3-requests`, `python3-pil` and `ros-jazzy-cv-bridge`, which the imports needed. `--restart unless-stopped` is new. |
| Versions | navigation2 / nav2-bringup / dwb-core 1.3.13 (2026-09-21 to 2026-10-06 builds), fastrtps 2.14.6, rmw-fastrtps-cpp 8.4.4, cv2 4.6.0 (no `ArucoDetector`, so the legacy path runs as designed), pydantic 2.14.0, jsonschema 4.10.3, numpy 1.26.4 |
| colcon | `colcon build --merge-install` **without** `--symlink-install`. Every `fc_launch` rebuild and restore uses plain merge-install, and the installed-copy md5 checks need real files. 5 packages built. The import gate passed: backend_factory with gemini, `grounding_view`, `command_grounder`, `maneuver_geometry`, `reasoning_pipeline`, `task_stream`, `reanalysis_suppression`, `perception_node`, `swarm_execution`, `swarm_interfaces.msg` and `cv_bridge`. 133 installed files are md5-equal to source, with 0 symlinks. |
| S1-critical md5 | Live-mounted: `grounding_view` `64ab60ce`, `command_grounder` `c93b350d`, `maneuver_geometry` `0bcd09a0`. Installed: `reasoning_pipeline` `792fa049`, `task_stream` `739ce1e9`, `reanalysis_suppression` `0079ec57`, `nav2_adapter` `21b010c2`. Config: `s1_dynamic.yaml` `956f64c3`, `rag.yaml` `e18c723c`. The `bottleneck_merge` map (pgm `3f475603`, yaml `36188f53`) matches the old VM. `runner.py` `4a59bf92` matches step 0. |
| Assets (as root) | `import_turtlebot3` (tracked URDF) → `build_warehouse` → `build_scenario` (smoke cell + `mapd_5`) → `validate_simulation` PASS ×2. `turtlebot3_burger.usda` `b98f9695`, `warehouse_base.usd` `867c60e8`. **`mapd_5.usd` `d7776daa` is byte-identical to the old VM's seed-1 USD.** |
| **Shim 2: robot asset folder** | The rc.7 URDF importer wrote to `turtlebot3_burger_1/`, because the URDF's own folder `turtlebot3_burger/` already exists. The asset was written and validated (wheel drives, fixed base disabled). The `.usda`, `payloads/` and `Textures/` were then moved into `turtlebot3_burger/`; the payload references are relative. The importer's `close()` then hung (see Caveats). |
| **Shim 3: kit-cache ownership** | The root Isaac builds wrote root-owned files into the kit-kernel cache under `~ubuntu/.cache/packman/chk/kit-kernel/…/{cache,data,python}`. The first ubuntu boot then failed: "Failed to acquire exclusive lock to data store", an OGN cache Permission denied, and `ROS2CameraHelper` unrecognized. Fixed by `chown -R ubuntu` of the kit-kernel tree. `build_usd.sh` repeats the chown after every root build. |
| FASTRTPS / GPU env | `fc_launch` sets `ROS_DISTRO=jazzy`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, the Isaac jazzy `LD_LIBRARY_PATH`, `FASTRTPS_DEFAULT_PROFILES_FILE=$REPO/config/dds/fastdds.xml` (UDP-only) and `PYTHONPATH`. Its hard-coded `/home/ubuntu/IsaacSim/python.sh` and `exts/isaacsim.ros2.core/jazzy/lib` paths resolve through the symlink, so **no launcher shim was needed**. Isaac's `setup_ros_env.sh` would default to humble on 22.04, which is what the autorun GUI ran, but the explicit jazzy wins. In-container data was verified, not just discovery: `/clock` at 13.3 Hz, plus `/robot_1/odom` and camera echoes. |
| Kit logs | Headless logs go to `…/kit-kernel/110.1.2+production.manylinux_2_35_x86_64.release/logs/Kit/Isaac-Sim Python/6.0/`, the old VM's `KITDIR` |
| Preflight | `scripts/preflight_backend.py --backend gemini` returned PREFLIGHT OK, served by `gemini-robotics-er-2-preview`. It was accidentally run twice: 2 calls, about 2.3k tokens. |

---

## 2. Environment Smoke

The setup is the step-0 stage-1 acceptance cell, run unchanged through the repo driver `scripts/vm/v2_final_run.sh`:

- cell `head_on_asymmetric_w0p2_eopen_bshort_o0`, mock `head_on_yield_robot_2_once.json`, seed 42;
- overlay `74b908d4`;
- `REC_SEC=1000`, `SIM_SEC=1200`.

The run was `smoke_a1`, STAMP `20261008_185139`.

| Criterion | New VM | Old VM (reference) |
|---|---|---|
| Arrivals (M5) | 2/2 accepted: robot_1 (2.6, 0) at 0.10 m, robot_2 (−1.5, 0) at 0.09 m; 0 rejected | 2/2 (0.10 / 0.09) |
| GT arrivals | 85.5 / 107.6 sim-s | 86.5 / 108.8 |
| M1 | 0 STALE (905 STOPPED, 236 MOVING, 215 SLOW) | — |
| Artifacts | 2: 1 grounded `yield` (`ok`) + 1 `vlm`/`none`. Audit keys present: `dispatched_command`, `dispatched_robot_ids`, `dispatch_dropped_robot_ids`, `plan_dispatch_order_source=chi`, `dispatch_order_source`. 0 Traceback, 0 openai/http. | same shape |
| GT / manifest | 3001 lines, last 300.0, `completed: true` | same |
| Nav2 | 0 jump-back; `Failed to create plan` r1 2 / r2 1 | 3 / 1 |
| Bring-up | Isaac PID +17 s, Nav2 2/2 active after 4 s, all components +86 s | +16 s, +77 s |
| **RTF** (M1 scene stamp vs M5 wall, 12→300 sim-s) | **0.3963** (60-row segments 0.364–0.417) | **0.3967** (0.363–0.411), recomputed from the step-0 bundle |
| Shutdown | `--/app/fastShutdown=True`. `SimulationApp.close` 19:05:13; `run_simulation` processes gone by 19:05:15 (1 Hz sidecar), so ≤ 2 s. | `--/app/fastShutdown=True`. close 08:46:59; gone by 08:47:01 (sidecar), so 1–2 s. |
| Option B | "Isaac exited (PID 38073 gone at 19:05:16); ending the M5 tail after 10s grace (741s into the tail)" | 735 s into the tail |
| **Cycle** | **840 s** from `fc_launch` start to `logs saved` (wrapper 842 s) | 825 s (838 s in the Option B smoke) |
| Restore | RESTORE OK (`1f656533` src and installed, rag `e18c723c`) | — |

- **RTF figure.** The brief's old-VM figure of "RTF ~0.21" could not be reproduced from the reference bundle with this metric, which gives 0.397. The two boxes run the 2-robot cell at the same RTF.
- **New reference.** These numbers are the new reference for this box.
- **Free-flow equivalence stays a registered OPEN item.** It covers zone, box, Isaac source-build-vs-automator, Nav2 1.3.13 rebuilds and pydantic 2.14. Nothing here harvests free-flow, and no CONFIRMATORY use may assume equivalence until it is measured.

---

## 3. Episode E1

### Condition

| Item | Value |
|---|---|
| Label / STAMP | `s1r_E1_seed1_echo` / `20261008_190705` |
| Overlay | `cdf3e0b8` = pin `1f656533` + the `4bfcd43` header snippet (7 keys replaced, 4 appended, `release_stagger_sim_sec: 4.0`) + `reanalysis_suppression: { enabled: true, pose_epsilon_m: 0.05 }`. `yaml.safe_load` equality is asserted. `load_config` on this overlay equals git base plus the same delta, across all 61 fields. |
| Run line | `SCENARIO=mapd_5 MAP_SCENARIO=bottleneck_merge MOCK_ECHO=1 BACKEND_ID=mock SEED=978442588 RECORD=0 REC_SEC=4800 NAV2_ACTIVE_TIMEOUT_SEC=360`, grace 45 s, through the resume driver `s1_run.sh` (explicit `MOCK_ECHO`, a GUI-Kit refusal gate, and pristine/seed/USD refusals) |
| Scenario | `mapd_5.yaml` `df1c6504` (`4bfcd43`, seed 1); USD `d7776daa` |
| Floor | off (junction-only, not set) |

### Outcome

| Measure | Value |
|---|---|
| Bring-up | Nav2 5/5 active at the first poll, with action servers live about 1 min 54 s after launch. 1 attempt. |
| Gate | First artifact `b7b526a5`: `diagnostics.mock_mode = "echo"` **OK** |
| RTF | **0.179** (scene vs M5 wall, 22.2–600.5 sim-s), 60-row segments 0.170–0.211. The pilot measured 0.164 on the old box. Isaac lifetime 600 sim-s in 3352 wall-s. |
| Release Δ (sim stagger) | 4.000 / 4.000 / 4.034 / 4.000 sim-s, **all in (0, 4.42)**. The releases are r1 22.233, r2 26.233, r3 30.233, r4 34.267, r5 38.267. The episode start sim (first scene) is 22.233. Release → first motion: 2.9–4.5 wall-s. |
| Tasks | **1 / 25** (robot_2 at N: issued 26.2, arrived 47.3, done 52.3). `complete` false, makespan null. |
| Analyses | **46**: 1 single-robot (robot_3) `yield refused: no other involved robot to pass`, then 8 s wait; **1 executable yield** (`cb78cd48`); 44 four/five-robot analyses that ground `dynamic_arms:ambiguous` with **0.00 m rear room for every robot**, then `yield refused`, then 8 s waits to all. |
| Suppression | **0** `reanalysis suppressed` lines. Every refused analysis still **dispatches** 8 s waits, so the no-dispatch reference (clause (c)) never arms. This is the A13(i) dispatched-loop residual, measured live. The cadence is set by 8 sim-s waits plus the 15 s cooldown: 46 analyses per episode, against 216 in the pilot without dispatch. |
| Arm B | `blocked_path/anomaly` 45, `head_on/deadlock` 1 |
| M1 | 0 STALE or absent in 5 × 2596 rows. Position error median 4 mm, p95 8 mm. θ on stopped robots: median 0.83°, p95 2.77°, max 4.86°; robot_4 carries a constant 2.77° bias. |
| Nav2 | 0 "Failed to make progress", 0 spin and 0 backup recoveries on **every** stack. robot_1 logged 45 "Begin navigating" and 176 cancels. 0 jump-back warnings, 0 Traceback. |
| Safety monitor | The min-distance (0.45 m) latch held robot_2 and robot_4 (N arm, 0.41 m apart) and robot_3 and robot_5 (0.385 m) for most of the episode. |
| Hold backstop | **Not violated.** The one yielder hold ran from `gate_admit` at 77.233 to `gate_release reason=clearance` at 103.333: 26.1 sim-s, or 134 wall-s. **The 45 s backstop counts SIM seconds.** `command_bus_node.py` arms it with `create_timer(_hold_sec, …)` on a node launched with `use_sim_time: true`. A 45 wall-s backstop would have fired at about 85 sim-s, and it did not. The only dwell (robot_2, 24.3 wall-s) had a blocked departure, so there is no new unblocked gate sample. See Open item 8. |
| hard_contact / floor | none logged |

### The pins (stop rule)

The pre-registered commanded-vs-moved test was applied to both robots.

| Robot | Where | Commanded (bag) | Moved |
|---|---|---|---|
| robot_3 (S → Wp) | SW rack corner, GT (−0.572, −0.528), heading −176°. Static from about 38 sim-s, **the same pose and leg as the 2026-10-08 pilot**. Centre-to-corner 0.077 m. | `/robot_3/cmd_vel` 0.161 m/s, −0.71 rad/s over sim 103.4–104.6 (160 msgs) | odom x/y 0.4 / 1.4 mm over 76.5–104.6. GT θ −177.20 to −175.86° over 102.5–106.5. A free robot would turn about 49° and translate about 18 cm. **Pinned.** |
| robot_1 (cb78 yielder, → E) | gate_S jaw corner (0.7, −0.275), GT (0.677, −0.225). Centre clearance 0.055 m, under the 0.07 m smallest half-extent, so it overlaps at any heading. It crept to 0.038 m by 445 sim-s. | 0.085–0.114 m/s, 0.87–1.50 rad/s over sim 149.1–150.1 | odom 0.5 / 0.2 mm; GT θ −19.62 to −19.33° (a free robot would turn about 60°). **Pinned.** |

- **Evidence.**
  - `evidence/E1_r3_swcorner_*/bag` is 147 s of robot_3's local and global costmaps **with `costmap_updates`**, plus `cmd_vel`, odom, plan, scan, published footprint and scene_state. This fills the pilot's evidence gap.
  - `evidence/E1_r1r3_pin_sample/bag` is 60 s of cmd_vel and odom for robot_1, robot_3 and robot_5, plus robot_1's costmaps, footprint and plan.
- **Layer 2 holds the wedges in place.** The 8 s waits are re-dispatched about every 11 sim-s. Each one cancels the Nav2 goal before the progress checker can fire, so the spin recovery that freed robot_3 at 325 s in the pilot never ran: 0 spins on every stack.
- **The rule fired on both robots.** Per the precedent, E1 ran to its horizon without the stop flag, and nothing was launched after it.
- **Self-clearance.** Neither robot self-cleared by 600 sim-s.

---

## 4. A13(iv) Residual Verdicts

One executable yield, `cb78cd48`, ran end to end. It is the first closed-loop run of the A13 chain. The two robots were in a head-on at the A55-E gate: robot_1 (N → E) arrived while robot_5 still held E.

Grounding:

- **Roles.** robot_1 yields to robot_5: `node_handoff:robot_1->robot_5`, `dynamic_arms:lane:x`, `order=lane_scoped:robot_2,robot_3`.
- **Backup.** 1.36 m with `backup_line_hold`, then a sidestep of `pull_off_lateral_m` −0.36 to the target (0.301, −0.314).
- **Escort.** 2.35 m at heading π, relative to reference yaw π.
- **Waits.** robot_2 and robot_3 get unlinked 120 s off-lane waits, and robot_5 a linked wait.

Timeline (GT sim-s): dispatched 48.6 → backup 48.5–63 → turn → sidestep 68.5–73 → turn back → `gate_admit` 77.233 → escort 77.2–103.3 → `gate_cleared` (moved 2.351 m) → `gate_release reason=clearance` 103.333.

| A13 item / residual | Closed-loop verdict |
|---|---|
| `backup_line_hold` (spawn-frame fix) | **WORKS.** 1.369 m achieved (grounded 1.36). The maximum lateral deviation from the start-heading line was **1.2 mm**. The held line is the start heading, which was 2.3° off the lane axis, so the robot ended 5.3 cm off the axis. |
| Sidestep (pull-off) | **Executed** 0.373 m (grounded 0.36), with 1.3 cm lateral deviation. The sidestep is relative to the post-backup pose, so the park landed at (0.306, −0.384), **0.07 m past the grounded target**. That target was computed from the scene pose: y 0.046 − 0.36. |
| "Sidestep 0.053 m from the jaw" | **Not tested at the jaw.** The live backup started from x 1.659, so the park was at x 0.306, **0.40 m** (centre) from gate_S. The replay's 0.053 m case (park x 0.556) did not occur. |
| **Post-yield resume from the sidestep park** | **FAILS: new pin class.** On release, robot_1's base mission to E drove diagonally (about 30°) from y −0.38 toward the 0.55 m gate mouth (\|y\| < 0.275). It overlapped the gate_S jaw corner at **105.1 GT-s, 2 s after release**, and stayed pinned. This is the A7a corner-wedge class at the gate jaw. It is **set up by the yield's off-lane park pose**, not by the sidestep motion. |
| Relative escort turn (heading from the passer's current registry goal) | **WORKS mechanically.** 2.355 m along heading π, max lateral **3.5 cm**, against the 12 cm budget (the pilot projected 5.7 cm p95 from M1 θ). M4 reported `escort complete: moved 2.351 m`. |
| Live escort headings use registry goals (replay used snapshot goals) | Heading π matched the replay. **But the fixed 2.35 m clear distance carried robot_5, whose registry goal is S, 0.4 m past the S-arm mouth** to (−0.40, −0.04). Its resumed mission then drove it south-west, where it stopped under the min-distance latch 0.385 m from pinned robot_3. The escort length clears the yielder; it does not stop at the passer's turn. |
| M4 release path | **WORKS (escort path).** `gate_cleared` released the yielder **and** both off-lane waits (robot_2, robot_3) at the same instant (103.333). The yielder hold was 26.1 sim-s (134 wall-s), under the **45 sim-s** backstop, so the backstop never fired. The **no-escort** single-passer path, which releases all waits at hold start, was **not exercised**: no escort dropped. |
| 120 s off-lane waits "tight" vs backup + hold + escort | **Not tight. They are SIM-s timers** (`use_sim_time: true` in `execution.launch.py`, `create_timer(duration_sec)`). The chain released them at 54.7 sim-s, leaving 65 sim-s of margin, with **0 expiries**. In wall time that is 290 s. The "8 s" refusal waits are 8 sim-s, about 45 wall-s. |
| Clearance set vs crossing order (an in-reach `goal_behind` robot can strip escorts) | **Not exercised.** The lane-scoped order kept the escort, and no `goal_behind` robot was in reach. |
| Stage 2 live selection | **Unexercised.** The echo mock skips stage 2 (`skip_reason=no_backend`), and E3 did not run. |
| Rear room 0.00 m (A13(ii), fixed on replay) | **Recurs closed-loop in the post-yield gridlock.** 44 / 46 analyses ground `dynamic_arms:ambiguous` and report 0.00 m for every robot. Whether this is a true zero (all robots boxed in) or the defect class in the ambiguous-arm view is **not established here**. It is a Step-6 item. |

---

## 5. Wandering vs Park

| Count | E1 |
|---|---|
| Finishers (`robot_done`) | **0** |
| Occupied-node approaches (pre-registered rule) | 2 |
| robot_1 → E onto held robot_5 at 37.5 GT-s | This was before robot_5's +16 sim-s release (38.27). The **sim stagger removes the Δ-window artifact but not the E handoff itself**: the N → E leg (3.85 m) arrives inside robot_5's 16 s hold. |
| robot_4 → N onto dwelling robot_2 | The N-arm handoff, as in the pilot. It froze under the min-distance latch. |
| Parked-finisher events / tail gridlock caused by a park | 0 / 0. The tail gridlock that did happen (from about 106 sim-s, 0 task progress) came from pins and latches, not from parking. |

**Recommendation: S1-1 stays UNDECIDED.** For the second episode running, no robot finished a queue. The datum needs an episode free of physical pins. Mechanistically, both handoff nodes (E, N) still produce head-ons at the node, so a parked finisher would add more of the same class. That remains a reason to expect the wandering analog to matter, not evidence that decides it.

---

## 6. Episodes Not Run, VM End State, Open Items

### Not run (stop rule)

| Episode | Status | Prepared on the VM |
|---|---|---|
| E2, seed 1181837745 (echo) | **Not run** | `scen/mapd_5_seed2.yaml` (regenerated from the `4bfcd43` yaml with the repo draws; starts r1 E, r2 Wm, r3 N, r4 Wp, r5 S), overlay `s1_orch_seed2.yaml` `d917f010`, validated in the container. `build_usd.sh 2` is ready, and the USD was never rebuilt. |
| E3, seed 537191633 (live ER-2) | **Not run, $0 episode spend** | `scen/mapd_5_seed3.yaml`, overlay `s1_orch_seed3.yaml` `537fc61f`, `launch_ep.sh` E3 (`BACKEND=gemini`, `MOCK_ECHO=0`, `MAX_ANALYSES=40`), and a passing preflight |

- **Live-cost projection for an E3 like E1.** Under the dispatched-loop cadence, about 46 analyses per episode at about $0.0074 per call (A13 budget row) comes to **about $0.34**. That fits the $1.50 cap with `MAX_ANALYSES=40`.
- **Spent here.** 2 preflight calls (1111-token prompts, about 2.3k tokens in total), **under $0.01**.

### VM end state

- **Configs.** `orchestrator.yaml` is `1f656533` in source and installed, and the installed backend is `openai`. `rag.yaml` is `e18c723c`.
- **Scenario.** `mapd_5.yaml` is `df1c6504` (seed 1, `4bfcd43`). `mapd_5.usd` is `d7776daa`, root-owned and newer than the yaml.
- **Tree.** The 903-file `4bfcd43` manifest fails only `orchestrator.yaml` (Shim 1).
- **Processes.** None: no `run_simulation`, `fc_launch`, `s1_run`, watcher, Kit, `ros2 launch` or bag.
- **GPU and container.** GPU 0%, 135 MiB. `vgu_ros` is up and idle.
- **Leftovers.** No root-owned files in `~ubuntu/.cache`, `.local`, `.nvidia-omniverse` or `IsaacSim-source`. No `mapd_5` GT is left in `data/logs/simulation`.
- **Files.** `~/v3_s1_resume/` holds `NOTES.md`, the drivers, overlays, seed yamls, runs, smoke and evidence.
- **Power.** The VM is **RUNNING**; the owner decides power. `autorun.sh` will start a GUI Kit on the next boot, and the drivers refuse to launch until it is stopped.

### Open items

1. **Two pin classes now block S1.** The A12(iv) Step-6 decision is now more urgent.
   - **SW rack corner (S → Wp).** Deterministic on seed 1 and reproduced on both boxes.
   - **Gate_S jaw on the post-yield resume.** New: the yield's off-lane park pose sets up the corner cut back into the gate mouth.
   - Layer 2 holds both pins, because its re-dispatched waits pre-empt Nav2's recoveries.
2. **Escort length vs passer turn.** A fixed lane-clear escort carries a passer past its own turn mouth. That pushed robot_5 into robot_3's 0.45 m latch radius.
3. **Dispatched-loop suppression residual.** It measured 0 suppressed lines out of 46 analyses. The suppression predicate for refused-yield waits is a Step-6 call.
4. **Ambiguous-arm 0.00 m rear room** on 44 / 46 analyses: a true zero or a defect. Needs a replay look.
5. **Min-distance latch** on handoff pairs (N arm 0.41 m, robot_3/robot_5 0.385 m). This is the same class as the step-0 IB10 latch.
6. **Free-flow equivalence across boxes** stays registered OPEN.
7. **The rc.7 shutdown watchdog.** `SimulationApp.close()` hung **120 s** once (the URDF import) and was killed by the new faulthandler watchdog, exiting rc 1. It did not happen on any `run_simulation` close; those took ≤ 3 s. If it ever hits an episode, it adds 120 s and a non-zero exit after the manifest is written. Watch the Option B tail line.
8. **The A11(iii) hold-backstop PASS/FAIL gate is stated in the wrong unit.** The `mapd_5` header arithmetic `5 / RTF + departure < 45` and A12(v)'s "fails below RTF ≈ 0.129" treat the 45 s backstop as **wall** seconds. M4 times it on the ROS clock under `use_sim_time`, so it is **45 sim-s**. In sim units the gate is dwell 5 sim-s plus departure (about 0.5–1.7 sim-s here) against 45, which passes at **any** RTF. The 2026-10-08 "PASS 40.3 < 45" is the right verdict for the wrong reason. This is for Step 6 or the owner. The header was not edited.

### Caveats

- **The build label differs.** This box runs a local source build of the `v6.0.1` tag, labelled `6.0.1-rc.7`. The old box ran the automator's 6.0.1 release. The running Kit's App, Kit and Kernel version strings are **identical** to the old VM's Kit log (verified by grep of both logs), and the 2-robot smoke and RTF match within noise. The extension set was not diffed, and the GUI banner reads "6.0.1-rc.7", so cross-box claims must still carry the packaging difference.
- **Version drift.** The container uses Nav2 1.3.13 (September/October 2026 noble builds) and pydantic 2.14.0. Old-VM versions were not recorded, so drift is possible. The smoke shows no behavioral difference on the reference cell.
- **E1 is one episode on one seed.** The A13 verdicts above rest on **one** executed yield.

---

## References

- Scenario, overlay and run line: `isaac/config/scenarios/mapd_5.yaml` header at `4bfcd43`.
- Previous pilot: `docs/reports/2026-10-08-s1-pilot.md`.
- Rulings: prereg-v3 A12 and A13 (`feat/v3-design:docs/superpowers/specs/2026-10-06-prereg-v3-design.md`).
- Smoke reference: `docs/reports/2026-10-08-v3-step0-rebaseline.md` stage 1, and `docs/reports/2026-10-07-harness-optionb.md`.
- VM notes: `~/v3_s1_resume/NOTES.md` on the VM. A local copy is in the bundle.

# Harness Option B and Isaac Stop Flag — Implementation and VM Smoke

**Prepared:** 2026-10-07

**Revision history:**

- Initial draft: the two ruled harness changes on `feat/v2-harness-optionb` and `prereg-v1-hotfix`, the DRY_RUN golden handling, suite deltas, one mock VM smoke and one deliberate abort test.

---

## Summary

This is a harness-only change. Decision semantics, prompts, configs and oracles are untouched. The authority is the main-checkout spec block "Shutdown-timing probe RESULTS + RULINGS (2026-10-07…)" in `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, with the measurements in `docs/reports/2026-10-07-shutdown-timing-probe.md`.

- **Option B.** `scripts/vm/fc_launch.sh` stage 9 no longer tails M5 for a fixed `REC_SEC`. It ends the tail 10 s after the Isaac process exits, and `REC_SEC − 10` s stays as the cap.
- **Stop flag.** An abort now stops Isaac through a path Kit honors. Cleanup touches a per-run flag file. The runner polls it in its sim loop and in its ROS-topic wait. The loop then exits normally: GT is closed, the manifest is written with an explicit aborted marker, and the ~1 s `close()` runs. SIGINT is not used. The `pkill` and every caller's `pgrep` relaunch gate stay as defense in depth.
- **VM smoke: PASS on every ruled criterion.** One 2-robot head-on mock episode ran on the composite build (cell `head_on_asymmetric_w0p2_eopen_bshort_o0`, seed 42, $0 API).
  - (a) The tail ended **11 s after the Isaac process disappeared**.
  - (b) GT has **3001 lines** with a valid last line (`sim_time_sec` 300.0), and the manifest is `completed=true` with the unchanged key set. The grounded decision artifact carries the `dispatched_*` keys. The M5 log is intact: 0 Tracebacks, 2/2 arrivals.
  - (c) The cycle took **838 s against the 1082 s baseline median** (−244 s, −22.6 %; the probe projected ~842 s).
- **Abort test: PASS.** `fc_launch` got SIGTERM 60 s into the M5 tail (seed 43).
  - Isaac saw the flag within about 1 s and its process was gone **≤ 3 s after the SIGTERM**. Before this change it would have kept simulating to its 300 sim-s horizon.
  - GT closed at 370 lines with a valid last line (36.9 s).
  - The manifest says `completed=false, aborted=true, abort_phase=sim_loop`.
  - `pgrep` was empty the moment `fc_launch` exited.
- **VM restored** byte-identically: 1048 source files and 519 installed files match the pre-deploy md5 manifests. No sim processes are running, and the VM was left RUNNING.
- **Nothing found blocks collection from using this.** The residuals under "Caveats" are documentation-level.

---

## Commits

| Branch | Commits | Base |
|---|---|---|
| `feat/v2-harness-optionb` | `7ddebe4` runner stop flag; `6564f15` `fc_launch` Option B + abort flag; plus this report and the notes entry | `5ab1294` (composite tip) |
| `prereg-v1-hotfix` | `c1bf820` runner stop flag; `fca3870` `fc_launch` Option B + abort flag; plus a notes entry | `a475fe0` |

Neither branch is pushed. The hotfix diff touches only `scripts/vm/`, `isaac/` (runner + CLI) and `tests/unit/`. Nothing under `reasoning/` or `config/` changed.

---

## Implementation

### `scripts/vm/fc_launch.sh`

- **Isaac PID.** `ISAAC_PID=$!` is taken from the `nohup sudo … python.sh` launch. Isaac Sim's `python.sh` runs Kit's Python as a child (`$python_exe … || error_exit`, no `exec`), so the `sudo` wrapper lives exactly as long as Isaac does. No `pgrep` polling is involved, so trap 5 (patterns matching their own shell) does not apply.
- **Stage 9.** The tail command is byte-identical, `sudo timeout $((REC_SEC-10))s docker exec … tail -f M5_LOG`, but now runs in the background. The shell polls every 2 s using `isaac_wait_exit_or_cap`, which returns one of three outcomes:

| Outcome | What happened | What happens next |
|---|---|---|
| 0 | Isaac exited | The tail runs 10 s more (`ISAAC_EXIT_GRACE_SEC`) |
| 1 | The cap was hit with Isaac still running | The tail ends |
| 2 | The tail ended by itself | The tail is already gone |

  In every case the in-container `tail -f` is then killed with the bracketed `pkill -f "[t]ail -f M5_LOG"`, the pattern `free_flow_run.sh` already proved, and the stage logs which outcome fired. Polling also means an INT/TERM now reaches the cleanup trap within about 2 s. The old foreground tail deferred it for up to `REC_SEC`.
- **Liveness is read with `ps -o stat=`, never `kill -0`.** `ISAAC_PID` is a root-owned `sudo`. Under an unprivileged `fc_launch`, `kill -0` returns EPERM, which would read as "exited" and end a live episode's tail at t=0. A zombie counts as exited.
- **What counts as an abort.** An abort is any exit before stage 9 finished, tracked by `TAIL_STAGE_DONE`. The exit status cannot be used, because every normal cycle exits 141 from the stage-11 `ls | head` SIGPIPE.
  - On an abort, cleanup touches `/tmp/fc_<STAMP>_isaac.stop` **first**, so Isaac winds down while the backend restore runs. After the container restart it waits up to `ISAAC_STOP_WAIT_SEC` (60 s) for the PID, logs the result, and only then runs the existing `pkill`.
- **The cap path is deliberately left alone.** On a normal exit, including the `REC_SEC` cap firing while a 4-robot Isaac is still simulating, the flag is **not** touched. Isaac finishes its 300 sim-s horizon and GT completes exactly as before. Stopping it at the cap would truncate GT, which would be an outcome change.
- **Plumbing.** The flag path reaches Isaac as `VGU_ISAAC_STOP_FLAG=…` in the existing `sudo … env` list, and the launcher removes any stale flag before launching.
- **Helper library.** The helpers live in a new sourced file, `scripts/vm/isaac_lifecycle.sh`, so they can be tested offline. It is bash 3.2 compatible.

### `isaac/vgu_sim/runner.py` and `isaac/scripts/run_simulation.py`

- `run_simulation(config, stop_flag=None)` → `run_repetition(..., stop_flag=None)`.
  - `stop_requested(flag)` is checked at the top of every sim-loop iteration. When it fires, the loop does a `break`, so the `with` block closes GT.
  - The same check runs inside the `_wait_for_ros_topics` loop and raises `_StopRequestedError`, so an abort during bring-up also stops promptly.
  - The flag is persistent, so even an abort during stage open or extension load is honored as soon as either loop is reached.
- **Manifest marker decision.**
  - An aborted run writes `completed=false` and `failure="aborted: stop flag <path> at sim_time_sec=<t>"`, plus five keys: `aborted=true`, `abort_reason="stop_flag"`, `abort_phase` (`sim_loop` or `topic_wait`), `aborted_at_sim_time_sec` and `stop_flag_path`.
  - The extra keys appear **only when aborted**, so a normal manifest keeps the probe-era 13-key set byte for byte.
  - `completed=false` was chosen over `true` because an aborted GT stops short of the horizon. Anything that trusts `completed` (for example `free_flow_run.sh`'s `gt_completed`) must not read it as a finished episode.
- **CLI.** `run_simulation.py` gained `--stop-flag`, which defaults to `$VGU_ISAAC_STOP_FLAG`.

### DRY_RUN Goldens

The pin mechanism is `tests/unit/test_fc_launch_dry_run.py` together with the five two-robot goldens in `tests/unit/data/fc_launch/`.

- **The goldens are unchanged.** The first precedent was the lifecycle-gate fold. Following it, `OPTION_B_LINE_PREFIXES` filters the two new DRY_RUN lines before the byte-for-byte golden comparison, and a separate parametrized test pins them exactly:
  - `[fc-launch] Isaac stop flag: /tmp/fc_<STAMP>_isaac.stop (touched by cleanup on abort only)`, right after the Isaac launch line;
  - `[fc-launch] [DRY_RUN] poll Isaac PID every 2s: end the M5 tail 10s after Isaac exits, cap 990s (sudo pkill -TERM -f [t]ail -f /tmp/fc_<STAMP>_m5.log)`, right after the unchanged tail line.
- **No existing line changed.** The tail line keeps its exact text, and the flag rides in the Isaac line's already-elided `env ...`.
- **Further pins.** Tests also pin the order of the lines and that `REC_SEC` and `ISAAC_EXIT_GRACE_SEC` drive the cap and the grace.

### Tests and Suite Deltas

New offline tests (+23 per branch):

- `tests/unit/test_isaac_lifecycle_sh.py` (9 tests) uses stand-in processes.
  - It covers liveness, including an unreaped zombie, and all three wait outcomes plus the no-PID fallback.
  - It also runs a **SIGTERM-swallowing stand-in for Kit** that survives `kill -TERM` and exits on the flag.
- `tests/unit/test_runner_stop_flag.py` (7 tests) stubs `omni` and `carb` and runs the real loop, GT writer and manifest.
  - It covers an abort at ~10 sim-s, the normal run (3001 GT lines, 13-key manifest), a flag present at loop entry, the topic-wait phase, and flag plumbing through `run_simulation`.
- `tests/unit/test_fc_launch_dry_run.py` (+7).

Full suite (`pytest --continue-on-collection-errors`) results, with the failing-id sets diffed against a detached baseline worktree:

| Tree | Before | After | Failing-id set |
|---|---|---|---|
| composite (`5ab1294` → `6564f15`) | 62 F / 5447 P / 153 S / 3 E | 62 F / 5470 P / 153 S / 3 E | identical (65 ids) |
| hotfix (`a475fe0` → `fca3870`) | 63 F / 2994 P / 16 S / 3 E | 63 F / 3017 P / 16 S / 3 E | identical (66 ids) |

### Divergence Between the Two Trees

- **Runner and CLI.** `runner.py` and `run_simulation.py` were byte-identical across the trees before the change, and still are after it.
- **`fc_launch.sh`.** The two copies differ in the same 20 lines before and after: the composite's free-flow scenario directory and `MAP_SCENARIO`. The patch applied to the hotfix tree without conflict.
- **Dry-run test.** The hotfix copy lacks the `MAP_SCENARIO` env entry and the two free-flow tests, so its `_CLEARED_ENV` hunk was adapted by hand. Everything else in the change is byte-identical across trees.

---

## VM Smoke

### Setup

| Item | Value |
|---|---|
| VM | `vgu-vgu-thule-base-isaac-workstation-vm` (us-central1-c), already RUNNING; Isaac Sim 6.0.1 |
| Tree before | `b5cafe4` content, except the VM-pinned pristine `orchestrator.yaml` (`1f656533…`, which every driver asserts; it differs from git's `11fb304a…` by comment blocks and the `plan_channel_enabled` key) and two docs. Verified by md5 against `git archive b5cafe4`. |
| Deployed | The 29 runtime files that differ between `b5cafe4` and `6564f15` (no docs or tests): `reasoning/` (live-mounted), `isaac/`, `scripts/`, `config/models.yaml` and `swarm_orchestrator` sources. Copied with fresh mtimes; `build/` and the installed Python were purged and rebuilt; installed `.py` content was md5-verified against source. `orchestrator.yaml` stayed pristine (source and installed both `1f656533…`). |
| Driver | `/home/ubuntu/hb_optionb/smoke.sh`, run as root under `setsid nohup`. It gates on an empty `pgrep -f "[r]un_simulation"` and a pristine orchestrator md5, and refuses to start if the GT dir already exists. A 1 Hz sidecar records Isaac PIDs and GPU. |
| Mock | `MOCK_DECISION_FILE=config/mock_decisions/head_on_yield_robot_2_once.json` (scripted-array form); `RECORD=0 REC_SEC=1000 SIM_SEC=1200` |

### Smoke Timing (seed 42, stamp `20261007_052329`)

Times are wall-clock UTC. The offset column counts from the `fc_launch` start.

| Event | UTC | Offset (s) |
|---|---|---|
| `fc_launch` start | 05:23:29 | 0 |
| Isaac launched (PID 1555495) | 05:23:44 | 15 |
| all components started | 05:24:45 | 76 |
| robot_1 / robot_2 arrived (M5) | 05:27:57 / 05:30:45 | 268 / 436 |
| Kit `SimulationApp.close` | 05:37:00 | 811 |
| Isaac process gone (sidecar: last present 05:37:02, first empty) | 05:37:03 | 814 |
| `fc_launch` detects exit ("PID 1555495 gone at 05:37:04") | 05:37:04 | 815 |
| **M5 tail ends** (10 s grace, "749s into the tail") | **05:37:14** | **825** |
| cleanup entry | 05:37:17 | 828 |
| `logs saved to`, `fc_launch` exit (rc 141, pre-existing) | 05:37:27 | 838 |
| `pgrep` empty (driver gate) | 05:37:27 | 838 |

- **Tail end vs. Isaac exit: 11 s.** The tail ends 10 s of grace plus at most one 2 s poll after the exit. The probe baseline was about 238 s of tail with no simulator.
- **Cycle: 838 s, against the 1082 s baseline median** (1079–1082 measured), a saving of 244 s (22.6 %). The probe's Option B projection was ~842 s.

### Smoke Artifact Completeness

| Check | Result |
|---|---|
| GT lines | **3001** (probe baseline: 3001 in all 4 cycles) |
| Last GT line | valid JSON, `sim_time_sec` 300.0 |
| Manifest | `completed: true`, `failure: null`, exactly the 13 pre-flag keys (no `aborted*`) |
| M5 log | 3010 lines, 0 Tracebacks, 2 `arrived at base goal`, 0 openai / 0 http mentions, stage-2 `stage2 marks enabled` line present |
| M5 decisions | 8 artifacts, all `backend_id=mock`: 1 grounded `yield` (`terminal_stage=ok`) plus 7 `vlm`/`none` re-checks |
| Provenance keys (A1/A5b) | The grounded artifact carries `dispatched_command`, `dispatched_robot_ids` and `dispatch_dropped_robot_ids`. `junction_phases` is absent by design: it is written only for `junction_clear` outcomes (`reasoning_pipeline.py:997`). `dispatch_filter_error` is absent by design: it is written only when the registry filter refuses (`reasoning_pipeline.py:1007`). |
| M5 scene | 1 jsonl |
| Stop flag | not created (normal path) |

### Abort Test (seed 43, stamp `20261007_053728`)

The driver sent SIGTERM to the `fc_launch` bash 60 s after "all components started". This exercises the whole chain: trap → cleanup → flag → runner loop → manifest → bounded wait → `pkill` → gate.

| Event | UTC |
|---|---|
| all components started | 05:38:45 |
| **SIGTERM to `fc_launch`** | **05:39:45** |
| cleanup: "abort before the M5 tail finished: touched Isaac stop flag" | 05:39:46 |
| Kit: `stop flag seen: aborted: stop flag … at sim_time_sec=36.97`, then `SimulationApp.close` | 05:39:46 |
| Isaac process gone (sidecar: last present 05:39:47, first empty) | **05:39:48** |
| cleanup: container restarted; "Isaac honored the stop flag … (waited 0s after the container restart)" | 05:39:59 |
| `fc_launch` exit (rc 130), `pgrep` empty (0 s gate wait) | 05:39:59 |

- **Isaac exited ≤ 3 s after the abort.** The trap-16 behavior was 231–356 s or more, up to the full 300 sim-s horizon. The "gone at 05:39:59" in the cleanup line is the time of the check after the 10 s container restart; the sidecar shows the real exit time.
- **GT.** 370 lines, valid last line (`sim_time_sec` 36.9), file closed.
- **Manifest.** `completed: false`, `aborted: true`, `abort_reason: "stop_flag"`, `abort_phase: "sim_loop"`, `aborted_at_sim_time_sec: 36.97`, `stop_flag_path: "/tmp/fc_20261007_053728_isaac.stop"`, and `failure: "aborted: stop flag … at sim_time_sec=36.97"`.
- **M5.** 303 lines, 0 Tracebacks, 1 grounded `yield` artifact with the `dispatched_*` keys.

---

## VM State After

- **Tree restored.**
  - Modified files were put back with their original mtimes, and the 7 files the deploy created were removed.
  - The 14 bytecode files the runs had rewritten were recompiled from the restored sources. Compilation used the interpreter and absolute `dfile` path that originally produced them: the container's Python 3.12.3 with `/ws/…` for `reasoning/`, and Isaac's Python 3.12.13 with `/home/ubuntu/vgu-vlm-swarm/…` for `isaac/`. A relative-path recompile does **not** reproduce the bytes, because `co_filename` is embedded.
  - `swarm_orchestrator` was purged and rebuilt.
  - **Source tree: 1048/1048 files and installed tree: 519/519 files are md5-identical to the pre-deploy manifests.** `fc_launch.sh` is back to `30d5c3c3…`, `runner.py` to `5fdfc285…`, `run_simulation.py` to `f08a6504…`, and `orchestrator.yaml` (source and installed) to `1f656533…`.
- **Repo `data/logs/`.** 0 files are newer than the smoke start marker; every byproduct was moved into the bundle.
- **Processes.** No `run_simulation`, `fc_launch` or driver processes remain, checked with a script-file `pgrep`. `vgu_ros` is up, the GPU is at 0 % and 171 MiB, and the VM was **left RUNNING**.
- **Bundle.** The bundle is on the VM at `/home/ubuntu/hb_optionb/` (23 MB). It holds the driver, md5 manifests, deploy/restore scripts and logs, and the `smoke/` and `abort/` run directories (fc, Kit, Isaac, M1, M4, M5 and Nav2 logs, GT, manifest, M5 artifacts, sidecar and `CHECK.txt`). There is a gitignored copy under `data/logs/vm_runs/harness_optionb/` in the main checkout.
- **Left alone.** `/home/ubuntu/shutdown_timing_probe/` and `/home/ubuntu/gpt56_sol_swap/` were not touched.

---

## Caveats

1. **The aborted run's exit code carries no signal.** Kit's fast shutdown terminates the process inside `app.close()`, so `run_simulation.py` never prints its `FAIL rep=…` line or exits 1. The same is true on normal runs: no "completed successfully" line is printed. The manifest, written before `close()`, is the only abort record, and scorers must read `completed` and `aborted` from it.
2. **The hotfix tree was not smoked separately.** Its runner, CLI and lifecycle helper are byte-identical to the smoked composite files. Its `fc_launch.sh` differs from the smoked one only in the pre-existing free-flow lines. Running one more $0 smoke from the hotfix tree is the coordinator's call.
3. **An interactive Ctrl-C was not exercised and may still reach Kit directly.** Kit sits in `fc_launch`'s process group, and SimulationApp installs its own SIGINT handler, which skips the manifest. Collection drivers run detached (`setsid nohup`), which is the path tested here.
4. **4-robot cells are unchanged by design.** Isaac outlives the `REC_SEC` cap, the flag is not touched on the cap path, and Isaac finishes its horizon after `fc_launch` exits. The `pgrep` gate before relaunch is still required there.
5. **`free_flow_run.sh`'s external tail-killer is now redundant but harmless.**
   - It kills the tail only once `pgrep '[r]un_simulation'` is empty. The `sudo` wrapper's command line contains `run_simulation`, so an empty `pgrep` means `ISAAC_PID` is already gone.
   - `isaac_wait_exit_or_cap` checks Isaac before it checks the tail, so `fc_launch` still takes the Isaac-exited branch and logs it.
   - The external kill can only end the tail early, inside the 10 s grace window.
6. **Collection wrappers.** `v2_final_run.sh`'s optional sampler and snapshot sidecars (`REC_SEC − 30`) are `docker exec` clients, and `fc_launch`'s container restart ends them, so its `wait` does not reimpose the fixed window.
7. **Pre-existing behavior, unchanged.** `fc_launch` still exits rc 141 on normal runs, and `SIM_SEC`/`--duration-sec` is still dead.

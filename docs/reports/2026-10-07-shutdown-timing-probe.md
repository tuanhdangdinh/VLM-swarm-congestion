# Shutdown Timing Probe — Per-Episode Wall-Time Breakdown

**Prepared:** 2026-10-07

**Revision history:**

- Initial draft: 3 standard mock cycles plus 1 short-horizon cycle on the Isaac VM; fast_shutdown no-op finding; shader-cache verdict; collection projections.

---

## Summary

This is a harness-engineering probe, not a scored experiment. It used the mock backend only and made zero API calls.

- **Baseline cycle.** The cycle is the standard `fc_launch.sh` cycle with `RECORD=0`, `REC_SEC=1000`, `SIM_SEC=1200`. It takes a median of **1082 s (18.0 min)**. The three runs took 1082, 1082 and 1079 s.
- **`fast_shutdown` is already on, so the patch is a no-op.**
  - Isaac Sim 6.0.1 ships `"fast_shutdown": True` in `SimulationApp.DEFAULT_LAUNCHER_CONFIG`, together with a 120 s faulthandler shutdown watchdog. The runner does not override it.
  - The Kit argv of every boot contains `--/app/fastShutdown=True`.
  - The runner already calls `app.close()` on the normal path.
  - `close()` to process exit is measured at **≤ 1 s**.
  - The brief's patch was therefore **not applied**, and the fast arm was **not run**. Three cycles of a byte-identical effective config is not an A/B test. This is a deliberate deviation; the evidence is in the No-Op Evidence section.
  - **Projected saving from adopting it: 0 s per episode.**
- **Where the 18 minutes go.**
  - The robots are both home a median 471 s into the cycle.
  - Isaac keeps simulating to its 300 sim-s horizon and exits at about 828 s.
  - `fc_launch` then tails an M5 log for about **238 s with no simulator running**: the GPU sits at 0–2 % and 171 MiB.
  - The cycle length is set by the fixed `REC_SEC` timer. Teardown is not the cause.
- **Shader cache.** No RTX shader compilation happens on any boot: there are 0 compile lines in 31 retained Kit logs. `app ready` lands at 16.3–21.7 s. The cache is warm and persistent, and no cleanup path touches it.
- **The "Isaac survives cleanup by 231–356 s" trap, explained.**
  - Kit catches and swallows SIGTERM, so `fc_launch`'s `pkill` never stops Isaac.
  - Isaac re-parents to PID 1 and runs its duration loop to the end.
  - Whether the trap shows depends on the cell, because Isaac's lifetime does.
    - **2-robot head-on cells** live about 780–860 s. Under `REC_SEC=1000` they exit about 240 s before cleanup, and the gate wait is 0 s.
    - **4-robot cells** (`intersection_bottleneck`, `convoy_counterflow_slip`) live 1085–1416 s in the `/tmp` history. They outlive cleanup by about 30–360 s even at `REC_SEC=1000`; this is the historic trap.
    - A shorter `REC_SEC` (cycle 4, 400 s) made a head-on Isaac outlive `fc_launch` by **290 s**.
- **Recommendation.**
  - fast_shutdown: **no-go**, because there is nothing to adopt.
  - The real lever is ending `fc_launch`'s fixed tail when Isaac exits. For **head-on cells** it saves about **241 s per episode (22 %)** and is outcome-neutral. Head-on-only, v1 would go from **141–177 VM-h (5.9–7.4 days at one seat) to 110–138 VM-h (4.6–5.7 days)**.
  - 3-robot cells save more, about 350 s. 4-robot cells save **nothing**, because Isaac's own lifetime binds them.
  - Shortening the 300 sim-s horizon is an owner decision.

---

## Setup

| Item | Value |
|---|---|
| VM | `vgu-vgu-thule-base-isaac-workstation-vm`, `us-central1-c`, Isaac Sim `6.0.1-rc.7+mr.0.045ca8b5`, Kit kernel 110.1.2 |
| VM tree | `/home/ubuntu/vgu-vlm-swarm` → `/ws`. This is not a git checkout (an rsync'd tree). Content is `b5cafe4`, per the coordinator. md5 matches `b5cafe4` for `fc_launch.sh`, `runner.py` and `run_simulation.py`. |
| Orchestrator config | Standing pristine `orchestrator.yaml` md5 `1f656533…`, for both source and installed copies, before and after every cycle |
| Cell | `head_on_asymmetric_w0p2_eopen_bshort_o0` (2 robots, `duration_sec: 300`) |
| Mock | `MOCK_DECISION_FILE=config/mock_decisions/head_on_yield_robot_2_once.json` → backend `mock` |
| Launcher | `scripts/vm/fc_launch.sh`, `RECORD=0 REC_SEC=1000 SIM_SEC=1200`, seeds 42/43/44. Cycle 4 used `REC_SEC=400`, seed 45. |
| Driver | Root `setsid nohup` driver. It gates every launch on `pgrep -f "[r]un_simulation"` being empty and moves each cycle's byproducts out of the repo tree. A 1 Hz sidecar records PIDs and GPU. |
| Time | 03:47:11–04:54:10 UTC, about 67 min of cycles. The VM was already RUNNING. |

### Deviations From the Brief

1. **Cell.** The probe used the collection cell, not `head_on_deadlock`.
   - The VM's `head_on_deadlock.usd` (2025-09-25) predates its yaml, which is the stale-USD trap.
   - The bshort cell ran live today, and has the same 300 sim-s horizon as `head_on_deadlock`.
   - The probe ran under the pristine config, not the collection overlay `ho_orchestrator.yaml`. Goals and gating may therefore differ from collection runs. The timer-bound cycle structure measured here does not depend on either.
2. **Fast arm not run.** See the No-Op Evidence section.
3. **Cycle 4 added.** It was one flagged short-horizon cycle (`REC_SEC=400`), added to test whether a shorter `fc_launch` horizon actually shortens the cycle.
4. **`SIM_SEC` has no effect.**
   - `run_simulation.py` parses `--duration-sec` but never passes it into `ResolvedRunConfig`.
   - Isaac's lifetime is the scenario yaml's `duration_sec`.

---

## Per-Run Phase Table

All times are seconds from `fc_launch` start. The anchors are `fc-launch` HH:MM:SS lines, Kit-log ISO stamps, the epoch stamps on M5 `arrived at base goal` lines, and the 1 Hz sidecar. Resolution is 1 s.

| Phase | c1 s42 | c2 s43 | c3 s44 | **Median** | c4 s45 (`REC_SEC=400`) |
|---|---|---|---|---|---|
| Container restart + `swarm_orchestrator` rebuild + scenario validate → Isaac launch | 16 | 16 | 16 | **16** | 16 |
| (a) Isaac launch → Kit `app ready` | 18 | 18 | 17 | **18** | 17 |
| (b) `app ready` → first `/camera/image_raw` frame ("Isaac topics live") | 16 | 16 | 15 | **16** | 16 |
| M1 + Nav2 (2 stacks) + M4 + M5 bring-up → "all components started" | 79 | 79 | 76 | **79** | 79 |
| robot_1 arrived | 296 | 282 | 272 | **282** | 277 |
| (c) both robots arrived (episode resolved) | 487 | 471 | 424 | **471** | — (M5 killed at 474) |
| Isaac duration loop ends → `SimulationApp.close()` | 838 | 826 | 828 | **828** | 775 |
| `close()` → Isaac process gone (sidecar) | ≤1 | ≤1 | ≤1 | **≤1** | ≤1 |
| `fc_launch` tail ends → cleanup entry (restore + rebuild) | 1069 | 1069 | 1066 | **1069** | 469 |
| Cleanup: container restart + `pkill` + log collect → `fc_launch` exit | 1082 | 1082 | 1079 | **1082** | 485 |
| (d) cleanup entry → `pgrep -f "[r]un_simulation"` empty | 13 | 13 | 13 | **13** | **306** |
| **Total cycle (launch → gate empty)** | **1082** | **1082** | **1079** | **1082** | **775** |

### Derived Spans (Baseline Medians)

| Span | Seconds | Share |
|---|---|---|
| Bring-up: launch → all components started | 79 | 7 % |
| Episode work: started → both arrived | 392 | 36 % |
| Post-resolution sim, until Isaac reaches 300 sim-s | 355 | 33 % |
| `fc_launch` tail with **no simulator** (GPU 0–2 %, 171 MiB) | 238 | 22 % |
| Teardown: `close()` plus cleanup | 14 | 1 % |

The episode resolves 471 s into a 1082 s cycle, so 56 % of the cycle runs after both robots are home. The last 238 s run nothing at all.

---

## fast_shutdown No-Op Evidence

- **Default config.** `/home/ubuntu/IsaacSim/exts/isaacsim.simulation_app/isaacsim/simulation_app/simulation_app.py` lines 95–96 sit in `DEFAULT_LAUNCHER_CONFIG`:
  - `"fast_shutdown": True,`
  - `"shutdown_watchdog_timeout": 120.0,`
- **The runner does not override it.** `isaac/vgu_sim/runner.py` `_get_app()` passes only `headless`, `anti_aliasing` and `extra_args`, and `config.update(launch_config)` merges on top of the defaults.
- **Kit argv.** Line 22 of every Kit log shows `--/app/fastShutdown=True`, and the experience file `apps/isaacsim.exp.base.kit:191` also sets `fastShutdown = true`.
- **`close()` already runs.** `run_simulation()` calls `app.close()` in its `finally`. Every Kit log ends with `SimulationApp.close: shutting down app`, and the sidecar shows the process gone within ≤ 1 s, in all 4 cycles.
- **The watchdog never fired.** That would take about 120 s.

The patch the brief asked for, recorded but **not applied**:

```text
--- isaac/vgu_sim/runner.py
+++ isaac/vgu_sim/runner.py
@@ def _get_app(headless: bool):
     return SimulationApp(
         {
             "headless": headless,
             "anti_aliasing": 0,
+            "fast_shutdown": True,
             "extra_args": [
```

The runner was never edited. Its md5 is `5fdfc285df5a010d014a7d2cd7b2c438` and its mtime is `2026-10-05 12:22:11`, the same before and after the probe. Pinning the setting explicitly would only guard against a future Isaac default flip; it has zero runtime effect on 6.0.1.

---

## Artifact Completeness

Every cycle produced complete artifacts. The checks are against the `b5cafe4`-era shape, which has no `junction_phases` or `dispatched_*` keys.

| Cycle | GT lines | Last GT line | Manifest | M5 decisions | M5 scene | m5.log Tracebacks | openai/http mentions |
|---|---|---|---|---|---|---|---|
| c1 | 3001 | valid JSON, `sim_time_sec` 300.0 | `completed=True` | 9 | 1 | 0 | 0 / 0 |
| c2 | 3001 | valid, 300.0 | `completed=True` | 9 | 1 | 0 | 0 / 0 |
| c3 | 3001 | valid, 300.0 | `completed=True` | 6 | 1 | 0 | 0 / 0 |
| c4 | 3001 | valid, 300.0 | `completed=True` | 11 | 1 | 0 | 0 / 0 |

- **Truncation.** No truncation was seen. The GT file is closed by the `with` block before `close()` is reached, so fast shutdown cannot truncate it.
- **Stage 2.** Every cycle logged `stage2 … status=skipped skip_reason=no_backend`, the expected mock behavior.
- **Exit code.** `fc_launch` exited `rc=141` in all 4 cycles. This is pre-existing, not caused by the probe: the stage-11 summary's `ls -lt … | head -10` SIGPIPEs under `set -euo pipefail`, which aborts the per-decision printout and jumps straight to cleanup. It costs no time, but the summary is never printed. The "GATE OK / logs saved to" line still prints, so verify M5 activity from logs as usual.

---

## The SIGTERM Finding

The surviving Isaac process in cycle 4 (PID 1525502) was inspected 2.5 min after `fc_launch`'s `pkill`:

```text
PPid:   1
SigIgn: 0000000001001005
SigCgt: 40000001000044fa
```

- **SIGTERM is caught and swallowed.** Bit 14 (SIGTERM) is set in `SigCgt`. Kit runs with `--/app/installSignalHandlers=0`, and `SimulationApp` installs a Python handler for SIGINT only, so the catcher is most likely the carb crash reporter. The process keeps running anyway.
- **The `pkill` takes out the wrapper only.** It kills `sudo` and `python.sh`, and the Kit Python re-parents to PID 1.
- **Isaac then finishes its loop.** It runs to the 300 sim-s horizon, writes GT and the manifest, and exits via the fast path.
- **This explains the trap.**
  - The "survives by 231–356 s" figure is simply the time left in Isaac's loop when cleanup fires.
  - A failed early run survives longer for the same reason.
  - The per-family lifetimes below show where it bites.
    - 2-robot head-on Isaac exits about 240 s *before* cleanup under `REC_SEC=1000`, so the trap never shows.
    - 4-robot cells live 1085–1416 s, against cleanup at about 1053 s Isaac-relative. They outlive cleanup by about 30–360 s, which brackets the historic 231–356 s figure.
- **Side benefit.** Because Isaac finishes on its own, an aborted `fc_launch` still yields complete GT.
- **Implication for horizon cuts.** Shortening `REC_SEC` alone cannot shorten the cycle below Isaac's own lifetime: cycle 4 still took 775 s. It also cut M5's window before robot_2 arrived, which makes that episode unscorable from M5 arrival lines.
- **Implication for teardown.** Any future "end early" must stop Isaac through a path it honors, such as a stop-file or flag checked in the loop, or SIGINT. SIGTERM does not work.

---

## Shader Cache

**Verdict: no RTX shader compilation on any boot. The cache is warm and persistent.**

- **Logs.** 31 retained Kit logs (`kit_20261006_025649` … `kit_20261007_044132`, the 4 probe boots included) were grepped case-insensitively for `ray tracing shaders`, `Waiting for compilation`, `compiling shader` and `shader compil`. Slang plugin registration lines were excluded. There were **0 hits**. The `/tmp` Isaac logs show no compile lines across 30 earlier boots either.
- **`app ready` timing.** Kit-relative `app ready` time was 16.3–21.7 s over the last 12 boots, 16.8–17.1 s in the probe.
- **Driver cache.** Every boot logs `Driver shadercache folder: …/kit-kernel/110.1.2+…/cache/nv_shadercache, file count: 6, size: 535.45 MB`, identical across boots.
- **App cache.** `…/cache/shadercache` has 129 files, all dated 2026-09-24 18:49–19:05, the first-boot fill. None are newer.
- **Other paths.**
  - `…/cache/DerivedDataCache`: 568 MB.
  - `~/.local/share/ov/data/exts/v2/omni.gpu_foundation.shadercache.vulkan-…/cache/nv_shadercache`: 8 KB.
  - `~/.cache/ov`: 8.3 MB.
  - `~/.nv/ComputeCache`: 6.1 MB.
- **Cleanup does not touch them.** `fc_launch` cleanup only restarts `vgu_ros` and runs `pkill`; it touches nothing under `~/.cache`.
- **Untouched by the probe.** No cache was deleted or moved.

---

## Projections

### Isaac Lifetime by Family

The Isaac lifetime is the Kit-relative "Simulation App Shutting Down" time from the `/tmp/fc_*_isaac.log` history, plus this probe. Cycle estimates use launch offset 16 s and teardown 13 s.

- **Current:** cycle = max(1082 s, 16 + lifetime + 13).
- **Option B:** cycle = 16 + lifetime + 13.

| Family (robots) | Boots | Isaac lifetime (s) | Current cycle (s) | Option B cycle (s) | B saving / ep |
|---|---|---|---|---|---|
| `head_on_asymmetric_*_bshort` (2) | 24 | 759–863 (probe median 812) | 1082 (measured) | ~842 | ~241 s |
| `bottleneck_merge` (3) | 3 | 680–729 | ~1082 | ~734 | ~350 s |
| `intersection_bottleneck`, `convoy_counterflow_slip` (4) | 6 | 1085–1416 | ~1114–1445 (Isaac-bound, gate waits) | same | **0 s** |

Only the head-on row was measured in this probe. The other rows are derived from historic lifetimes.

### v1 Collection Duration — Head-On Cells

Only the head-on figures are measured, and the v1 per-family episode mix was not pinned down for this report. The table below is therefore **scoped to head-on cells**: it applies all 470–590 v1 episodes (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`) at the head-on cycle. A mix that includes 4-robot cells lowers the real saving; a mix with 3-robot cells raises it. The cost basis is $0.9 per VM-hour, and wall days assume one sim seat running continuously.

| Option | Cycle (s) | Saving / ep | v1 VM-h (470–590) | Wall days (one seat) | Saving vs now |
|---|---|---|---|---|---|
| Current harness (`REC_SEC=1000`) | 1082 | — | 141–177 (~$127–160) | 5.9–7.4 | — |
| + `fast_shutdown: True` (brief's patch) | 1082 | **0 s** | 141–177 | 5.9–7.4 | 0 h |
| A. `REC_SEC=800` (no code; 30 s margin over the latest observed head-on Isaac exit) | ~882 | ~200 s (18 %) | 115–145 | 4.8–6.0 | 26–33 h |
| **B. `fc_launch` ends its tail when the Isaac PID exits (`REC_SEC` kept as cap)** | **~842** | **~241 s (22 %)** | **110–138** | **4.6–5.7** | **31–39 h** |
| C. End the episode at resolution (+30 s settle; requires an Isaac-honored stop) | ~515 (resolved episodes only) | ~567 s (52 %) | ≥ 67–84 (lower bound) | ≥ 2.8–3.5 | ≤ 74–93 h |

### Notes on the Options

- **A and B are outcome-neutral.** They only remove the window in which no simulator runs. M5 has no camera input in that window, and GT/manifest are already final.
- **B is preferred over A.** A's fixed `REC_SEC` must be tuned per family: 800 s would cut a 4-robot cell's M5 window while Isaac is still simulating. B ends exactly when Isaac does and saves where there is slack. For 4-robot cells it saves nothing; there it is merely safe.
- **Only C helps Isaac-bound cells.** For 4-robot cells the cycle is bound by Isaac's own 300 sim-s horizon, so only shortening that horizon (C) would help.
- **Registered apparatus.** `REC_SEC` 1000 is recorded apparatus for the registered runs, so changing it, or `fc_launch`'s stop rule, is the owner's call.
- **C changes the registered 300 sim-s horizon.** It touches GT-horizon outcome classification, dissolution metrics and post-resolution re-checks. Unresolved episodes would still run to the horizon. It is not recommended before collection without an owner ruling.
- **Cross-check against the v2 spec.**
  - The v2 spec estimates 330–410 VM-h for 1,600–2,000 exploratory-tier episodes, which implies about 12.3 min per episode.
  - The measured 18.0 min per episode puts that tier at roughly **480–600 VM-h** under the current harness.
  - Option B would put it at roughly 375–470 VM-h.
  - The gpt-5.6-sol live episodes today ("two 18-minute episodes") agree with this cycle length. A live backend does not change the cycle, because the length is set by the timer, not by API latency.

---

## Recommendation

1. **Do not adopt `fast_shutdown`. It is already active.** It is no-go as a change because there is nothing to adopt. An explicit pin in `_get_app()` is optional documentation only.
2. **Adopt Option B before collection, if the owner agrees.** End `fc_launch`'s M5 tail when the Isaac process exits, keeping `REC_SEC` as the upper cap.
   - Savings: about 4 min per head-on episode (up to 31–39 VM-h if v1 were all head-on), about 6 min per 3-robot episode, and nothing for 4-robot cells.
   - It has no outcome effect.
   - It is a small `fc_launch.sh` change; the change itself needs the usual `DRY_RUN` golden update.
3. **Fix the teardown so aborted runs stop Isaac.** `pkill` sends SIGTERM, which Kit swallows.
   - The recommended path is a stop-flag, for example a file or a ROS2 topic, checked in the runner's `while` loop. The loop then exits normally, closes GT, writes the manifest and runs the ≤ 1 s `close()`.
   - SIGINT is **not** recommended, and it is untested. `SimulationApp`'s SIGINT handler calls `self._app.shutdown()`, which with fastShutdown on terminates immediately, and then `sys.exit(0)`. Either way it skips `_write_manifest`, which sits after the `try/finally`, and it can lose the GT tail buffer.
   - Fixing this removes the "never relaunch until pgrep is empty" hazard at its source. Keep the pgrep gate regardless.
4. **Leave shader-cache handling as is.** There is nothing to fix.

---

## VM State After the Probe

- **Processes.** No `run_simulation`, `fc_launch`, sidecar or driver processes remain, checked with a literal-free `pgrep -af`. Docker runs only `vgu_ros`. The GPU is at 0 % and 171 MiB.
- **Files unchanged.**
  - `orchestrator.yaml`, source and installed: `1f656533a30a35882d57d0d64a57bd0d`.
  - `runner.py`: `5fdfc285…`, never edited.
  - `run_simulation.py`: `f08a6504…`.
  - `fc_launch.sh`: `30d5c3c3…`.
- **Repo tree.** No probe byproducts remain under `data/logs`: 0 files newer than the cycle-1 marker. GT directories, `m5_*` artifacts and `fc_run_*` directories were moved into the probe bundle.
- **Probe bundle.** The bundle is kept outside the repo, at `/home/ubuntu/shutdown_timing_probe/` (61 MB). It holds the driver, sidecar, `driver.log`, `sidecar.log` and per-cycle `c1`–`c4` (fc, Kit, Isaac, M1, M4, M5 and Nav2 logs, GT, manifest and M5 artifacts).
- **Other sessions.** `/home/ubuntu/gpt56_sol_swap/` was not touched.

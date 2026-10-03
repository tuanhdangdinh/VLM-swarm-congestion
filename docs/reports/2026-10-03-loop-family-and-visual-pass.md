# Loop-Detour Family (Step 8 Phase 2) and Step-9 Visual Pass

**Prepared:** 2026-10-03

**Revision history:**

- Initial draft: Part A (loop-map wait-vs-detour family) authored, pinned
  and taken to the VM, where its design control failed (STOP finding, for a
  coordinator ruling; no cost tables collected). Part B (step-9 visual
  pass) complete. Rev 1.1 (same day, review pass): the mechanism is
  restated as partly characterized, with the contradicting live probe
  added. The reroute failure is no longer folded into "undrivable". The
  checklist row now names the 99.55% empty-robot fresh rate. The evidence
  is persisted under `data/logs/vm_runs/loop_family/navfn_sweep/`. Part B:
  both B2-visual USDs and the B3 first-to-slip USD built
  and validated, load prop verified visible without occluding the marker,
  M1 detection unaffected, A/B crops saved, maps byte-identical, `b3`
  scored against a real GT log.

---

## Summary

Executes the final v2 build wave on branch `feat/v2-final-wave` (cut from
`feat/prereg-v2-composite` at `1ee23d2`): build-order step 8 phase 2 of
`docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (section (b), the
loop-map scenario family and its oracle) and the step-9 VM visual pass
(section (c)'s BUILT note; the turnkey checklist in
`docs/implementation_notes.md`, 2026-10-02 step-9 entry).

| Part | Outcome |
|---|---|
| A: M3 reroute grounding | Built (spec (b) "Builds"; it was never built in phase 1). `SceneGeometry.reroute_waypoints` grounds a `reroute` to the declared far-aisle waypoints in both grounding modes; every scene without the field still grounds `waypoints: []`, byte-identical. |
| A: family authoring | Built and pinned: `loop_detour_permanent` (box) and `loop_detour_transient` (marker-less robot visual), one factor with two cells. The minimal loop has one connector, so it supports only one detour length. Oracle block (`LoopDetourOracleConfig` + `LoopDetourCostRecord`), scorer (`coverage_scene_scores.py loop`, `loop-cost`), regret arms (`strategy_regret.py`), VM drivers. |
| A: VM | **STOP: the design control failed.** On the VM Nav2 self-detours in the permanent cell before any decision, in 3 of 3 runs. robot_1 never reaches the blocker, so the wait-vs-detour question is never asked of M2/M3. The self-detour is robust; its mechanism is only partly characterized (below). No cost table was collected. |
| A: tracked-robot blocker | **STOP (design):** a tracked "faulted robot" blocker cannot stall robot_1 without a permanent M4 pair latch or a Nav2 self-detour (arithmetic below). The authored transient cell therefore uses T3a's untracked marker-less visual. This deviates from the task's note and needs a coordinator ruling. |
| B: visual pass | **PASS** (table below). One caveat: the empty robot_1 in r2 was 99.55% fresh (a 2-row blip on the robot without a prop), against the checklist's 100%. One flagged recurrence: the B3 goal-stack latch at 0.445 m, which the registered censoring valve covers. |

VM state at close-out: pristine configs restored and md5-verified after
every run, GPU idle, no Isaac process, and the VM tree equals the branch
tip except the pristine `orchestrator.yaml`. Zero API spend (mock only).

---

## Part A: loop-detour family

### Design as authored

Geometry (`isaac/config/scenarios/loop_detour_permanent.yaml` header):

- **Loop map:** identical to the phase-1 probes. The second aisle is at
  y = 1.2 and there is one new connector at x = 1.8.
- **Pinch corridor:** a 0.50 m `aisle_barrier` over x ∈ [0.7, 1.25], between
  the junction and the connector.
- **Blocker:** lidar cross-section y ∈ [-0.25, 0.03], leaving a **0.22 m** gap.
- **robot_1:** (-2.4, 0) → (2.3, 0).
- **Detour:** waypoints (0.3, 1.2) → (1.8, 1.2); the base mission then
  resumes the goal down the connector.

The design control was that the gap is narrower than the collision
monitor's 0.24 m forward stop box, so robot_1 would be stopped short of
it. The gap was also meant to stay above NavFn's closure, so the global
plan would stay through the primary aisle and the detour would remain a
decision for M2/M3.

| Cell | Blocker (visual only) | Correct answer (design) | Arm B |
|---|---|---|---|
| permanent | grey box, never moves | `reroute` (wait censored by construction) | `blocked_path` → `reroute` (agrees) |
| transient | marker-less robot visual (T3a's transient), leaves at a dwell | `temporary_wait` (hypothesis; dwell **unregistered**) | `blocked_path` → `reroute` (diverges) |

No text channel carries persistence. Only robot_1 is tracked, the task
label is neutral, and there are no static obstacles. The rendered prompt is
pinned at grep level (`tests/unit/test_loop_detour_scenarios.py`,
`TestNoTextPersistence`). The template's own `blocker_kind` vocabulary
(robot / object / transient) is the T3a question, not a hint.

**Arm B per cell.** It is the same in both cells: robot_1 is stopped, and no
tracked robot is within `r_block_m` ahead. That gives `blocked_path`, then
`reroute`, and a one-leg `reroute` plan. Pinned (`TestArmB`) and confirmed
live: M5's shadow classical logged `scenario=blocked_path strategy=reroute`
on 43 of the 44 loop-run analyses. The remaining one was `none`.

### VM runs

All runs were mock, seed 42, `REC_SEC=950` / `SIM_SEC=1000` (`450`/`500`
for the diagnostic), driven by `scripts/vm/v2_final_run.sh`. Each passed
the `logs saved to` gate and ended with RESTORE OK. Scores come from
`coverage_scene_scores.py loop`. Bundles are in
`data/logs/vm_runs/loop_family/<label>/`.

| Run (stamp) | Mock | Left primary aisle (y > 0.6) | First dispatch | Outcome | STALE |
|---|---|---|---|---|---|
| `perm_wait_s42` (20261003_041339) | wait once | 26.4 s | `temporary_wait` @ 34.3 s | never arrived (censored 228.3 s), wedged at the second-aisle mouth (0.47–0.56, 0.68–0.93) for > 150 s | 44-row (20.4 s) streak, 219.5–240.0 s, during the final dwell at (0.559, 0.933) beside the 0.3 m remnant corner; flagged |
| `perm_reroute_s42` (20261003_043348) | reroute once | 25.3 s | `reroute` @ 36.3 s (robot already on its self-detour, at (0.31, 0.90)) | `follow_waypoints` never progressed: robot_1 sat 0.3 m from waypoint 1 for about 60 s. M4's Nav2-leg watchdog FAILED the command after about 121 wall-s; the robot ended at (0.564, 0.395) and never arrived | max 3 rows |
| `diag_costmap_s42` (20261003_054917) | silent (default) | 26.7 s | none | Nav2's own detour drove the loop after a 15 s pause at the aisle mouth; arrived at 55.9 s after t0 | 0 |

In all three runs (`self_detour: true`), NavFn's first sampled plan went
direct (sim 10.8 / 12.1 / 12.6 s, max |y| 0.13). **From the next sample on
(11.7 / 13.0 / 13.6 s), every global plan went round the loop.** That was
while robot_1 was still near x ≈ -2.3, long before it reached the gap. The
collision-monitor stall the design depends on therefore never occurred.

### Mechanism (partly characterized)

The self-detour is robust. Its mechanism is only partly established.
Evidence is in `data/logs/vm_runs/loop_family/navfn_sweep/` (README there),
plus `diag_costmap_s42/costmap_series.jsonl`.

1. **Contributing factor: the gap's cost.**
   - At sim 10.4 s, before departure, the live global costmap of
     `diag_costmap_s42` carried lidar marks of the box and its corner at
     x ≈ 0.78–1.03, y ≈ -0.125..0.125. Those marks are absent from the
     same static map loaded standalone (`standalone_C_corr50.json`).
   - With the global inflation band (inscribed radius 0.08 m, inflation
     0.10 m), almost every pinch cell is then high-cost (OccupancyGrid
     80–99).
   - A standalone NavFn sweep on baked maps (no Isaac; shipped
     planner and global-costmap settings; `sweep_results.txt`):

   | Map (loop present) | From (-2.4, 0) | From (0.5, 0) |
   |---|---|---|
   | no pinch, no box (phase-1 map) | direct | direct |
   | 0.50 / 0.55 / 0.60 / 0.70 / 0.80 m pinch, no box | direct | direct |
   | box leaving a **0.22 m** gap (open aisle) | **loop** | direct (max \|y\| 0.45) |
   | box leaving 0.30 / 0.40 / 0.55 m | direct | direct |

   A 0.22 m box gap alone flips NavFn from the spawn; 0.30 m does not. The
   collision monitor stops a centred robot only below 0.24 m. At the tested
   widths, no gap stalls robot_1 without also making NavFn prefer the loop
   on cost (cell cost ≈ 50 + 0.8 × costmap cost, against the loop's extra
   1.4–2.4 m).
2. **Unexplained contradiction.** In `perm_reroute_s42` at sim 54.8 the
   gap cost no longer applied, yet the live planner still preferred the
   loop:
   - `costmap_marks.py` found zero lethal sensor marks in the whole live
     global grid.
   - The live pinch crop matched the static map: centre band cost 0, 80 at
     |y| = 0.175, 99 at 0.225 (`costmap_dump_perm_reroute.json`).
   - A live `ComputePathToPose` still went round the loop from every
     tested start, including (0.65, 0) at the corridor mouth
     (`live_plan_probe_perm_reroute_s42.json`).
   - Standalone NavFn on the same static map plans direct.

   One lead is not followed up. Along the whole primary aisle, the live
   wall cells read 99 at y = ±0.525 where the standalone costmap reads 80
   (lidar marks the rack faces just inside the map's wall cell). This
   would not obviously close a 5-cell zero-cost centre band. **The live
   planner's preference cannot yet be fully explained by the costmap it
   publishes.**

Consequence for the options below: option (a), lengthening the detour,
assumes the flip is purely cost-relative. Item 2 means that is **not
established**.

Second finding, on **loop drivability**. Phase 1 only *planned* into the
loop with `compute_path_to_pose`, and nothing ever drove it.

- Nav2's own detour completed once, in the diagnostic run (silent mock).
- It wedged once at the second-aisle mouth for over 150 s
  (`perm_wait_s42`, after a `temporary_wait` cancelled and resumed it).
  The 0.3 m connector-flanking remnant corner is at (0.6, 0.6–0.925).
- **The declared reroute is unit-pinned but its live M4 path is
  unvalidated.** This was the first-ever live `follow_waypoints` in this
  stack. It was dispatched mid-self-detour and stalled 0.3 m from
  waypoint 1 (8 Nav2 "Failed to make progress" aborts, then the
  watchdog). It was not root-caused; it could be an integration issue
  (the M4 `follow_waypoints` leg) or geometry. It should not be read as
  "the loop is undrivable".

The global obstacle layer was also observed to keep stale box marks until
raytraced away. `perm_reroute_s42` at sim 54.8 showed zero sensor marks
after robot_1 had moved off.

### Tracked-robot blocker: why it is not the transient cell

Two mechanisms rule out the literal design. In it, the faulted robot is a
tracked robot held by M5's hold-back and released after the dwell.

- **M4 latch fires first.** The latch fires below 0.45 m centre-to-centre
  and both robots of the pair stay latched until a fresh reading shows them
  ≥ 0.45 m apart. Neither can move, so this is permanent (`safety.evaluate_latches`;
  the 7b "latches for good" mechanism). The collision monitor's stop box
  reaches at most √((0.25 + 0.07)² + (0.12 + 0.09)²) = 0.38 m
  centre-to-centre on another robot. Any proximity stall behind a tracked
  robot is therefore a permanent pair latch. The held robot can never leave,
  and both forced arms are censored.
- **The planner stops seeing it.** A tracked robot's lidar cross-section is
  only its LDS turret. A pinch narrow enough that the turret closes it is
  the passage-closing case, which makes NavFn replan onto the loop (above).

`isaac/config/scenarios/loop_detour_probe_tracked.yaml` (the literal design)
and `loop_detour_probe_lethal.yaml` are authored and USD-built but were
**not run**: the self-detour already decides both questions. The authored
transient cell instead uses T3a's untracked marker-less robot visual.

### Coordinator decision needed (not applied)

Options, none applied:

- (a) **Lengthen the detour.** NavFn's choice is cost-relative, so a
  far-aisle detour long enough to outweigh the inflated gap path could keep
  the global plan direct. The minimal loop cannot do this inside the
  tracked band. One candidate is to move the second aisle to y ≈ 1.6–1.8
  (unverified for M1 and for camera shadows).
- (b) **Use a stall mechanism NavFn cannot see.** One candidate is a
  sub-lidar-plane box (< 0.182 m) that physically stops robot_1. The robot
  cell cannot match it, so this changes the cell symmetry and becomes a
  contact event.
- (c) **Change shared Nav2 parameters** (global inflation, NavFn cost
  weighting). These are v1-shared; a protocol call.
- (d) **Accept Nav2's own detour** as the detour arm and re-scope the
  decision to wait-vs-let-Nav2-detour, so M2 would have to *stop* a
  self-detouring robot. That is a different question from the spec's.
- (e) **Retire (b)** from v2 and register it as a v3 item.

The transient dwell (`remove_at_sec: 45.0`) is a provisional placeholder,
explicitly unregistered. `cost: null` stays in both oracle blocks. Both
scenario headers now carry a STATUS block: do not collect.

### What is built and pinned regardless

| Artifact | Pin |
|---|---|
| M3 reroute waypoints (`reasoning/rag/scene_geometry.py`, `command_grounder._reroute_waypoints`) | `tests/unit/test_reroute_waypoints.py` (7): legacy and derived forward the detour; absent field = `waypoints: []`; byte-identical off the reroute action |
| Two cells + two probes, maps (all byte-identical on regeneration; all four share one map) | `tests/unit/test_loop_detour_scenarios.py` (44): pair diff, authored gap arithmetic vs `nav2_params.yaml`, tracked band, camera shadow, no-text, Arm B, oracle validators, overlay, scorer |
| `LoopDetourOracleConfig` / `LoopDetourCostRecord` (`isaac/vgu_sim/config.py`) | permanent ⇒ `reroute`; cost winner must equal the answer; censored winner rejected; margin consistency |
| `coverage_scene_scores.py loop` / `loop-cost` | self-detour flag, stall onset, censoring, `outcome_rank` = (arrived, −time_to_goal), STALE streaks, sampler summary |
| `strategy_regret.py` scenes `loop_detour_{permanent,transient}` (arms `wait`, `reroute`; `--min-runs 1`) | preflight checks `reroute_waypoints` (`tests/unit/test_strategy_regret.py`) |
| VM tooling: `scripts/vm/v2_final_run.sh` (all standing traps), `v2_overlay.py`, `loop_family_sampler.py`, `frame_snapshots.py` | overlay pinned against the real `load_config` and the regret preflight |

**Protocol note (M3, v2 branch only).** `SceneGeometry` gains an additive
optional field, None by default. No v1 artifact changes.

---

## Part B: step-9 visual pass

| Checklist item | Result | Evidence |
|---|---|---|
| Build + validate `priority_visual_r1`, `_r2`, `convoy_counterflow_slip` USDs | **PASS**: all three `build_rc=0`, then `validate_simulation` PASS; `validate_robot_load_prop` ran inside the build. The four `loop_detour_*` USDs also built and validated | VM `~/v2final_usd_build.log` |
| Load prop renders visibly in the annotated frame without occluding the marker, at standoff and at spawn/goal parallax positions | **PASS**: the brown load prop sits behind the marker on the loaded robot in every phase and in both members. The marker is never covered: at spawn (±1.5, 0), at standoff (±0.15, 0), and at the goals near the ROI edges (2.46, 0) and (-2.45, 0) with a rotated final heading | `data/logs/vm_runs/visual_pass/crops/` (24 PNG crops, raw + annotated, `crops.json`) |
| M1 detection unaffected (100% fresh, loaded + empty) | **PASS for the loaded robot**: 100.00% fresh in both members (r1 robot_1 436/436; r2 robot_2 440/440). Empty robots: r1 robot_2 100.00%, r2 robot_1 99.55% (one 2-row, 0.23 s blip). No STALE streak in either run | `pv_r{1,2}_s42/m5_scene.jsonl` |
| Loaded-vs-empty A/B crop diff | **Saved**: same robot, same spawn pose, stationary (sim ≈ 10.6 s), r1 vs r2. Prop region: 823 (robot_1) / 792 (robot_2) pixels differ by > 30 (max channel). **Marker window: 0 pixels differ** (mean 1.7–1.8, render noise) | `crops/ab/ab_robot_{1,2}_{loaded,empty,absdiff,side_by_side}.png` + `.json` |
| Maps regenerate byte-identical | **PASS**: `priority_visual_r1/_r2` (`.pgm` md5 `96113d92…`, shared) and `convoy_counterflow_slip` (`f48cb508…`) match the committed copies, which match the VM's installed copies | local regeneration + VM `md5sum` |
| `coverage_scene_scores.py b3` on a real `convoy_counterflow_slip` GT log | **Sane**: conflict onset 24.2 s (window [15, 50]). `first_slipper` = robot_1, `slip_onset_sec` robot_1 52.8 / robot_3 74.1 / robot_4 115.3, `first_slip_latency_sec` 28.6. GT agrees: robot_1 is stationary at (-0.13, -0.03) from about 26 s to 52 s and moves at 0.09 m/s from 52.8 s (x = 0.21 by 56 s), after robot_2 has pulled off to (1.13, -0.38) by about 48 s. GT horizon 260 s, well past the slip window | `visual_pass/b3_slip_s42/b3_score.json` |

**B2-visual runs.** `pv_r1_s42` (20261003_045905) and `pv_r2_s42`
(20261003_051343) used the mock `priority_visual_r{1,2}_yield_once.json`
with the pristine config, which is the goal-table row. Both reached 2/2
arrivals with zero contacts, and the loaded robot arrived first (71.3 /
71.1 s after t0).

**Flagged, not acted on:**

1. **Arm B's shadow yielder differs from the registered one.** Shadow
   only, one episode per member. The live Arm B yielder was robot_1 in r1
   and robot_2 in r2, the loaded robot in both. The oracle blocks register
   `classical_yielder: robot_2` for both members. Arm B's FCFS reads
   arrival stamps, so live arrival jitter can move it. The coordinator
   should know the registered classical answer is not stable across live
   episodes.
2. **B3 goal-stack latch recurred.** robot_3 stopped 0.37 m from its goal,
   0.4448 m from the parked robot_1: under the 0.45 m floor and latched
   permanently. That censored robot_3 (`score_ground_truth` total 654 s,
   censored). This is the registered B3 goal-stack issue (Rev 22 margin
   table: 0.463–0.475 m measured), now one measured instance below the
   floor. It is covered by the registered censoring valve and not touched
   here.
3. **STALE streak at robot_1's goal in B3.** robot_1 had STALE streaks of
   up to 20 rows (6.2 s) at (2.39, -0.30), 87 of 799 rows in all. This was
   a stationary dwell at the goal after arrival, so it is decision-
   irrelevant. Flagged per the instrumentation rule.
4. **The offline ArUco decoder is a weak secondary check.** It decoded the
   marker on most crops but missed some, including both members' robot_2
   at the west goal. M1's own fresh rate is the authoritative instrument,
   and it was 100% at those poses. The crops show every marker
   unobstructed.

---

## Verification

**Local suite.** `pytest -q --continue-on-collection-errors`, same `.venv`
for both runs.

| Tree | Failed | Passed | Skipped | Collection errors |
|---|---|---|---|---|
| Baseline at `1ee23d2` (clean detached worktree) | 63 | 4490 | 152 | 3 |
| Branch | 63 | 4551 | 152 | 3 |

The failing-name sets are identical (`diff` empty). The +61 passes are this
branch's new pins. The coordinator's quoted baseline (58 / 4479 / 149) is
from a different environment. The comparison here is like-for-like on one
venv.

**VM discipline.**

- Every launch was preceded by a `pgrep -f run_simulation` empty gate,
  launched as root, and used the FASTRTPS UDP profile (fc_launch).
- Deploy:
  - `git archive` of the branch tip was extracted with `tar -m`.
  - The pristine `orchestrator.yaml` was restored from a verbatim backup,
    with `touch`.
  - `colcon build --merge-install` was run for swarm_interfaces,
    swarm_execution, swarm_orchestrator and swarm_simulation.
  - Manifest: 760 tracked files, all md5-equal to the branch except
    `orchestrator.yaml` (`1f656533…`, pristine).
- USDs were rebuilt before any run of an edited scenario.
- Each run's `RESTORE.txt` confirms src, installed and rag md5s pristine.

---

## References

- Spec: `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (b), (c), (e)
- Phase-1 report: `docs/reports/2026-10-02-loop-preemption-smoke.md`
- T3a stall mechanism: `isaac/config/scenarios/blocked_path_object.yaml` header
- Run bundles: `data/logs/vm_runs/{loop_family,visual_pass}/` (local and VM)

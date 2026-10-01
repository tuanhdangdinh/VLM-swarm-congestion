# M1 Y-Extent Verification — Composite Command Recede Endpoints

**Prepared:** 2026-10-01

**Revision history:**

- Initial draft: v2 build-order step 3 (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`,
  "Prerequisites" item 3) — verifies M1 tracks the composite `junction_clear`
  command's cross-pair recede endpoints, `|y| ~= 1.2`, on the GPU VM with a
  mock backend (zero API spend), before oracle design proceeds.
- Rev 2 (2026-10-01): replicated run A (n=2) after review — the `|y|=1.2`
  result reproduces cleanly, and the `robot_1`/`x=-1.75` dropout also
  reproduces (51 vs. 53-row STALE streak), which rules out one-off noise
  and promotes it from a passing "surprise" note to a registered risk,
  below. Added per-frame `exact_stamp_match_rate` / `max_age_sec` columns
  (stricter than the STALE-threshold-gated fresh rate) and an explicit VM
  tree-state section.

**commit:** `a742768` (scenario yamls + driver script), `04cc9b0` / `ac2f689`
(two driver fixes found while running this probe), `ccd11b4` (rev 2:
replicate run + this revision), branch `feat/v2-y-extent`

---

## Purpose

`docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`
("Prereg-v2 Path — Composite Junction Clear") specifies that the
`junction_clear` command's cross pair "reverses along its own arms to
`|y| ~= 1.2`". That same study's Constraint 2 calls the tracked band
`|x| <= 2.5`, `|y| <= 1.80` "verified" by live VM runs, and leaves `1.80`
to the `2.092` homography y-edge "unverified". `1.2` sits well inside the
verified band on paper, but the study never ran a dedicated check at that
exact point, and the prereg-v2 design doc's build order makes that an
explicit, separate gate (item 3) before oracle design for (a)+(d) proceeds.
This report is that gate.

---

## Method

Three short mock-backend runs (`BACKEND_ID=mock`, no `MOCK_DECISION_FILE`,
zero VLM calls — confirmed below) on the standing VM
(`vgu-vgu-thule-base-isaac-workstation-vm`, container `vgu_ros`), each
holding all four robots **stationary** for a 120 sim-s dwell via a huge
`start_delay_sec` (no Nav2 goal is ever dispatched — `task_registry.py`
counts a pending assignment from load time, the same mechanism T2b/B1/B3
use for a hold-back, just sized to outlast the whole episode):

- `isaac/config/scenarios/m1_y_extent_probe_a.yaml`, run twice (seed 42
  both times) — the actual requirement point: `robot_3`/`robot_4` at
  `y = -1.2` / `+1.2` (both signs, matching the composite command's
  two-robot recede), plus `robot_1`/`robot_2` at the already-verified
  `x = -1.75` / `+1.75` as a live two-axis reference. Run twice because the
  first run's `robot_1` result (below) was surprising enough to need a
  replicate before trusting it either way.
- `isaac/config/scenarios/m1_y_extent_probe_b.yaml`, run once — the open
  question the study actually flags, not a repeat of run A: `robot_3`
  re-checks the `y = 1.80` edge stationary (it was previously only
  confirmed in motion, IBB4), `robot_4` pushes to `y = 2.0` inside the
  unverified `1.80-2.03` band and still inside the homography edge;
  `robot_1`/`robot_2` spend their free slots on a cheap bonus x-sweep at
  `x = +-2.4`, `0.1` m inside the verified `|x| <= 2.5` edge.

Every scenario build was validated (`validate_simulation.py`: `PASS` on
every USD) and run through the existing `scripts/vm/fc_launch.sh` harness
via a new driver, `scripts/vm/m1_y_extent_probe.sh`, which temporarily
rewrites `orchestrator.yaml`'s `initial_tasks` block to the four-robot hold
(`scripts/vm/patch_initial_tasks.py`, a byte-scoped regex patch that
touches only that block) and restores it — verified byte-identical and
pristine-md5 on both the source and the installed copy — on exit regardless
of outcome.

Detection was scored from M5's own per-second copy of
`/perception/scene_state` (`data/logs/m5_scene/<session_id>.jsonl`)
against each robot's known stationary spawn pose (confirmed by Isaac's
`ground_truth.jsonl` to settle within `0.0001` m of that spawn in every
run — the authored spawn is an adequate stand-in for "true position" here,
unlike a moving scenario):

- `fresh_rate`: fraction of rows with status `!= STALE`.
- `exact_stamp_match_rate`: the stricter fraction of rows where
  `robot.stamp == scene.stamp` exactly (CLAUDE.md's
  `RobotState.stamp <= SceneState.stamp` invariant — a carried-forward
  robot keeps its last stamp while the scene's own stamp advances);
  `fresh_rate` alone can hide short carried-forward gaps that never cross
  the `stale_after_sec` threshold (1.15 s).
- `max_age_sec`: the longest any single detection was carried forward.
- `longest_stale_streak`: the longest run of consecutive `STALE` rows.
- `bias_x_m` / `bias_y_m`: mean/median/max `|measured - spawn|` on fresh
  rows.

Full method and script: `scripts/m1_y_extent_probe_analysis.py`.

---

## Results

**Run A1** (`m1_y_extent_probe_a`, seed 42, STAMP `20261001_065904`, 285
scene rows/robot):

| Robot | Spawn | Fresh rate | Exact-stamp rate | Max age (s) | Longest STALE streak | Bias x (mean/max, m) | Bias y (mean/max, m) |
|---|---|---|---|---|---|---|---|
| robot_3 | (0, **-1.2**) | 100% | 100% | 0.0 | 0 | 0.0022 / 0.0022 | 0.0029 / 0.0029 |
| robot_4 | (0, **+1.2**) | 100% | 100% | 0.0 | 0 | 0.0022 / 0.0022 | 0.0072 / 0.0072 |
| robot_2 | (+1.75, 0) | 100% | 87.7% | 0.667 | 0 | 0.0061 / 0.0064 | 0.0022 / 0.0033 |
| robot_1 | (-1.75, 0) | 26.0% | 3.2% | **20.633** | **53** | 0.0102 / 0.0108 | 0.0022 / 0.0022 |

**Run A2** (replicate, same scenario/seed, STAMP `20261001_074401`, 291
scene rows/robot — run after the surprising `robot_1` result to rule out a
one-off):

| Robot | Spawn | Fresh rate | Exact-stamp rate | Max age (s) | Longest STALE streak | Bias x (mean/max, m) | Bias y (mean/max, m) |
|---|---|---|---|---|---|---|---|
| robot_3 | (0, **-1.2**) | 100% | 99.7% | 0.033 | 0 | 0.0022 / 0.0022 | 0.0029 / 0.0029 |
| robot_4 | (0, **+1.2**) | 100% | 100% | 0.0 | 0 | 0.0022 / 0.0022 | 0.0072 / 0.0072 |
| robot_2 | (+1.75, 0) | 100% | 92.4% | 0.433 | 0 | 0.0062 / 0.0064 | 0.0022 / 0.0033 |
| robot_1 | (-1.75, 0) | 17.9% | 1.4% | **19.833** | **51** | 0.0103 / 0.0108 | 0.0022 / 0.0022 |

**Run B** (`m1_y_extent_probe_b`, seed 42, STAMP `20261001_071617`, 292
scene rows/robot):

| Robot | Spawn | Fresh rate | Exact-stamp rate | Max age (s) | Longest STALE streak | Bias x (mean/max, m) | Bias y (mean/max, m) |
|---|---|---|---|---|---|---|---|
| robot_3 | (0, **-1.8**) | 100% | 97.3% | 0.367 | 0 | 0.0031 / 0.0033 | 0.0054 / 0.0065 |
| robot_4 | (0, **+2.0**) | 100% | 100% | 0.0 | 0 | 0.0018 / 0.0022 | 0.0113 / 0.0113 |
| robot_1 | (-2.4, 0) | 100% | 100% | 0.0 | 0 | 0.0123 / 0.0123 | 0.0022 / 0.0033 |
| robot_2 | (+2.4, 0) | 100% | 100% | 0.0 | 0 | 0.0080 / 0.0080 | 0.0011 / 0.0022 |

GT cross-check (all three runs): every robot's true pose (Isaac chassis-prim
samples, ~10 Hz) stayed within `0.0001` m of its authored spawn for the
whole episode — confirming the "stationary" premise holds, so the bias
figures above are M1 tracking error, not robot drift.

**Zero VLM spend confirmed operationally, not just by backend selection:**
`data/logs/m5_decisions/` carried the same newest file (dated Sep 30, before
any of these runs) after all three — no run's robots were ever close
enough, or stalled with a goal, to trip the congestion detector, so M2 was
never invoked.

---

## Verdict

| Check | Expected | Actual |
|---|---|---|
| `robot_3` tracked at `y = -1.2`, n=2 | fresh, non-STALE, bounded bias | PASS — 100% fresh both runs, 0 STALE both runs, bias 0.0029 m both runs |
| `robot_4` tracked at `y = +1.2`, n=2 | fresh, non-STALE, bounded bias | PASS — 100% fresh both runs, 0 STALE both runs, bias 0.0072 m both runs |
| Bias vs. M1 error budget (study: median <= 0.011, max 0.084 m) | within budget | PASS — 0.0029-0.0072 m, well inside |
| Bias vs. mover-legality clearance (study: 0.55 m) | negligible vs. budget | PASS — bias is ~1-2% of the clearance margin |

**PASS, replicated.** The composite `junction_clear` command's recede
endpoints, `|y| ~= 1.2` (both signs), are confirmed tracked across two
independent runs: 100% fresh detection (and 99.7-100% exact-stamp-match,
the stricter per-frame signal) across the full 120 sim-s dwell in both,
zero `STALE` events in either, bias an order of magnitude below the
study's own M1 error budget and essentially identical between the two
runs (0.0029 / 0.0072 m both times). Oracle design for (a)+(d) may proceed
past this gate. This verdict covers only the `|y| ~= 1.2` recede points —
see "Registered risk" below for a separate, reproducible finding at a
different point in the same scenario that the IB10 build should account
for before that step.

**Margin.** Run B additionally confirms clean (100% fresh, 0 STALE)
tracking at `|y| = 1.8` (stationary, not just in motion as IBB4 showed) and
at `|y| = 2.0` — inside the previously-"unverified" `1.80-2.03` band, with
bias still only `0.0113` m. That gives:

- `0.8` m of margin between the `1.2` requirement and the farthest point
  this probe confirmed clean (`2.0`).
- `0.892` m of margin between the `1.2` requirement and the hard
  homography y-edge (`2.092`).

These two points do not fully re-derive the band (a probe at exactly
`2.03`, where the marker clips, was not run — not needed for the `1.2`
requirement), but they substantially narrow the open question the study
recorded, as a byproduct of spending the scenario's spare N-S slots on it
rather than repeating the `1.2` measurement in run B.

---

## Registered risk — `robot_1` at (-1.75, 0) reproducibly loses tracking

**This is not a y-extent finding and does not change the PASS verdict
above** (it sits on the x-axis reference pair, not `|y| ~= 1.2`), but it is
significant enough, and close enough to this probe's own scope, to flag as
a registered risk rather than bury as a curiosity: **`robot_1` spent 74%
and 82% of two independent 120 s runs `STALE` at `(x, y) = (-1.75, 0)`,
with max carried-forward ages of 20.6 s and 19.8 s and STALE streaks of 53
and 51 consecutive ~1 s rows.** That is not noise:

- **It reproduced.** Same scenario, same seed, run twice, ~20 minutes
  apart, after a full container restart between them — 26.0% vs. 17.9%
  fresh, 53 vs. 51-row streaks, 20.633 s vs. 19.833 s max age. Two
  independent runs landing in the same regime rules out a one-off
  render/timing fluke.
- **It is specific to this (position, marker) pair, not a general x = 1.75
  or marker_id = 1 defect.** The mirror point `robot_2` (`marker_id = 2`)
  at `x = +1.75` was 100% fresh in both run A1 and A2. `robot_1` itself
  (`marker_id = 1`) was 100% fresh in run B at a different x (`-2.4`). So
  neither "that marker" nor "that x value" alone explains it — the
  specific combination `(marker_id=1, x=-1.75, y=0, yaw=0)` does.
- **It is exactly `robot_1`'s spawn in the real `intersection_bottleneck.yaml`
  scenario** (`isaac/config/scenarios/intersection_bottleneck.yaml`:
  `robot_1`, `marker_id: 1`, `spawn: {x: -1.75, y: 0.0, yaw_rad: 0.0}`) —
  the IB10 cell this whole v2 path is building toward. If this probe's
  dropout pattern carries over, `robot_1` could spend a large fraction of
  IB10's pre-trigger dwell `STALE`, which would affect:
  - **The resolution-scored IB10 criterion** ("all four robots reach
    goals, position-verified" — prereg-v2 design doc, "(a) Composite
    recede-then-yield command" > "Scoring"), since a `STALE` robot's
    reported pose is a carried-forward last-known position, not a live
    measurement.
  - **Arm B's shadow classification**, which reads the same
    `/perception/scene_state` snapshots.
- **Not root-caused here** — out of this probe's scope (y-extent only) and
  would need its own investigation (repeat `x = -1.75` alone at several
  seeds/marker_ids to isolate render vs. marker-pattern vs. position; check
  whether `robot_1` always bringing up `fc_launch.sh`'s shared Nav2 map
  server first is a confound, though run B's clean `robot_1` at a different
  x argues against it). **Recommendation: treat as a build-order item before
  step 6 (IB10 composite mock smoke)**, not before this gate.

---

## Other surprises

- **Bias grows mildly toward the tracked edge.** `bias_y` at the four y
  points tested: `1.2 m -> 0.0029-0.0072`, `1.8 m -> 0.0054`,
  `2.0 m -> 0.0113`. Small and still inside the study's documented M1 error
  budget (max `0.084` m), but a real, monotonic-looking trend consistent
  with a homography edge effect — not a detection failure (fresh rate
  stayed 100% throughout).
- **Even "clean" (non-STALE) robots are not always exact-fresh.**
  `robot_2` at `x = 1.75` was 100% `fresh_rate` in both A runs but only
  87.7% / 92.4% `exact_stamp_match_rate`, with carried-forward gaps up to
  0.667 s — short enough to never cross the 1.15 s `stale_after_sec`
  threshold, but evidence that brief detection gaps are a normal background
  rate, not unique to `robot_1`'s failure mode. Only `robot_3`/`robot_4` at
  `y = ±1.2` hit ~100% exact-stamp-match in both runs.
- **Two tooling bugs found and fixed while running this probe** (both
  landed in `scripts/vm/m1_y_extent_probe.sh` / `patch_initial_tasks.py`,
  commits `04cc9b0`, `ac2f689` — see their messages and the scripts'
  updated docstrings/comments for the full mechanism):
  1. `fc_launch.sh`'s own decision-summary stage runs
     `ls -t m5_decisions/*.json | head -3` under `set -e -o pipefail`; with
     more than 3 leftover files from unrelated prior sessions (there were
     2180), this aborts the script before its final `done: STAMP=...` log
     line — the run itself completes cleanly, but a caller relying on that
     line (as the first version of this probe's driver did) silently gets
     no stamp. Fixed by parsing the stamp from the M1-perception start line
     instead, which is unaffected and always present. Not a fix to
     `fc_launch.sh` itself (shared, frozen harness, out of this task's
     scope) — recorded here as an operational trap for any future caller.
  2. `patch_initial_tasks.py --restore` originally used `shutil.copy2`,
     which carries the **backup's** old mtime onto the restored file. A
     restored file older than the package's last `colcon build` output
     makes colcon's incremental build silently skip re-copying it into
     `install/` even though the content differs and the build reports
     success — exactly the project's standing "never trust colcon exit
     codes" trap, here triggered by a config *restore* rather than a
     *deploy*. Caught by an end-of-task manual md5 check (the driver's own
     post-restore log line was checking the wrong path — a second,
     separate bug, also fixed) that found the VM's **installed**
     `orchestrator.yaml` still carrying run B's patched `initial_tasks`
     after the driver claimed a clean restore. Fixed in both the Python
     script (plain `shutil.copy`, fresh mtime) and the driver (explicit
     `touch` before the post-restore rebuild, plus a loud
     pass/fail check against the pristine md5 instead of a bare log line).
     The VM was left pristine (see below) only after this fix was applied
     and manually re-verified.

---

## Artifacts

- Scenario yamls: `isaac/config/scenarios/m1_y_extent_probe_a.yaml`,
  `isaac/config/scenarios/m1_y_extent_probe_b.yaml`.
- Driver + patch tool: `scripts/vm/m1_y_extent_probe.sh`,
  `scripts/vm/patch_initial_tasks.py`.
- Analysis script: `scripts/m1_y_extent_probe_analysis.py`.
- VM raw logs (git-ignored, left on the VM at
  `/home/ubuntu/vgu-vlm-swarm/data/logs/vm_runs/y_extent_probe/`):
  - `a_20261001_065904/` — run A1 (`m1_y_extent_probe_a`, seed 42).
  - `a_20261001_074401/` — run A2, the replicate (same scenario/seed).
  - `b_20261001_071617/` — run B (`m1_y_extent_probe_b`, seed 42).
- Synced copy, durable in the main checkout (git-ignored, under
  `data/logs/`, not just the `feat/v2-y-extent` worktree — the worktree is
  disposable, this copy is not): same three directory names under
  `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/data/logs/vm_runs/y_extent_probe/`,
  each holding `scenario.yaml`, `m5_scene.jsonl`, `gt/ground_truth.jsonl`,
  `m1.log`, `m5.log`, `isaac.log`, `launcher.log`.

Reproduce the tables above:

```bash
python3 scripts/m1_y_extent_probe_analysis.py \
  data/logs/vm_runs/y_extent_probe/a_20261001_065904 \
  data/logs/vm_runs/y_extent_probe/a_20261001_074401 \
  data/logs/vm_runs/y_extent_probe/b_20261001_071617
```

---

## VM Tree State — What Actually Changed on Disk

The VM's repo checkout (`/home/ubuntu/vgu-vlm-swarm`, host path bind-mounted
to `/ws` in `vgu_ros`) had **no `.git` directory** before this task (deployed
by tar, not clone) and no record of which commit it held. The last known
marker, from memory, was the pre-freeze tree `4c06800`. This task's deploy
(`git archive HEAD` + a 652-file md5 manifest, verified 0 mismatches) moved
it forward to `a742768` (later to `f4cb623` for two in-place script fixes).
`git diff --stat 4c06800 f4cb623 -- . ':!docs'` — every **non-doc** file
that changed between the VM's prior state and its current one:

```text
 config/models.yaml                               |   7 +-
 isaac/config/scenarios/m1_y_extent_probe_a.yaml  |  61 ++
 isaac/config/scenarios/m1_y_extent_probe_b.yaml  |  54 ++
 scripts/m1_y_extent_probe_analysis.py            | 184 ++
 scripts/vm/m1_y_extent_probe.sh                  | 165 ++
 scripts/vm/patch_initial_tasks.py                |  90 ++
 tests/unit/test_m5_reasoning_pipeline.py         |   4 +-
 tests/unit/test_reasoner.py                      |   6 +-
 tests/unit/test_vlm_config.py                    |   2 +-
```

`config/models.yaml` and the three test files are **not from this task** —
they are part of the `prereg-v1` freeze commit (`569d95c`) that already
existed between `4c06800` and this branch's base; `4c06800..prereg-v1` is
exactly those commits (`5349db7`, `3959d7f`, `569d95c`). Everything from
`prereg-v1` (`569d95c`) to this task's base (`4307aa1`) is **docs-only**
(`git diff prereg-v1 4307aa1 --stat`: one file, the prereg-v2 design doc).
So the VM now holds: `prereg-v1`'s exact pinned code (unchanged), plus
docs-only prereg-v2 design commits, plus this task's five new files. No
v1-frozen artifact was touched. Any session resuming v1 collection on this
VM should be aware the tree advanced past `4c06800` to `prereg-v1`-equivalent
code; any session resuming v2 work should find the five files above still
present (the scenario yamls, the driver, the patch tool, the analysis
script) and their USDs/maps removed (next section).

---

## VM State After This Report

- `orchestrator.yaml` pristine on all three copies checked: host source,
  container source, container installed — `1f656533a30a35882d57d0d64a57bd0d`
  (matches the recorded pristine hash). Verified after an explicit `touch`
  + rebuild (see the tooling-bugs note above on why a bare restore +
  rebuild was not sufficient the first time).
- `config/rag.yaml` untouched throughout (never part of this probe's
  changes): `e18c723cff9cada3f320d564c2ecee5a`.
- Probe USDs (`isaac/scenarios/m1_y_extent_probe_{a,b}.usd`) and maps
  (`warehouse_map_m1_y_extent_probe_{a,b}.{pgm,yaml}`, both source and
  installed copies) removed; `swarm_simulation` and `swarm_orchestrator`
  rebuilt clean afterward.
- `data/logs/simulation/m1_y_extent_probe_{a,b}-seed42-rep000/` (Isaac's
  own GT output dirs) removed after their contents were copied into
  `data/logs/vm_runs/y_extent_probe/`.
- Container `vgu_ros` restarted; no stray
  `isaac.scripts.run_simulation` processes; GPU idle (0% utilization,
  171 MiB / 24570 MiB used — baseline, not this probe's).

---

## References

- Build-order gate: `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`,
  "(a) Composite recede-then-yield command" > "Prerequisites", item 3; "Build
  order", step 3.
- Band analysis this probe verifies against:
  `docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`,
  "Constraint 2: the north-south tracked band against the shipped yield",
  and "Prereg-v2 Path — Composite Junction Clear".
- M1 error budget and mover-legality criterion: same study, "Three
  conventions apply" (end of "Constraints That Bind Every Scheme").

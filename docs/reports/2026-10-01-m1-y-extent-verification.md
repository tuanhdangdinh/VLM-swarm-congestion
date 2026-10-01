# M1 Y-Extent Verification — Composite Command Recede Endpoints

**Prepared:** 2026-10-01

**Revision history:**

- Initial draft: v2 build-order step 3 (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`,
  "Prerequisites" item 3) — verifies M1 tracks the composite `junction_clear`
  command's cross-pair recede endpoints, `|y| ~= 1.2`, on the GPU VM with a
  mock backend (zero API spend), before oracle design proceeds.

**commit:** `a742768` (scenario yamls + driver script), `04cc9b0` / `ac2f689`
(two driver fixes found while running this probe), branch `feat/v2-y-extent`

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

Two short mock-backend runs (`BACKEND_ID=mock`, no `MOCK_DECISION_FILE`,
zero VLM calls — confirmed below) on the standing VM
(`vgu-vgu-thule-base-isaac-workstation-vm`, container `vgu_ros`), each
holding all four robots **stationary** for a 120 sim-s dwell via a huge
`start_delay_sec` (no Nav2 goal is ever dispatched — `task_registry.py`
counts a pending assignment from load time, the same mechanism T2b/B1/B3
use for a hold-back, just sized to outlast the whole episode):

- `isaac/config/scenarios/m1_y_extent_probe_a.yaml` — the actual
  requirement point: `robot_3`/`robot_4` at `y = -1.2` / `+1.2` (both
  signs, matching the composite command's two-robot recede), plus
  `robot_1`/`robot_2` at the already-verified `x = -1.75` / `+1.75` as a
  live two-axis reference.
- `isaac/config/scenarios/m1_y_extent_probe_b.yaml` — the open question
  the study actually flags, not a repeat of run A: `robot_3` re-checks the
  `y = 1.80` edge stationary (it was previously only confirmed in motion,
  IBB4), `robot_4` pushes to `y = 2.0` inside the unverified `1.80-2.03`
  band and still inside the homography edge; `robot_1`/`robot_2` spend
  their free slots on a cheap bonus x-sweep at `x = +-2.4`, `0.1` m inside
  the verified `|x| <= 2.5` edge.

Both scenarios were built, validated (`validate_simulation.py`: `PASS` on
both USDs) and run through the existing `scripts/vm/fc_launch.sh` harness
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
unlike a moving scenario): fraction of rows with status `!= STALE`
("fresh"), longest consecutive `STALE` streak, and mean/median/max
`|measured - spawn|` on fresh rows. Full method and script:
`scripts/m1_y_extent_probe_analysis.py`.

---

## Results

**Run A** (`m1_y_extent_probe_a`, seed 42, 285 scene rows/robot over the
120 sim-s dwell):

| Robot | Spawn | Fresh rows | Fresh rate | Longest STALE streak | Bias x (mean/max, m) | Bias y (mean/max, m) |
|---|---|---|---|---|---|---|
| robot_3 | (0, **-1.2**) | 285/285 | 100% | 0 | 0.0022 / 0.0022 | 0.0029 / 0.0029 |
| robot_4 | (0, **+1.2**) | 285/285 | 100% | 0 | 0.0022 / 0.0022 | 0.0072 / 0.0072 |
| robot_2 | (+1.75, 0) | 285/285 | 100% | 0 | 0.0061 / 0.0064 | 0.0022 / 0.0033 |
| robot_1 | (-1.75, 0) | 74/285 | 26.0% | 53 | 0.0102 / 0.0108 | 0.0022 / 0.0022 |

**Run B** (`m1_y_extent_probe_b`, seed 42, 292 scene rows/robot):

| Robot | Spawn | Fresh rows | Fresh rate | Longest STALE streak | Bias x (mean/max, m) | Bias y (mean/max, m) |
|---|---|---|---|---|---|---|
| robot_3 | (0, **-1.8**) | 292/292 | 100% | 0 | 0.0031 / 0.0033 | 0.0054 / 0.0065 |
| robot_4 | (0, **+2.0**) | 292/292 | 100% | 0 | 0.0018 / 0.0022 | 0.0113 / 0.0113 |
| robot_1 | (-2.4, 0) | 292/292 | 100% | 0 | 0.0123 / 0.0123 | 0.0022 / 0.0033 |
| robot_2 | (+2.4, 0) | 292/292 | 100% | 0 | 0.0080 / 0.0080 | 0.0011 / 0.0022 |

GT cross-check (both runs): every robot's true pose (Isaac chassis-prim
samples, ~10 Hz) stayed within `0.0001` m of its authored spawn for the
whole episode — confirming the "stationary" premise holds, so the bias
figures above are M1 tracking error, not robot drift.

**Zero VLM spend confirmed operationally, not just by backend selection:**
`data/logs/m5_decisions/` carried the same newest file (dated Sep 30, before
either run) after both runs — neither run's robots were ever close enough,
or stalled with a goal, to trip the congestion detector, so M2 was never
invoked.

---

## Verdict

| Check | Expected | Actual |
|---|---|---|
| `robot_3` tracked at `y = -1.2` | fresh, non-STALE, bounded bias | PASS — 100% fresh (285/285), 0 STALE, bias 0.0029 m |
| `robot_4` tracked at `y = +1.2` | fresh, non-STALE, bounded bias | PASS — 100% fresh (285/285), 0 STALE, bias 0.0072 m |
| Bias vs. M1 error budget (study: median <= 0.011, max 0.084 m) | within budget | PASS — 0.0029-0.0072 m, well inside |
| Bias vs. mover-legality clearance (study: 0.55 m) | negligible vs. budget | PASS — bias is ~1-2% of the clearance margin |

**PASS.** The composite `junction_clear` command's recede endpoints,
`|y| ~= 1.2` (both signs), are confirmed tracked: 100% fresh detection
across the full 120 sim-s dwell, zero `STALE` events, bias an order of
magnitude below the study's own M1 error budget. Oracle design for (a)+(d)
may proceed past this gate.

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

## Surprises

- **`robot_1` (x = -1.75) flickered STALE for 74% of run A, including one
  53-row-long streak — at a point the study calls "verified".** This is
  **not a y-extent finding**: it sits on the x-axis reference pair, not the
  measurement under test. Three facts isolate it from a real position
  effect: (1) the mirror point `robot_2` at `x = +1.75` was 100% fresh in
  the *same* run; (2) `robot_1` itself was 100% fresh in run B at a
  *different* x (`-2.4`); (3) the flicker was intermittent (repeated
  STOPPED/STALE transitions roughly every 5-10 sim-s throughout the whole
  run), not a one-time edge dropout. Read together, this looks like a
  transient per-run ArUco/render artifact rather than a reproducible
  position or marker-id defect — but it is a real data point that a
  "parked robot" scenario can still intermittently lose tracking even deep
  inside the verified band, worth a follow-up probe (repeat `x = -1.75`
  alone, several seeds) before anything leans on 100% M1 uptime for a
  long-dwell stationary robot. Out of scope to root-cause here.
- **Bias grows mildly toward the tracked edge.** `bias_y` at the four y
  points tested: `1.2 m -> 0.0029-0.0072`, `1.8 m -> 0.0054`,
  `2.0 m -> 0.0113`. Small and still inside the study's documented M1 error
  budget (max `0.084` m), but a real, monotonic-looking trend consistent
  with a homography edge effect — not a detection failure (fresh rate
  stayed 100% throughout).
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
  - `a_20261001_065904/` — run A (`m1_y_extent_probe_a`, seed 42).
  - `b_20261001_071617/` — run B (`m1_y_extent_probe_b`, seed 42).
- Synced copy (git-ignored, under `data/logs/`, same two directories):
  `data/logs/vm_runs/y_extent_probe/a_20261001_065904/`,
  `data/logs/vm_runs/y_extent_probe/b_20261001_071617/` — each holds
  `scenario.yaml`, `m5_scene.jsonl`, `gt/ground_truth.jsonl`, `m1.log`,
  `m5.log`, `isaac.log`, `launcher.log`.

Reproduce the table above:

```bash
python3 scripts/m1_y_extent_probe_analysis.py \
  data/logs/vm_runs/y_extent_probe/a_20261001_065904 \
  data/logs/vm_runs/y_extent_probe/b_20261001_071617
```

---

## VM State After This Report

- `orchestrator.yaml` pristine on all three copies checked: host source,
  container source, container installed — `1f656533a30a35882d57d0d64a57bd0d`
  (matches the recorded pristine hash).
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

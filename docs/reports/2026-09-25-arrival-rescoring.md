# Position-Verified Arrival Re-Scoring of the 2026-09-24/25 Runs

**Prepared:** 2026-09-25

**Revision history:**

- Initial draft: offline re-score of every VM run recorded before `4f39899` against M1's position estimate and ground truth.

---

## Purpose

Before `4f39899`, M5 logged `robot <id> arrived at base goal (x, y)` whenever
M4 relayed Nav2's own success report (`bt_navigator` "Goal succeeded"), with
no position check. Run `20260925_124609` (ER-2 pilot `E1`) showed this can be
a false success: Nav2 and M5 both declared `robot_2` arrived while M1 placed
it 0.59 m from the goal. `4f39899` added
`swarm_orchestrator/arrival.py::classify_arrival` and `ArrivalGate` to gate
*future* runs on M1's position estimate (`arrival_position_tolerance_m: 0.35`,
`arrival_estimate_max_age_sec: 2.0`). This report re-scores every run recorded
*before* that fix against the same rule, offline, plus an independent
ground-truth cross-check, so the arrival counts in prior findings documents
(`docs/reports/2026-09-25-overnight-findings.md` §V-§W item 1) rest on
position-verified arrivals rather than Nav2's own report.

---

## Method

`scripts/rescore_arrivals.py` walks every `data/logs/vm_runs/<STAMP>`
directory and, for each `robot <id> arrived at base goal (x, y)` line in that
run's M5 log:

1. Finds the M1 scene-log sample (1 Hz) nearest the report's epoch timestamp
   for that robot, regardless of the two runs' different directory layouts
   (`scene/*.jsonl` vs. the older `m5_scene/*.jsonl`). The scene log is
   selected by the `session_id=` M5 prints at startup, not by globbing the
   directory: `scene_log_dir` is a fixed path in `orchestrator.yaml`, not
   per-run, so five of the thirty-one run directories (`L1`-`L5`) carry 6-10
   *stray* scene-log files left over from earlier sessions on the same
   machine, and picking the wrong one would silently score the wrong robot's
   trajectory. Every run in this dataset had exactly one scene file matching
   its own session id.
2. Calls `classify_arrival(reported_goal, estimated_position, tolerance_m,
   estimate_age_sec, max_estimate_age_sec)` **imported directly** from
   `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/arrival.py` (confirmed
   importable without `rclpy`) — the offline verdict is the exact function
   `ArrivalGate` runs online, not a reimplementation. Default
   `--tolerance-m 0.35`, `--max-age-sec 2.0`, matching the shipped config.
   Before writing any scoring logic, every one of the 55 reported arrival
   events in this dataset was confirmed to have an M1 sample within 2 s, so
   `classify_arrival`'s `no_estimate`/`stale_estimate` branches never fire
   here — every verdict below is a clean `within_tolerance` or
   `beyond_tolerance`.
3. Cross-checks against ground truth (10 Hz robot world position) by
   **nearest-position match**, not nearest-time: ground truth's
   `sim_time_sec` has no field shared with the M5 log's epoch timestamps
   anywhere in the recorded data, and the GT stream caps at 3001 rows
   regardless of run length, so a handful of runs (including `E1`, whose
   308.9 s resolution time exceeds the 300.0 s cap) would have no valid GT
   row at the true report instant even if a clock mapping were built. Nearest
   position match instead finds, for the M1 estimate near the report, the
   GT row whose recorded `(x, y)` is closest to it — "ground truth near where
   M1 said the robot was" rather than "ground truth at this wall-clock
   instant". The M1-to-matched-GT-position residual (mean 0.0074 m, max
   0.0107 m across all 55 events) both validates the match landed on the
   right dwell segment and IS the finest-grained form of the M1-vs-GT bias
   this report reports.
4. Also reports each robot's **minimum** GT distance to goal anywhere in the
   run, independent of any report event, for context.
5. Computes "first `starting analysis` → last accepted arrival" per run,
   using the **first M1-accepted** report per robot (chronologically first,
   not first-in-episode-number), and marks a run `n/a` when a robot's arrival
   never passes the M1 check.

`classify_arrival` mirrors the STALE-status override inside
`ArrivalGate.on_nav2_success`, not the bare function; this script calls the
bare function directly (as the task specifies), so a STALE M1 sample is
scored on its raw age, not forced to `stale_estimate`. No sample in this
dataset was STALE at report time, so this made no difference here.

**Validation before trusting the output.** `ER2_PILOT_SUMMARY.txt`
independently states GT positions at every E-batch arrival (e.g. `E1 r1
2.456`, `E1 r2 (-1.9583, -0.2579)` = 0.5999 m, `E6 r1` "loosest... at 0.082
m"). The script reproduces all of them to within ~0.005 m (E1 r1: 0.044 m
here vs. 2.5-2.456=0.044; E1 r2: 0.598 m here vs. the stated 0.5999 m; E6 r1:
0.085 m here vs. the stated 0.082 m — the small residual is the Euclidean y
term the 1-D "loosest" phrasing in that text omitted). This also independently
reproduces the flip that motivated this task (`E1` `robot_2`,
`m1_dist=0.591 m`, `beyond_tolerance`) from raw logs alone, with no
`ArrivalGate` having run against this data. A unit test
(`tests/unit/test_rescore_arrivals.py`) reproduces this exact case (M1
estimate at 0.59 m from goal, tolerance 0.35 m → rejected + flipped) on a
synthetic scene log, plus ten other cases (tolerance acceptance, stale-sample
fallback, no-scene-log fallback using GT's final row, min-vs-at-report GT
distinction, session-id file selection, nested ground-truth paths).

**Post-gate log lines.** `REJECTED_RE` / `ACCEPTED_LATE_RE` parse the
`arrival rejected ...` / `arrival accepted late ...` lines `4f39899` added to
`orchestrator_node.py`. They matched **zero** lines across all 31 runs and
55 events in this dataset, confirmed before writing the scoring logic: the
gate was not wired into any of the runs this script re-scores. The parser
exists so a future re-run over post-fix logs is handled without code changes,
not because it does anything here.

**Known non-bug artifact.** M1 emitted a spurious extra id, `robot_17`
(a marker misdetection), in the scene log for `20260924_205009` only —
absent from ground truth and every M5 log line. `robots_in_run` is built from
ground truth and reported events only, not the scene log, specifically so
this kind of M1 perception glitch cannot make a run look one robot short.

---

## Results

**31 run directories, 55 M5-reported arrival events, 29 runs with at least
one arrival.** `L4` (`20260925_011246`) and `O2` (`20260925_045004`) have zero
`arrived at base goal` lines — both are the already-known 0/2 FAILED runs, not
a script gap.

### Per-event table

One row per `(run, robot)`; `n` reports > 1 marks a robot Nav2 reported
arrived more than once in the same run (`E0` `robot_2` ×2, `P1` `robot_1`
×5 — M5 re-logs the same `command_id="base_mission"` success on each
re-analysis while the *other* robot is still being worked; all duplicate
reports in this dataset agree with the first). M1 dist / GT dist are at the
first report; GT min is the robot's minimum distance to goal anywhere in the
run (frequently much smaller than GT-at-report when the robot's approach
overshoots and settles, e.g. `G3` `robot_2`, `L5` `robot_1` — this is the
10 Hz GT stream showing real overshoot/settle dynamics, not a matching
artifact, confirmed by inspecting those two rows' surrounding GT trajectory).

| STAMP (label) | scenario | backend | order | gate | robot | n | M1 dist (m) | GT dist (m) | GT min (m) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| `20260924_193112` (E0) | head_on_deadlock | openai | unknown | n/a (pre-gate) | robot_1 | 1 | 0.058 | 0.061 | 0.061 | accepted |
| `20260924_193112` (E0) | head_on_deadlock | openai | unknown | n/a (pre-gate) | robot_2 | 2 | 0.038 | 0.046 | 0.046 | accepted (x2 reports) |
| `20260924_195708` (R1) | head_on_asymmetric_w0p2_eopen_o0 | openai | unknown | n/a (pre-gate) | robot_1 | 1 | 0.062 | 0.059 | 0.040 | accepted |
| `20260924_195708` (R1) | head_on_asymmetric_w0p2_eopen_o0 | openai | unknown | n/a (pre-gate) | robot_2 | 1 | 0.058 | 0.066 | 0.065 | accepted |
| `20260924_201328` (R2) | head_on_asymmetric_w0p2_eopen_o0 | openai | unknown | n/a (pre-gate) | robot_2 | 1 | 0.081 | 0.089 | 0.089 | accepted |
| `20260924_203437` (R3) | head_on_asymmetric_wopen_e0p2_o0 | openai | unknown | n/a (pre-gate) | robot_1 | 1 | 0.063 | 0.067 | 0.067 | accepted |
| `20260924_203437` (R3) | head_on_asymmetric_wopen_e0p2_o0 | openai | unknown | n/a (pre-gate) | robot_2 | 1 | 0.025 | 0.035 | 0.035 | accepted |
| `20260924_205009` (R4) | head_on_asymmetric_wopen_e0p2_o0 | openai | unknown | n/a (pre-gate) | robot_1 | 1 | 0.063 | 0.066 | 0.066 | accepted |
| `20260924_205009` (R4) | head_on_asymmetric_wopen_e0p2_o0 | openai | unknown | n/a (pre-gate) | robot_2 | 1 | 0.030 | 0.040 | 0.040 | accepted |
| `20260925_002713` (L1) | head_on_asymmetric_w0p2_eopen_o0 | openai | id_asc | swap | robot_1 | 1 | 0.041 | 0.041 | 0.040 | accepted |
| `20260925_002713` (L1) | head_on_asymmetric_w0p2_eopen_o0 | openai | id_asc | swap | robot_2 | 1 | 0.088 | 0.096 | 0.096 | accepted |
| `20260925_004252` (L2) | head_on_asymmetric_wopen_e0p2_o0 | openai | id_desc | swap | robot_1 | 1 | 0.076 | 0.080 | 0.080 | accepted |
| `20260925_004252` (L2) | head_on_asymmetric_wopen_e0p2_o0 | openai | id_desc | swap | robot_2 | 1 | 0.035 | 0.044 | 0.044 | accepted |
| `20260925_005754` (L3) | head_on_asymmetric_w0p2_eopen_o0 | openai | random | swap | robot_1 | 1 | 0.051 | 0.050 | 0.046 | accepted |
| `20260925_005754` (L3) | head_on_asymmetric_w0p2_eopen_o0 | openai | random | swap | robot_2 | 1 | 0.057 | 0.066 | 0.066 | accepted |
| `20260925_011246` (L4) | -- | -- | -- | -- | -- | 0 | -- | -- | -- | 0/2, no Nav2 arrival either robot |
| `20260925_012747` (L5) | head_on_asymmetric_w0p2_eopen_o0 | openai | id_asc | refuse | robot_1 | 1 | 0.061 | 0.058 | 0.002 | accepted |
| `20260925_021549` (G0) | head_on_deadlock | gemini | id_asc | off | robot_1 | 1 | 0.076 | 0.081 | 0.081 | accepted |
| `20260925_021549` (G0) | head_on_deadlock | gemini | id_asc | off | robot_2 | 1 | 0.028 | 0.038 | 0.038 | accepted |
| `20260925_023122` (G1) | head_on_asymmetric_w0p2_eopen_o0 | gemini | id_asc | swap | robot_1 | 1 | 0.044 | 0.043 | 0.043 | accepted |
| `20260925_023122` (G1) | head_on_asymmetric_w0p2_eopen_o0 | gemini | id_asc | swap | robot_2 | 1 | 0.064 | 0.072 | 0.072 | accepted |
| `20260925_024628` (G2) | head_on_asymmetric_w0p2_eopen_o0 | gemini | id_desc | off | robot_1 | 1 | 0.032 | 0.038 | 0.038 | accepted |
| `20260925_024628` (G2) | head_on_asymmetric_w0p2_eopen_o0 | gemini | id_desc | off | robot_2 | 1 | 0.053 | 0.063 | 0.063 | accepted |
| `20260925_030129` (G3) | head_on_asymmetric_wopen_e0p2_o0 | gemini | id_desc | off | robot_1 | 1 | 0.064 | 0.069 | 0.069 | accepted |
| `20260925_030129` (G3) | head_on_asymmetric_wopen_e0p2_o0 | gemini | id_desc | off | robot_2 | 1 | 0.134 | 0.135 | 0.003 | accepted |
| `20260925_035042` (D1) | head_on_asymmetric_w0p2_eopen_o0 | gemini | id_asc | off | robot_1 | 1 | 0.063 | 0.067 | 0.041 | accepted |
| `20260925_035042` (D1) | head_on_asymmetric_w0p2_eopen_o0 | gemini | id_asc | off | robot_2 | 1 | 0.078 | 0.088 | 0.088 | accepted |
| `20260925_040539` (D2) | head_on_asymmetric_w0p2_eopen_o0 | gemini | id_asc | off | robot_1 | 1 | 0.062 | 0.067 | 0.067 | accepted |
| `20260925_040539` (D2) | head_on_asymmetric_w0p2_eopen_o0 | gemini | id_asc | off | robot_2 | 1 | 0.064 | 0.071 | 0.070 | accepted |
| `20260925_042022` (D3) | head_on_asymmetric_w0p2_eopen_o0 | gemini | id_asc | off | robot_1 | 1 | 0.034 | 0.040 | 0.040 | accepted |
| `20260925_043512` (O1) | head_on_asymmetric_w0p2_eopen_o0 | openai | id_asc | off | robot_1 | 1 | 0.075 | 0.083 | 0.083 | accepted |
| `20260925_043512` (O1) | head_on_asymmetric_w0p2_eopen_o0 | openai | id_asc | off | robot_2 | 1 | 0.082 | 0.090 | 0.090 | accepted |
| `20260925_045004` (O2) | -- | -- | -- | -- | -- | 0 | -- | -- | -- | 0/2, no Nav2 arrival either robot |
| `20260925_063520` (P1) | head_on_asymmetric_w0p2_eopen_o0 | openai | random | swap | robot_1 | 5 | 0.039 | 0.044 | 0.043 | accepted (x5 reports) |
| `20260925_065143` (P2) | head_on_asymmetric_w0p2_eopen_o0 | openai | random | swap | robot_1 | 1 | 0.044 | 0.047 | 0.047 | accepted |
| `20260925_065143` (P2) | head_on_asymmetric_w0p2_eopen_o0 | openai | random | swap | robot_2 | 1 | 0.083 | 0.091 | 0.090 | accepted |
| `20260925_070637` (P3) | head_on_asymmetric_w0p2_eopen_o0 | openai | random | swap | robot_1 | 1 | 0.038 | 0.042 | 0.042 | accepted |
| `20260925_070637` (P3) | head_on_asymmetric_w0p2_eopen_o0 | openai | random | swap | robot_2 | 1 | 0.082 | 0.092 | 0.092 | accepted |
| `20260925_072130` (P4) | head_on_asymmetric_wopen_e0p2_o0 | openai | random | swap | robot_1 | 1 | 0.077 | 0.082 | 0.082 | accepted |
| `20260925_072130` (P4) | head_on_asymmetric_wopen_e0p2_o0 | openai | random | swap | robot_2 | 1 | 0.029 | 0.038 | 0.038 | accepted |
| `20260925_073621` (P5) | head_on_asymmetric_wopen_e0p2_o0 | openai | random | swap | robot_1 | 1 | 0.067 | 0.069 | 0.069 | accepted |
| `20260925_073621` (P5) | head_on_asymmetric_wopen_e0p2_o0 | openai | random | swap | robot_2 | 1 | 0.034 | 0.044 | 0.044 | accepted |
| `20260925_075116` (P6) | head_on_asymmetric_wopen_e0p2_o0 | openai | random | swap | robot_2 | 1 | 0.030 | 0.040 | 0.040 | accepted |
| `20260925_124609` (E1) | head_on_asymmetric_w0p2_eopen_o0 | gemini | random | swap | robot_1 | 1 | 0.038 | 0.044 | 0.044 | accepted |
| `20260925_124609` (E1) | head_on_asymmetric_w0p2_eopen_o0 | gemini | random | swap | robot_2 | 1 | 0.591 | 0.598 | 0.598 | **FLIPPED: rejected** |
| `20260925_130115` (E2) | head_on_asymmetric_w0p2_eopen_o0 | gemini | random | swap | robot_1 | 1 | 0.044 | 0.049 | 0.049 | accepted |
| `20260925_130115` (E2) | head_on_asymmetric_w0p2_eopen_o0 | gemini | random | swap | robot_2 | 1 | 0.070 | 0.079 | 0.079 | accepted |
| `20260925_132335` (E3) | head_on_asymmetric_w0p2_eopen_o0 | gemini | random | swap | robot_1 | 1 | 0.043 | 0.050 | 0.050 | accepted |
| `20260925_133841` (E4) | head_on_asymmetric_wopen_e0p2_o0 | gemini | random | swap | robot_2 | 1 | 0.032 | 0.042 | 0.042 | accepted |
| `20260925_135334` (E5) | head_on_asymmetric_wopen_e0p2_o0 | gemini | random | swap | robot_2 | 1 | 0.033 | 0.044 | 0.044 | accepted |
| `20260925_140824` (E6) | head_on_asymmetric_wopen_e0p2_o0 | gemini | random | swap | robot_1 | 1 | 0.080 | 0.085 | 0.085 | accepted |
| `20260925_140824` (E6) | head_on_asymmetric_wopen_e0p2_o0 | gemini | random | swap | robot_2 | 1 | 0.033 | 0.043 | 0.043 | accepted |

`order`/`gate`/`backend`/`scenario` are recovered from `orchestrator.yaml.used`
where present, else from launcher-style logs; `R1`-`R4` and `E0` predate the
`prompt_robot_order` feature entirely (`order=unknown` is correct, not a gap).
The full event-level data, including every field above plus estimate age,
estimate status, and the position-match residual, is in
`data/logs/vm_runs/ARRIVALS_RESCORED.csv` (git-ignored, regenerate with
`python scripts/rescore_arrivals.py`).

### Every arrival that flips

**Exactly one, across all 55 events and 31 runs:**

| run | robot | M1 dist at report | GT dist at report | tolerance |
|---|---|---|---|---|
| `20260925_124609` (E1, ER-2 pilot) | robot_2 | 0.591 m | 0.598 m | 0.35 m |

M1 and ground truth agree to within 0.007 m that this arrival was real — the
false success is entirely a Nav2/M4 reporting bug (`bt_navigator` "Goal
succeeded" while the robot was still 0.6 m short), not an M1 perception
error. No other run in this dataset has an M1-vs-GT disagreement anywhere
near the 0.35 m tolerance boundary (next closest: `G3` `robot_2` at 0.134 m,
well inside tolerance).

### Corrected episode-outcome counts

"Legacy" = both robots reported `arrived at base goal` at least once (the
pre-fix measure these findings documents originally reported). "M1-verified"
/ "GT-verified" = both robots have at least one report accepted by
`classify_arrival` / within tolerance by ground truth.

| batch | legacy (before) | M1-verified (after) | GT-verified |
|---|---|---|---|
| gpt-4o Arm A pilot (P1-P6) | 4/6 | 4/6 | 4/6 |
| ER-2 pilot (E1-E6) | 3/6 | **2/6** | **2/6** |
| R1-R4 | 3/4 | 3/4 | 3/4 |
| L1-L5 | 3/5 | 3/5 | 3/5 |
| G0-G3 | 4/4 | 4/4 | 4/4 |
| D1-D3 | 2/3 | 2/3 | 2/3 |
| O1-O2 | 1/2 | 1/2 | 1/2 |
| E0 | 1/1 | 1/1 | 1/1 |

Only the ER-2 pilot's count changes, and it changes exactly as
`docs/reports/2026-09-25-overnight-findings.md` Rev 6 already anticipated by
hand for `E1`: 3/6 → 2/6 (`E1`, `E3`, `E4`, `E5` now correctly read as
misses; `E2`, `E6` remain the two true both-arrived runs). Every other batch
in this dataset — 25 runs, 53 of the 55 scored events — had no reported
arrival within 2 s of an M1 estimate that disagreed with Nav2's success
report. The Nav2-false-success failure mode observed once here does not
appear to be systematic across backends or scenario variants in this
dataset; it was caught once, in one run, by one robot stalling just past a
box edge off the corridor axis rather than at the goal.

### M1-vs-GT bias at arrival

Over all 55 scored events, `m1_dist_m - gt_dist_m`:

- mean: **-0.0062 m** (M1 reads, on average, 6 mm *closer* to goal than
  ground truth — well within ArUco/homography noise, not a directional bias
  worth correcting)
- range: -0.0106 m to +0.0038 m
- position-match residual (M1 estimate to matched GT row): mean 0.0074 m,
  max 0.0107 m

M1 tracks ground truth to within about a centimetre at arrival in every case
in this dataset, including the flipped `E1` event (bias -0.007 m there) —
confirming again that the false success was Nav2/M4 trusting its own
"Goal succeeded" report, not M1 misjudging the robot's position.

### What could not be scored

Nothing was skipped for lack of data. `L4` and `O2` scored zero arrival
events because neither run had any `arrived at base goal` line to begin
with (both already-known 0/2 FAILED runs) — this is the correct output, not
a fallback. No run in this dataset lacked a scene log or a ground-truth file;
the "no scene log → fall back to ground truth" and "no M1 estimate → fall
back to GT's final row" code paths exist for robustness against future data
and are exercised by unit tests, not by anything in this dataset.

---

## Limitations

- `order`/`backend`/`scenario` recovery for `R1`-`R4` and `E0` is
  best-effort text-matching against launcher logs, not a structured config
  capture (those runs predate `orchestrator.yaml.used` being archived); the
  scored distances and verdicts do not depend on it.
- Ground-truth-at-report is a nearest-*position* match, not nearest-*time*;
  it is validated against the ER-2 pilot's independently-stated numbers
  (method section) but is not a literal "ground truth at this wall-clock
  instant" value the way the M1 comparison is. For a robot that revisits a
  position at two different times within one run this could mismatch; no
  case in this dataset showed evidence of that (all 55 residuals are small
  and physically continuous with the M1 estimate they were matched against).
- `GT min dist` is a minimum over the *entire* run, including any part before
  the reported arrival; two rows (`G3` `robot_2`, `L5` `robot_1`) show a
  GT min far below GT-at-report, reflecting a real earlier close approach,
  not the arrival itself.

---

## Reproducing

```bash
source .venv/bin/activate
python scripts/rescore_arrivals.py \
  --runs-dir data/logs/vm_runs \
  --tolerance-m 0.35 \
  --max-age-sec 2.0 \
  --out data/logs/vm_runs/ARRIVALS_RESCORED.csv
```

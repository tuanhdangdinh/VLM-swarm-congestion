# T1 Tuning Basket — Final Threshold Values Before `prereg-v1`

**Prepared:** 2026-09-29

**Revision history:**

- Initial draft: the evidence and decision for the four thresholds in amendments item 14. The analysis covers the post-flip corpus plus one T1 `head_on_deadlock` confirmation run with a full-rate M1 recorder.

---

## Overview

### Scope

- The four thresholds in amendments item 14 are covered here. Each is frozen at `prereg-v1`.
  - M1 `stopped_threshold_mps` / `slow_threshold_mps`.
  - The head_on FCFS conflict-zone radius.
  - Arm B `stopped_speed_mps`.
  - The M4 `max_linear_velocity_mps` speed rule.
- The decision rule comes from the item-14 brief. A value changes only when the data separates it cleanly, with a disclosed percentile gap. Otherwise the current value stays and the reason is recorded.

### Summary of Decisions

| Threshold | Before | After | Basis |
|---|---|---|---|
| M1 `stopped_threshold_mps` | 0.01 | **0.01 (kept)** | No clean separator. Sustained sub-5 cm/s creep overlaps the parked-jitter tail. 0.03 is the named rejected option, with its flicker costs quantified |
| M1 `slow_threshold_mps` | 0.05 | **0.05 (kept)** | It sits in the empty band between parked max (0.055) and the 0.1 m/s maneuver legs (p1 0.084) |
| Head_on FCFS zone radius | `r_conflict_m` 1.5 | **new `fcfs_zone_radius_m` 1.0** | Spawn-phase censoring falls from 9/17 to 0/17. The classification rule is unchanged |
| Arm B `stopped_speed_mps` | 0.05 | **0.05 (kept)** | Clean gap: at-snapshot stall max 0.038, lowest motion 0.079 |
| M4 `max_linear_velocity_mps` | 0.2 | **0.2 (kept)** | Full-rate T1 transit max 0.1803 (p99 0.169, p99.9 0.178), 0 rows above 0.19. The margin is 0.020 above observed legitimate motion and 0.020 below the 0.22 mechanical max |

Commits: `caaf95f` (FCFS field, `config/rag.yaml`, tests), plus this report, the implementation-notes entry and the spec Rev 9.2 line. Every other value is unchanged in config. The T1 confirmation run (`T1B1`) contradicts none of the corpus-based decisions.

---

## Evidence Base

### Corpus and Provenance

- **Post-flip corpus.** 25 runs recorded after the sim-time camera flip (`a1aa81d`, merged at `97634be`).
  - The runs live under `data/logs/vm_runs/{simtime_shadow_val,t0_t3c_verify,calibration,funded_battery1,t2b_smoke}/`.
  - Pre-flip runs are excluded because their speeds are on a different basis (amendments A4 note).
- **Scenarios in the corpus.**
  - T2a `head_on_asymmetric_w0p2_eopen_bshort_o0` west: 9 runs (SV-S1/S2, CO1–3, CE1/CE2b/CE3, FB-A1 mock).
  - T2b `t2b_flow_ordering`: 6 runs.
  - T3a `blocked_path_*`: 4 runs.
  - T3b `obstacle_in_candidate`: 2 runs.
  - T3c `dynamic_anomaly{,_v2}`: 3 runs.
  - T0 `normal_flow`: 1 run.
  - The discarded run `funded_battery1/_discarded_by_condition/20260928_155012` is excluded.
- **T1 note.** None of the corpus is literally T1. It supplies the generic speed distributions: every tier uses the same robots, Nav2 caps and M1. The T1 confirmation run below then checks those values on `head_on_deadlock`.
- **Joins.**
  - M1 scene-log rows are joined to ground truth at M1 stamp − 0.45 s, the constant lag from findings Rev 14 §AQ.
  - Only freshly detected rows are used, meaning robot stamp equals scene stamp.
- **Sampling.** The M5 scene log samples M1 at about 1 row per wall-second, which is about 0.4 sim-s. The confirmation run adds a full-rate recording.
- **Regimes.** Each row gets one ground-truth regime:
  - **rest:** GT speed below 0.005 m/s for the preceding 1.5 s.
  - **maneuver:** GT between 0.08 and 0.11 m/s for 1.0 s. These are the 0.1 m/s raw-`cmd_vel` backup/escort legs and Nav2 slow approach.
  - **transit:** GT above 0.12 m/s for 0.5 s. This is Nav2 cruise at the 0.18 cap.
  - **creep:** GT between 0.003 and 0.05 m/s for 1.5 s. This is sustained slow motion.
  - **other:** acceleration and deceleration transients.
- Analysis scripts are in the session scratchpad and are not committed. Tables are reproduced here.
- **T1 confirmation run.** Details are in its own section below.
  - Run: `T1B1`, stamp `20260929_000054`, raw record in `data/logs/vm_runs/t1_basket/` (git-ignored).
  - It adds a passive full-rate recorder of `/perception/scene_state`: 8,738 scenes over 5.4–300.2 sim-s at a 0.034 s mean spacing, i.e. every camera frame.
  - Its tables use the same regimes. One M1 glitch window is excluded from them and reported separately under Limitations.

### M1 Speed by Regime (Post-Flip Corpus, Scene-Log Rows)

| Regime | Scope | n | min | p1 | p50 | p95 | p99 | p99.9 | max |
|---|---|---|---|---|---|---|---|---|---|
| rest | all tiers | 26918 | 0 | 0 | 0 | 0.0149 | 0.0235 | 0.0349 | 0.0549 |
| rest | T2a head-on | 8778 | 0 | 0 | 0.0007 | 0.0162 | 0.0231 | 0.0305 | 0.0364 |
| creep | all tiers | 42 | 0.0049 | 0.0074 | 0.0204 | 0.0422 | 0.0473 | 0.0501 | 0.0504 |
| maneuver | all tiers | 2233 | 0.0787 | 0.0838 | 0.0935 | 0.1018 | 0.1062 | 0.1132 | 0.859 (1 spike) |
| transit | all tiers | 2232 | 0.1214 | 0.1342 | 0.1524 | 0.1624 | 0.1684 | 0.1767 | 0.1813 |
| transit | T2a head-on | 806 | 0.1276 | 0.1384 | 0.1529 | 0.1632 | 0.1696 | 0.1742 | 0.1772 |

Two structural facts follow from this table:

- Sustained motion comes in two modes, both at or above about 0.08 m/s: the 0.1 m/s maneuver legs and Nav2 transit.
- Between rest and those modes lives only a thin creep population: 42 of 32,832 rows (0.13%). Its median, 0.020, lies at the parked tail's p98.

---

## Item 1 — M1 `stopped_threshold_mps` / `slow_threshold_mps`

### Evidence

Parked flicker comes from pose jitter on stationary robots. It crosses 0.01, so rest rows read SLOW; it does not cross 0.05. Rest rows versus sustained-creep rows, by candidate stopped threshold (corpus, scene-log rows):

| Stopped threshold | Rest rows labelled SLOW or above | Creep rows labelled STOPPED | Mislabelled rows (rest + creep) | Rest→rest status transitions (logged rows) |
|---|---|---|---|---|
| 0.01 (current) | 11.75% | 2.4% | 3165 | 3470 |
| 0.02 | 1.99% | 47.6% | 555 | 707 |
| 0.025 | 0.78% | 64.3% | 237 | 308 |
| 0.03 | 0.27% | 71.4% | 102 | 108 |
| 0.035 | 0.10% | 85.7% | 63 | 45 |
| 0.04 | 0.03% | 92.9% | 48 | 17 |

At analysis snapshots, the ones that reach prompts, 58 of 568 rest robot-snapshots (10.2%) carried `SLOW` under 0.01. Under 0.03 the count would be 4 (0.7%).

The T1 confirmation run agrees at full rate, with the glitch window excluded. There are 13,665 rest rows and 28 creep rows:

| Stopped threshold | T1 rest rows labelled SLOW or above | T1 creep rows labelled STOPPED | T1 rest→rest transitions (full rate) |
|---|---|---|---|
| 0.01 (current) | 27.2% | 1/28 | 871 |
| 0.02 | 8.4% | 21/28 | 645 |
| 0.025 | 3.3% | 27/28 | 335 |
| 0.03 | 1.0% | 28/28 | 134 |
| 0.04 | 0.02% | 28/28 | 4 |

- On T1, parked jitter is larger than the corpus average: rest p99 0.030, max 0.042. That is the robots parked near the ROI edge at ±2.5.
- The creep there is lower: max 0.026, median 0.016.
- So on T1 no value both clears the rest tail and keeps creep labelled SLOW. Even the rejected 0.03 leaves 1.0% of rest rows SLOW, while every creep row turns STOPPED.

### Decision

- **`stopped_threshold_mps` stays 0.01.**
  - The data cannot separate rest from creep cleanly. The sustained-creep median (0.020) sits at the parked tail's p98. Any value that removes the flicker also labels most genuine 1–5 cm/s creep STOPPED.
  - The item-14 rule says to keep the value in that case.
  - The threshold also feeds the Arm A stimulus: the prompt's status text ("both STOPPED or STALE" is the prompt's deadlock definition) and the annotation box colour. So a change is not a free parameter move; it shifts calibration comparability, the same mechanism as calibration divergence (a).
- **Named rejected option: 0.03.** The coordinator's reading (2026-09-29) is keep 0.01 per the decision rule; the option is recorded here for the tag.
  - Benefit:
    - Rest rows labelled non-STOPPED fall from 11.75% to 0.27% on the corpus and from 27.2% to 1.0% on T1 at full rate.
    - Rest→rest flicker transitions fall 3,470 → 108 on logged corpus rows and 871 → 134 on the T1 full-rate record.
    - SLOW labels on parked robots at analysis snapshots fall 58 → 4 of 568.
    - It roughly restores the pre-flip effective threshold: 0.01 m per wall-second at RTF ~0.38 is about 0.026 m per sim-second.
  - Cost:
    - Genuine creep would read STOPPED: 71% of the 42 corpus creep rows, and 28/28 T1 creep rows.
    - It is an Arm A stimulus change affecting every prompt and annotated frame.
  - Standing cost of keeping 0.01: parked robots reach prompts as `SLOW` at about 10% of snapshots. Every reported Arm A decision should be read with that in mind, and the prompt definition "both STOPPED or STALE" makes it relevant to deadlock framing.
- **`slow_threshold_mps` stays 0.05.**
  - It separates cleanly. Rest max is 0.0549: 2 of 26,918 rows (0.007%) reach 0.05.
  - Sustained motion never reads below 0.0787: the maneuver-regime minimum, with p1 at 0.0838.
  - Transit minimum is 0.1214.
  - 0.05 sits in the empty band (0.055, 0.079), 0.029 below the lowest sustained-motion row.
  - **T1 confirms:** full-rate rest max 0.042, creep max 0.026, maneuver min 0.0818, transit min 0.1312.

---

## Item 3 — Arm B `stopped_speed_mps`

### Evidence

- **At snapshots.** Speeds at the 289 analysis snapshots the shadow actually classified (672 robot-snapshots, STALE excluded):

  | GT regime at snapshot | n | p50 | p99 | max |
  |---|---|---|---|---|
  | rest | 567 | 0.0002 | 0.0259 | 0.0382 |
  | creep (stalled, GT < 0.05) | 16 | 0.0229 | 0.0380 | 0.0383 |
  | transit | 48 | 0.1521 | 0.1623 | 0.1633 |

- **Band between stall and motion.** At snapshots, no stalled robot reads above 0.0383, and no non-STALE robot reads between 0.0383 and 0.0603. The rows above 0.05 are robots still moving or decelerating, whose EMA still carries motion: FB-C1 0.060 and 0.106 with GT 0, plus five rows at 0.08–0.12 with GT 0.07–0.14. Classical calls those `none`, which is the correct or the conservative answer.
- **Corpus.** The same gap holds corpus-wide:
  - Rest max is 0.0549. Only 2 rows of 26,918 sit at or above 0.05, and none at a snapshot.
  - Sustained creep max is 0.0504.
  - The maneuver minimum is 0.0787.

### Decision

- **Keep 0.05.** It sits:
  - 0.012 above the highest stalled robot at any snapshot (0.0383);
  - 0.029 below the lowest sustained-motion row in the corpus (0.0787);
  - 0.08 below transit p1.
- **Disclosures.**
  - The 2 corpus rest rows up to 0.0549 lie above the threshold.
  - Rule precedence, not the threshold: the classifier trusts `linear_velocity` over `status`. A STALE robot keeps its last EMA speed, and 1 snapshot (CE2b `829aec21`, a STALE robot at 0.051 with GT 0) counts as moving. CE3's 18 STALE snapshots carried a frozen 0.096 from a robot lost mid-maneuver.
- **T1 confirms.**
  - The four T1 analysis snapshots read at most 0.0147 (robot_1 `SLOW` at the head_on snapshot `6271e686`). All were classified stopped as intended: 1× head_on, then 3× blocked_path for robot_2's post-yield stall.
  - At full rate, the T1 rest max is 0.042 and the creep max 0.026. The lowest sustained motion is 0.0818 (maneuver) and transit starts at 0.1312.
  - 0.05 sits 0.008 above the T1 rest max and 0.032 below the T1 maneuver minimum.
  - The one exception is the glitch window (Limitations). For about 1 s after a marker-identity glitch, a parked robot's EMA reads far above 0.05, so a snapshot landing there would call it moving. No snapshot did.

---

## Item 2 — Head_on FCFS Zone Radius

### Evidence

- **What FCFS measures.** FCFS dates a robot's arrival by the first buffered frame that has it inside the zone. For head_on, the zone is centred on the pair midpoint.
- **The two censoring mechanisms.** The corpus has 73 head_on shadow records: T2b 62, T2a 9, T3b 2. Two different mechanisms censor them:
  - **Window truncation.** 56 records are post-yield re-analyses in the T2b alternative arms. Both robots sat in the zone for the whole 60 s window. They stay censored at every radius; this is a window-length property, not a radius one.
  - **Spawn phase.** 17 records have a window that reaches M5's first scene. Here the radius decides. Spawns sit 1.25–1.69 m from the eventual standoff midpoint: T1/T2a/T2b spawn at ±1.5, T3b at ±1.25, and the midpoint drifts 2–19 cm.
- Zone entry for those 17 records, reconstructed from the scene log. The reconstruction reproduces every recorded `censored_arrivals` flag:

| FCFS radius (m) | Records with a censored arrival | One-sided censoring (censored robot wins outright) | Minimum entry − oldest frame (s) |
|---|---|---|---|
| 1.5 (current) | 9/17 | 5 (SV-S2 ×2, CE1, T2b-o42, T2b-a43 `d8a1b635`) | 0.0 |
| 1.4 | 5/17 | 2 | 0.0 |
| 1.3 | 2/17 (both T3b, spawn 1.25) | 0 | 0.0 |
| 1.25 | 0/17 | 0 | 0.43 |
| 1.2 | 0/17 | 0 | 0.83 |
| 1.1 | 0/17 | 0 | 1.26 |
| **1.0** | **0/17** | **0** | **2.06** |
| 0.75 | 0/17 | 0 | 3.73 |

- **Why not trust the per-radius order changes.** The scene log samples about every 0.4 sim-s, while the ring buffer samples every 0.25 s. At 1.5 m the rebuilt passing order differs from the recorded one in 5 of 17 records, even without censoring (commitment ties are sampling-sensitive). Per-radius order-change counts from the scene log are therefore not reported. The confirmation run rebuilds the buffer from full-rate data instead.
- **Ties.** In symmetric head-on geometry both robots enter any radius within `arrival_tie_sec`: 72 of 73 records are ties at every radius. The order is then decided by commitment, then by `robot_id`, as specified. So the radius mostly decides whether the arrival stamp is a real measurement or an artefact. It rarely decides who arrived first.

### Decision

- **New `ClassicalParams.fcfs_zone_radius_m`, set to 1.0 in `config/rag.yaml`** (`caaf95f`).
  - Default `None` means use `r_conflict_m`, i.e. legacy behaviour for any caller without config. No behavioural pin changed. Only the value-subject tests changed: the defaults dict, and the two repo-config tests now expect `fcfs_zone_radius_m=1.0`.
  - The head_on classification's `conflict_radius_m` now carries the FCFS radius, so `find_censored_arrivals` still checks the zone FCFS used.
  - Which robots form a head_on pair is still decided by `r_conflict_m` 1.5. A test pins the verdict as identical apart from the radius field.
- **Why 1.0.**
  - It is T1's physical corridor half-length.
  - It is at least `r_conflict_m` / 2 = 0.75. A validator now enforces that bound, so both members of a head_on pair are always inside the zone at the latest frame.
  - It leaves a 0.25 m spawn margin on T3b (the closest spawns) and 0.32 m on the worst drifted T2a record.
  - The first zone entry comes at least 2.06 s after the oldest frame across the corpus.
- **Not changed.** Window-truncation censoring (56 records) and the `censored_arrivals` flag, which stays as the detector for it.
- **Consequence to report.** Arm B's T2a yielder is now decided by commitment on uncensored stamps. Previously, a censored robot sometimes won outright (5 records). Arm B scores are measured, never read from YAML (amendments A3), so no oracle text changes.
- **T1 confirms.**
  - The run's single head_on shadow record is `6271e686`, with window 12.23–24.63 sim-s. Spawns are 1.517 and 1.495 m from the standoff midpoint.
  - The live record, running at 1.0: `conflict_radius_m` 1.0, `censored_arrivals` [], passing order [robot_1, robot_2], yielder robot_2.
  - Rebuilding the ring buffer from the full-rate record at 0.25 s spacing reproduces that exactly. At 1.0, arrivals are robot_2 15.53 s and robot_1 15.80 s: a tie inside `arrival_tie_sec`, broken by commitment, order [robot_1, robot_2], nothing censored.
  - At the old 1.5, the same buffer censors **both** robots (arrival = oldest frame for both).
  - The head_on verdict is unchanged. The executed mock yield (`robot_2`) completed and both robots arrived within tolerance: robot_1 0.08 m, robot_2 0.06 m.

---

## Item 4 — M4 Speed Rule (`max_linear_velocity_mps`)

### Evidence

- M4 applies the rule per robot to every `/perception/scene_state` message, i.e. to M1's EMA speed at camera rate. The scene log undersamples that stream, so the decision uses the T1 full-rate record:

  | Source | Regime | n | p99 | p99.9 | max | rows > 0.18 | rows > 0.19 | rows > 0.20 |
  |---|---|---|---|---|---|---|---|---|
  | T1 full rate | transit | 1149 | 0.1690 | 0.1784 | 0.1803 | 1 | 0 | 0 |
  | T1 full rate | all non-glitch motion | 2949 | — | — | 0.1803 | 1 | 0 | 0 |
  | Corpus scene log | transit | 2232 | 0.1684 | 0.1767 | 0.1813 | 1 | 0 | 0 |

- **Legitimate motion.** Across both sources it never exceeds 0.1813 m/s: Nav2's 0.18 cap plus less than 0.002 of EMA overshoot.
- **Runaway band.** The robot's mechanical maximum is 0.22 m/s (`nav2_params.yaml` comment). A robot above the Nav2 cap is outside planner control.
- **Why the log count proves nothing.** `speed_limit_violation` log counts are not evidence either way. M4 keeps a robot's first latch reason (`setdefault`), and clearing robots are exempt from the speed rule. So both corpus glitches below went unlogged.

### Decision

- **Keep 0.2.** It sits 0.020 above the highest legitimate reading (0.1803 full rate, 0.1813 corpus) and 0.020 below the 0.22 mechanical maximum. So it fires only on motion the planner did not command.
- The coordinator's escalation condition, transit above about 0.19, is not met: 0 of 1,149 full-rate transit rows exceed 0.19.

---

## Limitations

- **M1 glitches defeat any magnitude speed rule.**
  - **T2b-S1, 30.77 s:** `robot_2` read 0.859 m/s while GT was 0.087. It sits on the scene log, and the rule was masked by a concurrent min-distance latch.
  - **T1B1, 46.5 s, full rate:** `robot_2`, parked at x = 1.805, was reported for one frame at x = −0.160, which is `robot_1`'s position: a marker-identity swap.
  - The EMA then read 2.96 and 5.47 m/s and took about 0.7 s to decay below 0.2. There are 22 rest rows above 0.2, with GT 0.0003.
  - `robot_2` was yield-exempt at the time, so M4 did not act.
  - With a non-exempt robot, a single such frame would trip the speed rule, and at any threshold the glitch can't be told from a runaway.
  - A glitch detector (for example a pose-jump gate in M1) is out of scope for this basket. The limitation is recorded for the safety reporting.
- **Timestamps.**
  - The T1 full-rate record carries 64 repeated scene stamps (identical, never backwards).
  - The camera stamps are sim-time, and the repeated frames yield `dt ≤ 0`, which M1 already treats as zero velocity.
  - This was not investigated further.
- **Scope of the evidence.**
  - Items 1, 3 and 4 rest on the generic post-flip distributions, mostly T2a/T2b/T3, plus one T1 run.
  - Item 2 rests on 17 spawn-phase records plus the T1 record.
  - The tuning-parity rule's "T1 only" clause is met by the confirmation check on T1. The corpus supplies the distributions, with provenance disclosed per table.
- **`intersection_bottleneck`.** The other T1 scenario was not exercised. `shadow_classical_zones` is empty in `orchestrator.yaml`, so Arm B cannot classify `intersection` there until a zone is declared. Intersection FCFS uses the mapped zone radius, not `fcfs_zone_radius_m`.

---

## Verification

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider --continue-on-collection-errors
```

| Check | Expected | Actual |
|---|---|---|
| Full suite vs baseline | Same failing set, more passes | 63 failed / 2335 passed / 14 skipped / 3 errors vs 63 / 2327 / 14 / 3 before; failing and erroring ID sets identical (pass) |
| Two-robot classification unchanged | head_on verdict identical apart from radius | pinned by `test_classify_head_on_verdict_unchanged_by_fcfs_zone_radius` (pass) |
| FCFS radius validator | rejects < `r_conflict_m` / 2 | `test_fcfs_zone_radius_rejects_below_half_r_conflict` (pass) |
| VM deploy `6d66a0d..caaf95f` | tree and install match | 609/609 tree md5, 82/82 installed, `rag.yaml` host == container `e18c723c…` (pass) |
| T1B1 shadow at 1.0 | no censoring, rebuilt == live | `censored_arrivals` [], rebuilt order == live order (pass) |
| T1B1 full-rate transit | ≤ ~0.19 | max 0.1803, 0 rows > 0.19 (pass) |
| T1B1 outcome | both arrive | robot_1 0.08 m, robot_2 0.06 m, within tolerance (pass) |

---

## Decision

Item 14 is discharged pending coordinator review:

- `fcfs_zone_radius_m` 1.0 is added (`caaf95f`).
- `stopped_threshold_mps` 0.01, `slow_threshold_mps` 0.05, Arm B `stopped_speed_mps` 0.05 and M4 `max_linear_velocity_mps` 0.2 are kept.
- All values freeze at `prereg-v1`. The rejected 0.03 option for `stopped_threshold_mps` is the one item the user sees at the tag.

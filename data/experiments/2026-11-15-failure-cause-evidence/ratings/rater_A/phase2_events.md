# Rater A: Phase 2 Events Coding

Rater A, 2026-11-15. Each record applies rubric 7.5 step by step and stops at the first step that fires. Fixed readings (R1-R14) and ambiguities met while coding (A1-A10) are in `ambiguities.md`. Alternatives are tagged `ALT[...]` in the notes. The machine-readable form is `phase2_events.json`.

## Counts

- Sheets: 33.
- Unit records: 58. Of these, 55 are failure units and 3 are parked-finished lone stalls, listed separately with no primary.
- Episode records: 33.
- The distributions below count failure units only. EPISODE and NOT_FU records are excluded, except in the episode table.

### Primary code per failure unit

| Primary | n |
|---|---|
| `G4` | 14 |
| `U:no_m4_clock_anchor` | 10 |
| `X3` | 6 |
| `U:T1_fidelity` | 5 |
| `V1` | 4 |
| `G2` | 3 |
| `G5` | 3 |
| `X1` | 3 |
| `V4` | 3 |
| `X2` | 2 |
| `X5` | 1 |
| `G6` | 1 |

### Rule step that fired (failure units)

| Step | n |
|---|---|
| `4` | 40 |
| `7 (first deviation undetermined: no m4 clock anchor)` | 10 |
| `7 (entered from step 3: T1(t0) U:T1_fidelity)` | 5 |

### Episode primary (failure unit with the earliest t0)

| Episode primary | n |
|---|---|
| `G4` | 9 |
| `U:no_m4_clock_anchor` | 5 |
| `U:T1_fidelity` | 4 |
| `X3` | 4 |
| `G2` | 3 |
| `X1` | 2 |
| `X5` | 1 |
| `X2` | 1 |
| `V1` | 1 |
| `G6` | 1 |
| `G5` | 1 |
| `V4` | 1 |

### Contributing codes (failure units; counted separately from primaries, never summed)

| Contributing | n |
|---|---|
| `X3` | 32 |
| `G1` | 27 |
| `G2` | 21 |
| `V3` | 17 |
| `G6` | 12 |
| `X1` | 11 |
| `X2` | 10 |
| `N0` | 10 |
| `X4` | 9 |
| `V1` | 8 |
| `X6` | 8 |
| `G5` | 5 |
| `EG2` | 5 |
| `V4j` | 5 |
| `V4` | 5 |
| `G4` | 4 |
| `X5` | 3 |
| `V6` | 2 |

Strata (prereg tranche, pilots, November takes) cannot be told apart from the blinded sheets. Stop-flag episodes carry X6 and are marked in their notes.

## Per Unit

| Sheet | Unit | Primary | Step | Contributing | Confidence |
|---|---|---|---|---|---|
| EV-072a17 | FU1 | `G4` | 4 | X3, V3, G1 | medium |
| EV-072a17 | FU2 | `X2` | 4 | X3 | medium |
| EV-072a17 | EPISODE | `G4` | episode | G1, V3, X2, X3 | medium |
| EV-0bdad6 | FU1 | `G4` | 4 | G6, X3, G1, G2, V3, X4 | medium |
| EV-0bdad6 | FU2 | `U:T1_fidelity` | 7 (entered from step 3: T1(t0) U:T1_fidelity) | V1, X2, X4, X5 | medium |
| EV-0bdad6 | EPISODE | `G4` | episode | G1, G2, G6, U:T1_fidelity, V1, V3, X2, X3, X4, X5 | medium |
| EV-133a4a | FU1 | `U:no_m4_clock_anchor` | 7 (first deviation undetermined: no m4 clock anchor) | N0 | medium |
| EV-133a4a | FU2 | `U:no_m4_clock_anchor` | 7 (first deviation undetermined: no m4 clock anchor) | N0 | medium |
| EV-133a4a | FU3 | `NOT_FU:parked_finished` | none | - | high |
| EV-133a4a | EPISODE | `U:no_m4_clock_anchor` | episode | N0 | medium |
| EV-295a3e | FU1 | `G4` | 4 | X3, X1, G5, EG2, V3, G1, X5, X2, G2 | medium |
| EV-295a3e | EPISODE | `G4` | episode | EG2, G1, G2, G5, V3, X1, X2, X3, X5 | medium |
| EV-298037 | FU1 | `U:T1_fidelity` | 7 (entered from step 3: T1(t0) U:T1_fidelity) | X4, V3, G4, X3, G1, G2 | medium |
| EV-298037 | FU2 | `X3` | 4 | V1 | medium |
| EV-298037 | EPISODE | `U:T1_fidelity` | episode | G1, G2, G4, V1, V3, X3, X4 | medium |
| EV-2c719b | FU1 | `G2` | 4 | G1, V3 | medium |
| EV-2c719b | FU2 | `G5` | 4 | EG2, X3, G2, V1, X4 | high |
| EV-2c719b | EPISODE | `G2` | episode | EG2, G1, G5, V1, V3, X3, X4 | medium |
| EV-3233e2 | FU1 | `U:no_m4_clock_anchor` | 7 (first deviation undetermined: no m4 clock anchor) | N0 | medium |
| EV-3233e2 | FU2 | `U:no_m4_clock_anchor` | 7 (first deviation undetermined: no m4 clock anchor) | N0 | medium |
| EV-3233e2 | EPISODE | `U:no_m4_clock_anchor` | episode | N0 | medium |
| EV-344706 | FU1 | `G4` | 4 | X1, V3, G1, X6 | medium |
| EV-344706 | EPISODE | `G4` | episode | G1, V3, X1, X6 | medium |
| EV-359e3d | FU1 | `X5` | 4 | X3, X1, G6, V3, G1 | medium |
| EV-359e3d | FU2 | `X1` | 4 | V4j, X3 | medium |
| EV-359e3d | EPISODE | `X5` | episode | G1, G6, V3, V4j, X1, X3 | medium |
| EV-35eb04 | FU1 | `X3` | 4 | G2, G1, V3 | medium |
| EV-35eb04 | FU2 | `NOT_FU:parked_finished` | none | - | high |
| EV-35eb04 | EPISODE | `X3` | episode | G1, G2, V3 | medium |
| EV-37a70e | FU1 | `G4` | 4 | G5, X1, X5, X3, V3, G1, G2 | medium |
| EV-37a70e | FU2 | `V4` | 4 | G6, X3, V1, X4 | high |
| EV-37a70e | EPISODE | `G4` | episode | G1, G2, G5, G6, V1, V3, V4, X1, X3, X4, X5 | medium |
| EV-3e6d9b | FU1 | `U:no_m4_clock_anchor` | 7 (first deviation undetermined: no m4 clock anchor) | N0, X2 | medium |
| EV-3e6d9b | FU2 | `U:no_m4_clock_anchor` | 7 (first deviation undetermined: no m4 clock anchor) | N0 | medium |
| EV-3e6d9b | EPISODE | `U:no_m4_clock_anchor` | episode | N0, X2 | medium |
| EV-41a9d4 | FU1 | `X1` | 4 | V4, G6, X3, G1, G2 | high |
| EV-41a9d4 | FU2 | `V1` | 4 | X3, G2, X4 | medium |
| EV-41a9d4 | EPISODE | `X1` | episode | G1, G2, G6, V1, V4, X3, X4 | high |
| EV-478db7 | FU1 | `X3` | 4 | V3, G1, G6, X6 | medium |
| EV-478db7 | EPISODE | `X3` | episode | G1, G6, V3, X6 | medium |
| EV-52a0c3 | FU1 | `U:T1_fidelity` | 7 (entered from step 3: T1(t0) U:T1_fidelity) | X2, G4, X3, V3, G1 | medium |
| EV-52a0c3 | EPISODE | `U:T1_fidelity` | episode | G1, G4, V3, X2, X3 | medium |
| EV-62b8d0 | FU1 | `G4` | 4 | X1, X3, V4, V4j, G5, EG2, G6, V3, G1 | medium |
| EV-62b8d0 | EPISODE | `G4` | episode | EG2, G1, G5, G6, V3, V4, V4j, X1, X3 | medium |
| EV-69a2ea | FU1 | `U:no_m4_clock_anchor` | 7 (first deviation undetermined: no m4 clock anchor) | N0 | medium |
| EV-69a2ea | FU2 | `U:no_m4_clock_anchor` | 7 (first deviation undetermined: no m4 clock anchor) | N0 | medium |
| EV-69a2ea | EPISODE | `U:no_m4_clock_anchor` | episode | N0 | medium |
| EV-6f1277 | FU1 | `G2` | 4 | G1, X3 | medium |
| EV-6f1277 | FU2 | `V1` | 4 | - | high |
| EV-6f1277 | EPISODE | `G2` | episode | G1, V1, X3 | medium |
| EV-7bda3f | FU1 | `X3` | 4 | G2, V3, G1, V4, V4j, G4, G6, X6 | medium |
| EV-7bda3f | FU2 | `G4` | 4 | X3, V1, X6 | medium |
| EV-7bda3f | EPISODE | `X3` | episode | G1, G2, G4, G6, V1, V3, V4, V4j, X6 | medium |
| EV-7bf1e2 | FU1 | `G2` | 4 | X3 | high |
| EV-7bf1e2 | FU2 | `G4` | 4 | X3, G2, G1 | medium |
| EV-7bf1e2 | EPISODE | `G2` | episode | G1, G4, X3 | medium |
| EV-7e1fa5 | FU1 | `X2` | 4 | G2, G1, X3 | medium |
| EV-7e1fa5 | FU2 | `V1` | 4 | - | high |
| EV-7e1fa5 | FU3 | `NOT_FU:parked_finished` | none | - | high |
| EV-7e1fa5 | EPISODE | `X2` | episode | G1, G2, V1, X3 | medium |
| EV-80fb2a | FU1 | `V1` | 4 | - | high |
| EV-80fb2a | FU2 | `G4` | 4 | G5, X1, EG2, X3, X2, G2, G1 | medium |
| EV-80fb2a | EPISODE | `V1` | episode | EG2, G1, G2, G4, G5, X1, X2, X3 | high |
| EV-830943 | FU1 | `G6` | 4 | X3, G2, G1, V4, X2, X1 | medium |
| EV-830943 | EPISODE | `G6` | episode | G1, G2, V4, X1, X2, X3 | medium |
| EV-a2cfc5 | FU1 | `X3` | 4 | X1, V3, G2, G1, X4 | medium |
| EV-a2cfc5 | EPISODE | `X3` | episode | G1, G2, V3, X1, X4 | medium |
| EV-a6761e | FU1 | `G4` | 4 | G6, X3, G2, G1 | low |
| EV-a6761e | FU2 | `G4` | 4 | G6, X3, V1 | medium |
| EV-a6761e | EPISODE | `G4` | episode | G1, G2, G6, V1, X3 | low |
| EV-b13ac7 | FU1 | `X1` | 4 | X3, G2, G1, X2, V3, G6 | high |
| EV-b13ac7 | EPISODE | `X1` | episode | G1, G2, G6, V3, X2, X3 | high |
| EV-c49058 | FU1 | `U:no_m4_clock_anchor` | 7 (first deviation undetermined: no m4 clock anchor) | N0 | medium |
| EV-c49058 | FU2 | `U:no_m4_clock_anchor` | 7 (first deviation undetermined: no m4 clock anchor) | N0 | medium |
| EV-c49058 | EPISODE | `U:no_m4_clock_anchor` | episode | N0 | medium |
| EV-cb3996 | FU1 | `G5` | 4 | EG2, X3, X1, V3, G2, G1 | high |
| EV-cb3996 | FU2 | `X3` | 4 | X2, G2, G1 | medium |
| EV-cb3996 | EPISODE | `G5` | episode | EG2, G1, G2, V3, X1, X2, X3 | high |
| EV-db0df6 | FU1 | `V4` | 4 | G4, X3, G2, G1 | high |
| EV-db0df6 | FU2 | `V4` | 4 | V4j, G6, X3 | high |
| EV-db0df6 | EPISODE | `V4` | episode | G1, G2, G4, G6, V4j, X3 | high |
| EV-e0f9cf | FU1 | `G4` | 4 | V1, X1, V6, X6 | medium |
| EV-e0f9cf | FU2 | `G4` | 4 | X3, G6, G5, X1, V1, X2, V6, X6 | medium |
| EV-e0f9cf | EPISODE | `G4` | episode | G5, G6, V1, V6, X1, X2, X3, X6 | medium |
| EV-e26384 | FU1 | `U:T1_fidelity` | 7 (entered from step 3: T1(t0) U:T1_fidelity) | X3, G2, G1, X6 | medium |
| EV-e26384 | EPISODE | `U:T1_fidelity` | episode | G1, G2, X3, X6 | medium |
| EV-ef4e73 | FU1 | `U:T1_fidelity` | 7 (entered from step 3: T1(t0) U:T1_fidelity) | X3 | medium |
| EV-ef4e73 | FU2 | `G5` | 4 | X4, X3, G2, X2 | medium |
| EV-ef4e73 | EPISODE | `U:T1_fidelity` | episode | G2, G5, X2, X3, X4 | medium |
| EV-f7ab58 | FU1 | `G4` | 4 | X4, V3, G1, X3, V4, V4j, X6 | medium |
| EV-f7ab58 | EPISODE | `G4` | episode | G1, V3, V4, V4j, X3, X4, X6 | medium |

## Evidence and Notes per Unit

### EV-072a17 FU1: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_2:backup, D1:robot_5:escort, D1:robot_5:wait; D1 dispatched 14.133 < t0 22.937 (within 60 s), chain_start 14.133, step 3 skipped. Walk from 14.133: D1 analysis yield yield_robot=robot_5, C2 False, valid parse (no V4/V6); D1 not matched to FU1 so no T1 at its snapshot (V2/V3 untestable, R3). D1 grounding: verifier edit swap robot_5<->robot_2, G4_role_change_tags ['yield_robot=sweep_regrounded:robot_5->robot_2','yield_robot_grounded_from=robot_5'], dispatched robot_2:yield (dispatch differs from decision's yield_robot) -> G4 at 14.133.
- **Event codes:**
  - 14.133: D1 analysis -> none (V2/V3:U:T1_not_run (unmatched to FU1))
  - 14.133: D1 grounding/dispatch -> G4
  - 96.302: D1:robot_2:backup -> X3 (COMPLETED moved 1.613/1.438; pairs robot_2|robot_5 close+stopped from 105.64 and robot_3|robot_5 from 23.14 to censor; exemption robot_2+robot_5 cleared at 96.306)
  - 51.867: D1:robot_5:escort -> none (T3 not_executed(<50%), terminal None, stalled_clear; no X1 under R7)
  - 100.067: D2 (temporary_wait, matched to FU2, omits robot_2) -> none (V2 untestable for FU1 (no FU1 T1 row at D2))
  - 110.48: D2 waits COMPLETED -> X3
  - 113.567: D3 analysis junction_clear, plan reverse robot_2 -> V3 (named reverser robot_2 refused for retreat room (yield refused: no feasible yielder robot_2 0.15 m ...); T1[D3] pass 52/237 contains R:robot_3, R:robot_5)
  - 113.567: D3 grounding withheld refusal_no_action -> G1 (contract C1-C3 None, T2[D3] True)
- **Notes.** Alt R3 (U when V2/V3 untestable at D1): primary U:T1_not_run. Alt R8 (all X2 inputs count): robot_3 X2 run from 22.94 is after G4, primary unchanged. X2 inputs all safety_stop_cover_fraction 1.0 -> not X2 under R8. ALT[R3]=U:T1_not_run

### EV-072a17 FU2: `X2` (step 4)

- **Evidence.** Gate all True. Step 2 no chain (rubric chain []). Step 3: T2(t0)=True, T1(t0) as written 7/88 non-empty, fidelity episode_gate_pass -> continue. Walk from t0 30.137: Nav2 abort line robot_1 30.181 rel-s '[follow_path] [ActionServer] Aborting handle.' -> X2.
- **Event codes:**
  - 30.181: nav2 abort robot_1 -> X2
  - 100.067: D2 analysis temporary_wait inv robot_1,3,4,5 -> none (T1[D2] pass 7/88, no robot in every motion label -> no V2; no plan, m3_default (not G2))
  - 110.48: D2 waits robot_1/robot_4 COMPLETED -> X3 (pair robot_1|robot_4 close+stopped from 30.34 to censor, non-exempt)
- **Notes.** X2 here rests on the literal Nav2 abort clause; the abort coincides with robot_1's safety-stop start (30.179). If the abort line were not counted, the walk gives X3 at 110.48 (completed wait then pinned pair). X2 input runs have cover fraction 1.0 (not X2 under R8).

### EV-0bdad6 FU1: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_1:backup, D1:robot_4:escort, D1:robot_4:wait, D1:robot_5:wait; D1 dispatched 12.367, t0 69.04 (56.7 s before), chain_start 12.367; step 3 skipped. Walk: D1 analysis yield yield_robot robot_1, C2 False, parse valid; D1 not matched to FU1, no T1 row (V2/V3 untestable). D1 grounding: G4_role_change_tags ['grounding=node_handoff:robot_1->robot_4'] and G6_verbatim_contradicted True (provenance vlm_verbatim, dispatch_matches_plan False) -> G4 and G6 on the same event; G4 taken (lower-numbered G, see ambiguity A2).
- **Event codes:**
  - 12.367: D1 analysis -> none (V2/V3:U:T1_not_run)
  - 12.367: D1 grounding/dispatch -> G4, G6
  - 66.991: D1 backup robot_1 COMPLETED / escort robot_4 COMPLETED -> X3 (pair robot_1|robot_4 close+stopped from 69.24 to censor; exemption robot_1+robot_4 cleared 66.947)
  - 154.6: D3 yield robot_4 withheld (no feasible yielder robot_4 0.00, robot_1 0.00) -> G1, G2 (C2 False, T2[D3] True; G2_m3_default_with_plan True; V3 not met: no Y label in T1[D3] motion)
  - 159.433: D4 (same as D3) -> G1, G2
  - 181.533: D5 yield robot_1 withheld (no declared junction) -> G1, G2 (refusal not for room -> no V3)
  - 235.5: D6 yield robot_1 withheld (no shared lane) -> G1, G2 (handoff tags present but withheld -> not G4 (R5))
  - 239.367: D7 junction_clear, plan reverse robot_4+robot_1, withheld (retreat room) -> V3, G1 (R:robot_5 in T1[D7] motion)
  - 243.367: D8 junction_clear no plan, withheld -> G1
  - 277.967: robot_5 STALE 11.53 s / 10.1 s -> X4
- **Notes.** Alt R3: U:T1_not_run at D1. X2 runs cover fraction 1.0/0.99 -> not X2 (R8); alt R8 does not change primary (runs start 69.04, after D1). D1 fidelity as-written 'differs' (no T1 row at D1 anyway). ALT[R3]=U:T1_not_run

### EV-0bdad6 FU2: `U:T1_fidelity` (step 7 (entered from step 3: T1(t0) U:T1_fidelity))

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (no dispatch to robot_2/robot_3 in [t0-60, t0]; t0 240.94). Step 3: T2(t0) False (start_within_required_clearance robot_2, robot_3), T1(t0) as written 'U:T1_fidelity' (episode gate; 29/88 only under +intents). T1 decides EG1 vs continue -> U:T1_fidelity (R1).
- **Event codes:**
  - 240.94: FU V1 (a33_matched_positive_analyses 0) -> V1
  - 243.367: D8 junction_clear withheld (not matched to FU2) -> none (G1 untestable for FU2 (no FU2 T2 at D8))
  - 249.014: nav2 'Failed to make progress'/abort robot_3, robot_2 -> X2
  - 237.6: robot_3 STALE 330.73 s from 237.6 (starts before t0) -> X4
  - 238.54: gt_contact robot_2|obstacle_2 from 238.54 (no leg) -> X5 (starts 2.4 s before t0)
- **Notes.** Alt R1 (walk step 4 from t0): first event V1 at t0 -> primary V1. Blinding: this unit's t0/contact times match a case named in the methods note (disclosure D3); coded from sheet only. robot_3 contact with obstacle_2 from 114.74 began inside the D2:robot_3:escort leg (min static gap -0.0002, would be G5 for that leg) but that leg is outside FU2's chain/timeline, so not an FU2 event (S1 sensitivity is computed later).

### EV-133a4a FU1: `U:no_m4_clock_anchor` (step 7 (first deviation undetermined: no m4 clock anchor))

- **Evidence.** Layer-2-off coding (R2, rubric 7.6): no decision artifacts, no decisions/legs, m4.log < 2 sim_t= lines. Step 1: t0_snapshot True, m4_log True; decision artifacts not needed (no V/G). Step 2 never fires (nothing dispatched). Step 3: T2(t0) True, so G7 (not applicable by construction) vs continue is the only branch T1 could decide; continue. Step 4 (X only) from t0 14.67: X2 input runs for robot_3, robot_4 start at ~t0 and last to censor, but safety-stop spans are present and unmapped (rel None; wall mapping U:no_m4_clock_anchor), so 'under an active Nav2 goal' cannot be decided (R8); no STALE span >= 10 s; no GT contact (gap <= 0.005) for FU robots; X3 needs a completed command (none).
- **Event codes:**
  - 14.67: X2 input runs (stationary, no M4 leg, traveling) -> U:no_m4_clock_anchor (cover fraction 0.0 is an artefact of unmapped safety-stop spans)
- **Notes.** T1(t0) as written 29/88 non-empty: a Layer-2 action was available (yes); fidelity unverifiable_in_bundle. Alt R8 (every tool X2 input counts): primary X2 (run from ~t0). Alt R2 (treat as Layer-2-on with missing artifacts): U:no_decision_artifacts at step 1.

### EV-133a4a FU2: `U:no_m4_clock_anchor` (step 7 (first deviation undetermined: no m4 clock anchor))

- **Evidence.** Layer-2-off coding (R2, rubric 7.6): no decision artifacts, no decisions/legs, m4.log < 2 sim_t= lines. Step 1: t0_snapshot True, m4_log True; decision artifacts not needed (no V/G). Step 2 never fires (nothing dispatched). Step 3: T2(t0) True, so G7 (not applicable by construction) vs continue is the only branch T1 could decide; continue. Step 4 (X only) from t0 30.37: X2 input runs for robot_1, robot_5 start at ~t0 and last to censor, but safety-stop spans are present and unmapped (rel None; wall mapping U:no_m4_clock_anchor), so 'under an active Nav2 goal' cannot be decided (R8); no STALE span >= 10 s; no GT contact (gap <= 0.005) for FU robots; X3 needs a completed command (none).
- **Event codes:**
  - 30.37: X2 input runs (stationary, no M4 leg, traveling) -> U:no_m4_clock_anchor (cover fraction 0.0 is an artefact of unmapped safety-stop spans)
- **Notes.** T1(t0) as written 2/88 non-empty: a Layer-2 action was available (yes); fidelity unverifiable_in_bundle. Alt R8 (every tool X2 input counts): primary X2 (run from ~t0). Alt R2 (treat as Layer-2-on with missing artifacts): U:no_decision_artifacts at step 1.

### EV-133a4a FU3: `NOT_FU:parked_finished` (step none)

- **Evidence.** lone_stall robot_2 t0 139.37, flag finished_all_or_between_tasks_at_censor; protocol: parked robots that finished their last task are coded as not a failure unit and listed separately.
- **Notes.** Listed separately, excluded from primary counts.

### EV-295a3e FU1: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_2:backup, D1:robot_3:escort and D1 waits; D1 dispatched 13.8, t0 65.07 (51.3 s before); chain_start 13.8; step 3 skipped (T1(t0) U:T1_fidelity therefore not deciding). Walk: D1 analysis yield yield_robot robot_3, C2 False, valid; unmatched to FU1 (no T1 row) -> V2/V3 untestable. D1 grounding: swap robot_3<->robot_2 ('yield re-grounded: robot_3 has no retreat candidate surviving the sweep'), G4_role_change_tags ['yield_robot=sweep_regrounded:robot_3->robot_2',...], dispatched robot_2:yield -> G4 at 13.8.
- **Event codes:**
  - 13.8: D1 analysis -> none (V2/V3:U:T1_not_run)
  - 13.8: D1 grounding -> G4
  - 94.114: D1 backup robot_2 COMPLETED -> X3 (robot_1|robot_3 close+stopped from 65.67 to censor; exemptions cleared 94.116)
  - 100.133: D2 reverse robot_4+robot_5 (matched) -> none (C1 False; V4j not flagged (justification/reasoning do not name robot_4/robot_5 as continuing or passing); T1[D2] pass, no robot in every motion label; vlm_verbatim and dispatch matches)
  - 101.8: D2:robot_5:reverse leg -> G5, X1 (recomputed min static gap -0.0017 m to rack/SW_west (undeclared) at 134.67; FAILED deadline True 135.842)
  - 111.37: gt_contact robot_5|rack/SW_west 111.37-139.47 -> EG2 (inside the G5 leg -> not X5)
  - 114.801: D1:robot_3:escort FAILED 'escort timed out in phase drive' -> X1
  - 136.806: nav2 abort robot_5 -> X2
  - 141.067: D3 junction_clear plan reverse robot_4,robot_2 withheld (retreat room) -> V3, G1 (R:robot_1/R:robot_3/R:robot_5 in T1[D3] motion; T2[D3] True)
  - 145.1: D4 junction_clear (yield robot_3, reverse robot_4/robot_2) withheld -> V3, G1
  - 149.6: D5 junction_clear no plan withheld -> G1
  - 155.67: gt_contact robot_5|obstacle_1 155.67-157.97 (no leg) -> X5
  - 183.267: D6 yield robot_2 -> swapped to robot_5, dispatched -> V3, G4 (named yielder robot_2 refused for room; robot_5 appears first and last in T1[D6] Y labels)
  - 213.3: D6:robot_2:escort -> none (not_executed, terminal None (no X1 under R7))
  - 261.6: D7 junction_clear withheld -> G1, G2
  - 276.19: D8 waits COMPLETED -> X3
  - 279.367: D9 junction_clear yield robot_5 withheld (0.15 m room) -> V3, G1, G2
- **Notes.** Alt R3: U:T1_not_run at D1. X2 inputs all cover fraction 1.0 (not X2 under R8); alt R8 changes nothing (first run 94.17). D1 fidelity as-written 'differs' (no T1 row at D1). ALT[R3]=U:T1_not_run

### EV-298037 FU1: `U:T1_fidelity` (step 7 (entered from step 3: T1(t0) U:T1_fidelity))

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (no dispatch to robot_2/3/5 in [t0-60,t0], t0 19.373). Step 3: T2(t0) True; T1(t0) as written 'U:T1_fidelity' (episode gate as-written false; 96/237 only under +intents gate). T1 decides G7 vs continue -> U:T1_fidelity (R1).
- **Event codes:**
  - 57.733: robot_5 STALE 11.27 s (57.733-69.0), further spans 44.7 s etc. -> X4
  - 75.5: D3 yield robot_2 -> swapped to robot_3 (robot_2 0.58 m retreat room < 0.74 m) -> V3, G4 (T1[D3] pass; robot_3 first and last in Y labels)
  - 105.628: D3:robot_2:wait COMPLETED -> X3 (robot_2|robot_5 close+stopped from 22.57 to censor, not in exempt set)
  - 195.844: D3:robot_3:backup COMPLETED -> X3 (robot_3|robot_5 from 204.57; exemptions cleared 195.854)
  - 199.0: D4 yield robot_5 withheld (no retreat candidate surviving sweep) -> V3, G1, G2
  - 206.667: D5 junction_clear plan reverse robot_5 withheld (retreat room) -> V3, G1
- **Notes.** Alt R1 (walk step 4 from t0): first deviation X4 at 57.733 (robot_5 STALE >= 10 s) -> primary X4. X2 inputs cover fraction >= 0.996 (not X2 under R8); alt R8: X2 at 105.67 (after X4), no change to alt.

### EV-298037 FU2: `X3` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D2:robot_1:backup, D2:robot_4:escort, D2:robot_4:wait; D2 dispatched 22.4, t0 72.673 (50.3 s before); chain_start 22.4; step 3 skipped. Walk: D2 analysis yield robot_1, no plan (C1-C3 None), valid; unmatched (no T1 row, V2/V3 untestable). D2 grounding m3_default, no plan present (not G2), no G4 tags, published. Legs: D2:robot_1:backup COMPLETED 71.655 (moved 1.543/1.485), D2:robot_4:escort COMPLETED 71.695; exemption robot_1+robot_4 cleared 71.71; X3 GT input robot_1|robot_4 close+stopped from 72.97 to censor -> X3 at 71.695 (completed command followed by pinned non-exempt pair).
- **Event codes:**
  - 22.4: D2 analysis/grounding -> none (V2/V3:U:T1_not_run)
  - 71.695: D2 legs COMPLETED then pinned pair -> X3
  - 72.673: FU V1 (a33_matched_positive_analyses 0) -> V1
- **Notes.** D1 (18.267, withheld empty_reroute, G2 flag) precedes the chain start and is not walked. If V1 were placed at the chain start rather than t0 (R9), primary would be V1. Alt R3: U:T1_not_run at D2. ALT[R3]=U:T1_not_run; ALT[X3-at-pin-start]=V1 (A10)

### EV-2c719b FU1: `G2` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) []. Step 3: T2(t0) True, T1(t0) as written 7/237 non-empty, episode_gate_pass -> continue. Walk from t0 12.74: X2 inputs cover fraction 0.989/0.982 (uncovered < 60 s, not X2 under R8); no contact. D2 at 35.4 (matched): junction_clear, plan yield robot_3 + cross robot_1, C1-C3 None; verifier provenance m3_default with plan present (G2_m3_default_with_plan True) -> G2; grounding withheld refusal_no_action 'yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m ...)' with T2[D2] True -> G1. V3 not met: T1[D2] has no Y labels in motion (other FU robot not shown feasible as yielder). Two G codes on one event; G2 taken as more upstream (verifier before grounder, ambiguity A2).
- **Event codes:**
  - 35.4: D2 analysis -> none (T1[D2] pass 10/237; no Y motion -> no V3; no robot in every motion label -> no V2)
  - 35.4: D2 verifier/grounding -> G2, G1
  - 91.6: D7 junction_clear, plan reverse robot_4, withheld (retreat room) -> V3, G1 (R:robot_1/R:robot_3/R:robot_5 in T1[D7] motion; T2[D7] True; named reverser robot_4 is not an FU1 robot (literal reading))
- **Notes.** If within-G ties went by code number, primary would be G1 (A2). Negative analyses D4-D6 carry no robots and are not on the FU timeline.

### EV-2c719b FU2: `G5` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_2:reverse, D1:robot_4:reverse; D1 dispatched 13.233, t0 40.44; chain_start 13.233. Walk: D1 analysis reverse involved robot_2,robot_4, reverse legs robot_2,robot_4 (C1 False), V4j not flagged; unmatched (V2/V3 untestable). Grounding vlm_verbatim, dispatch_matches_plan True, no G1-G4/G6. D1:robot_2:reverse leg start 14.667: recomputed min static gap -0.0015 m to rack/NW_north (undeclared) at 29.64 -> G5.
- **Event codes:**
  - 13.233: D1 analysis/grounding -> none (V2/V3:U:T1_not_run)
  - 14.667: D1:robot_2:reverse -> G5 (COMPLETED 32.294, moved 1.301/1.3)
  - 27.24: gt_contact robot_2|rack/NW_north 27.24-33.94 -> EG2 (within the G5 leg -> not X5)
  - 32.294: D1 reverse legs COMPLETED -> X3 (robot_2|robot_4 close+stopped from 40.94 to censor; exemption cleared 32.297)
  - 39.467: D3 yield robot_4 withheld (no shared lane) -> G2 (not matched: no T1/T2 row, G1 untestable (U:T2_not_run); refusal not for room)
  - 40.44: FU V1 (0 matched) -> V1
  - 42.333: robot_2 STALE 140.77 s from 42.333 -> X4
  - 91.6: D7 junction_clear (robot_4 reverse) withheld -> none (unmatched to FU2: V3/G1 untestable)
- **Notes.** ALT[R3]=U:T1_not_run

### EV-3233e2 FU1: `U:no_m4_clock_anchor` (step 7 (first deviation undetermined: no m4 clock anchor))

- **Evidence.** Layer-2-off coding (R2, rubric 7.6): no decision artifacts, no decisions/legs, m4.log < 2 sim_t= lines. Step 1: t0_snapshot True, m4_log True; decision artifacts not needed (no V/G). Step 2 never fires (nothing dispatched). Step 3: T2(t0) True, so G7 (not applicable by construction) vs continue is the only branch T1 could decide; continue. Step 4 (X only) from t0 11.773: X2 input runs for robot_1, robot_2, robot_5 start at ~t0 and last to censor, but safety-stop spans are present and unmapped (rel None; wall mapping U:no_m4_clock_anchor), so 'under an active Nav2 goal' cannot be decided (R8); no STALE span >= 10 s; no GT contact (gap <= 0.005) for FU robots; X3 needs a completed command (none).
- **Event codes:**
  - 11.773: X2 input runs (stationary, no M4 leg, traveling) -> U:no_m4_clock_anchor (cover fraction 0.0 is an artefact of unmapped safety-stop spans)
- **Notes.** T1(t0) as written 33/237 non-empty: a Layer-2 action was available (yes); fidelity unverifiable_in_bundle. Alt R8 (every tool X2 input counts): primary X2 (run from ~t0). Alt R2 (treat as Layer-2-on with missing artifacts): U:no_decision_artifacts at step 1.

### EV-3233e2 FU2: `U:no_m4_clock_anchor` (step 7 (first deviation undetermined: no m4 clock anchor))

- **Evidence.** Layer-2-off coding (R2, rubric 7.6): no decision artifacts, no decisions/legs, m4.log < 2 sim_t= lines. Step 1: t0_snapshot True, m4_log True; decision artifacts not needed (no V/G). Step 2 never fires (nothing dispatched). Step 3: T2(t0) True, so G7 (not applicable by construction) vs continue is the only branch T1 could decide; continue. Step 4 (X only) from t0 12.073: X2 input runs for robot_3, robot_4 start at ~t0 and last to censor, but safety-stop spans are present and unmapped (rel None; wall mapping U:no_m4_clock_anchor), so 'under an active Nav2 goal' cannot be decided (R8); no STALE span >= 10 s; no GT contact (gap <= 0.005) for FU robots; X3 needs a completed command (none).
- **Event codes:**
  - 12.073: X2 input runs (stationary, no M4 leg, traveling) -> U:no_m4_clock_anchor (cover fraction 0.0 is an artefact of unmapped safety-stop spans)
- **Notes.** T1(t0) as written 33/88 non-empty: a Layer-2 action was available (yes); fidelity unverifiable_in_bundle. Alt R8 (every tool X2 input counts): primary X2 (run from ~t0). Alt R2 (treat as Layer-2-on with missing artifacts): U:no_decision_artifacts at step 1.

### EV-344706 FU1: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D13:robot_1:backup; D13 dispatched 218.167, t0 245.307 (27.1 s before); chain_start 218.167; step 3 skipped. Walk: D13 analysis yield yield_robot robot_4 (involved robot_1,robot_4,robot_3), C2 False, valid; not matched to FU1 (no T1 row) -> V2/V3 untestable. D13 grounding: verifier swap robot_1<->robot_4 ('robot_4 is off the dynamic lane robot_1/robot_3'), G4_role_change_tags ['grounding=node_handoff:robot_1->robot_3','grounding=node_handoff_regrounded:robot_4->robot_1'], dispatched robot_1:yield -> G4.
- **Event codes:**
  - 218.167: D13 analysis -> none (V2/V3:U:T1_not_run)
  - 218.167: D13 grounding/dispatch -> G4
  - 256.036: D13:robot_1:backup FAILED deadline True (moved 1.365/1.308; yield-backup caveat) -> X1
  - None: D13:robot_3:escort -> none (escort_not_admitted; robot_3 not an FU robot)
  - 266.333: D14 junction_clear, plan reverse robot_2,robot_1, withheld (retreat room) -> V3, G1 (R:robot_5 in T1[D14] motion (pass, 74/237); T2[D14] True)
  - 269.007: stop-rule censor -> X6
- **Notes.** Stop-flag episode (tabulate separately). Events before 218.167 (D12 legs, nav2 186.226) are before the walk start. No completed command to an FU robot after the chain start, so no X3. Alt R3: U:T1_not_run at D13. ALT[R3]=U:T1_not_run

### EV-359e3d FU1: `X5` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (D1 dispatched 14.0, after t0 12.27). Step 3: T2(t0) True, T1(t0) 120/237 non-empty, episode_gate_pass -> continue. Walk from 12.27: D1 at 14.0 (matched): yield robot_1, involved robot_1,robot_4, C2 False; T1[D1] pass, no robot in every motion label (no V2); vlm_verbatim, dispatch matches, no G tags; D1:robot_1:backup min static gap 0.0871 (no G5). gt_contact robot_5|box:obstacle_1 26.47-28.77 min gap 0.0032 m, robot_5 has no leg then -> X5 at 26.47 (first deviation; X2 inputs cover >= 0.997, not X2).
- **Event codes:**
  - 14.0: D1 analysis/grounding -> none
  - 26.47: gt_contact robot_5|obstacle_1 -> X5
  - 70.695: D1:robot_4:wait COMPLETED -> X3 (robot_3|robot_4 close+stopped from 20.57 to censor, non-exempt)
  - 70.695: D1:robot_1:backup FAILED deadline (moved 1.598/1.401; yield-backup caveat) -> X1
  - 87.333: D3 reroute robot_3 lead (C3 False), vlm_verbatim contradicted -> G6
  - 105.83: D3 waits COMPLETED -> X3
  - 110.892: D3:robot_3:reroute FAILED -> X1
  - 111.833: D4 junction_clear (reverse robot_4, yield robot_5) withheld (retreat room) -> V3, G1 (R:robot_1/R:robot_3/R:robot_5 in T1[D4]; T2[D4] True)
- **Notes.** X5 rests on a 2.3 s contact with min gap 0.0032 m (threshold 0.005). ALT[R8]=X2 (run from 20.47)

### EV-359e3d FU2: `X1` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_1:backup (robot_1 executing at t0 50.67); chain_start 14.0; step 3 skipped. Walk: D1 analysis yield robot_1 (not matched to FU2: V2/V3 untestable), C2 False; grounding vlm_verbatim, matches, no G tags; backup min static gap 0.0871 (no G5). D1:robot_1:backup m4_terminal FAILED, ended_by_deadline True at 70.695 -> X1.
- **Event codes:**
  - 14.0: D1 analysis/grounding -> none (V2/V3:U:T1_not_run for FU2)
  - 70.695: D1:robot_1:backup FAILED deadline -> X1 (moved 1.598 of 1.401 m (fraction 1.141): methods-note caveat, failure may be pull-off/hold)
  - 73.7: D2 reverse robot_1+robot_2 (C1 False), verifier substituted both reverse legs to wait ('both outside the corridor on the same side'), dispatched waits -> V4j (No G4: G4_role_change_tags and robots_dropped empty; substitute edits are not a listed G4 mechanism (R5 as revised, A6). V4j: justification 'reversing both robots will ... allow robot_2 to proceed' and reasoning 'allow each other to proceed' name an involved robot as proceeding under reverse (contributing only). Refusal not for room -> no V3.)
  - 83.78: D2 waits COMPLETED -> X3 (robot_1|robot_2 close+stopped from 50.87 to censor)
- **Notes.** X1 on a yield backup that moved > commanded distance (methods-note Limits). Alt R3: U:T1_not_run at D1. Alt A6 (substitutions count as G4): G4 contributing at D2. ALT[R3]=U:T1_not_run

### EV-35eb04 FU1: `X3` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (D1 at 19.3 is after t0 17.373). Step 3: T2(t0) True, T1(t0) 13/237 non-empty, episode_gate_pass -> continue. Walk from 17.373: D1 at 19.3 (matched) temporary_wait robot_3,robot_4; T1[D1] pass, no robot in every motion label (no V2); verifier substitute robot_4 cross->wait (not a G4 mechanism, A6); dispatched waits. D1:robot_3:wait / D1:robot_4:wait COMPLETED 29.008; X3 GT input robot_3|robot_4 close+stopped from 17.87 to censor; no exempt pairs on this sheet -> X3 at 29.008.
- **Event codes:**
  - 19.3: D1 analysis/grounding -> none
  - 29.008: D1 waits COMPLETED, robot_3|robot_4 pinned -> X3
  - 32.667: D2 yield robot_4 withheld (no shared lane) -> G2, G1 (m3_default with plan; C2 False; T2[D2] True; not a room refusal (no V3))
  - 39.433: D3 yield robot_3 withheld (no shared lane) -> G2, G1
  - 66.44: D6 waits COMPLETED -> X3
  - 69.7: D7 junction_clear yield robot_5 withheld (robot_5 0.00 m retreat room) -> G2, G1 (V3:U:Y_label_order (robot_4 only first, robot_1 only last in T1[D7] Y labels))
  - 85.58: D8/D9/D10 waits dispatched and COMPLETED -> X3
  - 115.833: D11 junction_clear, plan reverse robot_3 + yields, withheld (retreat room) -> V3, G1 (R:robot_1/R:robot_4/R:robot_5 in T1[D11])
- **Notes.** Alt A7 (X3 only after motion commands): first deviation D2 at 32.667 -> G2 (or G1 if within-G ties go by number, A2). Alt A6 (substitutions are G4): D1 -> G4 primary. X2 inputs cover 0.916 of 458.5 s (38.5 s uncovered < 60 s): not X2. ALT[X3-at-pin-start]=unchanged (pin already open at completion, A10)

### EV-35eb04 FU2: `NOT_FU:parked_finished` (step none)

- **Evidence.** lone_stall robot_2 t0 107.673 flagged finished_all_or_between_tasks_at_censor; listed separately per protocol.

### EV-37a70e FU1: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D2:robot_4:backup (dispatched 30.0, robot_4 executing at t0 36.573); chain_start 30.0; step 3 skipped. Walk: D2 analysis yield robot_4 (involved robot_4,robot_5), C2 False, valid; unmatched to FU1 (V2/V3 untestable). D2 grounding: provenance vlm_verbatim, dispatch_matches_plan True, but G4_role_change_tags ['grounding=node_handoff:robot_4->robot_5'] -> G4 at 30.0 (tool mechanical G4 input, A6).
- **Event codes:**
  - 30.0: D2 analysis -> none (V2/V3:U:T1_not_run)
  - 30.0: D2 grounding -> G4
  - 33.6: D2:robot_4:backup -> G5, X1 (min static gap -0.0057 m obstacle_1 (declared) at 62.57; FAILED deadline 72.33, pinned_on_declared_box)
  - 35.97: gt_contact robot_2|obstacle_1 from 35.97 to censor (robot_2 has no leg) -> X5
  - 39.87: gt_contact robot_4|obstacle_1 39.87-74.27 -> none (inside G5 leg -> not X5)
  - 105.4: D4 waits COMPLETED -> X3 (robot_2|robot_3 close+stopped from 36.77 to censor; no exemption after 92.08)
  - 149.767: D9 junction_clear yield robot_4 withheld (0.00 m retreat room) -> V3, G2, G1 (robot_2 first and last in T1[D9] Y labels; T2[D9] True)
- **Notes.** G4 here rests on a node_handoff tag although dispatch matched the plan (A6 reading A: the tool's mechanical tag). If node_handoff with matching dispatch were not G4, the walk gives G5 at 33.6. Alt R3: U:T1_not_run at D2. ALT[R3]=U:T1_not_run

### EV-37a70e FU2: `V4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D3:robot_1:reverse, D3:robot_5:reverse; D3 dispatched 76.3, t0 101.873; chain_start 76.3. Walk: D3 analysis strategy reverse, involved_robots [robot_1, robot_5], proposed_plan reverse legs [robot_1] only (robot_5 wait) -> contract C1 True -> V4 at 76.3 (also G6_verbatim_contradicted True on the same decision; V before G).
- **Event codes:**
  - 76.3: D3 analysis -> V4 (V4j not flagged: justification/reasoning do not state robot_5 continues or passes)
  - 76.3: D3 grounding (vlm_verbatim, dispatch_matches_plan False) -> G6
  - 92.009: D3 reverse legs COMPLETED -> X3 (robot_1|robot_5 close+stopped from 102.07; exemptions cleared 92.08)
  - 101.873: FU V1 (0 matched) -> V1
  - 186.367: robot_1 STALE 27.47 s -> X4

### EV-3e6d9b FU1: `U:no_m4_clock_anchor` (step 7 (first deviation undetermined: no m4 clock anchor))

- **Evidence.** Layer-2-off coding (R2, rubric 7.6): no decision artifacts, no decisions/legs, m4.log < 2 sim_t= lines. Step 1: t0_snapshot True, m4_log True; decision artifacts not needed (no V/G). Step 2 never fires (nothing dispatched). Step 3: T2(t0) True, so G7 (not applicable by construction) vs continue is the only branch T1 could decide; continue. Step 4 (X only) from t0 14.27: X2 input runs for robot_1, robot_5 start at ~t0 and last to censor, but safety-stop spans are present and unmapped (rel None; wall mapping U:no_m4_clock_anchor), so 'under an active Nav2 goal' cannot be decided (R8); no STALE span >= 10 s; no GT contact (gap <= 0.005) for FU robots; X3 needs a completed command (none).
- **Event codes:**
  - 14.27: X2 input runs (stationary, no M4 leg, traveling) -> U:no_m4_clock_anchor (cover fraction 0.0 is an artefact of unmapped safety-stop spans)
- **Notes.** T1(t0) as written 31/88 non-empty: a Layer-2 action was available (yes); fidelity unverifiable_in_bundle. Alt R8 (every tool X2 input counts): primary X2 (run from ~t0). Alt R2 (treat as Layer-2-on with missing artifacts): U:no_decision_artifacts at step 1. Nav2 abort line robot_1 '[compute_path_to_pose] Aborting handle' is in the FU timeline with unmapped time (rel None): X2 observed (contributing) but its order relative to t0 is unknown, so it cannot be placed as first deviation; if it were inside the walk, primary would be X2.

### EV-3e6d9b FU2: `U:no_m4_clock_anchor` (step 7 (first deviation undetermined: no m4 clock anchor))

- **Evidence.** Layer-2-off coding (R2, rubric 7.6): no decision artifacts, no decisions/legs, m4.log < 2 sim_t= lines. Step 1: t0_snapshot True, m4_log True; decision artifacts not needed (no V/G). Step 2 never fires (nothing dispatched). Step 3: T2(t0) True, so G7 (not applicable by construction) vs continue is the only branch T1 could decide; continue. Step 4 (X only) from t0 20.57: X2 input runs for robot_2, robot_3, robot_4 start at ~t0 and last to censor, but safety-stop spans are present and unmapped (rel None; wall mapping U:no_m4_clock_anchor), so 'under an active Nav2 goal' cannot be decided (R8); no STALE span >= 10 s; no GT contact (gap <= 0.005) for FU robots; X3 needs a completed command (none).
- **Event codes:**
  - 20.57: X2 input runs (stationary, no M4 leg, traveling) -> U:no_m4_clock_anchor (cover fraction 0.0 is an artefact of unmapped safety-stop spans)
- **Notes.** T1(t0) as written 69/237 non-empty: a Layer-2 action was available (yes); fidelity unverifiable_in_bundle. Alt R8 (every tool X2 input counts): primary X2 (run from ~t0). Alt R2 (treat as Layer-2-on with missing artifacts): U:no_decision_artifacts at step 1.

### EV-41a9d4 FU1: `X1` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_3:reverse, D1:robot_4:reverse (dispatched 13.2, t0 22.073); chain_start 13.2; step 3 skipped. Walk: D1 analysis reverse involved robot_3,robot_4, reverse legs robot_3,robot_4 (C1 False), valid; unmatched (V2/V3 untestable). Grounding vlm_verbatim, dispatch matches, no G tags. Legs: min static gaps 0.2419/0.1984 m (no G5). D1:robot_3:reverse m4_terminal FAILED, ended_by_deadline True at 48.913 (moved 0.66/1.3) -> X1; D1:robot_4:reverse FAILED deadline 48.948 (moved 0.345, not_executed).
- **Event codes:**
  - 13.2: D1 analysis -> none (V4j not flagged: 'allow for redirection or sequential passing' names no involved robot as passing (my reading); V2/V3:U:T1_not_run)
  - 48.913: D1:robot_3:reverse FAILED deadline -> X1
  - 48.948: D1:robot_4:reverse FAILED deadline -> X1
  - 52.967: D2 reroute (matched): involved_robots[0]=robot_1 has no reroute leg (C3 True); vlm_verbatim contradicted -> V4, G6
  - 70.99: D2 waits robot_2/3/4 COMPLETED -> X3 (robot_2|robot_3 close+stopped from 22.37; no exemption)
  - 163.4: D4 junction_clear yield robot_1 withheld (0.00 m room) -> G2, G1 (no Y labels in T1[D4] motion -> V3 not met; T2[D4] True)
- **Notes.** X2 inputs cover >= 0.973 (uncovered ~12 s): not X2. ALT[R3]=U:T1_not_run

### EV-41a9d4 FU2: `V1` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D3:robot_1:backup (robot_1 executing at t0 135.073); chain_start 76.733; step 3 skipped. Walk: D3 analysis yield robot_1 (involved robot_1,robot_4), C2 False; not matched to FU2 (V2/V3 untestable). Grounding vlm_verbatim, matches, no G tags; D3:robot_1:backup min static 0.2098 (no G5), COMPLETED at 157.45. No positive analysis matched to FU2 (V1 input a33_matched_positive_analyses 0) -> V1 placed at t0 135.073, before the X3 at 157.45.
- **Event codes:**
  - 76.733: D3 analysis/grounding -> none (V2/V3:U:T1_not_run)
  - 135.073: FU V1 -> V1
  - 157.45: D3:robot_1:backup COMPLETED, robot_1|robot_5 close+stopped from 135.27, non-exempt -> X3
  - 163.4: D4 junction_clear withheld (not matched to FU2) -> G2 (G1/V3 untestable for FU2 (no FU2 T1/T2 at D4))
  - 20.733: robot_1 STALE 20.733-82.067 (61.3 s), open at the walk start -> X4 (interval open at the start point: contributing, not a first deviation (A8))
- **Notes.** robot_1 STALE span 20.733-82.067 (61.3 s) begins before the walk start (76.733) and is not walked (R9); if intervals open at the start point were walked, X4 at the start would be primary. A5: V1 timing at t0. ALT[R3]=U:T1_not_run; ALT[R8]=X2 (run from 134.97)

### EV-478db7 FU1: `X3` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (D1 16.933 after t0 15.307). Step 3: T2(t0) True, T1(t0) 10/237 non-empty, episode_gate_pass -> continue. Walk from 15.307: D1 (matched) temporary_wait robot_2,robot_4 (omits robot_3; T1[D1] pass, no robot in every motion label -> no V2); verifier substitute robot_2 cross->wait (not G4, A6). D1 waits COMPLETED 26.344; robot_2|robot_4 close+stopped from 16.01 to censor, never exempt -> X3 at 26.344.
- **Event codes:**
  - 26.344: D1 waits COMPLETED, pinned pair -> X3
  - 70.0: D3 junction_clear (reverse robot_4, yield robot_3) withheld (retreat room) -> V3, G1 (R:robot_2/R:robot_3 in T1[D3]; T2[D3] True)
  - 110.633: D4 junction_clear reverse robot_4, vlm_verbatim contradicted, withheld -> V3, G1, G6
  - 114.3: D5 junction_clear no plan, withheld -> G1
  - 168.4: D6 junction_clear reverse robot_4/robot_3, withheld -> V3, G1
  - 170.907: stop-rule censor -> X6
- **Notes.** Stop-flag episode. Alt A7 (X3 only after motion commands): primary V3 at D3 (70.0). ALT[X3-at-pin-start]=unchanged (pin already open at completion, A10)

### EV-52a0c3 FU1: `U:T1_fidelity` (step 7 (entered from step 3: T1(t0) U:T1_fidelity))

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (D1 13.667 after t0 12.17). Step 3: T2(t0) True; T1(t0) as written 'U:T1_fidelity' (episode gate as-written false). T1 decides G7 vs continue -> U:T1_fidelity (R1).
- **Event codes:**
  - 12.189: nav2 abort robot_1 [compute_path_to_pose] -> X2
  - 13.667: D1 yield robot_5 (matched), swapped to robot_2 (node_handoff tags) -> G4 (T1[D1] as written U:T1_fidelity -> V2/V3:U:T1_fidelity; C2 False)
  - 50.6: D1:robot_5:escort -> none (not_executed, terminal None)
  - 94.9: D1 backup/waits COMPLETED -> X3 (robot_1|robot_5 close+stopped from 16.97 to censor, non-exempt)
  - 112.13: D3 waits COMPLETED -> X3
  - 115.667: D4 junction_clear (reverse robot_4/robot_3, yield robot_1) withheld (retreat room) -> V3, G1
- **Notes.** Alt R1 (walk step 4 from t0): first deviation Nav2 abort robot_1 at 12.189 -> X2.

### EV-62b8d0 FU1: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_1:backup, D1:robot_4:escort, D1:robot_4:wait; D1 dispatched 11.4, t0 23.607; chain_start 11.4; step 3 skipped (T1(t0) U:T1_fidelity not deciding). Walk: D1 analysis yield robot_1 (involved robot_1,robot_4), C2 False; unmatched (V2/V3 untestable; D1 fidelity as-written 'differs'). D1 grounding: vlm_verbatim, dispatch_matches_plan True, G4_role_change_tags ['grounding=node_handoff:robot_1->robot_4'] -> G4 at 11.4.
- **Event codes:**
  - 11.4: D1 analysis -> none (V2/V3:U:T1_not_run)
  - 11.4: D1 grounding -> G4
  - 48.278: D1:robot_1:backup FAILED deadline (moved 0.901/1.349) -> X1
  - 48.278: D1:robot_4:wait COMPLETED; robot_2|robot_4 close+stopped from 89.41, non-exempt -> X3
  - 51.567: D2 reverse involved robot_4,robot_5, reverse legs [robot_4] (C1 True); dispatch robot_5 reverse (robot_4 dropped, handoff tag) -> V4, V4j, G4 (V4j: justification 'open up space for robot_5 to continue' names involved robot_5 as continuing under reverse)
  - 59.733: D3 reverse involved all five, reverse legs robot_4,robot_5 (C1 True); dropped robot_2,robot_5, rear_exempt, handoff; vlm_verbatim contradicted -> V4, V4j, G4, G6 (V4j: 'create space for robot 1, 2, and 3 to safely proceed')
  - 61.234: D3:robot_1:reverse -> G5, X1 (min static gap -0.0 to rack/NW_west (undeclared); FAILED deadline 94.556, pinned_on_undeclared_box)
  - 67.51: gt_contact robot_1|rack/NW_west from 67.51 to censor -> EG2 (begins inside the G5 leg -> not X5)
  - 69.422: D2:robot_5:reverse COMPLETED; D3 robot_3/robot_4 reverse COMPLETED -> X3
  - 99.4: D4 junction_clear (reverse robot_4, yield robot_2) withheld (retreat room) -> V3, G1
- **Notes.** Alt R3: U:T1_not_run at D1. If node_handoff with matching dispatch were not G4 (A6), first deviation would be X1 at 48.278 (or X3 same time; X1 listed first only by order of legs - tie within X unresolved). ALT[R3]=U:T1_not_run

### EV-69a2ea FU1: `U:no_m4_clock_anchor` (step 7 (first deviation undetermined: no m4 clock anchor))

- **Evidence.** Layer-2-off coding (R2, rubric 7.6): no decision artifacts, no decisions/legs, m4.log < 2 sim_t= lines. Step 1: t0_snapshot True, m4_log True; decision artifacts not needed (no V/G). Step 2 never fires (nothing dispatched). Step 3: T2(t0) True, so G7 (not applicable by construction) vs continue is the only branch T1 could decide; continue. Step 4 (X only) from t0 15.97: X2 input runs for robot_1, robot_4 start at ~t0 and last to censor, but safety-stop spans are present and unmapped (rel None; wall mapping U:no_m4_clock_anchor), so 'under an active Nav2 goal' cannot be decided (R8); no STALE span >= 10 s; no GT contact (gap <= 0.005) for FU robots; X3 needs a completed command (none).
- **Event codes:**
  - 15.97: X2 input runs (stationary, no M4 leg, traveling) -> U:no_m4_clock_anchor (cover fraction 0.0 is an artefact of unmapped safety-stop spans)
- **Notes.** T1(t0) as written 5/88 non-empty: a Layer-2 action was available (yes); fidelity unverifiable_in_bundle. Alt R8 (every tool X2 input counts): primary X2 (run from ~t0). Alt R2 (treat as Layer-2-on with missing artifacts): U:no_decision_artifacts at step 1.

### EV-69a2ea FU2: `U:no_m4_clock_anchor` (step 7 (first deviation undetermined: no m4 clock anchor))

- **Evidence.** Layer-2-off coding (R2, rubric 7.6): no decision artifacts, no decisions/legs, m4.log < 2 sim_t= lines. Step 1: t0_snapshot True, m4_log True; decision artifacts not needed (no V/G). Step 2 never fires (nothing dispatched). Step 3: T2(t0) True, so G7 (not applicable by construction) vs continue is the only branch T1 could decide; continue. Step 4 (X only) from t0 19.57: X2 input runs for robot_2, robot_3, robot_5 start at ~t0 and last to censor, but safety-stop spans are present and unmapped (rel None; wall mapping U:no_m4_clock_anchor), so 'under an active Nav2 goal' cannot be decided (R8); no STALE span >= 10 s; no GT contact (gap <= 0.005) for FU robots; X3 needs a completed command (none).
- **Event codes:**
  - 19.57: X2 input runs (stationary, no M4 leg, traveling) -> U:no_m4_clock_anchor (cover fraction 0.0 is an artefact of unmapped safety-stop spans)
- **Notes.** T1(t0) as written 97/237 non-empty: a Layer-2 action was available (yes); fidelity unverifiable_in_bundle. Alt R8 (every tool X2 input counts): primary X2 (run from ~t0). Alt R2 (treat as Layer-2-on with missing artifacts): U:no_decision_artifacts at step 1.

### EV-6f1277 FU1: `G2` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) []. Step 3: T2(t0) True, T1(t0) 6/88 non-empty, episode_gate_pass -> continue. Walk from 17.273: D1 at 19.267 (matched) yield robot_5, C2 False, valid. V3 not met: refused for room ('no executable retreat (robot_4 has no retreat candidate surviving the sweep ...)') but T1[D1] has no Y labels in motion, so no other FU robot is shown feasible as yielder. Verifier provenance m3_default with plan present (G2_m3_default_with_plan True) -> G2; grounding withheld refusal_no_action with T2[D1] True -> G1; G2 taken as upstream (A2).
- **Event codes:**
  - 19.267: D1 verifier/grounding -> G2, G1 (heading_regrounded tag but withheld -> not G4)
  - 23.767: D2, D3, D4 (same pattern) -> G2, G1 (Y labels robust only for robot_2 (not an FU robot) -> no V3)
  - 68.667: D5 reverse robot_4+robot_5 (C1 False), substituted to waits, dispatched -> none (no G4 (A6); V4j not flagged)
  - 78.334: D5 waits COMPLETED; robot_4|robot_5 close+stopped from 17.77, never exempt -> X3
  - 81.467: D6, D7 (same as D1) -> G2, G1
- **Notes.** A2: by code number the primary would be G1.

### EV-6f1277 FU2: `V1` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) []. Step 3: T2(t0) True, T1(t0) 80/237 non-empty, episode_gate_pass -> continue. Walk from t0 23.473: V1 input a33_matched_positive_analyses 0 (no positive analysis matched to the FU) -> V1 at t0.
- **Event codes:**
  - 23.473: FU V1 -> V1
- **Notes.** X2 inputs cover >= 0.955 (uncovered < 60 s): not X2. No other events on the timeline. Under ALT[R8] the robot_2 run starts at 23.47, 0.003 s before t0, so it is open at the start point: contributing only (A8), and the primary stays V1.

### EV-7bda3f FU1: `X3` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (D1 14.267 after t0 12.277). Step 3: T2(t0) True, T1(t0) 61/237 non-empty, episode_gate_pass -> continue. Walk: D1 (matched) reverse robot_2,robot_3, reverse legs both (C1 False), V4j not flagged; T1[D1] no robot in every motion label; verifier substituted both reverse legs to wait ('both outside the corridor on the same side'; not G4 under A6, not a room refusal); waits dispatched and COMPLETED 23.705; robot_2|robot_3 close+stopped from 12.78 to censor, never exempt -> X3 at 23.705.
- **Event codes:**
  - 23.705: D1 waits COMPLETED, pinned pair -> X3
  - 27.2: D2 junction_clear (yields robot_1/robot_2) withheld, not matched to FU1 -> G2 (V3/G1 untestable for FU1 (no FU1 T1/T2 at D2))
  - 81.333: D4 junction_clear, plan reverse robot_2, withheld (retreat room) -> V3, G1 (R:robot_3/R:robot_4 in T1[D4])
  - 85.867: D5 reverse involved robot_2,3,4, reverse legs [robot_2] (C1 True); verifier swap robot_2<->robot_4; waits dispatched -> V4, V4j, G4 (V4j: 'allowing robot_3 and robot_4 to proceed'. G4 via the listed 'swap' mechanism (verifier edit op swap) although G4_role_change_tags is empty)
  - 96.385: D5 waits COMPLETED -> X3
  - 99.433: D6 junction_clear reverse robot_4 withheld (retreat room), vlm_verbatim contradicted -> V3, G1, G6
  - 102.277: stop-rule censor -> X6
- **Notes.** Stop-flag episode. Alt A7 (X3 only after motion commands): primary G2 at D2 (27.2). ALT[X3-at-pin-start]=unchanged (pin already open at completion, A10)

### EV-7bda3f FU2: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D3:robot_5:backup, D3:robot_1:escort, D3:robot_1:wait; D3 dispatched 36.567, t0 81.177 (44.6 s before); chain_start 36.567; step 3 skipped. Walk: D3 analysis yield robot_1, C2 False (not matched to FU2; V2/V3 untestable). D3 grounding: verifier swap robot_1<->robot_5, G4_role_change_tags ['grounding=heading_regrounded:robot_1->robot_5'], dispatched robot_5:yield -> G4.
- **Event codes:**
  - 36.567: D3 analysis -> none (V2/V3:U:T1_not_run)
  - 36.567: D3 grounding -> G4
  - 77.362: D3 legs COMPLETED (backup 1.422/1.361, escort 0.807/0.817); robot_1|robot_5 close+stopped from 81.28; exemption cleared 77.398 -> X3
  - 81.177: FU V1 (0 matched) -> V1
  - 102.277: stop-rule censor -> X6
- **Notes.** Alt R3: U:T1_not_run at D3. D2 (27.2) precedes the chain start. ALT[R3]=U:T1_not_run

### EV-7bf1e2 FU1: `G2` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) []. Step 3: T2(t0) True, T1(t0) 21/237 non-empty, episode_gate_pass -> continue. Walk from t0 11.203: no deviation before D2 (X2 runs begin 58.8 with cover 1.0). D2 at 48.8 (matched) temporary_wait robot_1,robot_2,robot_5 (T1[D2] pass; no robot in every motion label: no V2); proposed_plan present (robot_3 yield, robot_4 cross, waits) and verifier provenance m3_default -> G2_m3_default_with_plan True -> G2 at 48.8.
- **Event codes:**
  - 48.8: D2 verifier -> G2
  - 58.79: D2 waits COMPLETED; robot_1|robot_2 (from 28.6) and robot_1|robot_5 (from 11.9) pinned to censor, never exempt -> X3

### EV-7bf1e2 FU2: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_3:backup, D1:robot_4:escort, D1:robot_4:wait; D1 dispatched 13.767, t0 63.803 (50.0 s before); chain_start 13.767. Walk: D1 analysis yield robot_4, C2 False (no FU2 T1 row at D1: V2/V3 untestable). D1 grounding: swap robot_4<->robot_3 ('robot_4 has no retreat candidate surviving the sweep'), G4_role_change_tags ['yield_robot=sweep_regrounded:robot_4->robot_3', ...], dispatched robot_3:yield -> G4.
- **Event codes:**
  - 13.767: D1 analysis -> none (V2/V3:U:T1_not_run)
  - 13.767: D1 grounding -> G4
  - 63.391: D1 legs COMPLETED; robot_3|robot_4 close+stopped from 64.3; exemption cleared 63.381 -> X3
  - 67.1: D3 yield robot_3 withheld (no shared lane) -> G2, G1
- **Notes.** Alt R3: U:T1_not_run at D1. ALT[R3]=U:T1_not_run

### EV-7e1fa5 FU1: `X2` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) []. Step 3: T2(t0) True, T1(t0) 29/88 non-empty, episode_gate_pass -> continue. Walk from t0 14.97: Nav2 abort line robot_4 at 14.978 '[follow_path] [ActionServer] Aborting handle.' -> X2.
- **Event codes:**
  - 14.978: nav2 abort robot_4 -> X2
  - 16.567: D1 yield robot_3 withheld (ambiguous lane) -> G2, G1 (not a room refusal: no V3)
  - 29.85: D2 reverse robot_3+robot_4 (C1 False) substituted to waits; waits COMPLETED -> X3 (robot_3|robot_4 close+stopped from 15.57; no exemptions; V4j not flagged)
  - 33.3: D3, D4, D5 yield withheld (ambiguous lane) -> G2, G1
- **Notes.** Abort coincides with the safety-stop start (14.961). X2 runs cover 0.903 of 540.8 s (52 s uncovered < 60): not X2 by the run branch. If the abort were not counted, primary would be G2 at D1 (16.567).

### EV-7e1fa5 FU2: `V1` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) []. Step 3: T2(t0) True, T1(t0) 2/88 non-empty, episode_gate_pass -> continue. Walk from t0 30.67: V1 input a33_matched_positive_analyses 0 -> V1 at t0. Nav2 aborts for robot_1 at 16.6-16.7 precede t0 (not walked, A8).
- **Event codes:**
  - 30.67: FU V1 -> V1
- **Notes.** X2 runs: robot_5 from 28.57 cover 0.90 (54 s uncovered), robot_1 cover 0.903 (52 s): below 60 s, not X2. Alt R8: X2 run robot_5 from 28.57 precedes t0 (open at start) -> still V1 under A8.

### EV-7e1fa5 FU3: `NOT_FU:parked_finished` (step none)

- **Evidence.** lone_stall robot_2 t0 138.17 flagged finished_all_or_between_tasks_at_censor; listed separately.

### EV-80fb2a FU1: `V1` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (D2 dispatched 52.467, legs ended 109.5; neither within 60 s before t0 148.937 nor executing at t0). Step 3: T2(t0) True, T1(t0) 30/88 non-empty, episode_gate_pass -> continue. Walk from t0: V1 input a33_matched_positive_analyses 0 -> V1 at t0.
- **Event codes:**
  - 148.937: FU V1 -> V1
- **Notes.** X2 runs cover 1.0 (not X2). The end-window chain variant would link D2 (S1-type sensitivity, not used).

### EV-80fb2a FU2: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D4:robot_3:reverse, D4:robot_5:reverse; D4 dispatched 133.667, t0 162.237; chain_start 133.667. Walk: D4 analysis reverse involved robot_1,robot_3,robot_5 with no proposed_plan (C1-C3 None), not matched to FU2 (V2/V3 untestable). D4 grounding m3_default (no plan, so not G2), G4_role_change_tags ['grounding=node_handoff:robot_3->robot_1'], G4_robots_dropped ['robot_1']; dispatched robot_3, robot_5 reverse only -> G4 at 133.667.
- **Event codes:**
  - 133.667: D4 analysis -> none (V4j not flagged: robot_1/robot_5 described as waiting, not continuing/passing)
  - 133.667: D4 grounding -> G4
  - 135.4: D4:robot_3:reverse -> G5, X1 (min static gap -0.0015 m rack/SW_south (undeclared); FAILED deadline 171.656, pinned_on_undeclared_box)
  - 143.54: gt_contact robot_3|rack/SW_south 143.54 to censor -> EG2 (inside G5 leg -> not X5)
  - 149.252: D4:robot_5:reverse COMPLETED; robot_1|robot_5 close+stopped from 166.34, non-exempt after 149.264 -> X3
  - 172.986: nav2 abort robot_3 -> X2
  - 174.667: D5 yield robot_1 withheld (no shared lane) -> G2, G1
- **Notes.** Alt R3: U:T1_not_run at D4. ALT[R3]=U:T1_not_run

### EV-830943 FU1: `G6` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_1:backup, D1:robot_5:escort and D1 waits; D1 dispatched 15.433, t0 22.803; chain_start 15.433; step 3 skipped (T1(t0) U:T1_fidelity not deciding). Walk: D1 analysis yield robot_1 (involved robot_1,robot_5), C2 False; unmatched (V2/V3 untestable; D1 fidelity as-written 'differs'). D1 grounding: provenance vlm_verbatim, dispatch_matches_plan False, G6_verbatim_contradicted True; no G4 tags -> G6 at 15.433.
- **Event codes:**
  - 15.433: D1 analysis -> none (V2/V3:U:T1_not_run)
  - 15.433: D1 grounding -> G6
  - 70.21: D1 legs/waits COMPLETED; robot_2|robot_3 close+stopped from 23.3, non-exempt -> X3
  - 74.667: D2 yield robot_3 withheld (empty_reroute) -> G2, G1 (handoff tag but withheld -> not G4; C2 False; T2[D2] True; withheld treated as refused (R5))
  - 79.267: D3 reroute: involved_robots[0]=robot_2 has no reroute leg (C3 True); vlm_verbatim contradicted -> V4, G6
  - 99.367: D3:robot_3:wait COMPLETED -> X3
  - 104.633: D4 yield robot_2 withheld (empty_reroute) -> G2, G1
  - 105.501: nav2 'Failed to make progress'/abort robot_2 -> X2
  - 106.14: D3:robot_2:reroute FAILED -> X1
- **Notes.** Alt R3: U:T1_not_run at D1. ALT[R3]=U:T1_not_run

### EV-a2cfc5 FU1: `X3` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D2:robot_2:reverse, D2:robot_4:reverse; D2 dispatched 18.5, t0 25.07; chain_start 18.5; step 3 skipped. Walk: D2 analysis reverse robot_2,robot_4, reverse legs both (C1 False), V4j not flagged; unmatched (V2/V3 untestable). Grounding vlm_verbatim, matches, no G tags. D2:robot_2:reverse min static 0.0582 (no G5), COMPLETED 37.829 (moved 1.307/1.3). After 37.829 FU pairs robot_3|robot_5 (from 25.47) and robot_2|robot_3 (from 46.77) stay close+stopped to censor; neither is in the exempt set (only robot_2+robot_4) -> X3 at 37.829.
- **Event codes:**
  - 18.5: D2 analysis/grounding -> none (V2/V3:U:T1_not_run)
  - 37.829: D2:robot_2:reverse COMPLETED, pinned non-exempt pairs follow -> X3
  - 55.967: D3 junction_clear (yield robot_5, robot_4) withheld (retreat room) -> V3, G2, G1 (other FU robots first and last in T1[D3] Y labels)
  - 62.481: D2:robot_4:reverse FAILED deadline (moved 0.529/1.3) -> X1
  - 66.033: D4 junction_clear (reverse robot_5) withheld (retreat room) -> V3, G1
  - 66.4: robot_1 STALE 27.8 s (and later spans) -> X4
- **Notes.** X3 placed at the first completed command; the pinned pair robot_3|robot_5 does not include the commanded robot (R10 does not require it); robot_2|robot_3 does. Alt R3: U:T1_not_run at D2. D1 (14.7, withheld) precedes the chain start. ALT[R3]=U:T1_not_run; ALT[R8]=X2 (run from 25.07); ALT[X3-at-pin-start]=unchanged (pin already open at completion, A10)

### EV-a6761e FU1: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_3:wait (D1 dispatched 12.0, t0 12.073); chain_start 12.0; step 3 skipped. Walk: D1 analysis yield robot_1 (involved robot_1,robot_4; neither in FU1), C2 False; unmatched (V2/V3 untestable). D1 grounding: G4_role_change_tags ['grounding=node_handoff:robot_1->robot_4'] and G6_verbatim_contradicted True (vlm_verbatim, dispatch_matches_plan False) -> G4 (pipeline order before G6, A2) at 12.0.
- **Event codes:**
  - 12.0: D1 analysis -> none (V2/V3:U:T1_not_run)
  - 12.0: D1 grounding/dispatch (robot_3:temporary_wait) -> G4, G6
  - 68.0: D1:robot_3:wait COMPLETED; robot_2|robot_3 close+stopped from 12.57, never exempt -> X3
  - 71.1: D2, D3, D4 yield robot_3 withheld (no executable retreat) -> G2, G1 (no Y labels in T1 motion -> no V3; heading_regrounded tag but withheld -> not G4)
- **Notes.** The G4/G6 of the chain-start decision concern robot_1/robot_4 roles, not FU1 robots; the chain links FU1 to D1 only through robot_3's wait. If deviations had to concern an FU robot, the walk would give X3 at 68.0. Alt R3: U:T1_not_run at D1. ALT[R3]=U:T1_not_run

### EV-a6761e FU2: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_1:backup, D1:robot_4:escort, D1 waits; D1 dispatched 12.0, t0 69.773 (57.8 s before); chain_start 12.0. Walk: D1 analysis yield robot_1, C2 False; not matched to FU2 (V2/V3 untestable; D1 as-written fidelity 'differs'). D1 grounding: G4_role_change_tags ['grounding=node_handoff:robot_1->robot_4'], G6 True -> G4 at 12.0.
- **Event codes:**
  - 12.0: D1 grounding -> G4, G6
  - 68.034: D1 legs COMPLETED; robot_1|robot_4 close+stopped from 70.07; exemption cleared 68.116 -> X3
  - 69.773: FU V1 (0 matched) -> V1
- **Notes.** Alt R3: U:T1_not_run at D1. ALT[R3]=U:T1_not_run

### EV-b13ac7 FU1: `X1` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (D1 14.4 after t0 12.24). Step 3: T2(t0) True, T1(t0) 60/237 non-empty, episode_gate_pass -> continue. Walk: D1 (matched) reverse robot_3,robot_4, reverse legs both (C1 False); T1[D1] pass, no robot in every motion label; vlm_verbatim, dispatch matches, no G tags. D1:robot_3:reverse min static 0.3898 (no G5); m4_terminal FAILED at 17.386 (moved 0.106/1.3, deadline False) -> X1.
- **Event codes:**
  - 14.4: D1 analysis -> none (V4j not flagged: 'reversing will allow them to create enough clearance to negotiate passing' does not name one involved robot as continuing/passing while the other reverses (my reading))
  - 17.386: D1:robot_3:reverse FAILED -> X1
  - 31.724: D1:robot_4:reverse COMPLETED; robot_1|robot_3 (from 17.24), robot_3|robot_4 (from 38.94) pinned; exemption cleared 31.725 -> X3
  - 33.467: D2 yield robot_1 withheld (no shared lane) -> G2, G1
  - 34.31: nav2 abort robot_2 -> X2
  - 37.467: D3 junction_clear yield robot_4 withheld (retreat room) -> V3, G2, G1 (robot_3 first and last in T1[D3] Y labels)
  - 41.7: D4 junction_clear reverse robot_4 + yield robot_1 withheld -> V3, G1
  - 45.867: D5 junction_clear reverse robot_4 withheld, vlm_verbatim contradicted -> V3, G1, G6
  - 74.767: D6 junction_clear no plan withheld -> G1
- **Notes.** X2 runs cover >= 0.985 (uncovered < 60 s). ALT[R8]=X2 (run from 16.94)

### EV-c49058 FU1: `U:no_m4_clock_anchor` (step 7 (first deviation undetermined: no m4 clock anchor))

- **Evidence.** Layer-2-off coding (R2, rubric 7.6): no decision artifacts, no decisions/legs, m4.log < 2 sim_t= lines. Step 1: t0_snapshot True, m4_log True; decision artifacts not needed (no V/G). Step 2 never fires (nothing dispatched). Step 3: T2(t0) True, so G7 (not applicable by construction) vs continue is the only branch T1 could decide; continue. Step 4 (X only) from t0 17.173: X2 input runs for robot_3, robot_4, robot_5 start at ~t0 and last to censor, but safety-stop spans are present and unmapped (rel None; wall mapping U:no_m4_clock_anchor), so 'under an active Nav2 goal' cannot be decided (R8); no STALE span >= 10 s; no GT contact (gap <= 0.005) for FU robots; X3 needs a completed command (none).
- **Event codes:**
  - 17.173: X2 input runs (stationary, no M4 leg, traveling) -> U:no_m4_clock_anchor (cover fraction 0.0 is an artefact of unmapped safety-stop spans)
- **Notes.** T1(t0) as written 11/237 non-empty: a Layer-2 action was available (yes); fidelity unverifiable_in_bundle. Alt R8 (every tool X2 input counts): primary X2 (run from ~t0). Alt R2 (treat as Layer-2-on with missing artifacts): U:no_decision_artifacts at step 1.

### EV-c49058 FU2: `U:no_m4_clock_anchor` (step 7 (first deviation undetermined: no m4 clock anchor))

- **Evidence.** Layer-2-off coding (R2, rubric 7.6): no decision artifacts, no decisions/legs, m4.log < 2 sim_t= lines. Step 1: t0_snapshot True, m4_log True; decision artifacts not needed (no V/G). Step 2 never fires (nothing dispatched). Step 3: T2(t0) True, so G7 (not applicable by construction) vs continue is the only branch T1 could decide; continue. Step 4 (X only) from t0 54.673: X2 input runs for robot_1, robot_2 start at ~t0 and last to censor, but safety-stop spans are present and unmapped (rel None; wall mapping U:no_m4_clock_anchor), so 'under an active Nav2 goal' cannot be decided (R8); no STALE span >= 10 s; no GT contact (gap <= 0.005) for FU robots; X3 needs a completed command (none).
- **Event codes:**
  - 54.673: X2 input runs (stationary, no M4 leg, traveling) -> U:no_m4_clock_anchor (cover fraction 0.0 is an artefact of unmapped safety-stop spans)
- **Notes.** T1(t0) as written 29/88 non-empty: a Layer-2 action was available (yes); fidelity unverifiable_in_bundle. Alt R8 (every tool X2 input counts): primary X2 (run from ~t0). Alt R2 (treat as Layer-2-on with missing artifacts): U:no_decision_artifacts at step 1.

### EV-cb3996 FU1: `G5` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_2:reverse, D1:robot_4:reverse; D1 dispatched 13.4, t0 31.603; chain_start 13.4. Walk: D1 analysis reverse involved robot_1..robot_4, reverse legs all four (C1 False), V4j not flagged; not matched to FU1 (V2/V3 untestable). Grounding vlm_verbatim, matches, no G tags. D1:robot_2:reverse min static 0.2761 (no G5). D1:robot_4:reverse (start 15.233) recomputed min static gap -0.0 m to rack/NW_west (undeclared) at 22.6 -> G5.
- **Event codes:**
  - 13.4: D1 analysis/grounding -> none (V2/V3:U:T1_not_run)
  - 15.233: D1:robot_4:reverse -> G5, X1 (FAILED deadline 60.453, moved 0.647/1.3)
  - 22.0: gt_contact robot_4|rack/NW_west 22.0-54.4 -> EG2 (inside the G5 leg -> not X5)
  - 29.62: D1:robot_2:reverse COMPLETED; robot_2|robot_5 close+stopped from 31.9, non-exempt -> X3
  - 66.233: D4 junction_clear (yield robot_1, robot_2) withheld (retreat room) -> V3, G2, G1 (robot_4 first and last in T1[D4] Y labels)
- **Notes.** ALT[R3]=U:T1_not_run

### EV-cb3996 FU2: `X3` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_1:reverse, D1:robot_3:reverse; chain_start 13.4 (t0 37.803). Walk: D1 analysis reverse (C1 False), not matched to FU2 (V2/V3 untestable); grounding no G; legs min static 0.0763/0.2707 (no G5). D1:robot_3:reverse COMPLETED 29.628, D1:robot_1:reverse COMPLETED 29.712; robot_1+robot_3 leaves the exempt set at 29.744; X3 GT input robot_1|robot_3 close+stopped from 38.0 to censor -> X3 at 29.712.
- **Event codes:**
  - 13.4: D1 analysis/grounding -> none
  - 29.712: D1 reverse legs COMPLETED, pair pinned after exemption cleared -> X3
  - 32.516: nav2 abort robot_3 -> X2
  - 57.233: D2, D3 yield robot_1 withheld (ambiguous lane) -> G2, G1
  - 66.233: D4 junction_clear withheld (not matched to FU2) -> G2 (V3/G1 untestable for FU2)
- **Notes.** The pair was still exempt at the exact completion instant (cleared 0.03 s later); coded X3 because the pair stays pinned while non-exempt after the command. ALT[R3]=U:T1_not_run; ALT[X3-at-pin-start]=X2, nav2 abort robot_3 32.516 precedes pin start 38.0 (A10)

### EV-db0df6 FU1: `V4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D3:robot_1/2/3:reverse; D3 dispatched 30.067, t0 54.607; chain_start 30.067. Walk: D3 analysis strategy reverse, involved_robots [robot_1, robot_2, robot_3, robot_4], reverse legs [robot_3, robot_4] (robot_1, robot_2 cross) -> contract C1 True -> V4 at 30.067 (V before the same decision's G4).
- **Event codes:**
  - 30.067: D3 analysis -> V4 (V4j not flagged (justification names only robot_4/robot_3 reversing); D3 unmatched to FU1 so V2/V3 untestable, but C1 needs no T1)
  - 30.067: D3 grounding: node_handoff robot_1->robot_4, robot_4 dropped; dispatched robot_1/2/3 reverse -> G4
  - 44.547: D3 reverse legs COMPLETED (min static >= 0.0822); robot_2|robot_3 close+stopped from 54.91; exemption cleared 44.694 -> X3
  - 68.033: D5, D6 yield withheld (no declared junction) -> G2, G1 (not a room refusal)
  - 84.445: D7/D8 waits COMPLETED -> X3
  - 99.767: D9 junction_clear no plan withheld (matched to FU1) -> G1

### EV-db0df6 FU2: `V4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D4:robot_4:reverse, D4:robot_5:reverse; D4 dispatched 49.067, t0 73.507; chain_start 49.067. Walk: D4 analysis strategy reverse, involved [robot_4, robot_5], reverse legs [robot_4] only (robot_5 continue) -> C1 True -> V4 at 49.067.
- **Event codes:**
  - 49.067: D4 analysis -> V4, V4j (V4j: justification 'Robot 4 must reverse out of the passage so that Robot 5 can continue')
  - 49.067: D4 grounding vlm_verbatim, dispatch_matches_plan False -> G6
  - 50.4: D4 reverse legs -> none (min static gaps 0.0055 / 0.0191 m (not < 0.005): no G5)
  - 63.371: D4 legs COMPLETED; robot_4|robot_5 close+stopped from 73.61; exemption cleared 63.41 -> X3
  - 84.445: D7/D8 waits COMPLETED -> X3
  - 99.767: D9 withheld (not matched to FU2) -> none (G1 untestable for FU2)

### EV-e0f9cf FU1: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_1:backup; D1 dispatched 13.7, t0 28.303; chain_start 13.7; step 3 skipped (T1(t0) U:T1_fidelity not deciding). Walk: D1 analysis yield robot_5 (involved robot_1,robot_5), C2 False; unmatched (V2/V3 untestable; as-written fidelity 'differs'). D1 grounding: verifier swap robot_1<->robot_5, G4_role_change_tags ['grounding=node_handoff:robot_1->robot_5','grounding=node_handoff_regrounded:robot_5->robot_1'], dispatched robot_1:yield -> G4 at 13.7.
- **Event codes:**
  - 13.7: D1 analysis -> none (V2/V3:U:T1_not_run)
  - 13.7: D1 grounding -> G4
  - 28.303: FU V1 (0 matched) -> V1
  - 56.272: D1:robot_1:backup FAILED deadline (moved 1.023/1.408) -> X1
  - 99.2: 38 analyses backend_failed (ConnectionError) 99.2-207.9 -> V6 (not on the FU timeline (no robots named); counted as FU events because they fall inside the FU window (A9))
  - 210.103: stop-rule censor -> X6
- **Notes.** Stop-flag episode. Alt R3: U:T1_not_run at D1. ALT[R3]=U:T1_not_run

### EV-e0f9cf FU2: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_5:escort, D1:robot_5:wait, D2:robot_2:reverse; earliest qualifying dispatch D1 13.7 (t0 67.003, 53.3 s before); chain_start 13.7. Walk: D1 analysis (yield robot_5), C2 False, unmatched (V2/V3 untestable). D1 grounding: swap robot_5 -> robot_1 with node_handoff tags (G4_role_change_tags non-empty); FU robot robot_5 dispatched temporary_wait instead of its decided yield -> G4 at 13.7.
- **Event codes:**
  - 13.7: D1 grounding -> G4
  - None: D1:robot_5:escort -> none (escort_not_admitted)
  - 56.273: D1:robot_5:wait COMPLETED; robot_2|robot_4 close+stopped from 68.8, non-exempt -> X3
  - 60.067: D2 reverse robot_2,robot_4 (C1 False); dispatch robot_2 only (robot_4 dropped, handoff); vlm_verbatim contradicted -> G4, G6
  - 61.5: D2:robot_2:reverse -> G5, X1 (min static -0.0014 m obstacle_2 (declared); FAILED deadline 97.918, pinned)
  - 66.5: gt_contact robot_2|obstacle_2 66.5 to censor -> none (inside G5 leg -> not X5)
  - 67.003: FU V1 (0 matched) -> V1
  - 99.2: backend_failed analyses from 99.2 -> V6
  - 102.944: nav2 abort robot_5 -> X2
  - 210.103: stop-rule censor -> X6
- **Notes.** Stop-flag episode. Alt R3: U:T1_not_run at D1. ALT[R3]=U:T1_not_run

### EV-e26384 FU1: `U:T1_fidelity` (step 7 (entered from step 3: T1(t0) U:T1_fidelity))

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (D1 16.733 after t0 14.507). Step 3: T2(t0) True; T1(t0) as written 'U:T1_fidelity' (episode gate as-written false; 7/88 under +intents). T1 decides G7 vs continue -> U:T1_fidelity (R1).
- **Event codes:**
  - 16.733: D1 temporary_wait robot_1,robot_5 (matched; vlm_verbatim, matches) -> none
  - 26.235: D1 waits COMPLETED; robot_1|robot_5 close+stopped from 15.31, never exempt -> X3
  - 29.4: D2, D3 yield robot_5 withheld (no shared lane) -> G2, G1
  - 108.807: stop-rule censor -> X6
- **Notes.** Stop-flag episode. Alt R1 (walk step 4 from t0): primary X3 at 26.235 (and under A7-B, G2 at D2 29.4).

### EV-ef4e73 FU1: `U:T1_fidelity` (step 7 (entered from step 3: T1(t0) U:T1_fidelity))

- **Evidence.** Gate all True. Step 2: chain (rubric) [] (D4 dispatched 92.7 and completed 164.0; not within 60 s before t0 184.407 nor executing at t0). Step 3: T2(t0) True; T1(t0) as written 'U:T1_fidelity' (also under +intents). T1 decides G7 vs continue -> U:T1_fidelity (R1).
- **Event codes:**
  - 206.2: D6 temporary_wait robot_2,4,5 (matched; no plan, m3_default) -> none (T1[D6] pass, no robot in every motion label)
  - 217.164: D6 waits COMPLETED; robot_2|robot_5 (from 184.61) and robot_4|robot_5 (from 195.11) pinned, no exemption after 164.002 -> X3
- **Notes.** Alt R1 (walk step 4 from t0): primary X3 at 217.164 (under A7-B no deviation -> step 7 U). The end-window chain variant would link D4.

### EV-ef4e73 FU2: `G5` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D5:robot_1:backup, D5:robot_3:escort, D5:robot_3:wait; D5 dispatched 171.7, t0 219.007; chain_start 171.7; step 3 skipped. Walk: D5 analysis yield robot_1, C2 False, not matched to FU2 (V2/V3 untestable); grounding vlm_verbatim, matches, no G tags. D5:robot_1:backup (start 175.6) recomputed min robot gap -0.0003 m to robot_3 at 226.61 -> G5 (gap of a commanded leg < 0.005 m; the pair was exempt robot_1+robot_3 during the leg, which the G5 clause does not exempt).
- **Event codes:**
  - 171.7: D5 analysis/grounding -> none (V2/V3:U:T1_not_run)
  - 175.6: D5:robot_1:backup -> G5 (COMPLETED 235.587 (moved 1.582/1.373))
  - 204.634: D5:robot_3:escort -> G5 (min robot gap -0.0003 to robot_1)
  - 222.31: gt_contact robot_1|robot_3 222.31 to censor -> none (begins inside the G5 legs -> not X5)
  - 231.667: robot_1, robot_3 STALE 339.1 s -> X4
  - 235.635: D5 legs COMPLETED; robot_1|robot_3 close+stopped from 223.01; exemption cleared 235.627 -> X3
  - 236.767: D7 yield robot_1 withheld (no shared lane), m3_default with plan -> G2 (T2[D7] False -> not G1)
  - 261.69: nav2 'Failed to make progress'/abort robot_3 (repeated) -> X2
- **Notes.** G5 here is a robot-robot gap during an exempt (waivered) yield; if G5 were read as box-crossing only for exempt pairs, the walk gives X4 at 231.667. ALT[R3]=U:T1_not_run

### EV-f7ab58 FU1: `G4` (step 4)

- **Evidence.** Gate all True. Step 2: chain (rubric) D1:robot_1:backup (D1 dispatched 13.033, t0 14.903); chain_start 13.033; step 3 skipped (T1(t0) U:T1_fidelity not deciding). Walk: D1 analysis yield robot_5 (involved robot_1,robot_5), C2 False; unmatched (V2/V3 untestable). D1 grounding: swap robot_5<->robot_1 ('robot_5 has 0.00 m retreat room < 0.77 m required'), G4_role_change_tags ['yield_robot=regrounded','yield_robot_grounded_from=robot_5'], dispatched robot_1:yield -> G4 at 13.033.
- **Event codes:**
  - 13.033: D1 analysis -> none (V2/V3:U:T1_not_run)
  - 13.033: D1 grounding -> G4
  - 45.167: robot_1 STALE 10.73 s -> X4
  - 47.2: D2 junction_clear (reverse robot_3, yield robot_2) withheld (retreat room) -> V3, G1 (R:robot_1/R:robot_2/R:robot_4 in T1[D2])
  - 55.972: D1:robot_1:backup COMPLETED; robot_2|robot_3, robot_3|robot_4 pinned, non-exempt -> X3
  - 107.597: D3 reverse robot_3,robot_4, no plan (C1 None), waits dispatched and COMPLETED -> X3 (V4j not flagged)
  - 102.933: robot_1 STALE 39.03 s -> X4
  - 110.8: D4 junction_clear reverse robot_2/robot_3 withheld (retreat room) -> V3, G1
  - 129.233: D5 reverse involved robot_1..robot_4, reverse legs robot_2,robot_3 (C1 True); verifier swap robot_2<->robot_4; waits dispatched -> V4, V4j, G4 (V4j: 'allowing robot_4 and robot_1 to eventually pass through')
  - 142.0: D6 junction_clear reverse robot_1/robot_4 withheld (retreat room) -> V3, G1
  - 144.303: stop-rule censor -> X6
- **Notes.** Stop-flag episode. Alt R3: U:T1_not_run at D1. ALT[R3]=U:T1_not_run

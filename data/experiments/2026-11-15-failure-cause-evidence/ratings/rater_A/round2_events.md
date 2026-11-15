# Rater A: Round 2 Re-coding

Rater A, 2026-11-15. The 34 in-scope units from `rater_round2/in_scope_units.json` were re-coded with the round-2 addenda. Every other round-1 reading is kept; the readings new to round 2 are in `ambiguities_round2.md`.

- Units re-coded: 34; changed: 12.
- Primary distribution over all 55 failure units (round-1 codes for out-of-scope units):
  - `U:T1_fidelity` 15
  - `U:no_m4_clock_anchor` 10
  - `X3` 6
  - `V1` 4
  - `G2` 3
  - `G5` 3
  - `G4` 3
  - `X1` 3
  - `V4` 3
  - `V3` 2
  - `X2` 2
  - `X5` 1
- By class: G 9, U 25, V 9, X 12
- Under S3:
  - `G4` 10
  - `U:no_m4_clock_anchor` 10
  - `X3` 7
  - `V1` 5
  - `V3` 3
  - `X2` 3
  - `G2` 3
  - `G5` 3
  - `X1` 3
  - `V4` 3
  - `U:T1_fidelity` 2
  - `X4` 1
  - `X5` 1
  - `G6` 1
- S3 by class: G 17, U 12, V 11, X 15

| Sheet | Unit | Round 1 | Round 2 | S3 | Changed | Step |
|---|---|---|---|---|---|---|
| EV-072a17 | FU1 | `G4` | `V3` | `V3` | True | 4 |
| EV-0bdad6 | FU1 | `G4` | `U:T1_fidelity` | `G4` | True | 7 (deciding T1 at chain-start decision) |
| EV-0bdad6 | FU2 | `U:T1_fidelity` | `U:T1_fidelity` | `V1` | False | 7 (entered from step 3: T1(t0) U:T1_fidelity) |
| EV-295a3e | FU1 | `G4` | `U:T1_fidelity` | `U:T1_fidelity` | True | 7 (deciding T1 at chain-start decision) |
| EV-298037 | FU1 | `U:T1_fidelity` | `U:T1_fidelity` | `X4` | False | 7 (entered from step 3: T1(t0) U:T1_fidelity) |
| EV-298037 | FU2 | `X3` | `X3` | `X3` | False | 4 |
| EV-2c719b | FU2 | `G5` | `G5` | `G5` | False | 4 |
| EV-344706 | FU1 | `G4` | `G4` | `G4` | False | 4 |
| EV-359e3d | FU1 | `X5` | `X5` | `X5` | False | 4 |
| EV-359e3d | FU2 | `X1` | `X1` | `X1` | False | 4 |
| EV-37a70e | FU1 | `G4` | `U:T1_fidelity` | `G4` | True | 7 (deciding T1 at chain-start decision) |
| EV-37a70e | FU2 | `V4` | `V4` | `V4` | False | 4 |
| EV-41a9d4 | FU1 | `X1` | `X1` | `X1` | False | 4 |
| EV-41a9d4 | FU2 | `V1` | `V1` | `V1` | False | 4 |
| EV-52a0c3 | FU1 | `U:T1_fidelity` | `U:T1_fidelity` | `X2` | False | 7 (entered from step 3: T1(t0) U:T1_fidelity) |
| EV-62b8d0 | FU1 | `G4` | `U:T1_fidelity` | `G4` | True | 7 (deciding T1 at chain-start decision) |
| EV-7bda3f | FU1 | `X3` | `X3` | `X3` | False | 4 |
| EV-7bda3f | FU2 | `G4` | `G4` | `G4` | False | 4 |
| EV-7bf1e2 | FU2 | `G4` | `V3` | `V3` | True | 4 |
| EV-80fb2a | FU2 | `G4` | `G4` | `G4` | False | 4 |
| EV-830943 | FU1 | `G6` | `U:T1_fidelity` | `G6` | True | 7 (deciding T1 at chain-start decision) |
| EV-a2cfc5 | FU1 | `X3` | `X3` | `X3` | False | 4 |
| EV-a6761e | FU1 | `G4` | `U:T1_fidelity` | `G4` | True | 7 (deciding T1 at chain-start decision) |
| EV-a6761e | FU2 | `G4` | `U:T1_fidelity` | `G4` | True | 7 (deciding T1 at chain-start decision) |
| EV-cb3996 | FU1 | `G5` | `G5` | `G5` | False | 4 |
| EV-cb3996 | FU2 | `X3` | `X3` | `X3` | False | 4 |
| EV-db0df6 | FU1 | `V4` | `V4` | `V4` | False | 4 |
| EV-db0df6 | FU2 | `V4` | `V4` | `V4` | False | 4 |
| EV-e0f9cf | FU1 | `G4` | `U:T1_fidelity` | `G4` | True | 7 (deciding T1 at chain-start decision) |
| EV-e0f9cf | FU2 | `G4` | `U:T1_fidelity` | `G4` | True | 7 (deciding T1 at chain-start decision) |
| EV-e26384 | FU1 | `U:T1_fidelity` | `U:T1_fidelity` | `X3` | False | 7 (entered from step 3: T1(t0) U:T1_fidelity) |
| EV-ef4e73 | FU1 | `U:T1_fidelity` | `U:T1_fidelity` | `U:T1_fidelity` | False | 7 (entered from step 3: T1(t0) U:T1_fidelity) |
| EV-ef4e73 | FU2 | `G5` | `G5` | `G5` | False | 4 |
| EV-f7ab58 | FU1 | `G4` | `U:T1_fidelity` | `V3` | True | 7 (deciding T1 at chain-start decision) |

## Evidence per Unit

### EV-072a17 FU1: `G4` -> `V3` (S3 `V3`)

- **Evidence.** D1 (chain start, 14.133) new T1 row: as written pass, 140/237 motion. V2: D1 involved [robot_2, robot_5] misses FU robot robot_3, but no robot appears in every motion label -> no V2. V3: D1 named yielder robot_5 was re-grounded away for room ("no retreat candidate surviving the sweep", round-1 A4) and T1[D1] shows robot_2 and robot_3 as yielder under both label readings (R4) -> V3. V3 and G4 on the same decision: V before G.
- **Contributing.** X3, G1, G4
- **Notes.** Round-1 primary G4 came from R3 (V2/V3 untestable); R3 is now moot for D1. D2 row (pass, 38/237): no V2, no refusal.

### EV-0bdad6 FU1: `G4` -> `U:T1_fidelity` (S3 `G4`)

- **Evidence.** D1 (chain start, 12.367) new T1 row: as written U:T1_fidelity (S3 pass, 83/237). D1 involved [robot_1, robot_4] misses FU robot robot_5, so the non-T1 half of V2 holds and the T1 result decides whether V2 fires before the G4 on the same decision -> deciding T1 is U:T1_fidelity (step 7; ambiguity B1).
- **Contributing.** G6, X3, G1, G2, V3, X4, G4
- **Notes.** S3: D1 passes, no robot in every motion label (no V2), no room refusal (no V3) -> G4 as round 1.

### EV-0bdad6 FU2: `U:T1_fidelity` -> `U:T1_fidelity` (S3 `V1`)

- **Evidence.** Onset T1 as written still U:T1_fidelity (episode gate); onset not command-produced. New D8 row: as written pass, T2[D8] False -> G1 not met (round-1 contributing unaffected: G1 was untestable).
- **Contributing.** V1, X2, X4, X5
- **Notes.** S3: onset gate passes (8/8, 29/88 motion) -> step 4 from t0: V1 at t0 (0 matched analyses).

### EV-295a3e FU1: `G4` -> `U:T1_fidelity` (S3 `U:T1_fidelity`)

- **Evidence.** D1 (chain start, 13.8) new row: as written U:T1_fidelity and S3 also U:T1_fidelity. D1 involved [robot_2, robot_3] misses FU robots 1, 4, 5 (V2 non-T1 half) and its named yielder robot_3 was re-grounded for room (V3 non-T1 half) -> deciding T1 result is U:T1_fidelity.
- **Contributing.** X3, X1, G5, EG2, V3, G1, X5, X2, G2, G4
- **Notes.** Unresolved under S3 too (D1 S3 gate differs).

### EV-298037 FU1: `U:T1_fidelity` -> `U:T1_fidelity` (S3 `X4`)

- **Evidence.** Onset as written still U:T1_fidelity (4/5); no new decision row for this unit.
- **Contributing.** X4, V3, G4, X3, G1, G2
- **Notes.** S3: onset gate passes (5/5, 96/237) -> walk from t0: robot_5 STALE 11.27 s at 57.733 -> X4 (round-1 ALT[R1]).

### EV-298037 FU2: `X3` -> `X3` (S3 `X3`)

- **Evidence.** Chain start D2 (22.4) new row: as written U:T1_fidelity, but T1 is not deciding: D2 involved [robot_1, robot_4] equals the FU robots (no V2 non-T1 half) and D2 was dispatched without a room refusal (no V3 non-T1 half). Walk continues as round 1 -> X3 at 71.695. D1 (18.267) row is before the chain start and not walked.
- **Contributing.** V1
- **Notes.** ALT[X3-at-pin-start]=V1 still applies (round-1 A10).

### EV-2c719b FU2: `G5` -> `G5` (S3 `G5`)

- **Evidence.** Chain start D1 (13.233) new row: pass; involved = FU robots, no refusal -> no V2/V3; walk as round 1 -> G5 at 14.667. New D3 row: T2 True -> G1 now testable (withheld, C2 False). New D7 row: named reverser robot_4 refused for room, R:robot_2 in T1[D7] motion -> V3; T2 True -> G1.
- **Contributing.** EG2, X3, G2, V1, X4, G1, V3

### EV-344706 FU1: `G4` -> `G4` (S3 `G4`)

- **Evidence.** Chain start D13 (218.167) new row: pass, 143/237. D13 involved [robot_1, robot_4, robot_3] misses FU robots robot_2, robot_5, but no robot in every motion label -> no V2. Swap reason "robot_4 is off the dynamic lane" is not a room refusal -> no V3. G4 stands.
- **Contributing.** X1, V3, G1, X6

### EV-359e3d FU1: `X5` -> `X5` (S3 `X5`)

- **Evidence.** New D2 row (73.7, after the X5 at 26.47): pass; no V2; D2 substitutions not a room refusal. Primary unchanged.
- **Contributing.** X3, X1, G6, V3, G1

### EV-359e3d FU2: `X1` -> `X1` (S3 `X1`)

- **Evidence.** Chain start D1 (14.0) new row: pass, 30/88. D1 involved [robot_1, robot_4] misses robot_2, but no robot in every motion label -> no V2; no refusal -> no V3. Walk as round 1 -> X1 at 70.695.
- **Contributing.** V4j, X3

### EV-37a70e FU1: `G4` -> `U:T1_fidelity` (S3 `G4`)

- **Evidence.** Chain start D2 (30.0) new row: as written U:T1_fidelity (S3 pass). D2 involved [robot_4, robot_5] misses FU robots robot_2, robot_3 (V2 non-T1 half) -> deciding T1 result U:T1_fidelity.
- **Contributing.** G5, X1, X5, X3, V3, G1, G2, G4
- **Notes.** S3: D2 passes, no V2, no room refusal -> G4 (node_handoff tag) as round 1.

### EV-37a70e FU2: `V4` -> `V4` (S3 `V4`)

- **Evidence.** Chain start D3 (76.3) new row: pass; involved = FU robots (no V2); C1 True -> V4 as round 1 (V4 needs no T1).
- **Contributing.** G6, X3, V1, X4

### EV-41a9d4 FU1: `X1` -> `X1` (S3 `X1`)

- **Evidence.** Chain start D1 (13.2) new row: pass, 22/237. D1 involved [robot_3, robot_4] misses robot_2; no robot in every motion label -> no V2; no refusal. Walk as round 1 -> X1 at 48.913. New D3 row after the primary.
- **Contributing.** V4, G6, X3, G1, G2

### EV-41a9d4 FU2: `V1` -> `V1` (S3 `V1`)

- **Evidence.** Chain start D3 (76.733) new row: pass; D3 involved [robot_1, robot_4] misses robot_5, no robot in every motion label -> no V2; no refusal. V1 at t0 stands. New D4 row: T2 True -> G1 now testable (withheld); no Y labels -> no V3.
- **Contributing.** X3, G2, X4, G1

### EV-52a0c3 FU1: `U:T1_fidelity` -> `U:T1_fidelity` (S3 `X2`)

- **Evidence.** Onset as written still U:T1_fidelity (2/3).
- **Contributing.** X2, G4, X3, V3, G1
- **Notes.** S3: onset gate passes (3/3) -> walk from t0: Nav2 abort robot_1 at 12.189 -> X2.

### EV-62b8d0 FU1: `G4` -> `U:T1_fidelity` (S3 `G4`)

- **Evidence.** Chain start D1 (11.4) new row: as written U:T1_fidelity (S3 pass). D1 involved [robot_1, robot_4] misses FU robots 2, 3, 5 (V2 non-T1 half) -> deciding T1 result U:T1_fidelity. New D2 row (pass): no V2.
- **Contributing.** X1, X3, V4, V4j, G5, EG2, G6, V3, G1, G4
- **Notes.** S3: D1 passes, no V2, no room refusal -> G4 as round 1.

### EV-7bda3f FU1: `X3` -> `X3` (S3 `X3`)

- **Evidence.** New D2 row (27.2, after the X3 at 23.705): pass, T2 True. D2 withheld with named yielders refused for room; robot_3 is yielder under both label readings in T1[D2] -> V3; G1 now testable. Primary unchanged.
- **Contributing.** G2, V3, G1, V4, V4j, G4, G6, X6

### EV-7bda3f FU2: `G4` -> `G4` (S3 `G4`)

- **Evidence.** Chain start D3 (36.567) new row: pass; involved = FU robots; swap reason heading re-grounding, not a room refusal -> no V2/V3. G4 stands. D2 row before chain start.
- **Contributing.** X3, V1, X6

### EV-7bf1e2 FU2: `G4` -> `V3` (S3 `V3`)

- **Evidence.** Chain start D1 (13.767) new row: pass, 13/88. Involved = FU robots (no V2). Named yielder robot_4 re-grounded for room ("no retreat candidate surviving the sweep") and robot_3 is yielder under both label readings in T1[D1] -> V3, before the G4 of the same decision.
- **Contributing.** X3, G2, G1, G4
- **Notes.** Round-1 G4 came from R3.

### EV-80fb2a FU2: `G4` -> `G4` (S3 `G4`)

- **Evidence.** Chain start D4 (133.667) new row: pass; involved = FU robots; no plan, no refusal -> no V2/V3. G4 stands. D3 row (111.0) before chain start.
- **Contributing.** G5, X1, EG2, X3, X2, G2, G1

### EV-830943 FU1: `G6` -> `U:T1_fidelity` (S3 `G6`)

- **Evidence.** Chain start D1 (15.433) new row: as written U:T1_fidelity (S3 pass). D1 involved [robot_1, robot_5] misses FU robots 2, 3, 4 -> deciding T1 result U:T1_fidelity.
- **Contributing.** X3, G2, G1, V4, X2, X1, G6
- **Notes.** S3: D1 passes, no V2, no refusal -> G6 as round 1.

### EV-a2cfc5 FU1: `X3` -> `X3` (S3 `X3`)

- **Evidence.** Chain start D2 (18.5) new row: pass, 69/237. D2 involved [robot_2, robot_4] misses robots 1, 3, 5; no robot in every motion label -> no V2; no refusal. Walk as round 1 -> X3 at 37.829. D1 row before chain start.
- **Contributing.** X1, V3, G2, G1, X4

### EV-a6761e FU1: `G4` -> `U:T1_fidelity` (S3 `G4`)

- **Evidence.** Chain start D1 (12.0) new row: as written U:T1_fidelity (S3 pass). D1 involved [robot_1, robot_4] misses both FU robots robot_2, robot_3 -> deciding T1 result U:T1_fidelity.
- **Contributing.** G6, X3, G2, G1, G4
- **Notes.** S3: D1 passes, no V2, no room refusal -> G4.

### EV-a6761e FU2: `G4` -> `U:T1_fidelity` (S3 `G4`)

- **Evidence.** Chain start D1 (12.0) new row: as written U:T1_fidelity (S3 pass). D1 involved [robot_1, robot_4] misses FU robot robot_5 -> deciding T1 result U:T1_fidelity.
- **Contributing.** G6, X3, V1, G4
- **Notes.** S3: D1 passes, no V2, no V3 -> G4.

### EV-cb3996 FU1: `G5` -> `G5` (S3 `G5`)

- **Evidence.** Chain start D1 (13.4) new row: pass. D1 involved [robot_1..robot_4] misses robot_5; no robot in every motion label -> no V2; no refusal. G5 stands.
- **Contributing.** EG2, X3, X1, V3, G2, G1

### EV-cb3996 FU2: `X3` -> `X3` (S3 `X3`)

- **Evidence.** Chain start D1 (13.4) new row: pass; involves both FU robots; no refusal -> X3 as round 1. New D4 row: T2 True -> G1 now testable; no Y labels -> no V3.
- **Contributing.** X2, G2, G1
- **Notes.** ALT[X3-at-pin-start]=X2 still applies (round-1 A10).

### EV-db0df6 FU1: `V4` -> `V4` (S3 `V4`)

- **Evidence.** Chain start D3 (30.067) new row: pass; involved covers FU robots; C1 True -> V4 as round 1.
- **Contributing.** G4, X3, G2, G1

### EV-db0df6 FU2: `V4` -> `V4` (S3 `V4`)

- **Evidence.** Chain start D4 (49.067) new row: pass; involved = FU robots; C1 True -> V4 as round 1. New D9 row: T2 True -> G1 now testable (withheld, no plan).
- **Contributing.** V4j, G6, X3, G1

### EV-e0f9cf FU1: `G4` -> `U:T1_fidelity` (S3 `G4`)

- **Evidence.** Chain start D1 (13.7) new row: as written U:T1_fidelity (S3 pass). D1 involved [robot_1, robot_5] misses FU robot robot_3 -> deciding T1 result U:T1_fidelity.
- **Contributing.** V1, X1, V6, X6, G4
- **Notes.** S3: D1 passes, no V2; swap reason not a room refusal -> G4.

### EV-e0f9cf FU2: `G4` -> `U:T1_fidelity` (S3 `G4`)

- **Evidence.** Chain start D1 (13.7) new row: as written U:T1_fidelity (S3 pass). D1 involved [robot_1, robot_5] misses FU robots robot_2, robot_4 -> deciding T1 result U:T1_fidelity. D2 row (pass): no V2.
- **Contributing.** X3, G6, G5, X1, V1, X2, V6, X6, G4
- **Notes.** S3: D1 passes, no V2/V3 -> G4.

### EV-e26384 FU1: `U:T1_fidelity` -> `U:T1_fidelity` (S3 `X3`)

- **Evidence.** Onset as written still U:T1_fidelity (3/4).
- **Contributing.** X3, G2, G1, X6
- **Notes.** S3: onset passes (4/4) -> walk from t0: D1 waits COMPLETED 26.235 with pinned pair -> X3.

### EV-ef4e73 FU1: `U:T1_fidelity` -> `U:T1_fidelity` (S3 `U:T1_fidelity`)

- **Evidence.** Onset as written still U:T1_fidelity (3/6); S3 also U:T1_fidelity (4/6). Rows for D1, D3, D4 are off this unit's walk.
- **Contributing.** X3
- **Notes.** Undecided under S3 too.

### EV-ef4e73 FU2: `G5` -> `G5` (S3 `G5`)

- **Evidence.** Chain start D5 (171.7) new row: as written U:T1_fidelity, but not deciding: D5 involved [robot_1, robot_3] equals the FU robots (no V2 non-T1 half) and D5 was dispatched verbatim without refusal (no V3 non-T1 half). Walk as round 1 -> G5 at 175.6. Onset U:T1_fidelity not used (step 3 skipped by chain rule).
- **Contributing.** X4, X3, G2, X2

### EV-f7ab58 FU1: `G4` -> `U:T1_fidelity` (S3 `V3`)

- **Evidence.** Chain start D1 (13.033) new row: as written U:T1_fidelity (S3 pass). D1 involved [robot_1, robot_5] misses FU robots 2, 3, 4 and its named yielder robot_5 was re-grounded for room ("0.00 m retreat room") -> deciding T1 result U:T1_fidelity.
- **Contributing.** X4, V3, G1, X3, V4, V4j, X6, G4
- **Notes.** S3: D1 passes; other FU robots are yielders under both label readings in T1[D1] -> V3 (before the G4 of the same decision).

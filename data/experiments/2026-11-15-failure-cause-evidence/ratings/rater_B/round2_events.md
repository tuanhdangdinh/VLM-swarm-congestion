# Rater B: Round 2 Events Coding

Rater B re-coded only the 34 in-scope units, using the round-1 sheet and the round-2 addendum. Round-1 readings A1-A4 and B1-B16 are kept; the new readings are in `ambiguities_round2.md`. The as-written T1 status governs the primary. S3 is reported beside it and never replaces it.

## Summary

- Units re-coded: 34. Changed: 18.
- All 55 units, round 2: G1 3, G2 1, G4 3, G5 3, U:T1_fidelity 15, U:no_m4_clock_anchor 10, V1 5, V3 2, V4 3, X1 3, X2 3, X3 3, X5 1
- By class: G 10, U 25, V 10, X 10
- All 55 units, under S3: G1 3, G2 1, G4 5, G5 3, G6 4, U:T1_fidelity 2, U:no_m4_clock_anchor 10, V1 6, V3 3, V4 3, X1 4, X2 4, X3 4, X4 1, X5 2
- S3 by class: G 16, U 12, V 12, X 15

## Per Unit

| Sheet | FU | Criteria | Round 1 | Round 2 | Step | S3 | Changed |
|---|---|---|---|---|---|---|---|
| EV-f7ab58 | FU1 | a,b | U:T1_not_run | U:T1_fidelity | 4 + rule-7 U clause | V3 | True |
| EV-ef4e73 | FU2 | a,b | G5 | G5 | 4 | G5 | False |
| EV-ef4e73 | FU1 | b | U:T1_fidelity | U:T1_fidelity | 3 + rule-7 U clause | U:T1_fidelity | False |
| EV-e26384 | FU1 | b | U:T1_fidelity | U:T1_fidelity | 3 + rule-7 U clause | X3 | False |
| EV-e0f9cf | FU2 | a,b | U:T1_not_run | U:T1_fidelity | 4 + rule-7 U clause | G4 | True |
| EV-e0f9cf | FU1 | a,b | U:T1_not_run | U:T1_fidelity | 4 + rule-7 U clause | G4 | True |
| EV-db0df6 | FU2 | a | V4 | V4 | 4 | V4 | False |
| EV-db0df6 | FU1 | a | V4 | V4 | 4 | V4 | False |
| EV-cb3996 | FU2 | a | X2 | X2 | 4 | X2 | False |
| EV-cb3996 | FU1 | a | U:T1_not_run | G5 | 4 | G5 | True |
| EV-a6761e | FU2 | a,b | U:T1_not_run | U:T1_fidelity | 4 + rule-7 U clause | G6 | True |
| EV-a6761e | FU1 | a,b | U:T1_not_run | U:T1_fidelity | 4 + rule-7 U clause | G6 | True |
| EV-a2cfc5 | FU1 | a | U:T1_not_run | X3 | 4 | X3 | True |
| EV-830943 | FU1 | a,b | U:T1_not_run | U:T1_fidelity | 4 + rule-7 U clause | G6 | True |
| EV-80fb2a | FU2 | a | G4 | G4 | 4 | G4 | False |
| EV-7bf1e2 | FU2 | a | U:T1_not_run | V3 | 4 | V3 | True |
| EV-7bda3f | FU2 | a | G4 | G4 | 4 | G4 | False |
| EV-7bda3f | FU1 | a | G1 | G1 | 4 | G1 | False |
| EV-62b8d0 | FU1 | a,b | U:T1_not_run | U:T1_fidelity | 4 + rule-7 U clause | X1 | True |
| EV-52a0c3 | FU1 | b | U:T1_fidelity | U:T1_fidelity | 3 + rule-7 U clause | X2 | False |
| EV-41a9d4 | FU2 | a | U:T1_not_run | V1 | 4 | V1 | True |
| EV-41a9d4 | FU1 | a | U:T1_not_run | X1 | 4 | X1 | True |
| EV-37a70e | FU2 | a,b | V4 | V4 | 4 | V4 | False |
| EV-37a70e | FU1 | a,b | U:T1_not_run | U:T1_fidelity | 4 + rule-7 U clause | X5 | True |
| EV-359e3d | FU2 | a | U:T1_not_run | X1 | 4 | X1 | True |
| EV-359e3d | FU1 | a | X5 | X5 | 4 | X5 | False |
| EV-344706 | FU1 | a | U:T1_not_run | G4 | 4 | G4 | True |
| EV-2c719b | FU2 | a | G5 | G5 | 4 | G5 | False |
| EV-298037 | FU2 | a,b | V1 | V1 | 4 | V1 | False |
| EV-298037 | FU1 | b | U:T1_fidelity | U:T1_fidelity | 3 + rule-7 U clause | X4 | False |
| EV-295a3e | FU1 | a,b | U:T1_not_run | U:T1_fidelity | 4 + rule-7 U clause | U:T1_fidelity | True |
| EV-0bdad6 | FU2 | a,b | U:T1_fidelity | U:T1_fidelity | 3 + rule-7 U clause | V1 | False |
| EV-0bdad6 | FU1 | a,b | U:T1_not_run | U:T1_fidelity | 4 + rule-7 U clause | G6 | True |
| EV-072a17 | FU1 | a | U:T1_not_run | V3 | 4 | V3 | True |

## Evidence

### EV-f7ab58 FU1: U:T1_not_run -> U:T1_fidelity

- Evidence: Walk start D1@13.033. Addendum D1 as written gate U:T1_fidelity (D1 as-written differs); V2 and V3 non-T1 halves met -> U:T1_fidelity.
- S3: V3. S3 D1 pass; must-act empty -> no V2; named yielder robot_5 refused for room (0.00 m) while T1 (S3) shows FU robots robot_1..robot_4 feasible as yielder -> V3 (R2-C).
- Contributing: G4, X4, V3, G1, V4, V4j, X3, X6
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-ef4e73 FU2: G5 -> G5

- Evidence: Walk start D5@171.7. Addendum D5 as written gate U:T1_fidelity, but no non-T1 half of V2/V3 is met (involved = FU, not refused), so T1 does not decide; G5 at 222.31 unchanged.
- S3: G5. S3 D5 pass; no V -> G5.
- Contributing: X4, X3, G2, X2
- Notes: Readings A1-A4, B1-B16 kept.

### EV-ef4e73 FU1: U:T1_fidelity -> U:T1_fidelity

- Evidence: No chain. Step 3: T1(t0) as written U:T1_fidelity (3/6), unchanged. Addendum rows D1/D3/D4 are off this unit's timeline.
- S3: U:T1_fidelity. S3 episode gate also U:T1_fidelity (4/6) -> stays U.
- Contributing: X3
- Notes: Readings A1-A4, B1-B16 kept.

### EV-e26384 FU1: U:T1_fidelity -> U:T1_fidelity

- Evidence: No chain. Step 3: T1(t0) as written U:T1_fidelity (3/4), unchanged.
- S3: X3. S3 episode gate pass (4/4), T1(t0) 7 non-empty -> step 4 from t0: X3 after D1 waits complete 26.235 (B14).
- Contributing: X3, G1, G2, X6
- Notes: Readings A1-A4, B1-B16 kept.

### EV-e0f9cf FU2: U:T1_not_run -> U:T1_fidelity

- Evidence: Walk start D1@13.7. Addendum D1 as written gate U:T1_fidelity; V2 non-T1 half met (involved misses robot_2, robot_4) -> U:T1_fidelity. D2@60.067 as written pass (later).
- S3: G4. S3 D1 pass; no V2/V3 -> G4 on D1.
- Contributing: G4, V1, G6, G5, X1, V6, X2, X3, X6
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-e0f9cf FU1: U:T1_not_run -> U:T1_fidelity

- Evidence: Walk start D1@13.7. Addendum D1 as written gate U:T1_fidelity; V2 non-T1 half met (involved misses robot_3) -> U:T1_fidelity.
- S3: G4. S3 D1 pass; must-act empty -> no V2; handoff re-grounding not a room refusal -> no V3; G4 on D1 (swap, yielder changed).
- Contributing: G4, V1, X1, X3, X6
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-db0df6 FU2: V4 -> V4

- Evidence: Walk start D4@49.067. Addendum D4 as written pass; V4 unchanged. D2/D3 precede the chain start (R2-B).
- S3: V4. Same under S3.
- Contributing: V4j, G6, X3, G1
- Notes: Readings A1-A4, B1-B16 kept.

### EV-db0df6 FU1: V4 -> V4

- Evidence: Walk start D3@30.067. Addendum D3 as written pass; involved covers FU; no V2/V3; V4 (C1 True) unchanged. D1@11.9 and D2@15.833 precede the chain start (R2-B).
- S3: V4. Same under S3.
- Contributing: G4, X3, G1, G2
- Notes: Readings A1-A4, B1-B16 kept.

### EV-cb3996 FU2: X2 -> X2

- Evidence: Walk start D1@13.4. Addendum D1 as written pass; involved = FU; no V. X2 at 32.516 unchanged; D4 later.
- S3: X2. Same under S3.
- Contributing: X3, G1, G2, V3
- Notes: Readings A1-A4, B1-B16 kept.

### EV-cb3996 FU1: U:T1_not_run -> G5

- Evidence: Walk start D1@13.4. Addendum D1 as written pass (47/237); must-act empty -> no V2 (involved misses robot_5); no refusal; grounding clean. Next: D1:robot_4:reverse GT contact rack/NW_west at 22.0 -> G5.
- S3: G5. Same under S3.
- Contributing: EG2, X1, X3, V3, G1, G2
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-a6761e FU2: U:T1_not_run -> U:T1_fidelity

- Evidence: Walk start D1@12.0. Addendum D1 as written gate U:T1_fidelity; V2 non-T1 half met (involved misses robot_5) -> U:T1_fidelity.
- S3: G6. S3 D1 pass; no V2/V3 -> G6 on D1.
- Contributing: G6, V1, X3
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-a6761e FU1: U:T1_not_run -> U:T1_fidelity

- Evidence: Walk start D1@12.0. Addendum D1 as written gate U:T1_fidelity; V2 non-T1 half met (involved misses robot_2, robot_3) -> U:T1_fidelity.
- S3: G6. S3 D1 pass; must-act empty -> no V2; no V3 -> G6 on D1.
- Contributing: G6, X3, G1, G2
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-a2cfc5 FU1: U:T1_not_run -> X3

- Evidence: Walk start D2@18.5. Addendum D2 as written pass (69/237); must-act empty -> no V2 (involved misses robot_1/3/5); no refusal; grounding clean. D1@14.7 precedes chain start (R2-B). Next: X3 at 37.829 after D2:robot_2:reverse completes (B11).
- S3: X3. Same under S3.
- Contributing: V3, G1, G2, X1, X4
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-830943 FU1: U:T1_not_run -> U:T1_fidelity

- Evidence: Walk start D1@15.433. Addendum D1 as written gate U:T1_fidelity; V2 non-T1 half met (involved misses robot_2/3/4) -> U:T1_fidelity.
- S3: G6. S3 D1 pass; must-act empty -> no V2; no refusal -> no V3; first deviation G6 on D1.
- Contributing: G6, X3, G1, G2, V4, X2, X1
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-80fb2a FU2: G4 -> G4

- Evidence: Walk start D4@133.667. Addendum D4 as written pass; involved = FU; plan absent, no refusal -> no V -> G4 unchanged. D3@111.0 precedes the chain start (R2-B).
- S3: G4. Same under S3.
- Contributing: G5, EG2, X1, X2, X3, G1, G2
- Notes: Readings A1-A4, B1-B16 kept.

### EV-7bf1e2 FU2: U:T1_not_run -> V3

- Evidence: Walk start D1@13.767. Addendum D1 as written pass (13/88); FU yielders feasible robot_3, robot_4. Named yielder robot_4 refused ('no retreat candidate surviving the sweep', B9) while T1 shows robot_3 feasible as yielder -> V3 (before G4 on same event).
- S3: V3. Same under S3.
- Contributing: G4, X3, G1, G2
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-7bda3f FU2: G4 -> G4

- Evidence: Walk start D3@36.567. Addendum D3 as written pass; involved = FU; named yielder robot_1 re-grounded by heading, not room -> no V3 -> G4 unchanged. D2@27.2 precedes the chain start (R2-B).
- S3: G4. Same under S3.
- Contributing: X3, V1, X6
- Notes: Readings A1-A4, B1-B16 kept.

### EV-7bda3f FU1: G1 -> G1

- Evidence: No chain; walk from t0 12.277. G1 at D1 14.267 precedes addendum D2@27.2 (as written pass, T2 True) -> unchanged.
- S3: G1. Same under S3.
- Contributing: X3, G2, V3, V4, V4j, G4, G6, X6
- Notes: Readings A1-A4, B1-B16 kept.

### EV-62b8d0 FU1: U:T1_not_run -> U:T1_fidelity

- Evidence: Walk start D1@11.4. Addendum D1 as written gate U:T1_fidelity; V2 non-T1 half met (involved misses robot_2/3/5) -> U:T1_fidelity.
- S3: X1. S3 D1 pass; must-act empty -> no V2; no V3; handoff tag only (B15) -> continue: D1:robot_1:backup FAILED 48.278 -> X1.
- Contributing: X1, X3, V4, V4j, G4, G6, G5, EG2, V3, G1
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-52a0c3 FU1: U:T1_fidelity -> U:T1_fidelity

- Evidence: No chain. Step 3: T1(t0) as written U:T1_fidelity (episode gate 2/3), unchanged.
- S3: X2. S3 episode gate pass (3/3), T1(t0) 71 non-empty -> step 4 from t0: Nav2 abort robot_1 at 12.189 -> X2 (B4).
- Contributing: X2, G4, X3, V3, G1
- Notes: Readings A1-A4, B1-B16 kept.

### EV-41a9d4 FU2: U:T1_not_run -> V1

- Evidence: Walk start D3@76.733. Addendum D3 as written pass (21/88); must-act empty -> no V2 (involved misses robot_5); no refusal; grounding clean. robot_1 STALE span that began 20.733 is not a walk event (B16). Next: V1 at t0 135.073 (B8), before X3 at 157.45.
- S3: V1. Same under S3.
- Contributing: X4, X3, G1, G2
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-41a9d4 FU1: U:T1_not_run -> X1

- Evidence: Walk start D1@13.2. Addendum D1 as written pass (22/237); must-act intersection empty -> no V2 (involved misses robot_2); no refusal -> no V3; grounding clean. Next: D1 legs FAILED 48.913 (deadline) -> X1.
- S3: X1. Same under S3.
- Contributing: V4, G6, X3, G1, G2
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-37a70e FU2: V4 -> V4

- Evidence: Walk start D3@76.3. Addendum D3 as written pass; no V2/V3; V4 (C1 True) unchanged.
- S3: V4. Same under S3.
- Contributing: G6, X3, X4, V1
- Notes: Readings A1-A4, B1-B16 kept.

### EV-37a70e FU1: U:T1_not_run -> U:T1_fidelity

- Evidence: Walk start D2@30.0. Addendum D2 T1 as written gate U:T1_fidelity; V2 non-T1 half met (involved [robot_4, robot_5] misses robot_2, robot_3) -> U:T1_fidelity.
- S3: X5. S3 D2 pass; must-act empty -> no V2; no refusal; handoff tag only (B15) -> continue: robot_2 GT contact obstacle_1 at 35.97 -> X5 (B4).
- Contributing: X5, G5, X1, X3, V3, G1, G2
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-359e3d FU2: U:T1_not_run -> X1

- Evidence: Walk start D1@14.0. Addendum D1 as written pass (30/88); must-act intersection empty -> no V2 (involved misses robot_2); not refused -> no V3; grounding clean. Next deviation: D1:robot_1:backup FAILED 70.695 (deadline) -> X1.
- S3: X1. Same under S3.
- Contributing: X3, G1
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-359e3d FU1: X5 -> X5

- Evidence: No chain; walk from t0 12.27. Addendum D2@73.7 (as written pass, T2 True) lies after the round-1 primary X5 at 26.47, so the primary is unchanged; D2's G1 contributing is confirmed by T2 True.
- S3: X5. Same under S3.
- Contributing: X1, X3, G6, V3, G1
- Notes: Readings A1-A4, B1-B16 kept.

### EV-344706 FU1: U:T1_not_run -> G4

- Evidence: Walk start D13@218.167. Addendum D13 as written pass (143/237); must-act intersection empty -> V2 does not fire although involved misses robot_2/robot_5; named yielder robot_4 re-grounded for lane ('off the dynamic lane'), not room -> no V3. Same event grounding G4 (swap robot_4<->robot_1) -> G4.
- S3: G4. S3 pass, same set -> G4.
- Contributing: X1, X3, V3, G1, X6
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-2c719b FU2: G5 -> G5

- Evidence: Walk start D1@13.233. Addendum D1 as written pass (9/88); involved = FU, no refusal -> no V2/V3. G5 at 27.24 unchanged. D3 now has T2 True (addendum) -> G1 at D3 confirmed as contributing.
- S3: G5. Same under S3.
- Contributing: EG2, X3, G1, G2, X4, V3, V1
- Notes: Readings A1-A4, B1-B16 kept.

### EV-298037 FU2: V1 -> V1

- Evidence: Walk start D2@22.4 (chain). Addendum D2 T1 as written gate U:T1_fidelity, but no non-T1 half of V2/V3 is met (involved = FU, not refused), so T1 does not decide; D2 has no V/G code. D1@18.267 precedes the chain start and is not walked (R2-B). Next: V1 at t0 72.673 (B8), before X3 at 72.97.
- S3: V1. S3 D2 gate pass; must-act empty; no V2/V3 -> V1 unchanged.
- Contributing: X3
- Notes: Readings A1-A4, B1-B16 kept.

### EV-298037 FU1: U:T1_fidelity -> U:T1_fidelity

- Evidence: No chain. Step 3: T1(t0) as written U:T1_fidelity (episode gate 4/5), unchanged.
- S3: X4. S3 episode gate pass (5/5), T1(t0) 96 non-empty -> step 4 from t0: first deviation robot_5 STALE 11.27 s from 57.733 (X4), before D3 at 75.5.
- Contributing: X4, V3, G4, X3, G1, G2
- Notes: Readings A1-A4, B1-B16 kept.

### EV-295a3e FU1: U:T1_not_run -> U:T1_fidelity

- Evidence: Walk start D1@13.8 (chain). Addendum D1 T1 as written gate U:T1_fidelity; V2 and V3 non-T1 halves met -> deciding T1 is U:T1_fidelity.
- S3: U:T1_fidelity. S3 gate at D1 also U:T1_fidelity -> S3 stays U:T1_fidelity.
- Contributing: G4, X3, G5, EG2, X1, X2, V3, G1, X5, G2
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-0bdad6 FU2: U:T1_fidelity -> U:T1_fidelity

- Evidence: No chain. Step 3: T2(t0) False; T1(t0) as written still U:T1_fidelity (episode gate 6/8). Addendum row D8@243.367 (as written pass, T2 False) lies after t0 and is not reached by step 3.
- S3: V1. S3 episode gate pass (8/8), T1(t0) 29 motion non-empty -> continue to step 4 from t0: V1 at t0 (B8); D8 later. STALE/contact spans ongoing at t0 not walk events (B16).
- Contributing: V1, X2, X4, X5
- Notes: Readings A1-A4, B1-B16 kept.

### EV-0bdad6 FU1: U:T1_not_run -> U:T1_fidelity

- Evidence: Walk start D1@12.367 (chain). Addendum D1 T1 as written: gate U:T1_fidelity (83/237). V2's non-T1 half met (involved [robot_1, robot_4] misses robot_5), so the deciding T1 result is U:T1_fidelity (B2 reading).
- S3: G6. S3 gate pass; must-act intersection empty -> no V2; no room refusal -> no V3; first deviation G6 on D1 (verbatim contradicted).
- Contributing: G6, X3, G1, G2, V3, X4
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).

### EV-072a17 FU1: U:T1_not_run -> V3

- Evidence: Walk start D1@14.133 (chain). Addendum D1 T1 as written: gate pass, 140/237 motion; FU yielders feasible robot_2, robot_3, robot_5; must-act intersection empty (no V2). Named yielder robot_5 refused ('no retreat candidate surviving the sweep', B9) while T1 shows robot_2 and robot_3 feasible as yielder -> V3. Tie with G4 on same event -> V first (step 5).
- S3: V3. S3 gate pass, same motion set -> V3.
- Contributing: G4, X3, G1
- Notes: Readings A1-A4, B1-B16 kept. B2 is now answered by the addendum's T1 row; where that row is as-written U:T1_fidelity the rubric's U clause applies (U:T1_fidelity replaces U:T1_not_run).


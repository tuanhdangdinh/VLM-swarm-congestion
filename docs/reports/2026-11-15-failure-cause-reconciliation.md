# Failure-Cause Reconciliation and Interception Table

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: reconciliation of the two finished rating passes (55 failure units, 33 episodes, three strata), sensitivities S1, S2 and S3, rule properties, the interception table for three mechanisms with the stall-abort column recomputed from the committed detector, and the thesis placeholder values.

---

## Scope and Method

- **Governing documents, not edited:**
  - rubric `docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md` section 7, frozen at `b70d925` (verified: the file is unchanged between `b70d925` and this branch's HEAD);
  - rating protocol `docs/reports/2026-11-15-failure-cause-rating-protocol.md`, `b7a3d25`;
  - round-2 note `docs/reports/2026-11-15-failure-cause-rating-round2.md`, `89d9bf3`, `3c1a189`, `8671843`;
  - evidence tool `scripts/failure_cause_evidence.py`, md5 `675f561006afd7d3127ef8490048e394` (round-1 sheets were produced at `6c926768…`; methods note `docs/reports/2026-11-15-failure-cause-evidence-tool.md`), and `scripts/failure_cause_round2_scope.py`, md5 `31474ffa7aed248870801019de66ddde`;
  - stall-abort detector: v7p `fix/m4-stall-abort` at `1016e0b` (tree clean before and after the run), `swarm_execution/stall_abort.py` md5 `2afb5b86492fceec0c0ad6329d9b9b2b`, `scripts/stall_abort_replay.py` md5 `b0c89606bce8815e7794ca686ace071c`, `nav2_adapter.py` md5 `fe031a6237c9a9aeb62f4250bb0eb15f`;
  - guard replays: v7l `92158d3` (outputs already in `replay/`, not rerun).
- **New code:** `scripts/failure_cause_reconcile.py` (`geometry` and `build` subcommands), tests `tests/unit/test_failure_cause_reconcile.py` (24 passing; only this file was run).
- **Outputs:** `data/experiments/2026-11-15-failure-cause-evidence/reconciliation/`: `reconciled_units.json`, `agreement.json`, `interception_by_leg.tsv`, `interception_by_unit.tsv`, `thesis_values.json`, plus `tables.json` (every table below, with the consistency checks), `geometry.json` (S1 pair intervals and S2 recompute) and `stall_abort_replay_1016e0b.tsv`.
- **Read-only.** The md5 of all 367 pre-existing files under the evidence directory (including both raters' files, still untracked) were taken before and after; they are identical. `agreement.json` records the md5 of every rating file. v7n, v7m, v7l and v7p trees are clean.
- **Offline.** No VM, no API call, no push. One Python process at a time.

**Steps.**

1. Each rater's final primary code per unit: the round-2 code for the 34 in-scope units, the round-1 code otherwise. Both raters' 34 round-2 records equal `rater_round2/in_scope_units.json`. Opaque ids were mapped with `key/key.json` only at this step.
2. Agreement on the final codes, by column and stratum, and overall as a rating-quality statistic only. Round-1 agreement is given for comparison.
3. Every disagreement resolved by re-reading the clause. Where the text decides, that code is adopted; where it does not, the code is `U` with the clause named. Both raters' codes are kept in `reconciled_units.json`.
4. Tables per column. Tranche 1 is split into Arm A and Arm B, and the pilots into horizon and stop-rule episodes. Strata are never pooled in a cause table.
5. Sensitivities beside the primary coding, never replacing it.
6. Interception table from `interception/legs.json` (57 legs), joined to the reconciled units.

---

## 1. Unit Set and Phase-1 Check (Verified by Running)

- Both raters coded the same 55 failure units, and these equal the tool's non-parked units.
- Both listed the same 3 parked robots that had finished their tasks (E27A FU2, E30A FU3, E30B FU3), and these equal the tool's flags.
- **Phase 1 (GT fields), 58 GT units compared.** There is no difference between the raters in failure-unit status, T2 at onset, the X3 GT condition, onset, kind, robot set, X5 candidate or EG2 candidate. Every GT onset equals the full sheet's onset for the same unit.
- **Reported class totals, verified from the JSON:**
  - rater A: U 25, X 12, V 9, G 9, EG 0;
  - rater B: U 25, V 10, G 10, X 10, EG 0.

Units per column:

| Column | Episodes | Failure units | Parked robots (not units) |
|---|---|---|---|
| Tranche 1, Arm A (registered) | 5 | 8 | 2 |
| Tranche 1, Arm B (registered, Layer 2 off) | 5 | 10 | 1 |
| ER-2 pilots, horizon | 15 | 25 | 0 |
| ER-2 pilots, stop rule (E10, E17, E23, E24, E25, E26) | 6 | 8 | 0 |
| November takes | 2 | 4 | 0 |

---

## 2. Agreement

Computed on the codes before reconciliation. Kappa is n/a where it is undefined: in Arm B every unit is `U:no_m4_clock_anchor` for both raters. "Code" is the full primary code. "Class" is V, G, X, EG or U. "Determined" is not-U versus U.

**Final codes (round 2 where in scope):**

| Group | Units | Code: agree, raw, kappa | Class: agree, raw, kappa | Determined: agree, raw, kappa | Disagreements | Left U after reconciliation |
|---|---|---|---|---|---|---|
| Tranche 1 Arm A | 8 | 7, 0.875, 0.849 | 7, 0.875, 0.830 | 8, 1.000, 1.000 | 1 | 0 |
| Tranche 1 Arm B | 10 | 10, 1.000, n/a | 10, 1.000, n/a | 10, 1.000, n/a | 0 | 0 |
| Pilots, horizon | 25 | 22, 0.880, 0.861 | 25, 1.000, 1.000 | 25, 1.000, 1.000 | 3 | 2 |
| Pilots, stop rule | 8 | 7, 0.875, 0.810 | 7, 0.875, 0.800 | 8, 1.000, 1.000 | 1 | 0 |
| November takes | 4 | 4, 1.000, 1.000 | 4, 1.000, 1.000 | 4, 1.000, 1.000 | 0 | 0 |
| Stratum: tranche 1 | 18 | 17, 0.944, 0.916 | 17, 0.944, 0.892 | 18, 1.000, 1.000 | 1 | 0 |
| Stratum: pilots | 33 | 29, 0.879, 0.856 | 32, 0.970, 0.959 | 33, 1.000, 1.000 | 4 | 2 |
| All 55 (rating-quality statistic only; no outcome is pooled) | 55 | 50, 0.909, 0.895 | 53, 0.964, 0.948 | 55, 1.000, 1.000 | 5 | 2 |

**Round 1, for comparison:**

| Group | Code: agree, raw, kappa | Class: agree, raw, kappa | Determined: agree, raw, kappa |
|---|---|---|---|
| Tranche 1 Arm A | 5, 0.625, 0.579 | 5, 0.625, 0.520 | 6, 0.750, 0.385 |
| Tranche 1 Arm B | 10, 1.000, n/a | 10, 1.000, n/a | 10, 1.000, n/a |
| Pilots, horizon | 11, 0.440, 0.412 | 14, 0.560, 0.449 | 14, 0.560, 0.149 |
| Pilots, stop rule | 3, 0.375, 0.286 | 3, 0.375, 0.149 | 4, 0.500, 0.158 |
| November takes | 3, 0.750, 0.636 | 3, 0.750, 0.600 | 3, 0.750, 0.500 |
| All 55 | 32, 0.582, 0.551 | 35, 0.636, 0.507 | 37, 0.673, 0.400 |

- **Round-1 disagreements: 23.**
  - 18 are rater A's R3 against rater B's B2. Where the walk started at a decision with no T1 row, A continued the walk and B coded `U:T1_not_run`.
  - Round 2 supplied the missing rows. Both raters then applied the same test (section 3.2), so these 18 converge.
  - The other 5 are the 5 final disagreements below.
- Under S3 the agreement is 45 of 55 on the code, 51 of 55 on the class (kappa 0.902), and 55 of 55 on determined versus not.

---

## 3. Disagreements and Their Resolution

### 3.1 Final Primary Code: 5 Disagreements (3 Decided by the Text, 2 Left U)

| Unit | Rater A (step) | Rater B (step) | Recorded ambiguity | Ruling | Reconciled |
|---|---|---|---|---|---|
| E29A FU2 (tranche 1 A) | X3 (4) | V1 (4) | A: A10, `ALT[X3-at-pin-start]=V1`. B: B4, B8 (V1 at t0) | R-X3T: decided | X3 |
| E7 FU2 (pilot, horizon) | X3 (4) | X2 (4) | A: A10, `ALT[X3-at-pin-start]=X2`. B: B4 (X3 at the later of leg end and pin start) | R-X3T: decided | X3 |
| E26 FU1 (pilot, stop rule) | X3 (4) | G1 (4) | A: R5 (G1 needs a withheld or unpublished command). B: B10 | R-G1W: decided | G1 |
| E12 FU1 (pilot, horizon) | G2 (4) | G1 (4) | A: A2 (pipeline order). B: B13 (lower code number) | R-TIE: not decided | `U:unresolved_tie_order_7.5_step5` |
| E9 FU1 (pilot, horizon) | G2 (4) | G1 (4) | A: A2. B: B13 | R-TIE: not decided | `U:unresolved_tie_order_7.5_step5` |

- **Both raters put E12 FU1 and E9 FU1 in class G.** They differ only on which G code is primary. The protocol's rule ("where the text does not decide between the two readings, the reconciled code is `U`") moves both units to U. They are shown apart from the missing-evidence U codes in every table.
- **Rater B's log has no B8 to B13.** B's `ambiguities.md` goes from B7 to B14, but B's records cite B8 21 times, B9 11, B10 2, B11 6 and B13 4. Their meaning is reconstructed from the record text and is **inferred**:
  - B8: V1 placed at t0;
  - B9: "no retreat candidate surviving the sweep" counts as a refusal for room;
  - B10: G1 for a refusal converted to waits;
  - B11: legs of another unit's command are not this unit's events;
  - B13: within-class ties go to the lower code number.

**Rulings** (clause quoted; full text in `reconciled_units.json`, `rulings`):

- **R-X3T (where X3 sits in time): decided.**
  - 7.1: "Event. Any of: an analysis (decision artifact), a dispatched or withheld command, an M4 primitive terminal status, a Nav2 abort line, an M1 STALE interval, or a GT contact or sub-margin interval from the recompute." Also: "Codes are assigned per event."
  - 7.5 step 4: "a command outcome coded X1-X5 by T3". Step 6: "If that event was a completed command followed by a pinned pair, the code is X3."
  - A pinned-pair interval is not an event in 7.1's list. Steps 4 and 6 attach X3 to the completed command's outcome, so X3 sits at the M4 terminal status (completion).
  - **Rater A's reading.**
    - In E29A FU2 the completion at 71.695 precedes B's V1 at t0 72.673.
    - In E7 FU2 the completion at 29.712 precedes the Nav2 abort at 32.516. The pair became non-exempt 0.03 s after completion and stayed pinned and non-exempt from 38.0 to censoring.
- **R-G1W (a refusal turned into dispatched waits): decided.**
  - G1: "refused a decision that is contract-consistent and T2-feasible".
  - At E26 D1 (14.267) the grounder refused every action of the decision ("reverse refused: both robots outside the corridor on the same side") and substituted waits. C1 is False and T2 at D1 is True.
  - The clause asks for a refusal, not a withheld command. Rater A's "published False" condition is A's R5, not the clause.
  - **Rater B's G1** at 14.267 precedes the X3 at 23.705. Both raters accept the X3 after a completed wait (section 3.2), so the dispute is G1 only.
- **R-TIE (two G codes on one event): not decided.**
  - 7.5 step 5: "If one event carries several codes, the primary is the most upstream: V before G before X. Exception: G5 precedes the X code of the same leg, because the leg itself was unsafe."
  - The clause orders classes, not codes within a class. Rater A's pipeline order and rater B's code-number order are both readings the text does not make.

### 3.2 Interpretation Splits the Raters Flagged (Ruled; No Recoding Where Both Agree)

- **When an as-written `U:T1_fidelity` row "decides" (A's B1, B's R2-A).**
  - Both use the same test: the row decides only when the non-T1 half of V2 (`involved_robots` misses a unit robot) or of V3 (named yielder or reverser refused for room) holds.
  - Both coded the same 10 units `U:T1_fidelity` on this test. Both found the row not deciding in the same 2 units (E29A FU2 at D2, E20 FU2 at D5).
  - Clauses: step 7, "If a deciding T1 result is `U:T1_fidelity` or `U:T1_no_record`, the primary is that U code"; step 4, "an analysis coded V1-V6, judged against T1 at that snapshot: V2 and V3 need T1 non-empty".
  - At an analysis, T1 enters the walk only through V2 and V3, so it can decide only when one of them could fire. Step 6's use of T1 cannot fire there either, because a later passing row is non-empty.
  - **Decided by the text, as both raters applied it.** The alternative (any walked row decides) would move those 2 units to U.
- **Does a completed wait count as "a command completes" for X3 (A's A7, B's B14)?**
  - X3: "after a command completes, a non-exempt pair stays within `min_distance_m` until censoring and both robots are stopped". `temporary_wait` is a dispatched command (7.1 "a dispatched or withheld command"; T3 "for each dispatched leg").
  - The clause does not restrict the kind of command. **Decided: yes**, as both raters coded.
  - The alternative (motion commands only) would move E27A FU1 (X3 to G1) and E23 FU1 (X3 to V3).
  - Placement in time is ruled in R-X3T.
- **Does the tool's X2 input count where the safety-stop spans are unmapped (A's R8/A1, B's B4/B6)?**
  - X2: "Nav2 abort, or no progress for at least 60 sim-s under an active Nav2 goal". 7.1: "wall-clock lines are mapped with the linear fit over `sim_t=` lines in `m4.log`".
  - The 5 Arm B `m4.log` files have no `sim_t=` line, so neither Nav2 abort lines nor safety-stop spans can be placed on the sim clock, and "under an active Nav2 goal" cannot be judged.
  - **Decided: the code is `U:no_m4_clock_anchor`**, as both raters coded. Under the alternative all 10 Arm B units would be X2.
  - On Layer-2-on sheets both raters treat runs that the latch covers (cover fraction 0.9 or more) as not under an active goal. The alternative would make 4 more units X2: E14 FU1, E16 FU2, E8 FU1, E19 FU1 (A's `ALT[R8]`).
  - The clock mapping that failed its criterion stays not applied (see Limits).
- **Rows before the chain start (A's B4, B's R2-B).**
  - Step 2: "the walk starts at the earliest such dispatch ... the walk of step 4 starts there". Step 4: "Walk the FU's events from the start point".
  - **Decided: not walked**, as both raters coded. Whether they carry contributing codes is A8/B16; both exclude point events.
  - The alternative could add V or G codes before the primaries of up to 6 units (B's list). That needs re-rating and was not done.
- **"Swap for room" as "refused for room" for V3 (A's B2; B's B9).**
  - V3: "the named yielder or reverser is refused for room while T1 shows another robot of the FU feasible in that role".
  - The subject is the named robot. A sweep re-grounding whose reason is that the named yielder "has no retreat candidate surviving the sweep" removes that robot from the role for lack of room, even though another robot then yields.
  - **Decided: V3**, as both raters coded in E15 FU1 and E31A FU2. The alternative would keep them G4.
- **Step 3 with onset T1 `U:T1_fidelity` (A's R1, B's B2).** Both coded the 5 units U. With T1 unusable, step 3 can neither exclude nor establish EG1 or G7 (step 7). Rater A's alternative walk gives X4, X2, X3, X3 and V1.

### 3.3 S3 Codes: 10 Disagreements (4 Decided by the Text, 6 Left U)

These are the 5 above, carried into S3 and ruled the same way, plus five that turn on G4.

| Unit | Rater A S3 | Rater B S3 | Ruling | Reconciled S3 |
|---|---|---|---|---|
| E13 FU1 | G4 | X1 | R-G4M: decided (rater A's own note gives X1 under the other reading) | X1 |
| m5D FU1, E21 FU1, E21 FU2 | G4 | G6 | R-G4D: not decided | `U:unresolved_G4_handoff_7.2` |
| E11 FU1 | G4 | X5 | R-S3-37a: not decided | `U:unresolved_G5_placement_S3` |

- **R-G4M.**
  - G4: "roles changed so the dispatch differs from the decision (handoff, rear exemption, swap, robots dropped)".
  - Where the only evidence is a `node_handoff` tag and the dispatch matches the plan (same yielder), the dispatch does not differ, so G4 is not met. This is rater B's B15.
- **R-G4D.** Here the dispatch does differ, but by added waits, with the yielder unchanged. Whether the handoff is the role change that makes it differ is not fixed by the text. If it is, G4 and G6 sit on one event and R-TIE applies.
- **R-S3-37a.** Once G4 falls, rater A's own alternative is G5 (robot_4's backup) and rater B's code is X5 (robot_2's contact at 35.97). Which comes first depends on where G5 sits in time, and neither log settles that the same way. Adopting G5 would take a code neither rater gave as S3.

---

## 4. Reconciled Cause Tables

**Episode-level primary** (rubric 7.5): the primary of the unit with the earliest t0. No onset ties occurred.

### 4.1 Primary Cause by Class: Units (Episodes Whose Episode-Level Primary Is That Class)

| Primary class | Tranche 1 Arm A | Tranche 1 Arm B | Pilots, horizon | Pilots, stop rule | November takes |
|---|---|---|---|---|---|
| Decision (V) | 2 (0) | n/a by construction | 5 (2) | 0 (0) | 2 (1) |
| Grounding and verification (G) | 1 (1) | n/a by construction | 4 (1) | 3 (2) | 0 (0) |
| Execution (X) | 3 (2) | 0 (0) | 7 (4) | 1 (1) | 0 (0) |
| Environment geometry (EG) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| Undetermined (U) | 2 (2) | 10 (5) | 9 (8) | 4 (3) | 2 (1) |
| **All failure units (episodes with a unit)** | 8 (5) | 10 (5) | 25 (15) | 8 (6) | 4 (2) |
| Parked robots, not units | 2 | 1 | 0 | 0 | 0 |

- **Arm B.** It has no V or G codes by construction (rubric 7.6). Its 10 units are undetermined for lack of a clock anchor (`U:no_m4_clock_anchor`), and every unit carries the context code N0.
- **Stop-rule pilots.** The six episodes cut short by the stop rule (E10, E17, E23, E24, E25, E26) are the "stop rule" column. Their units carry X6 as contributing (7.6).
- **Undetermined share.**
  - Tranche 1: 12 of 18 units (Arm A 2 of 8, Arm B 10 of 10).
  - Pilots: 13 of 33.
  - November: 2 of 4.
- **Neutral reading.** No class has the most primary units in both raters' codes and after reconciliation in every stratum with determined units, so no dominant cause is stated.
  - Tranche 1 Arm A: rater A X 3, V 2, G 1; rater B V 3, X 2, G 1; reconciled X 3, V 2, G 1.
  - Pilots: rater A X 9, G 8, V 5; rater B G 9, X 8, V 5; reconciled X 8, G 7, V 5.
  - November: both determined units are V4 and 2 of 4 are undetermined. With four units this is not a finding.

**Each rater's final classes per column** (for the check above):

| Column | Rater A: V / G / X / U | Rater B: V / G / X / U |
|---|---|---|
| Tranche 1 Arm A | 2 / 1 / 3 / 2 | 3 / 1 / 2 / 2 |
| Tranche 1 Arm B | 0 / 0 / 0 / 10 | 0 / 0 / 0 / 10 |
| Pilots, horizon | 5 / 6 / 7 / 7 | 5 / 6 / 7 / 7 |
| Pilots, stop rule | 0 / 2 / 2 / 4 | 0 / 3 / 1 / 4 |
| November takes | 2 / 0 / 0 / 2 | 2 / 0 / 0 / 2 |

### 4.2 Primary Cause by Code (Units)

| Column | Codes |
|---|---|
| Tranche 1 Arm A | X3 2, X2 1, V1 1, V3 1, G2 1, `U:T1_fidelity` 2 |
| Tranche 1 Arm B | `U:no_m4_clock_anchor` 10 |
| Pilots, horizon | X1 3, X3 2, X2 1, X5 1, G5 3, G4 1, V1 3, V3 1, V4 1, `U:T1_fidelity` 7, `U:unresolved_tie_order_7.5_step5` 2 |
| Pilots, stop rule | G4 2, G1 1, X3 1, `U:T1_fidelity` 4 |
| November takes | V4 2, `U:T1_fidelity` 2 |

### 4.3 Undetermined Units by What Is Missing

| U code | Kind | Arm A | Arm B | Horizon | Stop rule | November | Total |
|---|---|---|---|---|---|---|---|
| `U:T1_fidelity` at onset (step 3) | missing evidence: the T1 gate fails as written | 1 | 0 | 2 | 1 | 1 | 5 |
| `U:T1_fidelity` at the chain-start decision (step 4/7) | missing evidence: same gate | 1 | 0 | 5 | 3 | 1 | 10 |
| `U:no_m4_clock_anchor` | missing evidence: no wall-to-sim clock | 0 | 10 | 0 | 0 | 0 | 10 |
| `U:unresolved_tie_order_7.5_step5` | reading unresolved at reconciliation (both raters: class G) | 0 | 0 | 2 | 0 | 0 | 2 |

The onset units are E29A FU1, E20 FU1, E22 FU1, E24 FU1 and m5D FU2. The chain-start units are E28A FU1, E11 FU1, E13 FU1, E18 FU1, E21 FU1/FU2, E10 FU1/FU2, E25 FU1 and m5D FU1.

### 4.4 Contributing Causes (Units Carrying a Code of the Class; Never Summed With the Primaries)

The reconciled contributing set is the intersection: codes both raters recorded on the unit, as primary or contributing, minus the reconciled primary and N0. The union is shown after the slash.

| Class | Tranche 1 Arm A | Tranche 1 Arm B | Pilots, horizon | Pilots, stop rule | November takes |
|---|---|---|---|---|---|
| V | 4 / 4 | n/a by construction | 13 / 15 | 7 / 7 | 3 / 3 |
| G | 5 / 5 | n/a by construction | 20 / 21 | 7 / 7 | 3 / 3 |
| X | 5 / 5 | 0 / 1 | 22 / 23 | 8 / 8 | 4 / 4 |
| EG (EG2 only) | 0 / 0 | 0 / 0 | 5 / 5 | 0 / 0 | 0 / 0 |

- X in the stop-rule column includes X6, which 7.6 adds to every unit open at the stop.
- V includes the free-text flag V4j.
- The one Arm B union entry is an X2 that rater A listed as contributing in E28B FU1.

---

## 5. Sensitivity Analyses (Beside the Primary; Never Replacing It)

### 5.1 S3: T1 With Stored Stage-2 Label and Rebuilt Task Intents (Raters' `s3_primary_code`, Reconciled as in 3.3)

| Class | Tranche 1 Arm A | Tranche 1 Arm B | Pilots, horizon | Pilots, stop rule | November takes |
|---|---|---|---|---|---|
| V | 2 | n/a | 5 | 1 | 3 |
| G | 2 | n/a | 4 | 5 | 0 |
| X | 4 | 0 | 9 | 2 | 0 |
| EG | 0 | 0 | 0 | 0 | 0 |
| U | 0 | 10 | 7 | 0 | 1 |
| Units whose code differs from the primary | 2 | 0 | 5 | 4 | 2 |

- Only 2 units stay `U:T1_fidelity` under S3: E18 FU1 and E20 FU1. These are the episodes whose task-intent rebuild misses live shield choices.
- The horizon U of 7 breaks down as:
  - 2 `U:T1_fidelity`;
  - 2 tie (R-TIE);
  - 2 `U:unresolved_G4_handoff_7.2`;
  - 1 `U:unresolved_G5_placement_S3`.

### 5.2 S1: Persistent-State Chain Rule (Computed Mechanically)

- **Definition, as the protocol states it.**
  - The commanded robot is in the unit.
  - From the end of the command's motion to the unit's onset, it stayed continuously within 0.05 m of one box, or within 0.45 m centre distance of one robot.
  - No later command went to that robot in between.
- **Inputs.**
  - Motion legs (backup, reverse, escort) with their T3 window end; wait legs have no motion end.
  - Box spans: the full sheets' 0.05 m sub-margin spans.
  - Robot pairs: A33 pair intervals recomputed from each bundle's GT with this tree's scorer (`conflicts.pair_intervals`). Bundles were read only; the full sheets do not carry continuous centre distances.
- **Result:** 1 unit of 45 Layer-2-on units changes its link set. In m5D FU2 ({robot_2, robot_3}, t0 240.94), the escort `a15f3fc5:robot_3:escort` is added.
  - The escort was dispatched at 70.93 and its motion ended at 172.05.
  - robot_3 stayed within 0.05 m of `obstacle_2` from 114.74 to censoring.
  - No later command went to robot_3.
  - The unit's walk start would move from t0 (no chain link) to 70.93, so step 3, where the unit is now `U:T1_fidelity`, would be skipped.
  - **No new cause code is assigned.** The change is not mechanical under the rule: the walk from 70.93 needs re-rating.
  - This is the case the protocol's "known consequence" names, and the validation case passes.
- No other Layer-2-on unit gains a link. Arm B dispatches nothing, so S1 is n/a there.

### 5.3 S2: Start-Inside Straight-Move Check (Computed Mechanically)

- **Rule.**
  - A robot that starts inside the required clearance (half-width + 0.05 = 0.14 m) of a box may move along or away from it, never deeper: a step is blocked when its footprint gap is below 0.14 m and below the start gap minus 1e-6 m.
  - Boxes the robot starts clear of block as written.
  - The same rule is applied to the other robots' footprints. This extension is this note's choice; the guard rule (v7l §2.1, `segment_entry_m`) covers boxes only.
  - The as-written branch of the same code reproduces every sheet's T2 result and shortest move at all 233 snapshots (160 round 1, 73 round 2).
- **Result.**
  - 85 of 233 snapshots have a robot starting inside the clearance.
  - T2 changes at **4 snapshots**, all from false to true. The shortest move changes at 36.

| Snapshot | Decision status | Can the unit's code change? |
|---|---|---|
| m5D FU2 t0 | onset | No. Step 3 continues whenever T1 is non-empty, whatever T2 says; T1 is non-empty here. The unit stays `U:T1_fidelity`. |
| m5D FU2 D8 (243.37) | withheld, "no feasible yielder" | Not the primary: the unit is decided at step 3. G1 becomes testable as a contributing code. |
| E20 FU2 D7 (236.77) | withheld, "no shared lane" | Not the primary: the unit's G5 (agreed) comes earlier. G1 becomes testable as a contributing code. |
| E29A FU2 D2 (22.40) | published (chain start) | No. G1 needs a refusal. |

- Units whose primary cause changes under S2: **0** in every column. This is mechanical: S2 changes only T2, T2 enters a primary only through EG1/G7 at step 3 (unreachable, section 6) and through G1, and none of the four changed snapshots precedes its unit's primary deviation as a refused decision.

---

## 6. Properties of the Rule That Shape the Result

- **EG1 and G7 cannot fire at onset.**
  - The as-written T1 motion set is non-empty at all 58 onset snapshots.
  - No EG1 or G7 code appears in either rater's primaries, S3 codes or contributing codes.
  - EG appears only as EG2, contributing in 5 horizon units, because step 4's list has no EG code.
- **V2 never fired.**
  - Of 306 T1 motion rows (round 1, and round 2 both as written and under S3), only 3 have a robot common to every motion label. All three are one-robot onset rows of parked robots, which are not failure units and have no analysis.
  - No failure unit has a robot that "appears in every motion-producing hypothetical".
- **The 60 s chain window.** A command is linked only if it was dispatched within 60 s before onset or was executing at onset. S1 shows 1 unit (m5D FU2) where a robot stayed pinned by an earlier command for longer than that.
- **The fidelity gate.**
  - 15 units are `U:T1_fidelity` as written (5 at onset, 10 at the chain-start decision); 2 remain under S3.
  - Re-grounding fidelity, Layer-2-on episodes: 139 of 154 recorded positive decisions reproduce as written, and 151 with the stage-2 label and task intents. This matches the methods note.
- **No clock anchor in Arm B.** The 10 Arm B units are undetermined because of 7.1's clock rule, not because of what the robots did.

---

## 7. Interception Table

### 7.1 Inputs and Definitions

- **Legs.** The 57 dispatched reverse and escort legs of `interception/legs.json`:
  - tranche 1 Arm A: 3;
  - pilots: 47 (horizon 34, stop rule 13);
  - November: 7.
- **Escort and reverse guards.** These come from the v7l replays already in `replay/`. A guard refuses a whole command, so every leg of a refused command is refused.
- **Stall abort, recomputed.**
  - Committed detector at v7p `1016e0b`, through `scripts/stall_abort_replay.py`, read-only, over all 28 Layer-2-on bundles.
  - The output is **byte-identical to the provisional TSV**: 100 primitives in 25 bundles, 10 fires.
  - No leg's stall-abort value differs from the provisional column.
  - Time to abort, from primitive start, for the 8 fires among the 57 legs:

    | Leg | Episode | Time to abort (sim-s) |
    |---|---|---|
    | `9cf93ebe` r2 | E17 | 9.1 |
    | `c7aeaac1` r4 | E7 | 9.4 |
    | `a15f3fc5` r3 | m5D | 10.9 |
    | `93100ae3` r3 | E6 | 11.1 |
    | `a3bbc017` r3 | E6 | 12.8 |
    | `8bf906be` r5 | E18 | 13.8 |
    | `d374802a` r2 | E12 | 16.6 |
    | `6cf402ed` r3 | E20 | 20.9 |

  - Two more fires are on yield backups outside the 57-leg set: E11 `7a47f2f7` r4 (10.5 s) and E17 `6745a136` r3 (15.5 s).
- **Physical outcome of a leg**, using the guard report's 0.05 m margin (v7l §8.6, criterion fixed before its GT gaps were printed) and the 0.005 m contact threshold:
  - *contact or pinned* (justified): footprint gap ≤ 0.005 m, or the T3 `pinned_on` tag;
  - *sub-margin graze* (justified): gap below 0.05 m;
  - *false positive*: driven to completion with gap ≥ 0.05 m;
  - *untested*: did not complete and touched nothing (the blocked robot never drove far enough, or never drove).
  - For the guards the gap is to boxes only, since they test declared boxes. For the stall abort a robot–robot contact counts too (E20 `6cf402ed` r3 pushing parked robot_1).
  - For the stall abort "untested" is not defined: it judges only a primitive that ran.
- **Blocked and co-refused legs.**
  - In refused reverse commands the guard report's robot-level split counts only blocked legs.
  - This table counts every refused leg and reports the blocked split beside it. The 20 blocked reverse legs give 11 justified (8 contact, 3 graze), 3 untested and 6 false positives, matching v7l §8.6.
  - Co-refused legs whose own path was clear are classed by their own outcome.
- **Linking.**
  - Primary rule: the leg is in the unit's step-2 chain (`legs.json` `fu_rubric_window`, equal to the full sheets' `chain.rubric`).
  - S1: the chain plus the S1 links of section 5.2.
- **Denominator, established from the data.**
  - The Layer-2-on strata hold 28 episodes. 25 dispatched at least one reverse or escort leg.
  - E9, E27A and E30A dispatched only wait legs (2, 17 and 2), and the stall replay emits no primitive for them. No guard or stall abort can act there.
  - The earlier figure "23" counts the October Layer-2-on bundles with such legs; the two November takes add 2.
  - The 5 units of those three episodes count as "no linked leg".
  - Unit denominator: 45 Layer-2-on units (8, 33, 4).

### 7.2 Per Mechanism, Per Stratum (Legs)

Columns: L = refused or aborted legs; J = justified (contact/pinned + graze); F = false positives; UT = untested. P = units with such a linked leg (primary rule); S = the same under S1. ANY is not the sum of the rows.

| Stratum, mechanism | L | J (contact + graze) | F | UT | Blocked split (contact / graze / untested / FP) | Co-refused clear | P | S |
|---|---|---|---|---|---|---|---|---|
| Tranche 1 Arm A (3 legs): any | 0 | 0 | 0 | 0 | — | — | 0 | 0 |
| Pilots (47 legs): escort guard | 1 | 0 | 0 | 1 | 0 / 0 / 1 / 0 | 0 | 0 | 0 |
| Pilots: reverse guard | 29 | 9 (8 + 1) | 15 | 5 | 8 / 1 / 3 / 6 | 11 | 8 | 8 |
| Pilots: stall abort | 7 | 7 (7 + 0) | 0 | n/a | — | — | 4 | 4 |
| Pilots: any of the three | 31 | 10 (9 + 1) | 15 | 6 | — | — | 9 | 9 |
| November (7 legs): escort guard | 1 | 1 (1 + 0) | 0 | 0 | 1 / 0 / 0 / 0 | 0 | 0 | 1 |
| November: reverse guard | 2 | 2 (0 + 2) | 0 | 0 | 0 / 2 / 0 / 0 | 0 | 1 | 1 |
| November: stall abort | 1 | 1 (1 + 0) | 0 | n/a | — | — | 0 | 1 |
| November: any of the three | 3 | 3 (1 + 2) | 0 | 0 | — | — | 1 | 2 |

- **Pilots split by censoring.**
  - Horizon: reverse 24 (J 7, F 12, UT 5), stall 6, escort 1, any 26.
  - Stop rule: reverse 5 (J 2, F 3), stall 1, any 5.
- **Tranche 1 Arm A.** Its 3 legs are the escorts E28A `3c234140`, E29A `14aefebe` and E31A `60afd0c1`. All completed with a gap of 0.16 m or more, and no mechanism acts on them.
- **Reverse-guard false positives.** The 15 completed-with-clearance refused legs in the pilots are 6 blocked legs and 9 co-refused clear legs. The E11 `c417cbff` r5 robot–robot graze (0.015 m) is not a box graze.
- **Overlap.**
  - Caught by two mechanisms (reverse guard and stall abort): `d374802a` r2, `9cf93ebe` r2, `8bf906be` r5, `93100ae3` r3, `a3bbc017` r3, `c7aeaac1` r4.
  - Caught by two mechanisms (escort guard and stall abort): m5D `a15f3fc5` r3.
  - Only the stall abort: E20 `6cf402ed` r3, an escort pushing the parked yielder; the guards cannot see robots.
- **Failed, pinned, stalled or deadline legs that nothing catches (9, all pilots):**
  - 7 escorts with no motion. 5 were never admitted: E10 `63f8d1ce`, E13 `984e3bdf`, E14 `c5a5e687`, E17 `6745a136` r4, E17 `6d37a549` r3. 2 were admitted but never cleared, with no terminal line: E15 `8066f542`, E22 `07da775d`. The stall-abort report lists `63f8d1ce`, `984e3bdf`, `8066f542` and `07da775d` as latch-held.
  - 2 legs that failed latch-held without contact: E17 `150b95a6` r3 (a reverse the guard admits, 0.37 m from boxes) and E18 `56b599af` r3 (escort failed after 1.16 m, 0.37 m from boxes). The stall abort is idle while the latch zeroes the wheels (stall-abort report §6.4).
  - The latch-at-face legs E10 `d5541ff0` r2 and E13 `ea23b1a7` r1 are silent under the stall abort, but the reverse guard refuses them.

### 7.3 Per Failure Unit, Per Stratum

Categories: *intercepted* (a linked leg would be refused or aborted); *linked, none intercepted*; *no linked leg* (no reverse or escort leg among the 57 is linked, so none of these mechanisms applies). Full rows are in `interception_by_unit.tsv`.

| Stratum (units) | Rule | Intercepted (of which with a justified leg) | Linked, none intercepted | No linked leg | None applies (sum) |
|---|---|---|---|---|---|
| Tranche 1 Arm A (8) | primary | 0 (0) | 3 | 5 | 8 |
| Tranche 1 Arm A (8) | S1 | 0 (0) | 3 | 5 | 8 |
| Pilots (33) | primary | 9 (5) | 5 | 19 | 24 |
| Pilots (33) | S1 | 9 (5) | 5 | 19 | 24 |
| November (4) | primary | 1 (1) | 2 | 1 | 3 |
| November (4) | S1 | 2 (2) | 2 | 0 | 2 |

**Intercepted units under the primary rule**, with the linked leg, its outcome and the unit's reconciled class:

| Unit | Class | Linked leg and mechanism | Leg outcome |
|---|---|---|---|
| E12 FU2 | G (G5) | `d374802a` r2: reverse guard and stall abort | contact |
| E6 FU2 | G (G4) | `a3bbc017` r3: reverse guard and stall abort | contact |
| E7 FU1 | G (G5) | `c7aeaac1` r4: reverse guard and stall abort | contact |
| E20 FU2 | G (G5) | `6cf402ed` r3: stall abort only | contact with a robot |
| E10 FU2 | U | `d5541ff0` r2: reverse guard | contact |
| E11 FU2 | V (V4) | `c417cbff`: reverse guard | false positive |
| E7 FU2 | X (X3) | `c7aeaac1` r1, r3: reverse guard | false positive |
| E8 FU1 | X (X3) | `f06c33b3` r2, r4: reverse guard | false positive and untested |
| E16 FU1 | X (X1) | `ede6d209` r3, r4: reverse guard | untested |
| m5V FU2 | V (V4) | `95066420` r4, r5: reverse guard | sub-margin graze ×2 |

- **Under S1**, m5D FU2 (U) is added: `a15f3fc5` r3, escort guard and stall abort, contact.
- **Intercepted units by reconciled class**, primary rule:
  - pilots: G 4, X 3, V 1, U 1;
  - November: V 1.
- **The 19 pilot units with no linked leg** are U 9, X 5, V 3 and G 2.
- **Outside the 57-leg set,** the stall abort also fires on the yield backup E11 `7a47f2f7` r4, which is chain-linked to E11 FU1 (U). That unit counts as "no linked leg" above.

### 7.4 Caveats

- The table says what would have been refused or aborted, not that the scene would then have resolved. A refused reverse becomes an 8 s wait fan-out that changes every later state. That needs live runs.
- The replayed command streams are reconstructed:
  - the guard replays re-ground recorded decisions on a later tree and do not re-ask stage 2;
  - the stall-abort replay regenerates `/cmd_vel` from the primitive's own logic on GT poses.
- October GT has no contact fields (hard-coded empty). Every October contact here is an offline geometric recompute (v7m `b5eaee5`) at 10 Hz.
- The guards cover declared boxes only. Racks and walls that are not declared are invisible to them, and declared walls over-approximate the open arms.
- None of the three mechanisms is validated live as firing. The escort guard was armed in one take and never fired. The reverse guard and the stall abort have not run live.
- Two primitives that made contact but completed would be re-labelled FAILED under the stall abort: E12 `d374802a` r2 and E20 `6cf402ed` r3. The owner accepted this. The original records and outcome fields are preserved and not changed here.

---

## 8. Limits and Disclosures

- **Prior exposure.** The planning session and the rubric author had read earlier diagnoses of some episodes (rubric 5.1, protocol). This reconciliation session read the mechanism reports and all evidence, unblinded, after both raters finished.
- **Rubric 7.8.** Both raters read rubric 7.8, the worked template, which 5.1 says raters are not shown. Its m5D illustration (G5 on the escort) does not match this data under the rule as written: the unit is `U:T1_fidelity`, and only S1 links the escort.
- **Identifiability.** One GT/EV sheet pair (m5D FU2) and the Layer-2-off sheets were identifiable from the protocol and the methods note.
- **Rater A's deviations.** Rater A opened two EV sheets and surveyed EV fields before saving Phase 1 (not revised afterwards). Rater A read methods-note sections that name episodes. Rater B ran one grep across all EV sheets before coding.
- **Dates.** EV sheets carry epoch wall times that date the runs.
- **Round 2 timing.** Round 2 was designed after round-1 codes were seen (round-2 note, disclosures).
- **B's missing log entries.** Rater B's records cite readings B8 to B13 that its ambiguity log does not contain; their meanings above are inferred. Rater B re-coded E29A FU2 from X3 to V1 "at hand-back review" (B's own note).
- **The clock mapping is not applied.** It failed its pre-declared criterion (5 of 28 bundles above 2.0 s against the m4 fit), and the planning-session ruling keeps it unapplied in the primary coding.
  - *Exploratory note, found after seeing results:* against the raw m4 `sim_t=` anchors the scene-log map's maximum error is 0.452 s over 28 bundles. Each failing bundle's excess matches the m4 fit's own residual.
  - This diagnostic was not used for any code here; the 10 Arm B units stay `U:no_m4_clock_anchor`.
- **The rulings are this session's reading of the clause text.** Where a ruling says "decided", another reader could disagree. Every ruling, both raters' codes and the U alternative are kept in `reconciled_units.json`, so the table can be recomputed under another ruling.
- **Size and status.** The counts are small (strata of 10, 21 and 2 episodes). The analysis is exploratory, post hoc and not confirmatory.
- **Original outcome.** The registered pilot's original outcome stands: 0 of 10 tranche-1 episodes complete. No outcome field or historical record was changed.

---

## 9. Thesis Placeholder Values

- `thesis_values.json` maps all 225 placeholder ids of section 11 of the thesis change list (v6d, read-only) to a value and its source row.
- **Filled: 215.** This includes `n/a` where the definition allows it: `TBD-T2-B-K` (kappa undefined), and the three `TBD-T3*-STL-UT` (untested is not defined for the stall abort; reason recorded).
- **Not filled as defined: 10.**
  - `TBD-T1-S1-{A,H,S,N}` and `TBD-R13`: S1 is computed as a change of link set, and assigning a new primary would need re-rating. The record gives the link-set count instead (1, in the November column).
  - `TBD-R23` to `TBD-R27`: these come from the plan-dispatch visibility report, not from this reconciliation.
- `TBD-E01` gives the report path; its commit is added by the follow-up commit.
- The contributing cells use the intersection set (4.4). `TBD-R08` states that no class has the most units in both raters' codes and after reconciliation, giving the undetermined share.
- **Consistency checks, all passing:**
  - row and column sums of Table 4.1, for units and episodes;
  - units per column 8 / 10 / 25 / 8 / 4 = 55;
  - legs per stratum 3 / 47 / 7 = 57;
  - per interception panel, intercepted + linked-none + no-link = total units = Table 4.1 total;
  - J + F + UT = L for every guard and ANY row;
  - ANY at least the largest mechanism row and at most their sum;
  - Arm B has no V or G code, primary or contributing.

---

## 10. Verified and Inferred

| Claim | Status |
|---|---|
| Same 55 units and 3 parked robots for both raters and the tool; Phase 1 identical | verified (run) |
| Agreement, kappa, disagreement lists | verified (run; kappa formula unit-tested) |
| Rulings R-X3T, R-G1W, R-G4M "decided by the text"; R-TIE, R-G4D, R-S3-37a not decided | this session's reading of the clause text |
| Meaning of rater B's B8 to B13 | inferred from B's record text |
| S1 link set (1 unit) and its m5D validation | verified (run; GT read from the bundles) |
| S2: as-written recompute equals all 233 sheet rows; 4 changes; no primary can change | verified (run); "no primary can change" from the walk positions in both raters' records |
| Stall-abort recompute at `1016e0b` equals the provisional column | verified (run; byte-identical TSV) |
| Reverse-guard blocked split equals v7l §8.6 (11 / 3 / 6) | verified (run) |
| Episodes E9, E27A, E30A dispatched no reverse, escort or backup leg | verified (full sheets and replay output) |
| No pre-existing evidence file changed | verified (md5 of 367 files before and after) |

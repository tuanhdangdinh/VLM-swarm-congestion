# Rater B: Ambiguities Log

Rater B, working alone. Sheets were coded in descending id order. Each entry gives the clause, the two readings, the reading chosen and why.

## Phase 1 (GT sheets)

A1. **Parked lone stalls.**
- Rubric 7.1 counts a lone stall as an FU unless the robot is "dwelling at a task node". The protocol says: "Parked robots that finished their last task (flagged on the sheets) are coded as not a failure unit and listed separately."
- Reading 1: the rubric keeps them as FUs. Reading 2: the protocol excludes them.
- Chosen: the protocol (reading 2). The task brief directs it, and the protocol is the application note that binds raters.
- Three units are affected: GT-b92f93 FU3, GT-4f524f FU3, GT-162c10 FU2. They are listed under `parked_finished_not_FU`.

A2. **EG2 timing and what counts as an "undeclared obstacle".**
- Clause (EG2): "an undeclared obstacle (present in the USD or scene builder, absent from `static_obstacles`) is in contact with an FU robot by the recompute." It sets no time window.
- Reading 1: a contact at any time in the episode. Reading 2: only a contact during the FU (at or after t0).
- Chosen: any time (reading 1). The clause has no window. Each contact record carries `relative_to_t0`, so reconciliation can switch to reading 2 mechanically.
- Racks (`rack/*`) are counted as undeclared obstacles because the sheet lists them under `undeclared_builder_boxes`.
- EG2 can never be primary under 7.5 (no step assigns it), so it is contributing or context only.
- Affected: GT-a3cdae FU1 (contact ended before t0), GT-9c8ad7 FU1 (after t0), GT-36197b FU2 (one contact before t0, one spanning it), GT-354e83 FU2 (before t0), GT-00408f FU1 (after t0).

A3. **X5 and X3 at the GT stage.** X5 means "GT contact not attributable to a G5 leg", and X3 means "after a command completes …".
- Both need event information, so Phase 1 records only the GT conditions: `X5_gt_candidates` and `X3_gt_condition`.
- Spans counted as contacts use the sheet's gap ≤ 0.005 m flag. The rubric says < 0.005 m. No listed contact has a minimum gap between 0.005 and 0.0050, so the difference does not matter.

A4. **The GT sheet's FU contact list contains contacts with non-FU robots.** For example, GT-c34011 FU1 lists robot_4|robot_5 while robot_5 is not in FU1. They are recorded as listed. EG2 is set only when the contacting robot is an FU robot.

## Phase 2: decisions settled once, before coding

B1. **Which T1 column governs.**
- Rubric 7.4: "Computed with guards as run, plus a sensitivity column with every guard on (not used for the primary)." Its inputs list does not include M5 intents.
- Chosen: the "as written" column governs every primary. The `+intents` and `all guards on` columns go in notes only.
- This follows protocol "raters use the tool's documented choice": methods item 2 says "The as-written column sets `U:T1_fidelity`", and item 9 says the episode-level gate is used at t0.

B2. **When a T1 that is U or absent is "deciding" (step 7, last sentence, and step 4 "V2 and V3 need T1 non-empty").**
- Two cases arise: (a) the t0 row is `U:T1_fidelity` at step 3; (b) at step 4, the decision that starts the walk is not in `analyses_on_fu`, so it has no T1 row.
- Reading 1 (chosen): T1 is deciding only when the non-T1 half of V2 or V3 is already met on the sheet. That half is: `involved_robots` misses an FU robot (V2), or the named yielder or reverser was refused for room (V3). In that case the primary is `U:T1_not_run`, or `U:T1_fidelity`, and the G or X code of the same event is recorded as contributing. Otherwise the determinable G or X code stands.
- Reading 2: the U clause is a fallback only, used when nothing else fires, so the G or X code on the same event becomes primary.
- Each affected record stores the reading-2 code in `notes` ("alt_reading2: ...") so reconciliation can flip it mechanically.
- Step 3 case: with T1(t0) U, "T1(t0) empty" cannot be decided, so the step cannot assign EG1 or G7.
  - Reading 1: the primary is `U:T1_fidelity` only if T2(t0) is false or T1 is deciding.
  - My choice: step 3 says "If T1(t0) is non-empty, continue to step 4 whatever T2 says." With T1 U, EG1 and G7 can be neither excluded nor established, so T1 is deciding for step 3.
  - Exception: when the episode has no Layer-2 decision at all (arm-B-like sheets), step 3 still applies per 7.6. See B6.

B3. **V2/V3 inputs and the `Y:a>b` labels.**
- V2: "must act (it appears in every motion-producing hypothetical)". This is computed as the intersection of the robot sets named in the as-written motion list.
- V3: "another robot of the FU feasible in that role" is read as follows. A hypothetical in the as-written motion list names that robot as the yielder (last robot in the `Y:` label, since the tool puts the yielder last) or as a reverser (`R:` label).
- Caveat: a label names the hypothetical decision. It does not say which robot moves after regrounding, because motion requires only that at least one FU robot gets a non-refused leg. This reading may therefore over-credit feasibility.

B4. **X-code conventions.**
- **X2:** the sheet's X2 input is used as given (methods item 5). It counts as an X2 event at its `from_rel + 60 s`, the time the 60 s criterion is met, or at `from_rel` for ordering.
  - Concern: the rubric clause says "under an active Nav2 goal". When `safety_stop_cover_fraction` is about 1, M4 cancels Nav2 goals under a latch (methods item 5), so no Nav2 goal was active.
  - Chosen: a run with a cover fraction of 0.9 or more is not X2, because the goal was cancelled by the latch. It is recorded in notes as an "X2 input, latch-covered".
  - Reading 2 (tool input as given) would code X2.
- **X3:** coded on a command whose leg completed (or ended), when afterwards a non-exempt FU pair is in the sheet's X3 GT input until censoring with both robots stopped. Event time is the later of the leg end and `close_and_stopped_from_rel`. Exemption is checked from the exempt changes; `-` means no exempt pair.
- **X4 and X2 on robots that were not commanded.**
  - Step 4 lists "a command outcome coded X1-X5 by T3". X4's own definition covers "a commanded or FU robot", so STALE spans of FU robots are walk events.
  - Chosen: X4 counts as a deviation in the walk for FU robots as well. X2 is handled the same way (subject to the latch rule above).
  - Reading 2 counts only codes attached to command legs.

B5. **The V versus S prefix.**
- Raters do not infer the arm. The V prefix is used unless a sheet states that the arm is scripted, default-plan or echo.
- Where a decision reads as an echo or scripted output, this is noted, but the V prefix is kept.

B6. **Sheets with no decisions.**
- Per 7.6, X codes only, and N0 is contributing.
- Step 1 is not tripped by "absent" decisions when none were made by design. The gate is judged on the sheet's `evidence_gate` flags.
- Wall-clock events (Nav2 abort, safety-stop spans) are `U:no_m4_clock_anchor` (methods item 1).
- Step 3 applies with T1 used only as "a Layer-2 action was available". Rubric 7.6 says T1 "is never used to assign V or G".
  - G7 is a G code, so step 3 can give only EG1 (T2 false and T1 empty) on such sheets.
  - A G7 outcome on a no-decision sheet is treated as not applicable. The rater continues to the X-only walk, and the case is logged.
- The sheet does not state the arm. The no-decision condition is read from the sheet's empty decision list. The arm is not inferred beyond that.

B7. **Stop-flag censoring.** Every open FU on a sheet whose censor reason is `stop_flag` gets X6 as contributing (7.6).

## Phase 2: per-sheet ambiguities

(appended while coding, in descending id order)

B14. **A wait leg completing as the X3 trigger.** X3 says "after a command completes …". Step 4 admits X codes as "a command outcome coded X1-X5 by T3". The methods note (3c) scopes T3 to backup, reverse and escort legs, and wait legs show `t3 None`.
- Chosen: a dispatched `temporary_wait` with an M4 terminal of COMPLETED is a command that completes, so it can trigger X3.
- Reading 2: only T3 legs count.
- Decides EV-478db7 FU1 (X3; would be V3 at D3 70.0) and EV-35eb04 FU1 (X3; would be G1 at D2 32.667). Both are marked medium confidence.
- It also changes the reading-2 alternatives on EV-ef4e73 FU1, EV-e26384 FU1 and EV-072a17 FU2.

B15. **G4 on a handoff tag alone.** Some decisions carry a `node_handoff` tag in `G4_role_change_tags`, but the dispatched yielder or reverser is the same as the decision's.
- Chosen: not G4. Clause G4 needs "roles changed so the dispatch differs from the decision".
- Applied to EV-a6761e FU1 and FU2, EV-62b8d0 FU1 (D1), EV-37a70e FU1 (D2) and EV-0bdad6 FU1 (D1). G6 is coded separately where its flag is set.

B16. **Interval events that began before the walk start.** Examples are a STALE span or a GT contact span still running at the chain-start dispatch or at t0.
- Chosen: an interval is ordered by its start time. One that began before the walk start is not a walk event and is recorded as contributing only.
- Affects the reading-2 alternatives on EV-41a9d4 FU2 and EV-0bdad6 FU2.

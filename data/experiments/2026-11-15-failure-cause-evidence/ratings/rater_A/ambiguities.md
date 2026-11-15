# Rater A: Ambiguities, Fixed Readings and Disclosures

Rater A, 2026-11-15. Rubric section 7 (frozen text, as found in the allowed file), rating protocol, methods-note field definitions and "clauses not applied as written" list.

## Disclosures (procedure deviations and blinding)

- **D1, order deviation.** Before `phase1_gt.json` was written I opened EV sheets: two in full (EV-3233e2, EV-072a17) plus key/field surveys (greps and JSON key counts) over all 33 EV sheets. Phase 1 was computed only from `rater_gt/*/sheet.json` fields, by a tabulation script, and was not revised afterwards.
- **D2, text read beyond the narrowest scope.** I read rubric 7.8 (worked illustrations), which rubric 5.1 lists as not to be shown to raters, although the task brief allowed it as an example. I also read the methods-note sections "Stall-Abort Column", "Limits" and "Verified and Inferred", which name episodes (m5D, E10, E12, E13, E17) and legs. I did not use any of it to code a sheet.
- **D3, blinding leak (episode identity).** Methods-note clause 11 gives the onset 240.94 rel-s and a contact from 114.74 rel-s for a {robot_2, robot_3} unit of a named episode. This matches GT-a74755 FU2 exactly (and therefore one EV sheet). That unit is coded strictly from its sheet. The chain link is taken only from the sheet's `Chain (rubric)` field, with no persistent-pin linking (that is sensitivity S1, computed later by someone else).
- **D4, blinding leak (date).** EV sheets carry `clock.wall_to_sim_fit_m4.wall_span` and `nav2[].wall` epoch values, which reveal run dates. I did not convert or use them.
- **D5.** The listing of `ratings/` showed that a `rater_B` directory exists. Its contents were not opened.

## Fixed Readings (decided before coding any EV sheet, applied uniformly)

Each unit's `notes` field gives the code under the alternative reading where it would differ.

- **R1, step 3 with an unusable T1 at t0.**
  - Clause: "If T1(t0) is non-empty, continue to step 4"; step 7: "If a deciding T1 result is U:T1_fidelity or U:T1_no_record, the primary is that U code". Tool clause 2: "The as-written column sets U:T1_fidelity."
  - Reading A: step 3 gates entry to step 4. With T2(t0) true, T1(t0) decides between G7 and continuing, so it is deciding. If the t0 row's as-written fidelity is not `episode_gate_pass`, the primary is `U:T1_fidelity` (step 3, via step 7).
  - Reading B: step 3 cannot fire, so walk step 4, and use the U code only if nothing fires.
  - **Chosen: A** (step 3 is an explicit gate). B's result is recorded in notes.
  - This applies only when the onset is not command-produced (step 2 did not fire) on a Layer-2-on sheet. On sheets with no decision artifacts (R2), G7 is not applicable by construction. With T2(t0) true, T1 is therefore not deciding and the walk continues.
- **R2, sheets with no decision artifacts.**
  - Evidence: `decision_artifacts: False`, no decisions, no legs, `m4.log` has fewer than 2 `sim_t=` lines, fidelity `unverifiable_in_bundle`.
  - Coded as Layer-2-off under rubric 7.6: step 1 needs no decision artifacts, N0 is contributing, and the walk uses X codes only.
  - Alternative: `U:no_decision_artifacts` at step 1. That holds if the sheet were a Layer-2-on arm with missing artifacts, which the sheet does not distinguish.
- **R3, V2/V3 at an analysis without usable T1 at its own snapshot.**
  - Applies when the analysis is not matched to the FU (no T1 row), or when its T1 row fidelity is not `pass`.
  - Clause: "judged against T1 at that snapshot: V2 and V3 need T1 non-empty".
  - Chosen: V2/V3 are untestable at that event. This is recorded at event level as `V2/V3:U:T1_not_run` or `V2/V3:U:T1_fidelity`. The walk continues with the other codes of that event and later events.
  - Alternative: the primary is that U code.
- **R4, Y-label role order.** No allowed material documents whether `Y:a>b` lists the yielder first or last.
  - V2 uses membership only: every robot named in every as-written motion label.
  - V3 (yield role): another FU robot X counts as feasible as yielder only if motion labels place X as yielder under both readings, that is, some label starting with X and some label ending with X. Otherwise the result is `U:Y_label_order` at event level.
  - V3 (reverse role): `R:X` (a 1-robot reverse of X) in the as-written motion set.
- **R5, G1 and G4.** (The G4 part is superseded by A6.)
  - G1: the decision is refused or withheld (published False with a refusal or withheld reason, or a verifier rejection), no C1/C2/C3 is True, and T2 at that snapshot is True. If T2 was not computed at that snapshot, G1 is untestable (`U:T2_not_run`) and the walk continues.
  - G4: the decision was dispatched, and either `G4_role_change_tags` is non-empty or verifier edits (swap, substitute, drop) left the dispatch different from the decision. A withheld decision cannot be G4.
- **R6, timing of G5 and X5.**
  - G5 is placed at the leg's start (M4 handover). Its condition is the recomputed leg minimum static or robot gap below 0.005 m. The guard-replay verdict is not on the sheets and is not used (tool 3d).
  - X5 is placed at the start of a GT contact span (gap ≤ 0.005 m). It is X5 only when the contact is not within a G5 leg of that robot.
- **R7, X1.** X1 is coded only when `m4_terminal` is FAILED, `ended_by_deadline` is True, or the terminal text says timed out.
  - A leg with terminal None and `not_executed` gets no X1. It is noted as a T3 observation.
  - Yield `backup` legs are read with the methods-note caveat but coded as written.
- **R8, X2.**
  - A Nav2 abort line is X2 at its mapped rel time.
  - For the "no progress for at least 60 sim-s under an active Nav2 goal" branch, the tool input is used: stationary at least 60 s, no M4 leg, task traveling. The tool states that M4 cancels Nav2 goals under a latch, so a run whose `safety_stop_cover_fraction` leaves less than 60 s uncovered is not "under an active Nav2 goal" and is not X2.
  - On sheets whose safety-stop spans are unmapped (`U:no_m4_clock_anchor`), the fraction 0.0 is an artefact. Whether a goal was active is then undetermined (`U:no_m4_clock_anchor`).
  - The X2 run is placed at its `from_rel`.
  - Alternative: every tool X2 input run is X2, whatever the latch coverage.
- **R9, events in the walk.** Every analysis, dispatch, leg, Nav2 line, STALE span (10 s or more) and contact on the FU's timeline counts, including analyses not in `analyses_on_fu`.
  - V1 (an FU-level absence) is placed at t0.
  - Timeline rows before the start point (t0, or the step-2 chain start) are not walked.
- **R10, X3.**
  - Conditions: a dispatched command to an FU robot reaches COMPLETED at time tc (any command kind, including `temporary_wait`, as the clause does not restrict it), and after tc an FU pair from the X3 GT input stays within 0.45 m with both robots stopped until censoring.
  - The pair must not be exempt at tc. The latch exempt changes are used, and `-` means no exemption.
  - X3 is placed at tc.
  - Alternative: only motion commands count.
- **R11, EG2.** EG2 (contact with an undeclared builder box: racks and walls) is not in step 4's V/G/X list, and step 3 names only EG1 and G7. EG2 is therefore recorded as contributing only. The same contact is also X5 if not within a G5 leg.
- **R12, V4j.** This is read only for `reverse` decisions, from justification and reasoning. It is contributing only, and my reading is recorded.
- **R13, X6.** X6 is contributing when `cut_short_stop_rule` is True.
- **R14, parked lone stalls.** Units flagged `finished_all_or_between_tasks_at_censor` are not failure units. They are listed separately with no primary.

## Ambiguities Met While Coding

Each entry gives the sheet and unit, the clause, readings A and B, and the chosen reading with its reason.

- **A1 (all no-decision sheets).** The case is the X2 "under an active Nav2 goal" branch when the safety-stop spans are unmapped. See R8. Coded `U:no_m4_clock_anchor`. Reading B (every tool X2 input counts) gives X2.
- **A2 (EV-0bdad6 FU1, EV-2c719b FU1 and later sheets).** Clause 7.5 step 5: "If one event carries several codes, the primary is the most upstream: V before G before X." The clause does not order two codes of the same class on one event (for example G2 and G1, or G4 and G6).
  - Reading A: pipeline order (parser G3, then verifier G2, then grounder G1/G4, then dispatch comparison G6, then the leg G5).
  - Reading B: code number.
  - Chosen: A, because "upstream" names pipeline position. This only changes the code where G2 and G1 co-occur (B would give G1).
- **A3 (EV-2c719b FU1 D7 and similar).** V3: "the named yielder or reverser is refused for room while T1 shows another robot of the FU feasible in that role."
  - The open question is whether the named robot must itself be an FU robot. Chosen: no (literal reading), so V3 holds when another FU robot is feasible.
  - Affects contributing codes only so far.
- **A4 (V3 with 'no retreat candidate surviving the sweep').** Swap re-grounds and refusals worded "has no retreat candidate surviving the sweep", or "X m retreat room < Y m required", are read as "refused for room". Refusals for "no shared lane", "no declared junction" or "escort_hits_park" are not.
- **A5 (EV-298037 FU2 and other chain-start units).** V1 is an FU-level absence placed at t0 (R9). When a command-produced onset puts an X3 (completed command, pinned pair) before t0, X3 is first. Placing V1 at the walk start would make V1 primary instead.
- **A6 (revises R5 for G4; decided while coding EV-35eb04, applied to all sheets including those already coded).** Clause: "G4 roles changed so the dispatch differs from the decision (handoff, rear exemption, swap, robots dropped)."
  - Reading A: only the listed mechanisms count. These are what the tool's mechanical inputs `G4_role_change_tags` / `G4_robots_dropped` carry: swap, node_handoff, sweep re-grounding, dropped robots.
  - Reading B: any verifier edit (including `substitute` cross->wait or reverse->wait) that leaves the dispatch different from the plan counts.
  - Chosen: A. The parenthesis enumerates the mechanisms, and the protocol says to use the tool's operationalisation, which does not flag substitutions.
  - Effect so far: EV-359e3d FU2 loses a contributing G4. No primary already coded changed.
  - Where B would change a primary, the notes say so.
  - A verifier edit with op `swap` is a listed mechanism, so it counts as G4 even when `G4_role_change_tags` is empty (EV-7bda3f FU1 D5, EV-f7ab58 FU1 D5; contributing only).
- **A7 (R10, X3 after a completed `temporary_wait`).** Clause: "X3 latch pinned: after a command completes, a non-exempt pair stays within min_distance_m until censoring and both robots are stopped."
  - Reading A: any dispatched command, including a wait, counts.
  - Reading B: only motion commands count.
  - Chosen: A, because the clause does not restrict the command kind.
  - This decides primaries where the first deviation is an X3 after a wait (EV-35eb04 FU1, for example). The notes give B's result.
- **A8 (events before the walk start; EV-0bdad6 FU2, EV-41a9d4 FU2, EV-7e1fa5 FU2).** Clause: "Walk the FU's events from the start point ... in time order and stop at the first deviation"; "Contributing codes. Every other code observed on the FU's events."
  - Chosen:
    - Point events before the start point (Nav2 lines, decisions) are not walked and not contributing.
    - Interval events (STALE spans, contact spans) that began before the start point and are still open at it are contributing, but never the first deviation.
  - Alternative: an interval open at the start point is the first deviation. EV-41a9d4 FU2 would then be X4 instead of V1.
- **A9 (EV-e0f9cf).** The question is whether analyses that failed (`backend_failed`, naming no robots) are "the FU's events".
  - The tool's per-FU timeline omits them.
  - Chosen: they are FU events when inside the FU window (V6). This only affects contributing codes there.

- **A10 (X3 timing; EV-298037 FU2, EV-cb3996 FU2).** The clause says "after a command completes, a non-exempt pair stays within min_distance_m until censoring". The question is when to place the X3 event.
  - Chosen: at the command completion.
  - Alternative: at the start of the pinned interval (`close_and_stopped_from_rel`) when that is later than the completion. This flips two primaries: EV-298037 FU2 becomes V1 (pin 72.97 after V1 at t0 72.673), and EV-cb3996 FU2 becomes X2 (Nav2 abort 32.516 before pin 38.0).
  - Tagged `ALT[X3-at-pin-start]` in the notes of every X3 primary.

## Parked-Finished Lone Stalls (Listed Separately, Not Failure Units)

- **Phase 1:** GT-162c10 FU2, GT-4f524f FU3, GT-b92f93 FU3.
- **Phase 2:** EV-133a4a FU3, EV-35eb04 FU2, EV-7e1fa5 FU3.

## Count of Ambiguities

- 14 fixed readings (R1-R14) were decided before coding.
- 10 ambiguities met while coding (A1-A10). A1 and A6 refine R8 and R5, so there are 22 distinct clauses where the rubric text did not fix the code uniquely.

## Most Consequential Readings (for Reconciliation)

1. **R3 (V2/V3 at chain-start decisions without a T1 row).** I continued the walk. Under the alternative, all 14 G4 primaries, and the other chain-start primaries (G5, G6, X1, X3, V1, V4) where V2/V3 were untestable at the chain-start decision, would become `U:T1_not_run`. V4 primaries come from C1 and do not depend on T1.
2. **R8 (X2 "under an active Nav2 goal" vs safety-stop coverage).**
   - Under my reading, all 10 units on no-decision sheets are `U:no_m4_clock_anchor`. Under the alternative they are X2.
   - On Layer-2-on sheets, every X2 input run that starts inside a walk window has coverage of 0.90 or more; runs with coverage 0.0 (EV-0bdad6 FU2, EV-344706 FU1) fall outside the walk windows.
   - Counting every run inside a walk would make X2 the primary of 4 more units: EV-359e3d FU1, EV-b13ac7 FU1, EV-a2cfc5 FU1 and EV-41a9d4 FU2 (tagged `ALT[R8]` in the notes).
3. **R1 (T1(t0) as written `U:T1_fidelity` with a non-command onset).** I coded this U at step 3 for 5 units. The walk alternative gives X4, X2, X3, X3 and V1 respectively (see each unit's notes).

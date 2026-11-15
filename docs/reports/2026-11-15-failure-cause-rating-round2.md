# Failure-Cause Rating, Round 2 (Added Evidence and Scope)

**Prepared:** 2026-11-15

**Revision history:**

- Initial version (pre-declaration): written and committed before the round-2 evidence was generated and before any round-2 coding. It fixes the purpose, the evidence to be added and how, the clock-mapping method and its acceptance tolerance, the scope rule, the instruction to raters and sensitivity S3. Results (counts, validation numbers, the in-scope unit list) are added in a later dated revision line; nothing in this version is changed by that revision except where a revision line says so.

---

## Why a Second Round Exists

- Round 1 coded 55 units on 33 events sheets. Many units were coded `U` because evidence that the frozen rule needs was not on the sheets. This is missing evidence, found by round 1. It is not a rule change.
- The rubric (`docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md` section 7, frozen at `b70d925`) and the rating protocol (`docs/reports/2026-11-15-failure-cause-rating-protocol.md`, `b7a3d25`) are not edited. No round-1 sheet or code is edited; round-1 codes are kept and reported.
- Three gaps were found:
  1. **T1 at a decision the walk reaches.** The chain rule (7.5 step 2) can start the walk at a dispatched decision before the unit's onset, and step 4 then judges that decision against "T1 at that snapshot". Round 1 ran T1 only at the onset snapshot and at analyses A33 matched to the unit, so such decisions had no T1 row.
  2. **T1 fidelity at onset.** Where the rubric's listed inputs do not reproduce the recorded commands, T1 at onset is `U:T1_fidelity` as written. The methods note shows most reproduce once the stored stage-2 label and rebuilt task intents are added. That second result was on the sheets only as a column, not as a separately labelled, separately gated result.
  3. **No clock anchor on the no-decision sheets.** Safety-stop spans and Nav2 abort lines carry wall-clock stamps only. Rubric 7.1 maps them with the fit over `sim_t=` lines in `m4.log`, and those sheets' `m4.log` files have none (nothing was dispatched). The X2 condition "under an active Nav2 goal" (and the cover fraction the tool reports with the X2 input) could not be decided.

## What Evidence Is Added, and How

All of it is computed by `scripts/failure_cause_evidence.py` (new `round2` subcommand), with the same code trees as round 1 (A33 scorer in this tree, T1 grounder v7n `a412949`, contact geometry v7m `b5eaee5`, each asserted at start-up), and written only to new directories:

- `data/experiments/2026-11-15-failure-cause-evidence/rater_round2/EV-*/addendum.{json,md}` (rater-facing; same opaque EV ids and the same `D1…Dn` decision ids and unit ids as the round-1 sheets; same leak check);
- `data/experiments/2026-11-15-failure-cause-evidence/full_round2/` (unblinded; reconciliation only; raters must not open it).

The round-2 code never reads anything under `ratings/`. Only the scope step below reads the raters' round-1 records.

**Item 1, T1 at decision snapshots.** For every unit and every recorded decision with a dispatched or withheld command that touches the unit's robots and lies on the unit's timeline (from the earlier of its chain start and 60 s before t0, to censoring), and that had no T1 row in round 1, T1 is computed at that decision's own snapshot exactly as round 1 did for matched analyses: H over the unit's robots plus the two nearest others, the decision's own `grounding_params_source.params`, the bundle's geometry and static obstacles, the snapshot goals; variants as written, with task intents, and every guard on. The gate is that decision's own reproduce check (round-1 vocabulary: `pass`, `U:T1_fidelity`, `U:T1_no_record`). T2 is computed at the same snapshot (G1 needs "T2-feasible" at the decision). A regression check recomputes round-1 rows and requires them to equal the round-1 sheets.

**Item 2, T1 fidelity both ways.** Every T1 row in the addendum carries two separately labelled results:

- **As written** (the inputs rubric 7.4 lists): reproduce status and the T1 motion set. This is the result the rubric's text licenses, and it governs the primary coding.
- **S3: with stored stage-2 label and rebuilt task intents.** Reproduce check of the recorded decision with its stored stage-2 label and the M5 task intents rebuilt from `tasks_*.jsonl`, and the T1 motion set with task intents. Hypothetical decisions have no stage-2 label of their own (the label belongs to the recorded decision), so the S3 motion set is the task-intent variant, gated by the S3 reproduce check. At onset the gate stays episode-level, as in round 1 (methods note, clause 9).

The two are never merged.

**Item 3, clock anchor for the no-decision sheets.** Method, declared before any validation number was computed:

- Anchors: the M1 scene log `m5_scene.jsonl`, whose rows carry the scene stamp (M1/ROS sim time) and the M5 monotonic time `t` at which the row was written. `t` is converted to the epoch clock of the ROS log lines with one per-bundle offset: the median, over task-stream events, of the `m5.log` line's epoch stamp minus the same event's `wall_t` in `tasks_*.jsonl` (the spread is reported).
- Mapping: piecewise-linear interpolation over those anchors (stamps strictly increasing; no extrapolation outside the anchor span; an event outside it stays unmapped). A single line is reported beside it, not used.
- Validation: the identical code path on every bundle that has `sim_t=` lines in `m4.log`. Reported: the difference to the rubric's m4 single fit at each m4 anchor's wall time (max and median absolute, and signed median), and the difference to the raw m4 `sim_t=` anchor values.
- **Tolerance: 2.0 sim-s maximum absolute difference to the m4 single fit, at every m4 anchor of every validation bundle.** Reason: 2.0 s is the finest timing parameter that applies to wall-mapped events (A33 `merge_gap_s` 2.0 s; the tool joins safety-stop lines into spans at gaps of 2.0 s); the rubric's own reference fit already has residuals up to 1.9 s; the windows that decide X2 (60 s) and the chain rule (60 s) are far wider.
- If the tolerance is met, the mapping is applied to the no-decision sheets only: mapped safety-stop spans, Nav2 abort times, and the X2 input recomputed with mapped spans (its cover fraction supersedes the round-1 value of 0.0, which was an artefact of unmapped spans). Sheets that already have the m4 fit keep it. If the tolerance is not met, nothing is mapped and those units stay `U:no_m4_clock_anchor`.
- This mapping is a tool choice in the sense of the methods note's "clauses not applied mechanically as written": rubric 7.1 names only the m4 fit.

## Round-2 Scope (Defined by the Evidence, Identically for Both Raters)

A unit is in scope for round 2 if, under either rater's round-1 record, the rule's walk for that unit passes a decision or snapshot for which round 1 lacked evidence that the addendum now supplies:

- **(a)** the walk start or a walked event is a dispatched (or withheld) decision that had no T1 row in round 1 and now has one;
- **(b)** T1 at onset was `U:T1_fidelity` as written (primary coding still uses the as-written status; S3 is sensitivity only);
- **(c)** the unit is on a sheet whose safety-stop and Nav2 times had no clock mapping, if and only if the validated mapping is applied.

The list is produced mechanically from the addendum and both raters' recorded walk starts and walked decisions, and written to `rater_round2/in_scope_units.json` (sheet id, unit id, which of (a)/(b)/(c)). Units not in scope keep their round-1 codes untouched. A round-1 code, `U` or not, does not by itself put a unit in scope or keep it out.

## Instruction to Raters for Round 2

- Re-code only the units listed in `rater_round2/in_scope_units.json`.
- For each, re-apply the same frozen rule (rubric section 7 and the protocol) from the first step the added evidence affects, using the round-1 sheet plus the addendum. Do not change readings you settled in round 1 (your ambiguity log) unless the added evidence makes a reading moot; record any such case.
- Record the round-2 code beside the round-1 code. Round-1 codes are kept and reported.
- A unit stays `U` if the added evidence does not decide it. Name the evidence that is still missing.
- The as-written T1 status governs the primary coding. Where it is `U:T1_fidelity`, the rubric's U clause applies as in round 1.
- **S3** (T1 with stored stage-2 label and rebuilt task intents) is declared here, post-freeze, before raters see it. Report the S3 code beside the primary coding; it never replaces it.
- Raters still do not open `key/`, `full/`, `full_round2/`, `interception/`, `replay/` or the other rater's output.

## Known Round-1 Facts (from the Raters' Hand-backs; Verified Against Their Files in a Later Revision)

- Rater A coded 15 of 55 units `U`; rater B 33 of 55. Both coded the same 10 units on the no-decision sheets `U:no_m4_clock_anchor`, and both have the same V totals (V1 4, V4 3).
- The raters resolved the missing-T1 gap in opposite ways. Rater B, where the walk starts at a dispatched decision with no T1 row and the non-T1 half of V2/V3 is met, coded `U:T1_not_run`. Rater A treated V2/V3 as untestable there and continued the walk, which produced step-4 primaries (including its G4 codes) and recorded the alternative in `ALT[...]` tags. The missing evidence can therefore change non-U codes as well as U codes, which is why scope is defined by the evidence and not by the round-1 code.
- Two further interpretation splits are left to reconciliation, not to round 2:
  - X3, "after a command completes, a non-exempt pair stays within `min_distance_m` until censoring and both robots are stopped": whether a completed `temporary_wait` leg counts as "a command completes", and where X3 is placed in time.
  - X2, "Nav2 abort, or no progress for at least 60 sim-s under an active Nav2 goal": whether the tool's X2 input counts when the safety-stop spans it is judged against are unmapped. If the clock mapping is applied, the mapped cover fraction is new evidence for that question, not a ruling on it.

## Procedure and Blinding Deviations (Disclosed)

- Both raters read rubric section 7.8 (the worked template), which section 5.1 says raters are not shown.
- The protocol and the methods note let one episode's GT/EV sheet pair and the no-decision (Layer-2-off) sheets be identified.
- Rater A opened two EV sheets and surveyed EV fields before saving Phase 1; Phase 1 was not revised afterwards.
- Rater A read methods-note sections that name episodes.
- EV sheets carry epoch wall times that date the runs (already disclosed in the methods note).
- Rater B ran one grep across all EV sheets before coding.
- **Round 2 itself.** Round 2 happens after round-1 codes were seen. The planning session saw rater B's codes; the session that generated the addendum read rater B's ambiguity log and events records to find the missing evidence before generating it. Rater A's output was not read before the addendum was generated; it was read afterwards, with the coordinator's permission, only to build the in-scope list and to verify the facts above. The evidence code reads no rating file.

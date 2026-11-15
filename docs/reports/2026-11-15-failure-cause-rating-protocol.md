# Failure-Cause Rating Protocol (Application Notes)

**Prepared:** 2026-11-15

**Revision history:**

- Initial version: committed before any rating pass started.

---

## Purpose

This note fixes how the two rating passes apply the frozen rubric
(`docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md`, commit `b70d925`
on `demo/campaign-kits`, section 7). The rubric text is not changed. The note
was written after the evidence tool ran and reported which clauses cannot be
applied exactly as written
(`docs/reports/2026-11-15-failure-cause-evidence-tool.md`). It was written
before any episode was coded, by the planning session, which had read earlier
diagnoses of some episodes. That is a limit of this exercise and is disclosed
here.

## Primary Coding

- Raters apply rubric section 7 as written, using only the rater sheets under
  `data/experiments/2026-11-15-failure-cause-evidence/rater_gt/` and
  `rater/`.
- Where the evidence tool had to choose an interpretation (methods note,
  section on clauses not applicable as written), raters use the tool's
  documented choice and do not substitute their own.
- Order: each rater codes the ground-truth fields from the `rater_gt` sheets
  first and saves them, then opens the `rater` events sheets.
- Raters must not open `key/`, `full/`, `interception/`, `replay/`, any report
  under `docs/reports/` other than the rubric and this note, any bundle, or
  the other rater's output.
- A code of `U` (undetermined) names the missing evidence. Raters do not guess.
- Parked robots that finished their last task (flagged on the sheets) are
  coded as not a failure unit and listed separately.
- Strata stay separate in every table: registered prereg-v3 tranche 1
  (10 episodes), ER-2 pilots (21), November takes (2). Nothing is pooled.

## Known Consequences of Applying the Rubric as Written

These are reported with the results, not corrected in the primary coding.

- The substitution set T1 is never empty at onset in this data, so the
  geometry code EG1 and the no-strategy code G7 cannot fire at onset.
- The chain rule's 60 sim-s window does not link a command to a unit when the
  robot stayed pinned for longer than 60 s before the unit's onset. The
  rubric's own illustration (`m5D_t01_a1`, escort of robot_3) is such a case.
- The straight-move check T2 fails at the start pose when a robot already
  stands inside the required clearance.

## Pre-declared Sensitivity Analyses

Declared here before rating, labelled post-freeze, reported beside the primary
coding and never replacing it.

- **S1, persistent-state chain rule.** A command is also linked to a unit when
  the commanded robot is in the unit and, from the end of the command's motion
  to the unit's onset, the robot stayed continuously within 0.05 m of the same
  box or within 0.45 m centre distance of the same robot, with no later
  command to that robot in between. The reconciliation step computes S1
  mechanically from the full sheets after both raters have finished.
- **S2, start-inside straight-move check.** T2 is recomputed with the rule the
  obstacle guards use: a robot that starts inside the clearance may move along
  or away from the box, never deeper. Computed mechanically by the tool.

## Reconciliation

- A third pass compares the two raters' codes after both are final: raw
  agreement and Cohen's kappa on the primary cause, by stratum and overall,
  with every disagreement listed.
- Disagreements are resolved by re-reading the rubric clause, with the
  resolution and its reason recorded. Unresolved cases stay `U`.
- Only after reconciliation are opaque ids mapped back with `key/key.json`,
  and the interception table joined.

## Interception Table

- Built from `interception/legs.tsv` after reconciliation: for each failure
  unit, whether a dispatched leg linked to it (primary rule, and S1) would
  have been refused by the escort or reverse obstacle guard, or aborted by the
  stall abort, with the physical outcome of the leg.
- The stall-abort column is recomputed from the committed detector on
  `fix/m4-stall-abort` (commit `1016e0b` or later). Earlier values are
  provisional.
- The table states what would have been intercepted, not that the scene would
  then have resolved. That needs live runs.
- Original outcome fields and historical records are not changed.

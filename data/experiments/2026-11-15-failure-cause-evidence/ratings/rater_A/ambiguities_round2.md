# Rater A: Round-2 Ambiguities

Rater A, 2026-11-15. The round-1 files (`ambiguities.md`, `phase1_gt.json`, `phase2_events.*`) are unchanged.

## Readings Made Moot or Replaced by the New Evidence

- **R3 is replaced.** Every chain-start decision the walk reaches now has a T1 row. V2/V3 are applied to that row as the rubric states them, as instructed.
- **R1 is unchanged.** At onset, an as-written `U:T1_fidelity` still gives `U:T1_fidelity` when the onset is not command-produced. The S3 column carries the walk result.
- **Earlier "G1 untestable" notes.** Where a new row supplies T2 at a withheld decision (EV-2c719b FU2 D3/D7, EV-41a9d4 FU2 D4, EV-cb3996 FU2 D4, EV-db0df6 FU2 D9, EV-7bda3f FU1 D2), G1 is now tested. It is added as contributing when T2 is True. At EV-0bdad6 FU2 D8, T2 is False, so G1 is not met.
- **All other round-1 readings are kept** (R2, R4–R14, A1–A10).

## New Ambiguities

- **B1 (most consequential; 10 units). When is an as-written `U:T1_fidelity` row at a chain-start decision "deciding"?**
  - Clause, step 7: "If a deciding T1 result is `U:T1_fidelity` or `U:T1_no_record`, the primary is that U code."
  - Clause, step 4: "V2 and V3 need T1 non-empty."
  - Reading A (chosen): the row decides only if the non-T1 half of V2 or V3 holds at that decision. For V2, `involved_robots` misses an FU robot. For V3, the named yielder or reverser was refused or re-grounded for room (round-1 A4). Then V2/V3 could fire and pre-empt the same decision's G code, so the primary is `U:T1_fidelity`.
    - If neither half holds, the row cannot change the outcome and the walk continues as in round 1.
    - Units that became U under A: EV-0bdad6 FU1, EV-295a3e FU1, EV-37a70e FU1, EV-62b8d0 FU1, EV-830943 FU1, EV-a6761e FU1/FU2, EV-e0f9cf FU1/FU2, EV-f7ab58 FU1.
    - Units where the row was not deciding: EV-298037 FU2, EV-ef4e73 FU2.
  - Reading B: any as-written `U:T1_fidelity` row at a walked decision makes the primary U. EV-298037 FU2 (X3) and EV-ef4e73 FU2 (G5) would also become `U:T1_fidelity`.
  - Reading C: the motion set is reported even when the gate fails. In every such row no robot appears in all motion labels, so V2 could be judged false from it and the round-1 codes kept. I rejected C because the rubric makes the gate a precondition for using T1.
- **B2 (V3 at a chain-start swap).** Round-1 A4 treats a sweep re-grounding ("no retreat candidate surviving the sweep", "X m retreat room") as "refused for room". With T1 rows now present, this makes V3 the primary in EV-072a17 FU1 and EV-7bf1e2 FU2. In both, the other FU robot is a yielder under both label readings (R4). Under S3 the same holds for EV-f7ab58 FU1.
  - Alternative: a swap that still dispatches a yield is a re-assignment, not a refusal. These would then stay G4.
- **B3 (S3 for units without an onset fidelity problem).** In units where the round-2 primary is not U and no walked row differs under S3, `s3_primary_code` equals the round-2 primary. This holds wherever the S3 motion sets equal the as-written ones, which they do at every new row.
- **B4 (off-walk rows).** Rows supplied for decisions before a unit's walk start (marked off the walk) were not used, per the chain rule and round-1 A8.

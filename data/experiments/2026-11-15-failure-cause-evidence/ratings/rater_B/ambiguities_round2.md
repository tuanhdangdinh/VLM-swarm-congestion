# Rater B: Round 2 Ambiguities

Round-1 readings A1-A4 and B1-B16 (`ambiguities.md`) are kept unchanged. This file adds only what round 2 raised.

R2-A. **What happens to B2 once the T1 row exists.**
- Round 1's `U:T1_not_run` code is now moot in all 18 units where it was used. Each walk-start decision now has a T1 row.
- B2's test is kept: T1 decides the code only if the non-T1 half of V2 or V3 is met.
  - Row as written `pass`: V2 and V3 are applied to its motion set.
  - Row as written `U:T1_fidelity`: the rubric's U clause gives `U:T1_fidelity`. This happened in 10 units.
- Where the non-T1 half is not met, an as-written `U:T1_fidelity` row does not decide the code, and the walk continues. This applies to EV-298037 FU2 (D2) and EV-ef4e73 FU2 (D5).
- Reading 2: any walked decision whose row is `U:T1_fidelity` makes the unit U. That would move those 2 units to U as well.

R2-B. **Addendum rows marked "on the unit timeline" that come before the chain-start dispatch.** Examples: EV-298037 FU2 D1, EV-a2cfc5 FU1 D1, EV-7bda3f FU2 D2, EV-db0df6 FU1 D1/D2, EV-db0df6 FU2 D2/D3, EV-80fb2a FU2 D3.
- Chosen: not walked. Step 2 says "the walk of step 4 starts there", meaning at the earliest qualifying dispatch, so earlier decisions are not judged. The addendum's timeline (from 60 s before t0) is wider than the walk.
- Reading 2: walk the whole timeline. That could add V or G codes before the current primaries.
- Most consequential new reading: it decides whether 6 units keep their codes.

R2-C. **V3 when the named yielder is not a robot of the FU.** In EV-f7ab58 FU1 D1 the named yielder (robot_5) is outside the FU, and T1 shows FU robots feasible as yielder.
- Chosen: V3 applies. The clause requires only that "another robot of the FU" is feasible in the role.
- This affects only the S3 column. The as-written code is `U:T1_fidelity`.

R2-D. **V2 never fires.** In every new as-written and S3 row, the intersection of robot sets across all motion hypotheticals is empty, so no robot "appears in every motion-producing hypothetical". Applied literally, the V2 clause therefore cannot fire in this data.
- I applied it literally and did not substitute a weaker test.

R2-E. **S3 at onset for units decided at step 3 (criterion b).** Where the S3 episode gate passes, the S3 code comes from continuing to step 4 from t0. I used the round-1 conventions (B4, B8, B14, B16) and the addendum rows for decisions reached in the walk.
- EV-ef4e73 FU1 stays `U:T1_fidelity` under S3, because its S3 gate also fails.

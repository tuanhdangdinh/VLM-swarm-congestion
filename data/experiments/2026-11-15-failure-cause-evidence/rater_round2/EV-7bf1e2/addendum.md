# Round-2 Addendum EV-7bf1e2

- New evidence only; the round-1 sheet is unchanged. Unit and decision ids are those of the round-1 sheet.
- As written governs the primary coding; S3 is a post-freeze sensitivity input.

## FU1

- No new evidence for this unit.

## FU2

### D1 at 13.767 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list True
- Candidates: ['robot_3', 'robot_4', 'robot_5', 'robot_1']
- **As written:** gate pass; T1 13/88 motion (errors 0); motion set ['Y:robot_3>robot_4', 'Y:robot_4>robot_3', 'Y:robot_3>robot_1>robot_4', 'Y:robot_3>robot_4>robot_1', 'Y:robot_3>robot_4>robot_5', 'Y:robot_3>robot_5>robot_4', 'Y:robot_4>robot_1>robot_3', 'Y:robot_4>robot_3>robot_1', 'Y:robot_4>robot_3>robot_5', 'Y:robot_4>robot_5>robot_3', 'R:robot_3', 'R:robot_4', 'R:robot_3+robot_4']
- **S3 (stage-2 label + task intents):** gate pass; T1 13/88 motion; motion set ['Y:robot_3>robot_4', 'Y:robot_4>robot_3', 'Y:robot_3>robot_1>robot_4', 'Y:robot_3>robot_4>robot_1', 'Y:robot_3>robot_4>robot_5', 'Y:robot_3>robot_5>robot_4', 'Y:robot_4>robot_1>robot_3', 'Y:robot_4>robot_3>robot_1', 'Y:robot_4>robot_3>robot_5', 'Y:robot_4>robot_5>robot_3', 'R:robot_3', 'R:robot_4', 'R:robot_3+robot_4']
- All guards on (sensitivity): 13/88
- T2 at this snapshot: True, shortest {'robot': 'robot_3', 'heading_deg': 0, 'distance_m': 0.11}, start within clearance {'robot_3': False, 'robot_4': False}


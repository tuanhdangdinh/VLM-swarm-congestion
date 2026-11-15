# Round-2 Addendum EV-cb3996

- New evidence only; the round-1 sheet is unchanged. Unit and decision ids are those of the round-1 sheet.
- As written governs the primary coding; S3 is a post-freeze sensitivity input.

## FU1

### D1 at 13.4 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list True
- Candidates: ['robot_2', 'robot_4', 'robot_5', 'robot_1', 'robot_3']
- **As written:** gate pass; T1 47/237 motion (errors 0); motion set ['Y:robot_2>robot_4', 'Y:robot_4>robot_2', 'Y:robot_2>robot_1>robot_4', 'Y:robot_2>robot_3>robot_4', 'Y:robot_2>robot_4>robot_1', 'Y:robot_2>robot_4>robot_3', 'Y:robot_2>robot_4>robot_5', 'Y:robot_2>robot_5>robot_4', 'Y:robot_2>robot_1>robot_3>robot_4', 'Y:robot_2>robot_1>robot_4>robot_3', 'Y:robot_2>robot_1>robot_4>robot_5', 'Y:robot_2>robot_1>robot_5>robot_4', 'Y:robot_2>robot_3>robot_1>robot_4', 'Y:robot_2>robot_3>robot_4>robot_1', 'Y:robot_2>robot_4>robot_1>robot_3', 'Y:robot_2>robot_4>robot_1>robot_5', 'Y:robot_2>robot_4>robot_3>robot_1', 'Y:robot_2>robot_4>robot_5>robot_1', 'Y:robot_2>robot_5>robot_1>robot_4', 'Y:robot_2>robot_5>robot_4>robot_1', 'Y:robot_4>robot_1>robot_2', 'Y:robot_4>robot_2>robot_1', 'Y:robot_4>robot_2>robot_3', 'Y:robot_4>robot_2>robot_5', 'Y:robot_4>robot_3>robot_2', 'Y:robot_4>robot_5>robot_2', 'Y:robot_4>robot_1>robot_2>robot_3', 'Y:robot_4>robot_1>robot_2>robot_5', 'Y:robot_4>robot_1>robot_3>robot_2', 'Y:robot_4>robot_1>robot_5>robot_2', 'Y:robot_4>robot_2>robot_1>robot_3', 'Y:robot_4>robot_2>robot_1>robot_5', 'Y:robot_4>robot_2>robot_3>robot_1', 'Y:robot_4>robot_2>robot_5>robot_1', 'Y:robot_4>robot_3>robot_1>robot_2', 'Y:robot_4>robot_3>robot_2>robot_1', 'Y:robot_4>robot_5>robot_1>robot_2', 'Y:robot_4>robot_5>robot_2>robot_1', 'R:robot_2', 'R:robot_4', 'R:robot_5', 'R:robot_1+robot_2', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_3+robot_4', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 47/237 motion; motion set ['Y:robot_2>robot_4', 'Y:robot_4>robot_2', 'Y:robot_2>robot_1>robot_4', 'Y:robot_2>robot_3>robot_4', 'Y:robot_2>robot_4>robot_1', 'Y:robot_2>robot_4>robot_3', 'Y:robot_2>robot_4>robot_5', 'Y:robot_2>robot_5>robot_4', 'Y:robot_2>robot_1>robot_3>robot_4', 'Y:robot_2>robot_1>robot_4>robot_3', 'Y:robot_2>robot_1>robot_4>robot_5', 'Y:robot_2>robot_1>robot_5>robot_4', 'Y:robot_2>robot_3>robot_1>robot_4', 'Y:robot_2>robot_3>robot_4>robot_1', 'Y:robot_2>robot_4>robot_1>robot_3', 'Y:robot_2>robot_4>robot_1>robot_5', 'Y:robot_2>robot_4>robot_3>robot_1', 'Y:robot_2>robot_4>robot_5>robot_1', 'Y:robot_2>robot_5>robot_1>robot_4', 'Y:robot_2>robot_5>robot_4>robot_1', 'Y:robot_4>robot_1>robot_2', 'Y:robot_4>robot_2>robot_1', 'Y:robot_4>robot_2>robot_3', 'Y:robot_4>robot_2>robot_5', 'Y:robot_4>robot_3>robot_2', 'Y:robot_4>robot_5>robot_2', 'Y:robot_4>robot_1>robot_2>robot_3', 'Y:robot_4>robot_1>robot_2>robot_5', 'Y:robot_4>robot_1>robot_3>robot_2', 'Y:robot_4>robot_1>robot_5>robot_2', 'Y:robot_4>robot_2>robot_1>robot_3', 'Y:robot_4>robot_2>robot_1>robot_5', 'Y:robot_4>robot_2>robot_3>robot_1', 'Y:robot_4>robot_2>robot_5>robot_1', 'Y:robot_4>robot_3>robot_1>robot_2', 'Y:robot_4>robot_3>robot_2>robot_1', 'Y:robot_4>robot_5>robot_1>robot_2', 'Y:robot_4>robot_5>robot_2>robot_1', 'R:robot_2', 'R:robot_4', 'R:robot_5', 'R:robot_1+robot_2', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_3+robot_4', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- All guards on (sensitivity): 47/237
- T2 at this snapshot: True, shortest {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01}, start within clearance {'robot_2': False, 'robot_4': False, 'robot_5': False}

## FU2

### D1 at 13.4 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list True
- Candidates: ['robot_1', 'robot_3', 'robot_5', 'robot_2']
- **As written:** gate pass; T1 7/88 motion (errors 0); motion set ['R:robot_1', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_5', 'R:robot_2+robot_3', 'R:robot_3+robot_5', 'R:robot_1+robot_2+robot_3+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 7/88 motion; motion set ['R:robot_1', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_5', 'R:robot_2+robot_3', 'R:robot_3+robot_5', 'R:robot_1+robot_2+robot_3+robot_5']
- All guards on (sensitivity): 7/88
- T2 at this snapshot: True, shortest {'robot': 'robot_1', 'heading_deg': 225, 'distance_m': 0.1}, start within clearance {'robot_1': False, 'robot_3': False}

### D4 at 66.233 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published False, withheld True, in round-1 chain list False
- Candidates: ['robot_1', 'robot_3', 'robot_5', 'robot_2']
- **As written:** gate pass; T1 6/88 motion (errors 0); motion set ['R:robot_1', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_5', 'R:robot_2+robot_3', 'R:robot_3+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 6/88 motion; motion set ['R:robot_1', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_5', 'R:robot_2+robot_3', 'R:robot_3+robot_5']
- All guards on (sensitivity): 6/88
- T2 at this snapshot: True, shortest {'robot': 'robot_1', 'heading_deg': 180, 'distance_m': 0.06}, start within clearance {'robot_1': False, 'robot_3': False}


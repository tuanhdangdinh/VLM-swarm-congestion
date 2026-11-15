# Round-2 Addendum EV-2c719b

- New evidence only; the round-1 sheet is unchanged. Unit and decision ids are those of the round-1 sheet.
- As written governs the primary coding; S3 is a post-freeze sensitivity input.

## FU1

- No new evidence for this unit.

## FU2

### D1 at 13.233 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list True
- Candidates: ['robot_2', 'robot_4', 'robot_1', 'robot_3']
- **As written:** gate pass; T1 9/88 motion (errors 0); motion set ['Y:robot_2>robot_4', 'Y:robot_4>robot_2', 'Y:robot_2>robot_1>robot_4', 'Y:robot_2>robot_4>robot_1', 'Y:robot_4>robot_1>robot_2', 'Y:robot_4>robot_2>robot_1', 'R:robot_2', 'R:robot_4', 'R:robot_2+robot_4']
- **S3 (stage-2 label + task intents):** gate pass; T1 9/88 motion; motion set ['Y:robot_2>robot_4', 'Y:robot_4>robot_2', 'Y:robot_2>robot_1>robot_4', 'Y:robot_2>robot_4>robot_1', 'Y:robot_4>robot_1>robot_2', 'Y:robot_4>robot_2>robot_1', 'R:robot_2', 'R:robot_4', 'R:robot_2+robot_4']
- All guards on (sensitivity): 3/88
- T2 at this snapshot: True, shortest {'robot': 'robot_2', 'heading_deg': 180, 'distance_m': 0.16}, start within clearance {'robot_2': False, 'robot_4': False}

### D3 at 39.467 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published False, withheld True, in round-1 chain list False
- Candidates: ['robot_2', 'robot_4', 'robot_1', 'robot_3']
- **As written:** gate pass; T1 2/88 motion (errors 0); motion set ['R:robot_2', 'R:robot_4']
- **S3 (stage-2 label + task intents):** gate pass; T1 2/88 motion; motion set ['R:robot_2', 'R:robot_4']
- All guards on (sensitivity): 2/88
- T2 at this snapshot: True, shortest {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01}, start within clearance {'robot_2': False, 'robot_4': True}

### D7 at 91.6 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published False, withheld True, in round-1 chain list False
- Candidates: ['robot_2', 'robot_4', 'robot_1', 'robot_3']
- **As written:** gate pass; T1 2/88 motion (errors 0); motion set ['R:robot_2', 'R:robot_4']
- **S3 (stage-2 label + task intents):** gate pass; T1 2/88 motion; motion set ['R:robot_2', 'R:robot_4']
- All guards on (sensitivity): 2/88
- T2 at this snapshot: True, shortest {'robot': 'robot_2', 'heading_deg': 90, 'distance_m': 0.02}, start within clearance {'robot_2': False, 'robot_4': True}


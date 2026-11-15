# Round-2 Addendum EV-db0df6

- New evidence only; the round-1 sheet is unchanged. Unit and decision ids are those of the round-1 sheet.
- As written governs the primary coding; S3 is a post-freeze sensitivity input.

## FU1

### D1 at 11.9 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published False, withheld True, in round-1 chain list False
- Candidates: ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']
- **As written:** gate pass; T1 10/237 motion (errors 0); motion set ['R:robot_1', 'R:robot_2', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_2+robot_4', 'R:robot_3+robot_4', 'R:robot_3+robot_5', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 10/237 motion; motion set ['R:robot_1', 'R:robot_2', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_2+robot_4', 'R:robot_3+robot_4', 'R:robot_3+robot_5', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- All guards on (sensitivity): 10/237
- T2 at this snapshot: True, shortest {'robot': 'robot_3', 'heading_deg': 0, 'distance_m': 0.01}, start within clearance {'robot_1': False, 'robot_2': True, 'robot_3': False}

### D2 at 15.833 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published False, withheld True, in round-1 chain list False
- Candidates: ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']
- **As written:** gate pass; T1 10/237 motion (errors 0); motion set ['R:robot_1', 'R:robot_2', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_2+robot_4', 'R:robot_3+robot_4', 'R:robot_3+robot_5', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 10/237 motion; motion set ['R:robot_1', 'R:robot_2', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_2+robot_4', 'R:robot_3+robot_4', 'R:robot_3+robot_5', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- All guards on (sensitivity): 10/237
- T2 at this snapshot: True, shortest {'robot': 'robot_2', 'heading_deg': 135, 'distance_m': 0.06}, start within clearance {'robot_1': False, 'robot_2': False, 'robot_3': False}

### D3 at 30.067 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list True
- Candidates: ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']
- **As written:** gate pass; T1 12/237 motion (errors 0); motion set ['R:robot_1', 'R:robot_2', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_3+robot_4', 'R:robot_3+robot_5', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 12/237 motion; motion set ['R:robot_1', 'R:robot_2', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_3+robot_4', 'R:robot_3+robot_5', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- All guards on (sensitivity): 12/237
- T2 at this snapshot: True, shortest {'robot': 'robot_2', 'heading_deg': 135, 'distance_m': 0.06}, start within clearance {'robot_1': False, 'robot_2': False, 'robot_3': False}

### D7 at 74.6 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list False
- Candidates: ['robot_1', 'robot_2', 'robot_3', 'robot_5', 'robot_4']
- **As written:** gate pass; T1 12/237 motion (errors 0); motion set ['R:robot_1', 'R:robot_2', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_3+robot_4', 'R:robot_3+robot_5', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 12/237 motion; motion set ['R:robot_1', 'R:robot_2', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_3+robot_4', 'R:robot_3+robot_5', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- All guards on (sensitivity): 12/237
- T2 at this snapshot: True, shortest {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01}, start within clearance {'robot_1': False, 'robot_2': False, 'robot_3': False}

### D8 at 87.233 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list False
- Candidates: ['robot_1', 'robot_2', 'robot_3', 'robot_5', 'robot_4']
- **As written:** gate pass; T1 33/237 motion (errors 0); motion set ['Y:robot_1>robot_2', 'Y:robot_2>robot_1', 'Y:robot_1>robot_2>robot_4', 'Y:robot_1>robot_2>robot_5', 'Y:robot_1>robot_4>robot_2', 'Y:robot_1>robot_5>robot_2', 'Y:robot_1>robot_2>robot_4>robot_5', 'Y:robot_1>robot_2>robot_5>robot_4', 'Y:robot_1>robot_4>robot_2>robot_5', 'Y:robot_1>robot_4>robot_5>robot_2', 'Y:robot_1>robot_5>robot_2>robot_4', 'Y:robot_1>robot_5>robot_4>robot_2', 'Y:robot_2>robot_1>robot_4', 'Y:robot_2>robot_1>robot_5', 'Y:robot_2>robot_4>robot_1', 'Y:robot_2>robot_5>robot_1', 'Y:robot_2>robot_1>robot_4>robot_5', 'Y:robot_2>robot_1>robot_5>robot_4', 'Y:robot_2>robot_4>robot_1>robot_5', 'Y:robot_2>robot_4>robot_5>robot_1', 'Y:robot_2>robot_5>robot_1>robot_4', 'Y:robot_2>robot_5>robot_4>robot_1', 'R:robot_1', 'R:robot_2', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_3+robot_4', 'R:robot_3+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 33/237 motion; motion set ['Y:robot_1>robot_2', 'Y:robot_2>robot_1', 'Y:robot_1>robot_2>robot_4', 'Y:robot_1>robot_2>robot_5', 'Y:robot_1>robot_4>robot_2', 'Y:robot_1>robot_5>robot_2', 'Y:robot_1>robot_2>robot_4>robot_5', 'Y:robot_1>robot_2>robot_5>robot_4', 'Y:robot_1>robot_4>robot_2>robot_5', 'Y:robot_1>robot_4>robot_5>robot_2', 'Y:robot_1>robot_5>robot_2>robot_4', 'Y:robot_1>robot_5>robot_4>robot_2', 'Y:robot_2>robot_1>robot_4', 'Y:robot_2>robot_1>robot_5', 'Y:robot_2>robot_4>robot_1', 'Y:robot_2>robot_5>robot_1', 'Y:robot_2>robot_1>robot_4>robot_5', 'Y:robot_2>robot_1>robot_5>robot_4', 'Y:robot_2>robot_4>robot_1>robot_5', 'Y:robot_2>robot_4>robot_5>robot_1', 'Y:robot_2>robot_5>robot_1>robot_4', 'Y:robot_2>robot_5>robot_4>robot_1', 'R:robot_1', 'R:robot_2', 'R:robot_3', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_3+robot_4', 'R:robot_3+robot_5']
- All guards on (sensitivity): 33/237
- T2 at this snapshot: True, shortest {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01}, start within clearance {'robot_1': False, 'robot_2': False, 'robot_3': False}

## FU2

### D1 at 11.9 rel-s (T1 at decision snapshot; before the unit's timeline)

- Supplies: T1 at this decision's own snapshot, supplied for completeness. The decision is before the unit's timeline start (earlier of t0 - 60 s and the chain start), so the frozen chain rule does not walk it; it is not round-1 missing evidence.
- Published False, withheld True, in round-1 chain list False
- Candidates: ['robot_4', 'robot_5', 'robot_1', 'robot_2']
- **As written:** gate pass; T1 6/88 motion (errors 0); motion set ['R:robot_4', 'R:robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_4+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 6/88 motion; motion set ['R:robot_4', 'R:robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_4+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- All guards on (sensitivity): 6/88
- T2 at this snapshot: True, shortest {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01}, start within clearance {'robot_4': False, 'robot_5': False}

### D2 at 15.833 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published False, withheld True, in round-1 chain list False
- Candidates: ['robot_4', 'robot_5', 'robot_1', 'robot_2']
- **As written:** gate pass; T1 5/88 motion (errors 0); motion set ['R:robot_4', 'R:robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 5/88 motion; motion set ['R:robot_4', 'R:robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- All guards on (sensitivity): 5/88
- T2 at this snapshot: True, shortest {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01}, start within clearance {'robot_4': False, 'robot_5': False}

### D3 at 30.067 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list False
- Candidates: ['robot_4', 'robot_5', 'robot_1', 'robot_2']
- **As written:** gate pass; T1 7/88 motion (errors 0); motion set ['R:robot_4', 'R:robot_5', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_4+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 7/88 motion; motion set ['R:robot_4', 'R:robot_5', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_4+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- All guards on (sensitivity): 7/88
- T2 at this snapshot: True, shortest {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01}, start within clearance {'robot_4': False, 'robot_5': False}

### D4 at 49.067 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list True
- Candidates: ['robot_4', 'robot_5', 'robot_1', 'robot_2']
- **As written:** gate pass; T1 27/88 motion (errors 0); motion set ['Y:robot_4>robot_5', 'Y:robot_5>robot_4', 'Y:robot_4>robot_2>robot_5', 'Y:robot_4>robot_5>robot_1', 'Y:robot_4>robot_5>robot_2', 'Y:robot_4>robot_1>robot_2>robot_5', 'Y:robot_4>robot_1>robot_5>robot_2', 'Y:robot_4>robot_2>robot_1>robot_5', 'Y:robot_4>robot_2>robot_5>robot_1', 'Y:robot_4>robot_5>robot_1>robot_2', 'Y:robot_4>robot_5>robot_2>robot_1', 'Y:robot_5>robot_1>robot_4', 'Y:robot_5>robot_2>robot_4', 'Y:robot_5>robot_4>robot_1', 'Y:robot_5>robot_4>robot_2', 'Y:robot_5>robot_1>robot_2>robot_4', 'Y:robot_5>robot_1>robot_4>robot_2', 'Y:robot_5>robot_2>robot_1>robot_4', 'Y:robot_5>robot_2>robot_4>robot_1', 'Y:robot_5>robot_4>robot_1>robot_2', 'Y:robot_5>robot_4>robot_2>robot_1', 'R:robot_4', 'R:robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_4+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 27/88 motion; motion set ['Y:robot_4>robot_5', 'Y:robot_5>robot_4', 'Y:robot_4>robot_2>robot_5', 'Y:robot_4>robot_5>robot_1', 'Y:robot_4>robot_5>robot_2', 'Y:robot_4>robot_1>robot_2>robot_5', 'Y:robot_4>robot_1>robot_5>robot_2', 'Y:robot_4>robot_2>robot_1>robot_5', 'Y:robot_4>robot_2>robot_5>robot_1', 'Y:robot_4>robot_5>robot_1>robot_2', 'Y:robot_4>robot_5>robot_2>robot_1', 'Y:robot_5>robot_1>robot_4', 'Y:robot_5>robot_2>robot_4', 'Y:robot_5>robot_4>robot_1', 'Y:robot_5>robot_4>robot_2', 'Y:robot_5>robot_1>robot_2>robot_4', 'Y:robot_5>robot_1>robot_4>robot_2', 'Y:robot_5>robot_2>robot_1>robot_4', 'Y:robot_5>robot_2>robot_4>robot_1', 'Y:robot_5>robot_4>robot_1>robot_2', 'Y:robot_5>robot_4>robot_2>robot_1', 'R:robot_4', 'R:robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_4+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- All guards on (sensitivity): 27/88
- T2 at this snapshot: True, shortest {'robot': 'robot_4', 'heading_deg': 270, 'distance_m': 0.09}, start within clearance {'robot_4': False, 'robot_5': False}

### D9 at 99.767 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published False, withheld True, in round-1 chain list False
- Candidates: ['robot_4', 'robot_5', 'robot_1', 'robot_2']
- **As written:** gate pass; T1 33/88 motion (errors 0); motion set ['Y:robot_4>robot_5', 'Y:robot_5>robot_4', 'Y:robot_4>robot_1>robot_5', 'Y:robot_4>robot_2>robot_5', 'Y:robot_4>robot_5>robot_1', 'Y:robot_4>robot_5>robot_2', 'Y:robot_4>robot_1>robot_2>robot_5', 'Y:robot_4>robot_1>robot_5>robot_2', 'Y:robot_4>robot_2>robot_1>robot_5', 'Y:robot_4>robot_2>robot_5>robot_1', 'Y:robot_4>robot_5>robot_1>robot_2', 'Y:robot_4>robot_5>robot_2>robot_1', 'Y:robot_5>robot_1>robot_4', 'Y:robot_5>robot_2>robot_4', 'Y:robot_5>robot_4>robot_1', 'Y:robot_5>robot_4>robot_2', 'Y:robot_5>robot_1>robot_2>robot_4', 'Y:robot_5>robot_1>robot_4>robot_2', 'Y:robot_5>robot_2>robot_1>robot_4', 'Y:robot_5>robot_2>robot_4>robot_1', 'Y:robot_5>robot_4>robot_1>robot_2', 'Y:robot_5>robot_4>robot_2>robot_1', 'R:robot_4', 'R:robot_5', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_4+robot_5', 'CV:robot_1', 'CV:robot_2', 'CV:robot_4', 'CV:robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 33/88 motion; motion set ['Y:robot_4>robot_5', 'Y:robot_5>robot_4', 'Y:robot_4>robot_1>robot_5', 'Y:robot_4>robot_2>robot_5', 'Y:robot_4>robot_5>robot_1', 'Y:robot_4>robot_5>robot_2', 'Y:robot_4>robot_1>robot_2>robot_5', 'Y:robot_4>robot_1>robot_5>robot_2', 'Y:robot_4>robot_2>robot_1>robot_5', 'Y:robot_4>robot_2>robot_5>robot_1', 'Y:robot_4>robot_5>robot_1>robot_2', 'Y:robot_4>robot_5>robot_2>robot_1', 'Y:robot_5>robot_1>robot_4', 'Y:robot_5>robot_2>robot_4', 'Y:robot_5>robot_4>robot_1', 'Y:robot_5>robot_4>robot_2', 'Y:robot_5>robot_1>robot_2>robot_4', 'Y:robot_5>robot_1>robot_4>robot_2', 'Y:robot_5>robot_2>robot_1>robot_4', 'Y:robot_5>robot_2>robot_4>robot_1', 'Y:robot_5>robot_4>robot_1>robot_2', 'Y:robot_5>robot_4>robot_2>robot_1', 'R:robot_4', 'R:robot_5', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_4+robot_5', 'CV:robot_1', 'CV:robot_2', 'CV:robot_4', 'CV:robot_5']
- All guards on (sensitivity): 33/88
- T2 at this snapshot: True, shortest {'robot': 'robot_4', 'heading_deg': 270, 'distance_m': 0.04}, start within clearance {'robot_4': False, 'robot_5': False}


# Round-2 Addendum EV-37a70e

- New evidence only; the round-1 sheet is unchanged. Unit and decision ids are those of the round-1 sheet.
- As written governs the primary coding; S3 is a post-freeze sensitivity input.

## FU1

### D2 at 30.0 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list True
- Candidates: ['robot_2', 'robot_3', 'robot_4', 'robot_5', 'robot_1']
- **As written:** gate U:T1_fidelity; T1 84/237 motion (errors 0); motion set ['Y:robot_2>robot_3', 'Y:robot_3>robot_2', 'Y:robot_4>robot_5', 'Y:robot_5>robot_4', 'Y:robot_1>robot_4>robot_5', 'Y:robot_1>robot_2>robot_4>robot_5', 'Y:robot_1>robot_4>robot_2>robot_5', 'Y:robot_1>robot_4>robot_3>robot_5', 'Y:robot_1>robot_4>robot_5>robot_2', 'Y:robot_1>robot_4>robot_5>robot_3', 'Y:robot_2>robot_3>robot_4', 'Y:robot_2>robot_3>robot_5', 'Y:robot_2>robot_4>robot_3', 'Y:robot_2>robot_4>robot_5', 'Y:robot_2>robot_5>robot_3', 'Y:robot_2>robot_5>robot_4', 'Y:robot_2>robot_1>robot_4>robot_5', 'Y:robot_2>robot_3>robot_4>robot_5', 'Y:robot_2>robot_3>robot_5>robot_4', 'Y:robot_2>robot_4>robot_1>robot_5', 'Y:robot_2>robot_4>robot_3>robot_5', 'Y:robot_2>robot_4>robot_5>robot_1', 'Y:robot_2>robot_4>robot_5>robot_3', 'Y:robot_2>robot_5>robot_3>robot_4', 'Y:robot_2>robot_5>robot_4>robot_3', 'Y:robot_3>robot_2>robot_4', 'Y:robot_3>robot_2>robot_5', 'Y:robot_3>robot_4>robot_2', 'Y:robot_3>robot_4>robot_5', 'Y:robot_3>robot_5>robot_2', 'Y:robot_3>robot_5>robot_4', 'Y:robot_3>robot_2>robot_4>robot_5', 'Y:robot_3>robot_2>robot_5>robot_4', 'Y:robot_3>robot_4>robot_2>robot_5', 'Y:robot_3>robot_4>robot_5>robot_2', 'Y:robot_3>robot_5>robot_2>robot_4', 'Y:robot_3>robot_5>robot_4>robot_2', 'Y:robot_4>robot_1>robot_5', 'Y:robot_4>robot_2>robot_5', 'Y:robot_4>robot_3>robot_5', 'Y:robot_4>robot_5>robot_1', 'Y:robot_4>robot_5>robot_2', 'Y:robot_4>robot_5>robot_3', 'Y:robot_4>robot_1>robot_2>robot_5', 'Y:robot_4>robot_1>robot_3>robot_5', 'Y:robot_4>robot_1>robot_5>robot_2', 'Y:robot_4>robot_1>robot_5>robot_3', 'Y:robot_4>robot_2>robot_1>robot_5', 'Y:robot_4>robot_2>robot_3>robot_5', 'Y:robot_4>robot_2>robot_5>robot_1', 'Y:robot_4>robot_2>robot_5>robot_3', 'Y:robot_4>robot_3>robot_1>robot_5', 'Y:robot_4>robot_3>robot_2>robot_5', 'Y:robot_4>robot_3>robot_5>robot_1', 'Y:robot_4>robot_3>robot_5>robot_2', 'Y:robot_4>robot_5>robot_1>robot_2', 'Y:robot_4>robot_5>robot_1>robot_3', 'Y:robot_4>robot_5>robot_2>robot_1', 'Y:robot_4>robot_5>robot_2>robot_3', 'Y:robot_4>robot_5>robot_3>robot_1', 'Y:robot_4>robot_5>robot_3>robot_2', 'Y:robot_5>robot_2>robot_4', 'Y:robot_5>robot_3>robot_4', 'Y:robot_5>robot_4>robot_2', 'Y:robot_5>robot_4>robot_3', 'Y:robot_5>robot_2>robot_3>robot_4', 'Y:robot_5>robot_2>robot_4>robot_3', 'Y:robot_5>robot_3>robot_2>robot_4', 'Y:robot_5>robot_3>robot_4>robot_2', 'Y:robot_5>robot_4>robot_2>robot_3', 'Y:robot_5>robot_4>robot_3>robot_2', 'R:robot_2', 'R:robot_3', 'R:robot_4', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_2+robot_3', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_3+robot_4', 'R:robot_3+robot_5', 'R:robot_4+robot_5', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 84/237 motion; motion set ['Y:robot_2>robot_3', 'Y:robot_3>robot_2', 'Y:robot_4>robot_5', 'Y:robot_5>robot_4', 'Y:robot_1>robot_4>robot_5', 'Y:robot_1>robot_2>robot_4>robot_5', 'Y:robot_1>robot_4>robot_2>robot_5', 'Y:robot_1>robot_4>robot_3>robot_5', 'Y:robot_1>robot_4>robot_5>robot_2', 'Y:robot_1>robot_4>robot_5>robot_3', 'Y:robot_2>robot_3>robot_4', 'Y:robot_2>robot_3>robot_5', 'Y:robot_2>robot_4>robot_3', 'Y:robot_2>robot_4>robot_5', 'Y:robot_2>robot_5>robot_3', 'Y:robot_2>robot_5>robot_4', 'Y:robot_2>robot_1>robot_4>robot_5', 'Y:robot_2>robot_3>robot_4>robot_5', 'Y:robot_2>robot_3>robot_5>robot_4', 'Y:robot_2>robot_4>robot_1>robot_5', 'Y:robot_2>robot_4>robot_3>robot_5', 'Y:robot_2>robot_4>robot_5>robot_1', 'Y:robot_2>robot_4>robot_5>robot_3', 'Y:robot_2>robot_5>robot_3>robot_4', 'Y:robot_2>robot_5>robot_4>robot_3', 'Y:robot_3>robot_2>robot_4', 'Y:robot_3>robot_2>robot_5', 'Y:robot_3>robot_4>robot_2', 'Y:robot_3>robot_4>robot_5', 'Y:robot_3>robot_5>robot_2', 'Y:robot_3>robot_5>robot_4', 'Y:robot_3>robot_2>robot_4>robot_5', 'Y:robot_3>robot_2>robot_5>robot_4', 'Y:robot_3>robot_4>robot_2>robot_5', 'Y:robot_3>robot_4>robot_5>robot_2', 'Y:robot_3>robot_5>robot_2>robot_4', 'Y:robot_3>robot_5>robot_4>robot_2', 'Y:robot_4>robot_1>robot_5', 'Y:robot_4>robot_2>robot_5', 'Y:robot_4>robot_3>robot_5', 'Y:robot_4>robot_5>robot_1', 'Y:robot_4>robot_5>robot_2', 'Y:robot_4>robot_5>robot_3', 'Y:robot_4>robot_1>robot_2>robot_5', 'Y:robot_4>robot_1>robot_3>robot_5', 'Y:robot_4>robot_1>robot_5>robot_2', 'Y:robot_4>robot_1>robot_5>robot_3', 'Y:robot_4>robot_2>robot_1>robot_5', 'Y:robot_4>robot_2>robot_3>robot_5', 'Y:robot_4>robot_2>robot_5>robot_1', 'Y:robot_4>robot_2>robot_5>robot_3', 'Y:robot_4>robot_3>robot_1>robot_5', 'Y:robot_4>robot_3>robot_2>robot_5', 'Y:robot_4>robot_3>robot_5>robot_1', 'Y:robot_4>robot_3>robot_5>robot_2', 'Y:robot_4>robot_5>robot_1>robot_2', 'Y:robot_4>robot_5>robot_1>robot_3', 'Y:robot_4>robot_5>robot_2>robot_1', 'Y:robot_4>robot_5>robot_2>robot_3', 'Y:robot_4>robot_5>robot_3>robot_1', 'Y:robot_4>robot_5>robot_3>robot_2', 'Y:robot_5>robot_2>robot_4', 'Y:robot_5>robot_3>robot_4', 'Y:robot_5>robot_4>robot_2', 'Y:robot_5>robot_4>robot_3', 'Y:robot_5>robot_2>robot_3>robot_4', 'Y:robot_5>robot_2>robot_4>robot_3', 'Y:robot_5>robot_3>robot_2>robot_4', 'Y:robot_5>robot_3>robot_4>robot_2', 'Y:robot_5>robot_4>robot_2>robot_3', 'Y:robot_5>robot_4>robot_3>robot_2', 'R:robot_2', 'R:robot_3', 'R:robot_4', 'R:robot_1+robot_2', 'R:robot_1+robot_3', 'R:robot_1+robot_4', 'R:robot_2+robot_3', 'R:robot_2+robot_4', 'R:robot_2+robot_5', 'R:robot_3+robot_4', 'R:robot_3+robot_5', 'R:robot_4+robot_5', 'R:robot_1+robot_2+robot_3+robot_4+robot_5']
- All guards on (sensitivity): 74/237
- T2 at this snapshot: True, shortest {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01}, start within clearance {'robot_2': False, 'robot_3': False, 'robot_4': False}

### t0 (T1 fidelity both ways)

- Supplies: T1 fidelity at onset reported both ways. The as-written status is unchanged and governs the primary; the S3 result (stored stage-2 label and rebuilt task intents) is a post-freeze sensitivity input (round-1 missing evidence: U:T1_fidelity).
- **As written:** U:T1_fidelity (episode gate, as round 1); recorded decisions reproduced 5/6
- **S3:** gate episode_gate_pass; reproduced 6/6; T1 (task intents) 75/237 motion
- Per-decision gate (as written / S3): D2 differs / reproduced; D3 reproduced / reproduced; D4 reproduced / reproduced; D5 reproduced / reproduced; D8 reproduced / reproduced; D9 reproduced / reproduced

## FU2

### D2 at 30.0 rel-s (T1 at decision snapshot; before the unit's timeline)

- Supplies: T1 at this decision's own snapshot, supplied for completeness. The decision is before the unit's timeline start (earlier of t0 - 60 s and the chain start), so the frozen chain rule does not walk it; it is not round-1 missing evidence.
- Published True, withheld False, in round-1 chain list False
- Candidates: ['robot_1', 'robot_5', 'robot_4', 'robot_2']
- **As written:** gate U:T1_fidelity; T1 7/88 motion (errors 0); motion set ['R:robot_1', 'R:robot_5', 'R:robot_1+robot_2', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 7/88 motion; motion set ['R:robot_1', 'R:robot_5', 'R:robot_1+robot_2', 'R:robot_1+robot_4', 'R:robot_1+robot_5', 'R:robot_2+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- All guards on (sensitivity): 7/88
- T2 at this snapshot: True, shortest {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01}, start within clearance {'robot_1': False, 'robot_5': False}

### D3 at 76.3 rel-s (T1 at decision snapshot)

- Supplies: T1 at this decision's own snapshot. Round 1 had no T1 row here (T1 ran only at the onset snapshot and at analyses matched to the unit); rubric 7.5 step 4 judges an analysis 'against T1 at that snapshot' and V2/V3 need T1 non-empty (round-1 missing evidence: U:T1_not_run).
- Published True, withheld False, in round-1 chain list True
- Candidates: ['robot_1', 'robot_5', 'robot_4', 'robot_2']
- **As written:** gate pass; T1 20/88 motion (errors 0); motion set ['Y:robot_1>robot_4', 'Y:robot_1>robot_5', 'Y:robot_4>robot_1', 'Y:robot_5>robot_1', 'Y:robot_1>robot_2>robot_4', 'Y:robot_1>robot_2>robot_5', 'Y:robot_1>robot_4>robot_2', 'Y:robot_1>robot_5>robot_2', 'Y:robot_2>robot_1>robot_4', 'Y:robot_2>robot_4>robot_1', 'Y:robot_4>robot_1>robot_2', 'Y:robot_4>robot_2>robot_1', 'Y:robot_5>robot_1>robot_2', 'Y:robot_5>robot_2>robot_1', 'R:robot_1', 'R:robot_5', 'R:robot_1+robot_2', 'R:robot_1+robot_5', 'R:robot_2+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- **S3 (stage-2 label + task intents):** gate pass; T1 20/88 motion; motion set ['Y:robot_1>robot_4', 'Y:robot_1>robot_5', 'Y:robot_4>robot_1', 'Y:robot_5>robot_1', 'Y:robot_1>robot_2>robot_4', 'Y:robot_1>robot_2>robot_5', 'Y:robot_1>robot_4>robot_2', 'Y:robot_1>robot_5>robot_2', 'Y:robot_2>robot_1>robot_4', 'Y:robot_2>robot_4>robot_1', 'Y:robot_4>robot_1>robot_2', 'Y:robot_4>robot_2>robot_1', 'Y:robot_5>robot_1>robot_2', 'Y:robot_5>robot_2>robot_1', 'R:robot_1', 'R:robot_5', 'R:robot_1+robot_2', 'R:robot_1+robot_5', 'R:robot_2+robot_5', 'R:robot_1+robot_2+robot_4+robot_5']
- All guards on (sensitivity): 20/88
- T2 at this snapshot: True, shortest {'robot': 'robot_5', 'heading_deg': 180, 'distance_m': 0.03}, start within clearance {'robot_1': False, 'robot_5': False}

### t0 (T1 fidelity both ways)

- Supplies: T1 fidelity at onset reported both ways. The as-written status is unchanged and governs the primary; the S3 result (stored stage-2 label and rebuilt task intents) is a post-freeze sensitivity input (round-1 missing evidence: U:T1_fidelity).
- **As written:** U:T1_fidelity (episode gate, as round 1); recorded decisions reproduced 5/6
- **S3:** gate episode_gate_pass; reproduced 6/6; T1 (task intents) 8/88 motion
- Per-decision gate (as written / S3): D2 differs / reproduced; D3 reproduced / reproduced; D4 reproduced / reproduced; D5 reproduced / reproduced; D8 reproduced / reproduced; D9 reproduced / reproduced


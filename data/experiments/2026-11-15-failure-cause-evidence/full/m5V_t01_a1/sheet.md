# Evidence Sheet m5V_t01_a1

- Censoring: t_end 573.807 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=39 max residual 1.368 s
- Outcome fields (frozen, copied): {"source": "[R] rubric 5.3 row (validation report figure)", "text": "2 of 5 arrived (GT 0.3 m), unresolved at 600 sim-s"}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3 | 54.607 | 573.807 | False | b07a700f:robot_1:reverse, b07a700f:robot_2:reverse, b07a700f:robot_3:reverse | - |
| FU2 | conflict | robot_4, robot_5 | 73.507 | 573.807 | False | 95066420:robot_4:reverse, 95066420:robot_5:reverse | - |

### FU1

- Pairs: [['robot_1', 'robot_2'], ['robot_2', 'robot_3']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 30.067 rel-s
- V1 input: {'a33_matched_positive_analyses': 3, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 96.61, 'until_rel': 573.81}, {'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 54.91, 'until_rel': 573.81}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 96.51, 'to_rel': 573.81, 'duration_s': 477.3, 'to_censor': True, 'safety_stop_cover_fraction': 0.999}, {'robot': 'robot_2', 'from_rel': 97.31, 'to_rel': 573.81, 'duration_s': 476.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 97.31, 'to_rel': 573.81, 'duration_s': 476.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 11.087 | safety_stop_span | robot_1 | to 32.524 (5892 lines) |
| 11.9 | analysis | 2461ee6bf74647828d201c02e8446d23 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 11.9 | withheld | 2461ee6bf74647828d201c02e8446d23 | robot_1:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 12.851 | safety_stop_span | robot_2 | to 32.524 (5413 lines) |
| 12.86 | safety_stop_span | robot_3 | to 32.524 (5413 lines) |
| 15.833 | analysis | 597e224f49f44265b8b4c55ae8d6a5c3 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_4 |
| 15.833 | withheld | 597e224f49f44265b8b4c55ae8d6a5c3 | robot_1:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 30.067 | analysis | b07a700f441b4745a6be81f3899668ed | positive strategy=reverse involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 30.067 | dispatched | b07a700f441b4745a6be81f3899668ed | robot_1:reverse, robot_2:reverse, robot_3:reverse |
| 31.7 | m4_leg_start | b07a700f:robot_1:reverse | reverse commanded=1.3 |
| 31.7 | m4_leg_start | b07a700f:robot_2:reverse | reverse commanded=1.3 |
| 31.734 | m4_leg_start | b07a700f:robot_3:reverse | reverse commanded=1.3 |
| 32.525 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_2+robot_3 |
| 44.48 | m4_terminal | b07a700f:robot_2:reverse | COMPLETED  moved=1.202 tags=['completed'] deadline=False |
| 44.523 | m4_terminal | b07a700f:robot_3:reverse | COMPLETED  moved=1.209 tags=['completed'] deadline=False |
| 44.547 | m4_terminal | b07a700f:robot_1:reverse | COMPLETED  moved=1.205 tags=['completed'] deadline=False |
| 53.205 | safety_stop_span | robot_2 | to 575.482 (143443 lines) |
| 53.206 | safety_stop_span | robot_3 | to 575.482 (143443 lines) |
| 68.033 | analysis | 6a621c29c66549009e2cffb40d4b20f6 | positive strategy=yield involved=['robot_2', 'robot_3'] yield=robot_3 |
| 68.033 | withheld | 6a621c29c66549009e2cffb40d4b20f6 | robot_3:temporary_wait, robot_2:temporary_wait withheld=refusal_no_action |
| 71.333 | analysis | 45f50dce9933404181d94b0332b2d8ed | positive strategy=yield involved=['robot_2', 'robot_3'] yield=robot_2 |
| 71.333 | withheld | 45f50dce9933404181d94b0332b2d8ed | robot_2:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |
| 74.6 | analysis | 929335f4a4774da5b32f3f1f8c60c56d | positive strategy=reverse involved=['robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 74.6 | dispatched | 929335f4a4774da5b32f3f1f8c60c56d | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 84.633 | m1_stale | robot_1 | STALE 0.87 s |
| 87.233 | analysis | 2acc6130567a488eb03f234447dbe2da | positive strategy=reverse involved=['robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 87.233 | dispatched | 2acc6130567a488eb03f234447dbe2da | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 97.09 | safety_stop_span | robot_1 | to 575.482 (131440 lines) |
| 99.767 | analysis | 6e4c8849a89a41c4820fa86606f59391 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 99.767 | withheld | 6e4c8849a89a41c4820fa86606f59391 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 54.9 | episode_gate_pass / episode_gate_pass | 10/237 | 10/237 | 10/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| 6a621c29c66549009e2cffb40d4b20f6 | 68.033 | pass / pass | 26/237 | 26/237 | 26/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| 45f50dce9933404181d94b0332b2d8ed | 71.333 | pass / pass | 12/237 | 12/237 | 12/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| 6e4c8849a89a41c4820fa86606f59391 | 99.767 | pass / pass | 9/237 | 9/237 | 9/237 | True | {'robot': 'robot_1', 'heading_deg': 135, 'distance_m': 0.03} |

### FU2

- Pairs: [['robot_4', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 49.067 rel-s
- V1 input: {'a33_matched_positive_analyses': 2, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_4', 'robot_5'], 'close_and_stopped_from_rel': 73.61, 'until_rel': 573.81}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_4', 'from_rel': 97.31, 'to_rel': 573.81, 'duration_s': 476.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_5', 'from_rel': 97.31, 'to_rel': 573.81, 'duration_s': 476.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 15.833 | analysis | 597e224f49f44265b8b4c55ae8d6a5c3 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_4 |
| 15.833 | withheld | 597e224f49f44265b8b4c55ae8d6a5c3 | robot_1:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 30.067 | analysis | b07a700f441b4745a6be81f3899668ed | positive strategy=reverse involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 30.067 | dispatched | b07a700f441b4745a6be81f3899668ed | robot_1:reverse, robot_2:reverse, robot_3:reverse |
| 36.61 | gt_submargin | robot_5|box:obstacle_1 | to 37.81 min gap 0.0247 m |
| 42.329 | safety_stop_span | robot_5 | to 49.349 (1921 lines) |
| 42.33 | safety_stop_span | robot_4 | to 49.35 (1921 lines) |
| 49.067 | analysis | 95066420efa54188962f5c4f68806a4c | positive strategy=reverse involved=['robot_4', 'robot_5'] yield=None |
| 49.067 | dispatched | 95066420efa54188962f5c4f68806a4c | robot_4:reverse, robot_5:reverse |
| 49.35 | exempt_change | - | robot_4+robot_5 |
| 50.4 | m4_leg_start | 95066420:robot_4:reverse | reverse commanded=1.3 |
| 50.4 | m4_leg_start | 95066420:robot_5:reverse | reverse commanded=1.3 |
| 53.51 | gt_submargin | robot_4|box:obstacle_1 | to 56.31 min gap 0.0055 m |
| 59.51 | gt_submargin | robot_5|box:obstacle_1 | to 62.01 min gap 0.0191 m |
| 63.217 | m4_terminal | 95066420:robot_5:reverse | COMPLETED  moved=1.205 tags=['completed'] deadline=False |
| 63.371 | m4_terminal | 95066420:robot_4:reverse | COMPLETED  moved=1.206 tags=['completed'] deadline=False |
| 72.885 | safety_stop_span | robot_5 | to 575.482 (138055 lines) |
| 72.888 | safety_stop_span | robot_4 | to 575.482 (138055 lines) |
| 74.6 | analysis | 929335f4a4774da5b32f3f1f8c60c56d | positive strategy=reverse involved=['robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 74.6 | dispatched | 929335f4a4774da5b32f3f1f8c60c56d | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 87.233 | analysis | 2acc6130567a488eb03f234447dbe2da | positive strategy=reverse involved=['robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 87.233 | dispatched | 2acc6130567a488eb03f234447dbe2da | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 99.767 | analysis | 6e4c8849a89a41c4820fa86606f59391 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 99.767 | withheld | 6e4c8849a89a41c4820fa86606f59391 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 73.633 | episode_gate_pass / episode_gate_pass | 30/88 | 30/88 | 30/88 | True | {'robot': 'robot_4', 'heading_deg': 270, 'distance_m': 0.05} |
| 929335f4a4774da5b32f3f1f8c60c56d | 74.6 | pass / pass | 30/88 | 30/88 | 30/88 | True | {'robot': 'robot_4', 'heading_deg': 270, 'distance_m': 0.04} |
| 2acc6130567a488eb03f234447dbe2da | 87.233 | pass / pass | 29/88 | 29/88 | 29/88 | True | {'robot': 'robot_4', 'heading_deg': 270, 'distance_m': 0.04} |

## Decisions

### 2461ee6bf74647828d201c02e8446d23 at 11.9 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_1, crossing_order ['robot_4', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_1 yield and step back will allow robot_4 to pass through the narrow channel safely, after which robot_1 can proceed.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_1', 'robot_4']}, yield refusal yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured', 'grounding=node_handoff:robot_1->robot_4', 'grounding=dynamic_arms:parallel_refused:robot_1,robot_4:45']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_1->robot_4'], 'G6_verbatim_contradicted': False}

### 597e224f49f44265b8b4c55ae8d6a5c3 at 15.833 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_4, crossing_order ['robot_1', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 needs to yield and back up to allow Robot 1 to pass and clear the narrow lower-left corridor.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured, held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_1', 'robot_4']}, yield refusal yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured', 'grounding=node_handoff:robot_1->robot_4', 'grounding=node_handoff_regrounded:robot_4->robot_1', 'grounding=dynamic_arms:parallel_refused:robot_1,robot_4:45']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_4 both run along x but sit 45 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_1->robot_4', 'grounding=node_handoff_regrounded:robot_4->robot_1'], 'G6_verbatim_contradicted': False}

### b07a700f441b4745a6be81f3899668ed at 30.067 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_1', 'robot_2', 'robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having the robots on one side of each pair (robot_4 and robot_3) reverse will quickly resolve both head-on standoffs.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_3', 'robot_4'], 'involved': ['robot_1', 'robot_2', 'robot_3', 'robot_4']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_1: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}, {'op': 'substitute', 'reason': "robot_2: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_1->robot_4', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_1', 'reverse', {'backup_distance_m': 1.3, 'fresh_latch_fast_fail': True}), ('robot_2', 'reverse', {'backup_distance_m': 1.3, 'fresh_latch_fast_fail': True}), ('robot_3', 'reverse', {'backup_distance_m': 1.3, 'fresh_latch_fast_fail': True})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_1->robot_4'], 'G6_verbatim_contradicted': False, 'G4_robots_dropped': ['robot_4']}

### 95066420efa54188962f5c4f68806a4c at 49.067 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_4', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Robot 4 and Robot 5 are physically blocking each other in a head-on deadlock; Robot 4 must reverse out of the passage so that Robot 5 can continue.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_4'], 'involved': ['robot_4', 'robot_5']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held True, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:lane:y']
- Actions: [('robot_4', 'reverse', {'backup_distance_m': 1.3, 'fresh_latch_fast_fail': True}), ('robot_5', 'reverse', {'backup_distance_m': 1.3, 'fresh_latch_fast_fail': True})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### 6a621c29c66549009e2cffb40d4b20f6 at 68.033 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3'], yield_robot robot_3, crossing_order ['robot_2', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 3 is STOPPED and has a clear path to back up or yield, allowing robot_2 (which is currently moving SLOW) to proceed to its goal.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_3'], 'yield_robot': 'robot_3'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no declared junction: robot_3 runs along y and robot_2 along x (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no declared junction: robot_3 runs along y and robot_2 along x (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured', 'would_dispatch_robot_ids': ['robot_3', 'robot_2']}, yield refusal yield refused: no declared junction: robot_3 runs along y and robot_2 along x (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no declared junction: robot_3 runs along y and robot_2 along x (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured', 'grounding=dynamic_arms:crossing_refused:robot_3,robot_2']
- Actions: [('robot_3', 'temporary_wait', {'reason': 'yield refused: no declared junction: robot_3 runs along y and robot_2 along x (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no declared junction: robot_3 runs along y and robot_2 along x (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 45f50dce9933404181d94b0332b2d8ed at 71.333 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3'], yield_robot robot_2, crossing_order ['robot_3', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 2 and Robot 3 are head-on. Robot 2 should yield by backing up or stepping aside to allow Robot 3 to pass and resolve the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_2'], 'yield_robot': 'robot_2'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no declared junction: robot_2 runs along x and robot_3 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no declared junction: robot_2 runs along x and robot_3 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured', 'would_dispatch_robot_ids': ['robot_2', 'robot_3']}, yield refusal yield refused: no declared junction: robot_2 runs along x and robot_3 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no declared junction: robot_2 runs along x and robot_3 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured', 'grounding=dynamic_arms:crossing_refused:robot_2,robot_3']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no declared junction: robot_2 runs along x and robot_3 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no declared junction: robot_2 runs along x and robot_3 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 929335f4a4774da5b32f3f1f8c60c56d at 74.6 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}]
- Justification: Robots 2 and 3, as well as robots 4 and 5, are head-on and within 0.5 m of each other, so reversing is necessary to open up space and resolve the blockage.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2', 'robot_3', 'robot_4', 'robot_5'], 'involved': ['robot_2', 'robot_3', 'robot_4', 'robot_5']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_2: reverse infeasible: robot_2/robot_3 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}, {'op': 'substitute', 'reason': "robot_3: reverse infeasible: robot_2/robot_3 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:crossing_undeclared']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_3', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_4', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_5', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 2acc6130567a488eb03f234447dbe2da at 87.233 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}]
- Justification: Both robot pairs (2/3 and 4/5) are facing each other at distances under 0.5 m. Having them reverse will clear the localized blocks.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2', 'robot_3', 'robot_4', 'robot_5'], 'involved': ['robot_2', 'robot_3', 'robot_4', 'robot_5']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_2: reverse infeasible: robot_2/robot_3 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}, {'op': 'substitute', 'reason': "robot_3: reverse infeasible: robot_2/robot_3 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held True, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_3', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_4', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_5', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 6e4c8849a89a41c4820fa86606f59391 at 99.767 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], type deadlock
- Plan legs (model): None
- Justification: Robots 1, 2, and 3 are in a multi-way conflict on the right side, and robots 4 and 5 on the left side, requiring coordinated wait, reverse, and cross actions to clear the aisles.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b07a700f:robot_1:reverse | reverse | 1.3 | 30.067 | 31.7 | 44.547 | COMPLETED | 1.205 | 0.927 | 0.3504 (rack/SW_west) | None (None) | completed | False |
| b07a700f:robot_2:reverse | reverse | 1.3 | 30.067 | 31.7 | 44.48 | COMPLETED | 1.202 | 0.924 | 0.0822 (obstacle_2) | None (None) | completed | False |
| b07a700f:robot_3:reverse | reverse | 1.3 | 30.067 | 31.734 | 44.523 | COMPLETED | 1.209 | 0.93 | 0.3134 (rack/SE_east) | None (None) | completed | False |
| 95066420:robot_4:reverse | reverse | 1.3 | 49.067 | 50.4 | 63.371 | COMPLETED | 1.206 | 0.928 | 0.0055 (obstacle_1) | None (None) | completed | False |
| 95066420:robot_5:reverse | reverse | 1.3 | 49.067 | 50.4 | 63.217 | COMPLETED | 1.205 | 0.927 | 0.0191 (obstacle_1) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 32.525, 'pairs': 'robot_1+robot_2,robot_1+robot_3,robot_2+robot_3'}, {'rel': 44.694, 'pairs': '-'}, {'rel': 49.35, 'pairs': 'robot_4+robot_5'}, {'rel': 63.41, 'pairs': '-'}]
- Safety-stop spans: robot_1|min_distance_violation: 2 spans; robot_4|min_distance_violation: 3 spans; robot_2|min_distance_violation: 2 spans; robot_3|min_distance_violation: 2 spans; robot_5|min_distance_violation: 2 spans

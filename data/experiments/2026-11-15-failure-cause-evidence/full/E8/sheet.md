# Evidence Sheet E8

- Censoring: t_end 577.27 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=6 max residual 0.005 s
- Outcome fields (frozen, copied): {"censor_reason": "horizon", "source": "[O] batch5/agg_b5.json gridlock.tasks_completed, gridlock.gt_end_rel_s; censor [P] batch6/s1_scoring_pilots.jsonl", "t_end_rel": 577.3, "tasks_completed": 3, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4, robot_5 | 25.07 | 577.27 | False | f06c33b3:robot_2:reverse, f06c33b3:robot_4:reverse | - |

### FU1

- Pairs: [['robot_1', 'robot_4'], ['robot_2', 'robot_3'], ['robot_2', 'robot_4'], ['robot_2', 'robot_5'], ['robot_3', 'robot_4'], ['robot_3', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 18.5 rel-s
- V1 input: {'a33_matched_positive_analyses': 2, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_4'], 'close_and_stopped_from_rel': 64.57, 'until_rel': 577.27}, {'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 46.77, 'until_rel': 577.27}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 46.77, 'until_rel': 577.27}, {'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 46.77, 'until_rel': 577.27}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 26.07, 'until_rel': 577.27}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 25.47, 'until_rel': 577.27}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 64.37, 'to_rel': 577.27, 'duration_s': 512.9, 'to_censor': True, 'safety_stop_cover_fraction': 0.974}, {'robot': 'robot_2', 'from_rel': 46.47, 'to_rel': 577.27, 'duration_s': 530.8, 'to_censor': True, 'safety_stop_cover_fraction': 0.984}, {'robot': 'robot_3', 'from_rel': 25.07, 'to_rel': 577.27, 'duration_s': 552.2, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 62.57, 'to_rel': 577.27, 'duration_s': 514.7, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_5', 'from_rel': 25.37, 'to_rel': 577.27, 'duration_s': 551.9, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 10.284 | safety_stop_span | robot_2 | to 20.009 (1983 lines) |
| 10.304 | safety_stop_span | robot_4 | to 20.009 (1983 lines) |
| 14.7 | analysis | 7003517d426b40e3a54db03aa3be3b04 | positive strategy=yield involved=['robot_2', 'robot_4'] yield=robot_2 |
| 14.7 | withheld | 7003517d426b40e3a54db03aa3be3b04 | robot_2:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 18.5 | analysis | f06c33b31fde441f9cb6a899fbfa73ba | positive strategy=reverse involved=['robot_2', 'robot_4'] yield=None |
| 18.5 | dispatched | f06c33b31fde441f9cb6a899fbfa73ba | robot_2:reverse, robot_4:reverse |
| 19.867 | m4_leg_start | f06c33b3:robot_2:reverse | reverse commanded=1.3 |
| 19.867 | m4_leg_start | f06c33b3:robot_4:reverse | reverse commanded=1.3 |
| 20.012 | exempt_change | - | robot_2+robot_4 |
| 20.87 | gt_submargin | robot_5|box:obstacle_2 | to 21.57 min gap 0.0451 m |
| 25.252 | safety_stop_span | robot_5 | to 698.463 (139847 lines) |
| 25.268 | safety_stop_span | robot_3 | to 698.464 (139847 lines) |
| 26.172 | safety_stop_span | robot_4 | to 698.464 (139654 lines) |
| 28.47 | gt_submargin | robot_1|box:obstacle_1 | to 29.67 min gap 0.0241 m |
| 37.829 | m4_terminal | f06c33b3:robot_2:reverse | COMPLETED  moved=1.307 tags=['completed'] deadline=False |
| 54.815 | safety_stop_span | robot_2 | to 698.464 (133786 lines) |
| 55.967 | analysis | 1c801c6ebf4f46699a6c27cb759e26a1 | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 55.967 | withheld | 1c801c6ebf4f46699a6c27cb759e26a1 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 62.481 | m4_terminal | f06c33b3:robot_4:reverse | FAILED  moved=0.529 tags=['not_executed(<50%)', 'stalled_clear(no robot or box within 0.05 m)'] deadline=True |
| 66.033 | analysis | 7cdb641af1234f38a106008faa425877 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 66.033 | withheld | 7cdb641af1234f38a106008faa425877 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 66.4 | m1_stale | robot_1 | STALE 27.8 s |
| 77.677 | safety_stop_span | robot_1 | to 698.464 (129076 lines) |
| 95.4 | m1_stale | robot_1 | STALE 4.8 s |
| 101.8 | m1_stale | robot_1 | STALE 7.87 s |
| 110.833 | m1_stale | robot_1 | STALE 9.17 s |
| 121.233 | m1_stale | robot_1 | STALE 8.37 s |
| 130.733 | m1_stale | robot_1 | STALE 1.9 s |
| 135.2 | m1_stale | robot_1 | STALE 5.4 s |
| 142.067 | m1_stale | robot_1 | STALE 2.23 s |
| 145.533 | m1_stale | robot_1 | STALE 11.2 s |
| 157.8 | m1_stale | robot_1 | STALE 17.1 s |
| 176.033 | m1_stale | robot_1 | STALE 8.33 s |
| 185.4 | m1_stale | robot_1 | STALE 24.57 s |
| 212.2 | m1_stale | robot_1 | STALE 0.4 s |
| 213.8 | m1_stale | robot_1 | STALE 21.83 s |
| 237.0 | m1_stale | robot_1 | STALE 6.43 s |
| 244.667 | m1_stale | robot_1 | STALE 2.67 s |
| 248.7 | m1_stale | robot_1 | STALE 7.0 s |
| 256.9 | m1_stale | robot_1 | STALE 19.8 s |
| 277.9 | m1_stale | robot_1 | STALE 68.07 s |
| 347.167 | m1_stale | robot_1 | STALE 24.33 s |
| 372.7 | m1_stale | robot_1 | STALE 14.93 s |
| 388.867 | m1_stale | robot_1 | STALE 6.33 s |
| 396.167 | m1_stale | robot_1 | STALE 9.33 s |
| 406.7 | m1_stale | robot_1 | STALE 2.23 s |
| 410.033 | m1_stale | robot_1 | STALE 0.67 s |
| 411.7 | m1_stale | robot_1 | STALE 9.93 s |
| 422.833 | m1_stale | robot_1 | STALE 9.17 s |
| 433.233 | m1_stale | robot_1 | STALE 23.77 s |
| 458.033 | m1_stale | robot_1 | STALE 8.07 s |
| 467.267 | m1_stale | robot_1 | STALE 8.97 s |
| 477.4 | m1_stale | robot_1 | STALE 23.9 s |
| 502.5 | m1_stale | robot_1 | STALE 27.53 s |
| 531.167 | m1_stale | robot_1 | STALE 7.87 s |
| 540.2 | m1_stale | robot_1 | STALE 0.4 s |
| 541.8 | m1_stale | robot_1 | STALE 3.2 s |
| 546.2 | m1_stale | robot_1 | STALE 4.6 s |
| 552.0 | m1_stale | robot_1 | STALE 5.83 s |
| 559.0 | m1_stale | robot_1 | STALE 10.9 s |
| 571.6 | m1_stale | robot_1 | STALE 5.2 s |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 25.5 | episode_gate_pass / episode_gate_pass | 122/237 | 122/237 | 122/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| 1c801c6ebf4f46699a6c27cb759e26a1 | 55.967 | pass / pass | 89/237 | 89/237 | 77/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| 7cdb641af1234f38a106008faa425877 | 66.033 | pass / pass | 165/237 | 165/237 | 141/237 | True | {'robot': 'robot_1', 'heading_deg': 225, 'distance_m': 0.03} |

## Decisions

### 7003517d426b40e3a54db03aa3be3b04 at 14.7 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_4'], yield_robot robot_2, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 2 is currently moving very slowly and should yield to let the faster-moving Robot 4 pass safely.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_2'], 'yield_robot': 'robot_2'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_4 has no retreat candidate surviving the sweep), held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_4 has no retreat candidate surviving the sweep)', 'would_dispatch_robot_ids': ['robot_2', 'robot_4']}, yield refusal yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_4 has no retreat candidate surviving the sweep), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_4 has no retreat candidate surviving the sweep)', 'grounding=dynamic_arms:lane:y']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_4 has no retreat candidate surviving the sweep)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_4 has no retreat candidate surviving the sweep)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### f06c33b31fde441f9cb6a899fbfa73ba at 18.5 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Both robots need to reverse to clear the narrow passage and resolve the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2', 'robot_4'], 'involved': ['robot_2', 'robot_4']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:lane:y']
- Actions: [('robot_2', 'reverse', {'backup_distance_m': 1.3}), ('robot_4', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 1c801c6ebf4f46699a6c27cb759e26a1 at 55.967 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_3', 'robot_2', 'robot_4', 'robot_5'], type crowding
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}]
- Justification: A junction clear is necessary to resolve the multi-robot conflict at the tight bottom passage by coordinating the order of moves.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 7cdb641af1234f38a106008faa425877 at 66.033 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_1', 'robot_3', 'robot_4', 'robot_2', 'robot_5'], type crowding
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_5'}]
- Justification: Robot 5 and Robot 2 are blocking the lane for Robot 1 and Robot 3; we need to clear the junction by reversing or yielding robot 5 first, then letting others pass.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_1: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}, {'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| f06c33b3:robot_2:reverse | reverse | 1.3 | 18.5 | 19.867 | 37.829 | COMPLETED | 1.307 | 1.006 | 0.0582 (obstacle_2) | None (None) | completed | False |
| f06c33b3:robot_4:reverse | reverse | 1.3 | 18.5 | 19.867 | 62.481 | FAILED | 0.529 | 0.407 | 0.338 (obstacle_2) | None (None) | not_executed(<50%); stalled_clear(no robot or box within 0.05 m) | True |

## Perception STALE Spans of 10 s or More

{"robot_1": [{"from_rel": 66.4, "to_rel": 94.2, "duration_s": 27.8, "ge_10s": true}, {"from_rel": 95.4, "to_rel": 100.2, "duration_s": 4.8, "ge_10s": false}, {"from_rel": 101.8, "to_rel": 109.667, "duration_s": 7.87, "ge_10s": false}, {"from_rel": 110.833, "to_rel": 120.0, "duration_s": 9.17, "ge_10s": false}, {"from_rel": 121.233, "to_rel": 129.6, "duration_s": 8.37, "ge_10s": false}, {"from_rel": 130.733, "to_rel": 132.633, "duration_s": 1.9, "ge_10s": false}, {"from_rel": 135.2, "to_rel": 140.6, "duration_s": 5.4, "ge_10s": false}, {"from_rel": 142.067, "to_rel": 144.3, "duration_s": 2.23, "ge_10s": false}, {"from_rel": 145.533, "to_rel": 156.733, "duration_s": 11.2, "ge_10s": true}, {"from_rel": 157.8, "to_rel": 174.9, "duration_s": 17.1, "ge_10s": true}, {"from_rel": 176.033, "to_rel": 184.367, "duration_s": 8.33, "ge_10s": false}, {"from_rel": 185.4, "to_rel": 209.967, "duration_s": 24.57, "ge_10s": true}, {"from_rel": 212.2, "to_rel": 212.6, "duration_s": 0.4, "ge_10s": false}, {"from_rel": 213.8, "to_rel": 235.633, "duration_s": 21.83, "ge_10s": true}, {"from_rel": 237.0, "to_rel": 243.433, "duration_s": 6.43, "ge_10s": false}, {"from_rel": 244.667, "to_rel": 247.333, "duration_s": 2.67, "ge_10s": false}, {"from_rel": 248.7, "to_rel": 255.7, "duration_s": 7.0, "ge_10s": false}, {"from_rel": 256.9, "to_rel": 276.7, "duration_s": 19.8, "ge_10s": true}, {"from_rel": 277.9, "to_rel": 345.967, "duration_s": 68.07, "ge_10s": true}, {"from_rel": 347.167, "to_rel": 371.5, "duration_s": 24.33, "ge_10s": true}, {"from_rel": 372.7, "to_rel": 387.633, "duration_s": 14.93, "ge_10s": true}, {"from_rel": 388.867, "to_rel": 395.2, "duration_s": 6.33, "ge_10s": false}, {"from_rel": 396.167, "to_rel": 405.5, "duration_s": 9.33, "ge_10s": false}, {"from_rel": 406.7, "to_rel": 408.933, "duration_s": 2.23, "ge_10s": false}, {"from_rel": 410.033, "to_rel": 410.7, "duration_s": 0.67, "ge_10s": false}, {"from_rel": 411.7, "to_rel": 421.633, "duration_s": 9.93, "ge_10s": false}, {"from_rel": 422.833, "to_rel": 432.0, "duration_s": 9.17, "ge_10s": false}, {"from_rel": 433.233, "to_rel": 457.0, "duration_s": 23.77, "ge_10s": true}, {"from_rel": 458.033, "to_rel": 466.1, "duration_s": 8.07, "ge_10s": false}, {"from_rel": 467.267, "to_rel": 476.233, "duration_s": 8.97, "ge_10s": false}, {"from_rel": 477.4, "to_rel": 501.3, "duration_s": 23.9, "ge_10s": true}, {"from_rel": 502.5, "to_rel": 530.033, "duration_s": 27.53, "ge_10s": true}, {"from_rel": 531.167, "to_rel": 539.033, "duration_s": 7.87, "ge_10s": false}, {"from_rel": 540.2, "to_rel": 540.6, "duration_s": 0.4, "ge_10s": false}, {"from_rel": 541.8, "to_rel": 545.0, "duration_s": 3.2, "ge_10s": false}, {"from_rel": 546.2, "to_rel": 550.8, "duration_s": 4.6, "ge_10s": false}, {"from_rel": 552.0, "to_rel": 557.833, "duration_s": 5.83, "ge_10s": false}, {"from_rel": 559.0, "to_rel": 569.9, "duration_s": 10.9, "ge_10s": true}, {"from_rel": 571.6, "to_rel": 576.8, "duration_s": 5.2, "ge_10s": false}]}

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 20.012, 'pairs': 'robot_2+robot_4'}, {'rel': 62.517, 'pairs': '-'}]
- Safety-stop spans: robot_2|min_distance_violation: 2 spans; robot_4|min_distance_violation: 2 spans; robot_5|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_1|min_distance_violation: 1 spans

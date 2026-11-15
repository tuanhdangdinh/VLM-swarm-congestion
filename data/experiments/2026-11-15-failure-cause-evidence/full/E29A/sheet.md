# Evidence Sheet E29A

- Censoring: t_end 570.073 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=20 max residual 0.447 s
- Outcome fields (frozen, copied): {"a33_involved_f1": [1.0, 1.0, null], "a33_n_conflicts": 3, "a33_n_detected": 2, "a33_type_correct": [true, true, null], "censor_reason": "horizon", "completeness_status": "failed", "source": "[T] batch6/scores_t1/s1_scoring.jsonl", "t_end_rel": 570.073333334, "tasks_completed": 0, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_3, robot_5 | 19.373 | 570.073 | False | - | - |
| FU2 | conflict | robot_1, robot_4 | 72.673 | 570.073 | False | 14aefebe:robot_1:backup, 14aefebe:robot_4:escort, 14aefebe:robot_4:wait | - |

### FU1

- Pairs: [['robot_2', 'robot_3'], ['robot_2', 'robot_5'], ['robot_3', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 3, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 22.57, 'until_rel': 570.07}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 204.57, 'until_rel': 570.07}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 105.67, 'to_rel': 570.07, 'duration_s': 464.4, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 204.27, 'to_rel': 570.07, 'duration_s': 365.8, 'to_censor': True, 'safety_stop_cover_fraction': 0.996}, {'robot': 'robot_5', 'from_rel': 195.87, 'to_rel': 570.07, 'duration_s': 374.2, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 12.57 | gt_submargin | robot_2|box:obstacle_2 | to 14.07 min gap 0.0071 m |
| 19.296 | safety_stop_span | robot_3 | to 77.271 (13896 lines) |
| 19.307 | safety_stop_span | robot_2 | to 592.245 (136653 lines) |
| 22.431 | safety_stop_span | robot_5 | to 592.245 (135912 lines) |
| 24.867 | m1_stale | robot_5 | STALE 0.4 s |
| 31.867 | m1_stale | robot_5 | STALE 0.83 s |
| 34.467 | m1_stale | robot_5 | STALE 1.9 s |
| 37.6 | m1_stale | robot_5 | STALE 0.47 s |
| 52.033 | m1_stale | robot_5 | STALE 4.33 s |
| 57.733 | m1_stale | robot_5 | STALE 11.27 s |
| 72.333 | m1_stale | robot_5 | STALE 44.7 s |
| 75.5 | analysis | 5622ed9cf4cd44e89ec752f4b9d49ca6 | positive strategy=yield involved=['robot_2', 'robot_3', 'robot_5'] yield=robot_2 |
| 75.5 | dispatched | 5622ed9cf4cd44e89ec752f4b9d49ca6 | robot_3:yield, robot_2:temporary_wait, robot_5:temporary_wait |
| 77.276 | exempt_change | - | robot_2+robot_3,robot_3+robot_5 |
| 77.333 | m4_leg_start | 5622ed9c:robot_3:backup | backup commanded=1.285 |
| 107.267 | m1_stale | robot_3 | STALE 0.57 s |
| 118.4 | m1_stale | robot_5 | STALE 28.2 s |
| 147.833 | m1_stale | robot_5 | STALE 6.2 s |
| 165.6 | m1_stale | robot_5 | STALE 1.53 s |
| 171.767 | m1_stale | robot_5 | STALE 27.3 s |
| 195.844 | m4_terminal | 5622ed9c:robot_3:backup | COMPLETED  moved=1.349 tags=['completed'] deadline=False |
| 199.0 | analysis | 40b4c0c975cc4005a065dc1fbcf8e0f7 | positive strategy=yield involved=['robot_2', 'robot_5'] yield=robot_5 |
| 199.0 | withheld | 40b4c0c975cc4005a065dc1fbcf8e0f7 | robot_5:temporary_wait, robot_2:temporary_wait withheld=refusal_no_action |
| 200.333 | m1_stale | robot_5 | STALE 3.9 s |
| 205.433 | m1_stale | robot_5 | STALE 77.53 s |
| 205.591 | safety_stop_span | robot_3 | to 592.245 (92048 lines) |
| 206.667 | analysis | ca3aecdfc6fa4aac8bcfac58cae0c725 | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_5'] yield=None |
| 206.667 | withheld | ca3aecdfc6fa4aac8bcfac58cae0c725 | robot_2:temporary_wait, robot_3:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 284.1 | m1_stale | robot_5 | STALE 7.23 s |
| 292.633 | m1_stale | robot_5 | STALE 62.8 s |
| 357.433 | m1_stale | robot_5 | STALE 0.2 s |
| 359.8 | m1_stale | robot_5 | STALE 0.4 s |
| 361.567 | m1_stale | robot_5 | STALE 21.0 s |
| 384.4 | m1_stale | robot_5 | STALE 57.0 s |
| 445.0 | m1_stale | robot_5 | STALE 3.17 s |
| 451.3 | m1_stale | robot_5 | STALE 3.97 s |
| 460.5 | m1_stale | robot_5 | STALE 4.03 s |
| 470.133 | m1_stale | robot_5 | STALE 3.77 s |
| 476.533 | m1_stale | robot_5 | STALE 0.6 s |
| 479.733 | m1_stale | robot_5 | STALE 0.63 s |
| 481.833 | m1_stale | robot_5 | STALE 1.6 s |
| 486.333 | m1_stale | robot_5 | STALE 20.2 s |
| 508.8 | m1_stale | robot_5 | STALE 24.97 s |
| 534.733 | m1_stale | robot_5 | STALE 5.63 s |
| 543.733 | m1_stale | robot_5 | STALE 0.8 s |
| 545.8 | m1_stale | robot_5 | STALE 2.93 s |
| 551.333 | m1_stale | robot_5 | STALE 0.2 s |
| 554.367 | m1_stale | robot_5 | STALE 9.1 s |
| 564.933 | m1_stale | robot_5 | STALE 0.8 s |
| 568.367 | m1_stale | robot_5 | STALE 1.33 s |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 19.567 | U:T1_fidelity / episode_gate_pass | 96/237 | 96/237 | 96/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| 5622ed9cf4cd44e89ec752f4b9d49ca6 | 75.5 | pass / pass | 99/237 | 99/237 | 81/237 | True | {'robot': 'robot_3', 'heading_deg': 225, 'distance_m': 0.02} |
| 40b4c0c975cc4005a065dc1fbcf8e0f7 | 199.0 | pass / pass | 82/237 | 82/237 | 78/237 | True | {'robot': 'robot_3', 'heading_deg': 0, 'distance_m': 0.01} |
| ca3aecdfc6fa4aac8bcfac58cae0c725 | 206.667 | pass / pass | 34/237 | 34/237 | 16/237 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.03} |

### FU2

- Pairs: [['robot_1', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 22.4 rel-s
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_4'], 'close_and_stopped_from_rel': 72.97, 'until_rel': 570.07}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 72.67, 'to_rel': 570.07, 'duration_s': 497.4, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 72.87, 'to_rel': 570.07, 'duration_s': 497.2, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 15.504 | safety_stop_span | robot_4 | to 25.312 (2329 lines) |
| 15.517 | safety_stop_span | robot_1 | to 25.312 (2329 lines) |
| 18.267 | analysis | 988fd4c5b5bc4c9aa2c58a2231d5fe55 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 18.267 | withheld | 988fd4c5b5bc4c9aa2c58a2231d5fe55 | robot_1:reroute, robot_4:temporary_wait withheld=empty_reroute |
| 22.4 | analysis | 14aefebe6c4b472d85194ae4c093d2b2 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 22.4 | dispatched | 14aefebe6c4b472d85194ae4c093d2b2 | robot_1:yield, robot_4:temporary_wait |
| 25.066 | m4_leg_start | 14aefebe:robot_1:backup | backup commanded=1.485 |
| 25.313 | exempt_change | - | robot_1+robot_4 |
| 55.1 | m4_leg_start | 14aefebe:robot_4:escort | escort commanded=1.538 |
| 71.655 | m4_terminal | 14aefebe:robot_1:backup | COMPLETED  moved=1.543 tags=['completed'] deadline=False |
| 71.695 | m4_terminal | 14aefebe:robot_4:escort | COMPLETED escort complete: moved 1.539 m moved=1.53 tags=['completed'] deadline=False |
| 72.391 | safety_stop_span | robot_4 | to 592.245 (123923 lines) |
| 72.393 | safety_stop_span | robot_1 | to 592.246 (123923 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 72.7 | U:T1_fidelity / episode_gate_pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.02} |

## Decisions

### 988fd4c5b5bc4c9aa2c58a2231d5fe55 at 18.267 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_1, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Since robot_1 is stopped and robot_4 is moving slowly towards its goal, robot_1 should yield (back up) to clear the narrow passage for robot_4.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield degrades to reroute: robot_1 has no retreat candidate clearing its park point (escort_hits_park:robot_4:0.262), held False, dispatch_matches_plan True
- Grounding: published False, withheld {'fallback_reason': 'yield=infeasible:escort_hits_park:robot_4:0.262', 'reason': 'empty_reroute', 'would_dispatch_robot_ids': ['robot_1', 'robot_4']}, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=escort_park_filtered:A:robot_4:0.262', 'yield=infeasible:escort_hits_park:robot_4:0.262', 'grounding=dynamic_arms:lane:y']
- Actions: [('robot_1', 'reroute', {'waypoints': []}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 14aefebe6c4b472d85194ae4c093d2b2 at 22.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_1, crossing_order ['robot_4', 'robot_1'], type deadlock
- Plan legs (model): None
- Justification: Robot 1 should yield or reroute to allow Robot 4 to pass through the lane, as currently planned in the active plan.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=escort_park_filtered:B:robot_4:0.263', 'grounding=dynamic_arms:lane:y', 'grounding=escort_turn_cap:robot_4:2.35->1.538']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.485, 'crossing_order': ['robot_4'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 1.538, 'passer_robot_id': 'robot_4', 'reason': 'Robot 1 and Robot 4 have encountered each other head-on in a narrow corridor, and both are currently stopped.', 'retreat_choice': 'A'}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 5622ed9cf4cd44e89ec752f4b9d49ca6 at 75.5 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3', 'robot_5'], yield_robot robot_2, crossing_order ['robot_5', 'robot_3', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Robot_2 should yield and back up to allow robot_5 to pass and proceed to its eastward destination.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_2'], 'yield_robot': 'robot_2'}}
- Plan verifier: provenance repaired, edits [{'op': 'reorder', 'reason': 'reordered; robot_5 and robot_3 exchanged position', 'robot_ids': ['robot_3', 'robot_5']}, {'op': 'swap', 'reason': 'yield re-grounded: robot_2 has 0.58 m retreat room < 0.74 m required; swapped roles robot_2 (yield) <-> robot_3 (cross)', 'robot_ids': ['robot_2', 'robot_3']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=default:no_choice', 'grounding=node_handoff:robot_3->robot_2', 'grounding=node_handoff_regrounded:robot_2->robot_3', 'grounding=dynamic_arms:bearing_lane:robot_2:32', 'grounding=dynamic_arms:lane:y', 'grounding=escort_off:robot_2:goal_reached']
- Actions: [('robot_3', 'yield', {'backup_distance_m': 1.285, 'crossing_order': ['robot_2', 'robot_5'], 'fresh_latch_fast_fail': True, 'passer_robot_id': 'robot_2', 'reason': 'Robot_2 and robot_5 are head-on blocking each other in a narrow corridor, with robot_3 queued behind robot_2.', 'retreat_choice': 'A'}), ('robot_2', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_3->robot_2', 'grounding=node_handoff_regrounded:robot_2->robot_3'], 'G6_verbatim_contradicted': False}

### 40b4c0c975cc4005a065dc1fbcf8e0f7 at 199.0 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_5'], yield_robot robot_5, crossing_order ['robot_2', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Robot 5 faces Robot 2 and vice versa within a very small distance. Robot 5 should yield to let Robot 2 clear the junction.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_5 has no retreat candidate surviving the sweep; robot_2 would back up off its retreat axis), held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_5 has no retreat candidate surviving the sweep; robot_2 would back up off its retreat axis)', 'would_dispatch_robot_ids': ['robot_5', 'robot_2']}, yield refusal yield refused: no executable retreat (robot_5 has no retreat candidate surviving the sweep; robot_2 would back up off its retreat axis), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_5 has no retreat candidate surviving the sweep; robot_2 would back up off its retreat axis)', 'grounding=dynamic_arms:bearing_lane:robot_2:32', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_5', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_5 has no retreat candidate surviving the sweep; robot_2 would back up off its retreat axis)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_5 has no retreat candidate surviving the sweep; robot_2 would back up off its retreat axis)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### ca3aecdfc6fa4aac8bcfac58cae0c725 at 206.667 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_5'], yield_robot None, crossing_order ['robot_3', 'robot_2', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_5'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Having robot_5 reverse creates the necessary clearance for robot_3 and robot_2 to resolve their conflict and move through the passage safely.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 14aefebe:robot_1:backup | backup | 1.485 | 22.4 | 25.066 | 71.655 | COMPLETED | 1.543 | 1.039 | 0.1493 (rack/NW_north) | None (None) | completed | False |
| 14aefebe:robot_4:escort | escort | 1.538 | 22.4 | 55.1 | 71.695 | COMPLETED | 1.53 | 0.995 | 0.4195 (rack/NW_north) | None (None) | completed | False |
| 5622ed9c:robot_3:backup | backup | 1.285 | 75.5 | 77.333 | 195.844 | COMPLETED | 1.349 | 1.05 | 0.0869 (obstacle_1) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

{"robot_5": [{"from_rel": 24.867, "to_rel": 25.267, "duration_s": 0.4, "ge_10s": false}, {"from_rel": 31.867, "to_rel": 32.7, "duration_s": 0.83, "ge_10s": false}, {"from_rel": 34.467, "to_rel": 36.367, "duration_s": 1.9, "ge_10s": false}, {"from_rel": 37.6, "to_rel": 38.067, "duration_s": 0.47, "ge_10s": false}, {"from_rel": 52.033, "to_rel": 56.367, "duration_s": 4.33, "ge_10s": false}, {"from_rel": 57.733, "to_rel": 69.0, "duration_s": 11.27, "ge_10s": true}, {"from_rel": 72.333, "to_rel": 117.033, "duration_s": 44.7, "ge_10s": true}, {"from_rel": 118.4, "to_rel": 146.6, "duration_s": 28.2, "ge_10s": true}, {"from_rel": 147.833, "to_rel": 154.033, "duration_s": 6.2, "ge_10s": false}, {"from_rel": 165.6, "to_rel": 167.133, "duration_s": 1.53, "ge_10s": false}, {"from_rel": 171.767, "to_rel": 199.067, "duration_s": 27.3, "ge_10s": true}, {"from_rel": 200.333, "to_rel": 204.233, "duration_s": 3.9, "ge_10s": false}, {"from_rel": 205.433, "to_rel": 282.967, "duration_s": 77.53, "ge_10s": true}, {"from_rel": 284.1, "to_rel": 291.333, "duration_s": 7.23, "ge_10s": false}, {"from_rel": 292.633, "to_rel": 355.433, "duration_s": 62.8, "ge_10s": true}, {"from_rel": 357.433, "to_rel": 357.633, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 359.8, "to_rel": 360.2, "duration_s": 0.4, "ge_10s": false}, {"from_rel": 361.567, "to_rel": 382.567, "duration_s": 21.0, "ge_10s": true}, {"from_rel": 384.4, "to_rel": 441.4, "duration_s": 57.0, "ge_10s": true}, {"from_rel": 445.0, "to_rel": 448.167, "duration_s": 3.17, "ge_10s": false}, {"from_rel": 451.3, "to_rel": 455.267, "duration_s": 3.97, "ge_10s": false}, {"from_rel": 460.5, "to_rel": 464.533, "duration_s": 4.03, "ge_10s": false}, {"from_rel": 470.133, "to_rel": 473.9, "duration_s": 3.77, "ge_10s": false}, {"from_rel": 476.533, "to_rel": 477.133, "duration_s": 0.6, "ge_10s": false}, {"from_rel": 479.733, "to_rel": 480.367, "duration_s": 0.63, "ge_10s": false}, {"from_rel": 481.833, "to_rel": 483.433, "duration_s": 1.6, "ge_10s": false}, {"from_rel": 486.333, "to_rel": 506.533, "duration_s": 20.2, "ge_10s": true}, {"from_rel": 508.8, "to_rel": 533.767, "duration_s": 24.97, "ge_10s": true}, {"from_rel": 534.733, "to_rel": 540.367, "duration_s": 5.63, "ge_10s": false}, {"from_rel": 543.733, "to_rel": 544.533, "duration_s": 0.8, "ge_10s": false}, {"from_rel": 545.8, "to_rel": 548.733, "duration_s": 2.93, "ge_10s": false}, {"from_rel": 551.333, "to_rel": 551.533, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 554.367, "to_rel": 563.467, "duration_s": 9.1, "ge_10s": false}, {"from_rel": 564.933, "to_rel": 565.733, "duration_s": 0.8, "ge_10s": false}, {"from_rel": 568.367, "to_rel": 569.7, "duration_s": 1.33, "ge_10s": false}]}

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 25.313, 'pairs': 'robot_1+robot_4'}, {'rel': 71.71, 'pairs': '-'}, {'rel': 77.276, 'pairs': 'robot_2+robot_3,robot_3+robot_5'}, {'rel': 195.854, 'pairs': '-'}]
- Safety-stop spans: robot_4|min_distance_violation: 2 spans; robot_1|min_distance_violation: 2 spans; robot_3|min_distance_violation: 2 spans; robot_2|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans

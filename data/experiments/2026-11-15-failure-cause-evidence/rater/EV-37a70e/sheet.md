# Evidence Sheet EV-37a70e

- Censoring: t_end 571.173 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=39 max residual 0.412 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_3, robot_4 | 36.573 | 571.173 | False | D2:robot_4:backup | - |
| FU2 | conflict | robot_1, robot_5 | 101.873 | 571.173 | False | D3:robot_1:reverse, D3:robot_5:reverse | - |

### FU1

- Pairs: [['robot_2', 'robot_3'], ['robot_2', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 30.0 rel-s
- V1 input: {'a33_matched_positive_analyses': 4, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 36.77, 'until_rel': 571.17}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 133.27, 'until_rel': 571.17}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 36.27, 'to_rel': 97.47, 'duration_s': 61.2, 'to_censor': False, 'safety_stop_cover_fraction': 0.994}, {'robot': 'robot_2', 'from_rel': 146.47, 'to_rel': 571.17, 'duration_s': 424.7, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 36.67, 'to_rel': 97.47, 'duration_s': 60.8, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 146.47, 'to_rel': 571.17, 'duration_s': 424.7, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 146.47, 'to_rel': 571.17, 'duration_s': 424.7, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_2|box:obstacle_1: [35.97, 571.17] -0.0001; robot_4|box:obstacle_1: [39.87, 74.27] -0.0057

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 12.67 | gt_submargin | robot_2|box:obstacle_2 | to 13.87 min gap 0.0266 m |
| 25.133 | m1_stale | robot_3 | STALE 1.07 s |
| 27.307 | safety_stop_span | robot_4 | to 33.902 (1603 lines) |
| 30.0 | analysis | D2 | positive strategy=yield involved=['robot_4', 'robot_5'] yield=robot_4 |
| 30.0 | dispatched | D2 | robot_4:yield, robot_5:temporary_wait |
| 33.6 | m4_leg_start | D2:robot_4:backup | backup commanded=1.395 |
| 33.904 | exempt_change | - | robot_4+robot_5 |
| 35.97 | gt_contact | robot_2|box:obstacle_1 | to 571.17 min gap -0.0001 m |
| 36.617 | safety_stop_span | robot_2 | to 578.638 (134071 lines) |
| 36.626 | safety_stop_span | robot_3 | to 578.638 (134071 lines) |
| 39.87 | gt_contact | robot_4|box:obstacle_1 | to 74.27 min gap -0.0057 m |
| 72.33 | m4_terminal | D2:robot_4:backup | FAILED  moved=0.862 tags=['pinned_on_declared_box:obstacle_1'] deadline=True |
| 77.481 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_1+robot_5,robot_2+robot_5,robot_3+robot_5,robot_4+robot_5 |
| 80.07 | gt_submargin | robot_4|robot_5 | to 80.77 min gap 0.0148 m |
| 91.895 | exempt_change | - | robot_1+robot_5,robot_2+robot_5,robot_3+robot_5,robot_4+robot_5 |
| 95.767 | analysis | D4 | positive strategy=temporary_wait involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 95.767 | dispatched | D4 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait |
| 108.833 | analysis | D5 | positive strategy=temporary_wait involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 108.833 | dispatched | D5 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait |
| 125.0 | m1_stale | robot_4 | STALE 1.13 s |
| 125.238 | safety_stop_span | robot_4 | to 125.238 (1 lines) |
| 125.24 | safety_stop_span | robot_4 | to 126.454 (301 lines) |
| 127.367 | m1_stale | robot_4 | STALE 0.87 s |
| 127.615 | safety_stop_span | robot_4 | to 127.615 (1 lines) |
| 127.616 | safety_stop_span | robot_4 | to 128.308 (171 lines) |
| 133.072 | safety_stop_span | robot_4 | to 578.638 (110173 lines) |
| 136.533 | analysis | D8 | positive strategy=temporary_wait involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 136.533 | dispatched | D8 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait |
| 149.767 | analysis | D9 | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 149.767 | withheld | D9 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 36.667 | U:T1_fidelity / episode_gate_pass | 75/237 | 75/237 | 75/237 | True | {'robot': 'robot_3', 'heading_deg': 90, 'distance_m': 0.01} |
| D4 | 95.767 | pass / pass | 10/237 | 10/237 | 10/237 | True | {'robot': 'robot_3', 'heading_deg': 90, 'distance_m': 0.01} |
| D5 | 108.833 | pass / pass | 12/237 | 12/237 | 12/237 | True | {'robot': 'robot_3', 'heading_deg': 90, 'distance_m': 0.01} |
| D8 | 136.533 | pass / pass | 17/237 | 17/237 | 15/237 | True | {'robot': 'robot_3', 'heading_deg': 90, 'distance_m': 0.01} |
| D9 | 149.767 | pass / pass | 17/237 | 17/237 | 15/237 | True | {'robot': 'robot_3', 'heading_deg': 90, 'distance_m': 0.01} |

### FU2

- Pairs: [['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 76.3 rel-s
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 102.07, 'until_rel': 571.17}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 101.87, 'to_rel': 571.17, 'duration_s': 469.3, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_5', 'from_rel': 101.97, 'to_rel': 571.17, 'duration_s': 469.2, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 46.039 | safety_stop_span | robot_1 | to 77.48 (7805 lines) |
| 46.04 | safety_stop_span | robot_5 | to 77.48 (7805 lines) |
| 76.3 | analysis | D3 | positive strategy=reverse involved=['robot_1', 'robot_5'] yield=None |
| 76.3 | dispatched | D3 | robot_1:reverse, robot_5:reverse |
| 77.481 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_1+robot_5,robot_2+robot_5,robot_3+robot_5,robot_4+robot_5 |
| 77.866 | m4_leg_start | D3:robot_1:reverse | reverse commanded=1.3 |
| 77.866 | m4_leg_start | D3:robot_5:reverse | reverse commanded=1.3 |
| 80.07 | gt_submargin | robot_4|robot_5 | to 80.77 min gap 0.0148 m |
| 91.893 | m4_terminal | D3:robot_1:reverse | COMPLETED  moved=1.261 tags=['completed'] deadline=False |
| 91.895 | exempt_change | - | robot_1+robot_5,robot_2+robot_5,robot_3+robot_5,robot_4+robot_5 |
| 92.009 | m4_terminal | D3:robot_5:reverse | COMPLETED  moved=1.263 tags=['completed'] deadline=False |
| 101.986 | safety_stop_span | robot_1 | to 578.637 (117875 lines) |
| 101.987 | safety_stop_span | robot_5 | to 578.637 (117875 lines) |
| 166.567 | m1_stale | robot_1 | STALE 0.3 s |
| 169.233 | m1_stale | robot_1 | STALE 8.93 s |
| 186.367 | m1_stale | robot_1 | STALE 27.47 s |
| 215.1 | m1_stale | robot_1 | STALE 6.17 s |
| 236.467 | m1_stale | robot_1 | STALE 1.97 s |
| 251.433 | m1_stale | robot_1 | STALE 1.83 s |
| 254.8 | m1_stale | robot_1 | STALE 0.57 s |
| 258.933 | m1_stale | robot_1 | STALE 0.8 s |
| 260.933 | m1_stale | robot_1 | STALE 0.8 s |
| 263.333 | m1_stale | robot_1 | STALE 2.4 s |
| 282.667 | m1_stale | robot_1 | STALE 5.47 s |
| 302.433 | m1_stale | robot_1 | STALE 2.07 s |
| 333.433 | m1_stale | robot_1 | STALE 4.07 s |
| 366.667 | m1_stale | robot_1 | STALE 7.27 s |
| 382.467 | m1_stale | robot_1 | STALE 1.03 s |
| 398.667 | m1_stale | robot_1 | STALE 7.5 s |
| 429.033 | m1_stale | robot_1 | STALE 11.93 s |
| 448.833 | m1_stale | robot_1 | STALE 3.2 s |
| 469.8 | m1_stale | robot_1 | STALE 5.6 s |
| 476.4 | m1_stale | robot_1 | STALE 18.0 s |
| 504.233 | m1_stale | robot_1 | STALE 2.7 s |
| 520.467 | m1_stale | robot_1 | STALE 0.63 s |
| 522.7 | m1_stale | robot_1 | STALE 0.47 s |
| 526.667 | m1_stale | robot_1 | STALE 5.07 s |
| 533.433 | m1_stale | robot_1 | STALE 0.43 s |
| 542.667 | m1_stale | robot_1 | STALE 0.8 s |
| 551.233 | m1_stale | robot_1 | STALE 2.8 s |
| 556.467 | m1_stale | robot_1 | STALE 8.37 s |
| 566.033 | m1_stale | robot_1 | STALE 2.4 s |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 101.933 | U:T1_fidelity / episode_gate_pass | 8/88 | 8/88 | 8/88 | True | {'robot': 'robot_1', 'heading_deg': 45, 'distance_m': 0.02} |

## Decisions

### D1 at 3.233 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: All robots are positioned more than 2 meters apart, and the moving robots have clear paths to proceed toward their goals without intersecting closely.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D2 at 30.0 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_4', 'robot_5'], yield_robot robot_4, crossing_order ['robot_5', 'robot_4'], type bottleneck
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Having robot_4 yield allows robot_5 to clear the area first, resolving the bottleneck.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_4->robot_5', 'grounding=dynamic_arms:lane:x', 'grounding=escort_off:robot_5:goal_behind']
- Actions: [('robot_4', 'yield', {'backup_distance_m': 1.395, 'crossing_order': ['robot_5'], 'passer_robot_id': 'robot_5', 'reason': 'robot_4 is blocked by the stopped robot_5 directly in its path.', 'retreat_choice': 'A'}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_4->robot_5'], 'G6_verbatim_contradicted': False}

### D3 at 76.3 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_1', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_1'}, {'action': 'wait', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Having robot_1 reverse allows both robots to clear the head-on conflict and resume their paths.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_1'], 'involved': ['robot_1', 'robot_5']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:lane:x']
- Actions: [('robot_1', 'reverse', {'backup_distance_m': 1.3}), ('robot_5', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### D4 at 95.767 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order None, type bottleneck
- Plan legs (model): None
- Justification: Robot 4 needs to finish its movement and clear the corridor before Robots 2 and 3 can continue their tasks.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_2', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D5 at 108.833 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order None, type bottleneck
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 is actively moving and has cleared robot 2 and robot 3, meaning they should continue to wait until robot 4 has fully cleared the area.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_4: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}], rejection None, held True, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_2', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D6 at 122.3 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: The previous congestion is successfully resolving as Robot 4 is currently moving to clear the bottleneck.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D7 at 132.133 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: No new congestion detected; the active plan is already managing the flow of robots properly.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D8 at 136.533 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order None, type crowding
- Plan legs (model): None
- Justification: Robot 2, 3, and 4 must remain stopped and wait until robot_1 and robot_5 finish their continuing movements to avoid collision.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held True, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_2', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D9 at 149.767 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_3', 'robot_2', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Since temporary wait did not clear the congestion, a junction clearing plan is needed to coordinate their moves and resolve the spatial conflict.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D2:robot_4:backup | backup | 1.395 | 30.0 | 33.6 | 72.33 | FAILED | 0.862 | 0.618 | -0.0057 (obstacle_1) | None (None) | pinned_on_declared_box:obstacle_1 | True |
| D3:robot_1:reverse | reverse | 1.3 | 76.3 | 77.866 | 91.893 | COMPLETED | 1.261 | 0.97 | 0.0766 (obstacle_2) | None (None) | completed | False |
| D3:robot_5:reverse | reverse | 1.3 | 76.3 | 77.866 | 92.009 | COMPLETED | 1.263 | 0.972 | 0.2339 (rack/SW_south) | 0.0148 (robot_4) | completed | False |

## Perception STALE Spans of 10 s or More

{"robot_1": [{"from_rel": 27.433, "to_rel": 28.733, "duration_s": 1.3, "ge_10s": false}, {"from_rel": 166.567, "to_rel": 166.867, "duration_s": 0.3, "ge_10s": false}, {"from_rel": 169.233, "to_rel": 178.167, "duration_s": 8.93, "ge_10s": false}, {"from_rel": 186.367, "to_rel": 213.833, "duration_s": 27.47, "ge_10s": true}, {"from_rel": 215.1, "to_rel": 221.267, "duration_s": 6.17, "ge_10s": false}, {"from_rel": 236.467, "to_rel": 238.433, "duration_s": 1.97, "ge_10s": false}, {"from_rel": 251.433, "to_rel": 253.267, "duration_s": 1.83, "ge_10s": false}, {"from_rel": 254.8, "to_rel": 255.367, "duration_s": 0.57, "ge_10s": false}, {"from_rel": 258.933, "to_rel": 259.733, "duration_s": 0.8, "ge_10s": false}, {"from_rel": 260.933, "to_rel": 261.733, "duration_s": 0.8, "ge_10s": false}, {"from_rel": 263.333, "to_rel": 265.733, "duration_s": 2.4, "ge_10s": false}, {"from_rel": 282.667, "to_rel": 288.133, "duration_s": 5.47, "ge_10s": false}, {"from_rel": 302.433, "to_rel": 304.5, "duration_s": 2.07, "ge_10s": false}, {"from_rel": 333.433, "to_rel": 337.5, "duration_s": 4.07, "ge_10s": false}, {"from_rel": 366.667, "to_rel": 373.933, "duration_s": 7.27, "ge_10s": false}, {"from_rel": 382.467, "to_rel": 383.5, "duration_s": 1.03, "ge_10s": false}, {"from_rel": 398.667, "to_rel": 406.167, "duration_s": 7.5, "ge_10s": false}, {"from_rel": 429.033, "to_rel": 440.967, "duration_s": 11.93, "ge_10s": true}, {"from_rel": 448.833, "to_rel": 452.033, "duration_s": 3.2, "ge_10s": false}, {"from_rel": 469.8, "to_rel": 475.4, "duration_s": 5.6, "ge_10s": false}, {"from_rel": 476.4, "to_rel": 494.4, "duration_s": 18.0, "ge_10s": true}, {"from_rel": 504.233, "to_rel": 506.933, "duration_s": 2.7, "ge_10s": false}, {"from_rel": 520.467, "to_rel": 521.1, "duration_s": 0.63, "ge_10s": false}, {"from_rel": 522.7, "to_rel": 523.167, "duration_s": 0.47, "ge_10s": false}, {"from_rel": 526.667, "to_rel": 531.733, "duration_s": 5.07, "ge_10s": false}, {"from_rel": 533.433, "to_rel": 533.867, "duration_s": 0.43, "ge_10s": false}, {"from_rel": 542.667, "to_rel": 543.467, "duration_s": 0.8, "ge_10s": false}, {"from_rel": 551.233, "to_rel": 554.033, "duration_s": 2.8, "ge_10s": false}, {"from_rel": 556.467, "to_rel": 564.833, "duration_s": 8.37, "ge_10s": false}, {"from_rel": 566.033, "to_rel": 568.433, "duration_s": 2.4, "ge_10s": false}]}

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 33.904, 'pairs': 'robot_4+robot_5'}, {'rel': 72.375, 'pairs': '-'}, {'rel': 77.481, 'pairs': 'robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_1+robot_5,robot_2+robot_5,robot_3+robot_5,robot_4+robot_5'}, {'rel': 91.895, 'pairs': 'robot_1+robot_5,robot_2+robot_5,robot_3+robot_5,robot_4+robot_5'}, {'rel': 92.08, 'pairs': '-'}]
- Safety-stop spans: robot_5|min_distance_violation: 3 spans; robot_4|min_distance_violation: 4 spans; robot_2|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_1|min_distance_violation: 2 spans; robot_4|stale_pose_unsafe: 2 spans

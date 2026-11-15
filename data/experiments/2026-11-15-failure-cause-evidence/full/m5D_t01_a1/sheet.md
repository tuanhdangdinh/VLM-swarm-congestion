# Evidence Sheet m5D_t01_a1

- Censoring: t_end 568.54 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=26 max residual 0.975 s
- Outcome fields (frozen, copied): {"source": "[R] rubric 5.3 row (demo report figure)", "text": "1 of 5 arrived (GT 0.3 m), tasks 1/25, 600 sim-s horizon"}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_4, robot_5 | 69.04 | 568.54 | False | 03bba450:robot_1:backup, 03bba450:robot_4:escort, 03bba450:robot_4:wait, 03bba450:robot_5:wait | - |
| FU2 | conflict | robot_2, robot_3 | 240.94 | 568.54 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_4'], ['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 12.367 rel-s
- V1 input: {'a33_matched_positive_analyses': 6, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_4'], 'close_and_stopped_from_rel': 69.24, 'until_rel': 568.54}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 179.84, 'until_rel': 568.54}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 69.14, 'to_rel': 568.54, 'duration_s': 499.4, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 69.04, 'to_rel': 568.54, 'duration_s': 499.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_5', 'from_rel': 179.74, 'to_rel': 568.54, 'duration_s': 388.8, 'to_censor': True, 'safety_stop_cover_fraction': 0.99}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 10.099 | safety_stop_span | robot_1 | to 14.163 (933 lines) |
| 10.108 | safety_stop_span | robot_4 | to 14.163 (933 lines) |
| 12.367 | analysis | 03bba450201447b78f13d94589a1ade5 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 12.367 | dispatched | 03bba450201447b78f13d94589a1ade5 | robot_1:yield, robot_4:temporary_wait, robot_5:temporary_wait, robot_3:temporary_wait |
| 14.164 | exempt_change | - | robot_1+robot_4 |
| 14.167 | m4_leg_start | 03bba450:robot_1:backup | backup commanded=1.514 |
| 32.24 | gt_submargin | robot_1|box:rack/SW_west | to 33.64 min gap 0.0464 m |
| 44.54 | gt_submargin | robot_1|box:rack/SW_west | to 67.94 min gap 0.0198 m |
| 47.733 | m1_stale | robot_1 | STALE 0.83 s |
| 48.633 | m4_leg_start | 03bba450:robot_4:escort | escort commanded=1.671 |
| 49.6 | m1_stale | robot_1 | STALE 0.4 s |
| 66.943 | m4_terminal | 03bba450:robot_1:backup | COMPLETED  moved=1.692 tags=['completed'] deadline=False |
| 66.991 | m4_terminal | 03bba450:robot_4:escort | COMPLETED escort complete: moved 1.672 m moved=1.663 tags=['completed'] deadline=False |
| 68.643 | safety_stop_span | robot_1 | to 623.208 (128421 lines) |
| 68.645 | safety_stop_span | robot_4 | to 623.208 (128421 lines) |
| 69.04 | gt_submargin | robot_4|box:rack/SW_west | to 568.54 min gap 0.0487 m |
| 70.567 | m1_stale | robot_4 | STALE 2.63 s |
| 70.933 | analysis | a15f3fc588d94f018454b3e719bc7c0a | positive strategy=yield involved=['robot_2', 'robot_3'] yield=robot_2 |
| 70.933 | dispatched | a15f3fc588d94f018454b3e719bc7c0a | robot_2:yield, robot_3:temporary_wait, robot_5:temporary_wait |
| 154.6 | analysis | c2f7094bf1254fa9a39aff04a69b72f3 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_4 |
| 154.6 | withheld | c2f7094bf1254fa9a39aff04a69b72f3 | robot_4:temporary_wait, robot_1:temporary_wait withheld=refusal_no_action |
| 159.433 | analysis | 28865c062e2a4cc88799910d8c4e47ad | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_4 |
| 159.433 | withheld | 28865c062e2a4cc88799910d8c4e47ad | robot_4:temporary_wait, robot_1:temporary_wait withheld=refusal_no_action |
| 169.24 | gt_submargin | robot_5|box:obstacle_1 | to 170.34 min gap 0.0304 m |
| 181.533 | analysis | f53de03829224cbf99cb54773d4dd012 | positive strategy=yield involved=['robot_1', 'robot_5'] yield=robot_1 |
| 181.533 | withheld | f53de03829224cbf99cb54773d4dd012 | robot_1:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 183.711 | safety_stop_span | robot_5 | to 623.208 (101576 lines) |
| 197.367 | m1_stale | robot_5 | STALE 1.8 s |
| 201.533 | m1_stale | robot_5 | STALE 0.87 s |
| 206.367 | m1_stale | robot_5 | STALE 5.37 s |
| 213.233 | m1_stale | robot_5 | STALE 2.0 s |
| 216.4 | m1_stale | robot_5 | STALE 8.77 s |
| 226.8 | m1_stale | robot_5 | STALE 2.53 s |
| 230.4 | m1_stale | robot_5 | STALE 2.27 s |
| 233.9 | m1_stale | robot_5 | STALE 0.53 s |
| 235.5 | analysis | cc6332da407c4e7280746fadef75bd6d | positive strategy=yield involved=['robot_1', 'robot_4', 'robot_5'] yield=robot_1 |
| 235.5 | withheld | cc6332da407c4e7280746fadef75bd6d | robot_5:temporary_wait, robot_4:temporary_wait, robot_1:temporary_wait withheld=refusal_no_action |
| 236.367 | m1_stale | robot_5 | STALE 0.8 s |
| 239.367 | analysis | 596b794bf536495a8aed6c11121842b0 | positive strategy=junction_clear involved=['robot_1', 'robot_4', 'robot_5'] yield=None |
| 239.367 | withheld | 596b794bf536495a8aed6c11121842b0 | robot_1:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 239.867 | m1_stale | robot_5 | STALE 0.73 s |
| 243.367 | analysis | 704fab63ce1e4c59b2f5c8383bd2fe73 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 243.367 | withheld | 704fab63ce1e4c59b2f5c8383bd2fe73 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 247.4 | m1_stale | robot_5 | STALE 0.77 s |
| 250.4 | m1_stale | robot_5 | STALE 2.8 s |
| 255.6 | m1_stale | robot_5 | STALE 5.73 s |
| 273.267 | m1_stale | robot_5 | STALE 0.43 s |
| 277.967 | m1_stale | robot_5 | STALE 11.53 s |
| 290.633 | m1_stale | robot_5 | STALE 0.23 s |
| 295.0 | m1_stale | robot_5 | STALE 0.87 s |
| 297.5 | m1_stale | robot_5 | STALE 1.63 s |
| 303.167 | m1_stale | robot_5 | STALE 0.2 s |
| 304.867 | m1_stale | robot_5 | STALE 5.73 s |
| 312.0 | m1_stale | robot_5 | STALE 0.2 s |
| 315.8 | m1_stale | robot_5 | STALE 2.8 s |
| 320.6 | m1_stale | robot_5 | STALE 0.2 s |
| 323.033 | m1_stale | robot_5 | STALE 1.33 s |
| 329.6 | m1_stale | robot_5 | STALE 2.93 s |
| 333.833 | m1_stale | robot_5 | STALE 0.57 s |
| 335.8 | m1_stale | robot_5 | STALE 0.6 s |
| 338.8 | m1_stale | robot_5 | STALE 0.2 s |
| 340.167 | m1_stale | robot_5 | STALE 3.83 s |
| 345.667 | m1_stale | robot_5 | STALE 10.1 s |
| 358.2 | m1_stale | robot_5 | STALE 0.2 s |
| 359.6 | m1_stale | robot_5 | STALE 0.83 s |
| 361.533 | m1_stale | robot_5 | STALE 4.27 s |
| 366.9 | m1_stale | robot_5 | STALE 1.97 s |
| 371.333 | m1_stale | robot_5 | STALE 6.53 s |
| 381.1 | m1_stale | robot_5 | STALE 3.33 s |
| 386.667 | m1_stale | robot_5 | STALE 3.43 s |
| 395.6 | m1_stale | robot_5 | STALE 0.5 s |
| 397.7 | m1_stale | robot_5 | STALE 1.97 s |
| 400.933 | m1_stale | robot_5 | STALE 0.57 s |
| 411.2 | m1_stale | robot_5 | STALE 0.2 s |
| 413.8 | m1_stale | robot_5 | STALE 2.0 s |
| 416.8 | m1_stale | robot_5 | STALE 2.8 s |
| 424.433 | m1_stale | robot_5 | STALE 0.43 s |
| 427.3 | m1_stale | robot_5 | STALE 5.17 s |
| 435.133 | m1_stale | robot_5 | STALE 6.4 s |
| 443.633 | m1_stale | robot_5 | STALE 1.83 s |
| 446.633 | m1_stale | robot_5 | STALE 3.2 s |
| 453.3 | m1_stale | robot_5 | STALE 1.0 s |
| 456.033 | m1_stale | robot_5 | STALE 0.2 s |
| 462.7 | m1_stale | robot_5 | STALE 2.4 s |
| 470.3 | m1_stale | robot_5 | STALE 0.8 s |
| 473.367 | m1_stale | robot_5 | STALE 3.47 s |
| 478.867 | m1_stale | robot_5 | STALE 0.2 s |
| 481.133 | m1_stale | robot_5 | STALE 0.53 s |
| 485.167 | m1_stale | robot_5 | STALE 1.57 s |
| 491.767 | m1_stale | robot_5 | STALE 1.03 s |
| 493.867 | m1_stale | robot_5 | STALE 1.57 s |
| 501.433 | m1_stale | robot_5 | STALE 2.57 s |
| 509.467 | m1_stale | robot_5 | STALE 1.2 s |
| 512.833 | m1_stale | robot_5 | STALE 2.23 s |
| 521.933 | m1_stale | robot_5 | STALE 2.57 s |
| 526.3 | m1_stale | robot_5 | STALE 4.63 s |
| 535.3 | m1_stale | robot_5 | STALE 6.0 s |
| 542.833 | m1_stale | robot_5 | STALE 3.9 s |
| 549.967 | m1_stale | robot_5 | STALE 0.8 s |
| 556.733 | m1_stale | robot_5 | STALE 3.77 s |
| 564.1 | m1_stale | robot_5 | STALE 1.6 s |
| 567.133 | m1_stale | robot_5 | STALE 0.77 s |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 69.067 | U:T1_fidelity / episode_gate_pass | 10/237 | 10/237 | 10/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| c2f7094bf1254fa9a39aff04a69b72f3 | 154.6 | pass / pass | 11/237 | 11/237 | 11/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| 28865c062e2a4cc88799910d8c4e47ad | 159.433 | pass / pass | 11/237 | 11/237 | 11/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| f53de03829224cbf99cb54773d4dd012 | 181.533 | pass / pass | 12/237 | 12/237 | 12/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.03} |
| cc6332da407c4e7280746fadef75bd6d | 235.5 | pass / pass | 17/237 | 17/237 | 12/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.03} |
| 596b794bf536495a8aed6c11121842b0 | 239.367 | pass / pass | 12/237 | 12/237 | 12/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.03} |
| 704fab63ce1e4c59b2f5c8383bd2fe73 | 243.367 | pass / pass | 12/237 | 12/237 | 12/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.03} |

### FU2

- Pairs: [['robot_2', 'robot_3']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 241.44, 'until_rel': 568.54}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 12.14, 'to_rel': 73.24, 'duration_s': 61.1, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_2', 'from_rel': 157.24, 'to_rel': 238.34, 'duration_s': 81.1, 'to_censor': False, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_2', 'from_rel': 241.14, 'to_rel': 568.54, 'duration_s': 327.4, 'to_censor': True, 'safety_stop_cover_fraction': 0.943}, {'robot': 'robot_3', 'from_rel': 172.14, 'to_rel': 234.14, 'duration_s': 62.0, 'to_censor': False, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_3', 'from_rel': 236.64, 'to_rel': 568.54, 'duration_s': 331.9, 'to_censor': True, 'safety_stop_cover_fraction': 0.93}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_3|box:obstacle_2: [114.74, 568.54] -0.0002; robot_2|box:obstacle_2: [238.54, 568.54] 0.0038

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 197.475 | nav2 | robot_3 | Failed to make progress |
| 197.475 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 201.564 | nav2 | robot_2 | Failed to make progress |
| 201.564 | nav2 | robot_2 | [follow_path] [ActionServer] Aborting handle. |
| 222.852 | nav2 | robot_3 | Failed to make progress |
| 222.852 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 227.42 | nav2 | robot_2 | Failed to make progress |
| 227.421 | nav2 | robot_2 | [follow_path] [ActionServer] Aborting handle. |
| 237.6 | m1_stale | robot_3 | STALE 330.73 s |
| 238.54 | gt_contact | robot_2|box:obstacle_2 | to 568.54 min gap 0.0038 m |
| 243.367 | analysis | 704fab63ce1e4c59b2f5c8383bd2fe73 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 243.367 | withheld | 704fab63ce1e4c59b2f5c8383bd2fe73 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 249.014 | nav2 | robot_3 | Failed to make progress |
| 249.014 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 252.976 | nav2 | robot_2 | Failed to make progress |
| 252.976 | nav2 | robot_2 | [follow_path] [ActionServer] Aborting handle. |
| 259.879 | safety_stop_span | robot_2 | to 623.208 (84146 lines) |
| 259.88 | safety_stop_span | robot_3 | to 623.208 (84146 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 240.967 | U:T1_fidelity / episode_gate_pass | 29/88 | 29/88 | 29/88 | False | None |

## Decisions

### 03bba450201447b78f13d94589a1ade5 at 12.367 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_1, crossing_order ['robot_4', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: robot_1 is closer to a wider area to step aside, so robot_1 should yield and allow robot_4 to pass.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=escort_park_filtered:A:robot_4:0.178', 'retreat=default:no_choice', 'grounding=node_handoff:robot_1->robot_4', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_4:2.35->1.671', 'grounding=retreat_shield:robot_5', 'grounding=retreat_shield:robot_3']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.514, 'crossing_order': ['robot_4'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 1.671, 'passer_robot_id': 'robot_4', 'reason': "robot_1 and robot_4 are in a head-on standoff in a narrow lane, blocking each other's progress.", 'retreat_choice': 'A'}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_1's retreat", 'retreat_shield_hold': True}), ('robot_3', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_1's retreat", 'retreat_shield_hold': True})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_1->robot_4'], 'G6_verbatim_contradicted': True}

### a15f3fc588d94f018454b3e719bc7c0a at 70.933 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3'], yield_robot robot_2, crossing_order ['robot_3', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 2 should yield and back up/step aside to let Robot 3 proceed first.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_2'], 'yield_robot': 'robot_2'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=escort_park_filtered:B:robot_3:0.151', 'grounding=dynamic_arms:bearing_lane:robot_3:37', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_3:2.35->1.604', 'grounding=retreat_shield:robot_5']
- Actions: [('robot_2', 'yield', {'backup_distance_m': 1.408, 'crossing_order': ['robot_3'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 1.604, 'passer_robot_id': 'robot_3', 'reason': "Robot 2 and Robot 3 are face-to-face within 0.38 meters, blocking each other's path.", 'retreat_choice': 'C'}), ('robot_3', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_2's retreat", 'retreat_shield_hold': True})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### c2f7094bf1254fa9a39aff04a69b72f3 at 154.6 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_4, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 is facing Robot 1 in a narrow lane at 0.43 m distance; making Robot 4 yield clears the passage for Robot 1.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_4', 'robot_1']}, yield refusal yield refused: no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required)', 'grounding=dynamic_arms:crossing', 'grounding=dynamic_arms:junction_box:SW']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required)'}), ('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 28865c062e2a4cc88799910d8c4e47ad at 159.433 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_4, crossing_order ['robot_1', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_4 yield and step aside or back up allows robot_1 to proceed and resolve the conflict in the narrow corridor.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_4', 'robot_1']}, yield refusal yield refused: no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required)', 'grounding=dynamic_arms:crossing', 'grounding=dynamic_arms:junction_box:SW']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required)'}), ('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### f53de03829224cbf99cb54773d4dd012 at 181.533 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_5'], yield_robot robot_1, crossing_order ['robot_5', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_4'}]
- Justification: Robot 1 should yield to Robot 5 to clear the narrow corridor and resolve the head-on conflict.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no declared junction: robot_1 runs along x and robot_5 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no declared junction: robot_1 runs along x and robot_5 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured', 'would_dispatch_robot_ids': ['robot_1', 'robot_5']}, yield refusal yield refused: no declared junction: robot_1 runs along x and robot_5 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no declared junction: robot_1 runs along x and robot_5 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured', 'grounding=dynamic_arms:crossing_refused:robot_1,robot_5']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no declared junction: robot_1 runs along x and robot_5 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no declared junction: robot_1 runs along x and robot_5 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots; no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### cc6332da407c4e7280746fadef75bd6d at 235.5 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4', 'robot_5'], yield_robot robot_1, crossing_order ['robot_5', 'robot_4', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Robot 1 should yield and back up to allow Robot 5 to pass through and clear the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_5 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_5 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_5', 'robot_4', 'robot_1']}, yield refusal yield refused: no shared lane: robot_5 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_5 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured', 'grounding=node_handoff:robot_5->robot_4', 'grounding=node_handoff_regrounded:robot_1->robot_5', 'grounding=dynamic_arms:parallel_refused:robot_5,robot_4:47']
- Actions: [('robot_5', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_5 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_5 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured'}), ('robot_1', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_5 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_5->robot_4', 'grounding=node_handoff_regrounded:robot_1->robot_5'], 'G6_verbatim_contradicted': False}

### 596b794bf536495a8aed6c11121842b0 at 239.367 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_5', 'robot_1', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Robot 1 and Robot 4 must back up (reverse) to clear the lane, allowing Robot 5 to finish its delivery and clear the bottleneck.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_5: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 704fab63ce1e4c59b2f5c8383bd2fe73 at 243.367 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): None
- Justification: The active resolution requires robot_4 and robot_1 to reverse while robot_5 waits, and robot_2 and robot_3 to resolve their proximity conflict.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 03bba450:robot_1:backup | backup | 1.514 | 12.367 | 14.167 | 66.943 | COMPLETED | 1.692 | 1.117 | 0.0198 (rack/SW_west) | None (None) | completed | False |
| 03bba450:robot_4:escort | escort | 1.671 | 12.367 | 48.633 | 66.991 | COMPLETED | 1.663 | 0.995 | 0.1726 (rack/SW_west) | None (None) | completed | False |
| a15f3fc5:robot_2:backup | backup | 1.408 | 70.933 | 73.233 | 150.625 | COMPLETED | 1.606 | 1.141 | 0.0551 (obstacle_2) | None (None) | completed | False |
| a15f3fc5:robot_3:escort | escort | 1.604 | 70.933 | 106.6 | 172.051 | FAILED | 0.516 | 0.321 | -0.0002 (obstacle_2) | None (None) | not_executed(<50%); pinned_on_declared_box:obstacle_2 | True |

## Perception STALE Spans of 10 s or More

{"robot_5": [{"from_rel": 197.367, "to_rel": 199.167, "duration_s": 1.8, "ge_10s": false}, {"from_rel": 201.533, "to_rel": 202.4, "duration_s": 0.87, "ge_10s": false}, {"from_rel": 206.367, "to_rel": 211.733, "duration_s": 5.37, "ge_10s": false}, {"from_rel": 213.233, "to_rel": 215.233, "duration_s": 2.0, "ge_10s": false}, {"from_rel": 216.4, "to_rel": 225.167, "duration_s": 8.77, "ge_10s": false}, {"from_rel": 226.8, "to_rel": 229.333, "duration_s": 2.53, "ge_10s": false}, {"from_rel": 230.4, "to_rel": 232.667, "duration_s": 2.27, "ge_10s": false}, {"from_rel": 233.9, "to_rel": 234.433, "duration_s": 0.53, "ge_10s": false}, {"from_rel": 236.367, "to_rel": 237.167, "duration_s": 0.8, "ge_10s": false}, {"from_rel": 239.867, "to_rel": 240.6, "duration_s": 0.73, "ge_10s": false}, {"from_rel": 247.4, "to_rel": 248.167, "duration_s": 0.77, "ge_10s": false}, {"from_rel": 250.4, "to_rel": 253.2, "duration_s": 2.8, "ge_10s": false}, {"from_rel": 255.6, "to_rel": 261.333, "duration_s": 5.73, "ge_10s": false}, {"from_rel": 273.267, "to_rel": 273.7, "duration_s": 0.43, "ge_10s": false}, {"from_rel": 277.967, "to_rel": 289.5, "duration_s": 11.53, "ge_10s": true}, {"from_rel": 290.633, "to_rel": 290.867, "duration_s": 0.23, "ge_10s": false}, {"from_rel": 295.0, "to_rel": 295.867, "duration_s": 0.87, "ge_10s": false}, {"from_rel": 297.5, "to_rel": 299.133, "duration_s": 1.63, "ge_10s": false}, {"from_rel": 303.167, "to_rel": 303.367, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 304.867, "to_rel": 310.6, "duration_s": 5.73, "ge_10s": false}, {"from_rel": 312.0, "to_rel": 312.2, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 315.8, "to_rel": 318.6, "duration_s": 2.8, "ge_10s": false}, {"from_rel": 320.6, "to_rel": 320.8, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 323.033, "to_rel": 324.367, "duration_s": 1.33, "ge_10s": false}, {"from_rel": 329.6, "to_rel": 332.533, "duration_s": 2.93, "ge_10s": false}, {"from_rel": 333.833, "to_rel": 334.4, "duration_s": 0.57, "ge_10s": false}, {"from_rel": 335.8, "to_rel": 336.4, "duration_s": 0.6, "ge_10s": false}, {"from_rel": 338.8, "to_rel": 339.0, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 340.167, "to_rel": 344.0, "duration_s": 3.83, "ge_10s": false}, {"from_rel": 345.667, "to_rel": 355.767, "duration_s": 10.1, "ge_10s": true}, {"from_rel": 358.2, "to_rel": 358.4, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 359.6, "to_rel": 360.433, "duration_s": 0.83, "ge_10s": false}, {"from_rel": 361.533, "to_rel": 365.8, "duration_s": 4.27, "ge_10s": false}, {"from_rel": 366.9, "to_rel": 368.867, "duration_s": 1.97, "ge_10s": false}, {"from_rel": 371.333, "to_rel": 377.867, "duration_s": 6.53, "ge_10s": false}, {"from_rel": 381.1, "to_rel": 384.433, "duration_s": 3.33, "ge_10s": false}, {"from_rel": 386.667, "to_rel": 390.1, "duration_s": 3.43, "ge_10s": false}, {"from_rel": 395.6, "to_rel": 396.1, "duration_s": 0.5, "ge_10s": false}, {"from_rel": 397.7, "to_rel": 399.667, "duration_s": 1.97, "ge_10s": false}, {"from_rel": 400.933, "to_rel": 401.5, "duration_s": 0.57, "ge_10s": false}, {"from_rel": 411.2, "to_rel": 411.4, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 413.8, "to_rel": 415.8, "duration_s": 2.0, "ge_10s": false}, {"from_rel": 416.8, "to_rel": 419.6, "duration_s": 2.8, "ge_10s": false}, {"from_rel": 424.433, "to_rel": 424.867, "duration_s": 0.43, "ge_10s": false}, {"from_rel": 427.3, "to_rel": 432.467, "duration_s": 5.17, "ge_10s": false}, {"from_rel": 435.133, "to_rel": 441.533, "duration_s": 6.4, "ge_10s": false}, {"from_rel": 443.633, "to_rel": 445.467, "duration_s": 1.83, "ge_10s": false}, {"from_rel": 446.633, "to_rel": 449.833, "duration_s": 3.2, "ge_10s": false}, {"from_rel": 453.3, "to_rel": 454.3, "duration_s": 1.0, "ge_10s": false}, {"from_rel": 456.033, "to_rel": 456.233, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 462.7, "to_rel": 465.1, "duration_s": 2.4, "ge_10s": false}, {"from_rel": 470.3, "to_rel": 471.1, "duration_s": 0.8, "ge_10s": false}, {"from_rel": 473.367, "to_rel": 476.833, "duration_s": 3.47, "ge_10s": false}, {"from_rel": 478.867, "to_rel": 479.067, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 481.133, "to_rel": 481.667, "duration_s": 0.53, "ge_10s": false}, {"from_rel": 485.167, "to_rel": 486.733, "duration_s": 1.57, "ge_10s": false}, {"from_rel": 491.767, "to_rel": 492.8, "duration_s": 1.03, "ge_10s": false}, {"from_rel": 493.867, "to_rel": 495.433, "duration_s": 1.57, "ge_10s": false}, {"from_rel": 501.433, "to_rel": 504.0, "duration_s": 2.57, "ge_10s": false}, {"from_rel": 509.467, "to_rel": 510.667, "duration_s": 1.2, "ge_10s": false}, {"from_rel": 512.833, "to_rel": 515.067, "duration_s": 2.23, "ge_10s": false}, {"from_rel": 521.933, "to_rel": 524.5, "duration_s": 2.57, "ge_10s": false}, {"from_rel": 526.3, "to_rel": 530.933, "duration_s": 4.63, "ge_10s": false}, {"from_rel": 535.3, "to_rel": 541.3, "duration_s": 6.0, "ge_10s": false}, {"from_rel": 542.833, "to_rel": 546.733, "duration_s": 3.9, "ge_10s": false}, {"from_rel": 549.967, "to_rel": 550.767, "duration_s": 0.8, "ge_10s": false}, {"from_rel": 556.733, "to_rel": 560.5, "duration_s": 3.77, "ge_10s": false}, {"from_rel": 564.1, "to_rel": 565.7, "duration_s": 1.6, "ge_10s": false}, {"from_rel": 567.133, "to_rel": 567.9, "duration_s": 0.77, "ge_10s": false}], "robot_3": [{"from_rel": 116.167, "to_rel": 233.5, "duration_s": 117.33, "ge_10s": true}, {"from_rel": 237.6, "to_rel": 568.333, "duration_s": 330.73, "ge_10s": true}]}

## Nav2 Abort Lines

- robot_2 178.544 rel-s: Failed to make progress
- robot_2 178.544 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_2 201.564 rel-s: Failed to make progress
- robot_2 201.564 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_2 227.42 rel-s: Failed to make progress
- robot_2 227.421 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_2 252.976 rel-s: Failed to make progress
- robot_2 252.976 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 174.418 rel-s: Failed to make progress
- robot_3 174.418 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 197.475 rel-s: Failed to make progress
- robot_3 197.475 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 222.852 rel-s: Failed to make progress
- robot_3 222.852 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 249.014 rel-s: Failed to make progress
- robot_3 249.014 rel-s: [follow_path] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 14.164, 'pairs': 'robot_1+robot_4'}, {'rel': 66.947, 'pairs': '-'}, {'rel': 73.732, 'pairs': 'robot_2+robot_3'}, {'rel': 150.679, 'pairs': '-'}]
- Safety-stop spans: robot_1|min_distance_violation: 2 spans; robot_4|min_distance_violation: 2 spans; robot_3|min_distance_violation: 2 spans; robot_2|min_distance_violation: 2 spans; robot_5|min_distance_violation: 1 spans
